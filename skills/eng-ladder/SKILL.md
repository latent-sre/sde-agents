---
name: eng-ladder
description: Use before starting any task that changes code or a design (skip single-file edits with an existing pattern to copy), when deciding what level of engineering a task needs ("who should handle this"), when asked to assess code or a design against a seniority bar ("review this at the principal level"), or to generate ladder-based growth feedback on a body of work.
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

Routing includes routing to yourself. Work stays in the current context when it fits the conversation you're already in; spawn the rung's agent when the work needs fresh context or runs alongside other work. For in-context work, load the matching altitude reference and work its method: [`references/builder.md`](references/builder.md), [`references/principal.md`](references/principal.md), or [`references/distinguished.md`](references/distinguished.md). Load **only** the tier that matches, and move up the moment it isn't enough — moving up means loading the next reference; a spawned agent never self-promotes, it reports the fork to its caller. The references paraphrase each rung's method and self-checks; the full bar stays the agent file (Mode 2) — on any conflict over method or bar, the agent file wins.

The `sre-tool` skill applies this routing inside its build pipeline, and each ladder agent's description and "Ladder position" section paraphrases its own rung so a spawned agent can escalate without loading this skill; the altitude references paraphrase the rungs the same way. This table is the source of truth for routing — on any conflict over which rung a task belongs to, the table wins; fix the paraphrase, not the table.

Infrastructure and service-operation work (deploying, configuring, or troubleshooting the lab itself) routes to `homelab-platform`, outside this ladder; code that *runs on* the lab routes through the ladder as usual.

## Mode 2 — Assess work at a bar

The table above routes; it is not the bar. The full bar for each rung is that agent's definition file (`agents/sde-fullstack.md`, `agents/principal-engineer.md`, `agents/distinguished-architect.md`) — read the relevant one before scoring. Score the artifact against its current-level bar: **meets**, or **gaps** with cited evidence (specific lines or sections — no generic feedback). Then state the next-level delta: the two or three concrete things that would make this artifact next-rung work. Example: "The code works and is tested — the principal version would name the migration rollback plan and cut the config surface in half."

## Mode 3 — Growth feedback

For a body of work (several diffs or docs): identify recurring patterns, strengths at the current level, and the single highest-leverage next-level behavior to practice. One behavior, not a list — growth feedback that names ten things changes nothing.
