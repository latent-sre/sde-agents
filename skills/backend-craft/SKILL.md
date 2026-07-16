---
name: backend-craft
description: Failure-first backend engineering rules — contracts, resiliency, operability, security, testing. Use when building or changing an API or backend service — HTTP endpoints, workers, schedulers, or the service behind a UI — and when consuming or integrating third-party APIs (clients, SDK wrappers, sync jobs, webhooks). For the UI layer, use sde-agents:frontend-craft; for a full multi-file feature with tests, use sde-agents:sde-fullstack.
argument-hint: [the API or service to build or change]
---

# Backend craft

**You write the actual code.** Complete, runnable files — routes, models, config, tests — never pseudo-code, never architecture-only answers. Make the decision, state it in one line, build it. Exception — a material fork (the answer changes what gets built: data model, auth, API surface) that can't be inferred goes back as one batched question round with recommended defaults *before* building; a materially better alternative to the requested approach gets one recommendation line with the trade-off, then build what was chosen — never silently substitute.

This skill is general-purpose — any backend or API, not just ops tooling — held to an SRE-grade bar: failure-first, observable, safe to operate. The examples lean ops/home-lab; the rules are domain-neutral.

## Contract first

- The API contract (OpenAPI or equivalent) is written/generated before the frontend consumes anything; it is the single source of truth for shapes — and it is **living**: if your implementation diverges, update the contract in the same change. A stale contract is worse than none; parallel builders trust it.
- **One error shape everywhere** (problem+json style) — a client should never parse two error formats. The shape, worked:

  ```json
  { "error": { "status": 504, "code": "upstream_timeout",
               "message": "Grafana did not respond within 5s.",
               "details": [], "request_id": "req_8f3a2c" } }
  ```

  Same envelope for validation errors (each field issue as a `details` entry), 404s, and 500s — and `request_id` in every one, so a user-reported error is greppable in the logs.
- **Serialize through explicit response models** — never return ORM objects or internal dicts directly. A response model is an allowlist: anything not declared in it (password hash, internal flag) *cannot* leak.
- `/v1` in the path from day one; breaking changes mean a new version, not a mutation.
- Every list endpoint paginates from the start — cursor-based by default (offset is fine for small, bounded admin lists); retrofitting pagination is a breaking change.

## Resiliency (the core focus)

- **Timeouts on every outbound call** — HTTP, DB, queue — no exceptions. An unset timeout is an unbounded outage.
- **Retries with backoff + jitter, only on idempotent operations**; a retry storm is self-inflicted DDoS.
- **Fail fast on persistent dependency failure** and define degradation per dependency: what still works when the DB / upstream API / cache is down, decided deliberately.
- **Idempotency**: mutating endpoints are safe to retry — naturally idempotent or via idempotency keys.
- **Validate at the boundary** (Pydantic / zod / validator): reject bad input early with a clear error. Your own frontend is still an untrusted caller.
- Guard shared mutable state and concurrent access; make every write safe under retry (transaction boundaries live in `references/persistence.md`).

These are the system-wide principles. The client-side mechanics for *calling other services* — retry policy, breakers, token refresh — live in `references/consuming-apis.md`; don't restate them ad hoc.

## Operability

- Structured logs with a request ID on every entry — one request must be traceable end to end.
- `/healthz` (process up) and `/readyz` (dependencies reachable) — distinct, because they answer different questions.
- RED metrics (rate, errors, duration) on the request path.
- Config from environment, validated at startup — fail fast and loud on bad config, never limp.
- Graceful shutdown: stop accepting, drain in-flight requests, finish or re-queue the running job, stop the scheduler, close live streams — then exit.

## Security

- Secrets from env or a secret store — never in code, images, or logs.
- Explicit CORS allowlist (never `*` with credentials); rate limiting on anything exposed (token bucket, return `Retry-After`).
- **Bound what you accept**: request-body size caps, server-side request timeouts, and bounded query params (max page size, max array length). Inbound requests can do unbounded damage exactly like unbounded outbound calls — input *validation* itself lives under Resiliency.

## Testing & quality gate

- **Unit** the pure logic; **integration-test** the handlers against a **real ephemeral database** (testcontainers or a throwaway Postgres — not mocks of your own DB).
- **Mock the upstreams** you consume (respx / WireMock) and **test the failure paths that matter**: a timeout fires, a retry backs off, the circuit breaker opens. Resiliency code is worthless untested.
- **Contract-test** against the OpenAPI spec so served shapes can't drift from what the frontend builds on.
- Before "done": the service starts clean, tests pass, and the primary endpoints were exercised with **real requests** (curl/httpie) — request and response pasted in the review packet. An API that was never called is written, not verified.

The **review packet** is the end-of-task report defined by the calling agent (`sde-agents:sde-fullstack`, which preloads this skill). Invoked standalone with no packet convention in context, end with: Changed / Assumptions / Verified / Not verified.

## Before you write it — load the reference for what you're building

Everything above applies to every backend task. The rules below apply only when the task involves the
thing named. Read the file **before** writing that code, not after — and name what you read in your
review packet.

| If the task involves… | Read first |
|---|---|
| choosing a stack for a greenfield service | `references/stack.md` |
| calling any upstream or third-party API | `references/consuming-apis.md` |
| a queue, a scheduled job, or an inbound webhook | `references/background-work.md` |
| streaming to clients (SSE or WebSocket) | `references/live-data.md` |
| a database or any persisted state | `references/persistence.md` |
| authenticating or authorizing a caller | `references/auth.md` |

Trips two predicates? Read both. Trips none? The core above is the whole job.
