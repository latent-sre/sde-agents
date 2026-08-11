#!/usr/bin/env python3
"""Codex transport for deterministic behavioral-contract sessions.

Codex CLI does not expose a main-session ``--agent`` selector. This adapter therefore projects
the exact ``developer_instructions`` from one generated ``.codex/agents/<name>.toml`` into a
single main session. It is intentionally narrower than the Claude transport: only direct-agent
cases with an explicit empty Claude tool allowlist are eligible. Codex 0.147 cannot remove every
model-visible code-mode tool or report every attempted custom call, so this transport requests
disabled built-in execution, refuses configured MCP at the batch boundaries, rejects observable
tool events, and records the remaining limitation instead of claiming empty-allowlist parity.
Unsupported authority fails before a model session starts.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path

CODEX = shutil.which("codex")
SUPPORTED_CLI_VERSION = "codex-cli 0.147.0"
SUBSCRIPTION_BASE_URL = "https://chatgpt.com/backend-api/codex"
SUBSCRIPTION_CONFIG_OVERRIDES = (
    'model_provider="openai"',
    f'openai_base_url="{SUBSCRIPTION_BASE_URL}"',
    'forced_login_method="chatgpt"',
    'cli_auth_credentials_store="file"',
)
_SUBSCRIPTION_CONFIG_ARGS = tuple(
    item
    for setting in SUBSCRIPTION_CONFIG_OVERRIDES
    for item in ("-c", setting)
)

_AGENT_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PROFILE_FIELDS = frozenset({
    "name", "description", "sandbox_mode", "developer_instructions",
})
DISABLED_FEATURES = (
    "apps",
    "auth_elicitation",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "code_mode_host",
    "computer_use",
    "default_mode_request_user_input",
    "goals",
    "hooks",
    "image_generation",
    "in_app_browser",
    "memories",
    "multi_agent",
    "plugins",
    "remote_plugin",
    "request_permissions_tool",
    "shell_tool",
    "skill_search",
    "tool_suggest",
    "tool_call_mcp_elicitation",
    "view_image",
)
_UNAVAILABLE_MARKERS = (
    "authentication failed",
    "not logged in",
    "login required",
    "unauthorized",
    "insufficient_quota",
    "rate limit",
    "usage limit",
    "model access",
    "model is not available",
    "model not available",
    "not entitled",
)

ReadFile = Callable[[Path], bytes]
GitIdentity = Callable[[Path], tuple[str | None, bool | None]]


class CodexRuntimeError(RuntimeError):
    """A Codex case or generated profile cannot be represented faithfully."""


class SessionUnavailable(RuntimeError):
    """Subscription authentication, entitlement, or capacity invalidated the batch."""


def _bare_agent(qualified_agent: object) -> str:
    if not isinstance(qualified_agent, str) or not qualified_agent.startswith("sde-agents:"):
        raise CodexRuntimeError(
            "Codex generated-role projection requires a direct agent named "
            "'sde-agents:<agent>'"
        )
    bare = qualified_agent.split(":", 1)[1]
    if not _AGENT_NAME.fullmatch(bare):
        raise CodexRuntimeError(f"invalid generated Codex agent name: {qualified_agent!r}")
    return bare


def profile_relative_path(qualified_agent: object) -> str:
    """Return the only generated profile path a qualified agent may select."""
    return f".codex/agents/{_bare_agent(qualified_agent)}.toml"


def _default_read_file(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CodexRuntimeError(f"cannot read generated Codex profile {path}: {exc}") from exc


def _parse_profile(content: bytes, expected_name: str, path: Path) -> dict[str, str]:
    try:
        document = tomllib.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise CodexRuntimeError(f"invalid generated Codex profile {path}: {exc}") from exc
    extra = sorted(set(document) - _PROFILE_FIELDS)
    missing = sorted(_PROFILE_FIELDS - set(document))
    if extra:
        raise CodexRuntimeError(
            f"generated Codex profile {path} has unsupported field(s): {', '.join(extra)}"
        )
    if missing:
        raise CodexRuntimeError(
            f"generated Codex profile {path} is missing field(s): {', '.join(missing)}"
        )
    if document["name"] != expected_name:
        raise CodexRuntimeError(
            f"generated Codex profile name {document['name']!r} does not match "
            f"selected agent {expected_name!r}"
        )
    for field in ("description", "developer_instructions"):
        if not isinstance(document[field], str) or not document[field].strip():
            raise CodexRuntimeError(
                f"generated Codex profile {path} has an empty or non-string {field!r}"
            )
    if (
        not isinstance(document["sandbox_mode"], str)
        or document["sandbox_mode"] not in {"read-only", "workspace-write"}
    ):
        raise CodexRuntimeError(
            f"generated Codex profile {path} requests unsupported sandbox_mode "
            f"{document['sandbox_mode']!r}"
        )
    return {field: document[field] for field in _PROFILE_FIELDS}


def validate_case_projection(case: Mapping[str, object]) -> str:
    """Return the bare role name, or refuse cases outside the bounded Codex lane."""
    name = _bare_agent(case.get("agent"))
    if case.get("allowed_tools") != []:
        raise CodexRuntimeError(
            f"case {case.get('id')!r}: Codex projection requires explicit empty allowed_tools"
        )
    if case.get("permission_mode") is not None:
        raise CodexRuntimeError(
            f"case {case.get('id')!r}: Codex projection cannot represent permission_mode"
        )
    return name


def _failure_codes(value: object) -> set[str]:
    """Collect wire discriminators only from an event already classified as failure."""
    codes: set[str] = set()
    if isinstance(value, dict):
        for field in ("code", "type"):
            code = value.get(field)
            if isinstance(code, str):
                codes.add(code.lower())
        for child in value.values():
            codes.update(_failure_codes(child))
    elif isinstance(value, list):
        for child in value:
            codes.update(_failure_codes(child))
    return codes


def _code_mode_fail_closed_warning(item: Mapping[str, object]) -> bool:
    message = item.get("message")
    if not isinstance(message, str):
        return False
    lowered = message.lower()
    return "code mode is unavailable" in lowered and "fail closed" in lowered


def parse_jsonl(text: str) -> dict[str, object]:
    """Parse exact Codex 0.147 event paths without grading nested diagnostic text."""
    events: list[dict[str, object]] = []
    models: set[str] = set()
    messages: list[str] = []
    usage: dict[str, object] | None = None
    completed = False
    failed = False
    failure_events: list[str] = []
    error_codes: set[str] = set()
    tool_attempts: set[str] = set()
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        events.append(event)
        event_type = event.get("type")
        model = event.get("model")
        if isinstance(model, str) and model.startswith("gpt-"):
            models.add(model)
        if event_type == "turn.completed":
            completed = True
            event_usage = event.get("usage")
            if isinstance(event_usage, dict):
                usage = dict(event_usage)
        elif event_type in {"turn.failed", "item.failed", "error"}:
            failed = True
            failure_events.append(json.dumps(event, sort_keys=True, ensure_ascii=False))
            error_codes.update(_failure_codes(event))
        if event_type not in {"item.started", "item.updated", "item.completed"}:
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "agent_message":
            # Only a completed agent message is eligible as the final contract response.
            if event_type == "item.completed" and isinstance(item.get("text"), str):
                messages.append(item["text"])
        elif item_type == "reasoning":
            continue
        elif item_type == "error":
            if event_type == "item.completed" and _code_mode_fail_closed_warning(item):
                continue
            else:
                failed = True
                failure_events.append(json.dumps(event, sort_keys=True, ensure_ascii=False))
                error_codes.update(_failure_codes(item))
        elif isinstance(item_type, str):
            # Known 0.147 tool items and future item kinds both invalidate the run. Unknown
            # non-message items fail closed rather than gaining authority when the CLI evolves.
            tool_attempts.add(item_type)
        else:
            tool_attempts.add("unknown-item")
    return {
        "events": len(events),
        "observed_models": sorted(models),
        "last_message": messages[-1] if messages else None,
        "usage": usage,
        "completed": completed,
        "failed": failed,
        "failure_text": "\n".join(failure_events),
        "error_codes": sorted(error_codes),
        "tool_attempts": sorted(tool_attempts),
    }


def build_command(
    executable: str,
    cwd: Path,
    *,
    model: str,
    reasoning_effort: str,
    developer_instructions: str,
) -> list[str]:
    """Build a tool-reduced, read-only generated-role projection command."""
    if not model or model != model.strip() or not reasoning_effort:
        raise CodexRuntimeError("Codex sessions require explicit model and reasoning effort")
    command = [
        executable,
        "-a", "never",  # Global on Codex 0.147; placing it after `exec` is rejected.
        "exec",
        "--cd", str(cwd),
        "--model", model,
        "--sandbox", "read-only",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "--skip-git-repo-check",
        "--color", "never",
    ]
    for feature in DISABLED_FEATURES:
        command += ["--disable", feature]
    command += [
        "-c", 'web_search="disabled"',
        "-c", f'model_reasoning_effort={json.dumps(reasoning_effort)}',
        *_SUBSCRIPTION_CONFIG_ARGS,
        "-c", "project_doc_max_bytes=0",
        "-c", "skills.include_instructions=false",
        "-c", "agents.enabled=false",
        "-c", "tools.update_plan.enabled=false",
        "-c", "developer_instructions=" + json.dumps(
            developer_instructions, ensure_ascii=False
        ),
        "-",  # Keep the task out of Windows' bounded command line; subprocess supplies stdin.
    ]
    return command


def _token(usage: object, field: str) -> int | None:
    value = usage.get(field) if isinstance(usage, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _stats(parsed: Mapping[str, object], duration_ms: int) -> dict[str, object]:
    observed = parsed["observed_models"]
    invalid = bool(parsed["failed"]) or bool(parsed["tool_attempts"])
    return {
        "input_tokens": _token(parsed.get("usage"), "input_tokens"),
        "output_tokens": _token(parsed.get("usage"), "output_tokens"),
        "duration_ms": duration_ms,
        "model": observed[0] if isinstance(observed, list) and len(observed) == 1 else None,
        "completed": bool(parsed["completed"]) and not invalid,
        "result_error": invalid,
    }


def _partial_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return ""


def _unavailable_code(code: str) -> bool:
    return (
        code == "usage_limit_reached"
        or (code.startswith("workspace_") and code.endswith("_usage_limit_reached"))
        or code.endswith("_credits_depleted")
    )


def _raise_if_unavailable(
    parsed: Mapping[str, object], diagnostics: str, stderr: str,
) -> None:
    codes = parsed.get("error_codes")
    if isinstance(codes, list) and any(
        isinstance(code, str) and _unavailable_code(code) for code in codes
    ):
        raise SessionUnavailable(
            "Codex subscription authentication, model access, or allowance is unavailable"
        )
    lowered = f"{parsed.get('failure_text', '')}\n{diagnostics}\n{stderr}".lower()
    if any(marker in lowered for marker in _UNAVAILABLE_MARKERS):
        raise SessionUnavailable(
            "Codex subscription authentication, model access, or rate limit is unavailable"
        )


def _diagnostic_lines(text: str) -> str:
    """Return non-event stdout diagnostics, excluding model-authored JSONL messages."""
    diagnostics: list[str] = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            diagnostics.append(line)
            continue
        if not isinstance(event, dict):
            diagnostics.append(line)
    return "\n".join(diagnostics)


def run_session(
    prompt: str,
    timeout: int,
    *,
    agent: str,
    developer_instructions: str,
    model: str,
    reasoning_effort: str,
    executable: str | None = None,
    scratch_root: Path | None = None,
) -> tuple[str, set[str], str | None, dict[str, object]]:
    """Run one captured Codex role; return the behavioral runner's shared result shape."""
    binary = executable or CODEX
    empty = {
        "input_tokens": None,
        "output_tokens": None,
        "duration_ms": None,
        "model": None,
        "completed": False,
        "result_error": False,
    }
    if binary is None:
        return "", set(), "the `codex` CLI is not on PATH", empty
    bare = _bare_agent(agent)
    root = scratch_root or (Path.home() / ".sde-agents" / "eval-scratch-codex")
    started = time.monotonic()
    try:
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="session-", dir=root) as temp_dir:
            cwd = Path(temp_dir)
            command = build_command(
                binary,
                cwd,
                model=model,
                reasoning_effort=reasoning_effort,
                developer_instructions=developer_instructions,
            )
            proc = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                cwd=cwd,
                timeout=timeout,
            )
    except subprocess.TimeoutExpired as exc:
        duration = round((time.monotonic() - started) * 1000)
        parsed = parse_jsonl(_partial_text(exc.stdout))
        stats = _stats(parsed, duration)
        return "", {bare}, f"timed out after {timeout}s before the session concluded", stats
    except (OSError, subprocess.SubprocessError) as exc:
        duration = round((time.monotonic() - started) * 1000)
        return "", {bare}, f"run failed: {exc}", {**empty, "duration_ms": duration}

    duration = round((time.monotonic() - started) * 1000)
    stdout, stderr = proc.stdout or "", proc.stderr or ""
    parsed = parse_jsonl(stdout)
    # A successful answer may legitimately discuss authentication or rate limits. Classify those
    # words only on a failed transport, never from contract output that would otherwise be graded.
    if proc.returncode != 0 or parsed["failed"]:
        _raise_if_unavailable(parsed, _diagnostic_lines(stdout), stderr)
    stats = _stats(parsed, duration)
    observed = parsed["observed_models"]
    if proc.returncode != 0:
        return "", {bare}, f"Codex exited {proc.returncode} before terminal success", stats
    if parsed["failed"]:
        return "", {bare}, "Codex emitted a failure event; error text was not graded", stats
    tool_attempts = parsed["tool_attempts"]
    if tool_attempts:
        return (
            "",
            {bare},
            "observable Codex tool activity invalidated the run: "
            + ", ".join(str(item) for item in tool_attempts),
            stats,
        )
    if not parsed["completed"]:
        return "", {bare}, "no turn.completed event was captured", stats
    if observed and (len(observed) != 1 or observed[0] != model):
        return "", {bare}, "observed model differs from the requested Codex model", stats
    final = parsed["last_message"]
    if not isinstance(final, str) or not final:
        return "", {bare}, "no completed agent_message was captured", stats
    return final, {bare}, None, stats


