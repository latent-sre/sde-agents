# Adaptation backlog — imports from `latent-sre/sre-agents` — July 2026

**Question:** which agents and skills from the sister repo `latent-sre/sre-agents` (enterprise-SRE
fleet, components under `.claude/agents/` and `.claude/skills/`) are worth adapting into this
plugin?

**Method:** three-pass independent research. Pass 1 — component-by-component quality/portability
review of the donor. Pass 2 — portfolio-gap review starting from this fleet's needs. Both passes
were blind: definition files only, no access to either repo's `docs/`, READMEs, prior reviews, or
git history, and they ran without sight of each other. Pass 3 — adversarial verification of the
union of their candidates against the actual files: every load-bearing claim re-checked, every
disputed verdict adjudicated, licensing and validator-invariant compliance checked. Only findings
that survived Pass 3 appear below.

**Licensing:** both repos are MIT; copying is legal in both directions. Note provenance
(`adapted from latent-sre/sre-agents`) in commit messages for substantial imports.

**Headline finding (all three passes converged independently):** this fleet is a *descendant* of
sre-agents — shared passages, byte-identical templates — and where the two diverge, this repo's
copy is almost always the more evolved one (e.g. categorical confidence vs. the donor's numeric
"9/10"; the plugin-aware frontmatter reference). Wholesale import would regress. The value is in
what the fork **dropped or never had**: the donor kept an entire detect→respond→learn loop
(incident method, observability craft, postmortems) and language-level idiom guidance that this
fleet demands ("match the codebase's idioms") but nowhere supplies. Independent cross-check: the
two blind passes re-derived `incident` and `postmortem` — the same top gaps
`docs/skills-modernization-plan.md` had already identified — without being allowed to read it.

Donor paths below are relative to the sre-agents repo root (`.claude/skills/...`,
`.claude/agents/...`).

---

## Tier 1 — high value, verified clean, low collision risk

### 1.1 Reviewer security lens → `agents/code-reviewer.md`

Donor `agents/reviewer.md:76-118` carries a full security-review section this fleet's
code-reviewer lacks despite listing security as dimension 2: per-category checklist (injection,
authn/z, secrets/crypto, deser/SSRF/traversal, agentic/prompt-injection with an inline
lethal-trifecta mini-check, supply chain, misconfig), the CI/CD "pwn request" class
(`pull_request_target` / `workflow_run` with secrets in scope), a CWE-referenced finding format
with a mandatory attack path, and the confirm-exploitability/downgrade-if-unreachable rule.
Biggest per-line payoff in the whole backlog; also gives `sre-tool` Phase 3 item 6 (the
security-only second review pass) the checklist it currently assumes exists.
**Adapt:** keep this fleet's categorical-confidence convention; route "active compromise" to the
human operator with preserve-evidence framing (donor hands to its `sre` agent).

### 1.2 Observability pack → one new `observability` skill

The largest genuine capability gap: `homelab-platform`, `service-onboard` step 6, and `lab-audit`
all *demand* monitoring; nothing teaches how — and the donor's stack-neutral column is exactly the
lab's declared stack (Prometheus, Grafana, Loki, Alloy). Consolidate the donor's six `obs-*`
skills into **one** skill with a predicate-keyed reference table (the `backend-craft` model), not
six new routing descriptions.

- **References verified clean (adopt):** `obs-metrics/references/promql.md`,
  `obs-logs/references/logql.md`, `obs-traces/references/traceql.md` and `otel-semantics.md`,
  `obs-alerting/references/burn-rate.md` (window/threshold pairs bound as a unit) and
  `grafana-alerting.md` (keep the full-policy-tree-overwrite warning; scrub one Moogsoft cell),
  `obs-dashboards/references/provisioning.md`, `obs-pipeline/references/otel-sdk.md`
  (tail-sampling failure modes) and `alloy.md` (3 lines to scrub),
  `obs-alerting/scripts/error_budget.py` (verified pure stdlib).
- **SKILL bodies:** four of six are dialect-neutral; `obs-dashboards` (licensing bullets) and
  `obs-pipeline` (Wavefront naming section) need surgery. Retarget every `sre-steward`/`sre`
  handoff to `sde-agents:homelab-platform`.
- **Exclude:** `spl.md`, `wql.md`, `indexes.md`, `metrics.md`, `moogsoft.md`, `thousandeyes.md`,
  `wavefront-legacy.md`. `traceql.md`/`otel-semantics.md` are optional if the lab runs no Tempo —
  mark the row accordingly rather than dropping the files.
- **Description:** owns query/alert/dashboard/pipeline *design*; live-lab applies route through
  `sde-agents:homelab-platform`'s tiers (the `lab-audit` precedent). Soften multi-window burn-rate
  ceremony to lab scale. Name the skill in `service-onboard` step 6.

