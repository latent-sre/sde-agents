---
name: prompt-craft
description: Eval-first method for anything an LLM consumes — prompts, agent definitions, skills, tool descriptions, multi-agent rosters — and for telling a prompt defect from a defect in the harness around it. Use for "write me an agent for X", "my skill never triggers", "my agent won't trigger", "the model keeps ignoring this instruction", "design a multi-agent system", "diagnose a wrapper/harness failure", "my LLM app got worse after I added a memory layer". Not for ordinary software work — use sde-agents:sde-fullstack; not for system architecture with no model in the loop — use sde-agents:principal-engineer.
argument-hint: [what to create or fix]
---

Apply this method inline, for one prompt or a whole roster. Reps that need a clean context are
subagents you spawn yourself (step 4).

## Method

Capturing a live workflow ("turn what we just did into a skill")? Extract the method from the conversation first — tools used, step order, corrections made — and confirm the gaps before drafting.

1. **Success criteria first.** Define what a correct output looks like, measurably, before touching the prompt.
2. **Baseline.** Reproduce the failure with the current prompt. No edit without an observed failure to pin it to.
3. **Minimal change.** Fix the observed failure; don't rewrite everything you'd have phrased differently.
4. **Retest fresh.** Spawn a clean-context subagent with a realistic task; check it triggers and complies. Multiple reps — variance is a metric. **If the repo ships an eval harness, run it instead of eyeballing** — in this fleet that is `scripts/eval_routing.py` for a description change (run the overlapping cluster before *and* after and diff the rates; a near-miss that starts firing is a defect at any rate). Measuring after only tells you the current number; the diff is the finding.

**Hold-out cases.** The second time the same eval set drives an edit, hold one or two of its cases
out of the tuning loop and judge the final version on those — a prompt tuned until its train cases
pass has learned the cases, not the job.

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

## When the problem is the system around the prompt

A miss is not evidence that the prompt text is wrong. Isolate the boundary first, in this order,
and edit prompt text only when the evidence points there:

1. **Routing** — did the component fire at all? Never-fires is rule 1, not a body problem.
2. **Wrapper** — right on a direct call, wrong inside the stack: bisect the prompt-assembly,
   memory, and delivery layers before blaming the model.
3. **Context** — did the instruction reach the model, and was it still in reach when it mattered?
   `references/context.md` has the symptom table.
4. **Transport** — the log shows the right answer and the user sees a wrong one: the defect is
   rendering or delivery, not generation.
5. **Tool** — a required tool the code never gates will be skipped under load; the fix is a gate,
   not a stronger sentence.
6. **Evaluator** — would the assert also pass a plainly wrong output? A pass on a weak assert
   manufactures confidence; fix the assert before the prompt.
7. **Capability** — fails in every configuration: beyond the model, not a prompt problem.

**Tools are authority.** An agent's tool list is its mandate — a reviewer that cannot edit is one
without `Write`, not one told not to. Enforce roles at the tool layer, never in prose
(`references/tools.md` designs the list); runtime constraints hold, instructions bend.

**Three wrapper-stack triggers.** "It got worse after I added a memory layer": the agent's own
assertions were admitted into durable memory, or one fact now arrives by prompt, history, and
memory and reads as three confirmations — user corrections outrank the agent's writes. "It skips
the tool": a prompt-only mandate; gate it in code (item 5). "The answer changed between generation
and delivery": a hidden repair, retry, or summarize pass, or transport corruption (item 4) — make
every second pass an explicit contract or remove it.

More than one agent is an architecture decision with real costs — tokens, latency, information
loss at every handoff — justified only when the work exceeds one context, stages need isolation, or
independent perspectives measurably reduce error. Otherwise ship one agent with good tools; when
you do split, `references/context.md` owns what a worker receives and what it must return.

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
