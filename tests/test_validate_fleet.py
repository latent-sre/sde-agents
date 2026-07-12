from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import validate_fleet


FIXTURES = Path(__file__).parent / "fixtures"


VALID_AGENT = (
    "---\n"
    "name: builder\n"
    "description: Use when implementing a small feature.\n"
    "tools: Read, Write\n"
    "model: inherit\n"
    "---\n\n"
    "# Builder\n\n"
    "## Review packet\n\n"
    "- **Changed**: what changed.\n"
)


class FleetValidatorTests(unittest.TestCase):
    def test_valid_fleet_and_generated_inventory(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(FIXTURES / "valid")
        self.assertEqual([], issues)

    def test_agent_requires_explicit_tools(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "missing-tools", check_inventory=False
        )
        self.assertTrue(any("missing explicit tools authority" in issue for issue in issues))

    def test_unknown_tool_is_reported(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "unknown-tool", check_inventory=False
        )
        self.assertTrue(any("unknown tool 'Bogus'" in issue for issue in issues))

    def test_missing_bundled_reference_fails(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "missing-reference", check_inventory=False
        )
        self.assertTrue(any("references/missing.md" in issue for issue in issues))

    def test_evidence_label_drift_is_reported(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "evidence-drift", check_inventory=False
        )
        self.assertTrue(any("evidence labels drifted" in issue for issue in issues))

    def test_missing_packet_is_reported(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "missing-packet", check_inventory=False
        )
        self.assertTrue(any("missing end-of-task packet" in issue for issue in issues))

    def test_inventory_drift_is_reported(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(FIXTURES / "inventory-drift")
        self.assertTrue(any("inventory drifted" in issue for issue in issues))

    def test_folded_description_is_supported(self) -> None:
        fields = validate_fleet.parse_frontmatter(FIXTURES / "folded" / "builder.md")
        self.assertIsNotNone(fields)
        self.assertEqual("Use when implementing a small feature.", fields["description"])

    def test_inventory_replacement_is_pure(self) -> None:
        content = (FIXTURES / "inventory-drift" / "README.md").read_text(encoding="utf-8")
        expected = validate_fleet.render_inventory(["builder"], ["craft"])
        updated = validate_fleet.replace_inventory(content, expected)
        self.assertIn(expected, updated)
        self.assertNotIn("stale", updated)

    def test_inventory_replacement_preserves_crlf(self) -> None:
        content = (
            (FIXTURES / "inventory-drift" / "README.md")
            .read_text(encoding="utf-8")
            .replace("\n", "\r\n")
        )
        expected = validate_fleet.render_inventory(["builder"], ["craft"])
        updated = validate_fleet.replace_inventory(content, expected)
        self.assertNotIn("\n", updated.replace("\r\n", ""))


    # --- main() exit-code contract (T1): CI's entire signal rests on this ---

    def test_main_returns_zero_on_valid_fleet(self) -> None:
        self.assertEqual(0, validate_fleet.main(["--root", str(FIXTURES / "valid")]))

    def test_main_returns_one_on_invalid_fleet(self) -> None:
        self.assertEqual(1, validate_fleet.main(["--root", str(FIXTURES / "missing-tools")]))

    # --- --write-inventory round-trip (T3): the operation the single-source design depends on ---

    def test_main_write_inventory_regenerates_readme_and_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "valid", dst)
            readme = dst / "README.md"
            drifted = validate_fleet.INVENTORY_RE.sub(
                "<!-- fleet-inventory:start -->\nstale\n<!-- fleet-inventory:end -->",
                readme.read_text(encoding="utf-8"),
                count=1,
            )
            readme.write_text(drifted, encoding="utf-8")
            # precondition: the drift makes plain validation fail
            self.assertEqual(1, validate_fleet.main(["--root", str(dst)]))
            # write mode repairs the README and exits clean
            self.assertEqual(
                0, validate_fleet.main(["--write-inventory", "--root", str(dst)])
            )
            repaired = readme.read_text(encoding="utf-8")
            self.assertNotIn("stale", repaired)
            self.assertIn("`builder`", repaired)
            self.assertIn("`craft`", repaired)
            # idempotent: a following read-only run stays green
            self.assertEqual(0, validate_fleet.main(["--root", str(dst)]))

    def test_replace_inventory_without_markers_raises(self) -> None:
        with self.assertRaises(ValueError):
            validate_fleet.replace_inventory("# no markers here\n", "whatever")

    # --- frontmatter parser edge cases (T6) ---

    def _parse(self, text: str) -> dict | None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "f.md"
            path.write_text(text, encoding="utf-8")
            return validate_fleet.parse_frontmatter(path)

    def test_parser_returns_none_without_opening_marker(self) -> None:
        self.assertIsNone(self._parse("name: builder\n---\n"))

    def test_parser_returns_none_when_frontmatter_is_unterminated(self) -> None:
        self.assertIsNone(self._parse("---\nname: builder\n\n# body but no closing marker\n"))

    def test_parser_strips_surrounding_quotes_from_values(self) -> None:
        fields = self._parse('---\nname: "builder"\ncolor: \'red\'\n---\n')
        self.assertEqual("builder", fields["name"])
        self.assertEqual("red", fields["color"])

    def test_parser_reads_literal_block_scalar(self) -> None:
        fields = self._parse("---\ndescription: |\n  line one\n  line two\n---\n")
        self.assertIn("line one", fields["description"])
        self.assertIn("line two", fields["description"])

    # --- validator guardrail branches (T2) ---

    def _agent_issues(self, *files: tuple[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            agents = Path(tmp) / "agents"
            agents.mkdir()
            for filename, body in files:
                (agents / filename).write_text(body, encoding="utf-8")
            issues, _ = validate_fleet.validate_agents(Path(tmp))
            return issues

    def test_agent_name_must_match_filename(self) -> None:
        body = VALID_AGENT.replace("name: builder", "name: other")
        self.assertTrue(any("must match filename" in i for i in self._agent_issues(("builder.md", body))))

    def test_unsupported_model_is_reported(self) -> None:
        body = VALID_AGENT.replace("model: inherit", "model: gpt-4")
        self.assertTrue(any("unsupported model" in i for i in self._agent_issues(("builder.md", body))))

    def test_invalid_agent_name_is_reported(self) -> None:
        # uppercase fails NAME_RE; filename Builder.md keeps name==stem so only the regex branch fires
        body = VALID_AGENT.replace("name: builder", "name: Builder")
        self.assertTrue(any("invalid agent name" in i for i in self._agent_issues(("Builder.md", body))))

    def test_duplicate_agent_names_are_reported(self) -> None:
        second = VALID_AGENT  # both files declare name: builder
        issues = self._agent_issues(("builder.md", VALID_AGENT), ("clone.md", second))
        self.assertTrue(any("duplicate agent names" in i for i in issues))

    def test_missing_agents_directory_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            issues, names = validate_fleet.validate_agents(Path(tmp))
            self.assertEqual([], names)
            self.assertTrue(any("missing agents directory" in i for i in issues))


if __name__ == "__main__":
    unittest.main()
