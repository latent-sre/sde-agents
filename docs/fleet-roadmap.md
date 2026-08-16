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

#### LEARN-002 — close the Learning-contract compliance gap

**Status:** `ready` — the measured residual of the merged LEARN-001 round, plus the six
LOOP-001/REV-001 contracts this docket now owns. The 2026-08-15 paired round landed the three
canonical text repairs and both halves' three-run baselines. What remains is the **nine** numbered
items under **Next action** — grader repairs, two text decisions, an operator ruling, a
two-consecutive-batch measurement, five unsettled LOOP/REV contracts, a bounded harness
investigation into `allowed_tools: []`, two shipped-but-unmeasured skill sentences, the
resultless-session flake, and a reference/skill grammar conflict. Read that list, not this
sentence, before scoping the item: a headline is not an inventory, and this one has already been
wrong twice by lagging the list beneath it.

**Outcome:** (1) Each of the seven behavioral contracts failing 0/3 under the final closed
graders (`self-improve-lifecycle-merge`, `self-improve-promotion-gate`,
`self-improve-canonical-triaged-candidate`, `runbook-disposition-propose`,
`learning-slot-readonly-agent`, `learning-slot-operational-agent`,
`learning-runbook-namespaces`) either holds 3/3 across two consecutive clean-room sonnet
batches or has its grammar amended with a recorded rationale — settling empirically whether
the closed contracts or the skill text carried the defect. No grader is silently loosened.
(2) Each of the six contracts the closed LOOP-001/REV-001 round authored
(`loop-capture-is-not-closure`, `loop-duplicate-merges-provenance`,
`loop-source-pass-is-not-released-pass`, `reviewer-approval-does-not-transfer`,
`verifier-envelope-mismatch-fails-closed`, `reviewer-formal-approval-emits-envelope`) has a
three-run clean-room baseline under recorded conditions and either holds its acceptance rate
or has a grammar/text repair with a recorded rationale — the first-contact single runs in
`evals/baselines/2026-08-10-learn-002/decisions.md` are diagnostic only and do not close this
half. Closing the original seven without settling these six is not closing LEARN-002.

**Source:** [`LEARN-001 outcome record`](archive/2026-08/learn-001-outcome-2026-08-02.md);
live rates in `evals/baselines/2026-08-01-self-improve/final-live/`; the six contracts' first
contact and ownership handoff in the
[LOOP-001](archive/2026-08/loop-001-outcome-2026-08-10.md) and
[REV-001](archive/2026-08/rev-001-outcome-2026-08-10.md) outcome records.

**Prerequisites:** None — the behavioral harness and pinned conditions are ready. Description
edits, if any emerge, owe the overlapping routing cluster before/after per standing law.

**Acceptance:** Per-contract paired before/after behavioral runs under identical recorded
conditions for the original seven; deterministic gates green; the two 2/3-flaky contracts
re-measured alongside; the watch-metrics (Learning-slot `none`-rate, ledger organic-candidate
count) reported at close. **And**, for each of the six LOOP-001/REV-001 contracts: a three-run
clean-room baseline under recorded conditions committed under `evals/baselines/`, plus either
a hold at the acceptance rate or a grammar/text repair with rationale — first-contact single
runs and deferred repairs do not satisfy this clause.

**Next action:** The 2026-08-10 calibration round
(`evals/baselines/2026-08-10-learn-002/`, 76 sessions, decisions.md per case) settled the
pattern-setter question for the original seven: **the closed contracts are right and the skill
text carries the defect** — the packet-grammar literal lives only in `references/`, unreachable
by a Skill-only session, so no grader was loosened. Batch 3 moved 2/10 → 7/10 with three
contracts settled 3/3. Two follow-ups now own the residue on that half: (1) **landed
2026-08-13** — failing-run transcript retention in `scripts/eval_behavioral.py` (`lc_2e549c0b`,
promoted; 22 of 76 sessions were re-buys of text the runner had already read and dropped). A
failing run under `--output-dir` now writes its final text to `failing-run-evidence.json` beside
the benchmark, so the four contracts parked at 1–2/3 can be settled from the next batch's own
artifacts instead of a re-buy; the settling runs themselves are still owed and are T3.
(2) **landed 2026-08-15** — the canonical `self-improve-loop` SKILL.md edits and their paired
measurement ([`2026-08-15-learn-002`](../evals/baselines/2026-08-15-learn-002/), 114 sessions,
`decisions.md` per case). Three text repairs shipped: the `Learning:` value grammar, the
`Provenance:` triad-first grammar (a second defect this round's own before capture surfaced — the
capture template taught `local` as a Provenance value while the canonical block requires the triad
word), and add-vs-merge. The two measured assertions moved 0/9 → 9/9 and 1/9 → 9/9 across graded
runs. **The six LOOP-001/REV-001 contracts now have their three-run clean-room baselines on both
sides**, superseding their first-contact single runs — but that satisfies only the *baseline* half
of their Acceptance clause. The clause also requires each of the six to hold its acceptance rate or
receive a repair with rationale, and five of the six do neither yet, so the clause as written is
**not** met.

