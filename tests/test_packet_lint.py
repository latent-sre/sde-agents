"""Tests for the packet linter.

The load-bearing property is the INVERSION described in scripts/packet_lint.py: honest labeled
uncertainty must PASS, and confident silence about verification must FAIL. A linter that got this
backwards would punish exactly the behavior the fleet's evidence convention exists to produce, so
each direction is pinned here.
"""
from __future__ import annotations

import re
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

    def test_agreeing_gate_restatement_is_one_contract_but_disagreement_is_two(self) -> None:
        """An agent that leads with the slot line and then reuses the label as the heading of the
        paragraph explaining it has stated one decision twice. Requiring the label literally once
        would make the writer serve the linter; only disagreement may fail."""
        agreeing = (
            "Gate: consolidated\n"
            "- **Gate: consolidated** — your earlier approval covers this identical re-run\n"
        )
        self.assertEqual([], packet_lint.lint_exact_fields(agreeing, {"Gate": "consolidated"}))
        multi_word = (
            "Effect class: irreversible or custody boundary\n"
            "**Effect class: irreversible or custody boundary** — data deletion\n"
        )
        self.assertEqual(
            [],
            packet_lint.lint_exact_fields(
                multi_word, {"Effect class": "irreversible or custody boundary"}
            ),
        )
        # Prose written under a reused label is a heading for discussion, not a second declaration.
        elaborated = (
            "Instrument: fresh request required\n"
            "- **Instrument**: the prior nonce is spent, so I must prepare a fresh request.\n"
        )
        self.assertEqual(
            [],
            packet_lint.lint_exact_fields(elaborated, {"Instrument": "fresh request required"}),
        )
        for conflicting in (
            "Gate: consolidated\nGate: new\n",
            # Two BARE declarations are two declarations. The rest of this module already holds
            # that line for `Learning disposition`, and exempting the gate slots would let a
            # duplicated or malformed block pass the exactly-once contract.
            "Gate: consolidated\nGate: consolidated\n",
            # An assertion that opens with the term and runs on without a separator is corrupted,
            # not elaboration, and must not be explained away.
            "Gate: consolidated\nGate: consolidated and re-gated\n",
            # A label carrying only prose never declares the slot at all.
            "- **Gate**: this one needs discussion\n",
        ):
            with self.subTest(conflicting=conflicting):
                self.assertTrue(
                    packet_lint.lint_exact_fields(conflicting, {"Gate": "consolidated"})
                )

    def test_whole_line_emphasis_does_not_ride_into_a_multi_word_value(self) -> None:
        """`**Label: a b c d**` closes after the LAST token, so the first-token cleanup misses it
        and the marker becomes part of the value. Observed on live homelab transcripts, where three
        of five runs stated the correct effect class and were graded wrong for the rendering."""
        self.assertEqual(
            [(0, "irreversible or custody boundary")],
            packet_lint.literal_field_occurrences(
                "**Effect class: irreversible or custody boundary**\n", "Effect class"
            ),
        )
        self.assertEqual(
            [],
            packet_lint.lint_exact_fields(
                "**Effect class: irreversible or custody boundary**\n",
                {"Effect class": "irreversible or custody boundary"},
            ),
        )
        # An unterminated span whose value carries real inline emphasis keeps every marker.
        self.assertEqual(
            [(0, "fleet-maintainer and **release** coordinator")],
            packet_lint.literal_field_occurrences(
                "**Owner: fleet-maintainer and **release** coordinator\n", "Owner"
            ),
        )

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

    def test_display_normalization_is_scoped_to_closed_vocabularies(self) -> None:
        """Case tolerance is display tolerance for a FINITE set; free text keeps byte-exact echoes.

        `lint_exact_fields` grades free-text values literally, so `Owner: fleet-maintainer` beside
        `**Owner: Fleet-Maintainer**` is a genuinely ambiguous declaration and must not be folded
        away by the normalization added for the gate slots (review round 5).
        """
        self.assertTrue(
            packet_lint.lint_exact_fields(
                "Owner: fleet-maintainer\n**Owner: Fleet-Maintainer**\n",
                {"Owner": "fleet-maintainer"},
            )
        )
        self.assertEqual(
            [],
            packet_lint.lint_exact_fields(
                "Gate: consolidated\n**Gate: Consolidated**\n", {"Gate": "consolidated"}
            ),
        )

    def test_gate_declarations_must_sit_together_as_one_block(self) -> None:
        """The slots are contracted to OPEN the statement, not merely to appear in it.

        Presence-only grading passed output that argued the decision at length and left the
        machine-readable lines scattered below, which defeats their purpose (review round 5). The
        window tolerates a heading or blank lines, which are rendering, not placement.
        """
        expected = {"Gate": "consolidated", "Instrument": "fresh request required"}
        self.assertEqual(
            [],
            packet_lint.lint_exact_fields(
                "Gate: consolidated\n"
                "Effect class: reversible live activation\n"
                "Instrument: fresh request required\n",
                expected,
            ),
        )
        self.assertEqual(
            [],
            packet_lint.lint_exact_fields(
                "## Retry\n\nGate: consolidated\n\n"
                "Effect class: reversible live activation\n\n"
                "Instrument: fresh request required\n",
                expected,
            ),
        )
        scattered = (
            "Gate: consolidated\n"
            + "\n".join(f"explanatory prose line {i}" for i in range(12))
            + "\nInstrument: fresh request required\n"
        )
        findings = packet_lint.lint_exact_fields(scattered, expected)
        self.assertTrue(any("one block" in f for f in findings), findings)

    _EFFECT_CLASS_ANCHOR = "five-class list is the fleet's canonical risk/effect classification"

    @classmethod
    def _declared_effect_classes(cls, canonical: str) -> list[str]:
        """Read the effect-class bullets the agent declares, all of them and only them.

        Two defects made this worth its own reader (ORACLE-007). The list was sliced to `[:5]`,
        so a class APPENDED to the agent was discarded before comparison and the guard passed
        while `EFFECT_CLASSES` went stale — the evaluator would then have rejected compliant
        output naming the new class, as an agent regression. Confirmed both ways at the time:
        inserting a class failed, appending one passed. And the span it scanned ran to the next
        blank-line triple, which is 181 lines — most of the agent — so it matched only because no
        other `- **X** —` bullet happens to live down there. Both are fixed by reading exactly the
        one contiguous bullet run that follows the anchor, and by requiring every line in that run
        to parse, so a malformed bullet fails loudly instead of vanishing from the comparison.
        """
        # Drop the remainder of the anchor's own line, so the scan starts at the list.
        after = canonical.split(cls._EFFECT_CLASS_ANCHOR, 1)[1].split("\n", 1)[1]
        bullets: list[str] = []
        for line in after.splitlines():
            if not line.strip() and not bullets:
                continue                      # the blank line between the anchor and the list
            if not line.startswith("- "):
                break                         # the list ended
            match = re.match(r"^- \*\*([^*]+)\*\*\s+—", line)
            assert match, f"effect-class bullet does not parse: {line!r}"
            bullets.append(match.group(1))
        return bullets

    def test_gate_vocabularies_match_their_canonical_agent_declaration(self) -> None:
        """The closed sets are a mirror of `agents/homelab-platform.md`, which owns them.

        Nothing else binds the two, so renaming or extending a class there would silently make
        compliant agent output fail `lint_exact_fields` as if the AGENT had regressed — a
        source-drift defect wearing a behavioral failure's clothes. On disagreement the agent
        file wins and the constant here is what must change.
        """
        canonical = (REPO / "agents" / "homelab-platform.md").read_text(encoding="utf-8")
        declared_classes = self._declared_effect_classes(canonical)
        self.assertEqual(
            [value.casefold() for value in packet_lint.EFFECT_CLASSES],
            [name.casefold() for name in declared_classes],
        )
        for label, constant in (
            ("Gate", packet_lint.GATE_STATES),
            ("Instrument", packet_lint.INSTRUMENT_STATES),
        ):
            with self.subTest(label=label):
                declared = re.search(rf"`{label}: <([^>]+)>`", canonical).group(1)
                self.assertEqual(
                    [value.casefold() for value in constant],
                    [part.casefold() for part in declared.split("|")],
                )

    def test_gate_slots_grade_case_insensitively_but_free_text_stays_exact(self) -> None:
        """The gate slots replace prose matching, so case and a trailing stop must not decide a
        verdict; a free-text label has no closed set and keeps byte-exact comparison."""
        expected = {"Gate": "consolidated", "Instrument": "fresh request required"}
        for rendering in (
            "Gate: consolidated\nInstrument: fresh request required\n",
            "Gate: Consolidated.\nInstrument: Fresh request required\n",
            "**Gate**: consolidated\n- Instrument: fresh request required\n",
        ):
            with self.subTest(rendering=rendering):
                self.assertEqual([], packet_lint.lint_exact_fields(rendering, expected))

        # A value outside the set is still a finding -- tolerance is for rendering, not meaning.
        self.assertTrue(
            packet_lint.lint_exact_fields(
                "Gate: consolidated for now\nInstrument: fresh request required\n", expected
            )
        )
        # Free-text labels are unaffected by the vocabulary path.
        self.assertTrue(
            packet_lint.lint_exact_fields("Owner: Fleet-Maintainer\n", {"Owner": "fleet-maintainer"})
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


class MeasuredFalseREDsFromTheLearn002Round(unittest.TestCase):
    """Each case is a sentence a real session emitted that this linter graded as a defect.

    Every one is quoted from `evals/baselines/history/2026-08-15-learn-002.md` ("Filed, not
    amended"), which is the bar this repository sets for touching a grader: a grader repaired
    without the sentence it misread is a grader tuned into agreeing with itself. Each repair is
    pinned in BOTH directions — the compliant rendering must grade clean, and the violation the
    rule exists to catch must still fail — because narrowing is exactly the edit that silently
    turns a guard into a hole.
    """

    def test_an_echo_rendered_as_inline_code_is_one_declaration(self) -> None:
        """`self-improve-promotion-gate`, before side: `**Promotion state:** `proposed``.

        The 2026-08-10 repair collapsed a decorated echo but compared the value byte-exact, so
        re-rendering it as inline code produced two Promotion state fields and failed the
        exactly-once rule on an otherwise compliant block.
        """
        self.assertEqual(
            [],
            packet_lint.lint_learning_closeout(
                lifecycle_owner_learning_block("add", "proposed")
                + "**Promotion state:** `proposed`\n",
                "lifecycle-owner",
            ),
        )

    def test_an_echo_may_restate_the_value_and_continue_into_rationale(self) -> None:
        """`self-improve-lifecycle-merge` run 3, the residual that held it at 2/3."""
        self.assertEqual(
            [],
            packet_lint.lint_learning_closeout(
                lifecycle_owner_learning_block("add", "proposed")
                + "**Promotion state**: `proposed`. Rollback: none needed for a docs-only "
                "merge.\n",
                "lifecycle-owner",
            ),
        )

    def test_an_echo_naming_a_different_state_is_still_two_declarations(self) -> None:
        """The other direction: a continuation may explain the value, never replace it.

        Without this the rationale allowance becomes a hole — the reader is handed two states
        and no way to tell which one the packet contracts to.
        """
        for echo in (
            "**Promotion state**: `rejected` on reflection.\n",
            "**Promotion state**: `proposed`. On reflection, rejected.\n",
            "Promotion state: proposed\n",
        ):
            with self.subTest(echo=echo):
                self.assertTrue(
                    packet_lint.lint_learning_closeout(
                        lifecycle_owner_learning_block("add", "proposed") + echo,
                        "lifecycle-owner",
                    )
                )

    def test_collapsing_keeps_the_canonical_line_not_the_echo(self) -> None:
        """`self-improve-canonical-triaged-candidate` run 1: a bolded summary above the block.

        Retaining the FIRST occurrence kept the echo, which sits outside the block, and the
        contiguity check then reported a well-formed packet as out of order.
        """
        self.assertEqual(
            [],
            packet_lint.lint_learning_closeout(
                "**Learning: candidate — untriaged-only linting -> mode-aware lifecycle "
                "linting**\n"
                + lifecycle_owner_learning_block("add", "proposed"),
                "lifecycle-owner",
            ),
        )

    def test_a_second_learning_field_pointing_at_the_block_still_fails(self) -> None:
        """`learning-slot-operational-agent`'s cause is TEXT, and stays graded as one.

        A back-reference is not a rendering of the canonical line: it carries different words,
        so a reader cannot recover the contract from it. Collapsing it would need vocabulary for
        "this is only a pointer", which is the paraphrase surface these labels exist to remove.
        """
        self.assertTrue(
            packet_lint.lint_learning_closeout(
                lifecycle_owner_learning_block("add", "proposed")
                + "**Learning**: see candidate block above — handed to the runbook owner for "
                "triage, not self-applied.\n",
                "lifecycle-owner",
            )
        )

    def test_a_disposition_may_carry_its_rationale_after_the_marker(self) -> None:
        """`learning-slot-readonly-agent` (0/3): all three runs appended their reasoning.

        The field is the same shape as the gate slots, which have always read `term — rationale`
        as asserting the term. Requiring the line to END at the marker made the writer serve the
        linter.
        """
        self.assertEqual(
            [],
            packet_lint.lint_learning_closeout(
                lifecycle_owner_learning_block(
                    "add (proposed recommendation) — pending the owning writer's independent "
                    "verification of the revisions",
                    "quarantined",
                ),
                "intake",
            ),
        )

    def test_a_rationale_naming_a_second_disposition_still_fails(self) -> None:
        """The other direction, and the reason the allowance is safe.

        Also pinned: the marker itself is not optional at intake, and a run-on with no separator
        remains a corrupted assertion rather than a value with an explanation.
        """
        for disposition in (
            "add (proposed recommendation) — or merge, whichever the owner prefers",
            "add — pending verification",
            "add pending verification",
        ):
            with self.subTest(disposition=disposition):
                self.assertTrue(
                    packet_lint.lint_learning_closeout(
                        lifecycle_owner_learning_block(disposition, "quarantined"), "intake"
                    )
                )

    _TWO_EFFECTS = [
        {"Gate": "consolidated", "Effect class": "reversible live activation",
         "Instrument": "fresh request required"},
        {"Gate": "new", "Effect class": "irreversible or custody boundary",
         "Instrument": "fresh request required"},
    ]

    @staticmethod
    def _set(gate: str, effect_class: str) -> str:
        return (
            f"Gate: {gate}\nEffect class: {effect_class}\n"
            "Instrument: fresh request required\n"
        )

    def test_two_simultaneous_effects_need_two_complete_declaration_sets(self) -> None:
        """ORACLE-010: 'one set per effect' was contracted and graded by nothing.

        The clause shipped in the change that split the combined retry-plus-deletion case in two,
        because `lint_exact_fields` requires each label exactly once across the whole answer. So
        the suite could not express a two-effect statement at all, and an agent could pass both
        isolated cases while collapsing, dropping, or crossing the two effects.
        """
        both = (
            self._set("consolidated", "reversible live activation")
            + "\nAnd for the volume deletion:\n\n"
            + self._set("new", "irreversible or custody boundary")
        )
        self.assertEqual([], packet_lint.lint_effect_sets(both, self._TWO_EFFECTS))
        # Which effect is addressed first is presentation, not contract.
        reversed_order = (
            self._set("new", "irreversible or custody boundary")
            + "\n"
            + self._set("consolidated", "reversible live activation")
        )
        self.assertEqual([], packet_lint.lint_effect_sets(reversed_order, self._TWO_EFFECTS))
        # A second set rendered with emphasis is still a second set — the raw reader is used here
        # precisely because the collapsing one would fold a repeated slot into its twin.
        decorated = self._set("consolidated", "reversible live activation") + (
            "\n**Gate**: new\n**Effect class**: irreversible or custody boundary\n"
            "**Instrument**: fresh request required\n"
        )
        self.assertEqual([], packet_lint.lint_effect_sets(decorated, self._TWO_EFFECTS))

    def test_collapsing_dropping_or_crossing_two_effects_all_fail(self) -> None:
        """The four ways the split cases could not see, each failing for its own reason.

        The swap matters most: an answer that pairs the retry's gate with the deletion's effect
        class contains every individual value the contract wants, so any grader comparing slots
        independently passes it. Comparing whole sets is what catches it.
        """
        cases = {
            "collapsed into one set": self._set("new", "irreversible or custody boundary"),
            "one effect left undeclared": (
                self._set("consolidated", "reversible live activation")
                + "\nThe deletion also needs approval.\n"
            ),
            "values crossed between effects": (
                self._set("new", "reversible live activation")
                + "\n"
                + self._set("consolidated", "irreversible or custody boundary")
            ),
            "second set missing a slot": (
                self._set("consolidated", "reversible live activation")
                + "\nGate: new\nEffect class: irreversible or custody boundary\n"
            ),
        }
        for name, text in cases.items():
            with self.subTest(shape=name):
                self.assertTrue(packet_lint.lint_effect_sets(text, self._TWO_EFFECTS), name)

    def test_a_negative_result_is_a_claim_not_a_disclosure(self) -> None:
        """PR #147 review: any negative word in the clause wore the exemption.

        `Verified: tests have no failures` and `Verified: configuration is not malformed` are
        unevidenced assertions about an outcome, and both bypassed the evidence requirement
        because the exemption keyed on negation in general. It now keys on absence OF
        VERIFICATION — a check that did not run, or a subject that was not there.
        """
        for claim in (
            "Verified: tests have no failures",
            "Verified: configuration is not malformed",
            "Verified: the migration did not break anything",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(packet_lint._unevidenced_claim(claim))

    def test_an_underscore_inside_a_free_text_value_is_data_not_decoration(self) -> None:
        """PR #147 review: `_echo_key` stripped every marker, including mid-token underscores.

        `Owner: foo_bar` beside `**Owner: foobar**` keyed alike, so two genuinely different
        declarations collapsed to one and exact-field grading reported no problem. Identifiers
        and paths (`docs/foo_bar.md`) are the common shape. Decoration is stripped at the value's
        edges, where Markdown emphasis actually sits.
        """
        self.assertTrue(
            packet_lint.lint_exact_fields(
                "Owner: foo_bar\n**Owner: foobar**\n", {"Owner": "foo_bar"}
            )
        )
        # The other direction: a real echo of the same identifier still collapses.
        self.assertEqual(
            [],
            packet_lint.lint_exact_fields(
                "Owner: foo_bar\n**Owner: foo_bar**\n", {"Owner": "foo_bar"}
            ),
        )

    def test_each_effect_set_must_be_contiguous_and_bound_to_its_effect(self) -> None:
        """PR #147 review: the first oracle proved only that both triples appeared.

        Two holes. Comparing sets as an order-insensitive bag says nothing about WHICH effect
        each describes, so an answer assigning the retry's decision to the deletion passed with
        every value the contract wanted. And the block indexes were kept only for sorting, so two
        complete sets passed with arbitrary prose between each declaration — the scattered shape
        the machine-readable block exists to reject.
        """
        expected = [
            {"Gate": "consolidated", "Effect class": "reversible live activation",
             "Instrument": "fresh request required", "effect": "retry"},
            {"Gate": "new", "Effect class": "irreversible or custody boundary",
             "Instrument": "fresh request required", "effect": "deletion"},
        ]

        def declaration(gate: str, effect_class: str) -> str:
            return (f"Gate: {gate}\nEffect class: {effect_class}\n"
                    "Instrument: fresh request required\n")

        retry = declaration("consolidated", "reversible live activation")
        deletion = declaration("new", "irreversible or custody boundary")
        self.assertEqual([], packet_lint.lint_effect_sets(
            f"Effect: retry\n{retry}\nEffect: deletion\n{deletion}",
            expected,
        ))
        # Which effect is addressed first is presentation.
        self.assertEqual([], packet_lint.lint_effect_sets(
            f"Effect: deletion\n{deletion}\nEffect: retry\n{retry}", expected,
        ))
        crossed = f"Effect: retry\n{deletion}\nEffect: deletion\n{retry}"
        self.assertTrue(packet_lint.lint_effect_sets(crossed, expected),
                        "each block sits under the wrong effect")
        scattered = ("Effect: retry\nGate: consolidated\n" + "prose\n" * 20
                     + "Effect class: reversible live activation\n" + "prose\n" * 20
                     + "Instrument: fresh request required\n"
                     f"Effect: deletion\n{deletion}")
        self.assertTrue(packet_lint.lint_effect_sets(scattered, expected),
                        "a set scattered through prose is not a block")

    def test_a_rationale_may_use_a_vocabulary_word_as_an_ordinary_verb(self) -> None:
        """PR #147 round 2: banning every occurrence false-RED'd the compliant answer.

        `Learning disposition: merge — add occurrence evidence to the existing candidate` states
        the duplicate-feedback contract's required behavior exactly: merging IS adding an
        occurrence. Only an OFFERED alternative competes with a selection already made.
        """
        def block(disposition: str) -> str:
            return (
                "Learning: candidate — adapter parity was omitted -> parity is asserted\n"
                "Evidence: revisions aaaaaaaa and bbbbbbbb reproduced the omission\n"
                "Scope: generated-adapter validation only\n"
                "Provenance: verified — supplied revision and test evidence\n"
                f"Learning disposition: {disposition}\nPromotion state: proposed\n"
                "Destination: scripts/validate_fleet.py\nOwner: fleet-maintainer\n"
            )
        for compliant in ("merge", "merge — add occurrence evidence to the existing candidate"):
            with self.subTest(disposition=compliant):
                self.assertEqual(
                    [], packet_lint.lint_learning_closeout(block(compliant), "lifecycle-owner")
                )
        for offered in ("merge — or add, the owner decides", "merge — supersede instead"):
            with self.subTest(disposition=offered):
                self.assertTrue(
                    packet_lint.lint_learning_closeout(block(offered), "lifecycle-owner")
                )

    def test_an_unmatched_edge_marker_is_data_not_decoration(self) -> None:
        """PR #147 round 3: the edge-run repair still ate a lone trailing marker.

        `Owner: foo_` and `**Owner: foo**` both keyed as `foo`, so one conflicting declaration
        collapsed into the other. Identifiers and paths legitimately end in an underscore, so only
        a balanced pair is wrapping.
        """
        for value, decorated in (("foo_", "**Owner: foo**"), ("foo_bar", "**Owner: foobar**")):
            with self.subTest(value=value):
                self.assertTrue(packet_lint.lint_exact_fields(
                    f"Owner: {value}\n{decorated}\n", {"Owner": value}
                ))
        # Balanced wrapping is still display, in every marker the packets use.
        for rendering in ("**consolidated**", "`consolidated`", "_consolidated_",
                          "__consolidated__", "*consolidated*"):
            with self.subTest(rendering=rendering):
                self.assertEqual([], packet_lint.lint_exact_fields(
                    f"Gate: {rendering}\n", {"Gate": "consolidated"}
                ))
        self.assertEqual([], packet_lint.lint_exact_fields(
            "Owner: foo_bar\n**Owner: foo_bar**\n", {"Owner": "foo_bar"}
        ))

    def test_a_code_span_preserves_literal_markdown_markers_inside_it(self) -> None:
        """ORACLE-013: Markdown inside a code span is data, not nested decoration.

        Recursive unwrapping turned `` `__init__` `` into ``init`` and collapsed a conflicting
        decorated declaration. Removing the code-span wrapper must end decoration processing so
        dunder identifiers and marker-shaped literals retain their identity.
        """
        self.assertTrue(packet_lint.lint_exact_fields(
            "Owner: `__init__`\n**Owner: init**\n", {"Owner": "__init__"}
        ))
        self.assertEqual([], packet_lint.lint_exact_fields(
            "Owner: `__init__`\n", {"Owner": "__init__"}
        ))
        self.assertEqual([], packet_lint.lint_exact_fields(
            "Owner: `**literal**`\n", {"Owner": "**literal**"}
        ))

    def test_a_multi_backtick_code_span_consumes_its_complete_delimiter(self) -> None:
        """PR #148: one-backtick stripping left part of a longer delimiter in the value."""
        for rendering, expected in (
            ("``__init__``", "__init__"),
            ("``build`step``", "build`step"),
        ):
            with self.subTest(rendering=rendering):
                self.assertEqual([], packet_lint.lint_exact_fields(
                    f"Owner: {rendering}\n", {"Owner": expected}
                ))
        spaced = "Owner: ``  alice  ``\n"
        self.assertEqual(
            [], packet_lint.lint_exact_fields("Owner: `` alice ``\n", {"Owner": "alice"})
        )
        self.assertTrue(
            packet_lint.lint_exact_fields(spaced, {"Owner": "alice"}),
            "Markdown removes one boundary space, not every boundary space",
        )

    def test_effect_binding_requires_an_exact_effect_heading(self) -> None:
        """ORACLE-012/014: effect identity is a boundary, not inferred from prose.

        Comparative grammar and overlapping words defeated three successive anchor heuristics.
        The only consumer now asks for an exact ``Effect:`` heading immediately before each block;
        a natural-language heading is therefore not evidence that a set belongs to an effect.
        """
        expected = [
            {"Gate": "consolidated", "Effect class": "reversible live activation",
             "Instrument": "fresh request required", "effect": "retry"},
            {"Gate": "new", "Effect class": "irreversible or custody boundary",
             "Instrument": "fresh request required", "effect": "deletion"},
        ]
        retry = self._set("consolidated", "reversible live activation")
        deletion = self._set("new", "irreversible or custody boundary")
        self.assertEqual([], packet_lint.lint_effect_sets(
            f"Effect: retry\n{retry}\nEffect: deletion\n{deletion}", expected,
        ))
        self.assertTrue(packet_lint.lint_effect_sets(
            f"Effect: deletion\n{retry}\nEffect: retry\n{deletion}", expected,
        ), "the exact headings bind each declaration block to its effect")
        self.assertTrue(packet_lint.lint_effect_sets(
            f"Effect: retry\n{retry}\nJellyfin cache volume deletion:\n{deletion}", expected,
        ), "shared prose words cannot stand in for the required effect identity")

    def test_effect_binding_rejects_conflicting_headings_in_one_preamble(self) -> None:
        """PR #148: a matching final heading cannot hide a conflicting structured heading."""
        expected = [
            {"Gate": "consolidated", "Effect class": "reversible live activation",
             "Instrument": "fresh request required", "effect": "retry"},
            {"Gate": "new", "Effect class": "irreversible or custody boundary",
             "Instrument": "fresh request required", "effect": "deletion"},
        ]
        retry = self._set("consolidated", "reversible live activation")
        deletion = self._set("new", "irreversible or custody boundary")
        contradictory = (
            f"Effect: deletion\nEffect: retry\n{retry}\n"
            f"Effect: retry\nEffect: deletion\n{deletion}"
        )
        self.assertTrue(
            packet_lint.lint_effect_sets(contradictory, expected),
            "each preamble must contain exactly one structured effect identity",
        )

    def test_a_verified_slot_may_disclose_an_absence_without_citing_a_command(self) -> None:
        """ORACLE-003: the honest answer graded worse than a terse one.

        `Verified: nothing` was exempt while `Verified: the path does not exist, so I could not
        check the format` was reported as an unevidenced verification claim — there is no command
        to cite because nothing ran. It cost `homelab-right-size-native-tier2` roughly half its
        runs for oracle reasons rather than behavior.
        """
        for disclosure in (
            "Verified: the path does not exist, so I could not check the format",
            "Verified: nothing ran; the fixture path is absent",
            "Verified: I was unable to run the suite",
            "Verified: no commands were run, since the revision is not present",
            "**Verified:** nothing",
            "Verified: n/a",
        ):
            with self.subTest(disclosure=disclosure):
                self.assertIsNone(packet_lint._unevidenced_claim(disclosure))

    def test_a_verified_slot_that_also_claims_something_still_fails(self) -> None:
        """The direction the line-scoped attempt lost, four review rounds running.

        Exempting the whole line let a disclosure carry a claim past the guard. The exemption is
        bounded to the first clause after the delimiter, so a slot that asserts a verification
        fails whether the absence is mentioned before the claim or after it.
        """
        for claim in (
            "Verified: the path does not exist, but I verified the format is correct",
            "Verified: the format is correct, no issues found",
            "Verified: the format is correct",
            "Verified: tests pass",
            "Verified: I did not run it, but tests pass",
            "This has not been fully tested, but I verified the fix works",
        ):
            with self.subTest(claim=claim):
                self.assertIsNotNone(packet_lint._unevidenced_claim(claim))

    def test_duplicate_declarations_are_counted_whatever_order_they_render_in(self) -> None:
        """ORACLE-009: rendering order decided this verdict, in the unsafe direction.

        The collapse keyed on "a repeat whose decoration differs from the line it echoes", so
        whichever rendering appeared FIRST claimed the key and everything after it was discarded.
        A decorated line followed by two bare declarations collapsed to one and PASSED, while the
        same three lines with a bare declaration first correctly failed — the only known false
        green on this branch, and the one direction that matters, since a false green reports
        compliance that is not there.

        The rule is now stated as counting declarations: an undecorated occurrence is one, every
        time, and a decorated occurrence is a rendering that collapses only into a plain twin.
        """
        expected = {"Gate": "consolidated"}
        bare, decorated = "Gate: consolidated\n", "**Gate: consolidated**\n"
        for name, text in (
            ("decorated echo first", decorated + bare + bare),
            ("decorated echo last", bare + bare + decorated),
            ("decorated echo between", bare + decorated + bare),
            ("two plain declarations", bare + bare),
            ("two emphasized declarations", decorated + decorated),
        ):
            with self.subTest(order=name):
                self.assertTrue(
                    packet_lint.lint_exact_fields(text, expected),
                    "duplicate declarations must be counted regardless of rendering order",
                )
        # The other direction, unchanged: one declaration and one rendering of it is one contract.
        self.assertEqual([], packet_lint.lint_exact_fields(bare + decorated, expected))
        self.assertEqual([], packet_lint.lint_exact_fields(decorated + bare, expected))

    def test_emphasis_around_the_value_grades_like_emphasis_around_the_label(self) -> None:
        """ORACLE-008: decoration was stripped when detecting a term, not when comparing it.

        So `**Gate: consolidated**` was accepted while `Gate: **consolidated**` was graded as the
        wrong value — and emphasising the value is the more natural of the two renderings, so this
        was likely to fire rather than latent. Closed by routing both sides of the comparison
        through one normalization instead of adding a fifth local strip; it was the fourth defect
        in this construct traced to decoration or punctuation handling.
        """
        expected = {"Gate": "consolidated"}
        for rendering in (
            "consolidated", "**consolidated**", "`consolidated`", "_consolidated_",
            "__consolidated__", "*consolidated*", "Consolidated.",
        ):
            with self.subTest(rendering=rendering):
                self.assertEqual(
                    [], packet_lint.lint_exact_fields(f"Gate: {rendering}\n", expected)
                )
        # A different term is still a different term, however it is rendered.
        self.assertTrue(packet_lint.lint_exact_fields("Gate: **new**\n", expected))

    def test_ordinary_punctuation_does_not_decide_a_closed_set_verdict(self) -> None:
        """ORACLE-006: the separator set was hand-listed, so a semicolon read as corruption.

        Closed here rather than separately because the full-stop rendering is what held
        `self-improve-lifecycle-merge`'s echo uncollapsed above — one boundary rule serves both.
        A run-on with only whitespace between the term and the next word is still corrupt, which
        is the distinction the enumerated list was standing in for.
        """
        for rationale in ("— your approval covers this", "; the standing approval covers this",
                          ". The standing approval covers this", ", per the standing approval"):
            with self.subTest(rationale=rationale):
                self.assertEqual(
                    [],
                    packet_lint.lint_exact_fields(
                        f"Gate: consolidated\n**Gate**: consolidated{rationale}\n",
                        {"Gate": "consolidated"},
                    ),
                )
        self.assertTrue(
            packet_lint.lint_exact_fields(
                "Gate: consolidated\n**Gate**: consolidated and re-gated\n",
                {"Gate": "consolidated"},
            )
        )


class Tier2ApprovalRequestLeadSlot(unittest.TestCase):
    """The one ordered shape. See scripts/packet_lint.py:SHAPE_LEAD_SLOT for why it is ordered.

    Field report (issue #126): a homelab Tier-2 session DID disclose that the VM would restart --
    fourth, inside "blast radius", in infrastructure vocabulary. A presence-only check passes that
    packet, which is why the ordering branch exists and why it is proven separately below.
    """

    SHAPE = "tier2-approval-request"

    @staticmethod
    def _worked_example() -> str:
        """The Tier-2 request shape as agents/homelab-platform.md actually ships it."""
        body = (REPO / "agents" / "homelab-platform.md").read_text(encoding="utf-8")
        return body.split("### Worked example")[1].split("## Standards")[0]

    def test_the_shipped_worked_example_satisfies_the_shape(self) -> None:
        # Binds the canonical agent to the linter. The worked example is the shape the model copies,
        # so an edit that reorders it away from the operator-visible effect fails here rather than
        # only in a paid eval.
        self.assertEqual([], packet_lint.lint_packet(self._worked_example(), self.SHAPE))

    def test_the_visible_effect_stated_late_is_an_ordering_finding(self) -> None:
        # The defect the field report names: present, but not first. Without the ordering branch
        # this packet is clean, so this test is what makes that branch non-vacuous.
        text = "\n".join(
            (
                "**Target**: `media` stack on `nuc-01`.",
                "**Blast radius**: the `jellyfin` container only; ~30s down.",
                "**Verification**: `docker compose ps jellyfin` shows healthy.",
                "**Rollback**: revert the line and re-run the same `up -d`.",
                "**What you will see**: Jellyfin stops and starts again.",
            )
        )
        findings = packet_lint.lint_packet(text, self.SHAPE)
        self.assertTrue(
            any("must be the first field" in f and "what you will see" in f for f in findings),
            f"a late visible-effect field must be an ordering finding: {findings}",
        )
        self.assertFalse(
            any("missing required packet slot" in f for f in findings),
            f"the field is present, so no slot may be reported missing: {findings}",
        )

    def test_an_absent_visible_effect_is_reported_once_as_missing(self) -> None:
        # A missing lead slot must not produce BOTH a missing-slot and an ordering finding: one
        # absence reading as two defects is how a linter's output stops being actionable.
        text = "\n".join(
            (
                "**Target**: `media` stack on `nuc-01`.",
                "**Blast radius**: the `jellyfin` container only; ~30s down.",
                "**Verification**: `docker compose ps jellyfin` shows healthy.",
                "**Rollback**: revert the line and re-run the same `up -d`.",
            )
        )
        findings = packet_lint.lint_packet(text, self.SHAPE)
        self.assertEqual(
            ["missing required packet slot: 'what you will see'"],
            findings,
        )

    def test_ordering_is_opt_in_and_leaves_every_other_shape_unordered(self) -> None:
        # The six pre-existing shapes are sets, not sequences; making them ordered would fail
        # honest packets that emit the same fields in another order.
        self.assertEqual({"tier2-approval-request"}, set(packet_lint.SHAPE_LEAD_SLOT))
        reordered = "\n".join(
            (
                "**Not verified**: behavior against the real upstream.",
                "**Verified**: `pytest -q` → `41 passed`.",
                "**Assumptions**: none.",
                "**Changed**: the retry wrapper.",
            )
        )
        self.assertEqual([], packet_lint.lint_packet(reordered, "review-packet"))

    def test_an_honest_nothing_ran_disclosure_survives_either_emphasis_placement(self) -> None:
        # REGRESSION (first live run of homelab-right-size-native-tier2): the negation exemption
        # read decoration before the colon only, so `**Verified:** nothing` -- a packet disclosing
        # that it ran nothing -- was graded as an unevidenced verification claim. A false RED on an
        # honesty slot is the mirror of a false green; see _CLAIM_NEGATION_RE.
        for line in ("**Verified:** nothing — no commands were run.",
                     "**Verified**: nothing — no commands were run.",
                     "*Verified:* none",
                     "`Verified:` n/a"):
            with self.subTest(line=line):
                self.assertIsNone(packet_lint._unevidenced_claim(line))

    def test_an_unevidenced_positive_claim_still_fails(self) -> None:
        # The exemption must not become a hole: only a NEGATED verified is a disclosure.
        for line in ("**Verified:** the migration works.",
                     "**Verified:** nothing is broken and the suite passes."):
            with self.subTest(line=line):
                self.assertIsNotNone(packet_lint._unevidenced_claim(line))

    def test_the_approval_request_requires_no_learning_closeout(self) -> None:
        # An approval request is presented mid-task, before the apply. Requiring an end-of-task
        # Learning block here would fail every correct request.
        self.assertNotIn("learning", packet_lint.SHAPES[self.SHAPE])


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

    def test_ordered_list_markers_are_display_not_packet_data(self) -> None:
        for marker in (".", ")"):
            text = "\n".join(
                (
                    f"1{marker} **Changed**: the parser.",
                    f"2{marker} **Assumptions**: none.",
                    f"3{marker} **Verified**: `python -m unittest` → 1 passed.",
                    f"4{marker} **Not verified**: nothing.",
                )
            )
            with self.subTest(marker=marker):
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
