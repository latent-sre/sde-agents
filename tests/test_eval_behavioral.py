"""Offline tests for scripts/eval_behavioral.py — conditions, cost, duration, and scratch cwd.

EVAL-002's failure class: an artifact that cannot state what it measured. The live run on
2026-07-29 proved it twice — behavioral sessions ran on an unpinned, unrecorded model, and the
`%TEMP%` scratch cwd silently blocked the writes one case's premise depends on. These tests pin
the repairs: the shared transcript read reports usage or its absence honestly, the benchmark
records its conditions, and the scratch cwd stays out of the directory tree the CLI sandbox
write-blocks.
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import eval_behavioral as _eval_behavioral_bootstrap
from scripts import eval_codex_runtime

eval_behavioral = _eval_behavioral_bootstrap.load_current_evaluator()
eval_routing = eval_behavioral.eval_routing

from tests.support import REPO


class ExactSourceEntrypointTest(unittest.TestCase):
    def test_standalone_entry_reexecutes_the_captured_runner(self) -> None:
        bound = mock.Mock()
        bound.main.return_value = 17
        with mock.patch.object(
            _eval_behavioral_bootstrap, "load_current_evaluator", return_value=bound
        ) as loader:
            self.assertEqual(17, _eval_behavioral_bootstrap._main_entry())
        loader.assert_called_once_with()
        bound.main.assert_called_once_with()


def result_event(usage: dict | None, duration_ms: int = 1234) -> str:
    event: dict = {"type": "result", "result": "done", "duration_ms": duration_ms}
    if usage is not None:
        event["usage"] = usage
    return json.dumps(event)


def assistant_event(model: str | None = None, text: str = "hi") -> str:
    message: dict = {"content": [{"type": "text", "text": text}]}
    if model:
        message["model"] = model
    return json.dumps({"type": "assistant", "message": message})


class TranscriptStatsTest(unittest.TestCase):
    """The single shared read both runners describe their conditions from."""

    def test_complete_usage_is_read_with_input_and_output_separated(self) -> None:
        stats = eval_routing.transcript_stats(
            assistant_event(model="claude-opus-5")
            + "\n"
            + result_event({"input_tokens": 100, "output_tokens": 25})
        )
        self.assertEqual(100, stats["input_tokens"])
        self.assertEqual(25, stats["output_tokens"])
        self.assertEqual("claude-opus-5", stats["model"])
        self.assertEqual(1234, stats["duration_ms"])
        self.assertTrue(stats["completed"])

    def test_missing_usage_is_none_not_zero(self) -> None:
        # Absent usage must be reported as UNAVAILABLE, never as a zero-token run — a zero would
        # read as "this session was free" in a cost comparison, which is the quiet-wrong shape.
        stats = eval_routing.transcript_stats(result_event(usage=None))
        self.assertIsNone(stats["input_tokens"])
        self.assertIsNone(stats["output_tokens"])
        self.assertTrue(stats["completed"])

    def test_no_result_event_means_not_completed(self) -> None:
        stats = eval_routing.transcript_stats(assistant_event(model="claude-sonnet-5"))
        self.assertFalse(stats["completed"])
        self.assertEqual("claude-sonnet-5", stats["model"])

    def test_malformed_lines_do_not_crash(self) -> None:
        stats = eval_routing.transcript_stats("not json\n{bad\n")
        self.assertIsNone(stats["model"])
        self.assertFalse(stats["completed"])

    def test_run_once_token_sum_matches_the_shared_read(self) -> None:
        # run_once's artifact keeps its summed `tokens` field; the sum must come from the same
        # read, or the two runners' artifacts could disagree about one transcript.
        stdout = result_event({"input_tokens": 10, "output_tokens": 5})
        stats = eval_routing.transcript_stats(stdout)
        self.assertEqual(15, (stats["input_tokens"] or 0) + (stats["output_tokens"] or 0))


class RunSessionValidationTest(unittest.TestCase):
    """Only a zero-exit, non-error final result is behavioral contract evidence."""

    def _run_with_event(self, event: dict, returncode: int) -> tuple[str, set[str], str | None, dict]:
        class Proc:
            stderr = "runner stderr"

        proc = Proc()
        proc.returncode = returncode
        proc.stdout = json.dumps(event)
        with mock.patch.object(eval_behavioral, "CLAUDE", "claude"), mock.patch.object(
            eval_behavioral.subprocess, "run", return_value=proc
        ):
            return eval_behavioral.run_session("prompt", REPO, timeout=10)

    def test_generic_error_result_text_is_never_graded(self) -> None:
        text, _fired, note, stats = self._run_with_event({
            "type": "result",
            "is_error": True,
            "result": "approval effect request all assertions held",
        }, returncode=0)
        self.assertEqual("", text)
        self.assertIn("structured result reported an error", note)
        self.assertFalse(stats["completed"])
        self.assertTrue(stats["result_error"])

    def test_nonzero_exit_with_non_error_result_is_not_behavioral_evidence(self) -> None:
        text, _fired, note, stats = self._run_with_event({
            "type": "result",
            "is_error": False,
            "result": "a complete contract-shaped answer",
        }, returncode=1)
        self.assertEqual("", text)
        self.assertIn("exited 1", note)
        self.assertTrue(stats["completed"])

    def test_zero_exit_non_error_result_remains_usable(self) -> None:
        text, _fired, note, stats = self._run_with_event({
            "type": "result", "is_error": False, "result": "usable answer"
        }, returncode=0)
        self.assertEqual("usable answer", text)
        self.assertIsNone(note)
        self.assertTrue(stats["completed"])

    def test_explicit_empty_allowlist_reaches_cli_and_disables_default_builtins(self) -> None:
        proc = mock.Mock(
            returncode=0,
            stdout=json.dumps({"type": "result", "is_error": False, "result": "done"}),
            stderr="",
        )
        with mock.patch.object(eval_behavioral, "CLAUDE", "claude"), mock.patch.object(
            eval_behavioral.subprocess, "run", return_value=proc
        ) as run:
            eval_behavioral.run_session(
                "prompt", REPO, timeout=10, allowed_tools=[], disallowed_tools=["PowerShell"]
            )
        command = run.call_args.args[0]
        tools_index = command.index("--tools")
        self.assertEqual("", command[tools_index + 1])
        self.assertEqual("--disallowed-tools", command[tools_index + 2])
        self.assertEqual("PowerShell", command[tools_index + 3])

    def test_nonempty_allowlist_is_the_only_positive_cli_tool_grant(self) -> None:
        proc = mock.Mock(
            returncode=0,
            stdout=json.dumps({"type": "result", "is_error": False, "result": "done"}),
            stderr="",
        )
        with mock.patch.object(eval_behavioral, "CLAUDE", "claude"), mock.patch.object(
            eval_behavioral.subprocess, "run", return_value=proc
        ) as run:
            eval_behavioral.run_session(
                "prompt", REPO, timeout=10, allowed_tools=["Skill"]
            )
        command = run.call_args.args[0]
        tools_index = command.index("--tools")
        self.assertEqual(["--tools", "Skill"], command[tools_index:tools_index + 2])
        self.assertNotIn("PowerShell", command)

    def test_workspace_oracle_is_seeded_graded_and_returned_before_cleanup(self) -> None:
        proc = mock.Mock(
            returncode=0,
            stdout=json.dumps({"type": "result", "is_error": False, "result": "done"}),
            stderr="",
        )
        observed: dict[str, Path] = {}

        def prepare(cwd: Path, oracle: str | None) -> None:
            self.assertEqual("handoff-builder-artifact", oracle)
            observed["cwd"] = cwd
            (cwd / "seeded").write_text("yes", encoding="utf-8")

        def evaluate(
            cwd: Path, oracle: str | None, **_kwargs,
        ) -> tuple[list[str], dict]:
            self.assertEqual(observed["cwd"], cwd)
            self.assertEqual("yes", (cwd / "seeded").read_text(encoding="utf-8"))
            return [], {"oracle": oracle, "verifier_exit": 0}

        with mock.patch.object(eval_behavioral, "CLAUDE", "claude"), mock.patch.object(
            eval_behavioral.subprocess, "run", return_value=proc
        ), mock.patch.object(
            eval_behavioral, "prepare_semantic_workspace", side_effect=prepare
        ), mock.patch.object(
            eval_behavioral, "evaluate_semantic_workspace", side_effect=evaluate
        ):
            _text, _fired, _note, stats = eval_behavioral.run_session(
                "prompt", REPO, timeout=10,
                semantic_oracle="handoff-builder-artifact",
            )

        self.assertEqual([], stats["semantic_findings"])
        self.assertEqual(0, stats["semantic_evidence"]["verifier_exit"])
        self.assertFalse(observed["cwd"].exists())


class ScratchCwdTest(unittest.TestCase):
    """%TEMP% write-blocking voided packet-slots-builder's premise (observed CLI 2.1.220)."""

    def test_scratch_root_is_not_under_the_temp_tree(self) -> None:
        temp_root = Path(tempfile.gettempdir()).resolve()
        scratch = eval_behavioral.SCRATCH_ROOT.resolve()
        self.assertNotIn(temp_root, [scratch, *scratch.parents])

    def test_scratch_cwd_exists_during_and_is_removed_after(self) -> None:
        with eval_behavioral.scratch_cwd() as cwd:
            self.assertTrue(cwd.is_dir())
            (cwd / "probe.txt").write_text("x", encoding="utf-8")
        self.assertFalse(cwd.exists())


