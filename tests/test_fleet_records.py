"""The shared collector's records, and the branches that keep an unknown from reading as a zero.

Every guard-parse failure path here is exercised deliberately: an untested defensive branch reads
as enforcement while enforcing nothing, and passes every existing check because no check knows it
is there.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import fleet_records
from tests.support import REPO


PLUGIN = json.loads(
    (REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
)["name"]


def _tree(guard_source: str | None) -> TemporaryDirectory:
    """A minimal tree carrying one agent, one skill, and an optional guard module."""
    handle = TemporaryDirectory()
    root = Path(handle.name)
    (root / "agents").mkdir()
    (root / "skills" / "demo-skill").mkdir(parents=True)
    (root / "agents" / "demo-agent.md").write_text(
        "---\n"
        "name: demo-agent\n"
        f"description: Routes to {PLUGIN}:demo-skill when asked.\n"
        "tools: Read, Grep\n"
        "skills:\n"
        "  - demo-skill\n"
        "---\n\n"
        f"Body mentions /{PLUGIN}:demo-skill once.\n",
        encoding="utf-8",
    )
    (root / "skills" / "demo-skill" / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: A demo skill.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    if guard_source is not None:
        (root / "scripts").mkdir()
        (root / "scripts" / "readonly-guard.py").write_text(guard_source, encoding="utf-8")
    return handle


class GuardCoverageTests(unittest.TestCase):
    def test_roster_is_read_without_executing_the_inspected_tree(self):
        """A guard module whose import-time side effect would be fatal still parses.

        The collector must treat an inspected tree as data. If it imported instead of parsing,
        this module would raise on load and the test would error rather than pass.
        """
        handle = _tree(
            "raise SystemExit('this module must never be executed by the collector')\n"
            'GUARDED_AGENT_NAMES = frozenset({"code-reviewer", "principal-engineer"})\n'
        )
        with handle:
            names = fleet_records.parse_guarded_agents(Path(handle.name))
        self.assertEqual(names, frozenset({"code-reviewer", "principal-engineer"}))

    def test_missing_guard_is_unknown_not_empty(self):
        """None and frozenset() are opposite facts; a report that conflates them would state
        that nothing is guarded on the strength of a file it never opened."""
        handle = _tree(None)
        with handle:
            self.assertIsNone(fleet_records.parse_guarded_agents(Path(handle.name)))

    def test_unparseable_guard_is_unknown_not_empty(self):
        handle = _tree("GUARDED_AGENT_NAMES = frozenset({  # truncated\n")
        with handle:
            self.assertIsNone(fleet_records.parse_guarded_agents(Path(handle.name)))

    def test_renamed_constant_is_unknown_not_empty(self):
        """A rename upstream must surface as unknown rather than as an empty roster."""
        handle = _tree('GUARDED_AGENTS_V2 = frozenset({"code-reviewer"})\n')
        with handle:
            self.assertIsNone(fleet_records.parse_guarded_agents(Path(handle.name)))

    def test_non_literal_roster_is_unknown_not_empty(self):
        """A computed roster cannot be read without running it, so it is unknown by construction."""
        handle = _tree("GUARDED_AGENT_NAMES = frozenset(compute_roster())\n")
        with handle:
            self.assertIsNone(fleet_records.parse_guarded_agents(Path(handle.name)))

    def test_the_last_module_level_assignment_is_the_effective_one(self):
        """Python keeps the last binding; taking the first reported a roster the live guard never
        uses -- a false host-authority claim from a file read correctly but interpreted wrongly."""
        handle = _tree(
            'GUARDED_AGENT_NAMES = frozenset({"everything"})\n'
            'GUARDED_AGENT_NAMES = frozenset({"code-reviewer"})\n'
        )
        with handle:
            self.assertEqual(
                fleet_records.parse_guarded_agents(Path(handle.name)),
                frozenset({"code-reviewer"}),
            )

    def test_a_nested_assignment_is_not_the_module_roster(self):
        handle = _tree(
            "def decoy():\n    GUARDED_AGENT_NAMES = frozenset({'everything'})\n"
            'GUARDED_AGENT_NAMES = frozenset({"code-reviewer"})\n'
        )
        with handle:
            self.assertEqual(
                fleet_records.parse_guarded_agents(Path(handle.name)),
                frozenset({"code-reviewer"}),
            )

    def test_only_a_nested_assignment_is_unknown(self):
        """No module-level binding means the live guard has no roster here; that is unknown, not
        whatever a function body happens to name."""
        handle = _tree("def decoy():\n    GUARDED_AGENT_NAMES = frozenset({'everything'})\n")
        with handle:
            self.assertIsNone(fleet_records.parse_guarded_agents(Path(handle.name)))

    def test_bare_set_literal_roster_parses(self):
        handle = _tree('GUARDED_AGENT_NAMES = {"code-reviewer"}\n')
        with handle:
            self.assertEqual(
                fleet_records.parse_guarded_agents(Path(handle.name)),
                frozenset({"code-reviewer"}),
            )

    def test_collector_never_takes_the_roster_from_its_caller(self):
        """Guard coverage always describes the inspected tree, never the caller's own."""
        handle = _tree(None)
        with handle:
            records = fleet_records.collect(Path(handle.name), PLUGIN)
        self.assertIsNone(records.guarded_agents)

    def test_this_repository_roster_matches_the_live_guard(self):
        parsed = fleet_records.parse_guarded_agents(REPO)
        self.assertIsNotNone(parsed)
        self.assertIn("code-reviewer", parsed)


