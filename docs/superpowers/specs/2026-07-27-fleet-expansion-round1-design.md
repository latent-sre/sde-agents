# Fleet expansion — Round 1 design (2026-07-27)

Approved in-session 2026-07-27. Scope was chosen from the fleet's three pre-adjudicated expansion
menus, not from a fresh gap hunt — the backlog's "Still open" list supplied every item here.
Round 2 (the `superpowers:systematic-debugging` → `skills/root-cause` mining round, top of the
official-plugin import menu) is deliberately out of scope and gets its own session and PR.

## Operator decisions that shaped scope (2026-07-27)

- **Lanes:** in-repo reopened items now; official-plugin mining round second, separately.
- **PowerShell:** the operator does author fleet/lab work in PowerShell — the exact question the
  backlog said settles the reopened `powershell.md` item. Decision: land it.
- **`skills/githits-mcp/`:** removed (was untracked; duplicated the system-installed skill and
  failed the inventory-drift check). Done in-session; validator green at 8 agents / 17 skills.
- **Eval posture:** touched-cluster anchor only — no full routing re-baseline this round.

## Non-goals

No new agents or skills (roster stays 8 agents / 17 skills). No full routing re-baseline. No
changes to `F:\repos\sre-agents` — the donor is read-only source material this round.

## Item A — `code-craft/references/powershell.md` + description widening

Port the donor file (`.claude/skills/craft/references/powershell.md`, sre-agents @ `e2eef27`)
rather than author blind — it verifiably contains everything the backlog item names: `$null -eq`
ordering, the Pester 5 Discovery/Run split, and 5.1-vs-7 divergence.

- **Scrub:** the one PCF mention ("PS 7 on Linux/PCF too") — the backlog's blanket kill rule.
- **Rewire:** the `./tdd.md` link to match how this fleet's references cross-link.
- **Adjudicate at port time:** the Authenticode-signing bullet — real Windows practice, not
  obviously enterprise-only; default keep-compressed.
- **SKILL table:** add the row `PowerShell → references/powershell.md`.
- **Description:** widen the language list to "Python, Bash, PowerShell, or Go" — this is the
  description edit that owes Item B's routing discipline.
- **Provenance:** commit message notes `adapted from latent-sre/sre-agents`.

## Item B — craft-cluster eval discipline (the gate Item A owes)

Sequence dictated by the parked re-baseline notes (backlog "Still open", 2026-07-25):

1. **Diagnose run first:** one completed foreground run of `evals/routing/craft-vs-fullstack.json`
   at raised timeout (~420s), `--model` pinned (opus — the only prior comparable data), conditions
   recorded. This doubles as the confirmation run the empty-cwd case-design hypothesis needs.
2. **If confirmed** (failures fire nothing; sessions answer "there is no project here"): fix the
   case design — narrative-style prompts like `homelab-ops` (20/24 under identical conditions) —
   *before* anchoring. Anchoring defective cases would produce the "anchor that cannot state what
   it measured" the parked notes warn against.
3. Capture the **before-anchor** on the (possibly fixed) cases; land Item A; run **after**; diff.
   Trust negatives and regressions over absolute positive rates, per `evals/README.md`.
4. **Seed:** one PowerShell positive (e.g. a Pester Discovery/Run failure prompt) and one tight
   negative into the cluster.

## Item C — `lab-audit/references/checks.md`

Body-only split; the description is untouched, so no routing run is owed. The eight inline checks
move to `references/checks.md` and gain the concrete command-level "how" each currently lacks.
`SKILL.md` keeps the mandate paragraph and a skill-relative link (orphan check requires it).

The **findings ledger** lands as an *output convention* — a ledger-shaped block the audit emits
for the operator to append in the lab repo — not a file the skill writes: the skill denies
Write/Edit/NotebookEdit, and a read-only skill cannot own a file it writes. This is a deliberate
departure from a literal reading of modernization Tier 2 item 6.

## Item D — three behavioral contracts

New cases in `evals/behavioral/contracts.json`, following the suite's own design rules (pin the
component, deterministic `must_match`/`must_not_match`, `disallowed_tools` on destructive-shaped
prompts):

1. **eng-ladder report-to-caller handoff** — a sub-question above altitude is reported up, not
   silently absorbed.
2. **lab-incident mitigate-before-diagnose** — a live-outage prompt produces mitigation-first
   ordering; never a root-cause loop while the service is down.
3. **restore-drill scratch-target rule** — a rehearsal targets scratch; never restores over the
   live service.

Landing rule: each case must run green against current definitions before it counts as landed —
a red case is a real defect finding to fix, not a case to ship failing.

## Verification and PR shape

- Validator + unit tests + `claude plugin validate . --strict` after each item.
- Behavioral suite run for the three new cases, green evidence captured.
- Routing before/after diff for the craft cluster only.
- One PR; conditional-gates rows filled for the description edit (routing run) and the new eval
  cases (green evidence).
- Backlog updated: `powershell.md` closed as decided-yes-landed; the lab-audit split and the three
  contracts struck from "Still open".

## Assumptions

- Pinned model for eval runs is opus, matching the only prior comparable data.
- Reference files do not appear in the README inventory, so no inventory churn is expected
  (the validator confirms either way).
- The ledger-as-output-convention reading of Item C, stated above.
