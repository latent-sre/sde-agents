# Group 4 rescan under the engineering-program lens (2026-08-14)

**What this is.** The five meta-and-process skills — `sre-tool`, `eng-ladder`, `root-cause`,
`self-improve-loop`, `prompt-craft` — re-scanned under the reading rule `AGENTS.md` and
`docs/engineering-program.md` state: the reader of fleet prose is the next session, and any trim is
decided by *who is the real reader* and *what consumes the artifact*. Method identical to the
[Group 1](group1-rescan-2026-08-13.md), [Group 2](group2-rescan-2026-08-13.md), and
[Group 3](group3-rescan-2026-08-14.md) rescans: full reads, measurement exposure mapped before
judging, per-finding re-verdicts, gaps hunted in the direction the original scan could not see.
Dated evidence; citations are by content, not line number, except where the original scan's
citations are quoted.

**Coverage.** All twenty-two files in the group were read in full in one pass — the five SKILL.md
bodies, every reference, every asset including `cli_skeleton.py` — applying the Group 3 coverage
lesson from the start rather than after a challenge. That includes the twelve files the original
scan never flagged.

**Measurement exposure, mapped first — and every candidate edit sits under a freeze.**
`eng-ladder` is frozen by LADDER-001: its stored `evals/routing/ladder.json` benchmark is STALE and
that item owes the capture, so both its description and its body stay untouched — an edit now would
move the bytes out from under a run the operator is about to buy. `self-improve-loop` is graded by
sixteen behavioral contracts and LEARN-002's next action is already a canonical SKILL.md edit to it
owing paired reruns; edits ride that item. `sre-tool` is contract-graded and measured
edit-sensitive — Correction 7 watched an adjacent sentence move the durable-state contract
3/3 → 2/3 → 1/3 in the original round. Consequence, stated up front: **this rescan ships zero
edits by design.** Its product is re-verdicts recorded, so the next session reads decisions
instead of re-deriving them.

## Headline

Ten flips, one finding upheld, four drops standing, two prior overturns confirmed, zero edits,
zero gaps. The pattern that distinguishes this group: it is the **meta group — the files where the
engineering program itself lives** — and the original scan's "enterprise ceremony" findings kept
resolving into the program's own scaffolding, named before the program was written down.
Org-chart vocabulary (consult protocols, debt registers, sign-off gates, version-owning contracts)
turned out to be typed authority edges and durable coordination artifacts wearing organizational
clothes — the exact half-blindness Correction 9 recorded, at its highest concentration. The one
finding all four groups' rescans leave standing at its original severity is eng-ladder's Mode 3.

## Per-finding re-verdicts

