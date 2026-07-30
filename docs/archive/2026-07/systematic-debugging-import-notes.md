# Import notes — superpowers:systematic-debugging → root-cause (2026-07-29)

**Status: historical evidence** (dated import adjudication, per `docs/README.md`). These are the
adaptation notes PORT-001 requires — the implementation specification the graft was built from.
Donor: `superpowers` v6.2.0 (MIT, Copyright (c) 2025 Jesse Vincent,
<https://github.com/obra/superpowers>), read verbatim from the plugin cache on disk. Method:
`README.md` → "Importing from another fleet (the porting method)", codified in the same round.

## The three frozen passes

Three sonnet readers, donor-only (no access to the fleet's artifact), conclusions frozen before
comparison:

- **Import lens** ranked ten disciplines; strongest: the phase gate (no fixes before
  investigation), three-strikes-to-architecture, backward tracing to the original trigger,
  defense-in-depth as bug-elimination, boundary instrumentation for multi-component systems,
  bisection. Flagged the quick-reference table, persona sections, and single-anecdote
  "Real-World Impact" blocks as non-transferable filler.
- **Conflict lens** found 24 MUST-SCRUB couplings: two `superpowers:`-namespaced sibling-skill
  references, real class names from the donor's own product (Lace's WorktreeManager/Session) in
  every technique reference's worked example, `npm test` hardcoded as the only runner in
  `find-polluter.sh`, dated single-session metrics presented as evidence, and stale
  `skills/debugging/` paths in the authoring fixtures.
- **Structure lens**: 9.5KB always-loaded core with reference-weight material inline; the three
  technique references share one incident as their entire evidence base; the test fixtures and
  CREATION-LOG are unmaintained authoring residue; the flagship `.ts` example hand-rolls three
  copies of the abstraction its own prose says to write once.

## What grafted (six lines, inline, freshly written)

| Donor discipline | Landed in `skills/root-cause/SKILL.md` |
|---|---|
| Bisection over many candidate changes/units | Step 2: `git bisect` across commits, or run candidates one at a time until the symptom appears |
| Boundary instrumentation in multi-component failures | Step 2: log what enters and leaves each boundary once; find *where* before *why* |
| Backward tracing to the original trigger | Step 5: fix at the origin of the bad state, not where the error surfaced |
| Defense-in-depth after the fix | Step 5: consider whether each layer the bad value passed unchallenged should also reject it |

No file was copied. The grafts are new sentences in the fleet's register, so the scrub obligation
is satisfied by construction; the MUST-SCRUB list above is what verbatim copying would have
dragged in.

## Rejected, with reasons

- **The phase-gate framing, rationalization table, and pressure-test fixtures** — the fleet's
  core rule, red-flags list, and eval suite already hold this ground more compactly; the donor's
  redundancy-by-design conflicts with the fleet's lean-core doctrine.
- **`find-polluter.sh` and the technique reference files** — the script only runs `npm test`
  (silently inapplicable elsewhere); the references' evidence base is one incident, and
  `root-cause` deliberately has no `references/` layer to keep the loop always-loaded and short.
- **Single-variable fix discipline** — owned repo-wide by the surgical-diffs working rule;
  restating it in one skill would create a second owner.
- **`condition-based-waiting`** — flaky-test timing, not root-cause method; off this skill's
  remit, and the donor's own example contradicts its prose.

## Contribute-back candidates (recorded, not acted on)

- The fleet's hypothesis table with likelihood × cheapest-test economics and a Result column —
  the donor ranks by likelihood only.
- The fleet's unsafe-to-reproduce fallback (stable signature / correlated traces / controlled
  simulation, with the dependency stated) — the donor's Phase 1 has no such path.
- `find-polluter.sh`'s hardcoded `npm test` line is a portability defect upstream might want a
  `--runner` parameter for.
- Independent convergence worth noting upstream: both artifacts arrived at three-failures →
  question-the-architecture.

## Gates

Body-only change: `root-cause`'s `description:` is untouched, so no routing run is owed. The
grafted file stays within the fleet's validator, test, and strict-plugin gates, run on this
branch before push.
