# Claude Code frontmatter — agents & skills

Read this before writing or editing the frontmatter of any agent or skill file. It is the fleet's
**single source of truth** for Claude Code frontmatter facts — the two prose copies it replaced (in
`prompt-craft`'s body and `agents/prompt-engineer.md`) drifted within one release, so platform facts
live here and only here. `validate_fleet.py` keeps the authoritative *field sets*
(`KNOWN_AGENT_FIELDS`, `KNOWN_SKILL_FIELDS`) checked against code; on any conflict with the live
docs (code.claude.com/docs/en/sub-agents, code.claude.com/docs/en/skills), the docs win — update
this file, re-verify after CLI upgrades.

## Agents

Locations: `agents/*.md` in a plugin; `.claude/agents/*.md` project-level; `~/.claude/agents/*.md`
user-level. A project-level definition shadows a user-level one of the same name.

Required: `name`, `description` (the trigger). Optional: `tools`, `disallowedTools`, `model`,
`permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`,
`isolation`, `color`, `initialPrompt`.

Authority lives in frontmatter, not in prose — the fields that carry it:

| Field | Notes |
|---|---|
| `tools` | Allowlist. **Omitting it inherits every tool** — omission is "all tools," not "none." `Agent(worker)` scoping works only for a main-thread agent (`claude --agent`); a subagent silently ignores the type list, so it reads like a limit and isn't one. `AskUserQuestion`, `EnterPlanMode`, `ScheduleWakeup`, `WaitForMcpServers` are never available to a subagent, however listed; `ExitPlanMode` only under `permissionMode: plan`, which a plugin-shipped agent can't set. |
| `disallowedTools` | Denylist; applied before `tools` resolves. |
| `permissionMode` | `default \| acceptEdits \| auto \| dontAsk \| bypassPermissions \| plan \| manual`. Ignored for plugin-shipped agents, so this fleet (a plugin) rejects the field outright — `validate_fleet.py` flags it as configuration that does not exist. |
| `hooks` | Agent-scoped lifecycle hooks. Real at project/user scope, **inert in a plugin**. A plugin must instead ship `hooks/hooks.json`, which is session-wide, and scope the hook itself on the payload's `agent_type` — that is how this fleet guards `sde-agents:code-reviewer`'s `Bash`. |
| `skills` | Preloads full skill content at startup — prefer this over putting `Skill` in `tools`. Don't list a `disable-model-invocation: true` skill here — the fleet's validator rejects it as policy. (Documented behavior is that such skills can't be preloaded; since that flag is unreliable in a plugin — see the caveat under Skills below — the fleet enforces the rule rather than depending on the runtime honoring it.) |
| `model` | Aliases `haiku \| sonnet \| opus \| fable \| inherit`, or a full ID (`claude-opus-4-8`); defaults to `inherit`. Use an alias — this fleet rejects pins, which rot silently while an alias follows the upgrade. |
| `memory` | `user \| project \| local`. **Setting it auto-enables Read, Write, and Edit** — never add it to a read-only agent (it would silently widen `sde-agents:code-reviewer`'s mandate). |

Also: `maxTurns` (int), `background` (bool), `effort` (`low|medium|high|xhigh|max`), `isolation`
(`worktree`), `color`, `initialPrompt` (main-session only).

Plugin-packaged agents **ignore** `hooks`, `mcpServers`, and `permissionMode` — a guard that works
locally is silently absent once the agent ships in a plugin. Spell keys exactly: an unrecognized key
is not guaranteed to fail loudly, so a typo can silently drop what it configured
(`validate_fleet.py` rejects unknown keys for that reason).

## Skills

Locations: `skills/<name>/SKILL.md` in a plugin; `.claude/skills/<name>/SKILL.md` project-level.
Precedence for **same-named non-namespaced skills** is the **reverse** of agents: a personal
(user-level) skill overrides a project-level one — enterprise → personal → project → bundled. Plugin
skills are namespaced (`plugin:name`, e.g. `sde-agents:service-onboard`) and don't participate in
that chain — a same-named project skill does not shadow them.

Core fields: `name`, `description` (the trigger), `argument-hint`. Behavior switches:

- `disable-model-invocation: true` — intended for side-effect skills (deploy, send, commit):
  user-only via `/name`, description removed from the model's context, and not preloadable via an
  agent's `skills:` field. **Caveat — version-sensitive, not timeless: this flag is currently
  ignored for plugin-shipped skills** (anthropics/claude-code#22345; last verified against CLI
  2.1.212, 2026-07-17 — the issue was open and the docs still described the flag as preventing
  model invocation). A plugin skill so marked still loads into context and stays model-invocable.
  Set it anyway (correct once fixed, and it documents intent), but do not treat it as an enforced
  boundary in a plugin; make the skill's own content defer authority instead. Re-verify after CLI
  upgrades — `scripts/probe_plugin.py` is the capability test — and update this stamp.
- `user-invocable: false` — background-knowledge skills, hidden from the `/` menu.
- `allowed-tools` **grants** (pre-approves, no permission prompt) while the skill is active — it
  does **not** restrict availability. Takes bare tool names or permission-rule specifiers
  (`Bash(git add *)`).
- `disallowed-tools` **removes** tools while the skill is active (clears on the next user message) —
  this is the restricting field.

Also available: `when_to_use`, `arguments`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`,
`shell` — not exhaustive; see code.claude.com/docs/en/skills for the current table
(`validate_fleet.py` keeps `KNOWN_SKILL_FIELDS` as the fleet's checked copy).

Keep descriptions lean — they load into context every session.

## Fleet decisions on unused fields

Fields the fleet deliberately does not use — considered, not overlooked. Reopen only with a reason:

- **`when_to_use`** — trigger phrasings live in `description` so routing has one surface to tune
  (and one surface for the routing evals to measure). Both fields share the same 1,536-character
  listing cap, so splitting saves nothing.
- **`maxTurns`** — loop bounds are task-shaped prose rules (three-strikes, two-round review caps),
  which fail with a diagnosis; a turn cap fails mid-thought. Revisit if a runaway loop is ever
  actually observed.
- **`memory`** — agents are stateless by design; durable lab knowledge lives in the repo (runbooks,
  `CLAUDE.md`). And setting `memory` auto-enables Read/Write/Edit, so it must never be added to
  `sde-agents:code-reviewer`.
