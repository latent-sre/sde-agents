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

Small items (the `Small items` section under Current work) are the deliberate exception: one
line carrying only ID, the observable fix, and source — the tier that keeps tiny defects in this
single tracker instead of leaking into memory or issue lists.

## Current work

### Ready

#### SAFE-003 — resolve the dangling `contract_digest` reference

**Status:** `ready` — a verified gap in shipped code, absorbed from the superseded control-plane
proposal via the GRAPH-003 ruling.

**Outcome:** `contract_digest` stops being a reserved slot that resolves to nothing: the
field's actual binding is documented and enforced at run creation in `scripts/run_state.py` —
never left readable-as-enforcement while enforcing nothing.

**Source:** [`GRAPH-003 adjudication`](archive/2026-08/graph-003-adjudication-2026-08-01.md)
(finding verified against `scripts/run_state.py:104,248-271,886`); absorbed into the accepted
[`AI graph engineering decision`](decisions/2026-07-31-ai-graph-engineering.md).

**Prerequisites:** None. Any schema change honors the version-1 hard-reject at
`scripts/run_state.py:174-177` with an explicit migration decision, never a workaround.

**Acceptance:** Tests for creation-time enforcement of the documented binding;
existing run-state tests and the
deterministic gates stay green.

**Next action:** Implement the ruled repair. The operator chose document-and-enforce
2026-08-09: document the field's actual binding and enforce it at run creation with a test;
the resolver stays trigger-bound on GRAPH-004 activating (re-verified same day: all seven
`contract_digest` references in `scripts/run_state.py` are write-side — schema, validation, storage,
echo — nothing resolves it). SAFE-002 closed without touching `scripts/run_state.py`, so this opens
its own review context rather than piggybacking on that round.

#### LEARN-002 — close the Learning-contract compliance gap

**Status:** `ready` — the measured residual of the merged LEARN-001 round.

**Outcome:** Each of the seven behavioral contracts failing 0/3 under the final closed graders
(`self-improve-lifecycle-merge`, `self-improve-promotion-gate`,
`self-improve-canonical-triaged-close`, `runbook-disposition-propose`,
`learning-slot-readonly-agent`, `learning-slot-operational-agent`,
`learning-runbook-namespaces`) either holds 3/3 across two consecutive clean-room sonnet batches
or has its grammar amended with a recorded rationale — settling empirically whether the closed
contracts or the skill text carried the defect. No grader is silently loosened.

**Source:** [`LEARN-001 outcome record`](archive/2026-08/learn-001-outcome-2026-08-02.md);
live rates in `evals/baselines/2026-08-01-self-improve/final-live/`.

**Prerequisites:** None — the behavioral harness and pinned conditions are ready. Description
edits, if any emerge, owe the overlapping routing cluster before/after per standing law.

**Acceptance:** Per-contract paired before/after behavioral runs under identical recorded
conditions; deterministic gates green; the two 2/3-flaky contracts re-measured alongside; the
watch-metrics (Learning-slot `none`-rate, ledger organic-candidate count) reported at close.

