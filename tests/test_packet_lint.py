"""Tests for the packet linter.

The load-bearing property is the INVERSION described in scripts/packet_lint.py: honest labeled
uncertainty must PASS, and confident silence about verification must FAIL. A linter that got this
backwards would punish exactly the behavior the fleet's evidence convention exists to produce, so
each direction is pinned here.
"""
from __future__ import annotations

import unittest

from scripts import learning_ledger
from scripts import packet_lint
from tests.support import REPO

COMPLIANT_REVIEW_PACKET = """
## Review packet

**Changed**: added a retry wrapper at `src/client.py:40` and its tests.
**Assumptions**: the upstream honors `Retry-After` [unverified] — no fixture covers it.
**Verified**: `pytest -q` → `41 passed`.

```
$ pytest -q
41 passed in 2.10s
```

**Not verified**: behavior against the real upstream; no credentials in this environment.
"""

LEARNING_PACKET_BASE = (
    "Changed: scripts/packet_lint.py:1\n"
    "Verified: `python -m unittest tests.test_packet_lint -v` -> 1 passed\n"
    "Check first: learning lifecycle boundary\n"
    "Learning: candidate — untriaged-only linting -> mode-aware lifecycle linting\n"
    "Evidence: review finding at revision worktree in Windows\n"
    "Scope: learning packet linting; excludes ledger transitions\n"
    "Provenance: verified — current source inspection on 2026-08-01\n"
)
INTAKE_LEARNING_PACKET = (
    LEARNING_PACKET_BASE
    + "Learning disposition: add (proposed recommendation)\n"
    + "Promotion state: quarantined\n"
    + "Destination: scripts/packet_lint.py\n"
    + "Owner: fleet-maintainer\n"
)
LIFECYCLE_OWNER_LEARNING_PACKET = (
    LEARNING_PACKET_BASE
    + "Learning disposition: add\n"
    + "Promotion state: proposed\n"
    + "Destination: scripts/packet_lint.py\n"
    + "Owner: fleet-maintainer\n"
)


def lifecycle_owner_packet(disposition: str, promotion_state: str) -> str:
    return (
        LEARNING_PACKET_BASE
        + f"Learning disposition: {disposition}\n"
        + f"Promotion state: {promotion_state}\n"
        + "Destination: scripts/packet_lint.py\n"
        + "Owner: fleet-maintainer\n"
    )


def lifecycle_owner_learning_block(disposition: str, promotion_state: str) -> str:
    return (
        "Learning: candidate — untriaged-only linting -> mode-aware lifecycle linting\n"
        "Evidence: review finding at revision worktree in Windows\n"
        "Scope: learning packet linting; excludes ledger transitions\n"
        "Provenance: verified — current source inspection on 2026-08-01\n"
        f"Learning disposition: {disposition}\n"
        f"Promotion state: {promotion_state}\n"
        "Destination: scripts/packet_lint.py\n"
        "Owner: fleet-maintainer\n"
    )


