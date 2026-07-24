# Routing baseline — July 2026

First measured routing baseline for the three clusters seeded this cycle (`homelab-ops`,
`craft-vs-fullstack`, `ladder`), the check the fleet's own doctrine demanded and never had: every
description was rewritten this cycle, none had been measured. Run with `scripts/eval_routing.py`
`--runs 3`, headless `claude -p … --plugin-dir .` per case, deterministic transcript grading. The
machine anchors are the per-cluster `benchmark.json` files beside this note; re-run and diff against
them after a description edit or after the planned `lab-incident` (backlog 1.5), `restore-drill`,
or `upgrade-campaign` skills land.

**Two corrections to this note, added 2026-07-24** (it was written before both):

- A **fourth** cluster, `proportionality`, was baselined right after this note and its
  `benchmark.json` sits beside the other three. It is negative-only and came back **6/6 clean**, so
  the cycle's true negative tally is **23/23**, not the 17/17 below, and the raw pass count is not
  24/40 either. The headline conclusion is unchanged and slightly stronger.
- The `homelab-ops` numbers here are **superseded**: `postmortem` joined that cluster on
  2026-07-24 (4 members / 15 cases here → 5 / 18), so this capture is a historical anchor, not a
  like-for-like diff target. The current capture is `../2026-07-24/`.

## Headline

- **Negatives: 17/17 across all three clusters.** Every near-miss that merely shares vocabulary
  routed *away* from its cluster — several confirmably to the right place (`also_fired`:
  frontend-craft on the status dashboard, homelab-platform on "add Prometheus", prompt-craft on
  prompt tasks). This is the load-bearing, variance-robust result: **no description is over-broad.**
  It is the goal a routing eval most needs to hit, and it holds even after the grader fix below made
  the one previously-invisible skill (lab-audit) visible on negatives.
- **Skill positives fire reliably; agent positives are a weak signal in headless one-shot.** Skills
  invoked inline route dependably (lab-audit 3/3, runbook 3/3, eng-ladder-altitude 3/3); agents,
  which only register when the session *delegates*, fire flakily under `claude -p` (homelab-platform
  0–1/3, sde-fullstack ~0/3, distinguished-architect 0–3/3). This is a property of the measurement
  harness, not the descriptions — see the caveat in `../../README.md` — and the same agents route
  correctly on the negatives' `also_fired`. Do not read the low agent-positive rates as routing
  defects.

Do **not** reduce this to the raw 24/40 pass count: that number is dragged down by the
agent-delegation harness characteristic, not by routing quality. The signals that matter — negatives
clean, skill positives reliable — are both good.

## What running this properly surfaced

Two findings came out of *verifying* the numbers rather than trusting them:

1. **A false-negative bug in the grader itself** (fixed, commit prior to this baseline). In headless
   mode the Skill tool signals invocation through the `tool_result`: a skill with no tool
   restrictions reports `Launching skill: <name>` with `is_error` unset, but a skill that sets
   `allowed-tools`/`disallowed-tools` is launched with `is_error: true` and content `Execute skill:
   <name>`. The grader treated every `is_error` result as a failed call, so it dropped **lab-audit**
   (the fleet's only tool-restricting skill) entirely — lab-audit scored 0 despite routing correctly
   on every run, and an over-trigger of lab-audit on a *negative* would have been an invisible false
   PASS. Proof the fix is right: the two lab-audit positives went 0/5 → **3/3**. This is exactly the
   "green/red for the wrong reason" the fleet warns about, found in its own tooling.
2. **The skill-vs-agent measurement asymmetry** (documented in `../../README.md`): the same reason
   agent positives read low. It is why the negatives and skill positives carry the signal here, and
   why the native `claude plugin eval` — which delegates properly — is the eventual home for these
   cases (they migrate unchanged).

## Per-cluster results (`--runs 3`, grader-fixed)

### homelab-ops — 11/15 (positives 4/8, negatives 7/7)

| Case | Rate | Note |
|---|---|---|
| pos-audit-whats-wrong | 3/3 | lab-audit — **was a false 0 before the grader fix** |
| pos-audit-security | 3/3 | lab-audit — likewise corrected |
| pos-runbook-write | 3/3 | runbook |
| pos-runbook-update | 3/3 | runbook |
| pos-pin-and-restart | 1/3 | homelab-platform agent — flaky delegation |
| pos-troubleshoot-proxy | 0/3 | homelab-platform agent (fired 2/5 in an earlier run — variance) |
| pos-add-service | 0/3 | homelab-platform agent — session tends to act inline |
| pos-onboard-standardize | 0/3 | homelab-platform agent |
| all 7 negatives | 7/7 | no cluster member fired |

Skills 4/4 at 100%; the four misses are all the homelab-platform **agent**.

### craft-vs-fullstack — 7/13 (positives 1/7, negatives 6/6)

Craft skills fire partially (backend-webhook 2/3, frontend-form 1/3); the cross-layer sde-fullstack
**agent** positives are ~0/3 (delegation). Negatives 6/6 clean — build vocabulary did not drag any
review / design / lab / prompt / debug near-miss onto a builder.

### ladder — 6/12 (positives 2/8, negatives 4/4)

pos-distinguished-adr 3/3 and pos-engladder-altitude 3/3 fire reliably; builder/principal positives
are flaky (agent delegation). Negatives 4/4 clean — a lab / code-review / prompt / debug near-miss
fired no ladder member (`also_fired` confirms homelab-platform and prompt-craft took the lab and
prompt cases).

## How to re-use

```bash
# re-baseline a cluster and diff against the committed benchmark.json
python3 scripts/eval_routing.py evals/routing/homelab-ops.json --runs 3 \
  --output-dir /tmp/after && diff <(jq .cases evals/baselines/2026-07/homelab-ops/benchmark.json) \
  <(jq .cases /tmp/after/benchmark.json)

# the load-bearing checks, cheap: any negative that fires at all is a real over-trigger
python3 scripts/eval_routing.py evals/routing/homelab-ops.json --case 'neg-*' --runs 3
```

The actionable regressions to watch on a re-run: a **negative that starts firing** (over-trigger —
a real defect at any rate) and a **skill positive whose rate collapses** (under-trigger after an
edit). Agent-positive rates are noisy here by construction; weight them lightly until measured under
`claude plugin eval`.
