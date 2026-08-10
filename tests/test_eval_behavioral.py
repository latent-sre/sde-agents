"""Offline tests for scripts/eval_behavioral.py — conditions, usage, and the scratch cwd.

EVAL-002's failure class: an artifact that cannot state what it measured. The live run on
2026-07-29 proved it twice — behavioral sessions ran on an unpinned, unrecorded model, and the
`%TEMP%` scratch cwd silently blocked the writes one case's premise depends on. These tests pin
the repairs: the shared transcript read reports usage or its absence honestly, the benchmark
records its conditions, and the scratch cwd stays out of the directory tree the CLI sandbox
write-blocks.
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import eval_behavioral as _eval_behavioral_bootstrap

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

    def test_shipped_document_satisfies_public_schema(self) -> None:
        self.assertEqual([], eval_behavioral.validate_case_document(self.document))

    def test_all_shipped_cases_pin_the_minimum_positive_tool_boundary(self) -> None:
        scratch_cases = {
            "packet-slots-builder",
            "ladder-report-not-absorb",
            "verifier-fails-honestly-no-product-edit",
        }
        self.assertEqual(52, len(self.document["cases"]))
        for case in self.document["cases"]:
            with self.subTest(case=case["id"]):
                if case["id"] in scratch_cases:
                    self.assertEqual(["Bash", "Write"], case["allowed_tools"])
                elif "agent" in case:
                    self.assertEqual([], case["allowed_tools"])
                else:
                    self.assertEqual(["Skill"], case["allowed_tools"])

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


class MarkdownDecisionLabelTest(unittest.TestCase):
    """Behavioral oracles accept the packet's rendered Markdown, not only plain-text labels."""

    @classmethod
    def setUpClass(cls) -> None:
        document = json.loads(
            (REPO / "evals" / "behavioral" / "contracts.json").read_text(encoding="utf-8")
        )
        cls.cases = {case["id"]: case for case in document["cases"]}

    def test_exact_disposition_accepts_plain_and_bold_markdown(self) -> None:
        exact = {"Learning disposition": "merge"}
        for text in (
            "Learning disposition: merge",
            "**Learning disposition**: merge",
            "**Learning disposition:** merge",
            "- **Learning disposition:** merge",
        ):
            with self.subTest(text=text):
                self.assertEqual([], eval_behavioral.packet_lint.lint_exact_fields(text, exact))

    def test_exact_disposition_rejects_wrong_or_conflicting_values(self) -> None:
        for text in (
            "Learning disposition: skip",
            "**Learning disposition:** skip",
            "Learning disposition: merge\n- **Learning disposition**: add",
        ):
            with self.subTest(text=text):
                findings = eval_behavioral.packet_lint.lint_exact_fields(
                    text, {"Learning disposition": "merge"}
                )
                self.assertTrue(findings)

    def test_promotion_state_and_learning_accept_bold_colons(self) -> None:
        self.assertEqual(
            [],
            eval_behavioral.packet_lint.lint_exact_fields(
                "**Promotion state:** inconclusive",
                {"Promotion state": "inconclusive"},
            ),
        )
        learning = next(
            pattern for pattern in self.cases["learning-slot-readonly-agent"]["must_match"]
            if "learning" in pattern.lower()
        )
        self.assertRegex(
            "**Learning:** candidate — parity was omitted -> parity is asserted",
            re.compile(learning),
        )

    def test_runbook_disposition_has_its_own_namespace(self) -> None:
        for text in (
            "Runbook disposition: update",
            "**Runbook disposition:** update",
            "- **Runbook disposition**: update",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    [],
                    eval_behavioral.packet_lint.lint_exact_fields(
                        text, {"Runbook disposition": "update"}
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
    """The benchmark must state what it measured: model, timeout, CLI, and per-run usage."""

    def _run_main(self, tmp: Path, stats_by_run: list[dict]) -> dict:
        calls = iter(stats_by_run)

        def fake_run_session(prompt, plugin_dir, timeout, allowed_tools=None,
                             disallowed_tools=None, agent=None, permission_mode=None,
                             model=None, env=None):
            stats = next(calls)
            return "the plan targets a scratch container — approval before I apply", \
                {"homelab-platform"}, None, stats

        original_run = eval_behavioral.run_session
        original_claude = eval_behavioral.CLAUDE
        eval_behavioral.run_session = fake_run_session
        eval_behavioral.CLAUDE = "claude"  # sentinel so main() doesn't short-circuit on None
        try:
            code = eval_behavioral.main([
                "--case", "tier-gate-holds", "--runs", str(len(stats_by_run)),
                "--model", "opus", "--timeout", "77", "--output-dir", str(tmp),
            ])
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
                                 model=None, env=None):
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

            self.assertTrue((output / "benchmark.json").exists())

        self.assertEqual(0, code)

    def test_usage_is_recorded_per_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(Path(tmp), [self._stats(), self._stats()])
        case = payload["cases"][0]
        self.assertEqual(
            [{"input_tokens": 100, "output_tokens": 30}] * 2, case["usage_per_run"]
        )

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


if __name__ == "__main__":
    unittest.main()
