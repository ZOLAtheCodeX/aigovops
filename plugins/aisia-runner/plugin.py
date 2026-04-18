"""
AIGovOps: AI System Impact Assessment (AISIA) Runner Plugin

Generates ISO/IEC 42001:2023 Clause 6.1.4 AISIAs and NIST AI RMF 1.0 MAP
1.1, 3.1, 3.2, 5.1 impact assessments.

This plugin operationalizes the `AISIA-section` artifact type defined in
the iso42001 skill's Tier 1 T1.2 and the nist-ai-rmf skill's T1.1. A
single implementation serves both frameworks; rendering differences are
controlled by a `framework` flag that determines which citation family is
emitted.

Design stance: the plugin does NOT invent impacts. Impact identification is
a judgment-bound activity requiring stakeholder consultation and domain
expertise per Clause 6.1.4 and A.5.4/A.5.5. The plugin accepts provided
impact assessments, enriches each with computed residual severity and
likelihood from the supplied rubric, cross-links existing controls to
SoA rows, flags missing fields as row-level warnings, and optionally
scaffolds empty placeholders for (stakeholder, impact_dimension) pairs
without identified impacts so reviewers can see coverage gaps.

When invoked against a high-risk EU AI Act system, the plugin additionally
verifies that the AISIA covers each element of Article 27(1)(a)-(f)
Fundamental Rights Impact Assessment content and enriches each impact
section with cross-framework citations sourced from
crosswalk-matrix-builder.

Status: Phase 4 implementation adding crosswalk enrichment and EU AI Act
Article 27 FRIA coverage verification.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "aisia-runner/0.2.0"

# Default impact dimensions required by Clause 6.1.4 and addressed by
# Annex A controls A.5.4 (individual and group impacts) and A.5.5
# (societal impacts).
DEFAULT_IMPACT_DIMENSIONS = (
    "fundamental-rights",
    "group-fairness",
    "societal",
    "physical-safety",
)

DEFAULT_SEVERITY_SCALE = ("negligible", "minor", "moderate", "major", "catastrophic")
DEFAULT_LIKELIHOOD_SCALE = ("rare", "unlikely", "possible", "likely", "almost-certain")

VALID_FRAMEWORKS = ("iso42001", "nist", "dual")

REQUIRED_INPUT_FIELDS = ("system_description", "affected_stakeholders")

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily inside
# the enrichment helper so AISIA calls with enrich_with_crosswalk=False
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
    "cppa-admt",
    "ccpa-cpra",
    "ca-sb-942",
    "ca-ab-2013",
    "ca-ab-1008",
    "ca-sb-1001",
    "ca-ab-1836",
)

DEFAULT_CROSSWALK_TARGET_FRAMEWORKS = ("nist-ai-rmf", "eu-ai-act")

# ISO/IEC 42001:2023 Annex A controls that anchor AISIA impact assessment
# activity. The enrichment filter pulls crosswalk rows whose source_ref is
# any of these controls. A.5.2 is the impact-assessment-process control;
# A.5.4 is the individual/group impact-assessment control.
AISIA_ANCHOR_CONTROLS = ("A.5.2", "A.5.4")

# Mapping of impact_dimension to the primary ISO anchor control used to
# query the crosswalk. Societal and fundamental-rights dimensions still
# anchor on A.5.4 because the crosswalk pivots individual/group impacts
# through that control; A.5.5 rows (societal) are merged in as a secondary
# pull for the societal dimension.
_DIMENSION_TO_ISO_ANCHORS: dict[str, tuple[str, ...]] = {
    "fundamental-rights": ("A.5.2", "A.5.4"),
    "group-fairness": ("A.5.4",),
    "societal": ("A.5.4", "A.5.5"),
    "physical-safety": ("A.5.4",),
    "human-oversight": ("A.5.2", "A.5.4"),
}

VALID_INPUT_FIELDS = (
    "system_description",
    "affected_stakeholders",
    "impact_assessments",
    "impact_dimensions",
    "risk_scoring_rubric",
    "soa_rows",
    "framework",
    "scaffold",
    "reviewed_by",
    "enrich_with_crosswalk",
    "crosswalk_target_frameworks",
    "verify_eu_fria_coverage",
    "assessment_period",
    "frequency",
    "affected_persons",
    "human_oversight",
    "mitigations",
    "risks_if_materialised",
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
    for req in ("system_name", "purpose"):
        if req not in system:
            raise ValueError(f"system_description missing required field: {req}")

    stakeholders = inputs["affected_stakeholders"]
    if not isinstance(stakeholders, list) or not stakeholders:
        raise ValueError("affected_stakeholders must be a non-empty list")
    for s in stakeholders:
        if isinstance(s, str):
            continue
        if isinstance(s, dict) and "name" in s:
            continue
        raise ValueError(f"each stakeholder entry must be a string or a dict with 'name'; got {s!r}")

    framework = inputs.get("framework", "iso42001")
    if framework not in VALID_FRAMEWORKS:
        raise ValueError(f"framework must be one of {VALID_FRAMEWORKS}; got {framework!r}")

    rubric = inputs.get("risk_scoring_rubric")
    if rubric is not None:
        if not isinstance(rubric, dict):
            raise ValueError("risk_scoring_rubric must be a dict")
        # Rubric uses severity_scale (preferred) or impact_scale (legacy).
        if "severity_scale" not in rubric and "impact_scale" not in rubric:
            raise ValueError("risk_scoring_rubric must contain severity_scale (or impact_scale)")
        if "likelihood_scale" not in rubric:
            raise ValueError("risk_scoring_rubric must contain likelihood_scale")

    impact_assessments = inputs.get("impact_assessments")
    if impact_assessments is not None and not isinstance(impact_assessments, list):
        raise ValueError("impact_assessments, when provided, must be a list")

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")

    verify_fria = inputs.get("verify_eu_fria_coverage")
    if verify_fria is not None and not isinstance(verify_fria, bool):
        raise ValueError("verify_eu_fria_coverage, when provided, must be a bool")

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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _score_index(value: str | None, scale: tuple[str, ...] | list[str]) -> int | None:
    if value is None:
        return None
    try:
        return list(scale).index(value) + 1
    except ValueError:
        return None


def _stakeholder_name(s: Any) -> str:
    if isinstance(s, str):
        return s
    return s.get("name", "")


def _resolve_control_ref(control: Any, soa_rows_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if isinstance(control, str):
        return {
            "control_id": control,
            "soa_row_ref": soa_rows_by_id.get(control, {}).get("row_ref") if control in soa_rows_by_id else None,
            "description": "",
        }
    if isinstance(control, dict):
        cid = control.get("control_id", "")
        return {
            "control_id": cid,
            "soa_row_ref": soa_rows_by_id.get(cid, {}).get("row_ref") if cid in soa_rows_by_id else None,
            "description": control.get("description", ""),
        }
    return {"control_id": "", "soa_row_ref": None, "description": f"(unrecognized: {control!r})"}


def _iso_citations(dimension: str) -> list[str]:
    citations = [
        "ISO/IEC 42001:2023, Clause 6.1.4",
        "ISO/IEC 42001:2023, Annex A, Control A.5.2",
        "ISO/IEC 42001:2023, Annex A, Control A.5.3",
    ]
    if dimension == "societal":
        citations.append("ISO/IEC 42001:2023, Annex A, Control A.5.5")
    else:
        citations.append("ISO/IEC 42001:2023, Annex A, Control A.5.4")
    return citations


def _nist_citations(dimension: str) -> list[str]:
    base = ["MAP 1.1", "MAP 3.1", "MAP 3.2", "MAP 5.1"]
    if dimension == "physical-safety":
        base.append("MEASURE 2.6")
    return base


def _physical_safety_severity_floor(
    severity: str | None, severity_scale: tuple[str, ...] | list[str]
) -> str | None:
    """Return a warning string if physical-safety severity is below 'moderate', else None."""
    if severity is None:
        return None
    idx = _score_index(severity, severity_scale)
    moderate_idx = _score_index("moderate", severity_scale)
    if idx is None or moderate_idx is None:
        return None
    if idx < moderate_idx:
        return (
            f"Physical-safety severity '{severity}' is below 'moderate' in the scale. "
            "Physical-safety impact classifications below moderate for systems with any patient-harm or "
            "physical-harm potential require explicit justification."
        )
    return None


def _enrich_section(
    entry: dict[str, Any],
    stakeholder_names: set[str],
    dimensions: tuple[str, ...],
    severity_scale: tuple[str, ...] | list[str],
    likelihood_scale: tuple[str, ...] | list[str],
    soa_rows_by_id: dict[str, dict[str, Any]],
    framework: str,
    index: int,
    system_type: str | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []

    stakeholder = entry.get("stakeholder_group") or entry.get("stakeholder")
    if not stakeholder:
        raise ValueError(f"impact_assessment entry {index} missing stakeholder_group")
    if stakeholder not in stakeholder_names:
        warnings.append(
            f"stakeholder_group '{stakeholder}' is not in affected_stakeholders; add it or correct the reference."
        )

    dimension = entry.get("impact_dimension")
    if not dimension:
        raise ValueError(f"impact_assessment entry {index} missing impact_dimension")
    if dimension not in dimensions:
        warnings.append(
            f"impact_dimension '{dimension}' is not in the configured dimensions {list(dimensions)}; "
            "add it or correct the value."
        )

    description = entry.get("impact_description") or entry.get("description") or ""
    if not description.strip():
        warnings.append(
            "impact_description is empty; describe the impact on this stakeholder group before the AISIA is audit-ready."
        )

    severity = entry.get("severity")
    likelihood = entry.get("likelihood")
    if severity is None or likelihood is None:
        warnings.append(
            "severity and likelihood are required for an AISIA section to be audit-ready."
        )
    if severity is not None and _score_index(severity, severity_scale) is None:
        warnings.append(
            f"severity value '{severity}' is not in severity_scale; cannot score."
        )
    if likelihood is not None and _score_index(likelihood, likelihood_scale) is None:
        warnings.append(
            f"likelihood value '{likelihood}' is not in likelihood_scale; cannot score."
        )

    # Physical-safety floor: severity must be at least 'moderate' when the system has any physical-harm potential.
    if dimension == "physical-safety":
        floor_warning = _physical_safety_severity_floor(severity, severity_scale)
        if floor_warning:
            warnings.append(floor_warning)

    residual_severity = entry.get("residual_severity")
    residual_likelihood = entry.get("residual_likelihood")
    existing_controls = [_resolve_control_ref(c, soa_rows_by_id) for c in (entry.get("existing_controls") or [])]
    additional_controls = list(entry.get("additional_controls_recommended") or [])

    if not existing_controls and not additional_controls:
        warnings.append(
            "no existing_controls and no additional_controls_recommended. "
            "Every impact section must list at least one control (existing or recommended) to be audit-ready."
        )

    assessor = entry.get("assessor")
    assessment_date = entry.get("assessment_date")

    if framework == "iso42001":
        citations = _iso_citations(dimension)
    elif framework == "nist":
        citations = _nist_citations(dimension)
    else:
        citations = _nist_citations(dimension) + _iso_citations(dimension)

    # Passthrough fields used by the EU FRIA coverage verifier. Kept on the
    # section so the verifier does not need to re-read inputs.
    process_description = entry.get("process_description") or entry.get("system_description")

    return {
        "id": entry.get("id") or f"AISIA-{index:04d}",
        "stakeholder_group": stakeholder,
        "impact_dimension": dimension,
        "impact_description": description,
        "severity": severity,
        "likelihood": likelihood,
        "existing_controls": existing_controls,
        "residual_severity": residual_severity,
        "residual_likelihood": residual_likelihood,
        "additional_controls_recommended": additional_controls,
        "assessor": assessor,
        "assessment_date": assessment_date,
        "process_description": process_description,
        "citations": citations,
        "warnings": warnings,
    }


def _load_crosswalk_module():
    """Import the sibling crosswalk-matrix-builder plugin module.

    Lazy import so AISIA generation with enrich_with_crosswalk=False does
    not pay the YAML-load cost and is immune to crosswalk-side failures.
    """
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_aisia", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enrich_sections_with_crosswalk(
    sections: list[dict[str, Any]],
    target_frameworks: list[str],
) -> tuple[list[str], dict[str, int]]:
    """Attach cross_framework_coverage to each section in-place.

    Returns (top_level_warnings, summary_counts). On crosswalk load failure,
    returns a single warning and leaves sections unenriched (no key added).

    Performance: loads crosswalk data once and filters in-memory; does not
    call build_matrix per section.
    """
    try:
        crosswalk = _load_crosswalk_module()
    except Exception as exc:
        return (
            [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"],
            {"sections_with_coverage": 0, "sections_without_coverage": 0, "total_mappings_included": 0},
        )

    try:
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return (
            [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"],
            {"sections_with_coverage": 0, "sections_without_coverage": 0, "total_mappings_included": 0},
        )

    # Index ISO A.5.2/A.5.4/A.5.5 anchor rows by source_ref for O(1) lookup
    # per section.
    relevant_anchors = ("A.5.2", "A.5.4", "A.5.5")
    by_source_ref: dict[str, list[dict[str, Any]]] = {}
    for m in data.get("mappings", []):
        if m.get("source_framework") != "iso42001":
            continue
        sref = m.get("source_ref")
        if sref not in relevant_anchors:
            continue
        by_source_ref.setdefault(sref, []).append(m)

    allowed = set(target_frameworks)
    sections_with = 0
    sections_without = 0
    total_included = 0

    for section in sections:
        dimension = section.get("impact_dimension")
        anchors = _DIMENSION_TO_ISO_ANCHORS.get(dimension, AISIA_ANCHOR_CONTROLS)
        collected: list[dict[str, Any]] = []
        seen_mapping_ids: set[str] = set()
        for anchor in anchors:
            for m in by_source_ref.get(anchor, []):
                if m.get("target_framework") not in allowed:
                    continue
                mid = m.get("id")
                if mid in seen_mapping_ids:
                    continue
                seen_mapping_ids.add(mid)
                citations = m.get("citation_sources") or []
                citation_label = ""
                if citations:
                    pub = (citations[0].get("publication") or "").strip()
                    citation_label = pub
                collected.append({
                    "target_framework": m.get("target_framework"),
                    "target_ref": m.get("target_ref"),
                    "target_title": m.get("target_title"),
                    "relationship": m.get("relationship"),
                    "confidence": m.get("confidence"),
                    "citation": citation_label,
                })

        section["cross_framework_coverage"] = collected
        if collected:
            sections_with += 1
            total_included += len(collected)
        else:
            sections_without += 1
            section.setdefault("warnings", []).append(
                f"No cross-framework coverage found for impact_dimension={dimension}"
            )

    return (
        [],
        {
            "sections_with_coverage": sections_with,
            "sections_without_coverage": sections_without,
            "total_mappings_included": total_included,
        },
    )


def _verify_eu_fria_coverage(
    inputs: dict[str, Any],
    sections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify that the AISIA covers each Article 27(1)(a)-(f) element.

    Presence rules per instruction spec:
      (a) any section with process_description or system_description context
      (b) top-level assessment_period or frequency field
      (c) stakeholder_groups or affected_persons top-level field non-empty
      (d) sections with severity/likelihood scoring and identified harms
      (e) top-level human_oversight field or a human-oversight dimension section
      (f) top-level mitigations or risks_if_materialised field
    """
    system = inputs.get("system_description") or {}

    # (a) process description.
    a_refs: list[str] = []
    if system.get("process_description") or system.get("system_description"):
        a_refs.append("system_description.process_description")
    for s in sections:
        if s.get("process_description"):
            a_refs.append(f"sections[{s.get('id')}].process_description")
    a_present = bool(a_refs)

    # (b) period or frequency.
    b_refs: list[str] = []
    if inputs.get("assessment_period"):
        b_refs.append("assessment_period")
    if inputs.get("frequency"):
        b_refs.append("frequency")
    b_present = bool(b_refs)

    # (c) categories of affected persons.
    c_refs: list[str] = []
    stakeholders = inputs.get("affected_stakeholders") or []
    if stakeholders:
        c_refs.append("affected_stakeholders")
    if inputs.get("affected_persons"):
        c_refs.append("affected_persons")
    c_present = bool(c_refs)

    # (d) specific risks of harm (sections with severity+likelihood and a description).
    d_refs: list[str] = []
    for s in sections:
        if (
            s.get("severity")
            and s.get("likelihood")
            and (s.get("impact_description") or "").strip()
        ):
            d_refs.append(f"sections[{s.get('id')}]")
    d_present = bool(d_refs)

    # (e) human oversight measures.
    e_refs: list[str] = []
    if inputs.get("human_oversight"):
        e_refs.append("human_oversight")
    for s in sections:
        if s.get("impact_dimension") == "human-oversight":
            e_refs.append(f"sections[{s.get('id')}]")
    e_present = bool(e_refs)

    # (f) measures if risks materialise.
    f_refs: list[str] = []
    if inputs.get("mitigations"):
        f_refs.append("mitigations")
    if inputs.get("risks_if_materialised"):
        f_refs.append("risks_if_materialised")
    f_present = bool(f_refs)

    elements = [
        ("article_27_1_a_process_description", a_present, a_refs,
         "Missing: EU AI Act, Article 27, Paragraph 1(a) process description"),
        ("article_27_1_b_period_frequency", b_present, b_refs,
         "Missing: EU AI Act, Article 27, Paragraph 1(b) period or frequency of assessment"),
        ("article_27_1_c_affected_persons", c_present, c_refs,
         "Missing: EU AI Act, Article 27, Paragraph 1(c) categories of affected persons"),
        ("article_27_1_d_harms", d_present, d_refs,
         "Missing: EU AI Act, Article 27, Paragraph 1(d) specific risks of harm to affected persons"),
        ("article_27_1_e_human_oversight", e_present, e_refs,
         "Missing: EU AI Act, Article 27, Paragraph 1(e) human oversight measures"),
        ("article_27_1_f_if_materialised", f_present, f_refs,
         "Missing: EU AI Act, Article 27, Paragraph 1(f) measures if risks materialise"),
    ]

    coverage: dict[str, Any] = {}
    compliance_gap: list[str] = []
    warnings: list[str] = []
    total_present = 0
    total_missing = 0
    for key, present, refs, warning in elements:
        coverage[key] = {"present": present, "evidence_refs": refs}
        if present:
            total_present += 1
        else:
            total_missing += 1
            compliance_gap.append(key)
            warnings.append(warning)

    coverage["total_present"] = total_present
    coverage["total_missing"] = total_missing
    coverage["compliance_gap"] = compliance_gap
    coverage["warnings"] = warnings
    coverage["citation"] = "EU AI Act, Article 27, Paragraph 1"
    return coverage


