# SAFE-003 spec — document and enforce `contract_digest`'s real shape

**Status: approved** — the operator's 2026-08-09 ruling chose document-and-enforce over the
resolver path; this spec was authored retroactively on 2026-08-10 to satisfy the execution
contract after review (codex deep review on PR #110) found the round active with no spec, a
gap the contract reads as no round running.

## Problem

The GRAPH-003 adjudication verified against the shipped code: `contract_digest` is stored,
validated, and echoed by `scripts/run_state.py` while nothing resolves it — a reserved slot
that resolves to nothing, which reads as enforcement and enforces nothing. The absorbed
control-plane proposal framed the repair as resolving the reference; the operator's 2026-08-09
ruling reframed it: document the field's actual binding and enforce it at run creation, with
resolution left trigger-bound on GRAPH-004.

## Scope

1. **Documentation at the enforcement site.** The slot is documented for what it is — a
   forward-compatibility binding nothing resolves until GRAPH-004 — so the field's text stops
   promising a lookup no code performs.
2. **Fail-closed shape enforcement at run creation.** Required, lowercase 64-hex SHA-256, in
   the module's own error type — exactly the shape the shipped `NOT NULL` schema and the
   `required` CLI flag already declare. Creation is the only place shape can be kept: the
   `started` event is append-only, so a malformed digest admitted there is permanent.
3. **Tests proving every rejection branch leaves no run behind**, and that accepted digests
   are stored and echoed verbatim.

## Explicitly out of scope

- **Any schema change.** Admitting null (the absorbed proposal's example) would contradict the
  shipped `NOT NULL` column and the version-1 hard-reject — enforcing the schema's reality is
  the repair, not amending it.
- **A resolver.** Nothing gains the ability to resolve a digest to a contract document; that
  remains GRAPH-004, trigger-bound.
- **Hardening sibling creation arguments.** Their pre-existing CLI-era assumptions were noted
  in the scoping comment and deliberately left alone.

## Acceptance

Creation-time enforcement of the documented binding with tests for every rejection branch
asserting no run survives one; existing run-state tests and the deterministic gates green.
Met on `round/safe-003` (PR #110).
