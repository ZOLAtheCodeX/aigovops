"""
AIGovOps: Internal Audit Programme Planner Plugin

Operationalizes ISO/IEC 42001:2023 Clause 9.2 (Internal audit).

Clause 9.2.1 requires the organization to conduct internal audits at
planned intervals to determine whether the AIMS conforms to (a) the
organization's own requirements, (b) the requirements of ISO/IEC
42001:2023, and (c) is effectively implemented and maintained.

Clause 9.2.2 requires the organization to:

(a) plan, establish, implement and maintain an audit programme including
    frequency, methods, responsibilities, planning, reporting
    requirements, taking into consideration importance of processes and
    results of previous audits;
(b) define audit criteria and scope for each audit;
(c) select auditors and conduct audits to ensure objectivity and
    impartiality of the audit process;
(d) ensure that results of audits are reported to relevant management;
(e) retain documented information as evidence of audit programme and
    audit results.

Design stance: the plugin plans; it does not conduct. It never invents
audit findings. It produces a programme, a schedule, a criteria mapping,
and an impartiality assessment from structured organizational input.
Content gaps surface as warnings.

Status: Phase 3 minimum-viable implementation.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "internal-audit-planner/0.1.0"

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily inside
# the enrichment helper so basic planner calls (enrich_with_crosswalk=False)
# pay no import cost and are unaffected by crosswalk load failures.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))

REQUIRED_INPUT_FIELDS = ("scope", "audit_frequency_months", "audit_criteria")

VALID_AUDIT_TYPES = ("first-party", "second-party", "third-party")

VALID_METHODS = (
    "document-review",
    "interview",
    "observation",
    "technical-test",
    "sampling",
    "re-performance",
)

VALID_IMPARTIALITY_TIERS = (
    "independent",
    "departmental-separation",
    "management-delegated",
    "insufficient",
)

DEFAULT_ANNEX_A_CATEGORIES = (
    "A.2",
    "A.3",
    "A.4",
    "A.5",
    "A.6",
    "A.7",
    "A.8",
    "A.9",
    "A.10",
)

DEFAULT_REPORTING_RECIPIENTS = ("AI Governance Officer", "Top Management")

DEFAULT_METHODS = ("document-review", "interview", "sampling")

# Canonical ISO citations emitted at the programme level.
TOP_LEVEL_CITATIONS = (
    "ISO/IEC 42001:2023, Clause 9.2.1",
    "ISO/IEC 42001:2023, Clause 9.2.2(a)",
    "ISO/IEC 42001:2023, Clause 9.2.2(b)",
    "ISO/IEC 42001:2023, Clause 9.2.2(c)",
    "ISO/IEC 42001:2023, Clause 9.2.2(d)",
    "ISO/IEC 42001:2023, Clause 9.2.2(e)",
    "ISO/IEC 42001:2023, Clause 7.5.3",
    "ISO/IEC 42001:2023, Clause 9.3",
)

# Crosswalk references emitted when enrich_with_crosswalk is True. These
# mirror the relationships asserted in the crosswalk data files.
CROSS_FRAMEWORK_AUDIT_REFERENCES = (
    {
        "target_framework": "nist-ai-rmf",
        "target_ref": "MEASURE 4.1",
        "relationship": "partial-match",
        "confidence": "medium",
        "note": "Measurement feedback. ISO 9.2 internal audit partially satisfies NIST MEASURE 4.1 intent when audit findings feed risk and metric updates.",
    },
    {
        "target_framework": "nist-ai-rmf",
        "target_ref": "MEASURE 4.2",
        "relationship": "partial-match",
        "confidence": "medium",
        "note": "Measurement informed by experts. ISO 9.2.2(c) impartiality requirement aligns with expert-informed measurement.",
    },
    {
        "target_framework": "nist-ai-rmf",
        "target_ref": "MEASURE 4.3",
        "relationship": "partial-match",
        "confidence": "medium",
        "note": "Feedback mechanisms. ISO 9.2.2(d) reporting-to-management aligns with NIST feedback posture.",
    },
    {
        "target_framework": "eu-ai-act",
        "target_ref": "Article 17, Paragraph 1, Point (d)",
        "relationship": "partial-satisfaction",
        "confidence": "high",
        "note": "Quality management system examination, test, and validation procedures. ISO 9.2 internal audit programme partially satisfies Article 17(1)(d) by testing and validating that AIMS procedures operate as designed.",
    },
    {
        "target_framework": "eu-ai-act",
        "target_ref": "Article 17, Paragraph 1, Point (k)",
        "relationship": "satisfies",
        "confidence": "high",
        "note": "Record-keeping. ISO 9.2.2(e) retention of documented information as evidence of audit programme satisfies Article 17(1)(k) record-keeping for internal audit activity.",
    },
)

_ISO_CITATION_RE = re.compile(r"^ISO/IEC 42001:2023, Clause \d+(\.\d+)*(\([a-z0-9]+\))?$")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")

    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    scope = inputs["scope"]
    if not isinstance(scope, dict):
        raise ValueError("scope must be a dict")
    for key in ("aims_boundaries", "systems_in_scope", "clauses_in_scope", "annex_a_in_scope"):
        if key not in scope:
            raise ValueError(f"scope missing required field {key!r}")
    for list_field in ("systems_in_scope", "clauses_in_scope", "annex_a_in_scope"):
        if not isinstance(scope[list_field], list):
            raise ValueError(f"scope.{list_field} must be a list")

    freq = inputs["audit_frequency_months"]
    if not isinstance(freq, int) or isinstance(freq, bool):
        raise ValueError("audit_frequency_months must be an int")
    if freq < 1 or freq > 36:
        raise ValueError(
            f"audit_frequency_months must be in the range 1 to 36 inclusive; got {freq}"
        )

    criteria = inputs["audit_criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("audit_criteria must be a non-empty list of documents defining the audit criteria")
    if not any("ISO/IEC 42001:2023" in c for c in criteria if isinstance(c, str)):
        raise ValueError(
            "audit_criteria must reference 'ISO/IEC 42001:2023' per Clause 9.2.2(b). "
            "Every internal audit in an AIMS programme audits against the standard itself."
        )

    audit_type = inputs.get("audit_type", "first-party")
    if audit_type not in VALID_AUDIT_TYPES:
        raise ValueError(
            f"audit_type must be one of {VALID_AUDIT_TYPES}; got {audit_type!r}"
        )

    auditor_pool = inputs.get("auditor_pool")
    if auditor_pool is not None:
        if not isinstance(auditor_pool, list):
            raise ValueError("auditor_pool, when provided, must be a list of auditor dicts")
        for i, auditor in enumerate(auditor_pool):
            if not isinstance(auditor, dict):
                raise ValueError(f"auditor_pool[{i}] must be a dict")
            if "name" not in auditor:
                raise ValueError(f"auditor_pool[{i}] missing required field 'name'")
            indep = auditor.get("independence_level")
            if indep is not None and indep not in VALID_IMPARTIALITY_TIERS:
                raise ValueError(
                    f"auditor_pool[{i}].independence_level must be one of {VALID_IMPARTIALITY_TIERS}; got {indep!r}"
                )

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")

    prior = inputs.get("prior_audit_findings")
    if prior is not None and not isinstance(prior, list):
        raise ValueError("prior_audit_findings, when provided, must be a list of finding dicts")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _partition(items: list[Any], n: int) -> list[list[Any]]:
    """Evenly partition items into n buckets; last buckets absorb remainder."""
    if n <= 0:
        return [items]
    if not items:
        return [[] for _ in range(n)]
    base, rem = divmod(len(items), n)
    out: list[list[Any]] = []
    idx = 0
    for i in range(n):
        size = base + (1 if i < rem else 0)
        out.append(items[idx:idx + size])
        idx += size
    return out


def _risk_rank(
    area: str,
    prior_findings: list[dict[str, Any]],
) -> int:
    """Rank an audit area by risk-weighting per Clause 9.2.2(a).

    Higher score indicates higher priority. A recent critical finding on
    the area ranks it highest; lesser severities contribute less. Areas
    with no recorded findings receive rank 0.
    """
    score = 0
    severity_weight = {"critical": 100, "major": 30, "minor": 10, "observation": 3}
    for f in prior_findings:
        if not isinstance(f, dict):
            continue
        ref = f.get("area") or f.get("clause") or f.get("annex_a_category") or ""
        if not ref:
            continue
        if ref == area or ref.startswith(f"{area}.") or area.startswith(f"{ref}.") or area == ref:
            sev = (f.get("severity") or "").lower()
            score += severity_weight.get(sev, 5)
    return score


def _auditor_is_conflicted(auditor: dict[str, Any], area: str) -> bool:
    """Return True if the auditor has a declared home-area conflict for this scope area.

    An auditor is conflicted if either:
    - independence_level is 'insufficient', or
    - the auditor's own_areas include the area being audited, or
    - the auditor's department matches the area owner's department and
      independence_level is not 'independent' or 'departmental-separation'.
    """
    indep = auditor.get("independence_level")
    if indep == "insufficient":
        return True
    own_areas = auditor.get("own_areas") or []
    for oa in own_areas:
        if oa == area or area.startswith(f"{oa}.") or oa.startswith(f"{area}."):
            return True
    return False


def _assign_auditors(
    auditor_pool: list[dict[str, Any]],
    scope_this_cycle: list[str],
) -> tuple[list[str], list[str]]:
    """Return (assigned_auditor_names, per-cycle warnings).

    The plugin does not optimize for load balancing beyond round-robin;
    governance-side human review allocates specialists where needed.
    """
    warnings: list[str] = []
    if not auditor_pool:
        warnings.append(
            "No auditors in auditor_pool. Clause 9.2.2(c) requires selected auditors for each cycle. "
            "Every cycle is flagged as REQUIRES AUDITOR ASSIGNMENT."
        )
        return (["REQUIRES AUDITOR ASSIGNMENT"], warnings)

    assigned: list[str] = []
    for i, area in enumerate(scope_this_cycle):
        auditor = auditor_pool[i % len(auditor_pool)]
        name = auditor.get("name", "REQUIRES AUDITOR ASSIGNMENT")
        if _auditor_is_conflicted(auditor, area):
            warnings.append(
                f"Impartiality conflict: auditor {name!r} assigned to audit {area!r} but declares own_areas or insufficient independence. "
                "Clause 9.2.2(c) requires objectivity and impartiality. Reassign before issuing the audit notice."
            )
        if name not in assigned:
            assigned.append(name)
    return (assigned, warnings)


def _programme_cycles(freq_months: int) -> int:
    """Return the number of cycles in a 12-month rolling programme window."""
    if freq_months >= 12:
        return 1
    return max(1, 12 // freq_months)


def _date_range_for_cycle(
    cycle_index: int,
    freq_months: int,
    start_anchor: date,
) -> tuple[str, str]:
    """Compute ISO planned_start and planned_end dates for a given cycle."""
    approx_days = freq_months * 30
    start = start_anchor + timedelta(days=cycle_index * approx_days)
    end = start + timedelta(days=max(5, min(approx_days - 2, 21)))
    return (start.isoformat(), end.isoformat())


def _risk_weighted_order(areas: list[str], prior_findings: list[dict[str, Any]]) -> list[str]:
    """Sort areas by risk score descending. Areas with ties retain input order (stable)."""
    indexed = list(enumerate(areas))
    indexed.sort(key=lambda t: (-_risk_rank(t[1], prior_findings), t[0]))
    return [area for _, area in indexed]


def _build_criteria_mapping(
    scope: dict[str, Any],
    audit_criteria: list[str],
    risk_register_ref: str | None,
) -> list[dict[str, Any]]:
    """Build the criteria_mapping entries per Clause 9.2.2(b)."""
    mapping: list[dict[str, Any]] = []

    for clause in scope["clauses_in_scope"]:
        citation = f"ISO/IEC 42001:2023, Clause {clause}"
        mapping.append({
            "scope_area": clause,
            "scope_kind": "clause",
            "authoritative_citation": citation,
            "audit_criteria_documents": list(audit_criteria),
            "risk_register_reference": risk_register_ref,
        })

    for ax in scope["annex_a_in_scope"]:
        citation = f"ISO/IEC 42001:2023, Annex A, Control {ax}"
        mapping.append({
            "scope_area": ax,
            "scope_kind": "annex-a",
            "authoritative_citation": citation,
            "audit_criteria_documents": list(audit_criteria),
            "risk_register_reference": risk_register_ref,
        })

    return mapping


def _build_impartiality_assessment(
    auditor_pool: list[dict[str, Any]],
    schedule: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize impartiality posture per Clause 9.2.2(c)."""
    tier_counts: dict[str, int] = dict.fromkeys(VALID_IMPARTIALITY_TIERS, 0)
    for a in auditor_pool or []:
        tier = a.get("independence_level") or "insufficient"
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    cycle_impartiality: list[dict[str, Any]] = []
    for cycle in schedule:
        assigned_names = cycle.get("assigned_auditors") or []
        assigned_tiers: list[str] = []
        for name in assigned_names:
            match = next((a for a in (auditor_pool or []) if a.get("name") == name), None)
            if match is None:
                assigned_tiers.append("insufficient")
            else:
                assigned_tiers.append(match.get("independence_level") or "insufficient")
        has_independent = any(t == "independent" for t in assigned_tiers)
        cycle_impartiality.append({
            "cycle_id": cycle["cycle_id"],
            "assigned_auditor_tiers": assigned_tiers,
            "includes_independent_auditor": has_independent,
        })

    return {
        "tier_counts": tier_counts,
        "per_cycle": cycle_impartiality,
        "citation": "ISO/IEC 42001:2023, Clause 9.2.2(c)",
    }