class LearningCloseoutPublicAPI(unittest.TestCase):
    def test_canonical_none_passes_directly_in_both_modes(self) -> None:
        for mode in packet_lint.LEARNING_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(
                    [],
                    packet_lint.lint_learning_closeout(
                        "Learning: none — no reusable signal\n", mode
                    ),
                )

    def test_shorthand_none_fails_directly_in_both_modes(self) -> None:
        for mode in packet_lint.LEARNING_MODES:
            with self.subTest(mode=mode):
                findings = packet_lint.lint_learning_closeout("Learning:none\n", mode)
                self.assertTrue(
                    any("none — no reusable signal" in item for item in findings), findings
                )

    def test_candidate_compatibility_is_enforced_without_a_packet_shape(self) -> None:
        self.assertEqual(
            [],
            packet_lint.lint_learning_closeout(
                lifecycle_owner_learning_block("add", "proposed"),
                "lifecycle-owner",
            ),
        )
        findings = packet_lint.lint_learning_closeout(
            lifecycle_owner_learning_block("add", "inconclusive"),
            "lifecycle-owner",
        )
        self.assertTrue(any("not valid for Promotion state" in item for item in findings), findings)

    def test_candidate_rejects_the_shipped_retro_template_order(self) -> None:
        # REGRESSION (review-reported): the retro template put a top-level Scope before Learning,
        # while the linter collected labels globally. That unrelated Scope therefore satisfied the
        # candidate field and let a non-contiguous, wrong-order handoff pass.
        packet = (
            "Scope: task retro and supplied evidence\n"
            "Signals: one review correction\n"
            "Candidates: packet fields need structural validation\n"
            "Learning: candidate — global field search -> one canonical block\n"
            "Evidence: review finding at revision worktree in Windows\n"
            "Provenance: verified — current source inspection on 2026-08-01\n"
            "Learning disposition: add\n"
            "Promotion state: proposed\n"
            "Destination: scripts/packet_lint.py\n"
            "Owner: fleet-maintainer\n"
        )
        findings = packet_lint.lint_learning_closeout(packet, "lifecycle-owner")
        self.assertTrue(any("contiguous block" in item for item in findings), findings)

    def test_candidate_rejects_scattered_global_fields(self) -> None:
        packet = (
            "Evidence: review finding at revision worktree in Windows\n"
            "Scope: learning packet linting; excludes ledger transitions\n"
            "Owner: fleet-maintainer\n"
            "Narrative: the fields above describe the whole report, not this candidate.\n"
            "Learning: candidate — global field search -> one canonical block\n"
            "Provenance: verified — current source inspection on 2026-08-01\n"
            "Learning disposition: add\n"
            "Promotion state: proposed\n"
            "Destination: scripts/packet_lint.py\n"
        )
        findings = packet_lint.lint_learning_closeout(packet, "lifecycle-owner")
        self.assertTrue(any("contiguous block" in item for item in findings), findings)

    def test_candidate_rejects_unresolved_template_metavariables_in_every_value(self) -> None:
        packet = (
            "Learning: candidate — <observed -> expected divergence>\n"
            "Evidence: <occurrences and exact revision/version/environment>\n"
            "Scope: <applicability and exclusions>\n"
            "Provenance: <verified/sourced/unverified and source>\n"
            "Learning disposition: <skip/add/merge/supersede/drop>\n"
            "Promotion state: <proposed/approved/promoted/rejected/inconclusive/retired>\n"
            "Destination: <exact artifact>\n"
            "Owner: <authorized owner>\n"
        )
        findings = packet_lint.lint_learning_closeout(packet, "lifecycle-owner")
        for label in packet_lint.LEARNING_CANDIDATE_FIELD_ORDER:
            with self.subTest(label=label):
                self.assertTrue(
                    any(label.title() in item and "metavariable" in item for item in findings),
                    findings,
                )

    def test_candidate_rejects_plain_template_sentinels_in_every_value(self) -> None:
        valid = lifecycle_owner_learning_block("add", "proposed")
        replacements = {
            "learning": (
                "Learning: candidate — untriaged-only linting -> mode-aware lifecycle linting",
                "Learning: candidate — TBD -> mode-aware lifecycle linting",
            ),
            "evidence": (
                "Evidence: review finding at revision worktree in Windows",
                "Evidence: TBD",
            ),
            "scope": (
                "Scope: learning packet linting; excludes ledger transitions",
                "Scope: TODO",
            ),
            "provenance": (
                "Provenance: verified — current source inspection on 2026-08-01",
                "Provenance: verified — TBA",
            ),
            "learning disposition": (
                "Learning disposition: add",
                "Learning disposition: FIXME",
            ),
            "promotion state": (
                "Promotion state: proposed",
                "Promotion state: PLACEHOLDER",
            ),
            "destination": (
                "Destination: scripts/packet_lint.py",
                "Destination: TBD",
            ),
            "owner": (
                "Owner: fleet-maintainer",
                "Owner: TODO",
            ),
        }
        for label, (old, new) in replacements.items():
            with self.subTest(label=label):
                findings = packet_lint.lint_learning_closeout(
                    valid.replace(old, new), "lifecycle-owner"
                )
                self.assertTrue(
                    any(
                        label.title() in item and "plain metavariable" in item
                        for item in findings
                    ),
                    findings,
                )

    def test_candidate_learning_rejects_plain_sentinel_on_either_side_of_arrow(self) -> None:
        valid = lifecycle_owner_learning_block("add", "proposed")
        learning = "Learning: candidate — untriaged-only linting -> mode-aware lifecycle linting"
        for replacement in (
            "Learning: candidate — TBD -> mode-aware lifecycle linting",
            "Learning: candidate — untriaged-only linting -> TBD",
        ):
            with self.subTest(replacement=replacement):
                findings = packet_lint.lint_learning_closeout(
                    valid.replace(learning, replacement), "lifecycle-owner"
                )
                self.assertTrue(
                    any(
                        "Learning candidate Learning:" in item
                        and "plain metavariable" in item
                        for item in findings
                    ),
                    findings,
                )

    def test_candidate_rejects_whole_value_semantic_sentinels(self) -> None:
        valid = lifecycle_owner_learning_block("add", "proposed")
        replacements = (
            (
                "Evidence: review finding at revision worktree in Windows",
                "Evidence: unknown",
            ),
            (
                "Scope: learning packet linting; excludes ledger transitions",
                "Scope: pending",
            ),
            (
                "Provenance: verified — current source inspection on 2026-08-01",
                "Provenance: unverified -> none",
            ),
            ("Destination: scripts/packet_lint.py", "Destination: n/a"),
            ("Owner: fleet-maintainer", "Owner: unassigned"),
        )
        for old, new in replacements:
            with self.subTest(new=new):
                findings = packet_lint.lint_learning_closeout(
                    valid.replace(old, new), "lifecycle-owner"
                )
                self.assertTrue(any("semantic placeholder" in item for item in findings), findings)

    def test_candidate_rejects_every_semantic_sentinel_on_either_arrow_side(self) -> None:
        valid = lifecycle_owner_learning_block("add", "proposed")
        original = (
            "Learning: candidate — untriaged-only linting -> mode-aware lifecycle linting"
        )
        for sentinel in ("unknown", "pending", "none", "n/a", "unassigned"):
            for replacement in (
                f"Learning: candidate — {sentinel} -> mode-aware lifecycle linting",
                f"Learning: candidate — untriaged-only linting -> {sentinel}",
            ):
                with self.subTest(replacement=replacement):
                    findings = packet_lint.lint_learning_closeout(
                        valid.replace(original, replacement), "lifecycle-owner"
                    )
                    self.assertTrue(
                        any("semantic placeholder" in item for item in findings), findings
                    )

    def test_semantic_sentinel_words_inside_substantive_values_remain_valid(self) -> None:
        text = lifecycle_owner_learning_block("add", "proposed")
        text = text.replace(
            "Evidence: review finding at revision worktree in Windows",
            "Evidence: pending jobs reproduce the unknown-state race",
        ).replace(
            "Scope: learning packet linting; excludes ledger transitions",
            "Scope: unknown-version handling only; excludes normal startup",
        ).replace(
            "Provenance: verified — current source inspection on 2026-08-01",
            "Provenance: verified — pending jobs inspected on 2026-08-01",
        ).replace(
            "Destination: scripts/packet_lint.py",
            "Destination: learning/unknown-candidates.md",
        ).replace(
            "Owner: fleet-maintainer",
            "Owner: unassigned-reviewer",
        )
        self.assertEqual(
            [], packet_lint.lint_learning_closeout(text, "lifecycle-owner")
        )

    def test_candidate_rejects_punctuation_only_fields_and_arrow_sides(self) -> None:
        valid = lifecycle_owner_learning_block("add", "proposed")
        replacements = (
            (
                "Evidence: review finding at revision worktree in Windows",
                "Evidence:?",
            ),
            (
                "Scope: learning packet linting; excludes ledger transitions",
                "Scope:.",
            ),
            (
                "Provenance: verified — current source inspection on 2026-08-01",
                "Provenance: unverified -> -",
            ),
            (
                "Learning: candidate — untriaged-only linting -> mode-aware lifecycle linting",
                "Learning: candidate — ? -> mode-aware lifecycle linting",
            ),
            (
                "Learning: candidate — untriaged-only linting -> mode-aware lifecycle linting",
                "Learning: candidate — untriaged-only linting -> .",
            ),
        )
        for old, new in replacements:
            with self.subTest(new=new):
                findings = packet_lint.lint_learning_closeout(
                    valid.replace(old, new), "lifecycle-owner"
                )
                self.assertTrue(any("semantic placeholder" in item for item in findings), findings)

    def test_candidate_provenance_requires_details_after_the_enum(self) -> None:
        valid = lifecycle_owner_learning_block("add", "proposed")
        detailed = "Provenance: verified — current source inspection on 2026-08-01"
        for bare in packet_lint.LEARNING_PROVENANCE:
            with self.subTest(bare=bare):
                findings = packet_lint.lint_learning_closeout(
                    valid.replace(detailed, f"Provenance: {bare}"), "lifecycle-owner"
                )
                self.assertTrue(
                    any("source or freshness details" in item for item in findings), findings
                )

    def test_candidate_rejects_duplicate_or_conflicting_fields(self) -> None:
        duplicate = lifecycle_owner_learning_block("add", "proposed") + (
            "Evidence: a conflicting report-level evidence field\n"
        )
        findings = packet_lint.lint_learning_closeout(duplicate, "lifecycle-owner")
        self.assertTrue(
            any("exactly one non-empty Evidence:" in item for item in findings), findings
        )

        conflicting = lifecycle_owner_learning_block("add", "proposed").replace(
            "Owner: fleet-maintainer\n",
            "Owner: fleet-maintainer\nOwner: prompt-maintainer\n",
        )
        findings = packet_lint.lint_learning_closeout(conflicting, "lifecycle-owner")
        self.assertTrue(
            any("exactly one non-empty Owner:" in item for item in findings), findings
        )

    def test_markdown_decorated_contiguous_candidate_passes(self) -> None:
        packets = (
            (
                "> **Learning**: candidate — global field search -> one canonical block\n"
                "> **Evidence**: review finding at revision worktree in Windows\n"
                "> **Scope**: learning packet linting; excludes ledger transitions\n"
                "> **Provenance**: verified — current source inspection on 2026-08-01\n"
                "> **Learning disposition**: add\n"
                "> **Promotion state**: proposed\n"
                "> **Destination**: scripts/packet_lint.py\n"
                "> **Owner**: fleet-maintainer\n"
            ),
            (
                "- **Learning:** candidate — global field search -> one canonical block\n"
                "- **Evidence:** review finding at revision worktree in Windows\n"
                "- **Scope:** learning packet linting; excludes ledger transitions\n"
                "- **Provenance:** verified — current source inspection on 2026-08-01\n"
                "- **Learning disposition:** add\n"
                "- **Promotion state:** proposed\n"
                "- **Destination:** scripts/packet_lint.py\n"
                "- **Owner:** fleet-maintainer\n"
            ),
            # The emphasis span opens before the label and closes inside the value. A live
            # planning-only session emitted the whole canonical block this way and the reader saw
            # no Learning field at all (LEARN-002 batch 1, self-improve-promotion-gate).
            (
                "**Learning: candidate — global field search -> one canonical block**\n"
                "**Evidence: review finding at revision worktree in Windows**\n"
                "**Scope: learning packet linting; excludes ledger transitions**\n"
                "**Provenance: verified — current source inspection on 2026-08-01**\n"
                "**Learning disposition: add**\n"
                "**Promotion state: proposed**\n"
                "**Destination: scripts/packet_lint.py**\n"
                "**Owner: fleet-maintainer**\n"
            ),
        )
        for packet in packets:
            with self.subTest(packet=packet):
                self.assertEqual(
                    [], packet_lint.lint_learning_closeout(packet, "lifecycle-owner")
                )

    def test_decorated_span_reads_the_value_without_laundering_it(self) -> None:
        """The span placement must recover the value, never excuse a bad one."""
        no_divergence = (
            "**Learning: candidate — generated adapters must carry a parity assertion**\n"
        )
        self.assertTrue(
            any(
                "must be `none` or `candidate" in finding
                for finding in packet_lint.lint_learning_closeout(
                    no_divergence, "lifecycle-owner"
                )
            ),
            packet_lint.lint_learning_closeout(no_divergence, "lifecycle-owner"),
        )

        # A different label that merely starts with the field name stays excluded.
        curve = "**Learning curve: candidate — steep -> shallow**\n"
        self.assertEqual(
            ["missing literal Learning: closeout; a prefix or dash is not the packet contract"],
            packet_lint.lint_learning_closeout(curve, "lifecycle-owner"),
        )

        # Exact-field grading still compares the literal value, not the decorated line.
        self.assertEqual(
            [],
            packet_lint.lint_exact_fields(
                "**Owner: fleet-maintainer**\n", {"Owner": "fleet-maintainer"}
            ),
        )
        self.assertTrue(
            packet_lint.lint_exact_fields(
                "**Owner: fleet-maintainer** and the release coordinator\n",
                {"Owner": "fleet-maintainer"},
            )
        )

    def test_unterminated_span_keeps_later_markdown_in_value(self) -> None:
        occurrences = packet_lint.literal_field_occurrences(
            "**Owner: fleet-maintainer and **release** coordinator\n",
            "Owner",
        )
        self.assertEqual([(0, "fleet-maintainer and **release** coordinator")], occurrences)

    def test_display_echoes_collapse_but_conflicts_still_count(self) -> None:
        """A repeated value is display; a different value is a conflict and must still fail."""
        # A bare section header above the block (learning-slot-operational-agent).
        headered = "**Learning**:\n" + lifecycle_owner_learning_block("add", "proposed")
        self.assertEqual(
            [], packet_lint.lint_learning_closeout(headered, "lifecycle-owner")
        )

        # A summary line echoing the same decision the block repeats verbatim
        # (learning-runbook-namespaces-compose).
        echoed = (
            "**Learning disposition: merge**\n"
            "**Runbook disposition: update**\n\n"
            "Learning disposition: merge\n"
            "Runbook disposition: update\n"
        )
        self.assertEqual(
            [],
            packet_lint.lint_exact_fields(
                echoed,
                {"Learning disposition": "merge", "Runbook disposition": "update"},
            ),
        )

        # The same field written twice inside the block, same rendering, is still two fields:
        # only a differently-decorated echo is a rendering of another line.
        repeated = "Learning disposition: merge\nLearning disposition: merge\n"
        self.assertTrue(
            packet_lint.lint_exact_fields(repeated, {"Learning disposition": "merge"})
        )

        # Two different values remain two fields, in both the exact-field and closeout paths.
        conflicting = "Learning disposition: merge\nLearning disposition: add\n"
        self.assertTrue(
            packet_lint.lint_exact_fields(conflicting, {"Learning disposition": "merge"})
        )
        two_learnings = (
            "Learning: none — no reusable signal\n"
            + lifecycle_owner_learning_block("add", "proposed")
        )
        self.assertEqual(
            ["Learning: must appear exactly once with a non-empty value"],
            packet_lint.lint_learning_closeout(two_learnings, "lifecycle-owner"),
        )

        # An empty field with no valued twin still reports its own emptiness.
        self.assertEqual(
            ["Learning: closeout has no disposition value"],
            packet_lint.lint_learning_closeout("Learning:\n", "lifecycle-owner"),
        )

    def test_closed_vocabulary_fields_tolerate_a_final_full_stop(self) -> None:
        """`Promotion state: quarantined.` is the same value; `quarantined and approved` is not."""
        intake = (
            "Learning: candidate — drills stall -> the runbook states a stop condition\n"
            "Evidence: two authorized restore drills\n"
            "Scope: ops/widgets.md restore section; excludes other runbooks\n"
            "Provenance: unverified — caller summary only, 2026-08-10\n"
            "Learning disposition: add (proposed recommendation).\n"
            "Promotion state: quarantined.\n"
            "Destination: ops/widgets.md\n"
            "Owner: runbook owner for ops/widgets.md\n"
        )
        self.assertEqual([], packet_lint.lint_learning_closeout(intake, "intake"))

        widened = intake.replace(
            "Promotion state: quarantined.", "Promotion state: quarantined and approved"
        )
        self.assertTrue(
            any(
                "Promotion state: quarantined" in finding
                for finding in packet_lint.lint_learning_closeout(widened, "intake")
            ),
            packet_lint.lint_learning_closeout(widened, "intake"),
        )
        negated = intake.replace(
            "Promotion state: quarantined.", "Promotion state: not quarantined"
        )
        self.assertTrue(packet_lint.lint_learning_closeout(negated, "intake"))

    def test_unknown_mode_fails_directly(self) -> None:
        with self.assertRaises(KeyError):
            packet_lint.lint_learning_closeout(
                "Learning: none — no reusable signal\n", "untriaged-owner"
            )


