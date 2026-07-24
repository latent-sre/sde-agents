# Batch-2 review — ten more `affaan-m/ECC` components — July 2026

**Question:** the operator pointed at ten further ECC components — three agents
(`agent-evaluator`, `architect`, `homelab-architect`) and seven skills
(`agent-architecture-audit`, `agent-eval`, `agentic-engineering`, `ai-first-engineering`,
`api-connector-builder`, `api-design`, `article-writing`) — and asked two things: do they carry
hooks or loops, and what do they offer for growing this fleet's agents and skills.

**Method:** raw fetch of all ten files from `affaan-m/ECC` @ `main` (fetched 2026-07-24; the
GitHub API is out of session scope, so this snapshot is dated, not SHA-pinned). Full read of each,
compared against the fleet's seven agents, ten skills, the guard and eval infrastructure, and both
standing review docs — `docs/ecc-skills-agents-review.md` (batch 1, four ECC components, July
2026) and `docs/sre-agents-adaptation-backlog.md` — so nothing already adjudicated is re-litigated.
`agents/homelab-architect` appears in both batches: batch 1 item 4 adjudicated it fully and its
two imports are landed; the fetched copy still matches every line that review cited, so it is
confirmed, not re-reviewed. Licensing: ECC is MIT; provenance noted in commit messages per house
convention.

**Headline:**

