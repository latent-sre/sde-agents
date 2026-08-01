# LEARN-001 Learning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the fleet's outer learning loop — discovery routing, retro protocol, doc self-healing duties, and its measurement — per the paired spec, without touching any live system.

**Architecture:** Approach A′ — `self-improve-loop` stays the single routing entry; depth lands in two on-demand references. Body-only grafts carry the doc-gap duty to `runbook`, `homelab-platform`, `researcher`. One description edit is the only routing-surface change, measured by a new 2-member eval cluster captured before and after under identical sonnet-pinned conditions.

**Tech Stack:** Markdown definitions; stdlib-only Python gates (`validate_fleet.py`, `generate_platform_adapters.py`, unittest); `scripts/eval_routing.py` for routing measurement.

## Global Constraints

- Spec: [`../specs/2026-08-01-learn-001-learning-loop-design.md`](../specs/2026-08-01-learn-001-learning-loop-design.md) governs scope; nothing outside it.
- Standard library only; no new dependencies.
- Generated adapters are never hand-edited; regenerate after any canonical edit.
- Eval runs pin `--model sonnet --timeout 420 --runs 3`, no `--clean-room`, both sides identical (operator rule: never Fable-tier).
- Evidence-label triad, where used, copies the canonical stems verbatim from an existing definition.
- Branch `agent/learn-001-learning-loop`; commit per task; no push until all gates are green.

---

### Task 1: Round documents

**Files:**
- Create: `docs/superpowers/specs/2026-08-01-learn-001-learning-loop-design.md` (done)
- Create: `docs/superpowers/plans/2026-08-01-learn-001-learning-loop.md` (this file)
- Modify: `docs/fleet-roadmap.md` (add LEARN-001 under "Current work → Ready/Active")

**Interfaces:** Produces the roadmap ID every later commit message references.

- [ ] **Step 1: Add the roadmap item** — insert after the SAFE-003 entry:

```markdown
#### LEARN-001 — land the fleet learning loop

**Status:** `active`

**Outcome:** Any discovery made mid-task has one documented routing destination with a threshold
and a disposition rule; retros exist above the micro-retro (session, round, meta, model/CLI
upgrade) with an encode-one-file-many cap; runbooks and operating docs found wrong get fixed or
filed at the point of use; auto-memory has a consolidation procedure honoring its index budget.

**Source:** [`LEARN-001 spec`](superpowers/specs/2026-08-01-learn-001-learning-loop-design.md),
grounded in the 2026-08-01 four-lane research report (artifact `82a338a5…`); operator fork
rulings recorded in the spec.

**Prerequisites:** None. No validator rule changes, so no GRAPH-002 sequencing conflict.

**Acceptance:** The spec's acceptance-evidence list: gates green, adapters regenerated, inventory
refreshed, before/after `retro-boundary` captures under identical recorded sonnet conditions with
zero negative fires and no positive regression beyond variance.

**Next action:** Execute the paired plan; retire this item to an outcome record whose lessons
section works the new routing table.
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers docs/fleet-roadmap.md
git commit -m "docs(LEARN-001): open the learning-loop round — spec, plan, roadmap item"
```

### Task 2: Eval cluster + BEFORE capture

**Files:**
- Create: `evals/routing/retro-boundary.json`
- Create (by runner): `evals/baselines/2026-08-01-learn-001/before/retro-boundary/benchmark.json`

**Interfaces:** Produces the before-side `benchmark.json` Task 5 diffs against. Case IDs are stable; Task 5 must not rename them.

- [ ] **Step 1: Write the cluster file** — exactly:

