# robustness-evaluator

Point-in-time robustness evaluation record. Operationalizes EU AI Act Article 15 (accuracy, robustness, cybersecurity), ISO/IEC 42001:2023 Annex A Control A.6.2.4 (verification and validation of the AI system), and NIST AI RMF 1.0 MEASURE 2.5, 2.6, and 2.7.

Distinct from siblings:

- [`metrics-collector`](../metrics-collector/) is the ongoing KPI surface.
- [`post-market-monitoring`](../post-market-monitoring/) is the forward-looking monitoring plan.
- [`nonconformity-tracker`](../nonconformity-tracker/) records the Clause 10.2 internal corrective-action lifecycle that follows an evaluation failure.
- [`incident-reporting`](../incident-reporting/) handles external statutory notification when an evaluation failure also qualifies as a reportable incident.

## Status

0.1.0. Ships Article 15 paragraphs (1) through (5) coverage with adversarial-posture aggregation, evaluator-independence tracking, and lifecycle trend computation against a previous evaluation reference.

## Design stance

The plugin does NOT compute metrics or run tests. Test execution is the MLOps and red-team pipelines' responsibility. The plugin validates a precomputed evaluation submission against per-dimension expectations, attaches the correct citations, aggregates Article 15(4) adversarial posture using a worst-of resilience-level rule, surfaces lifecycle deltas when a previous evaluation is referenced, and emits a cross-plugin action item for the Article 15(2) instructions-for-use declaration. Missing core dimensions for a high-risk EU system surface as blocking warnings rather than silent omissions.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | At minimum `system_id`, `risk_tier`, `jurisdiction`, optional `continuous_learning` bool. |
| `evaluation_scope` | dict | yes | `dimensions` (list from VALID_EVALUATION_DIMENSIONS), `evaluation_date`, `evaluator_identity`, `evaluator_independence` (one of `internal-team`, `third-party-audit`, `bug-bounty-program`). |
| `evaluation_results` | dict | yes | Maps dimension to a result dict. Result dict carries either a metric tuple (`primary_metric`, `metric_value`, `declared_threshold`, `pass`) or a `resilience_level` from RESILIENCE_THRESHOLD_LEVELS, plus `test_method`, optional `dataset_ref`, `attack_types_tested`, and `evidence_ref`. |
| `backup_plan_ref` | string | conditional | Required for high-risk EU systems per Article 15(3). |
| `concept_drift_monitoring_ref` | string | conditional | Required when `continuous_learning` is set or when `concept-drift-handling` / `continuous-learning-controls` dimensions are evaluated. |
| `previous_evaluation_ref` | dict | no | Previous output of `evaluate_robustness` (or any dict with `dimension_assessments`). Triggers `trend_delta` computation. |
| `enrich_with_crosswalk` | bool | no | Default True. When True, attaches Article 15 to ISO 42001 mappings from `crosswalk-matrix-builder`. |
| `reviewed_by` | string | no | Reviewer identity, surfaced in the rendered output. |

## Dimension enumeration

`accuracy`, `robustness`, `cybersecurity`, `adversarial-robustness`, `data-poisoning-resistance`, `model-evasion-resistance`, `confidentiality`, `fail-safe-design`, `concept-drift-handling`, `continuous-learning-controls`.

## Test method enumeration

`holdout`, `cross-validation`, `stress-test`, `boundary-test`, `adversarial-test`, `red-team-engagement`, `fuzz-test`, `membership-inference-test`, `poisoning-simulation`, `evasion-attack-simulation`.

## Resilience threshold levels

`verified-strong`, `verified-adequate`, `verified-weak`, `not-verified`. Worst-of aggregation produces `overall_adversarial_posture` per Article 15(4).

## Outputs

Structured dict with `timestamp`, `agent_signature`, `framework`, `system_description_echo`, `evaluation_scope_echo`, `dimension_assessments`, `adversarial_posture` (when applicable), `art_15_2_declaration_status`, `backup_plan_status`, `concept_drift_monitoring_status`, `evaluator_independence_note`, `trend_delta` (when applicable), `citations`, `cross_framework_citations` (when enriched), `warnings`, `summary`, `reviewed_by`.

Three renderers: `evaluate_robustness`, `render_markdown`, `render_csv`.

## Rule table

| Rule | Trigger | Action |
|---|---|---|
| Article 15(1) tri-requirement | EU high-risk system missing accuracy, robustness, or cybersecurity dimension evaluation | Emit BLOCKING warning |
| Article 15(2) declaration | accuracy dimension evaluated | Emit `art_15_2_declaration_status` cross-plugin action item |
| Article 15(3) backup plan | EU high-risk system without `backup_plan_ref` | Emit BLOCKING warning |
| Article 15(4) adversarial posture | Any sub-dimension in `adversarial-robustness`, `data-poisoning-resistance`, `model-evasion-resistance`, `confidentiality` | Aggregate worst-of resilience level into `adversarial_posture.overall_adversarial_posture` |
| Article 15(5) feedback loops | `continuous_learning` set or `concept-drift-handling` / `continuous-learning-controls` dimension evaluated, but no `concept_drift_monitoring_ref` | Emit warning |
| Evaluator independence | `evaluator_independence == "internal-team"` | Emit Article 43 notified-body note |
| Lifecycle delta | `previous_evaluation_ref` supplied | Emit `trend_delta` per dimension (`improving`, `stable`, `degrading`, `new`, `indeterminate`) |
| Anti-hallucination | Dimension declared in scope but absent from `evaluation_results` | Emit assessment with `status: not-evaluated` and a per-dimension warning |

## Example

```python
import plugins.robustness_evaluator.plugin as re

result = re.evaluate_robustness({
    "system_description": {
        "system_id": "sys-triage-eu",
        "risk_tier": "high",
        "jurisdiction": "eu",
        "continuous_learning": False,
    },
    "evaluation_scope": {
        "dimensions": ["accuracy", "robustness", "cybersecurity"],
        "evaluation_date": "2026-04-15",
        "evaluator_identity": "ACME Independent Evaluators GmbH",
        "evaluator_independence": "third-party-audit",
    },
    "evaluation_results": {
        "accuracy": {
            "test_method": "holdout",
            "dataset_ref": "test-data-2026-04-10",
            "primary_metric": "F1",
            "metric_value": 0.82,
            "declared_threshold": 0.75,
            "pass": True,
            "evidence_ref": "reports/accuracy-2026-04-10.pdf",
        },
        "robustness": {
            "test_method": "stress-test",
            "resilience_level": "verified-adequate",
            "evidence_ref": "reports/robustness-2026-04-10.pdf",
        },
        "cybersecurity": {
            "test_method": "red-team-engagement",
            "resilience_level": "verified-adequate",
            "attack_types_tested": ["prompt-injection", "evasion"],
            "evidence_ref": "reports/cyber-2026-04-10.pdf",
        },
    },
    "backup_plan_ref": "docs/fail-safe-design.pdf",
})
print(re.render_markdown(result))
```

## Determinism

Output is deterministic given the same input. The `timestamp` field is the only non-deterministic value (UTC clock).

## Related citations

- `EU AI Act, Article 15, Paragraph 1` through `Paragraph 5`
- `ISO/IEC 42001:2023, Annex A, Control A.6.2.4`
- `MEASURE 2.5`, `MEASURE 2.6`, `MEASURE 2.7`
- `UK ATRS, Section Tool details` (when UK jurisdiction)
- `Colorado SB 205, Section 6-1-1702(1)` (when Colorado jurisdiction)

## Testing

```bash
python -m pytest plugins/robustness-evaluator/tests/ -q
```
