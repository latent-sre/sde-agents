#!/usr/bin/env python3
"""Validate a prospective workflow DESIGN document for internal consistency.

What this proves and what it does not: a design that passes here is *design-consistent*. It is not
runtime-enforced, not executed, and not bound to any run. No host validates a workflow this way at
dispatch time, so a green result here is a reviewable property of the document alone. GRAPH-004
owns committed contracts, digest resolution, and execution.

Schema v1 is deliberately narrow. It accepts `all` joins, acyclic graphs, and all-path human
approval, and it rejects everything whose semantics cannot be settled without an executable
consumer -- `any`/quorum joins, late arrival, cancellation, reset, and any embedded expression or
predicate. A validator that guessed at those would certify designs whose real behavior nobody has
defined, which is worse than refusing them.

The CLI takes one explicit JSON path. It never scans a directory, and `validate_fleet.py` never
calls it: this is an operator tool, not a gate.

Exit codes:
    0  design-consistent; prints the design digest and a summary
    1  design defects; prints ordered diagnostics, each with a deterministic witness
    2  invocation or unreadable-input error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fleet_records  # noqa: E402  (sibling module; scripts/ is not a package)

SCHEMA_VERSION = 1

TOP_LEVEL_KEYS = {"schema_version", "name", "entry", "terminals", "zones", "nodes", "edges"}
NODE_KEYS = {
    "id", "kind", "zone", "binding", "join",
    "input_schema", "output_schema", "max_attempts", "timeout_ms",
}
EDGE_KEYS = {"from", "to", "kind", "schema", "state_field", "values", "effect", "classification"}
ZONE_KEYS = {"id", "allows"}
JOIN_KEYS = {"mode", "timeout_ms", "on_timeout", "on_failed_predecessor"}

NODE_KINDS = {"agent", "tool", "verifier", "subgraph", "deterministic", "human", "effect"}
EDGE_KINDS = {"control", "condition", "failure", "compensation", "data", "approval", "evidence"}

# Which edge kinds move execution forward, and which merely make a node ready. Treating all edges
# as interchangeable is what lets a mixed control/data deadlock read as an acyclic design.
TRANSITION_KINDS = {"control", "condition", "failure", "compensation"}
READINESS_KINDS = {"control", "condition", "data", "approval", "evidence"}

# Kinds that take no fleet-member binding: their stable ID, zone, and edges describe the role.
UNBOUND_KINDS = {"deterministic", "human", "effect"}
BINDING_DOMAINS = {
    "agent": {"agent"},
    "tool": {"tool"},
    "verifier": {"agent", "repo-script"},
    "subgraph": {"contract-digest"},
}
BUDGET_FIELDS = ("max_attempts", "timeout_ms")
MAX_BUDGET = 86_400_000  # one day in ms; a bound exists so "unbounded" cannot be spelled.

# Identifier fields accept a POSITIVE grammar, never a blacklist of suspicious substrings. A
# blacklist answers "does this look like an expression I thought of?", which `status == 'ok'`,
# `count > 3`, `x in (1,2)`, and `f(x)` all pass while being exactly the predicates schema v1 says
# it cannot evaluate. A grammar answers "is this a plain name?", and everything else is refused
# whether or not anyone anticipated its syntax.
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
IDENTIFIER_FIELDS = ("schema", "state_field", "classification", "input_schema", "output_schema")


class Defect(Exception):
    """A fatal structural problem: validation cannot continue meaningfully past it."""


def _digest(raw: bytes) -> str:
    """SHA-256 over LF-normalized UTF-8 bytes, lowercase 64-hex.

    Normalizing line endings first is what makes the same document hash identically on Windows and
    Linux; without it a checkout setting would change a design's identity.
    """
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def _unknown(keys, allowed, label: str) -> list[str]:
    extra = sorted(set(keys) - allowed)
    return [
        f"{label}: unknown key {key!r} is rejected; an unrecognized field configures nothing "
        f"while reading as though it does"
        for key in extra
    ]


def _identifier_defects(value, label: str) -> list[str]:
    """Accept a plain name; refuse everything else, including predicates nobody enumerated."""
    if value is None:
        return []
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        return [
            f"{label}: {value!r} is not a plain identifier. Schema v1 describes a design and has "
            f"no evaluator, so a predicate, expression, or template here would certify routing "
            f"semantics that nothing can execute"
        ]
    return []


def _shortest_path(adjacency: dict[str, list[str]], start: str, goals: set[str]) -> list[str]:
    """Breadth-first shortest path, with neighbours visited in sorted order.

    Determinism matters more than speed here: a witness that changes between runs cannot be quoted
    in a review.
    """
    if start in goals:
        return [start]
    seen = {start}
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        for nxt in sorted(adjacency.get(node, ())):
            if nxt in seen:
                continue
            if nxt in goals:
                return path + [nxt]
            seen.add(nxt)
            queue.append((nxt, path + [nxt]))
    return []


def _reachable(adjacency: dict[str, list[str]], start: str) -> set[str]:
    seen = {start}
    queue = deque([start])
    while queue:
        for nxt in sorted(adjacency.get(queue.popleft(), ())):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def _find_cycle(adjacency: dict[str, list[str]], nodes: list[str]) -> list[str]:
    """Return one cycle as a node path, choosing deterministically by sorted traversal."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {node: WHITE for node in nodes}
    stack: list[str] = []

    def visit(node: str) -> list[str]:
        colour[node] = GREY
        stack.append(node)
        for nxt in sorted(adjacency.get(node, ())):
            if colour.get(nxt) == GREY:
                return stack[stack.index(nxt):] + [nxt]
            if colour.get(nxt) == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        colour[node] = BLACK
        return []

    for node in sorted(nodes):
        if colour[node] == WHITE:
            found = visit(node)
            if found:
                return found
    return []


