# Fleet doctrine alignment

**Date:** 2026-07-12
**Status:** approved, not implemented

## Problem

`sde-fullstack`'s craft skills do not reliably load. That is an observed failure, not a
hypothesis.

The root cause is at `agents/sde-fullstack.md:42`, which asks the model to run a three-branch
fallback search *at inference time*: the caller's path, else the target repo's skills directory,
else `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`. Line 70 repeats the pattern for `root-cause`.
Every branch is a chance to skip the read, hallucinate it, or answer from memory of what
`backend-craft` probably says.

The platform already offers a runtime guarantee that makes the search unnecessary: the `skills:`
frontmatter field preloads full skill content before the first token. The fleet documents this
itself — "`skills` — preloads full skill content at startup. Prefer this over listing `Skill` in
`tools`" (`agents/prompt-engineer.md:52`, `skills/prompt-craft/SKILL.md:44`) — and no agent uses it.

That is one instance of a broader pattern. The fleet preaches four practices it does not follow:

| Rule the fleet states | Where | Who violates it |
|---|---|---|
| Prefer `skills:` over `Skill` in `tools` | `prompt-engineer.md:52` | all 7 agents (none declare `skills:`) |
| "Tools are authority… runtime constraints hold; instructions bend" | `prompt-engineer.md:41` | `sde-fullstack.md:42` — an instruction where a runtime field belongs |
| "One excellent example beats five mediocre ones" | `prompt-engineer.md:37` | `sde-fullstack`, `prompt-engineer`, `homelab-platform`, `multi-agent-architect` — no worked example |
| "Progressive disclosure — long reference material in separate files loaded on demand" | `prompt-engineer.md:39` | `backend-craft` (118 lines) and `frontend-craft` (123 lines) are flat monoliths |

Each of these is an internal contradiction, so each edit is justified by a rule the fleet already
declared — not by the author's taste. This matters because the fleet has no behavioral baseline: it
has been validated and routed, but not exercised. Fixing self-contradictions is the one class of
improvement that does not require one.

## Goals

- Make craft-skill loading a runtime guarantee rather than an instruction.
- Cut the always-on token cost of that guarantee.
- Give the three mandatory, non-obvious output shapes a worked example.

## Non-goals

- **Deduplicating the doctrine blocks.** The `[verified]`/`[sourced]`/`[unverified]` block is
  copy-pasted across five agents; "material fork" across four. Extracting it into a shared
  preloaded skill would move load-bearing text out of the system-prompt body — a behavior change
  that needs a baseline first. Deferred.
- **Rewriting craft-skill prose.** The split in Change 1 is a *move*. Every line survives verbatim.
- **Touching `homelab-platform`'s `service-onboard` path-read.** It is forced (see Verified facts)
  and already correct.
- **Changing any `description`.** Routing is therefore expected to be unaffected.

## Verified facts

Everything load-bearing below was checked, not assumed.

| Fact | Evidence |
|---|---|
| `skills:` preloads full skill content into a **plugin-shipped** subagent | Probe: two scratch agents granted `tools: Glob` only (no `Read`, `Bash`, or `Skill`) both quoted `req_8f3a2c` — the request-id from `backend-craft`'s error-envelope example. Glob returns paths, never content, so the string can only have arrived preloaded. |
| Bare skill names resolve; no namespace required | Same probe: `skills: [backend-craft]` and `skills: [sde-agents:backend-craft]` both worked. |
| Agent names, unlike skill names, **must** be namespaced at dispatch | Same probe: `subagent_type: probe-bare` was rejected; `sde-agents:probe-bare` succeeded. Undocumented asymmetry. |
| `skills` is supported for plugin agents | `code.claude.com/docs/en/plugins-reference` lists it as supported; only `hooks`, `mcpServers`, `permissionMode` are ignored. |
| A `disable-model-invocation: true` skill **cannot** be preloaded | `code.claude.com/docs/en/sub-agents`: "You can't preload skills that set `disable-model-invocation: true`, since preloading draws from the same set of skills Claude can invoke." This is why `service-onboard` keeps its path-read. |
| The validator already accepts `skills:` | `scripts/validate_fleet.py:52` — it is in `KNOWN_AGENT_FIELDS`. |
| The validator already existence-checks `references/*` links | `scripts/validate_fleet.py:331` (`validate_bundle_references`), added for `eng-ladder`. The split inherits it: a dangling routing-table link fails CI instead of silently starving the model. |
| Nothing else depends on `sde-fullstack` holding `Skill` | Grep across `agents/`, `skills/`, `README.md` returns exactly three skill-loading sites, all accounted for in Change 2. |

