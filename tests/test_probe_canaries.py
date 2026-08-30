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
import tempfile
import unittest
from pathlib import Path
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

    def test_a_root_session_reports_the_workflow_probe_inconclusive_not_failed(self) -> None:
        """PROBE-003: one environment condition read as five fleet defects.

        The five workflow assertions all need `--permission-mode bypassPermissions`, which Claude
        Code refuses under root, so the workflow never launches and every assertion fails as a
        cascade. Telling a broken fleet from a broken environment is the probe's job, and
        INCONCLUSIVE is its documented verdict for the second — reported once, because restating
        a single cause five times is the noise that verdict exists to remove.
        """
        probe = probe_plugin.Probe()
        with (
            mock.patch.object(probe_plugin.os, "geteuid", return_value=0, create=True),
            mock.patch.object(probe_plugin, "run") as run,
            mock.patch.object(probe_plugin.shutil, "copytree") as copytree,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            probe_plugin.probe_workflow_contract(probe)

        run.assert_not_called()
        copytree.assert_not_called()
        self.assertIn("INCONCLUSIVE", output.getvalue())
        statuses = [status for status, *_ in probe.results]
        self.assertEqual([probe_plugin.SKIP], statuses)
        self.assertNotIn(probe_plugin.FAIL, statuses)

    def test_an_uncorrelated_spawn_leaves_the_canaries_unevaluated_not_failed(self) -> None:
        """PROBE-002: "the canary is absent" and "the oracle saw nothing" are different findings.

        The 2026-08-17 run scored 12/19 with both preload canaries failing, and could not say
        whether that was a real regression or the oracle failing to consume an async agent
        launch's result — a signature the 2026-07-30 audit's F-03 had already reproduced. Both
        rendered as FAIL, so settling it needed another paid run. `agent_spawn_results` returning
        nothing now means unevaluated; a result the oracle DID observe, with no canary in it, is
        the real preload failure.
        """
        spawn = json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "toolu_async", "name": "Agent",
                "input": {"subagent_type": "sde-agents:sde-fullstack", "prompt": "build it"},
            }]},
        })
        # The spawn is never correlated to a tool_result, which is the async-launch shape.
        self.assertEqual([], probe_plugin.agent_spawn_results(spawn, "sde-agents:sde-fullstack"))
        # A correlated result with no canary stays a real, distinguishable failure.
        answered = spawn + "\n" + json.dumps({
            "type": "user",
            "message": {"content": [{
                "type": "tool_result", "tool_use_id": "toolu_async",
                "content": "done, no craft content quoted",
            }]},
        })
        results = probe_plugin.agent_spawn_results(answered, "sde-agents:sde-fullstack")
        self.assertEqual(1, len(results))
        self.assertNotIn(probe_plugin.BACKEND_CANARY, results[0])

    def test_an_errored_agent_result_is_not_an_observation(self) -> None:
        """PR #147 round 2: an errored tool_result was read as the agent's answer.

        A timeout or launch failure returns `is_error: true` with error text. Returning that text
        made both preload canaries FAIL — concluding the skills were absent from the agent's
        context when nothing had run. It now reaches the caller's empty-result branch, which
        reports INCONCLUSIVE.
        """
        spawn = json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "toolu_err", "name": "Agent",
                "input": {"subagent_type": "sde-agents:sde-fullstack", "prompt": "build"},
            }]},
        })

        def result(payload: dict) -> list[str]:
            return probe_plugin.agent_spawn_results(
                spawn + "\n" + json.dumps({"type": "user", "message": {"content": [payload]}}),
                "sde-agents:sde-fullstack",
            )

        self.assertEqual([], result({
            "type": "tool_result", "tool_use_id": "toolu_err", "is_error": True,
            "content": "Error: agent timed out",
        }))
        observed = result({
            "type": "tool_result", "tool_use_id": "toolu_err",
            "content": f"{probe_plugin.BACKEND_CANARY} and more",
        })
        self.assertEqual(1, len(observed))

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


