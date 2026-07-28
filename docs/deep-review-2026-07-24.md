# Deep fleet review — July 2026

**Question:** the operator asked for a deep review of the whole repo for improvements.

**Method:** four independent read-only reviewers fanned out over disjoint surfaces —
infrastructure (`scripts/`, `hooks/`, `tests/`, CI, manifests), the seven agents, the eleven
skills (+ all references/assets), and doc/eval coherence — each holding the code to `AGENTS.md`'s
own bar. Every load-bearing claim below was re-verified against the files by the synthesizer; the
two security findings were reproduced at ground truth (marker file created) and against the guard's
own `is_allowed()`. Deduped against the standing `docs/agents-skills-quality-review.md` (whose own
stale-status problem is finding D3 below). 23 findings survived; the 2 highest are already fixed.

## Fixed in this review (commit `31ff506`)

**S1 — two arbitrary-code-execution holes in the read-only guard [HIGH, verified, FIXED].** The
guard that makes `sde-agents:code-reviewer` read-only allowlisted three flags that execute an
external program mid-"read" — the exact class it deliberately closed for `rg --pre`:

- `git grep --open-files-in-pager=CMD` and its attached short form `-O<CMD>` run CMD as a pager
  *even with no TTY* (proven: `git grep -O/tmp/x.sh` created the marker; the guard returned ALLOW).
- `rg --hostname-bin=CMD` (rg 14+) runs CMD; `rg -z/--search-zip` shells out to PATH decompressors.

Fixed by rejecting `-O`/`--open-files-in-pager` in `_git_allowed` (the short form slips past the
`split("=")` test the write-flags use) and extending `_RG_EXECUTION_FLAGS`. Regression tests
reproduce every form as denied, with legitimate `git grep`/`rg --hidden` positives proving no
over-block. This is the fleet's load-bearing control breaching its own stated promise; it did not
wait behind triage.

**S2 — CI matrix comment described removed code [MED, FIXED].** `.github/workflows/validate.yml:14`
justified the OS matrix by a "PowerShell mutation-verb denylist" that doesn't exist — the guard was
inverted to a pure allowlist. Reworded to the real reasons (allowlist-default holds cross-OS; the
interpreter-probe dodges the Windows Store `python3` stub). Bundled with S1.

---

## Remaining findings, by theme (ranked)

### Theme D — documentation status-drift (the largest cluster; one real footgun)

The machine-checked surfaces are accurate (inventory, cluster JSONs, backlog "landed" stamps all
verify). The drift is in unregenerated prose, and the doc set has an *implicit* status ledger —
backlog supersedes modernization-plan supersedes quality-review — that `AGENTS.md`'s map never
discloses, so three docs present landed work as open.

- **D1 — `evals/README.md:44` calls a one-cluster run the "full suite" [HIGH, verified].** The
  bare `eval_routing.py` invocations default to `prompt-tooling.json` only (`eval_routing.py:202`);
  a maintainer who "smoke-checked the suite" silently skips 4 of 5 clusters, including the
  self-declared highest-risk `homelab-ops`. Accurate when prompt-tooling was the only cluster; a
  real trap now. **Fix:** reword to "one cluster"; show a `for f in evals/routing/*.json` loop, or
  add an all-clusters default to the runner.
- **D2 — `evals/README.md:96` + `baselines/2026-07/` counts are stale [HIGH, verified].** README
  says `homelab-ops` is "a baseline of the current members" — false since `postmortem` joined
  today (baseline has 4 members/15 cases; cluster now 5/18). "Four clusters seeded" (`:85`)
  understates five. The baselines README omits `proportionality` (negatives are 23/23, not 17/17).
  Both still name the planned skill `incident`, renamed `lab-incident` in the backlog. **Fix:**
  correct counts; note the pending re-baseline; fix the skill names.
