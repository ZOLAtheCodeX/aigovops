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


# Canonical risk-tier tokens expected by downstream plugins
# (post-market-monitoring, system-event-logger, human-oversight-designer,
# eu-conformity-assessor). The organization.yaml schema is looser (accepts
# plain 'limited', 'high', etc.), so we normalise before passing through.
_RISK_TIER_ALIASES = {
    "minimal": "minimal-risk",
    "minimal-risk": "minimal-risk",
    "limited": "limited-risk",
    "limited-risk": "limited-risk",
    "high": "high-risk-annex-iii",
    "high-risk": "high-risk-annex-iii",
    "high-risk-annex-i": "high-risk-annex-i",
    "high-risk-annex-iii": "high-risk-annex-iii",
    "gpai": "general-purpose-ai",
    "general-purpose-ai": "general-purpose-ai",
    "prohibited": "prohibited",
    "out-of-scope": "out-of-scope",
}


def normalize_risk_tier(value: Any, default: str = "limited-risk") -> str:
    """Normalise a risk-tier string to the canonical plugin enum."""
    if not isinstance(value, str) or not value:
        return default
    return _RISK_TIER_ALIASES.get(value.strip().lower(), default)


_LIFECYCLE_STATE_ALIASES = {
    "design": "design",
    "development": "development",
    "verification": "verification",
    "testing": "verification",
    "deployment": "deployment",
    "deploy": "deployment",
    "deployed": "in-service",
    "in-service": "in-service",
    "production": "in-service",
    "decommissioned": "decommissioned",
    "retired": "decommissioned",
}


def normalize_lifecycle_state(value: Any, default: str = "in-service") -> str:
    """Normalise a lifecycle-state string to the canonical plugin enum."""
    if not isinstance(value, str) or not value:
        return default
    return _LIFECYCLE_STATE_ALIASES.get(value.strip().lower(), default)


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
            "risk_tier": normalize_risk_tier(first.get("risk_tier"), "limited-risk"),
            "jurisdiction": _scalar_jurisdiction(first.get("jurisdiction")) or "us",
            "deployment_context": first.get("deployment_context") or "production",
            "lifecycle_state": normalize_lifecycle_state(first.get("lifecycle_state"), "in-service"),
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
    query_type = override.get("query_type", "gaps")
    inputs: dict[str, Any] = {
        "query_type": query_type,
        "source_framework": override.get("source_framework", "iso42001"),
        "target_framework": override.get("target_framework", "nist-ai-rmf"),
    }
    if "source_ref" in override:
        inputs["source_ref"] = override["source_ref"]
    elif query_type == "coverage":
        # coverage requires source_ref; default to an ISO 42001 clause known
        # to be in the seeded crosswalk data.
        inputs["source_ref"] = override.get("default_source_ref", "ISO/IEC 42001:2023, Clause 6.1.2")
    if "relationship_filter" in override:
        inputs["relationship_filter"] = override["relationship_filter"]
    return inputs


def _scalar_jurisdiction(value: Any, default: str | None = None) -> str | None:
    """Return a single jurisdiction token from a string or list."""
    if isinstance(value, str) and value:
        return value
    if isinstance(value, list) and value:
        for v in value:
            if isinstance(v, str) and v:
                return v
    return default


def _first_system_or_scaffold(config: dict[str, Any]) -> dict[str, Any]:
    """Return the first ai_system or a minimal scaffold for downstream plugins."""
    systems = ai_systems(config)
    if systems:
        return systems[0]
    return {
        "system_id": "system-001",
        "system_ref": "system-001",
        "system_name": "Unnamed AI system",
        "intended_use": "Not specified",
        "purpose": "Not specified",
        "risk_tier": "limited-risk",
        "jurisdiction": "us",
        "deployment_context": "production",
        "lifecycle_state": "in-service",
    }


