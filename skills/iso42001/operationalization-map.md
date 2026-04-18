# ISO/IEC 42001:2023 Operationalization Map

Working document for the `iso42001` skill. Maps every main-body clause and Annex A control to an operationalizability class, a candidate artifact type, and an operational-leverage ranking. This map is the intermediate deliverable between Phase 1 scaffolding and the Phase 2 `SKILL.md` body. It is not itself a SKILL.md and deliberately does not follow the required SKILL.md section headers.

**Validation status.** Validated by Zola Valashiya (ISO/IEC 42001 Lead Implementer) on 2026-04-18. All clause references and Annex A control IDs have been confirmed against the published ISO/IEC 42001:2023 text. Historical review record preserved at [../../docs/lead-implementer-review.md](../../docs/lead-implementer-review.md).

**Input to.** The priority-ranked backlog at the bottom of this document drives the order in which controls are operationalized in `SKILL.md`, in `evals/iso42001/test_cases.yaml`, and in Phase 3 plugin work.

## Methodology

For each clause and control, four dimensions are captured.

**Operationalizability class**: how much of the requirement can be implemented as an automated pipeline.

- **A (automatable):** end-to-end automation is feasible. A plugin can produce compliant output from structured input without human intervention in the common case. Example: an audit log entry that maps a governance event to applicable clauses.
- **H (hybrid):** automation produces a draft, scaffold, or computed candidate that a human must review, complete, or approve before it becomes audit evidence. Most of Clause 6 falls here. Example: an AISIA draft populated from a system description, but signed off by an accountable owner.
- **J (human judgment required):** the requirement is inherently judgment-bound; automation at most assists information gathering. Automating past the assist boundary here is an anti-pattern that produces evidence no auditor will accept. Example: Clause 5.1 leadership commitment.

**Artifact**: the concrete deliverable the operationalization produces. Constrained to the following set so that plugin outputs compose into a coherent evidence package.

- `AIMS-scope`: a written scope statement for the AI Management System.
- `AI-policy`: the organization's AI policy document (Clause 5.2 output).
- `role-matrix`: responsibility and authority mapping (Clause 5.3).
- `risk-register-row`: one row in the AI risk register.
- `SoA-row`: one row in the Statement of Applicability.
- `AISIA-section`: one section of an AI System Impact Assessment.
- `audit-log-entry`: one governance event record.
- `training-record`: competence or awareness evidence.
- `KPI`: a measured metric feeding Clause 9.1 monitoring.
- `review-minutes`: management review inputs and outputs (Clause 9.3).
- `nonconformity-record`: Clause 10.2 corrective action entry.
- `objective-record`: Clause 6.2 AI objective with plan and measurement.
- `change-record`: Clause 6.3 planned change control entry.

**Leverage**: operational value of automating this item, weighted by:

1. Frequency of evidence production (continuous > daily > weekly > per-change > quarterly > annual).
2. Tedium of manual production (evidence packages and citation-heavy outputs win over narrative paragraphs).
3. Error rate of manual production (citation mapping and cross-reference lookup win over pure text).

Scored as H / M / L with brief rationale.

**Open questions**: explicit uncertainty to resolve before the SKILL.md body is committed.

## Clauses 4 to 10

The main-body clauses follow the Harmonized Structure (HS) shared with ISO/IEC 27001 and ISO 9001. Operationalizability varies sharply: context-setting clauses (4 and 5) are largely judgment-bound, planning and operation clauses (6 and 8) are the densest hybrid territory, and documentation and evaluation clauses (7.5 and 9) hold the highest automation leverage.

### Clause 4: Context of the organization

