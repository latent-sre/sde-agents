# SDE Agents

A focused fleet of software-engineering and home-lab agents plus reusable skills, packaged as a
Claude Code plugin. The definitions in `agents/` and `skills/` are the canonical source — and, since
a plugin's components live at its root, they are also exactly what Claude Code loads. There is no
generated copy and no second source of truth.

## Fleet

<!-- fleet-inventory:start -->
- **Agents (7):** `code-reviewer`, `distinguished-architect`, `homelab-platform`, `multi-agent-architect`, `principal-engineer`, `prompt-engineer`, `sde-fullstack`
- **Skills (9):** `backend-craft`, `eng-ladder`, `frontend-craft`, `lab-audit`, `prompt-craft`, `root-cause`, `runbook`, `service-onboard`, `sre-tool`
<!-- fleet-inventory:end -->

Refresh the generated block after adding, renaming, or removing an agent or skill:

```bash
python3 scripts/validate_fleet.py --write-inventory
```

## Install

```
/plugin marketplace add latent-sre/sde-agents
/plugin install sde-agents@latent-sre
```

That is the whole installation. The agents, the skills, and the read-only guard all ship together;
nothing is copied into `~/.claude`, and there is no separate setup script to forget.

Components are **namespaced** by the plugin, so they are `sde-agents:code-reviewer`,
`/sde-agents:backend-craft`, and so on. The fleet's own cross-references use those names.

### Working on the fleet itself

`/plugin install` runs from a cached copy, which is the wrong loop when the plugin *is* what you are
editing. Load it straight from the working tree instead:

```bash
claude --plugin-dir .
```

## Project context convention

Agents should use the target repository's existing project-instruction file. `AGENTS.md` is the portable
default; if a repository already uses an equivalent such as `CLAUDE.md`, respect it instead of creating a
competing file. Record the environment card and mission block there.

Long-running work should use the progress file declared by that project context. When none is declared,
use `.agents/PROGRESS.md`. Progress files are coordination state, not a substitute for the final review
packet or committed documentation.

## The read-only guard

`code-reviewer` holds `Bash` so it can run `git diff`/`log`/`show`/`blame` and the existing test
suite. A `PreToolUse` hook denies the state-changing and data-egress verbs, so "read-only" is
enforced rather than promised.

The wiring is not obvious, and the reason matters:

**A plugin-shipped agent cannot carry its own `hooks:`.** Claude Code silently ignores `hooks`,
`mcpServers`, and `permissionMode` on plugin agents ("not supported for plugin-shipped agents" —
[plugins-reference](https://code.claude.com/docs/en/plugins-reference)). No error, no warning. So a
guard written into `agents/code-reviewer.md` would look exactly like armor and be nothing at all —
strictly worse than no guard, because nobody would go looking.

The guard therefore lives in `hooks/hooks.json`, which Claude Code registers **session-wide**, and
scopes *itself*: it no-ops unless the pending call's `agent_type` names a guarded agent. The main
session carries no `agent_type` at all, so your own Bash is never inspected — the hook costs one
shell glob and never even starts an interpreter.

Two properties fall out of that, both load-bearing and both tested:

- It runs from `${CLAUDE_PLUGIN_ROOT}` — the plugin's installed copy — so it can never execute a
  guard supplied by the repository under review.
- It fails **closed** for the reviewer (no working Python, missing or broken guard → deny) while
  leaving every other caller untouched. A broken install degrades the reviewer; it cannot brick your
  session.

`agent_type` is real but undocumented. If it is ever renamed upstream to another agent-named key
(`subagent_type`, `agentType`, …), the guard fails closed with an explicit message rather than
quietly ceasing to guard. A rename to something that no longer says "agent" at all would escape that
canary — the probe below is the backstop that catches it, which is why it must be re-run after CLI
upgrades.

One honest collision: the guard matches the *bare* name too, so any agent named `code-reviewer` from
any source — another plugin, your own `~/.claude/agents` — gets read-only Bash enforcement from this
plugin while it is enabled. That is deliberate (the guard must not be sidestepped by installing the
agent at a different scope), and the deny message names this guard so the collision is diagnosable.

Honest boundary: the guard is a denylist, not a sandbox. It stops the common state-changing verbs a
cooperative agent emits; it will not stop a determined adversary who fully controls the command
string. The load-bearing control is OS-level least privilege.

## Validation

```bash
python3 scripts/validate_fleet.py
python3 -m unittest discover -s tests -v
claude plugin validate . --strict
```

The validator checks frontmatter, names, descriptions, explicit agent tool authority (against a known
tool vocabulary), models, bundled skill references, the canonical evidence-label phrasing, the required
end-of-task packet heading, and README inventory drift. It is intentionally runtime-neutral and uses
only the Python standard library.

It also enforces the plugin invariants that fail *silently* at runtime: no agent may declare a field a
plugin ignores; every read-only agent holding `Bash` must be registered with the guard; the guard's
plugin name must match the manifest; the hook must resolve the guard through `${CLAUDE_PLUGIN_ROOT}`;
cross-references in **descriptions** must be namespaced (body text is namespaced by convention but not
machine-checked — prose mentions and invocation instructions are not reliably distinguishable by
regex); and no definition may resolve a fleet file under `~/.claude`, which does not contain this
fleet once it ships as a plugin.

`claude plugin validate --strict` covers the other half — the platform contract, which the Python
validator cannot see: manifest schema, frontmatter parsing, and hook JSON, with warnings as errors.

## Verifying the plugin

The validators prove the files are well-formed. They cannot prove the fleet actually *loads*, that
`${CLAUDE_PLUGIN_ROOT}` expands where the agents rely on it, or that the guard fires for the reviewer
and only the reviewer. That takes a behavioral probe against a real session:

```bash
python3 scripts/probe_plugin.py
```

It loads the plugin with `--plugin-dir .`, drives a headless run, and asserts against the transcript.
Re-run it after upgrading the Claude Code CLI: it is what turns an undocumented payload field from a
silent-disarm risk into a loud failure.
