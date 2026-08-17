# PR review gate: request explicitly, wait on the head, bound the disposition loop

**Status:** Accepted — consolidates rules already operative in `AGENTS.md` ("Opening a pull
request") together with the incident evidence that minted them; it proposes nothing new. The
escape semantics were unified to one-further-round-per-ruling across both convergence bounds on
2026-08-16 (`c2865eb`). The PR cap was raised from two rounds to **three** by operator ruling on
2026-08-17, under this record's own reopen trigger — see "The operator ruling" below.
**Date:** 2026-08-16 (amended 2026-08-17)
**Corroborating archive evidence:**
[`prop-001 outcome`](../archive/2026-08/prop-001-outcome-2026-08-13.md) (records the
review-latency and operator-step findings contemporaneously with PROP-001).

## The rules this record evidences

The governing text is `AGENTS.md`; this record is its provenance, kept out of the per-session
context on purpose. The rules, in short: the automated review is request-triggered and requesting
is an operator step; both passes are waited for on the current head, and a review-driven edit
owes another wait; every comment is dispositioned as applied or declined with the reason; and at
most three review-driven edit rounds land per PR, with an explicit operator ruling buying one
further round.

## Evidence

1. **Reviews are request-triggered and land roughly ten minutes after the request, not after PR
   creation.** Every bot pass in this repository's history is preceded by a `review_requested`
   event. PR #124: review requested at 07:07:07, passes at 07:17:28 and 07:17:44.
2. **The request cannot be automated from an agent session.** The reviewer is
   `copilot-pull-request-reviewer[bot]`, which `suggestedActors` does not list; `gh pr edit
   --add-reviewer Copilot` fails to resolve the login, and a REST `requested_reviewers` post
   silently leaves `reviewRequests` empty. The PR page's Reviewers box is the only path that
   works. The Codex connector has followed Copilot's request without needing one of its own.
3. **Merging without waiting costs reverts.** A PR merged four minutes after opening carried a P1
   finding that landed two minutes after the merge and cost a revert.
4. **Unread comments carry real refutations.** A later PR's unread review comments correctly
   refuted a claim that would otherwise have promoted an unsupported rule into `AGENTS.md`.
5. **PR #128 merged unreviewed** while a session waited for a pass nobody had asked for. The
   guide then described the reviews as arriving "two to five minutes behind `gh pr create`",
   which read as a wait to serve rather than a step to take; the rule was reworded to name
   requesting as an action, and on this repository an operator one.
6. **The head-binding clause closed a loophole in the rule's own first draft**, which would have
   let the gate be satisfied by a review of code a later fix had already replaced.
7. **PR #136 ran ten review-driven rounds** after the two-round deep-review cap was written,
   because that cap bound the static-review gate and left the disposition loop open. That is the
   origin of the PR cap (set at two, raised to three in 2026-08-17's ruling below), and of
   stating explicitly that the cap bounds edits, never
   waits.

## The operator ruling (2026-08-17)

The cap is **three** review-driven edit rounds per PR, not two. Evidence item 7 minted *a* cap and
still stands — ten unbounded rounds is the failure mode — but two rounds proved too tight against
observed review behavior: a first round routinely draws a follow-up finding on the bytes it just
minted (PR #142's round 2 caught defects in that branch's own round-1 fixes), which consumed the
budget before any independent third look could land. Three rounds lets that self-correcting
sequence finish inside the cap instead of spending the operator escape on it. The escape survives
unchanged on top, so a ruling still buys a fourth round when one is genuinely owed.

## Rejected alternative

Keeping this chronicle inline in `AGENTS.md` — rejected 2026-08-16. The narrative served the
rules' editors, not the next session (the guide's own reading rule), and cost roughly 530 tokens
in every session's context on every host. This record is the durable home; the guide cites it by
path, and the validator's stale-path tripwire fails the build if the record goes missing — so the
citation is machine-checked where the inline narrative never was.

## Reopen trigger

A change in the review platform's behavior — the bot becoming requestable via API, review passes
firing on PR creation, or a different reviewer identity — invalidates evidence items 1–2 and
reopens the operator-step rule. The caps (items 3–7) reopen only on an operator ruling.
