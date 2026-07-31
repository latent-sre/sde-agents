from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from scripts import generate_platform_adapters
from scripts import validate_fleet


REPO = Path(__file__).resolve().parents[1]
COPILOT_TOOL_ALIASES = {"agent", "edit", "execute", "read", "search", "web"}
WRITE_TOOLS = {"Edit", "NotebookEdit", "Write"}


class PlatformAdapterTests(unittest.TestCase):
    def test_tracked_generated_outputs_are_current(self) -> None:
        self.assertEqual(
            [],
            generate_platform_adapters.validate_generated_outputs(REPO),
        )
        self.assertFalse((REPO / "platforms" / "portable").exists())

    def test_every_canonical_agent_has_both_host_adapters(self) -> None:
        names = {path.stem for path in (REPO / "agents").glob("*.md")}
        copilot = {
            path.name.removesuffix(".agent.md")
            for path in (REPO / ".github" / "agents").glob("*.agent.md")
        }
        codex = {path.stem for path in (REPO / ".codex" / "agents").glob("*.toml")}
        self.assertEqual(names, copilot)
        self.assertEqual(names, codex)

    def test_copilot_adapters_use_only_native_aliases(self) -> None:
        for path in sorted((REPO / ".github" / "agents").glob("*.agent.md")):
            with self.subTest(agent=path.stem):
                fields = validate_fleet.parse_frontmatter(path)
                self.assertIsNotNone(fields)
                tools = set(validate_fleet.split_tools(fields["tools"]))
                self.assertTrue(tools)
                self.assertLessEqual(tools, COPILOT_TOOL_ALIASES)

    def test_guarded_copilot_agents_have_no_shell_tool(self) -> None:
        guard = validate_fleet.load_guard(REPO)
        for name in sorted(guard.GUARDED_AGENT_NAMES):
            with self.subTest(agent=name):
                fields = validate_fleet.parse_frontmatter(
                    REPO / ".github" / "agents" / f"{name}.agent.md"
                )
                tools = set(validate_fleet.split_tools(fields["tools"]))
                self.assertNotIn("execute", tools)

    def test_copilot_builder_retains_execution_and_edit_authority(self) -> None:
        fields = validate_fleet.parse_frontmatter(
            REPO / ".github" / "agents" / "sde-fullstack.agent.md"
        )
        tools = set(validate_fleet.split_tools(fields["tools"]))
        self.assertIn("execute", tools)
        self.assertIn("edit", tools)

    def test_preloaded_claude_skills_become_explicit_host_requirements(self) -> None:
        canonical = validate_fleet.parse_frontmatter(
            REPO / "agents" / "sde-fullstack.md"
        )
        skill_names = validate_fleet.split_tools(canonical["skills"])
        paths = (
            REPO / ".github" / "agents" / "sde-fullstack.agent.md",
            REPO / ".codex" / "agents" / "sde-fullstack.toml",
        )
        for path in paths:
            with self.subTest(path=path.relative_to(REPO)):
                text = path.read_text(encoding="utf-8")
                normalized = " ".join(text.split())
                for skill_name in skill_names:
                    self.assertIn(skill_name, text)
                self.assertIn("every listed installed skill", normalized)
                self.assertNotIn("preloaded craft skills", text)
                self.assertNotIn("which is **not** preloaded", text)
                self.assertNotIn("already in your context", text)
                self.assertNotIn("already in your\ncontext", text)

    def test_codex_sandbox_mode_tracks_canonical_write_authority(self) -> None:
        for source in sorted((REPO / "agents").glob("*.md")):
            with self.subTest(agent=source.stem):
                fields = validate_fleet.parse_frontmatter(source)
                tools = set(validate_fleet.split_tools(fields["tools"]))
                expected = "workspace-write" if tools & WRITE_TOOLS else "read-only"
                generated = tomllib.loads(
                    (REPO / ".codex" / "agents" / f"{source.stem}.toml").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(source.stem, generated["name"])
                self.assertEqual(expected, generated["sandbox_mode"])

    def test_host_agent_adapters_have_no_claude_runtime_references(self) -> None:
        paths = [
            *(REPO / ".github" / "agents").glob("*.agent.md"),
            *(REPO / ".codex" / "agents").glob("*.toml"),
        ]
        for path in sorted(paths):
            with self.subTest(path=path.relative_to(REPO)):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("sde-agents:", text)
                self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", text)
                self.assertNotIn("the variable is substituted", text)
                self.assertNotIn("platform-facts owner", text)
                for false_control in (
                    "A `PreToolUse` hook backs this",
                    "is **enforced** by a `PreToolUse` hook",
                    "that half is **enforced**: a `PreToolUse` hook",
                    "`permissionMode` is inert",
                    "add a destructive-command matcher",
                    "Your Bash access",
                    "you hold no `Agent` tool",
                    "Read/Grep/Glob",
                    "read-only, on the allowlist",
                    "hooks/hooks.json",
                    "## Claude Code specifics",
                    "Claude Code sandbox counts only",
                    "authoring suites of Claude Code agents",
                    "Before writing any frontmatter, read the fleet's single source",
                ):
                    self.assertNotIn(false_control, text)

    def test_host_skills_have_no_live_claude_namespace_references(self) -> None:
        roots = (
            REPO / "platforms" / "copilot" / "skills",
            REPO / "plugins" / "sde-agents" / "skills",
        )
        for root in roots:
            claude_reference = (
                root
                / "prompt-craft"
                / "references"
                / "claude-code-frontmatter.md"
            )
            for path in sorted(root.rglob("*.md")):
                if path == claude_reference:
                    continue
                with self.subTest(path=path.relative_to(REPO)):
                    text = path.read_text(encoding="utf-8")
                    self.assertNotIn("sde-agents:", text)
                    self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", text)
                    self.assertNotRegex(text, r"`skills/[a-z0-9-]+/")
                    for false_control in (
                        "Plugin-shipped agents silently ignore",
                        "`Bash(git diff:*)`",
                        "`memory:` auto-enables",
                        "via the Agent tool",
                        "If the Agent tool is unavailable",
                        "its preloaded skills",
                        "Workers never see the parent conversation",
                        "**not** the parent's conversation",
                        "preloads this skill",
                        "builder preloads both craft skills",
                        "A researcher with WebFetch",
                    ):
                        self.assertNotIn(false_control, text)

    def test_explicit_only_skills_keep_host_specific_invocation_controls(self) -> None:
        for name in ("host-onboard", "service-onboard"):
            with self.subTest(skill=name):
                copilot_skill = (
                    REPO
                    / "platforms"
                    / "copilot"
                    / "skills"
                    / name
                    / "SKILL.md"
                )
                copilot_fields = validate_fleet.parse_frontmatter(copilot_skill)
                self.assertEqual(
                    "true",
                    copilot_fields["disable-model-invocation"],
                )

                codex_skill = (
                    REPO
                    / "plugins"
                    / "sde-agents"
                    / "skills"
                    / name
                    / "SKILL.md"
                )
                codex_fields = validate_fleet.parse_frontmatter(codex_skill)
                self.assertNotIn("disable-model-invocation", codex_fields)
                policy = (
                    codex_skill.parent / "agents" / "openai.yaml"
                ).read_text(encoding="utf-8")
                self.assertIn("display_name:", policy)
                self.assertIn("short_description:", policy)
                self.assertIn("allow_implicit_invocation: false", policy)

    def test_non_claude_plugins_do_not_load_the_claude_guard(self) -> None:
        copilot = json.loads((REPO / "plugin.json").read_text(encoding="utf-8"))
        codex = json.loads(
            (
                REPO
                / "plugins"
                / "sde-agents"
                / ".codex-plugin"
                / "plugin.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual("./hooks/copilot-hooks.json", copilot["hooks"])
        hook_config = json.loads(
            (REPO / copilot["hooks"].removeprefix("./")).read_text(encoding="utf-8")
        )
        self.assertEqual({}, hook_config["hooks"])
        self.assertNotIn("hooks", codex)
        self.assertFalse(
            (REPO / "plugins" / "sde-agents" / "hooks" / "hooks.json").exists()
        )

    def test_manifest_identity_and_versions_cannot_drift(self) -> None:
        manifests = [
            json.loads(
                (REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
            ),
            json.loads((REPO / "plugin.json").read_text(encoding="utf-8")),
            json.loads(
                (
                    REPO
                    / "plugins"
                    / "sde-agents"
                    / ".codex-plugin"
                    / "plugin.json"
                ).read_text(encoding="utf-8")
            ),
        ]
        for field in (
            "name",
            "version",
            "description",
            "author",
            "homepage",
            "repository",
            "license",
            "keywords",
        ):
            with self.subTest(field=field):
                self.assertEqual([manifests[0][field]] * 3, [m[field] for m in manifests])

        self.assertEqual("./.github/agents/", manifests[1]["agents"])
        self.assertEqual("./platforms/copilot/skills/", manifests[1]["skills"])
        self.assertNotIn("agents", manifests[2])
        self.assertEqual("./skills/", manifests[2]["skills"])

    def test_codex_marketplace_points_to_the_isolated_plugin_root(self) -> None:
        marketplace = json.loads(
            (
                REPO / ".agents" / "plugins" / "marketplace.json"
            ).read_text(encoding="utf-8")
        )
        entries = [
            entry
            for entry in marketplace["plugins"]
            if entry["name"] == "sde-agents"
        ]
        self.assertEqual(1, len(entries))
        self.assertEqual(
            {
                "source": "local",
                "path": "./plugins/sde-agents",
            },
            entries[0]["source"],
        )


if __name__ == "__main__":
    unittest.main()
