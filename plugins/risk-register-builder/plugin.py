"""
AIGovOps: AI Risk Register Builder Plugin

Generates ISO/IEC 42001:2023 and NIST AI RMF 1.0-compliant AI risk register
entries.

This plugin operationalizes the `risk-register-row` artifact type defined in
the iso42001 skill's Tier 1 T1.7 (Clauses 6.1.2, 6.1.3, 8.2) and the
nist-ai-rmf skill's T1.3 (MAP 4.1, MANAGE 1.2, 1.3, 1.4). A single
implementation serves both frameworks because the risk-register artifact is
identical in structure; rendering differences are applied via a `framework`
toggle in inputs.

Design stance: the plugin does NOT invent risks. Risk identification is a
hybrid activity requiring domain expertise and stakeholder input per Clause
6.1.2. The plugin validates provided risks against the schema, enriches
each with computed scores, cross-links existing controls to SoA rows when
references are provided, flags rows with missing required fields, and
optionally scaffolds empty placeholders for (system, category) pairs that
have no identified risk yet.

Status: Phase 3 minimum-viable implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "risk-register-builder/0.1.0"

# ISO 42001 default risk taxonomy aligned with trustworthy-AI concerns and
# ISO/IEC 23894:2023 risk-source categories.
DEFAULT_TAXONOMY_ISO = (
    "bias",
    "robustness",
    "privacy",
    "security",
    "accountability",
    "transparency",
    "environmental",
)

# NIST trustworthy-AI characteristics from AI RMF 1.0, used as the default
# taxonomy when framework is 'nist'.
DEFAULT_TAXONOMY_NIST = (
    "valid-and-reliable",
    "safe",
    "secure-and-resilient",
    "accountable-and-transparent",
    "explainable-and-interpretable",
    "privacy-enhanced",
    "fair-with-bias-managed",
)

VALID_TREATMENT_OPTIONS = ("reduce", "retain", "avoid", "share")
VALID_FRAMEWORKS = ("iso42001", "nist", "dual")

DEFAULT_LIKELIHOOD_SCALE = ("rare", "unlikely", "possible", "likely", "almost-certain")
DEFAULT_IMPACT_SCALE = ("negligible", "minor", "moderate", "major", "catastrophic")

REQUIRED_INPUT_FIELDS = ("ai_system_inventory",)
REQUIRED_RISK_FIELDS = ("system_ref", "category", "description")


def _validate_inputs(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    inv = inputs["ai_system_inventory"]
    if not isinstance(inv, list) or not all(
        isinstance(s, dict) and "system_ref" in s and "system_name" in s for s in inv
    ):
        raise ValueError(
            "ai_system_inventory must be a list of dicts each with 'system_ref' and 'system_name'"
        )

    risks = inputs.get("risks") or []
    if not isinstance(risks, list):
        raise ValueError("risks, when provided, must be a list")
    for risk in risks:
        if not isinstance(risk, dict):
            raise ValueError(f"each risk must be a dict; got {type(risk).__name__}")
        risk_missing = [f for f in REQUIRED_RISK_FIELDS if f not in risk]
        if risk_missing:
            raise ValueError(
                f"risk missing required fields {sorted(risk_missing)}: {risk.get('id', '<no id>')}"
            )

    framework = inputs.get("framework", "iso42001")
    if framework not in VALID_FRAMEWORKS:
        raise ValueError(
            f"framework must be one of {VALID_FRAMEWORKS}; got {framework!r}"
        )

    rubric = inputs.get("risk_scoring_rubric")
    if rubric is not None:
        if not isinstance(rubric, dict) or "likelihood_scale" not in rubric or "impact_scale" not in rubric:
            raise ValueError("risk_scoring_rubric must be a dict with 'likelihood_scale' and 'impact_scale'")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _score_index(value: str | None, scale: tuple[str, ...] | list[str]) -> int | None:
    """Return 1-based index of value in scale, or None if not present."""
    if value is None:
        return None
    try:
        return list(scale).index(value) + 1
    except ValueError:
        return None


def _compute_score(likelihood: str | None, impact: str | None,
                   likelihood_scale: tuple[str, ...] | list[str],
                   impact_scale: tuple[str, ...] | list[str]) -> int | None:
    """Compute likelihood x impact score as the product of their 1-based indexes, or None if either is missing or unknown."""
    li = _score_index(likelihood, likelihood_scale)
    ii = _score_index(impact, impact_scale)
    if li is None or ii is None:
        return None
    return li * ii


def _iso_citations_for_row(treatment_option: str | None) -> list[str]:
    citations = [
        "ISO/IEC 42001:2023, Clause 6.1.2",
        "ISO/IEC 42001:2023, Clause 8.2",
    ]
    if treatment_option:
        citations.append("ISO/IEC 42001:2023, Clause 6.1.3")
    return citations


def _nist_citations_for_row(treatment_option: str | None, has_residual_disclosure: bool) -> list[str]:
    citations = [
        "MAP 4.1",
        "MANAGE 1.2",
        "MANAGE 1.3",
    ]
    if has_residual_disclosure:
        citations.append("MANAGE 1.4")
    return citations


def _resolve_control_ref(control: Any, soa_rows_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Normalize a control reference to a dict with control_id, soa_row_ref, description."""
    if isinstance(control, str):
        control_id = control
        description = ""
    elif isinstance(control, dict):
        control_id = control.get("control_id", "")
        description = control.get("description", "")
    else:
        return {
            "control_id": "",
            "soa_row_ref": None,
            "description": f"(unrecognized control reference: {control!r})",
        }
    soa_ref = None
    if control_id and control_id in soa_rows_by_id:
        soa_ref = soa_rows_by_id[control_id].get("row_ref") or control_id
    return {
        "control_id": control_id,
        "soa_row_ref": soa_ref,
        "description": description,
    }


