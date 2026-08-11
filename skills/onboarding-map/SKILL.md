---
name: onboarding-map
description: "Maps the fleet's explicit-only onboarding workflows without running them: which exist (sde-agents:service-onboard for a new or ad-hoc service, sde-agents:host-onboard for a new or rebuilt machine), the order — host first, then the services on it — and how to reach each on the current host. Use when someone asks whether an onboarding checklist or workflow exists, how to start onboarding a service or a host, or states new-service or new-host intent on a host where no routing agent is reachable. Recommending is not executing: the checklists run under sde-agents:homelab-platform's change tiers, and this map changes nothing and grants nothing. Not for performing the onboarding or any lab change — use sde-agents:homelab-platform — and not for auditing an existing setup, which is sde-agents:lab-audit."
argument-hint: [what you are adding — a service, a host, or both]
---

A map, not a procedure: which onboarding workflows exist, which one this situation needs, and how
to reach it here. It holds no authority and carries no steps — everything it names runs under
`sde-agents:homelab-platform`'s change tiers, so naming a workflow never starts one and never
supplies an approval.

## Which workflow applies

| Situation | Route | Why |
|---|---|---|
| A machine new to the lab, or rebuilt | `sde-agents:host-onboard` | Baseline, access recovery, exposure, telemetry, and backups before anything depends on it; its users/SSH/firewall steps are the lab's highest-risk work |
| A service being added, or an ad-hoc one brought up to standard | `sde-agents:service-onboard` | Placement, config as code, storage, network, security, monitoring, an operating doc, and an end-to-end verify |
| A new machine that will also run a new service | Host first, then the service — two sequenced lifecycles | The service checklist assumes the machine under it is already a lab citizen; merging them loses that assumption and fans one request into two efforts at once |
| A service landing on a host the lab already manages | The service workflow alone | An already-onboarded host does not repeat host onboarding — proportional service checks are the whole job |
| "Is this set up correctly?", with nothing to change | `sde-agents:lab-audit` for hygiene, `sde-agents:security-audit` for the adversary's view | A read-only question is an audit; opening a checklist that applies live changes answers a question nobody asked |
| Application code, or lab-shaping architecture | `sde-agents:sde-fullstack`; up the `sde-agents:eng-ladder` | Not onboarding at all — shared vocabulary ("add", "deploy", "service") is not shared remit |

## Four states — say which one this is

| State | What it means | What it authorizes |
|---|---|---|
| **Discovery** | the workflow exists, and this map names it | nothing |
| **Recommendation** | it applies to this request, and here is why | nothing |
| **Activation** | its checklist is open under `sde-agents:homelab-platform` | that agent's Tier 0 observation and Tier 1 preparation |
| **Execution** | a step reaches a live target | only the exact effect the operator approved for that step, under that agent's tiers |

Discovery and recommendation are free; activation and execution are not. Collapsing them fails in
both directions — a user who never learns the workflow exists, and a workflow that reads as
running because something named it. A pause during activation or execution belongs to a gate, and
`sde-agents:homelab-platform` names which one; nothing here removes a gate or stands in for an
approval.

## Reaching one from here

Plain language to `sde-agents:homelab-platform` — "add this service to my lab", "onboard this new
VM" — is the intended route: it owns change authority and works both checklists under its tiers.
Naming the workflow directly, `/sde-agents:host-onboard` or `/sde-agents:service-onboard`, is the
fallback, and it is the *only* route on a host that neither delegates to an agent by description
nor lists explicit-only workflows to the model. The plugin README's per-host install sections
carry the exact invocation syntax for each host; when the plain-language route does not surface
these workflows, say the workflow's name.