def capture_profiles(
    root: Path,
    qualified_agents: list[str],
    *,
    read_file: ReadFile | None = None,
    git_identity: GitIdentity | None = None,
) -> tuple[dict[str, dict[str, str]], dict[str, object]]:
    """Read selected profiles once and bind their exact in-memory contracts to an identity."""
    reader = read_file or _default_read_file
    files: dict[str, bytes] = {}
    profiles: dict[str, dict[str, str]] = {}
    for agent in sorted(set(qualified_agents)):
        relative = profile_relative_path(agent)
        content = reader(root / Path(relative))
        profiles[agent] = _parse_profile(
            content, _bare_agent(agent), root / Path(relative)
        )
        files[relative] = content
    if not files:
        raise CodexRuntimeError("Codex profile identity requires at least one selected agent")
    return profiles, _identity_from_files(root, files, git_identity)


def _identity_from_files(
    root: Path,
    files: Mapping[str, bytes],
    git_identity: GitIdentity | None,
) -> dict[str, object]:
    digest = hashlib.sha256()
    digest.update(b"sde-agents-codex-profile-content-v1\0")
    for relative in sorted(files):
        name = relative.encode("utf-8")
        content = files[relative]
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    git_head, git_dirty = git_identity(root) if git_identity else (None, None)
    return {
        "sha256": digest.hexdigest(),
        "files_hashed": len(files),
        "scope": {
            "strategy": "selected generated Codex agent profiles",
            "included": sorted(files),
            "excluded": ["all unselected repository paths"],
        },
        "git_head": git_head,
        "git_dirty": git_dirty,
        "git_scope": "containing worktree" if git_head is not None else None,
    }


