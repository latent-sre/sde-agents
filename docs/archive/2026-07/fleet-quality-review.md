# Fleet quality and deep review — July 2026

> **Status: historical archive.** This document combines the initial fleet-quality review and its
> deep follow-up. It preserves their evidence, decisions, and lessons; it is not a live work list.
> [`../../fleet-roadmap.md`](../../fleet-roadmap.md) is the only authority for current work.

## What this archive combines

Three dated views are retained:

1. **Initial quality review, 2026-07-16.** Three passes over 7 agents and 9 skills:
   structural/spec compliance, an independent content audit, and adversarial verification against
   the files and then-current platform documentation.
2. **Deep review, 2026-07-24.** Four independent read-only reviewers covered infrastructure,
   agents, skills, and documentation/eval coherence. A synthesizer rechecked every load-bearing
   claim. The review started at `1bc536e`; its first two fixes landed at `31ff506`.
3. **Deep-review Round 2, 2026-07-24.** Five direct passes red-teamed the guard, exercised the
   runtime, checked technical examples, inspected portfolio/platform gaps, and landed verified
   changes.

The 2026-07-28 current-tree reconciliation at `ab896b2` checked every item that either source still
called open. Its dispositions are included below so a dated recommendation cannot silently become
new work.

## Benchmarks and evidence model

The initial review compared the fleet with the then-current Anthropic skill-authoring guidance,
Agent Skills open specification v1.1, Claude Code skill/subagent documentation, and the Agentic AI
Knowledge Base. The deep review additionally held the repository to its own `AGENTS.md` rules and
used direct reproduction where a claim involved executable behavior.

Evidence strength differed by claim:

- schema, routing, path, and content claims were checked against repository files;
- guard bypasses were reproduced against `is_allowed()` and, for the highest-risk case, by
  creating a marker through the supposedly read-only command;
- runtime claims used the real plugin probe and headless routing sessions;
- platform facts were sourced from live documentation at review time and are retained as dated
  evidence, not current platform guarantees.

## Executive conclusion

Both reviews found the fleet materially above their benchmark bar. The strongest characteristics
were enforced authority, explicit verification labels, progressive disclosure, and disciplined
routing boundaries. The reviews nevertheless found real security defects and a broad layer of
documentation and consistency debt.

The current-tree reconciliation found that every item once left open by these two reviews is now
landed, deliberately retained, rejected by measurement, or superseded. These reviews therefore
contribute no live task by themselves.

One later result matters when interpreting their praise: the deep review's statement that the
read-only guard was “airtight after S1” was a dated conclusion, not an enduring guarantee. The
2026-07-28 review subsequently reproduced a malformed-JSON fail-open behavior, now tracked as
`GOV-001` in the roadmap. Current evidence wins over this archive.

## Initial quality review

### Overall assessment at the time

The fleet was structurally clean: names and directories matched, descriptions stayed within the
platform limit, agent and skill bodies were compact, references used predicate-keyed loading,
side-effect skills disabled model invocation, and tool grants were scoped. The code reviewer's
read-only mandate was hook-enforced rather than merely promised.

The review found three systemic themes:

1. duplicated doctrine without a declared owner;
2. a stack-neutrality contradiction in `frontend-craft`;
3. prose-only authority where a structural control or an honest boundary was possible.

### P1 — fix first

| ID | Historical finding and requested correction | Reconciled disposition |
|---|---|---|
| 1 | `frontend-craft` presented TanStack Query, TanStack Router, React Testing Library, and a Mantine ban as universal even though the stack exception loaded only for greenfield work. Keep the core stack-neutral and make library bindings conditional. | Landed. The core says an existing repository wins, labels bindings as the default stack, and limits the Mantine rule to its relevant context. |
| 2 | `prompt-craft` said `allowed-tools` accepted only bare names, contradicting the then-current platform syntax. Correct the fact and remove the duplicate update surface. | Landed. The corrected fact lives in the canonical Claude Code frontmatter reference. |

