# External-donor graft round outcomes — 2026-07-30

**Status: historical evidence.** Outcome record for the external-donor graft round (spec and plan
retired with this commit, per `docs/README.md` rule 4). The adjudication itself —
lineage findings, rejects with reasons, contribute-back candidates — lives in
[`external-donor-import-notes.md`](external-donor-import-notes.md); Git history holds the retired
spec and plan with their exact payloads. `docs/fleet-roadmap.md` owns all remaining work.

## What landed

Twelve operator-approved grafts from 20 supplied external sources plus the 2026 claude.com blog
corpus: one new reference file and ten body-only edits across eight existing definitions, with the
round's single description edit.

| Item | Target |
|---|---|
| A1 | `skills/code-craft/references/typescript.md` (new) + routing row and description widening in `skills/code-craft/SKILL.md` |
| A2 | Claude 5-era authoring deltas + the recorded examples-conflict → `skills/prompt-craft/SKILL.md` |
| A3 | Endpoint failure matrix → `skills/backend-craft/SKILL.md` |
| A4 | Verification-skill capture rule + deployment shapes → `skills/self-improve-loop/SKILL.md` |
| A5 | Domain typing + PEP 735 dependency-groups → `skills/code-craft/references/python.md` |
| A6 | Five docs-verified platform facts → `skills/prompt-craft/references/claude-code-frontmatter.md` |
| B7–B11 | Split heuristics + session boundary (`context.md`), fork kill-criterion (`sde-fullstack`), spec-diff CI gate (`api-design.md`), stock-component tells (`frontend-craft`), dependency cooldown (`ci-actions`) |

No agent or skill was added, renamed, or removed; no script, hook, or guard changed. Fleet stays at
**10 agents / 19 skills**.

## What was measured

`evals/routing/craft-vs-fullstack.json`, before and after the `code-craft` description edit under
identical pinned conditions (`--runs 3 --model opus --timeout 420 --clean-room`). Artifacts:
`evals/baselines/2026-07-30-donor-grafts/{before,after}/`.

- **All 8 negatives fired 0% in both runs**, including the seeded `neg-typescript-build-slow`
  decoy — the widening pulled in no near-misses.
- **No positive regressed**; every rate identical except `pos-ci-actions-harden` (33% → 67%,
  variance).
- **The cluster's positive side is suppressed under clean-room + opus**: `pos-code-craft-idioms`,
  3/3 in the 2026-07-27 diagnose, is 0/3 in both runs here, and the new
  `pos-typescript-branded-ids` is 0/3 in both. The widening's positive effect is therefore
  **unmeasured in these conditions, not disproven**. Recorded as EVAL-003 evidence — condition
  sensitivity is the finding, and re-running one side under different conditions would have
  destroyed the comparison.

## Lessons

- **Lineage first.** Three of the 20 supplied sources were vendored copies of other donors;
  adjudicating at the upstream (and citing its own frontmatter license, where the repo carried no
  LICENSE file) is what kept provenance true.
- **Concepts, not expression, for CC BY-SA.** The Trail of Bits material contributed two rules
  restated from the PEP and in fleet wording; no CC BY-SA text entered the tree.
- **Record the page, not the domain.** The blog corpus was captured at domain granularity only, so
  its date-sensitive claims cannot be re-read at a citation. `THIRD_PARTY_NOTICES.md` states that
  limit plainly; future rounds pin a URL per claim.
- **Conflicts can be recorded rather than resolved.** Two live first-party sources disagree on
  worked examples; `prompt-craft` carries the stamp and the reopen trigger instead of a guess.
