---
name: backend-craft
description: Use when building or changing an API or backend service — HTTP endpoints, workers, schedulers, integrations, or the service behind a UI — from a single endpoint to a full service. Covers stack choice, contract design, resiliency, data handling, and operability.
argument-hint: [the API or service to build or change]
---

# Backend craft

**You write the actual code.** Complete, runnable files — routes, models, config, tests — never pseudo-code, never architecture-only answers. Make the decision, state it in one line, build it. Exception — a material fork (the answer changes what gets built: data model, auth, API surface) that can't be inferred is worth one batched question round with recommended defaults *before* building; a wrong build costs a full rebuild-and-review cycle, a question costs seconds. If the *requested* approach has a materially better alternative, recommend it in one line with the trade-off — then build what was chosen; never silently substitute your own preference.

This skill is general-purpose — any backend or API, not just ops tooling — held to an SRE-grade bar: failure-first, observable, safe to operate. The examples lean ops/home-lab; the rules are domain-neutral.

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
- Guard shared mutable state and concurrent access; make every write safe under retry (transaction boundaries live under Persistence).

## Consuming APIs (integration discipline)

Much of this service's job is calling *other* APIs — take being a good client as seriously as being a good server.

- **One typed client per upstream**, configured once — base URL, auth, timeout, retry policy in a single place; never scatter ad-hoc calls (a shared `httpx.AsyncClient`, not a new session per call).
- **Auth to upstreams**: API key / bearer / OAuth2 client-credentials — **cache the token and refresh before expiry**, never re-auth per call.
- **Respect their limits**: honor `429` + `Retry-After`, self-throttle to their quota, backoff + jitter on retryable failures. Never be the reason an upstream rate-limits you.
- **Circuit breaker per upstream**: after N consecutive failures, open the circuit and fail fast instead of hammering a down dependency; half-open to probe recovery. Retries alone don't give you this.
- **Consume pagination fully**: follow cursor / next-links to completion, bounded — never assume one page.
- **Upstream responses are untrusted**: parse into *your own* models, tolerate schema drift (ignore unknown fields, fail loudly only on a missing critical one), and never leak a raw upstream error to your caller — translate it into your one error shape.
- **Cache upstream data** with a TTL (stale-while-revalidate) — fewer calls, and you ride out upstream blips.
- **Idempotency for side-effecting calls** — an idempotency key or dedup so a retry doesn't double-submit.
- **Observe every upstream call**: log target, latency, status, correlation ID; RED metrics per upstream; reflect a hard-down critical dependency in `/readyz`.

## Background work & scheduling

- **In-process** (FastAPI BackgroundTasks / a goroutine) only for short, fire-and-forget, loss-tolerant work. Anything that must not be lost goes to a **real queue** — ARQ or TaskIQ for async-native FastAPI, Celery when you need its ecosystem/scale.
- **Scheduled jobs** (polling an upstream, a nightly sync) via a scheduler (APScheduler / cron) with one owner — not a `sleep` loop; make each run **idempotent** so an overlap or replay is safe.
- **At-least-once is the norm**: jobs retry with backoff and land failures in a **dead-letter** path rather than vanishing; log job start/end with a correlation ID.
- **Receiving webhooks**: verify the signature, respond fast (202) and process async, and dedupe by event ID — deliveries repeat.

## Operability

- Structured logs with a request ID on every entry — one request must be traceable end to end.
- `/healthz` (process up) and `/readyz` (dependencies reachable) — distinct, because they answer different questions.
- RED metrics (rate, errors, duration) on the request path.
- Config from environment, validated at startup — fail fast and loud on bad config, never limp.
- Graceful shutdown: stop accepting, drain in-flight, then exit.

## Persistence

- **Postgres by default** for anything with real data — async driver + a bounded connection pool (asyncpg + SQLAlchemy 2.0 async for FastAPI, pgx for Go, Postgres.js/Drizzle for Node). **SQLite** only for embedded, single-file, single-node cases.
- **Migrations** versioned and reversible, expand → migrate → contract (Alembic for Python). Never edit a shipped migration — add a new one.
- **Explicit, short transaction boundaries** wherever an invariant spans more than one write — and never hold a transaction open across an outbound API call.
- Size the pool to the DB's real connection limit; kill N+1 (fetch related rows in one query, not per row). Parameterized queries only — never string-built SQL.

## Auth (serving side)

The server is the source of truth for auth — the frontend's checks are convenience; this is the boundary.

- **Validate a token on every non-public route.** Short-lived access token (JWT or opaque server session), paired with the frontend's **httpOnly, Secure refresh cookie** for the refresh flow.
- **Hash passwords with argon2id** (or bcrypt) — never store or log credentials, never roll your own crypto.
- **Authz by scope/role**, checked at the handler — "authenticated" is not "authorized." Deny by default.
- Tokens expire; support refresh and **revocation** (a logout or a leaked token must be killable). Rate-limit auth endpoints hardest.

## Security

- Secrets from env or a secret store — never in code, images, or logs.
- Explicit CORS allowlist (never `*` with credentials); rate limiting on anything exposed (token bucket, return `Retry-After`).
- Validate and bound every input at the boundary; your own frontend is still an untrusted caller.

## Testing & quality gate

- **Unit** the pure logic; **integration-test** the handlers against a **real ephemeral database** (testcontainers or a throwaway Postgres — not mocks of your own DB).
- **Mock the upstreams** you consume (respx / WireMock) and **test the failure paths that matter**: a timeout fires, a retry backs off, the circuit breaker opens. Resiliency code is worthless untested.
- **Contract-test** against the OpenAPI spec so served shapes can't drift from what the frontend builds on.
- Before "done": the service starts clean, tests pass, and the primary endpoints were exercised with **real requests** (curl/httpie) — request and response pasted in the review packet. An API that was never called is written, not verified.
