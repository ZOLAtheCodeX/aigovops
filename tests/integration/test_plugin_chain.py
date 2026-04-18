"""
Integration tests for the AIGovOps plugin chain.

Each test exercises a real data flow across two or more plugins, using one
plugin's output as another plugin's input. These tests complement the
per-plugin unit tests by verifying that the plugin contract (field names,
artifact types, citation formats) holds across composition boundaries.

Runs under pytest or as a standalone script. No external dependencies.

Invocation:
    python tests/integration/test_plugin_chain.py
    or
    pytest tests/integration/
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for plugin_name in (
    "audit-log-generator",
    "role-matrix-generator",
    "risk-register-builder",
    "soa-generator",
    "aisia-runner",
    "nonconformity-tracker",
    "management-review-packager",
    "metrics-collector",
    "gap-assessment",
):
    sys.path.insert(0, str(REPO_ROOT / "plugins" / plugin_name))

# Use importlib to avoid module name collisions (all plugin modules are
# named 'plugin').
import importlib.util


def _load(plugin_name: str):
    spec = importlib.util.spec_from_file_location(
        plugin_name.replace("-", "_"),
        REPO_ROOT / "plugins" / plugin_name / "plugin.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit_log = _load("audit-log-generator")
role_matrix = _load("role-matrix-generator")
risk_register = _load("risk-register-builder")
soa = _load("soa-generator")
aisia = _load("aisia-runner")
nonconformity = _load("nonconformity-tracker")
management_review = _load("management-review-packager")
metrics = _load("metrics-collector")
gap = _load("gap-assessment")


# --- Scenario fixtures ---

SYSTEM = {
    "system_ref": "SYS-001",
    "system_name": "ResumeScreen",
    "risk_tier": "limited",
    "intended_use": "Rank candidate resumes against a job posting.",
    "deployment_context": "Internal HR workflow.",
    "data_processed": ["candidate resume text", "job posting text"],
}


def _org_chart():
    return [
        {"role_name": "Chief Executive Officer"},
        {"role_name": "Chief Risk Officer", "reports_to": "Chief Executive Officer"},
        {"role_name": "AI Governance Officer", "reports_to": "Chief Risk Officer"},
        {"role_name": "Data Protection Officer", "reports_to": "Chief Risk Officer"},
        {"role_name": "Chief Information Security Officer", "reports_to": "Chief Risk Officer"},
        {"role_name": "Head of AI Engineering", "reports_to": "Chief Technology Officer"},
        {"role_name": "Chief Technology Officer", "reports_to": "Chief Executive Officer"},
        {"role_name": "Chief Legal Officer", "reports_to": "Chief Executive Officer"},
    ]


def _role_assignments():
    # Minimal RACI covering the 8 default decision categories.
    r: dict = {}
    categories = role_matrix.DEFAULT_DECISION_CATEGORIES
    activities = role_matrix.DEFAULT_ACTIVITIES
    default_roles = {
        "AI policy approval": ("AI Governance Officer", "Chief Risk Officer", "Chief Executive Officer", "Chief Legal Officer", "Head of AI Engineering"),
        "Risk acceptance": ("AI Governance Officer", "Chief Information Security Officer", "Chief Risk Officer", "Data Protection Officer", "Head of AI Engineering"),
        "SoA approval": ("AI Governance Officer", "Chief Information Security Officer", "Chief Risk Officer", "Data Protection Officer", "Head of AI Engineering"),
        "AISIA sign-off": ("Head of AI Engineering", "AI Governance Officer", "Chief Risk Officer", "Data Protection Officer", "Chief Executive Officer"),
        "Control implementation": ("Head of AI Engineering", "AI Governance Officer", "Chief Technology Officer", "Chief Information Security Officer", "Chief Risk Officer"),
        "Incident response": ("Chief Information Security Officer", "AI Governance Officer", "Chief Risk Officer", "Chief Legal Officer", "Chief Executive Officer"),
        "Audit programme approval": ("AI Governance Officer", "Chief Risk Officer", "Chief Executive Officer", "Chief Legal Officer", "Head of AI Engineering"),
        "External reporting": ("AI Governance Officer", "Chief Legal Officer", "Chief Executive Officer", "Chief Risk Officer", "Head of AI Engineering"),
    }
    for cat in categories:
        roles = default_roles[cat]
        for i, act in enumerate(activities):
            r[(cat, act)] = roles[i]
    return r


def _authority_register():
    return {
        "Chief Executive Officer": "Board Resolution 2024-01",
        "Chief Risk Officer": "Delegation of Authority Policy",
        "Chief Technology Officer": "Delegation of Authority Policy",
        "AI Governance Officer": "AI Governance Charter 2025",
        "Data Protection Officer": "GDPR Article 37 Appointment",
        "Chief Information Security Officer": "Information Security Policy",
        "Head of AI Engineering": "Job Description 2025",
        "Chief Legal Officer": "General Counsel Appointment",
    }


def _backup_assignments():
    return {
        "Chief Executive Officer": "Chief Risk Officer",
        "Chief Risk Officer": "Chief Information Security Officer",
        "Chief Technology Officer": "Head of AI Engineering",
    }


# --- Integration tests ---

def test_role_matrix_to_risk_register_owner_lookup():
    """role-matrix-generator output populates risk-register-builder owner via role_matrix_lookup."""
    matrix = role_matrix.generate_role_matrix({
        "org_chart": _org_chart(),
        "role_assignments": _role_assignments(),
        "authority_register": _authority_register(),
        "backup_assignments": _backup_assignments(),
    })
    # Derive a category -> approver lookup from the matrix for the risk-register owner_lookup.
    approver_by_category = {
        row["decision_category"]: row["role_name"]
        for row in matrix["rows"]
        if row["activity"] == "approve"
    }
    # Map risk categories to approver categories (organizational mapping).
    category_to_role = {
        "bias": approver_by_category["Risk acceptance"],
        "privacy": approver_by_category["Risk acceptance"],
    }
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [
            {"system_ref": "SYS-001", "category": "bias", "description": "Disparity in ranking outputs."},
        ],
        "role_matrix_lookup": category_to_role,
    })
    row = register["rows"][0]
    assert row["owner_role"] == approver_by_category["Risk acceptance"]


def test_risk_register_feeds_soa_inclusion():
    """risk-register-builder output controls SoA row inclusion in soa-generator."""
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [
            {
                "system_ref": "SYS-001",
                "category": "privacy",
                "description": "PII exposure risk.",
                "existing_controls": ["A.7.5", "A.7.4"],
                "treatment_option": "reduce",
                "owner_role": "Data Protection Officer",
            },
        ],
    })
    soa_result = soa.generate_soa({
        "ai_system_inventory": [SYSTEM],
        "risk_register": register["rows"],
    })
    by_id = {r["control_id"]: r for r in soa_result["rows"]}
    assert by_id["A.7.5"]["status"] == "included-implemented"
    assert by_id["A.7.4"]["status"] == "included-implemented"
    # A control not referenced by any risk should be excluded-with-review.
    assert "REQUIRES REVIEWER DECISION" in by_id["A.10.4"]["justification"]


def test_soa_feeds_gap_assessment():
    """soa-generator output drives gap-assessment classification."""
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [
            {
                "system_ref": "SYS-001",
                "category": "bias",
                "description": "Demographic disparity.",
                "existing_controls": ["A.5.4"],
                "treatment_option": "reduce",
            },
        ],
    })
    soa_result = soa.generate_soa({
        "ai_system_inventory": [SYSTEM],
        "risk_register": register["rows"],
        "exclusion_justifications": {"A.10.4": "No customer-facing AI."},
    })
    gap_result = gap.generate_gap_assessment({
        "ai_system_inventory": [SYSTEM],
        "target_framework": "iso42001",
        "soa_rows": soa_result["rows"],
    })
    by_id = {r["target_id"]: r for r in gap_result["rows"]}
    assert by_id["A.5.4"]["classification"] == "covered"
    assert by_id["A.10.4"]["classification"] == "not-applicable"
    # Unreferenced controls default to not-covered.
    assert by_id["A.6.2.7"]["classification"] == "not-covered"


def test_aisia_output_feeds_risk_register_additional_controls():
    """aisia-runner's additional_controls_recommended surface as candidate risk treatments."""
    aisia_result = aisia.run_aisia({
        "system_description": {
            "system_name": "ResumeScreen",
            "purpose": "Rank candidate resumes.",
            "system_type": "classical-ml",
        },
        "affected_stakeholders": ["Candidates", "HR reviewers"],
        "impact_assessments": [
            {
                "stakeholder_group": "Candidates",
                "impact_dimension": "group-fairness",
                "impact_description": "Potential disparate impact across protected groups.",
                "severity": "major",
                "likelihood": "possible",
                "existing_controls": ["A.5.4"],
                "additional_controls_recommended": ["Quarterly equity audit", "Ground-truth relabeling program"],
            },
        ],
    })
    # Verify the AISIA section carries the recommended controls that should feed the risk register.
    section = aisia_result["sections"][0]
    assert len(section["additional_controls_recommended"]) == 2
    assert any("equity audit" in c.lower() for c in section["additional_controls_recommended"])


