# Agent and skill full-fleet audit findings — 2026-08-30

**State:** Historical review evidence. This document is not a task list. Only
[`docs/fleet-roadmap.md`](../../fleet-roadmap.md) can import work from it.

**Audited revision:** `a9313acfb157acd694935ed65da05261a373c713` (`FETCH_HEAD`, fetched main).

**Scope:** All 11 canonical `agents/*.md` definitions, all 20 canonical
`skills/*/SKILL.md` entrypoints, and their linked Markdown, text, script, and template resources.
Generated host adapters were checked structurally but were not treated as authored sources.

## Executive verdict

The fleet is structurally valid but not semantically clean. The audit found nine high-priority
defects, 36 medium findings, four low findings, four findings already owned by the live roadmap,
and three rejected candidates whose proposed remediation conflicts with prior repository evidence.

The strongest defects are not prose style:

- destructive recipes whose advertised guard does not contain the target;
- audit commands that can copy secrets into retained model transcripts;
- evidence envelopes that can name a revision whose bytes were not proved;
- routing cases that can pass when the wrong same-cluster component fires;
- orchestration loops with no hard terminal bound; and
- current host or framework behavior stated as a universal fact.

The broad “remove fluff” hypothesis did not survive inspection. Most apparent ceremony is consumed
by a later stateless session, packet parser, grader, guard, or authority boundary. Readability debt
does exist, but it should be reduced only with the behavioral evidence the affected text requires.

## Method and evidence boundary

The audit applied five lenses:

1. **Prompt engineering:** triggering, ownership diagnosis, baseline comparability, and output shape.
2. **Context engineering:** always-loaded cost, conditional reachability, inheritance, and trust.
3. **Loop engineering:** stable identity, progress bounds, terminal states, and resumable artifacts.
4. **Graph engineering:** typed authority edges, joins, failure behavior, and effect uncertainty.
5. **Harness engineering:** exact-byte identity, oracle validity, false-green paths, and time bounds.

Local canonical source was inspected first. Perishable external claims were checked against current
primary documentation. GitHits was used separately for upstream implementation or adoption evidence;
it was not used as a substitute for the local checkout.

The following commands supplied fresh structural evidence:

```text
python scripts/validate_fleet.py                 PASS: 11 agents, 20 skills
claude plugin validate . --strict                PASS: Claude Code 2.1.251
git diff --check                                 PASS
python -m unittest tests.test_packet_lint \
  tests.test_learning_ledger tests.test_run_state
                                                   PASS: 160, skipped: 1
```

The full offline suite did **not** complete. Ten modules passed; `test_eval_routing.py` exposed a
stale 26-versus-27 directory assertion; `test_hook_wiring.py` produced environment-level process
launch errors; and the runner then required interruption because it has no per-module timeout.
No paid routing or behavioral model sessions were run. Static routing consequences therefore remain
static findings until a paired fresh-context run measures them.

## High-priority confirmed findings

### H-01 — the Bash recursive-delete guard does not contain the target

- **Evidence:** `skills/code-craft/references/bash.md:41-43` presents
  `rm -rf "${dir:?}"/` as the safe form.
- **Issue:** `${dir:?}` rejects only an unset or empty variable. `/`, `.`, `..`, a workspace root,
  or another broad resolved path still passes.
- **Consequence:** An LLM following the shipped recipe can recursively delete a root, checkout, or
  unintended directory while believing the guard made the operation safe.
- **Smallest fix:** Resolve the absolute target, compare it with an explicitly named allowed parent,
  reject filesystem and workspace roots, and operate on the verified literal path.
- **Acceptance:** Red-first tests make the rule fire for `/`, `.`, `..`, the workspace root, and a
  symlink or traversal escaping the intended parent.

### H-02 — read-only audit instructions can disclose secrets into their own transcript

- **Evidence:** `skills/lab-audit/references/checks.md:28-29,70-71` prescribes bare
  `docker inspect` and rendered `docker compose config`. The secret sweep at
  `skills/security-audit/references/secrets.md:31-42` uses normal grep forms that print matches.
  This conflicts with the capture-safety owner at `skills/service-onboard/SKILL.md:23-28`.
