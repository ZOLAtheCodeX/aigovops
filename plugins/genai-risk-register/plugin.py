"""
AIGovOps: GenAI Risk Register Plugin

Operationalizes the NIST AI 600-1 (July 2024) Generative AI Profile's 12-risk
catalogue as a dedicated GenAI risk register. Distinct from the general-
purpose `risk-register-builder` plugin, which operates over ISO 42001 / NIST
AI RMF taxonomies. This plugin applies only to generative AI systems and
cross-maps each risk to the AI RMF subcategories named in NIST AI 600-1
Appendix A, plus jurisdiction-specific obligations in the EU AI Act
(Articles 50 and 55) and California statutes (SB 942, AB 2013, AB 1008).

Design stance. The plugin does NOT invent risk evaluations. The practitioner
supplies a likelihood, impact, and existing-mitigations record per risk.
The plugin validates the 12-risk coverage, computes per-risk cross-
references, flags residual-risk logic errors, escalates high-residual
rows, and emits the artifact as JSON, Markdown, and CSV. The `is_generative`
guard in `system_description` is load-bearing: non-generative systems must
use `risk-register-builder`.

Status. 0.1.0.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "genai-risk-register/0.1.0"

REQUIRED_INPUT_FIELDS = ("system_description", "risk_evaluations")

GENAI_RISKS = (
    "cbrn-information-capabilities",
    "confabulation",
    "dangerous-violent-hateful-content",
    "data-privacy",
    "environmental-impacts",
    "harmful-bias-homogenization",
    "human-ai-configuration",
    "information-integrity",
    "information-security",
    "intellectual-property",
    "obscene-degrading-abusive-content",
    "value-chain-component-integration",
)

VALID_MITIGATION_STATUSES = (
    "implemented",
    "planned",
    "partial",
    "not-addressed",
    "not-applicable",
)

VALID_LIKELIHOOD = ("rare", "unlikely", "possible", "likely", "almost-certain")
VALID_IMPACT = ("negligible", "minor", "moderate", "major", "catastrophic")

# NIST AI 600-1 Appendix A subcategory mapping per GenAI risk.
RISK_TO_NIST_SUBCATEGORIES: dict[str, tuple[str, ...]] = {
    "cbrn-information-capabilities": ("GOVERN 1.1", "MAP 1.1", "MEASURE 2.6"),
    "confabulation": ("MEASURE 2.5", "MEASURE 2.8"),
    "dangerous-violent-hateful-content": ("MAP 5.1", "MANAGE 2.2"),
    "data-privacy": ("MEASURE 2.10",),
    "environmental-impacts": ("MEASURE 2.12",),
    "harmful-bias-homogenization": ("MEASURE 2.11",),
    "human-ai-configuration": ("MANAGE 2.3", "MEASURE 3.3"),
    "information-integrity": ("MEASURE 2.7", "MEASURE 2.8"),
    "information-security": ("MEASURE 2.7",),
    "intellectual-property": ("GOVERN 1.4", "GOVERN 6.1"),
    "obscene-degrading-abusive-content": ("MAP 5.1", "MANAGE 2.2"),
    "value-chain-component-integration": ("GOVERN 6.1", "GOVERN 6.2"),
}

# Which risks trigger EU AI Act systemic-risk supplementary citations when
# jurisdiction = eu AND gpai_obligations_ref is present.
SYSTEMIC_RISK_RELEVANT_RISKS = ("information-security", "value-chain-component-integration")

# Sibling-plugin path for crosswalk-matrix-builder.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _score_index(value: str, scale: tuple[str, ...]) -> int | None:
    try:
        return scale.index(value) + 1
    except ValueError:
        return None


def _compute_score(likelihood: str | None, impact: str | None) -> int | None:
    if likelihood is None or impact is None:
        return None
    li = _score_index(likelihood, VALID_LIKELIHOOD)
    ii = _score_index(impact, VALID_IMPACT)
    if li is None or ii is None:
        return None
    return li * ii


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    sd = inputs["system_description"]
    if not isinstance(sd, dict):
        raise ValueError("system_description must be a dict")
    if sd.get("is_generative") is not True:
        raise ValueError(
            "GenAI risk register only applies to generative AI systems. "
            "For non-generative AI, use the general risk-register-builder plugin."
        )

    risks = inputs["risk_evaluations"]
    if not isinstance(risks, list):
        raise ValueError("risk_evaluations must be a list")

    for idx, entry in enumerate(risks):
        if not isinstance(entry, dict):
            raise ValueError(f"risk_evaluations[{idx}] must be a dict")
        rid = entry.get("risk_id")
        if rid not in GENAI_RISKS:
            raise ValueError(
                f"risk_evaluations[{idx}].risk_id must be one of {GENAI_RISKS}; got {rid!r}"
            )
        likelihood = entry.get("likelihood")
        if likelihood is not None and likelihood not in VALID_LIKELIHOOD:
            raise ValueError(
                f"risk_evaluations[{idx}].likelihood must be one of {VALID_LIKELIHOOD}; got {likelihood!r}"
            )
        impact = entry.get("impact")
        if impact is not None and impact not in VALID_IMPACT:
            raise ValueError(
                f"risk_evaluations[{idx}].impact must be one of {VALID_IMPACT}; got {impact!r}"
            )
        resid_likelihood = entry.get("residual_likelihood")
        if resid_likelihood is not None and resid_likelihood not in VALID_LIKELIHOOD:
            raise ValueError(
                f"risk_evaluations[{idx}].residual_likelihood must be one of {VALID_LIKELIHOOD}; got {resid_likelihood!r}"
            )
        resid_impact = entry.get("residual_impact")
        if resid_impact is not None and resid_impact not in VALID_IMPACT:
            raise ValueError(
                f"risk_evaluations[{idx}].residual_impact must be one of {VALID_IMPACT}; got {resid_impact!r}"
            )
        mit_status = entry.get("mitigation_status")
        if mit_status is not None and mit_status not in VALID_MITIGATION_STATUSES:
            raise ValueError(
                f"risk_evaluations[{idx}].mitigation_status must be one of {VALID_MITIGATION_STATUSES}; got {mit_status!r}"
            )

    not_applicable = inputs.get("risks_not_applicable") or []
    if not isinstance(not_applicable, list):
        raise ValueError("risks_not_applicable, when provided, must be a list of dicts")
    for idx, entry in enumerate(not_applicable):
        if not isinstance(entry, dict):
            raise ValueError(f"risks_not_applicable[{idx}] must be a dict with risk_id and rationale")
        rid = entry.get("risk_id")
        if rid not in GENAI_RISKS:
            raise ValueError(
                f"risks_not_applicable[{idx}].risk_id must be one of {GENAI_RISKS}; got {rid!r}"
            )

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")

    cross_refs = inputs.get("cross_reference_refs")
    if cross_refs is not None and not isinstance(cross_refs, dict):
        raise ValueError("cross_reference_refs, when provided, must be a dict")


def _risk_citations(
    risk_id: str,
    jurisdiction: list[str],
    cross_refs: dict[str, Any],
) -> list[str]:
    citations: list[str] = [
        "NIST AI 600-1, Section 2",
        "NIST AI 600-1, Appendix A",
    ]
    for sub in RISK_TO_NIST_SUBCATEGORIES.get(risk_id, ()):
        citations.append(f"NIST AI RMF, {sub}")

    jset = {j.lower() for j in jurisdiction}
    gpai_ref = bool(cross_refs.get("gpai_obligations_ref"))

    if "eu" in jset:
        if risk_id == "information-integrity":
            citations.append("EU AI Act, Article 50, Paragraph 2")
            citations.append("EU AI Act, Article 50, Paragraph 4")
        if gpai_ref and risk_id in SYSTEMIC_RISK_RELEVANT_RISKS:
            if risk_id == "information-security":
                citations.append("EU AI Act, Article 55, Paragraph 1, Point (a)")
            if risk_id == "value-chain-component-integration":
                citations.append("EU AI Act, Article 55, Paragraph 1, Point (d)")

    if "usa-ca" in jset:
        if risk_id == "information-integrity":
            citations.append("Cal. Bus. & Prof. Code Section 22757")
        if risk_id == "data-privacy":
            citations.append("California AB 2013, Section 1")
            citations.append("Cal. Civ. Code Section 1798.140(v)")
        if risk_id == "intellectual-property":
            citations.append("California AB 2013, Section 1")

    return citations


def _normalize_risk_row(
    entry: dict[str, Any],
    jurisdiction: list[str],
    cross_refs: dict[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []
    rid = entry["risk_id"]
    likelihood = entry.get("likelihood")
    impact = entry.get("impact")
    residual_likelihood = entry.get("residual_likelihood")
    residual_impact = entry.get("residual_impact")

    inherent_score = entry.get("inherent_score")
    if inherent_score is None:
        inherent_score = _compute_score(likelihood, impact)
    residual_score = entry.get("residual_score")
    if residual_score is None:
        residual_score = _compute_score(residual_likelihood, residual_impact)

    if likelihood is None or impact is None:
        warnings.append(
            f"risk {rid!r} missing likelihood or impact; inherent_score cannot be computed."
        )

    mitigation_status = entry.get("mitigation_status")
    if mitigation_status is None:
        warnings.append(f"risk {rid!r} has no mitigation_status; set one of {VALID_MITIGATION_STATUSES}.")

    if (
        inherent_score is not None
        and residual_score is not None
        and residual_score > inherent_score
    ):
        warnings.append(
            f"risk {rid!r} residual_score ({residual_score}) exceeds inherent_score ({inherent_score}); "
            "check mitigation logic."
        )

    if (
        mitigation_status == "implemented"
        and inherent_score is not None
        and residual_score is not None
        and residual_score == inherent_score
    ):
        warnings.append(
            f"risk {rid!r} mitigation_status is 'implemented' but residual_score equals inherent_score; "
            "implemented mitigation should lower residual risk."
        )

    if entry.get("owner_role") is None:
        warnings.append(f"risk {rid!r} has no owner_role; every evaluated risk must have an assigned owner.")

    citations = _risk_citations(rid, jurisdiction, cross_refs)
    nist_subcategories = list(RISK_TO_NIST_SUBCATEGORIES.get(rid, ()))

    row = {
        "risk_id": rid,
        "likelihood": likelihood,
        "impact": impact,
        "inherent_score": inherent_score,
        "existing_mitigations": list(entry.get("existing_mitigations") or []),
        "mitigation_status": mitigation_status,
        "residual_likelihood": residual_likelihood,
        "residual_impact": residual_impact,
        "residual_score": residual_score,
        "owner_role": entry.get("owner_role"),
        "review_date": entry.get("review_date"),
        "notes": entry.get("notes"),
        "nist_subcategory_refs": nist_subcategories,
        "citations": citations,
        "warnings": warnings,
    }
    return row


def _coverage_assessment(
    evaluated_ids: set[str],
    not_applicable: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    na_ids = set()
    na_records: list[dict[str, Any]] = []
    for entry in not_applicable:
        rid = entry["risk_id"]
        rationale = entry.get("rationale")
        if not rationale or not str(rationale).strip():
            warnings.append(
                f"risk {rid!r} marked not-applicable without rationale; "
                "provide a rationale documenting why the risk does not apply."
            )
        na_ids.add(rid)
        na_records.append({"risk_id": rid, "rationale": rationale})

    missing = []
    for rid in GENAI_RISKS:
        if rid not in evaluated_ids and rid not in na_ids:
            missing.append(rid)
            warnings.append(
                f"NIST AI 600-1 risk {rid!r} not evaluated; "
                "either evaluate or mark not-applicable with rationale."
            )

    assessment = {
        "expected_total": len(GENAI_RISKS),
        "evaluated_count": len(evaluated_ids),
        "not_applicable_count": len(na_ids),
        "missing_count": len(missing),
        "missing_risk_ids": missing,
        "not_applicable": na_records,
    }
    return assessment, warnings


def _residual_risk_flags(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    flags: list[dict[str, Any]] = []
    warnings: list[str] = []
    for row in rows:
        rs = row.get("residual_score")
        if rs is not None and rs >= 15:
            flag = {
                "risk_id": row["risk_id"],
                "residual_score": rs,
                "severity": "critical",
                "escalation": "incident-reporting + management-review",
                "recommendation": (
                    "Residual score >= 15 on the 5x5 scale. Escalate to the management-review-packager for "
                    "documented review and stage an incident-reporting draft in case the risk materializes."
                ),
            }
            flags.append(flag)
            warnings.append(
                f"CRITICAL: risk {row['risk_id']!r} residual_score {rs} >= 15; escalate to "
                "incident-reporting and management-review."
            )
    return flags, warnings


def _version_diff(
    current_rows: list[dict[str, Any]],
    previous_ref: Any,
) -> dict[str, Any]:
    """Compute a best-effort diff when a previous register is supplied.

    previous_ref may be either a register dict with 'risk_evaluations_normalized'
    or a list of previous evaluated rows. Missing structure results in an empty
    diff with a note.
    """
    previous_rows: list[dict[str, Any]] = []
    if isinstance(previous_ref, dict):
        previous_rows = list(previous_ref.get("risk_evaluations_normalized") or [])
    elif isinstance(previous_ref, list):
        previous_rows = list(previous_ref)

    prev_by_id = {r.get("risk_id"): r for r in previous_rows if isinstance(r, dict)}
    curr_by_id = {r["risk_id"]: r for r in current_rows}

    added = [rid for rid in curr_by_id if rid not in prev_by_id]
    closed = [rid for rid in prev_by_id if rid not in curr_by_id]
    changed: list[dict[str, Any]] = []
    for rid, curr in curr_by_id.items():
        prev = prev_by_id.get(rid)
        if not prev:
            continue
        prev_res = prev.get("residual_score")
        curr_res = curr.get("residual_score")
        prev_inh = prev.get("inherent_score")
        curr_inh = curr.get("inherent_score")
        if prev_res != curr_res or prev_inh != curr_inh:
            changed.append({
                "risk_id": rid,
                "inherent_score_from": prev_inh,
                "inherent_score_to": curr_inh,
                "residual_score_from": prev_res,
                "residual_score_to": curr_res,
            })

    return {
        "added": added,
        "closed": closed,
        "changed": changed,
    }


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_genai_risk", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enrich_crosswalk(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Filter crosswalk mappings whose source_ref names a NIST subcategory
    referenced by any evaluated risk. Return (cross_framework_citations, warnings).
    Graceful on crosswalk failure: returns empty list plus a warning.
    """
    try:
        crosswalk = _load_crosswalk_module()
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return ([], [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"])

    wanted_subcategories: set[str] = set()
    for row in rows:
        for sub in row.get("nist_subcategory_refs") or []:
            wanted_subcategories.add(sub)

    filtered: list[dict[str, Any]] = []
    for m in data.get("mappings", []):
        src_fw = m.get("source_framework")
        src_ref = str(m.get("source_ref") or "")
        tgt_fw = m.get("target_framework")
        tgt_ref = str(m.get("target_ref") or "")
        if src_fw == "nist-ai-rmf" and src_ref in wanted_subcategories:
            filtered.append({
                "source_framework": src_fw,
                "source_ref": src_ref,
                "target_framework": tgt_fw,
                "target_ref": tgt_ref,
                "relationship": m.get("relationship"),
                "confidence": m.get("confidence"),
            })
        elif tgt_fw == "nist-ai-rmf" and tgt_ref in wanted_subcategories:
            filtered.append({
                "source_framework": src_fw,
                "source_ref": src_ref,
                "target_framework": tgt_fw,
                "target_ref": tgt_ref,
                "relationship": m.get("relationship"),
                "confidence": m.get("confidence"),
            })
    return (filtered, [])


def generate_genai_risk_register(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a NIST AI 600-1 GenAI risk register.

    Args:
        inputs: Dict with:
            system_description: dict (required) describing the generative AI
                system. Must include ``is_generative = True``. Other fields:
                system_id, model_type, modality, training_data_scope,
                deployment_context, jurisdiction (list of lowercase codes,
                e.g. ['eu', 'usa-ca']), base_model_ref.
            risk_evaluations: list (required) of per-risk dicts. See README
                and `GENAI_RISKS` for risk_id enum.
            risks_not_applicable: optional list of {risk_id, rationale}.
            cross_reference_refs: optional dict with gpai_obligations_ref,
                supplier_assessment_ref, bias_evaluation_ref.
            previous_register_ref: optional previous register dict or list
                for version diff.
            enrich_with_crosswalk: bool (default True).
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, framework, system_description_echo,
        risk_evaluations_normalized, coverage_assessment, per_risk_nist_coverage,
        jurisdiction_cross_references, residual_risk_flags, version_diff
        (when previous_register_ref supplied), citations, warnings, summary,
        cross_framework_citations (when enriched), reviewed_by.

    Raises:
        ValueError: on missing or malformed required inputs, including
            is_generative != True.
    """
    _validate(inputs)

    system_description = inputs["system_description"]
    jurisdiction = list(system_description.get("jurisdiction") or [])
    cross_refs = dict(inputs.get("cross_reference_refs") or {})

    warnings: list[str] = []

    normalized_rows: list[dict[str, Any]] = []
    evaluated_ids: set[str] = set()
    for entry in inputs["risk_evaluations"]:
        row = _normalize_risk_row(entry, jurisdiction, cross_refs)
        normalized_rows.append(row)
        evaluated_ids.add(row["risk_id"])
        warnings.extend(row["warnings"])

    not_applicable = list(inputs.get("risks_not_applicable") or [])
    coverage_assessment, coverage_warnings = _coverage_assessment(evaluated_ids, not_applicable)
    warnings.extend(coverage_warnings)

    per_risk_nist_coverage = {
        row["risk_id"]: row["nist_subcategory_refs"] for row in normalized_rows
    }

    # Jurisdiction cross-references summary (per-risk citations already on rows;
    # this section aggregates for dashboard rendering).
    jurisdiction_cross_references: dict[str, list[str]] = {}
    jset = {j.lower() for j in jurisdiction}
    if "eu" in jset:
        jurisdiction_cross_references["eu"] = [
            "EU AI Act, Article 50, Paragraph 2",
            "EU AI Act, Article 50, Paragraph 4",
        ]
        if cross_refs.get("gpai_obligations_ref"):
            jurisdiction_cross_references["eu"].extend([
                "EU AI Act, Article 55, Paragraph 1, Point (a)",
                "EU AI Act, Article 55, Paragraph 1, Point (d)",
            ])
    if "usa-ca" in jset:
        jurisdiction_cross_references["usa-ca"] = [
            "Cal. Bus. & Prof. Code Section 22757",
            "California AB 2013, Section 1",
            "Cal. Civ. Code Section 1798.140(v)",
        ]

    residual_flags, flag_warnings = _residual_risk_flags(normalized_rows)
    warnings.extend(flag_warnings)

    previous_ref = inputs.get("previous_register_ref")
    version_diff: dict[str, Any] | None = None
    if previous_ref is not None:
        version_diff = _version_diff(normalized_rows, previous_ref)

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True
    cross_framework_citations: list[dict[str, Any]] | None = None
    if enrich:
        cross_framework_citations, enrich_warnings = _enrich_crosswalk(normalized_rows)
        warnings.extend(enrich_warnings)

    citations: list[str] = [
        "NIST AI 600-1, Section 2",
        "NIST AI 600-1, Appendix A",
    ]
    for row in normalized_rows:
        for c in row["citations"]:
            if c not in citations:
                citations.append(c)

    summary = {
        "evaluated_count": coverage_assessment["evaluated_count"],
        "expected_total": coverage_assessment["expected_total"],
        "not_applicable_count": coverage_assessment["not_applicable_count"],
        "missing_count": coverage_assessment["missing_count"],
        "rows_with_warnings": sum(1 for r in normalized_rows if r["warnings"]),
        "critical_flag_count": len(residual_flags),
    }

    system_description_echo = {
        "system_id": system_description.get("system_id"),
        "model_type": system_description.get("model_type"),
        "modality": system_description.get("modality"),
        "is_generative": system_description.get("is_generative"),
        "training_data_scope": system_description.get("training_data_scope"),
        "deployment_context": system_description.get("deployment_context"),
        "jurisdiction": jurisdiction,
        "base_model_ref": system_description.get("base_model_ref"),
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "nist,eu-ai-act,usa-ca",
        "system_description_echo": system_description_echo,
        "risk_evaluations_normalized": normalized_rows,
        "coverage_assessment": coverage_assessment,
        "per_risk_nist_coverage": per_risk_nist_coverage,
        "jurisdiction_cross_references": jurisdiction_cross_references,
        "residual_risk_flags": residual_flags,
        "citations": citations,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": inputs.get("reviewed_by"),
    }
    if version_diff is not None:
        output["version_diff"] = version_diff
    if cross_framework_citations is not None:
        output["cross_framework_citations"] = cross_framework_citations
    return output


def render_markdown(register: dict[str, Any]) -> str:
    """Render a GenAI risk register as Markdown."""
    required = (
        "timestamp",
        "agent_signature",
        "system_description_echo",
        "risk_evaluations_normalized",
        "coverage_assessment",
        "per_risk_nist_coverage",
        "jurisdiction_cross_references",
        "residual_risk_flags",
        "citations",
        "warnings",
        "summary",
    )
    missing = [k for k in required if k not in register]
    if missing:
        raise ValueError(f"register missing required fields: {missing}")

    sd = register["system_description_echo"]
    summary = register["summary"]
    coverage = register["coverage_assessment"]

    lines = [
        "# GenAI Risk Register",
        "",
        f"**Generated at (UTC):** {register['timestamp']}",
        f"**Generated by:** {register['agent_signature']}",
        f"**Framework:** {register.get('framework')}",
    ]
    if register.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {register['reviewed_by']}")

    lines.extend([
        "",
        "## System description",
        "",
        f"- system_id: {sd.get('system_id') or ''}",
        f"- model_type: {sd.get('model_type') or ''}",
        f"- modality: {sd.get('modality') or ''}",
        f"- is_generative: {sd.get('is_generative')}",
        f"- training_data_scope: {sd.get('training_data_scope') or ''}",
        f"- deployment_context: {sd.get('deployment_context') or ''}",
        f"- jurisdiction: {', '.join(sd.get('jurisdiction') or []) or ''}",
        f"- base_model_ref: {sd.get('base_model_ref') or ''}",
        "",
        "## Coverage assessment",
        "",
        f"- expected_total: {coverage['expected_total']}",
        f"- evaluated_count: {coverage['evaluated_count']}",
        f"- not_applicable_count: {coverage['not_applicable_count']}",
        f"- missing_count: {coverage['missing_count']}",
    ])
    if coverage["missing_risk_ids"]:
        lines.append(f"- missing_risk_ids: {', '.join(coverage['missing_risk_ids'])}")
    if coverage["not_applicable"]:
        lines.extend(["", "### Risks marked not-applicable", ""])
        for entry in coverage["not_applicable"]:
            lines.append(f"- {entry['risk_id']}: {entry.get('rationale') or '(no rationale)'}")

    lines.extend([
        "",
        "## Per-risk evaluations",
        "",
        "| Risk | Inherent | Residual | Mitigation | Owner | NIST subcategories |",
        "|---|---|---|---|---|---|",
    ])
    for row in register["risk_evaluations_normalized"]:
        subs = "; ".join(row.get("nist_subcategory_refs") or [])
        lines.append(
            f"| {row['risk_id']} | {row.get('inherent_score') or ''} | "
            f"{row.get('residual_score') or ''} | {row.get('mitigation_status') or ''} | "
            f"{row.get('owner_role') or ''} | {subs} |"
        )

    lines.extend(["", "## Jurisdiction cross-references", ""])
    jxref = register["jurisdiction_cross_references"]
    if not jxref:
        lines.append("_No jurisdiction-specific cross-references apply._")
    else:
        for jur, refs in jxref.items():
            lines.append(f"### {jur}")
            lines.append("")
            for ref in refs:
                lines.append(f"- {ref}")
            lines.append("")

    lines.extend(["", "## Residual risk flags", ""])
    if register["residual_risk_flags"]:
        lines.append("| Risk | Residual score | Severity | Escalation |")
        lines.append("|---|---|---|---|")
        for flag in register["residual_risk_flags"]:
            lines.append(
                f"| {flag['risk_id']} | {flag['residual_score']} | "
                f"{flag['severity']} | {flag['escalation']} |"
            )
    else:
        lines.append("_No critical residual risk flags._")

    if "version_diff" in register:
        vd = register["version_diff"]
        lines.extend(["", "## Version diff", ""])
        lines.append(f"- added: {', '.join(vd.get('added') or []) or 'none'}")
        lines.append(f"- closed: {', '.join(vd.get('closed') or []) or 'none'}")
        if vd.get("changed"):
            lines.extend(["", "### Changed scores", "",
                          "| Risk | Inherent from | Inherent to | Residual from | Residual to |",
                          "|---|---|---|---|---|"])
            for ch in vd["changed"]:
                lines.append(
                    f"| {ch['risk_id']} | {ch['inherent_score_from']} | {ch['inherent_score_to']} | "
                    f"{ch['residual_score_from']} | {ch['residual_score_to']} |"
                )

    lines.extend(["", "## Applicable citations", ""])
    for c in register["citations"]:
        lines.append(f"- {c}")

    if register.get("cross_framework_citations"):
        lines.extend(["", "## Cross-framework citations", ""])
        for entry in register["cross_framework_citations"]:
            lines.append(
                f"- {entry.get('source_framework')} {entry.get('source_ref')} -> "
                f"{entry.get('target_framework')} {entry.get('target_ref')} "
                f"({entry.get('relationship')}, {entry.get('confidence')})"
            )

    lines.extend(["", "## Warnings", ""])
    if register["warnings"]:
        for w in register["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("_No warnings._")

    lines.extend([
        "",
        "## Summary",
        "",
        f"- evaluated_count: {summary['evaluated_count']}",
        f"- expected_total: {summary['expected_total']}",
        f"- not_applicable_count: {summary['not_applicable_count']}",
        f"- missing_count: {summary['missing_count']}",
        f"- rows_with_warnings: {summary['rows_with_warnings']}",
        f"- critical_flag_count: {summary['critical_flag_count']}",
        "",
    ])
    return "\n".join(lines)


def render_csv(register: dict[str, Any]) -> str:
    """Render a GenAI risk register as CSV. One row per evaluated risk.

    Columns: risk_id, likelihood, impact, inherent_score, mitigation_status,
    residual_likelihood, residual_impact, residual_score, owner_role,
    review_date, nist_subcategory_refs, citations.
    """
    if "risk_evaluations_normalized" not in register:
        raise ValueError("register missing 'risk_evaluations_normalized' field")
    header = ",".join([
        "risk_id",
        "likelihood",
        "impact",
        "inherent_score",
        "mitigation_status",
        "residual_likelihood",
        "residual_impact",
        "residual_score",
        "owner_role",
        "review_date",
        "nist_subcategory_refs",
        "citations",
    ])
    lines = [header]
    for row in register["risk_evaluations_normalized"]:
        fields = [
            _csv_escape(str(row.get("risk_id", ""))),
            _csv_escape(str(row.get("likelihood") or "")),
            _csv_escape(str(row.get("impact") or "")),
            _csv_escape(str(row.get("inherent_score") or "")),
            _csv_escape(str(row.get("mitigation_status") or "")),
            _csv_escape(str(row.get("residual_likelihood") or "")),
            _csv_escape(str(row.get("residual_impact") or "")),
            _csv_escape(str(row.get("residual_score") or "")),
            _csv_escape(str(row.get("owner_role") or "")),
            _csv_escape(str(row.get("review_date") or "")),
            _csv_escape("; ".join(row.get("nist_subcategory_refs") or [])),
            _csv_escape("; ".join(row.get("citations") or [])),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
