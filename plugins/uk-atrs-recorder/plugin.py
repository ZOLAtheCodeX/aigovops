"""
AIGovOps: UK Algorithmic Transparency Recording Standard (ATRS) Recorder Plugin

Generates a structured UK ATRS transparency record for a public-sector
algorithmic or AI-assisted decision-making tool. Operationalizes the UK
Central Digital and Data Office (CDDO) Algorithmic Transparency Recording
Standard, version 2.0 template, across its eight canonical sections.

Design stance: the plugin does not invent organizational content. Owner
identity, tool description, impact-assessment conclusions, data categories,
risks, and governance structures must be supplied by the caller. Missing
content surfaces as per-section warnings. Structural problems raise
ValueError.

Authoritative source:
https://www.gov.uk/government/publications/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies

Status: 0.1.0. First secondary-jurisdiction overlay per the AIGovOps
jurisdiction-scope policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "uk-atrs-recorder/0.1.0"

ATRS_STANDARD_URL = (
    "https://www.gov.uk/government/publications/"
    "algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies"
)
ATRS_TEMPLATE_VERSION = "ATRS Template v2.0"

VALID_TIERS = ("tier-1", "tier-2")

REQUIRED_INPUT_FIELDS = ("tier", "tool_description", "owner")

# Canonical eight ATRS sections. Order matters for rendering and CSV output.
ATRS_SECTIONS = (
    "Owner and contact",
    "Tool description",
    "Tool details",
    "Impact assessment",
    "Data",
    "Risks",
    "Governance",
    "Benefits",
)

# Sections mandatory for every Tier 2 record. Tier 1 is the short public
# summary and only requires Owner, Tool description, and Benefits at minimum.
TIER_1_REQUIRED_SECTIONS = ("Owner and contact", "Tool description", "Benefits")
TIER_2_REQUIRED_SECTIONS = ATRS_SECTIONS  # Tier 2 requires all eight.

# Section to input-key mapping. Caller supplies content under these keys.
SECTION_INPUT_KEYS = {
    "Owner and contact": "owner",
    "Tool description": "tool_description",
    "Tool details": "tool_details",
    "Impact assessment": "impact_assessment",
    "Data": "data",
    "Risks": "risks",
    "Governance": "governance",
    "Benefits": "benefits",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _citation(section_name: str) -> str:
    """Return the canonical citation string for a given ATRS section."""
    return f"UK ATRS, Section {section_name}"


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    tier = inputs.get("tier")
    if tier not in VALID_TIERS:
        raise ValueError(f"tier must be one of {VALID_TIERS}; got {tier!r}")

    owner = inputs.get("owner")
    if not isinstance(owner, dict):
        raise ValueError("owner must be a dict")

    tool_description = inputs.get("tool_description")
    if not isinstance(tool_description, dict):
        raise ValueError("tool_description must be a dict")

    # Optional fields must be the right shape when present.
    for key in ("tool_details", "impact_assessment", "data", "governance", "benefits"):
        value = inputs.get(key)
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"{key} must be a dict when provided")

    risks = inputs.get("risks")
    if risks is not None and not isinstance(risks, list):
        raise ValueError("risks must be a list when provided")


def _build_owner_section(owner: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    required = ("organization", "contact_point")
    for key in required:
        if not owner.get(key):
            warnings.append(
                f"owner missing {key!r}; Section Owner and contact requires a "
                "named public sector organization and a contact point for "
                "citizen queries."
            )
    return {
        "section": "Owner and contact",
        "content": {
            "organization": owner.get("organization"),
            "parent_organization": owner.get("parent_organization"),
            "contact_point": owner.get("contact_point"),
            "senior_responsible_owner": owner.get("senior_responsible_owner"),
        },
        "citations": [_citation("Owner and contact")],
        "warnings": warnings,
    }


def _build_tool_description_section(td: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    required = ("name", "purpose", "how_tool_works")
    for key in required:
        if not td.get(key):
            warnings.append(
                f"tool_description missing {key!r}; Section Tool description "
                "requires a name, a plain-English purpose, and a plain-English "
                "explanation of how the tool works."
            )
    return {
        "section": "Tool description",
        "content": {
            "name": td.get("name"),
            "purpose": td.get("purpose"),
            "how_tool_works": td.get("how_tool_works"),
            "decision_subject_scope": td.get("decision_subject_scope"),
            "phase": td.get("phase", "production"),
        },
        "citations": [_citation("Tool description")],
        "warnings": warnings,
    }


def _build_tool_details_section(details: dict[str, Any] | None) -> dict[str, Any]:
    warnings: list[str] = []
    if not details:
        warnings.append(
            "tool_details not supplied; Section Tool details requires model "
            "family, model type, development stage, and system architecture "
            "information."
        )
        details = {}
    for key in ("model_family", "model_type", "system_architecture"):
        if not details.get(key):
            warnings.append(
                f"tool_details missing {key!r}; Section Tool details requires "
                "it for technical reviewers."
            )
    return {
        "section": "Tool details",
        "content": {
            "model_family": details.get("model_family"),
            "model_type": details.get("model_type"),
            "system_architecture": details.get("system_architecture"),
            "training_data_summary": details.get("training_data_summary"),
            "model_performance_metrics": details.get("model_performance_metrics"),
            "third_party_components": details.get("third_party_components") or [],
        },
        "citations": [_citation("Tool details")],
        "warnings": warnings,
    }


def _build_impact_assessment_section(ia: dict[str, Any] | None) -> dict[str, Any]:
    warnings: list[str] = []
    if not ia:
        warnings.append(
            "impact_assessment not supplied; Section Impact assessment requires "
            "at minimum a description of assessments completed (DPIA, EIA, "
            "other) and the citizen-impact dimensions considered."
        )
        ia = {}
    assessments = ia.get("assessments_completed") or []
    if not assessments:
        warnings.append(
            "impact_assessment.assessments_completed is empty; Section Impact "
            "assessment requires references to completed assessments such as "
            "Data Protection Impact Assessment or Equality Impact Assessment."
        )
    if not ia.get("citizen_impact_dimensions"):
        warnings.append(
            "impact_assessment.citizen_impact_dimensions not set; Section "
            "Impact assessment requires enumerated impact dimensions."
        )
    return {
        "section": "Impact assessment",
        "content": {
            "assessments_completed": assessments,
            "citizen_impact_dimensions": ia.get("citizen_impact_dimensions") or [],
            "severity": ia.get("severity"),
            "affected_groups": ia.get("affected_groups") or [],
            "consultation_summary": ia.get("consultation_summary"),
        },
        "citations": [_citation("Impact assessment")],
        "warnings": warnings,
    }


def _build_data_section(data: dict[str, Any] | None) -> dict[str, Any]:
    warnings: list[str] = []
    if not data:
        warnings.append(
            "data not supplied; Section Data requires source, processing "
            "basis, and sharing information."
        )
        data = {}
    for key in ("source", "processing_basis"):
        if not data.get(key):
            warnings.append(
                f"data missing {key!r}; Section Data requires it."
            )
    return {
        "section": "Data",
        "content": {
            "source": data.get("source"),
            "processing_basis": data.get("processing_basis"),
            "data_categories": data.get("data_categories") or [],
            "collection_method": data.get("collection_method"),
            "sharing": data.get("sharing") or [],
            "retention": data.get("retention"),
        },
        "citations": [_citation("Data")],
        "warnings": warnings,
    }


def _build_risks_section(risks: list[Any] | None) -> dict[str, Any]:
    warnings: list[str] = []
    if not risks:
        warnings.append(
            "risks not supplied; Section Risks requires an enumerated list "
            "covering at minimum equity, data quality, and explainability risks."
        )
        risks = []
    normalised: list[dict[str, Any]] = []
    for i, r in enumerate(risks):
        if not isinstance(r, dict):
            warnings.append(f"risks[{i}] is not a dict; skipping")
            continue
        if not r.get("category") or not r.get("description"):
            warnings.append(
                f"risks[{i}] missing 'category' or 'description'; Section Risks "
                "requires both."
            )
        normalised.append({
            "category": r.get("category"),
            "description": r.get("description"),
            "mitigation": r.get("mitigation"),
            "residual_risk": r.get("residual_risk"),
        })
    return {
        "section": "Risks",
        "content": {"risks": normalised},
        "citations": [_citation("Risks")],
        "warnings": warnings,
    }


def _build_governance_section(gov: dict[str, Any] | None) -> dict[str, Any]:
    warnings: list[str] = []
    if not gov:
        warnings.append(
            "governance not supplied; Section Governance requires oversight "
            "body, escalation path, and review cadence."
        )
        gov = {}
    for key in ("oversight_body", "escalation_path", "review_cadence"):
        if not gov.get(key):
            warnings.append(
                f"governance missing {key!r}; Section Governance requires it."
            )
    return {
        "section": "Governance",
        "content": {
            "oversight_body": gov.get("oversight_body"),
            "escalation_path": gov.get("escalation_path"),
            "review_cadence": gov.get("review_cadence"),
            "incident_response": gov.get("incident_response"),
            "human_oversight_model": gov.get("human_oversight_model"),
        },
        "citations": [_citation("Governance")],
        "warnings": warnings,
    }


def _build_benefits_section(benefits: dict[str, Any] | None) -> dict[str, Any]:
    warnings: list[str] = []
    if not benefits:
        warnings.append(
            "benefits not supplied; Section Benefits requires stated benefit "
            "categories and how they are measured."
        )
        benefits = {}
    if not benefits.get("benefit_categories"):
        warnings.append(
            "benefits.benefit_categories not set; Section Benefits requires "
            "at minimum one benefit category and its measurement approach."
        )
    return {
        "section": "Benefits",
        "content": {
            "benefit_categories": benefits.get("benefit_categories") or [],
            "measurement_approach": benefits.get("measurement_approach"),
            "realised_benefits_summary": benefits.get("realised_benefits_summary"),
        },
        "citations": [_citation("Benefits")],
        "warnings": warnings,
    }


SECTION_BUILDERS = {
    "Owner and contact": _build_owner_section,
    "Tool description": _build_tool_description_section,
    "Tool details": _build_tool_details_section,
    "Impact assessment": _build_impact_assessment_section,
    "Data": _build_data_section,
    "Risks": _build_risks_section,
    "Governance": _build_governance_section,
    "Benefits": _build_benefits_section,
}


def generate_atrs_record(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a structured UK ATRS transparency record.

    Args:
        inputs: Dict with:
            tier: 'tier-1' (short public summary) or 'tier-2' (detailed record).
            owner: dict with organization, parent_organization, contact_point,
                   senior_responsible_owner.
            tool_description: dict with name, purpose, how_tool_works,
                              decision_subject_scope, phase.
            tool_details: optional dict (required for tier-2) with model_family,
                          model_type, system_architecture, training_data_summary,
                          model_performance_metrics, third_party_components.
            impact_assessment: optional dict (required for tier-2) with
                               assessments_completed, citizen_impact_dimensions,
                               severity, affected_groups, consultation_summary.
            data: optional dict (required for tier-2) with source,
                  processing_basis, data_categories, collection_method,
                  sharing, retention.
            risks: optional list (required for tier-2) of dicts with category,
                   description, mitigation, residual_risk.
            governance: optional dict (required for tier-2) with oversight_body,
                        escalation_path, review_cadence, incident_response,
                        human_oversight_model.
            benefits: optional dict with benefit_categories,
                      measurement_approach, realised_benefits_summary.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, tier, template_version,
        source_url, sections, citations, summary, warnings, reviewed_by.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    tier = inputs["tier"]
    required_sections = (
        TIER_2_REQUIRED_SECTIONS if tier == "tier-2" else TIER_1_REQUIRED_SECTIONS
    )

    sections: list[dict[str, Any]] = []
    register_warnings: list[str] = []

    for section_name in ATRS_SECTIONS:
        input_key = SECTION_INPUT_KEYS[section_name]
        # Owner and Tool description are dicts; Risks is a list.
        if section_name == "Risks":
            raw = inputs.get("risks")
        else:
            raw = inputs.get(input_key)
        section = SECTION_BUILDERS[section_name](raw)
        sections.append(section)

    # Tier-level gating: if a required section has no input at all, flag it.
    for section_name in required_sections:
        input_key = SECTION_INPUT_KEYS[section_name]
        raw = inputs.get(input_key) if section_name != "Risks" else inputs.get("risks")
        if not raw:
            register_warnings.append(
                f"Tier {tier!r} record missing required Section {section_name!r} "
                "input. Auditor judgment required before publication."
            )

    top_citations = [ATRS_STANDARD_URL, ATRS_TEMPLATE_VERSION] + [
        _citation(name) for name in ATRS_SECTIONS
    ]

    summary = {
        "tier": tier,
        "total_sections": len(sections),
        "sections_with_warnings": sum(1 for s in sections if s["warnings"]),
        "total_warnings": sum(len(s["warnings"]) for s in sections) + len(register_warnings),
    }

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "tier": tier,
        "template_version": ATRS_TEMPLATE_VERSION,
        "source_url": ATRS_STANDARD_URL,
        "sections": sections,
        "citations": top_citations,
        "summary": summary,
        "warnings": register_warnings,
        "reviewed_by": inputs.get("reviewed_by"),
    }


def render_markdown(record: dict[str, Any]) -> str:
    required = ("timestamp", "agent_signature", "tier", "sections", "citations", "summary")
    missing = [k for k in required if k not in record]
    if missing:
        raise ValueError(f"record missing required fields: {missing}")

    lines = [
        "# UK Algorithmic Transparency Recording Standard (ATRS) Record",
        "",
        f"**Generated at (UTC):** {record['timestamp']}",
        f"**Generated by:** {record['agent_signature']}",
        f"**Tier:** {record['tier']}",
        f"**Template version:** {record.get('template_version', '')}",
        f"**Authoritative source:** {record.get('source_url', '')}",
    ]
    if record.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {record['reviewed_by']}")

    summary = record["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Tier: {summary['tier']}",
        f"- Total sections: {summary['total_sections']}",
        f"- Sections with warnings: {summary['sections_with_warnings']}",
        f"- Total warnings: {summary['total_warnings']}",
        "",
        "## Applicable citations",
        "",
    ])
    for c in record["citations"]:
        lines.append(f"- {c}")

    for section in record["sections"]:
        lines.extend([
            "",
            f"## {section['section']}",
            "",
        ])
        content = section["content"]
        if isinstance(content, dict):
            for key, value in content.items():
                lines.append(f"- **{key}:** {_format_value(value)}")
        lines.extend(["", "**Citations:**", ""])
        for c in section["citations"]:
            lines.append(f"- {c}")
        if section["warnings"]:
            lines.extend(["", "**Warnings:**", ""])
            for w in section["warnings"]:
                lines.append(f"- {w}")

    if record.get("warnings"):
        lines.extend(["", "## Record-level warnings", ""])
        for w in record["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        if not value:
            return ""
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.append("; ".join(f"{k}={v}" for k, v in item.items() if v is not None))
            else:
                parts.append(str(item))
        return " | ".join(parts)
    if isinstance(value, dict):
        return "; ".join(f"{k}={v}" for k, v in value.items() if v is not None)
    return str(value)


def render_csv(record: dict[str, Any]) -> str:
    if "sections" not in record:
        raise ValueError("record missing 'sections' field")
    header = "section,citation,warning_count,content_summary"
    lines = [header]
    for section in record["sections"]:
        citation = section["citations"][0] if section["citations"] else ""
        warning_count = len(section["warnings"])
        content_summary = _format_value(section.get("content"))
        fields = [
            _csv_escape(section["section"]),
            _csv_escape(citation),
            _csv_escape(str(warning_count)),
            _csv_escape(content_summary),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