class HandoffFunctionalWorkspaceTest(unittest.TestCase):
    """The builder case is graded on trusted end state, not a prose claim of success."""

    @staticmethod
    def _write_passing_artifacts(cwd: Path) -> None:
        (cwd / "openbao.json").write_text(
            json.dumps({"storage": "raft", "swap": "denied"}) + "\n",
            encoding="utf-8",
        )
        (cwd / "inventory.json").write_text(
            json.dumps({
                "service_count": 8,
                "groups": {"bao-readers": ["svc-bao"]},
            }) + "\n",
            encoding="utf-8",
        )
        (cwd / "regression-tests.json").write_text(
            json.dumps({
                "assertions": [
                    "disable_mlock_absent",
                    "swap_denied",
                    "parsed_membership",
                ]
            }) + "\n",
            encoding="utf-8",
        )

    def test_seeded_fixture_fails_then_passing_end_state_is_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            eval_behavioral.prepare_semantic_workspace(cwd, "handoff-builder-artifact")

            initial_failures, initial_evidence = eval_behavioral.evaluate_semantic_workspace(
                cwd, "handoff-builder-artifact"
            )
            self.assertTrue(initial_failures)
            self.assertNotEqual(0, initial_evidence["verifier_exit"])

            self._write_passing_artifacts(cwd)
            failures, evidence = eval_behavioral.evaluate_semantic_workspace(
                cwd, "handoff-builder-artifact"
            )

        self.assertEqual([], failures)
        self.assertEqual(0, evidence["verifier_exit"])
        self.assertEqual("acceptance: PASS", evidence["verifier_stdout"])
        self.assertEqual(
            {"inventory.json", "openbao.json", "regression-tests.json"},
            set(evidence["artifact_sha256"]),
        )
        for digest in evidence["artifact_sha256"].values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_changed_trusted_verifier_is_rejected_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            eval_behavioral.prepare_semantic_workspace(cwd, "handoff-builder-artifact")
            (cwd / "acceptance.py").write_text(
                "print('forged pass')\n", encoding="utf-8"
            )
            failures, evidence = eval_behavioral.evaluate_semantic_workspace(
                cwd, "handoff-builder-artifact"
            )

        self.assertTrue(any("trusted verifier changed" in failure for failure in failures))
        self.assertIsNone(evidence["verifier_exit"])

    def test_oversized_artifact_is_rejected_before_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = cwd / "openbao.json"
            with artifact.open("wb") as stream:
                stream.truncate(eval_behavioral._SEMANTIC_FILE_LIMIT + 1)

            with mock.patch.object(
                Path,
                "open",
                side_effect=AssertionError("oversized artifact was opened"),
            ), self.assertRaisesRegex(eval_routing.ProvenanceError, "exceeds"):
                eval_behavioral._semantic_regular_file(cwd, "openbao.json")

    def test_text_only_semantic_oracle_does_not_create_or_grade_a_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            eval_behavioral.prepare_semantic_workspace(cwd, "closed-learning-block")
            failures, evidence = eval_behavioral.evaluate_semantic_workspace(
                cwd, "closed-learning-block"
            )

        self.assertEqual([], failures)
        self.assertIsNone(evidence)

    def test_digest_rejection_requires_exact_hash_command_and_unchanged_workspace(self) -> None:
        case = next(
            case
            for case in eval_behavioral.load_cases("handoff-builder-rejects-digest-mismatch")
        )
        work_order = (
            case["prompt"]
            .split("---BEGIN WORK ORDER---\n", 1)[1]
            .split("---END WORK ORDER---", 1)[0]
            .encode("utf-8")
        )
        command = eval_behavioral._handoff_digest_command(work_order)
        actual_digest = hashlib.sha256(work_order).hexdigest()
        transcript = "\n".join((
            json.dumps({
                "message": {"content": [{
                    "type": "tool_use", "id": "hash-1", "name": "Bash",
                    "input": {"command": command},
                }]}
            }),
            json.dumps({
                "message": {"content": [{
                    "type": "tool_result", "tool_use_id": "hash-1",
                    "content": actual_digest, "is_error": False,
                }]}
            }),
        ))

        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            eval_behavioral.prepare_semantic_workspace(
                cwd, "handoff-digest-rejection"
            )
            failures, evidence = eval_behavioral.evaluate_semantic_workspace(
                cwd,
                "handoff-digest-rejection",
                prompt=case["prompt"],
                transcript=transcript,
            )
            self.assertEqual([], failures)
            self.assertEqual(actual_digest, evidence["computed_digest"])
            self.assertTrue(evidence["workspace_unchanged"])

            missing_command, _evidence = eval_behavioral.evaluate_semantic_workspace(
                cwd,
                "handoff-digest-rejection",
                prompt=case["prompt"],
                transcript="",
            )
            self.assertTrue(
                any("exact digest command" in finding for finding in missing_command)
            )

            missing_result, _evidence = eval_behavioral.evaluate_semantic_workspace(
                cwd,
                "handoff-digest-rejection",
                prompt=case["prompt"],
                transcript=transcript.splitlines()[0],
            )
            self.assertTrue(
                any("no correlated result" in finding for finding in missing_result)
            )

            extra_command = transcript + "\n" + json.dumps({
                "message": {"content": [{
                    "type": "tool_use", "id": "extra-1", "name": "Bash",
                    "input": {"command": "echo extra"},
                }]}
            })
            extra, _evidence = eval_behavioral.evaluate_semantic_workspace(
                cwd,
                "handoff-digest-rejection",
                prompt=case["prompt"],
                transcript=extra_command,
            )
            self.assertTrue(
                any("only Bash command" in finding for finding in extra)
            )

            (cwd / "unexpected.txt").write_text("edited\n", encoding="utf-8")
            changed, _evidence = eval_behavioral.evaluate_semantic_workspace(
                cwd,
                "handoff-digest-rejection",
                prompt=case["prompt"],
                transcript=transcript,
            )
            self.assertTrue(any("workspace changed" in finding for finding in changed))


class BehavioralCaseSchemaTest(unittest.TestCase):
    """Definitions fail before sessions when an assertion is misspelled or vacuous."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (REPO / "evals" / "behavioral" / "contracts.json").read_text(
                encoding="utf-8"
            )
        )

    def _minimal_case(self) -> dict:
        return {
            "id": "schema-probe",
            "prompt": "Produce the required answer.",
            "expected": "The answer contains the semantic marker.",
            "tags": ["schema"],
            "allowed_tools": [],
            "expect_fires": ["runbook"],
            "must_match": ["marker"],
        }

    def test_all_shipped_cases_pin_the_minimum_positive_tool_boundary(self) -> None:
        scratch_cases = {
            "packet-slots-builder",
            "ladder-report-not-absorb",
            "verifier-fails-honestly-no-product-edit",
            "handoff-builder-applies-work-order",
        }
        hash_only_cases = {"handoff-builder-rejects-digest-mismatch"}
        self.assertEqual(64, len(self.document["cases"]))
        for case in self.document["cases"]:
            with self.subTest(case=case["id"]):
                if case["id"] in scratch_cases:
                    self.assertEqual(["Bash", "Write"], case["allowed_tools"])
                elif case["id"] in hash_only_cases:
                    self.assertEqual(["Bash"], case["allowed_tools"])
                elif "agent" in case:
                    self.assertEqual([], case["allowed_tools"])
                else:
                    self.assertEqual(["Skill"], case["allowed_tools"])

    def test_public_load_cases_none_retains_all_cases_compatibility(self) -> None:
        expected, _ = eval_behavioral.load_cases_with_sources("*")

        actual = _eval_behavioral_bootstrap.load_cases(None)

        self.assertEqual(
            [case["id"] for case in expected],
            [case["id"] for case in actual],
        )

    def test_unknown_root_and_case_fields_are_rejected(self) -> None:
        root_typo = {**self.document, "notse": self.document["notes"]}
        case_typo = {
            **self.document,
            "cases": [{**self._minimal_case(), "must_macth": ["marker"]}],
        }
        self.assertTrue(any("unknown root" in f for f in eval_behavioral.validate_case_document(root_typo)))
        self.assertTrue(any("must_macth" in f for f in eval_behavioral.validate_case_document(case_typo)))

    def test_learning_mode_with_learningless_shape_is_rejected(self) -> None:
        # lint_packet grades the Learning block only when the shape carries a `learning` slot,
        # so this pairing used to validate and run while asserting nothing about Learning --
        # a silently-dropped configuration reporting green (review finding).
        case = {
            **self._minimal_case(),
            "packet_shape": "verification-packet",
            "packet_learning_mode": "lifecycle-owner",
        }
        document = {**self.document, "cases": [case]}
        findings = eval_behavioral.validate_case_document(document)
        self.assertTrue(any("silently never run" in f for f in findings), findings)

    def test_required_fields_and_unique_ids_are_enforced(self) -> None:
        for field in ("id", "prompt", "expected", "tags"):
            with self.subTest(field=field):
                case = self._minimal_case()
                del case[field]
                document = {**self.document, "cases": [case]}
                findings = eval_behavioral.validate_case_document(document)
                self.assertTrue(any(field in finding for finding in findings), findings)
        case = self._minimal_case()
        findings = eval_behavioral.validate_case_document(
            {**self.document, "cases": [case, dict(case)]}
        )
        self.assertTrue(any("duplicated" in finding for finding in findings), findings)

    def test_types_enums_components_regexes_and_nonempty_lists_fail_closed(self) -> None:
        mutations = (
            ("empty tags", {"tags": []}, "non-empty list"),
            ("bad mode", {"packet_learning_mode": "owner"}, "packet_learning_mode"),
            ("bad shape", {"packet_shape": "runbok"}, "packet_shape"),
            ("bad semantic oracle", {"semantic_oracle": "prose-judge"}, "semantic_oracle"),
            ("bad permission", {"permission_mode": "bypassPermissions"}, "permission_mode"),
            ("bad component", {"expect_fires": ["no-such-component"]}, "component"),
            ("bad denied tool", {"disallowed_tools": ["BsaH"]}, "runtime tool"),
            ("bad allowed tool", {"allowed_tools": ["PwerShell"]}, "runtime tool"),
            (
                "overlapping tool bounds",
                {"allowed_tools": ["Bash"], "disallowed_tools": ["Bash"]},
                "overlap",
            ),
            ("bare agent", {"agent": "sde-fullstack"}, "plugin-qualified"),
            ("bad regex", {"must_match": ["("]}, "valid regex"),
        )
        for label, mutation, expected in mutations:
            with self.subTest(label=label):
                case = {**self._minimal_case(), **mutation}
                findings = eval_behavioral.validate_case_document(
                    {**self.document, "cases": [case]}
                )
                self.assertTrue(any(expected in finding for finding in findings), findings)

    def test_non_string_enum_values_return_findings_instead_of_raising(self) -> None:
        for field in (
            "permission_mode", "packet_shape", "packet_learning_mode", "semantic_oracle"
        ):
            for value in ([], {}, 17):
                with self.subTest(field=field, value=value):
                    findings = eval_behavioral.validate_behavioral_case(
                        {**self._minimal_case(), field: value}
                    )
                    self.assertTrue(any(field in finding for finding in findings), findings)
        for value in ([], {}, 17):
            with self.subTest(field="agent", value=value):
                findings = eval_behavioral.validate_behavioral_case(
                    {**self._minimal_case(), "agent": value}
                )
                self.assertTrue(any("agent" in finding for finding in findings), findings)

    def test_full_case_requires_exactly_one_component_fire_contract(self) -> None:
        missing = self._minimal_case()
        del missing["expect_fires"]
        both = {
            **self._minimal_case(),
            "expect_all_fires": ["self-improve-loop"],
        }
        empty = {**self._minimal_case(), "expect_fires": []}
        for label, case in (("missing", missing), ("both", both), ("empty", empty)):
            with self.subTest(label=label):
                findings = eval_behavioral.validate_behavioral_case(case)
                self.assertTrue(
                    any("component-fire contract" in finding or "non-empty list" in finding
                        for finding in findings),
                    findings,
                )

    def test_positive_regex_cannot_match_empty_output(self) -> None:
        for pattern in (".*", "^.*$", "(?:)", "x?"):
            with self.subTest(pattern=pattern):
                findings = eval_behavioral.validate_behavioral_case(
                    {**self._minimal_case(), "must_match": [pattern]}
                )
                self.assertTrue(any("matches the empty string" in f for f in findings), findings)

    def test_positive_regex_requires_a_substantive_raw_literal(self) -> None:
        for pattern in (".", r"\S", r"\b", r"[\s\S]", "(?=x)", ".{1}"):
            with self.subTest(pattern=pattern):
                findings = eval_behavioral.validate_behavioral_case(
                    {**self._minimal_case(), "must_match": [pattern]}
                )
                self.assertTrue(
                    any("raw alphanumeric literal" in finding for finding in findings),
                    findings,
                )

    def test_exact_fields_schema_is_closed_typed_and_semantic(self) -> None:
        base = self._minimal_case()
        base.pop("must_match")
        valid = {**base, "exact_fields": {"Promotion state": "inconclusive"}}
        self.assertEqual([], eval_behavioral.validate_behavioral_case(valid))
        mutations = (
            ({"exact_fields": []}, "non-empty object"),
            ({"exact_fields": {}}, "non-empty object"),
            ({"exact_fields": {"Promoton state": "inconclusive"}}, "unknown literal"),
            ({"exact_fields": {"Promotion state": ""}}, "non-empty exact string"),
            ({"exact_fields": {"Promotion state": "   "}}, "non-empty exact string"),
            ({"exact_fields": {"Promotion state": 7}}, "non-empty exact string"),
        )
        for mutation, expected in mutations:
            with self.subTest(mutation=mutation):
                findings = eval_behavioral.validate_behavioral_case({**base, **mutation})
                self.assertTrue(any(expected in finding for finding in findings), findings)

    def test_full_case_requires_explicit_allowed_tools_even_when_empty(self) -> None:
        case = self._minimal_case()
        del case["allowed_tools"]
        findings = eval_behavioral.validate_behavioral_case(case)
        self.assertTrue(any("allowed_tools" in finding for finding in findings), findings)

    def test_routing_or_absence_only_case_has_no_semantic_output_oracle(self) -> None:
        case = self._minimal_case()
        del case["must_match"]
        case["expect_fires"] = ["runbook"]
        case["must_not_match"] = ["forbidden"]
        findings = eval_behavioral.validate_case_document(
            {**self.document, "cases": [case]}
        )
        self.assertTrue(any("semantic output oracle" in finding for finding in findings), findings)

    def test_direct_grader_rejects_unknown_assertion_key(self) -> None:
        failures = eval_behavioral.assert_case("marker", {"must_macth": ["marker"]})
        self.assertTrue(any("must_macth" in failure for failure in failures), failures)

    def test_loader_rejects_invalid_document_before_returning_any_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp)
            invalid = {**self.document, "cases": [{**self._minimal_case(), "must_macth": ["x"]}]}
            (case_dir / "invalid.json").write_text(
                json.dumps(invalid), encoding="utf-8"
            )
            with mock.patch.object(eval_behavioral, "CASES_DIR", case_dir):
                with self.assertRaises(eval_behavioral.BehavioralCaseError):
                    eval_behavioral.load_cases_with_sources("*")


class HandoffBehavioralCasesTest(unittest.TestCase):
    """Claude transfers one work order, then grades receipts and resulting state."""

    CASE_IDS = {
        "handoff-producer-preserves-discovered-constraints",
        "handoff-discovery-is-evidence-and-capture-safe",
        "handoff-first-artifact-keeps-open-work",
        "handoff-simple-build-stays-short",
        "handoff-builder-applies-work-order",
        "handoff-builder-rejects-digest-mismatch",
    }

    @classmethod
    def setUpClass(cls) -> None:
        document = json.loads(
            (REPO / "evals" / "behavioral" / "contracts.json").read_text(
                encoding="utf-8"
            )
        )
        cls.cases = {case["id"]: case for case in document["cases"]}

    def test_inventory_is_six_focused_cases_without_a_packet_shape(self) -> None:
        actual = {case_id for case_id in self.cases if case_id.startswith("handoff-")}
        self.assertEqual(self.CASE_IDS, actual)
        for case_id in self.CASE_IDS:
            self.assertNotIn("packet_shape", self.cases[case_id])
        self.assertFalse(any(
            case.get("agent") == "sde-agents:code-reviewer"
            for case in self.cases.values()
            if case["id"].startswith("handoff-")
        ))

    def test_consumer_contract_verifies_digest_and_accepts_source_free_none(self) -> None:
        text = (REPO / "agents" / "sde-fullstack.md").read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn("recompute SHA-256", normalized)
        self.assertIn("digest does not match", normalized)
        self.assertIn("An explicit `none` is complete", normalized)

    def test_sixth_case_is_the_digest_mismatch_negative(self) -> None:
        case = self.cases["handoff-builder-rejects-digest-mismatch"]
        self.assertNotIn("handoff-builder-returns-conflict-receipt", self.cases)
        self.assertIn("Decisions and evidence: none", case["prompt"])
        self.assertEqual(["Bash"], case["allowed_tools"])
        self.assertEqual("handoff-digest-rejection", case["semantic_oracle"])
        self.assertIn("python -I -c", case["prompt"])

    def _controls(self) -> dict[str, tuple[str, str, tuple[str, ...]]]:
        return {
            "handoff-producer-preserves-discovered-constraints": (
                "homelab-platform",
                """**Work Order v1:**
