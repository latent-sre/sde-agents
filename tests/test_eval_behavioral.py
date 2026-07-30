"""Offline tests for scripts/eval_behavioral.py — conditions, usage, and the scratch cwd.

EVAL-002's failure class: an artifact that cannot state what it measured. The live run on
2026-07-29 proved it twice — behavioral sessions ran on an unpinned, unrecorded model, and the
`%TEMP%` scratch cwd silently blocked the writes one case's premise depends on. These tests pin
the repairs: the shared transcript read reports usage or its absence honestly, the benchmark
records its conditions, and the scratch cwd stays out of the directory tree the CLI sandbox
write-blocks.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import eval_behavioral, eval_routing

REPO = Path(__file__).resolve().parents[1]


def result_event(usage: dict | None, duration_ms: int = 1234) -> str:
    event: dict = {"type": "result", "result": "done", "duration_ms": duration_ms}
    if usage is not None:
        event["usage"] = usage
    return json.dumps(event)


def assistant_event(model: str | None = None, text: str = "hi") -> str:
    message: dict = {"content": [{"type": "text", "text": text}]}
    if model:
        message["model"] = model
    return json.dumps({"type": "assistant", "message": message})


class TranscriptStatsTest(unittest.TestCase):
    """The single shared read both runners describe their conditions from."""

    def test_complete_usage_is_read_with_input_and_output_separated(self) -> None:
        stats = eval_routing.transcript_stats(
            assistant_event(model="claude-opus-5")
            + "\n"
            + result_event({"input_tokens": 100, "output_tokens": 25})
        )
        self.assertEqual(100, stats["input_tokens"])
        self.assertEqual(25, stats["output_tokens"])
        self.assertEqual("claude-opus-5", stats["model"])
        self.assertEqual(1234, stats["duration_ms"])
        self.assertTrue(stats["completed"])

    def test_missing_usage_is_none_not_zero(self) -> None:
        # Absent usage must be reported as UNAVAILABLE, never as a zero-token run — a zero would
        # read as "this session was free" in a cost comparison, which is the quiet-wrong shape.
        stats = eval_routing.transcript_stats(result_event(usage=None))
        self.assertIsNone(stats["input_tokens"])
        self.assertIsNone(stats["output_tokens"])
        self.assertTrue(stats["completed"])

    def test_no_result_event_means_not_completed(self) -> None:
        stats = eval_routing.transcript_stats(assistant_event(model="claude-sonnet-5"))
        self.assertFalse(stats["completed"])
        self.assertEqual("claude-sonnet-5", stats["model"])

    def test_malformed_lines_do_not_crash(self) -> None:
        stats = eval_routing.transcript_stats("not json\n{bad\n")
        self.assertIsNone(stats["model"])
        self.assertFalse(stats["completed"])

    def test_run_once_token_sum_matches_the_shared_read(self) -> None:
        # run_once's artifact keeps its summed `tokens` field; the sum must come from the same
        # read, or the two runners' artifacts could disagree about one transcript.
        stdout = result_event({"input_tokens": 10, "output_tokens": 5})
        stats = eval_routing.transcript_stats(stdout)
        self.assertEqual(15, (stats["input_tokens"] or 0) + (stats["output_tokens"] or 0))


class ScratchCwdTest(unittest.TestCase):
    """%TEMP% write-blocking voided packet-slots-builder's premise (observed CLI 2.1.220)."""

    def test_scratch_root_is_not_under_the_temp_tree(self) -> None:
        temp_root = Path(tempfile.gettempdir()).resolve()
        scratch = eval_behavioral.SCRATCH_ROOT.resolve()
        self.assertNotIn(temp_root, [scratch, *scratch.parents])

    def test_scratch_cwd_exists_during_and_is_removed_after(self) -> None:
        with eval_behavioral.scratch_cwd() as cwd:
            self.assertTrue(cwd.is_dir())
            (cwd / "probe.txt").write_text("x", encoding="utf-8")
        self.assertFalse(cwd.exists())


class BenchmarkConditionsTest(unittest.TestCase):
    """The benchmark must state what it measured: model, timeout, CLI, and per-run usage."""

    def _run_main(self, tmp: Path, stats_by_run: list[dict]) -> dict:
        calls = iter(stats_by_run)

        def fake_run_session(prompt, plugin_dir, timeout, disallowed_tools=None,
                             agent=None, permission_mode=None, model=None, env=None):
            stats = next(calls)
            return "the plan targets a scratch container — approval before I apply", \
                {"homelab-platform"}, None, stats

        original_run = eval_behavioral.run_session
        original_claude = eval_behavioral.CLAUDE
        eval_behavioral.run_session = fake_run_session
        eval_behavioral.CLAUDE = "claude"  # sentinel so main() doesn't short-circuit on None
        try:
            code = eval_behavioral.main([
                "--case", "tier-gate-holds", "--runs", str(len(stats_by_run)),
                "--model", "opus", "--timeout", "77", "--output-dir", str(tmp),
            ])
        finally:
            eval_behavioral.run_session = original_run
            eval_behavioral.CLAUDE = original_claude
        self.assertIn(code, (0, 1))
        return json.loads((tmp / "benchmark.json").read_text(encoding="utf-8"))

    def _stats(self, model: str | None = "claude-opus-5", tokens: bool = True) -> dict:
        return {
            "input_tokens": 100 if tokens else None,
            "output_tokens": 30 if tokens else None,
            "duration_ms": 5, "model": model, "completed": True,
        }

    def test_conditions_block_records_what_ran(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(Path(tmp), [self._stats()])
        conditions = payload["conditions"]
        self.assertEqual("opus", conditions["model_requested"])
        self.assertEqual(77, conditions["timeout_s"])
        self.assertEqual(["claude-opus-5"], conditions["models_observed"])
        self.assertIn("cli_version", conditions)
        # Isolation is a measurement condition: without this key, a clean-room artifact and a
        # contaminated one look identical and would be diffed as if comparable.
        self.assertEqual(False, conditions["clean_room"])

    def test_usage_is_recorded_per_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(Path(tmp), [self._stats(), self._stats()])
        case = payload["cases"][0]
        self.assertEqual(
            [{"input_tokens": 100, "output_tokens": 30}] * 2, case["usage_per_run"]
        )

    def test_unavailable_usage_is_labeled_null_not_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._run_main(Path(tmp), [self._stats(tokens=False)])
        self.assertEqual([None], payload["cases"][0]["usage_per_run"])


if __name__ == "__main__":
    unittest.main()
