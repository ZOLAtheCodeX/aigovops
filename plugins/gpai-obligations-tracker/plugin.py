"""
AIGovOps: GPAI Obligations Tracker Plugin

Operationalizes EU AI Act Articles 51 to 55 (general-purpose AI models, GPAI).
Distinguishes the universal Article 53 obligations that attach to every GPAI
provider from the additional Article 55 obligations that attach only when a
GPAI model has systemic risk under Article 51. Wires the Article 54
authorised-representative check for non-EU providers and emits a downstream
integrator posture for organisations integrating an upstream GPAI without
meeting the substantial-modification re-classification threshold of
Article 25(1)(c).

Design stance. The plugin does NOT compute training compute, does NOT verify
external documentation URLs, and does NOT make the legal determination that a
copyright policy or training-data summary is adequate. It validates inputs,
applies deterministic rules over the GPAI obligation surface, attaches
citations, and surfaces gaps as warnings for practitioner action.

Status. Phase 4 implementation. 0.1.0.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "gpai-obligations-tracker/0.1.0"

REQUIRED_INPUT_FIELDS = ("model_description", "provider_role")

VALID_PROVIDER_ROLES = (
    "eu-established-provider",
    "non-eu-provider-with-representative",
    "non-eu-provider-without-representative",
    "downstream-integrator",
)

VALID_SYSTEMIC_RISK_STATUS = (
    "presumed-systemic-risk",
    "designated-systemic-risk",
    "not-systemic-risk",
    "requires-assessment",
)

# Article 51(2) presumption threshold for high-impact capability: cumulative
# compute used for training greater than 10^25 floating-point operations.
SYSTEMIC_RISK_COMPUTE_THRESHOLD_FLOPS = 10 ** 25

CODE_OF_PRACTICE_ENUM = (
    "signed-full",
    "signed-partial",
    "not-signed",
    "not-applicable",
)

REQUIRED_MODEL_DESCRIPTION_FIELDS = ("model_name",)

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily inside
# the enrichment helper so the plugin pays no import cost when crosswalk
# enrichment is disabled.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    model_description = inputs["model_description"]
    if not isinstance(model_description, dict):
        raise ValueError("model_description must be a dict")
    for req in REQUIRED_MODEL_DESCRIPTION_FIELDS:
        if req not in model_description or not model_description[req]:
            raise ValueError(f"model_description missing required field {req!r}")

    provider_role = inputs["provider_role"]
    if provider_role not in VALID_PROVIDER_ROLES:
        raise ValueError(
            f"provider_role must be one of {VALID_PROVIDER_ROLES}; got {provider_role!r}"
        )

    rep = inputs.get("authorised_representative")
    if rep is not None and not isinstance(rep, dict):
        raise ValueError("authorised_representative, when provided, must be a dict")

    sr_artifacts = inputs.get("systemic_risk_artifacts")
    if sr_artifacts is not None and not isinstance(sr_artifacts, dict):
        raise ValueError("systemic_risk_artifacts, when provided, must be a dict")

    cop = inputs.get("code_of_practice_status")
    if cop is not None and cop not in CODE_OF_PRACTICE_ENUM:
        raise ValueError(
            f"code_of_practice_status must be one of {CODE_OF_PRACTICE_ENUM}; got {cop!r}"
        )

    designated = inputs.get("designated_systemic_risk")
    if designated is not None and not isinstance(designated, bool):
        raise ValueError("designated_systemic_risk, when provided, must be a bool")

    below = inputs.get("self_declared_below_threshold")
    if below is not None and not isinstance(below, bool):
        raise ValueError("self_declared_below_threshold, when provided, must be a bool")

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")


def _classify_systemic_risk(
    model_description: dict[str, Any],
    designated: bool,
    self_declared_below: bool,
) -> tuple[str, list[str], list[str]]:
    """Return (status, citations, warnings) for Article 51 classification."""
    citations: list[str] = []
    warnings: list[str] = []

    if designated:
        citations.append("EU AI Act, Article 52")
        citations.append("EU AI Act, Article 51, Paragraph 1")
        return ("designated-systemic-risk", citations, warnings)

    flops = model_description.get("training_compute_flops")
    if isinstance(flops, (int, float)) and not isinstance(flops, bool):
        if flops >= SYSTEMIC_RISK_COMPUTE_THRESHOLD_FLOPS:
            citations.append("EU AI Act, Article 51, Paragraph 1, Point (a)")
            citations.append("EU AI Act, Article 51, Paragraph 2")
            return ("presumed-systemic-risk", citations, warnings)
        # Below threshold.
        citations.append("EU AI Act, Article 51, Paragraph 1")
        if self_declared_below:
            warnings.append(
                "self_declared_below_threshold is True. Practitioner-confirmation required: "
                "verify training_compute_flops measurement methodology and confirm no other "
                "Article 51 criterion (Annex XIII) applies."
            )
        else:
            warnings.append(
                "Confirm no other Article 51 criterion applies. The compute threshold is one "
                "of several pathways to systemic-risk classification under Annex XIII."
            )
        return ("not-systemic-risk", citations, warnings)

    # Unknown or non-numeric compute value (string "unknown", None, missing, etc.).
    citations.append("EU AI Act, Article 51, Paragraph 1")
    citations.append("EU AI Act, Annex XIII")
    warnings.append(
        "training_compute_flops unknown; systemic-risk status cannot be computed. Provide a "
        "numeric value or rely on Commission designation under Article 52."
    )
    return ("requires-assessment", citations, warnings)


def _evaluate_art_53(
    inputs: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (obligations, warnings) for Article 53 universal obligations."""
    obligations: list[dict[str, Any]] = []
    warnings: list[str] = []

    rules = (
        ("a", "technical_documentation_ref",
         "Technical documentation per Annex XI (model architecture, training data sources at "
         "a reasonable level, evaluation methodologies, energy consumption).",
         "EU AI Act, Article 53, Paragraph 1, Point (a)"),
        ("b", "downstream_integrator_docs_ref",
         "Documentation for downstream providers integrating the GPAI model.",
         "EU AI Act, Article 53, Paragraph 1, Point (b)"),
        ("c", "copyright_policy_ref",
         "Policy to comply with EU copyright law and Article 4(3) of Directive (EU) 2019/790 "
         "(text and data mining reservation of rights).",
         "EU AI Act, Article 53, Paragraph 1, Point (c)"),
        ("d", "training_data_summary_ref",
         "Sufficiently detailed training-data summary published per the Commission template.",
         "EU AI Act, Article 53, Paragraph 1, Point (d)"),
    )

    for letter, field, requirement, citation in rules:
        ref = inputs.get(field)
        present = bool(ref) and isinstance(ref, str) and ref.strip()
        status = "present" if present else "missing-warning"
        entry = {
            "obligation": f"Article 53(1)({letter})",
            "requirement": requirement,
            "input_field": field,
            "reference": ref if present else None,
            "status": status,
            "citation": citation,
        }
        obligations.append(entry)
        if not present:
            warnings.append(
                f"Article 53(1)({letter}) reference missing ({field}). Practitioner must supply "
                "a path or URL to the artifact, or document a justified non-applicability."
            )

    return (obligations, warnings)


