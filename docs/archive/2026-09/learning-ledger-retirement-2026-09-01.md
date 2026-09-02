# Learning-ledger retirement — the obligations it still carried

**State:** Historical record. This document is not a task list. Only `docs/fleet-roadmap.md` can
import work from it.

**Retired at:** commit `e34871d` (2026-09-01); the last revision holding the records is `3013a05`
(`git show 3013a05:learning/candidates/<id>.json`).

The ledger's own lifecycle rule said a promoted candidate whose destination ships in the plugin
closes only after a retest against the exact released version. At retirement, 45 candidates were
`promoted`; 11 carried a released version and a passing retest, and the 34 below did not. Their
lessons are landed in source — `promoted` meant the reviewed change merged — so what is
unrecorded is a released-artifact retest, not the change itself. Under the 2026-09-02
single-operator ruling the fleet no longer tracks that retest per lesson: a future regression
reaches the operator as field feedback, and the field-feedback issue's "Released version" and
"Downstream retest" fields are where such a retest is recorded. This list exists so a session
that meets one of these destinations knows a retest was never taken.

Several destinations have since been retired outright (the ledger itself, `workflow_contract.py`,
`verification_sandbox.py`, `eng-ladder`), which closes their rows by removal.

| State | Candidate | Destination | Released version | Retest |
|---|---|---|---|---|
| awaiting-release | `lc_081ce4a6a7fc415bb3f479037a2f2057` | agents/verification-engineer.md failure-path staging guidance | — | — |
| awaiting-release | `lc_1584f9cbf69342bf8cff121b05340599` | skills/code-craft/references/tdd.md Tests that stay useful | — | — |
| awaiting-release | `lc_2e549c0b8f6d4b78a4a7c915f372946f` | scripts/eval_behavioral.py (failing-run transcript retention) | — | — |
| awaiting-release | `lc_36adb3d0d10542eba6fc969c575590c7` | GitHub branch protection on main (live setting, not repo bytes) | — | — |
| awaiting-release | `lc_48a46800b83f48319af04e3916586f3d` | scripts/learning_ledger.py read-path root resolution, with its firing test in tests/test_learning_ledger.py | — | — |
| awaiting-release | `lc_502daaf35fc0414fbe3ef089f6b2c05f` | AGENTS.md Change playbooks, Closing a task that surfaced a discovery | — | — |
| awaiting-release | `lc_6f4f74f8fe7a4684b06e97d2825ec04c` | AGENTS.md One writer per checkout (confirm the base before reading it) | — | — |
| awaiting-release | `lc_854a12b53a16434f81128a9ca256fbc0` | agents/researcher.md Method section 3 retrieval-path fidelity clause | — | — |
| awaiting-release | `lc_8f572581438d407782e8371d3507d59a` | agents/prompt-engineer.md Craft knowledge form-to-failure guidance | — | — |
| awaiting-release | `lc_a3bedde1f8e846caa6656414f3c768c7` | evals/README.md behavioral-grading doctrine paragraph (2026-08-12 rules) | — | — |
| awaiting-release | `lc_b16a38fe36d84989925502b1b4fd68a5` | agents/sde-fullstack.md Receiving review findings | — | — |
| awaiting-release | `lc_b7e21dca0888431fbbf4243341f80e1f` | AGENTS.md Adding a defensive branch to a fleet script (diagnostic-message twin) | — | — |
| awaiting-release | `lc_b96e0c0a98d24c388c3e9ceb866ecdec` | AGENTS.md Change playbooks, a new Editing a workflow entry | — | — |
| awaiting-release | `lc_c361b3d364084ed99b530820e7aa4245` | README.md Codex lane section 'What this lane surfaces to the model' plus skills/onboarding-map/SKILL.md | — | — |
| awaiting-release | `lc_c4b42221326942d9b9e811aa0054b54c` | AGENTS.md Change playbooks (record-shape change) | — | — |
| awaiting-release | `lc_d4a94758c5084f9f86b39976c50f7383` | evals/README.md behavioral-grading doctrine paragraph (2026-08-12 rules) | — | — |
| awaiting-release | `lc_e3d20c6c37d84233aa476778d8f73263` | scripts/workflow_contract.py shape tables and the every-declared-field wrong-type test in tests/test_workflow_contract.py | — | — |
| awaiting-release | `lc_e4234dfe331f44ec9e546807c3e373d5` | skills/eng-ladder/SKILL.md Mode 1 | — | — |
| awaiting-release | `lc_eb28770cc9544349827ededf3151c52a` | evals/README.md grader-authoring guidance | — | — |
| awaiting-retest | `lc_0fe6c3d188cc403595bfc13b1f6d8cd2` | agents/homelab-platform.md:27 and skills/service-onboard/SKILL.md:20-25 | 1.7.3 | inconclusive |
| awaiting-retest | `lc_11afd10b693a45be8af6d34c4ed677e5` | agents/sde-fullstack.md Receiving review findings | 1.7.3 | inconclusive |
| awaiting-retest | `lc_19d4d9323990456f8be0dad0fb146aaf` | AGENTS.md Adding a defensive branch to a fleet script (doc-side twin) | 1.7.3 | inconclusive |
| awaiting-retest | `lc_2665af1325f840a2ae78622b922ac28c` | AGENTS.md Change playbooks | 1.7.3 | inconclusive |
| awaiting-retest | `lc_2c04ead31cc94f14bb029bfb243132b4` | agents/code-reviewer.md | 1.7.3 | inconclusive |
| awaiting-retest | `lc_6216159a5ce14e94875e8336c9fe24a1` | agents/researcher.md Method section 3 | 1.7.3 | inconclusive |
| awaiting-retest | `lc_6b36cf5d55cd439f88afd7f5ed24ad26` | docs/fleet-roadmap.md GATE-001 | 1.7.3 | inconclusive |
| awaiting-retest | `lc_74f047304cdc42f7b043404be1e8febb` | docs/fleet-roadmap.md LOOP-001 | 1.7.3 | inconclusive |
| awaiting-retest | `lc_7d0844a0af994428b174825451f1c7a9` | skills/code-craft/references/tdd.md | 1.7.3 | inconclusive |
| awaiting-retest | `lc_8223961a2a78461cbe5543afdc890b10` | AGENTS.md Validate before you push (review-loop stop rule) | 1.7.3 | inconclusive |
| awaiting-retest | `lc_90dd8dc7221846d285bdaedc5f92b2a4` | agents/verification-engineer.md | 1.7.3 | inconclusive |
| awaiting-retest | `lc_da1da4960edd46e2a4ed8410012ca3f7` | scripts/verification_sandbox.py docstring | 1.7.3 | inconclusive |
| awaiting-retest | `lc_de3dbac7d78148e89494a07e96e8afb1` | AGENTS.md | 1.7.3 | inconclusive |
| awaiting-retest | `lc_e15d1785bea747549b9a947dfa837be5` | agents/verification-engineer.md Method 5 (via GATE-001 round) | 1.7.3 | inconclusive |
| awaiting-retest | `lc_f3c0b831fc3d4429bc702107429df7a7` | agents/verification-engineer.md | 1.7.3 | inconclusive |
