from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import validate_fleet
from tests.support import REPO, repo_copy


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

    def test_unadopted_mcp_tool_is_reported(self) -> None:
        # The fixture uses GitHits' feedback tool: structurally real MCP authority, but an external
        # write that the fleet's evidence agents do not need. It must fail as a POLICY decision,
        # not be mislabeled as an unknown Claude Code tool.
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "unadopted-mcp-tool", check_inventory=False
        )
        feedback_issues = [issue for issue in issues if "feedback" in issue]
        self.assertTrue(any("not adopted by this fleet" in issue for issue in feedback_issues), issues)
        self.assertFalse(any("not a Claude Code tool" in issue for issue in feedback_issues), issues)

    def test_bare_skill_reference_without_preload_is_reported(self) -> None:
        # The fixture's agent says "work the `tuning` skill" with no skills: preload — an
        # instruction that cannot execute and errors nowhere, which is exactly how sde-fullstack's
        # `code-craft` reference shipped unreachable.
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "unreachable-bare-skill", check_inventory=False
        )
        self.assertTrue(any("unreachable authority" in issue and "tuning" in issue for issue in issues), issues)

    def test_perishable_token_outside_owner_is_reported(self) -> None:
        # The fixture's agent restates the complete upstream issue identifier while its skill uses
        # the same digits as an unrelated port. Only the platform-fact copy should be rejected.
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "perishable-token-copy", check_inventory=False
        )
        token_issues = [issue for issue in issues if "perishable platform token" in issue]
        self.assertEqual(1, len(token_issues), issues)
        self.assertIn("anthropics/claude-code#22345", token_issues[0])

    def test_missing_bundled_reference_fails(self) -> None:
        """The fixture links `./references/missing.md` on purpose. Before BUNDLE_REF_RE accepted the
        `./` prefix the link matched nothing at all, so a broken path raised no issue whatsoever --
        this test is what fails if that lookbehind regresses.
        """
        issues, _, _ = validate_fleet.validate_repo(
            FIXTURES / "missing-reference", check_inventory=False
        )
        self.assertTrue(any("references/missing.md" in issue for issue in issues))

    def test_dot_slash_and_bare_bundle_paths_are_the_same_reference(self) -> None:
        """Both direction checks compare against this set, so the two spellings must collapse or the
        orphan check would call a linked file unreachable.
        """
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "SKILL.md"
            skill.write_text(
                "See ./references/a.md and references/b.md.\n", encoding="utf-8"
            )
            self.assertEqual(
                {"references/a.md", "references/b.md"},
                validate_fleet.bundle_references(skill),
            )

    def test_bundle_reference_does_not_restart_inside_other_paths(self) -> None:
        """The optional `./` must not let matching restart inside a parent or dotted token."""
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "SKILL.md"
            invalid_paths = (
                "../references/parent.md",
                ".references/hidden.md",
                "foo.references/embedded.md",
                "https://example.test/references/remote.md",
            )
            for invalid_path in invalid_paths:
                with self.subTest(invalid_path=invalid_path):
                    skill.write_text(f"Read {invalid_path}.\n", encoding="utf-8")
                    self.assertEqual(set(), validate_fleet.bundle_references(skill))

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

    def test_malformed_frontmatter_is_rejected(self) -> None:
        """An unparseable line used to be skipped silently, so a typo'd key configured nothing and
        still validated.
        """
        self.assertIsNone(
            validate_fleet.parse_frontmatter(FIXTURES / "folded" / "malformed.md")
        )

    def test_duplicate_frontmatter_key_is_rejected(self) -> None:
        """YAML keeps the last duplicate, so the file would validate against a value its author did
        not mean to be live.
        """
        self.assertIsNone(
            validate_fleet.parse_frontmatter(FIXTURES / "folded" / "duplicate-key.md")
        )

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

    def test_parser_reads_yaml_block_sequence(self) -> None:
        # TOP_LEVEL_KEY_RE is anchored at column zero, so `  - item` lines under `skills:` never
        # matched it and `fields["skills"]` silently came back "" -- the root cause of P1-a.
        fields = self._parse(
            "---\nname: builder\nskills:\n  - backend-craft\n  - frontend-craft\nmodel: inherit\n---\n"
        )
        self.assertEqual("backend-craft, frontend-craft", fields["skills"])
        self.assertEqual("inherit", fields["model"])  # the key after the list is still parsed

    def test_parser_reads_block_sequence_with_interleaved_blanks_and_comments(self) -> None:
        # A blank line or `#` comment between `skills:` and the first `- item` used to leave the
        # list items stranded in the outer loop, which then returned None because `- item` lines
        # don't match TOP_LEVEL_KEY_RE.
        fields = self._parse(
            "---\nname: builder\nskills:\n  # note\n\n  - backend-craft\n  - frontend-craft\nmodel: inherit\n---\n"
        )
        self.assertIsNotNone(fields)
        self.assertEqual("backend-craft, frontend-craft", fields["skills"])
        self.assertEqual("inherit", fields["model"])

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
        # The full documented set must pass, or the allowlist is a false tripwire. "Full" is meant
        # literally: this asserts EVERY key in KNOWN_SKILL_FIELDS, because a typo'd allowlist entry
        # (`backgroud`) rejects the very field it was added to permit, and a test that exercised
        # only a hand-picked five would not notice.
        documented = sorted(validate_fleet.KNOWN_SKILL_FIELDS - {"name", "description"})
        extra = "".join(f"{key}: x\n" for key in documented)
        issues = self._skill_issues(
            "craft", "name: craft\ndescription: Use when building.\n" + extra
        )
        self.assertEqual([], [i for i in issues if "frontmatter key" in i])
        self.assertIn("background", documented)  # the field added 2026-07-24, now covered

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

    def test_scoped_bash_grant_is_reported_as_a_false_restriction(self) -> None:
        # The Agent(type) branch above had a test; this sibling branch — the one guarding the
        # `Bash(git diff:*)` footgun the read-only guard exists because of — had none, so a
        # refactor could have disarmed it silently.
        body = VALID_AGENT.replace("tools: Read", "tools: Read, Bash(git diff:*)")
        issues = self._agent_issues(("builder.md", body))
        self.assertTrue(any("SILENTLY IGNORES" in i for i in issues), issues)

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

    def test_adopted_exact_mcp_tool_is_accepted(self) -> None:
        body = VALID_AGENT.replace(
            "tools: Read",
            "tools: Read, ToolSearch, mcp__plugin_githits_githits__pkg_info",
        )
        issues = self._agent_issues(("builder.md", body))
        self.assertFalse(any("tool" in i.lower() and "authority" in i.lower() for i in issues), issues)

    def test_server_wide_mcp_grant_is_rejected_as_drifting_authority(self) -> None:
        # A server wildcard silently acquires every tool added in a future MCP release. GitHits
        # currently exposes a feedback write beside its read-only evidence tools, so broad grant
        # syntax defeats the fleet's "every tool is deliberate authority" policy.
        body = VALID_AGENT.replace(
            "tools: Read",
            "tools: Read, mcp__plugin_githits_githits__*",
        )
        issues = self._agent_issues(("builder.md", body))
        self.assertTrue(any("server-wide MCP grant" in i and "future tools" in i for i in issues), issues)

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

    # --- skills: list validation (P1-a): `skills` passed KNOWN_AGENT_FIELDS' key-namespace check,
    # but nothing ever validated its VALUES -- a typo'd or dropped entry, or a skill that cannot be
    # preloaded at all, passed silently. ---

    def _agent_issues_with_skills(
        self, agent_file: tuple[str, str], skill_files: dict[str, str]
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            agents = Path(tmp) / "agents"
            agents.mkdir()
            filename, body = agent_file
            (agents / filename).write_text(body, encoding="utf-8")
            for skill_name, skill_body in skill_files.items():
                skill_dir = Path(tmp) / "skills" / skill_name
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(skill_body, encoding="utf-8")
            issues, _ = validate_fleet.validate_agents(Path(tmp))
            return issues

    SKILL_BODY = (
        "---\nname: {name}\ndescription: Use when doing the thing.\n---\n\n# Skill\n"
    )
    DISABLED_SKILL_BODY = (
        "---\nname: {name}\ndescription: Use when doing the thing.\n"
        "disable-model-invocation: true\n---\n\n# Skill\n"
    )

    def test_skills_entry_that_does_not_resolve_is_reported(self) -> None:
        body = VALID_AGENT.replace("model: inherit", "skills:\n  - ghost-skill\nmodel: inherit")
        issues = self._agent_issues_with_skills(("builder.md", body), {})
        self.assertTrue(
            any("'ghost-skill'" in i and "does not resolve" in i for i in issues), issues
        )

    def test_skills_entry_naming_a_model_invocation_disabled_skill_is_reported(self) -> None:
        # A skill with `disable-model-invocation: true` cannot be preloaded ("preloading draws from
        # the same set of skills Claude can invoke") -- listing one under `skills:` is a silent no-op.
        body = VALID_AGENT.replace("model: inherit", "skills:\n  - disabled\nmodel: inherit")
        issues = self._agent_issues_with_skills(
            ("builder.md", body), {"disabled": self.DISABLED_SKILL_BODY.format(name="disabled")}
        )
        self.assertTrue(
            any("'disabled'" in i and "disable-model-invocation" in i for i in issues), issues
        )

    def test_skills_entry_that_resolves_to_a_preloadable_skill_is_accepted(self) -> None:
        body = VALID_AGENT.replace("model: inherit", "skills:\n  - ok\nmodel: inherit")
        issues = self._agent_issues_with_skills(
            ("builder.md", body), {"ok": self.SKILL_BODY.format(name="ok")}
        )
        self.assertEqual([], [i for i in issues if "skills:" in i], issues)


def _add_guarded_name(repo: Path, name: str) -> None:
    """Add one name to a repo COPY's GUARDED_AGENT_NAMES, whatever formatting the literal uses.

    The mutation tests below used to string-match the whole single-line frozenset, so extending the
    real roster broke them by silently mutating nothing — a green test that no longer tested
    anything. Anchoring on the first member instead survives reformatting.
    """
    path = repo / "scripts" / "readonly-guard.py"
    source = path.read_text(encoding="utf-8")
    anchor = '"code-reviewer"'
    assert anchor in source, "GUARDED_AGENT_NAMES no longer contains the expected anchor"
    path.write_text(source.replace(anchor, f'{anchor}, "{name}"', 1), encoding="utf-8")

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

    def _issues_after(self, mutate, *, check_adapters: bool = False) -> list[str]:
        with repo_copy() as dst:
            mutate(dst)
            # Default False: each test here checks ONE deliberate non-adapter breakage, and the
            # adapter byte-compare they would otherwise all repeat is 59% of a validation run.
            # A test that DOES mutate adapters must pass True — forgetting is loud (its
            # asserted issue never appears), never a silent pass. AdapterCheckTierTests pins
            # both sides of the flag.
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=check_adapters
            )
            return issues

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

    def test_learning_closeout_cannot_silently_leave_an_agent_packet(self) -> None:
        # Use a non-preloaded evidence role: its lightweight handoff is mandatory even though the
        # full improvement loop is intentionally absent from its context.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            text = path.read_text(encoding="utf-8")
            marker = validate_fleet.LEARNING_INTAKE_PACKET_SLOT
            assert marker in text, "positive control: researcher must declare the Learning slot"
            path.write_text(
                text.replace(marker, "- **Observation**:", 1),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "researcher.md" in issue
                and "Learning" in issue
                and "disappear" in issue
                for issue in issues
            ),
            issues,
        )

    def test_learning_closeout_wording_cannot_keep_the_marker_but_lose_durable_intake(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            text = path.read_text(encoding="utf-8")
            old = "receiving coordinator verifies and triages them"
            assert old in text, "positive control: researcher must declare durable intake"
            path.write_text(
                text.replace(old, "caller may mention them later", 1),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "researcher.md" in issue
                and "Learning" in issue
                and "drifted" in issue
                for issue in issues
            ),
            issues,
        )

    def test_non_preloaded_agent_cannot_claim_lifecycle_owner_closeout(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            text = path.read_text(encoding="utf-8")
            intake = validate_fleet.LEARNING_INTAKE_PACKET_SLOT
            assert intake in text, "positive control: researcher must use intake-only Learning"
            path.write_text(
                text.replace(
                    intake,
                    validate_fleet.LEARNING_LIFECYCLE_OWNER_PACKET_SLOT,
                    1,
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "researcher.md" in issue
                and "intake" in issue.lower()
                and "lifecycle-owner" in issue.lower()
                for issue in issues
            ),
            issues,
        )

    def test_each_lifecycle_owner_cannot_fall_back_to_intake_closeout(self) -> None:
        lifecycle_owners = {
            "prompt-engineer",
            "sde-fullstack",
            "verification-engineer",
        }
        self.assertEqual(
            frozenset(lifecycle_owners),
            validate_fleet.SELF_IMPROVE_LOOP_PRELOAD_AGENTS,
        )
        for name in sorted(lifecycle_owners):
            with self.subTest(name=name):
                def mutate(repo: Path) -> None:
                    path = repo / "agents" / f"{name}.md"
                    text = path.read_text(encoding="utf-8")
                    lifecycle = validate_fleet.LEARNING_LIFECYCLE_OWNER_PACKET_SLOT
                    assert lifecycle in text, (
                        f"positive control: {name} must use lifecycle-owner Learning"
                    )
                    path.write_text(
                        text.replace(
                            lifecycle,
                            validate_fleet.LEARNING_INTAKE_PACKET_SLOT,
                            1,
                        ),
                        encoding="utf-8",
                    )

                issues = self._issues_after(mutate)
                self.assertTrue(
                    any(
                        f"{name}.md" in issue
                        and "lifecycle-owner" in issue.lower()
                        and "intake" in issue.lower()
                        for issue in issues
                    ),
                    issues,
                )

    def test_self_improve_loop_preload_roster_cannot_silently_drift(self) -> None:
        # Exercise both halves of "only these three": dropping an owner loses full disposition;
        # adding an evidence-only role spends context and can imply authority that role lacks.
        def drop_required_preload(repo: Path) -> None:
            path = repo / "agents" / "prompt-engineer.md"
            text = path.read_text(encoding="utf-8")
            anchor = "skills:\n  - self-improve-loop\n"
            assert anchor in text, "positive control: prompt-engineer must preload the loop"
            path.write_text(text.replace(anchor, "", 1), encoding="utf-8")

        def add_unapproved_preload(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            text = path.read_text(encoding="utf-8")
            anchor = "model: inherit\n"
            assert anchor in text, "positive control: researcher must declare its model"
            path.write_text(
                text.replace(
                    anchor,
                    "skills:\n  - self-improve-loop\n" + anchor,
                    1,
                ),
                encoding="utf-8",
            )

        for label, mutate in (
            ("missing required preload", drop_required_preload),
            ("unexpected preload", add_unapproved_preload),
        ):
            with self.subTest(label=label):
                issues = self._issues_after(mutate)
                self.assertTrue(
                    any("self-improve-loop preload roster drifted" in issue for issue in issues),
                    issues,
                )

    def test_stale_generated_platform_adapter_is_reported(self) -> None:
        # The authored Claude definition is the source. A direct edit to a generated Codex copy
        # otherwise creates host-dependent behavior with no load error and no obvious review clue.
        def mutate(repo: Path) -> None:
            path = repo / ".codex" / "agents" / "code-reviewer.toml"
            path.write_text(
                path.read_text(encoding="utf-8") + "\n# stale local edit\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate, check_adapters=True)
        self.assertTrue(
            any(
                "code-reviewer.toml" in issue
                and "generated platform adapter drifted" in issue
                for issue in issues
            ),
            issues,
        )

    def test_codex_interface_contract_cannot_silently_disappear(self) -> None:
        # Codex accepts the nested plugin only when its presentation contract is complete. A
        # malformed marketplace card otherwise fails at install time outside this repo's CI.
        def mutate(repo: Path) -> None:
            path = (
                repo
                / "plugins"
                / "sde-agents"
                / ".codex-plugin"
                / "plugin.json"
            )
            manifest = json.loads(path.read_text(encoding="utf-8"))
            del manifest["interface"]
            path.write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate, check_adapters=True)
        self.assertTrue(
            any(
                "Codex manifest interface" in issue
                and "required presentation fields" in issue
                for issue in issues
            ),
            issues,
        )

    def test_codex_marketplace_policy_cannot_silently_disappear(self) -> None:
        # The repo-local marketplace is the Codex install entry point, not decorative metadata.
        # Its required policy and category must fail here instead of during a user's installation.
        def mutate(repo: Path) -> None:
            path = repo / ".agents" / "plugins" / "marketplace.json"
            marketplace = json.loads(path.read_text(encoding="utf-8"))
            del marketplace["plugins"][0]["policy"]
            path.write_text(
                json.dumps(marketplace, indent=2) + "\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate, check_adapters=True)
        self.assertTrue(
            any(
                "Codex marketplace entry requires installation policy" in issue
                for issue in issues
            ),
            issues,
        )

    def test_evidence_agent_cannot_silently_lose_its_mcp_authority(self) -> None:
        # Both evidence agents used to promise Context7/GitHits while their tools allowlist removed
        # every MCP tool. Mutation is the right test because the invariant binds a real role's
        # method to its real frontmatter rather than defining a synthetic "researcher" fixture.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "  - mcp__plugin_githits_githits__pkg_info\n", ""
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "evidence role 'researcher' is missing required tools" in issue
                and "pkg_info" in issue
                for issue in issues
            ),
            issues,
        )

    def test_investigation_roles_cannot_collapse_the_local_external_boundary(self) -> None:
        mutations = (
            ("researcher", "  - Read\n"),
            ("repository-investigator", "  - WebFetch\n"),
            ("application-security-auditor", "  - WebSearch\n"),
        )
        for name, tool_line in mutations:
            with self.subTest(agent=name):

                def mutate(repo: Path) -> None:
                    path = repo / "agents" / f"{name}.md"
                    text = path.read_text(encoding="utf-8")
                    path.write_text(
                        text.replace("tools:\n", "tools:\n" + tool_line, 1),
                        encoding="utf-8",
                    )

                issues = self._issues_after(mutate)
                self.assertTrue(
                    any(
                        f"trust-separated role '{name}' holds forbidden tools" in issue
                        for issue in issues
                    ),
                    issues,
                )

    def test_required_gpt_5_6_sol_baseline_cannot_silently_disappear(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "evals" / "conformance" / "hosts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["lanes"] = [
                lane for lane in document["lanes"] if lane.get("model") != "gpt-5.6-sol"
            ]
            path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(
            any("exactly one explicit gpt-5.6-sol baseline lane" in issue for issue in issues),
            issues,
        )

    def test_runtime_control_consumers_cannot_silently_lose_their_wiring(self) -> None:
        wiring = (
            ("agents/verification-engineer.md", "scripts/verification_sandbox.py"),
            ("skills/sre-tool/SKILL.md", "scripts/run_state.py"),
            ("agents/homelab-platform.md", "scripts/effect_broker.py"),
        )
        for consumer_relative, script_relative in wiring:
            with self.subTest(consumer=consumer_relative):

                def mutate(repo: Path) -> None:
                    path = repo / consumer_relative
                    reference = f"${{CLAUDE_PLUGIN_ROOT}}/{script_relative}"
                    path.write_text(
                        path.read_text(encoding="utf-8").replace(reference, script_relative),
                        encoding="utf-8",
                    )

                issues = self._issues_after(mutate)
                self.assertTrue(
                    any(
                        consumer_relative in issue
                        and "silently stop enforcing" in issue
                        for issue in issues
                    ),
                    issues,
                )

    def test_runtime_control_cannot_silently_drop_typed_evidence(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "scripts" / "effect_broker.py"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "evidence_envelope", "untyped_result"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "scripts/effect_broker.py" in issue
                and "typed evidence contract" in issue
                for issue in issues
            ),
            issues,
        )

    def test_dangling_namespace_reference_is_reported(self) -> None:
        # The corpus carries hundreds of `sde-agents:<name>` cross-references and nothing at
        # runtime resolves one: a renamed or deleted member leaves pointers that pass every gate
        # while routing quietly degrades. Mutation, not a fixture, because the invariant is about
        # the real repo's densely linked graph.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\nEscalate fan-out design to `sde-agents:ghost-skill`.\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(any("sde-agents:ghost-skill" in i for i in issues), issues)

    def test_malformed_namespace_reference_is_reported_as_the_complete_token(self) -> None:
        # A prefix-only regex used to accept code-reviewer_v2 as the live code-reviewer target and
        # skipped uppercase targets entirely. Each mutation introduces one malformed reference.
        for target in ("code-reviewer_v2", "Code-Reviewer", "code--reviewer"):
            with self.subTest(target=target):

                def mutate(repo: Path) -> None:
                    path = repo / "agents" / "researcher.md"
                    path.write_text(
                        path.read_text(encoding="utf-8")
                        + f"\nEscalate to `sde-agents:{target}`.\n",
                        encoding="utf-8",
                    )

                issues = self._issues_after(mutate)
                self.assertTrue(
                    any(
                        f"sde-agents:{target}" in issue
                        and "malformed namespaced reference" in issue
                        for issue in issues
                    ),
                    issues,
                )

    def test_slash_command_reference_must_target_a_skill(self) -> None:
        # code-reviewer is a real fleet member, but it is an agent and therefore cannot resolve
        # through slash-command syntax. Union membership must not certify the invocation.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\nRun `/sde-agents:code-reviewer` before continuing.\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "/sde-agents:code-reviewer" in issue
                and "slash-command reference" in issue
                and "must target a skill" in issue
                for issue in issues
            ),
            issues,
        )

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

    def test_guarded_agent_missing_from_the_hook_string_is_reported(self) -> None:
        # The hook filters on the agent name before it ever runs the guard, so the roster lives in
        # TWO places. Simulate adding another guarded agent to the guard alone: the hook's
        # fast-path would exit 0 for it, leaving it unguarded while every file claims otherwise.
        # `sde-fullstack` is a real agent, so this isolates the hook-sync rule from the
        # does-this-agent-exist rule above.
        def mutate(repo: Path) -> None:
            _add_guarded_name(repo, "sde-fullstack")

        issues = self._issues_after(mutate)
        self.assertTrue(any("never names 'sde-fullstack'" in i for i in issues), issues)

    def test_name_present_in_only_one_hook_roster_is_reported(self) -> None:
        # REGRESSION (review-reported, reproduced): the hook holds TWO rosters — the `case`
        # fast-path that decides whether the guard runs at all, and the no-interpreter fallback
        # that fails closed. Searching the whole command string passed when a name sat in one
        # block and was missing from the other, which is the silent-disarm this rule exists to
        # prevent. Each direction is pinned separately.
        def drop_from_fast_path(repo: Path) -> None:
            path = repo / "hooks" / "hooks.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            hook = doc["hooks"]["PreToolUse"][0]["hooks"][0]
            hook["command"] = hook["command"].replace("|*principal-engineer*", "", 1)
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

        issues = self._issues_after(drop_from_fast_path)
        self.assertTrue(
            any("fast-path filter" in i and "principal-engineer" in i for i in issues), issues
        )

        def drop_from_fallback(repo: Path) -> None:
            path = repo / "hooks" / "hooks.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            hook = doc["hooks"]["PreToolUse"][0]["hooks"][0]
            command = hook["command"]
            # Remove only the fallback's agent_type patterns for this agent, leaving the fast-path.
            for form in ("sde-agents:principal-engineer", "principal-engineer"):
                command = command.replace(f"""|*'"agent_type":"{form}"'*""", "")
                command = command.replace(f"""|*'"agent_type": "{form}"'*""", "")
            hook["command"] = command
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

        issues = self._issues_after(drop_from_fallback)
        self.assertTrue(
            any("no-interpreter fallback" in i and "principal-engineer" in i for i in issues), issues
        )

    def test_unrecognized_hook_shape_fails_rather_than_passing(self) -> None:
        # If the hook is ever restructured away from two `case` blocks, the roster cross-check
        # cannot verify it — and must say so instead of quietly reporting no issues.
        def mutate(repo: Path) -> None:
            path = repo / "hooks" / "hooks.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            hook = doc["hooks"]["PreToolUse"][0]["hooks"][0]
            hook["command"] = hook["command"].replace('case "$IN" in', "if false; then", 1)
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(any("does not recognize" in i for i in issues), issues)

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
            _add_guarded_name(repo, "ghost")

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

    # --- orphaned reference files (P2-b): validate_bundle_references only ever checks "does the
    # linked file exist?" -- never the reverse. A references/*.md file with no routing-table row is
    # silently unreachable: validator green, tests green, probe green (it only exercises linked rows).

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

    # --- AGENTS.md drift tripwires: the guide paraphrases the validator and the layout, and prose
    # has no runtime -- every failure mode below is silent without these. ---

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


