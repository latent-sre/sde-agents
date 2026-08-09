"""Tests for the error-budget calculator shipped with the observability skill.

The arithmetic is quotable in an incident, so it is pinned. The edge case that matters most is a
100% target: it makes the budget zero, and the naive 0/0 guard reported a flawless window as
"BUDGET EXHAUSTED" (found in review) — a script that invents an outage is worse than one that
prints nothing.
"""
from __future__ import annotations

import importlib.util
import unittest

from tests.support import REPO, run_main

_spec = importlib.util.spec_from_file_location(
    "error_budget", REPO / "skills" / "observability" / "scripts" / "error_budget.py"
)
error_budget = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(error_budget)


def run(*argv: str) -> tuple[int, str]:
    return run_main(error_budget.main, *argv)


class Arithmetic(unittest.TestCase):
    def test_budget_minutes(self) -> None:
        # 99.9% of 30 days = 0.1% of 43,200 minutes.
        self.assertAlmostEqual(43.2, error_budget.budget_minutes(99.9, 30), places=6)
        self.assertAlmostEqual(0.0, error_budget.budget_minutes(100, 30), places=6)

    def test_burn_rate_is_the_ratio_of_failure_shares(self) -> None:
        # 1% observed failure against a 0.1% allowance is exactly 10x.
        code, text = run("--target", "99.9", "--window-days", "30", "--observed", "99.0",
                         "--elapsed-hours", "12")
        self.assertEqual(0, code)
        self.assertIn("10.00x", text)
        self.assertIn("36.0 min", text)  # 43.2 total - 7.2 spent


class ZeroBudget(unittest.TestCase):
    def test_perfect_target_with_no_failure_is_not_an_outage(self) -> None:
        code, text = run("--target", "100", "--window-days", "30", "--observed", "100")
        self.assertEqual(0, code)
        self.assertNotIn("EXHAUSTED", text)
        self.assertNotIn("inf", text)
        self.assertIn("budget untouched", text)

    def test_perfect_target_with_any_failure_is_unbounded(self) -> None:
        code, text = run("--target", "100", "--window-days", "30", "--observed", "99.9")
        self.assertEqual(0, code)
        self.assertIn("EXHAUSTED", text)
        self.assertIn("zero budget", text)  # reported honestly, never as a number
        self.assertNotIn("inf%", text)


class Validation(unittest.TestCase):
    def test_rejects_impossible_inputs(self) -> None:
        for argv in (
            ("--target", "150", "--window-days", "30"),
            ("--target", "99.9", "--window-days", "0"),
            ("--target", "99.9", "--window-days", "30", "--observed", "-5"),
        ):
            with self.subTest(argv=argv):
                self.assertEqual(2, run(*argv)[0])


if __name__ == "__main__":
    unittest.main()
