# PROP-002 proportionality scan — full findings record (2026-08-13)

**Provenance.** Four parallel read-only scanner lanes (repository-investigator role, Opus), each
covering five skills — full SKILL.md plus every `references/` and `assets/` file — hunting
enterprise gates and ceremony disproportionate to a single-operator home lab. Scanned bytes:
main at `c38592c` (all file:line citations below bind those bytes; the round's fixes moved lines
in six files afterwards). Severity is scanner judgment, unmeasured against session cost:
HIGH = actively harmful friction, MEDIUM = wasted ceremony per invocation, LOW = vocabulary only.
The scan brief excluded homelab-platform's tiered change authority (deliberate design, PROP-001).

**How to read this record.** Findings marked **[FIXED]** were resolved in PR #132 (commit noted).
Findings marked **[OVERTURNED]** were checked against liveness evidence and rejected — a later
session must not re-apply them; the evidence is in the Corrections section. Findings the per-skill
notes below still call "open" were the PROP-002 backlog, and **that backlog is now closed**: the
`Backlog disposition` section at the end of this file dispositions every one of them as worked,
overturned, deferred trigger-bound, or dropped. Read the per-skill "open" markers as the state at
scan time and that section as the outcome; nothing here is a task list.

## Verdict table

| Skill | Verdict | Disposition |
|---|---|---|
| root-cause, prompt-craft | right-sized, zero findings | — |
| lab-audit, security-audit, restore-drill | right-sized, LOW residue | open (LOW tier) |
| host-onboard, postmortem, code-craft, observability | right-sized, LOW–1 MEDIUM | open |
| lab-incident | over-sized in places | HIGH **[FIXED]**, LOWs open |
| upgrade-campaign, onboarding-map, frontend-craft, ci-actions, eng-ladder | over-sized in places | open |
| backend-craft, service-onboard | over-sized in places, 1 HIGH each | HIGHs **[FIXED]**, MEDIUMs open |
| runbook | enterprise-shaped | open (largest backlog item) |
| sre-tool | enterprise-shaped | HIGHs **[FIXED]**, MEDIUMs open |
| self-improve-loop | enterprise-shaped | HIGHs **[FIXED]** as prose; mechanisms **[OVERTURNED]** |

## Group 1 — lab operations

Scanner proved its detector first: a sweep for
`stakeholder|change advisory|maintenance window|on-call|pager|ticket|SLA|incident commander|escalat|audit trail|regulat|multi-tenant|multi-region`
returned zero hits (control term `operator`: 8 hits); `compliance` appears once, negated.

