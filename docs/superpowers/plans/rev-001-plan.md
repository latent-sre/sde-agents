# REV-001 plan — execution payloads for the approved spec

Paired with the approved
[`REV-001 spec`](../specs/rev-001-immutable-review-envelope.md); operational only while this
round is active. Admits the two riders the roadmap holds for this round: `lc_90dd8dc7`
(multi-task branches with a shared-config edit need the whole-branch final verification) and
`lc_2c04ead3` (a finding's stated reproduction is a claim with an evidence class, both
directions). Operator condition carried: **the shared material-risk matrix grows by
generalization, never per-incident append.**

## Payloads

1. **`agents/code-reviewer.md` — advisory/approval split.** The existing PROVISIONAL form is
   the advisory mode and stays legal on a mutable tree. A formal **approval** binds to
   immutable identity — candidate commit, exact parent, tree digest — is refused or marked
   provisional when the tree is dirty, and **never transfers**: an approval for SHA A says
   nothing about SHA B, however small the delta. Field names follow the GRAPH-004 idiom
   (`candidate_sha`, `base_sha`, `tree_digest`) so later promotion to a typed contract is a
   rename-free change. Rider `lc_2c04ead3` lands beside the evidence gate: a finding's
   reproduction claim carries its class — executed (you ran it, within the read-only
   boundary) or reasoned (label it so) — and a repro the reviewer did not run is never
   presented as the confirmed trigger; the underlying defect may still be real, but the
   stated cause inherits the label.
2. **`agents/verification-engineer.md` — the envelope.** Method 1 already pins revision and
   criteria; it gains the envelope's missing half: verification of a *formal approval*
   requires the approval envelope (repository, `base_sha`, `candidate_sha`, `tree_digest`,
   scope, acceptance criteria), confirms identity before executing, and fails closed to
   inconclusive on mismatch, relevant uncommitted changes, or an unreproducible snapshot.
   Evidence destination is declared by the caller — no auto-committed bundles into product
   repositories. Rider `lc_90dd8dc7` lands in Method 4: on a multi-task branch where any task
   edits shared execution configuration (caches, runtime pins, fixtures other tasks read),
   the per-task greens do not compose — the final whole-branch verification re-runs the
   interacting checks cold, because a green produced in a warm world is evidence about the
   warm world.
3. **Shared material-risk matrix.** Canonical block in `code-reviewer` (the reviewing side
   owns requirement lists), carried verbatim by `verification-engineer` with the declared
   owner, registered in README's owned-conventions list. Seeded with exactly the two
   field-proven controls: irreversible remote credential mutation requires post-failure state
   reconciliation before rollback; secret-bearing nonstandard headers require a
   logging/redaction contract before shared access logging. The growth rule is stated in the
   block itself: entries enter only as general controls, never as incident notes.
4. **Evidence-provenance classes.** Already half-shipped by GATE-001's Method 6 work on the
   verifier side; the reviewer side gains the matching line: "fresh immutable review plus
   caller-reported test evidence" and "independent verifier executed the approved target" are
   distinct result classes, never collapsed into one PASS.
5. **Behavioral contracts** — the envelope refusal paths: `reviewer-approval-does-not-transfer`
   (approval for SHA A asked to bless SHA B → refuses, re-review required) and
   `verifier-envelope-mismatch-fails-closed` (envelope names one SHA, checkout resolves
   another → inconclusive before anything executes). Positives-first graders. The existing
   `reviewer-uncommitted-bytes-are-not-approvable` / `reviewer-committed-bytes-remain-approvable`
   pair already pins the dirty-tree boundary and stays untouched.

## Hard constraint (from the spec, restated for the builder)

The fleet's own working-diff lanes (`deep-review`, `multi-lens-review`, `/code-review`) map to
advisory mode exactly as deep-review's PROVISIONAL cap already does — no blanket mutable-tree
refusal anywhere.

## Verification payloads

Deterministic gates plus adapter parity; the two new contracts join LEARN-002's calibration
docket for live runs. Working-diff lanes demonstrably unaffected: the deep-review run on this
very branch is the fixture (it reviews a mutable-tree diff and must keep doing so).

## Rollback

Prompt-level edits to two agents plus contracts — one revert commit; no script changes.
