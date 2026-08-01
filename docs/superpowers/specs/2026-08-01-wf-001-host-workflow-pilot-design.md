# WF-001 — host-workflow pilot round (design spec)

**Status:** Approved scope for the active round — governs what the paired plan may implement.
Implementation authority: GRAPH-001 was **accepted by the operator 2026-08-01** (recorded in the
decision record and roadmap) — the round did not begin executing until that acceptance landed.
Amended 2026-08-01 after an adversarial review; dispositions in the
[review record](../../archive/2026-08/wf-001-adversarial-review-2026-08-01.md)
**Date:** 2026-08-01
**Base:** branch `agent/accept-plugin-deployment-mode` (`ece06d6`); everything here builds on the
revised [`GRAPH-001 decision`](../../decisions/2026-07-31-ai-graph-engineering.md) and the accepted
[`deployment-mode decision`](../../decisions/2026-07-29-deployment-mode.md)
**Probe evidence:** five headless runs against a clean `origin/main` worktree, CLI 2.1.220,
2026-08-01 (transcripts in the session scratchpad; the durable copy of each verified fact is the
probe extension this round ships)

## Decision question

GRAPH-001 deferred graph *execution* behind reopen triggers. Trigger #2 reads: "Claude Code's
native workflow orchestration stabilizes into an API a plugin can pin to — at which point the
question becomes *adopting* the host layer, not building a parallel one." This round's research
and probes show that trigger is now **partially fired**: plugin-shipped workflows are documented,
GA, and pin-plus-probe verifiable — but not yet mature. The round therefore does two things:

1. **Revise GRAPH-001** to record the new evidence and resolve trigger #2 into a bounded response.
2. **Implement WF-001**, the smallest host-layer adoption that produces real evidence: one pilot
   workflow, schema-typed packet contracts, a probe extension, and the platform boundary.

It does not build any part of the deferred execution phases (scheduler, run-state migration,
graph graders, dynamic expansion), and it does not touch SAFE-002 or CTX-001, which proceed as
GRAPH-001 already defines them.

## Evidence this round rests on

### Probe-verified platform facts (CLI 2.1.220, 2026-08-01)

| Fact | Evidence |
|---|---|
| A plugin `workflows/` script resolves as `/sde-agents:<name>` | Workflow launched from a `--plugin-dir` worktree carrying only the probe script |
| `agent(prompt, {agentType: 'sde-agents:code-reviewer'})` spawns the canonical fleet agent | Spawned reviewer executed Bash as itself against the probe target |
| PreToolUse fires for workflow-spawned agents, `agent_type` is plugin-namespaced | Instrumented hook logged `agent_type: 'sde-agents:code-reviewer'` on each Bash call |
| The read-only guard enforces inside workflows — including under `bypassPermissions` | Guard denied non-allowlisted `sort` with its own message; allowlisted `cat` passed |
| Default workflow agents carry `agent_type: 'workflow-subagent'` and are unguarded | Control agent ran both commands; hook logged the distinct identity |
| `agent({schema})` returns a validated object; retry ceiling 5, then abort | Validated objects returned; ceiling per CHANGELOG v2.1.186 |
| Headless invocation requires `bypassPermissions` or interactive approval | Plain `-p` runs blocked with "Review dynamic workflow before running" |

### Field cautions (external research, cited in the GRAPH-001 revision)

- Anthropic's own plugins ship zero workflow scripts; no third-party plugin shipping native
  `workflows/` was found. The fleet is early — the pilot is deliberately small because of it.
- Resume never survives exiting Claude Code; an open upstream bug (#65796) silently restarts
  long workflows after auto-compaction. The pilot is minutes-long so neither weakness applies.
- Token cost is the dominant practitioner complaint; the docs recommend validating on a slice.
- Format-forcing costs reasoning accuracy when a model must reason and serialize simultaneously;
  the mitigation consensus is reason free-form, schema only the final payload.
- No equivalent orchestration primitive exists on Copilot CLI, VS Code agent plugins, or Codex
  CLI; the multi-host convention for one-host features is omit-and-document, never emulate.

## Deliverables and acceptance boundaries

### D1 — GRAPH-001 revision

Four edits, nothing else:

1. Replace the "live host fact" paragraph with the probe-verified facts above, cited to the
   changelog and the probe extension.
2. Add a resolution note to reopen trigger #2: *pinnable* is demonstrated (CLI pin + probe, the
   same mechanism the guard's `agent_type` dependency uses); *stable* is not claimed (two-month-old
   feature, active bugfix stream, weak resume, no first-party dogfooding). The authorized response
   is this bounded pilot, not the deferred execution phases.