**Next action:** Start with the three self-improve packet-grammar cases — same failure shape, so
one grammar-vs-skill-text decision sets the pattern for the rest. New calibration input
2026-08-10: the first live run of the ten gate-001/verifier contracts
(`evals/baselines/2026-08-10-gate-001-first-live/`, sonnet clean-room, 2/10 green) — every
failure reads grader-shaped (a negation-blind forbidden pattern fired on the correct negated
answer; the packet shape held while the claim-evidence heuristic bit an honest "verified:
nothing" line; one vocabulary miss; one 300s timeout), so those cases join this item's
grammar-vs-text docket rather than being tuned in the GATE-001 branch.

#### CTX-001 — modernize fleet definitions for Claude 5-generation context rules

**Status:** `ready` — eval-gated experiment; the harness it needs already exists.

**Outcome:** The fleet's 30 canonical definitions are audited against the six published shifts for
Claude 5-generation models (rules→judgment, examples→interface design, upfront→progressive
disclosure, repetition→tool definitions, manual memory→auto-memory, simple specs→rich references),
and any edit is justified by paired before/after routing and behavioral evidence — or the audit
records that the published claim did not transfer to this artifact class.

**Source:** Revised
[`AI graph engineering decision`](decisions/2026-07-31-ai-graph-engineering.md) (accepted work),
grounded in the 2026-07-24 context-engineering rules; measurement basis (~190 prohibition-style
lines across the fleet, `sde-fullstack` leading at 24) in the
[`2026-07-31 independent review`](archive/2026-07/graph-decision-independent-review-2026-07-31.md).

**Prerequisites:** EVAL-003's grading evidence governs the measurement design: agent-expecting
routing positives under-fire in headless mode, so grade with negatives, clean-room conditions, and
the pinned behavioral suite. One pilot definition before any fleet-wide edit.

**Acceptance:** For every edited definition, paired before/after runs under identical recorded
conditions with no negative-case regression and behavioral contracts green; a written stop rule if
the pilot regresses; regenerated adapters and the deterministic gates green.

**Next action:** Open a bounded spec choosing the pilot definition (`sde-fullstack` is the
highest-density candidate) and the exact paired-measurement conditions before editing anything.
Named audit material from the 2026-08-09 estate feedback: the Learning-bullet specification is
~9 of 15 packet bullet-lines in each of 11 always-loaded definitions for a field whose ordinary
value is one line — a compression candidate gated on the pinned learning-slot behavioral
contracts holding.

#### GRAPH-002 — land the descriptive capability graph and contract validator

**Status:** `ready`

**Outcome:** The accepted GRAPH-001 descriptive layer exists: a derived machine-readable
capability graph over the canonical definitions and a standard-library workflow-contract
parser/validator, including the graph-level checks the decision names (unreferenced components,
eval-uncovered routing edges, self-loops, hub concentration, prompt-surface→tool reachability).

**Source:** Accepted
[`AI graph engineering decision`](decisions/2026-07-31-ai-graph-engineering.md) — the
"Accepted -- descriptive compiler and contract validator" work.

**Prerequisites:** None hard. Sequence after WF-001 closes: both rounds edit
`scripts/validate_fleet.py`, and serializing them keeps each round's mutation tests reviewable.

**Acceptance:** The decision's descriptive-layer acceptance-evidence list (a fixture or mutation
test per invariant; parser/validator tests for the negative contracts; no new runtime
dependency), delivered under its own bounded spec and paired plan.

**Next action:** Author the bounded spec and plan — WF-001 retired to its
[outcome record](archive/2026-08/wf-001-outcome-2026-08-01.md) on 2026-08-01, so the
validator-churn sequencing gate is satisfied.

#### LABSEC-002 — add a guard-enforced lab inspector

**Status:** `ready` — DEPLOY-001 accepted Option A on 2026-07-31, and normal-session probes proved
namespaced registration, guarded-agent denial, and main-loop exclusion.

**Outcome:** Add an optional read-only agent that can work the hygiene (`lab-audit`) or adversary
(`security-audit`) checklist under guard enforcement, without taking change authority or combining
lab secrets with web access. Both checklists now exist — LABSEC-001 landed 2026-07-29 — so this
item is purely the enforcement shell.

**Source:** Archived
[`roster expansion design`](archive/2026-07/roster-expansion-design.md), reconciled by the role
decision.

**Prerequisites:** Satisfied: LABSEC-001, DEPLOY-001, GOV-001, and EVAL-001 landed. The implementation
must still independently threat-review the proposed reader, regression-test every allowlist
addition, and retain hook/guard roster synchronization.

**Acceptance:** The agent has no write or web tools; every additional allowlisted command is
read-only by tested verb/flag policy; the POSIX plugin probe proves the guard fires for the exact
roster and ignores the main session; routing preserves outage/change authority in
`homelab-platform`.

**Next action:** Open a bounded spec/plan for the inspector, beginning with the smallest required
read-only command surface and a threat review of every new verb/flag before changing the guard.

#### REV-001 — advisory/approval split and the review-to-verify envelope

**Status:** `ready` — spec approved by the operator 2026-08-09, with the condition that the
shared material-risk matrix grows by generalization, never per-incident append.

**Outcome:** A formal review approval binds to immutable identity (commit, parent, tree digest)
and never transfers to changed bytes; the verifier requires that envelope and fails closed on
mismatch; reviewer and verifier share one material-risk matrix; caller-reported and
independently-executed evidence stay distinct classes. The fleet's working-diff review lanes
remain legal as advisory mode.

**Source:** [`REV-001 spec`](superpowers/specs/rev-001-immutable-review-envelope.md); issue #62
with its SEC-01 field closeouts; operator ruling 2026-08-03 (smallest mechanism,
GRAPH-004-compatible field names — GRAPH-004 stays deferred).

**Prerequisites:** None hard; behavioral-contract additions ride the pinned harness.

**Acceptance:** The spec's list; headline gates are the #62 scenario evals, adapter parity, and
no change to working-diff lane behavior.

