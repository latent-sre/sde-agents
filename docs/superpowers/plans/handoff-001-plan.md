# HANDOFF-001 plan — Claude manager-owned work order

Paired with the approved
[`HANDOFF-001 spec`](../specs/handoff-001-onboarding-handoff-packet.md); operational only while
this round is active. The operator approved this amendment on 2026-08-11 after the first
implementation's Terra evidence showed that repeating the entire packet consumed context while
lexical assertions obscured otherwise-correct behavior.

## Frozen baseline and success

Baseline `4777df9cc97b5a855c2c7ba693ce990e4d6ee1c2` has no onboarding producer or consumer. The
first lean candidate proved the producer repeatably, but only 1/6 strict cases passed in the final
Terra pair. Those artifacts remain valid historical evidence for their exact prompts, evaluator,
and Codex runtime; they are not mixed with this amended Claude case set.

This round succeeds when:

- `homelab-platform` returns one complete `Work Order v1` block to the main coordinator;
- the coordinator preserves exact LF-normalized UTF-8 bytes, computes SHA-256, and supplies the
  unchanged block and digest to `sde-fullstack`;
- the builder recomputes SHA-256 over those same normalized bytes before accepting the order;
- a complete, matching, conflict-free order receives only the three-line accepted receipt before
  work;
- a missing or conflicting field or mismatched digest receives an input-required receipt naming
  the field, with no edit or reconstruction; an explicit `none` remains complete when no claim
  needs a source;
- the builder's key constraint transfer is graded from a declarative scratch repository by a
  trusted, unchanged acceptance program rather than inferred from response prose;
- the simple-build exception and first-artifact/open-lane behavior remain proportional; and
- generated adapters, T0, affected tests, T1, and `claude plugin validate . --strict` are green on
  the exact candidate bytes.

## Work-order ownership

`agents/homelab-platform.md` owns the trigger, identity header, six field labels, field semantics,
capture safety, authority boundary, and short-form exception. It has no `Agent` tool and returns
the work order to its caller rather than attempting nested delegation.

The main Claude coordinator owns transport identity. It normalizes the returned block to LF with
one final newline, hashes those exact UTF-8 bytes, and gives the builder both the unchanged block
and `Work-order digest: sha256:<digest>`. This is a manager instruction, not new deployment
authority or a global runtime.

`agents/sde-fullstack.md` owns only the receipt and consumption behavior. It does not repeat the
work order. It recomputes the digest from the normalized block before accepting. An accepted
receipt contains status, exact ID, and exact digest. An input-required receipt contains status,
available identity, conflicting field labels, and one recommended resolution. Existing
material-fork, code-and-test regression, parsed-relationship, check-mode, secret, and Tier-2/3
rules remain authoritative.

No `packet_lint` shape, fleet-validator rule, global hook, agent-local hook, typed workflow runtime,
or new configuration surface is added. GRAPH-004 remains the separate trigger-bound typed-edge
decision; HANDOFF-001 does not implement it by stealth.

## Six focused cases

The case inventory stays at six while removing the non-consumer reviewer duplicate:

1. producer preserves the three observed failed assumptions and replacement controls;
2. discovery rejects skipped check-mode evidence and carries only secret-safe projections;
3. the requested Tier-1 artifact appears first while blockers and lane owners remain explicit;
4. a simple stateless service stays on the short path with real acceptance and authority;
5. the builder consumes one digest-bound work order, edits the declarative fixture, passes the
   trusted verifier, and returns the accepted receipt; and
6. the builder rejects a mismatched digest before editing while accepting explicit `none` in a
   source-free field.

Case 5 reuses the behavioral evaluator's existing `semantic_oracle` seam. The evaluator seeds
three JSON artifacts plus one trusted acceptance program in its disposable scratch directory. It
refuses a changed verifier, rejects links/reparse points through the existing provenance reader,
bounds artifact size, runs only the unchanged verifier under isolated Python, and persists the
verifier result plus artifact hashes. It never executes model-authored Python as grader code.

The ordinary code-reviewer contract remains covered elsewhere. Removing its HANDOFF-tagged case
does not change the reviewer prompt or authority; it removes a second paid wording check for a role
that does not produce or consume this work order.

## Verification and paid boundary

Offline work runs the exact-byte digest controls, functional red/green fixture, verifier-tamper
failure, session-to-oracle integration, benchmark evidence serialization, adapter generation, T0,
the affected module, T1, and strict plugin validation. No model session is part of implementation.

The previous `--runtime codex --case 'handoff-*'` command no longer describes this suite: the
functional builder case intentionally grants `Bash` and `Write` in a disposable Claude session.
The digest-mismatch case grants only `Bash` for the required hash calculation and denies every
write tool. The bounded Codex projection refuses both before spend. Existing Terra artifacts
remain archived; do not rerun or reinterpret them as Claude evidence.

Any live Claude measurement needs separate operator approval after the candidate freezes. The
smallest diagnostic is three candidate-only sessions: producer, functional builder, and
digest-mismatch receipt, one run each. Only if those responses and end-state evidence are sound
should a paired baseline/candidate capture be proposed. Runtime, CLI, exact model, timeout, case
bytes, evaluator bytes, plugin identities, isolation, and concurrency must be identical within
that pair.

## Rollback

Revert the producer/consumer prompt commit and regenerate adapters; revert the functional
case/evaluator commit to restore the prior six no-tool HANDOFF cases. Existing tier, capture,
effect-broker, and reviewer controls remain untouched.
