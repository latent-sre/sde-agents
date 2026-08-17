# `evals/baselines/` — what is actually in here

The name is aspirational. A **baseline** is a stored capture a future paired run can reuse as its
'before' side, and `scripts/eval_baseline.py` is the only thing that decides whether one qualifies.
**No capture in this directory currently qualifies** — every cluster resolves `STALE`, and the
provenance schema's v3 → v4 move plus the 2026-08-17 case retirements made that permanent rather
than incidental. Read the retention section of `../README.md` for the rule; this file is the map.

Three different kinds of thing live here, and they retire on different schedules:

## `history/` — round records, no captures

Distilled measurement records: what a round measured, under what conditions, and what it concluded.
Plain Markdown, **invisible to the resolver** (it globs `benchmark.json` and nothing else), and the
only thing most citations actually consume. These are archive records that happen to sit next to the
suite they describe; if `docs/archive/` ever becomes their home instead, nothing breaks but the
paths.

## Capture directories with a partial summary

`2026-07`, `2026-07-24`, `2026-07-30-pr48-review-fixes`, `2026-08-01-learn-001`,
`2026-08-01-self-improve`, `2026-08-10-rel-173`, `2026-08-14-ladder`. Each holds raw captures plus a
summary that names only some of its cases (18–54% as measured on 2026-08-17). The raw stays until the
summary records the rates — a summary that mentions a round without its numbers is not a substitute
for the capture.

`2026-08-13-prop-001` sits here for a different reason and is the one deliberate exception to the
`history/` collapse: `learning/candidates/lc_8f572581…json` pins this exact path in its evidence,
and the ledger **refuses** a hand-edit to that field (`evidence must match the first recurrence
source`). A path a ledger record cites is frozen — moving it would strand immutable evidence, so it
keeps its directory even though its content is now summary-shaped.

## Capture directories with no summary

`2026-07-30-donor-grafts`, `2026-07-31-p0-p1`, `2026-08-10-gate-001-field-probes`,
`2026-08-10-gate-001-first-live`. Here the raw **is** the record — there is nothing else — so none of
it can be retired before someone distils it. `2026-07-31-p0-p1` is the one to be most careful with:
it holds the only Codex CLI run this repository has ever recorded.

## If you are adding a capture

It goes in a new dated directory here (`--output-dir`), and it owes a summary in the same change —
either beside it or in `history/`. That is what makes it retirable later without losing what it
measured, and skipping it is how a directory ends up in the third category above.
