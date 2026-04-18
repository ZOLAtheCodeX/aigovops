# Internal audit operationalization map

Per-sub-clause mapping from ISO/IEC 42001:2023 Clause 9.2 text to `internal-audit-planner` plugin input and output fields.

## Scope

This map covers Clause 9.2.1 (General) and Clause 9.2.2(a) through (e) (Internal audit programme). It also records the two adjacent clauses that bracket Clause 9.2 in the AIMS lifecycle: Clause 7.5.3 (retention of documented information, cited at 9.2.2(e)) and Clause 9.3 (management review, downstream consumer of audit results).

## Clause 9.2.1: General

| Requirement | Plugin field | Consumer flow |
|---|---|---|
| Audits at planned intervals | `audit_frequency_months` input; `audit_schedule[].planned_start_date` and `planned_end_date` | Consumed by Clause 9.3.2 management review as `audit_results`. |
| Conformity to organization's own requirements | `audit_criteria` input (list must include organizational policies) | Audit team verifies each cycle. Findings to `nonconformity-tracker`. |
| Conformity to ISO/IEC 42001:2023 | `audit_criteria` input must include `"ISO/IEC 42001:2023"` (structural invariant enforced by `ValueError` at validation time) | Programme-level conformity assertion. |
| Effective implementation and maintenance | `criteria_mapping`; `audit_schedule[].methods_selected` | Auditor methodology selection; results feed Clause 10 continual improvement. |

## Clause 9.2.2(a): Plan, establish, implement, maintain the programme

| Sub-requirement | Plugin field | Consumer flow |
|---|---|---|
| Frequency | `audit_frequency_months` input; derived cycle count | Produces the rolling 12-month programme structure. |
| Methods | `audit_schedule[].methods_selected`; default `document-review`, `interview`, `sampling`; `technical-test` added automatically when scope includes A.7 or A.8. | Methods drive auditor toolkit selection. |
| Responsibilities | `audit_schedule[].assigned_auditors` | Paired with `impartiality_assessment` per 9.2.2(c). |
| Planning | `audit_schedule[].planned_start_date`, `planned_end_date` | Calendar handoff to audit team. |
| Reporting requirements | `audit_schedule[].reporting_recipients`; default `["AI Governance Officer", "Top Management"]` | Routes to Clause 9.2.2(d). |
| Importance of processes | `management_system_risk_register_ref` input (echoed in `criteria_mapping.risk_register_reference`) | Risk register drives cycle-by-cycle prioritization. |
| Results of previous audits | `prior_audit_findings` input | Severity-weighted scoring reorders the scope list so areas with recent critical findings land in the earliest cycle. |

## Clause 9.2.2(b): Define audit criteria and scope for each audit

| Sub-requirement | Plugin field | Consumer flow |
|---|---|---|
| Audit criteria | `audit_criteria` input; echoed per-cycle in `audit_schedule[].audit_criteria` and per-area in `criteria_mapping[].audit_criteria_documents` | Each cycle is rerun-reproducible from the criteria list. |
| Scope per audit | `audit_schedule[].scope_this_cycle` | Scope is a subset of declared `scope.clauses_in_scope + scope.annex_a_in_scope`, partitioned by cadence. |
| Authoritative citation per scope area | `criteria_mapping[].authoritative_citation` | Enforces STYLE.md citation format. |

## Clause 9.2.2(c): Select auditors; ensure objectivity and impartiality

| Sub-requirement | Plugin field | Consumer flow |
|---|---|---|
| Auditor selection | `auditor_pool` input | Round-robin assignment in the plugin; human reviewer re-allocates specialists. |
| Objectivity | `auditor_pool[].independence_level` (enum `independent`, `departmental-separation`, `management-delegated`, `insufficient`) | Feeds `impartiality_assessment.tier_counts`. |
| Impartiality | `auditor_pool[].own_areas`; conflict rule: auditor assigned to any `own_areas` value or `independence_level: insufficient` triggers warning | Warning text includes cycle and area; reviewer must reassign before issuing the audit notice. |
| Per-cycle independence presence | `impartiality_assessment.per_cycle[].includes_independent_auditor` | Reviewer can verify at a glance which cycles have at least one `independent` auditor on roster. |

## Clause 9.2.2(d): Report results to relevant management

| Sub-requirement | Plugin field | Consumer flow |
|---|---|---|
| Relevant management identified | `reporting_recipients` input; default `["AI Governance Officer", "Top Management"]` | Echoed on every cycle. |
| Results reported | Consumed by `management-review-packager.generate_review_package(inputs)` `audit_results` category | The planner produces the schedule; auditors produce the report; the management-review-packager routes it into Clause 9.3.2. |

## Clause 9.2.2(e): Retain documented information

| Sub-requirement | Plugin field | Consumer flow |
|---|---|---|
| Evidence of audit programme | The plan dict itself; `timestamp`, `agent_signature`, `citations` | Stored in audit-evidence archive per Clause 7.5.3. |
| Evidence of audit results | Nonconformity records (via `nonconformity-tracker`) + audit report artifacts (human-authored) + plan dict | Composite evidence bundle. |
| Retention rule | Citation `ISO/IEC 42001:2023, Clause 7.5.3` attached at programme and schedule levels | Downstream retention policy governed by organizational DMS. |

## Clause 9.3: Downstream consumer

| Sub-requirement | Plugin field | Consumer flow |
|---|---|---|
| Management review input category `audit_results` | `management-review-packager.generate_review_package(inputs)` consumes the internal-audit-planner `summary` and `audit_schedule` fields | Clause 9.2 output is a direct input to Clause 9.3.2. |

## Cross-framework references (when `enrich_with_crosswalk: True`)

| Target framework | Target ref | Relationship | Confidence |
|---|---|---|---|
| NIST AI RMF 1.0 | MEASURE 4.1 | partial-match | medium |
| NIST AI RMF 1.0 | MEASURE 4.2 | partial-match | medium |
| NIST AI RMF 1.0 | MEASURE 4.3 | partial-match | medium |
| EU AI Act | Article 17, Paragraph 1, Point (d) | partial-satisfaction | high |
| EU AI Act | Article 17, Paragraph 1, Point (k) | satisfies | high |

These references are also registered in `plugins/crosswalk-matrix-builder/data/iso42001-nist-ai-rmf.yaml` and `plugins/crosswalk-matrix-builder/data/iso42001-eu-ai-act.yaml`.
