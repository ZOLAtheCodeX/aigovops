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

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "management-review-packager/0.2.0"

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily inside
# the coverage helper so basic packager calls (include_crosswalk_coverage=False)
# pay no import cost and are unaffected by crosswalk load failures.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))

# Framework ids accepted in crosswalk_target_frameworks. Sourced from
# plugins/crosswalk-matrix-builder/data/frameworks.yaml.
VALID_CROSSWALK_TARGET_FRAMEWORKS = (
    "iso42001",
    "nist-ai-rmf",
    "eu-ai-act",
    "uk-atrs",
    "colorado-sb-205",
    "nyc-ll144",
    "singapore-magf",
    "cppa-admt",
    "ccpa-cpra",
    "ca-sb-942",
    "ca-ab-2013",
    "ca-ab-1008",
    "ca-sb-1001",
    "ca-ab-1836",
)

DEFAULT_CROSSWALK_TARGET_FRAMEWORKS = ("nist-ai-rmf", "eu-ai-act", "uk-atrs")

# Frameworks that are indexed from the jurisdiction side in the crosswalk
# data (i.e. the YAML file uses the jurisdiction as the source_framework
# and ISO as the target_framework). When one of these is requested as a
# crosswalk target we invert the query.
JURISDICTION_FRAMEWORKS = (
    "colorado-sb-205",
    "nyc-ll144",
    "uk-atrs",
    "singapore-magf",
)

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

    include = inputs.get("include_crosswalk_coverage")
    if include is not None and not isinstance(include, bool):
        raise ValueError("include_crosswalk_coverage, when provided, must be a bool")

    targets = inputs.get("crosswalk_target_frameworks")
    if targets is not None:
        if not isinstance(targets, list):
            raise ValueError("crosswalk_target_frameworks, when provided, must be a list of framework ids")
        for t in targets:
            if not isinstance(t, str):
                raise ValueError(
                    f"crosswalk_target_frameworks entries must be strings; got {type(t).__name__}"
                )
            if t not in VALID_CROSSWALK_TARGET_FRAMEWORKS:
                raise ValueError(
                    f"Unknown crosswalk target framework '{t}'. "
                    f"Must be one of {sorted(VALID_CROSSWALK_TARGET_FRAMEWORKS)}."
                )

    jurisdictions = inputs.get("jurisdictions")
    if jurisdictions is not None:
        if not isinstance(jurisdictions, list):
            raise ValueError("jurisdictions, when provided, must be a list of jurisdiction ids")
        for j in jurisdictions:
            if not isinstance(j, str):
                raise ValueError(
                    f"jurisdictions entries must be strings; got {type(j).__name__}"
                )


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


def _load_crosswalk_module():
    """Import the sibling crosswalk-matrix-builder plugin module.

    Lazy import so packager calls with include_crosswalk_coverage=False do
    not pay the YAML-load cost and are immune to crosswalk-side failures.
    """
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_mrp", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bucket_relationship(relationship: str) -> str:
    """Bucket a crosswalk relationship into covered/partial/gap."""
    if relationship in ("exact-match", "satisfies"):
        return "covered"
    if relationship in ("partial-match", "partial-satisfaction"):
        return "partial"
    if relationship == "no-mapping":
        return "gap"
    # complementary and statutory-presumption are neither coverage nor gap
    # for this summary; treat as partial so they appear in the denominator
    # without claiming full coverage.
    return "partial"


def _compute_coverage_for_target(
    mappings: list[dict[str, Any]],
    target_framework: str,
) -> dict[str, Any]:
    """Compute ISO Annex A coverage against a target framework.

    The crosswalk YAML files declare rows in either direction: some files
    use iso42001 as source with the target framework as target (e.g. NIST
    is indexed this way); others use the jurisdiction or peer framework
    as source with iso42001 as target (e.g. EU AI Act, UK ATRS). This
    function considers both directions so ISO Annex A controls are
    counted consistently regardless of the declaration direction.
    """
    per_control: dict[str, set[str]] = {}
    for m in mappings:
        sf = m.get("source_framework")
        tf = m.get("target_framework")
        if sf == "iso42001" and tf == target_framework:
            iso_ref = m.get("source_ref")
        elif sf == target_framework and tf == "iso42001":
            iso_ref = m.get("target_ref")
        else:
            continue
        if not iso_ref:
            continue
        per_control.setdefault(iso_ref, set()).add(
            _bucket_relationship(m.get("relationship", ""))
        )

    covered = 0
    partial = 0
    gap = 0
    top_gaps: list[str] = []
    for iso_ref, buckets in per_control.items():
        # Precedence: covered > partial > gap. A control is counted as
        # covered if any mapping to the target is exact-match or
        # satisfies; else partial if any is partial-match or
        # partial-satisfaction; else gap if every mapping is no-mapping.
        if "covered" in buckets:
            covered += 1
        elif "partial" in buckets:
            partial += 1
        elif "gap" in buckets:
            gap += 1
            top_gaps.append(iso_ref)

    total = covered + partial + gap
    coverage_percentage = round(covered / total * 100, 1) if total else 0.0

    return {
        "target_framework": target_framework,
        "iso_annex_a_controls_covered": covered,
        "iso_annex_a_controls_partial": partial,
        "iso_annex_a_controls_gaps": gap,
        "coverage_percentage": coverage_percentage,
        "top_gaps": sorted(top_gaps),
    }


