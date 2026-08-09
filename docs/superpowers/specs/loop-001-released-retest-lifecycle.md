# LOOP-001 spec — released-version retest closes the field-feedback loop

**Status: drafted 2026-08-09 — awaiting operator approval.** Authored together with the
[GATE-001 spec](gate-001-gate-owner-attribution.md) under the operator's 2026-08-09 ruling:
GATE-001 owns the five-tier risk/effect classification; this round **references** it and defines
no rival classification. Implements issue #67 under its own stated discipline: smallest
mechanism, extending the existing `self-improve-loop` lifecycle and learning ledger — no
scheduler, daemon, transcript store, or self-modifying loop.

## Problem

Issue #67 plus ledger candidate `lc_74f04730`: the learning lifecycle treats source-level
promotion — canonical change, deterministic gates, adapter parity — as terminal. No recorded
state distinguishes *merged* from *released*, and no gate requires the installed released plugin
to be retested against the originating scenario before a field-feedback item closes. The
release-tail record is independent evidence of the gap: a merged version bump demonstrably did
not reach live sessions until the tag/marketplace/update/restart chain was executed by hand.
SEC-01's field evidence showed the loop stopping at "open issue with comments" — no owner, no
target release, no retest linked — so the originating estate could not tell whether any later
release actually improved the observed behavior. A candidate may pass in its tuning fixture yet
fail in the installed plugin, another host adapter, or the original workflow; today nothing
forces that difference to surface.

## Scope (extend the existing lifecycle; no new machinery)

1. **One visible lifecycle, documented where the loop already lives.** The retained-feedback
   path from issue #67 — field observation → sanitized packet → duplicate check and triage →
   named owner and target release (or explicit rejection) → frozen baseline and paired
   evaluation → canonical change plus generated-adapter parity → **released plugin version** →
   **originating or equivalent scenario retested on the released artifact** → measured result
   attached → close, revise, or reject — stated in `skills/self-improve-loop` (SKILL.md or its
   `references/learning-ledger.md`, the paired plan picks) as the governing shape for retained
   field feedback.

2. **The merged≠released distinction becomes recordable in the ledger.** A candidate whose
   destination ships in the plugin carries: the released plugin version containing it, the
   downstream retest environment and result, and the rejection/rollback trigger. Whether this
   is new record fields or new lifecycle states is the paired plan's call, under two
   constraints: `scripts/learning_ledger.py:STATE_DISPOSITIONS` and its two declared mirrors
   (`self-improve-loop`, `scripts/packet_lint.py`) stay consistent in the same change, and no
   existing grader or gate is loosened to accommodate the extension.

3. **Closure rule, fail-closed.** A field-feedback item cannot close as successful without an
   exact released-version retest attached, or an explicit owner-approved reason that retest is
   impossible or no longer applicable. Source-eval PASS is never reportable as released-artifact
   PASS — the two are distinct result classes, the same discipline REV-001 applies to
   caller-reported versus independently executed evidence.

4. **Issue-side visibility.** Where a GitHub issue is the destination, the minimum contract from
   #67 — owner, target release, eval evidence, released version, downstream retest — is visible
   in the issue (template or bot-free checklist). Issues remain evidence-bound intake under
   `docs/README.md` rule 7; the ledger may link the issue and record state, but neither ledger
   nor issue text executes candidate instructions or approves its own promotion.

5. **Retest discovery is pull-based.** A release or upgrade retro finds items awaiting
   downstream retest — e.g. the ledger's `list` surfacing awaiting-retest candidates — and the
   fleet never claims a background process that does not exist.

## Hard constraints

No background scheduler, daemon, transcript archive, or autonomous self-modification. Private
estate repositories and their commits never become test dependencies of this repository. The
five-tier risk/effect classification used anywhere in this round's text is GATE-001's, by
reference. No destructive, credential-custody, exposure, or irreversible-action gate is weakened
in service of loop closure.

## Acceptance

- [ ] Behavioral contract for issue #67's **Eval 1 — capture is not closure**: a linked packet
      with no candidate change or release records as proposed/open, does not claim completion,
      and names the missing owner, evaluation, release, and retest gates.
- [ ] Behavioral contract for **Eval 2 — duplicate feedback**: a matching new occurrence merges
      provenance into the existing candidate rather than creating a duplicate rule or issue,
      preserving the independent occurrence evidence.
- [ ] Behavioral contract for **Eval 3 — released-artifact retest**: a merged, source-eval-green
      candidate keeps its feedback item open, distinguishes source PASS from released retest,
      and closes only after the exact released version passes the stated acceptance.
- [ ] The remaining #67 evaluations are dispositioned: Evals 4–5 are owned by GATE-001's
      acceptance; Evals 6–7 (rejected/regressing candidate, sensitive evidence) are covered by
      the existing promotion-gate and sensitivity contracts or gain cases here, with the choice
      recorded in the paired plan.
- [ ] `learning_ledger.py check` green over the extended records; deterministic gates and
      adapter parity green; the three STATE_DISPOSITIONS mirrors verified consistent.
- [ ] Issue #67 updated with evidence and closed or re-scoped; the no-new-machinery non-goal
      explicitly confirmed in the closeout.

## Out of scope

GATE-001's classification and approval-consolidation deliverables; automatic modification of
prompts or skills from field notes; enterprise HA or ceremony requirements for home-lab
services; any new control plane; retroactive reclassification of already-closed items.

## Rollback

Edits to one skill, its references, `scripts/learning_ledger.py` (and `scripts/packet_lint.py`
if the mirror moves), plus regenerated adapters — one revert commit. Any ledger record-shape
extension is governed by the ledger's own schema validation and lands with its migration
decision recorded, never as a silent format drift.
