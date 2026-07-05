---
name: sre-tool
description: Use when starting a new operator-facing or SRE tool — a dashboard, CLI, automation service, monitor, or internal web tool — or adding a major capability to one, and the work should run the full engineering ladder from requirements through review.
argument-hint: [what the tool should do]
---

Announce at start: "Running the sre-tool pipeline: requirements → right-sized design → build → review → verify."

## Phase 0 — Requirements (don't skip)

Establish before designing. Infer from context and the codebase where possible; ask the user only what genuinely can't be inferred, batched into one question round:

- **Operator and moment**: who uses this, and when — during an incident (optimize for speed and zero ambiguity) or routine work (optimize for automation)?
- **Inputs, outputs, systems touched** — and whether the tool is read-only or mutating.
- **Placement**: where it runs and deploys — host, container, VM — and which network boundaries it crosses to reach the systems it touches. Placement flips architectures; pin it before design.
- **Blast radius** if the tool itself misbehaves; auth and audit needs.
- **Interface**: CLI, TUI, or web — the thinnest one that serves the operator, not the most impressive one.
- **Success criterion**: the observable behavior that proves it works.
- **Environment card**: before spawning any builder, ensure the repo's CLAUDE.md records what every agent needs — toolchain paths, ports, run/test commands, module identity (from `git remote -v`), where credentials live. Builders read it there; spawn prompts stay small and consistent.
- **Cadence contract**: in the same question round, settle commit policy (e.g. "commit at every green batch boundary"), pause points, and which gates need the user's eyes (default: design approval and deploy artifacts). Anything not named a gate runs without a check-in; without an explicit grant, never commit.

## Phase 1 — Right-size the design

Routing rubric lives in the `eng-ladder` skill — that table is the source of truth.

- Single component, low blast radius → design inline at SDE level: a few sentences of plan plus stated assumptions. No ceremony.
- Multiple services, a data migration, or hard-to-reverse choices → spawn the `principal-engineer` agent for a short design doc; surface any one-way doors to the user before proceeding.
- Platform-shaping work (many teams or systems, multi-year consequences) → spawn `distinguished-architect` first.

For a **multi-component project** (e.g. a web UI plus its backend API), the design must include the interface contract as a **repo artifact with concrete example payloads** — endpoints, request/response JSON, error cases. It cannot be skipped, and it is **living**: a builder whose implementation diverges updates it in the same change, and parallel builders cite the artifact — never each other's code.

The design's build order is a **dependency graph, not a sequence**: serialize only what genuinely blocks — walking skeleton, then the safety core — and group every independent slice into parallel batches by file ownership. A numbered slice list where each item waits on the previous is a planning bug unless the dependencies are real.

If the tool has a web UI, a static mockup (artifact, key screens, light + dark) gets user approval **before any framework code** — the approved mockup is the visual spec and a named gate in the cadence contract.

Agents do not inherit this conversation. Pass each one full context: the Phase 0 requirements, repo layout and conventions, and constraints.

## Phase 2 — Build

Spawn `sde-fullstack` with the requirements, the design, exact repo paths and conventions, and the success criterion. Every spawn prompt states a **checkpoint contract**: the boundary to run to, the acceptance criteria the builder self-verifies against, and the leash — reversible decisions are the builder's to make and log, and it returns only at the boundary or on a material fork. For trivial scope, implement directly while holding to the same SRE-lens standards (observability, timeouts, idempotency, dry-run for destructive actions).

For multi-component projects: **walking skeleton first** (the thinnest end-to-end slice running against the real contract), fully verified — it proves the contract. Then **triage by blast radius**: safety-critical components (anything that can corrupt production state) keep per-slice verification and review-as-gate; everything else builds in **batches**, verified once at the batch boundary. After the skeleton, launch each batch's builders **in one message** so they run concurrently — one `sde-fullstack` per component with **disjoint file ownership**, each citing the contract artifact and pointed at `frontend-craft`/`backend-craft` for its half. Mechanical scope (scaffolding, boilerplate, packaging, docs) may run on a faster model; safety-critical code and all reviews stay at full effort. Prefer messaging a running builder with scope changes over killing and relaunching; if one is stopped early, inventory its partial writes and have the successor verify-and-finish rather than redo.

Accept a builder's review packet on its evidence (fresh command + output): re-run declared safety proofs and one spot-check per batch, never the whole verification. Answer status questions from `.claude/PROGRESS.md` — never interrupt a running builder to ask.

For builds with three or more parallel batches, offer the user workflow orchestration (their opt-in) — it removes the orchestrator as the serial hop between build finishing and review starting.

## Phase 3 — Review

Spawn `code-reviewer` with a **threat model** (what a P0 means for *this* tool) and named focus files. Reviews are read-only — run them **concurrently with the next build phase** unless that phase builds on the reviewed code; only safety-critical code treats review as a gate. Route P0/P1 fixes to whichever builder owns the files; report P2/P3 to the user rather than silently applying. For anything network-exposed or auth-bearing, add a security review before deploy artifacts ship.

## Phase 4 — Verify and hand over

Run the tool and exercise its primary flow for real — not just the test suite. Final report: what was built, how to run it, what was verified end to end, the review verdict, and known gaps.