| Sub-clause | Requirement summary | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| 4.1 Understanding the organization and its context | Determine external and internal issues relevant to the AI management system's purpose and strategic direction. | J | AIMS-scope | L | Automation can gather candidate issues from strategy documents and prior risk registers, but selection is judgment-bound. |
| 4.2 Understanding needs and expectations of interested parties | Identify interested parties relevant to the AIMS and their relevant requirements. | H | AIMS-scope | M | Automatable: inventory of interested parties from role-matrix and contracts. Human: which requirements apply. |
| 4.3 Determining the scope of the AIMS | Document the scope of the AIMS (boundaries, applicability, AI systems in scope). | H | AIMS-scope | M | A scope-statement generator can compose a draft from 4.1/4.2 outputs and a system inventory. Human signs off. |
| 4.4 AI management system | Establish, implement, maintain, and continually improve the AIMS. | J | (integrative) | L | Umbrella clause. No standalone artifact; satisfied by the presence of artifacts from 5-10. |

**Class split Clause 4:** J 2, H 2, A 0. Leverage weighted low: context-setting is human work.

### Clause 5: Leadership

| Sub-clause | Requirement summary | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| 5.1 Leadership and commitment | Top management demonstrates leadership and commitment to the AIMS. | J | review-minutes | L | Evidence lives in management review minutes and resourcing decisions. Automation assists information gathering for management review inputs only. |
| 5.2 AI policy | Establish an AI policy appropriate to the organization. | H | AI-policy | M | A policy-draft generator can produce a compliant skeleton from scope, values, and applicable frameworks. Human finalizes. Policy is updated infrequently (annual or per major change), so leverage is moderate not high. |
| 5.3 Roles, responsibilities, and authorities | Assign and communicate roles, responsibilities, and authorities for the AIMS. | H | role-matrix | H | RACI generation from an org chart, system inventory, and decision taxonomy is highly automatable. This is a high-leverage quick win. |

**Class split Clause 5:** J 1, H 2, A 0.

### Clause 6: Planning

Clause 6 is the analytic heart of the AIMS and concentrates the highest density of hybrid-automation opportunity. Sub-clauses 6.1.2, 6.1.3, and 6.1.4 are the controls the `aigovops` plugin layer primarily targets.

| Sub-clause | Requirement summary | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| 6.1.1 Planning: general | Determine risks and opportunities to the AIMS; plan actions to address them. | H | (integrative) | M | Umbrella for 6.1.2-6.1.4. Satisfied by outputs of those. |
| 6.1.2 AI risk assessment | Establish and implement an AI risk assessment process. | H | risk-register-row | H | Risk identification can be automated against a taxonomy (bias, robustness, privacy, security, accountability, transparency). Likelihood and impact scoring remains human-in-the-loop. Risk identification is a top-three Phase 3 plugin target. |
| 6.1.3 AI risk treatment | Select treatment options, determine controls, prepare SoA. | H | SoA-row | H | SoA generation from 6.1.2 outputs plus Annex A control applicability is strongly automatable. Exclusion justifications are hybrid. The SoA is the certification-audit centerpiece, so leverage is maximal. |
| 6.1.4 AI system impact assessment | Perform AISIAs on AI systems. | H | AISIA-section | H | AISIA is the flagship operationalization target. A system description input produces a structured draft covering individual, group, societal, and environmental impacts. Sign-off remains human. `aigovclaw/workflows/aisia-runner.md` is the corresponding workflow. |
| 6.2 AI objectives and planning | Establish measurable AI objectives and plans to achieve them. | H | objective-record | M | Objective generation from policy and context is automatable as a draft; target-setting is judgment. Measurement lives in 9.1. |
| 6.3 Planning of changes | Planned changes to the AIMS are carried out in a planned manner. | A | change-record | M | A change-record plugin can produce compliant entries from structured change descriptions. Change velocity determines leverage. |

**Class split Clause 6:** J 0, H 5, A 1. This is the densest operationalization territory in the standard.

### Clause 7: Support

Clause 7.5 (documented information) is the single highest-leverage area of the standard from an automation perspective. Every other clause produces documented information; Clause 7.5 defines the control over it.

