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
import hashlib
import json
import re
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
        "A skill's disallowed-tools removes write tools while it is active, but Bash can still "
        "mutate, so the read-only posture it declares is cooperative rather than enforced.",
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


def _adopted_tool_vocabulary() -> set[str]:
    """The fleet's adopted tool identifiers, taken from the validator so one allowlist governs."""
    import validate_fleet  # noqa: PLC0415  (deferred; keeps import cost off the common path)

    return set(validate_fleet.FLEET_TOOLS) | set(validate_fleet.FLEET_MCP_TOOLS)


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
    # The edge identity comes from fleet_records, never from a second filter here. Re-deriving it
    # inline meant two places encoded the same rule, so a future change applied to one and not the
    # other would reproduce exactly the two-reports-disagreeing failure that module exists to
    # prevent.
    identity = fleet_records.stable_edges(records)

    grouped: dict[tuple[str, str], list] = defaultdict(list)
    for reference in records.references:
        key = (reference.source, reference.target)
        if reference.in_core_definition and key in identity:
            grouped[key].append(reference)

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
    # `nodes.tools` names CAPABILITIES, so only identifiers this fleet actually adopts belong
    # there. An inspected tree no validator has run on can declare `Wrte` or `Bash(git diff:*)`,
    # and promoting those made the artifact assert a capability that does not exist -- and
    # contradict its own Copilot projection, which drops them.
    vocabulary = _adopted_tool_vocabulary()
    declared = {tool for tools in tool_grants.values() for tool in tools}
    adopted_tools = sorted(declared & vocabulary)
    unadopted_tools = sorted(declared - vocabulary)

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
            if skill in {m.name for m in records.skills}
        ],
        # A typo'd or removed skill in an agent's `skills:` is a declaration, not adoption. Emitting
        # it as a topology edge invented a phantom Mermaid node and let an invalid checkout read as
        # internally consistent; unresolved declarations are named instead.
        "preload_targets_unresolved": sorted(
            {
                f"{source} -> {skill}"
                for source, skill in fleet_records.preload_edges(records)
                if skill not in {m.name for m in records.skills}
            }
        ),
        "reference_edges": reference_edges,
        "report": _report(records, reference_edges, tool_grants, inherits_all),
        "schema_version": SCHEMA_VERSION,
        # The separate occurrence series the plan promises, covering the WHOLE authored reference
        # surface -- including the 60 occurrences in bundled references/ files that the stable edge
        # identity deliberately excludes. Without it those occurrences appear in no baseline diff at
        # all. Never differenced against the edge count: different things, on purpose.
        "surface_occurrences": fleet_records.surface_occurrences(records),
        "bundled_reference_occurrences": sorted(
            (
                {
                    "line": r.line,
                    "path": _relative(r.path, records.root),
                    "source": r.source,
                    "target": r.target,
                }
                for r in records.references
                if not r.in_core_definition
                and r.target in {m.name for m in records.members}
            ),
            key=lambda o: (o["path"], o["line"], o["target"]),
        ),
        "tool_grants": tool_grants,
        "tool_authority_undeclared": inherits_all,
        "tool_identifiers_unadopted": unadopted_tools,
        # A definition the parser refused contributes no node but may still contribute reference
        # occurrences, so omitting it entirely lets an operator diffing a baseline read a broken
        # file as a deleted member.
        "unreadable_definitions": sorted(
            _relative(path, records.root) for path in records.unparseable
        ),
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
        if is_guarded is None:
            # The Copilot alias set depends on guard membership, so an unreadable roster makes it
            # underivable. `bool(None)` is False, which silently answered "not guarded" and emitted
            # a definite `execute_available: true` for every Bash-holding agent -- a security claim
            # made on the strength of a file that was never opened, contradicting the Claude
            # projection in the same document.
            copilot[agent.name] = {
                "execute_available": None,
                "execute_withheld_by_guard": None,
                "tool_aliases": None,
                "projection": "unavailable_unknown_guard_roster",
            }
        else:
            aliases = adapters._copilot_tools(agent.fields, guarded=is_guarded)
            # "Never held Bash" and "the guard removed execute" are different facts about a role.
            # One flag for both would report `researcher` -- which has no shell tool at all -- as
            # having had execute taken away, describing a control never applied to it.
            copilot[agent.name] = {
                "execute_available": "execute" in aliases,
                "execute_withheld_by_guard": is_guarded and "Bash" in agent.tools,
                "tool_aliases": aliases,
            }
        writes = set(agent.tools) & set(adapters._validator_module().WRITE_TOOLS)
        codex[agent.name] = {
            "effective_authority": "unknown_or_inherited",
            "requested_sandbox_mode": "workspace-write" if writes else "read-only",
        }

    # Skills carry their own control -- `disallowed-tools` -- and the adapter generator strips it
    # for portable hosts. A report covering only agent tools would answer "what does each host
    # withhold?" while omitting the only authority a directly-invoked skill surface declares.
    declaring = {
        skill.name: sorted(skill.disallowed_tools)
        for skill in sorted(records.skills, key=lambda m: m.name)
        if skill.disallowed_tools
    }
    claude_skills = {
        name: {"disallowed_tools": tools, "enforcement": "declared_claude_side"}
        for name, tools in declaring.items()
    }
    portable_skills = {
        name: {
            "disallowed_tools": None,
            "enforcement": "not_projected",
            "projection": "tool_deny_stripped_for_portable_host",
        }
        for name in declaring
    }

    return {
        "claude": {
            "agents": claude,
            "skills": claude_skills,
            "limitations": HOST_LIMITATIONS["claude"],
        },
        "codex": {
            "agents": codex,
            "skills": portable_skills,
            "limitations": HOST_LIMITATIONS["codex"],
        },
        "copilot": {
            "agents": copilot,
            "skills": portable_skills,
            "limitations": HOST_LIMITATIONS["copilot"],
        },
        "vscode": {
            "agents": copilot,
            "skills": portable_skills,
            "limitations": HOST_LIMITATIONS["vscode"],
        },
    }


