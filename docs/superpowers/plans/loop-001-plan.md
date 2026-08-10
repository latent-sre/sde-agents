# LOOP-001 plan — execution payloads for the approved spec

Paired with the approved
[`LOOP-001 spec`](../specs/loop-001-released-retest-lifecycle.md); operational only while this
round is active, then retired to an outcome record. Evidence base at authoring: `lc_74f04730`,
`lc_546acdcc` (the 1.7.0 workflow shipped broken until a released-load caught it), issue #73
(handoffs dropped by foreign coordinators), and three hand-executed release retests
(1.7.0→1.7.1→1.7.2) proving the lifecycle by practice before encoding it.

## Design decision the spec left to the plan

**Fields, not new lifecycle states.** The merged≠released distinction lands as optional
record blocks on a promoted candidate — `release` (version, reference, recorded_at) and
`retest` (result, environment, reference, recorded_at) — because new `promotion_state` values
would ripple through the three declared STATE_DISPOSITIONS mirrors, the packet grammar, and
every learning contract, violating the no-grader-loosened constraint for no added power.
Closure remains a judgment the records make legible, enforced fail-closed at the tooling layer:

## Payloads

1. **`scripts/learning_ledger.py`** — two subcommands, additive schema:
   - `record-release <id> --version --reference` — legal only on a `promoted` candidate;
     stamps the release block; rejects a second release block (a later release is a new
     record's business).
   - `record-retest <id> --result {pass,fail,inconclusive} --environment --reference` — legal
     only when a release block exists; stamps the retest block. A `fail` result prints a
     loud pointer that the candidate's destination regressed in the field.
   - `list` gains `--view awaiting-retest`: promoted candidates carrying `release` but no
     `retest` — the pull-based discovery surface (spec item 5); a release or upgrade retro
     reads it, nothing schedules it.
   - `check` validates both blocks' shapes and their ordering invariants.
2. **`skills/self-improve-loop`** — the lifecycle statement (spec item 1) lands in
   [`references/learning-ledger.md`] as the governing shape for retained field feedback, with
   SKILL.md gaining only the closure rule sentence: *a field-feedback item closes as
   successful only with an exact released-version retest recorded, or the owner's explicit
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
5. **Tests** — subcommand happy/fail-closed paths in `tests/test_learning_ledger.py`
   (release-before-promoted rejected, retest-before-release rejected, double-release rejected,
   awaiting-retest view exact), per the defensive-branch playbook: every guard lands with the
   test that fires it.

## Verification payloads

Deterministic: validator, full suite, `learning_ledger.py check` over live records, adapter
parity (skill edit). Behavioral: the three new contracts ride LEARN-002's calibration docket
for their live paired run, per the review-loop stop rule — authored here, calibrated there.

## Rollback

Script + skill + template + contracts in one revert; the additive record blocks parse as
absent on old records, so no migration and no schema version bump.
