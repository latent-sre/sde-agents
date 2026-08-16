# Repository guide for coding agents

This repository packages one fleet for Claude Code, Codex, GitHub Copilot CLI, and VS Code Agent
Plugins. The definitions in `agents/` and `skills/` are the only authored source and exactly what
Claude Code loads. Codex, Copilot, and VS Code load generated host adapters. Edit the canonical
files directly and regenerate; never edit a generated copy or resolve a Claude fleet file under
`~/.claude`, which does not contain this fleet once it ships as a plugin. Every script under
`scripts/` states its own contract in its docstring — read it before touching or invoking one.

This file is the fleet's own instance of the project context convention that `README.md` defines
for target repositories. Where it paraphrases the README or a script's docstring, that source wins
on conflict — fix the paraphrase here, never the source. The validator holds this file to that
rule: the `@AGENTS.md` bridge in `CLAUDE.md`, every concrete multi-segment repo path named here,
and the model-alias list are checked against the source and fail on drift.

## The engineering program

The fleet is one program built on one premise: **a session is stateless.** Whatever it learns,
decides, or verifies dies at exit unless it lands in an artifact — and the next session reads
that artifact with no memory of why it was written, trusting it more than it should. Each strand
below is one engineered consequence; `docs/engineering-program.md` maps each strand to its
mechanisms and checks — read it before touching a discipline.

- **Handoff engineering — artifacts are the only carrier.** A handoff is complete only when the
  receiver can act correctly with nothing but the artifact (packets, ledger rows, work orders).
- **Loop engineering — convergence across memoryless sessions.** Audits, incidents, campaigns,
  and eval rounds must converge even though every iteration starts amnesiac; written exceptions,
  recurrence-merged rows, and literal status transitions make that possible.
- **Graph engineering — authority is typed edges.** Who may write what, who hands to whom, where
  approval sits: declared per definition, enforced per host, never inferred from prose. Owner:
  `docs/decisions/2026-07-31-ai-graph-engineering.md`.
- **Self-learning — admission-gated memory.** `scripts/learning_ledger.py` quarantines every
  lesson behind evidence-bound staged promotion: a stored lesson is replayed uncritically, so a
  wrong one compounds instead of fading.

The reading rule for any review of fleet prose: **the reader is the next session, not the
operator's memory.** Apparent ceremony here is usually a strand mechanism. Two questions decide
any trim: who is the real reader, and what consumes the artifact — "only the operator" and
"nothing" means trim it; a future session, script, grader, or guard as consumer means the trim
is a regression. The counterweight: coordination is not free — fewer handoffs over richer ones,
one writer per artifact, structure only at the boundaries that remain.

## Validate before you push

Validation is tiered: depth matches risk, and each tier reuses the previous tier's evidence
instead of recomputing it.

- **T0 — edit loop** (seconds): `python3 scripts/validate_fleet.py` plus the test module that
  owns what you touched (`python3 -m unittest discover -s tests -p test_<area>.py`). The
  validator byte-compares every generated adapter itself, so a separate
  `generate_platform_adapters.py --check` adds nothing here; `--write` (below) remains the
  regeneration command after canonical edits.
