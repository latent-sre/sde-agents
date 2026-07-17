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
methodology requires). The runner prints per-case pass/fail and rates; pass `--output-dir <path>`
to also write a `benchmark.json` there for before/after diffing. Exit code is non-zero if any case
fails, so you *can* gate on it — but see the caveat.

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

Four clusters are seeded — every overlap this README names:

| Cluster file | Members | Guards |
|---|---|---|
| `prompt-tooling.json` | prompt-craft, prompt-engineer | authoring/fixing an LLM artifact vs near-misses that share write/fix/optimize |
| `homelab-ops.json` | homelab-platform, service-onboard, lab-audit, runbook | a lab request → the right lab component; near-miss → no lab component (the highest-risk overlap, over a live lab) |
| `craft-vs-fullstack.json` | backend-craft, frontend-craft, sde-fullstack | single-layer vs cross-layer builder routing (the layer-ownership boundary this repo re-drew) |
| `ladder.json` | sde-fullstack, principal-engineer, distinguished-architect, eng-ladder | engineering altitude — scoped→builder, migration→principal, org/multi-year→distinguished |
| `proportionality.json` | sre-tool, eng-ladder, principal-engineer, distinguished-architect | simple-stays-simple (negative-only): small asks must fire NO heavy component; a builder/craft firing instead is correct |

`homelab-ops` is a **baseline of the current members**, to be re-run and diffed after the planned
`incident` / `restore-drill` / `upgrade-campaign` skills land (see
`docs/skills-modernization-plan.md`). A captured baseline lives under `baselines/`.

### Measurement caveat: skills fire, agents must be delegated to

This runner grades on which component the headless session actually **invoked** — a Skill tool call
(a skill fired) or an Agent/Task spawn (a subagent fired). Those are not equally likely. A skill is
invoked inline in the main session; an **agent** only registers when the main session chooses to
**delegate** to it, and a one-shot `claude -p` session tends to just start doing the work (often with
`Bash`) rather than spawn a subagent — so **agent positives systematically under-fire here relative
to skill positives**, and a low agent-positive rate is partly a property of headless one-shot mode,
not only of the description. Read the clusters accordingly:

- **Skill-heavy clusters** (`prompt-tooling`, the skill positives of `homelab-ops`) measure routing
  cleanly.
- **Agent positives** (`homelab-platform`, the `ladder` and `craft-vs-fullstack` agent members) are
  a weaker signal one run at a time; trust the **negatives** (over-trigger is a real defect at any
  rate) and **regressions across runs** over an absolute agent-positive rate.
- The native `claude plugin eval` (see below) delegates properly and will tighten the agent signal;
  these case files migrate to it unchanged.
