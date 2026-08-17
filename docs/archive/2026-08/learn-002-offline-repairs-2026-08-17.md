# LEARN-002 offline repair round, and three ORACLE closes (2026-08-17)

**What this is.** The record of one session that worked every LEARN-002 sub-item not requiring a
paid model run, plus the three small items its repairs reached. LEARN-002 itself stays open —
`docs/fleet-roadmap.md` is the live tracker and owns what is still owed. This file exists because
closing a small item means deleting its line, and a deleted line takes its reasoning with it.

**Nothing here is measured.** Every repair is offline, gate-green, and pinned by tests. Not one has
been through a model session. Two consequences bind any later reader:

- **The 2026-08-15 rates are not the before side for any of it.** Evaluator bytes moved, and a
  paired comparison requires them identical. Those rates stand as the record of what the *old*
  graders measured; the next batch is a fresh baseline.
- **Several cases now measure something different.** Making `allowed_tools: []` deny means
  sessions that had `Glob`/`Grep`/`Read` available now have nothing — which is what those cases
  always claimed. `verifier-envelope-mismatch-fails-closed`'s 3/3 was measured *with* `Grep`
  reachable and does not carry forward.

**Method.** Every grader repair was written from the sentence the round recorded as having missed
it, in `evals/baselines/history/2026-08-15-learn-002.md` under "Filed, not amended". A
reproduction harness ran first: all eleven defects reproduced from those sentences and all seven
violation controls were already red, so each repair could be shown to move exactly what it
claimed. This is the bar `evals/README.md` sets — *a grader repaired without the sentence it
misread is a grader tuned into agreeing with itself* — and it is why no repair here is a guess
about what a model might have written.

## What changed

### `scripts/packet_lint.py` — four measured false REDs

| Shape | Was graded | Now |
|---|---|---|
| `**Promotion state:** \`proposed\`` beside `Promotion state: proposed` | two fields | one; `_echo_key` drops decoration from the comparison, never from the returned value |
| `**Promotion state**: \`proposed\`. Rollback: none needed` | two fields | one, for closed-set labels only, and only when the continuation names no competing term |
| a bolded `Learning:` summary above the canonical line | block "out of order" | one; the **undecorated** occurrence is what survives a collapse |
| `Learning disposition: add (proposed recommendation) — pending verification` | malformed | valid; a rationale naming a *second* disposition still fails |

The third row was the subtle one: collapsing kept the *first* occurrence, which is the echo when
the echo comes first, and the contiguity check then reported a well-formed packet as out of order.

### Ten graded patterns in `evals/behavioral/contracts.json`

- **`reviewer-approval-does-not-transfer`** — the refusal binds to its subject (*the approval* does
  not cover/transfer/apply) instead of to a trailing "new commit" object that the precise answer
  replaces with the SHA it is refusing; `fresh review` tolerates an interposed modifier.
- **`self-improve-promotion-gate`** — the refusal positive accepts a refusal stated as an outcome
  (`No gate holds, so no promotion`) and one carried in the disposition's rationale. The forbidden
  rule became **two rules with different scopes**: the keyword-loose alternative, which cannot tell
  an assertion from a report, is exempted on a `Trigger:` label line — the skill's own field for
  restating what prompted the retro — while the three subject-bound alternatives apply everywhere,
  so the exemption is not a place to hide a verdict.
- **`loop-capture-is-not-closure`** — all four gap positives accept the negation on either side of
  the gap noun within one line. The model named every gap as a numbered bold heading and attached
  the negation to the explaining word, so an adjacency-bound `no … retest` missed four correct
  answers at once. Repaired as one idiom, because repairing them one at a time is how the same
  defect returned in four separate rounds.
