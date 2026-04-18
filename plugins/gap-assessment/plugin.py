"""
AIGovOps: Gap Assessment Generator Plugin

Assesses an organization's current AIMS state against a target framework
and produces a structured gap report classifying every framework control
or subcategory as covered, partially-covered, not-covered, or
not-applicable, with a recommended next step for any gap.

Operationalizes the gap-assessment workflow referenced in
aigovclaw/workflows/gap-assessment.md. Serves iso42001, nist-ai-rmf,
and (when supplied) eu-ai-act target frameworks via the `target_framework`
flag. Where a current SoA is supplied (iso42001), coverage inference
uses the SoA's inclusion status; otherwise coverage is inferred from
provided evidence references per control.

Design stance: the plugin does NOT infer coverage without evidence.
Every classification is grounded in either:
1. An SoA row from a prior soa-generator emission.
2. An explicit evidence reference in the `current_state_evidence` input.
3. An explicit classification override in the `manual_classifications`
   input (organizational decision, for example marking a control
   not-applicable because the related technology is out of scope).

Controls with no evidence surface as `not-covered` with a
`REQUIRES REVIEWER DECISION` next step. This mirrors the soa-generator's
"no silent guessing" stance.

Status: Phase 3 minimum-viable implementation.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "gap-assessment/0.2.0"

VALID_FRAMEWORKS = ("iso42001", "nist", "eu-ai-act")

# Crosswalk-plugin framework ids that may be passed as reference frameworks
# for cross-framework gap surfacing. These are the ids declared in
# crosswalk-matrix-builder/data/frameworks.yaml.
VALID_CROSSWALK_REFERENCE_FRAMEWORKS = (
    "iso42001",
    "nist-ai-rmf",
    "eu-ai-act",
    "uk-atrs",
    "colorado-sb-205",
    "nyc-ll144",
)

# Map gap-assessment target_framework ids to crosswalk framework ids. The
# gap-assessment plugin predates crosswalk-matrix-builder and uses shorter
# identifiers; the crosswalk uses canonical versioned ids.
_TARGET_FRAMEWORK_TO_CROSSWALK_ID = {
    "iso42001": "iso42001",
    "nist": "nist-ai-rmf",
    "eu-ai-act": "eu-ai-act",
}

DEFAULT_CROSSWALK_REFERENCE_FRAMEWORKS = (
    "nist-ai-rmf",
    "eu-ai-act",
    "uk-atrs",
    "colorado-sb-205",
)
VALID_CLASSIFICATIONS = (
    "covered",
    "partially-covered",
    "not-covered",
    "not-applicable",
)

# Default iso42001 target list (same as soa-generator default). Verify
# against published standard per docs/lead-implementer-review.md.
DEFAULT_ISO_TARGETS: tuple[dict[str, str], ...] = (
    {"id": "A.2.2", "title": "AI policy"},
    {"id": "A.2.3", "title": "Alignment with other organizational policies"},
    {"id": "A.2.4", "title": "Review of the AI policy"},
    {"id": "A.3.2", "title": "AI roles and responsibilities"},
    {"id": "A.3.3", "title": "Reporting of concerns"},
    {"id": "A.4.2", "title": "Resource documentation"},
    {"id": "A.4.3", "title": "Data resources"},
    {"id": "A.4.4", "title": "Tooling resources"},
    {"id": "A.4.5", "title": "System and computing resources"},
    {"id": "A.4.6", "title": "Human resources"},
    {"id": "A.5.2", "title": "AI system impact assessment process"},
    {"id": "A.5.3", "title": "Documentation of AI system impact assessments"},
    {"id": "A.5.4", "title": "Assessing AI system impact on individuals or groups"},
    {"id": "A.5.5", "title": "Assessing societal impacts of AI systems"},
    {"id": "A.6.1.2", "title": "Objectives for responsible development of AI systems"},
    {"id": "A.6.1.3", "title": "Processes for responsible design and development"},
    {"id": "A.6.2.2", "title": "AI system requirements and specification"},
    {"id": "A.6.2.3", "title": "Documentation of AI system design and development"},
    {"id": "A.6.2.4", "title": "AI system verification and validation"},
    {"id": "A.6.2.5", "title": "AI system deployment"},
    {"id": "A.6.2.6", "title": "AI system operation and monitoring"},
    {"id": "A.6.2.7", "title": "AI system technical documentation"},
    {"id": "A.6.2.8", "title": "AI system log recording"},
    {"id": "A.7.2", "title": "Data for development and enhancement of AI systems"},
    {"id": "A.7.3", "title": "Acquisition of data"},
    {"id": "A.7.4", "title": "Quality of data for AI systems"},
    {"id": "A.7.5", "title": "Data provenance"},
    {"id": "A.7.6", "title": "Data preparation"},
    {"id": "A.8.2", "title": "System documentation and information for users"},
    {"id": "A.8.3", "title": "External reporting"},
    {"id": "A.8.4", "title": "Communication of incidents"},
    {"id": "A.8.5", "title": "Information for interested parties"},
    {"id": "A.9.2", "title": "Processes for responsible use of AI systems"},
    {"id": "A.9.3", "title": "Objectives for responsible use of AI systems"},
    {"id": "A.9.4", "title": "Intended use of the AI system"},
    {"id": "A.10.2", "title": "Allocating responsibilities"},
    {"id": "A.10.3", "title": "Suppliers"},
    {"id": "A.10.4", "title": "Customers"},
)

REQUIRED_INPUT_FIELDS = ("ai_system_inventory", "target_framework")

VALID_INPUT_FIELDS = (
    "ai_system_inventory",
    "target_framework",
    "targets",
    "soa_rows",
    "current_state_evidence",
    "manual_classifications",
    "exclusion_justifications",
    "scope_boundary",
    "reviewed_by",
    "surface_crosswalk_gaps",
    "crosswalk_reference_frameworks",
)


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    tf = inputs["target_framework"]
    if tf not in VALID_FRAMEWORKS:
        raise ValueError(f"target_framework must be one of {VALID_FRAMEWORKS}; got {tf!r}")

    inv = inputs["ai_system_inventory"]
    if not isinstance(inv, list):
        raise ValueError("ai_system_inventory must be a list")

    for field_name in ("targets", "soa_rows"):
        v = inputs.get(field_name)
        if v is not None and not isinstance(v, list):
            raise ValueError(f"{field_name}, when provided, must be a list")

    for field_name in ("current_state_evidence", "manual_classifications", "exclusion_justifications"):
        v = inputs.get(field_name)
        if v is not None and not isinstance(v, dict):
            raise ValueError(f"{field_name}, when provided, must be a dict keyed by control or subcategory id")

    classifications = inputs.get("manual_classifications") or {}
    for cid, value in classifications.items():
        if isinstance(value, str) and value not in VALID_CLASSIFICATIONS:
            raise ValueError(
                f"manual_classifications[{cid!r}] must be one of {VALID_CLASSIFICATIONS}; got {value!r}"
            )
        if isinstance(value, dict):
            status = value.get("classification")
            if status and status not in VALID_CLASSIFICATIONS:
                raise ValueError(
                    f"manual_classifications[{cid!r}].classification must be one of {VALID_CLASSIFICATIONS}; got {status!r}"
                )

    surface = inputs.get("surface_crosswalk_gaps")
    if surface is not None and not isinstance(surface, bool):
        raise ValueError("surface_crosswalk_gaps, when provided, must be a bool")

    ref_fws = inputs.get("crosswalk_reference_frameworks")
    if ref_fws is not None:
        if not isinstance(ref_fws, list):
            raise ValueError("crosswalk_reference_frameworks, when provided, must be a list")
        for fw in ref_fws:
            if fw not in VALID_CROSSWALK_REFERENCE_FRAMEWORKS:
                raise ValueError(
                    f"crosswalk_reference_frameworks entry {fw!r} is not a valid crosswalk framework id; "
                    f"must be one of {VALID_CROSSWALK_REFERENCE_FRAMEWORKS}"
                )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_targets(provided: list[Any] | None, target_framework: str) -> list[dict[str, str]]:
    """Return list of {id, title} dicts from provided or framework-specific default."""
    if provided:
        normalized: list[dict[str, str]] = []
        for entry in provided:
            if isinstance(entry, dict):
                cid = entry.get("id") or entry.get("control_id")
                title = entry.get("title") or entry.get("control_title", "")
            elif isinstance(entry, str):
                cid, title = entry, ""
            else:
                raise ValueError(f"target entry must be dict or string; got {type(entry).__name__}")
            if not cid:
                raise ValueError(f"target entry missing id: {entry!r}")
            normalized.append({"id": cid, "title": title})
        return normalized
    if target_framework == "iso42001":
        return [dict(t) for t in DEFAULT_ISO_TARGETS]
    # nist and eu-ai-act callers must supply targets; no embedded default.
    return []


def _citation_for_target(target_id: str, target_framework: str) -> str:
    if target_framework == "iso42001":
        return f"ISO/IEC 42001:2023, Annex A, Control {target_id}"
    if target_framework == "nist":
        return target_id  # NIST subcategories are their own citation form.
    # eu-ai-act: assume id is already formatted like "Article 9" or "Article 9, Paragraph 2"
    if target_id.lower().startswith("article") or target_id.lower().startswith("annex"):
        return f"EU AI Act, {target_id}"
    return f"EU AI Act, {target_id}"


def _classify_target(
    target: dict[str, str],
    target_framework: str,
    soa_rows_by_id: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, Any],
    manual_by_id: dict[str, Any],
    exclusion_by_id: dict[str, str],
) -> tuple[str, str, str, list[str]]:
    """Return (classification, justification, next_step, warnings)."""
    warnings: list[str] = []
    cid = target["id"]

    # Manual override highest priority; represents explicit organizational decision.
    manual = manual_by_id.get(cid)
    if manual is not None:
        if isinstance(manual, str):
            classification = manual
            justification = "Manual classification set by organization."
        else:
            classification = manual.get("classification", "not-covered")
            justification = manual.get("justification") or "Manual classification set by organization."
        if not justification.strip():
            warnings.append(
                f"{cid}: manual classification has blank justification; every classification needs a basis."
            )
        next_step = _default_next_step(classification)
        return classification, justification, next_step, warnings

    # Explicit exclusion.
    exclusion = exclusion_by_id.get(cid)
    if exclusion and exclusion.strip():
        return "not-applicable", exclusion, "None; control out of scope.", warnings
    if exclusion is not None and not exclusion.strip():
        warnings.append(f"{cid}: exclusion_justifications entry is blank; treating as no evidence.")

    # SoA lookup (iso42001 only).
    if target_framework == "iso42001":
        soa_row = soa_rows_by_id.get(cid)
        if soa_row:
            status = soa_row.get("status", "")
            justification = soa_row.get("justification") or f"Inferred from SoA row with status {status!r}."
            if status == "included-implemented":
                return "covered", justification, "Continue routine monitoring.", warnings
            if status == "included-partial":
                return "partially-covered", justification, "Complete the implementation plan referenced in the SoA.", warnings
            if status == "included-planned":
                return "not-covered", justification, "Execute the planned implementation per the SoA's plan reference.", warnings
            if status == "excluded":
                # Distinguish real exclusions from placeholder exclusions that
                # soa-generator emits when it lacks evidence. The latter are
                # genuine gaps, not applicability decisions.
                if justification and "REQUIRES REVIEWER DECISION" in justification:
                    return (
                        "not-covered",
                        "SoA emitted excluded-with-review-required: no evidence of inclusion and no exclusion justification.",
                        "Either document evidence of coverage or justify not-applicable.",
                        warnings,
                    )
                return "not-applicable", justification, "None; control excluded per SoA.", warnings

    # Evidence reference lookup.
    evidence = evidence_by_id.get(cid)
    if evidence:
        if isinstance(evidence, dict):
            evidence_strength = evidence.get("strength", "full")
            evidence_refs = evidence.get("refs") or []
            justification = evidence.get("justification") or ""
        else:
            evidence_strength = "full"
            evidence_refs = evidence if isinstance(evidence, list) else [str(evidence)]
            justification = ""
        ref_text = ", ".join(str(r) for r in evidence_refs) if evidence_refs else "(no refs supplied)"
        if not evidence_refs:
            warnings.append(
                f"{cid}: evidence entry has no refs; coverage cannot be grounded in specific artifacts."
            )
        if evidence_strength == "partial":
            return (
                "partially-covered",
                justification or f"Partial evidence: {ref_text}.",
                "Identify remaining gap and establish an implementation plan.",
                warnings,
            )
        return (
            "covered",
            justification or f"Covered by evidence: {ref_text}.",
            "Continue routine monitoring.",
            warnings,
        )

    # No evidence.
    warnings.append(
        f"{cid}: no SoA row, evidence reference, or manual classification supplied. "
        "Classification defaults to not-covered with reviewer-decision-required justification."
    )
    return (
        "not-covered",
        "REQUIRES REVIEWER DECISION: no evidence of coverage and no exclusion justification.",
        "Either document evidence of coverage or justify not-applicable.",
        warnings,
    )


_CROSSWALK_MODULE_CACHE: Any = None


def _load_crosswalk_module():
    """Lazily load the sibling crosswalk-matrix-builder plugin module.

    The plugins directory uses hyphenated names so a straight import is not
    available. This helper resolves the sibling path and loads
    ``crosswalk-matrix-builder/plugin.py`` via importlib. Result is cached.
    """
    global _CROSSWALK_MODULE_CACHE
    if _CROSSWALK_MODULE_CACHE is not None:
        return _CROSSWALK_MODULE_CACHE
    plugin_path = (
        Path(__file__).resolve().parent.parent
        / "crosswalk-matrix-builder"
        / "plugin.py"
    )
    if not plugin_path.is_file():
        raise FileNotFoundError(f"crosswalk-matrix-builder/plugin.py not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location("_gap_assessment_crosswalk", plugin_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _CROSSWALK_MODULE_CACHE = module
    return module


def _surface_crosswalk_gaps(
    target_framework: str,
    reference_frameworks: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (surfaced, warnings).

    For each reference framework, query the crosswalk for bidirectional
    no-mapping entries between the reference and the gap-assessment target.
    Each returned record names the direction and carries a trimmed row list.
    """
    surfaced: list[dict[str, Any]] = []
    warnings: list[str] = []

    crosswalk_target = _TARGET_FRAMEWORK_TO_CROSSWALK_ID.get(target_framework)
    if crosswalk_target is None:
        warnings.append(
            f"Crosswalk gap surfacing skipped: no crosswalk framework id mapping for target_framework={target_framework!r}."
        )
        return surfaced, warnings

    try:
        crosswalk = _load_crosswalk_module()
    except Exception as exc:
        warnings.append(f"Crosswalk gap surfacing skipped: {exc}")
        return surfaced, warnings

    for ref_fw in reference_frameworks:
        if ref_fw == crosswalk_target:
            # Self-pair is meaningless.
            continue
        for direction_label, src, tgt in (
            ("reference-beyond-target", ref_fw, crosswalk_target),
            ("target-beyond-reference", crosswalk_target, ref_fw),
        ):
            try:
                result = crosswalk.build_matrix({
                    "query_type": "gaps",
                    "source_framework": src,
                    "target_framework": tgt,
                })
            except Exception as exc:
                warnings.append(
                    f"Crosswalk gap surfacing skipped for {src!r}->{tgt!r}: {exc}"
                )
                continue

            gap_rows = result.get("gaps") or []
            trimmed: list[dict[str, Any]] = []
            for row in gap_rows:
                citation_sources = row.get("citation_sources") or []
                citation_label = ""
                for src_item in citation_sources:
                    pub = (src_item.get("publication") or "").strip()
                    if pub:
                        citation_label = pub
                        break
                trimmed.append({
                    "source_ref": row.get("source_ref", ""),
                    "source_title": row.get("source_title", ""),
                    "notes": row.get("notes", "") or "",
                    "citation": citation_label,
                })

            surfaced.append({
                "reference_framework": ref_fw,
                "target_framework": crosswalk_target,
                "direction": direction_label,
                "gap_count": len(trimmed),
                "gaps": trimmed,
            })

    return surfaced, warnings


