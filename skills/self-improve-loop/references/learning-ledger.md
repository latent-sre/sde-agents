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

Reopening an adverse state, recurrence identity, and the review/retention clock are CLI-enforced;
read its errors rather than memorizing the rules. The operational core: a positive transition
(`proposed`, `approved`, `promoted`) requires fresh-enough evidence — review a stale candidate
first, and an expired one cannot advance — while rejection and subtraction stay possible so old
evidence can be invalidated without pretending it is current. `review` renews the clock and nothing
else: no new evidence, no recurrence, and no retention extension, which stays outside the CLI.

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

Ordering, repeat, and re-promotion-cycle rules are CLI-enforced and refused loudly, never silently
overwritten; read the CLI help and errors for the exact semantics rather than this summary. The
one behavior worth knowing in advance: `pass` and `fail` retests are settled, `inconclusive` stays
retriable, and a `fail` is a loud pointer that the candidate's destination regressed in the field.

Closure is fail-closed: a field-feedback item closes as successful only with an exact
released-version retest recorded, or the owner's explicit reason that a retest is impossible or
no longer applicable. Source-eval PASS from a `promoted` candidate is never reportable as
released-artifact PASS -- caller-reported and independently executed evidence stay distinct result
classes. Three views make the lifecycle pull-based, never scheduled: `awaiting-retest` (a release
but no settled retest), `regressed` (retest failed; listed until an owner moves the candidate off
`promoted`, so a settled fail cannot vanish from every actionable view), and `awaiting-release`
(promoted with no release block -- the merged-but-unreleased backlog). A release or upgrade retro
reads these; nothing here schedules or runs anything itself.

## Cross-task and maintenance use

Start a cross-task or round retro from `list --view pending` and `list --view stale`, then bind each
candidate back to its compact source references. Validate the store with `check` before and after a
mutation. A read overlapping a write may fail closed on transient state; retry after the single
writer completes rather than weakening validation.

The ledger makes recurrence observable. It does not prove recurrence, schedule its own review, or
promote anything. Fresh evaluation and the owning artifact's normal approval path remain mandatory.
