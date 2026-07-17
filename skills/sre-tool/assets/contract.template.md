<!-- Interface contract — instantiate as a repo artifact at Phase 1 for any multi-component build
     (see references/multi-component.md). Parallel builders cite THIS FILE and its version line,
     never each other's code. It is living: an implementation that diverges updates it in the same
     change; the owner propagates every change to affected builders at once. -->

# Interface contract — <project>

- **Owner**: <!-- required: the ONE builder who may edit this during a parallel batch; everyone else routes change requests through the orchestrator -->
- **Version**: <!-- required: bump on every change; builders cite the version they built against -->

## Endpoints

| Method + path | Purpose | Auth |
|---|---|---|

## Examples — one request/response pair per endpoint (prose alone is not a contract)

### <METHOD /path>

Request:

```json
```

Response (status <code>):

```json
```

## Error cases

<!-- every error a client can see, each in the one error envelope (backend-craft: same shape for
     validation errors, 404s, and 500s; request_id in every one) -->

## Change log

| Version | Change | Propagated to |
|---|---|---|