class RequiredSlots(unittest.TestCase):
    def test_a_compliant_packet_has_no_findings(self) -> None:
        self.assertEqual([], packet_lint.lint_packet(COMPLIANT_REVIEW_PACKET, "review-packet"))

    def test_missing_slot_is_reported(self) -> None:
        text = COMPLIANT_REVIEW_PACKET.replace("**Not verified**", "**Leftovers**")
        findings = packet_lint.lint_packet(text, "review-packet")
        self.assertTrue(any("not verified" in f for f in findings), findings)

    def test_slot_matching_ignores_markdown_and_case(self) -> None:
        text = "### CHANGED\nstuff\n### Assumptions\nnone\n### Verified\n`pytest -q` → 3 passed\n### NOT VERIFIED\nnothing"
        self.assertEqual([], packet_lint.lint_packet(text, "review-packet"))

    def test_unknown_shape_raises(self) -> None:
        with self.assertRaises(KeyError):
            packet_lint.lint_packet("anything", "no-such-shape")

    def test_a_slot_is_not_satisfied_by_being_a_substring_of_another_slot(self) -> None:
        # REGRESSION (review-reported, reproduced): the slot check searched one concatenated body,
        # so "**Not verified**: ..." contained "verified" and satisfied the `verified` slot. A
        # packet that never says what it DID verify then passed the contract it was meant to prove.
        text = """
        **Changed**: the retry wrapper.
        **Assumptions**: none.
        **Not verified**: everything — I could not run the suite.
        """
        findings = packet_lint.lint_packet(text, "review-packet")
        self.assertTrue(
            any("'verified'" in f and "missing" in f for f in findings),
            f"the 'verified' slot must not be satisfied by 'not verified': {findings}",
        )

    def test_prose_without_headings_is_not_a_packet(self) -> None:
        # REGRESSION (review-reported): free prose containing the slot WORDS satisfied every slot,
        # so the behavioral eval could report contract compliance for output in which a caller
        # cannot locate a single promised section.
        prose = (
            "I changed it after discussing assumptions. The work is verified by CI: 1 passed. "
            "It is not verified in production."
        )
        findings = packet_lint.lint_packet(prose, "review-packet")
        self.assertTrue(
            sum("missing required packet slot" in f for f in findings) >= 3,
            f"prose with no headings must fail most slots: {findings}",
        )

    def test_sde_fullstack_shape_requires_only_that_agent_s_guaranteed_slots(self) -> None:
        # The agent's packet SCALES: a small change legitimately ships Changed / Verified /
        # Check first / Learning and stops. A shape demanding the conditional slots would fail a
        # compliant agent, so the required set is pinned to the declared minimum — and to the agent
        # file, so a future edit to either surfaces here rather than as a mystery eval failure.
        packet_section = (REPO / "agents" / "sde-fullstack.md").read_text()
        for slot in packet_lint.SHAPES["sde-fullstack-packet"]:
            self.assertIn(slot, packet_section.lower(), f"{slot!r} is no longer a declared slot")
        compressed = (
            "**Changed**: duration.py:1-20, test_duration.py:1-30\n"
            "**Verified**: `pytest -q` -> 6 passed\n"
            "**Check first**: the 2h boundary case\n"
            "**Learning**: none — no reusable signal\n"
        )
        self.assertEqual([], packet_lint.lint_packet(compressed, "sde-fullstack-packet"))

    def test_learning_closeout_rejects_blank_whitespace_and_misleading_prefixes(self) -> None:
        base = (
            "**Changed**: duration.py:1\n"
            "**Verified**: `pytest -q` -> 1 passed\n"
            "**Check first**: boundary\n"
        )
        for closeout in ("Learning:\n", "Learning:   \n", "Learning curve: none\n", "Learning - none\n"):
            with self.subTest(closeout=closeout):
                findings = packet_lint.lint_packet(base + closeout, "sde-fullstack-packet")
                self.assertTrue(any("Learning" in finding for finding in findings), findings)

    def test_learning_closeout_rejects_unknown_status_and_incomplete_candidate(self) -> None:
        base = (
            "Changed: duration.py:1\n"
            "Verified: `pytest -q` -> 1 passed\n"
            "Check first: boundary\n"
        )
        malformed = packet_lint.lint_packet(
            base + "Learning: maybe later\n", "sde-fullstack-packet"
        )
        self.assertTrue(any("must be `none` or `candidate" in finding for finding in malformed))

        incomplete = packet_lint.lint_packet(
            base + "Learning: candidate — observed -> expected\nEvidence: issue-1\n",
            "sde-fullstack-packet",
        )
        self.assertTrue(any("Scope:" in finding for finding in incomplete), incomplete)
        self.assertTrue(any("Owner:" in finding for finding in incomplete), incomplete)

    def test_canonical_learning_none_passes_in_both_modes(self) -> None:
        packet = (
            "Changed: duration.py:1\n"
            "Verified: `pytest -q` -> 1 passed\n"
            "Check first: boundary\n"
            "Learning: none — no reusable signal\n"
        )
        for mode in packet_lint.LEARNING_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(
                    [],
                    packet_lint.lint_packet(
                        packet, "sde-fullstack-packet", learning_mode=mode
                    ),
                )

    def test_noncanonical_learning_none_fails_in_both_modes(self) -> None:
        base = (
            "Changed: duration.py:1\n"
            "Verified: `pytest -q` -> 1 passed\n"
            "Check first: boundary\n"
        )
        for mode in packet_lint.LEARNING_MODES:
            for closeout in (
                "Learning:none\n",
                "Learning: none\n",
                "Learning: none.\n",
                "Learning: none - no reusable signal\n",
                "Learning: none — no reusable signal.\n",
            ):
                with self.subTest(mode=mode, closeout=closeout):
                    findings = packet_lint.lint_packet(
                        base + closeout,
                        "sde-fullstack-packet",
                        learning_mode=mode,
                    )
                    self.assertTrue(
                        any("none — no reusable signal" in finding for finding in findings),
                        findings,
                    )

    def test_intake_candidate_passes_only_intake_mode(self) -> None:
        self.assertEqual(
            [],
            packet_lint.lint_packet(
                INTAKE_LEARNING_PACKET,
                "sde-fullstack-packet",
                learning_mode="intake",
            ),
        )
        findings = packet_lint.lint_packet(
            INTAKE_LEARNING_PACKET,
            "sde-fullstack-packet",
            learning_mode="lifecycle-owner",
        )
        self.assertTrue(any("lifecycle-owner" in finding for finding in findings), findings)

    def test_lifecycle_owner_candidate_passes_only_lifecycle_owner_mode(self) -> None:
        self.assertEqual(
            [],
            packet_lint.lint_packet(
                LIFECYCLE_OWNER_LEARNING_PACKET,
                "sde-fullstack-packet",
                learning_mode="lifecycle-owner",
            ),
        )

        findings = packet_lint.lint_packet(
            LIFECYCLE_OWNER_LEARNING_PACKET,
            "sde-fullstack-packet",
            learning_mode="intake",
        )
        self.assertTrue(any("intake" in finding for finding in findings), findings)

    def test_lifecycle_matrix_mirrors_ledger_owner(self) -> None:
        # scripts/learning_ledger.py owns the executable persistence contract. The packet linter is
        # a standalone eval tool, so it mirrors the map; equality here turns drift into a loud test
        # failure instead of letting a transcript pass a pair the ledger later refuses to store.
        expected = {
            state: frozenset(dispositions)
            for state, dispositions in learning_ledger.STATE_DISPOSITIONS.items()
        }
        self.assertEqual(expected, packet_lint.LEARNING_STATE_DISPOSITIONS)
        self.assertEqual(
            set(learning_ledger.DISPOSITIONS), set(packet_lint.LEARNING_DISPOSITIONS)
        )

    def test_every_ledger_compatible_lifecycle_pair_passes(self) -> None:
        for state, allowed in sorted(learning_ledger.STATE_DISPOSITIONS.items()):
            for disposition in sorted(allowed):
                with self.subTest(state=state, disposition=disposition):
                    packet = lifecycle_owner_packet(disposition, state)
                    self.assertEqual(
                        [],
                        packet_lint.lint_packet(
                            packet,
                            "sde-fullstack-packet",
                            learning_mode="lifecycle-owner",
                        ),
                    )

    def test_every_ledger_incompatible_lifecycle_pair_fails(self) -> None:
        for state, allowed in sorted(learning_ledger.STATE_DISPOSITIONS.items()):
            for disposition in sorted(learning_ledger.DISPOSITIONS - allowed):
                with self.subTest(state=state, disposition=disposition):
                    packet = lifecycle_owner_packet(disposition, state)
                    findings = packet_lint.lint_packet(
                        packet,
                        "sde-fullstack-packet",
                        learning_mode="lifecycle-owner",
                    )
                    self.assertTrue(
                        any("not valid for Promotion state" in finding for finding in findings),
                        findings,
                    )

    def test_modes_reject_each_wrong_boundary_field_independently(self) -> None:
        cases = (
            (
                "intake accepted disposition",
                INTAKE_LEARNING_PACKET.replace(" (proposed recommendation)", ""),
                "intake",
                "Learning disposition",
            ),
            (
                "intake post-triage state",
                INTAKE_LEARNING_PACKET.replace("quarantined", "proposed"),
                "intake",
                "Promotion state",
            ),
            (
                "owner proposed recommendation",
                LIFECYCLE_OWNER_LEARNING_PACKET.replace(
                    "Learning disposition: add",
                    "Learning disposition: add (proposed recommendation)",
                ),
                "lifecycle-owner",
                "Learning disposition",
            ),
            (
                "owner quarantined state",
                LIFECYCLE_OWNER_LEARNING_PACKET.replace("proposed", "quarantined"),
                "lifecycle-owner",
                "Promotion state",
            ),
        )
        for label, packet, mode, expected in cases:
            with self.subTest(label=label):
                findings = packet_lint.lint_packet(
                    packet, "sde-fullstack-packet", learning_mode=mode
                )
                self.assertTrue(any(expected in finding for finding in findings), findings)

    def test_sde_fullstack_shape_defaults_to_lifecycle_owner_mode(self) -> None:
        self.assertEqual(
            [],
            packet_lint.lint_packet(
                LIFECYCLE_OWNER_LEARNING_PACKET, "sde-fullstack-packet"
            ),
        )

    def test_unknown_learning_mode_raises(self) -> None:
        with self.assertRaises(KeyError):
            packet_lint.lint_packet(
                LIFECYCLE_OWNER_LEARNING_PACKET,
                "sde-fullstack-packet",
                learning_mode="untriaged-owner",
            )

    def test_learning_none_cannot_hide_candidate_fields(self) -> None:
        packet = (
            "Changed: x.py:1\nVerified: `pytest -q` -> 1 passed\nCheck first: x.py:1\n"
            "Learning: none — no reusable signal\nOwner: fleet-maintainer\n"
        )
        findings = packet_lint.lint_packet(packet, "sde-fullstack-packet")
        self.assertTrue(any("contradicts candidate fields" in finding for finding in findings), findings)

    def test_postmortem_shape_matches_the_shipped_template(self) -> None:
        # The shape's slots are the headings the asset actually emits; drift between them would
        # make the linter reject a compliant postmortem.
        template = (REPO / "skills" / "postmortem" / "assets" / "postmortem.md").read_text()
        self.assertEqual([], packet_lint.lint_packet(template, "postmortem"))


