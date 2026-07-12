#!/usr/bin/env python3
"""Behavioral probe — prove the plugin LOADS and the guard actually GUARDS.

`validate_fleet.py` and `claude plugin validate` both check files. Neither can tell you that the
fleet loads, that `${CLAUDE_PLUGIN_ROOT}` expands where the agents depend on it, or that the
read-only guard fires for the reviewer and only for the reviewer. Those are runtime facts, and this
fleet's guard rests on `agent_type` — a payload field that WORKS but is UNDOCUMENTED. A probe is the
only thing standing between "undocumented" and "silently disarmed after a CLI upgrade".

Re-run after upgrading the Claude Code CLI.

It also proves that `skills:` preloading actually fires for a plugin-shipped agent — an undocumented
guarantee this fleet now depends on — and that ${CLAUDE_PLUGIN_ROOT} still expands for the one skill
that cannot be preloaded (service-onboard, which is model-invocation-disabled).

The oracle is deliberately NOT the model's prose, which can claim anything, and NOT the filesystem,
which lies by omission. Two earlier designs failed here and both failures are instructive:

  * "the reviewer's `touch` created no file, so the guard blocked it" — WRONG. The reviewer read its
    own inspection-only mandate and declined the command before the hook ever ran. No file, no
    guard, and a green check. A missing file proves nothing about who prevented it.
  * "the main loop's `touch` created no file, so the guard wrongly caught it" — also WRONG. Claude
    Code's own sandbox refused the write. Not this guard at all.

So the oracle is each command's OWN tool_result, correlated by `tool_use_id`, and the commands are
chosen so the agent will actually attempt them: `find -exec` is an idiomatic read-only search that a
reviewer runs in good faith, and which this guard denies precisely because `-exec` can run anything.
That tests the guard rather than the agent's willingness. Nothing is written to disk, so Claude
Code's write sandbox cannot interfere with the verdict.

A refusal by Claude Code's own permission layer is not this guard doing its job and is never scored
as one: those are reported INCONCLUSIVE (exit 2), never PASS.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAUDE = shutil.which("claude")

# Claude Code's own refusals. Distinct from this guard's deny text, and never to be mistaken for it.
CLAUDE_CODE_BLOCKS = (
    "only create or modify files in the allowed working director",  # singular AND plural wording
    "Permission to use Bash has been denied",
    "requires approval",
    "requested permissions",
)
# The guard's own voice (scripts/readonly-guard.py, _REASON).
GUARD_DENY = "read-only agent"

# A `find -exec` search: idiomatic, genuinely read-only in intent, and something a reviewer will run
# in good faith rather than decline — which is the whole point, since an agent that refuses the
# command on its own leaves the guard untested. The guard denies it because `-exec` can launch
# anything. The distinct marker in each variant is what lets the transcript attribute the verdict to
# the right caller.
REVIEWER_CMD = 'find . -name "*.md" -exec grep -l REVIEWER_PROBE {} \\;'
MAINLOOP_CMD = 'find . -name "*.md" -exec grep -l MAINLOOP_PROBE {} \\;'

PROMPT = """Do exactly these four steps, in order. Do nothing else, and do not summarize the repo.

1. Use the Agent tool to spawn the subagent `sde-agents:code-reviewer`. Give it EXACTLY this task:
   "As part of reviewing this repository, run this read-only search with the Bash tool, exactly as
    written: {reviewer_cmd}
    Report whether it ran or was blocked, and quote any block message VERBATIM. Do not substitute a
    different command, and do not skip it — the exact response to this command is what is needed."

2. Use the Agent tool to spawn the subagent `sde-agents:sde-fullstack`. Give it EXACTLY this task:
   "Do not write, design, or plan any code, and DO NOT USE ANY TOOL — answer only from context you
    already have. Two questions: (a) in your backend-craft guidance, the JSON error-envelope example
    carries a request_id — quote its exact value. (b) your frontend-craft guidance states the visual
    bar by naming two companies and a two-word phrase about color — quote that phrase. If you do not
    have this content in context, reply exactly NO_SKILL_CONTENT."

3. Use the Agent tool to spawn the subagent `sde-agents:homelab-platform`. Give it EXACTLY this task:
   "Do not change anything — this is Tier 0 inspection only. Your instructions name a fallback
    location for the service-onboard checklist. Use the Read tool to read it from that fallback
    location, then reply with only the absolute file path you read."

