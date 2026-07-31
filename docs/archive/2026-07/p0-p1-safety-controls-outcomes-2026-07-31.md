# P0/P1 fleet safety-control outcomes — 2026-07-31

**Status: completed in the local working tree; not committed or published.** The operator approved
the P0/P1 backlog and required a separate `gpt-5.6-sol` Codex baseline. Work started from clean
`main` at `d50eda62c4fec083f5a5b0b3980f845d7ae0d8a1`, which matched `origin/main` at the freeze.

This record retires SAFE-001's active specification and plan. It is historical evidence, not a
live task list.

## Bottom line

The round landed all eight scoped controls. Generated text is checkout-independent; the fleet has
a mutation-free health doctor; local/private and external/public investigation are split at the
tool layer; runtime claims use typed evidence and durable state; verification has a pinned,
networkless container runner; agent-mediated live effects require a separately held one-shot
approval; and host/model conformance is reported without blending unavailable hosts into passes.

The controls do not turn one unrestricted OS identity into separate principals. The run database,
approval key, replay ledger, and engine socket must remain under operator-owned identities and ACLs
outside worker authority. When that placement is unavailable, the fleet now degrades explicitly
instead of claiming enforcement from prose.

## What landed

| ID | Outcome and consequence |
|---|---|
| SAFE-P0-001 | Text resources are decoded as UTF-8 and normalized to LF before generation; invalid UTF-8 fails and binary assets remain byte-exact, eliminating checkout-EOL drift without corrupting binary content. |
| SAFE-P0-002 | `scripts/fleet_doctor.py` inventories Git, generated outputs, manifests, CLI/install posture, junctions, the Claude guard, and Codex-agent sync through a command allowlist with Git optional locks disabled; it never repairs. |
| SAFE-P1-001 | New `repository-investigator` has only local read/search tools; `researcher` has only public/external evidence tools; `application-security-auditor` is local and static. The caller combines provenance-labeled packets. |
| SAFE-P1-002 | `scripts/evidence_envelope.py` validates schema-versioned JSON that binds producer, context IDs, immutable target, direct argv, timestamps, status, environment/isolation facts, artifact digests, and limitations while rejecting secret-bearing keys. |
| SAFE-P1-003 | `scripts/run_state.py` stores append-only events plus transactional run/task/attempt projections, optimistic versions, leases, heartbeat, cancellation, supersession, and evidence-linked completion in SQLite outside the workspace. Completion evidence must match context and output revision; successful completion requires pass evidence. |
| SAFE-P1-004 | `scripts/verification_sandbox.py` requires a digest-pinned local Docker/Podman image, disables pulls and network, mounts source read-only and scratch read-write, runs non-root with dropped capabilities, applies limits/timeouts, forces cleanup, checks residue, and emits typed evidence. |
| SAFE-P1-005 | `scripts/effect_broker.py` signs one exact action/target/argv/executable digest with expiry and nonce, reserves replay state atomically before execution, rejects shell interpreters and secret environment keys, and runs direct argv only. The agent prepares requests; an operator-owned mediator approves and executes. |
| SAFE-P1-006 | `evals/conformance/hosts.json` and `scripts/probe_hosts.py` give Claude, Codex, Copilot, and VS Code a common pass/fail/inconclusive/skip result shape, separating static, discovery, behavioral, and model lanes. |

The canonical runtime handoffs are wired into `verification-engineer`, `homelab-platform`, and the
`sre-tool` skill. Generated Copilot/VS Code and Codex copies replace Claude plugin-root paths with
an operator-provided trusted-control requirement because those packages do not ship repository
scripts. Validator mutation tests prevent either end of that wiring from disappearing silently.

## Verification evidence

### Deterministic gates

- `python -X utf8 scripts/generate_platform_adapters.py --check` — passed; 172 generated files are
  current.
- `python -X utf8 scripts/validate_fleet.py` — passed; 11 agents and 19 skills, current inventory.
- `python -X utf8 -m unittest discover -s tests -v` — passed; 273 tests, 14 skipped because the
  Windows host has no POSIX `sh` for those hook-wrapper unit cases.
- `claude plugin validate . --strict` — passed on Claude Code 2.1.220.
- `git diff --check` — passed.

The Windows hook skips are not presented as unit-test coverage. The independent live Claude probe
below exercised the installed runtime path and guard oracle; Linux/macOS/Windows CI remains owed
only when the change is committed and pushed, which this round was not authorized to do.

### Routing and behavioral evidence

The investigation description baseline used identical conditions before and after: Claude Code
2.1.220, requested model `opus`, observed `claude-opus-5`, three runs per case, 420-second timeout,
and clean-room configuration.

