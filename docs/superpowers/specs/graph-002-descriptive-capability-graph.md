# GRAPH-002 spec — descriptive capability graph and workflow-contract validator

**Status: drafted** — 2026-08-12; awaiting operator approval. A drafted spec starts no round and
carries no implementation authority (`docs/README.md`). Implements the accepted work headed
"Accepted -- descriptive compiler and contract validator" in the
[AI graph engineering decision](../../decisions/2026-07-31-ai-graph-engineering.md); that record
governs on conflict. Exact payloads live in the paired [plan](../plans/graph-002-plan.md).

## Problem

Two gaps, both named by the accepted decision:

1. **The fleet's topology is implicit.** At the decision's evidence snapshot the canonical
   definitions carried 140 distinct namespaced cross-reference edges and 85 tool-authority edges
   over 30 members, graded by 8 routing clusters — and the validator checks references one at a
   time, emitting no topology artifact. An edge change is reviewable only as a prose diff, and
   routing evals grade edges only as rates over runs. This tree already differs from the snapshot
   (11 agents, 20 skills, 10 routing clusters), which is the point: nothing measures the drift.
2. **The retained graph-contract design has no parser or validator.** GRAPH-004 (trigger-bound)
   would author the first real contract, and the decision requires canonical-member reference
   validation to ship "in the first descriptive slice, not with the executor" — a contract that
   silently survives a member rename is a second source in waiting.

No executor is in scope. The decision's reopen triggers for graph execution remain closed as of
this draft (re-checked 2026-08-12; see the external-check note at the end).

## Scope

**1. Derived capability graph** (`scripts/capability_graph.py`). Standard-library derivation from
the canonical `agents/` and `skills/` sources: nodes are agents, skills, and the adopted tool
surface; edges are namespaced cross-references (deduplicated per source, target, and surface),
tool grants, skill preloads, and read-only-guard coverage. Emission is on demand (JSON, optional
Mermaid) as review evidence with deterministic, byte-stable output. Generated output is never
committed — the decision names no consumer for a committed artifact, and an uncommitted emission
cannot become a second source.

**2. The five decision-named graph checks, as a deterministic report.** Components no other
member references, routing edges no eval cluster covers, self-loops, hub concentration, and a
prompt-surface→tool reachability view. Ruling made by this spec: **all five are report sections,
not validator failures.** Evidence for the ruling: the current tree legitimately trips the naive
self-loop definition twice (`host-onboard` and `service-onboard` name their own slash command in
their descriptions), and description-routed members legitimately have zero inbound reference
edges. A hard rule on either would need prose-intent heuristics that misfire silently — the
failure class the validator exists to catch, not to add. The report earns its keep through the
description-edit playbook and the PR gates table: a topology-affecting edit diffs the report
between baseline and candidate trees the same way routing rates are diffed.

**3. Workflow-contract parser and semantic validator** (`scripts/workflow_contract.py`). JSON
contracts, schema v1 frozen to the decision's retained design: the seven node kinds
(`deterministic`, `agent`, `tool`, `human`, `verifier`, `effect`, `subgraph`) and seven edge
kinds (`control`, `data`, `condition`, `approval`, `evidence`, `failure`, `compensation`).
Semantic checks, each mapped to the decision's invariants: unique node IDs; a declared entry and
at least one terminal, every node reachable from entry and reaching a terminal; duplicate edges
rejected; member references resolve against the current canonical fleet; data edges carry schema
identifiers and producer/consumer identifiers must agree (v1 compares identifiers — JSON Schema
evaluation is executor-adjacent machinery with no consumer yet); every cycle is declared with a
machine-enforceable iteration ceiling and a terminal condition; every fan-in declares
`all`/`any`/`quorum` plus timeout and failed-predecessor behavior; trust-zone transitions are
legal per the contract's declared zones; every `effect` node has an incoming `approval` edge; and
`condition` edges route on finite enums over typed state — expressions are rejected. The
canonical contract digest is SHA-256 over LF-normalized UTF-8 bytes, matching SAFE-003's required
lowercase 64-hex `contract_digest` shape, so GRAPH-004 can later bind a run to a contract
document without rework. This round changes nothing in `run_state.py`.

