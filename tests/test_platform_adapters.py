from __future__ import annotations

import json
import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from scripts import generate_platform_adapters
from scripts import validate_fleet


REPO = Path(__file__).resolve().parents[1]
COPILOT_TOOL_ALIASES = {"agent", "edit", "execute", "read", "search", "web"}
WRITE_TOOLS = {"Edit", "NotebookEdit", "Write"}


def _create_directory_link(target: Path, link: Path) -> None:
    """Create the link primitive that can redirect directory traversal on this host."""

    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise unittest.SkipTest(
                f"cannot create a Windows junction for the regression test: {result.stderr}"
            )
    else:
        link.symlink_to(target, target_is_directory=True)


def _remove_directory_link(link: Path) -> None:
    if link.is_symlink():
        link.unlink()
    elif link.exists():
        link.rmdir()


class PlatformAdapterTests(unittest.TestCase):
    def test_tracked_generated_outputs_are_current(self) -> None:
        self.assertEqual(
            [],
            generate_platform_adapters.validate_generated_outputs(REPO),
        )
        self.assertFalse((REPO / "platforms" / "portable").exists())

    def test_python_bytecode_caches_are_not_distribution_artifacts(self) -> None:
        relative = (
            Path("observability")
            / "scripts"
            / "__pycache__"
            / "adapter-test.pyc"
        )
        paths = (
            REPO / "skills" / relative,
            REPO / "platforms" / "copilot" / "skills" / relative,
            REPO / "plugins" / "sde-agents" / "skills" / relative,
        )
        try:
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"transient bytecode")

            expected = generate_platform_adapters.expected_outputs(REPO)
            self.assertFalse(
                any("__pycache__" in path.parts for path in expected),
                expected,
            )
            self.assertEqual(
                [],
                generate_platform_adapters.validate_generated_outputs(REPO),
            )
        finally:
            for path in paths:
                path.unlink(missing_ok=True)
                try:
                    path.parent.rmdir()
                except OSError:
                    pass

    def test_tracked_runtime_byproduct_cannot_evade_generated_drift_check(self) -> None:
        payload = (
            REPO
            / generate_platform_adapters.CODEX_SKILLS
            / "observability"
            / "scripts"
            / "__pycache__"
            / "tracked-adapter-payload.py"
        )
        relative = payload.relative_to(REPO)
        try:
            payload.parent.mkdir(parents=True, exist_ok=True)
            payload.write_text("arbitrary tracked payload\n", encoding="utf-8")
            with mock.patch.object(
                generate_platform_adapters,
                "_repository_tracked_files",
                return_value={relative},
            ):
                issues = generate_platform_adapters.validate_generated_outputs(REPO)
            self.assertTrue(
                any(
                    str(relative) in issue
                    and "stale generated platform adapter" in issue
                    for issue in issues
                ),
                issues,
            )
        finally:
            payload.unlink(missing_ok=True)
            try:
                payload.parent.rmdir()
            except OSError:
                pass

    def test_nested_non_repo_copy_does_not_inherit_parent_tracking_state(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO) as temporary:
            nested_copy = Path(temporary) / "archive"
            nested_copy.mkdir()
            self.assertIsNone(
                generate_platform_adapters._repository_tracked_files(nested_copy)
            )

    def test_non_git_copy_validates_cache_shaped_files_strictly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "archive"
            payload = (
                root
                / generate_platform_adapters.CODEX_SKILLS
                / "__pycache__"
                / "packaged-payload.py"
            )
            (root / ".claude-plugin").mkdir(parents=True)
            (root / ".claude-plugin" / "plugin.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            payload.parent.mkdir(parents=True)
            payload.write_text("packaged payload\n", encoding="utf-8")

            with mock.patch.object(
                generate_platform_adapters,
                "expected_outputs",
                return_value={},
            ):
                issues = generate_platform_adapters.validate_generated_outputs(root)
            self.assertTrue(
                any(
                    str(payload.relative_to(root)) in issue
                    and "stale generated platform adapter" in issue
                    for issue in issues
                ),
                issues,
            )

    def test_write_rejects_linked_generated_root_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            sensitive = root / "canonical-source"
            link = root / generate_platform_adapters.COPILOT_SKILLS
            sensitive.mkdir(parents=True)
            link.parent.mkdir(parents=True)
            sentinel = sensitive / "sentinel.txt"
            sentinel.write_text("must survive\n", encoding="utf-8")
            _create_directory_link(sensitive, link)
            try:
                with mock.patch.object(
                    generate_platform_adapters,
                    "expected_outputs",
                    return_value={},
                ):
                    with self.assertRaisesRegex(ValueError, "link|junction|reparse"):
                        generate_platform_adapters.write_generated_outputs(root)
                self.assertEqual("must survive\n", sentinel.read_text(encoding="utf-8"))
            finally:
                _remove_directory_link(link)

    def test_write_rejects_linked_generated_parent_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            sensitive = root / "canonical-source"
            redirected_target = sensitive / "copilot" / "skills"
            redirected_target.mkdir(parents=True)
            sentinel = redirected_target / "sentinel.txt"
            sentinel.write_text("must survive\n", encoding="utf-8")
            link = root / "platforms"
            _create_directory_link(sensitive, link)
            try:
                with mock.patch.object(
                    generate_platform_adapters,
                    "expected_outputs",
                    return_value={},
                ):
                    with self.assertRaisesRegex(ValueError, "link|junction|reparse"):
                        generate_platform_adapters.write_generated_outputs(root)
                self.assertEqual("must survive\n", sentinel.read_text(encoding="utf-8"))
            finally:
                _remove_directory_link(link)

    def test_canonical_source_links_are_rejected_before_resource_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "repo"
            external = base / "external"
            (root / "agents").mkdir(parents=True)
            (root / "skills").mkdir()
            external.mkdir()
            secret = external / "secret.bin"
            secret.write_bytes(b"external secret")
            link = root / "skills" / "linked-resource"
            _create_directory_link(external, link)
            try:
                with mock.patch.object(
                    generate_platform_adapters,
                    "_guarded_names",
                    return_value=set(),
                ):
                    with self.assertRaisesRegex(
                        ValueError,
                        "canonical source.*(?:link|junction|reparse)",
                    ):
                        generate_platform_adapters.expected_outputs(root)
                self.assertEqual(b"external secret", secret.read_bytes())
            finally:
                _remove_directory_link(link)

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

    def test_codex_adapters_do_not_claim_overridable_defaults_are_controls(self) -> None:
        for path in sorted((REPO / ".codex" / "agents").glob("*.toml")):
            with self.subTest(agent=path.stem):
                generated = tomllib.loads(path.read_text(encoding="utf-8"))
                instructions = generated["developer_instructions"]
                normalized = " ".join(instructions.split())
                self.assertIn(
                    "Parent session permissions can override this requested sandbox",
                    normalized,
                )
                self.assertIn(
                    "Codex custom-agent TOML does not provide a per-agent tool allowlist",
                    normalized,
                )
                for false_control in (
                    "Filesystem mutation is enforced by",
                    "The read-only sandbox enforces filesystem immutability",
                    "this role has no subagent-spawn authority",
                    "you hold no shell",
                    "no write tools, no shell",
                    "safe to spawn speculatively",
                    "Your tool list is the platform-enforced boundary",
                    "reviewers can't edit, researchers can't write",
                    "you hold no `Agent` tool",
                ):
                    self.assertNotIn(false_control, normalized)

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
