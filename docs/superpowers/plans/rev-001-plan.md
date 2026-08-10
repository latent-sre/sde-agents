# REV-001 plan — advisory/approval split and the review-to-verify envelope

**Paired with:** [`REV-001 spec`](../specs/rev-001-immutable-review-envelope.md), approved
2026-08-09 under one condition — the shared material-risk matrix grows **by generalization**,
never by per-incident append. Implements issue #62. Branch-scoped: the roadmap owns status, this
file owns the exact payloads.

**Admitted ledger candidates** (operator direction 2026-08-09): `lc_90dd8dc7` — destination
`agents/verification-engineer.md`, a multi-task branch's shared execution-configuration change
invalidates earlier per-task evidence, so verdicts are not composed across it — and
`lc_2c04ead3` — destination `agents/code-reviewer.md`, a failure scenario labeled traced or
inferred. Each transitions in the same change that lands its destination text, so the ledger can
never report a promotion no bytes carry.

## Payloads

### 1 — `agents/code-reviewer.md`: the modes section (spec scope 1 and 3)

A new `## Advisory and approval modes` section placed before the evidence gate, because it decides
which verdict vocabulary the rest of the file is allowed to reach:

- **Advisory mode** for mutable bytes — a working tree, a staged snapshot, a supplied patch. It
  keeps the existing `PROVISIONAL — COMMIT AND RE-REVIEW` verdict form and requires the exact
  mutable surface to be named. This is what keeps the fleet's own working-diff lanes legal; the
  spec's hard constraint forbids a blanket mutable-tree refusal, and the section is worded by
  *target identity* rather than by lane name so it stays host-neutral (Codex has no workflow
  runtime, and the generated non-Claude adapters may not name a Claude workflow at all).
- **Approval mode** for an immutable commit or sealed snapshot — the only mode that may emit
  APPROVE, APPROVE WITH NITS, or REQUEST CHANGES, closing with an **approval envelope**
  (`repository`, `base_revision`, `candidate_revision`, `tree_digest`, `scope`,
  `acceptance_criteria`, `material_risks`, `review_mode`). Snake_case, GRAPH-004-compatible, so a
  later typed contract is a rename-free promotion and GRAPH-004 stays deferred.
- **Approval binds to `candidate_revision` and transfers to nothing** — including bytes produced
  by applying the reviewer's own nits. The observed failure this closes is a verdict re-read as
  covering whatever HEAD later points at.
- **The material-risk matrix**, seeded with exactly the two field-proven controls (irreversible
  remote credential mutation requires post-failure state reconciliation before rollback;
  secret-bearing nonstandard headers require a logging/redaction contract before shared access
  logging), plus the retained independent pass and "ask for observable evidence, never a named
  harness unless the architecture requires it" — the SEC-01 lesson where a prescribed fixture
  would have made the ordinary repository gate depend on a new execution privilege.

This file **owns** the envelope field names and the matrix row shape; `README.md`'s
owned-conventions paragraph records it, so a future drift is fixed in the paraphrase and never in
the source.

The confidence bullet also gains the `lc_2c04ead3` payload: label the failure scenario **traced**
(you followed the path) or **inferred** (you reasoned it) — an inferred path stated in traced
register is how a plausible finding buys unearned weight.

### 2 — `agents/verification-engineer.md`: the envelope as target of record (spec scope 2 and 4)

- **Method 1** takes the envelope as the target of record — a prose "it was approved" is not an
  envelope — and fails closed *before executing* on four conditions: the requested revision differs
  from `candidate_revision`; `review_mode` is advisory; the worktree has uncommitted changes inside
  `scope`; the snapshot cannot be reproduced from `base_revision` plus the digests. It works
  `material_risks` rows as criteria and hands newly discovered risks back rather than absorbing
  them, which is the divergence SEC-01 produced when a PASS coexisted with two valid reviewer P1s.
