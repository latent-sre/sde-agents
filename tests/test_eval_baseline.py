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

    def test_cluster_bytes_the_scorer_cannot_read_stay_reusable(self) -> None:
        """Risk: a comment-only cluster edit re-buys a capture that measured identical routing.

        `eval_sources` hashes each cluster file whole, so editing `notes`, the top-level
        `description`, or an unselected case invalidated every stored baseline for it — while
        `selection` already pinned the graded fields of the exact selected cases. Restore
        `eval_sources` to the compared set in eval_baseline.provenance_divergences and this fails.
        """
        mutated = copy.deepcopy(self.desired)
        mutated["eval_sources"] = [
            {"path": "evals/routing/prompt-tooling.json", "sha256": "0" * 64}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            self._write_benchmark(Path(tmp), mutated, dict(CONDITIONS))
            code, out = self._run(Path(tmp))
        self.assertEqual(0, code, out)
        self.assertIn("REUSABLE", out)

    def test_selection_identity_ignores_documentation_only_case_fields(self) -> None:
        """`expected_output` and `tags` are intent, not inputs: the scorer never reads them."""
        sys.path.insert(0, str(REPO / "scripts"))
        import eval_routing  # noqa: PLC0415

        base = {
            "id": "pos-x", "polarity": "positive", "prompt": "p",
            "expect_fires": ["prompt-craft"],
        }
        documented = dict(base, expected_output="a prose note", tags=["near-miss"])
        self.assertEqual(
            eval_routing.selection_identity("*", [base])["sha256"],
            eval_routing.selection_identity("*", [documented])["sha256"],
        )
        # A graded field still moves it.
        regraded = dict(base, expect_fires=["prompt-engineer"])
        self.assertNotEqual(
            eval_routing.selection_identity("*", [base])["sha256"],
            eval_routing.selection_identity("*", [regraded])["sha256"],
        )

    def test_membership_is_part_of_the_selection_identity(self) -> None:
        """Risk: dropping the whole-file `eval_sources` check also dropped membership from identity.

        A cluster's `members` list is a grading input, not documentation — a negative with no
        `expect_not_fires` is scored against the whole member list, so adding or removing a member
        changes what identical case bytes assert. `eval_sources` used to catch that as a side effect
        of hashing the file whole; once it stopped being compared, only `selection` can. Drop
        `members` from `selection_identity` and this fails in both directions.
        """
        sys.path.insert(0, str(REPO / "scripts"))
        import eval_routing  # noqa: PLC0415

        case = {"id": "neg-x", "polarity": "negative", "prompt": "p"}
        two = eval_routing.selection_identity("*", [case], members=["prompt-craft", "sde-fullstack"])
        three = eval_routing.selection_identity(
            "*", [case], members=["prompt-craft", "sde-fullstack", "code-reviewer"]
        )
        self.assertNotEqual(two["sha256"], three["sha256"])
        # Order is not a grading fact — the scorer intersects against a set.
        reordered = eval_routing.selection_identity(
            "*", [case], members=["sde-fullstack", "prompt-craft"]
        )
        self.assertEqual(two["sha256"], reordered["sha256"])
        # And the resolver's own desired identity must actually carry membership. A None here is the
        # silent failure: the field exists, the hash is stable, and the check enforces nothing.
        self.assertIsNotNone(self.desired["selection"]["members"])

    def test_a_membership_change_stales_a_stored_benchmark(self) -> None:
        """The resolver end of the rule above: identity must reach the REUSABLE/STALE verdict."""
        mutated = copy.deepcopy(self.desired)
        mutated["selection"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            self._write_benchmark(Path(tmp), mutated, dict(CONDITIONS))
            code, out = self._run(Path(tmp))
        self.assertEqual(1, code, out)
        self.assertIn("selection", out)

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
