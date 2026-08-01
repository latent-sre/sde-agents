# WF-001 Host-Workflow Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the fleet's first plugin workflow (`deep-review.js`) with schema-typed packet
contracts, extend the probe to cover the workflow platform contract, enforce the Claude-only
boundary, and revise GRAPH-001 to record the evidence — exactly the scope of
[`the WF-001 spec`](../specs/2026-08-01-wf-001-host-workflow-pilot-design.md).

**Architecture:** Everything lands *beside* the canonical definitions: a new `workflows/`
directory (auto-discovered at plugin root, no manifest field), two stdlib validator rules with
mutation tests, a probe section that reproduces the five verified probe runs, and doc edits
(GRAPH-001 revision, roadmap, docs map, AGENTS.md, README). No file under `agents/` or `skills/`
changes.

**Tech Stack:** Python 3 stdlib only (validator, probe, tests); ES2022 JavaScript (workflow
script, executed by the Claude Code workflow runtime, never by Node in this repo).

## Global Constraints

- Standard library only for all scripts and tests — no new dependencies.
- No edits to `agents/*.md` or `skills/*/SKILL.md` (spec: out of scope; CTX-001 owns prose).
- Markdown wraps at ~100 columns; comments explain *why*, matching the existing register.
- Evidence-label enum values are exactly `"verified"`, `"sourced"`, `"unverified"` — the packet
  stems `EVIDENCE_LABEL_STEMS` at `scripts/validate_fleet.py:248` are canonical.
- Plugin version becomes `1.5.0` in every manifest that carries `1.4.0` today:
  `plugin.json`, `.claude-plugin/plugin.json`, `plugins/sde-agents/.codex-plugin/plugin.json`.
- Probe and pilot sessions launch on **sonnet**; workflow probe sessions use
  `--permission-mode bypassPermissions` (spec: Test modes and model policy).
