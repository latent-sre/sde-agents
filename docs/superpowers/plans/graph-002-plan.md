# GRAPH-002 plan — derivation, report, and contract-validator payloads

Paired with the drafted
[`GRAPH-002 spec`](../specs/graph-002-descriptive-capability-graph.md); operational only after
the operator approves that spec and while the round is active. The spec owns scope and rulings;
this plan owns exact payloads and sequence.

## Frozen baseline and measurement first

Record the baseline commit when the round activates. Before any code lands:

1. Re-derive the decision's topology counts on that commit — members, cross-reference edges by
   surface, tool-authority edges, preload edges, routing-cluster membership and case counts — and
   record them beside the decision's 2026-07-31 snapshot (11 agents, 19 skills, 140
   cross-reference edges, 85 tool edges, 8 clusters / 117 cases). Drift is expected and recorded;
   the decision record is dated evidence and is not edited.
2. Capture baseline `validate_fleet.py` wall time (median of five runs, same machine, quiet tree)
   for the T0 proportionality comparison the spec requires.

## Payload 1 — `scripts/capability_graph.py`

- **One parser.** `validate_fleet.py` stays the single frontmatter/reference parser. Derivation
  consumes its parsed member records; the standalone emission CLI loads `validate_fleet.py` by
  path through the same by-content module-loading seam the validator already uses for the guard.
  No second parser ships — divergent parsing is how the graph would silently disagree with the
  checks.
- **Node model:** agents, skills, and the adopted tool surface (`FLEET_TOOLS` /
  `FLEET_MCP_TOOLS`). **Edge model:** cross-references (`sde-agents:<member>` and
  `/sde-agents:<member>` occurrences, deduplicated per source file, target, and surface —
  description vs body), tool grants from agent frontmatter, `skills:` preloads, and
  `GUARDED_AGENT_NAMES` coverage from `scripts/readonly-guard.py`.
- **Report sections**, definitions fixed here so the tests can pin them:
  1. *Unreferenced components* — members with zero inbound cross-reference edges.
  2. *Eval-uncovered routing edges* — cross-reference edges whose endpoints never co-occur in one
     routing cluster's member set.
  3. *Self-loops* — edges with source == target, each with file and line context.
  4. *Hub concentration* — inbound/outbound degree per member and each hub's share of total
     edges, sorted; no threshold, reporting only.
  5. *Prompt-surface→tool reachability* — for each entry surface (user slash command, agent
     description routing), the transitive closure over preload, cross-reference, and Agent-spawn
     edges to tool grants, each path labeled by its edge kinds.
- **Emission:** `--emit <path>` writes JSON; `--mermaid <path>` optional. Output is deterministic
  and byte-stable (sorted keys, no timestamps) so a baseline/candidate diff is meaningful.
  Nothing is committed.

## Payload 2 — `scripts/workflow_contract.py`

- **Document shape (schema v1):** top-level `schema_version` (must be 1), `name`, `entry`,
  `terminals`, optional `zones`, `nodes`, `edges`, optional `cycles`. Node fields: `id`, `kind`
  (the seven decision kinds), `member` (required for `agent`/`tool`/`verifier` kinds; must
  resolve against the canonical fleet), `input_schema`/`output_schema` identifiers, `zone`,
  optional budget fields. Edge fields: `from`, `to`, `kind` (the seven decision kinds), `schema`
  on `data` edges, enum route table on `condition` edges. Fan-in nodes (more than one incoming
  `control` edge) require a join declaration: `all`/`any`/`quorum` (+ `quorum_n`), `timeout`, and
  `on_failed_predecessor`. Cycles are declared explicitly with member nodes, `max_iterations`,
  and a terminal condition; any undeclared cycle in the control graph is rejected as unbounded.
- **Validation order:** shape first (unknown keys rejected — the plugin-frontmatter lesson: a
  typo must not silently configure nothing), then references, then graph semantics (reachability,
  terminals, duplicates, joins, cycles, zones, effect/approval), so each error names the earliest
  broken layer. Every message states what broke and why it would have failed silently at
  execution time.
- **Digest helper:** SHA-256 over LF-normalized UTF-8 bytes, lowercase 64-hex, matching
  SAFE-003's `contract_digest` shape. Exposed as a function and a CLI flag; nothing writes to
  `run_state.py`.

## Payload 3 — wiring, fixtures, tests

- `validate_fleet.py` gains: derivation in every T0 pass (failure is a validator error), and
  contract validation over `contracts/*.json` when that directory exists. The directory is not
  created; fixtures prove the path.
- Contract fixtures under `tests/fixtures/contracts/`, one per acceptance class: `valid`,
  `unreachable`, `incompatible` (data-edge schema mismatch), `cyclic` (undeclared cycle),
  `unbounded` (declared cycle, no ceiling), `deadlocked` (fan-in without join/failed-predecessor
  policy), `trust-violating`, `unapproved-effect`, plus `duplicate-edge`, `missing-terminal`, and
  `unknown-member` for the remaining invariants.
- Report fixtures: minimal repositories via the `tests/support.py` isolation idiom, each tripping
  exactly one report section; one smoke test derives and emits from the real tree.
- Mutation test in `tests/test_validate_fleet.py`: copy the repository, sever the
  contract-validation wiring (and separately the derivation call), and watch the suite fail —
  proving the wiring non-vacuous per the defensive-branch rule.
- New test modules: `tests/test_capability_graph.py`, `tests/test_workflow_contract.py`.

## Sequence

1. Baseline measurements (above).
2. Payload 1 with its tests; T0 green.
3. Payload 2 with its fixtures and tests; T0 green.
4. Payload 3 wiring plus mutation tests; T0 green.
5. AGENTS.md map rows for both modules; inventory refresh not owed (no member added).
6. After-timing measurement; record beside the baseline.
7. T1: `python3 scripts/run_tests.py` and `claude plugin validate . --strict` on the exact
   candidate bytes.

## Verification and paid boundary

Everything here is offline. No model session is part of implementation or acceptance; no routing
or behavioral runs are owed because zero canonical definitions change. PR gates table rows owed:
new validator rules → tests proven to fail without them; everything else N/A. If any step turns
out to require editing a canonical definition, that is a scope change: stop and return to the
operator rather than absorbing it.

## Rollback

Revert the round's commits as one bounded set: two modules, tests, fixtures, wiring, and doc
rows. No canonical definition or generated adapter changes, so no regeneration is owed on revert.
