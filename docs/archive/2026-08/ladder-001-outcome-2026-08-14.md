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
(benchmark + decisions note); `eval_baseline.py --model sonnet --clean-room` resolves it
`REUSABLE`, so it stands as the cluster's stored 'before' for any future description edit.

## The result

- **`neg-embedded-decision-not-principal-owned`: 0/3 fired — PASS.** The issue #66 miscalibration
  does not reproduce: builder-owned work carrying one embedded, builder-recordable decision drew
  no principal, no distinguished, no eng-ladder in any run.
- **All seven negatives passed at 0% fire.** No forbidden agent fired anywhere in the batch. By
  the item's own decision rule, the Mode 1 ownership-vs-consult guidance and the description's
  scoped-work narrowing are **not indicted** — the calibration the guidance shipped to fix holds
  under measurement.
- **`pos-embedded-principal-fork-consult-required`: 0/3 — FAIL.** The consult-required shape never
  drew `eng-ladder`. Read against the suite's documented headless property and the 2026-07
  anchor's identical pass/fail shape (same two positives passing, same seven failing), the
  positive half of the split is under-measured in headless capture rather than newly broken —
  but the skill-member split is a real signal, recorded below.
- **Positives overall 2/9** (`pos-distinguished-adr` 2/3, `pos-engladder-altitude` 3/3): a
  reproduction of the historical shape, not a regression.

## The discovery this run surfaced (routed, per the closeout rule)

`eng-ladder`'s three advertised modes fired 3/3 (altitude question), 0/3 (assess-at-a-bar — also
0 in the 2026-07 anchor, a two-capture recurrence), and 0/3 (the embedded-consult-fork shape,
first measurement). Two of the three modes the description advertises never draw the skill in
headless capture. Routed to **LADDER-002** (roadmap, `decision-needed`): any repair is a
description edit measured against the stored 2026-08-14 'before', one delta per run, never a
grader change. Not ledgered separately — the roadmap item is the single owner.

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
  freeze this item imposed is now lifted and the stored capture makes the trim cheaply measurable;
  whether to buy the 'after' run is the operator's call, recorded as LADDER-002's decision.

## Lessons

1. **The negative half is the trustworthy instrument.** Every load-bearing conclusion here rests
   on 0%-fire negatives, which are defect-signals at any rate; the positive half reproduced the
   documented headless under-fire and settled nothing by itself. Buying 3 runs/case was worth it
   for the negatives alone.
2. **A stale anchor still earned its keep as a shape check.** The 2026-07 benchmark could not be
   diffed (no conditions/provenance — the exact defect the provenance schema fixed), but its
   identical pass/fail pattern is what separates "reproduced property" from "new regression"
   without a second paid run.
3. **A measured no-change is a closeable outcome.** This item retires with zero edits: the
   guidance held, the capture is stored and reusable, and the one discovery routes to a named
   owner instead of an edit bought mid-round.
