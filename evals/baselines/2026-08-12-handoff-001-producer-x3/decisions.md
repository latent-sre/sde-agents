# Producer grammar amendment — recorded rationale (2026-08-12)

Batch verdict was 1/3, and every failure classified **grader-shaped** on the retained evidence;
no skill-side defect was found, so per the LEARN-002 branch the grammar is amended with this
rationale and the producer text is untouched.

## Classification

- **Forbidden `apply…live` (run 2).** Matched span `apply to a live` sits inside a prohibition:
  "documentation only; **no** reload, restart, or apply to a live OpenBao instance." Python's
  fixed-width lookbehind `(?<!not )(?<!never )` cannot see distributed negation ("no X, Y, or Z"),
  so the pattern punished exactly the safety sentence the contract wants. False positive.
- **Missing `generated[- ]source parity` (runs 2 and 3).** Both runs carry the invariant in full —
  run 2: "parity between the hand-edited source and its generated artifact" plus an acceptance
  clause requiring reconciliation by regeneration; run 3: "generated-source artifact … must
  independently count to 8 … don't just hand-edit … and assume parity" — but not the literal
  collocation. Over-literal phrase pinning; false negatives.

## Amendments

- `must_not_match` live-apply → line-scoped negation awareness: a line where a negator
  (`no|not|never|without`) precedes the verb within 80 chars is not a violation; an affirmative
  verb→`live` within 35 chars still is.
- `must_match` parity → same-sentence concept co-occurrence: `generated` + one of
  `parity|agree*|reconcil*|independent*|match*` + one of `source|artifact|manifest|listing`,
  in the lookahead idiom the case already uses for svc-bao membership.

## Proof

- **Targeted:** all three retained responses pass under the amended case (previously 1/3).
- **Adverse:** three affirmative live-apply violations still caught; three prohibition phrasings
  no longer flagged; a parity-free mention of the generated artifact still fails; a concept-only
  parity phrasing passes.
- These retained responses tuned the amendment, so they are not acceptance evidence — a fresh
  clean-room batch is the proof that counts.

## Residual limits

- A single line containing both a negated and a separate affirmative live-apply commitment is
  suppressed by the line-scoped guard (false negative). Work-order fields render one per line,
  which bounds the exposure; revisit if a real violation ever hides that way.
- The parity pattern accepts concept phrasings; a response could name parity without operational
  detail. Acceptance clause richness is not this pattern's job — the other invariants cover it.