def profile_identity(
    root: Path,
    qualified_agents: list[str],
    *,
    read_file: ReadFile | None = None,
    git_identity: GitIdentity | None = None,
) -> dict[str, object]:
    """Identify only the generated profiles selected by this batch."""
    return capture_profiles(
        root,
        qualified_agents,
        read_file=read_file,
        git_identity=git_identity,
    )[1]


def assert_clean_subscription_context(
    *, environ: Mapping[str, str] | None = None,
) -> None:
    """Refuse inputs that can alter role instructions or switch away from subscription auth."""
    environment = os.environ if environ is None else environ
    credential_overrides = [
        name
        for name in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN")
        if environment.get(name)
    ]
    if credential_overrides:
        raise CodexRuntimeError(
            "Codex subscription eval refuses API credential environment variable(s): "
            + ", ".join(credential_overrides)
        )
    configured = environment.get("CODEX_HOME")
    if not configured:
        raise CodexRuntimeError(
            "Codex behavioral eval requires an explicit dedicated CODEX_HOME"
        )
    if not Path(configured).is_absolute():
        raise CodexRuntimeError(
            "Codex behavioral eval requires an absolute CODEX_HOME so auth and sessions "
            "resolve the same home"
        )
    home = Path(configured)
    present = [
        name
        for name in ("AGENTS.override.md", "AGENTS.md", "config.toml")
        if os.path.lexists(home / name)
    ]
    if present:
        raise CodexRuntimeError(
            "Codex behavioral eval requires an instruction/config-clean CODEX_HOME; found "
            + ", ".join(present)
            + ". Use a dedicated CODEX_HOME with its own ChatGPT login."
        )
    if os.path.lexists(home / "managed_config.toml"):
        raise CodexRuntimeError(
            "Codex behavioral eval refuses CODEX_HOME/managed_config.toml because it outranks "
            "the subscription and tool-boundary session overrides"
        )


