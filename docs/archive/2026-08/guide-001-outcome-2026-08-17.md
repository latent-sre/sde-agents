# GUIDE-001 outcome — the AGENTS.md audit remainder (closed 2026-08-17)

**Status: historical outcome record.** The round is finished; nothing here is a task list. The
roadmap item retired with this record; Git history retains its full text (last present at
`9369e4e`).

## What landed

The 2026-08-16 three-scan audit of the repository guide (design/weight, accuracy against
sources, consistency) closed in two waves. Wave one merged as **PR #142** (merge `62f4552`,
2026-08-16): the correctness fixes, the Map deletion with six relocations, the PR-section
rebuild, the Development-loop trim (three-pass verified), and the engineering-program
restructure per operator ruling. Wave two landed on the restarted
`claude/agents-md-review-jp2ly0` (`8d9dccf`..`9369e4e` plus this record's commit) and closed
every remaining outcome:

- **Validate before you push** rewritten for the stateless-session reader (`8d9dccf`): each
  tier leads with its command roster, T2 states it requires nothing from the reader, exit-3 is
  a linear read-repair-clear procedure, incident narrations reduced to citations. ~818 → ~642
  tokens.
- **Preamble** two-scan trim (`f806b29`): host list and canonical-source statement fused, the
  convention-genealogy sentence dropped, validator enumeration kept but unscaffolded. ~269 →
  ~206 tokens. Ride-along: **A3** closed — the `~/.claude` prohibition names fleet
  definitions, not sessions.
- **A2/A6/G3/G4** landed, **A4 dropped** (`b17da55`): tripwire-retirement doubt is recorded in
  the test's docstring beside the risk hypothesis it questions (A2); the Any-edit playbook
  runs T0 by name instead of paraphrasing it (A6); a check already red on arrival is fixed if
  trivial, otherwise recorded — never passed silently (G3, opens the Validate section); a host
  without the `claude` CLI says so and defers the contract check to CI's pinned job (G4,
  beside T1's contract command). A4 — a T3 cross-reference to the description-edit eval
  trigger — was dropped: the description playbook already binds that obligation specifically
  in the same always-in-context file, and a pointer restating a nearby fact is the redundancy
  the campaign removes.
- **Hard rules** rewritten from three independent deep reviews — home-lab necessity, LLM
  executability, integrity against sources (`9ce4db3`): every bullet leads with a bounded
  trigger and imperative; the proportionality maxims became three before-X-do-Y rules scoped
  to their real triggers (adding a check, claiming an optimization, building a mechanism) so
  they cannot fire on ordinary work; one-writer's narration compressed to its verified
  citation (learn-001 outcome); "Owned conventions" became "The source wins on drift" and
  closed the defective-source misdirection (fix the source, re-propagate). Two paraphrase
  corrections the guide's own rule required: "cannot carry" → never add (the keys are silently
  ignored, nothing errors at load), and "does not error at load time" → "not guaranteed to
  fail loudly" (the validator's owning comment rules the runtime behavior undocumented). No
  rule removed: five bullets are check-backed; the three prose-only rules (stdlib, one parser,
  one writer) keep their one-clause rationale because prose is their only enforcement. ~880 →
  ~710 tokens.
- **The register rule** (`9369e4e`): the campaign's discipline is now a standing preamble
  rule — lead each rule with its trigger and imperative, compress rationale to a clause or
  citation, keep incident narration in its archive or decision record. Costs ~64 tokens to
  protect the ~2,500 the campaign removed.

## The two operator rulings (2026-08-17)

- **A1 — the deep-review cap widens, two-tier:** at most two static deep-review rounds per
  prose-behavior change (agent or skill text), **three** for any other fleet prose — docs and
  this guide included. The operator-ruling escape is unchanged. Provenance: the guide itself
  accumulated more review rounds than any agent file during this campaign.
- **G5 — eval scope follows the trigger:** a release or CLI pin bump owes every routing
  cluster and the behavioral evals — a global trigger owes global coverage, so no
  affected-only subset exists. Description edits continue to owe their affected clusters per
  the description playbook; nothing new to remember.

## Measures

File: ~7,940 tokens at audit start → ~5,726 at PR #142 merge → **~5,498 at close** (the
register rule and rulings added back ~110 of wave two's ~380 trim; every figure measured with
the one instrument, chars/4 on the raw file slice — this closing figure itself was corrected
from a pre-measurement draft, the drift lesson below firing one last time). Every commit validator-green, 858 tests
passing.

## Lessons paid for

- A trim campaign needs its register codified in the trimmed file, or the next session
  re-fluffs it — the discipline now lives in the preamble, not in session memory.
- Forecasting token savings with a different instrument than the landed measure drifts
  one-directionally (~15-20% optimistic, twice); the fix is mechanical — measure the draft
  with the landing instrument before quoting a number.
- "Soften" and "trim" compose with LLM-optimization only when each rule keeps a bounded
  trigger: the burn source was never the rules' existence but maxims wide enough to fire on
  ordinary work.
