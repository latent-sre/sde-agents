#!/usr/bin/env python3
"""Two-session registration probe: what does an eval session actually see?

`evals/README.md` once claimed each headless run was "the clean-context isolation the methodology
requires". It was not: `claude -p --plugin-dir .` inherits everything under the user's
CLAUDE_CONFIG_DIR — personal agents, skills, plugins, memory — and a junction deployment
(`~/.claude/{agents,skills}` pointing into this repo) makes the fleet register TWICE, bare and
namespaced. Every registered component competes for every routing decision, so the registration
surface is a measurement condition; this probe is what states it instead of assuming it.

Two sessions, identical except for the room:

  1. status quo — whatever the operator's configuration contributes, plus `--plugin-dir`;
  2. clean room — CLAUDE_CONFIG_DIR relocated to a temporary directory holding only credentials
     (`scripts/eval_clean_room.py`), plus the same `--plugin-dir`.

Each session's `system/init` event declares the agents, skills, slash commands, and plugins it
registered. The probe records both surfaces, the diff, and the fleet's bare/namespaced split, and
writes the artifact to --output-dir. Registration is model-independent, so the sessions default to
haiku; conditions are recorded regardless, like every other measurement here.

Manual and on demand, like probe_plugin.py: it drives real API sessions. Re-run after DEPLOY-001
changes the deployment mode, or after a CLI upgrade changes what an init event lists.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAUDE = shutil.which("claude")
PROMPT = "Reply with exactly: ready"

_CLEAN_ROOM_PATH = Path(__file__).resolve().parent / "eval_clean_room.py"
_spec = importlib.util.spec_from_file_location("eval_clean_room", _CLEAN_ROOM_PATH)
# An assert here would vanish under `python -O` and surface later as an opaque AttributeError;
# a probe that cannot load its isolation module must say so before pretending to measure anything.
if _spec is None or _spec.loader is None:
    raise ImportError(f"cannot load the clean-room module from {_CLEAN_ROOM_PATH}; the probe "
                      "refuses to run without it because an unisolated clean-room session would "
                      "measure a contamination delta of zero by construction")
clean_room = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(clean_room)


def init_event(transcript: str) -> dict | None:
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            return event
    return None


def registration_surface(model: str, timeout: int, env: dict | None) -> dict:
    """One headless session; return the surface its init event declares.

    Runs through `validate_completed_run` so a dead CLI or expired login raises instead of
    returning an empty surface — an unauthenticated probe that "found no contamination" would be
    the same lie the clean room exists to refuse.
    """
    with tempfile.TemporaryDirectory() as cwd:
        proc = subprocess.run(
            [CLAUDE, "-p", PROMPT, "--plugin-dir", str(REPO),
             "--output-format", "stream-json", "--verbose", "--model", model],
            capture_output=True, encoding="utf-8", errors="replace", cwd=cwd,
            timeout=timeout, env=env,
        )
    clean_room.validate_completed_run(proc.stdout or "", proc.returncode, proc.stderr or "")
    event = init_event(proc.stdout or "")
    if event is None:
        raise clean_room.RunnerFailed("session completed but emitted no system/init event")
    plugins = event.get("plugins") or []
    servers = event.get("mcp_servers") or []
    return {
        "agents": sorted(event.get("agents") or []),
        "skills": sorted(event.get("skills") or []),
        "slash_commands": sorted(event.get("slash_commands") or []),
        # Names only for plugins and MCP servers: their full entries can carry local paths and
        # URLs, and this artifact is committed.
        "plugins": sorted(p.get("name", "?") if isinstance(p, dict) else str(p) for p in plugins),
        "mcp_servers": sorted(s.get("name", "?") if isinstance(s, dict) else str(s) for s in servers),
        "memory_path_count": len(event.get("memory_paths") or []),
        "model_observed": event.get("model"),
    }


def fleet_split(names: list[str], roster: frozenset[str]) -> dict:
    """How the fleet appears in one registration list: bare (junction/global) vs namespaced."""
    return {
        "bare": sorted(n for n in names if n in roster),
        "namespaced": sorted(n for n in names if n.startswith("sde-agents:")
                             and n.split(":", 1)[1] in roster),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="haiku",
                        help="session model; registration is model-independent (default haiku)")
    parser.add_argument("--timeout", type=int, default=240, help="per-session seconds")
    parser.add_argument("--output-dir", type=Path, default=None, help="write isolation.json here")
    args = parser.parse_args()

    if CLAUDE is None:
        print("claude CLI not found on PATH", file=sys.stderr)
        return 2

    agents_roster = frozenset(p.stem for p in (REPO / "agents").glob("*.md"))
    skills_roster = frozenset(p.name for p in (REPO / "skills").iterdir() if p.is_dir())

    try:
        status_quo = registration_surface(args.model, args.timeout, env=None)
        with clean_room.clean_env() as env:
            isolated = registration_surface(args.model, args.timeout, env=env)
    except clean_room.AuthUnavailable as exc:
        print(f"auth unavailable — nothing was measured: {exc}", file=sys.stderr)
        return 2
    except (clean_room.RunnerFailed, subprocess.TimeoutExpired) as exc:
        print(f"runner failed — nothing was measured: {exc}", file=sys.stderr)
        return 2

    report = {
        "conditions": {
            "cli_version": cli_version(),
            "model_requested": args.model,
            "models_observed": sorted({m for m in (status_quo["model_observed"],
                                                   isolated["model_observed"]) if m}),
            "plugin_dir": ".",
            "timeout_s": args.timeout,
        },
        "sessions": {"status_quo": status_quo, "clean_room": isolated},
        "fleet_agents": {
            "status_quo": fleet_split(status_quo["agents"], agents_roster),
            "clean_room": fleet_split(isolated["agents"], agents_roster),
        },
        "fleet_skills": {
            "status_quo": fleet_split(status_quo["skills"], skills_roster),
            "clean_room": fleet_split(isolated["skills"], skills_roster),
        },
        # What the operator's configuration was contributing to every eval session's routing
        # surface. This list IS the contamination finding.
        "removed_by_clean_room": {
            key: sorted(set(status_quo[key]) - set(isolated[key]))
            for key in ("agents", "skills", "slash_commands", "plugins", "mcp_servers")
        },
        "added_by_clean_room": {
            key: sorted(set(isolated[key]) - set(status_quo[key]))
            for key in ("agents", "skills", "slash_commands", "plugins", "mcp_servers")
        },
    }

    for label, surface in (("status quo", status_quo), ("clean room", isolated)):
        split = fleet_split(surface["agents"], agents_roster)
        print(f"{label}: {len(surface['agents'])} agents "
              f"(fleet bare {len(split['bare'])}, fleet namespaced {len(split['namespaced'])}), "
              f"{len(surface['skills'])} skills, {len(surface['plugins'])} plugins, "
              f"{surface['memory_path_count']} memory paths")
    removed = report["removed_by_clean_room"]
    print(f"clean room removed: {sum(len(v) for v in removed.values())} entries "
          f"({', '.join(f'{k}: {len(v)}' for k, v in removed.items() if v) or 'none'})")

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "isolation.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.output_dir / 'isolation.json'}")

    # The one hard invariant: the plugin itself must register namespaced in BOTH sessions. If the
    # clean room also removed the fleet, it isolated the eval from the thing under test.
    for label, surface in (("status_quo", status_quo), ("clean_room", isolated)):
        if not fleet_split(surface["agents"], agents_roster)["namespaced"]:
            print(f"FAIL: no namespaced fleet agents registered in the {label} session — "
                  f"--plugin-dir did not load the fleet there", file=sys.stderr)
            return 1
    return 0


def cli_version() -> str | None:
    try:
        proc = subprocess.run([CLAUDE, "--version"], capture_output=True, encoding="utf-8",
                              timeout=30)
        return (proc.stdout or "").strip() or None
    except Exception:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
