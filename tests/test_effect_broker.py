from __future__ import annotations

import copy
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
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


if __name__ == "__main__":
    unittest.main()
