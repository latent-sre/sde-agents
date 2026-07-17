# Default design language — designed, not default

Read this when styling a **greenfield or unbranded** UI — no established design system, brand, or
shell convention to match. An existing design system always wins (see SKILL.md's carve-out): in a
branded repo you match its vocabulary and never restyle toward this default, so don't load this file
there.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.

The bar: at home next to Linear or Vercel's dashboard with the color courage turned up — never
mistakable for an unstyled admin template. Organized and uncluttered is the floor, not the ceiling.

## App shell

- **Default to a sidebar rail.** Any app with more than ~5 destinations gets a persistent left
  sidebar rail, not top tabs (tabs don't scale past a handful): icon + label nav grouped by area,
  the active item marked with an accent bar or tint, a brand mark at the top and the user/account
  with theme toggle pinned at the bottom. Top tabs or a single-column layout are reserved for
  genuinely small apps (≤5 views) or a focused single-purpose tool. The rail collapses to
  icons-only on narrow viewports.

## Visual character

- **Dark-first, layered surfaces.** Dark is the designed-for theme (light stays supported via
  tokens): a deep page background, cards a distinct step lighter, raised elements a step lighter
  again. Depth comes from this layering plus low-alpha borders and soft shadows — not heavy lines.
- **Color with courage.** One vivid accent used confidently: gradient touches on primary actions
  and active states, and one hero moment per view — a gradient heading, a glowing stat. Status
  colors saturated enough to glow against dark surfaces; status pills get a colored dot *plus*
  text, never color alone.
- **Categorical accents on KPI grids.** When a view shows a row of distinct metrics or stat cards,
  give each its own accent hue (e.g. purple / teal / amber / cyan) rather than repeating one color —
  the color *codes* the category, with the icon and number tinted to match. Elevate one card above
  the rest (an accent border-glow on the most important metric) so the grid has a focal point. Keep
  the accent set to ~4–5 hues drawn from the theme tokens; this is categorical coding, not a
  rainbow.
- **Typography with character.** A quality UI font (Inter or similar, self-hosted — no CDN
  dependency), tight letter-spacing on large headings, `tabular-nums` for data, big confident
  numbers on stat tiles.
- **Depth cues, spent sparingly.** Rounded-xl cards, soft elevation shadows, hover lift (small
  translate + shadow), accent-colored focus rings. If every surface is elevated, nothing is.
- **Designed states.** Skeleton shimmer instead of spinners for content areas; empty states get an
  icon and a call to action; icons anchor navigation, actions, and stats.
- **Every view is a composition.** If the primary content fills only a fraction of the viewport,
  that's a design defect: either enrich the view (supporting detail, recent activity, a trend over
  time — whatever the data honestly supports) or constrain the canvas to fit the content. Never
  ship a screen that is mostly empty page.

## Motion

- Transitions 150–250 ms, ease-out.
- Micro-interactions are part of the design, not decoration on top of it: hover lifts, pressed
  states, animated number changes on live stats, staggered list entrances (30–50 ms steps), smooth
  expand/collapse.
- Motion serves state change and perceived quality — but stays fast and interruptible; if an
  animation makes the user wait, cut it.
