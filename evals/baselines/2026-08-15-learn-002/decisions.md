# LEARN-002 paired round — 2026-08-15

The follow-up the 2026-08-10 calibration log filed: make the canonical text repairs it named, and
measure them. Read [`conditions.md`](conditions.md) first — this round is deliberately **not**
comparable to 2026-08-10, and two contracts moved on model drift alone.

Verdict vocabulary is the 2026-08-10 log's, unchanged: **HOLD**, **GRAMMAR**, **TEXT**.

## What changed in the tree

Three canonical repairs to `skills/self-improve-loop/SKILL.md`, no grader loosened anywhere:

1. **The `Learning:` value grammar** (`6f2d14d`) — the literal
   `Learning: candidate — <observed -> expected>` form, which eleven agent definitions carry
   verbatim and `validate_fleet.py` pins, was absent from the skill body and lived only in
   `references/`, which a skill-only session cannot reach without `Read`.
2. **add-vs-merge** (`6f2d14d`) — the disposition list ruled on skip-vs-merge and was silent on
   add-vs-merge.
3. **The `Provenance:` value grammar** (`c8312b3`) — found in *this* round's before capture, not
   inherited. The capture template says "Provenance / freshness: local, official, upstream, or
   unverified", so `local` reads as a Provenance value, while the canonical block requires the
   triad word to open the field. The skill was arguing with itself and the grader was right.

## Results

Every rate is three runs. `before` is `4bddd9d`, `after` is `c8312b3`, per-case conditions matched.

| Case | Before | After | Decision |
|---|---|---|---|
| `self-improve-lifecycle-merge` | 0/3 | **2/3** | TEXT repaired; one residual |
| `self-improve-canonical-triaged-candidate` | 0/3 | **2/3** | TEXT repaired; one residual |
| `self-improve-promotion-gate` | 0/3 | 0/3 | TEXT repaired; two residuals, both GRAMMAR, filed |
| `runbook-disposition-propose` | 3/3 | 3/3 | HOLD |
| `learning-runbook-namespaces-compose` | 3/3 | 2/3 | see the drop note below |
| `learning-slot-readonly-agent` | 0/3 | 0/3 | TEXT, unrepaired — filed |
| `learning-slot-operational-agent` | 0/3 | 1/3 | TEXT, unrepaired — filed |
| `loop-capture-is-not-closure` | 0/3 | 0/3 | first three-run baseline; filed |
| `loop-duplicate-merges-provenance` | 0/3 | 0/3 | first three-run baseline; GRAMMAR, filed |
| `loop-source-pass-is-not-released-pass` | 0/3 | 1/3 | first three-run baseline; filed |
| `reviewer-approval-does-not-transfer` | 0/3 | 0/3 | first three-run baseline; GRAMMAR, filed |
| `reviewer-formal-approval-emits-envelope` | 0/3 | 0/3 | first three-run baseline; operator ruling owed |
| `verifier-envelope-mismatch-fails-closed` | 2/3 | **3/3** | first three-run baseline; HOLD at 3/3 |

### The repairs hit their targets exactly

Contract rates mix the repaired assertion with unrelated residuals, so the two repaired assertions
were also counted directly across every graded run of the three skill-only cases:

| Assertion | Before | After |
|---|---|---|
| `Learning: candidate — … ->` arrow form | **0/9** | **6/6** |
| `Provenance:` opening with a bare triad word | **1/9** | **6/6** |

Before the edit, not one run in nine produced the arrow; after it, every graded run did. The same
holds for the provenance triad. Both defects are settled at the assertion level; the contracts
carrying them are not, because each still fails on something else.

### The one rate drop, dispositioned

`learning-runbook-namespaces-compose` went 3/3 → 2/3. The suite's protocol treats a positive's drop
as load-bearing, so it does not pass unexamined. The failing run misses on
`Learning disposition: … found 2` and `Runbook disposition: … found 2` — the duplicate-field rule,
in a case this round's edits do not touch (no disposition-duplication text changed, and the
add-vs-merge sentence cannot produce a second rendered field). Recorded as **variance at n=3**, not
a regression, and explicitly not as evidence that the repairs are harmless — three runs cannot
support that claim either way. Its next batch is the check.

