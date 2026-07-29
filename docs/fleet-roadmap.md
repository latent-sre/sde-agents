# Fleet roadmap

> **Status: live.**
> This is the only document that tracks unfinished, blocked, or explicitly deferred fleet work.
> Reviews, decision records, and execution plans supply rationale and implementation detail; they
> do not independently add work to the queue.

This file will contain only unfinished, blocked, or explicitly deferred work for the current
fleet. Landed implementation history and donor-by-donor adjudication belong in `docs/archive/`;
architecture decisions and rejected alternatives belong in `docs/decisions/`.

## Item contract

Every roadmap item carries:

| Field | Meaning |
|---|---|
| ID | Stable identifier used by plans and decision records |
| Status | `ready`, `active`, `blocked`, `deferred`, or `decision-needed` |
| Outcome | The observable result, not a list of files |
| Source | The decision, review, or specification that established the work |
| Prerequisites | Gates that must land first |
| Acceptance | Evidence required to close the item |
| Next action | The smallest safe step that moves it forward |

An item leaves this file when its acceptance evidence is committed. The source decision remains;
Git history and archived reviews retain the implementation detail.

## Current work

### Active

### Ready

#### ROLE-001 — implement the home-lab SRE rebrand and Linux-host boundary

**Status:** `ready`

**Outcome:** Keep the canonical `homelab-platform` key, present it visibly as Home-Lab SRE /
Platform Engineer, add Linux-host trigger vocabulary, and add `host-onboard` as the first
explicit-only host lifecycle skill.

**Source:** [`fleet role-expansion decision`](decisions/2026-07-28-fleet-role-expansion.md),
accepted as proposed 2026-07-29 (see its acceptance record).

**Prerequisites:** Approval obtained 2026-07-29. The description edit owes a before/after
`homelab-ops` routing run.

**Acceptance:** Visible title/description and `host-onboard` land with inventory and routing
coverage; existing service/application near-misses remain clean in the before/after diff.

**Next action:** Implement the rebrand + `host-onboard` per the decision record's contract, with
the owed `homelab-ops` before/after run.

#### ROLE-002 — add the application-security auditor

**Status:** `ready`

**Outcome:** Add a static-first agent for repository/subsystem audits, threat models, attack paths,
and finding validation without taking PR review or remediation authority.

**Source:** [`fleet role-expansion decision`](decisions/2026-07-28-fleet-role-expansion.md),
accepted as proposed 2026-07-29 (see its acceptance record).

**Prerequisites:** Approval obtained 2026-07-29; EVAL-001 and GOV-001 both landed in PR #40 (the
routing-schema integrity the auditor's new cluster will be validated under, and the guard
fail-closed fix that would matter if the agent is ever given guarded Bash — the accepted initial
tools, `Read, Grep, Glob, WebSearch, WebFetch`, avoid it).

**Acceptance:** Agent has explicit static tools, no implementation authority, a source-backed
output contract, and negative routing against `code-reviewer`, `researcher`, `homelab-platform`,
and `sde-fullstack`; a routing cluster covers the auditor/reviewer/researcher seam.

**Next action:** Land EVAL-001, then author the agent per the decision record's role contract and
seed its routing cases.

## Deferred decisions

#### DEPLOY-001 — decide the fleet's daily deployment mode

**Status:** `deferred` — the operator confirmed 2026-07-29 this is the plugin-vs-junctions
deployment choice and deferred it to the end of the current implementation queue: decide after
GOV-001, EVAL-001, ROLE-001, and ROLE-002 land. The hard gates are unchanged — it must still be
decided before any LABSEC-002 work and before a second user installs the plugin.

**Outcome:** The fleet's daily-use deployment matches what its guard, namespacing, and eval
conditions assume — or the divergence is recorded and accepted in a governing decision record.

**Source:** Proposed [`deployment-mode decision`](decisions/2026-07-29-deployment-mode.md).
Verified 2026-07-29: `~/.claude/{skills,agents}` are junctions into this repo and `sde-agents` is
absent from the installed plugins, so components register bare and the read-only guard is dormant
in every normal session.

