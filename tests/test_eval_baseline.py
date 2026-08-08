"""Unit tests for the offline baseline resolver.

Everything runs against synthetic benchmark.json files in a temp baselines directory. The one
real computation is the desired provenance over THIS repository (computed once per class);
mutating a copy of it simulates each way a stored artifact can go stale. No test launches a
session, reads credentials, or touches the network — the resolver's whole point is that a
REUSABLE verdict costs nothing.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import REPO, run_main

sys.path.insert(0, str(REPO / "scripts"))

import eval_baseline  # noqa: E402

CLUSTER = REPO / "evals" / "routing" / "prompt-tooling.json"
CONDITIONS = {"model_requested": "sonnet", "clean_room": True, "threshold": 0.5,
              "timeout_s": 420, "cli_version": "2.1.220 (Claude Code)"}
ARGS = ["--model", "sonnet", "--clean-room", "--timeout", "420", str(CLUSTER)]


class EvalBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.desired = eval_baseline.desired_provenance(REPO, CLUSTER, "*", 0)

    def _write_benchmark(self, root: Path, provenance: dict, conditions: dict) -> Path:
        out = root / "2026-08-08-synthetic" / "routing-prompt-tooling"
        out.mkdir(parents=True)
        path = out / "benchmark.json"
        path.write_text(json.dumps({
            "cluster": "prompt-tooling", "conditions": conditions, "provenance": provenance,
        }), encoding="utf-8")
        return path

    def _run(self, baselines: Path) -> tuple[int, str]:
        return run_main(eval_baseline.main, "--baselines-dir", str(baselines), *ARGS)

    def test_exact_match_is_reusable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_benchmark(Path(tmp), self.desired, dict(CONDITIONS))
            code, out = self._run(Path(tmp))
        self.assertEqual(0, code, out)
        self.assertIn("REUSABLE", out)
        self.assertIn(path.parent.name, out)

    def test_changed_plugin_bytes_are_stale_and_named(self) -> None:
        mutated = copy.deepcopy(self.desired)
        mutated["plugin"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            self._write_benchmark(Path(tmp), mutated, dict(CONDITIONS))
            code, out = self._run(Path(tmp))
        self.assertEqual(1, code, out)
        self.assertIn("plugin", out)

    def test_changed_model_is_stale_and_named(self) -> None:
        conditions = dict(CONDITIONS, model_requested="opus")
        with tempfile.TemporaryDirectory() as tmp:
            self._write_benchmark(Path(tmp), self.desired, conditions)
            code, out = self._run(Path(tmp))
        self.assertEqual(1, code, out)
        self.assertIn("model_requested", out)

    def test_older_provenance_schema_is_stale(self) -> None:
        mutated = copy.deepcopy(self.desired)
        mutated["schema"] = "sde-agents/eval-provenance/v1"
        with tempfile.TemporaryDirectory() as tmp:
            self._write_benchmark(Path(tmp), mutated, dict(CONDITIONS))
            code, out = self._run(Path(tmp))
        self.assertEqual(1, code, out)
        self.assertIn("schema", out)

    def test_cli_version_difference_alone_stays_reusable(self) -> None:
        conditions = dict(CONDITIONS, cli_version="9.9.9 (Claude Code)")
        with tempfile.TemporaryDirectory() as tmp:
            self._write_benchmark(Path(tmp), self.desired, conditions)
            code, out = self._run(Path(tmp))
        self.assertEqual(0, code, out)
        self.assertIn("cli_version", out)  # advisory note, not a stale verdict

    def test_empty_baselines_directory_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out = self._run(Path(tmp))
        self.assertEqual(1, code, out)
        self.assertIn("STALE", out)


if __name__ == "__main__":
    unittest.main()
