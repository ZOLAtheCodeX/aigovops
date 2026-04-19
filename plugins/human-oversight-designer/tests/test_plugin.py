"""
Tests for the human-oversight-designer plugin.

Runs under pytest or as a standalone script. No external dependencies.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _stale_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=400)).date().isoformat()


def _full_ability_coverage() -> dict:
    return {
        ability: {
            "enabled": True,
            "mechanism": "operator training plus dashboard",
            "evidence_ref": f"docs/oversight-{ability}.md",
        }
        for ability in plugin.ART_14_4_ABILITIES
    }


def _base_inputs() -> dict:
    return {
        "system_description": {
            "system_id": "SYS-001",
            "system_name": "ResumeScreen",
            "intended_use": "Rank candidate resumes for human reviewer.",
            "risk_tier": "high-risk-annex-iii",
            "jurisdiction": "EU",
            "deployment_context": "Internal HR workflow.",
            "decision_authority": "decision-support",
            "biometric_identification_system": False,
        },
        "oversight_design": {
            "mode": "human-in-the-loop",
            "ability_coverage": _full_ability_coverage(),
            "override_controls": [
                {
                    "control_name": "stop-button-1",
                    "control_type": "stop-button",
                    "activation_latency_seconds": 5,
                    "tested_date": _today_iso(),
                    "tested_by": "QA Engineer",
                },
            ],
            "operator_training": {
                "curriculum_ref": "docs/training-curriculum-v1.md",
                "assessment_ref": "docs/assessment-v1.md",
                "completion_rate_percent": 95,
                "annual_refresh": True,
            },
            "automation_bias_mitigations": [
                {
                    "mitigation_name": "confidence-display",
                    "rationale": "Show prediction confidence to reviewer.",
                    "reference": "docs/ui-spec.md",
                },
            ],
            "escalation_paths": [
                {
                    "trigger_condition": "model-confidence-below-threshold",
                    "recipient_role": "Senior HR Reviewer",
                    "response_sla_hours": 4,
                },
            ],
        },
        "assigned_oversight_personnel": [
            {
                "person_role": "HR Reviewer",
                "authority_level": "sole-authority",
                "training_evidence_ref": "docs/hr-reviewer-training.md",
            },
            {
                "person_role": "HR Manager",
                "authority_level": "veto-authority",
                "training_evidence_ref": "docs/hr-manager-training.md",
            },
        ],
        "enrich_with_crosswalk": False,
    }


class TestHappyPath(unittest.TestCase):
    def test_full_compliance_high_risk(self):
        result = plugin.design_human_oversight(_base_inputs())
        self.assertEqual(result["agent_signature"], plugin.AGENT_SIGNATURE)
        self.assertEqual(result["art_14_applicability"], "applies")
        self.assertEqual(
            result["ability_coverage_assessment"]["status"], "full-coverage"
        )
        self.assertFalse(result["mode_validation"]["blocking_finding"])
        self.assertEqual(result["summary"]["abilities_enabled"], 5)
        self.assertEqual(result["framework"], "eu-ai-act,iso42001,nist")


class TestBiometricArt14_5(unittest.TestCase):
    def test_biometric_one_authoritative_person_blocks(self):
        inputs = _base_inputs()
        inputs["system_description"]["biometric_identification_system"] = True
        inputs["assigned_oversight_personnel"] = [
            {
                "person_role": "Officer",
                "authority_level": "sole-authority",
                "training_evidence_ref": "docs/officer.md",
            },
        ]
        result = plugin.design_human_oversight(inputs)
        check = result["biometric_dual_assignment_check"]
        self.assertFalse(check["satisfied"])
        self.assertTrue(any("Article 14(5)" in w for w in result["warnings"]))

    def test_biometric_two_authoritative_persons_satisfied(self):
        inputs = _base_inputs()
        inputs["system_description"]["biometric_identification_system"] = True
        result = plugin.design_human_oversight(inputs)
        check = result["biometric_dual_assignment_check"]
        self.assertTrue(check["satisfied"])
        self.assertEqual(check["authoritative_personnel_count"], 2)


class TestModeValidation(unittest.TestCase):
    def test_fully_automated_unauthorised_high_risk_blocking(self):
        inputs = _base_inputs()
        inputs["oversight_design"]["mode"] = "fully-automated-unauthorised"
        result = plugin.design_human_oversight(inputs)
        self.assertTrue(result["mode_validation"]["blocking_finding"])
        self.assertTrue(any(
            "Fully-automated mode" in f
            for f in result["mode_validation"]["findings"]
        ))

    def test_non_high_risk_mode_on_the_loop_valid(self):
        inputs = _base_inputs()
        inputs["system_description"]["risk_tier"] = "limited-risk"
        inputs["oversight_design"]["mode"] = "human-on-the-loop"
        result = plugin.design_human_oversight(inputs)
        self.assertEqual(
            result["art_14_applicability"], "not-mandated-but-recommended"
        )
        self.assertFalse(result["mode_validation"]["blocking_finding"])


class TestAbilityCoverage(unittest.TestCase):
    def test_missing_intervene_or_stop_partial(self):
        inputs = _base_inputs()
        inputs["oversight_design"]["ability_coverage"]["intervene-or-stop"][
            "enabled"
        ] = False
        result = plugin.design_human_oversight(inputs)
        self.assertEqual(
            result["ability_coverage_assessment"]["status"], "partial-coverage"
        )
        self.assertTrue(any(
            "intervene-or-stop" in w for w in result["warnings"]
        ))


class TestOverrideControls(unittest.TestCase):
    def test_latency_above_threshold_high_risk_warns(self):
        inputs = _base_inputs()
        inputs["oversight_design"]["override_controls"][0][
            "activation_latency_seconds"
        ] = 60
        result = plugin.design_human_oversight(inputs)
        self.assertTrue(any("inadequate" in w for w in result["warnings"]))

    def test_stale_test_date_warns(self):
        inputs = _base_inputs()
        inputs["oversight_design"]["override_controls"][0][
            "tested_date"
        ] = _stale_iso()
        result = plugin.design_human_oversight(inputs)
        self.assertTrue(any(
            "not tested in the last 12 months" in w for w in result["warnings"]
        ))

    def test_no_override_controls_warns(self):
        inputs = _base_inputs()
        inputs["oversight_design"]["override_controls"] = []
        result = plugin.design_human_oversight(inputs)
        self.assertTrue(any(
            "no override_controls documented" in w for w in result["warnings"]
        ))


class TestOperatorTraining(unittest.TestCase):
    def test_low_completion_rate_warns(self):
        inputs = _base_inputs()
        inputs["oversight_design"]["operator_training"][
            "completion_rate_percent"
        ] = 60
        result = plugin.design_human_oversight(inputs)
        self.assertTrue(any(
            "below 80 percent" in w for w in result["warnings"]
        ))

    def test_no_annual_refresh_warns(self):
        inputs = _base_inputs()
        inputs["oversight_design"]["operator_training"][
            "annual_refresh"
        ] = False
        result = plugin.design_human_oversight(inputs)
        self.assertTrue(any(
            "Annual oversight training refresh" in w
            for w in result["warnings"]
        ))


class TestAutomationBias(unittest.TestCase):
    def test_zero_mitigations_warns(self):
        inputs = _base_inputs()
        inputs["oversight_design"]["automation_bias_mitigations"] = []
        result = plugin.design_human_oversight(inputs)
        self.assertTrue(any(
            "automation bias awareness measures not documented" in w
            for w in result["warnings"]
        ))


class TestValidationErrors(unittest.TestCase):
    def test_missing_system_description_raises(self):
        with self.assertRaises(ValueError):
            plugin.design_human_oversight({"oversight_design": {"mode": "human-in-the-loop"}})

    def test_missing_oversight_design_raises(self):
        with self.assertRaises(ValueError):
            plugin.design_human_oversight({"system_description": {
                "system_id": "x", "system_name": "x", "intended_use": "x",
                "risk_tier": "limited-risk",
            }})

    def test_invalid_mode_raises(self):
        inputs = _base_inputs()
        inputs["oversight_design"]["mode"] = "no-such-mode"
        with self.assertRaises(ValueError):
            plugin.design_human_oversight(inputs)

    def test_invalid_authority_level_raises(self):
        inputs = _base_inputs()
        inputs["assigned_oversight_personnel"][0]["authority_level"] = "tsar"
        with self.assertRaises(ValueError):
            plugin.design_human_oversight(inputs)


class TestCrosswalkEnrichment(unittest.TestCase):
    def test_default_true_includes_cross_framework_citations(self):
        inputs = _base_inputs()
        del inputs["enrich_with_crosswalk"]
        result = plugin.design_human_oversight(inputs)
        self.assertIn("cross_framework_citations", result)
        self.assertIsInstance(result["cross_framework_citations"], list)

    def test_false_omits_cross_framework_citations(self):
        inputs = _base_inputs()
        inputs["enrich_with_crosswalk"] = False
        result = plugin.design_human_oversight(inputs)
        self.assertNotIn("cross_framework_citations", result)

    def test_graceful_crosswalk_failure_keeps_design(self):
        inputs = _base_inputs()
        inputs["enrich_with_crosswalk"] = True

        original_loader = plugin._load_crosswalk_module

        def broken():
            raise ImportError("simulated load failure")

        plugin._load_crosswalk_module = broken
        try:
            result = plugin.design_human_oversight(inputs)
        finally:
            plugin._load_crosswalk_module = original_loader

        self.assertTrue(any(
            "Crosswalk enrichment skipped" in w for w in result["warnings"]
        ))
        self.assertEqual(result["agent_signature"], plugin.AGENT_SIGNATURE)


class TestCitationFormat(unittest.TestCase):
    def test_citations_match_style_md(self):
        result = plugin.design_human_oversight(_base_inputs())
        for c in result["citations"]:
            self.assertTrue(
                c.startswith((
                    "EU AI Act, Article",
                    "ISO/IEC 42001:2023, Annex A, Control",
                    "ISO/IEC 42001:2023, Clause",
                    "MANAGE ",
                    "GOVERN ",
                    "MEASURE ",
                    "MAP ",
                    "UK ATRS, Section",
                )),
                msg=f"Citation does not match STYLE.md prefix: {c!r}",
            )


class TestRendering(unittest.TestCase):
    def test_no_em_dash_no_emoji_no_hedging_in_output(self):
        result = plugin.design_human_oversight(_base_inputs())
        md = plugin.render_markdown(result)
        self.assertNotIn("\u2014", md)
        for hedge in ("may want to consider", "might be helpful", "could potentially"):
            self.assertNotIn(hedge, md.lower())

    def test_markdown_required_sections(self):
        result = plugin.design_human_oversight(_base_inputs())
        # Add biometric section by toggling.
        biometric_inputs = _base_inputs()
        biometric_inputs["system_description"]["biometric_identification_system"] = True
        biometric_md = plugin.render_markdown(
            plugin.design_human_oversight(biometric_inputs)
        )
        md = plugin.render_markdown(result)
        for section in (
            "## Applicability",
            "## Ability coverage",
            "## Override capability",
            "## Mode validation",
            "## Operator training",
            "## Automation bias",
            "## Oversight personnel",
            "## Warnings",
        ):
            self.assertIn(section, md)
        self.assertIn("## Biometric dual-assignment", biometric_md)

    def test_csv_row_count(self):
        result = plugin.design_human_oversight(_base_inputs())
        csv_text = plugin.render_csv(result)
        lines = [ln for ln in csv_text.strip().split("\n") if ln]
        # 1 header + 5 ability + 1 override + 2 personnel + 1 bias = 10
        self.assertEqual(len(lines), 10)


if __name__ == "__main__":
    unittest.main()
