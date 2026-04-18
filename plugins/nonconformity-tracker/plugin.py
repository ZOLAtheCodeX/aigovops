"""
AIGovOps: Nonconformity and Corrective Action Tracker Plugin

Generates and validates ISO/IEC 42001:2023-compliant nonconformity records
and their corrective-action lifecycle.

Operationalizes the `nonconformity-record` artifact type defined in the
iso42001 skill's Tier 1 T1.5 (Clause 10.2) and nist-ai-rmf skill's T1.7
(MANAGE 4.2 continual improvement framing). Dual-framework support via
the `framework` flag.

Design stance: the plugin does NOT invent nonconformity content. Root
cause analysis, corrective action selection, and effectiveness evaluation
are judgment-bound activities. The plugin validates a list of records
against the Clause 10.2 workflow-state machine, enforces per-state
invariants (for example, status=closed requires effectiveness_review
fields), emits one audit-log-entry hook per state transition, and flags
missing fields as per-record warnings.

Status: Phase 3 minimum-viable implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "nonconformity-tracker/0.1.0"

# Clause 10.2 workflow states, ordered.
WORKFLOW_STATES = (
    "detected",
    "investigated",
    "root-cause-identified",
    "corrective-action-planned",
    "corrective-action-in-progress",
    "corrective-action-complete",
    "effectiveness-reviewed",
    "closed",
)

STATE_INDEX = {state: i for i, state in enumerate(WORKFLOW_STATES)}

VALID_FRAMEWORKS = ("iso42001", "nist", "dual")

REQUIRED_INPUT_FIELDS = ("records",)
REQUIRED_RECORD_FIELDS = (
    "description",
    "source_citation",
    "detected_by",
    "detection_date",
    "status",
)


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    records = inputs["records"]
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    for r in records:
        if not isinstance(r, dict):
            raise ValueError(f"each record must be a dict; got {type(r).__name__}")
        record_missing = [f for f in REQUIRED_RECORD_FIELDS if f not in r]
        if record_missing:
            raise ValueError(
                f"record missing required fields {sorted(record_missing)}: id={r.get('id', '<no id>')}"
            )
        if r["status"] not in WORKFLOW_STATES:
            raise ValueError(
                f"record {r.get('id', '<no id>')} has invalid status {r['status']!r}; "
                f"must be one of {WORKFLOW_STATES}"
            )

    framework = inputs.get("framework", "iso42001")
    if framework not in VALID_FRAMEWORKS:
        raise ValueError(f"framework must be one of {VALID_FRAMEWORKS}; got {framework!r}")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _per_state_warnings(record: dict[str, Any]) -> list[str]:
    """Return warnings based on which fields are required at the record's current state."""
    warnings: list[str] = []
    status = record["status"]
    idx = STATE_INDEX[status]

    if idx >= STATE_INDEX["investigated"]:
        if not record.get("investigation_started_at"):
            warnings.append("investigation_started_at is not set; investigated state requires the start timestamp.")

    if idx >= STATE_INDEX["root-cause-identified"]:
        if not (record.get("root_cause") or "").strip():
            warnings.append("root_cause text is not set; root-cause-identified state requires a root cause description.")
        if not record.get("root_cause_analysis_date"):
            warnings.append("root_cause_analysis_date is not set.")

    if idx >= STATE_INDEX["corrective-action-planned"]:
        actions = record.get("corrective_actions") or []
        if not isinstance(actions, list) or not actions:
            warnings.append("corrective_actions list is empty; corrective-action-planned state requires at least one planned action.")
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                warnings.append(f"corrective_actions[{i}] must be a dict with action, owner, target_date.")
                continue
            for req in ("action", "owner", "target_date"):
                if req not in action or not action[req]:
                    warnings.append(f"corrective_actions[{i}].{req} is not set.")

    if idx >= STATE_INDEX["corrective-action-complete"]:
        actions = record.get("corrective_actions") or []
        for i, action in enumerate(actions):
            if isinstance(action, dict) and not action.get("completed_at"):
                warnings.append(f"corrective_actions[{i}].completed_at is not set; corrective-action-complete requires completion timestamps.")

    if idx >= STATE_INDEX["effectiveness-reviewed"]:
        if not record.get("effectiveness_review_date"):
            warnings.append("effectiveness_review_date is not set.")
        if not (record.get("effectiveness_outcome") or "").strip():
            warnings.append("effectiveness_outcome is not set; effectiveness-reviewed state requires an outcome (effective, partially-effective, ineffective).")
        if not record.get("effectiveness_reviewer"):
            warnings.append("effectiveness_reviewer is not set.")

    if idx >= STATE_INDEX["closed"]:
        if not record.get("closed_at"):
            warnings.append("closed_at is not set.")
        if not record.get("closed_by"):
            warnings.append("closed_by is not set.")
        outcome = (record.get("effectiveness_outcome") or "").lower()
        if outcome == "ineffective":
            warnings.append(
                "status is closed but effectiveness_outcome is 'ineffective'; closing with ineffective outcome is a "
                "Clause 10.2 violation. Reopen the record at investigated or root-cause-identified."
            )

    # History sanity: if state_history is provided, check monotonic progression (skip detected).
    history = record.get("state_history") or []
    if history:
        prior_idx = -1
        for entry in history:
            if not isinstance(entry, dict) or "state" not in entry:
                warnings.append("state_history entries must be dicts with 'state' and 'at' keys.")
                continue
            if entry["state"] not in STATE_INDEX:
                warnings.append(f"state_history entry has invalid state {entry['state']!r}.")
                continue
            cur = STATE_INDEX[entry["state"]]
            if cur < prior_idx:
                warnings.append(
                    f"state_history moves backward from {WORKFLOW_STATES[prior_idx]} to {entry['state']}; "
                    "re-opening is allowed but should be recorded as a new cycle."
                )
            prior_idx = cur

    return warnings


