# 2026-07-30 PR 48 review fixes — routing evidence

The added `pos-diagnose-idle-lab-failure` case pins the review-reported boundary: a stopped live-lab
service with no current user impact is diagnosis work (`root-cause`), while the existing
`neg-lab-outage` case keeps a user-affecting outage on `lab-incident`.
`neg-idle-failure-not-incident` adds the deterministic other half in `homelab-ops`: regardless of
whether headless mode fires `root-cause`, it must not fire `lab-incident` when nobody is affected.

Conditions intended for both sides: CLI 2.1.220, `--model opus --timeout 420 --clean-room`,
three runs per case.

## Before

`before/investigation/benchmark.json` captured the branch with the new case present and
root-cause's pre-fix description:

- all seven positives, including the new case, fired their expected member in 0/3 runs;
- all four negatives were clean;
- `neg-lab-outage` fired `lab-incident`, the correct non-member destination.

This is the suite's documented headless agent/skill under-fire mode. The new positive is therefore
non-discriminating and does not prove the old description misrouted.

## After

The first after attempt is deliberately not stored as a benchmark. Every session returned
`is_error: true` with `Failed to authenticate: OAuth session expired and could not be refreshed`;
the runner then graded those error results as ordinary empty firings. Treating that output as four
clean negatives would be false evidence, so the artifact was removed.

The description change still owes a like-for-like after capture once Claude authentication is
refreshed. Even a valid 0/3 → 0/3 positive pair would show only that no negative regressed; it would
not demonstrate improved positive routing. A forced-choice or native plugin eval is needed to
measure the current-impact predicate directly. The new narrowed `homelab-ops` negative also owes
its before/after run; it was added after authentication failed and has not been measured.
