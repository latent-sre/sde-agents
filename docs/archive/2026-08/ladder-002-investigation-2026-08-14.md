# LADDER-002 investigation — why eng-ladder's advertised modes under-fire (2026-08-14)

**Question.** The LADDER-001 capture measured `eng-ladder`'s three advertised modes firing 3/3
(altitude question), 0/3 (assess-at-a-bar, also 0 in the 2026-07 anchor), and 0/3 (the
consult-fork shape). Is the cause the schema, the description phrasing, or the handoff?

**Method.** Local evidence (raw frontmatter, runner detection internals, cluster comparison,
description git history, listing-budget arithmetic), four single-session diagnostic probes — one
run each, ambient rather than clean-room: directional evidence, deliberately not
comparison-grade and not diffable against the stored baseline. Probe transcripts were
session-local and are deliberately **not** committed — the same rule that gitignores the probe
and pilot run logs: raw model text stays out of the tree, and a round's conclusions land as the
reviewed quotes this record carries. The probes are instead replayable exactly; each is
`claude -p "<prompt>" --model sonnet --plugin-dir <repo> --output-format stream-json --verbose`
with: (1) the `pos-engladder-assess` prompt verbatim, cwd = the repo checkout; (2) the
`pos-embedded-principal-fork-consult-required` prompt verbatim, cwd = the repo checkout; (3) the
assess prompt verbatim, cwd = an empty temp directory (the eval's condition); (4) a **blind**
listing dump — "quote the complete entry for `sde-agents:eng-ladder` exactly, character for
character", cwd = an empty temp directory so no file read can substitute for the listing, with
the prompt disclosing none of the target text, and the output diffed offline against the
canonical description bytes. (An earlier form of this probe named the assess clause in its own
question and ran where the file was readable — review correctly rejected it as unable to
distinguish listing-read from echo or file-read; the blind rerun reproduced the full 591-char
description byte-identically, Mode 3 tail included, which only the live listing could supply.)
Prompts (1)–(3) are the case bytes
in `evals/routing/ladder.json` at `7605e22`. Expect run-to-run variance: these are one-sample
observations of a probabilistic router, and a replay tests the mechanism, not the exact
transcript. The external research pass covers 2025–2026 skill-triggering findings
(egress-constrained: Anthropic docs and GitHub read directly; arXiv/practitioner sources
excerpt-mediated — weight accordingly, and the recurrence is recorded on ledger candidate
`lc_854a12b5`).

## Verdict, by suspect

**Schema — cleared, on five independent checks.** The frontmatter parses (591/1024 chars, no
plain-scalar colon trap); the description has been byte-identical since it shipped (the under-fire
is congenital, not drift); the same description fires 3/3 on the altitude mode; the runner's
detection is sound (it reads real `Skill`/`Agent` tool calls and handles the tool-restricting
launch quirk); and the one silent-truncation mechanism research surfaced — a reported ~8,000-char
skill-listing budget that shortens descriptions from the end (claude-code issue #64606, read
directly, closed not-planned; the budget figure itself is excerpt-sourced from claudefa.st's
skill-listing-budget guide; the fleet's 20 descriptions sum to 11,260 chars, so it *would* bite
if active — and eng-ladder's assess clause starts at char ~480) — was **falsified by blind
probe** on CLI 2.1.231: from an empty cwd, with the prompt disclosing none of the target text, a
headless session reproduced the full 591-character description byte-identically (verified by
offline diff against the canonical file), assess clause and Mode 3 tail included — bytes only
the live listing could supply. Keep the arithmetic in mind for future skills; it is not the
cause today, in the observed session.

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

**Consult-fork mode (0/3) — leading hypothesis: do-the-work bias, with the substance correct in
the one observed run.** Held as a hypothesis, not an established cause: the stored benchmark
records only firing data for the three clean-room failures, and the inline-consult behavior was
observed in one ambient probe — the general tool-underuse literature makes the reading plausible
without proving all three failures shared it. The behavioral port below is the instrument that
would confirm or kill it. The probe session
made zero tool calls and performed the consult inline: settled the trust-model fork with
principal-grade reasoning (internal CA over per-host self-signed, argued from `verify-full` +
topology change), deferred execution to `sde-agents:homelab-platform`, and proposed walking the
rollout/rollback plan past the operator before applying. That is the Mode 1 calibration's
substance — deliberate treatment of the embedded decision, builder/platform execution, an
operator gate — with no invocation for firing-based grading to see. External corroboration
[sourced]: "tool underuse" is a named finding (SMART, ACL Findings 2025, arXiv 2502.11435 —
large models "neglect to call essential tools"); practitioner trials put passive "Use when…"
descriptions at ~37–77% activation vs ~100% for imperative directive forms (Ivan Seleznov's
650-trial experiment, medium.com/@ivan.seleznov1 "Why Claude Code Skills Don't Activate…",
excerpt-mediated — its methodology could not be independently examined behind the egress proxy);
claude-code issue #32184 measured 100%-precision/0%-recall skill invocation in one `claude -p`
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
- Option (a), the Mode 3 trim, is unchanged — and the no-truncation probe shows the Mode 3
  clause occupying live listing context in the observed session (one ambient probe, CLI 2.1.231),
  which is representative evidence for the clause's per-session cost, not proof across every
  configuration or later CLI.
- The negatives' forbidden-sets-at-0%-fire conclusion from LADDER-001 is untouched — nothing here
  weakens the
  calibration verdict; the probes reinforce it (the consult-fork session did not over-escalate
  even inline).

**Residual observed, dropped with reason:** the probe's own Mode 2 assessment flagged that the
LADDER-001 outcome record's lesson 2 (stale-anchor-as-shape-check) is a reusable eval-methodology
procedure not yet routed to an owning reference. Recorded here as observed; the lesson lives in
the dated outcome record, and it is free evidence if `evals/README.md` is edited for a
substantive reason.
