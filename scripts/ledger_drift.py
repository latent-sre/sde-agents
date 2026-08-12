#!/usr/bin/env python3
"""Report pending learning candidates whose destination changed after their ledger record.

WHY THIS EXISTS. The ledger's `promoted` state means "a separately authorized change was
accepted" -- but nothing observes that acceptance. A pending record can therefore outlive the
work it describes. Each candidate names a `destination`, and later changes to that destination
are a cheap, reviewable signal that the lifecycle decision may need another look.

This is that watch. For every pending candidate it asks one question -- has the destination
been touched since the candidate's latest committed ledger state? -- and reports the ones
where the answer is yes. A hit is not a defect; it is a prompt to run the transition the
lifecycle already requires, or to record why the change was unrelated.

The watch has a second face. A pending candidate with no watchable destination -- every
quarantined record, whose `destination` is null by construction, and any triaged record naming
a non-path sink -- gives the question above nothing to bind to, so without a separate report it
ages invisibly: fifteen records once sat untriaged for five days while this checker printed OK.
Those are reported as unwatched intake, advisory always -- absence of triage is not destination
drift, and gating on it would train hasty triage rather than prompt it.

LIMIT. History is not a semantic repair detector. A destination change already ancestral to,
or committed together with, the candidate's latest state is part of the baseline and is not
reported. This checker finds later activity; it does not decide whether earlier work satisfied
the candidate.

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
from pathlib import Path, PurePosixPath

# The lifecycle module owns this vocabulary. Keeping a second literal here would let the drift
# job silently stop watching a newly added pending state even while the ledger accepted it.
if __package__:
    from .learning_ledger import PENDING_STATES
else:
    from learning_ledger import PENDING_STATES

# `destination` is free text -- it may name several files, or a non-path sink such as
# "learning:candidate:lc_...". Extract only things shaped like a tracked repo path. The
# boundaries deliberately include slash and dot: otherwise matching restarts inside `../foo.py`
# or strips the leading dot from `.github/agents/foo.md`, turning both into a different path.
# A slash is optional because top-level manifests such as `plugin.json` are valid destinations.
PATH_PATTERN = re.compile(
    r"(?<![\w./-])([\w.-]+(?:/[\w.-]+)*\.\w+)(?![\w./-])"
)


class GitError(RuntimeError):
    """A git command failed. Never swallowed: an empty log and a broken repository look
    identical to the caller, and conflating them turns `--fail-on-drift` into a false green."""


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed in {root}: {result.stderr.strip()}")
    return result.stdout.strip()


def candidate_paths(destination: str, root: Path) -> list[str]:
    """Paths named by a destination that git can report history for.

    A path missing from the working tree is not necessarily uninteresting: deleting or
    renaming a destination *is* a destination change, and dropping it here would report
    the deletion as a clean ledger. Only a path git has never tracked is discarded."""
    named = dict.fromkeys(PATH_PATTERN.findall(destination or ""))
    kept = []
    for p in named:
        # The regex admits dot-prefixed names such as `.github`, but `.` and `..` are path
        # operators rather than repository names. Reject them before joining to the root so
        # free-text evidence can never make this read history outside the repository.
        if any(part in {".", ".."} for part in PurePosixPath(p).parts):
            continue
        if (root / p).exists() or git(root, "log", "-1", "--format=%h", "--", p):
            kept.append(p)
    return kept


def last_activity(record: dict) -> str:
    """The latest ledger activity timestamp, used for human-readable reporting."""
    stamps = [record.get("created_at"), record.get("updated_at")]
    for field in ("transition_history", "review_history"):
        for entry in record.get(field) or []:
            stamps.append(entry.get("at") or entry.get("timestamp"))
    valid_stamps = [stamp for stamp in stamps if stamp]
    return max(valid_stamps, default="")


def candidate_revision(root: Path, path: Path) -> str:
    """The first-parent commit that integrated the candidate's current state."""
    relative = path.relative_to(root).as_posix()
    return git(root, "log", "--first-parent", "-1", "--format=%H", "--", relative)