def has_generative_system(config: dict[str, Any]) -> bool:
    """True if any ai_system is flagged generative."""
    for s in ai_systems(config):
        if bool(s.get("is_generative")):
            return True
        mtype = (s.get("model_type") or "").lower()
        if mtype in {"llm", "large-language-model", "diffusion-model", "generative"}:
            return True
    return False


def has_gpai_model(config: dict[str, Any]) -> bool:
    """True if any ai_system is a GPAI candidate (generative + transformer/DNN)."""
    for s in ai_systems(config):
        mtype = (s.get("model_type") or "").lower()
        is_gpai_like = mtype in {"transformer", "deep-neural-network", "llm", "large-language-model"}
        if bool(s.get("is_generative")) and is_gpai_like:
            return True
    return False


def has_eu_high_risk_system(config: dict[str, Any]) -> bool:
    """True if any ai_system has an EU-high-risk classification."""
    for s in ai_systems(config):
        tier = normalize_risk_tier(s.get("risk_tier"), "limited-risk")
        if tier in ("high-risk-annex-i", "high-risk-annex-iii"):
            return True
        if s.get("annex_iii_category"):
            return True
    return False


def build_supplier_vendor_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for supplier-vendor-assessor.

    Expects `supplier_vendor_inputs.vendors` (list) in organization.yaml. If
    absent, runs against a placeholder vendor so the plugin emits warnings
    rather than crashing.
    """
    override = section(config, "supplier_vendor_inputs") or {}
    vendors = override.get("vendors") or []
    if vendors:
        vendor = dict(vendors[0])
    else:
        vendor = {
            "vendor_name": "Placeholder vendor",
            "vendor_type": "model-provider",
            "products_services": [],
            "ai_systems_they_supply": [],
        }
    inputs: dict[str, Any] = {
        "vendor_description": vendor,
        "vendor_role": override.get("vendor_role", vendor.get("vendor_type", "model-provider")),
        "organization_role": override.get("organization_role", "deployer"),
        "enrich_with_crosswalk": override.get("enrich_with_crosswalk", False),
    }
    if "contract_summary" in override:
        inputs["contract_summary"] = override["contract_summary"]
    if "deployer_modification_note" in override:
        inputs["deployer_modification_note"] = override["deployer_modification_note"]
    return inputs


def build_bias_evaluator_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for bias-evaluator.

    Expects `bias_evaluator_inputs` with `evaluation_data`, `protected_attributes`.
    Missing blocks produce a minimal scaffold that triggers plugin warnings.
    """
    override = section(config, "bias_evaluator_inputs") or {}
    system = _first_system_or_scaffold(config)
    sysd = {
        "system_name": system.get("system_name", "system"),
        "purpose": system.get("purpose") or system.get("intended_use", "unspecified"),
        "decision_authority": system.get("decision_authority", "decision-support"),
        "sector": system.get("sector", "general"),
    }
    eval_data = override.get("evaluation_data") or {
        "dataset_ref": "not-provided",
        "evaluation_date": "1970-01-01",
        "sample_size": 0,
        "ground_truth_available": False,
        "per_group_counts": {},
    }
    if "per_group_counts" not in eval_data:
        eval_data["per_group_counts"] = {}
    pas = override.get("protected_attributes") or [
        {"attribute_name": "placeholder", "categories_present": []}
    ]
    inputs = {
        "system_description": sysd,
        "evaluation_data": eval_data,
        "protected_attributes": pas,
        "metrics_to_compute": override.get("metrics_to_compute", []),
        "jurisdiction_rules": override.get("jurisdiction_rules", []),
        "enrich_with_crosswalk": override.get("enrich_with_crosswalk", False),
    }
    for opt in ("intersectional_analysis", "organizational_thresholds", "minimum_group_size"):
        if opt in override:
            inputs[opt] = override[opt]
    return inputs


