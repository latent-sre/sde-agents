"""Offline tests for scripts/eval_routing.py — the pure grading logic, no live sessions.

The runner's live arm is inherently non-deterministic (it drives real model sessions), so the parts
that MUST be correct — did we detect the right component from a transcript, did we score a case the
right way — are the pure functions, and those are tested here against synthetic transcripts. A
parsing bug here would silently mis-grade every routing eval, so it gets the deterministic coverage
the live arm can't.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import eval_routing as _eval_routing_bootstrap

eval_routing = _eval_routing_bootstrap.load_current_evaluator()

REPO = Path(__file__).resolve().parents[1]


class ExactSourceEntrypointTest(unittest.TestCase):
    def test_standalone_entry_reexecutes_the_captured_runner(self) -> None:
        bound = mock.Mock()
        bound.main.return_value = 17
        with mock.patch.object(
            _eval_routing_bootstrap, "load_current_evaluator", return_value=bound
        ) as loader:
            self.assertEqual(17, _eval_routing_bootstrap._main_entry())
        loader.assert_called_once_with()
        bound.main.assert_called_once_with()


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


def authentication_failure_transcript() -> str:
    return "\n".join([
        json.dumps({
            "type": "assistant",
            "error": "authentication_failed",
            "message": {"content": []},
        }),
        json.dumps({
            "type": "result",
            "is_error": True,
            "terminal_reason": "api_error",
            "result": "Failed to authenticate: OAuth session expired and could not be refreshed",
        }),
    ])


def generic_error_transcript(message: str = "provider request failed") -> str:
    return json.dumps({
        "type": "result",
        "is_error": True,
        "terminal_reason": "api_error",
        "result": message,
    })


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

    def test_positive_expectations_remain_any_of(self) -> None:
        case = {
            "id": "p",
            "polarity": "positive",
            "expect_fires": ["prompt-craft", "prompt-engineer"],
        }
        result = eval_routing.score_case(
            case, self._runs(["prompt-engineer"]), self.MEMBERS, threshold=1.0
        )
        self.assertTrue(result["passed"], result)

    def test_score_case_rejects_threshold_outside_open_closed_unit_interval(self) -> None:
        case = {"id": "p", "polarity": "positive", "expect_fires": ["prompt-craft"]}
        for threshold in (0, -0.1, 1.01, float("inf"), float("nan"), True, "0.5"):
            with self.subTest(threshold=threshold):
                with self.assertRaisesRegex(ValueError, "threshold"):
                    eval_routing.score_case(
                        case, self._runs(["prompt-craft"]), self.MEMBERS, threshold
                    )

    def test_score_case_rejects_unknown_polarity(self) -> None:
        case = {"id": "bad", "polarity": "positve", "expect_fires": ["prompt-craft"]}
        with self.assertRaisesRegex(ValueError, "polarity"):
            eval_routing.score_case(case, self._runs([]), self.MEMBERS, threshold=0.5)

    def test_score_case_rejects_empty_positive_expectation(self) -> None:
        case = {"id": "bad", "polarity": "positive", "expect_fires": []}
        with self.assertRaisesRegex(ValueError, "expect_fires"):
            eval_routing.score_case(case, self._runs([]), self.MEMBERS, threshold=0.5)

    def test_score_case_rejects_wrongly_typed_or_nonmember_targets(self) -> None:
        cases = (
            {"id": "bad-pos-type", "polarity": "positive", "expect_fires": "prompt-craft"},
            {"id": "bad-pos-name", "polarity": "positive", "expect_fires": ["not-a-member"]},
            {"id": "bad-neg-type", "polarity": "negative", "expect_not_fires": "prompt-craft"},
            {"id": "bad-neg-name", "polarity": "negative", "expect_not_fires": ["not-a-member"]},
        )
        for case in cases:
            with self.subTest(case=case["id"]):
                with self.assertRaisesRegex(ValueError, "expect_(not_)?fires"):
                    eval_routing.score_case(case, self._runs([]), self.MEMBERS, threshold=0.5)

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

    def test_negative_omitted_forbidden_set_defaults_to_whole_cluster(self) -> None:
        case = {"id": "n", "polarity": "negative"}
        self.assertFalse(
            eval_routing.score_case(
                case, self._runs(["prompt-engineer"]), self.MEMBERS, threshold=0.5
            )["passed"]
        )

    def test_score_case_rejects_empty_explicit_forbidden_set(self) -> None:
        case = {"id": "bad", "polarity": "negative", "expect_not_fires": []}
        with self.assertRaisesRegex(ValueError, "expect_not_fires"):
            eval_routing.score_case(case, self._runs([]), self.MEMBERS, threshold=0.5)

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


class CliValidationTest(unittest.TestCase):
    def test_cli_rejects_zero_threshold_before_reading_or_running(self) -> None:
        self._assert_invalid_threshold("0")

    def test_cli_rejects_threshold_above_one_before_reading_or_running(self) -> None:
        self._assert_invalid_threshold("1.01")

    def _assert_invalid_threshold(self, threshold: str) -> None:
        stderr = io.StringIO()
        with (
            mock.patch.object(eval_routing, "CLAUDE", "claude"),
            mock.patch.object(
                eval_routing,
                "_read_regular_file",
                side_effect=AssertionError("invalid threshold reached cluster loading"),
            ),
            contextlib.redirect_stderr(stderr),
        ):
            code = eval_routing.main(["--threshold", threshold])
        self.assertEqual(2, code)
        self.assertIn("--threshold must be > 0 and <= 1", stderr.getvalue())


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

    def test_nonzero_non_error_result_mentioning_auth_is_still_a_measurement(self) -> None:
        stdout = json.dumps({
            "type": "result",
            "is_error": False,
            "result": "The input text was: authentication_failed",
            "duration_ms": 10,
        })
        run = self._run_with_stdout(stdout)
        self.assertIsNone(run["error"], run)
        self.assertEqual([], run["fired"])

    def test_session_that_produced_nothing_is_an_error(self) -> None:
        run = self._run_with_stdout("")
        self.assertIsNotNone(run["error"])

    def test_structured_auth_failure_is_never_a_routing_measurement(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "authentication failed"):
            self._run_with_stdout(authentication_failure_transcript())

    def test_generic_error_result_cannot_green_a_negative(self) -> None:
        run = self._run_with_stdout(generic_error_transcript())
        self.assertIsNotNone(run["error"], run)
        self.assertIn("structured result reported an error", run["error"])
        case = {
            "id": "neg",
            "polarity": "negative",
            "expect_not_fires": ["prompt-craft"],
        }
        scored = eval_routing.score_case(case, [run], {"prompt-craft"}, threshold=0.5)
        self.assertTrue(scored["inconclusive"], scored)
        self.assertFalse(scored["passed"], scored)

    def test_firing_before_generic_error_remains_labeled_partial_evidence(self) -> None:
        stdout = "\n".join([
            transcript(skill_use("sde-agents:prompt-craft")),
            generic_error_transcript(),
        ])
        run = self._run_with_stdout(stdout)
        self.assertEqual(["prompt-craft"], run["fired"])
        self.assertIsNone(run["error"], run)
        self.assertIn("structured result reported an error", run["note"])

    def test_error_result_is_not_a_completed_session_even_at_zero_exit(self) -> None:
        stats = eval_routing.transcript_stats(generic_error_transcript())
        self.assertFalse(stats["completed"])
        self.assertTrue(stats["result_error"])
        run = self._run_with_stdout(generic_error_transcript(), returncode=0)
        self.assertIsNotNone(run["error"], run)

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

    def test_coverage_table_lists_every_cluster_file(self) -> None:
        readme = (REPO / "evals" / "README.md").read_text(encoding="utf-8")
        missing = [
            path.name
            for path in sorted((REPO / "evals" / "routing").glob("*.json"))
            if f"`{path.name}`" not in readme
        ]
        self.assertEqual(
            [],
            missing,
            "evals/README.md omits routing clusters, so operators can silently skip shipped evals",
        )


class ConditionsTest(unittest.TestCase):
    def test_plugin_dir_inside_repo_is_recorded_repo_relative(self) -> None:
        # Recorded verbatim, the default plugin_dir (this repo, absolute) commits the operator's
        # local filesystem layout into a baseline artifact — identity noise that makes identical
        # measurements from two machines diff.
        self.assertEqual(".", eval_routing.plugin_dir_label(REPO))
        self.assertEqual("agents", eval_routing.plugin_dir_label(REPO / "agents"))

    def test_external_plugin_dir_is_recorded_verbatim(self) -> None:
        # A plugin_dir OUTSIDE the repo is a real measurement condition (a different plugin was
        # loaded), so it must survive into the artifact unchanged.
        outside = Path(REPO.anchor) / "somewhere-else"
        self.assertEqual(str(outside), eval_routing.plugin_dir_label(outside))


class ProvenanceTest(unittest.TestCase):
    """A benchmark identity changes only when an input that can affect the eval changes."""

    def _plugin(self, root: Path, files: list[tuple[str, bytes]] | None = None) -> None:
        files = files or [
            (".claude-plugin/plugin.json", b'{"name":"probe"}\n'),
            ("agents/probe.md", b"---\nname: probe\n---\nfirst\n"),
        ]
        for relative, content in files:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    def test_clean_room_classifier_is_loaded_once_per_evaluator_process(self) -> None:
        first = eval_routing._load_clean_room()
        second = eval_routing._load_clean_room()
        self.assertIs(first, second)

    def test_clean_room_identity_hashes_the_exact_compiled_source_buffer(self) -> None:
        eval_routing._load_clean_room()
        path = Path(eval_routing.__file__).with_name("eval_clean_room.py")
        key = eval_routing._evaluator_source_key(path)
        loaded = eval_routing._LOADED_EVALUATOR_SOURCES[key]
        with mock.patch.object(
            eval_routing,
            "_read_regular_file",
            side_effect=AssertionError("loaded evaluator source must not be re-read"),
        ):
            identity = eval_routing.evaluator_identity([path])
        self.assertEqual(eval_routing._sha256(loaded), identity["files"][0]["sha256"])

    @unittest.skipUnless(os.name == "nt", "path casing collapses only on Windows filesystems")
    def test_registry_survives_drive_letter_case_drift(self) -> None:
        # The #69 field failure: registration under one cwd casing, lookup under another —
        # the same file, two dict keys, and identity silently re-reads the bytes it promised
        # were the compiled ones. Fails without _evaluator_source_key normcasing both ends.
        eval_routing._load_clean_room()
        path = Path(eval_routing.__file__).with_name("eval_clean_room.py")
        drive_swapped = Path(str(path)[0].swapcase() + str(path)[1:])
        self.assertEqual(
            eval_routing._evaluator_source_key(path),
            eval_routing._evaluator_source_key(drive_swapped),
        )
        with mock.patch.object(
            eval_routing,
            "_read_regular_file",
            side_effect=AssertionError("case-drifted path must still hit the registry"),
        ):
            identity = eval_routing.evaluator_identity([drive_swapped])
        loaded = eval_routing._LOADED_EVALUATOR_SOURCES[eval_routing._evaluator_source_key(path)]
        self.assertEqual(eval_routing._sha256(loaded), identity["files"][0]["sha256"])

    def test_standalone_runner_is_bound_to_its_actual_compiled_source_buffer(self) -> None:
        path = Path(eval_routing.__file__)
        key = eval_routing._evaluator_source_key(path)
        loaded = eval_routing._LOADED_EVALUATOR_SOURCES[key]
        self.assertIsNotNone(eval_routing._EXECUTING_EVALUATOR_SOURCE)
        with mock.patch.object(
            eval_routing,
            "_read_regular_file",
            side_effect=AssertionError("bound main source must not be re-read"),
        ):
            identity = eval_routing.evaluator_identity([path])
        self.assertEqual(eval_routing._sha256(loaded), identity["files"][0]["sha256"])

    def test_loaded_a_disk_b_identity_records_the_executing_routing_buffer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp).resolve() / "eval_routing_copy.py"
            source_a = Path(eval_routing.__file__).read_bytes()
            path.write_bytes(source_a)
            loaded_module = eval_routing.load_evaluator_module("routing_copy", path)
            path.write_bytes(b"raise RuntimeError('disk B must not become provenance')\n")
            first = loaded_module.evaluator_identity([path])
            second = loaded_module.evaluator_identity([path])
        self.assertEqual(first, second)
        self.assertEqual(
            eval_routing._sha256(source_a), first["files"][0]["sha256"]
        )

    def test_source_identity_hashes_exact_file_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp).resolve() / "cluster.json"
            source.write_bytes(b'{"cases":[]}\n')
            before = eval_routing.source_identity([source])
            source.write_bytes(b'{"cases":[]}\r\n')
            after = eval_routing.source_identity([source])
        self.assertNotEqual(before[0]["sha256"], after[0]["sha256"])
        self.assertNotIn("\\", before[0]["path"])

    def test_evaluator_identity_hashes_exact_files_and_python_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evaluator = Path(tmp).resolve() / "grader.py"
            evaluator.write_bytes(b"first\n")
            before = eval_routing.evaluator_identity([evaluator])
            evaluator.write_bytes(b"second\n")
            after = eval_routing.evaluator_identity([evaluator])
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertRegex(before["files"][0]["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(before["runtime"]["implementation"])
        self.assertRegex(before["runtime"]["python_version"], r"^\d+\.\d+")

    def test_evaluator_change_makes_batch_provenance_incomparable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            source = root / "cluster.json"
            source.write_text('{"cases":[]}\n', encoding="utf-8")
            evaluator = root / "grader.py"
            evaluator.write_text("first\n", encoding="utf-8")
            before = eval_routing.benchmark_provenance(
                [source], [], "*", root, evaluator_paths=[evaluator]
            )
            evaluator.write_text("second\n", encoding="utf-8")
            after = eval_routing.benchmark_provenance(
                [source], [], "*", root, evaluator_paths=[evaluator]
            )
        self.assertFalse(eval_routing._content_provenance_matches(before, after))

    def test_selection_identity_hashes_definitions_expression_and_ids(self) -> None:
        cases = [{"id": "one", "prompt": "first"}]
        first = eval_routing.selection_identity("one*", cases)
        changed_definition = eval_routing.selection_identity(
            "one*", [{"id": "one", "prompt": "second"}]
        )
        changed_expression = eval_routing.selection_identity("*", cases)
        reordered_keys = eval_routing.selection_identity(
            "one*", [{"prompt": "first", "id": "one"}]
        )
        self.assertNotEqual(first["sha256"], changed_definition["sha256"])
        self.assertNotEqual(first["sha256"], changed_expression["sha256"])
        self.assertEqual(first["sha256"], reordered_keys["sha256"])
        self.assertEqual(["one"], first["case_ids"])
        self.assertEqual("one*", first["expression"])

    def test_plugin_identity_changes_with_runtime_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            before = eval_routing.plugin_identity(root)
            (root / "agents" / "probe.md").write_text("changed\n", encoding="utf-8")
            after = eval_routing.plugin_identity(root)
        self.assertNotEqual(before["sha256"], after["sha256"])

    def test_plugin_identity_is_stable_across_creation_and_traversal_order(self) -> None:
        files = [
            ("skills/z/SKILL.md", b"z\n"),
            (".claude-plugin/plugin.json", b"{}\n"),
            ("agents/a.md", b"a\n"),
        ]
        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            first, second = Path(first_tmp).resolve(), Path(second_tmp).resolve()
            self._plugin(first, files)
            self._plugin(second, list(reversed(files)))
            first_identity = eval_routing.plugin_identity(first)
            second_identity = eval_routing.plugin_identity(second)
        self.assertEqual(first_identity["sha256"], second_identity["sha256"])

    def test_eval_outputs_and_unrelated_docs_are_explicitly_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            output = root / "evals" / "baselines" / "run" / "benchmark.json"
            output.parent.mkdir(parents=True)
            output.write_text("first", encoding="utf-8")
            skill = root / "skills" / "probe" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "Ignore eval output `evals/baselines/run/benchmark.json`.\n", encoding="utf-8"
            )
            docs = root / "docs" / "roadmap.md"
            docs.parent.mkdir()
            docs.write_text("unrelated", encoding="utf-8")
            before = eval_routing.plugin_identity(root)
            output.write_text("second", encoding="utf-8")
            docs.write_text("also unrelated", encoding="utf-8")
            after = eval_routing.plugin_identity(root)
        self.assertEqual(before["sha256"], after["sha256"])
        self.assertIn("evals/**", after["scope"]["excluded"])
        self.assertIn("unreferenced docs/**", after["scope"]["excluded"])

    def test_external_plugin_directory_is_hashed_directly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "external-plugin"
            root.mkdir()
            self._plugin(root)
            identity = eval_routing.plugin_identity(root)
        self.assertEqual(2, identity["files_hashed"])
        self.assertEqual([".claude-plugin", "agents"], identity["scope"]["included"])

    def test_explicit_plugin_root_runtime_dependency_is_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            hook = root / "hooks" / "hooks.json"
            hook.parent.mkdir()
            hook.write_text('${CLAUDE_PLUGIN_ROOT}/scripts/guard.py', encoding="utf-8")
            guard = root / "scripts" / "guard.py"
            guard.parent.mkdir()
            guard.write_text("first\n", encoding="utf-8")
            before = eval_routing.plugin_identity(root)
            guard.write_text("second\n", encoding="utf-8")
            after = eval_routing.plugin_identity(root)
        self.assertIn("scripts/guard.py", before["scope"]["included"])
        self.assertNotEqual(before["sha256"], after["sha256"])

    def test_repo_relative_referenced_script_is_hashed_but_unrelated_script_is_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root, [
                (".claude-plugin/plugin.json", b"{}\n"),
                ("skills/probe/SKILL.md", b"Run `python scripts/learning_ledger.py check`.\n"),
                ("scripts/learning_ledger.py", b"print('first')\n"),
                ("scripts/unrelated.py", b"print('unrelated first')\n"),
            ])
            before = eval_routing.plugin_identity(root)
            (root / "scripts" / "unrelated.py").write_text(
                "print('unrelated second')\n", encoding="utf-8"
            )
            unrelated_changed = eval_routing.plugin_identity(root)
            (root / "scripts" / "learning_ledger.py").write_text(
                "print('second')\n", encoding="utf-8"
            )
            referenced_changed = eval_routing.plugin_identity(root)
        self.assertIn("scripts/learning_ledger.py", before["scope"]["included"])
        self.assertNotIn("scripts/unrelated.py", before["scope"]["included"])
        self.assertEqual(before["sha256"], unrelated_changed["sha256"])
        self.assertNotEqual(unrelated_changed["sha256"], referenced_changed["sha256"])

    def test_repo_relative_script_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root, [
                (".claude-plugin/plugin.json", b"{}\n"),
                ("skills/probe/SKILL.md", b"Run `python scripts/../outside.py`.\n"),
            ])
            with self.assertRaises(eval_routing.ProvenanceError):
                eval_routing.plugin_identity(root)

    def test_backticked_repo_relative_read_dependency_is_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root, [
                (".claude-plugin/plugin.json", b"{}\n"),
                ("skills/probe/SKILL.md", b"Read `learning/README.md` before deciding.\n"),
                ("learning/README.md", b"first\n"),
                ("learning/unrelated.md", b"unrelated first\n"),
            ])
            before = eval_routing.plugin_identity(root)
            (root / "learning" / "unrelated.md").write_text(
                "unrelated second\n", encoding="utf-8"
            )
            unrelated_changed = eval_routing.plugin_identity(root)
            (root / "learning" / "README.md").write_text("second\n", encoding="utf-8")
            referenced_changed = eval_routing.plugin_identity(root)
        self.assertIn("learning/README.md", before["scope"]["included"])
        self.assertNotIn("learning/unrelated.md", before["scope"]["included"])
        self.assertEqual(before["sha256"], unrelated_changed["sha256"])
        self.assertNotEqual(unrelated_changed["sha256"], referenced_changed["sha256"])

    @unittest.skipUnless(shutil.which("git"), "git is required for Git identity coverage")
    def test_git_head_and_dirty_boolean_are_recorded_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "core.autocrlf", "false"], check=True
            )
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run([
                "git", "-C", str(root), "-c", "user.name=Eval Test",
                "-c", "user.email=eval@example.invalid", "commit", "-qm", "baseline",
            ], check=True)
            clean = eval_routing.plugin_identity(root)
            self.assertRegex(clean["git_head"], r"^[0-9a-f]{40,64}$")
            self.assertIs(clean["git_dirty"], False)
            unrelated = root / "docs" / "note.md"
            unrelated.parent.mkdir()
            unrelated.write_text("dirty but outside runtime scope\n", encoding="utf-8")
            dirty_unrelated = eval_routing.plugin_identity(root)
            self.assertIs(dirty_unrelated["git_dirty"], True)
            self.assertEqual(clean["sha256"], dirty_unrelated["sha256"])
            (root / "agents" / "probe.md").write_text("dirty\n", encoding="utf-8")
            dirty = eval_routing.plugin_identity(root)
            self.assertIs(dirty["git_dirty"], True)
            self.assertNotEqual(clean["sha256"], dirty["sha256"])

    def test_reparse_attribute_is_treated_as_unsafe_on_every_platform(self) -> None:
        class FakeStat:
            st_mode = stat.S_IFDIR
            st_file_attributes = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

        self.assertTrue(eval_routing._is_link_or_reparse(FakeStat()))

    def test_symlink_in_runtime_tree_is_rejected_where_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self._plugin(root)
            target = root / "target.md"
            target.write_text("target", encoding="utf-8")
            link = root / "agents" / "linked.md"
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            with self.assertRaises(eval_routing.ProvenanceError):
                eval_routing.plugin_identity(root)

    def test_routing_benchmark_writes_complete_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            plugin = base / "plugin"
            plugin.mkdir()
            self._plugin(plugin)
            cluster = base / "cluster.json"
            cluster.write_text(json.dumps({
                "cluster": "probe",
                "members": ["prompt-craft"],
                "cases": [{
                    "id": "pos-probe",
                    "polarity": "positive",
                    "prompt": "probe",
                    "expect_fires": ["prompt-craft"],
                }],
            }), encoding="utf-8")
            output = base / "output"

            def fake_run_once(*args, **kwargs):
                return {
                    "fired": ["prompt-craft"], "tokens": 1, "duration_ms": 1,
                    "model": "test-model", "error": None, "note": None,
                }

            original_run = eval_routing.run_once
            original_claude = eval_routing.CLAUDE
            original_version = eval_routing.cli_version
            eval_routing.run_once = fake_run_once
            eval_routing.CLAUDE = "claude"
            eval_routing.cli_version = lambda: "test-cli"
            try:
                code = eval_routing.main([
                    str(cluster), "--case", "pos-*", "--runs", "1",
                    "--plugin-dir", str(plugin), "--output-dir", str(output),
                ])
            finally:
                eval_routing.run_once = original_run
                eval_routing.CLAUDE = original_claude
                eval_routing.cli_version = original_version

            payload = json.loads((output / "benchmark.json").read_text(encoding="utf-8"))
        self.assertEqual(0, code)
        provenance = payload["provenance"]
        self.assertEqual(eval_routing.PROVENANCE_SCHEMA, provenance["schema"])
        self.assertEqual("pos-*", provenance["selection"]["expression"])
        self.assertEqual(["pos-probe"], provenance["selection"]["case_ids"])
        self.assertEqual(1, len(provenance["eval_sources"]))
        self.assertRegex(provenance["eval_sources"][0]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            ["scripts/eval_clean_room.py", "scripts/eval_routing.py"],
            [record["path"] for record in provenance["evaluator"]["files"]],
        )
        self.assertRegex(provenance["evaluator"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(
            provenance["evaluator"]["runtime"]["python_version"], r"^\d+\.\d+"
        )
        self.assertRegex(provenance["plugin"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(4, payload["conditions"]["concurrency"])
        self.assertEqual(
            {"auth", "provider"}, set(payload["conditions"]["auth_provider"])
        )

    def test_routing_benchmark_refuses_plugin_content_changed_during_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            plugin = base / "plugin"
            plugin.mkdir()
            self._plugin(plugin)
            cluster = base / "cluster.json"
            cluster.write_text(json.dumps({
                "cluster": "probe",
                "members": ["prompt-craft"],
                "cases": [{
                    "id": "pos-probe", "polarity": "positive", "prompt": "probe",
                    "expect_fires": ["prompt-craft"],
                }],
            }), encoding="utf-8")
            output = base / "output"

            def mutating_run_once(*args, **kwargs):
                (plugin / "agents" / "probe.md").write_text("changed mid-run\n", encoding="utf-8")
                return {
                    "fired": ["prompt-craft"], "tokens": 1, "duration_ms": 1,
                    "model": "test-model", "error": None, "note": None,
                }

            original_run = eval_routing.run_once
            original_claude = eval_routing.CLAUDE
            original_version = eval_routing.cli_version
            eval_routing.run_once = mutating_run_once
            eval_routing.CLAUDE = "claude"
            eval_routing.cli_version = lambda: "test-cli"
            try:
                code = eval_routing.main([
                    str(cluster), "--runs", "1", "--plugin-dir", str(plugin),
                    "--output-dir", str(output),
                ])
            finally:
                eval_routing.run_once = original_run
                eval_routing.CLAUDE = original_claude
                eval_routing.cli_version = original_version

            self.assertFalse((output / "benchmark.json").exists())

        self.assertEqual(2, code)

    def test_routing_executes_frozen_plugin_when_source_changes_and_restores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            plugin = base / "plugin"
            plugin.mkdir()
            self._plugin(plugin)
            original = (plugin / "agents" / "probe.md").read_bytes()
            cluster = base / "cluster.json"
            cluster.write_text(json.dumps({
                "cluster": "probe",
                "members": ["prompt-craft"],
                "cases": [{
                    "id": "pos-probe", "polarity": "positive", "prompt": "probe",
                    "expect_fires": ["prompt-craft"],
                }],
            }), encoding="utf-8")
            output = base / "output"

            def restoring_run_once(prompt, execution_plugin, *args, **kwargs):
                self.assertNotEqual(plugin, execution_plugin)
                self.assertEqual(
                    original, (execution_plugin / "agents" / "probe.md").read_bytes()
                )
                (plugin / "agents" / "probe.md").write_text(
                    "temporary mid-run bytes\n", encoding="utf-8"
                )
                (plugin / "agents" / "probe.md").write_bytes(original)
                self.assertEqual(
                    original, (execution_plugin / "agents" / "probe.md").read_bytes()
                )
                return {
                    "fired": ["prompt-craft"], "tokens": 1, "duration_ms": 1,
                    "model": "test-model", "error": None, "note": None,
                }

            original_run = eval_routing.run_once
            original_claude = eval_routing.CLAUDE
            original_version = eval_routing.cli_version
            eval_routing.run_once = restoring_run_once
            eval_routing.CLAUDE = "claude"
            eval_routing.cli_version = lambda: "test-cli"
            try:
                code = eval_routing.main([
                    str(cluster), "--runs", "1", "--plugin-dir", str(plugin),
                    "--output-dir", str(output),
                ])
            finally:
                eval_routing.run_once = original_run
                eval_routing.CLAUDE = original_claude
                eval_routing.cli_version = original_version

            self.assertTrue((output / "benchmark.json").exists())

        self.assertEqual(0, code)

    def test_routing_refuses_frozen_plugin_mutated_by_a_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            plugin = base / "plugin"
            plugin.mkdir()
            self._plugin(plugin)
            cluster = base / "cluster.json"
            cluster.write_text(json.dumps({
                "cluster": "probe",
                "members": ["prompt-craft"],
                "cases": [{
                    "id": "pos-probe", "polarity": "positive", "prompt": "probe",
                    "expect_fires": ["prompt-craft"],
                }],
            }), encoding="utf-8")
            output = base / "output"

            def mutating_snapshot_run_once(prompt, execution_plugin, *args, **kwargs):
                (execution_plugin / "agents" / "probe.md").write_text(
                    "session mutation\n", encoding="utf-8"
                )
                return {
                    "fired": ["prompt-craft"], "tokens": 1, "duration_ms": 1,
                    "model": "test-model", "error": None, "note": None,
                }

            original_run = eval_routing.run_once
            original_claude = eval_routing.CLAUDE
            eval_routing.run_once = mutating_snapshot_run_once
            eval_routing.CLAUDE = "claude"
            try:
                code = eval_routing.main([
                    str(cluster), "--runs", "1", "--plugin-dir", str(plugin),
                    "--output-dir", str(output),
                ])
            finally:
                eval_routing.run_once = original_run
                eval_routing.CLAUDE = original_claude

            self.assertFalse((output / "benchmark.json").exists())

        self.assertEqual(2, code)

    def test_transient_private_snapshot_mutation_is_a_host_sandbox_boundary(self) -> None:
        """Endpoint hashing detects persistence, not same-user A -> B -> A snapshot writes."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            plugin = base / "plugin"
            plugin.mkdir()
            self._plugin(plugin)
            cluster = base / "cluster.json"
            cluster.write_text(json.dumps({
                "cluster": "probe",
                "members": ["prompt-craft"],
                "cases": [{
                    "id": "pos-probe", "polarity": "positive", "prompt": "probe",
                    "expect_fires": ["prompt-craft"],
                }],
            }), encoding="utf-8")
            output = base / "output"

            def restoring_snapshot(prompt, execution_plugin, *args, **kwargs):
                target = execution_plugin / "agents" / "probe.md"
                original = target.read_bytes()
                target.write_text("transient session mutation\n", encoding="utf-8")
                target.write_bytes(original)
                return {
                    "fired": ["prompt-craft"], "tokens": 1, "duration_ms": 1,
                    "model": "test-model", "error": None, "note": None,
                }

            original_run = eval_routing.run_once
            original_claude = eval_routing.CLAUDE
            original_version = eval_routing.cli_version
            eval_routing.run_once = restoring_snapshot
            eval_routing.CLAUDE = "claude"
            eval_routing.cli_version = lambda: "test-cli"
            try:
                code = eval_routing.main([
                    str(cluster), "--runs", "1", "--plugin-dir", str(plugin),
                    "--output-dir", str(output),
                ])
            finally:
                eval_routing.run_once = original_run
                eval_routing.CLAUDE = original_claude
                eval_routing.cli_version = original_version

            self.assertTrue((output / "benchmark.json").exists())
        self.assertEqual(0, code)

    def test_routing_batch_aborts_auth_failure_without_writing_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            plugin = base / "plugin"
            plugin.mkdir()
            self._plugin(plugin)
            cluster = base / "cluster.json"
            cluster.write_text(json.dumps({
                "cluster": "probe",
                "members": ["prompt-craft"],
                "cases": [{
                    "id": "neg-probe",
                    "polarity": "negative",
                    "prompt": "probe",
                    "expect_not_fires": ["prompt-craft"],
                }],
            }), encoding="utf-8")
            output = base / "output"

            class AuthProc:
                returncode = 1
                stdout = authentication_failure_transcript()
                stderr = ""

            original_run = subprocess.run

            def fake_run(command, *args, **kwargs):
                if "--output-format" in command:
                    return AuthProc()
                return original_run(command, *args, **kwargs)

            original_claude = eval_routing.CLAUDE
            eval_routing.CLAUDE = "claude"
            try:
                with mock.patch.object(eval_routing.subprocess, "run", side_effect=fake_run):
                    code = eval_routing.main([
                        str(cluster), "--runs", "1", "--concurrency", "1",
                        "--plugin-dir", str(plugin), "--output-dir", str(output),
                    ])
            finally:
                eval_routing.CLAUDE = original_claude

            self.assertEqual(2, code)
            self.assertFalse((output / "benchmark.json").exists())


if __name__ == "__main__":
    unittest.main()
