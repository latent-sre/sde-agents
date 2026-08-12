"""The operator capability graph: report semantics, host separation, and determinism.

Each report section gets an independent expected record rather than a shape check, because a
section that silently changes meaning still produces a well-shaped document.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import capability_graph, fleet_records
from tests.support import REPO


PLUGIN = "demo-plugin"


def _agent(name: str, tools: str, *, body: str = "", skills: list[str] | None = None) -> str:
    preload = "".join(f"\n  - {s}" for s in (skills or []))
    return (
        f"---\nname: {name}\ndescription: Demo {name}.\ntools: {tools}\n"
        + (f"skills:{preload}\n" if skills else "")
        + f"---\n\n{body}\n"
    )


def _tree(guarded: list[str] | None = None) -> TemporaryDirectory:
    """A fixture fleet with one of everything the five sections need to be non-empty."""
    handle = TemporaryDirectory()
    root = Path(handle.name)
    (root / "agents").mkdir()
    (root / "evals" / "routing").mkdir(parents=True)
    for skill in ("solo-skill", "preloaded-skill", "linked-skill"):
        (root / "skills" / skill).mkdir(parents=True)
        (root / "skills" / skill / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: The {skill}.\n---\n\nBody.\n", encoding="utf-8"
        )
    # Self-loop: this skill names itself.
    (root / "skills" / "linked-skill" / "SKILL.md").write_text(
        f"---\nname: linked-skill\ndescription: Links.\n---\n\nSee {PLUGIN}:linked-skill.\n",
        encoding="utf-8",
    )
    (root / "agents" / "builder.md").write_text(
        _agent("builder", "Read, Write, Bash", body=f"Route to {PLUGIN}:linked-skill.",
               skills=["preloaded-skill"]),
        encoding="utf-8",
    )
    (root / "agents" / "reviewer.md").write_text(
        _agent("reviewer", "Read, Bash", body=f"Ask {PLUGIN}:builder."), encoding="utf-8"
    )
    (root / "agents" / "dispatcher.md").write_text(
        _agent("dispatcher", "Read, Agent", body=f"Delegate to {PLUGIN}:builder."),
        encoding="utf-8",
    )
    (root / "evals" / "routing" / "core.json").write_text(
        json.dumps({
            "cluster": "core",
            "members": ["builder", "reviewer"],
            "cases": [{"id": "pos-build", "polarity": "positive", "expect_fires": ["builder"]}],
        }),
        encoding="utf-8",
    )
    (root / "plugin.json").write_text(json.dumps({"name": PLUGIN}), encoding="utf-8")
    if guarded is not None:
        (root / "scripts").mkdir()
        (root / "scripts" / "readonly-guard.py").write_text(
            f"GUARDED_AGENT_NAMES = frozenset({json.dumps(guarded)})\n", encoding="utf-8"
        )
    return handle


def _document(root: Path) -> dict:
    return capability_graph.build_document(fleet_records.collect(root, PLUGIN))


class ReportSectionTests(unittest.TestCase):
    def test_unreferenced_excludes_members_reached_only_by_preload(self):
        """A preloaded skill is adopted. Counting references alone reported a live skill as an
        orphan -- found against the real tree, where sde-fullstack preloads code-craft."""
        with _tree() as name:
            report = _document(Path(name))["report"]
        # dispatcher and reviewer are referenced by nobody either; solo-skill is the skill case.
        self.assertEqual(
            report["unreferenced_components"], ["dispatcher", "reviewer", "solo-skill"]
        )
        self.assertNotIn("preloaded-skill", report["unreferenced_components"])
        self.assertEqual(report["reached_only_by_preload"], ["preloaded-skill"])

    def test_self_loops_retain_every_occurrence_with_a_location(self):
        with _tree() as name:
            loops = _document(Path(name))["report"]["self_loops"]
        self.assertEqual([entry["source"] for entry in loops], ["linked-skill"])
        occurrence = loops[0]["occurrences"][0]
        self.assertEqual(occurrence["surface"], "body")
        self.assertGreater(occurrence["line"], 0)

    def test_hub_concentration_keeps_preload_inbound_in_its_own_column(self):
        """Adding preloads into inbound_degree would silently redefine the dated series."""
        with _tree() as name:
            hub = _document(Path(name))["report"]["hub_concentration"]
        rows = {row["member"]: row for row in hub}
        self.assertEqual(rows["builder"]["inbound_degree"], 2)
        self.assertEqual(rows["preloaded-skill"]["inbound_degree"], 0)
        self.assertEqual(rows["preloaded-skill"]["preload_inbound_degree"], 1)

    def test_cluster_gaps_report_endpoints_never_co_listed(self):
        with _tree() as name:
            gaps = _document(Path(name))["report"]["routing_cluster_relationship_gaps"]
        pairs = {(g["source"], g["target"]) for g in gaps}
        # builder and reviewer share the `core` cluster, so that edge is not a gap.
        self.assertNotIn(("reviewer", "builder"), pairs)
        self.assertIn(("dispatcher", "builder"), pairs)

    def test_section_key_avoids_claiming_coverage(self):
        """Cluster co-membership is not behavioral coverage; the key must not imply it."""
        with _tree() as name:
            report = _document(Path(name))["report"]
        self.assertIn("routing_cluster_relationship_gaps", report)
        self.assertFalse(any("coverage" in key for key in report))

    def test_agent_grant_marks_dynamic_delegation_without_merging_grants(self):
        with _tree() as name:
            document = _document(Path(name))
        delegation = document["report"]["host_authority_paths"]["dynamic_delegation"]
        self.assertEqual(sorted(delegation), ["dispatcher"])
        # The dispatcher must not acquire the builder's Write through a delegation edge.
        self.assertNotIn("Write", document["tool_grants"]["dispatcher"])


class HostSeparationTests(unittest.TestCase):
    def test_guard_coverage_is_claude_only_and_never_unioned(self):
        with _tree(guarded=["reviewer"]) as name:
            hosts = _document(Path(name))["host_authority"]
        self.assertTrue(hosts["claude"]["agents"]["reviewer"]["guarded"])
        self.assertNotIn("guarded", hosts["codex"]["agents"]["reviewer"])
        self.assertNotIn("guarded", hosts["copilot"]["agents"]["reviewer"])
        self.assertNotIn("fleet", hosts)

    def test_unknown_guard_roster_is_not_reported_as_unguarded(self):
        """The tree carries no guard module, so coverage is unknown -- not False."""
        with _tree(guarded=None) as name:
            claude = _document(Path(name))["host_authority"]["claude"]
        self.assertIsNone(claude["agents"]["reviewer"]["guarded"])
        self.assertEqual(claude["agents"]["reviewer"]["guard_evidence"], "unknown")

    def test_guarded_agent_loses_execute_on_copilot(self):
        with _tree(guarded=["reviewer"]) as name:
            copilot = _document(Path(name))["host_authority"]["copilot"]["agents"]
        self.assertTrue(copilot["reviewer"]["execute_withheld"])
        self.assertNotIn("execute", copilot["reviewer"]["tool_aliases"])
        self.assertIn("execute", copilot["builder"]["tool_aliases"])

    def test_codex_authority_stays_unknown_or_inherited(self):
        with _tree() as name:
            codex = _document(Path(name))["host_authority"]["codex"]
        self.assertEqual(codex["agents"]["builder"]["requested_sandbox_mode"], "workspace-write")
        self.assertEqual(codex["agents"]["reviewer"]["requested_sandbox_mode"], "read-only")
        for agent in codex["agents"].values():
            self.assertEqual(agent["effective_authority"], "unknown_or_inherited")
        self.assertTrue(codex["limitations"])

    def test_every_host_states_its_limitations(self):
        with _tree() as name:
            hosts = _document(Path(name))["host_authority"]
        for host, projection in hosts.items():
            self.assertTrue(projection["limitations"], f"{host} projection states no limitation")


class MeasurementOverlayTests(unittest.TestCase):
    def test_co_membership_and_case_assertions_stay_separable(self):
        with _tree() as name:
            overlay = _document(Path(name))["measurement_overlay"]
        self.assertEqual(overlay["cluster_co_membership"]["core"], ["builder", "reviewer"])
        # reviewer shares the cluster but no case asserts it fires.
        self.assertEqual(sorted(overlay["members_with_case_assertions"]), ["builder"])


class DeterminismTests(unittest.TestCase):
    def test_two_runs_of_one_tree_are_byte_identical(self):
        with _tree() as name:
            first = json.dumps(_document(Path(name)), indent=2, sort_keys=True)
            second = json.dumps(_document(Path(name)), indent=2, sort_keys=True)
        self.assertEqual(first, second)

    def test_emitted_files_use_lf_and_carry_no_timestamp(self):
        with _tree() as name, TemporaryDirectory() as out:
            target = Path(out) / "graph.json"
            capability_graph.main(["--root", name, "--emit", str(target)])
            raw = target.read_bytes()
        self.assertEqual(raw.count(b"\r\n"), 0)
        self.assertNotIn(b"generated_at", raw)

    def test_mermaid_is_a_view_of_the_same_edges(self):
        with _tree() as name:
            document = _document(Path(name))
        rendered = capability_graph.render_mermaid(document)
        self.assertEqual(
            rendered.count(" --> "), len(document["reference_edges"])
        )
        self.assertEqual(rendered.count(" -.preload.-> "), len(document["preload_edges"]))


class SafetyTests(unittest.TestCase):
    def test_inspected_tree_is_never_executed(self):
        """A tree whose guard module would abort on import must still produce a report."""
        with _tree() as name:
            root = Path(name)
            (root / "scripts").mkdir(exist_ok=True)
            (root / "scripts" / "readonly-guard.py").write_text(
                "raise SystemExit('never execute the inspected tree')\n"
                'GUARDED_AGENT_NAMES = frozenset({"reviewer"})\n',
                encoding="utf-8",
            )
            claude = _document(root)["host_authority"]["claude"]
        self.assertTrue(claude["agents"]["reviewer"]["guarded"])

    def test_unreadable_plugin_name_refuses_instead_of_emitting_a_blank_graph(self):
        """Without the namespace there is no reference grammar, so every edge would read as zero --
        a confident empty report about a densely linked tree."""
        with _tree() as name:
            (Path(name) / "plugin.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(capability_graph.main(["--root", name]), 1)


class RealTreeTests(unittest.TestCase):
    def test_this_repository_reproduces_the_recorded_stable_measure(self):
        """The dated identity, bound to the reproduction recorded in the GRAPH-002 plan."""
        plugin = json.loads((REPO / "plugin.json").read_text(encoding="utf-8"))["name"]
        document = capability_graph.build_document(fleet_records.collect(REPO, plugin))
        self.assertEqual(len(document["reference_edges"]), 155)
        self.assertEqual(len(document["preload_edges"]), 7)
        self.assertEqual(
            sum(len(t) for t in document["tool_grants"].values()), 85
        )


if __name__ == "__main__":
    unittest.main()
