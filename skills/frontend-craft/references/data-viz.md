# Data visualization

Read this when the view charts, graphs, or plots anything.

The universal frontend rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.

Chart *design*, in brief: pick the form the data asks for — time series → line, comparison → bar, part-of-whole → stacked bar (pie only for 2–3 slices), distribution → histogram; label axes and units; a dashboard leads with the number that answers the viewer's question. Implementation:

- **Library**: keep the repository's established chart layer. Prefer a declarative SVG library for
  ordinary interactive charts and a measured Canvas/WebGL path for dense real-time series. The
  default React choice lives in `references/stack.md`; a Vue or other framework target uses its
  established compatible equivalent. Never migrate chart libraries as incidental cleanup.
- **Theme**: charts read the same theme tokens and categorical accent palette — never hardcode chart colors.
- **Live data**: stream via the SSE→Query-cache path, but throttle/batch redraws (not every tick) and keep a rolling window for time-series.
- **Perf & a11y**: profile the real mark count and update rate before switching renderers;
  aggregate or downsample without hiding material outliers, and give every chart a text or
  data-table alternative.
