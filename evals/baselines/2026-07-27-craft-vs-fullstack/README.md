# 2026-07-27 craft-vs-fullstack round — distilled record

Three directories (`-before`, `-after`, `-diagnose`) held one round; they retired to Git history on
2026-08-17 under the retention rule in `../../README.md` and this file is their record.

**Conditions, all runs:** opus (`models_observed: claude-opus-5`), `--timeout 420`, threshold 0.5,
3 runs per case, **no clean-room** (`clean_room` unrecorded — these predate that condition, so they
must not be diffed against any clean-room capture). Provenance predates the schema, so none of them
was ever reusable as a paired 'before' side.

## The repair the round shipped

| case | before | after |
|---|---|---|
| `pos-powershell-pester` | **0.0** | **1.0** |
| the 7 cluster negatives | 1.0 clean each | 1.0 clean each |

`pos-powershell-pester` went from never firing to firing every run, and no negative moved — the
repair added reach without widening the description onto near-misses. That is the whole positive
result of the round.

## The diagnose run, and what it refuted

`-diagnose` measured nine positives in one pass and split them cleanly in two:

- **Zero-fire (0.0):** `pos-backend-pagination`, `pos-backend-webhook`, `pos-backend-resiliency`,
  `pos-frontend-table`, `pos-frontend-form`, `pos-fullstack-crosslayer`, `pos-fullstack-feature`
- **Fired every run (1.0):** `pos-code-craft-idioms`, `pos-ci-actions-harden`

That split is the finding, and it **refuted the empty-cwd hypothesis**: the two positives that
presuppose a repository passed 3/3 in the same empty working directory where the seven
agent-and-layer-expecting positives fired nothing. If the empty cwd were the cause, the
repo-presupposing cases would have failed first. The real causes are the two this cluster's `notes`
still document — preloaded craft skills are injected at startup and never register as "fired", and
agent-expecting positives under-fire in headless one-shot mode.

Read forward: `pos-fullstack-crosslayer` and `pos-fullstack-feature` were among the 26 agent-only
positives retired on 2026-08-17 for exactly the reason this run first measured, so those two rows
are the historical evidence for a decision taken three weeks later, not a live gap.