def build_robustness_evaluator_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for robustness-evaluator.

    Expects `robustness_evaluator_inputs` with `evaluation_scope`,
    `evaluation_results`. Missing blocks yield a minimal scaffold.
    """
    override = section(config, "robustness_evaluator_inputs") or {}
    system = _first_system_or_scaffold(config)
    sysd = {
        "system_id": system.get("system_id") or system.get("system_ref", "system-001"),
        "system_name": system.get("system_name", "system"),
        "risk_tier": normalize_risk_tier(system.get("risk_tier"), "limited-risk"),
        "jurisdiction": _scalar_jurisdiction(system.get("jurisdiction"), "us"),
        "continuous_learning": bool(system.get("continuous_learning", False)),
    }
    scope = override.get("evaluation_scope") or {
        "dimensions": ["accuracy"],
        "evaluation_date": "1970-01-01",
        "evaluator_identity": "not-provided",
    }
    results = override.get("evaluation_results") or {}
    inputs: dict[str, Any] = {
        "system_description": sysd,
        "evaluation_scope": scope,
        "evaluation_results": results,
        "enrich_with_crosswalk": override.get("enrich_with_crosswalk", False),
    }
    for opt in ("backup_plan_ref", "concept_drift_monitoring_ref", "continuous_learning_controls_ref"):
        if opt in override:
            inputs[opt] = override[opt]
    return inputs


def build_human_oversight_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for human-oversight-designer.

    Expects `human_oversight_inputs` with `oversight_design` and
    `assigned_oversight_personnel`. A missing block yields a minimal,
    warnings-producing scaffold.
    """
    override = section(config, "human_oversight_inputs") or {}
    system = _first_system_or_scaffold(config)
    sysd = {
        "system_id": system.get("system_id") or system.get("system_ref", "system-001"),
        "system_name": system.get("system_name", "system"),
        "intended_use": system.get("intended_use", "Not specified"),
        "risk_tier": normalize_risk_tier(system.get("risk_tier"), "limited-risk"),
        "jurisdiction": _scalar_jurisdiction(system.get("jurisdiction"), "us"),
        "deployment_context": system.get("deployment_context", "production"),
        "decision_authority": system.get("decision_authority", "decision-support"),
        "biometric_identification_system": bool(
            system.get("biometric_identification_system", False)
        ),
    }
    oversight = override.get("oversight_design") or {
        "mode": "human-in-the-loop",
    }
    inputs: dict[str, Any] = {
        "system_description": sysd,
        "oversight_design": oversight,
        "enrich_with_crosswalk": override.get("enrich_with_crosswalk", False),
    }
    if "assigned_oversight_personnel" in override:
        inputs["assigned_oversight_personnel"] = override["assigned_oversight_personnel"]
    return inputs


