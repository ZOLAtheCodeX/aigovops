"""
AIGovOps: Role and Responsibility Matrix Generator Plugin

Generates ISO/IEC 42001:2023-compliant role matrices for AI governance
decisions.

This plugin operationalizes the `role-matrix` artifact type defined in the
iso42001 skill's Tier 1 T1.6 and the nist-ai-rmf skill's T1.4. It implements
Clause 5.3 (roles, responsibilities, and authorities) and Annex A Control
A.3.2 (AI roles and responsibilities).

Design stance: the plugin does NOT invent role assignments. Role assignment
is an organizational decision that belongs to top management per Clause 5.3.
The plugin validates an explicit input RACI, enriches it with authority
basis references from the supplied authority register, and marks any
unassigned (decision_category, activity) pair as "requires human assignment".
An organization gets a draft matrix from which to work; it does not get a
hallucinated assignment.

Status: Phase 3 minimum-viable implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "role-matrix-generator/0.1.0"

# Default decision categories per iso42001 SKILL.md T1.6.
DEFAULT_DECISION_CATEGORIES = (
    "AI policy approval",
    "Risk acceptance",
    "SoA approval",
    "AISIA sign-off",
    "Control implementation",
    "Incident response",
    "Audit programme approval",
    "External reporting",
)

# RACI-style activities. "propose" and "consulted" are advisory; "approve" is
# the authority-bearing activity that requires Clause 5.3 sign-off attribution.
DEFAULT_ACTIVITIES = ("propose", "review", "approve", "consulted", "informed")

# Mapping from decision category to the enabling ISO 42001 clause or control
# that justifies the row. Rows cite both Clause 5.3 and A.3.2 (the role
# authority backbone) plus the enabling citation below.
_ENABLING_CITATIONS: dict[str, str] = {
    "AI policy approval": "ISO/IEC 42001:2023, Clause 5.2",
    "Risk acceptance": "ISO/IEC 42001:2023, Clause 6.1.3",
    "SoA approval": "ISO/IEC 42001:2023, Clause 6.1.3",
    "AISIA sign-off": "ISO/IEC 42001:2023, Clause 6.1.4",
    "Control implementation": "ISO/IEC 42001:2023, Clause 8.3",
    "Incident response": "ISO/IEC 42001:2023, Clause 10.2",
    "Audit programme approval": "ISO/IEC 42001:2023, Clause 9.2.2",
    "External reporting": "ISO/IEC 42001:2023, Annex A, Control A.8.3",
}

UNASSIGNED_MARKER = "REQUIRES HUMAN ASSIGNMENT"

REQUIRED_INPUT_FIELDS = (
    "org_chart",
    "role_assignments",
    "authority_register",
)


def _validate(inputs: dict[str, Any]) -> None:
    """Raise ValueError if required inputs are missing or malformed."""
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    org_chart = inputs["org_chart"]
    if not isinstance(org_chart, list) or not all(isinstance(e, dict) and "role_name" in e for e in org_chart):
        raise ValueError("org_chart must be a list of dicts each with a 'role_name' key")

    role_assignments = inputs["role_assignments"]
    if not isinstance(role_assignments, dict):
        raise ValueError("role_assignments must be a dict keyed by (decision_category, activity) tuple or '<category>::<activity>' string")

    authority_register = inputs["authority_register"]
    if not isinstance(authority_register, dict):
        raise ValueError("authority_register must be a dict mapping role_name to authority_basis")

    backup_assignments = inputs.get("backup_assignments", {})
    if not isinstance(backup_assignments, dict):
        raise ValueError("backup_assignments, when provided, must be a dict mapping role_name to backup_role_name")


def _assignment_key(category: str, activity: str) -> str:
    return f"{category}::{activity}"


def _lookup_assignment(assignments: dict[Any, Any], category: str, activity: str) -> str | None:
    """Look up an assignment under either tuple or string-key convention."""
    tuple_key = (category, activity)
    if tuple_key in assignments:
        return assignments[tuple_key]
    string_key = _assignment_key(category, activity)
    if string_key in assignments:
        return assignments[string_key]
    return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _row_citations(category: str) -> list[str]:
    """Return the citation anchors for a row: always Clause 5.3 and A.3.2, plus the category's enabling clause when known."""
    citations = [
        "ISO/IEC 42001:2023, Clause 5.3",
        "ISO/IEC 42001:2023, Annex A, Control A.3.2",
    ]
    enabling = _ENABLING_CITATIONS.get(category)
    if enabling and enabling not in citations:
        citations.append(enabling)
    return citations


