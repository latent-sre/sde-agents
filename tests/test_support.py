"""Tripwires for the shared fixtures in tests/support.py — above all the pooled repo copy.

`repo_copy` promises every borrower a provably pristine tree while reusing one working copy.
A restore bug would not fail the test that hits it; it would leak one test's mutation into the
next and weaken the wiring suite silently — the exact failure mode the mutation tests exist to
prevent. So each mutation type a borrower can perform (change, add, delete, and the same-size
rewrite that stat-based restoration would miss) gets a test proving the next borrower cannot
see it.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from tests import support
from tests.support import repo_copy


def _relative_snapshot(root: Path) -> dict[Path, bytes]:
    return {p.relative_to(root): p.read_bytes() for p in support._walk_files(root)}


class RepoPoolRestoreTests(unittest.TestCase):
    def test_consecutive_borrows_see_identical_pristine_content(self) -> None:
        # The positive control: with no mutation at all, two borrows are byte-identical.
        with repo_copy() as first:
            before = _relative_snapshot(first)
        with repo_copy() as second:
            self.assertEqual(before, _relative_snapshot(second))

    def test_every_mutation_type_is_restored_for_the_next_borrower(self) -> None:
        readme = Path("README.md")
        agents_md = Path("AGENTS.md")
        added = Path("agents") / "phantom.md"
        with repo_copy() as dst:
            original_readme = (dst / readme).read_bytes()
            original_agents = (dst / agents_md).read_bytes()
            (dst / readme).write_text("mutated\n", encoding="utf-8")
            (dst / agents_md).unlink()
            (dst / added).write_text("---\nname: phantom\n---\n", encoding="utf-8")
        with repo_copy() as dst:
            self.assertEqual(original_readme, (dst / readme).read_bytes())
            self.assertEqual(original_agents, (dst / agents_md).read_bytes())
            self.assertFalse((dst / added).exists())

    def test_same_size_rewrite_is_restored(self) -> None:
        # The mutation class a (size, mtime) comparison can miss: identical length, written
        # within the filesystem's timestamp granularity. Content hashing must catch it.
        target = Path("plugin.json")
        with repo_copy() as dst:
            original = (dst / target).read_bytes()
            flipped = bytes(reversed(original))
            self.assertEqual(len(original), len(flipped))
            (dst / target).write_bytes(flipped)
        with repo_copy() as dst:
            self.assertEqual(original, (dst / target).read_bytes())

    def test_file_replaced_by_a_directory_is_restored(self) -> None:
        # The shape mutation Codex review caught on #91: a borrower replaces a tracked file
        # with a directory. Restoration must clear the shadowing directory and put the file
        # back — raising IsADirectoryError here would poison the pool for every later test.
        target = Path("plugin.json")
        with repo_copy() as dst:
            original = (dst / target).read_bytes()
            (dst / target).unlink()
            (dst / target).mkdir()
            (dst / target / "interloper.txt").write_text("shadowed\n", encoding="utf-8")
        with repo_copy() as dst:
            self.assertTrue((dst / target).is_file())
            self.assertEqual(original, (dst / target).read_bytes())

    def test_deleted_directory_contents_are_restored(self) -> None:
        # A borrower that removes a whole subtree (files and all) must not leave the next
        # borrower a hollowed-out repo the validator would judge incorrectly.
        victim = Path("evals") / "routing"
        with repo_copy() as dst:
            files = sorted(p.relative_to(dst) for p in (dst / victim).rglob("*") if p.is_file())
            self.assertTrue(files, "fixture assumption: evals/routing ships files")
            for rel in files:
                (dst / rel).unlink()
        with repo_copy() as dst:
            for rel in files:
                self.assertTrue((dst / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
