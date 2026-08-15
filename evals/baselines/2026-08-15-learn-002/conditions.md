# LEARN-002 paired round — 2026-08-15 conditions

Every artifact under `before/` and `after/` is one case's `benchmark.json`, and each records its own
`conditions` and `provenance` blocks. This file states what is common to them and, more importantly,
the two places where they are **not** uniform — reading either side without those is how a paired
run gets misread.

## Common conditions

| | |
|---|---|
| Runner | `scripts/eval_behavioral.py --runs 3 --model sonnet --clean-room --retain-run-evidence` |
| CLI | 2.1.233 (Claude Code) |
| Model observed | claude-sonnet-5 |
| Python | CPython 3.11.15 |
| Timeout | 600s |
| Auth mode | `host-managed-provider` (see below) |
| `clean_room` | `true` on both sides |
| Before revision | `4bddd9d` (worktree, nothing else writing to it) |
| After revision | `c8312b3` (worktree, nothing else writing to it) — **not the shipped bytes; see below** |

The two sides differ in exactly one thing that is not a condition: the canonical
`skills/self-improve-loop/SKILL.md` text repairs in `6f2d14d` and `c8312b3`. `4bddd9d` is the
before base precisely so the clean-room enabler is present on both sides and is not part of the
delta.

## The after side is not the shipped skill

Two `skills/self-improve-loop/SKILL.md` amendments landed **after** `c8312b3` in response to the
PR #140 review: the no-signal literal became the fixed string `Learning: none — no reusable signal`
(it had been a `<reason>` slot that `packet_lint` rejects), and the `Destination:` instruction was
corrected. No session in this directory ran against those bytes.

What that does and does not invalidate is checkable rather than arguable, and it is pinned to
immutable identities so a later session can reproduce the claim from this file alone — `HEAD` moves,
and a comparison written against it would rot into either a false alarm or a false reassurance:

| | SKILL.md blob |
|---|---|
| Measured (`c8312b3`) | `ade8f47edecb37b87942948c6f4edf91212f294c` |
| Shipped (this round's final skill edit) | `b8b72622b8e676f86376f23943dc203b9c66309f` |

The blobs differ, as they must. The sentences governing the two measured assertions — the
`Learning: candidate — <observed -> expected>` form and the triad-first `Provenance:` paragraph —
are **byte-identical** across them, sha256 `224fe87f0392abcd…` on both sides, so `0/9 → 9/9` and
`1/9 → 9/9` are evidence for the shipped bytes. Reproduce with:

```
git show ade8f47:…/SKILL.md   # or b8b7262 for the shipped side
```

extracting the fenced value-forms block and the paragraph beginning `The angle-bracketed names`. The two amendments themselves are
unmeasured, tracked as LEARN-002 remainder item 7, and must not be described as having behavioral
evidence in this round.

## Not uniform: concurrency is paired per case, not across the round

Six cases ran at `--concurrency 3` and seven at `--concurrency 1`. The split is not a preference.
Sessions intermittently returned `Claude exited 1 before a successful result` on every run of a
case — a measurement failure, not a contract failure: re-running an affected case alone produced a
normal graded session every time. It struck five cases on the first before batch and four on the
first after batch, and it never struck a case running at concurrency 1.

Affected cases were re-measured, and where the flake persisted at concurrency 3 the **pair was
re-measured on both sides at concurrency 1** rather than one side being carried over. Every case in
this round therefore pairs against itself under identical conditions; the per-case `concurrency`
value in each `conditions` block is the check, and it matches across sides for all thirteen.

Concurrency 1 cases: `runbook-disposition-propose`, `learning-slot-operational-agent`,
`loop-capture-is-not-closure`, `loop-duplicate-merges-provenance`,
`loop-source-pass-is-not-released-pass`, `reviewer-formal-approval-emits-envelope`,
`self-improve-canonical-triaged-candidate`. All others ran at 3.

No rate in this round is reported from a run that exited 1. Where such runs are all that exist for
a case at a given concurrency, they were discarded and re-bought, not graded — a stub session
scored as a contract failure would be exactly the false result the runner's gradeable rule exists
to prevent.

Do not diff a concurrency-3 artifact against a concurrency-1 one. The runner records the value in
each `conditions` block for exactly this reason.

## Not uniform: this round is not comparable to 2026-08-10

The 2026-08-10 calibration round ran at CLI 2.1.226 on CPython 3.12.10 with
`auth: credentials-file-copy`. This round is CLI 2.1.233, CPython 3.11.15, and
`auth: host-managed-provider`. Its rates are therefore **not** the before side for anything here,
which is why a fresh before was captured rather than reused. Two cases show the drift plainly:
`learning-runbook-namespaces-compose` (1/3 there, 3/3 here before any edit) and
`runbook-disposition-propose` (2/3 there, 3/3 here). Neither improvement is attributable to this
round's changes, and neither is claimed.

## The auth mode is new, and why

`host-managed-provider` first appears in this round. The clean room previously refused to run
without a credential file or an auth environment variable; on a managed host the CLI's credentials
are resolved by the host and injected out of band, so every signal the precheck looked for is
absent while sessions authenticate normally — inside the room included. `4bddd9d` teaches the room
to recognize that case and record it under its own label rather than borrowing another's, so no
artifact claims a credential source it did not use. Artifacts differing on `auth` are a condition
difference like any other.
