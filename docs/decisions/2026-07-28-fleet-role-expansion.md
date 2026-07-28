# Fleet role expansion and home-lab SRE identity

**Status:** Proposed — awaiting operator acceptance, revision, or rejection  
**Date:** 2026-07-28  
**Reviewed revision:** `be2af4c87a3ecd53286fbcda84863d507ee47ac4`  
**Implementation status:** No role, skill, guard, or routing change has been authorized by this
record. Current work and gates live in [`fleet-roadmap.md`](../fleet-roadmap.md).

## Decision question

Does the fleet need dedicated QA, Linux, SRE, and security agents, and should
`homelab-platform` be renamed or rebranded as an SRE role?

## Proposed decision

| Capability | Proposal |
|---|---|
| Independent QA | Add `verification-engineer` only after a test-execution authority model is accepted |
| Linux operations | Do not add an agent; add action-shaped host lifecycle coverage |
| General SRE | Do not add an agent; the existing home-lab operator already owns that outcome |
| Application security | Add `application-security-auditor` with a static-first, non-PR remit |
| Home-lab identity | Present the role as **Home-Lab SRE / Platform Engineer** while keeping the `homelab-platform` key |

The resulting shape is two narrowly bounded agents, one Linux-host skill, and one visible rebrand
— not four new agents.

## How the proposal was reached

Three read-only reviewers received non-overlapping surfaces and no access to `docs/`, `README.md`,
repository history, or earlier review conclusions:

1. Agent topology: `agents/*.md` and the plugin manifest.
2. Skill topology: `skills/**`, including linked references and assets.
3. Governance and evidence: `scripts/`, `hooks/`, `tests/`, `evals/`, CI, and plugin wiring.

Their conclusions were frozen before comparison with the historical documents. The later document
comparison affected naming, sequencing, and safeguards; it did not choose the gaps.

## Context

### Independent verification is not currently owned

[`sde-fullstack`](../../agents/sde-fullstack.md) implements and verifies its own work.
[`code-reviewer`](../../agents/code-reviewer.md) independently reviews a diff but deliberately
cannot run repository tests or scripts. No role independently reproduces behavior, exercises the
actual runtime, compares it with acceptance criteria, and returns a release-readiness verdict.

### Whole-repository application security is not currently owned

`code-reviewer` has a strong security pass, but its public remit is a PR, commit, branch, or diff.
`researcher` can investigate external advisories and vendor evidence. Neither owns a repository or
subsystem threat model, source-to-sink audit, attack-path validation, or severity calibration.

### The home-lab operator already performs SRE work

[`homelab-platform`](../../agents/homelab-platform.md) owns VMs, containers, networking, storage,
monitoring, backups, change classification, rollback, access preservation, and operating
documentation. The operating skills form a service lifecycle: onboarding, observability, audits,
incidents, runbooks, postmortems, restore drills, and upgrade campaigns.

Linux is the substrate of that outcome. A generic Linux agent would overlap the authority owner
while routing on a technology name rather than a user outcome.

## Role contract: `application-security-auditor`

### Owns

- repository- or subsystem-wide application-security audits;
- threat models, trust boundaries, assets, actors, and entry points;
- source-to-sink and attack-path analysis;
- validation and severity calibration of suspected findings; and
- source-backed reports without implementing remediation.

### Does not own

- PR, commit, or branch review — `code-reviewer`;
- external CVE/vendor research alone — `researcher`;
- remediation implementation — `sde-fullstack`;
- home-lab exposure and operational hardening — `homelab-platform` / `lab-audit`; or
- multi-system security architecture — `principal-engineer`.

### Initial authority

Start with `Read, Grep, Glob, WebSearch, WebFetch`. Static source analysis and authoritative
external evidence do not require Bash. Add history or execution authority only after a
demonstrated need and after the malformed-input guard defect is fixed.

### Required output

- scope and threat model;
- assets, actors, entry points, and trust boundaries;
- candidate attack paths;
- validated findings with source-to-sink evidence;
- exploit preconditions, impact, severity, and confidence;
- remediation direction; and
- rejected candidates and residual unknowns.

The proposed name deliberately uses **auditor**, not `security-reviewer`, because “reviewer” would
collide with the fleet's most routing-sensitive existing role.

## Role contract: `verification-engineer`

### Owns

- independently reproducing reported behavior;
- executing acceptance, regression, and failure-path checks;
- exercising runtime integration;
- comparing observed behavior with explicit acceptance criteria; and
- returning traceable evidence and a pass/fail/inconclusive release verdict.

### Does not own

- implementing the feature or fix — `sde-fullstack`;
- static PR/diff review — `code-reviewer`;
- diagnosing an unknown failure — `root-cause`;
- changing live home-lab infrastructure — `homelab-platform`; or
- inventing a cross-component test architecture — `principal-engineer` when that design is
  material or hard to reverse.

### Authority prerequisite

The current policy treats Bash plus no write tools as a read-only agent, while the read-only guard
deliberately rejects Python, pytest, npm, make, and other test runners. Granting Write merely to
escape that classification would make the definition look safer without creating a real boundary.

