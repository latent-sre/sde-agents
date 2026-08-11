"""Guards the canary strings scripts/probe_plugin.py depends on to prove skill preloading.

`req_8f3a2c` (skills/backend-craft/SKILL.md, under "## Contract first") and `color courage`
(skills/frontend-craft/SKILL.md, under "## Visual character") read as ordinary prose, but the
probe's oracle for "was this skill preloaded, not read" is exactly "did this string appear in the
transcript" -- see scripts/probe_plugin.py's "sde-fullstack's craft skills are PRELOADED, not read"
section. An innocent copy-edit to either SKILL.md would silently disarm that check: the probe would
still run, still print PASS/FAIL, and never say why the canary stopped matching. This test is the
tripwire.
"""
from __future__ import annotations

import contextlib
import io
import unittest
from unittest import mock

from scripts import probe_plugin
from tests.support import REPO


class ProbeCanaryTests(unittest.TestCase):
    def test_help_exits_before_any_live_probe_or_workspace_change(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(probe_plugin, "run") as run,
            mock.patch.object(probe_plugin, "_remove_workspace") as remove_workspace,
            contextlib.redirect_stdout(output),
            self.assertRaises(SystemExit) as raised,
        ):
            probe_plugin.main(["--help"])

        self.assertEqual(0, raised.exception.code)
        self.assertIn("usage:", output.getvalue())
        run.assert_not_called()
        remove_workspace.assert_not_called()

    def test_backend_craft_canary_is_present(self) -> None:
        text = (REPO / "skills" / "backend-craft" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "req_8f3a2c",
            text,
            "scripts/probe_plugin.py quotes this canary to prove backend-craft was preloaded -- "
            "do not remove or reword it without updating the probe",
        )

    def test_frontend_craft_canary_is_present(self) -> None:
        text = (REPO / "skills" / "frontend-craft" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "color courage",
            text,
            "scripts/probe_plugin.py quotes this canary to prove frontend-craft was preloaded -- "
            "do not remove or reword it without updating the probe",
        )


if __name__ == "__main__":
    unittest.main()
