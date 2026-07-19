# Repository guide for coding agents

This repository is a Claude Code **plugin**: the definitions in `agents/` and `skills/` at the root
are both the canonical source and exactly what Claude Code loads. There is no generated copy and no
second source of truth — edit those files directly, and never resolve a fleet file under
`~/.claude`, which does not contain this fleet once it ships as a plugin.

This file is the fleet's own instance of the project context convention that `README.md` defines
for target repositories. Where it paraphrases the README or a script's docstring, that source wins
on conflict — fix the paraphrase here, never the source.

## Map

| Path | What it is |
|---|---|
| `agents/*.md` | The subagent definitions, loaded as-is. Filename must equal `name:`. |
| `skills/<name>/SKILL.md` | The skills; `references/` (predicate-keyed deep dives) and `assets/` (templates) sit beside each. |
| `hooks/hooks.json` | The **only** place a guard can attach — plugin agents cannot carry `hooks:`. |
| `scripts/readonly-guard.py` | Allowlist guard for read-only agents that hold `Bash`. Read its docstring before touching it. |
| `scripts/validate_fleet.py` | Fleet-policy validator; every rule is a tripwire for a failure that is silent at runtime. |
| `scripts/probe_plugin.py` | Behavioral probe against a real headless session. |
| `scripts/eval_routing.py` | Routing-eval runner over `evals/routing/*.json`; read `evals/README.md` first. |
| `tests/` | Stdlib unittest suite. `tests/fixtures/` holds minimal repos that each violate exactly one rule. |
| `docs/` | Working documents — the quality review and the skills modernization plan; pending work lives there. |
| `.claude-plugin/` | Plugin and marketplace manifests. The manifest `name` is the namespace; the guard cross-checks it. |

## Validate before you push

CI (`.github/workflows/validate.yml`) runs the first two commands on Linux, macOS, and Windows, and
the plugin contract check on Linux:

```bash
python3 scripts/validate_fleet.py          # fleet rules — offline, stdlib only
python3 -m unittest discover -s tests -v   # unit tests — offline, stdlib only
claude plugin validate . --strict          # platform contract: manifest, frontmatter, hook JSON
```

After adding, renaming, or removing an agent or skill, refresh the generated README inventory or
the validator fails on drift:

```bash
python3 scripts/validate_fleet.py --write-inventory
```

## Development loop

Load the plugin from the working tree — `/plugin install` runs from a cached copy, which is the
wrong loop when the plugin is what you are editing:

```bash
claude --plugin-dir .
```

Two checks are manual and on demand, deliberately not CI gates (both drive real API sessions):

- `python3 scripts/probe_plugin.py` — proves the fleet *loads*, `${CLAUDE_PLUGIN_ROOT}` expands,
  and the guard fires for the reviewer and only the reviewer. Re-run after upgrading the Claude
  Code CLI: the guard rests on the undocumented `agent_type` payload field, and the probe is what
  turns a silent upstream rename into a loud failure instead of a quietly disarmed guard.
- `python3 scripts/eval_routing.py evals/routing/<cluster>.json --runs 3` — routing evals. Run
  before **and** after any description edit and diff the rates. Results are rates over runs, not
  booleans; a negative (near-miss) case firing at all is a defect regardless of variance. Agent
  positives systematically under-fire in headless mode — trust negatives and regressions over
  absolute agent rates. See `evals/README.md`.

## Change playbooks

**Any edit** — run the validator and the tests. If you touched text that paraphrases another file,
find the declared owner and fix in the right direction (see "Owned conventions" below).

**Editing a description** (agent or skill) — descriptions drive routing. Run the overlapping
cluster in `evals/routing/` before and after, and diff the rates. Cross-references to other fleet
members must use the plugin namespace (`sde-agents:code-reviewer`, `/sde-agents:backend-craft`);
a bare backticked name is only for content already in context, such as a preloaded skill.

**Adding an agent** — the checklist the validator will hold you to:

- kebab-case `name:` equal to the filename; description ≤ 1024 chars, with trigger phrasings and
  negative routing ("Not for X — use `sde-agents:Y`").
- An explicit `tools:` list. Omitting it is not a harmless default — the agent **inherits every
  tool**. No parenthesized specifiers: `Bash(git diff:*)` and `Agent(worker)` are silently ignored
  by the runtime while reading as limits, so the validator rejects them. New tools outside the
  fleet's adopted set must be added to `FLEET_TOOLS` deliberately — every entry is authority.
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
- Refresh the README inventory; seed or extend a routing cluster if the remit overlaps an existing
  member (overlap is fine — unmeasured overlap is not).

**Adding a skill** — directory name equals `name:`; every path a SKILL.md mentions under
`references/`, `assets/`, or `scripts/` must exist, and every file under `references/` must be
linked from SKILL.md by a **skill-relative** path (an unlinked reference file is dead knowledge
that looks shipped — the orphan check fails it). A skill with side effects sets
`disable-model-invocation: true`, which also removes it from `Skill`-tool reach and from agent
preloading — route to it via a slash command or an agent that works its checklist.

**Touching the guard or hook** — read the docstrings in `scripts/readonly-guard.py` and the README
guard section first; then run the tests *and* the probe. Non-negotiables: the allowlist grows by
adding a *reader*, never an interpreter (no `python`, `pytest`, `npm`, `make`, no exemption for
this repo's own scripts); the hook resolves the guard through `${CLAUDE_PLUGIN_ROOT}` so a
repository under review can never supply it; it fails closed for guarded agents and no-ops for
everyone else; and the 42/43 exit-code contract between guard and hook shell string stays intact —
it is how the hook tells the guard's answer from a stand-in interpreter that merely exits 0.

**Changing validator behavior** — add a fixture under `tests/fixtures/` that violates exactly the
rule you are adding, plus a test that fails without your change. Match the existing error-message
register: each message says what broke *and why it would have failed silently*.

## Hard rules with no playbook exceptions

- **Standard library only.** The validator, guard, hook, and tests use only the Python standard
  library. Do not add dependencies.
- **Plugin agents cannot carry `hooks:`, `mcpServers:`, or `permissionMode:`.** Claude Code
  silently ignores those keys on plugin-shipped agents, so a guard declared there would look like
  armor and be nothing. Unknown frontmatter keys fail validation for the same reason: a typo does
  not error at load time, it silently drops what it was meant to configure.
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