def _validate_structure(document, root: Path) -> tuple[list[str], dict, dict]:
    """Schema-level checks. Returns (diagnostics, nodes_by_id, edges_by_identity)."""

    diagnostics: list[str] = []
    if not isinstance(document, dict):
        raise Defect("document: top level must be a JSON object")
    diagnostics += _unknown(document, TOP_LEVEL_KEYS, "document")

    if document.get("schema_version") != SCHEMA_VERSION:
        raise Defect(
            f"document: schema_version must be exactly {SCHEMA_VERSION}; this validator's "
            f"semantics are pinned to v1 and cannot speak for another version"
        )
    for required in ("name", "entry", "terminals", "zones", "nodes", "edges"):
        if required not in document:
            raise Defect(f"document: missing required key {required!r}")
    # Container shape is checked before anything iterates. Without this, a scalar or null where a
    # list belongs raised an uncaught TypeError and the CLI printed a Python traceback instead of
    # the ordered diagnostics its exit-1 contract promises -- a malformed document looked like a
    # crashed tool.
    for key in ("terminals", "zones", "nodes", "edges"):
        if not isinstance(document[key], list):
            raise Defect(
                f"document: {key!r} must be a list, not {type(document[key]).__name__}"
            )

    zones: dict[str, list[str]] = {}
    for index, zone in enumerate(document["zones"]):
        label = f"zones[{index}]"
        if not isinstance(zone, dict):
            raise Defect(f"{label}: must be an object")
        diagnostics += _unknown(zone, ZONE_KEYS, label)
        zone_id = zone.get("id")
        allows = zone.get("allows", [])
        if not isinstance(zone_id, str) or not zone_id:
            raise Defect(f"{label}: id must be a non-empty string")
        if zone_id in zones:
            diagnostics.append(f"{label}: duplicate zone id {zone_id!r}")
        if not isinstance(allows, list) or not all(isinstance(a, str) for a in allows):
            # Refuse before sorting or copying: `sorted(["b", 1])` and `list(None)` both raise, and
            # a diagnostic already appended does not help if the next line crashes the process.
            diagnostics.append(f"{label}: allows must be a list of zone-id strings")
            zones[zone_id] = []
            continue
        if allows != sorted(allows):
            diagnostics.append(
                f"{label}: allows must be a sorted list so two equivalent documents cannot "
                f"differ only by ordering"
            )
        zones[zone_id] = list(allows)

    nodes: dict[str, dict] = {}
    agent_names = {m.name for m in fleet_records.collect(root).members if m.kind == "agent"}
    fleet_tools = _fleet_tool_identifiers()

    for index, node in enumerate(document["nodes"]):
        label = f"nodes[{index}]"
        if not isinstance(node, dict):
            raise Defect(f"{label}: must be an object")
        diagnostics += _unknown(node, NODE_KEYS, label)
        node_id, kind, zone = node.get("id"), node.get("kind"), node.get("zone")
        if not isinstance(node_id, str) or not node_id:
            raise Defect(f"{label}: id must be a non-empty string")
        if node_id in nodes:
            diagnostics.append(f"{label}: duplicate node id {node_id!r}")
        if kind not in NODE_KINDS:
            diagnostics.append(
                f"{label} ({node_id}): unknown kind {kind!r}; expected one of "
                f"{sorted(NODE_KINDS)}"
            )
        if zone not in zones:
            diagnostics.append(f"{label} ({node_id}): zone {zone!r} is not declared in zones")
        for budget in BUDGET_FIELDS:
            if budget in node and not _bounded_positive_int(node[budget]):
                diagnostics.append(
                    f"{label} ({node_id}): {budget} must be a positive integer no greater than "
                    f"{MAX_BUDGET}; an unbounded budget is not a budget"
                )
        for field in ("input_schema", "output_schema"):
            diagnostics += _identifier_defects(node.get(field), f"{label} ({node_id}).{field}")
        diagnostics += _binding_defects(node, label, agent_names, fleet_tools, root)
        diagnostics += _join_shape_defects(node, label)
        nodes[node_id] = node

    edges, seen_identity = [], {}
    for index, edge in enumerate(document["edges"]):
        label = f"edges[{index}]"
        if not isinstance(edge, dict):
            raise Defect(f"{label}: must be an object")
        diagnostics += _unknown(edge, EDGE_KEYS, label)
        source, target, kind = edge.get("from"), edge.get("to"), edge.get("kind")
        if source not in nodes:
            diagnostics.append(f"{label}: from {source!r} is not a declared node")
        if target not in nodes:
            diagnostics.append(f"{label}: to {target!r} is not a declared node")
        if kind not in EDGE_KINDS:
            diagnostics.append(
                f"{label}: unknown kind {kind!r}; expected one of {sorted(EDGE_KINDS)}"
            )
        diagnostics += _edge_field_defects(edge, label, nodes)

        # Distinct enum routes stay representable; an accidental duplicate transition does not.
        route = edge.get("values") if kind == "condition" else None
        identity = (source, target, kind, json.dumps(route, sort_keys=True))
        if identity in seen_identity:
            diagnostics.append(
                f"{label}: duplicate transition {source!r}->{target!r} ({kind}) already declared "
                f"at {seen_identity[identity]}"
            )
        seen_identity[identity] = label
        edges.append(edge)

    if document["entry"] not in nodes:
        raise Defect(f"document: entry {document['entry']!r} is not a declared node")
    for terminal in document["terminals"]:
        if terminal not in nodes:
            diagnostics.append(f"document: terminal {terminal!r} is not a declared node")

    return diagnostics, nodes, {"edges": edges, "zones": zones}


