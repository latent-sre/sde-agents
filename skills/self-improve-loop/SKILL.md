---
name: self-improve-loop
description: Use when output quality is measurable and iteration demonstrably improves it — hardening a draft against review findings, grinding code up against a failing test whose cause is already diagnosed, or improving the fleet's own agent/skill definitions — and for the micro-retro at the end of any task that needed a fix cycle. Covers generate→evaluate→refine, act→verify ordering, guardrails for unattended outer loops, and moving recurring lessons into deterministic checks. For any undiagnosed bug, test failure, or unexpected behavior, use sde-agents:root-cause first — this loop iterates on known gaps; it does not diagnose.
argument-hint: [what to improve, and the criteria or verifier]
---

# Self-improvement loops

Make output better by **checking it and acting on the check** — not by trying harder in one pass.

**Start simple.** A single well-prompted pass handles most work. Add a loop only when (a) you can
*measure* quality against clear criteria and (b) iteration *demonstrably* improves the result. A loop
with no real evaluator is just extra tokens.

## Pattern 1 — Evaluator-optimizer (generate → critique → revise)

One role generates a candidate; a **separate** role evaluates it against explicit criteria and returns
actionable feedback; the generator revises. Loop until the evaluator is satisfied or the budget is hit.

- **Use when** the criteria are articulable (review findings, a rubric, a failing test) and the gap
  between "first draft" and "good" is real.
- **In this fleet:** `sde-agents:sde-fullstack` generates → `sde-agents:code-reviewer` evaluates — its findings are the
  feedback the author refines against; the `sde-agents:sre-tool` review phase is the formal checkpoint.
- **Separate the roles.** A fresh-context evaluator catches more than self-critique in the same
  context — bias toward a second lens for anything load-bearing.

## Pattern 2 — Act → verify → repeat

The leverage is in *verify* — an action you don't check is an assumption. Order verifiers
**cheapest-and-surest first**:

1. **Deterministic checks** — tests, linters/type-checks, `scripts/validate_fleet.py` for fleet
   edits, the `readonly-guard` hook. Fast, reliable, no judgment risk. **Default to these.**
2. **Observed signal** — run it and read the result: the failing assertion clears, the mission
   transaction succeeds end to end (never a substitute flow that happens to work).
3. **LLM-as-judge** — a reasoning review (`sde-agents:code-reviewer`) for what rules can't encode: design,
   intent, subtle correctness. Use it *after* the cheap checks, not instead of them.

**Move the lesson left.** When the same failure recurs, encode it as a rules-based check — a test, a
lint rule, a validator rule, a hook — rather than re-judging it by reasoning each time.

## Pattern 3 — The unattended outer loop ("Ralph")

A shell loop re-invokes a **fresh** agent process each iteration against a spec + checkbox backlog in
files, so durable state lives in the repo (spec, backlog, code, git history), not a context window
that rots. Each pass: read the backlog, do the **next one item**, run the verifier, commit *only on
green*, exit; the loop restarts clean.

- **Use when** the work is large, decomposable, and **test-backed**. Not for triage, review, or
  anything that touches the lab.
- This repo deliberately ships no loop scaffold yet. If you build one, four rails are
  **non-negotiable**, and it is hand-run only — never CI- or agent-invoked:
  1. Branch only — the loop never touches main or deploys anything.
  2. A hard verify gate every iteration — red means the iteration is discarded, not committed.
  3. Bounded — a max-iteration cap plus an explicit exit (backlog empty AND verifier green).
  4. A human reviews before merge. The loop produces a diff on a branch, never a shipped change.

  An outer loop with no hard verifier makes confident messes at machine speed; the verifier *is* the
  safety system.

## Micro-retro — how the loop learns

At the end of any task that needed a fix cycle (a review round, a failed verification, a re-spawned
builder), answer two questions before closing out:

1. **What failed more than once** — across iterations of this task, or across recent tasks?
2. **Which deterministic check would have caught it** before the evaluator did?

Then move **exactly one** lesson left: a test, a validator rule, a gate item, a hook, or an edit to
the agent/skill definition that misbehaved. Encode it yourself only when the target is inside the
task's granted scope — read-only roles and tasks without a commit grant **report the proposed check
in the wrap-up instead**, named precisely enough to implement. When you do encode it, name the
trigger in the commit message so the check's origin is auditable. One lesson per retro — a retro
that names ten things changes nothing (the same rule as `sde-agents:eng-ladder` growth feedback). No recurring
failure means no lesson — don't invent one. Fleet definitions are in scope: an agent or skill that
misroutes or misbehaves twice gets its definition fixed, not a workaround.

## Run the loop well

- **Bound it.** Set a max-iterations budget up front (often 2–3). No convergence by then → stop and
  hand off with what you found; don't spin.
- **Define "done" before you start.** The stop criterion is the evaluator passing, not "feels good."
- **One change per turn, then re-verify** — so you know which change moved the signal.
- **Stakes set depth.** Load-bearing or hard-to-reverse work earns a fresh-context second lens and a
  bigger iteration budget; routine work gets one pass plus the cheap checks.
- A verification failure you can't explain exits the loop — load `sde-agents:root-cause` and diagnose before
  the next attempt. Iterate here only on gaps whose cause is known.

## Output

State the **criteria**, each **iteration** (what changed → how it was verified → result), the **stop
reason** (criteria met / budget hit / handed off), and the micro-retro's one lesson — encoded, or
proposed if out of scope (or "none — no recurring failure"). Label verifications `[verified]`,
`[sourced]`, or `[unverified]` per the fleet evidence convention.

## Handoffs

- → `sde-agents:code-reviewer` as the evaluator lens; → `sde-agents:sde-fullstack` to apply a confirmed revision.
- → `sde-agents:root-cause` when verification fails for an unknown reason (the loop found a bug; now find its cause).
- → `sde-agents:prompt-craft` / `sde-agents:prompt-engineer` when the encoded lesson is an edit to a fleet definition.