What this item still owes, all of it now narrow:

1. **Five filed grader defects**, each already carrying the observed sentence that missed it, in
   `decisions.md` under "Filed, not amended" — two on `reviewer-approval-does-not-transfer`
   (a qualifier the precise answer replaces with the commit SHA; an adjacency-bound
   `fresh review`), and **three** on `self-improve-promotion-gate`: the forbidden promotion pattern
   firing on the retro's own `Trigger:` restatement, the exactly-once `Promotion state:` rule
   counting a backticked echo, and — the one that actually governs its after-side rate — the
   **promotion-refusal positive pattern** missing runs 1 and 3 (`No gate holds, so no promotion…`).
   The first two are before-side observations; repairing only those leaves this contract at most
   1/3, which is why the count was wrong and not merely short. Amending any of them needs
   both-directions proof, per standing law. **The decorated-echo repair's confirmation scope is four
   contracts, not one** — it is also the sole residual keeping `self-improve-lifecycle-merge` and
   `self-improve-canonical-triaged-candidate` at 2/3, and the same shape as
   `learning-slot-operational-agent`'s duplicate `Learning:` field. Validated against only the
   contract it is filed under, it would read as settled while three others still fail on it.
2. **The two learning-slot contracts, whose inherited diagnosis was wrong.** The
   `(proposed recommendation)` abbreviation this item previously carried from 2026-08-10 **does not
   occur** in any of the six after-side runs, so the prompt-side-emphasis repair it named would have
   spent a paid batch on a defect that is not there. Recounted causes, with sentences in
   `decisions.md`: `learning-slot-readonly-agent` (0/3) appends trailing rationale after an
   exact-value field, and once leaves a plain metavariable in `Provenance:`;
   `learning-slot-operational-agent` (1/3) emits a second literal `Learning:` field echoing the
   block, which the passing run omits. Both are unfiled; neither is the abbreviation.
3. **An operator ruling on `reviewer-formal-approval-emits-envelope`** — whether stipulated
   evidence substitutes for seen bytes. Not a grammar problem, and unchanged at 0/3.
4. **The two-consecutive-batches clause** for the seven, which no single round can satisfy.
   `learning-runbook-namespaces-compose`'s 3/3 → 2/3 drop is dispositioned as variance at n=3 and
   is the first thing the next batch re-checks.
5. **Five of the six LOOP-001/REV-001 contracts are baselined but unsettled**, and each still owes
   a hold or a repair with rationale before its half closes — they are named here because this file
   is the only live tracker, and a remainder list that omits them lets a later session close
   LEARN-002 with them red: `loop-capture-is-not-closure` (0/3), `loop-duplicate-merges-provenance`
   (0/3, GRAMMAR causes quoted in `decisions.md`), `loop-source-pass-is-not-released-pass` (1/3),
   `reviewer-approval-does-not-transfer` (0/3, item 1 above), and
   `reviewer-formal-approval-emits-envelope` (0/3, item 3 above). The sixth,
   `verifier-envelope-mismatch-fails-closed`, holds at 3/3 — with the caveat in item 6.
6. **`allowed_tools: []` does not deny tools**, discovered in the PR #140 review round and verified
   by reading `tool_use` blocks from a re-run: the runner turns an empty allowlist into `--tools ""`
   and actual denial comes from `disallowed_tools`. So `verifier-envelope-mismatch-fails-closed`
   passed with `Glob`/`Grep` available, and its HOLD must not be cited as no-tool evidence. Wider
   reach, and the reason this is listed rather than filed away: `AGENTS.md` uses a Claude contract's
   empty `allowed_tools` as the eligibility test for the Codex behavioral lane, on the reading that
   it disables tool execution. That rule currently rests on a property the harness does not enforce.
   Owed: a bounded check across every case declaring an empty allowlist, and a decision on whether
   the runner should reject the combination outright.
