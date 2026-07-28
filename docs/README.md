# Documentation map

This directory separates current work, durable decisions, active execution plans, and historical
evidence. Mixing those roles is how a landed item becomes an apparently open task, or a dated
review silently starts governing the current fleet.

## Authority

| Document class | Purpose | Authority |
|---|---|---|
| [`fleet-roadmap.md`](fleet-roadmap.md) | Current, deferred, and blocked fleet work | Becomes the live status owner after the consolidation reconciliation is committed |
| `decisions/` | Accepted architecture decisions, rejected alternatives, and reopen triggers | Governs the decision it records until explicitly superseded |
| `superpowers/specs/` | Approved scope and acceptance boundaries for an active round | Governs what its paired plan is allowed to implement |
| `superpowers/plans/` | Branch-specific execution instructions and exact payloads | Operational only while that round is active |
| `archive/` | Dated reviews, donor adjudication, and completed-plan evidence | Historical evidence only; never a task list |

During the consolidation in progress, `sre-agents-adaptation-backlog.md` remains the live status
owner until its genuinely open work has been reconciled into `fleet-roadmap.md`. The commit that
completes that import must update this sentence and the repository guide together.

## Current documents

| Document | State | Read it for |
|---|---|---|
| [`sre-agents-adaptation-backlog.md`](sre-agents-adaptation-backlog.md) | Transitional live backlog | Current import work and its detailed donor adjudication |
| [`fleet-role-gap-review-2026-07-28.md`](fleet-role-gap-review-2026-07-28.md) | Recommendation snapshot | QA, security, Linux, SRE, and homelab-role conclusions pending conversion to a decision record |
| [`skills-modernization-plan.md`](skills-modernization-plan.md) | Partly superseded snapshot | Original portfolio rationale; not current status |
| [`agents-skills-quality-review.md`](agents-skills-quality-review.md) | Historical snapshot | Initial fleet-quality findings and reasoning |
| [`deep-review-2026-07-24.md`](deep-review-2026-07-24.md) | Historical follow-up | Later findings, runtime probes, and resolution evidence |
| [`ecc-skills-agents-review.md`](ecc-skills-agents-review.md) | Historical donor review | First ECC comparison batch |
| [`ecc-batch2-review.md`](ecc-batch2-review.md) | Historical donor review | Second ECC comparison batch |
| [`superpowers/specs/2026-07-27-fleet-expansion-round1-design.md`](superpowers/specs/2026-07-27-fleet-expansion-round1-design.md) | Active approved specification | Round 1 scope, non-goals, and gates |
| [`superpowers/plans/2026-07-27-fleet-expansion-round1.md`](superpowers/plans/2026-07-27-fleet-expansion-round1.md) | Active execution plan | Round 1 task sequence and exact proposed payloads |

## Rules

1. A historical review may explain why a decision was made; it never proves that work is still
   open.
2. The roadmap names current work. A source review or decision record owns the detailed rationale.
3. A decision record states what was chosen, what lost, and what evidence should reopen it. It
   does not become an execution checklist.
4. An active plan may be detailed and branch-specific. Once complete, its lasting decisions and
   evidence move to a short outcome record; Git history retains the exact execution payload.
5. When a file moves or is consolidated, update every tracked reference in the same commit.
6. Agent and skill definitions remain canonical in `agents/` and `skills/`; documentation never
   overrides the files Claude Code loads.

