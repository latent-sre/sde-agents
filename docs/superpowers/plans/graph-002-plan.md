# GRAPH-002 plan — operator graph report and workflow-design checks

Paired with the drafted
[`GRAPH-002 spec`](../specs/graph-002-descriptive-capability-graph.md); operational only after
operator approval and while the round is active. The spec owns scope and rulings; this plan owns
the exact payloads and sequence.

## Frozen baseline and operator questions first

Record the baseline commit when the round activates. Before implementation:

1. Write the operator questions the first report must answer: which components are isolated or
   concentrated, which relationships changed, what each host requests or withholds, where
   authority remains unknown, and which relationship claims have actual behavioral evidence.
2. Reproduce the decision's topology measure using its original source-member→target-member edge
   identity. Record description/body occurrences as a separate `surface_occurrences` series. Do
   not compare a new surface-split count to the historical 140 and call the difference drift.
3. Capture median-of-five standalone times for the future graph CLI and contract CLI on the same
   quiet machine. No `validate_fleet.py` before/after timing is claimed because the new analyses do
   not enter its T0 path.

## Payload 1 — shared typed records

Refactor the existing canonical parser in `scripts/validate_fleet.py` into one typed collector that
returns the facts the validator already reads:

- canonical agent and skill identity, source path, description, body, and frontmatter;
- namespaced references with source, target, surface, line, and exact reference form;
- direct tool grants and skill preloads;
- guarded-agent membership;
- routing cluster members and per-case expectations.

The current validator consumes the same records so behavior stays characterized by its existing
tests. `scripts/capability_graph.py` imports that collector through the existing by-content
loading pattern pinned to the tool's own scripts directory (`Path(__file__).parent`), never the
operator-supplied repository root: the inspected tree — including a foreign or baseline
checkout — is parsed as data, and its scripts are never imported or executed. No second
YAML/frontmatter/reference parser ships.

This slice has one purpose: make the existing parse result reusable. It does not expose a new
configuration surface or make graph analysis mandatory.

## Payload 2 — `scripts/capability_graph.py`

### Artifact shape

The deterministic JSON document contains:

- `schema_version` and `extractor_version`;
- `nodes`: agents, skills, and adopted direct tool identifiers;
- `reference_edges`: stable source-member→target-member identity with sorted occurrence metadata;
- `preload_edges` and direct `tool_grants`;
- `host_authority`: one projection per supported host, each with an evidence label and limitations;
- `measurement_overlay`: cluster co-membership plus separately identified case assertions;
- `report`: the five advisory sections.

Sorted keys, sorted records, LF newlines, UTF-8, and no timestamps make baseline/candidate bytes
diffable. `--emit <path>` writes JSON; `--mermaid <path>` writes the same node/edge identity as a
view, never a second calculation.

### Host projections

- **Claude:** direct canonical tools and whether the agent is in `GUARDED_AGENT_NAMES`. Guard
  coverage is labeled Claude-only.
- **Copilot and VS Code:** the generator's existing rendered tool aliases and execute omission,
  derived through generator functions rather than reparsing generated files.
- **Codex:** generated `sandbox_mode` plus `effective_authority: unknown_or_inherited`; the report
  repeats that parent permissions, shell/MCP/skills, and managed configuration are outside the
  static projection.

No unioned fleet authority set is emitted.

### Advisory report definitions

1. `unreferenced_components`: zero inbound references where source != target.
2. `routing_cluster_relationship_gaps`: endpoints never co-listed in a cluster. The key deliberately
   avoids the word `coverage`.
3. `self_loops`: source == target, retaining every occurrence.
4. `hub_concentration`: degree/share over stable source→target edges; surface counts are metadata.
5. `host_authority_paths`: direct host projection plus dynamic delegation boundaries.

An `Agent` grant creates `delegation: dynamic`. If a conservative target set is displayed, every
path changes principal at dispatch; target grants never become caller grants. Prose cross-references
and skill preloads remain influence edges and are not traversed as authority.

### Operator consumer

AGENTS.md receives a map row and a short manual-use paragraph. The operator invokes the CLI when
reviewing fleet topology or comparing a baseline and candidate. No required PR checkbox, hidden
hook, or every-T0 call is added. The outcome record includes the operator's disposition of the
real-tree report, including a clean/no-action result if that is what the evidence shows.

## Payload 3 — `scripts/workflow_contract.py`

### Public boundary

The CLI accepts one explicit JSON path and returns:

- exit 0 plus canonical digest and summary for a valid design;
- exit 1 plus deterministic, ordered diagnostics and witness paths for an invalid design;
- exit 2 for invocation or unreadable-input errors.

It never scans `contracts/` and is not called by `validate_fleet.py`. Its output says
`design-consistent`, never `runtime-enforced`.

### Schema v1 document shape

Top level, unknown keys rejected:

- `schema_version`: exactly `1`;
- `name`, `entry`, `terminals`;
- `zones`: array of `{id, allows}` where `allows` is a sorted list of destination zone IDs;
- `nodes`;
- `edges`.

Node fields, unknown keys rejected:

- `id`, `kind`, `zone`;
- optional `input_schema`, `output_schema`, and bounded budget fields;
- kind-specific `binding` where required;
- optional `join` only on a node with multiple incoming required-control predecessors.

Binding domains are explicit:

- `agent` → `{domain: "agent", ref: <canonical agent name>}`;
- `tool` → `{domain: "tool", ref: <FLEET_TOOLS or FLEET_MCP_TOOLS identifier>}`;
- `verifier` → `{domain: "agent" | "repo-script", ref: <typed target>}`;
- `subgraph` → `{domain: "contract-digest", ref: <lowercase SHA-256>}`;
- `deterministic`, `human`, and `effect` do not accept a fleet-member binding. Their stable IDs,
  zone, and edge relationships describe the design role.

