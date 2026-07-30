# Verification round outcomes — 2026-07-29

**Status: historical evidence.** Outcome record for the verification round (spec and plan retired
with this commit, per `docs/README.md` rule 4). The round was adjudicated by the operator in one
question round — test-authoring verifier, local-containers-free effects gate, isolation-first for
EVAL-003, `systematic-debugging → root-cause` as the PORT-001 donor — and landed as three PRs the
same day. Git history holds the retired spec/plan and every eval artifact; `docs/fleet-roadmap.md`
owns all remaining work.

## What landed

| PR | Items | Outcome |
|---|---|---|
| #43 | ROLE-003, ROLE-004 | The authority contract accepted and recorded in the role-expansion decision record; `verification-engineer` (10th agent) with the `verification-seam` cluster and two behavioral contracts. Review hardened the contract regexes (negated-pass claims, contraction-blind patterns) before merge |
| #44 | EVAL-003 phase 1 | Clean room salvaged from `modernization-cleanup` with its phantom env var corrected and test-pinned; `--clean-room` on both runners, recorded in `conditions`; `probe_isolation.py`; the false isolation claim fixed; `THIRD_PARTY_NOTICES.md` landed (attribution the tree owed) |
| #45 | PORT-001 | The porting method codified in README as a documented convention (the roadmap's cost test applied); exercised end to end on `superpowers:systematic-debugging` → six inline lines in `root-cause`; provenance pinned by review to the v6.2.0 tag and commit SHA |

ROLE-003, ROLE-004, and PORT-001 left the roadmap with these PRs. Fleet: **10 agents / 19
skills**.

## What was measured

All conditions recorded in the artifacts under `evals/baselines/` (opus @ 420s routing, opus @
600s behavioral, CLI 2.1.220).

- **Both verifier contracts held every run on first landing** — blocked execution yielded
  `inconclusive` under release pressure with all tools denied, and the planted-bug case returned
  FAIL citing the given revision without the verifier editing the product code.
- **The verification seam does not leak inward**: all three negatives 0% across runs, with two
  decoys routing to the correct *non-members* (`lab-audit`, `ci-actions`). All five positives 0%,
  and `pos-diagnose-why` became the first *skill* positive observed at 0% (non-sharp vocabulary
  by design) — recorded in the cluster notes, not tuned.
- **The registration surface was measured for the first time**: every prior eval session had
  inherited 134 operator-side entries, with the fleet registered twice — 9 bare via the junction
  deployment plus 9 namespaced via `--plugin-dir` (fleet *skills* registered bare-only). Under
  the clean room: namespaced-only, one plugin.
- **The contamination hypothesis was refuted, cheaply.** Six sessions: the auditor's agent
  positives fired 0/6 under the clean room — identical to the same day's contaminated 0/6 at
  identical conditions. The headless one-shot under-fire is a property of the mode and tier, not
  of the operator's configuration. EVAL-003's remaining work is a grading decision plus one
  anchor capture under `--clean-room`; isolation owes nothing further.

## Deliberately not done

- **The full routing anchor** — it waits on the agent-member grading decision the refutation just
  made decidable, and capturing it in the same PR as the harness change would have graded the
  harness with itself.
- **No `packet_lint` shape for the verification packet** — two regex contracts carry the pinned
  promises; a lint shape earns its keep at a second consumer.
- **`CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` not adopted** — it would remove the CLI's built-ins from
  the surface and break comparability with every existing baseline; if wanted, it belongs beside
  `clean_room` in `conditions`.
- **Contribute-back to `obra/superpowers` recorded, not acted on** — the candidates (test-cost
  economics, the unsafe-to-reproduce fallback, the npm-only bisection script) live in the import
  notes; opening an upstream PR is a separate operator decision.

## Lessons carried forward

1. **A salvaged setting is a claim, not a fact.** The clean room's original env var existed in no
   documentation — it would have shipped as isolation that reads as armor and configures nothing.
   Verify platform names against current docs before trusting them, and pin the correction with a
   test.
2. **Kill hypotheses with controlled comparisons before spending captures.** Six sessions settled
   what a full-suite anchor would have spent an order of magnitude more on — and would have
   recorded ambiguously.
3. **Isolation is a measurement condition, not a property of "fresh".** A fresh session inherits
   the operator's whole configuration; any artifact that doesn't state its isolation cannot be
   compared with one that does. `conditions.clean_room` exists so that difference is never
   silent.
4. **Attribution debt surfaces on salvage.** The notices file was owed before anything was
   salvaged; imports under the porting method now have a standing place to record their upstream.
