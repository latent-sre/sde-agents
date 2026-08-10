# REL-173 released-artifact retest — conditions

- **Artifact under test:** installed plugin `sde-agents@latent-sre` version 1.7.3, updated from
  the `latent-sre` directory marketplace after tag `sde-agents--v1.7.3` (main `f6cfdb3`) was
  pushed. `claude plugin list` confirmed `Version: 1.7.3 / Status: enabled` before the run.
- **Instrument:** one headless session (`claude -p`, main loop `sonnet`, `--allowedTools
  Workflow`, no `--plugin-dir` — the installed artifact, not the working tree) in a scratch
  two-commit git repository, prompting a single invocation of the `sde-agents:deep-review`
  workflow; phase models are the workflow's own pins (scope sonnet, lanes opus).
- **Scenario retested:** the 1.7.0 failure class — the workflow shipping validator-green but
  unloadable (`meta is not defined`), caught twice from the same file in opposite directions
  (`lc_546acdcc`).
- **Result:** PASS — the workflow loaded, both lanes ran, and the deterministic merge record
  returned verdict `provisional-commit-and-re-review` with `confirmed_criticals: 0`; the
  provisional cap fired because the scratch tree was dirty (the tee'd output file), which is
  the REV-001-preserved advisory behavior operating on the released artifact. Transcript:
  [`deep-review-released-retest.txt`](deep-review-released-retest.txt).
- **Deterministic gates at the tag commit** (rerun after #115/#116/#117 landed post-PR-gates):
  `validate_fleet.py` clean (11 agents, 19 skills), `run_tests.py` 612/612 across 22 modules,
  `claude plugin validate . --strict` pass.
- **T3 probe:** `scripts/probe_plugin.py` run recorded separately in this directory
  (`probe-output.txt`) — load, `${CLAUDE_PLUGIN_ROOT}` expansion, guard scoping.