A repository-script verifier resolves to a normalized, existing repository-relative path and is
only design identity; the validator does not execute it. The resolved real path must remain
inside the repository root; a reference that escapes it, including through a symlink, is
rejected with the offending path as its witness.

Edge fields, unknown keys rejected:

- `from`, `to`, `kind`;
- `schema` on `data` edges;
- `state_field` and finite `values` on `condition` edges;
- `effect` on `approval` edges, equal to the target effect-node ID;
- optional `classification` on data/evidence edges for reporting only.

Expression strings, scripts, or embedded predicates are rejected. Duplicate identity is
`(from, to, kind, finite-route-value)` so distinct enum routes remain representable without
allowing accidental duplicate transitions.

### Join semantics

Schema v1 supports one explicit join object:

```json
{
  "mode": "all",
  "timeout_ms": 60000,
  "on_timeout": "fail",
  "on_failed_predecessor": "fail"
}
```

Only positive bounded integers and the literal fail-closed policies are accepted. `any`, quorum,
multi-merge, discriminator, late-arrival, reset, and cancellation semantics require a later schema
version with an executable consumer. A non-join node with multiple incoming required-control edges
is rejected with the predecessor list as its witness.

### Graph semantics

Build named graphs rather than treating all edges as interchangeable:

- **Transition graph:** `control`, `condition`, `failure`, and `compensation`; used for entry
  reachability and ability to reach a declared terminal.
- **Readiness graph:** required `control`, `data`, `approval`, and `evidence` dependencies plus the
  condition transition they gate; used to detect mixed dependency deadlocks.
- **Approval coverage:** for each effect, identify human predecessors whose approval edge names that
  effect, remove those human gates from the transition graph, and prove the effect is no longer
  reachable from entry. If it remains reachable, return the shortest bypass path. Coverage is
  proven over this document's node set only: the proof stops at every `subgraph` boundary, and
  the CLI summary lists each unresolved subgraph reference as an unverified interior.

Every transition and readiness cycle is rejected in v1, including condition-only and mixed
control/data cycles. Every node must be reachable from entry and reach some terminal in the
transition graph. Data-edge schema must match the producer output and consumer input identifiers.
Every cross-zone edge requires the destination in the source zone's `allows`; same-zone edges are
allowed. This zone check proves only the declared topology relation.

All path checks return a shortest deterministic witness: entry→stuck node, node→terminal frontier,
cycle, illegal zone edge, wrong-kind binding, or approval bypass.

### Digest

Expose SHA-256 over LF-normalized UTF-8 bytes, lowercase 64-hex. The CLI reports it as
`design_digest`. It is not called a resolved `contract_digest` until GRAPH-004 binds it to a run.

## Payload 4 — tests and operator acceptance

### Capability graph

- stable historical edge identity plus separate occurrence/surface series;
- unreferenced calculation excluding self-loops;
- independent expected-record assertions for all five report sections;
- cluster co-membership never labeled behavioral coverage;
- direct reference/preload never transfers tools;
- dynamic delegation changes principal and preserves target authority separately;
- Claude, Copilot/VS Code, and Codex projections retain their distinct controls and unknowns;
- JSON and Mermaid derive from one model and are byte-stable;
- the collector import base ignores the repository-root argument: a foreign root is parsed as
  data without its scripts being imported or executed;
- real-tree smoke emission.

### Workflow design

- shape: unknown keys, duplicate node IDs, duplicate edges, and expression conditions;
- bindings: valid and wrong-kind agent/tool/verifier/subgraph references, and a repo-script path
  that escapes the repository root;
- graph: unreachable, missing terminal, dead end, data mismatch, missing/unsupported join, control
  cycle, condition cycle, and mixed readiness cycle;
- zones: unknown zone and illegal directed transition;
- approvals: absent, non-human, wrong-effect scope, direct bypass, valid all-path human gate, and
  a subgraph-boundary case asserting the unverified-interior caveat appears;
- witness assertions for every graph/path failure;
- CLI exit codes, canonical digest, malformed UTF-8, and deterministic ordering.

Report fixtures assert the records relevant to each test; they do not pretend report sections are
mutually exclusive. There is no wiring mutation test because no mandatory wiring is added.

During acceptance the operator:

1. reviews the real-tree capability JSON and Mermaid;
2. supplies one non-authoritative workflow-design JSON to the CLI;
3. records whether each output answered the stated operator question;
4. records any limitation or rejected design without promoting the file into an executable
   contract.

## Sequence

1. Freeze baseline, operator questions, edge identities, and standalone timings.
2. Refactor shared typed records; run existing validator tests and T0.
3. Implement capability graph and focused tests; obtain the operator report review.
4. Implement the narrow schema-v1 design validator and focused tests; obtain the operator design
   review.
5. Add AGENTS.md map/manual-use documentation. Do not add a PR-template or T0 gate.
6. Record candidate timings and the exact operator dispositions.
7. Run T1: `python3 scripts/run_tests.py` and `claude plugin validate . --strict` on exact candidate
   bytes.

## Verification and paid boundary

Everything is offline. No routing or behavioral session is owed because canonical definitions and
descriptions do not change. Conditional PR rows:

- shared parser refactor → validator regression tests;
- new defensive/path branches → firing and witness tests;
- canonical adapters, descriptions, hooks, guards, and paid probes → N/A.

If implementation requires an executor, committed authoritative contract, runtime state change,
or new host control, stop and return to the operator; that is GRAPH-004 or a new round.

## Rollback

Revert the parser refactor, two operator CLIs, tests, and documentation as one bounded set. No
canonical member, generated adapter, runtime state, or authoritative contract is changed, so no
regeneration, migration, or recovery action is required.