| Sub-clause | Requirement summary | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| 7.1 Resources | Determine and provide resources needed for the AIMS. | J | review-minutes | L | Resourcing decisions are judgment-bound. Evidence in management review. |
| 7.2 Competence | Determine necessary competence; ensure persons are competent on the basis of education, training, or experience. | H | training-record | M | Competence matrices and training gap analysis are automatable from role-matrix plus skills inventory. Evidence collection (certifications, training completion) is automatable; curriculum design is human. |
| 7.3 Awareness | Ensure relevant persons are aware of the AI policy, their contribution, and implications of nonconformity. | A | training-record | M | Awareness program execution and evidence collection (attestation, completion tracking) is highly automatable. Content design is human (one-time or per-update). |
| 7.4 Communication | Determine internal and external communications relevant to the AIMS. | H | (plan) | L | Communications plans are artifact-light and low-frequency. Low leverage. |
| 7.5.1 Documented information: general | Documented information required by the standard and by the organization. | A | (integrative) | H | Documentation presence checking is automatable at the repository level. Every other control feeds here. |
| 7.5.2 Creating and updating | Identification, format, review, and approval of documented information. | A | audit-log-entry | H | Version control, approval workflow, and change history are fully automatable. This is pure process automation. |
| 7.5.3 Control of documented information | Access, distribution, retrieval, storage, change control, retention, disposal. | A | audit-log-entry | H | Same. Document management system integration. |

**Class split Clause 7:** J 1, H 2, A 4. Leverage concentrated in 7.5.

### Clause 8: Operation

Clause 8 runs the processes planned in Clause 6 and produces most of the operational evidence.

| Sub-clause | Requirement summary | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| 8.1 Operational planning and control | Plan, implement, and control the processes needed to meet requirements. | H | (integrative) | M | Process execution evidence is per-process. Umbrella for 8.2-8.4. |
| 8.2 AI risk assessment (operational) | Perform AI risk assessments at planned intervals or when significant changes occur. | A | risk-register-row | H | Triggers for risk reassessment are rule-based. Plugin runs 6.1.2 process on a schedule or trigger. |
| 8.3 AI risk treatment (operational) | Implement the AI risk treatment plan. | H | SoA-row, audit-log-entry | M | Treatment implementation is per-risk. Evidence is per-treatment. |
| 8.4 AI system impact assessment (operational) | Perform AISIAs and keep results documented. | A | AISIA-section | H | Same workflow as 6.1.4, run at the per-system and per-significant-change cadence. |

**Class split Clause 8:** J 0, H 2, A 2.

### Clause 9: Performance evaluation

Clause 9 is where measurement and audit infrastructure lives. High automation potential throughout.

| Sub-clause | Requirement summary | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| 9.1 Monitoring, measurement, analysis, and evaluation | Determine what needs to be monitored and measured; analyze and evaluate. | A | KPI | H | KPI definition from 6.2 objectives is hybrid; monitoring infrastructure and reporting are fully automatable. |
| 9.2.1 Internal audit: general | Conduct internal audits at planned intervals. | H | audit-log-entry | M | Audit execution is human; audit scheduling, scope, and evidence collection are automatable. |
| 9.2.2 Internal audit programme | Plan, establish, implement, and maintain an audit programme. | A | (plan) | M | Programme definition automates against a template. Execution tracking is fully automatable. |
| 9.3.1 Management review: general | Top management reviews the AIMS at planned intervals. | J | review-minutes | L | Meeting itself is human. Inputs and outputs are automatable. |
| 9.3.2 Management review inputs | Consider specified inputs (status of actions, changes, trends, performance, feedback, risks, improvement opportunities). | A | review-minutes | H | Input package compilation is pure automation: pulls from risk register, nonconformity log, audit results, KPI reports. High leverage because the package is tedious to assemble manually and required at every review. |
| 9.3.3 Management review results | Decisions and actions from review. | H | review-minutes, audit-log-entry | M | Minutes templating is automatable; decisions are human. |

**Class split Clause 9:** J 1, H 3, A 2.

### Clause 10: Improvement

