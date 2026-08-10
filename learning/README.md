# Learning candidate ledger

This directory is a repository-local holding area for evidence-backed learning candidates. It
closes the gap between a useful observation in one task and a later, deliberate fleet change. It
is not agent memory, a prompt, a task queue, or an authority source.

`scripts/learning_ledger.py` is the only supported writer. It can create candidate records, attach
independent observations, record a reviewed lifecycle transition, attach a released-artifact retest
result, list work, and validate the ledger. It never edits an agent, skill, runbook, test,
roadmap, or other policy artifact. Promotion always remains a separate, write-authorized change
with its own review and verification.

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
- `released` means a named released version was retested against the originating or an equivalent
  scenario. It is unreachable until `retest` records a passed or explicitly waived result for the
  merge being released, because every gate before it judged source: a candidate can pass them all
  and still fail in the installed artifact, another host adapter, or the workflow that reported it.

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

Each successful `add`, `observe`, `transition`, `review`, or `retest` prints one stable JSON object
to stdout. Its
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

Attach a released-artifact retest to a merged candidate, then close the loop:

```text
python scripts/learning_ledger.py `
  --root C:\path\to\repo `
  retest lc_00000000000000000000000000000000 `
  --released-version 1.7.3 `
  --environment "installed plugin 1.7.3, claude code cli" `
  --result pass `
  --evidence "The originating scenario ran on the released artifact and passed." `
  --rollback-trigger "Reopen the candidate if the released scenario regresses." `
  --owner fleet-maintainer `
  --reason "Released-artifact retest of the originating scenario." `
  --sensitivity-reviewed
```

`retest` is evidence, not a decision: it records what shipped, where it ran, and what happened, and
it never changes the promotion state. The candidate must already be `promoted` or `released`, the
version must name one exact release (a moving label such as `latest` records no retestable
artifact), and `--result` is `pass`, `fail`, or `waived`. `waived` is the owner-approved escape
hatch for a retest that is impossible or no longer applicable, and its reason is stored with it.

Surface work and validate the store:

```text
python scripts/learning_ledger.py --root C:\path\to\repo list --view pending
python scripts/learning_ledger.py --root C:\path\to\repo list --view stale
python scripts/learning_ledger.py --root C:\path\to\repo list --view awaiting-retest
python scripts/learning_ledger.py --root C:\path\to\repo check
```

`list --view pending` covers quarantined, proposed, approved, and inconclusive records.
`list --view stale` compares each explicit review timestamp with current UTC; staleness is
independent of disposition. `list --view awaiting-retest` lists merged candidates that have not
reached `released`, each with a `release_retested` flag saying whether the measurement or only the
transition is still owed. It is a pull query for a release or upgrade retro; nothing schedules it.

Promotion state constrains disposition. `proposed`, `approved`, `promoted`, and `released` accept
`add`, `merge`, or `supersede`; `inconclusive` accepts `skip`; `rejected` accepts `skip` or `drop`;
and `retired` accepts `skip`, `drop`, `merge`, or `supersede`. This prevents contradictory records
such as a promoted candidate whose disposition says to skip it. A transition back to `proposed`
from an adverse state is additionally evidence-gated as described above.

Transitioning `promoted` to `released` additionally requires a passed or explicitly waived retest
recorded after the promotion it releases and before the release itself, so a source-level PASS can
never be reported as a released-artifact PASS and an older release's PASS cannot certify a later
re-merge. The rule is enforced both by the command and by record validation, so a hand-written
`released` record fails `check`.

Transitions to `proposed`, `approved`, `promoted`, or `released` also require the current time to
be before both `freshness.review_at` and `retention.expires_at`. A stale candidate must first
receive an explicit `review`; an expired candidate cannot advance through a positive state. Adverse
or subtractive transitions remain available so stale evidence can still be rejected, invalidated,
or retired.

## Record and storage contract

Every JSON file under `learning/candidates/` contains schema version and opaque ID, ISO UTC
timestamps, the bounded claim and stable fingerprint, compact evidence provenance and recurrence
sources, sensitivity-review attestation, lifecycle and disposition fields, applicability, freshness,
next review date, retention expiry, explicit review history (schema version 2 and later), and
released-artifact retest history (schema version 3). Versions 1 and 2 remain readable exactly as
written; new records use version 3, and an older record is upgraded only by the write that needs a
newer field. The version-2 fingerprint includes applicability as part of the recurrence boundary.
Duplicate recurrence identities are rejected with the existing ID so the caller can use `observe`
explicitly.

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
