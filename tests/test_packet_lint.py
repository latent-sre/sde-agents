"""Tests for the packet linter.

The load-bearing property is the INVERSION described in scripts/packet_lint.py: honest labeled
uncertainty must PASS, and confident silence about verification must FAIL. A linter that got this
backwards would punish exactly the behavior the fleet's evidence convention exists to produce, so
each direction is pinned here.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("packet_lint", REPO / "scripts" / "packet_lint.py")
packet_lint = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(packet_lint)

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

    def test_every_shape_is_reachable_from_the_cli_listing(self) -> None:
        # A shape nobody can name is a shape nobody can assert against.
        self.assertIn("review-packet", packet_lint.SHAPES)
        self.assertTrue(all(slots for slots in packet_lint.SHAPES.values()))


if __name__ == "__main__":
    unittest.main()