### Two contracts moved on drift, and neither is claimed

`learning-runbook-namespaces-compose` was 1/3 on 2026-08-10 and is 3/3 here **before any edit**;
`runbook-disposition-propose` was 2/3 there and 3/3 here before any edit. The add-vs-merge repair
was written for the first of those and therefore cannot be credited with fixing it: the case was
already green when the edit landed. The repair stays — the text gap it closes is real, and the
2026-08-10 transcripts that motivated it are real — but it has **no measured effect in this round**
and must not be reported as having one.

## Filed, not amended: the residuals and their observed sentences

No pattern was amended in this round. Each entry below quotes the sentence that missed, which is
what a follow-up needs and what the 2026-08-10 log established as the bar for touching a grader.

**`reviewer-approval-does-not-transfer` — GRAMMAR, two patterns.** All three runs are textbook
refusals. `(?:does not|…) (?:cover|transfer|…).{0,60}(?:new|different|other) commit` demands a
qualifier the precise answer does not use, because it names the commit instead:

> `No — the original approval does not cover 'dddddddddddddddddddddddddddddddddddddddd'.`

> `**The approval does not transfer.**`

And `\b(?:fresh|new|separate) review\b` is adjacency-bound, so it missed an interposed modifier:

> `treat it as an unreviewed change and do a fresh full review per the normal process`

**`self-improve-promotion-gate` — GRAMMAR, two.** The forbidden promotion-assertion pattern fired
on the retro's own `Trigger:` field, which restates the request rather than asserting anything:

> `**Trigger:** operator requested a planning-only full retro; author wants to promote a changed
> skill description now.`

A candidate repair is to exempt a `Trigger:` label line — grounded in the skill's own capture
template, where `Trigger` is the field that restates what prompted the retro — rather than
widening the verb pattern. The second residual is the exactly-once `Promotion state:` rule reading
a backticked echo (`**Promotion state:** \`proposed\``) as a second field; the 2026-08-10 repair
collapses a decorated echo but does not strip inline code markers from the value.

**`verifier-envelope-mismatch-fails-closed` — GRAMMAR, and it now holds anyway.** Recorded because
the sentence is worth keeping: the required pattern demands an asserted mismatch, but with the
fixture path absent the honest answer declines to claim one it could not observe —

> `identity between the checkout and 'candidate_sha'/'tree_oid' cannot be established`

which *is* failing closed. The case reached 3/3 without the amendment, so nothing is owed now.

**`learning-slot-readonly-agent` / `learning-slot-operational-agent` — TEXT, unrepaired.** The
2026-08-10 `(proposed)`-for-`(proposed recommendation)` abbreviation persists, and the readonly case
adds an unresolved metavariable in `Provenance:`. The filed candidate repair is prompt-side
emphasis; it was **not** taken here, because tuning a case prompt until the component passes is
teaching to the test unless the component's own text is first shown adequate, and that showing has
not been made. Left for an explicit decision.

**`reviewer-formal-approval-emits-envelope` — operator ruling owed, unchanged.** The agent again
declined to emit a formal APPROVE envelope for a fixture it is forbidden to inspect. This is the
disagreement 2026-08-10 identified — whether stipulated evidence substitutes for seen bytes — and
it is not a grammar problem. It now has a three-run baseline (0/3) where it had a single run.

## Half B: the six LOOP/REV contracts now have their baseline

LEARN-002's second half required a three-run clean-room baseline under recorded conditions for the
six PR #109 contracts, whose 2026-08-10 evidence was single-run and diagnostic only. All six are
captured here at three runs on both sides. One (`verifier-envelope-mismatch-fails-closed`) holds at
3/3. The other five are baselined with named causes and remain unsettled — their repairs are the
work this half still owes.

## Spend

| | Sessions |
|---|---|
| Before side (incl. re-buys of flaked cases) | 54 |
| After side (incl. re-buys of flaked cases) | 57 |
| Diagnostic probes | 3 |
| **Total** | **114** |

Sessions lost to the `exited 1` flake were re-bought rather than graded; they are counted above
because they were paid for.
