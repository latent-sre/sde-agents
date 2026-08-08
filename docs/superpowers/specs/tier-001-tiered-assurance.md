# TIER-001 spec — tiered assurance and evidence reuse for the fleet's own gates

**Status: approved** — drafted 2026-08-08, approved by the operator the same day with the
recommended freshness-policy default. This spec governs the round's scope and acceptance; the
paired plan is `docs/superpowers/plans/2026-08-08-tier-001-tiered-assurance.md`.

## Problem

The repo's assurance surface grew one gate at a time, and the cost now concentrates in repeated
work over unchanged artifacts, not in rigor. Measured 2026-08-08 on the local Windows 11 dev
machine at commit `28a3838` (all figures wall-clock, quoted from runs in the drafting session):

| Check | Measured cost | Where the time actually goes |
|---|---|---|
| `generate_platform_adapters.py --check` | 0.63 s | full in-memory regeneration + byte compare |
| `validate_fleet.py` | 1.09 s wall / 0.59 s in-process | 0.35 s (59%) is that same adapter regeneration + byte compare, recomputed |
| `unittest discover -s tests` | ~116 s | `test_validate_fleet.py` alone is 76–83 s (129 tests) |
| routing / behavioral evals | minutes + real API dollars per cluster | fresh sessions per run; baselines stored by **date** with provenance hashes but no resolver from current bytes to a still-valid artifact |
| `probe_plugin.py` | API sessions | already risk-matched: owed only on CLI pin bumps |

Inside `test_validate_fleet.py`, `PluginWiringTests._issues_after` copies the entire repository
(0.41 s, 869 entries) **and** runs the full `validate_repo` (~0.6 s) once per test — so every
mutation test re-validates ~30 unchanged definitions and re-generates every host adapter to check
one deliberate breakage. The suite's dominant cost is the same authoritative result recomputed
dozens of times per run, which is exactly the anti-pattern the round exists to remove.

Already tiered — this round must not redo it: PR #88's conditional CI matrix (PRs ubuntu-only,
main/weekly/dispatch full), the manual-on-demand posture of both eval suites, the pin-bound
probe, and ledger-drift's advisory-findings / blocking-crashes split.

## Scope

1. **De-duplicate the wiring-test harness.** `validate_repo` gains an explicit
   `check_adapters: bool = True` parameter; `PluginWiringTests` mutation tests whose rule is not
   an adapter rule pass `False`. Adapter byte-drift keeps its own dedicated mutation tests and
   the full-validation positive control, so the control still fires — it just stops being
   recomputed under a hundred unrelated tests. Optionally, the per-test repo copy moves to a
   class-level pristine template copied per test, if measurement shows the walk (not the write)
   dominates. Target: full suite at or below ~60 s, measured before/after on the same machine
   and quoted in the PR. No mutation test may lose its failure assertion.
2. **Baseline resolver — `scripts/eval_baseline.py`** (stdlib, offline, read-only). Given a
   cluster file, recompute the identity material the benchmark provenance already records
   (cluster bytes, member definitions, evaluator/grader, plugin bytes) and scan
   `evals/baselines/**/benchmark.json` for the newest artifact matching the freshness policy
   below. Output: `REUSABLE <path>` or `STALE <which hash or condition diverged>`. The
   before/after law then reads: the **before** run may be satisfied by a `REUSABLE` artifact;
   the **after** run is always fresh. The resolver never launches a session and never touches
   the network — it converts already-purchased evidence into the authoritative reusable result.
3. **Tiered recipe in AGENTS.md.** "Validate before you push" becomes an explicit tier map:
   - **T0 edit loop** — `validate_fleet.py` plus the test module owning the touched artifact;
   - **T1 pre-push / PR** — the full offline suite. The separate `generate --check` line is
     dropped from the recipe: the validator's byte-drift check subsumes it (profile-proven —
     59% of a validator run *is* that check). `--write` remains the regeneration command;
   - **T2 merge / weekly** — CI's full matrix (already landed, #88);
   - **T3 release / pin-bump** — probe plus eval sweep (already law).
   The same edit fixes the stale CI paraphrase: AGENTS.md still claims the three-OS matrix runs
   "the first two commands" on every run — post-#88 the matrix is conditional, and CI runs
   `validate_fleet` + the unit tests, never `generate --check`.
4. **Suite performance tripwire.** The CI unittest step gains `--durations 10` (Python 3.12+ on
   all three runners) so the next slow-creep is visible in every log instead of rediscovered by
   a profiling session like this one.

## Freshness policy for baseline reuse (operator decision)

The one genuinely open design choice: what must match before a stored benchmark counts as the
**before**. Recommended default — exact on all five provenance hashes, and exact on
`model_requested`, `clean_room`, `threshold`, and `timeout_s` (the README already rules that
artifacts differing on `clean_room` must not be diffed, and that timeout moves every rate);
`cli_version` recorded in the resolver's output but advisory, since the probe — not the eval
suite — owns CLI drift. Approved 2026-08-08 as recommended; the block below is now the policy
the resolver implements:

```text
match_exact: provenance[cluster, members, evaluator, grader, plugin_bytes],
             conditions[model_requested, clean_room, threshold, timeout_s]
advisory:    conditions[cli_version]
```

## Out of scope

- No cross-gate result cache or content-addressed build layer: a cache is itself a
  silent-failure surface, and this repo's gates exist to make silence loud. Rejected.
- No CI matrix, billing, or scheduling changes — #88 owns that posture.
- No change to the manual-on-demand posture of the eval suites or the probe.
- No weakening of any control. Every mutation test keeps a positive failure assertion, and the
  validator CLI contract is unchanged (`check_adapters` defaults to `True`).

## Acceptance

- Suite wall time before/after on the same machine quoted in the PR; every existing mutation
  assertion intact, spot-proven by breaking one guarded rule per affected class and watching the
  suite go red (the detector-proof rule: a faster green is worthless until it is shown to fail).
- `eval_baseline.py` unit tests over synthetic benchmark fixtures: full match → `REUSABLE`;
  each provenance hash divergence and each exact-match condition divergence → `STALE` naming
  the diverged field; no network, no session, no API key read.
- AGENTS.md tier map matches `validate.yml` as merged (the source wins on conflict, per the
  file's own rule); the dropped `--check` line is justified in the PR by the profile evidence.
- Deterministic gates green; adapters regenerated only if canonical text changes (none planned).
