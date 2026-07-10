from __future__ import annotations

import unittest
from pathlib import Path

from scripts import validate_fleet


FIXTURES = Path(__file__).parent / "fixtures"


class FleetValidatorTests(unittest.TestCase):
    def test_valid_fleet_and_generated_inventory(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(FIXTURES / "valid")
        self.assertEqual([], issues)

    def test_agent_requires_explicit_tools(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "missing-tools", check_inventory=False
        )
        self.assertTrue(any("missing explicit tools authority" in issue for issue in issues))

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


if __name__ == "__main__":
    unittest.main()
