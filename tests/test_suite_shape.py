"""Every test module must load at least one test.

Risk hypothesis: `python -m unittest discover` reports only the aggregate count, so a module that
loses every test — a rename that breaks the `test_` prefix, an import guard that skips the class,
a file emptied by a bad merge — exits green while its coverage silently vanishes. The retired
parallel runner failed any module that ran zero tests; this keeps that tripwire without a runner.
"""
from __future__ import annotations

import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent


class SuiteShapeTests(unittest.TestCase):
    def test_every_test_module_loads_at_least_one_test(self) -> None:
        modules = sorted(p for p in TESTS.glob("test_*.py") if p.name != Path(__file__).name)
        self.assertGreater(len(modules), 0, "no test modules found beside this file")
        loader = unittest.TestLoader()
        empty: list[str] = []
        for path in modules:
            suite = loader.loadTestsFromName(f"tests.{path.stem}")
            if suite.countTestCases() == 0:
                empty.append(path.name)
        self.assertEqual(
            [],
            empty,
            "test modules that load zero tests — a lost or misnamed test class passes the whole "
            f"suite silently: {empty}",
        )


if __name__ == "__main__":
    unittest.main()
