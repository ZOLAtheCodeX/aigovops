"""
AIGovOps: Bias Evaluator Plugin

Computes standard fairness metrics across protected-attribute groups from
caller-supplied evaluation data and applies jurisdictional rule sets to
the computed values. Operationalizes:

- NIST AI RMF 1.0 MEASURE 2.11 (fairness and bias evaluated).
- EU AI Act, Article 10, Paragraph 4 (bias examination obligation for
  high-risk systems).
- NYC Local Law 144 of 2021 and DCWP Final Rule, Section 5-301
  (selection rate and impact ratio per the four-fifths rule).
- Colorado SB 205, Section 6-1-1702(1) (developer and deployer duty of
  reasonable care to protect against algorithmic discrimination).
- Singapore MAS Veritas (2022) fairness methodology
  (context-aware metric selection, balanced-dataset orientation).
- ISO/IEC 42001:2023, Annex A, Control A.7.4 (data quality) as the
  upstream control; ISO/IEC TR 24027:2021 referenced as advisory.

Design stance: the plugin does NOT perform model inference. It receives
per-group counts (totals, selected, true-positive, false-positive, etc.)
that the caller has already computed against an evaluation dataset, and
emits the standard fairness metrics that the protected-attribute slice
implies. The plugin does NOT assign an overall bias score; per-metric
results are emitted and the practitioner interprets them in context.

When ground truth is unavailable (ground_truth_available=False), metrics
that require true-positive or false-positive counts are emitted as
"requires-ground-truth" with a warning, never silently computed.

Status: 0.1.0.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "bias-evaluator/0.1.0"

REQUIRED_INPUT_FIELDS = ("system_description", "evaluation_data", "protected_attributes")

VALID_METRICS = (
    "selection-rate",
    "impact-ratio",
    "demographic-parity-difference",
    "equalized-odds-difference",
    "predictive-parity-difference",
    "statistical-parity-difference",
)

VALID_JURISDICTION_RULES = (
    "nyc-ll144-4-5ths",
    "eu-ai-act-art-10-4",
    "colorado-sb-205-reasonable-care",
    "singapore-veritas-fairness",
    "iso-42001-a-7-4",
    "nist-measure-2-11",
)

FOUR_FIFTHS_THRESHOLD = 0.8

DEFAULT_METRICS_TO_COMPUTE = ("selection-rate", "impact-ratio")

GROUND_TRUTH_REQUIRED_METRICS = (
    "equalized-odds-difference",
    "predictive-parity-difference",
)

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily so
# basic evaluations (enrich_with_crosswalk=False) pay no import cost and
# are not affected by crosswalk-side load failures.
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

    sysd = inputs["system_description"]
    if not isinstance(sysd, dict):
        raise ValueError("system_description must be a dict")

    eval_data = inputs["evaluation_data"]
    if not isinstance(eval_data, dict):
        raise ValueError("evaluation_data must be a dict")
    if "per_group_counts" not in eval_data or not isinstance(eval_data["per_group_counts"], dict):
        raise ValueError("evaluation_data.per_group_counts must be a dict")

    pa = inputs["protected_attributes"]
    if not isinstance(pa, list) or not pa:
        raise ValueError("protected_attributes must be a non-empty list of attribute dicts")
    for entry in pa:
        if not isinstance(entry, dict) or "attribute_name" not in entry:
            raise ValueError("each protected_attributes entry must be a dict with 'attribute_name'")

    metrics = inputs.get("metrics_to_compute", list(DEFAULT_METRICS_TO_COMPUTE))
    if not isinstance(metrics, list):
        raise ValueError("metrics_to_compute, when provided, must be a list")
    for m in metrics:
        if m not in VALID_METRICS:
            raise ValueError(
                f"metric {m!r} not in VALID_METRICS={list(VALID_METRICS)}"
            )

    rules = inputs.get("jurisdiction_rules", [])
    if not isinstance(rules, list):
        raise ValueError("jurisdiction_rules, when provided, must be a list")
    for r in rules:
        if r not in VALID_JURISDICTION_RULES:
            raise ValueError(
                f"jurisdiction_rule {r!r} not in VALID_JURISDICTION_RULES="
                f"{list(VALID_JURISDICTION_RULES)}"
            )

    inter = inputs.get("intersectional_analysis", False)
    if not isinstance(inter, bool):
        raise ValueError("intersectional_analysis, when provided, must be a bool")

    org_thresh = inputs.get("organizational_thresholds", {})
    if not isinstance(org_thresh, dict):
        raise ValueError("organizational_thresholds, when provided, must be a dict")

    min_size = inputs.get("minimum_group_size", 30)
    if not isinstance(min_size, int) or min_size < 1:
        raise ValueError("minimum_group_size must be a positive integer")

    enrich = inputs.get("enrich_with_crosswalk", True)
    if not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")


def _selection_rate(counts: dict[str, Any]) -> float | None:
    total = counts.get("total")
    selected = counts.get("selected")
    if total is None or selected is None or total == 0:
        return None
    return round(selected / total, 6)


def _tpr(counts: dict[str, Any]) -> float | None:
    tp = counts.get("true_positive")
    fn = counts.get("false_negative")
    if tp is None or fn is None or (tp + fn) == 0:
        return None
    return round(tp / (tp + fn), 6)


def _fpr(counts: dict[str, Any]) -> float | None:
    fp = counts.get("false_positive")
    tn = counts.get("true_negative")
    if fp is None or tn is None or (fp + tn) == 0:
        return None
    return round(fp / (fp + tn), 6)


def _ppv(counts: dict[str, Any]) -> float | None:
    """Positive predictive value. Prefer caller-supplied PPV; else compute."""
    if counts.get("positive_predictive_value") is not None:
        return round(float(counts["positive_predictive_value"]), 6)
    tp = counts.get("true_positive")
    fp = counts.get("false_positive")
    if tp is None or fp is None or (tp + fp) == 0:
        return None
    return round(tp / (tp + fp), 6)


def _is_intersectional_key(group_key: str) -> bool:
    """A compound group key contains '|' separating attribute:value pairs."""
    return "|" in group_key


def _per_metric_selection_rate(per_group_counts: dict[str, dict[str, Any]],
                               keys: list[str]) -> dict[str, Any]:
    rates: dict[str, float | None] = {}
    for k in keys:
        rates[k] = _selection_rate(per_group_counts[k])
    return {
        "metric": "selection-rate",
        "per_group": rates,
        "citation": "NIST AI RMF, MEASURE 2.11",
    }


def _per_metric_impact_ratio(per_group_counts: dict[str, dict[str, Any]],
                             keys: list[str]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    rates = [_selection_rate(per_group_counts[k]) for k in keys]
    valid = [r for r in rates if r is not None]
    if len(valid) < 2:
        return (
            {
                "metric": "impact-ratio",
                "value": None,
                "status": "insufficient-groups",
                "citation": "NYC LL144 Final Rule, Section 5-301",
            },
            ["Impact ratio requires at least two groups with computable selection rates."],
        )
    rate_max = max(valid)
    rate_min = min(valid)
    if rate_max == 0:
        warnings.append(
            "Impact ratio undefined: max selection rate is 0 across groups; "
            "no group was selected."
        )
        return (
            {
                "metric": "impact-ratio",
                "value": None,
                "status": "undefined-division-by-zero",
                "citation": "NYC LL144 Final Rule, Section 5-301",
            },
            warnings,
        )
    value = round(rate_min / rate_max, 6)
    return (
        {
            "metric": "impact-ratio",
            "value": value,
            "selection_rate_max": rate_max,
            "selection_rate_min": rate_min,
            "citation": "NYC LL144 Final Rule, Section 5-301",
        },
        warnings,
    )


def _per_metric_demographic_parity(per_group_counts: dict[str, dict[str, Any]],
                                   keys: list[str],
                                   absolute: bool) -> dict[str, Any]:
    rates = [_selection_rate(per_group_counts[k]) for k in keys]
    valid = [(k, r) for k, r in zip(keys, rates) if r is not None]
    if len(valid) < 2:
        return {
            "metric": "demographic-parity-difference" if not absolute else "statistical-parity-difference",
            "value": None,
            "status": "insufficient-groups",
            "citation": "NIST AI RMF, MEASURE 2.11",
        }
    pairs = list(combinations(valid, 2))
    diffs = [abs(a[1] - b[1]) for a, b in pairs] if absolute else [a[1] - b[1] for a, b in pairs]
    return {
        "metric": "demographic-parity-difference" if not absolute else "statistical-parity-difference",
        "value": round(max(abs(d) for d in diffs), 6),
        "max_pair": _name_max_pair(pairs, absolute),
        "citation": "NIST AI RMF, MEASURE 2.11",
    }


def _name_max_pair(pairs, absolute: bool) -> dict[str, Any]:
    best = None
    best_d = -1.0
    for a, b in pairs:
        d = abs(a[1] - b[1]) if absolute else (a[1] - b[1])
        if abs(d) > best_d:
            best_d = abs(d)
            best = (a, b)
    if best is None:
        return {}
    a, b = best
    return {"group_a": a[0], "rate_a": a[1], "group_b": b[0], "rate_b": b[1]}


def _per_metric_equalized_odds(per_group_counts: dict[str, dict[str, Any]],
                               keys: list[str]) -> dict[str, Any]:
    tprs = [(k, _tpr(per_group_counts[k])) for k in keys]
    fprs = [(k, _fpr(per_group_counts[k])) for k in keys]
    valid_tpr = [t for t in tprs if t[1] is not None]
    valid_fpr = [f for f in fprs if f[1] is not None]
    if len(valid_tpr) < 2 or len(valid_fpr) < 2:
        return {
            "metric": "equalized-odds-difference",
            "value": None,
            "status": "insufficient-groups",
            "citation": "NIST AI RMF, MEASURE 2.11",
        }
    tpr_max_diff = max(abs(a[1] - b[1]) for a, b in combinations(valid_tpr, 2))
    fpr_max_diff = max(abs(a[1] - b[1]) for a, b in combinations(valid_fpr, 2))
    return {
        "metric": "equalized-odds-difference",
        "value": round(max(tpr_max_diff, fpr_max_diff), 6),
        "tpr_max_difference": round(tpr_max_diff, 6),
        "fpr_max_difference": round(fpr_max_diff, 6),
        "per_group_tpr": dict(tprs),
        "per_group_fpr": dict(fprs),
        "citation": "NIST AI RMF, MEASURE 2.11",
    }


def _per_metric_predictive_parity(per_group_counts: dict[str, dict[str, Any]],
                                  keys: list[str]) -> dict[str, Any]:
    ppvs = [(k, _ppv(per_group_counts[k])) for k in keys]
    valid = [p for p in ppvs if p[1] is not None]
    if len(valid) < 2:
        return {
            "metric": "predictive-parity-difference",
            "value": None,
            "status": "insufficient-groups",
            "citation": "NIST AI RMF, MEASURE 2.11",
        }
    max_diff = max(abs(a[1] - b[1]) for a, b in combinations(valid, 2))
    return {
        "metric": "predictive-parity-difference",
        "value": round(max_diff, 6),
        "per_group_ppv": dict(ppvs),
        "citation": "NIST AI RMF, MEASURE 2.11",
    }


def _compute_metric(metric: str,
                    per_group_counts: dict[str, dict[str, Any]],
                    keys: list[str],
                    ground_truth_available: bool) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []

    if metric in GROUND_TRUTH_REQUIRED_METRICS and not ground_truth_available:
        warnings.append(
            f"Metric {metric!r} requires ground truth (true_positive, "
            "false_positive, false_negative, true_negative) but "
            "evaluation_data.ground_truth_available is False; not computed."
        )
        return (
            {
                "metric": metric,
                "value": None,
                "status": "requires-ground-truth",
                "citation": "NIST AI RMF, MEASURE 2.11",
            },
            warnings,
        )

    if metric == "selection-rate":
        return _per_metric_selection_rate(per_group_counts, keys), warnings
    if metric == "impact-ratio":
        result, w = _per_metric_impact_ratio(per_group_counts, keys)
        return result, warnings + w
    if metric == "demographic-parity-difference":
        return _per_metric_demographic_parity(per_group_counts, keys, absolute=False), warnings
    if metric == "statistical-parity-difference":
        return _per_metric_demographic_parity(per_group_counts, keys, absolute=True), warnings
    if metric == "equalized-odds-difference":
        return _per_metric_equalized_odds(per_group_counts, keys), warnings
    if metric == "predictive-parity-difference":
        return _per_metric_predictive_parity(per_group_counts, keys), warnings
    raise ValueError(f"Unknown metric {metric!r}")


def _split_groups(per_group_counts: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Return (single_attribute_keys, intersectional_keys)."""
    single: list[str] = []
    inter: list[str] = []
    for k in per_group_counts:
        if _is_intersectional_key(k):
            inter.append(k)
        else:
            single.append(k)
    return single, inter


