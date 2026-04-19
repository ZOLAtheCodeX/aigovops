"""Tests for supplier-vendor-assessor plugin.

Pytest-compatible and standalone-runnable.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _base_vendor(**overrides) -> dict:
    v = {
        "vendor_name": "Acme Foundation Models Inc.",
        "vendor_type": "model-provider",
        "jurisdiction_of_establishment": "US-DE",
        "products_services": ["foundation-model-api", "fine-tuning-service"],
        "ai_systems_they_supply": ["SYS-001", "SYS-007"],
    }
    v.update(overrides)
    return v


def _base_contract(**overrides) -> dict:
    c = {
        "contract_id": "MSA-2026-ACME-001",
        "effective_date": "2026-01-01",
        "expiry_date": "2027-12-31",
        "auto_renew": True,
        "termination_notice_days": 60,
        "sla_summary": "99.5 percent monthly uptime",
        "audit_rights_included": True,
        "security_incident_notification_days": 10,
        "data_processing_agreement_included": True,
        "liability_cap": "12 months fees",
    }
    c.update(overrides)
    return c


def _base_inputs(**overrides) -> dict:
    i = {
        "vendor_description": _base_vendor(),
        "vendor_role": "model-provider",
        "organization_role": "deployer",
        "contract_summary": _base_contract(),
    }
    i.update(overrides)
    return i


class TestHappyPaths(unittest.TestCase):
    def test_happy_path_model_provider_has_eight_dimensions(self):
        result = plugin.assess_vendor(_base_inputs())
        self.assertIn("assessment_matrix", result)
        self.assertEqual(len(result["assessment_matrix"]), 8)
        self.assertEqual(result["agent_signature"], "supplier-vendor-assessor/0.1.0")
        self.assertEqual(result["framework"], "iso42001,eu-ai-act")

    def test_happy_path_bias_audit_service_has_independence_assessment(self):
        inputs = _base_inputs(
            vendor_role="bias-audit-service",
            vendor_description=_base_vendor(vendor_type="bias-audit-service"),
        )
        result = plugin.assess_vendor(inputs)
        self.assertIn("independence_assessment", result)
        ia = result["independence_assessment"]
        self.assertEqual(len(ia["criteria"]), 4)
        self.assertEqual(ia["status"], "requires-practitioner-confirmation")
        self.assertIn("NYC LL144 Final Rule, Section 5-300", result["citations"])

    def test_deployer_substantial_modification_triggers_art_25_1_c_warning(self):
        inputs = _base_inputs(
            deployer_modification_note=(
                "Deployer fine-tuned foundation model on proprietary medical records and "
                "redeployed for clinical triage."
            )
        )
        result = plugin.assess_vendor(inputs)
        assert any(
            "Art. 25(1)(c)" in w and "re-classify" in w for w in result["warnings"]
        ), result["warnings"]
        self.assertIn("EU AI Act, Article 25, Paragraph 1", result["citations"])


class TestValidation(unittest.TestCase):
    def test_missing_vendor_description_raises(self):
        inputs = _base_inputs()
        del inputs["vendor_description"]
        with self.assertRaises(ValueError):
            plugin.assess_vendor(inputs)

    def test_missing_vendor_role_raises(self):
        inputs = _base_inputs()
        del inputs["vendor_role"]
        with self.assertRaises(ValueError):
            plugin.assess_vendor(inputs)

    def test_missing_organization_role_raises(self):
        inputs = _base_inputs()
        del inputs["organization_role"]
        with self.assertRaises(ValueError):
            plugin.assess_vendor(inputs)

    def test_invalid_vendor_role_raises(self):
        inputs = _base_inputs(vendor_role="not-a-real-role")
        with self.assertRaises(ValueError):
            plugin.assess_vendor(inputs)

    def test_invalid_organization_role_raises(self):
        inputs = _base_inputs(organization_role="purchaser")
        with self.assertRaises(ValueError):
            plugin.assess_vendor(inputs)


class TestWarnings(unittest.TestCase):
    def test_empty_contract_summary_emits_warning(self):
        inputs = _base_inputs(contract_summary={})
        result = plugin.assess_vendor(inputs)
        self.assertTrue(
            any("contract_summary is empty" in w for w in result["warnings"]),
            result["warnings"],
        )

    def test_audit_rights_false_emits_warning(self):
        contract = _base_contract(audit_rights_included=False)
        inputs = _base_inputs(contract_summary=contract)
        result = plugin.assess_vendor(inputs)
        joined = " ".join(result["warnings"])
        self.assertIn("audit_rights_included is False", joined)
        self.assertIn("A.10.3", joined)

    def test_security_incident_notification_over_threshold_emits_warning(self):
        contract = _base_contract(security_incident_notification_days=30)
        inputs = _base_inputs(contract_summary=contract)
        result = plugin.assess_vendor(inputs)
        joined = " ".join(result["warnings"])
        self.assertIn("security_incident_notification_days is 30", joined)


class TestSupplyChain(unittest.TestCase):
    def test_supply_chain_graph_maps_two_sub_processors(self):
        inputs = _base_inputs(
            sub_processors=[
                {
                    "vendor_name": "InferenceHost LLC",
                    "vendor_type": "deployment-infrastructure",
                    "jurisdiction_of_establishment": "US-VA",
                    "products_services": ["gpu-inference"],
                    "ai_systems_they_supply": [],
                },
                {
                    "vendor_name": "LabelCo",
                    "vendor_type": "training-data-provider",
                    "jurisdiction_of_establishment": "PH",
                    "products_services": ["human-labeling"],
                    "ai_systems_they_supply": [],
                },
            ]
        )
        result = plugin.assess_vendor(inputs)
        self.assertIn("supply_chain_graph", result)
        scg = result["supply_chain_graph"]
        self.assertEqual(scg["organization"]["role"], "deployer")
        self.assertEqual(len(scg["tier_2_sub_processors"]), 2)
        names = [sp["vendor_name"] for sp in scg["tier_2_sub_processors"]]
        self.assertIn("InferenceHost LLC", names)
        self.assertIn("LabelCo", names)
        for sp in scg["tier_2_sub_processors"]:
            self.assertEqual(sp["tier_2_assessment"], "tier-2-assessment-pending")


class TestIndependenceDefaults(unittest.TestCase):
    def test_independence_defaults_true_for_bias_audit_service(self):
        inputs = _base_inputs(
            vendor_role="bias-audit-service",
            vendor_description=_base_vendor(vendor_type="bias-audit-service"),
        )
        result = plugin.assess_vendor(inputs)
        self.assertIn("independence_assessment", result)
        self.assertTrue(result["summary"]["independence_check_required"])

    def test_independence_defaults_false_for_model_provider(self):
        result = plugin.assess_vendor(_base_inputs())
        self.assertNotIn("independence_assessment", result)
        self.assertFalse(result["summary"]["independence_check_required"])


class TestCrosswalkEnrichment(unittest.TestCase):
    def test_crosswalk_enrichment_default_true_attaches_cross_framework_citations(self):
        result = plugin.assess_vendor(_base_inputs())
        self.assertIn("cross_framework_citations", result)
        # NIST GOVERN 6.1 is in the top-level citations always.
        self.assertIn("NIST GOVERN 6.1", result["citations"])

    def test_crosswalk_enrichment_false_omits_key(self):
        result = plugin.assess_vendor(_base_inputs(enrich_with_crosswalk=False))
        self.assertNotIn("cross_framework_citations", result)


class TestCitationFormat(unittest.TestCase):
    def test_citations_conform_to_style_md_prefixes(self):
        inputs = _base_inputs(
            vendor_role="bias-audit-service",
            vendor_description=_base_vendor(vendor_type="bias-audit-service"),
            deployer_modification_note="Retrained on regulated dataset.",
        )
        result = plugin.assess_vendor(inputs)
        allowed_prefixes = (
            "ISO/IEC 42001:2023, Annex A, Control A.",
            "ISO/IEC 42001:2023, Clause ",
            "EU AI Act, Article ",
            "NYC LL144",
            "NIST GOVERN ",
            "NIST MAP ",
            "NIST MEASURE ",
            "NIST MANAGE ",
        )
        for c in result["citations"]:
            self.assertTrue(
                any(c.startswith(p) for p in allowed_prefixes),
                f"Citation {c!r} does not match STYLE.md prefixes",
            )


class TestStyleHygiene(unittest.TestCase):
    def test_no_em_dash_in_rendered_markdown(self):
        result = plugin.assess_vendor(
            _base_inputs(
                vendor_role="bias-audit-service",
                vendor_description=_base_vendor(vendor_type="bias-audit-service"),
                sub_processors=[
                    {
                        "vendor_name": "SubOne",
                        "vendor_type": "monitoring-service",
                        "jurisdiction_of_establishment": "US",
                        "products_services": ["drift-detection"],
                        "ai_systems_they_supply": [],
                    }
                ],
            )
        )
        md = plugin.render_markdown(result)
        self.assertNotIn("\u2014", md)
        lower = md.lower()
        for phrase in (
            "may want to consider",
            "might be helpful to",
            "could potentially",
            "it is possible that",
        ):
            self.assertNotIn(phrase, lower)
        # No emojis: check a few common blocks.
        for ch in ("\U0001f600", "\U0001f44d", "\u2705", "\u274c"):
            self.assertNotIn(ch, md)


class TestRendering(unittest.TestCase):
    def test_markdown_has_required_sections(self):
        result = plugin.assess_vendor(
            _base_inputs(
                vendor_role="bias-audit-service",
                vendor_description=_base_vendor(vendor_type="bias-audit-service"),
                sub_processors=[
                    {
                        "vendor_name": "SubOne",
                        "vendor_type": "monitoring-service",
                        "jurisdiction_of_establishment": "US",
                        "products_services": ["drift-detection"],
                        "ai_systems_they_supply": [],
                    }
                ],
            )
        )
        md = plugin.render_markdown(result)
        for section in (
            "## Vendor overview",
            "## Role reconciliation",
            "## Assessment matrix",
            "## Independence check",
            "## Supply chain",
            "## Warnings",
        ):
            self.assertIn(section, md)

    def test_csv_row_count_equals_assessment_matrix_length(self):
        result = plugin.assess_vendor(_base_inputs())
        csv = plugin.render_csv(result)
        data_rows = [line for line in csv.splitlines() if line][1:]
        self.assertEqual(len(data_rows), len(result["assessment_matrix"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