7. **Two SKILL.md sentences ship unmeasured.** Every after-side artifact binds
   `plugin.git_head` to `c8312b3`, and two review-driven amendments landed after it: the no-signal
   literal (`Learning: none — no reusable signal`, replacing a `<reason>` slot the linter rejects)
   and the `Destination:` clarification. What survives that gap is exact, not a judgement call —
   the sentences governing both *measured* assertions are byte-identical between `c8312b3` and the
   shipped commit, so `0/9 → 9/9` and `1/9 → 9/9` remain evidence for the shipped bytes. The two
   amendments themselves have **no** behavioral evidence. The no-signal one is the live risk, since
   it changes what a session emits for every no-signal scan; the next batch measures it, and until
   then this fleet's own exact-artifact gate is unsatisfied for those two sentences.
8. **The `Claude exited 1` resultless-session flake has a live owner here, and this is it.** It hit
   five before-side and four after-side case batches, never at concurrency 1. The runner grades a
   resultless session as a contract failure, so an operator who does not notice publishes a
   corrupted rate — it converted three working contracts into apparent 0/3s in this round alone.
   Interim workaround, used throughout this round: re-run the affected case at `--concurrency 1` and
   discard the flaked artifact rather than grading it. Owed: a root cause, and a decision on whether
   `eval_behavioral.py` should classify a resultless session as `INCONCLUSIVE` rather than a
   failure — the 2026-08-10 round filed that same runner-design question and it is still open.
9. **`references/retro-protocol.md` teaches a Provenance grammar the linter rejects.** Line 100
   still renders `Provenance: <verified/sourced/unverified, source, and freshness>` — the comma form
   — while `packet_lint` requires the triad word followed by an em dash, `->`, or a colon, which is
   the grammar `SKILL.md` now states. A skill-only session is fixed and a `Read`-capable session
   that opens the linked template gets the contradiction, so the repair reached the measured path
   and left the unmeasured one carrying two conflicting contracts. Owed: align the canonical
   template and regenerate host copies. Deliberately **not** taken in the round that found it —
   it is a shipped-behavior change, and making it would have added a third skill sentence with no
   behavioral evidence to item 7's list rather than shrinking it.

Two results are recorded against interest and must not be re-reported as wins: the add-vs-merge
repair has **no measured effect** (its target case was already 3/3 before the edit, on model
drift), and two contracts improved between 2026-08-10 and this round on drift alone.

**Rides this item (PROP-002 deferrals, 2026-08-13).** Three proportionality trims sit in files
this item is already paying to re-measure, so they ride its runs rather than buying their own:
`runbook`'s owner and escalation/stop slots and `references/example.md`'s two-role framing, and
`self-improve-loop`'s canonical candidate block (in SKILL.md and
`references/discovery-routing.md`) and the five retro types in `references/retro-protocol.md`.
Line numbers are deliberately omitted here: the scan record's citations bind commit `c38592c` and
say so, while this file is the live tracker, where a line number rots silently as the file moves —
`self-improve-loop/SKILL.md` has already shifted 37 lines since that scan.
They are optional to this item's acceptance — closing LEARN-002 does not require making them — but
they must not be made *without* its measurement, and **closing this item owes each ride-along a
disposition**: worked, re-homed to a named live item, or dropped with reason, recorded in the
outcome record. A silent close would strand them in archive evidence outside this tracker — the
roadmap is the only live owner a deferral can have (PR #133 review finding). The disposition and reasoning are in
[`prop-002-scan-findings-2026-08-13.md`](archive/2026-08/prop-002-scan-findings-2026-08-13.md).
Note the constraint that record's Correction 8 establishes before touching `runbook`: its propose
grammar cannot move to `references/`, because the contract that grades it runs skill-only and has
no `Read`.

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

#### CTX-002 — fit the model-visible skill listing inside the 8,000-char host budget

**Status:** `ready` — pass 1 of the three-pass context remediation (CTX-002 listing layer,
CTX-003 invocation layer, CTX-004 environment and enforcement); passes 1 and 3 share no files
with pass 2 and may run independently of it.

**Outcome:** The fleet's model-visible listing (non-DMI skills plus workflows, currently ~11.9k
chars across 19 entries) fits the 8,000-char worst-case budget with stated headroom — which
fully fixes Codex (whose 8,000 budget carries no bundled-skill share) and maximizes surviving
entries on 200k-context Claude hosts. Bundled skills are budget-exempt and charged first, so
trimming alone cannot guarantee full survival where the bundled share is large (measured
~5.5–6k chars in the investigation container: a ~3.9k-char trimmed listing still lost 8 of 18
descriptions at the default budget) — the settings-side completion and the enforcement
promotion are CTX-004's remit, gated on this trim landing first.

