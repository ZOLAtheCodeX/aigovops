# Post-market monitoring operationalization map

Per-framework mapping from authoritative-source text to `post-market-monitoring` plugin input and output fields, plus the per-dimension-to-response-plugin routing table.

## Scope

This map covers EU AI Act Article 72, ISO/IEC 42001:2023 Clause 9.1, NIST AI RMF MANAGE 4.1 and 4.2, UK ATRS Section Risks (uk-jurisdiction systems), and Colorado SB 205 Section 6-1-1703(3) (annual deployer impact assessment, monitoring-adjacent).

## EU AI Act Article 72

| Sub-paragraph | Plugin field | Consumer flow |
|---|---|---|
| 72(1) Establish and document a post-market monitoring system | `monitoring_plan.plan_id`; `monitoring_plan.plan_version`; `established_on` | Plan id is deterministic (`pmm-<system_id>-<yyyy-mm-dd>`); version increments when `previous_plan_ref` is supplied. |
| 72(2) Continuous evaluation of compliance with Chapter III | `chapter_iii_alignment` (only for EU high-risk-annex-i / high-risk-annex-iii systems) | Per-Chapter-III-article check that the monitored dimensions cover the dimension family the article expects. Gap warnings emitted per missing article. |
| 72(3) Commission template substance: elements, methods, frequency, indicators, responsibilities, trigger thresholds | `per_dimension_monitoring`; `trigger_catalogue`; `responsibilities` input | Per-dimension rows carry the template substance pending the Commission template publication. |
| 72(4) Plan as part of technical documentation (Article 11) | Plan dict serialized into the technical-documentation bundle by `evidence-bundle-packager` | `evidence-bundle` skill is the downstream consumer for retention and signing. |

## ISO/IEC 42001:2023 Clause 9.1

| Requirement | Plugin field | Consumer flow |
|---|---|---|
| (a) What needs to be monitored | `monitoring_scope.dimensions_monitored` | One row per dimension in `per_dimension_monitoring`. |
| (b) Methods for monitoring, measurement, analysis, evaluation | `data_collection[].method` (enum from `VALID_DATA_COLLECTION_METHODS`); `per_dimension_monitoring[].method` | Practitioner-supplied. Placeholder when missing. |
| (c) When monitoring shall be performed | `cadence` (str enum or per-dimension dict); `per_dimension_monitoring[].cadence`; `review_schedule.per_dimension[].next_review_date` | Cadence drives next-review-date computation. |
| (d) When results shall be analysed and evaluated | `review_schedule.next_full_plan_review_date` | Driven by `plan_review_interval_months` (default 12). |
| Evidence retention | `data_collection[].retention_days`; plan dict itself | Stored in the audit-evidence archive per Clause 7.5.3. |

Annex A, Control A.6.2.6 (AI system operation and monitoring) is cited at every `per_dimension_monitoring` row.

## NIST AI RMF MANAGE 4

| Subcategory | Plugin field | Consumer flow |
|---|---|---|
| MANAGE 4.1 (Post-deployment monitoring planned) | Top-level `citations`; per-row `citations` | Direct exact-match with ISO Clause 9.1. |
| MANAGE 4.2 (Continual improvement activities integrated; regular engagement with interested parties) | `continuous_improvement_loop`; `responsibilities`; `trigger_catalogue` (engagement triggers like `user-feedback`) | Predecessor link via `previous_plan_ref` records the loop closure. |

## UK ATRS Section Risks (uk-jurisdiction systems)

UK ATRS Template v2.0 Section Risks records the monitoring posture for an algorithmic tool. When `system_description.jurisdiction` includes `uk`, the citation `UK ATRS, Section Risks` is appended to the top-level citations list. The plan record itself supplies the structured monitoring fields the ATRS Section Risks free-text expects.

## Colorado SB 205 Section 6-1-1703(3) (deployer annual impact assessment)

The annual deployer impact assessment is monitoring-adjacent: it requires a deployer of a high-risk system to assess and document, at least annually, whether the system has caused or is reasonably likely to cause algorithmic discrimination. The monitoring plan is an upstream input to that assessment. Citation: `Colorado SB 205, Section 6-1-1703(3)`. This skill does not produce the assessment itself; `colorado-ai-act-compliance` does.

## Per-dimension to response-plugin routing table

| Dimension | Default cadence | Default method | Default escalation path | Routing-citation rationale |
|---|---|---|---|---|
| `accuracy` | monthly | `telemetry` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `robustness` | monthly | `red-team-engagement` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `cybersecurity` | weekly | `logs` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `drift` | weekly | `telemetry` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `bias-fairness` | quarterly | `audit-sampling` | `management-review` | ISO/IEC 42001:2023, Clause 9.3 |
| `privacy-leakage` | monthly | `telemetry` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `availability` | continuous | `telemetry` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `latency` | continuous | `telemetry` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `throughput` | continuous | `telemetry` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `user-feedback` | continuous | `user-survey` or `complaints-channel` | `management-review` | ISO/IEC 42001:2023, Clause 9.3 |
| `incident-rate` | continuous | `complaints-channel` | `incident-reporting` | EU AI Act, Article 73 |
| `safety-events` | event-driven | `logs` or `complaints-channel` | `incident-reporting` | EU AI Act, Article 73 |
| `explainability-signals` | quarterly | `audit-sampling` | `corrective-action-plan` | ISO/IEC 42001:2023, Clause 10.2 |

Practitioners override defaults by supplying triggers explicitly in `trigger_catalogue`.

## Chapter III dimension-mapping table (EU high-risk systems)

| Chapter III Article | Article subject | Expected monitored dimensions |
|---|---|---|
| Article 9 | Risk management system | drift, bias-fairness, incident-rate |
| Article 10 | Data and data governance | privacy-leakage, bias-fairness |
| Article 13 | Transparency and provision of information to deployers | user-feedback |
| Article 14 | Human oversight | (operationalized via human-review-sampling METHOD across dimensions; declare with caution) |
| Article 15 | Accuracy, robustness, cybersecurity | accuracy, robustness, cybersecurity, availability, latency |
| Article 26 | Obligations of deployers of high-risk AI systems | incident-rate |

Article 14 requires special handling: human oversight is operationalized through the `human-review-sampling` METHOD applied across dimensions like bias-fairness, accuracy, and explainability-signals. Declaring Article 14 in `chapter_iii_requirements_in_scope` will produce a coverage warning unless the organization adapts the dimension mapping; document this trade-off when you scope the plan.

## Cross-framework references emitted (when `enrich_with_crosswalk: True`)

| Target framework | Target ref | Relationship | Confidence |
|---|---|---|---|
| NIST AI RMF 1.0 | MANAGE 4.1 | exact-match | high |
| NIST AI RMF 1.0 | MANAGE 4.2 | partial-match | high |
| EU AI Act | Article 72, Paragraph 1 | satisfies | high |
| EU AI Act | Article 72, Paragraph 2 | satisfies | high |
| EU AI Act | Article 72, Paragraph 4 | satisfies | high |

These references are also registered in `plugins/crosswalk-matrix-builder/data/iso42001-eu-ai-act.yaml` and `plugins/crosswalk-matrix-builder/data/iso42001-nist-ai-rmf.yaml`.