## Change 1 — Split the craft skills

**Split predicate** (stated so placement is checkable rather than argued): *does this rule apply to
every task in this layer, or only when the task involves X?* Universal rules stay in `SKILL.md`;
conditional rules move to `references/`.

`skills/backend-craft/SKILL.md` keeps **Contract first · Resiliency · Operability · Security ·
Testing & quality gate**. These move out:

- `references/stack.md` — greenfield stack selection (conditional: greenfield only)
- `references/consuming-apis.md` — integration discipline (conditional: calls an upstream)
- `references/background-work.md` — queues, schedulers, webhooks (conditional)
- `references/live-data.md` — SSE / WebSocket serving (conditional)
- `references/persistence.md` — Postgres, migrations, transactions (conditional: has a datastore)
- `references/auth.md` — serving-side auth (conditional: non-public routes)

`skills/frontend-craft/SKILL.md` keeps **Layout · Visual character · Motion · State and data ·
Routing & URL state · Resilience UX · Accessibility · Performance · Testing & quality gate**. Its
core stays fatter than backend's on purpose: the visual bar applies to every view, so most of the
skill is genuinely universal. These move out:

- `references/stack.md` — greenfield stack (conditional)
- `references/data-views.md` — tables, virtualization, bulk actions (conditional: tabular data)
- `references/data-viz.md` — charts (conditional: the view charts something)
- `references/forms.md` — form state and validation (conditional: the view has a form)
- `references/auth.md` — client-side auth (conditional: not localhost-only)

No prose is rewritten. Each moved section is relocated verbatim, so a reviewer checks *placement*
without re-litigating *content*.

Each core ends with a **routing table keyed to an observable predicate** — the form
`prompt-engineer.md:31` prescribes for conditional behavior:

| If the task involves… | Read before writing it |
|---|---|
| calling any upstream API | `references/consuming-apis.md` |
| a database or any persisted state | `references/persistence.md` |
| … | … |

## Change 2 — Preload, and delete the resolution dance

In `agents/sde-fullstack.md` frontmatter:

```yaml
skills:
  - backend-craft
  - frontend-craft
  - root-cause
```

- Remove `Skill` from `tools`. With all three preloaded the agent has nothing left to invoke, so the
  grant is authority it does not need.
- Delete the path-resolution paragraph (line 42) and the `root-cause` resolution clause (line 70).
  The agent gets shorter *and* more reliable.

In `skills/sre-tool/SKILL.md:42`, update the instruction that currently reads "`sde-agents:sde-fullstack`
holds the `Skill` tool, so spawned builders invoke skills themselves — name the skill, don't hand
them a SKILL.md path to `Read`". After this change it is false: builders arrive with the craft skills
already in context and orchestrators need name neither.

**Token cost, counted rather than estimated.** Preloading is unconditional: every `sde-fullstack`
spawn carries all three skills, including a backend-only task where `frontend-craft` is dead weight.

| | unsplit | split (core only) |
|---|---|---|
| `backend-craft` | 118 | ~68 |
| `frontend-craft` | 123 | ~85 |
| `root-cause` | 28 | 28 |
| **preloaded per spawn** | **269** | **~181** |