class RoutingClusterTests(unittest.TestCase):
    """Schema integrity for evals/routing/*.json (EVAL-001).

    The scorer grades a positive on its own expect_fires but reports the CLUSTER's fire rate — so
    a positive naming a component outside the declared members can pass while the reported rate
    reads zero (observed live: pos-ci-actions-harden accepting code-reviewer). And both target
    lists match components BY NAME, so a typo'd member or target forbids or expects nothing and
    passes vacuously. The runner has no error to raise at grade time; only a validator sees it.
    """

    BASE = {"cluster": "demo", "members": ["craft", "builder"], "cases": []}

    def _issues_with_cluster(self, doc) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(FIXTURES / "valid", dst)
            routing = dst / "evals" / "routing"
            routing.mkdir(parents=True)
            payload = doc if isinstance(doc, str) else json.dumps(doc)
            (routing / "cluster.json").write_text(payload, encoding="utf-8")
            issues, _, _ = validate_fleet.validate_repo(dst)
            return issues

    def test_positive_target_outside_members_is_reported(self) -> None:
        issues, _, _ = validate_fleet.validate_repo(FIXTURES / "routing-nonmember-target")
        self.assertTrue(any("outside the cluster's members" in i for i in issues), issues)

    def test_well_formed_cluster_passes(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "pos-a", "prompt": "p", "polarity": "positive", "expect_fires": ["craft"]},
            {"id": "neg-a", "prompt": "p", "polarity": "negative",
             "expect_not_fires": ["craft", "builder"]},
            {"id": "neg-default", "prompt": "p", "polarity": "negative"},
        ])
        self.assertEqual([], self._issues_with_cluster(doc))

    def test_typoed_polarity_is_reported(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "bad", "prompt": "p", "polarity": "positve", "expect_fires": ["craft"]},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("polarity" in i and "positive or negative" in i for i in issues), issues)

    def test_empty_positive_expectation_is_reported(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "bad", "prompt": "p", "polarity": "positive", "expect_fires": []},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("expect_fires" in i and "non-empty list" in i for i in issues), issues)

    def test_empty_explicit_negative_forbidden_set_is_reported(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "bad", "prompt": "p", "polarity": "negative", "expect_not_fires": []},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("expect_not_fires" in i and "non-empty list" in i for i in issues), issues)

    def test_expectation_fields_reject_wrong_types(self) -> None:
        cases = [
            {"id": "bad-pos", "prompt": "p", "polarity": "positive", "expect_fires": "craft"},
            {"id": "bad-neg", "prompt": "p", "polarity": "negative",
             "expect_not_fires": "craft"},
        ]
        issues = self._issues_with_cluster(dict(self.BASE, cases=cases))
        self.assertTrue(any("bad-pos" in i and "expect_fires" in i for i in issues), issues)
        self.assertTrue(any("bad-neg" in i and "expect_not_fires" in i for i in issues), issues)

    def test_required_case_fields_are_reported(self) -> None:
        cases = [
            {"prompt": "p", "polarity": "negative"},
            {"id": "missing-prompt", "polarity": "negative"},
            {"id": "missing-polarity", "prompt": "p"},
            {"id": "missing-positive-targets", "prompt": "p", "polarity": "positive"},
        ]
        issues = self._issues_with_cluster(dict(self.BASE, cases=cases))
        self.assertTrue(any("non-empty 'id'" in i for i in issues), issues)
        self.assertTrue(any("missing-prompt" in i and "non-empty 'prompt'" in i for i in issues), issues)
        self.assertTrue(any("missing-polarity" in i and "polarity" in i for i in issues), issues)
        self.assertTrue(
            any("missing-positive-targets" in i and "expect_fires" in i for i in issues),
            issues,
        )

    def test_cases_must_be_a_non_empty_list(self) -> None:
        for cases in (None, {}, []):
            with self.subTest(cases=cases):
                issues = self._issues_with_cluster(dict(self.BASE, cases=cases))
                self.assertTrue(any("non-empty 'cases' list" in i for i in issues), issues)

    def test_cluster_name_is_required(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "neg-a", "prompt": "p", "polarity": "negative"},
        ])
        del doc["cluster"]
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("non-empty 'cluster' string" in i for i in issues), issues)

    def test_member_names_reject_wrong_types(self) -> None:
        doc = dict(self.BASE, members=["craft", {"not": "a name"}], cases=[
            {"id": "pos-a", "prompt": "p", "polarity": "positive", "expect_fires": ["craft"]},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("member #2" in i and "component name" in i for i in issues), issues)

    def test_each_case_must_be_an_object(self) -> None:
        issues = self._issues_with_cluster(dict(self.BASE, cases=["not-an-object"]))
        self.assertTrue(any("case #1 is not an object" in i for i in issues), issues)

    def test_unresolvable_member_is_reported(self) -> None:
        issues = self._issues_with_cluster(dict(self.BASE, members=["craft", "no-such-component"]))
        self.assertTrue(any("not a fleet component" in i for i in issues), issues)

    def test_duplicate_case_ids_are_reported(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "pos-a", "prompt": "p", "polarity": "positive", "expect_fires": ["craft"]},
            {"id": "pos-a", "prompt": "q", "polarity": "positive", "expect_fires": ["craft"]},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("duplicate case id" in i for i in issues), issues)

    def test_nonmember_forbidden_target_is_reported(self) -> None:
        doc = dict(self.BASE, cases=[
            {"id": "neg-a", "prompt": "p", "polarity": "negative",
             "expect_not_fires": ["no-such-component"]},
        ])
        issues = self._issues_with_cluster(doc)
        self.assertTrue(any("forbids" in i for i in issues), issues)

    def test_unparseable_cluster_file_is_reported(self) -> None:
        issues = self._issues_with_cluster("not json {")
        self.assertTrue(any("unreadable cluster file" in i for i in issues), issues)

    def test_reintroducing_the_observed_inconsistency_is_reported(self) -> None:
        # The exact defect EVAL-001 was opened on, proven against a COPY of the real repository
        # rather than a synthetic shape that could drift away from the actual cluster file.
        with repo_copy() as dst:
            path = dst / "evals" / "routing" / "craft-vs-fullstack.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            case = next(c for c in doc["cases"] if c["id"] == "pos-ci-actions-harden")
            case["expect_fires"].append("code-reviewer")
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            issues, _, _ = validate_fleet.validate_repo(dst, check_inventory=False)
        self.assertTrue(
            any("pos-ci-actions-harden" in i and "outside the cluster's members" in i
                for i in issues),
            issues,
        )