def _underpowered(per_group_counts: dict[str, dict[str, Any]],
                  minimum_group_size: int) -> tuple[list[dict[str, Any]], list[str]]:
    flagged: list[dict[str, Any]] = []
    warnings: list[str] = []
    for k, counts in per_group_counts.items():
        n = counts.get("total") or 0
        if n < minimum_group_size:
            flagged.append({"group_key": k, "total": n, "threshold": minimum_group_size})
            warnings.append(
                f"Group {k!r} has N={n} (below minimum_group_size="
                f"{minimum_group_size}); metric unreliable."
            )
    return flagged, warnings


def _rule_finding_nyc(impact_ratio_result: dict[str, Any] | None) -> dict[str, Any]:
    citation = "NYC LL144 Final Rule, Section 5-301"
    if impact_ratio_result is None or impact_ratio_result.get("value") is None:
        return {
            "rule": "nyc-ll144-4-5ths",
            "status": "not-computable",
            "computed_metric": None,
            "threshold_used": FOUR_FIFTHS_THRESHOLD,
            "citation": citation,
            "rationale": "Impact ratio not computable from supplied data; cannot evaluate the four-fifths rule.",
        }
    value = impact_ratio_result["value"]
    passed = value >= FOUR_FIFTHS_THRESHOLD
    return {
        "rule": "nyc-ll144-4-5ths",
        "status": "pass" if passed else "fail-disparate-impact-concern",
        "computed_metric": value,
        "threshold_used": FOUR_FIFTHS_THRESHOLD,
        "citation": citation,
        "rationale": (
            f"Impact ratio {value} {'meets' if passed else 'is below'} the "
            f"four-fifths threshold of {FOUR_FIFTHS_THRESHOLD}."
        ),
    }