- **T1 — before push / PR**: the full offline suite via `python3 scripts/run_tests.py` (one
  process per module, in parallel — a serial `python3 -m unittest discover -s tests -v` proves
  the same thing at the sum of the module times instead of roughly the longest one), plus
  `claude plugin validate . --strict` for the platform contract. CI runs the validator, the
  tests, and the ledger-drift report on Ubuntu for every PR, and the plugin contract check on
  Linux. Also run `python3 scripts/fleet_doctor.py` — it is **local-only and CI can never
  substitute for it**, because the drift it finds lives in your host installation rather than in
  the checkout every other tier reads. Exit 3 means at least one warning — read the report to see
  which; host drift from what the repository ships is the common case, and its repair is
  `python3 scripts/install_codex_agents.py --user`. Treat a warning as owed work before you
  measure anything: a session running against a stale installed profile is not testing the fleet
  you edited, which is how a superseded, materially stricter `homelab-platform` profile drove a
  whole Codex-host session and cost roughly ten hours (issue #126).
- **T2 — merge and weekly** (CI-owned): pushes to main, the Monday sweep, and manual dispatch
  run the full Linux/macOS/Windows matrix, so platform-specific guard and hook paths are
  exercised without billing every PR for them (see the matrix comment in
  `.github/workflows/validate.yml`).
- **T3 — release / CLI pin bump** (manual, real API): `scripts/probe_plugin.py` and the eval
  suites, per the section below. Before a paired routing run, `scripts/eval_baseline.py`
  reports whether a stored benchmark already covers the 'before' side — reuse it when it does;
  the 'after' side is always fresh.

Static review has a convergence bound. A prose-behavior change (agent or skill text) gets at
most **two** deep-review rounds: when a later round's criticals land in sentences the previous
round's fix introduced, the loop is diverging — natural-language rules have unbounded
hypothetical attack surface, so each rewrite mints the next round's findings. Close with the
instrument that measures behavior instead (a live behavioral-contract run, or an executed
verification pass); a third static round happens only on an explicit operator ruling. This rule
exists because one branch spent six rounds and ~1.5M review tokens finding defects only in its
own successive fixes.

After **any** canonical agent or skill edit, regenerate the host adapters:

```bash
python3 scripts/generate_platform_adapters.py --write
```

After adding, renaming, or removing a component, also refresh the README inventory:

```bash
python3 scripts/validate_fleet.py --write-inventory
```

## Development loop

Load the plugin from the working tree — `/plugin install` runs from a cached copy, which is the
wrong Claude loop when the plugin is what you are editing:

```bash
claude --plugin-dir .
```

The Copilot CLI, VS Code, and Codex local loops are owned by `README.md`'s Install section.
Standalone Codex agent sync — including `/import`'s one-time-migration limits and the exact-match
adoption contract — is owned by the `scripts/install_codex_agents.py` docstring.

Three checks are manual and on demand, deliberately not CI gates (all drive real model sessions):

- `python3 scripts/probe_plugin.py` — proves the fleet *loads*, `${CLAUDE_PLUGIN_ROOT}` expands,
  and the guard fires for the guarded agents and only them. Owed at every CLI pin bump (the pin
  lives in CI's `claude-plugin-contract` job): the probe is the only runtime proof the pinned
  binary still honors the guard's payload contract (owner: the `scripts/readonly-guard.py`
  docstring).
- `python3 scripts/eval_routing.py evals/routing/<cluster>.json --runs 3` — routing evals, owed
  before **and** after any description edit (the description playbook owns the recipe). Read
  `evals/README.md` first — it owns the negative-case and narrowing semantics and the headless
  caveat.
- `python3 scripts/eval_behavioral.py --runs 3` — deterministic contract evals, using Claude by
  default. The narrower Codex subscription lane (`--runtime codex`; transport
  `scripts/eval_codex_runtime.py`) is documented — invocation and eligibility limits — in
  `evals/README.md`; read it before running that lane.

One report is manual, on demand, and **offline** — no model session, no API cost:

```bash
python3 scripts/capability_graph.py --root . --emit graph.json --mermaid graph.mmd
```

Run it when reviewing fleet topology, or against two checkouts to compare a baseline with a
candidate — output is deterministic, and generated output is never committed (this report's
output, not the host adapters). Read it with its three layers kept
apart: authored edges are what the files declare, each host projection states only that host's
control and its limitations, and the routing overlay is co-membership plus separately identified
case assertions — co-membership is not behavioral coverage. Every section is advisory.
Deliberately **not** a T0, CI, or PR gate: an advisory that became a gate would make each
topology observation a merge blocker.

The design validator is the other offline on-demand tool, and it takes one explicit document:

```bash
python3 scripts/workflow_contract.py path/to/design.json --root .
```

Read the verdict as what it says — **design-consistent, not runtime-enforced**: no host checks a
workflow this way at dispatch, and approval coverage stops at every `subgraph` boundary. Schema
v1 is deliberately narrow; the semantics it excludes (`any`/quorum joins, late arrival,
cancellation, reset) wait for GRAPH-004.

## Change playbooks

**Any edit** — run the validator and the tests. If you touched text that paraphrases another file,
find the declared owner and fix in the right direction (see "Owned conventions" below).

**Editing any canonical agent or skill** — run
`python3 scripts/generate_platform_adapters.py --write` after the canonical edit. Generated copies
are consequences, never edit targets. The validator compares every generated byte and rejects
missing, stale, extra, or hand-edited output.

**Editing a description** (agent or skill) — descriptions drive routing. Run the overlapping
cluster in `evals/routing/` before and after, and diff the rates. The 'before' side may be
satisfied by a stored benchmark `scripts/eval_baseline.py` reports `REUSABLE` under the intended
conditions; the 'after' side is always a fresh run. Cross-references to other fleet
members must use the plugin namespace (`sde-agents:code-reviewer`, `/sde-agents:backend-craft`);
a bare backticked name is only for content already in context, such as a preloaded skill.

**Adding an agent** — the checklist the validator will hold you to:

- kebab-case `name:` equal to the filename; description ≤ 1024 chars, with trigger phrasings and
  negative routing ("Not for X — use `sde-agents:Y`").
- An explicit `tools:` list. Omitting it is not a harmless default — the agent **inherits every
  tool**. No parenthesized specifiers: `Bash(git diff:*)` and `Agent(worker)` are silently ignored
  by the runtime while reading as limits, so the validator rejects them. New built-in tools outside
  the fleet's adopted set must be added to `FLEET_TOOLS`; exact MCP tools go in
  `FLEET_MCP_TOOLS`. Add either deliberately — every entry is authority, and server-wide MCP
  grants are rejected because they silently acquire future tools.
- `model:` must be an alias (`inherit`, `haiku`, `sonnet`, `opus`, `fable`). A full model ID is a
  valid runtime value but banned: it goes stale silently while an alias follows the model upgrade.
- An end-of-task packet section (`## Output format` or a `## … packet` heading). If the body uses
  evidence labels, copy the canonical `[verified]/[sourced]/[unverified]` stems verbatim from an
  existing agent — the validator pins the exact phrasing so the triad cannot drift file by file.
- `skills:` entries must resolve to `skills/<name>/SKILL.md` and must not name a
  `disable-model-invocation` skill — such a skill cannot be preloaded, so listing it configures
  nothing.
- Holding `Bash` with no write tool (`Write`/`Edit`/`NotebookEdit`) makes it a read-only agent, and
  it **must** be added to `GUARDED_AGENT_NAMES` in `scripts/readonly-guard.py` or the validator
  fails: unguarded, its "read-only" is a promise, not a control.
- Regenerate every host adapter and refresh the README inventory; seed or extend a routing cluster
  if the remit overlaps an existing member (overlap is fine — unmeasured overlap is not).

**Adding a skill** — directory name equals `name:`; every path a SKILL.md mentions under
`references/`, `assets/`, or `scripts/` must exist, and every file under `references/` must be
linked from SKILL.md by a **skill-relative** path (an unlinked reference file is dead knowledge
that looks shipped — the orphan check fails it). A skill with side effects sets
`disable-model-invocation: true`, which also removes it from `Skill`-tool reach and from agent
preloading — route to it via a slash command or an agent that works its checklist.
Regenerate afterward: Copilot retains that explicit-invocation frontmatter, while Codex expresses
the same policy through each skill's generated OpenAI agent-policy file.

**Touching the Claude guard or hook** — read the docstrings in `scripts/readonly-guard.py` and the
README guard section first; then run the tests *and* the probe. Non-negotiables: the allowlist grows by
adding a *reader*, never an interpreter (no `python`, `pytest`, `npm`, `make`, no exemption for
this repo's own scripts); the hook resolves the guard through `${CLAUDE_PLUGIN_ROOT}` so a
repository under review can never supply it; it fails closed for guarded agents and no-ops for
everyone else; and the 42/43 exit-code contract between guard and hook shell string stays intact —
it is how the hook tells the guard's answer from a stand-in interpreter that merely exits 0.
Do not port that hook to Codex, Copilot, or VS Code: their `PreToolUse` payload does not supply the
active-agent identity used for scoping. Preserve the host-specific tool or sandbox controls instead;
`hooks/copilot-hooks.json` is the deliberately empty override that keeps Copilot and VS Code from
loading the Claude guard — leave it empty, it is doing its job.

**Changing validator behavior** — add a fixture under `tests/fixtures/` that violates exactly the
rule you are adding — or, for an invariant about this repo's real wiring, a mutation test in
`tests/test_validate_fleet.py` that copies the repo and breaks the one link — plus a test that
fails without your change. Match the existing error-message
register: each message says what broke *and why it would have failed silently*.

**Adding a defensive branch to a fleet script** — a crash-recovery, authority, or
input-validation guard lands in the same change as a test that makes it fire; when the trigger is
hard to stage, prove the branch non-vacuous by mutation (remove it and watch the test fail). An
untested guard reads as enforcement while enforcing nothing — the exact silent failure the
validator rules exist to catch, and it will pass every existing check because no check knows the
branch is there. The doc-side twin is equally binding: prose that calls an invariant "validated"
or "enforced" lands with the reader check and its firing test, or it is reworded as writer
behavior — a prose claim of enforcement with no guard behind it survives every check for the
same reason an untested guard does (executed-verification finding, 2026-08-10).

**Retiring a tripwire whose risk is structurally gone** — the symmetric half of the
defensive-branch rule above. A tripwire test names the silent failure it watches for (its
docstring's risk hypothesis); a change that makes that failure impossible *by construction* —
consolidating the second parser a drift test watched, removing the config surface a guard
checked — retires the test in the same change, with the elimination stated in the commit. The
suite is evidence, not a ledger of past fears: a test whose hypothesis can no longer occur
re-proves nothing (the proportionality rule already bans that) while still taxing every edit
that touches its fixtures. The bar is structural impossibility, not "hasn't fired lately" — a
quiet tripwire watching a still-possible failure stays, and when the two readings are arguable
the test stays and the doubt is recorded where the retirement would have been.

**Closing a task that surfaced a discovery** — a platform fact, a recurring failure, a doc found
wrong, a routing miss — route it per `skills/self-improve-loop/references/discovery-routing.md`
before closing out: routed, filed as a gap, or dropped with a stated reason. Silence is not a
disposition. `docs/fleet-roadmap.md` is the only task tracker; a GitHub issue is evidence-bound
intake that adds work only when the roadmap imports it (`docs/README.md` rule 7).

## Opening a pull request

Work reaches the default branch through a topic branch and a merge-commit PR, never a direct
push — every gate in this section attaches to the PR mechanism, and a direct push bypasses them
all silently. Branch names use the expanded conventional form `<type>/<kebab-slug>` (`feat`,
`fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`, `build`), so the branch list reads as a
change inventory. Merge commits keep branch history on the default branch, so a canonical edit
and everything it makes necessary — regenerated adapters, a refreshed README inventory, a
guard-list entry — land in the same commit, keeping every commit validator-green for bisect and
revert (writer discipline, not an enforced gate: CI validates the PR head, not each commit).

`.github/pull_request_template.md` is the shape, and it owns its own detail. Write every line —
commit messages included — in the claim-plus-consequence register the template models: what
changed *and* what it means, because a reviewer can only disagree with a decision they can see.
Fill the conditional-gates rows your change tripped — the table names the situational check each
change type owes. Keep "Deliberately not done" honest and the whole template short.

The automated review is request-triggered; opening a PR does not request it, and requesting is an
**operator step**: the reviewer bot resolves through neither `gh` nor the REST API — both fail
silently — and is assigned only in the PR page's Reviewers box (the Codex connector follows
Copilot's request). An agent opening a PR hands the request to its operator and says so, never
reporting the PR as awaiting review.

Wait for both passes **on the current head** — a review-driven edit mints bytes the cleared
passes never saw, so the last edit owes another wait — and disposition every comment: applied, or
declined with the reason. At most **two** review-driven edit rounds per PR; a later finding is
dispositioned in the thread without new bytes (declined with the reason, or recorded as owed work
in `docs/fleet-roadmap.md`) unless an explicit operator ruling buys one further round, the same
one-round escape as the deep-review bound's third static round. The cap bounds edits, never
waits. Provenance: `docs/decisions/2026-08-16-pr-review-gate.md`.

## Hard rules with no playbook exceptions

- **Standard library only.** The validators, generators, installers, guard, hook, and tests use only
  the Python standard library. Do not add dependencies.
- **Generated adapters are not a second source.** Never hand-edit `.claude/agents/`,
  `.github/agents/`, `.codex/agents/`, `platforms/copilot/skills/`, or
  `plugins/sde-agents/skills/`. Change the
  canonical file or generator, regenerate, and let byte-drift validation prove the result.
- **One parser per fact.** `scripts/fleet_records.py` is the fleet's only parser for frontmatter,
  `tools:` values, and namespaced references; every validator, generator, and report builds on its
  records. A second parser would let two reports about the same tree disagree with nothing to
  arbitrate them — extend the shared records, never parse alongside them.
- **Authority is host-specific.** Claude's guard, Copilot/VS Code's omission of `execute` from
  guarded roles, and Codex's `sandbox_mode` are distinct controls. Never replace one with
  compatible-looking prose or load the Claude hook on a host whose payload cannot scope it.
  `workflows/` is Claude-only for the same reason: Copilot, VS Code, and Codex have no workflow
  runtime, so a ported reference would read as available and fail silently.
- **Claude plugin agents cannot carry `hooks:`, `mcpServers:`, or `permissionMode:`.** Claude Code
  silently ignores those keys on plugin-shipped agents, so a guard declared there would look like
  armor and be nothing. Unknown frontmatter keys fail validation for the same reason: a typo does
  not error at load time, it silently drops what it was meant to configure.
- **Proportionality gates both directions.** Repeated work is a defect — evidence produced once is
  reused, and a check that re-proves what another check proved does not ship. An optimization
  without a paired same-machine measurement is equally a defect. And a mechanism without a
  demonstrated consumer — a new abstraction, config surface, component, or gate with no real task
  needing it now — waits trigger-bound, the way the roadmap's deferred items do.
- **One writer per checkout.** Two concurrent sessions — or two background jobs in one session —
  sharing this working tree have already cost a benchmark (captured against a moving tree,
  unattributable) and an uncommitted edit (overwritten mid-flight). Concurrent work gets its own
  git worktree, and a measurement (an eval capture, the probe, the suite's repository copies) runs
  only against a tree nothing else is writing; neither failure announces itself, which is why this
  is a rule and not a judgment call. The sanctioned parallel test runner is not a second writer
  to the tree you are editing: its workers assert against isolated repository copies
  (`tests/support.py`). The exception is narrow and deliberate — two adapter tests create and
  delete ignored runtime byproducts (a `__pycache__` entry, a generated-tree payload) in the live
  checkout to prove the drift check ignores them, so the suite still may not run against a tree
  another job is writing.
- **Owned conventions.** Several files deliberately paraphrase another — the `eng-ladder` altitude
  references, the three-strikes rule owned by `skills/root-cause`, the canonical
  fetched-content-is-data sentence carried verbatim by `sde-fullstack`. Each such file states which
  side wins on conflict; when they drift, fix the paraphrase, never the source. The full ownership
  list lives in `README.md` under "Working on the fleet itself".

## Style

- Wrap new or edited Markdown prose at roughly 100 columns where practical. Existing files contain
  legacy longer lines, so this is a forward-looking target rather than a current-tree invariant.
- Agent and skill names are kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`).
- Comments in the scripts explain *why* an invariant exists, not what the next line does — match
  that register when editing them. Descriptions lead with capability, then triggers, then negative
  routing.