class WorkflowEvidenceEnumTests(unittest.TestCase):
    def test_workflow_evidence_enum_drift_is_reported(self) -> None:
        # Proven against a COPY of the real repository so the test breaks the actual shipped
        # workflow, not a synthetic shape that could drift away from it.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_text(
                wf.read_text(encoding="utf-8").replace(
                    "const EVIDENCE = ['verified', 'sourced', 'unverified']",
                    "const EVIDENCE = ['verified', 'cited', 'unverified']",
                ),
                encoding="utf-8",
            )
            issues, _, _ = validate_fleet.validate_repo(dst, check_inventory=False)
        self.assertTrue(any("canonical" in i and "deep-review" in i for i in issues), issues)

    def test_workflow_evidence_enum_current_tree_is_clean(self) -> None:
        issues = validate_fleet.validate_workflow_evidence_enums(REPO)
        self.assertEqual(issues, [])


class WorkflowLineEndingTests(unittest.TestCase):
    def test_crlf_workflow_is_reported(self) -> None:
        # Mutation against a COPY of the real shipped workflow: re-encode it exactly the way
        # Windows checkout translation did on installed 1.6.10 (#75) — the failure the rule
        # exists to catch — rather than a synthetic file that could drift from the real shape.
        with repo_copy() as dst:
            wf = dst / "workflows" / "deep-review.js"
            wf.write_bytes(wf.read_bytes().replace(b"\n", b"\r\n"))
            issues, _, _ = validate_fleet.validate_repo(dst, check_inventory=False)
        self.assertTrue(
            any("carriage returns" in i and "deep-review" in i for i in issues), issues
        )

    def test_missing_gitattributes_js_eol_rule_is_reported(self) -> None:
        # Removing the `*.js text eol=lf` rule from .gitattributes is a configuration
        # regression: any subsequent fresh Windows checkout would translate workflows to CRLF
        # and the Workflow tool would refuse to run them. The byte check alone cannot catch
        # this because the file on disk stays LF until the next checkout. Verify that the
        # validator fires when only the rule is removed (bytes left intact).
        with repo_copy() as dst:
            ga = dst / ".gitattributes"
            ga.write_text(
                "\n".join(
                    line
                    for line in ga.read_text(encoding="utf-8").splitlines()
                    if "*.js text eol=lf" not in line
                )
                + "\n",
                encoding="utf-8",
            )
            issues = validate_fleet.validate_workflow_line_endings(dst)
        self.assertTrue(
            any("missing" in i and "*.js text eol=lf" in i for i in issues), issues
        )

    def test_missing_gitattributes_file_is_reported(self) -> None:
        # Deleting the whole file is the same configuration regression as deleting its JS
        # rule. An existence guard must not turn the more severe mutation into a false green.
        with repo_copy() as dst:
            (dst / ".gitattributes").unlink()
            issues = validate_fleet.validate_workflow_line_endings(dst)
        self.assertTrue(
            any("missing" in i and "*.js text eol=lf" in i for i in issues), issues
        )

    def test_workflow_line_endings_current_tree_is_clean(self) -> None:
        issues = validate_fleet.validate_workflow_line_endings(REPO)
        self.assertEqual(issues, [])


