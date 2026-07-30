# External-donor graft round — design (2026-07-30)

> **Status: active round.** Governs what the paired plan
> (`docs/superpowers/plans/2026-07-30-external-donor-grafts.md`) may implement. Retires to an
> outcome record when the round closes, per `docs/README.md` rule 4.

## What this round is

The trigger-bound reopening of PORT-001: the operator supplied 20 external donor sources plus the
2026 claude.com blog corpus across two review rounds on 2026-07-30. Donor-blind reading passes and
fleet-side gap scans produced an adjudicated menu (durable copy: memory
`external-skills-mining-2026-07-30`), and the operator approved the full menu — Tier A (6 grafts)
plus Tier B (6 one-liners). This spec freezes that scope.

## Scope — the twelve accepted items

| # | Graft | Target |
|---|---|---|
| A1 | New TypeScript/React reference distilled from three donors | `skills/code-craft/references/typescript.md` + routing row and description widening in `skills/code-craft/SKILL.md` |
| A2 | Claude 5-era authoring deltas + recorded examples-conflict | `skills/prompt-craft/SKILL.md` |
| A3 | Endpoint failure-matrix testing bullet | `skills/backend-craft/SKILL.md` |
| A4 | Verification-loop capture rule + deployment shapes + claim-level line (absorbs B12) | `skills/self-improve-loop/SKILL.md` |
| A5 | Domain-typing idioms + PEP 735 dependency-groups clause | `skills/code-craft/references/python.md` |
| A6 | Platform-facts refresh, docs-verified only | `skills/prompt-craft/references/claude-code-frontmatter.md` |
| B7 | Progressive-disclosure split heuristics + new-task-new-session | `skills/prompt-craft/references/context.md` |
| B8 | Kill-criterion clause on ask-the-forks | `agents/sde-fullstack.md` |
| B9 | Spec-diff CI gate line | `skills/backend-craft/references/api-design.md` |
| B10 | Concrete AI-aesthetic component tells | `skills/frontend-craft/SKILL.md` |
| B11 | Dependency-cooldown clause | `skills/ci-actions/SKILL.md` |

## Constraints (from the porting method and the adjudication)

1. **Adapt, don't copy.** Every graft is freshly written in the fleet's register. Mandatory for the
   two Trail of Bits-derived clauses (CC BY-SA 4.0 — concepts only, never prose).
2. **Evergreen rule.** No version pins or APIs that age (drop `react@canary`-gated material,
   `Activity`, `useEffectEvent`); version-conditional phrasing ("on React 19+ …") is allowed where
   the condition is the content.
3. **A1 reads upstream verbatim at import time** (`vercel-labs/agent-skills`, not the zebbern
   vendored snapshot) for every rule it keeps — the assessment reads went through a summarizing
   fetch. License cited from the rule-skills' own `license: MIT` frontmatter (the repo has no
   LICENSE file).
4. **A6 adds only facts verified against live docs/CLI this round**, stamped per that file's own
   convention; unverified blog claims are excluded and noted in the PR.
5. **One description edit only** (code-craft). No other `description:` changes — everything else is
   body-only.
6. **Surgical diffs**: each item touches only its stated target; no adjacent reformatting.

## Acceptance

- `python scripts/validate_fleet.py`, `python -m unittest discover -s tests`, and
  `claude plugin validate . --strict` all pass on the branch.
- Routing gate: `evals/routing/craft-vs-fullstack.json` run before AND after the code-craft edit
  under identical pinned conditions (`--runs 3 --model opus --timeout 420 --clean-room`), artifacts
  committed under `evals/baselines/2026-07-30-donor-grafts/{before,after}`. Pass criteria: no
  existing positive regresses; no negative fires at any rate (including the newly seeded
  `neg-typescript-build-slow`); `pos-typescript-branded-ids` before→after diff is reported
  (improvement expected, not required — skill positives are the reliable signal).
- Every reference file A1 creates is linked skill-relative from its SKILL.md (orphan check).
- Provenance recorded twice per donor-derived commit: `adapted from <repo>` + license in the commit
  message, and entries in `THIRD_PARTY_NOTICES.md`.
- Adaptation notes land in `docs/archive/2026-07/external-donor-import-notes.md` (the PORT-001
  notes shape); this spec and its plan retire to an outcome record when the round closes.
