# Worked example — a finished runbook

The shape done right: every command real and copy-pasteable, one honest "n/a", one honest
`unverified`, and a Last-verified line that tells the truth. Fictional service names; the
discipline is the point — adapt names, keep the shape.

---

# postgres-paperless runbook

- What/why: database for Paperless-ngx; document loads start failing within a minute if it's down.
- Where: host `nas-1`; compose file `/srv/stacks/paperless/compose.yaml`; data volume
  `/srv/appdata/paperless/pgdata`; no web UI.
- Health: `docker exec paperless-db pg_isready -U paperless` → `accepting connections`, and
  `docker inspect -f '{{.State.Health.Status}}' paperless-db` → `healthy`.
- Restart: `cd /srv/stacks/paperless && docker compose restart db`, wait until `pg_isready`
  returns `accepting connections` (typically under 10 s), then `docker compose restart webserver`.
- Common failures:
  - Paperless 500s and db log shows `FATAL: the database system is starting up` → crash recovery
    in progress → wait for `pg_isready`; do not restart again mid-recovery.
  - `No space left on device` in db log → `/srv` full (usually WAL growth) → free space, restart,
    then check what grew.
- Recovery: the restore needs a RUNNING database — stop the writers, keep `db` up:
  `cd /srv/stacks/paperless && docker compose stop webserver consumer`
  `gunzip -c /srv/backups/paperless/db-2026-07-20.sql.gz | docker compose exec -T db psql -U paperless paperless`
  `docker compose up -d`
  If pgdata itself is corrupt (startup loops), recreate it first: `docker compose down`, move
  `/srv/appdata/paperless/pgdata` aside, `docker compose up -d db`, wait until Health passes, then
  run the exec restore above and `docker compose up -d`.
  `unverified` — this restore has not been drilled on this host; drill it and update this line.
  Stop repairing and restore when pgdata won't complete startup twice in a row, or repair passes
  30 minutes.
- Dependencies: needs the `paperless` compose network and `/srv` mounted; the Paperless webserver
  and consumer depend on it.
- Alerts: n/a — nothing alerts on this yet; failures surface as Paperless 500s noticed by a
  person. Finding: add a postgres exporter check.
- Last verified: 2026-07-24 — Health and Restart run end to end; Recovery still `unverified` (see
  above).
