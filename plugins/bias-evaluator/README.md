# bias-evaluator

Computes standard fairness metrics from caller-supplied per-group counts and applies jurisdictional rule sets. Operationalizes NIST AI RMF MEASURE 2.11, EU AI Act Article 10(4), NYC LL144 Section 5-301 (four-fifths rule), Colorado SB 205 Section 6-1-1702(1), Singapore MAS Veritas (2022) fairness methodology, and ISO/IEC 42001:2023 Annex A Control A.7.4. ISO/IEC TR 24027:2021 is referenced as advisory.

## Design stance

The plugin does not perform model inference. The caller supplies per-group counts (totals, selected, and where ground truth is available, true-positive, false-positive, true-negative, false-negative, positive-predictive-value). The plugin computes the metrics that the supplied data supports and emits a `requires-ground-truth` status with a warning when a requested metric requires evidence not provided.

The plugin does not assign an overall bias score. Per-metric results are emitted; the practitioner interprets them in context. Jurisdictional rule application is explicit and deterministic per the rule tables below.

## Inputs

| Field | Required | Type | Description |
|---|---|---|---|
| `system_description` | yes | dict | System metadata. Recommended keys: `system_name`, `purpose`, `decision_authority`, `sector`. The `sector` field controls the recommended-not-mandated note for non-high-risk sectors. |
| `evaluation_data` | yes | dict | `dataset_ref`, `evaluation_date`, `sample_size`, `ground_truth_available` (bool), and `per_group_counts` keyed by group identifier (e.g. `"race:black"` or intersectional `"race:black|sex:female"`). Each value is a dict with `total`, `selected`, and optional `true_positive`, `false_positive`, `true_negative`, `false_negative`, `positive_predictive_value`. |
| `protected_attributes` | yes | list | List of dicts `{attribute_name, categories_present}`. |
| `metrics_to_compute` | no | list | Subset of `VALID_METRICS`. Default `["selection-rate", "impact-ratio"]`. |
| `jurisdiction_rules` | no | list | Subset of `VALID_JURISDICTION_RULES`. Default `[]`. |
| `intersectional_analysis` | no | bool | Default `False`. When `True`, compute metrics on compound-attribute keys (containing `\|`) separately. |
| `organizational_thresholds` | no | dict | Map of metric name to threshold. Used by EU AI Act Article 10(4) rule for organizational-threshold compliance status. |
| `minimum_group_size` | no | int | Default 30. Groups with `total` below this are flagged underpowered with a warning. |
| `enrich_with_crosswalk` | no | bool | Default `True`. |
| `reviewed_by` | no | str | Optional reviewer attribution. |

### Group key convention

Group keys are strings of the form `"<attribute>:<value>"` for single-attribute slices, or `"<attribute_a>:<value_a>|<attribute_b>:<value_b>"` for intersectional slices. The `|` character is the canonical compound separator. Plugin behavior splits compound keys from single-attribute keys automatically.

## Metrics

| Metric | Computation | Ground truth required |
|---|---|---|
| `selection-rate` | `selected / total` per group. | No |
| `impact-ratio` | `min(selection_rate) / max(selection_rate)` across groups. | No |
| `demographic-parity-difference` | Maximum pairwise difference in selection rates across groups. | No |
| `statistical-parity-difference` | Same as demographic parity, expressed in absolute-value form across pairs. | No |
| `equalized-odds-difference` | Maximum of (max pairwise TPR difference, max pairwise FPR difference). | Yes |
| `predictive-parity-difference` | Maximum pairwise PPV difference. | Yes |

When ground truth is unavailable, ground-truth-requiring metrics emit `value=None` and `status="requires-ground-truth"`. The plugin never silently substitutes a non-ground-truth proxy.

## Jurisdictional rules