### 1.3 RFC 9457 error-shape correction + OpenAPI starter → `skills/backend-craft`

Verified defect in a shipped skill: `backend-craft/SKILL.md:16-24` teaches a **nested**
`{"error":{...}}` envelope and mislabels it "problem+json style". The donor's version teaches
top-level RFC 9457 `application/problem+json` (`type`/`title`/`status`/`detail`/`instance` +
extensions) with "never a nested error envelope" — accurate to the standard and tool-supported.
Adopt the donor's error section; port `backend-craft/assets/openapi.starter.yaml` (problem+json
schema, Idempotency-Key, cursor pagination worked concretely) after scrubbing two comments (PCF
probe, corp SSO/UAA); link it from the contract-first section. Consider the donor's
breaking-change-is-principal-altitude compatibility rule in the same pass.

### 1.4 New skill: `postmortem`

No component owns learning-after-failure. Near drop-in from donor `postmortem/SKILL.md`: blameless
structure, trigger-vs-cause separation, the mitigative-vs-preventative action table, and "where we
got lucky" ("luck is a preventative action item waiting to be written").
**Adapt:** strip SEV header, IC-log seed, typed-agent handoffs; reframe blameless for one operator
("what made the mistake easy"); pair with `sde-agents:root-cause` and `sde-agents:lab-incident`.
Converges with the modernization plan's `incident` postmortem half.

### 1.5 New skill: `lab-incident` (+ root-cause deferral clause)

