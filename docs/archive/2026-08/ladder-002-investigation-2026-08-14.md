# LADDER-002 investigation — why eng-ladder's advertised modes under-fire (2026-08-14)

**Question.** The LADDER-001 capture measured `eng-ladder`'s three advertised modes firing 3/3
(altitude question), 0/3 (assess-at-a-bar, also 0 in the 2026-07 anchor), and 0/3 (the
consult-fork shape). Is the cause the schema, the description phrasing, or the handoff?

**Method.** Local evidence (raw frontmatter, runner detection internals, cluster comparison,
description git history, listing-budget arithmetic), four single-session diagnostic probes
(sonnet, `--plugin-dir .`, transcripts retained — one run each, ambient rather than clean-room:
directional evidence, deliberately not comparison-grade and not diffable against the stored
baseline), and an external research pass on 2025–2026 skill-triggering findings
(egress-constrained: Anthropic docs and GitHub read directly; arXiv/practitioner sources
excerpt-mediated — weight accordingly, and the recurrence is recorded on ledger candidate
`lc_854a12b5`).

## Verdict, by suspect

**Schema — cleared, on five independent checks.** The frontmatter parses (591/1024 chars, no
plain-scalar colon trap); the description has been byte-identical since it shipped (the under-fire
is congenital, not drift); the same description fires 3/3 on the altitude mode; the runner's
detection is sound (it reads real `Skill`/`Agent` tool calls and handles the tool-restricting
launch quirk); and the one silent-truncation mechanism research surfaced — a reported ~8,000-char
skill-listing budget that shortens descriptions from the end (claude-code #64606, closed
not-planned; the fleet's 20 descriptions sum to 11,260 chars, so it *would* bite if active — and
eng-ladder's assess clause starts at char ~480) — was **falsified by direct probe** on CLI
2.1.231: a headless session quoted the eng-ladder listing entry verbatim in full, assess clause
included. Keep the arithmetic in mind for future skills; it is not the cause today.

**Assess mode (0/3) — instrument artifact in the eval case, not a description defect.** The
runner spawns every session in an empty `TemporaryDirectory()` cwd
(`scripts/eval_routing.py:773`), and the case prompt says "Assess **this change** at the
principal level" — a dangling referent. Probes, one run each:

- *Repo cwd (referent exists):* the session resolved "this change" via `git log`, **invoked
  `sde-agents:eng-ladder` via the Skill tool**, read `agents/principal-engineer.md` (Mode 2's own
  read-the-bar instruction), and returned a faithful meets/gaps assessment.
- *Empty cwd (eval conditions):* the session inspected the directory, correctly reported there is
  no change to assess, asked for one — and **named `eng-ladder` as the skill it would use** once
  given the artifact. Routing resolved correctly; invoking would have been wrong; firing-based
  grading scores the exchange 0.

The case cannot fire as written, in the harness as built — an underspecified handoff (the fleet's
own #1-documented multi-agent bug) living inside its own eval suite. The repair goes to the
**case** (embed a small concrete diff in the prompt so the mode is measurable), which is an
eval-bytes change starting a new baseline lineage — distinct from the forbidden move of loosening
a grader to pass.

**Consult-fork mode (0/3) — do-the-work bias, and the substance was correct.** The probe session
made zero tool calls and performed the consult inline: settled the trust-model fork with
principal-grade reasoning (internal CA over per-host self-signed, argued from `verify-full` +
topology change), deferred execution to `sde-agents:homelab-platform`, and proposed walking the
rollout/rollback plan past the operator before applying. That is the Mode 1 calibration's
substance — deliberate treatment of the embedded decision, builder/platform execution, an
operator gate — with no invocation for firing-based grading to see. External corroboration
[sourced]: "tool underuse" is a named finding (SMART, ACL Findings 2025 — large models "neglect
to call essential tools"); practitioner trials put passive "Use when…" descriptions at ~37–77%
activation vs ~100% for imperative directive forms (650-trial experiment, excerpt-mediated);
claude-code #32184 measured 100%-precision/0%-recall skill invocation in one `claude -p`
environment (read directly; closed not-planned). If the fleet wants this calibration *measured*
rather than observed, the honest instrument is a behavioral-contract case grading the verdict's
content (builder-owned + named consult + no wholesale re-owning), not a routing case grading
invocation.

**Phrase — a contributing suppressor, demonstrably not fatal.** The description's lead gate
("Use when the right altitude is genuinely unclear… a scoped change with an obvious owner …
routes straight to its builder or craft skill **without this**") reads as an exclusion when a
prompt states its level — and external guidance treats descriptions as literal routing logic, with
negative-routing clauses working as suppressors by design. But both probes show the phrase
resolving correctly when a referent exists (fired) or is absent (named the right skill and asked).
No controlled study isolates conditional-clause suppression [unverified as a named finding]; the
directive-vs-passive activation gap is the adjacent evidence. Conclusion: a description rewrite is
**not** the indicated repair for the measured 0/3s — the two failing cases fail for
non-description reasons.

## What this changes for LADDER-002

- Original option (b) "repair the assess phrasing" **dissolves** — the description routes the
  assess ask correctly; the case is what cannot fire. Its successor is an eval-case repair
  (inline diff in the prompt), which is cheap and offline to author, T3 only to re-measure.
- The consult-fork positive gains an honest disposition path: port the calibration to a
  behavioral contract (grade the verdict, not the firing), and either retire the routing positive
  or keep it as documentation of what firing-based grading can see.
- Option (a), the Mode 3 trim, is unchanged — and the no-truncation probe confirms the Mode 3
  clause does occupy live listing context in every session, so its cost is real.
- The negatives' 0%-fire conclusion from LADDER-001 is untouched — nothing here weakens the
  calibration verdict; the probes reinforce it (the consult-fork session did not over-escalate
  even inline).

**Residual observed, dropped with reason:** the probe's own Mode 2 assessment flagged that the
LADDER-001 outcome record's lesson 2 (stale-anchor-as-shape-check) is a reusable eval-methodology
procedure not yet routed to an owning reference. Recorded here as observed; the lesson lives in
the dated outcome record, and it is free evidence if `evals/README.md` is edited for a
substantive reason.