def _rule_finding_eu_art_10_4(per_metric_results: list[dict[str, Any]],
                              org_thresholds: dict[str, float],
                              evaluation_data: dict[str, Any]) -> dict[str, Any]:
    citation = "EU AI Act, Article 10, Paragraph 4"
    bias_examined = any(
        r.get("metric") in (
            "demographic-parity-difference",
            "statistical-parity-difference",
            "equalized-odds-difference",
            "predictive-parity-difference",
            "impact-ratio",
        ) and r.get("value") is not None
        for r in per_metric_results
    )
    evidence_ref = evaluation_data.get("dataset_ref") or evaluation_data.get("evaluation_date")
    threshold_status = None
    threshold_metric = None
    threshold_value = None
    threshold_used = None
    for metric_name, threshold in org_thresholds.items():
        for r in per_metric_results:
            if r.get("metric") == metric_name and r.get("value") is not None:
                threshold_metric = metric_name
                threshold_value = r["value"]
                threshold_used = threshold
                threshold_status = (
                    "within-organizational-threshold"
                    if r["value"] <= threshold
                    else "concern-exceeds-organizational-threshold"
                )
                break
        if threshold_status is not None:
            break

    return {
        "rule": "eu-ai-act-art-10-4",
        "status": "examined" if bias_examined else "not-examined",
        "computed_metric": threshold_metric,
        "computed_value": threshold_value,
        "threshold_used": threshold_used,
        "organizational_threshold_status": threshold_status,
        "evidence_ref": evidence_ref,
        "citation": citation,
        "rationale": (
            "Bias examination performed; at least one bias metric computed against the supplied evaluation data."
            if bias_examined
            else "No bias metric was computable. Article 10(4) requires examination."
        ),
    }


