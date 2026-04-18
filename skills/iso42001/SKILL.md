---
name: iso42001
version: 0.2.0
description: >
  ISO/IEC 42001:2023 AI Management System governance skill.
  Operationalizes the main-body clause structure (Sections 4 to 10) and
  all 38 Annex A controls into agent workflows that produce audit-ready
  artifacts: Statement of Applicability, AI System Impact Assessment,
  risk register, role and responsibility matrix, documented-information
  control records, nonconformity records, and management review input
  packages. Validated by Lead Implementer on 2026-04-18.
frameworks:
  - ISO/IEC 42001:2023
tags:
  - ai-governance
  - iso42001
  - audit
  - certification
  - aims
  - statement-of-applicability
  - aisia
  - annex-a
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes ISO/IEC 42001:2023, the international standard for AI Management Systems (AIMS). It turns the standard's requirements into agent-runnable workflows that produce audit-ready artifacts.

The skill is framework-agnostic in the sense that it can be loaded by any agent runtime that reads SKILL.md (Hermes Agent, Claude Code, Codex CLI, Cursor, Jules). The runtime agent reads this skill as knowledge context and invokes the workflow or plugin that matches the user's governance task. The authoritative runtime for AIGovOps is [aigovclaw](https://github.com/ZOLAtheCodeX/aigovclaw).

The skill classifies every clause and control on one of three operationalizability axes, drawn from `operationalization-map.md` in this directory:

- **Automatable (A).** End-to-end automation is feasible. A plugin can produce compliant output from structured input without human intervention in the common case.
- **Hybrid (H).** Automation produces a draft or scaffold that a human must review, complete, or approve before the output becomes audit evidence.
- **Human judgment required (J).** The requirement is inherently judgment-bound. Automation assists information gathering at most. Automating past the assist boundary produces evidence an auditor will reject.

The seven Tier 1 operationalizations below are the primary output of this skill. They are ordered by operational leverage.

## Scope

**In scope.** ISO/IEC 42001:2023, the published international standard, including:

- Main-body Clauses 4 through 10 (the Harmonized Structure shared with ISO/IEC 27001 and ISO 9001).
- All 38 Annex A controls across categories A.2 through A.10.
- The artifact vocabulary defined in `operationalization-map.md`: AIMS-scope, AI-policy, role-matrix, risk-register-row, SoA-row, AISIA-section, audit-log-entry, training-record, KPI, review-minutes, nonconformity-record, objective-record, change-record.

**Out of scope.** This skill does not provide:

- Legal advice on jurisdiction-specific AI regulation (EU AI Act, state-level AI laws, sector regulation). Use the `eu-ai-act` skill or consult qualified counsel for those.
- Sector-specific regulatory interpretation (healthcare, financial services, employment).
- Audit conclusions. The skill produces artifacts a Lead Auditor evaluates. It does not replace the auditor.
- Certification issuance. Certification bodies issue certification decisions. This skill prepares the organization for that decision.
- Other AI management or risk standards. See the `nist-ai-rmf` skill for NIST AI RMF 1.0.

**Operating assumption.** The user organization has committed to implementing an AIMS conformant to ISO/IEC 42001:2023, whether for certification, customer assurance, or internal governance maturity. This skill presumes that commitment. It is not a persuasion tool for whether to adopt the standard.

## Framework Reference

**Authoritative source.** ISO/IEC 42001:2023, Information technology, Artificial intelligence, Management system, published by the International Organization for Standardization in December 2023. The standard is copyrighted; purchase via the ISO store or a national standards body.

**Structure.** The standard consists of:

- Sections 1 to 3: Scope, normative references, terms and definitions.
- Sections 4 to 10: Main-body requirements in the Harmonized Structure.
- Annex A (normative): 38 controls organized in nine categories (A.2 through A.10). Annex A provides reference controls; the Statement of Applicability (Clause 6.1.3) records which controls the organization has selected.
- Annex B (informative): Implementation guidance for Annex A controls.
- Annex C (informative): Potential AI-related organizational objectives and risk sources.
- Annex D (informative): Use of the AIMS across domains and sectors.

**Related standards and supporting documents.**