**Source:** [2026-08-16 skill-listing investigation](archive/2026-08/skill-listing-investigation-2026-08-16.md)
(CLI 2.1.233 binary constants; live listing state by model; behavioral routing A/B — the
`continuous-improvement` positive fired 0/2 with a bare name and 2/2 with the description
restored; mitigation calibration — fraction 0.02 measured partial, 0.05 full; trim simulation).
Platform facts recorded in `skills/prompt-craft/references/claude-code-frontmatter.md`; the
LADDER-002 investigation's "full description visible at 2.1.231 despite ~11k listing volume"
observation is explained by the window scaling — that probe ran on a large-window model.

**Prerequisites:** none — but every description edit owes the standing paired routing-eval
discipline, so the work batches naturally with any LADDER-002 repairs the operator buys.

**Acceptance:** Paired before/after routing runs for the overlapping clusters of every edited
description (`scripts/eval_baseline.py` may satisfy the 'before' side); doctor check reporting
`pass` with headroom on the trimmed tree; regenerated adapters. A live listing probe on a
200k-window model after the trim, recording how many entries survive at the default budget —
survivors are maximized here; full survival on bundled-rich hosts closes in CTX-004.

**Next action:** Trim the three largest entries first — `self-improve-loop` (951-char
description), `deep-review` (~940-char workflow meta description), `onboarding-map` (873) — the
listing needs ~3.9k chars cut. The consuming-repo mitigation available meanwhile is
`skillListingBudgetFraction: 0.05` in `.claude/settings.json` (verified full restoration in the
investigation container; 0.02 measured partial there — calibrate with a live listing probe, not
by assumption).

#### CTX-003 — shrink the per-spawn preload footprint without hollowing the probe's proof

**Status:** `ready` — pass 2 of the three-pass context remediation; independent of CTX-002 and
CTX-004, and the heaviest pass (behavioral-contract rounds), so it runs when there is appetite
for that instrument rather than blocking the other two.

**Outcome:** The per-spawn context cost of preloading drops measurably — `sde-fullstack`
currently loads ~12.1k tokens of skill bodies (48,317 bytes across five preloads) on top of its
own ~4.9k-token body, and `self-improve-loop` (largest body: 18.1k bytes, 272 lines, ~4.5k
tokens) is preloaded by three agents that already carry the Learning closeout stanza inline —
with behavioral contracts proving the slimmed bodies still deliver what the fat ones did.
References stay the on-demand layer (probe-verified 2026-08-16: conditional reference reads
work; preloading takes the SKILL.md body only).

**Source:** [2026-08-16 skill-listing investigation](archive/2026-08/skill-listing-investigation-2026-08-16.md),
"Preload and body footprint" — byte counts, the redundancy of the preloaded Learning protocol
against the agents' inline closeout stanzas, and the probe-canary constraint.

**Prerequisites:** none mechanically — but the probe-canary constraint is a design decision
inside the pass, not an accident to stumble into: `scripts/probe_plugin.py` asserts craft-skill
canary content is *preloaded* by quoting it from the body, so a body-to-reference move either
keeps the canaries in the body or moves them deliberately with a probe update in the same
change. A silent move fails the probe — or worse, quietly hollows out what "preloaded" proves.

**Acceptance:** Before/after behavioral-contract runs (`scripts/eval_behavioral.py`) for every
agent whose preloaded set changed; the probe green with its canary assertions intact or
deliberately migrated; regenerated adapters; the doctor and validator green throughout. Byte
deltas recorded per skill in the closing record.

**Next action:** Restructure `self-improve-loop` first — compact loop plus closeout contract in
SKILL.md, full lifecycle protocol to a reference — because it pays three times per fleet-heavy
session and its behavioral contracts (the learning-closeout cases) already exist as the
instrument.

