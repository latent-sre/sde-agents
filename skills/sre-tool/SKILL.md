---
name: sre-tool
description: Use when starting a new operator-facing or SRE tool — a dashboard, CLI, automation service, monitor, or internal web tool — or adding a major capability to one, and the work should run the full engineering ladder from requirements through review.
argument-hint: [what the tool should do]
---

Announce at start: "Running the sre-tool pipeline: requirements → right-sized design → build → review → verify."

## Phase 0 — Requirements (don't skip)

Establish before designing. Infer from context and the codebase where possible; ask the user only what genuinely can't be inferred, batched into one question round:

- **Operator and moment**: who uses this, and when — during an incident (optimize for speed and zero ambiguity) or routine work (optimize for automation)?
- **Inputs, outputs, systems touched** — and whether the tool is read-only or mutating.
- **Blast radius** if the tool itself misbehaves; auth and audit needs.
- **Interface**: CLI, TUI, or web — the thinnest one that serves the operator, not the most impressive one.
- **Success criterion**: the observable behavior that proves it works.

## Phase 1 — Right-size the design

- Single component, low blast radius → design inline at SDE level: a few sentences of plan plus stated assumptions. No ceremony.
- Multiple services, a data migration, or hard-to-reverse choices → spawn the `principal-engineer` agent for a short design doc; surface any one-way doors to the user before proceeding.
- Platform-shaping work (many teams or systems, multi-year consequences) → spawn `distinguished-architect` first.

Agents do not inherit this conversation. Pass each one full context: the Phase 0 requirements, repo layout and conventions, and constraints.

## Phase 2 — Build

Spawn `sde-fullstack` with the requirements, the design, exact repo paths and conventions, and the success criterion. For trivial scope, implement directly while holding to the same SRE-lens standards (observability, timeouts, idempotency, dry-run for destructive actions).

## Phase 3 — Review

Spawn `code-reviewer` on the resulting diff. Apply P0 and P1 findings; re-review if the fixes were substantial. Report P2/P3 findings to the user rather than silently applying them.

## Phase 4 — Verify and hand over

Run the tool and exercise its primary flow for real — not just the test suite. Final report: what was built, how to run it, what was verified end to end, the review verdict, and known gaps.
