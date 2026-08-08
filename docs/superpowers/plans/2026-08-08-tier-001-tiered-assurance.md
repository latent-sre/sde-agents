# TIER-001 Tiered Assurance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the four approved TIER-001 mechanisms — adapter-check de-duplication in the
wiring tests, the offline baseline resolver, the tiered validation recipe, and the CI durations
tripwire — with measured before/after evidence and no weakened control.

**Architecture:** One new keyword parameter on `validate_repo` removes the dominant recomputation
from `tests/test_validate_fleet.py`; one new stdlib script `scripts/eval_baseline.py` imports
`eval_routing`'s own provenance functions (never reimplements them) to map current bytes to a
still-valid stored benchmark; AGENTS.md and README.md get the tier map; `validate.yml` gains
`--durations 10`.

**Tech Stack:** Python 3.12 standard library only. No new dependencies (hard rule).

**Spec:** `docs/superpowers/specs/tier-001-tiered-assurance.md` (approved 2026-08-08, freshness
policy = the recommended default).

## Global Constraints

- Standard library only; no new dependencies anywhere.
- Surgical diffs: no reformatting of adjacent code; prose wraps at ~100 columns.
- Comments explain *why* an invariant exists; error/output messages say what diverged and why it
  matters — match the register of existing validator messages.
- No canonical agent or skill file changes → no adapter regeneration owed; no `description:`
  edits → no routing evals owed; no guard/hook changes → no probe owed.
- `.github/workflows/validate.yml` must stay LF (the validator's workflow line-ending check
  enforces it).
- Measurement discipline (ledger lesson `lc_4c0abc58`): every acceptance run captures full output
  to a file, reports the tested process's own exit status, and quotes the summary line from the
  file — never through a pipe, never chained.
- Branch: `tier-001/tiered-assurance` off current `main` (28a3838). Commit per task. The
  "before" number for the suite is already captured: **130.6 s** (full discover run, this
  machine, 2026-08-08).

---

### Task 0: Round bookkeeping — branch, spec status, roadmap entry

**Files:**
- Modify: `docs/superpowers/specs/tier-001-tiered-assurance.md` (status line + policy block note)
- Modify: `docs/fleet-roadmap.md` (add TIER-001 under Current work / Ready→Active)

**Interfaces:** Produces the governing docs later tasks cite; no code.

- [ ] **Step 1: Create the branch**

```bash
git checkout -b tier-001/tiered-assurance
```

- [ ] **Step 2: Flip the spec status line**

Replace the spec's status paragraph with:

```markdown
**Status: approved** — drafted 2026-08-08, approved by the operator the same day with the
recommended freshness-policy default. This spec governs the round's scope and acceptance; the
paired plan is `docs/superpowers/plans/2026-08-08-tier-001-tiered-assurance.md`.
```

In the freshness-policy section, replace the sentence introducing the fenced block
("The operator may tighten `cli_version` to exact instead:") with:

```markdown
Approved 2026-08-08 as recommended; the block below is now the policy the resolver implements:
```

- [ ] **Step 3: Add the roadmap item** (under `### Ready`, alphabetically it lands after
  SAFE-003; status `active` since this plan is executing)

```markdown
#### TIER-001 — tiered assurance and evidence reuse for the fleet's own gates

**Status:** `active` — spec approved 2026-08-08; the paired plan is executing.

**Outcome:** The wiring-test suite stops recomputing adapter byte-drift under every mutation
test (measured before/after wall time in the round PR); `scripts/eval_baseline.py` resolves
whether a stored routing benchmark still covers the 'before' side of a paired run, offline;
AGENTS.md and README.md state the T0–T3 validation tiers; CI prints per-test durations.

**Source:** [`TIER-001 spec`](superpowers/specs/tier-001-tiered-assurance.md); measurements in
the spec's Problem table (2026-08-08, commit 28a3838).

**Prerequisites:** None. PR #88's CI posture is consumed, not changed.

**Acceptance:** The spec's acceptance list — measured suite time, detector spot-proofs,
resolver unit tests over synthetic benchmarks, recipe/source consistency.

**Next action:** Merge the round PR; retire this item to an outcome record at closeout.
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/tier-001-tiered-assurance.md docs/superpowers/plans/2026-08-08-tier-001-tiered-assurance.md docs/fleet-roadmap.md
git commit -m "TIER-001: approve spec, add plan and active roadmap item"
```

