# CTX-001 spec — Claude 5-generation definition modernization

**Status: active, one pilot executed, acceptance evidence owed** — written 2026-08-20 under the
operator's standing directive to work CTX-001, which is the implementation authority for the
pilot below; it is not a claim that the *acceptance* has been met.

Read the sequence honestly, because the header first written here contradicted what then
happened. This file opened as `drafted — starts no round, grants no implementation authority`,
copying the convention from LANE-001, and then the `ci-actions` pilot was executed anyway under
the operator's directive. Both cannot be true. The directive is the governing fact, so the status
is corrected rather than the history hidden: a spec asserting it granted no authority, sitting
beside an implementation it authorized, is exactly the stale line that teaches a later reader to
distrust the file.

What remains genuinely un-granted is **acceptance**, not authority: the paired routing evidence in
the Acceptance section has not been bought, so the pilot is landed-but-unmeasured and must not be
reported as validated. It exists because CTX-001's own Next action is "open a bounded spec
choosing the pilot definition and the exact paired-measurement conditions **before editing
anything**", and because the audit below changes which pilot is defensible.

## Problem

CTX-001 asks whether the six published Claude 5-generation context shifts (rules→judgment,
examples→interface design, upfront→progressive disclosure, repetition→tool definitions, manual
memory→auto-memory, simple specs→rich references) transfer to this fleet's 31 canonical
definitions — and requires that any edit be justified by paired before/after evidence, *or* that
the audit record the claim did not transfer to this artifact class.

Nothing had been measured. This spec supplies the measurement and scopes one pilot.

## Audit (measured 2026-08-20, offline)

Two of the six shifts are mechanically measurable across `agents/` and `skills/`. The rest are
judgement calls that a number would misrepresent, and the audit records them in prose instead.

### rules → judgment

349 prohibition-style lines across 31 definitions, densest first:

| definition | kind | body lines | prohibition lines | per 10 lines |
|---|---|---|---|---|
| `sde-fullstack` | agent | 162 | 32 | 2.0 |
| `homelab-platform` | agent | 188 | 31 | 1.6 |
| `code-reviewer` | agent | 142 | 27 | 1.9 |
| `self-improve-loop` | skill | 208 | 25 | 1.2 |
| `sre-tool` | skill | 75 | 22 | **2.9** |
| `frontend-craft` | skill | 68 | 21 | **3.1** |

**Instrument caveat, stated so the figure is not misread as movement.** The 2026-07-31
independent review counted ~190 prohibition-style lines with `sde-fullstack` leading at 24. This
count uses a broader pattern (adding `is not`, `are not`, `cannot`, `will not`, `won't`), so 349
and 32 are **not** evidence that prohibitions grew — the two numbers are not comparable. What
survives comparison is the *ordering*: `sde-fullstack` still leads the agents. Anyone re-running
this must fix one pattern and record it, or repeat this caveat.

### upfront → progressive disclosure

The sharpest finding, and it is not about density but about absence: **8 of 20 skills ship no
`references/` directory at all** — 37,908 bytes of body with no disclosure layer to progress to.

| no-reference skill | body bytes |
|---|---|
| `ci-actions` | 7,024 |
| `upgrade-campaign` | 5,222 |
| `service-onboard` | 5,006 |
| `restore-drill` | 4,740 |
| `host-onboard` | 4,224 |
| `postmortem` | 4,221 |
| `root-cause` | 4,157 |
| `onboarding-map` | 3,314 |

Body-to-reference ratio for the skills that do have one (lower = more progressive):

| body-heavy | ratio | well-disclosed | ratio |
|---|---|---|---|
| `runbook` | 2.13 | `code-craft` | 0.04 |
| `sre-tool` | 1.90 | `prompt-craft` | 0.20 |
| `lab-incident` | 1.55 | `security-audit` | 0.26 |
| | | `frontend-craft` | 0.28 |

### The shifts this audit does not score

- **examples → interface design**, **repetition → tool definitions**, **manual memory →
  auto-memory**: no honest mechanical proxy. Counting examples or repeated phrases measures
  formatting, not whether the definition leans on them. Recorded as unscored rather than
  estimated.
- **simple specs → rich references** is partly covered by the disclosure ratio above, but "rich"
  is a quality claim a byte count cannot make.

## Amendment 2026-08-20 — the pilot moved again, after reading the candidate

The scope below chose `root-cause` on the audit metrics. **Reading it overturned that choice, and
the correction is the more useful finding.**

`root-cause` is 4,157 bytes and carries no `references/`, which is exactly what the
disclosure metric flags. But its body *is* the five-step method, and it is preloaded into
`sde-fullstack` **so that the method is in context**. Moving the method to a reference would force
an extra read at the moment of debugging — defeating the preload it was chosen to improve. The
metric measured the *absence of references*, not whether references would help. Only its worked
hypothesis table (~500 bytes) is genuinely reference-shaped, and a new file for 500 bytes is
ceremony, not disclosure.

