# External-Donor Grafts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This round is being executed inline by the adjudicating session (operator-approved "get to it"; direct execution satisfies the subagent model ceiling).

**Goal:** Land the twelve operator-approved donor grafts (spec:
`docs/superpowers/specs/2026-07-30-external-donor-grafts-design.md`) with the porting method's
gates: fresh-worded adaptations, provenance recorded twice, validator/tests green, and the
craft-vs-fullstack routing cluster diffed before/after the round's one description edit.

**Architecture:** One new reference file (`typescript.md`) plus ten surgical body edits across
eight existing definitions. No new agents or skills; no hook changes; no script changes.

**Tech Stack:** Markdown definitions; Python stdlib gates (`validate_fleet.py`, unittest);
`scripts/eval_routing.py` for the routing gate.

## Global Constraints

- Fresh wording everywhere; CC BY-SA sources (Trail of Bits) contribute concepts only.
- No version pins in evergreen guidance; version-conditional phrasing allowed where the condition
  is the content ("on React 19+").
- Body edits only, except the single `code-craft` description widening (Task 2).
- Surgical diffs — no adjacent reformatting; markdown wraps at ~100 columns.
- Eval conditions pinned and identical both sides: `--runs 3 --model opus --timeout 420
  --clean-room`, artifacts under `evals/baselines/2026-07-30-donor-grafts/{before,after}`.
- Commits carry `adapted from <repo> (<license>)` lines; `THIRD_PARTY_NOTICES.md` gains one entry
  per donor actually grafted.

---

### Task 0: Baseline (already in flight)

**Files:** Modify: `evals/routing/craft-vs-fullstack.json` (two seeded cases — DONE); artifacts →
`evals/baselines/2026-07-30-donor-grafts/before/`

- [x] Seed `pos-typescript-branded-ids` (expects `code-craft`; non-UI prompt so frontend-craft is
      not a legitimate route) and `neg-typescript-build-slow` (diagnosis decoy), mirroring the
      Round 1 powershell pair; note the seeding in the cluster `notes`.
- [x] Launch BEFORE run on the unedited definitions (background):
      `python scripts/eval_routing.py evals/routing/craft-vs-fullstack.json --runs 3 --model opus --timeout 420 --clean-room --output-dir evals/baselines/2026-07-30-donor-grafts/before`
- [ ] **No `skills/` or `agents/` edit may land until this run completes** — the runner loads the
      working tree via `--plugin-dir .`.

### Task 1: `skills/code-craft/references/typescript.md` (new)

**Files:** Create: `skills/code-craft/references/typescript.md`
**Sources (fetch these raw and verify each kept claim before writing):**
- `vercel-labs/agent-skills` (MIT via frontmatter) — `skills/react-best-practices/rules/`:
  `async-parallel.md`, `async-defer-await.md`, `rerender-derived-state-render.md` (or the rule
  covering derived-state-during-render), `rerender-no-inline-components.md`,
  `server-no-shared-module-state.md`, `bundle-barrel-imports.md`, and the useMemo-boundary rules;
  `skills/composition-patterns/rules/`: `architecture-avoid-boolean-props.md`,
  `patterns-explicit-variants.md`, `state-context-interface.md`, `state-lift-state.md`,
  `patterns-children-over-render-props.md`, `react19-no-forwardref.md`,
  `architecture-compound-components.md`.
- `stareezy-1/frontend-architecture-skill` (MIT) — `skills/frontend-optimistic-mutations/SKILL.md`
  (five-beat lifecycle, idempotency-key timing, retry stratification, cache lock-step).
- `addyosmani/agent-skills` (MIT) — `skills/api-and-interface-design/SKILL.md` (branded types,
  discriminated unions, input/output separation).

**Shape** (mirror `references/python.md`: one H1, trap/idiom register, a Verify close; target
100–140 lines):
1. Header: read before writing TypeScript/JavaScript, React included; SKILL.md wins; repo
   conventions outrank both. One boundary line: state *placement* across an app is
   `sde-agents:frontend-craft`'s ground — this file owns what the code does inside the module.
2. **Make the compiler catch what review would miss** — branded ids; `Literal`-style discriminated
   unions with exhaustive `switch`; input/output type separation.
