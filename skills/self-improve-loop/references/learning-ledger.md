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
python scripts/learning_ledger.py --root <repo> retest <candidate-id> <released-artifact result>
python scripts/learning_ledger.py --root <repo> list --view <pending|stale|awaiting-retest|all>
python scripts/learning_ledger.py --root <repo> check
```

Read `learning/README.md` in the source repository and the CLI help for the exact arguments. Never
guess them from this summary. A second writer, malformed record, unexpected file, symlink/reparse
point, likely secret, transcript-shaped field, or command-like content fails closed.

The files are Git-reviewed data, not authenticated state. `check` proves shape and internal
consistency; it cannot detect a coherent manual rewrite of both a decision and the fields that
justify it. Use only the CLI for mutation and review the Git diff/history as the external trust
anchor.

## Lifecycle and authority

`quarantined` records have no disposition. Triaged records carry one of `skip`, `add`, `merge`,
`supersede`, or `drop`, plus a separate state: `proposed`, `approved`, `promoted`, `released`,
`rejected`, `inconclusive`, or `retired`. The ledger enforces valid state/disposition combinations
and retains transition history.

Returning `inconclusive`, `rejected`, or `retired` to `proposed` requires a distinct observation
whose timestamp is later than the transition into that adverse state. A changed provenance label on
the same source does not increment recurrence and cannot reopen the candidate. Candidate recurrence
identity includes observation, expected behavior, scope, and applicability so unlike boundaries do
not collapse into one record.

An explicit `review` records reviewer, rationale, and old/new deadlines, moves `review_at` forward,
and cannot cross `retention.expires_at`. It does not change the evidence `as_of` timestamp or
recurrence count. Retention extension remains outside the CLI.

Advancing to `proposed`, `approved`, `promoted`, or `released` requires a current review date and
unexpired retention. Review a stale candidate explicitly before a positive transition; an expired candidate
cannot advance. Rejection and subtraction remain possible so old evidence can be invalidated or
retired without first pretending it is current.

No state authorizes the CLI to edit an agent, skill, test, runbook, or provider memory. `approved`
records owner approval; `promoted` records that a separately reviewed change landed. `released`
records that a named released version was retested against the originating or an equivalent
scenario, and it is reachable only after `retest` attaches a passed or explicitly waived result for
the merge being released -- a source-level PASS is not a released-artifact PASS. `retired` is
logical subtraction. Retention expiry only triggers review; physical deletion remains a separately
reviewed Git change. Current repository and runtime evidence can invalidate any retained claim.

## Cross-task and maintenance use

Start a cross-task or round retro from `list --view pending` and `list --view stale`, then bind each
candidate back to its compact source references. A release or upgrade retro also runs
`list --view awaiting-retest`, which names the merged candidates whose released artifact nobody has
certified yet; nothing schedules that query, so a release that never asks leaves the loop open. Validate the store with `check` before and after a
mutation. A read overlapping a write may fail closed on transient state; retry after the single
writer completes rather than weakening validation.

The ledger makes recurrence observable. It does not prove recurrence, schedule its own review, or
promote anything. Fresh evaluation and the owning artifact's normal approval path remain mandatory.