External guidance agrees on the division and was checked rather than assumed
(code.claude.com/docs/en/skills, retrieved 2026-08-20 [sourced]): `SKILL.md` is "overview and
navigation" carrying the essentials; supporting files hold "detailed API docs", "usage examples",
and large documents, so they do not load "into context unnecessarily". A compact method skill has
no such surplus.

**Executed pilot: `ci-actions`** — the largest no-reference skill (7,024 bytes) and the one whose
own structure concedes the split. Its sections were "The four rules that prevent the real
incidents" followed by "Everything else worth doing, **briefly**" plus a self-hosted-runner
scenario: essentials, then breadth. Result: **7,543 → 5,096 bytes (−2,447, −32%)**, with
`references/hardening.md` carrying run control, caching, runner pinning, secrets and OIDC, the
fork-PR boundary, linting, release provenance, and the runner rules.

One rule was deliberately **kept in the body** rather than relocated: *a self-hosted runner
executing untrusted PR code is remote code execution on your own hardware — never run fork PRs on
one.* A security boundary that must not wait for a lookup stays where it is read by default; the
mechanics of ephemerality and segmentation went to the reference. That is the general rule this
pilot establishes for the follow-on batch.

**So the shift transfers conditionally, not universally.** It transfers to a skill with an
essentials/breadth seam (`ci-actions`). It does **not** transfer to a compact method skill whose
body is the essential (`root-cause`) — recorded here as the audit's permitted "did not transfer to
this artifact class" outcome for that shape. Any follow-on must read the candidate for a seam, not
sort by the no-references metric.

**Still owed:** the paired routing evidence in Acceptance below. `ci-actions` belongs to
`craft-vs-fullstack` (17 cases, 51 sessions at `--runs 3`) and has exactly **one** live positive,
so it is a fragile detector — this is the skill whose only positive fell 67%→0% in the `f232f77`
round. The byte reduction is `[verified]`; the routing effect is `[unverified]`.

## Follow-on batch assessed 2026-08-20 — one transfer in eight

Every no-reference skill was read for an essentials/breadth seam rather than sorted by the
metric. **`ci-actions` was the exception, not the first of a batch**, so the follow-on the pilot
was meant to unlock does not exist:

| skill | bytes | seam? | why |
|---|---|---|---|
| `ci-actions` | 7,024 | **yes — executed** | "four rules that prevent the real incidents" then "everything else worth doing, briefly" |
| `upgrade-campaign` | 5,222 | no | every section is method; "Plan the campaign" is a 6-step ordered procedure, not breadth |
| `service-onboard` | 5,006 | no | no headings at all — a flat checklist; the checklist is the essential |
| `restore-drill` | 4,740 | no | method (rule / drill / permitted conclusions); "Cadence" is 7 lines, below the cost of a file |
| `host-onboard` | 4,224 | no | no headings — flat checklist, same shape as `service-onboard` |
| `postmortem` | 4,221 | no | method (required structure, feed-it-forward) |
| `root-cause` | 4,157 | no | method, and preloaded *so the method is in context* — see the amendment above |
| `onboarding-map` | 3,314 | not assessed | held for LANE-001 |

The three **body-heaviest skills that already have references** were assessed too, on the theory
that an existing-but-underused reference layer is a different and better-odds shape. It is not:

| skill | bytes | body:ref | seam? | why |
|---|---|---|---|---|
| `sre-tool` | 16,061 | 1.90 | no | six sequential pipeline phases; each is essential and ordered |
| `runbook` | 9,966 | 2.13 | no | the inline template is the **slot-definition** structure, which is precisely what this skill exists to produce. `references/example.md` already carries the complementary piece — 15 slots as a *filled* worked example. Definitions in the body, instance in the reference, is the correct division, not duplication |
| `lab-incident` | 6,501 | 1.55 | no | five ordered mitigation steps plus a security carve-out |

**What this settles for CTX-001.** The "upfront → progressive disclosure" shift transfers to a
definition that already contains a stated breadth section, and to no other shape here — **one
transfer in eleven assessed**. The other ten are method, checklist, or structural-template bodies,
where the body *is* the essential and a reference would add an indirection at the moment of use.
That is the audit's permitted "the published claim did not transfer to this artifact class"
outcome, now recorded with per-skill evidence rather than as a general impression.

Two corollaries worth more than the pilot's bytes:

1. **The disclosure metric must never be used as a work queue.** It ranked `root-cause` a top
   candidate when splitting it would actively damage the preload it was chosen to improve, and it
   ranked `runbook` second when `runbook` already has the correct split.
2. **A high body:ref ratio is not evidence of under-disclosure.** `runbook`'s 2.13 is what a
   correctly-divided template skill looks like. Ratio identifies candidates to *read*, never
   candidates to *edit*.