3. **Traps that produce wrong behavior, not errors** — floating promises; sequential awaits on
   independent work (waterfalls; `Promise.all`); awaiting before the value is needed; module scope
   on a server is process-wide shared memory (request data leaks across users); barrel imports
   (import deep or use the framework's optimizer).
4. **React: rendering and structure** — derived values compute during render, never
   effect-plus-setState; memo boundaries both sides (memoize the expensive, never the trivial); no
   component definitions inside a render; explicit variant components over boolean-prop
   proliferation; compound components = object of sub-components + one context with a
   `{state, actions, meta}` shape; the provider boundary grants access, not visual nesting;
   children over render props except per-item data; on React 19+ `ref` is a prop (forwardRef is
   legacy).
5. **The write path (query/cache layer)** — five beats (cancel → snapshot → patch → roll back
   verbatim → invalidate), and why skipping cancel loses (late refetch clobbers the patch); when
   NOT to be optimistic (server-owned fields → pending + seed cache; destructive → confirm);
   idempotency key minted at first intent, never inside the mutation function; non-idempotent
   writes never auto-retry and 409 never auto-retries; one entity lives in many caches — patch and
   roll back all of them.
6. **Verify** — typecheck at the repo's strictness, tests, and the frontend-craft browser gate for
   anything rendered.

- [ ] Fetch the listed source files verbatim; confirm each kept technical claim.
- [ ] Write the file in fleet register (fresh wording throughout).
- [ ] Task 2's routing row makes it non-orphaned; validator confirms.

### Task 2: `skills/code-craft/SKILL.md` — routing row + description widening

**Files:** Modify: `skills/code-craft/SKILL.md`

- [ ] Description: `…Use when writing or reviewing Python, TypeScript, Bash, PowerShell, or Go…`
      (insert `TypeScript, `; no other description text changes).
- [ ] Reference table: after the Python row insert
      `| TypeScript or JavaScript — including React | [`references/typescript.md`](references/typescript.md) |`

### Task 3: `skills/prompt-craft/SKILL.md` — model-generation section

**Files:** Modify: `skills/prompt-craft/SKILL.md` (insert after "The two rules" section)

- [ ] Insert verbatim:

```markdown
## When a new model generation lands

Try **removing instructions first** — each generation needs less scaffolding (Anthropic cut over
80% of Claude Code's system prompt for the Claude 5 models with no measured loss). Audit absolute
bans into contextual judgment ("never write multi-paragraph docstrings" → "match the surrounding
code's comment density"); the pressure-discipline row of the form table above is the exception
that stays absolute. When trimming a skill body, keep the gotchas — hard-won failure points are
the highest-signal content a skill carries; generic workflow prose is what goes.

One recorded conflict (stamped 2026-07): the official skill-authoring doc still recommends worked
input/output examples, while the Claude 5-era context-engineering guidance reports examples can
constrain exploration. The fleet keeps its compressed worked examples — re-decide when the docs
page moves.
```

### Task 4: `skills/backend-craft/SKILL.md` — endpoint failure matrix

**Files:** Modify: `skills/backend-craft/SKILL.md` (Testing & quality gate list, after the
"Mock the upstreams" bullet)

- [ ] Insert verbatim:

```markdown
- **Every endpoint earns a failure matrix**, not just a happy-path test: auth in its four shapes
  (missing, expired, malformed credential → 401; authenticated-but-wrong-role → 403), the
  validation split exercised (400 malformed vs 422 semantically invalid), 404 on absent resources,
  429 asserting `Retry-After` is present — and where the endpoint takes an idempotency key,
  replaying the key returns the recorded response, not a second effect. Uploads verify magic
  bytes, never the extension or declared Content-Type.
```

### Task 5: `skills/self-improve-loop/SKILL.md` — capture rule + deployment shapes

**Files:** Modify: `skills/self-improve-loop/SKILL.md` ("Move the lesson left" paragraph)

- [ ] Extend the encode list `…a test, a lint rule, a validator rule, a hook…` to
      `…a test, a lint rule, a validator rule, a hook, or a project-specific verification skill —
      anything you keep enforcing by hand qualifies for capture…`
- [ ] Append after that paragraph, verbatim:

```markdown
A captured verification skill deploys four ways — invoked deliberately after the artifact exists,
embedded in the producing skill's own steps, chained behind other checks, or run on every PR once
proven. Start standalone and chain only after it catches something real: every link in a chain
re-spends tokens. For generated reports and recommendations the strongest form is claim-level —
extract the output's checkable claims, verify each against ground truth, regenerate (bounded) on
failures.
```

### Task 6: `skills/code-craft/references/python.md` — domain typing + PEP 735

**Files:** Modify: `skills/code-craft/references/python.md`

- [ ] Idioms list, after the dataclasses bullet, insert verbatim:

```markdown
- **Type the domain, not just the shape.** `NewType("UserId", str)` costs nothing at runtime and
  stops an order id crossing into a user-id slot at check time. Variants are a
  `Literal`-discriminated union dispatched with `match`, not a string field plus `if`s; accept
  capabilities structurally with `Protocol` ("has a `read()`"), not by inheritance.
```

- [ ] Tooling bullet: append `Dev-only tools belong in PEP 735 `[dependency-groups]`, not
      `[project.optional-dependencies]` — extras ship to your users, groups don't.`

### Task 7: `skills/prompt-craft/references/context.md` — split heuristics + session boundary

**Files:** Modify: `skills/prompt-craft/references/context.md`

- [ ] Under "Just-in-time beats up-front", after the predicate-keyed bullet, insert verbatim:

```markdown
- **Splitting an oversized file** into an entry plus siblings: the test of a boundary is that the
  entry stays comprehensible alone — needing a sibling open to follow it means the cut is in the
  wrong place. Name siblings by content role (`verification.md`, not `notes.md`) so the filename is
  the trigger, and write pointers that name both trigger and target ("touching migrations? read
  `migrations.md` first"). Splitting removes nothing — delete obsolete content outright — and stop
  splitting while the entry file is still legible.
```

- [ ] Under "Long runs", append verbatim:

```markdown
- **A new task gets a new session.** Compaction manages a long run; it does not make a finished
  task's residue useful to the next one. Carrying a window across unrelated tasks buys nothing and
  costs attention.
```

### Task 8: `agents/sde-fullstack.md` — kill criterion

**Files:** Modify: `agents/sde-fullstack.md` ("Ask the forks, assume the details" bullet)

- [ ] After "One question round is cheaper than one wrong build." append:
      `An answer that dodges the fork — "as fast as possible", "whatever's best" — leaves it open:
      restate the question with your recommended default rather than building on the dodge.`

### Task 9: `skills/backend-craft/references/api-design.md` — spec-diff gate

**Files:** Modify: `skills/backend-craft/references/api-design.md` ("Evolving a published surface")

- [ ] Append bullet, verbatim:

```markdown
- **Gate the contract in CI**: diff every spec change with a breaking-change detector (oasdiff or
  equivalent) so a removal, rename, type change, or new-required-field cannot merge unlabeled —
  the taxonomy above, enforced mechanically.
```

### Task 10: `skills/frontend-craft/SKILL.md` — AI-aesthetic tells

**Files:** Modify: `skills/frontend-craft/SKILL.md` (Self-critique paragraph)

- [ ] Extend `…(cream page + serif display + terracotta accent; near-black + one acid accent;
      hairline-rule broadsheet)` with ` — and stock component tells: uniform rounded-2xl,
      purple-to-indigo gradients, a shadow on every surface`

### Task 11: `skills/ci-actions/SKILL.md` — cooldown clause

**Files:** Modify: `skills/ci-actions/SKILL.md` (rule 1)

- [ ] After "Re-pin deliberately (Dependabot can propose SHA bumps), and read the diff when you
      do." append: `Give re-pins a cooldown — adopt a release only after it has been public a few
      days; compromise campaigns count on fast adoption before detection catches the malicious
      version.`

### Task 12: `skills/prompt-craft/references/claude-code-frontmatter.md` — verified platform facts

**Files:** Modify: `skills/prompt-craft/references/claude-code-frontmatter.md`

- [ ] WebFetch the live docs (code.claude.com/docs/en/skills, /hooks-reference or /hooks,
      /cli-reference, /plugins-reference) and check each candidate fact: `/doctor`; a built-in
      `/verify` skill; `${CLAUDE_PLUGIN_DATA}`; `CLAUDE_ENV_FILE`; skill-scoped `hooks`; deferred
      tool loading.
- [ ] Add ONLY doc-confirmed facts, each with the file's stamp convention (doc-checked date +
      where). Anything unconfirmed is left out and named in the PR body under "Deliberately not
      done".

### Task 13: Provenance + notes

**Files:** Modify: `THIRD_PARTY_NOTICES.md` · Create:
`docs/archive/2026-07/external-donor-import-notes.md`

- [ ] One notices entry per grafted donor: vercel-labs/agent-skills (MIT, frontmatter-declared),
      stareezy-1/frontend-architecture-skill (MIT), addyosmani/agent-skills (MIT),
      alirezarezvani/claude-skills (MIT), alleneubank/claude-code (Apache-2.0),
      Neeeophytee/finding-unknowns-skills (MIT + attribution), trailofbits/skills (CC BY-SA 4.0,
      concepts only). Blog-derived items cite URLs in commit messages only.
- [ ] Import-notes doc in the PORT-001 shape: per-donor lens summary, what grafted where, what was
      rejected and why, contribute-back candidates.

### Task 14: Gates and close

- [ ] `python scripts/validate_fleet.py` → exit 0
- [ ] `python -m unittest discover -s tests` → all pass
- [ ] `claude plugin validate . --strict` → pass
- [ ] AFTER eval run (same pinned conditions, `…/after` output dir); diff vs before: no existing
      positive regresses, negatives stay 0%, report the seeded-positive delta.
- [ ] Commits with provenance trailers; push; PR per `.github/pull_request_template.md` with the
      conditional-gates table filled (description edit → before/after rates; no hook/guard change;
      no validator change).