def _inferred_audit_log_events(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive audit-log-entry hooks from state_history entries. Each transition is one hook."""
    history = record.get("state_history") or []
    events: list[dict[str, Any]] = []
    for entry in history:
        if not isinstance(entry, dict) or "state" not in entry:
            continue
        events.append({
            "event": f"nonconformity-transition-to-{entry['state']}",
            "timestamp": entry.get("at"),
            "actor": entry.get("by"),
            "nonconformity_id": record.get("id"),
            "citation": "ISO/IEC 42001:2023, Clause 7.5.2",
        })
    return events


def _citations(framework: str) -> list[str]:
    iso = [
        "ISO/IEC 42001:2023, Clause 10.2",
        "ISO/IEC 42001:2023, Clause 7.5.2",
    ]
    nist = ["MANAGE 4.2"]
    if framework == "iso42001":
        return iso
    if framework == "nist":
        return nist
    return nist + iso


def generate_nonconformity_register(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a validated and enriched nonconformity register.

    Args:
        inputs: Dict with:
            records: list of nonconformity dicts with required fields
                     description, source_citation, detected_by, detection_date,
                     status. Optional: id, investigation_started_at, root_cause,
                     root_cause_analysis_date, corrective_actions (list of
                     {action, owner, target_date, completed_at}),
                     effectiveness_review_date, effectiveness_outcome,
                     effectiveness_reviewer, closed_at, closed_by,
                     risk_register_updates, state_history, improvement_outcome.
            framework: 'iso42001' (default), 'nist', or 'dual'.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, citations, records, state_summary,
        audit_log_events, warnings, summary, reviewed_by.

    Raises:
        ValueError: if structural requirements are not met.
    """
    _validate(inputs)
    framework = inputs.get("framework", "iso42001")
    top_citations = _citations(framework)

    enriched_records: list[dict[str, Any]] = []
    state_counts: dict[str, int] = dict.fromkeys(WORKFLOW_STATES, 0)
    audit_log_events: list[dict[str, Any]] = []

    for i, record in enumerate(inputs["records"]):
        warnings = _per_state_warnings(record)
        state_counts[record["status"]] = state_counts.get(record["status"], 0) + 1
        events = _inferred_audit_log_events(record)
        audit_log_events.extend(events)

        if framework == "nist":
            rec_citations = ["MANAGE 4.2"]
        elif framework == "dual":
            rec_citations = ["MANAGE 4.2", "ISO/IEC 42001:2023, Clause 10.2"]
        else:
            rec_citations = ["ISO/IEC 42001:2023, Clause 10.2"]

        enriched = {
            "id": record.get("id") or f"NC-{i + 1:04d}",
            "status": record["status"],
            "detected_at": record.get("detection_date"),
            "detected_by": record["detected_by"],
            "detection_method": record.get("detection_method"),
            "source_citation": record["source_citation"],
            "description": record["description"],
            "investigation_started_at": record.get("investigation_started_at"),
            "root_cause": record.get("root_cause"),
            "root_cause_analysis_date": record.get("root_cause_analysis_date"),
            "corrective_actions": record.get("corrective_actions") or [],
            "effectiveness_review_date": record.get("effectiveness_review_date"),
            "effectiveness_outcome": record.get("effectiveness_outcome"),
            "effectiveness_reviewer": record.get("effectiveness_reviewer"),
            "closed_at": record.get("closed_at"),
            "closed_by": record.get("closed_by"),
            "risk_register_updates": record.get("risk_register_updates") or [],
            "improvement_outcome": record.get("improvement_outcome"),
            "state_history": record.get("state_history") or [],
            "citations": rec_citations,
            "warnings": warnings,
        }
        enriched_records.append(enriched)

    register_warnings: list[str] = []
    if not enriched_records:
        register_warnings.append(
            "No nonconformity records provided. An empty register is acceptable only if no nonconformities were "
            "detected in the reporting window; document the detection-scope if so."
        )

    open_states = [s for s in WORKFLOW_STATES if s != "closed"]
    open_count = sum(state_counts[s] for s in open_states)

    summary = {
        "total_records": len(enriched_records),
        "state_counts": state_counts,
        "open_records": open_count,
        "closed_records": state_counts["closed"],
        "records_with_warnings": sum(1 for r in enriched_records if r["warnings"]),
        "audit_log_events_emitted": len(audit_log_events),
    }

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": framework,
        "citations": top_citations,
        "records": enriched_records,
        "state_summary": state_counts,
        "audit_log_events": audit_log_events,
        "warnings": register_warnings,
        "summary": summary,
        "reviewed_by": inputs.get("reviewed_by"),
    }