class WorkflowHostBoundaryTests(unittest.TestCase):
    def test_adapter_referencing_workflow_is_reported(self) -> None:
        with repo_copy() as dst:
            adapter = next(iter(sorted((dst / ".github" / "agents").glob("*.md"))))
            adapter.write_text(
                adapter.read_text(encoding="utf-8")
                + "\nRun /sde-agents:deep-review before merging.\n",
                encoding="utf-8",
            )
            issues, _, _ = validate_fleet.validate_repo(dst, check_inventory=False)
        self.assertTrue(any("no workflow runtime" in i for i in issues), issues)

    def test_generated_script_resource_referencing_workflow_is_reported(self) -> None:
        # Generated skill resources are not limited to the prose/config suffixes originally
        # scanned here. A shell asset carrying the same unusable instruction must not bypass
        # the host boundary merely because its extension was absent from a validator tuple.
        with repo_copy() as dst:
            resource = dst / "platforms" / "copilot" / "skills" / "probe" / "scripts" / "run.sh"
            resource.parent.mkdir(parents=True)
            resource.write_text("Run /sde-agents:deep-review before merging.\n", encoding="utf-8")
            issues = validate_fleet.validate_workflow_host_boundary(dst)
        self.assertTrue(any("no workflow runtime" in i and "run.sh" in i for i in issues), issues)

    def test_untracked_python_cache_is_not_treated_as_a_shipped_workflow_reference(self) -> None:
        # The adapter generator already excludes runtime bytecode from distributable outputs.
        # A local import must not make the host-boundary scan certify a different file set.
        with repo_copy() as dst:
            byproduct = (
                dst / "platforms" / "copilot" / "skills" / "probe" / "__pycache__" / "probe.pyc"
            )
            byproduct.parent.mkdir(parents=True)
            byproduct.write_bytes(b"runtime cache /sde-agents:deep-review")
            issues = validate_fleet.validate_workflow_host_boundary(dst)
        self.assertEqual([], issues)

    def test_workflow_host_boundary_current_tree_is_clean(self) -> None:
        issues = validate_fleet.validate_workflow_host_boundary(REPO)
        self.assertEqual(issues, [])


