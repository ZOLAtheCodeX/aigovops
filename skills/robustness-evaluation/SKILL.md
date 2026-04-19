---
name: robustness-evaluation
version: 0.1.0
description: >
  Point-in-time robustness evaluation skill. Operationalizes EU AI Act
  Article 15 (Accuracy, robustness, cybersecurity), ISO/IEC 42001:2023
  Annex A Control A.6.2.4 (Verification and validation of the AI system),
  and NIST AI RMF 1.0 MEASURE 2.5, 2.6, and 2.7. Produces an evaluation
  record distinct from the metrics-collector ongoing KPI surface and the
  post-market-monitoring plan. Composes with nonconformity-tracker and
  incident-reporting on failure.
frameworks:
  - ISO/IEC 42001:2023
  - NIST AI RMF 1.0
  - EU AI Act (Regulation (EU) 2024/1689)
  - UK Algorithmic Transparency Recording Standard
  - Colorado Senate Bill 24-205
tags:
  - ai-governance
  - verification-validation
  - robustness
  - cybersecurity
  - accuracy
  - adversarial-robustness
  - eu-ai-act
  - iso42001
  - nist-ai-rmf
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the verification-and-validation evidence that a notified body or auditor reviews to confirm the Article 15 tri-requirement (accuracy, robustness, cybersecurity) has been verified for a specific AI system at a specific point in time. The evaluation record is the artifact that supports Article 43 conformity assessment, ISO 42001 certification audit evidence under Annex A Control A.6.2.4, and the NIST AI RMF MEASURE 2.5 / 2.6 / 2.7 measurement steps.

The skill pairs with the [`robustness-evaluator`](../../plugins/robustness-evaluator/) plugin. The plugin validates a precomputed evaluation submission, attaches per-dimension citations, aggregates Article 15(4) adversarial posture using a worst-of resilience-level rule, computes lifecycle trend against a previous evaluation reference, and emits a cross-plugin action item for the Article 15(2) instructions-for-use declaration. Test execution is upstream; the plugin records and validates results.

## Scope

**In scope.**

- EU AI Act Article 15 paragraphs (1) through (5), covering the tri-requirement, instructions-for-use declaration, fail-safe design, adversarial resilience, and feedback-loop handling.
- ISO/IEC 42001:2023 Annex A Control A.6.2.4 (verification and validation) as the core control reference.
- NIST AI RMF 1.0 MEASURE 2.5 (valid and reliable), 2.6 (safe), 2.7 (security and resilience).
- UK ATRS Section Tool details model-performance disclosure when the system has UK jurisdiction.
- Colorado SB 205 Section 6-1-1702(1) duty of reasonable care framing when the system is in scope of the Colorado AI Act.
- Composition with `nonconformity-tracker` (internal Clause 10.2 corrective action) and `incident-reporting` (external Article 73 or Section 6-1-1702(7) / 6-1-1703(7) notification) when an evaluation surfaces a failure that crosses the relevant threshold.

**Out of scope.**

- Test execution itself. The MLOps pipeline runs holdout, stress, adversarial, fuzzing, membership-inference, poisoning, and evasion tests. The plugin records the precomputed results.
- Threshold determination. Whether an F1 of 0.82 is acceptable for a clinical triage system is a domain judgment. The plugin records `declared_threshold` and the pass/fail computation; it does not select the threshold.
- Sectoral verification regimes (medical-device clinical evaluation under Regulation (EU) 2017/745, financial-services model risk management under SR 11-7 or OSFI E-23). These layer alongside Article 15 and are not crosswalked here.
- Article 43 conformity assessment workflow. The skill produces evidence consumed by conformity assessment; it does not perform conformity assessment.

**Operating assumption.** The user organization has executed the verification tests and now needs to record the outcome in an audit-ready form, with the correct citations, aggregations, and cross-plugin action items.

## Framework Reference

**Authoritative sources.**

- EU AI Act, Regulation (EU) 2024/1689: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689. Article 15 covers accuracy, robustness, and cybersecurity.
- ISO/IEC 42001:2023, Annex A, Control A.6.2.4 (Verification and validation of the AI system).
- NIST AI Risk Management Framework 1.0 (AI RMF 1.0), MEASURE function: https://www.nist.gov/itl/ai-risk-management-framework.
- UK Algorithmic Transparency Recording Standard, Section Tool details: https://www.gov.uk/government/publications/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies.
- Colorado Senate Bill 24-205, codified at Colorado Revised Statutes Title 6, Article 1, Part 17.

**Article 15 paragraph map.**

