"""
AIGovOps: Audit Log Generator Plugin

Generates ISO/IEC 42001:2023-compliant audit log entries from AI system
governance events.

This plugin operationalizes the audit-log-entry artifact type defined in the
iso42001 skill's operationalization map. It produces records suitable for the
`audit-log-entry` artifact described in skills/iso42001/SKILL.md, specifically
in service of Clause 9.1 (monitoring and performance evaluation) and Annex A
controls A.6.2.3 (design and development documentation), A.6.2.8 (AI system
log recording), and A.3.2 (AI roles).

Status: Phase 3 minimum-viable implementation. Validates inputs, performs
rule-based Annex A control mapping, emits structured audit log entries in
both dict (for JSON serialization) and Markdown forms. Rendering to PDF or
DOCX is deferred to a separate rendering plugin per the Output Standards
section of the iso42001 skill.

Style: all citations use the STYLE.md format. No em-dashes, no emojis, no
hedging language in output strings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "audit-log-generator/0.1.0"

REQUIRED_INPUT_FIELDS = (
    "system_name",
    "purpose",
    "risk_tier",
    "data_processed",
    "deployment_context",
    "governance_decisions",
    "responsible_parties",
)

VALID_RISK_TIERS = ("minimal", "limited", "high", "unacceptable")

# Classifiers used by map_to_annex_a_controls. Each entry is
# (predicate, control_id, rationale_template). Predicates receive the
# system_description dict and return a bool.
_CONTROL_RULES = (
    (
        lambda s: True,
        "A.6.2.3",
        "AI system design and development documentation is required for every AI system in AIMS scope.",
    ),
    (
        lambda s: True,
        "A.6.2.8",
        "AI system log recording applies to every deployed AI system.",
    ),
    (
        lambda s: bool(s.get("responsible_parties")),
        "A.3.2",
        "AI-specific roles and responsibilities are documented; responsible parties are named in the input.",
    ),
    (
        lambda s: s.get("risk_tier") == "high",
        "A.5.4",
        "Risk tier is high; AI system impact on individuals and groups must be assessed per Clause 6.1.4 and documented under Annex A, Control A.5.4.",
    ),
    (
        lambda s: s.get("risk_tier") in ("high", "limited"),
        "A.6.2.4",
        "Verification and validation activities apply to AI systems at limited and high risk tiers.",
    ),
    (
        lambda s: s.get("risk_tier") == "high",
        "A.6.2.6",
        "Operational monitoring applies to deployed AI systems at high risk tier.",
    ),
    (
        lambda s: _has_sensitive_data(s),
        "A.7.2",
        "Data for development and enhancement of AI systems is in scope; sensitive data categories referenced in data_processed.",
    ),
    (
        lambda s: _has_sensitive_data(s),
        "A.7.5",
        "Data provenance tracking applies; sensitive data categories referenced in data_processed.",
    ),
    (
        lambda s: _is_high_impact_context(s),
        "A.5.5",
        "Deployment context implies broader societal impact; societal impact assessment applies per Annex A, Control A.5.5.",
    ),
    (
        lambda s: bool(s.get("governance_decisions")),
        "A.8.3",
        "Governance decisions are present and may constitute external reporting events; external reporting control applies where decisions are communicated outside the organization.",
    ),
)


def _has_sensitive_data(system_description: dict[str, Any]) -> bool:
    """Return True if data_processed references categories typically treated as sensitive."""
    sensitive_markers = (
        "pii",
        "personal",
        "health",
        "medical",
        "financial",
        "biometric",
        "genetic",
        "children",
        "minor",
        "protected",
    )
    items = system_description.get("data_processed") or []
    text = " ".join(str(x).lower() for x in items)
    return any(marker in text for marker in sensitive_markers)


def _is_high_impact_context(system_description: dict[str, Any]) -> bool:
    """Return True if deployment_context suggests broader societal or high-stakes impact."""
    high_impact_markers = (
        "clinical",
        "healthcare",
        "medical",
        "hospital",
        "emergency",
        "lending",
        "credit",
        "employment",
        "hr ",
        " hr",
        "hiring",
        "criminal",
        "law enforcement",
        "judicial",
        "education",
        "immigration",
        "public",
        "welfare",
    )
    context = str(system_description.get("deployment_context", "")).lower()
    return any(marker in context for marker in high_impact_markers)


def _validate(system_description: dict[str, Any]) -> None:
    """Raise ValueError if required fields are missing or malformed. No silent defaults."""
    if not isinstance(system_description, dict):
        raise ValueError("system_description must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in system_description]
    if missing:
        raise ValueError(f"system_description missing required fields: {sorted(missing)}")
    risk_tier = system_description.get("risk_tier")
    if risk_tier not in VALID_RISK_TIERS:
        raise ValueError(
            f"risk_tier must be one of {VALID_RISK_TIERS}; got {risk_tier!r}"
        )
    if not isinstance(system_description.get("data_processed"), list):
        raise ValueError("data_processed must be a list")
    if not isinstance(system_description.get("governance_decisions"), list):
        raise ValueError("governance_decisions must be a list")
    if not isinstance(system_description.get("responsible_parties"), list):
        raise ValueError("responsible_parties must be a list")


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string with seconds precision."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _annex_a_citation(control_id: str) -> str:
    """Format an Annex A control citation per STYLE.md."""
    return f"ISO/IEC 42001:2023, Annex A, Control {control_id}"


def _clause_citation(clause: str) -> str:
    """Format a main-body clause citation per STYLE.md."""
    return f"ISO/IEC 42001:2023, Clause {clause}"


def map_to_annex_a_controls(system_description: dict[str, Any]) -> list[dict[str, str]]:
    """
    Map an AI system description to applicable ISO 42001 Annex A controls.

    Args:
        system_description: Dict containing system_name, purpose, risk_tier,
                            data_processed, deployment_context,
                            governance_decisions, responsible_parties.

    Returns:
        List of dicts, each with:
            control_id: Annex A control identifier (for example "A.6.2.4").
            citation: Full STYLE.md citation string.
            rationale: Why this control applies to the described system.

    Raises:
        ValueError: if required input fields are missing or malformed.
    """
    _validate(system_description)
    mappings: list[dict[str, str]] = []
    seen: set[str] = set()
    for predicate, control_id, rationale in _CONTROL_RULES:
        if control_id in seen:
            continue
        try:
            if predicate(system_description):
                mappings.append(
                    {
                        "control_id": control_id,
                        "citation": _annex_a_citation(control_id),
                        "rationale": rationale,
                    }
                )
                seen.add(control_id)
        except Exception as exc:
            # Predicates operate on validated input; a predicate failure here
            # is an internal error, not a user-input error.
            raise RuntimeError(f"Control rule evaluation failed for {control_id}: {exc}") from exc
    return mappings


def generate_audit_log(system_description: dict[str, Any]) -> dict[str, Any]:
    """
    Generate an ISO/IEC 42001:2023-compliant audit log entry for an AI system
    governance event.

    Args:
        system_description: Dict containing system_name, purpose, risk_tier,
                            data_processed, deployment_context,
                            governance_decisions, responsible_parties.

    Returns:
        Dict containing:
            timestamp: ISO 8601 UTC timestamp of log generation.
            system_name: echoed from input.
            clause_mappings: list of main-body Clause citations applicable
                             to this event (for example Clause 9.1 for
                             monitoring and Clause 7.5 for documented
                             information).
            annex_a_mappings: list of Annex A control dicts from
                              map_to_annex_a_controls.
            evidence_items: list of decisions, each with its citation
                            anchor.
            human_readable_summary: natural-language summary suitable for
                                    inclusion in an audit evidence package.
            agent_signature: identifier of the generating agent.

    Raises:
        ValueError: if required input fields are missing or malformed.
    """
    _validate(system_description)

    annex_a_mappings = map_to_annex_a_controls(system_description)

    clause_mappings = [
        _clause_citation("7.5.2"),
        _clause_citation("9.1"),
    ]
    if system_description.get("governance_decisions"):
        # Governance decisions imply a Clause 9.3 management-review connection
        # and a Clause 5.3 authority reference.
        clause_mappings.append(_clause_citation("5.3"))
        clause_mappings.append(_clause_citation("9.3"))
    if system_description.get("risk_tier") == "high":
        # High risk tier implies Clause 6.1.4 AISIA trigger.
        clause_mappings.append(_clause_citation("6.1.4"))

    evidence_items = [
        {
            "decision": str(decision),
            "citation_anchor": _clause_citation("9.3"),
        }
        for decision in system_description["governance_decisions"]
    ]

    responsible_parties_str = ", ".join(
        str(p) for p in system_description["responsible_parties"]
    )
    summary = (
        f"AI governance event recorded for system {system_description['system_name']}. "
        f"System purpose: {system_description['purpose']}. "
        f"Risk tier: {system_description['risk_tier']}. "
        f"Deployment context: {system_description['deployment_context']}. "
        f"Responsible parties: {responsible_parties_str}. "
        f"Applicable Annex A controls: {', '.join(m['control_id'] for m in annex_a_mappings)}."
    )

    return {
        "timestamp": _utc_now_iso(),
        "system_name": system_description["system_name"],
        "clause_mappings": clause_mappings,
        "annex_a_mappings": annex_a_mappings,
        "evidence_items": evidence_items,
        "human_readable_summary": summary,
        "agent_signature": AGENT_SIGNATURE,
    }


def render_markdown(audit_log: dict[str, Any]) -> str:
    """
    Render an audit log dict as a human-readable Markdown document.

    Args:
        audit_log: The dict returned by generate_audit_log.

    Returns:
        A Markdown string suitable for inclusion in an audit evidence package.
    """
    required = ("timestamp", "system_name", "clause_mappings", "annex_a_mappings", "evidence_items", "human_readable_summary")
    missing = [k for k in required if k not in audit_log]
    if missing:
        raise ValueError(f"audit_log missing required fields: {missing}")

    lines = [
        f"# AI Governance Audit Log Entry",
        "",
        f"**System:** {audit_log['system_name']}",
        f"**Timestamp (UTC):** {audit_log['timestamp']}",
        f"**Generated by:** {audit_log.get('agent_signature', 'unknown')}",
        "",
        "## Summary",
        "",
        audit_log["human_readable_summary"],
        "",
        "## Applicable Main-Body Clauses",
        "",
    ]
    for citation in audit_log["clause_mappings"]:
        lines.append(f"- {citation}")
    lines.extend(["", "## Applicable Annex A Controls", ""])
    if not audit_log["annex_a_mappings"]:
        lines.append("- None identified for this event.")
    else:
        for mapping in audit_log["annex_a_mappings"]:
            lines.append(f"- **{mapping['control_id']}** ({mapping['citation']}): {mapping['rationale']}")
    lines.extend(["", "## Evidence Items", ""])
    if not audit_log["evidence_items"]:
        lines.append("- No governance decisions referenced.")
    else:
        for item in audit_log["evidence_items"]:
            lines.append(f"- {item['decision']} [{item['citation_anchor']}]")
    lines.append("")
    return "\n".join(lines)
