"""
Tests for the bias-evaluator plugin.

Runs under pytest or as a standalone script. No external dependencies.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _system(sector: str = "employment") -> dict:
    return {
        "system_name": "ResumeScreen-X",
        "purpose": "Screen candidate resumes for an interview short-list.",
        "decision_authority": "decision-support",
        "sector": sector,
    }


def _protected_race() -> list:
    return [{"attribute_name": "race", "categories_present": ["white", "black"]}]


def _two_group_counts(impact_ratio_target: float, per_group_total: int = 1000) -> dict:
    """Build per_group_counts producing impact_ratio close to target.

    selection_rate_white = 0.40 (selected = 400)
    selection_rate_black = 0.40 * impact_ratio_target
    """
    selected_black = int(round(per_group_total * 0.40 * impact_ratio_target))
    return {
        "race:white": {"total": per_group_total, "selected": int(per_group_total * 0.40)},
        "race:black": {"total": per_group_total, "selected": selected_black},
    }


def _eval_data(per_group_counts: dict, ground_truth: bool = False) -> dict:
    return {
        "dataset_ref": "Q2-2026-test-pool",
        "evaluation_date": "2026-04-15",
        "sample_size": sum(c.get("total", 0) for c in per_group_counts.values()),
        "ground_truth_available": ground_truth,
        "per_group_counts": per_group_counts,
    }


# ---------------------------------------------------------------------------
# Happy path and metric correctness
# ---------------------------------------------------------------------------


class TestHappyPath(unittest.TestCase):
    def test_happy_path_pass_under_nyc_4_5ths(self):
        # Test 1: impact_ratio approximately 0.85, NYC rule passes.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.85)),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["selection-rate", "impact-ratio"],
            "jurisdiction_rules": ["nyc-ll144-4-5ths"],
        })
        for f in (
            "timestamp", "agent_signature", "framework",
            "system_description_echo", "evaluation_data_echo",
            "protected_attributes_echo", "per_metric_results",
            "rule_findings", "underpowered_groups", "citations",
            "warnings", "summary",
        ):
            self.assertIn(f, result)
        ir = next(r for r in result["per_metric_results"] if r["metric"] == "impact-ratio")
        self.assertAlmostEqual(ir["value"], 0.85, places=3)
        nyc_finding = next(f for f in result["rule_findings"] if f["rule"] == "nyc-ll144-4-5ths")
        self.assertEqual(nyc_finding["status"], "pass")

    def test_disparate_impact_concern_below_4_5ths(self):
        # Test 2: impact_ratio 0.65 fails NYC.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.65)),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["impact-ratio"],
            "jurisdiction_rules": ["nyc-ll144-4-5ths"],
        })
        ir = next(r for r in result["per_metric_results"] if r["metric"] == "impact-ratio")
        self.assertLess(ir["value"], 0.8)
        nyc_finding = next(f for f in result["rule_findings"] if f["rule"] == "nyc-ll144-4-5ths")
        self.assertEqual(nyc_finding["status"], "fail-disparate-impact-concern")

    def test_equalized_odds_requires_ground_truth(self):
        # Test 3: gt=False, equalized-odds requested.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.9), ground_truth=False),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["equalized-odds-difference"],
        })
        eod = next(r for r in result["per_metric_results"] if r["metric"] == "equalized-odds-difference")
        self.assertIsNone(eod.get("value"))
        self.assertEqual(eod.get("status"), "requires-ground-truth")
        warnings_text = " ".join(result["warnings"])
        self.assertIn("ground", warnings_text.lower())

    def test_equalized_odds_computed_when_ground_truth_supplied(self):
        # Test 4: gt=True with known counts.
        per_group = {
            "race:white": {
                "total": 1000, "selected": 400,
                "true_positive": 350, "false_positive": 50,
                "true_negative": 450, "false_negative": 150,
            },
            "race:black": {
                "total": 1000, "selected": 360,
                "true_positive": 280, "false_positive": 80,
                "true_negative": 420, "false_negative": 220,
            },
        }
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(per_group, ground_truth=True),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["equalized-odds-difference"],
        })
        eod = next(r for r in result["per_metric_results"] if r["metric"] == "equalized-odds-difference")
        self.assertIsNotNone(eod["value"])
        self.assertGreater(eod["value"], 0)

    def test_intersectional_analysis_compound_groups(self):
        # Test 5: intersectional True, small-group warnings surface.
        per_group = {
            "race:white": {"total": 500, "selected": 250},
            "race:black": {"total": 500, "selected": 200},
            "race:white|sex:male": {"total": 250, "selected": 130},
            "race:white|sex:female": {"total": 250, "selected": 120},
            "race:black|sex:male": {"total": 250, "selected": 110},
            "race:black|sex:female": {"total": 25, "selected": 8},
        }
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(per_group),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["selection-rate", "impact-ratio"],
            "intersectional_analysis": True,
            "minimum_group_size": 30,
        })
        self.assertIsNotNone(result["intersectional_results"])
        self.assertGreater(len(result["intersectional_results"]), 0)
        # The 25-record black female group should be flagged.
        flagged_keys = [g["group_key"] for g in result["underpowered_groups"]]
        self.assertIn("race:black|sex:female", flagged_keys)

    def test_underpowered_group_warning(self):
        # Test 6: minimum_group_size=100, one group N=20.
        per_group = {
            "race:white": {"total": 500, "selected": 200},
            "race:asian": {"total": 20, "selected": 8},
        }
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(per_group),
            "protected_attributes": [
                {"attribute_name": "race", "categories_present": ["white", "asian"]}
            ],
            "minimum_group_size": 100,
        })
        warnings_text = " ".join(result["warnings"])
        self.assertIn("race:asian", warnings_text)
        self.assertIn("100", warnings_text)


# ---------------------------------------------------------------------------
# Jurisdictional rule application
# ---------------------------------------------------------------------------


class TestJurisdictionalRules(unittest.TestCase):
    def test_nyc_4_5ths_rule_failure_with_citation(self):
        # Test 7: NYC LL144 fail with citation.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.7)),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["impact-ratio"],
            "jurisdiction_rules": ["nyc-ll144-4-5ths"],
        })
        finding = next(f for f in result["rule_findings"] if f["rule"] == "nyc-ll144-4-5ths")
        self.assertEqual(finding["status"], "fail-disparate-impact-concern")
        self.assertEqual(finding["citation"], "NYC LL144 Final Rule, Section 5-301")

    def test_eu_art_10_4_organizational_threshold_concern(self):
        # Test 8: EU Art 10(4) with org thresh=0.1, value 0.15 -> concern.
        per_group = {
            "race:white": {"total": 1000, "selected": 600},
            "race:black": {"total": 1000, "selected": 450},
        }
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(per_group),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["demographic-parity-difference"],
            "jurisdiction_rules": ["eu-ai-act-art-10-4"],
            "organizational_thresholds": {"demographic-parity-difference": 0.1},
        })
        eu_finding = next(f for f in result["rule_findings"] if f["rule"] == "eu-ai-act-art-10-4")
        self.assertEqual(eu_finding["organizational_threshold_status"], "concern-exceeds-organizational-threshold")
        self.assertEqual(eu_finding["citation"], "EU AI Act, Article 10, Paragraph 4")

    def test_colorado_reasonable_care_documented(self):
        # Test 9: Colorado SB 205 with evaluation -> reasonable-care-documented.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.9)),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["impact-ratio"],
            "jurisdiction_rules": ["colorado-sb-205-reasonable-care"],
        })
        co = next(f for f in result["rule_findings"] if f["rule"] == "colorado-sb-205-reasonable-care")
        self.assertEqual(co["status"], "reasonable-care-documented")
        self.assertEqual(co["citation"], "Colorado SB 205, Section 6-1-1702(1)")

    def test_singapore_veritas_next_steps(self):
        # Test 10: Singapore Veritas -> next-steps emitted.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.9)),
            "protected_attributes": _protected_race(),
            "jurisdiction_rules": ["singapore-veritas-fairness"],
        })
        sg = next(f for f in result["rule_findings"] if f["rule"] == "singapore-veritas-fairness")
        self.assertIn("next_steps", sg)
        self.assertGreater(len(sg["next_steps"]), 0)
        self.assertEqual(sg["citation"], "MAS Veritas (2022)")

    def test_multiple_jurisdictions_distinct_findings(self):
        # Test 11: Multiple jurisdictions applied, distinct entries.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.85)),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["selection-rate", "impact-ratio"],
            "jurisdiction_rules": [
                "nyc-ll144-4-5ths",
                "eu-ai-act-art-10-4",
                "colorado-sb-205-reasonable-care",
                "nist-measure-2-11",
                "iso-42001-a-7-4",
                "singapore-veritas-fairness",
            ],
        })
        rule_ids = [f["rule"] for f in result["rule_findings"]]
        self.assertEqual(len(rule_ids), 6)
        self.assertEqual(len(set(rule_ids)), 6)


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class TestValidationErrors(unittest.TestCase):
    def test_missing_evaluation_data_raises(self):
        # Test 12.
        with self.assertRaises(ValueError):
            plugin.evaluate_bias({
                "system_description": _system(),
                "protected_attributes": _protected_race(),
            })

    def test_missing_protected_attributes_raises(self):
        # Test 13.
        with self.assertRaises(ValueError):
            plugin.evaluate_bias({
                "system_description": _system(),
                "evaluation_data": _eval_data(_two_group_counts(0.9)),
            })

    def test_invalid_metric_raises(self):
        # Test 14.
        with self.assertRaises(ValueError):
            plugin.evaluate_bias({
                "system_description": _system(),
                "evaluation_data": _eval_data(_two_group_counts(0.9)),
                "protected_attributes": _protected_race(),
                "metrics_to_compute": ["nonexistent-metric"],
            })

    def test_invalid_jurisdiction_rule_raises(self):
        # Test 15.
        with self.assertRaises(ValueError):
            plugin.evaluate_bias({
                "system_description": _system(),
                "evaluation_data": _eval_data(_two_group_counts(0.9)),
                "protected_attributes": _protected_race(),
                "jurisdiction_rules": ["made-up-rule"],
            })


# ---------------------------------------------------------------------------
# Anti-hallucination and edge cases
# ---------------------------------------------------------------------------


class TestAntiHallucination(unittest.TestCase):
    def test_impact_ratio_division_by_zero_safe(self):
        # Test 16: max selection rate = 0.
        per_group = {
            "race:white": {"total": 1000, "selected": 0},
            "race:black": {"total": 1000, "selected": 0},
        }
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(per_group),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["impact-ratio"],
        })
        ir = next(r for r in result["per_metric_results"] if r["metric"] == "impact-ratio")
        self.assertIsNone(ir["value"])
        self.assertEqual(ir["status"], "undefined-division-by-zero")
        warnings_text = " ".join(result["warnings"])
        self.assertIn("0", warnings_text)


class TestCrosswalkEnrichment(unittest.TestCase):
    def test_crosswalk_default_true(self):
        # Test 17.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.9)),
            "protected_attributes": _protected_race(),
        })
        self.assertIn("cross_framework_citations", result)

    def test_crosswalk_disabled(self):
        # Test 18.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.9)),
            "protected_attributes": _protected_race(),
            "enrich_with_crosswalk": False,
        })
        self.assertNotIn("cross_framework_citations", result)


class TestCitationFormat(unittest.TestCase):
    def test_citation_format_compliance(self):
        # Test 19.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.85)),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["selection-rate", "impact-ratio"],
            "jurisdiction_rules": [
                "nyc-ll144-4-5ths",
                "eu-ai-act-art-10-4",
                "colorado-sb-205-reasonable-care",
                "iso-42001-a-7-4",
                "nist-measure-2-11",
                "singapore-veritas-fairness",
            ],
        })
        prefixes = (
            "NIST AI RMF, MEASURE",
            "EU AI Act, Article",
            "NYC LL144",
            "Colorado SB 205, Section",
            "ISO/IEC 42001:2023, Annex A, Control",
            "ISO/IEC TR 24027:2021",
            "MAS Veritas (2022)",
            "NYC DCWP AEDT Rules, 6 RCNY Section",
        )
        for c in result["citations"]:
            self.assertTrue(
                any(c.startswith(p) for p in prefixes),
                f"Citation {c!r} does not match any STYLE.md prefix",
            )


class TestStyle(unittest.TestCase):
    def test_no_em_dash_no_emoji_no_hedging(self):
        # Test 20.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.85)),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["selection-rate", "impact-ratio"],
            "jurisdiction_rules": [
                "nyc-ll144-4-5ths",
                "eu-ai-act-art-10-4",
                "colorado-sb-205-reasonable-care",
                "singapore-veritas-fairness",
            ],
        })
        md = plugin.render_markdown(result)
        csv = plugin.render_csv(result)
        for text in (md, csv):
            self.assertNotIn("\u2014", text)
            forbidden = [
                "may want to consider",
                "might be helpful to",
                "could potentially",
                "it is possible that",
                "you might find",
            ]
            lower = text.lower()
            for phrase in forbidden:
                self.assertNotIn(phrase, lower)


class TestRendering(unittest.TestCase):
    def test_markdown_required_sections(self):
        # Test 21.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.85)),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["selection-rate", "impact-ratio"],
            "jurisdiction_rules": ["nyc-ll144-4-5ths"],
        })
        md = plugin.render_markdown(result)
        for header in (
            "# Bias Evaluation Report",
            "## Summary",
            "## Applicable citations",
            "## Per-metric results",
            "## Rule findings",
        ):
            self.assertIn(header, md)

    def test_csv_row_count_matches_per_metric_results(self):
        # Test 22.
        result = plugin.evaluate_bias({
            "system_description": _system(),
            "evaluation_data": _eval_data(_two_group_counts(0.9)),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["selection-rate", "impact-ratio", "demographic-parity-difference"],
        })
        csv = plugin.render_csv(result)
        # Header + one row per per_metric_results entry.
        rows = [line for line in csv.strip().split("\n") if line]
        self.assertEqual(len(rows), 1 + len(result["per_metric_results"]))


class TestGracefulFailures(unittest.TestCase):
    def test_graceful_crosswalk_failure(self):
        # Test 23: temporarily redirect crosswalk dir to a non-existent path.
        original = plugin._CROSSWALK_DIR
        try:
            plugin._CROSSWALK_DIR = Path("/nonexistent/path/for/test")
            result = plugin.evaluate_bias({
                "system_description": _system(),
                "evaluation_data": _eval_data(_two_group_counts(0.9)),
                "protected_attributes": _protected_race(),
                "enrich_with_crosswalk": True,
            })
            self.assertIn("cross_framework_citations", result)
            # Empty list because load failed, plus a warning about the skip.
            self.assertEqual(result["cross_framework_citations"], [])
            warnings_text = " ".join(result["warnings"])
            self.assertIn("Crosswalk", warnings_text)
        finally:
            plugin._CROSSWALK_DIR = original

    def test_non_high_risk_sector_recommended_not_mandated_note(self):
        # Test 24: sector outside high-risk family still produces an evaluation
        # plus a recommended-not-mandated warning.
        result = plugin.evaluate_bias({
            "system_description": _system(sector="entertainment"),
            "evaluation_data": _eval_data(_two_group_counts(0.9)),
            "protected_attributes": _protected_race(),
            "metrics_to_compute": ["selection-rate", "impact-ratio"],
        })
        # Evaluation still produced.
        ir = next(r for r in result["per_metric_results"] if r["metric"] == "impact-ratio")
        self.assertIsNotNone(ir["value"])
        warnings_text = " ".join(result["warnings"])
        self.assertIn("recommended-not-mandated", warnings_text)


if __name__ == "__main__":
    unittest.main()
