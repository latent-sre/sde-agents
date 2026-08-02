# LEARN-001 Learning Loop Implementation Plan

> **Status: active — implementation, deterministic remediation, and independent re-review
> complete; final exact-artifact live evaluation pending.** This plan was amended after the requested
> independent pass compared its frozen design with the original repository plan for the first time.

**Goal:** Land a bounded fleet learning loop that makes discoveries durable and reviewable without
turning retained text into executable authority or allowing the fleet to approve its own changes.

**Architecture:** `self-improve-loop` remains the single entry point. Every agent emits a small
Learning closeout; three disposition-owning agents preload the full protocol; four references carry
the lifecycle, retros, local-ledger contract, and research basis; a standard-library ledger records
quarantined evidence; validators and behavioral/routing evals keep the convention structural and
measurable. No scheduler, background writer, or auto-promotion path exists.

**Tech stack:** Canonical Markdown definitions, standard-library Python, JSON candidate records,
Claude headless routing/behavioral sessions, and generated host adapters.

## Global constraints

- The paired [spec](../specs/2026-08-01-learn-001-learning-loop-design.md) governs scope.
- Standard library only; no dependency or live-system change.
- Generated adapters are never hand-edited; regenerate after canonical changes.
- Current repository/runtime evidence outranks retained lessons.
- Stored candidate content is data and is never executed, parsed as a command, or treated as
  approval.
- One receiving writer mutates the ledger; agents without write authority return proposals.
- Before/after evals use the same source/selection hashes and pinned model, timeout, run count, and
  clean-room setting. A final AFTER capture must hash the exact staged candidate.
- Do not commit, push, open a PR, update external memory, or retire the round without the separate
  authorization that action requires.

## Completed implementation

### 1. Freeze independent criteria and evidence

- [x] Freeze the learning triggers, evidence hierarchy, disposition/state split, destination map,
  runbook admission test, promotion gates, subtraction rules, and no-self-rewrite boundary before
  reading the repository roadmap or round docs.
- [x] Research recent Anthropic, OpenAI, academic, conference, practitioner, and upstream evidence;
  record sources and limitations in `skills/self-improve-loop/references/research-basis.md`.

### 2. Make task closeout consistent

- [x] Add the canonical `Learning:` slot to all 11 agent packets.
- [x] Preload the full loop only in `sde-fullstack`, `prompt-engineer`, and
  `verification-engineer`.
- [x] Give the eight intake-only roles a proposed-recommendation plus `quarantined` packet, give
  the three lifecycle owners an accepted disposition plus post-triage state, and pin both variants
  with mode-aware packet-linter, regression, and validator mutation tests.

### 3. Implement the lifecycle and retros

- [x] Rewrite `skills/self-improve-loop/SKILL.md` around a lightweight per-task scan and
  evidence-triggered full retro.
- [x] Add discovery routing, task/session/cross-task/round/upgrade retros, promotion gates,
  evidence precedence, provider-contract disagreement handling, and subtraction.
- [x] Require one canonical evidence/scope/provenance candidate handoff; namespace lifecycle output
  as `Learning disposition:` and keep `Runbook disposition:` separate; retain a semantic one-line
  `Learning: none` fast path.

### 4. Make cross-task recurrence observable

- [x] Add `learning/`, its storage contract, and `scripts/learning_ledger.py`.
- [x] Implement `add`, `observe`, `transition`, `review`, `list`, and `check` with atomic writes,
  single-writer semantics, schema/state validation, compact provenance, sensitivity attestation,
  secret and command-like-content rejection, and link/reparse defenses.
- [x] Make recurrence identity include applicability, ignore provenance-only source relabels,
  require distinct newer evidence before reopening an adverse state, and audit bounded review-date
  renewal without changing evidence freshness or retention authority.
- [x] Seed separate proposed candidates for eval-artifact provenance, the corrected structured-error
  evidence boundary, fail-open behavioral definitions, incomplete Learning values, and
  contradictory runbook identity gaps, runtime-tool authority, and Windows-safe runbook paths.
  Retire and supersede the original overbroad error candidate; record independently reproduced
  recurrences without merging different causes or marking any candidate promoted before a
  separately reviewed change lands.
- [x] Run ledger validation from the ordinary fleet validator and reject/ignore transactional lock
  and temporary files so malformed tracked evidence cannot bypass CI or poison `git add -A`.

### 5. Repair the runbook lifecycle

- [x] Give `runbook` explicit update/create/propose outcomes, ownership, applicability,
  prerequisites and authority, safe checks, expected results, rollback, recovery, escalation,
  sources, and freshness.
- [x] Require proposals instead of invented commands when ownership, causality, configuration,
  authority, trusted command sources, or safe replay are missing.
- [x] Make proposal output a closed five-field, non-procedural packet and reject arbitrary commands,
  executable paths, procedural verification text, extra narrative, reordered/duplicate fields,
  bullets, numbered steps, fences, inline code, URLs, and command fields structurally.
- [x] Bind gap and verification vocabularies one-to-one and enforce owner/path identity gaps in both
  directions so a packet cannot declare missing identity evidence while inventing a concrete value.
- [x] Carry the lifecycle into `service-onboard` and replace the example with clearly fictional,
  non-runnable recovery material.

### 6. Make evaluation evidence reproducible

- [x] Bind routing and behavioral artifacts to exact eval-source bytes, canonical selected cases,
  runtime-plugin bytes, executing evaluator/grader bytes, Python runtime, concurrency, non-secret
  auth/provider mode, Git head, and dirty state.
