# LEARN-001 outcome record — fleet learning loop — 2026-08-02

**Status: historical outcome record.** The round is closed: PR #57 merged to `main` (`8c2fca3`).
The amended spec and plan retired to this record per `docs/README.md` rule 4; Git history retains
their full text (`docs/superpowers/specs/2026-08-01-learn-001-learning-loop-design.md` and
`docs/superpowers/plans/2026-08-01-learn-001-learning-loop.md` at `98c5c20`).

## What landed

- **`self-improve-loop` as the single learning entry** — a per-task Learning scan with an honest
  `Learning: none` fast path, an evidence-triggered full retro, and four on-demand references:
  discovery routing (event→destination table with promotion thresholds that never authorize),
  retro protocol (task/session/cross-task/round/upgrade), the local-ledger contract, and the
  dated public research basis (Apr–Aug 2026 window, provenance-classed).
- **A closed `Learning:` closeout in all 11 agent packets** — eight intake-only roles emit
  quarantined proposals; `sde-fullstack`, `prompt-engineer`, and `verification-engineer` preload
  the full lifecycle — pinned by packet-linter and validator mutation tests so the convention
  cannot silently vanish from one agent.
- **`learning/` + `scripts/learning_ledger.py`** — fail-closed, single-writer, schema-checked
  candidate intake with lifecycle states, applicability-bound recurrence identity,
  evidence-gated reopening, and bounded review renewal. The ledger observes; it never edits or
  approves a destination.
- **Runbook lifecycle** — `runbook` and `service-onboard` gained update/create/propose admission
  with ownership, applicability, and freshness; missing evidence yields a closed five-field
  proposal, never invented commands. Found-wrong-in-use duties grafted where docs get used
  (`runbook`, `homelab-platform`).
- **Eval provenance v3** — both runners bind exact source/case/runtime/evaluator bytes, execute a
  private frozen plugin snapshot, treat structured errors as non-gradeable, and abort an
  auth-failed batch without writing. Built independently in-round; prevented recurrence of the
  same round's own measurement contamination (below).
- **Measurement surface** — `retro-boundary` and `continuous-improvement` routing clusters and
  the learning/runbook behavioral contracts, all listed in the eval coverage table.
- **`researcher` deterministic-reads rule** — encoded after its recorded recurrence trigger fired
  (three fetch-layer fabrications in one research round; trigger set 2026-07-30).

## Measured evidence

- **A real routing regression was caught by the round's own cluster and fixed.** The reconciled
  description dropped the operator's plain retro phrasings: on the byte-identical cluster under
  identical clean-room sonnet conditions, `pos-micro-retro` fell 100%→33% (`d027755`), recovered
  to 67% after the vocabulary merge (`4be21cd`); `pos-task-retro` 33%→0%→33%. Negatives fired 0%
  in every generation. Authoritative pair: `evals/baselines/2026-08-01-learn-001/pair-v3/`.
- **Final live captures** (clean-room, sonnet, 420 s, 3 runs, no selective reruns):
  `continuous-improvement` routing 9/10 (the historical weak positive improved 0%→33%);
  behavioral under the final strict graders — self-improve 7/12, runbook-disposition 2/3,
  learning-slot 3/10. On the ten shared self-improve cases, pass-runs rose 15→19→22 of 30
  across frozen-before → committed-after → live; the committed baselines were graded by earlier,
  looser evaluator bytes, and v3 provenance makes that drift visible by construction.
- **Deterministic gates at close**: 471 tests OK, validator and adapter byte-diff clean,
  `claude plugin validate --strict` passing — re-verified independently in a clean worktree at
  `98c5c20` and again at the merged base.

## How it was built

Two independent implementations, reconciled under an operator ruling. The original pass ran the
repo's round process (spec → plan → paired baseline → implementation → gates). An independently
frozen sibling pass — deliberately reading no round docs until its own comparison stage —
converged on every governing boundary (single entry skill, trigger-bound retros, deterministic
controls, point-of-use runbook repair, human approval, subtraction) and amended five real gaps
into the spec: durable intake, lifecycle separation, structural packet enforcement, exact
eval provenance, and structured-error grading. Reconciliation review found and repaired two
defects (below). The final branch is measurably better than either solo effort.

## Corrections recorded

- **A contaminated benchmark was unknowingly committed, then removed** (`98c5c20`). The capture
  ran while the second session rewrote the shared tree; its invalidity ruling existed only in the
  first session's conversation, so the sibling had no way to know. Lineage note:
  `evals/baselines/2026-08-01-learn-001/README.md`.
- **The reconciled description regressed operator phrasings** — caught and fixed as measured
  above; the sibling's own cluster could not see it because its cases were written in its own
  vocabulary. Independent-vocabulary clusters are the working control.
- **Two original-spec constraints were overridden by the amendment, with evidence**: "no
  validator rule changes" (narrow rules landed with mutation tests; GRAPH-002 must preserve those
  tripwires) and non-clean-room measurement (the final pair is clean-room; the original
  non-clean-room before-capture remains as history, labeled non-comparable).
- Earlier in-round reporting said "six" contracts fail the final graders; the correct count is
  **seven** at 0/3.

## Lessons — routed per this round's own table

- **Concurrent sessions must not share a checkout** — an eval capture measured a moving tree and
  an uncommitted iteration was overwritten. First occurrence → filed, not encoded: ledger
  candidate `lc_de3dbac7d78148e89494a07e96e8afb1` (quarantined); encodes as an AGENTS.md rule on
  a second occurrence, per the thresholds.
- **Seven behavioral contracts outpace current model compliance** → filed as roadmap item
  LEARN-002 (the round's one encoded follow-up).
- **Summarized-fetch fabrication** → already encoded this round (`researcher` Method §3) — the
  trigger-bound lesson from 2026-07-30 whose fingerprint matched.
- **Grader drift between baselines** → structural: v3 provenance binds evaluator bytes, so a
  stricter grader can never silently masquerade as a behavior change again.
- **Watch-metrics for the next round close** (data, not work): the Learning-slot `none`-rate and
  the ledger's organic-candidate count — the two numbers that decide whether the closed packet
  contract earns compression.

## Residuals

- LEARN-002 owns the seven strict-grader failures; two flaky contracts (2/3) ride along.
- Two `retro-boundary` positives fire 0% under clean-room in every generation and 67–100%
  outside it — documented as harness-conditioned, not chased at n=3.
- Plugin version: this closing change bumps 1.5.0 → 1.6.0 across the four manifests and the
  installed copy follows; the merged round itself shipped at an unbumped version for one day.
