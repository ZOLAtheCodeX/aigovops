"""
AIGovOps: Management Review Input Package Packager Plugin

Composes the ISO/IEC 42001:2023 Clause 9.3.2 management review input package
from organizational sources of record.

Operationalizes the `review-minutes` preamble artifact defined in the
iso42001 skill's Tier 1 T1.4. Emits an audit-log-entry hook for the
package distribution event per Clause 7.5.3.

Clause 9.3.2 requires the input package to cover seven categories:

1. Status of actions from previous management reviews.
2. Changes in external and internal issues relevant to the AIMS.
3. Information on AIMS performance: KPIs, internal audit results,
   nonconformity trends, fulfillment of AI objectives.
4. Feedback from interested parties.
5. AI risks and opportunities.
6. Opportunities for continual improvement.

The package is a pre-read distributed to top management before the review
meeting itself (Clause 9.3.1). The agent assembles the package; humans
conduct the meeting; outputs (Clause 9.3.3) are captured separately.

Design stance: the plugin is an aggregator. Every category is populated
from a supplied source-of-record reference, not from narrative summaries.
Empty categories surface warnings. The plugin does not synthesize or
editorialize.

Status: Phase 3 minimum-viable implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "management-review-packager/0.1.0"

# Clause 9.3.2 input categories. Order is enforced in output so the
# package presents consistently for reviewers across cycles.
INPUT_CATEGORIES = (
    ("previous_review_actions", "Status of actions from previous management reviews", "ISO/IEC 42001:2023, Clause 9.3.2(a)"),
    ("external_internal_issues_changes", "Changes in external and internal issues relevant to the AIMS", "ISO/IEC 42001:2023, Clause 4.1"),
    ("aims_performance", "Information on AIMS performance", "ISO/IEC 42001:2023, Clause 9.1"),
    ("audit_results", "Internal audit results", "ISO/IEC 42001:2023, Clause 9.2"),
    ("nonconformity_trends", "Nonconformity and corrective action trends", "ISO/IEC 42001:2023, Clause 10.2"),
    ("objective_fulfillment", "Fulfillment of AI objectives", "ISO/IEC 42001:2023, Clause 6.2"),
    ("stakeholder_feedback", "Feedback from interested parties", "ISO/IEC 42001:2023, Clause 4.2"),
    ("ai_risks_and_opportunities", "AI risks and opportunities", "ISO/IEC 42001:2023, Clause 6.1"),
    ("continual_improvement_opportunities", "Opportunities for continual improvement", "ISO/IEC 42001:2023, Clause 10.1"),
)

REQUIRED_INPUT_FIELDS = ("review_window", "attendees")


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    window = inputs["review_window"]
    if not isinstance(window, dict) or "start" not in window or "end" not in window:
        raise ValueError("review_window must be a dict with 'start' and 'end' ISO dates")

    attendees = inputs["attendees"]
    if not isinstance(attendees, list) or not attendees:
        raise ValueError("attendees must be a non-empty list of role names")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _summarize_input(value: Any) -> dict[str, Any]:
    """Turn a supplied input into a structured summary entry."""
    if value is None:
        return {
            "source_ref": None,
            "trend_direction": None,
            "breach_flags": [],
            "populated": False,
        }
    if isinstance(value, str):
        return {
            "source_ref": value,
            "trend_direction": None,
            "breach_flags": [],
            "populated": True,
        }
    if isinstance(value, dict):
        return {
            "source_ref": value.get("source_ref") or value.get("ref"),
            "trend_direction": value.get("trend_direction"),
            "breach_flags": list(value.get("breach_flags") or []),
            "populated": True,
        }
    if isinstance(value, list):
        return {
            "source_ref": None,
            "trend_direction": None,
            "breach_flags": [],
            "populated": bool(value),
            "items": list(value),
        }
    return {
        "source_ref": str(value),
        "trend_direction": None,
        "breach_flags": [],
        "populated": True,
    }


def generate_review_package(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Assemble the Clause 9.3.2 management review input package.

    Args:
        inputs: Dict with:
            review_window: dict with 'start' and 'end' ISO dates.
            attendees: non-empty list of role names.
            previous_review_actions: list or source ref.
            external_internal_issues_changes: list or source ref.
            aims_performance: dict with source_ref, trend_direction,
                              breach_flags.
            audit_results: list or source ref.
            nonconformity_trends: dict with source_ref + trend_direction.
            objective_fulfillment: dict with source_ref + trend_direction.
            stakeholder_feedback: list or source ref.
            ai_risks_and_opportunities: list or source ref (typically a risk
                                        register reference).
            continual_improvement_opportunities: list or source ref.
            meeting_metadata: optional dict with scheduled_date,
                              location, etc.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, citations, sections (one
        per Clause 9.3.2 category), summary, warnings, distribution_hook,
        reviewed_by.

    Raises:
        ValueError: if review_window or attendees are missing or malformed.
    """
    _validate(inputs)
    timestamp = _utc_now_iso()
    review_window = inputs["review_window"]
    attendees = inputs["attendees"]

    sections = []
    warnings: list[str] = []
    populated_count = 0

    for key, title, citation in INPUT_CATEGORIES:
        value = inputs.get(key)
        summary = _summarize_input(value)
        if summary["populated"]:
            populated_count += 1
        else:
            warnings.append(
                f"Clause 9.3.2 category '{title}' is not populated (source_ref not provided). "
                "Every category must reference a source of record, not a narrative summary."
            )
        sections.append({
            "key": key,
            "title": title,
            "citation": citation,
            **summary,
        })

    distribution_hook = {
        "event": "management-review-input-package-distributed",
        "timestamp": timestamp,
        "distribution_list": attendees,
        "citation": "ISO/IEC 42001:2023, Clause 7.5.3",
        "package_window": review_window,
    }

    summary = {
        "total_categories": len(INPUT_CATEGORIES),
        "populated_categories": populated_count,
        "unpopulated_categories": len(INPUT_CATEGORIES) - populated_count,
        "attendee_count": len(attendees),
        "review_window_start": review_window["start"],
        "review_window_end": review_window["end"],
    }

    return {
        "timestamp": timestamp,
        "agent_signature": AGENT_SIGNATURE,
        "citations": [
            "ISO/IEC 42001:2023, Clause 9.3.2",
            "ISO/IEC 42001:2023, Clause 7.5.3",
        ],
        "review_window": review_window,
        "attendees": attendees,
        "meeting_metadata": inputs.get("meeting_metadata") or {},
        "sections": sections,
        "distribution_hook": distribution_hook,
        "summary": summary,
        "warnings": warnings,
        "reviewed_by": inputs.get("reviewed_by"),
    }