### P2 — high-value improvements

| ID | Historical finding and requested correction | Reconciled disposition |
|---|---|---|
| 3 | `prompt-craft` and `prompt-engineer` carried divergent copies of Claude Code frontmatter guidance. Create one source of truth and point both consumers to it. | Landed. `skills/prompt-craft/references/claude-code-frontmatter.md` is canonical and the agent points to it. |
| 4 | Only `code-reviewer` explicitly treated fetched or repository content as data rather than instructions. Carry the rule across every applicable agent. | Landed. All applicable agents carry the canonical sentence or a declared role-specific adaptation. |
| 5 | `homelab-platform` routed service additions directly to an explicit-only skill that the router could not invoke. Route the task to the agent and have it work the checklist. | Landed. The agent owns the apply and loads the checklist by path. |
| 6 | `lab-audit` claimed to be read-only only in prose. Deny write tools and state honestly that Bash remains cooperative. | Landed. Write, Edit, and NotebookEdit are denied; the Bash boundary is explicit. |
| 7 | Eval coverage stopped at thin routing checks and did not measure output compliance. Seed overlap clusters and add deterministic behavioral contracts for high-risk promises. | Core machinery landed. Six routing clusters, a behavioral runner, packet linting, and deterministic contracts now exist. Any additional contracts are governed by the live roadmap, not this finding. |

### P3 — polish and debt

| ID | Historical finding and requested correction | Reconciled disposition |
|---|---|---|
| 8 | Craft references repeated headings and introduction text. Remove token-cost duplication. | Landed. The references use one heading and compact prose. |
| 9 | The Mantine prohibition appeared in five places with competing owners. Keep one conditional source and point the references to it. | Landed. `frontend-craft/SKILL.md` owns the rule. |
| 10 | Body cross-references mixed namespaced and bare component names. Adopt namespaced names for invocable references and bare names only for content already in context. | Closed. The convention is documented and no current broken route was found. |
| 11 | `sre-tool` kept dense multi-component orchestration in its always-loaded core. Move conditional detail behind progressive disclosure. | Landed in `skills/sre-tool/references/multi-component.md`. |
| 12 | Descriptions opened with trigger language but often lacked a capability-led clause. Add capability first and measure routing-sensitive edits. | Landed. Current descriptions lead with capability, then triggers and negative routing. |
| 13 | `multi-agent-architect` and `prompt-engineer` lacked the fleet's compressed worked example. | Landed. Both now include one. |
| 14 | The material-fork rule appeared in the builder and both craft skills. Reduce it without breaking standalone skill invocation. | Deliberately retained in compact form because each craft skill can be invoked without the builder in context. |
| 15 | Standalone craft skills required a “review packet” they did not define. Add a fallback packet shape. | Landed. Both skills provide a four-slot fallback. |
| 16 | Evergreen guidance embedded comparative or version-sensitive claims. Remove unnecessary age and fixed-tier language. | Landed. The cited time-sensitive wording is gone. |
| 17 | `prompt-engineer` described spawning as both unavailable to subagents and unrestricted. Branch on the Agent tool actually being unavailable. | Landed. |
| 18 | Design agents' documentation-only Write and inspection-only Bash constraints were prose-only and unacknowledged. Enforce what can be enforced and disclose the rest. | Landed. Principal and distinguished agents have guard-enforced Bash and acknowledge the cooperative Write boundary. |
| 19 | `homelab-platform` held the Skill tool without explaining its intended authority. Name the operating checklists and invocation model. | Landed. |
| 20 | `eng-ladder` references used repository-relative paths that did not resolve from an installed plugin. State repository and `${CLAUDE_PLUGIN_ROOT}` forms. | Landed across the rung references. |
| 21 | Optional platform fields such as `when_to_use`, `maxTurns`, and `memory` lacked an explicit yes/no decision. Record the trade-offs, especially authority expansion from memory. | Landed in the canonical frontmatter reference. |