| Rule id | Citation | Pass condition | Failure status |
|---|---|---|---|
| `nyc-ll144-4-5ths` | `NYC LL144 Final Rule, Section 5-301` | `impact_ratio >= 0.8` | `fail-disparate-impact-concern` |
| `eu-ai-act-art-10-4` | `EU AI Act, Article 10, Paragraph 4` | At least one bias metric computed against the supplied evaluation data; binary pass/fail not assigned. When `organizational_thresholds[metric]` is supplied, the rule emits `within-organizational-threshold` or `concern-exceeds-organizational-threshold`. | `not-examined` if no bias metric computed |
| `colorado-sb-205-reasonable-care` | `Colorado SB 205, Section 6-1-1702(1)` | Bias evaluation present in record. | `reasonable-care-not-documented` if absent |
| `singapore-veritas-fairness` | `MAS Veritas (2022)` | Always emits a Veritas-methodology next-steps list (context-aware metric selection, balanced-dataset orientation, independent validation, MAS FEAT mapping). | n/a |
| `iso-42001-a-7-4` | `ISO/IEC 42001:2023, Annex A, Control A.7.4` | Bias metrics serve as data-quality evidence. | `data-quality-evidence-absent` if no metric computed |
| `nist-measure-2-11` | `NIST AI RMF, MEASURE 2.11` | Bias metric computed. | `not-evaluated` if absent |

## Outputs

Top-level keys in the result dict:

| Key | Type | Description |
|---|---|---|
| `timestamp` | str | ISO 8601 UTC. |
| `agent_signature` | str | `bias-evaluator/0.1.0`. |
| `framework` | str | `nist,eu-ai-act,usa-nyc,usa-co,singapore,iso42001`. |
| `system_description_echo` | dict | Echo of the supplied system_description. |
| `evaluation_data_echo` | dict | Echo of evaluation_data minus per_group_counts. |
| `protected_attributes_echo` | list | Echo of protected_attributes. |
| `per_metric_results` | list | One entry per metric in `metrics_to_compute` (single-attribute groups). |
| `intersectional_results` | list or null | When `intersectional_analysis=True`, one entry per metric on compound keys. |
| `rule_findings` | list | One entry per rule in `jurisdiction_rules`. |
| `underpowered_groups` | list | Groups with `total < minimum_group_size`. |
| `citations` | list | Top-level applicable citations. Always includes `NIST AI RMF, MEASURE 2.11`, `ISO/IEC 42001:2023, Annex A, Control A.7.4`, and `ISO/IEC TR 24027:2021`. |
| `warnings` | list | Content gaps and small-sample warnings. |
| `summary` | dict | Aggregate counts. |
| `cross_framework_citations` | list | Present when `enrich_with_crosswalk=True`. |
| `reviewed_by` | str or null | Echo. |

## Example invocation

```python
from plugin import evaluate_bias, render_markdown

result = evaluate_bias({
    "system_description": {
        "system_name": "ResumeScreen-X",
        "sector": "employment",
    },
    "evaluation_data": {
        "dataset_ref": "Q2-2026 candidate pool",
        "evaluation_date": "2026-04-15",
        "sample_size": 4000,
        "ground_truth_available": False,
        "per_group_counts": {
            "race:white": {"total": 2000, "selected": 800},
            "race:black": {"total": 2000, "selected": 680},
        },
    },
    "protected_attributes": [
        {"attribute_name": "race", "categories_present": ["white", "black"]},
    ],
    "metrics_to_compute": ["selection-rate", "impact-ratio"],
    "jurisdiction_rules": ["nyc-ll144-4-5ths"],
})

print(render_markdown(result))
```

## Anti-hallucination invariants

1. The plugin does not perform inference. It computes only metrics that the supplied counts directly support.
2. Ground-truth-requiring metrics are not silently computed when ground truth is unavailable. They emit `requires-ground-truth` and a warning.
3. The plugin does not assign an overall fairness or bias score. Aggregated cross-metric verdicts require human judgment.
4. Impact-ratio division-by-zero is handled explicitly. A `max selection rate = 0` returns `value=None`, `status="undefined-division-by-zero"`, plus a warning.
5. Small-sample groups are flagged, not dropped or filled.
6. When a sector outside the canonical high-risk family is supplied, the plugin emits a recommended-not-mandated note rather than skipping evaluation.

## Determinism

Output is deterministic for a given input. The only non-deterministic field is `timestamp`. Crosswalk enrichment depends on the on-disk crosswalk data; if data load fails, enrichment is skipped with a warning and the rest of the report is unaffected.

## Related plugins

- [risk-register-builder](../risk-register-builder/) consumes `rule_findings` and per-metric results into a `bias` category risk row.
- [nyc-ll144-audit-packager](../nyc-ll144-audit-packager/) consumes selection rates and impact ratios into the public-disclosure bundle.
- [soa-generator](../soa-generator/) cites this plugin's output as evidence for `A.7.4` quality-of-data and for MEASURE 2.11 coverage.
- [crosswalk-matrix-builder](../crosswalk-matrix-builder/) supplies the cross-framework anchor data.
