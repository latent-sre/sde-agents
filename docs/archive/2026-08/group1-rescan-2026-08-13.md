# Group 1 rescan under the engineering-program lens (2026-08-13)

**What this is.** The five lab-operations skills — `lab-audit`, `lab-incident`, `security-audit`,
`upgrade-campaign`, `restore-drill` — re-scanned against the reading rule `AGENTS.md` and
`docs/engineering-program.md` now state: the reader of fleet prose is the next session, not the
operator's memory, and any trim is decided by *who is the real reader* and *what consumes the
artifact*. The original PROP-002 scan graded this group against an audience of one human with
continuous memory; this rescan re-judged its findings and hunted the failure class that lens could
not see — mechanisms the fleet needs that were missing or half-wired. Dated evidence; the edits it
produced are in git history and every deferral names its trigger.

## Re-verdicts on the original LOW findings

Six of ten flipped from "vocabulary" to load-bearing mechanism; three drops stand; one is partial.

| Original finding | Re-verdict | Why |
|---|---|---|
| lab-audit "the ledger's keeper" | **Keep** | Names the write-authority principal in a deliberate producer/consumer split: the auditor is read-only by design and structurally cannot flip its own findings. The row's reader is the next audit session |
| lab-audit "justify the exception in writing" | **Keep** | Loop convergence: without a durable written exception, a memoryless successor re-flags the same deliberate choice forever |
| lab-incident timeline note | **Keep** | `postmortem` builds its timeline from artifacts, never memory, and grades reconstructed entries `[unverified]`. For an agent, memory does not smooth — it is discarded; the contemporaneous note is the only `[verified]`-capable evidence a later session can hold |
| lab-incident outage→follow-up downgrade | **Keep** | A state edge that ends the mitigate-first authority inversion and gates the Step 5 handoff — mislabeling it either extends emergency latitude or exits it early |
| lab-incident "maintenance page" | Drop stands | One example action in a scope-reduction row; audience genuinely the household |
| security-audit "who can rotate it" | Partial keep, no edit | Thin as a role question; real as an authority question — rotation is an approval-gated change, and "consumers that hold a copy" includes agent sessions. The neighboring clauses carry it |
| security-audit observability audience | **Keep + sharpened** | The audience is real: agent sessions that read logs, plus the transcripts and eval artifacts they leave behind. The file already knew this — its `git log -p` ban exists because the session transcript persists — and now the logs row says it too |
| upgrade-campaign postmortem output | Drop stands | Already conditioned; "the near-miss is the cheapest lesson available" is learning-loop intake economics, not retro ceremony |
| upgrade-campaign "majors get their own session and approval" | **Keep + sharpened** | The scanner read a meeting; a session here is a context window. Now states what it is: the same per-apply tier grant sought unbatched so a breaking change cannot ride through a routine-looking list, and a fresh context holding one migration's notes |
| restore-drill RTO | Drop stands | A measured number with a date, never a negotiated target |

## What the rescan changed (all commits on this branch, dated 2026-08-13)

- **lab-audit** — the loose wire between check 1's "justify the exception in writing" and the
  ledger's `accepted` status is connected: an `accepted` row carries or points at its written
  justification, because the row's reader cannot tell a considered exception from a silence.
- **security-audit** — the secrets reference's logs row names its actual audience (agent sessions,
  retained transcripts and eval artifacts), consistent with its own transcript-leak rule.
- **upgrade-campaign** — the majors clause states its two mechanisms explicitly (unbatched tier
  approval; fresh context).
- **lab-incident** — two clauses, landed **with paired behavioral evidence** because the file is
  contract-graded: the Step 3 note is emitted as you go (a session that ends mid-incident takes
  everything unwritten with it — and `postmortem` refuses memory as a source, so an unemitted note
  is unrecoverable evidence), and the Step 4 downgrade is named as the authority edge that ends
  the mitigate-first inversion. `incident-mitigate-first`: 3/3 before == 3/3 after
  (`evals/baselines/history/2026-08-13-group1-rescan.md`, conditions recorded there).
- **restore-drill** — zero edits, and that is a verdict, not an omission: step 3 ("a restore
  performed from memory by the person who set it up proves nothing about the 3 a.m. version") is
  the program's clearest exemplar — an *executed* verification that the runbook artifact alone,
  without its author's memory, can drive recovery. The 3 a.m. version is the next session.

## Deferred trigger-bound

- **upgrade-campaign: the campaign plan has no durable home.** A campaign that outlives one
  session holds its plan and per-service done/verified/remaining status only in context. No
  campaign has yet demonstrably spanned sessions, so per the proportionality rule this waits.
  Trigger: the first campaign that dies mid-list and cannot resume from its own artifacts. Donor
  pattern: `skills/sre-tool`'s plan file.

## The external literature, as of this rescan

Anchors supporting the lens (all quotes search-excerpt-mediated — direct fetches of arxiv.org,
anthropic.com, and cognition.com are egress-blocked in this environment, recorded as ledger
candidate `lc_854a12b53a16434f81128a9ca256fbc0` — so grade these `[sourced]`, not `[verified]`):

- **MAST** ("Why Do Multi-Agent LLM Systems Fail?", Berkeley, NeurIPS 2025, arXiv 2503.13657;
  1,600+ annotated traces): ~42% of observed multi-agent failures are specification/organizational
  design defects and ~37% inter-agent misalignment (context loss at handoffs, format mismatches) —
  the failure distribution lives where ceremony operates.
- **MetaGPT** (ICLR 2024, arXiv 2308.00352) and **ChatDev** (ACL 2024, arXiv 2307.07924):
  structured document artifacts between agents measurably reduce cascading errors versus free-form
  chat; ChatDev's "communicative dehallucination" is a mandatory clarification step at the handoff.
- **ACE** ("Agentic Context Engineering", arXiv 2510.04618, Oct 2025): iterative self-rewriting of
  playbooks degrades them ("context collapse", "brevity bias"); what works is itemized incremental
  deltas by a separate curator role — structurally the learning ledger's design, and the reason
  the PROP-002 round's subtractive fix and the static-review convergence bound exist.
- **Experience-following** (ACL 2026, arXiv 2505.16067) and the 2025–2026 memory-poisoning line:
  agents replay stored experience uncritically, so unverified lessons propagate errors; surviving
  defenses are provenance checks, validation-before-trust, and quarantined intake — the ledger's
  state machine, independently justified.
- **A2A protocol** (2025, Linux Foundation): typed artifacts plus an eight-state task lifecycle as
  protocol primitives — status lifecycles are the industry's handoff standard, not enterprise
  residue.
- **The counterweight** (Cognition "Multi-Agents: What's Actually Working", Apr 2026; Anthropic's
  2026 multi-agent guidance): handoffs are lossy and cost 3–10x tokens; single-writer per artifact
  and fewer, richer boundaries beat elaborate graphs. Both halves of the fleet's rule.

No study yet measures ceremony *fields* (owner tags, written justifications, timeline capture) as
an experimental variable, and none quantifies the emit-but-never-persist packet failure — on those
two points this repository's field evidence is ahead of the literature.

## The correction this rescan grounds

The original scan's LOW tier definition — "vocabulary only" — was unsound for this group because
its severity model assumed an audience of one human. The generalizable rule, now stated in
`AGENTS.md` and `docs/engineering-program.md`: a fleet of stateless workers re-creates the
conditions organizations invented ceremony for, so the second person exists — it is the next
session. A later proportionality round must apply the two-question test before tiering, and must
read this record's re-verdicts rather than re-deriving them.