def build_system_event_logger_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for system-event-logger.

    Requires `system_event_logger_inputs.event_schema` (non-empty dict) and
    `retention_policy`. Plugin validation is strict; we supply defaults that
    pass validation and emit warnings on content gaps.
    """
    override = section(config, "system_event_logger_inputs") or {}
    system = _first_system_or_scaffold(config)
    sysd = {
        "system_id": system.get("system_id") or system.get("system_ref", "system-001"),
        "risk_tier": normalize_risk_tier(system.get("risk_tier"), "limited-risk"),
        "jurisdiction": _scalar_jurisdiction(system.get("jurisdiction"), "usa-co"),
        "remote_biometric_id": bool(system.get("biometric_identification_system", False)),
        "sector": system.get("sector", "general"),
        "lifecycle_state": normalize_lifecycle_state(system.get("lifecycle_state"), "in-service"),
    }
    event_schema = override.get("event_schema") or {
        "inference-request": {
            "request_id": {"type": "string", "required": True, "description": "unique request identifier"},
            "timestamp": {"type": "datetime", "required": True, "description": "request time UTC"},
        },
        "inference-output": {
            "request_id": {"type": "string", "required": True, "description": "matching request id"},
            "output_hash": {"type": "string", "required": True, "description": "hash of output"},
        },
    }
    retention = override.get("retention_policy") or {
        "policy_name": "eu-art-19-minimum",
        "minimum_days": 200,
        "maximum_days": 730,
        "deletion_procedure_ref": "not-provided",
        "legal_basis_citation": "EU AI Act, Article 19, Paragraph 1",
    }
    inputs: dict[str, Any] = {
        "system_description": sysd,
        "event_schema": event_schema,
        "retention_policy": retention,
    }
    for opt in ("log_storage", "traceability_mappings"):
        if opt in override:
            inputs[opt] = override[opt]
    return inputs


def build_explainability_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for explainability-documenter.

    Expects `explainability_inputs` with `model_type`, `explanation_methods`.
    Minimal scaffold otherwise.
    """
    override = section(config, "explainability_inputs") or {}
    system = _first_system_or_scaffold(config)
    sysd = {
        "system_name": system.get("system_name", "system"),
        "purpose": system.get("purpose") or system.get("intended_use", "unspecified"),
        "decision_authority": system.get("decision_authority", "decision-support"),
        "decision_effects": override.get("decision_effects", system.get("decision_effects", [])),
        "jurisdiction": _scalar_jurisdiction(system.get("jurisdiction"), "us"),
    }
    # Map org-yaml system_type values to the plugin's model_type enum.
    system_type_map = {
        "classical-ml": "tree-based",
        "decision-tree": "tree-based",
        "tree-based": "tree-based",
        "linear": "linear",
        "kernel": "kernel",
        "neural-network": "neural-network",
        "deep-neural-network": "deep-neural-network",
        "transformer": "transformer",
        "ensemble": "ensemble",
        "rule-based": "rule-based",
        "hybrid": "hybrid",
    }
    raw_type = override.get("model_type") or system.get("system_type") or "tree-based"
    model_type = system_type_map.get(str(raw_type).lower(), "tree-based")
    inputs: dict[str, Any] = {
        "system_description": sysd,
        "model_type": model_type,
        "explanation_methods": override.get("explanation_methods", []),
        "intrinsic_interpretability_claim": bool(
            override.get("intrinsic_interpretability_claim", False)
        ),
        "enrich_with_crosswalk": override.get("enrich_with_crosswalk", False),
    }
    if "art_86_response_template_ref" in override:
        inputs["art_86_response_template_ref"] = override["art_86_response_template_ref"]
    return inputs


def build_genai_risk_register_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for genai-risk-register.

    Guarded: caller should only invoke when at least one system is generative.
    """
    override = section(config, "genai_risk_register_inputs") or {}
    systems = ai_systems(config)
    genai_system = next(
        (
            s for s in systems
            if s.get("is_generative")
            or (s.get("model_type") or "").lower() in {"llm", "large-language-model", "transformer", "diffusion-model"}
        ),
        systems[0] if systems else _first_system_or_scaffold(config),
    )
    sysd = {
        "system_id": genai_system.get("system_id") or genai_system.get("system_ref", "genai-001"),
        "model_type": genai_system.get("model_type", "LLM"),
        "modality": genai_system.get("modality", "text"),
        "is_generative": True,
        "training_data_scope": genai_system.get("training_data_scope", "unspecified"),
        "deployment_context": genai_system.get("deployment_context", "production"),
        "jurisdiction": genai_system.get("jurisdiction", "us"),
    }
    if "base_model_ref" in genai_system:
        sysd["base_model_ref"] = genai_system["base_model_ref"]
    inputs: dict[str, Any] = {
        "system_description": override.get("system_description", sysd),
        "risk_evaluations": override.get("risk_evaluations", []),
        "enrich_with_crosswalk": override.get("enrich_with_crosswalk", False),
    }
    if "risks_not_applicable" in override:
        inputs["risks_not_applicable"] = override["risks_not_applicable"]
    return inputs


def build_gpai_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for gpai-obligations-tracker."""
    override = section(config, "gpai_inputs") or {}
    systems = ai_systems(config)
    candidate = next(
        (
            s for s in systems
            if (s.get("model_type") or "").lower() in {"transformer", "deep-neural-network", "llm", "large-language-model"}
            and s.get("is_generative")
        ),
        systems[0] if systems else _first_system_or_scaffold(config),
    )
    model = override.get("model_description") or {
        "model_name": candidate.get("system_name") or "Unnamed GPAI model",
        "model_family": candidate.get("model_family", "unknown"),
        "parameter_count": candidate.get("parameter_count", "unknown"),
        "training_compute_flops": candidate.get("training_compute_flops", "unknown"),
        "training_data_types": candidate.get("training_data_types", []),
        "modality": candidate.get("modality", "text"),
    }
    inputs: dict[str, Any] = {
        "model_description": model,
        "provider_role": override.get("provider_role", "eu-established-provider"),
    }
    for opt in (
        "technical_documentation_ref",
        "downstream_integrator_docs_ref",
        "copyright_policy_ref",
        "training_data_summary_ref",
        "authorised_representative",
        "systemic_risk_artifacts",
        "designated_systemic_risk",
        "self_declared_below_threshold",
        "code_of_practice_status",
        "enrich_with_crosswalk",
    ):
        if opt in override:
            inputs[opt] = override[opt]
    return inputs


