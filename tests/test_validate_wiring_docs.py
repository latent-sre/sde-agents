from __future__ import annotations

import unittest
from pathlib import Path

from scripts import validate_fleet
from tests.validate_fleet_wiring_support import PluginWiringMixin


class PluginWiringDocsTests(PluginWiringMixin, unittest.TestCase):
    def test_bare_cross_reference_in_a_description_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "code-reviewer.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "use sde-agents:lab-audit", "use lab-audit"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("without the plugin namespace" in i for i in issues), issues)

    def test_bare_cross_reference_in_a_folded_description_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "code-reviewer.md"
            text = path.read_text(encoding="utf-8")
            start = text.index("description:")
            end = text.index("\ntools:", start)
            path.write_text(
                text[:start]
                + "description: >\n  Use lab-audit for a whole home-lab.\n"
                + text[end + 1:],
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("without the plugin namespace" in i for i in issues), issues)

    def test_home_claude_skill_path_is_reported(self) -> None:
        # The fleet-breaker: ~/.claude/skills does NOT hold this fleet once it ships as a plugin,
        # and `service-onboard` (model-invocation-disabled) is reachable ONLY by path -- so a stale
        # path here silently removes a capability rather than erroring.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "homelab-platform.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "${CLAUDE_PLUGIN_ROOT}/skills/service-onboard/SKILL.md",
                    "~/.claude/skills/service-onboard/SKILL.md",
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("will NOT contain this fleet" in i for i in issues), issues)

    def test_documentation_reference_to_user_level_agents_is_not_a_false_positive(self) -> None:
        # `~/.claude/agents/*.md` correctly describes where USER-level agents live; the prompt
        # skills teach it. Only a path resolved to a specific file is the bug.
        issues = self._issues_after(lambda _: None)
        self.assertEqual([], [i for i in issues if "will NOT contain this fleet" in i])

    def test_typo_d_skills_list_entry_is_reported(self) -> None:
        # sde-fullstack's real `skills:` frontmatter. A typo here used to pass validate_fleet.py,
        # all unit tests, and `claude plugin validate --strict` -- only the 9-minute behavioral
        # probe would have caught it, and only for 2 of the 3 entries.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "sde-fullstack.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "  - backend-craft", "  - backend-crafts"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any("'backend-crafts'" in i and "does not resolve" in i for i in issues), issues
        )

    def test_skills_list_naming_service_onboard_is_reported(self) -> None:
        # service-onboard is the one skill in this repo with `disable-model-invocation: true`, which
        # makes it unpreloadable by construction. Use it as the real-repo trigger for that check.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "sde-fullstack.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "  - root-cause", "  - root-cause\n  - service-onboard"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any("'service-onboard'" in i and "disable-model-invocation" in i for i in issues),
            issues,
        )

    def test_orphaned_reference_file_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            (repo / "skills" / "backend-craft" / "references" / "caching.md").write_text(
                "# Caching\n\nNever linked from SKILL.md.\n", encoding="utf-8"
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any("orphaned" in i and "caching.md" in i for i in issues), issues
        )

    def test_real_repo_has_no_orphaned_reference_files(self) -> None:
        # The positive control for the orphan check, mirroring test_the_real_repo_is_a_valid_plugin.
        issues = self._issues_after(lambda _: None)
        self.assertEqual([], [i for i in issues if "orphaned" in i])

    def test_claude_md_without_the_import_is_reported(self) -> None:
        # Claude Code reads CLAUDE.md, not AGENTS.md. Lose the one-line import and the guide is
        # orphaned -- still in the repo, never in any session, and nothing errors.
        def mutate(repo: Path) -> None:
            (repo / "CLAUDE.md").write_text("# project notes, no import\n", encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("never loaded" in i for i in issues), issues)

    def test_missing_claude_md_bridge_is_reported(self) -> None:
        issues = self._issues_after(lambda r: (r / "CLAUDE.md").unlink())
        self.assertTrue(any("never loaded" in i for i in issues), issues)

    def test_dangling_import_without_agents_md_is_reported(self) -> None:
        issues = self._issues_after(lambda r: (r / "AGENTS.md").unlink())
        self.assertTrue(any("resolves to nothing" in i for i in issues), issues)

    def test_stale_path_in_the_guide_is_reported(self) -> None:
        # The rename-a-script case: the guide keeps naming the old path, and only a reader who
        # tries the command ever finds out.
        def mutate(repo: Path) -> None:
            path = repo / "AGENTS.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "scripts/probe_plugin.py", "scripts/probe_plugins.py"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("'scripts/probe_plugins.py'" in i for i in issues), issues)

    def test_alias_drift_in_the_guide_is_reported(self) -> None:
        # Add an alias to ALIAS_MODELS (or drop one) and the guide's paraphrase must follow.
        def mutate(repo: Path) -> None:
            path = repo / "AGENTS.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace("`fable`", "`fable-classic`"),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("omits `fable`" in i for i in issues), issues)

    def test_repo_with_no_guide_at_all_is_valid(self) -> None:
        # The check is self-gating: a repo that makes no guide claims has nothing to drift.
        def mutate(repo: Path) -> None:
            (repo / "AGENTS.md").unlink()
            (repo / "CLAUDE.md").unlink()

        issues = self._issues_after(mutate)
        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
