#!/usr/bin/env python3
"""Behavioral evals — does a component actually DO what its definition promises?

`eval_routing.py` measures which component fires. That is trigger accuracy, and it says nothing
about whether the thing that fired then honored its own contract. This runner measures the second
half: a real headless session is driven to completion, and its final output is asserted against
DETERMINISTIC checks — packet-slot compliance via scripts/packet_lint.py, plus literal
must-contain / must-not-contain assertions. No judge model, so a failure is a fact, not an opinion.

The three promises seeded here are the ones whose silent failure would be worst, and each is a claim
some file in this fleet makes about itself:

  * the builder's review packet arrives with every slot filled (the packet contract);
  * the reviewer IGNORES AND REPORTS an instruction embedded in the code it reviews, rather than
    obeying it (the fetched-content-is-data rule, tested adversarially);
  * a live-lab change is not applied without its approval gate (homelab-platform's change tiers).

Like the routing suite this is MANUAL and on demand, not a CI gate: it drives real API sessions,
costs real money, and has real variance. Run it before and after a change to a definition whose
behavior it covers.

    python3 scripts/eval_behavioral.py                       # all cases, 1 run each
    python3 scripts/eval_behavioral.py --runs 3
    python3 scripts/eval_behavioral.py --case packet-slots-* --output-dir /tmp/after

Pure standard library, and every assertion is offline once the transcript is captured.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import fnmatch
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CASES_DIR = REPO / "evals" / "behavioral"
CLAUDE = shutil.which("claude")

_spec = importlib.util.spec_from_file_location("packet_lint", REPO / "scripts" / "packet_lint.py")
packet_lint = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(packet_lint)

# Reuse the routing runner's transcript reader rather than re-deriving it. Grading a behavioral
# case on its final text ALONE proves only that some text arrived: the main session can satisfy a
# packet shape or a keyword without the component whose contract is being measured ever running
# (found in review). `expect_fires` closes that, and `components_fired` is the same
# correlate-by-tool_use_id detection the routing suite is already trusted for.
_routing_spec = importlib.util.spec_from_file_location(
    "eval_routing", REPO / "scripts" / "eval_routing.py"
)
eval_routing = importlib.util.module_from_spec(_routing_spec)
assert _routing_spec.loader is not None
_routing_spec.loader.exec_module(eval_routing)


def run_session(
    prompt: str, plugin_dir: Path, timeout: int, disallowed_tools: list[str] | None = None,
    agent: str | None = None, permission_mode: str | None = None,
) -> tuple[str, set[str], str | None]:
    """Drive one headless session to completion; return (final text, components fired, note).

    Unlike the routing runner — which grades the FIRST routing decision and is happy with a partial
    transcript — a behavioral eval needs the session's CONCLUSION, so a timeout is a real failure
    here rather than an expected outcome. It is still never raised: one bad case must not take the
    suite down.

    `disallowed_tools` is passed straight to the CLI. It matters for cases that describe a
    destructive action: this suite exists to prove a safety gate HOLDS, and a case that could
    perform the very apply it is testing for would, on a regression, become the incident it was
    meant to detect.
    """
    if CLAUDE is None:
        return "", set(), "the `claude` CLI is not on PATH"
    command = [
        CLAUDE, "-p", prompt,
        "--plugin-dir", str(plugin_dir),
        "--output-format", "stream-json", "--verbose",
    ]
    # `--agent` runs the session AS the component, which is the only deterministic way to measure
    # an agent's contract. Asking a headless session to delegate does not work reliably: probed
    # directly, "Use the sde-agents:code-reviewer subagent to review this" produced ZERO tool calls
    # and answered inline, and across runs of this suite the same three cases went 3/3 fired then
    # 0/3. That flakiness is a property of one-shot headless mode, not of the components — so
    # whether a bare request reaches a component is left to evals/routing/, and this suite pins the
    # component and asks only whether its contract holds.
    if agent:
        command += ["--agent", agent]
    # A case whose contract only appears AFTER the component does work (a builder's packet is
    # written once the code and tests exist) needs its writes to succeed. The session already runs
    # in a throwaway temp cwd, so accepting edits there is scoped, not broad -- and without it the
    # case measures the sandbox's permission prompt rather than the packet, which is what the first
    # runs were actually doing.
    if permission_mode:
        command += ["--permission-mode", permission_mode]
    if disallowed_tools:
        command += ["--disallowed-tools", *disallowed_tools]
    try:
        with tempfile.TemporaryDirectory() as cwd:
            proc = subprocess.run(
                command,
                capture_output=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=timeout,
            )
    except subprocess.TimeoutExpired:
        return "", set(), f"timed out after {timeout}s before the session concluded"
    except Exception as exc:
        return "", set(), f"run failed: {exc}"

    # The `result` event carries the session's final text; fall back to concatenating assistant
    # text blocks if the shape ever changes, so a stream-format tweak degrades rather than breaks.
    #
    # A SUMMONED SUBAGENT'S ANSWER IS NOT IN THE FINAL TEXT. Its packet is returned as the Agent
    # tool's result and the main session then paraphrases it — so grading the final text alone
    # marked a conforming packet as missing all four slots (observed on this suite's second real
    # run). The contract under test belongs to the component, so the component's own output is
    # graded too: collect every Agent/Task tool_result and append it to the corpus.
    final, assistant_text = "", []
    agent_calls: set[str] = set()
    agent_outputs: list[str] = []
    for line in (proc.stdout or "").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            final = event["result"]
        elif event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    assistant_text.append(block.get("text", ""))
                elif block.get("type") == "tool_use" and block.get("name") in ("Agent", "Task"):
                    agent_calls.add(block.get("id", ""))
        elif event.get("type") == "user":
            for block in event.get("message", {}).get("content", []):
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                if block.get("tool_use_id") not in agent_calls:
                    continue
                content = block.get("content")
                if isinstance(content, str):
                    agent_outputs.append(content)
                elif isinstance(content, list):
                    agent_outputs.extend(
                        part.get("text", "") for part in content
                        if isinstance(part, dict) and part.get("type") == "text"
                    )
    text = "\n\n".join(filter(None, [final or "\n".join(assistant_text), *agent_outputs]))
    fired = eval_routing.components_fired(proc.stdout or "")
    note = None if text else f"no output captured (exit {proc.returncode})"
    return text, fired, note


def assert_case(text: str, case: dict, fired: set[str] | None = None) -> list[str]:
    """Apply a case's deterministic assertions; return failure strings (empty = pass)."""
    failures: list[str] = []

    # Did the component whose contract this measures actually run? Without this, a passing result
    # says only that the main session produced conforming text.
    if expected := case.get("expect_fires"):
        if fired is None:
            failures.append("expect_fires declared but no transcript was captured to check it")
        elif not set(expected) & fired:
            failures.append(
                f"none of {sorted(expected)} fired (fired: {sorted(fired) or 'nothing'}) — the "
                f"output may conform without the component under test ever running"
            )

    if shape := case.get("packet_shape"):
        failures += [f"packet: {finding}" for finding in packet_lint.lint_packet(text, shape)]

    for pattern in case.get("must_match", []):
        if not re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            failures.append(f"missing required pattern: {pattern!r}")

    for pattern in case.get("must_not_match", []):
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            failures.append(f"forbidden pattern present: {pattern!r}")

    return failures