- Gate commands (run before every push): `py scripts/generate_platform_adapters.py --check`,
  `py scripts/validate_fleet.py`, `py -m unittest discover -s tests`,
  `claude plugin validate . --strict`. (CI uses `python3`; `py` is this machine's launcher.)
- Commits end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Revise GRAPH-001 and register the round in the docs map and roadmap

**Files:**
- Modify: `docs/decisions/2026-07-31-ai-graph-engineering.md`
- Modify: `docs/fleet-roadmap.md`
- Modify: `docs/README.md`

**Interfaces:**
- Produces: the decision-record language later tasks cite ("WF-001", "partially fired"); the
  roadmap item WF-001 whose Acceptance list mirrors the spec's Acceptance evidence.

- [ ] **Step 1: Apply the four spec-defined edits to the decision record**

Edit 1 — replace the "live host fact" bullet (currently the last bullet of the
"Claude 5-generation counterevidence" section, beginning "The host platform is converging on
owning deterministic orchestration natively"). New text:

```markdown
- The host platform now owns deterministic orchestration in a form a plugin can pin: plugin-shipped
  `workflows/` scripts are documented and GA (CLI v2.1.154, 2026-05-28), and were probe-verified on
  CLI 2.1.220 (2026-08-01): namespaced resolution (`/sde-agents:<name>`), `agentType` spawning of
  canonical fleet agents, PreToolUse delivery with plugin-namespaced `agent_type` inside
  workflow-spawned agents (the read-only guard denied a non-allowlisted command there, including
  under `bypassPermissions`), a distinct `workflow-subagent` identity for default workflow agents,
  and schema-validated returns with a five-retry ceiling (CHANGELOG v2.1.186). Pinnable is
  demonstrated; *stable* is not claimed — the feature is two months old with an active bugfix
  stream, resume does not survive session exit, and no first-party plugin ships one.
```

Edit 2 — in "Reopen triggers for the deferred execution phases", replace the second trigger
bullet ("Claude Code's native workflow/task orchestration stabilizes...") with:

```markdown
- ~~Claude Code's native workflow/task orchestration stabilizes into an API a plugin can pin to~~
  **Partially fired 2026-08-01** (see the probe-verified facts above): pinnable via the CLI pin
  plus probe, not yet mature. The authorized response is the bounded WF-001 host-layer pilot in
  the accepted work below — adopting the host layer, not the deferred repo-owned executor. The
  remaining maturity conditions (resume surviving sessions, first-party dogfooding, a stable
  documented hook contract for workflow agents) keep the rest of this trigger live.
```

Edit 3 — add a new accepted-work subsection after "### Accepted -- context-engineering
modernization (CTX-001)":

```markdown
### Accepted -- WF-001 host-workflow pilot (added 2026-08-01)

One bounded adoption of the host's native workflow layer, governed by the
[WF-001 round spec](../superpowers/specs/2026-08-01-wf-001-host-workflow-pilot-design.md):
a plugin-shipped `deep-review` workflow (parallel guarded reviewers with schema-typed packet
contracts and deterministic merge gates), a probe extension codifying the verified platform
contract, and the Claude-only platform boundary. The pilot does not write `run_state.py`; if the
deferred execution phases reopen, that spec decides integration — workflow scripts cannot touch
the filesystem, so integration would route authority through agent prose, which invariant #8
prohibits.
```

Edit 4 — in "### Accepted -- descriptive compiler and contract validator (former Phase 0)",
append one bullet to the existing list:

```markdown
- The derived graph's checks include, at minimum: components no other member references, routing
  edges no eval cluster covers, self-loops, hub-concentration reporting, and a reachability view
  of which prompt surfaces can reach which tools (the 2026-08-01 independent research round
  converged on the same check list from external evidence; see the WF-001 spec's research notes).
```

- [ ] **Step 2: Add the WF-001 item to `docs/fleet-roadmap.md` under `### Ready`** (before
SAFE-002, since it is the active round):

```markdown
#### WF-001 — host-workflow pilot round

**Status:** `active`

**Outcome:** The plugin ships one probe-covered workflow (`/sde-agents:deep-review`) whose packet
contracts are schema-typed and validator-pinned, with the Claude-only boundary enforced and the
GRAPH-001 record revised to carry the probe evidence.

**Source:** Revised [`graph decision`](decisions/2026-07-31-ai-graph-engineering.md) (trigger #2
partially fired) and the
[`WF-001 spec`](superpowers/specs/2026-08-01-wf-001-host-workflow-pilot-design.md).

**Prerequisites:** None — the spec is approved and the base branch carries the revised decision.

**Acceptance:** The spec's acceptance-evidence list: standard gates green, both new validator
rules proven by tests that fail without them, the extended probe green on CLI 2.1.220, and one
end-to-end pilot run on a real diff with session model and token cost recorded in the round's
outcome record.

**Next action:** Execute the paired plan
(`superpowers/plans/2026-08-01-wf-001-host-workflow-pilot.md`).
```

- [ ] **Step 3: Register the round documents in `docs/README.md`.** In the "Current documents"
table, insert two rows after the GRAPH-001 decision row:

```markdown
| [`superpowers/specs/2026-08-01-wf-001-host-workflow-pilot-design.md`](superpowers/specs/2026-08-01-wf-001-host-workflow-pilot-design.md) | Approved round spec | WF-001 scope and acceptance boundaries: the host-workflow pilot, its probe-verified platform facts, and what stays out of scope |
| [`superpowers/plans/2026-08-01-wf-001-host-workflow-pilot.md`](superpowers/plans/2026-08-01-wf-001-host-workflow-pilot.md) | Active round plan | WF-001 execution payloads; operational only while the round is active |
```

Also update the GRAPH-001 row's "Read it for" cell to end with: "revised 2026-08-01 with the
WF-001 probe evidence; trigger #2 partially fired".

- [ ] **Step 4: Run the doc-facing gates**

Run: `py scripts/validate_fleet.py`
Expected: `Validated 11 agents and 19 skills; inventory is current.` (exit 0 — the validator
checks tracked doc references and AGENTS.md paths; failures here mean a link target typo).

- [ ] **Step 5: Commit**

```bash
git add docs/decisions/2026-07-31-ai-graph-engineering.md docs/fleet-roadmap.md docs/README.md
git commit -m "docs: revise GRAPH-001 for WF-001 — trigger #2 partially fired, pilot accepted"
```

---

### Task 2: Ship the pilot workflow `workflows/deep-review.js`

**Files:**
- Create: `workflows/deep-review.js`

**Interfaces:**
- Produces: the workflow name `deep-review` (invoked `/sde-agents:deep-review`); the
  `EVIDENCE` enum `["verified", "sourced", "unverified"]` and `FINDING`/`PACKET` schema shapes
  that Task 4's validator rule parses; the returned object shape
  `{ verdict, confirmed_criticals, review, security, scope }`.

- [ ] **Step 1: Write the workflow script exactly as below**

```javascript
export const meta = {
  name: 'deep-review',
  description: 'Parallel review + security audit of the working diff, schema-typed packets, deterministic merge verdict',
  phases: [
    { title: 'Scope', detail: 'one agent enumerates the diff' },
    { title: 'Review', detail: 'code review and security audit in parallel' },
  ],
}

// The packet contracts mirror the agents' prose packets. The prose stays canonical
// (agents/code-reviewer.md, agents/application-security-auditor.md); the validator pins the
// evidence enum below to the canonical stems so schema and prose cannot drift silently.
// Schema constrains only the final packet — agents reason in free prose first (format-tax
// evidence in the WF-001 spec) — and validation retries at most 5 times before aborting.
const EVIDENCE = ['verified', 'sourced', 'unverified']
const FINDING = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    line: { type: 'integer' },
    claim: { type: 'string', description: 'one-sentence defect statement' },
    severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3'] },
    evidence: { type: 'string', enum: EVIDENCE },
    failure_scenario: { type: 'string', description: 'concrete inputs/state -> wrong outcome' },
  },
  required: ['file', 'claim', 'severity', 'evidence', 'failure_scenario'],
}
const PACKET = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: FINDING },
    verdict: { type: 'string', enum: ['merge', 'merge-with-fixes', 'do-not-merge'] },
    not_checked: { type: 'string', description: 'what this pass could not or did not examine' },
  },
  required: ['findings', 'verdict', 'not_checked'],
}
const SCOPE_SCHEMA = {
  type: 'object',
  properties: {
    base_ref: { type: 'string' },
    changed_files: { type: 'array', items: { type: 'string' } },
    diff_summary: { type: 'string', description: 'per-file one-line change summary' },
  },
  required: ['base_ref', 'changed_files', 'diff_summary'],
}

// Workflow scripts cannot run git themselves (no filesystem or process access), so a cheap
// default agent enumerates the diff; the reviewers then work a fixed file list instead of
// re-deriving scope two different ways.
phase('Scope')
const requestedRef = typeof args === 'string' && args.trim() ? args.trim() : null
const scope = await agent(
  'Enumerate the review scope. ' +
  (requestedRef
    ? `Diff the working tree against ${requestedRef}.`
    : 'Diff the working tree against the merge base with main (git merge-base HEAD main).') +
  ' Run git commands read-only. Report the resolved base ref, the changed file list, and a ' +
  'one-line-per-file summary of what changed. If the diff is empty, return an empty file list.',
  { label: 'scope', schema: SCOPE_SCHEMA },
)
if (!scope || scope.changed_files.length === 0) {
  return { verdict: 'no-diff', confirmed_criticals: 0, review: null, security: null, scope }
}

phase('Review')
const context =
  `Base ref: ${scope.base_ref}\nChanged files:\n- ${scope.changed_files.join('\n- ')}\n` +
  `Summary:\n${scope.diff_summary}\n` +
  'Work your normal checklist and reason in prose first; the schema constrains only your final packet. ' +
  'Label evidence honestly: verified only for what you ran or observed.'
const [review, security] = await parallel([
  () => agent(
    'Review this diff for correctness, safety, and convention adherence.\n' + context,
    { agentType: 'sde-agents:code-reviewer', label: 'review', schema: PACKET, phase: 'Review' },
  ),
  () => agent(
    'Audit this diff for security defects: source-to-sink reachability, authority changes, ' +
    'injection surfaces, secrets.\n' + context,
    { agentType: 'sde-agents:application-security-auditor', label: 'security', schema: PACKET, phase: 'Review' },
  ),
])

// Gates are code, not prose: a missing packet fails the run, and any P0/P1 forces the verdict
// down regardless of either agent's own verdict field.
if (!review || !security) {
  return { verdict: 'inconclusive-missing-packet', confirmed_criticals: 0, review, security, scope }
}
const criticals = [...review.findings, ...security.findings]
  .filter((f) => f.severity === 'P0' || f.severity === 'P1')
const worst = [review.verdict, security.verdict].includes('do-not-merge')
  ? 'do-not-merge'
  : [review.verdict, security.verdict].includes('merge-with-fixes')
    ? 'merge-with-fixes'
    : 'merge'
const verdict = criticals.length > 0 ? 'do-not-merge' : worst
return { verdict, confirmed_criticals: criticals.length, review, security, scope }
```

- [ ] **Step 2: Verify the plugin contract still validates**

Run: `claude plugin validate . --strict`
Expected: exit 0. (This is the only load-time check a workflow script gets; the runtime parses
`meta` at invocation. `workflows/` is auto-discovered — do NOT add a field to `plugin.json`.)

- [ ] **Step 3: Run the standard gates**

Run: `py scripts/validate_fleet.py && py scripts/generate_platform_adapters.py --check`
Expected: both exit 0 — the generator must not treat `workflows/` as adapter input; if `--check`
reports drift or extra files, stop: that is a generator assumption to fix in Task 3, not to
paper over.

- [ ] **Step 4: Commit**

```bash
git add workflows/deep-review.js
git commit -m "feat: ship deep-review pilot workflow with schema-typed packets"
```

---

### Task 3: Version bump and platform-boundary documentation

**Files:**
- Modify: `plugin.json` (version `1.4.0` -> `1.5.0`)
- Modify: `.claude-plugin/plugin.json` (same)
- Modify: `plugins/sde-agents/.codex-plugin/plugin.json` (same)
- Modify: `AGENTS.md` (Map table row)
- Modify: `README.md` (workflows note)

**Interfaces:**
- Produces: the AGENTS.md map row and README section Task 5's boundary rule message cites.

- [ ] **Step 1: Bump all three manifest versions to `1.5.0`.** Then confirm no other manifest
carries the old version:

Run: `grep -rn '"1.4.0"' --include='*.json' .`
Expected: no matches outside `docs/` or archives.

- [ ] **Step 2: Add the Map row to `AGENTS.md`** after the `hooks/copilot-hooks.json` row:

```markdown
| `workflows/*.js` | Claude-only plugin workflows (deterministic multi-agent pipelines). Auto-discovered at plugin root; **never** adapted to other hosts — Copilot, VS Code, and Codex have no workflow runtime, so a ported reference would read as available and fail silently. |
```

- [ ] **Step 3: Add a README section.** Place a short section after the guard section (locate the
heading that documents the read-only guard; insert the new `##`-level section immediately after
it):

```markdown
## Workflows (Claude-only)

`workflows/` ships deterministic multi-agent pipelines that only Claude Code executes
(`/sde-agents:deep-review`). The other hosts have no workflow runtime, so the generator ships
them nothing and the validator rejects any generated adapter that references a workflow — the
same omit-and-document convention as the Claude-only guard hook. Schema enums inside workflow
scripts are pinned to the canonical evidence stems by the fleet validator; edit the agent's
prose packet first and the schema second, never the reverse. Probe coverage:
`scripts/probe_plugin.py` verifies the workflow platform contract (namespaced resolution,
`agentType` spawns, guard delivery inside workflow-spawned agents) and is owed a re-run at every
CLI pin bump.
```

- [ ] **Step 4: Run the gates**

Run: `py scripts/validate_fleet.py && py scripts/generate_platform_adapters.py --check && py -m unittest discover -s tests`
Expected: all exit 0. The validator checks AGENTS.md's concrete repo paths — `workflows/*.js` is
a glob, but if it flags the row, use the literal path `workflows/deep-review.js` in the row
instead.

- [ ] **Step 5: Commit**

```bash
git add plugin.json .claude-plugin/plugin.json plugins/sde-agents/.codex-plugin/plugin.json AGENTS.md README.md
git commit -m "feat: bump plugin to 1.5.0 and document the Claude-only workflow boundary"
```

---

### Task 4: Validator rule — workflow evidence enums pin to the canonical stems

**Files:**
- Modify: `scripts/validate_fleet.py`
- Test: `tests/test_validate_fleet.py` (mutation test, per the AGENTS.md alternative for
  invariants about this repo's real wiring)

**Interfaces:**
- Consumes: `EVIDENCE_LABEL_STEMS` (`scripts/validate_fleet.py:248`), `read_text`, and the
  `issues.extend(...)` registration pattern used by `validate_bundle_references` in `main`.
- Produces: `validate_workflow_evidence_enums(root) -> list[str]`.

- [ ] **Step 1: Write the failing mutation test.** Follow the existing mutation-test pattern in
`tests/test_validate_fleet.py` (copy the repo to a temp dir, break one thing, assert the
validator reports it). Add:

```python
def test_workflow_evidence_enum_drift_is_rejected(self):
    root = self._copy_repo()
    wf = root / "workflows" / "deep-review.js"
    original = wf.read_text(encoding="utf-8")
    wf.write_text(
        original.replace(
            "const EVIDENCE = ['verified', 'sourced', 'unverified']",
            "const EVIDENCE = ['verified', 'cited', 'unverified']",
        ),
        encoding="utf-8",
    )
    issues = validate_fleet.validate_workflow_evidence_enums(root)
    self.assertTrue(any("canonical" in issue for issue in issues), issues)

def test_workflow_evidence_enum_current_tree_is_clean(self):
    issues = validate_fleet.validate_workflow_evidence_enums(validate_fleet_repo_root())
    self.assertEqual(issues, [])
```

Match the file's actual helper names for repo-copy and repo-root; if `_copy_repo` does not exist
under that name, use whatever the neighboring mutation tests use — the two tests above define the
required behavior, not the helper spelling.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `py -m unittest tests.test_validate_fleet -k workflow_evidence -v`
Expected: FAIL / ERROR with `validate_workflow_evidence_enums` not existing.

- [ ] **Step 3: Implement the rule in `scripts/validate_fleet.py`.** Near
`EVIDENCE_LABEL_STEMS`, add the derived enum; with the other validators, add the function:

```python
# The workflow packet schemas carry the same evidence triad as the agents' prose packets, as a
# bare enum. If either side drifts, nothing errors at load time -- the mismatch surfaces as a
# schema-validation failure five retries deep inside a live workflow run, billed and late. Pin
# the enum to the canonical stems so the drift is a validation failure at commit time instead.
WORKFLOW_EVIDENCE_ENUM = tuple(
    stem.split("[", 1)[1].split("]", 1)[0] for stem in EVIDENCE_LABEL_STEMS
)  # ("verified", "sourced", "unverified"), derived so the triad has exactly one authoring point
WORKFLOW_EVIDENCE_ENUM_RE = re.compile(
    r"const\s+EVIDENCE\s*=\s*\[([^\]]*)\]"
)


def validate_workflow_evidence_enums(root: Path) -> list[str]:
    """Every workflow script that declares an EVIDENCE enum must match the canonical triad."""
    issues: list[str] = []
    workflows_dir = root / "workflows"
    if not workflows_dir.is_dir():
        return issues
    for path in sorted(workflows_dir.glob("*.js")):
        text = read_text(path)
        matches = WORKFLOW_EVIDENCE_ENUM_RE.findall(text)
        if "evidence" in text and not matches:
            issues.append(
                f"{path}: declares an evidence field without a parseable `const EVIDENCE = [...]` "
                f"enum, so the canonical triad cannot be pinned and drift would be invisible "
                f"until a live run fails schema validation."
            )
        for group in matches:
            values = tuple(v.strip().strip("'\"") for v in group.split(",") if v.strip())
            if values != WORKFLOW_EVIDENCE_ENUM:
                issues.append(
                    f"{path}: workflow evidence enum {values!r} does not match the canonical "
                    f"triad {WORKFLOW_EVIDENCE_ENUM!r} from EVIDENCE_LABEL_STEMS; a drifted enum "
                    f"ships a packet contract that fails five retries deep with no load-time error."
                )
    return issues
```

Register it in `main` alongside the other repo-level validators:
`issues.extend(validate_workflow_evidence_enums(root))`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `py -m unittest tests.test_validate_fleet -k workflow_evidence -v`
Expected: PASS (both tests).

- [ ] **Step 5: Run the full gates and commit**

Run: `py scripts/validate_fleet.py && py -m unittest discover -s tests`
Expected: exit 0, all tests pass.

```bash
git add scripts/validate_fleet.py tests/test_validate_fleet.py
git commit -m "feat: pin workflow evidence enums to the canonical packet stems"
```

---

### Task 5: Validator rule — generated adapters must not reference workflows

**Files:**
- Modify: `scripts/validate_fleet.py`
- Test: `tests/test_validate_fleet.py`

**Interfaces:**
- Consumes: `read_text`; the generated-tree paths from the AGENTS.md map
  (`.github/agents`, `.codex/agents`, `platforms/copilot/skills`, `plugins/sde-agents/skills`).
- Produces: `validate_workflow_host_boundary(root) -> list[str]`.

- [ ] **Step 1: Write the failing mutation test**

```python
def test_adapter_referencing_workflow_is_rejected(self):
    root = self._copy_repo()
    adapter = next((root / ".github" / "agents").glob("*.md"))
    adapter.write_text(
        adapter.read_text(encoding="utf-8")
        + "\nRun /sde-agents:deep-review before merging.\n",
        encoding="utf-8",
    )
    issues = validate_fleet.validate_workflow_host_boundary(root)
    self.assertTrue(any("workflow" in issue.lower() for issue in issues), issues)

def test_workflow_host_boundary_current_tree_is_clean(self):
    issues = validate_fleet.validate_workflow_host_boundary(validate_fleet_repo_root())
    self.assertEqual(issues, [])
```

- [ ] **Step 2: Run to verify failure**

Run: `py -m unittest tests.test_validate_fleet -k host_boundary -v`
Expected: FAIL / ERROR — function does not exist.

- [ ] **Step 3: Implement**

```python
# Workflows are Claude-only: the other hosts have no workflow runtime, so a generated adapter
# that mentions one teaches an instruction that cannot execute there -- it reads as configured
# and fails silently, the exact failure class the bare-skill-reference rule already catches for
# skills. Match both the invocation form and the directory form.
GENERATED_ADAPTER_TREES = (
    ".github/agents",
    ".codex/agents",
    "platforms/copilot/skills",
    "plugins/sde-agents/skills",
)


def validate_workflow_host_boundary(root: Path) -> list[str]:
    """No generated non-Claude adapter may reference a plugin workflow."""
    issues: list[str] = []
    workflow_names = set()
    workflows_dir = root / "workflows"
    if workflows_dir.is_dir():
        workflow_names = {p.stem for p in workflows_dir.glob("*.js")}
    if not workflow_names:
        return issues
    for tree in GENERATED_ADAPTER_TREES:
        base = root / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in {".md", ".json", ".toml", ".yaml", ".yml"}:
                continue
            text = read_text(path)
            for name in sorted(workflow_names):
                if f"/sde-agents:{name}" in text or f"workflows/{name}" in text:
                    issues.append(
                        f"{path}: generated non-Claude adapter references the Claude-only "
                        f"workflow {name!r}; that host has no workflow runtime, so the "
                        f"instruction reads as available and fails silently at use time."
                    )
    return issues
```

Register in `main`: `issues.extend(validate_workflow_host_boundary(root))`.

- [ ] **Step 4: Run to verify pass, then full gates**

Run: `py -m unittest tests.test_validate_fleet -k host_boundary -v`
Expected: PASS.
Run: `py scripts/validate_fleet.py && py -m unittest discover -s tests && py scripts/generate_platform_adapters.py --check`
Expected: all exit 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/validate_fleet.py tests/test_validate_fleet.py
git commit -m "feat: reject generated adapters that reference Claude-only workflows"
```

---

### Task 6: Probe extension — the workflow platform contract

**Files:**
- Modify: `scripts/probe_plugin.py`

**Interfaces:**
- Consumes: `Probe`, `run`, `REPO`, `CLAUDE`, and the workspace conventions in `main`
  (`REPO / ".probe-tmp"`).
- Produces: `probe_workflow_contract(probe) -> None`, called from `main` after the existing
  checks.

- [ ] **Step 1: Add the workflow probe.** Design notes the code must honor (each maps to a
verified probe run from 2026-08-01): the shipped plugin stays clean, so the probe copies the repo
tree to `.probe-tmp/plugin`, instruments the *copy's* `hooks/hooks.json` with a payload logger
(prepended, guard logic retained), and adds a probe-only workflow there; `agent_type` delivery is
asserted from the hook log, never from agent prose (agents sometimes decline probes
cooperatively — the log is the deterministic oracle); the session runs
`--permission-mode bypassPermissions` because the interactive workflow-review gate blocks plain
`-p` sessions; the target repo needs at least one commit (the reviewer's git commands otherwise
exit 128 and add noise).

```python
PROBE_WORKFLOW = """export const meta = {
  name: 'probe-workflow',
  description: 'Probe: guard delivery and agentType resolution inside plugin workflows',
  phases: [{ title: 'Probe' }],
}
phase('Probe')
const SCHEMA = {
  type: 'object',
  properties: { outcome: { type: 'string' } },
  required: ['outcome'],
}
const PROMPT = 'Run exactly one Bash command: `cat README.md`. Report its verbatim output.'
const guarded = await agent(PROMPT, { agentType: 'sde-agents:code-reviewer', schema: SCHEMA, label: 'guarded' })
const unguarded = await agent(PROMPT, { schema: SCHEMA, label: 'unguarded' })
return { guarded, unguarded }
"""


def probe_workflow_contract(probe: "Probe") -> None:
    """The workflow platform contract: namespaced resolution, agentType spawns, and PreToolUse
    delivery with plugin-namespaced agent_type inside workflow-spawned agents.

    The oracle is the instrumented hook's payload log. Agent prose can claim anything, and the
    guarded agents sometimes decline probe commands cooperatively before Bash fires -- the log
    line either exists with the right agent_type or the contract is broken.
    """
    print("\n== the workflow platform contract ==")
    workspace = REPO / ".probe-tmp"
    plugin_copy = workspace / "plugin"
    shutil.copytree(
        REPO, plugin_copy,
        ignore=shutil.ignore_patterns(".git", ".probe-tmp", "node_modules"),
    )
    hook_log = workspace / "hook-log.jsonl"
    hooks_path = plugin_copy / "hooks" / "hooks.json"
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    entry = hooks["hooks"]["PreToolUse"][0]["hooks"][0]
    log_posix = hook_log.as_posix()
    if log_posix[1] == ":":  # C:/... -> /c/... for the sh hook on Windows
        log_posix = "/" + log_posix[0].lower() + log_posix[2:]
    entry["command"] = (
        f"IN=$(cat); printf '%s\\n' \"$IN\" >> '{log_posix}'; " + entry["command"][len("IN=$(cat); "):]
    )
    hooks_path.write_text(json.dumps(hooks, indent=2), encoding="utf-8")
    (plugin_copy / "workflows" / "probe-workflow.js").write_text(PROBE_WORKFLOW, encoding="utf-8")

    target = workspace / "workflow-target"
    target.mkdir(parents=True)
    (target / "README.md").write_text("workflow probe target\n", encoding="utf-8")
    run(["git", "init", "-q", str(target)])
    run(["git", "-C", str(target), "add", "-A"])
    run(["git", "-C", str(target), "commit", "-qm", "probe baseline"])

    session = run(
        [
            CLAUDE, "-p",
            "Invoke the workflow /sde-agents:probe-workflow now and report its returned JSON "
            "verbatim. Do not use the Agent tool yourself; only the Workflow tool.",
            "--plugin-dir", str(plugin_copy),
            "--output-format", "stream-json",
            "--verbose",
            "--permission-mode", "bypassPermissions",
            "--model", "sonnet",
        ],
        cwd=str(target),
    )
    text = session.stdout or ""
    probe.check(
        PASS if "probe-workflow" in text and session.returncode == 0 else FAIL,
        "plugin workflow resolved and the session completed",
        (session.stderr or "")[:300],
    )
    events = []
    if hook_log.exists():
        for line in hook_log.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    guarded_hits = [e for e in events if e.get("agent_type") == "sde-agents:code-reviewer"]
    default_hits = [e for e in events if e.get("agent_type") == "workflow-subagent"]
    probe.check(
        PASS if guarded_hits else FAIL,
        "PreToolUse fired inside the workflow-spawned guarded agent with namespaced agent_type",
        "no hook payload carried agent_type 'sde-agents:code-reviewer' -- the guard is "
        "undeliverable inside workflows and every guarded agent there is silently unguarded",
    )
    probe.check(
        PASS if default_hits else FAIL,
        "default workflow agents carry the 'workflow-subagent' identity",
        "the identity string changed upstream; re-verify guard scoping assumptions before "
        "trusting workflows with guarded agents",
    )
```

Call it from `main` after the existing session checks, before the final `probe.report()`:
`probe_workflow_contract(probe)`. Reuse the existing `.probe-tmp` cleanup (`shutil.rmtree` at
start of `main` already clears the workspace; confirm the end-of-run cleanup also removes it).

- [ ] **Step 2: Run the probe once to prove the section green**

Run: `py scripts/probe_plugin.py`
Expected: all existing checks PASS plus the three new workflow checks PASS. This drives real
sonnet sessions — it is the round's probe gate, not a CI job.

- [ ] **Step 3: Commit**

```bash
git add scripts/probe_plugin.py
git commit -m "feat: probe the workflow platform contract — resolution, agentType, guard delivery"
```

---

### Task 7: Pilot acceptance run and round wrap-up

**Files:**
- Create: `docs/archive/2026-08/wf-001-pilot-run-2026-08.md` (evidence note; the full outcome
  record retires the round docs later, when the round closes)

**Interfaces:**
- Consumes: `/sde-agents:deep-review` from Task 2.

- [ ] **Step 1: Run the pilot on a real diff.** From a **sonnet** session on this branch (the
round's own commits are the diff):

In an interactive `claude --plugin-dir .` session started with `--model sonnet`, invoke:
`/sde-agents:deep-review main`
Approve the workflow when prompted (interactive approval is the expected path outside probes).

- [ ] **Step 2: Record the evidence note** with, verbatim from the run: the session model, total
tokens (from `/workflows` or the final usage line), wall time, the returned verdict object, and
whether any schema retry fired (visible as repeated StructuredOutput calls in the workflow's
transcript dir). Note explicitly if retries fired: per the spec, that means the schema is too
strict or the packet prompt too loose — say which and file it for the outcome record.

- [ ] **Step 3: Run every gate one final time**

Run: `py scripts/generate_platform_adapters.py --check && py scripts/validate_fleet.py && py -m unittest discover -s tests && claude plugin validate . --strict`
Expected: all exit 0.

- [ ] **Step 4: Commit and open the PR**

```bash
git add docs/archive/2026-08/wf-001-pilot-run-2026-08.md
git commit -m "docs: record WF-001 pilot run evidence"
```

PR per `.github/pull_request_template.md`. Conditional gates table rows this round trips:
canonical fleet edit -> **no** (no agents/skills touched; adapters unchanged by design);
guard/hook edit -> **yes, probe run** (Task 6's probe output); validator rule -> **yes, tests
proven to fail without it** (Tasks 4-5); description edit -> **no** (no routing evals owed).
"Deliberately not done": no second workflow, no run_state integration, no fleet-graph tooling
(deferred to the descriptive-layer item), no agent/skill edits.

---

## Self-review notes (spec coverage)

- Spec D1 (GRAPH-001 revision) -> Task 1. D2 (pilot workflow) -> Task 2. D3 (schemas +
  drift rule) -> Tasks 2 and 4. D4 (probe extension) -> Task 6. D5 (platform boundary) -> Tasks
  3 and 5. D6 (roadmap) -> Task 1. Test modes and model policy -> Global Constraints, Tasks 6-7.
  Acceptance evidence -> Tasks 4-7.
- Helper-name caveat: Task 4/5 tests reference `_copy_repo` / `validate_fleet_repo_root` as
  *behavioral* placeholders for whatever the existing mutation tests in
  `tests/test_validate_fleet.py` actually use — the implementer copies the neighboring pattern.
  This is the one place the plan defers to the file because inventing names the file doesn't
  have would be worse.
- The probe's Windows path translation (`C:/` -> `/c/`) mirrors what the hook's `sh` runtime
  needs on this machine; on POSIX the branch is a no-op.
