"""Tests for scripts/ledger_drift.py.

The regression these guard is the one that motivated the script: seven candidates sat at
`proposed` while their destinations kept receiving commits, and nothing observed it.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ledger_drift", REPO / "scripts" / "ledger_drift.py")
ledger_drift = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ledger_drift)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


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
    _git(root, "commit", "-q", "-m", "seed")

    # A commit to the destination dated after the candidate was filed.
    target.write_text("repaired\n")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@example.com", "-c", "user.name=t",
         "commit", "-q", "-m", "repair the thing", "--date=2026-08-03T00:00:00")


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

    def test_clean_ledger_reports_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _repo_with_candidate(root, state="proposed", destination="scripts/thing.py",
                                 since="2027-01-01T00:00:00Z")  # filed after the commit
            self.assertEqual(ledger_drift.inspect(root), [])
            self.assertEqual(ledger_drift.main(["--root", str(root)]), 0)


if __name__ == "__main__":
    unittest.main()
