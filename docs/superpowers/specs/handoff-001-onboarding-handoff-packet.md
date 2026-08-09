# HANDOFF-001 spec — evidence-bound onboarding handoff packet

**Status: approved** — drafted 2026-08-03; approved by the operator 2026-08-09 ("we need it —
it has been burning us"), sequencing unchanged. Implements issue #60.
**Sequenced after REV-001**: the packet reuses whatever envelope/matrix idiom that round settles
plus the existing Learning-packet pattern — the fleet does not grow a third packet dialect.

## Problem

Verified POC constraints were lost across the POC→builder handoff **three times** in one
onboarding (`server -verify-only` reintroduced; `disable_mlock` reintroduced *with a regression
test requiring the wrong field*; a role-enrollment relationship asserted by string co-occurrence
rather than parsed). Live gates caught what source gates passed. Onboarding also fanned out into
every lifecycle lane before the first requested Tier-1 artifact. Issue #60's closeout comments
supply the complete field-derived section list below.

## Scope

One packet template in canonical source, owned by `sde-agents:homelab-platform` (it owns scope
and authority), emitted before delegating implementation, echoed back by the builder before work
starts. Sections, all field-derived:

1. Task identity and the bounded deliverable.
2. Fixed operator decisions.
3. Exact authoritative sources available in context.
4. Verified facts and environment constraints.
5. **Known failed assumptions / forbidden regressions** — the builder and its tests must reject
   reintroductions; acceptance checks parse relationships and postconditions, never string
   co-occurrence alone.
6. Acceptance criteria including failure paths, each with **verification-method validity**:
   execution class (Tier-0 read-only / check-mode simulation / live mutation), whether the
   command actually supports that mode, what output constitutes evidence, known false-positive
   and false-negative behavior, and the fallback probe when simulation cannot exercise the check.
7. Authority boundary and **executable-transport contract**: the host-native broker/mediator
   entry point is identified before Tier-2 execution is offered; request-generated, approved,
   consumed-exactly-once, and effect-verified are distinct states.
8. Irreversible actions with observable postconditions and ambiguous-response recovery
   (reconcile state before a rollback can destroy the proven replacement).
9. Temporary-authority envelope: acquisition point, maximum lifetime, guaranteed cleanup boundary.
10. Inventory-derived invariants that must change with the onboarding (counts, thresholds,
    generated-source parity).
11. Blocking prerequisites; non-blocking lanes with owners (explicit gates, never silently
    dropped); explicit out-of-scope.
12. Secret-safe capture: the packet carries field-scoped projections only; resolved secret
    material never enters it (rule now stated in `homelab-platform` Tier 0 and
    `service-onboard`).

## Acceptance

- [ ] Issue #60's paired evals under identical conditions: the known-failed-assumption fixture no
      longer regresses; staged-artifact-with-live-blockers stays safe; first-artifact latency
      improves with no missed gates; proportionality holds on a simple service; the adverse
      authority case names the approval gate.
- [ ] Added fixtures from the closeouts: check-mode-skipped-probe (dry run not treated as
      evidence), constraint-reintroduction rejection by builder *and* reviewer, vaulted-variables
      discovery (only non-secret fields enter the packet).
- [ ] Adapters regenerated with parity green; validator and tests green; documentation states
      when the packet is required and when it is ceremony.
- [ ] Issue #60 updated with measured baseline/candidate evidence.

## Non-goals

Removing lifecycle checks from `service-onboard`/`host-onboard`; new deployment authority;
OpenBao-specific behavior in a general skill; treating a faster first artifact as completion.

## Rollback

Template plus prompt-level wiring in canonical files, regenerated adapters — one revert commit.
