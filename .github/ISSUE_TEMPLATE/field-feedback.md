---
name: Field feedback
about: Evidence from running a released fleet version, with the lifecycle it must traverse before it can close
title: ""
---

<!--
This is a checklist, not automation: nothing fills these fields in for you and no bot closes this
issue. Fill what you know now and leave the rest visibly empty — an unfilled gate is the point.

Issues are evidence-bound intake, not a second work tracker (docs/README.md rule 7). This issue
adds work when the roadmap imports it; until then it is field evidence awaiting triage.

Sanitize before you paste. Keep the minimum reproducer and drop everything else: no secrets, no
credentials, no resolved inventory, no raw transcript. Estate repositories and their commits are
field evidence, never test dependencies of this repository.
-->

## Observation

**Observed → expected:**
**Scope (applies / excludes):**
**Evidence:** <!-- sanitized reproducer, plus the exact revision, version, or environment -->
**Provenance:** <!-- **[verified]** (you ran or observed it — the shown output backs it), **[sourced]** (cited to file:line, URL, or query), or **[unverified]** (assumption or couldn't check) -->

## Baseline conditions

**Fleet version / host / model / reasoning effort:**
**Tool access and budget, where the harness exposes them:**

## Lifecycle

Tick a state only when its evidence is in this issue. Capture is not closure, and a merge is not a
release.

- [ ] **Captured** — sanitized packet above; learning-ledger candidate ID (if recorded):
- [ ] **Triaged** — duplicate check done (existing candidate merged into, or "none found"), one
      disposition chosen (add / merge / supersede / skip / drop), owning canonical artifact named,
      and an owner named:
- [ ] **Evaluated** — targeted, adverse, and transfer fixtures named, with the paired baseline and
      candidate results under comparable conditions, plus the expected observable improvement and
      the non-regression boundary:
- [ ] **Implemented** — candidate revision and the exact generated artifacts evaluated (canonical
      source plus every regenerated host adapter):
- [ ] **Released** — the exact released version containing the candidate:
- [ ] **Retested** — the originating or an equivalent scenario rerun **on that released version**,
      with the environment and the measured result:

**Rejection or rollback trigger:** <!-- what result would reopen, revise, or revert this -->

## Close reason

<!-- One of:
     - retested: the named released version passed the stated downstream acceptance;
     - waived: an owner recorded why the retest is impossible or no longer applicable;
     - rejected: the candidate was revised or dropped, and the rejection evidence is retained here
       so a later loop does not rediscover it.

     A source-level PASS is not a released-artifact PASS. Neither implementation merge nor plugin
     publication is, by itself, evidence that the observed behavior improved. -->
