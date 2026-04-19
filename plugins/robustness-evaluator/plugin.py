"""
AIGovOps: Robustness Evaluator Plugin

Operationalizes EU AI Act Article 15 (Accuracy, robustness, cybersecurity),
ISO/IEC 42001:2023 Annex A Control A.6.2.4 (Verification and validation
of the AI system), and NIST AI RMF 1.0 MEASURE 2.5 (valid and reliable),
2.6 (safe), and 2.7 (security and resilience). UK ATRS Section 3.2 (model
performance) and Colorado SB 205 Section 6-1-1702(1) and 6-1-1702(7) duty
of reasonable care provide jurisdiction-conditional layering.

Distinct from sibling plugins:
- metrics-collector: ongoing KPI surface against a metric catalogue.
- post-market-monitoring: forward-looking monitoring PLAN.
- nonconformity-tracker: ISO Clause 10.2 internal corrective-action lifecycle
  triggered when an evaluation surfaces a failure.
- incident-reporting: external statutory notification when an evaluation
  failure also qualifies as a reportable incident.

This plugin produces a POINT-IN-TIME evaluation record. It records what
was tested on a specific date, by which evaluator, with which method, and
what the verified resilience posture is for each Article 15 dimension.
The record is the artifact a notified body or auditor reviews to confirm
that the Article 15(1) tri-requirement has been verified for the system.

Design stance: the plugin does NOT compute metrics or run tests. Test
execution is the MLOps and red-team pipelines' responsibility. The plugin
validates a precomputed evaluation submission against per-dimension
expectations, attaches the correct citations, aggregates adversarial
posture per Article 15(4), surfaces lifecycle deltas when a previous
evaluation is referenced, and emits cross-plugin action items (most
notably the Article 15(2) instructions-for-use declaration).

Status: Phase 3 minimum-viable implementation. 0.1.0.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "robustness-evaluator/0.1.0"

REQUIRED_INPUT_FIELDS = ("system_description", "evaluation_scope", "evaluation_results")

VALID_EVALUATION_DIMENSIONS = (
    "accuracy",
    "robustness",
    "cybersecurity",
    "adversarial-robustness",
    "data-poisoning-resistance",
    "model-evasion-resistance",
    "confidentiality",
    "fail-safe-design",
    "concept-drift-handling",
    "continuous-learning-controls",
)

VALID_TEST_METHODS = (
    "holdout",
    "cross-validation",
    "stress-test",
    "boundary-test",
    "adversarial-test",
    "red-team-engagement",
    "fuzz-test",
    "membership-inference-test",
    "poisoning-simulation",
    "evasion-attack-simulation",
)

RESILIENCE_THRESHOLD_LEVELS = (
    "verified-strong",
    "verified-adequate",
    "verified-weak",
    "not-verified",
)

VALID_EVALUATOR_INDEPENDENCE = (
    "internal-team",
    "third-party-audit",
    "bug-bounty-program",
)

# Article 15(1) tri-requirement core dimensions for high-risk EU systems.
ART_15_1_CORE_DIMENSIONS = ("accuracy", "robustness", "cybersecurity")

# Article 15(4) adversarial-posture sub-dimensions.
ART_15_4_ADVERSARIAL_SUB_DIMENSIONS = (
    "adversarial-robustness",
    "data-poisoning-resistance",
    "model-evasion-resistance",
    "confidentiality",
)

# Resilience-level severity ordering, lower index = stronger.
_RESILIENCE_RANK = {
    "verified-strong": 0,
    "verified-adequate": 1,
    "verified-weak": 2,
    "not-verified": 3,
}

# Sibling-plugin path for crosswalk-matrix-builder. Lazy import so callers
# that pass enrich_with_crosswalk=False pay no import cost.
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

    sd = inputs["system_description"]
    if not isinstance(sd, dict):
        raise ValueError("system_description must be a dict")

    scope = inputs["evaluation_scope"]
    if not isinstance(scope, dict):
        raise ValueError("evaluation_scope must be a dict")
    dims = scope.get("dimensions")
    if not isinstance(dims, list) or not dims:
        raise ValueError("evaluation_scope.dimensions must be a non-empty list")
    for d in dims:
        if d not in VALID_EVALUATION_DIMENSIONS:
            raise ValueError(
                f"evaluation_scope.dimensions contains invalid dimension {d!r}; "
                f"must be one of {VALID_EVALUATION_DIMENSIONS}"
            )
    indep = scope.get("evaluator_independence")
    if indep is not None and indep not in VALID_EVALUATOR_INDEPENDENCE:
        raise ValueError(
            f"evaluation_scope.evaluator_independence {indep!r} invalid; "
            f"must be one of {VALID_EVALUATOR_INDEPENDENCE}"
        )

    results = inputs["evaluation_results"]
    if not isinstance(results, dict):
        raise ValueError("evaluation_results must be a dict mapping dimension to result")
    for dim, res in results.items():
        if dim not in VALID_EVALUATION_DIMENSIONS:
            raise ValueError(
                f"evaluation_results contains invalid dimension key {dim!r}; "
                f"must be one of {VALID_EVALUATION_DIMENSIONS}"
            )
        if not isinstance(res, dict):
            raise ValueError(f"evaluation_results[{dim!r}] must be a dict")
        method = res.get("test_method")
        if method is not None and method not in VALID_TEST_METHODS:
            raise ValueError(
                f"evaluation_results[{dim!r}].test_method {method!r} invalid; "
                f"must be one of {VALID_TEST_METHODS}"
            )
        rl = res.get("resilience_level")
        if rl is not None and rl not in RESILIENCE_THRESHOLD_LEVELS:
            raise ValueError(
                f"evaluation_results[{dim!r}].resilience_level {rl!r} invalid; "
                f"must be one of {RESILIENCE_THRESHOLD_LEVELS}"
            )


def _is_high_risk_eu(system_description: dict[str, Any]) -> bool:
    """Determine whether the system is a high-risk EU AI Act system."""
    risk_tier = (system_description.get("risk_tier") or "").lower()
    juris = system_description.get("jurisdiction")
    if isinstance(juris, str):
        juris_set = {juris.lower()}
    elif isinstance(juris, (list, tuple)):
        juris_set = {str(j).lower() for j in juris}
    else:
        juris_set = set()
    eu_in_scope = any(j in ("eu", "european-union") for j in juris_set)
    return eu_in_scope and risk_tier in ("high", "high-risk")


def _assess_dimension(
    dim: str,
    result: dict[str, Any],
    scope: dict[str, Any],
) -> dict[str, Any]:
    """Build a per-dimension assessment record with warnings."""
    warnings: list[str] = []

    test_method = result.get("test_method")
    if not test_method:
        warnings.append(
            f"Dimension {dim!r} has no test_method; ISO/IEC 42001:2023 Annex A Control A.6.2.4 "
            "requires the verification method to be recorded."
        )

    evidence_ref = result.get("evidence_ref")
    if not evidence_ref:
        warnings.append(
            f"Dimension {dim!r} has no evidence_ref; the evaluation record is not auditable without "
            "a pointer to the underlying test report."
        )

    # Accuracy and accuracy-shaped dimensions use metric/threshold/pass.
    metric_value = result.get("metric_value")
    declared_threshold = result.get("declared_threshold")
    pass_flag = result.get("pass")
    primary_metric = result.get("primary_metric")
    resilience_level = result.get("resilience_level")

    has_metric_pathway = metric_value is not None or declared_threshold is not None or pass_flag is not None
    has_resilience_pathway = resilience_level is not None

    if not has_metric_pathway and not has_resilience_pathway:
        warnings.append(
            f"Dimension {dim!r} provides neither a metric/threshold/pass tuple nor a resilience_level; "
            "auditor cannot determine verification outcome."
        )

    if dim == "accuracy" and not has_metric_pathway:
        warnings.append(
            "Accuracy dimension requires primary_metric, metric_value, declared_threshold, and pass. "
            "Article 15(1) accuracy requirement cannot be assessed without the declared metric."
        )

    if has_metric_pathway and pass_flag is False:
        # Failures bubble up as register-level warnings too via summary.
        warnings.append(
            f"Dimension {dim!r} reports pass=False (value {metric_value} against threshold {declared_threshold}); "
            "Article 15(1) tri-requirement is not satisfied for this dimension until remediated."
        )

    if dim in ART_15_4_ADVERSARIAL_SUB_DIMENSIONS and resilience_level == "not-verified":
        warnings.append(
            f"Dimension {dim!r} resilience_level is not-verified; Article 15(4) requires verified resilience "
            "against unauthorised alteration of use, output, or performance."
        )

    return {
        "dimension": dim,
        "test_method": test_method,
        "dataset_ref": result.get("dataset_ref"),
        "primary_metric": primary_metric,
        "metric_value": metric_value,
        "declared_threshold": declared_threshold,
        "pass": pass_flag,
        "resilience_level": resilience_level,
        "attack_types_tested": result.get("attack_types_tested"),
        "evidence_ref": evidence_ref,
        "evaluator_identity": scope.get("evaluator_identity"),
        "evaluator_independence": scope.get("evaluator_independence"),
        "evaluation_date": scope.get("evaluation_date"),
        "citations": _dimension_citations(dim),
        "warnings": warnings,
    }


def _dimension_citations(dim: str) -> list[str]:
    """Return the canonical citations applicable to a single evaluated dimension."""
    citations: list[str] = []
    if dim == "accuracy":
        citations.extend([
            "EU AI Act, Article 15, Paragraph 1",
            "EU AI Act, Article 15, Paragraph 2",
            "MEASURE 2.5",
        ])
    elif dim == "robustness":
        citations.extend([
            "EU AI Act, Article 15, Paragraph 1",
            "EU AI Act, Article 15, Paragraph 3",
            "MEASURE 2.5",
            "MEASURE 2.6",
        ])
    elif dim == "cybersecurity":
        citations.extend([
            "EU AI Act, Article 15, Paragraph 1",
            "EU AI Act, Article 15, Paragraph 4",
            "MEASURE 2.7",
        ])
    elif dim in ART_15_4_ADVERSARIAL_SUB_DIMENSIONS:
        citations.extend([
            "EU AI Act, Article 15, Paragraph 4",
            "MEASURE 2.7",
        ])
    elif dim == "fail-safe-design":
        citations.extend([
            "EU AI Act, Article 15, Paragraph 3",
            "MEASURE 2.6",
        ])
    elif dim in ("concept-drift-handling", "continuous-learning-controls"):
        citations.extend([
            "EU AI Act, Article 15, Paragraph 5",
            "MEASURE 2.5",
        ])
    citations.append("ISO/IEC 42001:2023, Annex A, Control A.6.2.4")
    return citations


def _aggregate_adversarial_posture(
    assessments: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Compute Article 15(4) adversarial posture from sub-dimension assessments."""
    sub_assessments = [
        a for a in assessments if a["dimension"] in ART_15_4_ADVERSARIAL_SUB_DIMENSIONS
    ]
    if not sub_assessments:
        return None
    levels: dict[str, str | None] = {}
    worst_rank = -1
    worst_level = "verified-strong"
    for a in sub_assessments:
        rl = a.get("resilience_level")
        levels[a["dimension"]] = rl
        if rl is None:
            # Treat missing as not-verified for posture aggregation.
            rank = _RESILIENCE_RANK["not-verified"]
            current_level = "not-verified"
        else:
            rank = _RESILIENCE_RANK[rl]
            current_level = rl
        if rank > worst_rank:
            worst_rank = rank
            worst_level = current_level
    return {
        "sub_dimension_levels": levels,
        "overall_adversarial_posture": worst_level,
        "citations": [
            "EU AI Act, Article 15, Paragraph 4",
            "MEASURE 2.7",
            "ISO/IEC 42001:2023, Annex A, Control A.6.2.4",
        ],
    }


