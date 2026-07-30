#!/usr/bin/env python3
"""Clean-room support for model-driven plugin evals.

`claude -p` normally inherits personal agents, skills, plugins, settings, and CLAUDE.md. That makes
an eval describe the operator's machine rather than the plugin under test. This module relocates the
Claude configuration to a temporary directory containing only authentication material and refuses
to turn runner/auth failures into routing outcomes.

Adapted from latent-sre/sre-agents' clean-room design, with a Python 3.10-compatible cleanup path.
Source: https://github.com/latent-sre/sre-agents (MIT; Copyright 2026 SRE + SDE Agent Fleet
contributors). The source license notice is preserved in THIRD_PARTY_NOTICES.md.
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

CREDENTIALS = ".credentials.json"
AUTH_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_FOUNDRY_API_KEY",
    "ANTHROPIC_FOUNDRY_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_REFRESH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_MANTLE",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS",
)
CONTAMINATING_ENV_VARS = (
    "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD",
    # Phantom in current docs (see the note in clean_env), scrubbed anyway: the room must not SET
    # it, but it must not INHERIT it either — an operator who exported it would otherwise carry an
    # undocumented variable into an environment the artifact records as clean.
    "CLAUDE_CODE_DISABLE_POLICY_SKILLS",
    "CLAUDE_CODE_ENABLE_BACKGROUND_PLUGIN_REFRESH",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
    "CLAUDE_CODE_PLUGIN_CACHE_DIR",
    "CLAUDE_CODE_PLUGIN_SEED_DIR",
    "CLAUDE_CODE_SIMPLE",
    "CLAUDE_CODE_SYNC_PLUGIN_INSTALL",
    "CLAUDE_CODE_SYNC_PLUGIN_INSTALL_TIMEOUT_MS",
    "CLAUDE_CODE_SYNC_SKILLS",
    "CLAUDE_CODE_SYNC_SKILLS_INSTALL_TIMEOUT_MS",
    "CLAUDE_CODE_SYNC_SKILLS_WAIT_TIMEOUT_MS",
    "CLAUDE_CODE_TASK_LIST_ID",
    "CLAUDE_CODE_TEAM_NAME",
)
AUTH_MARKERS = ("authentication_failed", "Not logged in")


class AuthUnavailable(RuntimeError):
    """The harness cannot authenticate and therefore cannot produce a measurement."""


class RunnerFailed(RuntimeError):
    """A model run did not reach a successful structured result event."""


def user_config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def has_environment_auth() -> bool:
    return any(os.environ.get(name) for name in AUTH_ENV_VARS)


def require_credentials() -> Path:
    credentials = user_config_dir() / CREDENTIALS
    if not credentials.is_file():
        raise AuthUnavailable(
            f"no Claude credentials at {credentials}. The clean room refuses to run because an "
            "unauthenticated trace can look like a valid no-route result. Run `claude` and /login, "
            "set an API-key/Bedrock/Vertex auth variable, or point CLAUDE_CONFIG_DIR at a logged-in "
            "configuration directory."
        )
    return credentials


def _warn_cleanup(function, path, exc_info) -> None:
    detail = exc_info[1] if isinstance(exc_info, tuple) else exc_info
    print(
        f"eval_clean_room: WARNING: could not remove {path} ({function.__name__}: {detail}). "
        "The directory may contain a copy of Claude credentials; remove it manually.",
        file=sys.stderr,
    )


@contextlib.contextmanager
def clean_env():
    """Yield an environment isolated from personal Claude configuration.

    API-key/Bedrock/Vertex users need no credential file. Subscription users get a permission-
    restricted copy of only `.credentials.json`; skills, agents, plugins, settings, and CLAUDE.md
    are intentionally not copied.
    """
    credentials = None if has_environment_auth() else require_credentials()
    room = Path(tempfile.mkdtemp(prefix="sde-agents-cleanroom-"))
    try:
        os.chmod(room, stat.S_IRWXU)
        if credentials is not None:
            destination = room / CREDENTIALS
            shutil.copyfile(credentials, destination)
            os.chmod(destination, stat.S_IRUSR | stat.S_IWUSR)
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(room))
        for name in CONTAMINATING_ENV_VARS:
            env.pop(name, None)
        # The branch this was salvaged from also set CLAUDE_CODE_DISABLE_POLICY_SKILLS=1 here.
        # Verified against current docs (2026-07-29, CLI 2.1.220): no such variable exists — the
        # documented neighbor is CLAUDE_CODE_DISABLE_BUNDLED_SKILLS (v2.1.169), which disables the
        # CLI's OWN built-in skills. That is a different measurement condition (every existing
        # baseline ran with built-ins present), so it is deliberately not set: a knob that changes
        # comparability belongs in a conditions block, not silently inside the room. Setting the
        # phantom name would have shipped isolation that reads as armor and is nothing.
        env["CLAUDE_CODE_SKIP_PROMPT_HISTORY"] = "1"
        yield env
    finally:
        # onerror works on the repository's existing Python floor; upstream's onexc requires 3.12.
        shutil.rmtree(room, onerror=_warn_cleanup)


def result_event(transcript: str) -> dict | None:
    """Return the final structured CLI result event, if one was emitted."""
    result = None
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            result = event
    return result


def validate_completed_run(transcript: str, returncode: int, stderr: str = "") -> dict:
    """Return the successful result event or raise RunnerFailed/AuthUnavailable.

    A tool invocation, partial transcript, timeout, non-zero exit, or `is_error` result is not a
    measurement. In particular, it must never make a negative routing case pass vacuously.
    """
    event = result_event(transcript)
    event_text = json.dumps(event or {})
    # A run that already failed is classified by scanning everything the CLI said, not only the
    # result event: an auth failure can exit non-zero before any result event is emitted, or land
    # only in stderr/transcript, and mislabeling it RunnerFailed erases the very distinction this
    # helper exists to draw. Successful runs are never scanned — a model quoting "Not logged in"
    # in its answer is a measurement, not an outage.
    failed = returncode != 0 or event is None or bool(event.get("is_error"))
    if failed and any(
        marker in text for text in (event_text, stderr or "", transcript or "") for marker in AUTH_MARKERS
    ):
        raise AuthUnavailable("Claude authentication failed during the eval; refresh /login and rerun")
    if returncode != 0:
        raise RunnerFailed(f"Claude exited {returncode}: {(stderr or '')[:180]}")
    if event is None:
        raise RunnerFailed("Claude exited without a structured result event")
    if event.get("is_error"):
        raise RunnerFailed(f"Claude result event reported an error: {event_text[:220]}")
    return event
