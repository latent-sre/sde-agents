# Consuming APIs — integration discipline

Read this before writing any code that calls another service: a client, an SDK wrapper, a sync job,
or a webhook consumer. Much of a backend's job is being someone else's client; take that as
seriously as being a server.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

- **One typed client per upstream**, configured once — base URL, auth, timeout, retry policy in a single place; never scatter ad-hoc calls (a shared `httpx.AsyncClient`, not a new session per call).
- **Auth to upstreams**: API key / bearer / OAuth2 client-credentials — **cache the token and refresh before expiry**, never re-auth per call.
- **Respect their limits**: honor `429` + `Retry-After`, self-throttle to their quota, backoff + jitter on retryable failures. Never be the reason an upstream rate-limits you.
- **Circuit breaker per upstream**, once call volume can actually hurt something: after N consecutive failures, open the circuit and fail fast instead of hammering a down dependency; half-open to probe recovery. Retries alone don't give you this. At one caller and low volume, a bounded timeout with capped retries already stops the hammering — the breaker earns its state machine when the retry storm is large enough to slow your own service or get you blocked.
- **Consume pagination fully**: follow cursor / next-links to completion, bounded — never assume one page.
- **Upstream responses are untrusted**: parse into *your own* models, tolerate schema drift (ignore unknown fields, fail loudly only on a missing critical one), and never leak a raw upstream error to your caller — translate it into your one error shape.
- **Cache upstream data** with a TTL (stale-while-revalidate) — fewer calls, and you ride out upstream blips.
- **Idempotency for side-effecting calls** — an idempotency key or dedup so a retry doesn't double-submit.
- **Observe every upstream call**: log target, latency, status; **propagate your request ID downstream** (`X-Request-ID`) so one trace spans services; RED metrics per upstream; reflect a hard-down critical dependency in `/readyz`.
- **Adding another integration to a repo that already has them**: the pattern lives in the repo, not the vendor docs. Read at least two existing connectors first and map their layout, config shape, auth handling, retry/pagination conventions, registration wiring, and test style — where they disagree, the newest pattern wins; never invent a second architecture. Done means the new connector is registered, tested, and documented like its siblings, not transport code that compiles.
