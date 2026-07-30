# Round plan — verification role, eval isolation, import method (2026-07-29)

**Status: active.** Executes
[`specs/2026-07-29-verification-eval-port-design.md`](../specs/2026-07-29-verification-eval-port-design.md).
Three PRs, in order; each runs the full offline gate (`validate_fleet.py`, unit suite,
`claude plugin validate . --strict`) before push. Retire both documents to an outcome record when
PR C merges.

## PR A — `claude/role-003-004` (this branch)

1. Land the spec and this plan (the round's existence must be visible on main, per
   `docs/README.md`).
2. Decision record `decisions/2026-07-28-fleet-role-expansion.md`: record the ROLE-003 acceptance
   with the six-fork contract; update the status header.
3. Roadmap: ROLE-003 and ROLE-004 leave the file when this PR's acceptance evidence is committed
   (item contract: an item leaves when its evidence lands).
4. Author `agents/verification-engineer.md` per the spec's contract. Description leads with
   capability, then triggers, then negative routing; ≤ 1024 chars.
5. Seed `evals/routing/verification-seam.json`: negatives from the four adjacent remits
   (implementation, static review, diagnosis, live ops) plus agent positives carrying the known
   zero-fire caveat. Negatives are the graded signal.
6. Behavioral contracts: (a) a blocked/unrun check yields `inconclusive`, with a
   `must_not_match` on passing language; (b) the packet names the exact tested revision.
7. `--write-inventory`; run the new cluster (baseline capture — conditions recorded); run the
   behavioral contracts. Open PR with the conditional-gates table filled.

## PR B — `claude/eval-003-isolation`

1. Salvage `scripts/eval_clean_room.py` + `tests/test_eval_clean_room.py` from
   `modernization-cleanup` via `git checkout <branch> -- <paths>`; adapt only what current code
   requires; verify the two `CLAUDE_CODE_*` env-var claims against current docs.
2. Fix the false isolation claim at `evals/README.md:108` to state what is actually true.
3. Two-session registration probe (one contaminated, one clean-room); artifacts under
   `evals/baselines/2026-07-29-isolation/`.
4. If registration differs: re-run one prior agent-positive set (e.g. the auditor's 0/6) under
   the clean room, same conditions otherwise, and compare.
5. Update EVAL-003 on the roadmap with measured findings; decide there whether the anchor needs
   case redesign first. Review `THIRD_PARTY_NOTICES.md` on the branch; take it only if owed.
6. After merge: delete `modernization-cleanup`.

## PR C — `claude/port-001-import`

1. Write the porting method down (documented convention first; skill form only if it passes the
   roadmap's always-visible-cost test).
2. Execute the import: three independent read passes over `superpowers:systematic-debugging`
   before donor-doc comparison; adaptation notes as the implementation spec; scrub donor-only
   assumptions; record provenance; graft into `skills/root-cause`.
3. If `root-cause`'s description changes, run its overlapping routing cluster before and after.
4. PORT-001 leaves the roadmap when the import lands with the method's artifacts committed.

## Standing constraints

- Worker subagents spawned during this round run at or below sonnet (operator 2026-07-29); eval
  runner model pins are doctrine, not worker choices.
- Eval batches are controller-owned foreground or watched background runs with artifact-only
  watchdogs; liveness checks use the full command line with retry.
- No guard allowlist changes anywhere in this round.
