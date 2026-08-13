# GRAPH-002 outcome — operator capability graph and workflow-design validator

**Status: closed 2026-08-13** — implementation merged (PR #125, merge `10246d8`), retired to this
record (PR #127, merge `92f0611`), and accepted by the operator the same day. This record retires
the round's spec and plan, which were deleted at closeout per the convention that their absence
means no round is running. Both are preserved in Git history at `60ba49e` as
`docs/superpowers/specs/graph-002-descriptive-capability-graph.md` and
`docs/superpowers/plans/graph-002-plan.md`; read them with `git show`. Governed by the accepted
[AI graph engineering decision](../../decisions/2026-07-31-ai-graph-engineering.md) as amended
2026-08-12.

## What landed

Two on-demand operator CLIs on a shared parser, none of it wired into T0, CI, or a PR gate:

- **`scripts/fleet_records.py`** — the fleet's one parser for frontmatter, `tools:` values, and
  namespaced references, plus typed records. It records and never judges; every policy question
  stays in `validate_fleet.py`, so no new gate shipped. It parses an inspected tree as data and
  never imports or executes it, which is what makes a foreign or frozen-baseline checkout safe.
- **`scripts/capability_graph.py`** — a deterministic topology report that keeps authored edges,
  per-host authority projections, and the routing overlay separate. No unioned fleet authority is
  emitted, because no such thing exists at runtime.
- **`scripts/workflow_contract.py`** — schema-v1 design consistency for one explicit document,
  reporting `design-consistent` and never `runtime-enforced`.
- **`scripts/validate_fleet.py`** — 165 lines lighter, consuming the shared collector rather than
  its own copy of the parser.

Suite: 666 → 819 tests, 30 → 33 modules.

## The measure, and why it is trustworthy

The decision published four series but never the identity rule that produced them. Rather than
assume one, the plausible variants were swept at the decision's own snapshot `c02d8e12` and only
the variant reproducing every published number exactly was kept — 140 cross-reference edges, 85
tool-authority edges, 4 skill preloads, and the routing overlay at 8 clusters / 38 member-to-cluster
edges / 117 cases (64 positive, 53 negative) / 29 members covered. Measuring the candidate under a
guessed identity would have made every delta unattributable between a changed tree and a changed
measure.

**Stable identity:** distinct `(source_member, target_member)` pairs over core definition files
only, self-loops included, with surface and slash form as metadata. No other swept variant returns
140.

## The five frozen operator questions, answered from `main` at `10246d8`

| Question | Answer |
|---|---|
| 1 — isolated / concentrated | Unreferenced: `code-craft`, `onboarding-map`; `code-craft` is reached only by preload. Top hubs: `homelab-platform` 18, `sde-fullstack` 12, `principal-engineer` 10, `code-reviewer` 9 |
| 2 — changed vs the dated measure | Edges 140 → 155 (**18 added, 3 removed**); tool grants 85 → 85 with no per-agent change; preloads 4 → 7. The relationship-level list is below — the frozen question asks *which* relationships changed, and an aggregate does not answer it |
| 3 — host request / withhold | Claude guards 3 roles; Copilot withholds `execute` from those same 3 by guard; Codex requests `workspace-write` for 7 of 11; `lab-audit` and `security-audit` declare skill-level denies that portable hosts strip |
| 4 — where authority is unknown | Every Codex role `unknown_or_inherited`; `prompt-engineer` the sole dynamic-delegation principal switch |
| 5 — behavioral evidence | **Partly answered, and the limit matters.** 30 members carry positive case assertions and 31 carry negative ones — but assertions are *per member*, not per relationship, so they do not establish which **relationships** have behavioral evidence. What the overlay does establish is the co-membership half: 54 reference relationships have endpoints that share **no** routing cluster at all |

**Question 2 in full — which relationships changed.** Reproduced under the stable identity against
the decision's own snapshot `c02d8e12`, not against a second post-implementation head:

- **Added (18) = 8 + 7 + 3.** Eight agents gained a `/sde-agents:self-improve-loop` routing edge
  (`application-security-auditor`, `code-reviewer`, `distinguished-architect`, `homelab-platform`,
  `multi-agent-architect`, `principal-engineer`, `repository-investigator`, `researcher`); the new
  `onboarding-map` skill contributed seven outbound edges (`eng-ladder`, `homelab-platform`,
  `host-onboard`, `lab-audit`, `sde-fullstack`, `security-audit`, `service-onboard`); and three
  others landed — `code-reviewer → homelab-platform`, `sde-fullstack → homelab-platform`, and
  `self-improve-loop → runbook`.
- **Removed (3).** `self-improve-loop` dropped its references to `eng-ladder`, `sde-fullstack`, and
  `sre-tool`. This was the one substantive question the artifact raised about the fleet rather than
  about itself, and it is **disposed here rather than archived unowned**: the narrowing was
  intentional. All three disappeared in `d027755` (the LEARN-001 round), which rewrote the skill
  around a discovery-routing table; the removed lines were a worked example (`sde-fullstack`
  generates → `code-reviewer` evaluates, with the `sre-tool` review phase as checkpoint) and an
  analogy to `eng-ladder` growth feedback, not routing declarations. `code-reviewer` survived the
  rewrite and is still referenced. No routing capability was lost, so no roadmap item or ledger
  candidate is owed — the concern is dropped with this as its stated reason.

  Worth keeping as a reading note: the graph reports a **reference** disappearing, which is not the
  same as a **capability** disappearing. Prose examples and routing paths are the same edge kind to
  this tool, and only the source text distinguishes them.
- **Members:** 30 → 31, the addition being `onboarding-map`.

Integrity fields all clean on the real tree: no unreadable definitions, no unadopted tool
identifiers, no unresolved preload targets, no duplicate cluster identities.

**Standalone cost** (median of five, one quiet machine, `main` @ `10246d8`): capability graph
**122 ms**, workflow validator **81 ms**. Neither enters the T0 path, so no `validate_fleet.py`
before/after timing is claimed and none is owed.

## Operator acceptance

**Accepted by the operator on 2026-08-13.** Payload 4 is satisfied and GRAPH-002 is closed.

- **Real-tree capability JSON and Mermaid reviewed:** yes. Emitted from `main`, first at `10246d8`
  and re-emitted at `24f8711` after PRs #127 and #128 landed. The **aggregate topology series are
  unchanged** across both heads — 155 edges, 85 grants, 7 preloads, the same unreferenced and
  preload-only members, 54 relationship gaps, 10 clusters — so the accepted findings do not depend
  on a single transient head. The two documents are **not** byte-identical (140,991 vs 140,995
  bytes). PR #128 edited `agents/homelab-platform.md`, and because `reference_edges` carries
  per-occurrence line numbers, **16 edge records changed** across six distinct shifts (89→124,
  90→125, 97→132, 157→192, 163→198, 165→200), all within that one file. The **edge identity set is
  unchanged** — same pairs, same count. That contrast is the thing to carry into any
  baseline-versus-candidate diff: a single edit to one referring file rewrites occurrence records
  in bulk while the topology it describes stays put, so diffing whole artifacts reports churn that
  diffing the identity does not. It is why the two are separate series, and why a reviewer comparing
  snapshots should compare the identity first and treat occurrence movement as location metadata.
- **Workflow design supplied to the CLI:** yes — one non-authoritative six-node design
  (`review-then-apply`: deterministic entry, agent, repo-script verifier, human gate, effect,
  terminal). Result `design-consistent (NOT runtime-enforced)`, `design_digest`
  `bfdcaf3501395783bf7b47cb9a68b219181e66fb66527b83e45f8db31c12624d`. The file was **not** promoted
  into a committed contract, and no digest was resolved: that remains GRAPH-004's.
- **Did each output answer its stated operator question:** yes, for both outputs. The capability
  graph answered all five frozen questions; the table above is those answers. One attribution
  matters: questions 1 and 3–5 are emitted wholly by the tool, while question 2's `140 → 155` pairs
  an emitted candidate value with the historical 140 recorded in the decision. `capability_graph.py`
  takes a single `--root` and has no baseline or comparison mode, so a rerun reproduces the
  candidate side only — the comparison is this record's, not the tool's. The workflow validator
  answered its own question, which was whether a prospective design is internally consistent before
  any runtime exists: it returned `design-consistent (NOT runtime-enforced)` with a stable digest,
  and the verdict's wording is itself the answer — it establishes a document property and declines
  to claim an execution one.
- **Limitations recorded:** the "Deliberately not done" section below is the accepted limitation
  set. Two are worth carrying forward as live reading caveats rather than defects. First, the 54
  `routing_cluster_relationship_gaps` are relationships whose endpoints appear in **no shared
  routing cluster** — `_report` selects an edge precisely when its endpoints are absent from every
  cluster pairing. An earlier draft of this record described them as resting "on co-membership
  only", which is the inverse of what the section computes; they have *less* evidence than a
  co-listed pair, not more. Relationship-level behavioral evidence is not derived at all, because
  routing cases assert that a member fires, not that a pair is exercised. Second, every Codex
  authority projection is `unknown_or_inherited` — for Codex the report states what the profile
  *requests*, not what the host granted. Two host controls **are** evidenced and must not be read
  as unknown alongside it: Claude's guard coverage, and Copilot/VS Code's omission of `execute` from
  guarded roles, which the report derives through the same generator function that renders those
  adapters rather than by reparsing them.
- **Rejected designs:** none. No design was refused during acceptance; the validator's refusal
  paths are covered by tests rather than by a rejected operator submission.
- **T1 on the exact accepted bytes:** T1 has three parts and they are not all establishable the
  same way. The **suite and the plugin contract** are guaranteed structurally rather than by citing
  a run, because a cited SHA goes stale the moment a review correction adds bytes — which happened
  here twice. `validate (ubuntu-latest, python3)`, `claude-plugin-contract`, and `ledger-drift` are
  **required status checks on `main`**, so no head reaches `main` without them green *on that
  head*. That is narrower than it first reads: protection is **not `strict`**, so the checks run on
  this branch's head and not on a merge preview. If `main` advances after they pass, the merge
  combines a tested branch with an untested base, and no run has seen the resulting tree. The claim
  is therefore about the branch bytes, not the merged bytes. The **doctor check is local-only and CI can never substitute for it**, because the drift it
  finds lives in the host installation rather than in the checkout every other tier reads: run
  during acceptance, `scripts/fleet_doctor.py` reported **pass=14, warn=0, fail=0, exit 0** —
  repository worktree, generated adapters, platform contracts, and canonical line endings clean, all
  four host CLIs present, `sde-agents` **present in** both the Claude and Codex plugin inventories,
  and Codex's **standalone agents** matching the generated roles. The two plugin checks test
  presence in `plugin list`, not plugin-content parity; the only generated-role comparison in that
  count is the standalone Codex one.
  Two further limits: CI is Linux while the artifact figures above came from a Windows run, and the
  doctor result binds the host and the clean worktree it ran on, not the merged bytes. The Linux/Windows split is not cosmetic on this round — the only defect CI ever
  caught here was a test that passed vacuously on Windows and failed on POSIX.

## Review history, and what it cost

Five review rounds ran against this branch: one adversarial Codex pass, one `deep-review` workflow
(two lanes), and three GitHub PR passes. Roughly thirty findings; the ones that mattered:

- A test pinning live edge counts (155/7/85) had turned an explicitly advisory report into a CI
  blocker — one routine namespaced cross-reference failed the suite with `156 != 155`, while the
  tool's own docstring said the design is never a gate.
- Inherited-all tool authority rendered as *least* privilege: an agent with no `tools:` inherits
  every tool and was displayed with an empty grant.
- An unreadable guard roster reported as *not guarded*, twice, in different projections —
  `bool(None)` is `False`.
- Absolute occurrence paths defeated the baseline-versus-candidate comparison the artifact exists
  for, and the determinism test that missed it asserted the weaker same-root property.
- Untyped data edges and ordinary predicates (`status == 'ok'`) passing schema v1.

**Two rulings settled here rather than re-litigated.** Schema v1's narrowing to acyclic graphs and
`all`-only joins is authoritatively amended in the decision record, so no accepted behavior was
silently omitted. Approval coverage already traverses an unresolved `subgraph` as opaque but
traversable; that is now pinned by a regression test rather than incidental.

## Lessons this round paid for

1. **A static-review class can regenerate indefinitely.** Three rounds of field-by-field
   `isinstance` patches each cited the previous round's fix and named the next unchecked field. One
   shape table plus a test driving all 26 fields ended it. When findings cite your last fix, the
   diagnosis is the class, not the field.
2. **A prose invariant is not enforcement.** Three times in one round a correct sentence sat beside
   an artifact that violated it — `Member.tools`' docstring versus the graph that read it, the
   diffability claim versus absolute paths, and "never a CI gate" versus a pinned-count test. The
   sentence is the test's specification; if no test asserts it, it is decoration.
3. **One ambiguous word in a plan produced a wrong implementation defended for three rounds.**
   "Union the reference and preload series" was meant as *report both* and implemented as *merge
   into one metric*, which made `unreferenced_components` mean something its own name does not say.
   The plan sentence now says "side by side"; the fix that sticks is the one that removes the
   misreading, not the one that corrects its output.
4. **Local-only verification has a platform ceiling, and it hides vacuous tests.** The first CI run
   this branch ever had failed on Ubuntu inside a test written two commits earlier: `f"./{target}"`
   prefixes an absolute POSIX path with `./` and yields a relative path to a nonexistent directory,
   so the assertion was vacuous on Windows and wrong on Linux. Five static rounds could not have
   found it — a reviewer reads the intent, not the filesystem semantics.

## Deliberately not done

- `design_digest` is not a resolved `contract_digest`; GRAPH-004 owns committed contracts, digest
  resolution, and execution.
- No threshold on any advisory section, including the 54 co-membership-only relationship gaps.
- Tool nodes stay out of the Mermaid view — 29 tool nodes in a 31-member diagram costs the
  readability the diagram exists for; the docstring claims "member topology" rather than
  completeness it does not have.
- `_find_cycle` is iterative and handles a 1200-node chain, but no explicit node-count bound is
  declared in schema v1.
- The symlink-containment test skips where symlink creation is not permitted; the containment logic
  is covered by a relative-path escape test that does run.
