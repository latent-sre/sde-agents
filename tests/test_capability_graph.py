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

    def test_a_self_loop_is_not_adoption(self):
        """A member that only names itself has been adopted by nobody, so it stays unreferenced."""
        with _tree() as name:
            root = Path(name)
            (root / "skills" / "solo-skill" / "SKILL.md").write_text(
                f"---\nname: solo-skill\ndescription: Alone.\n---\n\nSee {PLUGIN}:solo-skill.\n",
                encoding="utf-8",
            )
            report = _document(root)["report"]
        self.assertIn("solo-skill", report["unreferenced_components"])
        self.assertIn("solo-skill", [entry["source"] for entry in report["self_loops"]])

    def test_neither_a_reference_nor_a_preload_transfers_the_target_tools(self):
        """Influence is not authority. builder references linked-skill and preloads
        preloaded-skill; neither may add anything to builder's declared grant."""
        with _tree() as name:
            document = _document(Path(name))
        self.assertEqual(document["tool_grants"]["builder"], ["Bash", "Read", "Write"])
        self.assertIn(
            "not traversed as authority", document["report"]["host_authority_paths"]["note"]
        )

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

    def test_unknown_guard_roster_refuses_the_copilot_projection(self):
        """`bool(None)` is False, so an unreadable roster silently answered 'not guarded' and the
        artifact asserted execute_available for every Bash-holding agent -- a security claim made
        on the strength of a file never opened, contradicting the Claude section beside it."""
        with _tree(guarded=None) as name:
            hosts = _document(Path(name))["host_authority"]
        copilot = hosts["copilot"]["agents"]["reviewer"]
        self.assertIsNone(copilot["execute_available"])
        self.assertIsNone(copilot["execute_withheld_by_guard"])
        self.assertIsNone(copilot["tool_aliases"])
        self.assertEqual(copilot["projection"], "unavailable_unknown_guard_roster")
        self.assertIsNone(hosts["claude"]["agents"]["reviewer"]["guarded"])

    def test_guarded_agent_loses_execute_on_copilot(self):
        with _tree(guarded=["reviewer"]) as name:
            copilot = _document(Path(name))["host_authority"]["copilot"]["agents"]
        self.assertTrue(copilot["reviewer"]["execute_withheld_by_guard"])
        self.assertFalse(copilot["reviewer"]["execute_available"])
        self.assertNotIn("execute", copilot["reviewer"]["tool_aliases"])
        self.assertIn("execute", copilot["builder"]["tool_aliases"])

    def test_never_holding_bash_is_not_the_same_as_the_guard_withholding_it(self):
        """dispatcher declares no Bash, so nothing was taken from it. Reporting one flag for both
        would describe a control that was never applied to that role."""
        with _tree(guarded=["reviewer", "dispatcher"]) as name:
            copilot = _document(Path(name))["host_authority"]["copilot"]["agents"]
        self.assertFalse(copilot["dispatcher"]["execute_available"])
        self.assertFalse(copilot["dispatcher"]["execute_withheld_by_guard"])
        self.assertTrue(copilot["reviewer"]["execute_withheld_by_guard"])

    def test_codex_authority_stays_unknown_or_inherited(self):
        with _tree() as name:
            codex = _document(Path(name))["host_authority"]["codex"]
        self.assertEqual(codex["agents"]["builder"]["requested_sandbox_mode"], "workspace-write")
        self.assertEqual(codex["agents"]["reviewer"]["requested_sandbox_mode"], "read-only")
        for agent in codex["agents"].values():
            self.assertEqual(agent["effective_authority"], "unknown_or_inherited")
        self.assertTrue(codex["limitations"])

    def test_skill_tool_denies_are_projected_per_host(self):
        """Skills carry their own control, and the generator strips it for portable hosts. A report
        covering only agent tools answers 'what does each host withhold?' while omitting the only
        authority a directly-invoked skill surface declares."""
        with _tree() as name:
            root = Path(name)
            (root / "skills" / "solo-skill" / "SKILL.md").write_text(
                "---\nname: solo-skill\ndescription: Read-only.\n"
                "disallowed-tools: Write, Edit, NotebookEdit\n---\n\nBody.\n",
                encoding="utf-8",
            )
            hosts = _document(root)["host_authority"]
        self.assertEqual(
            hosts["claude"]["skills"]["solo-skill"]["disallowed_tools"],
            ["Edit", "NotebookEdit", "Write"],
        )
        for host in ("copilot", "vscode", "codex"):
            projected = hosts[host]["skills"]["solo-skill"]
            self.assertIsNone(projected["disallowed_tools"], host)
            self.assertEqual(
                projected["projection"], "tool_deny_stripped_for_portable_host", host
            )

    def test_a_skill_declaring_no_deny_is_absent_from_the_skill_projection(self):
        with _tree() as name:
            hosts = _document(Path(name))["host_authority"]
        self.assertEqual(hosts["claude"]["skills"], {})

    def test_every_host_states_its_limitations(self):
        with _tree() as name:
            hosts = _document(Path(name))["host_authority"]
        for host, projection in hosts.items():
            self.assertTrue(projection["limitations"], f"{host} projection states no limitation")


