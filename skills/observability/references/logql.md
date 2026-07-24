# LogQL — querying Loki without melting it

Read before writing a LogQL query or designing Loki labels. The universal rules live in
`skills/observability/SKILL.md`. On any conflict, SKILL.md wins.

## Shape of a query: select a stream, then filter inside it

```logql
# Select by label (indexed), then filter by content (scanned)
{service="paperless", container="webserver"} |= "ERROR"

# Parse structured logs, then filter on a parsed field
{service="paperless"} | json | level="error" | line_format "{{.msg}}"

# Logfmt and regex extraction
{job="proxy"} | logfmt | status >= 500
{job="proxy"} | regexp `(?P<status>\d{3}) (?P<latency>[\d.]+)ms` | latency > 500

# A metric from logs — rate of error lines per service
sum(rate({env="lab"} |= "ERROR" [5m])) by (service)

# Count occurrences over a window, grouped by a parsed field
sum by (status) (count_over_time({job="proxy"} | logfmt | __error__="" [1h]))
```

## The one rule that matters most: label selectors are the index

Loki indexes **labels only**; everything after the stream selector scans the matched logs. So a
query's cost is set by how much the `{...}` narrows it. `{env="lab"} |= "timeout"` reads every log
in the lab; `{service="proxy"} |= "timeout"` reads one service's. Always select the narrowest stream
you can, and always bound the time range.

## Label design — the mirror of metric cardinality

- **Labels are stream identity.** Every distinct combination creates a stream; each stream carries
  its own index and chunks. High-cardinality labels (request id, user, trace id, full path,
  timestamp) are the way to make Loki unusable, and the failure looks like "queries got slow" rather
  than an error.
- Keep them bounded and structural: `service`, `container`, `host`, `env`, `job`, `level` if it's a
  fixed set.
- **Put the varying detail in the line, not the label.** That's what `| json`/`| logfmt` and filter
  expressions are for — you can query on parsed fields without paying index cost for them.
- Changing a label set creates new streams and does not rewrite history; old queries keep matching
  the old streams. Plan labels before you ship, not after.

## Traps

- **`__error__` on parse failures.** A malformed line makes `| json` set `__error__`, and downstream
  comparisons silently drop those lines — a filter that looks like it counts everything counts only
  the parseable. Add `| __error__=""` deliberately (and check what you're excluding) rather than
  by accident.
- **`|=` is a substring, not a regex.** Use `|~` for regex, and anchor it: an unanchored `.*` over a
  large stream is the expensive shape.
- **Line filters run in order** — put the cheapest, most selective filter first (`|= "ERROR"` before
  a regex), because each stage only sees what survived the last.
- **`rate()` over logs counts lines, not events.** A single logical error that logs a stack trace
  across 20 lines counts as 20 unless you filter to its first line.
- **Absence is invisible.** "No error logs" and "the log shipper stopped" look identical. Alert on
  the shipper's own health (or on a heartbeat log line's absence), not only on error volume.
- Grafana's default range is often wider than you think; a query that "hangs" is usually scanning
  days.

## Logs versus metrics for alerting

Prefer a metric for anything you alert on repeatedly — it's cheaper and more stable. Log-derived
alerts earn their place for things no metric captures: a specific error string, a stack trace class,
an authentication failure pattern. When a log-derived alert becomes routine, promote it to a real
metric in the application.