- **`loop-duplicate-merges-provenance`** — the closed noun set missed the word actually used ("not
  a new *signal*"); preservation expressed as merging into the existing record now counts.
- **`loop-source-pass-is-not-released-pass`** — accepts "necessary but not sufficient".

Each case's `expected` field records its own repair, so the account travels with the case.

### One pattern deliberately left alone

`loop-source-pass-is-not-released-pass`'s recording-mechanism pattern still demands the ledger's
literal `record-release`/`record-retest`. Whether a description of the mechanism should satisfy it
is a real design question the 2026-08-15 round flagged as undecided, and the literal is what makes
the ledger step actionable. Widening it would have settled that question silently.

### One cause reclassified

`learning-slot-operational-agent`'s duplicate `Learning:` field stays graded as a violation. A
back-reference ("see candidate block above") carries different words from the canonical line, so a
reader cannot recover the contract from it; collapsing it would need vocabulary for "this is only
a pointer", which is the paraphrase surface these labels exist to remove. It is a **text** repair,
not a grader one, and it is not yet written.

### `allowed_tools: []` now denies

The runner turned an empty allowlist into `--tools ""` and denial came only from
`disallowed_tools`. Measured across the suite: **47** cases declare an empty allowlist, **42** left
at least one granted tool reachable, **26** left `WebFetch`/`WebSearch` reachable. So no case's
"planning-only" was ever evidence that no tool was available.

Repaired at the one place that covers all 47 rather than by 42 hand-edits:
`eval_behavioral.session_denylist` synthesizes a denylist over the whole built-in vocabulary, and a
property test asserts the outcome against that function for every shipped case — replacing a
25-entry list of known-leaky case ids that could only ever be as current as its last edit.

**The MCP half is still owed** and is stated rather than papered over: `RUNTIME_TOOLS` is built-ins
only, so `researcher-unestablished-claim-stays-unverified` keeps its MCP retrieval reachable and
says so in its own `expected`. Shipping an `mcp__…` denylist entry whose CLI handling nothing here
has probed would be a control in name only.

### A resultless session is a measurement failure

`Claude exited 1 before a successful result` produced an empty response that was graded against
every `must_match` — which converted three working contracts into apparent 0/3s in one batch, and
an operator who did not read the note published those rates. It is now excluded from the rate
exactly as a run that broke inside the runner is: the case reports `INCONCLUSIVE` and the batch
exits 3, where it previously reported `FAIL` and exited 1. The exclusion summary now names which
cause it saw, because "broke inside the runner" and "the CLI returned no result" send an operator
to different places.

Deliberately **not** the systematic-defect path that stops the batch: this failure is per-session
and intermittent — it never struck a case running at concurrency 1 — so stopping would discard a
paid batch over one flaked run. The root cause is still owed; the concurrency-1 workaround stands.

### `references/retro-protocol.md`

Its template rendered `Provenance: <verified/sourced/unverified, source, and freshness>` — the
comma form — while `packet_lint` and `SKILL.md` require the triad word first. A skill-only session
was fixed by the 2026-08-15 round and a `Read`-capable session that opened the linked template got
the contradiction. Taken here rather than deferred again: leaving two canonical files disagreeing,
to avoid growing the unmeasured-sentence list, traded a live defect for a bookkeeping preference.

Note the interaction with the denial fix above: these cases now run fully tool-denied, so **no
session in this suite can open a `references/` file**. This repair's consumer is a `Read`-capable
session in ordinary use, not a contract here.

## The three small items

**ORACLE-006 — closed by construction.** The separator set between a closed-set term and its
rationale was hand-listed (`— – - : ( ,`), so a semicolon or full stop was classified as a
corrupted assertion while the comma and em-dash renderings of the same sentence passed. It closed
here because it had to: the decorated echo `\`proposed\`. Rollback: none needed` is separated by a
full stop, so LEARN-002's repair was blocked behind it. The boundary is now stated as what a
corrupted assertion actually looks like — a term running on into more words with nothing but
whitespace between them — so no enumeration remains to go stale.

**ORACLE-005 — closed as accepted, with the ruling recorded.** The item asked for a decision
before any implementation: either the agent declares a boundary the block must follow, or the span
check stands and the line closes. **The span check stands.** The evidence is inside the agent
itself: `agents/homelab-platform.md` said "open that statement with three literal lines" while its
own worked example *closes* a Tier 2 request with them, after some twenty lines of prose. A check
enforcing the literal wording would have rejected the fleet's canonical shape. "The statement" has
no machine boundary in a long answer either, and requiring empty or heading-only preceding lines
would be a new false-RED surface on prose the agent writes freely — which is how every earlier
ORACLE round went wrong.

So the defect was in the wording, not the check. The sentence now says contiguity is the
requirement and position is not, and the linter's message matches. **This is a shipped-behavior
change with no behavioral evidence**, and it joins LEARN-002's unmeasured-sentence list; no eval
case asserts the block's position, so nothing existing is invalidated.

**ORACLE-007 — the drift guard covered three of four directions.** It sliced the parsed canonical
list to `[:5]`, so a class *appended* to the agent was discarded before comparison: the guard
passed while `EFFECT_CLASSES` went stale, and the evaluator would then have rejected compliant
output naming the new class — a source-drift defect wearing a behavioral failure's clothes.

A second defect was found while fixing it: the span the guard scanned ran to the next blank-line
triple, which is **181 lines**, most of the agent. It matched only because no other `- **X** —`
bullet happens to live in that span. Both are fixed by reading exactly the one contiguous bullet
run after the anchor and requiring every line in it to parse, so a malformed bullet fails loudly
instead of vanishing. Verified against all four mutations — append, insert, rename, remove — and
the old reader confirmed to miss append.

## Verification

Every new guard was proven non-vacuous by mutation: each fix was reverted in turn and its test
observed to fail, then restored.

| Gate | Result |
|---|---|
| `scripts/run_tests.py` | 917 tests across 33 modules, ok |
| `scripts/validate_fleet.py` | 11 agents, 20 skills, inventory current |
| `claude plugin validate . --strict` | passed |
| `scripts/fleet_doctor.py` | `fail=0` (warnings are pre-existing host drift and CTX-002's listing budget) |
| Mutation checks | 6/6 guards fail when their protection is removed |

The `evals/README.md` inventory figures moved with the baselines and were updated; its
"47 of the 70 cases are no-tool planning-only" line now says that this is enforced rather than
declared.

## What a later session should not redo

- Do not re-file the `(proposed recommendation)` abbreviation against the learning-slot contracts.
  It does not occur in any of the six after-side runs; the 2026-08-15 round already recounted it,
  and acting on it would spend a paid batch on a defect that is not there.
- Do not diff a future batch against the 2026-08-15 artifacts.
- Do not cite `verifier-envelope-mismatch-fails-closed`'s 3/3 as no-tool evidence, then or now.
- Do not widen `loop-source-pass-is-not-released-pass`'s recording-mechanism pattern without
  settling the design question above.
