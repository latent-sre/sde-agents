from __future__ import annotations

import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import evidence_envelope


class EvidenceEnvelopeTests(unittest.TestCase):
    def _valid(self) -> dict[str, object]:
        started = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
        return evidence_envelope.new_envelope(
            producer="verification_sandbox",
            role="verification-engineer",
            target_root="C:/work/repo",
            target_revision="abc123",
            criterion="unit tests pass",
            status="pass",
            started_at=started,
            ended_at=started + timedelta(seconds=2),
            command_argv=["python", "-m", "unittest"],
            command_cwd="C:/work/repo",
            exit_code=0,
            run_id="run-1",
            task_id="task-1",
            attempt_id="attempt-1",
            isolation={"network": "none", "source_mount": "read-only"},
        )

    def test_valid_envelope_round_trips_canonical_json(self) -> None:
        envelope = self._valid()
        evidence_envelope.validate_envelope(envelope)
        rendered = evidence_envelope.canonical_json(envelope)
        self.assertEqual(rendered, evidence_envelope.canonical_json(envelope))
        self.assertTrue(envelope["evidence_id"].startswith("ev_"))

    def test_command_must_be_argv_not_a_shell_string(self) -> None:
        envelope = self._valid()
        envelope["command"]["argv"] = "python -m unittest"  # type: ignore[index]
        with self.assertRaisesRegex(
            evidence_envelope.EnvelopeValidationError,
            "command.argv",
        ):
            evidence_envelope.validate_envelope(envelope)

    def test_inverted_timestamps_are_rejected(self) -> None:
        envelope = self._valid()
        envelope["ended_at"] = "2026-07-31T11:59:59Z"
        with self.assertRaisesRegex(
            evidence_envelope.EnvelopeValidationError,
            "cannot precede",
        ):
            evidence_envelope.validate_envelope(envelope)

    def test_secret_bearing_keys_are_rejected_recursively(self) -> None:
        envelope = self._valid()
        envelope["environment"]["service"] = {"api_token": "do-not-record"}  # type: ignore[index]
        with self.assertRaisesRegex(
            evidence_envelope.EnvelopeValidationError,
            "must not contain credentials",
        ):
            evidence_envelope.validate_envelope(envelope)

    def test_invalid_status_and_unknown_fields_are_rejected(self) -> None:
        invalid_status = self._valid()
        invalid_status["status"] = "probably"
        with self.assertRaisesRegex(
            evidence_envelope.EnvelopeValidationError,
            "unknown evidence status",
        ):
            evidence_envelope.validate_envelope(invalid_status)

        unknown = self._valid()
        unknown["confidence"] = "high"
        with self.assertRaisesRegex(
            evidence_envelope.EnvelopeValidationError,
            "unknown evidence fields",
        ):
            evidence_envelope.validate_envelope(unknown)

    def test_artifact_record_binds_bytes_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.txt"
            path.write_bytes(b"evidence\n")
            record = evidence_envelope.artifact_record(path, display_path="result.txt")
        self.assertEqual("result.txt", record["path"])
        self.assertEqual(9, record["size"])
        self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")

    def test_context_identifiers_are_bounded(self) -> None:
        envelope = self._valid()
        invalid = copy.deepcopy(envelope)
        invalid["context"]["run_id"] = " contains spaces "  # type: ignore[index]
        with self.assertRaisesRegex(
            evidence_envelope.EnvelopeValidationError,
            "invalid identifier",
        ):
            evidence_envelope.validate_envelope(invalid)


if __name__ == "__main__":
    unittest.main()
