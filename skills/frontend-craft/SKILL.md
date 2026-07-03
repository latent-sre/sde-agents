---
name: frontend-craft
description: Use when building or changing a web UI — pages, dashboards, forms, admin panels, config editors — from a single page to a full SPA. Covers stack choice, layout, styling, motion, state management, and API integration.
argument-hint: [the UI to build or change]
---

# Frontend craft

**You write the actual code.** Complete, runnable files — components, styles, config, wiring — never pseudo-code, never "you could use X," never TODO stubs. If a decision is needed, make it, state it in one line, and build. Exception — a material fork (the answer changes what gets built: data model, auth, interface scope) that can't be inferred is worth one batched question round with recommended defaults *before* building; a wrong build costs a full rebuild-and-review cycle, a question costs seconds. If the *requested* approach has a materially better alternative, recommend it in one line with the trade-off — then build what was chosen; never silently substitute your own preference.

## Stack

An existing repo's stack always wins — match it. Greenfield default: **React + TypeScript** on Vite, **Tailwind** for styling, shadcn/ui-style components (Radix primitives + Tailwind), **TanStack Query** for server state, **Framer Motion** for transitions.

Every web UI gets this stack, no matter how small it looks — there is no plain-HTML escape hatch to reach for on your own. If the user explicitly asks for a static page or plain HTML, comply; that call is theirs, not yours.

## Layout — organized, uncluttered, space-efficient

- **Hierarchy first**: one primary action per view; group related controls; the eye should land on what matters without hunting.
- **Spacing grid**: consistent scale (4/8px steps), generous whitespace at decision points, higher density where data lives — tables and lists earn compactness, forms and actions earn air.
- **Constrain line lengths**: max content width; multi-column only when content genuinely parallels.
- **Typography**: 4–5 sizes total; hierarchy through size and weight, never color alone.
- **Color**: neutral base plus one accent; semantic colors (success/warn/error) reserved for status, never decoration. Dark mode via CSS variables from day one — lab dashboards get read at night.

## Motion — smooth, purposeful, cheap

- Transitions 150–250 ms, ease-out; animate `opacity` and `transform` only (compositor-friendly — no layout thrash).
- Motion communicates state change (enter/exit, expand, reorder), never decoration. If removing an animation loses no information, remove it.
- Respect `prefers-reduced-motion`.

## State and data

- Server state lives in TanStack Query (caching, retries, invalidation); UI state stays local. No global store until two distant components genuinely share state.
- **Typed API client derived from the contract** — the OpenAPI spec or shared types are the source of truth; never hand-maintain response shapes in two places.
- Every async view has designed **loading, error, and empty states**. The empty state is a real design ("no targets configured yet — add one") — never a blank region.

## Resilience UX (the SRE lens applied to pixels)

- Errors show what happened *and* what to do next; raw stack traces never reach the user.
- Buttons disable while pending; no double-submits.
- No infinite spinners — every wait times out into an actionable error state.
- Optimistic updates only with visible rollback on failure.

## Accessibility (baseline, not optional)

Semantic HTML first; every input labeled; keyboard reachable with visible focus; contrast at AA. If a div has an onClick, it wanted to be a button.

## Quality gate

Before "done": it typechecks, the dev server runs, and the primary flow was exercised in a real browser render — with the evidence in the review packet. A UI that compiles but was never rendered is written, not verified.
