---
name: bias-evaluation
version: 0.1.0
description: >
  Fairness and bias evaluation operationalization for AI systems.
  Computes standard fairness metrics (selection rate, impact ratio,
  demographic parity difference, equalized odds difference, predictive
  parity difference, statistical parity difference) from caller-supplied
  per-group counts, and applies jurisdictional rule sets covering NIST
  AI RMF 1.0 MEASURE 2.11, EU AI Act Article 10(4) bias examination,
  NYC LL144 Section 5-301 four-fifths rule, Colorado SB 205
  Section 6-1-1702(1) reasonable-care duty, Singapore MAS Veritas
  fairness methodology, and ISO/IEC 42001 Annex A Control A.7.4.
  ISO/IEC TR 24027:2021 referenced as advisory.
frameworks:
  - NIST AI RMF 1.0
  - EU AI Act (Regulation (EU) 2024/1689)
  - NYC Local Law 144 of 2021
  - Colorado Senate Bill 24-205 (Colorado AI Act)
  - Singapore MAS Veritas (2022)
  - ISO/IEC 42001:2023
  - ISO/IEC TR 24027:2021
tags:
  - ai-governance
  - fairness
  - bias
  - measure-2-11
  - ll144
  - eu-ai-act
  - colorado-sb-205
  - veritas
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes fairness and bias evaluation as a cross-jurisdictional governance activity. It is the upstream computational anchor for any plugin that consumes fairness metrics: the NYC LL144 audit packager, the risk-register builder (bias category rows), the SoA generator (A.7.4 evidence), and the certification-readiness consumer.

The skill pairs with the `bias-evaluator` plugin. The plugin computes the metrics; the skill documents what the metrics mean under each jurisdiction, which thresholds apply where, and how downstream artifacts cite the result.

The plugin does not perform model inference. It computes deterministically from per-group counts that the caller has produced against an evaluation dataset. When ground-truth labels are absent, ground-truth-requiring metrics are not silently substituted; they emit a `requires-ground-truth` status. The plugin does not assign an aggregate bias score.

## Scope

**In scope.**

- Selection rate, impact ratio, demographic parity difference, statistical parity difference, equalized odds difference, predictive parity difference, computed per protected-attribute group.
- Intersectional analysis on compound-attribute group keys (for example race-by-sex), with small-sample warnings surfaced automatically.
- Jurisdictional rule application: NYC LL144 four-fifths threshold, EU AI Act Article 10(4) bias examination obligation, Colorado SB 205 reasonable-care duty, Singapore MAS Veritas methodology recommendations, ISO/IEC 42001 Annex A Control A.7.4 data quality, NIST AI RMF MEASURE 2.11 fairness evaluation.
- Citation rendering for downstream consumers (risk register, SoA, NYC LL144 audit package, evidence bundles).

**Out of scope.**

- Model inference. The caller computes per-group outcomes; the plugin computes metrics.
- Aggregate bias scoring. The skill emits per-metric results; aggregate verdicts require human judgment in context.
- Protected-group definition. Protected-attribute lists are organizational and legal determinations supplied by the caller. The skill records what is supplied.
- Counsel-grade jurisdictional applicability determinations. The skill applies the rule when the caller declares it in scope.
- Causal attribution of disparate outcomes to specific model components. The skill computes outcome-level metrics; root-cause attribution is downstream interpretive work.

**Operating assumption.** The user organization either operates an AI system in a high-risk sector (employment, credit, lending, insurance, healthcare, education) where bias evaluation is statutorily required, or operates a system in another sector where bias evaluation is recommended as a matter of trustworthy-AI practice. The skill produces auditable evidence in either case.

## Framework Reference

**NIST AI RMF 1.0, MEASURE 2.11.** Authoritative source: https://www.nist.gov/itl/ai-risk-management-framework. MEASURE 2.11 requires fairness and bias to be evaluated and documented for AI systems. The subcategory does not prescribe specific metrics; the AI RMF Playbook supplies implementation suggestions. NIST SP 1270 (Towards a Standard for Identifying and Managing Bias in Artificial Intelligence) is the supporting technical document.