def render_markdown(package: dict[str, Any]) -> str:
    """Render the management review input package as Markdown."""
    required = ("timestamp", "agent_signature", "citations", "sections", "summary")
    missing = [k for k in required if k not in package]
    if missing:
        raise ValueError(f"package missing required fields: {missing}")

    review_window = package.get("review_window", {})
    attendees = package.get("attendees", [])
    meta = package.get("meeting_metadata", {})

    lines = [
        "# Management Review Input Package",
        "",
        f"**Generated at (UTC):** {package['timestamp']}",
        f"**Generated by:** {package['agent_signature']}",
        f"**Review window:** {review_window.get('start', '?')} to {review_window.get('end', '?')}",
    ]
    if meta.get("scheduled_date"):
        lines.append(f"**Meeting scheduled:** {meta['scheduled_date']}")
    if meta.get("location"):
        lines.append(f"**Location:** {meta['location']}")
    if package.get("reviewed_by"):
        lines.append(f"**Prepared for review by:** {package['reviewed_by']}")
    lines.extend([
        "",
        "## Attendees",
        "",
    ])
    for a in attendees:
        lines.append(f"- {a}")

    lines.extend([
        "",
        "## Applicable Citations",
        "",
    ])
    for c in package["citations"]:
        lines.append(f"- {c}")

    summary = package["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Categories populated: {summary['populated_categories']} of {summary['total_categories']}",
        f"- Attendee count: {summary['attendee_count']}",
        "",
        "## Input Categories",
        "",
    ])
    for section in package["sections"]:
        lines.extend([
            f"### {section['title']}",
            "",
            f"**Citation:** {section['citation']}",
        ])
        if section["populated"]:
            if section.get("source_ref"):
                lines.append(f"**Source of record:** {section['source_ref']}")
            if section.get("trend_direction"):
                lines.append(f"**Trend direction:** {section['trend_direction']}")
            if section.get("breach_flags"):
                lines.append(f"**Breach flags:** {', '.join(section['breach_flags'])}")
            if section.get("items") is not None:
                lines.append("**Items:**")
                lines.append("")
                for item in section["items"]:
                    lines.append(f"- {item}")
        else:
            lines.append("**Not populated.** Every Clause 9.3.2 input category must reference a source of record.")
        lines.append("")

    hook = package.get("distribution_hook")
    if hook:
        lines.extend([
            "## Distribution audit-log hook",
            "",
            f"- Event: {hook['event']}",
            f"- Timestamp: {hook['timestamp']}",
            f"- Distribution list: {', '.join(hook['distribution_list'])}",
            f"- Citation: {hook['citation']}",
            "",
        ])

    if package.get("warnings"):
        lines.extend(["## Warnings", ""])
        for w in package["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)
