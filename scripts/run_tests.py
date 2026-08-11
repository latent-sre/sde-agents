#!/usr/bin/env python3
"""Run the test suite with one process per test module, in parallel.

The suite is embarrassingly parallel at module granularity: modules share no state, and the
two deliberately stateful fixtures (the pooled repo copy in tests/support.py and the
validator's content-keyed module cache) are process-local, so process-per-module preserves
exactly the isolation a plain `unittest discover` run has. What changes is wall-clock: the
serial run costs the SUM of module times, this runner costs roughly the longest module.

Each child is a plain `python -m unittest discover -s <start-dir> -p <module>.py` — the same
sanctioned invocation the T0 loop uses — so a module that fails here reproduces verbatim by
copying the printed command. Child output is buffered and printed whole when the module
finishes, never interleaved; the summary aggregates the per-module "Ran N tests" counts so a
module silently discovering zero tests is visible instead of vanishing into a green total.

Exit code: 0 only when every module passed. Discovering no modules at all is an error, not an
empty success — a typoed --start-dir must not certify a suite that never ran.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

RAN_RE = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)


def importable_packages(start_dir: Path) -> list[Path]:
    """Importable packages under the start directory — grounds for refusing to run.

    `unittest discover` recurses into importable packages (each level carrying __init__.py),
    collects their test_*.py files, and honors a package __init__'s `load_tests` hook — the
    hook fires on EVERY discovery pass, so this runner's per-module children would execute it
    once per top-level module instead of once per suite. Either shape silently diverges from
    the serial invocation (skipped nested modules, multiplied package-level tests), so any
    importable package is refused outright rather than guessing at discovery semantics.
    Fixture trees without __init__.py are excluded the same way discovery excludes them; flat
    shared helpers (tests/support.py) are the sanctioned alternative to helper packages.
    """
    packages = []
    for path in sorted(start_dir.rglob("__init__.py")):
        if path.parent == start_dir:
            continue
        # Only an unbroken __init__.py chain back to the start directory participates in
        # discovery; a package buried under a plain fixture directory is invisible to serial
        # discovery too, so refusing it would reject suites the documented command accepts.
        walk = path.parent.parent
        importable = True
        while walk != start_dir:
            if not (walk / "__init__.py").exists():
                importable = False
                break
            walk = walk.parent
        if importable:
            packages.append(path.parent)
    return packages


def run_module(start_dir: Path, module: Path, passthrough: list[str]) -> tuple[Path, int, str, list[str]]:
    argv = [
        sys.executable, "-m", "unittest", "discover",
        "-s", str(start_dir), "-p", module.name, *passthrough,
    ]
    # Windows inherits the parent's legacy console encoding unless told otherwise. Force normal
    # Python text through UTF-8, but keep decoding total: os.write() and native grandchildren can
    # still emit arbitrary bytes. ASCII-safe escapes preserve that evidence without letting one
    # undecodable byte hide every module verdict and the aggregate summary.
    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "utf-8"
    child_env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        env=child_env,
    )
    return module, proc.returncode, proc.stdout + proc.stderr, argv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start-dir", default="tests", help="unittest discovery start directory")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 2,
                        help="concurrent module processes (default: cpu count)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="forward -v to every module run")
    parser.add_argument("--durations", type=int, metavar="N",
                        help="forward --durations N (Python 3.12+) to every module run")
    args = parser.parse_args(argv)

    start_dir = Path(args.start_dir)
    modules = sorted(start_dir.glob("test_*.py"))
    if not modules:
        print(f"error: no test_*.py modules under {start_dir}", file=sys.stderr)
        return 2
    packages = importable_packages(start_dir)
    if packages:
        print(
            "error: importable packages under the start directory diverge from serial "
            "discovery (nested modules would be skipped; a load_tests hook would run once "
            "per child): " + ", ".join(str(p) for p in packages)
            + " — flatten them into the start directory or extend the runner first.",
            file=sys.stderr,
        )
        return 2

    passthrough: list[str] = []
    if args.verbose:
        passthrough.append("-v")
    if args.durations is not None:
        passthrough += ["--durations", str(args.durations)]

    # Longest-work-first scheduling, with file size as the runtime proxy: the largest module
    # (test_validate_fleet) is also the slowest, and starting it last would leave the pool
    # idling behind it. The proxy being occasionally wrong costs seconds, not correctness.
    modules.sort(key=lambda p: p.stat().st_size, reverse=True)

    started = time.perf_counter()
    failures: list[Path] = []
    total_tests = 0
    unparsed: list[Path] = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run_module, start_dir, m, passthrough) for m in modules]
        # Completion order, not submission order: a slow first module must not sit on the
        # reports of everything that finished behind it.
        for future in as_completed(futures):
            module, code, output, argv = future.result()
            counted = RAN_RE.search(output)
            if counted:
                total_tests += int(counted.group(1))
            else:
                unparsed.append(module)
            verdict = "ok" if code == 0 else f"FAILED (exit {code})"
            print(f"== {module.name}: {verdict}")
            if code != 0 or args.verbose:
                print(output, end="" if output.endswith("\n") else "\n")
            if code != 0:
                print(f"reproduce: {' '.join(argv)}")
                failures.append(module)

    elapsed = time.perf_counter() - started
    print(f"\nRan {total_tests} tests across {len(modules)} modules in {elapsed:.1f}s")
    for module in unparsed:
        # A module whose output never says "Ran N tests" ran nothing recognizable; surfacing it
        # beats folding it into a green total.
        print(f"warning: could not count tests from {module.name}", file=sys.stderr)
    if failures:
        print(f"FAILED modules: {', '.join(sorted(m.name for m in failures))}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
