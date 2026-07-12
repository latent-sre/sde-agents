---
name: prompt-craft
description: Use when creating or fixing anything an LLM consumes — prompts, agent definitions, skills, or tool descriptions — including requests like "write me an agent for X", "my skill never triggers", or "the model keeps ignoring this instruction". The lightweight inline path; for eval-driven iteration, use prompt-engineer; for multi-agent systems, multi-agent-architect.
argument-hint: [what to create or fix]
---

For quick jobs, apply this method inline. For anything needing iterative testing or a full agent/skill suite, spawn the `prompt-engineer` agent with the target file, the observed failure, and the success criteria.

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

**Agents** (`~/.claude/agents/*.md` user-level, `.claude/agents/*.md` project-level):
Required: `name`, `description` (the trigger). Optional: `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`, `initialPrompt`.

Authority lives in frontmatter, not in prose — the fields that carry it:

| Field | Notes |
|---|---|
| `tools` | Allowlist. **Omitting it inherits every tool** — omission is "all tools," not "none." `Agent(worker)` scoping works only for a main-thread agent (`claude --agent`); a subagent silently ignores the type list. `AskUserQuestion`, `EnterPlanMode`, `ExitPlanMode`, `ScheduleWakeup`, `WaitForMcpServers` are never available to a subagent, however listed. |
| `disallowedTools` | Denylist; applied before `tools` resolves. |
| `permissionMode` | `default \| acceptEdits \| auto \| dontAsk \| bypassPermissions \| plan \| manual`. This fleet forbids `bypassPermissions` — it voids the read-only guard. |
| `hooks` | Agent-scoped lifecycle hooks; how `code-reviewer` takes write access back off `Bash`. |
| `skills` | Preloads full skill content at startup — prefer over putting `Skill` in `tools`. |
| `model` | Aliases `haiku \| sonnet \| opus \| fable \| inherit`, or a full ID (`claude-opus-4-8`); defaults to `inherit`. Use an alias — this fleet rejects pins, which rot silently while an alias follows the upgrade. |

Plugin-packaged agents **ignore** `hooks`, `mcpServers`, and `permissionMode`. Spell keys exactly: an unrecognized key isn't guaranteed to fail loudly, so a typo can silently drop what it configured (`validate_fleet.py` rejects unknown keys for this reason).

**Skills** (`.claude/skills/<name>/SKILL.md`):
`name`, `description` (the trigger), `argument-hint`; `disable-model-invocation: true` for side-effect skills (deploy, send, commit — user-only via `/name`); `user-invocable: false` for background-knowledge skills.

Project-level definitions shadow user-level ones of the same name. Keep descriptions lean — they load into context every session.
