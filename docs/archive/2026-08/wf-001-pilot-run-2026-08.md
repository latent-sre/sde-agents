# WF-001 pilot acceptance run — 2026-08-01

**Status: historical outcome evidence** for the WF-001 round's acceptance criterion "one
end-to-end pilot run on a real diff with session model and token cost recorded." Never a task
list.

## Conditions

- Workflow: `/sde-agents:deep-review` with args `main`, loaded from the working tree
  (`--plugin-dir .`), reviewing this round's own branch diff — 18 changed files at head
  `a487821`, clean tree.
- Session: headless (`-p`, `bypassPermissions`), **sonnet** (CLI flag plus `ANTHROPIC_MODEL`,
  per the round spec's test-modes policy); workflow agents are `model: inherit`, so all three
  lanes ran sonnet.
- CLI 2.1.220.

## Measurements

| Metric | Value |
|---|---|
| Wall time, invocation to returned JSON | 675 s |
| Session cost (all three lanes + main turn) | $3.96 |
| Agents spawned | 3 (guarded scope, review lane, security lane) |
| Schema retries | **0** — exactly one `StructuredOutput` call per agent transcript |
| Verdict | `do-not-merge`, `confirmed_criticals: 1`, bound to `head_sha a487821` |

The zero-retry result resolves the spec's "schema-retry economics" risk favorably at pilot
scale: the packets validated first try on every lane.

## The verdict was correct — and acted on

The pilot's first real act was catching a genuine defect in the round that built it. All three
findings were `[verified]` and all three were accepted and fixed:

- **P1 (review lane, the critical):** the shipped probe proved guard *delivery* only — its sole
  in-workflow command was allowlisted `cat`, which can never be denied, while the spec's
  acceptance evidence requires the attempt-and-deny oracle. Fixed in `b548ab5`: the guarded lane
  now also attempts non-allowlisted `sort`; the hook-log entry proves the attempt and the
  guard's own message marker in the stream proves the denial. Probe after fix: **19/19 PASS**.
- **P2 (review lane):** the roadmap's WF-001 "Next action" still said "start at Task 2" inside
  the diff that was already executing the tasks. Fixed in the wrap-up commit.
- **P3 (security lane):** the acceptance-evidence run logs (`.pilot-run.jsonl`, `.probe-run.log`)
  were untracked and unignored; raw session streams can carry repository content. Ignored in the
  wrap-up commit, distilled numbers recorded here.

The `do-not-merge` verdict binds to `a487821` — the head at which it was true. The P1 fix landed
after that head, which is exactly the re-review discipline the reviewer packet's provisional
form encodes.

## Reading for the next conversion decision

One review pipeline run ≈ $4 and ~11 minutes on sonnet at an 18-file diff, with zero schema
friction and a materially correct verdict. That is the unit economics a future decision about
converting further prose pipelines should start from.
