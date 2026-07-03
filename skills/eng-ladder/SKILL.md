---
name: eng-ladder
description: Use when deciding what level of engineering a task needs ("who should handle this"), when asked to assess code or a design against a seniority bar ("review this at the principal level"), or to generate ladder-based growth feedback on a body of work.
argument-hint: [task, diff, file, or design doc]
---

## The ladder

| | sde-fullstack | principal-engineer | distinguished-architect |
|---|---|---|---|
| **Scope** | a tool, feature, or service | a system across services/teams | platform or org, across years |
| **Horizon** | this release | 6–18 months | 3–5 years |
| **Core question** | does it work, and can it be operated? | is this the right design, and what's the blast radius? | is this the right problem, and will the solution survive the org? |
| **Artifacts** | working, verified code + tests | design docs, decision records, phased plans | ADRs, north-star architecture, build/buy analyses |
| **Failure lens** | handles errors, timeouts, retries | failure modes, rollout/rollback | failure domains, blast-radius containment |

## Mode 1 — Route a task

Match the task to the lowest rung whose core question it raises. Signals it needs principal: multiple services or teams, a migration, a hard-to-reverse choice, "design" or "how should we" phrasing. Signals it needs distinguished: build-vs-buy, platform consolidation, anything measured in years. When in doubt, route DOWN — a lower rung that recognizes its limit and escalates is cheaper than ceremony, and the agents are prompted to escalate.

## Mode 2 — Assess work at a bar

Read the artifact. Score it against its current-level bar: **meets**, or **gaps** with cited evidence (specific lines or sections — no generic feedback). Then state the next-level delta: the two or three concrete things that would make this artifact next-rung work. Example: "The code works and is tested — the principal version would name the migration rollback plan and cut the config surface in half."

## Mode 3 — Growth feedback

For a body of work (several diffs or docs): identify recurring patterns, strengths at the current level, and the single highest-leverage next-level behavior to practice. One behavior, not a list — growth feedback that names ten things changes nothing.