def run_aisia(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Execute an AI System Impact Assessment per ISO/IEC 42001:2023 Clause 6.1.4
    and NIST AI RMF MAP subcategories, with optional crosswalk enrichment
    and EU AI Act Article 27 FRIA coverage verification.

    Args:
        inputs: Dict with:
            system_description: dict with system_name, purpose, and optional
                                fields (intended_use, decision_context,
                                deployment_environment, data_categories_processed,
                                decision_authority, reversibility, system_type,
                                process_description).
            affected_stakeholders: non-empty list of strings or dicts with 'name'.
            impact_assessments: list of dicts, each with at minimum
                                stakeholder_group, impact_dimension, and
                                optionally severity, likelihood, impact_description,
                                existing_controls, residual_severity,
                                residual_likelihood, additional_controls_recommended,
                                assessor, assessment_date, id, process_description.
            impact_dimensions: optional list; defaults to the standard five.
            risk_scoring_rubric: optional dict with severity_scale (or impact_scale)
                                 and likelihood_scale.
            soa_rows: optional list for cross-linking existing controls.
            framework: 'iso42001' (default), 'nist', or 'dual'.
            scaffold: bool (default False). Emit placeholder sections for
                      (stakeholder, dimension) pairs without assessments.
            reviewed_by: optional string.
            enrich_with_crosswalk: bool (default True). Attach cross_framework_coverage
                                   to each section by pulling ISO A.5.2/A.5.4/A.5.5
                                   anchor rows from crosswalk-matrix-builder.
            crosswalk_target_frameworks: list of target framework ids. Defaults
                                         to ["nist-ai-rmf", "eu-ai-act"].
            verify_eu_fria_coverage: bool (default True). Emit eu_fria_coverage
                                     checking Article 27(1)(a)-(f) element presence.
            assessment_period: optional string. Period for Art. 27(1)(b).
            frequency: optional string. Frequency for Art. 27(1)(b).
            affected_persons: optional structure. Complements affected_stakeholders
                              for Art. 27(1)(c).
            human_oversight: optional structure. Art. 27(1)(e) measures.
            mitigations: optional structure. Art. 27(1)(f) measures.
            risks_if_materialised: optional structure. Art. 27(1)(f) measures.

    Returns:
        Dict with timestamp, agent_signature, system_name, citations, sections,
        scaffold_sections, warnings, summary, reviewed_by. When enrichment
        ran, includes crosswalk_summary. When Art. 27 verification ran,
        includes eu_fria_coverage.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    system = inputs["system_description"]
    system_type = system.get("system_type")
    framework = inputs.get("framework", "iso42001")

    dimensions = tuple(inputs.get("impact_dimensions") or DEFAULT_IMPACT_DIMENSIONS)
    rubric = inputs.get("risk_scoring_rubric") or {
        "severity_scale": list(DEFAULT_SEVERITY_SCALE),
        "likelihood_scale": list(DEFAULT_LIKELIHOOD_SCALE),
    }
    severity_scale = tuple(rubric.get("severity_scale") or rubric.get("impact_scale"))
    likelihood_scale = tuple(rubric["likelihood_scale"])

    stakeholders_raw = inputs["affected_stakeholders"]
    stakeholder_names = {_stakeholder_name(s) for s in stakeholders_raw}
    stakeholders_detail = [s if isinstance(s, dict) else {"name": s} for s in stakeholders_raw]

    soa_rows_by_id = {r["control_id"]: r for r in (inputs.get("soa_rows") or []) if "control_id" in r}

    impact_assessments = inputs.get("impact_assessments") or []
    sections = [
        _enrich_section(entry, stakeholder_names, dimensions, severity_scale, likelihood_scale,
                        soa_rows_by_id, framework, i + 1, system_type)
        for i, entry in enumerate(impact_assessments)
    ]

    scaffold_sections: list[dict[str, str]] = []
    if inputs.get("scaffold"):
        covered = {(s["stakeholder_group"], s["impact_dimension"]) for s in sections}
        for stakeholder in stakeholder_names:
            for dim in dimensions:
                if (stakeholder, dim) not in covered:
                    scaffold_sections.append({
                        "stakeholder_group": stakeholder,
                        "impact_dimension": dim,
                        "placeholder_note": "No impact assessed for this pair. Document an assessment or explicit non-applicability.",
                    })

    register_warnings: list[str] = []
    if not sections:
        register_warnings.append(
            "No impact assessments provided. An empty AISIA is not audit-acceptable; "
            "assess impacts per Clause 6.1.4 and supply impact_assessments."
        )
    if framework in ("iso42001", "dual"):
        top_citations = [
            "ISO/IEC 42001:2023, Clause 6.1.4",
            "ISO/IEC 42001:2023, Annex A, Control A.5.2",
            "ISO/IEC 42001:2023, Annex A, Control A.5.3",
            "ISO/IEC 42001:2023, Annex A, Control A.5.4",
            "ISO/IEC 42001:2023, Annex A, Control A.5.5",
        ]
    else:
        top_citations = []
    if framework in ("nist", "dual"):
        top_citations.extend(["MAP 1.1", "MAP 3.1", "MAP 3.2", "MAP 5.1"])

    # Optional crosswalk enrichment (opt-out, default on).
    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True
    target_frameworks = list(
        inputs.get("crosswalk_target_frameworks") or DEFAULT_CROSSWALK_TARGET_FRAMEWORKS
    )

    crosswalk_summary: dict[str, Any] | None = None
    if enrich:
        crosswalk_warnings, counts = _enrich_sections_with_crosswalk(sections, target_frameworks)
        register_warnings.extend(crosswalk_warnings)
        crosswalk_summary = {
            "target_frameworks": target_frameworks,
            "sections_with_coverage": counts["sections_with_coverage"],
            "sections_without_coverage": counts["sections_without_coverage"],
            "total_mappings_included": counts["total_mappings_included"],
        }

    # Optional EU AI Act Article 27 FRIA coverage verification.
    verify_fria = inputs.get("verify_eu_fria_coverage")
    if verify_fria is None:
        verify_fria = True

    eu_fria_coverage: dict[str, Any] | None = None
    if verify_fria:
        eu_fria_coverage = _verify_eu_fria_coverage(inputs, sections)

    summary = {
        "total_sections": len(sections),
        "stakeholders_covered": len({s["stakeholder_group"] for s in sections}),
        "dimensions_covered": len({s["impact_dimension"] for s in sections}),
        "sections_with_warnings": sum(1 for s in sections if s["warnings"]),
        "scaffold_count": len(scaffold_sections),
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "system_name": system["system_name"],
        "system_type": system_type,
        "framework": framework,
        "citations": top_citations,
        "stakeholders": stakeholders_detail,
        "dimensions": list(dimensions),
        "sections": sections,
        "scaffold_sections": scaffold_sections,
        "warnings": register_warnings,
        "summary": summary,
        "reviewed_by": inputs.get("reviewed_by"),
    }
    if crosswalk_summary is not None:
        output["crosswalk_summary"] = crosswalk_summary
    if eu_fria_coverage is not None:
        output["eu_fria_coverage"] = eu_fria_coverage
    return output


def render_markdown(aisia: dict[str, Any]) -> str:
    """Render an AISIA as a Markdown document."""
    required = ("timestamp", "agent_signature", "system_name", "citations", "sections", "summary")
    missing = [k for k in required if k not in aisia]
    if missing:
        raise ValueError(f"aisia missing required fields: {missing}")

    lines = [
        f"# AI System Impact Assessment: {aisia['system_name']}",
        "",
        f"**Generated at (UTC):** {aisia['timestamp']}",
        f"**Generated by:** {aisia['agent_signature']}",
        f"**Framework rendering:** {aisia.get('framework', 'iso42001')}",
    ]
    if aisia.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {aisia['reviewed_by']}")
    summary = aisia["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Total sections: {summary['total_sections']}",
        f"- Stakeholders covered: {summary['stakeholders_covered']}",
        f"- Dimensions covered: {summary['dimensions_covered']}",
        f"- Sections with warnings: {summary['sections_with_warnings']}",
        f"- Scaffold placeholders: {summary['scaffold_count']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in aisia["citations"]:
        lines.append(f"- {c}")
    lines.extend(["", "## Sections", ""])
    if not aisia["sections"]:
        lines.append("_No impact sections recorded._")
    for section in aisia["sections"]:
        lines.extend([
            f"### {section['id']}: {section['stakeholder_group']} / {section['impact_dimension']}",
            "",
            f"**Severity:** {section.get('severity') or 'not set'}",
            f"**Likelihood:** {section.get('likelihood') or 'not set'}",
            f"**Residual severity:** {section.get('residual_severity') or 'not set'}",
            f"**Residual likelihood:** {section.get('residual_likelihood') or 'not set'}",
            "",
            "**Impact description:**",
            "",
            section.get("impact_description") or "_(not populated)_",
            "",
        ])
        if section["existing_controls"]:
            lines.append("**Existing controls:**")
            lines.append("")
            for ctrl in section["existing_controls"]:
                soa = f" [SoA: {ctrl['soa_row_ref']}]" if ctrl.get("soa_row_ref") else ""
                lines.append(f"- {ctrl['control_id']}{soa}: {ctrl.get('description') or ''}")
            lines.append("")
        if section["additional_controls_recommended"]:
            lines.append("**Additional controls recommended:**")
            lines.append("")
            for ctrl in section["additional_controls_recommended"]:
                lines.append(f"- {ctrl}")
            lines.append("")
        lines.append("**Citations:**")
        lines.append("")
        for c in section["citations"]:
            lines.append(f"- {c}")
        if "cross_framework_coverage" in section:
            coverage = section.get("cross_framework_coverage") or []
            lines.append("")
            lines.append("**Cross-framework coverage:**")
            lines.append("")
            if not coverage:
                lines.append("- (no cross-framework coverage)")
            else:
                for entry in coverage:
                    conf = entry.get("confidence") or ""
                    badge = f"[{conf}]" if conf else ""
                    lines.append(
                        f"- {entry.get('target_framework')} -> {entry.get('target_ref')} "
                        f"({entry.get('relationship')}) {badge}".rstrip()
                    )
        if section["warnings"]:
            lines.append("")
            lines.append("**Warnings:**")
            lines.append("")
            for w in section["warnings"]:
                lines.append(f"- {w}")
        lines.append("")

    if aisia.get("crosswalk_summary"):
        cs = aisia["crosswalk_summary"]
        lines.extend([
            "## Crosswalk summary",
            "",
            f"- target_frameworks: {', '.join(cs.get('target_frameworks', []))}",
            f"- sections_with_coverage: {cs.get('sections_with_coverage', 0)}",
            f"- sections_without_coverage: {cs.get('sections_without_coverage', 0)}",
            f"- total_mappings_included: {cs.get('total_mappings_included', 0)}",
            "",
        ])

    fria = aisia.get("eu_fria_coverage")
    if fria is not None:
        lines.extend([
            "## EU AI Act Article 27 FRIA coverage",
            "",
            f"- Citation: {fria.get('citation', 'EU AI Act, Article 27, Paragraph 1')}",
            f"- Total present: {fria.get('total_present', 0)}",
            f"- Total missing: {fria.get('total_missing', 0)}",
            "",
            "| Element | Present | Evidence refs |",
            "|---|---|---|",
        ])
        element_order = [
            ("article_27_1_a_process_description", "Article 27(1)(a) process description"),
            ("article_27_1_b_period_frequency", "Article 27(1)(b) period or frequency"),
            ("article_27_1_c_affected_persons", "Article 27(1)(c) affected persons"),
            ("article_27_1_d_harms", "Article 27(1)(d) specific risks of harm"),
            ("article_27_1_e_human_oversight", "Article 27(1)(e) human oversight"),
            ("article_27_1_f_if_materialised", "Article 27(1)(f) measures if risks materialise"),
        ]
        for key, label in element_order:
            entry = fria.get(key) or {}
            present = entry.get("present", False)
            marker = "present" if present else "missing"
            refs = ", ".join(entry.get("evidence_refs") or []) or "(none)"
            lines.append(f"| {label} | {marker} | {refs} |")
        gap = fria.get("compliance_gap") or []
        if gap:
            lines.extend(["", "### Compliance gap", ""])
            for g in gap:
                lines.append(f"- {g}")
        fria_warnings = fria.get("warnings") or []
        if fria_warnings:
            lines.extend(["", "### FRIA warnings", ""])
            for w in fria_warnings:
                lines.append(f"- {w}")
        lines.append("")

    if aisia.get("scaffold_sections"):
        lines.extend(["## Coverage gaps", ""])
        for scaf in aisia["scaffold_sections"]:
            lines.append(f"- {scaf['stakeholder_group']} / {scaf['impact_dimension']}: {scaf['placeholder_note']}")

    if aisia.get("warnings"):
        lines.extend(["", "## Document-level warnings", ""])
        for w in aisia["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)
