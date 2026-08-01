# LEARN-001 — the fleet learning loop (spec)

> **Status: active round.** Approved scope and acceptance boundaries for LEARN-001. Governs what
> the paired plan (`../plans/2026-08-01-learn-001-learning-loop.md`) is allowed to implement.
> Retires to an outcome record under `docs/archive/` when the round closes.

## Source and authority

- Operator commission 2026-08-01: a consistent, ongoing improvement-and-learning loop for the
  fleet — discovery routing ("if it discovered something new it should know what to do with
  that"), runbook/doc self-healing, retros that also look for what the loop itself misses —
  grounded in current public research.
- Research evidence: the LEARN-001 research report (artifact
  `claude.ai/code/artifact/82a338a5-15ed-4b2e-a07b-674f7c53ce75`, compiled 2026-08-01 from four
  primary-source lanes: Anthropic, OpenAI/Google/Microsoft, academic, practitioner). Key anchors:
  Anthropic's build-over-time trigger table and Dreaming's separate-output retro shape; ACE's
  measured context collapse (delta updates only); the 2026 write-time-gating wave (SAGE, MemGuard,
  SSGM); "abstraction dictates transferability"; AEVAL's deterministic-check discipline; every
  lane's human-on-the-approval-path finding.
- Donor pattern: `sre-agents` `skills/operational-learning/` (event→artifact map, explicit
  dispositions, recurrence fingerprint). Concepts adapted, text original, packet machinery
  deliberately rejected — home-lab scale does not need schema-validated closeout packets.
- Operator fork rulings (2026-08-01, recorded verbatim in intent):
  1. **Home:** graft into `self-improve-loop` + two on-demand references. No new skill.
  2. **Cadence:** trigger-bound only. No hook, no cron. Reopen trigger recorded below.
  3. **Memory hygiene:** procedure lives in the retro reference; a one-line global-CLAUDE.md
     pointer is *proposed to the operator separately*, never applied by this round.
  4. **Execution:** full round now; **routing evals must not run on a Fable-tier model** — both
     sides of every comparison pin `--model sonnet`.

## Scope — what this round implements

1. `skills/self-improve-loop/SKILL.md` — description gains retro trigger phrases, discovery
   routing, and negative routing to `sde-agents:postmortem` for incident retros; body gains a
   "Retros beyond the micro-retro" section (trigger set + encode-one-file-many rule) and pointers
   to the two new references. Micro-retro semantics unchanged.
2. `skills/self-improve-loop/references/discovery-routing.md` *(new)* — the discovery→destination
   table with thresholds, the disposition rule, and the write-gate rules.
3. `skills/self-improve-loop/references/retro-protocol.md` *(new)* — session retro, round retro,
   meta-retro, model/CLI-upgrade retro, and the memory-consolidation procedure.
4. `skills/runbook/SKILL.md` — the found-wrong duty rule (fix small-and-in-scope in the same
   change, else file the gap and name it in the packet; never silently work around).
5. `agents/homelab-platform.md` — one Standards bullet carrying the same duty for operating docs,
   inside existing tier semantics (doc edits are Tier 1).
6. `agents/researcher.md` — one deterministic-reads sentence in Method §3. Trigger fired
   2026-08-01: three fetch-layer fabrications in one research round matched the recurrence
   fingerprint recorded in the operator memory `deterministic-reads-over-webfetch`.
7. `AGENTS.md` — one line in "Change playbooks" pointing at the routing reference.
8. `evals/routing/retro-boundary.json` *(new cluster)* — members `self-improve-loop`,
   `postmortem`; positives for both members (including one pre-existing-remit positive to catch
   regression), vocabulary-collision negatives, and a live-outage negative. Before/after captures
   under `evals/baselines/2026-08-01-learn-001/{before,after}/`.
9. Round docs: this spec, the paired plan, a roadmap item, regenerated host adapters, refreshed
   README inventory.

## Design rules the payloads must honor

- **Capture only on an observed event, never speculatively.** No lesson without a trigger.
- **Thresholds before promotion**: twice for rules and deterministic checks (once for a material
  safety/authority failure), once for verified facts and runbook procedures, third occurrence for
  a new skill. Anchored to Anthropic's build-over-time table, the promote-after-twice practitioner
  rule, and the donor fingerprint ("repeats" = same normalized failure, not two vaguely similar
  complaints).
- **Silence is not a disposition**: at close of a qualifying task, each discovery is routed, filed
  as a gap, or dropped with a stated reason.
- **No self-approval**: durable-store changes ride PRs and operator review; memory writes carry
  date + evidence label; nothing fetched or generated approves its own promotion.
- **Delta edits only**: consolidation merges, dedupes, retires item-by-item
  (`CREATED/UPDATED/DELETED` vocabulary); never a full-store rewrite.
- **Encode one, file many**: a retro encodes at most one lesson (existing law); further findings
  become roadmap/gap entries, not edits.
- **Advisory vs enforced stays intact**: recurring failures move left into deterministic checks;
  prose never substitutes for a control.

## Measurement conditions (both sides identical, or the diff is void)

`--model sonnet --timeout 420 --runs 3`, no `--clean-room`, `--output-dir` as above. Rationale:
operator constraint (no Fable-tier evals); non-clean-room matches the conditions under which
sharp-trigger skill positives are known to fire (EVAL-003 evidence: clean-room suppressed skill
positives at opus tier; agent positives under-fire headless regardless — but both cluster members
here are skills, so the positive signal is real). `conditions` blocks must record model, timeout,
CLI version, threshold, clean_room.

## Acceptance evidence

- `python3 scripts/generate_platform_adapters.py --check`, `python3 scripts/validate_fleet.py`,
  and `python3 -m unittest discover -s tests` green at the head of the branch.
- Before and after `benchmark.json` pairs with matching recorded conditions; **no negative fires
  at any rate** (an over-trigger is a defect regardless of variance); no positive regression
  beyond run variance; `INCONCLUSIVE` cases re-run, not counted.
- Every new reference linked skill-relative from its SKILL.md (orphan check green).
- README inventory refreshed; roadmap carries LEARN-001 while active; the round retires to an
  outcome record whose lessons section itself works the new routing table (the loop's first
  self-application).

## Deliberately not done, with reopen triggers

- **No hook, no cron, no scheduled sweep.** Reopen when two consecutive rounds each surface a
  lesson that a periodic sweep would have caught earlier than its trigger did.
- **No new skill/agent; no auto-applied lessons; no lab-repo changes** (the runbook duty binds at
  use time in whatever repo the runbook lives in; this round edits only the fleet).
- **No global-CLAUDE.md edit** — a one-line pointer is drafted and presented for separate
  approval.
- **No validator rule changes** — GRAPH-002's sequencing gate is untouched.
- **No donor packet machinery** (schemas, SHA-256 binding, disposition validator). Recorded as a
  contribute-back-shaped divergence, not a gap: the PR-review culture is this repo's equivalent
  control.

## Rollback

Docs-and-definitions branch; no live system is touched. Revert = delete the branch or revert the
merge commit; the eval baselines are additive artifacts and harmless to keep.
