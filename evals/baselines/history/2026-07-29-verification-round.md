# 2026-07-29 verification and role-expansion round — distilled record

Seven directories held one day's work — the ROLE-001/002/003/004 and LABSEC-001 landings, PRs
#37–#45. They retired to Git history on 2026-08-17 under the retention rule in `../../README.md`;
this file is their record. Former paths, for anyone reading an older citation:
`2026-07-29/`, `-isolation/`, `-labsec/`, `-roles-before/`, `-roles-after/`,
`-verification-seam/`, `-verifier-contracts/`.

**Conditions:** opus throughout (`models_observed: claude-opus-5`), routing at `--timeout 420`,
behavioral at 600s, 3 runs per case except where noted. `clean_room` was set **only** on the
isolation capture — every other directory predates that condition being recorded, so they must not
be diffed against clean-room artifacts. All predate the provenance schema, so none was ever
reusable as a paired 'before' side.

## The contamination refutation — the result the roadmap still cites

The auditor's two `investigation` positives, `pos-appsec-audit` and `pos-appsec-threatmodel`, were
measured twice under otherwise-identical conditions:

| capture | clean room | result |
|---|---|---|
| `-roles-after/investigation-appsec` | no (inherited config) | **0/6** — both cases 0.0 across 3 runs |
| `-isolation/appsec-cleanroom` | **yes** | **0/6** — both cases 0.0 across 3 runs |

Identical zero under isolation. That refuted configuration contamination as the cause of agent
under-fire and established it as a property of headless one-shot mode on this tier. `EVAL-003` in
`docs/fleet-roadmap.md` rests on this pair.

## The roles pair: nothing regressed, and nothing moved

`-roles-before` vs `-roles-after`, `homelab-ops` and `investigation`:

- **All 10 `homelab-ops` negatives 1.0 clean on both sides** (`neg-app-feature`,
  `neg-review-deploy`, `neg-debug-test`, `neg-api-docs`, `neg-lab-architecture`,
  `neg-status-dashboard`, `neg-prompt-fix`, `neg-sprint-retro`, `neg-resolved-not-incident`,
  `neg-personal-machine`). ROLE-001's rebrand widened no description onto a near-miss.
- **`pos-host-linux` and `pos-host-onboard` were 0.0 before and 0.0 after** — the rebrand did not
  move the host positives, because they are agent-expecting and could not fire either way.
- `investigation` negatives 1.0 clean: three before, four after (`neg-security-fix` joined with the
  new auditor).

So the pair's honest reading is: no over-trigger introduced, and the positives it was meant to
demonstrate were unmeasurable in this harness. `-roles-after` additionally carried a note recording
that its three pre-existing negatives were **re-scored** against the then-current four-member
cluster after `application-security-auditor` joined — no new sessions were run, `fired_per_run`
made the regrade deterministic, `application-security-auditor` fired in 0 runs of every case, and
every rate and the 4/4 summary were unchanged.

## LABSEC-001: the one clean positive result of the day

`-labsec`, all 3 runs, all 1.0: `pos-attacker-reach`, `pos-default-creds`,
`pos-audit-whats-wrong`, `pos-audit-security`, and `neg-harden-app-code` clean. The
`security-audit` skill landed reachable and did not pull application-hardening work.

## verification-seam: the seam's shape at seeding

All five positives 0.0 (`pos-verify-fix`, `pos-verify-acceptance`, `pos-review-not-run`,
`pos-diagnose-why`, `pos-build-and-test`); all three negatives 1.0 clean, and two decoys routed to
the correct **non**-members. Same agent-positive story, with the negatives doing the real work.

## The cross-cutting finding, only visible with all seven together

`-verifier-contracts` (behavioral, 2 runs, opus) passed **2/2 on both**
`verifier-blocked-is-inconclusive` and `verifier-fails-honestly-no-product-edit`, and `2026-07-29/`
passed `ladder-report-not-absorb` 1/1 on **opus and again on fable**, plus `packet-slots-builder`
1/1.

So on the same day, with the same agents and the same model: **routing could not see them firing
while behavioral confirmed their contracts held once pinned.** That is the entire argument for
retiring agent-only routing positives in favour of pinned behavioral contracts — measured three
weeks before that decision was taken on 2026-08-17. Keep this next to the LADDER and LEARN-002
records; it is the earliest instance of the pattern.

Caveat carried forward: the `2026-07-29/` behavioral numbers are single runs (and one 2-run
capture), which bound nothing. They are recorded as the reason the behavioral suite continued, not
as rates.
