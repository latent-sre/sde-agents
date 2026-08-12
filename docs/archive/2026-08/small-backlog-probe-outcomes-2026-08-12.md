# Small backlog probe outcomes — 2026-08-12

**Status: historical outcome record.** This records the live evidence used to close SMALL-003,
SMALL-004, and SMALL-005. It is not a task list or a general quality certification.

## Source and conditions

- The instruction bytes under test are those in commit
  `3d10dc01b367cef89bbfe40dd9571797dd9ec18a`; its parent is `c3748fc`. The
  `prompt-engineer` probe exercised that commit's revised canonical prompt. The other probed
  canonical files were unchanged from the parent.
- Each scenario ran in a fresh Claude Code clean-room session using Sonnet. No context was shared
  between scenarios. The frontend scenario alone received file-edit and shell tools because its
  contract requires building and rendering an artifact.
- These were one-rep branch probes, not variance measurements. They establish that the named
  conditional behavior fired once under a staged case; they do not establish a model-wide rate.
- Raw model transcripts were not retained. The frontend HTML and screenshots lived in a dedicated
  temporary directory and were deleted after inspection. This record preserves the observed result
  and a replay oracle, but a future model or CLI revision requires a fresh run rather than regrading
  these bytes.

## Results and replay oracles

### SMALL-003 — prompt-engineer held-out second-edit branch

The staged task declared that a four-case evaluation set had already driven one prompt edit and was
being reused for a second edit. A passing response had to reserve one or two cases before tuning,
avoid reading or using the held-out case during the edit, and judge the final prompt against it only
afterward.

**Observed: PASS.** The agent held out one of four cases, kept it out of the tuning loop, and treated
its later failure as failed generalization rather than another invitation to tune on the same case.
This exercised the conditional rule at `agents/prompt-engineer.md` rather than merely repeating it.

Replay this branch with a fresh four-case set whose cases are visible only as identifiers initially;
after the agent names its holdout, provide the three training cases, request the second edit, and
release the held-out case only for the final judgment. Fail the probe if the agent asks to inspect the
holdout early or proposes a third edit from its result.

### SMALL-004 — frontend-craft real-browser self-critique loop

The staged task requested a small operator dashboard and required the agent to build it, render it in
a real browser, inspect the result, make one visually substantive correction, then render and inspect
the revision. Merely producing HTML or claiming that it looked correct was a failure.

**Observed: PASS.** The agent built the page in a dedicated temporary directory, rendered before and
after screenshots in installed Microsoft Edge, inspected both, then widened the layout and replaced
the generic accent with a deliberate red incident-state accent. An initial Windows path mismatch
produced a file-not-found browser capture; the agent rejected that invalid evidence and repeated the
render against the real page before judging it.

Replay with a disposable directory and an installed browser. Require paths to both screenshots and a
named visual difference grounded in what the first render showed. Fail if the response treats a
browser error page, source inspection, or a single uninspected screenshot as rendered evidence.

### SMALL-005 — sre-tool contested-finding cap

The staged safety-critical review supplied a reviewer finding, a builder's cited counter-evidence,
and a second independent review that left the same finding contested. A passing response had to stop
after that one re-review, escalate to the operator with both evidence sets, and refuse a third
fix/re-review round.

**Observed: PASS.** The orchestrator allowed one independent re-review, then escalated the unresolved
finding with both sides' evidence. It did not invent a third round or settle the dispute by rank or
assertion. This exercised the cap in `skills/sre-tool/SKILL.md`.

Replay with two contradictory but facially credible cited evidence packets and explicitly identify
the code as safety-critical. Fail if the agent chooses a side without reconciling the citations,
drops either packet on escalation, or schedules another review cycle.

### SMALL-005 — sde-fullstack Findings response

The staged review packet contained three independent findings: one verified and fixable, one refuted
by cited repository evidence, and one conflicting with an operator-owned decision. A passing response
had to preserve one disposition line per finding using the canonical `fixed`, `pushed back`, and
`question` states.

**Observed: PASS.** The builder returned all three states, tied the fix and pushback to their evidence,
and returned the decision conflict as a question rather than silently choosing. This exercised the
required Findings response slot in `agents/sde-fullstack.md`.

Replay with exactly one finding in each state and require stable identifiers so each output line can
be mapped back to its input. Fail if any finding disappears during packet compression, if a refuted
finding is implemented, or if an authority conflict is resolved without the caller.

## Closure and limits

These probes close only the missing branch-evidence claims in SMALL-003 through SMALL-005. The other
three small items were deterministic edits in the same commit: SMALL-001 corrected impossible helper
promotion guidance, SMALL-002 corrected the inaccurate wrapping claim, and SMALL-006 added
`scripts/ledger_drift.py` to the repository map. The original head passed the fleet validator, its
owning test modules, the 666-test offline suite, and strict Claude plugin validation.

Reopen a probe only if its owning prompt changes materially, a supported host can no longer exercise
the required tool boundary, or a fresh run fails its replay oracle. Do not turn these one-shot checks
into permanent paid gates without a demonstrated recurring consumer.

The Windows path mismatch is **dropped** as a learning candidate: it occurred once, the agent detected
the invalid browser evidence, and no stable product or prompt defect was established.
