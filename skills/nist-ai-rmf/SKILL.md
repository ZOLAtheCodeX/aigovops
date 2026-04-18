---
name: nist-ai-rmf
version: 0.2.0-draft
description: >
  NIST AI Risk Management Framework 1.0 governance skill.
  Operationalizes all four functions (GOVERN, MAP, MEASURE, MANAGE) and
  their approximately 72 subcategories. Cross-references the iso42001 skill
  for shared operationalizations (AISIA, risk register, role matrix,
  nonconformity) so that a single plugin serves both frameworks where
  requirements align. Owns NIST-distinctive content in the MEASURE
  function (technical performance, privacy, fairness, robustness, safety
  metric families) and the Generative AI Profile (NIST AI 600-1) overlay.
  Draft pending Lead Implementer review.
frameworks:
  - NIST AI RMF 1.0
  - NIST AI 600-1 (Generative AI Profile)
tags:
  - ai-governance
  - nist
  - ai-rmf
  - risk-management
  - trustworthy-ai
  - genai
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the NIST AI Risk Management Framework 1.0, a voluntary framework published by the National Institute of Standards and Technology in January 2023. The skill turns the framework's four functions (GOVERN, MAP, MEASURE, MANAGE) and their subcategories into agent-runnable workflows that produce risk-aware artifacts and trustworthy-AI measurement outputs.

The skill is companion to the [iso42001](../iso42001/SKILL.md) skill in this catalogue. Six of the seven NIST Tier 1 operationalizations share a plugin with an ISO 42001 Tier 1 item, and the shared plugin produces outputs usable under either framework with rendering differences only. This skill documents NIST-specific guidance and cross-references the iso42001 skill for shared operationalizations rather than duplicating content. NIST-distinctive content (especially the MEASURE 2 metric families and the Generative AI Profile overlay) is covered in full here.

The A/H/J operationalizability classification, artifact vocabulary, and leverage ranking are identical to the iso42001 skill. See `operationalization-map.md` in this directory for the per-subcategory classification.

## Scope

**In scope.** NIST AI RMF 1.0 as published, including:

- All four functions: GOVERN, MAP, MEASURE, MANAGE.
- Approximately 72 subcategories across 19 categories.
- The AI RMF Playbook as the primary source for per-subcategory implementation suggestions beyond this skill's guidance.
- The Generative AI Profile (NIST AI 600-1, published July 2024) as an applicability overlay on the MEASURE and MAP functions.
- Crosswalk mappings to ISO/IEC 42001:2023 (where direct operationalization overlap exists).

**Out of scope.** This skill does not provide:

- Legal advice on US federal or state AI regulation. NIST frameworks are voluntary; specific regulatory obligations (CFPB, EEOC, FTC, state consumer protection, sector regulation) require qualified counsel.
- EU AI Act compliance. See the `eu-ai-act` skill when published.
- ISO 42001 certification preparation. See the [iso42001](../iso42001/SKILL.md) skill.
- Sector-specific NIST guidance (for example NIST Special Publication 800 series on information security). This skill covers the AI RMF only.
- TEVV (test, evaluation, verification, validation) methodology detail. MAP 2.3 and MEASURE 2 reference TEVV; implementation lives in MLOps tooling this skill integrates with rather than replaces.

**Operating assumption.** The user organization has adopted the NIST AI RMF as a voluntary risk-management framework for its AI systems, either standalone or alongside ISO 42001. Dual-adoption is common and this skill's cross-references assume it.

## Framework Reference

**Authoritative source.** NIST AI Risk Management Framework 1.0 (AI RMF 1.0), published January 2023 by the National Institute of Standards and Technology. Freely available at https://www.nist.gov/itl/ai-risk-management-framework.

**Structure.** The framework consists of:

- Part 1: Foundational information including context, audience, AI lifecycle, AI actor roles, and trustworthy AI characteristics.
- Part 2: Core functions (GOVERN, MAP, MEASURE, MANAGE) with categories and subcategories. This is the actionable content.
- Appendices and supporting materials.

**Core structure.**