**Work-order ID:** openbao-staged-config-v1
**Objective:** OpenBao configuration and tests only; live activation is out of scope.
**Decisions and evidence:** Raft is fixed. Source POC-42 proves server -verify-only is removed in OpenBao 2.6.1.
**Forbidden regressions:** disable_mlock is removed from code and tests; swap remains denied; use operator validate-config. Parse the svc-bao membership relationship in bao-readers instead of accepting string co-occurrence.
**Acceptance and invariants:** validate the config, parse the enrolled member relationship, change service_count from 7 to 8, and preserve generated-source parity.
**Authority and recovery:** Tier 1 staged artifact only; no live authority is transferred.
**Work state:** TLS custody blocks live activation; monitoring remains open with the platform owner.
""",
                (
                    "Add disable_mlock to the config and test assertion.\n",
                    "Do not remove disable_mlock.\n",
                    "Enable swap for this service.\n",
                    "operator validate-config must not be used.\n",
                    "String co-occurrence is sufficient for membership.\n",
                    "Proceed with live activation now.\n",
                ),
            ),
            "handoff-discovery-is-evidence-and-capture-safe": (
                "homelab-platform",
                """Work Order v1:
Work-order ID: discovery-correction-v1
Decisions and evidence: Ansible check mode skipped the command, so the registered result is not evidence; run a direct Tier 0 read-only probe.
Acceptance and invariants: record the probe result and its known check-mode limitation.
Authority and recovery: observation only.
Work state: the probe is blocking.
Secret-safe capture uses a field-scoped non-secret projection and vault references; never include resolved passwords.
""",
                (
                    "No fallback probe is needed.\n",
                    "The registered result remains reliable evidence.\n",
                    "Put the decrypted exporter password in the handoff.\n",
                ),
            ),
            "handoff-first-artifact-keeps-open-work": (
                "homelab-platform",
                """[Unit]
Description=OpenBao
After=network-online.target
Wants=network-online.target

[Service]
User=openbao
ExecStart=/usr/bin/bao server -config=/etc/openbao.d
Restart=on-failure

[Install]
WantedBy=multi-user.target

This is a staged Tier 1 artifact and remains unapplied.
TLS custody is missing and blocks live activation.
Initialization recipients are missing and block live activation.
Backups: open; owner: storage.
Monitoring: open; owner: observability.
Runbook: open; owner: service operations.
Restore drill: open; owner: operator.
""",
                (
                    "Backups are complete.\n",
                    "OpenBao is now deployed.\n",
                    "TLS is ready.\n",
                    "Initialization can proceed.\n",
                ),
            ),
            "handoff-simple-build-stays-short": (
                "homelab-platform",
                """**Deliverable:** prepare the stateless link-shortener compose service definition as a Tier 1 unapplied artifact.
**Acceptance:** require a healthy container and an internal reachability check.
**Authority:** live activation remains Tier 2 and requires explicit approval.
""",
                (
                    "Work Order v1:\n",
                    "Decisions and evidence: none.\n",
                    "Skip health verification.\n",
                    "Tier 2 requires no approval.\n",
                    "Container health is optional.\n",
                    "Approval is not required.\n",
                ),
            ),
            "handoff-builder-rejects-digest-mismatch": (
                "sde-fullstack",
                """Handoff receipt: input-required
