# Group 2 rescan under the engineering-program lens (2026-08-13)

**What this is.** The five onboarding-and-docs skills — `onboarding-map`, `host-onboard`,
`service-onboard`, `runbook`, `postmortem` — re-scanned under the reading rule `AGENTS.md` and
`docs/engineering-program.md` state: the reader of fleet prose is the next session, and any trim
is decided by *who is the real reader* and *what consumes the artifact*. Method identical to
[`group1-rescan-2026-08-13.md`](group1-rescan-2026-08-13.md): full reads of every file,
measurement exposure mapped before judging, per-finding re-verdicts, and gaps hunted in the
direction the original scan could not see. Dated evidence.

**Measurement exposure, mapped first.** All five sit in the `homelab-ops` routing cluster whose
paired 'before' capture LANE-001 owes — **description edits are frozen for this whole group**.
`runbook` is graded by six behavioral contracts and its wording changes already ride LEARN-002's
recorded measurement (see the roadmap ride-along and Correction 8). `postmortem` also sits in
`continuous-improvement` and `retro-boundary`. `onboarding-map`, `host-onboard`,
`service-onboard`, and `postmortem` bodies are behaviorally ungraded.

## Headline

**Zero edits, and that is the finding.** Group 1's rescan produced four edits because its
mechanisms were half-wired — connections missing between parts that existed. Group 2's mechanisms
are *fully* wired: every remaining finding is either a misreading of wiring that exists (six
flips), a wording change already riding a recorded measurement (runbook → LEARN-002,
onboarding-map's description → LANE-001), or a drop that survives the new lens. The scan's
"enterprise-shaped" verdict on `runbook` inverts completely: it is the fleet's most-consumed
artifact contract.

## Per-finding re-verdicts

| Original finding | Re-verdict | Why |
|---|---|---|
| onboarding-map MEDIUM — authority restated ×4 | Stands as worked/riding | Body copy trimmed in `eb53758`; the description's copy waits on LANE-001's capture (recorded on that roadmap item) |
| onboarding-map LOW `:23` — mandatory four-state declaration | **Keep** | Discovery/Recommendation/Activation/Execution is a typed authority lifecycle — each state names what it authorizes. On the host class this skill exists for (no tier-holding agent reachable — LANE-001's lane), the declaration is the *only* authority control present. Industry handoff protocols carry exactly this shape (task-lifecycle states) |
| host-onboard LOW `:60` — per-apply "approval evidence" in the packet | **Keep** | Correction 5's class: the writer is an agent session that performed lockout-capable Tier 2/3 applies, and the slot is the anti-fabrication control — a pointer to the operator's words, readable by anyone later asking "who authorized this firewall change" |
| host-onboard LOW `:11-20` — authority preamble, intra-file repetition + duplicated in service-onboard | Drop-the-trim, upgraded reason | Each sentence carries a distinct mechanism (tier enumeration, Tier-3-by-definition with its lockout rationale, the arrival-path guard for slash-command invocation without agent context). The cross-file copy is the standalone-invocability pattern the reconciliation record already ratifies for the material-fork rule. And the deciding fact: **no behavioral contract grades either file**, so a trim's damage would be unmeasurable — the worst risk/benefit in the group for saving two lines on the fleet's highest-blast-radius path |
| service-onboard MEDIUM `:61-62,66-67` — packet lists | Stands as worked | `eb53758`; confirmed in place on re-read |
| runbook MEDIUM `:32-73` — relocate the propose grammar | Stands as overturned | Correction 8; the skill-only contract session has no `Read` |
| runbook MEDIUM `:100` — mandatory Owner slot | **Keep** | The disposition gate's own input: *update* requires a known owner, an unknown owner forces *propose* with the `owner` gap. Five distinct consumers: the update predicate, the propose grammar (machine-checked by `scripts/packet_lint.py`), service-onboard step 7's inventory, lab-audit's hand-it-to-the-named-owner fix class, and postmortem's Runbook-updated slot. Remove the slot and the update/create/propose gate has nothing to read |
| runbook MEDIUM `:112` — Escalation/stop slot | **Keep** | The authority ceiling made procedural: conditions that forbid continuing plus the handoff destination — the same mechanism as the skill's own "caller's authority is the ceiling… hand it to the owner" rule, placed where the 3 a.m. session will actually read it |
| runbook LOW `:104` — "approvals" slot | **Keep** | Tier-routing metadata: it tells the executing session *before it starts* which steps hit an approval gate under `homelab-platform`'s tiers. The reader is the untrusted worker; the consumer is tier discipline |
| runbook LOW `:54` — `platform-sre` / oncall-email owner examples | Partially dissolves; wording rides LEARN-002 | The examples document what the owner-id regex admits (dot, `+`, `@` punctuation) — `tests/test_packet_lint.py` exercises exactly these shapes — so they are grammar documentation, not owner recommendations. Any clarifying rewording is a graded-file change and rides LEARN-002's runbook measurement |
| runbook `references/example.md` MEDIUMs — service/storage owner roles, "admission gates" | Downgrade to vocabulary-in-fiction; rides LEARN-002 | The file is a declared fictional scenario whose whole payload is honest `unverified`/`n/a` marking; the role split is part of the fiction, and the "admission gates" preconditions (destructive approval, validated backup identity, exact config match, rehearsed drill) are KEEP-class recovery discipline under an org-flavored label |
| postmortem LOW `assets/postmortem.md:3` — "Status: draft \| final" | Keep, no edit | A settledness marker whose reader is the resuming session (a write-up interrupted mid-session — the same failure class Group 1 fixed in lab-incident's Step 3) and the recurrence reader deciding whether the record is citable evidence. One template line; nothing machine-reads it; costs nothing |
| postmortem LOW `:39` — went-well / went-poorly lists | **Keep** | Bidirectional learning intake, capped at a line each: went-poorly feeds Actions; went-well is KEEP-list capture — the same record-what-not-to-strip pattern the PROP-002 scan itself uses |

## Gaps found (the direction the original scan could not see)

1. **The fleet's two highest-blast-radius checklists are eval-unguarded.** `host-onboard` and
   `service-onboard` — lockout-capable SSH/firewall/user changes, live proxy/DNS/TLS applies —
   have **no behavioral contract** grading their authority preambles. A bad trim or silent drift
   in exactly the prose that keeps a slash-command arrival from running tier-free would fail
   nothing. This is also what decided the preamble re-verdict above: an unmeasurable edit was
   declined. **Trigger-bound:** any future edit to either file's authority text owes a contract
   first (written red-before-green, before the edit), and the contract is worth writing on its
   own the next time a behavioral-eval round is already paying for case design.
2. **Packet asymmetry, observation only.** host-onboard's packet captures per-apply tier and
   approval evidence; service-onboard's packet does not (its approvals live per-step in the
   body). Both apply Tier 2/3 changes. No observed failure, and adding a slot is growth the
   counterweight forbids without one — recorded so a future failure has its pre-registered
   hypothesis.

## The exemplar

`postmortem` is this group's `restore-drill`. "Every action names the **artifact** it becomes —
a runbook line, an alert, a drill, a validator rule — and a **proof-of-done** check. An action
with no artifact will not happen" is the strongest handoff-completeness rule in the fleet's
prose: it is ACK-001's dropped-packet lesson, stated as discipline, two months before that item
existed. Its Feed-it-forward section closes three loops by name (runbook, lab-audit's next sweep,
self-improve-loop), it builds timelines only from artifacts and grades reconstruction
`[unverified]`, and it states its own scale-invariance: "This holds with one operator exactly as
it does with forty."

## Groups 3 and 4 — standing findings, rescan owed

**The dispositions below stand under the original one-human lens.** Correction 9 in the
[scan record](prop-002-scan-findings-2026-08-13.md) scopes itself to Group 1, and this record
extends it to Group 2 only. Nobody has re-judged the following under the program lens — a later
session must rescan them with the same method (full reads first, measurement exposure mapped,
two-question test per finding) rather than trusting either the original tier or this list's
hunches. Findings marked ⚑ were flagged as mis-tier suspects during this branch's general review
or carry an obvious program-lens question; the flag is a hypothesis, not a verdict.

**Group 3 — engineering craft:**

- `backend-craft` — worked MEDIUMs stand (`eb53758`). Standing LOWs: X-RateLimit headers
  (`SKILL.md:52`); Hyrum's-Law framing (`api-design.md:56-57`) — program-lens question: agent
  consumers *do* hardcode observed behavior, so is this enterprise framing or the correct warning
  for the fleet's own clients?; ten-million-row framing (`database-reliability.md:47-48`);
  ⚑ mandatory Idempotency-Key in `assets/openapi.starter.yaml:108-118` — a shipped starter asset
  is a *received default*, not vocabulary, and retry-safety matters more when the caller is an
  agent with automatic retries.
- `frontend-craft` — worked MEDIUM stands; a11y cluster deliberately retained. Standing LOWs:
  ⚑ both-themes + persisted toggle + pre-paint script mandated day one (`SKILL.md:24` — mandates
  real build work, not word choice); ⚑ the required five-line design-brief comment
  (`design-language.md:13-28`) — program-lens question: that comment is a handoff artifact to the
  next session editing the UI, a likely flip; ⚑ E2E criterion phrased "would page someone"
  (`SKILL.md:75` — the criterion decides coverage, so the wrong mental model picks the wrong
  flows); product-onboarding framing (`ux-writing.md:26-27`).
- `code-craft` — standing LOWs: support-matrix framing (`python.md:196-208`, correctly
  conditioned); publishing framing (`python.md:137-138`); ⚑ multi-reviewer/team-habit framing
  (`safe-refactor.md:21`, `tdd.md:63`) — program-lens question: in this fleet reviews *are*
  multi-party — the reviewer is another agent session — so the "team" framing may be literally
  accurate here.
- `ci-actions` — worked MEDIUMs and the placeholder overturn stand. Standing LOWs: fork-PR
  secrets splitting (`SKILL.md:53-55`); ⚑ OIDC preferred where the target is a LAN box with an
  SSH key (`SKILL.md:51-52` — steers a real config choice); ⚑ "executes code from anyone who can
  open a pull request" (`SKILL.md:11-12`) — program-lens question: with agent-authored PRs this
  is *more* true, not less.
- `observability` — the SLO-triplicate drop and its reasons stand; both LOWs already carry their
  own resolutions (tail-sampling quarantined under traces-optional; pager idiom repaired by
  alerting.md). The cheapest rescan in the set.

**Group 4 — meta and process:**

- `sre-tool` — the two Correction-5 overturns (gate-status register, mockup gate) already
  *applied* the program lens; the env-card/orchestrator-plan-file drop carries its reopen
  trigger. Standing LOWs: "many teams" routing predicate (`SKILL.md:51`); ⚑ the
  relaunch/round-count table — program-lens question: a round-count bound is loop-engineering's
  termination condition, a likely flip. **Constraint: Correction 7 measured this file as
  edit-sensitive; any text change owes a paired run.**
- `eng-ladder` — Mode 3 and the consult protocol ride LADDER-001 and are **frozen until its
  capture** (recorded on that roadmap item). Standing LOWs: promotion-packet framing
  (`SKILL.md:31`); "survive the org" (`SKILL.md:11-13`); principal Hyrum/SemVer signaling
  (`principal.md:24-26`); ⚑ debt-register framing (`principal.md:36-38`) — program-lens
  question: a debt register is a durable-disposition ledger, a likely flip; "decision-maker is
  the reader" (`distinguished.md:33`).
- `self-improve-loop` — the standing MEDIUMs (candidate block, five retro types, intake prose)
  ride LEARN-002 and its sixteen contracts; the LOW (`research-basis.md` standing recheck burden)
  can only be judged beside them. Rescan rides that round.
- `root-cause`, `prompt-craft` — zero findings at scan time; no rescan owed, though neither has
  had a C-bucket (missing-mechanism) pass, which the Group 1 and 2 rescans show is where the new
  lens earns its keep.

**Constraints snapshot for whoever rescans** (verify against the live roadmap first — this list
is dated): descriptions across `homelab-ops` frozen by LANE-001's pending capture; `eng-ladder`
frozen by LADDER-001; `runbook` and `self-improve-loop` wording rides LEARN-002; `sre-tool` and
`lab-incident` are contract-graded and edit-sensitive — paired runs owed; `backend-craft` has one
contract (`packet-slots-builder`) and `eng-ladder` one (`ladder-report-not-absorb`) to check
against before assuming a file is unguarded.
