"""Offline tests for scripts/eval_routing.py — the pure grading logic, no live sessions.

The runner's live arm is inherently non-deterministic (it drives real model sessions), so the parts
that MUST be correct — did we detect the right component from a transcript, did we score a case the
right way — are the pure functions, and those are tested here against synthetic transcripts. A
parsing bug here would silently mis-grade every routing eval, so it gets the deterministic coverage
the live arm can't.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from scripts import eval_routing

REPO = Path(__file__).resolve().parents[1]


def transcript(*tool_uses: dict) -> str:
    """A minimal stream-json transcript: one assistant message carrying the given tool_use blocks."""
    import json
    event = {"type": "assistant", "message": {"content": list(tool_uses)}}
    return json.dumps(event)


def skill_use(name: str, tool_id: str = "t1") -> dict:
    return {"type": "tool_use", "id": tool_id, "name": "Skill", "input": {"command": name}}


def agent_use(name: str, tool_id: str = "t1") -> dict:
    return {"type": "tool_use", "id": tool_id, "name": "Agent", "input": {"subagent_type": name, "prompt": "go"}}


def tool_result(tool_id: str, is_error: bool) -> dict:
    return {"type": "tool_result", "tool_use_id": tool_id, "is_error": is_error}


class ComponentDetectionTest(unittest.TestCase):
    def test_detects_namespaced_skill(self) -> None:
        self.assertEqual(
            {"prompt-craft"}, eval_routing.components_fired(transcript(skill_use("sde-agents:prompt-craft")))
        )

    def test_detects_bare_agent_spawn(self) -> None:
        self.assertEqual(
            {"prompt-engineer"}, eval_routing.components_fired(transcript(agent_use("prompt-engineer")))
        )

    def test_detects_multiple_components(self) -> None:
        fired = eval_routing.components_fired(
            transcript(skill_use("sde-agents:backend-craft", tool_id="a"), agent_use("sde-agents:sde-fullstack", tool_id="b"))
        )
        self.assertEqual({"backend-craft", "sde-fullstack"}, fired)

    def test_prose_mention_is_not_a_firing(self) -> None:
        # The model naming a component in TEXT is not the component firing. Only tool calls count.
        prose = {"type": "text", "text": "You could use prompt-craft or spawn prompt-engineer for this."}
        self.assertEqual(set(), eval_routing.components_fired(transcript(prose)))

    def test_non_fleet_tool_is_ignored(self) -> None:
        read = {"type": "tool_use", "name": "Read", "input": {"file_path": "prompt-craft.md"}}
        self.assertEqual(set(), eval_routing.components_fired(transcript(read)))

    def test_unknown_name_in_skill_input_is_ignored(self) -> None:
        self.assertEqual(set(), eval_routing.components_fired(transcript(skill_use("some-other-skill"))))

    def test_malformed_lines_do_not_crash(self) -> None:
        self.assertEqual(set(), eval_routing.components_fired("not json\n{bad\n"))

    def test_errored_tool_result_does_not_count_as_fired(self) -> None:
        # A failed skill invocation (is_error: true) is NOT the skill firing — counting it would
        # produce false PASS results on positives whose spawn failed.
        line1 = transcript(skill_use("sde-agents:prompt-craft", tool_id="tu_1"))
        line2 = transcript(tool_result("tu_1", is_error=True))
        self.assertEqual(set(), eval_routing.components_fired(line1 + "\n" + line2))

    def test_successful_tool_result_counts_as_fired(self) -> None:
        line1 = transcript(agent_use("prompt-engineer", tool_id="tu_2"))
        line2 = transcript(tool_result("tu_2", is_error=False))
        self.assertEqual({"prompt-engineer"}, eval_routing.components_fired(line1 + "\n" + line2))

    def test_missing_tool_result_still_counts_as_fired(self) -> None:
        # Streams can end before the result comes back (timeout); absence of an error is not an error.
        self.assertEqual(
            {"prompt-craft"},
            eval_routing.components_fired(transcript(skill_use("sde-agents:prompt-craft", tool_id="tu_3"))),
        )


class ScoringTest(unittest.TestCase):
    MEMBERS = {"prompt-craft", "prompt-engineer"}

    def _runs(self, *fired_lists) -> list[dict]:
        return [
            {"fired": list(f), "tokens": None, "duration_ms": None, "model": None, "error": None}
            for f in fired_lists
        ]

    def test_positive_passes_when_expected_member_fires_enough(self) -> None:
        case = {"id": "p", "polarity": "positive", "expect_fires": ["prompt-craft"]}
        runs = self._runs(["prompt-craft"], ["prompt-craft"], [])  # 2/3
        result = eval_routing.score_case(case, runs, self.MEMBERS, threshold=0.5)
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(result["correct_rate"], 2 / 3, places=2)

    def test_positive_fails_below_threshold(self) -> None:
        case = {"id": "p", "polarity": "positive", "expect_fires": ["prompt-craft"]}
        runs = self._runs(["prompt-craft"], [], [])  # 1/3 < 0.5
        self.assertFalse(eval_routing.score_case(case, runs, self.MEMBERS, threshold=0.5)["passed"])

    def test_negative_fails_if_cluster_fires_even_once(self) -> None:
        # Over-trigger is a defect regardless of variance — one firing across the runs fails it.
        case = {"id": "n", "polarity": "negative", "expect_not_fires": list(self.MEMBERS)}
        runs = self._runs([], [], ["prompt-engineer"])
        self.assertFalse(eval_routing.score_case(case, runs, self.MEMBERS, threshold=0.5)["passed"])

    def test_negative_passes_when_cluster_never_fires(self) -> None:
        case = {"id": "n", "polarity": "negative", "expect_not_fires": list(self.MEMBERS)}
        runs = self._runs(["backend-craft"], ["sde-fullstack"], [])
        result = eval_routing.score_case(case, runs, self.MEMBERS, threshold=0.5)
        self.assertTrue(result["passed"])
        self.assertEqual(["backend-craft", "sde-fullstack"], result["also_fired"])  # diagnostic

    def test_negative_grades_against_its_own_expect_not_fires(self) -> None:
        # REGRESSION: this used to grade every negative against the WHOLE member list, ignoring the
        # field each case declares. A disambiguation case — "the mitigation skill must not fire here,
        # but its sibling legitimately should" — then failed for the sibling doing the right thing.
        # Real instance: neg-resolved-not-incident forbids lab-incident on an already-resolved
        # outage while `postmortem`, a cluster member, is the correct destination.
        members = {"lab-incident", "postmortem", "runbook"}
        case = {"id": "n", "polarity": "negative", "expect_not_fires": ["lab-incident"]}
        runs = self._runs(["postmortem"], ["postmortem"], ["postmortem"])
        result = eval_routing.score_case(case, runs, members, threshold=0.5)
        self.assertTrue(result["passed"], result["detail"])
        self.assertIn("lab-incident", result["detail"])  # says what was actually forbidden

        # ...and the forbidden component firing still fails it.
        runs = self._runs(["postmortem"], ["lab-incident"], ["postmortem"])
        self.assertFalse(eval_routing.score_case(case, runs, members, threshold=0.5)["passed"])

    def test_errored_runs_are_excluded_from_the_rates(self) -> None:
        # REGRESSION: run_once marks a run with `error` when it captured no usable transcript, and
        # its comment says such a run must not count — but nothing implemented that, so an invalid
        # sample was scored as a confident "did not route". It bit as soon as a slower model was
        # pinned and sessions began timing out before their first tool call.
        case = {"id": "p", "polarity": "positive", "expect_fires": ["prompt-craft"]}
        runs = self._runs(["prompt-craft"])
        runs += [{"fired": [], "tokens": None, "duration_ms": None, "model": None,
                  "error": "timed out after 180s (partial transcript graded)"}]
        result = eval_routing.score_case(case, runs, self.MEMBERS, threshold=0.5)
        self.assertTrue(result["passed"], result["detail"])       # 1/1 valid, not 1/2
        self.assertEqual(1, result["runs_excluded"])
        self.assertIn("excluded", result["detail"])

    def test_a_case_whose_every_run_errored_is_inconclusive_not_passed(self) -> None:
        # An unmeasured case must not be reported as a result in either direction. For a NEGATIVE
        # this is the vacuous pass the exclusion exists to prevent: no transcript is not evidence
        # that nothing fired.
        errored = [{"fired": [], "tokens": None, "duration_ms": None, "model": None,
                    "error": "run failed: boom"} for _ in range(2)]
        for polarity, extra in (("positive", {"expect_fires": ["prompt-craft"]}),
                                ("negative", {"expect_not_fires": list(self.MEMBERS)})):
            with self.subTest(polarity=polarity):
                case = {"id": "c", "polarity": polarity, **extra}
                result = eval_routing.score_case(case, errored, self.MEMBERS, threshold=0.5)
                self.assertTrue(result["inconclusive"])
                self.assertFalse(result["passed"])
                self.assertIn("INCONCLUSIVE", result["detail"])

    def test_per_run_firings_are_recorded_for_audit(self) -> None:
        # A surprising verdict must be explicable from the artifact rather than by re-running.
        case = {"id": "n", "polarity": "negative", "expect_not_fires": list(self.MEMBERS)}
        result = eval_routing.score_case(case, self._runs([], ["prompt-craft"]), self.MEMBERS, 0.5)
        self.assertEqual([[], ["prompt-craft"]], result["fired_per_run"])

    def test_trouble_on_a_graded_run_is_still_reported(self) -> None:
        # A run can now be graded despite a non-zero exit, so the artifact has to say so — otherwise
        # a rate taken from troubled sessions is indistinguishable from a clean one.
        case = {"id": "p", "polarity": "positive", "expect_fires": ["prompt-craft"]}
        runs = self._runs(["prompt-craft"])
        runs[0]["note"] = "exit 1: stream closed"
        result = eval_routing.score_case(case, runs, self.MEMBERS, threshold=0.5)
        self.assertEqual(["exit 1: stream closed"], result["notes"])
        self.assertEqual(0, result["runs_excluded"])


class RunUsabilityTest(unittest.TestCase):
    """Which troubled runs count as measurements — the line between 'routed elsewhere' and 'blank'."""

    def _run_with_stdout(self, stdout: str, returncode: int = 1) -> dict:
        # `run_once`'s post-processing, exercised without spawning a session: monkeypatch the
        # subprocess call so the pure grading half runs against a synthetic transcript.
        import subprocess as sp

        class _Proc:
            stderr = "boom"

        proc = _Proc()
        proc.returncode, proc.stdout = returncode, stdout
        original_run, original_claude = sp.run, eval_routing.CLAUDE
        eval_routing.CLAUDE = "claude"
        sp.run = lambda *a, **k: proc
        try:
            return eval_routing.run_once("p", REPO)
        finally:
            sp.run, eval_routing.CLAUDE = original_run, original_claude

    def test_completed_session_that_routed_off_the_fleet_is_a_measurement(self) -> None:
        # REGRESSION: a non-zero exit whose session nonetheless finished used to be discarded merely
        # because no FLEET component fired. That deletes the wrong-route evidence a negative needs
        # and drops real misses out of a positive's denominator.
        import json
        stdout = "\n".join([
            transcript({"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}),
            json.dumps({"type": "result", "duration_ms": 10, "usage": {"input_tokens": 1, "output_tokens": 2}}),
        ])
        run = self._run_with_stdout(stdout)
        self.assertIsNone(run["error"], run)
        self.assertEqual([], run["fired"])
        self.assertIn("exit 1", run["note"])

    def test_session_that_produced_nothing_is_an_error(self) -> None:
        run = self._run_with_stdout("")
        self.assertIsNotNone(run["error"])

    def test_observed_model_is_read_even_when_one_was_requested(self) -> None:
        # REGRESSION: the transcript-derived model reused the `model` PARAMETER, so the read was
        # skipped whenever --model was passed — and `models_observed` then echoed the requested
        # alias for exactly the pinned runs the conditions block exists to describe.
        import json
        import subprocess as sp

        class _Proc:
            returncode = 0
            stdout = json.dumps({"type": "result", "model": "claude-opus-4-5-20260101"})
            stderr = ""

        original_run, original_claude = sp.run, eval_routing.CLAUDE
        eval_routing.CLAUDE = "claude"
        sp.run = lambda *a, **k: _Proc()
        try:
            run = eval_routing.run_once("p", REPO, model="opus")
        finally:
            sp.run, eval_routing.CLAUDE = original_run, original_claude
        self.assertEqual("claude-opus-4-5-20260101", run["model"])


class CaseFileTest(unittest.TestCase):
    def test_seed_cluster_is_well_formed(self) -> None:
        import json
        spec = json.loads((REPO / "evals" / "routing" / "prompt-tooling.json").read_text(encoding="utf-8"))
        members = set(spec["members"])
        self.assertTrue(members <= eval_routing.FLEET, "cluster members must be real fleet components")
        ids = [c["id"] for c in spec["cases"]]
        self.assertEqual(len(ids), len(set(ids)), "case ids must be unique")
        for case in spec["cases"]:
            self.assertIn(case["polarity"], ("positive", "negative"), case["id"])
            if case["polarity"] == "positive":
                self.assertTrue(set(case["expect_fires"]) <= members, case["id"])

    def test_every_negative_forbids_only_cluster_members(self) -> None:
        # A negative is graded against its own `expect_not_fires`, so a name that is not a cluster
        # member forbids nothing and the case passes vacuously — silently, and across every cluster.
        import json
        for path in sorted((REPO / "evals" / "routing").glob("*.json")):
            spec = json.loads(path.read_text(encoding="utf-8"))
            members = set(spec["members"])
            for case in spec["cases"]:
                if case["polarity"] != "negative":
                    continue
                forbidden = set(case.get("expect_not_fires", members))
                self.assertTrue(forbidden <= members,
                                f"{path.name}:{case['id']} forbids non-members "
                                f"{sorted(forbidden - members)} — they can never fire, so the case "
                                f"would pass without measuring anything")
                self.assertTrue(forbidden, f"{path.name}:{case['id']} forbids nothing")


if __name__ == "__main__":
    unittest.main()
