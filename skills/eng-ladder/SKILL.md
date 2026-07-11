---
name: eng-ladder
description: >-
  Set your engineering altitude for a coding task, then load the matching tier — match depth to the
  task's ambiguity and blast radius. Use at the start of any work that changes code or a design (skip
  single-file edits with an existing pattern to copy): builder (a scoped, well-defined change inside
  one component), principal (cross-cutting design, a contract/schema change, a migration, real blast
  radius), or distinguished (high-ambiguity architecture, build-vs-buy, a standard everything else
  follows). Read the one tier file for the full method.
---

# Engineering ladder — pick your altitude

Judge the task's **ambiguity** and **blast radius**, then work at the matching tier. When in doubt,
think one level up, then drop to execution. Load **only** the tier that matches.

- **Builder** — scoped change inside one component with a clear spec; match patterns, edge cases,
  test, ship. → [`references/builder.md`](references/builder.md)
- **Principal** — spans components, alters a contract/schema, needs a design, or carries real blast
  radius; call-site/impact analysis + expand→contract migration. → [`references/principal.md`](references/principal.md)
- **Distinguished** — high ambiguity, multiple systems, build-vs-buy, or a standard everything else
  follows; frame the problem and the tradeoffs before any code. → [`references/distinguished.md`](references/distinguished.md)

Escalating in the main loop means loading the next tier's file and continuing; a spawned agent never
self-promotes — it reports the fork to its caller. Work stays in the current context when it fits the
conversation you're already in; spawn the rung's agent (`sde-fullstack`, `principal-engineer`,
`distinguished-architect`) when the work needs fresh context or runs alongside other work.

To assess existing work against a rung's bar ("review this at the principal level"), read that rung's
agent file — it is the full bar; these tier files are the inline method, and on any conflict the agent
file wins. Score **meets**, or **gaps** with cited evidence, then state the next-level delta; for
growth feedback on a body of work, name the single highest-leverage next-level behavior — one, not a
list. Infrastructure and service-operation work (deploying, configuring, or troubleshooting the
lab itself) routes to `homelab-platform`, outside this ladder; code that *runs on* the lab picks a
tier as usual.
