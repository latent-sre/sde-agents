# Fleet program outcomes — 2026-07-29

**Status: historical evidence.** This is the outcome record for two completed rounds (fleet
expansion Round 1, and the role-expansion/governance program that followed), written per
`docs/README.md` rule 4 when their spec and plans were retired. It records what landed, what was
measured, what was deliberately not done, and the lessons worth carrying. It is **not** a task
list — `docs/fleet-roadmap.md` owns all remaining work.

Git history holds the exact execution payloads (the retired plan files, their task-by-task steps,
and every eval artifact). Their content is not reproduced here.

## What landed

| PR | Items | Outcome |
|---|---|---|
| #37 | ROUND1-001 (partial) | `code-craft/references/powershell.md` + measured description widening; `lab-audit` checks split to `references/checks.md` with the findings-ledger output convention; 2 of 3 behavioral contracts |
| #38 | Governance docs | ROLE-001/ROLE-002 accepted; DEPLOY-001 opened as a proposed decision; two stale "`agent_type` is undocumented" claims corrected |
| #39 | EVAL-002, DEF-001, ROUND1-001 closure | Behavioral runner records conditions + per-run usage and pins its model; scratch cwd moved off `%TEMP%`; the ladder report-up contract fixed and its case relanded green |
| #40 | GOV-001, EVAL-001 | Guard answers `EXIT_INDETERMINATE` on unparseable input instead of the authoritative allow; routing clusters validate their own members, targets, and case ids |
| #41 | ROLE-001, ROLE-002 | Home-Lab SRE identity + `host-onboard` checklist; `application-security-auditor` (static tools, no Bash) |
| #42 | LABSEC-001 | `security-audit` — the adversary sweep of the running lab, with `checks.md` and `secrets.md` |

Fleet went from 8 agents / 17 skills to **9 agents / 19 skills**, inventory regenerated at each
step, with the validator, unit suite, and `claude plugin validate --strict` green throughout.

## What was measured

All routing runs pinned `--model opus` (which resolved to `claude-opus-5`) at a 420s timeout on
CLI 2.1.220, with conditions recorded in every artifact under `evals/baselines/`.

- **The PowerShell widening worked and cost nothing:** `pos-powershell-pester` 0/3 → **3/3**, with
  all seven cluster negatives holding 0% on both sides.
- **The empty-cwd hypothesis was refuted, and something more useful surfaced.** The diagnose run
  found the two most repo-presupposing prompts passing 3/3 while every green-field-buildable
  positive failed 0/3 — the split tracked the *expected component*, not the prompt's assumptions.
  Skill positives with sharp trigger vocabulary: 6/6. Agent- and layer-expecting positives:
  **0/21, firing nothing at all rather than misrouting.** No case rewrites were applied, because
  the hypothesis they were conditional on did not hold.
- **Both role additions dragged nothing:** 14 negatives across two clusters at 0% fire before *and*
  after, including two purpose-built decoys (a personal-laptop prompt wearing Linux-host
  vocabulary; a "fix the SQL injection" remediation bait).
- **The Linux-host positives returned a null** (0/3 → 0/3) with the same zero-fire signature as
  every other agent-expecting positive on this tier. Recorded, not tuned.
- **The hygiene/adversary seam measured clean in both directions on its first run:** both adversary
  prompts 3/3 to `security-audit`; both hygiene prompts 3/3 to `lab-audit` with zero cross-fire;
  the app-code decoy 0%.
- **Governance fixes were proven red-first:** 5 new guard cases and 6 new cluster-schema cases were
  observed failing before their fixes existed, and the schema rule then failed the *real* tree on
  the exact `pos-ci-actions-harden` inconsistency it was written for. `probe_plugin.py`: 14/14.

## DEF-001 — the defect worth remembering

Round 1's third behavioral contract failed twice at landing, and the failure was more interesting
than a passing case would have been. (The raw transcript was captured only to the local, gitignored
SDD workspace; the analysis below is the durable copy.)

Baited with a retry-module task plus "decide whether we should break our monolith into
microservices — just make the call yourself", `sde-fullstack` did **not** absorb the decision, and
did not report it either. It declined with a substantive architectural default — modular-monolith
first, extraction criteria, a "one-question test", "that deserves its own session" — without ever
naming `principal-engineer` or `distinguished-architect`. Its review-packet contract meanwhile held
perfectly, including an honest "Verified: nothing — no code has been executed."

Root cause was drift between siblings: `principal-engineer` and `distinguished-architect` both
required handing the packet back **with the rung named**, while the builder's ladder paragraph asked
only for "the decision needed, the options you see, and your recommendation" — which is almost
exactly what the failing session produced. The definition permitted what the eval punished.

The fix required naming the owning rung, treated an aside-shaped multi-year fork as still above
altitude, and closed the "just make the call yourself" loophole. The case then relanded
**byte-identical** and passed on opus *and* on the tier it had failed on — same case, same regex,
only the definition changed, which is what isolates the fix as the cause.

## Deliberately not done

- **No case rewrites** for the refuted empty-cwd hypothesis; the original cases stand as the
  true-rate record.
- **Full-cluster positive-regression anchoring** was dropped mid-round by operator budget decision
  (thrift scope). The negatives gate — the doctrine's hard signal — ran at full strength.
- **The agent-positive null was not tuned away.** It belongs to EVAL-003's case-design question.
- **No `plugin.json` version bump** in any PR; that discipline is RELEASE-001's.
- **No `lab-inspector`** (LABSEC-002): it is the enforcement shell for these checklists and stays
  blocked on DEPLOY-001, because a guard-enforced agent must not ship into a deployment where the
  guard never runs.

## Lessons carried forward

1. **Agent positives are not a usable routing signal in headless one-shot mode on this tier**
   (0/21, then 0/6, then 0/6), while sharp-trigger skill positives are (6/6, then 6/6). Trust
   negatives and skill positives; design agent cases differently or grade them differently before
   spending a full-suite capture. Recorded on EVAL-003.
2. **An eval that cannot state its conditions is not a measurement.** The behavioral runner was
   silently using the CLI's default model — the most expensive tier, chosen by nobody, recorded
   nowhere — and its `%TEMP%` scratch cwd was blocking the very writes one case's premise depended
   on. Both were found while investigating something else, which is the usual way.
3. **A red case is a finding, not a chore.** Shipping `ladder-report-not-absorb` green by softening
   its regex would have hidden a real definition defect; surfacing it produced the fix.
4. **Own your batches.** A background eval batch must be owned by a session that stays alive to
   receive its completion; artifact-only watchdogs are the false-positive-free liveness check, and
   process attribution must use the full command line *with a retry* — a single-shot process-table
   miss produced a false "the batch died" verdict during this program.
5. **Platform capabilities move.** Verified by invocation rather than memory: `claude plugin eval`
   exists but is still gated ("currently in early access"), so the stopgap runner remains the path;
   `claude plugin tag` already validates `plugin.json` against the marketplace entry, which
   RELEASE-001 should consume rather than reimplement.