3. Add WF-001 to the accepted work, scoped exactly as this spec's D2–D5.
4. Extend the accepted descriptive-layer item's acceptance evidence with the fleet-graph checks
   this round's research converged on independently: unreferenced components, routing edges no
   eval cluster covers, self-loops, hub-concentration reporting, and a reachability view of which
   prompt surfaces can reach which tools. (The descriptive layer itself is not built this round.)

One sentence records the run-state boundary: the pilot does not write `run_state.py`; if the
deferred execution phases reopen, that spec decides integration. Workflow scripts cannot touch the
filesystem, so integration would have to route through agent prompts — prose-granted authority,
which invariant #8 already prohibits.

### D2 — pilot workflow: `workflows/deep-review.js`

A multi-agent review pipeline: guarded diff scope → two parallel `sde-agents:code-reviewer`
lanes via `agentType` — one correctness pass, one seeded with a security-only threat model —
→ schema-validated packets → a deterministic merge record in script code (a missing or invalid
packet yields a structured inconclusive verdict naming the failed lane; a confirmed P0/P1 forces
do-not-merge; a dirty tree caps the record at the reviewer's own PROVISIONAL form — gates are
code, not prose).

Two structural rules the adversarial review forced explicit (both were defects in the first
draft): **every stage with agency runs under the guarded reviewer identity** — the scope stage
included, because default workflow agents are unguarded (`workflow-subagent`, probe run 5) and a
prompt-level "read-only" instruction is authority by prose; and
**`application-security-auditor` is deliberately not in the pipeline** — its own negative routing
excludes branch diffs ("Not for a PR/branch diff — use `sde-agents:code-reviewer`") and it holds
no Bash, so the security lane uses the second-reviewer fallback `sre-tool` already documents.
Every agent await is fail-closed: schema-retry exhaustion or a lane crash returns a structured
inconclusive verdict naming the failed lane, never a bare runtime error. The merge record binds
to the scope stage's recorded head SHA.

Why this pilot and not an `sre-tool` conversion: it is read-heavy and parallelizable (the one
regime the multi-agent economics favor), short-lived (resume and compaction weaknesses cannot
bite), exercises guarded agents where the guard is now probe-proven, and complements `/code-review`
without replacing anything.

Input contract: the workflow takes an optional `args` ref and reviews the diff of the working
branch against it, defaulting to the merge base with `main` — the same scope a reviewer gets today.

Boundaries: no writes to the reviewed repository; no `run_state.py` integration; total agent count
small enough that the default medium size guideline is never approached.

### D3 — packet schemas

