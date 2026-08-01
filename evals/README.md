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

`expect_not_fires` is what a negative is graded against, and it defaults to the whole cluster — so
an ordinary near-miss passes only when nothing in the cluster fires. A case may **narrow** it to
name a *disambiguation* boundary instead: the components that must not fire, while a named sibling
legitimately may. `neg-resolved-not-incident` is the one in the tree — an already-resolved outage
must not reach the mitigation skills, but `postmortem` (a cluster member) is the correct
destination, so grading it cluster-wide failed the case for its sibling doing the right thing. Keep
the narrowing rare and visible: it is a declared exemption, the runner prints the forbidden set it
actually used, and every name in it must be a cluster member (a typo would forbid nothing and pass
vacuously).

## Running

The runner takes **one cluster file per invocation**, and defaults to `prompt-tooling.json` when
given none — there is no all-clusters mode, so "I ran the evals" without naming a file means one
default cluster was measured:

```bash
# one cluster, 3 runs per case (the methodology's default), ~4 parallel
python3 scripts/eval_routing.py evals/routing/prompt-tooling.json --runs 3

# every cluster — what "the full suite" actually takes
for f in evals/routing/*.json; do python3 scripts/eval_routing.py "$f" --runs 3; done

# cheap smoke check of ONE cluster (prompt-tooling, the default)
python3 scripts/eval_routing.py --runs 1

# just the negatives, still one cluster at a time
python3 scripts/eval_routing.py evals/routing/homelab-ops.json --case 'neg-*'

# a run whose numbers will be COMPARED to another's: pin the model, and give a slower
# model room to reach its first tool call before the timeout cuts the session
python3 scripts/eval_routing.py evals/routing/homelab-ops.json --runs 3 --model opus --timeout 420
```

### Pin the model, or the comparison is not one

**`--model` is required for any run you intend to diff against another.** Without it each session
takes whatever the CLI defaults to, and that default is **not** inherited from the session that
launched the runner — a `/model` change in an interactive session does not reach a `claude -p`
child. This silently invalidated a comparison here: two runs of `craft-vs-fullstack` believed to
differ by model tier were both sonnet, so their near-identical results said nothing about the tier.

Every `benchmark.json` therefore records a `conditions` block — `cli_version`, `model_requested`,
`models_observed` (read off the transcripts, i.e. what actually ran), `timeout_s`, and
`threshold`. A benchmark without it is
not a baseline: it cannot state what it measured. If a single run mixes models, the runner says so
loudly and that artifact should not be treated as one anchor.

### `INCONCLUSIVE` is not a failure

A run whose transcript cannot support a verdict — a timeout cut before anything fired, a spawn that
produced nothing — is **excluded from the rates**, and a case whose every run was excluded is
reported `INCONCLUSIVE` rather than failed. A measurement failure and a routing failure are
different facts, and conflating them sends you to audit descriptions when the problem is the clock.
When you see it, raise `--timeout` and re-run those cases; they are evidence in neither direction.

The test is usability, not silence. A session that reached its `result` event **is** graded even if
the CLI then exited non-zero — it routed somewhere, possibly off the fleet entirely, and that is a
real negative sample and a real positive miss. Dropping those would delete exactly the wrong-route
evidence and could let a mostly-misrouting positive pass on its one surviving run. Runs graded
despite trouble are listed in the output and kept in `benchmark.json` as `notes`.

The default 180s timeout was tuned when sessions were faster. A more deliberative model can spend
longer than that before its first tool call, so **the timeout and the model are one decision** —
pin both together, and both are recorded in `conditions` (`timeout_s`, `model_requested`) because
a shorter timeout excludes more runs and therefore moves every rate in the artifact.

Each run is a fresh headless `claude -p … --plugin-dir .` session — a fresh *conversation*, which
is **not** configuration isolation: the session still inherits everything under the user's
`CLAUDE_CONFIG_DIR` (personal agents, skills, plugins, global CLAUDE.md), and a junction
deployment makes the fleet register twice, bare and namespaced, in every run (measured 2026-07-29
by `scripts/probe_isolation.py`). `--clean-room` relocates the configuration to a temporary
directory holding only credentials (`scripts/eval_clean_room.py`) and is recorded in `conditions`
— artifacts that differ on it measured different routing competitions and must not be diffed
against each other. The runner prints per-case pass/fail and rates; pass `--output-dir <path>`
to also write a `benchmark.json` there for before/after diffing. Exit codes separate the two things
you would do about them — `0` all passed, `1` a case failed (a routing verdict to investigate), `3`
nothing failed but something was `INCONCLUSIVE` (re-run it; nothing was measured), `2` a usage
error. You *can* gate on non-zero — but see the caveat.

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

## The other half: behavioral evals