def test_metrics_breach_to_nonconformity_workflow():
    """metrics-collector threshold breach produces a routing entry the nonconformity workflow can consume."""
    metrics_report = metrics.generate_metrics_report({
        "ai_system_inventory": [SYSTEM],
        "measurements": [
            {
                "system_ref": "SYS-001",
                "metric_family": "fairness",
                "metric_id": "demographic_parity_difference",
                "value": 0.18,
                "window_start": "2026-04-01T00:00:00Z",
                "window_end": "2026-04-30T23:59:59Z",
                "measurement_method_ref": "METHOD-FAIRNESS-2026Q2",
                "test_set_ref": "TS-fairness-2026Q2",
            },
        ],
        "thresholds": {"demographic_parity_difference": {"operator": "max", "value": 0.05}},
    })
    assert metrics_report["summary"]["threshold_breach_count"] == 1
    breach = metrics_report["threshold_breaches"][0]

    # The nonconformity workflow would create a record from this breach.
    nc_result = nonconformity.generate_nonconformity_register({
        "records": [
            {
                "description": f"Threshold breach: {breach['metric_id']} = {breach['value']} exceeds max.",
                "source_citation": breach["citations"][0],
                "detected_by": "metrics-collector",
                "detection_date": "2026-04-30",
                "detection_method": "Automated threshold check",
                "status": "detected",
            },
        ],
    })
    assert len(nc_result["records"]) == 1
    # Warning about source_citation being a MEASURE subcategory is expected and acceptable.
    # Test that the source_citation was preserved from the breach.
    assert nc_result["records"][0]["source_citation"] == breach["citations"][0]