- **Issue:** These commands can print fully interpolated configuration, container environment values,
  or the matching credential itself into model context, transcripts, and retained evidence.
- **Consequence:** A nominally read-only assessment can create a new durable copy of a password,
  exporter credential, or token.
- **Smallest fix:** Replace broad inspection with field-scoped, non-value queries or a small tested
  helper that emits only paths, variable names, counts, and redacted match metadata.
- **Acceptance:** A sentinel-secret fixture proves the literal value never appears in stdout, stderr,
  findings, or evidence artifacts. Docker’s current contract confirms that Compose interpolation and
  container environment inspection expose values; `env_file` is not runtime secret isolation.
  Sources: [Compose interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/),
  [Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/).

### H-03 — the destructive CLI starter accepts booleans as age thresholds

- **Evidence:** `skills/sre-tool/assets/cli_skeleton.py:68-72` accepts JSON configuration values
  without an exact type check; lines 94 and 128 compare the value numerically.
- **Issue:** In Python, `False` is an integer equal to zero. A configuration containing
  `"older_than": false`, combined with `--yes`, can select every positive-age item for deletion.
- **Consequence:** Malformed configuration crosses the dry-run boundary into an unexpectedly broad
  destructive plan.
- **Smallest fix:** Require `type(value) is int`; reject booleans, floats, strings, negative values,
  and non-object roots before constructing a plan.
- **Acceptance:** Red-first tests cover `false`, `true`, strings, floats, negative integers, and a
  non-object document, then prove `--yes` cannot widen a rejected plan.

### H-04 — lease-token confidentiality is claimed but not enforced

- **Evidence:** `skills/sre-tool/SKILL.md:16-24` says a lease token travels only through stdin and
  never enters a prompt or transcript. `scripts/run_state.py:394-395,447-455` returns the plaintext
  token, and the CLI prints the result near line 963.
- **Issue:** A direct model-invoked claim operation places the token in tool output visible to the
  model and retained transcript.
- **Consequence:** A capability intended to bind one worker attempt can be copied or replayed from
  the very evidence channel said not to contain it.
- **Smallest fix:** Return an opaque handle or capture the token through a protected descriptor or
  wrapper outside model-visible output. Until then, call the property caller discipline.
- **Acceptance:** Exercise the actual model-facing invocation path and prove the token is absent from
  stdout, stderr, returned JSON, logs, and transcript-shaped capture.

### H-05 — verification can claim an exact revision without proving those bytes

- **Evidence:** `agents/verification-engineer.md:26-44,75-81` promises exact-revision evidence.
  `scripts/verification_sandbox.py:235-248` accepts `target_revision` as caller text, its envelope
  call at lines 297-340 omits a tree digest, and `scripts/evidence_envelope.py:105-120` defaults that
  digest to `None`. `tests/test_verification_sandbox.py:101` accepts an arbitrary `abc123` value.
- **Issue:** The trusted harness does not resolve Git identity, reject dirty product bytes, or bind a
  verifier-authored test patch.
- **Consequence:** A future session can receive PASS evidence labelled with candidate SHA A even when
  different source bytes or different verifier tests actually ran.
- **Smallest fix:** Resolve and verify the source revision inside the harness, compute a tree digest,
  reject dirty or mismatched product bytes, and hash a verifier-authored patch separately.
- **Acceptance:** Red-first cases cover mismatched HEAD, dirty product bytes, a caller-forged revision,
  and the same candidate executed with two different test patches.

### H-06 — five repo-reading writers violate the fleet’s lethal-trifecta rule

- **Evidence:** `skills/prompt-craft/references/agent-security.md:11-32` defines untrusted content,
  private data, and outbound requests in one context as a vulnerability that prose cannot fix.
  `distinguished-architect`, `principal-engineer`, `multi-agent-architect`, `prompt-engineer`, and
  `sde-fullstack` each grant local `Read` plus `WebFetch`/`WebSearch` at frontmatter line 4.
- **Issue:** Their “fetched content is data” instruction is mitigation, not a structural boundary.
  Repository content can steer a query or URL that contains private data.