def render_markdown(register: dict[str, Any]) -> str:
    """Render a nonconformity register as Markdown."""
    required = ("timestamp", "agent_signature", "citations", "records", "summary")
    missing = [k for k in required if k not in register]
    if missing:
        raise ValueError(f"register missing required fields: {missing}")

    lines = [
        "# Nonconformity and Corrective Action Register",
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
        f"- Total records: {summary['total_records']}",
        f"- Open: {summary['open_records']}; Closed: {summary['closed_records']}",
        f"- State counts: " + ", ".join(f"{k}={v}" for k, v in summary["state_counts"].items()),
        f"- Records with warnings: {summary['records_with_warnings']}",
        f"- Inferred audit-log events: {summary['audit_log_events_emitted']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in register["citations"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Records", ""])
    if not register["records"]:
        lines.append("_No nonconformity records in this register._")
    for r in register["records"]:
        lines.extend([
            f"### {r['id']}: {r['status']}",
            "",
            f"**Detected:** {r['detected_at']} by {r['detected_by']}",
            f"**Source citation:** {r['source_citation']}",
            f"**Description:** {r['description']}",
            "",
        ])
        if r.get("root_cause"):
            lines.extend([f"**Root cause:** {r['root_cause']}", ""])
        if r["corrective_actions"]:
            lines.append("**Corrective actions:**")
            lines.append("")
            for action in r["corrective_actions"]:
                if isinstance(action, dict):
                    text = action.get("action", "")
                    owner = action.get("owner", "")
                    tgt = action.get("target_date", "")
                    done = action.get("completed_at", "")
                    lines.append(f"- {text} (owner: {owner}; target: {tgt}; completed: {done})")
            lines.append("")
        if r.get("effectiveness_outcome"):
            lines.extend([
                f"**Effectiveness outcome:** {r['effectiveness_outcome']}",
                f"**Reviewer:** {r.get('effectiveness_reviewer', 'not set')} on {r.get('effectiveness_review_date', 'not set')}",
                "",
            ])
        if r.get("improvement_outcome"):
            lines.extend([f"**Improvement outcome:** {r['improvement_outcome']}", ""])
        if r["risk_register_updates"]:
            lines.append("**Risk register updates:** " + ", ".join(r["risk_register_updates"]))
            lines.append("")
        lines.append("**Citations:**")
        lines.append("")
        for c in r["citations"]:
            lines.append(f"- {c}")
        if r["warnings"]:
            lines.extend(["", "**Warnings:**", ""])
            for w in r["warnings"]:
                lines.append(f"- {w}")
        lines.append("")

    if register.get("warnings"):
        lines.extend(["", "## Register-level warnings", ""])
        for w in register["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)