- **D3 — `docs/agents-skills-quality-review.md` shows ≥7 landed findings as open [MED, verified].**
  Its findings 2, 3, 4, 5, 6, 7, 19 have all landed (the frontmatter reference, the
  fetched-content lines in all 7 agents, `homelab-platform`'s routing fix, `lab-audit`'s
  `disallowed-tools`, five eval clusters) but the doc carries no stamps, unlike the backlog and ECC
  reviews. `AGENTS.md:26` frames `docs/` as where "pending work lives," so it reads as live
  defects. **Fix:** add landed/superseded stamps or a dated header pointing at the backlog as the
  live status owner.
- **D4 — `docs/skills-modernization-plan.md` shows landed items as open [MED, verified].** Item 2
  (eval seeding) is fully landed; item 3 (`incident`) was superseded by backlog 1.4/1.5 with its
  postmortem half shipped today as a standalone skill — a reader would rebuild a shipped skill.
  Line 15's fleet-size arithmetic is stale (11 skills, not 13). Stale "backend-craft's envelope"
  language at `:42,136` survives today's RFC 9457 rewrite that *bans* the envelope. **Fix:** stamp
  items 2/3/10; fix the size line and the `homelab.json`→`homelab-ops.json` path; s/envelope/error
  shape/.
- **D5 — `AGENTS.md:26` docs/ map omits the backlog and both ECC reviews [MED, verified].** The
  map names only the quality review and modernization plan — the two mostly-superseded docs — and
  omits `sre-agents-adaptation-backlog.md`, the file that actually owns what's open. **Fix:**
  reword to "reviews, plans, and the adaptation backlog; the backlog tracks what remains open."
- **D6 — the legacy ECC Batch 2 review (now consolidated in
  `docs/archive/2026-07/ecc-import-review.md`) stated the RFC 9457 hazard as still open [LOW,
  verified].** It landed today (`c88d380`) and the backlog stamps it resolved; batch-2 itself uses
  "landed" stamps elsewhere, so the unamended hazard reads as a live ban on error-shape edits.
  **Fix:** append "— resolved 2026-07-24, see backlog 1.3" at both spots.

### Theme P — postmortem integration seams (yesterday's new skill isn't wired in)

The skill landed internally consistent, but its *integration* with the rest of the fleet has three
gaps — the class most likely to make a new capability silently unused.

- **P1 — no agent file mentions `postmortem` [MED, verified].** `homelab-platform` owns the
  incident moment; its `Skill` grant enumeration (`:78`) names runbook/lab-audit/root-cause but not
  postmortem, and `grep -rn postmortem agents/` is empty. Postmortem routes live failures *to*
  homelab-platform, but nothing routes back to the write-up after recovery, so the feed-forward
  loop only starts if the user asks unprompted. **Fix:** add `sde-agents:postmortem` to
  `homelab-platform.md:78` with an after-recovery cue. Body-only.
- **P2 — `runbook`'s description has no negative routing toward postmortem [MED, verified].** The
  fleet's tightest new seam (both write docs; "what happened" vs "how to operate") is guarded only
  in runbook's *body*, and routing runs on descriptions. The eval can't catch a runbook co-fire
  (a positive passes if any expected member fires). **Fix:** add "Not for incident write-ups —
  `sde-agents:postmortem`" to runbook's description, then run the homelab-ops cluster before/after
  (this one touches a description — eval-gated per the AGENTS.md playbook).
- **P3 — the asset template has a slot the SKILL's slot list omits [LOW, verified].**
  `assets/postmortem.md` ends with "## Runbook updated" but the SKILL's enumerated required slots
  (`SKILL.md:27`) stop at Actions. **Fix:** add the bullet to the SKILL's list, or a one-line
  pointer that the template adds it per feed-it-forward.

### Theme L — the ladder's downward handoff is unmechanized

