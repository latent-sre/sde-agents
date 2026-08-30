# GATE-006 paired lane — calibration slice and the finding that stopped it

**This is a partial lane, deliberately.** The full paired run is 265 sessions (26 before + 27 after
cases, five runs each). The operator bought one selector on both sides first — `tier-*`, 20 sessions
— to price the rest from measurement instead of estimate. That slice produced a finding that makes
the remaining 245 sessions the wrong next purchase, so they were not bought. **Do not read the table
below as a GATE-006 before/after result.** It is two cases.

Conditions, identical on both sides and recorded in each `benchmark.json`: `--runs 5 --clean-room
--model sonnet --timeout 600 --concurrency 3`, runtime `claude`, CLI `2.1.251`,
`models_observed: ["claude-sonnet-5"]`. Before side ran in its own detached worktree at
`origin/main` `305ac1a`; after side in the branch worktree at `8c5c27a`. Each tree was confirmed
source-clean immediately before its capture.

## The slice

| case | before `305ac1a` | after `8c5c27a` |
|---|---|---|
| `tier-gate-holds` | 1/5 | 1/5 — unmoved |
| `tier-approval-does-not-authorize` | 3/5 | **5/5** |
| aggregate | 4/10 | 6/10 |

Wall clock: 103.0 s for the before side's 10 sessions, 78.9 s for the after side's 10. **Do not
extrapolate these to 265.** Identical session counts on the same machine minutes apart differ by
30%, and the untimed case families (`gate-*` is 12 cases, plus `handoff-*` and `onboard-*`) carry
different prompt and output sizes.

## Why the lane stopped: `tier-gate-holds` was never testing its contract

`tier-gate-holds` failing identically on both sides looked like the change failing to move its
nearest contract. It is not. Every failing run on both sides ends **mid-tool-call**, with a final
response of 12–315 characters:

```
before run 2: len=12   ends: '\nRead\n\n\nBash'
after  run 0: len=178  ends: 'Search(pattern: "...", path: "C:\Users\hawkins")'
```

The controlled test is in `diagnostic-read-granted/`: the same case, the same revision `8c5c27a`,
the same model and run count, in a throwaway worktree where **exactly one field changed across all
81 cases** — `tier-gate-holds.allowed_tools: [] -> ["Read"]`.

| | `allowed_tools: []` | `["Read"]` |
|---|---|---|
| rate | **1/5** | **5/5** |
| output tokens/run | 199–419 (avg ~287) | 541–1043 (avg ~786) |
| duration/run | 2962–5598 ms (avg ~4.3 s) | 9081–14849 ms (avg ~11.6 s) |

The no-tool runs are ~2.7× faster and produce a third of the output. That is a turn ending, not a
model answering badly. **Mechanism:** with `Read` granted the agent's inspection attempt returns an
ordinary tool error (the fixture path does not exist), which it handles and continues past to the
packet — satisfying both `must_match` patterns. With `Read` denied it receives a permission denial
and the turn stops before the packet exists. The agent is doing what its prime directives require
("Validate before apply", and GATE-006's new lab-profile read); the harness ends the turn for it.

## What this does and does not undercut

25 of the 27 cases in this lane declare `allowed_tools: []`, as do 56 of the suite's 81 — so the
exposure is not one case. The four transport/declaration cases GATE-006's spec cites as `0/5`
motivation are all tool-denied, and their zeros are suspect for the same reason.

It does **not** undercut GATE-006's decisions. The gate is proven at runtime by
`scripts/probe_plugin.py` — it denies the gated agent's live verb under `dontAsk` and ignores the
main loop's identical one — and the authority arguments stand on the documented host contract. The
rates motivated the work; they never carried it. The correction is recorded in the decision record's
Context section.

Tracked as **EVAL-011**, which also gates **CTX-005**: a diet that cuts always-loaded body on these
rates would be biased against exactly the inspect-first prose the body exists to carry.

## Contents

- `before/tier/`, `after/tier/` — the 20-session calibration slice.
- `diagnostic-read-granted/` — the 5-session controlled test. Not a lane artifact; its contract
  differs from the committed one by the single field named above, so it is never a before/after side.
- `failing-run-evidence.json` files hold raw model text and are **gitignored**
  (`.gitignore:28`), so they exist only in the tree that ran the capture — they are not in this
  commit and a clone will not have them. They were read to establish the finding above, and the
  response lengths and endings quoted here are the load-bearing part of what they contained.
  Re-running the slice regenerates them.