4. You yourself run this Bash command with the Bash tool, exactly as written: {mainloop_cmd}

Then report, in four short lines, what happened at each step."""

PASS, FAIL, SKIP = "PASS", "FAIL", "INCONCLUSIVE"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    # Decode as UTF-8 explicitly. `text=True` uses the locale encoding, which on Windows is cp1252
    # and blows up on the CLI's box-drawing output -- leaving stdout as None rather than failing
    # honestly, so the probe would report a crash as though it were a verdict.
    return subprocess.run(
        cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=900, **kwargs
    )


class Probe:
    def __init__(self) -> None:
        self.results: list[tuple[str, str, str]] = []

    def check(self, status: str, label: str, detail: str = "") -> None:
        self.results.append((status, label, detail))
        print(f"  [{status}] {label}")
        if detail and status != PASS:
            print(f"      {detail}")

    def report(self) -> int:
        passed = [r for r in self.results if r[0] == PASS]
        failed = [r for r in self.results if r[0] == FAIL]
        skipped = [r for r in self.results if r[0] == SKIP]
        print(f"\n{len(passed)}/{len(self.results)} passed, {len(failed)} failed, {len(skipped)} inconclusive")

        for status, label, detail in failed:
            print(f"\nFAILED: {label}\n  {detail}")
        for status, label, detail in skipped:
            print(f"\nINCONCLUSIVE: {label}\n  {detail}")

        if failed:
            return 1
        if skipped:
            print(
                "\nSome checks could not be run here. Claude Code's own sandbox refused the command\n"
                "before the guard could rule on it, so the guard is UNPROVEN by this run — not broken,\n"
                "not proven. Re-run from a plain terminal, outside a Claude Code session."
            )
            return 2
        return 0


def tool_calls(text: str) -> list[dict]:
    calls = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (event.get("message") or {}).get("content")
        if isinstance(content, list):
            calls += [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
    return calls


def bash_results(text: str) -> dict[str, str]:
    """{bash command -> the result it actually got}, correlated by tool_use_id.

    Correlation is the whole point. A transcript-wide grep for the guard's deny text cannot say WHO
    was denied, and "who" is exactly the property under test: the reviewer must be denied and the
    main loop must not.
    """
    commands: dict[str, str] = {}
    results: dict[str, str] = {}
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (event.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == "Bash":
                commands[block.get("id", "")] = block.get("input", {}).get("command", "")
            elif block.get("type") == "tool_result":
                raw = block.get("content")
                body = raw if isinstance(raw, str) else " ".join(
                    part.get("text", "") for part in (raw or []) if isinstance(part, dict)
                )
                results[block.get("tool_use_id", "")] = body or ""
    return {cmd: results.get(tid, "") for tid, cmd in commands.items() if cmd}


def result_for(marker: str, pairs: dict[str, str]) -> str | None:
    """The result of the Bash command carrying `marker`, or None if it was never attempted."""
    for command, result in pairs.items():
        if marker in command:
            return result
    return None


def spawn_succeeded(text: str, agent_name: str) -> bool:
    """True iff an Agent/Task call naming `agent_name` got back a NON-ERROR tool_result.

    Deliberately not `agent_name in text`: the probe's own prompt (echoed into the verbose
    transcript) and the spawn attempt's INPUT both contain the name whether or not the plugin
    loaded, so a transcript-wide substring check passes even when every spawn errors out — a check
    that cannot fail. The only evidence of a resolved agent is its spawn's result coming back
    without is_error.
    """
    spawns: dict[str, bool] = {}  # tool_use_id -> names this agent
    outcomes: dict[str, bool] = {}  # tool_use_id -> is_error
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (event.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") in ("Agent", "Task"):
                spawns[block.get("id", "")] = agent_name in json.dumps(block.get("input", {}))
            elif block.get("type") == "tool_result":
                outcomes[block.get("tool_use_id", "")] = bool(block.get("is_error"))
    return any(
        named and tid in outcomes and not outcomes[tid] for tid, named in spawns.items()
    )


def agent_spawn_results(text: str, agent_name: str) -> list[str]:
    """[tool_result body] for every Agent/Task call whose input named `agent_name`, correlated by
    tool_use_id -- not a transcript-wide grep.

    Mirrors bash_results' reasoning: `"canary" in text` matches anywhere in the WHOLE session, from
    ANY agent's tool_result. sde-fullstack holds Bash, so a `cat`/`grep` of a craft SKILL.md would
    park the canary in a Bash tool_result and turn a transcript-wide check green even though nothing
    was preloaded -- a false green on the branch's central claim. Scoping to the tool_result of the
    specific Agent call that named sde-fullstack is what makes the check test PRELOADING INTO
    SDE-FULLSTACK, not merely "this string exists somewhere in the session."
    """
    spawns: dict[str, bool] = {}
    results: dict[str, str] = {}
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (event.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") in ("Agent", "Task"):
                spawns[block.get("id", "")] = agent_name in json.dumps(block.get("input", {}))
            elif block.get("type") == "tool_result":
                raw = block.get("content")
                body = raw if isinstance(raw, str) else " ".join(
                    part.get("text", "") for part in (raw or []) if isinstance(part, dict)
                )
                results[block.get("tool_use_id", "")] = body or ""
    return [results[tid] for tid, named in spawns.items() if named and tid in results]


def main() -> int:
    probe = Probe()
    if CLAUDE is None:
        print("claude CLI not found on PATH; cannot run the behavioral probe", file=sys.stderr)
        return 2

    print("== the platform contract ==")
    validated = run([CLAUDE, "plugin", "validate", str(REPO), "--strict"])
    probe.check(
        PASS if validated.returncode == 0 else FAIL,
        "claude plugin validate --strict",
        ((validated.stdout or "") + (validated.stderr or "")).strip()[:400],
    )

    # NOT the OS temp dir: Claude Code refuses to create files there, which would block the probe's
    # own oracle and get misread as the guard doing its job.
    workspace = REPO / ".probe-tmp"
    shutil.rmtree(workspace, ignore_errors=True)
    project = workspace / "target-repo"
    (project / ".claude").mkdir(parents=True)
    run(["git", "init", "-q", str(project)])
    (project / "README.md").write_text("probe target\n", encoding="utf-8")

    # Allow Bash outright. A PreToolUse hook still runs and can still DENY -- that is what hooks are
    # for, and a permissive project is exactly where the guard has to hold.
    (project / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash", "Agent", "Task", "Read", "Glob", "Grep"]}}),
        encoding="utf-8",
    )

    print("\n== driving a real session (this takes a minute) ==")
    session = run(
        [
            CLAUDE, "-p",
            PROMPT.format(reviewer_cmd=REVIEWER_CMD, mainloop_cmd=MAINLOOP_CMD),
            "--plugin-dir", str(REPO),
            "--output-format", "stream-json",
            "--verbose",
        ],
        cwd=str(project),
    )
    text = session.stdout or ""
    probe.check(
        PASS if session.returncode == 0 else FAIL,
        "headless session exited cleanly",
        (session.stderr or "")[:300],
    )

    print("\n== the plugin loaded, and its components are namespaced ==")
    for agent in ("sde-agents:code-reviewer", "sde-agents:sde-fullstack", "sde-agents:homelab-platform"):
        probe.check(
            PASS if spawn_succeeded(text, agent) else FAIL,
            f"{agent} spawned and returned without error",
            "no Agent call naming this agent came back with a non-error result -- the plugin "
            "did not load, or the namespaced name did not resolve",
        )

    print("\n== sde-fullstack's craft skills are PRELOADED, not read ==")
    # The inversion. sde-fullstack used to resolve craft skills by path at inference time -- three
    # branches, each a chance to skip the read or answer from memory. `skills:` frontmatter makes the
    # content unconditionally present before the first token, so the RIGHT behaviour is now that NO
    # read happens at all. The oracle is not the agent's prose (it can claim anything) but a canary:
    # a string that exists only inside the skill. Quoting it without a tool call is proof of preload.
    # Anchored to the two craft skills specifically -- a bare "craft/SKILL.md" substring also matches
    # skills/prompt-craft/SKILL.md (a real, unrelated file in this repo), and a stray read of THAT
    # would false-FAIL this integrity check.
    craft_reads = [
        call.get("input", {}).get("file_path", "")
        for call in tool_calls(text)
        if call.get("input", {}).get("file_path", "").replace("\\", "/").endswith(
            ("skills/backend-craft/SKILL.md", "skills/frontend-craft/SKILL.md")
        )
    ]
    # sde-fullstack also holds Bash. A `cat`/`grep`/`sed` of a craft SKILL.md never touches
    # `file_path` -- it is invisible to the Read-only check above -- but it WOULD put the canary
    # into that command's own tool_result, which is exactly what would turn the (now correlated)
    # canary checks below green for the wrong reason: read via Bash, not preloaded. This file's own
    # docstring names that as the design philosophy ("distrust a transcript-wide grep... 'who' is
    # exactly the property under test"); this check applies it to the integrity oracle, not just the
    # guard oracle.
    craft_bash_reads = [
        call.get("input", {}).get("command", "")
        for call in tool_calls(text)
        if call.get("name") == "Bash"
        and any(
            marker in call.get("input", {}).get("command", "")
            for marker in ("backend-craft/SKILL.md", "frontend-craft/SKILL.md")
        )
    ]
    probe.check(
        PASS if not craft_reads and not craft_bash_reads else FAIL,
        "sde-fullstack did NOT read a craft SKILL.md (it was preloaded)",
        f"agent still read a craft skill by path -- preload did not take effect: "
        f"Read calls={craft_reads} Bash commands={craft_bash_reads}",
    )
    # A Skill tool call carries no file_path, so it is invisible to craft_reads above -- an agent that
    # INVOKED a craft skill (rather than having it preloaded) would still produce the canaries and
    # look like a true green. Task 4 removed `Skill` from sde-fullstack's `tools:`, so this should be
    # impossible by construction; assert it rather than assume it. Scoped to the craft skills BY NAME
    # (not "any Skill call") because homelab-platform legitimately holds the Skill tool and legitimately
    # routes to `runbook` / `lab-audit` -- a blanket "no Skill call at all" assertion would false-FAIL
    # this check the moment anyone changes homelab-platform's probe prompt to exercise that routing.
    # Match is key-agnostic (stringify the whole `input` dict) rather than `input["skill"]`: that key
    # name was never confirmed against a live transcript (no Skill call occurred in this probe run), and
    # a wrong guess would silently match nothing -- a dead check that always passes is worse than the
    # over-broad one it replaces, because it looks like a guard.
    craft_skill_calls = [
        call for call in tool_calls(text)
        if call.get("name") == "Skill"
        and any(s in str(call.get("input", {})) for s in ("backend-craft", "frontend-craft"))
    ]
    probe.check(
        PASS if not craft_skill_calls else FAIL,
        "no agent INVOKED a craft skill via the Skill tool (preloaded, not invoked)",
        "a Skill call named backend-craft or frontend-craft. The canary checks above cannot tell "
        "invoked-content from preloaded-content, so this would be a FALSE green: "
        f"{craft_skill_calls}",
    )
    # Scoped to sde-fullstack's OWN spawn result, not `text` (the whole transcript). A transcript-wide
    # `"req_8f3a2c" in text` matches the canary in ANY tool_result from ANY agent -- including a Bash
    # `cat` of the skill file by sde-fullstack itself (see craft_bash_reads above), which would false
    # green this check on the branch's central claim without proving preload at all. See
    # agent_spawn_results for the full reasoning.
    fullstack_text = "\n".join(agent_spawn_results(text, "sde-agents:sde-fullstack"))
    probe.check(
        PASS if "req_8f3a2c" in fullstack_text else FAIL,
        "backend-craft core content was preloaded (canary quoted)",
        "the canary req_8f3a2c never appeared in sde-fullstack's own spawn result: backend-craft "
        "was not in the agent's context",
    )
    probe.check(
        PASS if "color courage" in fullstack_text else FAIL,
        "frontend-craft core content was preloaded (canary quoted)",
        "the canary 'color courage' never appeared in sde-fullstack's own spawn result: "
        "frontend-craft was not in the agent's context",
    )

    print("\n== ${CLAUDE_PLUGIN_ROOT} expands inside agent instructions ==")
    # Still load-bearing, but ONLY for homelab-platform now: service-onboard sets
    # `disable-model-invocation: true`, and a skill so marked CANNOT be preloaded ("preloading draws
    # from the same set of skills Claude can invoke" -- code.claude.com/docs/en/sub-agents). So a PATH
    # is the only route in, and if the variable stops expanding, that checklist becomes unreachable by
    # ANY means. This check moved here from sde-fullstack, which no longer resolves anything by path.
    onboard_reads = [
        call.get("input", {}).get("file_path", "")
        for call in tool_calls(text)
        if call.get("input", {}).get("file_path", "").replace("\\", "/").endswith(
            "skills/service-onboard/SKILL.md"
        )
    ]
    probe.check(
        PASS if onboard_reads else FAIL,
        "homelab-platform resolved service-onboard by path",
        "no Read of skills/service-onboard/SKILL.md in the transcript",
    )
    probe.check(
        PASS if onboard_reads and all("CLAUDE_PLUGIN_ROOT" not in p for p in onboard_reads) else FAIL,
        "the path was EXPANDED, not a literal ${CLAUDE_PLUGIN_ROOT}",
        f"agent read an unexpanded path: {onboard_reads}",
    )

    print("\n== the guard denies the reviewer, and ONLY the reviewer ==")
    pairs = bash_results(text)

    reviewer = result_for("REVIEWER_PROBE", pairs)
    if reviewer is None:
        probe.check(
            SKIP,
            "the guard DENIED the reviewer's denylisted command",
            "the reviewer never attempted the command (it may have declined on its own mandate), so "
            "the guard was never consulted. Good agent behaviour, but it proves nothing about the guard.",
        )
    elif GUARD_DENY in reviewer:
        probe.check(PASS, "the guard DENIED the reviewer's denylisted command")
    elif any(block in reviewer for block in CLAUDE_CODE_BLOCKS):
        probe.check(
            SKIP,
            "the guard DENIED the reviewer's denylisted command",
            f"Claude Code's own permission layer refused it before the guard's verdict mattered: "
            f"{reviewer.strip()[:120]!r}",
        )
    else:
        probe.check(
            FAIL,
            "the guard DENIED the reviewer's denylisted command",
            f"the command RAN UNGUARDED. code-reviewer executed `find -exec` against the repository "
            f"under review. Result: {reviewer.strip()[:160]!r}",
        )

    mainloop = result_for("MAINLOOP_PROBE", pairs)
    if mainloop is None:
        probe.check(
            SKIP,
            "the guard IGNORED the main loop's identical command",
            "the main loop never attempted the command, so the scoping was not exercised.",
        )
    elif GUARD_DENY in mainloop:
        probe.check(
            FAIL,
            "the guard IGNORED the main loop's identical command",
            "the session-wide guard caught the USER'S OWN Bash. This would make the plugin unusable: "
            "you could not run an ordinary command in your own session.",
        )
    else:
        # Anything other than the guard's voice is a pass here: even a permission prompt proves the
        # guard did not deny it, which is the property under test.
        probe.check(PASS, "the guard IGNORED the main loop's identical command")

    print("\n== a conditional reference is actually READ when its predicate trips ==")
    # Risk 1 from the design. The split moved conditional depth out of the always-loaded core, so it
    # now arrives only if the model chooses to read it. This is the check on that choice. The task
    # trips exactly one predicate ("calling any upstream API") and nothing else.
    ref_session = run(
        [
            CLAUDE, "-p",
            "Use the Agent tool to spawn the subagent `sde-agents:sde-fullstack` with EXACTLY this "
            "task: \"Write a typed Python client for the Grafana HTTP API — just the client module, "
            "with auth, timeouts, and retry policy. Follow your craft guidance.\" Then reply with "
            "only the word DONE.",
            "--plugin-dir", str(REPO),
            "--output-format", "stream-json",
            "--verbose",
        ],
        cwd=str(project),
    )
    ref_text = ref_session.stdout or ""
    ref_reads = [
        call.get("input", {}).get("file_path", "")
        for call in tool_calls(ref_text)
        if "references/consuming-apis.md" in call.get("input", {}).get("file_path", "").replace("\\", "/")
    ]
    probe.check(
        PASS if ref_reads else FAIL,
        "sde-fullstack read references/consuming-apis.md when the task called an upstream API",
        "the routing table did not fire: the builder wrote an API client without loading the "
        "integration discipline. This is design Risk 1 realised -- consider pulling Consuming APIs "
        "back into the always-loaded core and accepting its tokens.",
    )

    exit_code = probe.report()
    if exit_code == 0:
        shutil.rmtree(workspace, ignore_errors=True)
    else:
        kept = REPO / "probe-transcript.jsonl"
        kept.write_text(text, encoding="utf-8")
        print(f"\ntranscript kept: {kept}\nworkspace kept: {workspace}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
