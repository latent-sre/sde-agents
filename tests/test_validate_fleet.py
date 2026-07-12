from __future__ import annotations

import json
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

    def _skill_issues(self, name: str, frontmatter: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "skills" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\n{frontmatter}---\n\nBody.\n", encoding="utf-8"
            )
            issues, _ = validate_fleet.validate_skills(Path(tmp))
            return issues

    def test_unknown_skill_frontmatter_key_is_reported(self) -> None:
        # Symmetric with the agent check. Before this, the skill path validated name/description/
        # bundle refs but never the KEY namespace, so a `disable-model-invocaton` typo left a
        # side-effect skill model-invocable with no error (external-review gap).
        issues = self._skill_issues(
            "craft",
            "name: craft\ndescription: Use when building.\ndisable-model-invocaton: true\n",
        )
        self.assertTrue(
            any("unknown frontmatter key" in i and "disable-model-invocaton" in i for i in issues),
            issues,
        )

    def test_documented_skill_frontmatter_keys_are_accepted(self) -> None:
        # The full documented set must pass, or the allowlist is a false tripwire.
        extra = "when_to_use: x\nallowed-tools: Read\nmodel: inherit\neffort: high\ncontext: fresh\n"
        issues = self._skill_issues(
            "craft", "name: craft\ndescription: Use when building.\n" + extra
        )
        self.assertEqual([], [i for i in issues if "frontmatter key" in i])

    def test_agent_name_must_match_filename(self) -> None:
        body = VALID_AGENT.replace("name: builder", "name: other")
        self.assertTrue(any("must match filename" in i for i in self._agent_issues(("builder.md", body))))

    def test_unknown_model_is_reported(self) -> None:
        body = VALID_AGENT.replace("model: inherit", "model: gpt-4")
        self.assertTrue(any("unknown model" in i for i in self._agent_issues(("builder.md", body))))

    def test_fable_alias_is_accepted(self) -> None:
        # `fable` is a documented Claude Code alias (code.claude.com/docs/en/sub-agents);
        # rejecting it was a real bug, so pin the fix.
        body = VALID_AGENT.replace("model: inherit", "model: fable")
        self.assertEqual([], [i for i in self._agent_issues(("builder.md", body)) if "model" in i])

    def test_pinned_full_model_id_is_a_policy_error_not_a_schema_error(self) -> None:
        # Valid at runtime, banned by fleet policy — the message must say so, not claim it's unknown.
        body = VALID_AGENT.replace("model: inherit", "model: claude-opus-4-8")
        issues = [i for i in self._agent_issues(("builder.md", body)) if "model" in i]
        self.assertTrue(any("pinned" in i for i in issues), issues)
        self.assertFalse(any("unknown model" in i for i in issues), issues)

    def test_scoped_agent_grant_is_reported_as_a_false_restriction(self) -> None:
        # `Agent(code-reviewer)` restricts spawning only for a main-thread agent (`claude --agent`).
        # Everything in agents/ is a SUBAGENT definition, where the type list is ignored — so this
        # reads like a limit and grants unrestricted spawn. It must not pass silently.
        body = VALID_AGENT.replace("tools: Read", "tools: Read, Agent(code-reviewer)")
        issues = self._agent_issues(("builder.md", body))
        self.assertTrue(any("does not restrict anything here" in i for i in issues), issues)

    def test_scoped_grant_survives_the_comma_split(self) -> None:
        # A naive split(",") shreds `Agent(worker, researcher)` into `Agent(worker` and `researcher)`,
        # which would surface as two bogus "unknown tool" errors instead of the real problem.
        self.assertEqual(
            ["Read", "Agent(worker, researcher)", "Bash"],
            validate_fleet.split_tools("Read, Agent(worker, researcher), Bash"),
        )
        body = VALID_AGENT.replace("tools: Read", "tools: Read, Agent(worker, researcher)")
        issues = self._agent_issues(("builder.md", body))
        self.assertFalse(any("unknown tool" in i for i in issues), issues)

    def test_real_but_unadopted_tool_is_a_policy_error_not_a_schema_error(self) -> None:
        body = VALID_AGENT.replace("tools: Read", "tools: Read, PowerShell")
        issues = [i for i in self._agent_issues(("builder.md", body)) if "PowerShell" in i]
        self.assertTrue(any("not adopted by this fleet" in i for i in issues), issues)
        self.assertFalse(any("is not a Claude Code tool" in i for i in issues), issues)

    def test_tool_unavailable_to_subagents_is_reported(self) -> None:
        body = VALID_AGENT.replace("tools: Read", "tools: Read, AskUserQuestion")
        issues = self._agent_issues(("builder.md", body))
        self.assertTrue(any("never available to a subagent" in i for i in issues), issues)

    def test_retired_tool_names_are_rejected(self) -> None:
        # BashOutput/KillShell/SlashCommand were allowed but appear nowhere in the canonical table.
        for retired in ("BashOutput", "KillShell", "SlashCommand"):
            body = VALID_AGENT.replace("tools: Read", f"tools: Read, {retired}")
            issues = self._agent_issues(("builder.md", body))
            self.assertTrue(any("is not a Claude Code tool" in i for i in issues), (retired, issues))

    def test_unknown_frontmatter_key_is_reported(self) -> None:
        # An unrecognized key is not guaranteed to fail loudly, so a typo silently drops whatever
        # it configured. The key namespace itself is the tripwire.
        body = VALID_AGENT.replace("model: inherit", "hook: PreToolUse\nmodel: inherit")
        issues = self._agent_issues(("builder.md", body))
        self.assertTrue(any("unknown frontmatter key" in i and "'hook'" in i for i in issues), issues)

    def test_known_optional_frontmatter_keys_are_accepted(self) -> None:
        # The documented fields must pass, or the allowlist becomes a false tripwire. `hooks`,
        # `mcpServers`, and `permissionMode` are deliberately NOT here — see the test below.
        extra = "skills: runbook\neffort: high\nisolation: worktree\nmaxTurns: 5\n"
        body = VALID_AGENT.replace("model: inherit", extra + "model: inherit")
        self.assertEqual([], [i for i in self._agent_issues(("builder.md", body)) if "frontmatter key" in i])

    def test_fields_that_a_plugin_silently_ignores_are_rejected(self) -> None:
        # THE bug this whole layout exists to prevent. Claude Code silently ignores `hooks`,
        # `mcpServers`, and `permissionMode` on a plugin-shipped agent. This fleet ships as a
        # plugin, so a `hooks:` block on code-reviewer would look exactly like a read-only guard
        # and be nothing at all — and no test, no load error, and no log would say so.
        for field in ("hooks", "mcpServers", "permissionMode"):
            with self.subTest(field=field):
                body = VALID_AGENT.replace("model: inherit", f"{field}: whatever\nmodel: inherit")
                issues = self._agent_issues(("builder.md", body))
                self.assertTrue(
                    any("SILENTLY IGNORED" in i and repr(field) in i for i in issues), issues
                )

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


