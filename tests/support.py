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
import hashlib
import io
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_IGNORED_DIRS = {".git", "__pycache__"}


def _walk_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if any(part in _IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


class _RepoPool:
    """One pristine template plus one reused working tree, built lazily on first use.

    Copying the whole repository per mutation test was measured at 60% of the owning module's
    wall-clock (93 copies × ~160-325ms). The pool replaces every copy after the first two with
    a restore that compares each file's CONTENT against a SHA-256 manifest of the template —
    never stat shortcuts, whose mtime granularity on some filesystems would miss a same-size
    rewrite — so every borrower still provably starts pristine. The pool is process-local and
    unittest runs tests sequentially, so no two borrowers overlap.
    """

    def __init__(self) -> None:
        # Held for the process lifetime; the TemporaryDirectory finalizer cleans up at exit.
        self._holder = tempfile.TemporaryDirectory()
        base = Path(self._holder.name)
        self.template = base / "template"
        shutil.copytree(REPO, self.template, ignore=shutil.ignore_patterns(*_IGNORED_DIRS))
        self.work = base / "repo"
        shutil.copytree(self.template, self.work)
        self.manifest = {
            path.relative_to(self.template): hashlib.sha256(path.read_bytes()).digest()
            for path in _walk_files(self.template)
        }
        self.directories = {
            path.relative_to(self.template)
            for path in self.template.rglob("*")
            if path.is_dir()
            and not any(part in _IGNORED_DIRS for part in path.relative_to(self.template).parts)
        }

    def restore(self) -> None:
        """Return the working tree to exactly the manifest's content, whatever the last test did."""
        seen: set[Path] = set()
        for path in _walk_files(self.work):
            rel = path.relative_to(self.work)
            seen.add(rel)
            want = self.manifest.get(rel)
            if want is None:
                path.unlink()  # file the last borrower added
            elif hashlib.sha256(path.read_bytes()).digest() != want:
                shutil.copyfile(self.template / rel, path)  # file the last borrower changed
        for rel in self.manifest.keys() - seen:
            target = self.work / rel
            if target.is_dir():
                # A directory now shadows the manifest file's path (the borrower replaced the
                # file); its contents were already removed above as additions, but copyfile
                # onto the shell would raise and poison the pool for every later borrower.
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.template / rel, target)  # file the last borrower deleted
        # Directories the borrower ADDED are not invisible once their files are gone: an empty
        # skills/<name>/ shell reads to validate_skills() as a skill missing its SKILL.md, so a
        # leftover would hand later borrowers a tree the validator judges differently (caught in
        # review on #91). Shallowest-first, so one rmtree takes any nested additions with it.
        for rel in sorted(
            path.relative_to(self.work)
            for path in self.work.rglob("*")
            if path.is_dir()
            and not any(part in _IGNORED_DIRS for part in path.relative_to(self.work).parts)
        ):
            if rel not in self.directories:
                target = self.work / rel
                if target.is_dir():
                    shutil.rmtree(target)


_pool: _RepoPool | None = None


@contextlib.contextmanager
def repo_copy() -> Iterator[Path]:
    """A disposable copy of the real repository, for mutation tests.

    Wiring invariants are proven against a copy of the actual repo, not a synthetic fixture
    that could drift away from it. tests/ stays in the copy: AGENTS.md names `tests/fixtures/`,
    and the guide drift check resolves every multi-segment path it asserts. Only `.git` and
    `__pycache__` are excluded — one is not part of the tree under validation, the other is
    machine-local byproduct that would make copies differ between runs.

    Callers may mutate file contents, add files, or delete anything under the yielded path,
    and must not touch it after the with-block: the tree is pooled, and the next borrower gets
    it restored by content. Restoration is content-level only — a test that needs to mutate
    file metadata (permissions, timestamps) must build its own copy instead.
    """
    global _pool
    if _pool is None:
        _pool = _RepoPool()
    else:
        _pool.restore()
    yield _pool.work


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
