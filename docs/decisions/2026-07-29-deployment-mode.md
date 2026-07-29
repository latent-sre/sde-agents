# Fleet deployment mode on the operator's machine

**Status:** Proposed — parked deliberately by the operator on 2026-07-29 (fresh-look session);
tracked as roadmap `DEPLOY-001`
**Date:** 2026-07-29
**Verified state at writing:** `~/.claude/skills` and `~/.claude/agents` are NTFS junctions into
this repository, and `sde-agents` appears in neither `installed_plugins.json` nor
`enabledPlugins`. Confirmed live the same day: agents register **bare** (un-namespaced) in a
normal session, and a fleet edit deploys instantly through the junction.

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

## Reopen triggers

- Before implementing LABSEC-002 (a guard-enforced agent must not ship into a deployment where
  the guard never runs).
- Before any second user installs the plugin.
- Any real incident in which a junction-session agent performed a write its guarded-mode contract
  would have denied.
