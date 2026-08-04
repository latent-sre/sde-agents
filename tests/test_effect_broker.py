from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import effect_broker, evidence_envelope


class EffectBrokerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.workspace = self.base / "workspace"
        self.control = self.base / "control"
        self.workspace.mkdir()
        self.control.mkdir()
        self.executable = self.control / "approved-helper.exe"
        self.executable.write_bytes(b"fixture executable bytes\n")
        self.key = b"k" * 32
        self.start = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _request(self) -> dict[str, object]:
        return effect_broker.create_request(
            action="publish-artifact",
            target="staging/release-1",
            argv=[str(self.executable), "--artifact", "release-1"],
            cwd=self.workspace,
            blast_radius="one staging artifact",
            rollback="delete staging/release-1 by its immutable identifier",
            expires_at=self.start + timedelta(minutes=5),
            timeout_seconds=30,
            environment={"MODE": "staging"},
            run_id="run-1",
            task_id="task-1",
            attempt_id="attempt-1",
            now=lambda: self.start,
        )

    def _approval(self, request: dict[str, object]) -> dict[str, object]:
        return effect_broker.approve_request(
            request,
            key=self.key,
            approver="operator@example",
            now=lambda: self.start + timedelta(seconds=1),
        )

    def _ledger(self) -> effect_broker.ReplayLedger:
        return effect_broker.ReplayLedger(
            self.control / "ledger.sqlite3",
            self.workspace,
        )

    def test_exact_approved_effect_executes_once_and_emits_evidence(self) -> None:
        request = self._request()
        approval = self._approval(request)
        calls: list[tuple[tuple[str, ...], Path, dict[str, str], int]] = []

        def runner(argv, cwd, environment, timeout):
            calls.append((tuple(argv), cwd, dict(environment), timeout))
            return effect_broker.ProcessResult(0, b"published\n", b"")

        times = iter(
            [
                self.start + timedelta(seconds=2),
                self.start + timedelta(seconds=3),
            ]
        )
        envelope = effect_broker.execute_approved(
            request,
            approval,
            key=self.key,
            ledger=self._ledger(),
            runner=runner,
            now=lambda: next(times),
        )
        evidence_envelope.validate_envelope(envelope)
        self.assertEqual("pass", envelope["status"])
        self.assertEqual(1, len(calls))
        self.assertEqual(tuple(request["argv"]), calls[0][0])
        self.assertEqual({"MODE": "staging"}, calls[0][2])
        self.assertEqual("direct-argv", envelope["environment"]["execution"])

    def test_request_tampering_fails_before_runner_or_ledger_consumption(self) -> None:
        request = self._request()
        approval = self._approval(request)
        tampered = copy.deepcopy(request)
        tampered["argv"].append("--extra-effect")
        called = False

        def runner(argv, cwd, environment, timeout):
            nonlocal called
            called = True
            return effect_broker.ProcessResult(0, b"", b"")

        with self.assertRaisesRegex(effect_broker.ApprovalError, "digest"):
            effect_broker.execute_approved(
                tampered,
                approval,
                key=self.key,
                ledger=self._ledger(),
                runner=runner,
                now=lambda: self.start + timedelta(seconds=2),
            )
        self.assertFalse(called)

    def test_expired_request_cannot_be_approved_or_executed(self) -> None:
        request = self._request()
        with self.assertRaisesRegex(effect_broker.ApprovalError, "expired"):
            effect_broker.approve_request(
                request,
                key=self.key,
                approver="operator@example",
                now=lambda: self.start + timedelta(minutes=6),
            )
        approval = self._approval(request)
        with self.assertRaisesRegex(effect_broker.ApprovalError, "expired"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=self._ledger(),
                now=lambda: self.start + timedelta(minutes=6),
            )

    def test_replay_is_rejected_before_second_subprocess(self) -> None:
        request = self._request()
        approval = self._approval(request)
        calls = 0

        def runner(argv, cwd, environment, timeout):
            nonlocal calls
            calls += 1
            return effect_broker.ProcessResult(0, b"", b"")

        times = iter(
            [
                self.start + timedelta(seconds=2),
                self.start + timedelta(seconds=3),
            ]
        )
        effect_broker.execute_approved(
            request,
            approval,
            key=self.key,
            ledger=self._ledger(),
            runner=runner,
            now=lambda: next(times),
        )
        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=self._ledger(),
                runner=runner,
                now=lambda: self.start + timedelta(seconds=4),
            )
        self.assertEqual(1, calls)

    def test_executable_drift_invalidates_approval(self) -> None:
        request = self._request()
        approval = self._approval(request)
        self.executable.write_bytes(b"different executable bytes\n")
        with self.assertRaisesRegex(effect_broker.ApprovalError, "bytes changed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=self._ledger(),
                now=lambda: self.start + timedelta(seconds=2),
            )

    def test_key_and_replay_ledger_must_be_outside_workspace(self) -> None:
        key = self.workspace / "key.bin"
        key.write_bytes(self.key)
        with self.assertRaisesRegex(effect_broker.BrokerError, "outside"):
            effect_broker._read_key(key, self.workspace)
        with self.assertRaisesRegex(effect_broker.BrokerError, "outside"):
            effect_broker.ReplayLedger(self.workspace / "ledger.sqlite3", self.workspace)

    def test_concurrent_consumers_get_exactly_one_execution(self) -> None:
        request = self._request()
        approval = self._approval(request)
        calls = 0
        calls_lock = threading.Lock()

        def runner(argv, cwd, environment, timeout):
            nonlocal calls
            with calls_lock:
                calls += 1
            return effect_broker.ProcessResult(0, b"", b"")

        def consume(index: int):
            times = iter(
                [
                    self.start + timedelta(seconds=2 + index),
                    self.start + timedelta(seconds=3 + index),
                ]
            )
            return effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=self._ledger(),
                runner=runner,
                now=lambda: next(times),
            )

        outcomes: list[object] = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(consume, index) for index in range(2)]
            for future in futures:
                try:
                    outcomes.append(future.result())
                except effect_broker.ReplayError as exc:
                    outcomes.append(exc)
        self.assertEqual(1, sum(isinstance(item, dict) for item in outcomes))
        self.assertEqual(1, sum(isinstance(item, effect_broker.ReplayError) for item in outcomes))
        self.assertEqual(1, calls)

    def test_shell_executables_and_secret_environment_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(effect_broker.BrokerError, "shell interpreters"):
            effect_broker._validate_argv([str(self.control / "pwsh.exe"), "-Command", "Write-Host x"])
        with self.assertRaisesRegex(
            evidence_envelope.EnvelopeValidationError,
            "credentials",
        ):
            effect_broker._validate_environment({"API_TOKEN": "secret"})

    def _timestamp(self, value: datetime) -> str:
        return effect_broker._format_timestamp(value)

    def _foreign_reservation(
        self,
        request: dict[str, object],
        approval: dict[str, object],
        *,
        reserved_at: datetime,
    ) -> effect_broker.ReplayLedger:
        """Leave a `reserved` row as a broker process that died mid-flight would."""
        ledger = self._ledger()
        ledger.reserve(
            nonce=request["nonce"],
            request_id=request["request_id"],
            request_digest=request["request_digest"],
            approval_id=approval["approval_id"],
            action=request["action"],
            target=request["target"],
            argv=request["argv"],
            reserved_at=self._timestamp(reserved_at),
        )
        # The reserving process is gone, so its pid no longer matches any live sweeper.
        with closing(sqlite3.connect(ledger.path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE consumptions SET reserver_pid = -1 WHERE nonce = ?",
                    (request["nonce"],),
                )
        return ledger

    def test_crash_leftover_reservation_is_promoted_and_replay_blocked(self) -> None:
        crashed_request = self._request()
        crashed_approval = self._approval(crashed_request)
        ledger = self._foreign_reservation(
            crashed_request,
            crashed_approval,
            reserved_at=self.start + timedelta(seconds=2),
        )
        other_request = self._request()
        other_approval = self._approval(other_request)
        times = iter(
            [
                self.start + timedelta(seconds=10),
                self.start + timedelta(seconds=11),
            ]
        )
        envelope = effect_broker.execute_approved(
            other_request,
            other_approval,
            key=self.key,
            ledger=ledger,
            runner=lambda *args: effect_broker.ProcessResult(0, b"", b""),
            now=lambda: next(times),
        )
        self.assertEqual("pass", envelope["status"])
        self.assertTrue(
            any("crash-leftover" in item for item in envelope["limitations"]),
            envelope["limitations"],
        )
        rows = ledger.unresolved()
        self.assertEqual([crashed_request["request_id"]], [row["request_id"] for row in rows])
        row = rows[0]
        self.assertEqual("unknown", row["status"])
        self.assertEqual("stale-reservation", row["unknown_origin"])
        self.assertEqual("publish-artifact", row["action"])
        self.assertEqual("staging/release-1", row["target"])
        self.assertEqual(list(crashed_request["argv"]), row["argv"])
        self.assertIsNone(row["finished_at"])
        called = False

        def runner(argv, cwd, environment, timeout):
            nonlocal called
            called = True
            return effect_broker.ProcessResult(0, b"", b"")

        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                crashed_request,
                crashed_approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(minutes=4),
            )
        self.assertFalse(called)

    def test_crash_during_dispatch_marks_unknown_and_blocks_replay(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()
        calls = 0

        def runner(argv, cwd, environment, timeout):
            nonlocal calls
            calls += 1
            raise RuntimeError("broker host died mid-dispatch")

        with self.assertRaisesRegex(RuntimeError, "mid-dispatch"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(seconds=2),
            )
        rows = ledger.unresolved()
        self.assertEqual(1, len(rows))
        self.assertEqual("unknown", rows[0]["status"])
        self.assertEqual("dispatch-exception", rows[0]["unknown_origin"])
        self.assertIsNone(rows[0]["finished_at"])
        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(seconds=3),
            )
        self.assertEqual(1, calls)

    def test_crash_after_dispatch_before_finalization_marks_unknown(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()
        calls = 0

        def runner(argv, cwd, environment, timeout):
            nonlocal calls
            calls += 1
            return effect_broker.ProcessResult(0, b"done\n", b"")

        def failing_finish(**kwargs):
            raise sqlite3.Error("ledger write failed after dispatch")

        ledger.finish = failing_finish  # type: ignore[method-assign]
        times = iter(
            [
                self.start + timedelta(seconds=2),
                self.start + timedelta(seconds=3),
            ]
        )
        with self.assertRaisesRegex(sqlite3.Error, "after dispatch"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: next(times),
            )
        rows = ledger.unresolved()
        self.assertEqual(1, len(rows))
        self.assertEqual("unknown", rows[0]["status"])
        self.assertEqual("finalization-exception", rows[0]["unknown_origin"])
        self.assertIsNone(rows[0]["finished_at"])
        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(seconds=4),
            )
        self.assertEqual(1, calls)

    def test_unknown_resolution_is_recorded_and_stays_terminal(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()

        def runner(argv, cwd, environment, timeout):
            raise RuntimeError("broker host died mid-dispatch")

        with self.assertRaises(RuntimeError):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(seconds=2),
            )
        resolved = ledger.resolve(
            nonce=request["nonce"],
            resolver="operator@example",
            resolution="not-applied",
            resolution_note="staging has no release-1 artifact and its log shows no publish",
            resolved_at=self._timestamp(self.start + timedelta(minutes=3)),
        )
        self.assertEqual("resolved", resolved["status"])
        self.assertEqual("operator@example", resolved["resolver"])
        self.assertEqual("not-applied", resolved["resolution"])
        self.assertEqual(
            "staging has no release-1 artifact and its log shows no publish",
            resolved["resolution_note"],
        )
        self.assertEqual(
            self._timestamp(self.start + timedelta(minutes=3)), resolved["resolved_at"]
        )
        self.assertEqual([], ledger.unresolved())
        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(minutes=4),
            )
        with self.assertRaisesRegex(effect_broker.ReplayError, "no unresolved unknown"):
            ledger.resolve(
                nonce=request["nonce"],
                resolver="operator@example",
                resolution="applied",
                resolution_note="a resolved row must never be re-resolved",
                resolved_at=self._timestamp(self.start + timedelta(minutes=4)),
            )

    def test_resolve_rejects_non_unknown_rows_and_empty_evidence(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()
        times = iter(
            [
                self.start + timedelta(seconds=2),
                self.start + timedelta(seconds=3),
            ]
        )
        effect_broker.execute_approved(
            request,
            approval,
            key=self.key,
            ledger=ledger,
            runner=lambda *args: effect_broker.ProcessResult(0, b"", b""),
            now=lambda: next(times),
        )
        resolved_at = self._timestamp(self.start + timedelta(minutes=4))
        with self.assertRaisesRegex(effect_broker.ReplayError, "no unresolved unknown"):
            ledger.resolve(
                nonce=request["nonce"],
                resolver="operator@example",
                resolution="applied",
                resolution_note="a finalized execution is not a crash outcome",
                resolved_at=resolved_at,
            )
        with self.assertRaisesRegex(effect_broker.BrokerError, "nonce"):
            ledger.resolve(
                nonce="not-a-nonce",
                resolver="operator@example",
                resolution="applied",
                resolution_note="verified",
                resolved_at=resolved_at,
            )
        with self.assertRaisesRegex(effect_broker.BrokerError, "resolution must be one of"):
            ledger.resolve(
                nonce="f" * 64,
                resolver="operator@example",
                resolution="maybe",
                resolution_note="verified",
                resolved_at=resolved_at,
            )
        with self.assertRaisesRegex(effect_broker.BrokerError, "note"):
            ledger.resolve(
                nonce="f" * 64,
                resolver="operator@example",
                resolution="applied",
                resolution_note="  ",
                resolved_at=resolved_at,
            )
        with self.assertRaisesRegex(effect_broker.BrokerError, "resolver"):
            ledger.resolve(
                nonce="f" * 64,
                resolver=" ",
                resolution="applied",
                resolution_note="verified",
                resolved_at=resolved_at,
            )

    def test_reconcile_cli_lists_exact_approved_effect_and_resolves(self) -> None:
        healthy_request = self._request()
        healthy_approval = self._approval(healthy_request)
        ledger = self._ledger()
        times = iter(
            [
                self.start + timedelta(seconds=2),
                self.start + timedelta(seconds=3),
            ]
        )
        effect_broker.execute_approved(
            healthy_request,
            healthy_approval,
            key=self.key,
            ledger=ledger,
            runner=lambda *args: effect_broker.ProcessResult(0, b"", b""),
            now=lambda: next(times),
        )
        crashed_request = self._request()
        crashed_approval = self._approval(crashed_request)
        self._foreign_reservation(
            crashed_request,
            crashed_approval,
            reserved_at=self.start + timedelta(seconds=4),
        )
        listing = io.StringIO()
        with contextlib.redirect_stdout(listing):
            code = effect_broker.main(
                [
                    "reconcile",
                    "--ledger",
                    str(ledger.path),
                    "--workspace-root",
                    str(self.workspace),
                ]
            )
        self.assertEqual(0, code)
        report = json.loads(listing.getvalue())
        self.assertEqual(
            [crashed_request["request_id"]],
            [row["request_id"] for row in report["promoted"]],
        )
        self.assertEqual(1, len(report["unresolved"]))
        row = report["unresolved"][0]
        self.assertEqual("unknown", row["status"])
        self.assertEqual("publish-artifact", row["action"])
        self.assertEqual("staging/release-1", row["target"])
        self.assertEqual(list(crashed_request["argv"]), row["argv"])
        self.assertNotIn(
            healthy_request["request_id"],
            [item["request_id"] for item in report["promoted"] + report["unresolved"]],
        )
        resolution = io.StringIO()
        with contextlib.redirect_stdout(resolution):
            code = effect_broker.main(
                [
                    "resolve",
                    "--ledger",
                    str(ledger.path),
                    "--workspace-root",
                    str(self.workspace),
                    "--nonce",
                    crashed_request["nonce"],
                    "--resolver",
                    "operator@example",
                    "--resolution",
                    "applied",
                    "--note",
                    "release-1 is present in staging with the expected bytes",
                ]
            )
        self.assertEqual(0, code)
        resolved = json.loads(resolution.getvalue())
        self.assertEqual("resolved", resolved["status"])
        self.assertEqual("applied", resolved["resolution"])
        self.assertEqual([], ledger.unresolved())

    def test_pre_reconciliation_ledger_migrates_and_reconciles(self) -> None:
        path = self.control / "ledger.sqlite3"
        with closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE consumptions (
                        nonce TEXT PRIMARY KEY,
                        request_id TEXT NOT NULL,
                        request_digest TEXT NOT NULL,
                        approval_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        reserved_at TEXT NOT NULL,
                        finished_at TEXT,
                        returncode INTEGER,
                        evidence_id TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO consumptions VALUES(
                        'legacy-nonce-done', 'req_legacy_done', 'digest', 'approval_legacy_done',
                        'executed', '2026-08-01T10:00:00Z', '2026-08-01T10:00:04Z', 0, 'ev_done'
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO consumptions VALUES(
                        'legacy-nonce-stale', 'req_legacy_stale', 'digest',
                        'approval_legacy_stale', 'reserved', '2026-08-01T11:00:00Z',
                        NULL, NULL, NULL
                    )
                    """
                )
        ledger = self._ledger()
        ledger.initialize()
        promoted = ledger.promote_stale_reservations(
            promoted_at="2026-08-04T00:00:00Z",
            current_pid=os.getpid(),
        )
        self.assertEqual(["req_legacy_stale"], [row["request_id"] for row in promoted])
        rows = ledger.unresolved()
        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("unknown", row["status"])
        self.assertEqual("stale-reservation", row["unknown_origin"])
        self.assertIsNone(row["action"])
        self.assertIsNone(row["target"])
        self.assertIsNone(row["argv"])
        with closing(sqlite3.connect(ledger.path)) as connection:
            status = connection.execute(
                "SELECT status FROM consumptions WHERE request_id = 'req_legacy_done'"
            ).fetchone()
        self.assertEqual(("executed",), status)

    def test_live_reservation_survives_same_process_sweep(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()
        ledger.reserve(
            nonce=request["nonce"],
            request_id=request["request_id"],
            request_digest=request["request_digest"],
            approval_id=approval["approval_id"],
            action=request["action"],
            target=request["target"],
            argv=request["argv"],
            reserved_at=self._timestamp(self.start + timedelta(seconds=2)),
        )
        promoted = ledger.promote_stale_reservations(
            promoted_at=self._timestamp(self.start + timedelta(seconds=3))
        )
        self.assertEqual([], promoted)
        self.assertEqual([], ledger.unresolved())


if __name__ == "__main__":
    unittest.main()
