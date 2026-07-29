# Security-audit checks — command-level detail

Read from `SKILL.md`. Every command here is read-only; anything that would fix what it finds
routes to `sde-agents:homelab-platform`, and vulnerability findings feed
`sde-agents:upgrade-campaign`'s ordering. Substitute the lab's real hosts, zones, and domains, and
read the lab repo's own config first — the adversary questions below are all "what does the
running system let someone do", and the repo is where the *intended* answer lives.

Per check: what to read, the attack path a finding must show, and the fix class (one line — the
audit never applies it).

Boundary with hygiene: `sde-agents:lab-audit` check 1 (Exposure) asks whether ports match the
proxy list — that is hygiene, and it stays there. This file asks what an attacker reaches *from a
named position*, which is why every row below starts from an attacker location rather than from an
inventory.

## 1. Trust zones and reachability

- Read: the lab's zone/VLAN map from the repo; `ip -br addr` and `ip route` per host; the
  router/firewall inter-zone rules where the repo exports them; the reverse proxy's upstream map;
  `docker network ls` plus `docker network inspect <net>` for container-level reachability.
- Ask, per attacker position (guest wifi, IoT VLAN, a compromised container, the LAN, the WAN):
  what is reachable at all, and what of that is reachable *without* crossing the proxy.
- Finding: `[P0]` a service reachable from a lower-trust zone without auth; `[P1]` flat container
  networking that lets one compromised service reach every other; `[P2]` reachable but
  authenticated and patched.
- Attack path: "on guest wifi → 10.0.0.0/24 unfiltered → Grafana admin on :3000 with no auth."
- Fix class: an inter-zone rule, a proxy-only binding, or a segmented docker network.

## 2. Authentication on exposed services

- Read: the proxy config's auth blocks per route; each app's own auth setting from its config or
  compose env (names, never values); anything answering on a WAN-forwarded port.
- Ask: which exposed routes have *no* authentication, which have app-native auth only, and which
  sit behind the lab's SSO or forward-auth. An unauthenticated route that "nobody knows the URL
  of" is unauthenticated.
- Finding: `[P0]` WAN-reachable with no auth; `[P1]` LAN-reachable admin surface with no auth or
  with app-native auth that has no lockout/2FA on an account that can change the system.
- Attack path: name the reachable URL and what the unauthenticated caller can do with it.
- Fix class: auth in front at the proxy, or remove the exposure.

## 3. Management planes

- Read: what listens on management ports across hosts (hypervisor UI/API, IPMI/BMC, switch and AP
  admin UIs, container APIs — `ss -tlnp` filtered to those ports, the hypervisor's own config,
  the repo's network inventory); whether the docker socket is mounted into any container
  (`docker inspect` for `/var/run/docker.sock` in Mounts).
- Ask: is each management plane reachable only from the management zone or VPN? A mounted docker
  socket is root on the host — treat any container holding it as a management plane.
- Finding: `[P0]` a management plane reachable from a user or guest zone, or from the WAN;
  `[P0]` docker socket mounted into an internet-exposed container; `[P1]` management plane on the
  ordinary LAN with default or shared credentials.
- Attack path: position → management plane → what it controls (all VMs, all containers, the
  network itself).
- Fix class: bind to the management interface, VPN-only, or remove the socket mount.

## 4. Credentials

- Read: compose and unit files for credential *names* and defaults left in place; each app's admin
  account list where readable; the lab's password-manager or vault inventory as the intended
  record; SSH `authorized_keys` per host and per user.
- Ask: which services still hold their shipped default, which share one password across services,
  which admin accounts predate the current operator's practice, and which SSH keys are
  unaccounted for. An unknown authorized key is a compromise signal — see the stop rule.
- Finding: `[P0]` default or shared credential on anything reachable from a lower-trust zone;
  `[P1]` shared credential internally; `[P1]` stale admin account or unaccounted key.
- Attack path: which position can present the credential, and what it unlocks.
- Fix class: rotate and record in the vault; delete stale accounts and keys.

## 5. Secrets posture

- Read: see [`secrets.md`](secrets.md) — that file owns this row's depth (where secrets live, what
  leaks them, rotation, and blast radius).
- Finding shape and fix class: per that file.

## 6. Vulnerability triage

- Read: pinned image tags and package versions from the repo; the advisory record for the ones
  that matter (GHSA/CVE, and whether the vulnerability is in the known-exploited list); check 1's
  reachability answer for each affected service.
- Ask: not "what CVEs exist" but "which of them is reachable from an attacker position, and what
  does it get them". Triage output is an ordered list for `sde-agents:upgrade-campaign`, never a
  raw dump. Version intel is a web lookup: when the session can't fetch it, say so in the
  denominator (the caller or `sde-agents:researcher` supplies it).
- Finding: `[P0]` known-exploited vulnerability in a WAN-reachable service; `[P1]` high-severity
  and reachable from a user zone; `[P2]` unreachable or requires local access already held.
- Attack path: attacker position → the vulnerable version → what the exploit yields.
- Fix class: an ordered upgrade batch via `sde-agents:upgrade-campaign` (single urgent bump via
  `sde-agents:homelab-platform`).

## 7. Personal-data paths

- Read: which services hold household data (photos, documents, messages, health, finance, camera
  footage), where their volumes live, where backups go (including any off-site or cloud
  destination), and which of those paths cross a boundary in cleartext.
- Ask: at home scale the question is not compliance but "what would hurt": whose data, who can
  reach it, whether backups of it are encrypted before leaving the house, and whether an ex-guest
  or old device still has a path to it.
- Finding: `[P0]` family data reachable from a lower-trust zone or backed up unencrypted off-site;
  `[P1]` camera or document storage with weak auth; `[P2]` data whose retention nobody chose.
- Attack path: position → data store → what is readable or downloadable in bulk.
- Fix class: encrypt the backup destination, tighten the reach, or delete what nobody needs.

## Findings ledger

Use the same ledger table `sde-agents:lab-audit`'s
[`references/checks.md`](../../lab-audit/references/checks.md) defines, with `check` naming the
row above (e.g. `zones`, `mgmt-planes`, `personal-data`) so hygiene and adversary findings coexist
in one ledger and neither overwrites the other.