def build_incident_reporting_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for incident-reporting.

    When no incidents are declared, emit a scaffold template so the plugin
    still runs and warns about empty inputs.
    """
    from datetime import datetime, timezone
    override = section(config, "incident_reporting_inputs") or {}
    incidents = override.get("incidents") or []
    if incidents:
        incident = dict(incidents[0])
    else:
        incident = {
            "summary": "No incidents declared; template scaffold for future reporting.",
            "affected_systems": [
                s.get("system_id") or s.get("system_ref")
                for s in ai_systems(config)
                if s.get("system_id") or s.get("system_ref")
            ],
            "potential_harms": [],
            "impacted_persons_count": 0,
            "geographic_scope": "not-provided",
        }
    # Applicable jurisdictions: use explicit override, then incident, then org jurisdictions.
    jset = set(jurisdictions(config))
    mapped_jset: list[str] = []
    juris_alias = {"usa": "usa-ca"}
    for j in jset:
        jl = j.lower()
        if jl in ("eu", "usa-co", "usa-nyc", "usa-ca", "uk", "singapore", "canada"):
            mapped_jset.append(jl)
    applicable = (
        override.get("applicable_jurisdictions")
        or incident.get("applicable_jurisdictions")
        or (mapped_jset if mapped_jset else ["eu"])
    )
    detected_at = (
        override.get("detected_at")
        or incident.pop("detected_at", None)
        or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    inputs: dict[str, Any] = {
        "incident_description": incident,
        "applicable_jurisdictions": applicable,
        "detected_at": detected_at,
    }
    for opt in ("severity", "actor_role", "consequential_domains"):
        if opt in override:
            inputs[opt] = override[opt]
    return inputs


def build_eu_conformity_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build inputs for eu-conformity-assessor. Caller should gate on EU + high-risk."""
    override = section(config, "eu_conformity_inputs") or {}
    systems = ai_systems(config)
    high_risk_sys = next(
        (
            s for s in systems
            if normalize_risk_tier(s.get("risk_tier"), "limited-risk") in ("high-risk-annex-i", "high-risk-annex-iii")
            or s.get("annex_iii_category")
        ),
        systems[0] if systems else _first_system_or_scaffold(config),
    )
    sysd = override.get("system_description") or {
        "system_id": high_risk_sys.get("system_id") or high_risk_sys.get("system_ref", "system-001"),
        "risk_tier": "high-risk",
        "intended_use": high_risk_sys.get("intended_use", "Not specified"),
        "sector": high_risk_sys.get("sector", "general"),
        "annex_iii_category": high_risk_sys.get("annex_iii_category", "4-employment"),
        "ce_marking_required": bool(high_risk_sys.get("ce_marking_required", True)),
    }
    provider = override.get("provider_identity") or {
        "legal_name": organization_name(config),
        "address": "not-provided",
        "country": "US",
        "contact": "not-provided",
    }
    inputs: dict[str, Any] = {
        "system_description": sysd,
        "provider_identity": provider,
        "procedure_requested": override.get("procedure_requested", "annex-vi-internal-control"),
        "enrich_with_crosswalk": override.get("enrich_with_crosswalk", False),
    }
    for opt in (
        "harmonised_standards_applied",
        "ce_marking_location",
        "registration_status",
        "evidence_bundle_ref",
        "reviewed_by",
    ):
        if opt in override:
            inputs[opt] = override[opt]
    return inputs