def _default_next_step(classification: str) -> str:
    return {
        "covered": "Continue routine monitoring.",
        "partially-covered": "Complete the implementation plan; track progress in the risk register.",
        "not-covered": "Establish an implementation plan with owner and target date.",
        "not-applicable": "None; control out of scope.",
    }.get(classification, "")


def generate_gap_assessment(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a structured gap assessment against a target framework.

    Args:
        inputs: Dict with:
            ai_system_inventory: list of AI systems in scope.
            target_framework: 'iso42001', 'nist', or 'eu-ai-act'.
            targets: optional list of {id, title} dicts. Required for
                     nist and eu-ai-act; defaults to Annex A for iso42001.
            soa_rows: optional list of SoA rows from soa-generator; used
                      for iso42001 coverage inference.
            current_state_evidence: optional dict mapping target id to
                                    evidence. Value may be a list of refs,
                                    a string ref, or a dict with
                                    {refs, strength, justification}.
            manual_classifications: optional dict mapping target id to
                                    classification string or dict with
                                    {classification, justification}.
            exclusion_justifications: optional dict mapping target id to
                                      exclusion justification text.
            scope_boundary: optional string describing AIMS scope for
                            report context.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, target_framework, citations,
        rows, summary, warnings, reviewed_by.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)
    tf = inputs["target_framework"]
    targets = _normalize_targets(inputs.get("targets"), tf)
    if not targets:
        raise ValueError(
            f"target_framework={tf!r} has no embedded default targets; "
            "supply the 'targets' input with the subcategory or article list."
        )

    soa_rows_by_id = {r["control_id"]: r for r in (inputs.get("soa_rows") or []) if "control_id" in r}
    evidence_by_id = inputs.get("current_state_evidence") or {}
    manual_by_id = inputs.get("manual_classifications") or {}
    exclusion_by_id = inputs.get("exclusion_justifications") or {}

    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = dict.fromkeys(VALID_CLASSIFICATIONS, 0)

    for target in targets:
        classification, justification, next_step, warnings = _classify_target(
            target, tf, soa_rows_by_id, evidence_by_id, manual_by_id, exclusion_by_id
        )
        counts[classification] = counts.get(classification, 0) + 1
        rows.append({
            "target_id": target["id"],
            "target_title": target["title"],
            "citation": _citation_for_target(target["id"], tf),
            "classification": classification,
            "justification": justification,
            "next_step": next_step,
            "warnings": warnings,
        })

    register_warnings: list[str] = []
    known_ids = {t["id"] for t in targets}
    for cid in evidence_by_id:
        if cid not in known_ids:
            register_warnings.append(
                f"current_state_evidence references {cid!r} which is not in targets; add to targets or correct the key."
            )
    for cid in manual_by_id:
        if cid not in known_ids:
            register_warnings.append(
                f"manual_classifications references {cid!r} which is not in targets."
            )

    summary = {
        "target_framework": tf,
        "total_targets": len(targets),
        "classification_counts": counts,
        "targets_with_warnings": sum(1 for r in rows if r["warnings"]),
        "coverage_score": (
            (counts["covered"] + 0.5 * counts["partially-covered"]) /
            max(1, counts["covered"] + counts["partially-covered"] + counts["not-covered"])
        ),
    }

    citations: list[str] = []
    if tf == "iso42001":
        citations = ["ISO/IEC 42001:2023, Clause 6.1.2", "ISO/IEC 42001:2023, Clause 6.1.3"]
    elif tf == "nist":
        citations = ["MAP 4.1", "MANAGE 1.2"]
    elif tf == "eu-ai-act":
        citations = ["EU AI Act, Article 9"]  # Risk-management reference; caller may override.

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "target_framework": tf,
        "scope_boundary": inputs.get("scope_boundary"),
        "citations": citations,
        "rows": rows,
        "summary": summary,
        "warnings": register_warnings,
        "reviewed_by": inputs.get("reviewed_by"),
    }

    surface = inputs.get("surface_crosswalk_gaps")
    if surface is None:
        surface = True
    if surface:
        reference_frameworks = inputs.get("crosswalk_reference_frameworks")
        if reference_frameworks is None:
            reference_frameworks = list(DEFAULT_CROSSWALK_REFERENCE_FRAMEWORKS)
        surfaced, surfacing_warnings = _surface_crosswalk_gaps(tf, reference_frameworks)
        output["crosswalk_gaps_surfaced"] = surfaced
        if surfacing_warnings:
            output["warnings"] = list(output["warnings"]) + surfacing_warnings

    return output


