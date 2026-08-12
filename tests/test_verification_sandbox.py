from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from unittest import mock

from scripts import evidence_envelope, verification_sandbox
from tests.support import TempDirTestCase


IMAGE = "example.test/verifier@sha256:" + "a" * 64


class VerificationSandboxTests(TempDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.source = self.base / "source"
        self.scratch = self.base / "scratch"
        self.source.mkdir()

    def _config(self, command: tuple[str, ...] = ("python", "-m", "unittest")) -> verification_sandbox.SandboxConfig:
        return verification_sandbox.SandboxConfig(
            engine="docker",
            image=IMAGE,
            source=self.source,
            scratch=self.scratch,
            command=command,
            timeout_seconds=60,
        )

    def test_command_has_fail_closed_isolation_before_image(self) -> None:
        command = verification_sandbox.build_command(
            self._config(("--privileged", "not-an-engine-option")),
            container_name="sde-verify-0123456789abcdef",
        )
        image_index = command.index(IMAGE)
        for required in (
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
        ):
            self.assertIn(required, command[:image_index])
        self.assertEqual(
            ["--privileged", "not-an-engine-option"],
            command[image_index + 1 :],
        )
        source_mount = command[command.index("--mount") + 1]
        self.assertIn("dst=/workspace", source_mount)
        self.assertIn("readonly", source_mount)

    def test_unpinned_image_and_writable_scratch_inside_source_are_rejected(self) -> None:
        with self.assertRaisesRegex(verification_sandbox.SandboxError, "name@sha256"):
            verification_sandbox.build_command(
                verification_sandbox.SandboxConfig(
                    engine="docker",
                    image="example.test/verifier:latest",
                    source=self.source,
                    scratch=self.scratch,
                    command=("true",),
                ),
                container_name="sde-verify-0123456789abcdef",
            )
        with self.assertRaisesRegex(verification_sandbox.SandboxError, "outside"):
            verification_sandbox.build_command(
                verification_sandbox.SandboxConfig(
                    engine="docker",
                    image=IMAGE,
                    source=self.source,
                    scratch=self.source / "scratch",
                    command=("true",),
                ),
                container_name="sde-verify-0123456789abcdef",
            )

    def test_success_emits_valid_typed_evidence_and_checks_residue(self) -> None:
        calls: list[tuple[str, ...]] = []

        def runner(argv, timeout, environment):
            calls.append(tuple(argv))
            if tuple(argv[1:3]) == ("container", "inspect"):
                return verification_sandbox.ProcessResult(
                    1, b"", b"Error: No such container"
                )
            if argv[1] == "rm":
                return verification_sandbox.ProcessResult(
                    1, b"", b"Error: No such container"
                )
            return verification_sandbox.ProcessResult(0, b"tests passed\n", b"")

        fixed = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
        envelope = verification_sandbox.execute(
            self._config(),
            target_revision="abc123",
            criterion="unit tests pass",
            run_id="run-1",
            task_id="task-1",
            attempt_id="attempt-1",
            runner=runner,
            now=lambda: fixed,
        )
        evidence_envelope.validate_envelope(envelope)
        self.assertEqual("pass", envelope["status"])
        self.assertEqual("none", envelope["isolation"]["network"])
        self.assertEqual(False, envelope["source"]["residue"])
        self.assertEqual(3, len(calls))
        self.assertEqual("run", calls[0][1])
        self.assertEqual("rm", calls[1][1])
        self.assertEqual(("container", "inspect"), calls[2][1:3])

    def test_timeout_is_inconclusive_but_residue_is_an_error(self) -> None:
        def no_residue_runner(argv, timeout, environment):
            if tuple(argv[1:3]) == ("container", "inspect"):
                return verification_sandbox.ProcessResult(
                    1, b"", b"Error: No such object"
                )
            if argv[1] == "rm":
                return verification_sandbox.ProcessResult(0, b"", b"")
            return verification_sandbox.ProcessResult(None, b"partial", b"", timed_out=True)

        timeout_envelope = verification_sandbox.execute(
            self._config(),
            target_revision="abc123",
            criterion="unit tests pass",
            runner=no_residue_runner,
        )
        self.assertEqual("inconclusive", timeout_envelope["status"])
        self.assertTrue(any("timed out" in item for item in timeout_envelope["limitations"]))

        def residue_runner(argv, timeout, environment):
            if tuple(argv[1:3]) == ("container", "inspect"):
                return verification_sandbox.ProcessResult(0, b"container json", b"")
            return verification_sandbox.ProcessResult(0, b"", b"")

        residue_envelope = verification_sandbox.execute(
            self._config(),
            target_revision="abc123",
            criterion="unit tests pass",
            runner=residue_runner,
        )
        self.assertEqual("error", residue_envelope["status"])
        self.assertTrue(any("still exists" in item for item in residue_envelope["limitations"]))

    def test_command_exit_127_is_failure_but_engine_spawn_error_is_inconclusive(self) -> None:
        def runner_for(run_result):
            def runner(argv, timeout, environment):
                if tuple(argv[1:3]) == ("container", "inspect"):
                    return verification_sandbox.ProcessResult(
                        1, b"", b"Error: No such container"
                    )
                if argv[1] == "rm":
                    return verification_sandbox.ProcessResult(1, b"", b"No such container")
                return run_result

            return runner

        command_missing = verification_sandbox.execute(
            self._config(("/bin/not-present",)),
            target_revision="abc123",
            criterion="missing command fails",
            runner=runner_for(
                verification_sandbox.ProcessResult(127, b"", b"command not found")
            ),
        )
        self.assertEqual("fail", command_missing["status"])

        engine_missing = verification_sandbox.execute(
            self._config(),
            target_revision="abc123",
            criterion="engine availability",
            runner=runner_for(
                verification_sandbox.ProcessResult(
                    127,
                    b"",
                    b"engine executable missing",
                    spawn_error=True,
                )
            ),
        )
        self.assertEqual("inconclusive", engine_missing["status"])
        self.assertTrue(
            any("could not be started" in item for item in engine_missing["limitations"])
        )

    def test_engine_environment_does_not_inherit_remote_or_secret_configuration(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "PATH": "C:/tools",
                "DOCKER_HOST": "tcp://remote.example:2375",
                "DOCKER_CONFIG": "C:/secret-config",
                "OPENAI_API_KEY": "secret",
            },
            clear=True,
        ):
            environment = verification_sandbox._engine_environment()
        self.assertEqual({"PATH": "C:/tools"}, environment)


if __name__ == "__main__":
    unittest.main()
