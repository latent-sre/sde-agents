"""Tests for the parallel module runner.

The runner replaces the serial CI invocation, so the properties that must not regress are the
ones a green total could otherwise hide: a failing module must fail the whole run, the summary
must aggregate real per-module counts, and discovering nothing must be an error rather than an
empty success — each is pinned against a synthetic module directory, so no test here re-runs
the real suite inside itself.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import run_tests
from tests.support import run_main

PASSING = (
    "import unittest\n"
    "class Ok(unittest.TestCase):\n"
    "    def test_one(self): pass\n"
    "    def test_two(self): pass\n"
)
FAILING = (
    "import unittest\n"
    "class Bad(unittest.TestCase):\n"
    "    def test_broken(self): self.fail('deliberate')\n"
)


class ParallelRunnerTests(unittest.TestCase):
    def _run(self, tmp: Path) -> tuple[int, str]:
        return run_main(run_tests.main, "--start-dir", str(tmp))

    def test_all_green_modules_aggregate_and_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "test_alpha.py").write_text(PASSING, encoding="utf-8")
            (Path(tmp) / "test_beta.py").write_text(PASSING, encoding="utf-8")
            code, out = self._run(Path(tmp))
        self.assertEqual(0, code, out)
        self.assertIn("Ran 4 tests across 2 modules", out)

    def test_one_failing_module_fails_the_run_and_is_named(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "test_alpha.py").write_text(PASSING, encoding="utf-8")
            (Path(tmp) / "test_bad.py").write_text(FAILING, encoding="utf-8")
            code, out = self._run(Path(tmp))
        self.assertEqual(1, code, out)
        self.assertIn("test_bad.py: FAILED", out)
        # The failing module's own traceback must surface without -v, or diagnosing a red CI
        # run would require a local re-run just to see what failed.
        self.assertIn("deliberate", out)

    def test_discovering_no_modules_is_an_error_not_an_empty_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(Path(tmp))
        self.assertEqual(2, code)

    def test_nested_importable_test_package_refuses_to_run(self) -> None:
        # Serial `unittest discover` recurses into importable packages; the runner's top-level
        # glob does not. Diverging silently would leave CI green while never running the nested
        # modules, so the runner must refuse instead (Codex review on #91).
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "test_alpha.py").write_text(PASSING, encoding="utf-8")
            package = Path(tmp) / "subpkg"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "test_hidden.py").write_text(PASSING, encoding="utf-8")
            code, _ = self._run(Path(tmp))
        self.assertEqual(2, code)

    def test_non_importable_fixture_trees_do_not_block_the_run(self) -> None:
        # Fixture repos may carry test-shaped filenames without __init__.py chains; discovery
        # ignores them, so the runner must too rather than refusing to run the real suite.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "test_alpha.py").write_text(PASSING, encoding="utf-8")
            fixture = Path(tmp) / "fixtures" / "sample"
            fixture.mkdir(parents=True)
            (fixture / "test_shaped.py").write_text(FAILING, encoding="utf-8")
            code, out = self._run(Path(tmp))
        self.assertEqual(0, code, out)
        self.assertIn("Ran 2 tests across 1 modules", out)


if __name__ == "__main__":
    unittest.main()