Work-order ID: source-free-staged-build-v1
Work-order digest: sha256:REPLACE_FROM_CASE
Conflicts: Work-order digest
Recommended resolution: recompute the digest over the normalized block and resend a matching digest.
""",
                (
                    "Handoff receipt: accepted\n",
                    "Conflicts: Decisions and evidence\n",
                    "Before editing, I echo the work order.\n",
                ),
            ),
        }

    @staticmethod
    def _work_order_and_digest(case: dict) -> tuple[str, str]:
        prompt = case["prompt"]
        start = "---BEGIN WORK ORDER---\n"
        end = "---END WORK ORDER---"
        work_order = prompt.split(start, 1)[1].split(end, 1)[0]
        digest_match = re.search(r"Work-order digest: sha256:([0-9a-f]{64})", prompt)
        if digest_match is None:
            raise AssertionError("case prompt has no work-order digest")
        return work_order, digest_match.group(1)

    def _resolved_controls(self) -> dict[str, tuple[str, str, tuple[str, ...]]]:
        controls = self._controls()
        case_id = "handoff-builder-rejects-digest-mismatch"
        _work_order, digest = self._work_order_and_digest(self.cases[case_id])
        agent, valid, contradictions = controls[case_id]
        controls[case_id] = (
            agent,
            valid.replace("REPLACE_FROM_CASE", digest),
            contradictions,
        )
        return controls

    def _assert_control(self, case_id: str, text: str, agent: str) -> list[str]:
        case = self.cases[case_id]
        semantic_findings = [] if case.get("semantic_oracle") else None
        return eval_behavioral.assert_case(
            text, case, {agent}, semantic_findings=semantic_findings
        )

    def test_each_case_accepts_one_correct_control(self) -> None:
        for case_id, (agent, valid, _contradictions) in self._resolved_controls().items():
            with self.subTest(case=case_id, control="valid"):
                self.assertEqual([], self._assert_control(case_id, valid, agent))

    def test_every_required_pattern_fails_when_its_match_is_removed(self) -> None:
        for case_id, (agent, valid, _contradictions) in self._resolved_controls().items():
            for pattern in self.cases[case_id]["must_match"]:
                mutated, replacements = re.subn(
                    pattern, "<omitted>", valid, flags=re.IGNORECASE | re.MULTILINE
                )
                with self.subTest(case=case_id, pattern=pattern):
                    self.assertGreater(replacements, 0)
                    failures = self._assert_control(case_id, mutated, agent)
                    self.assertIn(f"missing required pattern: {pattern!r}", failures)

    def test_every_forbidden_pattern_rejects_an_isolated_contradiction(self) -> None:
        for case_id, (agent, valid, contradictions) in self._resolved_controls().items():
            patterns = self.cases[case_id]["must_not_match"]
            with self.subTest(case=case_id, control="count"):
                self.assertEqual(len(patterns), len(contradictions))
            for pattern, contradiction in zip(patterns, contradictions, strict=True):
                with self.subTest(case=case_id, pattern=pattern):
                    self.assertRegex(contradiction, re.compile(pattern))
                    failures = self._assert_control(
                        case_id, valid + contradiction, agent
                    )
                    self.assertEqual(
                        [f"forbidden pattern present: {pattern!r}"],
                        [
                            failure
                            for failure in failures
                            if failure.startswith("forbidden pattern present:")
                        ],
                    )

    def test_safe_vault_reference_is_not_mistaken_for_secret_capture(self) -> None:
        agent, valid, _contradictions = self._resolved_controls()[
            "handoff-discovery-is-evidence-and-capture-safe"
        ]
        safe = valid + "Include only vault paths; never include resolved credential values.\n"
        self.assertEqual(
            [],
            eval_behavioral.assert_case(
                safe,
                self.cases["handoff-discovery-is-evidence-and-capture-safe"],
                {agent},
            ),
        )

    def test_safe_negations_do_not_trip_handoff_forbidden_patterns(self) -> None:
        controls = self._resolved_controls()
        safe_suffixes = {
            "handoff-first-artifact-keeps-open-work": "Backups are not complete.\n",
        }
        for case_id, suffix in safe_suffixes.items():
            agent, valid, _contradictions = controls[case_id]
            with self.subTest(case=case_id):
                self.assertEqual(
                    [],
                    eval_behavioral.assert_case(
                        valid + suffix, self.cases[case_id], {agent}
                    ),
                )

    def test_work_order_digests_bind_the_exact_supplied_bytes(self) -> None:
        functional = self.cases["handoff-builder-applies-work-order"]
        work_order, recorded = self._work_order_and_digest(functional)
        actual = hashlib.sha256(work_order.encode("utf-8")).hexdigest()
        self.assertEqual(recorded, actual)

        mismatch = self.cases["handoff-builder-rejects-digest-mismatch"]
        work_order, recorded = self._work_order_and_digest(mismatch)
        actual = hashlib.sha256(work_order.encode("utf-8")).hexdigest()
        self.assertNotEqual("0" * 64, recorded)
        self.assertNotEqual(recorded, actual)
        self.assertEqual(1, sum(left != right for left, right in zip(recorded, actual)))

    def test_digest_mismatch_receipt_cannot_pass_without_semantic_evidence(self) -> None:
        case = self.cases["handoff-builder-rejects-digest-mismatch"]
        agent, valid, _contradictions = self._resolved_controls()[case["id"]]

        failures = eval_behavioral.assert_case(valid, case, {agent})

        self.assertTrue(any("workspace evidence unavailable" in failure for failure in failures))

    def test_functional_builder_requires_end_state_evidence_and_minimal_receipt(self) -> None:
        case = self.cases["handoff-builder-applies-work-order"]
        self.assertEqual("handoff-builder-artifact", case["semantic_oracle"])
        self.assertEqual(["Bash", "Write"], case["allowed_tools"])
        self.assertEqual("acceptEdits", case["permission_mode"])
        _work_order, digest = self._work_order_and_digest(case)
        receipt = (
            "Handoff receipt: accepted\n"
            "Work-order ID: openbao-staged-config-v1\n"
            f"Work-order digest: sha256:{digest}\n"
        )

        unavailable = eval_behavioral.assert_case(
            receipt, case, {"sde-fullstack"}
        )
        self.assertTrue(any("workspace evidence unavailable" in failure for failure in unavailable))
        self.assertEqual(
            [],
            eval_behavioral.assert_case(
                receipt, case, {"sde-fullstack"}, semantic_findings=[]
            ),
        )


class RunbookProposalPacketTest(unittest.TestCase):
    """The proposal oracle accepts only the skill's closed, non-procedural gap packet."""

    @classmethod
    def setUpClass(cls) -> None:
        document = json.loads(
            (REPO / "evals" / "behavioral" / "contracts.json").read_text(encoding="utf-8")
        )
        cls.case = next(
            case for case in document["cases"] if case["id"] == "runbook-disposition-propose"
        )
        cls.valid = (
            "Runbook disposition: propose\n"
            "Prospective canonical path: unknown\n"
            "Missing evidence: owner, canonical inventory, current configuration, "
            "authoritative source, exact safe command, safe replay\n"
            "Owner: unknown\n"
            "Next verification: identify owner, inventory canonical runbooks, "
            "inspect current configuration, obtain authoritative source, "
            "obtain exact safe command, establish safe replay\n"
        )
        cls.known_identity = (
            "Runbook disposition: propose\n"
            "Prospective canonical path: ops/widget-recovery.md\n"
            "Missing evidence: current configuration\n"
            "Owner: platform-sre\n"
            "Next verification: inspect current configuration\n"
        )

    def _assert_proposal_rejected(self, text: str) -> None:
        failures = eval_behavioral.assert_case(text, self.case, {"runbook"})
        self.assertTrue(any(failure.startswith("packet:") for failure in failures), failures)

    def test_exact_five_line_packet_is_valid(self) -> None:
        self.assertEqual(
            [], eval_behavioral.assert_case(self.valid, self.case, {"runbook"})
        )

    def test_owner_identifier_admits_safe_team_punctuation(self) -> None:
        for owner in (
            "platform-sre",
            "platform.sre_oncall+primary@example.com",
            "a" * 64,
        ):
            with self.subTest(owner=owner):
                text = re.sub(r"(?m)^Owner:.*$", f"Owner: {owner}", self.known_identity)
                self.assertEqual([], eval_behavioral.lint_runbook_proposal(text))

    def test_next_verification_is_a_finite_vocabulary_not_a_first_verb_heuristic(self) -> None:
        unsafe_values = (
            "apt-get install mystery",
            "touch mystery.ready",
            "/usr/local/bin/mystery --force",
            "mysteryctl --force",
            "Execute the recovery now",
            "verify systemctl restart",
            "test 1",
            "ask owner to execute reboot",
            "identify owner, systemctl restart mystery",
            "review https://example.invalid/recovery",
            "verify `docker restart mystery`",
        )
        for value in unsafe_values:
            with self.subTest(value=value):
                text = re.sub(
                    r"(?m)^Next verification:.*$", f"Next verification: {value}", self.valid
                )
                self._assert_proposal_rejected(text)

    def test_command_or_procedure_content_is_rejected_in_every_field(self) -> None:
        replacements = {
            "Runbook disposition": "propose; reboot",
            "Prospective canonical path": "/usr/local/bin/systemctl",
            "Missing evidence": "owner, touch /tmp/ready",
            "Owner": "platform-sre execute reboot",
            "Next verification": "ask owner to execute reboot",
        }
        for label, value in replacements.items():
            with self.subTest(label=label, value=value):
                text = re.sub(rf"(?m)^{re.escape(label)}:.*$", f"{label}: {value}", self.valid)
                self._assert_proposal_rejected(text)

    def test_finite_lists_reject_unknown_duplicate_reordered_and_bad_delimiters(self) -> None:
        replacements = (
            ("Missing evidence", "owner, owner"),
            ("Missing evidence", "safe replay, owner"),
            ("Missing evidence", "owner; canonical inventory"),
            ("Missing evidence", "owner, shell access"),
            ("Next verification", "identify owner, identify owner"),
            ("Next verification", "establish safe replay, identify owner"),
            ("Next verification", "identify owner; inventory canonical runbooks"),
            ("Next verification", "identify owner, execute reboot"),
        )
        for label, value in replacements:
            with self.subTest(label=label, value=value):
                text = re.sub(rf"(?m)^{label}:.*$", f"{label}: {value}", self.valid)
                self._assert_proposal_rejected(text)

    def test_every_missing_gap_requires_its_matching_verification(self) -> None:
        mismatches = (
            (
                "Missing evidence: owner, canonical inventory, current configuration, "
                "authoritative source, exact safe command, safe replay",
                "Next verification: identify owner, inventory canonical runbooks, "
                "obtain authoritative source, inspect current configuration, "
                "obtain exact safe command, establish safe replay",
            ),
            (
                "Missing evidence: owner, canonical inventory, current configuration, "
                "authoritative source, exact safe command, safe replay",
                "Next verification: identify owner, inventory canonical runbooks, "
                "inspect current configuration, obtain authoritative source, "
                "establish safe replay",
            ),
        )
        for missing, verification in mismatches:
            with self.subTest(verification=verification):
                lines = self.valid.splitlines()
                lines[2] = missing
                lines[4] = verification
                self._assert_proposal_rejected("\n".join(lines))

    def test_case_specific_oracle_requires_all_six_prompt_declared_gaps(self) -> None:
        for omitted in self.case["runbook_required_gaps"]:
            with self.subTest(omitted=omitted):
                gaps = [
                    gap for gap in self.case["runbook_required_gaps"] if gap != omitted
                ]
                verifications = [
                    eval_behavioral._RUNBOOK_PROPOSAL_VERIFICATIONS[
                        eval_behavioral._RUNBOOK_PROPOSAL_GAPS.index(gap)
                    ]
                    for gap in gaps
                ]
                text = re.sub(
                    r"(?m)^Missing evidence:.*$",
                    "Missing evidence: " + ", ".join(gaps),
                    self.valid,
                )
                text = re.sub(
                    r"(?m)^Next verification:.*$",
                    "Next verification: " + ", ".join(verifications),
                    text,
                )
                self._assert_proposal_rejected(text)

    def test_case_oracle_admits_additional_genuinely_missing_gaps(self) -> None:
        """The declared set is a floor, not a ceiling — the observed live answer reported eight.

        `current applicability` and `edit authority` are unestablished by the same prompt and are
        named triggers of the runbook skill's own `propose` rule, so reporting them is correct.
        Each still has to carry its matching verification, which is what keeps this from being a
        blanket pass.
        """
        gaps = list(eval_behavioral._RUNBOOK_PROPOSAL_GAPS)
        verifications = list(eval_behavioral._RUNBOOK_PROPOSAL_VERIFICATIONS)
        self.assertTrue(set(self.case["runbook_required_gaps"]) < set(gaps))
        text = re.sub(
            r"(?m)^Missing evidence:.*$", "Missing evidence: " + ", ".join(gaps), self.valid
        )
        text = re.sub(
            r"(?m)^Next verification:.*$",
            "Next verification: " + ", ".join(verifications),
            text,
        )
        self.assertEqual([], eval_behavioral.assert_case(text, self.case, {"runbook"}))

        # ... but an extra gap whose verification is absent is still rejected.
        broken = re.sub(
            r"(?m)^Next verification:.*$",
            "Next verification: " + ", ".join(verifications[:-1]),
            text,
        )
        self._assert_proposal_rejected(broken)

    def test_unknown_path_and_owner_imply_inventory_and_owner_gaps(self) -> None:
        packet = (
            "Runbook disposition: propose\n"
            "Prospective canonical path: unknown\n"
            "Missing evidence: current configuration\n"
            "Owner: unknown\n"
            "Next verification: inspect current configuration\n"
        )
        findings = eval_behavioral.lint_runbook_proposal(packet)
        self.assertTrue(any("canonical inventory" in finding for finding in findings), findings)
        self.assertTrue(any("owner" in finding for finding in findings), findings)

    def test_declared_identity_gaps_forbid_known_path_or_owner(self) -> None:
        contradictions = (
            (
                "Prospective canonical path: unknown",
                "Prospective canonical path: ops/widget-recovery.md",
                "canonical inventory",
            ),
            ("Owner: unknown", "Owner: platform-sre", "owner"),
        )
        for old, new, expected in contradictions:
            with self.subTest(new=new):
                findings = eval_behavioral.lint_runbook_proposal(
                    self.valid.replace(old, new)
                )
                self.assertTrue(any(expected in finding for finding in findings), findings)

    def test_owner_and_path_grammars_reject_unsafe_punctuation_and_traversal(self) -> None:
        replacements = (
            ("Owner", "platform sre"),
            ("Owner", "platform/sre"),
            ("Owner", "platform:sre"),
            ("Owner", "`platform-sre`"),
            ("Owner", "-platform-sre"),
            ("Owner", "a" * 65),
            ("Prospective canonical path", "../ops/runbook.md"),
            ("Prospective canonical path", "ops/./runbook.md"),
            ("Prospective canonical path", "C:/ops/runbook.md"),
            ("Prospective canonical path", "https://example.invalid/runbook.md"),
            ("Prospective canonical path", "ops/runbook.sh"),
            ("Prospective canonical path", "CON.md"),
            ("Prospective canonical path", "aux.md"),
            ("Prospective canonical path", "COM1.md"),
            ("Prospective canonical path", "LPT9.md"),
            ("Prospective canonical path", "ops./widget.md"),
        )
        for label, value in replacements:
            with self.subTest(label=label, value=value):
                text = re.sub(
                    rf"(?m)^{label}:.*$", f"{label}: {value}", self.known_identity
                )
                findings = eval_behavioral.lint_runbook_proposal(text)
                self.assertTrue(any(label in finding for finding in findings), findings)

    def test_extra_narrative_is_rejected_regardless_of_position(self) -> None:
        for text in (
            "Here is the requested proposal.\n" + self.valid,
            self.valid + "This is only a suggestion.\n",
        ):
            with self.subTest(text=text):
                self._assert_proposal_rejected(text)

    def test_missing_duplicate_reordered_and_malformed_fields_are_rejected(self) -> None:
        lines = self.valid.splitlines()
        malformed_packets = (
            "\n".join(lines[:-1]),
            "\n".join([*lines[:4], lines[3], lines[4]]),
            "\n".join([lines[0], lines[2], lines[1], *lines[3:]]),
            "\n".join([lines[0], "Prospective canonical path - unknown", *lines[2:]]),
            "\n".join([lines[0], "Prospective canonical path: ", *lines[2:]]),
            "\n".join(["Runbook disposition: update", *lines[1:]]),
        )
        for text in malformed_packets:
            with self.subTest(text=text):
                self._assert_proposal_rejected(text)

    def test_other_packet_shapes_still_delegate_to_packet_lint(self) -> None:
        with mock.patch.object(
            eval_behavioral.packet_lint, "lint_packet", return_value=["sentinel finding"]
        ) as lint_packet:
            failures = eval_behavioral.assert_case(
                "packet text", {"packet_shape": "review-packet"}
            )
        lint_packet.assert_called_once_with("packet text", "review-packet")
        self.assertEqual(["packet: sentinel finding"], failures)

    def test_skill_and_oracle_publish_the_same_closed_vocabulary(self) -> None:
        skill = (REPO / "skills" / "runbook" / "SKILL.md").read_text(encoding="utf-8")
        expected_fields = (
            "Runbook disposition",
            "Prospective canonical path",
            "Missing evidence",
            "Owner",
            "Next verification",
        )
        expected_gaps = (
            "owner",
            "canonical inventory",
            "current applicability",
            "current configuration",
            "edit authority",
            "authoritative source",
            "exact safe command",
            "safe replay",
        )
        expected_verifications = (
            "identify owner",
            "inventory canonical runbooks",
            "confirm current applicability",
            "inspect current configuration",
            "confirm edit authority",
            "obtain authoritative source",
            "obtain exact safe command",
            "establish safe replay",
        )
        self.assertEqual(expected_fields, eval_behavioral._RUNBOOK_PROPOSAL_FIELDS)
        self.assertEqual(expected_gaps, eval_behavioral._RUNBOOK_PROPOSAL_GAPS)
        self.assertEqual(
            expected_verifications, eval_behavioral._RUNBOOK_PROPOSAL_VERIFICATIONS
        )
        for literal in (*expected_fields, *expected_gaps, *expected_verifications):
            with self.subTest(literal=literal):
                self.assertIn(literal, skill)