- **L1 — upper rungs are told to "delegate" but hold no `Agent` tool [MED, verified].**
  `distinguished-architect` and `principal-engineer` say "delegate implementation" / "hand it down
  the ladder" but neither holds `Agent`, and neither states the report-to-caller fallback that
  `sde-fullstack.md:137` spells out. `eng-ladder:23` says each file carries its rung's paraphrase
  "so a spawned agent can escalate without loading this skill" — so this is a hole in the
  convention's own terms, and the worst case is an upper rung implementing code itself, violating
  its own Write-scope mandate. Same shape at `homelab-platform.md:76`. **Fix:** add the explicit
  "hand the packet back to your caller naming the rung — never spawn or implement it yourself"
  clause to both rungs and homelab.

### Theme H — guard/validator hardening (latent; no live defect)

- **H1 — the hook hardcodes `code-reviewer` in 5 places with nothing keeping it in sync with
  `GUARDED_AGENT_NAMES` [MED, verified].** A second guarded agent would hit the hook's
  `*) exit 0` fast-path and be silently unguarded — the exact silent-disarm class this repo
  hardens against, and `AGENTS.md`'s "Adding an agent" playbook points only at the Python set. This
  is the blocker to ever acting on L-adjacent ideas like guarding the upper rungs (Theme L /
  agents-review finding 4). **Fix:** a validator rule that every `GUARDED_AGENT_NAMES` entry
  appears in the hook string, or derive the fast-path from the roster.
- **H2 — the validator's `Bash(...)`-scoped-grant branch is untested [LOW, verified].**
  `validate_fleet.py:347` (the "silently ignores permission-rule syntax" check) has no fixture,
  though it guards the same footgun as the guard's docstring; only the `Agent(...)` branch is
  tested. A refactor could disarm it silently. **Fix:** add a fixture agent with
  `tools: Read, Bash(git diff:*)`.
- **H3 — the `background` skill field (added today) is unexercised [LOW, verified].**
  `test_documented_skill_frontmatter_keys_are_accepted` covers 5 of ~17 fields; a typo in the
  allowlist entry would be caught by nothing. **Fix:** extend the accept-test to the full
  documented set.
- **H4 — `plugin.json` version stale at `1.1.0` [LOW, verified].** 92 commits since the bump,
  including a new skill and doctrine changes; a marketplace consumer can't tell versions apart on
  update, and nothing gates a bump. Inconsistent with the fleet's own anti-staleness doctrine.
  **Fix:** bump the version; consider a CI reminder when `agents/`/`skills/` change without a
  version delta.

### Theme C — small correctness / consistency nits

- **C1 — `multi-agent-architect`'s description misroutes its own new wrapper remit [MED,
  verified].** The body (`:41`) diagnoses single-agent wrapper stacks, but the description's
  negative (`:3`) sends "a single … agent" to `prompt-engineer`, whose remit doesn't cover
  transport corruption / memory poisoning. The batch-2 doc registered the *positive* trigger as
  deferred but not this active misroute. **Fix:** when the deferred description edit is taken up
  (eval-gated), narrow the negative to "a single prompt or skill"; note the misroute in the backlog
  meanwhile.
- **C2 — `principal-engineer.md:63` "build-vs-buy at platform scale" conflicts with the
  eng-ladder table [LOW, verified].** The table (the declared source of truth) and
  `distinguished-architect` both claim build-vs-buy unqualified; PE's qualifier keeps work the
  table routes up. **Fix:** drop "at platform scale" (fix the paraphrase, not the table).
- **C3 — `sre-tool`'s three-strikes citation counts a different unit than the owner [LOW,
  plausible].** `sre-tool:46` caps at "two rounds"; `root-cause` (the owner) says three failed
  attempts. Reconciles only if the initial failed build is strike one — which the text never says.
  **Fix:** state the counting explicitly and defer, or drop the borrowed "a third means the
  diagnosis is wrong" formula.
- **C4 — `README.md:51` "everything else quotes it exactly" is false [LOW, verified].**
  `root-cause:11` and `runbook:9` carry *adaptations* of the fetched-content sentence, not exact
  quotes. Per the fleet's own rule the ownership list must be accurate. **Fix:** name the skill
  adaptations or scope "everything else" to agents.
