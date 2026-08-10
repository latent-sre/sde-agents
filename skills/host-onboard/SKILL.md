---
name: host-onboard
description: The standardization checklist sde-agents:homelab-platform works when bringing a new or rebuilt machine into the lab — OS and patch baseline, users and SSH with access recovery, package and update policy, firewall and management exposure, systemd health, storage, time and DNS, telemetry enrollment, backup enrollment, and config tracking with rollback. To onboard a host, ask sde-agents:homelab-platform (it owns change authority and works this checklist under its tiers); a user can also run it directly as /sde-agents:host-onboard.
argument-hint: [host to onboard]
disable-model-invocation: true
---

The checklist that turns a fresh install into a lab host someone can operate at 3 a.m. Work every
step in order; when one is skipped, say so explicitly and why — silence reads as "done."

`sde-agents:homelab-platform` owns change authority for everything below, and this checklist runs
**under** that agent — it is not self-sufficient standalone. Nearly every step changes a live
host, and several touch the paths you or the operator are connected through: classify each apply
under homelab-platform's change tiers (Tier 0 observe · 1 prepare · 2 reversible live change,
needs approval · 3 destructive/access-path, needs approval + proven recovery) — SSH, firewall,
and user changes are Tier 3 by definition, because getting them wrong locks the operator out.
This checklist grants no permission of its own. Whichever way you arrived here (homelab-platform
reads it by path; it may also be model-invocable as a plugin skill), the authority stays with
homelab-platform: if you reached it without that agent's tier discipline, stop and route through
it.

**Read the lab's own profile before step 1.** The lab repo's project context states the stack,
hosts, conventions, and quirks; those facts outrank any default here. If the lab has no such
file, the lab-profile template that ships with `sde-agents:service-onboard`
is the shape to create in *the lab's* repository.

**These steps are acceptance criteria, not a queue to drain before the first artifact.** A
bounded request gets its blocking discovery, then the artifact under the tier it lands in; every
step not yet worked travels in the delegation handoff packet `sde-agents:homelab-platform` owns —
`Blocking:` when it stops the artifact, `Open lanes:` with an owner when it does not. Access-path
steps (2 and 4) are blocking by nature, because a staged host nobody can reach is not progress.

1. **OS and patch baseline** — supported release, current patch level, and where this host sits in
   `sde-agents:upgrade-campaign`'s cadence from day one. Record the installed baseline in the lab
   repo.
2. **Users, SSH, and access recovery** — named users and groups, sudo policy, key-only SSH, root
   login off — and a proven second way in (console, IPMI/KVM, or physical) **before** the first
   lockout-capable change, not after. Never cut the branch you're sitting on: sequence SSH and
   firewall edits so the current session survives every step.
3. **Package sources and update policy** — the repos and channels this host trusts, unattended
   security updates on or deliberately off (say which and why), and nothing installed outside them
   without a note in the lab repo.
4. **Host firewall and management exposure** — default-deny inbound where the lab's pattern allows
   it; management planes (SSH, IPMI, hypervisor UI) reachable only from the management network or
   VPN, never the WAN. Every open port is either justified in writing or closed.
5. **systemd health** — units the host exists to run are enabled with restart policies; failed
   units are zero at handoff (`systemctl --failed` is the evidence); anything the household would
   miss gets a health check.
6. **Disks, filesystems, and mounts** — layout recorded in the lab repo, mounts in fstab or units
   (not hand-mounted), capacity headroom stated, and SMART/health monitoring on physical disks.
7. **Time and DNS** — NTP syncing against the lab's chosen source, correct timezone, and the
   host's resolver pointing where the lab profile says — with the fallback path stated if that
   resolver is itself a lab service.
8. **Telemetry enrollment** — node metrics scraped and logs shipped per the lab's stack; designing
   the queries, alerts, or dashboards is the `sde-agents:observability` skill's job. An alert
   exists if the household would notice this host being down.
9. **Backup enrollment and restore ownership** — anything stateful on this host joins the backup
   set now, the restore path is named (not assumed), and the first
   `sde-agents:restore-drill` rehearsal is scheduled rather than implied.
10. **Config tracking, validation, and rollback** — the host's config lives in the lab repo
    (files, or the automation the lab already uses), every applied change had its validate step,
    and the rollback for each Tier 2/3 change was stated before the apply. The services this host
    will run each get `sde-agents:service-onboard` separately — this checklist ends where that one
    begins.

Finish with the review packet: what was configured (with tier and approval evidence per apply),
the access-recovery path proven in step 2, the enrollment evidence from steps 8–9, and anything
skipped — named, with why.