1. **Hooks: none.** No file in this batch declares, ships, or wires a hook. The nearest thing is
   `agent-evaluator`'s in-body "Bash Tool Constraints" paragraph — a prose allowlist of read-only
   commands, which is a *promise* where this fleet ships a *control*
   (`scripts/readonly-guard.py` + `hooks/hooks.json`, fail-closed). Batch 1 already saw ECC's only
   real hook usage (`agent-self-evaluation`'s opt-in Stop/PostToolUse reminders) and rejected it.
2. **Loops: procedural prose only, nothing wired.** `agentic-engineering` describes an eval-first
   loop (define → baseline → implement → re-run) — the same shape as `prompt-craft`'s method and
   the routing evals' before/after discipline, unmeasured on their side. `agent-eval`'s run loop
   lives in an external CLI, not the skill. `agent-architecture-audit` is *about* detecting hidden
   repair/retry loops in target systems — diagnostic content, not a loop itself. Nothing is
   recurring, scheduled, or hook-driven. This fleet's enforced hook and measured loops
   (`eval_routing.py` baselines, `self-improve-loop`) have no counterpart in the batch.
3. **Growth: three small imports landed, all body-only** (no routing surface): wrapper-layer
   failure diagnostics into `multi-agent-architect`; API version-lifecycle mechanics and
   rate-limit budget headers into `backend-craft`; the exemplar-first integration method into
   `backend-craft/references/consuming-apis.md`. Eval doctrine from `agent-eval` is registered
   into the finding-7b behavioral-eval work. Everything else is validation or rejection.
4. **One import would be a regression and is banned:** `api-design` teaches the same nested
   `{"error": {...}}` envelope that backlog item 1.3 already flags as a defect in our own
   `backend-craft/SKILL.md:18-24`. Two circulating sources now teach the wrong shape — that
   *raises* 1.3's priority (fix to top-level RFC 9457 problem+json); it must land before any
   error-shape text is touched again. **— Resolved 2026-07-24: 1.3 landed (commit `c88d380`);
   `backend-craft` now teaches top-level problem+json and bans the nested envelope. The ban on
   importing `api-design`'s error sections stands; the block on our own error-shape edits is
   lifted.**

---

## Hooks and loops — the direct answer, per file

| Component | Hooks | Loops |
|---|---|---|
| `agents/agent-evaluator` | None; prose Bash allowlist only (unenforced) | None |
| `agents/architect` | None | None |
| `agents/homelab-architect` | None | None (staged-phases plan is a sequence, not a loop) |
| `skills/agent-architecture-audit` | None | None of its own; *detects* hidden repair loops in audited systems (its layer 11) |
| `skills/agent-eval` | None | Benchmark loop (N runs × agents × tasks) — in the external CLI it wraps, not the skill |
| `skills/agentic-engineering` | None | "Eval-First Loop" in prose; no harness, no measurement |
| `skills/ai-first-engineering` | None | None |
| `skills/api-connector-builder` | None | None |
| `skills/api-design` | None | None |
| `skills/article-writing` | None | None |

ECC agents could not carry effective hooks even if they declared them — `hooks:` frontmatter is
silently ignored on plugin-shipped agents, the exact silent-disarm class this fleet's
`hooks/hooks.json` + validator design exists to avoid (see the docstring in
`scripts/readonly-guard.py`).

## Per-component verdicts

### 1. `agents/agent-evaluator` — reject (batch 1 adjudication extends; new residue dominated)

The agent-shaped wrapper of `agent-self-evaluation`, whose 5-axis numeric rubric batch 1 rejected
on three doctrine conflicts (uncalibrated numbers, same-context self-grading, averaging past the
gate). The agent inherits all three. What is new in the agent file, checked one by one:

- **Evidence-symmetric scoring** ("DO NOT assign score 5 without citing evidence") partially fixes
  the confident-silence inversion batch 1 found in `evaluate.py` — but only inside a rubric we
  don't run; our evidence labels already make unsupported claims visible without scores.
- **The prose Bash allowlist** is the instructive artifact: grep/cat/ls plus hardened git reads,
  forbidden-verbs list, ask-before-running escape hatch — all of it advisory. This fleet holds the
  enforced version of exactly this list. Verified against `scripts/readonly-guard.py`: their one
  novel detail, pager hardening (`--no-pager`, `-c core.pager=cat` against repo-local
  `.git/config` pager execution), is *dominated* by our guard — `--no-pager`/`-P` are allowlisted
  globals, `-c key=val` is denied outright (`_git_allowed`), and hook-context stdout is not a TTY,
  so git never spawns a pager at all. Nothing to import.
- "Don't penalize missing features the user didn't request" — already landed (batch 1 item 3b,
  `eng-ladder` Mode 2).

### 2. `agents/architect` — reject; validates the ladder

A generic pattern listicle (SOLID-style principles, frontend/backend/data pattern menus, a
10K→10M-user scaling table) with the boilerplate Prompt Defense Baseline batch 1 rejected. Its two
concrete artifacts both exist here in stronger form: the ADR template lacks reopen triggers, which
`distinguished-architect.md:28` requires ("the triggers that should reopen it"); the design
checklist is `principal-engineer`'s design-doc slots without the failure-mode-hunting or the
blast-radius sizing. Its "Use PROACTIVELY when planning new features" description overlaps ECC's
own `homelab-architect` (also a planning agent) with no negative routing between them — the
systemic unmeasured-overlap flaw again, now visible inside the same batch.

### 3. `agents/homelab-architect` — previously adjudicated; confirmed unchanged

Batch 1 item 4: the two network-safety invariants (resolver cutover readiness, management-plane
survival) are landed in `homelab-platform`; the rest was rejected with reasons. The re-fetched
copy still matches every cited line, including the four `homelab-network-*` skills it instructs
itself to use with no mechanism to load them. Nothing further.

### 4. `skills/agent-architecture-audit` — adopt the diagnostics, reject the apparatus (landed)

The one genuinely new content in the batch: a failure taxonomy for LLM apps whose defects hide in
the wrapper stack rather than the model. Its strongest moves converge with fleet doctrine from the
diagnostic side — "do not accept 'must use tool' in prompt text when code never enforces it" is
the checking counterpart of `multi-agent-architect`'s "tools are authority… enforce roles at the
tool layer, not with prose."

**Adopted** (landed as a wrapper-systems paragraph in `multi-agent-architect`'s "Failure modes you
diagnose" — body-only, no description change):

- **Wrapper regression + the differential test** — the model answers correctly on a direct call
  but fails inside the stack; bisect layer by layer before blaming the model. A diagnostic move
  the fleet nowhere states.
- **Hidden second passes** — repair/retry/summarize steps mutating output between generation and
  delivery; make them explicit contracts or remove them.
- **Memory-admission discipline** — user corrections outrank the agent's own assertions; an
  agent's monologue must never auto-admit into durable memory.
- **Context duplication** — the same fact arriving via prompt, history, and memory reads as
  independent confirmation.
- **Transport corruption** — logs show the right answer, the user sees a wrong one: the defect is
  in rendering/delivery, not generation.
- **Prompt-only tool mandates** — a required tool the code never gates will be skipped under load.

**Rejected:** the 12-layer taxonomy as shipped (layers 4/5, "distillation"/"active recall", are
their memory stack's implementation detail; ~seven distinctions carry all the content); numeric
`confidence: 0.0` (categorical-confidence doctrine, `code-reviewer.md`); the JSON report schema
(packet conventions own end-of-task shape); `metadata.origin` frontmatter (validator-rejected by
design — provenance lives in commit messages); the body-level "MANDATORY for" triggers (below the
routing decision); the rg anti-pattern corpus (named after their stack; fine as inspiration, not
as imported text).

### 5. `skills/agent-eval` — reject the component, adopt the doctrine (registered)

A wrapper for a third-party CLI (`github.com/joaquinhuigomez/agent-eval`) whose own installation
line is "install from its repository after reviewing the source" — a dependency shape the
stdlib-only rule exists to refuse, wrapped in a skill that is mostly the tool's README. Its
head-to-head agent-comparison remit also has no fleet consumer (we eval routing and, per quality
finding 7, behavior — not Claude-Code-vs-Aider selection).

**Adopted as doctrine** into the finding-7b behavioral-eval work (registered in the backlog, not
built standalone — same sequencing rule as the packet-lint assert): every case carries **at least
one deterministic assert** (LLM judges add noise — the routing evals are already fully
deterministic; keep that property as behavioral evals land); **fixtures are pinned and versioned
as code** (their commit-pinning rule, generalized); **token cost is tracked beside pass rate** (a
95% component at 10× the cost is a finding, not a win).

### 6. `skills/agentic-engineering` — one line adopted (landed); rest validates or is out of remit

Its eval-first loop is `prompt-craft`'s method plus `evals/README.md`'s before/after discipline —
preached there, measured here. Its decomposition rule (independently verifiable units, one
dominant risk each) is `multi-agent-architect`'s worker-sizing said smaller. Its session-strategy
section (compaction timing) is operator guidance, not fleet-definition content. **Adopted:** the
model-tier escalation rule — escalate only when the lower tier fails with a clear reasoning gap,
never as the first response to a miss — landed as one sentence in `multi-agent-architect`'s
"Budget explicitly" principle, which already owned tier-by-cost-vs-capability. **Rejected as a
skill:** topic-shaped description ("Operate as an agentic engineer") and near-total overlap with
`ai-first-engineering`, unmeasured, no negative routing — the systemic flaw, third sighting.

### 7. `skills/ai-first-engineering` — reject; one optional residue registered

An org-process operating model (process shifts, review policy, *hiring signals*) for a
single-operator fleet. Its architecture section — explicit boundaries, stable contracts, typed
interfaces, deterministic tests; avoid implicit behavior spread across hidden conventions — is
`principal-engineer`'s "boring by default" plus `sde-fullstack`'s conventions discipline, with one
angle ours never states: **AI agents as a named maintainer class** whose legibility needs
(greppability, explicitness) are stricter than humans'. Registered as an optional one-line clause
for `principal-engineer`'s cognitive defaults — to be adjudicated against nuance-bloat before
landing, not landed now.

### 8. `skills/api-connector-builder` — adopt the method (landed); reject as a separate skill

The best-crafted skill of the ten, and its core rule is house doctrine ("match the codebase's
idioms") given a concrete method: read ≥2 existing connectors before vendor docs; map layout,
config, auth, retry/pagination, registry wiring, test style; newest in-repo pattern wins over
oldest; done includes registration + tests + docs, not transport code that compiles. **Landed** as
one bullet in `backend-craft/references/consuming-apis.md`, which the "consuming or integrating
third-party APIs" predicate already routes to — importing it as a skill would put a second
description on a remit `backend-craft`'s description literally owns. Its "Related Skills"
(`backend-patterns`, `mcp-server-patterns`, `github-ops`) are bare unresolvable names —
aspirational-reference flaw, fourth sighting.

### 9. `skills/api-design` — reject the bulk; two residues adopted (landed); one hazard flagged

524 lines that mostly re-derive `backend-craft` at lower strength (no failure-first spine, no
contract-testing, examples in three frameworks — the example-library token load our doctrine
avoids). The hazard: its error format is the **nested** `{"error": {...}}` envelope — the same
shape backlog 1.3 verified as a defect in our own `backend-craft/SKILL.md:18-24` and scheduled to
fix to top-level RFC 9457 problem+json. Nothing from its response-format sections may be imported,
and 1.3's priority rises: our SKILL currently agrees with a wrong external source.
**— Resolved 2026-07-24: 1.3 landed; our SKILL no longer agrees with it. The import ban on
`api-design`'s response-format sections is permanent, for the same reason.**

**Adopted** (landed in `backend-craft/SKILL.md`, body-only): the **version-lifecycle mechanics**
missing from our one-liner — what counts as breaking vs additive, at most two live versions,
`Sunset` header with a date, `410 Gone` after it (an undated deprecation never completes); and the
**rate-limit budget headers** (`X-RateLimit-Limit/-Remaining/-Reset`) completing the loop that
`consuming-apis.md:11` already teaches from the client side ("self-throttle to their quota" — now
the server publishes the quota). **Rejected:** offset-vs-cursor decision table
(`backend-craft`'s cursor-by-default with a bounded-admin-list exception is the stronger form);
auth/authz snippets (`references/auth.md` owns); sparse fieldsets and filtering grammars
(situational; no observed fleet need).

### 10. `skills/article-writing` — off-remit; operator's call, default skip

Competent content — the banned-pattern list, proof-before-explanation structure, quality gate —
but long-form marketing/editorial writing is outside an SDE/SRE fleet's remit, and no fleet
member borders it (no routing home, no consumer). It also hard-depends on a `brand-voice` skill
that isn't in the batch (aspirational reference, fifth sighting). If the operator wants a writing
capability, this is a reasonable seed — registered as an operator decision; importing it would
need a reworked action-shaped description and removal of the `brand-voice` dependency.

---

## What this batch validates (same list as batch 1, now with more evidence)

- **Enforcement over recitation** — `agent-evaluator`'s prose allowlist vs `readonly-guard.py`:
  the same list, one advisory, one fail-closed. The comparison is now side-by-side.
- **Measured overlap** — `agentic-engineering`/`ai-first-engineering` overlap each other;
  `architect` overlaps `homelab-architect`; none has negative routing or an eval.
- **Descriptions route; bodies condition** — five of seven skills carry body-level "When to
  Activate"/"When to Use" sections below the routing decision.
- **Provenance in commits, not frontmatter** — `metadata.origin`, `license`, `version` keys would
  all fail `KNOWN_SKILL_FIELDS` here, by design.
- **Categorical confidence** — numeric `confidence: 0.0` and 1–5 axes appear in both batch-1 and
  batch-2 components; the fleet's categorical triad keeps not needing them.

## Compliance checklist — the landed imports

Same gates as both standing docs: all three landings are body-only — no `description:` touched,
so no routing-eval surface; no new files, so no orphan-check surface and no README inventory
change; canonical evidence-label stems untouched; validator + unit tests +
`claude plugin validate . --strict` run at land time; provenance (`adapted from affaan-m/ECC`,
MIT) in the landing commit message.

## Sequencing

1. **Landed with this review:** item 4 residue (`multi-agent-architect` wrapper diagnostics +
   tier-escalation line), item 9 residues (`backend-craft` version lifecycle + rate-limit
   headers), item 8 method (`consuming-apis.md` exemplar-first bullet).
2. **Registered in `docs/sre-agents-adaptation-backlog.md`:** eval doctrine (item 5) folded into
   the finding-7b behavioral-eval entry; the optional `principal-engineer` agent-legibility clause
   (item 7); the `article-writing` operator decision (item 10); the raised priority of backlog 1.3
   (item 9 hazard).
3. **Explicitly not done:** extending `multi-agent-architect`'s *description* with wrapper-app
   phrasing ("my LLM app got worse after adding a layer"). It would sharpen routing but is a
   description edit — gated on running the affected routing cluster before and after, which is
   manual and on demand. Take it up only with eval time budgeted.

Source snapshot: `affaan-m/ECC` @ `main`, raw fetch 2026-07-24 (API access out of session scope;
snapshot dated, not SHA-pinned).
