# Round design — verification role, eval isolation, import method (2026-07-29)

**Status: active round.** Scope was operator-adjudicated on 2026-07-29 in one question round; the
four forks below are decisions, not defaults. Per `docs/README.md` rule 4, this file retires to an
archived outcome record when the round finishes. The paired plan is
[`plans/2026-07-29-verification-eval-port.md`](../plans/2026-07-29-verification-eval-port.md).

Roadmap items in scope: **ROLE-003**, **ROLE-004**, **EVAL-003 (phase 1 only)**, **PORT-001**.

## Item 1 — ROLE-003: verification execution authority (decided)

Operator chose the **test-authoring verifier** model, with the **local-containers-free** effects
gate. The contract, answering the six forks the role-expansion decision record posed:

1. **Test creation and edits: allowed.** Authoring missing acceptance/regression tests is part of
   the remit (the old `test-engineer` contract folds in here, as the record anticipated).
2. **Product-code edits: always prohibited.** This is a cooperative limit — no tool layer can
   distinguish test paths from product paths — and the definition must say so honestly rather
   than implying enforcement.
3. **Worktree: disposable worktree by default.** Evidence binds to the exact revision and
   environment actually tested; a verdict for revision X must have been produced at revision X.
4. **Effects gate:** hermetic checks (unit tests, builds, linters, in-worktree scripts) run
   freely. **Throwaway local containers are also free** (operator choice) — with mandatory
   teardown and any residue (ports, volumes, images) reported in the packet, because container
   side effects outlive the worktree. Live-lab services, external network calls, shared
   databases, and external systems require approval named in the task.
5. **Approval rule:** a check that needs an ungated effect without approval is reported
   **inconclusive** — never silently skipped, never counted passed.
6. **Enforced versus cooperative:** the `tools:` list is enforced by the platform; path scoping
   and effects gating are cooperative. The definition states which is which.

Holding Write/Edit for the real purpose of test authoring is what keeps this agent out of the
read-only classification — an execute-only design would either be blocked by the guard's
no-interpreters rule or require weakening it, and both were rejected.

## Item 2 — ROLE-004: `verification-engineer` agent

- Owns: independently reproducing reported behavior, executing acceptance/regression/failure-path
  checks, comparing observed behavior with explicit acceptance criteria, returning a
  pass/fail/inconclusive verdict with traceable evidence.
- Does not own: implementing fixes (`sde-agents:sde-fullstack`), static diff review
  (`sde-agents:code-reviewer`), diagnosing unknown failures (`root-cause`), live lab changes
  (`sde-agents:homelab-platform`), cross-component test architecture
  (`sde-agents:principal-engineer`).
- `tools: Glob, Grep, Read, Bash, Write, Edit`; `model: inherit` (roster convention). Not a
  guard-roster agent: it holds write tools for a real reason.
- Packet: target/environment/exact revision, acceptance criteria, checks executed, expected vs
  observed, failure-path coverage, evidence with reproducible commands, verdict, skipped checks
  and remaining risk. Canonical `[verified]/[sourced]/[unverified]` stems verbatim.

**Acceptance:** validator/tests/strict plugin validation green; a routing cluster covering the
verification-vs-implementation/review/diagnosis seams (negatives are the graded signal — agent
positives carry the known headless zero-fire caveat); behavioral contracts proving (a) an unrun
or blocked check cannot be reported as passed and (b) a planted-bug verification returns FAIL
citing the exact given revision, without the verifier "fixing" the product code to make its own
tests pass.

## Item 3 — EVAL-003 phase 1: harness isolation (not the anchor)

The eval harness has no configuration isolation, `evals/README.md` line 108 claims it does, and
the deployed junctions mean fleet components register bare *and* namespaced in every
`--plugin-dir` eval session. Hypothesis (plausible, unproven): this contamination is what
suppresses agent-expecting positives (0/21, 0/6, 0/6).

- Salvage `scripts/eval_clean_room.py` + `tests/test_eval_clean_room.py` from the unmerged
  `modernization-cleanup` branch; verify its two env-var facts against current CLI docs before
  trusting them; take `THIRD_PARTY_NOTICES.md` only if review shows it is owed.
- Fix the false isolation claim in `evals/README.md`.
- Run the two-session registration probe: one contaminated session, one clean-room session,
  comparing what registers. If registration differs, re-run one known agent-positive set under
  isolation before any case redesign.
- Record findings on the roadmap's EVAL-003 item; delete `modernization-cleanup` after salvage.

**Deliberately out of scope:** the full anchor capture. It stays conditional on what the probe
shows — capturing an anchor with a contaminated harness records the harness, not the fleet.

## Item 4 — PORT-001: codify the import method, exercise it once

- Write down the proven four-pass method (import / conflict-identity / craft /
  tooling-verification) with adaptation-notes-as-specification, donor-assumption scrub, and
  provenance. Default form is a documented convention; it becomes a skill only if an invocation
  shape with zero always-visible routing cost justifies itself (the roadmap's own cost test).
- Exercise it on the operator-chosen donor: `superpowers:systematic-debugging` →
  `skills/root-cause`. Deltas are expected in both directions; contribute-back candidates are
  recorded, not acted on.

**Acceptance:** the import follows the codified method with adaptation notes and provenance
recorded; validator/tests green; if `root-cause`'s description changes, its overlapping routing
cluster runs before and after.

## Out of scope for the whole round

DEPLOY-001 (parked by operator), LABSEC-002 (blocked on it), RELEASE-001, EVAL-004, LAB-001,
the full routing anchor, and any change to the read-only guard's allowlist.
