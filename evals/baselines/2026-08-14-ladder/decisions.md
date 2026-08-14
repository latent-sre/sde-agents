# 2026-08-14 ladder capture — LADDER-001 acceptance run

**Command (the roadmap's acceptance invocation, verbatim in effect):**

```bash
python3 scripts/eval_routing.py evals/routing/ladder.json --runs 3 --model sonnet --clean-room \
  --output-dir evals/baselines/2026-08-14-ladder
```

Conditions: CLI 2.1.231, `model_requested: sonnet` (`claude-sonnet-5` observed in every graded
run), timeout 180s, threshold 0.5, concurrency 4, clean-room. 16 cases × 3 runs = 48 sessions;
one run excluded (structured error result on `pos-principal-migration`), four runs graded on
partial transcripts after the 180s timeout — each noted in `benchmark.json`.
`eval_baseline.py --model sonnet --clean-room` resolves this capture `REUSABLE`.

## The two rates LADDER-001 exists to record

| Case | Rate | Verdict |
|---|---|---|
| `pos-embedded-principal-fork-consult-required` | **0/3** | FAIL — the consult-required shape drew `eng-ladder` in no run |
| `neg-embedded-decision-not-principal-owned` | **0/3 fired** | PASS — principal, distinguished, and eng-ladder all stayed silent in every run |

## Reading

**The negative half — the half issue #66 was about — is clean.** All seven negatives passed at a
0% fire rate, including both disambiguation negatives and the issue #66 calibration case. No
forbidden agent fired anywhere in 48 sessions: nothing re-owned builder work, nothing summoned the
meta-router onto scoped work. Per the roadmap's own decision rule ("a forbidden agent that fires
is evidence the guidance is insufficient"), the Mode 1 ownership-vs-consult text and the
description's scoped-work narrowing are **not indicted**.

**The positive half under-fires, in exactly the shape the suite documents.** 2/9 positives passed
(`pos-distinguished-adr` 2/3, `pos-engladder-altitude` 3/3). The 2026-07 stored anchor — not
comparison-grade (no conditions/provenance), but a shape check — shows the *identical* pass/fail
pattern on its twelve shared cases: same two positives passing, the six shared positives failing
identically (the consult-fork positive postdates the anchor and has no historical rate), all negatives
clean. So this is a reproduction of the known headless-mode property (`evals/README.md`: agent
positives systematically under-fire because a one-shot session does the work instead of
delegating), not a regression introduced since.

**The one genuinely new signal is the skill-member split.** `eng-ladder` is a skill, which the
under-fire caveat does not excuse, and its three advertised modes fired very differently: the
altitude question 3/3, the assess-at-a-bar phrasing 0/3 (also failing in the 2026-07 anchor — a
two-capture recurrence), and the embedded-consult-fork shape 0/3 (first measurement; the case
postdates the old anchor). Two of the three modes the description advertises never draw the skill
in headless capture. If a repair is bought it goes to the description — never the grader — and
this capture is the stored 'before' for it (LADDER-002 on the roadmap owns that decision).

Raw per-case rates live in `benchmark.json` beside this note.