**lab-audit — right-sized.**
- `references/checks.md:101` LOW — "the ledger's keeper" implies a ledger owner distinct from the
  operator; the ledger itself is earned (check 7 needs the prior audit's row).
- `references/checks.md:24` LOW — "or justify the exception in writing" — exception-management
  register; the useful form at home is a repo comment.

**lab-incident — over-sized in places.**
- `SKILL.md:79` MEDIUM-edging-HIGH **[FIXED `70747b8`]** — "Every incident, including near-misses
  → postmortem." Unconditional write-up phase; upgrade-campaign carried the correctly conditioned
  twin. Now conditioned on recovery-wasn't-obvious / recurred / gap-worth-fixing. Parent paraphrase
  in `agents/homelab-platform.md` aligned in `d28fb6b` (Codex review finding).
- `SKILL.md:63` LOW — "You are writing the postmortem's timeline right now" justifies the note by
  an organizational artifact; the memory-will-smooth-it clause carries it alone.
- `SKILL.md:71` LOW — "downgrade the situation from 'outage' to 'follow-up'" — status-taxonomy
  vocabulary with no status board.
- `SKILL.md:48` LOW — "serve a maintenance page" — a comms artifact whose audience is the person
  typing.
- `references/golden-signals.md` — zero findings, purely technical.

**security-audit — right-sized.**
- `references/secrets.md:45` LOW — "who can rotate it" — role-separation question whose answer is
  always the operator; the other clauses (what breaks, ever rehearsed) are load-bearing.
- `references/secrets.md:32` LOW — "everyone with read access to observability" assumes an
  audience wider than one; the underlying grep-for-token-shapes check is sound.

**upgrade-campaign — over-sized in places (mildly).**
- `SKILL.md:72` LOW — postmortem-as-campaign-output; already half right-sized (conditions on
  non-obvious recovery, names the absent pager).
- `SKILL.md:39` LOW — "Majors get their own session and their own approval" — a second approval
  concept atop the tier structure that already governs each apply (may read as tier routing).
- Step-count audit: 19 mandatory items for "update everything"; 17 judged risk-earned
  (rollback-first, digest pins, one-way doors, backups, stop-on-first-failure) — not findings.

**restore-drill — right-sized.**
- `SKILL.md:11,32` LOW — RTO used twice, but as a measured number, never a negotiated target;
  arguably earned.

## Group 2 — onboarding and docs

**onboarding-map — over-sized in places (marginal).**
- `SKILL.md:3,7-10,23-30,32-36` MEDIUM — "this authorizes nothing" restated four times in 47
  lines: description, opening, the four-states table's authorizes-column, closing. One sentence
  covers the risk.
- `SKILL.md:23` LOW (judgment call, PROP-001-boundary) — the mandatory four-state declaration
  (Discovery/Recommendation/Activation/Execution) layered on a skill whose payload is
  "host first, then the service."

**host-onboard — right-sized.**
- `SKILL.md:60` LOW — per-apply "approval evidence" in the packet: an audit trail whose only
  reader granted the approvals seconds earlier (adjacent to deliberate tier design).
- `SKILL.md:11-20` LOW — 10-line authority preamble near-verbatim duplicated in
  service-onboard:10-18; four restatements of one rule, ~16% of the file.

**service-onboard — over-sized in places.**
- `SKILL.md:35-57` HIGH **[FIXED `13f0977`]** — step 7 restated runbook's full 15-item contract
  inline (34% of the file) and then routed to `sde-agents:runbook`; undeclared paraphrase under
  the owned-conventions rule. Now delegates with declared precedence.
- `SKILL.md:40,44,51,52` MEDIUM **[FIXED with the above]** — four of those items assumed org scale
  (owner/escalation route, authority/approvals, notification route; escalation required twice).
  Resolved for this file by the delegation; the slots themselves remain in runbook (below).
- `SKILL.md:61-62,66-67` MEDIUM — packet requires three parallel verified/unverified/n-a lists
  plus per-gap "named owner and handoff" where every handoff destination is the reader.
- `assets/lab-profile.template.md` — right-sized, no findings ("Fill every slot or delete it").

**runbook — enterprise-shaped.** The largest open backlog item.
- `SKILL.md:32-73` MEDIUM — the `propose` gap packet is a 42-line closed grammar (27% of the
  file): five exact lines, two 8-value positional enums, an owner-id regex, path rules excluding
  `.`/`..` and Windows device basenames. **Live consumers**: `scripts/packet_lint.py`,
  `scripts/eval_behavioral.py`, `evals/behavioral/contracts.json`, `tests/test_packet_lint.py` —
  and packet_lint runs at eval time, not in live sessions. Remedy is relocation to a
  `references/` file loaded on the propose path — never deletion. Re-run the runbook-related
  behavioral contracts after moving it.
- `SKILL.md:100,112` MEDIUM — mandatory Owner ("team or person… contact/escalation route") and
  Escalation/stop ("handoff destination") slots — filled performatively in a one-person lab.
- `SKILL.md:54` LOW — `platform-sre` / `platform.sre+oncall@example.com` as the canonical owner
  examples teach that owners are teams with rotation addresses.
- `SKILL.md:104` LOW — "approvals" as a mandatory runbook slot when the approver is the reader.
- `references/example.md:55-56,23,48` MEDIUM — distinct "service owner" and "storage owner" roles
  for one Postgres container; "admission gates" register for "check your backup first."

**postmortem — right-sized.**
- `assets/postmortem.md:3` LOW — "Status: draft | final" lifecycle on a document only its author
  reads.
- `SKILL.md:39` LOW — two mandatory went-well/went-poorly lists (retro-meeting shape; capped at a
  line each, and the went-well prompt has real value solo).

## Group 3 — engineering craft

**backend-craft — over-sized in places.**
- `references/api-design.md:63-65` HIGH **[FIXED `0d5fe31` + `c647046` + `d28fb6b`]** — CI
  breaking-change detector (oasdiff) mandated for every spec change; whole payoff assumes
  consumers you can't coordinate with. Fixed by defining "published" (deploy-atomicity keyed,
  already-loaded-client caveat) — and, per Codex review, the boundary now lives in the winning
  file (SKILL.md:27) since api-design.md declares SKILL.md wins on conflict.
- `SKILL.md:27` MEDIUM **[FIXED `d28fb6b`]** — dual-version running + Sunset protocol +
  principal-engineer escalation for any break; now scoped to published surfaces.
- `references/api-design.md:61-62,51-52` MEDIUM — deprecation-protocol and error-codes-as-contract
  bullets ("an outage you scheduled for someone else" — someone else does not exist); now
  conditioned wholesale by the published-surface definition, residual register open.
