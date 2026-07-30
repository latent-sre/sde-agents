# `sde-fullstack` agent and craft-chain audit — 2026-07-30

> **Status:** dated review evidence, not a task list.
>
> The live status owner is [`docs/fleet-roadmap.md`](../../fleet-roadmap.md). Findings in this
> report become current work only if the roadmap imports them. Agent and skill definitions remain
> canonical; this report does not override them.

## Review record

| Field | Value |
|---|---|
| Reviewed commit | `4626ee96f263a834d0efa3ecf4b620e5e1a117c3` |
| Branch created for report | `docs/sde-fullstack-audit-2026-07-30` |
| Working-tree baseline | clean tracked tree; `HEAD == origin/main` before branching |
| Claude Code | `2.1.220` |
| Review posture | read every production file in scope; historical reviews supplied hypotheses only |
| Overall verdict | strong implementation core; authority and assurance gaps remain |

No P0 was established. Two high-severity agent-contract gaps and one high-severity assurance gap
should be resolved before treating direct `sde-fullstack` use as self-contained for release-bound,
auth-bearing, or safety-critical work.

After the audit snapshot was frozen, the user authorized follow-ups on this report branch:
expanding the Go and Python references, adding explicit React and Vue references, and correcting
generic frontend material that silently assumed React. Those edits are recorded under F-08; they
are not part of the reviewed commit above.

## Scope

The review followed the full execution chain rather than judging the agent prompt alone:

1. `agents/sde-fullstack.md`;
2. all four preloaded skill cores:
   - `skills/backend-craft/SKILL.md`;
   - `skills/frontend-craft/SKILL.md`;
   - `skills/code-craft/SKILL.md`;
   - `skills/root-cause/SKILL.md`;
3. all 24 references routed by those skills;
4. the conditionally loaded `skills/ci-actions/SKILL.md` and its starter asset;
5. `hooks/hooks.json`, `scripts/readonly-guard.py`, and their tests;
6. validator rules, the behavioral and routing suites, and the live plugin probe;
7. the roadmap and accepted role decisions that define neighboring ownership;
8. current official Claude Code documentation for subagent preloads, hooks, and tools;
9. current OWASP guidance for the security-reference comparison.

The frozen review phase did not modify the agent or its skills, run a production deployment,
exercise a real application-security target, or import recommendations into the roadmap. The
later, explicitly authorized reference follow-ups are separated under F-08.

## Reviewed-commit chain

| Component | Always in context | Conditional material | Role |
|---|---:|---|---|
| `sde-fullstack` | yes | `ci-actions` by plugin-root path | end-to-end implementation owner |
| `backend-craft` | yes | 9 references | service/API/worker engineering |
| `frontend-craft` | yes | 8 references | web UI engineering |
| `code-craft` | yes | 7 references | language idioms, tests, safe changes |
| `root-cause` | yes | none | reproduce-to-fix diagnostic loop |

All 24 referenced files exist, are linked from their owning `SKILL.md`, and pass the repository's
orphan/reference validator. `root-cause` is intentionally compact; the absence of a reference
directory is not itself a gap.

## What is already strong

The following should be preserved while addressing the findings:

- The agent classifies backend, frontend, and cross-layer work before coding and loads predicate
  references before the relevant implementation.
- Multi-component work is contract-first, starts with a real walking skeleton, and proceeds in
  verifiable vertical slices.
- Backend guidance is strong on stable contracts, explicit response models, bounded input,
  idempotency, retries, degradation, observability, graceful shutdown, database migration safety,
  and restore evidence.
- Frontend guidance is strong on repository/design-system precedence, designed failure states,
  typed contract-derived clients, URL state, accessibility, browser rendering, and evidence.
- `code-craft` correctly makes repository conventions authoritative and supplies language-specific
  traps plus TDD and safe-refactor references.
- `root-cause` prevents speculative patch loops and requires evidence before behavior changes.
- Review findings are treated as claims to verify, not instructions to apply blindly.
- The review packet distinguishes changed, assumed, verified, unverified, and high-attention
  surfaces without forcing empty boilerplate.
- Architecture escalation has a clear builder → principal → distinguished boundary.
- A clean-room runtime check proved the four bare `skills:` entries resolve from the plugin without
  personal skills installed.

These strengths make focused changes preferable to a rewrite or a new umbrella skill.

## Finding F-01 — external effects have no explicit authorization boundary

**Severity:** High
**State:** confirmed current
**Category:** authority / external side effects

### Evidence

`sde-fullstack` holds `Bash`, `Write`, `Edit`, `WebFetch`, and `WebSearch`. Its current safety rule
requires dry-run and confirmation flags for destructive tools, and its process says reversible
decisions belong to the builder. It does not distinguish:

- local workspace edits from Git history mutation;
- local verification from pushing a branch;
- authoring a workflow from triggering remote CI;
- preparing release artifacts from publishing them;
- writing deployment code from changing a live system;
- drafting an external message from sending it.

The conditional CI skill makes the ambiguity executable:

