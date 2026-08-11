# HANDOFF-001 plan — execution payloads for the approved spec

Paired with the approved
[`HANDOFF-001 spec`](../specs/handoff-001-onboarding-handoff-packet.md); operational only while
this round is active. The spec delegated the packet's exact shape to implementation; this plan
records how the twelve spec sections became thirteen graded slots, and settles the sequencing
clause against the REV-001 idiom that has since landed.

## The idiom ruling (the spec's sequencing clause, resolved)

The spec sequenced this round after REV-001 so "the fleet does not grow a third packet dialect."
REV-001 has settled, and what it settled is a **field vocabulary**, not a packet dialect: the
approval envelope binds a verdict to immutable identity through named snake_case fields
(`candidate_sha`, `base_sha`, `tree_oid`) carried in the reviewer's and verifier's prose. The
handoff packet is the other kind of artifact — a labeled-line prose packet, the same dialect as
the fleet's existing Learning packet, graded by a `scripts/packet_lint.py` shape
(`handoff-packet`). Two artifacts, one packet dialect, one field vocabulary: the "no third
dialect" constraint holds because the packet reuses the labeled-line pattern rather than minting
a new one, and where a packet line names an immutable revision it uses REV-001's field names
rather than a synonym. Operator approval of this plan records that reconciliation; if a later
round replaces the labeled-line dialect wholesale, this packet is one of the files that migrates.

## Payloads

1. **`agents/homelab-platform.md` — the packet, thirteen slots, end of file.** The spec's twelve
   sections map without loss: §1 → `Deliverable:`; §2 → `Fixed decisions:`; §3 → `Sources:`;
   §4 → `Verified facts:` (each fact carries the probe that measured it); §5 → `Forbidden
   regressions:` (binding tests as well as code — the field failure was a regression test that
   *required* the disproved form); §6 folds verification-method validity into `Acceptance:`
   rather than a standalone slot, so a criterion and its evidence contract cannot drift apart;
   §7 → `Authority:` with the four transport states kept distinct; §8 → `Irreversible:`;
   §9 → `Temporary authority:`; §10 → `Inventory invariants:`; §11 splits into `Blocking:`,
   `Open lanes:` (each with an owner), and `Out of scope:` — deferral and abandonment must not
   share a line; §12 is the secret-safe capture rule, held as a packet rule rather than a slot
   because it governs every line. End-of-file placement is load-bearing: the validator's
   Learning-closeout window opens at the **first** `## …packet` heading and closes at the next
   `##` heading, so an earlier position pushes the Learning slot outside that window and fails
   the fleet gate loudly (`agents/homelab-platform.md: end-of-task packet omits or drifted from
   the canonical intake-only Learning closeout…`). End of file is the position that passes.
2. **`agents/sde-fullstack.md` — the builder echo.** Before the first edit the builder restates
   `Deliverable`, `Fixed decisions`, `Forbidden regressions`, and `Blocking` in its own words.
   On hosts with no per-agent tool authority the echo is the only evidence the caller gets that
   the constraints arrived; a packet claim the builder finds false goes back as a correction
   with evidence, never a silent override.
3. **`skills/service-onboard` / `skills/host-onboard` — lanes are acceptance criteria, not a
   queue.** A bounded request gets its blocking discovery and the first artifact; every unworked
   step travels as `Blocking:` or `Open lanes:` with an owner. No check removed (spec non-goal).
4. **Proportionality predicate, stated in the packet section.** The full packet is owed when the
   delegation crosses a context boundary *and* carries a verified fact contradicting a plausible
   default, a live effect, an irreversible or custody action, temporary authority, or lanes that
   would otherwise read as finished. Below that bar, three sentences (deliverable, acceptance,
   authority) — ceremony where it buys nothing trains the reader to skim the packet that matters.
5. **`scripts/packet_lint.py` `handoff-packet` shape + `scripts/validate_fleet.py` pin.** The
   lint shape grades the slots deterministically; the validator rule pins the canonical slot list
   to the shape so they cannot drift apart while the grader keeps passing. Both mutation-proven
   (slot renamed, shape entry dropped, section deleted — each fails distinctly).
6. **Nine `handoff-001` behavioral contracts.** The issue's five evals plus
   check-mode-is-not-evidence, secret-safe capture, the builder echo, and reviewer rejection of a
   constraint encoded in a test. Graders are positives-first; negation-aware `must_not_match`
   patterns were written and rejected because each false-fired on the correct answer — the fourth
   recurrence of that grader class in this suite.

## Verification payloads

Deterministic gates plus adapter parity ran offline. The nine contracts join the live docket
paired against pre-change bytes under identical conditions; the spec's Evals 3 and 4 additionally
owe their turns-and-tokens measurement, which no offline grader substitutes for. Closure follows
issue #60's own condition: delivered, released, and the closeout fixtures passing on the released
artifact — a green offline suite is not that evidence.

## Rollback

Prompt-level packet section plus two skill paragraphs, one lint shape, one validator rule, nine
contracts, regenerated adapters — one revert commit. Records already written against the packet
(an emitted handoff in a session log) are evidence about the session that wrote them and need no
migration.