| Paragraph | Subject | Plugin field |
|---|---|---|
| Article 15, Paragraph 1 | Tri-requirement: accuracy, robustness, cybersecurity throughout lifecycle | `dimension_assessments` for `accuracy`, `robustness`, `cybersecurity` |
| Article 15, Paragraph 2 | Accuracy metrics declared in instructions for use (Article 13) | `art_15_2_declaration_status` |
| Article 15, Paragraph 3 | Robustness to errors, faults, inconsistencies; backup plans (fail-safe) | `backup_plan_status`, `dimension_assessments[fail-safe-design]` |
| Article 15, Paragraph 4 | Resilience against unauthorised alteration of use, output, performance | `adversarial_posture` (worst-of aggregation across `adversarial-robustness`, `data-poisoning-resistance`, `model-evasion-resistance`, `confidentiality`) |
| Article 15, Paragraph 5 | Feedback loops, concept drift, continuous learning | `concept_drift_monitoring_status`, `dimension_assessments[concept-drift-handling]`, `dimension_assessments[continuous-learning-controls]` |

## Operationalizable Controls

The skill operationalizes one Tier 1 capability and composes with three siblings.

**Tier 1: per-dimension evaluation record.**

- Input: precomputed evaluation results per dimension, evaluation date, evaluator identity, evaluator independence, optional backup-plan reference, optional concept-drift-monitoring reference, optional previous-evaluation reference.
- Processing: per-dimension assessment with citations, Article 15(4) adversarial-posture aggregation, Article 15(2) declaration action item, Article 15(3) backup-plan check, Article 15(5) feedback-loop check, evaluator-independence note, optional trend-delta against previous evaluation.
- Output: `dimension_assessments`, `adversarial_posture`, `art_15_2_declaration_status`, `backup_plan_status`, `concept_drift_monitoring_status`, `trend_delta`, `cross_framework_citations`, `warnings`, `summary`.
- Plugin: `evaluate_robustness()`, `render_markdown()`, `render_csv()`.

**Composition with `metrics-collector`.** The metrics-collector is the ongoing KPI surface; it tracks production metrics over time. The robustness-evaluator is a point-in-time evaluation against a declared threshold. A metrics-collector threshold breach for an Article 15 dimension is a signal to schedule a fresh robustness-evaluator run. The two plugins do not share storage; aigovclaw routes the breach into a re-evaluation workflow.

**Composition with `post-market-monitoring`.** The post-market-monitoring plugin produces the monitoring PLAN (cadence, dimensions, thresholds, owners). The robustness-evaluator produces the EXECUTION RECORD against that plan. A post-market plan with an `accuracy` dimension at quarterly cadence implies a robustness-evaluator invocation each quarter.

**Composition with `nonconformity-tracker`.** A robustness-evaluator output with `pass: False` on any dimension or `not-verified` resilience on an Article 15(4) sub-dimension is an internal nonconformity. The aigovclaw runtime routes the failure into a Clause 10.2 record via `nonconformity-tracker` for root-cause analysis and corrective action.

**Composition with `incident-reporting`.** When an evaluation failure also crosses a statutory threshold (Article 73 serious-incident definition, Section 6-1-1701(1) algorithmic-discrimination definition), the failure is also an external reportable incident. The robustness-evaluator record provides the evidence base; the incident-reporting plugin computes the deadline matrix.

See [`operationalization-map.md`](operationalization-map.md) for the per-paragraph mapping.

## Output Standards

All outputs carry citations in [STYLE.md](../../STYLE.md) format:

- `EU AI Act, Article 15, Paragraph 1` through `EU AI Act, Article 15, Paragraph 5`
- `ISO/IEC 42001:2023, Annex A, Control A.6.2.4`
- `MEASURE 2.5`, `MEASURE 2.6`, `MEASURE 2.7`
- `UK ATRS, Section Tool details` (when UK jurisdiction)
- `Colorado SB 205, Section 6-1-1702(1)` (when Colorado jurisdiction)

Resilience levels use a fixed four-value vocabulary: `verified-strong`, `verified-adequate`, `verified-weak`, `not-verified`. Adversarial-posture aggregation uses a worst-of rule: the overall posture is the weakest sub-dimension level. Trend deltas use `improving`, `stable`, `degrading`, `new`, `indeterminate`. The plugin emits `BLOCKING` warnings for missing core dimensions on a high-risk EU system and missing backup plan; non-blocking warnings for missing concept-drift reference. No em-dashes. No emojis. No hedging.

## Limitations

1. **No test execution.** The plugin validates and aggregates precomputed results. Test execution is the MLOps and red-team pipelines' responsibility.
2. **No threshold selection.** The plugin records `declared_threshold` and computes pass/fail; it does not propose the threshold. Threshold selection requires domain judgment.
3. **No Article 43 conformity assessment.** The plugin produces evidence consumed by conformity assessment workflows; it is not a notified-body assessment.
4. **Single point-in-time per invocation.** Lifecycle posture requires repeated invocations; trend computation requires the previous output as input.
5. **No automated cross-system aggregation.** The plugin records one system per invocation. Portfolio-level posture requires aggregation outside the plugin.