---

### Task 1: `check_adapters` parameter and wiring-test de-duplication

**Files:**
- Modify: `scripts/validate_fleet.py:1728-1747` (`validate_repo`)
- Modify: `tests/test_validate_fleet.py:521-535` (`_issues_after`, positive control),
  `tests/test_validate_fleet.py:809` (`test_stale_generated_platform_adapter_is_reported`)
- Test: new class `AdapterCheckTierTests` in `tests/test_validate_fleet.py`

**Interfaces:**
- Produces: `validate_repo(root, *, check_inventory: bool = True, check_adapters: bool = True)`
  — same return type `tuple[list[str], list[str], list[str]]`. CLI behavior unchanged (`main`
  never passes `check_adapters`, so the command line always runs the full validation).

- [ ] **Step 1: Write the failing test** (add near the other repo-copy classes; it mirrors the
  mutation style of `test_stale_generated_platform_adapter_is_reported`)

```python
class AdapterCheckTierTests(unittest.TestCase):
    """The T0/T1 tier boundary for adapter byte-drift.

    check_adapters=False exists so ~100 wiring mutation tests stop re-generating and
    byte-comparing every host adapter to check one unrelated breakage. These two tests pin the
    flag's semantics: True still reports drift (so dropping the separate --check recipe line
    loses nothing), and False genuinely skips it (so the speedup is real, and a future adapter
    test that forgets to pass True fails loudly — its expected issue never appears)."""

    def _repo_with_drifted_adapter(self, tmp: str) -> Path:
        dst = Path(tmp) / "repo"
        shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        adapter = sorted((dst / ".github" / "agents").glob("*.md"))[0]
        adapter.write_text(
            adapter.read_text(encoding="utf-8") + "\nhand edit\n", encoding="utf-8"
        )
        return dst

    def test_flag_on_reports_hand_edited_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = self._repo_with_drifted_adapter(tmp)
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=True
            )
            self.assertTrue(issues, "hand-edited adapter must be reported when the check runs")

    def test_flag_off_skips_only_the_adapter_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = self._repo_with_drifted_adapter(tmp)
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=False
            )
            self.assertEqual([], issues, "the only defect is adapter drift; skipping the "
                                         "adapter check must leave a clean report")
```

- [ ] **Step 2: Run to verify both fail**

```bash
python -m unittest discover -s tests -p test_validate_fleet.py -k AdapterCheckTierTests > "$SCRATCH/task1-red.txt" 2>&1; echo "exit=$?"
```

Expected: exit=1, `TypeError: validate_repo() got an unexpected keyword argument
'check_adapters'` in the file. This failure IS the proves-it-fails-without-the-change evidence —
save the file for the PR.

- [ ] **Step 3: Implement the parameter** in `scripts/validate_fleet.py`

```python
def validate_repo(
    root: Path, *, check_inventory: bool = True, check_adapters: bool = True
) -> tuple[list[str], list[str], list[str]]:
    agent_issues, agent_names = validate_agents(root)
    skill_issues, skill_names = validate_skills(root)
    issues = agent_issues + skill_issues
    issues.extend(validate_plugin(root, agent_names, skill_names))
    # The adapter byte-compare is 59% of a validation run (profiled 2026-08-08) and is
    # independent of every other rule, so callers validating a deliberate non-adapter mutation
    # may skip it. The command line never does: `main` always runs the full set, which is why
    # the recipe's separate `generate --check` step could be retired without losing the gate.
    if check_adapters:
        issues.extend(validate_platform_adapters(root))
    issues.extend(validate_agent_guide(root))
    ...  # remaining lines unchanged
```

- [ ] **Step 4: Run the new tests to verify they pass**