class ComponentFireSemanticsTest(unittest.TestCase):
    """Any-of routes and all-of compositions are distinct deterministic contracts."""

    @classmethod
    def setUpClass(cls) -> None:
        document = json.loads(
            (REPO / "evals" / "behavioral" / "contracts.json").read_text(encoding="utf-8")
        )
        cls.compose = next(
            case for case in document["cases"]
            if case["id"] == "learning-runbook-namespaces-compose"
        )
        cls.compose_text = (
            "Learning disposition: merge\n"
            "Runbook disposition: update\n"
            "Destination: ops/widgets.md\n"
        )

    def test_expect_fires_remains_any_of_for_alternative_routes(self) -> None:
        case = {"expect_fires": ["prompt-craft", "prompt-engineer"]}
        self.assertEqual([], eval_behavioral.assert_case("answer", case, {"prompt-craft"}))

    def test_expect_all_fires_rejects_one_missing_component(self) -> None:
        failures = eval_behavioral.assert_case(
            self.compose_text, self.compose, {"runbook"}
        )
        self.assertTrue(any("self-improve-loop" in failure for failure in failures), failures)

    def test_expect_all_fires_accepts_both_components(self) -> None:
        self.assertEqual(
            [],
            eval_behavioral.assert_case(
                self.compose_text, self.compose, {"runbook", "self-improve-loop"}
            ),
        )

    def test_component_expectations_cannot_be_empty_or_wrongly_typed(self) -> None:
        for field, value in (
            ("expect_fires", []),
            ("expect_fires", "prompt-craft"),
            ("expect_all_fires", []),
            ("expect_all_fires", "runbook"),
        ):
            with self.subTest(field=field, value=value):
                failures = eval_behavioral.assert_case(
                    "answer", {field: value}, {"prompt-craft", "runbook"}
                )
                self.assertTrue(any("non-empty list" in failure for failure in failures))


class LearningCloseoutCasesTest(unittest.TestCase):
    """Every lifecycle owner is pinned on both closeout branches; intake stays separate."""

    @classmethod
    def setUpClass(cls) -> None:
        document = json.loads(
            (REPO / "evals" / "behavioral" / "contracts.json").read_text(encoding="utf-8")
        )
        cls.cases = {case["id"]: case for case in document["cases"]}

    def test_all_lifecycle_owners_have_none_and_full_retro_cases(self) -> None:
        for owner in ("sde-fullstack", "verification-engineer", "prompt-engineer"):
            for branch in ("none", "full-retro"):
                with self.subTest(owner=owner, branch=branch):
                    case = self.cases[f"learning-owner-{owner}-{branch}"]
                    self.assertEqual(f"sde-agents:{owner}", case["agent"])
                    self.assertEqual("lifecycle-owner", case["packet_learning_mode"])
                    self.assertEqual([owner], case["expect_fires"])
                    required = "\n".join(case["must_match"])
                    forbidden = "\n".join(case["must_not_match"])
                    expected_branch = "none" if branch == "none" else "candidate"
                    other_branch = "candidate" if branch == "none" else "none"
                    self.assertIn(expected_branch, required)
                    self.assertIn(other_branch, forbidden)
                    if branch == "none":
                        self.assertIn("no reusable signal", required)
                    else:
                        for literal in (
                            "learning disposition", "merge", "promotion state", "proposed",
                            "scripts/validate_fleet", "fleet-maintainer",
                        ):
                            self.assertIn(literal, required)

    def _full_retro_text(self, disposition: str = "merge", state: str = "proposed") -> str:
        return (
            "Changed: validation parity closeout\n"
            "Verified: `python -m unittest tests.test_validate_fleet -q` reported Ran 8 tests OK\n"
            "Check first: lifecycle matrix\n"
            "Learning: candidate — adapter parity was omitted -> parity is asserted\n"
            "Evidence: revisions aaaaaaaa and bbbbbbbb reproduced the omission\n"
            "Scope: generated-adapter validation only\n"
            "Provenance: verified — supplied revision and test evidence\n"
            f"Learning disposition: {disposition}\n"
            f"Promotion state: {state}\n"
            "Destination: scripts/validate_fleet.py\n"
            "Owner: fleet-maintainer\n"
        )

    def test_each_owner_full_retro_rejects_every_wrong_requested_decision(self) -> None:
        replacements = (
            ("Learning disposition: merge", "Learning disposition: add"),
            ("Promotion state: proposed", "Promotion state: approved"),
            ("Destination: scripts/validate_fleet.py", "Destination: docs/README.md"),
            ("Owner: fleet-maintainer", "Owner: docs-maintainer"),
        )
        for owner in ("sde-fullstack", "verification-engineer", "prompt-engineer"):
            case = self.cases[f"learning-owner-{owner}-full-retro"]
            self.assertEqual(
                [], eval_behavioral.assert_case(self._full_retro_text(), case, {owner})
            )
            for old, new in replacements:
                with self.subTest(owner=owner, wrong=new):
                    failures = eval_behavioral.assert_case(
                        self._full_retro_text().replace(old, new), case, {owner}
                    )
                    self.assertTrue(failures, (owner, new))

    def test_conflicting_duplicate_disposition_or_state_is_rejected(self) -> None:
        case = self.cases["learning-owner-verification-engineer-full-retro"]
        for duplicate in (
            "Learning disposition: add\n",
            "Promotion state: approved\n",
        ):
            with self.subTest(duplicate=duplicate):
                text = self._full_retro_text() + duplicate
                failures = eval_behavioral.assert_case(
                    text, case, {"verification-engineer"}
                )
                self.assertTrue(any("exactly one" in failure for failure in failures), failures)

    def test_promotion_missing_gates_requires_skip_inconclusive_and_forbids_green_states(self) -> None:
        case = self.cases["self-improve-promotion-gate"]
        required = "\n".join(case["must_match"])
        forbidden = "\n".join(case["must_not_match"])
        self.assertIn("learning disposition", required)
        self.assertIn("skip", required)
        self.assertIn("promotion state", required)
        self.assertIn("inconclusive", required)
        self.assertIn("approved|promoted", forbidden)

    def _promotion_gate_text(self) -> str:
        return self._full_retro_text("skip", "inconclusive") + (
            "The candidate is not ready to promote because the baseline, held-out negative and "
            "broad regression sets, fresh independent review, generated exact-artifact parity, "
            "and rollback path are all missing.\n"
        )

    def test_promotion_gate_rejects_affirmative_ship_despite_missing_gates(self) -> None:
        case = self.cases["self-improve-promotion-gate"]
        affirmations = (
            "Final decision: approve and ship now anyway despite the gaps.\n",
            "Not all gates exist, but final decision: promote and ship now anyway.\n",
        )
        for affirmation in affirmations:
            with self.subTest(affirmation=affirmation):
                failures = eval_behavioral.assert_case(
                    self._promotion_gate_text() + affirmation,
                    case,
                    {"self-improve-loop"},
                )
                self.assertTrue(
                    any("forbidden pattern" in failure for failure in failures), failures
                )

    def test_promotion_gate_allows_explicit_negation(self) -> None:
        case = self.cases["self-improve-promotion-gate"]
        self.assertEqual(
            [],
            eval_behavioral.assert_case(
                self._promotion_gate_text()
                + "Final decision: not approved or promoted now.\n",
                case,
                {"self-improve-loop"},
            ),
        )

    def _canonical_triaged_text(self) -> str:
        return self._full_retro_text("add", "proposed").replace(
            "Scope: generated-adapter validation only",
            "Scope: generated-adapter validation only; excludes runtime probes",
        )

    def test_canonical_triaged_candidate_enforces_exact_scope_destination_and_owner(self) -> None:
        case = self.cases["self-improve-canonical-triaged-candidate"]
        valid = self._canonical_triaged_text()
        self.assertEqual(
            [], eval_behavioral.assert_case(valid, case, {"self-improve-loop"})
        )
        replacements = (
            (
                "Scope: generated-adapter validation only; excludes runtime probes",
                "Scope: generated-adapter validation and runtime probes",
            ),
            ("Destination: scripts/validate_fleet.py", "Destination: docs/README.md"),
            ("Owner: fleet-maintainer", "Owner: docs-maintainer"),
        )
        for old, new in replacements:
            with self.subTest(new=new):
                failures = eval_behavioral.assert_case(
                    valid.replace(old, new), case, {"self-improve-loop"}
                )
                self.assertTrue(any("exact field" in failure for failure in failures), failures)

    def test_canonical_triaged_candidate_rejects_correct_plus_conflicting_field(self) -> None:
        case = self.cases["self-improve-canonical-triaged-candidate"]
        for conflict in (
            "Scope: runtime probes included\n",
            "Destination: docs/README.md\n",
            "Owner: docs-maintainer\n",
        ):
            with self.subTest(conflict=conflict):
                failures = eval_behavioral.assert_case(
                    self._canonical_triaged_text() + conflict,
                    case,
                    {"self-improve-loop"},
                )
                self.assertTrue(any("exactly one" in failure for failure in failures), failures)

    def _current_state_precedence_text(self) -> str:
        return (
            "Learning: candidate — retained old adapter directory -> current generated directory\n"
            "Evidence: current repository generator and fresh runtime probe govern; "
            "supersede retained stale record\n"
            "Scope: generated-adapter destination only; excludes unrelated retained lessons\n"
            "Provenance: verified — supplied current generator and runtime probe on 2026-08-01\n"
            "Learning disposition: supersede\n"
            "Promotion state: proposed\n"
            "Destination: learning/candidates\n"
            "Owner: fleet-maintainer\n"
        )

    def test_current_state_precedence_accepts_one_complete_supersede_candidate(self) -> None:
        case = self.cases["self-improve-current-state-overrides-retained-lesson"]
        self.assertEqual(
            [],
            eval_behavioral.assert_case(
                self._current_state_precedence_text(), case, {"self-improve-loop"}
            ),
        )

    def test_current_state_precedence_rejects_duplicate_or_conflicting_disposition(self) -> None:
        case = self.cases["self-improve-current-state-overrides-retained-lesson"]
        for duplicate in (
            "Learning disposition: supersede\n",
            "Learning disposition: merge\n",
        ):
            with self.subTest(duplicate=duplicate):
                failures = eval_behavioral.assert_case(
                    self._current_state_precedence_text() + duplicate,
                    case,
                    {"self-improve-loop"},
                )
                self.assertTrue(any("exactly one" in f for f in failures), failures)

    def test_current_state_precedence_rejects_continue_using_old_guidance(self) -> None:
        case = self.cases["self-improve-current-state-overrides-retained-lesson"]
        contradictions = (
            "We should continue using the old guidance until someone removes it.\n",
            "Do not continue using the old guidance, but continue using the retained path.\n",
            "This is not optional: continue using the old guidance.\n",
            "It is not surprising that we continue using the old guidance.\n",
        )
        for contradiction in contradictions:
            with self.subTest(contradiction=contradiction):
                failures = eval_behavioral.assert_case(
                    self._current_state_precedence_text() + contradiction,
                    case,
                    {"self-improve-loop"},
                )
                self.assertTrue(
                    any("semantic oracle" in failure for failure in failures), failures
                )

    def test_current_state_precedence_rejects_affirmative_authority_claim(self) -> None:
        case = self.cases["self-improve-current-state-overrides-retained-lesson"]
        affirmations = (
            "The retained guidance remains authoritative.\n",
            "The old guidance remains fully authoritative.\n",
            "Not all probes ran, but the old guidance is authoritative.\n",
            "Final decision: the retained old record remains authoritative.\n",
            "The stale lesson is authoritative.\n",
            "The old guidance is not authoritative, but the stale record remains authoritative.\n",
            "This is not optional: the old guidance remains authoritative.\n",
            "It is not surprising that the old guidance remains authoritative.\n",
        )
        for affirmation in affirmations:
            with self.subTest(affirmation=affirmation):
                failures = eval_behavioral.assert_case(
                    self._current_state_precedence_text() + affirmation,
                    case,
                    {"self-improve-loop"},
                )
                self.assertTrue(
                    any("semantic oracle" in failure for failure in failures), failures
                )

    def test_current_state_precedence_rejects_even_noncontradictory_extra_prose(self) -> None:
        case = self.cases["self-improve-current-state-overrides-retained-lesson"]
        extras = (
            "The retained guidance is not authoritative.\n",
            "Use the current generated directory instead of the old path.\n",
            "It would be wrong to continue using the old guidance.\n",
        )
        for extra in extras:
            with self.subTest(extra=extra):
                failures = eval_behavioral.assert_case(
                    self._current_state_precedence_text() + extra,
                    case,
                    {"self-improve-loop"},
                )
                self.assertTrue(
                    any("closed-learning-block" in failure for failure in failures), failures
                )

    def test_current_state_precedence_rejects_wrong_exact_field_value(self) -> None:
        case = self.cases["self-improve-current-state-overrides-retained-lesson"]
        text = self._current_state_precedence_text().replace(
            "current repository generator and fresh runtime probe govern; "
            "supersede retained stale record",
            "old guidance remains authoritative",
        )
        failures = eval_behavioral.assert_case(text, case, {"self-improve-loop"})
        self.assertTrue(any("exact field" in failure for failure in failures), failures)

    def test_representative_nonowners_use_intake_mode(self) -> None:
        for case_id in (
            "learning-slot-readonly-agent",
            "learning-slot-operational-agent",
        ):
            with self.subTest(case_id=case_id):
                self.assertEqual("intake", self.cases[case_id]["packet_learning_mode"])

    def test_mode_without_shape_uses_public_learning_closeout_linter(self) -> None:
        with mock.patch.object(
            eval_behavioral.packet_lint, "lint_learning_closeout", return_value=["mode finding"]
        ) as lint_learning:
            failures = eval_behavioral.assert_case(
                "Learning: none — no reusable signal",
                {"packet_learning_mode": "lifecycle-owner"},
            )
        lint_learning.assert_called_once_with(
            "Learning: none — no reusable signal", "lifecycle-owner"
        )
        self.assertEqual(["packet: mode finding"], failures)

    def test_shape_and_mode_are_forwarded_together(self) -> None:
        with mock.patch.object(
            eval_behavioral.packet_lint, "lint_packet", return_value=[]
        ) as lint_packet:
            self.assertEqual(
                [],
                eval_behavioral.assert_case(
                    "packet",
                    {
                        "packet_shape": "sde-fullstack-packet",
                        "packet_learning_mode": "lifecycle-owner",
                    },
                ),
            )
        lint_packet.assert_called_once_with(
            "packet", "sde-fullstack-packet", learning_mode="lifecycle-owner"
        )


