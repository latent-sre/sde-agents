# Fleet deployment mode on the operator's machine

**Status:** Accepted — Option A (installed plugin, no active fleet junctions) on 2026-07-31
**Date:** Proposed 2026-07-29; accepted and applied 2026-07-31
**Previous state:** `~/.claude/skills` and `~/.claude/agents` were NTFS junctions into this
repository, and `sde-agents` appeared in neither `installed_plugins.json` nor `enabledPlugins`.
Agents therefore registered **bare** (un-namespaced) in a normal session and the plugin guard was
dormant.
**Current state:** `sde-agents@latent-sre` 1.4.0 is installed and enabled at user scope from the
local marketplace. The active junction names are absent, so normal sessions load one namespaced
fleet with its hook guard.

**Scope clarification (2026-07-30):** This record governs only the operator's daily Claude Code
deployment. Consumer and cross-host packaging is governed by the accepted
[`multi-platform packaging decision`](2026-07-30-multi-platform-packaging.md), so a new Codex,
Copilot, VS Code, or plugin-mode Claude consumer does not force this machine-local choice.

## Decision question

Should the fleet's daily deployment on this machine be the installed plugin (which arms the hook
guard and the namespace), or the junctions (which give an instant dev loop), or deliberately
both-with-eyes-open?

## Why this needs a decision at all

The repository's governance investment assumes plugin mode, but daily use runs junction mode:

- **The read-only guard is dormant in every normal session.** Hooks ship with the plugin;
  junction-deployed components register with no plugin and no hook. `code-reviewer`,
  `principal-engineer`, and `distinguished-architect` hold Bash with prose-only restraint outside
  `--plugin-dir` sessions (verified previously: a junction-session reviewer ran a non-allowlisted
  command unblocked). GOV-001 hardens a control that daily use never arms; LABSEC-002's entire
  premise is that guard.
- **Namespaced cross-references name a form that does not exist under junctions.** The validator
  enforces `sde-agents:X` in descriptions; junction-registered components are bare `X`.
- **The routing evals measure plugin mode** (`--plugin-dir .`), i.e. a deployment the operator's
  daily sessions do not run.

None of this is new breakage — it was probed on 2026-07-19 — but no decision record governed it
until now, and further guard investment (GOV-001 hardening, LABSEC-002) should not proceed as if
the guard were armed daily.

## Options

| Option | What it buys | What it costs |
|---|---|---|
| **A. Install as plugin, drop junctions** (recommended) | Guard + namespacing real in daily use; matches README install story, validator claims, and eval conditions | Fleet edits reach daily sessions only after a plugin update from the local marketplace path; dev sessions keep `claude --plugin-dir .` (already the documented loop) |
| **B. Keep junctions, record the dormancy honestly** | Instant-deploy dev loop stays; zero friction | Guard remains probe-time-only; README/AGENTS must say so; LABSEC-002 loses most of its value; namespace enforcement stays aspirational |
| **C. Both (plugin enabled + junctions kept)** | — | Rejected: components double-register (bare and namespaced), which is strictly worse for routing than either mode alone |

## Recommendation

Option A, because the fleet's own documentation, validator invariants, and eval conditions all
already assume it — Option B is coherent but means maintaining an honest "the armor is displayed,
not worn" caveat everywhere the guard is described. The friction cost of A is one update command
after fleet edits, and probe/eval work already uses `--plugin-dir` regardless.

## Acceptance evidence — 2026-07-31

The operator accepted Option A after PR #53 merged at `a445623`. The migration was rollback-first:

- The pre-change Claude settings and plugin inventories were copied to
  `~/.claude/deployment-backups/sde-agents-plugin-mode-2026-07-31/` with SHA-256 hashes recorded in
  the operator transcript.
- `claude plugin marketplace add C:\Users\hawkins\sde-agents --scope user` registered the
  `latent-sre` directory marketplace, then
  `claude plugin install sde-agents@latent-sre --scope user` installed and enabled version 1.4.0.
  The cached copy contains the manifest, canonical agents and skills, hook registration, and
  `scripts/readonly-guard.py`.
- The active junction entries were renamed, not deleted, to
  `~/.claude/agents.sde-agents-junction-backup-2026-07-31` and
  `~/.claude/skills.sde-agents-junction-backup-2026-07-31`. Their targets remain this repository;
  neither backup name is a Claude component-discovery root.
- `scripts/fleet_doctor.py --json` reports `pass` for the Claude plugin, deployment, and read-only
  guard checks. Its overall exit remains nonzero only because the separately tracked unmanaged
  Codex-agent collision is outside this decision.
- A normal session with `--agent sde-agents:code-reviewer`, user settings, explicit model `haiku`,
  and **no** `--plugin-dir` resolved the namespaced agent and attempted the exact read-only search
  `find . -name "*.md" -exec grep -l DEPLOY_REVIEWER_PROBE {} \;`. The plugin guard denied it with
  its own `read-only agent` reason; Claude's permission layer did not block it first.
- A second normal session, also explicit `haiku` and without `--plugin-dir`, ran the equivalent
  `DEPLOY_MAINLOOP_PROBE` command in the main loop. It completed normally, proving the hook remained
  scoped to guarded agents. These were deployment contract probes, not model baselines; no Opus
  baseline was run.

Rollback is intentionally recoverable: uninstall `sde-agents@latent-sre` at user scope, remove the
`latent-sre` user marketplace, verify the active `~/.claude/agents` and `~/.claude/skills` names are
absent, then rename the two backup junctions to those original names. The dated configuration
copies are emergency evidence, not a standing restore source after unrelated settings change.

## Reopen triggers

- A Claude CLI or plugin upgrade makes a normal-session namespaced agent fail to load or makes the
  guard denial/main-loop scoping probes fail.
- The active fleet junction names reappear, which would double-register bare and namespaced
  components if the plugin remains enabled.
- Update friction becomes operationally material enough to reconsider Option B. Option C remains
  rejected: never enable the plugin and active fleet junctions together.
