"""
Loader for organization.yaml.

Reads a single organization configuration file and produces per-plugin
input dicts. The organization.yaml shape is documented in
cli/README.md and examples/organization.example.yaml.

Only dependency: PyYAML (already a repo-wide dependency).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_TOP_LEVEL = ("organization",)


class OrganizationConfigError(ValueError):
    """Raised when organization.yaml is missing required fields or malformed."""


def load_organization(path: str | Path) -> dict[str, Any]:
    """Load and validate organization.yaml.

    Args:
        path: path to the organization.yaml file.

    Returns:
        Parsed dict.

    Raises:
        OrganizationConfigError: if the file is missing required top-level
            fields or is not a mapping.
        FileNotFoundError: if path does not exist.
    """
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise OrganizationConfigError(
            "organization.yaml must be a YAML mapping at the top level"
        )
    missing = [f for f in REQUIRED_TOP_LEVEL if f not in data]
    if missing:
        raise OrganizationConfigError(
            f"organization.yaml missing required top-level fields: {sorted(missing)}"
        )
    org = data["organization"]
    if not isinstance(org, dict):
        raise OrganizationConfigError("'organization' must be a mapping")
    if "name" not in org:
        raise OrganizationConfigError("organization.name is required")
    return data


def organization_name(config: dict[str, Any]) -> str:
    return str(config["organization"].get("name", "<unnamed>"))


def jurisdictions(config: dict[str, Any]) -> list[str]:
    """Return the union of headquarters + operational jurisdictions plus
    any jurisdiction listed on an AI system."""
    org = config.get("organization", {})
    result: list[str] = []
    hq = org.get("headquarters_jurisdiction")
    if isinstance(hq, str):
        result.append(hq)
    op = org.get("operational_jurisdictions") or []
    if isinstance(op, list):
        for j in op:
            if isinstance(j, str) and j not in result:
                result.append(j)
    for sys in config.get("ai_systems") or []:
        if not isinstance(sys, dict):
            continue
        sj = sys.get("jurisdiction")
        if isinstance(sj, str) and sj not in result:
            result.append(sj)
        elif isinstance(sj, list):
            for j in sj:
                if isinstance(j, str) and j not in result:
                    result.append(j)
    return result


def ai_systems(config: dict[str, Any]) -> list[dict[str, Any]]:
    systems = config.get("ai_systems") or []
    if not isinstance(systems, list):
        raise OrganizationConfigError("ai_systems must be a list")
    return [dict(s) for s in systems if isinstance(s, dict)]


def section(config: dict[str, Any], key: str, default: Any = None) -> Any:
    """Safe get for top-level keys other than 'organization'."""
    return config.get(key, default)


def build_inventory_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build input dict for ai-system-inventory-maintainer."""
    systems = ai_systems(config)
    boundary = section(config, "aims_boundary", {}) or {}
    org = config["organization"]
    inputs: dict[str, Any] = {
        "systems": systems,
        "operation": "validate",
        "organizational_scope": {
            "jurisdictions": jurisdictions(config),
            "sectors": [org.get("industry")] if org.get("industry") else [],
            "decision_domains": [],
            "aims_boundary": boundary,
        },
        "reviewed_by": section(config, "reviewed_by", f"{organization_name(config)} CLI run"),
    }
    override = section(config, "inventory_inputs") or {}
    if isinstance(override, dict):
        inputs.update(override)
    return inputs


def _first_system(config: dict[str, Any]) -> dict[str, Any]:
    systems = ai_systems(config)
    if not systems:
        raise OrganizationConfigError(
            "ai_systems must contain at least one entry for this plugin"
        )
    return systems[0]


def build_applicability_inputs(config: dict[str, Any]) -> dict[str, Any]:
    system = _first_system(config)
    override = section(config, "applicability_inputs") or {}
    default = {
        "system_description": dict(system),
        "target_date": override.get("target_date", "2026-08-02"),
        "enforcement_timeline": override.get(
            "enforcement_timeline",
            {
                "enforcement_events": [
                    {
                        "date": "2024-08-01",
                        "phase": "entry-into-force",
                        "description": "EU AI Act enters into force.",
                        "effective_provisions": ["Article 1", "Article 3"],
                        "citation": "EU AI Act, Article 113",
                        "organizational_actions": [],
                    },
                    {
                        "date": "2025-02-02",
                        "phase": "prohibited-practices-applicable",
                        "description": "Article 5 prohibitions take effect.",
                        "effective_provisions": ["Article 5"],
                        "citation": "EU AI Act, Article 113(a)",
                        "organizational_actions": [],
                    },
                ]
            },
        ),
    }
    default.update({k: v for k, v in override.items() if k not in default})
    return default


