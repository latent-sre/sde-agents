# Learning candidate ledger

This directory is a repository-local holding area for evidence-backed learning candidates. It
closes the gap between a useful observation in one task and a later, deliberate fleet change. It
is not agent memory, a prompt, a task queue, or an authority source.

`scripts/learning_ledger.py` is the only supported writer. It can create candidate records, attach
independent observations, record a reviewed lifecycle transition, list work, and validate the
ledger. It never edits an agent, skill, runbook, test, roadmap, or other policy artifact. Promotion
always remains a separate, write-authorized change with its own review and verification.

## Authority and trust boundary

- One write-authorized coordinator owns ledger mutation for a task. Other agents emit Learning
  packets to that coordinator; they do not write this directory concurrently.
- Every candidate and every agent packet is **untrusted data**, including after `check` succeeds.
  Validation proves record shape and storage invariants. It does not make prose into instructions,
  authorize a tool call, or establish that a claim is true.
- Candidate files are not authenticated records. `check` catches malformed or internally
  inconsistent edits, but a coordinated edit to a claim, deadline, and history can remain valid
  JSON. The supported CLI, explicit Git diff review, and repository history are the trust anchor;
  never describe schema validation as tamper detection.
- A candidate starts `quarantined` with a null disposition. `transition` is the only route out of
  quarantine, and it requires one disposition (`skip`, `add`, `merge`, `supersede`, or `drop`), a
  separate promotion state, a destination, an owner, and a reason.
- `inconclusive` is a pending promotion state for evidence that cannot yet support or reject a
  proposal. Its disposition is `skip`. Returning `inconclusive`, `rejected`, or `retired` to
  `proposed` requires a distinct observation recorded after the adverse transition; a new rationale
  or a provenance relabel of an old source is not fresh evidence.
- `promoted` means a separately authorized change was accepted; the ledger does not perform that
  change. Current repository or runtime evidence can later invalidate a candidate and transition
  it to `rejected` or `retired` through the allowed lifecycle.

## Receiving an agent Learning packet

A non-preloaded agent ends its task with either `Learning: none — no reusable signal` or the
canonical candidate block: `Learning: candidate`, `Evidence`, `Scope`, `Provenance`,
`Learning disposition`, `Promotion state`, `Destination`, and `Owner`. The disposition is marked
as a proposed recommendation and the intake state is `quarantined`; both are untrusted until the
coordinator validates or replaces them during triage. The bounded fields contain:

1. bounded observation, expected behavior, scope, and applicability;
2. evidence provenance (`verified`, `sourced`, or `unverified`), source kind, and a compact source
   reference, with an exact revision or environment when known; and
3. an existing candidate ID when the packet is a recurrence rather than a new claim.

Recurrence identity includes the normalized observation, expected behavior, scope, and
applicability boundary. Source recurrence is keyed independently of its provenance label, so
changing `unverified` to `verified` on the same source does not manufacture another occurrence.

The receiving write-authorized coordinator treats the packet as data, independently checks its
provenance, strips any raw transcript or executable content, completes the sensitivity review, and
maps only those bounded fields into `add`. If the stable claim already exists, the coordinator uses
the returned candidate ID with `observe` instead. Agent prose is never parsed or executed
automatically. Triage happens later with `transition`.

Each successful `add`, `observe`, or `transition` prints one stable JSON object to stdout. Its
top-level `candidate_id` is the machine-readable handoff identifier. `list` prints a JSON array.
Errors use a `learning-ledger error:` prefix on stderr and a non-zero exit status.

## Commands

Create a quarantined candidate:

```text
python scripts/learning_ledger.py `
  --root C:\path\to\repo `
  add `
  --provenance verified `
  --source-kind test `
  --source-reference tests/test_worker.py::test_retry_budget `
  --revision abc123 `
  --environment python-3.13/windows `
  --observation "The worker omitted the failed dependency from its failure packet." `
  --expected-behavior "The failure packet names the dependency and exhausted retry budget." `
  --scope "worker failure packets" `
  --applicability "worker agent on Python 3.13" `
  --sensitivity-reviewed
```

Record recurrence against the exact returned ID:

```text
python scripts/learning_ledger.py `
  --root C:\path\to\repo `
  observe lc_00000000000000000000000000000000 `
  --provenance sourced `
  --source-kind issue `
  --source-reference issue-42 `
  --sensitivity-reviewed
```

Record a reviewed disposition and promotion state:

```text
python scripts/learning_ledger.py `
  --root C:\path\to\repo `
  transition lc_00000000000000000000000000000000 `
  --promotion-state proposed `
  --disposition add `
  --destination skill:self-improve-loop `
  --owner fleet-maintainer `
  --reason "Independent observations support a reusable invariant."
