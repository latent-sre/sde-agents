# Fleet roadmap

> **Status: consolidation skeleton — not yet the live status owner.**
> `docs/sre-agents-adaptation-backlog.md` remains authoritative until the historical-open-item
> reconciliation and current-work import are complete.

This file will contain only unfinished, blocked, or explicitly deferred work for the current
fleet. Landed implementation history and donor-by-donor adjudication belong in `docs/archive/`;
architecture decisions and rejected alternatives belong in `docs/decisions/`.

## Item contract

Every roadmap item carries:

| Field | Meaning |
|---|---|
| ID | Stable identifier used by plans and decision records |
| Status | `ready`, `active`, `blocked`, `deferred`, or `decision-needed` |
| Outcome | The observable result, not a list of files |
| Source | The decision, review, or specification that established the work |
| Prerequisites | Gates that must land first |
| Acceptance | Evidence required to close the item |
| Next action | The smallest safe step that moves it forward |

An item leaves this file when its acceptance evidence is committed. The source decision remains;
Git history and archived reviews retain the implementation detail.

## Current work

No items are imported yet. Step 2 reconciles every historical “open” claim against the current
tree; Step 3 imports only the survivors.

## Deferred decisions

No decisions are imported yet.

## Reconciliation record

Pending. This section will record the reviewed revision, source documents, and exclusions that
prevent stale historical findings from re-entering the roadmap.

