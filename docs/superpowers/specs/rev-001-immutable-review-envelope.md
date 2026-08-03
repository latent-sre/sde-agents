# REV-001 spec — advisory/approval split and the review-to-verify envelope

**Status: proposed** — drafted 2026-08-03, awaiting operator approval. Implements issue #62 under
the operator's 2026-08-03 ruling: **smallest mechanism, GRAPH-004-compatible field names**;
GRAPH-004 itself stays deferred per its own economics baseline.

## Problem

Issue #62 plus the SEC-01 field record: orchestration started review and verification against
moving bytes (superseded work, verdict rebinding), a verifier's evidence bundle died in temporary
storage, and — on the same immutable target — reviewer and verifier judged **different effective
risk sets**, so a verifier PASS coexisted with two valid reviewer P1s. The final runs also proved
the desired lifecycle works when followed (nits invalidated a target; the amended SHA got a fresh
review bound to exact parent and tree; gates were rerun, not inherited; a verifier returned
INCONCLUSIVE rather than faking a verdict when its isolation could not start) — so this round
formalizes an observed-good practice rather than inventing one.

## Scope (prompt-level, canonical agents only)

1. **Advisory/approval modes in `code-reviewer`.** Advisory findings on a mutable tree stay legal
   and labeled (the existing PROVISIONAL verdict form is the model); a formal **approval** binds
   to immutable identity — candidate commit, exact parent, tree digest — and is refused or marked
   provisional when the tree is dirty.
2. **The envelope in `verification-engineer`.** Verification requires the approval envelope
   (repository, base SHA, candidate SHA, tree digest, scope, acceptance criteria) and confirms
   the identity before executing; mismatch, relevant uncommitted changes, or an unreproducible
   snapshot fail closed as refuse/INCONCLUSIVE. Field names follow the GRAPH-004/`contract_digest`
   idiom so a later promotion to a typed contract is a rename-free change.
3. **Shared material-risk matrix.** Reviewer and verifier receive the same compact
   requirement-and-risk list so their effective criteria cannot silently diverge; seeded with the
   two field-proven transferable controls (irreversible remote credential mutation requires
   post-failure state reconciliation before rollback; secret-bearing nonstandard headers require
   a logging/redaction contract before shared access logging).
4. **Evidence-provenance classes.** "Fresh immutable review plus caller-reported test evidence"
   and "independent verifier executed the approved target" are distinct result classes and are
   never collapsed into one PASS; the evidence destination is declared by the caller (no
   auto-committed bundles into product repositories).

## Hard constraint

The fleet's own primary review lanes (`deep-review`, `multi-lens-review`, `/code-review`) judge
the working diff. A blanket mutable-tree refusal is **out of scope**; those lanes map to advisory
mode, exactly as deep-review's PROVISIONAL cap already does.

## Acceptance

- [ ] Scenario evals from issue #62 pass: mutable-tree review stays advisory; approval for SHA A
      does not transfer to SHA B; verifier target mismatch fails closed before executing;
      post-verification mutation inherits nothing; evidence-persistence failure is reported
      separately from the product result; offline PASS never implies live acceptance.
- [ ] Behavioral contract(s) added for the envelope refusal paths under the pinned harness.
- [ ] Adapters regenerated with parity green; validator and tests green; working-diff lanes
      demonstrably unaffected (deep-review probe or fixture run unchanged).
- [ ] Issue #62 updated with evidence and closed or re-scoped.

## Out of scope

Reopening GRAPH-004; CI-enforced envelopes; the #60 handoff packet (HANDOFF-001 consumes this
round's idiom); any change to verifier isolation mechanics.

## Rollback

Prompt-level edits to two canonical agents plus regenerated adapters — one revert commit.