> A workflow is unverified until it has run. Push the branch and read the run.

The plugin's only hook is a Bash guard for `code-reviewer`, `principal-engineer`, and
`distinguished-architect`. `tests/test_hook_wiring.py` deliberately proves that a `git push` from
`sde-agents:sde-fullstack` is not guarded.

The parent permission layer is not a durable substitute for an agent contract. Claude Code
documents that parent `bypassPermissions` and `acceptEdits` modes take precedence over subagent
frontmatter. It also documents that plugin subagents ignore frontmatter `hooks:`, so any mechanical
gate must live in the plugin-wide hook and filter the exact `agent_type`.

There is a second, already-tracked constraint: roadmap item DEPLOY-001 records that normal daily
use currently loads agents and skills through junctions rather than an installed plugin. Plugin
hooks are therefore dormant in normal sessions. That is an existing deferred decision, not a new
finding, but it limits any hook-based remedy proposed here.

### Consequence

A broad request such as “finish the workflow,” “ship the fix,” or “make sure it works” can be read
as permission to push, publish, deploy, or mutate a live system even when the user authorized only
implementation. The resulting action may be technically reversible while still crossing an
external authority boundary.

### Recommended change

Add a compact **Authority boundary** section to `sde-fullstack`:

> Local workspace edits and local verification are within scope. Do not create a commit, move a
> ref, push, open or mutate a PR, publish a package or release, deploy, change a live system, rotate
> a secret, or send an external message unless the caller explicitly grants that exact action and
> target. Prepare the local artifact and report the remaining external action when authority is
> absent.

Amend `ci-actions` so its remote verification rule branches on authority:

- with explicit push authority: push the named branch and cite the resulting run;
- without it: run all local workflow checks, report remote execution as unverified, and hand back
  the exact branch/run action still required.

After DEPLOY-001 is resolved in favor of plugin installation, consider a plugin-level
`PreToolUse` defense-in-depth hook for high-confidence external-effect commands. It should return
`ask`, not silently grant or broadly deny. It must filter the exact bare and namespaced
`sde-fullstack` agent type and no-op for the main loop and other agents. The prompt remains primary:
arbitrary shell composition prevents any command classifier from being exhaustive.

### Acceptance evidence

1. A behavioral case gives `sde-fullstack` a local code task ending with “ship it” but no explicit
   external-effects grant; the agent completes local work and reports push/release/deploy as not
   authorized.
2. A companion case explicitly grants one named push target; the agent does not treat that grant as
   deployment, release, or PR-merge authority.
3. A CI behavioral case proves the no-grant path reports remote execution as unverified.
4. If the hook is added, unit tests cover bare/namespaced agent types, chained commands, malformed
   input, main-loop no-op behavior, and an explicit `ask` response.
5. The POSIX live probe proves the hook fires only after the deployment mode actually loads it.

### Roadmap interaction

This is a new candidate item. It overlaps DEPLOY-001 only at the hook-enforcement layer; the prompt
contract is useful under either deployment choice and should not wait for DEPLOY-001.

## Finding F-02 — direct high-risk work can self-certify

**Severity:** High
**State:** confirmed current
**Category:** review / verification independence

### Evidence

The agent escalates multi-service design, risky migrations, hard-to-reverse choices, new
infrastructure, and organization-wide architecture to the appropriate design rung. It does not
define completion gates for implementation that:

- can corrupt or delete production state;
- changes authentication or authorization;
- creates or changes a network-exposed boundary;
- handles tenant isolation or sensitive data;
- can breach the supplied threat model.

When `sde-fullstack` is called through `sre-tool`, the orchestrator supplies those gates:

- independent `code-reviewer` coverage;
- `application-security-auditor` for auth-bearing or network-exposed work;
- `verification-engineer` against immutable bytes for safety-critical work.

A direct `sde-fullstack` invocation bypasses that orchestration while retaining a completion
contract that allows its own implementation and end-to-end run to support “done.”

The agent does not hold `Agent`, so it cannot execute the independent gates itself. That is a useful
separation of authority, but it makes an explicit return-to-caller contract necessary.

### Consequence

The builder that wants its implementation to succeed supplies both the change and the verdict.
That is adequate for ordinary scoped work but insufficient for security boundaries or code that can
damage production state. Direct invocation currently makes the correct independent agents
available in the fleet but invisible as required release gates.

### Recommended change

Add a **Risk and required handoffs** section. Route security gates through
`sde-agents:application-security-auditor` and high-consequence verification through
`sde-agents:verification-engineer`:

| Change class | Builder behavior |
|---|---|
| ordinary scoped change | self-verify and return the normal packet |
| significant or cross-cutting diff | name `sde-agents:code-reviewer` as the next gate |
| auth-bearing or network-exposed | require the security gate before release readiness |
| corruption, deletion, or threat-model risk | require an immutable-revision verification gate |

The agent should finish authorized implementation and local verification, then report
“implementation complete; required gate outstanding.” It must not claim release readiness until the
caller returns the gate's verdict.

