# Role expansion — active plan and the remaining queue (2026-07-29)

> **Authority note:** `docs/fleet-roadmap.md` is the only live tracker; this file is operational
> while the role-expansion round is active and records the full remaining program as of
> 2026-07-29 for orientation. Where this file and the roadmap disagree, the roadmap wins.

## Where the program stands

The 2026-07-29 fresh-look review re-verified the whole ledger and executed four merged PRs:

| PR | What it closed |
|---|---|
| #37 | Round 1 — powershell.md + measured widening, lab-audit split, 2 of 3 contracts |
| #38 | Docs wave — ROLE-001/002 accepted, DEPLOY-001 opened, stale lines fixed |
| #39 | Round 1 gate — EVAL-002 (conditions/usage/model pin/scratch cwd), DEF-001 (ladder fix) |
| #40 | GOV-001 (guard fails closed on malformed input) + EVAL-001 (cluster-target integrity) |

## Active: the role-expansion round (branch `claude/role-expansion`)

Landed so far: Linux-host cases seeded (`7191822`) · before-anchors committed (`0db198b` —
homelab negatives 10/10 clean, host positives 0/3 baseline, investigation negatives 3/3 clean) ·
the edit wave (`d291da1` — SRE rebrand + `host-onboard` + `application-security-auditor` + both
cluster extensions, 9 agents / 18 skills, all gates green).

Remaining steps, in order:

1. **After-batch completes** (running: both clusters' negatives + `pos-host-*` +
   `pos-appsec-*`, opus/420, ~54 sessions, controller-owned with artifact watchdog).
2. **Acceptance diffs.** Hard gates: every negative holds at 0% fire (a rise on any near-miss is
   a widening defect — revisit only the changed description sentence, once, per the three-strikes
   rule); `pos-host-*` at or above their 0/3 baseline (the direct measure of the Linux-host
   widening). Soft signals: `pos-appsec-*` rates read under the agent-under-fire caveat — a low
   rate is recorded, not silently tuned.
3. **Commit after-artifacts** with the diff paragraph in the commit message.
4. **Roadmap closures:** ROLE-001 and ROLE-002 leave the roadmap in the same PR as their
   acceptance evidence.
5. **PR** with the conditional-gates table filled (description edits → before/after artifacts;
   new components → inventory + routing coverage), then operator review and merge.
6. **Memory update** to the closed state.

## The queue after this round

Everything below lives in the roadmap with full contracts; listed here as the complete remaining
program, in recommended order:

- **DEPLOY-001** (operator decision, deliberately deferred to the end of this queue): junctions
  vs installed plugin for daily use. Hard gates unchanged — must be decided before any LABSEC-002
  work and before a second user installs. Decision record:
  `docs/decisions/2026-07-29-deployment-mode.md`.
- **LABSEC-001** (operator decision, now decidable): whether an adversary-focused `security-audit`
  skill should exist for the *running lab*, distinct from `lab-audit` hygiene and from the new
  repository auditor. Its prerequisite (the lab-audit checks split) landed in PR #37 — the next
  step is comparing the archived proposal against `skills/lab-audit/references/checks.md`.
- **LABSEC-002** (blocked): guard-enforced lab inspector — needs LABSEC-001 accepted *and*
  DEPLOY-001 decided (a guard-enforced agent must not ship into a deployment where the guard
  never runs). GOV-001 is already landed.
- **ROLE-003 / ROLE-004** (parked trigger-bound): verification execution authority, then the
  independent verification engineer. Reopens on the first real verification task.
- **EVAL-003** (deferred): one comparable full routing anchor. The measurement path is proven
  healthy now; before anchoring, settle the layer-skill zero-fire question the Round 1 diagnose
  run surfaced (backend-craft/frontend-craft/sde-fullstack positives at 0/21 with sharp-trigger
  skill positives at 6/6 — case design vs description strength, deliberately unresolved).
- **PORT-001** (trigger: next donor import): codify the cross-fleet import method before the next
  mining round (the `superpowers:systematic-debugging` → `root-cause` round tops that menu).
- **RELEASE-001** (trigger: next release task): plugin version/changelog/tag discipline — also the
  standing reason no PR bumps `plugin.json` ad hoc.
- **EVAL-004** (trigger: next real UI task): behavioral verification of the accessibility imports.
- **LAB-001** (trigger: next onboarding in a lab with no compose pattern): the fallback service
  compose asset.

Standing manual duties that never leave: re-run `scripts/probe_plugin.py` when the CI CLI pin
bumps or the guard/hook change; any description edit owes its cluster's before/after; behavioral
and routing suites stay manual-and-on-demand, never CI gates.

## End state when the queue drains

A 9-agent / 18-skill fleet whose guard is armed in the deployment mode the operator actually
uses (DEPLOY-001), whose lab has both hygiene and (if accepted) adversary security coverage,
whose measurements always state their conditions, and whose only open work arrives with its
trigger — a release, an import, a UI task, a verification ask — rather than sitting in a queue.