**Prerequisites:** Operator choice; parked deliberately on 2026-07-29.

**Acceptance:** The decision record is accepted. If plugin-install is chosen: junctions dropped,
install verified, and a reproducible normal-session (non `--plugin-dir`) check proves namespaced
registration plus guarded-command denial. If junctions are kept: the README/AGENTS honest-posture
note lands and LABSEC-002's value is re-adjudicated.

**Next action:** Reopen after the current Ready queue lands; the operator then reviews the
decision record's trade table and picks a mode.

#### ROLE-003 — define verification execution authority

**Status:** `deferred` — parked trigger-bound by the operator on 2026-07-29: reopen on the first
real independent-verification task; choose the authority model then. ROLE-004 stays blocked
behind it.

**Outcome:** Decide how an independent verifier may execute repository tests without pretending
that test runners are read-only or that a worktree contains network/database side effects.

**Source:** Proposed
[`fleet role-expansion decision`](decisions/2026-07-28-fleet-role-expansion.md).

**Prerequisites:** GOV-001 and operator choice on test-file edits, worktree isolation, integration
tests, external effects, and live-environment approval.

**Acceptance:** A written authority contract names allowed product/test edits, worktree behavior,
external-effect gates, and enforcement limits; governance tests pin any new roster or exception.

**Next action:** Choose the authority model before authoring the agent.

#### ROLE-004 — add an independent verification engineer

**Status:** `blocked`

**Outcome:** Add an agent that independently reproduces and executes acceptance/regression
evidence without implementing the product fix.

**Source:** Proposed
[`fleet role-expansion decision`](decisions/2026-07-28-fleet-role-expansion.md).

**Prerequisites:** ROLE-003 accepted, GOV-001 landed, and EVAL-001 landed.

**Acceptance:** Agent and routing cases separate verification from implementation, diagnosis,
static review, and live operations; behavioral tests prove unrun checks cannot be called passed and
evidence belongs to the exact tested revision/environment.

**Next action:** None until ROLE-003 is accepted.

#### LABSEC-001 — decide adversary-focused running-lab security coverage

**Status:** `decision-needed`

**Outcome:** Decide whether an intent-driven `security-audit` skill should own trust zones,
exposed services, authentication, management planes, secrets posture, vulnerability prioritization,
and personal-data paths in the running lab without taking hygiene or fix authority.

**Source:** Reconciled
[`fleet role-expansion decision`](decisions/2026-07-28-fleet-role-expansion.md) and archived
[`roster expansion design`](archive/2026-07/roster-expansion-design.md).

**Prerequisites:** Operator approval and completion of ROUND1-001's `lab-audit` check split, so the
hygiene/adversary boundary is tested against the final checklist rather than its transitional form.

**Acceptance:** An accepted decision names the checklist boundary, active-compromise stop rule,
fix routing to `homelab-platform`, cooperative tool limits, output contract, and routing cases
against application security and ordinary lab hygiene.

**Next action:** After ROUND1-001, compare the archived checklist proposal with the landed
`lab-audit` reference and accept, narrow, or reject the separate adversary sweep.

#### LABSEC-002 — add a guard-enforced lab inspector

**Status:** `blocked`

**Outcome:** If LABSEC-001 is accepted, add an optional read-only agent that can work the hygiene
or adversary checklist without taking change authority or combining lab secrets with web access.

**Source:** Archived
[`roster expansion design`](archive/2026-07/roster-expansion-design.md), reconciled by the role
decision.

**Prerequisites:** LABSEC-001 accepted; DEPLOY-001 accepted; GOV-001 landed; each proposed lab
reader independently threat-reviewed and regression-tested; hook/guard roster synchronization
retained; EVAL-001 landed.

**Acceptance:** The agent has no write or web tools; every additional allowlisted command is
read-only by tested verb/flag policy; the POSIX plugin probe proves the guard fires for the exact
roster and ignores the main session; routing preserves outage/change authority in
`homelab-platform`.

**Next action:** None until LABSEC-001, DEPLOY-001, and GOV-001 are complete.