def _rule_finding_colorado(per_metric_results: list[dict[str, Any]]) -> dict[str, Any]:
    citation = "Colorado SB 205, Section 6-1-1702(1)"
    has_evaluation = any(r.get("value") is not None for r in per_metric_results)
    if has_evaluation:
        status = "reasonable-care-documented"
        rationale = (
            "Bias evaluation present in record; documents the developer or "
            "deployer duty of reasonable care under Section 6-1-1702(1)."
        )
    else:
        status = "reasonable-care-not-documented"
        rationale = (
            "No bias metric computed. Colorado SB 205 Section 6-1-1702(1) "
            "establishes a duty of reasonable care to protect against "
            "algorithmic discrimination; document an evaluation."
        )
    return {
        "rule": "colorado-sb-205-reasonable-care",
        "status": status,
        "computed_metric": None,
        "threshold_used": None,
        "citation": citation,
        "rationale": rationale,
    }


def _rule_finding_singapore() -> dict[str, Any]:
    citation = "MAS Veritas (2022)"
    next_steps = [
        "Confirm context-aware metric selection per Veritas Document 1: Fairness; "
        "the appropriate fairness metric depends on the use-case harm profile.",
        "Verify the evaluation dataset is balanced across protected groups, "
        "or document the rationale and limitations of an unbalanced sample.",
        "Subject the evaluation results to independent internal validation "
        "before relying on them for deployment decisions.",
        "Map computed metrics to the MAS FEAT Principles (2018), Principle "
        "Fairness commitments documented for the system.",
    ]
    return {
        "rule": "singapore-veritas-fairness",
        "status": "next-steps-emitted",
        "computed_metric": None,
        "threshold_used": None,
        "citation": citation,
        "rationale": "Singapore MAS Veritas methodology recommends iterative, context-aware fairness assessment.",
        "next_steps": next_steps,
    }