- ISO/IEC 23894:2023, AI risk management guidance. Supports Clause 6.1 implementation.
- ISO/IEC 22989:2022, AI concepts and terminology. Source for terminology used in the standard.
- ISO/IEC 38507:2022, Governance implications of the use of AI by organizations. Supports Clause 4 and Clause 5 implementation.
- ISO/IEC 5338:2023, AI system life cycle processes. Supports Annex A category A.6.

**Crosswalks.** Many ISO 42001 requirements have direct analogues in other frameworks. The `nist-ai-rmf` skill in this catalogue provides the ISO 42001 to NIST AI RMF 1.0 crosswalk. The `eu-ai-act` skill (when published) will provide the ISO 42001 to EU AI Act crosswalk.

**Validation status.** Every Annex A control ID cited in this skill body has been cross-referenced against the published ISO/IEC 42001:2023 text and validated by Zola Valashiya (ISO/IEC 42001 Lead Implementer) on 2026-04-18. Historical review record at [../../docs/lead-implementer-review.md](../../docs/lead-implementer-review.md).

## Operationalizable Controls

Seven Tier 1 operationalizations are detailed below. Tier 2 controls receive abbreviated guidance. Tier 3 controls are judgment-bound and receive prescriptive prose only.

### T1.1 Statement of Applicability (ISO/IEC 42001:2023, Clause 6.1.3)

Class: H. Artifact: `SoA-row` per Annex A control. Leverage: H. Consumer: `plugins/soa-generator` (Phase 3).

**Requirement summary.** Clause 6.1.3 requires the organization to determine controls necessary to implement the AI risk treatment options selected, prepare a Statement of Applicability that contains the necessary controls, provide justification for inclusions, explain whether the controls are implemented, and provide justification for exclusions of any Annex A controls. The SoA is the primary evidence of control selection reviewed at certification audit.

**Inputs.**

- `AI-system-inventory`: list of AI systems in AIMS scope, each with risk tier, intended use, and deployment context.
- `risk-register`: outputs of Clause 6.1.2 AI risk assessment, mapped to identified risks.
- `organizational-context`: outputs of Clause 4.1 and 4.2.
- `treatment-decisions`: selected treatment options per risk (reduce, retain, avoid, share).

**Process.**

1. Enumerate all 38 Annex A controls as candidate SoA rows.
2. For each control, evaluate applicability against the AI-system-inventory and risk-register:
   1. If one or more identified risks are treated by this control, mark as included with the treated risks as justification.
   2. If no identified risk is treated by this control and the AI-system-inventory does not surface the underlying concern, mark as excluded with justification grounded in the inventory and risk register.
   3. If the control is partially applicable (applies to some systems in scope, not others), mark as included with a scope note naming the systems.
3. For each included control, record implementation status: implemented, partially implemented, or planned. Partial and planned status must reference an implementation plan with a target date.
4. For each excluded control, record the exclusion justification. Exclusions grounded in "no AI systems of this type" must match the AI-system-inventory; exclusions grounded in "covered by other management systems" must name the system and reference its control.
5. Emit one `SoA-row` per Annex A control.

**Output artifact.** `SoA-row` records. Each row contains:

- `control_id`: Annex A control identifier in the format `A.X.Y` or `A.X.Y.Z`.
- `control_title`: Title as published in ISO/IEC 42001:2023, Annex A.
- `status`: one of `included-implemented`, `included-partial`, `included-planned`, `excluded`.
- `justification`: free text. Must reference at least one of: AI-system-inventory entry, risk-register row, Clause 4 context output, or another management system's control.
- `implementation_plan_ref`: required when status is `included-partial` or `included-planned`. Link or reference to the plan.
- `scope_note`: required when the control applies to a subset of systems. Names the systems in scope for this control.
- `last_reviewed`: ISO 8601 timestamp of the last SoA review.
- `reviewed_by`: named accountable party.

Rendering: JSON for ingestion into GRC tooling; Markdown table for human review and audit evidence package.

**Citation anchors.** Every `SoA-row` carries `ISO/IEC 42001:2023, Clause 6.1.3` in its metadata, plus the Annex A control citation in `control_id`. Clause 6.1.3 is the authority for SoA structure; Annex A is the authority for control text.

**Auditor acceptance criteria.**