#### CTX-004 — lock the context wins in: settings lines, validator promotion, Copilot cap

**Status:** `ready` — pass 3 of the three-pass context remediation; the promotion step is gated
on CTX-002, the other two deliverables are not.

**Outcome:** Three locks, one per discovered cliff. (1) Consuming lab repositories carry a
probe-calibrated `skillListingBudgetFraction` line in `.claude/settings.json` (0.05 verified
full in the investigation container; 0.02 measured partial — each environment calibrates by
live listing probe because the bundled share differs). (2) The doctor's
`repository.skill-listing-budget` warning is promoted to a `validate_fleet.py` hard rule with a
fixture that fails without it, so listing regrowth fails T0 instead of failing silently at
runtime — honest only once CTX-002 makes the tree fit. (3) A generated-adapter size tripwire
warns before GitHub's 30,000-character `.agent.md` hard cap: `homelab-platform.agent.md` is at
24,631 (82%) and that body is the fleet's fastest-growing; today the first signal would be a
host rejecting the profile.

**Source:** [2026-08-16 skill-listing investigation](archive/2026-08/skill-listing-investigation-2026-08-16.md)
(mitigation calibration table; the Copilot cap under "Preload and body footprint").

**Prerequisites:** CTX-002 for the promotion step only.

**Acceptance:** Settings lines landed in the lab repositories with each environment's live-probe
calibration recorded; the promoted validator rule with its failing fixture; the Copilot-cap
tripwire with a test that makes it fire (a synthetic body over threshold), thresholds stated in
the rule's message with the consequence named; regenerated adapters and green tiers.

**Next action:** The Copilot-cap tripwire — it is prerequisite-free, small, and the 82%
measurement is already committed evidence.

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

#### HANDOFF-001 — evidence-bound onboarding handoff packet

**Status:** `active` — Claude manager-owned amendment authorized by the operator 2026-08-11;
original spec approved 2026-08-09. The REV-001 sequencing condition is met: that round closed
2026-08-10
([outcome record](archive/2026-08/rev-001-outcome-2026-08-10.md)) with the envelope idiom
settled — `candidate_sha`/`base_sha`/`tree_oid` and the six-field approval envelope.

**Outcome:** Onboarding work delegates through one manager-owned, digest-bound work order whose
sections carry failed assumptions, verification-method validity, the executable-transport contract,
irreversible postconditions, authority lifetimes, inventory invariants, and secret-safe capture
— the builder returns only an accepted/input-required receipt, and the known-failed-assumption
fixture is graded from resulting state rather than a second prose copy.

**Source:** [`HANDOFF-001 spec`](superpowers/specs/handoff-001-onboarding-handoff-packet.md) and
its [paired lean plan](superpowers/plans/handoff-001-plan.md);
issue #60 with three-occurrence recurrence evidence and its field-derived section list.

**Prerequisites:** None — REV-001's idiom is settled in source (merged in PR #109). The 1.7.3
release stamp is REL-173's evidence, not a gate on this item.

**Acceptance:** The spec's list — issue #60's paired evals plus the three closeout fixtures.

**Current evidence:** The first Terra/medium round remains preserved under
[`evals/baselines/2026-08-11-handoff-001`](../evals/baselines/2026-08-11-handoff-001/): it proved the
producer at 3/3 but left five strict cases unresolved, which triggered this amendment. Those
artifacts are historical for their exact no-tool cases and are not regraded as Claude functional
evidence. Commit `dc02bed` replaces the builder echo with manager-owned work-order identity and
small receipts. The paired evaluator change keeps six cases by replacing the reviewer duplicate
with a digest-mismatch receipt and a declarative builder fixture. Its trusted verifier is
byte-checked, grades captured regular-file bytes, and records artifact hashes/results. The
digest-negative oracle now requires one exact hash command and correlated result plus an unchanged
seeded workspace, closing the prior receipt-only false green. Red-before-green controls, T0, the
behavioral-evaluator module, the full suite, and `claude plugin validate . --strict` all passed at
`dc02bed` (107 evaluator tests, 666 across 30 modules **at that commit** — GRAPH-002 and this
round's additions have since moved the suite to 837 across 33 modules, so re-run rather than
compare against those figures).

