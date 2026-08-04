#!/usr/bin/env python3
"""Report learning candidates whose destination changed after they were filed.

WHY THIS EXISTS. The ledger's `promoted` state means "a separately authorized change was
accepted" -- but nothing observes that acceptance. Seven LEARN-001 candidates sat at
`proposed` from 2026-08-02 while the repairs they describe had already merged in PR #57 on
2026-08-01, so the ledger reported seven closed repairs as pending work until a manual audit
found them. The signal was available the whole time and no process was watching it: each
candidate names a `destination`, and that destination kept receiving commits.

This is that watch. For every pending candidate it asks one question -- has the destination
been touched since the candidate was filed or last transitioned? -- and reports the ones
where the answer is yes. A hit is not a defect; it is a prompt to run the transition the
lifecycle already requires, or to record why the change was unrelated.

DELIBERATELY ADVISORY BY DEFAULT. `packet_lint.py` documents why a live gate is the wrong
instrument for a judgement call: it trains the shape rather than the work. Drift here is
evidence a human should look, not proof anything is wrong -- an unrelated commit to a shared
file is the common case. `--fail-on-drift` exists for a caller who wants a hard gate in CI;
the default exit code is 0 so this can be wired into an existing pipeline without turning a
prompt into a blocker.

Pure standard library; git is the only external call.

    python3 scripts/ledger_drift.py                    # advisory report
    python3 scripts/ledger_drift.py --fail-on-drift    # exit 1 when any candidate has drifted
    python3 scripts/ledger_drift.py --json             # machine-readable, for a bot comment
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# States that still expect action. `promoted`, `rejected`, and `retired` are closed: drift
# against a closed record is just ordinary maintenance of a file the record once named.
PENDING_STATES = {"quarantined", "proposed", "approved", "inconclusive"}

# `destination` is free text -- it may name several files, or a non-path sink such as
# "learning:candidate:lc_...". Extract only things shaped like a tracked repo path.
PATH_PATTERN = re.compile(r"\b((?:[\w.-]+/)+[\w.-]+\.\w+)\b")


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def candidate_paths(destination: str, root: Path) -> list[str]:
    """Paths named by a destination that actually exist in the working tree."""
    return [p for p in dict.fromkeys(PATH_PATTERN.findall(destination or "")) if (root / p).exists()]


def last_activity(record: dict) -> str:
    """The timestamp after which a destination commit is interesting."""
    history = record.get("transition_history") or []
    if history:
        stamps = [entry.get("at") or entry.get("timestamp") for entry in history]
        stamps = [s for s in stamps if s]
        if stamps:
            return max(stamps)
    return record.get("updated_at") or record.get("created_at") or ""


def inspect(root: Path) -> list[dict]:
    findings = []
    for path in sorted((root / "learning" / "candidates").glob("*.json")):
        record = json.loads(path.read_text())
        if record.get("promotion_state") not in PENDING_STATES:
            continue
        since = last_activity(record)
        paths = candidate_paths(record.get("destination") or "", root)
        if not paths or not since:
            continue
        commits = []
        for target in paths:
            log = git(root, "log", f"--since={since}", "--format=%h %ad %s", "--date=short",
                      "--", target)
            for line in log.splitlines():
                commits.append({"path": target, "commit": line})
        if commits:
            findings.append({
                "candidate_id": record["candidate_id"],
                "promotion_state": record["promotion_state"],
                "since": since,
                "destination_paths": paths,
                "commits": commits[:5],
                "commit_count": len(commits),
            })
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--fail-on-drift", action="store_true",
                        help="exit 1 when any pending candidate's destination has changed")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument("--annotate", action="store_true",
                        help="also emit GitHub Actions ::warning:: lines, so a drifted "
                             "candidate is visible on the pull request rather than only in a log")
    args = parser.parse_args(argv)

    if not (args.root / "learning" / "candidates").is_dir():
        print(f"no learning/candidates under {args.root}", file=sys.stderr)
        return 2

    findings = inspect(args.root)

    if args.json:
        print(json.dumps(findings, indent=2))
    elif not findings:
        print("OK - no pending candidate's destination has changed since it was filed.")
    else:
        print(f"{len(findings)} pending candidate(s) whose destination changed since filing.")
        print("Each may need a `learning_ledger.py transition`, or a note that the change was")
        print("unrelated. This is a prompt to look, not a defect.\n")
        for finding in findings:
            print(f"  {finding['candidate_id'][:11]}  [{finding['promotion_state']}]"
                  f"  since {finding['since'][:10]}  ({finding['commit_count']} commit(s))")
            for entry in finding["commits"]:
                print(f"      {entry['path']}: {entry['commit'][:96]}")
            print()

    if args.annotate:
        for finding in findings:
            paths = ", ".join(finding["destination_paths"])
            print(f"::warning file={finding['destination_paths'][0]}::"
                  f"Learning candidate {finding['candidate_id'][:11]} is "
                  f"{finding['promotion_state']} but its destination ({paths}) has "
                  f"{finding['commit_count']} commit(s) since {finding['since'][:10]}. "
                  f"If the repair landed, run learning_ledger.py transition; "
                  f"if unrelated, no action.")

    return 1 if (findings and args.fail_on_drift) else 0


if __name__ == "__main__":
    raise SystemExit(main())