- GOVERN cultivates an organizational culture of AI risk management. Approximately 19 subcategories across six categories.
- MAP establishes the context to frame risks related to an AI system. Approximately 20 subcategories across five categories.
- MEASURE analyzes, assesses, benchmarks, and monitors AI risk and related impacts. Approximately 21 subcategories across four categories. The highest-automation function.
- MANAGE allocates risk resources to mapped and measured risks. Approximately 12 subcategories across four categories.

**Related NIST documents.**

- NIST AI 600-1, Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile. Applied as an overlay on the MEASURE and MAP functions when the organization operates generative AI systems.
- NIST AI RMF Playbook (https://airc.nist.gov/AI_RMF_Knowledge_Base/Playbook). Per-subcategory implementation suggestions that complement this skill's operationalization guidance.
- NIST SP 1270, Towards a Standard for Identifying and Managing Bias in Artificial Intelligence. Supports MEASURE 2.10 fairness measurement.
- NIST Trustworthy and Responsible AI Resource Center (https://airc.nist.gov).

**Crosswalks.** This skill's `operationalization-map.md` provides an inline crosswalk to ISO/IEC 42001:2023 in the Notes column of every subcategory row. Key alignments:

- GOVERN function aligns with ISO 42001 Clauses 4, 5, 6.1 (policy and governance portions), and 7.1 through 7.3.
- MAP function aligns with ISO 42001 Clause 4 (context), Clause 6.1.4 (AISIA), and Annex A category A.5.
- MEASURE function aligns with ISO 42001 Clause 9 (performance evaluation). MEASURE is substantially more developed on technical metrics than Clause 9.
- MANAGE function aligns with ISO 42001 Clauses 6.1.3 (risk treatment), 8.3 (operational treatment), and 10.2 (nonconformity and corrective action).

**Verification note.** Subcategory IDs in this skill body carry a `[verify]` marker where sub-numbering needs confirmation against the published AI RMF 1.0 Core document. Function and category structure is stable and not flagged. The `operationalization-map.md` in this directory lists all `[verify]` items for Lead Implementer review.

## Operationalizable Controls

Seven Tier 1 operationalizations are detailed below. Six of the seven share a plugin with an iso42001 Tier 1 item and cross-reference the iso42001 skill rather than duplicating content. One Tier 1 item (T1.2 Technical performance and safety measurement) is NIST-distinctive and receives full treatment. Tier 2 and Tier 3 follow the iso42001 skill pattern.

### T1.1 AI System Impact Assessment (MAP 1.1, MAP 3.1, MAP 3.2, MAP 5.1)

Class: H. Artifact: `AISIA-section`. Leverage: H. Consumer: `plugins/aisia-runner` (Phase 3); runtime workflow [aigovclaw/workflows/aisia-runner.md](https://github.com/ZOLAtheCodeX/aigovclaw/blob/main/workflows/aisia-runner.md).

**Cross-reference.** Shared operationalization with [iso42001 T1.2](../iso42001/SKILL.md). The AISIA plugin and artifact schema are defined in the iso42001 SKILL.md. NIST-specific differences:

- Input vocabulary uses NIST trustworthy-AI characteristics (valid and reliable; safe, secure, and resilient; explainable and interpretable; privacy-enhanced; fair with harmful bias managed; accountable and transparent) instead of the ISO 42001 Clause 6.1.4 dimensions.
- Output rendering includes subcategory citations for MAP 1.1 (intended purpose), MAP 3.1 (benefits), MAP 3.2 (costs including non-monetary), and MAP 5.1 (likelihood and magnitude per impact). Each citation uses the `<FUNCTION> <Subcategory>` format defined in [STYLE.md](../../STYLE.md).
- Both sets of citations appear when the organization operates under both frameworks. A dual-rendering mode produces NIST-only, ISO-only, or dual-citation AISIA sections per organizational preference.

**Auditor acceptance criteria (NIST-specific additions to the iso42001 set).**

- Every identified impact is mapped to at least one NIST trustworthy-AI characteristic.
- Benefits (MAP 3.1) are documented with the same rigor as costs (MAP 3.2). The NIST framing requires both sides; ISO 42001 A.5 focuses on impacts.

### T1.2 Technical performance and safety measurement (MEASURE 2.1, 2.3, 2.5, 2.6, 2.7)

Class: A. Artifact: `KPI`, `audit-log-entry`, and V&V records. Leverage: H. Consumer: `plugins/metrics-collector` (Phase 3 candidate, name reserved).

This is the NIST-distinctive Tier 1 operationalization. ISO 42001 Clause 9.1 requires monitoring and measurement but does not prescribe metric families; MEASURE 2 is substantially more developed and operates as the organization's trustworthy-AI measurement backbone.

**Requirement summary.** MEASURE 2 subcategories require AI systems to be evaluated for trustworthy characteristics at development time and at deployment, with methods and metrics documented (2.1), test sets documented (2.1), in-context performance measured (2.3), validity and reliability characterized (2.5), safety risks and incidents documented (2.6), and security and resilience evaluated (2.7). The evaluations produce continuous evidence that feeds MEASURE 3 (tracking), MANAGE 4.1 (post-deployment monitoring), and GOVERN 1.5 (ongoing monitoring).

**Inputs.**

- `ai-system-inventory`: AI systems in scope with model architecture, intended purpose, and deployment environment.
- `metric-catalog`: organizational or skill-provided catalog of metrics by trustworthy-AI characteristic. The default catalog is specified below.
- `test-sets`: evaluation datasets with provenance, sampling methodology, and applicable-population documentation.
- `deployment-telemetry`: monitoring signals from the production environment (latency, error rate, drift indicators, security events).
- `incident-log`: safety and security incidents reported since the last measurement cycle.

**Default metric catalog.**

- `validity-reliability`: held-out test set accuracy, precision, recall, F1, calibration (expected calibration error), coverage at operating threshold. Feeds MEASURE 2.5.
- `in-context-performance`: production inference accuracy on sampled labels, latency at load, throughput, error rate per failure mode. Feeds MEASURE 2.3.
- `safety`: refusal rate on harmful-use prompts, false positive and false negative rates on safety filters, incident count by severity, time-to-detect, time-to-mitigate. Feeds MEASURE 2.6 and cross-links to `nonconformity-record` when an incident is material.
- `security-resilience`: adversarial robustness (accuracy under defined attack families: prompt injection, data poisoning, evasion), rate of successful authentication bypass attempts, dependency CVE count at runtime, mean time to patch for AI-specific vulnerabilities. Feeds MEASURE 2.7.

**Process.**

1. Validate inputs. Reject if `ai-system-inventory` is missing or if any system lacks intended-purpose documentation.
2. For each system, look up the applicable metric families from the metric catalog. Generative AI systems receive the AI 600-1 overlay (see GenAI Profile section below).
3. Compute metrics over the supplied test sets (pre-deployment) and deployment telemetry (production). Produce one `KPI` record per metric per measurement window.
4. For safety metrics, emit one `audit-log-entry` per incident referenced in the incident-log, linked to the applicable `nonconformity-record` where one has been raised.
5. Emit a V&V record summarizing the measurement cycle, including which test sets were used, which metrics were computed, and which organizational thresholds were breached.
6. Where a metric breaches an organizational threshold, trigger a `risk-register-row` update via the T1.3 workflow and raise a `nonconformity-record` if the breach is material per Clause 10.2 equivalence.

**Output artifacts.**

- `KPI`: one record per metric per measurement window. Fields: `metric_id`, `system_ref`, `value`, `window_start`, `window_end`, `threshold_breached` (bool), `measurement_method_ref`, `test_set_ref`. Referenced by dashboards and the Clause 9.3.2 management review input package.
- `audit-log-entry`: per-incident and per-threshold-breach records. Linked to the source `KPI` record.
- V&V record: per measurement-cycle summary. Includes the subcategory citations for every metric computed.

Rendering: JSON for programmatic consumption and time-series ingestion; Markdown summary tables for review packages.

**Citation anchors.** Each `KPI` record carries the applicable MEASURE 2 subcategory citation: `MEASURE 2.1` for the method-and-test-set metadata, `MEASURE 2.3` for in-context metrics, `MEASURE 2.5` for validity metrics, `MEASURE 2.6` for safety metrics, `MEASURE 2.7` for security metrics. Multi-citation records are common and acceptable.

**Auditor acceptance criteria.**

- Every `KPI` record cites the specific MEASURE subcategory and the measurement methodology reference.
- Every test set has provenance documented at creation and immutability preserved at measurement.
- Every threshold breach produces either a risk register update, a nonconformity record, or a documented organizational decision to retain the risk. No silent breaches.
- Measurement methodology is periodically re-evaluated (MEASURE 1.2, MEASURE 4.1) with the review itself logged as an `audit-log-entry`.
- V&V records reference every metric computed and every subcategory satisfied.

**Human-review gate.** Metric selection (the metric catalog) is a hybrid-class decision: the plugin ships a default catalog; the organization approves it and extends it per context. Threshold setting is organizational policy, not a plugin output. Incidents that surface at measurement time are reviewed by the risk owner (role matrix) before a nonconformity is formally raised.

**GenAI Profile (NIST AI 600-1) overlay.** When the system is generative AI, this subcategory family adds the following metric families to the catalog:

- `confabulation`: hallucination rate measured against a fact-verification harness; source attribution accuracy on retrieval-augmented outputs.
- `data-regurgitation`: training-data memorization detection (exact-match and near-match rates against known training corpora).
- `abusive-content`: rate of policy-violating output on adversarial and safety-probe prompts; false-negative rate for known-harmful content categories.
- `information-integrity`: rate of synthetic-content labeling compliance where required by policy; provenance-signal attachment rate.
- `ip-risk`: rate of uncleared-content reproduction in outputs (style, lyrics, code, images).
- `value-chain-integrity`: foundation-model provenance tracking and pre-trained-model risk posture per MANAGE 3.2.

The GenAI overlay is applied automatically when `system_type: generative-ai` is set in the `ai-system-inventory` row for the system.

### T1.3 AI risk register (MAP 4.1, MANAGE 1.2, MANAGE 1.3)

Class: H. Artifact: `risk-register-row`. Leverage: H. Consumer: `plugins/risk-register-builder` (Phase 3).

**Cross-reference.** Shared operationalization with [iso42001 T1.7](../iso42001/SKILL.md). The risk register plugin and artifact schema are defined in the iso42001 SKILL.md. NIST-specific differences:

- Risk taxonomy defaults to NIST trustworthy-AI characteristics (valid-reliable, safe, secure-resilient, accountable-transparent, explainable-interpretable, privacy-enhanced, fair-bias-managed) in addition to or instead of the ISO 42001 default categories.
- Every row carries both the NIST subcategory citations (`MAP 4.1`, `MANAGE 1.2`, `MANAGE 1.3`, and others as applicable) and optionally the ISO 42001 citation (`Clause 6.1.2`, `Clause 6.1.3`) for dual-track organizations.
- MANAGE 1.4 (negative residual risks documented for affected AI actors) adds a transparency field to the row: `negative_residual_disclosure_ref` naming where the residual risk is communicated to affected individuals or groups per MANAGE 1.4. This field is not required under ISO 42001 and is populated only when the NIST framework is in scope.

### T1.4 Role and responsibility matrix (GOVERN 2.1)

Class: H. Artifact: `role-matrix`. Leverage: H. Consumer: `plugins/role-matrix-generator` (Phase 3).

**Cross-reference.** Shared operationalization with [iso42001 T1.6](../iso42001/SKILL.md). The role matrix plugin and artifact schema are defined in the iso42001 SKILL.md. NIST-specific differences:

- The decision taxonomy includes NIST-specific decision categories: AI RMF adoption scope, trustworthy-AI characteristic prioritization, metric catalog approval, generative-AI policy approval.
- Interdisciplinary AI actor representation (GOVERN 3.1 [verify] workforce diversity and MAP 1.2 interdisciplinary AI actors consulted) is tracked as a matrix property: each decision category carries an `interdisciplinary_coverage` flag with a reference to the composition evidence.
- The matrix cites both `ISO/IEC 42001:2023, Clause 5.3` and `GOVERN 2.1` when the organization operates under both frameworks.

### T1.5 Ongoing monitoring dashboard (GOVERN 1.5, MEASURE 3.1, MEASURE 4.1, MANAGE 4.1)

Class: A. Artifact: `KPI` and `audit-log-entry` aggregated into a dashboard. Leverage: H. Consumer: `plugins/monitoring-dashboard` (Phase 3 candidate).

**Requirement summary.** GOVERN 1.5, MEASURE 3.1, MEASURE 4.1, and MANAGE 4.1 together require continuous monitoring of AI risks, periodic measurement of measurement efficacy, and post-deployment monitoring of AI systems. These subcategories jointly demand a monitoring surface that aggregates inputs from multiple systems and multiple metric families over time.

**Inputs.**

- All `KPI` records produced by T1.2 (technical measurement).
- All `risk-register-row` records produced by T1.3 (risk state).
- All `audit-log-entry` records relevant to the monitoring window.
- Monitoring-plan configuration: which metrics and risk classes require dashboard surfacing and at what refresh cadence.

**Process.**

1. Aggregate `KPI` records into time-series views per system per metric family.
2. Aggregate `risk-register-row` state changes into a risk-posture view over time.
3. Cross-reference with `nonconformity-record` state transitions to surface which risks have active corrective actions.
4. Emit a dashboard snapshot at the configured cadence. Each snapshot is a `KPI`-like record but at the aggregate level, with its own subcategory citation (`MEASURE 3.1` or `MANAGE 4.1` as applicable).
5. At the MEASURE 4.1 meta-measurement cadence (typically quarterly), emit an evaluation of measurement efficacy: are the metrics detecting what they should, are thresholds calibrated, is there measurement drift. This emission is a V&V record referenced from management review (T1.6 below).

**Output artifact.** Dashboard snapshot records (structured subset of `KPI`) plus an optional rendered dashboard (HTML or static image) for human review. Rendering is a Phase 3 concern.

**Citation anchors.** Each dashboard snapshot cites `MEASURE 3.1`. Meta-measurement evaluations cite `MEASURE 4.1`. Dashboards framed for executive governance audiences additionally cite `GOVERN 1.5`. Post-deployment system-level views cite `MANAGE 4.1`.

**Auditor acceptance criteria.**

- The monitoring surface covers every AI system in scope and every metric family designated for surfacing.
- Cadence is defined and met (not best-effort).
- Meta-measurement cycles occur on schedule and produce evaluation records, not just summaries.
- Measurement drift is investigated when detected (trigger criteria documented at plan configuration time).

**Human-review gate.** The monitoring plan itself (which metrics, what cadence, which thresholds trigger which responses) is approved at the authority level specified by the role matrix. The plugin executes the plan; approval of plan changes is human.

### T1.6 Privacy and fairness metrics (MEASURE 2.9, MEASURE 2.10)

Class: A. Artifact: `KPI`. Leverage: H. Consumer: `plugins/metrics-collector` (same as T1.2).

These are NIST-distinctive Tier 1 items. ISO 42001 Annex A addresses privacy (overlap with A.7 data controls) and fairness (implicit in A.5 impact assessment) but does not prescribe metric families. MEASURE 2.9 and 2.10 do.

**Requirement summary.** MEASURE 2.9 [verify] requires privacy risk to be evaluated. MEASURE 2.10 [verify] requires fairness to be evaluated across demographic groups. Both subcategories expect measurement at development time and periodic re-measurement in production.

**Privacy metrics (MEASURE 2.9).**

- `training-data-exposure`: rate at which training data appears in model outputs under probing (verbatim and near-match).
- `membership-inference-risk`: accuracy at which membership in the training set can be inferred from model outputs, measured against a standard attack.
- `attribute-inference-risk`: accuracy at which sensitive attributes can be inferred from model outputs.
- `pii-in-outputs`: rate at which outputs contain personally identifiable information that was not in the prompt.

**Fairness metrics (MEASURE 2.10).**

- `demographic-parity-difference`: difference in positive-outcome rate across protected demographic groups.
- `equal-opportunity-difference`: difference in true-positive rate across protected demographic groups.
- `calibration-parity`: difference in calibration error across protected demographic groups.
- `representational-harm-rate`: rate of stereotype or demeaning output by protected group. Relevant for generative systems per AI 600-1.

**Process, outputs, and acceptance criteria:** Same as T1.2 technical measurement, with privacy and fairness metric families added to the metric catalog. The privacy and fairness metrics carry additional acceptance criteria:

- Protected-group definitions are documented with their legal or policy basis.
- Measurements occur on test sets with sufficient protected-group representation; the test set composition is documented per MEASURE 2.1.
- Disparity values that breach organizational tolerance are surfaced to the risk register and trigger the nonconformity workflow.

**Human-review gate.** Protected-group definitions and fairness thresholds are organizational policy decisions, not plugin outputs. Privacy threshold setting requires Data Protection Officer or equivalent authority from the role matrix.

### T1.7 Continual improvement integration (MANAGE 4.2)

Class: H. Artifact: `review-minutes`, `nonconformity-record`. Leverage: H. Consumer: `plugins/nonconformity-tracker` (same as iso42001 T1.5).

**Cross-reference.** Shared operationalization with [iso42001 T1.5](../iso42001/SKILL.md). The nonconformity tracker and corrective-action workflow are defined in the iso42001 SKILL.md. NIST-specific differences:

- MANAGE 4.2 frames the activity as measurable continual-improvement integration, not purely as corrective action. The tracker extends the iso42001 `nonconformity-record` workflow with an `improvement_outcome` field that captures the positive direction of change (reduced disparity, improved calibration, reduced incident rate) rather than just "cause eliminated".
- Management review inputs (T1.8 below) include a continual-improvement section citing `MANAGE 4.2`.

### Tier 2

Tier 2 operationalizations receive abbreviated guidance. Many share plugins with iso42001 Tier 2; cross-references note the alignment.

1. **Legal and regulatory register** (GOVERN 1.1). Integration target: existing legal-hold and compliance registers. Shared with iso42001 T2 policy-review scheduling.
2. **AI policy and mission documentation** (GOVERN 1.2, MAP 1.3). Shared with iso42001 Tier 1 policy drafting.
3. **Workforce training** (GOVERN 2.2, GOVERN 3.2). Shared with iso42001 Clauses 7.2 and 7.3.
4. **Incident response playbook** (GOVERN 4.3, MANAGE 2.3). Shared across NIST functions. Crosswalk to iso42001 Clause 10.2.
5. **Third-party and pre-trained model management** (GOVERN 6, MANAGE 3). Shared with iso42001 Annex A A.10. MANAGE 3.2 (foundation-model management) is NIST-distinctive and extends the supplier register with `pretrained_model_provenance` fields.
6. **System documentation** (MAP 2.1, 2.2, 2.3). Shared with iso42001 Annex A A.6.2.3 design and development documentation.
7. **Targeted application scope and operator proficiency** (MAP 3.3, 3.4). Scope documentation plus training.
8. **Metrics catalog** (MEASURE 1.1). Foundational for all T1.2 and T1.6 pipelines. The catalog itself is the artifact; the catalog feeds the metrics-collector plugin.

### Tier 3

Judgment-bound subcategories. This skill states what the organization must do, cites the subcategory, and surfaces that the determination requires human judgment.

- **GOVERN 1.4: risk tolerance.** Tolerance is an executive decision. Plugin produces drafts; approval is human.
- **GOVERN 2.3: executive accountability.** Evidence in management-review participation, not a plugin output.
- **GOVERN 3.1 [verify]: workforce diversity.** Composition decision. Plugin may surface gaps from the role matrix; composition selection is human.
- **GOVERN 4.1: culture of critical thinking.** No direct artifact. Evidence from training patterns, incident response, review minutes.
- **GOVERN 5.1: external stakeholder feedback process definition.** Process design is human; execution is automation-assisted.
- **MAP 1.5: risk tolerance application.** Tolerance is GOVERN 1.4's output; applied here in mapping. No new artifact.
- **MAP 5.2 [verify]: engagement cadence.** Cadence setting is human; execution is automation-assisted.
- **MEASURE 1.3 [verify]: expert selection for method and metric selection.** Composition decision.
- **MANAGE 1.1: go-or-no-go determination.** Purpose-fitness judgment per AI system. No plugin.

## Output Standards

All outputs produced by this skill conform to the canonical output standards defined in the [iso42001 skill Output Standards section](../iso42001/SKILL.md). The following NIST-specific additions apply.

**Citation format.** Per [STYLE.md](../../STYLE.md): `<FUNCTION> <Subcategory>`. Examples: `GOVERN 1.1`, `MAP 3.5`, `MEASURE 2.7`, `MANAGE 4.3`. On first reference in any document, write `NIST AI Risk Management Framework 1.0 (AI RMF 1.0)` followed by the subcategory citation; subsequent references in the same document use only the subcategory form.

**Dual-framework citations.** For organizations operating under both NIST AI RMF and ISO 42001, artifacts may carry both citation families. The canonical rendering puts the primary framework citation first (organization's choice) followed by the secondary. Example: `MEASURE 2.6; ISO/IEC 42001:2023, Clause 10.2`.

**GenAI Profile citations.** When the GenAI overlay is applied, the citation reads `<FUNCTION> <Subcategory> (AI 600-1 overlay)`. Example: `MEASURE 2.6 (AI 600-1 overlay)`. This is not a separate subcategory; it indicates the overlay modified the metric selection or threshold.

**Metric catalog versioning.** The `metric-catalog` artifact carries its own version. KPI records cite the catalog version in use at measurement time. Catalog changes are auditable events logged per ISO 42001 Clause 7.5.2 equivalence.

## Limitations

**This skill does not produce NIST certification.** NIST AI RMF is voluntary. There is no accredited certification program for AI RMF conformance as of the publication of this skill. The skill produces artifacts that demonstrate framework adoption to internal stakeholders, federal contracting officers (where AI RMF alignment is required), customers, and external auditors reviewing voluntary conformance.

**This skill does not replace human expertise.** NIST AI RMF is principle-based. Its application requires judgment about context, risk tolerance, and stakeholder values. This skill operationalizes the structured, repeatable, measurable work. Judgment-bound subcategories remain human.

**Metric catalogs are organizational choices.** The default metric catalog in this skill is a starting point grounded in published research and the AI RMF Playbook. Specific metric selection, threshold setting, and protected-group definitions are organizational decisions informed by legal, ethical, and domain context. A skill-default catalog is not a substitute for organizational policy.

**Subcategory IDs flagged `[verify]` require confirmation.** Operationalization guidance keyed to a `[verify]`-flagged subcategory must be confirmed against the published AI RMF 1.0 Core before the output is used as evidence. Function and category structure are stable.

**This skill targets AI RMF 1.0 as published.** NIST has signaled that the framework will be updated. AI 600-1 (Generative AI Profile) was added after the core framework; other profiles may follow. The `framework-monitor` workflow surfaces changes when detected; skill updates follow.

**GenAI Profile coverage is overlay, not exhaustive.** The AI 600-1 overlay in this skill covers the MEASURE-function impact of generative AI. Full GenAI governance may warrant a dedicated `nist-ai-genai-profile` skill in the future. The overlay is sufficient for non-specialist generative-AI deployments.

**Technical measurement depends on the MLOps stack.** MEASURE 2 metric computation requires production telemetry, test datasets, and a measurement pipeline. This skill describes what to measure and how to cite it; the measurement infrastructure itself is an organizational capability the skill integrates with rather than replaces.

**Cross-framework interaction is scoped to the iso42001 crosswalk.** Organizations subject to EU AI Act, GDPR, sectoral AI regulation, or other standards beyond NIST AI RMF and ISO 42001 have additional obligations not covered here. The `eu-ai-act` skill (when published) will address EU AI Act alignment; this skill does not.
