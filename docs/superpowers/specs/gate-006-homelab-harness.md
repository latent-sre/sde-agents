# GATE-006 spec — homelab live-effect gate and gate-vocabulary fold

**Status: approved** — operator ruling 2026-08-29 ("lets do 1": Track A of the homelab-platform
audit runs first, the body diet second). This spec is the implementation authority for the plan
at `docs/superpowers/plans/gate-006-plan.md`; acceptance is not met until the evidence in
"Acceptance" is committed.

## Problem

`agents/homelab-platform.md` was audited on 2026-08-29 against the fleet's five engineering
strands (prompt, context, harness, loop, graph). Its authority model is home-lab sized; its
transport prose is not enforceable and its closed grammar is wider than the model reliably emits.
The measured fact: on the current text's own lane (sonnet, clean room, five runs per case,
`docs/archive/2026-08/ctx-005-engineering-discipline-audit-2026-08-23.md`) the agent passes
60/130 of the contracts pinned to it, ten of twenty-six at 0/5, and the zero cluster is transport
evidence and declaration sets. Seven defects, each with a structural fix:

1. **Managed-gate evidence is unprovable on Claude Code.** The agent must inspect "the effective
   control for that argv" before invoking and never invoke to find out. Claude Code exposes no
   non-executing permission evaluation to the model, and the plugin ships no hook that forces a
   prompt for this agent (`hooks/hooks.json` guards four read-only agents only). By its own rule
   every Tier 2 apply on Claude falls to operator handoff.
2. **Standing policy is self-defeating on Claude Code.** It must be "outside your writable
   authority"; the agent holds `Write`/`Edit`, and Claude permission rules live in settings files
   it can edit.
3. **The lethal trifecta.** `WebFetch`+`WebSearch` on an agent that also holds `Bash`+`Write` and
   reads `.env` files, defended by one sentence of prose.
4. **Unbounded identical retries** after a "confirmed transient failure".
5. **Two taxonomies for one fact.** `Effect class:` (GATE-001's reviewer/builder classification) is
   1:1 with `Tier:` except "optional hardening", which the text itself says "gates as whatever
   effect it is"; the model fails to emit the three-line set (`gate-two-effects-declare-one-set-each`
   and `gate-same-effect-consolidation-deletion` at 0/5).
6. **Onboarding floor charged twice.** The body restates `service-onboard`'s four applicability
   predicates because the two `onboard-*` contracts deny `Read`, so the skill is unreachable in
   the eval.
7. **No stop conditions, no lab-profile gate, guard-denied conflated with not-granted** — the
   loop and context gaps the sibling's `sre` agent closes in three sentences.

## Scope — seven decisions, one branch, one PR

Recorded in `docs/decisions/2026-08-29-homelab-live-effect-gate.md` (accepted). In one line each:

1. The plugin ships the interposition: `scripts/live-effect-gate.py`, registered in
   `hooks/hooks.json` as a second `PreToolUse`/`Bash` hook scoped to `agent_type`
   `homelab-platform`; `ask` for a live-effect argv when the session can prompt, `deny` when the
   payload's `permission_mode` says it cannot (`bypassPermissions`, `dontAsk`, `auto`) or is
   absent, no decision otherwise; a static `ask`/`deny` fallback when no interpreter answers.
2. The agent's transport evidence becomes structural: running as the plugin agent on Claude Code
   *is* the evidence; Codex's sandbox/approval prompt is its gate; anything else is operator
   handoff. "Never run a live command to discover whether it prompts" stays.
3. Standing policy on Claude Code qualifies only from managed (administrator-owned) settings;
   on Codex from a root-owned exec-policy path.
4. One `consolidated` retry; a second failure of the same effect stops the plan, opens
   `sde-agents:root-cause`, and returns the next effect as `new`.
5. `Effect class:` is retired from the declaration set, the worked example, `packet_lint.py`'s
   vocabularies, and every contract; `Tier:` carries the classification; the three-way
   finding-effect classification (merge blocker / live-activation blocker / optional hardening)
   is owned by `agents/code-reviewer.md`.
