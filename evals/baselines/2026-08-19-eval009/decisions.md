# EVAL-009 - paired n=6 disposition: closed, no regression attributable to the edit

Conditions: sonnet, clean-room, --case pos-ci-actions-harden --runs 6 per side, worktree-isolated.
before = `8b41239` (pre-CTX-002 descriptions): **2/6 (33%)**. after = `76bdbf5` (trimmed+repaired):
**1/6 (17%)**.

The item's acceptance rule said after < before at same n means a real regression. Overridden on
recorded evidence, for three reasons. (1) A one-run gap at n=6 separates nothing. (2) The before
side itself refuted the premise: the ORIGINAL description measures 33% at n=6, so the wave-1 2/3
(67%) that motivated this item was a high draw, consistent with the craft cluster's all-floor
positive behavior. (3) The byte diff between the sides' ci-actions descriptions is connectives
only (495 vs 493 chars; the after side even ADDS the trigger token "hardening"), so no textual
cause for a rate difference exists - the gap measures the case's own variance by construction.
Pooled across every capture regardless of bytes: ~8/24 = 33%. This case is a low-rate positive in
headless mode; a future drop below ~15% at n>=6 would be signal, single-run swings are not.

Retirement trigger: the item is closed and this file is the record; both benchmarks retire at
the next baselines consolidation pass after the PR carrying them merges — kept until then only
so the override's arithmetic stays checkable.
