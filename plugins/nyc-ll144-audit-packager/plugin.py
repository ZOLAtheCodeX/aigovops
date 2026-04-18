"""
AIGovOps: NYC Local Law 144 Bias Audit Packager Plugin

Given the results of an externally-conducted bias audit of an Automated
Employment Decision Tool (AEDT), produces the public-disclosure bundle
and the notice-to-candidates checklist required by NYC Local Law 144
of 2021 and the implementing Department of Consumer and Worker
Protection (DCWP) rules (6 RCNY, Chapter 5, Subchapter T, Section
5-300 et seq.).

Design stance: the plugin does NOT conduct the bias audit itself. The
audit is performed by an independent auditor against a defined
candidate-pool dataset, per DCWP Final Rule Section 5-301. This
plugin packages already-computed selection rates and impact ratios
into the public-disclosure format that employers and employment
agencies must publish before using the AEDT for a NYC employment
decision.

Applicability determination for an AEDT in scope is derived
deterministically from three inputs: whether the tool substantially
assists or replaces discretionary decision-making, whether it is used
for NYC candidates or NYC employees, and the employer's role
(employer or employment agency). Legal edge cases (whether a specific
tool "substantially assists" under DCWP Section 5-300 definitions)
remain human determinations; the plugin surfaces the question and
records the answer supplied by the caller.

Status: Phase 3 implementation. 0.1.0.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

AGENT_SIGNATURE = "nyc-ll144-audit-packager/0.1.0"

REQUIRED_INPUT_FIELDS = ("aedt_description", "employer_role", "audit_data")

VALID_EMPLOYER_ROLES = ("employer", "employment-agency")

DCWP_REQUIRED_RACE_CATEGORIES = (
    "Hispanic or Latino",
    "White (Not Hispanic or Latino)",
    "Black or African American (Not Hispanic or Latino)",
    "Native Hawaiian or Pacific Islander (Not Hispanic or Latino)",
    "Asian (Not Hispanic or Latino)",
    "Native American or Alaska Native (Not Hispanic or Latino)",
    "Two or More Races (Not Hispanic or Latino)",
)

DCWP_REQUIRED_SEX_CATEGORIES = ("Male", "Female")

MIN_CATEGORIES_FOR_IMPACT_RATIO = 2


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_date(date_str: str) -> datetime:
    """Parse an ISO 8601 date or datetime. Returns a UTC-aware datetime."""
    clean = date_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    aedt = inputs["aedt_description"]
    if not isinstance(aedt, dict):
        raise ValueError("aedt_description must be a dict")

    role = inputs["employer_role"]
    if role not in VALID_EMPLOYER_ROLES:
        raise ValueError(
            f"employer_role must be one of {VALID_EMPLOYER_ROLES}, got {role!r}"
        )

    audit_data = inputs["audit_data"]
    if not isinstance(audit_data, dict):
        raise ValueError("audit_data must be a dict")

    audit_date = audit_data.get("audit_date")
    if audit_date is not None:
        if not isinstance(audit_date, str):
            raise ValueError("audit_data.audit_date must be an ISO date string")
        try:
            _parse_date(audit_date)
        except ValueError as exc:
            raise ValueError(f"audit_data.audit_date must be ISO 8601: {exc}") from exc

    selection_rates = audit_data.get("selection_rates")
    if selection_rates is not None and not isinstance(selection_rates, dict):
        raise ValueError("audit_data.selection_rates, when provided, must be a dict")


def _determine_applicability(
    aedt: dict[str, Any], role: str
) -> tuple[bool, list[str]]:
    """Return (in_scope, rationale_bullets) per DCWP Section 5-300 definitions.

    An AEDT is in scope when ALL of:
    - substantially_assists_decision is True, AND
    - used_for_nyc_candidates_or_employees is True, AND
    - role is a covered role (employer or employment-agency).

    Missing booleans default to False (conservative: not in scope until
    the caller confirms). This is load-bearing: a plugin that assumed
    scope would mislabel out-of-scope tools; a plugin that required
    explicit booleans would halt the caller prematurely.
    """
    substantially_assists = bool(aedt.get("substantially_assists_decision"))
    used_nyc = bool(aedt.get("used_for_nyc_candidates_or_employees"))
    covered_role = role in VALID_EMPLOYER_ROLES

    rationale: list[str] = []
    rationale.append(
        f"Tool substantially assists or replaces discretionary employment decision: "
        f"{substantially_assists}."
    )
    rationale.append(
        f"Tool used for NYC candidates or NYC employees: {used_nyc}."
    )
    rationale.append(f"Caller role {role!r} is a covered role: {covered_role}.")

    in_scope = substantially_assists and used_nyc and covered_role
    return in_scope, rationale


def _compute_impact_ratios(
    selection_rates: dict[str, dict[str, float]],
) -> dict[str, dict[str, Any]]:
    """Compute impact ratios per DCWP Final Rule Section 5-301.

    For each demographic group (race/ethnicity, sex, intersectional),
    the impact ratio is the selection rate of the group divided by the
    selection rate of the most-selected group in that category.

    Input shape:
        {
          "race_ethnicity": {"White (...)": 0.42, "Black (...)": 0.31, ...},
          "sex": {"Male": 0.40, "Female": 0.35},
          "intersectional": {"Hispanic Male": 0.33, "White Female": 0.41, ...}
        }

    Output shape per category:
        {
          "selection_rates": {...},
          "most_selected_group": str,
          "most_selected_rate": float,
          "impact_ratios": {group: ratio},
        }
    """
    out: dict[str, dict[str, Any]] = {}
    for category, rates in selection_rates.items():
        if not isinstance(rates, dict) or not rates:
            out[category] = {
                "selection_rates": rates or {},
                "most_selected_group": None,
                "most_selected_rate": None,
                "impact_ratios": {},
            }
            continue
        most_group = max(rates, key=lambda g: rates[g])
        most_rate = rates[most_group]
        if most_rate == 0:
            impact_ratios = {g: None for g in rates}
        else:
            impact_ratios = {g: round(rates[g] / most_rate, 4) for g in rates}
        out[category] = {
            "selection_rates": dict(rates),
            "most_selected_group": most_group,
            "most_selected_rate": most_rate,
            "impact_ratios": impact_ratios,
        }
    return out


def _next_audit_due_by(audit_date: str | None) -> str | None:
    """LL144 requires annual re-audit. Compute audit_date + 365 days."""
    if not audit_date:
        return None
    dt = _parse_date(audit_date)
    due = dt + timedelta(days=365)
    return due.date().isoformat()


def _required_candidate_notices(role: str) -> list[dict[str, str]]:
    """Notices required under DCWP Final Rule Section 5-303.

    Both employers and employment agencies must provide: (a) notice
    that an AEDT will be used in connection with the assessment or
    evaluation, (b) notice of the job qualifications and
    characteristics that the AEDT will use, (c) information about the
    type and source of data collected for the AEDT and the retention
    policy, available upon written request.

    Notice must be provided at least 10 business days before use.
    """
    return [
        {
            "notice_id": "aedt-use-notice",
            "content": (
                "Notice to the candidate or employee that an AEDT will be used in "
                "connection with the assessment or evaluation."
            ),
            "timing": "At least 10 business days before use of the AEDT.",
            "citation": "NYC DCWP AEDT Rules, Subchapter T, Section 5-303",
        },
        {
            "notice_id": "job-qualifications-notice",
            "content": (
                "Notice of the job qualifications and characteristics that the AEDT "
                "will use in the assessment of the candidate or employee."
            ),
            "timing": "At least 10 business days before use of the AEDT.",
            "citation": "NYC DCWP AEDT Rules, Subchapter T, Section 5-303",
        },
        {
            "notice_id": "data-type-source-retention",
            "content": (
                "Information about the type and source of data collected for the "
                "AEDT and the employer's or employment agency's data retention "
                "policy. Available upon written request within 30 days."
            ),
            "timing": "Available upon written request.",
            "citation": "NYC DCWP AEDT Rules, Subchapter T, Section 5-303",
        },
    ]


def _validate_audit_data_content(
    audit_data: dict[str, Any],
) -> list[str]:
    """Surface content gaps as warnings. Does not raise.

    Gaps flagged:
    - Missing audit_date (blocks next-audit-due calculation).
    - Missing auditor_identity (blocks public disclosure).
    - selection_rates missing intersectional breakdown.
    - Any category with fewer than MIN_CATEGORIES_FOR_IMPACT_RATIO groups
      (impact ratio is meaningless with one group).
    - Missing distribution_comparison (historical baseline required
      by DCWP for the public disclosure).
    """
    warnings: list[str] = []
    if not audit_data.get("audit_date"):
        warnings.append(
            "audit_data.audit_date missing. Required for the public-disclosure "
            "bundle and the next-audit-due-by calculation."
        )
    if not audit_data.get("auditor_identity"):
        warnings.append(
            "audit_data.auditor_identity missing. DCWP Final Rule Section 5-304 "
            "requires the independent auditor to be identified in the public "
            "disclosure."
        )
    selection_rates = audit_data.get("selection_rates") or {}
    if not selection_rates:
        warnings.append(
            "audit_data.selection_rates missing or empty. Impact-ratio "
            "computation cannot proceed."
        )
    else:
        if "intersectional" not in selection_rates or not selection_rates.get(
            "intersectional"
        ):
            warnings.append(
                "audit_data.selection_rates.intersectional missing. DCWP "
                "Final Rule Section 5-301 requires intersectional breakdown "
                "(race/ethnicity by sex)."
            )
        for category, rates in selection_rates.items():
            if isinstance(rates, dict) and len(rates) < MIN_CATEGORIES_FOR_IMPACT_RATIO:
                warnings.append(
                    f"audit_data.selection_rates.{category} has fewer than "
                    f"{MIN_CATEGORIES_FOR_IMPACT_RATIO} groups. Impact ratio is "
                    "undefined for a single-group category."
                )
    if not audit_data.get("distribution_comparison"):
        warnings.append(
            "audit_data.distribution_comparison missing. DCWP public disclosure "
            "requires a historical or test-pool distribution comparison."
        )
    return warnings


def _citations_for_report(in_scope: bool) -> list[str]:
    base = [
        "NYC LL144",
        "NYC LL144 Final Rule, Section 5-301",
        "NYC LL144 Final Rule, Section 5-303",
        "NYC LL144 Final Rule, Section 5-304",
        "NYC DCWP AEDT Rules, Subchapter T",
    ]
    if in_scope:
        base.append("NYC LL144 Final Rule, Section 5-302")
    return base


def generate_audit_package(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Produce the NYC LL144 public-disclosure and notice bundle for an AEDT.

    Args:
        inputs: Dict with:
            aedt_description: dict with at minimum
                tool_name, substantially_assists_decision (bool),
                used_for_nyc_candidates_or_employees (bool). Optional:
                vendor, decision_category (screen / rank / score / other).
            employer_role: one of VALID_EMPLOYER_ROLES.
            audit_data: dict with
                audit_date (ISO date), auditor_identity (str),
                selection_rates (dict), distribution_comparison (dict).
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, framework, in_scope,
        applicability_rationale, aedt_description_echo, employer_role,
        audit_date, next_audit_due_by, auditor_identity,
        selection_rates_analysis, distribution_comparison,
        public_disclosure_bundle, candidate_notices, citations,
        warnings, reviewed_by, summary.

    Raises:
        ValueError: when required inputs are missing or malformed.
    """
    _validate(inputs)

    aedt = inputs["aedt_description"]
    role = inputs["employer_role"]
    audit_data = inputs["audit_data"]

    in_scope, rationale = _determine_applicability(aedt, role)

    warnings: list[str] = []
    if not in_scope:
        warnings.append(
            "AEDT determined out of scope. Public disclosure and candidate "
            "notices are not mandated. Confirm the substantially-assists and "
            "NYC-use determinations with counsel before relying on this result."
        )

    warnings.extend(_validate_audit_data_content(audit_data))

    selection_rates = audit_data.get("selection_rates") or {}
    analysis = _compute_impact_ratios(selection_rates)

    audit_date = audit_data.get("audit_date")
    next_due = _next_audit_due_by(audit_date)

    auditor_identity = audit_data.get("auditor_identity") or "REQUIRES AUDITOR IDENTIFICATION"

    public_disclosure = {
        "date_of_most_recent_audit": audit_date or "REQUIRES AUDIT DATE",
        "auditor_identity": auditor_identity,
        "summary_of_results": {
            "selection_rates": {
                category: data.get("selection_rates")
                for category, data in analysis.items()
            },
            "impact_ratios": {
                category: data.get("impact_ratios")
                for category, data in analysis.items()
            },
        },
        "distribution_comparison": audit_data.get("distribution_comparison") or {},
        "publication_method": (
            "Employer or employment agency must post on the public-facing "
            "careers website or equivalent, easily accessible from the AEDT "
            "use point, per DCWP Final Rule Section 5-304."
        ),
    }

    candidate_notices = _required_candidate_notices(role) if in_scope else []

    citations = _citations_for_report(in_scope)

    summary = {
        "in_scope": in_scope,
        "employer_role": role,
        "audit_date": audit_date,
        "next_audit_due_by": next_due,
        "categories_analyzed": sorted(analysis.keys()),
        "warnings_count": len(warnings),
    }

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "nyc-ll144",
        "in_scope": in_scope,
        "applicability_rationale": rationale,
        "aedt_description_echo": aedt,
        "employer_role": role,
        "audit_date": audit_date,
        "next_audit_due_by": next_due,
        "auditor_identity": auditor_identity,
        "selection_rates_analysis": analysis,
        "distribution_comparison": audit_data.get("distribution_comparison") or {},
        "public_disclosure_bundle": public_disclosure,
        "candidate_notices": candidate_notices,
        "citations": citations,
        "warnings": warnings,
        "reviewed_by": inputs.get("reviewed_by"),
        "summary": summary,
    }


