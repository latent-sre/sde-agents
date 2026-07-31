from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import evidence_envelope, run_state


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


class RunStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        self.clock = Clock()
        self.store = run_state.StateStore(
            self.base / "control" / "state.sqlite3",
            self.workspace,
            now=self.clock.now,
        )
        self.store.initialize()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _start(self, run_id: str = "run-1", task_id: str = "task-1") -> None:
        self.store.start_run(
            run_id,
            input_revision="abc123",
            contract_digest="a" * 64,
        )
        self.store.add_task(
            run_id,
            task_id,
            "verify the acceptance criteria",
            expected_run_version=0,
        )

    def _evidence(
        self,
        *,
        run_id: str = "run-1",
        task_id: str = "task-1",
        attempt_id: str = "attempt-1",
        status: str = "pass",
        target_revision: str = "abc123",
    ) -> dict[str, object]:
        return evidence_envelope.new_envelope(
            producer="test",
            role="verification-engineer",
            target_root=str(self.workspace),
            target_revision=target_revision,
            criterion="acceptance criteria",
            status=status,
            started_at=self.clock.now(),
            ended_at=self.clock.now(),
            command_argv=["python", "-m", "unittest"],
            exit_code=0 if status == "pass" else 1,
            run_id=run_id,
            task_id=task_id,
            attempt_id=attempt_id,
            isolation={"network": "none"},
        )

    def test_database_inside_worker_workspace_is_rejected(self) -> None:
        with self.assertRaisesRegex(run_state.StateError, "outside the worker workspace"):
            run_state.StateStore(self.workspace / "state.sqlite3", self.workspace)

    def test_complete_lifecycle_binds_evidence_and_versions(self) -> None:
        self._start()
        claim = self.store.claim_task(
            "task-1",
            "attempt-1",
            worker_id="worker-1",
            lease_seconds=60,
            expected_task_version=0,
            input_revision="abc123",
        )
        attempt = self.store.complete_attempt(
            "attempt-1",
            lease_token=claim["lease_token"],
            verdict="completed",
            output_revision="abc123",
            evidence=[self._evidence()],
            expected_attempt_version=0,
        )
        self.assertEqual("completed", attempt["status"])
        self.assertNotIn("lease_token_hash", attempt)
        run = self.store.complete_run("run-1", expected_run_version=1)
        self.assertEqual("complete", run["status"])
        linked = self.store.status(attempt_id="attempt-1")["evidence"]
        self.assertEqual(1, len(linked))
        self.assertRegex(linked[0]["envelope_digest"], r"^[0-9a-f]{64}$")

    def test_stale_controller_version_fails_without_overwrite(self) -> None:
        self._start()
        with self.assertRaisesRegex(run_state.StaleVersionError, "stale run version"):
            self.store.add_task(
                "run-1",
                "task-2",
                "second task",
                expected_run_version=0,
            )
        status = self.store.status(run_id="run-1")
        self.assertEqual(["task-1"], [task["task_id"] for task in status["tasks"]])

    def test_expired_lease_is_reaped_before_a_second_attempt(self) -> None:
        self._start()
        first = self.store.claim_task(
            "task-1",
            "attempt-1",
            worker_id="worker-1",
            lease_seconds=10,
            expected_task_version=0,
            input_revision="abc123",
        )
        self.clock.advance(11)
        with self.assertRaisesRegex(run_state.LeaseError, "expired"):
            self.store.complete_attempt(
                "attempt-1",
                lease_token=first["lease_token"],
                verdict="failed",
                output_revision="abc123",
                evidence=[self._evidence(status="fail")],
                expected_attempt_version=0,
            )
        second = self.store.claim_task(
            "task-1",
            "attempt-2",
            worker_id="worker-2",
            lease_seconds=30,
            expected_task_version=1,
            input_revision="abc123",
        )
        self.assertEqual(2, second["attempt_number"])
        attempts = self.store.status(task_id="task-1")["attempts"]
        self.assertEqual(["expired", "active"], [item["status"] for item in attempts])

    def test_cancelled_run_invalidates_active_attempt(self) -> None:
        self._start()
        claim = self.store.claim_task(
            "task-1",
            "attempt-1",
            worker_id="worker-1",
            lease_seconds=60,
            expected_task_version=0,
            input_revision="abc123",
        )
        self.store.cancel_run(
            "run-1",
            reason="operator cancelled the run",
            expected_run_version=1,
        )
        with self.assertRaisesRegex(run_state.StaleVersionError, "stale attempt version"):
            self.store.complete_attempt(
                "attempt-1",
                lease_token=claim["lease_token"],
                verdict="completed",
                output_revision="abc123",
                evidence=[self._evidence()],
                expected_attempt_version=0,
            )
        with self.assertRaisesRegex(run_state.LeaseError, "status 'cancelled'"):
            self.store.complete_attempt(
                "attempt-1",
                lease_token=claim["lease_token"],
                verdict="completed",
                output_revision="abc123",
                evidence=[self._evidence()],
                expected_attempt_version=1,
            )
        self.assertEqual(
            "cancelled",
            self.store.status(attempt_id="attempt-1")["attempt"]["status"],
        )

    def test_superseded_run_propagates_and_cannot_complete_afterward(self) -> None:
        self._start()
        claim = self.store.claim_task(
            "task-1",
            "attempt-1",
            worker_id="worker-1",
            lease_seconds=60,
            expected_task_version=0,
            input_revision="abc123",
        )
        superseded = self.store.supersede_run(
            "run-1",
            superseded_by="run-2",
            reason="newer immutable input replaced this run",
            expected_run_version=1,
        )
        self.assertEqual("superseded", superseded["status"])
        self.assertEqual("run-2", superseded["superseded_by"])
        self.assertEqual(
            "superseded",
            self.store.status(task_id="task-1")["task"]["status"],
        )
        self.assertEqual(
            "superseded",
            self.store.status(attempt_id="attempt-1")["attempt"]["status"],
        )
        with self.assertRaisesRegex(run_state.LeaseError, "status 'superseded'"):
            self.store.complete_attempt(
                "attempt-1",
                lease_token=claim["lease_token"],
                verdict="completed",
                output_revision="abc123",
                evidence=[self._evidence()],
                expected_attempt_version=1,
            )
        with self.assertRaisesRegex(run_state.StateError, "status 'superseded'"):
            self.store.complete_run("run-1", expected_run_version=2)

    def test_evidence_context_must_match_attempt(self) -> None:
        self._start()
        claim = self.store.claim_task(
            "task-1",
            "attempt-1",
            worker_id="worker-1",
            lease_seconds=60,
            expected_task_version=0,
            input_revision="abc123",
        )
        with self.assertRaisesRegex(run_state.StateError, "context does not match"):
            self.store.complete_attempt(
                "attempt-1",
                lease_token=claim["lease_token"],
                verdict="completed",
                output_revision="abc123",
                evidence=[self._evidence(attempt_id="different-attempt")],
                expected_attempt_version=0,
            )
        self.assertEqual(
            "active",
            self.store.status(attempt_id="attempt-1")["attempt"]["status"],
        )

    def test_completion_without_typed_evidence_is_rejected(self) -> None:
        self._start()
        claim = self.store.claim_task(
            "task-1",
            "attempt-1",
            worker_id="worker-1",
            lease_seconds=60,
            expected_task_version=0,
            input_revision="abc123",
        )
        with self.assertRaisesRegex(run_state.StateError, "typed evidence"):
            self.store.complete_attempt(
                "attempt-1",
                lease_token=claim["lease_token"],
                verdict="completed",
                output_revision="abc123",
                evidence=[],
                expected_attempt_version=0,
            )

    def test_evidence_target_revision_must_match_attempt_output(self) -> None:
        self._start()
        claim = self.store.claim_task(
            "task-1",
            "attempt-1",
            worker_id="worker-1",
            lease_seconds=60,
            expected_task_version=0,
            input_revision="abc123",
        )
        with self.assertRaisesRegex(run_state.StateError, "target revision"):
            self.store.complete_attempt(
                "attempt-1",
                lease_token=claim["lease_token"],
                verdict="completed",
                output_revision="def456",
                evidence=[self._evidence(target_revision="abc123")],
                expected_attempt_version=0,
            )

    def test_completed_attempt_requires_pass_evidence(self) -> None:
        self._start()
        claim = self.store.claim_task(
            "task-1",
            "attempt-1",
            worker_id="worker-1",
            lease_seconds=60,
            expected_task_version=0,
            input_revision="abc123",
        )
        with self.assertRaisesRegex(run_state.StateError, "requires pass evidence"):
            self.store.complete_attempt(
                "attempt-1",
                lease_token=claim["lease_token"],
                verdict="completed",
                output_revision="abc123",
                evidence=[self._evidence(status="inconclusive")],
                expected_attempt_version=0,
            )

    def test_event_log_is_append_only_at_database_layer(self) -> None:
        self._start()
        connection = sqlite3.connect(self.store.database)
        try:
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                connection.execute("DELETE FROM events")
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
