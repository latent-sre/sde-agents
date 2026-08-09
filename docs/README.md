# Documentation map

This directory separates current work, durable decisions, active execution plans, and historical
evidence. Mixing those roles is how a landed item becomes an apparently open task, or a dated
review silently starts governing the current fleet.

## Authority

| Document class | Purpose | Authority |
|---|---|---|
| [`fleet-roadmap.md`](fleet-roadmap.md) | Current, deferred, and blocked fleet work | The only live status owner |
| `decisions/` | Proposed or accepted architecture decisions, rejected alternatives, and reopen triggers | An accepted record governs its decision; a proposed record carries no implementation authority |
| `superpowers/specs/` | Approved scope and acceptance boundaries for an active round | Governs what its paired plan is allowed to implement |
| `superpowers/plans/` | Branch-specific execution instructions and exact payloads | Operational only while that round is active |
| `archive/` | Dated reviews, donor adjudication, and completed-plan evidence | Historical evidence only; never a task list |

The roadmap became authoritative after the 2026-07-28 current-tree reconciliation. Historical
files may retain dated “open” sections as evidence of what was believed then; those sections do
not re-enter the queue unless the roadmap imports them.

## Current documents

The roadmap, decision records, and any active-round spec/plan listed below are live. Everything
else here is historical evidence.