class UndeclaredAuthorityTests(unittest.TestCase):
    """An agent with no `tools:` inherits EVERY tool. Rendering that as an empty grant shows
    maximal authority as least privilege -- and no validator has necessarily run on an inspected
    foreign or baseline tree, so nothing upstream prevents the state."""

    def _tree_with_undeclared_agent(self) -> TemporaryDirectory:
        handle = _tree(guarded=["reviewer"])
        root = Path(handle.name)
        (root / "agents" / "inheritor.md").write_text(
            "---\nname: inheritor\ndescription: Declares no tools.\n---\n\nBody.\n",
            encoding="utf-8",
        )
        return handle

    def test_undeclared_agent_is_not_listed_with_an_empty_grant(self):
        with self._tree_with_undeclared_agent() as name:
            document = _document(Path(name))
        self.assertNotIn("inheritor", document["tool_grants"])
        self.assertEqual(document["tool_authority_undeclared"], ["inheritor"])

    def test_claude_projection_says_inherits_all_rather_than_an_empty_list(self):
        with self._tree_with_undeclared_agent() as name:
            claude = _document(Path(name))["host_authority"]["claude"]["agents"]
        self.assertEqual(claude["inheritor"]["authority"], "inherits_all")
        self.assertIsNone(claude["inheritor"]["declared_tools"])
        self.assertEqual(claude["builder"]["authority"], "declared")

    def test_other_host_projections_refuse_rather_than_guess_least_privilege(self):
        with self._tree_with_undeclared_agent() as name:
            hosts = _document(Path(name))["host_authority"]
        copilot = hosts["copilot"]["agents"]["inheritor"]
        codex = hosts["codex"]["agents"]["inheritor"]
        self.assertIsNone(copilot["tool_aliases"])
        self.assertIsNone(copilot["execute_available"])
        self.assertIsNone(codex["requested_sandbox_mode"])
        self.assertEqual(copilot["projection"], "unavailable_no_declared_tools")

    def test_report_marks_the_artifact_incomplete(self):
        with self._tree_with_undeclared_agent() as name:
            paths = _document(Path(name))["report"]["host_authority_paths"]
        self.assertEqual(paths["inherits_all_tools"], ["inheritor"])
        self.assertIn("INCOMPLETE", paths["note"])

    def test_a_fully_declared_fleet_is_not_marked_incomplete(self):
        with _tree() as name:
            paths = _document(Path(name))["report"]["host_authority_paths"]
        self.assertEqual(paths["inherits_all_tools"], [])
        self.assertNotIn("INCOMPLETE", paths["note"])


class UnreadableDefinitionTests(unittest.TestCase):
    def test_an_unparseable_definition_is_surfaced_not_silently_dropped(self):
        """It contributes no node, so omitting it entirely lets an operator diffing a baseline
        read a broken file as a deleted member."""
        with _tree() as name:
            root = Path(name)
            (root / "agents" / "broken.md").write_text(
                "---\nname: broken\ntools Read, Write\n---\n\nBody.\n", encoding="utf-8"
            )
            document = _document(root)
        self.assertEqual(document["unreadable_definitions"], ["agents/broken.md"])
        self.assertNotIn("broken", document["nodes"]["agents"])
        self.assertIn("INCOMPLETE", document["report"]["host_authority_paths"]["note"])

    def test_a_clean_tree_reports_no_unreadable_definitions(self):
        with _tree() as name:
            document = _document(Path(name))
        self.assertEqual(document["unreadable_definitions"], [])