**4. Fleet-validator wiring.** `validate_fleet.py` runs the graph derivation in every T0 pass (a
derivation failure is loud, not latent) and validates every contract found under `contracts/`.
That directory does not exist and is not created by this round — the code path is proven by
fixtures, and the directory appears when GRAPH-004 authors the first real contract. An empty
directory shipped now would be a mechanism without a demonstrated consumer.

**5. Docs.** AGENTS.md map rows for both new modules land with the implementation; the roadmap
entry, this spec, and the plan retire to an outcome record when the round closes (rule 4).

## Acceptance

From the decision's acceptance-evidence list, verbatim where it is specific:

- A fixture or mutation test for every new validator invariant.
- Parser/validator tests for valid, unreachable, incompatible, cyclic, unbounded, deadlocked,
  trust-violating, and unapproved-effect contracts.
- Canonical-source and generated-adapter validation unchanged; **zero canonical definitions
  edited**, so no adapter regeneration and no routing runs are owed.
- Standard library only; no new runtime dependency.
- Error messages in the validator's what-broke-and-why-it-would-have-been-silent register.
- The five report sections exercised against fixture repositories that each trip exactly one
  check (`tests/support.py` isolation idiom), plus one smoke test that the real tree derives and
  emits without error.
- T0 proportionality (TIER-001): derivation reuses the validator's existing parse of the
  canonical sources — no second frontmatter parser ships — and before/after `validate_fleet.py`
  wall time is measured on the same machine and recorded in the outcome record.
- No model sessions run; no model baselines owed (per the decision).

## Non-goals

No executor, scheduler, or ready-state computation; no `run_state.py` schema change
(`contract_digest` resolution stays with GRAPH-004); no committed generated graph; no authored
real contract; no canonical agent or skill edits; no third-party dependency; no knowledge-graph
or retrieval work; no host-adapter behavior change; no new hook, guard, or configuration surface.

## Rollback

Two new standard-library modules, their tests and fixtures, the validator wiring, and the doc
rows — one bounded revert restores prior validator behavior byte-for-byte. No canonical
definition or generated adapter is touched, so no regeneration is owed on revert.

## External check (2026-08-12)

A fresh external sweep of the "graph engineering" discourse and the decision's reopen-trigger
maturity conditions ran with this draft (2026-08-12). Findings, labeled per the decision's
convention:

- **No reopen trigger fires.** [verified] Claude Code workflow resume remains session-scoped —
  the official workflows doc still states "If you exit Claude Code while a workflow is running,
  the next session starts the workflow fresh" (code.claude.com/docs/en/workflows, fetched
  2026-08-12). [verified] The changelog through CLI 2.1.228 shows only workflow hardening since
  the probe-verified 2.1.220: a 2.1.223 sandbox fix (dynamic `import()` escape closed) and a
  restricted-subagent-model warning. No hook contract for workflow-spawned agents was documented.
- **No host-neutral workflow standard emerged.** [sourced] The four supported hosts diverged
  further in this window (Claude workflows, Copilot `/fleet` and saveable agent workflows, Codex
  0.147.0 portable Agent Plugins, ADK Go 2.0's graph runtime); A2A v1.0 (April 2026) remains
  server-side, absent from local CLI hosts.
- **The term consolidated as a label, not a discipline.** [sourced] LangChain's "3 Years of
  Graph Engineering with LangGraph" (~2026-07-22) adopted the phrase while framing it as a
  rebrand of existing LangGraph practice; no Anthropic publication uses the term, so the
  decision's misattribution finding stands. Secondary content-farm coverage continues through
  mid-August.
- **One watch-signal, below the trigger bar.** [unverified] arXiv 2608.02353 (early Aug 2026)
  claims offline workflow-graph optimization beats prior optimizers with gains that transfer
  across executors — a single unreplicated result read only via search summaries. The
  offline-optimization trigger requires repeatable gains on this repository's own eval bank;
  re-check if independent replication appears.

Standing rule: had the sweep found cross-session durable resume or a host-neutral standard, the
correct response would be a decision amendment, not a wider GRAPH-002 — this spec's boundary
stays descriptive-only.