| Sub-clause | Requirement summary | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| 10.1 Continual improvement | Continually improve the suitability, adequacy, and effectiveness of the AIMS. | J | (integrative) | L | Evidence lives across 9.1 KPIs, 9.2 audits, 9.3 reviews, and 10.2 corrective actions. No standalone artifact. |
| 10.2 Nonconformity and corrective action | React to nonconformities; evaluate the need for action; implement actions; review effectiveness. | A | nonconformity-record | H | Nonconformity logging, root-cause template, corrective-action tracking, and effectiveness review are fully automatable. High frequency = high leverage. |

**Class split Clause 10:** J 1, H 0, A 1.

## Annex A: the 38 controls

Annex A is organized into nine categories (A.2 through A.10). The category-level theme is stable; the specific control IDs below represent my best recollection of the published standard and must be verified.

### A.2 Policies related to AI

Theme: organizational policy framework for AI (policy content, alignment with organizational policies, and review).

| Control | Theme | Class | Artifact | Leverage |
|---|---|---|---|---|
| A.2.2 AI policy | The organization's AI policy and its alignment with organizational objectives. | H | AI-policy | M |
| A.2.3 Alignment with other organizational policies | AI policy alignment with security, privacy, and other policies. | H | AI-policy | M |
| A.2.4 Review of the AI policy | Scheduled review of the AI policy. | A | audit-log-entry | M |

### A.3 Internal organization

Theme: roles, responsibilities, and reporting lines for AI governance inside the organization.

| Control | Theme | Class | Artifact | Leverage |
|---|---|---|---|---|
| A.3.2 AI roles and responsibilities | Defined AI-specific roles and their responsibilities. | H | role-matrix | H |
| A.3.3 Reporting of concerns | Mechanism for reporting AI-related concerns internally. | A | audit-log-entry | M |

### A.4 Resources for AI systems

Theme: identifying, documenting, and managing the resources required to develop and operate AI systems (compute, data, human, tooling).

| Control | Theme | Class | Artifact | Leverage |
|---|---|---|---|---|
| A.4.2 Resource documentation | Documented AI system resources. | A | audit-log-entry | M |
| A.4.3 Data resources | Data resources required for AI systems. | H | (data-inventory) | H |
| A.4.4 Tooling resources | Tooling resources for AI systems. | A | (inventory) | M |
| A.4.5 System and computing resources | Compute and system resources. | A | (inventory) | M |
| A.4.6 Human resources | Human resources required for AI systems. | H | role-matrix, training-record | M |

### A.5 Assessing impacts of AI systems

Theme: the AISIA process and its documentation. This is the category most directly operationalized by the `aisia-runner` workflow.

| Control | Theme | Class | Artifact | Leverage |
|---|---|---|---|---|
| A.5.2 AI system impact assessment process | Establish the AISIA process. | H | AISIA-section | H |
| A.5.3 Documentation of AI system impact assessments | AISIA documentation requirements. | A | AISIA-section | H |
| A.5.4 Assessing AI system impact on individuals or groups | Impact on individuals and groups of individuals. | H | AISIA-section | H |
| A.5.5 Assessing societal impacts of AI systems | Broader societal impact. | H | AISIA-section | H |

### A.6 AI system life cycle

The largest and most operationally dense Annex A category. Covers the full development and operation life cycle: objectives, documentation, development process, verification, validation, deployment, and operational monitoring. Contains ten controls across two sub-categories: A.6.1 management guidance (objectives and processes) and A.6.2 AI system life-cycle processes.

**A.6.1 Management guidance for AI system development (objectives and processes):**

| Control | Theme | Class | Artifact | Leverage |
|---|---|---|---|---|
| A.6.1.2 Objectives for responsible development of AI systems | Responsible-development objectives. | J | AI-policy, objective-record | M |
| A.6.1.3 Processes for responsible design and development | Life-cycle process definition. | H | (process-doc) | M |
| A.6.1.4 Impact assessment for AI systems | Management guidance on AISIA performance and documentation. | H | AISIA-section | H |

**A.6.2 AI system life-cycle processes:**

