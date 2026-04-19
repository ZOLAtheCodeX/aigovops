"""Tests for gpai-obligations-tracker plugin.

Pytest-compatible and standalone-runnable.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

import plugin  # noqa: E402


def _base_model(**overrides) -> dict:
    m = {
        "model_name": "ExampleLM-Base",
        "model_family": "ExampleLM",
        "parameter_count": "7B",
        "training_compute_flops": 5e23,
        "training_data_types": ["text-web", "text-books"],
        "training_data_jurisdictions": ["EU", "USA"],
        "modality": "text",
        "release_date": "2026-03-01",
        "model_version": "1.0",
    }
    m.update(overrides)
    return m


def _base_inputs(**overrides) -> dict:
    i = {
        "model_description": _base_model(),
        "provider_role": "eu-established-provider",
        "technical_documentation_ref": "/docs/annex-xi.md",
        "downstream_integrator_docs_ref": "/docs/integrator-guide.md",
        "copyright_policy_ref": "/policies/copyright.md",
        "training_data_summary_ref": "/docs/training-data-summary.md",
    }
    i.update(overrides)
    return i


def _systemic_risk_artifacts(**overrides) -> dict:
    sr = {
        "model_evaluation_ref": "/eval/state-of-art-eval.json",
        "adversarial_testing_ref": "/eval/adversarial-report.md",
        "systemic_risk_assessment_ref": "/risk/systemic-risk-assessment.md",
        "cybersecurity_measures_ref": "/security/measures.md",
        "serious_incidents_log_ref": "/ops/serious-incidents.log",
    }
    sr.update(overrides)
    return sr


class TestHappyPath(unittest.TestCase):
    def test_eu_established_below_threshold_full_art_53(self):
        result = plugin.assess_gpai_obligations(_base_inputs())
        self.assertEqual(result["systemic_risk_status"], "not-systemic-risk")
        self.assertEqual(result["art_54_status"], "not-applicable")
        for o in result["art_53_obligations"]:
            self.assertEqual(o["status"], "present", o)
        self.assertNotIn("art_55_obligations", result)
        self.assertEqual(result["agent_signature"], "gpai-obligations-tracker/0.1.0")
        self.assertEqual(result["framework"], "eu-ai-act")

    def test_designated_systemic_risk_full_compliance(self):
        inputs = _base_inputs(
            designated_systemic_risk=True,
            systemic_risk_artifacts=_systemic_risk_artifacts(),
            code_of_practice_status="signed-full",
        )
        result = plugin.assess_gpai_obligations(inputs)
        self.assertEqual(result["systemic_risk_status"], "designated-systemic-risk")
        self.assertIn("art_55_obligations", result)
        statuses = [o["status"] for o in result["art_55_obligations"]
                    if o["obligation"] != "Article 55(2)"]
        for s in statuses:
            self.assertEqual(s, "present")
        # Code of practice produces a presumption note.
        cop_entry = next(o for o in result["art_55_obligations"]
                         if o["obligation"] == "Article 55(2)")
        self.assertIn("presumption", cop_entry["note"].lower())


class TestSystemicRiskClassification(unittest.TestCase):
    def test_presumed_systemic_risk_at_or_above_threshold(self):
        inputs = _base_inputs(
            model_description=_base_model(training_compute_flops=2e25),
        )
        result = plugin.assess_gpai_obligations(inputs)
        self.assertEqual(result["systemic_risk_status"], "presumed-systemic-risk")
        self.assertIn("EU AI Act, Article 51, Paragraph 1, Point (a)", result["citations"])

    def test_unknown_compute_returns_requires_assessment(self):
        inputs = _base_inputs(
            model_description=_base_model(training_compute_flops="unknown"),
        )
        result = plugin.assess_gpai_obligations(inputs)
        self.assertEqual(result["systemic_risk_status"], "requires-assessment")
        joined = " ".join(result["warnings"])
        self.assertIn("training_compute_flops unknown", joined)


class TestArt54Representative(unittest.TestCase):
    def test_non_eu_provider_with_rep_satisfied(self):
        inputs = _base_inputs(
            provider_role="non-eu-provider-with-representative",
            authorised_representative={
                "name": "EU Rep GmbH",
                "eu_member_state": "DE",
                "contact": "rep@example.eu",
            },
        )
        result = plugin.assess_gpai_obligations(inputs)
        self.assertEqual(result["art_54_status"], "satisfied")

    def test_non_eu_provider_without_rep_non_compliant(self):
        inputs = _base_inputs(
            provider_role="non-eu-provider-without-representative",
        )
        result = plugin.assess_gpai_obligations(inputs)
        self.assertEqual(result["art_54_status"], "non-compliant")
        joined = " ".join(result["warnings"])
        self.assertIn("Non-EU GPAI provider must designate EU authorised representative", joined)


class TestDownstreamIntegrator(unittest.TestCase):
    def test_downstream_integrator_posture_emitted_when_base_model_ref_set(self):
        inputs = _base_inputs(
            provider_role="downstream-integrator",
            model_description=_base_model(base_model_ref="ExampleLM-Foundation/v3"),
        )
        result = plugin.assess_gpai_obligations(inputs)
        self.assertIn("downstream_integrator_posture", result)
        dp = result["downstream_integrator_posture"]
        self.assertEqual(dp["base_model_ref"], "ExampleLM-Foundation/v3")
        self.assertTrue(dp["received_art_53_1_b_docs"])
        self.assertEqual(len(dp["responsibilities"]), 3)

    def test_downstream_integrator_not_assigned_art_55(self):
        inputs = _base_inputs(
            provider_role="downstream-integrator",
            model_description=_base_model(
                base_model_ref="ExampleLM-Foundation/v3",
                training_compute_flops=2e25,
            ),
        )
        result = plugin.assess_gpai_obligations(inputs)
        self.assertEqual(result["systemic_risk_status"], "presumed-systemic-risk")
        self.assertNotIn("art_55_obligations", result)
        joined = " ".join(result["warnings"])
        self.assertIn("downstream-integrator", joined.lower())


class TestArt53Warnings(unittest.TestCase):
    def test_missing_copyright_policy_emits_warning(self):
        inputs = _base_inputs()
        del inputs["copyright_policy_ref"]
        result = plugin.assess_gpai_obligations(inputs)
        joined = " ".join(result["warnings"])
        self.assertIn("Article 53(1)(c)", joined)
        # The relevant obligation row reflects missing-warning.
        c_entry = next(
            o for o in result["art_53_obligations"]
            if o["obligation"] == "Article 53(1)(c)"
        )
        self.assertEqual(c_entry["status"], "missing-warning")


class TestArt55Warnings(unittest.TestCase):
    def test_missing_serious_incidents_log_emits_critical_warning(self):
        sr = _systemic_risk_artifacts()
        del sr["serious_incidents_log_ref"]
        inputs = _base_inputs(
            designated_systemic_risk=True,
            systemic_risk_artifacts=sr,
        )
        result = plugin.assess_gpai_obligations(inputs)
        joined = " ".join(result["warnings"])
        self.assertIn("Article 55(1)(c)", joined)
        self.assertIn("incident-reporting plugin", joined)


class TestCodeOfPractice(unittest.TestCase):
    def test_signed_full_creates_presumption_note(self):
        inputs = _base_inputs(
            designated_systemic_risk=True,
            systemic_risk_artifacts=_systemic_risk_artifacts(),
            code_of_practice_status="signed-full",
        )
        result = plugin.assess_gpai_obligations(inputs)
        cop_entry = next(o for o in result["art_55_obligations"]
                         if o["obligation"] == "Article 55(2)")
        self.assertEqual(cop_entry["status"], "signed-full")
        self.assertIn("presumption", cop_entry["note"].lower())

    def test_not_applicable_path(self):
        inputs = _base_inputs(
            designated_systemic_risk=True,
            systemic_risk_artifacts=_systemic_risk_artifacts(),
            code_of_practice_status="not-applicable",
        )
        result = plugin.assess_gpai_obligations(inputs)
        cop_entry = next(o for o in result["art_55_obligations"]
                         if o["obligation"] == "Article 55(2)")
        self.assertEqual(cop_entry["status"], "not-applicable")
        self.assertIn("not applicable", cop_entry["note"].lower())


class TestValidation(unittest.TestCase):
    def test_missing_model_description_raises(self):
        inputs = _base_inputs()
        del inputs["model_description"]
        with self.assertRaises(ValueError):
            plugin.assess_gpai_obligations(inputs)

    def test_missing_provider_role_raises(self):
        inputs = _base_inputs()
        del inputs["provider_role"]
        with self.assertRaises(ValueError):
            plugin.assess_gpai_obligations(inputs)

    def test_invalid_provider_role_raises(self):
        inputs = _base_inputs(provider_role="foo")
        with self.assertRaises(ValueError):
            plugin.assess_gpai_obligations(inputs)


class TestSystemicRiskAbsentForNotSystemicRisk(unittest.TestCase):
    def test_art_55_absent_when_not_systemic_risk(self):
        result = plugin.assess_gpai_obligations(_base_inputs())
        self.assertNotIn("art_55_obligations", result)


class TestCrosswalkEnrichment(unittest.TestCase):
    def test_enrichment_default_true_attaches_cross_framework_citations(self):
        result = plugin.assess_gpai_obligations(_base_inputs())
        self.assertIn("cross_framework_citations", result)
        # cross_framework_citations is a list (possibly empty if data lookup
        # finds no matches; we assert presence of the key, not minimum count).
        self.assertIsInstance(result["cross_framework_citations"], list)

    def test_enrichment_false_omits_key(self):
        result = plugin.assess_gpai_obligations(
            _base_inputs(enrich_with_crosswalk=False)
        )
        self.assertNotIn("cross_framework_citations", result)

    def test_crosswalk_failure_does_not_break_assessment(self):
        # Substitute a module loader that raises, then call the helper directly.
        original_loader = plugin._load_crosswalk_module

        def _bad_loader():
            raise RuntimeError("simulated crosswalk failure")

        plugin._load_crosswalk_module = _bad_loader  # type: ignore[assignment]
        try:
            citations, warnings = plugin._enrich_crosswalk(systemic_risk=False)
            self.assertEqual(citations, [])
            self.assertTrue(any("Crosswalk enrichment skipped" in w for w in warnings))
        finally:
            plugin._load_crosswalk_module = original_loader  # type: ignore[assignment]


class TestCitationFormat(unittest.TestCase):
    def test_citations_conform_to_style_md_prefixes(self):
        inputs = _base_inputs(
            provider_role="non-eu-provider-with-representative",
            authorised_representative={
                "name": "EU Rep GmbH",
                "eu_member_state": "DE",
                "contact": "rep@example.eu",
            },
            designated_systemic_risk=True,
            systemic_risk_artifacts=_systemic_risk_artifacts(),
            code_of_practice_status="signed-full",
        )
        result = plugin.assess_gpai_obligations(inputs)
        allowed_prefixes = (
            "EU AI Act, Article ",
            "EU AI Act, Annex ",
        )
        for c in result["citations"]:
            self.assertTrue(
                any(c.startswith(p) for p in allowed_prefixes),
                f"Citation {c!r} does not match STYLE.md prefixes",
            )

    def test_paragraph_point_citation_format_present(self):
        result = plugin.assess_gpai_obligations(_base_inputs())
        # Article 53(1)(a..d) citations should follow "Article 53, Paragraph 1, Point (X)".
        pattern = re.compile(
            r"^EU AI Act, Article 53, Paragraph 1, Point \([abcd]\)$"
        )
        for o in result["art_53_obligations"]:
            self.assertRegex(o["citation"], pattern)


class TestStyleHygiene(unittest.TestCase):
    def test_no_em_dash_or_hedging_in_rendered_markdown(self):
        inputs = _base_inputs(
            designated_systemic_risk=True,
            systemic_risk_artifacts=_systemic_risk_artifacts(),
            code_of_practice_status="signed-full",
        )
        result = plugin.assess_gpai_obligations(inputs)
        md = plugin.render_markdown(result)
        self.assertNotIn("\u2014", md)
        lower = md.lower()
        for phrase in (
            "may want to consider",
            "might be helpful to",
            "could potentially",
            "it is possible that",
            "you might find",
        ):
            self.assertNotIn(phrase, lower)
        for ch in ("\U0001f600", "\U0001f44d", "\u2705", "\u274c"):
            self.assertNotIn(ch, md)


class TestRendering(unittest.TestCase):
    def test_markdown_has_required_sections_systemic_risk(self):
        inputs = _base_inputs(
            provider_role="downstream-integrator",
            model_description=_base_model(base_model_ref="Upstream/v1"),
            designated_systemic_risk=True,
            systemic_risk_artifacts=_systemic_risk_artifacts(),
        )
        result = plugin.assess_gpai_obligations(inputs)
        md = plugin.render_markdown(result)
        for section in (
            "## Systemic-risk classification",
            "## Article 53 obligations",
            "## Article 54 status",
            "## Downstream integrator posture",
            "## Warnings",
        ):
            self.assertIn(section, md)

    def test_markdown_has_art_55_section_for_systemic_risk_provider(self):
        inputs = _base_inputs(
            designated_systemic_risk=True,
            systemic_risk_artifacts=_systemic_risk_artifacts(),
        )
        result = plugin.assess_gpai_obligations(inputs)
        md = plugin.render_markdown(result)
        self.assertIn("## Article 55 obligations", md)

    def test_csv_row_count_matches_obligation_count(self):
        inputs = _base_inputs(
            designated_systemic_risk=True,
            systemic_risk_artifacts=_systemic_risk_artifacts(),
            code_of_practice_status="signed-full",
        )
        result = plugin.assess_gpai_obligations(inputs)
        csv_text = plugin.render_csv(result)
        rows = [line for line in csv_text.splitlines() if line]
        # Header + Article 53 rows (4) + Article 55 rows (5: a, b, c, d, 2).
        self.assertEqual(len(rows), 1 + 4 + 5)


class TestAllArt55ArtifactsMissing(unittest.TestCase):
    def test_all_warnings_populated_when_zero_artifacts(self):
        inputs = _base_inputs(
            designated_systemic_risk=True,
        )
        result = plugin.assess_gpai_obligations(inputs)
        joined = " ".join(result["warnings"])
        # All four 55(1) obligations should be flagged.
        self.assertIn("Article 55(1)(a)", joined)
        self.assertIn("Article 55(1)(b)", joined)
        self.assertIn("Article 55(1)(c)", joined)
        self.assertIn("Article 55(1)(d)", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