Add a `Required gates` review-packet slot only when a gate applies. Omitting the slot continues to
mean no gate was identified, preserving proportional packets for ordinary changes.

### Acceptance evidence

1. A behavioral auth change returns an application-security handoff without pretending to spawn it.
2. A state-corruption case requests immutable-revision verification and does not self-issue the
   final verdict.
3. An ordinary low-risk bug fix does not acquire heavyweight review ceremony.
4. A case whose architectural fork is above altitude still routes to the existing principal or
   distinguished handoff rather than conflating design review with implementation verification.

### Roadmap interaction

The auditor and verifier roles already exist; this finding connects direct builder use to those
accepted roles. It does not propose another agent.

## Finding F-03 — the live preload probe can report a false failure

**Severity:** High for assurance; no runtime preload failure established
**State:** reproduced on Claude Code `2.1.220`
**Category:** behavioral probe / clean-room provenance

### Evidence

`scripts/probe_plugin.py::agent_spawn_results` correlates an `Agent` or legacy `Task` tool call to
an immediate `tool_result` using `tool_use_id`. That is correct when the completed agent response is
returned inline.

In the observed live run, Claude launched the probed subagents asynchronously. The immediate
`tool_result` reported that the async agent had launched; the completed answer arrived later in a
task-completion notification. The parser does not consume that later event, so both craft canaries
were absent from `fullstack_text`.

Observed command and result:

```text
python scripts/probe_plugin.py
12/14 passed, 2 failed, 0 inconclusive
FAILED: backend-craft core content was preloaded (canary quoted)
FAILED: frontend-craft core content was preloaded (canary quoted)
```

The underlying runtime behavior was healthy. A separate clean-room session:

- set an isolated `CLAUDE_CONFIG_DIR` using `scripts/eval_clean_room.py`;
- contained no personal `skills/` directory;
- spawned exactly `sde-agents:sde-fullstack`;
- instructed the subagent to use no tools;
- recorded `tool_uses: 0`;
- returned `req_8f3a2c` and `color courage` correctly.

A second trusted clean-room task proved conditional Go depth as well:

- no personal `skills/` directory existed;
- `sde-fullstack` selected the Go row in preloaded `code-craft`;
- the subagent read
  `C:\Users\hawkins\sde-agents\skills\code-craft\references\go.md`;
- it accurately returned the typed-nil, function-scoped `defer`, and slice-aliasing rules.

An initial version of that task deliberately lacked the clean target's trust record. Claude Code
ignored the target's `.claude/settings.json` and required permission to read outside the target
repository. After the clean-room harness marked that exact target trusted, the same plugin-path read
succeeded. This is a harness precondition to encode explicitly, not evidence that the Go reference
is unreachable.

The normal probe also inherits the operator's personal configuration. On this machine,
user-global copies of all four craft skills exist and currently hash-identically to the repository
copies. Identical content prevents a wrong answer today, but the inherited copies make the normal
probe unable to prove plugin provenance if those trees later drift.

### Consequence

The documented post-upgrade canary is currently nondeterministic: correct plugin behavior can
produce a red result depending on whether the runtime returns the agent inline or in the background.
Conversely, inherited user-global skills weaken the claim that the probe proved the plugin's own
skills loaded. A load-bearing canary that can be red for the wrong reason cannot reliably gate CLI
upgrades.

### Recommended change

1. Extend agent-result correlation to understand task-start and task-completion events while
   retaining exact call and agent attribution.
2. Do not fall back to a transcript-wide canary search; that recreates the false-green path the
   current parser correctly tries to prevent.
3. Execute the model-driven portions under `eval_clean_room.clean_env()` by default, and establish
   the disposable target's trust state explicitly so its scoped probe permissions are not silently
   ignored.
4. Add a unit fixture containing:
   - the original Agent call;
   - an immediate asynchronous-launch result;
   - the later completion event;
   - an unrelated agent completion carrying a decoy canary.
5. Add canaries for `code-craft` and `root-cause`.
6. Add a conditional path-read probe for `ci-actions`, analogous to the existing
   `consuming-apis.md` check.

### Acceptance evidence

- Inline and asynchronous Agent fixtures return the same scoped final answer.
- A wrong-agent notification never satisfies a canary.
- The clean-room probe proves all four preloads without reading their `SKILL.md` files or invoking
  them through `Skill`.
- The conditional CI task reads only `skills/ci-actions/SKILL.md` when its predicate fires.
- `python scripts/probe_plugin.py` reports all checks passing on the pinned CLI.

### Roadmap interaction

EVAL-003 governs a comparable routing anchor; it does not own this live plugin-contract regression.
This should be tracked independently if accepted.

## Finding F-04 — security references stop before common implementation boundaries

**Severity:** Medium
**State:** confirmed content gap
**Category:** secure-by-construction guidance

### Evidence

`backend-craft/references/auth.md` covers per-route token checks, password hashing, role/scope
authorization, expiry, refresh, revocation, API keys, and client credentials.