class TheInversion(unittest.TestCase):
    """Labeled uncertainty passes; unbacked confidence fails. This is the whole design."""

    def test_labeled_uncertainty_passes(self) -> None:
        text = COMPLIANT_REVIEW_PACKET.replace(
            "**Not verified**: behavior against the real upstream; no credentials in this environment.",
            "**Not verified**: [unverified] this should work against the real upstream, but I could not check.",
        )
        findings = packet_lint.lint_packet(text, "review-packet")
        self.assertEqual([], findings, "an honestly labeled hedge must not be a finding")

    def test_unlabeled_hedge_is_a_finding(self) -> None:
        text = COMPLIANT_REVIEW_PACKET.replace(
            "**Not verified**: behavior against the real upstream; no credentials in this environment.",
            "**Not verified**: this should work against the real upstream.",
        )
        findings = packet_lint.lint_packet(text, "review-packet")
        self.assertTrue(any("no evidence label" in f for f in findings), findings)

    def test_verification_claim_without_evidence_is_a_finding(self) -> None:
        # The claim most worth lying about: asserted, never shown.
        text = """
        **Changed**: the retry wrapper.
        **Assumptions**: none.
        **Verified**: tests pass.
        **Not verified**: nothing.
        """
        findings = packet_lint.lint_packet(text, "review-packet")
        self.assertTrue(any("no command or output cited" in f for f in findings), findings)

    def test_verification_claim_with_evidence_passes(self) -> None:
        self.assertEqual([], packet_lint.lint_packet(COMPLIANT_REVIEW_PACKET, "review-packet"))

    def test_negated_verified_is_a_disclosure_not_an_unevidenced_claim(self) -> None:
        """The honest slots of a nothing-ran packet must not read as unbacked claims.

        Recorded verbatim in the 2026-08-10 first-live verifier benchmark, where all three of
        these lines were reported as verification claims with no command cited.
        """
        text = "\n".join((
            "**Changed**: nothing — no check ran.",
            "**Assumptions**: none load-bearing, and I am not treating them as verified.",
            "**Verified**: nothing, with output to show — there is no output.",
            "**Not verified**: everything — revision identity, existence of the path.",
        ))
        self.assertEqual([], packet_lint.lint_packet(text, "review-packet"))

        # The affirmative claim on the same slot still needs evidence.
        claimed = text.replace(
            "**Verified**: nothing, with output to show — there is no output.",
            "**Verified**: I verified the version constant.",
        )
        self.assertTrue(
            any("no command or output cited" in f
                for f in packet_lint.lint_packet(claimed, "review-packet")),
            packet_lint.lint_packet(claimed, "review-packet"),
        )

        # A negation far from the word does not launder a claim beside it.
        distant = text.replace(
            "**Verified**: nothing, with output to show — there is no output.",
            "**Verified**: this has not been fully reviewed by anyone, but I verified the fix.",
        )
        self.assertTrue(
            any("no command or output cited" in f
                for f in packet_lint.lint_packet(distant, "review-packet")),
            packet_lint.lint_packet(distant, "review-packet"),
        )

    def test_piped_test_run_as_evidence_is_a_finding(self) -> None:
        # The pipeline reports the LAST stage's status, and block buffering can push the runner's
        # summary out of the excerpt -- the claim rides the wrong command's zero.
        text = COMPLIANT_REVIEW_PACKET.replace(
            "$ pytest -q", "$ python3 -m unittest discover -s tests | tail -5"
        )
        findings = packet_lint.lint_packet(text, "review-packet")
        self.assertTrue(any("own exit status" in f for f in findings), findings)

    def test_chained_test_run_as_evidence_is_a_finding(self) -> None:
        # `runner; other` reports `other`'s status over the runner's failure.
        text = COMPLIANT_REVIEW_PACKET.replace("$ pytest -q", "$ pytest -q; git status")
        findings = packet_lint.lint_packet(text, "review-packet")
        self.assertTrue(any("own exit status" in f for f in findings), findings)

    def test_status_echo_after_test_run_stays_legal(self) -> None:
        # A trailing command that reads $?/$LASTEXITCODE is reporting the runner's OWN status;
        # flagging it would punish exactly the provenance the rule exists to demand.
        for suffix in ("; echo $?", '; "exit: $LASTEXITCODE"'):
            with self.subTest(suffix=suffix):
                text = COMPLIANT_REVIEW_PACKET.replace(
                    "$ pytest -q", f"$ python3 scripts/run_tests.py -v{suffix}"
                )
                self.assertEqual([], packet_lint.lint_packet(text, "review-packet"))

    def test_piped_filter_is_not_a_test_run(self) -> None:
        # The runner vocabulary is deliberately narrow: an ordinary filter piped over logs is
        # legal evidence, even near a claim -- only a TEST RUN piped onward launders its status.
        text = COMPLIANT_REVIEW_PACKET.replace(
            "41 passed in 2.10s", "41 passed in 2.10s\n$ grep -c retry client.log | sort"
        )
        self.assertEqual([], packet_lint.lint_packet(text, "review-packet"))

    def test_or_true_fallback_is_a_finding(self) -> None:
        # `runner || true` forces exit 0 over the runner's failure -- the canonical status
        # launder. The first version of this rule exempted it as a side effect of telling the
        # pipe apart from logical-or (review finding); `&&` stays legal because a failing
        # runner short-circuits and its own status survives.
        text = COMPLIANT_REVIEW_PACKET.replace("$ pytest -q", "$ pytest -q || true")
        findings = packet_lint.lint_packet(text, "review-packet")
        self.assertTrue(any("own exit status" in f for f in findings), findings)

    def test_quoted_pipe_in_runner_args_is_not_laundering(self) -> None:
        # `$ pytest -k "retry|backoff"` is a direct run; the pipe is data inside a quoted
        # argument. The unblanked first version false-fired on it (review finding) -- the same
        # punish-the-honest-run direction the prompt anchoring exists to prevent.
        text = COMPLIANT_REVIEW_PACKET.replace("$ pytest -q", '$ pytest -k "retry|backoff"')
        self.assertEqual([], packet_lint.lint_packet(text, "review-packet"))

    def test_go_test_regex_alternation_is_not_laundering(self) -> None:
        # `$ go test ./... -run 'TestFoo|TestBar'` is a direct run; the `|` is inside a single-
        # quoted regex argument, not a shell pipeline. Without quoted-span blanking this false-
        # fires because the pipe character appears on a prompt line after a runner name.
        text = COMPLIANT_REVIEW_PACKET.replace(
            "$ pytest -q", "$ go test ./... -run 'TestFoo|TestBar'"
        )
        self.assertEqual([], packet_lint.lint_packet(text, "review-packet"))

    def test_prose_semicolon_near_a_runner_is_not_laundering(self) -> None:
        # The scan is anchored to shell-prompt lines: a prose sentence or a markdown table
        # that happens to contain a runner name plus `;` or `|` is not a command, and the
        # unanchored first version false-fired on exactly these (review finding), punishing
        # honest direct runs.
        for evidence_line in (
            "**Verified**: `pytest -q` -> 41 passed; `ruff check` clean.",
            "**Verified**: `pytest -q` → `41 passed`.\n| tests | `pytest -q` -> 41 passed | ok |",
        ):
            with self.subTest(evidence_line=evidence_line):
                text = COMPLIANT_REVIEW_PACKET.replace(
                    "**Verified**: `pytest -q` → `41 passed`.", evidence_line
                )
                self.assertEqual([], packet_lint.lint_packet(text, "review-packet"))

    def test_silence_is_not_rewarded(self) -> None:
        # ECC's scorer would give this a perfect score ("assumes correctness"). Here, a packet that
        # simply omits the verification slots fails -- missing evidence is missing, not fine.
        text = "**Changed**: rewrote the client.\n**Assumptions**: none.\n"
        findings = packet_lint.lint_packet(text, "review-packet")
        self.assertTrue(any("verified" in f for f in findings), findings)


