"""Tests for certification-readiness plugin. Runs under pytest or standalone."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


# ---------------------------------------------------------------------------
# Synthetic-bundle helpers
# ---------------------------------------------------------------------------


_STANDARD_CITATIONS = {
    "ISO/IEC 42001:2023, Clause 6.1.2",
    "ISO/IEC 42001:2023, Clause 6.1.3",
    "ISO/IEC 42001:2023, Clause 9.2",
    "ISO/IEC 42001:2023, Clause 9.3",
    "ISO/IEC 42001:2023, Clause 10.2",
}

_EU_CITATIONS = {
    "EU AI Act, Article 9",
    "EU AI Act, Article 10",
    "EU AI Act, Article 12",
    "EU AI Act, Article 17",
    "EU AI Act, Article 25",
    "EU AI Act, Article 27",
    "EU AI Act, Article 43",
}


# Artifact type to filename substring mapping (must match evidence-bundle-packager
# classification table).
_TYPE_TO_FILENAME = {
    "ai-system-inventory": "ai-system-inventory.json",
    "role-matrix": "role-matrix.json",
    "risk-register": "risk-register.json",
    "soa": "soa.json",
    "audit-log-entry": "audit-log-entry.json",
    "aisia": "aisia.json",
    "nonconformity-register": "nonconformity-register.json",
    "management-review-package": "management-review-package.json",
    "internal-audit-plan": "internal-audit-plan.json",
    "metrics-report": "metrics-report.json",
    "gap-assessment": "gap-assessment.json",
    "data-register": "data-register.json",
    "applicability-check": "applicability-check.json",
    "high-risk-classification": "high-risk-classification.json",
    "atrs-record": "atrs-record.json",
    "colorado-compliance-record": "colorado-compliance-record.json",
    "nyc-ll144-audit-package": "nyc-ll144-audit-package.json",
    "magf-assessment": "magf-assessment.json",
}


_TYPE_TO_PLUGIN = {
    "ai-system-inventory": "ai-system-inventory-maintainer",
    "role-matrix": "role-matrix-generator",
    "risk-register": "risk-register-builder",
    "soa": "soa-generator",
    "audit-log-entry": "audit-log-generator",
    "aisia": "aisia-runner",
    "nonconformity-register": "nonconformity-tracker",
    "management-review-package": "management-review-packager",
    "internal-audit-plan": "internal-audit-planner",
    "metrics-report": "metrics-collector",
    "gap-assessment": "gap-assessment",
    "data-register": "data-register-builder",
    "applicability-check": "applicability-checker",
    "high-risk-classification": "high-risk-classifier",
    "atrs-record": "uk-atrs-recorder",
    "colorado-compliance-record": "colorado-ai-act-compliance",
    "nyc-ll144-audit-package": "nyc-ll144-audit-packager",
    "magf-assessment": "singapore-magf-assessor",
}


def _artifact_json(artifact_type: str, *, extras: dict | None = None, warnings: list | None = None, citations: list | None = None) -> dict:
    base_citations = citations if citations is not None else _default_citations_for(artifact_type)
    data = {
        "timestamp": "2026-04-18T00:00:00Z",
        "agent_signature": f"{_TYPE_TO_PLUGIN[artifact_type]}/0.1.0",
        "citations": base_citations,
        "warnings": warnings or [],
    }
    if extras:
        data.update(extras)
    return data


def _default_citations_for(artifact_type: str) -> list[str]:
    mapping = {
        "soa": ["ISO/IEC 42001:2023, Clause 6.1.3", "ISO/IEC 42001:2023, Annex A, Control A.2.2"],
        "risk-register": ["ISO/IEC 42001:2023, Clause 6.1.2", "EU AI Act, Article 9"],
        "aisia": ["ISO/IEC 42001:2023, Clause 6.1.2", "EU AI Act, Article 27"],
        "audit-log-entry": ["ISO/IEC 42001:2023, Clause 7.5.3", "EU AI Act, Article 12"],
        "data-register": ["ISO/IEC 42001:2023, Annex A, Control A.7.2", "EU AI Act, Article 10"],
        "internal-audit-plan": ["ISO/IEC 42001:2023, Clause 9.2"],
        "management-review-package": ["ISO/IEC 42001:2023, Clause 9.3"],
        "nonconformity-register": ["ISO/IEC 42001:2023, Clause 10.2"],
        "metrics-report": ["MEASURE 2.7"],
        "gap-assessment": ["ISO/IEC 42001:2023, Clause 6.1.2"],
        "role-matrix": ["ISO/IEC 42001:2023, Annex A, Control A.3.2"],
        "ai-system-inventory": ["ISO/IEC 42001:2023, Clause 4.3"],
        "high-risk-classification": ["EU AI Act, Article 6", "EU AI Act, Article 17"],
        "colorado-compliance-record": ["Colorado SB 205, Section 6-1-1703(2)"],
        "nyc-ll144-audit-package": ["NYC LL144 Final Rule, Section 5-301"],
        "magf-assessment": ["Singapore MAGF 2e, Pillar Internal Governance Structures and Measures"],
        "atrs-record": ["UK ATRS, Section Tool description"],
    }
    return mapping.get(artifact_type, [])


def _build_bundle(
    tmp_root: Path,
    artifact_types: list[str],
    *,
    bundle_id: str = "test-bundle-001",
    artifact_overrides: dict | None = None,
    extra_citations: list[str] | None = None,
) -> Path:
    """Build a synthetic evidence bundle directory. Returns the bundle path."""
    bundle_dir = tmp_root / bundle_id
    artifacts_dir = bundle_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    artifact_overrides = artifact_overrides or {}
    manifest_artifacts: list[dict] = []
    all_citations: set[str] = set()

    for atype in artifact_types:
        plugin_name = _TYPE_TO_PLUGIN[atype]
        filename = _TYPE_TO_FILENAME[atype]
        plugin_dir = artifacts_dir / plugin_name
        plugin_dir.mkdir(parents=True, exist_ok=True)

        override = artifact_overrides.get(atype, {})
        artifact = _artifact_json(
            atype,
            extras=override.get("extras"),
            warnings=override.get("warnings"),
            citations=override.get("citations"),
        )
        path = plugin_dir / filename
        path.write_text(json.dumps(artifact, sort_keys=True, indent=2), encoding="utf-8")
        all_citations.update(artifact.get("citations", []))

        manifest_artifacts.append({
            "path": f"artifacts/{plugin_name}/{filename}",
            "plugin": plugin_name,
            "artifact_type": atype,
            "agent_signature": artifact["agent_signature"],
            "sha256": "0" * 64,
            "size_bytes": path.stat().st_size,
            "emitted_at": artifact["timestamp"],
        })

    if extra_citations:
        all_citations.update(extra_citations)

    manifest = {
        "bundle_schema_version": "1.0.0",
        "bundle_id": bundle_id,
        "generated_at": "2026-04-18T00:00:00Z",
        "generated_by": "evidence-bundle-packager/0.1.0",
        "scope": {
            "organization": "Test Org",
            "aims_boundary": "All test AI systems",
            "systems_in_scope": ["SYS-001"],
            "reporting_period_start": "2026-01-01",
            "reporting_period_end": "2026-03-31",
            "intended_recipient": "external-auditor",
        },
        "artifact_count": len(manifest_artifacts),
        "artifacts": manifest_artifacts,
        "included_plugins": sorted({a["plugin"] for a in manifest_artifacts}),
        "missing_plugins": [],
        "citations_unique_count": len(all_citations),
        "crosswalk_files_included": [],
    }
    (bundle_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8"
    )

    # citation-summary.md: the plugin parses numbered lines under each section.
    sorted_cits = sorted(all_citations)
    summary_lines = [
        "# Citation Summary",
        "",
        "## Citations by framework",
        "",
        "### All",
        "",
    ]
    for i, c in enumerate(sorted_cits, 1):
        summary_lines.append(f"{i}. {c}")
    summary_lines.append("")
    (bundle_dir / "citation-summary.md").write_text(
        "\n".join(summary_lines), encoding="utf-8"
    )
    return bundle_dir


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


_ISO_STAGE1_TYPES = [
    "ai-system-inventory", "role-matrix", "risk-register", "soa",
    "audit-log-entry", "aisia", "management-review-package",
    "gap-assessment", "internal-audit-plan",
]

_ISO_STAGE2_TYPES = _ISO_STAGE1_TYPES + ["nonconformity-register", "metrics-report"]

_EU_INTERNAL_TYPES = [
    "aisia", "risk-register", "data-register", "audit-log-entry",
    "soa", "high-risk-classification",
]


class BundleTempCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# 1. Happy path iso42001-stage1
# ---------------------------------------------------------------------------


def test_iso42001_stage1_happy_path_ready_with_high_confidence():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        bundle = _build_bundle(
            tmp_root, _ISO_STAGE1_TYPES,
            extra_citations=list(_STANDARD_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
        })
        assert report["readiness_level"] == "ready-with-high-confidence", report
        assert report["summary"]["blocker_count"] == 0
        assert report["summary"]["gap_count"] == 0


# ---------------------------------------------------------------------------
# 2. Happy path iso42001-stage2 with completed internal audit
# ---------------------------------------------------------------------------


def test_iso42001_stage2_with_completed_cycle():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        overrides = {
            "internal-audit-plan": {
                "extras": {
                    "audit_schedule": [{"cycle_id": "C1", "cycle_status": "completed"}],
                },
            },
        }
        bundle = _build_bundle(
            tmp_root, _ISO_STAGE2_TYPES,
            artifact_overrides=overrides,
            extra_citations=list(_STANDARD_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage2",
        })
        assert report["readiness_level"] == "ready-with-high-confidence", report
        assert report["summary"]["blocker_count"] == 0


# ---------------------------------------------------------------------------
# 3. Partially-ready: stage1 missing aisia
# ---------------------------------------------------------------------------


def test_iso42001_stage1_missing_aisia_yields_blocker_not_ready():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        types = [t for t in _ISO_STAGE1_TYPES if t != "aisia"]
        bundle = _build_bundle(
            tmp_root, types, extra_citations=list(_STANDARD_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
        })
        # aisia is critical in iso42001-stage1 required list -> blocker.
        assert report["readiness_level"] == "not-ready"
        blocker_keys = [b["gap_key"] for b in report["blockers"]]
        assert "missing-aisia" in blocker_keys


# ---------------------------------------------------------------------------
# 4. Not-ready: missing risk-register + soa
# ---------------------------------------------------------------------------


def test_not_ready_missing_risk_register_and_soa():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        types = [t for t in _ISO_STAGE1_TYPES if t not in ("risk-register", "soa")]
        bundle = _build_bundle(tmp_root, types, extra_citations=list(_STANDARD_CITATIONS))
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
        })
        assert report["readiness_level"] == "not-ready"
        keys = {b["gap_key"] for b in report["blockers"]}
        assert "missing-risk-register" in keys
        assert "missing-soa" in keys


# ---------------------------------------------------------------------------
# 5. Ready with conditions: warnings on role-matrix
# ---------------------------------------------------------------------------


def test_ready_with_conditions_when_warnings_on_role_matrix():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        overrides = {
            "role-matrix": {"warnings": ["one role missing owner"]},
        }
        bundle = _build_bundle(
            tmp_root, _ISO_STAGE1_TYPES,
            artifact_overrides=overrides,
            extra_citations=list(_STANDARD_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
        })
        assert report["readiness_level"] == "ready-with-conditions", report
        assert report["summary"]["condition_count"] >= 1


# ---------------------------------------------------------------------------
# 6. EU AI Act internal-control happy path
# ---------------------------------------------------------------------------


def test_eu_ai_act_internal_control_happy_path():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        overrides = {
            "aisia": {
                "extras": {"fria_complete": True},
                "citations": ["EU AI Act, Article 27"],
            },
            "high-risk-classification": {
                "extras": {
                    "requires_legal_review": False,
                    "risk_tier": "high-risk",
                },
                "citations": ["EU AI Act, Article 6"],
            },
        }
        bundle = _build_bundle(
            tmp_root, _EU_INTERNAL_TYPES,
            artifact_overrides=overrides,
            extra_citations=list(_EU_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "eu-ai-act-internal-control",
        })
        assert report["readiness_level"] == "ready-with-high-confidence", report


# ---------------------------------------------------------------------------
# 7. EU AI Act internal-control with requires_legal_review=True
# ---------------------------------------------------------------------------


def test_eu_ai_act_internal_control_legal_review_pending():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        overrides = {
            "high-risk-classification": {
                "extras": {"requires_legal_review": True},
            },
        }
        bundle = _build_bundle(
            tmp_root, _EU_INTERNAL_TYPES,
            artifact_overrides=overrides,
            extra_citations=list(_EU_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "eu-ai-act-internal-control",
        })
        assert report["readiness_level"] == "partially-ready", report
        gap_keys = {g["gap_key"] for g in report["gaps"]}
        assert "legal-review-pending" in gap_keys


# ---------------------------------------------------------------------------
# 8. Colorado SB 205 safe-harbor happy path
# ---------------------------------------------------------------------------


def test_colorado_sb205_safe_harbor_happy_path():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        overrides = {
            "colorado-compliance-record": {
                "extras": {"actor_conformance_frameworks": ["iso42001"]},
            },
            "high-risk-classification": {
                "extras": {
                    "requires_legal_review": False,
                    "sb205_assessment": {"section_6_1_1706_3_applies": True},
                },
            },
        }
        types = [
            "high-risk-classification", "colorado-compliance-record",
            "aisia", "soa", "risk-register", "audit-log-entry",
        ]
        bundle = _build_bundle(
            tmp_root, types, artifact_overrides=overrides,
            extra_citations=["Colorado SB 205, Section 6-1-1706(3)"],
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "colorado-sb205-safe-harbor",
        })
        assert report["readiness_level"] in ("ready-with-high-confidence", "ready-with-conditions"), report
        assert report["summary"]["blocker_count"] == 0


# ---------------------------------------------------------------------------
# 9. Colorado SB 205 with no conformance claim -> not-ready
# ---------------------------------------------------------------------------


def test_colorado_sb205_no_conformance_not_ready():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        overrides = {
            "colorado-compliance-record": {
                "extras": {"actor_conformance_frameworks": []},
            },
            "high-risk-classification": {
                "extras": {"sb205_assessment": {"section_6_1_1706_3_applies": False}},
            },
        }
        types = [
            "high-risk-classification", "colorado-compliance-record",
            "aisia", "soa", "risk-register", "audit-log-entry",
        ]
        bundle = _build_bundle(
            tmp_root, types, artifact_overrides=overrides,
            extra_citations=["Colorado SB 205, Section 6-1-1706(3)"],
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "colorado-sb205-safe-harbor",
        })
        assert report["readiness_level"] == "not-ready", report
        keys = {b["gap_key"] for b in report["blockers"]}
        assert "sb205-conformance-missing" in keys


# ---------------------------------------------------------------------------
# 10. NYC LL144 with imminent re-audit -> ready-with-conditions
# ---------------------------------------------------------------------------


def test_nyc_ll144_imminent_reaudit_condition():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        imminent_date = (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat()
        overrides = {
            "nyc-ll144-audit-package": {
                "extras": {
                    "summary": {"next_audit_due_by": imminent_date},
                },
            },
        }
        bundle = _build_bundle(
            tmp_root, ["nyc-ll144-audit-package"],
            artifact_overrides=overrides,
            extra_citations=["NYC LL144"],
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "nyc-ll144-annual-audit",
        })
        assert report["readiness_level"] == "ready-with-conditions", report
        cond_keys = {c["gap_key"] for c in report["conditions"]}
        assert "imminent-reaudit-due" in cond_keys


# ---------------------------------------------------------------------------
# 11. Singapore MAGF alignment happy path
# ---------------------------------------------------------------------------


def test_singapore_magf_alignment_happy_path():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        bundle = _build_bundle(
            tmp_root, ["magf-assessment"],
            extra_citations=[
                "Singapore MAGF 2e, Pillar Internal Governance Structures and Measures",
            ],
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "singapore-magf-alignment",
        })
        assert report["readiness_level"] == "ready-with-high-confidence", report


# ---------------------------------------------------------------------------
# 12. UK ATRS Tier 1 populated happy path
# ---------------------------------------------------------------------------


def test_uk_atrs_publication_happy_path():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        overrides = {
            "atrs-record": {
                "extras": {
                    "sections": {
                        "owner_and_contact": "Department X",
                        "tool_description": "Classifier",
                        "tool_details": "model v1",
                        "impact_assessment": "medium",
                    },
                },
            },
        }
        bundle = _build_bundle(
            tmp_root, ["atrs-record"],
            artifact_overrides=overrides,
            extra_citations=["UK ATRS, Section Tool description"],
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "uk-atrs-publication",
        })
        assert report["readiness_level"] == "ready-with-high-confidence", report


# ---------------------------------------------------------------------------
# 13-16. Validation errors
# ---------------------------------------------------------------------------


def test_valueerror_on_missing_bundle_path():
    try:
        plugin.assess_readiness({"target_certification": "iso42001-stage1"})
    except ValueError as exc:
        assert "bundle_path" in str(exc)
        return
    raise AssertionError("ValueError not raised")


def test_valueerror_on_missing_target_certification():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            plugin.assess_readiness({"bundle_path": tmp})
        except ValueError as exc:
            assert "target_certification" in str(exc)
            return
    raise AssertionError("ValueError not raised")


def test_valueerror_on_invalid_target_certification():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            plugin.assess_readiness({
                "bundle_path": tmp,
                "target_certification": "invalid-target",
            })
        except ValueError as exc:
            assert "target_certification" in str(exc)
            return
    raise AssertionError("ValueError not raised")


def test_valueerror_on_bundle_path_not_a_directory():
    with tempfile.NamedTemporaryFile() as tmpf:
        try:
            plugin.assess_readiness({
                "bundle_path": tmpf.name,
                "target_certification": "iso42001-stage1",
            })
        except ValueError as exc:
            assert "directory" in str(exc)
            return
    raise AssertionError("ValueError not raised")


# ---------------------------------------------------------------------------
# 17. Warning when MANIFEST.json absent
# ---------------------------------------------------------------------------


def test_warning_when_manifest_absent():
    with tempfile.TemporaryDirectory() as tmp:
        # tmp exists but has no MANIFEST.json.
        report = plugin.assess_readiness({
            "bundle_path": tmp,
            "target_certification": "iso42001-stage1",
        })
        assert report["readiness_level"] == "not-ready"
        assert any("MANIFEST.json is absent" in w for w in report["warnings"])


# ---------------------------------------------------------------------------
# 18. strict_mode elevates warnings to blockers
# ---------------------------------------------------------------------------


def test_strict_mode_elevates_warnings_to_blockers():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        overrides = {
            "soa": {"warnings": ["one control lacks justification"]},
        }
        bundle = _build_bundle(
            tmp_root, _ISO_STAGE1_TYPES,
            artifact_overrides=overrides,
            extra_citations=list(_STANDARD_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
            "scope_overrides": {"strict_mode": True},
        })
        assert report["readiness_level"] == "not-ready", report
        # The soa warning should appear as a blocker in strict mode.
        assert report["summary"]["blocker_count"] >= 1


# ---------------------------------------------------------------------------
# 19. Remediation entries populate target_plugin
# ---------------------------------------------------------------------------


def test_remediation_entries_have_target_plugin():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        types = [t for t in _ISO_STAGE1_TYPES if t != "aisia"]
        bundle = _build_bundle(
            tmp_root, types, extra_citations=list(_STANDARD_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
        })
        assert report["remediations"], "expected at least one remediation"
        for r in report["remediations"]:
            assert r["target_plugin"], f"target_plugin empty for {r}"


# ---------------------------------------------------------------------------
# 20. Citation verification: missing expected citation -> gap
# ---------------------------------------------------------------------------


def test_citation_verification_missing_expected_citation_yields_gap():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        # Use a minimal citation set that does NOT include Clause 9.2.
        bundle = _build_bundle(
            tmp_root, _ISO_STAGE1_TYPES,
            extra_citations=["ISO/IEC 42001:2023, Clause 6.1.2"],
            artifact_overrides={
                atype: {"citations": ["ISO/IEC 42001:2023, Clause 6.1.2"]}
                for atype in _ISO_STAGE1_TYPES
            },
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
        })
        gap_keys = [g.get("gap_key") for g in report["gaps"]]
        assert "missing-citation" in gap_keys
        missing_cits = [g.get("citation") for g in report["gaps"] if g.get("gap_key") == "missing-citation"]
        assert any("Clause 9.2" in c for c in missing_cits)


# ---------------------------------------------------------------------------
# 21. Markdown contains the legal disclaimer callout
# ---------------------------------------------------------------------------


def test_markdown_contains_legal_disclaimer():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        bundle = _build_bundle(
            tmp_root, _ISO_STAGE1_TYPES,
            extra_citations=list(_STANDARD_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
        })
        md = plugin.render_markdown(report)
        assert "> This readiness report is informational." in md
        assert "qualified auditor or notified body" in md


# ---------------------------------------------------------------------------
# 22. CSV row count matches gaps + blockers + conditions + remediations
# ---------------------------------------------------------------------------


def test_csv_row_count_matches_gaps_blockers_conditions_remediations():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        # Missing aisia -> 1 blocker, 1 remediation, + any missing citations.
        types = [t for t in _ISO_STAGE1_TYPES if t != "aisia"]
        bundle = _build_bundle(
            tmp_root, types, extra_citations=list(_STANDARD_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
        })
        csv_text = plugin.render_csv(report)
        lines = [l for l in csv_text.splitlines() if l.strip()]
        # header + all entries.
        expected = 1 + len(report["blockers"]) + len(report["gaps"]) + len(report["conditions"]) + len(report["remediations"])
        assert len(lines) == expected


# ---------------------------------------------------------------------------
# 23. No em-dash, emoji, or hedging in rendered output
# ---------------------------------------------------------------------------


def test_no_em_dash_or_emoji_in_rendered_output():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        types = [t for t in _ISO_STAGE1_TYPES if t != "aisia"]
        bundle = _build_bundle(
            tmp_root, types, extra_citations=list(_STANDARD_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
        })
        md = plugin.render_markdown(report)
        csv_text = plugin.render_csv(report)
        assert "\u2014" not in md
        assert "\u2014" not in csv_text
        # Check for emoji/hedging phrases.
        hedging = ["may want to consider", "might be helpful to", "could potentially"]
        for phrase in hedging:
            assert phrase not in md.lower()
            assert phrase not in csv_text.lower()


# ---------------------------------------------------------------------------
# 24. Citation format compliance
# ---------------------------------------------------------------------------


def test_citation_format_compliance():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        bundle = _build_bundle(
            tmp_root, _ISO_STAGE1_TYPES,
            extra_citations=list(_STANDARD_CITATIONS),
        )
        report = plugin.assess_readiness({
            "bundle_path": str(bundle),
            "target_certification": "iso42001-stage1",
        })
        valid_prefixes = (
            "ISO/IEC 42001:2023, ",
            "ISO 42001, ",
            "EU AI Act, ",
            "NYC LL144",
            "Colorado SB 205, ",
            "UK ATRS, ",
            "Singapore MAGF ",
            "GOVERN ", "MAP ", "MEASURE ", "MANAGE ",
        )
        for c in report["citations"]:
            assert c.startswith(valid_prefixes), f"citation {c!r} has unexpected prefix"


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------


def _run_all():
    import inspect
    tests = [(n, o) for n, o in inspect.getmembers(sys.modules[__name__])
             if n.startswith("test_") and callable(o)]
    failures = []
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:
            failures.append((name, f"{type(exc).__name__}: {exc}"))
    print(f"Ran {len(tests)} tests: {len(tests) - len(failures)} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