```json
{
  "cluster": "retro-boundary",
  "members": ["self-improve-loop", "postmortem"],
  "notes": "Non-incident retros and lesson routing belong to self-improve-loop; the retro on a resolved incident belongs to postmortem. Negatives are vocabulary collisions (retro styling, sprint ceremonies, forensic postmortems) and a live outage, which must reach neither member.",
  "cases": [
    { "id": "pos-task-retro", "prompt": "That deploy script took three attempts before its tests went green. Before we close out, do a retro on this task and capture what kept failing.", "polarity": "positive", "expect_fires": ["self-improve-loop"], "tags": ["retro", "task"] },
    { "id": "pos-lessons-learned", "prompt": "The migration is finished. Capture the lessons learned from the repeated review findings — and where should each one actually go so it sticks?", "polarity": "positive", "expect_fires": ["self-improve-loop"], "tags": ["retro", "routing"] },
    { "id": "pos-micro-retro", "prompt": "My fix finally passed after two failed attempts — run the micro-retro and move one lesson left into a deterministic check.", "polarity": "positive", "expect_fires": ["self-improve-loop"], "tags": ["retro", "existing-remit"] },
    { "id": "pos-iterate-draft", "prompt": "Here are the reviewer's findings on my draft doc. Iterate on it against the checklist until it passes.", "polarity": "positive", "expect_fires": ["self-improve-loop"], "tags": ["existing-remit", "evaluator-optimizer"] },
    { "id": "pos-outage-retro", "prompt": "Last night's NAS outage is resolved and everything is healthy again. Do a retro on the outage and write it up properly.", "polarity": "positive", "expect_fires": ["postmortem"], "tags": ["incident", "boundary"] },
    { "id": "neg-sprint-retro", "prompt": "Facilitate a sprint retrospective for my team's Tuesday ceremony — agenda, icebreaker, and a template for action items.", "polarity": "negative", "tags": ["near-miss", "ceremony"] },
    { "id": "neg-retro-style", "prompt": "Restyle this landing page with a retro 80s synthwave look — neon grid, chrome type, the works.", "polarity": "negative", "tags": ["near-miss", "vocabulary"] },
    { "id": "neg-forensic-postmortem", "prompt": "For a story I'm writing: what does a postmortem examination involve in forensic pathology, step by step?", "polarity": "negative", "tags": ["near-miss", "vocabulary"] },
    { "id": "neg-live-outage", "prompt": "Grafana is down right now — every dashboard is blank and the household is asking. Help.", "polarity": "negative", "tags": ["near-miss", "live-incident"] }
  ]
}
```

- [ ] **Step 2: Confirm runner + interpreter** — `python3 --version || python --version`; `python3 scripts/eval_routing.py --help` shows `--model/--timeout/--runs/--output-dir`.
- [ ] **Step 3: Capture BEFORE (pre-edit descriptions)** —

```bash
python3 scripts/eval_routing.py evals/routing/retro-boundary.json --runs 3 --model sonnet --timeout 420 \
  --output-dir evals/baselines/2026-08-01-learn-001/before
```

Expected: negatives 0% fire; `pos-outage-retro` fires postmortem; the two new-remit positives (`pos-task-retro`, `pos-lessons-learned`) may under-fire before the edit — that is the point of the diff. `INCONCLUSIVE` → re-run those cases.
- [ ] **Step 4: Verify `benchmark.json` exists and its `conditions` records sonnet/420/threshold/cli/clean_room=false.**
- [ ] **Step 5: Commit**

```bash
git add evals/routing/retro-boundary.json evals/baselines/2026-08-01-learn-001/before
git commit -m "eval(LEARN-001): seed retro-boundary cluster and capture the pre-edit baseline (sonnet, 420s, 3 runs)"
```

### Task 3: self-improve-loop — description, retro section, two references

**Files:**
- Modify: `skills/self-improve-loop/SKILL.md:3` (description), body after the Micro-retro section
- Create: `skills/self-improve-loop/references/discovery-routing.md`
- Create: `skills/self-improve-loop/references/retro-protocol.md`

**Interfaces:** Produces reference paths consumed verbatim by Task 4's AGENTS.md line: `skills/self-improve-loop/references/discovery-routing.md`.

- [ ] **Step 1: Replace the description** (frontmatter line 3) with exactly:

```text
Use when output quality is measurable and iteration demonstrably improves it — hardening a draft against review findings, grinding code up against a failing test whose cause is already diagnosed, or improving the fleet's own agent/skill definitions — and for retros outside incidents: the micro-retro after any task that needed a fix cycle, a session or round retro ("do a retro on this task", "capture the lessons learned", "what did we miss"), and routing a new discovery to its durable home (instructions file, skill, runbook, memory, or a deterministic check). Covers generate→evaluate→refine, act→verify ordering, guardrails for unattended outer loops, discovery routing, and moving recurring lessons into deterministic checks. For the retro on a resolved lab incident or outage, use sde-agents:postmortem. For any undiagnosed bug, test failure, or unexpected behavior, use sde-agents:root-cause first — this loop iterates on known gaps; it does not diagnose.
```