class OccurrenceSeriesTests(unittest.TestCase):
    def test_bundled_reference_occurrences_reach_the_artifact(self):
        """The stable edge identity excludes references/ files by design; dropping them from the
        document entirely meant that whole surface appeared in no baseline diff at all."""
        with _tree() as name:
            root = Path(name)
            bundle = root / "skills" / "linked-skill" / "references"
            bundle.mkdir()
            (bundle / "detail.md").write_text(f"See {PLUGIN}:builder.\n", encoding="utf-8")
            document = _document(root)
        bundled = document["bundled_reference_occurrences"]
        self.assertEqual(len(bundled), 1)
        self.assertEqual(bundled[0]["source"], "linked-skill")
        self.assertEqual(bundled[0]["target"], "builder")
        self.assertFalse(Path(bundled[0]["path"]).is_absolute())
        # ...and the edge identity still excludes it.
        self.assertNotIn(
            ("linked-skill", "builder"),
            {(e["source"], e["target"]) for e in document["reference_edges"]},
        )

    def test_surface_series_is_emitted_with_all_three_keys(self):
        with _tree() as name:
            document = _document(Path(name))
        self.assertEqual(
            sorted(document["surface_occurrences"]), ["body", "description", "frontmatter"]
        )


class UnreadableClusterTests(unittest.TestCase):
    def test_a_malformed_cluster_is_named_not_silently_skipped(self):
        """Corruption and intentional removal produce the same absence unless it is recorded, and
        this overlay exists to be diffed across two trees."""
        with _tree() as name:
            root = Path(name)
            (root / "evals" / "routing" / "broken.json").write_text(
                "{not json", encoding="utf-8"
            )
            document = _document(root)
        overlay = document["measurement_overlay"]
        self.assertEqual(overlay["unreadable_clusters"], ["evals/routing/broken.json"])
        self.assertIn("INCOMPLETE", document["report"]["host_authority_paths"]["note"])

    def test_a_clean_tree_names_no_unreadable_clusters(self):
        with _tree() as name:
            overlay = _document(Path(name))["measurement_overlay"]
        self.assertEqual(overlay["unreadable_clusters"], [])


class EndpointIntegrityTests(unittest.TestCase):
    def test_an_unparseable_source_emits_no_phantom_edge(self):
        """The definition contributes no node but its body is still scanned, so checking only the
        target left an edge whose source appears in no node list -- a phantom node in Mermaid."""
        with _tree() as name:
            root = Path(name)
            (root / "agents" / "broken.md").write_text(
                f"---\nname: broken\ntools Read, Write\n---\n\nSee {PLUGIN}:builder here.\n",
                encoding="utf-8",
            )
            document = _document(root)
        sources = {e["source"] for e in document["reference_edges"]}
        self.assertNotIn("broken", sources)
        self.assertNotIn("broken", document["nodes"]["agents"])
        self.assertEqual(document["unreadable_definitions"], ["agents/broken.md"])

    def test_every_mermaid_edge_endpoint_has_a_declared_node(self):
        with _tree() as name:
            root = Path(name)
            (root / "agents" / "broken.md").write_text(
                f"---\nname: broken\ntools Read, Write\n---\n\nSee {PLUGIN}:builder here.\n",
                encoding="utf-8",
            )
            document = _document(root)
        declared = {
            capability_graph._mermaid_id(n)
            for n in document["nodes"]["agents"] + document["nodes"]["skills"]
        }
        for line in capability_graph.render_mermaid(document).splitlines()[1:]:
            if "-->" in line or "-.preload.->" in line:
                left, right = line.replace("-.preload.->", "-->").split("-->")
                self.assertIn(left.strip(), declared, line)
                self.assertIn(right.strip(), declared, line)


