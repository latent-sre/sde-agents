# CI hardening — the rules beyond the four

Read when writing or reviewing a workflow beyond the basics, and before standing up a self-hosted
runner. The four rules that prevent the real incidents live in
[`SKILL.md`](../SKILL.md); on any conflict, SKILL.md wins. Everything here is breadth — each item
is independently checkable, so read the one you need rather than the file.

## Run control

- **Concurrency**: cancel superseded runs
  (`concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }`)
  so a busy branch doesn't queue ten builds.
- **Timeouts on every job** (`timeout-minutes:`) — a hung job holds a runner until the platform's
  6-hour cap.
- **Fail the build on the checks you care about.** A workflow with `continue-on-error` everywhere
  is a status badge, not a gate.

## Caching

**Cache the dependency store, not the build output**, and key it on the lockfile hash. A cache key
that ignores the lockfile serves stale dependencies — a debugging nightmare that presents as
flakiness.

**Never cache anything derived from untrusted PR code into a shared key.** That is a cache-poisoning
path from a fork into your trusted builds.

## Reproducibility

**Pin the runner image** (`ubuntu-24.04`, not `ubuntu-latest`) when reproducibility matters —
`latest` moves and breaks builds on the platform's schedule, not yours.

## Secrets

- **Per-job, never echoed.** Don't pass a secret as a command-line argument — it shows in process
  listings. Use `env:` or stdin.
- **Prefer OIDC** (`id-token: write` plus a cloud trust policy) over long-lived stored credentials
  wherever the deploy target can trust a workload identity. A LAN target takes the same rule
  through whatever its transport is: a dedicated, job-scoped credential (an SSH key when SSH is the
  transport), never a reused operator credential.
- **Fork PRs don't get secrets, by design.** A workflow that requires a secret to pass will always
  fail on fork contributions. Split it: the required checks run without secrets, and the
  secret-needing job runs post-merge or on a label.

## Linting the workflows

`actionlint` for correctness — it catches expression and shell errors CI would otherwise find at
runtime — and `zizmor` for the security patterns.

Run them locally when you edit a workflow. Promote them to CI jobs once workflows change often
enough that finding the error at runtime costs more than the jobs do.
[`assets/ci.reusable.yml`](../assets/ci.reusable.yml) pre-wires them for that case: CI checking the
CI is worth a job when someone else's edit can break it, not on a repository where the only author
already ran the linter.

## Release integrity, once the artifact leaves the lab

Generate build provenance/attestation and an SBOM **in the release job**, so a consumer can verify
what they got. The payoff is a consumer who cannot just ask you — a public image, a published
package, a release a stranger pulls.

For an image only your own hosts pull, the build is the answer **only when deployment pins the
built digest**. A mutable tag through a registry is a boundary where different bytes can come back,
so pin the digest or keep the attestation.

## Self-hosted runners

A self-hosted runner executing untrusted PR code is **remote code execution on your own hardware,
persisting between jobs**. So:

- **Never run fork PRs on a self-hosted runner** — restrict it to trusted branches and post-merge
  jobs.
- Make it **ephemeral** (`--ephemeral`, one job then re-register, or a container/VM per job) so
  nothing survives into the next job.
- Give it **no standing credentials** beyond the job's.
- Put it on a **segmented network** — a lab runner that can reach every host is a lateral-movement
  path.

Standing up a runner in the home lab is an apply under `sde-agents:homelab-platform`'s change
tiers, including the network placement.