def _rule_finding_iso_a_7_4(per_metric_results: list[dict[str, Any]]) -> dict[str, Any]:
    citation = "ISO/IEC 42001:2023, Annex A, Control A.7.4"
    has_evaluation = any(r.get("value") is not None for r in per_metric_results)
    return {
        "rule": "iso-42001-a-7-4",
        "status": "data-quality-evidence-present" if has_evaluation else "data-quality-evidence-absent",
        "computed_metric": None,
        "threshold_used": None,
        "citation": citation,
        "rationale": (
            "Bias metrics serve as data-quality evidence under A.7.4; "
            "ISO/IEC TR 24027:2021 is the advisory technical report on bias in AI systems."
        ),
    }


def _rule_finding_nist_measure_2_11(per_metric_results: list[dict[str, Any]]) -> dict[str, Any]:
    citation = "NIST AI RMF, MEASURE 2.11"
    has_evaluation = any(r.get("value") is not None for r in per_metric_results)
    return {
        "rule": "nist-measure-2-11",
        "status": "evaluated" if has_evaluation else "not-evaluated",
        "computed_metric": None,
        "threshold_used": None,
        "citation": citation,
        "rationale": (
            "MEASURE 2.11 requires fairness and bias to be evaluated and documented."
            if has_evaluation
            else "No bias metric was computed. MEASURE 2.11 requires fairness evaluation."
        ),
    }


