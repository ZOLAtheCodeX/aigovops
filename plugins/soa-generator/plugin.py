"""
AIGovOps: Statement of Applicability Generator Plugin

Generates ISO/IEC 42001:2023-compliant Statements of Applicability (SoAs).

This plugin operationalizes the `SoA-row` artifact type defined in the
iso42001 skill's Tier 1 T1.1 (Clause 6.1.3). The SoA is the
certification-audit centerpiece: it records, for every Annex A control,
whether the control is included or excluded from the AIMS, with a
justification grounded in the organization's context, risk register, and
implementation posture.

Design stance: the plugin does NOT invent applicability. It reads the
organization's risk register, treatment decisions, implementation plans,
and explicit exclusion justifications, then emits one SoA-row per Annex A
control with its status computed from those inputs. Rows that lack the
evidence required for a clean status (for example, an excluded control
with no justification, a partially-implemented control with no plan
reference) are emitted with a specific warning so the reviewer can
correct the input.

Status: Phase 3 minimum-viable implementation. Every control ID and title
is authored against the operationalization map; verification against the
published standard text is flagged on the relevant IDs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "soa-generator/0.1.0"

# Default Annex A control list with titles as best-recalled from the
# operationalization map. Control IDs and titles require standard-text
# verification before submission as audit evidence. The count is 38 per
# the published standard.
DEFAULT_ANNEX_A_CONTROLS: tuple[tuple[str, str], ...] = (
    ("A.2.2", "AI policy"),
    ("A.2.3", "Alignment with other organizational policies"),
    ("A.2.4", "Review of the AI policy"),
    ("A.3.2", "AI roles and responsibilities"),
    ("A.3.3", "Reporting of concerns"),
    ("A.4.2", "Resource documentation"),
    ("A.4.3", "Data resources"),
    ("A.4.4", "Tooling resources"),
    ("A.4.5", "System and computing resources"),
    ("A.4.6", "Human resources"),
    ("A.5.2", "AI system impact assessment process"),
    ("A.5.3", "Documentation of AI system impact assessments"),
    ("A.5.4", "Assessing AI system impact on individuals or groups"),
    ("A.5.5", "Assessing societal impacts of AI systems"),
    ("A.6.1.2", "Objectives for responsible development of AI systems"),
    ("A.6.1.3", "Processes for responsible design and development"),
    ("A.6.2.2", "AI system requirements and specification"),
    ("A.6.2.3", "Documentation of AI system design and development"),
    ("A.6.2.4", "AI system verification and validation"),
    ("A.6.2.5", "AI system deployment"),
    ("A.6.2.6", "AI system operation and monitoring"),
    ("A.6.2.7", "AI system technical documentation"),
    ("A.6.2.8", "AI system log recording"),
    ("A.7.2", "Data for development and enhancement of AI systems"),
    ("A.7.3", "Acquisition of data"),
    ("A.7.4", "Quality of data for AI systems"),
    ("A.7.5", "Data provenance"),
    ("A.7.6", "Data preparation"),
    ("A.8.2", "System documentation and information for users"),
    ("A.8.3", "External reporting"),
    ("A.8.4", "Communication of incidents"),
    ("A.8.5", "Information for interested parties"),
    ("A.9.2", "Processes for responsible use of AI systems"),
    ("A.9.3", "Objectives for responsible use of AI systems"),
    ("A.9.4", "Intended use of the AI system"),
    ("A.10.2", "Allocating responsibilities"),
    ("A.10.3", "Suppliers"),
    ("A.10.4", "Customers"),
)

VALID_STATUSES = (
    "included-implemented",
    "included-partial",
    "included-planned",
    "excluded",
)

REQUIRED_INPUT_FIELDS = ("ai_system_inventory",)


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")
    inv = inputs["ai_system_inventory"]
    if not isinstance(inv, list):
        raise ValueError("ai_system_inventory must be a list")

    for field_name in ("risk_register", "annex_a_controls"):
        value = inputs.get(field_name)
        if value is not None and not isinstance(value, list):
            raise ValueError(f"{field_name}, when provided, must be a list")

    for field_name in ("implementation_plans", "exclusion_justifications", "scope_notes"):
        value = inputs.get(field_name)
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"{field_name}, when provided, must be a dict keyed by control_id")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _annex_a_citation(control_id: str) -> str:
    return f"ISO/IEC 42001:2023, Annex A, Control {control_id}"


def _normalize_controls(
    provided: list[Any] | None,
) -> list[dict[str, str]]:
    """Return list of {control_id, control_title} dicts from provided or default."""
    source = provided if provided else [
        {"control_id": cid, "control_title": title}
        for cid, title in DEFAULT_ANNEX_A_CONTROLS
    ]
    normalized: list[dict[str, str]] = []
    for entry in source:
        if isinstance(entry, dict):
            cid = entry.get("control_id")
            title = entry.get("control_title", "")
        elif isinstance(entry, str):
            cid = entry
            title = ""
        else:
            raise ValueError(f"annex_a_controls entry must be dict or string; got {type(entry).__name__}")
        if not cid or not isinstance(cid, str):
            raise ValueError(f"annex_a_controls entry missing control_id: {entry!r}")
        normalized.append({"control_id": cid, "control_title": title})
    return normalized


def _controls_linked_by_risk_register(
    risk_register: list[dict[str, Any]] | None,
) -> dict[str, list[str]]:
    """Return map of control_id to list of risk row ids that reference it."""
    linked: dict[str, list[str]] = {}
    if not risk_register:
        return linked
    for risk_row in risk_register:
        row_id = risk_row.get("id", "<no-id>")
        controls = risk_row.get("existing_controls") or []
        for ctrl in controls:
            if isinstance(ctrl, dict):
                cid = ctrl.get("control_id")
            elif isinstance(ctrl, str):
                cid = ctrl
            else:
                continue
            if cid:
                linked.setdefault(cid, []).append(row_id)
    return linked


def _compute_status_and_justification(
    control_id: str,
    linked_risks: dict[str, list[str]],
    implementation_plans: dict[str, Any],
    exclusion_justifications: dict[str, str],
) -> tuple[str, str, str | None, list[str]]:
    """Return (status, justification, implementation_plan_ref, warnings)."""
    warnings: list[str] = []

    # Explicit exclusion has highest priority; auditor accepts justified exclusions.
    if control_id in exclusion_justifications:
        justification = exclusion_justifications[control_id]
        if not justification or not str(justification).strip():
            warnings.append(
                f"Control {control_id} is marked excluded but the justification is blank. "
                "Exclusion justifications must reference AI-system-inventory, scope, or another management system."
            )
        return "excluded", str(justification or ""), None, warnings

    plan_entry = implementation_plans.get(control_id)

    # Implementation plan with target date => planned; without target date but existing => partial.
    if plan_entry:
        plan_status = plan_entry.get("status", "planned") if isinstance(plan_entry, dict) else "planned"
        plan_ref = plan_entry.get("plan_ref") if isinstance(plan_entry, dict) else str(plan_entry)
        if plan_status in ("partial", "included-partial"):
            return "included-partial", f"Partial implementation per plan {plan_ref}.", plan_ref, warnings
        target_date = plan_entry.get("target_date") if isinstance(plan_entry, dict) else None
        if not target_date:
            warnings.append(
                f"Control {control_id} is in implementation_plans but no target_date is set; "
                "planned and partial statuses must reference a plan with a target date."
            )
        justification = f"Planned implementation per plan {plan_ref}"
        if target_date:
            justification += f" targeting {target_date}"
        return "included-planned", justification + ".", plan_ref, warnings

    # Risk-register linkage => implemented; the risk register rows document the control's use.
    if control_id in linked_risks:
        risks = ", ".join(linked_risks[control_id])
        return (
            "included-implemented",
            f"Control is referenced by risk register rows: {risks}.",
            None,
            warnings,
        )

    # No evidence either way; emit excluded with an explicit warning so the reviewer knows to decide.
    warnings.append(
        f"Control {control_id} has no exclusion justification and no risk-register or implementation-plan "
        "evidence of inclusion. Reviewer must either justify exclusion or document inclusion before the SoA is audit-ready."
    )
    return (
        "excluded",
        "REQUIRES REVIEWER DECISION: no evidence of inclusion and no exclusion justification provided.",
        None,
        warnings,
    )


def generate_soa(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Generate an ISO/IEC 42001:2023-compliant Statement of Applicability.

    Args:
        inputs: Dict with:
            ai_system_inventory: list of AI systems in AIMS scope.
            risk_register: list of risk-register-row dicts (from the
                           risk-register-builder plugin output).
            annex_a_controls: optional list of {control_id, control_title}
                              dicts or control_id strings. Defaults to the
                              embedded DEFAULT_ANNEX_A_CONTROLS.
            implementation_plans: optional dict mapping control_id to either
                                  a plan_ref string or a dict with plan_ref,
                                  target_date, status ('planned' or 'partial').
            exclusion_justifications: optional dict mapping control_id to
                                      justification text.
            scope_notes: optional dict mapping control_id to a string
                         describing subset-of-systems scope.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, citations, rows, summary,
        warnings, reviewed_by.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)
    controls = _normalize_controls(inputs.get("annex_a_controls"))
    risk_register = inputs.get("risk_register") or []
    implementation_plans = inputs.get("implementation_plans") or {}
    exclusion_justifications = inputs.get("exclusion_justifications") or {}
    scope_notes = inputs.get("scope_notes") or {}

    linked_risks = _controls_linked_by_risk_register(risk_register)

    rows: list[dict[str, Any]] = []
    all_warnings: list[str] = []
    status_counts: dict[str, int] = dict.fromkeys(VALID_STATUSES, 0)
    timestamp = _utc_now_iso()

    for control in controls:
        cid = control["control_id"]
        title = control["control_title"]
        status, justification, plan_ref, row_warnings = _compute_status_and_justification(
            cid, linked_risks, implementation_plans, exclusion_justifications
        )
        status_counts[status] = status_counts.get(status, 0) + 1
        rows.append({
            "control_id": cid,
            "control_title": title,
            "citation": _annex_a_citation(cid),
            "status": status,
            "justification": justification,
            "implementation_plan_ref": plan_ref,
            "scope_note": scope_notes.get(cid),
            "last_reviewed": timestamp,
            "reviewed_by": inputs.get("reviewed_by"),
            "linked_risks": linked_risks.get(cid, []),
            "warnings": row_warnings,
        })
        all_warnings.extend(row_warnings)

    # Register-level cross-checks.
    register_level_warnings: list[str] = []
    if not risk_register:
        register_level_warnings.append(
            "No risk register supplied. SoA inclusion status cannot be grounded in risk evidence; "
            "every control defaults to excluded-with-review-required."
        )
    # Flag if exclusion_justifications reference controls not in the annex_a list.
    known_ids = {c["control_id"] for c in controls}
    for ex_id in exclusion_justifications:
        if ex_id not in known_ids:
            register_level_warnings.append(
                f"exclusion_justifications references control {ex_id} which is not in annex_a_controls; "
                "add it to the list or correct the key."
            )
    for plan_id in implementation_plans:
        if plan_id not in known_ids:
            register_level_warnings.append(
                f"implementation_plans references control {plan_id} which is not in annex_a_controls; "
                "add it to the list or correct the key."
            )

    summary = {
        "total_controls": len(rows),
        "status_counts": status_counts,
        "controls_with_warnings": sum(1 for r in rows if r["warnings"]),
        "risk_register_rows_referenced": sum(len(v) for v in linked_risks.values()),
    }

    return {
        "timestamp": timestamp,
        "agent_signature": AGENT_SIGNATURE,
        "citations": [
            "ISO/IEC 42001:2023, Clause 6.1.3",
        ],
        "rows": rows,
        "summary": summary,
        "warnings": register_level_warnings,
        "reviewed_by": inputs.get("reviewed_by"),
    }


def render_markdown(soa: dict[str, Any]) -> str:
    """Render a Statement of Applicability as a Markdown document."""
    required = ("timestamp", "agent_signature", "citations", "rows", "summary")
    missing = [k for k in required if k not in soa]
    if missing:
        raise ValueError(f"soa missing required fields: {missing}")

    lines = [
        "# Statement of Applicability",
        "",
        f"**Generated at (UTC):** {soa['timestamp']}",
        f"**Generated by:** {soa['agent_signature']}",
    ]
    if soa.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {soa['reviewed_by']}")
    summary = soa["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Total controls: {summary['total_controls']}",
        f"- Status counts: " + ", ".join(f"{k}={v}" for k, v in summary["status_counts"].items()),
        f"- Controls with warnings: {summary['controls_with_warnings']}",
        f"- Risk-register rows referenced: {summary['risk_register_rows_referenced']}",
        "",
        "## Applicable Citation",
        "",
    ])
    for c in soa["citations"]:
        lines.append(f"- {c}")
    lines.extend(["", "## Rows", "", "| Control | Title | Status | Justification | Plan Ref | Scope Note |", "|---|---|---|---|---|---|"])
    for row in soa["rows"]:
        plan_ref = row.get("implementation_plan_ref") or ""
        scope = row.get("scope_note") or ""
        justification = (row.get("justification") or "").replace("|", "\\|")
        lines.append(
            f"| {row['control_id']} | {row.get('control_title') or ''} | {row['status']} | "
            f"{justification} | {plan_ref} | {scope} |"
        )
    if soa.get("warnings"):
        lines.extend(["", "## Register-level warnings", ""])
        for w in soa["warnings"]:
            lines.append(f"- {w}")
    row_warnings = [(r["control_id"], w) for r in soa["rows"] for w in r["warnings"]]
    if row_warnings:
        lines.extend(["", "## Control-level warnings", ""])
        for cid, w in row_warnings:
            lines.append(f"- ({cid}) {w}")
    lines.append("")
    return "\n".join(lines)


def render_csv(soa: dict[str, Any]) -> str:
    """Render a Statement of Applicability as CSV."""
    if "rows" not in soa:
        raise ValueError("soa missing 'rows' field")
    header = "control_id,control_title,status,justification,implementation_plan_ref,scope_note,linked_risks,citation"
    lines = [header]
    for row in soa["rows"]:
        fields = [
            _csv_escape(str(row.get("control_id", ""))),
            _csv_escape(str(row.get("control_title") or "")),
            _csv_escape(str(row.get("status", ""))),
            _csv_escape(str(row.get("justification") or "")),
            _csv_escape(str(row.get("implementation_plan_ref") or "")),
            _csv_escape(str(row.get("scope_note") or "")),
            _csv_escape("; ".join(row.get("linked_risks") or [])),
            _csv_escape(str(row.get("citation") or "")),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