def _evaluate_art_54(
    provider_role: str,
    authorised_representative: dict[str, Any] | None,
) -> tuple[str, list[str], list[str]]:
    """Return (status, citations, warnings) for Article 54 representative check."""
    citations: list[str] = []
    warnings: list[str] = []

    if provider_role == "non-eu-provider-with-representative":
        citations.append("EU AI Act, Article 54, Paragraph 1")
        if not authorised_representative:
            warnings.append(
                "provider_role declares an authorised representative but "
                "authorised_representative dict is not provided. Required content: name, "
                "eu_member_state, contact."
            )
            return ("incomplete", citations, warnings)
        required_rep_fields = ("name", "eu_member_state", "contact")
        missing = [f for f in required_rep_fields if not authorised_representative.get(f)]
        if missing:
            warnings.append(
                f"authorised_representative missing required fields: {sorted(missing)}."
            )
            return ("incomplete", citations, warnings)
        return ("satisfied", citations, warnings)

    if provider_role == "non-eu-provider-without-representative":
        citations.append("EU AI Act, Article 54, Paragraph 1")
        warnings.append(
            "Non-EU GPAI provider must designate EU authorised representative before "
            "placing on EU market. Article 54(1) is a precondition for market access."
        )
        return ("non-compliant", citations, warnings)

    # EU-established providers and downstream integrators.
    return ("not-applicable", citations, warnings)