JSON Schemas for the two review packets, derived from the canonical prose: findings array (file,
line, claim, severity enum (P0–P3, the reviewer's canonical scale), evidence-label enum pinned
verbatim to the canonical `[verified]/[sourced]/[unverified]` stems, failure scenario), the
reviewer's canonical verdict enum — approve / approve-with-nits / request-changes /
provisional-commit-and-re-review, so a dirty tree cannot receive an unconditional approval — and
a required "what was not checked" field. Schema constrains only the final packet — the agents' free-prose
reasoning stays untouched, matching both the fleet's existing pattern and the format-tax evidence.

Schemas live as constants inside the workflow script — the runtime offers no shared-schema
mechanism, and a separate schema file would be a second source the script could drift from.

The prose packets remain canonical. A validator rule pins the schema enums to the canonical stems
so schema and prose cannot drift apart silently — without it, a stem edit in one place ships a
contract mismatch that nothing errors on until a workflow run fails five retries deep.

### D4 — probe extension

`scripts/probe_plugin.py` gains a workflow section codifying the five probe runs as standing
checks: namespaced workflow resolution, `agentType` spawn of a canonical agent, guard denial
inside a workflow-spawned guarded agent (attempt-and-deny oracle, not agent prose), and the
`workflow-subagent` identity assumption. Owed at every CLI pin bump, exactly like the existing
guard probes — the pin makes the contract deterministic; the probe makes a silent upstream rename
loud.

### D5 — platform boundary

`workflows/` is Claude-only. The generator excludes it from all three adapter trees; a validator
rule fails any non-Claude adapter that references a workflow; README and AGENTS.md carry the
omit-and-document note. This extends the existing convention (Claude-only guard hook, Copilot
execute-capability omission) rather than inventing a new one.

Mechanics the probe settled: `workflows/` is auto-discovered at the plugin root — `plugin.json`
needs no new field. The round ships a new component class, so plugin versions bump minor
(1.4.0 → 1.5.0), aligned across every host manifest per the standing manifest rule.

### D6 — roadmap

WF-001 enters the roadmap with this spec as its source and the acceptance evidence below. The
deferred fleet-graph tooling and routing-eval metric upgrades are recorded against their owning
items (descriptive layer; EVAL follow-ons), not silently dropped.

## Explicitly out of scope

- Any edit to `agents/*.md` or `skills/*/SKILL.md` — no reductions, no grafts. CTX-001 owns prose
  posture and proceeds separately, eval-gated, exactly as GRAPH-001 defines it.
- The deferred execution phases: repo-owned scheduler, `run_state.py` schema changes, graph
  graders, dynamic expansion.
- SAFE-002 implementation (accepted in GRAPH-001; separate work).
- Graph databases, knowledge graphs, third-party orchestration runtimes, routing changes — all
  remain rejected or trigger-bound per GRAPH-001.
- A second workflow. One pilot produces the evidence; the outcome record adjudicates whether more
  flows earn conversion.

## Test modes and model policy

- Unit tests and validator rules run offline — no sessions, no model, same as every existing gate.
- Workflow probe sessions run headless with `--permission-mode bypassPermissions`: the interactive
  workflow-review gate blocks plain `-p` sessions regardless of the settings allowlist (probe runs
  2 vs 3), the probe target is a throwaway repository the harness creates and deletes, and run 5
  proved the guard still enforces under bypass — bypass removes permission prompts, not hooks.
  Existing non-workflow probe sections keep their current invocation unchanged.
- Probe and pilot acceptance sessions launch on **sonnet**. Both pilot agents declare
  `model: inherit`, so the session model is the control; Fable capacity is not spent on probes or
  the pilot. The outcome record states the session model alongside the recorded token cost.

## Acceptance evidence

- Standard gates green: `generate_platform_adapters.py --check`, `validate_fleet.py`, the unit
  suite, `claude plugin validate . --strict`.
- New validator rules each carry a fixture under `tests/fixtures/` that violates exactly that rule
  (schema-stem drift; non-Claude adapter referencing a workflow), plus tests that fail without the
  change.
- Extended probe run green on CLI 2.1.220, including the guard-inside-workflow denial.
- The pilot workflow executed end-to-end on a real diff, with token cost and wall time recorded in
  the round's outcome record — the number the next conversion decision needs.
- No model baselines owed beyond the probe's own sessions; any Codex/OpenAI baseline in this
  program remains `gpt-5.6-sol` per SAFE-001.

## Most likely to be wrong

1. **The headless approval gate.** The probe ran workflows under `bypassPermissions`; if a future
   CLI closes that path without adding a scoped approval mechanism, the probe extension breaks
   loudly (by design) but the pilot's CI story would need rework.
2. **`workflow-subagent` identity.** The guard's correctness for default workflow agents rests on
   that string staying out of `GUARDED_AGENT_NAMES` matching; the probe records the assumption,
   but an upstream rename to something matching a guarded pattern would over-block rather than
   under-block (fail-closed, but noisy).
3. **Schema-retry economics.** Five retries on a large review packet is up to five full reviewer
   passes in the worst case; if the pilot shows retries firing at all, the schema is too strict or
   the packet prompt too loose, and the outcome record must say which.
