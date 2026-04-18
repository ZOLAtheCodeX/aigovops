"""Tests for singapore-magf-assessor plugin."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


CITATION_PATTERN = re.compile(
    r"^(Singapore MAGF 2e, (Section|Pillar) .+"
    r"|MAS FEAT Principles \(2018\), Principle (Fairness|Ethics|Accountability|Transparency)"
    r"|AI Verify \(IMDA 2024\), Principle [a-z-]+)$"
)


def _full_pillar_evidence() -> dict:
    return {
        "internal-governance": {
            "role_assignments": "AI governance committee chartered.",
            "risk_controls": "Annual AI risk review procedure.",
            "staff_training": "Quarterly AI ethics training log.",
        },
        "human-involvement": {
            "human_involvement_tier": "human-in-the-loop",
            "risk_matrix": "Documented probability-severity matrix.",
            "escalation_process": "Escalation to senior reviewer on low-confidence outputs.",
        },
        "operations-management": {
            "data_lineage": "End-to-end data lineage captured.",
            "data_quality": "Monthly data quality monitoring.",
            "bias_mitigation": "Protected-class parity testing.",
            "model_robustness": "Adversarial robustness testing.",
            "explainability": "SHAP explanations generated per decision.",
            "reproducibility": "Model artifacts versioned and hashed.",
            "monitoring": "Drift and performance dashboards.",
        },
        "stakeholder-communication": {
            "disclosure_policy": "Public AI use disclosure page.",
            "feedback_channel": "Consumer contact form for AI decisions.",
            "decision_review_process": "Documented decision-review workflow.",
        },
    }


def _full_feat_evidence() -> dict:
    return {
        "fairness": {
            "justifiability": "Model features documented and reviewed annually.",
            "accuracy_bias": "Regular review of accuracy and bias metrics.",
            "systematic_disadvantage": "Protected-class disparate-impact testing.",
        },
        "ethics": {
            "ethical_standards": "Decisions benchmarked against human-decision baseline.",
            "alignment": "Model aligned with firm code of conduct.",
            "human_alternative": "Escalation path to human underwriter.",
        },
        "accountability": {
            "internal_approval": "Model approved by credit risk committee.",
            "external_accountability": "Customer notice covers AI-driven decisions.",
            "data_subject_rights": "Appeal channel for adverse decisions.",
            "verification": "Reason codes produced per decision.",
        },
        "transparency": {
            "proactive_disclosure": "AI use disclosed in account-opening flow.",
            "clear_explanation": "Reason codes returned on adverse action notice.",
            "ease_of_understanding": "Plain-language explanation template.",
        },
    }


def _base_inputs(org_type: str = "general", **system_extras) -> dict:
    system = {
        "system_name": "TestSystem",
        "human_involvement_tier": "human-in-the-loop",
        "pillar_evidence": _full_pillar_evidence(),
    }
    system.update(system_extras)
    return {
        "system_description": system,
        "organization_type": org_type,
    }


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


class TestHappyPaths(unittest.TestCase):
    def test_happy_path_general_organization(self):
        result = plugin.generate_magf_assessment(_base_inputs(org_type="general"))
        self.assertEqual(result["organization_type"], "general")
        self.assertEqual(result["applicable_frameworks"], ["magf"])
        self.assertEqual(len(result["pillars"]), 4)
        for p in result["pillars"]:
            self.assertEqual(p["assessment_status"], "addressed")
        self.assertNotIn("feat_principles", result)

    def test_happy_path_financial_services_adds_feat(self):
        inputs = _base_inputs(org_type="financial-services")
        inputs["system_description"]["feat_evidence"] = _full_feat_evidence()
        result = plugin.generate_magf_assessment(inputs)
        self.assertEqual(result["applicable_frameworks"], ["magf", "feat"])
        self.assertIn("feat_principles", result)
        self.assertEqual(len(result["feat_principles"]), 4)
        for fp in result["feat_principles"]:
            self.assertEqual(fp["assessment_status"], "addressed")

    def test_happy_path_government_magf_only(self):
        result = plugin.generate_magf_assessment(_base_inputs(org_type="government"))
        self.assertEqual(result["applicable_frameworks"], ["magf"])
        self.assertNotIn("feat_principles", result)


# ---------------------------------------------------------------------------
# Human involvement tier classification
# ---------------------------------------------------------------------------


class TestHumanInvolvementTiers(unittest.TestCase):
    def test_human_in_the_loop(self):
        inputs = _base_inputs()
        inputs["system_description"]["human_involvement_tier"] = "human-in-the-loop"
        result = plugin.generate_magf_assessment(inputs)
        self.assertEqual(result["human_involvement_tier"]["tier"], "human-in-the-loop")
        self.assertIn("full control", result["human_involvement_tier"]["note"])

    def test_human_over_the_loop(self):
        inputs = _base_inputs()
        inputs["system_description"]["human_involvement_tier"] = "human-over-the-loop"
        result = plugin.generate_magf_assessment(inputs)
        self.assertEqual(result["human_involvement_tier"]["tier"], "human-over-the-loop")
        self.assertIn("monitors", result["human_involvement_tier"]["note"])

    def test_human_out_of_the_loop(self):
        inputs = _base_inputs()
        inputs["system_description"]["human_involvement_tier"] = "human-out-of-the-loop"
        result = plugin.generate_magf_assessment(inputs)
        self.assertEqual(result["human_involvement_tier"]["tier"], "human-out-of-the-loop")
        self.assertIn("autonomously", result["human_involvement_tier"]["note"])


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidation(unittest.TestCase):
    def test_missing_system_description_raises(self):
        with self.assertRaises(ValueError):
            plugin.generate_magf_assessment({"organization_type": "general"})

    def test_missing_organization_type_raises(self):
        with self.assertRaises(ValueError):
            plugin.generate_magf_assessment(
                {"system_description": {"system_name": "x"}}
            )

    def test_invalid_organization_type_raises(self):
        with self.assertRaises(ValueError):
            plugin.generate_magf_assessment(
                {
                    "system_description": {"system_name": "x"},
                    "organization_type": "unicorns",
                }
            )

    def test_invalid_human_involvement_tier_raises(self):
        with self.assertRaises(ValueError):
            plugin.generate_magf_assessment(
                {
                    "system_description": {
                        "system_name": "x",
                        "human_involvement_tier": "human-somewhere-near-the-loop",
                    },
                    "organization_type": "general",
                }
            )


# ---------------------------------------------------------------------------
# Warning triggers
# ---------------------------------------------------------------------------


class TestWarnings(unittest.TestCase):
    def test_warning_when_pillar_evidence_empty(self):
        inputs = _base_inputs()
        inputs["system_description"]["pillar_evidence"] = {}
        result = plugin.generate_magf_assessment(inputs)
        # Every pillar should have at least one warning about missing evidence.
        for p in result["pillars"]:
            self.assertTrue(
                any("no evidence_refs provided" in w for w in p["warnings"]),
                f"Pillar {p['id']} did not emit the expected evidence warning.",
            )

    def test_warning_when_feat_fairness_evidence_missing_for_financial_services(self):
        inputs = _base_inputs(org_type="financial-services")
        feat = _full_feat_evidence()
        feat.pop("fairness")
        inputs["system_description"]["feat_evidence"] = feat
        result = plugin.generate_magf_assessment(inputs)
        fairness = next(
            fp for fp in result["feat_principles"] if fp["id"] == "fairness"
        )
        self.assertEqual(fairness["assessment_status"], "not-addressed")
        self.assertTrue(
            any("fairness" in w for w in result["warnings"]),
            "Register-level warnings do not mention fairness.",
        )

    def test_warning_when_human_involvement_tier_missing(self):
        inputs = {
            "system_description": {
                "system_name": "x",
                "pillar_evidence": _full_pillar_evidence(),
            },
            "organization_type": "general",
        }
        result = plugin.generate_magf_assessment(inputs)
        self.assertEqual(
            result["human_involvement_tier"]["tier"], "human-in-the-loop"
        )
        self.assertTrue(
            any(
                "human_involvement_tier absent" in w for w in result["warnings"]
            ),
            "Expected warning about absent human_involvement_tier.",
        )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class TestRendering(unittest.TestCase):
    def test_markdown_contains_every_pillar_and_feat_for_financial_services(self):
        inputs = _base_inputs(org_type="financial-services")
        inputs["system_description"]["feat_evidence"] = _full_feat_evidence()
        result = plugin.generate_magf_assessment(inputs)
        md = plugin.render_markdown(result)
        for p in result["pillars"]:
            self.assertIn(p["name"], md)
        self.assertIn("MAS FEAT Principles", md)
        for fp in result["feat_principles"]:
            self.assertIn(fp["name"], md)

    def test_csv_row_count_matches_pillars_plus_feat(self):
        inputs = _base_inputs(org_type="financial-services")
        inputs["system_description"]["feat_evidence"] = _full_feat_evidence()
        result = plugin.generate_magf_assessment(inputs)
        csv_text = plugin.render_csv(result)
        lines = [l for l in csv_text.strip().split("\n") if l]
        # 1 header + 4 pillars + 4 feat = 9
        self.assertEqual(len(lines), 9)

    def test_csv_row_count_matches_pillars_only_for_general(self):
        result = plugin.generate_magf_assessment(_base_inputs(org_type="general"))
        csv_text = plugin.render_csv(result)
        lines = [l for l in csv_text.strip().split("\n") if l]
        self.assertEqual(len(lines), 5)


# ---------------------------------------------------------------------------
# Citation format compliance
# ---------------------------------------------------------------------------


class TestCitations(unittest.TestCase):
    def test_all_citations_match_declared_formats(self):
        inputs = _base_inputs(org_type="financial-services")
        inputs["system_description"]["feat_evidence"] = _full_feat_evidence()
        result = plugin.generate_magf_assessment(inputs)
        for c in result["citations"]:
            self.assertTrue(
                CITATION_PATTERN.match(c),
                f"Citation does not match declared format: {c!r}",
            )


# ---------------------------------------------------------------------------
# Style compliance
# ---------------------------------------------------------------------------


class TestStyleCompliance(unittest.TestCase):
    def test_no_em_dash_emoji_or_hedging_in_markdown(self):
        inputs = _base_inputs(org_type="financial-services")
        inputs["system_description"]["feat_evidence"] = _full_feat_evidence()
        result = plugin.generate_magf_assessment(inputs)
        md = plugin.render_markdown(result)
        self.assertNotIn("\u2014", md)
        hedging = (
            "may want to consider",
            "might be helpful to",
            "could potentially",
            "it is possible that",
            "you might find",
        )
        lowered = md.lower()
        for phrase in hedging:
            self.assertNotIn(phrase, lowered)
        # Common emoji ranges should not appear.
        for ch in md:
            cp = ord(ch)
            self.assertFalse(
                0x1F300 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF,
                f"Emoji-range character present: U+{cp:04X}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