- **Consequence:** The agent topology contradicts its own prompt-security contract and gives one
  compromised context all three legs of the exfiltration path.
- **Smallest fix:** Route current external evidence through a research-only context without private
  repository access. Use a provenance-labelled structured handoff and re-review the composition,
  because delegation by itself is not isolation.
- **Acceptance:** The capability graph shows no context with all three legs. Adversarial tests attempt
  to move sentinel private data through every outbound-capable edge.

### H-07 — the SRE-tool pipeline permits review against moving bytes

- **Evidence:** `skills/sre-tool/SKILL.md:68-73` allows review to run concurrently with the next build
  phase. `AGENTS.md` requires measurements and review against a tree no other writer is changing.
- **Issue:** A reviewer can inspect one state while a builder changes the same checkout underneath it.
- **Consequence:** Review findings and PASS evidence are not bound to stable bytes; late edits can
  escape the gate or invalidate earlier observations silently.
- **Smallest fix:** Review an immutable revision or isolated worktree. Permit concurrency only when
  target revisions and write ownership are explicitly disjoint.
- **Acceptance:** The review packet records revision and tree identity, and the harness rejects a
  changing or mismatched target.

### H-08 — the homelab routing harness can green the wrong same-cluster route

- **Evidence:** `scripts/eval_routing.py:1086-1091` passes a positive on any expected-member
  intersection. Lines 1112-1124 remove all cluster members from `also_fired`, although
  `evals/routing/homelab-ops.json:18,333` says audit cross-fire is visible there. Onboarding cases at
  lines 21-28 and 303-310 accept either the authority owner or an explicit-only checklist.
- **Issue:** Both audit skills can fire on one prompt, or an explicit-only checklist can fire instead
  of `homelab-engineer`, while the case still passes and hides the near miss.
- **Consequence:** The harness can certify the authority boundary it was meant to measure without
  observing that boundary.
- **Smallest fix:** Add required, forbidden, and exclusive positive targets, or expose
  `also_fired_members`. Require `homelab-engineer` in mutation/onboarding cases and forbid direct
  checklist activation in separate disambiguation cases.
- **Acceptance:** Named mutants that add the wrong same-cluster route make the focused cases fail.

### H-09 — one ARIA recipe is incorrectly universalized across widget patterns

- **Evidence:** `skills/frontend-craft/references/interaction-a11y.md:20-29` says custom options use
  `role="option"` and `aria-selected`, although the entrypoint routes menus, tabs, tooltips, and other
  widgets into this reference.
- **Issue:** Tabs require `tablist`/`tab`/`tabpanel`; menus require `menu`/`menuitem`; `option` belongs
  to listboxes and related patterns.
- **Consequence:** Generated interfaces can expose invalid roles, state, and keyboard behavior to
  assistive technology.
- **Smallest fix:** Prefer native or established primitives and replace the universal block with a
  compact widget-to-APG-pattern table.