def _measurement_overlay(records) -> dict:
    """Cluster co-membership and case assertions, kept separable on purpose.

    Sharing a cluster means someone graded two members together. Only `expect_fires` asserts that a
    specific member should be summoned, so the two are never merged into one 'coverage' number.
    """
    co_membership: dict[str, list[str]] = {}
    asserted: dict[str, list[str]] = defaultdict(list)
    prohibited: dict[str, list[str]] = defaultdict(list)
    duplicates: set[str] = set()
    for cluster in sorted(records.clusters, key=lambda c: c.name):
        if cluster.name in co_membership:
            # Two files declaring one cluster string silently overwrote the first membership while
            # the gap computation still used both records -- an internally inconsistent overlay from
            # a tree the fleet validator passes, since it checks each file independently.
            duplicates.add(cluster.name)
        co_membership[cluster.name] = sorted(cluster.members)
        for case in cluster.cases:
            for member in case.expect_fires:
                asserted[member].append(f"{cluster.name}:{case.case_id}")
            if case.polarity == "negative":
                # An omitted expect_not_fires means the whole cluster is prohibited for that
                # prompt, so the assertion is normalized from membership rather than lost.
                targets = case.expect_not_fires or tuple(cluster.members)
                for member in targets:
                    prohibited[member].append(f"{cluster.name}:{case.case_id}")
    return {
        "cluster_co_membership": co_membership,
        "members_with_case_assertions": {
            member: sorted(cases) for member, cases in sorted(asserted.items())
        },
        # A corrupt cluster file and a deliberately removed one produce the same absence unless the
        # unreadable ones are named, and this overlay exists to be diffed across two trees.
        "unreadable_clusters": sorted(
            _relative(path, records.root) for path in records.unreadable_clusters
        ),
        "duplicate_cluster_identities": sorted(duplicates),
        "members_with_negative_assertions": {
            member: sorted(cases) for member, cases in sorted(prohibited.items())
        },
    }


def _incomplete_note(inherits_all: list[str], unreadable: tuple, clusters: tuple = ()) -> str:
    """Say what the report could not establish, in the report itself."""
    notes = []
    if inherits_all:
        notes.append(
            " INCOMPLETE: one or more agents declare no tools and therefore inherit every tool; "
            "their host projections are unavailable, not least-privileged."
        )
    if unreadable:
        notes.append(
            f" INCOMPLETE: {len(unreadable)} definition(s) could not be parsed and contribute no "
            f"node; see unreadable_definitions before reading an absence as a removal."
        )
    if clusters:
        notes.append(
            f" INCOMPLETE: {len(clusters)} routing-cluster file(s) could not be read; see "
            f"measurement_overlay.unreadable_clusters before reading missing evidence as removed."
        )
    return "".join(notes)


def _report(
    records, reference_edges: list[dict], tool_grants: dict, inherits_all: list[str]
) -> dict:
    """The six advisory sections. Every one is an observation; none is a verdict."""

    member_names = sorted(m.name for m in records.members)
    external = {(e["source"], e["target"]) for e in reference_edges if e["source"] != e["target"]}
    external_inbound = defaultdict(int)
    for _, target in external:
        external_inbound[target] += 1

    # Preloads are inbound adoption too, and a STRONGER form than a reference: the skill is placed
    # in the agent's context rather than merely named. Counting references alone reported
    # `code-craft` as adopted by nobody while `sde-fullstack` preloaded it -- a false positive that
    # would send an operator to question a skill that is actively in use.
    preload_inbound = defaultdict(int)
    for source, skill in fleet_records.preload_edges(records):
        if source != skill:
            preload_inbound[skill] += 1

    # Strictly what the section is named and what the approved spec defines: no inbound REFERENCE
    # from a different member. Self-references are excluded because a file naming itself is not
    # adoption by anyone. Preloads are deliberately NOT folded in -- `reached_only_by_preload`
    # below answers that question under its own name, so an operator sees both facts instead of a
    # metric whose meaning has drifted from its label.
    unreferenced = [name for name in member_names if external_inbound[name] == 0]
    # Surfaced separately so the distinction stays visible instead of being silently folded away:
    # these members ARE adopted, and only a reference-only measure would call them orphans.
    preload_only = [
        name for name in member_names
        if external_inbound[name] == 0 and preload_inbound[name] > 0
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

    # Hub degree is computed over the FULL stable identity, self-loops included, because that is
    # the measure it claims to summarize; totalling only external edges gave rows summing to 153
    # against an identity of 155. `external` stays the basis for adoption and gap checks, where a
    # member naming itself is deliberately not evidence.
    identity = {(e["source"], e["target"]) for e in reference_edges}
    total = len(identity) or 1
    inbound = defaultdict(int)
    for _, target in identity:
        inbound[target] += 1
    outbound = defaultdict(int)
    for source, _ in identity:
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
            + _incomplete_note(
                inherits_all, records.unparseable, records.unreadable_clusters
            ),
        },
        "hub_concentration": hub,
        "reached_only_by_preload": preload_only,
        "routing_cluster_relationship_gaps": gaps,
        "self_loops": self_loops,
        "unreferenced_components": unreferenced,
    }