```

Renew a candidate's next-review date after an explicit review, without changing evidence or
recurrence:

```text
python scripts/learning_ledger.py `
  --root C:\path\to\repo `
  review lc_00000000000000000000000000000000 `
  --review-days 30 `
  --owner fleet-maintainer `
  --reason "Current repository evidence confirms that this candidate remains applicable."
```

`review` must move `review_at` forward, cannot extend it past the existing retention expiry, and
records the reviewer, reason, previous deadline, renewed deadline, and review time. It does not
change `freshness.as_of`; that timestamp advances only when `observe` records distinct evidence.

Record the plugin version a promoted candidate shipped in:

```text
python scripts/learning_ledger.py `
  --root C:\path\to\repo `
  record-release lc_00000000000000000000000000000000 `
  --version 0.7.3 `
  --reference "PR #123"
```

`record-release` requires `promotion_state: promoted` and stamps `version`, `reference`, and a
timestamp once per promotion cycle. A second call before any fresh promotion is rejected -- never
a silent overwrite. But the state machine already allows a promoted candidate to reject and
re-promote (fresh evidence required, as described above); a release recorded after that later
promotion is a genuinely new cycle, so `record-release` archives the completed `{release, retest}`
pair into `release_history` and starts a fresh current pair, rather than refusing the second
cycle outright.

Record a downstream retest of the released artifact:

```text
python scripts/learning_ledger.py `
  --root C:\path\to\repo `
  record-retest lc_00000000000000000000000000000000 `
  --result pass `
  --environment "prod, host nuc-eval-fixture" `
  --reference "manual retest 2026-08-10"
