---
name: backend-craft
description: Use when building or changing an API or backend service — HTTP endpoints, workers, schedulers, or the service behind a UI — and when consuming or integrating third-party APIs (clients, SDK wrappers, sync jobs, webhooks). For the UI layer, use sde-agents:frontend-craft; for a full multi-file feature with tests, use sde-agents:sde-fullstack.
argument-hint: [the API or service to build or change]
---

# Backend craft

**You write the actual code.** Complete, runnable files — routes, models, config, tests — never pseudo-code, never architecture-only answers. Make the decision, state it in one line, build it. Exception — a material fork (the answer changes what gets built: data model, auth, API surface) that can't be inferred is worth one batched question round with recommended defaults *before* building; a wrong build costs a full rebuild-and-review cycle, a question costs seconds. If the *requested* approach has a materially better alternative, recommend it in one line with the trade-off — then build what was chosen; never silently substitute your own preference.

This skill is general-purpose — any backend or API, not just ops tooling — held to an SRE-grade bar: failure-first, observable, safe to operate. The examples lean ops/home-lab; the rules are domain-neutral.

## Stack

An existing repo's stack always wins — match it. Greenfield, pick by the **dominant constraint** and say why in one line:

- **Python + FastAPI** (default): typed Pydantic, OpenAPI for free (feeds the contract-first flow), and the richest ecosystem of API/SDK clients — best when the job is data work or integrating many upstream APIs.
- **Go**: single static binary, tiny container, first-class concurrency — best for agents, daemons, network services, and anything that must land on a host with no runtime.
- **Node + TypeScript** (Fastify / Hono; Bun for raw speed): when sharing types end-to-end with the React frontend is the dominant concern.
- **Rust** (Axum): max throughput and memory safety with no GC — a data-plane component or a hot-path agent. More to write; spend it only where the performance *is* the point.

Beyond these four, reach further only when a constraint clearly beats all of them and name it — e.g. **Elixir/Phoenix** when soft-real-time plus massive connection concurrency is the product. The rules below are language-neutral; only the examples are Python/Go-flavored.

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
- Guard shared mutable state and concurrent access; make every write safe under retry (transaction boundaries live under Persistence).

These are the system-wide principles. The client-side mechanics for *calling other services* — retry policy, breakers, token refresh — live in Consuming APIs below; don't restate them ad hoc.

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
- **Observe every upstream call**: log target, latency, status; **propagate your request ID downstream** (`X-Request-ID`) so one trace spans services; RED metrics per upstream; reflect a hard-down critical dependency in `/readyz`.

## Background work & scheduling

- **In-process** (FastAPI BackgroundTasks / a goroutine) only for short, fire-and-forget, loss-tolerant work. Anything that must not be lost goes to a **real queue** — ARQ or TaskIQ for async-native FastAPI, Celery when you need its ecosystem/scale.
- **Scheduled jobs** (polling an upstream, a nightly sync) via a scheduler (APScheduler / cron) with one owner — not a `sleep` loop; make each run **idempotent** so an overlap or replay is safe.
- **At-least-once is the norm**: jobs retry with backoff and land failures in a **dead-letter** path rather than vanishing; log job start/end with a correlation ID.
- **Receiving webhooks**: verify the signature, respond fast (202) and process async, and dedupe by event ID — deliveries repeat.

## Serving live data (SSE / WebSocket)

The frontend's default for live data is SSE — this is the serving half of that contract.

- **SSE for one-way push** (status, metrics, logs): send a keep-alive comment every 15–30 s so proxies don't kill idle streams; `Cache-Control: no-cache` and disable proxy buffering (flush per event).
- **Support resume**: give events `id`s and honor `Last-Event-ID` on reconnect — EventSource auto-reconnects, so design for dropped clients rather than pretending they don't happen.
- **WebSocket only when the client must push too**; then heartbeat/pong and close idle connections deliberately.
- **Bound it**: cap concurrent streams, drop slow consumers instead of buffering unbounded, and count open streams in your metrics.
- Streams are requests: authenticate them, tag them with a request ID, and close them cleanly during shutdown.

## Operability

- Structured logs with a request ID on every entry — one request must be traceable end to end.
- `/healthz` (process up) and `/readyz` (dependencies reachable) — distinct, because they answer different questions.
- RED metrics (rate, errors, duration) on the request path.
- Config from environment, validated at startup — fail fast and loud on bad config, never limp.
- Graceful shutdown: stop accepting, drain in-flight requests, finish or re-queue the running job, stop the scheduler, close live streams — then exit.

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
- **Machine callers too**: scripts and services calling your API get scoped, revocable API keys or client-credentials — logged like any user, never a shared admin token pasted into a script.

## Security

- Secrets from env or a secret store — never in code, images, or logs.
- Explicit CORS allowlist (never `*` with credentials); rate limiting on anything exposed (token bucket, return `Retry-After`).
- **Bound what you accept**: request-body size caps, server-side request timeouts, and bounded query params (max page size, max array length). Inbound requests can do unbounded damage exactly like unbounded outbound calls — input *validation* itself lives under Resiliency.

## Testing & quality gate

- **Unit** the pure logic; **integration-test** the handlers against a **real ephemeral database** (testcontainers or a throwaway Postgres — not mocks of your own DB).
- **Mock the upstreams** you consume (respx / WireMock) and **test the failure paths that matter**: a timeout fires, a retry backs off, the circuit breaker opens. Resiliency code is worthless untested.
- **Contract-test** against the OpenAPI spec so served shapes can't drift from what the frontend builds on.
- Before "done": the service starts clean, tests pass, and the primary endpoints were exercised with **real requests** (curl/httpie) — request and response pasted in the review packet. An API that was never called is written, not verified.