class LearningLedgerWiringTests(unittest.TestCase):
    def test_current_store_and_transactional_ignores_are_validated(self) -> None:
        self.assertEqual([], validate_fleet.validate_learning_ledger(REPO))

    def test_tracked_candidate_corruption_fails_the_ordinary_validator(self) -> None:
        with repo_copy() as dst:
            candidate = next((dst / "learning" / "candidates").glob("lc_*.json"))
            candidate.write_text("{}\n", encoding="utf-8")
            issues = validate_fleet.validate_learning_ledger(dst)
        self.assertTrue(any("ledger validation failed" in issue for issue in issues), issues)

    def test_transactional_ignore_drift_is_reported(self) -> None:
        with repo_copy() as dst:
            ignore = dst / ".gitignore"
            ignore.write_text(
                ignore.read_text(encoding="utf-8").replace(
                    "learning/candidates/.learning-ledger.lock\n", ""
                ),
                encoding="utf-8",
            )
            issues = validate_fleet.validate_learning_ledger(dst)
        self.assertTrue(any(".learning-ledger.lock" in issue for issue in issues), issues)


class AdapterCheckTierTests(unittest.TestCase):
    """The T0/T1 tier boundary for adapter byte-drift.

    check_adapters=False exists so the wiring mutation tests stop re-generating and
    byte-comparing every host adapter to check one unrelated breakage. These two tests pin the
    flag's semantics: True still reports drift (so retiring the recipe's separate
    `generate --check` step loses nothing), and False genuinely skips it (so the speedup is
    real, and a future adapter test that forgets to pass True fails loudly — its expected issue
    never appears — instead of passing vacuously)."""

    def _drift_adapter(self, dst: Path) -> None:
        adapter = sorted((dst / ".github" / "agents").glob("*.md"))[0]
        adapter.write_text(
            adapter.read_text(encoding="utf-8") + "\nhand edit\n", encoding="utf-8"
        )

    def test_flag_on_reports_hand_edited_adapter(self) -> None:
        with repo_copy() as dst:
            self._drift_adapter(dst)
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=True
            )
        self.assertTrue(issues, "hand-edited adapter must be reported when the check runs")

    def test_flag_off_skips_only_the_adapter_check(self) -> None:
        with repo_copy() as dst:
            self._drift_adapter(dst)
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
        self.assertEqual(
            [],
            issues,
            "the only defect is adapter drift; skipping the adapter check must leave a clean "
            "report",
        )


if __name__ == "__main__":
    unittest.main()
