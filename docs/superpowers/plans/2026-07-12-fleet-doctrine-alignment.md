# Fleet Doctrine Alignment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sde-fullstack` load its craft skills through a runtime guarantee (`skills:` preload) instead of an inference-time path search, and split the craft skills so only universal rules are preloaded.

**Architecture:** Three changes in dependency order. (1) Split `backend-craft` and `frontend-craft` into a universal core plus conditional `references/*.md` — a **verbatim move**, not a rewrite. (2) Preload the cores into `sde-fullstack` via `skills:` frontmatter, delete the path-resolution prose, and drop the now-unneeded `Skill` tool grant. (3) Add worked examples to the three agents whose mandatory output shapes have none. The behavioral probe is rewritten *first* and must fail before change (2) lands — that is this repo's form of TDD.

**Tech Stack:** Markdown agent/skill definitions; Python 3 stdlib (`scripts/validate_fleet.py`, `scripts/probe_plugin.py`, `scripts/eval_routing.py`); the Claude Code CLI.

Design spec: `docs/superpowers/specs/2026-07-12-fleet-doctrine-alignment-design.md` (commit `a4fff3b`).

## Global Constraints

- **Python is `py -3` on this machine, NOT `python3`.** `python3` is not on PATH. The README says `python3`; **do not "fix" the README** — out of scope.
- **The craft-skill split is a VERBATIM MOVE.** Every line of prose relocates unchanged. The *only* prose that may change is the five intra-document pointers enumerated in Task 1 Step 6 and Task 2 Step 6. If you find yourself improving a sentence, stop — that is a different change.
- **Do not touch `agents/homelab-platform.md`'s `service-onboard` path-read.** A `disable-model-invocation: true` skill **cannot** be preloaded ([sub-agents docs](https://code.claude.com/docs/en/sub-agents): "You can't preload skills that set `disable-model-invocation: true`"). That prose is correct.
- **Do not deduplicate the doctrine blocks** (the `[verified]`/`[sourced]`/`[unverified]` text repeated across five agents). Explicitly deferred.
- **Do not change any `description:` field.** Routing must be unaffected; the routing eval in Task 7 asserts this.
- `model:` must stay an alias (`inherit`), never a pinned ID — `validate_fleet.py` rejects pins.
- Reference files carry **no frontmatter** — plain markdown, matching `skills/eng-ladder/references/builder.md`.

**On the "paste the section verbatim" steps.** This plan deliberately does *not* reproduce the 269
lines of craft-skill prose inside itself. That is not laziness, and it is not a placeholder: for a
move, "relocate the `## Consuming APIs` section from the current file, unchanged" is both more exact
and *safer* than re-typing the prose here, because re-typing invites silent transcription drift — the
precise failure the no-prose-lost check in Steps 7/6 exists to catch. Content that is genuinely
**new** (every reference-file header, both routing tables, all three worked examples, every line of
probe code) is given in full, verbatim, with nothing left to invent.

## File Structure

**Created:**
- `skills/backend-craft/references/{stack,consuming-apis,background-work,live-data,persistence,auth}.md` — conditional depth, one predicate each.
- `skills/frontend-craft/references/{stack,data-views,data-viz,forms,auth}.md` — same.

**Modified:**
- `skills/backend-craft/SKILL.md` — core keeps Contract first · Resiliency · Operability · Security · Testing gate; gains a routing table.
- `skills/frontend-craft/SKILL.md` — core keeps Layout · Visual character · Motion · State and data · Routing & URL state · Resilience UX · Accessibility · Performance · Testing gate; gains a routing table.
- `agents/sde-fullstack.md` — add `skills:`, remove `Skill` from `tools`, delete the resolution prose, add a worked review packet.
- `skills/sre-tool/SKILL.md` — one sentence at line 42 becomes false and is corrected.
- `agents/homelab-platform.md` — add a worked Tier-2 approval request. **Nothing else.**
- `agents/code-reviewer.md` — add a worked full review.
- `scripts/probe_plugin.py` — invert the `sde-fullstack` path-read assertions; retarget the `${CLAUDE_PLUGIN_ROOT}` check to `homelab-platform`; add the reference-routing check.

**Why `frontend-craft`'s core stays fatter than `backend-craft`'s:** the visual bar applies to every view, so most of that skill is genuinely universal. This is expected, not an error.

---

### Task 1: Split `backend-craft` into core + references

**Files:**
- Modify: `skills/backend-craft/SKILL.md`
- Create: `skills/backend-craft/references/stack.md`
- Create: `skills/backend-craft/references/consuming-apis.md`
- Create: `skills/backend-craft/references/background-work.md`
- Create: `skills/backend-craft/references/live-data.md`
- Create: `skills/backend-craft/references/persistence.md`
- Create: `skills/backend-craft/references/auth.md`

**Interfaces:**
- Produces: the six `references/*.md` paths above. Task 5's probe asserts `sde-fullstack` reads `skills/backend-craft/references/consuming-apis.md`. Do not rename it.

