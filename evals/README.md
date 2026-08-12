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

The runner rejects any polarity other than literal `positive` or `negative`, a positive case with
no valid `expect_fires` member, an explicitly empty or invalid negative target set, and a threshold
outside `(0, 1]`. These are configuration errors, not low scores: each could otherwise make a case
pass without testing the declared routing boundary.

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
`models_observed` (read off the transcripts, i.e. what actually ran), `timeout_s`, `threshold`,
concurrency, Python runtime, and non-secret authentication/provider mode. Its provenance separately
hashes the exact eval definitions, selected cases, plugin under test, and executing evaluator and
grader files. Both runners self-bootstrap from one checked source buffer and compile imported
graders from likewise registered buffers, so those hashes name what executed rather than a later
read of the same paths. Provenance schema v3 executes a private copy of the identified plugin bytes,
so an A -> B -> A edit to the source checkout cannot make concurrent sessions load mixed content
while leaving equal endpoint hashes. Persistent mutation of the private snapshot aborts the artifact. A
same-user session can transiently mutate and restore that snapshot unless the host sandbox denies
writes; endpoint hashing does not claim to detect that, so host write isolation remains part of the
trust boundary. A benchmark without these identities is not a baseline: it cannot state what it
measured. If a single run mixes models, the runner also says so loudly.

### `INCONCLUSIVE` is not a failure

A run whose transcript cannot support a verdict — a timeout cut before anything fired, a spawn that
produced nothing — is **excluded from the rates**, and a case whose every run was excluded is
reported `INCONCLUSIVE` rather than failed. A measurement failure and a routing failure are
different facts, and conflating them sends you to audit descriptions when the problem is the clock.
When you see it, raise `--timeout` and re-run those cases; they are evidence in neither direction.

The test is usability, not silence. A session that reached a non-error `result` event **is** graded
for routing even if the CLI then exited non-zero — it routed somewhere, possibly off the fleet
entirely, and that is a real negative sample and a real positive miss. A structured error result is
never a no-route sample; a component firing observed before that error may remain explicitly
labeled partial evidence. Behavioral assertions are stricter: they require exit zero and a final
non-error result. Authentication failure or missing namespaced fleet registration aborts the whole
batch with exit 2 and writes no benchmark. These rules prevent quota, API, runner, expired-session,
or absent-plugin state from becoming a false green.

The default 180s timeout was tuned when sessions were faster. A more deliberative model can spend
longer than that before its first tool call, so **the timeout and the model are one decision** —
pin both together, and both are recorded in `conditions` (`timeout_s`, `model_requested`) because
a shorter timeout excludes more runs and therefore moves every rate in the artifact.

Each run is a fresh headless `claude -p … --plugin-dir .` session — a fresh *conversation*, which
is **not** configuration isolation: the session still inherits everything under the user's
`CLAUDE_CONFIG_DIR` (personal agents, skills, plugins, global CLAUDE.md), and a junction
deployment makes the fleet register twice, bare and namespaced, in every run (measured in the
[archived 2026-07-29 isolation outcome](../docs/archive/2026-07/verification-round-outcomes-2026-07-29.md)).
`--clean-room` relocates the configuration to a temporary
directory holding only credentials (`scripts/eval_clean_room.py`) and is recorded in `conditions`
— artifacts that differ on it measured different routing competitions and must not be diffed
against each other. The runner prints per-case pass/fail and rates; pass `--output-dir <path>`
to also write a `benchmark.json` there for before/after diffing. Exit codes separate the two things
you would do about them — `0` all passed, `1` a case failed (a routing verdict to investigate), `3`
nothing failed but something was `INCONCLUSIVE` (re-run it; nothing was measured), `2` a usage,
authentication, or registration error for which no benchmark was written. You *can* gate on
non-zero — but see the caveat.

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