class OtherShapes(unittest.TestCase):
    def test_design_packet_shape(self) -> None:
        text = "**Decisions**: chose X.\n**Assumptions**: load is small [unverified].\n**Weakest point**: the cache.\n"
        self.assertEqual([], packet_lint.lint_packet(text, "design-packet"))

    def test_multi_agent_packet_requires_cheapest_test(self) -> None:
        text = "**Decisions**: pipeline.\n**Assumptions**: none.\n**Weakest seam**: the handoff.\n"
        findings = packet_lint.lint_packet(text, "multi-agent-packet")
        self.assertTrue(any("cheapest test" in f for f in findings), findings)

    def test_verification_packet_shape_requires_isolation_slot(self) -> None:
        # The Execution-isolation slot records what actually happened to every executable
        # check; without this shape that record was prose only (review finding). The
        # Skipped-or-blocked-checks slot names which criteria could not run, preventing a
        # "Checks executed: none" packet from passing as green with no criteria named.
        # All directions: a packet naming all four floor slots passes; one omitting
        # isolation is a finding; one omitting skipped-or-blocked is also a finding.
        compliant = (
            "**Target**: repo at abc1234, Python 3.12.\n"
            "**Checks executed**: `pytest -q` → `41 passed` [verified].\n"
            "```\n$ pytest -q\n41 passed in 2.10s\n```\n"
            "**Skipped or blocked checks**: none — all criteria ran.\n"
            "**Execution isolation**: verification_sandbox.py, digest-pinned image, "
            "network none, residue none.\n"
        )
        self.assertEqual([], packet_lint.lint_packet(compliant, "verification-packet"))
        missing_isolation = compliant.replace("**Execution isolation**", "**Isolation notes**")
        findings = packet_lint.lint_packet(missing_isolation, "verification-packet")
        self.assertTrue(any("execution isolation" in f for f in findings), findings)
        missing_blocked = compliant.replace("**Skipped or blocked checks**", "**Nothing skipped**")
        findings = packet_lint.lint_packet(missing_blocked, "verification-packet")
        self.assertTrue(any("skipped or blocked checks" in f for f in findings), findings)

    def test_every_shape_is_reachable_from_the_cli_listing(self) -> None:
        # A shape nobody can name is a shape nobody can assert against.
        self.assertIn("review-packet", packet_lint.SHAPES)
        self.assertTrue(all(slots for slots in packet_lint.SHAPES.values()))