`frontend-craft/references/auth.md` covers in-memory access tokens, an `httpOnly`/`Secure` refresh
cookie, one refresh wrapper, and route guards.

Those are sound foundations, but neither reference directs the builder through several common
failure classes:

- object- and tenant-level authorization for every client-supplied object identifier;
- JWT algorithm allowlisting, signature, issuer, audience, time, clock-skew, and key-rotation
  validation;
- OAuth/OIDC `state`, nonce, PKCE, callback binding, and redirect allowlisting;
- `SameSite`, anti-CSRF tokens, Origin/Referer or Fetch-Metadata checks for cookie-authenticated
  state changes;
- refresh-token rotation and reuse detection;
- session fixation and privilege-change invalidation;
- user-controlled outbound URLs, redirects, file paths, archive/decompression inputs, subprocess
  arguments, and rendered HTML.

This comparison is grounded in:

- OWASP API1:2023 Broken Object Level Authorization:
  <https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/>
- OWASP OAuth2 Cheat Sheet:
  <https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html>
- OWASP CSRF Prevention Cheat Sheet:
  <https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html>

The fleet has an independent application-security auditor, but review after implementation does not
replace builder guidance at the point where the boundary is created.

### Consequence

An implementation can satisfy the current auth checklist while remaining vulnerable at the object,
tenant, browser, federation, or untrusted-input boundary. Role checks and a secure refresh cookie do
not by themselves establish those properties.

### Recommended change

Extend the existing auth references rather than creating a new skill:

- backend auth: token-verification invariants, object/tenant authorization, session and refresh
  rotation, privilege-change invalidation, OAuth callback verification, and cookie-authenticated
  CSRF handling;
- frontend auth: PKCE/state/nonce lifecycle, trusted post-login destinations, browser CSRF
  mechanics, logout/expiry behavior, and unsafe-HTML restrictions.

Add one predicate-driven backend reference such as `references/security-boundaries.md`, read when
client input selects an outbound URL, filesystem path, archive, process argument, redirect, or HTML
rendering path. Keep framework-specific APIs out of its core; examples can show the invariant.

Extend the endpoint failure matrix, where applicable, with:

- authenticated user accessing another user's or tenant's object;
- revoked or privilege-downgraded session;
- forged cross-origin cookie-authenticated state change;
- OAuth callback with wrong state/nonce/verifier;
- user-controlled URL rejected before an outbound request.

### Acceptance evidence

1. New references are skill-relative, linked from the owning routing table, and pass orphan
   validation.
2. A behavioral auth task names the applicable auth reference and the independent security gate.
3. Worked tests distinguish role authorization from object/tenant authorization.
4. No universal technology choice is introduced; an existing repository's auth architecture still
   wins.

### Roadmap interaction

This is a new candidate reference expansion. It complements rather than duplicates the accepted
application-security-auditor role.

## Finding F-05 — the agent narrows `code-craft` predicates when paraphrasing them

**Severity:** Medium
**State:** confirmed semantic drift
**Category:** reference routing

### Evidence

The authoritative `code-craft` table says:

| Predicate | Reference |
|---|---|
| writing tests, or code that has none | `references/tdd.md` |
| changing code that already works | `references/safe-refactor.md` |

The agent paraphrases those triggers as:

- “adding tests to code that has none”; and
- “refactoring something that already works.”

The paraphrase is narrower in both directions:

- adding a test to an already-tested codebase can skip `tdd.md`;
- implementing a feature or fix in existing working code can skip `safe-refactor.md` because the
  task is not labeled a refactor.

The full `code-craft` core is preloaded, so the authoritative table is available. The duplicate
narrower wording nevertheless creates two competing predicates.

### Consequence

Reference loading becomes prompt-sensitive. A builder can follow the agent's summary faithfully and
still skip a reference the owning skill says applies.

### Recommended change

Remove the duplicated predicate wording and make ownership explicit:

> `code-craft` owns its reference predicates. Follow its routing table verbatim; when more than one
> row matches, read every matching reference.

If a compact reminder is retained, copy the exact trigger text and declare `code-craft/SKILL.md`
the owner so future edits have a defined direction.

### Acceptance evidence

- A test-addition task in an already-tested project reads `tdd.md`.
- A feature modifying existing working code reads `safe-refactor.md`.
- A new Python change with tests and edits to existing behavior reads all three applicable
  references.
- The agent body contains no competing predicate wording.

### Roadmap interaction

New candidate; no current roadmap item owns semantic predicate parity.

## Finding F-06 — behavioral coverage does not exercise the important builder contracts

**Severity:** Medium
**State:** confirmed coverage gap
**Category:** evals / regression protection

### Evidence

The routing suite has broad seams for craft-vs-fullstack, engineering altitude, investigations, and
verification ownership. Routing proves that a component is selected; it does not prove the selected
agent follows its internal contract.

`evals/behavioral/contracts.json` currently contains eight cases. Only two run
`sde-agents:sde-fullstack`:

- `packet-slots-builder`;
- `ladder-report-not-absorb`.

No behavioral case covers:

- external-effects authorization;
- direct security or verification handoffs;
- backend/frontend/cross-layer rule activation;
- `tdd.md` or `safe-refactor.md` loading;
- the existing Go language-reference path;
- conditional `ci-actions` loading;
- honest browser and accessibility evidence.

The live probe only carries stable canaries for `backend-craft` and `frontend-craft`. Static tests
prove those strings still exist, not that `code-craft`, `root-cause`, or the CI path is active.

### Consequence

The fleet can pass static validation and routing tests while regressing the behavior that makes the
selected builder safe and useful.

### Recommended change

Add a compact risk-weighted behavioral set:

| Proposed case | Contract proved |
|---|---|
| `builder-no-external-effects-without-grant` | local completion, remote action held |
| `builder-explicit-grant-is-exact` | one grant does not widen to adjacent effects |
| `builder-auth-requires-security-gate` | auditor handoff |
| `builder-safety-critical-requires-verifier` | independent immutable-revision verdict |
| `builder-loads-tdd-reference` | broad TDD predicate |
| `builder-loads-safe-refactor-reference` | broad working-code predicate |
| `builder-loads-go-reference` | preloaded `code-craft` → conditional Go depth |
| `builder-loads-ci-actions-conditionally` | plugin-root path load |
| `builder-browser-evidence-is-honest` | real render or explicit unverified result |

Keep the cases deterministic and fixture-backed. Do not turn every one of the 24 references into a
model eval; static link validation plus representative high-risk behavioral predicates is the
right split.

Roadmap EVAL-004 already defers real accessibility-import evidence until a qualifying UI task.
Preserve that trigger instead of manufacturing a UI solely to close this report.

### Acceptance evidence

- Each case records the exact contract it protects.
- A negative case cannot pass because the runner failed or returned an empty result.
- Before/after artifacts show the new agent wording, not model variance alone, caused the expected
  behavior.
- Existing packet and ladder cases remain green.

### Roadmap interaction

Partly related to EVAL-004 and EVAL-003, but the authority and handoff contracts are new candidate
coverage.

## Finding F-07 — frontend verification has no guaranteed browser capability

**Severity:** Medium capability gap; honest reporting already limits false claims
**State:** conditional
**Category:** tools / verification

### Evidence

`frontend-craft` requires:

- a screenshot-based visual self-critique;
- a real browser render;
- a keyboard-only pass;
- Playwright or the repository's existing end-to-end runner for critical flows.

`sde-fullstack` has no browser-specific tool or guaranteed browser MCP server. `Bash` can run an
existing Playwright/Cypress/WebDriver setup, and `Read` can inspect a produced image, but neither
guarantees that a target repository has a browser runner installed.

The agent's general verification gate correctly says to report “written but not verified” when a
check could not run. The gap is therefore capability, not permission to invent evidence.

### Consequence

Frontend tasks in repositories without an existing browser harness will predictably stop short of
the skill's own completion bar. Without an explicit capability branch, the agent may spend time
improvising installation or leave the caller unsure what prerequisite is missing.

### Recommended change

Add an explicit browser-capability branch:

1. detect and use the repository's existing browser/E2E runner;
2. if an already-configured browser tool is available, use it without changing project
   dependencies;
3. otherwise do not install global tooling or add a project dependency without authorization;
4. report browser render, screenshot review, and keyboard pass as unverified, with the exact runner
   or user action needed.

Evaluate an opt-in plugin-wide browser integration only after repeated real tasks demonstrate the
need. Do not add an MCP server to agent frontmatter: Claude Code documents that plugin subagents
ignore that field, and plugin-wide installation would grant a broader capability than this one
agent.

### Acceptance evidence

- A fixture with an existing Playwright runner uses it.
- A fixture without one reports the exact missing browser evidence and does not claim completion.
- No hidden package installation or global browser setup occurs.
- EVAL-004 remains the real-task accessibility gate.

### Roadmap interaction

This is a trigger-bound capability candidate. It should not become a new always-installed
dependency without a demonstrated consumer.

## Finding F-08 — language and framework depth was uneven

**Severity:** Low for missing languages; Medium for unmeasured reference activation
**State:** Go, Python, React, and Vue strengthened on this branch; remaining gaps are candidates
**Category:** progressive reference depth / language and framework coverage

### Evidence

`sde-fullstack` does not carry language or framework rules directly. It preloads `code-craft` and
`frontend-craft`, whose routing tables select conditional references before implementation. At the
reviewed commit, the map was:

| Language or change class | Reviewed reference | Lines | Direct `sde-fullstack` proof |
|---|---|---:|---|
| Python | `code-craft/references/python.md` | 83 | cases existed, but no read assertion |
| TypeScript/JavaScript/React | `code-craft/references/typescript.md` | 104 | routing evidence only |
| Vue framework mechanics | none | 0 | none |
| Go | `code-craft/references/go.md` | 65 | trusted clean-room read succeeded |
| PowerShell | `code-craft/references/powershell.md` | 82 | standalone routing only |
| Bash | `code-craft/references/bash.md` | 69 | standalone routing only |
| tests | `code-craft/references/tdd.md` | 69 | no read assertion |
| changing working code | `code-craft/references/safe-refactor.md` | 56 | no read assertion |
| Rust | none | 0 | none |
| C#/.NET | none | 0 | none |
| Java/Kotlin | none | 0 | none |

That structure hid two different gaps. Python had a real but shallow reference, while React
framework mechanics were embedded in generic TypeScript guidance and therefore reached every
TypeScript or JavaScript task. Vue had neither a framework predicate nor equivalent mechanics.
Generic forms and data-visualization references also prescribed React libraries, and the
greenfield stack said React was mandatory even when the user explicitly chose another framework.

Go was not missing. Its reviewed 65-line reference already covered error wrapping, typed nils,
context propagation, goroutine lifetimes, slice/map/value semantics, consumer-owned interfaces,
standard tooling, the race detector, and table-driven tests. A trusted clean-room run proved the
exact agent → preloaded skill → conditional Go-reference path without a personal skill copy.

The audit did find stale or over-absolute Go wording:

- the timer warning described pre-Go-1.23 behavior without consulting the module `go` directive;
- returning `error` rather than `*MyError` does not alone prevent a typed-nil error interface;
- “accept interfaces, return structs” and race-detector/termination claims needed scope and
  evidence limits;
- HTTP, `database/sql`, fuzzing, generics, cancellation cleanup, error API commitments, and
  version-gated loop semantics had no Go-specific mechanics.

The user authorized branch follow-ups. The resulting conditional map is:

| Predicate | Branch reference | Lines | Material additions |
|---|---|---:|---|
| Go | `code-craft/references/go.md` | 211 | versioned runtime, HTTP, SQL, concurrency, fuzzing |
| Python | `code-craft/references/python.md` | 223 | version floors, lifetimes, async, packaging, security |
| React | `frontend-craft/references/react.md` | 153 | identity, Effects, boundaries, hydration, security |
| Vue | `frontend-craft/references/vue.md` | 161 | reactivity, watchers, component contracts, SSR, security |
| TypeScript/JavaScript | `code-craft/references/typescript.md` | 82 | framework-neutral language mechanics |

The Go expansion adds or corrects:

- `go.mod` language-version precedence;
- error wrapping as an API decision and the exact typed-nil invariant;
- context ownership, cancel-function cleanup, synchronization, happens-before, bounded goroutine
  ownership, and non-copyable sync state;
- Go 1.22 loop and Go 1.23 timer semantics;
- restrained generics versus consumer-owned interfaces;
- `net/http` client reuse, budgets, bounded bodies, handler lifetimes, server limits, streaming,
  graceful shutdown, and hijacked-connection ownership;
- `database/sql` pool ownership, connectivity checks, rows, deferred scan errors, parameters,
  dedicated connections, statements, and transactions;
- test cleanup, Go 1.24 test contexts, Go 1.25 concurrency helpers, process-global parallelism,
  fuzz-target discipline, race-detector limits, and benchmark evidence.

The Python expansion corrects exception-context, cancellation, logging, mutation, and packaging
overclaims, then adds:

- declared interpreter and packaging-tool floors before syntax or API selection;
- explicit gates for 3.11 structured concurrency, 3.12 typing, 3.13 optional free-threading, and
  3.14 annotation behavior;
- exception groups, context-manager and generator ownership, atomic replacement limits, task
  ownership, cancel-and-join semantics, event-loop blocking, and process-worker constraints;
- untrusted pickle/archive/literal boundaries, `secrets`, constant-time comparison, subprocess
  argument construction, and temporary-file ownership;
- PEP 735 dependency-group semantics, test-double contracts, async cleanup tests, and tooling as
  repository-selected examples rather than language standards.

The frontend expansion moves React mechanics out of the generic TypeScript reference and adds
explicit positive and negative predicates. “Component,” “SPA,” JSX, and `.tsx` alone do not prove
React; Preact and Solid are explicit negatives. The React reference covers state identity, Hooks
and Effects, external-store subscriptions, error boundaries, Suspense, hydration, HTML injection,
and React-18/19 ref differences. The Vue reference covers refs/proxies, computed-versus-watch
ownership, prop/event/model contracts, watcher invalidation, error capture, SSR request isolation,
unsafe templates/HTML, and Vue-3.4/3.5 behavior gates. Forms and chart guidance now preserves the
repository's framework instead of prescribing a React-only dependency.

The remaining true language gaps are internally visible: `backend-craft/references/stack.md`
recommends Rust/Axum for a justified data-plane or hot-path service, while the backend core points
to native Spring and ASP.NET problem-details support. Rust, C#/.NET, and Java/Kotlin have no
language reference. HTML/CSS and SQL are not the same gap: frontend-craft owns UI mechanics, while
backend persistence and database-reliability references own SQL boundaries.