| Control | Theme | Class | Artifact | Leverage |
|---|---|---|---|---|
| A.6.2.2 AI system requirements and specification | Requirements and specs. | H | (spec-doc) | M |
| A.6.2.3 Documentation of AI system design and development | Design and development documentation. | A | audit-log-entry | H |
| A.6.2.4 AI system verification and validation | V&V activities. | H | (V&V-record) | H |
| A.6.2.5 AI system deployment | Deployment controls. | H | audit-log-entry | M |
| A.6.2.6 AI system operation and monitoring | Operational monitoring. | A | KPI, audit-log-entry | H |
| A.6.2.7 AI system technical documentation | Technical documentation. | A | audit-log-entry | H |
| A.6.2.8 AI system log recording | Logs generated during operation. | A | audit-log-entry | H |

### A.7 Data for AI systems

Theme: the quality, provenance, and lifecycle of data used by AI systems. Strongly overlaps with data governance and privacy programs.

| Control | Theme | Class | Artifact | Leverage |
|---|---|---|---|---|
| A.7.2 Data for development and enhancement of AI systems | Data used in development. | H | (data-register) | H |
| A.7.3 Acquisition of data | Data acquisition controls. | H | (data-register) | M |
| A.7.4 Quality of data for AI systems | Data quality requirements. | H | (data-register) | H |
| A.7.5 Data provenance | Provenance tracking. | A | audit-log-entry | H |
| A.7.6 Data preparation | Preparation activities and their documentation. | H | (data-register) | M |

### A.8 Information for interested parties of AI systems

Theme: transparency obligations to users, affected individuals, and other interested parties.

| Control | Theme | Class | Artifact | Leverage |
|---|---|---|---|---|
| A.8.2 System documentation and information for users | User-facing documentation. | H | (user-doc) | M |
| A.8.3 External reporting | Reporting obligations to regulators and external parties. | A | audit-log-entry | H |
| A.8.4 Communication of incidents | Incident communication. | H | audit-log-entry | M |
| A.8.5 Information for interested parties | Broader stakeholder information. | H | (comms-plan) | L |

### A.9 Use of AI systems

Theme: controls governing how AI systems are used by the organization once deployed.

| Control | Theme | Class | Artifact | Leverage |
|---|---|---|---|---|
| A.9.2 Processes for responsible use of AI systems | Use-process definition. | H | (process-doc) | M |
| A.9.3 Objectives for responsible use of AI systems | Use objectives. | J | objective-record | M |
| A.9.4 Intended use of the AI system | Documented intended use. | H | audit-log-entry | M |

### A.10 Third-party and customer relationships

Theme: controls on AI systems provided by third parties and on obligations to customers receiving AI-based services.

| Control | Theme | Class | Artifact | Leverage |
|---|---|---|---|---|
| A.10.2 Allocating responsibilities | Responsibility allocation in third-party AI arrangements. | H | role-matrix | M |
| A.10.3 Suppliers | Supplier management. | H | (supplier-register) | M |
| A.10.4 Customers | Obligations to customers. | H | (customer-register) | M |

**Annex A class split (approximate, pending ID verification):** J 2, H 25, A 11.

## Priority-ranked operationalization backlog

Ranked by leverage class and cross-weighted against implementation sequence dependencies. Class-A and class-H items with H-leverage are the Phase 3 plugin targets. J-class items stay in SKILL.md prose and receive tooling only where information gathering or template production adds value.

### Tier 1: highest leverage, Phase 3 plugin priority

These items deliver the largest compliance leverage per unit of implementation effort and have well-scoped artifact outputs. The existing `audit-log-generator` stub in `plugins/` targets this tier.