#### EVAL-003 — capture a comparable full routing anchor

**Status:** `deferred`

**Outcome:** Establish one current, condition-complete baseline across all routing clusters.

**Source:** Adaptation backlog's parked re-baseline analysis.

**Prerequisites:** ROUND1-001 measurement path is healthy; run small watched foreground batches;
fix case-design defects before treating numbers as description evidence.

**Acceptance:** Every artifact records requested/observed model, timeout, CLI version, threshold,
and per-run evidence; no known-invalid artifact is called an anchor.

**Next action:** Revisit after Round 1's watched smoke run and scoped anchor complete.

#### PORT-001 — codify the cross-fleet import method

**Status:** `deferred`

**Outcome:** Before the next donor-mining round, make the independent review, adaptation-notes,
scrub, provenance, and adapt-don't-copy method invocable without duplicating prompt authoring or
post-landing self-improvement.

**Source:** Archived
[`roster expansion design`](archive/2026-07/roster-expansion-design.md), whose timing question was
accepted in the originating operator session.

**Prerequisites:** A scheduled donor import or mining round. Measure whether a skill description
routes correctly; if it cannot justify its always-visible cost, retain the method as a documented
convention instead.

**Acceptance:** The next import uses three independent passes before donor-doc comparison,
produces adaptation notes as the implementation specification, scrubs donor-only assumptions,
records provenance, and passes fleet validation and relevant routing checks.

**Next action:** Reopen immediately before the next donor import.

#### RELEASE-001 — add repository release discipline

**Status:** `deferred`

**Outcome:** On the next release-workflow task, add a bounded component for version choice,
changelog, tag, publication, and release rollback without absorbing merge verdicts, CI authoring,
or deployment authority.

**Source:** Archived
[`roster expansion design`](archive/2026-07/roster-expansion-design.md).

**Prerequisites:** A real plugin or repository release task demonstrates the consumer. Keep
pipeline implementation with `ci-actions`, merge readiness with `code-reviewer`, and running
service changes with `homelab-platform`.

**Acceptance:** Routing cases distinguish release, CI, deploy, and merge-verdict requests; the
component states rollback boundaries; its first use performs the repository's actual version,
inventory, validation, tag, and publication sequence.

**Next action:** Reopen before the next manually orchestrated release.

#### EVAL-004 — verify the accessibility imports behaviorally

**Status:** `deferred`

**Outcome:** Demonstrate that a real UI task loads and applies form wiring or interaction
accessibility guidance and supplies keyboard-pass evidence.

**Source:** Combined
[`ECC import review`](archive/2026-07/ecc-import-review.md), Batch 1 accessibility residue.

**Prerequisites:** A real task involving a form, modal, drawer, custom widget, toast, or async
status. Do not manufacture a component solely to close this item.

**Acceptance:** Task packet names the applicable reference and provides keyboard/announcement
evidence; two observed misses trigger a dedicated behavioral contract and definition repair.

**Next action:** Evaluate on the next qualifying UI task.

#### LAB-001 — provide a fallback service compose asset

**Status:** `deferred`

**Outcome:** Supply an annotated service block only for a lab that has no established compose
pattern, covering pinned image, restart, health, resource, and storage slots.

**Source:** Skills modernization Tier 2.

**Prerequisites:** An onboarding task demonstrates that the target lab lacks a reusable pattern.
Existing lab conventions always win.

**Acceptance:** Asset is linked skill-relative from `service-onboard`, contains no environment
specific defaults, and the validator's orphan/reference checks pass.

**Next action:** Reopen on the first qualifying service-onboarding task.

## Reconciliation record

Reconciled against commit `ab896b2` on 2026-07-28. The review compared every item that a historical
document still called open, optional, deferred, or not yet landed with the current definitions,
scripts, eval cases, inventory, and active Round 1 branch.

### Quality and deep-review findings

The initial and deep reviews are consolidated in
[`archive/2026-07/fleet-quality-review.md`](archive/2026-07/fleet-quality-review.md).