class CanonicalLearningPrompts(unittest.TestCase):
    OWNER_AGENTS = ("prompt-engineer", "sde-fullstack", "verification-engineer")
    MATRIX_FRAGMENTS = (
        "proposed|approved|promoted → add|merge|supersede",
        "inconclusive → skip",
        "rejected → skip|drop",
        "retired → skip|drop|merge|supersede",
    )

    def test_each_lifecycle_owner_is_taught_the_compatibility_matrix(self) -> None:
        for name in self.OWNER_AGENTS:
            content = (REPO / "agents" / f"{name}.md").read_text(encoding="utf-8")
            with self.subTest(name=name):
                for fragment in self.MATRIX_FRAGMENTS:
                    self.assertIn(fragment, content)

    def test_worked_examples_use_the_canonical_none_closeout(self) -> None:
        for name in ("prompt-engineer", "sde-fullstack"):
            content = (REPO / "agents" / f"{name}.md").read_text(encoding="utf-8")
            example = content.split("### Worked example", 1)[1]
            with self.subTest(name=name):
                self.assertIn("> **Learning**: none — no reusable signal", example)

    def test_self_improve_loop_declares_the_matrix_owner_and_drift_rule(self) -> None:
        content = (REPO / "skills" / "self-improve-loop" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("scripts/learning_ledger.py:STATE_DISPOSITIONS", content)
        self.assertIn("owns that executable matrix", content)
        self.assertIn("treat the mirrors as drift", content)

    def test_retro_template_separates_retro_scope_from_candidate_scope(self) -> None:
        content = (
            REPO / "skills" / "self-improve-loop" / "references" / "retro-protocol.md"
        ).read_text(encoding="utf-8")
        template = content.split("```text", 1)[1].split("```", 1)[0]
        lines = [line for line in template.splitlines() if line]
        self.assertTrue(lines[0].startswith("Retro scope:"), lines)
        learning_index = next(
            index for index, line in enumerate(lines) if line.startswith("Learning:")
        )
        self.assertEqual("Evidence:", lines[learning_index + 1].split(" ", 1)[0])
        self.assertEqual("Scope:", lines[learning_index + 2].split(" ", 1)[0])


if __name__ == "__main__":
    unittest.main()
