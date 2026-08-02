# LEARN-001 — the fleet learning loop (spec)

> **Status: active round.** Approved scope and acceptance boundaries for LEARN-001. This spec was
> amended on 2026-08-01 after an independent research and implementation pass that deliberately did
> not read the repository roadmap, this spec, or its paired plan until the comparison stage. Where
> the original narrow plan conflicts with this amendment, this file governs.

## Source and authority

- Operator commission 2026-08-01: give the fleet a consistent, ongoing improvement-and-learning
  loop; tell every agent what to do with a discovery; repair or create admitted runbooks when the
  evidence supports it; run retros that look for what the loop itself missed; keep the mechanism
  local to this fleet; and ground it in recent Anthropic, OpenAI, academic, conference, and
  practitioner evidence.
- Public research ledger:
  [`skills/self-improve-loop/references/research-basis.md`](../../../skills/self-improve-loop/references/research-basis.md).
  It keeps provider contracts, research claims, practitioner reports, and upstream source evidence
  separate and records limitations rather than blending them into one authority class.
- Canonical implementation: `agents/`, `skills/`, `scripts/`, `learning/`, and `evals/` in this
  repository. Generated adapters and documentation never override those sources.

## End-stage comparison with the independently frozen design

The original round documents and the independent pass converged on important boundaries:

- keep `self-improve-loop` as the single learning entry rather than add another persona;
- make retros event-triggered, not a cron job or an unfulfillable background promise;
- route recurring mechanical failures into deterministic controls instead of more prose;
- fix a wrong runbook at the point of use when evidence, ownership, authority, and scope support it;
- preserve human review and forbid a candidate from approving its own promotion;
- subtract stale or harmful guidance instead of building an append-only instruction bank.

The comparison also exposed five material gaps in the original narrow scope:

1. A conversation-only handoff could not make recurrence observable across tasks. LEARN-001 now
   includes a repository-local, fail-closed candidate ledger that stores compact evidence records,
   not transcripts or executable instructions.
2. A routing table without a lifecycle could not distinguish intake, disposition, approval, and
   promotion. The amendment separates `skip/add/merge/supersede/drop` from
   `quarantined/proposed/approved/promoted/rejected/inconclusive/retired`.
3. A prose-only Learning convention could silently disappear from one agent. All agent packets now
   carry the same lightweight slot, while a validator and packet linter pin the structural contract.
4. A before/after artifact that named only a Git checkout could not prove which dirty runtime files
   were evaluated. Both eval runners now bind the exact eval-source bytes, selected cases, runtime
   plugin content, executing evaluator/grader files, Python runtime, concurrency, non-secret auth
   mode, Git head, and dirty state. Version-3 artifacts execute a private copy of the identified
   plugin bytes, so an A -> B -> A source edit cannot mix runtime inputs while leaving equal endpoint
   hashes. Source drift and persistent private-snapshot mutation fail closed; transient same-user
   snapshot mutation remains a host-sandbox write-isolation boundary, not an endpoint-hash claim.
5. A structured API error could previously be graded as model output and even green a negative.
   Error results now supply neither ordinary no-fire nor final-output evidence; routing may retain
   only an explicitly labeled component firing observed before the error. Behavioral grading
   requires exit zero plus a non-error final result, and authentication failure aborts the batch
   without writing a benchmark.

The original fixed “twice for a rule / third time for a skill” thresholds were retained only where
they describe a useful default for normalized mechanical recurrence. They do not override severity,
transfer evidence, ownership, or deterministic safety failures, and they never authorize promotion.

## Scope — what this round implements

1. `skills/self-improve-loop/SKILL.md` defines the lightweight scan, evidence-triggered full retro,
   evidence/authority boundaries, one disposition and destination, promotion gates, and honest
   `Learning: none` closeout.
2. Four on-demand references define discovery routing, task/session/cross-task/round/upgrade retros,
   repository-local ledger use, and the dated public research basis.
3. Every canonical agent packet gains the same lightweight `Learning:` slot. Eight intake-only
   roles emit an untrusted proposed recommendation in `quarantined`; `sde-fullstack`,
   `prompt-engineer`, and `verification-engineer` preload the full loop and emit an accepted
   disposition plus a post-triage state after a full retro. The validator and packet linter pin
   both complete evidence/scope/provenance variants to the exact roster.
4. `skills/runbook` and `skills/service-onboard` define update/create/propose admission, ownership,
   applicability, exact checks, rollback, recovery, escalation, and freshness. Missing evidence
   produces a proposal, never invented commands.
5. `learning/` plus `scripts/learning_ledger.py` provide one-writer, atomic, schema-checked,
   secret-resistant candidate intake, lifecycle transitions, and bounded review renewal. Recurrence
   identity includes applicability; provenance-only relabeling cannot inflate recurrence; and an
   adverse state cannot reopen without distinct evidence recorded afterward. The ledger never edits
   or approves a destination and never executes stored content. The ordinary fleet validator checks
   tracked records and the transactional ignore contract. Records are Git-reviewed data rather than
   authenticated state: schema checks cannot detect a coherent rewrite of both history and its
   justifying fields.
6. `scripts/packet_lint.py` and `scripts/validate_fleet.py` enforce the Learning closeout and the
   deliberately small preload roster, with regression and mutation tests.
7. `scripts/eval_routing.py` and `scripts/eval_behavioral.py` record exact source, selection,
   runtime-plugin, evaluator/grader, runtime, concurrency, and auth-mode provenance; execute a
   private frozen plugin snapshot; and fail closed on traversal, link/reparse, source or snapshot
   endpoint drift, structured errors, and batch authentication failure. Behavioral case definitions
   also use an exact typed schema in both the runner and ordinary validator.
