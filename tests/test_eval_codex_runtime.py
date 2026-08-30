from __future__ import annotations

import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from scripts import eval_codex_runtime


class CodexRuntimeContractTest(unittest.TestCase):
    def _profile(self, root: Path, name: str = "homelab-engineer") -> Path:
        path = root / ".codex" / "agents" / f"{name}.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                (
                    f'name = "{name}"',
                    'description = "Generated role"',
                    'sandbox_mode = "workspace-write"',
                    "developer_instructions = '''Exact role instructions.'''",
                    "",
                )
            ),
            encoding="utf-8",
        )
        return path

    def test_profile_projection_loads_exact_generated_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._profile(root)
            profiles, _identity = eval_codex_runtime.capture_profiles(
                root, ["sde-agents:homelab-engineer"]
            )
            profile = profiles["sde-agents:homelab-engineer"]

        self.assertEqual("homelab-engineer", profile["name"])
        self.assertEqual("Exact role instructions.", profile["developer_instructions"])
        self.assertEqual("workspace-write", profile["sandbox_mode"])

    def test_profile_projection_rejects_unrepresented_fields_and_name_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._profile(root)
            path.write_text(path.read_text(encoding="utf-8") + 'model = "gpt-5.6-sol"\n',
                            encoding="utf-8")
            with self.assertRaisesRegex(eval_codex_runtime.CodexRuntimeError, "unsupported field"):
                eval_codex_runtime.capture_profiles(root, ["sde-agents:homelab-engineer"])

            path = self._profile(root)
            path.write_text(path.read_text(encoding="utf-8").replace(
                'name = "homelab-engineer"', 'name = "different"'
            ), encoding="utf-8")
            with self.assertRaisesRegex(eval_codex_runtime.CodexRuntimeError, "does not match"):
                eval_codex_runtime.capture_profiles(root, ["sde-agents:homelab-engineer"])

            path = self._profile(root)
            path.write_text(path.read_text(encoding="utf-8").replace(
                'sandbox_mode = "workspace-write"', 'sandbox_mode = ["read-only"]'
            ), encoding="utf-8")
            with self.assertRaisesRegex(eval_codex_runtime.CodexRuntimeError, "sandbox_mode"):
                eval_codex_runtime.capture_profiles(root, ["sde-agents:homelab-engineer"])

    def test_case_projection_accepts_only_direct_no_tool_agent_cases(self) -> None:
        supported = {
            "id": "supported",
            "agent": "sde-agents:homelab-engineer",
            "allowed_tools": [],
            "disallowed_tools": ["Bash", "Write"],
        }
        self.assertEqual("homelab-engineer", eval_codex_runtime.validate_case_projection(supported))

        variants = (
            ({**supported, "agent": None}, "direct agent"),
            ({**supported, "allowed_tools": ["Skill"]}, "empty allowed_tools"),
            ({**supported, "permission_mode": "acceptEdits"}, "permission_mode"),
        )
        for case, message in variants:
            with self.subTest(case=case):
                with self.assertRaisesRegex(eval_codex_runtime.CodexRuntimeError, message):
                    eval_codex_runtime.validate_case_projection(case)

    def test_command_pins_subscription_eval_boundary_and_reads_prompt_from_stdin(self) -> None:
        command = eval_codex_runtime.build_command(
            "C:/tools/codex.exe",
            Path("C:/scratch/session"),
            model="gpt-5.6-terra",
            reasoning_effort="medium",
            developer_instructions="Exact role instructions.",
        )

        self.assertEqual(["C:/tools/codex.exe", "-a", "never", "exec"], command[:4])
        self.assertEqual("-", command[-1])
        self.assertEqual("gpt-5.6-terra", command[command.index("--model") + 1])
        self.assertEqual("read-only", command[command.index("--sandbox") + 1])
        self.assertEqual(str(Path("C:/scratch/session")), command[command.index("--cd") + 1])
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--strict-config", command)
        self.assertIn('model_reasoning_effort="medium"', command)
        self.assertIn('web_search="disabled"', command)
        self.assertIn("skills.include_instructions=false", command)
        self.assertIn('model_provider="openai"', command)
        self.assertIn(
            f'openai_base_url="{eval_codex_runtime.SUBSCRIPTION_BASE_URL}"', command
        )
        self.assertIn('forced_login_method="chatgpt"', command)
        self.assertIn('cli_auth_credentials_store="file"', command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        disabled = {
            command[index + 1]
            for index, value in enumerate(command[:-1])
            if value == "--disable"
        }
        self.assertTrue({
            "code_mode_host",
            "default_mode_request_user_input",
            "shell_tool",
            "multi_agent",
            "plugins",
            "apps",
        } <= disabled)
        self.assertIn("tools.update_plan.enabled=false", command)
        encoded = next(
            value.split("=", 1)[1]
            for value in command
            if value.startswith("developer_instructions=")
        )
        self.assertEqual(
            "Exact role instructions.", tomllib.loads(f"value = {encoded}")["value"]
        )
        with self.assertRaisesRegex(eval_codex_runtime.CodexRuntimeError, "explicit model"):
            eval_codex_runtime.build_command(
                "codex",
                Path("C:/scratch/session"),
                model=" ",
                reasoning_effort="medium",
                developer_instructions="Exact role instructions.",
            )

    def test_parser_requires_terminal_success_and_keeps_last_message_and_usage(self) -> None:
        transcript = "\n".join(
            (
                "diagnostic",
                json.dumps({"type": "thread.started", "model": "gpt-5.6-terra"}),
                json.dumps({
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "first"},
                }),
                json.dumps({
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "final"},
                }),
                json.dumps({
                    "type": "metadata",
                    "nested": {"type": "agent_message", "text": "not the answer"},
                }),
                json.dumps({
                    "type": "turn.completed",
                    "usage": {"input_tokens": 11, "output_tokens": 7},
                }),
            )
        )
        parsed = eval_codex_runtime.parse_jsonl(transcript)
        self.assertEqual(5, parsed["events"])
        self.assertEqual("final", parsed["last_message"])
        self.assertEqual(["gpt-5.6-terra"], parsed["observed_models"])
        self.assertEqual(11, parsed["usage"]["input_tokens"])
        self.assertTrue(parsed["completed"])
        self.assertFalse(parsed["failed"])
        self.assertEqual([], parsed["tool_attempts"])

        failed = eval_codex_runtime.parse_jsonl(
            transcript + "\n" + json.dumps({"type": "turn.failed", "error": "outage"})
        )
        self.assertTrue(failed["failed"])

        absent = eval_codex_runtime.parse_jsonl("\n".join((
            json.dumps({
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "answer"},
            }),
            json.dumps({"type": "turn.completed"}),
        )))
        self.assertIsNone(absent["usage"])
        self.assertEqual([], absent["observed_models"])

    def test_run_session_never_grades_error_text_and_passes_prompt_on_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scratch = root / "scratch"
            completed = "\n".join((
                json.dumps({
                    "type": "item.completed",
                    "item": {
                        "type": "error",
                        "message": (
                            "Code mode is unavailable because its host is disabled; "
                            "code mode will fail closed."
                        ),
                    },
                }),
                json.dumps({
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": "usable answer that discusses a rate limit safely",
                    },
                }),
                json.dumps({
                    "type": "turn.completed",
                    "usage": {"input_tokens": 5, "output_tokens": 2},
                }),
            ))
            proc = mock.Mock(returncode=0, stdout=completed, stderr="")
            with mock.patch.object(eval_codex_runtime.subprocess, "run", return_value=proc) as run:
                text, fired, note, stats = eval_codex_runtime.run_session(
                    "task prompt", 20,
                    agent="sde-agents:homelab-engineer",
                    developer_instructions="Exact role instructions.",
                    model="gpt-5.6-terra",
                    reasoning_effort="medium",
                    executable="codex",
                    scratch_root=scratch,
                )
            self.assertEqual("usable answer that discusses a rate limit safely", text)
            self.assertEqual({"homelab-engineer"}, fired)
            self.assertIsNone(note)
            self.assertTrue(stats["completed"])
            self.assertEqual(5, stats["input_tokens"])
            self.assertEqual("task prompt", run.call_args.kwargs["input"])
            self.assertEqual("-", run.call_args.args[0][-1])
            self.assertEqual([], list(scratch.iterdir()))

            failed = completed + "\n" + json.dumps({"type": "turn.failed", "error": "bad"})
            proc = mock.Mock(returncode=0, stdout=failed, stderr="oracle-shaped error text")
            with mock.patch.object(eval_codex_runtime.subprocess, "run", return_value=proc):
                text, _fired, note, stats = eval_codex_runtime.run_session(
                    "task prompt", 20,
                    agent="sde-agents:homelab-engineer",
                    developer_instructions="Exact role instructions.",
                    model="gpt-5.6-terra",
                    reasoning_effort="medium",
                    executable="codex",
                    scratch_root=scratch,
                )
            self.assertEqual("", text)
            self.assertIn("failure event", note)
            self.assertFalse(stats["completed"])

            proc = mock.Mock(returncode=1, stdout=completed, stderr="generic runner error")
            with mock.patch.object(eval_codex_runtime.subprocess, "run", return_value=proc):
                text, _fired, note, stats = eval_codex_runtime.run_session(
                    "task prompt", 20,
                    agent="sde-agents:homelab-engineer",
                    developer_instructions="Exact role instructions.",
                    model="gpt-5.6-terra",
                    reasoning_effort="medium",
                    executable="codex",
                    scratch_root=scratch,
                )
            self.assertEqual("", text)
            self.assertIn("exited 1", note)
            self.assertTrue(stats["completed"])

            tool_transcript = completed + "\n" + json.dumps({
                "type": "item.completed",
                "item": {"type": "command_execution", "command": "whoami"},
            })
            proc = mock.Mock(returncode=0, stdout=tool_transcript, stderr="")
            with mock.patch.object(eval_codex_runtime.subprocess, "run", return_value=proc):
                text, _fired, note, stats = eval_codex_runtime.run_session(
                    "task prompt", 20,
                    agent="sde-agents:homelab-engineer",
                    developer_instructions="Exact role instructions.",
                    model="gpt-5.6-terra",
                    reasoning_effort="medium",
                    executable="codex",
                    scratch_root=scratch,
                )
            self.assertEqual("", text)
            self.assertIn("command_execution", note)
            self.assertTrue(stats["result_error"])

    def test_auth_preflight_records_only_chatgpt_mode(self) -> None:
        proc = mock.Mock(returncode=0, stdout="", stderr="Logged in using ChatGPT\n")
        with mock.patch.object(
            eval_codex_runtime.subprocess, "run", return_value=proc
        ) as run:
            self.assertEqual(
                {"auth": "chatgpt", "provider": "openai"},
                eval_codex_runtime.auth_provider_mode("codex"),
            )
        command = run.call_args.args[0]
        self.assertEqual("login", command[-2])
        self.assertEqual("status", command[-1])
        self.assertIn('model_provider="openai"', command)
        self.assertIn(
            f'openai_base_url="{eval_codex_runtime.SUBSCRIPTION_BASE_URL}"', command
        )
        self.assertIn('forced_login_method="chatgpt"', command)
        self.assertIn('cli_auth_credentials_store="file"', command)

    def test_mcp_preflight_requires_a_valid_empty_inventory(self) -> None:
        empty = mock.Mock(returncode=0, stdout="[]\n", stderr="")
        with mock.patch.object(
            eval_codex_runtime.subprocess, "run", return_value=empty
        ) as run:
            eval_codex_runtime.assert_no_configured_mcp("codex")
        command = run.call_args.args[0]
        self.assertEqual(["mcp", "list", "--json"], command[-3:])
        self.assertIn(
            f'openai_base_url="{eval_codex_runtime.SUBSCRIPTION_BASE_URL}"', command
        )

        invalid_results = (
            (
                mock.Mock(returncode=0, stdout='[{"name": "managed"}]', stderr=""),
                "configured MCP",
            ),
            (mock.Mock(returncode=0, stdout="{}", stderr=""), "JSON list"),
            (mock.Mock(returncode=0, stdout="not-json", stderr=""), "valid JSON"),
            (mock.Mock(returncode=2, stdout="", stderr="refused"), "could not be checked"),
        )
        for proc, message in invalid_results:
            with self.subTest(message=message), mock.patch.object(
                eval_codex_runtime.subprocess, "run", return_value=proc
            ), self.assertRaisesRegex(eval_codex_runtime.CodexRuntimeError, message):
                eval_codex_runtime.assert_no_configured_mcp("codex")

    def test_capacity_failure_aborts_instead_of_becoming_a_contract_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = mock.Mock(
                returncode=1,
                stdout=json.dumps({
                    "type": "turn.failed",
                    "error": {"type": "usage_limit_reached", "message": "unavailable"},
                }),
                stderr="",
            )
            with mock.patch.object(eval_codex_runtime.subprocess, "run", return_value=proc):
                with self.assertRaises(eval_codex_runtime.SessionUnavailable):
                    eval_codex_runtime.run_session(
                        "task prompt",
                        20,
                        agent="sde-agents:homelab-engineer",
                        developer_instructions="Exact role instructions.",
                        model="gpt-5.6-terra",
                        reasoning_effort="medium",
                        executable="codex",
                        scratch_root=root / "scratch",
                    )

    def test_timeout_capacity_failure_aborts_from_partial_streams(self) -> None:
        variants = (
            (
                "structured stdout",
                json.dumps({
                    "type": "turn.failed",
                    "error": {"type": "usage_limit_reached", "message": "unavailable"},
                }),
                "",
            ),
            ("stderr marker", "", "You have reached your usage limit"),
        )
        for label, stdout, stderr in variants:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                failure = eval_codex_runtime.subprocess.TimeoutExpired(
                    cmd=["codex"], timeout=20, output=stdout, stderr=stderr
                )
                with mock.patch.object(
                    eval_codex_runtime.subprocess, "run", side_effect=failure
                ), self.assertRaises(eval_codex_runtime.SessionUnavailable):
                    eval_codex_runtime.run_session(
                        "task prompt",
                        20,
                        agent="sde-agents:homelab-engineer",
                        developer_instructions="Exact role instructions.",
                        model="gpt-5.6-terra",
                        reasoning_effort="medium",
                        executable="codex",
                        scratch_root=Path(tmp) / "scratch",
                    )

    def test_cli_version_is_pinned_before_sessions(self) -> None:
        proc = mock.Mock(returncode=0, stdout="codex-cli 0.148.0\n", stderr="")
        with mock.patch.object(eval_codex_runtime.subprocess, "run", return_value=proc):
            with self.assertRaisesRegex(eval_codex_runtime.CodexRuntimeError, "0.147.0"):
                eval_codex_runtime.require_supported_cli("codex")

    def test_profile_capture_tracks_only_selected_agents_and_keeps_execution_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            selected = self._profile(root)
            unrelated = self._profile(root, "code-reviewer")
            agents = ["sde-agents:homelab-engineer"]
            profiles, original = eval_codex_runtime.capture_profiles(root, agents)

            unrelated.write_text(
                unrelated.read_text(encoding="utf-8").replace("Exact role", "Other role"),
                encoding="utf-8",
            )
            self.assertEqual(
                original["sha256"],
                eval_codex_runtime.profile_identity(root, agents)["sha256"],
            )

            selected.write_text(
                selected.read_text(encoding="utf-8").replace("Exact role", "Changed role"),
                encoding="utf-8",
            )
            self.assertEqual(
                "Exact role instructions.",
                profiles["sde-agents:homelab-engineer"]["developer_instructions"],
            )

            self.assertNotEqual(
                original["sha256"],
                eval_codex_runtime.profile_identity(root, agents)["sha256"],
            )

    def test_codex_home_with_ambient_instructions_refuses_before_spend(self) -> None:
        with self.assertRaisesRegex(eval_codex_runtime.CodexRuntimeError, "dedicated CODEX_HOME"):
            eval_codex_runtime.assert_clean_subscription_context(environ={})
        with self.assertRaisesRegex(eval_codex_runtime.CodexRuntimeError, "absolute CODEX_HOME"):
            eval_codex_runtime.assert_clean_subscription_context(
                environ={"CODEX_HOME": "relative-home"}
            )
        for variable in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN"):
            with self.subTest(variable=variable), self.assertRaisesRegex(
                eval_codex_runtime.CodexRuntimeError, variable
            ):
                eval_codex_runtime.assert_clean_subscription_context(
                    environ={variable: "present-but-never-read"}
                )
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            eval_codex_runtime.assert_clean_subscription_context(
                environ={"CODEX_HOME": str(home)}
            )
            (home / "AGENTS.md").write_text("ambient", encoding="utf-8")
            with self.assertRaisesRegex(
                eval_codex_runtime.CodexRuntimeError, "instruction/config-clean CODEX_HOME"
            ):
                eval_codex_runtime.assert_clean_subscription_context(
                    environ={"CODEX_HOME": str(home)}
                )
            (home / "AGENTS.md").unlink()
            (home / "config.toml").write_text("user config", encoding="utf-8")
            with self.assertRaisesRegex(
                eval_codex_runtime.CodexRuntimeError, "instruction/config-clean CODEX_HOME"
            ):
                eval_codex_runtime.assert_clean_subscription_context(
                    environ={"CODEX_HOME": str(home)}
                )
            (home / "config.toml").unlink()
            (home / "managed_config.toml").write_text("managed", encoding="utf-8")
            with self.assertRaisesRegex(
                eval_codex_runtime.CodexRuntimeError, "managed_config.toml"
            ):
                eval_codex_runtime.assert_clean_subscription_context(
                    environ={"CODEX_HOME": str(home)}
                )


if __name__ == "__main__":
    unittest.main()