## Scope — one pilot, and it is not `sde-fullstack`

CTX-001's Next action names `sde-fullstack` as "the highest-density candidate", and by
prohibition count it is. **This spec proposes `root-cause` instead**, for reasons the audit
surfaced:

1. **`sde-fullstack` cannot be piloted in isolation for the named compression candidate.** The
   Learning-bullet specification is not hand-written prose in eleven places — `validate_fleet.py`
   holds `LEARNING_INTAKE_PACKET_SLOT` and `LEARNING_LIFECYCLE_OWNER_PACKET_SLOT` and enforces
   each as a **verbatim substring** of the owning agent's packet. Editing one definition's slot
   fails the gate; the constant and all eleven definitions move together or not at all. That is a
   fleet-wide change, which is the opposite of a bounded pilot.
2. **`root-cause` is a clean, small, high-value test of the disclosure shift.** 4,157 bytes, no
   reference layer, and it is one of the five skills `sde-fullstack` preloads — so a successful
   split is measurable twice: as a definition change (CTX-001) and as a per-spawn preload
   reduction (CTX-003).
3. It carries **no preload canary** (canaries live only in `backend-craft` and `frontend-craft`),
   so the probe's proof is not at stake.

## Out of scope

- The Learning-slot compression. It is a fleet-wide slot revision gated on the packet-grammar
  behavioral contracts and `scripts/packet_lint.py`'s tests; it needs its own spec and its own
  paired evidence. Recorded here so it is not smuggled into a pilot.
- The seven other no-reference skills. If the pilot succeeds they become a follow-on batch; if it
  regresses, the audit records that progressive disclosure did not transfer to this artifact class
  and they stay as they are.
- `onboarding-map` and `eng-ladder`, held for LANE-001 and LADDER-002.

## Acceptance

1. Paired before/after **routing** runs for `root-cause`'s overlapping clusters
   (`continuous-improvement`, `investigation`, `verification-seam` — 41 cases, 123 sessions at
   `--runs 3`) under identical recorded conditions, with **no negative-case regression**.
   `evals/baselines/` may supply the before side only if its recorded conditions match.
2. Behavioral contracts green for any agent whose preloaded set changed — `sde-fullstack`, whose
   `loop-*` contracts already exercise the preload path.
3. The measured byte delta recorded per file, and the disclosure ratio restated.
4. Regenerated adapters, validator and full suite green.
5. **A written stop rule, honored:** if the pilot regresses any positive below its before-side
   rate outside measured noise, the split is reverted and the audit records that the shift did not
   transfer. No second attempt on the same definition without new evidence about *why*.

## Measurement conditions (fixed before any edit)

Model `sonnet`; `--clean-room`; `--runs 3`; timeout 180; concurrency 4; CLI version recorded from
the run; the exact revision under test recorded as bytes, not as a branch name.

**One writer per checkout.** The tree is frozen for the duration of each capture — no edits, no
adapter regeneration, no roadmap writes. This is stated explicitly because it was violated on
2026-08-20: a 99-session `homelab-ops` sweep was invalidated mid-run by concurrent edits, the
runner refused to write `benchmark.json`, and the session budget was spent for no citable result.
The rule is `AGENTS.md`'s "One writer per checkout"; the cost of ignoring it is one full sweep.

### The two owed captures, as commands

Recorded here rather than left in a session transcript, so the next operator does not re-derive
them. Both are unbought as of 2026-08-20.

```bash
# CTX-002 acceptance — 99 sessions. Covers the six edited homelab-ops descriptions.
# The before side already exists at evals/baselines/2026-08-18-ctx-002/after-repair/ (at f232f77),
# so only this after side costs anything.
python3 scripts/eval_routing.py evals/routing/homelab-ops.json \
  --runs 3 --clean-room --model sonnet --timeout 180 --concurrency 4 \
  --output-dir evals/baselines/2026-08-20-ctx-002-floor/after/homelab-ops

# CTX-001 pilot acceptance — 3 sessions, against the contract written with the pilot.
python3 scripts/eval_behavioral.py --case 'ci-actions-*' \
  --runs 3 --clean-room --model sonnet
```

`craft-vs-fullstack` (17 cases, 51 sessions) additionally covers the trimmed `backend-craft`,
`ci-actions`, `code-craft`, and `frontend-craft` **descriptions**. It does **not** cover the
`ci-actions` body split — routing is description-driven, and the body change is what the
behavioral case above exists to reach.

## Rollback

A single revert of the pilot commit restores `root-cause`'s body; the reference file is deleted
with it. Nothing else depends on the split — no validator constant, no canary, no contract text.

## Round exit

The round closes when either the pilot meets acceptance and the follow-on batch is scoped, or the
audit records the non-transfer with its evidence. Either outcome retires this spec to
`docs/archive/`.