def _trend_delta(
    current_assessments: list[dict[str, Any]],
    previous_evaluation: dict[str, Any] | None,
) -> list[dict[str, Any]] | None:
    """Compute per-dimension trend delta against a previous evaluation."""
    if not previous_evaluation:
        return None
    prev_by_dim: dict[str, dict[str, Any]] = {}
    prev_assessments = previous_evaluation.get("dimension_assessments") or []
    if not isinstance(prev_assessments, list):
        return None
    for a in prev_assessments:
        if isinstance(a, dict) and "dimension" in a:
            prev_by_dim[a["dimension"]] = a

    deltas: list[dict[str, Any]] = []
    for cur in current_assessments:
        dim = cur["dimension"]
        prev = prev_by_dim.get(dim)
        if not prev:
            deltas.append({
                "dimension": dim,
                "trend": "new",
                "previous": None,
                "current_summary": _delta_summary(cur),
            })
            continue
        cur_rl = cur.get("resilience_level")
        prev_rl = prev.get("resilience_level")
        if cur_rl is not None and prev_rl is not None:
            cur_rank = _RESILIENCE_RANK[cur_rl]
            prev_rank = _RESILIENCE_RANK[prev_rl]
            if cur_rank < prev_rank:
                trend = "improving"
            elif cur_rank > prev_rank:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            cur_v = cur.get("metric_value")
            prev_v = prev.get("metric_value")
            try:
                if cur_v is not None and prev_v is not None:
                    cv = float(cur_v)
                    pv = float(prev_v)
                    if cv > pv:
                        trend = "improving"
                    elif cv < pv:
                        trend = "degrading"
                    else:
                        trend = "stable"
                else:
                    trend = "indeterminate"
            except (TypeError, ValueError):
                trend = "indeterminate"
        deltas.append({
            "dimension": dim,
            "trend": trend,
            "previous": _delta_summary(prev),
            "current_summary": _delta_summary(cur),
        })
    return deltas


