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
| Constraints | Operator rulings and do-not lines that bind this item, one line each |
| Acceptance | Evidence required to close the item |
| Next action | The smallest safe step that moves it forward |

An item leaves this file when its acceptance evidence is committed. The source decision remains;
Git history and archived reviews retain the implementation detail.

Small items (the `Small items` section under Current work) are the deliberate exception: one
line carrying only ID, the observable fix, and source — the tier that keeps tiny defects in this
single tracker instead of leaking into memory or issue lists.

Every item below was cut to these fields on 2026-09-01; the narration, dated addenda, and
round-by-round detail removed in that pass live verbatim in
[`roadmap-history-2026-09-01.md`](archive/2026-09/roadmap-history-2026-09-01.md), linked from
each item's Source.

## Current work

### Ready

#### LEARN-002 — close the Learning-contract compliance gap

**Status:** `ready` — one paid behavioral batch plus one operator ruling remain; see Next action
for the full owed list.

**Outcome:** Each of seven originally 0/3 contracts holds 3/3 across two consecutive clean-room
batches, or is amended with rationale; each of six LOOP-001/REV-001 contracts holds its baseline
rate or is repaired with rationale.

**Source:**
[LEARN-001 outcome](archive/2026-08/learn-001-outcome-2026-08-02.md) ·
[LOOP-001 outcome](archive/2026-08/loop-001-outcome-2026-08-10.md) ·
[REV-001 outcome](archive/2026-08/rev-001-outcome-2026-08-10.md) ·
[offline repairs](archive/2026-08/learn-002-offline-repairs-2026-08-17.md) ·
[2026-08-19 settling decisions](../evals/baselines/2026-08-19-settling/decisions.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#learn-002-close-the-learning-contract-compliance-gap)

**Prerequisites:** None — harness and pinned conditions are ready; description edits owe the
routing cluster before/after.

**Constraints:** Do not diff results against the 2026-08-15 artifacts — evaluator bytes moved
since then.

**Acceptance:** Per-contract behavioral runs under identical recorded conditions for the original
seven, deterministic gates green, the two flaky contracts re-measured; a grader-side repair is
satisfied by one current-tree batch, a text repair owes a genuine pair. Each of the six
LOOP-001/REV-001 contracts needs a three-run clean-room baseline plus a held rate or a repair with
rationale.

**Next action:** One paid batch — the seven originals plus five unsettled LOOP/REV contracts —
under recorded conditions, re-checking `learning-runbook-namespaces-compose`'s n=3 drop first;
plus the deferred operator ruling on `reviewer-formal-approval-emits-envelope`.

#### CTX-001 — modernize fleet definitions for Claude 5-generation context rules

**Status:** `ready` — eval-gated experiment; the harness it needs already exists.

**Outcome:** The fleet's 31 canonical definitions are audited against six published Claude
5-generation context shifts, and any edit is justified by paired before/after routing and
behavioral evidence, or recorded as not transferring.

**Source:**
[AI graph engineering decision](decisions/2026-07-31-ai-graph-engineering.md) ·
[2026-07-31 independent review](archive/2026-07/graph-decision-independent-review-2026-07-31.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ctx-001-modernize-fleet-definitions-for-claude-5-generation-context-rules)

**Prerequisites:** EVAL-003's grading design (negatives, clean-room, pinned behavioral suite); one
pilot definition before any fleet-wide edit.

**Acceptance:** For every edited definition: paired before/after runs under identical recorded
conditions, no negative-case regression, behavioral contracts green, a written stop rule if the
pilot regresses, regenerated adapters, deterministic gates green.

**Next action:** Open a bounded spec choosing the pilot definition (`sde-fullstack` is the
highest-density candidate) and the exact paired-measurement conditions before editing anything.

#### CTX-002 — fit the model-visible skill listing inside the 8,000-char host budget

**Status:** `ready` — pass 1 of three; independent of pass 2, may run before or alongside pass 3.

**Outcome:** The fleet's model-visible listing (~11.9k chars, 19 entries) fits the 8,000-char
worst-case budget with stated headroom, fixing Codex fully and maximizing survivors on
200k-context Claude hosts.

**Source:**
[2026-08-16 skill-listing investigation](archive/2026-08/skill-listing-investigation-2026-08-16.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ctx-002-fit-the-model-visible-skill-listing-inside-the-8000-char-host-budget)

**Prerequisites:** None — every description edit owes the standing paired routing-eval
discipline.

**Constraints:** The v4 benchmarks in `evals/baselines/2026-08-18-ctx-002/` must not be retired
while this item or LANE-001 is open.

**Acceptance:** Paired before/after routing runs for every edited description's overlapping
clusters (a stored capture may satisfy 'before' if checked by hand and still unchanged); doctor
reports `pass` with headroom; regenerated adapters; a live listing probe on a 200k-window model
recording survivors.

**Next action:** Trim the three largest entries first — `self-improve-loop`, `deep-review`,
`onboarding-map` — roughly 3.9k chars to cut.

#### CTX-003 — shrink the per-spawn preload footprint without hollowing the probe's proof

**Status:** `ready` — pass 2 of three; heaviest pass, runs when there is appetite for
behavioral-contract rounds.

**Outcome:** Per-spawn preload cost drops measurably (e.g. `sde-fullstack`'s ~12.1k preloaded
tokens), with behavioral contracts proving slimmed bodies still deliver what fat ones did;
references stay the on-demand layer.

**Source:**
[2026-08-16 skill-listing investigation](archive/2026-08/skill-listing-investigation-2026-08-16.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ctx-003-shrink-the-per-spawn-preload-footprint-without-hollowing-the-probes-proof)

**Prerequisites:** None mechanically; `scripts/probe_plugin.py`'s craft canaries must move
deliberately with the body, or stay in it.

**Constraints:** The conditional-reference read is measured intermittent (falsified 2026-08-30) —
re-verify it before shrinking anything into the on-demand layer.

**Acceptance:** Before/after behavioral-contract runs for every agent whose preloaded set
changed; probe green with canary assertions intact or deliberately migrated; regenerated
adapters; doctor and validator green; byte deltas recorded per skill.

**Next action:** Restructure `self-improve-loop` first — compact loop plus closeout contract in
SKILL.md, full lifecycle protocol to a reference.

#### CTX-004 — lock the context wins in: settings lines, validator promotion, Copilot cap

**Status:** `ready` — pass 3 of three; only the promotion step is gated on CTX-002.

**Outcome:** Three locks: a calibrated `skillListingBudgetFraction` in lab repositories'
settings, the doctor's listing-budget warning promoted to a hard validator rule, and a
generated-adapter size tripwire ahead of GitHub's 30,000-char cap.

**Source:**
[2026-08-16 skill-listing investigation](archive/2026-08/skill-listing-investigation-2026-08-16.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ctx-004-lock-the-context-wins-in-settings-lines-validator-promotion-copilot-cap)

**Prerequisites:** CTX-002, for the promotion step only.

**Acceptance:** Settings lines landed with each environment's live-probe calibration; the
promoted validator rule with a failing fixture; the Copilot-cap tripwire with a firing test;
regenerated adapters; green tiers.

**Next action:** Ship the Copilot-cap tripwire first — prerequisite-free, small, and its
measurement is already committed evidence.

#### CTX-005 — shrink `homelab-engineer`'s always-loaded body

**Status:** `decision-needed` — one authorized safety repair and one behavioral round are spent;
the branch is no-go evidence, not merge-ready.

**Outcome:** The safety repair improved fresh behavior (45/125 to 55/125, new safety case 5/5)
but regressed three baseline-perfect contracts to 4/5 (60/130 overall); acceptance still fails.

**Source:**
[Homelab proportional operations decision](decisions/2026-08-23-homelab-proportional-operations.md) ·
[CTX-005 discipline audit](archive/2026-08/ctx-005-engineering-discipline-audit-2026-08-23.md) ·
[GATE-006 outcome](archive/2026-08/gate-006-outcome-2026-08-30.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ctx-005-shrink-homelab-engineers-always-loaded-body)

**Prerequisites:** GATE-006 (landed). Its after-side lane cannot serve as this diet's before
side — a fresh baseline must be captured.

**Constraints:**
- EVAL-011 gates this item; cutting always-loaded body on biased rates would penalize the
  inspect-first discipline the body carries. Re-measure after EVAL-011, or state why not.
- Do not mix another policy change into the diet.

**Acceptance:** Before/after character counts under the same instrument; every affected homelab
behavioral contract passes in the required fresh lane; probe and offline suite stay green;
adapters match sources; the outcome names what was removed, compressed, or kept and why.

**Next action:** No further review-driven bytes or capture retries are planned; a later ruling
reopening work restarts root-cause analysis from refreshed main.

#### LABSEC-002 — add a guard-enforced lab inspector

**Status:** `ready` — Option A accepted 2026-07-31; normal-session probes proved registration,
denial, and exclusion.

**Outcome:** Add an optional read-only agent working the hygiene (`lab-audit`) or adversary
(`security-audit`) checklist under guard enforcement, with no change authority or web access;
this item is purely the enforcement shell.

**Source:**
[roster expansion design](archive/2026-07/roster-expansion-design.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#labsec-002-add-a-guard-enforced-lab-inspector)

**Prerequisites:** None — LABSEC-001, DEPLOY-001, GOV-001, EVAL-001 landed.

**Acceptance:** The agent has no write or web tools; every added allowlisted command is
read-only by tested verb/flag policy; the plugin probe proves the guard fires for the exact
roster and ignores the main session; routing preserves `homelab-engineer`'s outage/change
authority.

**Next action:** Open a bounded spec/plan, starting with the smallest read-only command surface
and a threat review of every new verb/flag.

#### HANDOFF-001 — evidence-bound onboarding handoff packet

**Status:** `active` — manager-owned amendment authorized 2026-08-11; REV-001's sequencing
condition is met.

**Outcome:** Onboarding delegates through one manager-owned, digest-bound work order carrying
failed assumptions, verification-method validity, executable-transport contract, irreversible
postconditions, authority lifetimes, inventory invariants, and secret-safe capture; the builder
returns only an accepted/input-required receipt.

**Source:**
[HANDOFF-001 spec](superpowers/specs/handoff-001-onboarding-handoff-packet.md) ·
[paired lean plan](superpowers/plans/handoff-001-plan.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#handoff-001-evidence-bound-onboarding-handoff-packet)

**Prerequisites:** None — REV-001's idiom is settled in source.

**Constraints:** Do not compare Claude results with the archived Terra approximation
(different runtime/model).

**Acceptance:** The spec's list — issue #60's paired evals plus the three closeout fixtures.

**Next action:** Re-run the two void cases (`handoff-builder-applies-work-order`,
`handoff-builder-rejects-digest-mismatch`) under recorded conditions and confirm the mandated
`python -I` commands execute; only then propose a full paired capture.

#### LANE-001 — Codex-lane onboarding discoverability

**Status:** `ready` — spec approved 2026-08-09; host-neutral packaging landed in PR #107, but no
round is running and no Codex host evidence exists yet.

**Outcome:** On a Codex session with the fleet installed, plain-language onboarding intent
yields a model recommendation of the explicit workflow, never implicit execution, with the
Claude lane's measured routing rates unaffected.

**Source:**
[LANE-001 spec](superpowers/specs/lane-001-codex-onboarding-discoverability.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#lane-001-codex-lane-onboarding-discoverability)

**Prerequisites:** The spec's Phase 0 (two SEC-01 one-liners), still blocking; waiving it takes
an operator-approved spec amendment.

**Acceptance:** The spec's list: Phase 0's one-liners (or amendment); the paired `homelab-ops`
before/after capture at merge base `4fef0ce`; a recorded Codex smoke run against a released
artifact, filed through the ledger's release/retest rule.

**Next action:** Operator runs the two Phase-0 one-liners on the SEC-01 Linux host, then
captures the paired routing run; the smoke run follows the next release.

#### LADDER-002 — decide the eng-ladder description round

**Status:** `decision-needed` — diagnosis complete; which repairs, if any, to buy is the
operator's ruling.

**Outcome:** Each of the LADDER-001 capture's two under-firing modes gets its measured repair,
or a recorded decision not to buy one, with the instrument fixed to measure what it claims.

**Source:**
[LADDER-001 outcome](archive/2026-08/ladder-001-outcome-2026-08-14.md) ·
[2026-08-14 investigation](archive/2026-08/ladder-002-investigation-2026-08-14.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ladder-002-decide-the-eng-ladder-description-round)

**Prerequisites:** A fresh 'before' capture — the 2026-08-14 baseline is STALE;
`evals/baselines/2026-08-11-ladder/` is a historical anchor only.

**Constraints:** Do not author another Mode 3 growth-feedback routing case beyond the landed
`pos-engladder-growth-feedback`.

**Acceptance:** (a) Mode 3 trim: description-plus-body edit, paired before/after including the
landed growth-feedback case, no unexplained regression on surviving positives, and disposition
of the measurement-only case. (b) Instrument repairs: assess case fires in an empty cwd
(threshold 0.5); consult-fork ported to a required-consult behavioral contract (5 runs); or the
falsifying experiment is recorded. Full criteria: history.

**Next action:** Operator ruling on which half, if either, to buy.

#### ACK-001 — make a dropped Learning handoff visible

**Status:** `decision-needed` — gap twice-observed; candidate mechanisms differ in size and
authority, so the operator chooses before any spec.

**Outcome:** A Learning packet the caller does not persist becomes visibly unpersisted, instead
of looking identical to a persisted one.

**Source:**
Issue #73 ·
[LOOP-001 outcome](archive/2026-08/loop-001-outcome-2026-08-10.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#ack-001-make-a-dropped-learning-handoff-visible)

**Prerequisites:** None — LOOP-001's capture-to-released lifecycle closed 2026-08-10.

**Constraints:** `scripts/learning_ledger.py` and the `learning/` store were retired 2026-09-01;
this item is moot unless the ledger returns.

**Acceptance:** A scenario where a caller receives a packet and stops shows the stop; the
emitting side's contract is unchanged for callers that do route it; no new write authority
granted to a read-only role; adapter parity and deterministic gates green.

**Next action:** Operator rules among three mechanisms (emitter-side pointer plus manifest —
recommended; caller-side lint scan — deferred, trigger-bound; scratch-file write — declined),
then a bounded spec.

#### LEDGER-001 — the promoted set has no absorption or drift coverage

**Status:** `ready` — diagnosis complete from a full 53-record audit; each repair below is
independently landable.

**Outcome:** A lesson recorded as `promoted` is one a reader can trust landed, verified by
something other than manual audit; three specific records are reconciled with the tree, and the
coverage gap that hid them is closed or stated.

**Source:**
[history](archive/2026-09/roadmap-history-2026-09-01.md#ledger-001-the-promoted-set-has-no-absorption-or-drift-coverage)

**Prerequisites:** None. Findings 1 and 2 landed 2026-08-20; findings 3–4 remain.

**Constraints:** `scripts/learning_ledger.py` and the `learning/` store were retired 2026-09-01;
this item is moot unless the ledger returns.

**Acceptance:** Findings 1–2 land their prose with the required reader check, or drop with a
stated reason. Finding 3 records its narrowing. Finding 4 extends drift coverage to terminal
states with a firing test, or states the limitation in `learning/README.md`.

**Next action:** Finding 3 — scope-narrow `lc_36adb3d0` or renew its `review`. Finding 4 —
extend drift coverage to terminal states or document the limitation.

#### GATE-007 — bind a tier to each declared effect, or say one response carries one tier

**Status:** `ready` — review-reported on PR #164; not fixed there because the fix is a
vocabulary decision, not a lint change.

**Outcome:** A response declaring two effects can no longer leave the more dangerous one
unclassified, closing the gap where a Tier 3 deletion could pass a safety eval declared only as
Tier 2.

**Source:**
[homelab live-effect gate decision](decisions/2026-08-29-homelab-live-effect-gate.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#gate-007-bind-a-tier-to-each-declared-effect-or-say-one-response-carries-one-tier)

**Prerequisites:** GATE-006 (landed) — this amends what that decision established.

**Constraints:** EVAL-011 gates whether a behavioral re-measure of either fix would mean
anything.

**Acceptance:** Either (a) `Tier` joins each bound effect set, with agent text, contracts,
`packet_lint.py`, and adapters changed together plus a firing test for a mis-tiered second
effect; or (b) the agent text states one response carries one tier, enforced by `packet_lint`.
The decision record gains the amendment either way.

**Next action:** Decide (a) or (b); both change what the agent emits and owe a behavioral
re-measure.

#### EVAL-011 — a permission-cut session must not be graded as a contract failure

**Status:** `ready` — measured during GATE-006's lane calibration, on the branch head.

**Outcome:** The runner tells a genuine contract failure apart from a turn the harness ended at a
denied tool call, reporting the latter honestly instead of scoring FAIL — today `tier-gate-holds`
scores 1/5 tools-denied vs. 5/5 with `Read` granted.

**Source:**
[GATE-006 outcome](archive/2026-08/gate-006-outcome-2026-08-30.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#eval-011-a-permission-cut-session-must-not-be-graded-as-a-contract-failure)

**Prerequisites:** None — `eval_behavioral.py` already carries `runs_excluded`/`inconclusive`;
this closes the stub case those fields don't yet cover.

**Acceptance:** A turn that ends at a denied tool call with no gradeable response is excluded
and reported, never scored FAIL, with a firing test; the read-only-floor alternative is recorded
as a separate decision with its re-baselining cost.

**Next action:** Decide instrument-first (exclude and report) versus contract-first (read-only
floor); calibration evidence favors doing the instrument first.

#### PORT-002 — second mining round from save-toolkit, the sibling's delta since 2026-07-24

**Status:** `decision-needed` — scoping read done and recorded; operator picks the set before
any graft is authored.

**Outcome:** Lab-portable improvements from `latent-sre/save-toolkit` since the July import land
as capped grafts inside the skills that already own the ground, with no twin this fleet leads on
touched and provenance recorded twice.

**Source:**
[save-toolkit delta scoping](archive/2026-08/save-toolkit-delta-scoping-2026-08-29.md) ·
[sre-agents adaptation backlog](archive/2026-07/sre-agents-adaptation-backlog.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#port-002-second-mining-round-from-save-toolkit-the-siblings-delta-since-2026-07-24)

**Prerequisites:** The operator's pick (Next action); each slice then runs PORT-001's three
blind passes from refreshed `origin/main`.

**Constraints:** No description edit is planned; if one becomes necessary it owes the routing
cluster before/after.

**Acceptance:** Per slice: graft lands inside the owning skill; the scrub list is gone from
landed text; validator and tests green; commit carries attribution, every adapted code file
names its source and license, and the dated adjudication record is extended with the reviewed
commit and renamed repository; verified-skip twins stay byte-unchanged. Closes when every
picked slice merges and the record is linked from `docs/README.md`.

**Next action:** Operator chooses (a) the recommended five candidates, (b) all eight, or (c) (b)
plus filing the PROP-003/EVAL leads as their own items; then open slice 1 (`runbook`).

### Small items

The deliberate lightweight tier: defects and gaps too small for the full item contract, so they
do not leak into session memory or issue lists as a shadow queue. One line each — ID, the
observable fix, and source. No prerequisites and no acceptance section: the fix plus green
deterministic gates closes a line, and closing it means deleting it. A line that turns out to
need prerequisites or acceptance evidence beyond itself graduates to a full item above. A line
naming a GitHub issue **is** that issue's roadmap import under `docs/README.md` rule 7.

- **HOST-012** — Installing this repository as a VS Code plugin loads the canonical Claude
  fleet, which is unsupported. Source: [README.md](../README.md);
  [history](archive/2026-09/roadmap-history-2026-09-01.md#host-012-vs-code-plugin-install-loads-the-canonical-fleet).
- **PROBE-002** — Settled 2026-08-30 as a real, intermittent craft-preload failure (2 passes, 3
  failures across five runs); not caused by GATE-006. Source:
  [GATE-006 outcome](archive/2026-08/gate-006-outcome-2026-08-30.md);
  [history](archive/2026-09/roadmap-history-2026-09-01.md#probe-002-craft-preload-canaries-missing-in-sde-fullstack-spawn).
- **PROBE-006** — A probe leg timeout raises `TimeoutExpired` instead of recording INCONCLUSIVE,
  discarding every later check. Source:
  [GATE-006 outcome](archive/2026-08/gate-006-outcome-2026-08-30.md);
  [history](archive/2026-09/roadmap-history-2026-09-01.md#probe-006-a-probe-leg-timeout-crashes-instead-of-recording-inconclusive).
- **ORACLE-019** — Three oracle constructions remain open after PR #152's four review rounds,
  to be closed with a behavioral batch rather than a fifth static round; LEARN-002 owes that
  batch. Source:
  [history](archive/2026-09/roadmap-history-2026-09-01.md#oracle-019-three-oracle-constructions-open-after-pr-152).

## Deferred decisions

#### GRAPH-004 — typed edge-contract pilot

**Status:** `deferred` — trigger-bound, absorbed from the superseded control-plane proposal.

**Outcome:** One real handoff (builder to reviewer) expressed as a host-neutral typed contract,
with `contract_digest` resolving to it.

**Source:**
[GRAPH-003 adjudication](archive/2026-08/graph-003-adjudication-2026-08-01.md) ·
[AI graph engineering decision](decisions/2026-07-31-ai-graph-engineering.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#graph-004-typed-edge-contract-pilot)

**Prerequisites:** A demonstrated consumer — a second workflow conversion decided.

**Acceptance:** The contract document exists, `contract_digest` resolves to it with a test, the
workflow (if any) consuming it validates against it, and no judgment text lives outside
canonical files.

**Next action:** None until a trigger fires — a second workflow conversion is the only live
ignition.

#### EVAL-003 — capture a comparable full routing anchor

**Status:** `deferred`

**Outcome:** Establish one current, condition-complete routing baseline across all routing
clusters.

**Source:**
[history](archive/2026-09/roadmap-history-2026-09-01.md#eval-003-capture-a-comparable-full-routing-anchor)

**Prerequisites:** Run small watched foreground batches; fix case-design defects before treating
numbers as description evidence.

**Acceptance:** Every artifact records requested/observed model, timeout, CLI version,
threshold, and per-run evidence; no known-invalid artifact is called an anchor.

**Next action:** Decide agent-member grading (evidence-backed default: negatives-only in
routing, agent contracts covered by the behavioral suite), then capture the anchor under
`--clean-room`.

#### RELEASE-001 — add repository release discipline

**Status:** `deferred`

**Outcome:** On the next release-workflow task, add a bounded component for version choice,
changelog, tag, publication, and rollback, without absorbing merge verdicts, CI authoring, or
deployment authority.

**Source:**
[roster expansion design](archive/2026-07/roster-expansion-design.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#release-001-add-repository-release-discipline)

**Prerequisites:** A real plugin or repository release task demonstrates the consumer.

**Acceptance:** Routing cases distinguish release, CI, deploy, and merge-verdict requests; the
component states rollback boundaries; its first use performs the repository's actual version,
inventory, validation, tag, and publication sequence.

**Next action:** Reopen before the next manually orchestrated release; start from `claude plugin
tag --dry-run` and build around what it does not cover.

#### EVAL-004 — verify the accessibility imports behaviorally

**Status:** `deferred`

**Outcome:** Demonstrate that a real UI task loads and applies form wiring or interaction
accessibility guidance and supplies keyboard-pass evidence.

**Source:**
[ECC import review](archive/2026-07/ecc-import-review.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#eval-004-verify-the-accessibility-imports-behaviorally)

**Prerequisites:** A real task involving a form, modal, drawer, custom widget, toast, or async
status.

**Constraints:** Do not manufacture a component solely to close this item.

**Acceptance:** Task packet names the applicable reference and provides keyboard/announcement
evidence; two observed misses trigger a dedicated behavioral contract and definition repair.

**Next action:** Evaluate on the next qualifying UI task.

#### LAB-001 — provide a fallback service compose asset

**Status:** `deferred`

**Outcome:** Supply an annotated service block for a lab with no established compose pattern,
covering pinned image, restart, health, resource, and storage slots.

**Source:**
[skills modernization plan](archive/2026-07/skills-modernization-plan.md) ·
[history](archive/2026-09/roadmap-history-2026-09-01.md#lab-001-provide-a-fallback-service-compose-asset)

**Prerequisites:** An onboarding task demonstrates the target lab lacks a reusable pattern.

**Constraints:** Existing lab conventions always win over this asset.

**Acceptance:** Asset is linked skill-relative from `service-onboard`, contains no
environment-specific defaults, and the validator's orphan/reference checks pass.

**Next action:** Reopen on the first qualifying service-onboarding task.

## Reconciliation record

Reconciled against commit `ab896b2` on 2026-07-28: every item a historical document still called
open was checked against current definitions, scripts, eval cases, and inventory. Detail lives in
each source below, not here; every "Survives" finding is already tracked live above (LAB-001,
EVAL-003, EVAL-004, LABSEC-002, RELEASE-001) or, for LABSEC-001, recorded landed in LABSEC-002.

- **Quality and deep-review findings** — nearly all landed:
  [`archive/2026-07/fleet-quality-review.md`](archive/2026-07/fleet-quality-review.md).
- **Modernization and adaptation items** — landed except LAB-001, EVAL-003 above:
  [`archive/2026-07/skills-modernization-plan.md`](archive/2026-07/skills-modernization-plan.md).
- **ECC residue** — landed except EVAL-004 above:
  [`archive/2026-07/ecc-import-review.md`](archive/2026-07/ecc-import-review.md).
- **Role and governance review** — all six candidates landed:
  [`decisions/2026-07-28-fleet-role-expansion.md`](decisions/2026-07-28-fleet-role-expansion.md).
- **Roster-expansion design branch** — landed/rejected except LABSEC-002, RELEASE-001 above:
  [`archive/2026-07/roster-expansion-design.md`](archive/2026-07/roster-expansion-design.md).