def generate_role_matrix(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Generate an ISO 42001-compliant role and responsibility matrix.

    Args:
        inputs: Dict containing at least:
            org_chart: list of {role_name, reports_to (optional)}.
            role_assignments: dict keyed either by (decision_category, activity)
                              tuple or "<decision_category>::<activity>" string,
                              mapping to role_name present in org_chart.
            authority_register: dict mapping role_name to authority_basis string
                                (organizational policy reference, job description
                                reference, or delegation record).
        Optional:
            decision_categories: list of strings; defaults to DEFAULT_DECISION_CATEGORIES.
            activities: list of strings; defaults to DEFAULT_ACTIVITIES.
            backup_assignments: dict mapping role_name to backup_role_name.
            reviewed_by: named reviewer of the matrix.

    Returns:
        Dict with:
            timestamp: ISO 8601 UTC timestamp at matrix generation.
            agent_signature: plugin version.
            citations: top-level citation anchors for the whole matrix.
            rows: list of row dicts; one per (decision_category, activity) pair.
            unassigned_rows: list of row keys where no assignment was provided.
            warnings: list of warning strings (for example, unknown roles in
                      role_assignments that are not present in org_chart).

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    decision_categories = list(inputs.get("decision_categories") or DEFAULT_DECISION_CATEGORIES)
    activities = list(inputs.get("activities") or DEFAULT_ACTIVITIES)
    org_chart = inputs["org_chart"]
    known_roles: set[str] = {entry["role_name"] for entry in org_chart}
    role_assignments = inputs["role_assignments"]
    authority_register = inputs["authority_register"]
    backup_assignments = inputs.get("backup_assignments") or {}
    reviewed_by = inputs.get("reviewed_by")

    rows: list[dict[str, Any]] = []
    unassigned_rows: list[str] = []
    warnings: list[str] = []

    seen_approve_for_category: dict[str, str] = {}

    for category in decision_categories:
        for activity in activities:
            role_name = _lookup_assignment(role_assignments, category, activity)
            if role_name is None:
                row_role = UNASSIGNED_MARKER
                authority_basis = None
                unassigned_rows.append(_assignment_key(category, activity))
            else:
                if role_name not in known_roles:
                    warnings.append(
                        f"Role '{role_name}' assigned to ({category!r}, {activity!r}) is not present in org_chart; "
                        "add it to org_chart or correct the assignment."
                    )
                row_role = role_name
                authority_basis = authority_register.get(role_name)
                if activity == "approve":
                    authority_basis = authority_basis or UNASSIGNED_MARKER
                if role_name not in authority_register:
                    warnings.append(
                        f"Role '{role_name}' assigned to ({category!r}, {activity!r}) has no entry in authority_register; "
                        "authority_basis for approval rows must not be blank per Clause 5.3."
                    )
                if activity == "approve":
                    prior = seen_approve_for_category.get(category)
                    if prior and prior != role_name:
                        warnings.append(
                            f"Multiple approve-activity roles for decision_category '{category}': "
                            f"'{prior}' and '{role_name}'. Exactly one approver role is required."
                        )
                    else:
                        seen_approve_for_category[category] = role_name

            backup_role = None
            if row_role != UNASSIGNED_MARKER:
                backup_role = backup_assignments.get(row_role)
                if activity == "approve" and not backup_role:
                    warnings.append(
                        f"Role '{row_role}' has approve-activity authority for '{category}' but no backup is defined; "
                        "continuity requires a backup role for every role with approval authority."
                    )

            rows.append(
                {
                    "decision_category": category,
                    "activity": activity,
                    "role_name": row_role,
                    "authority_basis": authority_basis,
                    "backup_role_name": backup_role,
                    "citations": _row_citations(category),
                }
            )

    # Cross-check: every decision_category has exactly one approve-activity role.
    for category in decision_categories:
        if category not in seen_approve_for_category:
            warnings.append(
                f"decision_category '{category}' has no approve-activity assignment; "
                "every decision category requires exactly one approver role per Clause 5.3."
            )

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "citations": [
            "ISO/IEC 42001:2023, Clause 5.3",
            "ISO/IEC 42001:2023, Annex A, Control A.3.2",
        ],
        "rows": rows,
        "unassigned_rows": unassigned_rows,
        "warnings": warnings,
        "reviewed_by": reviewed_by,
    }


