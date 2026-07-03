---
name: frontend-craft
description: Use when building or changing a web UI — pages, dashboards, forms, admin panels, config editors — from a single page to a full SPA. Covers stack choice, layout, styling, motion, state management, and API integration.
argument-hint: [the UI to build or change]
---

# Frontend craft

**You write the actual code.** Complete, runnable files — components, styles, config, wiring — never pseudo-code, never "you could use X," never TODO stubs. If a decision is needed, make it, state it in one line, and build. Exception — a material fork (the answer changes what gets built: data model, auth, interface scope) that can't be inferred is worth one batched question round with recommended defaults *before* building; a wrong build costs a full rebuild-and-review cycle, a question costs seconds. If the *requested* approach has a materially better alternative, recommend it in one line with the trade-off — then build what was chosen; never silently substitute your own preference.

## Stack

An existing repo's stack always wins — match it. Greenfield default: **React + TypeScript** on Vite, **Tailwind** for styling, shadcn/ui-style components (Radix primitives + Tailwind), **TanStack Query** for server state, **lucide-react** for icons, and **Framer Motion** when transitions outgrow what CSS handles cleanly — CSS transitions are the right call for hovers, fades, and modals. Any deviation from this stack gets named in the review packet with its one-line reason.

Every web UI gets this stack, no matter how small it looks — there is no plain-HTML escape hatch to reach for on your own. If the user explicitly asks for a static page or plain HTML, comply; that call is theirs, not yours.

## Layout — organized, uncluttered, space-efficient

- **Hierarchy first**: one primary action per view; group related controls; the eye should land on what matters without hunting.
- **Spacing grid**: consistent scale (4/8px steps), generous whitespace at decision points, higher density where data lives — tables and lists earn compactness, forms and actions earn air.
- **Constrain line lengths**: max content width; multi-column only when content genuinely parallels.
- **Typography**: 4–5 sizes total; hierarchy through size and weight, never color alone.
- **Color**: all color through theme tokens, both themes from day one — the palette itself lives in Visual character below.

## Visual character — designed, not default

Organized and uncluttered is the floor, not the ceiling. The bar: at home next to Linear or Vercel's dashboard with the color courage turned up — never mistakable for an unstyled admin template.

- **Dark-first, layered surfaces.** Dark is the designed-for theme (light stays supported via tokens): a deep page background, cards a distinct step lighter, raised elements a step lighter again. Depth comes from this layering plus low-alpha borders and soft shadows — not heavy lines.
- **Color with courage.** One vivid accent used confidently: gradient touches on primary actions and active states, and one hero moment per view — a gradient heading, a glowing stat. Status colors saturated enough to glow against dark surfaces; status pills get a colored dot *plus* text, never color alone.
- **Typography with character.** A quality UI font (Inter or similar, self-hosted — no CDN dependency), tight letter-spacing on large headings, `tabular-nums` for data, big confident numbers on stat tiles.
- **Depth cues, spent sparingly.** Rounded-xl cards, soft elevation shadows, hover lift (small translate + shadow), accent-colored focus rings. If every surface is elevated, nothing is.
- **Designed states.** Skeleton shimmer instead of spinners for content areas; empty states get an icon and a call to action; icons anchor navigation, actions, and stats.

## Motion — smooth, purposeful, alive

- Transitions 150–250 ms, ease-out; animate `opacity` and `transform` only (compositor-friendly — no layout thrash).
- Micro-interactions are part of the design, not decoration on top of it: hover lifts, pressed states, animated number changes on live stats, staggered list entrances (30–50 ms steps), smooth expand/collapse.
- Motion serves state change and perceived quality — but stays fast and interruptible; if an animation makes the user wait, cut it.
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