**Next action:** Author the paired plan. Ledger candidates `lc_90dd8dc7` and `lc_2c04ead3`
completed their ledger transitions (proposed, with destinations `verification-engineer` and
`code-reviewer`) and ride this round per the operator's 2026-08-09 direction — the paired plan
admits them explicitly when it is authored.

#### HANDOFF-001 — evidence-bound onboarding handoff packet

**Status:** `ready` — spec approved by the operator 2026-08-09; **sequenced after REV-001** so
the packet reuses that round's envelope idiom.

**Outcome:** Onboarding work delegates through one echoed, evidence-bound packet whose sections
carry failed assumptions, verification-method validity, the executable-transport contract,
irreversible postconditions, authority lifetimes, inventory invariants, and secret-safe capture
— and the known-failed-assumption fixture stops regressing across POC→builder handoffs.

**Source:** [`HANDOFF-001 spec`](superpowers/specs/handoff-001-onboarding-handoff-packet.md);
issue #60 with three-occurrence recurrence evidence and its field-derived section list.

**Prerequisites:** REV-001's settled idiom.

**Acceptance:** The spec's list — issue #60's paired evals plus the three closeout fixtures.

**Next action:** Hold for REV-001's settled idiom, then author the paired plan.

#### LANE-001 — Codex-lane onboarding discoverability

**Status:** `ready` — spec approved by the operator 2026-08-09, with the design premise
re-verified same-day against upstream HEAD `a16863f8` (skill filtering and spawn-schema
suppression both hold). A host-neutral implementation candidate is open as PR #107 — a
model-visible `onboarding-map` skill with its cluster cases, README lane section, and decision
amendment — and its deterministic gates and adapter parity are green. That is packaging evidence,
not lane evidence: nothing on that branch measures a Codex host, the spec's Phase-0 host evidence
is still outstanding, and `superpowers/plans/` holds no LANE-001 plan, so no round is running.

**Outcome:** On a Codex session with the fleet installed, plain-language new-service or new-host
intent yields a model recommendation of the explicit onboarding workflow — never an implicit
execution — and the Claude lane's measured routing rates do not regress.

**Source:** [`LANE-001 spec`](superpowers/specs/lane-001-codex-onboarding-discoverability.md);
issue #61 (failure layer identified 2026-08-02: skills hard-hidden from the model, agent
delegation v2-suppressed); operator rulings 2026-08-02 (supported-but-limited lane, smallest
mechanism); learning-ledger candidate `lc_c361b3d3`.

**Prerequisites:** the spec's Phase 0, unchanged and still blocking — `codex --version` and
`grep -L "Managed by sde-agents" $CODEX_HOME/agents/*.toml`, both from the SEC-01 Linux host. No
codex-cli version has ever been measured on that host. The only Codex CLI version this repository
records from a run is `codex-cli 0.145.0` (2026-07-31 SAFE-001 host conformance,
`evals/baselines/2026-07-31-p0-p1/host-conformance/`). `rust-v0.147.0` is an upstream GitHub
release tag quoted in a researcher packet — `learning/candidates/`, candidate
`lc_9e5728c32b23494296f9bec3881c12d2` — not an observation of any host, and citing it as one is
what let this item read as evidence-backed. Waiving Phase 0 takes an operator-approved spec
amendment, not a roadmap sentence.

**Acceptance:** The spec's list. Three gates are open, all operator-owned:

1. Phase 0's two one-liners from SEC-01, or that spec amendment.
2. The paired `homelab-ops` before/after captures. `eval_baseline.py` returns `STALE` for this
   cluster, so the 'before' side is a fresh capture at merge base `4fef0ce`, not a stored reuse.
3. The recorded Codex smoke run (spec line 92), which must exercise a **released** artifact. The
   1.7.3 release records 19 skills (`evals/baselines/2026-08-10-rel-173/conditions.md`) and this
   map would be the twentieth, so the run waits on a 1.7.4 release tail and is filed through the
   ledger's `record-release`/`record-retest` — LOOP-001's rule below, that source PASS is never
   reportable as released-artifact PASS, is exactly this case.

**Next action:** Operator runs the two Phase-0 one-liners on the SEC-01 Linux host, then captures
the paired routing run; the smoke run follows the 1.7.4 release.

#### LOOP-001 — released-version retest closes the field-feedback loop

**Status:** `ready` — the shared-ownership prerequisite is fully settled: GATE-001 closed
2026-08-10 ([outcome record](archive/2026-08/gate-001-outcome-2026-08-10.md)) and the five-tier
classification it owns is shipped canonically in `agents/homelab-platform.md`'s
change-authority section; this spec references that canonical text.