Routing measures **which component fires**. It says nothing about whether the thing that fired then
honored its own contract — so "the agents comply with their packet rules" was itself an unverified
claim. `evals/behavioral/` closes that, run by `scripts/eval_behavioral.py`:

```bash
python3 scripts/eval_behavioral.py --runs 1              # all cases
python3 scripts/eval_behavioral.py --case 'tier-gate-*'  # one contract
```

Grading is deterministic — no judge model. `scripts/packet_lint.py` asserts packet-slot compliance,
plus literal must-match / must-not-match patterns per case. Twenty-one contracts are seeded. They
cover packet completeness, reviewer approval boundaries, adversarial embedded instructions,
live-change tier gates, incident and restore behavior, architecture handoffs, verification
isolation and honest inconclusive verdicts, prompt-eval separation, and multi-agent validation.
The count is descriptive, not a quota; `evals/behavioral/contracts.json` is the authoritative
inventory.

The packet linter deliberately **inverts** the scoring most self-evaluation tools use: honest
labeled uncertainty (`[unverified] I could not check X`) passes, while a confident "tests pass" with
no command or output cited fails. Missing evidence is a finding, never an assumption of correctness.
It is also deliberately **not** wired as a live hook — an output linter firing on real sessions
trains packet-shaped evasion.

Unlike routing, a behavioral case must pass **every** run: a contract that holds only sometimes does
not hold (and a case with *no* runs fails rather than passing vacuously — `--runs 0` used to report
every contract green having started nothing). Same manual-and-on-demand posture, and same reason —
real sessions, real cost, real variance.

Two case fields keep the measurement honest, both added after review found the suite could pass
without measuring what it claimed:

- **`expect_fires`** — the component whose contract is under test must actually have been invoked,
  read off the transcript with the same detection the routing suite uses. Without it, the main
  session can satisfy a packet shape or a keyword while the component never runs.
- **`disallowed_tools`** — passed straight to the CLI, for any case whose prompt *describes* a
  destructive action. The tier-gate case is the reason: it must never be able to perform the apply
  it exists to prove was refused, so it names a non-existent path and is denied write and shell
  tools. An eval that can cause the incident it tests for is not a test.

## Relationship to `claude plugin eval`

The native `claude plugin eval` is the right long-term home for this — it does ablation baselines,
repetitions, and LLM grading natively. It is currently **early access** and does not run in every
environment, so `scripts/eval_routing.py` is the stopgap that exercises these cases today. The case
files are kept close to the native shape so they migrate when it opens; the runner retires then.

## Coverage

Nine clusters are seeded — every overlap this README names, plus the altitude,
simple-stays-simple, and read-only-investigation seams:

| Cluster file | Members | Guards |
|---|---|---|
| `prompt-tooling.json` | prompt-craft, prompt-engineer | authoring/fixing an LLM artifact vs near-misses that share write/fix/optimize |
| `homelab-ops.json` | homelab-platform and ten lab-operation skills | a lab request → the right lab component; near-miss → no lab component (the highest-risk overlap, over a live lab) |
| `craft-vs-fullstack.json` | backend-craft, frontend-craft, sde-fullstack, code-craft, ci-actions | single-layer vs cross-layer builder routing (the layer-ownership boundary this repo re-drew) |
| `ladder.json` | sde-fullstack, principal-engineer, distinguished-architect, eng-ladder | engineering altitude — scoped→builder, migration→principal, org/multi-year→distinguished |
| `proportionality.json` | sre-tool, eng-ladder, principal-engineer, distinguished-architect | simple-stays-simple (negative-only): small asks must fire NO heavy component; a builder/craft firing instead is correct |
| `investigation.json` | researcher, repository-investigator, code-reviewer, root-cause, application-security-auditor | trust-separated investigation: external/public research vs local/private source evidence vs a diff, failure, or source-to-sink audit |
| `agent-systems.json` | multi-agent-architect, prompt-engineer, principal-engineer | AI-agent system design and wrapper diagnosis vs one prompt or ordinary software architecture |
| `verification-seam.json` | verification-engineer, sde-fullstack, code-reviewer, root-cause | execute verification vs implement a fix vs static review vs root-cause diagnosis |
| `retro-boundary.json` | self-improve-loop, postmortem | non-incident retros and lesson routing vs the resolved-incident write-up; "retro"/"postmortem" vocabulary collisions and a live outage must reach neither |

`homelab-ops` is re-run and diffed whenever its membership changes. The captured baseline under
`baselines/2026-07/` predates `postmortem` joining the cluster on 2026-07-24 (4 members / 15 cases
there); the capture under `baselines/2026-07-24/` records the later 5-member / 18-case shape. Both
are *historical* anchors, not like-for-like comparisons with the current 11-member / 33-case
cluster. Re-baseline whenever membership changes.

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