| Historical claim | Current evidence | Disposition |
|---|---|---|
| `frontend-craft` presents the default React stack as universal | `skills/frontend-craft/SKILL.md` now says an existing repository always wins and labels every core library binding as the default stack | Landed; exclude |
| Claude Code frontmatter facts are duplicated | `skills/prompt-craft/references/claude-code-frontmatter.md` declares itself the single source, and `prompt-engineer` points to it | Landed; exclude |
| Fetched repository/web content is not consistently treated as data | Every applicable agent carries the canonical rule or its declared role adaptation | Landed; exclude |
| `homelab-platform` routes service additions to an unreachable skill | The agent now owns the apply and reads the explicit-only checklist by path | Landed; exclude |
| `lab-audit` has no tool-layer write restriction | It denies Write, Edit, and NotebookEdit and states Bash remains cooperative | Landed; exclude |
| Eval coverage stops at one routing cluster with no behavioral checks | Six routing clusters, the behavioral runner, packet linter, and three deterministic contracts exist | Machinery landed; additional contract coverage survives below |
| Craft references duplicate headings and Mantine doctrine | References now use one H1; `frontend-craft/SKILL.md` owns the conditional Mantine rule and references point to it | Landed; exclude |
| Body cross-reference namespacing is inconsistent | Descriptions are validator-enforced; body text follows the namespaced-when-invocable convention, with bare names reserved for content already in context | No current broken route found; close |
| `sre-tool` keeps multi-component detail in its always-loaded core | `skills/sre-tool/references/multi-component.md` now owns that conditional material | Landed; exclude |
| Descriptions lack capability-led openers | Current agent and skill descriptions lead with capability and then triggers/negative routing | Landed; exclude |
| `multi-agent-architect` and `prompt-engineer` lack worked examples | Both now carry compressed worked examples | Landed; exclude |
| The material-fork rule is repeated across builder and craft skills | The compact copies remain deliberately because each craft skill is directly invocable without the builder in context | Deliberately retained; close |
| Standalone craft invocations have no defined review packet | Both craft skills provide a four-slot fallback | Landed; exclude |
| Evergreen guidance carries version/comparative claims | The cited “newer”, fixed Recharts major, and fixed model-tier wording is gone | Landed; exclude |
| `prompt-engineer` contradicts itself about spawning | It now branches on the Agent tool actually being unavailable | Landed; exclude |
| Design-agent read-only Bash and handoff boundaries are prose-only | Principal and distinguished agents are guard-enforced for Bash, acknowledge the cooperative Write boundary, and report work back to the caller | Landed; exclude |
| `homelab-platform` does not explain how it reaches operating skills | Its body names the checklists and path-loading convention it uses | Landed; exclude |
| `eng-ladder` references do not resolve in an installed plugin | Each rung reference names both the repo path and `${CLAUDE_PLUGIN_ROOT}` path | Landed; exclude |
| Unused frontmatter fields have no deliberate decision | The canonical frontmatter reference records decisions for `when_to_use`, `maxTurns`, `memory`, and related fields | Landed; exclude |
| Deep-review C1: wrapper-stack failures are missing from routing | `multi-agent-architect` now names wrapper, memory-layer, tool-skip, and delivery-corruption triggers | Landed; exclude |
| Deep-review C7: upper-rung Bash is not guarded | Principal and distinguished agents are in the guard roster and describe the enforced boundary | Landed; exclude |

The deep review's final “still open” list named wrapper routing, upper-rung guarding, and
`frontend-craft` stack neutrality. All three are present in the current tree, so that dated list
must not seed new work.

### Modernization and adaptation items