Before authoring this agent, decide:

- whether it may create or edit tests;
- whether product-code edits are always prohibited;
- how `isolation: worktree` is used;
- how network, database, container, and external-system effects are gated;
- which integration or live-environment checks require approval; and
- which limits are enforced versus cooperative.

Claude Code documents custom subagents as separate contexts with selectable tools:
<https://code.claude.com/docs/en/sub-agents>. It documents `isolation: worktree` as temporary
file-change isolation: <https://code.claude.com/docs/en/worktrees>. A worktree is not a sandbox for
external effects.

### Required output

- target, environment, and exact revision;
- acceptance criteria;
- tests and checks executed;
- expected versus observed behavior;
- failure-path coverage;
- evidence and reproducible commands;
- pass/fail/inconclusive verdict; and
- skipped checks and remaining risk.

## Home-lab SRE identity and Linux boundary

Keep the stable component key:

```yaml
name: homelab-platform
```

Proposed visible heading:

```markdown
# Home-Lab SRE / Platform Engineer
```

Proposed description opener:

> Home-lab site reliability and platform operations for Linux hosts, VMs, container stacks,
> networking, storage, observability, backups, and self-hosted services.

Add trigger vocabulary for systemd and services, packages and patching, users/permissions/SSH,
disks/filesystems/mounts, host networking/firewalls, and host telemetry.

The first Linux addition should be explicit-only `host-onboard`, covering:

- OS and patch baseline;
- users, groups, sudo, SSH, and access recovery;
- package sources and update policy;
- host firewall and management exposure;
- systemd health and restart policy;
- disks, filesystems, mounts, and capacity;
- time synchronization and DNS;
- metrics/log enrollment;
- backup enrollment and restore ownership; and
- configuration tracking, validation, and rollback.

Because onboarding changes a live host, `host-onboard` should set
`disable-model-invocation: true`; `homelab-platform` retains the change authority.

## Governance prerequisites discovered during the review

### Malformed guarded input returns ALLOW

[`readonly-guard.py`](../../scripts/readonly-guard.py) catches JSON decoding failure and returns
the exit-42 allow sentinel. [`hooks.json`](../../hooks/hooks.json) treats 42 as authoritative and
exits before the raw guarded-agent fallback.

Reproduction:

| Input | Result |
|---|---|
| Valid guarded payload with a state-changing Git command | Denied, exit 43 |
| Same guarded payload truncated into malformed JSON | Allowed, exit 42 |
| Malformed unscoped payload | Allowed, exit 42 |

Fix before adding another guarded or execution-capable role. The roadmap owns the regression and
acceptance requirements as `GOV-001`.

### A routing case can pass outside its declared cluster

`evals/routing/craft-vs-fullstack.json` accepts `code-reviewer` for
`pos-ci-actions-harden`, although `code-reviewer` is not a declared member. The scorer can therefore
pass the case while reporting zero cluster fire rate. The roadmap owns schema enforcement as
`EVAL-001`.

### Current baselines are not one comparable anchor

Some clusters have no current baseline, membership and case counts have changed, and known-invalid
artifacts lack comparable conditions. Negative near-misses and measured regressions remain the
strongest routing signals. The full re-baseline stays deferred as `EVAL-003` until the active
Round 1 measurement path is healthy.

## Alternatives rejected

### Add a generic Linux agent

Rejected because it duplicates `homelab-platform`'s authority and routes on a substrate. Reopen
only if repeated Linux work has a distinct output and authority boundary that does not belong to
the home-lab operator.

### Add a generic SRE agent

Rejected because the current home-lab hub and operating skills already provide SRE outcomes.
Reopen if the plugin intentionally expands to non-home-lab production operations and can state a
clean “not for home labs” boundary.

### Add a generic QA or test-strategy skill

Rejected because testing method already exists in the craft and implementation skills. It would
not solve the missing independent executable verdict. Extract a reusable verification skill only
after a second consumer demonstrates one.

### Put security into another `reviewer`

Rejected because `code-reviewer` owns diffs and PRs. Whole-system security gets a separate output
and an auditor name; remediation remains with the builder.

### Rename the canonical home-lab key

Rejected because `homelab-platform` is a useful routing discriminator and is referenced throughout
the skills, evals, inventory, and user-facing conventions. Rebrand the presentation without
breaking the component identity.

## Reopen triggers

Revisit this proposal when:

- an operator accepts, revises, or rejects the role boundaries;
- a real verification task demonstrates a safer execution-authority model;
- repeated Linux work falls outside both host onboarding and home-lab operations;
- the plugin expands to enterprise/non-home-lab production systems;
- static security assessment proves insufficient without Git history or execution; or
- routing measurements show the proposed names or boundaries collide.

## Verification at review time

At the reviewed revision:

- fleet validator: 8 agents and 17 skills, inventory current;
- unit suite: 138 passed, 12 POSIX-shell hook tests skipped on Windows;
- strict plugin validation: passed.

No live routing run or role implementation was performed. The skipped hook tests are why the
guard defect is not treated as covered by the otherwise-green Windows suite.

