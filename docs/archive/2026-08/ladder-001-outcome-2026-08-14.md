# LADDER-001 outcome — the ownership-vs-consult calibration, measured (2026-08-14)

**What the item asked.** One recorded clean-room sonnet run of `evals/routing/ladder.json`
(3 runs/case, pinned output) with the rates of `pos-embedded-principal-fork-consult-required` and
`neg-embedded-decision-not-principal-owned` reported — replacing the single DB-01 anecdote
(issue #66: `eng-ladder` blind read "mandatory principal ownership", dispatch read "optional
escalation", the accurate call was builder-owned with a required consult) with a measurement.

**What ran.** The acceptance command, verbatim, on 2026-08-14: 48 sessions, CLI 2.1.231,
`claude-sonnet-5` observed, clean-room, one run excluded on a structured error, four graded on
timeout-partial transcripts. Capture at
[`evals/baselines/2026-08-14-ladder/`](../../../evals/baselines/2026-08-14-ladder/decisions.md)
(benchmark + decisions note). **Correction, 2026-08-17:** this record originally said the capture
resolves `REUSABLE` on the capture host and therefore stands as the cluster's stored 'before'. It
does not, and did not when written — `eval_baseline.py evals/routing/ladder.json --model sonnet
--clean-room` reports `STALE: diverged on evaluator, plugin`, verified on CPython 3.11.15, the
capture's own recorded runtime, so the runtime caveat the record gave was never the binding cause
(`scripts/eval_clean_room.py` changed the day after the capture, and the plugin hash moved). The
provenance schema has since gone v3 → v4 as well. Treat the capture as evidence of what LADDER-001
measured, never as a before-side: any paired ladder run owes a fresh capture. It was in any case
not the Mode 3 trim's before-side,
which requires a targeted Mode 3 case authored first and a fresh capture including it (the case
edit changes the exact `eval_sources` identity; LADDER-002 carries the protocol). The reuse is
also identity-bound, not unconditional: the evaluator identity pins the runtime (CPython 3.11.15
recorded), so a host on another Python reports `STALE: diverged on evaluator` and owes that
runtime or a fresh capture.

## The result

- **`neg-embedded-decision-not-principal-owned`: 0/3 fired — PASS.** The **ownership half** of
  the issue #66 miscalibration does not reproduce: builder-owned work carrying one embedded,
  builder-recordable decision drew no principal, no distinguished, no eng-ladder in any run.
  This case's decision is deliberately reversible with no standing authority, so it tests only
  the no-over-ownership boundary — the required-consult half (whether a verdict rejects
  "optional escalation") is not measured by this run; the consult-required positive fired 0/3
  and that half awaits LADDER-002's behavioral contract.
- **All seven negatives passed with their forbidden sets at 0% fire.** No forbidden agent fired
  anywhere in the batch. Stated precisely: the five cluster-wide negatives saw zero cluster
  members fire; the two narrowed disambiguation negatives saw their forbidden targets fire 0/3,
  and one of them (`neg-org-five-year-standard-not-principal`) recorded a single
  `distinguished-architect` firing — a *permitted* sibling doing the correct routing its
  narrowing exists to allow, recorded as `cluster_fire_rate: 0.333` in the benchmark. By the
  item's own decision rule, the Mode 1 ownership-vs-consult guidance and the description's
  scoped-work narrowing are **not indicted** — the calibration the guidance shipped to fix holds
  under measurement.
- **`pos-embedded-principal-fork-consult-required`: 0/3 — FAIL.** The consult-required shape never
  drew `eng-ladder`. Read against the suite's documented headless property and the 2026-07
  anchor's matching pass/fail shape (same two positives passing, the six shared positives failing
  identically — this consult-fork positive itself postdates the anchor and has no historical
  rate), the
  positive half of the split reads as under-measured in headless capture, consistent with the
  historical shape (per lesson 2, the anchor cannot rule out a regression) —
  but the skill-member split is a real signal, recorded below.
- **Positives overall 2/9** (`pos-distinguished-adr` 2/3, `pos-engladder-altitude` 3/3):
  consistent with the historical shape on the six shared positives. Per lesson 2 below, the
  provenance-free anchor cannot *rule out* a regression — this reading is the cheaper prior, not
  a cleared gate.

## The discovery this run surfaced (routed, per the closeout rule)

`eng-ladder`'s three advertised modes fired 3/3 (altitude question), 0/3 (assess-at-a-bar — also
0 in the 2026-07 anchor, a two-capture recurrence), and 0/3 (the embedded-consult-fork shape,
first measurement). Two of the three modes the description advertises never draw the skill in
headless capture. Routed to **LADDER-002** (roadmap, `decision-needed`). *(Routing updated
2026-08-14, same day: the follow-up
[investigation](ladder-002-investigation-2026-08-14.md) diagnosed the two failures to different
instruments — the assess case needs an inline-diff case repair and the consult calibration a
behavioral-contract port — and found a description rewrite explicitly **not** indicated, so this
record's original "any repair is a description edit" direction is superseded; the roadmap item
carries the current options.)* Not ledgered separately — the roadmap item is the single owner.

## Ride-along dispositions (owed by this closeout)

Two PROP-002 deferrals rode this item; neither is silently stranded:

- **Mode 1 consult-and-decision-record protocol trim — dropped with reason.** The Group 4 rescan
  ([`group4-rescan-2026-08-14.md`](group4-rescan-2026-08-14.md)) flipped the finding to keep:
  ownership-vs-consult is a typed edge between separate agent contexts, not ceremony between rungs
  one person occupies. This run adds the measured half: the guidance's negative boundary holds at
  0% over-fire, so there is no defect for a trim to fix.
- **Mode 3 growth-feedback trim — re-homed to LADDER-002.** The Group 4 rescan upheld the finding
  (the only PROP-002 finding whose severity survived all four group rescans: agents do not
  practice, and the nearest real consumer is owned by `self-improve-loop`/`prompt-engineer`). The
  freeze this item imposed is now lifted; the trim's measurement follows LADDER-002's fresh
  paired protocol (a targeted Mode 3 case authored first, then a fresh 'before' including it —
  this capture carries no Mode 3 case and cannot serve as that half's before-side), and whether
  to buy it is the operator's call, recorded as LADDER-002's decision.

## Lessons

1. **The negative half is the trustworthy instrument.** Every load-bearing conclusion here rests
   on forbidden sets holding at 0% fire, which are defect-signals at any rate; the positive half
   reproduced the documented headless under-fire and settled nothing by itself. Buying 3 runs/case was worth it
   for the negatives alone.
2. **A stale anchor still earned its keep — as anecdote, not evidence.** The 2026-07 benchmark
   could not be diffed (no conditions/provenance — the exact defect the provenance schema fixed),
   and matching threshold-level pass/fail booleans cannot rule out a regression hiding inside
   changed conditions; only a comparison-grade 'before' can. What the anchor's matching shape
   *did* buy is a cheaper prior: the under-fire pattern is consistent with a long-standing
   property rather than something newly broken, which informed where the diagnosis looked first.
   Historical shape is a hint that guides investigation, never a gate that clears one.
3. **A measured no-change is a closeable outcome.** This item retires with zero edits: the
   guidance held, the capture is stored and reusable, and the one discovery routes to a named
   owner instead of an edit bought mid-round.