def build_high_risk_inputs(config: dict[str, Any]) -> dict[str, Any]:
    system = _first_system(config)
    desc = dict(system)
    desc.setdefault("sector", config["organization"].get("industry", "general"))
    override = section(config, "high_risk_inputs") or {}
    out = {"system_description": desc, "reviewed_by": override.get("reviewed_by")}
    out.update({k: v for k, v in override.items() if k not in out})
    if out["reviewed_by"] is None:
        out.pop("reviewed_by")
    return out


def build_risk_register_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "risk_register_inputs") or {}
    inputs = {
        "ai_system_inventory": ai_systems(config),
        "risks": override.get("risks", []),
        "framework": override.get("framework", "iso42001"),
        "reviewed_by": override.get("reviewed_by", f"{organization_name(config)} CLI run"),
    }
    inputs.update({k: v for k, v in override.items() if k not in inputs})
    return inputs


def build_data_register_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "data_register_inputs") or {}
    inputs = {
        "data_inventory": override.get("data_inventory", []),
        "framework": override.get("framework", "iso42001"),
    }
    inputs.update({k: v for k, v in override.items() if k not in inputs})
    return inputs


def build_role_matrix_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "role_matrix_inputs") or {}
    inputs = {
        "org_chart": override.get("org_chart", []),
        "role_assignments": override.get("role_assignments", {}),
        "authority_register": override.get("authority_register", {}),
    }
    for opt in ("backup_assignments", "reviewed_by"):
        if opt in override:
            inputs[opt] = override[opt]
    return inputs


def build_soa_inputs(config: dict[str, Any], risk_register: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    override = section(config, "soa_inputs") or {}
    inputs = {
        "ai_system_inventory": ai_systems(config),
        "risk_register": risk_register if risk_register is not None else override.get("risk_register", []),
        "reviewed_by": override.get("reviewed_by", f"{organization_name(config)} CLI run"),
    }
    for opt in ("exclusion_justifications", "implementation_plans", "scope_notes", "annex_a_controls"):
        if opt in override:
            inputs[opt] = override[opt]
    return inputs


def build_aisia_inputs(
    config: dict[str, Any], soa_rows: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    system = _first_system(config)
    override = section(config, "aisia_inputs") or {}
    stakeholders = override.get(
        "affected_stakeholders",
        ["Primary users", "Affected individuals", "Operators"],
    )
    desc = {
        "system_name": system.get("system_name", "system"),
        "purpose": system.get("intended_use") or system.get("purpose", "unspecified"),
    }
    for k in ("intended_use", "decision_authority", "deployment_environment", "reversibility", "system_type", "deployment_context"):
        if system.get(k) is not None:
            desc[k] = system[k]
    if "deployment_context" in desc and "deployment_environment" not in desc:
        desc["deployment_environment"] = desc["deployment_context"]
    desc.update(override.get("system_description_overrides", {}))
    inputs = {
        "system_description": desc,
        "affected_stakeholders": stakeholders,
        "impact_assessments": override.get("impact_assessments", []),
        "framework": override.get("framework", "iso42001"),
        "reviewed_by": override.get("reviewed_by", f"{organization_name(config)} CLI run"),
    }
    if soa_rows:
        inputs["soa_rows"] = [
            {"control_id": r.get("control_id"), "row_ref": f"SOA-{r.get('control_id')}"}
            for r in soa_rows
            if r.get("control_id")
        ]
    return inputs


def build_audit_log_inputs(config: dict[str, Any]) -> dict[str, Any]:
    system = _first_system(config)
    override = section(config, "audit_log_inputs") or {}
    return {
        "system_name": system.get("system_name", "system"),
        "purpose": system.get("purpose") or system.get("intended_use", "unspecified"),
        "risk_tier": system.get("risk_tier", "limited"),
        "data_processed": system.get("data_processed", []),
        "deployment_context": system.get("deployment_context", "unspecified"),
        "governance_decisions": override.get(
            "governance_decisions", section(config, "governance_decisions", [])
        ),
        "responsible_parties": override.get(
            "responsible_parties", ["AI Governance Officer"]
        ),
    }


def build_metrics_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "metrics_inputs") or {}
    inputs = {
        "ai_system_inventory": ai_systems(config),
        "measurements": override.get("measurements", []),
        "framework": override.get("framework", "iso42001"),
        "reviewed_by": override.get("reviewed_by", f"{organization_name(config)} CLI run"),
    }
    if "thresholds" in override:
        inputs["thresholds"] = override["thresholds"]
    return inputs


def build_nonconformity_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "nonconformity_inputs") or {}
    return {
        "records": override.get("records", []),
        "framework": override.get("framework", "iso42001"),
        "reviewed_by": override.get("reviewed_by", f"{organization_name(config)} CLI run"),
    }


