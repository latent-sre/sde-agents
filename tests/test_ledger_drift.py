"""Tests for scripts/ledger_drift.py.

The regression these tests guard against is the one that motivated the script: seven candidates sat at
`proposed` while their destinations kept receiving commits, and nothing observed it.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ledger_drift", REPO / "scripts" / "ledger_drift.py")
ledger_drift = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ledger_drift)


def _git(root: Path, *args: str, date: str | None = None) -> None:
    # Both dates are pinned: `git log --since` filters on the *committer* date, so a fixture
    # that sets only the author date drifts with the wall clock and the tests rot silently.
    env = dict(os.environ)
    if date is not None:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)


def _repo_with_candidate(root: Path, *, state: str, destination: str, since: str) -> None:
    """A minimal repo holding one candidate whose destination has a later commit."""
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")

    target = root / "scripts" / "thing.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("original\n")
    candidates = root / "learning" / "candidates"
    candidates.mkdir(parents=True, exist_ok=True)
    (candidates / "lc_test.json").write_text(json.dumps({
        "candidate_id": "lc_test0000000000000000000000000",
        "promotion_state": state,
        "destination": destination,
        "created_at": since,
        "updated_at": since,
        "transition_history": [],
    }))
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed", date="2026-07-01T00:00:00+0000")

    # A commit to the destination dated after the candidate was filed.
    target.write_text("repaired\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "repair the thing", date="2026-08-03T00:00:00+0000")


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
            _repo_with_candidate(root, state="proposed", destination="scripts/thing.py",
                                 since="2026-08-01T00:00:00Z")
            # Rename, not delete: git marks its object files read-only, and on Windows
            # shutil.rmtree refuses to delete them (WinError 5). Breaking the fixture only
            # needs git to stop finding a repository here; the temporary directory's own
            # cleanup already handles the read-only objects.
            (root / ".git").rename(root / ".git-broken")
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

    def test_clean_ledger_reports_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed", destination="scripts/thing.py",
                                 since="2027-01-01T00:00:00Z")  # filed after the commit
            self.assertEqual(ledger_drift.inspect(root), [])
            self.assertEqual(ledger_drift.main(["--root", str(root)]), 0)


if __name__ == "__main__":
    unittest.main()
