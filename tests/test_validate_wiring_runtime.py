from __future__ import annotations

import unittest
import json
from pathlib import Path

from scripts import validate_fleet
from tests.support import repo_copy
from tests.validate_fleet_wiring_support import PluginWiringMixin


class PluginWiringRuntimeTests(PluginWiringMixin, unittest.TestCase):
    def test_learning_closeout_wording_cannot_keep_the_marker_but_lose_durable_intake(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            text = path.read_text(encoding="utf-8")
            old = "receiving coordinator verifies and triages them"
            assert old in text, "positive control: researcher must declare durable intake"
            path.write_text(
                text.replace(old, "caller may mention them later", 1),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "researcher.md" in issue
                and "Learning" in issue
                and "drifted" in issue
                for issue in issues
            ),
            issues,
        )

    def test_non_preloaded_agent_cannot_claim_lifecycle_owner_closeout(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            text = path.read_text(encoding="utf-8")
            intake = validate_fleet.LEARNING_INTAKE_PACKET_SLOT
            assert intake in text, "positive control: researcher must use intake-only Learning"
            path.write_text(
                text.replace(
                    intake,
                    validate_fleet.LEARNING_LIFECYCLE_OWNER_PACKET_SLOT,
                    1,
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "researcher.md" in issue
                and "intake" in issue.lower()
                and "lifecycle-owner" in issue.lower()
                for issue in issues
            ),
            issues,
        )

    def test_each_lifecycle_owner_cannot_fall_back_to_intake_closeout(self) -> None:
        lifecycle_owners = {
            "prompt-engineer",
            "sde-fullstack",
            "verification-engineer",
        }
        self.assertEqual(
            frozenset(lifecycle_owners),
            validate_fleet.SELF_IMPROVE_LOOP_PRELOAD_AGENTS,
        )
        for name in sorted(lifecycle_owners):
            with self.subTest(name=name):
                def mutate(repo: Path) -> None:
                    path = repo / "agents" / f"{name}.md"
                    text = path.read_text(encoding="utf-8")
                    lifecycle = validate_fleet.LEARNING_LIFECYCLE_OWNER_PACKET_SLOT
                    assert lifecycle in text, (
                        f"positive control: {name} must use lifecycle-owner Learning"
                    )
                    path.write_text(
                        text.replace(
                            lifecycle,
                            validate_fleet.LEARNING_INTAKE_PACKET_SLOT,
                            1,
                        ),
                        encoding="utf-8",
                    )

                issues = self._issues_after(mutate)
                self.assertTrue(
                    any(
                        f"{name}.md" in issue
                        and "lifecycle-owner" in issue.lower()
                        and "intake" in issue.lower()
                        for issue in issues
                    ),
                    issues,
                )

    def test_self_improve_loop_preload_roster_cannot_silently_drift(self) -> None:
        # Exercise both halves of "only these three": dropping an owner loses full disposition;
        # adding an evidence-only role spends context and can imply authority that role lacks.
        def drop_required_preload(repo: Path) -> None:
            path = repo / "agents" / "prompt-engineer.md"
            text = path.read_text(encoding="utf-8")
            anchor = "skills:\n  - self-improve-loop\n"
            assert anchor in text, "positive control: prompt-engineer must preload the loop"
            path.write_text(text.replace(anchor, "", 1), encoding="utf-8")

        def add_unapproved_preload(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            text = path.read_text(encoding="utf-8")
            anchor = "model: inherit\n"
            assert anchor in text, "positive control: researcher must declare its model"
            path.write_text(
                text.replace(
                    anchor,
                    "skills:\n  - self-improve-loop\n" + anchor,
                    1,
                ),
                encoding="utf-8",
            )

        for label, mutate in (
            ("missing required preload", drop_required_preload),
            ("unexpected preload", add_unapproved_preload),
        ):
            with self.subTest(label=label):
                issues = self._issues_after(mutate)
                self.assertTrue(
                    any("self-improve-loop preload roster drifted" in issue for issue in issues),
                    issues,
                )

    def test_codex_interface_contract_cannot_silently_disappear(self) -> None:
        # Codex accepts the nested plugin only when its presentation contract is complete. A
        # malformed marketplace card otherwise fails at install time outside this repo's CI.
        def mutate(repo: Path) -> None:
            path = (
                repo
                / "plugins"
                / "sde-agents"
                / ".codex-plugin"
                / "plugin.json"
            )
            manifest = json.loads(path.read_text(encoding="utf-8"))
            del manifest["interface"]
            path.write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate, check_adapters=True)
        self.assertTrue(
            any(
                "Codex manifest interface" in issue
                and "required presentation fields" in issue
                for issue in issues
            ),
            issues,
        )

    def test_codex_marketplace_policy_cannot_silently_disappear(self) -> None:
        # The repo-local marketplace is the Codex install entry point, not decorative metadata.
        # Its required policy and category must fail here instead of during a user's installation.
        def mutate(repo: Path) -> None:
            path = repo / ".agents" / "plugins" / "marketplace.json"
            marketplace = json.loads(path.read_text(encoding="utf-8"))
            del marketplace["plugins"][0]["policy"]
            path.write_text(
                json.dumps(marketplace, indent=2) + "\n",
                encoding="utf-8",
            )

        issues = self._issues_after(mutate, check_adapters=True)
        self.assertTrue(
            any(
                "Codex marketplace entry requires installation policy" in issue
                for issue in issues
            ),
            issues,
        )

    def test_evidence_agent_cannot_silently_lose_its_mcp_authority(self) -> None:
        # Both evidence agents used to promise Context7/GitHits while their tools allowlist removed
        # every MCP tool. Mutation is the right test because the invariant binds a real role's
        # method to its real frontmatter rather than defining a synthetic "researcher" fixture.
        def mutate(repo: Path) -> None:
            path = repo / "agents" / "researcher.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "  - mcp__plugin_githits_githits__pkg_info\n", ""
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "evidence role 'researcher' is missing required tools" in issue
                and "pkg_info" in issue
                for issue in issues
            ),
            issues,
        )

    def test_investigation_roles_cannot_collapse_the_local_external_boundary(self) -> None:
        mutations = (
            ("researcher", "  - Read\n"),
            ("repository-investigator", "  - WebFetch\n"),
            ("application-security-auditor", "  - WebSearch\n"),
        )
        for name, tool_line in mutations:
            with self.subTest(agent=name):

                def mutate(repo: Path) -> None:
                    path = repo / "agents" / f"{name}.md"
                    text = path.read_text(encoding="utf-8")
                    path.write_text(
                        text.replace("tools:\n", "tools:\n" + tool_line, 1),
                        encoding="utf-8",
                    )

                issues = self._issues_after(mutate)
                self.assertTrue(
                    any(
                        f"trust-separated role '{name}' holds forbidden tools" in issue
                        for issue in issues
                    ),
                    issues,
                )

    def test_host_manifest_schema_failure_reaches_the_ordinary_fleet_gate(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "evals" / "conformance" / "hosts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["description"] = ""
            path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

        issues = self._issues_after(mutate)
        self.assertTrue(
            any("conformance description must be non-empty" in issue for issue in issues),
            issues,
        )

    def test_host_fleet_policy_keeps_static_hosts_and_required_sol_baseline(self) -> None:
        with repo_copy() as repo:
            path = repo / "evals" / "conformance" / "hosts.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            document["lanes"] = [
                lane for lane in document["lanes"] if lane.get("id") != "vscode-static"
            ]
            sol_lane = next(
                lane
                for lane in document["lanes"]
                if lane.get("kind") == "model-baseline"
                and lane.get("model") == "gpt-5.6-sol"
            )
            sol_lane["required"] = False
            decoy = next(lane for lane in document["lanes"] if lane.get("kind") == "static")
            decoy["model"] = "gpt-5.6-sol"
            document["lanes"].remove(decoy)
            document["lanes"].insert(0, decoy)
            path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
            issues = validate_fleet.validate_host_conformance_manifest(repo)

        self.assertTrue(any("missing hosts ['vscode']" in issue for issue in issues), issues)
        self.assertTrue(any("baseline is not required" in issue for issue in issues), issues)

    def test_runtime_control_consumers_cannot_silently_lose_their_wiring(self) -> None:
        wiring = (
            ("agents/verification-engineer.md", "scripts/verification_sandbox.py"),
            ("skills/sre-tool/SKILL.md", "scripts/run_state.py"),
            # effect_broker.py was retired 2026-09-01 (no consumer named it); the
            # typed-evidence tripwire below now exercises run_state.py instead.
        )
        for consumer_relative, script_relative in wiring:
            with self.subTest(consumer=consumer_relative):

                def mutate(repo: Path) -> None:
                    path = repo / consumer_relative
                    reference = f"${{CLAUDE_PLUGIN_ROOT}}/{script_relative}"
                    path.write_text(
                        path.read_text(encoding="utf-8").replace(reference, script_relative),
                        encoding="utf-8",
                    )

                issues = self._issues_after(mutate)
                self.assertTrue(
                    any(
                        consumer_relative in issue
                        and "silently stop enforcing" in issue
                        for issue in issues
                    ),
                    issues,
                )

    def test_runtime_control_cannot_silently_drop_typed_evidence(self) -> None:
        def mutate(repo: Path) -> None:
            path = repo / "scripts" / "run_state.py"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "evidence_envelope", "untyped_result"
                ),
                encoding="utf-8",
            )

        issues = self._issues_after(mutate)
        self.assertTrue(
            any(
                "scripts/run_state.py" in issue
                and "typed evidence contract" in issue
                for issue in issues
            ),
            issues,
        )


if __name__ == "__main__":
    unittest.main()
