"""Shared test fixtures — only patterns with multiple real consumers live here.

This module deliberately stays small. A helper earns its place by replacing the same code in
two or more test modules (or a dozen repetitions in one); anything a single module needs stays
in that module, per the repository's proportionality rule. It is named so `unittest discover`
never collects it, and imported as `from tests.support import ...`, which holds under every
sanctioned invocation for the same reason the existing `from scripts import ...` imports do:
the suite runs from the repository root.
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def repo_copy() -> Iterator[Path]:
    """A disposable copy of the real repository, for mutation tests.

    Wiring invariants are proven against a copy of the actual repo, not a synthetic fixture
    that could drift away from it. tests/ stays in the copy: AGENTS.md names `tests/fixtures/`,
    and the guide drift check resolves every multi-segment path it asserts. Only `.git` and
    `__pycache__` are excluded — one is not part of the tree under validation, the other is
    machine-local byproduct that would make copies differ between runs.
    """
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / "repo"
        shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        yield dst


def run_main(main: Callable[[list[str]], int], *argv: str) -> tuple[int, str]:
    """Call a script's main(argv) in-process, returning (exit code, stdout).

    Stderr is swallowed rather than asserted on: the scripts' contract is exit code plus
    stdout, and pinning diagnostics would turn every reworded warning into a test failure.
    """
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


def git(root: Path, *args: str, date: str | None = None) -> None:
    """Run git against a test repo. `date` pins both author and committer dates.

    Both dates are pinned so history display and deliberately backdated graph fixtures stay
    deterministic across machines and over time.
    """
    env = dict(os.environ)
    if date is not None:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)
