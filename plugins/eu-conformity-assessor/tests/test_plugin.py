"""Tests for the eu-conformity-assessor plugin.

Pytest-compatible and standalone-runnable.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

import plugin  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _eu_provider() -> dict:
    return {
        "legal_name": "Acme Healthcare AI BV",
        "address": "Keizersgracht 1, 1015 CJ Amsterdam, Netherlands",
        "country": "NL",
        "contact": "compliance@acme-health.eu",
    }


def _non_eu_provider(with_rep: bool = False) -> dict:
    base = {
        "legal_name": "Acme Healthcare AI Inc",
        "address": "1 Acme Way, Seattle, WA 98101 USA",
        "country": "US",
        "contact": "compliance@acme-health.com",
    }
    if with_rep:
        base["authorised_representative"] = {
            "legal_name": "Acme EU Rep BV",
            "address": "Keizersgracht 1, 1015 CJ Amsterdam, Netherlands",
        }
    return base


def _system(annex_iii: str = "4-employment", **overrides) -> dict:
    base = {
        "system_id": "AISYS-001",
        "risk_tier": "high-risk",
        "intended_use": "Resume screening for job applicants in EU",
        "sector": "employment",
        "annex_iii_category": annex_iii,
        "ce_marking_required": True,
    }
    base.update(overrides)
    return base


def _write_bundle(tmp: Path, artifact_types: list[str]) -> Path:
    bundle_dir = tmp / "bundle"
    bundle_dir.mkdir()
    artifacts = []
    for atype in artifact_types:
        artifacts.append({
            "path": f"artifacts/{atype}/{atype}.json",
            "plugin": "test",
            "agent_signature": "test/0.1.0",
            "sha256": "x" * 64,
            "size_bytes": 100,
            "artifact_type": atype,
            "emitted_at": "2026-04-18T00:00:00Z",
        })
    manifest = {
        "bundle_schema_version": "1.0.0",
        "bundle_id": "test-bundle",
        "generated_at": "2026-04-18T00:00:00Z",
        "generated_by": "test",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    (bundle_dir / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle_dir


def _full_bundle_artifact_types() -> list[str]:
    """Every artifact type that satisfies all Annex IV categories + QMS."""
    return [
        "ai-system-inventory",
        "high-risk-classification",
        "audit-log-entry",
        "metrics-report",
        "risk-register",
        "aisia",
        "soa",
        "management-review-package",
        "internal-audit-plan",
    ]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath(unittest.TestCase):
    def test_001_employment_internal_control_full_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = _write_bundle(Path(tmpdir), _full_bundle_artifact_types())
            result = plugin.assess_conformity_procedure({
                "system_description": _system(annex_iii="4-employment"),
                "provider_identity": _eu_provider(),
                "procedure_requested": "annex-vi-internal-control",
                "evidence_bundle_ref": str(bundle_dir),
                "ce_marking_location": "system",
                "registration_status": {
                    "eu_database_entry_id": "EU-DB-12345",
                    "registration_date": "2026-04-01",
                    "public_or_restricted": "public",
                },
                "reviewed_by": "Zola Valashiya",
                "enrich_with_crosswalk": False,
            })
        self.assertEqual(result["procedure_selected"], "annex-vi-internal-control")
        self.assertTrue(result["procedure_applicability"]["aligned"])
        self.assertEqual(result["registration_check"]["status"], "registered")
        self.assertEqual(result["qms_attestation"]["status"], "satisfied")
        self.assertEqual(result["summary"]["annex_iv_categories_missing"], 0)
        self.assertEqual(result["framework"], "eu-ai-act")


# ---------------------------------------------------------------------------
# Procedure selection (Article 43)
# ---------------------------------------------------------------------------


class TestProcedureSelection(unittest.TestCase):
    def test_002_biometrics_no_standards_requires_notified_body(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(annex_iii="1-biometrics"),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
            "harmonised_standards_applied": [],
            "enrich_with_crosswalk": False,
        })
        self.assertEqual(
            result["procedure_applicability"]["required_procedure"],
            "annex-vii-notified-body",
        )
        self.assertFalse(result["procedure_applicability"]["aligned"])
        self.assertTrue(any(
            "Biometric system without harmonised standards" in w
            for w in result["warnings"]
        ))

    def test_003_biometrics_with_standards_permits_internal_control(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(annex_iii="1-biometrics"),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
            "harmonised_standards_applied": ["ISO/IEC 19795-1:2021"],
            "enrich_with_crosswalk": False,
        })
        self.assertEqual(
            result["procedure_applicability"]["required_procedure"],
            "annex-vi-internal-control",
        )
        self.assertTrue(result["procedure_applicability"]["aligned"])

    def test_004_annex_i_legislation_routes_to_harmonised_procedure(self):
        sysdesc = _system(annex_iii=None)
        sysdesc["annex_iii_category"] = None
        sysdesc["annex_i_legislation"] = ["Regulation (EU) 2017/745 (MDR)"]
        result = plugin.assess_conformity_procedure({
            "system_description": sysdesc,
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-i-harmonised-legislation",
            "enrich_with_crosswalk": False,
        })
        self.assertEqual(
            result["procedure_applicability"]["required_procedure"],
            "annex-i-harmonised-legislation",
        )
        self.assertIn(
            "EU AI Act, Article 43, Paragraph 3",
            result["procedure_applicability"]["citations"],
        )


# ---------------------------------------------------------------------------
# Authorised representative (Article 22)
# ---------------------------------------------------------------------------


class TestAuthorisedRepresentative(unittest.TestCase):
    def test_005_non_eu_provider_without_rep_warns(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(),
            "provider_identity": _non_eu_provider(with_rep=False),
            "procedure_requested": "annex-vi-internal-control",
            "enrich_with_crosswalk": False,
        })
        self.assertTrue(any(
            "authorised representative" in w and "Article 22" in w
            for w in result["warnings"]
        ))

    def test_005b_non_eu_provider_with_rep_no_warning(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(),
            "provider_identity": _non_eu_provider(with_rep=True),
            "procedure_requested": "annex-vi-internal-control",
            "enrich_with_crosswalk": False,
        })
        self.assertFalse(any(
            "authorised representative" in w for w in result["warnings"]
        ))


# ---------------------------------------------------------------------------
# Annex IV completeness
# ---------------------------------------------------------------------------


class TestAnnexIvCompleteness(unittest.TestCase):
    def test_006_missing_risk_management_recommends_risk_register_builder(self):
        # Bundle with everything except risk-register and aisia.
        with tempfile.TemporaryDirectory() as tmpdir:
            types = [t for t in _full_bundle_artifact_types() if t not in ("risk-register", "aisia")]
            bundle_dir = _write_bundle(Path(tmpdir), types)
            result = plugin.assess_conformity_procedure({
                "system_description": _system(),
                "provider_identity": _eu_provider(),
                "procedure_requested": "annex-vi-internal-control",
                "evidence_bundle_ref": str(bundle_dir),
                "enrich_with_crosswalk": False,
            })
        rm_row = next(r for r in result["annex_iv_completeness"] if r["category"] == "risk-management")
        self.assertEqual(rm_row["status"], "missing")
        self.assertEqual(rm_row["recommended_producing_plugin"], "risk-register-builder")

    def test_007_complete_bundle_marks_all_categories_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = _write_bundle(Path(tmpdir), _full_bundle_artifact_types())
            result = plugin.assess_conformity_procedure({
                "system_description": _system(),
                "provider_identity": _eu_provider(),
                "procedure_requested": "annex-vi-internal-control",
                "evidence_bundle_ref": str(bundle_dir),
                "enrich_with_crosswalk": False,
            })
        for row in result["annex_iv_completeness"]:
            self.assertEqual(row["status"], "present", msg=f"category {row['category']}")


# ---------------------------------------------------------------------------
# QMS attestation (Article 17)
# ---------------------------------------------------------------------------


class TestQmsAttestation(unittest.TestCase):
    def test_008_missing_internal_audit_plan_warns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            types = [t for t in _full_bundle_artifact_types() if t != "internal-audit-plan"]
            bundle_dir = _write_bundle(Path(tmpdir), types)
            result = plugin.assess_conformity_procedure({
                "system_description": _system(),
                "provider_identity": _eu_provider(),
                "procedure_requested": "annex-vi-internal-control",
                "evidence_bundle_ref": str(bundle_dir),
                "enrich_with_crosswalk": False,
            })
        self.assertEqual(result["qms_attestation"]["status"], "gaps-present")
        self.assertIn("internal-audit-plan", result["qms_attestation"]["missing_artifact_types"])
        self.assertTrue(any(
            "Art. 17 QMS" in w and "internal-audit" in w
            for w in result["warnings"]
        ))


# ---------------------------------------------------------------------------
# Declaration of conformity (Article 47)
# ---------------------------------------------------------------------------


class TestDeclarationOfConformity(unittest.TestCase):
    def test_009_declaration_populated_from_inputs(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
            "reviewed_by": "Zola Valashiya",
            "enrich_with_crosswalk": False,
        })
        doc = result["declaration_of_conformity_draft"]
        self.assertEqual(doc["provider_legal_name"], "Acme Healthcare AI BV")
        self.assertEqual(doc["system_id"], "AISYS-001")
        self.assertEqual(doc["signatory"], "Zola Valashiya")
        self.assertEqual(doc["template_status"], "DRAFT_REQUIRES_PROVIDER_SIGNATURE")
        self.assertIn("EU AI Act, Article 47, Paragraph 1", doc["citations"])

    def test_010_missing_signatory_warns(self):
        provider = _eu_provider()
        result = plugin.assess_conformity_procedure({
            "system_description": _system(),
            "provider_identity": provider,
            "procedure_requested": "annex-vi-internal-control",
            "enrich_with_crosswalk": False,
        })
        self.assertTrue(any(
            "missing signatory" in w for w in result["warnings"]
        ))


# ---------------------------------------------------------------------------
# CE marking (Article 48)
# ---------------------------------------------------------------------------


class TestCeMarking(unittest.TestCase):
    def test_011_ce_marking_location_not_specified_warns(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
            "enrich_with_crosswalk": False,
        })
        self.assertTrue(any(
            "CE marking location not specified" in w for w in result["warnings"]
        ))

    def test_012_notified_body_id_missing_warns_for_art_48(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(annex_iii="1-biometrics"),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vii-notified-body",
            "ce_marking_location": "system",
            "notified_body": {"name": "TUV Sud", "certificate_ref": "CERT-001"},
            "enrich_with_crosswalk": False,
        })
        self.assertTrue(any(
            "Article 48, Paragraph 3" in w for w in result["warnings"]
        ))


# ---------------------------------------------------------------------------
# Registration (Article 49)
# ---------------------------------------------------------------------------


class TestRegistration(unittest.TestCase):
    def test_013_registration_required_but_missing_blocks(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(annex_iii="4-employment"),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
            "ce_marking_location": "system",
            "enrich_with_crosswalk": False,
        })
        self.assertEqual(result["registration_check"]["status"], "missing")
        self.assertTrue(any(
            "Art. 49 registration required" in w for w in result["warnings"]
        ))

    def test_014_critical_infrastructure_exempt(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(annex_iii="2-critical-infrastructure"),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
            "enrich_with_crosswalk": False,
        })
        self.assertEqual(result["registration_check"]["status"], "not-required")

    def test_015_law_enforcement_registration_restricted(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(annex_iii="6-law-enforcement"),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
            "registration_status": {
                "eu_database_entry_id": "EU-DB-LE-001",
                "registration_date": "2026-04-01",
            },
            "enrich_with_crosswalk": False,
        })
        self.assertEqual(result["registration_check"]["public_or_restricted"], "restricted")


# ---------------------------------------------------------------------------
# Surveillance
# ---------------------------------------------------------------------------


class TestSurveillance(unittest.TestCase):
    def test_016_surveillance_with_previous_assessment(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
            "previous_assessment_ref": "ASSESS-2025-0001",
            "enrich_with_crosswalk": False,
        })
        self.assertIsNotNone(result["surveillance_check"])
        self.assertEqual(result["surveillance_check"]["status"], "surveillance-mode")
        self.assertEqual(
            result["surveillance_check"]["previous_assessment_ref"],
            "ASSESS-2025-0001",
        )


# ---------------------------------------------------------------------------
# ValueError paths
# ---------------------------------------------------------------------------


class TestValidationErrors(unittest.TestCase):
    def test_017_missing_system_description_raises(self):
        with self.assertRaises(ValueError) as cm:
            plugin.assess_conformity_procedure({
                "provider_identity": _eu_provider(),
                "procedure_requested": "annex-vi-internal-control",
            })
        self.assertIn("system_description", str(cm.exception))

    def test_018_missing_provider_identity_raises(self):
        with self.assertRaises(ValueError) as cm:
            plugin.assess_conformity_procedure({
                "system_description": _system(),
                "procedure_requested": "annex-vi-internal-control",
            })
        self.assertIn("provider_identity", str(cm.exception))

    def test_019_missing_procedure_requested_raises(self):
        with self.assertRaises(ValueError) as cm:
            plugin.assess_conformity_procedure({
                "system_description": _system(),
                "provider_identity": _eu_provider(),
            })
        self.assertIn("procedure_requested", str(cm.exception))

    def test_020_invalid_procedure_enum_raises(self):
        with self.assertRaises(ValueError) as cm:
            plugin.assess_conformity_procedure({
                "system_description": _system(),
                "provider_identity": _eu_provider(),
                "procedure_requested": "made-up-procedure",
            })
        self.assertIn("procedure_requested", str(cm.exception))

    def test_021_invalid_annex_iii_category_raises(self):
        with self.assertRaises(ValueError) as cm:
            plugin.assess_conformity_procedure({
                "system_description": _system(annex_iii="9-impossible"),
                "provider_identity": _eu_provider(),
                "procedure_requested": "annex-vi-internal-control",
            })
        self.assertIn("annex_iii_category", str(cm.exception))


# ---------------------------------------------------------------------------
# Crosswalk enrichment
# ---------------------------------------------------------------------------


class TestCrosswalk(unittest.TestCase):
    def test_022_crosswalk_default_true_emits_cross_framework_citations(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
        })
        self.assertIn("cross_framework_citations", result)
        self.assertIsInstance(result["cross_framework_citations"], list)
        # At least one Annex IV mapping should surface.
        self.assertTrue(any(
            "Annex IV" in (row.get("eu_ai_act_ref") or "")
            for row in result["cross_framework_citations"]
        ))

    def test_023_crosswalk_false_omits_field(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
            "enrich_with_crosswalk": False,
        })
        self.assertNotIn("cross_framework_citations", result)

    def test_028_crosswalk_failure_handled_gracefully(self):
        # Force failure by monkeypatching the module loader to raise.
        original = plugin._load_crosswalk_module

        def _boom():
            raise RuntimeError("simulated crosswalk failure")

        plugin._load_crosswalk_module = _boom
        try:
            result = plugin.assess_conformity_procedure({
                "system_description": _system(),
                "provider_identity": _eu_provider(),
                "procedure_requested": "annex-vi-internal-control",
            })
            self.assertEqual(result["cross_framework_citations"], [])
            self.assertTrue(any(
                "Crosswalk enrichment skipped" in w for w in result["warnings"]
            ))
        finally:
            plugin._load_crosswalk_module = original


# ---------------------------------------------------------------------------
# Citation format and style compliance
# ---------------------------------------------------------------------------


class TestCitationFormat(unittest.TestCase):
    def test_024_citation_format_compliance(self):
        result = plugin.assess_conformity_procedure({
            "system_description": _system(),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vi-internal-control",
            "enrich_with_crosswalk": False,
        })
        accepted_prefixes = (
            "EU AI Act, Article ",
            "EU AI Act, Annex ",
        )
        for c in result["citations"]:
            self.assertTrue(
                c.startswith(accepted_prefixes),
                msg=f"citation {c!r} does not match STYLE.md prefix",
            )


class TestProhibitedContent(unittest.TestCase):
    def test_025_no_em_dash_no_emoji_no_hedging(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle_dir = _write_bundle(Path(tmpdir), _full_bundle_artifact_types())
            result = plugin.assess_conformity_procedure({
                "system_description": _system(),
                "provider_identity": _eu_provider(),
                "procedure_requested": "annex-vi-internal-control",
                "evidence_bundle_ref": str(bundle_dir),
                "ce_marking_location": "system",
                "registration_status": {
                    "eu_database_entry_id": "EU-DB-1",
                    "registration_date": "2026-04-01",
                },
                "reviewed_by": "Zola Valashiya",
                "enrich_with_crosswalk": False,
            })
        md = plugin.render_markdown(result)
        csv_text = plugin.render_csv(result)
        for output in (md, csv_text):
            self.assertNotIn("\u2014", output)
            for hedge in (
                "may want to consider",
                "might be helpful to",
                "could potentially",
                "it is possible that",
                "you might find",
            ):
                self.assertNotIn(hedge, output.lower())


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class TestRendering(unittest.TestCase):
    def _result_with_notified_body(self):
        return plugin.assess_conformity_procedure({
            "system_description": _system(annex_iii="1-biometrics"),
            "provider_identity": _eu_provider(),
            "procedure_requested": "annex-vii-notified-body",
            "notified_body": {
                "body_id": "NB-1234",
                "name": "TUV Sud",
                "certificate_ref": "CERT-2026-001",
            },
            "ce_marking_location": "system",
            "registration_status": {
                "eu_database_entry_id": "EU-DB-1",
                "registration_date": "2026-04-01",
            },
            "enrich_with_crosswalk": False,
        })

    def test_026_markdown_has_required_sections(self):
        result = self._result_with_notified_body()
        md = plugin.render_markdown(result)
        for section in (
            "## Procedure applicability",
            "## Annex IV completeness",
            "## QMS attestation",
            "## Notified body check",
            "## Declaration of conformity",
            "## CE marking",
            "## Registration",
            "## Warnings",
        ):
            self.assertIn(section, md, msg=f"missing section {section!r}")

    def test_027_csv_row_count_matches_annex_iv_completeness(self):
        result = self._result_with_notified_body()
        csv_text = plugin.render_csv(result)
        lines = [line for line in csv_text.splitlines() if line.strip()]
        # Header + one row per Annex IV category.
        self.assertEqual(
            len(lines) - 1,
            len(result["annex_iv_completeness"]),
        )
        self.assertEqual(lines[0].split(",")[0], "category")


if __name__ == "__main__":
    unittest.main(verbosity=2)
