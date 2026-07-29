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


REPO = Path(__file__).resolve().parents[1]


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

    def _issues_after(self, mutate) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            # tests/ stays in the copy: AGENTS.md names `tests/fixtures/`, and the guide drift
            # check resolves every multi-segment path it asserts.
            shutil.copytree(
                REPO, dst, ignore=shutil.ignore_patterns(".git", "__pycache__")
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
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
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


if __name__ == "__main__":
    unittest.main()