def render_markdown(assessment: dict[str, Any]) -> str:
    """Render a gap assessment as Markdown."""
    required = ("timestamp", "agent_signature", "target_framework", "citations", "rows", "summary")
    missing = [k for k in required if k not in assessment]
    if missing:
        raise ValueError(f"assessment missing required fields: {missing}")

    tf = assessment["target_framework"]
    summary = assessment["summary"]
    coverage_pct = f"{summary['coverage_score'] * 100:.1f}%"

    lines = [
        f"# Gap Assessment: {tf}",
        "",
        f"**Generated at (UTC):** {assessment['timestamp']}",
        f"**Generated by:** {assessment['agent_signature']}",
    ]
    if assessment.get("scope_boundary"):
        lines.append(f"**Scope boundary:** {assessment['scope_boundary']}")
    if assessment.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {assessment['reviewed_by']}")
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Target framework: {tf}",
        f"- Total targets: {summary['total_targets']}",
        f"- Coverage score: {coverage_pct}",
        f"- Classification counts: " + ", ".join(f"{k}={v}" for k, v in summary["classification_counts"].items()),
        f"- Targets with warnings: {summary['targets_with_warnings']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in assessment["citations"]:
        lines.append(f"- {c}")

    # Group rows by classification for easier review.
    lines.extend(["", "## Gaps by classification", ""])
    for classification in VALID_CLASSIFICATIONS:
        group = [r for r in assessment["rows"] if r["classification"] == classification]
        if not group:
            continue
        lines.extend([f"### {classification} ({len(group)})", "", "| Target | Citation | Justification | Next step |", "|---|---|---|---|"])
        for row in group:
            justification = (row.get("justification") or "").replace("|", "\\|")
            next_step = (row.get("next_step") or "").replace("|", "\\|")
            lines.append(
                f"| {row['target_id']}: {row.get('target_title', '')} | {row.get('citation', '')} | "
                f"{justification} | {next_step} |"
            )
        lines.append("")

    # Cross-framework gap visibility (opt-out enrichment from crosswalk plugin).
    surfaced = assessment.get("crosswalk_gaps_surfaced")
    if surfaced is not None:
        lines.extend(["## Cross-framework gap visibility", ""])
        if not surfaced:
            lines.append(
                "No cross-framework gaps surfaced. Verify crosswalk_reference_frameworks or crosswalk data scope."
            )
            lines.append("")
        else:
            lines.append(
                "Gaps below are sourced from crosswalk-matrix-builder no-mapping entries. "
                "See the crosswalk plugin for the full row list and citations."
            )
            lines.append("")
            # Group by reference_framework.
            by_ref: dict[str, list[dict[str, Any]]] = {}
            for entry in surfaced:
                by_ref.setdefault(entry["reference_framework"], []).append(entry)
            for ref_fw in sorted(by_ref):
                entries = by_ref[ref_fw]
                total = sum(e["gap_count"] for e in entries)
                lines.append(f"### {ref_fw} ({total} gap rows)")
                lines.append("")
                for entry in entries:
                    lines.append(
                        f"- direction: {entry['direction']} "
                        f"(source: {_direction_source(entry)}, target: {_direction_target(entry)}); "
                        f"gap_count: {entry['gap_count']}"
                    )
                    top = entry["gaps"][:5]
                    for gap in top:
                        ref = gap.get("source_ref", "")
                        title = gap.get("source_title", "")
                        notes = (gap.get("notes") or "").replace("\n", " ")
                        citation = gap.get("citation", "")
                        lines.append(f"  - {ref}: {title}. {notes} [{citation}]")
                    remaining = entry["gap_count"] - len(top)
                    if remaining > 0:
                        lines.append(
                            f"  - (+{remaining} more; query crosswalk-matrix-builder for the full list)"
                        )
                lines.append("")

    warnings = [(r["target_id"], w) for r in assessment["rows"] for w in r["warnings"]]
    if warnings or assessment.get("warnings"):
        lines.extend(["## Warnings", ""])
        for w in assessment.get("warnings", []):
            lines.append(f"- (report) {w}")
        for tid, w in warnings:
            lines.append(f"- ({tid}) {w}")

    lines.append("")
    return "\n".join(lines)