- **Method 2** voids a run whose product bytes change mid-flight (re-pin and rerun, or
  inconclusive — results from two revisions never compose), and carries `lc_90dd8dc7`: on a
  multi-task branch, a task that changed shared execution configuration (caching, fact gathering,
  parallelism, connection behavior) means earlier per-task evidence was gathered under the old
  semantics, so that task is named and what it invalidates is re-derived rather than composed.
- **Method 6** separates the five result classes (product, test/fixture, execution environment,
  evidence custody, live behavior never exercised), holds the offline verdict to its scope
  (deployment, runtime recovery, and monitoring delivery stay explicitly unverified), keeps
  caller-reported evidence at `**[sourced]**`, and states that verdicts expire for every other
  revision.
- The packet gains an **Evidence custody** slot: the caller names the durable destination, a
  custody failure is reported beside the product result rather than folded into it, bundles are
  never auto-committed into the product repository, and secrets are redacted.

`packet_lint`'s `verification-packet` shape is a floor, so the added slot needs no shape change —
the existing `verifier-packet-shape-holds` case keeps grading the floor unchanged.

### 3 — `evals/behavioral/contracts.json`: five scenario cases (spec acceptance line 1)

Issue #62's Eval 1 already ships as `reviewer-uncommitted-bytes-are-not-approvable`. The remaining
scenarios become cases, agent-pinned with every execution tool denied so a regression cannot become
a real run:

| Case | Issue eval |
|---|---|
| `reviewer-approval-does-not-transfer-to-a-new-sha` | 2 — approval invalidated by a fix |
| `verifier-envelope-target-mismatch-fails-closed` | 3 — verifier target mismatch |
| `verifier-verdict-does-not-follow-later-commits` | 5 — post-verification mutation |
| `verifier-evidence-custody-failure-is-separate` | 6 — evidence-persistence failure |
| `verifier-offline-pass-is-not-live-acceptance` | 7 — live-vs-offline scope |

Eval 4 (verification executes against the approved revision) needs a real execution session and is
not a text-graded contract; it is proven by the manual T3 run, not asserted here — a case that
graded it offline would assert nothing.

Oracles follow the `gate-phase-calibration` shape: positives carry the load (a response asserting
the opposite cannot state the correct answer affirmatively) and each negative is scoped so an
honest denial cannot false-fire on it — the negation-blindness that cost GATE-001 a review round.

### 4 — Ledger transitions

`scripts/learning_ledger.py transition` moves both candidates to `promoted` with a reason naming
this round. `scripts/ledger_drift.py` must stay clean afterward: a promoted candidate whose
destination text does not exist is exactly the drift that report exists to catch.

## Verification

- `python3 scripts/generate_platform_adapters.py --write` after every canonical edit, then
  `python3 scripts/validate_fleet.py` (T0) — byte-parity across the six generated copies of the two
  agents is the gate that keeps one fix from producing three fleets.
- `python3 -m unittest discover -s tests -p test_eval_behavioral.py` for the case additions,
  including the hard-coded case count that would otherwise let a silently dropped case pass.
- `python3 scripts/run_tests.py` (T1) before the PR.
- **No routing evals are owed:** no `description:` field changes in this round. Body prose does not
  drive routing, so a paired routing run would re-prove what nothing changed.
- The behavioral suite itself is T3 (real API, manual). This branch ships the cases; the run that
  grades them is the operator's, and the round does not claim their result.

## Deliberately not done

- No CI-enforced envelope, no schema file, no new script — the spec's smallest mechanism is prose
  in two canonical agents, and a mechanism without a demonstrated consumer waits trigger-bound.
- GRAPH-004 stays deferred; this round only borrows its field-name idiom.
- No outcome record: the round is not finished until its acceptance list is evidenced against
  released bytes, and a closeout PR retires this plan and its spec then.

## Rollback

Prompt-level edits to two canonical agents, their regenerated adapters, five eval cases, one test
count, one README paragraph, and this round's docs — one revert commit, no state to unwind.
