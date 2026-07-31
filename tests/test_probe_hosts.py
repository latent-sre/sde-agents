from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts import probe_hosts


REPO = Path(__file__).resolve().parents[1]


class ProbeHostsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = probe_hosts.load_manifest(probe_hosts.DEFAULT_MANIFEST)

    def _sol_lane(self) -> dict[str, object]:
        return next(
            lane for lane in self.manifest["lanes"] if lane["id"] == "codex-gpt-5.6-sol"
        )

    def test_manifest_requires_exact_sol_lane_and_preserved_effort(self) -> None:
        lane = self._sol_lane()
        self.assertEqual("gpt-5.6-sol", lane["model"])
        self.assertEqual("high", lane["reasoning_effort"])
        self.assertEqual("read-only", lane["sandbox"])

        missing = copy.deepcopy(self.manifest)
        missing["lanes"] = [item for item in missing["lanes"] if item["id"] != lane["id"]]
        with self.assertRaisesRegex(probe_hosts.ConformanceError, "exactly one"):
            probe_hosts.validate_manifest(missing)

        wrong_effort = copy.deepcopy(self.manifest)
        next(
            item for item in wrong_effort["lanes"] if item["id"] == lane["id"]
        )["reasoning_effort"] = "medium"
        with self.assertRaisesRegex(probe_hosts.ConformanceError, "explicit high"):
            probe_hosts.validate_manifest(wrong_effort)

    def test_codex_command_pins_model_effort_sandbox_and_clean_conditions(self) -> None:
        lane = self._sol_lane()
        command = probe_hosts.build_codex_command(
            "C:/tools/codex.exe",
            REPO,
            lane,
            "fixed prompt",
        )
        self.assertEqual("fixed prompt", command[-1])
        self.assertEqual("gpt-5.6-sol", command[command.index("--model") + 1])
        self.assertEqual("read-only", command[command.index("--sandbox") + 1])
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertNotIn("--enable", command)
        self.assertFalse(any("reasoning.mode" in item or "pro_mode" in item for item in command))

    def test_codex_json_parser_extracts_model_message_and_usage(self) -> None:
        transcript = "\n".join(
            (
                json.dumps({"type": "thread.started", "model": "gpt-5.6-sol"}),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "agent_message",
                            "text": '{"marker":"SDE_FLEET_BASELINE_OK"}',
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {"input_tokens": 10, "output_tokens": 4},
                    }
                ),
            )
        )
        parsed = probe_hosts.parse_codex_jsonl(transcript)
        self.assertEqual(["gpt-5.6-sol"], parsed["observed_models"])
        self.assertEqual('{"marker":"SDE_FLEET_BASELINE_OK"}', parsed["last_message"])
        self.assertEqual(10, parsed["usage"]["input_tokens"])

    def test_model_lane_passes_only_the_deterministic_oracle(self) -> None:
        lane = self._sol_lane()
        case = next(case for case in self.manifest["cases"] if case["id"] == lane["case"])
        calls: list[tuple[str, ...]] = []

        def runner(argv, cwd, timeout):
            calls.append(tuple(argv))
            if tuple(argv[-1:]) == ("--version",):
                return probe_hosts.CommandResult(0, "codex-cli 0.test\n", "")
            transcript = "\n".join(
                (
                    json.dumps({"type": "thread.started", "model": "gpt-5.6-sol"}),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "agent_message",
                                "text": json.dumps(case["expected"]),
                            },
                        }
                    ),
                )
            )
            return probe_hosts.CommandResult(0, transcript, "")

        result = probe_hosts._model_lane(
            REPO,
            lane,
            case,
            which=lambda command: "C:/tools/codex.exe",
            runner=runner,
        )
        self.assertEqual("pass", result.verdict)
        self.assertEqual("gpt-5.6-sol", result.requested_model)
        self.assertEqual(["gpt-5.6-sol"], result.observed_models)
        self.assertEqual("high", result.reasoning_effort)
        self.assertEqual([], result.details["command_conditions"]["optional_features_enabled"])
        self.assertEqual(2, len(calls))

    def test_model_access_failure_is_inconclusive_not_passed(self) -> None:
        lane = self._sol_lane()
        case = next(case for case in self.manifest["cases"] if case["id"] == lane["case"])

        def runner(argv, cwd, timeout):
            if tuple(argv[-1:]) == ("--version",):
                return probe_hosts.CommandResult(0, "codex-cli 0.test\n", "")
            return probe_hosts.CommandResult(1, "", "model access is not available")

        result = probe_hosts._model_lane(
            REPO,
            lane,
            case,
            which=lambda command: "C:/tools/codex.exe",
            runner=runner,
        )
        self.assertEqual("inconclusive", result.verdict)

    def test_unavailable_cli_is_skip_and_static_lanes_remain_separate(self) -> None:
        report = probe_hosts.run_manifest(
            REPO,
            self.manifest,
            lane_pattern="*-static",
            which=lambda command: None,
        )
        self.assertEqual(4, len(report["results"]))
        self.assertEqual(
            {"claude", "codex", "copilot", "vscode"},
            {result["host"] for result in report["results"]},
        )
        self.assertTrue(all(result["verdict"] == "pass" for result in report["results"]))

        discovery = probe_hosts.run_manifest(
            REPO,
            self.manifest,
            lane_pattern="copilot-discovery",
            which=lambda command: None,
        )
        self.assertEqual("skip", discovery["results"][0]["verdict"])

    def test_readable_plugin_inventory_without_fleet_is_inconclusive(self) -> None:
        def runner(argv, cwd, timeout):
            if tuple(argv[-1:]) == ("--version",):
                return probe_hosts.CommandResult(0, "claude 2.test\n", "")
            if tuple(argv[-2:]) == ("plugin", "list"):
                return probe_hosts.CommandResult(0, "other-plugin 1.0\n", "")
            self.fail(f"unexpected command: {argv}")

        report = probe_hosts.run_manifest(
            REPO,
            self.manifest,
            lane_pattern="claude-discovery",
            which=lambda command: "C:/tools/claude.exe",
            runner=runner,
        )
        result = report["results"][0]
        self.assertEqual("inconclusive", result["verdict"])
        self.assertFalse(result["details"]["fleet_plugin_present"])
        self.assertIn("not installed", result["details"]["reason"])


if __name__ == "__main__":
    unittest.main()