def _load_crosswalk_module():
    """Import the sibling crosswalk-matrix-builder plugin module."""
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_iap", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_cross_framework_references() -> tuple[list[dict[str, Any]], list[str]]:
    """Return the hard-coded cross-framework audit references.

    The crosswalk plugin is loaded only to validate import availability;
    the references themselves are authored inline in this module so the
    plugin remains self-contained when the crosswalk data files are not
    present at runtime.
    """
    warnings: list[str] = []
    try:
        _load_crosswalk_module()
    except Exception as exc:
        warnings.append(
            f"Crosswalk plugin unavailable ({type(exc).__name__}: {exc}); cross_framework_audit_references use hard-coded values."
        )
    return ([dict(ref) for ref in CROSS_FRAMEWORK_AUDIT_REFERENCES], warnings)


# ---------------------------------------------------------------------------
# Canonical entry point
# ---------------------------------------------------------------------------


def generate_audit_plan(inputs: dict[str, Any]) -> dict[str, Any]:
    """Generate a validated ISO/IEC 42001:2023 Clause 9.2 internal audit plan.

    Args:
        inputs: Dict with:
            scope (required): dict with aims_boundaries, systems_in_scope,
                clauses_in_scope, annex_a_in_scope.
            audit_frequency_months (required): int in 1..36.
            audit_criteria (required): list with at least one reference
                to 'ISO/IEC 42001:2023'.
            audit_type: enum default 'first-party'.
            auditor_pool: list of {name, role, independence_level,
                qualifications, own_areas}.
            prior_audit_findings: list of dicts for risk-weighted
                prioritization per 9.2.2(a).
            management_system_risk_register_ref: str echoed into criteria.
            reporting_recipients: list, default AI Governance Officer and
                Top Management.
            reviewed_by: optional str.
            enrich_with_crosswalk: bool, default True.

    Returns:
        Dict with timestamp, agent_signature, framework, reviewed_by,
        scope_echo, audit_schedule, scope_coverage_summary,
        impartiality_assessment, criteria_mapping, citations, warnings,
        summary, and optionally cross_framework_audit_references.

    Raises:
        ValueError: if structural requirements are not met.
    """
    _validate(inputs)
    scope = inputs["scope"]
    freq_months = inputs["audit_frequency_months"]
    audit_criteria = list(inputs["audit_criteria"])
    audit_type = inputs.get("audit_type", "first-party")
    auditor_pool = list(inputs.get("auditor_pool") or [])
    prior_findings = list(inputs.get("prior_audit_findings") or [])
    risk_register_ref = inputs.get("management_system_risk_register_ref")
    reporting_recipients = list(
        inputs.get("reporting_recipients") or DEFAULT_REPORTING_RECIPIENTS
    )
    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True

    warnings: list[str] = []

    # Combined audit areas: clauses + annex-A categories. Risk-weight them.
    raw_areas = list(scope["clauses_in_scope"]) + list(scope["annex_a_in_scope"])
    if not raw_areas:
        warnings.append(
            "Scope contains no clauses or Annex A categories. Clause 9.2.2(b) requires each audit to define a scope. "
            "Programme produces zero cycles."
        )
    ordered_areas = _risk_weighted_order(raw_areas, prior_findings)

    # Compute cycles. freq_months controls cadence; we build a rolling
    # 12-month programme with one slot per cadence step.
    cycles = _programme_cycles(freq_months)
    buckets = _partition(ordered_areas, cycles)

    today = _today()
    audit_schedule: list[dict[str, Any]] = []
    assignment_warnings: list[str] = []
    for i in range(cycles):
        cycle_scope = buckets[i] if i < len(buckets) else []
        planned_start, planned_end = _date_range_for_cycle(i, freq_months, today)
        assigned_auditors, cycle_warnings = _assign_auditors(auditor_pool, cycle_scope)
        assignment_warnings.extend(cycle_warnings)

        methods_selected = list(DEFAULT_METHODS)
        if any(ax.startswith("A.7") or ax.startswith("A.8") for ax in cycle_scope):
            if "technical-test" not in methods_selected:
                methods_selected.append("technical-test")

        audit_schedule.append({
            "cycle_id": f"IA-{today.year}-{i + 1:02d}",
            "planned_start_date": planned_start,
            "planned_end_date": planned_end,
            "scope_this_cycle": list(cycle_scope),
            "assigned_auditors": list(assigned_auditors),
            "audit_type": audit_type,
            "audit_criteria": list(audit_criteria),
            "methods_selected": methods_selected,
            "reporting_recipients": list(reporting_recipients),
            "citations": [
                "ISO/IEC 42001:2023, Clause 9.2.2(a)",
                "ISO/IEC 42001:2023, Clause 9.2.2(b)",
                "ISO/IEC 42001:2023, Clause 9.2.2(c)",
                "ISO/IEC 42001:2023, Clause 9.2.2(d)",
            ],
        })

    warnings.extend(assignment_warnings)

    # Scope coverage gap warning: any declared area not covered by any cycle.
    covered_areas = {a for cycle in audit_schedule for a in cycle["scope_this_cycle"]}
    gap_areas = [a for a in raw_areas if a not in covered_areas]
    if gap_areas:
        warnings.append(
            f"Scope gap: {len(gap_areas)} declared area(s) not covered by any cycle: {sorted(gap_areas)}. "
            "Clause 9.2.2(a) requires the programme to cover every area in organizational scope."
        )

    # Prior-findings follow-up check.
    for f in prior_findings:
        if not isinstance(f, dict):
            continue
        if f.get("corrective_action_status") in (None, "", "open") and not f.get("follow_up_cycle_id"):
            fid = f.get("id") or f.get("area") or "<unknown>"
            warnings.append(
                f"Prior audit finding {fid!r} has no recorded follow-up in the schedule. "
                "Clause 9.2.2(a) requires results of previous audits to inform the next cycle."
            )

    # Risk register echo warning.
    if risk_register_ref is None:
        warnings.append(
            "management_system_risk_register_ref is not provided. Clause 9.2.2(a) requires the programme to take the "
            "importance of processes and results of previous audits into consideration; the risk register is the primary input."
        )

    impartiality_assessment = _build_impartiality_assessment(auditor_pool, audit_schedule)
    criteria_mapping = _build_criteria_mapping(scope, audit_criteria, risk_register_ref)

    scope_coverage_summary = {
        "clauses_declared": len(scope["clauses_in_scope"]),
        "annex_a_categories_declared": len(scope["annex_a_in_scope"]),
        "total_areas_declared": len(raw_areas),
        "areas_covered_by_schedule": len(covered_areas),
        "areas_not_covered": sorted(gap_areas),
    }

    summary = {
        "cycles_planned": len(audit_schedule),
        "audit_frequency_months": freq_months,
        "auditor_pool_size": len(auditor_pool),
        "areas_declared": len(raw_areas),
        "areas_covered": len(covered_areas),
        "warning_count": len(warnings),
        "reporting_recipients_count": len(reporting_recipients),
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "iso42001",
        "reviewed_by": inputs.get("reviewed_by"),
        "scope_echo": {
            "aims_boundaries": scope["aims_boundaries"],
            "systems_in_scope": list(scope["systems_in_scope"]),
            "clauses_in_scope": list(scope["clauses_in_scope"]),
            "annex_a_in_scope": list(scope["annex_a_in_scope"]),
        },
        "audit_schedule": audit_schedule,
        "scope_coverage_summary": scope_coverage_summary,
        "impartiality_assessment": impartiality_assessment,
        "criteria_mapping": criteria_mapping,
        "citations": list(TOP_LEVEL_CITATIONS),
        "warnings": warnings,
        "summary": summary,
    }

    if enrich:
        refs, enrich_warnings = _build_cross_framework_references()
        output["cross_framework_audit_references"] = refs
        warnings.extend(enrich_warnings)

    return output


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_markdown(plan: dict[str, Any]) -> str:
    """Render the audit plan as Markdown audit evidence."""
    required = (
        "timestamp",
        "agent_signature",
        "citations",
        "audit_schedule",
        "scope_coverage_summary",
        "impartiality_assessment",
        "criteria_mapping",
        "summary",
    )
    missing = [k for k in required if k not in plan]
    if missing:
        raise ValueError(f"plan missing required fields: {missing}")

    lines: list[str] = [
        "# Internal Audit Programme",
        "",
        f"**Generated at (UTC):** {plan['timestamp']}",
        f"**Generated by:** {plan['agent_signature']}",
        f"**Framework:** {plan.get('framework', 'iso42001')}",
    ]
    if plan.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {plan['reviewed_by']}")

    scope = plan.get("scope_echo", {})
    lines.extend([
        "",
        "## AIMS scope",
        "",
        f"- AIMS boundaries: {scope.get('aims_boundaries', 'not set')}",
        f"- Systems in scope: {', '.join(scope.get('systems_in_scope', [])) or 'none declared'}",
        f"- Clauses in scope: {', '.join(scope.get('clauses_in_scope', [])) or 'none declared'}",
        f"- Annex A categories in scope: {', '.join(scope.get('annex_a_in_scope', [])) or 'none declared'}",
    ])

    summary = plan["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Cycles planned: {summary['cycles_planned']}",
        f"- Audit frequency (months): {summary['audit_frequency_months']}",
        f"- Auditor pool size: {summary['auditor_pool_size']}",
        f"- Areas declared: {summary['areas_declared']}",
        f"- Areas covered: {summary['areas_covered']}",
        f"- Warnings: {summary['warning_count']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in plan["citations"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Schedule", ""])
    if not plan["audit_schedule"]:
        lines.append("_No audit cycles planned in this programme window._")
    for cycle in plan["audit_schedule"]:
        lines.extend([
            f"### {cycle['cycle_id']}",
            "",
            f"**Planned window:** {cycle['planned_start_date']} to {cycle['planned_end_date']}",
            f"**Audit type:** {cycle['audit_type']}",
            f"**Assigned auditors:** {', '.join(cycle['assigned_auditors']) or 'REQUIRES AUDITOR ASSIGNMENT'}",
            f"**Methods:** {', '.join(cycle['methods_selected'])}",
            f"**Reporting recipients:** {', '.join(cycle['reporting_recipients'])}",
            "",
            "**Scope this cycle:**",
            "",
        ])
        if cycle["scope_this_cycle"]:
            for a in cycle["scope_this_cycle"]:
                lines.append(f"- {a}")
        else:
            lines.append("- (empty)")
        lines.extend([
            "",
            "**Audit criteria:**",
            "",
        ])
        for c in cycle["audit_criteria"]:
            lines.append(f"- {c}")
        lines.extend(["", "**Citations:**", ""])
        for c in cycle["citations"]:
            lines.append(f"- {c}")
        lines.append("")

    cov = plan["scope_coverage_summary"]
    lines.extend([
        "## Scope coverage",
        "",
        f"- Clauses declared: {cov['clauses_declared']}",
        f"- Annex A categories declared: {cov['annex_a_categories_declared']}",
        f"- Total areas declared: {cov['total_areas_declared']}",
        f"- Areas covered by schedule: {cov['areas_covered_by_schedule']}",
    ])
    if cov["areas_not_covered"]:
        lines.append(f"- Areas not covered: {', '.join(cov['areas_not_covered'])}")
    else:
        lines.append("- Areas not covered: none")

    imp = plan["impartiality_assessment"]
    lines.extend([
        "",
        "## Impartiality",
        "",
        f"- Citation: {imp['citation']}",
        "- Tier counts:",
    ])
    for tier, count in imp["tier_counts"].items():
        lines.append(f"  - {tier}: {count}")
    lines.append("- Per cycle:")
    for entry in imp["per_cycle"]:
        lines.append(
            f"  - {entry['cycle_id']}: independent auditor present = {entry['includes_independent_auditor']}; tiers = {', '.join(entry['assigned_auditor_tiers']) or 'none'}"
        )

    lines.extend(["", "## Criteria mapping", ""])
    for m in plan["criteria_mapping"]:
        lines.append(
            f"- {m['scope_area']} ({m['scope_kind']}): {m['authoritative_citation']}; "
            f"criteria docs: {', '.join(m['audit_criteria_documents'])}; "
            f"risk register: {m['risk_register_reference'] or 'not set'}"
        )

    refs = plan.get("cross_framework_audit_references")
    if refs:
        lines.extend(["", "## Cross-framework audit references", ""])
        for r in refs:
            lines.append(
                f"- {r['target_framework']} {r['target_ref']}: {r['relationship']} (confidence: {r['confidence']}). {r['note']}"
            )

    if plan.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in plan["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(plan: dict[str, Any]) -> str:
    """Render the audit schedule as CSV, one row per audit cycle."""
    if "audit_schedule" not in plan:
        raise ValueError("plan missing required field 'audit_schedule'")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "cycle_id",
        "planned_start_date",
        "planned_end_date",
        "audit_type",
        "scope_this_cycle",
        "assigned_auditors",
        "methods_selected",
        "audit_criteria",
        "reporting_recipients",
        "citations",
    ])
    for cycle in plan["audit_schedule"]:
        writer.writerow([
            cycle.get("cycle_id", ""),
            cycle.get("planned_start_date", ""),
            cycle.get("planned_end_date", ""),
            cycle.get("audit_type", ""),
            "; ".join(cycle.get("scope_this_cycle", [])),
            "; ".join(cycle.get("assigned_auditors", [])),
            "; ".join(cycle.get("methods_selected", [])),
            "; ".join(cycle.get("audit_criteria", [])),
            "; ".join(cycle.get("reporting_recipients", [])),
            "; ".join(cycle.get("citations", [])),
        ])
    return buf.getvalue()