def render_markdown(package: dict[str, Any]) -> str:
    required = (
        "timestamp",
        "agent_signature",
        "in_scope",
        "aedt_description_echo",
        "employer_role",
        "public_disclosure_bundle",
        "citations",
        "summary",
    )
    missing = [k for k in required if k not in package]
    if missing:
        raise ValueError(f"package missing required fields: {missing}")

    aedt = package["aedt_description_echo"]
    tool_name = aedt.get("tool_name", "AEDT")

    lines = [
        f"# NYC Local Law 144 Audit Package: {tool_name}",
        "",
        f"**Generated at (UTC):** {package['timestamp']}",
        f"**Generated by:** {package['agent_signature']}",
        f"**Employer role:** {package['employer_role']}",
        f"**In scope:** {package['in_scope']}",
        "",
        "## Applicability determination",
        "",
    ]
    for bullet in package.get("applicability_rationale", []):
        lines.append(f"- {bullet}")
    lines.extend(["", "## Summary", ""])
    summary = package["summary"]
    lines.append(f"- In scope: {summary['in_scope']}")
    lines.append(f"- Audit date: {summary.get('audit_date') or 'not provided'}")
    lines.append(
        f"- Next audit due by: {summary.get('next_audit_due_by') or 'not computed'}"
    )
    lines.append(
        f"- Categories analyzed: {', '.join(summary.get('categories_analyzed', [])) or 'none'}"
    )
    lines.append(f"- Warnings: {summary.get('warnings_count', 0)}")

    lines.extend(["", "## Applicable citations", ""])
    for c in package["citations"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Public disclosure bundle", ""])
    pdb = package["public_disclosure_bundle"]
    lines.append(f"- Date of most recent audit: {pdb['date_of_most_recent_audit']}")
    lines.append(f"- Auditor identity: {pdb['auditor_identity']}")
    lines.append(f"- Publication method: {pdb['publication_method']}")

    lines.extend(["", "### Selection rates and impact ratios", ""])
    analysis = package["selection_rates_analysis"]
    if not analysis:
        lines.append("_No selection-rate categories supplied._")
    for category, data in analysis.items():
        lines.append(f"#### Category: {category}")
        lines.append("")
        most = data.get("most_selected_group")
        most_rate = data.get("most_selected_rate")
        lines.append(
            f"Most-selected group: {most} (rate {most_rate})."
            if most is not None
            else "Most-selected group: not determinable."
        )
        lines.append("")
        lines.append("| Group | Selection rate | Impact ratio |")
        lines.append("|---|---|---|")
        rates = data.get("selection_rates", {})
        ratios = data.get("impact_ratios", {})
        for group, rate in rates.items():
            ratio = ratios.get(group)
            ratio_str = "undefined" if ratio is None else f"{ratio}"
            lines.append(f"| {group} | {rate} | {ratio_str} |")
        lines.append("")

    notices = package.get("candidate_notices") or []
    if notices:
        lines.extend(["## Required candidate notices", ""])
        for notice in notices:
            lines.append(f"### {notice['notice_id']}")
            lines.append("")
            lines.append(notice["content"])
            lines.append("")
            lines.append(f"Timing: {notice['timing']}")
            lines.append(f"Citation: {notice['citation']}")
            lines.append("")
    else:
        lines.extend(["## Required candidate notices", "",
                      "_Not required (tool determined out of scope)._", ""])

    if package.get("warnings"):
        lines.extend(["## Warnings", ""])
        for w in package["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def render_csv(package: dict[str, Any]) -> str:
    """CSV rendering of the selection-rate and impact-ratio table.

    One row per (category, group) tuple. Header row included.
    """
    required = ("selection_rates_analysis",)
    missing = [k for k in required if k not in package]
    if missing:
        raise ValueError(f"package missing required fields: {missing}")

    lines = ["category,group,selection_rate,impact_ratio,most_selected_group,audit_date"]
    audit_date = package.get("audit_date") or ""
    analysis = package["selection_rates_analysis"]
    for category, data in analysis.items():
        most = data.get("most_selected_group") or ""
        rates = data.get("selection_rates", {})
        ratios = data.get("impact_ratios", {})
        for group, rate in rates.items():
            ratio = ratios.get(group)
            ratio_str = "" if ratio is None else f"{ratio}"
            # Escape commas in group names with quotes.
            group_escaped = f'"{group}"' if "," in str(group) else str(group)
            most_escaped = f'"{most}"' if "," in str(most) else str(most)
            lines.append(
                f"{category},{group_escaped},{rate},{ratio_str},{most_escaped},{audit_date}"
            )
    return "\n".join(lines) + "\n"
