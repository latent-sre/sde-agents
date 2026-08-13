# GRAPH-002 spec — operator capability graph and workflow-design validator

**Status: approved** — approved 2026-08-12 by the operator after independent citation
verification and a zero-critical branch deep-review; revised the same day after the
operator-consumer ruling. It implements the accepted work headed "Accepted -- descriptive
compiler and contract validator" in the
[AI graph engineering decision](../../decisions/2026-07-31-ai-graph-engineering.md), as amended
2026-08-12 with the operator-consumer ruling; that record governs on conflict. Exact payloads
live in the paired [plan](../plans/graph-002-plan.md).

## Operator ruling and problem

The operator is the consumer. GRAPH-002 is not justified by an internal Python caller or by making
another repository gate invoke it. It is justified by two current operator tasks:

1. **Inspect the fleet as a graph.** Before approving topology changes, the operator needs an
   on-demand, diffable view of canonical references, preloads, direct tool declarations, guarded
   roles, host-specific authority projections, hubs, and routing-cluster overlap. The current
   validator checks individual links but emits no topology artifact.
2. **Design workflow contracts before execution exists.** The operator needs a strict linter for
   prospective contracts so node identity, joins, data dependencies, trust transitions, and
   mandatory human gates are reviewable before GRAPH-004 binds a contract to a runtime.

The first output is operator-facing review evidence. The second is a **design-consistency** result,
not proof that a host executed the design. Neither tool earns its keep by being run on every edit,
and neither becomes more useful if a PR checkbox is added solely to call it.

The dated decision snapshot recorded 140 source→target cross-reference edges and 85 direct
tool-authority edges over 30 members, graded by 8 routing clusters. The tree has changed since then.
Metric definitions must remain stable when comparing snapshots: a new surface dimension is useful
metadata, but it cannot be reported as topology drift from the old 140-edge measure.

## Scope

### 1. Operator capability graph (`scripts/capability_graph.py`)

Derive deterministic JSON and optional Mermaid from canonical `agents/` and `skills/`. Generated
output is never committed. The CLI is invoked on demand by the operator and accepts a repository
root plus explicit output paths. The root is data only: the CLI parses canonical files under it
and never imports or executes code from the inspected tree — the shared collector resolves from
the tool's own scripts directory, so one extractor version reads every tree, including a frozen
baseline checkout.

The artifact separates three things that the first draft incorrectly collapsed:

- **Authored topology:** agents, skills, namespaced references, skill preloads, and direct declared
  tool grants.
- **Host authority projection:** Claude declarations plus guard coverage; Copilot/VS Code rendered
  tool aliases and execute omission; Codex requested sandbox mode plus an explicit
  `effective_authority: unknown_or_inherited` limitation. No host's control is relabeled as another
  host's guarantee.
- **Measurement overlay:** routing-cluster co-membership and case assertions. Co-membership is not
  behavioral coverage, and the report must not call it coverage unless a case specifically asserts
  the relationship.

A prose reference does not transfer the target member's tools to the source. A source with the
`Agent` tool receives a dynamic-delegation marker and a principal boundary; the report may show a
conservative potential delegation path, but it must not merge the target principal's grants into
the caller's authority.

### 2. Six report sections, all advisory

The decision-named checks remain report sections rather than validator failures:

1. **Unreferenced components:** members with no inbound reference from a *different* member.
   Self-references do not count as external adoption. Skill preloads are **not** folded in; section
   6 reports them.

   *Implementation note (2026-08-13).* This definition was briefly widened to "no reference **and**
   no preload" because the first real-tree run listed `code-craft` — which `sde-fullstack` preloads
   — as adopted by nobody, which reads as an orphan. The union was the wrong repair: it made a
   section mean something its own name does not say, and a metric whose label and definition
   disagree is the thing baseline/candidate comparisons cannot survive. The real gap was that the
   report had no way to say "adopted, but only by preload" — section 6 now does. A preloaded skill
   therefore appears in **both** lists, and the pair is the correct picture rather than a
   contradiction: section 1 answers "does anything reference this?", section 6 answers "is it
   reached another way?".
2. **Routing-cluster relationship gaps:** reference endpoints that never appear together in a
   routing cluster, labeled as co-membership evidence only. A future behavioral case may add a
   separate measured-coverage label.
3. **Self-loops:** source equals target, with file, line, and surface context.
4. **Hub concentration:** stable source→target degree and share, with description/body surfaces
   retained as metadata rather than a changed edge identity.