## Deep review — Round 1

### Immediate fixes

#### S1 — executable surfaces in the read-only guard

The guard allowed flags that could run an external program inside a command presented as a read:

- `git grep --open-files-in-pager=CMD` and attached `-O<CMD>`;
- `rg --hostname-bin=CMD`;
- `rg -z` and `rg --search-zip`, which can invoke decompressors from `PATH`.

The `git grep -O` path was reproduced by creating a marker while the guard returned ALLOW. The fix
rejected both pager spellings and extended the ripgrep execution-flag set. Regression tests
covered every denied form and retained legitimate `git grep` and `rg --hidden` reads. This landed
at `31ff506`.

#### S2 — stale CI explanation

The OS-matrix comment still described a removed PowerShell mutation-verb denylist even though the
guard had moved to an allowlist. The comment was corrected to the actual cross-platform and
interpreter-probe reasons in the same commit.

### Documentation status drift

| ID | Historical finding | Final disposition |
|---|---|---|
| D1 | `evals/README.md` called a default one-cluster invocation the “full suite,” allowing four clusters to be skipped silently. | Landed; the documentation distinguishes one-cluster and all-cluster runs. |
| D2 | Routing-cluster counts, baseline membership, and the planned incident-skill name were stale. | Landed; counts/names were corrected and the homelab cluster was re-baselined. |
| D3 | The initial quality review presented landed findings as open. | Resolved by dated status stamps and now by this consolidated archive. |
| D4 | The modernization plan presented landed or renamed work as open and used stale fleet arithmetic/API-envelope language. | Resolved; the plan is explicitly a snapshot and the roadmap owns current work. |
| D5 | The repository map omitted the actual work ledger and donor reviews. | Landed; `AGENTS.md` and `docs/README.md` now state the documentation authority chain. |
| D6 | The second ECC review still called the RFC 9457 transition hazard open after it landed. | Resolved in the combined ECC archive and roadmap reconciliation. |

### Postmortem integration

| ID | Historical finding | Final disposition |
|---|---|---|
| P1 | No agent routed recovered incidents into `postmortem`. | Landed; `homelab-platform` names the after-recovery handoff. |
| P2 | `runbook` lacked a negative routing clause toward `postmortem`. | Rejected by measurement. The re-baseline showed no cross-firing, so the fleet correctly declined an unpinned description edit. |
| P3 | The postmortem asset included “Runbook updated,” but the skill's required-slot list omitted it. | Landed. |

### Ladder, guard, and validator hardening

| ID | Historical finding | Final disposition |
|---|---|---|
| L1 | Upper engineering rungs said to delegate but lacked the Agent tool and a report-to-caller fallback. | Landed. Principal, distinguished, and homelab roles return a named handoff rather than implementing outside their remit. |
| H1 | The hook duplicated the guarded-agent roster with no validator keeping it synchronized. | Landed as a validator rule with a mutation test proven to fail without it. |
| H2 | The validator branch rejecting scoped `Bash(...)` grants lacked a regression fixture. | Landed. |
| H3 | The documented skill-field allowlist, including `background`, was only partially exercised. | Landed. The test asserts the complete known-field set. |
| H4 | Plugin version `1.1.0` no longer distinguished more than 90 commits and a new skill. | Landed at the time as `1.2.0`; this is historical version evidence, not a current-version claim. |

### Correctness and consistency

