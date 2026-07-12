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
        return [{"fired": list(f), "tokens": None, "duration_ms": None, "error": None} for f in fired_lists]

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


if __name__ == "__main__":
    unittest.main()
