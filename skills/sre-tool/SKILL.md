---
name: sre-tool
description: Use when building a new operator-facing or SRE tool — a dashboard, CLI, automation service, monitor, or internal web tool — or substantially changing one, when the work is big enough to run the full engineering ladder from requirements through review. For a focused change to one layer, use backend-craft or frontend-craft.
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
- **Success criterion**: the **mission transaction** — the one real-world exchange that proves the tool does its job (for a TLS proxy: a real HTTPS request to a managed route returns the backend). Boot, build-clean, and container-healthy are table stakes, never the criterion.
- **Environment card**: before spawning any builder, ensure the repository's project context records what every agent needs — toolchain paths, ports, run/test commands, module identity (from `git remote -v`), where credentials live, and the progress-file path (portable defaults: `AGENTS.md` and `.agents/PROGRESS.md`; respect an existing equivalent such as `CLAUDE.md`). Builders read it there; spawn prompts stay small and consistent. The card also carries the **mission block**: the tool's purpose, the mission transaction, the threat model, and what the verification pipeline can and cannot see — builders, reviewers, and every future maintenance session read the mission there.
- **Cadence contract**: in the same question round, settle commit policy (e.g. "commit at every green batch boundary"), pause points, and which gates need the user's eyes (default: design approval and deploy artifacts). Anything not named a gate runs without a check-in; without an explicit grant, never commit. Write the settled contract into the plan file immediately — conversation memory does not survive compaction. A waiting gate blocks only its own scope; independent non-gated work continues.

## Phase 1 — Right-size the design

Routing rubric lives in the `eng-ladder` skill — that table is the source of truth.

- Single component, low blast radius → design inline at SDE level: a few sentences of plan plus stated assumptions. No ceremony.
- Multiple services, a data migration, or hard-to-reverse choices → spawn the `principal-engineer` agent for a short design doc; surface any one-way doors to the user before proceeding.
- Platform-shaping work (many teams or systems, multi-year consequences) → spawn `distinguished-architect` first.

For a **multi-component project** (e.g. a web UI plus its backend API), the design must include the interface contract as a **repo artifact with concrete example payloads** — endpoints, request/response JSON, error cases. It cannot be skipped, and it is **living**: a builder whose implementation diverges updates it in the same change, and parallel builders cite the artifact — never each other's code. During a parallel batch the contract has **one named owner**; every other builder is read-only on it and routes change requests through the orchestrator, contract changes are a required review-packet slot, and the orchestrator propagates them to every affected builder at once.

The design's build order is a **dependency graph, not a sequence**: serialize only what genuinely blocks — walking skeleton, then the safety core — and group every independent slice into parallel batches by file ownership. A numbered slice list where each item waits on the previous is a planning bug unless the dependencies are real.

If the tool has a web UI, a static mockup (artifact, key screens, light + dark) gets user approval **before any framework code** — the approved mockup is the visual spec and a named gate in the cadence contract.

Agents do not inherit this conversation. Pass each one full context: the Phase 0 requirements, repo layout and conventions, and constraints.

## Phase 2 — Build

Spawn `sde-fullstack` with the requirements, the design, exact repo paths and conventions, and the success criterion. Every spawn prompt states a **checkpoint contract**: the boundary to run to, the acceptance criteria the builder self-verifies against, and the leash — reversible decisions are the builder's to make and log, and it returns only at the boundary or on a material fork. For trivial scope, implement directly while holding to the same SRE-lens standards (observability, timeouts, idempotency, dry-run for destructive actions).

For multi-component projects: **walking skeleton first** (the thinnest end-to-end slice running against the real contract), fully verified — it proves the contract. Then **triage by blast radius**: safety-critical components (anything that can corrupt production state) keep per-slice verification and review-as-gate; everything else builds in **batches**, verified once at the batch boundary. After the skeleton, launch each batch's builders **in one message** so they run concurrently — one `sde-fullstack` per component with **disjoint file ownership**, each citing the contract artifact and told to invoke the `frontend-craft` or `backend-craft` skill for its half (`sde-fullstack` holds the `Skill` tool, so spawned builders invoke skills themselves — name the skill, don't hand them a SKILL.md path to `Read`). Mechanical scope (scaffolding, boilerplate, packaging, docs) may run on a faster model (spawn-time model override; sonnet by default); safety-critical code and all reviews stay at full effort. Prefer messaging a running builder with scope changes over killing and relaunching; if one is stopped early, inventory its partial writes and have the successor verify-and-finish rather than redo.

Accept a builder's review packet on its evidence (fresh command + output): re-run declared safety proofs and one spot-check per batch, never the whole verification. Answer status questions from the progress file declared in the project context (portable default: `.agents/PROGRESS.md`) — never interrupt a running builder to ask.

Failure path: a packet that returns short of its checkpoint contract gets one relaunch with the gap named; a second miss escalates to the user. Fix→re-review cycles cap at two rounds — a third means the diagnosis is wrong; switch to root-cause. Files a reviewer skipped as mid-edit are queued for the next review, never dropped. When routing a review fix on **safety-core** code, hand the builder the defect and the acceptance test the fix must satisfy — **not the implementation**. A fix you dictate is only as good as your own untested reasoning, and it collapses the builder into a typist whose verification is no longer independent of yours. Dictate only genuinely mechanical fixes.

For builds with three or more parallel batches, offer the user workflow orchestration (their opt-in) — it removes the orchestrator as the serial hop between build finishing and review starting.

## Phase 3 — Review

Spawn `code-reviewer` with the mission and **threat model** (from the environment card), the **contract artifact** (served shapes are checked against it), and focus files seeded from the builders' "Check first" packet entries. **Seed the gate with those and nothing more — never your diagnosis or your fix.** If you already suspect a specific defect, record it in the plan file and let the reviewer report independently first, then reconcile: a reviewer handed your hypothesis can only confirm it, and you will not be able to tell a discovering gate from an echoing one. Read the reviewer's independent P0/P1 count — a gate that returns zero independent findings has not been exercised, and your own suspicions were the only net. Reviews are read-only — run them **concurrently with the next build phase** unless that phase builds on the reviewed code; only safety-critical code treats review as a gate. Route P0/P1 fixes to whichever builder owns the files; report P2/P3 to the user rather than silently applying. For anything network-exposed or auth-bearing, add a security review before deploy artifacts ship. **The gate keys on the file, not the size of the diff**: any later edit to a safety-critical file — including a one-line "nit" the orchestrator is tempted to apply directly — re-enters review before it ships. "Too small to review" is how an unreviewed change lands in exactly the code the gate exists to protect.

## Phase 4 — Verify and hand over

**Clean baseline first.** Before the first mission-transaction apply, assert that no stale process the pipeline — or an earlier detour — spawned is still bound to the target's ports, and that the target admin API answers. A stale process serving a *previous* config can return a green that proves nothing — more dangerous than the failed apply it might instead cause. Any process the pipeline launches is the pipeline's to tear down at hand-over.

Run the tool and execute the **mission transaction from the environment card, verbatim** — not just the test suite, and not a substitute flow that happens to work. Deploy/install docs are runbooks: every command executed as written or labeled `unverified`. Final report: what was built, how to run it, what was verified end to end, the review verdict, and known gaps.

## Phase 5 — Deploy and onboard

If the tool lands on the lab, hand off to `homelab-platform` with the `service-onboard` checklist and the tool's runbook as acceptance criteria — built-but-never-onboarded is not done. Name this gate in the Phase 0 cadence contract.