- [ ] **Step 2: Insert the outer-loop section** between "## Micro-retro — how the loop learns" and "## Run the loop well" (payload in the spec's scope item 1; final text authored in place, register-matched).
- [ ] **Step 3: Write `references/discovery-routing.md`** — the routing table, disposition rule, write gates, provenance note (adapted-concepts from sre-agents `operational-learning`).
- [ ] **Step 4: Write `references/retro-protocol.md`** — session/round/meta/upgrade retros + memory consolidation.
- [ ] **Step 5: Validator** — `python3 scripts/validate_fleet.py` green (description ≤1024, references linked, no orphans).
- [ ] **Step 6: Commit**

```bash
git add skills/self-improve-loop
git commit -m "feat(LEARN-001): self-improve-loop gains the outer loop — retro triggers, discovery routing, retro protocol

Routing thresholds adapted from Anthropic's build-over-time triggers and the
sre-agents operational-learning disposition map (concepts, not text)."
```

### Task 4: Body grafts — runbook, homelab-platform, researcher, AGENTS.md

**Files:**
- Modify: `skills/runbook/SKILL.md` (Rules list, new final rule)
- Modify: `agents/homelab-platform.md` (Standards section, new bullet before "Expose the minimum")
- Modify: `agents/researcher.md` (Method §3, one added sentence)
- Modify: `AGENTS.md` (Change playbooks, one new entry)

**Interfaces:** Consumes Task 3's reference path in the AGENTS.md line.

- [ ] **Step 1: runbook rule** — append to the Rules list:

```markdown
- Found wrong in use: a step this runbook told you that reality contradicted gets fixed in the
  same change when the fix is small and in scope — update "Last verified" only if you re-ran the
  steps — otherwise file the gap where the repo tracks work and say so in your handoff. Silently
  working around a wrong runbook guarantees the next reader hits it too.
```

- [ ] **Step 2: homelab-platform bullet** — insert before the "**Expose the minimum.**" bullet:

```markdown
- **Docs are part of the change.** An operating doc you relied on and found wrong or missing — a runbook step that failed, a stale path, a dead recovery note — gets fixed in the same change when small and in scope (doc edits are Tier 1; a runbook's "Last verified" moves only on run evidence), else the gap is named in your review packet. Never silently work around a wrong doc.
```

- [ ] **Step 3: researcher sentence** — in Method §3, after "use it to find the primary source, then cite that.":

```text
When a claim hinges on a literal string, an exact quote, a count, or a version, read the raw artifact deterministically (GitHits code/docs readers, raw file endpoints) rather than trusting a summarized fetch — summarizing readers have fabricated details and missed literal strings that a direct read finds.
```

- [ ] **Step 4: AGENTS.md playbook entry** — after the "**Changing validator behavior**" entry:

```markdown
**Closing a task that surfaced a discovery** — a platform fact, a recurring failure, a doc found
wrong, a routing miss — route it per `skills/self-improve-loop/references/discovery-routing.md`
before closing out: routed, filed as a gap, or dropped with a stated reason. Silence is not a
disposition.
```

- [ ] **Step 5: Validator green.**
- [ ] **Step 6: Commit**

```bash
git add skills/runbook/SKILL.md agents/homelab-platform.md agents/researcher.md AGENTS.md
git commit -m "feat(LEARN-001): doc-gap duty at point of use; researcher deterministic-reads rule

The researcher line encodes the deterministic-reads lesson whose recurrence
fingerprint matched on 2026-08-01 (three fetch-layer fabrications in one round)."
```

### Task 5: AFTER capture + diff

**Files:**
- Create (by runner): `evals/baselines/2026-08-01-learn-001/after/retro-boundary/benchmark.json`

- [ ] **Step 1: Capture AFTER** — same command as Task 2 Step 3 with `--output-dir …/after`.
- [ ] **Step 2: Diff** — compare per-case rates before/after. Gate: negatives 0% both sides; `pos-micro-retro`/`pos-iterate-draft`/`pos-outage-retro` not regressed beyond variance; new-remit positives improved or explained.
- [ ] **Step 3: Commit**

```bash
git add evals/baselines/2026-08-01-learn-001/after
git commit -m "eval(LEARN-001): post-edit retro-boundary capture — conditions identical to the before side"
```

### Task 6: Gates and generated surfaces

- [ ] **Step 1:** `python3 scripts/generate_platform_adapters.py --write`
- [ ] **Step 2:** `python3 scripts/validate_fleet.py --write-inventory`
- [ ] **Step 3:** `python3 scripts/generate_platform_adapters.py --check && python3 scripts/validate_fleet.py && python3 -m unittest discover -s tests` — all green.
- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(LEARN-001): regenerate host adapters and README inventory"
```

### Task 7: Push + PR

- [ ] **Step 1:** `git push -u origin agent/learn-001-learning-loop`
- [ ] **Step 2:** `gh pr create` against `main` per `.github/pull_request_template.md` — claim-plus-consequence lines; conditional-gates rows filled: description edit → before/after eval diff (sonnet-pinned), canonical edits → regenerated adapters; "Deliberately not done" from the spec.

### Task 8: Close-out (not a commit)

- [ ] Present the drafted global-CLAUDE.md one-liner for separate approval (spec fork 3).
- [ ] Update operator memory (`learn-001-round-…`) with PR number and eval verdicts.
- [ ] Wrap-up packet: changed files, assumptions, verified/unverified, likely-wrong spots.
