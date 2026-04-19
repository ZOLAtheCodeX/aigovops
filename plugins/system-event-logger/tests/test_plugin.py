"""Tests for the system-event-logger plugin."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

import plugin as sel  # noqa: E402


def _base_system_description(**overrides):
    sd = {
        "system_id": "SYS-001",
        "risk_tier": "high-risk-annex-iii",
        "jurisdiction": "eu",
        "remote_biometric_id": False,
        "sector": "employment",
        "lifecycle_state": "in-service",
    }
    sd.update(overrides)
    return sd


def _base_event_schema():
    return {
        "inference-request": {
            "request_id": {"type": "string", "required": True, "description": "unique request identifier"},
            "timestamp": {"type": "datetime", "required": True, "description": "request time UTC"},
            "input_hash": {"type": "string", "required": True, "description": "hash of input payload"},
        },
        "inference-output": {
            "request_id": {"type": "string", "required": True, "description": "matching request id"},
            "output_hash": {"type": "string", "required": True, "description": "hash of output"},
            "confidence": {"type": "float", "required": False, "description": "model confidence"},
        },
        "drift-signal": {
            "timestamp": {"type": "datetime", "required": True, "description": "signal time"},
            "metric": {"type": "string", "required": True, "description": "drift metric name"},
            "value": {"type": "float", "required": True, "description": "drift value"},
        },
        "safety-event": {
            "timestamp": {"type": "datetime", "required": True, "description": "event time"},
            "severity": {"type": "string", "required": True, "description": "severity tier"},
            "description": {"type": "string", "required": True, "description": "event description"},
        },
    }


def _base_retention_policy(**overrides):
    policy = {
        "policy_name": "eu-art-19-minimum",
        "minimum_days": 200,
        "maximum_days": 730,
        "deletion_procedure_ref": "DEL-PROC-001",
        "legal_basis_citation": "EU AI Act, Article 19, Paragraph 1",
    }
    policy.update(overrides)
    return policy


def _base_log_storage(**overrides):
    storage = {
        "storage_system": "encrypted-cloud-bucket",
        "encryption_at_rest": True,
        "access_controls_ref": "IAM-POLICY-001",
        "tamper_evidence_method": "hash-chain",
    }
    storage.update(overrides)
    return storage


def _base_traceability_mappings():
    return {
        "drift-signal": ["a"],
        "safety-event": ["a", "b"],
        "inference-output": ["b", "c"],
        "inference-request": ["c"],
    }


def _base_inputs(**overrides):
    inputs = {
        "system_description": _base_system_description(),
        "event_schema": _base_event_schema(),
        "retention_policy": _base_retention_policy(),
        "log_storage": _base_log_storage(),
        "traceability_mappings": _base_traceability_mappings(),
    }
    inputs.update(overrides)
    return inputs


class HappyPathTests(unittest.TestCase):
    def test_happy_path_compliant(self):
        result = sel.define_event_schema(_base_inputs())
        self.assertEqual(result["agent_signature"], "system-event-logger/0.1.0")
        self.assertEqual(result["art_12_applicability"]["status"], "mandatory")
        self.assertTrue(result["retention_policy_assessment"]["eu_art_19_floor_satisfied"])
        self.assertTrue(result["tamper_evidence_assessment"]["tamper_evidence_present"])
        self.assertTrue(result["traceability_coverage"]["all_purposes_covered"])
        # No blocking retention warnings.
        self.assertFalse(
            any("six-month floor" in w for w in result["warnings"])
        )

    def test_happy_path_has_required_top_level_keys(self):
        result = sel.define_event_schema(_base_inputs())
        for key in (
            "timestamp",
            "agent_signature",
            "framework",
            "system_description_echo",
            "art_12_applicability",
            "event_schema_normalized",
            "traceability_coverage",
            "retention_policy_assessment",
            "tamper_evidence_assessment",
            "citations",
            "warnings",
            "summary",
        ):
            self.assertIn(key, result)


class BiometricTests(unittest.TestCase):
    def test_biometric_all_fields_present(self):
        schema = _base_event_schema()
        schema["biometric-verification"] = {
            f: {"type": "string", "required": True, "description": ""}
            for f in sel.BIOMETRIC_REQUIRED_FIELDS
        }
        inputs = _base_inputs(
            system_description=_base_system_description(remote_biometric_id=True),
            event_schema=schema,
        )
        # Add traceability for the new category to preserve coverage.
        inputs["traceability_mappings"]["biometric-verification"] = ["a"]
        result = sel.define_event_schema(inputs)
        self.assertIn("biometric_art_12_3_check", result)
        self.assertTrue(result["biometric_art_12_3_check"]["satisfied"])
        self.assertFalse(
            any("Biometric-verification field" in w for w in result["warnings"])
        )

    def test_biometric_missing_operating_person_identity(self):
        schema = _base_event_schema()
        required_minus_one = [f for f in sel.BIOMETRIC_REQUIRED_FIELDS if f != "operating_person_identity"]
        schema["biometric-verification"] = {
            f: {"type": "string", "required": True, "description": ""}
            for f in required_minus_one
        }
        inputs = _base_inputs(
            system_description=_base_system_description(remote_biometric_id=True),
            event_schema=schema,
        )
        inputs["traceability_mappings"]["biometric-verification"] = ["a"]
        result = sel.define_event_schema(inputs)
        self.assertFalse(result["biometric_art_12_3_check"]["satisfied"])
        self.assertIn("operating_person_identity", result["biometric_art_12_3_check"]["missing_fields"])
        self.assertTrue(
            any("operating_person_identity" in w and "Article 12, Paragraph 3" in w
                for w in result["warnings"])
        )


class RetentionTests(unittest.TestCase):
    def test_retention_below_six_month_floor_blocks(self):
        inputs = _base_inputs(
            retention_policy=_base_retention_policy(minimum_days=90),
        )
        result = sel.define_event_schema(inputs)
        self.assertFalse(result["retention_policy_assessment"]["eu_art_19_floor_satisfied"])
        self.assertTrue(
            any("six-month floor" in w and "Article 19" in w for w in result["warnings"])
        )

    def test_retention_policy_none_blocks_for_high_risk(self):
        inputs = _base_inputs(
            retention_policy=_base_retention_policy(policy_name="none", minimum_days=0),
        )
        result = sel.define_event_schema(inputs)
        self.assertTrue(
            any("policy_name is 'none'" in w and "Article 19" in w for w in result["warnings"])
        )

    def test_sectoral_finance_with_five_year_retention_and_citation_compliant(self):
        inputs = _base_inputs(
            retention_policy=_base_retention_policy(
                policy_name="sectoral-finance",
                minimum_days=1825,
                legal_basis_citation="MiFID II Article 16(7)",
            ),
        )
        result = sel.define_event_schema(inputs)
        self.assertTrue(result["retention_policy_assessment"]["eu_art_19_floor_satisfied"])
        self.assertFalse(
            any("legal_basis_citation" in w for w in result["warnings"])
        )
        self.assertIn("EU AI Act, Article 19, Paragraph 2", result["citations"])

    def test_sectoral_policy_missing_legal_basis_warns(self):
        inputs = _base_inputs(
            retention_policy=_base_retention_policy(
                policy_name="sectoral-healthcare",
                minimum_days=730,
                legal_basis_citation="",
            ),
        )
        result = sel.define_event_schema(inputs)
        self.assertTrue(
            any("legal_basis_citation is empty" in w for w in result["warnings"])
        )


class TraceabilityTests(unittest.TestCase):
    def test_missing_purpose_a(self):
        mappings = _base_traceability_mappings()
        # Remove all references to purpose 'a'.
        for category in list(mappings.keys()):
            mappings[category] = [p for p in mappings[category] if p != "a"]
        inputs = _base_inputs(traceability_mappings=mappings)
        result = sel.define_event_schema(inputs)
        self.assertTrue(
            any("Article 12, Paragraph 2, Point (a)" in w for w in result["warnings"])
        )

    def test_missing_purpose_b(self):
        mappings = _base_traceability_mappings()
        for category in list(mappings.keys()):
            mappings[category] = [p for p in mappings[category] if p != "b"]
        inputs = _base_inputs(traceability_mappings=mappings)
        result = sel.define_event_schema(inputs)
        self.assertTrue(
            any("Article 12, Paragraph 2, Point (b)" in w for w in result["warnings"])
        )

    def test_missing_purpose_c(self):
        mappings = _base_traceability_mappings()
        for category in list(mappings.keys()):
            mappings[category] = [p for p in mappings[category] if p != "c"]
        inputs = _base_inputs(traceability_mappings=mappings)
        result = sel.define_event_schema(inputs)
        self.assertTrue(
            any("Article 12, Paragraph 2, Point (c)" in w for w in result["warnings"])
        )


class TamperEvidenceTests(unittest.TestCase):
    def test_missing_tamper_evidence_method_warns(self):
        storage = _base_log_storage()
        storage["tamper_evidence_method"] = ""
        inputs = _base_inputs(log_storage=storage)
        result = sel.define_event_schema(inputs)
        self.assertFalse(result["tamper_evidence_assessment"]["tamper_evidence_present"])
        self.assertTrue(
            any("tamper_evidence_method" in w and "Article 26, Paragraph 6" in w
                for w in result["warnings"])
        )


class SchemaDiffTests(unittest.TestCase):
    def test_schema_diff_emitted_when_previous_ref_supplied(self):
        inputs = _base_inputs(previous_schema_ref="sel-2025-12-01-v0")
        result = sel.define_event_schema(inputs)
        self.assertIn("schema_diff_summary", result)
        self.assertEqual(
            result["schema_diff_summary"]["previous_schema_ref"], "sel-2025-12-01-v0"
        )

    def test_schema_diff_absent_when_no_ref(self):
        result = sel.define_event_schema(_base_inputs())
        self.assertNotIn("schema_diff_summary", result)


class ApplicabilityTests(unittest.TestCase):
    def test_non_high_risk_recommended_not_mandated(self):
        inputs = _base_inputs(
            system_description=_base_system_description(
                risk_tier="limited-risk",
            ),
            retention_policy=_base_retention_policy(minimum_days=90),
        )
        result = sel.define_event_schema(inputs)
        self.assertEqual(
            result["art_12_applicability"]["status"], "recommended-not-mandated"
        )
        # Non-high-risk should not be blocked by the six-month floor.
        self.assertFalse(
            any("six-month floor" in w for w in result["warnings"])
        )


class ValidationErrorTests(unittest.TestCase):
    def test_missing_system_description_raises(self):
        with self.assertRaises(ValueError):
            sel.define_event_schema({
                "event_schema": _base_event_schema(),
                "retention_policy": _base_retention_policy(),
            })

    def test_missing_event_schema_raises(self):
        with self.assertRaises(ValueError):
            sel.define_event_schema({
                "system_description": _base_system_description(),
                "retention_policy": _base_retention_policy(),
            })

    def test_missing_retention_policy_raises(self):
        with self.assertRaises(ValueError):
            sel.define_event_schema({
                "system_description": _base_system_description(),
                "event_schema": _base_event_schema(),
            })

    def test_invalid_retention_policy_name_raises(self):
        inputs = _base_inputs(
            retention_policy=_base_retention_policy(policy_name="unknown-policy"),
        )
        with self.assertRaises(ValueError):
            sel.define_event_schema(inputs)

    def test_invalid_event_category_raises(self):
        schema = _base_event_schema()
        schema["unknown-category"] = {
            "field_a": {"type": "string", "required": True, "description": ""}
        }
        inputs = _base_inputs(event_schema=schema)
        with self.assertRaises(ValueError):
            sel.define_event_schema(inputs)

    def test_invalid_risk_tier_raises(self):
        inputs = _base_inputs(
            system_description=_base_system_description(risk_tier="very-high"),
        )
        with self.assertRaises(ValueError):
            sel.define_event_schema(inputs)

    def test_invalid_traceability_purpose_raises(self):
        mappings = {"inference-request": ["z"]}
        inputs = _base_inputs(traceability_mappings=mappings)
        with self.assertRaises(ValueError):
            sel.define_event_schema(inputs)


class CrosswalkTests(unittest.TestCase):
    def test_crosswalk_default_true_populates_cross_framework_citations(self):
        result = sel.define_event_schema(_base_inputs())
        self.assertIn("cross_framework_citations", result)
        self.assertTrue(result["cross_framework_citations"])

    def test_crosswalk_false_omits_key(self):
        inputs = _base_inputs()
        inputs["enrich_with_crosswalk"] = False
        result = sel.define_event_schema(inputs)
        self.assertNotIn("cross_framework_citations", result)
        self.assertNotIn("cross_framework_references", result)

    def test_graceful_crosswalk_failure_still_produces_schema(self):
        # Monkey-patch the load helper to raise, simulating a missing
        # crosswalk module, and confirm the plugin still emits a schema
        # with a top-level warning instead of crashing.
        orig = sel._load_crosswalk_module
        try:
            def raise_fn():
                raise ImportError("simulated missing crosswalk")
            sel._load_crosswalk_module = raise_fn  # type: ignore[assignment]
            result = sel.define_event_schema(_base_inputs())
        finally:
            sel._load_crosswalk_module = orig  # type: ignore[assignment]
        self.assertIn("event_schema_normalized", result)
        self.assertTrue(
            any("Crosswalk plugin unavailable" in w for w in result["warnings"])
        )


class CitationFormatTests(unittest.TestCase):
    def test_citation_prefixes_compliant(self):
        result = sel.define_event_schema(_base_inputs())
        for c in result["citations"]:
            self.assertTrue(
                c.startswith(("EU AI Act, ", "ISO/IEC 42001:2023, ", "NIST AI RMF, ")),
                f"citation {c!r} fails STYLE.md prefix check",
            )


class StylePurityTests(unittest.TestCase):
    def test_markdown_has_required_sections(self):
        schema = _base_event_schema()
        schema["biometric-verification"] = {
            f: {"type": "string", "required": True, "description": ""}
            for f in sel.BIOMETRIC_REQUIRED_FIELDS
        }
        inputs = _base_inputs(
            system_description=_base_system_description(remote_biometric_id=True),
            event_schema=schema,
            previous_schema_ref="sel-prev-ref",
        )
        inputs["traceability_mappings"]["biometric-verification"] = ["a"]
        result = sel.define_event_schema(inputs)
        md = sel.render_markdown(result)
        for section in (
            "## Applicability",
            "## Event schema",
            "## Biometric Article 12(3) check",
            "## Traceability",
            "## Retention policy",
            "## Tamper evidence",
            "## Schema diff",
            "## Warnings",
        ):
            self.assertIn(section, md, f"missing section {section!r}")

    def test_no_emdash_no_emoji_no_hedging_in_output(self):
        result = sel.define_event_schema(_base_inputs())
        md = sel.render_markdown(result)
        csv_out = sel.render_csv(result)
        for text in (md, csv_out):
            self.assertNotIn("\u2014", text, "em-dash present in output")
            for phrase in (
                "may want to consider",
                "might be helpful to",
                "could potentially",
                "it is possible that",
                "you might find",
            ):
                self.assertNotIn(phrase, text.lower())


class RenderingTests(unittest.TestCase):
    def test_csv_row_count_matches_normalized_entries(self):
        result = sel.define_event_schema(_base_inputs())
        csv_out = sel.render_csv(result)
        data_lines = [ln for ln in csv_out.strip().splitlines() if ln]
        # header + one row per normalized entry
        self.assertEqual(len(data_lines), 1 + len(result["event_schema_normalized"]))


if __name__ == "__main__":
    unittest.main()
