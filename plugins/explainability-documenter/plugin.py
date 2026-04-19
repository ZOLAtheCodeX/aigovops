"""
AIGovOps: Explainability Documenter Plugin

Produces a dedicated explainability documentation artifact operationalizing
NIST AI RMF 1.0 MEASURE 2.9 (model is explained and interpretable; functionality,
outputs, and associated risks are characterised), EU AI Act Article 86 (right
to explanation of individual decisions for affected persons), ISO/IEC 42001:2023
Annex A Control A.8.2 (system documentation and information for interested
parties), and UK Algorithmic Transparency Recording Standard Section Tool
details (model performance and explainability signals).

Design stance. The plugin does not invent explanation methods, interpretability
claims, known limitations, or evidence references. Every method declared by
the practitioner is echoed verbatim with its scope, target audience, and
implementation status, then assessed for coverage and consistency against
the four frameworks. Gaps surface as warnings; malformed inputs raise
ValueError.

Composition with sibling plugins.

- The aisia-runner plugin records explainability considerations as part of
  the impact dimension assessment. This plugin produces the dedicated
  explainability artifact that the AISIA cross-references.
- The soa-generator plugin cites A.8.2 at control-row level; this plugin
  produces the A.8.2 content that the SoA row points to.
- The audit-log-generator plugin records explainability decisions as
  governance events.
- The risk-register-builder plugin consumes explanation-method limitations
  as risk inputs.

Style. All citations use STYLE.md format. No em-dashes, no emojis, no
hedging language.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "explainability-documenter/0.1.0"

REQUIRED_INPUT_FIELDS = ("system_description", "model_type", "explanation_methods")

VALID_MODEL_TYPES = (
    "linear",
    "tree-based",
    "kernel",
    "neural-network",
    "deep-neural-network",
    "transformer",
    "ensemble",
    "rule-based",
    "hybrid",
)

VALID_EXPLANATION_METHODS = (
    "intrinsic-coefficients",
    "intrinsic-decision-path",
    "shap",
    "lime",
    "integrated-gradients",
    "attention-visualization",
    "counterfactual",
    "feature-importance-global",
    "feature-importance-local",
    "surrogate-model",
    "prototype-retrieval",
    "model-card-only",
)

VALID_SCOPES = ("global", "local", "both")

VALID_AUDIENCES = (
    "developers",
    "deployers",
    "operators",
    "auditors",
    "affected-persons",
    "regulators",
    "end-users",
)

VALID_IMPLEMENTATION_STATUSES = ("implemented", "planned", "not-applicable")

EU_ART_86_APPLICABILITY_THRESHOLD = ("legal-effect", "similarly-significant-effect")

VALID_DECISION_EFFECTS = (
    "legal",
    "financial",
    "safety-related",
    "opportunity-related",
    "reputation-related",
    "none",
    # Accept the threshold tokens too, so callers can use either the
    # effect name or the threshold name.
    "legal-effect",
    "similarly-significant-effect",
)

INTRINSIC_COMPATIBLE_MODEL_TYPES = ("linear", "tree-based", "rule-based")
POST_HOC_REQUIRED_MODEL_TYPES = (
    "neural-network",
    "deep-neural-network",
    "transformer",
    "ensemble",
    "kernel",
    "hybrid",
)

_POST_HOC_METHODS = {
    "shap",
    "lime",
    "integrated-gradients",
    "attention-visualization",
    "counterfactual",
    "feature-importance-global",
    "feature-importance-local",
    "surrogate-model",
    "prototype-retrieval",
    "model-card-only",
}

_INTRINSIC_METHODS = {"intrinsic-coefficients", "intrinsic-decision-path"}

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily inside
# the enrichment helper so calls with enrich_with_crosswalk=False pay no
# import cost and are unaffected by crosswalk-side failures.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))

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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    system = inputs["system_description"]
    if not isinstance(system, dict):
        raise ValueError("system_description must be a dict")

    model_type = inputs["model_type"]
    if model_type not in VALID_MODEL_TYPES:
        raise ValueError(
            f"model_type must be one of {VALID_MODEL_TYPES}; got {model_type!r}"
        )

    methods = inputs["explanation_methods"]
    if not isinstance(methods, list):
        raise ValueError("explanation_methods must be a list")
    for i, m in enumerate(methods):
        if not isinstance(m, dict):
            raise ValueError(
                f"explanation_methods[{i}] must be a dict; got {type(m).__name__}"
            )
        method_name = m.get("method")
        if method_name not in VALID_EXPLANATION_METHODS:
            raise ValueError(
                f"explanation_methods[{i}].method must be one of {VALID_EXPLANATION_METHODS}; "
                f"got {method_name!r}"
            )
        scope = m.get("scope")
        if scope not in VALID_SCOPES:
            raise ValueError(
                f"explanation_methods[{i}].scope must be one of {VALID_SCOPES}; got {scope!r}"
            )
        audience = m.get("target_audience")
        if not isinstance(audience, list):
            raise ValueError(
                f"explanation_methods[{i}].target_audience must be a list of audience tokens"
            )
        for a in audience:
            if a not in VALID_AUDIENCES:
                raise ValueError(
                    f"explanation_methods[{i}].target_audience entry {a!r} is not in {VALID_AUDIENCES}"
                )
        status = m.get("implementation_status")
        if status not in VALID_IMPLEMENTATION_STATUSES:
            raise ValueError(
                f"explanation_methods[{i}].implementation_status must be one of "
                f"{VALID_IMPLEMENTATION_STATUSES}; got {status!r}"
            )
        limitations = m.get("known_limitations")
        if limitations is not None and not isinstance(limitations, list):
            raise ValueError(
                f"explanation_methods[{i}].known_limitations, when provided, must be a list"
            )

    intrinsic_claim = inputs.get("intrinsic_interpretability_claim")
    if intrinsic_claim is not None and not isinstance(intrinsic_claim, bool):
        raise ValueError(
            "intrinsic_interpretability_claim, when provided, must be a bool"
        )

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")


def _classify_model_type(
    model_type: str, intrinsic_claim: bool, methods: list[dict[str, Any]]
) -> tuple[str, list[str]]:
    """Return (classification, warnings).

    Classification is one of:
      - intrinsic-interpretable
      - post-hoc-required
      - post-hoc-covered
      - post-hoc-missing
    """
    warnings: list[str] = []

    if intrinsic_claim and model_type not in INTRINSIC_COMPATIBLE_MODEL_TYPES:
        warnings.append(
            f"Intrinsic interpretability claim incompatible with model type {model_type}. "
            "NIST AI RMF, MEASURE 2.9 requires an intrinsic-interpretability claim to align with a model "
            "family whose structure makes the claim defensible."
        )

    if intrinsic_claim and model_type in INTRINSIC_COMPATIBLE_MODEL_TYPES:
        return "intrinsic-interpretable", warnings

    if model_type in POST_HOC_REQUIRED_MODEL_TYPES:
        has_post_hoc = any(m["method"] in _POST_HOC_METHODS for m in methods)
        if has_post_hoc:
            return "post-hoc-covered", warnings
        warnings.append(
            f"Model type {model_type} requires at least one post-hoc explanation method. "
            "NIST AI RMF, MEASURE 2.9 requires characterisation of explanation methodology for opaque model families."
        )
        return "post-hoc-missing", warnings

    # Intrinsic-compatible type without the claim: treat as post-hoc-covered
    # if at least one method present; else post-hoc-missing.
    if methods:
        return "post-hoc-covered", warnings
    warnings.append(
        "No explanation methods declared. NIST AI RMF, MEASURE 2.9 requires characterisation of "
        "explanation methodology."
    )
    return "post-hoc-missing", warnings


def _assess_scope_coverage(methods: list[dict[str, Any]]) -> dict[str, Any]:
    scopes_covered: set[str] = set()
    for m in methods:
        s = m["scope"]
        if s == "both":
            scopes_covered.add("global")
            scopes_covered.add("local")
        else:
            scopes_covered.add(s)
    global_covered = "global" in scopes_covered
    local_covered = "local" in scopes_covered
    warnings: list[str] = []
    if not global_covered:
        warnings.append(
            "No explanation method covers global scope. NIST AI RMF, MEASURE 2.9 requires characterisation "
            "of global interpretability (overall model behaviour)."
        )
    if not local_covered:
        warnings.append(
            "No explanation method covers local scope. EU AI Act, Article 86 confers a right to explanation "
            "for individual decisions, which requires a local-scope explanation method."
        )
    return {
        "global_covered": global_covered,
        "local_covered": local_covered,
        "scopes_covered": sorted(scopes_covered),
        "warnings": warnings,
    }


def _assess_audience_coverage(
    methods: list[dict[str, Any]], decision_effects: list[str]
) -> dict[str, Any]:
    audiences_covered: set[str] = set()
    for m in methods:
        for a in m.get("target_audience") or []:
            audiences_covered.add(a)

    warnings: list[str] = []
    art_86_triggers = {"legal", "legal-effect", "similarly-significant-effect"}
    high_risk_effect = any(e in art_86_triggers for e in decision_effects)

    if high_risk_effect and "affected-persons" not in audiences_covered:
        warnings.append(
            "BLOCKING: decision_effects include legal or similarly significant effects, but no explanation "
            "method targets affected-persons. EU AI Act, Article 86 confers a right to explanation for "
            "affected persons on high-risk decisions with legal or similarly significant effects."
        )

    if high_risk_effect and not ({"deployers", "operators"} & audiences_covered):
        warnings.append(
            "No explanation method targets deployers or operators. EU AI Act, Article 13 requires "
            "instructions for use sufficient for deployers to operate a high-risk AI system."
        )

    return {
        "audiences_covered": sorted(audiences_covered),
        "affected_persons_covered": "affected-persons" in audiences_covered,
        "deployer_or_operator_covered": bool({"deployers", "operators"} & audiences_covered),
        "warnings": warnings,
    }


def _assess_art_86_applicability(
    decision_effects: list[str], template_ref: str | None
) -> dict[str, Any]:
    applies = any(e in EU_ART_86_APPLICABILITY_THRESHOLD or e == "legal" for e in decision_effects)
    warnings: list[str] = []
    if applies and not (template_ref and str(template_ref).strip()):
        warnings.append(
            "EU AI Act, Article 86 applies to this system but art_86_response_template_ref is empty. "
            "Article 86 requires a template for responding to individual explanation requests from affected persons."
        )
    triggers = [e for e in decision_effects if e in EU_ART_86_APPLICABILITY_THRESHOLD or e == "legal"]
    return {
        "applies": applies,
        "triggering_effects": triggers,
        "response_template_ref": template_ref,
        "warnings": warnings,
    }


def _assess_limitations(methods: list[dict[str, Any]]) -> dict[str, Any]:
    per_method: list[dict[str, Any]] = []
    warnings: list[str] = []
    empty_count = 0
    not_applicable_missing_rationale = 0
    planned_missing_target_date = 0
    for i, m in enumerate(methods):
        lim = m.get("known_limitations") or []
        status = m["implementation_status"]
        target_date = m.get("target_date")
        entry: dict[str, Any] = {
            "method": m["method"],
            "limitations_present": bool(lim),
            "limitation_count": len(lim),
            "implementation_status": status,
        }
        if not lim:
            empty_count += 1
            warnings.append(
                f"explanation_methods[{i}] method={m['method']} has empty known_limitations. "
                "NIST AI RMF, MEASURE 2.9 requires characterisation of explanation limitations."
            )
        if status == "not-applicable" and not lim:
            not_applicable_missing_rationale += 1
            warnings.append(
                f"explanation_methods[{i}] method={m['method']} has implementation_status=not-applicable "
                "but known_limitations is empty. The rationale for non-applicability must be recorded in known_limitations."
            )
        if status == "planned" and not target_date:
            planned_missing_target_date += 1
            warnings.append(
                f"explanation_methods[{i}] method={m['method']} has implementation_status=planned but no target_date. "
                "Planned methods must reference a target completion date."
            )
        per_method.append(entry)
    return {
        "per_method": per_method,
        "methods_with_empty_limitations": empty_count,
        "not_applicable_missing_rationale": not_applicable_missing_rationale,
        "planned_missing_target_date": planned_missing_target_date,
        "warnings": warnings,
    }


def _build_methods_coverage(methods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in methods:
        out.append({
            "method": m["method"],
            "scope": m["scope"],
            "target_audience": list(m.get("target_audience") or []),
            "implementation_status": m["implementation_status"],
            "evidence_ref": m.get("evidence_ref"),
            "known_limitations": list(m.get("known_limitations") or []),
            "target_date": m.get("target_date"),
        })
    return out


def _build_citations(
    art_86_applies: bool,
    jurisdiction: str | None,
    classification: str,
) -> list[str]:
    citations = [
        "NIST AI RMF, MEASURE 2.9",
        "ISO/IEC 42001:2023, Annex A, Control A.8.2",
        "ISO/IEC TR 24028:2020",
    ]
    if art_86_applies:
        citations.append("EU AI Act, Article 86, Paragraph 1")
        # Instructions-for-use obligation for deployers.
        citations.append("EU AI Act, Article 13, Paragraph 3, Point (b)")
    if jurisdiction and "uk" in jurisdiction.lower():
        citations.append("UK ATRS, Section Tool details")
    return citations


def _compute_schema_diff(
    current: dict[str, Any], previous_ref: str | None
) -> dict[str, Any] | None:
    if not previous_ref:
        return None
    # The plugin does not resolve external references. It records the
    # comparison anchor so a downstream reviewer can run the diff against
    # the retrieved prior artifact.
    return {
        "previous_documentation_ref": previous_ref,
        "comparison_performed": False,
        "comparison_note": (
            "Schema diff requires the prior artifact payload. The plugin records the reference and defers "
            "payload-level comparison to the reviewer."
        ),
    }


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_explainability", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enrich_with_crosswalk(
    target_frameworks: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Pull cross-framework coverage for MEASURE 2.9 and A.8.2 anchors.

    Returns (citations_list, warnings). Each entry carries target_framework,
    target_ref, target_title, relationship, confidence, citation.
    """
    try:
        crosswalk = _load_crosswalk_module()
    except Exception as exc:
        return [], [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"]

    try:
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return [], [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"]

    anchors = {
        ("nist-ai-rmf", "MEASURE 2.9"),
        ("iso42001", "A.8.2"),
        ("eu-ai-act", "Article 86"),
    }
    allowed = set(target_frameworks)
    collected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for m in data.get("mappings", []):
        sfw = m.get("source_framework")
        sref = m.get("source_ref") or ""
        matched = False
        for anchor_fw, anchor_ref in anchors:
            if sfw == anchor_fw and anchor_ref in sref:
                matched = True
                break
        if not matched:
            continue
        if m.get("target_framework") not in allowed:
            continue
        mid = m.get("id")
        if mid in seen_ids:
            continue
        seen_ids.add(mid)
        cs = m.get("citation_sources") or []
        citation_label = ""
        if cs:
            citation_label = (cs[0].get("publication") or "").strip()
        collected.append({
            "source_framework": sfw,
            "source_ref": m.get("source_ref"),
            "target_framework": m.get("target_framework"),
            "target_ref": m.get("target_ref"),
            "target_title": m.get("target_title"),
            "relationship": m.get("relationship"),
            "confidence": m.get("confidence"),
            "citation": citation_label,
        })
    return collected, []


def document_explainability(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Produce an explainability documentation artifact.

    Args:
        inputs: Dict with required fields system_description, model_type,
            explanation_methods; optional intrinsic_interpretability_claim,
            art_86_response_template_ref, previous_documentation_ref,
            enrich_with_crosswalk, reviewed_by, crosswalk_target_frameworks.

    Returns:
        Dict with timestamp, agent_signature, framework, system_description_echo,
        model_type_classification, methods_coverage, scope_coverage,
        audience_coverage, art_86_applicability, art_86_readiness,
        limitations_documentation_assessment, schema_diff_summary (when
        applicable), citations, warnings, summary, cross_framework_citations
        (when enriched), reviewed_by.

    Raises:
        ValueError on malformed input.
    """
    _validate(inputs)

    system = inputs["system_description"]
    model_type = inputs["model_type"]
    methods = inputs["explanation_methods"]
    intrinsic_claim = bool(inputs.get("intrinsic_interpretability_claim", False))
    template_ref = inputs.get("art_86_response_template_ref")
    previous_ref = inputs.get("previous_documentation_ref")
    reviewed_by = inputs.get("reviewed_by")

    decision_effects = list(system.get("decision_effects") or [])
    jurisdiction = system.get("jurisdiction")

    # Classification.
    classification_value, classification_warnings = _classify_model_type(
        model_type, intrinsic_claim, methods
    )

    # Coverage assessments.
    scope_assessment = _assess_scope_coverage(methods)
    audience_assessment = _assess_audience_coverage(methods, decision_effects)
    art_86_assessment = _assess_art_86_applicability(decision_effects, template_ref)
    limitations_assessment = _assess_limitations(methods)

    # Methods coverage echo.
    methods_coverage = _build_methods_coverage(methods)

    # Citations.
    citations = _build_citations(
        art_86_assessment["applies"], jurisdiction, classification_value
    )

    # Schema diff.
    schema_diff = _compute_schema_diff(inputs, previous_ref)

    # Aggregate warnings.
    warnings: list[str] = []
    warnings.extend(classification_warnings)
    warnings.extend(scope_assessment["warnings"])
    warnings.extend(audience_assessment["warnings"])
    warnings.extend(art_86_assessment["warnings"])
    warnings.extend(limitations_assessment["warnings"])

    # Art. 86 readiness summary.
    art_86_readiness = {
        "applies": art_86_assessment["applies"],
        "response_template_present": bool(template_ref and str(template_ref).strip()),
        "affected_persons_audience_present": audience_assessment["affected_persons_covered"],
        "local_scope_method_present": scope_assessment["local_covered"],
        "ready": (
            art_86_assessment["applies"]
            and bool(template_ref and str(template_ref).strip())
            and audience_assessment["affected_persons_covered"]
            and scope_assessment["local_covered"]
        ) if art_86_assessment["applies"] else None,
    }

    # Optional crosswalk enrichment.
    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True
    target_frameworks = list(
        inputs.get("crosswalk_target_frameworks") or DEFAULT_CROSSWALK_TARGET_FRAMEWORKS
    )
    cross_framework_citations: list[dict[str, Any]] | None = None
    if enrich:
        cross_framework_citations, enrich_warnings = _enrich_with_crosswalk(target_frameworks)
        warnings.extend(enrich_warnings)

    summary = {
        "total_methods": len(methods),
        "scopes_covered": scope_assessment["scopes_covered"],
        "audiences_covered": audience_assessment["audiences_covered"],
        "methods_with_empty_limitations": limitations_assessment["methods_with_empty_limitations"],
        "warning_count": len(warnings),
        "art_86_applies": art_86_assessment["applies"],
        "classification": classification_value,
    }

    framework_list = "nist,eu-ai-act,iso42001,uk-atrs"

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": framework_list,
        "system_description_echo": dict(system),
        "model_type_classification": {
            "model_type": model_type,
            "classification": classification_value,
            "intrinsic_interpretability_claim": intrinsic_claim,
        },
        "methods_coverage": methods_coverage,
        "scope_coverage": {
            "global_covered": scope_assessment["global_covered"],
            "local_covered": scope_assessment["local_covered"],
            "scopes_covered": scope_assessment["scopes_covered"],
        },
        "audience_coverage": {
            "audiences_covered": audience_assessment["audiences_covered"],
            "affected_persons_covered": audience_assessment["affected_persons_covered"],
            "deployer_or_operator_covered": audience_assessment["deployer_or_operator_covered"],
        },
        "art_86_applicability": art_86_assessment,
        "art_86_readiness": art_86_readiness,
        "limitations_documentation_assessment": limitations_assessment,
        "citations": citations,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": reviewed_by,
    }
    if schema_diff is not None:
        output["schema_diff_summary"] = schema_diff
    if cross_framework_citations is not None:
        output["cross_framework_citations"] = cross_framework_citations
    return output


def render_markdown(documentation: dict[str, Any]) -> str:
    """Render an explainability documentation artifact as Markdown."""
    required = (
        "timestamp",
        "agent_signature",
        "framework",
        "model_type_classification",
        "methods_coverage",
        "scope_coverage",
        "audience_coverage",
        "citations",
        "summary",
    )
    missing = [k for k in required if k not in documentation]
    if missing:
        raise ValueError(f"documentation missing required fields: {missing}")

    system = documentation.get("system_description_echo") or {}
    lines: list[str] = [
        f"# Explainability Documentation: {system.get('system_name', '(unnamed system)')}",
        "",
        f"**Generated at (UTC):** {documentation['timestamp']}",
        f"**Generated by:** {documentation['agent_signature']}",
        f"**Framework coverage:** {documentation['framework']}",
    ]
    if documentation.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {documentation['reviewed_by']}")

    cls = documentation["model_type_classification"]
    lines.extend([
        "",
        "## Classification",
        "",
        f"- Model type: {cls['model_type']}",
        f"- Classification: {cls['classification']}",
        f"- Intrinsic interpretability claim: {cls['intrinsic_interpretability_claim']}",
        "",
        "## Methods coverage",
        "",
        "| Method | Scope | Target audience | Status | Evidence ref |",
        "|---|---|---|---|---|",
    ])
    for m in documentation["methods_coverage"]:
        audience = ", ".join(m.get("target_audience") or [])
        evidence = m.get("evidence_ref") or ""
        lines.append(
            f"| {m['method']} | {m['scope']} | {audience} | {m['implementation_status']} | {evidence} |"
        )

    scope = documentation["scope_coverage"]
    lines.extend([
        "",
        "## Scope coverage",
        "",
        f"- Global covered: {scope['global_covered']}",
        f"- Local covered: {scope['local_covered']}",
        f"- Scopes covered: {', '.join(scope['scopes_covered']) or '(none)'}",
    ])

    audience_cov = documentation["audience_coverage"]
    lines.extend([
        "",
        "## Audience coverage",
        "",
        f"- Audiences covered: {', '.join(audience_cov['audiences_covered']) or '(none)'}",
        f"- Affected-persons covered: {audience_cov['affected_persons_covered']}",
        f"- Deployer or operator covered: {audience_cov['deployer_or_operator_covered']}",
    ])

    art_86 = documentation.get("art_86_applicability") or {}
    if art_86.get("applies"):
        readiness = documentation.get("art_86_readiness") or {}
        lines.extend([
            "",
            "## Art. 86 applicability",
            "",
            f"- Applies: {art_86.get('applies')}",
            f"- Triggering effects: {', '.join(art_86.get('triggering_effects') or []) or '(none)'}",
            f"- Response template ref: {art_86.get('response_template_ref') or '(missing)'}",
            f"- Ready: {readiness.get('ready')}",
        ])

    lim = documentation.get("limitations_documentation_assessment") or {}
    lines.extend([
        "",
        "## Limitations assessment",
        "",
        f"- Methods with empty limitations: {lim.get('methods_with_empty_limitations', 0)}",
        f"- not-applicable methods missing rationale: {lim.get('not_applicable_missing_rationale', 0)}",
        f"- planned methods missing target_date: {lim.get('planned_missing_target_date', 0)}",
    ])

    lines.extend(["", "## Citations", ""])
    for c in documentation["citations"]:
        lines.append(f"- {c}")

    if documentation.get("cross_framework_citations") is not None:
        lines.extend(["", "## Cross-framework citations", ""])
        refs = documentation.get("cross_framework_citations") or []
        if not refs:
            lines.append("- (no cross-framework citations found for target frameworks)")
        else:
            for ref in refs:
                conf = ref.get("confidence") or ""
                badge = f"[{conf}]" if conf else ""
                lines.append(
                    f"- {ref.get('source_framework')} {ref.get('source_ref')} -> "
                    f"{ref.get('target_framework')} {ref.get('target_ref')} "
                    f"({ref.get('relationship')}) {badge}".rstrip()
                )

    if documentation.get("schema_diff_summary"):
        diff = documentation["schema_diff_summary"]
        lines.extend([
            "",
            "## Schema diff summary",
            "",
            f"- previous_documentation_ref: {diff.get('previous_documentation_ref', '')}",
            f"- comparison_performed: {diff.get('comparison_performed', False)}",
            f"- note: {diff.get('comparison_note', '')}",
        ])

    lines.extend(["", "## Warnings", ""])
    warnings = documentation.get("warnings") or []
    if not warnings:
        lines.append("- (no warnings)")
    else:
        for w in warnings:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(documentation: dict[str, Any]) -> str:
    """Render methods_coverage as CSV, one row per method."""
    if "methods_coverage" not in documentation:
        raise ValueError("documentation missing 'methods_coverage' field")

    header_cols = [
        "method",
        "scope",
        "target_audience",
        "implementation_status",
        "evidence_ref",
        "known_limitations_count",
        "target_date",
    ]
    header = ",".join(header_cols)
    lines = [header]
    for m in documentation["methods_coverage"]:
        fields = [
            _csv_escape(str(m.get("method", ""))),
            _csv_escape(str(m.get("scope", ""))),
            _csv_escape("; ".join(m.get("target_audience") or [])),
            _csv_escape(str(m.get("implementation_status", ""))),
            _csv_escape(str(m.get("evidence_ref") or "")),
            _csv_escape(str(len(m.get("known_limitations") or []))),
            _csv_escape(str(m.get("target_date") or "")),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
