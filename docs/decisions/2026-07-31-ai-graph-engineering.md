# AI graph engineering boundary for the fleet

**Status:** Proposed -- research complete; implementation authority pending
**Date:** 2026-07-31
**Evidence snapshot:** `c02d8e12cb2c3d086890b884942908d18bcdbd17`

## Decision question

Should this repository turn its implicit fleet topology and its flat durable task state into an
explicit, typed workflow graph? If so, which graph is authoritative, what should execute it, and
which concerns must remain separate?

The proposed answer is a **repo-native, two-layer graph control plane**:

1. Derive a descriptive capability graph from the canonical `agents/` and `skills/` sources. It is
   generated evidence, never a second authored fleet.
2. Add versioned, authored workflow contracts only for bounded workflows whose order, approval,
   recovery, and evidence requirements must be enforced. Execute those contracts through the
   existing run-state, evidence, sandbox, and effect controls.

Do not adopt a universal third-party runtime, replace host-native orchestration, add a knowledge
graph, or permit self-modifying production topology in the first implementation round.

## What "AI graph engineering" means here

As of this date, **AI graph engineering is an emerging label, not a stable standard or one vendor's
API**. Current provider and framework documentation consistently describes graph-based workflows,
durable agent harnesses, typed state, and multi-agent orchestration, but does not define a shared
discipline named "AI graph engineering." This record uses the label for the engineering of explicit
relationships around an AI system: legal transitions, data flow, authority, recovery, evidence, and
evaluation.

Several different graphs are commonly conflated:

| Graph | Nodes and edges mean | Relevance to this repository |
|---|---|---|
| Workflow/control | Work units and legal transitions | Primary missing layer |
| Agent communication | Agents and the messages or delegations between them | Partly described in prompts; not machine-enforced |
| Capability/authority | Agents, skills, tools, trust zones, and grants | Already implicit and partly validated |
| State/provenance | Runs, attempts, events, artifacts, evidence, and lineage | Strong primitives; incomplete lineage |
| Knowledge/retrieval | Entities, relationships, claims, and source documents | A different problem; no current need proves it |
| Reasoning/thought | Candidate thoughts and dependencies inside inference | Experimental optimization; not a control plane |

The first four can form one operational architecture. Knowledge graphs and graph-of-thought methods
may later consume or emit artifacts, but they must not be allowed to redefine authority or legal
workflow transitions.

## External evidence

### Provider and framework convergence

Anthropic distinguishes **workflows**, whose paths are predefined in code, from **agents**, whose
models direct their own process. It recommends starting with the simplest arrangement, then adding
prompt chains, routing, parallel work, orchestrator-workers, evaluator-optimizer loops, or autonomous
agents only when evaluation proves the added complexity. It also requires environmental ground truth,
stopping conditions, sandboxed testing, and human checkpoints for open-ended agents. See
[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents).

Anthropic's production research system adds the economic and coordination evidence: independent
breadth-first work benefits from parallel agents, but their reported system uses roughly 15 times the
tokens of chat, and tightly coupled coding work has fewer parallel seams. Delegations need an
objective, output format, tool/source guidance, and boundaries; the lead retains synthesis ownership.
See
[How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system).

