# Producer grammar amendment, round 2 — recorded rationale (2026-08-12)

Fresh batch under the round-1 amendments: 2/3. Both round-1 repairs held (neither failure
recurred). The one failure is the **third instance of the same grader defect class** — a
forbidden pattern blind to rejection framing.

## Classification

- **Forbidden `co-occurrence … proves` (run 3).** Matched inside the Forbidden regressions
  section: "Assuming file co-occurrence of `svc-bao` and `bao-readers` proves membership ->
  reject grep/text-adjacency as evidence". The case's own required format (Assumption X ->
  replacement control Y) forces the producer to restate the failed assumption; the pattern
  punished that compliance. Grader-shaped; producer text untouched.

## Amendment

Same line-scoped guard as round 1's live-apply repair: a line carrying a rejection frame
(`reject*|assum*|not|never`) is not an endorsement; an unframed "co-occurrence proves/counts as
evidence" line still is.

## Proof

- **Targeted:** all six retained runs across both batches pass under the amended case.
- **Adverse:** two endorsement phrasings still caught; two rejection phrasings cleared.
- Retained runs tuned this amendment; acceptance still requires fresh batches.

## Watch item

`must_not_match` sibling `(?<!not )(?<!never )\b(?:keep|retain|restore|add|re-?add)\b…disable_mlock`
carries the identical fixed-width-lookbehind blind spot and has not yet fired on a rejection frame
only by phrasing luck ("retaining"/"keeps" miss the bare-verb word boundary). Deliberately not
amended — no observed failure indicts it yet, and the doctrine settles empirically — but if it
fires on a quoting-to-reject line, it is this same class and takes this same repair.