**Outcome:** A retained field-feedback item has one visible lifecycle from sanitized packet
through triage, owner and target release, paired evaluation, canonical change with adapter
parity, released plugin version, and a retest of the originating scenario on the released
artifact — and cannot close as successful without that retest or an owner-approved reason it is
impossible. Source-eval PASS is never reportable as released-artifact PASS. No scheduler,
daemon, transcript store, or self-modifying loop.

**Source:** [`LOOP-001 spec`](superpowers/specs/loop-001-released-retest-lifecycle.md) (approved
2026-08-09); issue #67; ledger candidate `lc_74f04730`; the
release-tail record (a merged bump demonstrably not reaching live sessions) as independent
evidence of the merged≠released gap; issue #73 (Learning handoffs dropped by foreign
coordinators in a 26-dispatch field run) as capture-is-not-closure evidence for Eval 1.

**Prerequisites:** None — the classification this spec references is released canonical text
(GATE-001, closed 2026-08-10).

**Acceptance:** Issue #67's list; headline gates are its Evals 1–3 (capture is not closure;
duplicates merge provenance; source PASS ≠ released retest) plus the no-new-machinery non-goal.

**Next action:** Author the paired plan.

### Small items

The deliberate lightweight tier: defects and gaps too small for the full item contract, so they
do not leak into session memory or issue lists as a shadow queue. One line each — ID, the
observable fix, source. No prerequisites and no acceptance section: the fix plus green
deterministic gates closes a line, and closing it means deleting it. A line that turns out to
need prerequisites or acceptance evidence beyond itself graduates to a full item above. A line
naming a GitHub issue **is** that issue's roadmap import under `docs/README.md` rule 7.

- **SMALL-001** — `agents/prompt-engineer.md:43`: scope the promote-repeated-helpers-into-
  `scripts/` advice to skills; agents and tool descriptions have no bundle directories, so as
  written it recommends the impossible. Source: 2026-07-19 multi-lens self-review; re-verified
  2026-08-04.
- **SMALL-002** — the AGENTS.md style rule claims prose wraps at ~100 columns "matching the
  existing files"; measured 2026-08-04, 218/1152 agent lines and 232/1623 SKILL.md lines exceed
  100. Fix the rule's claim or the files — not neither. Source: same review; re-measured
  2026-08-04.
- **SMALL-003** — the `prompt-engineer` held-out rule's second-edit-same-eval-set branch has
  never fired; probe it with a staged scenario. Source: 2026-07-19 wrap-up, unprobed since.
- **SMALL-004** — `frontend-craft` screenshot-as-you-build needs a probe with a real browser
  loop; headless fixtures could not exercise it. Source: 2026-07-19 wrap-up, unprobed since.
- **SMALL-005** — `sre-tool`'s contested-finding cap and `sde-fullstack`'s Findings-response
  packet slot are validator-green but behaviorally unprobed. Source: 2026-07-19 self-review
  fixes, unprobed since.
- **SMALL-006** — the AGENTS.md Map has no row for `scripts/ledger_drift.py`, the only
  CI-wired script missing from it. Source: PR #89 review note, imported at TIER-001 closeout
  ([outcome record](archive/2026-08/tier-001-outcome-2026-08-08.md)).

## Deferred decisions

#### GRAPH-004 — typed edge-contract pilot

**Status:** `deferred` — trigger-bound, absorbed from the superseded control-plane proposal via
the GRAPH-003 ruling.

**Outcome:** One real handoff (builder → reviewer is the natural candidate) expressed as a
host-neutral typed contract, with `contract_digest` resolving to it — extending WF-001's packet
schemas from workflow-edge validation to a ledger-bound contract, under the accepted record's
retained node/edge design.

**Source:** [`GRAPH-003 adjudication`](archive/2026-08/graph-003-adjudication-2026-08-01.md);
governed by the accepted
[`AI graph engineering decision`](decisions/2026-07-31-ai-graph-engineering.md), including its
absorbed generated-prompt provenance control.

**Prerequisites:** A demonstrated consumer, per the accepted record's discipline. Reopen
triggers: a second workflow conversion is decided (the pilot economics in the
[`WF-001 pilot note`](archive/2026-08/wf-001-pilot-run-2026-08.md) are the baseline for that
call), or SAFE-003's repair chooses the resolver path and needs a real contract document to
resolve to.

**Acceptance:** The contract document exists, `contract_digest` resolves to it with a test, the
workflow (if any) consuming it validates against it, and no judgment text lives outside
canonical files.

**Next action:** None until a trigger fires; SAFE-003's resolver decision is the likeliest
ignition.

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
