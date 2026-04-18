# NIST AI Risk Management Framework 1.0 Operationalization Map

Working document for the `nist-ai-rmf` skill. Maps every function, category, and subcategory of NIST AI RMF 1.0 to an operationalizability class, a candidate artifact type, and an operational-leverage ranking. Structure mirrors `../iso42001/operationalization-map.md` so the two maps can be reviewed together and so crosswalk decisions are obvious at the row level.

**Methodology reference.** A/H/J classes, artifact vocabulary, and leverage scoring are identical to the ISO 42001 map. See `../iso42001/operationalization-map.md` for the full methodology statement. This map omits the methodology preamble.

**Authority caveat.** Subcategory IDs are flagged `[verify]` where sub-numbering needs confirmation against the published NIST AI RMF 1.0 Core. Function names (GOVERN, MAP, MEASURE, MANAGE) and top-level category structure are stable. The AI RMF Playbook (https://airc.nist.gov/AI_RMF_Knowledge_Base/Playbook) supplies per-subcategory implementation suggestions and is the primary source for operationalization detail beyond this map.

**Verification note on counts.** NIST AI RMF 1.0 Core contains 72 subcategories across 19 categories across 4 functions. The counts below are best-effort; any off-by-one at the category level must reconcile to 72 before this map drives SKILL.md body drafting.

## Relationship to ISO/IEC 42001:2023

Operationalization overlap with the `iso42001` skill is substantial. Both frameworks require: risk identification and treatment, documentation, role assignment, incident response, third-party risk management, and ongoing monitoring. Many AIGovOps plugins produce artifacts usable under both standards with minor rendering differences.

Key structural differences that affect operationalization choices:

- **ISO 42001 is a management-system standard.** It requires conformance at the system level (Plan-Do-Check-Act loop) and produces a Statement of Applicability (Clause 6.1.3). NIST AI RMF has no direct SoA analogue; the equivalent is a voluntary documentation of which subcategories the organization has adopted.
- **NIST is risk-framework-first.** The MAP function front-loads contextual understanding that ISO distributes across Clauses 4 and 6.1. MEASURE is far more developed in NIST than in ISO 42001 Clause 9.
- **NIST is voluntary; ISO is certifiable.** This affects auditor acceptance criteria. NIST outputs are accepted by internal stakeholders, federal contracting officers, and customers; ISO outputs are accepted by accredited certification bodies. The quality bar for AIGovOps outputs is the ISO bar (certification-grade) because meeting it also satisfies NIST.

Where a NIST subcategory maps to an ISO clause with a shared operationalization, the `Notes` column flags the crosswalk. When drafting `SKILL.md` bodies, shared operationalizations are documented once (preferring the ISO skill) and cross-referenced from the other.

## GOVERN function

GOVERN cultivates a culture of AI risk management across the organization. It is broadly analogous to ISO 42001 Clauses 4, 5, 6.1 (policy and governance portions), and 7.1 to 7.3.

### GOVERN 1: Policies, processes, procedures, practices

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| GOVERN 1.1 | Legal and regulatory requirements understood, managed, documented. | H | (legal-register) | M | Crosswalk: ISO 42001 Clause 4.2 interested parties; Annex A A.2.3 policy alignment. Automation: legal register population from contracts and a jurisdiction inventory. |
| GOVERN 1.2 | AI risk management characteristics (trustworthy AI attributes) integrated into organizational policies. | H | `AI-policy` | M | Crosswalk: ISO 42001 Clause 5.2, Annex A A.2.2. Shared operationalization with iso42001 T1 policy drafting. |
| GOVERN 1.3 | Processes for AI risk management established. | H | (process-doc) | M | Crosswalk: ISO 42001 Clause 6.1.1. |
| GOVERN 1.4 | Risk tolerance defined and communicated. | J | `AI-policy` | L | Tolerance is an executive judgment call. Draft scaffold possible. |
| GOVERN 1.5 | Ongoing monitoring and review of AI risks. | A | `KPI`, `audit-log-entry` | H | Crosswalk: ISO 42001 Clause 9.1 (MEASURE overlap as well). |
| GOVERN 1.6 [verify] | Mechanisms to address third-party AI systems. | H | (supplier-register) | M | Crosswalk: ISO 42001 Annex A A.10 third-party relationships. |
| GOVERN 1.7 [verify] | Decommissioning processes for AI systems. | H | `audit-log-entry` | M | Crosswalk: ISO 42001 Annex A A.6 life-cycle processes (end-of-life). |

**Count check:** approximately 7 subcategories.

### GOVERN 2: Accountability structures

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| GOVERN 2.1 | Roles, responsibilities, lines of communication for AI risk documented and assigned. | H | `role-matrix` | H | Crosswalk: ISO 42001 Clause 5.3, Annex A A.3.2. Shared operationalization with iso42001 T1.6. |
| GOVERN 2.2 | Workforce trained on AI risk management roles. | A | `training-record` | M | Crosswalk: ISO 42001 Clauses 7.2, 7.3. |
| GOVERN 2.3 | Executive leadership takes responsibility for AI risk management. | J | `review-minutes` | L | Evidence in management-review participation. |

### GOVERN 3: Workforce diversity

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| GOVERN 3.1 [verify] | Decision-making and oversight teams reflect diversity and interdisciplinary expertise. | J | `role-matrix` | L | Composition decision is human. Plugin can surface gaps. |
| GOVERN 3.2 [verify] | Policies on how workforce is informed about and equipped to address AI system risks. | A | `training-record` | M | Same vehicle as GOVERN 2.2. |

### GOVERN 4: Culture, risk tolerance, communication

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| GOVERN 4.1 | Organizational practices encourage critical thinking and safety-first mindset. | J | (culture-artifacts) | L | No direct artifact. Evidence from training, incident response patterns, review minutes. |
| GOVERN 4.2 | Organizational teams document risks and impacts. | A | `risk-register-row`, `AISIA-section` | H | Crosswalk: ISO 42001 Clauses 6.1.2, 6.1.4. Shared with iso42001 T1.7 and T1.2. |
| GOVERN 4.3 | Testing, incident response, and recovery processes practiced and documented. | H | `audit-log-entry` | M | Crosswalk: ISO 42001 Clause 10.2 nonconformity + Annex A A.6 life-cycle. |

### GOVERN 5: External engagement

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| GOVERN 5.1 | Policies and processes for eliciting external stakeholder feedback. | H | (feedback-log) | M | Crosswalk: ISO 42001 Clause 4.2. Integration target: customer feedback and public consultation systems. |
| GOVERN 5.2 [verify] | Mechanisms for incorporating feedback and addressing AI risks from external sources. | H | `audit-log-entry` | M | Process evidence. |

### GOVERN 6: Third-party software, data, and systems

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| GOVERN 6.1 | Policies and procedures for third-party AI risks. | H | (supplier-register) | M | Crosswalk: ISO 42001 Annex A A.10. |
| GOVERN 6.2 [verify] | Contingency processes for third-party AI failures. | H | (incident-playbook) | M | Shared with GOVERN 4.3. |

**GOVERN class split (approximate):** J 4, H 12, A 3. Total approximately 19 subcategories.

## MAP function

MAP establishes the context to frame risks related to the AI system. Analogue to ISO 42001 Clause 4 (context of the organization), parts of Clause 6.1, and Annex A A.5 (assessing impacts).

### MAP 1: Context established and understood

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MAP 1.1 | Intended purpose, potentially beneficial uses, context-specific laws. | H | `AISIA-section` | H | Crosswalk: ISO 42001 Clause 6.1.4, Annex A A.5.2. Shared with iso42001 T1.2. |
| MAP 1.2 | Interdisciplinary AI actors consulted. | H | (stakeholder-log) | M | Consultation evidence. |
| MAP 1.3 | Organization's mission and goals for AI documented. | H | `AI-policy` | M | Crosswalk: ISO 42001 Clause 5.2. |
| MAP 1.4 | Business value and social context understood. | H | `AISIA-section` | M | Augments MAP 1.1. |
| MAP 1.5 | Organizational risk tolerances reflected in context mapping. | J | (applied in others) | L | Tolerance is GOVERN 1.4's output; applied here. |
| MAP 1.6 [verify] | System requirements elicitation includes stakeholder expectations. | H | (spec-doc) | M | Requirements process. |

### MAP 2: Categorization of the AI system

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MAP 2.1 | Specific tasks and methods used to implement them documented. | A | `audit-log-entry` | H | Crosswalk: ISO 42001 Annex A A.6.2.3 design and development documentation. |
| MAP 2.2 | Information about the AI system's knowledge limits and operational context. | A | `audit-log-entry` | M | Technical documentation component. |
| MAP 2.3 | Scientific integrity and TEVV (test, evaluation, verification, validation) considerations documented. | H | (V&V-record) | H | Crosswalk: ISO 42001 Annex A A.6.2.4. |

### MAP 3: AI capabilities and potential benefits mapped

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MAP 3.1 | Benefits identified and documented. | H | `AISIA-section` | M | Benefits side of AISIA. |
| MAP 3.2 | Potential costs (including non-monetary) of the AI system documented. | H | `AISIA-section` | H | Costs side of AISIA. Crosswalk: ISO 42001 Annex A A.5.4, A.5.5. |
| MAP 3.3 | Targeted application scope specified and documented. | H | `AISIA-section` | M | Scope documentation feeds into ISO 42001 Clause 4.3. |
| MAP 3.4 [verify] | Processes for operator and practitioner proficiency. | H | `training-record` | M | Crosswalk: ISO 42001 Clause 7.2, Annex A A.4.6. |
| MAP 3.5 | Processes for human oversight of AI system outputs documented. | H | (oversight-process-doc) | H | High-leverage: human oversight is centerpiece of trustworthy-AI narrative. |

### MAP 4: Risks and benefits to all components mapped

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MAP 4.1 | Approaches for mapping AI risks to specific components documented. | H | `risk-register-row` | H | Crosswalk: ISO 42001 Clause 6.1.2. |
| MAP 4.2 | Internal risk controls for AI system components identified. | H | (control-inventory) | M | Input to MANAGE function. |

### MAP 5: Impacts on individuals, groups, communities, organizations, society

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MAP 5.1 | Likelihood and magnitude of each identified impact assessed. | H | `AISIA-section` | H | Crosswalk: ISO 42001 Clause 6.1.4, Annex A A.5.4. |
| MAP 5.2 [verify] | Practices and personnel for supporting regular engagement with relevant AI actors. | J | (stakeholder-log) | M | Engagement cadence is human-run. |

**MAP class split (approximate):** J 2, H 16, A 2. Total approximately 20 subcategories.

## MEASURE function

MEASURE analyzes, assesses, benchmarks, and monitors AI risk and related impacts. Strong overlap with ISO 42001 Clause 9 (Performance evaluation) and with technical MLOps practice. This is where the operationalization density is highest for automated pipelines.

### MEASURE 1: Appropriate methods and metrics

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MEASURE 1.1 | Approaches and metrics for measurement of AI risks documented. | H | (metrics-catalog) | H | Foundational for the rest of MEASURE. |
| MEASURE 1.2 [verify] | Appropriateness of metrics and measurement approaches periodically evaluated. | A | `audit-log-entry` | M | Meta-measurement. |
| MEASURE 1.3 [verify] | Internal experts involved in selection of methods, metrics, and periodic re-evaluation. | J | `role-matrix` | L | Composition decision. |

### MEASURE 2: AI systems evaluated for trustworthy characteristics

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MEASURE 2.1 | Test sets, metrics, and details related to model performance documented. | A | (V&V-record, `KPI`) | H | Crosswalk: ISO 42001 Annex A A.6.2.4. |
| MEASURE 2.2 | Evaluations on human subjects conducted where applicable. | H | `AISIA-section` | M | Human-subjects research overlay. |
| MEASURE 2.3 | AI system performance evaluated in context. | A | `KPI` | H | In-context performance measurement. |
| MEASURE 2.4 | Measurement approaches applicable to deployment context used. | A | `KPI` | M | |
| MEASURE 2.5 | System's validity and reliability characteristics documented. | A | `audit-log-entry`, `KPI` | H | Evidence. |
| MEASURE 2.6 | Safety risks and incidents documented. | A | `audit-log-entry` | H | Crosswalk: ISO 42001 Clause 10.2 nonconformity + Annex A A.6.2.6 operational monitoring. |
| MEASURE 2.7 | Security and resilience evaluated. | A | `KPI`, `audit-log-entry` | H | ML security testing evidence. |
| MEASURE 2.8 | Explainability and interpretability evaluated. | H | `KPI`, `audit-log-entry` | M | Context-dependent. |
| MEASURE 2.9 [verify] | Privacy risk evaluated. | A | `KPI` | H | Privacy impact assessment hooks. Crosswalk: GDPR DPIA. |
| MEASURE 2.10 [verify] | Fairness evaluated across demographic groups. | A | `KPI` | H | Fairness metrics pipeline. |
| MEASURE 2.11 [verify] | Environmental impacts evaluated. | A | `KPI` | M | Sustainability metric. |
| MEASURE 2.12 [verify] | Computational efficiency and cost evaluated. | A | `KPI` | M | |
| MEASURE 2.13 [verify] | Effectiveness of measurement methodology periodically reviewed. | A | `audit-log-entry` | M | Meta-measurement. |

### MEASURE 3: Mechanisms for tracking

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MEASURE 3.1 | Approaches to ongoing monitoring established and deployed. | A | `KPI`, `audit-log-entry` | H | Crosswalk: ISO 42001 Clause 9.1. |
| MEASURE 3.2 | Identified risks communicated to relevant AI actors. | A | `audit-log-entry` | M | Reporting pipeline. |
| MEASURE 3.3 [verify] | Feedback mechanisms for affected individuals and groups. | H | (feedback-log) | M | |

### MEASURE 4: Feedback about measurement efficacy

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MEASURE 4.1 | Measurement approaches periodically assessed for efficacy. | A | `audit-log-entry` | M | Meta-measurement close. |
| MEASURE 4.2 | Measurement results documented and made available to relevant AI actors. | A | `audit-log-entry` | M | Distribution evidence. |
| MEASURE 4.3 [verify] | Measurement outcomes incorporated into organizational processes. | H | `review-minutes`, `risk-register-row` | H | Closes MEASURE to GOVERN and MANAGE. |

**MEASURE class split (approximate):** J 1, H 6, A 14. Total approximately 21 subcategories. This is the highest-automation function.

## MANAGE function

MANAGE allocates risk resources to mapped and measured risks. Analogue to ISO 42001 Clauses 6.1.3 (treatment), 8.3 (operational treatment), and 10.2 (nonconformity and corrective action).

### MANAGE 1: AI risks addressed per organizational risk tolerances

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MANAGE 1.1 | Determination made for whether AI system achieves its intended purposes. | J | `review-minutes` | L | Go or no-go decision. |
| MANAGE 1.2 | Treatment of documented AI risks based on risk tolerance. | H | `risk-register-row` | H | Crosswalk: ISO 42001 Clause 6.1.3. |
| MANAGE 1.3 | Responses to high-priority AI risks developed and implemented. | H | `risk-register-row`, `audit-log-entry` | H | Action implementation. |
| MANAGE 1.4 | Negative residual risks documented for affected AI actors. | H | `risk-register-row` | M | Transparency requirement. |

### MANAGE 2: Strategies to maximize benefits, minimize negative impacts

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MANAGE 2.1 | Resources and controls implemented to address impacts. | H | `SoA-row` (or equivalent), `audit-log-entry` | M | Crosswalk: ISO 42001 Clause 6.1.3 + SoA structure (if dual-track). |
| MANAGE 2.2 | Mechanisms to sustain the value of AI systems implemented. | H | `audit-log-entry` | M | Lifecycle management. |
| MANAGE 2.3 | Procedures for responding to and recovering from negative impacts. | H | (incident-playbook) | M | Crosswalk: GOVERN 4.3. |
| MANAGE 2.4 [verify] | Mechanisms for superseded, rogue, or unknown AI systems. | H | `audit-log-entry` | M | Shadow-AI detection and decommissioning. |

### MANAGE 3: AI risks and benefits from third-party entities managed

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MANAGE 3.1 [verify] | AI risks and benefits from third-party sources identified and managed. | H | (supplier-register) | M | Crosswalk: GOVERN 6, ISO 42001 Annex A A.10. |
| MANAGE 3.2 [verify] | Pre-trained models tested, monitored, managed. | H | (V&V-record) | H | Foundation model governance. Crosswalk: ISO 42001 Annex A A.7 data (for training data provenance). |

### MANAGE 4: Risk treatment documented, monitored, improved

| Subcategory | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MANAGE 4.1 | Post-deployment AI monitoring plans implemented. | A | `KPI`, `audit-log-entry` | H | Crosswalk: MEASURE 3.1, ISO 42001 Annex A A.6.2.6. |
| MANAGE 4.2 | Measurable activities for continual improvement integrated. | H | `review-minutes`, `nonconformity-record` | H | Crosswalk: ISO 42001 Clause 10. |
| MANAGE 4.3 [verify] | Incidents and errors communicated to relevant AI actors. | A | `audit-log-entry` | M | Communication evidence. |

**MANAGE class split (approximate):** J 1, H 9, A 2. Total approximately 12 subcategories.

## GenAI Profile (NIST AI 600-1) overlay

NIST AI 600-1, the Generative AI Profile, overlays the four functions with subcategory-level guidance specific to generative AI risks: confabulation, data privacy, dangerous or violent recommendations, human-AI configuration risks, information integrity, obscene or abusive content, intellectual property, value chain and component integration.

This map treats AI 600-1 as an applicability overlay, not a new subcategory set. When an organization operates generative AI systems, the AI 600-1 guidance modifies the operationalization of several subcategories. Notable overlay points:

- **MEASURE 2.6 (safety risks and incidents)** gains confabulation, abusive content, and violent recommendation metrics.
- **MEASURE 2.9 (privacy)** gains training-data exposure and regurgitation metrics.
- **MAP 1.1 (intended purpose)** requires explicit GenAI use-case boundaries.
- **GOVERN 6 (third-party)** gains pre-trained foundation model provenance tracking.

The `nist-ai-rmf` SKILL.md body references AI 600-1 as an overlay. A dedicated `nist-ai-genai-profile` skill is a candidate Phase 3 deliverable if demand warrants separation.

## Priority-ranked operationalization backlog

Ranked by leverage, cross-weighted against shared operationalizations with the `iso42001` skill. Items that share an operationalization with iso42001 receive their numbering priority from the iso42001 backlog; new items (NIST-only) are interleaved by leverage.

### Tier 1 (NIST AI RMF plugin priority)

1. **MAP 1.1, MAP 3.1, MAP 3.2, MAP 5.1: AISIA / impact-assessment set.** Shared operationalization with iso42001 T1.2 (AISIA). One plugin serves both frameworks; rendering differs.
2. **MEASURE 2.1, 2.3, 2.5, 2.6, 2.7: technical performance and safety measurement.** A-class, high leverage, and the most NIST-distinctive operationalization area (ISO 42001's equivalent coverage is thinner). Pipeline plugin: `metrics-collector` (Phase 3 candidate).
3. **MAP 4.1, MANAGE 1.2, 1.3: risk register and treatment.** Shared operationalization with iso42001 T1.7 (risk register). Unified `risk-register-row` serves both.
4. **GOVERN 2.1: role and responsibility matrix.** Shared operationalization with iso42001 T1.6.
5. **GOVERN 1.5, MEASURE 3.1, MEASURE 4.1, MANAGE 4.1: ongoing monitoring.** A-class. Feeds dashboards. Crosswalk to ISO 42001 Clause 9.1.
6. **MEASURE 2.9, 2.10: privacy and fairness metrics.** A-class. Distinctive NIST leverage because ISO 42001 is less prescriptive on these metrics.
7. **MANAGE 4.2: continual improvement integration.** Shared operationalization with iso42001 T1.5 (nonconformity and corrective action).

### Tier 2 (opportunistic)

1. **GOVERN 1.1: legal and regulatory register.** Integration target: existing legal-hold or compliance registers.
2. **GOVERN 1.2, MAP 1.3: AI policy and mission documentation.** Shared with iso42001 T1 policy drafting.
3. **GOVERN 2.2, GOVERN 3.2: workforce training.** Shared with iso42001 T2.
4. **GOVERN 4.3, MANAGE 2.3: incident response playbook.** Shared across functions.
5. **GOVERN 6, MANAGE 3: third-party and pre-trained model management.** Shared with iso42001 Annex A A.10.
6. **MAP 2.1, 2.2, 2.3: system documentation.** Shared with iso42001 Annex A A.6.2.3.
7. **MAP 3.3, 3.4: targeted application scope and operator proficiency.** Training and scope documentation.
8. **MEASURE 1.1: metrics catalog.** Foundational; enables MEASURE 2.x pipelines.

### Tier 3 (judgment-bound, prescriptive prose only)

- GOVERN 1.4 (risk tolerance).
- GOVERN 2.3 (executive accountability).
- GOVERN 3.1 (workforce diversity).
- GOVERN 4.1 (culture).
- GOVERN 5.1 (external stakeholder feedback process definition; execution is automation-assisted).
- MAP 1.5 (risk tolerance application).
- MAP 5.2 (engagement cadence).
- MEASURE 1.3 (expert selection).
- MANAGE 1.1 (go or no-go decision).

## Open questions (resolve before SKILL.md body commit)

1. **Exact subcategory counts and IDs.** Function and category structure is stable; specific sub-numbering (for example, whether GOVERN 1 has 6 or 7 subcategories) needs confirmation against the published AI RMF 1.0 Core document. Off-by-one at the subcategory level is expected and does not invalidate the operationalization analysis.
2. **Reconciliation to 72.** Sum of approximate counts: GOVERN 19 + MAP 20 + MEASURE 21 + MANAGE 12 = 72. This matches the official total. Individual category counts may need correction.
3. **NIST has no formal SoA equivalent.** The NIST `SKILL.md` should clarify that MANAGE 2.1 (controls implemented) is the analogue, but the artifact is less formal. When operating dual-track (ISO and NIST), the ISO SoA serves both; when NIST-only, a lighter "implemented subcategories register" suffices. This is a plugin rendering decision, not a new artifact type.
4. **AI 600-1 overlay: separate skill or inline?** Current posture: inline overlay in the `nist-ai-rmf` skill. Reconsider if GenAI operationalization grows enough to warrant a dedicated skill.
5. **Measurement metric library ownership.** MEASURE 2 subcategories each imply specific metric families (fairness, robustness, privacy, explainability, safety). Does the `nist-ai-rmf` skill own a metric-catalog artifact, or is the catalog a separate shared artifact used by multiple skills? Recommended: shared `metrics-catalog` artifact type added to the vocabulary, owned by this skill initially and expanded by others.
6. **Shared operationalizations governance.** When the ISO and NIST SKILL.md files both describe the same plugin (for example, AISIA), which file is authoritative and which cross-references? Proposed rule: the ISO skill is authoritative because ISO's artifact requirements are stricter; the NIST skill cross-references and notes any rendering or scope differences.

## Next step

Draft `skills/nist-ai-rmf/SKILL.md` body against the Tier 1 priority list. For subcategories that share an operationalization with the `iso42001` skill, the NIST SKILL.md cross-references the ISO SKILL.md section rather than duplicating content. NIST-distinctive operationalizations (especially the MEASURE 2.x metric families) get full treatment in the NIST SKILL.md.