def _enrich_risk(
    risk: dict[str, Any],
    systems_by_ref: dict[str, dict[str, Any]],
    taxonomy: tuple[str, ...],
    rubric: dict[str, Any],
    soa_rows_by_id: dict[str, dict[str, Any]],
    role_matrix_lookup: dict[str, str],
    framework: str,
    index: int,
) -> dict[str, Any]:
    warnings: list[str] = []

    system_ref = risk["system_ref"]
    system = systems_by_ref.get(system_ref)
    if system is None:
        warnings.append(
            f"system_ref '{system_ref}' not found in ai_system_inventory; add the system or correct the reference."
        )
        system_name = None
    else:
        system_name = system.get("system_name")

    category = risk["category"]
    if category not in taxonomy:
        warnings.append(
            f"category '{category}' is not in the risk taxonomy {list(taxonomy)}; add it to the taxonomy or correct the category."
        )

    likelihood_scale = tuple(rubric["likelihood_scale"])
    impact_scale = tuple(rubric["impact_scale"])

    likelihood = risk.get("likelihood")
    impact = risk.get("impact")
    inherent_score = _compute_score(likelihood, impact, likelihood_scale, impact_scale)
    if likelihood is None or impact is None:
        warnings.append(
            "likelihood and impact are required to produce inherent_score; row is incomplete."
        )
    else:
        if _score_index(likelihood, likelihood_scale) is None:
            warnings.append(
                f"likelihood value '{likelihood}' not present in likelihood_scale; cannot score."
            )
        if _score_index(impact, impact_scale) is None:
            warnings.append(
                f"impact value '{impact}' not present in impact_scale; cannot score."
            )

    residual_likelihood = risk.get("residual_likelihood")
    residual_impact = risk.get("residual_impact")
    residual_score = _compute_score(residual_likelihood, residual_impact, likelihood_scale, impact_scale)

    existing_controls = [_resolve_control_ref(c, soa_rows_by_id) for c in (risk.get("existing_controls") or [])]

    treatment_option = risk.get("treatment_option")
    if treatment_option is not None and treatment_option not in VALID_TREATMENT_OPTIONS:
        raise ValueError(
            f"treatment_option for risk '{risk.get('id', '<no id>')}' must be one of {VALID_TREATMENT_OPTIONS}; got {treatment_option!r}"
        )

    owner_role = risk.get("owner_role")
    if owner_role is None and role_matrix_lookup:
        # Allow caller to supply a per-category owner hint via role_matrix_lookup.
        owner_role = role_matrix_lookup.get(category)
    if owner_role is None:
        warnings.append(
            "owner_role is not set; every risk must have an assigned owner per iso42001 T1.7."
        )

    has_residual_disclosure = bool(risk.get("negative_residual_disclosure_ref"))
    if treatment_option == "retain" and not has_residual_disclosure and framework in ("nist", "dual"):
        warnings.append(
            "treatment_option is 'retain' but negative_residual_disclosure_ref is not set; NIST MANAGE 1.4 requires disclosure of negative residual risks to affected AI actors."
        )

    iso_citations = _iso_citations_for_row(treatment_option)
    nist_citations = _nist_citations_for_row(treatment_option, has_residual_disclosure)
    if framework == "iso42001":
        citations = iso_citations
    elif framework == "nist":
        citations = nist_citations
    else:
        citations = nist_citations + iso_citations

    row = {
        "id": risk.get("id") or f"RR-{index:04d}",
        "system_ref": system_ref,
        "system_name": system_name,
        "category": category,
        "description": risk["description"],
        "likelihood": likelihood,
        "impact": impact,
        "inherent_score": inherent_score,
        "scoring_rationale": list(risk.get("scoring_rationale") or []),
        "existing_controls": existing_controls,
        "residual_likelihood": residual_likelihood,
        "residual_impact": residual_impact,
        "residual_score": residual_score,
        "treatment_option": treatment_option,
        "owner_role": owner_role,
        "planned_treatment_actions": list(risk.get("planned_treatment_actions") or []),
        "negative_residual_disclosure_ref": risk.get("negative_residual_disclosure_ref"),
        "citations": citations,
        "warnings": warnings,
    }
    return row


