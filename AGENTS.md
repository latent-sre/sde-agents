# Repository guide for coding agents

This repository packages one fleet for Claude Code, Codex, GitHub Copilot CLI, and VS Code Agent
Plugins. The definitions in `agents/` and `skills/` are the only authored source and exactly what
Claude Code loads. Codex, Copilot, and VS Code load generated host adapters. Edit the canonical
files directly and regenerate; never edit a generated copy or resolve a Claude fleet file under
`~/.claude`, which does not contain this fleet once it ships as a plugin.

This file is the fleet's own instance of the project context convention that `README.md` defines
for target repositories. Where it paraphrases the README or a script's docstring, that source wins
on conflict — fix the paraphrase here, never the source. The validator holds this file to that
rule: the `@AGENTS.md` bridge in `CLAUDE.md`, every concrete multi-segment repo path named here,
and the model-alias list are checked against the source and fail on drift.

## The engineering program

This is not a prompt library. It is one engineering program with four strands, and most of the
disciplines below that look odd in isolation are mechanisms of one of them:

- **Handoff engineering.** Sessions are stateless and forget everything at exit, so a fleet
  artifact — a review packet, a ledger row, a work order, a runbook slot, an audit findings
  table — is the only bridge between the session that wrote it and the session that acts on it.
  HANDOFF-001's digest-bound work orders are the explicit form; the packet contracts everywhere
  else are the ambient form.
- **Loop engineering.** Audits, incidents, upgrade campaigns, and eval rounds are loops that must
  converge across sessions. Written exceptions, recurrence-merged ledger rows, and literal status
  transitions (`open` → `accepted`, outage → follow-up) are the convergence mechanisms: without
  them a memoryless successor re-flags the same finding forever, or holds emergency authority
  past the emergency.
- **Graph engineering.** Authority is typed edges: which member may write what, who hands to
  whom, where approval sits. A read-only emitter paired with a write-authority consumer — the
  audit skills' ledger rows, the guard roster — is a deliberate split, not indirection. Owned by
  `docs/decisions/2026-07-31-ai-graph-engineering.md`.
- **Self-learning.** The fleet improves itself through `scripts/learning_ledger.py` and the
  `self-improve-loop` skill: evidence-bound, quarantined intake with staged promotion, because a
  session replays stored lessons uncritically — an unverified lesson propagates its error into
  every future session that retrieves it.