Verification found this gap worse than either pass claimed: the fleet has *zero* incident content,
and its only debugging doctrine (`root-cause`) is diagnose-before-fix — actively wrong mid-outage.
Build from donor `incident-command/SKILL.md:97-137` mitigate-first core: the mitigation-decision
table (rewritten for compose rollback / proxy route revert / restart / flag / restore), one-change-
then-observe, "restart is a stopgap, not a fix", downgrade-only-when-signals-hold-at-baseline, and
the security carve-out (don't restart a compromised box — preserve evidence, `:43-49`). Reference:
`eng-ladder/references/golden-signals.md` (60-second signal read, "what changed" checklist, signal
patterns) with donor-stack columns replaced by Grafana/Loki/`docker` equivalents.
**Skip** the SEV1-4/IC-roles/comms machinery, and donor `responder.md`/`investigator.md`
(redundant with homelab-platform's tiers + root-cause's loop); `elite.md`'s systemic-failure
catalog (retry storms, metastable failure) is an optional second reference, low priority.
**Routing:** mitigations are Tier 2/3 applies under `sde-agents:homelab-platform` — route through
it, not as a peer trigger (highest-value import is also the highest collision surface). Add one
deferral clause to `root-cause`'s description ("live outage → mitigation-first via
sde-agents:homelab-platform precedes this loop"). Do NOT land the donor refs in `eng-ladder` —
its own line 25 places infrastructure operation outside that ladder.

## Tier 2 — solid adds, moderate adaptation

### 2.1 New skill: `craft` (language idiom + TDD + safe refactor)

`sde-fullstack` demands "match the codebase's idioms"; nothing supplies them. Adopt donor
`craft/SKILL.md` (32-line router) + `references/python.md` (decision-vs-effect dry-run proven with
a spy), `bash.md` (`set -e` leak analysis, `((i++))` trap, `rm -rf "${dir:?}"`), `go.md`,
`tdd.md`, `safe-refactor.md`. **Adapt:** drop `powershell.md`; scrub "this team"/RHEL7 asides;
namespace the ownership map (`sde-agents:backend-craft` etc.); dedupe expand→migrate→contract —
`eng-ladder/references/principal.md` already owns it, so safe-refactor defers with an on-conflict
line (house convention). Wire into `sde-fullstack`'s `skills:` preload or a predicate row.

### 2.2 New skill: `ci-actions`

No CI-authoring coverage exists. Donor content verified current and concrete: SHA-pinning with the
tj-actions compromise, `${{ github.event.* }}` script injection, `pull_request_target` pwn
request, least-privilege `permissions`, actionlint/zizmor, attestation/SBOM.
`assets/ci.reusable.yml` (SHA-pinned uv/ruff/mypy/pytest) is already clean — the PCF matter lives
in the SKILL body, not the asset. **Adapt:** cut the PCF deploy half; the ephemeral self-hosted
runner guidance ports well to homelab deploy targets — keep it, gated on the tiers.

### 2.3 `ops-tooling/references/cli.md` + `assets/cli_skeleton.py` → `skills/sre-tool`

The fork kept the four coordination templates but lost the CLI contract: exit-code/streams
discipline (stdout result, stderr logs, `| jq` stays clean), stable `--json`, flag > env > config
precedence, secrets-never-in-argv, dry-run proven with a spy — plus an 86-line Typer skeleton
demonstrating all of it. Near drop-in: scrub one `cf` line and one donor-`craft` ownership line;
add the routing line in `sre-tool/SKILL.md` (orphan check requires it).

### 2.4 New skill (or prompt-craft reference): `agent-security` + two authoring references

The fleet authors agents but has no security-review method for them — only scattered
fetched-content one-liners. Adopt the trifecta legs, Rule of Two, delegation-is-not-isolation,
hash-binding. **Adapt:** rewrite the donor "Runtime boundary" section around this plugin's actual
guard (`hooks/hooks.json` + `GUARDED_AGENT_NAMES`) — the donor describes per-agent frontmatter
hooks, which are inert in a plugin. Also adopt `agent-authoring/references/tools.md` (tool-surface
design, bash→tool promotion) and `context.md` (JIT retrieval, compaction, rewind-beats-correct)
into `prompt-craft/references/` with routing lines. **Never import `agent-authoring/SKILL.md`
itself** — near-verbatim duplicate of `prompt-craft` and asserts plugin-false facts
(`Agent(type)` scoping, bare-name skill invocation).

### 2.5 `database-reliability` → `skills/backend-craft/references/database-reliability.md`

Adjudicated landing: a backend-craft reference, not a new skill (skills own layers; references
load by predicate; `persistence.md` is verified write-side-only). Keep: the
EXPLAIN-ANALYZE-**executes** warning table with the `BEGIN; … ROLLBACK;` recipe and its
sequence/FDW caveats; `CHECK (col IS NOT NULL) NOT VALID` → backfill → `VALIDATE`; expand→contract
mechanics; saturation triage; RPO/RTO + tested restores. **Adapt:** trim Oracle
licensing/PCF/typed handoffs; split the routing row ("a schema migration on a live database,
a slow query, or lock/pool contention → this file"); persistence.md gains a one-line pointer;
the triage bullet defers to `lab-incident`.

## Tier 3 — small, surgical

- **3.1 Runbook idea-imports** (not the donor template — it would create a second, competing
  required structure): machine-linkable frontmatter (`alert_names`, `last_verified`) that pairs
  with the obs pack's `runbook_url` linking; the runbook/playbook/SOP distinction; the
  rehearse-or-it-rots rule (game days = the restore drill). If an asset is wanted, generate it
  from this fleet's own 7-slot structure.
- **3.2 Worked hypothesis table → `root-cause`** (likelihood × cheapness-to-test, Result column) —
  matches the fleet's house "worked example" style; append without disturbing the three-strikes
  ownership sentence.
- **3.3 One sentence → frontmatter reference:** `Bash(...)`-style scoped specifiers are **inert on
  agent `tools:` lists** (validator already enforces; the declared single-source-of-truth file
  doesn't state it).
- **3.4 "What a rollback does NOT reverse" → `homelab-platform` Prime directive 1**, rephrased for
  compose/images: the migration the new version ran; changes outside the compose file; anything
  consumers already did with the new version's output.
- **3.5 Stale-approval-SHA discipline → `code-reviewer`** (+ echoes sre-tool Phase 3.5): record
  the SHA reviewed; the verdict applies to that SHA only; any later commit touching reviewed files
  re-enters review. The only survivor of donor `merge-gate`.
- **3.6 `researcher` agent — optional adopt.** The one agent-shaped candidate that passes this
  fleet's own distinct-tool-scope test (`Read, Grep, Glob, WebSearch, WebFetch` — no Bash, no
  Write; a cheap isolation spawn target no current agent provides), with a real method
  (memory-is-a-lead-not-a-source, adversarial verification, KEV-first) and output contract.
  Validator-hard adaptations required: add `model: inherit`; rename `## Output contract` →
  `## Output format`; canonical evidence-label stems; delete the donor's false-here
  "network allowlist is the load-bearing control" claim and state egress honestly; narrow the
  description to spawn-shaped phrasing. Fallback if roster growth is unwanted: fold its output
  contract into prompt-craft as a research method.
- **3.7 Lab-profile pattern — convention + template, never a plugin skill.** One file of lab-wide
  stack facts + a stay-in-lane rule ("do not suggest Kubernetes; hand platform-internal problems
  up"), living in the *lab repo's* project context per the environment-card convention. Land as a
  template (e.g. asset) + one read-before-proposing line in `homelab-platform`/`service-onboard`.

## Killed — do not import (with reasons)

- **`merge-gate` as a skill** — routing collision verified: its trigger "is this ready to merge"
  is literally in `code-reviewer`'s description; branch-protection machinery presumes an org.
- **`production-change-gate`** — same lineage as homelab-platform's tiers; two owners of one gate,
  and its prepare-only/human-executes model contradicts the approved-apply model.
- **`service-onboarding`** — duplicate of `service-onboard` + `lab-audit`.
- **`sre` / `sre-steward` as agents** — their value arrives as the Tier 1 skills; as agents they
  carry enterprise separation-of-duties and inert-in-plugin frontmatter hooks.
- **`agent-authoring/SKILL.md` body** — duplicates `prompt-craft`; asserts plugin-false facts.
- **Donor twins of existing components** (sde, reviewer body, ops-tooling, eng-ladder eng track,
  root-cause/runbook/backend-craft/frontend-craft/prompt-engineer bodies) — this repo's copies are
  the refined descendants; import only the named residue above.
- **All PCF/Splunk/Wavefront/Moogsoft/ThousandEyes material** — no homelab analogue.

## Compliance checklist — every import

1. `sde-agents:` namespacing for any component named in a `description:`.
2. Every bundled `references/`/`assets/`/`scripts/` file linked skill-relative from its SKILL.md
   (orphan + resolution checks).
3. Canonical evidence-label stems; packet heading matches `PACKET_HEADING_RE`
   (`## … packet` / `## Output format`).
4. Agents: `model:` alias required; explicit `tools:`; no `hooks`/`mcpServers`/`permissionMode`;
   no scoped `Bash(...)`/`Agent(type)` grants; Bash-holding read-only agents registered in
   `scripts/readonly-guard.py`'s `GUARDED_AGENT_NAMES`.
5. Scrub donor voice: "Evidence default" blockquotes, terminal-canary comments, `~/.claude` paths,
   donor agent names, `py -3` invocations.
6. Regenerate the README inventory (`python3 scripts/validate_fleet.py --write-inventory`); run
   the validator, the unit tests, and `claude plugin validate . --strict`.
7. New/changed descriptions get routing-eval coverage: extend the relevant cluster (or seed a new
   one) and diff against the July 2026 baselines before/after — `lab-incident` vs `root-cause` vs
   `homelab-platform` is the highest-collision surface and needs negative cases.

## Related open work (pre-existing backlog, folds into the tiers)

From `docs/skills-modernization-plan.md` and the July 2026 best-practices re-check:

- Modernization Tier 1 `incident`/postmortem → **superseded by items 1.4/1.5** (richer donor
  source material); `restore-drill` and `upgrade-campaign` remain open as originally planned;
  `security-seed.md` for sre-tool partially served by 1.1's checklist.
- Frontmatter reference: record deliberate non-use of `effort` and the `context`/`agent`/`paths`
  rationale in "Fleet decisions on unused fields"; note the five hook types (`command`, `http`,
  `mcp_tool`, `prompt`, `agent` — verified against live docs 2026-07-18) and why the guard stays
  `command`; plus item 3.3 above.
- `lab-audit`: add `NotebookEdit` to `disallowed-tools`; `allowed-tools` pre-approvals with pinned
  verbs; `references/checks.md` + findings ledger (modernization Tier 2 item 6).
- `prompt-craft`: eval-wiring line in Method step 4 (repo has routing evals → run the harness
  before/after).
- `runbook`: worked example reference (merges with 3.1).
- `eng-ladder`: infra-that-is-also-architecture exception clause on the homelab routing line;
  H1-title convention sweep across skills.

From `docs/ecc-skills-agents-review.md` (July 2026; that file owns the adjudication detail —
its Tier 1/2 imports are landed, these are what remains):

- **Packet-lint assert helper** (ECC review item 3a) — stdlib script asserting packet-slot
  presence and flagging hedge-claims that carry no evidence label; missing evidence fails, never
  "assumes correctness" (the inversion of ECC's `evaluate.py`, whose smell regexes seed the
  vocabulary). Deliberately sequenced *inside* the behavioral-eval work (quality review
  finding 7b) as its deterministic assert — do not build it standalone before that consumer
  exists, and never wire it as a live hook (it would train packet-shaped evasion).
- **Behavioral verification of the landed a11y imports** — the ECC imports shipped `[unverified]`
  on impact: no descriptions changed (so routing evals didn't apply), and no behavioral eval
  asserts reference compliance yet. On the next real UI task involving a modal, toast, or form,
  check the packet names `interaction-a11y.md` (or `forms.md`'s wiring bullets) and carries
  keyboard-pass evidence. Two misses trigger the `self-improve-loop` micro-retro: fix the
  definition, not the workflow. A durable assert belongs in the same finding-7b eval set.

## Sequencing

1. Tier 1 in order (1.1 → 1.5), validator + tests + `--strict` at each step; seed/extend routing
   evals before landing 1.2 and 1.5 (new descriptions).
2. Tier 2, then Tier 3, same gates.
3. Fold the "related open work" items in wherever they touch the same file as a tier item (one
   change per file-owner, not two passes).

Source snapshot: `latent-sre/sre-agents` @ `e2eef27` (2026-07-18 clone).