def _bounded_positive_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 < value <= MAX_BUDGET


def _fleet_tool_identifiers() -> set[str]:
    """The adopted tool vocabulary, taken from the validator so one allowlist governs both."""
    import validate_fleet  # noqa: PLC0415  (deferred: keeps import cost off the common path)

    return set(validate_fleet.FLEET_TOOLS) | set(validate_fleet.FLEET_MCP_TOOLS)


def _binding_defects(node, label, agent_names, fleet_tools, root: Path) -> list[str]:
    kind, node_id = node.get("kind"), node.get("id")
    binding = node.get("binding")
    if kind in UNBOUND_KINDS:
        if binding is not None:
            return [
                f"{label} ({node_id}): kind {kind!r} takes no binding; its design role is carried "
                f"by its id, zone, and edges, and a fleet binding here would imply an executor "
                f"this document does not describe"
            ]
        return []
    if kind not in BINDING_DOMAINS:
        return []
    if not isinstance(binding, dict):
        return [f"{label} ({node_id}): kind {kind!r} requires a binding object"]
    if set(binding) != {"domain", "ref"}:
        return [f"{label} ({node_id}): binding must carry exactly 'domain' and 'ref'"]

    domain, ref = binding.get("domain"), binding.get("ref")
    allowed = BINDING_DOMAINS[kind]
    if domain not in allowed:
        return [
            f"{label} ({node_id}): kind {kind!r} accepts domain {sorted(allowed)}, not "
            f"{domain!r}; a wrong-domain binding names a target the role cannot dispatch"
        ]
    if not isinstance(ref, str) or not ref:
        return [f"{label} ({node_id}): binding ref must be a non-empty string"]

    if domain == "agent" and ref not in agent_names:
        return [
            f"{label} ({node_id}): binding ref {ref!r} is not a canonical agent in this fleet"
        ]
    if domain == "tool" and ref not in fleet_tools:
        return [
            f"{label} ({node_id}): binding ref {ref!r} is not an adopted fleet tool identifier"
        ]
    if domain == "contract-digest" and not _is_sha256(ref):
        return [
            f"{label} ({node_id}): subgraph ref must be a lowercase 64-hex SHA-256 digest"
        ]
    if domain == "repo-script":
        return _repo_script_defects(ref, f"{label} ({node_id})", root)
    return []


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _repo_script_defects(ref: str, label: str, root: Path) -> list[str]:
    """A repo-script verifier is design identity only; it is never executed.

    The containment check resolves symlinks: a reference that escapes the repository -- directly or
    through a link -- names a target outside the reviewed tree, so its witness is the resolved path
    rather than the string as written.
    """
    if Path(ref).is_absolute():
        return [f"{label}: repo-script ref {ref!r} must be repository-relative"]
    resolved = (root / ref).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return [
            f"{label}: repo-script ref {ref!r} escapes the repository root; witness: {resolved}"
        ]
    if not resolved.is_file():
        return [f"{label}: repo-script ref {ref!r} does not resolve to an existing file"]
    return []


