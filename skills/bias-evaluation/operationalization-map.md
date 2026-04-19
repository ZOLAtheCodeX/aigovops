# Bias Evaluation Operationalization Map

Working document for the `bias-evaluation` skill. Maps each computed metric and each jurisdictional rule to its upstream framework anchor and the downstream plugins that consume it.

## Methodology

A/H/J classification:

- A: automatable. The plugin computes the metric deterministically from caller-supplied per-group counts.
- H: hybrid. Computation is automated; protected-group definition, threshold setting, or interpretation requires human input.
- J: judgment. A qualified human (counsel, auditor, statistician) determines applicability or interpretation.

Leverage:

- H: strong cost reduction. The plugin replaces a meaningful manual computation or rule-application step.
- M: moderate.
- L: low; narrow applicability.

## Per-metric mapping

| Metric | Class | Leverage | Upstream framework anchor | Downstream plugin consumers |
|---|---|---|---|---|
| `selection-rate` | A | H | NIST AI RMF, MEASURE 2.11; ISO/IEC 42001:2023, Annex A, Control A.7.4 | `nyc-ll144-audit-packager` (selection_rates field), `risk-register-builder` (bias category row), `evidence-bundle-packager` |
| `impact-ratio` | A | H | NYC LL144 Final Rule, Section 5-301 (four-fifths rule); NIST AI RMF, MEASURE 2.11 | `nyc-ll144-audit-packager` (impact_ratios field), `risk-register-builder`, `colorado-ai-act-compliance` (reasonable-care evidence) |
| `demographic-parity-difference` | A | M | NIST AI RMF, MEASURE 2.11; EU AI Act, Article 10, Paragraph 4 | `risk-register-builder`, `metrics-collector` (NIST MEASURE 2.11 KPI) |
| `statistical-parity-difference` | A | M | NIST AI RMF, MEASURE 2.11 | `metrics-collector`, `risk-register-builder` |
| `equalized-odds-difference` | A | M | NIST AI RMF, MEASURE 2.11 | `metrics-collector`, `risk-register-builder`. Requires `ground_truth_available=True`. |
| `predictive-parity-difference` | A | M | NIST AI RMF, MEASURE 2.11 | `metrics-collector`, `risk-register-builder`. Requires `ground_truth_available=True`. |

## Per-rule mapping

| Rule id | Class | Citation | Pass condition | Downstream consumer |
|---|---|---|---|---|
| `nyc-ll144-4-5ths` | A | `NYC LL144 Final Rule, Section 5-301`; continuous-output cases cite `NYC DCWP AEDT Rules, 6 RCNY Section 5-301(b)` | impact_ratio >= 0.8 | `nyc-ll144-audit-packager` consumes the rule_finding directly into the public-disclosure bundle. |
| `eu-ai-act-art-10-4` | A | `EU AI Act, Article 10, Paragraph 4` | At least one bias metric computed against the supplied evaluation data; organizational threshold compliance status when `organizational_thresholds[metric]` supplied | `risk-register-builder` (bias category row references the rule_finding); `evidence-bundle-packager` (Article 10 bias examination evidence). |
| `colorado-sb-205-reasonable-care` | A | `Colorado SB 205, Section 6-1-1702(1)` | Bias evaluation present in record | `colorado-ai-act-compliance` (consumes the rule_finding as developer or deployer reasonable-care evidence per Section 6-1-1702(1) and Section 6-1-1703(1)). |
| `singapore-veritas-fairness` | H | `MAS Veritas (2022)` | Methodology next-steps emitted | `singapore-magf-assessor` (consumes the rule_finding into the FEAT Principle Fairness assessment). |
| `iso-42001-a-7-4` | A | `ISO/IEC 42001:2023, Annex A, Control A.7.4`; `ISO/IEC TR 24027:2021` advisory | Bias metric computed | `soa-generator` (cites the rule_finding as A.7.4 quality-of-data evidence with status `included-implemented`). |
| `nist-measure-2-11` | A | `NIST AI RMF, MEASURE 2.11` | Bias metric computed | `metrics-collector` (consumes the result as a MEASURE 2.11 KPI record); `risk-register-builder` (NIST framework rendering). |

## Plugin coverage summary

One plugin: `bias-evaluator`. The plugin's `evaluate_bias` function covers every automatable metric and every automatable rule above. The skill's two judgment-bound determinations (which rules apply, how to aggregate per-metric results into a release-or-hold decision) remain human determinations and are surfaced as documentation in the report.

## Upstream and downstream graph

Upstream inputs to `bias-evaluator`:

- AI system inventory: `system_description.system_name` references an entry in the `ai-system-inventory-maintainer` output where one exists.
- Evaluation dataset: `evaluation_data.dataset_ref` references a dataset registered in the `data-register-builder` output.
- Protected attribute definitions: organizational policy, captured in the `protected_attributes` input.

Downstream consumers of `bias-evaluator`:

- `nyc-ll144-audit-packager`: consumes `per_metric_results[selection-rate].per_group` and `per_metric_results[impact-ratio].value` into the public-disclosure bundle.
- `risk-register-builder`: consumes `rule_findings` and per-metric results into a `bias` category risk row, with the rule-finding citation as `existing_controls` reference.
- `soa-generator`: cites `rule_findings[iso-42001-a-7-4]` as A.7.4 quality-of-data evidence.
- `metrics-collector`: consumes `per_metric_results` entries as MEASURE 2.11 KPI records.
- `colorado-ai-act-compliance`: consumes `rule_findings[colorado-sb-205-reasonable-care]` as developer or deployer reasonable-care evidence.
- `singapore-magf-assessor`: consumes `rule_findings[singapore-veritas-fairness]` into the FEAT Principle Fairness assessment.
- `evidence-bundle-packager`: includes the full report in audit and regulatory submission bundles.
- `certification-readiness`: consumes the report as MEASURE 2.11 and A.7.4 coverage evidence.

## Cross-framework crosswalk

| Source anchor | Target | Relationship | File |
|---|---|---|---|
| ISO 42001 A.7.4 | NIST MEASURE 2.11 | partial-match (high) | `plugins/crosswalk-matrix-builder/data/iso42001-nist-ai-rmf.yaml` |
| EU AI Act Article 10(4) | NIST MEASURE 2.11 | satisfies (high) | `plugins/crosswalk-matrix-builder/data/iso42001-eu-ai-act.yaml` |
| EU AI Act Article 10(4) | ISO 42001 A.7.4 and A.6.1.2 | partial-satisfaction (existing row) | `plugins/crosswalk-matrix-builder/data/iso42001-eu-ai-act.yaml` |
| NYC LL144 Section 5-301 | EU AI Act Article 10; NIST MEASURE 2.11 | complementary (existing row) | `plugins/crosswalk-matrix-builder/data/nyc-ll144-crosswalk.yaml` |
| Colorado SB 205 Section 6-1-1702(1) | NIST AI RMF; ISO/IEC 42001:2023 | statutory-presumption (existing rows under Section 6-1-1706(3)) | `plugins/crosswalk-matrix-builder/data/colorado-sb205-crosswalk.yaml` |
| ISO/IEC TR 24027:2021 | n/a (advisory) | Referenced; no direct mapping row | n/a |

ISO/IEC TR 24027:2021 is a technical report. It informs methodology selection and is cited in plugin output for completeness. It does not establish a conformance obligation and does not have a direct mapping row in the crosswalk data.
