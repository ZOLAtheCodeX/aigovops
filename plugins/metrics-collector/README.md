# metrics-collector

Aggregates, validates, and cites NIST AI RMF 1.0 MEASURE 2.x metric families, with optional AI 600-1 Generative AI Profile overlay. Emits KPI records and routes threshold breaches to downstream governance workflows.

## Status

Phase 3 minimum-viable implementation. Closes the NIST Tier 1 gap on trustworthy-AI measurement (T1.2 technical performance and safety; T1.6 privacy and fairness). Also serves iso42001 Clause 9.1 monitoring and measurement when `framework='iso42001'` or `'dual'`.

## Design stance

The plugin does NOT compute metrics. Metric computation is the MLOps pipeline's job (held-out evaluations, production telemetry, fairness-probe runs, privacy-attack simulations, and so on). The plugin takes precomputed measurement values and:

1. Validates each measurement against the metric catalog (family and metric_id must be known).
2. Enforces that every measurement carries a `measurement_method_ref` and a `test_set_ref` where the family requires one (MEASURE 2.1 demands method and test-set documentation).
3. Applies organizational threshold specs (`max`, `min`, `range`) and flags breaches deterministically.
4. Attaches the correct MEASURE subcategory citations (plus Clause 9.1 in iso42001 or dual mode).
5. Emits per-system V&V summaries covering which families were measured and how many breaches occurred.
6. Emits a routable `threshold_breaches` list naming the recommended downstream workflow (risk-register update, nonconformity-tracker) for each breach.

## Default metric catalog

| Family | Metrics | MEASURE subcategories | Requires test set |
|---|---|---|---|
| `validity-reliability` | `f1`, `precision`, `recall`, `calibration_ece`, `coverage_at_threshold` | `MEASURE 2.5`, `MEASURE 2.1` | yes |
| `in-context-performance` | `production_accuracy`, `latency_p95_ms`, `throughput_rps`, `error_rate` | `MEASURE 2.3` | no |
| `safety` | `refusal_rate`, `safety_filter_fp`, `safety_filter_fn`, `incident_count`, `time_to_detect_seconds`, `time_to_mitigate_seconds` | `MEASURE 2.6` | no |
| `security-resilience` | `adversarial_robustness`, `auth_bypass_rate`, `cve_count`, `mean_time_to_patch_days` | `MEASURE 2.7` | no |
| `explainability` | `explanation_coverage`, `explanation_fidelity` | `MEASURE 2.8` | no |
| `privacy` | `training_data_exposure`, `membership_inference_risk`, `attribute_inference_risk`, `pii_in_outputs_rate` | `MEASURE 2.9` | yes |
| `fairness` | `demographic_parity_difference`, `equal_opportunity_difference`, `calibration_parity`, `representational_harm_rate` | `MEASURE 2.10` | yes |
| `environmental` | `kwh_per_inference`, `gco2eq_per_inference`, `training_kwh` | `MEASURE 2.11` | no |
| `computational-efficiency` | `inference_cost_usd_per_1k`, `p99_latency_ms` | `MEASURE 2.12` | no |

Organizations extend or override the catalog by supplying a `metric_catalog` input that is merged into the defaults. Adding a new family under a new key is the recommended path; overriding existing families is supported but should be documented.

## AI 600-1 (Generative AI) overlay

When any system in `ai_system_inventory` carries `system_type: generative-ai`, the plugin auto-enables the overlay. The overlay adds six metric families addressing generative-AI-specific concerns:

| Overlay family | Metrics | Subcategory citation |
|---|---|---|
| `confabulation` | `hallucination_rate`, `source_attribution_accuracy` | `MEASURE 2.6 (AI 600-1 overlay)` |
| `data-regurgitation` | `exact_match_regurgitation_rate`, `near_match_regurgitation_rate` | `MEASURE 2.9 (AI 600-1 overlay)` |
| `abusive-content` | `policy_violation_rate`, `known_harmful_content_false_negative_rate` | `MEASURE 2.6 (AI 600-1 overlay)` |
| `information-integrity` | `synthetic_labeling_compliance`, `provenance_signal_attachment_rate` | `MEASURE 2.8 (AI 600-1 overlay)` |
| `ip-risk` | `uncleared_content_reproduction_rate` | `MEASURE 2.6 (AI 600-1 overlay)` |
| `value-chain-integrity` | `foundation_model_provenance_documented`, `pretrained_model_risk_posture` | `MANAGE 3.2 (AI 600-1 overlay)` |

