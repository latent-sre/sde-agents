# `sde-fullstack` agent and craft-chain audit — 2026-07-30 (condensed record)

> **Status:** dated review evidence, not a task list.
>
> The live status owner is [`docs/fleet-roadmap.md`](../../fleet-roadmap.md). Findings in this
> report become current work only if the roadmap imports them. Agent and skill definitions remain
> canonical; this report does not override them.
>
> **Condensed 2026-08-17.** Git history retains the full 959-line report (this path at
> `f4b119cf1a64a02bfabeedd5e074518e7d157fc4`): the complete recommended-change prose and
> acceptance-evidence lists for findings F-01–F-07 were never imported into the roadmap, so they
> retire to history with the reference-inventory snapshot. What survives here is the evidence a
> future session still consumes: the review record, per-finding dispositions, the reproduced F-03
> probe false-red mechanism, the F-08 verification provenance, and the O-01 preload measurement.

## Review record

| Field | Value |
|---|---|
| Reviewed commit | `4626ee96f263a834d0efa3ecf4b620e5e1a117c3` |
| Claude Code | `2.1.220` |
| Review posture | read every production file in the agent's execution chain (agent, four preloaded skill cores, all 24 routed references, conditional `ci-actions`, hooks, guard, validator, eval suites) |
| Overall verdict | strong implementation core; authority and assurance gaps remain; no P0 |

After the audit snapshot froze, the operator authorized follow-ups on the report branch:
expanding the Go and Python references, adding React and Vue references, and correcting generic
frontend material that silently assumed React (F-08 below). Those shipped; the candidate
findings did not.

## Finding dispositions

| Finding | Severity | One-line claim | Disposition |
|---|---|---|---|
| F-01 | High | external effects (push, publish, deploy) had no explicit authorization boundary in the agent contract | never imported as written; the concern was later addressed through a different lineage (the tier/work-order/gate mechanism now in `agents/sde-fullstack.md`) |
| F-02 | High | direct high-risk work could self-certify without independent review/security/verification gates | never imported as written; same later lineage as F-01 |
| F-03 | High (assurance) | the live preload probe can report a false failure on async agent launches | reproduced, mechanism recorded below; probe repair recommended first in the sequence |
| F-04 | Medium | auth references stopped before object/tenant authorization, OAuth/OIDC, and CSRF boundaries | candidate reference expansion; never imported |
| F-05 | Medium | the agent's paraphrase narrowed `code-craft`'s tdd/safe-refactor predicates | candidate wording fix; never imported |
| F-06 | Medium | behavioral coverage did not exercise the builder's authority/handoff/reference-loading contracts | candidate eval coverage; never imported |
| F-07 | Medium | frontend verification had no guaranteed browser capability | trigger-bound capability candidate; never imported |
| F-08 | Low/Medium | language and framework depth was uneven (shallow Python, React embedded in generic TypeScript, no Vue) | **shipped on the report branch**: expanded `go.md`/`python.md`, new `react.md`/`vue.md`, framework-neutral `typescript.md`; provenance below |
| O-01 | observation | measure preload cost before changing the preload design | measurement recorded below |

## F-03 — the reproduced probe false-red mechanism

`scripts/probe_plugin.py::agent_spawn_results` correlates an `Agent` (or legacy `Task`) tool call
to an immediate `tool_result` by `tool_use_id` — correct when the completed agent response
returns inline. In the observed live run on CLI `2.1.220`, Claude launched the probed subagents
**asynchronously**: the immediate `tool_result` only reported the launch, and the completed
answer arrived later in a task-completion notification the parser does not consume. Both craft
canaries were therefore absent from `fullstack_text`:

```text
python scripts/probe_plugin.py
12/14 passed, 2 failed, 0 inconclusive
FAILED: backend-craft core content was preloaded (canary quoted)
FAILED: frontend-craft core content was preloaded (canary quoted)
```

The underlying runtime behavior was healthy: a clean-room session (isolated `CLAUDE_CONFIG_DIR`
via `scripts/eval_clean_room.py`, no personal `skills/` directory, `tool_uses: 0`) returned both
canaries correctly, and a second trusted clean-room task proved the conditional Go-reference read.
Two operational caveats from the reproduction: the disposable target's trust state must be
established explicitly or its scoped probe permissions are silently ignored; and the normal
(non-clean-room) probe inherits the operator's personal configuration, so hash-identical
user-global skill copies mask plugin-provenance drift. The recommended repair — extend
agent-result correlation to consume task-start/task-completion events with exact call and agent
attribution, never fall back to a transcript-wide canary search (that recreates the false-green
path) — was not imported at the time; the mechanism is recorded here because a canary that can
be red for the wrong reason cannot gate CLI upgrades.

## F-08 — verification provenance for the shipped reference expansions

Primary-source snapshot pins (evidence snapshots, not version recommendations):

- Go: official documentation and `golang/go` at `145001b82a7b23d0e2510e48bdf0f7608a699700`;
- Python: language/stdlib documentation, packaging specifications, and the PEP-owned version
  boundaries;
- React: `reactjs/react.dev` at `9e97ad0bbc38800041ce908250fe0128a2d437b1` and released
  `facebook/react` tag `v19.2.4`;
- Vue: `vuejs/docs` at `7681134fd8505e61a265d161d73d28acb3c74822` and released `vuejs/core` tag
  `v3.5.40`.

Before the edits, two isolated baseline sessions reproduced the gap (React and Vue tasks read
only generic TypeScript material). Eight post-edit clean-room sessions — isolated
`CLAUDE_CONFIG_DIR`, no personal skill tree, the plugin's namespaced `sde-agents:sde-fullstack`
run directly — are the behavioral proof that the shipped references load on the right predicates
and not on near-misses:

| Case | Exact conditional-read result |
|---|---|
| React 18 nested-component identity | read `react.md`; also forms, TypeScript, safe-refactor, TDD |
| React 19 hydration and unsafe HTML | read `react.md`; also forms and TypeScript |
| Vue 3.5 computed/watcher cleanup | read `vue.md`; also TypeScript, safe-refactor, TDD |
| Vue 3.4 SSR request isolation | read `vue.md`; also TypeScript and auth |
| vanilla TypeScript custom element | read neither `react.md` nor `vue.md` |
| Preact TSX | read neither `react.md` nor `vue.md` |
| Python 3.11 task ownership | read `python.md`; returned structured cancellation ownership |
| Python 3.9–3.12 compatibility | read `python.md` under an explicit multi-version-floor task |

The first post-edit batch was discarded when its Windows console could not encode Unicode result
text; the ASCII-safe rerun above is the evidence counted — a completed model call without a
preserved transcript summary was not treated as proof. The earlier Go clean-room check recorded a
`Read` of the branch's exact `skills/code-craft/references/go.md` and recovered distinctive new
rules (main-module timer semantics, HTTP handler lifetimes, `QueryRowContext.Scan`, Go 1.25
`testing/synctest` external-I/O boundaries).

## O-01 — the preload token observation

A trivial clean-room canary task returned the correct answer with zero tool calls and reported
**21,590 total subagent tokens**. Attribution is incomplete: the total includes the agent prompt,
project context, Claude system context, and response, so it is not a skill-only cost. Recorded as
a before-point for any preload redesign; the audit's ruling was to retain the four-preload design
unless a measured variant preserves behavior at materially lower cost.
