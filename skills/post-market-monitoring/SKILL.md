---
name: post-market-monitoring
version: 0.1.0
description: >
  Post-market monitoring plan operationalization for EU AI Act Article 72,
  ISO/IEC 42001:2023 Clause 9.1, and NIST AI RMF MANAGE 4.1 / 4.2. Produces
  the conforming post-market monitoring plan artifact (template, dimensions,
  cadence, trigger catalogue, response routing) regulators expect under
  Article 72(3) and 72(4). UK ATRS Section Risks attaches when the system
  is uk-jurisdiction.
frameworks:
  - EU AI Act (Regulation (EU) 2024/1689)
  - ISO/IEC 42001:2023
  - NIST AI RMF 1.0
  - UK ATRS Template v2.0
tags:
  - ai-governance
  - post-market-monitoring
  - eu-ai-act
  - iso42001
  - clause-9-1
  - manage-4-1
  - manage-4-2
  - article-72
  - aims
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the post-market monitoring plan as a single artifact that simultaneously satisfies EU AI Act Article 72, ISO/IEC 42001:2023 Clause 9.1, NIST AI RMF MANAGE 4.1 and 4.2, and UK ATRS Section Risks (for uk-jurisdiction systems).

The artifact is distinct from three sibling artifacts in the AIGovOps catalogue:

- `metrics-collector` is point-in-time KPI MEASUREMENT against the NIST MEASURE 2.x catalogue. It says what a metric was at one moment.
- `nonconformity-tracker` is INTERNAL Clause 10.2 corrective-action response when monitoring detects an issue.
- `incident-reporting` is the EXTERNAL statutory notification when an incident triggers Article 73, Colorado, or NYC deadlines.

`post-market-monitoring` is the PLAN that names what to monitor, at what cadence, how to detect signal, and how to route observed signals to the correct response mechanism (nonconformity-tracker, incident-reporting, management-review, risk-register-update, corrective-action-plan, or system-decommission). EU Article 72(3) instructs the Commission to publish a template for this plan; this skill ships a conforming template now.

## Scope

**In scope.** Post-market monitoring plan construction for an in-service AI system or programme of systems:

- Plan establishment and version control (Article 72(1), Clause 9.1, MANAGE 4.1).
- Per-dimension monitoring rows: cadence, method, data source, retention, owner, threshold, escalation path (Article 72(3) template substance).
- Trigger catalogue: per-trigger detection method, threshold rule, escalation path enum, notification recipients, framework citation justifying the routing decision.
- Chapter III alignment for EU high-risk-annex-i and high-risk-annex-iii systems (Article 72(2) continuous-evaluation expectation).
- Continuous-improvement loop record linking to a previous plan (NIST MANAGE 4.2).
- Review schedule: per-cadence next-review dates plus full-plan review date driven by `plan_review_interval_months`.

**Out of scope.**

- Metric COMPUTATION. The plan declares thresholds; metric computation is the MLOps pipeline's responsibility, surfaced by `metrics-collector`.
- Specific corrective-action selection. Triggers route to a response plugin; response selection is judgment-bound and handled by `nonconformity-tracker` or `incident-reporting`.
- Statutory notification authoring. Article 73 incident reports are produced by `incident-reporting`.
- Colorado SB 205 annual deployer impact assessment authoring. The plan is monitoring-adjacent and feeds the assessment but does not author it.

**Operating assumption.** The organization has an AI system inventory, a risk register, and at least one assigned owner role. Article 72 cannot be operationalized without those inputs.

## Framework Reference

**Authoritative sources.**

