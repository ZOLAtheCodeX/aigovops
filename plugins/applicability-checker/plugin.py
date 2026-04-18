"""
AIGovOps: EU AI Act Applicability Checker Plugin

Given a system description, a target date, and the enforcement-timeline
and delegated-acts data from skills/eu-ai-act/, produces a report naming
which provisions apply now, which are pending (with dates), and which
delegated acts or codes of practice affect the organization at the
target date.

Design stance: the plugin does NOT interpret legal applicability. The
Regulation's applicability rules for a given system are data-driven from
the system's risk classification (is_high_risk, is_gpai, and so on), the
target date, and the enforcement-timeline data. Legal edge cases
(Article 6(3) exception, Article 25 role flips, and so on) remain human
determinations; the plugin surfaces the questions, not the answers.

Status: Phase 3 implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "applicability-checker/0.1.0"

REQUIRED_INPUT_FIELDS = (
    "system_description",
    "target_date",
    "enforcement_timeline",
)


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    system = inputs["system_description"]
    if not isinstance(system, dict):
        raise ValueError("system_description must be a dict")

    target_date = inputs["target_date"]
    if not isinstance(target_date, str):
        raise ValueError("target_date must be an ISO date string (YYYY-MM-DD)")
    try:
        _parse_date(target_date)
    except ValueError as exc:
        raise ValueError(f"target_date must be ISO 8601: {exc}") from exc

    timeline = inputs["enforcement_timeline"]
    if not isinstance(timeline, dict) or "enforcement_events" not in timeline:
        raise ValueError("enforcement_timeline must be a dict with 'enforcement_events'")
    if not isinstance(timeline["enforcement_events"], list):
        raise ValueError("enforcement_timeline.enforcement_events must be a list")

    delegated = inputs.get("delegated_acts")
    if delegated is not None and not isinstance(delegated, dict):
        raise ValueError("delegated_acts, when provided, must be a dict")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_date(date_str: str) -> datetime:
    """Parse an ISO 8601 date or datetime. Returns a date-only datetime for comparison."""
    clean = date_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        # Accept date-only 'YYYY-MM-DD'.
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)


def _is_event_applicable_to_system(
    event: dict[str, Any], system: dict[str, Any]
) -> bool:
    """Return True if the enforcement event's provisions apply to this system.

    This filters the event's effective_provisions by system properties:
    GPAI obligations apply only to GPAI providers; high-risk obligations
    apply only to high-risk systems; prohibitions apply to all.
    """
    phase = (event.get("phase") or "").lower()
    # Prohibited-practices phase applies to every system.
    if phase == "prohibited-practices-applicable":
        return True
    # Entry-into-force applies to every system.
    if phase == "entry-into-force":
        return True
    # GPAI-specific phases apply only to GPAI models.
    if "gpai" in phase:
        return bool(system.get("is_gpai"))
    # Annex-I extended-transition applies only to Annex I-route high-risk.
    if "annex-i" in phase:
        return bool(system.get("is_annex_i_product"))
    # Core obligations apply to high-risk systems.
    if phase == "core-obligations-applicable":
        return bool(system.get("is_high_risk"))
    # Legacy-system sunset applies to systems placed before 2 Aug 2025.
    if phase == "member-state-legacy-transition-sunset":
        placed_before = system.get("placed_on_market_before")
        if not placed_before:
            return False
        try:
            return _parse_date(placed_before) < _parse_date("2025-08-02")
        except ValueError:
            return False
    # Codes of practice apply to GPAI providers.
    if phase == "codes-of-practice-expected":
        return bool(system.get("is_gpai"))
    # Default: applies to every system (err toward inclusion for planning).
    return True


def _derive_organizational_actions(
    events: list[dict[str, Any]], system: dict[str, Any]
) -> list[dict[str, Any]]:
    """Collect organizational_actions from applicable events for the system."""
    actions: list[dict[str, Any]] = []
    for event in events:
        if not _is_event_applicable_to_system(event, system):
            continue
        for action in event.get("organizational_actions") or []:
            actions.append({
                "effective_from": event.get("date"),
                "phase": event.get("phase"),
                "action": action,
                "citation": event.get("citation"),
            })
    return actions


def _select_delegated_acts(
    delegated: dict[str, Any] | None, system: dict[str, Any]
) -> dict[str, Any]:
    """Return the subset of delegated-act entries relevant to this system."""
    if not delegated:
        return {"guidelines_and_codes": [], "harmonised_standards": [],
                "delegated_acts": [], "implementing_acts": [],
                "high_priority_monitors": []}

    relevance_bucket: dict[str, list[dict[str, Any]]] = {
        "guidelines_and_codes": [],
        "harmonised_standards": [],
        "delegated_acts": [],
        "implementing_acts": [],
    }

    is_gpai = bool(system.get("is_gpai"))
    is_high_risk = bool(system.get("is_high_risk"))

    for bucket in ("guidelines_and_codes", "harmonised_standards",
                   "delegated_acts", "implementing_acts"):
        for entry in delegated.get(bucket) or []:
            # Heuristic relevance filter based on empowering article and subject.
            subject = (entry.get("subject") or "").lower()
            empowering = (entry.get("empowering_article") or "").lower()

            relevant = False
            if "gpai" in subject or "general-purpose" in subject or "article 51" in empowering or "article 56" in empowering:
                relevant = is_gpai
            elif "high-risk" in subject or "chapter iii" in subject or "article 40" in empowering:
                relevant = is_high_risk
            elif "article 5" in empowering or "prohibit" in subject:
                relevant = True  # Applies to everyone.
            elif "article 6" in empowering or "annex iii" in subject.lower():
                relevant = True  # Classification guidance applies to everyone.
            elif "article 27" in subject.lower() or "fria" in subject.lower():
                relevant = is_high_risk
            elif "article 47" in empowering or "article 48" in empowering or "article 49" in empowering:
                relevant = is_high_risk
            else:
                relevant = True  # Default inclusive for planning.

            if relevant:
                relevance_bucket[bucket].append(entry)

    return {
        **relevance_bucket,
        "high_priority_monitors": delegated.get("high_priority_monitors") or [],
    }


def check_applicability(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Produce an EU AI Act applicability report for a system at a target date.

    Args:
        inputs: Dict with:
            system_description: dict with booleans is_high_risk, is_gpai,
                                is_systemic_risk_gpai, is_annex_i_product,
                                and optional placed_on_market_before (ISO date).
            target_date: ISO date (YYYY-MM-DD) or datetime string.
            enforcement_timeline: loaded YAML structure from
                                  skills/eu-ai-act/enforcement-timeline.yaml.
            delegated_acts: optional loaded YAML from
                            skills/eu-ai-act/delegated-acts.yaml.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, target_date, system_description,
        applicable_provisions, pending_provisions, organizational_actions,
        delegated_act_status, citations, warnings, reviewed_by.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    target = _parse_date(inputs["target_date"])
    system = inputs["system_description"]
    timeline = inputs["enforcement_timeline"]
    delegated = inputs.get("delegated_acts")

    applicable_events: list[dict[str, Any]] = []
    pending_events: list[dict[str, Any]] = []

    for event in timeline["enforcement_events"]:
        date_str = event.get("date")
        if not date_str:
            continue
        try:
            event_date = _parse_date(date_str)
        except ValueError:
            continue
        event_meta = {
            "date": date_str,
            "phase": event.get("phase"),
            "description": event.get("description"),
            "effective_provisions": event.get("effective_provisions") or [],
            "citation": event.get("citation"),
            "applies_to_system": _is_event_applicable_to_system(event, system),
        }
        if event_date <= target:
            applicable_events.append(event_meta)
        else:
            pending_events.append(event_meta)

    organizational_actions = _derive_organizational_actions(
        [e for e in timeline["enforcement_events"] if _parse_date(e.get("date", "1970-01-01")) <= target and _is_event_applicable_to_system(e, system)],
        system,
    )

    delegated_status = _select_delegated_acts(delegated, system)

    warnings: list[str] = []
    if not applicable_events:
        warnings.append(
            f"No enforcement events apply as of {inputs['target_date']}. This likely means the "
            "target_date is before the Regulation's entry into force (2024-08-01)."
        )

    pending_relevant = [e for e in pending_events if e["applies_to_system"]]
    if pending_relevant:
        warnings.append(
            f"{len(pending_relevant)} enforcement event(s) not yet applicable to this system. "
            "Pre-effective-date planning outputs should carry 'planning; effective DD Month YYYY' annotations."
        )

    top_citations = [
        "EU AI Act, Article 113 (entry into force and application)",
    ]
    if system.get("is_high_risk"):
        top_citations.append("EU AI Act, Article 6 (classification as high-risk)")
    if system.get("is_gpai"):
        top_citations.append("EU AI Act, Article 51 (GPAI model classification)")

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "eu-ai-act",
        "target_date": inputs["target_date"],
        "system_description_echo": system,
        "applicable_events": applicable_events,
        "pending_events": pending_events,
        "organizational_actions": organizational_actions,
        "delegated_act_status": delegated_status,
        "citations": top_citations,
        "warnings": warnings,
        "reviewed_by": inputs.get("reviewed_by"),
        "summary": {
            "target_date": inputs["target_date"],
            "applicable_event_count": len(applicable_events),
            "pending_event_count": len(pending_events),
            "pending_relevant_to_system": len(pending_relevant),
            "organizational_action_count": len(organizational_actions),
            "is_high_risk": bool(system.get("is_high_risk")),
            "is_gpai": bool(system.get("is_gpai")),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    required = ("timestamp", "target_date", "applicable_events", "pending_events", "summary")
    missing = [k for k in required if k not in report]
    if missing:
        raise ValueError(f"report missing required fields: {missing}")

    lines = [
        f"# EU AI Act Applicability Report: {report['target_date']}",
        "",
        f"**Generated at (UTC):** {report['timestamp']}",
        f"**Generated by:** {report['agent_signature']}",
        f"**Target date:** {report['target_date']}",
    ]
    sys_desc = report.get("system_description_echo", {})
    if sys_desc.get("system_name"):
        lines.append(f"**System:** {sys_desc['system_name']}")
    lines.extend([
        f"**High-risk:** {sys_desc.get('is_high_risk', False)}",
        f"**GPAI:** {sys_desc.get('is_gpai', False)}",
        "",
        "## Summary",
        "",
        f"- Applicable enforcement events: {report['summary']['applicable_event_count']}",
        f"- Pending events (all): {report['summary']['pending_event_count']}",
        f"- Pending events relevant to this system: {report['summary']['pending_relevant_to_system']}",
        f"- Organizational actions due: {report['summary']['organizational_action_count']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in report["citations"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Applicable enforcement events", ""])
    if not report["applicable_events"]:
        lines.append("_No events applicable at this date._")
    for event in report["applicable_events"]:
        lines.extend([
            f"### {event['date']}: {event.get('phase', 'event')}",
            "",
            event.get("description", ""),
            "",
            "**Effective provisions:**",
            "",
        ])
        for prov in event.get("effective_provisions", []):
            lines.append(f"- {prov}")
        if event.get("citation"):
            lines.append(f"\n**Citation:** {event['citation']}")
        lines.append("")

    lines.extend(["## Pending events (not yet applicable)", ""])
    if not report["pending_events"]:
        lines.append("_No pending events._")
    for event in report["pending_events"]:
        applies = event["applies_to_system"]
        marker = "[relevant to system]" if applies else "[not relevant to system]"
        lines.append(f"- {event['date']}: {event.get('phase', 'event')} {marker}")

    actions = report.get("organizational_actions") or []
    if actions:
        lines.extend(["", "## Organizational actions due", ""])
        for a in actions:
            lines.append(f"- [{a['effective_from']}] {a['action']}")

    delegated = report.get("delegated_act_status") or {}
    relevant_items: list[str] = []
    for bucket in ("guidelines_and_codes", "harmonised_standards",
                   "delegated_acts", "implementing_acts"):
        for entry in delegated.get(bucket, []):
            relevant_items.append(f"[{bucket}] {entry.get('subject', entry.get('id', 'unknown'))} - {entry.get('status', 'status unknown')}")
    if relevant_items:
        lines.extend(["", "## Relevant secondary instruments", ""])
        for item in relevant_items:
            lines.append(f"- {item}")

    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in report["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)
