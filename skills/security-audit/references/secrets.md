# Secrets posture — the audit row's depth

Read when check 5 trips. `SKILL.md` owns the sweep's rules (read-only, attack path or downgrade,
active-compromise stop); this file owns what to look at and what a real finding looks like. On
conflict, SKILL.md wins; the lab's own conventions outrank both.

The question is not "are secrets stored badly" in the abstract. It is: **what does an attacker who
reaches position X learn, and what does that credential then open?** Blast radius is the finding.

## Where to look, and what it means

- **The lab repo's history, not just its worktree.** A secret deleted in the current file is still
  in git history and still valid until rotated. `git log -p -- <env-or-config-path>` and a search
  across history for the shapes below; a hit is a finding even if the file is now clean.
- **Compose and unit files** for inline values rather than `env_file:`/`EnvironmentFile=`
  indirection. Read names, never values — an audit that copies a secret into its own report has
  created a new leak. Cite `file:line` and the variable *name*.
- **Env files on disk**: permissions (`ls -l` — world-readable is a finding), ownership, and
  whether they sit inside a directory the proxy or an app can serve.
- **Container environment at runtime** (`docker inspect` env keys): anything present here is
  visible to anyone who can talk to the docker socket — which ties this row to check 3.
- **Backups**: whether the backup set includes the env/secret files, and whether that destination
  is encrypted. An unencrypted off-site backup of a secrets directory is the same exposure as
  publishing it, delayed.
- **Logs and telemetry**: grep the log paths and any log shipper's config for the token shapes
  below — secrets in logs leak to everyone with read access to observability, which is usually
  wider than the operator thinks.
- **The vault or password manager as the intended record**: what should be in it, what isn't
  (a secret that exists only in a compose file has no rotation story), and whether its own unlock
  path survives losing a device.

Shapes worth grepping for (in configs, history, and logs — never in the report):
`api[_-]?key`, `secret`, `token`, `password`, `passwd`, `BEGIN .*PRIVATE KEY`, `xox[baprs]-`,
`ghp_`, `github_pat_`, `AKIA`, `eyJ` (a JWT prefix), `postgres://`/`mysql://`/`redis://` with
credentials inline.

## Rotation and reuse

- **A secret with no rotation path is a permanent one.** For each credential: who can rotate it,
  what breaks when it rotates (consumers that hold a copy), and whether that has ever been done.
  "It would break too much to rotate" is itself the P1 finding.
- **Reuse multiplies blast radius.** One password across services, one API token across scripts,
  or a database superuser shared by three apps means one leak is three compromises. Map each
  secret to its consumers; the count is the severity multiplier.
- **Long-lived tokens on the WAN edge** (proxy, VPN, dynamic-DNS updater, anything with a cloud
  API key) rank above internal ones at equal severity, because their exposure position is the
  cheapest for an attacker to reach.

## Findings

- `[P0]` a live secret readable from a lower-trust zone, present in git history for a still-valid
  credential, or included unencrypted in an off-site backup.
- `[P1]` reused across services, world-readable on disk, leaking into logs, or holding no rotation
  path at all.
- `[P2]` internal-only, single-consumer, rotatable, but not recorded in the vault.

Each finding names the secret by variable/file **name and location**, the attacker position that
reads it, and what it opens — never the value itself, in the report or the ledger.

Fix class: rotate first (a leaked secret is leaked regardless of what you fix afterward), then
move it behind indirection (env_file, a secret store, or the lab's vault), then narrow who can
read it. Every one of those is a `sde-agents:homelab-platform` change under its tiers; where the
consumer is application code or CI, the pattern lives in `sde-agents:backend-craft` and
`sde-agents:ci-actions` respectively.
