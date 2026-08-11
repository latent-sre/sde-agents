from __future__ import annotations

import unittest
import json
from pathlib import Path

from scripts import validate_fleet
from tests.validate_fleet_wiring_support import PluginWiringMixin


class PluginWiringBehavioralTests(PluginWiringMixin, unittest.TestCase):
    def test_the_real_repo_is_a_valid_plugin(self) -> None:
        # The positive control. Without it, every test below could pass for the wrong reason.
        self.assertEqual([], self._issues_after(lambda _: None, check_adapters=True))

    def test_behavioral_assertion_typo_fails_the_ordinary_fleet_gate(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "evals" / "behavioral" / "contracts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["cases"][0]["must_macth"] = ["silent typo"]
            path.write_text(json.dumps(document), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("must_macth" in issue for issue in issues), issues)

    def test_behavioral_case_without_semantic_oracle_fails_the_fleet_gate(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "evals" / "behavioral" / "contracts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            case = document["cases"][1]
            case.pop("must_match", None)
            case.pop("packet_shape", None)
            case.pop("packet_learning_mode", None)
            path.write_text(json.dumps(document), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("semantic output oracle" in issue for issue in issues), issues)

    def test_behavioral_invalid_regex_and_duplicate_id_fail_the_fleet_gate(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "evals" / "behavioral" / "contracts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["cases"][1]["id"] = document["cases"][0]["id"]
            document["cases"][1]["must_match"] = ["("]
            path.write_text(json.dumps(document), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("duplicated" in issue for issue in issues), issues)
        self.assertTrue(any("valid regex" in issue for issue in issues), issues)

    def test_behavioral_fire_contract_and_agent_namespace_fail_the_fleet_gate(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "evals" / "behavioral" / "contracts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            case = document["cases"][0]
            case.pop("expect_fires")
            case["agent"] = "sde-fullstack"
            path.write_text(json.dumps(document), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("component-fire contract" in issue for issue in issues), issues)
        self.assertTrue(any("plugin-qualified" in issue for issue in issues), issues)

    def test_behavioral_denied_tool_typo_and_empty_positive_regex_fail_the_fleet_gate(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "evals" / "behavioral" / "contracts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            case = document["cases"][0]
            case["disallowed_tools"] = ["BsaH"]
            case["must_match"] = [".*"]
            path.write_text(json.dumps(document), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("runtime tool" in issue and "BsaH" in issue for issue in issues), issues)
        self.assertTrue(any("matches the empty string" in issue for issue in issues), issues)

    def test_behavioral_tool_vocabulary_matches_the_full_runtime(self) -> None:
        from scripts import eval_behavioral as behavioral_bootstrap

        behavioral = behavioral_bootstrap.load_current_evaluator()
        self.assertEqual(validate_fleet.RUNTIME_TOOLS, behavioral.RUNTIME_TOOLS)

    def test_behavioral_allowed_tools_are_required_typed_and_nonoverlapping(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "evals" / "behavioral" / "contracts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["cases"][0].pop("allowed_tools")
            document["cases"][1]["allowed_tools"] = ["PwerShell"]
            document["cases"][2]["allowed_tools"] = ["Bash"]
            document["cases"][2]["disallowed_tools"] = ["Bash"]
            path.write_text(json.dumps(document), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("allowed_tools" in issue and "required" in issue for issue in issues), issues)
        self.assertTrue(any("PwerShell" in issue and "runtime tool" in issue for issue in issues), issues)
        self.assertTrue(any("overlap" in issue and "Bash" in issue for issue in issues), issues)

    def test_behavioral_vacuous_positive_regexes_fail_the_fleet_gate(self) -> None:
        for pattern in (".", r"\S", r"\b", r"[\s\S]", "(?=x)", ".{1}"):
            with self.subTest(pattern=pattern):
                def mutate(repo: Path, pattern: str = pattern) -> None:
                    path = repo / "evals" / "behavioral" / "contracts.json"
                    document = json.loads(path.read_text(encoding="utf-8"))
                    document["cases"][0]["must_match"] = [pattern]
                    path.write_text(json.dumps(document), encoding="utf-8")

                issues = self._issues_after(mutate)
                self.assertTrue(
                    any("raw alphanumeric literal" in issue for issue in issues), issues
                )

    def test_behavioral_exact_fields_schema_fails_through_the_fleet_gate(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "evals" / "behavioral" / "contracts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["cases"][0]["exact_fields"] = {
                "Promoton state": "inconclusive",
                "Owner": 7,
            }
            path.write_text(json.dumps(document), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("Promoton state" in issue and "unknown literal" in issue for issue in issues), issues)
        self.assertTrue(any("Owner" in issue and "non-empty exact string" in issue for issue in issues), issues)

    def test_behavioral_non_string_enums_return_fleet_findings_not_loader_crashes(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "evals" / "behavioral" / "contracts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            case = document["cases"][0]
            case["permission_mode"] = []
            case["packet_shape"] = {}
            case["packet_learning_mode"] = []
            case["agent"] = 17
            path.write_text(json.dumps(document), encoding="utf-8")

        issues = self._issues_after(mutate)
        for field in ("permission_mode", "packet_shape", "packet_learning_mode", "agent"):
            with self.subTest(field=field):
                self.assertTrue(any(field in issue for issue in issues), issues)


if __name__ == "__main__":
    unittest.main()
