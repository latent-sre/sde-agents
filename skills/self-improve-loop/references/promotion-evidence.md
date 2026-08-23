# Promotion evidence: the conditions a comparison depends on

Expansion of gate 3 ("fresh evaluator, comparable conditions") in [SKILL.md](../SKILL.md). The
gate itself is stated there and is binding; this file records *which conditions must be captured*
and why each one changes the result.

## Record every condition, by hand or via the repository's eval harness

- **Model**, with the timeout pinned to it
- **Runtime and version** (CLI or SDK build)
- **Exact artifact** — the bytes evaluated, not the branch name
- **Grader** — which oracle judged it
- **Seed or repetitions** — how many runs the rate is over
- **Budget** — session or token ceiling in force
- **Configuration state each run inherited** — clean-room, or the ambient one

## Why these are not bookkeeping

A shorter timeout **drops runs out of every rate**: a run that times out is not a run that failed
the contract, but an unrecorded timeout change makes the two indistinguishable, and the rate moves
for a reason that has nothing to do with the candidate.

Clean-room and ambient runs **measure different competitions**. An ambient run inherits the
user's personal agents, skills, plugins, and global instruction files; a clean-room run does not.
The same candidate can win one and lose the other without changing.

Therefore: **results differing on any recorded condition must not be diffed.** Two artifacts that
disagree on even one of these are not a pair, and presenting them as before/after is a
measurement error, not a finding.

## Rates, not booleans

Results are rates over runs. A change inside the measured noise is **inconclusive**, not a small
win — report it as inconclusive and say what would settle it. Re-running until the number moves
the desired direction is the failure mode this framing exists to block.