6. `WebFetch` and `WebSearch` leave the agent's `tools:`; external lookups return to the caller
   for `sde-agents:researcher`.
7. `service-onboard` owns the applicability predicates; the body keeps the floor and the
   read-by-path rule; the two `onboard-*` contracts grant `Read` so the skill is reachable.

Plus three sentences: stop conditions, read-the-lab-profile-first, not-granted ≠ guard-denied.

## Non-goals

- The always-loaded body diet (CTX-005): no passage is compressed here except where its words
  contradict a decision above. Sizes are recorded, not targeted.
- The `description:` field — unchanged byte for byte, so no routing capture is owed.
- The Learning slot (fleet-wide, validator-pinned; CTX-001 keeps it out of scope).
- Sentinel/preflight reuse (2026-08-23 decision 4) — unchanged.
- Porting either hook to Codex or Copilot (`AGENTS.md` hard rule).

## Acceptance

1. `tests/test_live_effect_gate.py`, `tests/test_hook_wiring.py`, `tests/test_packet_lint.py`,
   `tests/test_eval_behavioral.py`, `tests/test_validate_wiring_guard.py` green, each new
   invariant with a red-first test (a mutation that removes the gate entry, the roster, or the
   verb table fails the named test).
2. `python scripts/validate_fleet.py` green; adapters regenerated; `python scripts/run_tests.py`
   green; `claude plugin validate . --strict` green; `python scripts/fleet_doctor.py` exit 0 or
   3 with every warning read.
3. `agents/homelab-platform.md` carries none of: `WebFetch`, `WebSearch`, `Effect class`, the
   five-class list, the four onboarding predicate bullets; and all of: the gate-evidence line,
   the retry cap, the stop conditions, the lab-profile sentence, the not-granted sentence.
4. `evals/behavioral/contracts.json`: no `Effect class` key anywhere; `onboard-*` cases grant
   `Read`; `gate-second-failure-stops-plan` exists with an offline oracle control;
   `gate-owner-attribution-stacked` accepts `command-approval`; the case count and the
   `evals/README.md` figures agree.
5. **Paid, operator purchase, owed before merge:** `python scripts/probe_plugin.py` shows the
   gate denying `homelab-platform` under `--permission-mode dontAsk` and not the main loop; and a
   paired behavioral lane — before on `origin/main` `305ac1a` in its own worktree, after on the
   branch head — under `--model sonnet --clean-room --runs 5 --timeout 600 --concurrency 3`,
   captured to `evals/baselines/2026-08-29-gate-006/{before,after}/`. The success contract is
   CTX-005's, carried over: every baseline-perfect case stays 5/5; aggregate does not fall below
   the before side; the four transport/declaration zero cases move.
6. The `ask` leg is witnessed once interactively by the operator (a real prompt on a live verb
   from a `homelab-platform` session) and the witness is recorded in the decision record.

## Measurement conditions

Model `sonnet`; `--clean-room`; `--runs 5`; timeout 600; concurrency 3; CLI version recorded from
the run; the revision under test recorded as bytes (`git rev-parse HEAD:agents/homelab-platform.md`).
One writer per checkout: the before side runs in a worktree at `305ac1a` that nothing edits; the
after side runs on the frozen branch head.

## Rollback

Revert the branch's commits in reverse order. The hook entry, gate script, and its tests leave
together; `packet_lint.py`'s `EFFECT_CLASSES` and the contracts' `Effect class` keys return
together with the agent's five-class list (the vocabulary drift test binds them). Web tools return
to the frontmatter with the adapters regenerated. No on-disk record migrates: declaration values
are evaluation-time output, and historical transcripts stay immutable evidence.

## Round exit

The round closes when acceptance 1–6 are committed and the roadmap item GATE-006 leaves the
tracker with an outcome record under `docs/archive/2026-08/`, or when the paired lane shows a
hard regression and the decision record's reopen section records why.