5. **Host-specific potential authority paths:** direct declarations and host controls, with dynamic
   delegation shown as a principal switch and every unknown effective-authority boundary retained.
6. **Reached only by preload:** members with no inbound reference that at least one agent preloads
   through frontmatter `skills:`. A preload is the stronger adoption relation — it places the skill
   in the agent's context, where a reference only names it — so section 1 read alone would call such
   a member an orphan. Added during implementation (2026-08-13); kept as its own section rather than
   merged into section 1 so neither metric means something its name does not say.

The operator consumes these sections during topology review. No threshold or merge rule is created
in this round. A report can support a decision without every advisory becoming a gate.

### 3. Workflow-design validator (`scripts/workflow_contract.py`)

The CLI validates an explicit JSON path supplied by the operator. It does not scan a repository
`contracts/` directory, run from T0, or claim that valid design bytes govern execution. GRAPH-004
owns the future runtime binding, `contract_digest` resolution, and any committed authoritative
contract.

Schema v1 is intentionally narrower than the decision's full future envelope. Expressiveness that
has no current design consumer waits for a schema-version change instead of shipping ambiguous
semantics:

- strict known fields, unique IDs, one entry, and at least one terminal;
- the seven retained node roles, with kind-specific binding domains rather than one untyped
  `member` string;
- the seven retained edge roles, interpreted through separate transition and readiness graphs;
- finite-enum condition routes only; expressions are rejected;
- explicit fan-in configuration supporting only an `all` barrier in v1, with fail-closed timeout
  and failed-predecessor behavior;
- directed cycles rejected in v1. Bounded retries and loops require an executable consumer whose
  reset, late-arrival, checkpoint, and termination semantics can be specified;
- explicit zone declarations and allowed directed transitions. This is topology policy, not proof
  of runtime authorization;
- effect approval that originates at a human node **and covers every entry→effect transition
  path**. Merely finding an incoming approval edge is insufficient. A bypass failure includes a
  concrete witness path;
- approval coverage proven over declared nodes only: the proof stops at every `subgraph`
  boundary because v1 never resolves a contract digest, and the CLI summary names each
  unresolved subgraph reference as an unverified interior rather than passing it silently;
- every reachable node can reach a terminal, and every semantic failure includes the smallest
  deterministic witness available;
- a digest helper over LF-normalized UTF-8 bytes, useful for design identity now and compatible
  with SAFE-003's lowercase SHA-256 shape later.

Validation can prove consistency of the declared model. It cannot prove that a human identity was
authenticated, that a host enforced the design, that an LLM produced safe content, or that an
external effect occurred exactly once. Those claims require the GRAPH-004 runtime binding,
effect-broker state, and runtime provenance.

### 4. Parser reuse without mandatory wiring

The implementation may refactor `validate_fleet.py`'s existing canonical parsing into one typed
record collector used by both the validator and the graph CLI. It must not introduce a second
frontmatter/reference implementation. That parser refactor remains covered by the current
validator tests.

Neither graph derivation nor contract validation is added to `validate_fleet.py`'s T0 execution
path. Their own tests and real-tree smoke checks prove the tools; operator invocation is their
consumer. GRAPH-004 may add contract-directory wiring when a committed contract and runtime
consumer exist.

### 5. Documentation and evidence

The implementation adds AGENTS.md map rows and a short operator-use paragraph with exact on-demand
commands. It does not add a mandatory PR-template row. The outcome record captures:

- the immutable baseline and candidate topology metrics under the same edge identity;
- any separately named surface metric;
- one operator review of the real-tree capability report;
- one operator review of an explicitly supplied, non-authoritative workflow-design contract;
- standalone CLI timings and exact validation results.

## Acceptance

- A real-tree JSON report and Mermaid rendering are deterministic and operator-reviewed.
- The report keeps authored topology, host projections, and measurement evidence separate.
- Claude, Copilot/VS Code, and Codex authority examples demonstrate their distinct controls and
  unknowns; cross-references never convey authority.
- Stable edge identity reproduces the historical metric definition; any new surface metric is
  labeled as a new series rather than drift.
- Report tests assert expected records per section independently; sections need not be mutually
  exclusive.
- The capability CLI's collector import base is unaffected by the repository-root argument; a
  test parses a foreign root as data without executing its scripts.