def render_markdown(matrix: dict[str, Any]) -> str:
    """
    Render a role matrix as a human-readable Markdown document.

    Args:
        matrix: The dict returned by generate_role_matrix.

    Returns:
        A Markdown string with a summary, a citation block, a per-row table,
        and a warnings section. Suitable for inclusion in audit evidence
        packages and for review by the authority approving the matrix.

    Raises:
        ValueError: if matrix is missing required fields.
    """
    required = ("timestamp", "agent_signature", "citations", "rows", "unassigned_rows", "warnings")
    missing = [k for k in required if k not in matrix]
    if missing:
        raise ValueError(f"matrix missing required fields: {missing}")

    lines = [
        "# AI Governance Role and Responsibility Matrix",
        "",
        f"**Generated at (UTC):** {matrix['timestamp']}",
        f"**Generated by:** {matrix['agent_signature']}",
    ]
    if matrix.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {matrix['reviewed_by']}")
    lines.extend([
        "",
        "## Applicable Citations",
        "",
    ])
    for citation in matrix["citations"]:
        lines.append(f"- {citation}")

    lines.extend(["", "## Assignments", "", "| Decision Category | Activity | Role | Authority Basis | Backup Role |", "|---|---|---|---|---|"])
    for row in matrix["rows"]:
        category = row["decision_category"]
        activity = row["activity"]
        role = row["role_name"] or UNASSIGNED_MARKER
        authority = row.get("authority_basis") or ""
        backup = row.get("backup_role_name") or ""
        lines.append(f"| {category} | {activity} | {role} | {authority} | {backup} |")

    if matrix["unassigned_rows"]:
        lines.extend(["", "## Unassigned rows", "", f"The following {len(matrix['unassigned_rows'])} row(s) require human assignment before this matrix is used as audit evidence:", ""])
        for key in matrix["unassigned_rows"]:
            lines.append(f"- {key}")

    if matrix["warnings"]:
        lines.extend(["", "## Warnings", "", f"The following {len(matrix['warnings'])} warning(s) require attention:", ""])
        for warning in matrix["warnings"]:
            lines.append(f"- {warning}")

    lines.append("")
    return "\n".join(lines)


def render_csv(matrix: dict[str, Any]) -> str:
    """
    Render a role matrix as CSV for spreadsheet ingestion.

    Columns: decision_category, activity, role_name, authority_basis, backup_role_name, citations.
    Citations are joined with '; ' within the cell.

    Args:
        matrix: The dict returned by generate_role_matrix.

    Returns:
        A CSV string with a header row and one row per matrix row.

    Raises:
        ValueError: if matrix is missing required fields.
    """
    if "rows" not in matrix:
        raise ValueError("matrix missing 'rows' field")
    lines = ["decision_category,activity,role_name,authority_basis,backup_role_name,citations"]
    for row in matrix["rows"]:
        fields = [
            _csv_escape(row["decision_category"]),
            _csv_escape(row["activity"]),
            _csv_escape(row["role_name"] or UNASSIGNED_MARKER),
            _csv_escape(row.get("authority_basis") or ""),
            _csv_escape(row.get("backup_role_name") or ""),
            _csv_escape("; ".join(row.get("citations", []))),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