def build_evidence_bundle_inputs(
    config: dict[str, Any],
    *,
    artifacts_root: Any,
    bundle_output_dir: Any,
) -> dict[str, Any]:
    """Build inputs for evidence-bundle-packager.

    Consumes the artifacts directory produced by the current run.
    """
    override = section(config, "evidence_bundle_inputs") or {}
    org = config.get("organization", {})
    boundary = section(config, "aims_boundary", {}) or {}
    systems = ai_systems(config)
    scope = override.get("scope") or {
        "organization": organization_name(config),
        "aims_boundary": boundary.get("description", "All AI systems in AIMS scope"),
        "systems_in_scope": [
            s.get("system_id") or s.get("system_ref")
            for s in systems
            if s.get("system_id") or s.get("system_ref")
        ] or ["all"],
        "reporting_period_start": override.get("reporting_period_start", "2026-01-01"),
        "reporting_period_end": override.get("reporting_period_end", "2026-12-31"),
        "intended_recipient": override.get("intended_recipient", "internal-audit"),
    }
    inputs: dict[str, Any] = {
        "source_dir": str(artifacts_root),
        "output_dir": str(bundle_output_dir),
        "scope": scope,
        "signing_algorithm": override.get("signing_algorithm", "none"),
        "include_source_crosswalk": override.get("include_source_crosswalk", False),
    }
    if "bundle_id" in override:
        inputs["bundle_id"] = override["bundle_id"]
    if "reviewed_by" in override:
        inputs["reviewed_by"] = override["reviewed_by"]
    return inputs


def build_certification_readiness_inputs(
    config: dict[str, Any], *, bundle_path: Any
) -> dict[str, Any]:
    """Build inputs for certification-readiness. Requires a packed bundle path."""
    override = section(config, "certification_readiness_inputs") or {}
    return {
        "bundle_path": str(bundle_path),
        "target_certification": override.get("target_certification", "iso42001-stage1"),
        "scope_overrides": override.get("scope_overrides", {}),
    }


def build_certification_path_planner_inputs(
    config: dict[str, Any], *, readiness_snapshot: dict[str, Any]
) -> dict[str, Any]:
    """Build inputs for certification-path-planner from a prior readiness output."""
    from datetime import datetime, timedelta, timezone
    override = section(config, "certification_path_planner_inputs") or {}
    default_target_date = (
        datetime.now(timezone.utc).date() + timedelta(days=180)
    ).isoformat()
    inputs: dict[str, Any] = {
        "current_readiness_ref": readiness_snapshot,
        "target_certification": override.get(
            "target_certification",
            readiness_snapshot.get("target_certification", "iso42001-stage1"),
        ),
        "target_date": override.get("target_date", default_target_date),
    }
    if "organization_capacity" in override:
        inputs["organization_capacity"] = override["organization_capacity"]
    if "risk_register" in override:
        inputs["risk_register"] = override["risk_register"]
    return inputs


def build_cascade_impact_inputs(config: dict[str, Any]) -> dict[str, Any]:
    """Build default query for cascade-impact-analyzer.

    Not invoked by default CLI runs; only when --include-query-plugins is
    passed. Exercises the plugin against a representative trigger event.
    """
    override = section(config, "cascade_impact_inputs") or {}
    trigger_event = override.get("trigger_event") or {
        "event": "risk.new_high_risk_registered",
    }
    inputs: dict[str, Any] = {"trigger_event": trigger_event}
    if "max_hops" in override:
        inputs["max_hops"] = override["max_hops"]
    return inputs


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