class ProbeInconclusiveReportingTests(unittest.TestCase):
    """The epilogue must not assert one cause for every inconclusive check.

    Codex review on #151: `report()` attributed every SKIP to Claude Code's sandbox refusing the
    command and told the operator to re-run outside a Claude Code session. That was already wrong
    for a command the agent never attempted and for PROBE-002's uncorrelated spawn; the
    correlation-gap SKIP added in this PR makes it wrong a third way. A probe that prints an
    accurate per-check cause and then contradicts it in the summary sends the operator to fix
    the wrong thing.
    """

    @staticmethod
    def _report(*results: tuple[str, str, str]) -> tuple[int, str]:
        probe = probe_plugin.Probe()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            for status, label, detail in results:
                probe.check(status, label, detail)
            code = probe.report()
        return code, buffer.getvalue()

    def test_the_epilogue_does_not_blame_the_sandbox_for_a_correlation_gap(self) -> None:
        code, out = self._report((
            probe_plugin.SKIP,
            "the guard DENIED a --agent main session's denylisted command",
            "the call was emitted but no tool_result ever correlated to it, so the oracle saw "
            "no verdict: the session exited or truncated first.",
        ))
        self.assertEqual(2, code)
        self.assertIn("no tool_result ever correlated", out, "the real cause must still print")
        self.assertNotIn(
            "Claude Code's own sandbox refused the command",
            out,
            "the summary asserted a cause this check did not report",
        )

    def test_a_sandbox_refusal_still_gets_its_actionable_advice(self) -> None:
        _code, out = self._report((
            probe_plugin.SKIP,
            "the guard DENIED the reviewer's denylisted command",
            "Claude Code's own permission layer refused it before the guard's verdict mattered.",
        ))
        self.assertIn("plain terminal", out)

    def test_a_clean_run_prints_no_inconclusive_epilogue(self) -> None:
        code, out = self._report((probe_plugin.PASS, "everything held", ""))
        self.assertEqual(0, code)
        self.assertNotIn("UNPROVEN", out)


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

        self.assertEqual({"echo GOOD": ["good result"]}, probe_plugin.bash_results(transcript))

    def test_an_uncorrelated_bash_call_is_inconclusive_not_an_unguarded_run(self) -> None:
        """PROBE-004: a Bash call with no correlated tool_result proves nothing about the guard.

        `bash_results` supplied "" for such a call, so `result_for` returned an empty string
        rather than signalling the gap; the guard checks then fell through to their FAIL branch
        and recorded "the command RAN UNGUARDED" with an empty Result. A session that emitted
        the call and then exited nonzero or truncated is the probe's INCONCLUSIVE case - the
        same distinction PROBE-002 and PROBE-003 already draw.
        """
        transcript = json.dumps({"message": {"content": [{
            "type": "tool_use", "id": "bash-uncorrelated", "name": "Bash",
            "input": {"command": "find . -exec AGENTFLAG_PROBE"},
        }]}})

        pairs = probe_plugin.bash_results(transcript)
        self.assertEqual({"find . -exec AGENTFLAG_PROBE": [None]}, pairs)

        attempted, result = probe_plugin.result_for("AGENTFLAG_PROBE", pairs)
        self.assertTrue(attempted, "the call WAS emitted; the session simply never answered it")
        self.assertEqual([], probe_plugin.observed(result),
                         "no correlated result, so there is nothing to grade")

    def test_a_repeated_command_keeps_its_observed_result_over_a_later_gap(self) -> None:
        """Codex review on #151: the map is command-keyed, so a duplicate call overwrote evidence.

        An agent that retries the same denylisted command produces two `tool_use` ids for one
        command string. If the first RAN and returned a result, and the retry was emitted before
        the transcript truncated, later-wins replaced the observed result with the correlation
        gap -- and the guard check downgraded a detected FAILURE to INCONCLUSIVE. A gap is the
        absence of evidence and must never displace evidence.
        """
        def transcript(*blocks: dict) -> str:
            return json.dumps({"message": {"content": list(blocks)}})

        ran_then_truncated = transcript(
            {"type": "tool_use", "id": "call-1", "name": "Bash",
             "input": {"command": "find . -exec REVIEWER_PROBE"}},
            {"type": "tool_result", "tool_use_id": "call-1", "content": "ran unguarded"},
            {"type": "tool_use", "id": "call-2", "name": "Bash",
             "input": {"command": "find . -exec REVIEWER_PROBE"}},
        )
        self.assertEqual(
            {"find . -exec REVIEWER_PROBE": ["ran unguarded", None]},
            probe_plugin.bash_results(ran_then_truncated),
            "the observed result is the evidence; the retry's gap must not displace it",
        )
        self.assertEqual(
            ["ran unguarded"],
            probe_plugin.observed(
                probe_plugin.result_for(
                    "REVIEWER_PROBE", probe_plugin.bash_results(ran_then_truncated)
                )[1]
            ),
        )

        truncated_then_ran = transcript(
            {"type": "tool_use", "id": "call-1", "name": "Bash",
             "input": {"command": "find . -exec REVIEWER_PROBE"}},
            {"type": "tool_use", "id": "call-2", "name": "Bash",
             "input": {"command": "find . -exec REVIEWER_PROBE"}},
            {"type": "tool_result", "tool_use_id": "call-2", "content": "ran unguarded"},
        )
        self.assertEqual(
            {"find . -exec REVIEWER_PROBE": [None, "ran unguarded"]},
            probe_plugin.bash_results(truncated_then_ran),
            "order must not decide it either: the correlated result wins from either side",
        )

    def test_every_correlated_result_is_kept_for_a_repeated_command(self) -> None:
        """Retires the merge-precedence tests: there is no merge left to get wrong.

        Two rounds of review killed two opposite precedences -- first-wins hid a run behind a
        denial, unguarded-wins hid a denial behind a run -- because the reviewer check and the
        main-loop check read the SAME evidence with opposite polarity. One value cannot serve
        both, so the parser now returns all of them and each check decides. The old tests pinned
        a decision that no longer exists; these pin the evidence and the two verdicts instead.
        """
        def transcript(*results: str) -> str:
            blocks = []
            for index, body in enumerate(results):
                blocks.append({"type": "tool_use", "id": f"c{index}", "name": "Bash",
                               "input": {"command": "find . -exec PROBE"}})
                if body is not None:
                    blocks.append({"type": "tool_result", "tool_use_id": f"c{index}",
                                   "content": body})
            return json.dumps({"message": {"content": blocks}})

        RAN = "total 12 drwxr-xr-x repo"
        both = probe_plugin.bash_results(transcript(probe_plugin.GUARD_DENY, RAN))
        self.assertEqual({"find . -exec PROBE": [probe_plugin.GUARD_DENY, RAN]}, both)
        self.assertEqual(
            both, probe_plugin.bash_results(transcript(probe_plugin.GUARD_DENY, RAN)),
            "order is preserved, not resolved",
        )

    def test_each_check_reads_the_shared_evidence_with_its_own_polarity(self) -> None:
        """The reviewer must be denied; the main loop must not. Same input, opposite verdicts."""
        RAN = "total 12 drwxr-xr-x repo"
        DENY = probe_plugin.GUARD_DENY

        for label, results in (
            ("denied then ran", [DENY, RAN]),
            ("ran then denied", [RAN, DENY]),
        ):
            with self.subTest(order=label):
                seen = probe_plugin.observed(results)
                # Reviewer polarity: any unguarded run is the failure.
                self.assertTrue(
                    probe_plugin.unguarded_runs(seen),
                    "a guard that allowed one attempt has not held",
                )
                # Main-loop polarity: any denial is the failure.
                self.assertTrue(
                    [r for r in seen if DENY in r],
                    "the guard caught the user's own Bash at least once",
                )

        denied_twice = probe_plugin.observed([DENY, DENY])
        self.assertEqual([], probe_plugin.unguarded_runs(denied_twice),
                         "denied twice is denied -- the aggregate must not invent a failure")

        gap_only = probe_plugin.observed([None, None])
        self.assertEqual([], gap_only, "a correlation gap is never evidence in either direction")

    def test_a_command_never_attempted_stays_distinct_from_one_never_answered(self) -> None:
        """The two INCONCLUSIVE causes need different operator actions, so they stay separable."""
        self.assertEqual((False, []), probe_plugin.result_for("ABSENT_PROBE", {}))

    def test_a_correlated_empty_result_remains_a_real_gradeable_answer(self) -> None:
        """An empty tool_result is the command running and printing nothing - that IS evidence.

        The repair must not swallow it: only the absence of any correlated result is the gap.
        """
        transcript = json.dumps({"message": {"content": [
            {"type": "tool_use", "id": "bash-empty", "name": "Bash",
             "input": {"command": "find . -exec MAINLOOP_PROBE"}},
            {"type": "tool_result", "tool_use_id": "bash-empty", "content": ""},
        ]}})

        pairs = probe_plugin.bash_results(transcript)
        self.assertEqual({"find . -exec MAINLOOP_PROBE": [""]}, pairs)
        self.assertEqual((True, [""]), probe_plugin.result_for("MAINLOOP_PROBE", pairs))

    def test_a_canary_leak_needs_an_observed_result_not_a_correlation_gap(self) -> None:
        """PROBE-004 fallout: a None body is a gap, not a leak, and must not be searched.

        Once `bash_results` reports an uncorrelated call as None, every consumer that treats its
        values as text is a crash waiting for a truncated session - `CANARY in None` raises
        TypeError. It is also wrong on the merits: the oracle saw no output for that call, so
        there is nothing to have leaked.
        """
        canaries = (probe_plugin.BACKEND_CANARY, probe_plugin.FRONTEND_CANARY)

        self.assertEqual([], probe_plugin.canary_leaks({"echo hi": [None]}, canaries))
        self.assertEqual([], probe_plugin.canary_leaks({"echo hi": ["clean output"]}, canaries))
        self.assertEqual(
            ["cat backend-craft/SKILL.md"],
            probe_plugin.canary_leaks(
                {
                    "cat backend-craft/SKILL.md": [f"...{probe_plugin.BACKEND_CANARY}..."],
                    "echo hi": [None],
                },
                canaries,
            ),
        )

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
        self.assertEqual({"echo PROBE": ["bash ok"]}, probe_plugin.bash_results(transcript))
        self.assertTrue(probe_plugin.spawn_succeeded(transcript, "sde-agents:sde-fullstack"))
        self.assertEqual(
            ["agent ok"],
            probe_plugin.agent_spawn_results(transcript, "sde-agents:sde-fullstack"),
        )


