"""Tests for the bounded advisory contract in scripts/ledger_drift.py.

Only destination activity integrated after the current ledger state is drift. Earlier or
co-committed changes are the baseline, not evidence this history-only checker can interpret.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import ledger_drift
from tests.support import git as _git


def _repo_with_candidate(
    root: Path,
    *,
    state: str,
    destination: str,
    since: str,
    candidate_after_repair: bool = False,
) -> None:
    """A minimal repo holding one candidate and one destination repair."""
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")

    target = root / "scripts" / "thing.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("original\n")
    candidates = root / "learning" / "candidates"
    candidates.mkdir(parents=True, exist_ok=True)
    candidate = candidates / "lc_test.json"
    record = {
        "candidate_id": "lc_test0000000000000000000000000",
        "promotion_state": state,
        "destination": destination,
        "created_at": since,
        "updated_at": since,
        "transition_history": [],
    }
    if not candidate_after_repair:
        candidate.write_text(json.dumps(record))
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed", date="2026-07-01T00:00:00+0000")

    # A commit to the destination dated after the candidate was filed.
    target.write_text("repaired\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "repair the thing", date="2026-08-03T00:00:00+0000")

    if candidate_after_repair:
        candidate.write_text(json.dumps(record))
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "file candidate after repair",
             date=since.replace("Z", "+0000"))


class LedgerDriftTests(unittest.TestCase):
    def test_pending_candidate_with_changed_destination_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed", destination="scripts/thing.py",
                                 since="2026-08-01T00:00:00Z")
            findings = ledger_drift.inspect(root)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["promotion_state"], "proposed")
            self.assertIn("scripts/thing.py", findings[0]["destination_paths"])

    def test_backdated_repair_merged_after_candidate_is_reported(self) -> None:
        """Reachability, not a commit's timestamp, determines whether a change is new."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git(root, "init", "-q", "-b", "main")
            _git(root, "config", "user.email", "t@example.com")
            _git(root, "config", "user.name", "t")
            target = root / "scripts" / "thing.py"
            target.parent.mkdir(parents=True)
            target.write_text("original\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "seed",
                 date="2026-07-01T00:00:00+0000")

            _git(root, "switch", "-q", "-c", "repair")
            target.write_text("repaired\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "repair before filing",
                 date="2026-07-15T00:00:00+0000")

            _git(root, "switch", "-q", "main")
            candidates = root / "learning" / "candidates"
            candidates.mkdir(parents=True)
            (candidates / "lc_test.json").write_text(json.dumps({
                "candidate_id": "lc_test0000000000000000000000000",
                "promotion_state": "proposed",
                "destination": "scripts/thing.py",
                "created_at": "2026-08-01T00:00:00Z",
                "updated_at": "2026-08-01T00:00:00Z",
                "transition_history": [],
            }))
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "file candidate",
                 date="2026-08-01T00:00:00+0000")

            # The merge happens after filing in graph order, but imported/backdated history can
            # carry an older committer date. A --since query silently misses this repair.
            _git(root, "merge", "-q", "--no-ff", "repair", "-m", "merge repair",
                 date="2026-07-20T00:00:00+0000")

            findings = ledger_drift.inspect(root)

            self.assertEqual(1, len(findings))
            self.assertTrue(
                any("merge repair" in entry["commit"] for entry in findings[0]["commits"]),
                findings,
            )

    def test_mainline_change_before_candidate_merge_is_not_drift(self) -> None:
        """A side-branch author commit is not the state integration point."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git(root, "init", "-q", "-b", "main")
            _git(root, "config", "user.email", "t@example.com")
            _git(root, "config", "user.name", "t")
            target = root / "scripts" / "thing.py"
            target.parent.mkdir(parents=True)
            target.write_text("original\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "seed",
                 date="2026-07-01T00:00:00+0000")

            _git(root, "switch", "-q", "-c", "candidate")
            candidates = root / "learning" / "candidates"
            candidates.mkdir(parents=True)
            (candidates / "lc_test.json").write_text(json.dumps({
                "candidate_id": "lc_test0000000000000000000000000",
                "promotion_state": "proposed",
                "destination": "scripts/thing.py",
                "created_at": "2026-08-02T00:00:00Z",
                "updated_at": "2026-08-02T00:00:00Z",
                "transition_history": [],
            }))
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "author candidate",
                 date="2026-08-02T00:00:00+0000")

            _git(root, "switch", "-q", "main")
            target.write_text("mainline repair\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "mainline repair before candidate merge",
                 date="2026-08-03T00:00:00+0000")
            _git(root, "merge", "-q", "--no-ff", "candidate", "-m", "merge candidate",
                 date="2026-08-04T00:00:00+0000")

            self.assertEqual(ledger_drift.inspect(root), [])

    def test_closed_candidate_is_not_reported(self) -> None:
        """A promoted record naming a file under ordinary maintenance is not drift."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="promoted", destination="scripts/thing.py",
                                 since="2026-08-01T00:00:00Z")
            self.assertEqual(ledger_drift.inspect(root), [])

    def test_non_path_destination_is_ignored(self) -> None:
        """`destination` is free text and may name a sink that is not a file."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed",
                                 destination="learning:candidate:lc_other",
                                 since="2026-08-01T00:00:00Z")
            self.assertEqual(ledger_drift.inspect(root), [])

    def test_destination_naming_a_missing_file_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed", destination="scripts/absent.py",
                                 since="2026-08-01T00:00:00Z")
            self.assertEqual(ledger_drift.inspect(root), [])

    def test_dot_prefixed_destination_keeps_its_repo_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destinations = [
                ".github/agents/reviewer.md",
                ".codex/agents/reviewer.toml",
            ]
            _repo_with_candidate(root, state="proposed", destination=" and ".join(destinations),
                                 since="2026-08-01T00:00:00Z")
            for destination in destinations:
                target = root / destination
                target.parent.mkdir(parents=True)
                target.write_text("reviewer\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "add generated reviewers",
                 date="2026-08-04T00:00:00+0000")

            findings = ledger_drift.inspect(root)

            self.assertEqual(destinations, findings[0]["destination_paths"])

    def test_top_level_destination_is_inspected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            destination = "plugin.json"
            _repo_with_candidate(root, state="proposed", destination=destination,
                                 since="2026-08-01T00:00:00Z")
            (root / destination).write_text("{}\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "add manifest",
                 date="2026-08-04T00:00:00+0000")

            findings = ledger_drift.inspect(root)

            self.assertEqual([destination], findings[0]["destination_paths"])

    def test_parent_traversal_is_not_reinterpreted_as_a_repo_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed", destination="../scripts/thing.py",
                                 since="2026-08-01T00:00:00Z")

            self.assertEqual(ledger_drift.inspect(root), [])

    def test_review_after_destination_change_advances_the_activity_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed", destination="scripts/thing.py",
                                 since="2026-08-01T00:00:00Z")
            candidate = root / "learning" / "candidates" / "lc_test.json"
            record = json.loads(candidate.read_text())
            record["transition_history"] = [{"at": "2026-08-01T12:00:00Z"}]
            record["review_history"] = [{"at": "2026-08-04T00:00:00Z"}]
            record["updated_at"] = "2026-08-02T00:00:00Z"
            candidate.write_text(json.dumps(record))
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "review candidate",
                 date="2026-08-04T00:00:00+0000")

            (root / "scripts" / "thing.py").write_text("repaired again\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "change after review",
                 date="2026-08-05T00:00:00+0000")

            findings = ledger_drift.inspect(root)

            self.assertEqual(findings[0]["since"], "2026-08-04T00:00:00Z")
            self.assertIn("change after review", findings[0]["commits"][0]["commit"])

    def test_exit_code_is_advisory_unless_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed", destination="scripts/thing.py",
                                 since="2026-08-01T00:00:00Z")
            self.assertEqual(ledger_drift.main(["--root", str(root)]), 0)
            self.assertEqual(ledger_drift.main(["--root", str(root), "--fail-on-drift"]), 1)

    def test_deleted_destination_is_still_inspected(self) -> None:
        """Deleting a destination is itself a destination change, not a clean ledger."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed", destination="scripts/thing.py",
                                 since="2026-08-01T00:00:00Z")
            (root / "scripts" / "thing.py").unlink()
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "remove the thing",
                 date="2026-08-04T00:00:00+0000")
            findings = ledger_drift.inspect(root)
            self.assertEqual(len(findings), 1)
            self.assertIn("scripts/thing.py", findings[0]["destination_paths"])

    def test_git_failure_is_not_reported_as_clean(self) -> None:
        """A broken repository must not read as OK, least of all under --fail-on-drift."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "scripts" / "thing.py"
            target.parent.mkdir(parents=True)
            target.write_text("repaired\n")
            candidates = root / "learning" / "candidates"
            candidates.mkdir(parents=True)
            (candidates / "lc_test.json").write_text(json.dumps({
                "candidate_id": "lc_test0000000000000000000000000",
                "promotion_state": "proposed",
                "destination": "scripts/thing.py",
                "created_at": "2026-08-01T00:00:00Z",
                "updated_at": "2026-08-01T00:00:00Z",
                "transition_history": [],
            }))
            # The fixture is deliberately not a Git repository. This reaches the GitError path
            # without deleting platform-managed metadata or relying on cleanup semantics.
            with self.assertRaises(ledger_drift.GitError):
                ledger_drift.inspect(root)
            self.assertEqual(ledger_drift.main(["--root", str(root), "--fail-on-drift"]), 2)

    def test_one_commit_touching_two_destinations_counts_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed",
                                 destination="scripts/thing.py and scripts/other.py",
                                 since="2026-08-01T00:00:00Z")
            (root / "scripts" / "other.py").write_text("also repaired\n")
            (root / "scripts" / "thing.py").write_text("repaired again\n")
            _git(root, "add", "-A")
            _git(root, "commit", "-q", "-m", "repair both", date="2026-08-05T00:00:00+0000")
            findings = ledger_drift.inspect(root)
            self.assertEqual(len(findings), 1)
            # Three log lines (two paths in the shared commit, one earlier), two commits.
            self.assertEqual(findings[0]["commit_count"], 2)

    def test_destination_change_before_candidate_is_not_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed", destination="scripts/thing.py",
                                 since="2027-01-01T00:00:00Z", candidate_after_repair=True)
            self.assertEqual(ledger_drift.inspect(root), [])
            self.assertEqual(ledger_drift.main(["--root", str(root)]), 0)


if __name__ == "__main__":
    unittest.main()
