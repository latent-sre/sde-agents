---
name: backend-craft
description: Use when building or changing an API or backend service — HTTP endpoints, workers, schedulers, integrations, or the service behind a UI — from a single endpoint to a full service. Covers stack choice, contract design, resiliency, data handling, and operability.
argument-hint: [the API or service to build or change]
---

# Backend craft

**You write the actual code.** Complete, runnable files — routes, models, config, tests — never pseudo-code, never architecture-only answers. Make the decision, state it in one line, build it.

## Stack

An existing repo's stack always wins — match it. Greenfield, pick by the project and say why in one line:

- **Python + FastAPI** (default): typed Pydantic models, OpenAPI generated for free — which feeds the contract-first flow — async-capable, ideal for ops tools and home-lab services.
- **Go**: when a single static binary, tiny container, or high concurrency is the point.
- **Node + TypeScript** (Fastify/Hono): when sharing types end-to-end with a React frontend is the dominant concern.

## Contract first

- The API contract (OpenAPI or equivalent) is written/generated before the frontend consumes anything; it is the single source of truth for shapes.
- **One error shape everywhere** (problem+json style: status, code, human message, details) — a client should never parse two error formats.
- `/v1` in the path from day one; breaking changes mean a new version, not a mutation.
- Every list endpoint paginates from the start — retrofitting pagination is a breaking change.

## Resiliency (the core focus)

- **Timeouts on every outbound call** — HTTP, DB, queue — no exceptions. An unset timeout is an unbounded outage.
- **Retries with backoff + jitter, only on idempotent operations**; a retry storm is self-inflicted DDoS.
- **Fail fast on persistent dependency failure** and define degradation per dependency: what still works when the DB / upstream API / cache is down, decided deliberately.
- **Idempotency**: mutating endpoints are safe to retry — naturally idempotent or via idempotency keys.
- **Validate at the boundary** (Pydantic / zod / validator): reject bad input early with a clear error. Your own frontend is still an untrusted caller.
- Transactions wherever an invariant spans more than one write; no shared mutable state without protection.

## Operability

- Structured logs with a request ID on every entry — one request must be traceable end to end.
- `/healthz` (process up) and `/readyz` (dependencies reachable) — distinct, because they answer different questions.
- RED metrics (rate, errors, duration) on the request path.
- Config from environment, validated at startup — fail fast and loud on bad config, never limp.
- Graceful shutdown: stop accepting, drain in-flight, then exit.

## Data and security

- Migrations versioned and reversible (expand → migrate → contract); parameterized queries only.
- Secrets from env or a secret store — never in code, images, or logs.
- Authn/z on every non-public route; explicit CORS; rate limiting on anything exposed.

## Quality gate

Before "done": the service starts clean, tests pass, and the primary endpoints were exercised with real requests (curl/httpie) — request and response pasted in the review packet. An API that was never called is written, not verified.
