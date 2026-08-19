# CTX-002 paired routing captures — summary, dispositions, retirement trigger

The round's narrative previously lived only in PR #154's body; this file is the in-repo record
the retention rule requires before any of this directory can ever retire.

Conditions: sonnet, `--clean-room`, `--runs 3`, timeout 180, concurrency 4, CLI 2.1.235.
`before/` at `8b41239` (pre-edit bytes), `after/` at `1103342` (14 trimmed descriptions),
`after-repair/` at `f232f77` (prompt-craft and ci-actions token restorations) — for those two
clusters `after-repair/` is the pair's after side and `after/` records the trim-only state that
motivated the repairs. `disposition/` holds the n=5/n=6 variance checks. The after batch was
interrupted by a Claude auth expiry between clusters five and six and resumed after `/login`;
auth state is not a measurement condition.

## Paired result (97 cases, 8 clusters)

Negatives: **0% forbidden-fire on every case, both sides** (52/52 assertions). Positives: 32
unchanged, 5 gains, 8 drops — every drop dispositioned:

| Cluster | before → after (passed/total) | Disposition of movement |
|---|---|---|
| verification-seam | 3/4 → 3/4 | pos-diagnose-why floor (0%) both sides — pair blind there |
| proportionality | 5/5 → 5/5 | all-negative cluster, clean |
| investigation | 5/7 → 6/7 | root-cause positives at/near floor both sides; one gain |
| retro-boundary | 6/9 → 7/9 | gains; pos-iterate-draft floor both sides (runbook steals it) |
| continuous-improvement | 10/10 → 10/10 | self-improve-loop positives held (one ±33% swap pair) |
| prompt-tooling | 9/12 → 8/12 → **10/12 after repair** | 4-drop pattern traced to lost `fix`/`request` tokens; repaired to aggregate parity (301 vs 300) |
| craft-vs-fullstack | 9/17 → 8/17 → 8/17 | 8 of 9 positives floor on all sides; ci-actions-harden dispositioned by n=6 (3/6) and later EVAL-009 paired n=6 (before-side bytes measure 2/6 — the 67% premise was a high draw) |
| homelab-ops | 31/33 → 30/33 | observability-alert 67→0 dispositioned variance (n=5: 4/5); add-service ±1 run; discovery-question +67 |

Floor cases (0% both sides — the pair proves nothing about them, disclosed in PR #154):
craft quartet ×5, root-cause ×2, prompt-tooling ×2, host-onboard, iterate-draft, lessons-learned.

## Retirement trigger

The `before/` and `after(-repair)/` benchmarks are **machine-reusable 'before' capital** via
`scripts/eval_baseline.py` — `homelab-ops/before` is additionally the capture LANE-001's
ride-along requires to exist before `onboarding-map`'s description moves. Retire nothing here
until **both** hold: (1) CTX-002 and LANE-001 are closed (the held eng-ladder and onboarding-map
trims will consume these benchmarks as their 'before' sides), and (2) `eval_baseline.py` reports
the benchmarks STALE for every remaining consumer. After that, this summary is the record and
the raw retires per `evals/README.md`'s retention rules. `disposition/` retires with CTX-002's
close regardless — its verdicts are recorded above and in `2026-08-19-eval009/decisions.md`.