**EU AI Act, Article 10, Paragraph 4.** Authoritative source: https://eur-lex.europa.eu/eli/reg/2024/1689/oj. Article 10(4) requires providers of high-risk AI systems to examine training, validation, and testing datasets for possible biases that may affect health, safety, or fundamental rights, and to take appropriate measures to detect, prevent, and mitigate them. The examination obligation is process-based; specific thresholds are organizational policy.

**NYC Local Law 144 of 2021, DCWP Final Rule, Section 5-301.** Authoritative source: https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/. Section 5-301 requires selection rates and impact ratios per protected category for any AEDT used for NYC candidates or employees. The four-fifths rule (impact ratio < 0.8 indicates a disparate impact concern) operationalizes the EEOC Uniform Guidelines on Employee Selection Procedures (29 CFR Part 1607). NYC LL144 Final Rule, Section 5-301(b) addresses continuous-output cases.

**Colorado SB 205 (Colorado AI Act), Section 6-1-1702(1).** Authoritative source: https://leg.colorado.gov/bills/sb24-205. Codified under Colorado Revised Statutes Title 6, Article 1, Part 17. Section 6-1-1702(1) imposes a duty of reasonable care on developers of high-risk AI systems to protect consumers from any known or reasonably foreseeable risks of algorithmic discrimination. Section 6-1-1703(1) imposes a parallel duty on deployers. The statute does not specify a threshold; reasonable care is a process-and-documentation determination.

**Singapore MAS Veritas (2022), Fairness Methodology.** Authoritative source: https://www.mas.gov.sg/. Veritas is the Monetary Authority of Singapore's industry fairness methodology, developed iteratively with the financial-industry consortium. The methodology emphasizes context-aware metric selection (the appropriate fairness measure depends on the use-case harm profile), balanced-dataset orientation, and independent internal validation. Maps to MAS FEAT Principles (2018), Principle Fairness.

**ISO/IEC 42001:2023, Annex A, Control A.7.4 (Quality of data for AI systems).** Authoritative source: https://www.iso.org/standard/81230.html. A.7.4 requires the organization to define and document data-quality requirements for AI systems. Bias evaluation results constitute data-quality evidence under A.7.4 because dataset composition is a primary driver of measured group-level disparity.

**ISO/IEC TR 24027:2021 (Bias in AI systems and AI aided decision making).** Advisory technical report. Cited for completeness when bias methodology context is required; the technical report does not establish a conformance obligation.

**Crosswalks.** Anchored on NIST MEASURE 2.11 and ISO/IEC 42001:2023 A.7.4; see `plugins/crosswalk-matrix-builder/data/iso42001-nist-ai-rmf.yaml`. The mapping records that A.7.4 partially addresses MEASURE 2.11 by way of upstream data-quality controls; explicit examination methodology comes from the NIST subcategory.

## Operationalizable Controls

One Tier 1 operationalization, one Tier 2.

### T1.1 Per-protected-group fairness metrics with jurisdictional rules

Class: A. Artifact: `bias-evaluation-report`. Leverage: H. Consumer: `plugins/bias-evaluator`.

**Requirement summary.** Compute the standard fairness metrics across protected-attribute groups, apply jurisdictional rules, surface small-sample and ground-truth-availability constraints, and emit downstream-consumable per-metric results plus rule findings.

**Inputs.**

- `system_description`: dict including a `sector` field. Sector controls the recommended-not-mandated note for sectors outside the canonical high-risk family.
- `evaluation_data`: dict with `dataset_ref`, `evaluation_date`, `sample_size`, `ground_truth_available` (bool), and `per_group_counts` mapping group keys to count dicts (`total`, `selected`, and where ground truth is available, `true_positive`, `false_positive`, `true_negative`, `false_negative`, `positive_predictive_value`).
- `protected_attributes`: list of `{attribute_name, categories_present}`.
- `metrics_to_compute`: subset of the six supported metrics. Default `["selection-rate", "impact-ratio"]`.
- `jurisdiction_rules`: subset of the six supported rule sets. Default `[]`.
- `intersectional_analysis`: bool, default False. When True, the plugin separately computes metrics on compound-attribute keys (containing `|`).
- `organizational_thresholds`: dict mapping metric to threshold for EU AI Act Article 10(4) organizational-compliance status.
- `minimum_group_size`: int, default 30. Groups below this are flagged underpowered.
- `enrich_with_crosswalk`: bool, default True.

