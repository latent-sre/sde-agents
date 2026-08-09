#!/usr/bin/env python3
"""Run one verification command in a pinned, networkless Docker or Podman sandbox.

Windows/Git Bash caveat: an MSYS shell converts argument strings that look like POSIX paths
(`/scratch/x.py`, `/workspace`) into Windows paths BEFORE this script or the engine sees them, so
the container receives argv naming paths that do not exist inside it and the command exits 2
("can't open file") while the sandbox itself looks healthy — the envelope faithfully records a
failing check that never actually ran. Field-proven 2026-08-09 (Git for Windows 2.53, Docker
29.6). From Git Bash, prefix the invocation with `MSYS_NO_PATHCONV=1` and pass host-side paths in
Windows form; PowerShell and cmd do not rewrite argv and need nothing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

try:
    from scripts import evidence_envelope
except ModuleNotFoundError:
    import evidence_envelope  # type: ignore[no-redef]


IMAGE_RE = re.compile(r"^[^\s]+@sha256:[0-9a-f]{64}$")
USER_RE = re.compile(r"^[1-9][0-9]*:[1-9][0-9]*$")
MEMORY_RE = re.compile(r"^[1-9][0-9]*(?:[bkmg])?$", re.IGNORECASE)
MAX_CAPTURE_BYTES = 1024 * 1024


class SandboxError(ValueError):
    pass


def _default_container_user() -> str:
    """Use the local non-root identity so a private host scratch directory stays writable."""

    if os.name != "nt" and hasattr(os, "geteuid") and hasattr(os, "getegid"):
        uid = os.geteuid()
        gid = os.getegid()
        if uid > 0 and gid > 0:
            return f"{uid}:{gid}"
    return "65532:65532"


@dataclass(frozen=True)
class ProcessResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    spawn_error: bool = False


@dataclass(frozen=True)
class SandboxConfig:
    engine: str
    image: str
    source: Path
    scratch: Path
    command: tuple[str, ...]
    timeout_seconds: int = 600
    cpus: float = 1.0
    memory: str = "1g"
    pids_limit: int = 256
    user: str = _default_container_user()


Runner = Callable[[Sequence[str], int, Mapping[str, str]], ProcessResult]


def _engine_environment() -> dict[str, str]:
    """Give the local engine only process-launch essentials, never inherited remote endpoints."""

    allowed = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
    return {key: os.environ[key] for key in allowed if key in os.environ}


def _run_process(argv: Sequence[str], timeout: int, environment: Mapping[str, str]) -> ProcessResult:
    try:
        result = subprocess.run(
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
            env=dict(environment),
        )
    except subprocess.TimeoutExpired as exc:
        return ProcessResult(
            None,
            bytes(exc.stdout or b""),
            bytes(exc.stderr or b""),
            timed_out=True,
        )
    except OSError as exc:
        return ProcessResult(
            127,
            b"",
            str(exc).encode("utf-8", errors="replace"),
            spawn_error=True,
        )
    return ProcessResult(result.returncode, result.stdout, result.stderr)


def _validate_config(config: SandboxConfig) -> SandboxConfig:
    engine_name = Path(config.engine).stem.lower()
    if engine_name not in {"docker", "podman"}:
        raise SandboxError("engine must resolve to docker or podman")
    if not IMAGE_RE.fullmatch(config.image) or config.image.startswith("-"):
        raise SandboxError("image must be an explicit name@sha256:<64 lowercase hex> reference")
    source = config.source.expanduser().resolve()
    scratch = config.scratch.expanduser().resolve()
    if not source.is_dir():
        raise SandboxError(f"source is not a directory: {source}")
    if scratch == source or scratch.is_relative_to(source):
        raise SandboxError("scratch must be outside the read-only source tree")
    if "," in str(source) or "," in str(scratch):
        raise SandboxError("source and scratch paths cannot contain commas in --mount syntax")
    if not config.command or not all(
        isinstance(item, str) and item and "\0" not in item for item in config.command
    ):
        raise SandboxError("command must be a non-empty argv sequence without NUL bytes")
    if not 1 <= config.timeout_seconds <= 86400:
        raise SandboxError("timeout_seconds must be between 1 and 86400")
    if not 0 < config.cpus <= 64:
        raise SandboxError("cpus must be greater than zero and at most 64")
    if not MEMORY_RE.fullmatch(config.memory):
        raise SandboxError("memory must be a positive Docker/Podman memory value such as 1g")
    if not 1 <= config.pids_limit <= 4096:
        raise SandboxError("pids_limit must be between 1 and 4096")
    if not USER_RE.fullmatch(config.user):
        raise SandboxError("user must be a non-root numeric uid:gid pair")
    scratch.mkdir(parents=True, exist_ok=True)
    if os.name != "nt" and hasattr(os, "geteuid"):
        uid, gid = (int(part) for part in config.user.split(":"))
        effective_uid = os.geteuid()
        effective_gid = os.getegid()
        if effective_uid == 0:
            os.chown(scratch, uid, gid)
            scratch.chmod(0o700)
        elif (uid, gid) != (effective_uid, effective_gid):
            raise SandboxError(
                "container user must match the non-root host uid:gid that owns scratch; "
                "a mismatched bind mount would make the advertised writable scratch unusable"
            )
    return SandboxConfig(
        engine=config.engine,
        image=config.image,
        source=source,
        scratch=scratch,
        command=config.command,
        timeout_seconds=config.timeout_seconds,
        cpus=config.cpus,
        memory=config.memory,
        pids_limit=config.pids_limit,
        user=config.user,
    )


def build_command(config: SandboxConfig, *, container_name: str) -> list[str]:
    config = _validate_config(config)
    if not re.fullmatch(r"sde-verify-[0-9a-f]{16}", container_name):
        raise SandboxError("container name is not a fleet-generated verification name")
    return [
        config.engine,
        "run",
        "--name",
        container_name,
        "--rm",
        "--pull",
        "never",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(config.pids_limit),
        "--memory",
        config.memory,
        "--cpus",
        str(config.cpus),
        "--user",
        config.user,
        "--mount",
        f"type=bind,src={config.source},dst=/workspace,readonly",
        "--mount",
        f"type=bind,src={config.scratch},dst=/scratch",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--workdir",
        "/workspace",
        "--env",
        "HOME=/scratch/home",
        "--env",
        "TMPDIR=/tmp",
        config.image,
        *config.command,
    ]


def _captured_artifact(name: str, content: bytes) -> dict[str, object]:
    return {
        "path": name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def _truncate(content: bytes) -> tuple[bytes, bool]:
    if len(content) <= MAX_CAPTURE_BYTES:
        return content, False
    return content[:MAX_CAPTURE_BYTES], True


def _no_such_container(result: ProcessResult) -> bool:
    message = (result.stdout + result.stderr).decode("utf-8", errors="replace").lower()
    return "no such container" in message or "no such object" in message


def execute(
    config: SandboxConfig,
    *,
    target_revision: str,
    criterion: str,
    run_id: str | None = None,
    task_id: str | None = None,
    attempt_id: str | None = None,
    runner: Runner = _run_process,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, object]:
    config = _validate_config(config)
    container_name = f"sde-verify-{secrets.token_hex(8)}"
    argv = build_command(config, container_name=container_name)
    environment = _engine_environment()
    started = now()
    result = runner(argv, config.timeout_seconds, environment)

    cleanup = runner(
        (config.engine, "rm", "--force", container_name),
        30,
        environment,
    )
    inspect = runner(
        (config.engine, "container", "inspect", container_name),
        30,
        environment,
    )
    if inspect.returncode == 0:
        residue = True
        residue_check = "container still exists after forced cleanup"
    elif _no_such_container(inspect):
        residue = False
        residue_check = "no container residue found"
    else:
        residue = None
        residue_check = "engine could not prove whether container residue remains"

    stdout, stdout_truncated = _truncate(result.stdout)
    stderr, stderr_truncated = _truncate(result.stderr)
    limitations: list[str] = []
    if stdout_truncated:
        limitations.append(f"stdout truncated to {MAX_CAPTURE_BYTES} bytes")
    if stderr_truncated:
        limitations.append(f"stderr truncated to {MAX_CAPTURE_BYTES} bytes")
    if result.timed_out:
        status = "inconclusive"
        limitations.append("verification timed out before a verdict")
    elif result.spawn_error:
        status = "inconclusive"
        limitations.append("container engine could not be started")
    elif result.returncode == 0:
        status = "pass"
    else:
        status = "fail"
    if residue is not False:
        status = "error"
        limitations.append(residue_check)
    if cleanup.returncode not in {0, 1, 125}:
        limitations.append(f"forced cleanup returned {cleanup.returncode}")

    ended = now()
    return evidence_envelope.new_envelope(
        producer="verification_sandbox",
        role="verification-engineer",
        target_root=str(config.source),
        target_revision=target_revision,
        criterion=criterion,
        status=status,
        started_at=started,
        ended_at=ended,
        command_argv=argv,
        command_cwd=str(config.source),
        exit_code=result.returncode,
        source={
            "kind": "container-verification",
            "container_name": container_name,
            "container_argv": list(config.command),
            "cleanup_returncode": cleanup.returncode,
            "residue": residue,
            "residue_check": residue_check,
        },
        run_id=run_id,
        task_id=task_id,
        attempt_id=attempt_id,
        environment={
            "engine": Path(config.engine).stem.lower(),
            "image": config.image,
        },
        isolation={
            "network": "none",
            "root_filesystem": "read-only",
            "source_mount": "read-only",
            "scratch_mount": "read-write",
            "capabilities": "dropped-all",
            "no_new_privileges": True,
            "user": config.user,
            "cpus": config.cpus,
            "memory": config.memory,
            "pids_limit": config.pids_limit,
            "pull": "never",
        },
        artifacts=(
            _captured_artifact("captured-stdout.bin", stdout),
            _captured_artifact("captured-stderr.bin", stderr),
        ),
        limitations=limitations,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("docker", "podman"), default="docker")
    parser.add_argument("--image", required=True)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--target-revision", required=True)
    parser.add_argument("--criterion", required=True)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--cpus", type=float, default=1.0)
    parser.add_argument("--memory", default="1g")
    parser.add_argument("--pids-limit", type=int, default=256)
    parser.add_argument("--user", default=_default_container_user())
    parser.add_argument("--run-id")
    parser.add_argument("--task-id")
    parser.add_argument("--attempt-id")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    executable = shutil.which(args.engine)
    if executable is None:
        print(f"verification sandbox error: {args.engine} is not on PATH", file=sys.stderr)
        return 2
    try:
        if args.scratch is not None:
            config = SandboxConfig(
                engine=executable,
                image=args.image,
                source=args.source,
                scratch=args.scratch,
                command=tuple(command),
                timeout_seconds=args.timeout,
                cpus=args.cpus,
                memory=args.memory,
                pids_limit=args.pids_limit,
                user=args.user,
            )
            envelope = execute(
                config,
                target_revision=args.target_revision,
                criterion=args.criterion,
                run_id=args.run_id,
                task_id=args.task_id,
                attempt_id=args.attempt_id,
            )
        else:
            with tempfile.TemporaryDirectory(prefix="sde-verification-") as temporary:
                config = SandboxConfig(
                    engine=executable,
                    image=args.image,
                    source=args.source,
                    scratch=Path(temporary),
                    command=tuple(command),
                    timeout_seconds=args.timeout,
                    cpus=args.cpus,
                    memory=args.memory,
                    pids_limit=args.pids_limit,
                    user=args.user,
                )
                envelope = execute(
                    config,
                    target_revision=args.target_revision,
                    criterion=args.criterion,
                    run_id=args.run_id,
                    task_id=args.task_id,
                    attempt_id=args.attempt_id,
                )
    except (OSError, SandboxError, evidence_envelope.EnvelopeValidationError) as exc:
        print(f"verification sandbox error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(envelope, indent=2, sort_keys=True))
    return 0 if envelope["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
