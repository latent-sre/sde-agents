# LOOP-001 plan — released-version retest closes the field-feedback loop

**Status: active.** Paired with the approved
[LOOP-001 spec](../specs/loop-001-released-retest-lifecycle.md) and the roadmap's LOOP-001 entry.
Implements issue #67 under its own discipline: extend the existing lifecycle, add no scheduler,
daemon, transcript store, or self-modifying loop.

## Decisions the spec delegated

**1. Both a record field and a lifecycle state.** The spec left "new record fields or new lifecycle
states" to this plan. The gap the roadmap and the field evidence name is that *no recorded state
distinguishes merged from released*, so a state is required — `promoted` stops being terminal and
`released` follows it. A state alone would carry no measurement, so the retest itself lands as
`retest_history` on the record: released version, environment, result, evidence, rollback trigger,
owner, reason, attestation. The two halves split along the ledger's existing seam — `add`,
`observe`, and the new `retest` record evidence; `transition` records decisions — so recording a
retest never advances a candidate, and reaching `released` is always an owner's explicit act.

**2. Schema version 3, not an in-place field addition.** Record validation requires an exact
top-level key set, so adding `retest_history` to version 2 would invalidate all 32 tracked records
at once. Versions 1 and 2 stay readable exactly as written, new records are version 3, and an older
record is upgraded only by the write that needs a newer field — the upgrade appears in the same diff
as the command that caused it instead of sweeping the store invisibly.

**3. The lifecycle text lives in `skills/self-improve-loop/SKILL.md`.** The spec allowed SKILL.md or
`references/learning-ledger.md`. The closure rule is a *gate*, and the gates are in SKILL.md; the
reference carries the operational contract (commands, states, retest semantics). Placing the rule
next to the seven promotion gates is what makes "merging is not closure" read as a gate rather than
as background.

**4. `PENDING_STATES` is unchanged; discovery is a separate view.** A merged candidate awaiting a
retest owes a *measurement*, not a decision, so folding it into `pending` would change what the
ledger-drift report means. `list --view awaiting-retest` answers it instead, holding a candidate
until the `released` transition and flagging `release_retested` so the operator can see which of the
two remaining steps is owed. Nothing schedules the query — a release, an upgrade, or a retro asks.

**5. The gate is enforced twice, deliberately.** `transition` refuses `released` without a
qualifying retest, and record validation refuses the same record on disk, so a hand-written
`released` fails `check`. Each layer has its own test and its own message, and both were proven
non-vacuous by mutation: removing either makes exactly one test fail.

**6. Eval dispositions for issue #67's seven scenarios.**

| Eval | Disposition |
|---|---|
| 1 — capture is not closure | New behavioral contract in this round. |
| 2 — duplicate feedback | New behavioral contract in this round. |
| 3 — released-artifact retest | New behavioral contract in this round. |
| 4 — home-lab phase calibration | GATE-001's, closed 2026-08-10; the five-tier classification is canonical in `agents/homelab-platform.md`. Not restated here. |
| 5 — approval reuse and new risk | GATE-001's (Tier-2 identical-retry consolidation). Not restated here. |
| 6 — rejected or regressing candidate | Covered: the promotion gate already requires regression and adverse proof and requires retaining the rejection evidence, and the ledger's adverse states are reopen-gated on distinct fresh evidence. No new case. |
| 7 — sensitive evidence | Covered: intake stores references rather than transcripts, every source carries `--sensitivity-reviewed`, and secret-like, multiline, and command-like fields already fail closed with tests. The new retest fields pass through the same filters. No new case. |

## Execution payload

1. `scripts/learning_ledger.py` — schema v3, the `released` state and its transitions,
   `RETEST_RESULTS`, the exact-version shape, `retest()`, the `transition` gate, the
   record-validation gate, and the `awaiting-retest` view.
2. Mirrors, in the same change: `scripts/packet_lint.py:LEARNING_STATE_DISPOSITIONS`, the
   `self-improve-loop` state list and pair list, and the pinned lifecycle-owner packet enum in
   `agents/sde-fullstack.md`, `agents/verification-engineer.md`, `agents/prompt-engineer.md`, and
   `scripts/validate_fleet.py:LEARNING_LIFECYCLE_OWNER_PACKET_SLOT`.
3. Prose: the closure gate and lifecycle diagram in `skills/self-improve-loop/SKILL.md`; commands
   and state semantics in its `references/learning-ledger.md`; state lists in
   `references/retro-protocol.md` and `references/discovery-routing.md`; `learning/README.md`.
4. `.github/ISSUE_TEMPLATE/field-feedback.md` — issue #67's minimum contract as a bot-free
   checklist.
5. `evals/behavioral/contracts.json` — Evals 1–3.
6. Regenerate every host adapter. The README inventory is untouched: no component is added, renamed,
   or removed.

## Gates

Owed by this change: the validator, the full offline suite, `learning_ledger.py check`, and adapter
parity — all runnable offline and all green before merge. No `description:` field changed, so no
routing eval is owed. The three new behavioral contracts are T3 (real API) and are owed **on the
released artifact**, which is this round's own closure rule applied to itself.

## Closure

LOOP-001 and issue #67 stay open past this merge. They close when the next release ships, Evals 1–3
run against that released version, the measured result is attached, and the ledger records
`lc_74f04730` as `released` with that version — or an owner records an explicit waiver and its
reason. A merge that closed this item would be the exact substitution the round exists to prevent.

## Rollback

One revert commit: the ledger script, the mirrors, one skill and its references, the issue template,
the contracts file, and the regenerated adapters. A record written at schema 3 does not validate
against the reverted script, so any `retest` or `released` record created before a rollback is
reverted with it.
