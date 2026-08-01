# Adversarial review of the WF-001 round documents — 2026-08-01

**Status: historical review evidence.** A Codex adversarial review (via the codex-companion
plugin runtime) examined the WF-001 round's branch diff against `main` — seven files, ~1,676
added lines: the GRAPH-001 revision base, the round spec, and the paired plan. Verdict:
**needs-attention**, four findings. Each was verified against the tree before disposition; all
four changed the round documents in the same-day amendment commit. This file is dated evidence
for WF-001; it is never a task list.

## Findings, verification, and dispositions

**1. [high] The round docs bypassed their own approval gate — CONFIRMED.** The roadmap's
GRAPH-001 item said "Do not extend `run_state.py` or add workflow files until the boundary is
accepted," and GRAPH-001 was still `decision-needed` ("implementation authority pending") while
the spec declared an active round. A proposed record carries no implementation authority
(docs/README.md rule 3); conversational approval is not a recorded transition.
*Disposition:* the operator accepted the revised GRAPH-001 on 2026-08-01; the acceptance, the
WF-001 amendment, the roadmap resolution (decision-needed item retired, WF-001 `active`,
GRAPH-002 `ready` for the descriptive layer), and the round registration all landed before any
implementation task runs.

**2. [high] The scope worker could mutate the reviewed checkout — CONFIRMED, by this round's own
probe.** The plan's scope stage used a default workflow agent (`workflow-subagent`, unguarded per
probe run 5) with only the prompt phrase "read-only" as its boundary — authority by prose.
*Disposition:* scope now runs under `agentType: 'sde-agents:code-reviewer'`, structurally guarded
and probe-verified inside workflows; every command scope needs is on the guard's git allowlist
(`diff`, `log`, `status`, `merge-base`, `rev-parse`, `ls-files`).

**3. [high] The packet schema contradicted the invoked agents' canonical contracts — CONFIRMED
on both material counts, with one reviewer error.** Confirmed: the verdict enum
(`merge/merge-with-fixes/do-not-merge`) contradicted `code-reviewer`'s canonical verdicts
(APPROVE / APPROVE WITH NITS / REQUEST CHANGES, and PROVISIONAL — COMMIT AND RE-REVIEW for
mutable trees — exactly what the pilot reviews); and `application-security-auditor` was the
wrong agent entirely — its own description excludes branch diffs ("Not for a PR/branch diff —
use `sde-agents:code-reviewer`") and it holds no `Bash`, so it cannot even enumerate a diff.
Codex's severity claim was wrong: P0–P3 **is** the reviewer's canonical scale
(`agents/code-reviewer.md:65`); the schema's severity enum was already correct.
*Disposition:* the security lane is a second `code-reviewer` pass seeded with a security-only
threat model (the fallback `sre-tool` documents); the verdict enum now mirrors the reviewer's
canonical forms including PROVISIONAL; the scope packet records `head_sha` and `tree_dirty`, and
the merge record binds to that SHA and is capped at PROVISIONAL on a dirty tree.

**4. [medium] No fail-closed path on schema-retry exhaustion — PARTIALLY CONFIRMED.** The
runtime's documented contract resolves failed `parallel()` thunks to `null`, so the falsy-packet
check did catch lane failures; but the direct-await scope call's abort path was unhandled and
would have surfaced as a bare runtime error.
*Disposition:* every agent await is wrapped; failures return structured `inconclusive` verdicts
naming the failed lane. Codex's further recommendation of a dedicated deterministic
failure-path probe was **deliberately not adopted** — disproportionate for a bounded pilot; the
documented null-contract plus the recorded assumption covers it, and the pilot run itself
reports whether retries fired.

## Review limits

The reviewer worked from the round documents and repository tree only; it did not run the
probes, so finding 2's confirmation rests on this round's own probe evidence (run 5), and its
severity-scale error in finding 3 shows document-level review can misread a contract it did not
open — the same reason the round's own gates demand fixtures over prose.
