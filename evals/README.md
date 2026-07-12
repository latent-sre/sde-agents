# Routing evals

`agents/prompt-engineer.md` mandates eval-first prompt changes — baseline, repetitions, fresh
contexts, measured against a previous version. The fleet shipped none, so it preached a practice it
didn't follow. This directory is that practice: it measures whether a realistic request **routes to
the right agent or skill**, and whether near-miss requests that only share vocabulary route
elsewhere.

## Why routing, and why here

The agents and skills have deliberately overlapping remits — `prompt-engineer` (agent) and
`prompt-craft` (skill) both cover "creating or fixing anything an LLM consumes"; `sde-fullstack`
overlaps `backend-craft`/`frontend-craft`; `homelab-platform` overlaps `service-onboard`,
`lab-audit`, and `runbook`. Overlap is fine — until a description drifts and a request starts landing
on the wrong member. Nothing measured that, so nothing would catch the regression. These evals do.

## Format

Cases follow the [Agent Skills eval shape](https://agentskills.io/skill-creation/evaluating-skills)
(a realistic `prompt` plus an expectation), adapted so the graded assertion is a **routing fact read
off the transcript** — which component actually fired — rather than output quality. That makes
grading deterministic and free (no judge model). One file per overlap cluster under `routing/`:

```json
{
  "cluster": "prompt-tooling",
  "members": ["prompt-craft", "prompt-engineer"],
  "cases": [
    { "id": "pos-...", "prompt": "...", "polarity": "positive",
      "expect_fires": ["prompt-craft", "prompt-engineer"], "tags": ["..."] },
    { "id": "neg-...", "prompt": "...", "polarity": "negative",
      "expect_not_fires": ["prompt-craft", "prompt-engineer"], "tags": ["near-miss"] }
  ]
}
```

- **positive** — an expected cluster member should fire.
- **negative** — a near-miss that shares vocabulary (write / fix / optimize / rewrite) but should
  route to NO cluster member.

## Running

```bash
# full suite, 3 runs per case (the methodology's default), ~4 parallel
python3 scripts/eval_routing.py evals/routing/prompt-tooling.json --runs 3

# cheap smoke check: one run each
python3 scripts/eval_routing.py --runs 1

# just the negatives
python3 scripts/eval_routing.py --case 'neg-*'
```

Each run is a fresh headless `claude -p … --plugin-dir .` session (the clean-context isolation the
methodology requires). The runner prints per-case pass/fail and rates and writes a `benchmark.json`.
Exit code is non-zero if any case fails, so you *can* gate on it — but see the caveat.

## How to read the results, and the caveat

Routing is **probabilistic**: a skill or agent fires perhaps half the time on a clear match, with
real run-to-run variance. So results are **rates over `--runs`, not booleans**, and a single low
positive rate is as likely to be variance as a real problem. The load-bearing signals are the ones
that survive that noise:

- **Regression** — a positive whose rate *drops* between two runs of this suite, e.g. right after a
  description edit. That is the eval-first check `prompt-engineer` asks for: run it before and after.
- **Over-trigger** — a negative that fires *at all*. A near-miss landing on the cluster means the
  description is too broad, and it's a defect regardless of variance (which is why negatives pass
  only at a 0% fire rate).

Because of that variance, this suite is meant to be run **manually, on demand** — before and after a
prompt change — not as a hard CI gate that would flake-fail honest PRs. It is intentionally *not*
wired into CI.

## Relationship to `claude plugin eval`

The native `claude plugin eval` is the right long-term home for this — it does ablation baselines,
repetitions, and LLM grading natively. It is currently **early access** and does not run in every
environment, so `scripts/eval_routing.py` is the stopgap that exercises these cases today. The case
files are kept close to the native shape so they migrate when it opens; the runner retires then.

## Coverage

Seeded with the tightest, highest-risk cluster (`prompt-tooling`: `prompt-engineer` vs
`prompt-craft`). Extend by adding a `routing/<cluster>.json` for the other overlaps
(`sde-fullstack` vs the craft skills, `homelab-platform` vs `service-onboard`/`lab-audit`/`runbook`,
the eng-ladder rungs) using the same shape.