Anthropic's newer managed-agent architecture separates three stable interfaces: an append-only
session log, a replaceable harness, and replaceable sandboxes/tools. The session remains outside the
harness so work can resume after a crash; credentials remain outside the sandbox. This is stronger
than treating a context window, transcript summary, or writable progress file as control-plane state.
See
[Scaling Managed Agents](https://www.anthropic.com/engineering/managed-agents).

OpenAI makes two distinct multi-agent ownership choices: a handoff transfers ownership to a
specialist, while an agent-as-tool leaves the manager responsible for the final answer. OpenAI also
recommends adding specialists only when capability, policy, prompt, or trace contracts materially
change. See
[Orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration).

OpenAI's current runtime contract adds durable sessions and resumable run state, treats approval as
a pause in the same run, and places validation beside the tool that creates a side effect. Its sandbox
architecture separates the harness/control plane from model-directed compute, and its trace grading
evaluates end-to-end decisions and tool calls instead of only the final answer. See
[Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents),
[Guardrails and human review](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals),
[Sandbox Agents](https://developers.openai.com/api/docs/guides/agents/sandboxes), and
[Trace grading](https://developers.openai.com/api/docs/guides/trace-grading).

Google ADK 2.0 describes graph workflows as explicit nodes and edges that combine agents, functions,
tools, and human input. It supports sequences, conditional routes, fan-out/fan-in, nested workflows,
and cycles. Its typed node inputs and outputs are especially relevant here. Its join warning is also
important: a join that expects every predecessor can stop forever when one predecessor fails to emit
an output, so every join requires a declared failure and timeout policy. See
[Graph-based agent workflows](https://adk.dev/graphs/),
[Graph routes](https://adk.dev/graphs/routes/), and
[Data handling](https://adk.dev/graphs/data-handling/).

Microsoft Agent Framework defines workflows as directed graphs of executors and edges, validates
type compatibility and reachability when building them, and executes them in bulk-synchronous
supersteps. That model makes checkpoint boundaries deterministic, but its synchronization barrier
can also delay an independent fast path behind a slow peer. Its Durable Extension adds persisted
sessions, restart recovery, external-event waits, and distributed stateless workers. See
[Workflow builder and execution](https://learn.microsoft.com/en-us/agent-framework/workflows/workflows)
and the
[Durable Extension](https://learn.microsoft.com/en-us/agent-framework/integrations/durable-extension).

LangGraph's implementation and documentation make the replay hazard explicit: checkpoints are saved
at superstep boundaries, and resuming an interrupted node runs that node again from its beginning.
Effects before the pause therefore need idempotency keys, upserts, or another reconciliation
mechanism. This is documented in the
[Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) and implemented in
[`interrupt()`](https://github.com/langchain-ai/langgraph/blob/b2926a0ff9589c28c7e01fe7cdbb337b86d5a4b4/libs/langgraph/langgraph/types.py#L811-L831).

### Research direction

Berkeley's compound-AI-systems framing explains why the graph matters: leading systems increasingly
combine models, retrievers, tools, filters, and traditional code. This improves control and
adaptability but creates a large design space and requires traces of intermediate behavior, not just
model-level metrics. See
[The Shift from Models to Compound AI Systems](https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/).

Berkeley's 2026 data-systems perspective goes further: large agent fleets need a substrate for
durable state, coordination, concurrent work, failure handling, and result reuse. Its reported
text-to-SQL experiments found only 10--20% of multi-agent subplans distinct, which makes deduplication
and cacheable node contracts future optimization targets. It also warns against admitting raw failed
traces directly into memory; useful memory should be structured and corrective. See
[Intelligence is Free, Now What?](https://bair.berkeley.edu/blog/2026/07/07/intelligence-is-free-now-what/).

Research systems such as
[Language Agents as Optimizable Graphs](https://arxiv.org/abs/2402.16823),
[AFlow](https://arxiv.org/abs/2410.10762),
[AgentPrune](https://arxiv.org/abs/2410.02506), and
[Agent Lightning](https://arxiv.org/abs/2508.03680)
show that prompts, topology, communication edges, and trajectory credit can be optimized. Their
results justify an offline experimentation lane after a stable graph and eval bank exist. They do
not justify allowing a production fleet to rewrite its own graph: benchmark gains do not establish
authority safety, recovery correctness, or transfer to this repository's workloads.

Knowledge-graph retrieval is a separate decision. Microsoft GraphRAG extracts entities,
relationships, claims, communities, and summaries from unstructured text to improve local and global
retrieval. That is valuable when questions require whole-corpus relationship reasoning, but it does
not supply workflow durability or effect safety. See the
[GraphRAG overview](https://microsoft.github.io/graphrag/index/overview/).

## Current repository topology

The following counts were measured from the evidence snapshot named above:

- 11 canonical agents and 19 canonical skills form 30 fleet-member nodes.
- Their definitions contain 140 distinct namespaced cross-reference edges.
- Agent frontmatter contains 85 tool-authority edges.
- `sde-fullstack` has four explicit skill-preload edges.
- Eight routing clusters contain 38 member-to-cluster edges and 117 cases: 64 positive and 53
  negative. They cover 29 distinct members.

Those facts show that this repository already has a substantial **implicit static graph**. The
validator checks namespaced targets and the kind of slash-command target, but it does not emit one
topology artifact, reason about trust paths, or validate executable workflow transitions. See
[`validate_fleet.py`](../../scripts/validate_fleet.py).

The runtime control plane is also close to a graph substrate:

- [`run_state.py`](../../scripts/run_state.py) durably records runs, tasks, attempts, leases,
  immutable events, cancellation, supersession, target revisions, and evidence links.
- [`evidence_envelope.py`](../../scripts/evidence_envelope.py) defines typed producer, context,
  target, criterion, command, environment, isolation, artifact, and limitation fields.
- [`effect_broker.py`](../../scripts/effect_broker.py) binds one signed approval to one exact action,
  target, executable digest, argument vector, expiry, and nonce.
- [`verification_sandbox.py`](../../scripts/verification_sandbox.py) separates verification from the
  builder's mutable workspace.
- [`hosts.json`](../../evals/conformance/hosts.json) keeps host lanes separate and pins the one
  required OpenAI baseline to `gpt-5.6-sol`, high effort, and a read-only sandbox.
- [`multi-agent-architect.md`](../../agents/multi-agent-architect.md) already describes pipeline,
  fan-out/barrier, adversarial verification, bounded-loop, and completeness-critic patterns.

The central gap is structural: tasks under a run are a flat set. A task can be claimed while any
other task is pending or failed. There is no task dependency table, node input/output contract,
condition, join, ready-state calculation, failure edge, compensation edge, or cycle budget. A run's
`contract_digest` proves that some contract was named, but the state store does not persist or
validate the corresponding graph.

## Maturity model

Graph maturity should be assessed per dimension, not reduced to one score:

| Level | Topology and contracts | Runtime and recovery | Evidence and improvement |
|---|---|---|---|
| 0 -- prompt loop | One model loop; paths live in prose | Context is the state | Final-output spot checks |
| 1 -- composed workflow | Named chains, routers, workers, and judges | Host session plus manual handoffs | Routing and outcome evals |
| 2 -- explicit graph | Versioned nodes, typed edges, budgets, joins, and legal transitions | Ready-state and path validation | Node, edge, path, and terminal graders |
| 3 -- durable graph | Immutable graph version and typed artifacts | Checkpoint, resume, leases, cancellation, replay, and reconciliation | End-to-end trace lineage and recovery tests |
| 4 -- adaptive graph | Bounded dynamic expansion and subgraphs | Distributed scheduling and cache-safe reuse | Offline topology and policy optimization |
| 5 -- federated graph | Capability negotiation across organizations and protocols | Cross-domain identity, policy, and durable task exchange | Interoperability and ecosystem-level assurance |

This fleet is deliberately uneven. Its prompt patterns and routing suites are Level 1; its implicit
capability topology is near Level 2; its state, leases, evidence, sandbox, and approval primitives
contain important Level-3 pieces. Its **workflow execution** is still Level 1 because those durable
pieces do not enforce edges. The recommended work fills Level 2 and closes the recovery gaps needed
for Level 3 before attempting adaptive or federated behavior.

## Gaps that matter before graph execution

| Gap | Current evidence | Consequence |
|---|---|---|
| No workflow definition | Runs store only a contract digest | The legal path cannot be reconstructed or validated |
| No dependency edges | Tasks contain only `run_id`, description, status, and version | Workers may claim logically blocked work |
| No typed node handoff | Evidence is typed, ordinary outputs are not | Telephone-game loss remains a prompt concern |
| No join/failure policy | No all/any/quorum or failed-predecessor state | Fan-in can deadlock or silently skip work |
| No cycle contract | Loop limits exist only in prose | A dynamic loop can spend indefinitely |
| No graph-level trace | Evidence links to attempts, not input/output lineage edges | A final result cannot be traced through every transformation |
| No graph-level eval | Routing cases grade selection, not legal paths or terminal state | A topology regression can remain green |
| No version migration | Run-state schema version 1 rejects mismatches | Adding graph tables needs an explicit migration/rollback contract |
| Ambiguous effect crash | Broker reserves a nonce before execution and finalizes afterward | A crash after the effect but before finalization leaves an unreplayable `reserved` action with unknown outcome |
| No cross-host lifecycle API | Hosts expose different orchestration and authority controls | A claimed universal executor would be cooperative on some hosts |

The effect crash is not solvable by calling it "exactly once." For an arbitrary external system,
the safe contract is at-most-once dispatch plus an explicit **unknown-effect** state, operator or
target-system reconciliation, and target-native idempotency keys where available. A graph scheduler
must never automatically replay a reserved effect whose outcome is unknown.

## Options

### Option A -- keep the graph implicit

This has zero implementation cost, but leaves dependency order, joins, retries, budgets, and failure
paths as prompt prose. It cannot make the existing durable state enforce workflow order. Not
recommended.

### Option B -- adopt a third-party graph runtime as the fleet core

LangGraph, Google ADK, and Microsoft Agent Framework contain useful reference implementations. A
direct dependency conflicts with this repository's standard-library-only control-plane rule, adds a
runtime that none of the four supported hosts uniformly embeds, and risks turning a host-adapter
repository into an application framework. Not recommended for the core.

### Option C -- descriptive graph only

Deriving the fleet's capability graph would improve review, reachability analysis, and visualization
at low risk. It would not stop a worker from claiming a task whose predecessors are incomplete.
Useful as the first slice, insufficient as the final boundary.

### Option D -- repo-native two-layer graph control plane

Derive the static fleet graph, then add small, versioned JSON workflow contracts that reference
canonical fleet members without copying their prompts, tools, or model settings. Validate and
execute only the control-plane portion in repository-owned standard-library code. Let each host
remain responsible for actually invoking its agents, and record unsupported guarantees explicitly.

**Recommended.** It extends the controls already present, preserves host-specific authority, avoids
a second authored fleet, and can be delivered in reversible slices.

## Proposed graph contract

### Node kinds

The first schema should support only kinds with distinct execution or authority semantics:

- `deterministic` -- trusted code that transforms typed input without model discretion;
- `agent` -- one canonical agent identity invoked by a host driver;
- `tool` -- a bounded tool call with a declared authority and trust zone;
- `human` -- an input or decision pause in the same run;
- `verifier` -- an independent attempt whose evidence gates a transition;
- `effect` -- an approved action executed only through the effect broker;
- `subgraph` -- a versioned nested workflow exposed through a typed boundary.

Nodes should declare an input schema identifier, output schema identifier, trust zone, timeout,
retry policy, idempotency class, evidence requirements, and token/tool/iteration budget where
applicable. A graph must reference canonical agent and skill names; it must not duplicate their
instructions, tools, or model aliases.

### Edge kinds

Edges should distinguish what they authorize rather than use one generic arrow:

- `control` -- a predecessor's terminal state enables a successor;
- `data` -- a typed artifact or value becomes a successor input;
- `condition` -- a finite, validated route based on typed state or evidence;
- `approval` -- an operator decision enables a bounded effect;
- `evidence` -- a criterion must pass before the successor becomes ready;
- `failure` -- a declared failed, timed-out, or inconclusive path;
- `compensation` -- a separately approved recovery action, never an assumed rollback.

Fan-in must declare `all`, `any`, or `quorum`, plus timeout and missing/failed-predecessor behavior.
Cycles must be explicit and carry both a machine-enforced maximum iteration count and a terminal
condition. Arbitrary executable expressions in edge conditions should be rejected; the first
version should use finite enums over typed state.

### Required invariants

1. The graph is immutable for a run and bound to `contract_digest`; dynamic expansion creates a new
   versioned proposal or append-only patch event, not an in-place topology rewrite.
2. A task is claimable only when its incoming control, approval, and evidence edges are satisfied.
3. Node output is persisted as a digest-bound artifact before downstream nodes become ready.
4. Cancellation and supersession dominate late completion across the entire graph.
5. Every cycle has an iteration ceiling; every join has failure and timeout behavior.
6. Every effect routes through the broker, and an unknown effect blocks automatic continuation until
   reconciled.
7. The validator rejects unreachable nodes, duplicate edges, incompatible data schemas, missing
   terminals, illegal trust-zone paths, and effects without approval edges.
8. Credentials remain outside worker and sandbox reach; graph data never grants authority by prose.
9. Traces preserve graph version, node, edge, attempt, artifact, evidence, cost, latency, and model
   observation separately from the final outcome.
10. OpenAI model baselines in this program use `gpt-5.6-sol` only. Anthropic sources inform the
    design, but no Anthropic or Opus baseline is part of this decision.

## Recommended implementation sequence

### Phase 0 -- descriptive compiler and contract validator

- Derive a machine-readable capability graph from canonical agent and skill definitions.
- Add a standard-library workflow-contract parser and semantic validator.
- Validate reachability, node IDs, canonical member references, typed schema compatibility,
  terminals, cycle budgets, join policies, trust paths, and effect approval edges.
- Export JSON and optional Mermaid as review evidence; generated output is not committed as a second
  source unless a later decision names a consumer that needs it.

This phase does not execute models and therefore needs no model baseline.

### Phase 1 -- one bounded executable pilot

Use the existing `sre-tool` lifecycle as the pilot because it already names requirements, design,
build, review, verification, evidence, and deploy gates. Compile a small workflow whose simulated
path is:

`requirements -> design gate -> build -> review -> verify -> terminal`

The review or verification failure route may return to build no more than the existing retry cap.
Safety-critical work adds the independent security-review node. A deploy effect requires a human
approval edge and the effect broker. The first acceptance run should use deterministic fake host
drivers; live host execution follows only after state transitions, replay, cancellation, and effect
ambiguity are proven.

### Phase 2 -- graph traces and evals

- Add graders for node contract compliance, illegal edge traversal, terminal outcome, evidence
  completeness, cost, latency, duplicate work, and path efficiency.
- Keep outcome grading separate from trace grading and run multiple trials for model-driven nodes.
- Add cross-host lanes only for guarantees each host can actually expose.
- Use `gpt-5.6-sol` for every OpenAI/Codex model baseline in this program.

### Phase 3 -- controlled dynamic expansion

Permit an orchestrator to propose child nodes and edges only inside operator-set type, count, token,
tool, trust-zone, and depth limits. Validate the proposal before activation and persist its graph
version. An agent may propose an effect node; it may not create its approval.

### Phase 4 -- future experiments

- Cache or deduplicate deterministic and research nodes by graph version, input digest, target
  revision, and policy version.
- Test communication-edge pruning and topology search offline against the eval bank.
- Consider A2A Agent Cards generated from canonical role metadata if the fleet later exposes remote
  agents. A2A complements MCP by describing agent capability and task exchange; it does not replace
  local authority controls. See
  [Google's protocol guide](https://developers.googleblog.com/en/developers-guide-to-ai-agent-protocols/).
- Consider structured corrective memory only after admission, provenance, conflict, and deletion
  policies exist.
- Consider GraphRAG only if a measured retrieval workload needs relationship- or whole-corpus
  reasoning that the current local-first references cannot provide.

## Acceptance evidence for an implementation round

An accepted implementation spec should require all of the following:

- a fixture or mutation test for every new validator invariant;
- graph parser/validator tests for valid, unreachable, incompatible, cyclic, unbounded, deadlocked,
  trust-violating, and unapproved-effect graphs;
- state migration forward and rollback tests against a real schema-v1 database;
- concurrency tests proving only ready tasks can be leased once;
- restart tests at each checkpoint and between effect reservation, dispatch, evidence persistence,
  and completion;
- cancellation and supersession tests with late workers;
- an end-to-end synthetic pilot showing success, retry, failure, timeout, human pause/resume,
  unknown-effect reconciliation, and final evidence lineage;
- unchanged canonical-source and generated-adapter validation;
- no new runtime dependency;
- paired routing or model runs only when agent/skill descriptions or model behavior are changed,
  with every OpenAI baseline explicitly using `gpt-5.6-sol`.

## Rejected and deferred applications

- **A universal cross-host scheduler now:** rejected because the hosts do not expose one common,
  enforceable lifecycle and authority interface.
- **A graph database now:** rejected because JSON plus SQLite is sufficient for the current graph
  size and keeps the control plane standard-library only.
- **GraphRAG as fleet memory:** deferred until a measured retrieval problem exists and memory
  admission can distinguish sourced facts, corrections, and failed traces.
- **Graph-of-thought prompting by default:** deferred; it is an inference strategy, not durable
  orchestration, and must earn its cost on task-specific evals.
- **Automatic production topology optimization:** rejected; AFlow, GPTSwarm, AgentPrune, and Agent
  Lightning motivate an offline proposal lane, not self-authorizing mutation.
- **One global shared state object for every node:** rejected because it collapses least-context and
  trust-zone boundaries. Edges should carry the smallest typed artifact a successor needs.
- **Exactly-once claims for arbitrary effects:** rejected because the broker and an external target
  cannot commit atomically without target support.

## Consequences if accepted

- `agents/` and `skills/` remain the only authored fleet-member definitions.
- Workflow contracts become a new authored control-flow source, but may only reference canonical
  members; they cannot restate member authority or prompt content.
- `run_state.py` becomes a graph scheduler projection and requires an explicit schema migration.
- The effect broker gains an unknown-outcome reconciliation contract before effect nodes execute.
- The fleet validator gains graph semantic checks and negative fixtures.
- Host adapters remain host-specific; unsupported runtime controls stay labeled cooperative.
- The first round is a control-plane and deterministic-state round, not a model-quality round.

## Reopen triggers

- A supported host exposes a stable, enforceable workflow lifecycle API that can replace part of the
  repo-owned scheduler.
- A workflow framework becomes a host-neutral standard already present on all supported hosts.
- A measured retrieval workload demonstrates that a knowledge graph materially improves grounded
  answers over local files and ordinary search.
- Effect targets adopt idempotency or transaction protocols strong enough to narrow the
  unknown-effect state.
- Offline graph optimization shows repeatable gains across the fleet's own eval bank with acceptable
  token, latency, and safety cost.
