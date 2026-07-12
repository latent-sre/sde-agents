"""End-to-end test of the code-reviewer PreToolUse hook AS THE AGENT FILE DEFINES IT.

tests/test_readonly_guard.py tests the guard's decisions by invoking the script
directly. That is not the same thing as testing the hook: the hook is a shell
command string in agents/code-reviewer.md, and it is what Claude Code actually
runs. This string is also a trust boundary: CLAUDE_PROJECT_DIR is the repository
being reviewed, so executing a guard from there would execute untrusted target
code. The hook must use the installed fleet guard and convert missing interpreters,
missing files, and guard crashes into an explicit deny decision. Otherwise an empty
stdout or a non-blocking hook error lets the Bash call proceed unguarded.

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
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import install_reviewer_guard

REPO = Path(__file__).resolve().parents[1]
AGENT = REPO / "agents" / "code-reviewer.md"
INSTALLER = REPO / "scripts" / "install_reviewer_guard.py"
SH = shutil.which("sh")

PUSH = {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}}
DIFF = {"tool_name": "Bash", "tool_input": {"command": "git diff HEAD~1"}}


def hook_command() -> str:
    """The PreToolUse command string, read from the agent definition itself.

    Walks the real `hooks: -> PreToolUse: -> matcher: Bash -> command:` path rather than
    grepping the frontmatter for any `command:` line. The loose grep passed even when the
    wiring was broken: rename `hooks:` to `hook:` and the runtime stops installing the guard
    entirely, but the `command:` string is still sitting there in the frontmatter, so the old
    regex found it and every test went green while the guard was dead. The structure IS the
    thing under test — an unreachable command is not a wired hook.
    """
    # Only split off the leading frontmatter block; the agent body may legitimately
    # contain '---' (e.g. in markdown), and an unbounded split would misalign it.
    frontmatter = AGENT.read_text(encoding="utf-8").split("---", 2)[1]

    # A plain `assert` would be stripped under `python -O`, turning a broken wiring path into a
    # confusing NoneType error further down; these must fail loudly.
    def require(pattern: str, what: str) -> re.Match:
        match = re.search(pattern, frontmatter, re.MULTILINE)
        if match is None:
            raise RuntimeError(
                f"code-reviewer frontmatter: {what} not found. The read-only guard is wired "
                f"through hooks->PreToolUse->matcher: Bash->command; a renamed or misnested key "
                f"silently disarms it."
            )
        return match

    require(r"^hooks:\s*$", "top-level 'hooks:' key")
    require(r"^\s+PreToolUse:\s*$", "'PreToolUse:' event under hooks")
    require(r"^\s+-\s*matcher:\s*Bash\s*$", "'matcher: Bash' under PreToolUse")
    match = require(r'^\s*command:\s*"(.*)"\s*$', "PreToolUse 'command:' string")

    # Undo the YAML double-quoted escaping to recover the shell string.
    return match.group(1).replace('\\"', '"').replace("\\\\", "\\")


def run_hook(
    payload: dict,
    *,
    project_dir: str,
    home: str,
    cwd: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run the hook exactly as Claude Code would: sh -c <command>, JSON on stdin."""
    # Inherit the real environment and override only what the hook resolves paths from.
    # (A stripped env breaks Windows: unset SystemDrive/SystemRoot make native calls
    # expand %SystemDrive% literally and scatter directories into the CWD.)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=project_dir, HOME=home)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [str(SH), "-c", hook_command()],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        timeout=30,
    )


def decision(stdout: str) -> str | None:
    if not stdout.strip():
        return None  # no decision -> Claude allows the command
    return json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]


def install_guard(home: str, *, contents: str | None = None) -> Path:
    """Install either the real guard or a test double into a throwaway HOME."""
    installed, _ = install_reviewer_guard.install(Path(home) / ".claude" / "scripts")
    if contents is not None:
        installed.write_text(contents, encoding="utf-8")
    return installed


def seed_target_guard(project: str) -> Path:
    """Create a target-repository guard that leaves proof if it is executed."""
    marker = Path(project) / "target-guard-executed"
    target_guard = Path(project) / "scripts" / "readonly-guard.py"
    target_guard.parent.mkdir(parents=True)
    target_guard.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n",
        encoding="utf-8",
    )
    return marker