def _apply_jurisdictional_rules(
    rules: list[str],
    per_metric_results: list[dict[str, Any]],
    org_thresholds: dict[str, float],
    evaluation_data: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    findings: list[dict[str, Any]] = []
    citations: list[str] = []
    impact_ratio = next(
        (r for r in per_metric_results if r.get("metric") == "impact-ratio"),
        None,
    )
    for rule in rules:
        if rule == "nyc-ll144-4-5ths":
            findings.append(_rule_finding_nyc(impact_ratio))
            citations.extend(["NYC LL144", "NYC LL144 Final Rule, Section 5-301"])
            citations.append("NYC DCWP AEDT Rules, 6 RCNY Section 5-301(b)")
        elif rule == "eu-ai-act-art-10-4":
            findings.append(_rule_finding_eu_art_10_4(per_metric_results, org_thresholds, evaluation_data))
            citations.append("EU AI Act, Article 10, Paragraph 4")
        elif rule == "colorado-sb-205-reasonable-care":
            findings.append(_rule_finding_colorado(per_metric_results))
            citations.append("Colorado SB 205, Section 6-1-1702(1)")
        elif rule == "singapore-veritas-fairness":
            findings.append(_rule_finding_singapore())
            citations.append("MAS Veritas (2022)")
        elif rule == "iso-42001-a-7-4":
            findings.append(_rule_finding_iso_a_7_4(per_metric_results))
            citations.append("ISO/IEC 42001:2023, Annex A, Control A.7.4")
            citations.append("ISO/IEC TR 24027:2021")
        elif rule == "nist-measure-2-11":
            findings.append(_rule_finding_nist_measure_2_11(per_metric_results))
            citations.append("NIST AI RMF, MEASURE 2.11")
    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for c in citations:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    return findings, deduped


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enrich_with_crosswalk() -> tuple[list[dict[str, Any]], list[str]]:
    """Return (cross_framework_citations, warnings).

    Bias evaluation anchors on NIST MEASURE 2.11 and ISO A.7.4. Returns a
    short list of mappings into commonly-requested target frameworks.
    """
    try:
        crosswalk = _load_crosswalk_module()
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return ([], [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"])

    interesting_anchors = {("iso42001", "A.7.4"), ("nist-ai-rmf", "MEASURE 2.11")}
    citations: list[dict[str, Any]] = []
    for m in data.get("mappings", []):
        if (m.get("source_framework"), m.get("source_ref")) in interesting_anchors:
            citations.append({
                "source_framework": m.get("source_framework"),
                "source_ref": m.get("source_ref"),
                "target_framework": m.get("target_framework"),
                "target_ref": m.get("target_ref"),
                "relationship": m.get("relationship"),
                "confidence": m.get("confidence"),
            })
    return citations, []


def evaluate_bias(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate bias and fairness metrics across protected-attribute groups.

    Args:
        inputs: dict containing:
            system_description (required): dict describing the system, with
                a 'sector' field where employment-context disparate-impact
                thresholds apply.
            evaluation_data (required): dict with dataset_ref,
                evaluation_date, sample_size, ground_truth_available (bool),
                and per_group_counts mapping group_key (e.g.
                "race:black|sex:female") to count dicts.
            protected_attributes (required): list of attribute dicts
                {attribute_name, categories_present (list)}.
            metrics_to_compute (optional): list from VALID_METRICS.
                Defaults to ["selection-rate", "impact-ratio"].
            jurisdiction_rules (optional): list from VALID_JURISDICTION_RULES.
                Defaults to [].
            intersectional_analysis (optional, default False): if True,
                separately compute metrics on compound-attribute group keys
                (those containing '|').
            organizational_thresholds (optional, default {}): dict mapping
                metric -> threshold for EU Art 10(4) organizational status.
            minimum_group_size (optional, default 30): groups with fewer
                than this many records are flagged underpowered.
            enrich_with_crosswalk (optional, default True).
            reviewed_by (optional).

    Returns:
        dict with timestamp, agent_signature, framework, system and
        evaluation echoes, per_metric_results, intersectional_results
        (if enabled), rule_findings, underpowered_groups, citations,
        warnings, summary, cross_framework_citations (if enriched),
        reviewed_by.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    sysd = inputs["system_description"]
    eval_data = inputs["evaluation_data"]
    protected_attributes = inputs["protected_attributes"]
    metrics = list(inputs.get("metrics_to_compute") or DEFAULT_METRICS_TO_COMPUTE)
    rules = list(inputs.get("jurisdiction_rules") or [])
    intersectional = bool(inputs.get("intersectional_analysis", False))
    org_thresholds = dict(inputs.get("organizational_thresholds") or {})
    minimum_group_size = int(inputs.get("minimum_group_size", 30))
    enrich = bool(inputs.get("enrich_with_crosswalk", True))
    ground_truth_available = bool(eval_data.get("ground_truth_available", False))

    per_group_counts = eval_data["per_group_counts"]
    single_keys, intersectional_keys = _split_groups(per_group_counts)

    warnings: list[str] = []

    # Underpowered groups across all keys.
    underpowered, underpowered_warnings = _underpowered(per_group_counts, minimum_group_size)
    warnings.extend(underpowered_warnings)

    # Per-metric computation on single-attribute groups.
    per_metric_results: list[dict[str, Any]] = []
    for metric in metrics:
        result, w = _compute_metric(metric, per_group_counts, single_keys, ground_truth_available)
        per_metric_results.append(result)
        warnings.extend(w)

    # Intersectional analysis. Separate result block; small-group warnings
    # surface automatically for any compound bucket below threshold.
    intersectional_results: list[dict[str, Any]] | None = None
    if intersectional:
        if not intersectional_keys:
            warnings.append(
                "intersectional_analysis=True but no compound group keys "
                "(containing '|') were supplied in per_group_counts."
            )
            intersectional_results = []
        else:
            intersectional_results = []
            for metric in metrics:
                result, w = _compute_metric(metric, per_group_counts, intersectional_keys, ground_truth_available)
                intersectional_results.append(result)
                warnings.extend(w)

    # Jurisdictional rules application against the single-attribute results
    # (the canonical surface).
    rule_findings, rule_citations = _apply_jurisdictional_rules(
        rules, per_metric_results, org_thresholds, eval_data
    )

    # Top-level citations: anchor metric citations + jurisdictional
    # citations. Always include MEASURE 2.11 and A.7.4 as anchors.
    citations: list[str] = [
        "NIST AI RMF, MEASURE 2.11",
        "ISO/IEC 42001:2023, Annex A, Control A.7.4",
        "ISO/IEC TR 24027:2021",
    ]
    for c in rule_citations:
        if c not in citations:
            citations.append(c)

    # Non-high-risk advisory note when sector is supplied and is not in the
    # known high-risk employment family. Bias evaluation remains
    # recommended even when not statutorily mandated.
    sector = (sysd.get("sector") or "").lower()
    if sector and sector not in ("employment", "hr", "hiring", "credit", "lending", "insurance", "education", "healthcare"):
        warnings.append(
            f"System sector {sector!r} is not within the canonical high-risk "
            "employment, credit, insurance, healthcare, or education families. "
            "Bias evaluation is recommended-not-mandated for this sector."
        )

    cross_framework_citations: list[dict[str, Any]] | None = None
    if enrich:
        enriched, enrich_warnings = _enrich_with_crosswalk()
        warnings.extend(enrich_warnings)
        cross_framework_citations = enriched

    summary = {
        "metrics_computed": [r["metric"] for r in per_metric_results],
        "metrics_with_value": [r["metric"] for r in per_metric_results if r.get("value") is not None or r.get("per_group")],
        "intersectional": intersectional,
        "intersectional_metrics_computed": (
            [r["metric"] for r in (intersectional_results or [])]
            if intersectional_results is not None
            else []
        ),
        "rules_applied": rules,
        "rule_findings_count": len(rule_findings),
        "underpowered_group_count": len(underpowered),
        "warnings_count": len(warnings),
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "nist,eu-ai-act,usa-nyc,usa-co,singapore,iso42001",
        "system_description_echo": sysd,
        "evaluation_data_echo": {
            k: v for k, v in eval_data.items() if k != "per_group_counts"
        },
        "protected_attributes_echo": protected_attributes,
        "per_metric_results": per_metric_results,
        "intersectional_results": intersectional_results,
        "rule_findings": rule_findings,
        "underpowered_groups": underpowered,
        "citations": citations,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": inputs.get("reviewed_by"),
    }
    if cross_framework_citations is not None:
        output["cross_framework_citations"] = cross_framework_citations
    return output


def render_markdown(report: dict[str, Any]) -> str:
    """Render a bias evaluation report as Markdown."""
    required = (
        "timestamp",
        "agent_signature",
        "system_description_echo",
        "per_metric_results",
        "rule_findings",
        "citations",
        "summary",
    )
    missing = [k for k in required if k not in report]
    if missing:
        raise ValueError(f"report missing required fields: {missing}")

    sysd = report["system_description_echo"]
    name = sysd.get("system_name", "AI system")

    lines = [
        f"# Bias Evaluation Report: {name}",
        "",
        f"**Generated at (UTC):** {report['timestamp']}",
        f"**Generated by:** {report['agent_signature']}",
        f"**Framework coverage:** {report.get('framework', '')}",
    ]
    if report.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {report['reviewed_by']}")

    summary = report["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Metrics computed: {', '.join(summary.get('metrics_computed', [])) or 'none'}",
        f"- Intersectional analysis: {summary.get('intersectional', False)}",
        f"- Jurisdictional rules applied: {', '.join(summary.get('rules_applied', [])) or 'none'}",
        f"- Rule findings: {summary.get('rule_findings_count', 0)}",
        f"- Underpowered groups: {summary.get('underpowered_group_count', 0)}",
        f"- Warnings: {summary.get('warnings_count', 0)}",
        "",
        "## Applicable citations",
        "",
    ])
    for c in report["citations"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Per-metric results", ""])
    for r in report["per_metric_results"]:
        lines.append(f"### {r.get('metric')}")
        lines.append("")
        if r.get("status") in ("requires-ground-truth", "insufficient-groups", "undefined-division-by-zero", "not-computable"):
            lines.append(f"- Status: {r['status']}")
        if "per_group" in r:
            lines.append("")
            lines.append("| Group | Selection rate |")
            lines.append("|---|---|")
            for g, v in r["per_group"].items():
                lines.append(f"| {g} | {v if v is not None else 'undefined'} |")
        elif "value" in r:
            lines.append(f"- Value: {r.get('value')}")
            if r.get("max_pair"):
                mp = r["max_pair"]
                lines.append(
                    f"- Max-difference pair: {mp.get('group_a')} ({mp.get('rate_a')}) "
                    f"vs {mp.get('group_b')} ({mp.get('rate_b')})"
                )
        lines.append(f"- Citation: {r.get('citation')}")
        lines.append("")

    if report.get("intersectional_results") is not None:
        lines.extend(["## Intersectional results", ""])
        if not report["intersectional_results"]:
            lines.append("_No compound-attribute group keys supplied._")
            lines.append("")
        for r in report["intersectional_results"]:
            lines.append(f"### intersectional / {r.get('metric')}")
            lines.append("")
            if "value" in r:
                lines.append(f"- Value: {r.get('value')}")
            if "per_group" in r:
                lines.append("")
                lines.append("| Group | Selection rate |")
                lines.append("|---|---|")
                for g, v in r["per_group"].items():
                    lines.append(f"| {g} | {v if v is not None else 'undefined'} |")
            lines.append(f"- Citation: {r.get('citation')}")
            lines.append("")

    lines.extend(["## Rule findings", ""])
    if not report["rule_findings"]:
        lines.append("_No jurisdictional rules applied._")
        lines.append("")
    for f in report["rule_findings"]:
        lines.append(f"### {f.get('rule')}")
        lines.append("")
        lines.append(f"- Status: {f.get('status')}")
        if f.get("computed_metric") is not None:
            lines.append(f"- Computed metric: {f.get('computed_metric')}")
        if f.get("threshold_used") is not None:
            lines.append(f"- Threshold used: {f.get('threshold_used')}")
        lines.append(f"- Citation: {f.get('citation')}")
        lines.append(f"- Rationale: {f.get('rationale')}")
        if f.get("next_steps"):
            lines.append("- Next steps:")
            for s in f["next_steps"]:
                lines.append(f"  - {s}")
        lines.append("")

    if report.get("underpowered_groups"):
        lines.extend(["## Underpowered groups", ""])
        lines.append("| Group key | Total | Threshold |")
        lines.append("|---|---|---|")
        for g in report["underpowered_groups"]:
            lines.append(f"| {g['group_key']} | {g['total']} | {g['threshold']} |")
        lines.append("")

    if report.get("warnings"):
        lines.extend(["## Warnings", ""])
        for w in report["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    if report.get("cross_framework_citations"):
        lines.extend(["## Cross-framework citations", ""])
        for entry in report["cross_framework_citations"]:
            lines.append(
                f"- {entry.get('source_framework')} {entry.get('source_ref')} "
                f"-> {entry.get('target_framework')} {entry.get('target_ref')} "
                f"({entry.get('relationship')})"
            )
        lines.append("")

    return "\n".join(lines)


def render_csv(report: dict[str, Any]) -> str:
    """One row per per_metric_results entry. Header included.

    Columns: metric, value, status, per_group_summary, citation.
    """
    if "per_metric_results" not in report:
        raise ValueError("report missing 'per_metric_results' field")

    header = "metric,value,status,per_group_summary,citation"
    lines = [header]
    for r in report["per_metric_results"]:
        metric = r.get("metric", "")
        value = r.get("value")
        status = r.get("status", "")
        per_group = r.get("per_group")
        if per_group:
            per_group_summary = "; ".join(
                f"{k}={v if v is not None else 'undefined'}"
                for k, v in per_group.items()
            )
        else:
            per_group_summary = ""
        citation = r.get("citation", "")
        lines.append(",".join([
            _csv_escape(str(metric)),
            _csv_escape("" if value is None else str(value)),
            _csv_escape(str(status)),
            _csv_escape(per_group_summary),
            _csv_escape(citation),
        ]))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