Explicit control via `genai_overlay_enabled: True|False` overrides auto-detection.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `ai_system_inventory` | list | yes | Systems in scope with `system_ref`, `system_name`, optional `system_type`. |
| `measurements` | list | yes | Precomputed measurements with `system_ref`, `metric_family`, `metric_id`, `value`, `window_start`, `window_end`, optional `measurement_method_ref`, `test_set_ref`, `id`. |
| `metric_catalog` | dict | no | Overrides or extends `DEFAULT_METRIC_CATALOG`. |
| `thresholds` | dict | no | Maps `metric_id` to `{operator: 'max' or 'min' or 'range', value: X, range: [lo, hi]}`. |
| `genai_overlay_enabled` | bool | no | Explicit override; auto-detected from `system_type` otherwise. |
| `framework` | string | no | `iso42001`, `nist` (default), or `dual`. |
| `reviewed_by` | string | no | |

Missing required fields, invalid framework, invalid threshold operator, or missing threshold parameters raise `ValueError`. Content gaps surface as per-KPI or register-level warnings.

## Outputs

Report dict:

- `timestamp`, `agent_signature`, `framework`, `overlay_applied`, `catalog_used` (list of family names used in this invocation), top-level `citations`, `reviewed_by`.
- `kpi_records`: one dict per measurement with `id`, `system_ref`, `system_name`, `metric_family`, `metric_id`, `value`, window, method and test set refs, `threshold_breached`, `threshold_reason`, `citations`, per-record `warnings`.
- `v_and_v_summaries`: one entry per covered system with families measured, KPI count, breach count, breached metric IDs, and per-entry citations.
- `threshold_breaches`: flat list of breach entries with routing recommendations for the next governance workflow.
- `warnings`: register-level warnings (empty register, and so on).
- `summary`: aggregate counts suitable for dashboard consumption.

Three renderers: `generate_metrics_report`, `render_markdown`, `render_csv`.

## Threshold semantics

```python
thresholds = {
    "f1": {"operator": "min", "value": 0.85},
    "incident_count": {"operator": "max", "value": 3},
    "pii_in_outputs_rate": {"operator": "range", "range": [0.0, 0.001]},
}
```

- `operator: max`: breach if `value > threshold.value`.
- `operator: min`: breach if `value < threshold.value`.
- `operator: range`: breach if `value` is outside `[range[0], range[1]]`.

Non-numeric measurement values against numeric thresholds surface a warning and do not breach (the plugin does not coerce).

## Example

```python
from plugins.metrics_collector import plugin

inputs = {
    "ai_system_inventory": [
        {"system_ref": "SYS-001", "system_name": "FraudScore-Prod"},
        {"system_ref": "SYS-002", "system_name": "CS-GenAI-Assist", "system_type": "generative-ai"},
    ],
    "measurements": [
        {
            "system_ref": "SYS-001",
            "metric_family": "validity-reliability",
            "metric_id": "f1",
            "value": 0.92,
            "window_start": "2026-04-01T00:00:00Z",
            "window_end": "2026-04-30T23:59:59Z",
            "measurement_method_ref": "METHOD-HOLDOUT-2026Q1",
            "test_set_ref": "TS-holdout-2026Q1",
        },
        {
            "system_ref": "SYS-002",
            "metric_family": "confabulation",
            "metric_id": "hallucination_rate",
            "value": 0.04,
            "window_start": "2026-04-01T00:00:00Z",
            "window_end": "2026-04-30T23:59:59Z",
            "measurement_method_ref": "METHOD-HALLUC-PROBE-2026Q1",
            "test_set_ref": "TS-HALLUC-2026Q1",
        },
    ],
    "thresholds": {
        "f1": {"operator": "min", "value": 0.85},
        "hallucination_rate": {"operator": "max", "value": 0.05},
    },
    "framework": "dual",
    "reviewed_by": "AI Governance Committee, 2026-Q2",
}

report = plugin.generate_metrics_report(inputs)
print(plugin.render_markdown(report))
```

## Tests

```bash
python plugins/metrics-collector/tests/test_plugin.py
```

33 tests covering happy path, framework modes, AI 600-1 overlay auto-detection and explicit control, all threshold operators and breach routing, validation error paths, unknown-family and unknown-metric warnings, per-system V&V summary aggregation, custom catalog extension, Markdown and CSV rendering, and no-em-dash enforcement.

## Related

- NIST AI RMF 1.0: MEASURE 1.1, 2.1, 2.3, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12; MEASURE 3.1, MEASURE 4.1, MANAGE 4.1
- NIST AI 600-1 (Generative AI Profile)
- ISO/IEC 42001:2023 Clause 9.1 (Monitoring, measurement, analysis and evaluation)
- Skill references: [skills/nist-ai-rmf/SKILL.md](../../skills/nist-ai-rmf/SKILL.md) T1.2 and T1.6
- Upstream: MLOps telemetry pipelines, test-set registries, incident logs
- Downstream: risk-register-builder (threshold breaches may create risks), nonconformity-tracker (material breaches become nonconformities), management-review-packager (KPI summary feeds Clause 9.3.2 AIMS performance)
