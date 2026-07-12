"""End-to-end test of the code-reviewer PreToolUse hook AS THE AGENT FILE DEFINES IT.

tests/test_readonly_guard.py tests the guard's decisions by invoking the script
directly. That is not the same thing as testing the hook: the hook is a shell
command string in agents/code-reviewer.md, and it is what Claude Code actually
runs. Both of this repo's real guard failures lived in that string, not in the
guard -- it selected `python3` without checking the interpreter works (on Windows
the Microsoft Store stub exists, wins `command -v`, and exits 49 without running
anything), and it resolved the script under CLAUDE_PROJECT_DIR, so in any repo
other than this one the script was missing. Both failed OPEN: no decision on
stdout means the Bash call proceeds unguarded.

So these tests extract the command from the agent frontmatter and run it, and the
load-bearing case is the one where the guard cannot be found at all: a read-only
agent whose guard is unavailable must DENY, never fall through.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENT = REPO / "agents" / "code-reviewer.md"

PUSH = {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}}
DIFF = {"tool_name": "Bash", "tool_input": {"command": "git diff HEAD~1"}}


def hook_command() -> str:
    """The PreToolUse command string, read from the agent definition itself."""
    # Only split off the leading frontmatter block; the agent body may legitimately
    # contain '---' (e.g. in markdown), and an unbounded split would misalign it.
    frontmatter = AGENT.read_text(encoding="utf-8").split("---", 2)[1]
    match = re.search(r'^\s*command:\s*"(.*)"\s*$', frontmatter, re.MULTILINE)
    # A plain `assert` here would be stripped under `python -O`, turning a missing
    # or renamed frontmatter key into a confusing NoneType error further down.
    if match is None:
        raise RuntimeError("no PreToolUse command found in code-reviewer frontmatter")
    # Undo the YAML double-quoted escaping to recover the shell string.
    return match.group(1).replace('\\"', '"').replace("\\\\", "\\")


def run_hook(payload: dict, *, project_dir: str, home: str) -> subprocess.CompletedProcess:
    """Run the hook exactly as Claude Code would: sh -c <command>, JSON on stdin."""
    # Inherit the real environment and override only what the hook resolves paths from.
    # (A stripped env breaks Windows: unset SystemDrive/SystemRoot make native calls
    # expand %SystemDrive% literally and scatter directories into the CWD.)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=project_dir, HOME=home)
    return subprocess.run(
        ["sh", "-c", hook_command()],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def decision(stdout: str) -> str | None:
    if not stdout.strip():
        return None  # no decision -> Claude allows the command
    return json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]


@unittest.skipIf(shutil.which("sh") is None, "POSIX sh unavailable")
class HookWiringTest(unittest.TestCase):
    def _run(self, payload: dict, *, project_dir: str, home: str) -> str:
        # A crashing hook prints nothing on stdout, and empty stdout is silently
        # treated as allow -- exactly the failure mode this test file exists to
        # catch. Fail loudly instead, surfacing stderr for debugging.
        result = run_hook(payload, project_dir=project_dir, home=home)
        self.assertEqual(
            result.returncode, 0,
            f"hook exited {result.returncode}; stderr:\n{result.stderr}",
        )
        return result.stdout

    def test_denies_state_change_when_guard_resolves_in_repo(self) -> None:
        out = self._run(PUSH, project_dir=str(REPO), home=str(Path.home()))
        self.assertEqual(decision(out), "deny")

    def test_allows_read_only_command_when_guard_resolves(self) -> None:
        out = self._run(DIFF, project_dir=str(REPO), home=str(Path.home()))
        self.assertIsNone(decision(out))

    def test_fails_closed_when_guard_is_missing_everywhere(self) -> None:
        # A foreign target repo with no fleet install: the guard cannot be found.
        # A read-only agent MUST deny rather than run unguarded.
        out = self._run(DIFF, project_dir="/nonexistent-project", home="/nonexistent-home")
        self.assertEqual(decision(out), "deny")
        self.assertIn("guard unavailable", out)

    def test_falls_back_to_installed_guard_outside_the_repo(self) -> None:
        # CLAUDE_PROJECT_DIR points at a foreign repo, but the fleet is installed
        # at ~/.claude/scripts -- the guard must still enforce. Seed a throwaway HOME
        # with the guard installed so the fallback branch runs deterministically in CI
        # (the real ~/.claude install is absent on a clean runner).
        with tempfile.TemporaryDirectory() as home:
            installed = Path(home) / ".claude" / "scripts" / "readonly-guard.py"
            installed.parent.mkdir(parents=True)
            shutil.copyfile(REPO / "scripts" / "readonly-guard.py", installed)
            out = self._run(PUSH, project_dir="/nonexistent-project", home=home)
            self.assertEqual(decision(out), "deny")
            # and a read-only command in that same fallback config is allowed
            allow = self._run(DIFF, project_dir="/nonexistent-project", home=home)
            self.assertIsNone(decision(allow))


if __name__ == "__main__":
    unittest.main()