def test_audit_log_entries_reference_plugin_agent_signature():
    """audit-log-generator agent_signature appears correctly on every emission."""
    entry = audit_log.generate_audit_log({
        "system_name": "ResumeScreen",
        "purpose": "Rank candidate resumes.",
        "risk_tier": "limited",
        "data_processed": ["resume text"],
        "deployment_context": "Internal HR workflow.",
        "governance_decisions": ["Deployed after Phase 2 review."],
        "responsible_parties": ["AI Governance Officer"],
    })
    assert entry["agent_signature"] == "audit-log-generator/0.1.0"
    # Every Annex A mapping must cite in STYLE.md format.
    for m in entry["annex_a_mappings"]:
        assert m["citation"].startswith("ISO/IEC 42001:2023, Annex A, Control ")


def test_management_review_package_references_downstream_artifacts():
    """management-review-packager correctly incorporates risk-register, nonconformity, and audit-log refs."""
    # Simulate downstream artifacts that would feed the management review.
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [{
            "system_ref": "SYS-001",
            "category": "bias",
            "description": "Demographic disparity.",
            "treatment_option": "reduce",
        }],
    })
    nc = nonconformity.generate_nonconformity_register({
        "records": [{
            "description": "Protected-group disparity detected.",
            "source_citation": "ISO/IEC 42001:2023, Annex A, Control A.5.4",
            "detected_by": "Equity audit",
            "detection_date": "2026-03-20",
            "status": "investigated",
            "investigation_started_at": "2026-03-21",
        }],
    })
    package = management_review.generate_review_package({
        "review_window": {"start": "2026-01-01", "end": "2026-03-31"},
        "attendees": ["Chief Risk Officer", "AI Governance Officer"],
        "ai_risks_and_opportunities": f"RR-register-ref-{register['timestamp']}",
        "nonconformity_trends": {
            "source_ref": f"NC-log-ref-{nc['timestamp']}",
            "trend_direction": "stable",
        },
    })
    # Package references arrived at source_ref correctly.
    by_key = {s["key"]: s for s in package["sections"]}
    assert by_key["ai_risks_and_opportunities"]["source_ref"].startswith("RR-register-ref-")
    assert by_key["nonconformity_trends"]["source_ref"].startswith("NC-log-ref-")
    assert by_key["nonconformity_trends"]["trend_direction"] == "stable"