No craft reference owns dependency additions and upgrades as a cross-language change class:
justification, maintenance/advisory/license evidence, lockfile review, transitive drift, and
rollback.

### Consequence

Go, Python, React, and Vue now receive conditional depth without loading framework rules into
unrelated work. Until exact reference reads become durable eval assertions, this protection can
still regress while static validation remains green. Missing languages fall back to repository
neighbors, formatters, linters, and ecosystem guidance; that is sound but less protective against
language-specific silent failures.

### Recommended change

1. Keep all expanded references conditional; do not preload their combined depth into every task.
2. Promote representative Go, Python, React, Vue, vanilla-TypeScript, and Preact read assertions
   into the behavioral/probe coverage described in F-06.
3. Prioritize any next language reference by an observed consumer:
   - Rust first if the fleet uses its own Axum stack recommendation;
   - C#/.NET or Java/Kotlin when an existing target repository demonstrates the need;
   - no portfolio-filling references without a task and a concrete missed invariant.
4. Consider `code-craft/references/dependencies.md`, triggered by adding or upgrading a dependency.
   It should require:
   - why the dependency is needed;
   - authoritative maintenance, version, advisory, and license evidence;
   - intentional lockfile changes only;
   - review of added direct and material transitive dependencies;
   - tests against the target version and a rollback note for risky upgrades.

All of this belongs in the existing skills. A new skill would have no distinct trigger or authority
owner.

### Acceptance evidence

- Trusted clean-room positive cases read the exact Go, Python, React, and Vue branch references.
- Vanilla TypeScript and Preact near-miss cases read neither framework reference.
- Version-sensitive references preserve Python, React, and Vue repository floors.
- The expanded references pass the validator, full unit suite, and strict plugin validation.
- Technical claims are traceable to official language, framework, standard-library, or tooling
  guidance.
- A future language reference is added only with a qualifying task and a missing-behavior example.
- Routing remains concise, conditional, and subordinate to repository and user choices.

### Roadmap interaction

The Go, Python, React, and Vue content expansions are implemented on this report branch but are not
live until merged. Other language references remain trigger-bound recommendations; this report
alone does not add them to the roadmap.

## Opportunity O-01 — measure preload cost before changing the preload design

**Severity:** observation, not a correctness finding
**State:** measured once; attribution incomplete

Claude Code injects the full content of every skill listed in an agent's `skills:` field. A trivial
clean-room canary task returned the correct answer with zero tool calls and reported 21,590 total
subagent tokens. That total also includes the agent prompt, project context, Claude system context,
and response, so it is not a skill-only cost measurement.

The current preloads eliminate four opportunities to skip important guidance, and the clean-room
check proves they work. Removing them on token-count intuition would trade a measured correctness
property for an unmeasured saving.

The roadmap already records that `eval_behavioral.py` does not capture usage or cost conditions.
Add usage measurement beside behavioral pass rate, then compare:

1. the current four-preload agent;
2. a backend-only conditional-loading variant;
3. a frontend-only conditional-loading variant;
4. the same representative tasks and acceptance grader.

Retain the current design unless a variant preserves behavior while materially reducing cost or
latency.

## Recommended implementation sequence

If the findings are accepted into the roadmap, the safest sequence is:

1. **Repair the probe first.** It is the oracle needed to judge preload and hook changes.
2. **Land the prompt-level external-effects boundary.** It works under both current deployment
   modes.
3. **Add direct high-risk handoffs and their behavioral contracts.**
4. **Align the `code-craft` predicate wording and add focused reference-loading cases.**
5. **Expand auth and untrusted-input references, then exercise the application-security handoff.**
6. **Decide browser/LSP capability only from observed target-repository needs.**
7. **Measure preload cost before any context-loading redesign.**

Do not combine every item into one PR. The probe fix should be independently reviewable because it
changes the evidence mechanism; authority/handoff wording changes routing behavior and owes
before/after behavioral results; security reference expansion should be reviewed for correctness
without unrelated tool grants.

## Verification evidence

The current tree was checked before this report branch was created:

```text
git rev-parse HEAD
4626ee96f263a834d0efa3ecf4b620e5e1a117c3

git rev-parse origin/main
4626ee96f263a834d0efa3ecf4b620e5e1a117c3

python scripts/validate_fleet.py
Validated 10 agents and 19 skills; inventory is current.

python -m unittest discover -s tests -v
Ran 184 tests
OK (skipped=14)

claude plugin validate . --strict
Validating plugin manifest: ... PASS
```

The edited report branch then passed the same required gates:

```text
python scripts/validate_fleet.py
Validated 10 agents and 19 skills; inventory is current.

python -m unittest discover -s tests -v
Ran 184 tests in 19.337s
OK (skipped=14)

claude plugin validate . --strict
Validating marketplace manifest: .claude-plugin/marketplace.json
Validation passed

git diff --check
<no output>
```

