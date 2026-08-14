# Group 3 rescan under the engineering-program lens (2026-08-14)

**What this is.** The five engineering-craft skills — `backend-craft`, `frontend-craft`,
`code-craft`, `ci-actions`, `observability` — re-scanned under the reading rule `AGENTS.md` and
`docs/engineering-program.md` state: the reader of fleet prose is the next session, and any trim is
decided by *who is the real reader* and *what consumes the artifact*. Method identical to the
[Group 1](group1-rescan-2026-08-13.md) and [Group 2](group2-rescan-2026-08-13.md) rescans: full
reads of every cited file, measurement exposure mapped before judging, per-finding re-verdicts,
gaps hunted in the direction the original scan could not see. Dated evidence; citations are by
content, not line number, except where the original scan's `c38592c`-bound citations are quoted.

**Coverage, honestly.** This record's first pass read every *cited* file in full — a narrower
scope than Groups 1 and 2, which read their groups completely — and the operator's question caught
the gap: a zero-gaps claim can only cover the files actually read, and files the original scan
left clean were clean under the *old* lens, which could not see missing mechanisms at all. The
completion pass then read the remaining nineteen files (both auth references, the framework and
language references in full, the observability query/dashboard references, `error_budget.py`, the
complete starter asset and CI template). Result: **zero new findings**, and one flip strengthened
— `typescript.md` is a *third* member of the Idempotency-Key contract (the mint-once-per-logical-
write key lifecycle, with the double-charge and stale-key-replay bugs named), joining the starter
asset's producer half and consuming-apis' client rule. Representative program-consistent mechanisms
found in the completion files, none previously flagged: PowerShell's `SupportsShouldProcess` ("buys
`-WhatIf` from the runtime instead of a hand-rolled dry-run flag" — the gated-effect dry-run rule),
dashboards' `allowUiUpdates: false` ("makes the repo the source of truth and makes drift impossible
rather than merely discouraged" — the fleet's byte-drift doctrine in Grafana form), promql's
`absent()` companion ("the failure mode that hides all the others"), and `error_budget.py`'s
no-clock determinism ("the same inputs always produce the same output and the result can be pasted
into a packet as evidence").

**Measurement exposure, mapped first.** `backend-craft`, `frontend-craft`, and `observability`
appear in the `homelab-ops` routing cluster whose paired 'before' capture LANE-001 owes — and
description edits owe routing runs regardless — so **no description was touched**. No Group 3 file
is graded by a behavioral contract; `backend-craft` and `frontend-craft` SKILL.md are preloaded
into the session `packet-slots-builder` grades, handled per the PR #132/#133 precedent as
T0-covered body edits.

## Headline

Six flips, two one-phrase edits, eight drops confirmed, zero gaps. The pattern that distinguishes
this group: the "vocabulary" findings kept resolving into **halves of typed producer/consumer
contracts** — one half flagged as ceremony while its consuming half sat in a neighboring file. The
craft group is the fleet's most cross-consumed prose: backend-craft alone is named as a consumer by
tdd.md, observability, database-reliability, and its own consuming-apis file, and the original
scan's severity model — which asked "who is the audience" per sentence — could not see pairings
that live across files.

## Per-finding re-verdicts

| Original finding | Re-verdict | Why |
|---|---|---|
| backend-craft `SKILL.md:52` — X-RateLimit budget headers "for third-party clients the operator wrote" | **Keep** | The consuming half is in the same skill: `consuming-apis.md` instructs clients to "self-throttle to their quota" — and the fleet's clients are agent-written, i.e. exactly the well-behaved automated callers that read those headers. Producer publishes the budget ↔ consumer throttles to it: a typed contract, both halves taught here |
| backend-craft `api-design.md` — Hyrum's-Law framing | Keep, no edit | Now sits inside the published-surface section this round's earlier fixes conditioned wholesale ("earns its cost from the first consumer you cannot reach") — and the warning is *more* accurate for agent consumers, which observe real responses and bake quirks into generated clients |
| backend-craft `database-reliability.md` — ten-million-row framing | Drop stands | A vividness device on a correct asymmetric-cost rule: batching a small backfill costs nothing, not batching a big one is an outage. The number illustrates the consequence; the mandate does not depend on it |
| ⚑ backend-craft `assets/openapi.starter.yaml` — required Idempotency-Key on the starter create endpoint | **Keep** | The received-default worry was answered by the skill's own rules: SKILL.md's resiliency section unconditionally requires mutating endpoints to be retry-safe, a POST create is not naturally idempotent, and `consuming-apis.md` instructs the callers — auto-retrying agent clients — to send the key. The starter demonstrating the mandated pattern (with a full contract: replay semantics, 24h retention, reused-key-conflict → 409) is the rule worked, not extra ceremony; stripping it would make the starter violate the SKILL it ships with |
| ⚑ frontend-craft `SKILL.md:24` — both themes + persisted toggle + pre-paint script day one | Deliberately retained | Same disposition class as the a11y cluster, for the same reason the scanner itself named there: a values call that is cheap to build in and a rewrite to retrofit — theme tokens over hardcoded colors is the archetype of that asymmetry. Not a fleet mechanism; honestly re-rationalized, not flipped |
| ⚑ frontend-craft `design-language.md:13-28` — required five-line design-brief comment | **Keep** | A committed comment carrying audience/tone/palette/type/signature is the design's durable spec: the build session derives every choice from it, and the next session editing the UI reads it instead of re-deriving or drifting the system — contemporaneous capture whose reader is a stateless successor, and the working half of the anti-stock-look discipline. The ⚑ was right |
| ⚑ frontend-craft `SKILL.md:75` — E2E criterion "would page someone" | **Worked** | The scanner's point holds — the criterion selects the coverage, so the wrong mental model tests the wrong flows — and the skill is deliberately domain-neutral, so the fix names both registers. First wording ("household-noticed") was itself caught by review as re-widening the bound — notice is not dependence — and the final canonical text reads: "would interrupt someone — the paged flows in a product, the ones that block household use in a lab" |
| frontend-craft `ux-writing.md` — "how people learn the product" | Drop stands | Usability rationale accurate at any scale; the household learns the product too |
| code-craft `python.md` — support-matrix framing | Drop stands | Correctly conditioned on a *declared* matrix and version-sensitive behavior — and this repository's own T2 three-platform CI is a live instance of the rule |
| code-craft `python.md` — publishing framing | Drop stands | Conditioned on "a distributable project" |
| ⚑ code-craft `safe-refactor.md` + `tdd.md` — multi-reviewer/team-habit framing | **Keep** | Reviews here *are* multi-party: every PR draws Codex and Copilot passes (fifteen threads on PR #133 alone), so "the review comment you will get anyway" is literally true; and tdd.md's "teaches everyone to ignore red" includes every future session that runs the suite — a flake trains stateless successors to distrust red, which is the untrusted-claims problem wearing team vocabulary |
| ci-actions `SKILL.md:53-55` — fork-PR secrets splitting | Drop stands | Self-conditioned ("on fork contributions") — inert until its trigger exists, correct the day it does |
| ⚑ ci-actions `SKILL.md:51-52` — OIDC preferred where the target is a LAN box | **Worked** | The rule self-scoped to cloud ("a cloud trust policy") but left the LAN case unstated, which is the one real mis-steer. First wording ("in SSH form") was itself caught by review as categorical over transport — a Kubernetes or hypervisor-API target would be told to provision an unusable key — and the final canonical text reads: OIDC where the target can trust a workload identity; "a LAN target takes the same rule through whatever its transport is — a dedicated, job-scoped credential (an SSH key when SSH is the transport), never a reused operator credential" |
| ⚑ ci-actions `SKILL.md:11-12` — "executes code from anyone who can open a pull request" | **Keep** | With agent-authored PRs this is more true, not less: this repository's own CI runs bot-authored branches continuously. The sentence is the correct threat model for the fleet's actual PR population |
| observability `pipeline.md` — tail-sampling tuning | Drop stands, quarantine confirmed on re-read | Sits under an explicit "if you sample" conditional |
| observability `SKILL.md:9,63` — pager idiom | Drop stands | The household-scale carve-out sits three lines below the pager sentence in the same section, and `alerting.md` owns the lab redefinition |

## Gaps (the direction the original scan could not see)

None found, and the record should say why rather than leave the absence ambiguous: this group's
mechanisms are the most cross-consumed in the fleet — evidence-binding in every Verify section
("break something on purpose once", "paste the run URL", "a green suite proves the tests still
pass, not that the feature still works"), prove-the-instrument discipline throughout, and loop
closures already wired to `runbook`, `restore-drill`, `observability`, and `lab-incident` by name.
tdd.md's structural-guard rule ("prove the guard by deleting the block and watching the test
fail") is this repository's own mutation-proof discipline, generalized — the craft skills were
teaching the program before it was written down.

## Disposition summary

Six flips join the KEEP consensus (KEEP 16 in the
[scan record](prop-002-scan-findings-2026-08-13.md)); two findings worked as one-phrase edits in
ungraded text (`frontend-craft` E2E criterion, `ci-actions` OIDC conditioning), adapters
regenerated; eight drops confirmed with their reasons upgraded where the old reason was merely
"harmless". Group 4 — `sre-tool`, `eng-ladder`, `self-improve-loop`, plus the zero-finding
`root-cause` and `prompt-craft` — remains the last group standing under the original one-human
lens, with the heaviest constraints in the set: `sre-tool` is contract-graded and measured
edit-sensitive, `eng-ladder` is frozen by LADDER-001's pending capture, and `self-improve-loop`
rides LEARN-002's sixteen contracts. Its rescan re-judges under those freezes; it does not lift
them.
