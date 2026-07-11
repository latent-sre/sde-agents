---
name: lab-audit
description: Use for a periodic home-lab health and hygiene sweep, or when asked "what's wrong with my lab", "audit my setup", or after a long gap in maintenance. Surveys and reports; for the fixes themselves, use the homelab-platform agent.
argument-hint: [scope - a host, a stack, or the whole lab]
---

Audit the lab against its own standards and report like a code review of the infrastructure: severity-ranked, evidence-cited, no finding without the command output that proves it.

## Checks (run what's applicable; list what you couldn't run and why)

All checks are read-only — fan them out in parallel (per host or per area) rather than sweeping serially.

- **Exposure** — listening ports vs. what the reverse proxy should be fronting; anything WAN-reachable; services without auth in front.
- **Container hygiene** — `latest` tags, missing restart policies, missing health checks, no resource limits, containers in exited/restarting loops.
- **Certificates** — anything expiring within 30 days; services still on plain HTTP.
- **Backups** — stateful services missing from the backup set; age of the last successful backup; date of the last actual restore test. A backup that has never been restored is a hope, not a backup.
- **Monitoring gaps** — services with no probe or scrape target; alerts that route to nowhere.
- **Drift** — running config vs. the git repo; snowflake changes made outside code.
- **Capacity** — disk usage and growth rate; anything over 80%; logs or volumes growing without rotation.
- **Updates** — pinned versions vs. available, prioritizing the security-relevant surface: the proxy, VPN, and anything exposed.

## Output

`[P0]`–`[P3]` findings, each with the evidence (command + output) and the one-line fix. P0 = exposed without auth, or stateful and unbacked-up. End with the top three things to fix this weekend — not a list of thirty.
