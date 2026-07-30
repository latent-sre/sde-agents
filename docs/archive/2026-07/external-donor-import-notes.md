# Import notes — 2026-07-30 external-donor graft round

**Status: historical evidence** (dated import adjudication, per `docs/README.md`). These are the
adaptation notes the porting method requires — the implementation specification the round's grafts
were built from. Method: `README.md` → "Importing from another fleet (the porting method)".
Operator supplied 20 sources across two requests; donor-blind sonnet readers covered the three
lenses per bundle (assessment grade — one reader per bundle rather than three per donor; the
graft-bearing sources were re-read verbatim from upstream at import time). Durable menu:
memory `external-skills-mining-2026-07-30`. Reviewed SHAs and licenses: `THIRD_PARTY_NOTICES.md`.

## Lineage findings (checked before value)

Three supplied sources were copies; adjudication moved to their upstreams:

- `zebbern/claude-code-guide` react-best-practices → vendored, unmodified **Vercel**
  (`vercel-labs/agent-skills`) snapshot, 13 rules stale (57 vs 70; upstream metadata frozen at the
  pre-growth values — drift detectable only by diffing file lists).
- `ComposioHQ/awesome-claude-skills` skill-creator → stale fork of **Anthropic's** official
  skill-creator, generations behind (upstream `anthropics/skills` gained a full eval-driven
  workflow); the fleet already mined the official skill (PR #24). Rejected as a donor.
- `sickn33/agentic-awesome-skills` — all three supplied skills are catalog copies:
  frontend-ui-engineering ← addyosmani (credited), frontend-optimistic-mutations ←
  **stareezy-1/frontend-architecture-skill** (credited), frontend-developer ← wshobson/agents
  (uncredited; character-identical sentences). Value adjudicated against the upstreams.

## What grafted, and where

| Donor (license) | Grafted into |
|---|---|
| vercel-labs react-best-practices + composition-patterns (MIT via SKILL.md frontmatter; repo has no LICENSE file) | `code-craft/references/typescript.md` (new): waterfalls, defer-await, module-scope-is-shared-memory, barrel imports, derived-state-in-render, no inline components, memo both directions + React Compiler carve-out, boolean-props→variants, compound components with `{state, actions, meta}`, provider-boundary-not-visual-nesting, children-over-render-props with its stated exception, React 19 ref/`use()` |
| stareezy-1 frontend-optimistic-mutations (MIT) | Same file, write-path section: five-beat lifecycle (cancel→snapshot→patch→rollback-verbatim→invalidate-on-settle), when-not-optimistic, multi-cache lock-step via key factory, idempotency key at first intent never in `mutationFn`, retry stratification incl. 409-never-retries |
| addyosmani api-and-interface-design + frontend-ui-engineering (MIT) | Branded ids / discriminated unions / input-output separation → `typescript.md`; three stock component tells → `frontend-craft/SKILL.md` self-critique line |
| alirezarezvani api-test-suite-builder + engineering-team twins (MIT) | Endpoint failure matrix → `backend-craft/SKILL.md`; spec-diff CI gate → `backend-craft/references/api-design.md`; fork kill-criterion → `agents/sde-fullstack.md` |
| alleneubank python-best-practices (Apache-2.0) | `NewType` domain ids, `Literal` unions + `match`, `Protocol` → `code-craft/references/python.md` |
| trailofbits modern-python (CC BY-SA 4.0 — concepts only, zero adapted expression) | PEP 735 dependency-groups rule (restated from the PEP) → `python.md`; dependency-cooldown rationale (fleet's own words) → `ci-actions/SKILL.md` |
| Neeeophytee progressive-disclosure (MIT + Thariq attribution) | Split-boundary test, name-by-role, stop-splitting rule → `prompt-craft/references/context.md` |
| Anthropic blog corpus + platform docs (claude.com/blog 2026; code.claude.com/docs) | Model-generation section → `prompt-craft/SKILL.md`; new-task-new-session → `context.md`; verification-skill capture + deployment shapes + claim-level line → `self-improve-loop/SKILL.md`; doc-verified platform facts (`/doctor`, `/verify`, `${CLAUDE_PLUGIN_DATA}`, `CLAUDE_ENV_FILE`, component-scoped hooks) → `claude-code-frontmatter.md` |

## Rejected, with reasons

- **All eleven alirezarezvani scripts** — senior-backend's SKILL.md documents CLI flags its
  scripts don't implement (`--connection`, `--migrate`, `--dry-run`, `--from-db`), its
  description is malformed YAML, and `api_load_tester.py` live-fires HTTP with `--no-verify-ssl`
  and no confirmation. The prose discipline ("attach tool outputs") is already fleet-wide doctrine.
- **VoltAgent fullstack-developer / sickn33 frontend-developer / wshobson api-documenter** —
  persona-framed capability inventories (~80–90% / ~30–40% filler), a communication protocol
  addressed to an inter-agent JSON bus Claude Code does not have, no verification loops. The
  fleet's `sde-fullstack` is stronger on every compared axis; api-documenter's one good inversion
  (docs examples are contract tests) is already covered by backend-craft's contract-testing rule.
- **Trail of Bits PATH-shim hook** — the best-engineered hook reviewed (fail-open preconditions,
  self-recursion-avoiding passthrough, 42 bats tests), but it mutates every session unconditionally
  to enforce a uv-only policy with no observed fleet failure, and the license is CC BY-SA. Recorded
  as the reference example if environment-level enforcement is ever needed; `CLAUDE_ENV_FILE`
  itself was doc-verified and recorded as a platform fact.
- **vercel-optimize as an import** — deterministic gates, typed-claim verification with a
  pass-rate-gated bounded regeneration loop, version-aware citation allow-listing: a reference
  architecture for any future LLM-output-verification pipeline, with no fleet consumer today. One
  distilled line landed in `self-improve-loop`.
- **react-native-skills** (no mobile remit), **react-view-transitions** (hard-gated to
  `react@canary` / Chromium 125+ / Next 16.2 — revisit when stable), **deploy-to-vercel /
  vercel-cli-with-tokens** (platform-operational; the consent-gate and secrets-not-in-argv
  patterns are already owned), **web-design/writing-guidelines** (fetch shims with no in-repo
  content), **api-design-reviewer / api-and-interface-design prose** (`api-design.md` already
  owns Hyrum's law, the breaking-change taxonomy, and the deprecation protocol), **forcing-question
  numeric stances** (team-size/ARR thresholds — out of register and anti-evergreen; only the
  kill-criterion transferred).
- **One conflict recorded, not resolved**: Thariq's 2026-07-24 post reports worked examples can
  constrain Claude 5-generation models; the official best-practices doc still recommends them.
  The fleet keeps its compressed worked examples; `prompt-craft` carries the stamp and the reopen
  trigger (the docs page moving).

## Contribute-back candidates (recorded, not acted on)

- Upstream `vercel-labs/agent-skills`: three sampled rule files carry a doubled `---` frontmatter
  delimiter (`advanced-effect-event-deps`, `navigation-native-navigators`,
  `scroll-position-no-state`) that most parsers read as an empty frontmatter block; rule counts in
  README/metadata lag the tree by up to 2×.
- Upstream `addyosmani/agent-skills`: skills reference a repo-root `references/` directory by
  skill-relative path, so any standalone copy ships a dead link; `api-and-interface-design`'s
  description promises GraphQL and component-prop content its body doesn't contain.
- Upstream `alirezarezvani/claude-skills`: the senior-backend doc/CLI mismatch and unescaped
  quotes in its description YAML, as above.
- Convergences worth noting upstream someday: the fleet's validator-generated README inventory vs
  Vercel's systemic doc drift; the fleet's orphan-reference check vs addyosmani's dead link — both
  external demonstrations of failure classes the fleet already gates.

## Gates

One description edit (`code-craft` gains the TypeScript trigger) →
`evals/routing/craft-vs-fullstack.json` run before and after under pinned conditions
(`--runs 3 --model opus --timeout 420 --clean-room`), artifacts in
`evals/baselines/2026-07-30-donor-grafts/{before,after}`; `pos-typescript-branded-ids` +
`neg-typescript-build-slow` were seeded ahead of the baseline, mirroring the Round 1 powershell
pair. Everything else is body-only. Validator, unit tests, and `claude plugin validate --strict`
run on the branch before push.