def build_internal_audit_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "internal_audit_inputs") or {}
    systems = ai_systems(config)
    boundary = section(config, "aims_boundary", {}) or {}
    scope = override.get(
        "scope",
        {
            "aims_boundaries": boundary.get("description", "All AI systems in AIMS scope"),
            "systems_in_scope": [s.get("system_id") or s.get("system_ref") for s in systems if s.get("system_id") or s.get("system_ref")],
            "clauses_in_scope": ["4", "5", "6", "7", "8", "9", "10"],
            "annex_a_in_scope": ["A.5", "A.6", "A.7", "A.8"],
        },
    )
    return {
        "scope": scope,
        "audit_frequency_months": override.get("audit_frequency_months", 12),
        "audit_criteria": override.get(
            "audit_criteria",
            ["ISO/IEC 42001:2023", "Internal AI governance policy"],
        ),
        "reviewed_by": override.get("reviewed_by", f"{organization_name(config)} CLI run"),
    }


def build_post_market_monitoring_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for the post-market-monitoring plugin.

    Default behavior: pick the first ai_system in the inventory and emit a
    minimal monitoring plan covering accuracy, user-feedback, and
    incident-rate. Organizations override via
    ``post_market_monitoring_inputs`` in organization.yaml.
    """
    override = section(config, "post_market_monitoring_inputs") or {}
    systems = ai_systems(config)
    if override.get("system_description"):
        system_description = override["system_description"]
    elif systems:
        first = systems[0]
        system_description = {
            "system_id": first.get("system_id") or first.get("system_ref") or "system-001",
            "system_name": first.get("system_name") or "Unnamed AI system",
            "intended_use": first.get("intended_use") or "Not specified",
            "risk_tier": first.get("risk_tier") or "limited-risk",
            "jurisdiction": first.get("jurisdiction") or "us",
            "deployment_context": first.get("deployment_context") or "production",
            "lifecycle_state": first.get("lifecycle_state") or "in-service",
        }
    else:
        system_description = {
            "system_id": "system-001",
            "system_name": "Unnamed AI system",
            "intended_use": "Not specified",
            "risk_tier": "limited-risk",
            "jurisdiction": "us",
            "deployment_context": "production",
            "lifecycle_state": "in-service",
        }
    monitoring_scope = override.get(
        "monitoring_scope",
        {
            "dimensions_monitored": ["accuracy", "user-feedback", "incident-rate"],
            "chapter_iii_requirements_in_scope": [],
            "systems_in_program": [system_description["system_id"]],
        },
    )
    cadence = override.get("cadence", "quarterly")
    inputs = {
        "system_description": system_description,
        "monitoring_scope": monitoring_scope,
        "cadence": cadence,
        "reviewed_by": override.get("reviewed_by", f"{organization_name(config)} CLI run"),
    }
    for opt in (
        "data_collection",
        "thresholds",
        "responsibilities",
        "previous_plan_ref",
        "plan_review_interval_months",
        "trigger_catalogue",
        "enrich_with_crosswalk",
    ):
        if opt in override:
            inputs[opt] = override[opt]
    return inputs


def build_gap_assessment_inputs(
    config: dict[str, Any], soa_rows: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    override = section(config, "gap_assessment_inputs") or {}
    boundary = section(config, "aims_boundary", {}) or {}
    inputs = {
        "ai_system_inventory": ai_systems(config),
        "target_framework": override.get("target_framework", "iso42001"),
        "scope_boundary": override.get(
            "scope_boundary",
            boundary.get("description", "All AI systems in AIMS scope"),
        ),
        "reviewed_by": override.get("reviewed_by", f"{organization_name(config)} CLI run"),
    }
    if soa_rows:
        inputs["soa_rows"] = soa_rows
    for opt in ("targets", "current_state_evidence", "manual_classifications"):
        if opt in override:
            inputs[opt] = override[opt]
    return inputs


def build_management_review_inputs(
    config: dict[str, Any],
    *,
    metrics_summary: str = "",
    nc_summary: str = "",
    risks_summary: str = "",
) -> dict[str, Any]:
    override = section(config, "management_review_inputs") or {}
    return {
        "review_window": override.get(
            "review_window", {"start": "2026-04-01", "end": "2026-06-30"}
        ),
        "attendees": override.get(
            "attendees",
            [
                "Chief Executive Officer",
                "Chief Risk Officer",
                "AI Governance Officer",
            ],
        ),
        "previous_review_actions": override.get(
            "previous_review_actions", "MR-prior-action-log"
        ),
        "external_internal_issues_changes": override.get(
            "external_internal_issues_changes", "CHG-log"
        ),
        "aims_performance": override.get(
            "aims_performance",
            {"source_ref": metrics_summary or "KPI-report", "trend_direction": "stable"},
        ),
        "audit_results": override.get("audit_results", "IA-report"),
        "nonconformity_trends": override.get(
            "nonconformity_trends",
            {
                "source_ref": nc_summary or "NC-log",
                "trend_direction": "stable",
            },
        ),
        "objective_fulfillment": override.get(
            "objective_fulfillment", "OBJ-status"
        ),
        "stakeholder_feedback": override.get("stakeholder_feedback", []),
        "ai_risks_and_opportunities": override.get(
            "ai_risks_and_opportunities", risks_summary or "RR-register"
        ),
        "continual_improvement_opportunities": override.get(
            "continual_improvement_opportunities", []
        ),
        "meeting_metadata": override.get(
            "meeting_metadata", {"scheduled_date": "2026-07-15"}
        ),
        "reviewed_by": override.get("reviewed_by", f"{organization_name(config)} CLI run"),
    }


def build_colorado_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "colorado_inputs") or {}
    system = _first_system(config)
    return {
        "actor_role": override.get("actor_role", "deployer"),
        "system_description": override.get("system_description", dict(system)),
        "consequential_decision_domains": override.get(
            "consequential_decision_domains", ["employment"]
        ),
    }


def build_nyc_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "nyc_inputs") or {}
    system = _first_system(config)
    return {
        "aedt_description": override.get("aedt_description", dict(system)),
        "employer_role": override.get("employer_role", "employer"),
        "audit_data": override.get("audit_data", {}),
    }


def build_uk_atrs_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "uk_atrs_inputs") or {}
    system = _first_system(config)
    return {
        "tier": override.get("tier", "tier-1"),
        "tool_description": override.get(
            "tool_description",
            {
                "name": system.get("system_name", "system"),
                "description": system.get("intended_use", "unspecified"),
            },
        ),
        "owner": override.get(
            "owner",
            {
                "organization": organization_name(config),
                "contact_email": "governance@example.org",
            },
        ),
    }


def build_singapore_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "singapore_inputs") or {}
    system = _first_system(config)
    return {
        "system_description": override.get("system_description", dict(system)),
        "organization_type": override.get("organization_type", "general"),
    }


def build_crosswalk_inputs(config: dict[str, Any]) -> dict[str, Any]:
    override = section(config, "crosswalk_inputs") or {}
    return {
        "query_type": override.get("query_type", "coverage"),
        "frameworks": override.get("frameworks", ["iso42001", "nist-ai-rmf"]),
    }


def system_applies_to(system: dict[str, Any], jurisdiction: str) -> bool:
    """True if system is in scope of given jurisdiction."""
    sj = system.get("jurisdiction")
    if sj is None:
        return False
    if isinstance(sj, str):
        return sj == jurisdiction
    if isinstance(sj, list):
        return jurisdiction in sj
    return False


def any_system_applies(config: dict[str, Any], jurisdiction: str) -> bool:
    if jurisdiction in jurisdictions(config):
        return True
    return any(system_applies_to(s, jurisdiction) for s in ai_systems(config))
