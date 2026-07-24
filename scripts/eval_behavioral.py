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


def run_session(prompt: str, plugin_dir: Path, timeout: int) -> tuple[str, str | None]:
    """Drive one headless session to completion and return (final assistant text, note).

    Unlike the routing runner — which grades the FIRST routing decision and is happy with a partial
    transcript — a behavioral eval needs the session's CONCLUSION, so a timeout is a real failure
    here rather than an expected outcome. It is still never raised: one bad case must not take the
    suite down.
    """
    if CLAUDE is None:
        return "", "the `claude` CLI is not on PATH"
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
    except subprocess.TimeoutExpired:
        return "", f"timed out after {timeout}s before the session concluded"
    except Exception as exc:
        return "", f"run failed: {exc}"

    # The `result` event carries the session's final text; fall back to concatenating assistant
    # text blocks if the shape ever changes, so a stream-format tweak degrades rather than breaks.
    final, assistant_text = "", []
    for line in (proc.stdout or "").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            final = event["result"]
        elif event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    assistant_text.append(block.get("text", ""))
    text = final or "\n".join(assistant_text)
    note = None if text else f"no output captured (exit {proc.returncode})"
    return text, note


def assert_case(text: str, case: dict) -> list[str]:
    """Apply a case's deterministic assertions; return failure strings (empty = pass)."""
    failures: list[str] = []

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
        text, note = run_session(case["prompt"], args.plugin_dir, args.timeout)
        if note and not text:
            return case["id"], [f"session produced nothing: {note}"], note
        return case["id"], assert_case(text, case), note

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
        ok = passes == len(runs)          # every run must satisfy the contract
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
