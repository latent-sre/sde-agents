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
| `scripts/validate_fleet.py` | Fleet-policy validator; every rule is a tripwire for a failure that is silent at runtime. |
| `scripts/run_tests.py` | Parallel test runner — one process per module, exactly the discovery invocation T0 uses. |
| `scripts/probe_plugin.py` | Behavioral probe against a real headless session. |
| `scripts/eval_routing.py` | Routing-eval runner over `evals/routing/*.json`; read `evals/README.md` first. |
| `scripts/eval_baseline.py` | Offline resolver from current bytes to a still-valid stored routing benchmark; it answers whether a paired run's 'before' side is already on disk before any API money is spent. |
| `scripts/eval_behavioral.py` | Behavioral-contract runner over `evals/behavioral/contracts.json`; it binds exact source, frozen plugin execution bytes, evaluator/grader, runtime, concurrency, and non-secret auth-mode provenance. |
| `scripts/learning_ledger.py`, `learning/` | Fail-closed repository-local intake for evidence-bound learning candidates. It records applicability-bound recurrence, lifecycle decisions, and bounded review renewal; it never edits or approves a destination. |
| `tests/` | Stdlib unittest suite. `tests/fixtures/` holds minimal repos that each violate exactly one rule. |
| `docs/` | The roadmap, decision records, and `archive/`. `docs/fleet-roadmap.md` is the only file that tracks unfinished or deferred work; `docs/README.md` maps authority. GitHub issues are evidence-bound intake, not a second tracker — an issue adds work only when the roadmap imports it, per `docs/README.md` rule 7. Archived reviews, outcome records, and the adaptation backlog are dated evidence, never task lists. An active round adds a spec and a plan document under the layout `docs/README.md` defines, and both retire to an archived outcome record when it finishes — so their absence means no round is running, not a missing file. |
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
  Linux.
- **T2 — merge and weekly** (CI-owned): pushes to main, the Monday sweep, and manual dispatch
  run the full Linux/macOS/Windows matrix, so platform-specific guard and hook paths are
  exercised without billing every PR for them (see the matrix comment in
  `.github/workflows/validate.yml`).
- **T3 — release / CLI pin bump** (manual, real API): `scripts/probe_plugin.py` and the eval
  suites, per the section below. Before a paired routing run, `scripts/eval_baseline.py`
  reports whether a stored benchmark already covers the 'before' side — reuse it when it does;
  the 'after' side is always fresh.

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

Two checks are manual and on demand, deliberately not CI gates (both drive real API sessions):

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
branch is there.

**Closing a task that surfaced a discovery** — a platform fact, a recurring failure, a doc found
wrong, a routing miss — route it per `skills/self-improve-loop/references/discovery-routing.md`
before closing out: routed, filed as a gap, or dropped with a stated reason. Silence is not a
disposition.

## Opening a pull request

`.github/pull_request_template.md` is the shape. Two things about it are load-bearing:

- **Claim plus consequence.** Every line says what changed *and* what it means — "removed `ag`,
  whose exec-flag surface cannot be enumerated without the binary" rather than "removed `ag`". Same
  register as the comments in `scripts/` and the validator's error messages, for the same reason: a
  reviewer can only disagree with a decision they can see.
- **The conditional gates table is the part that catches things.** The expensive checks here are
  situational — a description edit owes a before/after routing run, a guard or hook edit owes the
  probe, a validator rule owes a test proven to fail without it, and a canonical fleet edit owes
  regenerated host adapters. Fill the rows you tripped.

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

- Markdown prose wraps at roughly 100 columns, matching the existing files.
- Agent and skill names are kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`).
- Comments in the scripts explain *why* an invariant exists, not what the next line does — match
  that register when editing them. Descriptions lead with capability, then triggers, then negative
  routing.