| Document | State | Read it for |
|---|---|---|
| [`fleet-roadmap.md`](fleet-roadmap.md) | Live | Every unfinished, blocked, deferred, and decision-needed item. Nothing else adds work |
| [`archive/2026-08/tier-001-outcome-2026-08-08.md`](archive/2026-08/tier-001-outcome-2026-08-08.md) | Historical outcome record | What TIER-001 landed (PRs #89/#90): the adapter-check tier split, the offline baseline resolver, the T0–T3 recipe, the proportionality rule, the missed ~60s target and its root cause, and the profiler-fraction lesson |
| [`archive/2026-08/safe-002-outcome-2026-08-04.md`](archive/2026-08/safe-002-outcome-2026-08-04.md) | Historical outcome record | What SAFE-002 landed: the broker's `unknown` state and key-gated reconciliation, the deadline-vs-pid staleness decision, the verification chain, and the duplicate-PR (#82) comparison |
| [`archive/2026-08/learn-001-outcome-2026-08-02.md`](archive/2026-08/learn-001-outcome-2026-08-02.md) | Historical outcome record | What LEARN-001 landed (PR #57): the learning lifecycle, ledger, packet closeouts, eval provenance v3, the measured regression and its fix, corrections, and the routed lessons |
| [`decisions/2026-07-31-ai-graph-engineering.md`](decisions/2026-07-31-ai-graph-engineering.md) | Accepted | The graph boundary: descriptive layer, SAFE-002, CTX-001, and the WF-001 pilot accepted; graph execution trigger-bound. Accepted 2026-08-01, amended with the WF-001 probe evidence, and extended with the absorbed sibling-record contributions per the GRAPH-003 ruling |
| [`decisions/2026-07-28-fleet-role-expansion.md`](decisions/2026-07-28-fleet-role-expansion.md) | Accepted in part | ROLE-001, ROLE-002, and LABSEC-001 accepted and implemented; ROLE-003 parked trigger-bound |
| [`decisions/2026-07-29-deployment-mode.md`](decisions/2026-07-29-deployment-mode.md) | Accepted | Option A governs daily Claude use: installed, namespaced plugin mode with no active fleet junctions; includes normal-session guard evidence and rollback |
| [`decisions/2026-07-30-multi-platform-packaging.md`](decisions/2026-07-30-multi-platform-packaging.md) | Accepted | Canonical-source ownership, generated host adapters, per-host authority controls, and Codex's separate custom-agent sync |
| [`decisions/2026-08-01-graph-control-plane.md`](decisions/2026-08-01-graph-control-plane.md) | Superseded (absorbed) | The second, independently authored GRAPH-001 proposal. The operator's GRAPH-003 ruling (2026-08-01) let the sibling record's acceptance stand and absorbed this record's distinct contributions: SAFE-003, GRAPH-004, the ledger-by-construction argument, and the generated-prompt provenance control |
| [`archive/2026-08/wf-001-outcome-2026-08-01.md`](archive/2026-08/wf-001-outcome-2026-08-01.md) | Historical outcome record | What WF-001 landed (PR #55): the deep-review workflow, validator rules, probe coverage, pilot economics, corrections, and process lessons |
| [`archive/2026-08/graph-003-adjudication-2026-08-01.md`](archive/2026-08/graph-003-adjudication-2026-08-01.md) | Historical decision evidence | The rival-record verification (every local claim held; one citation downgraded) and the operator's Absorb ruling with its rationale |
| [`archive/2026-08/wf-001-pilot-run-2026-08.md`](archive/2026-08/wf-001-pilot-run-2026-08.md) | Historical outcome evidence | The pilot acceptance run: conditions, measurements ($3.96 / 675 s / zero schema retries), and the three findings its correct do-not-merge verdict produced |
| [`archive/2026-08/wf-001-adversarial-review-2026-08-01.md`](archive/2026-08/wf-001-adversarial-review-2026-08-01.md) | Historical review evidence | The Codex adversarial review of the WF-001 round docs: four findings, per-finding verification, and the dispositions the same-day amendments applied |
| [`archive/2026-07/graph-decision-independent-review-2026-07-31.md`](archive/2026-07/graph-decision-independent-review-2026-07-31.md) | Historical review evidence | The cross-model review of the initial graph proposal: per-claim verification results, the misattribution and counterevidence findings, and what the same-day revision changed |
| [`archive/2026-07/p0-p1-safety-controls-outcomes-2026-07-31.md`](archive/2026-07/p0-p1-safety-controls-outcomes-2026-07-31.md) | Historical outcome record | SAFE-001's eight landed controls, exact verification and model baselines, current installation warnings, and residual trust assumptions |
| [`archive/2026-07/fleet-program-outcomes-2026-07-29.md`](archive/2026-07/fleet-program-outcomes-2026-07-29.md) | Historical outcome record | What Round 1 and the role-expansion program landed, what was measured, and the lessons — including the DEF-001 defect analysis |
| [`archive/2026-07/verification-round-outcomes-2026-07-29.md`](archive/2026-07/verification-round-outcomes-2026-07-29.md) | Historical outcome record | What the verification round landed (PRs #43–#45): the implemented ROLE-003 contract, the measured registration surface and its refuted contamination hypothesis, and the exercised porting method |
| [`archive/2026-07/external-donor-graft-outcomes-2026-07-30.md`](archive/2026-07/external-donor-graft-outcomes-2026-07-30.md) | Historical outcome record | What the external-donor graft round landed (the twelve grafts), the before/after routing measurement and its suppressed positive side, and the lessons |
| [`archive/2026-07/external-donor-import-notes.md`](archive/2026-07/external-donor-import-notes.md) | Historical import adjudication | The 2026-07-30 donor menu: lineage findings, per-source verdicts, rejects with reasons, contribute-back candidates |
| [`archive/2026-07/systematic-debugging-import-notes.md`](archive/2026-07/systematic-debugging-import-notes.md) | Historical import adjudication | The PORT-001 adaptation notes: three frozen donor passes, what grafted into `root-cause` and what was rejected, contribute-back candidates |
| [`archive/2026-07/sde-fullstack-agent-audit-2026-07-30.md`](archive/2026-07/sde-fullstack-agent-audit-2026-07-30.md) | Historical review evidence | Current-commit audit of the builder, its preloaded craft chain, references, hooks, and behavioral proof, plus branch-authorized Go, Python, React, and Vue reference expansions; candidate findings are not live work until the roadmap imports them |
| [`archive/2026-07/sre-agents-adaptation-backlog.md`](archive/2026-07/sre-agents-adaptation-backlog.md) | Historical import adjudication | Donor decisions and dated execution evidence; not current status |
| [`archive/2026-07/skills-modernization-plan.md`](archive/2026-07/skills-modernization-plan.md) | Partly superseded snapshot | Original portfolio rationale; not current status |
| [`archive/2026-07/fleet-quality-review.md`](archive/2026-07/fleet-quality-review.md) | Historical quality archive | Combined initial and deep reviews, security evidence, finding dispositions, and lessons |
| [`archive/2026-07/ecc-import-review.md`](archive/2026-07/ecc-import-review.md) | Historical donor adjudication | Combined ECC comparison, component verdicts, accepted residue, and resolution ledger |
| [`archive/2026-07/roster-expansion-design.md`](archive/2026-07/roster-expansion-design.md) | Historical roster design | Earlier component contracts and constraints, reconciled into the current decision and roadmap |

`superpowers/specs/` and `superpowers/plans/` are empty when no round is active. SAFE-001 retired to
its outcome record under rule 4 — a plan file lying around after its round is how a finished task
keeps reading as pending work.

## Rules

1. A historical review may explain why a decision was made; it never proves that work is still
   open.
2. The roadmap names current work. A source review or decision record owns the detailed rationale.
3. A decision record states its status, what is proposed or chosen, what lost, and what evidence
   should reopen it. Only an accepted record governs implementation; it never becomes an execution
   checklist.
4. An active plan may be detailed and branch-specific. Once complete, its lasting decisions and
   evidence move to a short outcome record; Git history retains the exact execution payload.
5. When a file moves or is consolidated, update every tracked reference in the same commit.
6. Agent and skill definitions remain canonical in `agents/` and `skills/`; documentation and
   generated host adapters never override them.
7. GitHub issues are evidence-bound intake, never a second work tracker. An issue adds work only
   when the roadmap imports it (the roadmap entry names the source issue); an issue that is not
   imported is field evidence awaiting triage, and letting the two lists drift is how the same
   work gets tracked twice or dropped once.