class ReferenceRecordTests(unittest.TestCase):
    def test_surface_and_line_are_recorded_per_occurrence(self):
        handle = _tree(None)
        with handle:
            records = fleet_records.collect(Path(handle.name), PLUGIN)
        surfaces = {r.surface for r in records.references}
        self.assertEqual(surfaces, {"description", "body"})
        for reference in records.references:
            self.assertEqual(reference.source, "demo-agent")
            self.assertEqual(reference.target, "demo-skill")
            self.assertGreater(reference.line, 0)
        body = next(r for r in records.references if r.surface == "body")
        self.assertTrue(body.is_slash_command)
        self.assertEqual(body.raw, f"/{PLUGIN}:demo-skill")

    def test_reference_lines_point_at_the_real_source_line(self):
        handle = _tree(None)
        with handle:
            root = Path(handle.name)
            records = fleet_records.collect(root, PLUGIN)
            lines = (root / "agents" / "demo-agent.md").read_text(encoding="utf-8").splitlines()
            for reference in records.references:
                self.assertIn(reference.raw, lines[reference.line - 1])

    def test_a_reference_in_another_frontmatter_field_gets_its_own_surface(self):
        """The third surface value, which previously had no firing test at all. Folding it into
        description or body would count a reference where no reader sees one."""
        handle = _tree(None)
        with handle:
            root = Path(handle.name)
            skill = root / "skills" / "demo-skill" / "SKILL.md"
            skill.write_text(
                "---\nname: demo-skill\ndescription: A demo skill.\n"
                f"argument-hint: pass {PLUGIN}:demo-agent\n---\n\nBody.\n",
                encoding="utf-8",
            )
            records = fleet_records.collect(root, PLUGIN)
        surfaces = {r.surface for r in records.references if r.path == skill}
        self.assertEqual(surfaces, {"frontmatter"})
        self.assertEqual(fleet_records.surface_occurrences(records)["frontmatter"], 1)

    def test_surface_occurrences_always_carries_all_three_keys(self):
        handle = _tree(None)
        with handle:
            records = fleet_records.collect(Path(handle.name), PLUGIN)
        self.assertEqual(
            sorted(fleet_records.surface_occurrences(records)),
            ["body", "description", "frontmatter"],
        )

    def test_bundled_reference_files_are_attributed_to_their_skill(self):
        handle = _tree(None)
        with handle:
            root = Path(handle.name)
            bundle = root / "skills" / "demo-skill" / "references"
            bundle.mkdir()
            (bundle / "detail.md").write_text(f"See {PLUGIN}:demo-agent.\n", encoding="utf-8")
            records = fleet_records.collect(root, PLUGIN)
        bundled = [r for r in records.references if r.path.name == "detail.md"]
        self.assertEqual(len(bundled), 1)
        self.assertEqual(bundled[0].source, "demo-skill")
        self.assertFalse(bundled[0].in_core_definition)

    def test_stable_edges_exclude_bundled_files_but_occurrences_do_not(self):
        """The dated identity is core-definition-only; the surface series is not. Differencing one
        against the other is the drift-that-isn't this separation exists to prevent."""
        handle = _tree(None)
        with handle:
            root = Path(handle.name)
            bundle = root / "skills" / "demo-skill" / "references"
            bundle.mkdir()
            (bundle / "detail.md").write_text(f"See {PLUGIN}:demo-agent.\n", encoding="utf-8")
            records = fleet_records.collect(root, PLUGIN)
        self.assertNotIn(("demo-skill", "demo-agent"), fleet_records.stable_edges(records))
        self.assertEqual(sum(fleet_records.surface_occurrences(records).values()), 3)