def _evaluate_art_55(
    sr_artifacts: dict[str, Any] | None,
    code_of_practice_status: str | None,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Return (obligations, citations, warnings) for Article 55 systemic-risk
    additional obligations."""
    obligations: list[dict[str, Any]] = []
    citations: list[str] = []
    warnings: list[str] = []
    sr = sr_artifacts or {}

    eval_ref = sr.get("model_evaluation_ref")
    adv_ref = sr.get("adversarial_testing_ref")
    eval_present = bool(eval_ref) and isinstance(eval_ref, str) and eval_ref.strip()
    adv_present = bool(adv_ref) and isinstance(adv_ref, str) and adv_ref.strip()
    if eval_present and adv_present:
        a_status = "present"
    elif eval_present or adv_present:
        a_status = "partial"
    else:
        a_status = "missing"
    obligations.append({
        "obligation": "Article 55(1)(a)",
        "requirement": (
            "Model evaluation using state-of-the-art protocols and tools, including adversarial "
            "testing, with documentation."
        ),
        "input_fields": ["model_evaluation_ref", "adversarial_testing_ref"],
        "references": {
            "model_evaluation_ref": eval_ref if eval_present else None,
            "adversarial_testing_ref": adv_ref if adv_present else None,
        },
        "status": a_status,
        "citation": "EU AI Act, Article 55, Paragraph 1, Point (a)",
    })
    if a_status != "present":
        warnings.append(
            "Article 55(1)(a) requires both model_evaluation_ref and adversarial_testing_ref "
            "for systemic-risk GPAI providers. Status: " + a_status + "."
        )

    sra_ref = sr.get("systemic_risk_assessment_ref")
    sra_present = bool(sra_ref) and isinstance(sra_ref, str) and sra_ref.strip()
    obligations.append({
        "obligation": "Article 55(1)(b)",
        "requirement": (
            "Assess and mitigate possible systemic risks at Union level, including the sources "
            "of those risks."
        ),
        "input_fields": ["systemic_risk_assessment_ref"],
        "references": {"systemic_risk_assessment_ref": sra_ref if sra_present else None},
        "status": "present" if sra_present else "missing",
        "citation": "EU AI Act, Article 55, Paragraph 1, Point (b)",
    })
    if not sra_present:
        warnings.append(
            "Article 55(1)(b) systemic-risk assessment and mitigation reference missing "
            "(systemic_risk_assessment_ref)."
        )

    inc_ref = sr.get("serious_incidents_log_ref")
    inc_present = bool(inc_ref) and isinstance(inc_ref, str) and inc_ref.strip()
    obligations.append({
        "obligation": "Article 55(1)(c)",
        "requirement": (
            "Track, document, and report serious incidents and possible corrective measures to "
            "the AI Office and, as appropriate, national competent authorities."
        ),
        "input_fields": ["serious_incidents_log_ref"],
        "references": {"serious_incidents_log_ref": inc_ref if inc_present else None},
        "status": "present" if inc_present else "missing",
        "citation": "EU AI Act, Article 55, Paragraph 1, Point (c)",
    })
    if not inc_present:
        warnings.append(
            "Article 55(1)(c) serious-incidents log reference missing "
            "(serious_incidents_log_ref). This is a critical obligation: incidents must be "
            "tracked and reported to the AI Office. Pair with the incident-reporting plugin."
        )

    cyb_ref = sr.get("cybersecurity_measures_ref")
    cyb_present = bool(cyb_ref) and isinstance(cyb_ref, str) and cyb_ref.strip()
    obligations.append({
        "obligation": "Article 55(1)(d)",
        "requirement": (
            "Adequate level of cybersecurity protection for the GPAI model and the physical "
            "infrastructure of the model."
        ),
        "input_fields": ["cybersecurity_measures_ref"],
        "references": {"cybersecurity_measures_ref": cyb_ref if cyb_present else None},
        "status": "present" if cyb_present else "missing",
        "citation": "EU AI Act, Article 55, Paragraph 1, Point (d)",
    })
    if not cyb_present:
        warnings.append(
            "Article 55(1)(d) cybersecurity measures reference missing "
            "(cybersecurity_measures_ref)."
        )

    cop_status = code_of_practice_status or "not-signed"
    cop_note = ""
    if cop_status == "signed-full":
        cop_note = (
            "Code of Practice signed in full. Article 55(2) creates a presumption of compliance "
            "with Article 55(1) obligations until a harmonised standard is published."
        )
    elif cop_status == "signed-partial":
        cop_note = (
            "Code of Practice signed in part. Compliance presumption applies only to the "
            "obligations covered by signed sections."
        )
    elif cop_status == "not-signed":
        cop_note = (
            "Code of Practice not signed. Provider must demonstrate compliance through "
            "alternative adequate means under Article 55(1)."
        )
    elif cop_status == "not-applicable":
        cop_note = (
            "Code of Practice not applicable to this provider posture."
        )
    obligations.append({
        "obligation": "Article 55(2)",
        "requirement": (
            "Adherence to AI Office Codes of Practice creates a rebuttable presumption of "
            "compliance with Article 55(1) until a harmonised standard is published."
        ),
        "input_fields": ["code_of_practice_status"],
        "references": {"code_of_practice_status": cop_status},
        "status": cop_status,
        "citation": "EU AI Act, Article 55, Paragraph 2",
        "note": cop_note,
    })

    citations.extend([
        "EU AI Act, Article 55, Paragraph 1, Point (a)",
        "EU AI Act, Article 55, Paragraph 1, Point (b)",
        "EU AI Act, Article 55, Paragraph 1, Point (c)",
        "EU AI Act, Article 55, Paragraph 1, Point (d)",
        "EU AI Act, Article 55, Paragraph 2",
    ])
    return (obligations, citations, warnings)


def _build_downstream_integrator_posture(
    inputs: dict[str, Any],
) -> dict[str, Any] | None:
    model_description = inputs["model_description"]
    base_ref = model_description.get("base_model_ref")
    if not base_ref:
        return None
    received_docs = bool(inputs.get("downstream_integrator_docs_ref"))
    return {
        "base_model_ref": base_ref,
        "received_art_53_1_b_docs": received_docs,
        "responsibilities": [
            "Verify base model provider has Article 53 documentation.",
            "Rely on Article 53(1)(b) documentation for integration decisions.",
            "Do not inherit Article 55 obligations unless substantial modification per "
            "Article 25(1)(c) applies. Substantial-modification analysis is out of scope "
            "for this plugin; refer to supplier-vendor-assessor.",
        ],
        "citation": "EU AI Act, Article 53, Paragraph 1, Point (b)",
    }


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_gpai", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enrich_crosswalk(
    systemic_risk: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (cross_framework_citations, warnings) for GPAI obligations.

    Filters crosswalk mappings whose source_ref starts with 'Article 51',
    'Article 52', 'Article 53', 'Article 54', or 'Article 55' (the latter
    only when systemic-risk applies).
    """
    try:
        crosswalk = _load_crosswalk_module()
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return ([], [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"])

    wanted_prefixes = ("Article 51", "Article 52", "Article 53", "Article 54")
    if systemic_risk:
        wanted_prefixes = wanted_prefixes + ("Article 55",)

    filtered: list[dict[str, Any]] = []
    for m in data.get("mappings", []):
        if m.get("source_framework") != "eu-ai-act":
            continue
        source_ref = str(m.get("source_ref") or "")
        if not any(source_ref.startswith(p) for p in wanted_prefixes):
            continue
        filtered.append({
            "source_framework": m.get("source_framework"),
            "source_ref": source_ref,
            "target_framework": m.get("target_framework"),
            "target_ref": m.get("target_ref"),
            "relationship": m.get("relationship"),
            "confidence": m.get("confidence"),
        })
    return (filtered, [])


def assess_gpai_obligations(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Assess GPAI obligations under EU AI Act Articles 51 to 55.

    Args:
        inputs: Dict. See module docstring for the full input contract. Required
            keys: model_description (dict with model_name), provider_role
            (one of VALID_PROVIDER_ROLES). Optional keys: authorised_representative,
            technical_documentation_ref, copyright_policy_ref,
            training_data_summary_ref, downstream_integrator_docs_ref,
            designated_systemic_risk (bool), self_declared_below_threshold (bool),
            systemic_risk_artifacts (dict), code_of_practice_status (enum),
            enrich_with_crosswalk (bool, default True), reviewed_by.

    Returns:
        Dict with timestamp, agent_signature, framework, model_description_echo,
        systemic_risk_status, art_53_obligations, art_54_status,
        art_55_obligations (when applicable), downstream_integrator_posture
        (when applicable), code_of_practice_status, citations, warnings,
        summary, cross_framework_citations (when enriched), reviewed_by.

    Raises:
        ValueError: on missing or malformed required inputs.
    """
    _validate(inputs)

    model_description = inputs["model_description"]
    provider_role = inputs["provider_role"]
    authorised_representative = inputs.get("authorised_representative")
    designated = bool(inputs.get("designated_systemic_risk", False))
    self_declared_below = bool(inputs.get("self_declared_below_threshold", False))
    sr_artifacts = inputs.get("systemic_risk_artifacts")
    cop_status = inputs.get("code_of_practice_status")
    enrich = inputs.get("enrich_with_crosswalk", True)
    reviewed_by = inputs.get("reviewed_by")

    warnings: list[str] = []
    citations: list[str] = []

    # Article 51 classification.
    sr_status, sr_citations, sr_warnings = _classify_systemic_risk(
        model_description, designated, self_declared_below
    )
    citations.extend(sr_citations)
    warnings.extend(sr_warnings)

    # Article 53 universal obligations.
    art_53_obligations, art_53_warnings = _evaluate_art_53(inputs)
    warnings.extend(art_53_warnings)
    citations.append("EU AI Act, Article 53, Paragraph 1")
    citations.append("EU AI Act, Annex XI")
    for entry in art_53_obligations:
        c = entry["citation"]
        if c not in citations:
            citations.append(c)

    # Article 54 authorised-representative check.
    art_54_status, art_54_citations, art_54_warnings = _evaluate_art_54(
        provider_role, authorised_representative
    )
    for c in art_54_citations:
        if c not in citations:
            citations.append(c)
    warnings.extend(art_54_warnings)

    # Article 55 systemic-risk additional obligations (only when applicable).
    art_55_obligations: list[dict[str, Any]] | None = None
    if sr_status in ("presumed-systemic-risk", "designated-systemic-risk"):
        if provider_role == "downstream-integrator":
            warnings.append(
                "Provider role is downstream-integrator and systemic-risk classification "
                "applies to the upstream model. Downstream integrators do not inherit "
                "Article 55 obligations unless substantial modification per Article 25(1)(c) "
                "applies. Out of scope here; refer to supplier-vendor-assessor."
            )
        else:
            obligations, art_55_citations, art_55_warnings = _evaluate_art_55(
                sr_artifacts, cop_status
            )
            art_55_obligations = obligations
            for c in art_55_citations:
                if c not in citations:
                    citations.append(c)
            warnings.extend(art_55_warnings)

    # Downstream integrator posture (only when base_model_ref is set).
    downstream_posture = _build_downstream_integrator_posture(inputs)
    if downstream_posture:
        citation = downstream_posture.get("citation")
        if citation and citation not in citations:
            citations.append(citation)

    # Crosswalk enrichment.
    cross_framework_citations: list[dict[str, Any]] = []
    if enrich:
        cross_framework_citations, enrich_warnings = _enrich_crosswalk(
            systemic_risk=sr_status in ("presumed-systemic-risk", "designated-systemic-risk")
        )
        warnings.extend(enrich_warnings)

    # Defensive echo of model description (preserve only the canonical fields).
    model_description_echo = {
        "model_name": model_description.get("model_name"),
        "model_family": model_description.get("model_family"),
        "parameter_count": model_description.get("parameter_count"),
        "training_compute_flops": model_description.get("training_compute_flops"),
        "training_data_types": list(model_description.get("training_data_types") or []),
        "training_data_jurisdictions": list(
            model_description.get("training_data_jurisdictions") or []
        ),
        "modality": model_description.get("modality"),
        "release_date": model_description.get("release_date"),
        "model_version": model_description.get("model_version"),
        "base_model_ref": model_description.get("base_model_ref"),
    }

    summary = {
        "systemic_risk_status": sr_status,
        "provider_role": provider_role,
        "art_53_present_count": sum(
            1 for o in art_53_obligations if o["status"] == "present"
        ),
        "art_53_missing_count": sum(
            1 for o in art_53_obligations if o["status"] == "missing-warning"
        ),
        "art_54_status": art_54_status,
        "art_55_obligations_count": len(art_55_obligations) if art_55_obligations else 0,
        "downstream_integrator_posture_present": downstream_posture is not None,
        "code_of_practice_status": cop_status,
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "eu-ai-act",
        "model_description_echo": model_description_echo,
        "provider_role": provider_role,
        "systemic_risk_status": sr_status,
        "art_53_obligations": art_53_obligations,
        "art_54_status": art_54_status,
        "code_of_practice_status": cop_status,
        "citations": citations,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": reviewed_by,
    }
    if art_55_obligations is not None:
        output["art_55_obligations"] = art_55_obligations
    if downstream_posture is not None:
        output["downstream_integrator_posture"] = downstream_posture
    if enrich:
        output["cross_framework_citations"] = cross_framework_citations

    return output


def render_markdown(assessment: dict[str, Any]) -> str:
    """Render a GPAI obligations assessment as Markdown."""
    required = (
        "timestamp",
        "agent_signature",
        "model_description_echo",
        "systemic_risk_status",
        "art_53_obligations",
        "art_54_status",
        "citations",
        "warnings",
        "summary",
    )
    missing = [k for k in required if k not in assessment]
    if missing:
        raise ValueError(f"assessment missing required fields: {missing}")

    md = assessment["model_description_echo"]
    summary = assessment["summary"]

    lines = [
        "# GPAI Obligations Assessment",
        "",
        f"**Generated at (UTC):** {assessment['timestamp']}",
        f"**Generated by:** {assessment['agent_signature']}",
        f"**Framework:** {assessment.get('framework', 'eu-ai-act')}",
        f"**Provider role:** {assessment.get('provider_role')}",
    ]
    if assessment.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {assessment['reviewed_by']}")

    lines.extend([
        "",
        "## Model overview",
        "",
        f"- Model name: {md.get('model_name') or ''}",
        f"- Model family: {md.get('model_family') or ''}",
        f"- Parameter count: {md.get('parameter_count') or ''}",
        f"- Training compute (FLOPs): {md.get('training_compute_flops') or 'unknown'}",
        f"- Modality: {md.get('modality') or ''}",
        f"- Model version: {md.get('model_version') or ''}",
        f"- Release date: {md.get('release_date') or ''}",
        f"- Base model ref: {md.get('base_model_ref') or 'none'}",
        "",
        "## Systemic-risk classification",
        "",
        f"- Status: {assessment['systemic_risk_status']}",
        f"- Compute threshold (Article 51(2)): {SYSTEMIC_RISK_COMPUTE_THRESHOLD_FLOPS:.0e} FLOPs",
        "",
        "## Article 53 obligations",
        "",
        "| Obligation | Status | Reference | Citation |",
        "|---|---|---|---|",
    ])
    for o in assessment["art_53_obligations"]:
        ref = (o.get("reference") or "").replace("|", "\\|")
        lines.append(
            f"| {o['obligation']} | {o['status']} | {ref} | {o['citation']} |"
        )

    lines.extend([
        "",
        "## Article 54 status",
        "",
        f"- Status: {assessment['art_54_status']}",
    ])

    if assessment.get("art_55_obligations"):
        lines.extend([
            "",
            "## Article 55 obligations",
            "",
            "| Obligation | Status | Citation |",
            "|---|---|---|",
        ])
        for o in assessment["art_55_obligations"]:
            lines.append(f"| {o['obligation']} | {o['status']} | {o['citation']} |")
        # Surface code-of-practice note when present.
        for o in assessment["art_55_obligations"]:
            if o.get("note"):
                lines.append("")
                lines.append(f"**{o['obligation']} note:** {o['note']}")

    if assessment.get("downstream_integrator_posture"):
        dp = assessment["downstream_integrator_posture"]
        lines.extend([
            "",
            "## Downstream integrator posture",
            "",
            f"- Base model ref: {dp.get('base_model_ref')}",
            f"- Received Article 53(1)(b) documentation: {dp.get('received_art_53_1_b_docs')}",
            "",
            "**Responsibilities:**",
            "",
        ])
        for r in dp.get("responsibilities") or []:
            lines.append(f"- {r}")

    lines.extend([
        "",
        "## Summary",
        "",
        f"- Systemic-risk status: {summary['systemic_risk_status']}",
        f"- Article 53 present count: {summary['art_53_present_count']}",
        f"- Article 53 missing count: {summary['art_53_missing_count']}",
        f"- Article 54 status: {summary['art_54_status']}",
        f"- Article 55 obligations count: {summary['art_55_obligations_count']}",
        f"- Downstream integrator posture present: {summary['downstream_integrator_posture_present']}",
        f"- Code of practice status: {summary['code_of_practice_status']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in assessment["citations"]:
        lines.append(f"- {c}")

    if assessment.get("cross_framework_citations"):
        lines.extend(["", "## Cross-framework citations", ""])
        for m in assessment["cross_framework_citations"]:
            lines.append(
                f"- {m.get('source_framework')} {m.get('source_ref')} -> "
                f"{m.get('target_framework')} {m.get('target_ref')} "
                f"({m.get('relationship')}, {m.get('confidence')})"
            )

    lines.extend(["", "## Warnings", ""])
    if assessment.get("warnings"):
        for w in assessment["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("_No warnings._")

    lines.append("")
    return "\n".join(lines)


def render_csv(assessment: dict[str, Any]) -> str:
    """Render the obligations as CSV. One row per Article 53 and Article 55
    obligation. Columns: obligation, status, reference, citation."""
    if "art_53_obligations" not in assessment:
        raise ValueError("assessment missing 'art_53_obligations' field")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["obligation", "status", "reference", "citation"])

    for o in assessment["art_53_obligations"]:
        writer.writerow([
            o.get("obligation", ""),
            o.get("status", ""),
            o.get("reference") or "",
            o.get("citation", ""),
        ])

    for o in (assessment.get("art_55_obligations") or []):
        refs = o.get("references") or {}
        # Flatten reference dict into "k=v;k=v" string for the CSV cell.
        ref_parts = []
        for k, v in refs.items():
            if v is None or v == "":
                continue
            ref_parts.append(f"{k}={v}")
        writer.writerow([
            o.get("obligation", ""),
            o.get("status", ""),
            "; ".join(ref_parts),
            o.get("citation", ""),
        ])

    return buf.getvalue()
