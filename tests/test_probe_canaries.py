"""Guards the canary strings scripts/probe_plugin.py depends on to prove skill preloading.

BACKEND_CANARY (skills/backend-craft/SKILL.md, under "## Contract first") and FRONTEND_CANARY
(skills/frontend-craft/SKILL.md, under "## Visual character") are embedded in ordinary skill
content, but the probe's oracle for "was this skill preloaded, not read" is exactly "did this
string appear in the transcript" -- see scripts/probe_plugin.py's "sde-fullstack's craft skills
are PRELOADED, not read" section. A copy-edit to either SKILL.md would silently disarm that
check: the probe would still run, still print PASS/FAIL, and never say why the canary stopped
matching. Two layers hold this together: a marker comment beside each canary in the skill file
warns the editor at the edit site, and this test is the tripwire behind the warning -- asserted
through the probe's own constants so the probe and this guard cannot drift apart.
"""
from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest import mock

from scripts import probe_plugin
from tests.support import REPO


class ProbeCanaryTests(unittest.TestCase):
    def test_help_exits_before_any_live_probe_or_workspace_change(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(probe_plugin, "run") as run,
            mock.patch.object(probe_plugin, "_remove_workspace") as remove_workspace,
            contextlib.redirect_stdout(output),
            self.assertRaises(SystemExit) as raised,
        ):
            probe_plugin.main(["--help"])

        self.assertEqual(0, raised.exception.code)
        self.assertIn("usage:", output.getvalue())
        run.assert_not_called()
        remove_workspace.assert_not_called()

    def test_backend_craft_canary_is_present(self) -> None:
        # Asserted via the probe's own constant, not a copied literal: with a duplicate string
        # here, a probe-side canary change would fail live probes while this tripwire stayed
        # green — the exact split-truth this test exists to prevent.
        text = (REPO / "skills" / "backend-craft" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            probe_plugin.BACKEND_CANARY,
            text,
            "scripts/probe_plugin.py quotes this canary to prove backend-craft was preloaded -- "
            "do not remove or reword it without updating the probe",
        )

    def test_frontend_craft_canary_is_present(self) -> None:
        text = (REPO / "skills" / "frontend-craft" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            probe_plugin.FRONTEND_CANARY,
            text,
            "scripts/probe_plugin.py quotes this canary to prove frontend-craft was preloaded -- "
            "do not remove or reword it without updating the probe",
        )


