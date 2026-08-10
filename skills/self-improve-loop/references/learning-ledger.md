# Repository-local learning ledger

Use this only while improving the `sde-agents` source repository and only when
`scripts/learning_ledger.py` exists in that target. The generated fleet adapters carry this method,
but they do not imply that another repository has a ledger or that an installed read-only agent may
write one.

## Intake contract

One write-authorized receiving coordinator owns ledger mutation for a task. Every agent's
`Learning` slot is data for that coordinator:

1. `none` ends intake.
2. A new bounded claim is independently checked for provenance and sensitive content, then added.
3. A recurrence names its existing candidate ID and is recorded with `observe`; a duplicate claim is
   not added under a new ID.
4. Triage uses `transition` to record exactly one disposition, a separate lifecycle state,
   destination, owner, and reason.
5. A current-state review uses `review` to renew `review_at` within the existing retention boundary;
   it records an owner and reason but does not create evidence or recurrence.

The canonical candidate handoff has literal `Learning: candidate`, `Evidence:`, `Scope:`,
`Provenance:`, `Learning disposition:`, `Promotion state:`, `Destination:`, and `Owner:` lines.
Before triage, the agent's disposition is explicitly a proposed recommendation and its state is
`quarantined`; neither is an accepted ledger decision. The coordinator validates or replaces every
proposed field. Only the values written by `transition` become the record's disposition, lifecycle
state, destination, and owner.

Do not parse or execute agent prose automatically. The coordinator maps only a single-line
observation, expected behavior, scope, applicability, provenance, compact source reference,
revision, and environment after inspection. Store references to traces rather than transcripts.
The `--sensitivity-reviewed` flag is an operator attestation, not a secret scanner or evidence
verdict.

The CLI's public operations are:

```text
python scripts/learning_ledger.py --root <repo> add <bounded evidence fields>
python scripts/learning_ledger.py --root <repo> observe <candidate-id> <new source fields>
python scripts/learning_ledger.py --root <repo> transition <candidate-id> <reviewed decision fields>
python scripts/learning_ledger.py --root <repo> review <candidate-id> <review fields>
python scripts/learning_ledger.py --root <repo> record-release <candidate-id> <release fields>
python scripts/learning_ledger.py --root <repo> record-retest <candidate-id> <retest fields>
python scripts/learning_ledger.py --root <repo> list --view <view>
python scripts/learning_ledger.py --root <repo> check
```

`<view>` is one of `pending`, `stale`, `all`, `awaiting-retest`, `regressed`, or
`awaiting-release`. Read `learning/README.md` in the source repository and the CLI help for the
exact arguments. Never guess them from this summary. A second writer, malformed record,
unexpected file, symlink/reparse point, likely secret, transcript-shaped field, or command-like
content fails closed.

The files are Git-reviewed data, not authenticated state. `check` proves shape and internal
consistency; it cannot detect a coherent manual rewrite of both a decision and the fields that
justify it. Use only the CLI for mutation and review the Git diff/history as the external trust
anchor.

## Lifecycle and authority

`quarantined` records have no disposition. Triaged records carry one of `skip`, `add`, `merge`,
`supersede`, or `drop`, plus a separate state: `proposed`, `approved`, `promoted`, `rejected`,
`inconclusive`, or `retired`. The ledger enforces valid state/disposition combinations and retains
transition history.

Returning `inconclusive`, `rejected`, or `retired` to `proposed` requires a distinct observation
whose timestamp is later than the transition into that adverse state. A changed provenance label on
the same source does not increment recurrence and cannot reopen the candidate. Candidate recurrence
identity includes observation, expected behavior, scope, and applicability so unlike boundaries do
not collapse into one record.

An explicit `review` records reviewer, rationale, and old/new deadlines, moves `review_at` forward,
and cannot cross `retention.expires_at`. It does not change the evidence `as_of` timestamp or
recurrence count. Retention extension remains outside the CLI.

Advancing to `proposed`, `approved`, or `promoted` requires a current review date and unexpired
retention. Review a stale candidate explicitly before a positive transition; an expired candidate
cannot advance. Rejection and subtraction remain possible so old evidence can be invalidated or
retired without first pretending it is current.