def audit(root: Path, *, include_drift: bool = True) -> tuple[list[dict], list[dict]]:
    """Return destination drift and pending intake after one candidate scan."""
    drift_findings = []
    unwatched_findings = []
    for path in sorted((root / "learning" / "candidates").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("promotion_state") not in PENDING_STATES:
            continue
        since = last_activity(record)
        destination = record.get("destination") or ""
        paths = candidate_paths(destination, root)
        if not paths:
            unwatched_findings.append({
                "candidate_id": record["candidate_id"],
                "promotion_state": record["promotion_state"],
                "since": since,
                "destination": destination or None,
            })
            continue
        if not include_drift or not since:
            continue
        baseline = candidate_revision(root, path)
        if not baseline:
            # An uncommitted candidate has no durable graph point from which later changes can
            # be measured. Treat it as local work-in-progress rather than inventing a baseline.
            continue
        commits = []
        # One commit touching several destination paths is one change, not several: count
        # distinct SHAs so the report cannot imply more independent activity than happened.
        shas = set()
        for target in paths:
            # Reachability is the contract: a repair authored or backdated before the candidate
            # can still become reachable afterward through a merge. A timestamp filter silently
            # misses that case, while the candidate-state revision gives Git an exact graph range.
            log = git(root, "log", f"{baseline}..HEAD", "--full-history",
                      "--format=%h %ad %s", "--date=short", "--", target)
            for line in log.splitlines():
                commits.append({"path": target, "commit": line})
                shas.add(line.split(" ", 1)[0])
        if commits:
            drift_findings.append({
                "candidate_id": record["candidate_id"],
                "promotion_state": record["promotion_state"],
                "since": since,
                "destination_paths": paths,
                "commits": commits[:5],
                "commit_count": len(shas),
            })
    return drift_findings, unwatched_findings


def inspect(root: Path) -> list[dict]:
    """Destination-drift findings retained for callers of the original report API."""
    return audit(root)[0]


def unwatched(root: Path) -> list[dict]:
    """Pending candidates the destination watch cannot see."""
    return audit(root, include_drift=False)[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--fail-on-drift", action="store_true",
                        help="exit 1 when a pending candidate changed after its ledger state")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument("--annotate", action="store_true",
                        help="also emit GitHub Actions ::warning:: lines, so a drifted "
                             "candidate is visible on the pull request rather than only in a log")
    args = parser.parse_args(argv)

    if not (args.root / "learning" / "candidates").is_dir():
        print(f"no learning/candidates under {args.root}", file=sys.stderr)
        return 2

    try:
        findings, intake = audit(args.root)
    except GitError as exc:
        # A git failure is not "no drift" -- reporting OK here would hand a caller asking
        # for a hard gate a green run over a repository nobody could read.
        print(f"ledger_drift: {exc}", file=sys.stderr)
        return 2

    if args.json:
        # An object, not the old bare list: the shape changed while it still had no consumer,
        # which was the cheap moment -- leaving JSON blind to unwatched intake would let the
        # text report know more than the machine-readable one.
        print(json.dumps({"drift": findings, "unwatched": intake}, indent=2))
    elif not findings:
        print("OK - no pending candidate's destination changed after its ledger state.")
    else:
        print(
            f"{len(findings)} pending candidate(s) whose destination changed "
            "after ledger activity."
        )
        print("Each may need a `learning_ledger.py transition`, or a note that the change was")
        print("unrelated. This is a prompt to look, not a defect.\n")
        for finding in findings:
            print(f"  {finding['candidate_id'][:11]}  [{finding['promotion_state']}]"
                  f"  since {finding['since'][:10]}  ({finding['commit_count']} commit(s))")
            for entry in finding["commits"]:
                print(f"      {entry['path']}: {entry['commit'][:96]}")
            print()

    if intake and not args.json:
        print(f"\n{len(intake)} pending candidate(s) the destination watch cannot see"
              " (no tracked destination path).")
        print("A quarantined record here is untriaged intake: nothing else prompts its triage,")
        print("so it ages invisibly until someone asks.\n")
        for entry in intake:
            destination = entry["destination"] or "(none - untriaged)"
            print(f"  {entry['candidate_id'][:11]}  [{entry['promotion_state']}]"
                  f"  since {entry['since'][:10]}  destination: {destination}")

    if args.annotate and not args.json:
        # Annotations are human/CI log furniture: after a JSON document they leave
        # json.loads() with extra data, so machine-readable mode stays machine-readable.
        for finding in findings:
            paths = ", ".join(finding["destination_paths"])
            print(f"::warning file={finding['destination_paths'][0]}::"
                  f"Learning candidate {finding['candidate_id'][:11]} is "
                  f"{finding['promotion_state']} but its destination ({paths}) has "
                  f"{finding['commit_count']} commit(s) since {finding['since'][:10]}. "
                  f"If the repair landed, run learning_ledger.py transition; "
                  f"if unrelated, no action.")
        if intake:
            # One aggregate line, not one per record: a backlog is a single fact about the
            # ledger, and fifteen identical warnings would bury the drift findings this job
            # exists to surface.
            ids = ", ".join(entry["candidate_id"][:11] for entry in intake)
            print(f"::warning::{len(intake)} learning candidate(s) pending with no watchable "
                  f"destination -- untriaged intake ages invisibly: {ids}. Triage with "
                  f"learning_ledger.py transition, or record why each stays pending.")

    return 1 if (findings and args.fail_on_drift) else 0


if __name__ == "__main__":
    raise SystemExit(main())
