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

#### ROUND1-001 — complete the approved fleet-expansion Round 1

**Status:** `active`

**Outcome:** Land the PowerShell craft reference with measured routing behavior, split
`lab-audit`'s checks into command-level guidance with a ledger output, and add the three approved
behavioral contracts.

**Source:** Approved
[`Round 1 design`](superpowers/specs/2026-07-27-fleet-expansion-round1-design.md) and executable
[`Round 1 plan`](superpowers/plans/2026-07-27-fleet-expansion-round1.md).

**Prerequisites:** Resume measurement safely. A 27-session batch launched in a fire-and-return
subagent produced no artifact and no provable eval session. The plan must now be worked from an
owning foreground session.

**Acceptance:** Every planned file and case lands; the scoped routing before/after artifacts record
comparable model and timeout conditions; all new behavioral cases pass at the agreed thrift scope;
validator, unit suite, and strict plugin validation pass; this item is closed with exact commits
and any deliberate deviations.

**Next action:** Run the backlog's cheap discriminator in a watched owning session:
`eval_routing.py` with `--runs 1 --limit 1`, pinned model and timeout. If it completes, resume the
plan in the foreground. If it hangs or dies, diagnose the Windows runner rather than launching
another batch.

### Ready

#### GOV-001 — make malformed guarded input fail closed

**Status:** `ready`

**Outcome:** A malformed hook payload that still identifies a guarded agent can never return the
authoritative allow sentinel, while malformed unguarded/main-session input cannot brick unrelated
work.

**Source:** 2026-07-28 role/governance review, Finding G1.

**Prerequisites:** None. Fix before adding any guarded or execution-capable role.

**Acceptance:** A focused test proves the current malformed-guarded payload passes before the fix;
new direct and end-to-end cases cover malformed guarded deny, malformed unguarded no-op, valid
guarded deny, and valid unguarded pass-through; hook/guard probe passes on a POSIX-capable host.

**Next action:** Add the failing regression cases, then change parse failure from ALLOW to an
indeterminate path that reaches the hook's guarded-agent fallback.

#### EVAL-001 — validate routing-cluster target integrity

**Status:** `ready`

**Outcome:** A positive case cannot silently pass by accepting a component outside the cluster's
declared members unless the schema explicitly declares that adjacent target.

**Source:** 2026-07-28 role/governance review, Finding G2.

**Prerequisites:** Decide whether outside-member positive targets are prohibited or represented by
a named `adjacent_accepts` field. Default recommendation: prohibit until a real case requires the
exception.

**Acceptance:** A fixture or mutation test fails against the current
`pos-ci-actions-harden`/`code-reviewer` inconsistency; validation covers unique IDs, resolvable
members and targets, positive membership, and negative forbidden sets; the test fails without the
validator change.

**Next action:** Encode the failing cluster fixture and choose the smallest schema rule that makes
the scorer and reported cluster rate agree.

#### EVAL-002 — record behavioral-eval conditions and token use

**Status:** `ready`

**Outcome:** Behavioral benchmark artifacts record enough conditions and usage to compare contract
pass rate and cost rather than reporting pass/fail alone.

**Source:** ECC Batch 2's accepted eval doctrine, confirmed missing during reconciliation.

**Prerequisites:** Preserve deterministic grading; usage collection must not introduce a judge.

**Acceptance:** `benchmark.json` records CLI/model/timeout conditions plus observed input/output
token usage per run or labels usage unavailable; unit tests cover complete and missing usage; the
existing behavioral cases grade identically.

**Next action:** Reuse the routing runner's transcript-usage extraction rather than deriving a
second parser.

## Deferred decisions

#### ROLE-001 — approve the home-lab SRE rebrand and Linux-host boundary

**Status:** `decision-needed`

**Outcome:** Keep the canonical `homelab-platform` key, present it visibly as Home-Lab SRE /
Platform Engineer, add Linux-host trigger vocabulary, and decide whether `host-onboard` should be
the first explicit-only host lifecycle skill.