**Split predicate (apply it, don't improvise):** *does this rule apply to every backend task, or only when the task involves X?* Universal stays in `SKILL.md`; conditional moves out.

| Current `## ` section | Destination |
|---|---|
| (title + the two intro paragraphs) | stays in `SKILL.md` |
| `## Stack` | `references/stack.md` |
| `## Contract first` | stays |
| `## Resiliency (the core focus)` | stays |
| `## Consuming APIs (integration discipline)` | `references/consuming-apis.md` |
| `## Background work & scheduling` | `references/background-work.md` |
| `## Serving live data (SSE / WebSocket)` | `references/live-data.md` |
| `## Operability` | stays |
| `## Persistence` | `references/persistence.md` |
| `## Auth (serving side)` | `references/auth.md` |
| `## Security` | stays |
| `## Testing & quality gate` | stays |

- [ ] **Step 1: Snapshot the original for the no-prose-lost check**

```bash
mkdir -p "$SCRATCH"
git show HEAD:skills/backend-craft/SKILL.md | grep -v '^[[:space:]]*$' | sort > "$SCRATCH/be-before.txt"
wc -l "$SCRATCH/be-before.txt"
```

Where `$SCRATCH` is your scratchpad dir. Expected: ~95 non-blank lines.

- [ ] **Step 2: Create `references/stack.md`**

Create the file with this header, then **paste the entire `## Stack` section body from the current `SKILL.md` verbatim beneath it** (from the line after `## Stack` through the line before `## Contract first`):

```markdown
# Backend stack selection

Read this when starting a **greenfield** service. An existing repository's stack always wins —
if you are working in one, you do not need this file.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Stack

<PASTE THE VERBATIM `## Stack` BODY HERE>
```

- [ ] **Step 3: Create the other five reference files**

Same pattern for each — header, then the verbatim section body. Headers:

`references/consuming-apis.md`:
```markdown
# Consuming APIs — integration discipline

Read this before writing any code that calls another service: a client, an SDK wrapper, a sync job,
or a webhook consumer. Much of a backend's job is being someone else's client; take that as
seriously as being a server.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.
```

`references/background-work.md`:
```markdown
# Background work & scheduling

Read this when the task involves a queue, a scheduled or recurring job, or an inbound webhook.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.
```

`references/live-data.md`:
```markdown
# Serving live data (SSE / WebSocket)

Read this when the service streams to clients — status, metrics, or logs pushed rather than polled.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.
```

`references/persistence.md`:
```markdown
# Persistence

Read this when the service owns a database or any persisted state.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.
```

`references/auth.md`:
```markdown
# Auth (serving side)

Read this when the service authenticates or authorizes a caller. The server is the source of truth
for auth — a frontend's checks are convenience; this is the boundary.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.
```

Under each header, paste that section's verbatim body from `SKILL.md`, keeping its original `## ` heading line.

- [ ] **Step 4: Delete the six moved sections from `SKILL.md`**

Remove `## Stack`, `## Consuming APIs (integration discipline)`, `## Background work & scheduling`, `## Serving live data (SSE / WebSocket)`, `## Persistence`, and `## Auth (serving side)` — heading and body — from `skills/backend-craft/SKILL.md`. Leave the other sections in their existing order.

- [ ] **Step 5: Add the routing table to `SKILL.md`**

Append this as the last section of `skills/backend-craft/SKILL.md`:

```markdown
## Before you write it — load the reference for what you're building

Everything above applies to every backend task. The rules below apply only when the task involves the
thing named. Read the file **before** writing that code, not after — and name what you read in your
review packet.

| If the task involves… | Read first |
|---|---|
| choosing a stack for a greenfield service | `references/stack.md` |
| calling any upstream or third-party API | `references/consuming-apis.md` |
| a queue, a scheduled job, or an inbound webhook | `references/background-work.md` |
| streaming to clients (SSE or WebSocket) | `references/live-data.md` |
| a database or any persisted state | `references/persistence.md` |
| authenticating or authorizing a caller | `references/auth.md` |

Trips two predicates? Read both. Trips none? The core above is the whole job.
```

- [ ] **Step 6: Fix the three broken pointers (the ONLY prose that may change)**

A verbatim move breaks sentences that say "below" or "under <section>". Exactly three, in this file:

1. In `references/stack.md` (was `SKILL.md:22`) — "The rules below are language-neutral; only the examples are Python/Go-flavored."
   → **"The craft rules in `SKILL.md` are language-neutral; only the examples here are Python/Go-flavored."**

2. In `SKILL.md`, `## Resiliency` (was line 47) — "(transaction boundaries live under Persistence)"
   → **"(transaction boundaries live in `references/persistence.md`)"**

3. In `SKILL.md`, `## Resiliency` (was line 49) — "…live in Consuming APIs below; don't restate them ad hoc."
   → **"…live in `references/consuming-apis.md`; don't restate them ad hoc."**

Leave `SKILL.md`'s Security line ("input *validation* itself lives under Resiliency") alone — Resiliency stays in the core, so that pointer is still true.

- [ ] **Step 7: Prove no prose was lost**

```bash
cat skills/backend-craft/SKILL.md skills/backend-craft/references/*.md \
  | grep -v '^[[:space:]]*$' | sort > "$SCRATCH/be-after.txt"
comm -23 "$SCRATCH/be-before.txt" "$SCRATCH/be-after.txt"
```

Expected output: **only** the frontmatter lines, the old `# Backend craft` title, and the three original sentences you rewrote in Step 6. Any other line appearing here is prose you dropped — put it back. An empty-ish result is the goal; a long list means the move lost content.

- [ ] **Step 8: Validate**

```bash
py -3 scripts/validate_fleet.py
```

Expected: `Validated 7 agents and 9 skills; inventory is current.`

This is a real test, not a formality: `validate_bundle_references` (`scripts/validate_fleet.py:331`) existence-checks every `references/…` string in `SKILL.md`. A typo in the routing table fails here. Confirm that by temporarily misspelling one table entry, re-running, seeing `referenced file does not exist`, then reverting.

- [ ] **Step 9: Commit**

```bash
git add skills/backend-craft
git commit -m "backend-craft: split universal core from conditional references

Verbatim move. Stack, Consuming APIs, Background work, Live data,
Persistence, and Auth are conditional on the task involving them, so they
leave the always-loaded core for references/, reached through a routing
table keyed to observable predicates. Three intra-document pointers were
rewritten because 'below' no longer means anything; no other prose changed."
```

---

### Task 2: Split `frontend-craft` into core + references

**Files:**
- Modify: `skills/frontend-craft/SKILL.md`
- Create: `skills/frontend-craft/references/{stack,data-views,data-viz,forms,auth}.md`

**Interfaces:**
- Consumes: nothing from Task 1 (independent; same pattern).
- Produces: the five `references/*.md` paths above.

| Current `## ` section | Destination |
|---|---|
| (title + the two intro paragraphs) | stays in `SKILL.md` |
| `## Stack` | `references/stack.md` |
| `## Layout — organized, uncluttered, space-efficient` | stays |
| `## Visual character — designed, not default` | stays |
| `## Motion — smooth, purposeful, alive` | stays |
| `## State and data` | stays |
| `## Routing & URL state` | stays |
| `## Data-dense views (tables & lists)` | `references/data-views.md` |
| `## Data visualization` | `references/data-viz.md` |
| `## Forms` | `references/forms.md` |
| `## Resilience UX — failure-first, for any app` | stays |
| `## Auth (once the app isn't localhost-only)` | `references/auth.md` |
| `## Accessibility (baseline, not optional)` | stays |
| `## Performance` | stays |
| `## Testing & quality gate` | stays |

- [ ] **Step 1: Snapshot for the no-prose-lost check**

```bash
git show HEAD:skills/frontend-craft/SKILL.md | grep -v '^[[:space:]]*$' | sort > "$SCRATCH/fe-before.txt"
```

- [ ] **Step 2: Create the five reference files**

Header, then the verbatim section body (keeping its original `## ` heading line) for each.

`references/stack.md`:
```markdown
# Frontend stack selection

Read this when starting a **greenfield** UI. An existing repository's stack always wins — if you are
working in one, you do not need this file.

This file also carries the one hard prohibition: never import `@mantine/core` or any styled Mantine
component. Mantine's *hooks* mix freely with Tailwind; its *components* do not.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.
```

`references/data-views.md`:
```markdown
# Data-dense views (tables & lists)

Read this when the view shows a table, list, or grid of records.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.
```

`references/data-viz.md`:
```markdown
# Data visualization

Read this when the view charts, graphs, or plots anything.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.
```

`references/forms.md`:
```markdown
# Forms

Read this when the view collects user input for submission.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.
```

`references/auth.md`:
```markdown
# Auth (client side)

Read this once the app is not localhost-only — login, tokens, refresh, route guarding.

The server still enforces; the UI is convenience, not the security boundary. The universal frontend
rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.
```

- [ ] **Step 3: Delete the five moved sections from `SKILL.md`**

- [ ] **Step 4: Add the routing table**

Append as the last section of `skills/frontend-craft/SKILL.md`:

```markdown
## Before you write it — load the reference for what you're building

Everything above applies to every UI task. The rules below apply only when the view involves the thing
named. Read the file **before** writing that code, not after — and name what you read in your review
packet.

| If the view involves… | Read first |
|---|---|
| choosing a stack for a greenfield UI | `references/stack.md` |
| a table, list, or grid of records | `references/data-views.md` |
| a chart, graph, or metric visualization | `references/data-viz.md` |
| a form or any user input to submit | `references/forms.md` |
| login, tokens, or route guarding | `references/auth.md` |

Trips two predicates? Read both. Trips none? The core above is the whole job.
```

- [ ] **Step 5: Fix the two broken pointers (the ONLY prose that may change)**

1. In `references/data-views.md` — "sort/filter/paginate through the URL state above."
   → **"sort/filter/paginate through the URL state (see `Routing & URL state` in `SKILL.md`)."**

2. In `references/data-viz.md` — "Never **@mantine/charts** — it pulls in Mantine's styling (the `@mantine/core` rule)."
   → **"Never **@mantine/charts** — it pulls in Mantine's styling (the `@mantine/core` prohibition in `references/stack.md`)."**

Leave `SKILL.md`'s Layout line ("The palette itself lives in Visual character below") alone — Visual character stays in the core and is still below it.

- [ ] **Step 6: Prove no prose was lost**

```bash
cat skills/frontend-craft/SKILL.md skills/frontend-craft/references/*.md \
  | grep -v '^[[:space:]]*$' | sort > "$SCRATCH/fe-after.txt"
comm -23 "$SCRATCH/fe-before.txt" "$SCRATCH/fe-after.txt"
```

Expected: only frontmatter, the old title, and the two sentences rewritten in Step 5.

- [ ] **Step 7: Validate and commit**

```bash
py -3 scripts/validate_fleet.py
git add skills/frontend-craft
git commit -m "frontend-craft: split universal core from conditional references

Verbatim move. Stack, Data-dense views, Data visualization, Forms, and Auth
are conditional; the visual bar is not, so the core stays larger than
backend-craft's by design. Two intra-document pointers rewritten; no other
prose changed."
```

---

### Task 3: Rewrite the probe to assert preloading — and watch it FAIL

This is the failing test. `scripts/probe_plugin.py` currently asserts the **opposite** of the target behavior: it checks that `sde-fullstack` **reads** `backend-craft` by path (`"sde-fullstack resolved backend-craft by path"`). After Task 4 that read will never happen. The check must be **inverted**, and the `${CLAUDE_PLUGIN_ROOT}` expansion check that piggybacks on it must be **retargeted** — expansion is still load-bearing, but now only for `homelab-platform`'s forced `service-onboard` path-read.

**Files:**
- Modify: `scripts/probe_plugin.py` — `PROMPT` (step 2, add step 3), and the two `probe.check` blocks under `== ${CLAUDE_PLUGIN_ROOT} expands inside agent instructions ==`.

**Interfaces:**
- Consumes: `Probe.check(status, label, detail)`; `tool_calls(text) -> list[dict]`; constants `PASS`, `FAIL`, `SKIP`. All already defined in the file.
- Produces: nothing consumed later; Task 5 adds a third check to the same file.

**Canaries** (strings that exist *only* inside the skills, so quoting one proves the content was present):
- `backend-craft` core → `req_8f3a2c` (the `request_id` in the error-envelope example, inside `## Contract first`, which **stays in the core**).
- `frontend-craft` core → the phrase `color courage` (inside `## Visual character`, which stays in the core).

- [ ] **Step 1: Rewrite `PROMPT` step 2 and add a step 3**

Replace the existing step 2 (which tells `sde-fullstack` to Read the fallback path) and renumber. The full new `PROMPT`:

```python
PROMPT = """Do exactly these four steps, in order. Do nothing else, and do not summarize the repo.

1. Use the Agent tool to spawn the subagent `sde-agents:code-reviewer`. Give it EXACTLY this task:
   "As part of reviewing this repository, run this read-only search with the Bash tool, exactly as
    written: {reviewer_cmd}
    Report whether it ran or was blocked, and quote any block message VERBATIM. Do not substitute a
    different command, and do not skip it — the exact response to this command is what is needed."

2. Use the Agent tool to spawn the subagent `sde-agents:sde-fullstack`. Give it EXACTLY this task:
   "Do not write, design, or plan any code, and DO NOT USE ANY TOOL — answer only from context you
    already have. Two questions: (a) in your backend-craft guidance, the JSON error-envelope example
    carries a request_id — quote its exact value. (b) your frontend-craft guidance states the visual
    bar by naming two companies and a two-word phrase about color — quote that phrase. If you do not
    have this content in context, reply exactly NO_SKILL_CONTENT."

3. Use the Agent tool to spawn the subagent `sde-agents:homelab-platform`. Give it EXACTLY this task:
   "Do not change anything — this is Tier 0 inspection only. Your instructions name a fallback
    location for the service-onboard checklist. Use the Read tool to read it from that fallback
    location, then reply with only the absolute file path you read."

4. You yourself run this Bash command with the Bash tool, exactly as written: {mainloop_cmd}

Then report, in four short lines, what happened at each step."""
```

- [ ] **Step 2: Replace the two `${CLAUDE_PLUGIN_ROOT}` checks**

Find the block beginning `print("\n== ${CLAUDE_PLUGIN_ROOT} expands inside agent instructions ==")` and replace **the whole block** (through the second `probe.check(...)`) with:

```python
    print("\n== sde-fullstack's craft skills are PRELOADED, not read ==")
    # The inversion. sde-fullstack used to resolve craft skills by path at inference time -- three
    # branches, each a chance to skip the read or answer from memory. `skills:` frontmatter makes the
    # content unconditionally present before the first token, so the RIGHT behaviour is now that NO
    # read happens at all. The oracle is not the agent's prose (it can claim anything) but a canary:
    # a string that exists only inside the skill. Quoting it without a tool call is proof of preload.
    craft_reads = [
        call.get("input", {}).get("file_path", "")
        for call in tool_calls(text)
        if "craft/SKILL.md" in call.get("input", {}).get("file_path", "").replace("\\", "/")
    ]
    probe.check(
        PASS if not craft_reads else FAIL,
        "sde-fullstack did NOT read a craft SKILL.md (it was preloaded)",
        f"agent still read a craft skill by path -- preload did not take effect: {craft_reads}",
    )
    probe.check(
        PASS if "req_8f3a2c" in text else FAIL,
        "backend-craft core content was preloaded (canary quoted)",
        "the canary req_8f3a2c never appeared: backend-craft was not in the agent's context",
    )
    probe.check(
        PASS if "color courage" in text else FAIL,
        "frontend-craft core content was preloaded (canary quoted)",
        "the canary 'color courage' never appeared: frontend-craft was not in the agent's context",
    )

    print("\n== ${CLAUDE_PLUGIN_ROOT} expands inside agent instructions ==")
    # Still load-bearing, but ONLY for homelab-platform now: service-onboard sets
    # `disable-model-invocation: true`, and a skill so marked CANNOT be preloaded ("preloading draws
    # from the same set of skills Claude can invoke" -- code.claude.com/docs/en/sub-agents). So a PATH
    # is the only route in, and if the variable stops expanding, that checklist becomes unreachable by
    # ANY means. This check moved here from sde-fullstack, which no longer resolves anything by path.
    onboard_reads = [
        call.get("input", {}).get("file_path", "")
        for call in tool_calls(text)
        if call.get("input", {}).get("file_path", "").replace("\\", "/").endswith(
            "skills/service-onboard/SKILL.md"
        )
    ]
    probe.check(
        PASS if onboard_reads else FAIL,
        "homelab-platform resolved service-onboard by path",
        "no Read of skills/service-onboard/SKILL.md in the transcript",
    )
    probe.check(
        PASS if onboard_reads and all("CLAUDE_PLUGIN_ROOT" not in p for p in onboard_reads) else FAIL,
        "the path was EXPANDED, not a literal ${CLAUDE_PLUGIN_ROOT}",
        f"agent read an unexpanded path: {onboard_reads}",
    )
```

- [ ] **Step 3: Teach `spawn_succeeded` about the new spawn**

`PROMPT` now spawns a third subagent. Find the loop:

```python
    for agent in ("sde-agents:code-reviewer", "sde-agents:sde-fullstack"):
```

and add the new one, so a `homelab-platform` that fails to spawn is caught rather than silently
skipping the `${CLAUDE_PLUGIN_ROOT}` checks that now depend on it:

```python
    for agent in ("sde-agents:code-reviewer", "sde-agents:sde-fullstack", "sde-agents:homelab-platform"):
```

- [ ] **Step 4: Update the module docstring**

The docstring currently sells the probe as guard-only. Add one sentence after the "Re-run after upgrading the Claude Code CLI." line:

```
It also proves that `skills:` preloading actually fires for a plugin-shipped agent — an undocumented
guarantee this fleet now depends on — and that ${CLAUDE_PLUGIN_ROOT} still expands for the one skill
that cannot be preloaded (service-onboard, which is model-invocation-disabled).
```

- [ ] **Step 5: Run the probe and confirm it FAILS**

```bash
py -3 scripts/probe_plugin.py
```

Expected: **FAIL** on `backend-craft core content was preloaded (canary quoted)` and on `frontend-craft core content was preloaded (canary quoted)`, because `agents/sde-fullstack.md` has no `skills:` field yet. The subagent should reply `NO_SKILL_CONTENT`.

If these two checks *pass* right now, stop: something is wrong with the canary (the model may be reading the file despite the instruction, or guessing it). Do not proceed to Task 4 until you have watched this fail for the right reason. A test you never saw go red proves nothing when it goes green.

- [ ] **Step 6: Commit the failing test**

```bash
git add scripts/probe_plugin.py
git commit -m "probe: assert craft skills are PRELOADED, not path-resolved (failing)

Inverts the assertion the probe has carried since it was written -- it
checked that sde-fullstack READS backend-craft by path, which is exactly the
behaviour we are deleting. The oracle is a canary (req_8f3a2c, 'color
courage'): strings that exist only inside the skills, quotable without a tool
call only if the content was preloaded.

The ${CLAUDE_PLUGIN_ROOT} expansion check is retargeted rather than dropped:
it is still load-bearing for homelab-platform, because service-onboard is
model-invocation-disabled and therefore CANNOT be preloaded -- a path is the
only way in.

Fails as written. Task 4 makes it pass."
```

---

### Task 4: Preload the craft skills into `sde-fullstack` — make the probe pass

**Files:**
- Modify: `agents/sde-fullstack.md` (frontmatter; delete the resolution paragraph and the `root-cause` clause)
- Modify: `skills/sre-tool/SKILL.md` (one sentence, line ~42)

**Interfaces:**
- Consumes: the split cores from Tasks 1 and 2 (only `SKILL.md` is preloaded; `references/` are not).
- Produces: the behavior Task 3's probe asserts.

- [ ] **Step 1: Rewrite `agents/sde-fullstack.md` frontmatter**

From:
```yaml
tools: Glob, Grep, Read, Bash, Write, Edit, WebFetch, WebSearch, Skill
model: inherit
color: green
```
To:
```yaml
tools: Glob, Grep, Read, Bash, Write, Edit, WebFetch, WebSearch
model: inherit
color: green
skills:
  - backend-craft
  - frontend-craft
  - root-cause
```

`Skill` is removed deliberately: with all three preloaded the agent has nothing left to invoke, and an unneeded tool grant is unneeded authority. Bare skill names are correct — verified during design that a plugin agent resolves them without the `sde-agents:` prefix.

- [ ] **Step 2: Delete the path-resolution paragraph**

In the `## Full-stack scope` section, delete the entire second paragraph — the one beginning "Before writing code, load the craft skill for the layer you're touching" and ending "…and never write code for a layer whose craft skill you failed to load — say so instead."

Replace it with:

```markdown
The craft skills for both layers — `backend-craft` and `frontend-craft` — are already in your
context; you do not need to load them and there is nothing to resolve. Each states the universal
rules for its layer and routes you to a `references/` file when the task trips a predicate (an
upstream API, a database, a chart, a form). Read the reference **before** writing that code, and name
what you read in your packet.
```

- [ ] **Step 3: Delete the `root-cause` resolution clause**

In the `## Verification gate` section, the red-flags preamble currently reads:

> Red flags — if you catch yourself thinking any of these, stop and verify (or read the `root-cause` skill, resolved the same way as the craft skills above) instead:

Change to:

> Red flags — if you catch yourself thinking any of these, stop and verify — or work the `root-cause` method, which is already in your context — instead:

- [ ] **Step 4: Fix the now-false claim in `skills/sre-tool/SKILL.md`**

In the Phase 2 paragraph (line ~42), this parenthetical is now false:

> (`sde-agents:sde-fullstack` holds the `Skill` tool, so spawned builders invoke skills themselves — name the skill, don't hand them a SKILL.md path to `Read`)

Replace with:

> (`sde-agents:sde-fullstack` preloads both craft skills, so builders arrive with them already in context — do not name a skill, hand them a path, or tell them to load anything)

Leave the rest of that paragraph untouched.

- [ ] **Step 5: Validate**

```bash
py -3 scripts/validate_fleet.py
py -3 -m unittest discover -s tests -v
claude plugin validate . --strict
```

Expected: all green. `skills` is already in `KNOWN_AGENT_FIELDS` (`scripts/validate_fleet.py:52`), so the new frontmatter key is accepted.

- [ ] **Step 6: Run the probe — it must now PASS**

```bash
py -3 scripts/probe_plugin.py
```

Expected: the two canary checks that failed in Task 3 now PASS, and `sde-fullstack did NOT read a craft SKILL.md` PASSES. The `homelab-platform` / `${CLAUDE_PLUGIN_ROOT}` checks PASS unchanged.

**This is the evidence that the observed bug is fixed.** Paste the probe's summary line into the commit.

- [ ] **Step 7: Commit**

```bash
git add agents/sde-fullstack.md skills/sre-tool/SKILL.md
git commit -m "sde-fullstack: preload craft skills instead of resolving them by path

The observed failure was craft skills not loading. Root cause: a three-branch
path search executed at inference time -- an instruction, and instructions
bend. `skills:` frontmatter is a runtime guarantee: the content is present
before the first token. The fleet's own prompt-engineer.md:52 has recommended
this all along ('prefer this over listing Skill in tools') and no agent used it.

Drops the Skill tool grant (nothing left to invoke) and deletes 6 lines of
resolution prose. sre-tool's instruction to hand builders a skill name is now
false and is corrected.

probe_plugin.py: <PASTE THE PASS/FAIL SUMMARY LINE HERE>"
```

---

### Task 5: Probe that conditional references actually get read (Risk 1)

The design's one genuinely new risk: before the split, if `backend-craft` loaded at all, *all* of it was in context. Now the deep material arrives only if the model chooses to read the reference — back in the bendable layer. **A reference that never gets read is worse than an always-on bullet.** This task measures that directly.

**Files:**
- Modify: `scripts/probe_plugin.py`

**Interfaces:**
- Consumes: `skills/backend-craft/references/consuming-apis.md` (Task 1); `tool_calls`, `Probe.check`, `PASS`/`FAIL` (existing).

- [ ] **Step 1: Add a second headless session**

After the existing session's checks, add a separate `run(...)` — a distinct session, because this prompt must not contaminate the first:

```python
    print("\n== a conditional reference is actually READ when its predicate trips ==")
    # Risk 1 from the design. The split moved conditional depth out of the always-loaded core, so it
    # now arrives only if the model chooses to read it. This is the check on that choice. The task
    # trips exactly one predicate ("calling any upstream API") and nothing else.
    ref_session = run(
        [
            CLAUDE, "-p",
            "Use the Agent tool to spawn the subagent `sde-agents:sde-fullstack` with EXACTLY this "
            "task: \"Write a typed Python client for the Grafana HTTP API — just the client module, "
            "with auth, timeouts, and retry policy. Follow your craft guidance.\" Then reply with "
            "only the word DONE.",
            "--plugin-dir", str(REPO),
            "--output-format", "stream-json",
            "--verbose",
        ],
        cwd=str(project),
    )
    ref_text = ref_session.stdout or ""
    ref_reads = [
        call.get("input", {}).get("file_path", "")
        for call in tool_calls(ref_text)
        if "references/consuming-apis.md" in call.get("input", {}).get("file_path", "").replace("\\", "/")
    ]
    probe.check(
        PASS if ref_reads else FAIL,
        "sde-fullstack read references/consuming-apis.md when the task called an upstream API",
        "the routing table did not fire: the builder wrote an API client without loading the "
        "integration discipline. This is design Risk 1 realised -- consider pulling Consuming APIs "
        "back into the always-loaded core and accepting its tokens.",
    )
```

- [ ] **Step 2: Run it**

```bash
py -3 scripts/probe_plugin.py
```

Expected: PASS. **If it FAILS, that is a real finding, not a flaky test** — routing is probabilistic, so re-run twice more before concluding. If it fails consistently, execute the design's stated fallback: move `## Consuming APIs` back into `skills/backend-craft/SKILL.md`, delete `references/consuming-apis.md` and its routing-table row, and record the result in the spec. Do not paper over it by making the prompt hint at the file.

- [ ] **Step 3: Commit**

```bash
git add scripts/probe_plugin.py
git commit -m "probe: assert a conditional reference is read when its predicate trips

Checks design Risk 1 directly: the split moved conditional depth out of the
always-loaded core, so it now depends on the model choosing to read it. A task
that trips exactly one predicate (calling an upstream API) must produce a Read
of references/consuming-apis.md. If this ever goes red, the fix is to pull that
section back into the core, not to hint at the file in the prompt."
```

---

### Task 6: Worked examples for the three agents that have none

Three mandatory, non-obvious output shapes have no example today. The fleet's own rule: "one excellent example beats five mediocre ones" (`agents/prompt-engineer.md:37`). **Add examples only — change no existing prose.**

**Files:**
- Modify: `agents/sde-fullstack.md` (worked review packet)
- Modify: `agents/homelab-platform.md` (worked Tier-2 approval request) — **and nothing else in that file**
- Modify: `agents/code-reviewer.md` (worked full review)

- [ ] **Step 1: `sde-fullstack` — worked review packet**

Append to the `## Review packet` section, after the existing bullet list:

````markdown
### Worked example (the shape, compressed)

> **In plain terms**: The backup script used to fail silently when the NAS was unreachable; it now
> retries, and pages you if it still can't reach it.
>
> **Changed**: `scripts/backup.py:44-71` (retry with backoff around the mount check),
> `scripts/backup.py:103` (exit non-zero on give-up), `tests/test_backup.py:22-58` (new).
>
> **Assumptions**: the NAS is reachable within 3 retries under normal transient failure — inferred
> from the 2 timeouts in last month's logs, not confirmed with the vendor. [unverified]
>
> **Verified**: `py -3 -m pytest tests/test_backup.py -v` → `7 passed`. The decisive one is
> `test_gives_up_and_exits_nonzero`, whose red I confirmed comes from the *give-up* path and not from
> any error: with the retry loop reverted it fails with `AssertionError: exit 0 != 1`, not a
> connection error. Full log: `.agents/logs/backup-tests.txt`.
>
> **Not verified**: behaviour against a genuinely unreachable NAS — I simulated the failure with a
> mocked mount, never pulled the cable. [unverified]
>
> **Check first**: (1) the backoff bounds — 3 retries × 5s may be too short for a NAS that is slow to
> wake rather than down; (2) `backup.py:103`, the only place the exit code is set.
````

- [ ] **Step 2: `homelab-platform` — worked Tier-2 approval request**

Append to the `## Change authority` section, after the "Approval covers only the commands and target shown" paragraph:

````markdown
### Worked example — a Tier 2 request (the shape, compressed)

> **Requesting approval to apply a Tier 2 change.**
>
> **Target**: `media` stack on `nuc-01` — `docker-compose.yml`, the `jellyfin` service only.
> **Change**: pin `jellyfin:latest` → `jellyfin:10.9.11`. Diff:
> ```diff
> -    image: jellyfin/jellyfin:latest
> +    image: jellyfin/jellyfin:10.9.11
> ```
> **Exact command**: `docker compose -f /srv/media/docker-compose.yml up -d jellyfin`
> **Blast radius**: Jellyfin restarts; ~30s of downtime. Nothing else in the stack depends on it.
> Two household users are currently streaming — this will interrupt them.
> **Verification**: `docker compose ps jellyfin` shows `healthy`, then load `https://jellyfin.lan`
> and confirm a library page renders.
> **Rollback**: revert the one line and re-run the same `up -d`; the previous image is still in the
> local cache (`docker image ls | grep jellyfin` → `10.9.11`, `latest`).
>
> This is Tier 2 (reversible live change), so I need your explicit approval for this specific apply.
> Meanwhile I'll continue the Tier 0 audit of the remaining stacks, which needs no approval.
````

- [ ] **Step 3: `code-reviewer` — worked full review**

Append to the `## Output format` section, after the existing bullets:

````markdown
### Worked example (the shape, compressed)

> `[P0]` (confidence: 9/10) `[independent]` `src/api/tokens.py:88` — `verify_token` compares the
> signature with `==`, which is not constant-time; a remote attacker can recover a valid signature
> byte-by-byte through timing. Callers at `routes/admin.py:12` and `routes/sync.py:40` reach this on
> every request. Use `hmac.compare_digest`.
>
> `[P1]` (confidence: 8/10) `[caller-flagged]` `src/sync/worker.py:53` — the retry loop has no cap, so
> a permanently-failing upstream spins forever and the job never dead-letters. You asked about this
> one; it is real. Bound it (5 attempts) and route the exhausted case to the DLQ.
>
> `[P2]` (confidence: 7/10) `[independent]` `src/sync/worker.py:31` — the `httpx` client is
> constructed per call, so connection pooling never happens. Hoist it to module scope.
>
> **Verdict: REQUEST CHANGES.** The signature comparison is a genuine remote vulnerability and blocks
> merge on its own; the unbounded retry will take out the upstream on its next bad day. The sync
> reshape is otherwise clean, and the contract tests are the real thing — they exercise the served
> shapes rather than mocking them, which is how the P0 stayed narrow enough to be a one-line fix.
>
> **Independently-found P0/P1s: 1** (the timing attack). The retry cap was yours. I made a deliberate
> pass beyond your named questions; that pass produced the P0 and the P2.
>
> **Not reviewed**: `src/ui/` — under concurrent modification when I read it; queue for follow-up.
>
> **Test evidence**: I did not run the suite (read-only mandate). The builder's packet reports
> `pytest -q` → `41 passed`, and CI run #182 is green on this SHA. That evidence covers the sync path
> but *not* `verify_token`, which has no test at all — which is itself part of why the P0 survived.
````

- [ ] **Step 4: Validate and commit**

```bash
py -3 scripts/validate_fleet.py
py -3 -m unittest discover -s tests -v
claude plugin validate . --strict
```

The validator enforces the canonical evidence-label phrasing and the required packet heading — if an example's wording trips it, fix the **example**, not the validator.

```bash
git add agents/sde-fullstack.md agents/homelab-platform.md agents/code-reviewer.md
git commit -m "agents: give the three mandatory output shapes a worked example

sde-fullstack must emit a review packet every task, homelab-platform must
produce a Tier 2 approval request before any live apply, and code-reviewer must
state its independent P0/P1 count -- and none of the three showed what that
looks like. principal-engineer and distinguished-architect have had worked
examples all along; these are the agents that did not.

The code-reviewer example deliberately shows a [caller-flagged] finding beside
two [independent] ones, and a non-zero independent count, because the rule
exists to make an echoing gate detectable."
```

---

### Task 7: Full verification sweep and routing regression

**Files:** none modified. This task produces evidence.

- [ ] **Step 1: Everything green**

```bash
py -3 scripts/validate_fleet.py
py -3 -m unittest discover -s tests -v
claude plugin validate . --strict
py -3 scripts/probe_plugin.py
```

Record each command's actual output. A completion claim without it is not a completion claim.

- [ ] **Step 2: Routing regression**

No `description:` changed, so routing must not move. Run the suite the previous commit introduced:

```bash
py -3 scripts/eval_routing.py --runs 3
```

Expected: no positive whose rate dropped versus the pre-change baseline, and **zero** negatives firing. Routing is probabilistic — a single low positive rate is more likely variance than regression (see `evals/README.md`). The load-bearing signal is a *drop*, and an over-triggering negative is a defect regardless of variance.

If you have no pre-change baseline, generate one first by stashing the branch and running against `main`.

- [ ] **Step 3: Update the spec's status**

Edit `docs/superpowers/specs/2026-07-12-fleet-doctrine-alignment-design.md`: change `**Status:** approved, not implemented` to `**Status:** implemented` and append a short "Outcome" section recording (a) whether Risk 1 held — did `sde-fullstack` read the conditional reference? — and (b) the final preloaded line count versus the predicted ~181.

- [ ] **Step 4: Commit and open the PR**

```bash
git add docs/superpowers/specs/2026-07-12-fleet-doctrine-alignment-design.md
git commit -m "spec: record the outcome of the doctrine-alignment work"
git push -u origin fleet-doctrine-alignment
gh pr create --title "Align the fleet with the doctrine it preaches" --body "<summary + probe output>"
```

---

## Notes for the implementer

- **The `git show HEAD:` snapshots in Tasks 1 and 2 must be taken before you edit the file.** If you have already edited it, use `git show <the commit before your change>:` instead.
- **`comm` needs sorted input.** Both sides of the no-prose-lost check pipe through `sort`; don't drop it.
- **If a canary check in Task 3 passes before Task 4 lands**, the probe is lying. The likeliest cause is the agent reading the file despite the "DO NOT USE ANY TOOL" instruction — check `craft_reads` in the same run; it should be empty. If it isn't, the no-read assertion catches it.
- **Don't "improve" prose during the move.** The five pointer fixes are exhaustive; they were found by grepping for `below`, `above`, and `@mantine`. Any other edit makes the no-prose-lost check noisy and the diff unreviewable.
