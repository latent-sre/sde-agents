---
name: prompt-craft
description: Use when creating or fixing anything an LLM consumes — prompts, agent definitions, skills, or tool descriptions — including requests like "write me an agent for X", "my skill never triggers", or "the model keeps ignoring this instruction". The lightweight inline path; for eval-driven iteration, use sde-agents:prompt-engineer; for multi-agent systems, sde-agents:multi-agent-architect.
argument-hint: [what to create or fix]
---

For quick jobs, apply this method inline. For anything needing iterative testing or a full agent/skill suite, spawn the `sde-agents:prompt-engineer` agent with the target file, the observed failure, and the success criteria.

## Method

1. **Success criteria first.** Define what a correct output looks like, measurably, before touching the prompt.
2. **Baseline.** Reproduce the failure with the current prompt. No edit without an observed failure to pin it to.
3. **Minimal change.** Fix the observed failure; don't rewrite everything you'd have phrased differently.
4. **Retest fresh.** Spawn a clean-context subagent with a realistic task; check it triggers and complies. Multiple reps — variance is a metric.

## The two rules that fix most agent/skill failures

**1. Description = trigger, not workflow.** The frontmatter description states only *when* to use the thing — the words a user would actually say. Never summarize the internal process: agents given a workflow summary execute the summary and skip the body. Diagnosis: "never triggers" → description doesn't match real user phrasing; "fires too often" → description is topic-shaped ("helps with documents") instead of action-shaped ("extracts form fields from PDFs").

**2. Match the form to the failure.**

| Observed failure | Right form |
|---|---|
| Knows the rule, breaks it under pressure | Hard prohibition + rationalization table + red-flag list |
| Complies, but output is the wrong shape | Positive recipe: state what the output IS, part by part |
| Omits a required element | Required slot in a template it must fill |
| Behavior should depend on a condition | Conditional keyed to an observable predicate |

Prohibitions backfire on shaping problems; recipes leave nothing to negotiate. Avoid nuance clauses ("unless it matters") — they reopen the negotiation.

## Frontmatter quick reference

Authority lives in frontmatter, not in prose. Before writing or editing any agent or skill
frontmatter, read [`references/claude-code-frontmatter.md`](references/claude-code-frontmatter.md) —
the fleet's single source of truth for Claude Code fields and their traps (tool inheritance on
omission, plugin-inert keys, `memory` auto-enabling write tools, the grant-vs-restrict split between
`allowed-tools` and `disallowed-tools`, and the skill-vs-agent precedence inversion). Platform facts
belong in that file and nowhere else — on drift, fix it there, never a local copy.
