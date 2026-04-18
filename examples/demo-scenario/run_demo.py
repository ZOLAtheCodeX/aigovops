"""
End-to-end demo scenario for AIGovOps.

Loads the scenario inputs from inputs/, invokes every plugin in sequence,
writes artifacts to outputs/, and emits a summary.md that indexes the
artifacts and describes the composite AIMS state.

Usage:
    python run_demo.py

No external dependencies beyond the Python standard library.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
INPUTS = HERE / "inputs"
OUTPUTS = HERE / "outputs"
OUTPUTS.mkdir(parents=True, exist_ok=True)


def _load_plugin(name: str):
    spec = importlib.util.spec_from_file_location(
        name.replace("-", "_"),
        REPO_ROOT / "plugins" / name / "plugin.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(filename: str):
    return json.loads((INPUTS / filename).read_text(encoding="utf-8"))


def _write_json(obj, filename: str) -> Path:
    path = OUTPUTS / filename
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
    return path


def _write_text(content: str, filename: str) -> Path:
    path = OUTPUTS / filename
    path.write_text(content, encoding="utf-8")
    return path


def _role_assignments_to_tuple_keys(raw: dict) -> dict:
    """The role-matrix-generator accepts either tuple keys or 'cat::act' strings.
    The JSON file uses strings; pass them directly."""
    return raw


def main() -> int:
    print("Loading plugins...")
    audit_log = _load_plugin("audit-log-generator")
    role_matrix = _load_plugin("role-matrix-generator")
    risk_register = _load_plugin("risk-register-builder")
    soa = _load_plugin("soa-generator")
    aisia = _load_plugin("aisia-runner")
    nonconformity = _load_plugin("nonconformity-tracker")
    management_review = _load_plugin("management-review-packager")
    metrics = _load_plugin("metrics-collector")
    gap = _load_plugin("gap-assessment")

    print("Loading scenario inputs...")
    inventory = _read_json("ai_system_inventory.json")
    risks = _read_json("risks.json")
    org_chart = _read_json("org_chart.json")
    role_assignments = _role_assignments_to_tuple_keys(_read_json("role_assignments.json"))
    authority_register = _read_json("authority_register.json")
    measurements = _read_json("measurements.json")
    thresholds = _read_json("thresholds.json")
    stakeholders = _read_json("stakeholders.json")
    impact_assessments = _read_json("impact_assessments.json")
    governance_decisions = _read_json("governance_decisions.json")

    system = inventory[0]
    run_timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    artifacts: list[dict] = []

    # 1. Audit log entry
    print("1/9  audit-log-generator: deployment event...")
    entry = audit_log.generate_audit_log({
        "system_name": system["system_name"],
        "purpose": system["purpose"],
        "risk_tier": system["risk_tier"],
        "data_processed": system["data_processed"],
        "deployment_context": system["deployment_context"],
        "governance_decisions": governance_decisions,
        "responsible_parties": ["AI Governance Officer", "Head of AI Engineering"],
    })
    _write_json(entry, "audit-log-entry.json")
    _write_text(audit_log.render_markdown(entry), "audit-log-entry.md")
    artifacts.append({"name": "Audit Log Entry", "files": ["audit-log-entry.json", "audit-log-entry.md"]})

    # 2. Role matrix
    print("2/9  role-matrix-generator...")
    matrix = role_matrix.generate_role_matrix({
        "org_chart": org_chart,
        "role_assignments": role_assignments,
        "authority_register": authority_register,
        "backup_assignments": {
            "Chief Executive Officer": "Chief Risk Officer",
            "Chief Risk Officer": "Chief Information Security Officer",
            "Chief Technology Officer": "Head of AI Engineering",
        },
        "reviewed_by": "AI Governance Committee 2026-Q2",
    })
    _write_json(matrix, "role-matrix.json")
    _write_text(role_matrix.render_markdown(matrix), "role-matrix.md")
    _write_text(role_matrix.render_csv(matrix), "role-matrix.csv")
    artifacts.append({"name": "Role and Responsibility Matrix", "files": ["role-matrix.json", "role-matrix.md", "role-matrix.csv"]})

    # Derive a category-to-owner lookup for risk-register from the matrix.
    approver_by_category = {
        row["decision_category"]: row["role_name"]
        for row in matrix["rows"]
        if row["activity"] == "approve"
    }

    # 3. Risk register
    print("3/9  risk-register-builder...")
    register = risk_register.generate_risk_register({
        "ai_system_inventory": inventory,
        "risks": risks,
        "role_matrix_lookup": {
            "bias": approver_by_category.get("Risk acceptance"),
            "privacy": approver_by_category.get("Risk acceptance"),
            "transparency": approver_by_category.get("Risk acceptance"),
        },
        "framework": "dual",
        "reviewed_by": "AI Governance Committee 2026-Q2",
    })
    _write_json(register, "risk-register.json")
    _write_text(risk_register.render_markdown(register), "risk-register.md")
    _write_text(risk_register.render_csv(register), "risk-register.csv")
    artifacts.append({"name": "AI Risk Register", "files": ["risk-register.json", "risk-register.md", "risk-register.csv"]})

    # 4. SoA
    print("4/9  soa-generator...")
    soa_result = soa.generate_soa({
        "ai_system_inventory": inventory,
        "risk_register": register["rows"],
        "exclusion_justifications": {
            "A.10.4": "No customer-facing AI services in AIMS scope.",
            "A.9.3": "No generative AI use in this scope.",
        },
        "reviewed_by": "AI Governance Committee 2026-Q2",
    })
    _write_json(soa_result, "soa.json")
    _write_text(soa.render_markdown(soa_result), "soa.md")
    _write_text(soa.render_csv(soa_result), "soa.csv")
    artifacts.append({"name": "Statement of Applicability", "files": ["soa.json", "soa.md", "soa.csv"]})

    # 5. AISIA
    print("5/9  aisia-runner...")
    aisia_result = aisia.run_aisia({
        "system_description": {
            "system_name": system["system_name"],
            "purpose": system["purpose"],
            "intended_use": system["intended_use"],
            "decision_authority": system["decision_authority"],
            "deployment_environment": system["deployment_context"],
            "reversibility": system["reversibility"],
            "system_type": system["system_type"],
        },
        "affected_stakeholders": stakeholders,
        "impact_assessments": impact_assessments,
        "soa_rows": [{"control_id": r["control_id"], "row_ref": f"SOA-{r['control_id']}"} for r in soa_result["rows"]],
        "framework": "dual",
        "reviewed_by": "AI Governance Committee 2026-Q2",
    })
    _write_json(aisia_result, "aisia.json")
    _write_text(aisia.render_markdown(aisia_result), "aisia.md")
    artifacts.append({"name": "AI System Impact Assessment", "files": ["aisia.json", "aisia.md"]})

    # 6. Nonconformity: demonstrate the lifecycle with a sample record.
    print("6/9  nonconformity-tracker (demo lifecycle)...")
    nc_result = nonconformity.generate_nonconformity_register({
        "records": [
            {
                "id": "NC-DEMO-001",
                "description": "Demonstration nonconformity: quarterly equity audit surfaced a 0.06 demographic-parity difference in 2026-Q1, marginally above the organizational tolerance of 0.05.",
                "source_citation": "ISO/IEC 42001:2023, Annex A, Control A.5.4",
                "detected_by": "Clinical Informatics Equity Audit",
                "detection_date": "2026-03-20",
                "detection_method": "Scheduled quarterly equity audit",
                "status": "corrective-action-in-progress",
                "investigation_started_at": "2026-03-22",
                "root_cause": "Training data over-represented one demographic cohort.",
                "root_cause_analysis_date": "2026-03-25",
                "corrective_actions": [
                    {"action": "Rebalance training data", "owner": "Head of AI Engineering", "target_date": "2026-09-30"},
                    {"action": "Ongoing fairness metric monitoring", "owner": "AI Governance Officer", "target_date": "2026-06-30", "completed_at": "2026-04-10"},
                ],
                "state_history": [
                    {"state": "detected", "at": "2026-03-20", "by": "Clinical Informatics Equity Audit"},
                    {"state": "investigated", "at": "2026-03-22", "by": "AI Governance Officer"},
                    {"state": "root-cause-identified", "at": "2026-03-25", "by": "AI Governance Officer"},
                    {"state": "corrective-action-planned", "at": "2026-03-28", "by": "Chief Risk Officer"},
                    {"state": "corrective-action-in-progress", "at": "2026-04-01", "by": "Head of AI Engineering"},
                ],
            },
        ],
        "framework": "dual",
        "reviewed_by": "AI Governance Committee 2026-Q2",
    })
    _write_json(nc_result, "nonconformity-register.json")
    _write_text(nonconformity.render_markdown(nc_result), "nonconformity-register.md")
    artifacts.append({"name": "Nonconformity Register", "files": ["nonconformity-register.json", "nonconformity-register.md"]})

    # 7. Metrics report
    print("7/9  metrics-collector...")
    metrics_report = metrics.generate_metrics_report({
        "ai_system_inventory": inventory,
        "measurements": measurements,
        "thresholds": thresholds,
        "framework": "dual",
        "reviewed_by": "AI Governance Committee 2026-Q2",
    })
    _write_json(metrics_report, "metrics-report.json")
    _write_text(metrics.render_markdown(metrics_report), "metrics-report.md")
    _write_text(metrics.render_csv(metrics_report), "metrics-report.csv")
    artifacts.append({"name": "Trustworthy-AI Metrics Report", "files": ["metrics-report.json", "metrics-report.md", "metrics-report.csv"]})

    # 8. Management review package
    print("8/9  management-review-packager...")
    package = management_review.generate_review_package({
        "review_window": {"start": "2026-04-01", "end": "2026-06-30"},
        "attendees": ["Chief Executive Officer", "Chief Risk Officer", "AI Governance Officer", "Data Protection Officer"],
        "previous_review_actions": "MR-2026-Q1-action-log",
        "external_internal_issues_changes": "CHG-log-2026-Q2",
        "aims_performance": {"source_ref": "KPI-report-2026-Q2 (metrics-report.json)", "trend_direction": "stable"},
        "audit_results": "IA-2026-Q2-report",
        "nonconformity_trends": {"source_ref": f"NC-log-2026-Q2 (nonconformity-register.json with {nc_result['summary']['total_records']} record)", "trend_direction": "improving"},
        "objective_fulfillment": "OBJ-status-2026-Q2",
        "stakeholder_feedback": ["HR operations: positive reception", "Candidate advocacy: requested appeals process documentation"],
        "ai_risks_and_opportunities": f"RR-register-2026-Q2 (risk-register.json with {register['summary']['total_rows']} rows)",
        "continual_improvement_opportunities": ["Automate reviewer training refresh", "Integrate appeals process"],
        "meeting_metadata": {"scheduled_date": "2026-07-15"},
        "reviewed_by": "AI Governance Committee 2026-Q2",
    })
    _write_json(package, "management-review-package.json")
    _write_text(management_review.render_markdown(package), "management-review-package.md")
    artifacts.append({"name": "Management Review Input Package", "files": ["management-review-package.json", "management-review-package.md"]})

    # 9. Gap assessment
    print("9/9  gap-assessment (iso42001)...")
    gap_result = gap.generate_gap_assessment({
        "ai_system_inventory": inventory,
        "target_framework": "iso42001",
        "soa_rows": soa_result["rows"],
        "scope_boundary": "All AI systems in HR processes at this organization.",
        "reviewed_by": "AI Governance Committee 2026-Q2",
    })
    _write_json(gap_result, "gap-assessment.json")
    _write_text(gap.render_markdown(gap_result), "gap-assessment.md")
    _write_text(gap.render_csv(gap_result), "gap-assessment.csv")
    artifacts.append({"name": "Gap Assessment (iso42001)", "files": ["gap-assessment.json", "gap-assessment.md", "gap-assessment.csv"]})

    # Compose summary.md
    print("Writing summary.md...")
    summary_lines = [
        "# Demo Scenario: ResumeScreen AIMS Artifacts",
        "",
        f"Generated at (UTC): {run_timestamp}",
        f"Scenario: {system['system_name']} ({system['system_ref']}), risk tier {system['risk_tier']}",
        "",
        "## AIMS composite state",
        "",
        f"- Risk register rows: {register['summary']['total_rows']}",
        f"- SoA status counts: " + ", ".join(f"{k}={v}" for k, v in soa_result["summary"]["status_counts"].items()),
        f"- AISIA sections: {aisia_result['summary']['total_sections']} across {aisia_result['summary']['stakeholders_covered']} stakeholder groups",
        f"- Nonconformity records: {nc_result['summary']['total_records']} ({nc_result['summary']['open_records']} open)",
        f"- Metrics KPIs: {metrics_report['summary']['total_kpi_records']} records, {metrics_report['summary']['threshold_breach_count']} breaches",
        f"- Gap assessment coverage score: {gap_result['summary']['coverage_score']:.2%}",
        "",
        "## Artifacts",
        "",
    ]
    for art in artifacts:
        summary_lines.append(f"### {art['name']}")
        summary_lines.append("")
        for f in art["files"]:
            summary_lines.append(f"- [{f}]({f})")
        summary_lines.append("")
    summary_lines.append("## Citations appearing across artifacts")
    summary_lines.append("")
    summary_lines.append("Every artifact in this demo carries canonical STYLE.md citations. Key clauses and subcategories exercised:")
    summary_lines.append("")
    summary_lines.append("- ISO/IEC 42001:2023: Clauses 5.3, 6.1.2, 6.1.3, 6.1.4, 7.5.2, 7.5.3, 9.1, 9.3.2, 10.2; Annex A Controls A.3.2, A.5.2 through A.5.5, A.6.2.3, A.6.2.4, A.6.2.6, A.6.2.8, A.7.2, A.7.4, A.7.5, A.8.2, A.8.3, A.10.4.")
    summary_lines.append("- NIST AI RMF 1.0: MAP 4.1, MANAGE 1.2, MANAGE 1.3, MEASURE 2.1, 2.3, 2.5, 2.6, 2.9, 2.10, MEASURE 3.1, MANAGE 4.1.")
    summary_lines.append("")
    _write_text("\n".join(summary_lines), "summary.md")

    print()
    print(f"Demo complete. See {OUTPUTS}/summary.md for the index.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
