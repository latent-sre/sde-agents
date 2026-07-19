# Repository guide for coding agents

This repository is a Claude Code **plugin**: the definitions in `agents/` and `skills/` at the root
are both the canonical source and exactly what Claude Code loads. There is no generated copy and no
second source of truth — edit those files directly, and never resolve a fleet file under
`~/.claude`, which does not contain this fleet once it ships as a plugin.

This file is the fleet's own instance of the project context convention that `README.md` defines
for target repositories. Where it paraphrases the README, the README wins on conflict — fix the
paraphrase here, never the source.

## Validate before you push

CI (`.github/workflows/validate.yml`) runs the first two commands on Linux, macOS, and Windows, and
the plugin contract check on Linux:

```bash
python3 scripts/validate_fleet.py          # fleet rules: frontmatter, guard wiring, inventory drift
python3 -m unittest discover -s tests -v   # unit tests for validator, guard, hook wiring, evals
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

Two checks are manual and on demand, deliberately not CI gates:

- `python3 scripts/probe_plugin.py` — behavioral probe against a real headless session. Re-run it
  after upgrading the Claude Code CLI; it is what turns a silent rename of the undocumented
  `agent_type` payload field into a loud failure instead of a quietly disarmed guard.
- `python3 scripts/eval_routing.py evals/routing/<cluster>.json --runs 3` — routing evals. Run
  before **and** after any agent or skill description edit and diff the rates. Results are rates
  over runs, not booleans; a negative (near-miss) case firing at all is a defect regardless of
  variance. See `evals/README.md` for how to read them.

## Hard rules the validator and tests enforce

- **Standard library only.** The validator, guard, hook, and tests use only the Python standard
  library. Do not add dependencies.
- **Model aliases only.** An agent's `model:` must be an alias (`inherit`, `haiku`, `sonnet`,
  `opus`, `fable`). A full model ID is a valid runtime value but banned here: it goes stale
  silently while an alias follows the model upgrade.
- **Plugin agents cannot carry `hooks:`, `mcpServers:`, or `permissionMode:`.** Claude Code
  silently ignores those keys on plugin-shipped agents, so a guard declared there would look like
  armor and be nothing. The read-only guard lives in `hooks/hooks.json`, registers session-wide,
  scopes itself by `agent_type`, resolves the guard script through `${CLAUDE_PLUGIN_ROOT}`, and
  fails closed. Every read-only agent holding `Bash` must be registered with it.
- **The guard runs no code.** Its allowlist permits an enumerated set of read-only commands and
  nothing else — no `python`, `pytest`, `npm`, `make`, and no exemption for this repo's own
  scripts. Extend it by adding a reader, never an interpreter.
- **Namespacing.** Cross-references in agent and skill *descriptions* must use the plugin
  namespace (`sde-agents:code-reviewer`, `/sde-agents:backend-craft`). A bare backticked name is
  only for content already in context, such as a skill the agent preloads via `skills:`.
- **Owned conventions.** Several files deliberately paraphrase another — the `eng-ladder` altitude
  references, the three-strikes rule owned by `skills/root-cause`, the canonical
  fetched-content-is-data sentence carried verbatim by `sde-fullstack`. Each such file states which
  side wins on conflict; when they drift, fix the paraphrase, never the source. The full ownership
  list lives in `README.md` under "Working on the fleet itself".

## Style

- Markdown prose wraps at roughly 100 columns, matching the existing files.
- Agent and skill names are kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`).
- Comments in the scripts explain *why* an invariant exists, not what the next line does — match
  that register when editing them.