The default `claude` runtime retains the complete case surface. The `codex` runtime is deliberately
bounded to direct-agent cases that declare `allowed_tools: []` and no `permission_mode`; skill
cases, tool-enabled cases, and cases requiring a Claude permission mode are refused before a model
call. A writer-role profile is eligible only when the selected contract explicitly declares
`allowed_tools: []`; the Codex session still runs read-only. This declaration selects the bounded
lane, but does not mean Codex has reproduced Claude's empty allowlist. Codex CLI 0.147.0 has no
main-session
`--agent` selector, so the adapter captures the selected generated
`.codex/agents/<name>.toml` once and projects its exact `developer_instructions` into one main
session. The artifact calls this
`generated-role-projection`: it measures generated role behavior, not custom-agent discovery,
routing, or delegation.

The full current `handoff-*` selection is Claude-only. Its builder case grants `Bash` and `Write`
inside the disposable scratch directory and requires `permission_mode: acceptEdits`, so the Codex
projection refuses that selector before spend. The stored 2026-08-11 Terra captures remain valid
for their exact prior no-tool cases; they are historical artifacts, not evidence for the amended
functional suite.

Codex execution requires an explicit, absolute, dedicated `CODEX_HOME` with a **ChatGPT
subscription login**. Perform its one-time `codex login` using file credential storage and the
same ChatGPT subscription that will run both sides. The adapter pins Codex CLI 0.147.0, requests
the built-in OpenAI provider, its ChatGPT Codex endpoint, and the ChatGPT login method, and requires
`codex login status` to report ChatGPT login before the batch starts. On PowerShell, initialize the
dedicated home once with the same overrides the evaluator uses:

```powershell
$env:CODEX_HOME = 'C:\absolute\path\to\dedicated-codex-eval-home'
codex -c 'model_provider="openai"' `
  -c 'openai_base_url="https://chatgpt.com/backend-api/codex"' `
  -c 'forced_login_method="chatgpt"' `
  -c 'cli_auth_credentials_store="file"' login
