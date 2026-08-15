# `homelab-ops` re-baseline — 2026-07-24

Why this exists: `postmortem` joined the cluster on 2026-07-24 (backlog 1.4), taking it from 4
members / 15 cases to 5 / 18. The `2026-07/` capture therefore stopped being a like-for-like diff
target — its case set no longer matches. This was the replacement anchor for that five-member
cluster; the live suite has since expanded, so use it only as dated evidence.

Run: `python3 scripts/eval_routing.py evals/routing/homelab-ops.json --runs 3` (54 headless
sessions, deterministic transcript grading). Captured against the descriptions as they stood
*before* any of this review's edits, so it doubles as the "before" for the next description change.

## Result: 15/18 — positives 7/10, **negatives 8/8**

**The load-bearing signals are both good, and the new member is the strongest performer.**

- **No over-trigger anywhere.** All 8 negatives fired no cluster member in 0/3 runs, including the
  new `neg-sprint-retro` ("write up what happened in yesterday's sprint retro… action items"),
  which was written specifically to bait `postmortem` with its own vocabulary. Two negatives
  routed confirmably right (`frontend-craft` took the status dashboard, `prompt-craft` the
  description fix). Negatives are the variance-robust result: **no description is over-broad.**
- **`postmortem` positives 3/3 and 3/3.** The new skill routes reliably on both the implicit
  ("it's fixed now — write up what happened") and explicit ("do a postmortem on…") phrasings.
- **The runbook↔postmortem seam is clean in measurement.** No postmortem positive shows `runbook`
  in `also_fired`, and no runbook positive shows `postmortem`. This is why the reviewer-proposed
  negative-routing clause for `runbook`'s description was **not** landed: the fleet's own rule is
  no description edit without an observed failure to pin it to, and the seam it would guard is not
  failing in this capture. Re-check the live cluster rather than treating this dated result as
  evidence of its present behavior.
- **Agent positives remain the harness characteristic**, not a routing defect — `homelab-platform`
  fires 0–2/3 because a one-shot `claude -p` session tends to act inline rather than delegate (see
  `../../README.md`). Notably they moved *up* versus 2026-07 (troubleshoot-proxy 0/3 → 2/3,
  add-service 0/3 → 1/3) with no description change, which is variance and should be read as such.

## Comparison with `../../2026-07/homelab-ops/` (historical, not like-for-like)

| | 2026-07 | 2026-07-24 |
|---|---|---|
| members / cases | 4 / 15 | 5 / 18 |
| negatives | 7/7 | 8/8 |
| skill positives | 4/4 at 100% | 6/6 passing (2 at 67%, variance) |
| agent positives | 1/4 cases passing | 1/4 cases passing (rates up) |

## What would be a real regression here

A negative that fires at all, or a skill positive collapsing from 3/3. Agent-positive rates are
noisy by construction; weight them lightly until these cases migrate to `claude plugin eval`.
