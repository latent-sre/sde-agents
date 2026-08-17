# 2026-07-30 deep-review round 1 — routing before/after

Its `before/`, `after/`, `recheck-before/` and `recheck-after/` captures retired to Git history on
2026-08-17 under the retention rule in `../README.md`, and **this file is their record** — the
checkout no longer contains them.
Recover the whole directory with `git show f4b119c:evals/baselines/2026-07-30-deep-review-r1/` (or
a single file by appending its path); `f4b119c` is the last revision that carried it.

Conditions (all runs): `--model opus --timeout 420 --clean-room`, CLI 2.1.220, threshold 0.5.
`before/` is main @ `ab7660e`; `after/` is the deep-review wiring branch. Clusters measured:
`investigation`, `verification-seam`, `homelab-ops` — the three whose members' descriptions the
round edited (code-reviewer, application-security-auditor, security-audit, root-cause, postmortem).

Verdict, per the suite's reading rules (negatives at any fire rate are defects; positive rate
drops are regressions; absolute agent-positive rates are known-suppressed in headless mode):

- **Negatives: 18/18 clean on both sides.** No near-miss started firing after the edits.
- **Positives:** investigation and verification-seam sat at 0% both sides (headless agent
  suppression — nothing to regress). homelab-ops: `pos-incident-after-update` improved 33%→67%
  (the outage-routing fix); three cases dropped at `--runs 3` and were re-measured at
  `--runs 5` per side (`recheck-before/`, `recheck-after/`): `pos-attacker-reach` and
  `pos-default-creds` recovered to 5/5 — variance. `pos-audit-security` stayed depressed
  (before 8/8 total, after 4/8).
- **Ablation** (`ablate-secaudit/`): reverting security-audit's description alone still produced
  3/5. That does **not** isolate the cause: application-security-auditor's description also gained
  the competing terms "running lab", "security-audit", and "lab-audit" in this round, so the
  single-description ablation cannot exonerate either routing edit. The case's prompt deliberately
  straddles the lab-audit/security-audit boundary and every failing run fired *nothing* (inline
  answering, the known headless noise mode) rather than a wrong component. The depressed rate is
  unresolved; no causal claim is made from this incomplete ablation. lab-audit's own description
  was not edited in this round.
