# `evals/baselines/` — what is actually in here

The name is aspirational. A **baseline** is a stored capture a future paired run can reuse as its
'before' side, and no capture in this directory qualifies for that job — every routing cluster
resolves `STALE` against the current evaluator/plugin identity, and the script that once automated
that check (`eval_baseline.py`) was retired 2026-09-01. What remains here is retained for a
narrower reason: something outside this directory still names it or still needs it.

**2026-09-01 consolidation.** Every raw capture no live document reached — an uncited directory,
or a cited one whose summary already carried its outcomes — was `git rm`'d in one pass. The bytes
are not gone: `git show <rev>:<path>` recovers any of them from history before commit `e34871d`.
What is left below is only what a live document (`docs/fleet-roadmap.md`, `docs/README.md`, a
decision record, the roadmap history archive, `evals/README.md`, or a script/test) still links to,
names by path, or states an explicit reason to keep.

## `history/` — round records, no captures

Distilled measurement records: what a round measured, under what conditions, and what it concluded.
The only thing most citations actually consume. These are archive records that happen to sit next
to the suite they describe; if `docs/archive/` ever becomes their home instead, nothing breaks but
the paths.

Mostly Markdown, with one exception that states the rule for any future one:
`2026-08-15-learn-002-tool-events.json` is raw `stream-json` retained **because its record's claim is
not checkable without it** — the `allowed_tools: []` finding turns on `tool_use` blocks correlated
with their results, and the behavioral runner grades and discards the transcript. Distillation is for
evidence a summary can carry; a record that says "the raw is why you can believe this" keeps its raw
beside it, named for the record it belongs to. Retiring this file once (PR #145) broke exactly the
claim it backed, which is how the exception earned its sentence here.

## What survives outside `history/`, and why

Every one of these is named by path (or by an explicit retirement condition) in a live document.
Where only a directory's summary is named, its raw capture was cut; where a live document says a
capture must not retire yet, the raw stays until that condition is met.

- **`2026-07/README.md`, `2026-07-24/behavioral/README.md`, `2026-07-24/homelab-ops/README.md`** —
  self-contained routing/behavioral narratives (every rate, every case) named by `evals/README.md`
  as historical cluster anchors. Their raw `benchmark.json` files added nothing the prose doesn't
  already state, so they retired; the summaries stay as the dated shape-check they're cited for.
- **`2026-07-31-p0-p1/host-conformance/`** — the only Codex CLI run this repository has ever
  recorded (`codex-cli 0.145.0`), cited by exact version in
  `docs/archive/2026-09/roadmap-history-2026-09-01.md`. No summary exists for this round, so the
  raw *is* the record; the sibling `behavioral/`, `investigation/`, and `routing-comparison.json`
  captures from the same round are uncited and retired.
- **`2026-08-01-self-improve/README.md` and `final-live/`** — `final-live/` is retained in full
  because the roadmap history cites it as LEARN-002's live rates; a live item rests on it. The six
  other generations that round produced were already retired before this pass (2026-08-17).
- **`2026-08-10-gate-001-first-live/verifier.json`** — `scripts/packet_lint.py` quotes this file
  verbatim as the worked example of an honest no-evidence verification packet. Its sibling
  `gate.json` is uncited and retired.
- **`2026-08-10-rel-173/conditions.md`** — cited by the roadmap history for the pre-correction
  `1.7.3` skill-inventory count (19 skills). The two raw `.txt` transcripts beside it are uncited.
- **`2026-08-11-ladder/benchmark.json`** — named a historical anchor by both `docs/fleet-roadmap.md`
  and the roadmap history, which states it "retires when \[LADDER-002] closes." LADDER-002 is still
  open, so this stays.
- **`2026-08-12-handoff-001-diagnostic/producer/`, `-digest-diagnosable/`, `-digest-outcomes/`,
  `-digest-reader/`, `-digest-refix/`, `-producer-amended-x3/`, `-producer-x3/`** — the salvaged
  2026-08-12 sonnet-testing arc. The roadmap history states explicit, unmet retirement triggers:
  the producer batches retire once the producer contract settles green in LEARN-002's second
  batch; the digest diagnostics retire once `handoff-builder-rejects-digest-mismatch` resolves with
  a written receipt grammar. Neither has happened, so all seven stay. The sibling
  `2026-08-12-handoff-001-diagnostic/builders/` capture is not named by that trigger (its runner
  mechanism was superseded by the 2026-08-15 `--allowedTools` fix) and retired.
- **`2026-08-13-prop-001/README.md`** — already summary-only; its raw retired in 2026-08-17's pass
  because a learning-ledger record pinned this exact path in its evidence.
- **`2026-08-14-ladder/`** — `decisions.md` is self-contained (every cited rate, and the `STALE`
  resolution `docs/README.md` quotes, is stated in prose), but the roadmap history names
  `benchmark.json` itself by exact path (the per-run timeout and exclusion detail behind the
  `STALE: diverged on evaluator, plugin` resolution), so the raw stays beside the note.
- **`2026-08-18-ctx-002/`** — kept whole, raw included. `docs/fleet-roadmap.md`'s Constraints line
  is explicit: "The v4 benchmarks in `evals/baselines/2026-08-18-ctx-002/` must not be retired while
  this item or LANE-001 is open," and the directory's own `decisions.md` repeats the same
  condition. Both CTX-002 and LANE-001 are still open.
- **`2026-08-18-handoff-001-producer-r2-x3/benchmark.json`** — the roadmap history: "the 2026-08-18
  rerun capture retires with the producer batches" above, which have not retired.
- **`2026-08-19-eval009/decisions.md`** — the item this batch measured is closed and the file's own
  retirement trigger says the raw retires "at the next baselines consolidation pass after the PR
  carrying them merges" — this pass. Its `before/`/`after/` raw retired accordingly.
- **`2026-08-19-settling/`** — kept whole, raw and the gitignored `failing-run-evidence.json`
  sidecars included. `docs/fleet-roadmap.md` and the roadmap history both cite
  `decisions.md` by path, and that file's own retirement trigger has not fired: these benchmarks
  are the 'before' side of LEARN-002's second settling batch and of HANDOFF-001's confirmation run,
  and it says the sidecars may be deleted only once the widen-vs-redesign ruling lands — neither
  has happened.
- **`2026-08-29-gate-006/README.md`** — a comprehensive distillation (every rate, the timing data,
  the mechanism finding) cited by path from `docs/decisions/2026-08-29-homelab-live-effect-gate.md`
  and the roadmap history. Its `Contents` section states what each raw subdirectory held; none of
  it is cited beyond what the README already carries, so `before/tier/`, `after/tier/`, and
  `diagnostic-read-granted/` retired.

## The retention rule for anything added here going forward

A raw capture retires once a summary carries every outcome it would be consulted for, **and** no
live document states a reason it must still exist raw (a pending pair, an unmet retirement
trigger, a fact only the raw contains). Write the summary before deleting anything — a citation
survives deletion, the ability to check it does not — and if a live document ties a capture's
retirement to a condition, name that condition in the capture's own note so the next consolidation
pass does not have to re-derive it from context.

## If you are adding a capture

It goes in a new dated directory here (`--output-dir`), and it owes a summary in the same change —
either beside it or in `history/`. That is what makes it retirable later without losing what it
measured.