- Thirteen common cases had no nonzero rate delta: all five negatives remained clean at 3/3 and
  all eight agent positives remained at 0/3, the already documented headless-agent under-fire
  behavior.
- The two new `repository-investigator` positives also fired 0/3. They have no pre-change analog
  and are not represented as improved positive routing.
- Evidence: [`routing-comparison.json`](../../../evals/baselines/2026-07-31-p0-p1/routing-comparison.json),
  plus its linked before/after benchmark files.

Affected behavioral contracts used `opus`, one clean-room run, and direct component selection:

- Tier/effect broker: 2/2 passed, including refusal to place the key/ledger in the repository.
- Verification: four unique contracts passed. The first isolated-execution run exposed a brittle
  matcher that omitted the correct word “boundary”; a reproduced response showed the safety
  contract held, the matcher was minimally corrected, and the fresh rerun passed 1/1.
- Homelab dry-run classification: 1/1 passed.
- `sre-tool` durable-state degraded mode: 1/1 passed.

The failed pre-fix matcher artifact is retained beside the passing rerun so the correction is
auditable rather than overwritten.

### Host and model evidence

- Static packaging: Claude, Codex, Copilot, and VS Code all passed with 11 agents and 19 skills and
  no adapter issues.
- Claude live behavior: 14/14 passed in 425 seconds — namespaced agents loaded, craft skills were
  preloaded rather than fetched, plugin-root paths expanded, the read-only guard denied the
  reviewer but ignored the main loop, and the conditional API reference was read.
- Codex `gpt-5.6-sol`: passed the fixed 11-agent inventory oracle on Codex CLI 0.145.0 in 15.969
  seconds. Conditions were explicit `gpt-5.6-sol`, high reasoning, read-only sandbox, ephemeral
  session, ignored user config, and no optional features or pro mode. The CLI did not expose an
  observed-model field, so the artifact records that absence instead of copying the requested
  model into observed evidence. Usage was 47,037 input, 22,016 cached input, 243 output, and 120
  reasoning-output tokens. The lane follows the official
  [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/model-guidance?model=gpt-5.6-sol).
- Live discovery: VS Code passed; Claude and Codex were inconclusive because their readable plugin
  inventories do not contain `sde-agents`; Copilot was skipped because its CLI is unavailable.
- Evidence: [`host-conformance/`](../../../evals/baselines/2026-07-31-p0-p1/host-conformance/).

### Runtime-control evidence

- A live Docker 29.6.1 smoke used local
  `alpine@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b`.
  Direct `/bin/touch /scratch/probe` passed with network none, no pull, read-only root/source,
  non-root UID, dropped capabilities, resource limits, writable scratch, forced cleanup, and no
  container residue.
- Unit tests cover typed-envelope schema failures; state version, lease, cancellation,
  supersession, context/revision, and append-only failures; sandbox option placement, timeout,
  engine-start versus command-exit classification, and residue; and effect tamper, expiry,
  executable drift, replay, concurrent exactly-once consumption, key/ledger placement, shell, and
  secret-environment rejection.

## Current host posture found by the doctor

The doctor correctly exits nonzero on one external-state failure rather than repairing it:

- Claude and Codex CLIs are available; Copilot is absent; VS Code is available.
- `sde-agents` is not installed in Claude or Codex plugin inventory.
- Claude's daily junction deployment bypasses plugin namespacing, leaving the plugin-scoped guard
  dormant in normal junction sessions.
- Seven unmanaged user-level Codex custom-agent files conflict with generated fleet role names.
- `skills/backend-craft/assets/openapi.starter.yaml` contains CR bytes in this checkout. Generation
  now normalizes it deterministically, so this is a checkout-policy warning rather than adapter
  drift.

These are deployment choices or user-scope conflicts outside SAFE-001. They remain visible under
the deferred DEPLOY-001 decision; this round did not install, overwrite, or delete user state.

## Deliberately not done and residual limits

- No commit, push, pull request, tag, release, plugin installation, junction replacement, or
  user-level Codex-agent overwrite was performed.
- No live home-lab effect was brokered. Broker tests use temporary helper executables, keys, and
  ledgers only.
- The broker uses an HMAC because public-key/operator-service infrastructure was out of scope. It
  is enforceable only when the signing key and replay ledger are genuinely outside agent identity.
- Network-enabled verification remains unsupported; those criteria are inconclusive until an
  independently enforced destination allowlist exists.
- Host static conformance proves packaging contracts, not equivalent runtime enforcement. Codex
  custom-agent tool narrowing remains cooperative when parent authority overrides its sandbox;
  Copilot/VS Code were not live behaviorally driven on this host.
- Routing agent positives remain unsuitable as an absolute quality score in one-shot headless
  mode. Negative seams and pinned behavioral contracts remain the load-bearing evidence.
