# SDE Agents

A focused fleet of software-engineering and home-lab agents plus reusable skills. The definitions in
`agents/` and `skills/` are the canonical source; generated adapters and documentation must derive from
them rather than becoming a second source of truth.

## Fleet

<!-- fleet-inventory:start -->
- **Agents (7):** `code-reviewer`, `distinguished-architect`, `homelab-platform`, `multi-agent-architect`, `principal-engineer`, `prompt-engineer`, `sde-fullstack`
- **Skills (9):** `backend-craft`, `eng-ladder`, `frontend-craft`, `lab-audit`, `prompt-craft`, `root-cause`, `runbook`, `service-onboard`, `sre-tool`
<!-- fleet-inventory:end -->

Refresh the generated block after adding, renaming, or removing an agent or skill:

```bash
python3 scripts/validate_fleet.py --write-inventory
```

## Project context convention

Agents should use the target repository's existing project-instruction file. `AGENTS.md` is the portable
default; if a repository already uses an equivalent such as `CLAUDE.md`, respect it instead of creating a
competing file. Record the environment card and mission block there.

Long-running work should use the progress file declared by that project context. When none is declared,
use `.agents/PROGRESS.md`. Progress files are coordination state, not a substitute for the final review
packet or committed documentation.

## Validation

```bash
python3 scripts/validate_fleet.py
python3 -m unittest discover -s tests -v
```

The validator checks frontmatter, names, descriptions, explicit agent tool authority (against a known
tool vocabulary), models, bundled skill references, the canonical evidence-label phrasing, the required
end-of-task packet heading, and README inventory drift. It is intentionally runtime-neutral and uses
only the Python standard library.