def generate_risk_register(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a structured AI risk register.

    Args:
        inputs: Dict containing:
            ai_system_inventory: list of {system_ref, system_name, risk_tier (optional), ...}.
            risks: list of input risks. Each must contain at minimum system_ref,
                   category, description. Optional: likelihood, impact, scoring_rationale,
                   existing_controls, residual_likelihood, residual_impact,
                   treatment_option, owner_role, planned_treatment_actions,
                   negative_residual_disclosure_ref.
            framework: 'iso42001' (default), 'nist', or 'dual'. Controls citation rendering.
            risk_taxonomy: list of category strings. Defaults based on framework.
            risk_scoring_rubric: dict with likelihood_scale and impact_scale lists.
                                 Defaults to 5-level qualitative scales.
            soa_rows: list of dicts with at least 'control_id' and optional 'row_ref'.
                      Used to cross-link existing_controls.
            role_matrix_lookup: dict mapping category to default owner_role.
                                Applied when a risk has no owner_role.
            scaffold: bool (default False). When True, emit placeholder rows for
                      (system, category) pairs without an identified risk, so
                      reviewers can see coverage gaps.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, citations, rows, scaffold_rows,
        warnings, summary, reviewed_by.

    Raises:
        ValueError: if required inputs are missing, malformed, or invalid.
    """
    _validate_inputs(inputs)

    framework = inputs.get("framework", "iso42001")
    taxonomy = tuple(
        inputs.get("risk_taxonomy")
        or (DEFAULT_TAXONOMY_NIST if framework == "nist" else DEFAULT_TAXONOMY_ISO)
    )
    rubric = inputs.get("risk_scoring_rubric") or {
        "likelihood_scale": list(DEFAULT_LIKELIHOOD_SCALE),
        "impact_scale": list(DEFAULT_IMPACT_SCALE),
    }
    systems_by_ref = {s["system_ref"]: s for s in inputs["ai_system_inventory"]}
    soa_rows_by_id = {r["control_id"]: r for r in (inputs.get("soa_rows") or []) if "control_id" in r}
    role_matrix_lookup = inputs.get("role_matrix_lookup") or {}

    risks_input = inputs.get("risks") or []
    rows = [
        _enrich_risk(risk, systems_by_ref, taxonomy, rubric, soa_rows_by_id, role_matrix_lookup, framework, i + 1)
        for i, risk in enumerate(risks_input)
    ]

    scaffold_rows: list[dict[str, str]] = []
    if inputs.get("scaffold"):
        covered = {(row["system_ref"], row["category"]) for row in rows}
        for system in inputs["ai_system_inventory"]:
            for category in taxonomy:
                if (system["system_ref"], category) not in covered:
                    scaffold_rows.append(
                        {
                            "system_ref": system["system_ref"],
                            "system_name": system.get("system_name", ""),
                            "category": category,
                            "placeholder_note": "No risk identified for this (system, category) pair. Either document that no risk applies, or add a risk entry.",
                        }
                    )

    warnings: list[str] = []
    if framework in ("iso42001", "dual"):
        top_citations = [
            "ISO/IEC 42001:2023, Clause 6.1.2",
            "ISO/IEC 42001:2023, Clause 6.1.3",
            "ISO/IEC 42001:2023, Clause 8.2",
        ]
    else:
        top_citations = []
    if framework in ("nist", "dual"):
        top_citations.extend(["MAP 4.1", "MANAGE 1.2", "MANAGE 1.3", "MANAGE 1.4"])

    if not rows:
        warnings.append(
            "No risks provided. An empty risk register is not audit-acceptable; run risk identification per Clause 6.1.2 and supply risks."
        )

    summary = {
        "total_rows": len(rows),
        "systems_covered": len({row["system_ref"] for row in rows}),
        "systems_in_scope": len(inputs["ai_system_inventory"]),
        "rows_with_warnings": sum(1 for row in rows if row["warnings"]),
        "scaffold_count": len(scaffold_rows),
    }

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": framework,
        "taxonomy": list(taxonomy),
        "citations": top_citations,
        "rows": rows,
        "scaffold_rows": scaffold_rows,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": inputs.get("reviewed_by"),
    }


def render_markdown(register: dict[str, Any]) -> str:
    """
    Render a risk register dict as a human-readable Markdown document.

    Sorted by residual_score descending when available, then inherent_score
    descending; rows with no scores sort last.
    """
    required = ("timestamp", "agent_signature", "citations", "rows", "summary")
    missing = [k for k in required if k not in register]
    if missing:
        raise ValueError(f"register missing required fields: {missing}")

    def sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
        resid = -(row.get("residual_score") or 0)
        inher = -(row.get("inherent_score") or 0)
        has_any = 0 if (row.get("residual_score") or row.get("inherent_score")) else 1
        return (has_any, resid, inher)

    rows_sorted = sorted(register["rows"], key=sort_key)

    lines = [
        "# AI Risk Register",
        "",
        f"**Generated at (UTC):** {register['timestamp']}",
        f"**Generated by:** {register['agent_signature']}",
        f"**Framework rendering:** {register.get('framework', 'iso42001')}",
    ]
    if register.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {register['reviewed_by']}")
    summary = register["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Total rows: {summary['total_rows']}",
        f"- Systems covered: {summary['systems_covered']} of {summary['systems_in_scope']} in scope",
        f"- Rows with warnings: {summary['rows_with_warnings']}",
        f"- Scaffold placeholders: {summary['scaffold_count']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in register["citations"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Rows (sorted by residual risk descending)", ""])
    if not rows_sorted:
        lines.append("_No risks recorded._")
    else:
        lines.append("| ID | System | Category | Inherent | Residual | Treatment | Owner |")
        lines.append("|---|---|---|---|---|---|---|")
        for row in rows_sorted:
            lines.append(
                f"| {row['id']} | {row.get('system_name') or row['system_ref']} | {row['category']} | "
                f"{row.get('inherent_score') or ''} | {row.get('residual_score') or ''} | "
                f"{row.get('treatment_option') or ''} | {row.get('owner_role') or ''} |"
            )

    if register.get("scaffold_rows"):
        lines.extend(["", "## Coverage gaps (scaffold placeholders)", ""])
        for scaf in register["scaffold_rows"]:
            lines.append(f"- {scaf['system_ref']} / {scaf['category']}: {scaf['placeholder_note']}")

    row_warnings = [(row["id"], w) for row in register["rows"] for w in row["warnings"]]
    if row_warnings or register.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in register.get("warnings", []):
            lines.append(f"- (register) {w}")
        for rid, w in row_warnings:
            lines.append(f"- ({rid}) {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(register: dict[str, Any]) -> str:
    """
    Render a risk register as CSV for spreadsheet ingestion.

    Columns: id, system_ref, system_name, category, description,
    likelihood, impact, inherent_score, residual_likelihood,
    residual_impact, residual_score, treatment_option, owner_role,
    citations.
    """
    if "rows" not in register:
        raise ValueError("register missing 'rows' field")
    header = (
        "id,system_ref,system_name,category,description,"
        "likelihood,impact,inherent_score,"
        "residual_likelihood,residual_impact,residual_score,"
        "treatment_option,owner_role,citations"
    )
    lines = [header]
    for row in register["rows"]:
        fields = [
            _csv_escape(str(row.get("id", ""))),
            _csv_escape(str(row.get("system_ref", ""))),
            _csv_escape(str(row.get("system_name", "") or "")),
            _csv_escape(str(row.get("category", ""))),
            _csv_escape(str(row.get("description", ""))),
            _csv_escape(str(row.get("likelihood", "") or "")),
            _csv_escape(str(row.get("impact", "") or "")),
            _csv_escape(str(row.get("inherent_score") or "")),
            _csv_escape(str(row.get("residual_likelihood", "") or "")),
            _csv_escape(str(row.get("residual_impact", "") or "")),
            _csv_escape(str(row.get("residual_score") or "")),
            _csv_escape(str(row.get("treatment_option", "") or "")),
            _csv_escape(str(row.get("owner_role", "") or "")),
            _csv_escape("; ".join(row.get("citations", []))),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
