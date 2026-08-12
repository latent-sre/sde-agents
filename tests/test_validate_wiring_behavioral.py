from __future__ import annotations

import unittest
import json
from pathlib import Path

from scripts import validate_fleet
from tests.support import repo_copy
from tests.validate_fleet_wiring_support import PluginWiringMixin


class PluginWiringBehavioralTests(PluginWiringMixin, unittest.TestCase):
    def _behavioral_issues_after(self, mutate) -> list[str]:
        with repo_copy() as repo:
            mutate(repo)
            agent_names = [path.stem for path in (repo / "agents").glob("*.md")]
            skill_names = [path.parent.name for path in (repo / "skills").glob("*/SKILL.md")]
            return validate_fleet.validate_behavioral_contracts(
                repo,
                agent_names,
                skill_names,
            )

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

    def test_behavioral_tool_vocabulary_matches_the_full_runtime(self) -> None:
        from scripts import eval_behavioral as behavioral_bootstrap

        behavioral = behavioral_bootstrap.load_current_evaluator()
        self.assertEqual(validate_fleet.RUNTIME_TOOLS, behavioral.RUNTIME_TOOLS)

    def test_behavioral_wrapper_failures_are_reported_without_retesting_the_schema(self) -> None:
        def missing_runner(repo: Path) -> None:
            (repo / "scripts" / "eval_behavioral.py").unlink()

        def broken_runner(repo: Path) -> None:
            (repo / "scripts" / "eval_behavioral.py").write_text(
                "raise RuntimeError('broken behavioral validator')\n",
                encoding="utf-8",
            )

        def unreadable_document(repo: Path) -> None:
            (repo / "evals" / "behavioral" / "contracts.json").write_text(
                "not json {\n",
                encoding="utf-8",
            )

        def empty_corpus(repo: Path) -> None:
            (repo / "evals" / "behavioral" / "contracts.json").unlink()

        for label, mutate, expected in (
            ("missing runner", missing_runner, "without their schema validator"),
            ("broken runner", broken_runner, "could not load"),
            ("unreadable document", unreadable_document, "unreadable behavioral case document"),
            ("empty corpus", empty_corpus, "no behavioral case documents"),
        ):
            with self.subTest(label=label):
                issues = self._behavioral_issues_after(mutate)
                self.assertTrue(any(expected in issue for issue in issues), issues)

    def test_behavioral_wrapper_rejects_cross_document_duplicate_ids(self) -> None:
        def mutate(repo: Path) -> None:
            source = repo / "evals" / "behavioral" / "contracts.json"
            source.with_name("duplicate.json").write_bytes(source.read_bytes())

        issues = self._behavioral_issues_after(mutate)
        self.assertTrue(any("duplicates" in issue for issue in issues), issues)


if __name__ == "__main__":
    unittest.main()