```bash
python -m unittest discover -s tests -p test_validate_fleet.py -k AdapterCheckTierTests
```

Expected: `OK`, 2 tests. If `test_flag_off_skips_only_the_adapter_check` reports non-adapter
issues, some other check also reads generated adapter bytes — investigate before proceeding;
the flag must not paper over a second reader.

- [ ] **Step 5: Thread the flag through the wiring harness.** In
  `PluginWiringTests._issues_after`, default to skipping — safe because a mutation test whose
  expected issue needs the adapter check will fail loudly, not pass vacuously:

```python
    def _issues_after(self, mutate, *, check_adapters: bool = False) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "repo"
            # tests/ stays in the copy: AGENTS.md names `tests/fixtures/`, and the guide drift
            # check resolves every multi-segment path it asserts.
            shutil.copytree(
                REPO, dst, ignore=shutil.ignore_patterns(".git", "__pycache__")
            )
            mutate(dst)
            # Default False: these tests each check ONE deliberate non-adapter breakage, and
            # the adapter byte-compare they would otherwise repeat is 59% of a run. A test
            # that DOES mutate adapters must pass True — forgetting is loud (its asserted
            # issue never appears), never a silent pass.
            issues, _, _ = validate_fleet.validate_repo(
                dst, check_inventory=False, check_adapters=check_adapters
            )
            return issues
```

Then update exactly two callers:
- the positive control: `self.assertEqual([], self._issues_after(lambda _: None, check_adapters=True))`
- `test_stale_generated_platform_adapter_is_reported` (line 809): pass `check_adapters=True`
  in its `_issues_after` call.

- [ ] **Step 6: Run the whole module, timed, capturing to a file**

```bash
python -m unittest discover -s tests -p test_validate_fleet.py > "$SCRATCH/task1-module.txt" 2>&1; echo "exit=$?"
```

Expected: exit=0; quote `Ran 131 tests in …s` from the file (129 + the 2 new). Target for the
module: roughly half of the 76–83 s baseline. Record the number for the PR.

- [ ] **Step 7: Commit**

```bash
git add scripts/validate_fleet.py tests/test_validate_fleet.py
git commit -m "validate_repo: optional adapter check; stop recomputing byte-drift under every wiring test"
```

---

### Task 2: `scripts/eval_baseline.py` — offline baseline resolver

**Files:**
- Create: `scripts/eval_baseline.py`
- Test: `tests/test_eval_baseline.py`

**Interfaces:**
- Consumes (imported from `scripts/eval_routing.py`, never copied):
  `benchmark_provenance(source_paths, cases, expression, plugin_dir, limit, *, evaluator_paths)`,
  `routing_evaluator_paths()`, `ProvenanceError`, `PROVENANCE_SCHEMA`.
