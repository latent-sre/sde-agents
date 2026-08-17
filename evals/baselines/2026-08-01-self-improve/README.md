# 2026-08-01 self-improve-loop round — distilled record

The LEARN-001 round that built the learning lifecycle (`self-improve-loop`, the runbook
dispositions, and the Learning packet slot) measured itself seven times as it went. Six of those
generations retired to Git history on 2026-08-17 under the retention rule in `../../README.md`;
this file is their record. **`final-live/` is retained in full** — `docs/fleet-roadmap.md` cites it
as LEARN-002's live rates, so it is evidence a live item still rests on.

## The generations, and why they are not one series

| Generation | Model | Behavioral timeout | Provenance | What it was |
|---|---|---|---|---|
| `before/`, `after/` | **opus** | 600s | none | first pass; `after/` captured routing only |
| `iteration-2-smoke/` | sonnet | 600s | v1 | one-run smoke check, not a rate |
| `comparable-v2/{before,after}` | sonnet | 600s | v1 | the cleanest same-tier behavioral pair |
| `final-before/`, `final-after/` | sonnet | 600s | v1 | the round's closing pair |
| `final-live/` | sonnet | 420s | **v3** | current state; the cited one |

**Read across generations with care — three conditions moved mid-round.** The model tier changed
(`before`/`after` ran opus, everything after it sonnet), the behavioral timeout dropped 600s → 420s
at `final-live`, and the provenance schema went none → v1 → v3. Per this suite's own rule that the
timeout and the model are one decision, and that artifacts differing on conditions must not be
diffed, **only the within-generation pairs below are like-for-like.** The case set also grew across
generations, so a case absent from an early capture was not failing — it did not exist yet.

Two pairs are also incomplete and were never completed: `after/` holds routing only (no behavioral
side), and `comparable-v2/before` holds behavioral only (no routing side).

## What the pairs measured

**`comparable-v2` before → after** (sonnet, 3 runs, behavioral only) — the round's strongest
evidence, and the reason the lifecycle text shipped. Nine contracts moved up, one moved down:

- `runbook-disposition-create` 0/3 → **3/3**; `runbook-disposition-propose` 0/3 → 2/3;
  `runbook-disposition-update` 2/3 → 2/3 (flat)
- `learning-slot-readonly-agent` 0/3 → **3/3**
- `self-improve-lifecycle-merge` 0/3 → **3/3**; `self-improve-freshness-gate` 0/3 → **3/3**;
  `self-improve-provider-regression-workaround` 0/3 → **3/3**
- `self-improve-runbook-destination` 1/3 → **3/3**; `self-improve-read-only-proposal` 0/3 → 2/3;
  `self-improve-untrusted-source-quarantine` 2/3 → 3/3;
  `self-improve-unknown-failure-handoff` 2/3 → 3/3
- `self-improve-promotion-gate` 3/3 → **2/3** — the one regression, and it stayed unresolved

**`final-before` → `final-after`** (sonnet, 3 runs) — the closing pair. The runbook trio settled
(`update` 2/3 → 3/3, `create` 0/3 → 3/3, `propose` 0/3 → 3/3) and `runbook-destination` went
0/3 → 3/3, but three contracts did not follow: `lifecycle-merge` 1/3 → **0/3** (a regression
against `comparable-v2`'s 3/3), `freshness-gate` 0/3 → 0/3 (never repaired in this pair), and
`learning-slot-readonly-agent` 0/3 → 1/3. Routing over `continuous-improvement`:
`pos-learning-successful-scan` 0.667 → 1.0, `pos-learning-runbook-gap` 0.0 → 0.0,
`pos-learning-rejected-candidate` 0.667 → 0.667, all six negatives clean at 0% fire on both sides.

**`before` → `after`** (opus, 3 runs, routing only) — `pos-learning-runbook-gap` 0.0 → 0.667 and
`pos-learning-rejected-candidate` 0.333 → 1.0, with all six negatives clean both sides. This is the
only opus evidence in the round and cannot be compared with any sonnet generation above.

**`iteration-2-smoke`** (sonnet, **1 run**) — a smoke check, not a measurement: `lifecycle-merge`
and `freshness-gate` at 0/1, everything else 1/1, and `pos-learning-runbook-gap` routing at 1.0.
A single run cannot distinguish a rate from a draw; it is recorded only because it is the reason
iteration 2 continued.

## Where the round actually landed

`final-live/` (retained) is the current-state record. Seven contracts sat at **0/3** there:
`learning-slot-readonly-agent`, `learning-slot-operational-agent`,
`learning-runbook-namespaces-compose`, `runbook-disposition-propose`,
`self-improve-lifecycle-merge`, `self-improve-promotion-gate`, and
`self-improve-canonical-triaged-candidate` — with `learning-owner-prompt-engineer-full-retro` at
1/3 and several others at 2/3. Routing had `pos-learning-runbook-gap` at 0.333 (still failing) and
every negative clean. That failing set, not this file's history, is what LEARN-002 owes; the
roadmap item states its closure conditions.

Note the shape worth keeping: `lifecycle-merge` reached 3/3 in `comparable-v2/after`, fell to 0/3
by `final-after`, and is still 0/3 at `final-live`. A contract that passed once and then stopped is
a different problem from one that never passed, and only the cross-generation view shows it.

## What retired, and what did not

Retired to Git history (4,986 lines, last present at the commit that removed them): `before/`,
`after/`, `comparable-v2/`, `final-before/`, `final-after/`, `iteration-2-smoke/`. Nothing in the
tree cited any of them, none can ever be reused (all pre-v3, and the case bytes have since
changed), and every rate they held is stated above.

Retained: `final-live/`, cited by `docs/fleet-roadmap.md` as LEARN-002's live rates.