def _join_shape_defects(node, label) -> list[str]:
    join, node_id = node.get("join"), node.get("id")
    if join is None:
        return []
    if not isinstance(join, dict):
        return [f"{label} ({node_id}): join must be an object"]
    defects = _unknown(join, JOIN_KEYS, f"{label} ({node_id}).join")
    if join.get("mode") != "all":
        defects.append(
            f"{label} ({node_id}): join mode must be 'all' in schema v1; any, quorum, and "
            f"multi-merge semantics need an executable consumer before they can be validated"
        )
    if not _bounded_positive_int(join.get("timeout_ms")):
        defects.append(
            f"{label} ({node_id}): join timeout_ms must be a positive integer no greater than "
            f"{MAX_BUDGET}"
        )
    for policy in ("on_timeout", "on_failed_predecessor"):
        if join.get(policy) != "fail":
            defects.append(
                f"{label} ({node_id}): join {policy} must be 'fail'; schema v1 is fail-closed "
                f"because no other policy has a defined executor"
            )
    return defects


def _edge_field_defects(edge, label, nodes) -> list[str]:
    defects: list[str] = []
    kind = edge.get("kind")
    for field in ("schema", "state_field", "classification"):
        defects += _identifier_defects(edge.get(field), f"{label}.{field}")

    if kind == "condition":
        if not isinstance(edge.get("state_field"), str) or not edge.get("state_field"):
            defects.append(f"{label}: condition edge requires a state_field name")
        values = edge.get("values")
        if not isinstance(values, list) or not values:
            defects.append(
                f"{label}: condition edge requires a finite, non-empty values list; an open "
                f"predicate has no evaluator in a design document"
            )
        elif any(not isinstance(v, (str, int, bool)) for v in values):
            defects.append(f"{label}: condition values must be finite scalars")
    elif "state_field" in edge or "values" in edge:
        defects.append(f"{label}: state_field/values are only meaningful on a condition edge")

    if kind == "approval":
        effect = edge.get("effect")
        target = nodes.get(edge.get("to"), {})
        if effect is None:
            defects.append(f"{label}: approval edge must name the effect it authorizes")
        elif effect != edge.get("to") or target.get("kind") != "effect":
            defects.append(
                f"{label}: approval effect {effect!r} must equal the target node id and that "
                f"node must be kind 'effect'; otherwise the approval authorizes nothing checkable"
            )
    elif "effect" in edge:
        defects.append(f"{label}: 'effect' is only meaningful on an approval edge")

    if kind != "data" and "schema" in edge:
        defects.append(f"{label}: 'schema' is only meaningful on a data edge")
    if kind not in ("data", "evidence") and "classification" in edge:
        # Every other kind-specific field says where it applies; without this one, a classification
        # on a control edge validated clean while configuring nothing.
        defects.append(
            f"{label}: 'classification' is only meaningful on a data or evidence edge"
        )
    return defects