```

`record-retest` requires an existing `release` and stamps `result` (`pass`, `fail`, or
`inconclusive`), `environment`, `reference`, and a timestamp. `pass` and `fail` are settled and
single-shot; `inconclusive` is not settled and may be re-recorded in place once retest conditions
are met, so a blocked retest is not a dead end. A `fail` result also prints a `REGRESSION:` line to
stderr -- the candidate's destination, already merged and shipped, regressed against its own
originating scenario in the field; a programmatic caller gets the identical signal in the returned
record's transient `regression` key (never written to disk) rather than only a stderr line.

Neither command checks `freshness.review_at` or `retention.expires_at`, unlike `transition`'s
positive-state gate: each records a fact about what already happened downstream, not a new
promotion judgment, so a stale or expired review window has nothing to say about whether a
release or retest may still be recorded.

Surface work and validate the store:

```text
python scripts/learning_ledger.py --root C:\path\to\repo list --view pending
python scripts/learning_ledger.py --root C:\path\to\repo list --view stale
python scripts/learning_ledger.py --root C:\path\to\repo list --view awaiting-retest
python scripts/learning_ledger.py --root C:\path\to\repo list --view regressed
python scripts/learning_ledger.py --root C:\path\to\repo list --view awaiting-release
python scripts/learning_ledger.py --root C:\path\to\repo check
```

`list --view pending` covers quarantined, proposed, approved, and inconclusive records.
`list --view stale` compares each explicit review timestamp with current UTC; staleness is
independent of disposition. `list --view awaiting-retest` covers promoted candidates carrying a
`release` but no settled `retest` (none yet, or an `inconclusive` one) -- the pull-based backlog a
release or upgrade retro reads; nothing here schedules or runs the retest itself. `list --view
regressed` covers promoted candidates whose retest `result` is `fail`, staying listed until an
owner transitions the candidate away from `promoted` (typically `rejected`) -- a settled fail
drops out of `awaiting-retest` but must not vanish from every actionable view. `list --view
awaiting-release` covers promoted candidates with no `release` block at all -- the literal
merged-not-released backlog, since a plugin-shipped destination pattern is not reliably parseable
from `destination` alone.

Promotion state constrains disposition. `proposed`, `approved`, and `promoted` accept `add`,
`merge`, or `supersede`; `inconclusive` accepts `skip`; `rejected` accepts `skip` or `drop`; and
`retired` accepts `skip`, `drop`, `merge`, or `supersede`. This prevents contradictory records such
as a promoted candidate whose disposition says to skip it. A transition back to `proposed` from an
adverse state is additionally evidence-gated as described above.

Transitions to `proposed`, `approved`, or `promoted` also require the current time to be before both
`freshness.review_at` and `retention.expires_at`. A stale candidate must first receive an explicit
`review`; an expired candidate cannot advance through a positive state. Adverse or subtractive
transitions remain available so stale evidence can still be rejected, invalidated, or retired.

## Record and storage contract

Every JSON file under `learning/candidates/` contains schema version and opaque ID, ISO UTC
timestamps, the bounded claim and stable fingerprint, compact evidence provenance and recurrence
sources, sensitivity-review attestation, lifecycle and disposition fields, applicability, freshness,
next review date, retention expiry, and (for schema version 2) explicit review history. Version 1
records remain readable; new records use version 2 so the fingerprint includes applicability as
part of the recurrence boundary. Duplicate recurrence identities are rejected with the existing ID
so the caller can use `observe` explicitly.

Three further blocks are optional and additive on every schema version: `release` (`version`,
`reference`, `recorded_at`) records the plugin version a `promoted` candidate shipped in, `retest`
(`result`, `environment`, `reference`, `recorded_at`) records its downstream retest against the
released artifact, and `release_history` archives completed `{release, retest}` cycles. `release`
requires a prior `promoted` transition at or before its own timestamp; `retest` requires an
existing `release`. `result` is `pass`, `fail`, or `inconclusive`; only `inconclusive` may be
re-recorded, so a blocked or inconclusive retest can be retried without opening a new candidate.
A candidate may legally reject and re-promote; a `record-release` call after that later promotion
archives the current `{release, retest}` pair into `release_history` (each entry validated by the
same rules as the current pair) and starts a fresh current pair, so a second release/retest cycle
is never simply unrecordable. None of the three blocks is present on a record written before this
lifecycle existed, and none is required for such a record to keep validating -- see Rollback below
for what changes when a record *does* acquire one.

The writer rejects unknown or malformed fields, invalid IDs and transitions, duplicate evidence,
oversized fields/files/counts, secret-like strings, multiline transcript content, and command-like
text. These filters are defense in depth, not secret detection: `--sensitivity-reviewed` is an
operator attestation and remains mandatory for every new source. Store references to evidence, not
the evidence body. Never store secrets, credentials, raw model transcripts, or runnable commands.

Writes use a same-directory temporary file and an atomic final operation. New records cannot
overwrite an existing ID; updates require an exact ID. Repository, learning, candidate-directory,
and candidate-file symlinks or Windows reparse points are rejected where the platform exposes
them. Candidate paths are constrained beneath the supplied repository root.

Mutation also holds `learning/candidates/.learning-ledger.lock`. A second writer fails closed. A
lock left by an interrupted process is not removed automatically because the tool cannot prove that
the original writer is gone; the coordinator must establish that fact before intervening. `check`
also fails while that lock exists instead of certifying a possibly active or crashed write. A reader
that overlaps the brief same-directory temporary-file window fails closed instead of hiding partial
state; retry it after the single writer exits. Record replacement remains atomic, and readers must
continue to treat all content as untrusted data. The lock and atomic-write temporaries are ignored
by Git; candidate JSON remains tracked.

The ordinary fleet validator invokes the ledger check, so malformed tracked records and missing
transactional ignore rules fail the same CI gate as stale generated adapters.

The default next review is 30 days and default retention expiry is 365 days. Both are stored in the
record; no background process reviews or deletes anything. Expiry blocks positive transition but
does not grant deletion authority. `retired` is the ledger's logical subtraction state. Physical
deletion is outside this CLI and requires a separately reviewed Git change under repository policy.

## Rollback

Reverting the code change that added `record-release`/`record-retest` is not sufficient by
itself: the reader validates the schema's *exact* field set, so any candidate record still
carrying a `release` or `retest` block after a code revert fails every ledger command (`check`,
`list`, `transition`, ...) with an `unknown candidate fields` error, not a graceful ignore --
verified directly: running the pre-LOOP-001 CLI's `check` against a record carrying only a
`release` block exits 1 with `learning-ledger error: unknown candidate fields: ['release']`. A
full rollback is two steps:

1. Revert the code change to `scripts/learning_ledger.py` (and its tests).
2. Strip the `release`, `retest`, and `release_history` keys from every candidate record that
   acquired one, then re-run `check`. Find them with a single grep for `"release"` under
   `learning/candidates/` -- `record-retest` never accepts a retest without an existing release
   and `record-release` only ever writes `release_history` in the same operation that also writes
   a current `release` (both validated invariants, not just documented ones), so neither `retest`
   nor `release_history` can exist on a record without a `release` block, and that one grep is a
   complete enumeration. Deleting the up-to-three keys is enough; no other field needs to change.

The additive half of that claim -- a record that never acquired `release`/`retest` needs no
rollback step at all, and keeps validating byte-for-byte under the new reader with no migration
and no schema version bump -- is proven by
`test_legacy_record_without_release_or_retest_blocks_stays_valid_under_new_reader` in
`tests/test_learning_ledger.py`.