- Produces: `main(argv: list[str] | None = None) -> int` with exit codes 0 REUSABLE / 1 STALE /
  2 usage-or-provenance error; helpers `desired_provenance(root, cluster_path, expression,
  limit)`, `provenance_divergences(stored, desired) -> list[str]`,
  `condition_divergences(stored, desired) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the offline baseline resolver.

Everything runs against synthetic benchmark.json files in a temp baselines directory. The one
real computation is the desired provenance over THIS repository (computed once per class);
mutating a copy of it simulates each way a stored artifact can go stale. No test launches a
session, reads credentials, or touches the network — the resolver's whole point is that a
REUSABLE verdict costs nothing.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import eval_baseline  # noqa: E402

CLUSTER = REPO / "evals" / "routing" / "prompt-tooling.json"
CONDITIONS = {"model_requested": "sonnet", "clean_room": True, "threshold": 0.5,
              "timeout_s": 420, "cli_version": "2.1.220 (Claude Code)"}
ARGS = ["--model", "sonnet", "--clean-room", "--timeout", "420", str(CLUSTER)]


class EvalBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.desired = eval_baseline.desired_provenance(REPO, CLUSTER, "*", 0)

    def _write_benchmark(self, root: Path, provenance: dict, conditions: dict) -> Path:
        out = root / "2026-08-08-synthetic" / "routing-prompt-tooling"
        out.mkdir(parents=True)
        path = out / "benchmark.json"
        path.write_text(json.dumps({
            "cluster": "prompt-tooling", "conditions": conditions, "provenance": provenance,
        }), encoding="utf-8")
        return path

    def _run(self, baselines: Path) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            code = eval_baseline.main(["--baselines-dir", str(baselines), *ARGS])
        return code, stdout.getvalue()

    def test_exact_match_is_reusable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_benchmark(Path(tmp), self.desired, dict(CONDITIONS))
            code, out = self._run(Path(tmp))
        self.assertEqual(0, code)
        self.assertIn("REUSABLE", out)
        self.assertIn(path.parent.name, out)

    def test_changed_plugin_bytes_are_stale_and_named(self) -> None:
        mutated = copy.deepcopy(self.desired)
        mutated["plugin"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            self._write_benchmark(Path(tmp), mutated, dict(CONDITIONS))
            code, out = self._run(Path(tmp))
        self.assertEqual(1, code)
        self.assertIn("plugin", out)

    def test_changed_model_is_stale_and_named(self) -> None:
        conditions = dict(CONDITIONS, model_requested="opus")
        with tempfile.TemporaryDirectory() as tmp:
            self._write_benchmark(Path(tmp), self.desired, conditions)
            code, out = self._run(Path(tmp))
        self.assertEqual(1, code)
        self.assertIn("model_requested", out)

    def test_older_provenance_schema_is_stale(self) -> None:
        mutated = copy.deepcopy(self.desired)
        mutated["schema"] = "sde-agents/eval-provenance/v1"
        with tempfile.TemporaryDirectory() as tmp:
            self._write_benchmark(Path(tmp), mutated, dict(CONDITIONS))
            code, out = self._run(Path(tmp))
        self.assertEqual(1, code)
        self.assertIn("schema", out)

    def test_cli_version_difference_alone_stays_reusable(self) -> None:
        conditions = dict(CONDITIONS, cli_version="9.9.9 (Claude Code)")
        with tempfile.TemporaryDirectory() as tmp:
            self._write_benchmark(Path(tmp), self.desired, conditions)
            code, out = self._run(Path(tmp))
        self.assertEqual(0, code)
        self.assertIn("cli_version", out)  # advisory note, not a stale verdict

    def test_empty_baselines_directory_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out = self._run(Path(tmp))
        self.assertEqual(1, code)
        self.assertIn("STALE", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

```bash
python -m unittest discover -s tests -p test_eval_baseline.py > "$SCRATCH/task2-red.txt" 2>&1; echo "exit=$?"
```

Expected: exit=1, `ModuleNotFoundError: No module named 'eval_baseline'`.

- [ ] **Step 3: Implement `scripts/eval_baseline.py`**

```python
"""Resolve whether a stored routing benchmark still covers the 'before' side of a paired run.

The eval-first law says a description edit owes a before/after routing diff. The 'before' side
is evidence about bytes, not the calendar: if nothing a benchmark measured has changed — same
cluster definition, same selected cases, same evaluator and graders, same plugin bytes — and
the conditions the operator intends match the recorded ones, that benchmark IS the before run,
already paid for. This resolver answers exactly that question offline. It recomputes the same
provenance identities the runner records — imported from eval_routing, never reimplemented, so
the hash semantics cannot fork — and compares them against every stored benchmark.json. It
never launches a session and never touches the network: a REUSABLE verdict spends nothing, and
a STALE verdict names what diverged so the operator knows why a fresh capture is owed.

Match policy (TIER-001 spec, operator-approved 2026-08-08): provenance exact on schema,
eval_sources, selection, evaluator, and the plugin content hash; conditions exact on
model_requested, clean_room, threshold, timeout_s. cli_version is advisory — the probe, not
the eval suite, owns CLI drift — so a mismatch is printed but does not stale the verdict.

Exit codes: 0 a reusable benchmark exists (newest path printed), 1 none does (divergences
printed per same-cluster candidate), 2 usage or provenance error.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_routing  # noqa: E402  (sibling module; scripts/ is not a package)

REPO = Path(__file__).resolve().parents[1]
EXACT_CONDITIONS = ("model_requested", "clean_room", "threshold", "timeout_s")


def desired_provenance(root: Path, cluster_path: Path, expression: str, limit: int) -> dict:
    """The provenance a run started right now would record — the comparison target."""
    spec = json.loads(cluster_path.read_text(encoding="utf-8"))
    cases = [case for case in spec.get("cases", [])
             if isinstance(case, dict) and fnmatch.fnmatch(str(case.get("id", "")), expression)]
    if limit:
        cases = cases[:limit]
    if not cases:
        raise eval_routing.ProvenanceError("no cases matched the selection expression")
    return eval_routing.benchmark_provenance(
        [cluster_path], cases, expression, root, limit,
        evaluator_paths=eval_routing.routing_evaluator_paths(),
    )


def provenance_divergences(stored: dict, desired: dict) -> list[str]:
    if stored.get("schema") != desired["schema"]:
        # Older schemas lack identities the policy compares; nothing else is worth naming.
        return [f"schema ({stored.get('schema')!r}, current is {desired['schema']!r})"]
    diverged = [key for key in ("eval_sources", "selection", "evaluator")
                if stored.get(key) != desired[key]]
    stored_plugin = stored.get("plugin")
    if not isinstance(stored_plugin, dict) or stored_plugin.get("sha256") != desired["plugin"]["sha256"]:
        diverged.append("plugin")
    return diverged


def condition_divergences(stored: dict, desired: dict) -> list[str]:
    return [f"{key} (stored {stored.get(key)!r}, requested {desired[key]!r})"
            for key in EXACT_CONDITIONS if stored.get(key) != desired[key]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cluster", nargs="?",
                        default=str(REPO / "evals" / "routing" / "prompt-tooling.json"))
    parser.add_argument("--root", type=Path, default=REPO, help="repository root")
    parser.add_argument("--baselines-dir", type=Path, default=None,
                        help="benchmark store (default <root>/evals/baselines)")
    # Selection and conditions mirror eval_routing's flags and defaults exactly: the resolver
    # asks "would THIS invocation's before-run be redundant", so it must speak the same request.
    parser.add_argument("--case", default="*", help="glob over case ids (default all)")
    parser.add_argument("--limit", type=int, default=0, help="cap number of cases (0 = all)")
    parser.add_argument("--model", required=True,
                        help="model the paired run will pin (required: an unpinned run is not "
                             "comparison-grade, so it has no baseline to resolve)")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--clean-room", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    cluster_path = Path(args.cluster).resolve()
    baselines = (args.baselines_dir or root / "evals" / "baselines").resolve()
    try:
        desired = desired_provenance(root, cluster_path, args.case, args.limit)
    except (OSError, ValueError, eval_routing.ProvenanceError) as exc:
        print(f"resolver error: {exc}", file=sys.stderr)
        return 2
    cluster_name = json.loads(cluster_path.read_text(encoding="utf-8")).get("cluster")
    desired_conditions = {"model_requested": args.model, "clean_room": args.clean_room,
                          "threshold": args.threshold, "timeout_s": args.timeout}

    matches: list[Path] = []
    near_misses: list[tuple[Path, list[str]]] = []
    # Lexicographic order: baseline directories are date-prefixed by convention, and file
    # mtimes do not survive a fresh clone, so path order is the only stable notion of "newest".
    for path in sorted(baselines.rglob("benchmark.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print(f"warning: unreadable benchmark skipped: {path}", file=sys.stderr)
            continue
        if not isinstance(document, dict) or document.get("cluster") != cluster_name:
            continue
        stored_provenance = document.get("provenance")
        stored_conditions = document.get("conditions")
        if not isinstance(stored_provenance, dict) or not isinstance(stored_conditions, dict):
            near_misses.append((path, ["no recorded provenance/conditions — not a baseline"]))
            continue
        diverged = provenance_divergences(stored_provenance, desired)
        diverged += condition_divergences(stored_conditions, desired_conditions)
        if diverged:
            near_misses.append((path, diverged))
        else:
            matches.append(path)
            cli = stored_conditions.get("cli_version")
            if cli is not None:
                print(f"note: cli_version {cli!r} recorded (advisory only; the probe owns CLI drift)")

    if matches:
        print(f"REUSABLE {matches[-1]}")
        for extra in matches[:-1]:
            print(f"  also matching: {extra}")
        return 0
    print(f"STALE: no stored benchmark for cluster {cluster_name!r} matches the current bytes "
          f"and requested conditions; a fresh 'before' capture is owed.")
    for path, diverged in near_misses[-3:]:
        print(f"  {path}: diverged on {', '.join(diverged)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m unittest discover -s tests -p test_eval_baseline.py > "$SCRATCH/task2-green.txt" 2>&1; echo "exit=$?"
```

Expected: exit=0, `Ran 6 tests` in the file. Also smoke the CLI against the real store (expect
STALE, exit 1 — current bytes long since diverged from the 2026-08-01 artifacts):

```bash
python scripts/eval_baseline.py --model sonnet --clean-room --timeout 420 evals/routing/continuous-improvement.json; echo "exit=$?"
```

- [ ] **Step 5: Commit**

```bash
git add scripts/eval_baseline.py tests/test_eval_baseline.py
git commit -m "eval_baseline: offline resolver from current bytes to a still-valid routing benchmark"
```

---

### Task 3: Tier map in AGENTS.md and README.md

**Files:**
- Modify: `AGENTS.md:40-50` (the "Validate before you push" section)
- Modify: `README.md:~310-345` (read the section first; it owns the convention on conflict)

**Interfaces:** none (prose). The validator's guide checks require every multi-segment repo path
named in AGENTS.md to exist — `scripts/eval_baseline.py` exists after Task 2, which is why this
task comes third.

- [ ] **Step 1: Replace the AGENTS.md section** (lines 40-50) with:

```markdown
## Validate before you push

Validation is tiered: depth matches risk, and each tier reuses the previous tier's evidence
instead of recomputing it.

- **T0 — edit loop** (seconds): `python3 scripts/validate_fleet.py` plus the test module that
  owns what you touched (`python3 -m unittest discover -s tests -p test_<area>.py`). The
  validator byte-compares every generated adapter itself, so a separate
  `generate_platform_adapters.py --check` adds nothing here; `--write` (below) remains the
  regeneration command after canonical edits.
- **T1 — before push / PR**: the full offline suite, `python3 -m unittest discover -s tests -v`,
  plus `claude plugin validate . --strict` for the platform contract. CI runs the validator,
  the tests, and the ledger-drift report on Ubuntu for every PR, and the plugin contract check
  on Linux.
- **T2 — merge and weekly** (CI-owned): pushes to main, the Monday sweep, and manual dispatch
  run the full Linux/macOS/Windows matrix, so platform-specific guard and hook paths are
  exercised without billing every PR for them (see the matrix comment in
  `.github/workflows/validate.yml`).
- **T3 — release / CLI pin bump** (manual, real API): `scripts/probe_plugin.py` and the eval
  suites, per the section below. Before a paired routing run, `scripts/eval_baseline.py`
  reports whether a stored benchmark already covers the 'before' side — reuse it when it does;
  the 'after' side is always fresh.
```

- [ ] **Step 2: Read `README.md:300-350` and apply the same tiering to its validation section**
  — keep README the authority: its text should state the tier convention; AGENTS.md's version
  paraphrases it. Where README's current text lists `generate_platform_adapters.py --check` as a
  pre-push step, retitle it as the direct probe of the byte-drift gate (its line 339 framing)
  rather than a required serial step. Do not touch unrelated README prose.

- [ ] **Step 3: Validate and commit**

```bash
python scripts/validate_fleet.py; echo "exit=$?"
git add AGENTS.md README.md
git commit -m "docs: tiered validation recipe; retire the duplicate adapter --check step; fix the stale CI matrix paraphrase"
```

Expected: exit=0 — this also proves the guide path-drift check accepts every path the new text
names.

---

### Task 4: CI durations tripwire

**Files:**
- Modify: `.github/workflows/validate.yml` (the unittest step)

- [ ] **Step 1: Edit the step**

```yaml
      - name: Run repository unit tests
        # --durations 10 (Python 3.12+) prints the slowest tests in every log: the suite's
        # slow-creep gets rediscovered by reading CI instead of by a profiling session.
        run: ${{ matrix.py }} -m unittest discover -s tests -v --durations 10
```

- [ ] **Step 2: Verify LF endings survived and the validator accepts the workflow**

```bash
git ls-files --eol .github/workflows/validate.yml
python scripts/validate_fleet.py; echo "exit=$?"
```

Expected: `w/lf`, exit=0.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/validate.yml
git commit -m "ci: print the ten slowest tests in every unittest log"
```

---

### Task 5: Acceptance evidence and the round PR

**Files:** none new (scratch outputs only, under the session scratchpad `$SCRATCH`)

- [ ] **Step 1: Full-suite after-measurement, file-captured**

```bash
python -m unittest discover -s tests > "$SCRATCH/after-suite.txt" 2>&1; echo "exit=$?"
```

Quote the `Ran N tests in X.XXXs` line and `OK` from the file. Compare against the recorded
before (130.6 s).

- [ ] **Step 2: Detector spot-proof A — the retired `--check` recipe line is still covered.**
  Hand-edit one generated adapter in the working tree, run `python scripts/validate_fleet.py`,
  expect exit 1 naming the file; then `git checkout -- <file>` and re-run, expect exit 0.
  Capture both runs to `$SCRATCH/detector-a.txt`.

- [ ] **Step 3: Detector spot-proof B — the wiring class still fires.** Add a bogus key
  (`nonsense: true`) to `agents/code-reviewer.md` frontmatter, run
  `python -m unittest discover -s tests -p test_validate_fleet.py -k test_the_real_repo_is_a_valid_plugin`,
  expect FAIL (the positive control asserts a clean repo); revert, re-run, expect OK. Capture to
  `$SCRATCH/detector-b.txt`.

- [ ] **Step 4: Remaining gates**

```bash
python scripts/generate_platform_adapters.py --check
python scripts/validate_fleet.py
python scripts/ledger_drift.py --root .
claude plugin validate . --strict
```

Each on its own, each exit status echoed. If the `claude` CLI is unavailable locally, record
that line as [unverified locally — CI's pinned job covers it].

- [ ] **Step 5: Push and open the PR** using `.github/pull_request_template.md`: claim plus
  consequence per line; conditional-gates rows tripped — *validator rule changed* (Task 1's red
  run is the fails-without-it proof) and *work a doc tracks as open* (the roadmap TIER-001
  entry, added this round). State explicitly: no description edits → no routing runs owed; no
  guard/hook changes → no probe owed; no canonical agent/skill bytes → no adapter regeneration.
  Quote before/after suite numbers and both detector proofs.

```bash
git push -u origin tier-001/tiered-assurance
gh pr create --title "TIER-001: tiered assurance and evidence reuse for the fleet's own gates" --body-file "$SCRATCH/pr-body.md"
```

---

## Self-review

- Spec coverage: scope 1 → Task 1; scope 2 → Task 2; scope 3 → Task 3; scope 4 → Task 4;
  acceptance bullets → Task 5 (+ Task 1 Step 2 and Task 2 tests). Freshness policy → Task 2's
  `EXACT_CONDITIONS` + advisory cli_version. Roadmap/spec governance → Task 0.
- No placeholders: every code step carries the actual payload; README Step 2 is deliberately a
  read-then-edit instruction because the README section must be read before rewording (source
  of authority), with the outcome pinned (tier convention stated, `--check` reframed not
  required).
- Type consistency: `validate_repo` keyword threading matches between Tasks 1; resolver helper
  names match between test and implementation (`desired_provenance`, `main`,
  `--baselines-dir`).
