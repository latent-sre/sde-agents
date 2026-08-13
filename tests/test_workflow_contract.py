"""Schema v1 design-consistency checks, their witnesses, and the boundaries they refuse to cross.

The design validator's whole value is that a green result means something specific, so each test
pins one refusal and the witness it must produce. A checker that accepted a design nobody had
defined the semantics of would be worse than one that refused it.
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import workflow_contract as wc
from tests.support import REPO


BASE = {
    "schema_version": 1,
    "name": "review-then-apply",
    "entry": "start",
    "terminals": ["done"],
    "zones": [
        {"id": "review", "allows": ["apply"]},
        {"id": "apply", "allows": []},
    ],
    "nodes": [
        {"id": "start", "kind": "deterministic", "zone": "review"},
        {"id": "reviewer", "kind": "agent", "zone": "review",
         "binding": {"domain": "agent", "ref": "code-reviewer"},
         "output_schema": "review.v1", "max_attempts": 2},
        {"id": "verify", "kind": "verifier", "zone": "review",
         "binding": {"domain": "repo-script", "ref": "scripts/run_tests.py"},
         "input_schema": "review.v1"},
        {"id": "approve", "kind": "human", "zone": "review"},
        {"id": "deploy", "kind": "effect", "zone": "apply"},
        {"id": "done", "kind": "deterministic", "zone": "apply"},
    ],
    "edges": [
        {"from": "start", "to": "reviewer", "kind": "control"},
        {"from": "reviewer", "to": "verify", "kind": "data", "schema": "review.v1"},
        {"from": "reviewer", "to": "verify", "kind": "control"},
        {"from": "verify", "to": "approve", "kind": "control"},
        {"from": "approve", "to": "deploy", "kind": "control"},
        {"from": "approve", "to": "deploy", "kind": "approval", "effect": "deploy"},
        {"from": "deploy", "to": "done", "kind": "control"},
    ],
}


def _check(document: dict, root: Path = REPO) -> list[str]:
    """Return diagnostics for one design, or [] when it is design-consistent."""
    try:
        diagnostics, nodes, context = wc._validate_structure(document, root)
    except wc.Defect as defect:
        return [str(defect)]
    return diagnostics or wc._validate_semantics(document, nodes, context)


def _mutate(**_unused):
    return copy.deepcopy(BASE)


class ValidDesignTests(unittest.TestCase):
    def test_the_reference_design_is_consistent(self):
        self.assertEqual(_check(copy.deepcopy(BASE)), [])

    def test_cli_reports_design_consistent_and_never_runtime_enforced(self):
        with TemporaryDirectory() as out:
            path = Path(out) / "design.json"
            path.write_text(json.dumps(BASE), encoding="utf-8")
            self.assertEqual(wc.main([str(path), "--root", str(REPO)]), 0)

    def test_digest_is_lf_normalized_so_a_checkout_setting_cannot_change_identity(self):
        payload = json.dumps(BASE, indent=2)
        self.assertEqual(
            wc._digest(payload.encode("utf-8")),
            wc._digest(payload.replace("\n", "\r\n").encode("utf-8")),
        )

    def test_digest_is_lowercase_64_hex(self):
        digest = wc._digest(b"{}")
        self.assertEqual(len(digest), 64)
        self.assertTrue(wc._is_sha256(digest))


class ApprovalCoverageTests(unittest.TestCase):
    def test_effect_reachable_around_the_gate_is_rejected_with_the_bypass_path(self):
        """An 'is there an approval edge' check passes this. All-path coverage does not."""
        document = _mutate()
        document["edges"].append({"from": "start", "to": "deploy", "kind": "failure"})
        diagnostics = _check(document)
        self.assertEqual(len(diagnostics), 1)
        self.assertIn("without passing an approving human gate", diagnostics[0])
        # Node ids are repr'd in witnesses so a crafted id cannot forge output structure.
        self.assertIn("'start' -> 'deploy'", diagnostics[0])

    def test_effect_with_no_human_approval_edge_is_rejected(self):
        document = _mutate()
        document["edges"] = [e for e in document["edges"] if e.get("kind") != "approval"]
        self.assertTrue(
            any("no human approval edge naming it" in d for d in _check(document))
        )

    def test_approval_from_a_non_human_node_does_not_count_as_a_gate(self):
        document = _mutate()
        for node in document["nodes"]:
            if node["id"] == "approve":
                node["kind"] = "deterministic"
        self.assertTrue(
            any("no human approval edge naming it" in d for d in _check(document))
        )

    def test_approval_edge_must_name_its_own_target_effect(self):
        document = _mutate()
        for edge in document["edges"]:
            if edge.get("kind") == "approval":
                edge["effect"] = "done"
        self.assertTrue(any("must equal the target node id" in d for d in _check(document)))

    def test_subgraph_boundaries_are_listed_as_unverified_interiors(self):
        document = _mutate()
        document["nodes"].append({
            "id": "inner", "kind": "subgraph", "zone": "review",
            "binding": {"domain": "contract-digest", "ref": "a" * 64},
        })
        document["edges"].insert(1, {"from": "start", "to": "inner", "kind": "control"})
        document["edges"].insert(2, {"from": "inner", "to": "done", "kind": "control"})
        _, nodes, _ = wc._validate_structure(document, REPO)
        self.assertEqual(wc._unverified_interiors(nodes), ["a" * 64])


class GraphSemanticsTests(unittest.TestCase):
    def test_transition_cycle_is_rejected_with_the_cycle_as_witness(self):
        document = _mutate()
        document["edges"].append({"from": "deploy", "to": "reviewer", "kind": "control"})
        self.assertTrue(
            any("cycle rejected in schema v1" in d and "->" in d for d in _check(document))
        )

    def test_mixed_control_data_cycle_is_rejected_by_the_readiness_graph(self):
        """A data edge closing a loop is invisible to a transition-only cycle check."""
        document = _mutate()
        document["edges"].append(
            {"from": "approve", "to": "reviewer", "kind": "evidence"}
        )
        self.assertTrue(
            any("readiness graph: cycle" in d for d in _check(document))
        )

    def test_unreachable_node_is_rejected(self):
        document = _mutate()
        document["nodes"].append({"id": "orphan", "kind": "deterministic", "zone": "review"})
        self.assertTrue(any("unreachable from entry" in d for d in _check(document)))

    def test_node_reaching_no_terminal_is_rejected_with_its_frontier(self):
        document = _mutate()
        document["nodes"].append({"id": "sink", "kind": "deterministic", "zone": "review"})
        document["edges"].append({"from": "start", "to": "sink", "kind": "failure"})
        self.assertTrue(
            any("reaches no declared terminal" in d and "frontier" in d for d in _check(document))
        )

    def test_cross_zone_edge_requires_an_allow_and_says_what_it_proves(self):
        document = _mutate()
        document["zones"][0]["allows"] = []
        diagnostics = [d for d in _check(document) if "does not allow" in d]
        self.assertTrue(diagnostics)
        self.assertIn("declared topology relation only", diagnostics[0])

    def test_same_zone_edges_need_no_allow_entry(self):
        document = _mutate()
        document["zones"][1]["allows"] = []
        self.assertEqual([d for d in _check(document) if "does not allow" in d], [])

    def test_data_edge_schema_must_match_producer_and_consumer(self):
        document = _mutate()
        for node in document["nodes"]:
            if node["id"] == "verify":
                node["input_schema"] = "other.v1"
        self.assertTrue(any("does not match producer" in d for d in _check(document)))


class JoinTests(unittest.TestCase):
    def test_multiple_control_predecessors_without_a_join_are_rejected(self):
        document = _mutate()
        document["edges"].append({"from": "start", "to": "verify", "kind": "control"})
        diagnostics = [d for d in _check(document) if "no join" in d]
        self.assertTrue(diagnostics)
        self.assertIn("['reviewer', 'start']", diagnostics[0])

    def test_a_valid_all_join_is_accepted(self):
        document = _mutate()
        document["edges"].append({"from": "start", "to": "verify", "kind": "control"})
        for node in document["nodes"]:
            if node["id"] == "verify":
                node["join"] = {
                    "mode": "all", "timeout_ms": 60000,
                    "on_timeout": "fail", "on_failed_predecessor": "fail",
                }
        self.assertEqual(_check(document), [])

    def test_join_on_a_single_predecessor_configures_nothing(self):
        document = _mutate()
        for node in document["nodes"]:
            if node["id"] == "verify":
                node["join"] = {
                    "mode": "all", "timeout_ms": 60000,
                    "on_timeout": "fail", "on_failed_predecessor": "fail",
                }
        self.assertTrue(any("configures nothing" in d for d in _check(document)))

    def test_non_all_join_modes_are_refused_until_an_executor_exists(self):
        for mode in ("any", "quorum", "first"):
            document = _mutate()
            document["edges"].append({"from": "start", "to": "verify", "kind": "control"})
            for node in document["nodes"]:
                if node["id"] == "verify":
                    node["join"] = {
                        "mode": mode, "timeout_ms": 60000,
                        "on_timeout": "fail", "on_failed_predecessor": "fail",
                    }
            self.assertTrue(
                any("join mode must be 'all'" in d for d in _check(document)), mode
            )

    def test_join_policies_are_fail_closed(self):
        document = _mutate()
        document["edges"].append({"from": "start", "to": "verify", "kind": "control"})
        for node in document["nodes"]:
            if node["id"] == "verify":
                node["join"] = {
                    "mode": "all", "timeout_ms": 60000,
                    "on_timeout": "continue", "on_failed_predecessor": "ignore",
                }
        diagnostics = _check(document)
        self.assertTrue(any("on_timeout must be 'fail'" in d for d in diagnostics))
        self.assertTrue(any("on_failed_predecessor must be 'fail'" in d for d in diagnostics))

    def test_unbounded_join_timeout_is_rejected(self):
        document = _mutate()
        document["edges"].append({"from": "start", "to": "verify", "kind": "control"})
        for node in document["nodes"]:
            if node["id"] == "verify":
                node["join"] = {
                    "mode": "all", "timeout_ms": 0,
                    "on_timeout": "fail", "on_failed_predecessor": "fail",
                }
        self.assertTrue(any("timeout_ms must be a positive integer" in d for d in _check(document)))


class BindingTests(unittest.TestCase):
    def test_each_kind_accepts_only_its_own_binding_domains(self):
        for node_id, domain, ref in (
            ("reviewer", "tool", "code-reviewer"),
            ("verify", "contract-digest", "a" * 64),
        ):
            document = _mutate()
            for node in document["nodes"]:
                if node["id"] == node_id:
                    node["binding"] = {"domain": domain, "ref": ref}
            self.assertTrue(any("accepts domain" in d for d in _check(document)), node_id)

    def test_agent_binding_must_name_a_canonical_agent(self):
        document = _mutate()
        for node in document["nodes"]:
            if node["id"] == "reviewer":
                node["binding"] = {"domain": "agent", "ref": "code-reviewer-v2"}
        self.assertTrue(any("not a canonical agent" in d for d in _check(document)))

    def test_tool_binding_must_name_an_adopted_tool(self):
        document = _mutate()
        document["nodes"].append({
            "id": "grep", "kind": "tool", "zone": "review",
            "binding": {"domain": "tool", "ref": "Telepathy"},
        })
        document["edges"].append({"from": "start", "to": "grep", "kind": "control"})
        self.assertTrue(any("not an adopted fleet tool" in d for d in _check(document)))

    def test_unbound_kinds_reject_a_fleet_binding(self):
        for node_id in ("start", "approve", "deploy"):
            document = _mutate()
            for node in document["nodes"]:
                if node["id"] == node_id:
                    node["binding"] = {"domain": "agent", "ref": "code-reviewer"}
            self.assertTrue(any("takes no binding" in d for d in _check(document)), node_id)

    def test_subgraph_ref_must_be_a_lowercase_sha256(self):
        document = _mutate()
        document["nodes"].append({
            "id": "inner", "kind": "subgraph", "zone": "review",
            "binding": {"domain": "contract-digest", "ref": "A" * 64},
        })
        document["edges"].append({"from": "start", "to": "inner", "kind": "control"})
        self.assertTrue(any("lowercase 64-hex" in d for d in _check(document)))

    def test_repo_script_escaping_the_root_is_rejected_with_the_resolved_path(self):
        document = _mutate()
        for node in document["nodes"]:
            if node["id"] == "verify":
                node["binding"] = {"domain": "repo-script", "ref": "../../../etc/passwd"}
        diagnostics = [d for d in _check(document) if "escapes the repository root" in d]
        self.assertTrue(diagnostics)
        self.assertIn("witness:", diagnostics[0])

    def test_repo_script_escaping_through_a_symlink_is_rejected(self):
        with TemporaryDirectory() as outside, TemporaryDirectory() as root:
            target = Path(outside) / "payload.py"
            target.write_text("# outside the tree\n", encoding="utf-8")
            link = Path(root) / "linked.py"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation not permitted on this host")
            defects = wc._repo_script_defects("linked.py", "nodes[x]", Path(root))
        self.assertTrue(any("escapes the repository root" in d for d in defects))

    def test_repo_script_must_exist(self):
        document = _mutate()
        for node in document["nodes"]:
            if node["id"] == "verify":
                node["binding"] = {"domain": "repo-script", "ref": "scripts/not_here.py"}
        self.assertTrue(any("does not resolve to an existing file" in d for d in _check(document)))


class SchemaStrictnessTests(unittest.TestCase):
    def test_unknown_keys_are_rejected_at_every_level(self):
        for path, patch in (
            ("document", lambda d: d.update({"retries": 1})),
            ("node", lambda d: d["nodes"][0].update({"retries": 1})),
            ("edge", lambda d: d["edges"][0].update({"weight": 1})),
            ("zone", lambda d: d["zones"][0].update({"trusted": True})),
        ):
            document = _mutate()
            patch(document)
            self.assertTrue(any("unknown key" in d for d in _check(document)), path)

    def test_wrong_schema_version_is_refused_outright(self):
        document = _mutate()
        document["schema_version"] = 2
        self.assertTrue(any("must be exactly 1" in d for d in _check(document)))

    def test_embedded_expressions_are_rejected(self):
        for value in ("${env.X}", "{{ ctx.y }}", "$(whoami)", "a && b", "lambda x: x"):
            document = _mutate()
            document["nodes"][1]["output_schema"] = value
            self.assertTrue(
                any("is not a plain identifier" in d for d in _check(document)), value
            )

    def test_ordinary_predicates_are_rejected_as_state_fields(self):
        """A substring blacklist accepted every one of these: none contains a marker anyone had
        thought to list, and all four are predicates schema v1 says it cannot evaluate."""
        for value in ("status == 'ok'", "count > 3", "x in (1,2)", "f(x)", "a-b == c", "not ready"):
            document = _mutate()
            document["edges"][0] = {
                "from": "start", "to": "reviewer", "kind": "condition",
                "state_field": value, "values": ["ok"],
            }
            self.assertTrue(
                any("is not a plain identifier" in d for d in _check(document)), value
            )

    def test_plain_identifiers_remain_acceptable(self):
        for value in ("status", "review_state", "result.kind", "phase-1"):
            document = _mutate()
            document["edges"][0] = {
                "from": "start", "to": "reviewer", "kind": "condition",
                "state_field": value, "values": ["ok"],
            }
            self.assertEqual(
                [d for d in _check(document) if "plain identifier" in d], [], value
            )

    def test_a_data_edge_with_no_schema_on_any_side_is_untyped_and_rejected(self):
        """None == None == None passed, so a handoff with no contract earned design-consistent."""
        document = _mutate()
        for edge in document["edges"]:
            if edge.get("kind") == "data":
                edge.pop("schema", None)
        for node in document["nodes"]:
            node.pop("output_schema", None)
            node.pop("input_schema", None)
        self.assertTrue(any("data edge is untyped" in d for d in _check(document)))

    def test_each_missing_schema_side_is_named(self):
        for drop, expected in (
            ("edge", "edge schema"),
            ("producer", "producer output_schema"),
            ("consumer", "consumer input_schema"),
        ):
            document = _mutate()
            if drop == "edge":
                for edge in document["edges"]:
                    if edge.get("kind") == "data":
                        edge.pop("schema")
            elif drop == "producer":
                document["nodes"][1].pop("output_schema")
            else:
                document["nodes"][2].pop("input_schema")
            self.assertTrue(
                any(expected in d for d in _check(document) if "untyped" in d), drop
            )

    def test_a_non_string_schema_is_rejected(self):
        for value in (None, 1, True, [], {}):
            document = _mutate()
            for edge in document["edges"]:
                if edge.get("kind") == "data":
                    edge["schema"] = value
            self.assertNotEqual(_check(document), [], repr(value))

    def test_condition_edges_require_a_finite_value_set(self):
        document = _mutate()
        document["edges"][0] = {"from": "start", "to": "reviewer", "kind": "condition",
                                "state_field": "status"}
        self.assertTrue(any("finite, non-empty values list" in d for d in _check(document)))

    def test_distinct_enum_routes_are_representable(self):
        document = _mutate()
        document["edges"][0] = {"from": "start", "to": "reviewer", "kind": "condition",
                                "state_field": "status", "values": ["ok"]}
        document["edges"].append({"from": "start", "to": "reviewer", "kind": "condition",
                                  "state_field": "status", "values": ["retry"]})
        self.assertEqual([d for d in _check(document) if "duplicate transition" in d], [])

    def test_identical_routes_are_a_duplicate_transition(self):
        document = _mutate()
        document["edges"].append({"from": "start", "to": "reviewer", "kind": "control"})
        self.assertTrue(any("duplicate transition" in d for d in _check(document)))

    def test_unbounded_node_budget_is_rejected(self):
        document = _mutate()
        document["nodes"][1]["max_attempts"] = 0
        self.assertTrue(any("positive integer" in d for d in _check(document)))

    def test_ill_typed_containers_produce_diagnostics_not_a_traceback(self):
        """`list(None)` and `sorted(["b", 1])` raised uncaught, so the CLI printed a Python
        traceback instead of the ordered diagnostics its exit-1 contract promises -- a malformed
        document was indistinguishable from a crashed tool."""
        for patch in (
            lambda d: d["zones"].__setitem__(0, {"id": "review", "allows": None}),
            lambda d: d["zones"].__setitem__(0, {"id": "review", "allows": ["b", 1]}),
            lambda d: d.__setitem__("nodes", "not-a-list"),
            lambda d: d.__setitem__("edges", 7),
            lambda d: d.__setitem__("terminals", None),
            lambda d: d.__setitem__("zones", {}),
        ):
            document = _mutate()
            patch(document)
            diagnostics = _check(document)  # must not raise
            self.assertTrue(diagnostics)

    def test_ill_typed_containers_exit_one_through_the_cli(self):
        with TemporaryDirectory() as out:
            document = _mutate()
            document["zones"][0] = {"id": "review", "allows": None}
            path = Path(out) / "illtyped.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            self.assertEqual(wc.main([str(path), "--root", str(REPO)]), 1)

    def test_classification_is_scoped_to_data_and_evidence_edges(self):
        document = _mutate()
        document["edges"][0]["classification"] = "secret"  # a control edge
        self.assertTrue(
            any("only meaningful on a data or evidence edge" in d for d in _check(document))
        )

    def test_classification_is_accepted_on_an_evidence_edge(self):
        document = _mutate()
        document["edges"].append({
            "from": "verify", "to": "approve", "kind": "evidence", "classification": "internal",
        })
        self.assertEqual(
            [d for d in _check(document) if "classification" in d], []
        )

    def test_duplicate_node_ids_are_rejected(self):
        document = _mutate()
        document["nodes"].append({"id": "verify", "kind": "deterministic", "zone": "review"})
        self.assertTrue(any("duplicate node id" in d for d in _check(document)))

    def test_a_node_in_an_undeclared_zone_is_rejected(self):
        document = _mutate()
        document["nodes"][1]["zone"] = "shadow"
        self.assertTrue(any("is not declared in zones" in d for d in _check(document)))

    def test_a_condition_only_cycle_is_rejected(self):
        """Condition edges are transitions; a loop built purely from them is still a cycle."""
        document = _mutate()
        document["edges"].append({
            "from": "deploy", "to": "reviewer", "kind": "condition",
            "state_field": "status", "values": ["retry"],
        })
        self.assertTrue(
            any("cycle rejected in schema v1" in d for d in _check(document))
        )

    def test_zone_allows_must_be_sorted(self):
        document = _mutate()
        document["zones"][0]["allows"] = ["review", "apply"]
        self.assertTrue(any("must be a sorted list" in d for d in _check(document)))


class CliBoundaryTests(unittest.TestCase):
    def test_unreadable_input_exits_two_not_one(self):
        """Exit 1 means 'the design is wrong'. A missing file is not a design defect."""
        with TemporaryDirectory() as out:
            missing = Path(out) / "absent.json"
            self.assertEqual(wc.main([str(missing), "--root", str(REPO)]), 2)

    def test_malformed_json_exits_two(self):
        with TemporaryDirectory() as out:
            path = Path(out) / "bad.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(wc.main([str(path), "--root", str(REPO)]), 2)

    def test_malformed_utf8_exits_two(self):
        """Undecodable bytes are an input problem, not a statement about the design."""
        with TemporaryDirectory() as out:
            path = Path(out) / "bad.json"
            path.write_bytes(b'{"schema_version": 1, "name": "\xff\xfe"}')
            self.assertEqual(wc.main([str(path), "--root", str(REPO)]), 2)

    def test_diagnostics_are_deterministically_ordered(self):
        """A defect list that reorders between runs cannot be diffed across a review."""
        # Structurally sound on purpose: structural defects short-circuit the semantic pass, so a
        # multi-diagnostic ordering check has to come from the semantic layer.
        document = _mutate()
        document["nodes"].append({"id": "orphan", "kind": "deterministic", "zone": "review"})
        document["edges"].append({"from": "start", "to": "deploy", "kind": "failure"})
        document["zones"][0]["allows"] = []
        first, second = _check(copy.deepcopy(document)), _check(copy.deepcopy(document))
        self.assertEqual(first, second)
        self.assertGreater(len(first), 2)

    def test_an_inconsistent_design_exits_one(self):
        with TemporaryDirectory() as out:
            document = _mutate()
            document["edges"].append({"from": "start", "to": "deploy", "kind": "failure"})
            path = Path(out) / "design.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            self.assertEqual(wc.main([str(path), "--root", str(REPO)]), 1)


if __name__ == "__main__":
    unittest.main()