The plan's three-session Claude diagnostic **has now run** — operator-approved model
`claude-sonnet-5`, candidate `7074d8d`, CLI 2.1.233, one run each, artifacts and full reading in
[`evals/baselines/2026-08-15-handoff-001-sonnet5/`](../evals/baselines/2026-08-15-handoff-001-sonnet5/decisions.md).
One of the three returned a usable result: the producer passed 1/1. Both builder cases are
recorded **VOID, not FAIL** — `scripts/eval_behavioral.py:502` grants case tools with `--tools`,
which bounds the tool *surface* while granting no *permission*, so on CLI 2.1.233 the session's
Bash calls fall to the sandbox, which admits `sha256sum`/`grep`/`ls` and refuses interpreters. The
functional case's mandated `python -I acceptance.py` and the digest case's one prescribed hash
command therefore never executed (`hash_command_observed: false`). Two same-prompt sessions
differing only in that flag reproduce it exactly. What the void sessions still show: the
functional case's end state was independently graded `acceptance: PASS` by the trusted verifier,
and the digest case left `workspace_unchanged: true` with no edit and no `accepted` receipt issued
on trust. HANDOFF-001 remains unaccepted — the plan gates a paired capture on "exact hash-command
evidence", which does not exist.

**Next action:** The runner grant is **fixed** (2026-08-15): `run_session` now passes `--tools`
for the surface bound its comment argues for **and** `--allowedTools` for permission, with a test
proven to fail without it by mutation; an empty allowlist deliberately gets no permission flag,
since `--tools ""` leaves nothing to permit. T0, the module, T1 (836 tests, 33 modules), and
`claude plugin validate . --strict` are green. What remains is the paid half: **re-run the two
void cases** — `handoff-builder-applies-work-order` and `handoff-builder-rejects-digest-mismatch`
— under recorded conditions, and confirm the mandated `python -I` commands now execute
(`hash_command_observed: true` is the digest case's tell). **This is not only a HANDOFF-001
repair:** five
behavioral cases grant `Bash` (`packet-slots-builder`, `ladder-report-not-absorb`,
`verifier-fails-honestly-no-product-edit`, and the two here), so any stored rate for the other
three may have measured the permission gate rather than the contract and should be re-read before
being cited. The fix moves evaluator bytes and so invalidates comparison with the 2026-08-15
artifacts, the producer result included. Only after the two re-runs are sound should a full paired
capture be proposed. Do not compare Claude results with the archived Terra approximation.

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

**Prerequisites:** the spec's Phase 0, still blocking; the
[LANE-001 spec](superpowers/specs/lane-001-codex-onboarding-discoverability.md) owns both
one-liners and their exact form, and its 2026-08-11 amendment note records the one mechanical
change they have had. Read them there rather than from this paraphrase: `codex --version` and the
unmanaged-TOML check, both from the SEC-01 Linux host, with **empty output as the pass** — the
exit status is not the signal, since `grep` returns 1 for no match and 2 for an unreadable path.
That distinction is the point of the amended form: absent directory is a clean pass through the
`-d` guard, while a genuine read error still reaches stderr instead of being silenced into the
same empty output. No codex-cli version has ever been measured on that host. The only Codex CLI
version this repository
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

**Rides this item (PROP-002 deferral, 2026-08-13).** `onboarding-map`'s description restates "this
authorizes nothing" a fourth time; the body's three other copies were reconciled in `eb53758`, but
the description drives routing and this skill sits in the `homelab-ops` cluster whose paired
'before' capture this item owes at merge base `4fef0ce`. Trimming it first would invalidate that
side. Optional to acceptance; not to be made without the capture — and this item's closeout owes
the ride-along a disposition (worked, re-homed to a named live item, or dropped with reason)
rather than a silent close that strands it in archive evidence.

#### LADDER-002 — decide the eng-ladder description round

**Status:** `decision-needed` — the diagnosis is done; which repairs (if any) to buy is the
operator's ruling.

**Outcome:** Each of the LADDER-001 capture's two under-firing modes has its measured repair, or
a recorded decision not to buy one — with the instrument fixed to measure what it claims.

**Source:** [`LADDER-001 outcome record`](archive/2026-08/ladder-001-outcome-2026-08-14.md)
(3/3 / 0/3 / 0/3 mode split), diagnosed by the
[2026-08-14 investigation](archive/2026-08/ladder-002-investigation-2026-08-14.md): schema
cleared by probe (full description visible at CLI 2.1.231 despite the fleet's 11,260-char
listing volume exceeding the reported ~8k budget), the assess 0/3 shown to be an **eval-case
artifact** (dangling "this change" referent in the runner's empty cwd — the mode fires when a
referent exists and correctly asks-and-names-the-skill when not), and the consult-fork 0/3
consistent with **do-the-work bias** as the leading hypothesis (one directional probe performed
the consult's substance inline — deliberate fork treatment, deferred execution, operator gate —
with zero invocations). The hypothesis stays provisional either way: the behavioral port in
half (b) validates the *verdict's content* once the component runs — reachability is the routing
suite's question, so no behavioral result confirms why the routing positive failed. The Group 4
rescan's upheld Mode 3 finding rides here unchanged.

**Prerequisites:** None on the capture host — `eval_baseline.py evals/routing/ladder.json
--model sonnet --clean-room` resolves `evals/baselines/2026-08-14-ladder/benchmark.json`
`REUSABLE` there. The reuse is identity-bound, not unconditional: the stored evaluator identity
pins the runtime (CPython 3.11.15 recorded), so a host on another Python reports
`STALE: diverged on evaluator` and owes either that runtime or a fresh 'before' capture before
any paired comparison.

**Acceptance:** For each half the operator elects: (a) **Mode 3 trim** — the rescan's remedy is
description **plus** body: remove the growth-feedback clause from the description and the body's
Mode 3 section in the same delta (a description-only trim would close this item while the
duplicate stateless remit survives in the body). Electing this half is a values call, not a
dead-code removal: review named the candidate reader the upheld finding does not cover — the
human operator, whose own diffs Mode 3 could assess at a ladder bar, a consumer neither
`self-improve-loop` nor `prompt-engineer` serves — so the ruling weighs that route's worth
against its per-session description surface. **The cluster cannot witness this trim as it
stands**: `evals/routing/ladder.json` carries no Mode 3 growth-feedback positive, so a paired run
on today's cases would report identical rates while never exercising the removed route. The
trim's measurement therefore starts by authoring a targeted Mode 3 positive (a body-of-work
growth-feedback prompt), capturing a fresh 'before' that includes it, then making the
description-plus-body edit and the 'after' — the stored 2026-08-14 baseline cannot serve as this
half's 'before' (its case bytes lack the route) and stands only as the historical anchor. In the
after run, negatives hold their forbidden sets at 0% fire, the new Mode 3 positive's silence is
the *expected* result of the trim, **and the surviving positive modes show no unexplained
regression against the paired before** — the suite's own protocol treats a positive's rate
*drop* as the load-bearing signal, so a drop is dispositioned (explained as variance with the
runs to show it, or repaired) before this item closes on the trim. The closeout also
**dispositions the measurement-only Mode 3 case** once the paired result is stored: retire it,
or convert it to a negative boundary asserting the trimmed route stays silent — left as a
positive it would grade every future ladder run permanently red and blur real regressions. **Ordering when both halves
are elected:** every elected case-bytes change (the Mode 3 positive here, the assess rewrite in
half (b)) lands **before** the single fresh 'before' capture on the revised cases, and the
description-plus-body edit lands between that 'before' and the 'after' — case edits after the
'before' stale it through `eval_baseline.py`'s exact `eval_sources` identity, and an unordered
session can spend the full T3 batch and produce no valid comparison. (b) **Instrument repairs** —
rewrite `pos-engladder-assess` to carry a small concrete diff inline so the mode can fire in an
empty cwd, and port the consult-fork calibration to a behavioral contract grading the verdict's
content — builder-owned, the named principal consult marked **required** (optional/advisory
consult wording fails the case: "optional escalation" is the exact issue #66 miscalibration this
contract exists to reject), and no wholesale re-owning. The routing positive is **annotated,
not retired by default**: it is the only routing assertion for the bare consult-fork shape, so
removing it would leave no active instrument recording the reachability gap the behavioral case
cannot test — retiring it takes an explicit recorded decision accepting that unresolved
reachability failure. Case authoring is offline, the re-measure is T3 and starts a new
case-bytes lineage. Success is defined per instrument, not by having run the sessions: the rewritten assess
case passes at the recorded threshold (0.5 — at three runs, 2/3 or better; a 1/3 "nonzero" is
still a failing positive), and the new behavioral contract holds across **three runs**
(`--runs 3` stated because `eval_behavioral.py` defaults to one — a single lucky pass is a
smoke test, not the promised measured repair) — or the
experiment that falsified the proposed repair is recorded as its explicit disposition. A repeat
0/3 or a red contract closed silently would satisfy the letter of a run-only acceptance while
delivering none of this item's promised outcome. A description rewrite for the assess mode is explicitly **not** indicated — the
investigation cleared the phrasing for both measured failures. Electing neither half closes the
item as a recorded decision with the reason.

