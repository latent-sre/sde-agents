# GATE-001 spec — gate-owner attribution and same-effect approval consolidation

**Status: approved** — drafted 2026-08-09, approved by the operator the same day (recorded at
the PR #98 closeout). Authored together with the
[LOOP-001 spec](loop-001-released-retest-lifecycle.md) under the operator's 2026-08-09 ruling:
**GATE-001 owns the five-tier risk/effect classification** — the tiers classify effects
generally, not broker-mediated effects only — and LOOP-001 references it. The ownership follows
the evidence: the consolidation rule is embedded in the tier text itself and is this item's
deliverable, and a mis-defined tier at a gate is a safety error where at the lifecycle it is
only a process error.

## Problem

Issue #61's SEC-01 field closeouts plus ledger candidate `lc_6b36cf5d`: during a real
service-onboarding round, repository confirmation strings, host managed-command approval, plugin
effect-broker availability, immutable review, credential custody, and irreversible initialization
were six distinct, individually functional gates — but they read to the operator as **one
repeated unexplained approval**. When the broker transport was unavailable after an exact
operator approval, the workflow stalled in a way that implied approval was missing rather than
diagnosing the absent integration, and the bounded work completed only through an
operator-authorized host-native bypass. Separately, repeated prompts for the same
already-approved reversible effect added ceremony without exposing any new consequence — while
the exact-target, destructive, credential-custody, and irreversible-initialization gates caught
real risk and must not be weakened. The imported closeout criteria are #61's final comment,
items 2–5; item 1 (plain-language discovery) is LANE-001's remit, not this round's.

## Scope (prompt-level, canonical definitions only)

1. **The five-tier risk/effect classification, canonically owned by this round.** The
   classification from issue #67's calibration requirement, stated once in one canonical fleet
   artifact:

   - **artifact preparation** — read-only design, tests, or default-off implementation; no live
     effect;
   - **repository publication** — commit, push, PR, or merge; changes source history but not
     live state;
   - **reversible live activation** — bounded deployment with stated health check and rollback;
   - **irreversible or custody boundary** — credential destruction, initialization/root
     generation, deletion, secret export, recovery-material retirement, temporary
     unauthenticated exposure, teardown, or an outage with materially new consequences;
   - **optional hardening** — defense-in-depth not required for the current merge or
     live-activation boundary.

   The classification **feeds** `homelab-platform`'s existing Tier 0–3 change-authority gates;
   it does not replace them and no second authority system appears. Reviewers classify findings
   against it (merge blocker vs. live-activation blocker vs. optional hardening); approvals
   classify effects against it. Every other consumer carries a declared-owner paraphrase per the
   owned-conventions rule; the paired plan picks the canonical file and the validator's existing
   checks hold the copies to it.

2. **Gate-owner attribution.** Every pause in a lab workflow names its gate owner from the
   closed set: repository confirmation, host sandbox/managed approval, plugin effect-broker
   transport, reviewer verdict, credential custody, irreversible service action. The
   `homelab-platform` tier text and its worked example demonstrate the attribution so a stacked
   pause (repository guard + host approval + broker) reads as its distinct layers, never as one
   unexplained gate.

3. **Broker-unavailable-after-approval.** When the effect-broker transport is not consumable
   after an exact approval, the workflow: diagnoses it as an integration absence attributed to
   the plugin-transport layer; retains the exact bounded request; offers the supported
   host-native continuation without broadening the approved effect; and never implies operator
   approval is missing. This sharpens the existing "mediator unavailable" stop in
   `homelab-platform` — the stop itself, and the rule that the agent never executes or calls the
   action brokered, are unchanged.

4. **Same-effect approval consolidation, embedded in the tier text.** An approval for a
   reversible live effect covers its reversible corrections (retry after a transient failure,
   the same bounded apply re-run) without re-gating; a new gate is required exactly when the
   next action introduces a materially new outage, exposure, deletion, authority, or custody
   consequence. Initialization/root generation, credential destruction, recovery-material
   retirement, and service teardown keep distinct unavoidable gates in all cases.

## Hard constraints

No gate is weakened: exact-target approval, the destructive/custody Tier 3 rules, the broker's
fail-closed contract, and the mediator-unavailable stop all survive verbatim in force.
`scripts/effect_broker.py` is not modified in this round — every change is prompt-level text in
canonical definitions. Consolidation never spans classification boundaries: a Tier 2 approval
never covers a Tier 3 effect, and nothing in the irreversible/custody tier is ever consolidated.

## Acceptance

- [ ] Behavioral contract: broker-unavailable-after-exact-approval yields the integration
      diagnosis, the retained bounded request, and the host-native continuation — with no
      approval-missing implication and no authority broadening (the eval requested in #61's
      2026-08-03 comment).
- [ ] Behavioral contract: an approval-consolidation case where reversible same-effect
      corrections proceed under one approval while a subsequent irreversible/custody action
      still re-gates (issue #67's Eval 5, fixtures A and B).
- [ ] Phase-calibration case: a default-off change lacking operator custody material is
      classified merge-safe but live-activation-blocked, with optional hardening reported
      separately (issue #67's Eval 4 — this round owns the classification it exercises).
- [ ] Gate-owner attribution: a stacked-gate fixture shows each pause naming exactly one owner
      from the closed set.
- [ ] One canonical classification text; consumer paraphrases declare the owner; validator,
      tests, and adapter parity green. Any description edit owes the overlapping routing
      cluster before/after per standing law.
- [ ] Issue #61 updated: criteria 2–5 evidenced and closed out from this round; criterion 1
      remains with LANE-001.

## Out of scope

LANE-001's discovery mechanism (criterion 1); LOOP-001's lifecycle states, which reference this
classification; any change to `scripts/effect_broker.py` or the guard/hook; REV-001's shared
material-risk matrix, which is review-verify doctrine, not effect classification — the paired
plans keep the two documents pointing at each other rather than merging or duplicating them.

## Rollback

Prompt-level edits to canonical definitions plus one new reference file and regenerated
adapters — one revert commit.