def _validate_semantics(document, nodes, context) -> list[str]:
    """Graph-level checks. Every finding carries a deterministic shortest witness."""

    diagnostics: list[str] = []
    edges = context["edges"]
    zones = context["zones"]
    entry, terminals = document["entry"], set(document["terminals"])

    valid = [e for e in edges if e.get("from") in nodes and e.get("to") in nodes]

    transition: dict[str, list[str]] = {}
    readiness: dict[str, list[str]] = {}
    for edge in valid:
        if edge.get("kind") in TRANSITION_KINDS:
            transition.setdefault(edge["from"], []).append(edge["to"])
        if edge.get("kind") in READINESS_KINDS:
            # Readiness points from the dependency to the dependant, the direction a deadlock runs.
            readiness.setdefault(edge["from"], []).append(edge["to"])

    for name, graph in (("transition", transition), ("readiness", readiness)):
        cycle = _find_cycle(graph, sorted(nodes))
        if cycle:
            diagnostics.append(
                f"{name} graph: cycle rejected in schema v1; witness: "
                f"{' -> '.join(repr(n) for n in cycle)}"
            )

    reachable = _reachable(transition, entry)
    for node_id in sorted(set(nodes) - reachable):
        diagnostics.append(
            f"nodes[{node_id}]: unreachable from entry {entry!r}; witness: no transition path "
            f"exists from {entry!r}"
        )
    for node_id in sorted(reachable):
        if not _shortest_path(transition, node_id, terminals):
            diagnostics.append(
                f"nodes[{node_id}]: reaches no declared terminal; witness: frontier from "
                f"{node_id!r} is {sorted(_reachable(transition, node_id))}"
            )

    for index, edge in enumerate(valid):
        source_zone = nodes[edge["from"]].get("zone")
        target_zone = nodes[edge["to"]].get("zone")
        # Same-zone edges need no allow entry, but they are still subject to every other rule --
        # nesting the data-schema check under this branch silently exempted the common case.
        if source_zone != target_zone and target_zone not in zones.get(source_zone, []):
            diagnostics.append(
                f"edges[{index}]: zone {source_zone!r} does not allow {target_zone!r}; witness: "
                f"{edge['from']!r} -> {edge['to']!r} ({edge.get('kind')!r}). This proves the "
                f"declared "
                f"topology relation only, not a runtime boundary."
            )
        if edge.get("kind") == "data":
            produced = nodes[edge["from"]].get("output_schema")
            consumed = nodes[edge["to"]].get("input_schema")
            declared = edge.get("schema")
            missing = [
                name
                for name, value in (
                    ("edge schema", declared),
                    ("producer output_schema", produced),
                    ("consumer input_schema", consumed),
                )
                if not isinstance(value, str) or not value.strip()
            ]
            if missing:
                # Comparing absent values matched None against None and passed, so an entirely
                # untyped handoff earned `design-consistent`. A typed-data edge must name a type on
                # all three sides before equality means anything.
                diagnostics.append(
                    f"edges[{index}]: data edge is untyped; {', '.join(missing)} must be a "
                    f"non-empty schema identifier. An absent type on every side compared equal and "
                    f"passed, certifying a handoff with no contract at all."
                )
            elif declared != produced or declared != consumed:
                diagnostics.append(
                    f"edges[{index}]: data schema {declared!r} does not match producer "
                    f"output {produced!r} and consumer input {consumed!r}"
                )

    diagnostics += _join_topology_defects(nodes, valid)
    diagnostics += _approval_coverage_defects(nodes, valid, transition, entry)
    return diagnostics