class MemberRecordTests(unittest.TestCase):
    def test_block_sequence_and_inline_tools_both_parse(self):
        """An inline-only reader scores block-sequence agents zero and still totals a plausible
        number -- measured as 58 against a true 85 while reproducing the decision's snapshot."""
        inline = fleet_records.parse_frontmatter(REPO / "agents" / "code-reviewer.md")
        block = fleet_records.parse_frontmatter(REPO / "agents" / "researcher.md")
        self.assertGreater(len(fleet_records.split_tools(inline["tools"])), 0)
        self.assertGreater(len(fleet_records.split_tools(block["tools"])), 3)

    def test_preloads_are_a_separate_series_from_references(self):
        handle = _tree(None)
        with handle:
            records = fleet_records.collect(Path(handle.name), PLUGIN)
        self.assertEqual(fleet_records.preload_edges(records), {("demo-agent", "demo-skill")})

    def test_absent_tools_is_not_the_same_as_empty_authority(self):
        """An absent `tools:` INHERITS EVERY TOOL. The record reports an empty list, so any
        consumer reasoning about authority must consult the raw field, not the convenience view."""
        handle = _tree(None)
        with handle:
            root = Path(handle.name)
            skill = fleet_records.collect(root, PLUGIN).by_name("demo-skill")
        self.assertEqual(skill.tools, [])
        self.assertNotIn("tools", skill.fields)


class RoutingOverlayTests(unittest.TestCase):
    def test_clusters_and_cases_are_collected_from_this_repository(self):
        records = fleet_records.collect(REPO, PLUGIN)
        self.assertGreater(len(records.clusters), 0)
        cases = [case for cluster in records.clusters for case in cluster.cases]
        self.assertGreater(len(cases), 0)
        self.assertEqual({c.polarity for c in cases}, {"positive", "negative"})

    def test_a_scalar_nested_case_field_is_unreadable_not_a_crash(self):
        """Checking only top-level containers relocated the crash one level down: `expect_fires: 1`
        killed `tuple(...)` instead of listing the file as unreadable."""
        for payload in (
            '{"cluster":"x","cases":[{"id":"a","expect_fires":1}]}',
            '{"cluster":"x","cases":[{"id":"a","tags":"nope"}]}',
            '{"cluster":"x","cases":["not-an-object"]}',
        ):
            handle = _tree(None)
            with handle:
                root = Path(handle.name)
                (root / "evals" / "routing").mkdir(parents=True, exist_ok=True)
                (root / "evals" / "routing" / "bad.json").write_text(payload, encoding="utf-8")
                records = fleet_records.collect(root, PLUGIN)  # must not raise
            self.assertEqual([p.name for p in records.unreadable_clusters], ["bad.json"])

    def test_a_malformed_cluster_does_not_take_the_collector_down(self):
        handle = _tree(None)
        with handle:
            root = Path(handle.name)
            (root / "evals" / "routing").mkdir(parents=True)
            (root / "evals" / "routing" / "broken.json").write_text("{not json", encoding="utf-8")
            (root / "evals" / "routing" / "ok.json").write_text(
                json.dumps({"cluster": "ok", "members": ["demo-agent"], "cases": []}),
                encoding="utf-8",
            )
            records = fleet_records.collect(root, PLUGIN)
        self.assertEqual([c.name for c in records.clusters], ["ok"])


if __name__ == "__main__":
    unittest.main()
