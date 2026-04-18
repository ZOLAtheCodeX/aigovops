"""
AIGovOps: Trustworthy-AI Metrics Collector Plugin

Aggregates, validates, and cites NIST AI RMF 1.0 MEASURE 2.x metric
families with optional AI 600-1 (Generative AI Profile) overlay. Emits
KPI records with subcategory citations and routes threshold breaches to
downstream governance workflows (risk-register, nonconformity-tracker).

This plugin operationalizes the NIST-distinctive Tier 1 items T1.2
(technical performance and safety measurement) and T1.6 (privacy and
fairness metrics) from the nist-ai-rmf skill. Also serves iso42001
Clause 9.1 monitoring and measurement when framework='iso42001' or
'dual' is set.

Design stance: the plugin does NOT compute metrics. Metric computation
is the MLOps pipeline's responsibility. The plugin validates
precomputed measurement values against a metric catalog, enforces that
every measurement carries a measurement_method_ref and test_set_ref
where applicable, attaches the correct MEASURE subcategory citations,
applies threshold checks from organizational policy, and emits KPI
records for dashboard consumption and routing hooks for breach-driven
downstream workflows.

Status: Phase 3 minimum-viable implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "metrics-collector/0.1.0"

# Default MEASURE 2.x metric catalog. Every family maps to at least one
# NIST subcategory citation; privacy and fairness families are iso42001
# T1.6 / NIST MEASURE 2.9 and 2.10. Organizations extend this catalog
# per their MLOps stack; the schema is stable.
DEFAULT_METRIC_CATALOG: dict[str, dict[str, Any]] = {
    "validity-reliability": {
        "metrics": ("f1", "precision", "recall", "calibration_ece", "coverage_at_threshold"),
        "measure_subcategories": ("MEASURE 2.5", "MEASURE 2.1"),
        "requires_test_set": True,
    },
    "in-context-performance": {
        "metrics": ("production_accuracy", "latency_p95_ms", "throughput_rps", "error_rate"),
        "measure_subcategories": ("MEASURE 2.3",),
        "requires_test_set": False,
    },
    "safety": {
        "metrics": ("refusal_rate", "safety_filter_fp", "safety_filter_fn", "incident_count",
                    "time_to_detect_seconds", "time_to_mitigate_seconds"),
        "measure_subcategories": ("MEASURE 2.6",),
        "requires_test_set": False,
    },
    "security-resilience": {
        "metrics": ("adversarial_robustness", "auth_bypass_rate", "cve_count", "mean_time_to_patch_days"),
        "measure_subcategories": ("MEASURE 2.7",),
        "requires_test_set": False,
    },
    "explainability": {
        "metrics": ("explanation_coverage", "explanation_fidelity"),
        "measure_subcategories": ("MEASURE 2.8",),
        "requires_test_set": False,
    },
    "privacy": {
        "metrics": ("training_data_exposure", "membership_inference_risk",
                    "attribute_inference_risk", "pii_in_outputs_rate"),
        "measure_subcategories": ("MEASURE 2.9",),
        "requires_test_set": True,
    },
    "fairness": {
        "metrics": ("demographic_parity_difference", "equal_opportunity_difference",
                    "calibration_parity", "representational_harm_rate"),
        "measure_subcategories": ("MEASURE 2.10",),
        "requires_test_set": True,
    },
    "environmental": {
        "metrics": ("kwh_per_inference", "gco2eq_per_inference", "training_kwh"),
        "measure_subcategories": ("MEASURE 2.11",),
        "requires_test_set": False,
    },
    "computational-efficiency": {
        "metrics": ("inference_cost_usd_per_1k", "p99_latency_ms"),
        "measure_subcategories": ("MEASURE 2.12",),
        "requires_test_set": False,
    },
}

# AI 600-1 Generative AI Profile overlay. Applied when any system in
# scope carries system_type: generative-ai. Overlay adds metric
# families specific to generative AI risks; existing families (safety,
# privacy) may gain additional metrics within them.
GENAI_OVERLAY_FAMILIES: dict[str, dict[str, Any]] = {
    "confabulation": {
        "metrics": ("hallucination_rate", "source_attribution_accuracy"),
        "measure_subcategories": ("MEASURE 2.6 (AI 600-1 overlay)",),
        "requires_test_set": True,
    },
    "data-regurgitation": {
        "metrics": ("exact_match_regurgitation_rate", "near_match_regurgitation_rate"),
        "measure_subcategories": ("MEASURE 2.9 (AI 600-1 overlay)",),
        "requires_test_set": True,
    },
    "abusive-content": {
        "metrics": ("policy_violation_rate", "known_harmful_content_false_negative_rate"),
        "measure_subcategories": ("MEASURE 2.6 (AI 600-1 overlay)",),
        "requires_test_set": True,
    },
    "information-integrity": {
        "metrics": ("synthetic_labeling_compliance", "provenance_signal_attachment_rate"),
        "measure_subcategories": ("MEASURE 2.8 (AI 600-1 overlay)",),
        "requires_test_set": False,
    },
    "ip-risk": {
        "metrics": ("uncleared_content_reproduction_rate",),
        "measure_subcategories": ("MEASURE 2.6 (AI 600-1 overlay)",),
        "requires_test_set": True,
    },
    "value-chain-integrity": {
        "metrics": ("foundation_model_provenance_documented", "pretrained_model_risk_posture"),
        "measure_subcategories": ("MANAGE 3.2 (AI 600-1 overlay)",),
        "requires_test_set": False,
    },
}

VALID_FRAMEWORKS = ("iso42001", "nist", "dual")
VALID_THRESHOLD_OPERATORS = ("max", "min", "range")

REQUIRED_INPUT_FIELDS = ("ai_system_inventory", "measurements")
REQUIRED_MEASUREMENT_FIELDS = (
    "system_ref",
    "metric_family",
    "metric_id",
    "value",
    "window_start",
    "window_end",
)


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    inv = inputs["ai_system_inventory"]
    if not isinstance(inv, list) or not all(
        isinstance(s, dict) and "system_ref" in s and "system_name" in s for s in inv
    ):
        raise ValueError(
            "ai_system_inventory must be a list of dicts each with 'system_ref' and 'system_name'"
        )

    measurements = inputs["measurements"]
    if not isinstance(measurements, list):
        raise ValueError("measurements must be a list")
    for i, m in enumerate(measurements):
        if not isinstance(m, dict):
            raise ValueError(f"measurements[{i}] must be a dict")
        m_missing = [f for f in REQUIRED_MEASUREMENT_FIELDS if f not in m]
        if m_missing:
            raise ValueError(
                f"measurements[{i}] missing required fields {sorted(m_missing)}"
            )

    framework = inputs.get("framework", "nist")
    if framework not in VALID_FRAMEWORKS:
        raise ValueError(f"framework must be one of {VALID_FRAMEWORKS}; got {framework!r}")

    thresholds = inputs.get("thresholds") or {}
    if not isinstance(thresholds, dict):
        raise ValueError("thresholds must be a dict mapping metric_id to threshold spec")
    for metric_id, spec in thresholds.items():
        if not isinstance(spec, dict) or "operator" not in spec:
            raise ValueError(f"threshold for {metric_id!r} must be a dict with 'operator'")
        if spec["operator"] not in VALID_THRESHOLD_OPERATORS:
            raise ValueError(
                f"threshold for {metric_id!r} has invalid operator {spec['operator']!r}; "
                f"must be one of {VALID_THRESHOLD_OPERATORS}"
            )
        if spec["operator"] == "range":
            if "range" not in spec or not isinstance(spec["range"], (list, tuple)) or len(spec["range"]) != 2:
                raise ValueError(f"threshold for {metric_id!r} with operator 'range' requires 'range': [lo, hi]")
        else:
            if "value" not in spec:
                raise ValueError(f"threshold for {metric_id!r} with operator {spec['operator']!r} requires 'value'")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _iso_citation_for_measure(measure_subcategory: str) -> str:
    """Return ISO 42001 Clause 9.1 citation to pair with a MEASURE subcategory for dual mode."""
    return "ISO/IEC 42001:2023, Clause 9.1"


def _compute_threshold_breach(value: Any, spec: dict[str, Any]) -> tuple[bool, str | None]:
    """Return (breached, reason). reason is None when not breached."""
    op = spec["operator"]
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False, f"threshold configured but value {value!r} is not numeric"
    if op == "max":
        limit = float(spec["value"])
        if v > limit:
            return True, f"value {v} exceeds max threshold {limit}"
    elif op == "min":
        limit = float(spec["value"])
        if v < limit:
            return True, f"value {v} is below min threshold {limit}"
    elif op == "range":
        lo, hi = float(spec["range"][0]), float(spec["range"][1])
        if v < lo:
            return True, f"value {v} is below range low {lo}"
        if v > hi:
            return True, f"value {v} is above range high {hi}"
    return False, None


def _genai_enabled(inventory: list[dict[str, Any]], explicit: bool | None) -> bool:
    if explicit is True:
        return True
    if explicit is False:
        return False
    # Auto-enable when any system is generative-ai.
    return any(s.get("system_type") == "generative-ai" for s in inventory)


def _enrich_measurement(
    measurement: dict[str, Any],
    systems_by_ref: dict[str, dict[str, Any]],
    full_catalog: dict[str, dict[str, Any]],
    thresholds: dict[str, Any],
    framework: str,
    index: int,
) -> dict[str, Any]:
    warnings: list[str] = []

    system_ref = measurement["system_ref"]
    system = systems_by_ref.get(system_ref)
    if system is None:
        warnings.append(
            f"system_ref {system_ref!r} not found in ai_system_inventory; add the system or correct the reference."
        )
        system_name = None
    else:
        system_name = system.get("system_name")

    family = measurement["metric_family"]
    metric_id = measurement["metric_id"]
    catalog_entry = full_catalog.get(family)
    if catalog_entry is None:
        warnings.append(
            f"metric_family {family!r} not in catalog. Add to the catalog or correct the family name."
        )
        citations: list[str] = []
        requires_test_set = False
    else:
        if metric_id not in catalog_entry["metrics"]:
            warnings.append(
                f"metric_id {metric_id!r} is not in the {family!r} family's metric list "
                f"{list(catalog_entry['metrics'])}."
            )
        citations = list(catalog_entry["measure_subcategories"])
        requires_test_set = catalog_entry.get("requires_test_set", False)

    if requires_test_set and not measurement.get("test_set_ref"):
        warnings.append(
            f"metric_family {family!r} requires a test_set_ref; none was provided."
        )
    if not measurement.get("measurement_method_ref"):
        warnings.append(
            "measurement_method_ref is not set. MEASURE 2.1 requires methods and metrics to be documented."
        )

    # Framework citation augmentation.
    if framework in ("iso42001", "dual"):
        if "ISO/IEC 42001:2023, Clause 9.1" not in citations:
            citations.append("ISO/IEC 42001:2023, Clause 9.1")
    # For 'nist' (default), keep just MEASURE citations.

    threshold_spec = thresholds.get(metric_id)
    threshold_breached = False
    threshold_reason: str | None = None
    if threshold_spec is not None:
        threshold_breached, threshold_reason = _compute_threshold_breach(measurement["value"], threshold_spec)
        if threshold_reason and not threshold_breached:
            warnings.append(threshold_reason)

    return {
        "id": measurement.get("id") or f"KPI-{index:04d}",
        "system_ref": system_ref,
        "system_name": system_name,
        "metric_family": family,
        "metric_id": metric_id,
        "value": measurement["value"],
        "window_start": measurement["window_start"],
        "window_end": measurement["window_end"],
        "measurement_method_ref": measurement.get("measurement_method_ref"),
        "test_set_ref": measurement.get("test_set_ref"),
        "threshold_breached": threshold_breached,
        "threshold_reason": threshold_reason,
        "citations": citations,
        "warnings": warnings,
    }


def generate_metrics_report(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and enrich a set of precomputed trustworthy-AI measurements.

    Args:
        inputs: Dict with:
            ai_system_inventory: list of dicts with system_ref, system_name,
                                 optional system_type (set to 'generative-ai'
                                 to auto-enable the AI 600-1 overlay).
            measurements: list of measurement dicts with system_ref,
                          metric_family, metric_id, value, window_start,
                          window_end, and optional measurement_method_ref,
                          test_set_ref, id.
            metric_catalog: optional dict overriding or extending
                            DEFAULT_METRIC_CATALOG.
            thresholds: optional dict mapping metric_id to
                        {operator: 'max'|'min'|'range', value: X or range: [lo, hi]}.
            genai_overlay_enabled: optional bool. When None, auto-enable
                                   if any system is system_type 'generative-ai'.
            framework: 'iso42001', 'nist' (default), or 'dual'.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, framework, overlay_applied,
        catalog_used, citations, kpi_records, v_and_v_summaries, threshold_breaches,
        warnings, summary, reviewed_by.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    framework = inputs.get("framework", "nist")
    overlay_enabled = _genai_enabled(inputs["ai_system_inventory"], inputs.get("genai_overlay_enabled"))

    full_catalog = dict(DEFAULT_METRIC_CATALOG)
    if inputs.get("metric_catalog"):
        for family, entry in inputs["metric_catalog"].items():
            full_catalog[family] = entry
    if overlay_enabled:
        for family, entry in GENAI_OVERLAY_FAMILIES.items():
            if family not in full_catalog:
                full_catalog[family] = entry

    systems_by_ref = {s["system_ref"]: s for s in inputs["ai_system_inventory"]}
    thresholds = inputs.get("thresholds") or {}

    kpi_records = [
        _enrich_measurement(m, systems_by_ref, full_catalog, thresholds, framework, i + 1)
        for i, m in enumerate(inputs["measurements"])
    ]

    # Per-system V&V summaries: which families measured, which breached.
    v_and_v_summaries: list[dict[str, Any]] = []
    systems_covered: set[str] = set()
    for system in inputs["ai_system_inventory"]:
        ref = system["system_ref"]
        system_records = [r for r in kpi_records if r["system_ref"] == ref]
        if not system_records:
            continue
        systems_covered.add(ref)
        families_measured = sorted({r["metric_family"] for r in system_records})
        breached = [r for r in system_records if r["threshold_breached"]]
        v_and_v_summaries.append({
            "system_ref": ref,
            "system_name": system.get("system_name"),
            "families_measured": families_measured,
            "total_kpi_records": len(system_records),
            "threshold_breach_count": len(breached),
            "breached_metric_ids": [r["metric_id"] for r in breached],
            "citations": (
                ["MEASURE 3.1", "MANAGE 4.1"]
                if framework in ("nist", "dual")
                else ["ISO/IEC 42001:2023, Clause 9.1"]
            ),
        })

    # Threshold-breach list is the routing hook for downstream governance workflows.
    threshold_breaches = [
        {
            "kpi_id": r["id"],
            "system_ref": r["system_ref"],
            "metric_family": r["metric_family"],
            "metric_id": r["metric_id"],
            "value": r["value"],
            "reason": r["threshold_reason"],
            "citations": r["citations"],
            "routing_recommendation": (
                "nonconformity-tracker if material; risk-register-builder for register update"
            ),
        }
        for r in kpi_records if r["threshold_breached"]
    ]

    register_warnings: list[str] = []
    if not kpi_records:
        register_warnings.append(
            "No measurements supplied. MEASURE 1.1 requires methods and metrics to be documented; "
            "with no measurements emitted, the cycle has no evidence."
        )

    top_citations: list[str] = []
    if framework in ("nist", "dual"):
        top_citations.extend(["MEASURE 1.1", "MEASURE 2.1", "MEASURE 3.1", "MEASURE 4.1"])
    if framework in ("iso42001", "dual"):
        top_citations.append("ISO/IEC 42001:2023, Clause 9.1")

    summary = {
        "total_kpi_records": len(kpi_records),
        "systems_covered": len(systems_covered),
        "systems_in_scope": len(inputs["ai_system_inventory"]),
        "families_measured": sorted({r["metric_family"] for r in kpi_records}),
        "threshold_breach_count": len(threshold_breaches),
        "records_with_warnings": sum(1 for r in kpi_records if r["warnings"]),
        "overlay_applied": overlay_enabled,
    }

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": framework,
        "overlay_applied": overlay_enabled,
        "catalog_used": sorted(full_catalog.keys()),
        "citations": top_citations,
        "kpi_records": kpi_records,
        "v_and_v_summaries": v_and_v_summaries,
        "threshold_breaches": threshold_breaches,
        "warnings": register_warnings,
        "summary": summary,
        "reviewed_by": inputs.get("reviewed_by"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a metrics report as a Markdown document."""
    required = ("timestamp", "agent_signature", "citations", "kpi_records", "summary")
    missing = [k for k in required if k not in report]
    if missing:
        raise ValueError(f"report missing required fields: {missing}")

    lines = [
        "# Trustworthy-AI Metrics Report",
        "",
        f"**Generated at (UTC):** {report['timestamp']}",
        f"**Generated by:** {report['agent_signature']}",
        f"**Framework rendering:** {report.get('framework', 'nist')}",
        f"**GenAI overlay applied:** {report.get('overlay_applied', False)}",
    ]
    if report.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {report['reviewed_by']}")
    summary = report["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Total KPI records: {summary['total_kpi_records']}",
        f"- Systems covered: {summary['systems_covered']} of {summary['systems_in_scope']} in scope",
        f"- Metric families measured: {', '.join(summary['families_measured']) if summary['families_measured'] else 'none'}",
        f"- Threshold breaches: {summary['threshold_breach_count']}",
        f"- Records with warnings: {summary['records_with_warnings']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in report["citations"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Per-system V&V summaries", ""])
    if not report.get("v_and_v_summaries"):
        lines.append("_No per-system summaries; no measurements recorded for any system in scope._")
    for summary_entry in report.get("v_and_v_summaries", []):
        lines.extend([
            f"### {summary_entry.get('system_name') or summary_entry['system_ref']}",
            "",
            f"- Families measured: {', '.join(summary_entry['families_measured'])}",
            f"- KPI records: {summary_entry['total_kpi_records']}",
            f"- Threshold breaches: {summary_entry['threshold_breach_count']}",
        ])
        if summary_entry["breached_metric_ids"]:
            lines.append(f"- Breached metric IDs: {', '.join(summary_entry['breached_metric_ids'])}")
        lines.append("- Citations: " + ", ".join(summary_entry["citations"]))
        lines.append("")

    lines.extend(["## Threshold breaches", ""])
    if not report.get("threshold_breaches"):
        lines.append("_No threshold breaches in this window._")
    else:
        lines.append("| KPI ID | System | Family | Metric | Value | Reason |")
        lines.append("|---|---|---|---|---|---|")
        for b in report["threshold_breaches"]:
            lines.append(
                f"| {b['kpi_id']} | {b['system_ref']} | {b['metric_family']} | {b['metric_id']} | "
                f"{b['value']} | {b['reason']} |"
            )

    warnings = [(r["id"], w) for r in report["kpi_records"] for w in r["warnings"]]
    if warnings or report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in report.get("warnings", []):
            lines.append(f"- (report) {w}")
        for kid, w in warnings:
            lines.append(f"- ({kid}) {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(report: dict[str, Any]) -> str:
    """Render KPI records as CSV."""
    if "kpi_records" not in report:
        raise ValueError("report missing 'kpi_records' field")
    header = (
        "kpi_id,system_ref,system_name,metric_family,metric_id,value,"
        "window_start,window_end,measurement_method_ref,test_set_ref,"
        "threshold_breached,threshold_reason,citations"
    )
    lines = [header]
    for r in report["kpi_records"]:
        fields = [
            _csv_escape(str(r.get("id", ""))),
            _csv_escape(str(r.get("system_ref", ""))),
            _csv_escape(str(r.get("system_name", "") or "")),
            _csv_escape(str(r.get("metric_family", ""))),
            _csv_escape(str(r.get("metric_id", ""))),
            _csv_escape(str(r.get("value", ""))),
            _csv_escape(str(r.get("window_start", ""))),
            _csv_escape(str(r.get("window_end", ""))),
            _csv_escape(str(r.get("measurement_method_ref", "") or "")),
            _csv_escape(str(r.get("test_set_ref", "") or "")),
            _csv_escape(str(r.get("threshold_breached", False))),
            _csv_escape(str(r.get("threshold_reason") or "")),
            _csv_escape("; ".join(r.get("citations", []))),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