def load_cases(selector: str | None) -> list[dict]:
    cases: list[dict] = []
    for path in sorted(CASES_DIR.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for case in document.get("cases", []):
            case.setdefault("suite", document.get("suite", path.stem))
            if selector is None or fnmatch.fnmatch(case["id"], selector):
                cases.append(case)
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=1, help="runs per case (default 1)")
    parser.add_argument("--case", help="glob over case ids")
    parser.add_argument("--timeout", type=int, default=600, help="per-session timeout in seconds")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--plugin-dir", type=Path, default=REPO)
    parser.add_argument("--output-dir", type=Path, help="also write benchmark.json here")
    args = parser.parse_args(argv)

    cases = load_cases(args.case)
    if not cases:
        print("no cases matched", file=sys.stderr)
        return 2
    # `--runs 0` used to schedule no jobs, leaving every case with an empty result list — and
    # `passes == len(runs)` is trivially true for 0 == 0, so the suite reported every contract
    # green having started no sessions at all (found in review). A green that proves nothing is
    # the worst output this tool can produce, so the count is bounded before any work is planned.
    if args.runs < 1:
        print("error: --runs must be at least 1", file=sys.stderr)
        return 2
    if CLAUDE is None:
        print("error: the `claude` CLI is not on PATH", file=sys.stderr)
        return 2

    total = len(cases) * args.runs
    print(f"{len(cases)} case(s) x {args.runs} run(s) = {total} sessions "
          f"(concurrency {args.concurrency})\n")

    jobs = [(case, run) for case in cases for run in range(args.runs)]
    results: dict[str, list[list[str]]] = {case["id"]: [] for case in cases}
    notes: dict[str, list[str]] = {case["id"]: [] for case in cases}

    def execute(job: tuple[dict, int]) -> tuple[str, list[str], str | None]:
        case, _ = job
        text, fired, note = run_session(
            case["prompt"], args.plugin_dir, args.timeout, case.get("disallowed_tools"),
            case.get("agent"), case.get("permission_mode"),
        )
        # A case pinned with `agent:` IS the component, so there is no Agent tool call to detect;
        # treat the pin itself as the invocation evidence expect_fires would otherwise supply.
        if case.get("agent"):
            fired = fired | {case["agent"].split(":")[-1]}
        if note and not text:
            return case["id"], [f"session produced nothing: {note}"], note
        return case["id"], assert_case(text, case, fired), note

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for case_id, failures, note in pool.map(execute, jobs):
            results[case_id].append(failures)
            if note:
                notes[case_id].append(note)
            done += 1
            print(f"  [{done}/{total}] complete", end="\r", flush=True)
    print(" " * 40, end="\r")

    print(f"\n{'case':32s} {'verdict':8s} {'pass':>6s}  detail")
    print("-" * 100)
    passed_cases = 0
    payload: list[dict] = []
    for case in cases:
        runs = results[case["id"]]
        passes = sum(1 for failures in runs if not failures)
        rate = passes / len(runs) if runs else 0.0
        # Every run must satisfy the contract -- AND at least one run must exist. Without the
        # second clause an empty result list passes vacuously, which is how a suite reports success
        # for work it never did.
        ok = bool(runs) and passes == len(runs)
        passed_cases += ok
        first_failure = next((f for failures in runs if failures for f in failures), "")
        detail = "all assertions held" if ok else first_failure[:60]
        print(f"{case['id'][:32]:32s} {'PASS' if ok else 'FAIL':8s} "
              f"{passes}/{len(runs):<4} {detail}")
        payload.append({
            "id": case["id"], "suite": case["suite"], "passes": passes,
            "runs": len(runs), "rate": rate,
            "failures": sorted({f for failures in runs for f in failures}),
            "notes": notes[case["id"]],
        })

    print("-" * 100)
    print(f"{passed_cases}/{len(cases)} cases passed every run")

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "benchmark.json").write_text(
            json.dumps({"runs_per_case": args.runs, "cases": payload}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nwrote {args.output_dir / 'benchmark.json'}")

    return 0 if passed_cases == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