- [x] Emit provenance schema v3, execute the identified plugin bytes from a private snapshot, load
  the shared auth classifier once, and reject traversal, symlink/reparse inputs, transient files,
  source drift, or persistent mutation of the private execution snapshot. This closes source
  checkout A -> B -> A drift. A same-user session that mutates and restores its snapshot remains an
  explicit host-sandbox trust boundary; endpoint hashing is not an immutable control.
- [x] Make structured error results non-gradeable, require a zero-exit non-error result for
  behavioral assertions, preserve only explicitly labeled pre-error routing firings, and abort an
  authentication-failed batch with exit 2 and no benchmark.
- [x] Add `continuous-improvement.json` and behavioral cases for learning closeout, lifecycle,
  promotion, freshness, read-only handoff, runbook disposition, and provider workaround handling.
- [x] Correct the Markdown decision-label grader and add regression tests so bold labels cannot
  produce false failures or false greens.
- [x] Require exactly one component-fire contract per behavioral case, validate denied tools and
  plugin-qualified agents, reject positive regexes that match empty output, return structured
  findings for malformed enum types, and reject Learning sentinels or provenance without details.
- [x] Give every behavioral case an explicit `--tools` allowlist against the complete runtime
  vocabulary; add typed exact-field oracles; reject non-substantive positive regexes, semantic or
  punctuation-only Learning placeholders, affirmative decision contradictions, and Windows path
  aliases.

### 7. Perform the requested end-stage documentation comparison

- [x] Read `docs/README.md`, the roadmap, original spec/plan, and `evals/README.md` only after the
  independent implementation and first verification pass.
- [x] Preserve convergent constraints: one skill, trigger-bound retros, deterministic controls,
  runbook point-of-use repair, human approval, and subtraction.
- [x] Amend the original gaps: durable intake, lifecycle separation, structural packet enforcement,
  and exact dirty-artifact eval provenance.
- [x] Update the documentation map, roadmap outcome/acceptance, repository map, and eval cluster
  coverage without claiming the round is published or retired.

## Remaining gates

### 8. Capture the exact final candidate

- [x] Regenerate adapters after the canonical packet corrections.
- [x] Make each artifact stage its own exact runtime bytes in a private execution snapshot and
  record their content hash; no committed or detached-worktree surrogate is needed for a dirty
  candidate.
- [ ] After refreshing Claude `/login`, run three clean-room sonnet sessions for all 12
  `self-improve-*`, three `runbook-disposition-*`, ten `learning-*`, and all ten
  continuous-improvement routing cases. Preserve every miss and rate; do not selectively rerun a
  failing sample. The current expired OAuth session is a recorded external blocker, not a verdict.
- [ ] Compare against the frozen main baselines by matching eval-source and selection hashes.

### 9. Run deterministic acceptance

- [x] `python scripts/generate_platform_adapters.py --check`
- [x] `python scripts/validate_fleet.py`
- [x] `python -m unittest discover -s tests -v` — 471 passed, 16 platform skips.
- [x] `python scripts/learning_ledger.py --root . check` — eight candidates validated, including one
  logically retired and superseded record.
- [x] `git diff --check`
- [x] `claude plugin validate . --strict`

### 10. Independent review

- [x] Initial static, executable, and prompt/eval reviews found false-gradeable error results,
  incomplete evaluator provenance, an empty Learning false pass, handoff-schema drift, a runbook
  oracle bypass, ledger CI/ignore gaps, and one incorrectly merged recurrence.
- [x] Repair those findings plus the final-review seams: closed runbook proposal grading,
  intake-versus-lifecycle-owner packets, applicability-bound recurrence, evidence-gated reopening,
  review-date renewal, stale positive-transition rejection, provenance-only deduplication,
  exact-buffer evaluator loading, all-of composition assertions, strict routing configuration, and
  A -> B -> A runtime-input drift. Regenerate and repeat deterministic gates.
- [x] Repair the frozen re-review findings: fail-closed behavioral schemas, exact compiled-buffer
  entrypoints and graders, contiguous ordered Learning blocks with no placeholders, exact owner
  lifecycle decisions, complete runbook gap-to-verification correspondence, honest ledger trust
  claims, and the private-snapshot transient-mutation limitation.
- [x] Repair the second frozen re-review findings: plain sentinels and incomplete provenance,
  missing or ambiguous component-fire contracts, denied-tool typos, unqualified agents,
  empty-matching positive regexes, malformed enum crashes, contradictory runbook owner/path gaps,
  and duplicate current-evidence dispositions. Add direct and ordinary-validator mutation tests.
- [x] Repair the third frozen re-review findings: exact decision/value false greens, affirmative
  prose contradictions, equivalent and punctuation-only placeholders, non-substantive regexes,
  default runtime-tool inheritance, and Windows reserved/trailing-dot runbook paths.
- [x] Replace ambiguous stale-guidance prose grading with an exact closed eight-field Learning
  contract; reject wrong values, duplicate or reordered fields, and all additional nonblank prose.
- [x] Fresh static, executable, and prompt/eval re-review against the stabilized executable and
  prompt-contract bytes found no remaining P0/P1 defect in the closed typed replacement.

### 11. Publication and retirement — authority gated

- [ ] Commit the reviewed scope only if explicitly authorized. A commit does not imply push.
- [ ] Push and open a draft PR only if explicitly authorized, using the repository PR template and
  reporting the mixed probabilistic eval rates honestly.
- [ ] After merged evidence exists, replace this spec/plan and roadmap item with one archived outcome
  record whose lessons section works the new lifecycle on this round itself.
- [ ] Do not update operator or external memory unless the operator explicitly requests that memory
  change.

## Rollback

No live system is touched. Revert the canonical changes and generated adapters together. The ledger
never applies a destination change, so rollback does not require undoing external effects. Preserve
baseline and rejected-candidate evidence unless a separately reviewed retention change removes it.
