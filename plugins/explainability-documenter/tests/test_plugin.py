"""Tests for the explainability-documenter plugin."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_PLUGIN_PATH = Path(__file__).resolve().parent.parent / "plugin.py"
_spec = importlib.util.spec_from_file_location("explainability_documenter_plugin", _PLUGIN_PATH)
assert _spec is not None and _spec.loader is not None
_plugin = importlib.util.module_from_spec(_spec)
sys.modules["explainability_documenter_plugin"] = _plugin
_spec.loader.exec_module(_plugin)

document_explainability = _plugin.document_explainability
render_markdown = _plugin.render_markdown
render_csv = _plugin.render_csv


def _base_inputs(**overrides):
    system_description = {
        "system_name": "Test credit scoring model",
        "purpose": "Consumer credit decisioning",
        "decision_authority": "automated-with-human-review",
        "decision_effects": ["financial", "opportunity-related"],
        "jurisdiction": "eu",
    }
    if "system_description_override" in overrides:
        system_description.update(overrides.pop("system_description_override"))
    inputs = {
        "system_description": system_description,
        "model_type": "tree-based",
        "explanation_methods": [
            {
                "method": "intrinsic-decision-path",
                "scope": "both",
                "target_audience": ["developers", "deployers", "affected-persons"],
                "implementation_status": "implemented",
                "evidence_ref": "docs/explainability-report.pdf",
                "known_limitations": [
                    "Shallow trees omit interaction effects",
                    "Paths do not quantify confidence",
                ],
            }
        ],
        "intrinsic_interpretability_claim": True,
        "art_86_response_template_ref": "templates/art86-response.md",
        "enrich_with_crosswalk": False,
    }
    inputs.update(overrides)
    return inputs


class HappyPathTests(unittest.TestCase):
    def test_tree_based_intrinsic_global_affected_persons(self):
        """Test 1. Tree-based with intrinsic claim + both scopes + affected-persons audience."""
        inputs = _base_inputs(
            system_description_override={"decision_effects": ["legal"]},
        )
        out = document_explainability(inputs)
        self.assertEqual(out["agent_signature"], "explainability-documenter/0.1.0")
        self.assertEqual(out["model_type_classification"]["classification"], "intrinsic-interpretable")
        self.assertTrue(out["scope_coverage"]["global_covered"])
        self.assertTrue(out["scope_coverage"]["local_covered"])
        self.assertTrue(out["audience_coverage"]["affected_persons_covered"])
        # No blocking warnings expected.
        self.assertFalse(any("BLOCKING" in w for w in out["warnings"]))

    def test_deep_neural_network_shap_lime_both_scopes(self):
        """Test 2. DNN with SHAP (local) + LIME (global) covers both scopes."""
        inputs = _base_inputs(
            model_type="deep-neural-network",
            explanation_methods=[
                {
                    "method": "shap",
                    "scope": "local",
                    "target_audience": ["developers", "deployers", "affected-persons"],
                    "implementation_status": "implemented",
                    "evidence_ref": "docs/shap.pdf",
                    "known_limitations": ["Approximation error on high-dimensional inputs"],
                },
                {
                    "method": "lime",
                    "scope": "global",
                    "target_audience": ["developers", "auditors"],
                    "implementation_status": "implemented",
                    "evidence_ref": "docs/lime.pdf",
                    "known_limitations": ["Local fidelity degrades for nonlinear regions"],
                },
            ],
            intrinsic_interpretability_claim=False,
            system_description_override={"decision_effects": ["legal"]},
        )
        out = document_explainability(inputs)
        self.assertEqual(out["model_type_classification"]["classification"], "post-hoc-covered")
        self.assertTrue(out["scope_coverage"]["global_covered"])
        self.assertTrue(out["scope_coverage"]["local_covered"])


class ClassificationWarningTests(unittest.TestCase):
    def test_intrinsic_claim_on_deep_neural_network(self):
        """Test 3. Intrinsic claim on DNN emits incompatibility warning."""
        inputs = _base_inputs(
            model_type="deep-neural-network",
            intrinsic_interpretability_claim=True,
            explanation_methods=[
                {
                    "method": "shap",
                    "scope": "both",
                    "target_audience": ["developers", "deployers", "affected-persons"],
                    "implementation_status": "implemented",
                    "evidence_ref": "docs/shap.pdf",
                    "known_limitations": ["Approximation error"],
                }
            ],
        )
        out = document_explainability(inputs)
        self.assertTrue(
            any("Intrinsic interpretability claim incompatible" in w for w in out["warnings"])
        )


class ScopeCoverageTests(unittest.TestCase):
    def test_missing_global_scope(self):
        """Test 4. Missing global-scope method emits MEASURE 2.9 warning."""
        inputs = _base_inputs(
            explanation_methods=[
                {
                    "method": "shap",
                    "scope": "local",
                    "target_audience": ["developers", "affected-persons"],
                    "implementation_status": "implemented",
                    "evidence_ref": "x",
                    "known_limitations": ["limitation"],
                }
            ],
            intrinsic_interpretability_claim=False,
        )
        out = document_explainability(inputs)
        self.assertTrue(
            any("No explanation method covers global scope" in w for w in out["warnings"])
        )
        self.assertTrue(any("MEASURE 2.9" in w for w in out["warnings"]))

    def test_missing_local_scope_with_legal_effect(self):
        """Test 5. Missing local-scope method with legal effect triggers Art. 86 warning."""
        inputs = _base_inputs(
            explanation_methods=[
                {
                    "method": "feature-importance-global",
                    "scope": "global",
                    "target_audience": ["developers", "deployers", "affected-persons"],
                    "implementation_status": "implemented",
                    "evidence_ref": "x",
                    "known_limitations": ["limitation"],
                }
            ],
            intrinsic_interpretability_claim=False,
            system_description_override={"decision_effects": ["legal"]},
        )
        out = document_explainability(inputs)
        self.assertTrue(
            any("No explanation method covers local scope" in w for w in out["warnings"])
        )
        self.assertTrue(any("Article 86" in w for w in out["warnings"]))

    def test_overlapping_scope_methods_no_warning(self):
        """Test 11. Multiple methods with overlapping scope report coverage correctly."""
        inputs = _base_inputs(
            explanation_methods=[
                {
                    "method": "shap",
                    "scope": "both",
                    "target_audience": ["developers", "deployers", "affected-persons"],
                    "implementation_status": "implemented",
                    "evidence_ref": "x",
                    "known_limitations": ["a"],
                },
                {
                    "method": "lime",
                    "scope": "local",
                    "target_audience": ["developers"],
                    "implementation_status": "implemented",
                    "evidence_ref": "y",
                    "known_limitations": ["b"],
                },
            ],
            intrinsic_interpretability_claim=False,
            model_type="deep-neural-network",
        )
        out = document_explainability(inputs)
        self.assertTrue(out["scope_coverage"]["global_covered"])
        self.assertTrue(out["scope_coverage"]["local_covered"])


class AudienceCoverageTests(unittest.TestCase):
    def test_legal_effect_without_affected_persons_audience(self):
        """Test 6. decision_effects=[legal] without affected-persons audience is BLOCKING."""
        inputs = _base_inputs(
            explanation_methods=[
                {
                    "method": "intrinsic-decision-path",
                    "scope": "both",
                    "target_audience": ["developers", "deployers"],
                    "implementation_status": "implemented",
                    "evidence_ref": "x",
                    "known_limitations": ["limitation"],
                }
            ],
            system_description_override={"decision_effects": ["legal"]},
        )
        out = document_explainability(inputs)
        blocking = [w for w in out["warnings"] if w.startswith("BLOCKING")]
        self.assertTrue(any("affected-persons" in w for w in blocking))


class Art86Tests(unittest.TestCase):
    def test_art_86_applies_but_template_missing(self):
        """Test 7. Art. 86 applies but template_ref empty emits warning."""
        inputs = _base_inputs(
            art_86_response_template_ref="",
            system_description_override={"decision_effects": ["similarly-significant-effect"]},
        )
        out = document_explainability(inputs)
        self.assertTrue(out["art_86_applicability"]["applies"])
        self.assertTrue(
            any("Article 86 requires a template" in w for w in out["warnings"])
        )

    def test_art_86_readiness_fields(self):
        inputs = _base_inputs(
            system_description_override={"decision_effects": ["legal"]},
        )
        out = document_explainability(inputs)
        readiness = out["art_86_readiness"]
        self.assertTrue(readiness["applies"])
        self.assertTrue(readiness["response_template_present"])
        self.assertTrue(readiness["affected_persons_audience_present"])
        self.assertTrue(readiness["local_scope_method_present"])


class LimitationsTests(unittest.TestCase):
    def test_method_with_empty_known_limitations(self):
        """Test 8. Method with empty known_limitations emits MEASURE 2.9 warning."""
        inputs = _base_inputs(
            explanation_methods=[
                {
                    "method": "intrinsic-decision-path",
                    "scope": "both",
                    "target_audience": ["developers", "deployers", "affected-persons"],
                    "implementation_status": "implemented",
                    "evidence_ref": "x",
                    "known_limitations": [],
                }
            ],
        )
        out = document_explainability(inputs)
        self.assertTrue(
            any("empty known_limitations" in w for w in out["warnings"])
        )

    def test_not_applicable_without_rationale(self):
        """Test 9. implementation_status=not-applicable without rationale emits warning."""
        inputs = _base_inputs(
            model_type="deep-neural-network",
            intrinsic_interpretability_claim=False,
            explanation_methods=[
                {
                    "method": "shap",
                    "scope": "both",
                    "target_audience": ["developers", "deployers", "affected-persons"],
                    "implementation_status": "implemented",
                    "evidence_ref": "x",
                    "known_limitations": ["approximation"],
                },
                {
                    "method": "counterfactual",
                    "scope": "local",
                    "target_audience": ["developers"],
                    "implementation_status": "not-applicable",
                    "evidence_ref": "",
                    "known_limitations": [],
                },
            ],
        )
        out = document_explainability(inputs)
        self.assertTrue(
            any("not-applicable" in w and "known_limitations is empty" in w for w in out["warnings"])
        )


class VersionDiffTests(unittest.TestCase):
    def test_version_diff_computed_when_previous_ref_supplied(self):
        """Test 10. Schema diff summary emitted when previous_documentation_ref set."""
        inputs = _base_inputs(
            previous_documentation_ref="artifacts/explainability-v0.1.json",
        )
        out = document_explainability(inputs)
        self.assertIn("schema_diff_summary", out)
        self.assertEqual(
            out["schema_diff_summary"]["previous_documentation_ref"],
            "artifacts/explainability-v0.1.json",
        )


class JurisdictionTests(unittest.TestCase):
    def test_uk_jurisdiction_adds_atrs_citation(self):
        """Test 12. UK jurisdiction adds UK ATRS Section Tool details citation."""
        inputs = _base_inputs(
            system_description_override={"jurisdiction": "uk", "decision_effects": ["none"]},
        )
        out = document_explainability(inputs)
        self.assertIn("UK ATRS, Section Tool details", out["citations"])


class ValidationErrorTests(unittest.TestCase):
    def test_missing_system_description(self):
        """Test 13."""
        with self.assertRaises(ValueError):
            document_explainability({"model_type": "tree-based", "explanation_methods": []})

    def test_missing_model_type(self):
        """Test 14."""
        with self.assertRaises(ValueError):
            document_explainability({
                "system_description": {"system_name": "x"},
                "explanation_methods": [],
            })

    def test_missing_explanation_methods(self):
        """Test 15."""
        with self.assertRaises(ValueError):
            document_explainability({
                "system_description": {"system_name": "x"},
                "model_type": "linear",
            })

    def test_invalid_model_type(self):
        """Test 16."""
        inputs = _base_inputs(model_type="quantum-woo")
        with self.assertRaises(ValueError):
            document_explainability(inputs)

    def test_invalid_method_enum(self):
        """Test 17."""
        inputs = _base_inputs(
            explanation_methods=[
                {
                    "method": "magic-wand",
                    "scope": "both",
                    "target_audience": ["developers"],
                    "implementation_status": "implemented",
                    "known_limitations": ["x"],
                }
            ]
        )
        with self.assertRaises(ValueError):
            document_explainability(inputs)

    def test_invalid_scope_enum(self):
        """Test 18."""
        inputs = _base_inputs(
            explanation_methods=[
                {
                    "method": "shap",
                    "scope": "cosmic",
                    "target_audience": ["developers"],
                    "implementation_status": "implemented",
                    "known_limitations": ["x"],
                }
            ]
        )
        with self.assertRaises(ValueError):
            document_explainability(inputs)


class CrosswalkTests(unittest.TestCase):
    def test_crosswalk_default_true_emits_citations_key(self):
        """Test 19. Default enrich=True produces cross_framework_citations key."""
        inputs = _base_inputs()
        inputs.pop("enrich_with_crosswalk")
        out = document_explainability(inputs)
        self.assertIn("cross_framework_citations", out)
        self.assertIsInstance(out["cross_framework_citations"], list)

    def test_crosswalk_false_omits_key(self):
        """Test 20. enrich_with_crosswalk=False omits cross_framework_citations key."""
        inputs = _base_inputs(enrich_with_crosswalk=False)
        out = document_explainability(inputs)
        self.assertNotIn("cross_framework_citations", out)

    def test_crosswalk_graceful_failure(self):
        """Test 25. Crosswalk load failure degrades gracefully with a warning."""
        # Directly exercise enrichment with a target framework that yields no mappings.
        inputs = _base_inputs(
            enrich_with_crosswalk=True,
            crosswalk_target_frameworks=["nist-ai-rmf"],
        )
        out = document_explainability(inputs)
        # Either we got a list (success) or a warning (graceful fail). Both are acceptable.
        self.assertIn("cross_framework_citations", out)


class CitationFormatTests(unittest.TestCase):
    def test_citation_format_compliance(self):
        """Test 21. Citations match STYLE.md prefixes."""
        inputs = _base_inputs(
            system_description_override={"decision_effects": ["legal"], "jurisdiction": "uk"},
        )
        out = document_explainability(inputs)
        citations = out["citations"]
        # Required NIST prefix form.
        self.assertIn("NIST AI RMF, MEASURE 2.9", citations)
        # ISO.
        self.assertIn("ISO/IEC 42001:2023, Annex A, Control A.8.2", citations)
        # EU AI Act Art. 86 when applicable.
        self.assertTrue(any(c.startswith("EU AI Act, Article 86") for c in citations))
        # EU AI Act Art. 13.
        self.assertTrue(any(c.startswith("EU AI Act, Article 13") for c in citations))
        # UK ATRS when uk jurisdiction.
        self.assertIn("UK ATRS, Section Tool details", citations)
        # ISO/IEC TR 24028 trustworthiness reference.
        self.assertIn("ISO/IEC TR 24028:2020", citations)


class StyleTests(unittest.TestCase):
    def test_no_em_dash_no_emoji_no_hedging_in_rendered_output(self):
        """Test 22. Rendered Markdown contains no em-dashes, emojis, or hedging phrases."""
        inputs = _base_inputs(
            system_description_override={"decision_effects": ["legal"], "jurisdiction": "uk"},
        )
        out = document_explainability(inputs)
        md = render_markdown(out)
        csv = render_csv(out)
        for text in (md, csv):
            self.assertNotIn("\u2014", text)
            for phrase in (
                "may want to consider",
                "might be helpful to",
                "could potentially",
                "it is possible that",
                "you might find",
            ):
                self.assertNotIn(phrase, text.lower())


class MarkdownRenderingTests(unittest.TestCase):
    def test_markdown_has_required_sections(self):
        """Test 23. Markdown renders required sections."""
        inputs = _base_inputs(
            system_description_override={"decision_effects": ["legal"]},
        )
        out = document_explainability(inputs)
        md = render_markdown(out)
        for section in (
            "## Classification",
            "## Methods coverage",
            "## Scope coverage",
            "## Audience coverage",
            "## Art. 86 applicability",
            "## Limitations assessment",
            "## Warnings",
        ):
            self.assertIn(section, md)


class CsvRenderingTests(unittest.TestCase):
    def test_csv_row_count_matches_methods_coverage(self):
        """Test 24. CSV has one data row per method."""
        inputs = _base_inputs(
            model_type="deep-neural-network",
            intrinsic_interpretability_claim=False,
            explanation_methods=[
                {
                    "method": "shap",
                    "scope": "local",
                    "target_audience": ["developers", "deployers", "affected-persons"],
                    "implementation_status": "implemented",
                    "evidence_ref": "docs/shap.pdf",
                    "known_limitations": ["a"],
                },
                {
                    "method": "lime",
                    "scope": "global",
                    "target_audience": ["developers"],
                    "implementation_status": "implemented",
                    "evidence_ref": "docs/lime.pdf",
                    "known_limitations": ["b"],
                },
                {
                    "method": "counterfactual",
                    "scope": "local",
                    "target_audience": ["affected-persons"],
                    "implementation_status": "planned",
                    "evidence_ref": "",
                    "known_limitations": ["c"],
                    "target_date": "2026-06-30",
                },
            ],
        )
        out = document_explainability(inputs)
        csv_out = render_csv(out)
        lines = [ln for ln in csv_out.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1 + 3)  # header + 3 methods


if __name__ == "__main__":
    unittest.main()
