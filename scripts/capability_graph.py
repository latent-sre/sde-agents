#!/usr/bin/env python3
"""Derive an operator-facing capability graph from a fleet checkout.

This is a REPORT, not a gate. It is invoked on demand when reviewing topology or comparing a
baseline against a candidate; nothing here runs in T0, in CI, or behind a PR checkbox, and no
section produces a pass/fail verdict. An advisory that quietly became a gate would make every
topology observation a merge blocker, which this round's plan explicitly refuses.

Three things are kept apart on purpose, because the first draft of this design collapsed them:

* **Authored topology** -- what the canonical files declare.
* **Host authority projection** -- what each host requests or withholds. No host's control is
  reported as another host's guarantee, and no unioned "fleet authority" set is emitted, because
  no such thing exists at runtime.
* **Measurement overlay** -- routing-cluster co-membership and case assertions. Co-membership is
  NOT behavioral coverage of a relationship; only a case naming a member asserts anything.

The inspected tree is DATA. This tool's own collector and generator are loaded from the directory
this file lives in, never from the tree under inspection, so pointing it at a foreign or frozen
baseline checkout cannot execute that tree's code.

Usage:
    python3 scripts/capability_graph.py --root . --emit graph.json --mermaid graph.mmd
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fleet_records  # noqa: E402  (sibling module; scripts/ is not a package)
import generate_platform_adapters as adapters  # noqa: E402

SCHEMA_VERSION = 1
# Bumped when the extractor's OUTPUT SHAPE OR SEMANTICS change, so two artifacts that disagree can
# be told apart from two trees that disagree. Not a release version and not a timestamp: the
# document must be byte-diffable between a baseline and a candidate run.
EXTRACTOR_VERSION = "graph-002.1"

# Every host control this tool can state statically, with what it cannot see. A projection without
# its limitations reads as a completed authority model, which is the failure this separation exists
# to prevent.
HOST_LIMITATIONS = {
    "claude": [
        "Guard coverage is Claude-only: it rests on the PreToolUse payload's agent_type, which no "
        "other host supplies.",
        "A cooperative Write boundary stated in prose is not a tool-layer control.",
    ],
    "copilot": [
        "Tool aliases are the host's vocabulary; an unknown alias is ignored rather than refused, "
        "so a plausible-looking name is not a restriction until the host accepts it.",
    ],
    "vscode": [
        "Shares Copilot's alias vocabulary and the same unknown-alias behavior.",
    ],
    "codex": [
        "effective_authority is unknown_or_inherited: parent permissions, shell, MCP, skills, and "
        "managed configuration are outside this static projection.",
        "sandbox_mode is what the generated profile REQUESTS, not what the host granted.",
    ],
}


def _relative(path: Path, root: Path) -> str:
    """Repository-relative POSIX path.

    Absolute paths made every occurrence differ between two checkouts of identical bytes, which
    defeats the baseline-vs-candidate comparison this artifact exists for and embeds the operator's
    directory layout in a shareable report. Identity is the file's place in the tree, not the
    machine it was read on.
    """
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        # Outside the inspected root: keep it distinguishable rather than silently rewriting it
        # into something that looks repository-relative.
        return path.as_posix()


def _sorted_occurrences(references, root: Path) -> list[dict]:
    """Occurrence metadata for one stable edge, ordered so two runs diff cleanly."""
    return [
        {
            "line": reference.line,
            "path": _relative(reference.path, root),
            "raw": reference.raw,
            "slash_command": reference.is_slash_command,
            "surface": reference.surface,
        }
        for reference in sorted(
            references, key=lambda r: (_relative(r.path, root), r.line, r.raw)
        )
    ]


def build_document(records) -> dict:
    """Assemble the deterministic report document from already-collected records."""

    member_names = {m.name for m in records.members}
    core_references = [
        r for r in records.references if r.in_core_definition and r.target in member_names
    ]

    grouped: dict[tuple[str, str], list] = defaultdict(list)
    for reference in core_references:
        grouped[(reference.source, reference.target)].append(reference)

    reference_edges = [
        {
            "occurrences": _sorted_occurrences(group, records.root),
            "source": source,
            "surface_occurrences": {
                surface: sum(1 for r in group if r.surface == surface)
                for surface in sorted({r.surface for r in group})
            },
            "target": target,
        }
        for (source, target), group in sorted(grouped.items())
    ]

    # An agent with no `tools:` inherits EVERY tool. Listing it with an empty grant would render
    # maximal authority as least privilege -- the exact trust-boundary error this report exists to
    # surface. Declared grants and inherited-all authority are therefore separate keys, so a
    # consumer cannot read one as the other by accident.
    declared = [a for a in sorted(records.agents, key=lambda m: m.name) if a.declares_tools]
    inherits_all = sorted(a.name for a in records.agents if not a.declares_tools)
    tool_grants = {agent.name: sorted(agent.tools) for agent in declared}
    adopted_tools = sorted({tool for tools in tool_grants.values() for tool in tools})

    return {
        "extractor_version": EXTRACTOR_VERSION,
        "host_authority": _host_authority(records),
        "measurement_overlay": _measurement_overlay(records),
        "nodes": {
            "agents": sorted(m.name for m in records.agents),
            "skills": sorted(m.name for m in records.skills),
            "tools": adopted_tools,
        },
        "preload_edges": [
            {"skill": skill, "source": source}
            for source, skill in sorted(fleet_records.preload_edges(records))
        ],
        "reference_edges": reference_edges,
        "report": _report(records, reference_edges, tool_grants, inherits_all),
        "schema_version": SCHEMA_VERSION,
        "tool_grants": tool_grants,
        "tool_authority_undeclared": inherits_all,
    }


def _host_authority(records) -> dict:
    """One projection per host. Never unioned, never cross-attributed."""

    guarded = records.guarded_agents
    # None means the roster could not be read. Reporting "not guarded" here would state a security
    # property on the strength of a file that was never opened.
    guard_evidence = "unknown" if guarded is None else "parsed_from_guard_roster"

    claude, copilot, codex = {}, {}, {}
    for agent in sorted(records.agents, key=lambda m: m.name):
        is_guarded = None if guarded is None else agent.name in guarded
        claude[agent.name] = {
            "authority": "declared" if agent.declares_tools else "inherits_all",
            "declared_tools": sorted(agent.tools) if agent.declares_tools else None,
            "guard_evidence": guard_evidence,
            "guarded": is_guarded,
        }
        if not agent.declares_tools:
            # Nothing downstream can be projected from an absent declaration: the alias mapping and
            # the sandbox decision both read a tool list that does not exist. Emitting the
            # least-privilege answer each would produce is worse than emitting none.
            copilot[agent.name] = {
                "execute_available": None,
                "execute_withheld_by_guard": None,
                "tool_aliases": None,
                "projection": "unavailable_no_declared_tools",
            }
            codex[agent.name] = {
                "effective_authority": "unknown_or_inherited",
                "requested_sandbox_mode": None,
                "projection": "unavailable_no_declared_tools",
            }
            continue
        # Derived through the generator's own mapping rather than by reparsing generated files, so
        # one alias table governs both the adapters and this report.
        aliases = adapters._copilot_tools(agent.fields, guarded=bool(is_guarded))
        # "Never held Bash" and "the guard removed execute" are different facts about a role. One
        # flag for both would report `researcher` -- which has no shell tool at all -- as having had
        # execute taken away, describing a control that was never applied to it.
        copilot[agent.name] = {
            "execute_available": "execute" in aliases,
            "execute_withheld_by_guard": bool(is_guarded) and "Bash" in agent.tools,
            "tool_aliases": aliases,
        }
        writes = set(agent.tools) & set(adapters._validator_module().WRITE_TOOLS)
        codex[agent.name] = {
            "effective_authority": "unknown_or_inherited",
            "requested_sandbox_mode": "workspace-write" if writes else "read-only",
        }

    return {
        "claude": {"agents": claude, "limitations": HOST_LIMITATIONS["claude"]},
        "codex": {"agents": codex, "limitations": HOST_LIMITATIONS["codex"]},
        "copilot": {"agents": copilot, "limitations": HOST_LIMITATIONS["copilot"]},
        "vscode": {"agents": copilot, "limitations": HOST_LIMITATIONS["vscode"]},
    }


def _measurement_overlay(records) -> dict:
    """Cluster co-membership and case assertions, kept separable on purpose.

    Sharing a cluster means someone graded two members together. Only `expect_fires` asserts that a
    specific member should be summoned, so the two are never merged into one 'coverage' number.
    """
    co_membership: dict[str, list[str]] = {}
    asserted: dict[str, list[str]] = defaultdict(list)
    for cluster in sorted(records.clusters, key=lambda c: c.name):
        co_membership[cluster.name] = sorted(cluster.members)
        for case in cluster.cases:
            for member in case.expect_fires:
                asserted[member].append(f"{cluster.name}:{case.case_id}")
    return {
        "cluster_co_membership": co_membership,
        "members_with_case_assertions": {
            member: sorted(cases) for member, cases in sorted(asserted.items())
        },
    }


def _report(
    records, reference_edges: list[dict], tool_grants: dict, inherits_all: list[str]
) -> dict:
    """The five advisory sections. Every one is an observation; none is a verdict."""

    member_names = sorted(m.name for m in records.members)
    external = {(e["source"], e["target"]) for e in reference_edges if e["source"] != e["target"]}
    inbound = defaultdict(int)
    for _, target in external:
        inbound[target] += 1

    # Preloads are inbound adoption too, and a STRONGER form than a reference: the skill is placed
    # in the agent's context rather than merely named. Counting references alone reported
    # `code-craft` as adopted by nobody while `sde-fullstack` preloaded it -- a false positive that
    # would send an operator to question a skill that is actively in use.
    preload_inbound = defaultdict(int)
    for source, skill in fleet_records.preload_edges(records):
        if source != skill:
            preload_inbound[skill] += 1

    # A member nothing else reaches, by either route. Self-references are excluded because a file
    # naming itself is not adoption by anyone.
    unreferenced = [
        name
        for name in member_names
        if inbound[name] == 0 and preload_inbound[name] == 0
    ]
    # Surfaced separately so the distinction stays visible instead of being silently folded away:
    # these members ARE adopted, and only a reference-only measure would call them orphans.
    preload_only = [
        name for name in member_names if inbound[name] == 0 and preload_inbound[name] > 0
    ]

    clustered_pairs = set()
    for cluster in records.clusters:
        members = sorted(cluster.members)
        for i, left in enumerate(members):
            for right in members[i + 1:]:
                clustered_pairs.add((left, right))
    gaps = [
        {"source": source, "target": target}
        for source, target in sorted(external)
        if (min(source, target), max(source, target)) not in clustered_pairs
    ]

    self_loops = [
        {"occurrences": edge["occurrences"], "source": edge["source"]}
        for edge in reference_edges
        if edge["source"] == edge["target"]
    ]

    total = len(external) or 1
    outbound = defaultdict(int)
    for source, _ in external:
        outbound[source] += 1
    # Degree and share stay on the stable reference identity so they remain comparable to the dated
    # measure; preload inbound rides alongside as its own column rather than being added in, which
    # would silently redefine the series.
    hub = [
        {
            "inbound_degree": inbound[name],
            "inbound_share": round(inbound[name] / total, 4),
            "member": name,
            "outbound_degree": outbound[name],
            "preload_inbound_degree": preload_inbound[name],
        }
        for name in member_names
        if inbound[name] or outbound[name] or preload_inbound[name]
    ]
    hub.sort(key=lambda row: (-row["inbound_degree"], row["member"]))

    delegation = {
        agent: {
            "boundary": "target grants never become caller grants; every dispatch changes "
            "principal",
            "delegation": "dynamic",
        }
        for agent, tools in sorted(tool_grants.items())
        if "Agent" in tools
    }

    return {
        "host_authority_paths": {
            "dynamic_delegation": delegation,
            # Surfaced in the report, not only in the data: an agent inheriting every tool is the
            # largest authority statement the artifact can make, and burying it in a key an
            # operator has to go looking for would defeat reading the report at all.
            "inherits_all_tools": inherits_all,
            "note": "Prose cross-references and skill preloads are influence edges and are not "
            "traversed as authority."
            + (
                " INCOMPLETE: one or more agents declare no tools and therefore inherit every "
                "tool; their host projections are unavailable, not least-privileged."
                if inherits_all
                else ""
            ),
        },
        "hub_concentration": hub,
        "reached_only_by_preload": preload_only,
        "routing_cluster_relationship_gaps": gaps,
        "self_loops": self_loops,
        "unreferenced_components": unreferenced,
    }


def render_mermaid(document: dict) -> str:
    """A VIEW of the same node/edge identity the JSON carries -- never a second calculation."""
    lines = ["graph LR"]
    for name in document["nodes"]["agents"]:
        lines.append(f'  {name.replace("-", "_")}["{name}"]')
    for name in document["nodes"]["skills"]:
        lines.append(f'  {name.replace("-", "_")}(["{name}"])')
    for edge in document["reference_edges"]:
        lines.append(
            f'  {edge["source"].replace("-", "_")} --> {edge["target"].replace("-", "_")}'
        )
    for edge in document["preload_edges"]:
        lines.append(
            f'  {edge["source"].replace("-", "_")} -.preload.-> {edge["skill"].replace("-", "_")}'
        )
    return "\n".join(lines) + "\n"


def _write(path: Path, text: str) -> None:
    # newline="" keeps LF on every platform; the default would emit CRLF on Windows and make two
    # runs of the same tree differ by line ending alone.
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=".", help="repository root to inspect (data only)")
    parser.add_argument("--emit", help="write the JSON document to this path")
    parser.add_argument("--mermaid", help="write the Mermaid view to this path")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    manifest = root / "plugin.json"
    plugin_name = ""
    if manifest.is_file():
        try:
            plugin_name = str(json.loads(fleet_records.read_text(manifest)).get("name", ""))
        except (json.JSONDecodeError, UnicodeDecodeError):
            plugin_name = ""
    if not plugin_name:
        # Without the plugin name there is no namespaced-reference grammar, so the graph would
        # report zero edges for a tree that has many. Refuse rather than emit a confident blank.
        print(
            f"{root}: no readable plugin.json name; cannot resolve reference grammar",
            file=sys.stderr,
        )
        return 1

    records = fleet_records.collect(root, plugin_name)
    document = build_document(records)
    payload = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    if args.emit:
        _write(Path(args.emit), payload)
    if args.mermaid:
        _write(Path(args.mermaid), render_mermaid(document))
    if not args.emit and not args.mermaid:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