def assert_no_configured_mcp(executable: str) -> None:
    """Refuse configured MCP servers; this is a snapshot, not runtime-registry attestation."""
    try:
        proc = subprocess.run(
            [executable, *_SUBSCRIPTION_CONFIG_ARGS, "mcp", "list", "--json"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CodexRuntimeError("configured Codex MCP servers could not be checked") from exc
    if proc.returncode != 0:
        raise CodexRuntimeError("configured Codex MCP servers could not be checked")
    try:
        servers = json.loads(proc.stdout or "")
    except json.JSONDecodeError as exc:
        raise CodexRuntimeError("Codex MCP inventory was not valid JSON") from exc
    if not isinstance(servers, list):
        raise CodexRuntimeError("Codex MCP inventory was not a JSON list")
    if servers:
        raise CodexRuntimeError(
            f"Codex subscription eval refuses {len(servers)} configured MCP server(s)"
        )


def auth_provider_mode(executable: str) -> dict[str, str]:
    """Require ChatGPT subscription login and return only non-secret provenance."""
    try:
        proc = subprocess.run(
            [
                executable,
                *_SUBSCRIPTION_CONFIG_ARGS,
                "login",
                "status",
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise SessionUnavailable("Codex ChatGPT login status could not be checked") from exc
    diagnostic = f"{proc.stdout or ''}\n{proc.stderr or ''}".lower()
    if proc.returncode != 0 or "logged in using chatgpt" not in diagnostic:
        raise SessionUnavailable("Codex is not logged in using ChatGPT subscription access")
    return {"auth": "chatgpt", "provider": "openai"}


def cli_version(executable: str) -> str | None:
    """Return the local Codex CLI version without starting a model session."""
    try:
        proc = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return (proc.stdout or "").strip() or None


def require_supported_cli(executable: str) -> str:
    """Refuse before auth or spend when the parser/tool contract is not the pinned CLI."""
    observed = cli_version(executable)
    if observed != SUPPORTED_CLI_VERSION:
        raise CodexRuntimeError(
            f"Codex behavioral eval requires {SUPPORTED_CLI_VERSION}; observed "
            f"{observed or 'no version'}"
        )
    return observed