The reading rule that follows, binding on reviews of fleet prose: **the reader is the next
session, not the operator's memory.** A fleet of stateless workers re-creates the conditions
organizations invented ceremony for — no shared memory, artifact-only communication, claims that
cannot be trusted unverified — so owner slots, status lifecycles, contemporaneous capture, and
written justifications are often coordination mechanisms wearing organizational vocabulary.
Before trimming one as disproportionate, identify its real reader and confirm nothing consumes it
(PROP-002's scanner judged against an audience of one human and mis-tiered exactly this class).
The counterweight binds equally: coordination is not free — prefer fewer handoffs over richer
ones, keep one writer per artifact, and put structure only at the boundaries that remain.

## Map

| Path | What it is |
|---|---|
| `agents/*.md` | Canonical subagent definitions, loaded as-is by Claude. Filename must equal `name:`. |
| `skills/<name>/SKILL.md` | Canonical skills; `references/` and `assets/` sit beside each. |
| `.claude/agents/` | Generated, Claude-compatible staging profiles for Codex's official `/import` migration. Never edit them directly. |
| `.github/agents/`, `.codex/agents/` | Generated Copilot/VS Code and Codex agent adapters. Never edit them directly. |
| `platforms/copilot/skills/`, `plugins/sde-agents/skills/` | Generated host-specific skill copies. Never edit them directly. |
| `plugin.json`, `.claude-plugin/`, `.agents/plugins/marketplace.json`, `plugins/sde-agents/.codex-plugin/` | Host manifests. Identity and versions must remain aligned. |
| `hooks/hooks.json` | The **Claude-only** session guard; plugin agents cannot carry `hooks:`. |
| `hooks/copilot-hooks.json` | Empty override that prevents Copilot/VS Code from loading the Claude guard. |
| `workflows/deep-review.js` | Claude-only plugin workflow (deterministic multi-agent review pipeline). `workflows/` is auto-discovered at plugin root; **never** adapted to other hosts — Copilot, VS Code, and Codex have no workflow runtime, so a ported reference would read as available and fail silently. |
| `scripts/readonly-guard.py` | Allowlist guard for read-only agents that hold `Bash`. Read its docstring before touching it. |
| `scripts/generate_platform_adapters.py` | Generates and validates every non-Claude adapter. |
| `scripts/install_codex_agents.py` | Safely synchronizes standalone Codex agents into an explicit scope. |
| `scripts/fleet_records.py` | The fleet's one parser for frontmatter, `tools:` values, and namespaced references, plus the typed records built from them. It records and never judges; a second parser would let two reports about the same tree disagree with nothing to arbitrate them. It parses an inspected tree as data and never imports or executes it, so a foreign or frozen-baseline checkout is safe to read. |
| `scripts/capability_graph.py` | On-demand operator topology report over a fleet checkout — authored edges, per-host authority projections, and the routing overlay, kept separate on purpose. Advisory only: it is never a T0 or PR gate, and it emits no unioned fleet authority. |
| `scripts/workflow_contract.py` | Design-consistency validator for one prospective workflow document (schema v1). It proves `design-consistent`, never `runtime-enforced`: nothing here executes, and no host validates a workflow this way at dispatch. Takes one explicit path, never scans a directory, and `validate_fleet.py` never calls it. |
| `scripts/validate_fleet.py` | Fleet-policy validator; every rule is a tripwire for a failure that is silent at runtime. |
| `scripts/run_tests.py` | Parallel test runner — one process per module, exactly the discovery invocation T0 uses. |
| `scripts/probe_plugin.py` | Behavioral probe against a real headless session. |
| `scripts/eval_routing.py` | Routing-eval runner over `evals/routing/*.json`; read `evals/README.md` first. |
| `scripts/eval_baseline.py` | Offline resolver from current bytes to a still-valid stored routing benchmark; it answers whether a paired run's 'before' side is already on disk before any API money is spent. |
| `scripts/eval_behavioral.py` | Behavioral-contract runner over `evals/behavioral/contracts.json`; Claude is the default, while bounded empty-Claude-allowlist cases can use `--runtime codex` through a tool-execution-disabled generated-role projection. Both bind source, execution bytes, evaluator/grader, runtime, concurrency, and non-secret auth-mode provenance. |
| `scripts/eval_codex_runtime.py` | Narrow Codex behavioral transport; it captures each selected generated agent once, requires a dedicated instruction-clean Codex home, rejects observable tool events, and reuses opaque ChatGPT login state without reading credentials. |
| `scripts/learning_ledger.py`, `learning/` | Fail-closed repository-local intake for evidence-bound learning candidates. It records applicability-bound recurrence, lifecycle decisions, and bounded review renewal; it never edits or approves a destination. |
| `scripts/ledger_drift.py` | Advisory CI watch for pending learning candidates whose named destinations changed later, plus intake with no watchable destination. |
| `scripts/fleet_doctor.py` | Read-only health report over the repository **and this host's installation** — generated-adapter drift, manifest alignment, canonical line endings, which host CLIs are present, and whether the standalone Codex agents still match the generated roles. It is the only check that sees the gap between what this repository ships and what your session actually loads; a stale installed profile is invisible to every other tier because they all read the checkout. Exit 0 clean, 3 warnings, 1 a failed check, 2 unreadable. It never generates, installs, prunes, or runs a model session — the fix it reports is yours to run. |
| `tests/` | Stdlib unittest suite. `tests/fixtures/` holds minimal repos that each violate exactly one rule. |
| `docs/` | The roadmap, decision records, and `archive/`. `docs/fleet-roadmap.md` is the only file that tracks unfinished or deferred work; `docs/README.md` maps authority. GitHub issues are evidence-bound intake, not a second tracker — an issue adds work only when the roadmap imports it, per `docs/README.md` rule 7. Archived reviews, outcome records, and the adaptation backlog are dated evidence, never task lists. An active round adds a spec and a plan document under the layout `docs/README.md` defines, and both retire to an archived outcome record when it finishes — so their absence means no round is running, not a missing file; a spec headed drafted merely awaits operator approval and starts nothing. |
| `.gitattributes` | Marks generated host trees for review tooling; it does not change their authority. |

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
  the checkout every other tier reads. Exit 3 means this host has drifted from what the
  repository ships; the usual repair is
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

For Copilot CLI, the equivalent local loop is `copilot plugin install .`. VS Code uses the
working-tree path in `chat.pluginLocations`. Codex loads `.codex/agents/` at project scope; its
nested plugin is installed through the repository marketplace. Generated `.claude/agents/`
profiles exercise Codex's official `/import` conversion contract, while
`scripts/install_codex_agents.py --target <agents-directory>` exercises repeatable standalone-agent
sync without touching the real user scope. `/import` is an initial migration and skips an existing
same-name Codex TOML; it is not an update mechanism. The synchronizer may adopt unmarked importer
output only when its parsed contract exactly matches the current generated agent. Any extra or
changed field remains an unmanaged conflict.

Three checks are manual and on demand, deliberately not CI gates (all drive real model sessions):

- `python3 scripts/probe_plugin.py` — proves the fleet *loads*, `${CLAUDE_PLUGIN_ROOT}` expands,
  and the guard fires for the guarded agents and only them. Re-run after upgrading the Claude
  Code CLI: the guard rests on the `agent_type` payload field — documented upstream since July
  2026, though its plugin-namespaced form is still only probe-verified — and the probe is what
  turns a silent upstream rename into a loud failure instead of a quietly disarmed guard.
  **CI's `plugin-contract` job pins the CLI version**, so bumping that pin is the upgrade — and the
  moment this probe is owed. The pin buys a deterministic gate; this probe is what keeps the pin
  from meaning the platform contract stopped being tested.
- `python3 scripts/eval_routing.py evals/routing/<cluster>.json --runs 3` — routing evals. Run
  before **and** after any description edit and diff the rates. Results are rates over runs, not
  booleans; a negative (near-miss) case firing at all is a defect regardless of variance. Agent
  positives systematically under-fire in headless mode — trust negatives and regressions over
  absolute agent rates. See `evals/README.md`.
- `python3 scripts/eval_behavioral.py --runs 3` — deterministic contract evals, using Claude by
  default. The Codex subscription lane is explicit and narrower:
  `--runtime codex --model <exact-slug> --reasoning-effort <effort>`. It projects the selected
  generated agent into a read-only, tool-reduced main session because `codex exec` has no
  `--agent` selector. Skill/tool-enabled cases and cases requiring a Claude permission mode are
  refused; a writer-role profile is eligible only when its contract declares `allowed_tools: []`.
  Codex 0.147.0 cannot expose every code-mode tool attempt or atomically attest managed MCP state,
  so this is same-host paired evidence with a no-MCP activation prerequisite, not Claude
  empty-allowlist parity. See `evals/README.md`.

One report is manual, on demand, and **offline** — no model session, no API cost:

```bash
python3 scripts/capability_graph.py --root . --emit graph.json --mermaid graph.mmd
```

Run it when reviewing fleet topology, or against two checkouts to compare a baseline with a
candidate — output is sorted, timestamp-free, LF, and repository-relative, so identical trees in
different directories emit identical bytes and the two documents diff cleanly. Generated output is
never committed. An agent declaring no `tools:` inherits every tool, so the report separates
declared grants from `tool_authority_undeclared`, withholds the host projections it cannot derive,
and marks itself INCOMPLETE rather than showing an empty grant. Read it with its three layers kept
apart: authored edges are what the
files declare, each host projection states only that host's control and its limitations, and the
routing overlay is co-membership plus separately identified case assertions — co-membership is not
behavioral coverage. Every section is advisory. Deliberately **not** a T0, CI, or PR gate: an
advisory that became a gate would make each topology observation a merge blocker.

The design validator is the other offline on-demand tool, and it takes one explicit document:

```bash
python3 scripts/workflow_contract.py path/to/design.json --root .
```

Exit 0 prints a `design_digest`; exit 1 lists ordered defects, each with a deterministic witness
(entry→stuck node, a cycle, an illegal zone edge, a wrong-kind binding, or an approval bypass path);
exit 2 means the input could not be read, which is not a design defect. Read the verdict as what it
says — **design-consistent, not runtime-enforced**. No host checks a workflow this way at dispatch,
so this is a reviewable property of the document, and approval coverage stops at every `subgraph`
boundary, which the summary lists as unverified interiors. Schema v1 is deliberately narrow: `all`
joins, acyclic graphs, all-path human approval, finite condition routes, and no embedded
expressions. `any`/quorum joins, late arrival, cancellation, and reset wait for GRAPH-004, because a
validator that guessed at those semantics would certify designs whose behavior nobody has defined.

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
active-agent identity used for scoping. Preserve the host-specific tool or sandbox controls instead.

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

**Closing a task that surfaced a discovery** — a platform fact, a recurring failure, a doc found
wrong, a routing miss — route it per `skills/self-improve-loop/references/discovery-routing.md`
before closing out: routed, filed as a gap, or dropped with a stated reason. Silence is not a
disposition.

## Opening a pull request

`.github/pull_request_template.md` is the shape. Three things about it are load-bearing:

- **Claim plus consequence.** Every line says what changed *and* what it means — "removed `ag`,
  whose exec-flag surface cannot be enumerated without the binary" rather than "removed `ag`". Same
  register as the comments in `scripts/` and the validator's error messages, for the same reason: a
  reviewer can only disagree with a decision they can see.
- **The conditional gates table is the part that catches things.** The expensive checks here are
  situational — a description edit owes a before/after routing run, a guard or hook edit owes the
  probe, a validator rule owes a test proven to fail without it, and a canonical fleet edit owes
  regenerated host adapters. Fill the rows you tripped.
- **The automated review is request-triggered, and opening a PR does not request it.** Every bot
  pass in this repository's history is preceded by a `review_requested` event, and the passes land
  roughly **ten minutes after that request** rather than after `gh pr create` — PR #124 was
  requested at 07:07:07 and reviewed at 07:17:28 and 07:17:44. Request Copilot explicitly; the
  Codex connector has followed that request without needing one of its own. Requesting is a step
  you take, not a wait you serve — **and on this repository it is an operator step, not an agent
  one**: the reviewer is `copilot-pull-request-reviewer[bot]`, which `suggestedActors` does not
  list, so `gh pr edit --add-reviewer Copilot` fails to resolve the login and a REST
  `requested_reviewers` post silently leaves `reviewRequests` empty. Use the PR page's Reviewers
  box. An agent opening a PR here must therefore hand the request to its operator and say so,
  rather than reporting the PR as awaiting review. Then wait for both passes **on the current
  head**, and
  disposition every comment — applied,
  or declined with the reason. Applying one writes new bytes, and the passes that cleared the
  previous head never saw them: the last review-driven edit owes another wait, or the gate is
  satisfiable by a review of code the fix already replaced. Four rounds paid for this line — a PR
  merged four minutes after opening carried a P1 that landed two minutes *after* the merge and cost
  a revert; a later PR's unread comments correctly refuted a claim that would otherwise have
  promoted an unsupported rule into this file; the head-binding clause exists because the first
  draft of this very rule shipped with that loophole in it; and the sentence you are reading
  replaced one asserting the reviews arrive "two to five minutes behind `gh pr create`", which read
  as a wait rather than an action and let PR #128 merge unreviewed while a session sat waiting for a
  pass nobody had asked for.

Keep the "Deliberately not done" section honest and keep the whole thing short; a template long
enough to skim past stops working, and each section in it was added for an observed failure.

## Hard rules with no playbook exceptions

- **Standard library only.** The validators, generators, installers, guard, hook, and tests use only
  the Python standard library. Do not add dependencies.
- **Generated adapters are not a second source.** Never hand-edit `.claude/agents/`,
  `.github/agents/`, `.codex/agents/`, `platforms/copilot/skills/`, or
  `plugins/sde-agents/skills/`. Change the
  canonical file or generator, regenerate, and let byte-drift validation prove the result.
- **Authority is host-specific.** Claude's guard, Copilot/VS Code's omission of `execute` from
  guarded roles, and Codex's `sandbox_mode` are distinct controls. Never replace one with
  compatible-looking prose or load the Claude hook on a host whose payload cannot scope it.
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
