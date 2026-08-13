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
session must not re-apply them; the evidence is in the Corrections section. Everything else is
the open backlog the PROP-002 roadmap item tracks. This is dated evidence, not a task list.

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

## Round disposition as of this record

Fixed and verified in PR #132 (`4071e0f`..`d28fb6b`): the five HIGH clusters, the deep-review
findings (P2 + four P3), and the three Codex review P2s. Verification: deep-review
`merge-with-nits` / 0 criticals; validator + 833 tests at every commit; paired behavioral
evidence (sre-tool 3/3 == 3/3; self-improve/loop-capture failures identical to stored pre-change
baselines — LEARN-002's known gap, not this round's). Everything marked "open" above is the
backlog the PROP-002 roadmap item carries.
