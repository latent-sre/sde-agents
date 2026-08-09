"""Tripwires for the shared fixtures in tests/support.py — above all the pooled repo copy.

`repo_copy` promises every borrower a provably pristine tree while reusing one working copy.
A restore bug would not fail the test that hits it; it would leak one test's mutation into the
next and weaken the wiring suite silently — the exact failure mode the mutation tests exist to
prevent. So each mutation type a borrower can perform (change, add, delete, and the same-size
rewrite that stat-based restoration would miss) gets a test proving the next borrower cannot
see it.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tests import support
from tests.support import create_directory_link, repo_copy


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

    def test_added_directory_is_removed_not_left_as_an_empty_shell(self) -> None:
        # Removing an added file but keeping its new parent directory is not pristine: an empty
        # skills/<name>/ reads to validate_skills() as a skill missing its SKILL.md, so a
        # leftover shell hands later borrowers a tree the validator judges differently
        # (Codex review on #91).
        added = Path("skills") / "phantom" / "SKILL.md"
        with repo_copy() as dst:
            (dst / added).parent.mkdir(parents=True)
            (dst / added).write_text("---\nname: phantom\n---\n", encoding="utf-8")
        with repo_copy() as dst:
            self.assertFalse((dst / added).parent.exists())

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

    def test_symlink_mutation_is_unlinked_never_written_through(self) -> None:
        # A borrower that replaces a tracked file with a symlink must not make the NEXT restore
        # write pristine content through the link to a target outside the pool (Codex review on
        # #91). The link is residue to remove, and the outside target must stay untouched.
        target = Path("plugin.json")
        with tempfile.TemporaryDirectory() as outside_dir:
            victim = Path(outside_dir) / "victim.txt"
            victim.write_text("outside content\n", encoding="utf-8")
            with repo_copy() as dst:
                original = (dst / target).read_bytes()
                (dst / target).unlink()
                try:
                    (dst / target).symlink_to(victim)
                except OSError as exc:  # e.g. Windows without symlink privilege
                    (dst / target).write_bytes(original)
                    self.skipTest(f"cannot create symlinks here: {exc}")
            with repo_copy() as dst:
                self.assertFalse((dst / target).is_symlink())
                self.assertEqual(original, (dst / target).read_bytes())
            self.assertEqual("outside content\n", victim.read_text(encoding="utf-8"))

    def test_directory_replaced_by_a_link_is_restored_without_writing_through(self) -> None:
        # The directory variant of the symlink escape, which on Windows is a JUNCTION that
        # is_symlink() does not report (Codex review on #91): restoration must remove the link
        # primitive itself and rebuild the real directory, never writing into the link target.
        victim_dir = Path("hooks")
        with tempfile.TemporaryDirectory() as outside_dir:
            outside = Path(outside_dir) / "decoy"
            outside.mkdir()
            with repo_copy() as dst:
                originals = {
                    p.name: p.read_bytes() for p in (dst / victim_dir).iterdir() if p.is_file()
                }
                self.assertTrue(originals, "fixture assumption: hooks/ ships files")
                shutil.rmtree(dst / victim_dir)
                try:
                    create_directory_link(outside, dst / victim_dir)
                except OSError as exc:
                    self.skipTest(f"cannot create directory links here: {exc}")
            with repo_copy() as dst:
                for name, content in originals.items():
                    self.assertEqual(content, (dst / victim_dir / name).read_bytes(), name)
            self.assertEqual([], list(outside.iterdir()), "restore wrote through the link")

    def test_hard_link_mutation_is_broken_never_written_through(self) -> None:
        # A hard link is invisible to symlink checks: copyfile onto the entry would write
        # through the SHARED inode into a file outside the pool, and a link whose content
        # already matches would survive restoration and expose later borrows' writes (Codex
        # review on #91). Both variants: differing content, and matching content.
        target = Path("plugin.json")
        with tempfile.TemporaryDirectory() as outside_dir:
            differing = Path(outside_dir) / "differing.txt"
            differing.write_text("outside content\n", encoding="utf-8")
            matching = Path(outside_dir) / "matching.bin"
            with repo_copy() as dst:
                original = (dst / target).read_bytes()
                matching.write_bytes(original)
                (dst / target).unlink()
                try:
                    os.link(differing, dst / target)
                except OSError as exc:  # filesystem without hard-link support
                    (dst / target).write_bytes(original)
                    self.skipTest(f"cannot create hard links here: {exc}")
            with repo_copy() as dst:
                self.assertEqual(original, (dst / target).read_bytes())
                self.assertEqual(1, (dst / target).stat().st_nlink)
            self.assertEqual("outside content\n", differing.read_text(encoding="utf-8"))

            with repo_copy() as dst:
                (dst / target).unlink()
                os.link(matching, dst / target)  # same bytes as the manifest expects
            with repo_copy() as dst:
                self.assertEqual(1, (dst / target).stat().st_nlink)
                (dst / target).write_bytes(b"in-pool write\n")
            self.assertEqual(original, matching.read_bytes(), "write leaked through hard link")

    def test_cyclic_ancestor_link_is_removed_without_recursing_into_it(self) -> None:
        # A directory link pointing at an ANCESTOR of the pool creates a cycle. Enumeration
        # that descends before removing (rglob into a Windows junction, which the symlink-skip
        # does not cover) would recurse until path-length exhaustion; the top-down removal
        # walk must delete the link before ever descending (Codex review on #91).
        victim_dir = Path("hooks")
        with repo_copy() as dst:
            originals = {
                p.name: p.read_bytes() for p in (dst / victim_dir).iterdir() if p.is_file()
            }
            shutil.rmtree(dst / victim_dir)
            try:
                create_directory_link(dst, dst / victim_dir)
            except OSError as exc:
                self.skipTest(f"cannot create directory links here: {exc}")
        with repo_copy() as dst:
            self.assertFalse((dst / victim_dir).is_symlink())
            for name, content in originals.items():
                self.assertEqual(content, (dst / victim_dir / name).read_bytes(), name)

    def test_dangling_directory_link_is_removed_and_restored(self) -> None:
        # The dispatch must not follow the link: is_dir() on a DANGLING link answers for the
        # missing target and picks the wrong removal call, poisoning the pool (Codex review on
        # #91). Delete the link's target before restoration to force that state.
        victim_dir = Path("hooks")
        with tempfile.TemporaryDirectory() as outside_dir:
            outside = Path(outside_dir) / "vanishing"
            outside.mkdir()
            with repo_copy() as dst:
                originals = {
                    p.name: p.read_bytes() for p in (dst / victim_dir).iterdir() if p.is_file()
                }
                shutil.rmtree(dst / victim_dir)
                try:
                    create_directory_link(outside, dst / victim_dir)
                except OSError as exc:
                    self.skipTest(f"cannot create directory links here: {exc}")
                outside.rmdir()  # the link now dangles
            with repo_copy() as dst:
                for name, content in originals.items():
                    self.assertEqual(content, (dst / victim_dir / name).read_bytes(), name)

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