REPO = Path(__file__).resolve().parents[1]

READONLY_BASH_AGENT = (
    "---\n"
    "name: auditor\n"
    "description: Use when auditing something read-only.\n"
    "tools: Read, Grep, Bash\n"
    "model: inherit\n"
    "---\n\n"
    "# Auditor\n\n"
    "## Review packet\n\n"
    "- **Changed**: nothing.\n"
)


class PluginWiringTests(unittest.TestCase):
    """Tripwires for failures that are SILENT at runtime.

    A plugin-shipped agent cannot carry its own `hooks:` — Claude Code ignores the field without a
    word. So the read-only guard has exactly one place to live (hooks/hooks.json) and exactly one
    way to recognize its subject (the payload's namespaced `agent_type`). Break any link in that
    chain and nothing errors, nothing logs, and code-reviewer simply runs Bash unguarded against
    the repository it was pointed at. Only a validator can see it, so each link gets a test.

    These mutate a COPY of the real repository: the invariant is about this fleet's actual wiring,
    not a synthetic fixture that could drift away from it.
    """

    def _issues_after(self, mutate) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(
                REPO, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "tests")
            )
            mutate(dst)
            issues, _, _ = validate_fleet.validate_repo(dst, check_inventory=False)
            return issues

    def test_the_real_repo_is_a_valid_plugin(self) -> None:
        # The positive control. Without it, every test below could pass for the wrong reason.
        self.assertEqual([], self._issues_after(lambda _: None))

    def test_missing_hook_registration_is_reported(self) -> None:
        issues = self._issues_after(lambda r: (r / "hooks" / "hooks.json").unlink())
        self.assertTrue(any("ONLY place the read-only guard" in i for i in issues), issues)

    def test_hook_that_does_not_use_the_plugin_root_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "hooks" / "hooks.json"
            path.write_text(
                path.read_text(encoding="utf-8").replace("${CLAUDE_PLUGIN_ROOT}", "$HOME/.claude"),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("CLAUDE_PLUGIN_ROOT" in i for i in issues), issues)

    def test_plugin_name_mismatch_is_reported(self) -> None:
        # The guard matches a NAMESPACED agent_type. Rename the plugin and it matches nobody.
        def mutate(repo: Path) -> None:
            path = repo / ".claude-plugin" / "plugin.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["name"] = "renamed-fleet"
            path.write_text(json.dumps(manifest), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("silently guards nothing" in i for i in issues), issues)

    def test_missing_author_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / ".claude-plugin" / "plugin.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            del manifest["author"]
            path.write_text(json.dumps(manifest), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("--strict" in i for i in issues), issues)

    def test_unguarded_readonly_bash_agent_is_reported(self) -> None:
        # Add a new read-only agent that holds Bash and forget to register it with the guard --
        # the exact way a future agent would arrive unguarded while every test stayed green.
        issues = self._issues_after(
            lambda r: (r / "agents" / "auditor.md").write_text(READONLY_BASH_AGENT, encoding="utf-8")
        )
        self.assertTrue(
            any("'read-only' is a promise, not a control" in i for i in issues), issues
        )

    def test_guarding_an_agent_that_does_not_exist_is_reported(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "scripts" / "readonly-guard.py"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    'GUARDED_AGENT_NAMES = frozenset({"code-reviewer"})',
                    'GUARDED_AGENT_NAMES = frozenset({"code-reviewer", "ghost"})',
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("'ghost'" in i and "not an agent" in i for i in issues), issues)

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


if __name__ == "__main__":
    unittest.main()