def _join_topology_defects(nodes, edges) -> list[str]:
    incoming: dict[str, list[str]] = {}
    for edge in edges:
        if edge.get("kind") == "control":
            incoming.setdefault(edge["to"], []).append(edge["from"])
    defects = []
    for node_id, node in sorted(nodes.items()):
        predecessors = sorted(incoming.get(node_id, []))
        if len(predecessors) > 1 and node.get("join") is None:
            defects.append(
                f"nodes[{node_id}]: {len(predecessors)} required-control predecessors with no "
                f"join; the merge policy is undefined. Witness: {predecessors}"
            )
        if len(predecessors) <= 1 and node.get("join") is not None:
            defects.append(
                f"nodes[{node_id}]: join declared with {len(predecessors)} required-control "
                f"predecessor(s); a join here configures nothing"
            )
    return defects


def _approval_coverage_defects(nodes, edges, transition, entry) -> list[str]:
    """Prove every effect sits behind a human gate on ALL paths, not merely on one.

    Method: delete the approving human gates from the transition graph and re-run reachability. If
    the effect is still reachable, that surviving path IS the bypass, and it is the witness. A
    'there exists an approval edge' check would pass a design with one guarded path and one open
    one.
    """
    defects: list[str] = []
    approvals: dict[str, set[str]] = {}
    for edge in edges:
        if edge.get("kind") == "approval" and edge.get("effect") == edge.get("to"):
            if nodes.get(edge["from"], {}).get("kind") == "human":
                approvals.setdefault(edge["to"], set()).add(edge["from"])

    for node_id, node in sorted(nodes.items()):
        if node.get("kind") != "effect":
            continue
        gates = approvals.get(node_id, set())
        if not gates:
            defects.append(
                f"nodes[{node_id}]: effect has no human approval edge naming it; witness: "
                f"{_shortest_path(transition, entry, {node_id}) or [entry]}"
            )
            continue
        pruned = {
            source: [t for t in targets if t not in gates]
            for source, targets in transition.items()
            if source not in gates
        }
        bypass = _shortest_path(pruned, entry, {node_id})
        if bypass:
            defects.append(
                f"nodes[{node_id}]: effect reachable without passing an approving human gate "
                f"{sorted(gates)}; witness: {' -> '.join(repr(n) for n in bypass)}"
            )
    return defects


def _unverified_interiors(nodes) -> list[str]:
    """Subgraph boundaries stop the proof, and the summary must say so.

    Silence here would let a design read as fully covered when an unresolved interior could contain
    an unapproved effect.
    """
    return sorted(
        node["binding"]["ref"]
        for node in nodes.values()
        if node.get("kind") == "subgraph" and isinstance(node.get("binding"), dict)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("design", help="path to one workflow design JSON document")
    parser.add_argument("--root", default=".", help="repository root for binding resolution")
    args = parser.parse_args(argv)

    path = Path(args.design)
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f"{path}: unreadable design document: {error}", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    try:
        diagnostics, nodes, context = _validate_structure(document, root)
        # Semantics run only on a structurally sound document; graph checks over malformed nodes
        # produce noise that buries the real defect.
        if not diagnostics:
            diagnostics = _validate_semantics(document, nodes, context)
    except Defect as defect:
        print(f"design-inconsistent: 1 defect", file=sys.stderr)
        print(f"  - {defect}", file=sys.stderr)
        return 1

    if diagnostics:
        print(f"design-inconsistent: {len(diagnostics)} defect(s)", file=sys.stderr)
        for diagnostic in diagnostics:
            print(f"  - {diagnostic}", file=sys.stderr)
        return 1

    interiors = _unverified_interiors(nodes)
    print("design-consistent (NOT runtime-enforced)")
    print(f"  name:          {document['name']!r}")
    print(f"  design_digest: {_digest(raw)}")
    print(f"  nodes:         {len(nodes)}")
    print(f"  edges:         {len(context['edges'])}")
    if interiors:
        print(f"  unverified interiors ({len(interiors)}): approval coverage stops at each")
        for ref in interiors:
            print(f"    - subgraph {ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