def _alignment_label(avg_pct: float) -> str:
    if avg_pct >= 75.0:
        return "strong"
    if avg_pct >= 50.0:
        return "moderate"
    return "limited"


def _build_cross_framework_coverage(
    target_frameworks: list[str],
    jurisdictions: list[str],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Build the cross_framework_coverage section.

    Returns (section_or_none, warnings). On crosswalk load failure returns
    (None, [warning]).
    """
    try:
        crosswalk = _load_crosswalk_module()
    except Exception as exc:
        return (
            None,
            [f"Cross-framework coverage skipped: {type(exc).__name__}: {exc}"],
        )

    try:
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return (
            None,
            [f"Cross-framework coverage skipped: {type(exc).__name__}: {exc}"],
        )

    mappings = data.get("mappings", [])
    per_framework_summary: list[dict[str, Any]] = []
    for tf in target_frameworks:
        per_framework_summary.append(_compute_coverage_for_target(mappings, tf))

    if per_framework_summary:
        avg_pct = sum(p["coverage_percentage"] for p in per_framework_summary) / len(per_framework_summary)
    else:
        avg_pct = 0.0

    section: dict[str, Any] = {
        "target_frameworks": list(target_frameworks),
        "per_framework_summary": per_framework_summary,
        "overall_multi_framework_alignment": _alignment_label(avg_pct),
        "average_coverage_percentage": round(avg_pct, 1),
    }

    # Jurisdictional posture: map each supplied jurisdiction to its
    # applicable frameworks and coverage status.
    if jurisdictions:
        posture: list[dict[str, Any]] = []
        summary_by_tf = {p["target_framework"]: p for p in per_framework_summary}
        for jur in jurisdictions:
            applicable = _applicable_frameworks_for_jurisdiction(jur)
            entries: list[dict[str, Any]] = []
            for fw in applicable:
                # Use precomputed summary where possible; otherwise compute
                # on demand so that posture reflects the jurisdiction's
                # applicable frameworks even when not in target_frameworks.
                if fw in summary_by_tf:
                    summary = summary_by_tf[fw]
                else:
                    summary = _compute_coverage_for_target(mappings, fw)
                entries.append({
                    "framework": fw,
                    "coverage_percentage": summary["coverage_percentage"],
                    "status": _alignment_label(summary["coverage_percentage"]),
                })
            posture.append({
                "jurisdiction": jur,
                "applicable_frameworks": applicable,
                "framework_coverage": entries,
            })
        section["jurisdictional_posture"] = posture

    return section, []


def _applicable_frameworks_for_jurisdiction(jurisdiction: str) -> list[str]:
    """Map a jurisdiction id to the frameworks applicable there.

    Deliberately conservative: only frameworks present in the crosswalk
    catalogue are returned. Unknown jurisdictions return an empty list,
    which surfaces as an empty posture entry rather than an error.
    """
    mapping = {
        "eu": ["eu-ai-act", "iso42001"],
        "uk": ["uk-atrs", "iso42001"],
        "us-federal": ["nist-ai-rmf", "iso42001"],
        "us-colorado": ["colorado-sb-205", "nist-ai-rmf", "iso42001"],
        "us-california": ["ca-sb-942", "ca-ab-2013", "nist-ai-rmf", "iso42001"],
        "us-nyc": ["nyc-ll144", "nist-ai-rmf", "iso42001"],
        "singapore": ["singapore-magf", "iso42001"],
    }
    return mapping.get(jurisdiction, [])


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
            include_crosswalk_coverage: optional bool, default True.
            crosswalk_target_frameworks: optional list of framework ids,
                              default ["nist-ai-rmf", "eu-ai-act", "uk-atrs"].
            jurisdictions: optional list of jurisdiction ids (e.g. "eu",
                              "uk", "us-federal") for jurisdictional
                              posture subsection.

    Returns:
        Dict with timestamp, agent_signature, citations, sections (one
        per Clause 9.3.2 category), summary, warnings, distribution_hook,
        reviewed_by, and (when enabled) cross_framework_coverage.

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

    # Cross-framework coverage (opt-out, default on).
    include_coverage = inputs.get("include_crosswalk_coverage")
    if include_coverage is None:
        include_coverage = True
    target_frameworks = list(
        inputs.get("crosswalk_target_frameworks") or DEFAULT_CROSSWALK_TARGET_FRAMEWORKS
    )
    jurisdictions = list(inputs.get("jurisdictions") or [])

    cross_framework_coverage: dict[str, Any] | None = None
    if include_coverage:
        cross_framework_coverage, coverage_warnings = _build_cross_framework_coverage(
            target_frameworks, jurisdictions
        )
        warnings.extend(coverage_warnings)

    output: dict[str, Any] = {
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
    if cross_framework_coverage is not None:
        output["cross_framework_coverage"] = cross_framework_coverage
    return output


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

    # Cross-framework coverage summary.
    cfc = package.get("cross_framework_coverage")
    if cfc:
        lines.extend([
            "## Cross-framework coverage summary",
            "",
            f"- Target frameworks: {', '.join(cfc.get('target_frameworks', []))}",
            f"- Overall multi-framework alignment: {cfc.get('overall_multi_framework_alignment', 'limited')}",
            f"- Average coverage: {cfc.get('average_coverage_percentage', 0.0)}%",
            "",
            "| Target framework | Covered | Partial | Gaps | Coverage % |",
            "|---|---|---|---|---|",
        ])
        for entry in cfc.get("per_framework_summary", []):
            lines.append(
                "| {tf} | {c} | {p} | {g} | {pct}% |".format(
                    tf=entry.get("target_framework", ""),
                    c=entry.get("iso_annex_a_controls_covered", 0),
                    p=entry.get("iso_annex_a_controls_partial", 0),
                    g=entry.get("iso_annex_a_controls_gaps", 0),
                    pct=entry.get("coverage_percentage", 0.0),
                )
            )
        lines.append("")

        # Per-framework top gaps.
        any_gaps = any(e.get("top_gaps") for e in cfc.get("per_framework_summary", []))
        if any_gaps:
            lines.extend(["### Top ISO Annex A gaps per target framework", ""])
            for entry in cfc.get("per_framework_summary", []):
                tg = entry.get("top_gaps") or []
                if not tg:
                    continue
                lines.append(
                    f"- {entry.get('target_framework')}: {', '.join(tg)}"
                )
            lines.append("")

        # UK ATRS subsection when requested.
        if "uk-atrs" in cfc.get("target_frameworks", []):
            uk_entry = next(
                (e for e in cfc.get("per_framework_summary", []) if e.get("target_framework") == "uk-atrs"),
                None,
            )
            if uk_entry:
                lines.extend([
                    "### UK ATRS posture",
                    "",
                    f"- Coverage: {uk_entry.get('coverage_percentage', 0.0)}%",
                    f"- Controls with gaps: {uk_entry.get('iso_annex_a_controls_gaps', 0)}",
                ])
                if uk_entry.get("top_gaps"):
                    lines.append(f"- Top gaps: {', '.join(uk_entry['top_gaps'])}")
                lines.append("")

        # Jurisdictional posture subsection.
        posture = cfc.get("jurisdictional_posture") or []
        if posture:
            lines.extend(["### Jurisdictional posture", ""])
            for entry in posture:
                lines.append(f"- **{entry.get('jurisdiction', '')}**")
                applicable = entry.get("applicable_frameworks") or []
                if applicable:
                    lines.append(f"  - Applicable frameworks: {', '.join(applicable)}")
                for fw_entry in entry.get("framework_coverage", []):
                    lines.append(
                        f"  - {fw_entry.get('framework')}: "
                        f"{fw_entry.get('coverage_percentage', 0.0)}% "
                        f"({fw_entry.get('status', 'limited')})"
                    )
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
