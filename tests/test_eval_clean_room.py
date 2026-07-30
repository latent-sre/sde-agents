"""Offline tests for scripts/eval_clean_room.py."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import eval_clean_room


class CleanEnvironmentTest(unittest.TestCase):
    def _config(self, root: Path) -> Path:
        config = root / "config"
        (config / "skills" / "personal").mkdir(parents=True)
        (config / "agents").mkdir()
        (config / "plugins").mkdir()
        (config / "CLAUDE.md").write_text("personal instructions", encoding="utf-8")
        (config / eval_clean_room.CREDENTIALS).write_text(
            '{"token":"test-secret"}', encoding="utf-8"
        )
        return config

    def test_clean_room_copies_only_credentials_and_removes_itself(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            config = self._config(Path(root))
            room = None
            with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(config)}, clear=False):
                with eval_clean_room.clean_env() as env:
                    room = Path(env["CLAUDE_CONFIG_DIR"])
                    self.assertEqual([eval_clean_room.CREDENTIALS], [p.name for p in room.iterdir()])
                    self.assertEqual(
                        '{"token":"test-secret"}',
                        (room / eval_clean_room.CREDENTIALS).read_text(encoding="utf-8"),
                    )
                    self.assertFalse((room / "skills").exists())
                    self.assertFalse((room / "agents").exists())
                    self.assertFalse((room / "plugins").exists())
                    self.assertFalse((room / "CLAUDE.md").exists())
            self.assertIsNotNone(room)
            self.assertFalse(room.exists())

    def test_missing_credentials_refuses_instead_of_creating_fake_no_route(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(
                os.environ,
                {"CLAUDE_CONFIG_DIR": root},
                clear=False,
            ):
                for key in eval_clean_room.AUTH_ENV_VARS:
                    os.environ.pop(key, None)
                with self.assertRaises(eval_clean_room.AuthUnavailable):
                    with eval_clean_room.clean_env():
                        pass

    def test_api_key_auth_uses_empty_isolated_config(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(
                os.environ,
                {"CLAUDE_CONFIG_DIR": root, "ANTHROPIC_API_KEY": "test-not-real"},
                clear=False,
            ):
                with eval_clean_room.clean_env() as env:
                    room = Path(env["CLAUDE_CONFIG_DIR"])
                    self.assertEqual([], list(room.iterdir()))

    def test_oauth_token_is_a_supported_clean_room_auth_source(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(
                os.environ,
                {"CLAUDE_CONFIG_DIR": root, "CLAUDE_CODE_OAUTH_TOKEN": "test-not-real"},
                clear=False,
            ):
                with eval_clean_room.clean_env() as env:
                    self.assertEqual("test-not-real", env["CLAUDE_CODE_OAUTH_TOKEN"])

    def test_personal_skill_and_plugin_sync_environment_is_scrubbed(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(
                os.environ,
                {
                    "CLAUDE_CONFIG_DIR": root,
                    "ANTHROPIC_API_KEY": "test-not-real",
                    "CLAUDE_CODE_SYNC_SKILLS": "1",
                    "CLAUDE_CODE_PLUGIN_SEED_DIR": "/personal/plugins",
                    "CLAUDE_CODE_DISABLE_POLICY_SKILLS": "1",
                },
                clear=False,
            ):
                with eval_clean_room.clean_env() as env:
                    self.assertNotIn("CLAUDE_CODE_SYNC_SKILLS", env)
                    self.assertNotIn("CLAUDE_CODE_PLUGIN_SEED_DIR", env)
                    # The salvage source set CLAUDE_CODE_DISABLE_POLICY_SKILLS here; that variable
                    # exists in no current documentation, so the room must NOT set it — and must
                    # scrub an externally exported copy, or the phantom leaks in via inheritance.
                    self.assertNotIn("CLAUDE_CODE_DISABLE_POLICY_SKILLS", env)
                    self.assertEqual("1", env["CLAUDE_CODE_SKIP_PROMPT_HISTORY"])


class RunValidationTest(unittest.TestCase):
    def event(self, *, error: bool = False, result: str = "done") -> str:
        return json.dumps({"type": "result", "is_error": error, "result": result})

    def test_success_requires_structured_non_error_result(self) -> None:
        event = eval_clean_room.validate_completed_run(self.event(), 0)
        self.assertFalse(event["is_error"])

    def test_nonzero_exit_is_runner_failure(self) -> None:
        with self.assertRaises(eval_clean_room.RunnerFailed):
            eval_clean_room.validate_completed_run("", 1, "network failed")

    def test_missing_result_event_is_runner_failure(self) -> None:
        with self.assertRaises(eval_clean_room.RunnerFailed):
            eval_clean_room.validate_completed_run('{"type":"system"}', 0)

    def test_auth_failure_is_distinct_and_never_scored(self) -> None:
        trace = self.event(error=True, result="Not logged in · Please run /login")
        with self.assertRaises(eval_clean_room.AuthUnavailable):
            eval_clean_room.validate_completed_run(trace, 1)

    def test_auth_failure_in_stderr_without_result_event_is_auth_unavailable(self) -> None:
        with self.assertRaises(eval_clean_room.AuthUnavailable):
            eval_clean_room.validate_completed_run("", 1, "Not logged in · Please run /login")

    def test_auth_failure_in_transcript_without_result_event_is_auth_unavailable(self) -> None:
        trace = '{"type":"system","subtype":"authentication_failed"}'
        with self.assertRaises(eval_clean_room.AuthUnavailable):
            eval_clean_room.validate_completed_run(trace, 1)

    def test_successful_run_mentioning_auth_text_is_not_an_outage(self) -> None:
        event = eval_clean_room.validate_completed_run(
            self.event(result="the error was: Not logged in"), 0
        )
        self.assertFalse(event["is_error"])


if __name__ == "__main__":
    unittest.main()
