#!/usr/bin/env python3
"""Routing eval runner — measure whether the fleet routes a prompt to the right component.

WHY THIS EXISTS. `agents/prompt-engineer.md` mandates eval-first prompt changes (baseline,
repetitions, fresh contexts), but the fleet shipped none — it preached a practice it did not
follow. This is the practice: given a realistic prompt, does the intended agent/skill fire, and do
near-miss prompts that merely share vocabulary (write / fix / optimize / rewrite) route ELSEWHERE?

WHY A LOCAL RUNNER AND NOT `claude plugin eval`. The native harness is the right long-term home —
it does ablation baselines, repetitions, and LLM grading — but it is currently EARLY ACCESS and
does not run in every environment. The case files here follow the Agent Skills eval shape
(agentskills.io/skill-creation/evaluating-skills) so they migrate cleanly when it opens; this
runner exercises them TODAY, and retires when `claude plugin eval` is generally available.

HOW IT GRADES. Routing is a fact you can read straight off the transcript — which Skill was
invoked, which subagent was spawned — so grading needs no judge model and is deterministic and
free. A positive case passes when an expected cluster member fires; a negative passes only when NO
cluster member fires. Routing is probabilistic (a skill/agent fires perhaps half the time in
practice), so results are RATES over --runs, not booleans. The load-bearing signals are a positive
whose rate collapses after a description edit (regression) and a negative that fires at all
(over-trigger) — both visible in the delta between runs of this suite.

Pure standard library. Spawns headless `claude -p ... --plugin-dir <repo>` sessions, one per run,
each a fresh context (the isolation the methodology requires).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import fnmatch
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAUDE = shutil.which("claude")

# The fleet roster, derived from the repo so this never drifts from what actually ships.
FLEET_AGENTS = frozenset(p.stem for p in (REPO / "agents").glob("*.md"))
FLEET_SKILLS = frozenset(p.name for p in (REPO / "skills").iterdir() if p.is_dir()) if (REPO / "skills").is_dir() else frozenset()
FLEET = FLEET_AGENTS | FLEET_SKILLS


def strip_ns(name: str) -> str:
    """`sde-agents:prompt-craft` -> `prompt-craft`; a bare name is returned unchanged."""
    return name.split(":", 1)[1] if ":" in name else name


def components_fired(transcript: str) -> set[str]:
    """The set of fleet components (bare names) invoked anywhere in a run's transcript.

    Detects the two invocation paths: the Skill tool (a skill fired) and the Agent/Task tool (a
    subagent spawned). Rather than guess the exact input field name — which differs across the two
    and across CLI versions — it scans each relevant tool_use's input values for a known fleet name.
    A component named only in ASSISTANT PROSE (not a tool call) is intentionally NOT counted: the
    model mentioning 'prompt-craft' is not the same as prompt-craft firing. A tool_use whose matching
    tool_result is a GENUINE dispatch failure is likewise NOT counted — counting a truly failed
    spawn would produce false PASS results (see scripts/probe_plugin.py:174 for the same
    correlate-by-tool_use_id pattern).

    Crucially, `is_error` is NOT a reliable "the call failed" flag for the Skill tool. A skill that
    restricts tools (allowed-tools / disallowed-tools) is LAUNCHED via a tool_result the CLI marks
    `is_error: true` with content "Execute skill: <name>"; a skill WITHOUT restrictions reports
    "Launching skill: <name>" with is_error unset. Both mean the skill was invoked — the routing fact
    we grade. Treating the first as an error silently dropped every tool-restricting skill's
    invocation: `lab-audit` (which sets `disallowed-tools`) scored 0/N despite routing correctly on
    every run, and — worse — an over-trigger of `lab-audit` on a NEGATIVE case was invisible, a false
    PASS. So a skill-launch control signal is never treated as a failure; only a genuine hard error
    (real dispatch failure, different content) excludes the routing decision.
    """
    launch_signals = ("execute skill:", "launching skill:")
    candidates: dict[str, set[str]] = {}  # tool_use_id -> bare names named in this call
    errored: set[str] = set()  # tool_use_ids whose tool_result was a genuine dispatch failure
    for line in transcript.splitlines():
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
            btype = block.get("type")
            if btype == "tool_use" and block.get("name") in ("Skill", "Agent", "Task"):
                names = {strip_ns(v) for v in _string_values(block.get("input"))} & FLEET
                if names:
                    candidates[block.get("id", "")] = names
            elif btype == "tool_result" and block.get("is_error"):
                result_text = " ".join(_string_values(block.get("content"))).lower()
                if any(sig in result_text for sig in launch_signals):
                    continue  # skill-launch control signal, not a failure — the skill WAS invoked
                errored.add(block.get("tool_use_id", ""))
    fired: set[str] = set()
    for tid, names in candidates.items():
        if tid not in errored:
            fired |= names
    return fired


def _string_values(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in _string_values(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in _string_values(v)]
    return []


def run_once(prompt: str, plugin_dir: Path, timeout: int = 180) -> dict:
    """One headless run in a fresh temp cwd. Returns {fired, tokens, duration_ms, error}.

    Never raises: this drives a flaky, sometimes long-running subprocess, and a routing eval only
    needs the FIRST routing decision, not a completed session. A timeout is therefore expected, not
    exceptional — the transcript captured up to that point almost always already contains the Skill
    or Agent call we grade on. (An earlier version let TimeoutExpired propagate out of the thread
    pool, and one prompt that induced a long agentic build took the whole 16-case suite down with
    it.) So: parse whatever stdout exists whether the run exits, times out, or errors, and only
    report an error when NOTHING was captured.
    """
    stdout, stderr, note = "", "", None
    try:
        with tempfile.TemporaryDirectory() as cwd:
            proc = subprocess.run(
                [
                    CLAUDE, "-p", prompt,
                    "--plugin-dir", str(plugin_dir),
                    "--output-format", "stream-json", "--verbose",
                ],
                capture_output=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=timeout,
            )
            stdout, stderr = proc.stdout or "", proc.stderr or ""
            if proc.returncode != 0:
                note = f"exit {proc.returncode}: {stderr[:150]}"
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        note = f"timed out after {timeout}s (partial transcript graded)"
    except Exception as exc:  # a broken spawn must not crash the suite
        note = f"run failed: {exc}"

    tokens = duration = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            usage = event.get("usage") or {}
            tokens = (usage.get("input_tokens", 0) or 0) + (usage.get("output_tokens", 0) or 0) or None
            duration = event.get("duration_ms")

    fired = sorted(components_fired(stdout))
    # A timeout that captured a firing is a usable result; a timeout that captured NOTHING is an
    # error (otherwise negatives would pass vacuously on empty transcripts). Non-timeout notes are
    # always errors.
    error = note if (note and not fired) else None
    return {"fired": fired, "tokens": tokens, "duration_ms": duration, "error": error}


def score_case(case: dict, runs: list[dict], members: set[str], threshold: float) -> dict:
    """Aggregate a case's runs into rates and a pass/fail verdict."""
    n = len(runs)
    member_hits = [bool(set(r["fired"]) & members) for r in runs]
    fire_rate = sum(member_hits) / n if n else 0.0
    polarity = case["polarity"]

    if polarity == "positive":
        expected = set(case.get("expect_fires", members))
        correct = [bool(set(r["fired"]) & expected) for r in runs]
        correct_rate = sum(correct) / n if n else 0.0
        passed = correct_rate >= threshold
        detail = f"expected {sorted(expected)} fired in {sum(correct)}/{n} runs"
    else:
        correct_rate = sum(not h for h in member_hits) / n if n else 0.0  # rate of NOT firing
        passed = fire_rate == 0.0  # a negative fails if the cluster fires even once
        detail = f"cluster fired in {sum(member_hits)}/{n} runs (want 0)"

    # What else fired — diagnostic, e.g. a negative correctly landing on backend-craft/sde-fullstack.
    other = sorted({c for r in runs for c in r["fired"]} - members)
    return {
        "id": case["id"],
        "polarity": polarity,
        "tags": case.get("tags", []),
        "passed": passed,
        "cluster_fire_rate": round(fire_rate, 3),
        "correct_rate": round(correct_rate, 3),
        "detail": detail,
        "also_fired": other,
        "errors": [r["error"] for r in runs if r["error"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cluster", nargs="?", default=str(REPO / "evals" / "routing" / "prompt-tooling.json"),
                        help="path to a cluster JSON file")
    parser.add_argument("--runs", type=int, default=3, help="runs per case (default 3)")
    parser.add_argument("--plugin-dir", type=Path, default=REPO, help="plugin to load (default this repo)")
    parser.add_argument("--case", default="*", help="glob over case ids (default all)")
    parser.add_argument("--limit", type=int, default=0, help="cap number of cases (0 = all) — for cheap demo runs")
    parser.add_argument("--concurrency", type=int, default=4, help="parallel runs (default 4)")
    parser.add_argument("--timeout", type=int, default=180,
                        help="per-run seconds before the session is cut and its partial transcript graded (default 180)")
    parser.add_argument("--threshold", type=float, default=0.5, help="positive passes at this fire rate (default 0.5)")
    parser.add_argument("--output-dir", type=Path, default=None, help="write benchmark.json here")
    args = parser.parse_args()

    if args.runs < 1:
        print(f"--runs must be >= 1 (got {args.runs}); 0 would make every negative pass vacuously", file=sys.stderr)
        return 2
    if CLAUDE is None:
        print("claude CLI not found on PATH", file=sys.stderr)
        return 2

    spec = json.loads(Path(args.cluster).read_text(encoding="utf-8"))
    members = set(spec["members"])
    cases = [c for c in spec["cases"] if fnmatch.fnmatch(c["id"], args.case)]
    if args.limit:
        cases = cases[:args.limit]
    if not cases:
        print("no cases matched", file=sys.stderr)
        return 2

    # Flatten to (case, run_index) work items so all runs across all cases share the pool.
    work = [(c, i) for c in cases for i in range(args.runs)]
    print(f"cluster '{spec['cluster']}': {len(cases)} cases x {args.runs} runs = {len(work)} sessions "
          f"(members: {sorted(members)}, concurrency {args.concurrency})\n")

    results_by_case: dict[str, list[dict]] = {c["id"]: [] for c in cases}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(run_once, c["prompt"], args.plugin_dir, args.timeout): c["id"] for c, _ in work}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            results_by_case[futures[future]].append(future.result())
            done += 1
            print(f"  [{done}/{len(work)}] runs complete", end="\r")
    print()

    scored = [score_case(c, results_by_case[c["id"]], members, args.threshold) for c in cases]

    print("\n{:<28} {:<9} {:>6} {:<40}".format("case", "verdict", "rate", "detail"))
    print("-" * 90)
    for s in scored:
        rate = s["correct_rate"]
        mark = "PASS" if s["passed"] else "FAIL"
        also = f"  [also fired: {', '.join(s['also_fired'])}]" if s["also_fired"] else ""
        print("{:<28} {:<9} {:>6.0%} {}{}".format(s["id"], mark, rate, s["detail"], also))
        for err in s["errors"]:
            print(f"    ! run error: {err}")

    passed = sum(s["passed"] for s in scored)
    pos = [s for s in scored if s["polarity"] == "positive"]
    neg = [s for s in scored if s["polarity"] == "negative"]
    print("-" * 90)
    print(f"{passed}/{len(scored)} passed  "
          f"(positives: {sum(s['passed'] for s in pos)}/{len(pos)} routed correctly, "
          f"negatives: {sum(s['passed'] for s in neg)}/{len(neg)} correctly did NOT fire)")

    benchmark = {
        "cluster": spec["cluster"],
        "runs_per_case": args.runs,
        "members": sorted(members),
        "summary": {"passed": passed, "total": len(scored)},
        "cases": scored,
    }
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "benchmark.json").write_text(json.dumps(benchmark, indent=2), encoding="utf-8")
        print(f"\nwrote {args.output_dir / 'benchmark.json'}")

    # Exit non-zero if any case failed, so a caller can gate on it if they choose.
    return 0 if passed == len(scored) else 1


if __name__ == "__main__":
    raise SystemExit(main())
