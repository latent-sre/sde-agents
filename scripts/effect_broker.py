#!/usr/bin/env python3
"""Create, approve, and consume one-shot approvals bound to one exact subprocess effect."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

try:
    from scripts import evidence_envelope
except ModuleNotFoundError:
    import evidence_envelope  # type: ignore[no-redef]


SCHEMA_VERSION = 1
REQUEST_FIELDS = {
    "schema_version",
    "request_id",
    "action",
    "target",
    "argv",
    "cwd",
    "environment",
    "executable_sha256",
    "blast_radius",
    "rollback",
    "created_at",
    "expires_at",
    "timeout_seconds",
    "nonce",
    "context",
    "request_digest",
}
APPROVAL_FIELDS = {
    "schema_version",
    "approval_id",
    "request_id",
    "request_digest",
    "action",
    "target",
    "argv",
    "cwd",
    "environment",
    "executable_sha256",
    "expires_at",
    "timeout_seconds",
    "nonce",
    "context",
    "approved_at",
    "approver",
    "signature",
}
ACTION_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUEST_ID_RE = re.compile(r"^req_[0-9a-f]{32}$")
APPROVAL_ID_RE = re.compile(r"^approval_[0-9a-f]{32}$")
NONCE_RE = re.compile(r"^[0-9a-f]{64}$")
SHELL_EXECUTABLES = {
    "bash",
    "cmd",
    "cmd.exe",
    "dash",
    "fish",
    "ksh",
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
    "sh",
    "zsh",
}


class BrokerError(ValueError):
    pass


class ApprovalError(BrokerError):
    pass


class ReplayError(BrokerError):
    pass


@dataclass(frozen=True)
class ProcessResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool = False


Runner = Callable[[Sequence[str], Path, Mapping[str, str], int], ProcessResult]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    return evidence_envelope.format_timestamp(value)


def _parse_timestamp(value: object, field: str) -> datetime:
    return evidence_envelope.parse_timestamp(value, field)


def _canonical(value: Mapping[str, object]) -> bytes:
    return evidence_envelope.canonical_json(value)


def _payload_digest(request: Mapping[str, object]) -> str:
    payload = {key: value for key, value in request.items() if key != "request_digest"}
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _approval_payload(approval: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in approval.items() if key != "signature"}


def _path_outside_workspace(path: Path, workspace_root: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    workspace = workspace_root.expanduser().resolve()
    if resolved == workspace or resolved.is_relative_to(workspace):
        raise BrokerError(
            f"{label} must be outside the worker workspace; worker access would collapse the "
            "approval boundary"
        )
    return resolved


def _read_key(path: Path, workspace_root: Path) -> bytes:
    resolved = _path_outside_workspace(path, workspace_root, "approval key")
    if not resolved.is_file():
        raise BrokerError(f"approval key is not a regular file: {resolved}")
    key = resolved.read_bytes()
    if len(key) < 32:
        raise BrokerError("approval key must contain at least 32 bytes")
    if os.name != "nt" and resolved.stat().st_mode & 0o077:
        raise BrokerError("approval key must not be readable or writable by group/other")
    return key


def _validate_environment(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and key and isinstance(item, str)
        for key, item in value.items()
    ):
        raise BrokerError("environment must be an object of explicit string values")
    evidence_envelope._reject_sensitive_keys(value, "environment")
    return dict(value)


def _validate_context(value: object) -> dict[str, str | None]:
    if not isinstance(value, dict) or set(value) != {"run_id", "task_id", "attempt_id"}:
        raise BrokerError("context must contain exactly run_id, task_id, and attempt_id")
    result: dict[str, str | None] = {}
    for field, item in value.items():
        if item is not None and (
            not isinstance(item, str) or not evidence_envelope.CONTEXT_ID_RE.fullmatch(item)
        ):
            raise BrokerError(f"context.{field} has an invalid identifier")
        result[field] = item
    return result


def _validate_argv(value: object) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item and "\0" not in item for item in value)
    ):
        raise BrokerError("argv must be a non-empty array of strings without NUL bytes")
    executable = Path(value[0])
    if not executable.is_absolute():
        raise BrokerError("argv[0] must be an absolute executable path")
    if executable.name.lower() in SHELL_EXECUTABLES:
        raise BrokerError("shell interpreters are not valid effect-broker executables")
    return list(value)


def create_request(
    *,
    action: str,
    target: str,
    argv: Sequence[str],
    cwd: Path,
    blast_radius: str,
    rollback: str,
    expires_at: datetime,
    timeout_seconds: int,
    environment: Mapping[str, str] | None = None,
    run_id: str | None = None,
    task_id: str | None = None,
    attempt_id: str | None = None,
    now: Callable[[], datetime] = _now,
) -> dict[str, object]:
    created = now()
    executable = Path(argv[0]).expanduser().resolve() if argv else Path("")
    normalized_argv = [str(executable), *list(argv[1:])]
    if not executable.is_file():
        raise BrokerError(f"effect executable is not a regular file: {executable}")
    request: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "request_id": f"req_{uuid.uuid4().hex}",
        "action": action,
        "target": target,
        "argv": normalized_argv,
        "cwd": str(cwd.expanduser().resolve()),
        "environment": dict(environment or {}),
        "executable_sha256": evidence_envelope.sha256_file(executable),
        "blast_radius": blast_radius,
        "rollback": rollback,
        "created_at": _format_timestamp(created),
        "expires_at": _format_timestamp(expires_at),
        "timeout_seconds": timeout_seconds,
        "nonce": secrets.token_hex(32),
        "context": {
            "run_id": run_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
        },
    }
    request["request_digest"] = _payload_digest(request)
    validate_request(request, now=created)
    return request


def validate_request(
    request: Mapping[str, object],
    *,
    now: datetime | None = None,
    require_unexpired: bool = True,
) -> None:
    unknown = set(request) - REQUEST_FIELDS
    missing = REQUEST_FIELDS - set(request)
    if unknown or missing:
        raise BrokerError(
            f"request fields differ from schema; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if request["schema_version"] != SCHEMA_VERSION:
        raise BrokerError("unsupported effect request schema version")
    if not isinstance(request["request_id"], str) or not REQUEST_ID_RE.fullmatch(request["request_id"]):
        raise BrokerError("request_id is invalid")
    if not isinstance(request["action"], str) or not ACTION_RE.fullmatch(request["action"]):
        raise BrokerError("action must be kebab-case")
    for field in ("target", "blast_radius", "rollback"):
        if not isinstance(request[field], str) or not request[field].strip():
            raise BrokerError(f"{field} must be a non-empty string")
    argv = _validate_argv(request["argv"])
    executable = Path(argv[0])
    if not isinstance(request["cwd"], str) or not Path(request["cwd"]).is_absolute():
        raise BrokerError("cwd must be an absolute path")
    _validate_environment(request["environment"])
    if not isinstance(request["executable_sha256"], str) or not evidence_envelope.SHA256_RE.fullmatch(
        request["executable_sha256"]
    ):
        raise BrokerError("executable_sha256 is invalid")
    created = _parse_timestamp(request["created_at"], "created_at")
    expires = _parse_timestamp(request["expires_at"], "expires_at")
    if expires <= created:
        raise BrokerError("effect request must expire after it is created")
    if expires - created > timedelta(hours=24):
        raise BrokerError("effect request lifetime cannot exceed 24 hours")
    effective_now = now or _now()
    if require_unexpired and expires <= effective_now:
        raise ApprovalError("effect request has expired")
    if (
        not isinstance(request["timeout_seconds"], int)
        or isinstance(request["timeout_seconds"], bool)
        or not 1 <= request["timeout_seconds"] <= 3600
    ):
        raise BrokerError("timeout_seconds must be between 1 and 3600")
    if not isinstance(request["nonce"], str) or not NONCE_RE.fullmatch(request["nonce"]):
        raise BrokerError("request nonce is invalid")
    _validate_context(request["context"])
    if not isinstance(request["request_digest"], str) or not evidence_envelope.SHA256_RE.fullmatch(
        request["request_digest"]
    ):
        raise BrokerError("request_digest is invalid")
    if not hmac.compare_digest(request["request_digest"], _payload_digest(request)):
        raise ApprovalError("effect request digest does not match its content")
    if not executable.is_absolute():
        raise BrokerError("effect executable must be absolute")


def approve_request(
    request: Mapping[str, object],
    *,
    key: bytes,
    approver: str,
    now: Callable[[], datetime] = _now,
) -> dict[str, object]:
    approved_at = now()
    validate_request(request, now=approved_at)
    if len(key) < 32:
        raise BrokerError("approval key must contain at least 32 bytes")
    if not approver.strip():
        raise BrokerError("approver must be non-empty")
    approval: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "approval_id": f"approval_{uuid.uuid4().hex}",
        "request_id": request["request_id"],
        "request_digest": request["request_digest"],
        "action": request["action"],
        "target": request["target"],
        "argv": request["argv"],
        "cwd": request["cwd"],
        "environment": request["environment"],
        "executable_sha256": request["executable_sha256"],
        "expires_at": request["expires_at"],
        "timeout_seconds": request["timeout_seconds"],
        "nonce": request["nonce"],
        "context": request["context"],
        "approved_at": _format_timestamp(approved_at),
        "approver": approver,
    }
    approval["signature"] = hmac.new(
        key,
        _canonical(approval),
        hashlib.sha256,
    ).hexdigest()
    validate_approval(approval, request=request, key=key, now=approved_at)
    return approval


def validate_approval(
    approval: Mapping[str, object],
    *,
    request: Mapping[str, object],
    key: bytes,
    now: datetime | None = None,
) -> None:
    unknown = set(approval) - APPROVAL_FIELDS
    missing = APPROVAL_FIELDS - set(approval)
    if unknown or missing:
        raise ApprovalError(
            f"approval fields differ from schema; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if approval["schema_version"] != SCHEMA_VERSION:
        raise ApprovalError("unsupported approval schema version")
    if not isinstance(approval["approval_id"], str) or not APPROVAL_ID_RE.fullmatch(
        approval["approval_id"]
    ):
        raise ApprovalError("approval_id is invalid")
    validate_request(request, now=now)
    expected_fields = (
        "request_id",
        "request_digest",
        "action",
        "target",
        "argv",
        "cwd",
        "environment",
        "executable_sha256",
        "expires_at",
        "timeout_seconds",
        "nonce",
        "context",
    )
    drifted = [field for field in expected_fields if approval[field] != request[field]]
    if drifted:
        raise ApprovalError(f"approval does not match request fields: {drifted}")
    approved_at = _parse_timestamp(approval["approved_at"], "approved_at")
    if approved_at > _parse_timestamp(approval["expires_at"], "expires_at"):
        raise ApprovalError("approval was created after the request expired")
    if not isinstance(approval["approver"], str) or not approval["approver"].strip():
        raise ApprovalError("approver is invalid")
    if not isinstance(approval["signature"], str) or not evidence_envelope.SHA256_RE.fullmatch(
        approval["signature"]
    ):
        raise ApprovalError("approval signature is invalid")
    expected_signature = hmac.new(
        key,
        _canonical(_approval_payload(approval)),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(approval["signature"], expected_signature):
        raise ApprovalError("approval signature verification failed")


class ReplayLedger:
    def __init__(self, path: Path, workspace_root: Path) -> None:
        self.path = _path_outside_workspace(path, workspace_root, "approval replay ledger")

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS consumptions (
                        nonce TEXT PRIMARY KEY,
                        request_id TEXT NOT NULL,
                        request_digest TEXT NOT NULL,
                        approval_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        reserved_at TEXT NOT NULL,
                        finished_at TEXT,
                        returncode INTEGER,
                        evidence_id TEXT
                    )
                    """
                )

    def reserve(
        self,
        *,
        nonce: str,
        request_id: str,
        request_digest: str,
        approval_id: str,
        reserved_at: str,
    ) -> None:
        self.initialize()
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO consumptions(
                    nonce, request_id, request_digest, approval_id, status, reserved_at
                ) VALUES(?, ?, ?, ?, 'reserved', ?)
                """,
                (nonce, request_id, request_digest, approval_id, reserved_at),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise ReplayError("approval nonce has already been consumed or reserved") from exc
        finally:
            connection.close()

    def finish(
        self,
        *,
        nonce: str,
        status: str,
        finished_at: str,
        returncode: int | None,
        evidence_id: str,
    ) -> None:
        with closing(sqlite3.connect(self.path)) as connection:
            with connection:
                result = connection.execute(
                    """
                    UPDATE consumptions
                    SET status = ?, finished_at = ?, returncode = ?, evidence_id = ?
                    WHERE nonce = ? AND status = 'reserved'
                    """,
                    (status, finished_at, returncode, evidence_id, nonce),
                )
                if result.rowcount != 1:
                    raise ReplayError("reserved approval nonce could not be finalized")


def _run_effect(
    argv: Sequence[str],
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int,
) -> ProcessResult:
    try:
        result = subprocess.run(
            list(argv),
            cwd=cwd,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return ProcessResult(
            None,
            bytes(exc.stdout or b""),
            bytes(exc.stderr or b""),
            timed_out=True,
        )
    except OSError as exc:
        return ProcessResult(127, b"", str(exc).encode("utf-8", errors="replace"))
    return ProcessResult(result.returncode, result.stdout, result.stderr)


def execute_approved(
    request: Mapping[str, object],
    approval: Mapping[str, object],
    *,
    key: bytes,
    ledger: ReplayLedger,
    runner: Runner = _run_effect,
    now: Callable[[], datetime] = _now,
) -> dict[str, object]:
    started = now()
    validate_approval(approval, request=request, key=key, now=started)
    executable = Path(request["argv"][0])
    if not executable.is_file():
        raise ApprovalError(f"approved executable no longer exists: {executable}")
    observed_digest = evidence_envelope.sha256_file(executable)
    if not hmac.compare_digest(observed_digest, request["executable_sha256"]):
        raise ApprovalError("approved executable bytes changed after approval")
    cwd = Path(request["cwd"])
    if not cwd.is_dir():
        raise ApprovalError(f"approved cwd no longer exists: {cwd}")

    ledger.reserve(
        nonce=request["nonce"],
        request_id=request["request_id"],
        request_digest=request["request_digest"],
        approval_id=approval["approval_id"],
        reserved_at=_format_timestamp(started),
    )
    result = runner(
        request["argv"],
        cwd,
        _validate_environment(request["environment"]),
        request["timeout_seconds"],
    )
    ended = now()
    if result.timed_out:
        status = "inconclusive"
        ledger_status = "timed-out"
        limitations = ["approved effect timed out; partial external effects may remain"]
    elif result.returncode == 0:
        status = "pass"
        ledger_status = "executed"
        limitations = []
    else:
        status = "fail"
        ledger_status = "failed"
        limitations = [
            "a non-zero process result does not prove that the external effect was rolled back"
        ]
    context = _validate_context(request["context"])
    envelope = evidence_envelope.new_envelope(
        producer="effect_broker",
        role="approved-effect-executor",
        target_root=request["cwd"],
        target_revision=f"effect-request:{request['request_digest']}",
        criterion=f"execute approved {request['action']} against {request['target']}",
        status=status,
        started_at=started,
        ended_at=ended,
        command_argv=request["argv"],
        command_cwd=request["cwd"],
        exit_code=result.returncode,
        source={
            "kind": "effect-approval",
            "request_id": request["request_id"],
            "request_digest": request["request_digest"],
            "approval_id": approval["approval_id"],
            "approver": approval["approver"],
            "action": request["action"],
            "target": request["target"],
            "blast_radius": request["blast_radius"],
            "rollback": request["rollback"],
        },
        run_id=context["run_id"],
        task_id=context["task_id"],
        attempt_id=context["attempt_id"],
        environment={"execution": "direct-argv", "shell": False},
        isolation={"approval": "hmac-sha256", "one_shot_nonce": True},
        artifacts=(
            {
                "path": "captured-stdout.bin",
                "sha256": hashlib.sha256(result.stdout).hexdigest(),
                "size": len(result.stdout),
            },
            {
                "path": "captured-stderr.bin",
                "sha256": hashlib.sha256(result.stderr).hexdigest(),
                "size": len(result.stderr),
            },
        ),
        limitations=limitations,
    )
    ledger.finish(
        nonce=request["nonce"],
        status=ledger_status,
        finished_at=_format_timestamp(ended),
        returncode=result.returncode,
        evidence_id=envelope["evidence_id"],
    )
    return envelope


def _load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise BrokerError(f"JSON document must be an object: {path}")
    return data


def _parse_environment(entries: Sequence[str]) -> dict[str, str]:
    environment: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise BrokerError(f"environment entry must be KEY=VALUE: {entry!r}")
        key, value = entry.split("=", 1)
        if key in environment:
            raise BrokerError(f"duplicate environment key: {key}")
        environment[key] = value
    return _validate_environment(environment)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create")
    create.add_argument("--action", required=True)
    create.add_argument("--target", required=True)
    create.add_argument("--cwd", type=Path, required=True)
    create.add_argument("--blast-radius", required=True)
    create.add_argument("--rollback", required=True)
    create.add_argument("--expires-in", type=int, required=True, help="approval lifetime in seconds")
    create.add_argument("--timeout", type=int, default=300)
    create.add_argument("--env", action="append", default=[])
    create.add_argument("--run-id")
    create.add_argument("--task-id")
    create.add_argument("--attempt-id")
    create.add_argument("argv", nargs=argparse.REMAINDER)

    approve = commands.add_parser("approve")
    approve.add_argument("request", type=Path)
    approve.add_argument("--key-file", type=Path, required=True)
    approve.add_argument("--workspace-root", type=Path, required=True)
    approve.add_argument("--approver", required=True)

    execute = commands.add_parser("execute")
    execute.add_argument("request", type=Path)
    execute.add_argument("approval", type=Path)
    execute.add_argument("--key-file", type=Path, required=True)
    execute.add_argument("--ledger", type=Path, required=True)
    execute.add_argument("--workspace-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "create":
            command_argv = list(args.argv)
            if command_argv and command_argv[0] == "--":
                command_argv = command_argv[1:]
            result = create_request(
                action=args.action,
                target=args.target,
                argv=command_argv,
                cwd=args.cwd,
                blast_radius=args.blast_radius,
                rollback=args.rollback,
                expires_at=_now() + timedelta(seconds=args.expires_in),
                timeout_seconds=args.timeout,
                environment=_parse_environment(args.env),
                run_id=args.run_id,
                task_id=args.task_id,
                attempt_id=args.attempt_id,
            )
        elif args.command == "approve":
            request = _load_json(args.request)
            key = _read_key(args.key_file, args.workspace_root)
            result = approve_request(request, key=key, approver=args.approver)
        else:
            request = _load_json(args.request)
            approval = _load_json(args.approval)
            key = _read_key(args.key_file, args.workspace_root)
            ledger = ReplayLedger(args.ledger, args.workspace_root)
            result = execute_approved(request, approval, key=key, ledger=ledger)
    except (
        OSError,
        sqlite3.Error,
        json.JSONDecodeError,
        BrokerError,
        evidence_envelope.EnvelopeValidationError,
    ) as exc:
        print(f"effect-broker error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
