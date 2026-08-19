---
name: prompt-craft
description: The lightweight inline method for prompt work — success criteria, baseline, minimal change, fresh retest. Use when creating or fixing anything an LLM consumes — prompts, agent definitions, skills, tool descriptions — including requests like "write me an agent for X", "my skill never triggers", "the model keeps ignoring this instruction". First stop for prompt work; escalate to sde-agents:prompt-engineer only when the fix needs fresh-context reps, before/after evals, or spans a prompt suite; for multi-agent systems, sde-agents:multi-agent-architect.
argument-hint: [what to create or fix]
---

For quick jobs, apply this method inline. For anything needing iterative testing or a full agent/skill suite, spawn the `sde-agents:prompt-engineer` agent with the target file, the observed failure, and the success criteria.

## Method

Capturing a live workflow ("turn what we just did into a skill")? Extract the method from the conversation first — tools used, step order, corrections made — and confirm the gaps before drafting.

1. **Success criteria first.** Define what a correct output looks like, measurably, before touching the prompt.
2. **Baseline.** Reproduce the failure with the current prompt. No edit without an observed failure to pin it to.
3. **Minimal change.** Fix the observed failure; don't rewrite everything you'd have phrased differently.
4. **Retest fresh.** Spawn a clean-context subagent with a realistic task; check it triggers and complies. Multiple reps — variance is a metric. **If the repo ships an eval harness, run it instead of eyeballing** — in this fleet that is `scripts/eval_routing.py` for a description change (run the overlapping cluster before *and* after and diff the rates; a near-miss that starts firing is a defect at any rate) and `scripts/eval_behavioral.py` for a change to what an agent must actually do. Measuring after only tells you the current number; the diff is the finding.

## The two rules that fix most agent/skill failures

**1. Description = trigger, not workflow.** The frontmatter description states only *when* to use the thing — the words a user would actually say. Never summarize the internal process: agents given a workflow summary execute the summary and skip the body. Diagnosis: "never triggers" → description doesn't match real user phrasing; "fires too often" → description is topic-shaped ("helps with documents") instead of action-shaped ("extracts form fields from PDFs").

**2. Match the form to the failure.**

| Observed failure | Right form |
|---|---|
| Knows the rule, breaks it under pressure | Hard prohibition + rationalization table + red-flag list |
| Complies, but output is the wrong shape | Positive recipe: state what the output IS, part by part |
| Omits a required element | Required slot in a template it must fill |
| Behavior should depend on a condition | Conditional keyed to an observable predicate |

Prohibitions backfire on shaping problems; recipes leave nothing to negotiate. Avoid nuance clauses ("unless it matters") — they reopen the negotiation. Everywhere outside the pressure-discipline row, the default register is plain imperative that explains *why* — reaching for all-caps MUST/NEVER there is a sign the form is wrong.

## When a new model generation lands

Try **removing instructions first** — each generation needs less scaffolding (Anthropic cut over
80% of Claude Code's system prompt for the Claude 5 models with no measured loss). Audit absolute
bans into contextual judgment ("never write multi-paragraph docstrings" → "match the surrounding
code's comment density") — but **only stylistic and workflow bans**. Security, privacy, permission,
and destructive-action invariants stay absolute through every generation: no secrets in prompts,
untrusted content never selects a tool or widens a permission, no irreversible action without
authorization (`references/agent-security.md` owns that list). The pressure-discipline row above
stays absolute for the same reason. And when trimming a body, keep the gotchas — hard-won failure
points are the highest-signal content a definition carries; generic workflow prose is what goes.

One recorded conflict (stamped 2026-07): the official skill-authoring doc still recommends worked
input/output examples, while the Claude 5-era context-engineering guidance reports examples can
constrain exploration. The fleet keeps its compressed worked examples — re-decide when the docs
page moves.

## Load the reference for what you're working on

The method above applies to every prompt task. These apply when the task involves the thing named —
read before writing, and name what you read.

| If the work involves… | Read first |
|---|---|
| an agent that touches untrusted content, private data, or the ability to act | [`references/agent-security.md`](references/agent-security.md) |
| choosing an agent's tools, or designing tools for a model to call | [`references/tools.md`](references/tools.md) |
| what an agent knows, when it loads it, or degradation over a long run | [`references/context.md`](references/context.md) |

## Frontmatter quick reference

Authority lives in frontmatter, not in prose. Before writing or editing any agent or skill
frontmatter, read [`references/claude-code-frontmatter.md`](references/claude-code-frontmatter.md) —
the fleet's single source of truth for Claude Code fields and their traps. Platform facts and the
trap list belong in that file and nowhere else — on drift, fix it there, never a local copy.