1. **Clause 6.1.3: Statement of Applicability generation.** Artifact: `SoA-row` per Annex A control. Certification-audit centerpiece. Composable from system inventory plus Annex A control applicability.
2. **Clause 6.1.4 / A.5: AISIA generation.** Artifact: `AISIA-section`. The `aigovclaw/workflows/aisia-runner.md` workflow is the runtime consumer. High frequency (per system, per significant change), high tedium manually.
3. **Clause 7.5: documented information control.** Artifact: `audit-log-entry`. Presence checking, version control, approval workflow, retention. Underpins every other clause's evidence.
4. **Clause 9.3.2: management review input package.** Artifact: `review-minutes` preamble. Pulls from risk register, nonconformity log, audit results, KPI reports. High tedium manually, required at every review.
5. **Clause 10.2: nonconformity and corrective action.** Artifact: `nonconformity-record`. High frequency. Root-cause template, corrective-action tracking, effectiveness review.
6. **Clause 5.3 and A.3.2: role and responsibility matrix.** Artifact: `role-matrix`. Quick win. Input to multiple other controls (A.4.6, A.10.2).
7. **Clause 6.1.2 and 8.2: AI risk register.** Artifact: `risk-register-row`. Taxonomy-driven risk identification. Likelihood and impact scoring stays human-in-the-loop.

### Tier 2: medium leverage, opportunistic plugin work

Valuable operationalizations but lower frequency or smaller artifacts than Tier 1. Good candidates for community plugin contributions in Phase 3.

1. **A.2.4: AI policy review scheduling.** Artifact: `audit-log-entry`. Low code, high process value.
2. **Clause 6.2: AI objectives.** Artifact: `objective-record`. Links Clause 5.2 policy to Clause 9.1 measurement.
3. **Clause 6.3: change control.** Artifact: `change-record`. Velocity determines leverage.
4. **Clause 7.2 / 7.3: competence and awareness.** Artifact: `training-record`. Cross-walk to existing HR learning management systems.
5. **Clause 9.1: KPI reporting.** Artifact: `KPI`. Definition is hybrid; reporting is automatable.
6. **Clause 9.2.1 / 9.2.2: internal audit programme.** Artifact: audit programme doc plus `audit-log-entry` per engagement.
7. **A.6.2.6 / A.6.2.8: AI system operational monitoring and logs.** Artifact: `KPI`, `audit-log-entry`. Strong overlap with MLOps tooling.
8. **A.7.5: data provenance.** Artifact: `audit-log-entry`. Overlaps with data-lineage tooling.
9. **A.8.3: external reporting.** Artifact: `audit-log-entry`. Template-driven.

### Tier 3: judgment-bound, minimal tooling

Plugin work here risks producing evidence auditors reject. Keep the SKILL.md body prescriptive about what the organization must do; do not ship plugins that pretend to decide these items.

- Clause 4.1: context of the organization.
- Clause 5.1: leadership and commitment.
- Clause 7.1: resources.
- Clause 9.3.1: management review (the meeting itself).
- Clause 10.1: continual improvement (umbrella).
- A.6.1.2: responsible-development objectives.
- A.9.3: responsible-use objectives.

## Open design questions

Items 1 through 3 in prior versions of this map concerned control-ID verification and were resolved in the Lead Implementer validation pass on 2026-04-18. The remaining open items are design questions carried forward into Phase 4 planning:

1. **Responsible-development and responsible-use objectives (A.6.1.2, A.9.3) tier assignment.** Currently classified J-class because the objectives are set by the organization, not derived by the plugin. A future `objective-record` plugin may shift these toward H-class by producing organizationally-parameterizable drafts; decision is deferred.
2. **Data-register artifact type.** Several A.7 controls share an ambiguous `(data-register)` artifact slot in this map. Deferred: decide whether to add `data-register` as a formal artifact type (warranting a dedicated plugin) or to fold its rows into `audit-log-entry`.
3. **Cross-skill operationalization ownership.** Several Clause 6 and Annex A controls are implemented by plugins shared with the `nist-ai-rmf` skill. The shared-plugin convention (single plugin, `framework` flag) is established; documentation ownership (which skill's SKILL.md is authoritative for the shared plugin) is currently: the ISO skill owns the canonical description; the NIST skill cross-references.

## Next step

Draft `skills/iso42001/SKILL.md` body against this map, prioritized by Tier 1 items, with Tier 2 items receiving shorter "operationalize in Phase 3" stubs and Tier 3 items receiving prescriptive prose only. After the draft lands, Lead Implementer review corrects the flagged uncertainties and the `evals/iso42001/test_cases.yaml` file is populated against the corrected draft.