```

The artifact stores only
`{auth: chatgpt, provider: openai}`. No credential, account identifier, auth-file metadata, status
text, or Codex-home path enters the benchmark.

Because `--ignore-user-config` does not suppress every Codex-home surface, the preflight refuses
`AGENTS.md`, `AGENTS.override.md`, `config.toml`, or the higher-precedence `managed_config.toml` in
that home before checking auth or starting sessions. It also refuses non-empty `OPENAI_API_KEY`,
`CODEX_API_KEY`, or `CODEX_ACCESS_TOKEN` variables so an intended subscription capture cannot
silently become API-billed execution.

The command ignores user config and rules, sets project-document bytes to zero, uses an empty
disposable cwd, requests disabled configurable tool surfaces including the code-mode host,
suppresses host skill-catalog instructions, disables plan updates, pins a read-only sandbox with
approvals disabled, and sends the task on stdin. The runner also requires
`codex mcp list --json` to report no configured server before and after the batch. Every observable
non-message/reasoning item invalidates the run. In Codex 0.147.0,
however, code-mode-only models still see inert `exec`/`wait` entries and their custom-call attempts
are omitted from JSONL. The disabled host makes execution fail closed, but the artifact cannot
prove no attempt occurred.

Treat this as tool-reduced, observable-tool-invalidating same-runtime evidence, not Claude
empty-allowlist parity or ordinary interactive Codex behavior. This is also not complete
effective-configuration attestation: system and cloud-managed layers can still affect
instructions, features, sandboxing, or MCP behavior, and Codex 0.147.0 exposes no atomic
execution-equivalent preflight. Live capture therefore requires an independently controlled
machine and ChatGPT workspace with no system, cloud, or managed MCP servers. The pre/post empty
inventory checks are defense in depth, not a substitute for that activation prerequisite.

Codex requires an exact model and reasoning effort. Its current JSONL exposes usage but not an
independently observed model or server duration, so `model_requested` is not copied into
`models_observed`, and duration is labeled runner wall-clock time. Subscription runs consume plan
allowance rather than separately billed API-key usage; no dollar-cost claim is available. Never
diff a Claude artifact against a Codex artifact. A paired comparison keeps runtime, CLI, exact
model, effort, subscription auth, sandbox, timeout, concurrency, case bytes, and evaluator bytes
identical across baseline and candidate. Each side records its own selected-profile identity; those
profiles are expected to differ only through the intended HANDOFF-001 prompt edits.

Grading is deterministic — no judge model. `scripts/packet_lint.py` asserts packet-slot compliance,
including separate intake and lifecycle-owner Learning variants; the evaluator adds a closed
five-field oracle for non-procedural runbook proposals plus literal must-match / must-not-match
patterns per case. The seeded inventory covers packet completeness, semantic
Learning closeout and candidate fields, reviewer approval boundaries, adversarial embedded
instructions, live-change tier gates, incident and restore behavior, runbook proposal safety,
learning/runbook lifecycle composition, current-evidence precedence, architecture handoffs,
verification isolation and honest inconclusive verdicts, prompt-eval separation, and multi-agent
validation, plus proportional onboarding handoffs that preserve discovered constraints without
turning a simple build into packet ceremony. Each case artifact records input/output usage and
duration. The HANDOFF builder additionally uses the existing `semantic_oracle` seam: it seeds three
declarative JSON artifacts and a trusted acceptance program, refuses a changed verifier or linked
artifact, runs only that unchanged verifier, and records its exit/output plus artifact SHA-256
values. Model-authored Python is never executed as grader code; receipt patterns prove only the
transfer identity while the trusted verifier proves the end state. An unavailable duration is
`null`, never a fabricated zero. The runner prints the
selected case and session count before starting;
`evals/behavioral/contracts.json` is the authoritative inventory.

By default, a behavioral artifact does not retain raw model text. For diagnosis only,
`--retain-run-evidence` adds an ordered `run_evidence_per_run` list containing each final response
and that run's assertion failures; it requires `--output-dir`, and the conditions block records
that retention was enabled. Treat the resulting `benchmark.json` as potentially sensitive model
output: inspect it before committing or sharing it. The flag is evidence for separating a grader
defect from a prompt defect, not a different scoring path.

Behavioral documents are exact schemas, validated both by the runner before any session and by the
ordinary fleet validator. Unknown root or case keys, missing or duplicate identities, empty or
wrongly typed lists, unknown components or denied-tool names, unqualified agent names, invalid
packet modes or shapes, malformed or non-substantive positive regexes, and a case without exactly
one non-empty `expect_fires` XOR `expect_all_fires` contract, an explicit runtime-tool allowlist,
and a positive semantic output oracle are configuration errors. Typed `exact_fields` assertions
require one literal label with one exact value; a matching substring or duplicate conflicting line
cannot satisfy them. A
`runbook_required_gaps` list additionally binds a proposal case to its prompt-declared gap set as a
floor — every declared gap must be reported, and reporting a further gap from the closed vocabulary
is allowed because a prompt that names six unavailable things has not said the other two are
available; every gap must have its corresponding closed-vocabulary verification, and missing owner
or inventory evidence cannot coexist with an invented concrete owner or path. Learning candidate
blocks likewise reject unresolved or punctuation-only values and provenance without
source/freshness detail. Runbook paths reject traversal, trailing-dot aliases, and Windows reserved
device names. These failures exit before model cost can produce a misleading benchmark.

The packet linter deliberately **inverts** the scoring most self-evaluation tools use: honest
labeled uncertainty (`[unverified] I could not check X`) passes, while a confident "tests pass" with
no command or output cited fails. Missing evidence is a finding, never an assumption of correctness.
It is also deliberately **not** wired as a live hook — an output linter firing on real sessions
trains packet-shaped evasion.

Unlike routing, a behavioral case must pass **every** run: a contract that holds only sometimes does
not hold (and a case with *no* runs fails rather than passing vacuously — `--runs 0` used to report
every contract green having started nothing). Same manual-and-on-demand posture, and same reason —
real sessions, real cost, real variance.

Three case fields keep the measurement honest, added after review found the suite could pass
without measuring what it claimed. Every full case declares exactly one of the first two:

- **`expect_fires`** — the component whose contract is under test must actually have been invoked,
  read off the transcript with the same detection the routing suite uses. Without it, the main
  session can satisfy a packet shape or a keyword while the component never runs.
- **`expect_all_fires`** — every named component must be observed. Use this for composition
  contracts where an any-of assertion could pass after invoking only one half of the workflow.
- **`allowed_tools`** — always passed through `--tools`, including an explicit empty value that
  disables all tools. Planning-only skill cases allow only `Skill`; reasoning-only pinned agents
  allow none; the four scratch build/verification cases allow only `Bash` and `Write`. Names are
  validated against the CLI's full adopted runtime vocabulary, not merely the smaller fleet grant
  set, so alternate built-ins such as `PowerShell` cannot arrive by default.
- **`disallowed_tools`** — passed straight to the CLI, for any case whose prompt *describes* a
  destructive action after the name is validated against the complete mirrored CLI runtime-tool
  vocabulary, and forbidden from overlapping `allowed_tools`. It is defense in depth around the
  positive allowlist. The tier-gate case is the reason: it must never be able to perform the apply
  it exists to prove was refused. An eval that can cause the incident it tests for is not a test.

## Relationship to `claude plugin eval`

The native `claude plugin eval` is the right long-term home for this — it does ablation baselines,
repetitions, and LLM grading natively. It is currently **early access** and does not run in every
environment, so `scripts/eval_routing.py` is the stopgap that exercises these cases today. The case
files are kept close to the native shape so they migrate when it opens; the runner retires then.

## Coverage

Ten clusters are seeded — every overlap this README names, plus the altitude,
simple-stays-simple, and read-only-investigation seams:

| Cluster file | Members | Guards |
|---|---|---|
| `prompt-tooling.json` | prompt-craft, prompt-engineer | authoring/fixing an LLM artifact vs near-misses that share write/fix/optimize |
| `homelab-ops.json` | homelab-platform and eleven lab-operation skills | a lab request → the right lab component; near-miss → no lab component (the highest-risk overlap, over a live lab) |
| `craft-vs-fullstack.json` | backend-craft, frontend-craft, sde-fullstack, code-craft, ci-actions | single-layer vs cross-layer builder routing (the layer-ownership boundary this repo re-drew) |
| `ladder.json` | sde-fullstack, principal-engineer, distinguished-architect, eng-ladder | engineering altitude — scoped→builder, migration→principal, org/multi-year→distinguished |
| `proportionality.json` | sre-tool, eng-ladder, principal-engineer, distinguished-architect | simple-stays-simple (negative-only): small asks must fire NO heavy component; a builder/craft firing instead is correct |
| `investigation.json` | researcher, repository-investigator, code-reviewer, root-cause, application-security-auditor | trust-separated investigation: external/public research vs local/private source evidence vs a diff, failure, or source-to-sink audit |
| `agent-systems.json` | multi-agent-architect, prompt-engineer, principal-engineer | AI-agent system design and wrapper diagnosis vs one prompt or ordinary software architecture |
| `verification-seam.json` | verification-engineer, sde-fullstack, code-reviewer, root-cause | execute verification vs implement a fix vs static review vs root-cause diagnosis |
| `retro-boundary.json` | self-improve-loop, postmortem | non-incident retros and lesson routing vs the resolved-incident write-up; "retro"/"postmortem" vocabulary collisions and a live outage must reach neither |
| `continuous-improvement.json` | self-improve-loop, runbook, postmortem, root-cause, prompt-craft, prompt-engineer | learning intake, runbook-gap routing, lifecycle decisions, and negative boundaries against diagnosis, direct authoring, incidents, prompt repair, and ordinary builds |

`homelab-ops` is re-run and diffed whenever its membership changes. The captured baseline under
`baselines/2026-07/` predates `postmortem` joining the cluster on 2026-07-24 (4 members / 15 cases
there); the capture under `baselines/2026-07-24/` records the later 5-member / 18-case shape. Both
are *historical* anchors, not like-for-like comparisons with the current 12-member / 37-case
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