def _direction_source(entry: dict[str, Any]) -> str:
    if entry["direction"] == "reference-beyond-target":
        return entry["reference_framework"]
    return entry["target_framework"]


def _direction_target(entry: dict[str, Any]) -> str:
    if entry["direction"] == "reference-beyond-target":
        return entry["target_framework"]
    return entry["reference_framework"]


def render_csv(assessment: dict[str, Any]) -> str:
    """Render gap assessment rows as CSV.

    The main per-target rows use the standard six columns. When the
    assessment carries a non-empty ``crosswalk_gaps_surfaced`` block, one
    summary row per (reference_framework, direction) pair is appended so
    consumers can see cross-framework gap counts without bloating the
    primary table with full gap text.
    """
    if "rows" not in assessment:
        raise ValueError("assessment missing 'rows' field")
    header = "target_id,target_title,citation,classification,justification,next_step"
    lines = [header]
    for r in assessment["rows"]:
        fields = [
            _csv_escape(str(r.get("target_id", ""))),
            _csv_escape(str(r.get("target_title", "") or "")),
            _csv_escape(str(r.get("citation", ""))),
            _csv_escape(str(r.get("classification", ""))),
            _csv_escape(str(r.get("justification", "") or "")),
            _csv_escape(str(r.get("next_step", "") or "")),
        ]
        lines.append(",".join(fields))

    surfaced = assessment.get("crosswalk_gaps_surfaced") or []
    for entry in surfaced:
        ref_fw = entry.get("reference_framework", "")
        direction = entry.get("direction", "")
        count = entry.get("gap_count", 0)
        target_id = f"CROSSWALK:{ref_fw}:{direction}"
        target_title = f"Cross-framework gap summary ({ref_fw}, {direction})"
        justification = f"{count} no-mapping rows surfaced from crosswalk-matrix-builder."
        next_step = "Query crosswalk-matrix-builder for full gap rows and citations."
        fields = [
            _csv_escape(target_id),
            _csv_escape(target_title),
            _csv_escape("crosswalk-matrix-builder"),
            _csv_escape("crosswalk-summary"),
            _csv_escape(justification),
            _csv_escape(next_step),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