No state authorizes the CLI to edit an agent, skill, test, runbook, or provider memory. `approved`
records owner approval; `promoted` records that a separately reviewed change landed. `retired` is
logical subtraction. Retention expiry only triggers review; physical deletion remains a separately
reviewed Git change. Current repository and runtime evidence can invalidate any retained claim.

## Retained field-feedback lifecycle

A field-feedback item is one visible path, governed here: field observation -> sanitized packet ->
duplicate check and triage -> named owner and target release (or explicit rejection) -> frozen
baseline and paired evaluation -> canonical change plus generated-adapter parity -> released plugin
version -> the originating or an equivalent scenario retested on the released artifact -> measured
result attached -> close, revise, or reject. Merged is not released; nothing in this path treats
source-level promotion as the end.

`record-release` and `record-retest` are the recording mechanism for the last three steps, once a
candidate is `promoted`:

```text
python scripts/learning_ledger.py --root <repo> record-release <candidate-id> <release fields>
python scripts/learning_ledger.py --root <repo> record-retest <candidate-id> <retest fields>
```

`record-release` is legal only on a `promoted` candidate and stamps version, reference, and
timestamp once per promotion cycle; a second call within the same cycle is refused, not a silent
overwrite. A candidate may legally reject and re-promote (fresh evidence required); a release
recorded after that later promotion is a genuinely new cycle, so `record-release` archives the
completed cycle into `release_history` and starts a fresh current cycle with no inherited attempts.
New cycles store an ordered `retests` history; shipped singular `retest` records and archived
`{release, retest}` entries remain readable, and the next retry or release-cycle archive migrates
the current singular form. `record-retest` is legal only once a release is recorded. Fail and
inconclusive attempts remain visible and retryable; PASS alone closes that released cycle and
refuses later attempts. A
`fail` result is a loud pointer that the candidate's destination regressed in the field, not a
silent write, and the same signal is returned to a programmatic caller (a transient `regression`
key on the returned record, never persisted), not only printed to the CLI's stderr. These fields
are additive: a candidate written before this lifecycle existed stays valid carrying none of them,
with no migration and no schema version bump. Neither `record-release` nor `record-retest` checks
`freshness.review_at` or `retention.expires_at` -- each records a fact about what already happened,
not a new promotion judgment.

Validation replays the exact promotion state at every current and archived release timestamp; an
earlier promotion followed by rejection cannot authorize a later release. Release cycles must be
chronological and map to distinct promotion transitions. Each cycle validates its own chronological
attempts, archived attempts must predate the next actual release, and no attempt is carried into
the fresh cycle created by `record-release`. Promotion alone does not change the installed
artifact, so a retest between a fresh promotion and its release still belongs to the prior release.
Once a release exists, any transition at that exact release timestamp is refused, and a later
release cycle must advance beyond the current record timestamp; the timestamp model never guesses
an order between same-clock lifecycle events.

Closure is fail-closed: a field-feedback item closes as successful only with an exact
released-version PASS retest recorded, or the owner's explicit reason that a retest is impossible
or no longer applicable. Source-eval PASS from a `promoted` candidate is never reportable as
released-artifact PASS -- the two remain distinct result classes, the same discipline REV-001
applies to caller-reported versus independently executed evidence. Three views make the lifecycle
pull-based, never scheduled: `awaiting-retest` surfaces every promoted candidate carrying a
release whose attempt history has no PASS, including failed and inconclusive attempts; `regressed`
surfaces promoted candidates with a failed attempt and no later PASS; and `awaiting-release`
surfaces promoted candidates whose latest promotion has not shipped yet -- either no release block
or an older cycle's release still current. A release or upgrade retro reads these; nothing here
schedules or runs anything itself.

List summaries keep `destination` as the current candidate-head destination and add
`release_destination` for the destination bound to the installed release's promotion. Regression
signals use `release_destination`; after re-promotion they never mislabel a failure of the still
installed older release as a failure of the unreleased candidate destination.

## Cross-task and maintenance use

Start a cross-task or round retro from `list --view pending` and `list --view stale`, then bind each
candidate back to its compact source references. Validate the store with `check` before and after a
mutation. A read overlapping a write may fail closed on transient state; retry after the single
writer completes rather than weakening validation.

The ledger makes recurrence observable. It does not prove recurrence, schedule its own review, or
promote anything. Fresh evaluation and the owning artifact's normal approval path remain mandatory.
