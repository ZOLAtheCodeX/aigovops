# Robustness Evaluation Operationalization Map

Working document for the `robustness-evaluation` skill. Maps each EU AI Act Article 15 paragraph and each related ISO 42001 / NIST AI RMF reference to the A/H/J operationalizability classification and the AIGovOps artifact vocabulary. Same methodology as `skills/iso42001/operationalization-map.md`.

**Validation status.** Section references validated against the EU AI Act (Regulation (EU) 2024/1689), ISO/IEC 42001:2023 Annex A, and NIST AI RMF 1.0 on 2026-04-18.

**Classification legend.**

- A: automatable. The plugin derives output deterministically from structured input.
- H: hybrid. The plugin assembles and validates; a human provides key substantive content.
- J: judgment. A qualified human (evaluator, counsel, notified body, senior reviewer) must decide.

**Leverage legend.**

- H: strong cost reduction from automation.
- M: moderate.
- L: low.

## EU AI Act Article 15: Accuracy, robustness, cybersecurity

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Article 15, Paragraph 1 | Tri-requirement: accuracy, robustness, cybersecurity throughout lifecycle | A | `dimension_assessments` | H | Plugin verifies presence of all three core dimensions for high-risk EU systems and emits BLOCKING warnings on omission. |
| Article 15, Paragraph 2 | Accuracy metrics declared in instructions for use (Article 13) | H | `art_15_2_declaration_status` | M | Plugin emits a cross-plugin action item with primary_metric, metric_value, and declared_threshold; practitioner declares in Article 13 instructions and routes to soa-generator and audit-log-generator outputs. |
| Article 15, Paragraph 3 | Robustness to errors, faults, inconsistencies; backup plans (fail-safe design) | A | `backup_plan_status`, `dimension_assessments[fail-safe-design]` | M | Plugin enforces presence of `backup_plan_ref` for high-risk EU systems and emits BLOCKING warning on absence. |
| Article 15, Paragraph 4 | Resilience against unauthorised alteration of use, output, performance | A | `adversarial_posture` | H | Plugin aggregates worst-of resilience level across `adversarial-robustness`, `data-poisoning-resistance`, `model-evasion-resistance`, and `confidentiality` sub-dimensions. |
| Article 15, Paragraph 5 | Feedback loops, concept drift, continuous learning | A | `concept_drift_monitoring_status` | M | Plugin enforces presence of `concept_drift_monitoring_ref` for continuously-learning systems. |
| Article 13 (cross-reference) | Instructions for use carry the declared accuracy metric | H | external (instructions for use) | M | Plugin surfaces the declaration action item; practitioner edits the instructions for use document. |
| Article 43 (cross-reference) | Conformity assessment may require independent verification | J | `evaluator_independence_note` | L | Plugin emits a note when `evaluator_independence == "internal-team"`; notified-body pathway selection is counsel-side. |

## ISO/IEC 42001:2023 Annex A Control A.6.2.4

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| A.6.2.4 Verification and validation | Per-dimension test method, dataset, evidence | H | `dimension_assessments[*].test_method`, `dataset_ref`, `evidence_ref` | M | Plugin requires `test_method` and `evidence_ref` per dimension; missing values surface as warnings. |
| A.6.2.5 AI system deployment (cross-reference) | Operational fail-safe wiring | H | external (deployment runbook) | M | Plugin records `backup_plan_ref` pointer; deployment runbook lives outside. |
| A.6.2.6 AI system operation and monitoring (cross-reference) | Concept-drift detection in production | H | `concept_drift_monitoring_status` | M | Plugin records the pointer to the monitoring plan produced by `post-market-monitoring`. |

