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

### Ready

## Deferred decisions

#### DEPLOY-001 — decide the fleet's daily deployment mode

**Status:** `deferred` — indefinitely, by operator choice. The original deferral said "decide after
GOV-001, EVAL-001, ROLE-001, and ROLE-002 land"; **all four landed on 2026-07-29 and the operator
deferred again with no new condition**, so this item is parked rather than pending. Do not read it
as ready-to-decide. The hard gates are unchanged and are the reopen triggers: it must be decided
before any LABSEC-002 work or after a real junction-session boundary incident. Cross-host consumer
installation is governed separately by the accepted
[`multi-platform packaging decision`](decisions/2026-07-30-multi-platform-packaging.md).

**Both options are executable when it reopens** (verified 2026-07-29, CLI 2.1.220): the CLI carries
`claude plugin marketplace add <path>` and `claude plugin install`, so plugin mode needs no manual
`settings.json` surgery; junction mode needs only the honest-posture note.

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

#### LABSEC-002 — add a guard-enforced lab inspector

**Status:** `blocked`

**Outcome:** Add an optional read-only agent that can work the hygiene (`lab-audit`) or adversary
(`security-audit`) checklist under guard enforcement, without taking change authority or combining
lab secrets with web access. Both checklists now exist — LABSEC-001 landed 2026-07-29 — so this
item is purely the enforcement shell.

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

**Two facts established 2026-07-29 that shape this item:**

1. **The native `claude plugin eval` is still gated** — the subcommand now exists with ablation,
   graders, and JSON output, but invoking it returns "`plugin eval` is currently in early access"
   (checked at CLI 2.1.220). So `evals/README.md`'s stopgap framing remains accurate, and this
   anchor must still be captured with `scripts/eval_routing.py`. Re-check on CLI upgrades: when it
   opens, note that its case shape (`evals/**/case.yaml` or `prompt.md` + `graders/*.md`) is *not*
   the fleet's cluster JSON, so migration is real work, not a rename.
2. **Agent-expecting positives fire at ~0% in headless one-shot mode on the current tier** —
   0/21 in the Round 1 diagnose, 0/6 for ROLE-001's host cases, 0/6 for the auditor's, while
   sharp-trigger *skill* positives hit 100% (6/6 in the diagnose, 6/6 for `security-audit`). An
   anchor capturing agent positives at zero would record the harness, not the descriptions. Settle
   the case design — or grade agent members differently — before spending a full-suite capture.

3. **Configuration contamination is measured — and refuted as the agent-positive suppressor**
   (2026-07-29, phase 1 of this item). `scripts/probe_isolation.py` showed every eval session had
   been inheriting 134 operator-side entries, with the fleet registered twice (9 bare via the
   junction deployment + 9 namespaced via `--plugin-dir`). Under `--clean-room`
   (`scripts/eval_clean_room.py`; namespaced-only fleet, one plugin) the auditor's two agent
   positives still fired **0/6** under otherwise-identical conditions
   (`baselines/2026-07-29-isolation/appsec-cleanroom` vs the same day's contaminated 0/6). The
   under-fire is a property of headless one-shot mode on this tier, not of the operator's
   configuration. Both runners now record `clean_room` in `conditions`, and artifacts differing on
   it must not be diffed against each other.

**Next action:** Decide the agent-member grading — the evidence-backed default is negatives-only
in routing, with each agent's contract covered by the pinned behavioral suite (`--agent` runs are
deterministic where routing summons are not) — then capture the anchor under `--clean-room`, whose
conditions the artifact now records. Isolation will not rescue agent positives; nothing further is
owed on that question.

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

**The platform already does part of this** (found 2026-07-29, CLI 2.1.220):
`claude plugin tag [path]` creates a `{name}--v{version}` git tag *and validates that `plugin.json`
agrees with the enclosing marketplace entry* — with `--dry-run`, `--push`, and `--remote`. That is
exactly the manifest-consistency check this item would otherwise hand-roll, so the component must
**consume** it rather than reimplement it, and the tagging step of its own release row is one
command. `claude plugin update` is the counterpart for a consumer refreshing an installed copy.

**Next action:** Reopen before the next manually orchestrated release; start from `claude plugin
tag --dry-run` and write the component around what it does *not* cover (version choice, changelog,
publication, yank).

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
| Eval coverage stops at one routing cluster with no behavioral checks | Six routing clusters, the behavioral runner, packet linter, and 21 deterministic contracts exist | Machinery landed; additional contract coverage survives below |
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
| `restore-drill` and `upgrade-campaign` | Both appear in the generated 19-skill inventory | Landed; exclude despite the backlog's stale “remain open” sentence |
| `security-seed.md` for `sre-tool` | The diff reviewer gained a security lens; the role review now proposes a distinct whole-repository security auditor | Superseded by the application-security decision |
| `host-onboard` | `skills/host-onboard/SKILL.md` ships the host-lifecycle checklist and is wired from `homelab-platform` | Landed; exclude |
| `lab-audit` command reference and findings ledger | `skills/lab-audit/references/checks.md` owns the command detail and ledger format; `SKILL.md` links it and emits ledger rows | Landed; exclude |
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
| Track token cost beside behavioral pass rate | `eval_behavioral.py` records per-run input/output usage plus requested/observed model and other measurement conditions | Landed; exclude |
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
