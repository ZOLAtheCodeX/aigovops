"""Tests for metrics-collector plugin."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _inventory(genai: bool = False) -> list:
    item = {"system_ref": "SYS-001", "system_name": "FraudScore-Prod"}
    if genai:
        item["system_type"] = "generative-ai"
    return [item]


def _measurement(**kwargs) -> dict:
    base = {
        "system_ref": "SYS-001",
        "metric_family": "validity-reliability",
        "metric_id": "f1",
        "value": 0.92,
        "window_start": "2026-04-01T00:00:00Z",
        "window_end": "2026-04-30T23:59:59Z",
        "measurement_method_ref": "METHOD-HOLDOUT-2026Q1",
        "test_set_ref": "TS-holdout-2026Q1",
    }
    base.update(kwargs)
    return base


def _base_inputs() -> dict:
    return {"ai_system_inventory": _inventory(), "measurements": [_measurement()]}


def test_happy_path_required_fields():
    result = plugin.generate_metrics_report(_base_inputs())
    for f in ("timestamp", "agent_signature", "framework", "citations",
              "kpi_records", "v_and_v_summaries", "threshold_breaches",
              "summary", "overlay_applied", "catalog_used"):
        assert f in result


def test_default_framework_is_nist():
    result = plugin.generate_metrics_report(_base_inputs())
    assert result["framework"] == "nist"
    assert "MEASURE 1.1" in result["citations"]


def test_iso_framework_cites_clause_9_1():
    result = plugin.generate_metrics_report({**_base_inputs(), "framework": "iso42001"})
    assert "ISO/IEC 42001:2023, Clause 9.1" in result["citations"]
    record = result["kpi_records"][0]
    assert "ISO/IEC 42001:2023, Clause 9.1" in record["citations"]


def test_dual_framework_carries_both():
    result = plugin.generate_metrics_report({**_base_inputs(), "framework": "dual"})
    citations = result["citations"]
    assert "MEASURE 1.1" in citations
    assert "ISO/IEC 42001:2023, Clause 9.1" in citations


def test_kpi_records_have_family_citation():
    result = plugin.generate_metrics_report(_base_inputs())
    record = result["kpi_records"][0]
    # validity-reliability family has MEASURE 2.5 and MEASURE 2.1
    assert "MEASURE 2.5" in record["citations"]
    assert "MEASURE 2.1" in record["citations"]


def test_genai_overlay_auto_enabled_on_generative_system():
    result = plugin.generate_metrics_report({
        "ai_system_inventory": _inventory(genai=True),
        "measurements": [_measurement()],
    })
    assert result["overlay_applied"] is True
    assert "confabulation" in result["catalog_used"]
    assert "data-regurgitation" in result["catalog_used"]


def test_genai_overlay_explicit_false_disables():
    result = plugin.generate_metrics_report({
        "ai_system_inventory": _inventory(genai=True),
        "measurements": [_measurement()],
        "genai_overlay_enabled": False,
    })
    assert result["overlay_applied"] is False
    assert "confabulation" not in result["catalog_used"]


def test_genai_overlay_explicit_true_enables_for_non_genai():
    result = plugin.generate_metrics_report({
        "ai_system_inventory": _inventory(genai=False),
        "measurements": [_measurement()],
        "genai_overlay_enabled": True,
    })
    assert result["overlay_applied"] is True


def test_threshold_max_breach_detected():
    inputs = _base_inputs()
    inputs["measurements"] = [_measurement(metric_id="incident_count", metric_family="safety", value=5)]
    inputs["thresholds"] = {"incident_count": {"operator": "max", "value": 3}}
    result = plugin.generate_metrics_report(inputs)
    record = result["kpi_records"][0]
    assert record["threshold_breached"] is True
    assert "exceeds max threshold" in record["threshold_reason"]
    assert len(result["threshold_breaches"]) == 1


def test_threshold_min_breach_detected():
    inputs = _base_inputs()
    inputs["measurements"] = [_measurement(value=0.60)]
    inputs["thresholds"] = {"f1": {"operator": "min", "value": 0.80}}
    result = plugin.generate_metrics_report(inputs)
    record = result["kpi_records"][0]
    assert record["threshold_breached"] is True
    assert "below min threshold" in record["threshold_reason"]


def test_threshold_range_breach_detected():
    inputs = _base_inputs()
    inputs["measurements"] = [_measurement(metric_id="pii_in_outputs_rate", metric_family="privacy", value=0.01, test_set_ref="TS-X", measurement_method_ref="M-X")]
    inputs["thresholds"] = {"pii_in_outputs_rate": {"operator": "range", "range": [0.0, 0.001]}}
    result = plugin.generate_metrics_report(inputs)
    record = result["kpi_records"][0]
    assert record["threshold_breached"] is True
    assert "above range high" in record["threshold_reason"]


def test_threshold_not_breached_when_within():
    inputs = _base_inputs()
    inputs["thresholds"] = {"f1": {"operator": "min", "value": 0.80}}
    result = plugin.generate_metrics_report(inputs)
    assert result["kpi_records"][0]["threshold_breached"] is False
    assert result["threshold_breaches"] == []


def test_non_numeric_value_against_threshold_warns_but_does_not_breach():
    inputs = _base_inputs()
    inputs["measurements"] = [_measurement(value="non-numeric-label")]
    inputs["thresholds"] = {"f1": {"operator": "min", "value": 0.80}}
    result = plugin.generate_metrics_report(inputs)
    record = result["kpi_records"][0]
    assert record["threshold_breached"] is False
    assert any("not numeric" in w for w in record["warnings"])


def test_unknown_metric_family_warns():
    inputs = _base_inputs()
    inputs["measurements"] = [_measurement(metric_family="made-up-family")]
    result = plugin.generate_metrics_report(inputs)
    text = " ".join(result["kpi_records"][0]["warnings"])
    assert "made-up-family" in text


def test_metric_id_not_in_family_warns():
    inputs = _base_inputs()
    inputs["measurements"] = [_measurement(metric_id="not_a_metric")]
    result = plugin.generate_metrics_report(inputs)
    text = " ".join(result["kpi_records"][0]["warnings"])
    assert "not_a_metric" in text


def test_missing_test_set_for_test_set_family_warns():
    inputs = _base_inputs()
    inputs["measurements"] = [_measurement(test_set_ref=None)]
    result = plugin.generate_metrics_report(inputs)
    text = " ".join(result["kpi_records"][0]["warnings"])
    assert "test_set_ref" in text


def test_missing_measurement_method_ref_warns():
    inputs = _base_inputs()
    inputs["measurements"] = [_measurement(measurement_method_ref=None)]
    result = plugin.generate_metrics_report(inputs)
    text = " ".join(result["kpi_records"][0]["warnings"])
    assert "measurement_method_ref" in text


def test_unknown_system_ref_warns():
    inputs = _base_inputs()
    inputs["measurements"] = [_measurement(system_ref="SYS-999")]
    result = plugin.generate_metrics_report(inputs)
    text = " ".join(result["kpi_records"][0]["warnings"])
    assert "SYS-999" in text


def test_v_and_v_summaries_one_per_covered_system():
    inventory = [
        {"system_ref": "SYS-001", "system_name": "A"},
        {"system_ref": "SYS-002", "system_name": "B"},
    ]
    measurements = [
        _measurement(system_ref="SYS-001"),
        _measurement(system_ref="SYS-002"),
    ]
    result = plugin.generate_metrics_report({
        "ai_system_inventory": inventory,
        "measurements": measurements,
    })
    assert len(result["v_and_v_summaries"]) == 2


def test_v_and_v_summary_tracks_breaches():
    inputs = _base_inputs()
    inputs["measurements"] = [
        _measurement(metric_id="incident_count", metric_family="safety", value=10),
    ]
    inputs["thresholds"] = {"incident_count": {"operator": "max", "value": 3}}
    result = plugin.generate_metrics_report(inputs)
    summary = result["v_and_v_summaries"][0]
    assert summary["threshold_breach_count"] == 1
    assert "incident_count" in summary["breached_metric_ids"]


def test_genai_overlay_metric_carries_overlay_citation():
    result = plugin.generate_metrics_report({
        "ai_system_inventory": _inventory(genai=True),
        "measurements": [_measurement(
            metric_family="confabulation",
            metric_id="hallucination_rate",
            value=0.03,
            test_set_ref="TS-HALLUC-2026Q1",
            measurement_method_ref="M-HALLUC",
        )],
    })
    record = result["kpi_records"][0]
    assert any("AI 600-1 overlay" in c for c in record["citations"])


def test_missing_required_input_raises():
    try:
        plugin.generate_metrics_report({"ai_system_inventory": _inventory()})
    except ValueError as exc:
        assert "measurements" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_required_measurement_field_raises():
    try:
        plugin.generate_metrics_report({
            "ai_system_inventory": _inventory(),
            "measurements": [{"system_ref": "SYS-001", "metric_family": "validity-reliability"}],
        })
    except ValueError as exc:
        assert "metric_id" in str(exc) or "value" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_invalid_framework_raises():
    try:
        plugin.generate_metrics_report({**_base_inputs(), "framework": "cobit"})
    except ValueError as exc:
        assert "framework" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_invalid_threshold_operator_raises():
    inputs = _base_inputs()
    inputs["thresholds"] = {"f1": {"operator": "unknown", "value": 0.5}}
    try:
        plugin.generate_metrics_report(inputs)
    except ValueError as exc:
        assert "operator" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_threshold_missing_value_raises():
    inputs = _base_inputs()
    inputs["thresholds"] = {"f1": {"operator": "min"}}
    try:
        plugin.generate_metrics_report(inputs)
    except ValueError as exc:
        assert "value" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_threshold_range_missing_range_raises():
    inputs = _base_inputs()
    inputs["thresholds"] = {"f1": {"operator": "range"}}
    try:
        plugin.generate_metrics_report(inputs)
    except ValueError as exc:
        assert "range" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_empty_measurements_warns():
    result = plugin.generate_metrics_report({
        "ai_system_inventory": _inventory(),
        "measurements": [],
    })
    text = " ".join(result["warnings"])
    assert "measurements" in text.lower() or "no evidence" in text.lower()


def test_custom_catalog_extends_defaults():
    inputs = _base_inputs()
    inputs["metric_catalog"] = {
        "custom-family": {
            "metrics": ("custom_metric",),
            "measure_subcategories": ("MEASURE 2.13",),
            "requires_test_set": False,
        }
    }
    inputs["measurements"] = [_measurement(
        metric_family="custom-family",
        metric_id="custom_metric",
        value=0.5,
        test_set_ref=None,
    )]
    result = plugin.generate_metrics_report(inputs)
    record = result["kpi_records"][0]
    assert "MEASURE 2.13" in record["citations"]


def test_render_markdown_sections():
    result = plugin.generate_metrics_report(_base_inputs())
    md = plugin.render_markdown(result)
    for s in ("# Trustworthy-AI Metrics Report", "## Summary", "## Applicable Citations",
              "## Per-system V&V summaries", "## Threshold breaches"):
        assert s in md


def test_render_csv_header():
    result = plugin.generate_metrics_report(_base_inputs())
    csv = plugin.render_csv(result)
    lines = csv.strip().split("\n")
    assert lines[0].startswith("kpi_id,system_ref,system_name")
    assert len(lines) == 2  # header + 1 record


def test_no_em_dashes_in_output():
    result = plugin.generate_metrics_report(_base_inputs())
    md = plugin.render_markdown(result)
    csv = plugin.render_csv(result)
    assert "\u2014" not in md
    assert "\u2014" not in csv


def test_auto_generated_kpi_ids():
    result = plugin.generate_metrics_report({
        "ai_system_inventory": _inventory(),
        "measurements": [_measurement(), _measurement(metric_id="precision")],
    })
    assert result["kpi_records"][0]["id"] == "KPI-0001"
    assert result["kpi_records"][1]["id"] == "KPI-0002"


def _run_all():
    import inspect
    tests = [(n, o) for n, o in inspect.getmembers(sys.modules[__name__])
             if n.startswith("test_") and callable(o)]
    failures = []
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:
            failures.append((name, f"{type(exc).__name__}: {exc}"))
    print(f"Ran {len(tests)} tests: {len(tests) - len(failures)} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