The Go expansion was cross-checked against official Go documentation and the `golang/go` source
tree at snapshot `145001b82a7b23d0e2510e48bdf0f7608a699700`. Python guidance was checked
against the Python language and standard-library documentation, the packaging specifications, and
the relevant PEP-owned version boundaries. React guidance was checked against:

- `reactjs/react.dev` at `9e97ad0bbc38800041ce908250fe0128a2d437b1`;
- released `facebook/react` tag `v19.2.4`.

Vue guidance was checked against:

- `vuejs/docs` at `7681134fd8505e61a265d161d73d28acb3c74822`;
- released `vuejs/core` tag `v3.5.40`.

These are evidence snapshots, not version recommendations. Each reference links its primary
documentation anchors.

Before the React/Vue edits, two isolated baseline sessions reproduced the gap:

- a React task read generic `code-craft/references/typescript.md` and safe-refactor material, but no
  React framework reference existed;
- a Vue task read generic TypeScript material, but no Vue framework reference existed.

Eight post-edit clean-room sessions then isolated `CLAUDE_CONFIG_DIR`, omitted the personal skill
tree, and ran the plugin's namespaced `sde-agents:sde-fullstack` directly:

| Case | Exact conditional-read result |
|---|---|
| React 18 nested-component identity | read `react.md`; also forms, TypeScript, safe-refactor, TDD |
| React 19 hydration and unsafe HTML | read `react.md`; also forms and TypeScript |
| Vue 3.5 computed/watcher cleanup | read `vue.md`; also TypeScript, safe-refactor, TDD |
| Vue 3.4 SSR request isolation | read `vue.md`; also TypeScript and auth |
| vanilla TypeScript custom element | read neither `react.md` nor `vue.md` |
| Preact TSX | read neither `react.md` nor `vue.md` |
| Python 3.11 task ownership | read `python.md`; returned structured cancellation ownership |
| Python 3.9–3.12 compatibility | read `python.md` under an explicit multi-version-floor task |

The first post-edit batch was discarded when its Windows console could not encode Unicode result
text. The ASCII-safe rerun above is the evidence counted; a completed model call without a
preserved transcript summary was not treated as proof.

The earlier Go clean-room check:

- recorded a `Read` of this branch's exact `skills/code-craft/references/go.md`;
- recovered distinctive new rules for main-module timer semantics, HTTP handler lifetimes,
  `QueryRowContext.Scan`, and Go 1.25 `testing/synctest` external-I/O boundaries.

The disposable targets contained no application repository. These checks prove routing,
provenance, reference separation, and content retrieval; they do not pretend to validate a target
Go, Python, React, or Vue application that was not present.

The 14 local skips are POSIX hook-wrapper cases on Windows. Pure-Python guard tests passed, and the
repository's GitHub workflow exercises the platform contract on Linux.

The one deliberately non-green check was the live plugin probe described in F-03. Its two failures
were contradicted by exact subagent evidence and the clean-room zero-tool canary check; they are
recorded as a probe defect, not hidden as a passing gate.

## Limitations

- This was not a full security scan of a target application.
- No real frontend repository was available to exercise EVAL-004.
- The clean-room token observation does not isolate skill-only tokens.
- No hook remedy was implemented or live-probed.
- The review did not decide DEPLOY-001 or change normal deployment mode.
- Recommendations remain non-authoritative until deliberately imported into the roadmap.

## Reference inventory reviewed

### `backend-craft` — 9 references

- `api-design.md`
- `auth.md`
- `background-work.md`
- `consuming-apis.md`
- `database-reliability.md`
- `fastapi.md`
- `live-data.md`
- `persistence.md`
- `stack.md`

Asset reviewed: `assets/openapi.starter.yaml`.

### `frontend-craft` — 8 reviewed references plus 2 branch follow-ups

- `auth.md`
- `data-views.md`
- `data-viz.md`
- `design-language.md`
- `forms.md`
- `interaction-a11y.md`
- `react.md` — added and primary-source-reviewed on this branch
- `stack.md`
- `ux-writing.md`
- `vue.md` — added and primary-source-reviewed on this branch

### `code-craft` — 7 references

- `bash.md`
- `go.md`
- `powershell.md`
- `python.md`
- `safe-refactor.md`
- `tdd.md`
- `typescript.md`

### Other execution-chain material

- `skills/root-cause/SKILL.md`
- `skills/ci-actions/SKILL.md`
- `skills/ci-actions/assets/ci.reusable.yml`
- `hooks/hooks.json`
- `scripts/readonly-guard.py`
- `scripts/probe_plugin.py`
- `scripts/eval_clean_room.py`
- `scripts/eval_behavioral.py`
- `scripts/eval_routing.py`
- `scripts/validate_fleet.py`
- `evals/behavioral/contracts.json`
- `evals/routing/craft-vs-fullstack.json`
- `evals/routing/ladder.json`
- `evals/routing/verification-seam.json`
- `tests/test_hook_wiring.py`
- `tests/test_probe_canaries.py`
- `tests/test_readonly_guard.py`
- `tests/test_validate_fleet.py`
