# post-market-monitoring

Operationalizes EU AI Act Article 72 (Post-market monitoring system and plan), ISO/IEC 42001:2023 Clause 9.1 (Monitoring, measurement, analysis, evaluation), NIST AI RMF 1.0 MANAGE 4.1 (post-deployment monitoring planned), and MANAGE 4.2 (continual improvement activities integrated). UK ATRS Section Risks attaches when the system is uk-jurisdiction.

## Status

Phase 3 minimum-viable implementation. 0.1.0.

## Distinct from siblings

| Plugin | What it does |
|---|---|
| `metrics-collector` | POINT-IN-TIME measurement of NIST MEASURE 2.x KPIs. |
| `nonconformity-tracker` | INTERNAL Clause 10.2 corrective-action response when monitoring detects an issue. |
| `incident-reporting` | EXTERNAL statutory notification under Article 73, Colorado SB 205, NYC LL144. |
| `post-market-monitoring` | The PLAN itself: what is monitored, at what cadence, by what method, and how observed signals route to a response mechanism via the trigger catalogue. |

## Design stance

The plugin does not invent thresholds, owners, or data-collection methods. Inputs carry them. Dimensions declared in monitoring scope without a matching `data_collection` entry produce a placeholder row with `method = "REQUIRES PRACTITIONER ASSIGNMENT"` and a warning. The plugin never prescribes a specific corrective action for an observed trigger; that is `incident-reporting` (external) or `nonconformity-tracker` (internal).

## What Article 72 requires

- **72(1).** Providers establish and document a post-market monitoring system that actively and systematically collects, documents, and analyses data about the performance of high-risk AI systems throughout their lifetime.
- **72(2).** The system enables continuous evaluation of compliance with Chapter III requirements.
- **72(3).** Commission implementing act establishes a template for the monitoring plan, including elements monitored, methods, frequency, indicators, responsibilities, and trigger thresholds for corrective action.
- **72(4).** The plan is part of the technical documentation referred to in Article 11.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | `system_id`, `system_name`, `intended_use`, `risk_tier`, `jurisdiction`, `deployment_context`, `lifecycle_state`. |
| `monitoring_scope` | dict | yes | `dimensions_monitored` (list from `VALID_DIMENSIONS`), `chapter_iii_requirements_in_scope` (list of EU AI Act article refs), `systems_in_program` (list). |
| `cadence` | str or dict | yes | Enum from `VALID_CADENCES` or dict mapping dimension to cadence value. |
| `data_collection` | list | no | List of `{dimension, method, source_system, retention_days, owner_role}`. |
| `thresholds` | dict | no | `{dimension: {lower_bound, upper_bound, trigger_action, escalation_path}}`. |
| `responsibilities` | dict | no | Role-to-duty mapping. |
| `previous_plan_ref` | str | no | Path or ID of prior plan for continuous-improvement diff. |
| `plan_review_interval_months` | int | no | Default 12. |
| `trigger_catalogue` | list | no | List of `{trigger_name, detection_method, threshold_rule, escalation_path_enum, notification_recipients}`. |
| `enrich_with_crosswalk` | bool | no | Default True. |
| `reviewed_by` | str | no | |

### Enums

- `VALID_CADENCES = ("continuous", "daily", "weekly", "monthly", "quarterly", "annual", "event-driven", "mixed")`
- `VALID_DIMENSIONS = ("accuracy", "robustness", "cybersecurity", "drift", "bias-fairness", "privacy-leakage", "availability", "latency", "throughput", "user-feedback", "incident-rate", "safety-events", "explainability-signals")`
- `VALID_DATA_COLLECTION_METHODS = ("telemetry", "logs", "human-review-sampling", "user-survey", "complaints-channel", "shadow-deployment", "canary-analysis", "audit-sampling", "red-team-engagement")`
- `VALID_ESCALATION_PATHS = ("nonconformity-tracker", "incident-reporting", "management-review", "risk-register-update", "corrective-action-plan", "system-decommission")`

## Outputs

A structured plan dict with:

- `timestamp`, `agent_signature`, `framework` (`"eu-ai-act,iso42001,nist"`).
- `plan_id` (`pmm-<system_id>-<yyyy-mm-dd>`), `plan_version` (`1.0` or bumped when a previous plan is referenced).
- `system_description_echo`, `monitoring_plan`.
- `per_dimension_monitoring`: one row per dimension, with cadence, method, data source, retention, owner, threshold, escalation path, indicator description, next review date, and citations.
- `trigger_catalogue`: per-trigger rules that route to one of the escalation paths, each with its framework citation.
- `chapter_iii_alignment` (only for EU high-risk systems): per-Chapter III article, expected and monitored dimensions, with coverage flag.
- `continuous_improvement_loop`: predecessor link plus diff scaffolding when `previous_plan_ref` is supplied. Maps to NIST MANAGE 4.2.
- `review_schedule`: per-dimension next-review dates plus next full plan review date.
- `citations`, `cross_framework_citations` (when enriched), `warnings`, `summary`, `reviewed_by`.

Three renderers: `generate_monitoring_plan`, `render_markdown`, `render_csv`.

## Routing rule table

| Trigger condition | Escalation path | Rationale citation |
|---|---|---|
| Drift beyond `upper_bound` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| Safety event with `severity: serious-physical-harm` | `incident-reporting` | EU AI Act, Article 73, Paragraph 6 / 7 |
| Repeated bias-fairness threshold breach | `management-review` | ISO/IEC 42001:2023, Clause 9.3 |
| Threshold breach without specific severity | (per practitioner-supplied `escalation_path`) | ISO/IEC 42001:2023, Clause 9.1 |

## Warning surface

- Dimension declared in `monitoring_scope.dimensions_monitored` without a matching `data_collection` entry: placeholder row + warning.
- Threshold for a dimension lacks `escalation_path`: warning naming the dimension.
- Chapter III requirement declared in scope (EU high-risk system) but no monitored dimension matches: per-article warning.
- `data_collection` entry lacks `owner_role`: warning naming the dimension.
- Crosswalk plugin fails to load: warning, plan still generated with hard-coded cross-framework references.

Structural problems (missing required fields, invalid enums) raise `ValueError`.

## Citations always emitted

- `EU AI Act, Article 72, Paragraph 1`
- `EU AI Act, Article 72, Paragraph 2`
- `EU AI Act, Article 72, Paragraph 4`
- `EU AI Act, Article 11`
- `ISO/IEC 42001:2023, Clause 9.1`
- `ISO/IEC 42001:2023, Annex A, Control A.6.2.6`
- `NIST AI RMF, MANAGE 4.1`
- `NIST AI RMF, MANAGE 4.2`
- `UK ATRS, Section Risks` (when `jurisdiction` includes uk)

## Tests

```bash
python3 plugins/post-market-monitoring/tests/test_plugin.py
```

24 tests covering happy paths (EU high-risk, ISO-only), Chapter III gap warning, missing-input validation errors, invalid enum errors, placeholder emission, threshold-without-escalation warning, trigger-routing to nonconformity-tracker and incident-reporting, continuous-improvement diff, cadence-derived next-review dates, plan_review_interval handling, multi-system coverage, UK ATRS citation, crosswalk enrichment toggle, citation format compliance, no-em-dash and no-hedging enforcement, Markdown section completeness, CSV row count, and graceful crosswalk-load-failure handling.

## Related

- EU AI Act, Article 72; Article 11 (technical documentation); Article 73 (incident reporting routing target).
- ISO/IEC 42001:2023, Clause 9.1; Annex A, Control A.6.2.6; Annex A, Control A.6.2.7; Clause 7.5.3.
- NIST AI RMF, MANAGE 4.1; MANAGE 4.2.
- UK ATRS, Section Risks (uk-jurisdiction systems).
- Skill references: [skills/post-market-monitoring/SKILL.md](../../skills/post-market-monitoring/SKILL.md).
- Upstream inputs: `metrics-collector` (KPI catalogue), `risk-register-builder` (residual risks), `ai-system-inventory-maintainer` (system identity).
- Downstream consumers: `nonconformity-tracker` (drift-and-bound triggers), `incident-reporting` (safety-event triggers), `management-review-packager` (review-schedule and continuous-improvement-loop sections).