class GateProbeTargetInertness(unittest.TestCase):
    """The gate probe's MAIN arm deliberately RUNS `docker compose ... up -d` under dontAsk.

    Risk hypothesis: that is harmless ONLY while the referenced compose file cannot be loaded.
    The path is fixed and predictable, and the probe's comment asserted it "cannot exist" while
    nothing enforced it — so a file sitting at that path would turn the deny/run differential
    into a real container start against the operator's Docker daemon, with the probe still
    printing a green MAIN leg. An unenforceable safety comment is the failure this watches.
    """

    def test_an_existing_target_is_reported_so_the_probe_can_refuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            present = str(Path(tmp) / "docker-compose.yml")
            Path(present).write_text("services: {}\n", encoding="utf-8")
            absent = str(Path(tmp) / "no-such" / "docker-compose.yml")
            self.assertIsNone(probe_plugin.existing_path([absent]))
            self.assertEqual(present, probe_plugin.existing_path([absent, present]))

    def test_the_checked_paths_are_the_paths_the_command_runs(self) -> None:
        # A guard that inspects a different path than the command uses enforces nothing.
        targets = probe_plugin.gate_targets()
        self.assertEqual(2, len(targets))
        for marker, target in zip(("AGENT", "MAIN"), targets):
            with self.subTest(marker=marker):
                self.assertIn(target, probe_plugin.GATE_CMD.format(marker=marker))
                self.assertIn(marker, target)


if __name__ == "__main__":
    unittest.main()