**Group-key convention.** Group keys are strings of the form `attribute:value` for single-attribute groups, or `attribute_a:value_a|attribute_b:value_b` for intersectional groups. The `|` separator is the canonical compound delimiter; the plugin splits compound keys from single-attribute keys automatically.

**Process.**

1. Validate inputs. Raise `ValueError` on missing required fields, invalid metrics, or invalid jurisdiction rules.
2. Split per-group counts into single-attribute and intersectional buckets.
3. Flag underpowered groups (total below `minimum_group_size`).
4. For each requested metric, compute the value on single-attribute groups. Ground-truth-requiring metrics emit `requires-ground-truth` when ground truth is unavailable.
5. If intersectional analysis is enabled, repeat the metric computation on compound-attribute keys.
6. Apply jurisdictional rules against the per-metric results, producing one rule_findings entry per rule with `pass_fail_or_concern`, `computed_metric`, `threshold_used`, `citation`, and `rationale`.
7. Optionally enrich with cross-framework citations via the crosswalk module.
8. Emit the report dict.

**Output artifact.** `bias-evaluation-report`. Fields:

- `timestamp`, `agent_signature`, `framework`.
- `system_description_echo`, `evaluation_data_echo`, `protected_attributes_echo`.
- `per_metric_results`: list of metric dicts, each with metric name, value (or per-group dict for selection rate), citation, and where applicable status, max-difference pair, per-group TPR or PPV.
- `intersectional_results`: same structure when enabled.
- `rule_findings`: per-rule outcome with citation and rationale.
- `underpowered_groups`: groups flagged below `minimum_group_size`.
- `citations`: top-level applicable citations.
- `warnings`: content gaps and small-sample notices.
- `cross_framework_citations`: when enrichment ran.
- `summary`: aggregate counts.

Rendering: JSON for programmatic consumption; Markdown for review packages; CSV for spreadsheet ingestion (one row per per_metric_result entry).

**Citation anchors.** Top-level citations always include `NIST AI RMF, MEASURE 2.11`, `ISO/IEC 42001:2023, Annex A, Control A.7.4`, and `ISO/IEC TR 24027:2021`. Per-rule citations follow the rule table below.

| Rule id | Citation | Pass condition |
|---|---|---|
| `nyc-ll144-4-5ths` | `NYC LL144 Final Rule, Section 5-301` and `NYC DCWP AEDT Rules, 6 RCNY Section 5-301(b)` | impact_ratio >= 0.8 |
| `eu-ai-act-art-10-4` | `EU AI Act, Article 10, Paragraph 4` | At least one bias metric computed; organizational-threshold compliance status when thresholds supplied |
| `colorado-sb-205-reasonable-care` | `Colorado SB 205, Section 6-1-1702(1)` | Bias evaluation present in record |
| `singapore-veritas-fairness` | `MAS Veritas (2022)` | Methodology next-steps emitted |
| `iso-42001-a-7-4` | `ISO/IEC 42001:2023, Annex A, Control A.7.4` | Bias metric computed |
| `nist-measure-2-11` | `NIST AI RMF, MEASURE 2.11` | Bias metric computed |

**Auditor acceptance criteria.**

- Every metric record carries the subcategory or rule citation.
- Ground-truth-requiring metrics never have a value when `ground_truth_available=False`; the `requires-ground-truth` status is explicit.
- Impact-ratio division-by-zero is handled (status `undefined-division-by-zero` plus warning), not silently treated as a passing result.
- Small-sample groups are flagged in `underpowered_groups` and in `warnings`; downstream consumers can choose to suppress the metric for those groups.
- The plugin does not assign an aggregate bias score; aggregate interpretation requires human judgment.