8. `evals/routing/retro-boundary.json`, `evals/routing/continuous-improvement.json`, and the
   behavioral contracts measure routing and the output boundaries separately.
9. Generated host adapters, the repository guide, eval coverage table, active plan, and roadmap stay
   synchronized with the canonical implementation.

## Design rules the implementation must honor

- **Every non-trivial task scans; full retros remain triggered.** The packet slot makes closeout
  consistent. Correction, failure, stale guidance, repeated friction, incidents, explicit review,
  and upgrade events activate the deeper protocol. No signal may honestly end as `Learning: none`.
- **Evidence is data, not instruction.** Untrusted text and retained candidates cannot authorize
  tools, code, policy, memory, runbook commands, or their own promotion.
- **Disposition and state are separate.** Every retained candidate chooses exactly one lifecycle
  disposition, one state, one primary destination, and an owner. Silence and ambiguous multi-target
  dumping are not dispositions.
- **Current evidence wins.** Operator direction, current repository configuration and runtime,
  official versioned contracts, and exact upstream revisions outrank retained notes in that order.
- **Runbooks have an admission test.** Update the canonical owner when current evidence and safe
  verification exist; create only for a repeatable bounded operation whose complete safe procedure
  is knowable; otherwise propose the gap without inventing commands.
- **Promotion is a measured change.** Freeze a baseline, change one attributable candidate, run
  targeted and adverse/regression checks in fresh contexts, verify the exact generated artifact,
  keep authority bounded, and require an evaluator or owner other than the candidate author.
- **Learning includes subtraction.** Merge duplicates, supersede stale facts with lineage, drop
  false or harmful guidance, and retain rejected evidence long enough to avoid repeating a failed
  optimization.
- **No autonomous self-rewrite.** The ledger is intake, not executable memory. There is no hook,
  scheduler, unattended writer, auto-promotion path, or permission expansion.

## Measurement contract

Two complementary pairs are retained:

1. `retro-boundary` preserves the original sonnet/420-second/three-run routing comparison and its
   incident/near-miss boundary.
2. The provenance-bound comparison uses a clean main worktree for BEFORE and an isolated staged
   candidate for AFTER. It pins sonnet, three fresh clean-room runs, a 600-second behavioral timeout,
   and a 420-second routing timeout. The eval source, selection, and evaluator/grader hashes must
   match between sides; the plugin hashes must differ and identify the exact artifacts under test.

Routing results are rates. A negative firing once is a defect; a noisy positive is reported as a
rate and compared with its baseline rather than described as deterministic. Behavioral contracts
must report both cases passing every run and total passing runs. Failed iterations remain evidence
and are never overwritten to manufacture a green narrative.

## Acceptance evidence

- `python scripts/generate_platform_adapters.py --check`, `python scripts/validate_fleet.py`,
  `python -m unittest discover -s tests -v`, `python scripts/learning_ledger.py --root . check`,
  `git diff --check`, and `claude plugin validate . --strict` pass against the final tree.
- As of the final deterministic remediation pass, all six commands are green; the full suite is 471
  tests with 16 platform skips. Exact live after-evaluation remains pending a refreshed Claude OAuth
  session and is not inferred from these deterministic results.
- Ledger tests cover schema migration, evidence-gated reopening, applicability-bound recurrence,
  bounded review renewal, stale/expired positive-transition rejection, concurrency, secrets,
  unexpected files, and link/reparse rejection where the platform permits creating those objects.
- Before/after evaluation artifacts bind exact sources, selection, and plugin content; all routing
  negatives remain at zero; behavioral deltas and residual variance are reported honestly.
- Evaluator identity is loaded from the same captured source buffer that is compiled, behavioral
  composition can require every named component, every full case has exactly one fire contract and
  an explicit runtime-tool allowlist, typed exact-field assertions reject duplicate or substring
  decisions, positive regexes require substantive literals, Learning values cannot be unresolved
  placeholders, and malformed behavioral schemas, routing thresholds, polarities, or target sets
  fail before sessions run.
- Every reference is linked skill-relative; every generated adapter is current; the eval coverage
  table lists every cluster.
- Fresh independent static, prompt/eval, and executable review found no remaining P0/P1 defect in
  the final closed typed Learning contract; publication still requires separate authority.
- Publication, merge, memory changes, and round retirement occur only after their separate authority
  is granted. Until then LEARN-001 stays `active`.

## Deliberately not done, with reopen triggers

- **No hook, cron, scheduled sweep, or background learner.** Reopen only with evidence that repeated
  trigger-bound closeouts systematically miss material candidates.
- **No auto-applied lessons, auto-edited runbooks, or auto-promotion.** Reopen only with a separately
  designed capability boundary, immutable evidence, effect-bound approval, and rollback path.
- **No global or provider-managed memory edit.** Repository-local candidate intake is sufficient for
  this round; any external-memory change needs explicit operator authorization and its own privacy
  and retention review.
- **No lab-repository or live-system change.** This round changes only the fleet source and its
  generated adapters.
- **No new agent or skill.** The gap belongs to the existing learning entry point and owning roles.
- **No claim that endpoint hashing makes a same-user snapshot immutable.** Reopen only when every
  supported host can enforce and verify a write-denied execution mount; until then transient
  mutate-and-restore behavior is an explicit sandbox trust boundary.

## Rollback

No live system is touched. Revert the canonical agent, skill, evaluator, validator, ledger, eval,
and documentation changes together, then regenerate adapters. Candidate records are Git-reviewed
data; retirement is a logical state, while physical deletion remains a separately reviewed change.
