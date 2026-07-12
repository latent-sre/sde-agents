#!/usr/bin/env python3
"""Install the code-reviewer guard with a pinned trusted Python interpreter."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


GUARD_NAME = "readonly-guard.py"
INTERPRETER_RECORD = "readonly-guard.python"


def install(target_dir: Path, *, interpreter: Path | None = None) -> tuple[Path, Path]:
    """Copy the guard and record an absolute interpreter path using LF-only text."""
    source = Path(__file__).with_name(GUARD_NAME)
    selected = (interpreter or Path(sys.executable)).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"guard source not found: {source}")
    if not selected.is_file():
        raise FileNotFoundError(f"Python interpreter not found: {selected}")

    target_dir = target_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    installed_guard = target_dir / GUARD_NAME
    interpreter_record = target_dir / INTERPRETER_RECORD
    shutil.copyfile(source, installed_guard)

    # Git Bash reliably executes a quoted C:/... path, while backslashes in a value
    # read by POSIX sh are needlessly fragile. POSIX paths are unchanged.
    executable = str(selected).replace("\\", "/")
    interpreter_record.write_bytes(f"{executable}\n".encode("utf-8"))
    return installed_guard, interpreter_record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path.home() / ".claude" / "scripts",
        help="installation directory (defaults to ~/.claude/scripts)",
    )
    parser.add_argument(
        "--python",
        type=Path,
        default=None,
        help="trusted Python interpreter to record (defaults to this interpreter)",
    )
    args = parser.parse_args(argv)
    guard, record = install(args.target_dir, interpreter=args.python)
    print(f"Installed reviewer guard: {guard}")
    print(f"Recorded trusted interpreter: {record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