- `references/database-reliability.md:33-35` MEDIUM — unconditional "**Every** migration is
  expand → migrate → contract, each phase ships separately" — three deploys and a dual-write
  window for one column; a lab service tolerates a 20-second restart. Needs the household
  carve-out (observability's register). Open.
- `SKILL.md:67` MEDIUM — mandatory contract-testing layer against the OpenAPI spec, justified by
  producer/consumer drift between parties who sync in one commit. Open.
- `SKILL.md:58` + `references/consuming-apis.md:12` MEDIUM — mandatory circuit breaker per
  upstream plus a test that it opens; timeouts and bounded retries carry the value at one-caller
  volume. Open.
- `SKILL.md:52` LOW — publishing X-RateLimit budget headers for third-party clients the operator
  wrote. `references/api-design.md:56-57`, `references/database-reliability.md:47-48` LOW —
  Hyrum's-Law and ten-million-row framing. `assets/openapi.starter.yaml:108-118` LOW — mandatory
  Idempotency-Key on the starter create endpoint.

**frontend-craft — over-sized in places.**
- `SKILL.md:64` + `references/interaction-a11y.md` (whole file) + `references/forms.md:14-15` +
  `references/data-viz.md:18` MEDIUM — full a11y compliance mandatory and unconditioned across
  four files. Scanner's own caveat: a values call — cheap to build in, expensive to retrofit; if
  touched at all, gate like `references/auth.md:3` ("Read this once the app is not
  localhost-only"), do not strip. Open, deliberately low priority.
- `references/design-language.md:63-66` MEDIUM — "Every view is a composition… enrich the view…
  Never ship a screen that is mostly empty page" — instructs inventing unrequested features;
  collides with the operator's no-unrequested-scope rule. Open.
- `SKILL.md:24` LOW — both themes + persisted toggle + pre-paint script mandatory day-one.
  `references/design-language.md:13-28` LOW — required five-line design-brief comment.
  `SKILL.md:75` LOW — E2E selection criterion phrased as "would page someone" (the criterion
  decides coverage, so the wrong mental model picks the wrong flows).
  `references/ux-writing.md:26-27` LOW — product-onboarding framing.
- `references/react.md`, `references/vue.md` — not flagged: dense correctness knowledge, gated by
  framework evidence.

**code-craft — right-sized.** Three LOWs, none worth an edit alone: `references/python.md:196-208`
(support-matrix framing, correctly conditioned on a declared matrix), `references/python.md:137-138`
(publishing framing), `references/safe-refactor.md:21` + `references/tdd.md:63` (multi-reviewer/
team-habit framing over solo-valid rules).

**ci-actions — over-sized in places.**
- `SKILL.md:58-59` MEDIUM — SBOM + provenance attestation ("so a consumer can verify what they
  got") — no external consumer exists; "where it matters" hedges without scoping. Open.
- `SKILL.md:56-57` MEDIUM — actionlint + zizmor as mandatory CI jobs (CI-for-the-CI), pre-wired
  in `assets/ci.reusable.yml:86-105`. Open.
- `assets/ci.reusable.yml:3-24` MEDIUM — three placeholder classes (SHA, image digest, version)
  each needing a lookup command plus a Docker toolchain before the first green run. Open.
- `SKILL.md:53-55` LOW — fork-PR secrets splitting for a contributor population of zero.
  `SKILL.md:51-52` LOW — OIDC/cloud-trust-policy preference where the deploy target is a LAN box
  with an SSH key. `SKILL.md:11-12` LOW — "executes code from anyone who can open a pull request"
  framing.

**observability — right-sized** (already deliberately deflated; the model for the carve-out
register: `SKILL.md:66-69`, `references/alerting.md:63-64,94-98`, `references/pipeline.md:63-70`).
- `references/alerting.md:76-98` + `SKILL.md:107-108` + `scripts/error_budget.py` MEDIUM — the
  SLO/burn-rate apparatus carried in triplicate (23-line multi-window table, SKILL pointer,
  145-line script) for a pattern the same files twice say most lab services don't need;
  `SKILL.md:3` advertises "SLO burn-rate rule" as a routing trigger. Open.
- `references/pipeline.md:51-55` LOW — tail-sampling tuning, correctly quarantined under
  traces-optional. `SKILL.md:9,63` LOW — pager idiom, repaired by alerting.md's redefinition.

## Group 4 — meta and process

**sre-tool — was enterprise-shaped.**
- `SKILL.md:16-25` HIGH **[FIXED `dcb0945` + `35bfdff`]** — run_state.py control plane mandated
  for "any multi-agent run". Mechanism kept (SAFE-P1-003, tested, contract-graded); trigger
  narrowed to safety-critical or unattended. Two follow-up wordings measured worse on the
  durable-state contract (3/3 → 2/3 → 1/3); the subtractive fix restored 3/3 — see Corrections.
- `SKILL.md:82-96` HIGH **[FIXED `dcb0945`]** — chain-of-custody synthetic-snapshot capture
  (freeze, disposable clone, binary diff, SHA-256 inventory) replaced by commit-or-inconclusive;
  `agents/verification-engineer.md` consumer side removed with the producer.
- `SKILL.md:76` HIGH **[FIXED `dcb0945`, register only]** — residual-risk-acceptance record
  softened to a final-report note. The reviewer stack itself was found conditional (security
  review: network-exposed/auth-bearing only; independent verifier: safety-critical only) — the
  scan's "three mandatory reviewers" reading was an overstatement.
- `SKILL.md:40` MEDIUM **[FIXED via Phase-0 rewording in `dcb0945`]** — no-commit-without-grant
  stays (it is also the harness's own rule); the Phase-4 have-it-both-ways machinery it forced is
  what was removed.
- Open MEDIUMs: `SKILL.md:39-40` environment-card mission-block breadth and orchestrator-owned
  plan file; `assets/plan-file.template.md:19-23` gate-status sign-off register;
  `references/multi-component.md:9-16` + `assets/contract.template.md` versioned interface
  governance with owner and change-log; `references/multi-component.md:21-23` mockup sign-off
  gate register. LOWs: `SKILL.md:51` "many teams" routing predicate; relaunch/round-count table.
- KEEP (scanner-flagged): `SKILL.md:9` pre-Phase-0 exit (the skill's own proportionality valve),
  `:38` mission transaction, `:71` never-seed-the-reviewer, all of `references/cli.md`.

**eng-ladder — over-sized in places.** All open.
- `SKILL.md:33-35` MEDIUM — Mode 3 growth feedback: career-development machinery with no engineer
  being developed; costs description surface every session.
- `SKILL.md:21` MEDIUM — formal consult-and-decision-record protocol between rungs one person
  occupies; the content is "think hard about the irreversible bit."
- `SKILL.md:31` LOW — "meets the bar"/"next-level delta" promotion-packet framing. `SKILL.md:11-13`
  LOW — "survive the org." `references/principal.md:24-26` LOW — Hyrum/SemVer/deprecation
  signaling to nobody (expand→migrate→contract still earns its place). `references/principal.md:36-38`
  LOW — debt register framing. `references/distinguished.md:33` LOW — "decision-maker" is the reader.

**root-cause — right-sized, zero findings.** (KEEP: three-strikes at `SKILL.md:30`, hypothesis
table `:19-24`.)

**self-improve-loop — was enterprise-shaped; the largest correction target.**
- `SKILL.md:147-164` HIGH **[FIXED `4071e0f` + `c647046`]** — 7-gate promotion sequence → 4 gates.
  Deep review then caught the fold making condition-recording harness-dependent and dropping
  seed/repetitions; `c647046` restored it unconditionally and reinstated the unrun-gate/merge/ship
  prohibition.
- `SKILL.md:171-175` HIGH **[OVERTURNED as mechanism; prose trimmed]** — release-retest closure:
  26/28 promoted candidates carry release+retest records; origin is the real merged≠released
  incident (installed 1.4.0 vs shipped 1.6.0). Field-earned. Prose-only compression shipped.
- `SKILL.md:219-228` HIGH **[OVERTURNED]** — "three synchronized copies" drift risk:
  `tests/test_packet_lint.py:816-818` imports the owner and asserts full cross-product equality;
  `packet_lint.py:235-239` documents the standalone copy as deliberate. Test-pinned; kept.
- `references/learning-ledger.md:19-79` HIGH **[partially FIXED `4071e0f`]** — retention/renewal/
  reviewer-of-record: `review` has fired on 4/49 records (rare but live); code kept, prose
  compressed to the operational core.
- `references/learning-ledger.md:124-131` MEDIUM **[OVERTURNED on its volume claim]** — "a store
  whose realistic population is a handful of records": the store holds 49 candidates.
- Open MEDIUMs: intake coordinator/attestation prose (`references/learning-ledger.md:10-27,33` —
  describes real CLI trust model, light-touch at most); the five retro types
  (`references/retro-protocol.md:7-90`) and 13-line output block; the 8–10-field candidate block
  (`SKILL.md:209-217`, `references/discovery-routing.md:98-109`) — note the block is
  contract-graded, so any change owes a behavioral run. LOW: `references/research-basis.md`
  standing recheck burden.

**prompt-craft — right-sized, zero findings.**

## KEEP consensus — rigor that matters more solo, never strip

1. lab-incident's security carve-out (`SKILL.md:84-92`) — don't restart a compromised box.
2. restore-drill's scratch-target rule and exit-0-is-not-verification (`SKILL.md:16-25,43-44`).
3. Coverage denominators in both audit skills; attack-path-or-downgrade in security-audit.
4. upgrade-campaign's one-way-door identification and stop-on-first-failure.
5. host-onboard's proven second way in before lockout-capable changes (`SKILL.md:30-33`).
6. service-onboard's discovery-output-is-blast-radius rule (`SKILL.md:20-25`, field-proven).
7. runbook's never-guess-a-command and Rollback≠Recovery (`SKILL.md:117-119,123-129`).
8. Backup verification + BackupStale timestamp alerting (backend-craft database-reliability;
   observability).
9. ci-actions supply-chain hardening (SHA pinning, pwn-request, self-hosted-runner rules).
10. Prove-the-instrument discipline everywhere (tdd see-it-fail, promtool-fires, workflow-runs).
11. root-cause in full; prompt-craft's baseline-before-change.
12. sre-tool's pre-Phase-0 exit, mission transaction, reviewer independence, cli.md.
13. postmortem's re-scoped blameless framing (`SKILL.md:14-16`).
14. *(Added 2026-08-13, Correction 9's rescan.)* Group 1's fleet-coordination mechanisms: the
    audit ledger's keeper/emitter split and written-exception acceptance, lab-incident's
    contemporaneous timeline note and the outage→follow-up authority edge, security-audit's
    transcript-aware observability audience, and upgrade-campaign's unbatched major
    session+approval. Per-finding evidence in
    [`group1-rescan-2026-08-13.md`](group1-rescan-2026-08-13.md).
15. *(Added 2026-08-13, the Group 2 rescan.)* Group 2's coordination mechanisms:
    onboarding-map's four-state authority lifecycle, host-onboard's per-apply approval-evidence
    slot and its deliberately redundant authority preamble (unguarded by any contract, so a trim
    is unmeasurable), runbook's Owner / Escalation-stop / approvals slots (the disposition gate's
    own inputs, with five named consumers), and postmortem's action-artifact-proof rule, both
    retro lists, and its draft|final settledness marker. Per-finding evidence in
    [`group2-rescan-2026-08-13.md`](group2-rescan-2026-08-13.md).
16. *(Added 2026-08-14, the Group 3 rescan.)* Group 3's producer/consumer contract pairs and
    threat framings: backend-craft's X-RateLimit budget headers (paired with consuming-apis'
    self-throttle rule) and the starter asset's required Idempotency-Key (the SKILL's own
    unconditional retry-safety rule, worked, with its consumer instruction in consuming-apis);
    frontend-craft's committed design-brief comment (the design's durable spec for the next
    session); code-craft's multi-reviewer and flaky-test framings (reviews are multi-party here —
    bot passes and future sessions); and ci-actions' "executes code from anyone who can open a
    pull request" (the correct threat model for an agent-authored PR population). Per-finding
    evidence in [`group3-rescan-2026-08-14.md`](group3-rescan-2026-08-14.md).
17. *(Added 2026-08-14, the Group 4 rescan.)* Group 4's program scaffolding: sre-tool's
    environment card and orchestrator-owned plan file (the canonical spawn handoff and the loop's
    durable state — counters, gate evidence, safe resume point), its one-owner versioned interface
    contract ("cite the version built against" — provenance binding in prose form); eng-ladder's
    ownership-vs-consult typed edge (a scoped consult request returning one decision record across
    separate agent contexts), the debt-with-payback-trigger rule, and "act from your framing
    without re-deriving it" (the handoff-completeness criterion); and self-improve-loop's
    candidate block and retro output block (the quarantine boundary's contract-graded wire
    formats). Per-finding evidence in
    [`group4-rescan-2026-08-14.md`](group4-rescan-2026-08-14.md).

## Corrections — scan claims the round's evidence overturned

A later session must not re-apply these as findings:

1. **Release-retest lifecycle is live, not ceremony** — 26/28 promoted candidates carry both
   blocks; the mechanism's origin is a real release-tail incident. Only prose was compressed.
2. **The state-matrix mirror is test-pinned** — silent drift fails T0; the standalone copy in
   packet_lint is documented as deliberate.
3. **The ledger holds 49 candidates**, not "a handful"; volume-based arguments against its views
   fail.
4. **`review` renewal is rare but live** (4/49) — code kept.
5. **run_state.py targets untrusted LLM workers, not colleagues** — the evidence-envelope control
   is real at any headcount; only the any-multi-agent trigger was oversized.
6. **The sre-tool "three mandatory reviewers" reading was overstated** — two of three are
   conditional.
7. **Eval lesson (adjacent-context bleed):** adding an explanatory "normal mode" sentence beside
   the safety-critical denial degraded the durable-state contract (3/3 pre-change → 2/3 → 1/3
   with the denial strengthened beside it → 3/3 once removed). Prominence of the required
   behavior did not compensate for offering an alternative framing; the fix was subtractive.
   n=3 per measurement — the conclusion rests on the paired direction tracking the sentence.
8. **Relocating `runbook`'s propose grammar to `references/` would break it** — added 2026-08-13,
   and it retires what this record called its largest open backlog item. The remedy the scan
   proposed ("relocation to a `references/` file loaded on the propose path") cannot be loaded on
   that path: `runbook-disposition-propose` runs as a skill-only session (`allowed_tools:
   ["Skill"]`, `evals/behavioral/contracts.json`), so it has no `Read` with which to reach a
   reference file. The identical move is the measured cause of a different contract failure —
   LEARN-002's 2026-08-10 calibration found the `Learning: candidate — <observed -> expected>`
   literal living only in `references/retro-protocol.md:97` and `references/discovery-routing.md:99`,
   ruled the graders right and the text wrong, and chose *moving the literal into the body* as the
   fix (`evals/baselines/history/2026-08-10-learn-002.md`, "The systemic finding"). That round
   also considered and rejected the cheaper inverse — granting `Read` to the cases — because it
   "would leave every other skill-only caller in the same position". Relocating the runbook grammar
   would recreate exactly that position for a contract currently at 2/3 whose one remaining failure
   is already a session emitting narrative the grammar forbids. The 42 lines are not ceremony: they
   are a closed machine-checked vocabulary with four live consumers, and the session that must obey
   them is the one that cannot open a second file. **Do not re-propose this relocation.** Reducing
   the runbook body's cost has to come from somewhere the grammar is not.
9. **The LOW tier's "vocabulary only" definition was unsound for the lab-operations group** —
   added 2026-08-13 after the Group 1 rescan
   ([`group1-rescan-2026-08-13.md`](group1-rescan-2026-08-13.md), which owns the per-finding
   evidence). The scan's severity model judged prose against an audience of one human with
   continuous memory; the fleet's artifacts are read by the next session, which has neither
   memory nor grounds to trust unverified claims. Six of Group 1's ten LOWs are coordination
   mechanisms wearing organizational vocabulary — the ledger keeper (write-authority principal),
   the written exception (loop convergence), the timeline note (the only `[verified]`-capable
   evidence a later session can hold), the outage downgrade (the edge ending the mitigate-first
   authority inversion), the observability audience (agent sessions and their retained
   transcripts), and majors-get-their-own-session (unbatched tier approval plus a fresh context).
   A later proportionality round applies the two-question test — who is the real reader, what
   consumes the artifact — before tiering, and reads the rescan record rather than re-deriving
   it. Group 2 was re-scanned the same day under the same method
   ([`group2-rescan-2026-08-13.md`](group2-rescan-2026-08-13.md)) — six further flips, zero edits
   owed, and the `runbook` "enterprise-shaped" verdict inverted: its slots are the fleet's
   most-consumed artifact contract. Group 3 followed on 2026-08-14
   ([`group3-rescan-2026-08-14.md`](group3-rescan-2026-08-14.md)) — six flips, two one-phrase
   edits, and the group's own pattern: vocabulary findings resolving into halves of typed
   producer/consumer contracts whose consuming half sat in a neighboring file. Group 4 closed the
   set on 2026-08-14 ([`group4-rescan-2026-08-14.md`](group4-rescan-2026-08-14.md)) — ten flips
   under the freezes its rescanner had to respect (sre-tool contract-graded and edit-sensitive,
   eng-ladder frozen by LADDER-001, self-improve-loop riding LEARN-002), zero edits by design,
   and the one finding whose original severity survives all four rescans: eng-ladder's Mode 3.
   No finding now remains under the lens this correction records.

## Round disposition as of this record

Fixed and verified in PR #132 (`4071e0f`..`d28fb6b`): the five HIGH clusters, the deep-review
findings (P2 + four P3), and the three Codex review P2s. Verification: deep-review
`merge-with-nits` / 0 criticals; validator + 833 tests at every commit; paired behavioral
evidence (sre-tool 3/3 == 3/3; self-improve/loop-capture failures identical to stored pre-change
baselines — LEARN-002's known gap, not this round's).

## Backlog disposition (2026-08-13, closing PROP-002)

Every finding this record left `open` is dispositioned below, which is what the roadmap item's
acceptance required before it could retire. Four dispositions are used: **worked** (edited, with
the commit), **overturned** (checked against liveness evidence and rejected — do not re-apply),
**deferred** (trigger-bound to a named item that already owns a paid measurement on the same
file), and **dropped** (judged not worth an edit, with the reason).

Two rules did most of the sorting, and both are the fleet's own proportionality discipline pointed
at this backlog rather than at the skills:

1. **A description edit owes a paired routing run**, which is T3 and operator-owned. Every
   description-level finding therefore defers rather than shipping an unmeasured edit — including
   `onboarding-map`'s fourth authority restatement, which lives in the description.
2. **Where another live roadmap item already owns a paid run on the same file, the trim rides that
   item.** Buying a second batch to measure a trim in a file LEARN-002 or LADDER-001 will already
   be re-measuring is the repeated work the fleet's proportionality rule forbids. This is a
   sequencing decision, not a downgrade: each deferral names the item that carries it.

### Worked (`eb53758`, plus `ci.reusable.yml` in the closing commit)

| Finding | What changed |
|---|---|
| `onboarding-map` MEDIUM (body half) | Closing restatement removed; opening sentence, the four-states authorizes column, and the both-directions failure note kept — each says something the others do not |
| `service-onboard SKILL.md:61-62,66-67` MEDIUM | Three parallel lists → unverified items kept distinct from not-applicable; owner named only when it is someone else; the unverified list named as the load-bearing part |
| `ci-actions SKILL.md:56-57` MEDIUM | actionlint/zizmor run locally on workflow edits, graduating to CI jobs when someone else's edit can break a workflow |
| `ci-actions SKILL.md:58-59` MEDIUM | SBOM/provenance keyed to the artifact leaving the lab |
| `backend-craft SKILL.md:67` MEDIUM | Contract tests keyed to a consumer not deployed in the same commit |
| `backend-craft database-reliability.md:33-35` MEDIUM | expand→migrate→contract keyed to a migration that cannot stop its readers |
| `backend-craft SKILL.md:58` + `consuming-apis.md:12` MEDIUM | Circuit breaker keyed to call volume that can hurt something |
| `frontend-craft design-language.md:63-66` MEDIUM | Constraining the canvas is the no-permission fix; enriching became a proposal, not a ship |
| `sre-tool multi-component.md:9-16` MEDIUM | Interface-contract artifact required once more than one builder writes against the interface |
| `ci-actions ci.reusable.yml:3-24` MEDIUM (partial) | Non-Docker digest lookup added; see the overturn below for the rest |

### Overturned — do not re-apply

- **`runbook SKILL.md:32-73`** — Correction 8 above. The largest item in this backlog, retired on
  measured evidence that the proposed move would break a live contract.
- **`ci-actions ci.reusable.yml:3-24`** (the placeholder friction itself) — the file's own header
  already carries each lookup command and the reason the placeholders are invalid rather than
  stale: "a stale-but-valid pin … would run *some* version silently. An invalid ref fails loudly on
  the first run instead." That is prove-the-instrument discipline (KEEP 10) inside the
  supply-chain hardening this same scan's KEEP 9 protects. Only the missing non-Docker route for
  the image-digest class was real, and it is fixed.
- **`sre-tool plan-file.template.md:19-23`** (gate-status sign-off register) — same class as
  Correction 5. The template says "approval evidence is a pointer to the user's words, never
  inferred"; that is an anti-fabrication control against an LLM worker claiming an approval it was
  never given, which is real at any headcount. The register reading mistakes the adversary.
- **`sre-tool multi-component.md:21-23`** (mockup sign-off gate) — approving a static mockup before
  framework code is the cheapest fork point in the whole build, and naming gates in the cadence
  contract is this skill's own live mechanism, not borrowed ceremony.

### Deferred, trigger-bound

| Finding | Rides | Why |
|---|---|---|
| `runbook SKILL.md:100,112` (owner/escalation slots), `references/example.md:55-56,23,48` | **LEARN-002** | `runbook-disposition-propose` sits at 2/3 with a TEXT residual LEARN-002 already owns; that round pays for runbook sessions and will re-measure this file |
| `self-improve-loop SKILL.md:209-217` + `discovery-routing.md:98-109` (candidate block), `retro-protocol.md:7-90` (five retro types) | **LEARN-002** | Contract-graded by 16 cases, and LEARN-002's next action is already a canonical SKILL.md edit to this file owing paired reruns |
| `eng-ladder SKILL.md:33-35` (Mode 3), `SKILL.md:21` (consult protocol) | **LADDER-001** | That item owes one recorded `evals/routing/ladder.json` capture whose stored benchmark is already STALE; editing the skill now would move the bytes out from under a run the operator is about to buy |
| `onboarding-map` description clause | **LANE-001** | `onboarding-map` is in the `homelab-ops` cluster whose paired 'before' capture LANE-001 owes at merge base `4fef0ce` |

Each deferral above names an item that is live on the roadmap and already buying sessions on that
file, and each receiving item records the ride-along. A deferral with no such owner is not a
deferral — it is an untracked task — so the two findings that had no owner were decided instead of
parked, below.

### Dropped, with reason

- **`observability` SLO/burn-rate triplicate** (`alerting.md:76-98`, `SKILL.md:107-108`,
  `scripts/error_budget.py`) — the always-loaded surface already carries the carve-out this scan
  itself named as the model register ("Household scale, honestly", `SKILL.md:66-69`). The 23-line
  table is conditionally loaded and costs nothing until its predicate trips, and `error_budget.py`
  is live tested code invoked on demand. What remains is the description trigger, deferred above.
- **`frontend-craft` unconditioned a11y** (`SKILL.md:64`, all of `interaction-a11y.md`,
  `forms.md:14-15`, `data-viz.md:18`) — the scanner filed its own caveat, and it holds: this is a
  values call, cheap to build in and expensive to retrofit. Nothing here is dropped for being
  wrong; it is left alone deliberately.
- **`backend-craft api-design.md:61-62,51-52`** (deprecation protocol, error codes as contract) —
  already conditioned wholesale by the published-surface definition `0d5fe31`/`c647046`/`d28fb6b`
  landed. The residual register is a vocabulary echo of a boundary that now exists.
- **`self-improve-loop learning-ledger.md:10-27,33`** (intake coordinator, attestation) — describes
  the fail-closed CLI's actual trust model. Rewording prose to sound smaller while the mechanism it
  documents is unchanged trades accuracy for tone.
- **`sre-tool SKILL.md:39-40`** (environment-card breadth, orchestrator-owned plan file) — decided
  rather than parked, because no live item is buying `sre-tool` sessions to carry it. The trim's
  benefit is a little less always-loaded text; its cost is a paired behavioral run on a region
  Correction 7 measured as edit-sensitive, where an adjacent sentence moved the durable-state
  contract 3/3 → 2/3 → 1/3 in this very round. Measured cost exceeds unmeasured benefit. Reopen
  only if an `sre-tool` round is paying for sessions anyway, when the trim rides a run that already
  exists.
- **`observability SKILL.md:3`** ("SLO burn-rate rule" as a routing trigger) — same reasoning, and
  additionally the trigger is not wrong: `observability` genuinely owns burn-rate rules, and the
  finding is that advertising them over-invites a pattern most lab services skip. That is a routing
  *precision* claim with no observed miss behind it, and buying a paired routing run to test a
  speculative improvement inverts the eval discipline. Reopen on an actual observed routing miss.
- **Every remaining LOW, as one batch** — the ~30 LOW findings across `lab-audit`,
  `lab-incident`, `security-audit`, `upgrade-campaign`, `restore-drill`, `onboarding-map`,
  `host-onboard`, `runbook`, `postmortem`, `backend-craft`, `frontend-craft`, `code-craft`,
  `ci-actions`, `observability`, `sre-tool`, `eng-ladder`, and `self-improve-loop`. The scan
  defined this tier as **vocabulary only**, and its own per-skill notes say repeatedly that none is
  worth an edit alone. Shared reason: each is a word choice inherited from a larger-organization
  idiom ("the ledger's keeper", "meets the bar", "service owner", "Status: draft | final") whose
  underlying rule is correct and load-bearing. Editing ~30 sentences across 17 files to adjust tone
  would rewrite text that behavioral contracts and routing descriptions grade, buying measurable
  risk for no behavior change — the exact trade Correction 7 measured going the wrong way. They are
  recorded here as observed, and a LOW is available as free evidence if a future round edits one of
  these files for a substantive reason anyway.

### 2026-08-13/14 addendum — Groups 1–4 re-dispositioned by rescan

The batch drop above is now **fully superseded**: every group was re-scanned under the
engineering-program reading rule and carries **individual** dispositions that replace its
membership in the batch. Group 1: six kept as coordination mechanisms (KEEP 14), three drops
confirmed, one partial, four sharpening edits landed (one with paired behavioral evidence), one
gap deferred trigger-bound — [`group1-rescan-2026-08-13.md`](group1-rescan-2026-08-13.md).
Group 2: six further flips (KEEP 15), zero edits owed — every remaining finding was fully wired
mechanism, riding a recorded measurement, or a surviving drop — plus two gaps recorded, the larger
being that host-onboard and service-onboard's authority preambles are graded by no behavioral
contract — [`group2-rescan-2026-08-13.md`](group2-rescan-2026-08-13.md), whose closing section
enumerates the remaining groups' standing findings and rescanner constraints. Group 3: six flips
(KEEP 16), two one-phrase edits in ungraded text, eight drops confirmed, zero gaps — the craft
group's findings kept resolving into halves of typed producer/consumer contracts —
[`group3-rescan-2026-08-14.md`](group3-rescan-2026-08-14.md). Group 4: ten flips (KEEP 17), one
finding upheld (eng-ladder Mode 3, parked as a measured trim candidate on LADDER-001), four drops
standing, zero edits — every candidate edit sits under a named freeze —
[`group4-rescan-2026-08-14.md`](group4-rescan-2026-08-14.md). Correction 9 owns the lens error
that made the rescans necessary.

### What closing this item does not claim

No behavioral or routing run was purchased for this closeout. Every edit in it was chosen to be
provable by the deterministic gates alone — conditioning a mandate or removing a restatement in
text no contract grades — and everything that would have needed a paid run is deferred above with
the item that will pay for it. T0, T1 (837 tests across 33 modules), regenerated adapters, and
`claude plugin validate . --strict` are what backs it, and that is a claim about consistency, not
about measured session behavior.
