#!/usr/bin/env python3
"""Durable run/task/attempt state with leases, cancellation, and typed evidence links."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator, Mapping, Sequence

try:
    from scripts import evidence_envelope
except ModuleNotFoundError:
    import evidence_envelope  # type: ignore[no-redef]


SCHEMA_VERSION = 1
RUN_TERMINAL = {"complete", "cancelled", "superseded"}


class StateError(ValueError):
    pass


class StaleVersionError(StateError):
    pass


class LeaseError(StateError):
    pass


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise StateError("state timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _validate_id(value: str, field: str) -> str:
    if not evidence_envelope.CONTEXT_ID_RE.fullmatch(value):
        raise StateError(f"{field} has an invalid identifier")
    return value


# ``contract_digest`` names the contract a run was started under, and naming is all it does: the
# store requires it at creation, writes it to the run row, echoes it in the ``started`` event and
# in status output, and never reads it back. Nothing in this repository resolves a digest to a
# contract document — that is GRAPH-004, deferred — so this is a reserved forward-compatibility
# slot, never evidence that the named contract exists or matches. Shape is therefore the only
# promise the field can keep, and creation is the only place to keep it: the ``started`` event is
# append-only, so a malformed digest admitted here is permanent in the ledger and reads forever
# after as a binding no later resolver can match. Non-strings are rejected here rather than left
# to the regex, whose TypeError is an exception this module never raises and ``main`` does not
# catch — it would surface as a traceback instead of a run-state error.
def _validate_contract_digest(value: object) -> str:
    if not isinstance(value, str) or not evidence_envelope.SHA256_RE.fullmatch(value):
        raise StateError(
            "contract_digest must be a lowercase 64-character SHA-256 digest, not "
            f"{value!r}: nothing resolves this value, so an unchecked one is stored and echoed "
            "as a contract binding that no reader could ever match"
        )
    return value


def _outside_workspace(database: Path, workspace_root: Path) -> tuple[Path, Path]:
    database = database.expanduser().resolve()
    workspace_root = workspace_root.expanduser().resolve()
    if database == workspace_root or database.is_relative_to(workspace_root):
        raise StateError(
            "run-state database must be outside the worker workspace; a worker that can write its "
            "own leases or cancellation state can bypass the control plane"
        )
    return database, workspace_root


class StateStore:
    def __init__(
        self,
        database: Path,
        workspace_root: Path,
        *,
        now: Callable[[], datetime] = evidence_envelope.utc_now,
    ) -> None:
        self.database, self.workspace_root = _outside_workspace(database, workspace_root)
        self.now = now

    def initialize(self) -> None:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    input_revision TEXT NOT NULL,
                    contract_digest TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    reason TEXT,
                    superseded_by TEXT
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(run_id),
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    reason TEXT
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(task_id),
                    attempt_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    worker_id TEXT NOT NULL,
                    lease_token_hash TEXT NOT NULL,
                    lease_expires_at TEXT NOT NULL,
                    input_revision TEXT NOT NULL,
                    output_revision TEXT,
                    verdict TEXT,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    reason TEXT,
                    UNIQUE(task_id, attempt_number)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_attempt_per_task
                    ON attempts(task_id) WHERE status = 'active';
                CREATE TABLE IF NOT EXISTS evidence_links (
                    evidence_id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL REFERENCES attempts(attempt_id),
                    envelope_digest TEXT NOT NULL,
                    envelope_json TEXT NOT NULL,
                    attached_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS events_are_append_only_update
                    BEFORE UPDATE ON events BEGIN
                        SELECT RAISE(ABORT, 'events are append-only');
                    END;
                CREATE TRIGGER IF NOT EXISTS events_are_append_only_delete
                    BEFORE DELETE ON events BEGIN
                        SELECT RAISE(ABORT, 'events are append-only');
                    END;
                """
            )
            existing = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if existing is None:
                connection.execute(
                    "INSERT INTO metadata(key, value) VALUES('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )
            elif existing["value"] != str(SCHEMA_VERSION):
                raise StateError(
                    f"unsupported run-state schema version {existing['value']!r}"
                )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()

    def _event(
        self,
        connection: sqlite3.Connection,
        *,
        occurred_at: str,
        entity_type: str,
        entity_id: str,
        event_type: str,
        entity_version: int,
        payload: Mapping[str, object] | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO events(
                occurred_at, entity_type, entity_id, event_type, entity_version, payload_json
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                occurred_at,
                entity_type,
                entity_id,
                event_type,
                entity_version,
                json.dumps(payload or {}, sort_keys=True, separators=(",", ":")),
            ),
        )

    @staticmethod
    def _require_version(row: sqlite3.Row, expected: int, entity: str) -> None:
        if row["version"] != expected:
            raise StaleVersionError(
                f"stale {entity} version: expected {expected}, current {row['version']}"
            )

    @staticmethod
    def _row(connection: sqlite3.Connection, table: str, key: str, value: str) -> sqlite3.Row:
        row = connection.execute(f"SELECT * FROM {table} WHERE {key} = ?", (value,)).fetchone()
        if row is None:
            raise StateError(f"unknown {key}: {value}")
        return row

    def start_run(
        self,
        run_id: str,
        *,
        input_revision: str,
        contract_digest: str,
    ) -> dict[str, object]:
        _validate_id(run_id, "run_id")
        if not input_revision.strip():
            raise StateError("input_revision must be non-empty")
        _validate_contract_digest(contract_digest)
        now = _timestamp(self.now())
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO runs(
                    run_id, status, version, input_revision, contract_digest, created_at, updated_at
                ) VALUES(?, 'active', 0, ?, ?, ?, ?)
                """,
                (run_id, input_revision, contract_digest, now, now),
            )
            self._event(
                connection,
                occurred_at=now,
                entity_type="run",
                entity_id=run_id,
                event_type="started",
                entity_version=0,
                payload={"input_revision": input_revision, "contract_digest": contract_digest},
            )
        return self.status(run_id=run_id)["run"]

    def add_task(
        self,
        run_id: str,
        task_id: str,
        description: str,
        *,
        expected_run_version: int,
    ) -> dict[str, object]:
        _validate_id(run_id, "run_id")
        _validate_id(task_id, "task_id")
        if not description.strip():
            raise StateError("task description must be non-empty")
        now = _timestamp(self.now())
        with self._transaction() as connection:
            run = self._row(connection, "runs", "run_id", run_id)
            self._require_version(run, expected_run_version, "run")
            if run["status"] != "active":
                raise StateError(f"cannot add a task to run in status {run['status']!r}")
            connection.execute(
                """
                INSERT INTO tasks(
                    task_id, run_id, description, status, version, created_at, updated_at
                ) VALUES(?, ?, ?, 'pending', 0, ?, ?)
                """,
                (task_id, run_id, description, now, now),
            )
            new_run_version = run["version"] + 1
            connection.execute(
                "UPDATE runs SET version = ?, updated_at = ? WHERE run_id = ?",
                (new_run_version, now, run_id),
            )
            self._event(
                connection,
                occurred_at=now,
                entity_type="task",
                entity_id=task_id,
                event_type="added",
                entity_version=0,
                payload={"run_id": run_id, "description": description},
            )
            self._event(
                connection,
                occurred_at=now,
                entity_type="run",
                entity_id=run_id,
                event_type="task-added",
                entity_version=new_run_version,
                payload={"task_id": task_id},
            )
        return self.status(task_id=task_id)["task"]

    def _expire_active_attempt(
        self,
        connection: sqlite3.Connection,
        task: sqlite3.Row,
        now_value: datetime,
    ) -> sqlite3.Row:
        active = connection.execute(
            "SELECT * FROM attempts WHERE task_id = ? AND status = 'active'",
            (task["task_id"],),
        ).fetchone()
        if active is None or _parse_timestamp(active["lease_expires_at"]) > now_value:
            return task
        now = _timestamp(now_value)
        attempt_version = active["version"] + 1
        connection.execute(
            """
            UPDATE attempts
            SET status = 'expired', version = ?, updated_at = ?, completed_at = ?,
                reason = 'lease expired'
            WHERE attempt_id = ?
            """,
            (attempt_version, now, now, active["attempt_id"]),
        )
        task_version = task["version"] + 1
        connection.execute(
            "UPDATE tasks SET status = 'pending', version = ?, updated_at = ? WHERE task_id = ?",
            (task_version, now, task["task_id"]),
        )
        self._event(
            connection,
            occurred_at=now,
            entity_type="attempt",
            entity_id=active["attempt_id"],
            event_type="lease-expired",
            entity_version=attempt_version,
        )
        return self._row(connection, "tasks", "task_id", task["task_id"])

    def claim_task(
        self,
        task_id: str,
        attempt_id: str,
        *,
        worker_id: str,
        lease_seconds: int,
        expected_task_version: int,
        input_revision: str,
    ) -> dict[str, object]:
        _validate_id(task_id, "task_id")
        _validate_id(attempt_id, "attempt_id")
        _validate_id(worker_id, "worker_id")
        if lease_seconds <= 0:
            raise StateError("lease_seconds must be positive")
        if not input_revision.strip():
            raise StateError("input_revision must be non-empty")
        now_value = self.now()
        now = _timestamp(now_value)
        expires = _timestamp(now_value + timedelta(seconds=lease_seconds))
        lease_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(lease_token.encode("utf-8")).hexdigest()
        with self._transaction() as connection:
            task = self._row(connection, "tasks", "task_id", task_id)
            self._require_version(task, expected_task_version, "task")
            run = self._row(connection, "runs", "run_id", task["run_id"])
            if run["status"] != "active":
                raise StateError(f"cannot claim task from run in status {run['status']!r}")
            task = self._expire_active_attempt(connection, task, now_value)
            if task["status"] not in {"pending", "failed"}:
                raise StateError(f"cannot claim task in status {task['status']!r}")
            next_number = connection.execute(
                "SELECT COALESCE(MAX(attempt_number), 0) + 1 AS value FROM attempts WHERE task_id = ?",
                (task_id,),
            ).fetchone()["value"]
            connection.execute(
                """
                INSERT INTO attempts(
                    attempt_id, task_id, attempt_number, status, version, worker_id,
                    lease_token_hash, lease_expires_at, input_revision, started_at, updated_at
                ) VALUES(?, ?, ?, 'active', 0, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    task_id,
                    next_number,
                    worker_id,
                    token_hash,
                    expires,
                    input_revision,
                    now,
                    now,
                ),
            )
            task_version = task["version"] + 1
            connection.execute(
                "UPDATE tasks SET status = 'leased', version = ?, updated_at = ? WHERE task_id = ?",
                (task_version, now, task_id),
            )
            self._event(
                connection,
                occurred_at=now,
                entity_type="attempt",
                entity_id=attempt_id,
                event_type="claimed",
                entity_version=0,
                payload={
                    "task_id": task_id,
                    "worker_id": worker_id,
                    "lease_expires_at": expires,
                    "attempt_number": next_number,
                },
            )
        return {
            "attempt_id": attempt_id,
            "task_id": task_id,
            "attempt_number": next_number,
            "lease_token": lease_token,
            "lease_expires_at": expires,
            "attempt_version": 0,
            "task_version": task_version,
        }

    @staticmethod
    def _verify_lease(attempt: sqlite3.Row, lease_token: str, now_value: datetime) -> None:
        supplied_hash = hashlib.sha256(lease_token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(attempt["lease_token_hash"], supplied_hash):
            raise LeaseError("lease token does not match the active attempt")
        if _parse_timestamp(attempt["lease_expires_at"]) <= now_value:
            raise LeaseError("attempt lease has expired")

    def heartbeat(
        self,
        attempt_id: str,
        *,
        lease_token: str,
        extend_seconds: int,
        expected_attempt_version: int,
    ) -> dict[str, object]:
        if extend_seconds <= 0:
            raise StateError("extend_seconds must be positive")
        now_value = self.now()
        now = _timestamp(now_value)
        expires = _timestamp(now_value + timedelta(seconds=extend_seconds))
        with self._transaction() as connection:
            attempt = self._row(connection, "attempts", "attempt_id", attempt_id)
            self._require_version(attempt, expected_attempt_version, "attempt")
            if attempt["status"] != "active":
                raise LeaseError(f"cannot heartbeat attempt in status {attempt['status']!r}")
            self._verify_lease(attempt, lease_token, now_value)
            task = self._row(connection, "tasks", "task_id", attempt["task_id"])
            run = self._row(connection, "runs", "run_id", task["run_id"])
            if run["status"] != "active" or task["status"] != "leased":
                raise LeaseError("run or task no longer accepts heartbeats")
            version = attempt["version"] + 1
            connection.execute(
                """
                UPDATE attempts SET version = ?, lease_expires_at = ?, updated_at = ?
                WHERE attempt_id = ?
                """,
                (version, expires, now, attempt_id),
            )
            self._event(
                connection,
                occurred_at=now,
                entity_type="attempt",
                entity_id=attempt_id,
                event_type="heartbeat",
                entity_version=version,
                payload={"lease_expires_at": expires},
            )
        return {"attempt_id": attempt_id, "version": version, "lease_expires_at": expires}

    @staticmethod
    def _validate_evidence_context(
        envelope: Mapping[str, object],
        *,
        run_id: str,
        task_id: str,
        attempt_id: str,
        target_revision: str,
    ) -> None:
        evidence_envelope.validate_envelope(envelope)
        context = envelope["context"]
        expected = {"run_id": run_id, "task_id": task_id, "attempt_id": attempt_id}
        if any(context[key] != value for key, value in expected.items()):
            raise StateError(
                "evidence context does not match the run/task/attempt being completed"
            )
        if envelope["target"]["revision"] != target_revision:
            raise StateError(
                "evidence target revision does not match the attempt output revision"
            )

    def complete_attempt(
        self,
        attempt_id: str,
        *,
        lease_token: str,
        verdict: str,
        output_revision: str,
        evidence: Sequence[Mapping[str, object]],
        expected_attempt_version: int,
        reason: str | None = None,
    ) -> dict[str, object]:
        if verdict not in {"completed", "failed"}:
            raise StateError("attempt verdict must be 'completed' or 'failed'")
        if not output_revision.strip():
            raise StateError("output_revision must be non-empty")
        if not evidence:
            raise StateError("attempt completion requires at least one typed evidence envelope")
        now_value = self.now()
        now = _timestamp(now_value)
        with self._transaction() as connection:
            attempt = self._row(connection, "attempts", "attempt_id", attempt_id)
            self._require_version(attempt, expected_attempt_version, "attempt")
            if attempt["status"] != "active":
                raise LeaseError(f"cannot complete attempt in status {attempt['status']!r}")
            self._verify_lease(attempt, lease_token, now_value)
            task = self._row(connection, "tasks", "task_id", attempt["task_id"])
            run = self._row(connection, "runs", "run_id", task["run_id"])
            if run["status"] != "active" or task["status"] != "leased":
                raise StateError("cancelled or superseded work cannot complete")

            for envelope in evidence:
                self._validate_evidence_context(
                    envelope,
                    run_id=run["run_id"],
                    task_id=task["task_id"],
                    attempt_id=attempt_id,
                    target_revision=output_revision,
                )
                if verdict == "completed" and envelope["status"] != "pass":
                    raise StateError(
                        "a completed attempt requires pass evidence for every attached criterion"
                    )
                encoded = evidence_envelope.canonical_json(envelope)
                connection.execute(
                    """
                    INSERT INTO evidence_links(
                        evidence_id, attempt_id, envelope_digest, envelope_json, attached_at
                    ) VALUES(?, ?, ?, ?, ?)
                    """,
                    (
                        envelope["evidence_id"],
                        attempt_id,
                        hashlib.sha256(encoded).hexdigest(),
                        encoded.decode("utf-8"),
                        now,
                    ),
                )

            attempt_version = attempt["version"] + 1
            connection.execute(
                """
                UPDATE attempts
                SET status = ?, version = ?, output_revision = ?, verdict = ?, updated_at = ?,
                    completed_at = ?, reason = ?
                WHERE attempt_id = ?
                """,
                (
                    verdict,
                    attempt_version,
                    output_revision,
                    verdict,
                    now,
                    now,
                    reason,
                    attempt_id,
                ),
            )
            task_status = "completed" if verdict == "completed" else "failed"
            task_version = task["version"] + 1
            connection.execute(
                "UPDATE tasks SET status = ?, version = ?, updated_at = ?, reason = ? WHERE task_id = ?",
                (task_status, task_version, now, reason, task["task_id"]),
            )
            self._event(
                connection,
                occurred_at=now,
                entity_type="attempt",
                entity_id=attempt_id,
                event_type=verdict,
                entity_version=attempt_version,
                payload={
                    "output_revision": output_revision,
                    "evidence_ids": [item["evidence_id"] for item in evidence],
                    "reason": reason,
                },
            )
        return self.status(attempt_id=attempt_id)["attempt"]

    def _terminate_run(
        self,
        run_id: str,
        *,
        status: str,
        reason: str,
        expected_run_version: int,
        superseded_by: str | None = None,
    ) -> dict[str, object]:
        if status not in {"cancelled", "superseded"}:
            raise StateError("invalid terminating run status")
        if not reason.strip():
            raise StateError("termination reason must be non-empty")
        if superseded_by is not None:
            _validate_id(superseded_by, "superseded_by")
        now = _timestamp(self.now())
        with self._transaction() as connection:
            run = self._row(connection, "runs", "run_id", run_id)
            self._require_version(run, expected_run_version, "run")
            if run["status"] in RUN_TERMINAL:
                raise StateError(f"run is already terminal: {run['status']}")
            version = run["version"] + 1
            connection.execute(
                """
                UPDATE runs
                SET status = ?, version = ?, updated_at = ?, reason = ?, superseded_by = ?
                WHERE run_id = ?
                """,
                (status, version, now, reason, superseded_by, run_id),
            )
            attempt_status = "cancelled" if status == "cancelled" else "superseded"
            active_attempts = connection.execute(
                """
                SELECT attempts.* FROM attempts
                JOIN tasks ON tasks.task_id = attempts.task_id
                WHERE tasks.run_id = ? AND attempts.status = 'active'
                """,
                (run_id,),
            ).fetchall()
            for attempt in active_attempts:
                attempt_version = attempt["version"] + 1
                connection.execute(
                    """
                    UPDATE attempts
                    SET status = ?, version = ?, updated_at = ?, completed_at = ?, reason = ?
                    WHERE attempt_id = ?
                    """,
                    (attempt_status, attempt_version, now, now, reason, attempt["attempt_id"]),
                )
                self._event(
                    connection,
                    occurred_at=now,
                    entity_type="attempt",
                    entity_id=attempt["attempt_id"],
                    event_type=attempt_status,
                    entity_version=attempt_version,
                    payload={"run_id": run_id, "reason": reason},
                )
            tasks = connection.execute(
                "SELECT * FROM tasks WHERE run_id = ? AND status NOT IN ('completed', 'cancelled', 'superseded')",
                (run_id,),
            ).fetchall()
            for task in tasks:
                task_version = task["version"] + 1
                connection.execute(
                    "UPDATE tasks SET status = ?, version = ?, updated_at = ?, reason = ? WHERE task_id = ?",
                    (attempt_status, task_version, now, reason, task["task_id"]),
                )
            self._event(
                connection,
                occurred_at=now,
                entity_type="run",
                entity_id=run_id,
                event_type=status,
                entity_version=version,
                payload={"reason": reason, "superseded_by": superseded_by},
            )
        return self.status(run_id=run_id)["run"]

    def cancel_run(
        self,
        run_id: str,
        *,
        reason: str,
        expected_run_version: int,
    ) -> dict[str, object]:
        return self._terminate_run(
            run_id,
            status="cancelled",
            reason=reason,
            expected_run_version=expected_run_version,
        )

    def supersede_run(
        self,
        run_id: str,
        *,
        superseded_by: str,
        reason: str,
        expected_run_version: int,
    ) -> dict[str, object]:
        return self._terminate_run(
            run_id,
            status="superseded",
            reason=reason,
            expected_run_version=expected_run_version,
            superseded_by=superseded_by,
        )

    def complete_run(self, run_id: str, *, expected_run_version: int) -> dict[str, object]:
        now = _timestamp(self.now())
        with self._transaction() as connection:
            run = self._row(connection, "runs", "run_id", run_id)
            self._require_version(run, expected_run_version, "run")
            if run["status"] != "active":
                raise StateError(f"cannot complete run in status {run['status']!r}")
            counts = connection.execute(
                "SELECT status, COUNT(*) AS count FROM tasks WHERE run_id = ? GROUP BY status",
                (run_id,),
            ).fetchall()
            if not counts:
                raise StateError("cannot complete a run with no tasks")
            unfinished = {row["status"]: row["count"] for row in counts if row["status"] != "completed"}
            if unfinished:
                raise StateError(f"cannot complete run with unfinished tasks: {unfinished}")
            version = run["version"] + 1
            connection.execute(
                "UPDATE runs SET status = 'complete', version = ?, updated_at = ? WHERE run_id = ?",
                (version, now, run_id),
            )
            self._event(
                connection,
                occurred_at=now,
                entity_type="run",
                entity_id=run_id,
                event_type="completed",
                entity_version=version,
            )
        return self.status(run_id=run_id)["run"]

    def status(
        self,
        *,
        run_id: str | None = None,
        task_id: str | None = None,
        attempt_id: str | None = None,
    ) -> dict[str, object]:
        requested = sum(value is not None for value in (run_id, task_id, attempt_id))
        if requested != 1:
            raise StateError("status requires exactly one of run_id, task_id, or attempt_id")
        with self._connect() as connection:
            if run_id is not None:
                run = dict(self._row(connection, "runs", "run_id", run_id))
                tasks = [dict(row) for row in connection.execute(
                    "SELECT * FROM tasks WHERE run_id = ? ORDER BY created_at, task_id", (run_id,)
                )]
                return {"run": run, "tasks": tasks}
            if task_id is not None:
                task = dict(self._row(connection, "tasks", "task_id", task_id))
                attempts = [dict(row) for row in connection.execute(
                    "SELECT * FROM attempts WHERE task_id = ? ORDER BY attempt_number", (task_id,)
                )]
                for attempt in attempts:
                    attempt.pop("lease_token_hash", None)
                return {"task": task, "attempts": attempts}
            attempt = dict(self._row(connection, "attempts", "attempt_id", attempt_id))
            attempt.pop("lease_token_hash", None)
            evidence = [dict(row) for row in connection.execute(
                """
                SELECT evidence_id, envelope_digest, attached_at
                FROM evidence_links WHERE attempt_id = ? ORDER BY evidence_id
                """,
                (attempt_id,),
            )]
            return {"attempt": attempt, "evidence": evidence}


def _read_envelopes(paths: Sequence[Path]) -> list[Mapping[str, object]]:
    envelopes: list[Mapping[str, object]] = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise StateError(f"evidence is not a JSON object: {path}")
        evidence_envelope.validate_envelope(data)
        envelopes.append(data)
    return envelopes


def _read_lease_token() -> str:
    token = sys.stdin.readline().strip()
    if not token:
        raise StateError("lease token must be supplied on stdin")
    return token


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--workspace-root", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init")
    start = commands.add_parser("start-run")
    start.add_argument("run_id")
    start.add_argument("--input-revision", required=True)
    start.add_argument(
        "--contract-digest",
        required=True,
        help="lowercase 64-character SHA-256 naming the contract this run is started under; "
        "recorded and echoed, resolved by nothing",
    )

    add = commands.add_parser("add-task")
    add.add_argument("run_id")
    add.add_argument("task_id")
    add.add_argument("description")
    add.add_argument("--expected-version", type=int, required=True)

    claim = commands.add_parser("claim")
    claim.add_argument("task_id")
    claim.add_argument("attempt_id")
    claim.add_argument("--worker-id", required=True)
    claim.add_argument("--lease-seconds", type=int, required=True)
    claim.add_argument("--input-revision", required=True)
    claim.add_argument("--expected-version", type=int, required=True)

    heartbeat = commands.add_parser("heartbeat")
    heartbeat.add_argument("attempt_id")
    heartbeat.add_argument("--extend-seconds", type=int, required=True)
    heartbeat.add_argument("--expected-version", type=int, required=True)

    complete = commands.add_parser("complete-attempt")
    complete.add_argument("attempt_id")
    complete.add_argument("--verdict", choices=("completed", "failed"), required=True)
    complete.add_argument("--output-revision", required=True)
    complete.add_argument("--evidence", type=Path, action="append", default=[])
    complete.add_argument("--reason")
    complete.add_argument("--expected-version", type=int, required=True)

    cancel = commands.add_parser("cancel-run")
    cancel.add_argument("run_id")
    cancel.add_argument("reason")
    cancel.add_argument("--expected-version", type=int, required=True)

    supersede = commands.add_parser("supersede-run")
    supersede.add_argument("run_id")
    supersede.add_argument("superseded_by")
    supersede.add_argument("reason")
    supersede.add_argument("--expected-version", type=int, required=True)

    finish = commands.add_parser("complete-run")
    finish.add_argument("run_id")
    finish.add_argument("--expected-version", type=int, required=True)

    status = commands.add_parser("status")
    target = status.add_mutually_exclusive_group(required=True)
    target.add_argument("--run-id")
    target.add_argument("--task-id")
    target.add_argument("--attempt-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        store = StateStore(args.db, args.workspace_root)
        if args.command == "init":
            store.initialize()
            result: object = {"initialized": str(store.database)}
        else:
            store.initialize()
            if args.command == "start-run":
                result = store.start_run(
                    args.run_id,
                    input_revision=args.input_revision,
                    contract_digest=args.contract_digest,
                )
            elif args.command == "add-task":
                result = store.add_task(
                    args.run_id,
                    args.task_id,
                    args.description,
                    expected_run_version=args.expected_version,
                )
            elif args.command == "claim":
                result = store.claim_task(
                    args.task_id,
                    args.attempt_id,
                    worker_id=args.worker_id,
                    lease_seconds=args.lease_seconds,
                    expected_task_version=args.expected_version,
                    input_revision=args.input_revision,
                )
            elif args.command == "heartbeat":
                result = store.heartbeat(
                    args.attempt_id,
                    lease_token=_read_lease_token(),
                    extend_seconds=args.extend_seconds,
                    expected_attempt_version=args.expected_version,
                )
            elif args.command == "complete-attempt":
                result = store.complete_attempt(
                    args.attempt_id,
                    lease_token=_read_lease_token(),
                    verdict=args.verdict,
                    output_revision=args.output_revision,
                    evidence=_read_envelopes(args.evidence),
                    expected_attempt_version=args.expected_version,
                    reason=args.reason,
                )
            elif args.command == "cancel-run":
                result = store.cancel_run(
                    args.run_id,
                    reason=args.reason,
                    expected_run_version=args.expected_version,
                )
            elif args.command == "supersede-run":
                result = store.supersede_run(
                    args.run_id,
                    superseded_by=args.superseded_by,
                    reason=args.reason,
                    expected_run_version=args.expected_version,
                )
            elif args.command == "complete-run":
                result = store.complete_run(
                    args.run_id,
                    expected_run_version=args.expected_version,
                )
            else:
                result = store.status(
                    run_id=args.run_id,
                    task_id=args.task_id,
                    attempt_id=args.attempt_id,
                )
    except (OSError, sqlite3.Error, json.JSONDecodeError, StateError, ValueError) as exc:
        print(f"run-state error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
