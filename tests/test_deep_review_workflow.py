"""Deterministic contract tests for the shipped deep-review workflow."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.support import REPO


NODE = shutil.which("node")
WORKFLOW = REPO / "workflows" / "deep-review.js"
ACCEPTANCE_CRITERIA = (
    "correctness, safety, repository convention adherence, and security threat-model "
    "coverage for the enumerated diff"
)


class DeepReviewApprovalEnvelopeTest(unittest.TestCase):
    """A merge verdict exists only when both lanes confirm one immutable envelope."""

    @classmethod
    def setUpClass(cls) -> None:
        if NODE is None:
            raise AssertionError("node is required to execute the shipped JavaScript workflow")
        source = WORKFLOW.read_text(encoding="utf-8")
        body, substitutions = re.subn(
            r"\Aexport const meta = \{.*?^\}\n",
            "",
            source,
            count=1,
            flags=re.DOTALL | re.MULTILINE,
        )
        if substitutions != 1:
            raise AssertionError("could not isolate the deep-review workflow body")
        cls.harness = (
            "const payload = JSON.parse(await new Promise((resolve) => {\n"
            "  let input = '';\n"
            "  process.stdin.setEncoding('utf8');\n"
            "  process.stdin.on('data', (chunk) => { input += chunk });\n"
            "  process.stdin.on('end', () => resolve(input));\n"
            "}));\n"
            "const args = payload.args ?? null;\n"
            "const phase = () => {};\n"
            "const prompts = {};\n"
            "const agent = async (prompt, options) => {\n"
            "  prompts[options.label] = prompt;\n"
            "  return structuredClone(payload.responses[options.label]);\n"
            "};\n"
            "const parallel = async (lanes) => Promise.all(lanes.map((lane) => lane()));\n"
            "const execute = async () => {\n"
            + body
            + "\n};\n"
            "const result = await execute();\n"
            "result._fixture_prompts = prompts;\n"
            "process.stdout.write(JSON.stringify(result));\n"
        )

    def _git(self, repo: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "Workflow Fixture",
                "GIT_AUTHOR_EMAIL": "workflow@example.invalid",
                "GIT_COMMITTER_NAME": "Workflow Fixture",
                "GIT_COMMITTER_EMAIL": "workflow@example.invalid",
            },
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    def _multi_commit_scope(self, repo: Path) -> dict:
        self._git(repo, "init", "--initial-branch=main")
        (repo / "base.txt").write_text("base\n", encoding="utf-8")
        self._git(repo, "add", "base.txt")
        self._git(repo, "commit", "-m", "base")
        self._git(repo, "switch", "-c", "topic")
        (repo / "first.txt").write_text("first\n", encoding="utf-8")
        self._git(repo, "add", "first.txt")
        self._git(repo, "commit", "-m", "first topic commit")
        (repo / "second.txt").write_text("second\n", encoding="utf-8")
        self._git(repo, "add", "second.txt")
        self._git(repo, "commit", "-m", "second topic commit")

        merge_base = self._git(repo, "merge-base", "HEAD", "main")
        exact_parent = self._git(repo, "rev-parse", "HEAD^1")
        self.assertNotEqual(merge_base, exact_parent)
        return {
            "repository": str(repo.resolve()),
            "base_ref": merge_base,
            "base_sha": exact_parent,
            "candidate_sha": self._git(repo, "rev-parse", "HEAD"),
            "head_sha": self._git(repo, "rev-parse", "HEAD"),
            "tree_oid": self._git(repo, "rev-parse", "HEAD^{tree}"),
            "tree_dirty": False,
            "changed_files": ["first.txt", "second.txt"],
            "diff_summary": "first.txt: added\nsecond.txt: added",
        }

    def _expected_envelope(self, scope: dict) -> dict:
        return {
            "repository": scope["repository"],
            "base_sha": scope["base_sha"],
            "candidate_sha": scope["candidate_sha"],
            "tree_oid": scope["tree_oid"],
            "scope": (
                f"ambient diff {scope['base_ref']}..{scope['candidate_sha']}; files: "
                + ", ".join(scope["changed_files"])
            ),
            "acceptance_criteria": ACCEPTANCE_CRITERIA,
        }

    def _packet(self, envelope: dict | None, verdict: str = "approve") -> dict:
        packet = {
            "findings": [],
            "verdict": verdict,
            "not_checked": "nothing",
        }
        if envelope is not None:
            packet["approval_envelope"] = envelope
        return packet

    def _run_workflow(
        self,
        scope: dict,
        *,
        review: dict | None = None,
        security: dict | None = None,
    ) -> dict:
        envelope = self._expected_envelope(scope)
        payload = {
            "args": "main",
            "responses": {
                "scope": scope,
                "review": review or self._packet(envelope),
                "security": security or self._packet(envelope),
            },
        }
        completed = subprocess.run(
            [NODE, "--input-type=module", "--eval", self.harness],
            input=json.dumps(payload),
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def test_multi_commit_branch_merge_binds_exact_parent_not_merge_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scope = self._multi_commit_scope(Path(tmp))
            result = self._run_workflow(scope)

        self.assertEqual("merge", result["verdict"])
        self.assertEqual(self._expected_envelope(scope), result["approval_envelope"])
        self.assertEqual(scope["base_sha"], result["approval_envelope"]["base_sha"])
        self.assertNotEqual(scope["base_ref"], result["approval_envelope"]["base_sha"])

    def test_scope_prompt_discovers_exact_parent_repository_and_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scope = self._multi_commit_scope(Path(tmp))
            result = self._run_workflow(scope)

        prompt = result["_fixture_prompts"]["scope"]
        self.assertRegex(prompt, r"repository \(git rev-parse --show-toplevel\)")
        self.assertRegex(prompt, r"candidate_sha.*\(both git rev-parse HEAD\)")
        self.assertRegex(
            prompt,
            r"base_sha \(git rev-parse HEAD\^1 -- never substitute the merge base\)",
        )
        self.assertRegex(prompt, r"tree_oid \(git rev-parse HEAD\^\{tree\}\)")

    def test_each_lane_prompt_requires_independent_envelope_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scope = self._multi_commit_scope(Path(tmp))
            result = self._run_workflow(scope)

        for lane in ("review", "security"):
            with self.subTest(lane=lane):
                prompt = result["_fixture_prompts"][lane]
                self.assertIn(
                    "independently confirm the repository, HEAD, its exact first parent, "
                    "HEAD^{tree}, and that git status --porcelain is still empty",
                    prompt,
                )
                self.assertIn("copy every supplied approval_envelope field exactly", prompt)

    def test_dirty_tree_reducer_caps_approving_envelope_bearing_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scope = self._multi_commit_scope(Path(tmp))
        scope["tree_dirty"] = True

        result = self._run_workflow(scope)

        self.assertEqual("provisional-commit-and-re-review", result["verdict"])
        self.assertNotIn("approval_envelope", result)
        for lane in ("review", "security"):
            with self.subTest(lane=lane):
                self.assertEqual("approve", result[lane]["verdict"])
                self.assertEqual(
                    self._expected_envelope(scope), result[lane]["approval_envelope"]
                )

    def test_missing_lane_approval_envelope_never_merges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scope = self._multi_commit_scope(Path(tmp))
        valid = self._packet(self._expected_envelope(scope))
        missing = self._packet(None)

        for lane in ("review", "security"):
            with self.subTest(lane=lane):
                packets = {"review": valid, "security": valid, lane: missing}
                result = self._run_workflow(scope, **packets)
                self.assertEqual("inconclusive", result["verdict"])
                self.assertEqual(f"{lane}-approval-envelope", result["failed_lane"])

    def test_each_missing_lane_approval_field_never_merges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scope = self._multi_commit_scope(Path(tmp))
        envelope = self._expected_envelope(scope)

        for lane in ("review", "security"):
            for field in envelope:
                with self.subTest(lane=lane, field=field):
                    incomplete = {key: value for key, value in envelope.items() if key != field}
                    packets = {
                        "review": self._packet(envelope),
                        "security": self._packet(envelope),
                        lane: self._packet(incomplete),
                    }
                    result = self._run_workflow(scope, **packets)
                    self.assertEqual("inconclusive", result["verdict"])
                    self.assertEqual(f"{lane}-approval-envelope", result["failed_lane"])

    def test_each_mismatched_lane_approval_field_never_merges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scope = self._multi_commit_scope(Path(tmp))
        envelope = self._expected_envelope(scope)

        for lane in ("review", "security"):
            for field in envelope:
                with self.subTest(lane=lane, field=field):
                    mismatch = {**envelope, field: f"mismatched-{field}"}
                    packets = {
                        "review": self._packet(envelope),
                        "security": self._packet(envelope),
                        lane: self._packet(mismatch),
                    }
                    result = self._run_workflow(scope, **packets)
                    self.assertEqual("inconclusive", result["verdict"])
                    self.assertEqual(f"{lane}-approval-envelope", result["failed_lane"])


if __name__ == "__main__":
    unittest.main()