| Original finding | Re-verdict | Why |
|---|---|---|
| sre-tool `SKILL.md:39-40` — environment-card mission-block breadth; orchestrator-owned plan file | **Flip to keep** | The card is the fleet's canonical spawn handoff: builders, reviewers, and future maintenance sessions read the mission there so spawn prompts stay small — the artifact-only-carrier rule, working. The plan file is the loop's durable state: cadence contract, counters, gate evidence, safe resume point, all held outside conversation memory because "conversation memory does not survive compaction". The original drop was cost-based (Correction 7 edit-sensitivity); this makes it merit-based |
| sre-tool `plan-file.template.md:19-23` — gate-status sign-off register | Overturn confirmed | "Approval evidence is a pointer to the user's words, never inferred" is an anti-fabrication control against an LLM worker claiming an approval it was never given — an authority edge, real at any headcount. The scan's own overturn holds under the lens that named it |
| sre-tool `multi-component.md:9-16` + `contract.template.md` — versioned interface governance with owner and change-log | **Flip to keep** (conditioning already worked at `eb53758` stands) | One named owner during a parallel batch is the one-writer-per-artifact rule; "builders cite the version they built against" is provenance binding in prose form — the same identity discipline the eval sidecar carries as a digest; the change-log's Propagated-to column is loop convergence made checkable. The `eb53758` conditioning (required once more than one builder writes against the interface) keys it to the coordination boundary correctly |
| sre-tool `multi-component.md:21-23` — mockup sign-off gate | Overturn confirmed | The cheapest fork point in the build, held as a named operator gate in the cadence contract — the skill's live gate mechanism, not borrowed ceremony |
| sre-tool `SKILL.md:51` — "many teams" routing predicate | Drop stands | A paraphrase of the eng-ladder table, which the skill itself names as the source of truth; the owned-conventions rule says any fix lands in the table, and the table is frozen by LADDER-001. "Many teams or systems" already carries the systems half honestly |
| sre-tool relaunch/round-count table | **Flip to keep** | "Counters (survive compaction — the caps reset silently otherwise)" is the loop-engineering mechanism verbatim: a cap held in conversation memory silently resets at compaction and the loop diverges. The template says exactly why it exists |
| eng-ladder `SKILL.md:33-35` — Mode 3 growth feedback | **Upheld** — the one finding the program lens does not rescue | "The single highest-leverage next-level behavior to practice" has no practicing reader: agents are stateless and do not practice. The nearest real consumer — improving an agent from a body of its work — is owned by `self-improve-loop` and `prompt-engineer` with evidence gates, so Mode 3 is at best a duplicate remit costing description surface every session. Frozen by LADDER-001; the trim is a description-plus-body edit that rides that item's paired capture as a measured candidate |
| eng-ladder `SKILL.md:21` — consult-and-decision-record protocol | **Flip to keep** | The "rungs one person occupies" reading was the lens error: the rungs are separate agent contexts, and ownership-vs-consult is a typed edge between them. A scoped consult request at the fork, one decision record back, ownership explicitly declined — that is an artifact-mediated handoff across stateless sessions, and the paragraph carries its own field evidence (the same task read as mandatory ownership blind and optional escalation in dispatch) |
| eng-ladder `SKILL.md:31` — "meets the bar"/"next-level delta" framing | Drop stands | Promotion-packet vocabulary on a sound assessment contract: meets-or-gaps with cited evidence, never invented gaps, scored against the artifact's own remit |
| eng-ladder `SKILL.md:11-13` — "survive the org" | Drop stands | The org is honestly the fleet plus the lab over years; the distinguished core question is accurate at this scale |
| eng-ladder `principal.md:24-26` — Hyrum/SemVer/deprecation "signaling to nobody" | **Flip to keep** | Mirrors Group 3's Hyrum verdict: agent consumers observe real responses and bake quirks into generated clients, and backend-craft's published-surface boundary now conditions the class. The reference also paraphrases `agents/principal-engineer.md`, which wins on conflict — the fix direction runs through the agent file, not this copy |
| eng-ladder `principal.md:36-38` — debt register framing | **Flip to keep** | Deliberate debt recorded "with the trigger to pay it back" is the roadmap's own trigger-bound deferral discipline; the reader is the next session that hits the debt, and "name it in the review packet" makes the capture contemporaneous |
| eng-ladder `distinguished.md:33` — "decision-maker" as reader | **Flip to keep** | "A decision-maker can act from your framing without re-deriving it" is the handoff-completeness criterion verbatim — the receiver acts on the artifact alone. The decision-maker exists: the operator, or the calling session |
| root-cause — zero findings | Confirmed | The hypothesis table's Result column is contemporaneous capture with a named later consumer ("the evidence a postmortem timeline needs"), and three-strikes is a loop-divergence bound — the in-fleet ancestor of AGENTS.md's own two-round static-review convergence bound |
| self-improve-loop `learning-ledger.md:10-27,33` — intake coordinator / attestation prose | Drop **strengthened to keep** | The scan dropped it as accurate description; under the lens it is the self-learning strand's core: quarantine, proposed-fields-as-untrusted-data, coordinator validation, `--sensitivity-reviewed` as attestation-not-scanner. The prose is the CLI's real trust model, documented at the boundary where the next session needs it |
| self-improve-loop `retro-protocol.md:7-90` — five retro types + 13-line output block | **Flip to keep** | The output block is the machine-readable handoff the sixteen behavioral contracts grade — a typed artifact schema, not a form. The five retro types are event-trigger taxonomies (task, session, cross-task, round, upgrade), each bound to a real loop event; the upgrade retro is live every CLI pin bump. Residual trim rides LEARN-002, which already owns paid runs on this file |
| self-improve-loop `SKILL.md:209-217` + `discovery-routing.md:98-109` — 8–10-field candidate block | **Flip to keep** | The quarantine boundary's wire format: Evidence/Scope/Provenance/Owner are what make a lesson evidence-bound rather than remembered, and the state↔disposition matrix is CLI-owned (`STATE_DISPOSITIONS`) with the mirrors declared as drift to fix toward the ledger. Contract-graded — any change owes a paired behavioral run, which LEARN-002 carries |
| self-improve-loop `research-basis.md` — standing recheck burden | Drop stands | A dated evidence record with freshness stamps and an explicit not-an-instruction-feed rule — the evidence-quarantine pattern applied to the skill's own design rationale. The recheck burden is the maintenance cost the `[sourced]` tier owes, not ceremony; the file is on-demand, never always-loaded |
| prompt-craft — zero findings | Confirmed | See the gaps section: its references are the program taught as method |

## Gaps (the direction the original scan could not see)

None found, and — as in Group 3 — the record should say why: this group's unflagged files are where
the program is taught as method, so the missing-mechanism hunt kept finding mechanisms already
present. Representative, none previously flagged: `context.md`'s "the worker's return message is
the entire interface" and durable-state-lives-in-files (the handoff and loop strands as working
rules); `agent-security.md`'s "delegation is not isolation — the subagent gets its own context
window, not its own trust domain" (graph engineering's composite-authority rule, with the trifecta
evaluated across the handoff); `tools.md`'s "the tool list is the mandate" (authority as declared
edges, prose loses at runtime); the frontmatter reference's "a grant that looks like a limit and
isn't" (enforcement honesty — the same rule the validator applies to parenthesized specifiers);
the plan file's "Parked suspicions — never shown to the reviewer" (evaluator independence held as
an artifact slot, not a memory) and its "Safe resume point — a successor starts here, never by
reconstructing the conversation" (handoff completeness, stated as the slot's own rule); the
altitude references' "a spawned agent never self-promotes, it reports the fork to its caller" (no
edge widens itself); and `cli_skeleton.py`'s injected-spy dry-run test (prove-the-instrument,
runnable). The meta group was not merely consistent with the program — it is where most of the
program's mechanisms were first written down.

## Disposition summary

Ten flips join the KEEP consensus (KEEP 17 in the
[scan record](prop-002-scan-findings-2026-08-13.md)); one finding upheld (`eng-ladder` Mode 3 —
the only finding in all four groups whose original severity survives the program lens, parked as a
measured trim candidate on LADDER-001's paired capture); four drops standing with reasons
upgraded; two prior overturns confirmed. Zero edits — every candidate edit sits under a named
freeze (LADDER-001, LEARN-002, sre-tool's measured edit-sensitivity), so this record's re-verdicts
are the deliverable, and the freezes' owning items carry the two live ride-alongs. With this
record the PROP-002 batch drop is fully superseded: **all four groups now carry individual
rescan dispositions**, and no finding remains under the original one-human lens.
