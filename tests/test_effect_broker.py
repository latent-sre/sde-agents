from __future__ import annotations

import copy
import hashlib
import hmac
import io
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, redirect_stdout
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

    def _reserve_directly(
        self,
        ledger: effect_broker.ReplayLedger,
        request: dict[str, object],
        approval: dict[str, object],
        *,
        reserved_at: datetime,
    ) -> None:
        """Write a 'reserved' row through the ledger API, as a broker that then crashed would have."""
        ledger.reserve(
            nonce=request["nonce"],
            request_id=request["request_id"],
            request_digest=request["request_digest"],
            approval_id=approval["approval_id"],
            reserved_at=effect_broker._format_timestamp(reserved_at),
            action=request["action"],
            target=request["target"],
            argv=request["argv"],
            timeout_seconds=request["timeout_seconds"],
            expires_at=request["expires_at"],
        )

    def test_crash_between_reservation_and_dispatch_becomes_unknown_via_reconcile(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()
        self._reserve_directly(ledger, request, approval, reserved_at=self.start)
        self.assertEqual("reserved", ledger.get(request["nonce"])["status"])

        past_deadline = self.start + timedelta(
            seconds=request["timeout_seconds"] + effect_broker.RECONCILIATION_GRACE_SECONDS + 1
        )
        unresolved = ledger.list_unresolved(now=lambda: past_deadline)
        self.assertEqual(1, len(unresolved))
        self.assertEqual("unknown", unresolved[0]["status"])
        self.assertEqual(request["nonce"], unresolved[0]["nonce"])
        self.assertEqual(request["argv"], unresolved[0]["argv"])
        row = ledger.get(request["nonce"])
        self.assertEqual("unknown", row["status"])
        self.assertEqual("stale-reservation", row["unknown_origin"])

        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=lambda *a: (_ for _ in ()).throw(AssertionError("no replay")),
                now=lambda: self.start + timedelta(seconds=1),
            )

    def test_reserved_before_deadline_is_in_flight_and_not_resolvable(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()
        self._reserve_directly(ledger, request, approval, reserved_at=self.start)

        before_deadline = self.start + timedelta(seconds=5)
        unresolved = ledger.list_unresolved(now=lambda: before_deadline)
        self.assertEqual(["reserved-in-flight"], [item["status"] for item in unresolved])
        self.assertEqual("reserved", ledger.get(request["nonce"])["status"])

        with self.assertRaisesRegex(effect_broker.ReplayError, "not 'unknown'"):
            effect_broker.resolve_unknown(
                ledger,
                nonce=request["nonce"],
                resolution="executed",
                operator="oncall@example",
                note="checked externally",
                workspace_root=self.workspace,
                key=self.key,
            )

    def test_runner_exception_marks_unknown_eagerly_and_blocks_replay(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()

        def runner(argv, cwd, environment, timeout):
            raise RuntimeError("external effect may have started before the runner crashed")

        times = iter([self.start + timedelta(seconds=2)])
        with self.assertRaisesRegex(RuntimeError, "crashed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: next(times),
            )
        row = ledger.get(request["nonce"])
        self.assertEqual("unknown", row["status"])
        self.assertEqual("dispatch-exception", row["unknown_origin"])

        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(seconds=10),
            )

    def test_keyboard_interrupt_mid_dispatch_marks_unknown_and_blocks_replay(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()

        def runner(argv, cwd, environment, timeout):
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(seconds=2),
            )
        row = ledger.get(request["nonce"])
        self.assertEqual("unknown", row["status"])
        self.assertEqual("dispatch-exception", row["unknown_origin"])

        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(seconds=10),
            )

    def test_post_runner_now_failure_marks_unknown_eagerly_and_blocks_replay(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()

        def runner(argv, cwd, environment, timeout):
            return effect_broker.ProcessResult(0, b"", b"")

        # Only one `now()` value: reserve()'s `started` consumes it, so the finalization call to
        # `ended = now()` raises -- simulating a crash between dispatch and finalization.
        times = iter([self.start + timedelta(seconds=2)])
        with self.assertRaises(StopIteration):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: next(times),
            )
        row = ledger.get(request["nonce"])
        self.assertEqual("unknown", row["status"])
        self.assertEqual("finalization-exception", row["unknown_origin"])

        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(seconds=10),
            )

    def test_mark_unknown_failure_does_not_mask_original_exception(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()

        def runner(argv, cwd, environment, timeout):
            # The reservation already committed; now break the ledger file itself (replace it
            # with a directory) so mark_unknown's own connect() fails inside the exception
            # handler. The RuntimeError below -- not a masking sqlite3.Error -- must still win.
            ledger.path.unlink()
            ledger.path.mkdir()
            raise RuntimeError("effect runner crashed")

        times = iter([self.start + timedelta(seconds=2)])
        with self.assertRaisesRegex(RuntimeError, "crashed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: next(times),
            )

    def test_resolve_records_evidence_and_blocks_double_resolution(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()

        def runner(argv, cwd, environment, timeout):
            raise RuntimeError("boom")

        times = iter([self.start + timedelta(seconds=2)])
        with self.assertRaises(RuntimeError):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: next(times),
            )

        envelope = effect_broker.resolve_unknown(
            ledger,
            nonce=request["nonce"],
            resolution="not-executed",
            operator="oncall@example",
            note="confirmed target artifact absent",
            workspace_root=self.workspace,
            key=self.key,
            now=lambda: self.start + timedelta(minutes=10),
        )
        evidence_envelope.validate_envelope(envelope)
        self.assertEqual("unknown-reservation-resolution", envelope["source"]["kind"])
        self.assertEqual("not-executed", envelope["source"]["resolution"])
        self.assertIn("attestation", envelope["limitations"][0])
        self.assertEqual("hmac-sha256", envelope["isolation"]["signature"])

        row = ledger.get(request["nonce"])
        self.assertEqual("resolved-not-executed", row["status"])
        self.assertEqual("not-executed", row["resolution"])
        self.assertEqual("oncall@example", row["resolved_by"])
        self.assertEqual(envelope["evidence_id"], row["resolution_evidence_id"])
        expected_signature = hmac.new(
            self.key,
            effect_broker._canonical(
                {
                    "nonce": request["nonce"],
                    "resolution": "not-executed",
                    "resolved_at": row["resolved_at"],
                    "resolved_by": "oncall@example",
                    "note": "confirmed target artifact absent",
                }
            ),
            hashlib.sha256,
        ).hexdigest()
        self.assertTrue(hmac.compare_digest(expected_signature, row["resolution_signature"]))

        with self.assertRaisesRegex(effect_broker.ReplayError, "not 'unknown'"):
            effect_broker.resolve_unknown(
                ledger,
                nonce=request["nonce"],
                resolution="executed",
                operator="someone-else@example",
                note="second look",
                workspace_root=self.workspace,
                key=self.key,
            )

        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=lambda *a: (_ for _ in ()).throw(AssertionError("no replay")),
                now=lambda: self.start + timedelta(seconds=20),
            )

    def test_indeterminate_resolution_is_recorded_and_terminal(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()

        with self.assertRaises(RuntimeError):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=lambda *a: (_ for _ in ()).throw(RuntimeError("boom")),
                now=lambda: self.start + timedelta(seconds=2),
            )
        envelope = effect_broker.resolve_unknown(
            ledger,
            nonce=request["nonce"],
            resolution="indeterminate",
            operator="oncall@example",
            note="target system unreachable; outcome could not be established either way",
            workspace_root=self.workspace,
            key=self.key,
            now=lambda: self.start + timedelta(minutes=10),
        )
        evidence_envelope.validate_envelope(envelope)
        self.assertEqual("indeterminate", envelope["source"]["resolution"])
        row = ledger.get(request["nonce"])
        self.assertEqual("resolved-indeterminate", row["status"])

        # Admitting uncertainty is just as terminal as a definite answer: no re-resolution,
        # no replay.
        with self.assertRaisesRegex(effect_broker.ReplayError, "not 'unknown'"):
            effect_broker.resolve_unknown(
                ledger,
                nonce=request["nonce"],
                resolution="executed",
                operator="oncall@example",
                note="second look",
                workspace_root=self.workspace,
                key=self.key,
            )
        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=lambda *a: (_ for _ in ()).throw(AssertionError("no replay")),
                now=lambda: self.start + timedelta(seconds=20),
            )

    def _resolved_row(self, resolution: str = "not-executed") -> tuple:
        """Drive one reservation to a terminal resolution and return (ledger, nonce)."""
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()
        with self.assertRaises(RuntimeError):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=lambda *a: (_ for _ in ()).throw(RuntimeError("boom")),
                now=lambda: self.start + timedelta(seconds=2),
            )
        effect_broker.resolve_unknown(
            ledger,
            nonce=request["nonce"],
            resolution=resolution,
            operator="oncall@example",
            note="checked externally",
            workspace_root=self.workspace,
            key=self.key,
            now=lambda: self.start + timedelta(minutes=10),
        )
        return ledger, request["nonce"]

    def test_reconcile_verify_passes_on_intact_rows(self) -> None:
        """An untampered resolved row verifies; the report names it and carries no findings."""
        ledger, nonce = self._resolved_row()
        report = effect_broker.verify_resolutions(ledger, key=self.key)
        self.assertEqual(report["checked"], 1)
        self.assertEqual(report["verified"], [nonce])
        self.assertEqual(report["findings"], [])

    def test_reconcile_verify_fires_on_tampered_resolution(self) -> None:
        """Editing a signed field directly in SQLite must surface as a finding. Before the
        verify path existed this exact edit kept its stale signature indefinitely -- the
        column looked like tamper-evidence while detecting nothing."""
        ledger, nonce = self._resolved_row()
        with closing(sqlite3.connect(ledger.path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE consumptions SET resolution_note = ? WHERE nonce = ?",
                    ("history rewritten after the fact", nonce),
                )
        report = effect_broker.verify_resolutions(ledger, key=self.key)
        self.assertEqual(report["checked"], 1)
        self.assertEqual(report["verified"], [])
        self.assertEqual(len(report["findings"]), 1)
        self.assertEqual(report["findings"][0]["nonce"], nonce)

    def test_reconcile_verify_rejects_wrong_key_and_short_key(self) -> None:
        """A wrong (full-length) key must fail every row rather than silently verify, and a
        short key is refused outright with the same bound the write side enforces."""
        ledger, nonce = self._resolved_row()
        report = effect_broker.verify_resolutions(ledger, key=b"w" * 32)
        self.assertEqual(report["verified"], [])
        self.assertEqual(len(report["findings"]), 1)
        with self.assertRaisesRegex(effect_broker.BrokerError, "at least 32 bytes"):
            effect_broker.verify_resolutions(ledger, key=b"short")

    def test_reconcile_verify_flags_unsigned_resolved_rows(self) -> None:
        """Strict policy: a resolved row with a NULL signature is an "unsigned" finding, not a
        benign legacy skip -- whoever can UPDATE a signed field can also NULL the signature,
        so a skip would hand tampering an evasion path."""
        ledger, nonce = self._resolved_row()
        with closing(sqlite3.connect(ledger.path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE consumptions SET resolution_signature = NULL WHERE nonce = ?",
                    (nonce,),
                )
        report = effect_broker.verify_resolutions(ledger, key=self.key)
        self.assertEqual(report["checked"], 1)
        self.assertEqual(report["verified"], [])
        self.assertEqual(report["findings"], [{"nonce": nonce, "problem": "unsigned"}])

    def test_reconcile_verify_cli_gates_on_findings(self) -> None:
        """The exit contract both ways: findings exit 1, an intact ledger exits 0. A verify
        that printed a mismatch but exited 0 would be the write-only column one layer up --
        visible to a log reader, invisible to everything that gates."""
        ledger, nonce = self._resolved_row()
        key_file = self.control / "verify-key"
        key_file.write_bytes(self.key)
        argv = [
            "reconcile", "verify",
            "--ledger", str(ledger.path),
            "--workspace-root", str(self.workspace),
            "--key-file", str(key_file),
        ]
        with closing(sqlite3.connect(ledger.path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE consumptions SET resolution_note = ? WHERE nonce = ?",
                    ("rewritten", nonce),
                )
        with redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(effect_broker.main(argv), 1)
        self.assertIn("mismatch", captured.getvalue())
        with closing(sqlite3.connect(ledger.path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE consumptions SET resolution_note = ? WHERE nonce = ?",
                    ("checked externally", nonce),
                )
        with redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(effect_broker.main(argv), 0)
        self.assertIn(nonce, captured.getvalue())

    def test_reconcile_verify_ignores_unresolved_rows(self) -> None:
        """Nothing signed an unresolved row, so verify must not count or flag it."""
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()
        with self.assertRaises(RuntimeError):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=lambda *a: (_ for _ in ()).throw(RuntimeError("boom")),
                now=lambda: self.start + timedelta(seconds=2),
            )
        report = effect_broker.verify_resolutions(ledger, key=self.key)
        self.assertEqual(report["checked"], 0)
        self.assertEqual(report["findings"], [])

    def test_list_unresolved_projects_the_approval_expiry(self) -> None:
        """The expiry copied onto the row at reservation is triage context for the operator;
        unprojected it was a write-only column."""
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()
        with self.assertRaises(RuntimeError):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=lambda *a: (_ for _ in ()).throw(RuntimeError("boom")),
                now=lambda: self.start + timedelta(seconds=2),
            )
        rows = ledger.list_unresolved(now=lambda: self.start + timedelta(hours=2))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["expires_at"], request["expires_at"])

    def test_resolve_unknown_input_guards_fire(self) -> None:
        ledger = self._ledger()
        base: dict[str, object] = {
            "nonce": "0" * 64,
            "resolution": "executed",
            "operator": "oncall@example",
            "note": "checked externally",
            "workspace_root": self.workspace,
            "key": self.key,
        }
        # Each guard precedes the row lookup, so an empty ledger proves the guard itself fired
        # rather than the missing-row path.
        for override, message in (
            ({"resolution": "retried"}, "resolution must be one of"),
            ({"operator": "   "}, "operator must be non-empty"),
            ({"note": ""}, "resolution note must be non-empty"),
            ({"key": b"short"}, "at least 32 bytes"),
        ):
            with self.subTest(**override):
                with self.assertRaisesRegex(effect_broker.BrokerError, message):
                    effect_broker.resolve_unknown(ledger, **{**base, **override})

    def test_resolve_unknown_nonce_fails(self) -> None:
        ledger = self._ledger()
        with self.assertRaisesRegex(effect_broker.ReplayError, "no reservation exists"):
            effect_broker.resolve_unknown(
                ledger,
                nonce="0" * 64,
                resolution="executed",
                operator="oncall@example",
                note="n/a",
                workspace_root=self.workspace,
                key=self.key,
            )

    def test_nonce_is_never_freed_across_every_terminal_state(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()

        times = iter([self.start + timedelta(seconds=2)])
        with self.assertRaises(RuntimeError):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=lambda *a: (_ for _ in ()).throw(RuntimeError("boom")),
                now=lambda: next(times),
            )
        effect_broker.resolve_unknown(
            ledger,
            nonce=request["nonce"],
            resolution="executed",
            operator="oncall@example",
            note="verified manually against the target system",
            workspace_root=self.workspace,
            key=self.key,
            now=lambda: self.start + timedelta(minutes=5),
        )

        with closing(sqlite3.connect(ledger.path)) as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM consumptions WHERE nonce = ?", (request["nonce"],)
            ).fetchone()[0]
        self.assertEqual(1, count)

        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=lambda *a: (_ for _ in ()).throw(AssertionError("no replay")),
                now=lambda: self.start + timedelta(seconds=30),
            )

    def test_old_schema_ledger_migrates_and_still_enforces_one_shot(self) -> None:
        path = self.control / "old-ledger.sqlite3"
        old_nonce = "deadbeef" * 8
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
                    INSERT INTO consumptions(
                        nonce, request_id, request_digest, approval_id, status, reserved_at,
                        finished_at, returncode, evidence_id
                    ) VALUES (?, 'req_old', 'digest_old', 'approval_old', 'executed',
                              '2026-01-01T00:00:00Z', '2026-01-01T00:00:05Z', 0, 'ev_old')
                    """,
                    (old_nonce,),
                )

        ledger = effect_broker.ReplayLedger(path, self.workspace)
        request = self._request()
        approval = self._approval(request)

        def runner(argv, cwd, environment, timeout):
            return effect_broker.ProcessResult(0, b"ok\n", b"")

        times = iter([self.start + timedelta(seconds=2), self.start + timedelta(seconds=3)])
        envelope = effect_broker.execute_approved(
            request,
            approval,
            key=self.key,
            ledger=ledger,
            runner=runner,
            now=lambda: next(times),
        )
        evidence_envelope.validate_envelope(envelope)

        with self.assertRaisesRegex(effect_broker.ReplayError, "already been consumed"):
            effect_broker.execute_approved(
                request,
                approval,
                key=self.key,
                ledger=ledger,
                runner=runner,
                now=lambda: self.start + timedelta(seconds=10),
            )

        old_row = ledger.get(old_nonce)
        self.assertEqual("executed", old_row["status"])
        self.assertIsNone(old_row["action"])

        new_row = ledger.get(request["nonce"])
        self.assertEqual(request["action"], new_row["action"])
        self.assertEqual(request["argv"], new_row["argv"])


    def test_finish_after_reconciliation_marked_unknown_reports_discarded_outcome(self) -> None:
        request = self._request()
        approval = self._approval(request)
        ledger = self._ledger()
        self._reserve_directly(ledger, request, approval, reserved_at=self.start)

        # A reconciliation pass on a deadline flips the row to 'unknown' while the (stalled but
        # alive) broker still believes it holds the reservation.
        past_deadline = self.start + timedelta(
            seconds=request["timeout_seconds"] + effect_broker.RECONCILIATION_GRACE_SECONDS + 1
        )
        ledger.list_unresolved(now=lambda: past_deadline)

        with self.assertRaisesRegex(
            effect_broker.ReplayError, r"finalized as 'executed' \(returncode=0\).*'unknown'"
        ) as caught:
            ledger.finish(
                nonce=request["nonce"],
                status="executed",
                finished_at=effect_broker._format_timestamp(past_deadline),
                returncode=0,
                evidence_id="ev_late_finish",
            )
        self.assertIn("could not be finalized", str(caught.exception))
        self.assertEqual("unknown", ledger.get(request["nonce"])["status"])

    def test_legacy_reserved_row_reconciles_with_placeholder_evidence(self) -> None:
        path = self.control / "legacy-reserved-ledger.sqlite3"
        legacy_nonce = "abcd1234" * 8
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
                    INSERT INTO consumptions(
                        nonce, request_id, request_digest, approval_id, status, reserved_at
                    ) VALUES (?, 'req_legacy', 'digest_legacy', 'approval_legacy', 'reserved',
                              '2026-01-01T00:00:00Z')
                    """,
                    (legacy_nonce,),
                )

        ledger = effect_broker.ReplayLedger(path, self.workspace)
        # A legacy row has NULL timeout_seconds, so its deadline collapses to reserved_at + grace.
        past_collapsed_deadline = datetime(2026, 1, 1, 0, 2, tzinfo=timezone.utc)
        unresolved = ledger.list_unresolved(now=lambda: past_collapsed_deadline)
        self.assertEqual(["unknown"], [item["status"] for item in unresolved])
        self.assertIsNone(unresolved[0]["action"])

        envelope = effect_broker.resolve_unknown(
            ledger,
            nonce=legacy_nonce,
            resolution="not-executed",
            operator="oncall@example",
            note="legacy reservation predates the recorded-effect columns; target checked by hand",
            workspace_root=self.workspace,
            key=self.key,
            now=lambda: self.start,
        )
        evidence_envelope.validate_envelope(envelope)
        self.assertIn("unrecorded-legacy-action", envelope["criterion"])
        self.assertIn("unrecorded-legacy-target", envelope["criterion"])
        self.assertEqual("unrecorded-legacy-action", envelope["source"]["action"])
        self.assertEqual("unrecorded-legacy-target", envelope["source"]["target"])
        self.assertEqual("resolved-not-executed", ledger.get(legacy_nonce)["status"])


if __name__ == "__main__":
    unittest.main()
