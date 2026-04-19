"""Tests for genai-risk-register plugin.

Pytest-compatible and standalone-runnable.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

import plugin  # noqa: E402


def _system_description(**overrides) -> dict:
    sd = {
        "system_id": "genai-001",
        "model_type": "LLM",
        "modality": "text",
        "is_generative": True,
        "training_data_scope": "public-web + curated",
        "deployment_context": "customer-facing chatbot",
        "jurisdiction": ["usa-federal"],
        "base_model_ref": "ExampleLM-7B",
    }
    sd.update(overrides)
    return sd


def _risk_eval(risk_id: str, **overrides) -> dict:
    r = {
        "risk_id": risk_id,
        "likelihood": "unlikely",
        "impact": "moderate",
        "inherent_score": 6,
        "existing_mitigations": [
            {"name": "input-filter", "description": "prompt filter", "evidence_ref": "/ops/filter.md"},
        ],
        "mitigation_status": "implemented",
        "residual_likelihood": "rare",
        "residual_impact": "minor",
        "residual_score": 2,
        "owner_role": "AI Safety Lead",
        "review_date": "2026-04-18",
        "notes": "Standard evaluation.",
    }
    r.update(overrides)
    return r


def _all_twelve_evaluations() -> list[dict]:
    return [_risk_eval(rid) for rid in plugin.GENAI_RISKS]


def _base_inputs(**overrides) -> dict:
    i = {
        "system_description": _system_description(),
        "risk_evaluations": _all_twelve_evaluations(),
        "enrich_with_crosswalk": False,
    }
    i.update(overrides)
    return i


class TestHappyPath(unittest.TestCase):
    def test_all_twelve_risks_evaluated(self):
        result = plugin.generate_genai_risk_register(_base_inputs())
        self.assertEqual(result["coverage_assessment"]["evaluated_count"], 12)
        self.assertEqual(result["coverage_assessment"]["missing_count"], 0)
        self.assertEqual(result["agent_signature"], "genai-risk-register/0.1.0")
        self.assertEqual(result["framework"], "nist,eu-ai-act,usa-ca")
        # No residual flags when residual_score stays at 2.
        self.assertEqual(result["summary"]["critical_flag_count"], 0)
        # Coverage warnings absent.
        coverage_warnings = [w for w in result["warnings"] if "not evaluated" in w]
        self.assertEqual(coverage_warnings, [])


class TestCoverage(unittest.TestCase):
    def test_missing_confabulation_warns(self):
        evals = [e for e in _all_twelve_evaluations() if e["risk_id"] != "confabulation"]
        result = plugin.generate_genai_risk_register(_base_inputs(risk_evaluations=evals))
        self.assertEqual(result["coverage_assessment"]["missing_count"], 1)
        self.assertIn("confabulation", result["coverage_assessment"]["missing_risk_ids"])
        self.assertTrue(
            any("'confabulation'" in w and "not evaluated" in w for w in result["warnings"]),
            msg=f"warnings: {result['warnings']}",
        )

    def test_not_applicable_with_rationale_accepted(self):
        evals = [e for e in _all_twelve_evaluations() if e["risk_id"] != "cbrn-information-capabilities"]
        result = plugin.generate_genai_risk_register(_base_inputs(
            risk_evaluations=evals,
            risks_not_applicable=[{
                "risk_id": "cbrn-information-capabilities",
                "rationale": "Customer-service chatbot restricted to order status; no technical uplift vector.",
            }],
        ))
        self.assertEqual(result["coverage_assessment"]["missing_count"], 0)
        self.assertEqual(result["coverage_assessment"]["not_applicable_count"], 1)
        for w in result["warnings"]:
            self.assertNotIn("'cbrn-information-capabilities'", w)

    def test_not_applicable_without_rationale_warns(self):
        evals = [e for e in _all_twelve_evaluations() if e["risk_id"] != "cbrn-information-capabilities"]
        result = plugin.generate_genai_risk_register(_base_inputs(
            risk_evaluations=evals,
            risks_not_applicable=[{"risk_id": "cbrn-information-capabilities", "rationale": ""}],
        ))
        self.assertTrue(
            any("not-applicable without rationale" in w for w in result["warnings"]),
            msg=f"warnings: {result['warnings']}",
        )


class TestIsGenerativeGuard(unittest.TestCase):
    def test_non_generative_raises(self):
        bad = _base_inputs()
        bad["system_description"]["is_generative"] = False
        with self.assertRaises(ValueError) as cm:
            plugin.generate_genai_risk_register(bad)
        self.assertIn("generative", str(cm.exception))

    def test_missing_is_generative_raises(self):
        bad = _base_inputs()
        bad["system_description"].pop("is_generative")
        with self.assertRaises(ValueError):
            plugin.generate_genai_risk_register(bad)


class TestResidualLogic(unittest.TestCase):
    def test_residual_exceeds_inherent_warns(self):
        evals = _all_twelve_evaluations()
        evals[0] = _risk_eval("cbrn-information-capabilities",
                              inherent_score=5, residual_score=8,
                              mitigation_status="partial")
        result = plugin.generate_genai_risk_register(_base_inputs(risk_evaluations=evals))
        self.assertTrue(
            any("exceeds inherent_score" in w for w in result["warnings"]),
            msg=f"warnings: {result['warnings']}",
        )

    def test_implemented_with_equal_scores_warns(self):
        evals = _all_twelve_evaluations()
        evals[0] = _risk_eval("cbrn-information-capabilities",
                              inherent_score=9, residual_score=9,
                              mitigation_status="implemented")
        result = plugin.generate_genai_risk_register(_base_inputs(risk_evaluations=evals))
        self.assertTrue(
            any("implemented" in w and "residual_score equals inherent_score" in w
                for w in result["warnings"]),
            msg=f"warnings: {result['warnings']}",
        )


class TestHighResidualFlagging(unittest.TestCase):
    def test_residual_18_flags_critical(self):
        evals = _all_twelve_evaluations()
        evals[0] = _risk_eval("cbrn-information-capabilities",
                              likelihood="likely", impact="catastrophic",
                              inherent_score=20,
                              residual_likelihood="likely", residual_impact="catastrophic",
                              residual_score=18,
                              mitigation_status="partial")
        result = plugin.generate_genai_risk_register(_base_inputs(risk_evaluations=evals))
        self.assertEqual(len(result["residual_risk_flags"]), 1)
        flag = result["residual_risk_flags"][0]
        self.assertEqual(flag["severity"], "critical")
        self.assertIn("incident-reporting", flag["escalation"])
        self.assertIn("management-review", flag["escalation"])
        self.assertTrue(any("CRITICAL" in w for w in result["warnings"]))


class TestJurisdictionCrossReferences(unittest.TestCase):
    def test_eu_info_integrity_art_50_citations(self):
        sd = _system_description(jurisdiction=["eu"])
        result = plugin.generate_genai_risk_register(_base_inputs(system_description=sd))
        info_row = next(r for r in result["risk_evaluations_normalized"]
                        if r["risk_id"] == "information-integrity")
        self.assertIn("EU AI Act, Article 50, Paragraph 2", info_row["citations"])
        self.assertIn("EU AI Act, Article 50, Paragraph 4", info_row["citations"])

    def test_usa_ca_info_integrity_sb_942(self):
        sd = _system_description(jurisdiction=["usa-ca"])
        result = plugin.generate_genai_risk_register(_base_inputs(system_description=sd))
        info_row = next(r for r in result["risk_evaluations_normalized"]
                        if r["risk_id"] == "information-integrity")
        self.assertIn("Cal. Bus. & Prof. Code Section 22757", info_row["citations"])

    def test_usa_ca_data_privacy_ab_1008_and_ab_2013(self):
        sd = _system_description(jurisdiction=["usa-ca"])
        result = plugin.generate_genai_risk_register(_base_inputs(system_description=sd))
        dp_row = next(r for r in result["risk_evaluations_normalized"]
                      if r["risk_id"] == "data-privacy")
        self.assertIn("Cal. Civ. Code Section 1798.140(v)", dp_row["citations"])
        self.assertIn("California AB 2013, Section 1", dp_row["citations"])

    def test_eu_with_gpai_ref_systemic_risk_art_55_citations(self):
        sd = _system_description(jurisdiction=["eu"])
        result = plugin.generate_genai_risk_register(_base_inputs(
            system_description=sd,
            cross_reference_refs={"gpai_obligations_ref": "/artifacts/gpai.json"},
        ))
        sec_row = next(r for r in result["risk_evaluations_normalized"]
                       if r["risk_id"] == "information-security")
        self.assertIn("EU AI Act, Article 55, Paragraph 1, Point (a)", sec_row["citations"])
        vc_row = next(r for r in result["risk_evaluations_normalized"]
                      if r["risk_id"] == "value-chain-component-integration")
        self.assertIn("EU AI Act, Article 55, Paragraph 1, Point (d)", vc_row["citations"])


class TestNistSubcategoryCoverage(unittest.TestCase):
    def test_per_risk_nist_coverage_cbrn(self):
        result = plugin.generate_genai_risk_register(_base_inputs())
        coverage = result["per_risk_nist_coverage"]
        self.assertEqual(
            list(coverage["cbrn-information-capabilities"]),
            ["GOVERN 1.1", "MAP 1.1", "MEASURE 2.6"],
        )

    def test_per_risk_nist_coverage_confabulation_and_security(self):
        result = plugin.generate_genai_risk_register(_base_inputs())
        coverage = result["per_risk_nist_coverage"]
        self.assertEqual(list(coverage["confabulation"]), ["MEASURE 2.5", "MEASURE 2.8"])
        self.assertEqual(list(coverage["information-security"]), ["MEASURE 2.7"])


class TestVersionDiff(unittest.TestCase):
    def test_version_diff_added_closed_changed(self):
        previous_rows = [
            {"risk_id": "cbrn-information-capabilities", "inherent_score": 9, "residual_score": 4},
            {"risk_id": "environmental-impacts", "inherent_score": 3, "residual_score": 3},
        ]
        result = plugin.generate_genai_risk_register(_base_inputs(
            previous_register_ref={"risk_evaluations_normalized": previous_rows},
        ))
        diff = result["version_diff"]
        # 12 current risks; 10 are "added" (previously had only 2 of them).
        self.assertIn("confabulation", diff["added"])
        self.assertNotIn("cbrn-information-capabilities", diff["added"])
        # cbrn score changed from (9, 4) to (6, 2).
        changed_ids = {c["risk_id"] for c in diff["changed"]}
        self.assertIn("cbrn-information-capabilities", changed_ids)


class TestValidationErrors(unittest.TestCase):
    def test_missing_system_description(self):
        with self.assertRaises(ValueError):
            plugin.generate_genai_risk_register({"risk_evaluations": []})

    def test_missing_risk_evaluations(self):
        with self.assertRaises(ValueError):
            plugin.generate_genai_risk_register({"system_description": _system_description()})

    def test_invalid_risk_id(self):
        with self.assertRaises(ValueError) as cm:
            plugin.generate_genai_risk_register(_base_inputs(
                risk_evaluations=[_risk_eval("not-a-real-risk")],
            ))
        self.assertIn("risk_id", str(cm.exception))

    def test_invalid_mitigation_status(self):
        bad = _risk_eval("confabulation", mitigation_status="totally-fixed")
        with self.assertRaises(ValueError):
            plugin.generate_genai_risk_register(_base_inputs(risk_evaluations=[bad]))

    def test_invalid_likelihood_enum(self):
        bad = _risk_eval("confabulation", likelihood="maybe")
        with self.assertRaises(ValueError):
            plugin.generate_genai_risk_register(_base_inputs(risk_evaluations=[bad]))


class TestCrosswalkEnrichment(unittest.TestCase):
    def test_crosswalk_default_enabled(self):
        result = plugin.generate_genai_risk_register({
            "system_description": _system_description(),
            "risk_evaluations": _all_twelve_evaluations(),
        })
        self.assertIn("cross_framework_citations", result)
        self.assertIsInstance(result["cross_framework_citations"], list)

    def test_crosswalk_disabled(self):
        result = plugin.generate_genai_risk_register(_base_inputs(enrich_with_crosswalk=False))
        self.assertNotIn("cross_framework_citations", result)

    def test_crosswalk_graceful_failure(self):
        # Point the loader at a non-existent crosswalk dir; the helper should
        # return an empty list and a warning rather than raising.
        orig = plugin._CROSSWALK_DIR
        try:
            plugin._CROSSWALK_DIR = Path("/nonexistent/crosswalk/dir")
            rows = [{"risk_id": "confabulation", "nist_subcategory_refs": ["MEASURE 2.5"]}]
            citations, warnings = plugin._enrich_crosswalk(rows)
            self.assertEqual(citations, [])
            self.assertTrue(warnings)
            self.assertIn("Crosswalk enrichment skipped", warnings[0])
        finally:
            plugin._CROSSWALK_DIR = orig


class TestCitationFormat(unittest.TestCase):
    def test_citation_prefixes(self):
        sd = _system_description(jurisdiction=["eu", "usa-ca"])
        result = plugin.generate_genai_risk_register(_base_inputs(
            system_description=sd,
            cross_reference_refs={"gpai_obligations_ref": "/artifacts/gpai.json"},
        ))
        allowed_prefixes = (
            "NIST AI 600-1, ",
            "NIST AI RMF, ",
            "EU AI Act, Article ",
            "Cal. Bus. & Prof. Code Section ",
            "California AB 2013, Section ",
            "Cal. Civ. Code Section ",
        )
        for c in result["citations"]:
            self.assertTrue(
                c.startswith(allowed_prefixes),
                msg=f"citation {c!r} does not start with any allowed prefix",
            )


class TestNoEmDashOrEmoji(unittest.TestCase):
    def test_rendered_output_has_no_em_dash(self):
        result = plugin.generate_genai_risk_register(_base_inputs())
        md = plugin.render_markdown(result)
        csv_text = plugin.render_csv(result)
        self.assertNotIn("\u2014", md)
        self.assertNotIn("\u2014", csv_text)

    def test_rendered_output_has_no_hedging(self):
        result = plugin.generate_genai_risk_register(_base_inputs())
        md = plugin.render_markdown(result).lower()
        for phrase in ("may want to consider", "might be helpful", "could potentially"):
            self.assertNotIn(phrase, md)


class TestRendering(unittest.TestCase):
    def test_markdown_has_required_sections(self):
        result = plugin.generate_genai_risk_register(_base_inputs())
        md = plugin.render_markdown(result)
        for section in (
            "# GenAI Risk Register",
            "## Coverage assessment",
            "## Per-risk evaluations",
            "## Jurisdiction cross-references",
            "## Residual risk flags",
            "## Warnings",
            "## Summary",
        ):
            self.assertIn(section, md, msg=f"missing section {section!r}")

    def test_markdown_version_diff_conditional(self):
        result = plugin.generate_genai_risk_register(_base_inputs(
            previous_register_ref={"risk_evaluations_normalized": []},
        ))
        md = plugin.render_markdown(result)
        self.assertIn("## Version diff", md)

    def test_csv_row_count_matches(self):
        result = plugin.generate_genai_risk_register(_base_inputs())
        csv_text = plugin.render_csv(result)
        lines = [ln for ln in csv_text.splitlines() if ln.strip()]
        # Header + one row per evaluated risk.
        self.assertEqual(len(lines) - 1, len(result["risk_evaluations_normalized"]))
        self.assertTrue(lines[0].startswith("risk_id,"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