- **C5 — `lab-audit.md:12` "This runs under homelab-platform" is a misleading premise [LOW,
  verified].** The skill is designed to fire directly (its description and eval cases expect it).
  The security conclusion still holds; the premise doesn't. **Fix:** "Whether invoked directly or
  under homelab-platform, the reviewer's Bash guard does not cover this…".
- **C6 — `multi-agent-architect.md:45` names only `.claude/agents/*.md` [LOW, verified].** For a
  plugin engagement (including this fleet) the path is `agents/*.md`; the same sentence mandates
  reading the frontmatter reference that says so. **Fix:** "`.claude/agents/*.md` (or a plugin's
  `agents/*.md`)".
- **C7 — upper rungs' "inspection-only Bash" is prose-only [LOW, verified].** `principal-engineer`
  and `distinguished-architect` justify non-enforcement with "no tool boundary distinguishes doc
  from code" — true for Write, but the guard *does* enforce read-only Bash and its allowlist
  already covers their stated needs. Gated on H1. **Fix:** either add them to `GUARDED_AGENT_NAMES`
  (after H1, +tests/probe), or narrow the rationale so the Bash half reads as a choice.

---

## What is excellent (keep, don't dilute)

The reviewers independently confirmed the fleet is well above its benchmark bar. Enforced authority
over promised (the hook-backed allowlist — now actually airtight after S1); the uniform
`[verified]/[sourced]/[unverified]` verification culture; progressive disclosure via predicate-keyed
reference tables; routing discipline with reciprocal namespaced negative routing; and the
owned-conventions machinery visibly working (today's contract-template fix toward its source,
same-day eval seeding). Every mechanical invariant — packets, stems, aliases, namespacing, guard
membership, link resolution, dir==name — holds across all 7 agents and 11 skills, and the validator
+ 103 tests + `--strict` pass clean.

## Recommended sequencing

1. **Done:** S1/S2 (security) — landed.
2. **Batch D (documentation truth):** D1–D6 are zero-risk prose-accuracy fixes in six files; land
   together. D1 is the one with real consequence (a maintainer skipping 4 eval clusters).
3. **Batch P (postmortem wiring):** P1/P3 are body-only; P2 touches a description → run the
   homelab-ops cluster before/after (also the moment to do the pending re-baseline from D2).
4. **H1 then C7/L1:** fix the hook-sync validator gap first, because it's the precondition for
   safely guarding more agents. Then L1 (ladder handoff) and the remaining C-nits as a cleanup
   pass.
5. **Eval-gated, defer with budget:** C1 and P2's description halves — measured, not eyeballed.

Source: four-reviewer fan-out, 2026-07-24, head `1bc536e` (pre-fix); S1/S2 landed at `31ff506`.

---

# Round 2 — five deep passes (same day, after the above)

**Method:** five passes done directly rather than delegated: (1) red-team the guard for further
exec holes, (2) empirical runtime verification, (3) technical accuracy of the content itself,
(4) portfolio/platform gaps, (5) adversarial verification and landing. Everything below is
probed, not reasoned — and everything in it is **landed**.

## Pass 1 — the guard, again (it had more)

A corpus of ~40 candidate bypasses run against `is_allowed()`. **The tokenizer is sound**: every
shell-structure injection — `|&`, herestrings, subshells, brace groups, `&&` chains, escaped and
quoted `#`, ANSI-C quoting, `env`/`command`/`exec`/`time` prefixes, empty segments — denied
correctly, and the `#`-comment handling matches bash's. Three more exec surfaces did not:

- **`ag --pager COMMAND`** — the same lever gated on `rg` and `less`. Removed the tool: its flag
  surface can't be enumerated (not installed on any probed machine) and `rg`+`grep` cover it.
- **`git help -w`** — hands off to a config-named browser via `git web--browse` (`-i` to an info
  reader). Removed the subcommand, which closes every spelling at once.
- **`gh … --web`** — launches `$BROWSER` instead of printing. Gated.

