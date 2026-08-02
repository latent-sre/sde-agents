# 2026-08-01 LEARN-001 retro-boundary baselines — lineage

Three generations of artifacts live here; only `pair-v3/` is a valid like-for-like pair.

- `before/` — the original pre-edit capture (commit `dc73938`; sonnet, 420s, 3 runs, **no**
  clean-room, pre-v3 artifact schema). Valid as history for the tree it measured; not comparable
  to any clean-room artifact.
- `after/` — **removed 2026-08-01.** The capture at this path ran while the working tree was being
  rewritten by a parallel session (the runner then had no private-snapshot execution, so sessions
  loaded a moving tree). Its 9/9-at-100% result could not be attributed to any specific
  description and was ruled measurement-contaminated before commit; it was committed unknowingly
  during reconciliation and is deleted rather than left readable-as-evidence. The v3 runner's
  private frozen snapshot exists precisely so this failure mode cannot recur.
- `pair-v3/` — the authoritative pair, captured with the v3 provenance runner (clean-room, sonnet,
  420s, 3 runs, byte-identical cluster file throughout):
  - `before/` — pre-edit tree (`dc73938`, via a detached worktree passed as `--plugin-dir`).
  - `after/` — the reconciled tree as committed (`d027755`). Measured regression:
    `pos-micro-retro` 100%→33%, `pos-task-retro` 33%→0% — the description rewrite had dropped the
    operator's plain retro phrasings.
  - `after-merged/` — after the vocabulary-merge fix (`4be21cd`) restoring the four measured
    trigger phrases. This is the shipping description's capture.

Negatives fired 0% in every generation and every condition — the boundary held throughout; the
churn above is entirely about positive-trigger vocabulary and measurement validity.
