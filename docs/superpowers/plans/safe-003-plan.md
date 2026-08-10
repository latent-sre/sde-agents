# SAFE-003 plan — document and enforce `contract_digest`'s real shape

Operational on `round/safe-003` (PR #110) while the round is active; retires to the outcome
record when the round closes. Spec: [safe-003-contract-digest-shape.md](../specs/safe-003-contract-digest-shape.md).

1. **Replace `_validate_digest` with `_validate_contract_digest(object) -> str`** in
   `scripts/run_state.py`: reject non-strings with `StateError` (the regex's `TypeError` is an
   exception this module never raises and `main` does not catch), reject anything failing
   `SHA256_RE.fullmatch`, return the value verbatim. The doc comment carries the ruling: a
   reserved forward-compatibility slot, shape is the only promise it can keep, creation is the
   only place to keep it, and the hardening is scoped to this field.
2. **Enforce at `StateStore.start_run`** — the single creation path — assigning the returned
   value so a future normalization cannot be silently dropped.
3. **Document the binding in the CLI help** for `--contract-digest` ("recorded and echoed,
   resolved by nothing"), keeping the flag `required` per the shipped `NOT NULL` schema.
4. **Tests in `tests/test_run_state.py`**: fire every rejection branch (missing, non-string,
   malformed) and assert no run or event survives a rejection; assert an accepted digest is
   stored and echoed verbatim. Mutation-proof the guard: deleting it must fail these tests.
5. **Roadmap reconciliation**: SAFE-003's status/outcome/acceptance record the 2026-08-09
   ruling, and GRAPH-004's reopen triggers drop the superseded resolver path (the ruling chose
   document-and-enforce, so nothing there needs a contract document to resolve to).

Ride-along (builder handoff, ledger candidate `lc_b2d00e7d`, promoted): exclude the platform's
nested-worktree home from the repo-copy and probe copytrees — scoped to the repository-relative
`.claude/worktrees` path per the codex deep review, with a tripwire test proving an unrelated
`worktrees/` directory survives every borrow — and ignore `.claude/worktrees/` in git.