**The finding that is not a fix [HIGH, probed]:** with `diff.<driver>.command` in a repo's local
`.git/config` and a `.gitattributes` line selecting it, a **bare `git diff` — no flags — executes
the named program.** So `--ext-diff`/`--textconv` are deliberately *not* denied: denying them
would close nothing while reading as armor, the precise failure this guard's design rejects. It is
now documented in the honest-boundary section with its mitigation (`git clone` does not carry the
remote's config, so a repo you cloned yourself can't set the driver) and its real exposure (a repo
that *arrives* as a directory or archive with `.git/config` already written). Also probed and
cleared: `core.pager` does **not** fire without a TTY, so that vector is genuinely absent — the
earlier dismissal of the ECC pager-hardening idea holds.

## Pass 2 — empirical runtime

- **The probe was run** — required by AGENTS.md after any guard change, and not run when S1 landed.
  All checks PASS, including the two that matter here: *the guard DENIED the reviewer's command*
  and *the guard IGNORED the main loop's identical command*. Preloading, `${CLAUDE_PLUGIN_ROOT}`
  expansion, and namespacing all still hold.
- **The pending re-baseline was run** (54 headless sessions): **15/18, negatives 8/8, `postmortem`
  positives 3/3 and 3/3.** Captured at `evals/baselines/2026-07-24/homelab-ops/`.
- **A finding was killed by measurement.** Round 1's P2 proposed negative routing on `runbook`'s
  description to guard the runbook↔postmortem seam. The eval shows no cross-firing in either
  direction, and the fleet's own rule is *no description edit without an observed failure to pin
  it to*. **Not landed**, with the evidence recorded in the baseline note. A reviewer's
  plausible suggestion losing to a measurement is the system working.

## Pass 3 — technical accuracy of the content

- **The runbook example's restore was wrong [MED, fixed].** It piped a plain `pg_dump` into a
  database that still had its schema — `relation already exists` when followed. Now drops and
  recreates the schema first, adds `ON_ERROR_STOP=1` (without it psql prints errors, exits 0, and
  a half-restored database looks like a success), and addresses containers by compose *service*
  name, since `docker exec paperless-db` fails unless the compose file pins `container_name`. Note
  this file has now been corrected twice — Codex caught the missing server, this pass caught the
  non-empty target. Worked examples earn their keep by being executed, not read.
- **Verified clean:** the a11y reference (live-region semantics, `aria-activedescendant`, focus
  restoration — all correct), `homelab-platform`'s compose commands, the OpenAPI starter, and the
  RFC 9457 text.

## Pass 4 — portfolio and platform gaps

- **`.probe-tmp/` and `probe-transcript.jsonl` were not gitignored [LOW, fixed].** The probe
  removes its workspace *only when the run passes* — so a failing probe leaves both in the tree,
  exactly when a maintainer is debugging and least likely to notice.
- **Version stamp [fixed]:** 1.1.0 → 1.2.0; 90+ commits and a new skill had shipped under one
  version.
- Manifests, LICENSE, `.gitattributes`, and CI job coverage are complete. The remaining gaps are
  the known backlog ones (observability, `lab-incident`, behavioral evals).

## Pass 5 — verification and landing

Round 1's H1/H2/H3 landed as code, not notes:

- **The guard/hook roster split-brain is now a validator rule.** `hooks.json` carries its own copy
  of the roster in a `case` fast-path; adding an agent to `GUARDED_AGENT_NAMES` alone left it
  unguarded while every file claimed otherwise, and the hook still exited 0. Covered by a mutation
  test, **verified to fail without the rule**.
- The `Bash(git diff:*)` scoped-grant branch has a test; the documented-skill-fields test now
  asserts *every* key in `KNOWN_SKILL_FIELDS` rather than a hand-picked five, so a typo in the
  newly-added `background` entry cannot pass unnoticed.
- Round 1's P1/P3, L1, C2, C4, C5, C6 and D1–D6 all landed (see the commits).

**Still open, deliberately:** round 1's C1 and C7 (both eval- or H1-gated by design), finding 1 of
the July quality review (stack-neutrality), and the backlog's own Tier 1/2 items.
