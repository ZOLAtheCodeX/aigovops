"""
AIGovOps: Incident Reporting Plugin

Regulatory-deadline-aware external incident reporting. Distinct from
nonconformity-tracker, which handles ISO 42001 Clause 10.2 internal
corrective action. This plugin prepares external authority notifications
governed by statutory deadlines: EU AI Act Article 73 (2 / 10 / 15 days),
Colorado SB 205 Sections 6-1-1702(7) and 6-1-1703(7) (90-day Attorney
General disclosure), and NYC Local Law 144 (candidate complaint
disclosure window under DCWP AEDT Rules).

Design stance: the plugin does NOT write the practitioner's narrative and
does NOT transmit reports to authorities. It determines applicability per
jurisdiction, computes filing deadlines, assembles report-draft templates
with required-content checklists, and surfaces content gaps as warnings.
The practitioner completes the narrative and files with the competent
authority.

Status: Phase 3 implementation. 0.1.0.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "incident-reporting/0.1.0"

REQUIRED_INPUT_FIELDS = ("incident_description", "applicable_jurisdictions", "detected_at")

VALID_SEVERITY = (
    "fatal",
    "serious-physical-harm",
    "widespread-infringement",
    "critical-infrastructure-disruption",
    "limited-harm",
    "no-harm",
)

VALID_JURISDICTIONS = (
    "eu",
    "usa-co",
    "usa-nyc",
    "usa-ca",
    "uk",
    "singapore",
    "canada",
)

VALID_ACTOR_ROLES = ("provider", "deployer")

# EU AI Act Article 73 deadlines by severity. Values in days.
# Article 73(6): fatality or widespread infringement = 2 days.
# Article 73(7): serious-physical-harm or critical-infrastructure = 10 days.
# Article 73(2) default: 15 days.
EU_AI_ACT_DEADLINES = {
    "fatal": 2,
    "serious-physical-harm": 10,
    "widespread-infringement": 2,
    "critical-infrastructure-disruption": 10,
    "default": 15,
}

COLORADO_SB205_DEADLINE_DAYS = 90

# DCWP complaint-response window reference. NYC LL144 does not set a
# statutory deadline on the employer for a candidate complaint; 30 days
# is the investigation/response window practitioners apply by convention.
NYC_LL144_COMPLAINT_WINDOW_DAYS = 30

# Sibling-plugin path for crosswalk-matrix-builder. Lazy import.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(ts: str) -> datetime:
    """Parse an ISO 8601 date or datetime as UTC-aware."""
    if not isinstance(ts, str):
        raise ValueError(f"timestamp must be a string; got {type(ts).__name__}")
    clean = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean)
    except ValueError:
        try:
            dt = datetime.strptime(ts, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"detected_at must be ISO 8601; got {ts!r}: {exc}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    incident = inputs["incident_description"]
    if not isinstance(incident, dict):
        raise ValueError("incident_description must be a dict")

    jurisdictions = inputs["applicable_jurisdictions"]
    if not isinstance(jurisdictions, list) or not jurisdictions:
        raise ValueError("applicable_jurisdictions must be a non-empty list")
    for j in jurisdictions:
        if j not in VALID_JURISDICTIONS:
            raise ValueError(
                f"jurisdiction {j!r} not in VALID_JURISDICTIONS {VALID_JURISDICTIONS}"
            )

    detected_at = inputs["detected_at"]
    _parse_iso(detected_at)

    severity = inputs.get("severity")
    if severity is not None and severity not in VALID_SEVERITY:
        raise ValueError(
            f"severity must be one of {VALID_SEVERITY}; got {severity!r}"
        )

    actor_role = inputs.get("actor_role")
    if actor_role is not None and actor_role not in VALID_ACTOR_ROLES:
        raise ValueError(
            f"actor_role must be one of {VALID_ACTOR_ROLES}; got {actor_role!r}"
        )


def _derive_severity(
    incident: dict[str, Any], explicit: str | None
) -> tuple[str, list[str]]:
    """Return (severity, warnings). If explicit is provided, use it."""
    warnings: list[str] = []
    if explicit:
        return explicit, warnings
    potential = incident.get("potential_harms") or []
    normalized = [str(h).lower().strip() for h in potential]
    if any("fatality" in h or "death" in h for h in normalized):
        return "fatal", warnings
    if any("serious physical" in h or "serious injury" in h for h in normalized):
        return "serious-physical-harm", warnings
    if any("widespread infringement" in h for h in normalized):
        return "widespread-infringement", warnings
    if any("critical infrastructure" in h for h in normalized):
        return "critical-infrastructure-disruption", warnings
    warnings.append(
        "severity not provided and could not be derived from potential_harms. "
        "Defaulted to 'limited-harm'. Confirm severity with qualified counsel "
        "before filing with any authority."
    )
    return "limited-harm", warnings


def _eu_deadline_days(severity: str) -> int:
    return EU_AI_ACT_DEADLINES.get(severity, EU_AI_ACT_DEADLINES["default"])


def _status_for(deadline: datetime, now: datetime) -> str:
    if deadline < now:
        return "overdue"
    delta = deadline - now
    if delta <= timedelta(hours=48):
        return "imminent-within-48h"
    return "future"


def _days_remaining(deadline: datetime, now: datetime) -> int:
    """Signed integer days remaining. Negative if overdue."""
    return (deadline.date() - now.date()).days


def _eu_article_73_citation(severity: str) -> str:
    if severity in ("fatal", "widespread-infringement"):
        return "EU AI Act, Article 73, Paragraph 6"
    if severity in ("serious-physical-harm", "critical-infrastructure-disruption"):
        return "EU AI Act, Article 73, Paragraph 7"
    return "EU AI Act, Article 73, Paragraph 2"


def _eu_required_contents_checklist() -> list[str]:
    return [
        "System identity (provider name, system name, version).",
        "Nature of the serious incident.",
        "Chain of events leading to the incident.",
        "Corrective measures taken or planned.",
        "Provider or deployer identification, including authorised representative if applicable.",
        "Affected persons count and geographic scope.",
        "Date of occurrence and date of discovery.",
    ]


def _colorado_required_contents_checklist() -> list[str]:
    return [
        "detected_at timestamp (90-day clock start).",
        "Description of the algorithmic discrimination concern.",
        "Actor role (developer under Section 6-1-1702(7) or deployer under Section 6-1-1703(7)).",
        "Affected consequential decision domain.",
        "Evidence summary supporting the discrimination finding.",
        "Mitigation or corrective action taken or planned.",
        "Identity of the reporting organization and contact.",
    ]


def _nyc_required_contents_checklist() -> list[str]:
    return [
        "AEDT identifier (tool name and version).",
        "Candidate complaint summary.",
        "Employer or employment-agency response.",
        "Compliance posture statement referencing the current bias audit.",
        "Next bias-audit-due date.",
        "Contact for follow-up.",
    ]


def _build_eu_draft(
    incident: dict[str, Any],
    severity: str,
    deadline_iso: str,
    containment: list[str],
    correction_plan: str,
    actor_role: str | None,
    org_contact: str,
) -> dict[str, Any]:
    actor = actor_role or "REQUIRES ACTOR ROLE DETERMINATION"
    affected_systems = incident.get("affected_systems") or []
    summary = incident.get("summary") or "Requires practitioner completion: incident summary"
    occurrence = incident.get("date_of_occurrence") or "Requires practitioner completion: date_of_occurrence"
    discovery = incident.get("date_discovered") or "Requires practitioner completion: date_discovered"
    channel = incident.get("discovery_channel") or "Requires practitioner completion: discovery_channel"
    potential = incident.get("potential_harms") or []
    impacted = incident.get("impacted_persons_count", "unknown")
    scope = incident.get("geographic_scope") or "Requires practitioner completion: geographic_scope"

    contain_lines = "\n".join(f"- {c}" for c in containment) if containment else "- Requires practitioner completion: containment actions"
    corr = correction_plan or "Requires practitioner completion: correction_plan"

    draft = (
        f"# EU AI Act Article 73 Serious Incident Report\n\n"
        f"**Filing deadline (UTC):** {deadline_iso}\n"
        f"**Severity classification:** {severity}\n"
        f"**Actor role:** {actor}\n\n"
        f"## System identity\n\n"
        f"- Affected systems: {', '.join(affected_systems) if affected_systems else 'Requires practitioner completion: affected_systems'}\n"
        f"- Organization contact: {org_contact or 'Requires practitioner completion: organization_contact'}\n\n"
        f"## Nature of the serious incident\n\n"
        f"{summary}\n\n"
        f"## Chain of events\n\n"
        f"- Date of occurrence: {occurrence}\n"
        f"- Date of discovery: {discovery}\n"
        f"- Discovery channel: {channel}\n"
        f"- Potential harms: {', '.join(potential) if potential else 'Requires practitioner completion: potential_harms'}\n"
        f"- Impacted persons count: {impacted}\n"
        f"- Geographic scope: {scope}\n\n"
        f"## Corrective measures\n\n"
        f"Containment actions taken:\n{contain_lines}\n\n"
        f"Correction plan: {corr}\n\n"
        f"## Citation\n\n"
        f"Filed under EU AI Act, Article 73.\n"
    )
    return {
        "jurisdiction": "eu",
        "template_name": "eu-ai-act-article-73",
        "draft_markdown": draft,
        "required_recipient": "EU AI Office via the national competent authority in the Member State of the incident.",
        "required_contents_checklist": _eu_required_contents_checklist(),
        "warnings": [] if actor_role else [
            "Requires practitioner completion: actor_role (provider or deployer under EU AI Act)."
        ],
    }


def _build_colorado_draft(
    incident: dict[str, Any],
    detected_at: str,
    deadline_iso: str,
    actor_role: str | None,
    consequential_domains: list[str],
    containment: list[str],
    correction_plan: str,
    org_contact: str,
) -> dict[str, Any]:
    actor = actor_role or "Requires practitioner completion: developer or deployer"
    summary = incident.get("summary") or "Requires practitioner completion: discrimination concern summary"
    affected_systems = incident.get("affected_systems") or []
    domains_str = ", ".join(consequential_domains) if consequential_domains else "Requires practitioner completion: consequential_domains"
    contain_lines = "\n".join(f"- {c}" for c in containment) if containment else "- Requires practitioner completion: containment actions"
    corr = correction_plan or "Requires practitioner completion: correction_plan"

    # Select the controlling section for the draft's citation line.
    if actor_role == "provider":
        section = "Colorado SB 205, Section 6-1-1702(7)"
    elif actor_role == "deployer":
        section = "Colorado SB 205, Section 6-1-1703(7)"
    else:
        section = "Colorado SB 205, Section 6-1-1702(7) or Section 6-1-1703(7)"

    draft = (
        f"# Colorado AI Act Algorithmic Discrimination Disclosure\n\n"
        f"**Detected at (90-day clock start):** {detected_at}\n"
        f"**Filing deadline (UTC):** {deadline_iso}\n"
        f"**Actor role:** {actor}\n\n"
        f"## Algorithmic discrimination concern\n\n"
        f"{summary}\n\n"
        f"## Affected systems and domains\n\n"
        f"- Affected systems: {', '.join(affected_systems) if affected_systems else 'Requires practitioner completion: affected_systems'}\n"
        f"- Consequential decision domains: {domains_str}\n\n"
        f"## Evidence summary\n\n"
        f"Requires practitioner completion: evidence supporting the discrimination finding.\n\n"
        f"## Mitigation\n\n"
        f"Containment actions taken:\n{contain_lines}\n\n"
        f"Correction plan: {corr}\n\n"
        f"## Reporting organization\n\n"
        f"{org_contact or 'Requires practitioner completion: organization_contact'}\n\n"
        f"## Citation\n\n"
        f"Filed under {section}.\n"
    )
    return {
        "jurisdiction": "usa-co",
        "template_name": "colorado-sb205-discrimination-disclosure",
        "draft_markdown": draft,
        "required_recipient": "Colorado Attorney General (and, for developer reports, known deployers of the system).",
        "required_contents_checklist": _colorado_required_contents_checklist(),
        "warnings": [] if actor_role else [
            "Requires practitioner completion: actor_role. Both developer (Section 6-1-1702(7)) and deployer (Section 6-1-1703(7)) obligations may apply."
        ],
    }


def _build_nyc_draft(
    incident: dict[str, Any],
    deadline_iso: str,
    containment: list[str],
    correction_plan: str,
    org_contact: str,
) -> dict[str, Any]:
    summary = incident.get("summary") or "Requires practitioner completion: candidate complaint summary"
    affected_systems = incident.get("affected_systems") or []
    contain_lines = "\n".join(f"- {c}" for c in containment) if containment else "- Requires practitioner completion: employer response"
    corr = correction_plan or "Requires practitioner completion: correction plan"

    draft = (
        f"# NYC Local Law 144 Candidate Complaint Response\n\n"
        f"**Response window (UTC):** {deadline_iso}\n\n"
        f"## AEDT identifier\n\n"
        f"- Affected tools: {', '.join(affected_systems) if affected_systems else 'Requires practitioner completion: AEDT identifier'}\n\n"
        f"## Candidate complaint summary\n\n"
        f"{summary}\n\n"
        f"## Employer or employment-agency response\n\n"
        f"{contain_lines}\n\n"
        f"Correction plan: {corr}\n\n"
        f"## Compliance posture\n\n"
        f"Requires practitioner completion: reference current bias audit (audit_date, auditor_identity) and confirm annual-cadence compliance.\n\n"
        f"## Contact\n\n"
        f"{org_contact or 'Requires practitioner completion: organization_contact'}\n\n"
        f"## Citation\n\n"
        f"Filed under NYC LL144 and NYC DCWP AEDT Rules, Subchapter T.\n"
    )
    return {
        "jurisdiction": "usa-nyc",
        "template_name": "nyc-ll144-candidate-complaint-response",
        "draft_markdown": draft,
        "required_recipient": "NYC Department of Consumer and Worker Protection (DCWP) and the candidate as applicable.",
        "required_contents_checklist": _nyc_required_contents_checklist(),
        "warnings": [],
    }


def _load_crosswalk_module():
    """Import the sibling crosswalk-matrix-builder plugin module (lazy)."""
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_incident", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enrich_crosswalk(applicable_jurisdictions: list[str]) -> tuple[list[str], list[str]]:
    """Return (cross_framework_citations, warnings).

    Looks up incident-reporting-relevant source_refs (EU AI Act Article 73,
    Colorado Sections 6-1-1702(7)/6-1-1703(7)) in the crosswalk data.
    """
    try:
        crosswalk = _load_crosswalk_module()
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return ([], [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"])

    wanted_source_refs: set[tuple[str, str]] = set()
    if "eu" in applicable_jurisdictions:
        wanted_source_refs.add(("eu-ai-act", "Article 73"))
    if "usa-co" in applicable_jurisdictions:
        wanted_source_refs.add(("colorado-sb-205", "Section 6-1-1702(7)"))
        wanted_source_refs.add(("colorado-sb-205", "Section 6-1-1703(7)"))

    citations: list[str] = []
    seen: set[str] = set()
    for m in data.get("mappings", []):
        key = (m.get("source_framework"), m.get("source_ref"))
        if key not in wanted_source_refs:
            continue
        target_fw = m.get("target_framework", "")
        target_ref = m.get("target_ref", "")
        if not target_ref:
            continue
        rel = m.get("relationship", "")
        citation = f"{target_fw}: {target_ref} ({rel})"
        if citation in seen:
            continue
        seen.add(citation)
        citations.append(citation)
    return (citations, [])


def generate_incident_report(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a deadline-aware external incident report package.

    See module docstring for input contract and design stance.

    Raises:
        ValueError: on missing or malformed required inputs.
    """
    _validate(inputs)

    incident = inputs["incident_description"]
    jurisdictions = list(inputs["applicable_jurisdictions"])
    detected_at = inputs["detected_at"]
    detected_dt = _parse_iso(detected_at)

    explicit_severity = inputs.get("severity")
    severity, severity_warnings = _derive_severity(incident, explicit_severity)

    actor_role = inputs.get("actor_role")
    already_reported_to = list(inputs.get("already_reported_to") or [])
    containment = list(inputs.get("containment_actions_taken") or [])
    correction_plan = inputs.get("correction_plan") or ""
    org_contact = inputs.get("organization_contact") or ""
    consequential_domains = list(inputs.get("consequential_domains") or [])
    enrich = inputs.get("enrich_with_crosswalk", True)
    reviewed_by = inputs.get("reviewed_by")

    warnings: list[str] = []
    warnings.extend(severity_warnings)

    now_dt = datetime.now(timezone.utc)

    deadline_matrix: list[dict[str, Any]] = []
    report_drafts: list[dict[str, Any]] = []
    citations: list[str] = [
        "ISO/IEC 42001:2023, Clause 10.2",
    ]

    # EU AI Act Article 73
    if "eu" in jurisdictions:
        if severity in EU_AI_ACT_DEADLINES or severity == "limited-harm" or severity == "no-harm":
            # Article 73 applicability is broad for serious incidents; use default for
            # unspecified categories but still emit an entry so the practitioner
            # confirms applicability.
            days = _eu_deadline_days(severity)
            deadline_dt = detected_dt + timedelta(days=days)
            rule_citation = _eu_article_73_citation(severity)
            entry = {
                "jurisdiction": "eu",
                "rule_citation": rule_citation,
                "deadline_iso": deadline_dt.date().isoformat(),
                "days_remaining": _days_remaining(deadline_dt, now_dt),
                "status": _status_for(deadline_dt, now_dt),
                "filing_recipient": "EU AI Office via national competent authority",
            }
            deadline_matrix.append(entry)
            citations.append(rule_citation)
            if actor_role is None:
                warnings.append(
                    "EU AI Act jurisdiction declared but actor_role not provided. "
                    "Article 73 attaches distinct obligations to provider vs deployer."
                )
            report_drafts.append(
                _build_eu_draft(
                    incident, severity, deadline_dt.date().isoformat(),
                    containment, correction_plan, actor_role, org_contact,
                )
            )

    # Colorado SB 205
    if "usa-co" in jurisdictions:
        if not consequential_domains:
            warnings.append(
                "Colorado jurisdiction declared but consequential_domains not provided. "
                "Colorado SB 205 Section 6-1-1701(3) applicability turns on consequential "
                "decision domain; confirm before filing."
            )
        deadline_dt = detected_dt + timedelta(days=COLORADO_SB205_DEADLINE_DAYS)
        # Emit both developer and deployer obligations so the filer confirms both.
        rule_citations_co = [
            "Colorado SB 205, Section 6-1-1702(7)",
            "Colorado SB 205, Section 6-1-1703(7)",
        ]
        entry = {
            "jurisdiction": "usa-co",
            "rule_citation": "; ".join(rule_citations_co),
            "deadline_iso": deadline_dt.date().isoformat(),
            "days_remaining": _days_remaining(deadline_dt, now_dt),
            "status": _status_for(deadline_dt, now_dt),
            "filing_recipient": "Colorado Attorney General",
        }
        deadline_matrix.append(entry)
        for c in rule_citations_co:
            if c not in citations:
                citations.append(c)
        report_drafts.append(
            _build_colorado_draft(
                incident, detected_at, deadline_dt.date().isoformat(),
                actor_role, consequential_domains, containment, correction_plan, org_contact,
            )
        )

    # NYC LL144
    if "usa-nyc" in jurisdictions:
        deadline_dt = detected_dt + timedelta(days=NYC_LL144_COMPLAINT_WINDOW_DAYS)
        rule_citation = "NYC DCWP AEDT Rules, Subchapter T, Section 5-303"
        entry = {
            "jurisdiction": "usa-nyc",
            "rule_citation": rule_citation,
            "deadline_iso": deadline_dt.date().isoformat(),
            "days_remaining": _days_remaining(deadline_dt, now_dt),
            "status": _status_for(deadline_dt, now_dt),
            "filing_recipient": "NYC Department of Consumer and Worker Protection (DCWP)",
        }
        deadline_matrix.append(entry)
        citations.append(rule_citation)
        citations.append("NYC LL144")
        report_drafts.append(
            _build_nyc_draft(
                incident, deadline_dt.date().isoformat(),
                containment, correction_plan, org_contact,
            )
        )

    # Unsupported jurisdictions warning.
    supported = {"eu", "usa-co", "usa-nyc"}
    for j in jurisdictions:
        if j not in supported:
            warnings.append(
                f"Jurisdiction {j!r} declared but no automated deadline rule shipped yet; review manually."
            )

    # Crosswalk enrichment.
    cross_framework_citations: list[str] = []
    if enrich:
        cross_framework_citations, enrich_warnings = _enrich_crosswalk(jurisdictions)
        warnings.extend(enrich_warnings)

    summary = {
        "applicable_jurisdictions": jurisdictions,
        "severity": severity,
        "deadline_count": len(deadline_matrix),
        "report_drafts_count": len(report_drafts),
        "overdue_count": sum(1 for e in deadline_matrix if e["status"] == "overdue"),
        "imminent_count": sum(1 for e in deadline_matrix if e["status"] == "imminent-within-48h"),
        "already_reported_to": already_reported_to,
    }

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "multi-jurisdiction",
        "incident_description_echo": incident,
        "severity": severity,
        "actor_role": actor_role,
        "applicable_jurisdictions": jurisdictions,
        "detected_at": detected_at,
        "deadline_matrix": deadline_matrix,
        "report_drafts": report_drafts,
        "already_reported_to": already_reported_to,
        "containment_actions_taken": containment,
        "correction_plan": correction_plan,
        "organization_contact": org_contact,
        "citations": citations,
        "cross_framework_citations": cross_framework_citations,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": reviewed_by,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render an incident report package as Markdown."""
    required = (
        "timestamp", "agent_signature", "severity", "applicable_jurisdictions",
        "deadline_matrix", "report_drafts", "citations", "summary",
    )
    missing = [k for k in required if k not in report]
    if missing:
        raise ValueError(f"report missing required fields: {missing}")

    lines: list[str] = [
        "# Incident Report Package",
        "",
        f"**Generated at (UTC):** {report['timestamp']}",
        f"**Generated by:** {report['agent_signature']}",
        f"**Severity:** {report['severity']}",
        f"**Detected at:** {report.get('detected_at', 'not set')}",
        f"**Actor role:** {report.get('actor_role') or 'not set'}",
        f"**Applicable jurisdictions:** {', '.join(report['applicable_jurisdictions'])}",
    ]
    if report.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {report['reviewed_by']}")
    lines.append("")

    # Incident summary
    incident = report.get("incident_description_echo") or {}
    lines.extend([
        "## Incident summary",
        "",
        f"- Summary: {incident.get('summary', 'not set')}",
        f"- Affected systems: {', '.join(incident.get('affected_systems') or []) or 'not set'}",
        f"- Date of occurrence: {incident.get('date_of_occurrence', 'not set')}",
        f"- Date discovered: {incident.get('date_discovered', 'not set')}",
        f"- Discovery channel: {incident.get('discovery_channel', 'not set')}",
        f"- Potential harms: {', '.join(incident.get('potential_harms') or []) or 'not set'}",
        f"- Impacted persons count: {incident.get('impacted_persons_count', 'unknown')}",
        f"- Geographic scope: {incident.get('geographic_scope', 'not set')}",
        "",
    ])

    # Deadline matrix
    lines.extend(["## Deadline matrix", ""])
    if not report["deadline_matrix"]:
        lines.append("_No applicable deadlines computed._")
    else:
        lines.append("| Jurisdiction | Rule | Deadline | Days remaining | Status | Recipient |")
        lines.append("|---|---|---|---|---|---|")
        for e in report["deadline_matrix"]:
            lines.append(
                f"| {e['jurisdiction']} | {e['rule_citation']} | {e['deadline_iso']} | "
                f"{e['days_remaining']} | {e['status']} | {e['filing_recipient']} |"
            )
    lines.append("")

    # Report drafts
    lines.extend(["## Report drafts", ""])
    if not report["report_drafts"]:
        lines.append("_No report drafts generated._")
    for d in report["report_drafts"]:
        lines.extend([
            f"### {d['jurisdiction']}: {d['template_name']}",
            "",
            f"**Required recipient:** {d['required_recipient']}",
            "",
            "**Required contents checklist:**",
            "",
        ])
        for item in d["required_contents_checklist"]:
            lines.append(f"- {item}")
        lines.extend(["", "**Draft:**", "", "```markdown", d["draft_markdown"], "```", ""])
        if d.get("warnings"):
            lines.extend(["**Draft-level warnings:**", ""])
            for w in d["warnings"]:
                lines.append(f"- {w}")
            lines.append("")

    # Recipient list
    lines.extend(["## Recipient list", ""])
    if not report["deadline_matrix"]:
        lines.append("_No recipients._")
    else:
        for e in report["deadline_matrix"]:
            lines.append(f"- {e['jurisdiction']}: {e['filing_recipient']}")
    lines.append("")

    # Citations
    lines.extend(["## Applicable citations", ""])
    for c in report["citations"]:
        lines.append(f"- {c}")
    lines.append("")

    if report.get("cross_framework_citations"):
        lines.extend(["## Cross-framework citations", ""])
        for c in report["cross_framework_citations"]:
            lines.append(f"- {c}")
        lines.append("")

    # Warnings
    lines.extend(["## Warnings", ""])
    if report.get("warnings"):
        for w in report["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("_No warnings._")
    lines.append("")

    return "\n".join(lines)


def render_csv(report: dict[str, Any]) -> str:
    """CSV rendering of the report drafts. One row per draft.

    Columns: jurisdiction, template_name, required_recipient, deadline_iso,
    status, days_remaining.
    """
    required = ("report_drafts", "deadline_matrix")
    missing = [k for k in required if k not in report]
    if missing:
        raise ValueError(f"report missing required fields: {missing}")

    by_jurisdiction = {e["jurisdiction"]: e for e in report["deadline_matrix"]}

    lines = ["jurisdiction,template_name,required_recipient,deadline_iso,status,days_remaining"]
    for d in report["report_drafts"]:
        j = d["jurisdiction"]
        matrix = by_jurisdiction.get(j, {})
        recipient = d["required_recipient"]
        # Quote if any field contains a comma.
        def _q(s: Any) -> str:
            s = str(s)
            if "," in s or '"' in s:
                return '"' + s.replace('"', '""') + '"'
            return s
        lines.append(
            f"{_q(j)},{_q(d['template_name'])},{_q(recipient)},"
            f"{_q(matrix.get('deadline_iso', ''))},{_q(matrix.get('status', ''))},"
            f"{_q(matrix.get('days_remaining', ''))}"
        )
    return "\n".join(lines) + "\n"