- Every Annex A control is addressed in the SoA (no silent omissions).
- Every included control has implementation status recorded.
- Every excluded control has justification that references organizational or scope-level evidence, not generic "not applicable" text.
- Every partial or planned status has an implementation plan reference with a target date.
- The SoA is dated and signed by an accountable party at the authority level required by organizational policy.

**Human-review gate.** The SoA is a documented decision. The plugin produces a draft; a human with delegated authority approves it. The agent does not finalize the SoA autonomously.

### T1.2 AI System Impact Assessment (ISO/IEC 42001:2023, Clause 6.1.4 and Annex A, category A.5)

Class: H. Artifact: `AISIA-section` per assessment dimension. Leverage: H. Consumer: `plugins/aisia-runner` (Phase 3); runtime workflow [aigovclaw/workflows/aisia-runner.md](https://github.com/ZOLAtheCodeX/aigovclaw/blob/main/workflows/aisia-runner.md).

**Requirement summary.** Clause 6.1.4 requires the organization to assess the potential impacts of AI systems on individuals, groups of individuals, and societies. Annex A category A.5 elaborates the process and documentation requirements. The AISIA is required for any AI system in AIMS scope and must be reviewed when significant changes occur.

**Inputs.**

- `system-description`: AI system name, purpose, intended use, decision context, deployment environment, data categories processed, decision authority (decision support, automation, operation without human review), reversibility of outputs.
- `affected-stakeholders`: identified individuals, groups, communities, or societal segments affected by the system's outputs.
- `existing-controls`: controls already in place that mitigate potential impacts.
- `risk-scoring-rubric`: organizational scale for severity and likelihood.

**Process.**

1. Validate inputs against the schema. Reject with a clear error if any required input is missing.
2. For each affected stakeholder group, identify potential impacts across the dimensions required by Clause 6.1.4 and A.5.4 and A.5.5. At minimum, address:
   1. Impact on fundamental rights and freedoms of individuals.
   2. Impact on groups of individuals (disparate or discriminatory impact).
   3. Societal impact (information ecosystem, economic, environmental, democratic).
   4. Physical safety impact where the AI system can cause physical harm directly or indirectly.
3. Classify each identified impact by severity and likelihood using the supplied rubric.
4. For each impact, identify existing controls (organizational, technical, or procedural) that mitigate it. Link to the `SoA-row` where applicable.
5. Compute residual impact after existing controls.
6. Recommend additional controls where residual impact exceeds the organization's tolerance. Additional controls surface as candidate `risk-register-row` inputs to the next Clause 6.1.2 cycle.
7. Produce a summary statement an auditor can use to determine whether the impact assessment satisfies Clause 6.1.4 and A.5.

**Output artifact.** `AISIA-section` records, one per impact dimension per affected stakeholder group, aggregated into a complete AISIA document. Each record contains:

- `system_ref`: AI system identifier.
- `stakeholder_group`: identified affected group.
- `impact_dimension`: one of `fundamental-rights`, `group-fairness`, `societal`, `physical-safety`, or an organizationally-defined dimension.
- `impact_description`: free text characterizing the potential impact.
- `severity`, `likelihood`: values from the supplied rubric.
- `existing_controls`: list of control references (organizational policy, SoA row, or technical control).
- `residual_severity`, `residual_likelihood`: post-control scores.
- `additional_controls_recommended`: list. May be empty.
- `assessor`, `assessment_date`: named human assessor and ISO 8601 date.

Rendering: Markdown for human review and submission; JSON for programmatic consumption.

**Citation anchors.** Document header carries `ISO/IEC 42001:2023, Clause 6.1.4`. Each record carries the relevant A.5 control citation (A.5.2 for process, A.5.3 for documentation, A.5.4 for individual and group impacts, A.5.5 for societal impacts).

**Auditor acceptance criteria.**

- Every stakeholder group identified in the input appears in the output.
- Every impact has a severity and a likelihood classification grounded in the supplied rubric.
- Every impact has at least one control reference (existing or recommended).
- The document header explicitly references Clause 6.1.4.
- The assessment is dated and assessor-attributed.
- Significant-change triggers are documented: the assessment records the system-version or scope state at assessment time.

**Human-review gate.** The AISIA is signed by the designated accountable party (typically the AI system owner or a delegated Data Protection Officer or AI Ethics Officer role per Clause 5.3). The plugin produces the draft; the accountable party signs it.

### T1.3 Documented information control (ISO/IEC 42001:2023, Clause 7.5)

Class: A. Artifact: `audit-log-entry` per document lifecycle event. Leverage: H. Consumer: `plugins/audit-log-generator`.

**Requirement summary.** Clause 7.5 requires that documented information required by the standard and by the organization be identified, formatted, reviewed, approved, controlled for access and distribution, retained, and disposed of according to a defined regime. Sub-clause 7.5.1 is general; 7.5.2 covers creating and updating; 7.5.3 covers control. Clause 7.5 is the AIMS-wide documentation backbone: every other clause's evidence flows through it.

**Inputs.**

- Document metadata: identifier, type, owner, classification, retention requirement.
- Lifecycle event: one of `created`, `updated`, `reviewed`, `approved`, `published`, `distributed`, `superseded`, `retained`, `disposed`.
- Actor identity.

**Process.**

1. On each lifecycle event, produce one `audit-log-entry` capturing the document identifier, event type, actor, timestamp, and pre- and post-event state where applicable (for example, version number before and after an update).
2. For approval events, record the approver's authority reference (role or delegation record) supporting the approval.
3. For distribution events, record the distribution list or access control rule.
4. For disposal events, record the retention policy reference and the disposal method.
5. Emit the entry to the audit log store. The store is the organizational system-of-record (a document management system, a ticketing system, or a dedicated audit log service).

**Output artifact.** `audit-log-entry` records. Fields:

- `doc_id`, `doc_type`, `doc_version`.
- `event`, `event_timestamp` (ISO 8601).
- `actor`, `actor_role`.
- `approver` and `approver_authority_ref` where applicable.
- `prior_state`, `new_state` for updates.
- `retention_policy_ref` for disposal events.
- `clause_mappings`: `["ISO/IEC 42001:2023, Clause 7.5.2"]` or `["ISO/IEC 42001:2023, Clause 7.5.3"]` depending on event type.

Rendering: JSON only. Human-readable rendering is produced on demand by a separate report generator.

**Citation anchors.** Every entry references Clause 7.5 and the applicable sub-clause in `clause_mappings`.

**Auditor acceptance criteria.**

- Every documented information event produces exactly one entry (no silent events, no duplicates).
- Every approval event has an approver authority reference.
- Every disposal event has a retention policy reference.
- Entries are immutable once emitted. Corrections are new entries referencing the prior entry.
- The audit log spans the full retention period required by organizational policy and applicable regulation.

**Human-review gate.** None for entry emission. Human review occurs at the approval event, which is itself one of the logged lifecycle events.

### T1.4 Management review input package (ISO/IEC 42001:2023, Clause 9.3.2)

Class: A. Artifact: `review-minutes` preamble. Leverage: H. Consumer: `plugins/management-review-packager` (Phase 3).

**Requirement summary.** Clause 9.3.2 requires management review inputs to include status of actions from previous reviews, changes in external and internal issues relevant to the AIMS, information on AIMS performance (including trends in nonconformities, monitoring results, audit results, fulfillment of AI objectives), feedback from interested parties, AI risks and opportunities, and opportunities for continual improvement. The input package is the pre-read distributed to top management before the review meeting.

**Inputs.**

- `previous-review-actions`: open items from the previous management review.
- `risk-register`: current state of the AI risk register.
- `nonconformity-log`: nonconformities raised since the last review and their corrective action status.
- `audit-results`: internal audit results since the last review.
- `kpi-report`: current values of Clause 9.1 KPIs against Clause 6.2 objectives.
- `change-log`: significant changes in context, scope, systems, or stakeholders since the last review.
- `stakeholder-feedback`: recorded feedback from interested parties.

**Process.**

1. Pull each input from its source of record.
2. For each input, summarize by trend direction (improving, stable, degrading) and flag any item that breaches an organizational threshold.
3. Compose the input package document in the order required by Clause 9.3.2.
4. Attach the raw data referenced by each summary for auditor traceability.
5. Emit the `review-minutes` preamble: the meeting header, the agenda, and the full input package.

**Output artifact.** `review-minutes` preamble. Sections:

- Meeting metadata: scheduled date, attendees list, review period covered.
- Status of actions from previous reviews.
- Changes in external and internal issues (Clause 4.1).
- Information on AIMS performance (Clause 9.1 KPIs, Clause 9.2 audit results, Clause 10.2 nonconformity trends, Clause 6.2 objective fulfillment).
- Feedback from interested parties.
- AI risks and opportunities (Clause 6.1.2 current state).
- Opportunities for continual improvement (Clause 10.1).

Rendering: Markdown document for distribution; JSON manifest for archival.

**Citation anchors.** The document carries `ISO/IEC 42001:2023, Clause 9.3.2` in its header. Each section carries the secondary clause citation for the source material.

**Auditor acceptance criteria.**

- All seven Clause 9.3.2 input categories appear in the package.
- Every category is populated from a source-of-record, not a narrative summary without data.
- The package is dated and distributed to attendees before the review meeting; distribution is logged per Clause 7.5.3.

**Human-review gate.** The package is reviewed by the AIMS owner (typically the role responsible for AIMS operation under Clause 5.3) before distribution. The agent does not distribute autonomously.

### T1.5 Nonconformity and corrective action (ISO/IEC 42001:2023, Clause 10.2)

Class: A. Artifact: `nonconformity-record`. Leverage: H. Consumer: `plugins/nonconformity-tracker` (Phase 3).

**Requirement summary.** Clause 10.2 requires the organization to react to nonconformities (take action, deal with consequences), evaluate the need for action to eliminate the causes of the nonconformity, implement any action needed, review the effectiveness of any corrective action taken, and update risks and opportunities and the AIMS as necessary. Records of nonconformities and corrective actions must be retained per Clause 7.5.

**Inputs.**

- Nonconformity description: what occurred, where, when, how detected.
- Nonconformity source: which clause or control is the nonconformity against.
- Immediate actions taken.
- Root cause analysis (when performed).
- Corrective actions planned.

**Process.**

1. On nonconformity detection, create one `nonconformity-record` capturing description, source clause or control, detection method, detection date, and immediate actions.
2. Drive the record through the Clause 10.2 workflow states: `detected`, `investigated`, `root-cause-identified`, `corrective-action-planned`, `corrective-action-in-progress`, `corrective-action-complete`, `effectiveness-reviewed`, `closed`.
3. For each state transition, emit an `audit-log-entry` against Clause 7.5.2 and link to the `nonconformity-record`.
4. At `effectiveness-reviewed`, evaluate whether the corrective action eliminated the cause. If not, reopen at `investigated` with a nonconformity record reference.
5. At `closed`, update the risk register if the nonconformity surfaced a previously-unregistered risk, and update the AIMS as necessary.

**Output artifact.** `nonconformity-record`. Fields:

- `id`, `status` (workflow state).
- `detected_at`, `detected_by`, `detection_method`.
- `source_citation`: clause or Annex A control against which the nonconformity is raised, using the STYLE.md citation format.
- `description`.
- `immediate_actions`, `immediate_actions_timestamp`.
- `root_cause`, `root_cause_analysis_date`.
- `corrective_actions`: list of planned actions with owner, target date.
- `effectiveness_review_date`, `effectiveness_outcome`, `effectiveness_reviewer`.
- `risk_register_updates`: list of risk-register rows created or modified as a result.
- `closed_at`, `closed_by`.

Rendering: JSON for the tracker; Markdown rendering on demand.

**Citation anchors.** Every record carries `ISO/IEC 42001:2023, Clause 10.2` in its metadata. Each state transition is logged against Clause 7.5.2.

**Auditor acceptance criteria.**

- Every nonconformity has a source citation (no generic nonconformities against "the AIMS").
- Every closed record has an effectiveness review and reviewer attributed.
- Every closed record shows whether risk register updates occurred.
- State transitions are timestamped and attributed.
- The record is retained for the retention period required by organizational policy.

**Human-review gate.** Root cause identification and effectiveness review both require human judgment. The plugin tracks state and produces templates; the analysis content is human.

### T1.6 Role and responsibility matrix (ISO/IEC 42001:2023, Clause 5.3; Annex A, control A.3.2)

Class: H. Artifact: `role-matrix`. Leverage: H. Consumer: `plugins/role-matrix-generator` (Phase 3).

**Requirement summary.** Clause 5.3 requires top management to ensure that the responsibilities and authorities for relevant roles are assigned, communicated, and understood within the organization. Annex A control A.3.2 specifies AI-specific roles and their responsibilities. The role matrix is a referenced input to Clauses 5.3, 6.1.3 (SoA approver authority), 6.1.4 (AISIA assessor), 7.2 (competence), 7.3 (awareness), 9.3 (management review attendees), and several Annex A controls.

**Inputs.**

- `org-chart`: organizational roles and reporting lines.
- `ai-system-inventory`: AI systems in AIMS scope.
- `decision-taxonomy`: categories of AI governance decisions (policy approval, risk acceptance, control implementation, incident response, audit programme approval, external reporting).
- `regulatory-overlay` (optional): roles required by applicable regulation (EU AI Act Article 26 obligations, DPO under GDPR, and similar).

**Process.**

1. Enumerate AI governance decision categories from the decision-taxonomy.
2. For each decision category, enumerate the typical AIMS activities: propose, review, approve, consulted, informed.
3. Map each activity to an organizational role from the org-chart. Roles may be existing (CIO, CISO, DPO) or AI-specific (AI Governance Officer, AI Risk Owner, AI System Owner) per A.3.2.
4. For each role, record the authority basis: organizational policy reference, job description reference, or delegation record.
5. Emit the `role-matrix` with one row per (decision category, activity) pair.

**Output artifact.** `role-matrix`. Fields:

- `decision_category`.
- `activity` (one of `propose`, `review`, `approve`, `consulted`, `informed`).
- `role_name`.
- `authority_basis`: reference to organizational policy, job description, or delegation record.
- `backup_role_name`: backup for continuity.
- `last_reviewed`, `reviewed_by`.

Rendering: Markdown table for human review; CSV for spreadsheet ingestion; JSON for programmatic consumption.

**Citation anchors.** The matrix header carries `ISO/IEC 42001:2023, Clause 5.3` and `ISO/IEC 42001:2023, Annex A, Control A.3.2`. Individual rows carry the clause or control they enable (for example, the SoA-approval row cites Clause 6.1.3).

**Auditor acceptance criteria.**

- Every decision category has exactly one approver role.
- Every role has an authority basis reference.
- The matrix is dated and reviewed on a schedule (annual at minimum, or on significant org change).
- Backup roles are defined for every role with approval authority (continuity requirement).

**Human-review gate.** Role assignment is approved at the authority level specified by organizational policy (typically top management per Clause 5.3). The plugin produces a draft from the inputs; approval is human.

### T1.7 AI risk register (ISO/IEC 42001:2023, Clause 6.1.2 and Clause 8.2)

Class: H. Artifact: `risk-register-row`. Leverage: H. Consumer: `plugins/risk-register-builder` (Phase 3).

**Requirement summary.** Clause 6.1.2 requires the organization to establish and implement an AI risk assessment process that produces consistent, valid, and comparable results. Clause 8.2 requires the process to be executed at planned intervals or when significant changes occur, with results retained as documented information. ISO/IEC 23894:2023 provides supplementary guidance. The risk register is the structured output of the process.

**Inputs.**

- `ai-system-inventory`: AI systems in scope.
- `risk-taxonomy`: organizational or skill-provided taxonomy of AI risk categories (bias, robustness, privacy, security, accountability, transparency, environmental, economic). The default taxonomy is provided by this skill; organizations may extend.
- `risk-scoring-rubric`: likelihood and impact scales.
- `stakeholder-consultation-notes`: inputs from affected stakeholders (often sourced from AISIA stakeholder analysis).
- `prior-incident-log`: past AI-related incidents (if any) to ground likelihood estimates.
- `threat-landscape-feed` (optional): external inputs on emerging AI threats.

**Process.**

1. For each AI system in the inventory, iterate the risk taxonomy. For each (system, category) pair, apply structured prompts to identify candidate risks. Record the source (taxonomy category) for each risk.
2. For each candidate risk, score likelihood and impact using the supplied rubric. Record the scoring rationale referencing at least one of: AISIA output, prior incident, stakeholder input, threat feed.
3. For each risk, identify the risk owner from the `role-matrix`.
4. Identify existing controls that mitigate the risk. Link each control reference to the corresponding `SoA-row` when the control is from Annex A.
5. Compute residual risk after existing controls.
6. Classify treatment option (reduce, retain, avoid, share) per Clause 6.1.3.
7. Emit one `risk-register-row` per risk.

**Output artifact.** `risk-register-row`. Fields:

- `id`, `system_ref`.
- `category` (from taxonomy).
- `description`.
- `likelihood`, `impact`, `inherent_score`.
- `scoring_rationale`: references to AISIA, incident log, stakeholder input, or threat feed.
- `existing_controls`: list of control references, each with SoA-row link where applicable.
- `residual_likelihood`, `residual_impact`, `residual_score`.
- `treatment_option` (one of `reduce`, `retain`, `avoid`, `share`).
- `owner_role`: from role matrix.
- `planned_treatment_actions`: list.
- `last_reviewed`, `reviewed_by`.

Rendering: CSV for spreadsheet ingestion; Markdown table for human review; JSON for programmatic consumption.

**Citation anchors.** Each row carries `ISO/IEC 42001:2023, Clause 6.1.2` in metadata. Planned treatment actions reference Clause 6.1.3. Operational re-assessment triggers reference Clause 8.2. Linked SoA rows reference the Annex A control.

**Auditor acceptance criteria.**

- Every risk has at least one control mapping with a valid citation.
- Every risk has an assigned owner from the role matrix.
- Every risk has inherent and residual scores.
- Scoring uses the supplied rubric consistently (no free-text scores).
- Re-assessment trigger is defined at the register level or per row: schedule-based, event-based, or both.
- The register is dated and attributed.

**Human-review gate.** Likelihood and impact scoring remains human-in-the-loop. The plugin may suggest scores based on similar rows, prior incidents, or taxonomy defaults, but the final score is set by the risk owner or a risk-scoring authority.

### Tier 2

Tier 2 operationalizations are valuable but lower-frequency or smaller-artifact than Tier 1. Abbreviated guidance below; full plugin treatment planned for Phase 3.

1. **AI policy review scheduling** (Annex A, control A.2.4). `audit-log-entry` per review event. Rule-based scheduler against a policy register.
2. **AI objectives** (Clause 6.2). `objective-record` linking Clause 5.2 policy to Clause 9.1 measurement. Draft generator from policy and context.
3. **Change control** (Clause 6.3). `change-record` per significant AIMS change. Template-driven.
4. **Competence and awareness** (Clauses 7.2, 7.3). `training-record` from role-matrix plus skills inventory. Integration target: existing Learning Management System.
5. **KPI reporting** (Clause 9.1). `KPI` aggregates against Clause 6.2 objectives. Definition is hybrid; reporting is automatable.
6. **Internal audit programme** (Clauses 9.2.1, 9.2.2). Programme doc plus `audit-log-entry` per engagement. Programme plan and scheduling automate; fieldwork is human.
7. **AI system operational monitoring and logs** (Annex A, controls A.6.2.6, A.6.2.8). `KPI` and `audit-log-entry`. Strong overlap with MLOps tooling; integration target: existing ML monitoring stack.
8. **Data provenance** (Annex A, control A.7.5). `audit-log-entry` per data lifecycle event. Integration target: existing data-lineage tooling.
9. **External reporting** (Annex A, control A.8.3). `audit-log-entry`. Template-driven per regulatory or contractual reporting obligation.

### Tier 3

Tier 3 controls are judgment-bound. This skill states what the organization must do, cites the clause, and surfaces that the determination requires human judgment. Plugin attempts to automate past the assist boundary produce outputs an auditor will reject.

- **Clause 4.1: context of the organization.** The organization determines external and internal issues relevant to its AIMS. Automation gathers candidate issues; selection is human.
- **Clause 5.1: leadership and commitment.** Top management demonstrates leadership through resourcing, review attendance, and policy approval. Evidence lives in management review minutes and resourcing decisions.
- **Clause 7.1: resources.** Resourcing decisions are judgment-bound. Evidence in management review.
- **Clause 9.3.1: management review general.** The meeting itself is human. Inputs (9.3.2) and results (9.3.3) are automation-assisted; the meeting is not.
- **Clause 10.1: continual improvement.** Umbrella clause. Evidence lives across 9.1, 9.2, 9.3, and 10.2 outputs.
- **Annex A, control A.6.1.2: objectives for responsible development.** Objectives are set by the organization. Drafts may be produced; approval is human.
- **Annex A, control A.9.3: objectives for responsible use.** Same posture as A.6.1.2.

## Output Standards

All outputs produced by this skill, by any plugin consuming this skill, or by any workflow in the aigovclaw runtime grounded in this skill, conform to the following standards. Outputs that do not conform are drafts, not evidence.

**Citation format.** Every output that references a clause or control uses the canonical citation format from [STYLE.md](../../STYLE.md):

- Clauses: `ISO/IEC 42001:2023, Clause X.X.X`. The first reference in any document uses the full standard identifier; subsequent references in the same document may use `ISO 42001, Clause X.X.X`.
- Annex A controls: `ISO/IEC 42001:2023, Annex A, Control A.X.Y` on first reference; `ISO 42001, A.X.Y` thereafter within the same document.

**Dual rendering.** Every artifact is produced in two forms:

- JSON for programmatic consumption, ingestion into GRC tooling, and archival.
- Markdown for human review, inclusion in audit evidence packages, and distribution to stakeholders.

**Timestamping.** Every artifact carries an ISO 8601 timestamp at the document or record level. Timestamps use UTC unless organizational policy requires local time with offset.

**Attribution.** Every approval, review, and sign-off event names the human actor and their role. Agent-produced drafts carry an agent signature field identifying the agent and version; this is not sufficient for approval and must be signed by a human with appropriate authority.

**Evidence linkage.** Every artifact that references another artifact (SoA-row citing a risk-register-row, nonconformity-record citing a clause, AISIA-section citing an existing control) uses stable identifiers, not text names. Identifier resolution must survive document regeneration.

**Version control.** Every artifact has a version and a change history per Clause 7.5.2. The history lives in the audit log. Corrections are new versions referencing the prior version; they are not in-place edits.

**Retention.** Retention periods are set by organizational policy against applicable regulation. This skill does not impose a retention period. The skill's outputs must be storable and retrievable for the organization's declared period.

**Prohibited content.** Per [STYLE.md](../../STYLE.md), outputs contain no em-dashes (U+2014), no emojis, and no hedging language. A certification-grade output is definite. If a determination requires human judgment, the output states `Requires human determination.` or `Auditor judgment required.` rather than hedging.

## Limitations

**This skill does not produce certification.** Certification is a decision of an accredited certification body following an audit. This skill produces the artifacts an auditor evaluates.

**This skill does not replace a Lead Implementer or Lead Auditor.** The skill operationalizes the structured, repeatable, evidence-producing work. Judgment-bound work (Tier 3 above) remains human. Framework interpretation, scope negotiation with stakeholders, defense of exclusions to an auditor, and strategic AIMS decisions require qualified human practitioners.

**This skill does not provide legal advice.** ISO 42001 intersects with AI regulation in many jurisdictions. Regulatory questions, jurisdictional interpretation, and defense against regulatory enforcement require qualified legal counsel.

**This skill depends on organizational inputs it does not produce.** The AI system inventory, risk scoring rubric, owner registry, organizational policies, stakeholder consultation notes, and prior incident log are organizational inputs. A skill output cannot be more accurate than its inputs. Missing or stale inputs produce weak outputs; the skill does not fabricate inputs.

**Framework revision tracking.** This skill targets ISO/IEC 42001:2023 as published. The framework-monitor workflow surfaces detected changes (errata, amendments, successor standards). Skill updates follow the change-update protocol in [AGENTS.md](../../AGENTS.md).

**This skill targets ISO/IEC 42001:2023 as published.** Future amendments, errata, or successor standards may change requirements. The `framework-monitor` workflow in this repository surfaces changes when detected; skill updates follow.

**Cross-framework interaction is out of scope for this skill.** Organizations subject to EU AI Act, GDPR, sectoral AI regulation, or NIST AI RMF alignment have additional obligations. The `eu-ai-act` and `nist-ai-rmf` skills in this catalogue address those; this skill does not.

**Partial operationalization is honest.** Approximately 60% of the standard is hybrid, 15% is fully automatable, and 25% requires human judgment. Claims of "full ISO 42001 automation" are either dishonest or imply that judgment-bound evidence is being fabricated. This skill refuses that posture.