| ID | Historical finding | Final disposition |
|---|---|---|
| C1 | `multi-agent-architect`'s negative routing sent wrapper-stack failures to prompt engineering despite owning that diagnosis in its body. | Landed. The description now names wrapper, memory-layer, tool-skip, and delivery-corruption triggers. |
| C2 | `principal-engineer` narrowed build-vs-buy differently from the declared ladder owner. | Landed by fixing the paraphrase toward the owner. |
| C3 | `sre-tool` counted two fix rounds against the root-cause three-strikes rule without naming the initial failed review as strike one. | Landed. The counting is now explicit. |
| C4 | The README claimed every fetched-content rule was an exact quote even though two skills intentionally adapted it. | Landed by accurately naming the adaptations. |
| C5 | `lab-audit` implied it always ran under `homelab-platform` even though it also routes directly. | Landed. |
| C6 | `multi-agent-architect` named only project-local agent paths, omitting plugin paths. | Landed. |
| C7 | Principal and distinguished agents' inspection-only Bash remained prose-only even though the guard could enforce it. | Landed after the guard/hook roster validator made expansion safe. |

## Deep review — Round 2 evidence

### Guard red-team

About 40 candidate bypasses were exercised against `is_allowed()`. Shell-structure attempts such
as pipes, heredoc forms, subshells, brace groups, chained commands, quoting tricks, and execution
prefixes were denied correctly. Three additional execution surfaces were found and closed:

- `ag --pager COMMAND`: `ag` was removed because its execution-capable flag surface could not be
  bounded and `rg` plus `grep` covered the read need;
- `git help -w`: the subcommand was removed because it can hand off to a configured browser;
- `gh ... --web`: browser-launching forms were gated.

One important boundary was documented rather than falsely “fixed”: repository-local Git config can
define `diff.<driver>.command`, and a matching `.gitattributes` entry can make bare `git diff`
execute that program. Blocking `--ext-diff` or `--textconv` would not close this path. The stated
mitigation is that a normal clone does not inherit remote local config; the exposure remains for a
repository that arrives with its `.git/config` already populated. `core.pager` was probed and did
not execute without a TTY.

### Runtime and routing evidence

The real plugin probe passed after the guard changes:

- the guarded reviewer's write-capable command was denied;
- the main loop's identical command was ignored by the guard;
- preloading, namespacing, and `${CLAUDE_PLUGIN_ROOT}` expansion remained intact.

A 54-session homelab routing run scored 15/18 positives, 8/8 negatives, and both `postmortem`
positive groups at 3/3. That result rejected P2's plausible but unsupported description edit.

### Technical-content evidence

The runbook restore example was executed conceptually against its actual failure modes and fixed:
it now drops and recreates the target schema, uses `ON_ERROR_STOP=1`, and addresses Compose
services rather than assuming a pinned container name. The accessibility guidance, Compose
commands, OpenAPI starter, and RFC 9457 text were rechecked and found consistent.

### Repository and validator evidence

The review also:

- ignored `.probe-tmp/` and `probe-transcript.jsonl`, which a failed probe can leave behind;
- advanced the plugin version for the then-current release state;
- added the guard/hook roster consistency rule;
- added the scoped-Bash regression case;
- expanded the known-skill-field test to the complete documented set.

## What the reviews said to preserve

1. **Enforced authority.** Tool grants, hook-backed allowlists, fail-closed behavior for guarded
   roles, and honest disclosure of cooperative boundaries were stronger than prose promises.
2. **Verification culture.** The `[verified]`, `[sourced]`, and `[unverified]` stems; evidence-gated
   completion; and explicit “not verified” reporting counter unsupported confidence.
3. **Progressive disclosure.** Predicate-keyed reference tables keep always-loaded guidance small
   while making task-specific rules available before edits.
4. **Routing discipline.** Capability-led descriptions, real trigger phrasings, reciprocal
   negative routing, and measured description changes reduce accidental overlap.
5. **Owned conventions.** Declared source-of-truth relationships and validator tripwires make
   silent drift visible.

## Final resolution

The 2026-07-28 reconciliation closed the three items that the deep review's final paragraph still
called open: wrapper-stack routing, upper-rung Bash enforcement, and frontend stack neutrality.
The measurement-rejected runbook description change remains correctly unimplemented. The local
Git diff-driver exposure remains an explicit boundary, not a hidden claim of enforcement.

No task should be reopened from this archive without fresh current-tree evidence and a roadmap
entry.