- EU AI Act (Regulation (EU) 2024/1689), Article 72 (Post-market monitoring system and plan), Article 11 (Technical documentation), Article 73 (Serious incident reporting; routing target).
- ISO/IEC 42001:2023, Clause 9.1 (Monitoring, measurement, analysis, evaluation), Annex A, Control A.6.2.6 (AI system operation and monitoring), Annex A, Control A.6.2.7 (AI system technical documentation), Clause 7.5.3 (Control of documented information).
- NIST AI RMF 1.0, MANAGE 4.1 (Post-deployment monitoring planned), MANAGE 4.2 (Continual improvement activities integrated).
- UK ATRS Template v2.0, Section Risks (https://www.gov.uk/government/publications/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies).

**Supplementary instruments tracked but not directly produced.**

- Colorado SB 205, Section 6-1-1703(3): annual deployer impact assessment is monitoring-adjacent.
- ISO/IEC 23894:2023 (AI risk management) informs monitoring-as-risk-control framing.

**Relationship to other frameworks.**

- ISO Clause 9.1 satisfies EU Article 72(1) and 72(2) per CEN-CENELEC JTC 21 working drafts. Confidence: high.
- ISO Clause 9.1 exact-matches NIST MANAGE 4.1 per NIST AI 600-1 Appendix A. Confidence: high.
- ISO Clause 9.1 partial-matches NIST MANAGE 4.2 (continual improvement). Confidence: high.
- EU Article 72(3) Commission template has no ISO equivalent (template specificity is EU-only). Confidence: high.

## Operationalizable Controls

Two-tier operationalization. Tier 1 (Automatable) covers plan-construction outputs that can be emitted from structured input. Tier 2 (Hybrid) covers the routing and response-selection junctions where a human practitioner confirms the determination.

| Tier | Sub-clause / Article | Artifact | Plugin field | Classification |
|---|---|---|---|---|
| T1.1 | Article 72(1); Clause 9.1; MANAGE 4.1 | Plan record (id, version, covered systems, lifecycle anchor) | `monitoring_plan` | Automatable |
| T1.2 | Article 72(3) template substance | Per-dimension monitoring rows | `per_dimension_monitoring` | Automatable |
| T1.3 | Article 72(2); Clause 9.3 | Trigger catalogue and escalation routing | `trigger_catalogue` | Hybrid (plugin attaches default routing; human confirms) |
| T1.4 | Article 72(2); Clause 9.1 | Chapter III alignment block (EU high-risk only) | `chapter_iii_alignment` | Automatable |
| T1.5 | Clause 9.1; MANAGE 4.2 | Review schedule | `review_schedule` | Automatable |
| T2.1 | MANAGE 4.2 | Continuous-improvement loop diff (predecessor link, change set) | `continuous_improvement_loop` | Hybrid (plugin records the link; practitioner authors the substantive diff) |

### Per-dimension to response-plugin routing table

| Dimension | Typical method | Default escalation path on threshold breach | Routing-citation rationale |
|---|---|---|---|
| `accuracy` | `telemetry` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `robustness` | `red-team-engagement` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `cybersecurity` | `logs` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `drift` | `telemetry` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `bias-fairness` | `audit-sampling` or `human-review-sampling` | `management-review` | ISO/IEC 42001:2023, Clause 9.3 |
| `privacy-leakage` | `telemetry` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `availability`, `latency`, `throughput` | `telemetry` | `nonconformity-tracker` | ISO/IEC 42001:2023, Clause 10.2 |
| `user-feedback`, `complaints-channel` | `complaints-channel` | `management-review` | ISO/IEC 42001:2023, Clause 9.3 |
| `incident-rate`, `safety-events` | `complaints-channel` or `logs` | `incident-reporting` | EU AI Act, Article 73 |
| `explainability-signals` | `audit-sampling` | `corrective-action-plan` | ISO/IEC 42001:2023, Clause 10.2 |

Practitioners override the default by supplying the trigger explicitly in `trigger_catalogue`.

## Output Standards

**Artifact type.** Post-market monitoring plan with per-dimension rows, trigger catalogue, Chapter III alignment block (when applicable), continuous-improvement loop, and review schedule.

**Format.** Structured dict (JSON-serializable). Renderers emit Markdown (audit evidence package) and CSV (per-dimension spreadsheet).

**Citation format.** All citations match STYLE.md exactly. ISO citations use `ISO/IEC 42001:2023, Clause X.X.X` or `ISO/IEC 42001:2023, Annex A, Control A.X.Y`. EU AI Act citations use `EU AI Act, Article XX, Paragraph X`. NIST citations use `NIST AI RMF, <FUNCTION> <Subcategory>`. UK ATRS uses `UK ATRS, Section <name>`.

**Canonical top-level citations emitted.**

- EU AI Act, Article 72, Paragraph 1
- EU AI Act, Article 72, Paragraph 2
- EU AI Act, Article 72, Paragraph 4
- EU AI Act, Article 11
- ISO/IEC 42001:2023, Clause 9.1
- ISO/IEC 42001:2023, Annex A, Control A.6.2.6
- NIST AI RMF, MANAGE 4.1
- NIST AI RMF, MANAGE 4.2
- UK ATRS, Section Risks (uk-jurisdiction systems only)

**Input schema.** See the plugin README for the full input dict contract.

**Output schema.** Top-level keys: `timestamp`, `agent_signature`, `framework`, `plan_id`, `plan_version`, `system_description_echo`, `monitoring_plan`, `per_dimension_monitoring`, `trigger_catalogue`, optional `chapter_iii_alignment`, `continuous_improvement_loop`, `review_schedule`, `citations`, `warnings`, `summary`, `reviewed_by`, optional `cross_framework_citations` and `cross_framework_references`.

**Jurisdiction.** Multi-jurisdiction. EU AI Act applies to EU-marketed high-risk systems. ISO Clause 9.1 applies wherever the AIMS is implemented. NIST MANAGE 4.x is voluntary worldwide. UK ATRS Section Risks attaches for UK public-sector systems.

## Limitations

- **The plugin produces the plan, not the monitoring data.** Metric computation, signal collection, and threshold evaluation are MLOps responsibilities. The plugin emits the structure those activities populate.
- **Trigger routing is deterministic, not discretionary.** Default routing is attached based on `escalation_path`; the practitioner can override per trigger but the plugin does not select severity classifications or weigh trade-offs.
- **No corrective-action prescription.** When a threshold breach occurs at runtime, response selection happens in `nonconformity-tracker` (internal) or `incident-reporting` (external). This plan only routes the signal.
- **Chapter III alignment is dimension-level, not control-level.** The plugin matches monitored dimensions to the dimension family expected by each Chapter III article. Article-level conformance assessment (Annex VI / Annex VII) is a separate certification activity.
- **Continuous-improvement diff requires practitioner review.** The plugin records the predecessor link and a scaffold but does not infer substantive change semantics from prior plan content.
- **Article 72(3) Commission template is not yet published as of skill version date.** The plan structure here reflects the substantive elements named in Article 72(3) (elements monitored, methods, frequency, indicators, responsibilities, trigger thresholds for corrective action). When the Commission publishes the implementing-act template, the plugin schema will be aligned in a minor version bump.

### Maintenance

ISO/IEC 42001:2023 Clause 9.1 is stable. EU AI Act Article 72 is in force; the Commission implementing-act template is forthcoming. NIST AI RMF MANAGE 4.x is stable in version 1.0. The skill requires no clause-text update between standard revisions; plugin schema is aligned to the Article 72(3) template when published.