def _delta_summary(assessment: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric_value": assessment.get("metric_value"),
        "declared_threshold": assessment.get("declared_threshold"),
        "pass": assessment.get("pass"),
        "resilience_level": assessment.get("resilience_level"),
    }


def _load_crosswalk_module():
    """Import the sibling crosswalk-matrix-builder plugin module."""
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_robustness", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _crosswalk_enrich() -> tuple[list[dict[str, Any]], list[str]]:
    """Pull EU AI Act Article 15 mappings to ISO 42001 from the crosswalk dataset."""
    try:
        crosswalk = _load_crosswalk_module()
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return [], [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"]

    rows: list[dict[str, Any]] = []
    for m in data.get("mappings", []):
        if m.get("source_framework") != "eu-ai-act":
            continue
        src_ref = m.get("source_ref") or ""
        if not src_ref.startswith("Article 15"):
            continue
        rows.append({
            "source_ref": src_ref,
            "source_title": m.get("source_title"),
            "target_framework": m.get("target_framework"),
            "target_ref": m.get("target_ref"),
            "target_title": m.get("target_title"),
            "relationship": m.get("relationship"),
            "confidence": m.get("confidence"),
        })
    return rows, []


def evaluate_robustness(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and enrich a robustness evaluation submission.

    Args:
        inputs: Dict with:
            system_description: dict with system_id, risk_tier, jurisdiction,
                                continuous_learning (bool), and other context.
            evaluation_scope: dict with dimensions (list), evaluation_date,
                              evaluator_identity, evaluator_independence.
            evaluation_results: dict mapping dimension to result dict.
            backup_plan_ref: optional pointer to fail-safe documentation.
            concept_drift_monitoring_ref: optional pointer to drift-monitoring plan.
            previous_evaluation_ref: optional dict for lifecycle comparison.
            enrich_with_crosswalk: optional bool, default True.
            reviewed_by: optional string.

    Returns:
        Structured evaluation record dict.

    Raises:
        ValueError: if structural requirements are not met.
    """
    _validate(inputs)

    sd = inputs["system_description"]
    scope = inputs["evaluation_scope"]
    results = inputs["evaluation_results"]
    enrich = inputs.get("enrich_with_crosswalk", True)

    high_risk_eu = _is_high_risk_eu(sd)

    register_warnings: list[str] = []

    declared_dims: list[str] = list(scope["dimensions"])

    # Per-dimension assessment.
    dimension_assessments: list[dict[str, Any]] = []
    for dim in declared_dims:
        if dim in results:
            assessment = _assess_dimension(dim, results[dim], scope)
        else:
            assessment = {
                "dimension": dim,
                "test_method": None,
                "dataset_ref": None,
                "primary_metric": None,
                "metric_value": None,
                "declared_threshold": None,
                "pass": None,
                "resilience_level": None,
                "attack_types_tested": None,
                "evidence_ref": None,
                "evaluator_identity": scope.get("evaluator_identity"),
                "evaluator_independence": scope.get("evaluator_independence"),
                "evaluation_date": scope.get("evaluation_date"),
                "citations": _dimension_citations(dim),
                "warnings": [
                    f"Dimension {dim!r} declared in evaluation_scope but no result supplied; status=not-evaluated."
                ],
                "status": "not-evaluated",
            }
            dimension_assessments.append(assessment)
            continue
        dimension_assessments.append(assessment)

    # Article 15(1) high-risk EU systems require accuracy, robustness, cybersecurity.
    if high_risk_eu:
        evaluated_dims = {a["dimension"] for a in dimension_assessments if a.get("status") != "not-evaluated"}
        for core in ART_15_1_CORE_DIMENSIONS:
            if core not in evaluated_dims:
                register_warnings.append(
                    f"BLOCKING: Dimension {core!r} not evaluated. EU AI Act Article 15, Paragraph 1 "
                    "requires accuracy, robustness, and cybersecurity to be verified for high-risk systems."
                )

    # Article 15(4) adversarial-posture aggregation.
    adversarial_posture = _aggregate_adversarial_posture(dimension_assessments)

    # Article 15(2) declaration cross-plugin action item.
    accuracy_assessment = next(
        (a for a in dimension_assessments if a["dimension"] == "accuracy" and a.get("status") != "not-evaluated"),
        None,
    )
    art_15_2_declaration_status: dict[str, Any] | None = None
    if accuracy_assessment is not None:
        art_15_2_declaration_status = {
            "required_action": (
                "Declare the accuracy metric and threshold in the instructions for use "
                "per EU AI Act Article 13. Cross-plugin action: route to soa-generator and "
                "audit-log-generator outputs to evidence the declaration."
            ),
            "primary_metric": accuracy_assessment.get("primary_metric"),
            "metric_value": accuracy_assessment.get("metric_value"),
            "declared_threshold": accuracy_assessment.get("declared_threshold"),
            "citation": "EU AI Act, Article 15, Paragraph 2",
        }

    # Article 15(3) backup plan status.
    backup_plan_ref = inputs.get("backup_plan_ref")
    backup_plan_status: dict[str, Any] = {
        "backup_plan_ref": backup_plan_ref,
        "satisfied": bool(backup_plan_ref),
        "citation": "EU AI Act, Article 15, Paragraph 3",
    }
    if high_risk_eu and not backup_plan_ref:
        register_warnings.append(
            "BLOCKING: backup_plan_ref is not set. EU AI Act Article 15, Paragraph 3 requires "
            "fail-safe design and backup plans for high-risk systems."
        )

    # Article 15(5) concept drift monitoring status.
    cdm_ref = inputs.get("concept_drift_monitoring_ref")
    continuous_learning_dim_present = any(
        a["dimension"] in ("concept-drift-handling", "continuous-learning-controls")
        and a.get("status") != "not-evaluated"
        for a in dimension_assessments
    )
    continuous_learning_flag = bool(sd.get("continuous_learning"))
    concept_drift_monitoring_status: dict[str, Any] = {
        "concept_drift_monitoring_ref": cdm_ref,
        "continuous_learning_declared": continuous_learning_flag,
        "satisfied": bool(cdm_ref),
        "citation": "EU AI Act, Article 15, Paragraph 5",
    }
    if (continuous_learning_dim_present or continuous_learning_flag) and not cdm_ref:
        register_warnings.append(
            "Article 15, Paragraph 5: concept_drift_monitoring_ref is not set for a continuously-learning "
            "system. Feedback-loop risks must be addressed by the drift-monitoring plan."
        )

    # Evaluator independence note.
    indep = scope.get("evaluator_independence")
    independence_note: str | None = None
    if indep == "internal-team":
        independence_note = (
            "Evaluator independence is internal-team. EU AI Act Article 15 does not require external "
            "evaluation, but Article 43 conformity assessment by a notified body may require independent "
            "verification depending on the Annex VII pathway."
        )

    # Trend delta against previous evaluation.
    trend_delta = _trend_delta(dimension_assessments, inputs.get("previous_evaluation_ref"))

    # Top-level citations.
    top_citations = [
        "EU AI Act, Article 15, Paragraph 1",
        "ISO/IEC 42001:2023, Annex A, Control A.6.2.4",
        "MEASURE 2.5",
        "MEASURE 2.6",
        "MEASURE 2.7",
    ]
    juris = sd.get("jurisdiction")
    juris_set = set()
    if isinstance(juris, str):
        juris_set = {juris.lower()}
    elif isinstance(juris, (list, tuple)):
        juris_set = {str(j).lower() for j in juris}
    if any(j == "uk" for j in juris_set):
        top_citations.append("UK ATRS, Section Tool details")
    if any(j in ("usa-co", "colorado") for j in juris_set):
        top_citations.append("Colorado SB 205, Section 6-1-1702(1)")

    # Crosswalk enrichment.
    cross_framework_citations: list[dict[str, Any]] = []
    if enrich:
        rows, crosswalk_warnings = _crosswalk_enrich()
        cross_framework_citations = rows
        register_warnings.extend(crosswalk_warnings)

    # Article 15 applicability posture for non-high-risk systems.
    art_15_applicability = "mandatory" if high_risk_eu else "recommended-not-mandated"

    # Summary.
    failed_dims = [a["dimension"] for a in dimension_assessments if a.get("pass") is False]
    not_evaluated_dims = [a["dimension"] for a in dimension_assessments if a.get("status") == "not-evaluated"]
    summary = {
        "total_dimensions_in_scope": len(declared_dims),
        "dimensions_evaluated": len(declared_dims) - len(not_evaluated_dims),
        "dimensions_not_evaluated": len(not_evaluated_dims),
        "failed_dimensions": failed_dims,
        "overall_adversarial_posture": (
            adversarial_posture["overall_adversarial_posture"] if adversarial_posture else None
        ),
        "art_15_applicability": art_15_applicability,
        "blocking_warnings": sum(1 for w in register_warnings if w.startswith("BLOCKING")),
        "total_warnings": len(register_warnings)
            + sum(len(a.get("warnings") or []) for a in dimension_assessments),
        "trend_delta_present": trend_delta is not None,
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "eu-ai-act,iso42001,nist",
        "system_description_echo": sd,
        "evaluation_scope_echo": scope,
        "art_15_applicability": art_15_applicability,
        "dimension_assessments": dimension_assessments,
        "art_15_2_declaration_status": art_15_2_declaration_status,
        "backup_plan_status": backup_plan_status,
        "concept_drift_monitoring_status": concept_drift_monitoring_status,
        "evaluator_independence_note": independence_note,
        "citations": top_citations,
        "warnings": register_warnings,
        "summary": summary,
        "reviewed_by": inputs.get("reviewed_by"),
    }
    if adversarial_posture is not None:
        output["adversarial_posture"] = adversarial_posture
    if trend_delta is not None:
        output["trend_delta"] = trend_delta
    if enrich:
        output["cross_framework_citations"] = cross_framework_citations
    return output


def render_markdown(evaluation: dict[str, Any]) -> str:
    """Render a robustness evaluation as a Markdown document."""
    required = (
        "timestamp",
        "agent_signature",
        "citations",
        "dimension_assessments",
        "summary",
    )
    missing = [k for k in required if k not in evaluation]
    if missing:
        raise ValueError(f"evaluation missing required fields: {missing}")

    sd = evaluation.get("system_description_echo") or {}
    scope = evaluation.get("evaluation_scope_echo") or {}
    summary = evaluation["summary"]

    lines = [
        "# Robustness Evaluation Record",
        "",
        f"**Generated at (UTC):** {evaluation['timestamp']}",
        f"**Generated by:** {evaluation['agent_signature']}",
        f"**Framework rendering:** {evaluation.get('framework', 'eu-ai-act,iso42001,nist')}",
        f"**Article 15 applicability:** {evaluation.get('art_15_applicability', 'unknown')}",
    ]
    if evaluation.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {evaluation['reviewed_by']}")

    lines.extend([
        "",
        "## Scope",
        "",
        f"- System ID: {sd.get('system_id', 'not set')}",
        f"- Risk tier: {sd.get('risk_tier', 'not set')}",
        f"- Jurisdiction: {sd.get('jurisdiction', 'not set')}",
        f"- Evaluation date: {scope.get('evaluation_date', 'not set')}",
        f"- Evaluator identity: {scope.get('evaluator_identity', 'not set')}",
        f"- Evaluator independence: {scope.get('evaluator_independence', 'not set')}",
        f"- Dimensions in scope: {', '.join(scope.get('dimensions', []))}",
        "",
        "## Summary",
        "",
        f"- Total dimensions in scope: {summary['total_dimensions_in_scope']}",
        f"- Dimensions evaluated: {summary['dimensions_evaluated']}",
        f"- Dimensions not evaluated: {summary['dimensions_not_evaluated']}",
        f"- Failed dimensions: {', '.join(summary['failed_dimensions']) if summary['failed_dimensions'] else 'none'}",
        f"- Overall adversarial posture: {summary['overall_adversarial_posture'] or 'not assessed'}",
        f"- Blocking warnings: {summary['blocking_warnings']}",
        f"- Total warnings: {summary['total_warnings']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in evaluation["citations"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Dimension assessments", ""])
    if not evaluation["dimension_assessments"]:
        lines.append("_No dimensions assessed._")
    for a in evaluation["dimension_assessments"]:
        lines.extend([
            f"### {a['dimension']}",
            "",
            f"- Test method: {a.get('test_method') or 'not set'}",
            f"- Dataset reference: {a.get('dataset_ref') or 'not set'}",
            f"- Primary metric: {a.get('primary_metric') or 'not set'}",
            f"- Metric value: {a.get('metric_value') if a.get('metric_value') is not None else 'not set'}",
            f"- Declared threshold: {a.get('declared_threshold') if a.get('declared_threshold') is not None else 'not set'}",
            f"- Pass: {a.get('pass') if a.get('pass') is not None else 'not set'}",
            f"- Resilience level: {a.get('resilience_level') or 'not set'}",
            f"- Evidence reference: {a.get('evidence_ref') or 'not set'}",
            f"- Evaluator: {a.get('evaluator_identity') or 'not set'} ({a.get('evaluator_independence') or 'not set'})",
            "",
            "Citations:",
            "",
        ])
        for c in a.get("citations", []):
            lines.append(f"- {c}")
        if a.get("warnings"):
            lines.extend(["", "Warnings:", ""])
            for w in a["warnings"]:
                lines.append(f"- {w}")
        lines.append("")

    lines.extend(["## Adversarial posture", ""])
    if evaluation.get("adversarial_posture"):
        ap = evaluation["adversarial_posture"]
        lines.append(f"- Overall posture: {ap['overall_adversarial_posture']}")
        for sub, lvl in ap["sub_dimension_levels"].items():
            lines.append(f"- {sub}: {lvl or 'not set'}")
        lines.append("- Citations: " + ", ".join(ap["citations"]))
    else:
        lines.append("_No Article 15(4) sub-dimensions evaluated; adversarial posture not aggregated._")
    lines.append("")

    lines.extend(["## Article 15(2) declaration action", ""])
    decl = evaluation.get("art_15_2_declaration_status")
    if decl:
        lines.extend([
            f"- Required action: {decl['required_action']}",
            f"- Primary metric: {decl.get('primary_metric') or 'not set'}",
            f"- Metric value: {decl.get('metric_value') if decl.get('metric_value') is not None else 'not set'}",
            f"- Declared threshold: {decl.get('declared_threshold') if decl.get('declared_threshold') is not None else 'not set'}",
            f"- Citation: {decl['citation']}",
        ])
    else:
        lines.append("_Accuracy dimension not evaluated; no Article 15(2) declaration action emitted._")
    lines.append("")

    lines.extend(["## Backup plan status", ""])
    bps = evaluation["backup_plan_status"]
    lines.extend([
        f"- backup_plan_ref: {bps.get('backup_plan_ref') or 'not set'}",
        f"- Satisfied: {bps['satisfied']}",
        f"- Citation: {bps['citation']}",
        "",
    ])

    lines.extend(["## Concept drift status", ""])
    cds = evaluation["concept_drift_monitoring_status"]
    lines.extend([
        f"- concept_drift_monitoring_ref: {cds.get('concept_drift_monitoring_ref') or 'not set'}",
        f"- Continuous learning declared: {cds['continuous_learning_declared']}",
        f"- Satisfied: {cds['satisfied']}",
        f"- Citation: {cds['citation']}",
        "",
    ])

    if evaluation.get("trend_delta") is not None:
        lines.extend(["## Trend delta", ""])
        for d in evaluation["trend_delta"]:
            lines.append(f"- {d['dimension']}: {d['trend']}")
        lines.append("")

    if evaluation.get("evaluator_independence_note"):
        lines.extend(["## Evaluator independence note", "", evaluation["evaluator_independence_note"], ""])

    if evaluation.get("cross_framework_citations"):
        lines.extend(["## Cross-framework citations", ""])
        lines.append("| Source | Target framework | Target ref | Relationship | Confidence |")
        lines.append("|---|---|---|---|---|")
        for r in evaluation["cross_framework_citations"]:
            lines.append(
                f"| {r.get('source_ref', '')} | {r.get('target_framework', '')} | "
                f"{r.get('target_ref', '')} | {r.get('relationship', '')} | {r.get('confidence', '')} |"
            )
        lines.append("")

    lines.extend(["## Warnings", ""])
    if not evaluation.get("warnings"):
        lines.append("_No register-level warnings._")
    for w in evaluation.get("warnings", []):
        lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(evaluation: dict[str, Any]) -> str:
    """Render dimension assessments as CSV. One row per dimension in scope."""
    if "dimension_assessments" not in evaluation:
        raise ValueError("evaluation missing 'dimension_assessments' field")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "dimension",
        "test_method",
        "dataset_ref",
        "primary_metric",
        "metric_value",
        "declared_threshold",
        "pass",
        "resilience_level",
        "evidence_ref",
        "evaluator_identity",
        "evaluator_independence",
        "evaluation_date",
        "citations",
        "warning_count",
    ])
    for a in evaluation["dimension_assessments"]:
        writer.writerow([
            a.get("dimension", ""),
            a.get("test_method") or "",
            a.get("dataset_ref") or "",
            a.get("primary_metric") or "",
            "" if a.get("metric_value") is None else a.get("metric_value"),
            "" if a.get("declared_threshold") is None else a.get("declared_threshold"),
            "" if a.get("pass") is None else a.get("pass"),
            a.get("resilience_level") or "",
            a.get("evidence_ref") or "",
            a.get("evaluator_identity") or "",
            a.get("evaluator_independence") or "",
            a.get("evaluation_date") or "",
            "; ".join(a.get("citations") or []),
            len(a.get("warnings") or []),
        ])
    return buffer.getvalue()