## NIST AI RMF 1.0

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MEASURE 2.5 (valid and reliable) | Validity and reliability measurement | A | `dimension_assessments[accuracy]`, `dimension_assessments[robustness]` | H | Plugin attaches MEASURE 2.5 to accuracy and robustness assessments. |
| MEASURE 2.6 (safe) | Safety measurement | A | `dimension_assessments[robustness]`, `dimension_assessments[fail-safe-design]` | H | Plugin attaches MEASURE 2.6 to robustness and fail-safe-design assessments. |
| MEASURE 2.7 (security and resilience) | Security and resilience measurement | A | `dimension_assessments[cybersecurity]`, `adversarial_posture` | H | Plugin attaches MEASURE 2.7 to cybersecurity and to all Article 15(4) sub-dimensions. |

## UK ATRS Section Tool details

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Section Tool details (model performance) | Performance metric publication | H | external (ATRS record) | L | Plugin appends `UK ATRS, Section Tool details` to top-level citations when UK is in jurisdiction; the actual ATRS record is produced by `uk-atrs-recorder`. |

## Colorado SB 205 Section 6-1-1702(1)

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Section 6-1-1702(1) duty of reasonable care | Documented care evidence | H | external (compliance record) | L | Plugin appends the citation when Colorado is in jurisdiction; the actual compliance record is produced by `colorado-ai-act-compliance`. |
| Section 6-1-1702(7) and 6-1-1703(7) (cross-reference) | External disclosure on discrimination finding | J | external (incident report) | L | Plugin does not file; failures route to `incident-reporting` for deadline computation. |

## Composition with sibling plugins

### Ongoing KPI sibling: `metrics-collector`

The metrics-collector is the ongoing surface; the robustness-evaluator is the point-in-time gate. A metrics-collector threshold breach for an Article 15 dimension is a signal to schedule a fresh robustness-evaluator invocation. The two plugins do not share storage; aigovclaw orchestrates the routing.

### Forward-looking sibling: `post-market-monitoring`

The post-market-monitoring plugin produces the monitoring PLAN (cadence, owners, thresholds). The robustness-evaluator produces the EXECUTION RECORD against that plan at the cadence the plan declares.

### Internal failure sibling: `nonconformity-tracker`

A `pass: False` on any dimension or `not-verified` on an Article 15(4) sub-dimension is an internal Clause 10.2 nonconformity. The robustness-evaluator output is the source citation for the nonconformity record; aigovclaw routes the failure into the tracker.

### External failure sibling: `incident-reporting`

When an evaluation failure also crosses a statutory threshold (Article 73 serious-incident definition, Section 6-1-1701(1) algorithmic-discrimination definition), the failure is also a reportable incident. The robustness-evaluator record provides the evidence base; the incident-reporting plugin computes deadlines and assembles report drafts.

## Field-level traceability

Each `dimension_assessment` entry carries `citations` populated as follows:

| Dimension | Citations |
|---|---|
| `accuracy` | `EU AI Act, Article 15, Paragraph 1`; `EU AI Act, Article 15, Paragraph 2`; `MEASURE 2.5`; `ISO/IEC 42001:2023, Annex A, Control A.6.2.4` |
| `robustness` | `EU AI Act, Article 15, Paragraph 1`; `EU AI Act, Article 15, Paragraph 3`; `MEASURE 2.5`; `MEASURE 2.6`; `ISO/IEC 42001:2023, Annex A, Control A.6.2.4` |
| `cybersecurity` | `EU AI Act, Article 15, Paragraph 1`; `EU AI Act, Article 15, Paragraph 4`; `MEASURE 2.7`; `ISO/IEC 42001:2023, Annex A, Control A.6.2.4` |
| `adversarial-robustness`, `data-poisoning-resistance`, `model-evasion-resistance`, `confidentiality` | `EU AI Act, Article 15, Paragraph 4`; `MEASURE 2.7`; `ISO/IEC 42001:2023, Annex A, Control A.6.2.4` |
| `fail-safe-design` | `EU AI Act, Article 15, Paragraph 3`; `MEASURE 2.6`; `ISO/IEC 42001:2023, Annex A, Control A.6.2.4` |
| `concept-drift-handling`, `continuous-learning-controls` | `EU AI Act, Article 15, Paragraph 5`; `MEASURE 2.5`; `ISO/IEC 42001:2023, Annex A, Control A.6.2.4` |