_MERMAID_SAFE_RE = re.compile(r"[^A-Za-z0-9_]")


def _mermaid_id(name: str) -> str:
    """A Mermaid-safe, COLLISION-FREE node id derived from a member name.

    Member names come from the INSPECTED tree, and this tool records without judging -- `NAME_RE`
    is enforced by validate_fleet.py, which has not necessarily run on a foreign or baseline
    checkout. Interpolating such a name raw let `;` and other Mermaid syntax reach the diagram as
    statements the graph never derived. The JSON path is unaffected because json.dumps escapes.

    Sanitizing alone was not enough: `a;b` and `a?b` both reduce to `a_b`, which merged two distinct
    JSON nodes into one visual node and redirected their edges through it -- a view that contradicts
    the identity it claims to show. A short digest of the original name is appended whenever
    sanitizing changed anything, so distinct members stay distinct.
    """
    safe = _MERMAID_SAFE_RE.sub("_", name) or "_"
    if safe == name:
        return safe
    return f"{safe}_{hashlib.sha256(name.encode('utf-8')).hexdigest()[:8]}"


def _mermaid_label(name: str) -> str:
    """Neutralize a label so it cannot terminate its own quoted string.

    Mermaid does not honor backslash escapes inside a quoted label -- `\\"` still ends the string --
    so the quote is replaced with the `#quot;` entity Mermaid does document. Newlines are flattened
    because a line break would end the statement regardless of quoting.
    """
    return (
        name.replace('"', "#quot;")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def render_mermaid(document: dict) -> str:
    """A VIEW of the MEMBER topology the JSON carries -- never a second calculation.

    Members and their reference/preload edges only. `nodes.tools` is deliberately not rendered:
    adding 29 tool nodes to a 31-member diagram costs the readability the diagram exists for, and
    the JSON already carries tool authority in a form built to be read rather than looked at. The
    docstring says "member topology" rather than "the same node identity" because the earlier
    wording claimed a completeness this view does not have.
    """
    lines = ["graph LR"]
    for name in document["nodes"]["agents"]:
        lines.append(f'  {_mermaid_id(name)}["{_mermaid_label(name)}"]')
    for name in document["nodes"]["skills"]:
        lines.append(f'  {_mermaid_id(name)}(["{_mermaid_label(name)}"])')
    for edge in document["reference_edges"]:
        lines.append(f'  {_mermaid_id(edge["source"])} --> {_mermaid_id(edge["target"])}')
    for edge in document["preload_edges"]:
        lines.append(
            f'  {_mermaid_id(edge["source"])} -.preload.-> {_mermaid_id(edge["skill"])}'
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
    manifest = root / ".claude-plugin" / "plugin.json"
    plugin_name = ""
    if manifest.is_file():
        try:
            parsed = json.loads(fleet_records.read_text(manifest))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            parsed = None
        # An inspected checkout is arbitrary: a non-object manifest made `.get` raise, and a
        # non-string `name` produced an impossible grammar that exited 0 with every namespaced edge
        # missing -- a confident blank topology. Both take the refusal path below instead.
        if isinstance(parsed, dict) and isinstance(parsed.get("name"), str):
            plugin_name = parsed["name"].strip()
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

    # Both artifacts are promised; writing them to one path let the Mermaid render silently
    # destroy the JSON and still exit 0. Equivalent spellings resolve to the same file, so the
    # comparison is on the resolved path, not the string.
    if args.emit and args.mermaid:
        if Path(args.emit).resolve() == Path(args.mermaid).resolve():
            print(
                f"--emit and --mermaid resolve to the same file "
                f"({Path(args.emit).resolve()}); writing both would destroy one",
                file=sys.stderr,
            )
            return 2
    # A destination that cannot be written is an invocation problem and exits 2, the same class as
    # an unreadable manifest. Letting OSError escape printed a traceback for a mistyped path.
    try:
        if args.emit:
            _write(Path(args.emit), payload)
        if args.mermaid:
            _write(Path(args.mermaid), render_mermaid(document))
    except OSError as error:
        print(f"cannot write output: {error}", file=sys.stderr)
        return 2
    if not args.emit and not args.mermaid:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