Change 1 buys a **33% cut** — not the 3x an earlier draft of this design claimed before the sections
were actually counted. The honest case for the split is therefore **not** primarily tokens; it is
**signal-to-noise in the always-on context**. The single largest thing leaving the core is the
`Stack` section of each skill (19 + 11 lines): the FastAPI/Go/Rust and TanStack/HeroUI-v3/Recharts-v3
pins. Those apply *only to greenfield*, they are the most rot-prone prose in the fleet, and
preloading them means every bug-fix spawn carries a confident stack opinion it must actively ignore.
That is interference, not merely waste.

The cost is accepted deliberately: the observed failure *is* the craft skill not loading, and
reliability on the fleet's builder outweighs the residual tokens.

**Fallback.** If Risk 1 (below) is judged to outweigh a 33% cut, drop Change 1 and preload the craft
skills unsplit. Change 2 and Change 3 stand on their own; only the token line and the second
behavioral check change.

## Change 3 — Three worked examples

Three mandatory, non-obvious output shapes have no example at all today:

1. **`sde-fullstack`** — a filled-in review packet. The workhorse agent, required to emit one every
   task, with zero examples.
2. **`homelab-platform`** — a Tier-2 approval request (target, exact command, blast radius,
   verification, rollback). This gate is the agent's reason to exist; a malformed one means an
   unsafe apply.
3. **`code-reviewer`** — a complete review: findings, verdict, and the explicit *independent* P0/P1
   count. That count (`code-reviewer.md:42`) is the subtlest rule in the fleet — it exists so a gate
   that only echoes its caller's suspicions is detectable — and nothing shows what honoring it looks
   like.

`prompt-engineer` and `multi-agent-architect` are skipped: simpler shapes, lower traffic.

## Verification

Schema checks are table stakes:

```bash
python3 scripts/validate_fleet.py
python3 -m unittest discover -s tests -v
claude plugin validate . --strict
```

Two behavioral checks carry the actual proof. Both use the canary technique validated during design
(grant the agent no content-reading tools; assert it can quote a string that exists only in the
skill).

- **Preload holds.** Spawn `sde-agents:sde-fullstack`; assert core craft content is present with
  zero `Read`/`Skill` calls in the transcript. This is the observed bug, dead, with evidence.
- **References are actually read.** Spawn it on a task that trips a predicate — *"build a client for
  the Grafana API"* — and assert it reads `references/consuming-apis.md` before writing the client.
  This is the check on Risk 1.

Both belong in `scripts/probe_plugin.py`, which already exists for exactly this class of question.

Finally, run `scripts/eval_routing.py` before and after. No `description` changes, so no movement is
expected — but running it is the fleet's own eval-first rule, and this is the first change since the
suite was built.

## Risks, ranked

1. **The split downgrades reliability for conditional content.** Today, if `backend-craft` loads at
   all, *all* of it is in context. Afterwards the deep material arrives only if the model reads the
   reference — the bendable layer this design is otherwise escaping. A reference that never gets read
   is worse than an always-on bullet. This is the one genuinely new risk introduced here. Mitigated
   by the predicate-keyed routing table, by the validator's existence check on the links, and
   measured directly by the second behavioral check. If that check fails, the fallback is to pull the
   affected section back into the core and accept its tokens.
2. **What lands in "core" is a judgment call.** Mitigated by the stated split predicate, and by the
   move-not-rewrite rule: placement is reviewable without re-reading content.
3. **Removing `Skill` from `sde-fullstack` is a capability removal.** Verified that only
   `sre-tool:42` depends on it, and that site is updated in the same change. A future caller wanting
   the builder to invoke some *other* skill would need the grant back.

## Open question

Whether preloaded skill content is as behaviorally load-bearing as system-prompt body text is
**[unverified]** — the docs do not say, and the design does not depend on it (Change 1 and 2 move
*skill* content, which was always intended to be loaded content). It becomes load-bearing only for
the deferred doctrine-dedup work, and should be settled before that starts.
