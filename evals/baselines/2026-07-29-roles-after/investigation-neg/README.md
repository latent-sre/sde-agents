# Regraded 2026-07-29 — grading scope, not measurements

Why this exists: the sessions behind this artifact ran while the three pre-existing negatives
still carried explicit `expect_not_fires` lists written before `application-security-auditor`
joined the cluster, so their `detail` strings showed a three-member grading scope that would have
let the new member fire without failing the case. The cluster spec then moved those negatives to
the documented whole-cluster default (the same-day homelab-ops lesson), which made this artifact's
recorded scope stale against the spec it anchors.

No new sessions were run for the regrade, and none were needed: `fired_per_run` records every
fleet component that fired in each run (that is why `neg-lab-outage` shows `lab-incident`, a
non-member), so regrading is deterministic. The recorded runs were re-scored with the runner's own
`score_case` against the then-current four-member cluster. `application-security-auditor` fired in 0
runs of every case; every verdict, rate, and the 4/4 summary are unchanged — only the grading
scope shown in `detail` now matches the spec. `conditions.plugin_dir` was also normalized to `.`
in the same pass;
the original absolute path recorded local-machine layout, which is identity noise, not a
measurement condition.
