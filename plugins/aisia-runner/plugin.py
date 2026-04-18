"""
AIGovOps: AI System Impact Assessment (AISIA) Runner Plugin

Generates ISO/IEC 42001:2023 Clause 6.1.4 AISIAs and NIST AI RMF 1.0 MAP
1.1, 3.1, 3.2, 5.1 impact assessments.

This plugin operationalizes the `AISIA-section` artifact type defined in
the iso42001 skill's Tier 1 T1.2 and the nist-ai-rmf skill's T1.1. A
single implementation serves both frameworks; rendering differences are
controlled by a `framework` flag that determines which citation family is
emitted.

Design stance: the plugin does NOT invent impacts. Impact identification is
a judgment-bound activity requiring stakeholder consultation and domain
expertise per Clause 6.1.4 and A.5.4/A.5.5. The plugin accepts provided
impact assessments, enriches each with computed residual severity and
likelihood from the supplied rubric, cross-links existing controls to
SoA rows, flags missing fields as row-level warnings, and optionally
scaffolds empty placeholders for (stakeholder, impact_dimension) pairs
without identified impacts so reviewers can see coverage gaps.

Status: Phase 3 minimum-viable implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "aisia-runner/0.1.0"

# Default impact dimensions required by Clause 6.1.4 and addressed by
# Annex A controls A.5.4 (individual and group impacts) and A.5.5
# (societal impacts).
DEFAULT_IMPACT_DIMENSIONS = (
    "fundamental-rights",
    "group-fairness",
    "societal",
    "physical-safety",
)

DEFAULT_SEVERITY_SCALE = ("negligible", "minor", "moderate", "major", "catastrophic")
DEFAULT_LIKELIHOOD_SCALE = ("rare", "unlikely", "possible", "likely", "almost-certain")

VALID_FRAMEWORKS = ("iso42001", "nist", "dual")

REQUIRED_INPUT_FIELDS = ("system_description", "affected_stakeholders")


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    system = inputs["system_description"]
    if not isinstance(system, dict):
        raise ValueError("system_description must be a dict")
    for req in ("system_name", "purpose"):
        if req not in system:
            raise ValueError(f"system_description missing required field: {req}")

    stakeholders = inputs["affected_stakeholders"]
    if not isinstance(stakeholders, list) or not stakeholders:
        raise ValueError("affected_stakeholders must be a non-empty list")
    for s in stakeholders:
        if isinstance(s, str):
            continue
        if isinstance(s, dict) and "name" in s:
            continue
        raise ValueError(f"each stakeholder entry must be a string or a dict with 'name'; got {s!r}")

    framework = inputs.get("framework", "iso42001")
    if framework not in VALID_FRAMEWORKS:
        raise ValueError(f"framework must be one of {VALID_FRAMEWORKS}; got {framework!r}")

    rubric = inputs.get("risk_scoring_rubric")
    if rubric is not None:
        if not isinstance(rubric, dict):
            raise ValueError("risk_scoring_rubric must be a dict")
        # Rubric uses severity_scale (preferred) or impact_scale (legacy).
        if "severity_scale" not in rubric and "impact_scale" not in rubric:
            raise ValueError("risk_scoring_rubric must contain severity_scale (or impact_scale)")
        if "likelihood_scale" not in rubric:
            raise ValueError("risk_scoring_rubric must contain likelihood_scale")

    impact_assessments = inputs.get("impact_assessments")
    if impact_assessments is not None and not isinstance(impact_assessments, list):
        raise ValueError("impact_assessments, when provided, must be a list")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _score_index(value: str | None, scale: tuple[str, ...] | list[str]) -> int | None:
    if value is None:
        return None
    try:
        return list(scale).index(value) + 1
    except ValueError:
        return None


def _stakeholder_name(s: Any) -> str:
    if isinstance(s, str):
        return s
    return s.get("name", "")


def _resolve_control_ref(control: Any, soa_rows_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if isinstance(control, str):
        return {
            "control_id": control,
            "soa_row_ref": soa_rows_by_id.get(control, {}).get("row_ref") if control in soa_rows_by_id else None,
            "description": "",
        }
    if isinstance(control, dict):
        cid = control.get("control_id", "")
        return {
            "control_id": cid,
            "soa_row_ref": soa_rows_by_id.get(cid, {}).get("row_ref") if cid in soa_rows_by_id else None,
            "description": control.get("description", ""),
        }
    return {"control_id": "", "soa_row_ref": None, "description": f"(unrecognized: {control!r})"}


def _iso_citations(dimension: str) -> list[str]:
    citations = [
        "ISO/IEC 42001:2023, Clause 6.1.4",
        "ISO/IEC 42001:2023, Annex A, Control A.5.2",
        "ISO/IEC 42001:2023, Annex A, Control A.5.3",
    ]
    if dimension == "societal":
        citations.append("ISO/IEC 42001:2023, Annex A, Control A.5.5")
    else:
        citations.append("ISO/IEC 42001:2023, Annex A, Control A.5.4")
    return citations


def _nist_citations(dimension: str) -> list[str]:
    base = ["MAP 1.1", "MAP 3.1", "MAP 3.2", "MAP 5.1"]
    if dimension == "physical-safety":
        base.append("MEASURE 2.6")
    return base


def _physical_safety_severity_floor(
    severity: str | None, severity_scale: tuple[str, ...] | list[str]
) -> str | None:
    """Return a warning string if physical-safety severity is below 'moderate', else None."""
    if severity is None:
        return None
    idx = _score_index(severity, severity_scale)
    moderate_idx = _score_index("moderate", severity_scale)
    if idx is None or moderate_idx is None:
        return None
    if idx < moderate_idx:
        return (
            f"Physical-safety severity '{severity}' is below 'moderate' in the scale. "
            "Physical-safety impact classifications below moderate for systems with any patient-harm or "
            "physical-harm potential require explicit justification."
        )
    return None


def _enrich_section(
    entry: dict[str, Any],
    stakeholder_names: set[str],
    dimensions: tuple[str, ...],
    severity_scale: tuple[str, ...] | list[str],
    likelihood_scale: tuple[str, ...] | list[str],
    soa_rows_by_id: dict[str, dict[str, Any]],
    framework: str,
    index: int,
    system_type: str | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []

    stakeholder = entry.get("stakeholder_group") or entry.get("stakeholder")
    if not stakeholder:
        raise ValueError(f"impact_assessment entry {index} missing stakeholder_group")
    if stakeholder not in stakeholder_names:
        warnings.append(
            f"stakeholder_group '{stakeholder}' is not in affected_stakeholders; add it or correct the reference."
        )

    dimension = entry.get("impact_dimension")
    if not dimension:
        raise ValueError(f"impact_assessment entry {index} missing impact_dimension")
    if dimension not in dimensions:
        warnings.append(
            f"impact_dimension '{dimension}' is not in the configured dimensions {list(dimensions)}; "
            "add it or correct the value."
        )

    description = entry.get("impact_description") or entry.get("description") or ""
    if not description.strip():
        warnings.append(
            "impact_description is empty; describe the impact on this stakeholder group before the AISIA is audit-ready."
        )

    severity = entry.get("severity")
    likelihood = entry.get("likelihood")
    if severity is None or likelihood is None:
        warnings.append(
            "severity and likelihood are required for an AISIA section to be audit-ready."
        )
    if severity is not None and _score_index(severity, severity_scale) is None:
        warnings.append(
            f"severity value '{severity}' is not in severity_scale; cannot score."
        )
    if likelihood is not None and _score_index(likelihood, likelihood_scale) is None:
        warnings.append(
            f"likelihood value '{likelihood}' is not in likelihood_scale; cannot score."
        )

    # Physical-safety floor: severity must be at least 'moderate' when the system has any physical-harm potential.
    if dimension == "physical-safety":
        floor_warning = _physical_safety_severity_floor(severity, severity_scale)
        if floor_warning:
            warnings.append(floor_warning)

    residual_severity = entry.get("residual_severity")
    residual_likelihood = entry.get("residual_likelihood")
    existing_controls = [_resolve_control_ref(c, soa_rows_by_id) for c in (entry.get("existing_controls") or [])]
    additional_controls = list(entry.get("additional_controls_recommended") or [])

    if not existing_controls and not additional_controls:
        warnings.append(
            "no existing_controls and no additional_controls_recommended. "
            "Every impact section must list at least one control (existing or recommended) to be audit-ready."
        )

    assessor = entry.get("assessor")
    assessment_date = entry.get("assessment_date")

    if framework == "iso42001":
        citations = _iso_citations(dimension)
    elif framework == "nist":
        citations = _nist_citations(dimension)
    else:
        citations = _nist_citations(dimension) + _iso_citations(dimension)

    return {
        "id": entry.get("id") or f"AISIA-{index:04d}",
        "stakeholder_group": stakeholder,
        "impact_dimension": dimension,
        "impact_description": description,
        "severity": severity,
        "likelihood": likelihood,
        "existing_controls": existing_controls,
        "residual_severity": residual_severity,
        "residual_likelihood": residual_likelihood,
        "additional_controls_recommended": additional_controls,
        "assessor": assessor,
        "assessment_date": assessment_date,
        "citations": citations,
        "warnings": warnings,
    }


def run_aisia(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Execute an AI System Impact Assessment per ISO/IEC 42001:2023 Clause 6.1.4
    and NIST AI RMF MAP subcategories.

    Args:
        inputs: Dict with:
            system_description: dict with system_name, purpose, and optional
                                fields (intended_use, decision_context,
                                deployment_environment, data_categories_processed,
                                decision_authority, reversibility, system_type).
            affected_stakeholders: non-empty list of strings or dicts with 'name'.
            impact_assessments: list of dicts, each with at minimum
                                stakeholder_group, impact_dimension, and
                                optionally severity, likelihood, impact_description,
                                existing_controls, residual_severity,
                                residual_likelihood, additional_controls_recommended,
                                assessor, assessment_date, id.
            impact_dimensions: optional list; defaults to the standard four.
            risk_scoring_rubric: optional dict with severity_scale (or impact_scale)
                                 and likelihood_scale.
            soa_rows: optional list for cross-linking existing controls.
            framework: 'iso42001' (default), 'nist', or 'dual'.
            scaffold: bool (default False). Emit placeholder sections for
                      (stakeholder, dimension) pairs without assessments.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, system_name, citations, sections,
        scaffold_sections, warnings, summary, reviewed_by.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    system = inputs["system_description"]
    system_type = system.get("system_type")
    framework = inputs.get("framework", "iso42001")

    dimensions = tuple(inputs.get("impact_dimensions") or DEFAULT_IMPACT_DIMENSIONS)
    rubric = inputs.get("risk_scoring_rubric") or {
        "severity_scale": list(DEFAULT_SEVERITY_SCALE),
        "likelihood_scale": list(DEFAULT_LIKELIHOOD_SCALE),
    }
    severity_scale = tuple(rubric.get("severity_scale") or rubric.get("impact_scale"))
    likelihood_scale = tuple(rubric["likelihood_scale"])

    stakeholders_raw = inputs["affected_stakeholders"]
    stakeholder_names = {_stakeholder_name(s) for s in stakeholders_raw}
    stakeholders_detail = [s if isinstance(s, dict) else {"name": s} for s in stakeholders_raw]

    soa_rows_by_id = {r["control_id"]: r for r in (inputs.get("soa_rows") or []) if "control_id" in r}

    impact_assessments = inputs.get("impact_assessments") or []
    sections = [
        _enrich_section(entry, stakeholder_names, dimensions, severity_scale, likelihood_scale,
                        soa_rows_by_id, framework, i + 1, system_type)
        for i, entry in enumerate(impact_assessments)
    ]

    scaffold_sections: list[dict[str, str]] = []
    if inputs.get("scaffold"):
        covered = {(s["stakeholder_group"], s["impact_dimension"]) for s in sections}
        for stakeholder in stakeholder_names:
            for dim in dimensions:
                if (stakeholder, dim) not in covered:
                    scaffold_sections.append({
                        "stakeholder_group": stakeholder,
                        "impact_dimension": dim,
                        "placeholder_note": "No impact assessed for this pair. Document an assessment or explicit non-applicability.",
                    })

    register_warnings: list[str] = []
    if not sections:
        register_warnings.append(
            "No impact assessments provided. An empty AISIA is not audit-acceptable; "
            "assess impacts per Clause 6.1.4 and supply impact_assessments."
        )
    if framework in ("iso42001", "dual"):
        top_citations = [
            "ISO/IEC 42001:2023, Clause 6.1.4",
            "ISO/IEC 42001:2023, Annex A, Control A.5.2",
            "ISO/IEC 42001:2023, Annex A, Control A.5.3",
            "ISO/IEC 42001:2023, Annex A, Control A.5.4",
            "ISO/IEC 42001:2023, Annex A, Control A.5.5",
        ]
    else:
        top_citations = []
    if framework in ("nist", "dual"):
        top_citations.extend(["MAP 1.1", "MAP 3.1", "MAP 3.2", "MAP 5.1"])

    summary = {
        "total_sections": len(sections),
        "stakeholders_covered": len({s["stakeholder_group"] for s in sections}),
        "dimensions_covered": len({s["impact_dimension"] for s in sections}),
        "sections_with_warnings": sum(1 for s in sections if s["warnings"]),
        "scaffold_count": len(scaffold_sections),
    }

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "system_name": system["system_name"],
        "system_type": system_type,
        "framework": framework,
        "citations": top_citations,
        "stakeholders": stakeholders_detail,
        "dimensions": list(dimensions),
        "sections": sections,
        "scaffold_sections": scaffold_sections,
        "warnings": register_warnings,
        "summary": summary,
        "reviewed_by": inputs.get("reviewed_by"),
    }


def render_markdown(aisia: dict[str, Any]) -> str:
    """Render an AISIA as a Markdown document."""
    required = ("timestamp", "agent_signature", "system_name", "citations", "sections", "summary")
    missing = [k for k in required if k not in aisia]
    if missing:
        raise ValueError(f"aisia missing required fields: {missing}")

    lines = [
        f"# AI System Impact Assessment: {aisia['system_name']}",
        "",
        f"**Generated at (UTC):** {aisia['timestamp']}",
        f"**Generated by:** {aisia['agent_signature']}",
        f"**Framework rendering:** {aisia.get('framework', 'iso42001')}",
    ]
    if aisia.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {aisia['reviewed_by']}")
    summary = aisia["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Total sections: {summary['total_sections']}",
        f"- Stakeholders covered: {summary['stakeholders_covered']}",
        f"- Dimensions covered: {summary['dimensions_covered']}",
        f"- Sections with warnings: {summary['sections_with_warnings']}",
        f"- Scaffold placeholders: {summary['scaffold_count']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in aisia["citations"]:
        lines.append(f"- {c}")
    lines.extend(["", "## Sections", ""])
    if not aisia["sections"]:
        lines.append("_No impact sections recorded._")
    for section in aisia["sections"]:
        lines.extend([
            f"### {section['id']}: {section['stakeholder_group']} / {section['impact_dimension']}",
            "",
            f"**Severity:** {section.get('severity') or 'not set'}",
            f"**Likelihood:** {section.get('likelihood') or 'not set'}",
            f"**Residual severity:** {section.get('residual_severity') or 'not set'}",
            f"**Residual likelihood:** {section.get('residual_likelihood') or 'not set'}",
            "",
            "**Impact description:**",
            "",
            section.get("impact_description") or "_(not populated)_",
            "",
        ])
        if section["existing_controls"]:
            lines.append("**Existing controls:**")
            lines.append("")
            for ctrl in section["existing_controls"]:
                soa = f" [SoA: {ctrl['soa_row_ref']}]" if ctrl.get("soa_row_ref") else ""
                lines.append(f"- {ctrl['control_id']}{soa}: {ctrl.get('description') or ''}")
            lines.append("")
        if section["additional_controls_recommended"]:
            lines.append("**Additional controls recommended:**")
            lines.append("")
            for ctrl in section["additional_controls_recommended"]:
                lines.append(f"- {ctrl}")
            lines.append("")
        lines.append("**Citations:**")
        lines.append("")
        for c in section["citations"]:
            lines.append(f"- {c}")
        if section["warnings"]:
            lines.append("")
            lines.append("**Warnings:**")
            lines.append("")
            for w in section["warnings"]:
                lines.append(f"- {w}")
        lines.append("")

    if aisia.get("scaffold_sections"):
        lines.extend(["## Coverage gaps", ""])
        for scaf in aisia["scaffold_sections"]:
            lines.append(f"- {scaf['stakeholder_group']} / {scaf['impact_dimension']}: {scaf['placeholder_note']}")

    if aisia.get("warnings"):
        lines.extend(["", "## Document-level warnings", ""])
        for w in aisia["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)
