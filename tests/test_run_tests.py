"""Tests for the parallel module runner.

The runner replaces the serial CI invocation, so the properties that must not regress are the
ones a green total could otherwise hide: a failing module must fail the whole run, the summary
must aggregate real per-module counts, and discovering nothing must be an error rather than an
empty success. Subprocess behavior is pinned end to end; discovery classification and synthetic
child reports are tested in process, so this module does not over-test the runner by repeatedly
starting children when the child process itself is not the subject.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
NON_ASCII_FAILING = (
    "import unittest\n"
    "class Bad(unittest.TestCase):\n"
    "    def test_broken(self): self.fail('em dash —')\n"
)
RAW_BYTES_FAILING = (
    "import os, unittest\n"
    "class Raw(unittest.TestCase):\n"
    "    def test_raw(self):\n"
    "        os.write(2, bytes([255]))\n"
    "        self.fail('raw child output')\n"
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

    def test_child_output_is_forced_to_utf8_even_under_a_legacy_parent_encoding(self) -> None:
        """Windows CI must not decode CP-1252 test output into an unprintable replacement char."""
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / "test_non_ascii.py"
            module.write_text(NON_ASCII_FAILING, encoding="utf-8")
            with mock.patch.dict(os.environ, {"PYTHONIOENCODING": "cp1252"}):
                _, code, output, _ = run_tests.run_module(Path(tmp), module, [])

        self.assertEqual(1, code)
        self.assertIn("em dash —", output)
        self.assertNotIn("\ufffd", output)

    def test_raw_child_bytes_do_not_crash_the_parent_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / "test_raw.py"
            module.write_text(RAW_BYTES_FAILING, encoding="utf-8")
            code, output = self._run(Path(tmp))

        self.assertEqual(1, code, output)
        self.assertIn("test_raw.py: FAILED", output)
        self.assertIn(r"\xff", output)
        self.assertIn("raw child output", output)
        self.assertIn("Ran 1 tests across 1 modules", output)

    def test_discovering_no_modules_is_an_error_not_an_empty_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(Path(tmp))
        self.assertEqual(2, code)

    def test_zero_or_unparseable_child_count_cannot_pass_the_run(self) -> None:
        # Modern unittest already exits 5 when it discovers zero tests. A real empty
        # child would therefore exercise the generic child-failure path and leave the runner's
        # count guard unproved. Synthetic successful reports make both added branches fire and
        # prove the runner itself—not this interpreter version—rejects lost coverage.
        reports = {
            "zero": "Ran 0 tests in 0.000s\n\nOK\n",
            "unparseable": "child completed without a unittest summary\n",
        }
        for name, report in reports.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                module = Path(tmp) / "test_report.py"
                module.write_text("# run_module is replaced below\n", encoding="utf-8")
                result = (module, 0, report, ["python", "-m", "unittest"])
                with mock.patch.object(run_tests, "run_module", return_value=result):
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

    def test_package_with_only_a_load_tests_hook_also_refuses_to_run(self) -> None:
        # A package __init__ carrying load_tests contributes tests on EVERY discovery pass, so
        # per-module children would run them once per top-level module instead of once per
        # suite (Codex review on #91). No nested test_*.py file exists to trip the other
        # guard, so the package itself must be the tripwire.
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "hookpkg"
            package.mkdir()
            (package / "__init__.py").write_text(
                "def load_tests(loader, tests, pattern):\n    return tests\n",
                encoding="utf-8",
            )
            self.assertEqual([package], run_tests.importable_packages(Path(tmp)))

    def test_non_importable_fixture_trees_do_not_block_the_run(self) -> None:
        # Fixture repos may carry test-shaped filenames — or even real sample packages — below
        # a container without __init__.py. Discovery never descends through the container, so
        # the runner must ignore them too rather than refusing to run the real suite (Codex
        # review on #91: only an unbroken __init__.py chain participates in discovery).
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fixtures" / "sample"
            fixture.mkdir(parents=True)
            (fixture / "test_shaped.py").write_text(FAILING, encoding="utf-8")
            (fixture / "__init__.py").write_text("", encoding="utf-8")
            self.assertEqual([], run_tests.importable_packages(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