class MermaidSafetyTests(unittest.TestCase):
    def test_member_names_cannot_inject_mermaid_statements(self):
        """This tool records without judging, and NAME_RE is enforced only by validate_fleet.py,
        which has not necessarily run on an inspected foreign tree."""
        with _tree() as name:
            root = Path(name)
            (root / "agents" / "demo-agent.md").write_text(
                '---\nname: a; click a "javascript:alert(1)"\ndescription: Hostile.\n'
                "tools: Read\n---\n\nBody.\n",
                encoding="utf-8",
            )
            rendered = capability_graph.render_mermaid(_document(root))
        # No line may begin with a Mermaid keyword the graph never derived, and no label may carry
        # a raw quote that could terminate its own string.
        for line in rendered.splitlines()[1:]:
            self.assertTrue(line.startswith("  "), line)
            self.assertFalse(line.strip().startswith("click"), line)
        self.assertIn("#quot;", rendered)
        self.assertIn("a__click_a__javascript_alert_1_[", rendered)
        for line in rendered.splitlines()[1:]:
            identifier = line.strip().split("[")[0].split("(")[0].split(" ")[0]
            self.assertRegex(identifier, r"^[A-Za-z0-9_]+$")


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

    def test_identical_trees_in_different_directories_produce_identical_bytes(self):
        """The property the artifact actually claims. The same-root repeat test below is a weaker
        proxy that passed while every occurrence path still carried the checkout directory,
        defeating baseline-vs-candidate comparison and embedding the operator's layout."""
        with _tree() as first, _tree() as second:
            self.assertNotEqual(first, second)
            left = json.dumps(_document(Path(first)), indent=2, sort_keys=True)
            right = json.dumps(_document(Path(second)), indent=2, sort_keys=True)
        self.assertEqual(left, right)

    def test_no_absolute_path_reaches_the_artifact(self):
        with _tree() as name:
            payload = json.dumps(_document(Path(name)))
        self.assertNotIn(Path(name).as_posix(), payload)
        for edge in json.loads(payload)["reference_edges"]:
            for occurrence in edge["occurrences"]:
                self.assertFalse(Path(occurrence["path"]).is_absolute(), occurrence["path"])

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

    def test_the_inspected_root_never_supplies_the_extractor(self):
        """A tree carrying its own fleet_records.py and validate_fleet.py must not have them
        imported. If the root were on the import base, these would load and abort, so the report
        completing at all is the evidence."""
        with _tree() as name:
            root = Path(name)
            (root / "scripts").mkdir(exist_ok=True)
            for module in ("fleet_records.py", "validate_fleet.py", "capability_graph.py"):
                (root / "scripts" / module).write_text(
                    "raise SystemExit('the inspected tree supplied the extractor')\n",
                    encoding="utf-8",
                )
            document = _document(root)
        self.assertEqual(len(document["nodes"]["agents"]), 3)

    def test_unreadable_plugin_name_refuses_instead_of_emitting_a_blank_graph(self):
        """Without the namespace there is no reference grammar, so every edge would read as zero --
        a confident empty report about a densely linked tree."""
        with _tree() as name:
            (Path(name) / "plugin.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(capability_graph.main(["--root", name]), 1)


class RealTreeTests(unittest.TestCase):
    """Real-tree SMOKE emission, which is all the plan's Payload-4 list asks for.

    An earlier version pinned the live counts (155 edges, 7 preloads, 85 grants). That turned an
    explicitly advisory report into a merge blocker: adding one namespaced cross-reference -- the
    form AGENTS.md mandates -- failed the suite with `156 != 155` and no guidance, which is exactly
    what this tool's own docstring says the design refuses. The dated 140-edge reproduction belongs
    in the GRAPH-002 plan's record, not in a gate. What is asserted here instead is internal
    consistency, which no ordinary content edit can break.
    """

    def _document(self):
        plugin = json.loads((REPO / "plugin.json").read_text(encoding="utf-8"))["name"]
        return fleet_records.collect(REPO, plugin)

    def test_the_real_tree_emits_a_well_formed_report(self):
        document = capability_graph.build_document(self._document())
        self.assertTrue(document["reference_edges"])
        self.assertTrue(document["tool_grants"])
        self.assertEqual(document["schema_version"], capability_graph.SCHEMA_VERSION)

    def test_emitted_edges_match_the_collector_identity_exactly(self):
        """One rule, one owner. If the graph and the collector ever disagree about which pairs are
        edges, that is the duplicate-derivation failure, and it shows up here regardless of how
        many edges the tree happens to have."""
        records = self._document()
        document = capability_graph.build_document(records)
        emitted = {(e["source"], e["target"]) for e in document["reference_edges"]}
        self.assertEqual(emitted, fleet_records.stable_edges(records))

    def test_every_edge_endpoint_is_a_declared_member(self):
        records = self._document()
        document = capability_graph.build_document(records)
        members = {m.name for m in records.members}
        for edge in document["reference_edges"]:
            self.assertIn(edge["source"], members)
            self.assertIn(edge["target"], members)


if __name__ == "__main__":
    unittest.main()
