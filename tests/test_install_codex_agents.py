from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import install_codex_agents


class InstallCodexAgentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "source"
        self.target = self.root / "target"
        self.source.mkdir()
        (self.source / "reviewer.toml").write_text(
            "# generated\nname = \"reviewer\"\n",
            encoding="utf-8",
        )
        (self.source / "builder.toml").write_text(
            "# generated\nname = \"builder\"\n",
            encoding="utf-8",
        )

    def test_install_writes_managed_copies_and_then_is_idempotent(self) -> None:
        plan = install_codex_agents.build_sync_plan(self.source, self.target)
        self.assertEqual(2, len(plan.writes))
        self.assertFalse(plan.conflicts)

        install_codex_agents.apply_sync_plan(plan)
        reviewer = (self.target / "reviewer.toml").read_text(encoding="utf-8")
        self.assertTrue(reviewer.startswith(install_codex_agents.INSTALL_MARKER))

        second_plan = install_codex_agents.build_sync_plan(self.source, self.target)
        self.assertFalse(second_plan.out_of_sync)

    def test_exact_unmarked_generated_copy_is_safely_adopted(self) -> None:
        self.target.mkdir()
        source_content = (self.source / "reviewer.toml").read_bytes()
        (self.target / "reviewer.toml").write_bytes(source_content)

        plan = install_codex_agents.build_sync_plan(self.source, self.target)
        self.assertIn(self.target / "reviewer.toml", dict(plan.writes))
        self.assertFalse(plan.conflicts)

        install_codex_agents.apply_sync_plan(plan)
        installed = (self.target / "reviewer.toml").read_text(encoding="utf-8")
        self.assertTrue(installed.startswith(install_codex_agents.INSTALL_MARKER))

    def test_unmanaged_collision_aborts_before_any_change(self) -> None:
        self.target.mkdir()
        conflict = self.target / "reviewer.toml"
        conflict.write_text("user-owned\n", encoding="utf-8")

        plan = install_codex_agents.build_sync_plan(self.source, self.target)
        self.assertEqual((conflict,), plan.conflicts)
        with self.assertRaisesRegex(ValueError, "refusing to overwrite unmanaged"):
            install_codex_agents.apply_sync_plan(plan)

        self.assertEqual("user-owned\n", conflict.read_text(encoding="utf-8"))
        self.assertFalse((self.target / "builder.toml").exists())

    def test_prune_removes_only_stale_managed_agents(self) -> None:
        self.target.mkdir()
        stale = self.target / "stale.toml"
        stale.write_text(
            f"{install_codex_agents.INSTALL_MARKER}\nname = \"stale\"\n",
            encoding="utf-8",
        )
        unmanaged = self.target / "personal.toml"
        unmanaged.write_text("name = \"personal\"\n", encoding="utf-8")

        plan = install_codex_agents.build_sync_plan(self.source, self.target)
        self.assertEqual((stale,), plan.removals)
        install_codex_agents.apply_sync_plan(plan)

        self.assertFalse(stale.exists())
        self.assertEqual(
            "name = \"personal\"\n",
            unmanaged.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