- Contract tests cover valid design, duplicate IDs and edges, unknown keys, wrong-kind bindings,
  unreachable nodes, missing terminals, data mismatch, unsupported joins, control/condition/mixed
  readiness cycles, illegal zone transitions, missing/non-human approval, an approval-bypass path,
  a subgraph approval-boundary caveat, an escaping repo-script path, and rejection of expression
  conditions.
- Every path-oriented failure asserts its witness, so a check cannot pass while diagnosing nothing.
- The operator validates one non-authoritative design contract through the public CLI. The result
  is labeled design consistency, not runtime enforcement.
- Standard library only; no graph database or new runtime dependency.
- Existing canonical-source and generated-adapter validation remains unchanged. Zero canonical
  definitions are edited, so adapter regeneration and routing/model sessions are not owed.
- T0 and T1 pass on exact candidate bytes. Before/after standalone tool timings are recorded; no
  always-on validator-cost claim is made because no always-on graph work is added.

## Non-goals

No executor, scheduler, dynamic graph mutation, ready-state engine, runtime contract resolver,
`run_state.py` schema change, committed generated graph, committed authoritative workflow contract,
graph database, GraphRAG control plane, host-adapter behavior change, new hook or guard, or model
session. Schema v1 does not support `any`/quorum joins, cycles, late-arrival policies, cancellation,
or compensation execution.

## Rollback

The graph CLI, design validator, typed-parser refactor, tests, and documentation form one bounded
set. Reverting them restores prior behavior. No canonical definition, generated adapter, runtime
state, or committed contract changes on either implementation or rollback.

## External check (refreshed 2026-08-12)

- **Graphs are useful where structure is intentional, not universal.** [sourced] LangChain's
  [current account](https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph)
  describes graphs as a way to constrain predictable paths while warning that open-ended research
  can fit an agent harness better. It also emphasizes cycles and dynamic transitions; GRAPH-002
  therefore rejects unsupported execution semantics instead of pretending a broad static schema
  has defined them.
- **Static checking is promising when tied to the executable representation.** [sourced]
  [Agentproof](https://arxiv.org/abs/2603.20356) (arXiv:2603.20356v1, 2026-03-20)
  extracts graphs from framework objects, distinguishes structural checks from temporal policies,
  and emits witness traces. Its 18 author-constructed workflows establish feasibility, not
  production prevalence. GRAPH-002 adopts the witness-path principle but not its framework, policy
  DSL, or prevalence claims.
- **Execution semantics belong to the runtime.** [sourced] Current
  [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/concepts/workflows/builder-and-execution)
  and
  [Google ADK](https://github.com/google/adk-go/blob/362e5297b55e006589904d9364f841a85d2325e8/workflow/validation.go#L361-L385)
  material tie validation to the graph and scheduler they execute;
  [Temporal](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/workflow/workflow-definition.mdx)
  ties replay to deterministic workflow code and moves nondeterministic operations into
  activities, which are retried automatically and
  [recommended, not guaranteed](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/activities/activity-definition.mdx),
  to be idempotent. A design-only JSON file cannot inherit those guarantees.
- **No host-neutral workflow executor was found.** [verified within the reviewed source set]
  [A2A v1.0](https://github.com/a2aproject/A2A/releases/tag/v1.0.0) was released
  2026-03-12, not April; its
  [specification](https://a2a-protocol.org/latest/specification/) standardizes remote agent
  communication and task lifecycle rather than a local fleet workflow executor.
  [Agent Plugins 1.0.0](https://agentplugins.codes/) (announced 2026-08-06 by a steering
  committee of Amazon, Cursor, Microsoft, OpenAI, and Vercel, with Google joining the same day)
  is the nearest cross-host standard and is packaging only — manifest, skills, and MCP
  configuration, with no workflow or orchestration component — and Claude Code is not among its
  launch clients. Claude, Copilot, Codex, and VS Code retain distinct host contracts.
- **Optimization remains below the reopen bar.** [sourced]
  [GRAFT](https://arxiv.org/abs/2608.02353) (arXiv:2608.02353v1, 2026-08-03)
  reports a 3.85-point average improvement over MaAS under its experiment. It is a primary preprint
  but remains unreplicated and has not demonstrated a gain on this repository's eval bank.

Standing rule: cross-session durable execution, a host-neutral executor, or repeatable local
optimization gains require a decision amendment. They do not silently widen GRAPH-002.
