# LOOP-001 plan — execution payloads for the approved spec

Paired with the approved
[`LOOP-001 spec`](../specs/loop-001-released-retest-lifecycle.md); operational only while this
round is active, then retired to an outcome record. Evidence base at authoring: `lc_74f04730`,
`lc_546acdcc` (the 1.7.0 workflow shipped broken until a released-load caught it), issue #73
(handoffs dropped by foreign coordinators), and three hand-executed release retests
(1.7.0→1.7.1→1.7.2) proving the lifecycle by practice before encoding it.

## Design decision the spec left to the plan

**Fields, not new lifecycle states.** The merged≠released distinction lands as optional record
blocks on a promoted candidate: `release` (version, reference, recorded_at), ordered `retests`
attempts (result, environment, reference, recorded_at), and `release_history` for completed
promotion cycles. Shipped singular `retest` records remain read-compatible and migrate on retry or
release-cycle archive.
New `promotion_state` values would ripple through the three declared STATE_DISPOSITIONS mirrors,
the packet grammar, and every learning contract for no added power. Closure remains a judgment the
records make legible, enforced fail-closed at the tooling layer.

## Payloads

1. **`scripts/learning_ledger.py`** — two subcommands, additive schema:
   - `record-release <id> --version --reference` — legal only on a `promoted` candidate;
     stamps one release per promotion cycle; after a fresh re-promotion, archives the prior
     release and all of its attempts and starts a clean cycle.
   - `record-retest <id> --result {pass,fail,inconclusive} --environment --reference` — legal
     only when a release block exists; appends ordered attempts. Fail and inconclusive remain
     retryable; PASS alone closes the cycle. A `fail` result emits and returns a loud regression
     pointer.
   - `list` gains pull-based `awaiting-retest`, `regressed`, and `awaiting-release` views. Failed
     attempts remain in both actionable retry and regression views until PASS or owner action.
   - Release identity resolves from its bound promotion transition, not mutable record-head
     destination metadata. Same-clock post-release transitions and later-release writes fail
     closed instead of inventing event order.
   - `check` replays exact promotion state at each release, validates distinct chronological
     release cycles and their attempt ordering, and rejects attempts crossing cycle boundaries.
2. **`skills/self-improve-loop`** — the lifecycle statement (spec item 1) lands in
   [`references/learning-ledger.md`] as the governing shape for retained field feedback, with
   SKILL.md gaining only the closure rule sentence: *a field-feedback item closes as
   successful only with an exact released-version PASS retest recorded, or the owner's explicit
   reason it is impossible; source-eval PASS is never reportable as released PASS.*
3. **`.github/ISSUE_TEMPLATE/field-feedback.md`** — the minimum contract made visible where
   issues are the destination (spec item 4): sanitized packet, duplicate check, owner, target
   release, eval evidence, released version, downstream retest, close reason. A template, not
   a bot; issues remain intake under docs rule 7.
4. **Behavioral contracts** — Evals 1–3 as agent-pinned cases in the pinned harness
   (`loop-capture-is-not-closure`, `loop-duplicate-merges-provenance`,
   `loop-source-pass-is-not-released-pass`), lifecycle-owner Learning shapes, graders built
   positives-first per the stop-rule lesson. Evals 4–5 belong to GATE-001 (closed, shipped);
   Evals 6–7 are covered by the existing promotion-gate and sensitivity contracts — recorded
   here as the spec requires.
5. **Tests** — subcommand happy/fail-closed paths in `tests/test_learning_ledger.py`: release before
   promotion and forged promotion→rejection→release are rejected; fail→retry→PASS and
   inconclusive→retry preserve ordered history; singular current and archived forms remain
   readable; archived attempts cannot leak into a later cycle; PASS alone closes; and all three
   pull views are exact. Every defensive guard lands with the test that fires it.

## Verification payloads

Deterministic: validator, full suite, `learning_ledger.py check` over live records, adapter
parity (skill edit). Behavioral: the three new contracts ride LEARN-002's calibration docket
for their live paired run, per the review-loop stop rule — authored here, calibrated there.

## Design ruling recorded at review

The spec's "rejection/rollback trigger" clause is carried by the lifecycle rather than another
record block: a `fail` attempt surfaces in `regressed` while remaining retryable in
`awaiting-retest`. A later PASS proves repair; otherwise the owner records a transition (rejected,
or retired-with-supersede naming the successor), whose `reason` field is the durable trigger.

## Rollback

The code reverts in one commit, but records are data: any candidate that has gained
`release`/`retest`/`retests`/`release_history` fields must have them stripped in the same change
(enumerable with a single grep for `"release"` — the other fields can only exist alongside it), or
the restored reader rejects the ledger on every command and the validator goes red with it.
`learning/README.md`'s Rollback section is the executable procedure. No schema version bump either
way; corrected from this plan's original one-revert claim, which review proved false.