| Historical item | Current evidence | Disposition |
|---|---|---|
| `incident` plus postmortem | Split into `lab-incident` and `postmortem`; both ship | Landed; exclude |
| `restore-drill` and `upgrade-campaign` | Both appear in the generated 17-skill inventory | Landed; exclude despite the backlog's stale “remain open” sentence |
| `security-seed.md` for `sre-tool` | The diff reviewer gained a security lens; the role review now proposes a distinct whole-repository security auditor | Superseded by the application-security decision |
| `host-onboard` | No skill or equivalent host-lifecycle checklist exists | Survives |
| `lab-audit` command reference and findings ledger | Checks remain inline and no reference file exists; active Round 1 Item C owns it | Survives as active Round 1 work |
| `lab-audit` allowed-tool preapprovals | The backlog explicitly rejected the authority expansion because approval friction is useful | Deliberately closed |
| `service-onboard` compose template | No template exists; the original plan limits it to labs with no existing pattern | Survives as deferred, trigger-bound work |
| Prompt-craft eval wiring | The retest step now requires the repository harness before/after | Landed; exclude |
| Runbook worked example | `skills/runbook/references/example.md` exists | Landed; exclude |
| Root-cause intermittence reference | No file exists, but the proposal was explicitly optional and no repeated failure demonstrates a consumer | Close; reopen after an observed probabilistic-debugging miss |
| PowerShell craft reference | No file exists; the operator decided it is needed and active Round 1 Items A/B own it | Survives as active Round 1 work |
| Full routing re-baseline | No comparable current anchor exists; prior attempts are invalid or incomplete | Survives as deferred measurement work |

### ECC residue

The two source reviews are consolidated in
[`archive/2026-07/ecc-import-review.md`](archive/2026-07/ecc-import-review.md).

| Historical item | Current evidence | Disposition |
|---|---|---|
| Packet-lint helper | `scripts/packet_lint.py`, fixtures, and behavioral-runner integration exist | Landed; exclude |
| Behavioral verification of accessibility imports | No behavioral contract covers form wiring, overlays, keyboard flow, or async announcements | Survives, triggered by the next applicable UI task |
| Deterministic behavioral assertions and pinned fixtures | The current suite is deterministic and stores cases as versioned JSON | Landed; exclude |
| Track token cost beside behavioral pass rate | `eval_behavioral.py` does not capture usage or cost conditions | Survives |
| Principal-engineer AI-maintainer clause | Still absent; explicitly optional and adds nuance without an observed failure | Deliberately closed |
| Multi-agent wrapper-stack trigger | Present in the current description | Landed; exclude |
| `article-writing` import | Remains outside the SDE/SRE fleet remit with no routing home | Deliberately closed |

### Role and governance review

The proposed
[`fleet role-expansion decision`](decisions/2026-07-28-fleet-role-expansion.md) preserves the
2026-07-28 review's method, role boundaries, evidence, and reopen triggers. Static inspection and
direct reproduction left these candidates for the live roadmap:

- malformed guarded JSON returns the authoritative allow sentinel;
- one routing positive accepts a component outside its declared cluster;
- rebrand the visible homelab role and add Linux-host triggers without renaming its key;
- add the action-shaped `host-onboard` skill;
- add an application-security auditor with a non-PR remit;
- design test-execution authority, then add an independent verification engineer.

The current-work sections above carry these survivors, the active Round 1 work, the deferred
routing measurement, ECC behavioral residue, and the trigger-bound compose asset.

### Roster-expansion design branch

The detailed source design is preserved at
[`archive/2026-07/roster-expansion-design.md`](archive/2026-07/roster-expansion-design.md).

| Historical proposal | Current disposition |
|---|---|
| `test-engineer` | Folded into ROLE-003/ROLE-004 as an authority choice; no second testing agent yet |
| Running-lab `security-audit` | Survives as LABSEC-001, distinct from repository application security |
| Guard-enforced `lab-inspector` | Survives as blocked LABSEC-002 behind GOV-001 and command-level validation |
| `release` | Survives as trigger-bound RELEASE-001 |
| `porting-method` | Survives as trigger-bound PORT-001 |
| Home-lab SRE description line | Folded into ROLE-001's rebrand without changing the component key |
| Standalone secrets component | Remains rejected; lab posture belongs inside LABSEC-001 if accepted |
| Generic Linux references | Superseded by ROLE-001's action-shaped `host-onboard` boundary |
| LLM-cost, profiling, continuity, and hardware-health references | Not imported as work without an observed consumer; reopen from fresh task evidence |
| Generic Linux agent, generic SRE agent, and merged prompt/multi-agent role | Rejected in both reviews |
