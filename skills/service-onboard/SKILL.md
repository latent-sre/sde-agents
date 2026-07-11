---
name: service-onboard
description: Use when adding a new self-hosted service to the home lab — a new container, stack, or app — or when bringing an existing ad-hoc service up to standard. For broader platform work or troubleshooting, use homelab-platform.
argument-hint: [service to add]
---

The checklist that keeps the lab from rotting. Work through every step in order; when one is skipped, say so explicitly and why — silence reads as "done."

1. **Placement** — which host, what resource envelope (CPU/RAM/disk), and what conflicts exist (ports, storage paths, names).
2. **Config as code** — compose file or unit in the lab repo; image version pinned (never `latest`); restart policy; health check; resource limits.
3. **Storage** — named volumes or explicit paths for state; added to the backup set; confirm the restore path actually exists, don't assume it.
4. **Network** — reverse proxy entry, DNS record, TLS. No direct port exposure without written justification.
5. **Security** — auth in front (SSO, basic auth, or app-native); default credentials changed; not WAN-reachable unless genuinely required.
6. **Observability** — health or metrics endpoint scraped or probed; an alert exists if the household would notice this service being down.
7. **Runbook stub** — what it is, how to restart it, where its data lives, known quirks. Use the `runbook` skill.
8. **End-to-end verify** — reach it at its final URL as a normal user would; restart the container once and confirm it comes back up on its own.

Finish with the review packet: what was deployed, the rollback (how to remove it cleanly), the evidence from step 8, and anything that was skipped.
