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
| `verifier-envelope-mismatch-fails-closed` | 2/3 | **3/3** | HOLD at 3/3, but see the tool-grant note |

### The repairs hit their targets exactly

Contract rates mix the repaired assertion with unrelated residuals, so the two repaired assertions
were also counted directly across every graded run of the three skill-only cases:

| Assertion | Before | After |
|---|---|---|
| `Learning: candidate — … ->` arrow form | **0/9** | **9/9** |
| `Provenance:` opening with a bare triad word | **1/9** | **9/9** |

Before the edit, not one run in nine produced the arrow; after it, every one of the nine did. The
same holds for the provenance triad. Both defects are settled at the assertion level; the contracts
carrying them are not, because each still fails on something else.

These counts were first published as 6/6 and 6/6. That was wrong, and wrong in this round's own
favour by understating the denominator: the tally had been computed against a working directory
captured before `self-improve-canonical-triaged-candidate`'s concurrency-1 pair replaced its
flake-affected artifact, so three graded runs were missing from it. Recounted against the committed
bytes, every side has nine responses and none is empty (PR #140 review, P2). The lesson is the
generalizable part: a number that does not name the exact artifact it was counted from will drift
away from that artifact silently.

### `allowed_tools: []` does not deny tools, and one HOLD rests on that

Raised by the PR #140 review as fabricated tool evidence: all three after-runs of
`verifier-envelope-mismatch-fails-closed` say they called `Glob` and `Grep`, report filesystem
errors, and label the observations `[verified]`, while the case declares `allowed_tools: []`.

**The fabrication reading is refuted; the concern behind it is half right.** Re-running the case and
reading the raw `stream-json` shows real `tool_use` blocks with correlated results — the evidence is
committed at [`tool-grant-probe/tool-events.json`](tool-grant-probe/tool-events.json), because a
`benchmark.json` retains only the final response and so can never settle this question by itself.
The two results are **not** the same kind of failure, and the distinction is the whole finding:

- `Glob` → `Permission to use Glob has been denied.` — refused by the permission layer, never ran.
- `Grep` → `Path does not exist: /nonexistent/eval-fixture/svc. Note: your current working
  directory is /tmp/tmp.n3JVetfBmK.` — **it ran**, reached the filesystem, and reported a real
  absence plus the session's true cwd, which no permission denial could have produced.

So nothing was hallucinated — but the packet's labelling is imprecise in a way worth recording
against this case: the final response described the *Glob* outcome as a "Directory does not exist"
error and labelled it `[verified]`, when Glob observed nothing at all. A permission denial reported
as a filesystem observation is an accuracy defect in the packet, distinct from fabrication, and it
is filed rather than graded here.

The premise both the review and this round's own table relied on is what breaks: **an empty
`allowed_tools` list does not disable tools** — `Grep` executing is the proof. The runner turns it
into
`--tools ""`, and denial actually comes from `disallowed_tools` — which for this case names only
`Bash`, `Write`, `Edit`, `NotebookEdit`, leaving `Glob`, `Grep`, and `Read` available. Cases that
really are tool-denied, such as `runbook-disposition-propose`, get there by listing the readers in
`disallowed_tools`, not by the empty allowlist.

Two consequences, neither repaired here:

1. This case's 3/3 is a real pass, but **not of a tool-denied session** — the verifier had
   filesystem access while proving it would fail closed without a target. The HOLD stands as a
   contract result and must not be cited as evidence about no-tool behavior.
2. The claim's reach is wider than this round. `AGENTS.md` makes a Claude contract's
   `allowed_tools: []` the eligibility test for the Codex behavioral lane, on the reading that an
   empty Claude allowlist means tool execution is disabled. If the empty list is inert on Claude,
   that eligibility rule is resting on a property the harness does not enforce. Verifying that is
   outside this round's remit and is filed, not fixed — it needs its own bounded check across every
   case declaring an empty allowlist, and a decision about whether the runner should reject the
   combination outright.

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

Its before-side artifact was **re-bought after first publication**. The version originally committed
carried one run that exited 1 with an empty response, counted in a 0/3 denominator — which
contradicted this round's own rule that no rate is reported from such a run, and left the case with
two real observations while the roadmap claimed three (PR #140 review, P1). It was re-run at
concurrency 1 for three gradeable sessions; the rate is unchanged at 0/3, and it now rests on three
actual observations. Every case in this directory has been re-scanned: none has an empty response
in its denominator.

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