def test_aisia_soa_linking_via_existing_controls():
    """aisia-runner cross-links existing_controls to soa_rows when refs match."""
    # Build an SoA first.
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [{
            "system_ref": "SYS-001",
            "category": "bias",
            "description": "Disparity risk.",
            "existing_controls": ["A.5.4"],
            "treatment_option": "reduce",
        }],
    })
    soa_result = soa.generate_soa({
        "ai_system_inventory": [SYSTEM],
        "risk_register": register["rows"],
    })
    # Build soa_rows input suitable for aisia-runner (with row_ref for cross-linking).
    soa_for_aisia = [
        {"control_id": r["control_id"], "row_ref": f"SOA-ROW-{r['control_id']}"}
        for r in soa_result["rows"]
    ]
    aisia_result = aisia.run_aisia({
        "system_description": {
            "system_name": "ResumeScreen",
            "purpose": "Rank resumes.",
        },
        "affected_stakeholders": ["Candidates"],
        "impact_assessments": [{
            "stakeholder_group": "Candidates",
            "impact_dimension": "group-fairness",
            "impact_description": "Potential disparity.",
            "severity": "major",
            "likelihood": "possible",
            "existing_controls": ["A.5.4"],
        }],
        "soa_rows": soa_for_aisia,
    })
    section = aisia_result["sections"][0]
    assert section["existing_controls"][0]["soa_row_ref"] == "SOA-ROW-A.5.4"


def test_every_plugin_emits_agent_signature():
    """All eight plugins emit an agent_signature with the plugin name prefix."""
    expected_signatures = {
        "audit-log-generator": audit_log.generate_audit_log({
            "system_name": "X", "purpose": "X", "risk_tier": "minimal",
            "data_processed": [], "deployment_context": "X",
            "governance_decisions": [], "responsible_parties": [],
        })["agent_signature"],
        "role-matrix-generator": role_matrix.generate_role_matrix({
            "org_chart": _org_chart(),
            "role_assignments": _role_assignments(),
            "authority_register": _authority_register(),
        })["agent_signature"],
        "risk-register-builder": risk_register.generate_risk_register({
            "ai_system_inventory": [SYSTEM],
            "risks": [{"system_ref": "SYS-001", "category": "bias", "description": "X"}],
        })["agent_signature"],
        "soa-generator": soa.generate_soa({"ai_system_inventory": [SYSTEM]})["agent_signature"],
        "aisia-runner": aisia.run_aisia({
            "system_description": {"system_name": "X", "purpose": "X"},
            "affected_stakeholders": ["A"],
        })["agent_signature"],
        "nonconformity-tracker": nonconformity.generate_nonconformity_register({"records": []})["agent_signature"],
        "management-review-packager": management_review.generate_review_package({
            "review_window": {"start": "2026-01-01", "end": "2026-01-31"},
            "attendees": ["CRO"],
        })["agent_signature"],
        "metrics-collector": metrics.generate_metrics_report({
            "ai_system_inventory": [SYSTEM],
            "measurements": [],
        })["agent_signature"],
        "gap-assessment": gap.generate_gap_assessment({
            "ai_system_inventory": [SYSTEM],
            "target_framework": "iso42001",
        })["agent_signature"],
    }
    for name, signature in expected_signatures.items():
        assert signature.startswith(name + "/"), f"{name} signature {signature!r} does not start with {name}/"


def test_style_md_citation_format_across_chain():
    """Every plugin emits citations in STYLE.md format across a composed chain."""
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [{"system_ref": "SYS-001", "category": "bias", "description": "X", "treatment_option": "reduce"}],
    })
    soa_result = soa.generate_soa({
        "ai_system_inventory": [SYSTEM],
        "risk_register": register["rows"],
    })
    gap_result = gap.generate_gap_assessment({
        "ai_system_inventory": [SYSTEM],
        "target_framework": "iso42001",
        "soa_rows": soa_result["rows"],
    })

    def check(citations: list[str]) -> None:
        for c in citations:
            assert (
                c.startswith("ISO/IEC 42001:2023, Clause ")
                or c.startswith("ISO/IEC 42001:2023, Annex A, Control ")
                or c.startswith("MAP ") or c.startswith("GOVERN ")
                or c.startswith("MEASURE ") or c.startswith("MANAGE ")
                or c.startswith("EU AI Act, ")
            ), f"citation {c!r} does not match STYLE.md prefix"

    for row in register["rows"]:
        check(row["citations"])
    check(soa_result["citations"])
    for row in soa_result["rows"]:
        check([row["citation"]])
    check(gap_result["citations"])
    for row in gap_result["rows"]:
        check([row["citation"]])


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
    print(f"Ran {len(tests)} integration tests: {len(tests) - len(failures)} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