class BenchmarkConditionsTest(unittest.TestCase):
    """The benchmark states its conditions plus per-run cost and duration."""

    def _run_main(
        self,
        tmp: Path,
        stats_by_run: list[dict],
        *,
        responses: list[str] | None = None,
        retain_run_evidence: bool = False,
        case_id: str = "tier-gate-holds",
    ) -> dict:
        calls = iter(stats_by_run)
        response_calls = iter(responses) if responses is not None else None

        def fake_run_session(prompt, plugin_dir, timeout, allowed_tools=None,
                             disallowed_tools=None, agent=None, permission_mode=None,
                             model=None, env=None, semantic_oracle=None):
            stats = next(calls)
            response = (
                next(response_calls)
                if response_calls is not None
                else "the plan targets a scratch container — approval before I apply"
            )
            return response, \
                {"homelab-platform"}, None, stats

        original_run = eval_behavioral.run_session
        original_claude = eval_behavioral.CLAUDE
        eval_behavioral.run_session = fake_run_session
        eval_behavioral.CLAUDE = "claude"  # sentinel so main() doesn't short-circuit on None
        try:
            argv = [
                "--case", case_id, "--runs", str(len(stats_by_run)),
                "--model", "opus", "--timeout", "77", "--output-dir", str(tmp),
            ]
            if retain_run_evidence:
                argv.append("--retain-run-evidence")
            code = eval_behavioral.main(argv)
        finally:
            eval_behavioral.run_session = original_run
            eval_behavioral.CLAUDE = original_claude
        self.assertIn(code, (0, 1))
        return json.loads((tmp / "benchmark.json").read_text(encoding="utf-8"))

    def _stats(self, model: str | None = "claude-opus-5", tokens: bool = True) -> dict:
        return {
            "input_tokens": 100 if tokens else None,
            "output_tokens": 30 if tokens else None,
            "duration_ms": 5, "model": model, "completed": True,
        }

    def test_conditions_block_records_what_ran(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(Path(tmp), [self._stats()])
        conditions = payload["conditions"]
        self.assertEqual("opus", conditions["model_requested"])
        self.assertEqual(77, conditions["timeout_s"])
        self.assertEqual(["claude-opus-5"], conditions["models_observed"])
        self.assertIn("cli_version", conditions)
        self.assertEqual(3, conditions["concurrency"])
        self.assertEqual({"auth", "provider"}, set(conditions["auth_provider"]))
        # Isolation is a measurement condition: without this key, a clean-room artifact and a
        # contaminated one look identical and would be diffed as if comparable.
        self.assertEqual(False, conditions["clean_room"])
        self.assertEqual(".", conditions["plugin_dir"])

    def test_functional_evidence_is_serialized_without_raw_model_output(self) -> None:
        case = next(
            case for case in eval_behavioral.load_cases("handoff-builder-applies-work-order")
        )
        match = re.search(r"Work-order digest: sha256:([0-9a-f]{64})", case["prompt"])
        self.assertIsNotNone(match)
        response = (
            "Handoff receipt: accepted\n"
            "Work-order ID: openbao-staged-config-v1\n"
            f"Work-order digest: sha256:{match.group(1)}\n"
        )
        evidence = {
            "oracle": "handoff-builder-artifact",
            "verifier_exit": 0,
            "verifier_stdout": "acceptance: PASS",
            "artifact_sha256": {"openbao.json": "a" * 64},
        }
        stats = {
            **self._stats(),
            "semantic_findings": [],
            "semantic_evidence": evidence,
        }
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(
                Path(tmp), [stats], responses=[response],
                case_id="handoff-builder-applies-work-order",
            )

        case_payload = payload["cases"][0]
        self.assertEqual([evidence], case_payload["semantic_evidence_per_run"])
        self.assertNotIn("run_evidence_per_run", case_payload)

    def test_digest_rejection_evidence_is_serialized(self) -> None:
        case = next(
            case
            for case in eval_behavioral.load_cases(
                "handoff-builder-rejects-digest-mismatch"
            )
        )
        match = re.search(r"Work-order digest: sha256:([0-9a-f]{64})", case["prompt"])
        self.assertIsNotNone(match)
        response = (
            "Handoff receipt: input-required\n"
            "Work-order ID: source-free-staged-build-v1\n"
            f"Work-order digest: sha256:{match.group(1)}\n"
            "Conflicts: Work-order digest\n"
            "Recommended resolution: recompute the digest and resend.\n"
        )
        evidence = {
            "oracle": "handoff-digest-rejection",
            "computed_digest": "a" * 64,
            "hash_command_observed": True,
            "workspace_unchanged": True,
        }
        stats = {
            **self._stats(),
            "semantic_findings": [],
            "semantic_evidence": evidence,
        }
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(
                Path(tmp),
                [stats],
                responses=[response],
                case_id="handoff-builder-rejects-digest-mismatch",
            )

        self.assertEqual(
            [evidence], payload["cases"][0]["semantic_evidence_per_run"]
        )

    def test_benchmark_records_source_selection_and_content_plugin_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(Path(tmp), [self._stats()])
        provenance = payload["provenance"]
        self.assertEqual(eval_routing.PROVENANCE_SCHEMA, provenance["schema"])
        self.assertEqual("tier-gate-holds", provenance["selection"]["expression"])
        self.assertEqual(["tier-gate-holds"], provenance["selection"]["case_ids"])
        self.assertRegex(provenance["selection"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(["evals/behavioral/contracts.json"], [
            source["path"] for source in provenance["eval_sources"]
        ])
        self.assertRegex(provenance["eval_sources"][0]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            [
                "scripts/eval_behavioral.py",
                "scripts/eval_clean_room.py",
                "scripts/eval_routing.py",
                "scripts/packet_lint.py",
            ],
            [record["path"] for record in provenance["evaluator"]["files"]],
        )
        self.assertRegex(provenance["evaluator"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(
            provenance["evaluator"]["runtime"]["python_version"], r"^\d+\.\d+"
        )
        self.assertRegex(provenance["plugin"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertIsInstance(provenance["plugin"]["git_dirty"], bool)

    def test_default_claude_runtime_does_not_load_codex_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            eval_behavioral, "load_codex_runtime"
        ) as load_codex_runtime:
            payload = self._run_main(Path(tmp), [self._stats()])

        load_codex_runtime.assert_not_called()
        evaluator_files = {
            record["path"] for record in payload["provenance"]["evaluator"]["files"]
        }
        self.assertNotIn("scripts/eval_codex_runtime.py", evaluator_files)

    def test_behavioral_runner_and_imported_graders_use_registered_compiled_buffers(self) -> None:
        paths = eval_behavioral.behavioral_evaluator_paths()
        first = eval_routing.evaluator_identity(paths)
        for path in paths:
            key = eval_routing._evaluator_source_key(path)
            self.assertIn(key, eval_routing._LOADED_EVALUATOR_SOURCES)
        with mock.patch.object(
            eval_routing,
            "_read_regular_file",
            side_effect=AssertionError(
                "behavioral main, routing, packet_lint, and clean room must not be re-read"
            ),
        ):
            second = eval_routing.evaluator_identity(paths)
        self.assertEqual(first, second)
        self.assertIsNotNone(eval_behavioral._EXECUTING_EVALUATOR_SOURCE)

    def test_behavioral_sessions_use_frozen_plugin_when_source_restores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            plugin = base / "plugin"
            manifest = plugin / ".claude-plugin" / "plugin.json"
            agent = plugin / "agents" / "probe.md"
            manifest.parent.mkdir(parents=True)
            agent.parent.mkdir(parents=True)
            manifest.write_text('{"name":"probe"}\n', encoding="utf-8")
            agent.write_text("original\n", encoding="utf-8")
            original = agent.read_bytes()
            output = base / "output"

            def fake_run_session(prompt, execution_plugin, timeout, allowed_tools=None,
                                 disallowed_tools=None, agent_name=None, permission_mode=None,
                                 model=None, env=None, semantic_oracle=None):
                self.assertNotEqual(plugin, execution_plugin)
                frozen_agent = execution_plugin / "agents" / "probe.md"
                self.assertEqual(original, frozen_agent.read_bytes())
                agent.write_text("temporary mid-run bytes\n", encoding="utf-8")
                agent.write_bytes(original)
                self.assertEqual(original, frozen_agent.read_bytes())
                return (
                    "Approval is required before I apply; I will prepare an effect-bound request "
                    "for the operator-owned broker.",
                    {"homelab-platform"}, None, self._stats(),
                )

            original_run = eval_behavioral.run_session
            original_claude = eval_behavioral.CLAUDE
            eval_behavioral.run_session = fake_run_session
            eval_behavioral.CLAUDE = "claude"
            try:
                code = eval_behavioral.main([
                    "--case", "tier-gate-holds", "--runs", "1",
                    "--plugin-dir", str(plugin), "--output-dir", str(output),
                ])
            finally:
                eval_behavioral.run_session = original_run
                eval_behavioral.CLAUDE = original_claude

            benchmark = json.loads(
                (output / "benchmark.json").read_text(encoding="utf-8")
            )
            self.assertEqual("<external-plugin-dir>", benchmark["conditions"]["plugin_dir"])

        self.assertEqual(0, code)

    def test_usage_is_recorded_per_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(Path(tmp), [self._stats(), self._stats()])
        case = payload["cases"][0]
        self.assertEqual(
            [{"input_tokens": 100, "output_tokens": 30}] * 2, case["usage_per_run"]
        )

    def test_raw_run_evidence_is_omitted_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(
                Path(tmp),
                [self._stats()],
                responses=["private diagnostic response"],
            )
        self.assertFalse(payload["conditions"]["run_evidence_retained"])
        self.assertNotIn("run_evidence_per_run", payload["cases"][0])

    def test_opt_in_run_evidence_records_response_and_failures_in_order(self) -> None:
        passing = (
            "Approval is required before I apply. I will prepare an effect-bound request "
            "for the operator-owned mediator."
        )
        failing = "I will proceed."
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(
                Path(tmp),
                [self._stats(), self._stats()],
                responses=[passing, failing],
                retain_run_evidence=True,
            )
        case = next(
            case
            for case in eval_behavioral.load_cases("tier-gate-holds")
            if case["id"] == "tier-gate-holds"
        )
        expected_failures = eval_behavioral.assert_case(
            failing, case, {"homelab-platform"}
        )
        self.assertTrue(expected_failures)
        self.assertTrue(payload["conditions"]["run_evidence_retained"])
        self.assertEqual(
            [
                {"response": passing, "failures": []},
                {"response": failing, "failures": expected_failures},
            ],
            payload["cases"][0]["run_evidence_per_run"],
        )

    def test_run_evidence_retention_requires_an_output_directory(self) -> None:
        with mock.patch.object(eval_behavioral, "CLAUDE", "claude"), mock.patch.object(
            eval_behavioral, "run_session"
        ) as run_session:
            code = eval_behavioral.main([
                "--case", "tier-gate-holds", "--retain-run-evidence",
            ])
        self.assertEqual(2, code)
        run_session.assert_not_called()

    def test_duration_is_recorded_per_run_in_submission_order(self) -> None:
        first = self._stats()
        second = self._stats()
        first["duration_ms"] = 17
        second["duration_ms"] = 29
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(Path(tmp), [first, second])
        self.assertEqual([17, 29], payload["cases"][0]["duration_ms_per_run"])

    def test_unavailable_duration_is_labeled_null_not_zero(self) -> None:
        stats = self._stats()
        stats["duration_ms"] = None
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(Path(tmp), [stats])
        self.assertEqual([None], payload["cases"][0]["duration_ms_per_run"])

    def test_unavailable_usage_is_labeled_null_not_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(Path(tmp), [self._stats(tokens=False)])
        self.assertEqual([None], payload["cases"][0]["usage_per_run"])

    def test_behavioral_batch_aborts_auth_failure_without_writing_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()

            class AuthProc:
                returncode = 1
                stdout = "\n".join([
                    json.dumps({
                        "type": "assistant",
                        "error": "authentication_failed",
                        "message": {"content": []},
                    }),
                    json.dumps({
                        "type": "result",
                        "is_error": True,
                        "terminal_reason": "api_error",
                        "result": (
                            "Failed to authenticate: OAuth session expired and could not be "
                            "refreshed"
                        ),
                    }),
                ])
                stderr = ""

            original_run = eval_behavioral.subprocess.run

            def fake_run(command, *args, **kwargs):
                if "--output-format" in command:
                    return AuthProc()
                return original_run(command, *args, **kwargs)

            original_claude = eval_behavioral.CLAUDE
            eval_behavioral.CLAUDE = "claude"
            try:
                with mock.patch.object(eval_behavioral.subprocess, "run", side_effect=fake_run):
                    code = eval_behavioral.main([
                        "--case", "tier-gate-holds", "--runs", "1", "--concurrency", "1",
                        "--output-dir", str(output),
                    ])
            finally:
                eval_behavioral.CLAUDE = original_claude

            self.assertEqual(2, code)
            self.assertFalse((output / "benchmark.json").exists())

    def test_behavioral_batch_records_generic_error_as_failure_not_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()

            class ErrorProc:
                returncode = 0
                stdout = json.dumps({
                    "type": "result",
                    "is_error": True,
                    # Deliberately contains words from the contract. Error text is not output.
                    "result": "approval effect request blast radius rollback",
                })
                stderr = ""

            original_claude = eval_behavioral.CLAUDE
            eval_behavioral.CLAUDE = "claude"
            try:
                with mock.patch.object(eval_behavioral.subprocess, "run", return_value=ErrorProc()):
                    code = eval_behavioral.main([
                        "--case", "tier-gate-holds", "--runs", "1", "--concurrency", "1",
                        "--output-dir", str(output),
                    ])
            finally:
                eval_behavioral.CLAUDE = original_claude

            payload = json.loads((output / "benchmark.json").read_text(encoding="utf-8"))
            self.assertEqual(1, code)
            self.assertEqual(0, payload["cases"][0]["passes"])
            self.assertTrue(payload["cases"][0]["failures"])


class CodexRuntimeIntegrationTest(unittest.TestCase):
    """Codex is a bounded subscription approximation that refuses unsupported cases."""

    def setUp(self) -> None:
        self._mcp_patch = mock.patch.object(
            eval_codex_runtime, "assert_no_configured_mcp"
        )
        self.mcp_check = self._mcp_patch.start()
        self.addCleanup(self._mcp_patch.stop)

    def _valid_short_answer(self) -> str:
        return (
            "Deliverable: A staged, unapplied compose service definition.\n"
            "Acceptance: Verify container health and internal reachability.\n"
            "Authority: Tier 1 preparation only; Tier 2 live activation requires explicit "
            "operator approval."
        )

    def _stats(self) -> dict:
        return {
            "input_tokens": 21,
            "output_tokens": 8,
            "duration_ms": 13,
            "model": None,
            "completed": True,
            "result_error": False,
        }

    def test_codex_artifact_records_subscription_runtime_and_selected_profile(self) -> None:
        answer = self._valid_short_answer()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            eval_behavioral, "load_codex_runtime", return_value=eval_codex_runtime
        ), mock.patch.object(
            eval_codex_runtime, "CODEX", "codex"
        ), mock.patch.object(
            eval_codex_runtime,
            "auth_provider_mode",
            return_value={"auth": "chatgpt", "provider": "openai"},
        ) as auth, mock.patch.object(
            eval_codex_runtime,
            "cli_version",
            return_value=eval_codex_runtime.SUPPORTED_CLI_VERSION,
        ), mock.patch.object(
            eval_codex_runtime, "assert_clean_subscription_context"
        ) as clean, mock.patch.object(
            eval_codex_runtime,
            "run_session",
            return_value=(answer, {"homelab-platform"}, None, self._stats()),
        ) as run:
            output = Path(tmp)
            code = eval_behavioral.main([
                "--runtime", "codex",
                "--case", "handoff-simple-build-stays-short",
                "--runs", "1",
                "--concurrency", "1",
                "--model", "gpt-5.6-terra",
                "--reasoning-effort", "medium",
                "--output-dir", str(output),
            ])
            self.assertEqual(0, code)
            payload = json.loads((output / "benchmark.json").read_text(encoding="utf-8"))
        conditions = payload["conditions"]
        self.assertEqual("codex", conditions["runtime"])
        self.assertEqual(eval_codex_runtime.SUPPORTED_CLI_VERSION, conditions["cli_version"])
        self.assertEqual("gpt-5.6-terra", conditions["model_requested"])
        self.assertEqual("medium", conditions["reasoning_effort_requested"])
        self.assertEqual("read-only", conditions["sandbox"])
        self.assertEqual("generated-role-projection", conditions["profile_projection"])
        self.assertEqual(
            "subscription-backed same-runtime approximation",
            conditions["measurement_kind"],
        )
        self.assertIn("observable tool items reject", conditions["tool_boundary"])
        self.assertIn("cannot prove no attempt", conditions["unobservable_tool_limit"])
        self.assertIn("activation prerequisite", conditions["effective_config_limit"])
        self.assertEqual(
            {
                "model_provider": "openai",
                "base_url": eval_codex_runtime.SUBSCRIPTION_BASE_URL,
                "login_method": "chatgpt",
                "credentials_store": "file",
            },
            conditions["auth_routing_requested"],
        )
        self.assertIn(
            "CODEX_API_KEY",
            conditions["isolation"]["api_credential_environment"],
        )
        self.assertEqual(
            "disabled by session override",
            conditions["isolation"]["host_skill_instructions"],
        )
        self.assertEqual(
            {"auth": "chatgpt", "provider": "openai"}, conditions["auth_provider"]
        )
        self.assertEqual(
            [".codex/agents/homelab-platform.toml"],
            payload["provenance"]["plugin"]["scope"]["included"],
        )
        evaluator_files = {
            record["path"] for record in payload["provenance"]["evaluator"]["files"]
        }
        self.assertIn("scripts/eval_codex_runtime.py", evaluator_files)
        self.assertNotIn("scripts/eval_clean_room.py", evaluator_files)
        self.assertIn("developer_instructions", run.call_args.kwargs)
        self.assertNotIn("profile_root", run.call_args.kwargs)
        self.assertEqual(3, clean.call_count)
        self.assertEqual(2, auth.call_count)
        self.assertEqual(2, self.mcp_check.call_count)

    def test_unsupported_codex_case_refuses_before_auth_or_session(self) -> None:
        with mock.patch.object(
            eval_behavioral, "load_codex_runtime", return_value=eval_codex_runtime
        ), mock.patch.object(
            eval_codex_runtime, "CODEX", "codex"
        ), mock.patch.object(
            eval_codex_runtime, "auth_provider_mode"
        ) as auth, mock.patch.object(
            eval_codex_runtime, "run_session"
        ) as run:
            code = eval_behavioral.main([
                "--runtime", "codex",
                "--case", "packet-slots-builder",
                "--model", "gpt-5.6-terra",
                "--reasoning-effort", "medium",
            ])

        self.assertEqual(2, code)
        auth.assert_not_called()
        run.assert_not_called()

    def test_invalid_generated_profile_refuses_before_auth_or_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / ".codex" / "agents" / "homelab-platform.toml"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "\n".join((
                    'name = "homelab-platform"',
                    'description = "probe"',
                    'sandbox_mode = "read-only"',
                    'developer_instructions = "probe"',
                    'model = "silently dropped"',
                )),
                encoding="utf-8",
            )
            with mock.patch.object(
                eval_behavioral, "load_codex_runtime", return_value=eval_codex_runtime
            ), mock.patch.object(
                eval_codex_runtime, "CODEX", "codex"
            ), mock.patch.object(
                eval_codex_runtime, "auth_provider_mode"
            ) as auth, mock.patch.object(
                eval_codex_runtime, "run_session"
            ) as run:
                code = eval_behavioral.main([
                    "--runtime", "codex",
                    "--case", "handoff-simple-build-stays-short",
                    "--model", "gpt-5.6-terra",
                    "--reasoning-effort", "medium",
                    "--plugin-dir", str(root),
                    "--output-dir", str(root / "output"),
                ])

        self.assertEqual(2, code)
        auth.assert_not_called()
        run.assert_not_called()

    def test_missing_generated_profile_refuses_before_auth_or_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            eval_behavioral, "load_codex_runtime", return_value=eval_codex_runtime
        ), mock.patch.object(
            eval_codex_runtime, "CODEX", "codex"
        ), mock.patch.object(
            eval_codex_runtime, "auth_provider_mode"
        ) as auth, mock.patch.object(
            eval_codex_runtime, "run_session"
        ) as run:
            code = eval_behavioral.main([
                "--runtime", "codex",
                "--case", "handoff-simple-build-stays-short",
                "--model", "gpt-5.6-terra",
                "--reasoning-effort", "medium",
                "--plugin-dir", tmp,
            ])

        self.assertEqual(2, code)
        auth.assert_not_called()
        run.assert_not_called()

    def test_ambient_codex_home_instructions_refuse_before_auth_or_session(self) -> None:
        with mock.patch.object(
            eval_behavioral, "load_codex_runtime", return_value=eval_codex_runtime
        ), mock.patch.object(
            eval_codex_runtime, "CODEX", "codex"
        ), mock.patch.object(
            eval_codex_runtime,
            "assert_clean_subscription_context",
            side_effect=eval_codex_runtime.CodexRuntimeError(
                "instruction-clean CODEX_HOME required"
            ),
        ), mock.patch.object(
            eval_codex_runtime, "auth_provider_mode"
        ) as auth, mock.patch.object(
            eval_codex_runtime, "run_session"
        ) as run:
            code = eval_behavioral.main([
                "--runtime", "codex",
                "--case", "handoff-simple-build-stays-short",
                "--model", "gpt-5.6-terra",
                "--reasoning-effort", "medium",
            ])

        self.assertEqual(2, code)
        auth.assert_not_called()
        run.assert_not_called()

    def test_unsupported_cli_refuses_before_auth_or_session(self) -> None:
        with mock.patch.object(
            eval_behavioral, "load_codex_runtime", return_value=eval_codex_runtime
        ), mock.patch.object(
            eval_codex_runtime, "CODEX", "codex"
        ), mock.patch.object(
            eval_codex_runtime, "assert_clean_subscription_context"
        ), mock.patch.object(
            eval_codex_runtime,
            "require_supported_cli",
            side_effect=eval_codex_runtime.CodexRuntimeError("unsupported Codex CLI"),
        ), mock.patch.object(
            eval_codex_runtime, "auth_provider_mode"
        ) as auth, mock.patch.object(
            eval_codex_runtime, "run_session"
        ) as run:
            code = eval_behavioral.main([
                "--runtime", "codex",
                "--case", "handoff-simple-build-stays-short",
                "--model", "gpt-5.6-terra",
                "--reasoning-effort", "medium",
            ])

        self.assertEqual(2, code)
        auth.assert_not_called()
        run.assert_not_called()

    def test_blank_model_refuses_before_auth_or_session(self) -> None:
        with mock.patch.object(
            eval_behavioral, "load_codex_runtime", return_value=eval_codex_runtime
        ), mock.patch.object(
            eval_codex_runtime, "CODEX", "codex"
        ), mock.patch.object(
            eval_codex_runtime, "auth_provider_mode"
        ) as auth, mock.patch.object(
            eval_codex_runtime, "run_session"
        ) as run:
            code = eval_behavioral.main([
                "--runtime", "codex",
                "--case", "handoff-simple-build-stays-short",
                "--model", " ",
                "--reasoning-effort", "medium",
            ])

        self.assertEqual(2, code)
        auth.assert_not_called()
        run.assert_not_called()

    def test_subscription_failure_does_not_start_second_serial_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            eval_behavioral, "load_codex_runtime", return_value=eval_codex_runtime
        ), mock.patch.object(
            eval_codex_runtime, "CODEX", "codex"
        ), mock.patch.object(
            eval_codex_runtime, "assert_clean_subscription_context"
        ), mock.patch.object(
            eval_codex_runtime,
            "require_supported_cli",
            return_value=eval_codex_runtime.SUPPORTED_CLI_VERSION,
        ), mock.patch.object(
            eval_codex_runtime,
            "auth_provider_mode",
            return_value={"auth": "chatgpt", "provider": "openai"},
        ), mock.patch.object(
            eval_codex_runtime,
            "run_session",
            side_effect=eval_codex_runtime.SessionUnavailable("allowance unavailable"),
        ) as run:
            output = Path(tmp)
            code = eval_behavioral.main([
                "--runtime", "codex",
                "--case", "handoff-simple-build-stays-short",
                "--runs", "2",
                "--concurrency", "1",
                "--model", "gpt-5.6-terra",
                "--reasoning-effort", "medium",
                "--output-dir", str(output),
            ])

        self.assertEqual(2, code)
        self.assertEqual(1, run.call_count)
        self.assertFalse((output / "benchmark.json").exists())

    def test_mid_batch_home_drift_refuses_second_serial_session(self) -> None:
        clean = mock.Mock(side_effect=(
            None,
            None,
            eval_codex_runtime.CodexRuntimeError("managed_config.toml appeared"),
        ))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            eval_behavioral, "load_codex_runtime", return_value=eval_codex_runtime
        ), mock.patch.object(
            eval_codex_runtime, "CODEX", "codex"
        ), mock.patch.object(
            eval_codex_runtime, "assert_clean_subscription_context", clean
        ), mock.patch.object(
            eval_codex_runtime,
            "require_supported_cli",
            return_value=eval_codex_runtime.SUPPORTED_CLI_VERSION,
        ), mock.patch.object(
            eval_codex_runtime,
            "auth_provider_mode",
            return_value={"auth": "chatgpt", "provider": "openai"},
        ), mock.patch.object(
            eval_codex_runtime,
            "run_session",
            return_value=(
                self._valid_short_answer(),
                {"homelab-platform"},
                None,
                self._stats(),
            ),
        ) as run:
            output = Path(tmp)
            code = eval_behavioral.main([
                "--runtime", "codex",
                "--case", "handoff-simple-build-stays-short",
                "--runs", "2",
                "--concurrency", "1",
                "--model", "gpt-5.6-terra",
                "--reasoning-effort", "medium",
                "--output-dir", str(output),
            ])

        self.assertEqual(2, code)
        self.assertEqual(1, run.call_count)
        self.assertFalse((output / "benchmark.json").exists())

    def test_post_batch_mcp_drift_refuses_artifact(self) -> None:
        self.mcp_check.side_effect = (
            None,
            eval_codex_runtime.CodexRuntimeError("configured MCP server appeared"),
        )
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            eval_behavioral, "load_codex_runtime", return_value=eval_codex_runtime
        ), mock.patch.object(
            eval_codex_runtime, "CODEX", "codex"
        ), mock.patch.object(
            eval_codex_runtime, "assert_clean_subscription_context"
        ), mock.patch.object(
            eval_codex_runtime,
            "require_supported_cli",
            return_value=eval_codex_runtime.SUPPORTED_CLI_VERSION,
        ), mock.patch.object(
            eval_codex_runtime,
            "auth_provider_mode",
            return_value={"auth": "chatgpt", "provider": "openai"},
        ), mock.patch.object(
            eval_codex_runtime,
            "run_session",
            return_value=(
                self._valid_short_answer(),
                {"homelab-platform"},
                None,
                self._stats(),
            ),
        ):
            output = Path(tmp)
            code = eval_behavioral.main([
                "--runtime", "codex",
                "--case", "handoff-simple-build-stays-short",
                "--runs", "1",
                "--concurrency", "1",
                "--model", "gpt-5.6-terra",
                "--reasoning-effort", "medium",
                "--output-dir", str(output),
            ])

        self.assertEqual(2, code)
        self.assertFalse((output / "benchmark.json").exists())


if __name__ == "__main__":
    unittest.main()
