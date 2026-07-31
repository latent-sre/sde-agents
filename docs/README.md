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

The roadmap and decision records are live. Everything else here is historical evidence.

| Document | State | Read it for |
|---|---|---|
| [`fleet-roadmap.md`](fleet-roadmap.md) | Live | Every unfinished, blocked, deferred, and decision-needed item. Nothing else adds work |
| [`decisions/2026-07-28-fleet-role-expansion.md`](decisions/2026-07-28-fleet-role-expansion.md) | Accepted in part | ROLE-001, ROLE-002, and LABSEC-001 accepted and implemented; ROLE-003 parked trigger-bound |
| [`decisions/2026-07-29-deployment-mode.md`](decisions/2026-07-29-deployment-mode.md) | Proposed, parked | The junctions-vs-plugin trade table and its reopen triggers; DEPLOY-001 is undecided by choice |
| [`decisions/2026-07-30-multi-platform-packaging.md`](decisions/2026-07-30-multi-platform-packaging.md) | Accepted | Canonical-source ownership, generated host adapters, per-host authority controls, and Codex's separate custom-agent sync |
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
