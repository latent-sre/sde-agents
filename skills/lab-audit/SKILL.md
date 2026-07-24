---
name: lab-audit
description: A read-only home-lab health and hygiene sweep that reports severity-ranked, evidence-cited findings. Use for a periodic audit, when asked "what's wrong with my lab" or "audit my setup", or after a long gap in maintenance. Surveys and reports; for the fixes themselves, use sde-agents:homelab-platform.
argument-hint: [scope - a host, a stack, or the whole lab]
disallowed-tools: Write, Edit
---

Audit the lab against its own standards and report like a code review of the infrastructure: severity-ranked, evidence-cited, no finding without the command output that proves it.

## Checks (run what's applicable; list what you couldn't run and why)

All checks are read-only. `disallowed-tools` removes Write and Edit while this skill is active, but Bash can still mutate (redirects, `docker rm`), so the mandate is still yours: inspection commands only — fixes route to `sde-agents:homelab-platform`. Whether you were invoked directly from the main session or under `homelab-platform`, the reviewer's Bash guard does not cover this skill (that hook keys on the `code-reviewer` agent_type, and the main loop carries none at all) — the read-only-ness here is cooperative, not enforced. Fan the checks out in parallel (per host or per area) rather than sweeping serially.

- **Exposure** — listening ports vs. what the reverse proxy should be fronting; anything WAN-reachable; services without auth in front.
- **Container hygiene** — `latest` tags, missing restart policies, missing health checks, no resource limits, containers in exited/restarting loops.
- **Certificates** — anything expiring within 30 days; services still on plain HTTP.
- **Backups** — stateful services missing from the backup set; age of the last successful backup; date of the last actual restore test. A backup that has never been restored is a hope, not a backup.
- **Monitoring gaps** — services with no probe or scrape target; alerts that route to nowhere.
- **Drift** — running config vs. the git repo; snowflake changes made outside code.
- **Capacity** — disk usage and growth rate; anything over 80%; logs or volumes growing without rotation.
- **Updates** — pinned versions vs. available, prioritizing the security-relevant surface: the proxy, VPN, and anything exposed.

## Output

Open with the coverage denominator — hosts covered and checks run vs. skipped, with why (e.g. "3/4 hosts; 6/8 checks — backups and drift skipped: no repo access") — findings without a denominator overstate the sweep. Then `[P0]`–`[P3]` findings, each with the evidence (command + output) and the one-line fix. P0 = exposed without auth, or stateful and unbacked-up. End with the top three things to fix this weekend — not a list of thirty.
