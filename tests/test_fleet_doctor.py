from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scripts import fleet_doctor
from tests.support import REPO


class FleetDoctorTests(unittest.TestCase):
    def test_command_allowlist_rejects_mutating_or_model_commands(self) -> None:
        fleet_doctor._assert_read_only_command(
            ("git", "--no-optional-locks", "-C", str(REPO), "status", "--short")
        )
        fleet_doctor._assert_read_only_command(("claude", "plugin", "list"))
        for command in (
            ("git", "--no-optional-locks", "-C", str(REPO), "fetch"),
            ("git", "-C", str(REPO), "status", "--short"),
            ("claude", "plugin", "install", "sde-agents"),
            ("codex", "exec", "inspect this repo"),
            ("python", "scripts/generate_platform_adapters.py", "--write"),
        ):
            with self.subTest(command=command):
                with self.assertRaisesRegex(ValueError, "read-only allowlist"):
                    fleet_doctor._assert_read_only_command(command)

    def test_report_uses_only_read_only_commands_and_does_not_touch_home(self) -> None:
        calls: list[tuple[str, ...]] = []

        def run(argv: tuple[str, ...]) -> fleet_doctor.CommandResult:
            calls.append(tuple(argv))
            fleet_doctor._assert_read_only_command(argv)
            if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
                return fleet_doctor.CommandResult(0, "a" * 40 + "\n", "")
            if tuple(argv[-2:]) == ("status", "--short"):
                return fleet_doctor.CommandResult(0, "", "")
            if tuple(argv[-2:]) == ("plugin", "list"):
                return fleet_doctor.CommandResult(0, "sde-agents 1.4.0\n", "")
            return fleet_doctor.CommandResult(0, "test-cli 1.0\n", "")

        def which(command: str) -> str:
            return str(Path("C:/tools") / f"{command}.exe")

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            codex_home = Path(temporary) / "codex"
            home.mkdir()
            sentinel = home / "sentinel.txt"
            sentinel.write_text("unchanged\n", encoding="utf-8")
            before = {path.relative_to(home): path.read_bytes() for path in home.rglob("*") if path.is_file()}

            with mock.patch.object(
                fleet_doctor,
                "_repository_checks",
                return_value=[
                    fleet_doctor.Check(
                        "repository.generated-adapters",
                        "pass",
                        "fixture repository is current",
                    )
                ],
            ):
                report = fleet_doctor.collect_report(
                    REPO,
                    home=home,
                    codex_home=codex_home,
                    run=run,
                    which=which,
                    now=datetime(2026, 7, 31, tzinfo=timezone.utc),
                )

            after = {path.relative_to(home): path.read_bytes() for path in home.rglob("*") if path.is_file()}

        self.assertEqual(before, after)
        self.assertTrue(calls)
        for argv in calls:
            fleet_doctor._assert_read_only_command(argv)
            self.assertFalse({"install", "update", "fetch", "prune", "exec"} & set(argv))
            if Path(argv[0]).stem.lower() == "git":
                self.assertIn("--no-optional-locks", argv)
        self.assertEqual(1, report["schema_version"])
        self.assertEqual("2026-07-31T00:00:00Z", report["generated_at"])
        self.assertGreaterEqual(report["summary"]["pass"], 1)

    def test_junction_mode_without_plugin_reports_dormant_guard(self) -> None:
        def run(argv: tuple[str, ...]) -> fleet_doctor.CommandResult:
            if tuple(argv[-2:]) == ("plugin", "list"):
                return fleet_doctor.CommandResult(0, "other-plugin\n", "")
            return fleet_doctor.CommandResult(0, "test-cli 1.0\n", "")

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            codex_home = base / "codex"
            with mock.patch.object(fleet_doctor, "_same_location", return_value=True):
                checks = fleet_doctor._installation_checks(
                    REPO,
                    base,
                    {"claude": "claude"},
                    run,
                    codex_home=codex_home,
                )

        by_id = {check.check_id: check for check in checks}
        self.assertEqual("warn", by_id["host.claude.deployment"].status)
        self.assertEqual("warn", by_id["host.claude.readonly-guard"].status)
        self.assertIn("dormant", by_id["host.claude.readonly-guard"].summary)

    def test_main_exits_one_only_for_failing_checks(self) -> None:
        report = {
            "schema_version": 1,
            "generated_at": "2026-07-31T00:00:00Z",
            "root": str(REPO),
            "summary": {
                "pass": 0,
                "warn": 0,
                "fail": 1,
                "skip": 0,
                "inconclusive": 0,
            },
            "checks": [
                {
                    "check_id": "fixture.failure",
                    "status": "fail",
                    "summary": "fixture failed",
                    "details": {},
                }
            ],
        }
        output = io.StringIO()
        with mock.patch.object(fleet_doctor, "collect_report", return_value=report):
            with redirect_stdout(output):
                exit_code = fleet_doctor.main(["--json"])
        self.assertEqual(1, exit_code)
        self.assertIn('"fixture.failure"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