**Source:** 2026-07-28 independent role review; decision proposal is consolidated in Step 4.

**Prerequisites:** Operator approval. Any description edit then owes a before/after
`homelab-ops` routing run.

**Acceptance:** Decision record is marked accepted; visible title/description and `host-onboard`
land with inventory and routing coverage; existing service/application near-misses remain clean.

**Next action:** Review the Step 4 decision record and accept, revise, or reject the recommendation.

#### ROLE-002 — approve an application-security auditor

**Status:** `decision-needed`

**Outcome:** Add a static-first agent for repository/subsystem audits, threat models, attack paths,
and finding validation without taking PR review or remediation authority.

**Source:** 2026-07-28 independent role review.

**Prerequisites:** Operator approval and EVAL-001. GOV-001 is required only if the initial agent is
given guarded Bash; the recommended initial tools avoid it.

**Acceptance:** Decision is accepted; agent has explicit static tools, no implementation authority,
a source-backed output contract, and negative routing against `code-reviewer`, `researcher`,
`homelab-platform`, and `sde-fullstack`.

**Next action:** Approve the role boundary and initial no-Bash authority.

#### ROLE-003 — define verification execution authority

**Status:** `decision-needed`

**Outcome:** Decide how an independent verifier may execute repository tests without pretending
that test runners are read-only or that a worktree contains network/database side effects.

**Source:** 2026-07-28 independent role review.

**Prerequisites:** GOV-001 and operator choice on test-file edits, worktree isolation, integration
tests, external effects, and live-environment approval.

**Acceptance:** A written authority contract names allowed product/test edits, worktree behavior,
external-effect gates, and enforcement limits; governance tests pin any new roster or exception.

**Next action:** Choose the authority model before authoring the agent.

#### ROLE-004 — add an independent verification engineer

**Status:** `blocked`

**Outcome:** Add an agent that independently reproduces and executes acceptance/regression
evidence without implementing the product fix.

**Source:** 2026-07-28 independent role review.

**Prerequisites:** ROLE-003 accepted, GOV-001 landed, and EVAL-001 landed.

**Acceptance:** Agent and routing cases separate verification from implementation, diagnosis,
static review, and live operations; behavioral tests prove unrun checks cannot be called passed and
evidence belongs to the exact tested revision/environment.

**Next action:** None until ROLE-003 is accepted.

#### EVAL-003 — capture a comparable full routing anchor

**Status:** `deferred`

**Outcome:** Establish one current, condition-complete baseline across all routing clusters.

**Source:** Adaptation backlog's parked re-baseline analysis.

**Prerequisites:** ROUND1-001 measurement path is healthy; run small watched foreground batches;
fix case-design defects before treating numbers as description evidence.

**Acceptance:** Every artifact records requested/observed model, timeout, CLI version, threshold,
and per-run evidence; no known-invalid artifact is called an anchor.

**Next action:** Revisit after Round 1's watched smoke run and scoped anchor complete.

#### EVAL-004 — verify the accessibility imports behaviorally

**Status:** `deferred`

**Outcome:** Demonstrate that a real UI task loads and applies form wiring or interaction
accessibility guidance and supplies keyboard-pass evidence.

**Source:** ECC Batch 1's only remaining implementation-verification residue.

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

The 2026-07-28 role review is current rather than historical. Static inspection and direct
reproduction leave these candidates for Step 3:

- malformed guarded JSON returns the authoritative allow sentinel;
- one routing positive accepts a component outside its declared cluster;
- rebrand the visible homelab role and add Linux-host triggers without renaming its key;
- add the action-shaped `host-onboard` skill;
- add an application-security auditor with a non-PR remit;
- design test-execution authority, then add an independent verification engineer.

Step 3 converts these survivors, the active Round 1 work, the deferred routing measurement, ECC
behavioral residue, and the trigger-bound compose asset into full roadmap items.
