# Multi-platform packaging and authority adapters

**Status:** Accepted and implemented on 2026-07-30
**Date:** 2026-07-30

## Context

The fleet was authored as a Claude Code plugin. Codex, GitHub Copilot CLI, and VS Code Agent
Plugins can consume similar Markdown skills and agents, but their formats are not interchangeable:

- Claude agent definitions use Claude frontmatter, plugin namespaces, preloaded skills, and
  `${CLAUDE_PLUGIN_ROOT}`.
- Copilot and VS Code custom agents use `.agent.md` files and host tool aliases. Their
  `PreToolUse` payload does not identify the active custom agent.
- Codex custom agents are standalone TOML with a sandbox mode. Codex plugins package skills,
  hooks, apps, and MCP servers, but not custom-agent TOML.
- Codex and Copilot express explicit skill invocation differently.

Copying the Claude files unchanged would therefore preserve the appearance of controls while
silently dropping namespaces, tool restrictions, paths, or hooks.

The format comparison uses the current official
[VS Code Agent Plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins),
[Copilot CLI plugin](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference),
[Codex plugin](https://developers.openai.com/plugins/build/plugins), and
[Codex custom-agent](https://learn.chatgpt.com/docs/agent-configuration/subagents.md)
contracts. Runtime behavior still belongs to each installed host version.

## Decision

### One authored fleet

`agents/` and `skills/` remain the only authored definitions. Claude Code loads them directly.
`scripts/generate_platform_adapters.py` derives every other host artifact and the fleet validator
compares the tracked output byte for byte.

Generated artifacts are:

| Host | Agent artifact | Skill artifact | Package entry point |
|---|---|---|---|
| Claude Code | `agents/*.md` | `skills/*` | `.claude-plugin/plugin.json` |
| Copilot CLI / VS Code | `.github/agents/*.agent.md` | `platforms/copilot/skills/*` | `plugin.json` |
| Codex | `.codex/agents/*.toml` | `plugins/sde-agents/skills/*` | `.agents/plugins/marketplace.json` → nested `.codex-plugin/plugin.json` |

The Codex plugin is nested deliberately. Its plugin root has no `hooks/hooks.json`, so default
component discovery cannot load Claude's session hook.

### Translate authority, not just syntax

Claude retains its session-wide allowlist hook for roles whose Bash contract is read-only.
Copilot and VS Code do not expose the active agent identity in `PreToolUse`, so those guarded roles
receive no `execute` tool. Codex profiles with no canonical write tool request
`sandbox_mode = "read-only"`; canonical writers request `workspace-write`. Those values are agent
defaults rather than immutable boundaries: parent live permission changes and full-access mode
override them and are reapplied to child agents. Codex custom-agent TOML also has no per-agent
tool allowlist, so inherited shell and subagent capabilities remain available unless an outer
boundary removes them.

The adapters therefore state Codex no-write, no-shell, and no-spawn mandates as cooperative when
parent authority remains broader. Document-only authority, approval requirements, and live-effect
limits likewise remain cooperative unless the host provides a stronger outer control.

Claude `skills:` preloads become explicit required-skill instructions because neither generated
agent format packages that frontmatter contract. Agent bodies and prompt-authoring references also
replace Claude-only hook, tool-name, and context-inheritance claims with the target host's actual
boundary.

### Keep host-specific skill policy

Both generated skill copies remove Claude namespaces and installed-root paths and serialize
frontmatter as valid YAML. Copilot retains `disable-model-invocation: true`. Codex removes that
unsupported value and generates `agents/openai.yaml` with
`policy.allow_implicit_invocation: false`.

### Distribute Codex agents honestly

Codex plugins currently do not package custom-agent TOML. The repository keeps `.codex/agents/`
for project-scoped use and provides `scripts/install_codex_agents.py` for an explicit user or
alternate project sync. The installer owns only marked files, adopts only an exact generated copy,
preflights every conflict before mutation, and prunes only stale managed files. User-scope sync
uses `$CODEX_HOME/agents` when configured and otherwise defaults to `~/.codex/agents`.

## Rejected alternatives

- **Load the Claude files unchanged everywhere.** Rejected because syntax that looks plausible but
  is ignored is worse than an explicit adapter.
- **Reuse the Claude hook on every host.** Rejected because its scope depends on an active-agent
  payload field that Copilot, VS Code, and Codex do not provide on `PreToolUse`.
- **Use one shared "portable" skill copy.** Rejected because Copilot and Codex encode
  explicit-invocation policy differently.
- **Keep the Codex manifest at repository root.** Rejected because Codex default discovery would
  see Claude's incompatible `hooks/hooks.json`.
- **Maintain four authored fleets.** Rejected because fixes and authority changes would drift
  independently with no reliable owner.
- **Use symlinks for generated components.** Rejected because installed plugin archives and
  Windows checkouts do not preserve a dependable cross-host symlink contract.

## Consequences

- Any canonical agent or skill edit owes adapter regeneration.
- Generation rejects symlinks, junctions, and reparse points in canonical resources and generated
  roots so a local indirection cannot redirect reads or recursive replacement.
- Untracked Python cache residue is ignored only when Git proves it is untracked; archives and
  other non-worktree copies validate cache-shaped files strictly.
- An added host contract becomes a generator and validator change, not another hand-maintained
  corpus.
- Claude routing measurements remain measurements of the canonical descriptions. Generated-only
  wording does not trigger a second routing-eval gate.
- Copilot/VS Code and Codex runtime smoke tests remain version-specific manual checks; offline CI
  proves structure, parity, generated currency, and the authority mapping.

## Reopen triggers

- A host gains a reliable active-agent identity in `PreToolUse`.
- Codex plugins gain first-class custom-agent packaging.
- A host adds an enforceable skill-level tool deny that can replace a cooperative boundary.
- A manifest or frontmatter version changes the discovery or invocation contract.
