# Backend stack selection

Read this when starting a **greenfield** service. An existing repository's stack always wins —
if you are working in one, you do not need this file.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

Greenfield, pick by the **dominant constraint** and say why in one line:

- **Python + FastAPI** (default): typed Pydantic, OpenAPI for free (feeds the contract-first flow), and the richest ecosystem of API/SDK clients — best when the job is data work or integrating many upstream APIs.
- **Go**: single static binary, tiny container, first-class concurrency — best for agents, daemons, network services, and anything that must land on a host with no runtime.
- **Node + TypeScript** (Fastify / Hono; Bun for raw speed): when sharing types end-to-end with the React frontend is the dominant concern.
- **Rust** (Axum): max throughput and memory safety with no GC — a data-plane component or a hot-path agent. More to write; spend it only where the performance *is* the point.

Beyond these four, reach further only when a constraint clearly beats all of them and name it — e.g. **Elixir/Phoenix** when soft-real-time plus massive connection concurrency is the product. The craft rules in `SKILL.md` are language-neutral; only the examples here are Python/Go-flavored.