class ProbeTranscriptParserTests(unittest.TestCase):
    def test_tool_consumers_ignore_non_object_tool_input(self) -> None:
        transcript = json.dumps(
            {
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "bash-bad",
                            "name": "Bash",
                            "input": "legacy string input",
                        }
                    ]
                }
            }
        )

        self.assertEqual([], probe_plugin.tool_calls(transcript))
        self.assertEqual({}, probe_plugin.bash_results(transcript))

    def test_bash_results_ignore_non_string_commands_and_correlation_ids(self) -> None:
        transcript = "\n".join(
            (
                json.dumps({
                    "message": {"content": [{
                        "type": "tool_use", "id": "bad-command", "name": "Bash",
                        "input": {"command": ["not", "a", "string"]},
                    }]}
                }),
                json.dumps({
                    "message": {"content": [{
                        "type": "tool_use", "id": ["bad-id"], "name": "Bash",
                        "input": {"command": "echo BAD"},
                    }]}
                }),
                json.dumps({
                    "message": {"content": [{
                        "type": "tool_result", "tool_use_id": ["bad-result-id"],
                        "content": "ignored",
                    }]}
                }),
                json.dumps({
                    "message": {"content": [
                        {
                            "type": "tool_use", "id": "bash-good", "name": "Bash",
                            "input": {"command": "echo GOOD"},
                        },
                        {
                            "type": "tool_result", "tool_use_id": "bash-good",
                            "content": "good result",
                        },
                    ]}
                }),
            )
        )

        self.assertEqual({"echo GOOD": "good result"}, probe_plugin.bash_results(transcript))

    def test_agent_consumers_ignore_non_object_tool_input(self) -> None:
        transcript = json.dumps(
            {
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "agent-bad",
                            "name": "Agent",
                            "input": "sde-agents:sde-fullstack",
                        },
                        {
                            "type": "tool_result",
                            "tool_use_id": "agent-bad",
                            "content": "not a valid spawn",
                            "is_error": False,
                        },
                    ]
                }
            }
        )

        self.assertFalse(
            probe_plugin.spawn_succeeded(transcript, "sde-agents:sde-fullstack")
        )
        self.assertEqual(
            [],
            probe_plugin.agent_spawn_results(transcript, "sde-agents:sde-fullstack"),
        )

        malformed_ids = "\n".join((
            json.dumps({
                "message": {"content": [{
                    "type": "tool_use",
                    "id": ["bad-agent-id"],
                    "name": "Agent",
                    "input": {"subagent_type": "sde-agents:sde-fullstack"},
                }]}
            }),
            json.dumps({
                "message": {"content": [{
                    "type": "tool_result",
                    "tool_use_id": ["bad-result-id"],
                    "content": "ignored",
                    "is_error": False,
                }]}
            }),
            json.dumps({
                "message": {"content": [
                    {
                        "type": "tool_use",
                        "id": "agent-good",
                        "name": "Agent",
                        "input": {"subagent_type": "sde-agents:sde-fullstack"},
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "agent-good",
                        "content": "valid spawn",
                        "is_error": False,
                    },
                ]}
            }),
        ))

        self.assertTrue(
            probe_plugin.spawn_succeeded(
                malformed_ids, "sde-agents:sde-fullstack"
            )
        )
        self.assertEqual(
            ["valid spawn"],
            probe_plugin.agent_spawn_results(
                malformed_ids, "sde-agents:sde-fullstack"
            ),
        )

    def test_spawn_success_prefers_the_structured_agent_target(self) -> None:
        transcript = json.dumps({
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "agent-wrong",
                        "name": "Agent",
                        "input": {
                            "subagent_type": "sde-agents:code-reviewer",
                            "prompt": "Discuss sde-agents:sde-fullstack.",
                        },
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "agent-wrong",
                        "content": "review complete",
                        "is_error": False,
                    },
                ]
            }
        })

        self.assertFalse(
            probe_plugin.spawn_succeeded(transcript, "sde-agents:sde-fullstack")
        )

    def test_consumers_skip_invalid_shapes_without_losing_correlations(self) -> None:
        transcript = "\n".join(
            (
                "not json",
                "42",
                json.dumps({"message": "diagnostic"}),
                json.dumps(
                    {
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "bash-1",
                                    "name": "Bash",
                                    "input": {"command": "echo PROBE"},
                                },
                                {
                                    "type": "tool_use",
                                    "id": "agent-1",
                                    "name": "Agent",
                                    "input": {
                                        "subagent_type": "sde-agents:sde-fullstack"
                                    },
                                },
                                "non-object block",
                            ]
                        }
                    }
                ),
                json.dumps(
                    {
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "bash-1",
                                    "content": "bash ok",
                                },
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "agent-1",
                                    "content": [{"text": "agent ok"}],
                                    "is_error": False,
                                },
                            ]
                        }
                    }
                ),
            )
        )

        self.assertEqual(
            ["bash-1", "agent-1"],
            [call["id"] for call in probe_plugin.tool_calls(transcript)],
        )
        self.assertEqual({"echo PROBE": "bash ok"}, probe_plugin.bash_results(transcript))
        self.assertTrue(probe_plugin.spawn_succeeded(transcript, "sde-agents:sde-fullstack"))
        self.assertEqual(
            ["agent ok"],
            probe_plugin.agent_spawn_results(transcript, "sde-agents:sde-fullstack"),
        )


if __name__ == "__main__":
    unittest.main()
