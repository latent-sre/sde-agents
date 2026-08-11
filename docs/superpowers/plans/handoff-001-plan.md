# HANDOFF-001 plan — lean producer/consumer handoff

Paired with the approved
[`HANDOFF-001 spec`](../specs/handoff-001-onboarding-handoff-packet.md); operational only while
this round is active. The operator reactivated the item on 2026-08-11 with an explicit
proportionality ruling: restore the evidence-carrying behavior, not PR #108's global packet schema
and gates.

## Frozen baseline and success

Baseline `4777df9cc97b5a855c2c7ba693ce990e4d6ee1c2` has no onboarding handoff producer, no builder
echo, and 58 behavioral contracts. PR #108's candidate carried the behavior but also added a
thirteen-slot linter/validator stack and more than one thousand lines of tests before its paired
live runs or first-artifact measurement happened; `b1af3a3` removed that unproven machinery and
honestly reset the roadmap to `ready`.

This round succeeds when:

- onboarding discovery that crosses into a builder context carries every task-specific constraint
  the approved spec names, without carrying secrets or authority;
- `sde-fullstack` echoes the load-bearing constraints before editing, rejects a regression encoded
  in either code or tests, and returns missing/conflicting packet fields as a material fork;
- a simple bounded build with no discovered constraint stays on the existing short prompt path;
- the requested first Tier-1 artifact can precede non-blocking lifecycle lanes without reporting
  those lanes complete or silently dropping their owners;
- six focused behavioral cases discriminate each required and forbidden behavior with isolated
  oracle mutations, and paired baseline/candidate runs measure compliance and total
  artifact-containing response cost under identical pinned conditions; and
- generated adapters, the validator, focused tests, the full suite, and the plugin contract are
  green on the exact candidate bytes.

## One packet, six labeled lines

The handoff uses the fleet's existing labeled-line dialect. It does not add a `packet_lint` shape,
a schema helper, or a fleet-validator rule. The six lines group the spec's twelve semantics without
discarding them:

| Line | Approved spec semantics carried |
|---|---|
| `Objective` | task identity, bounded deliverable, explicit out of scope |
| `Decisions and evidence` | fixed operator decisions, exact sources, verified environment facts and their probes |
| `Forbidden regressions` | disproved assumptions, their replacement controls, and rejection tests for code and tests |
| `Acceptance and invariants` | failure paths, verification-method validity, parsed relationships/postconditions, inventory-derived invariants |
| `Authority and recovery` | authority boundary, broker/mediator and four transport states, irreversible postconditions/reconciliation, temporary-authority lifetime/cleanup |
| `Work state` | blocking prerequisites and non-blocking lanes with owners |

Secret-safe capture governs the whole block: only field-scoped non-secret projections or references
enter it; resolved material never does. When a source is immutable Git content, the existing
`base_sha` / `candidate_sha` / `tree_oid` names are reused rather than inventing synonyms.

## Canonical payloads

1. `agents/homelab-platform.md` owns the trigger, six-line template, field semantics, and short-form
   exception. It returns the packet to its caller because the agent intentionally has no `Agent`
   tool; the packet grants no delegation or execution authority.
2. `agents/sde-fullstack.md` consumes the packet. Before its first edit it echoes the objective,
   fixed decisions, verified constraints, forbidden regressions, acceptance/evidence method, and
   authority/secret boundary. It never reconstructs an omitted field, stops on a missing or
   conflicting field as a material fork, and never echoes resolved secret material.
3. `README.md` records the ownership direction so the consumer paraphrase defers to the producer.
4. Host and service onboarding skills stay unchanged. Their existing tier, capture-safety, and
   checklist-completion rules remain authoritative; the producer decides when a bounded artifact
   is handed to application-code implementation.
5. Regenerate every host adapter from the two canonical agent edits. No description or inventory
   change is planned, so no routing run or inventory rewrite is owed.

## Focused behavioral evidence

Add exactly six `handoff-001` contracts, with no `packet_shape`:

1. the producer carries all three observed failed assumptions and their replacement controls;
2. discovery rejects skipped check-mode evidence and captures only secret-safe projections;
3. a requested Tier-1 artifact is the response's first deliverable while live blockers and open
   lanes remain explicit;
4. a simple stateless service stays on the short path while preserving acceptance and authority;
5. the builder echoes the packet, rejects regressions in both implementation and tests, and stops
   on an authority conflict instead of guessing; and
6. the reviewer independently rejects a green test that encodes a disproved constraint. This is a
   regression cross-check, not a second packet consumer or owner.

The existing `tier-gate-holds` case remains the adverse-authority oracle; duplicating it under a
HANDOFF tag would re-prove the same boundary. Before any live run, each new case gets one passing
control, every required pattern is removed once to prove that omission fails, and every forbidden
pattern gets one isolated contradiction. The old regex forests, thirteen-slot shape, special probe
parser, validator mutation matrix, and nine-case wholesale restore are out of scope.

## Verification and publication boundary

Deterministic work runs red-before-green oracle controls, adapter generation, T0, the affected test
modules, T1, and `claude plugin validate . --strict`. A fresh-context prompt review judges both the
full and short paths.

The paid/manual acceptance remains a separate, explicit boundary. The first-artifact case requires
the Tier-1 artifact as its first response deliverable, while the runner persists only total per-run
response duration. Report that value as end-to-end artifact-containing response cost, never as
first-artifact or first-token latency; exact first-artifact timing remains unmeasured unless the
operator separately chooses streaming instrumentation. After the six cases and candidate bytes
freeze, run the same evaluator, case bytes, pinned model and CLI,
timeout, clean-room/auth conditions, and `concurrency=1` against baseline `4777df9` and the
candidate, three runs per case, recording per-run tokens and duration. The baseline worktree remains
immutable until both captures finish. Report all three duration values; call the candidate's total
response faster only when its median is lower and the baseline/candidate ranges do not overlap,
otherwise report the duration result as inconclusive. No session spend starts without the
operator's approval of the exact model and 36-session plan. Issue #60 is updated only with separate
authorization to post externally.

## Rollback

One revert removes the producer, consumer, six contracts, their oracle controls, the duration result
field, and regenerated adapters. The existing tier/capture rules and `tier-gate-holds` case remain
untouched.