**Next action:** Operator ruling on which half, if either, to buy.

#### ACK-001 — make a dropped Learning handoff visible

**Status:** `decision-needed` — the gap is twice-observed, but the three candidate mechanisms
differ in size and authority, so the choice is the operator's before any spec is authored.

**Outcome:** A Learning packet the caller does not persist is *visibly* unpersisted. Today a
persisted packet and a dropped one produce identical-looking output, so the drop is discoverable
only by auditing the destination file afterward.

**Source:** Issue #73 — the 2026-08-03 26-dispatch SDD run (five canonical packets emitted by
`code-reviewer`, all five silently discarded, recovered only because the operator asked) and its
2026-08-09 comment (a second, differently shaped run: 8 packets, 3 dropped — and
`self-improve-loop` was itself invoked, emitted three triaged blocks, and those were not persisted
either, so reaching the loop is not the missing step). Ledger candidate `lc_50297f97`
(proposed/add, two occurrences). The issue's other asks are already disposed: the args contract and
its deliberate unsteerability ship in the workflow description (issue #63), the repro
measured-vs-reasoned calibration rides REV-001 as `lc_2c04ead3`, the cross-task config-semantics
lesson rides it as `lc_90dd8dc7`, the string-presence contract-test lesson promoted as
`lc_7d0844a0`, the slot-competition half got the operator's 2026-08-10 configuration relief, and
the branch-final-gate and convergence-signal lines landed in the workflow description with this
import.

**Prerequisites:** None — LOOP-001's capture-to-released lifecycle closed 2026-08-10
([outcome record](archive/2026-08/loop-001-outcome-2026-08-10.md)); this item sits upstream of
that lifecycle's first state and can now be designed without a concurrent edit to the same
skill text. The 1.7.3 release-tail evidence now lives in that archived closeout, not in this
live tracker.

**Acceptance:** A scenario where a caller receives a packet and stops shows the stop; the emitting
side's contract is unchanged for callers that do route it; no new write authority is granted to a
read-only role; adapter parity and the deterministic gates green.

**Next action:** Operator rules among three mechanisms, then a bounded spec. (1) Emitter-side
pointer in the verdict line plus an end-of-loop manifest of packet identifiers, destinations, and
dispositions — **recommended**: prose-only, and the only option that helps a caller running another
plugin's loop. (2) A caller-side `scripts/packet_lint.py` mode scanning a transcript or ledger for
`Learning: candidate` blocks with no recorded disposition — **recommended: defer, trigger-bound**;
no coordinator transcript artifact exists here to consume, and a mechanism without a demonstrated
consumer waits. (3) Agents writing packets to a well-known scratch file — **recommended: decline**;
that is the substitute store `self-improve-loop` forbids for foreign repositories, and it invents a
write authority read-only roles do not hold.

### Small items

The deliberate lightweight tier: defects and gaps too small for the full item contract, so they
do not leak into session memory or issue lists as a shadow queue. One line each — ID, the
observable fix, source. No prerequisites and no acceptance section: the fix plus green
deterministic gates closes a line, and closing it means deleting it. A line that turns out to
need prerequisites or acceptance evidence beyond itself graduates to a full item above. A line
naming a GitHub issue **is** that issue's roadmap import under `docs/README.md` rule 7.

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
call). SAFE-003 (closed 2026-08-10,
[outcome record](archive/2026-08/safe-003-outcome-2026-08-10.md)) is no longer a trigger: its
2026-08-09 ruling chose document-and-enforce over the resolver path, so nothing there now needs
a contract document to resolve to.

**Acceptance:** The contract document exists, `contract_digest` resolves to it with a test, the
workflow (if any) consuming it validates against it, and no judgment text lives outside
canonical files.

**Next action:** None until a trigger fires; with SAFE-003 ruled away from the resolver, a
second workflow conversion is now the only live ignition.

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
   (2026-07-29, phase 1 of this item). The
   [archived isolation outcome](archive/2026-07/verification-round-outcomes-2026-07-29.md) showed every eval session had
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
