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

| Document | State | Read it for |
|---|---|---|
| [`sre-agents-adaptation-backlog.md`](sre-agents-adaptation-backlog.md) | Historical import adjudication | Donor decisions and dated execution evidence; not current status |
| [`decisions/2026-07-28-fleet-role-expansion.md`](decisions/2026-07-28-fleet-role-expansion.md) | Accepted in part | ROLE-001 and ROLE-002 accepted; ROLE-003 remains parked trigger-bound |
| [`skills-modernization-plan.md`](skills-modernization-plan.md) | Partly superseded snapshot | Original portfolio rationale; not current status |
| [`archive/2026-07/fleet-quality-review.md`](archive/2026-07/fleet-quality-review.md) | Historical quality archive | Combined initial and deep reviews, security evidence, finding dispositions, and lessons |
| [`archive/2026-07/ecc-import-review.md`](archive/2026-07/ecc-import-review.md) | Historical donor adjudication | Combined ECC comparison, component verdicts, accepted residue, and resolution ledger |
| [`archive/2026-07/roster-expansion-design.md`](archive/2026-07/roster-expansion-design.md) | Historical roster design | Earlier component contracts and constraints, reconciled into the current decision and roadmap |
| [`superpowers/specs/2026-07-27-fleet-expansion-round1-design.md`](superpowers/specs/2026-07-27-fleet-expansion-round1-design.md) | Active approved specification | Round 1 scope, non-goals, and gates |
| [`superpowers/plans/2026-07-27-fleet-expansion-round1.md`](superpowers/plans/2026-07-27-fleet-expansion-round1.md) | Active execution plan | Round 1 task sequence and exact proposed payloads |

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
6. Agent and skill definitions remain canonical in `agents/` and `skills/`; documentation never
   overrides the files Claude Code loads.