**Human-review gate.** Protected-group definitions, organizational thresholds, jurisdictional applicability determinations, and aggregate cross-metric verdicts are human decisions. The plugin executes the computation; the auditor or governance reviewer interprets the result.

### T2.1 Continuous-output AEDT case

Class: H. Artifact: `bias-evaluation-report` with continuous-output extension. Leverage: M.

NYC LL144 Final Rule Section 5-301(b) addresses AEDTs that produce continuous outputs (a numerical risk score) rather than binary screening outcomes. The plugin's standard inputs assume binary selection counts; for continuous-output AEDTs the caller bins the score into a binary selection by applying the operational threshold (the score above which the candidate would be advanced). The binned counts are then supplied as `selected` per group. Documentation requirements: cite Section 5-301(b) and record the binning threshold used.

## Output Standards

All outputs produced by this skill conform to the canonical output standards defined in [STYLE.md](../../STYLE.md). Skill-specific additions:

**Citation format.** All citations use the prefixes defined in STYLE.md:

- NIST: `NIST AI RMF, MEASURE 2.11`.
- EU AI Act: `EU AI Act, Article 10, Paragraph 4`.
- NYC LL144: `NYC LL144 Final Rule, Section 5-301`; for continuous-output cases `NYC DCWP AEDT Rules, 6 RCNY Section 5-301(b)`.
- Colorado: `Colorado SB 205, Section 6-1-1702(1)`.
- Singapore Veritas: `MAS Veritas (2022)`.
- ISO 42001 Annex A: `ISO/IEC 42001:2023, Annex A, Control A.7.4`.
- ISO/IEC TR 24027:2021 cited verbatim with no clause suffix; the technical report is advisory.

**No aggregate score.** Outputs do not assign a single overall bias score. Per-metric values plus per-rule findings are emitted; aggregation is a human interpretive decision.

**Group-key escaping.** When rendering per-group entries that contain commas in CSV outputs, the plugin double-quotes the group key per RFC 4180.

**Determinism.** Metric values, rule findings, and citations are deterministic for a given input. The only non-deterministic field is `timestamp`.

## Limitations

**The skill does not perform model inference.** Per-group counts must be computed by the caller against the evaluation dataset. The skill consumes counts; it does not invoke models or score samples.

**Protected-group definition is organizational.** The skill records the protected attributes the caller supplies. Selecting which attributes constitute protected classes for a given jurisdiction (and how to operationally measure them in the dataset) is a legal-and-policy determination that requires counsel and a privacy-preserving collection methodology.

**Threshold setting is organizational policy.** The four-fifths threshold is statutory under NYC LL144. All other thresholds (organizational maximum acceptable demographic parity difference, equalized odds tolerance, etc.) are organizational policy decisions. The skill applies thresholds when supplied; it does not invent them.

**Ground-truth availability constrains the metric set.** Metrics that require true-positive, false-positive, or PPV counts (equalized odds, predictive parity) are computable only when the caller supplies labeled outcome data. The skill emits an explicit `requires-ground-truth` status rather than substituting a non-ground-truth proxy.

**The skill does not assign aggregate bias scores.** Cross-metric aggregation requires human judgment about which fairness criterion applies to the use-case harm profile. The skill emits per-metric results; aggregate verdicts are a downstream interpretive activity.

**Jurisdictional applicability is a human determination.** The skill applies the rule when the caller declares it in scope. Determining whether a system is in scope under each statute (NYC LL144 AEDT definition, Colorado high-risk AI definition, EU AI Act high-risk list) requires counsel.

**Singapore MAS Veritas is recommended methodology, not statute.** The MAS FEAT Principles (2018) and the Veritas methodology (2022) are voluntary industry guidance for the Singapore financial-services sector. The skill applies the methodology when requested; it does not impose it as a binding obligation outside that sector.

**Causal attribution is out of scope.** The skill measures outcomes at the protected-group level. Attributing a measured disparity to specific model components (training data composition, feature selection, threshold calibration, deployment environment) requires post-hoc analysis the skill does not perform.