class GuardInstallerTest(unittest.TestCase):
    def test_cli_installs_guard_and_records_absolute_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "scripts"
            result = subprocess.run(
                [sys.executable, str(INSTALLER), "--target-dir", str(target)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            installed = target / "readonly-guard.py"
            record = target / "readonly-guard.python"
            self.assertEqual(
                installed.read_bytes(),
                (REPO / "scripts" / "readonly-guard.py").read_bytes(),
            )
            record_bytes = record.read_bytes()
            self.assertTrue(record_bytes.endswith(b"\n"))
            self.assertNotIn(b"\r", record_bytes)
            recorded_python = Path(record_bytes.decode("utf-8").strip())
            self.assertTrue(recorded_python.is_absolute())
            self.assertEqual(recorded_python.resolve(), Path(sys.executable).resolve())


@unittest.skipIf(SH is None, "POSIX sh unavailable")
class HookWiringTest(unittest.TestCase):
    def _run(
        self,
        payload: dict,
        *,
        project_dir: str,
        home: str,
        cwd: str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> str:
        # A crashing hook prints nothing on stdout, and empty stdout is silently
        # treated as allow -- exactly the failure mode this test file exists to
        # catch. Fail loudly instead, surfacing stderr for debugging.
        result = run_hook(
            payload,
            project_dir=project_dir,
            home=home,
            cwd=cwd,
            extra_env=extra_env,
        )
        self.assertEqual(
            result.returncode, 0,
            f"hook exited {result.returncode}; stderr:\n{result.stderr}",
        )
        return result.stdout

    def test_denies_state_change_when_installed_guard_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            install_guard(home)
            out = self._run(PUSH, project_dir=str(REPO), home=home)
            self.assertEqual(decision(out), "deny")

    def test_allows_read_only_command_when_installed_guard_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            install_guard(home)
            out = self._run(DIFF, project_dir=str(REPO), home=home)
            self.assertIsNone(decision(out))

    def test_fails_closed_when_guard_is_missing_everywhere(self) -> None:
        # A foreign target repo with no fleet install: the guard cannot be found.
        # A read-only agent MUST deny rather than run unguarded.
        out = self._run(DIFF, project_dir="/nonexistent-project", home="/nonexistent-home")
        self.assertEqual(decision(out), "deny")
        self.assertIn("guard unavailable", out)

    def test_installed_guard_works_outside_the_repo(self) -> None:
        # CLAUDE_PROJECT_DIR points at a foreign repo, but the fleet is installed
        # at ~/.claude/scripts -- the guard must still enforce. Seed a throwaway HOME
        # so the test never depends on the developer's real installation.
        with tempfile.TemporaryDirectory() as home:
            install_guard(home)
            out = self._run(PUSH, project_dir="/nonexistent-project", home=home)
            self.assertEqual(decision(out), "deny")
            # and a read-only command in that same fallback config is allowed
            allow = self._run(DIFF, project_dir="/nonexistent-project", home=home)
            self.assertIsNone(decision(allow))

    def test_ignores_untrusted_guard_in_target_repository(self) -> None:
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as home:
            marker = seed_target_guard(project)
            install_guard(home)

            out = self._run(DIFF, project_dir=project, home=home, cwd=project)

            self.assertIsNone(decision(out))
            self.assertFalse(marker.exists(), "the target repository's guard was executed")

    def test_never_falls_back_to_target_guard_when_install_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as home:
            marker = seed_target_guard(project)

            out = self._run(DIFF, project_dir=project, home=home, cwd=project)

            self.assertEqual(decision(out), "deny")
            self.assertFalse(marker.exists(), "the target repository's guard was executed")

    def test_installed_guard_runtime_failure_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            install_guard(home, contents="raise RuntimeError('broken guard')\n")

            out = self._run(DIFF, project_dir="/nonexistent-project", home=home)

            self.assertEqual(decision(out), "deny")
            self.assertIn("guard unavailable or failed", out)

    def test_target_cannot_inject_guard_interpreter_or_python_imports(self) -> None:
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as home:
            install_guard(home)
            path_marker = Path(project) / "path-shim-executed"
            import_marker = Path(project) / "pythonpath-executed"

            poison_bin = Path(project) / "poison-bin"
            poison_bin.mkdir()
            python_shim = poison_bin / "python3"
            python_shim.write_text(
                "#!/bin/sh\n"
                'printf executed > "$CLAUDE_PROJECT_DIR/path-shim-executed"\n',
                encoding="utf-8",
            )
            python_shim.chmod(0o755)

            poison_imports = Path(project) / "poison-imports"
            poison_imports.mkdir()
            (poison_imports / "json.py").write_text(
                "import os\n"
                "open(os.path.join(os.environ['CLAUDE_PROJECT_DIR'], "
                "'pythonpath-executed'), 'w').write('executed')\n",
                encoding="utf-8",
            )
            injected = {
                "PATH": str(poison_bin) + os.pathsep + os.environ.get("PATH", ""),
                "PYTHONHOME": str(poison_imports),
                "PYTHONPATH": str(poison_imports),
            }

            out = self._run(
                DIFF,
                project_dir=project,
                home=home,
                cwd=project,
                extra_env=injected,
            )

            self.assertIsNone(decision(out))
            self.assertFalse(path_marker.exists(), "the PATH interpreter shim was executed")
            self.assertFalse(import_marker.exists(), "PYTHONPATH code was imported")


if __name__ == "__main__":
    unittest.main()