- **Acceptance:** Component tests assert the role, focus, state, and keyboard contract for each
  supported widget family. Sources: [tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/),
  [menu button](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/),
  [listbox](https://www.w3.org/WAI/ARIA/apg/patterns/listbox/).

## Medium findings

### Prompt and context engineering

#### M-01 — Prompt Engineer begins with a monocausal diagnosis

`agents/prompt-engineer.md:13` says every model miss means the prompt was ambiguous. The same fleet
recognizes routing, wrapper, context, transport, tool, evaluator, and capability failures. Replace the
absolute with a boundary-isolation order and edit prompt text only when evidence points there. Prove
the change with one case from each non-prompt failure class.

#### M-02 — Prompt Engineer does not prefer the repository-owned harness

`agents/prompt-engineer.md:19-21` mandates raw Agent repetitions but does not first route to an
existing repository eval harness. Prepend “use the repository-owned harness when one exists”; make
raw fresh-context repetitions the fallback and record runtime, profile, artifact, and grader identity.

#### M-03 — prompt-craft has no coherent greenfield path

`skills/prompt-craft/SKILL.md:3` triggers on creating new artifacts, while line 14 forbids any edit
without an observed existing failure. Add a greenfield branch: define acceptance cases, use a
no-artifact or nearest-current baseline, and distinguish creation from repair.

#### M-04 — context inheritance is stated as an absolute

`skills/prompt-craft/references/context.md:31-40`, `skills/sre-tool/SKILL.md:54`, and
`skills/sre-tool/assets/spawn-prompt.template.md:1-4` say spawned agents do not inherit parent
conversation. Ordinary Claude subagents are fresh, Claude fork mode inherits the conversation, and
Codex inheritance is configured by `fork_turns`. Add a host/mode table and require fresh mode when
independence is an acceptance property. Source:
[Claude subagent context](https://code.claude.com/docs/en/sub-agents#fork-the-current-conversation).

#### M-05 — prompt-size and tool-count advice is unsupported or internally inconsistent

`agents/prompt-engineer.md:51` recommends roughly 100-word descriptions, bodies under 500 words, and
“unbounded” references. `skills/prompt-craft/references/tools.md:55-63` gives a roughly twelve-tool
accuracy threshold without a local measurement. Descriptions share an aggregate listing budget and
loaded references still consume context. Replace universal counts with measured aggregate bytes,
routing rates, schema-token cost, selection errors, and actual load predicates.

#### M-06 — upstream frontmatter support and local fleet policy are not distinguished

`skills/prompt-craft/references/claude-code-frontmatter.md:3-9` says current official docs win, while
`scripts/validate_fleet.py:96-120` intentionally admits a smaller set and rejects upstream-supported
`metadata`, `license`, and `compatibility`. This is not evidence that the validator must accept every
field; it is an undocumented policy boundary. Label the validator set as the fleet-approved subset,
state how a supported field is adopted, and add fixtures if the owner chooses to admit one. Source:
[Claude skill frontmatter](https://code.claude.com/docs/en/skills#frontmatter-reference).

### Loop, graph, handoff, and harness engineering

#### M-07 — multi-agent discovery loops have no hard convergence bound

`agents/multi-agent-architect.md:24-25` recommends loop-until-dry and completeness-critic feedback
without maximum rounds, tokens, or wall time. Require both a dry-out condition and a hard budget.
At exhaustion, return durable partial state, uncovered scope, and explicit incomplete or inconclusive
status.

#### M-08 — root-cause has no no-progress exit and SRE-tool misuses its three-strikes rule

`skills/root-cause/SKILL.md:28-30` counts three failed fixes of the same causal diagnosis.
`skills/sre-tool/SKILL.md:62` instead counts the original build plus two review rounds. Neither defines
what happens after every hypothesis is ruled out or another evidence round makes no progress. Keep
review caps separate, rerank a diagnosis after its first cause-directed fix fails, and define success,
inconclusive, no-progress, unsafe, and interrupted terminals.

#### M-09 — the multi-agent pattern catalog omits accepted graph invariants

`agents/multi-agent-architect.md:24-33` covers orchestration shapes but not typed state and edges, join
failure/timeout, cancellation, approval, effect uncertainty, idempotency, or recovery. The accepted
graph decision requires every cycle to have a ceiling and every join failure/timeout behavior. Add a
compact always-loaded invariant list or conditional decision pointer; do not build the deferred graph
runtime merely to repair the prose.

#### M-10 — deterministic behavioral graders overclaim semantic truth

`scripts/eval_behavioral.py:7-9` says a deterministic no-judge failure is “fact, not opinion.”
`ORACLE-019` records reproducible false-reds and false-greens. Change the claim to “reproducible
assertion result” and keep semantic validity as a separately calibrated property.

#### M-11 — the offline test runner has no per-module timeout

`scripts/run_tests.py:64-84` calls each module with `subprocess.run` and no timeout. Add a configurable
module deadline, terminate the child process tree, preserve partial output, and emit an explicit
timeout/inconclusive result rather than hanging the entire evidence loop.

#### M-12 — Researcher’s example violates its own sourcing contract

`agents/researcher.md:114-129` presents “latest release,” maintenance, and advisory claims with generic
source labels, no direct URLs, and no Sources section. Make the example fictional or date/version
bound and demonstrate the URL-bearing output shape required by the body.

#### M-13 — Verification Engineer’s description advertises an insufficient isolation boundary

`agents/verification-engineer.md:3` leads with a disposable worktree, while lines 38-44 and 81-83
correctly say a worktree is not an execution sandbox. Lead with the enforced isolation boundary and
describe the worktree only as byte isolation. Treat Docker/Podman as a preferred implementation, not
the only durable boundary.

#### M-14 — lab-incident lacks a durable standalone handoff packet

`skills/lab-incident/SKILL.md:70-92` requires timestamped notes and downstream handoffs but defines no
minimum final fields. `scripts/packet_lint.py:93` acknowledges that no shape exists. Add a compact
incident-state packet containing current impact, interventions and outcomes, rollback state, recovery
proof, outstanding hypotheses, owner, and next authority edge.

#### M-15 — audit recurrence has no stable finding identity

`skills/lab-audit/references/checks.md:103-110` defines date, check, severity, free-text finding,
evidence, and status, then requires a re-observed finding to update the same row. A stateless session
cannot deterministically match paraphrased prose. Add a stable target-scoped key plus first-seen,
last-seen, current evidence, state, and owner for open rows.

#### M-16 — postmortem actions have proof but no owner or lifecycle state

`skills/postmortem/SKILL.md:44` requires an artifact and proof of done, while
`skills/postmortem/assets/postmortem.md:42` has no action owner or state. This is a candidate handoff
gap, not a reason to remove the existing artifact/proof or draft/final fields that prior review kept.
Add only owner and target/state for unfinished actions, then add one semantic handoff case.

#### M-17 — volatile harness counts have already drifted

`evals/README.md:600` says the sample repository has 26 top-level directories; the fixture has 27.
`evals/routing/homelab-ops.json` also describes eight and ten members while listing twelve. Derive
counts from parsed records where they are consumed, or remove counts that add no decision value.

### Framework, API, CI, and operational correctness

#### M-18 — the Mantine/Tailwind prohibition is false on current Mantine

`skills/frontend-craft/SKILL.md:35-38` and `references/stack.md:22-25` prohibit Mantine components in
Tailwind projects because of an asserted reset conflict. Current Mantine supports third-party utility
styling and CSS layers. Remove the ban; inspect installed versions, repository conventions, and style
order. Source: [Mantine styles API](https://mantine.dev/styles/styles-api/). GitHits separately
confirmed the upstream CSS-layer documentation at Mantine commit `8a284e2c`.

#### M-19 — FastAPI does not require response_model on every route

`skills/backend-craft/references/fastapi.md:21-27` mandates `response_model=` universally. Direct
`Response`, redirect, streaming/file, no-content, and `response_model=None` routes are valid. Scope the
rule to structured application payloads and name the exceptions. Source:
[FastAPI response-model contract](https://fastapi.tiangolo.com/tutorial/response-model/#disable-response-model).

#### M-20 — the PostgreSQL restore statement is false

`skills/backend-craft/references/database-reliability.md:109-115` says restoring over any non-empty
database fails. `pg_restore` supports selective restore and `--clean`. Replace the blanket statement
with mode-specific collision, cleanup, ownership, transaction, and exit-on-error guidance. Source:
[`pg_restore`](https://www.postgresql.org/docs/current/app-pgrestore.html).

#### M-21 — auth and external-API guidance universalizes one architecture

`backend-craft/references/auth.md:8-11`, `frontend-craft/references/auth.md:3-9`, and
`backend-craft/references/consuming-apis.md:13-18` require access-token/refresh-cookie flows, complete
pagination, TTL caching, and the newest connector pattern. Add observable predicates for public apps,
server sessions or BFFs, gateway/mTLS auth, bounded retrieval, non-cacheable data, and experimental
connectors. The target repository and provider contract remain authority.

#### M-22 — data-view guidance bypasses repository stack precedence

`skills/frontend-craft/references/data-views.md:7-8` mandates TanStack Table, Tailwind, and TanStack
Virtual for every tabular view despite the entrypoint saying the existing stack wins. Make repository
primitives the first branch; keep these as greenfield defaults and virtualize only after measured need.

#### M-23 — the privileged CI lane is underspecified

`skills/ci-actions/SKILL.md:32-38,55-57` overgeneralizes `pull_request_target`, `workflow_run`, and
label-triggered secret availability. Require an explicitly separate trusted workflow, actor and
revision validation, least privileges, an artifact trust boundary, and a prohibition on executing
fork-controlled bytes. Source:
[GitHub secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use).

#### M-24 — the distinguished reference overlaps the principal rung

`skills/eng-ladder/references/distinguished.md:12-16` claims any multi-system or costly-to-reverse
data-model decision already assigned to principal by the entrypoint and principal reference. Narrow
distinguished triggers to organization/platform standards, consolidation, build-versus-buy, and
multi-year failure-domain decisions.

#### M-25 — the TypeScript reference owns frontend cache architecture after disclaiming it

`skills/code-craft/references/typescript.md:45-74` gives frontend ownership to `frontend-craft` and
then prescribes query-cache optimistic-update architecture. Move lifecycle design to a conditional
frontend/data-layer reference; retain language-level promise, typing, and idempotency mechanics.

#### M-26 — the TDD mutation recipe lacks isolation and exact restoration

`skills/code-craft/references/tdd.md:75-79` tells the model to break code deliberately without a
disposable copy, named mutant, or byte-exact restoration contract. Require an isolated worktree or
injected mutation, bind one test to one mutant, and verify restoration before returning.

#### M-27 — the CLI starter’s “every rule” claim overstates its implementation

Beyond H-03, `cli_skeleton.py:54-58` checks `stdout.isatty()` when coloring stderr, reports
`commit unknown`, claims signal cleanup but only exits, and does not summarize partial deletion
failures as its reference requires. Narrow the claim or implement and test the missing behaviors.

#### M-28 — restore-drill misdefines RTO

`skills/restore-drill/SKILL.md:32` says measured recovery duration is the RTO. RTO is the maximum
acceptable target. Record observed recovery time, compare it with declared RTO, and report backup
age/data loss against RPO separately. Source:
[NIST RTO definition](https://csrc.nist.gov/glossary/term/Recovery_Time_Objective).

#### M-29 — Alloy formatting is presented as sufficient validation

`skills/observability/SKILL.md:99` and `references/pipeline.md:59` use `alloy fmt` as the pre-reload
validation gate. Current Alloy documents `fmt` as syntax/format handling and `alloy validate` as the
configuration validator. Require `validate` with runtime-matching feature flags; retain `fmt` as
formatting evidence. Sources: [Alloy fmt](https://grafana.com/docs/alloy/latest/reference/cli/fmt/),
[Alloy validate](https://grafana.com/docs/alloy/latest/reference/cli/validate/). GitHits separately
confirmed the component-registry validation path in Alloy v1.18.0 `cmd_validate.go`.

#### M-30 — PromQL division-by-zero behavior is wrong

`skills/observability/references/promql.md:32` says division by zero yields no data. PromQL float
arithmetic follows IEEE 754 and produces infinity or NaN; empty vectors more commonly result from
absent operands or label mismatch. Teach those cases and an explicit zero-traffic policy separately.
Source: [Prometheus arithmetic operators](https://prometheus.io/docs/prometheus/latest/querying/operators/).

#### M-31 — upgrade ordering ignores dependency compatibility

`skills/upgrade-campaign/SKILL.md:37-38` asks for minimum dependency versions and then unconditionally
upgrades dependencies last. Build a compatibility DAG from release contracts first; use blast-radius
preference only to choose among topologically valid orders.

#### M-32 — incident signals are converted into causal certainty

`skills/lab-incident/references/golden-signals.md:16-17,43-44` says zero traffic proves upstream
failure, proxy codes identify one layer, and name failure proves the resolver is at fault. Rewrite each
as “suggests” plus the cheapest discriminator; service withdrawal, downstream failures, proxy
misconfiguration, client caching, and authoritative DNS can produce the same symptoms.

#### M-33 — secret-pattern candidates are promoted directly to findings

`skills/security-audit/references/secrets.md:12-20,39-42,67-68` treats generic history hits as
findings and places `env_file` beside runtime secret stores. Require type, validity, access path, and
consumer confirmation. Separate repository hygiene from runtime isolation and never print candidate
values while validating them.

#### M-34 — audit severity is condition-based rather than impact-based

`skills/lab-audit/SKILL.md:26` and `skills/security-audit/SKILL.md:44` classify every unauthenticated
boundary exposure as P0, while `security-audit/references/checks.md:24` calls authenticated and patched
reachability a P2 finding without an adverse condition. Score exposed capability or data,
preconditions, blast radius, detection, and recovery. Keep secure reachability as coverage evidence.

#### M-35 — restore-drill routes home-lab backup design to the wrong owner

`skills/restore-drill/SKILL.md:3` routes backup design to backend-craft or service-onboard, while
`agents/homelab-engineer.md:3` explicitly owns lab storage and backups. Route lab backup architecture
to `homelab-engineer`; retain backend-craft only for application-level backup behavior.

#### M-36 — internal process status is labelled externally observable health

`skills/observability/SKILL.md:38` calls the requirement external and then accepts container health or
service status. Those can be green while DNS, proxy, TLS, or the user path is broken. Rename them
component/process health and require an external synthetic signal only when the consumer-boundary
predicate fires.

## Low findings and owner questions

### L-01 — Principal Engineer’s required design shape is prose rather than slots

`agents/principal-engineer.md:25` packs eight required sections into one sentence, while its final
packet does not repeat them. Convert the same requirements into short headings or template slots; add
no new policy.

### L-02 — Code Reviewer requires praise even when none is supportable

`agents/code-reviewer.md:73-77` requires one thing done genuinely well. A uniformly defective or
malicious change can force filler or fabricated praise. Make the strength slot conditional on evidence.

### L-03 — Repository Investigator accepts stated isolation without observable proof

`agents/repository-investigator.md:29-33` recognizes that local Git configuration can execute code but
permits Git commands when the caller states the isolation boundary. Decide whether trusted caller
attestation is accepted authority; otherwise require independently observable boundary evidence.

### L-04 — long lines hide independent predicates

The agent lane contains 171 lines over 120 characters; the core-skill lane contains 181. The largest
skill concentrations are `frontend-craft`, `sre-tool`, `backend-craft`, and `eng-ladder`. Reflow only
when touching the affected prose, especially where multiple authority or failure predicates share one
paragraph. A formatting-only sweep would create review noise without behavior evidence.

## Findings already owned by the live roadmap

These are not new backlog imports:

1. **LABSEC-002 — guard-enforced lab inspector (`ready`).** The report-only audit boundary is
   cooperative because shell remains available. `docs/fleet-roadmap.md:483-507` already owns the
   no-write/no-web inspector and tested allowlist. More warning prose is not the fix.
2. **CTX-003 — preload reduction (`ready`, evidence constraint changed).**
   `docs/fleet-roadmap.md:350-374` owns the `sde-fullstack`/skill-body context cost and records that
   conditional reference reads became intermittent. Do not slim required guidance into references
   until that failure is understood and re-measured.
3. **CTX-005 — homelab-engineer body reduction (`decision-needed`, current candidates no-go).**
   `docs/fleet-roadmap.md:421-481` records the spent rounds and fresh regressions. This audit supplies
   no reason to reopen or merge either candidate.
4. **ORACLE-019 — deterministic grader false-red/false-green constructions.**
   `docs/fleet-roadmap.md:1034-1054` already requires a behavioral batch rather than another static
   regex round.

## Rejected or corrected audit candidates

### R-01 — do not move runbook’s proposal grammar to a reference

The initial readability pass proposed moving `skills/runbook/SKILL.md:32-73` behind conditional
loading. That recommendation is wrong in the current harness. The prior executed review at
`docs/archive/2026-08/prop-002-scan-findings-2026-08-13.md:337-364` records that the
`runbook-disposition-propose` contract grants only `Skill`, not `Read`; moving the grammar would make
it unreachable and reproduce a measured failure class. The body is large but load-bearing. Any future
reduction must preserve the closed grammar in the context that executes it.

### R-02 — the plan template’s approval register is not a general workflow-state field

The initial pass treated `skills/sre-tool/assets/plan-file.template.md:19-23` as if it had to encode
all pipeline states. Prior adjudication at
`docs/archive/2026-08/prop-002-scan-findings-2026-08-13.md:422-427` establishes that this field is a
gate approval/sign-off register and an anti-fabrication control. Do not add blocked/failed/inconclusive
values there without first identifying a consumer that expects them.

### R-03 — do not run a broad fluff or formatting purge

Search found no meaningful concentration of generic “robust,” “seamless,” “best-in-class,” or similar
corporate filler. Most repeated-looking sections are packet fields, authority restatements at host
boundaries, grader-visible literals, or future-session handoffs. Trim only after naming the reader and
consumer and measuring behavior on the changed bytes.

## Complete component coverage

### Agents

| Agent | Audit result |
|---|---|
| `application-security-auditor` | No material finding in this pass |
| `code-reviewer` | L-02 |
| `distinguished-architect` | H-06 |
| `homelab-engineer` | Existing LABSEC-002/CTX-005 boundaries; no new prose finding |
| `multi-agent-architect` | H-06, M-07, M-09 |
| `principal-engineer` | H-06, L-01 |
| `prompt-engineer` | H-06, M-01, M-02, M-05 |
| `repository-investigator` | L-03 owner decision |
| `researcher` | M-12 |
| `sde-fullstack` | H-06 and existing CTX-003 |
| `verification-engineer` | H-05, M-13 |

### Skills

| Skill | Audit result |
|---|---|
| `backend-craft` | M-19, M-20, M-21 |
| `ci-actions` | M-23 |
| `code-craft` | H-01, M-25, M-26 |
| `eng-ladder` | M-24 |
| `frontend-craft` | H-09, M-18, M-21, M-22 |
| `host-onboard` | Prose clean; routing surface affected by H-08 |
| `lab-audit` | H-02, M-15, M-34; enforcement already LABSEC-002 |
| `lab-incident` | M-14, M-32 |
| `observability` | M-29, M-30, M-36 |
| `onboarding-map` | No material finding in this pass |
| `postmortem` | M-16 |
| `prompt-craft` | M-03, M-04, M-05, M-06 |
| `restore-drill` | M-28, M-35 |
| `root-cause` | M-08 |
| `runbook` | R-01; no active new finding |
| `security-audit` | H-02, M-15, M-33, M-34; enforcement already LABSEC-002 |
| `self-improve-loop` | Context cost already CTX-003; references otherwise aligned |
| `service-onboard` | No material finding; capture-safety owner used as evidence for H-02 |
| `sre-tool` | H-03, H-04, H-07, M-08, M-27, R-02 |
| `upgrade-campaign` | M-31 |

All linked Markdown references and Markdown/text templates were present and reachable. No malformed
frontmatter, broken code fences, unresolved component references, or missing end-of-task packet
headings were found.

## Recommended import order

This ordering is advisory; it creates no live work until the roadmap imports selected findings.

1. **Safety and evidence integrity:** H-01 through H-08. Each needs a named firing regression before
   prose claims are strengthened.
2. **Harness and convergence:** M-07 through M-17. Fix false-green and non-terminating mechanisms
   before using their output to justify prompt edits.
3. **Perishable factual corrections:** H-09 and M-18 through M-36, batched by owning skill and paired
   with the relevant current primary source.
4. **Prompt and context contract repairs:** M-01 through M-06, with repository-owned before/after
   harness evidence.
5. **Readability debt:** L-01 through L-04 only while substantively touching the same files. Preserve
   R-01 through R-03 as negative constraints.

## What this record does not claim

- It does not make any finding live roadmap work.
- Structural validator success does not clear semantic findings.
- Static inspection does not prove a routing-rate regression or exploit success.
- Current primary documentation does not override an intentional local restriction unless the local
  policy claims to mirror the upstream contract.
- A count of long lines, large bodies, or surviving mutants is not itself a finding.
- No canonical agent, skill, generated adapter, harness, or roadmap item was changed by this audit.
