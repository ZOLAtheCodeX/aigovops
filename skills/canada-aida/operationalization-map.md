# Canada AI Operationalization Map

Working document for the `canada-aida` skill. Maps each instrument in `regulatory-register.yaml` to AIGovOps plugin artifacts and the A/H/J operationalizability classification. Same methodology as the other skills in this repository.

**Validation status.** Register entries and section references validated on 2026-04-18 against the ISED AIDA companion document, the Parliament of Canada Bill C-27 page, the Office of the Privacy Commissioner of Canada, the OSFI website, the Treasury Board Directive page, and the Commission d'acces a l'information du Quebec. AIDA section references are to the draft text as tabled; these will be re-anchored to the enacted text if and when the Act receives Royal Assent.

**Design stance.** Canada is a secondary-priority jurisdiction under `docs/jurisdiction-scope.md`. AIDA is also drafting-volatile, which reinforces the no-plugin stance. Practitioners use the existing primary-jurisdiction plugins (iso42001, NIST AI RMF, EU AI Act) with Canadian citations added to the `citations` fields of artifact records. This map records which plugin produces which Canada-relevant output, and what Canada-specific additions the caller must supply.

## AIDA (Bill C-27, Part 3) anticipated obligations

| Obligation | Class | Artifact | AIGovOps plugin | Canada-specific additions |
|---|---|---|---|---|
| High-impact AI system designation | J | `AISIA-section` | `aisia-runner` | Counsel determination against the high-impact criteria in the draft text; supporting factual record |
| Risk identification, assessment, mitigation | H | `risk-register-row` | `risk-register-builder` | AIDA draft Section reference; mapping to ISO 42001 Clause 6.1.2 baseline |
| Non-discriminatory design measures | H | `AISIA-section` | `aisia-runner` | Fairness-testing evidence; protected-characteristic coverage |
| Transparency and plain-language description | A | `data-register-row` | `data-register-builder` | Plain-language summary; intended-use description; risk-mitigation description |
| Record-keeping obligations | A | `audit-log-entry` | `audit-log-generator` | Retention-period determination; record-scope determination |
| Incident or serious harm reporting | A | `audit-log-entry` | `audit-log-generator` | Incident-classification criteria; Minister/Commissioner notification field |

Citation format: `Canada AIDA (Bill C-27, Part 3), Section <n>` while drafting; `AIDA Section <n>` once in force.

## PIPEDA

| Obligation | Class | Artifact | AIGovOps plugin | Canada-specific additions |
|---|---|---|---|---|
| Identify purposes for collection | A | `data-register-row` | `data-register-builder` | Purpose taxonomy; PIPEDA Principle 4.2 reference |
| Obtain meaningful consent | A | `data-register-row` | `data-register-builder` | Consent-mechanism description; PIPEDA Principle 4.3 reference |
| Limit collection, use, disclosure, retention | H | `data-register-row` | `data-register-builder` | Retention-schedule linkage; disposal evidence |
| Safeguards proportional to sensitivity | H | `risk-register-row` | `risk-register-builder` | Safeguard-tiering rationale; PIPEDA Principle 4.7 reference |
| Individual access to personal information | H | `data-register-row` | `data-register-builder` | Access-request response SLA; record-location mapping |
| Breach notification to OPC and affected individuals | A | `audit-log-entry` | `audit-log-generator` | Breach-notification event record; real-risk-of-significant-harm determination |

Citation format: `PIPEDA, Section <n>`. PIPEDA principles in Schedule 1 are referenced as `PIPEDA, Schedule 1, Principle <n>`.

## Consumer Privacy Protection Act (proposed, Bill C-27 Part 1)

| Obligation | Class | Artifact | AIGovOps plugin | Canada-specific additions |
|---|---|---|---|---|
| Codified privacy management program | A | external (governance) | N/A | Program document outside the plugin catalogue |
| Automated decision-system explanation right (draft) | A | `audit-log-entry` | `audit-log-generator` | Explanation-delivery event; CPPA Section reference |
| De-identification and anonymization distinctions | A | `data-register-row` | `data-register-builder` | De-identification-method field; re-identification-risk field |

Citation format: `CPPA (Bill C-27, Part 1), Section <n>`.

Not yet in force. Tracked in the register with status `drafting`.

## OSFI Guideline E-23 (Model Risk Management)

| Obligation | Class | Artifact | AIGovOps plugin | Canada-specific additions |
|---|---|---|---|---|
| Enterprise-wide model inventory | A | `risk-register-row` | `risk-register-builder` | Model-ID field; model-tier field |
| Model risk tiering | H | `risk-register-row` | `risk-register-builder` | Tiering methodology; material/non-material determination |
| Independent model validation | H | `AISIA-section` | `aisia-runner` | Validator identity; validation-scope description |
| Ongoing monitoring and performance assessment | A | `metrics-report` | `metrics-collector` | Performance-threshold definition; drift-detection cadence |
| Governance and roles | A | `role-matrix` | `role-matrix-generator` | First-line, second-line, third-line role assignment |
| Documentation and audit trail | A | `audit-log-entry` | `audit-log-generator` | Validation-report retention; board-reporting cadence |

Citation format: `OSFI Guideline E-23, Paragraph <n>`.

Applies only to federally-regulated financial institutions. Outside that scope, OSFI Guideline E-23 is useful as a benchmark but not binding.

## Canada Directive on Automated Decision-Making (Treasury Board)

| Obligation | Class | Artifact | AIGovOps plugin | Canada-specific additions |
|---|---|---|---|---|
| Complete Algorithmic Impact Assessment | H | `AISIA-section` | `aisia-runner` | Mapping of AIGovOps AISIA fields onto the Government of Canada AIA questionnaire; impact-level determination |
| Apply proportional controls by impact level | H | `risk-register-row` | `risk-register-builder` | Impact-level-to-control-set mapping |
| Provide notice and explanation to affected individuals | A | `audit-log-entry` | `audit-log-generator` | Notice-delivery mechanism; explanation-delivery mechanism |
| Maintain recourse mechanisms | A | `role-matrix` | `role-matrix-generator` | Recourse-owner role; escalation path |
| Quality assurance and peer review | A | `AISIA-section` | `aisia-runner` | Peer-review-attestation field |

Citation format: `Canada Directive on Automated Decision-Making, Subsection <n>`.

Applies only to federal government departments and agencies. The AIGovOps AISIA fields map onto the Government of Canada AIA questionnaire; federal practitioners use the plugin output to pre-populate the questionnaire.

## Quebec Law 25

| Obligation | Class | Artifact | AIGovOps plugin | Canada-specific additions |
|---|---|---|---|---|
| Privacy impact assessment for confidentiality of personal information | H | `AISIA-section` | `aisia-runner` | Quebec-resident scope assertion; sensitivity-of-information field |
| Consent and transparency for personal information use | A | `data-register-row` | `data-register-builder` | Quebec-specific consent-language reference |
| Automated decision-making notice | A | `audit-log-entry` | `audit-log-generator` | Notice-delivery event record; right-to-be-heard documentation |
| Right to correction and observations submission | H | `data-register-row` | `data-register-builder` | Correction-workflow linkage |
| Governance role: person in charge of protection of personal information | A | `role-matrix` | `role-matrix-generator` | Quebec-specific role-label field |

Citation format: `Quebec Law 25, Section <n>`.

Quebec Law 25 intersects both the privacy-rooted tier and the automated decision-making surface. The automated decision-making notice at Section 12.1 is the most operationally distinct requirement.

## Canada Voluntary Code of Conduct on Advanced Generative AI Systems (2023)

| Obligation (Principle) | Class | Artifact | AIGovOps plugin | Canada-specific additions |
|---|---|---|---|---|
| Accountability | A | `gap-assessment` | `gap-assessment` | `target_framework="ca-voluntary-code"`; principle reference |
| Safety | A | `gap-assessment` | `gap-assessment` | Red-team-testing evidence; harm-mitigation evidence |
| Fairness and equity | A | `gap-assessment` | `gap-assessment` | Fairness-testing evidence |
| Transparency | A | `gap-assessment` | `gap-assessment` | Content-provenance evidence; capability-and-limitation disclosure |
| Human oversight and monitoring | A | `gap-assessment` | `gap-assessment` | Oversight-role-assignment evidence |
| Validity and robustness | A | `gap-assessment` | `gap-assessment` | Evaluation-benchmarks evidence; robustness-testing evidence |

Citation format: `Canada Voluntary AI Code (2023), Principle <n>`.

Non-binding. Signatories self-report against the six principles. The `gap-assessment` plugin produces the signed self-report surface when invoked with `target_framework="ca-voluntary-code"`.

## Counts across the skill

| Class | Obligations |
|---|---|
| A | 22 |
| H | 11 |
| J | 1 |

The Canadian footprint is wider than a single-instrument jurisdiction because it spans federal statute (PIPEDA), draft federal statute (AIDA, CPPA), federal sectoral (OSFI E-23), federal directive (Treasury Board), provincial statute (Quebec Law 25), and voluntary code. Most obligations map to plugins that already exist for primary-jurisdiction frameworks. Canada adds citations and scope annotations rather than new plugin logic.

## Cross-jurisdictional consolidation

A Canadian-operating AI system often also falls under NIST AI RMF, ISO 42001, and (for generative AI reaching the EU) the EU AI Act. The table below shows overlap. Practitioners who produce the ISO 42001 and NIST artifacts in `dual` mode capture most Canadian-specific content through citation extension.

| Canadian instrument | EU AI Act analogue | NIST AI RMF analogue | ISO 42001 analogue |
|---|---|---|---|
| AIDA risk management (draft) | Article 9 risk management; Article 27 FRIA | MAP 5.2; MEASURE 2.11; MANAGE 2.1 | Clause 6.1.2; Annex A, Control A.6.2.4 |
| AIDA transparency (draft) | Article 13; Article 50 | MAP 5.1; MEASURE 2.8 | Annex A, Control A.9.2 |
| AIDA record-keeping (draft) | Article 12; Annex IV | MANAGE 4.1 | Clause 7.5; Annex A, Control A.5 |
| PIPEDA consent and safeguards | GDPR-analogue through Article 10(5) intersection | MAP 4.1 | Annex A, Control A.7 |
| OSFI Guideline E-23 model risk | Article 9 risk management (analogue) | MEASURE 2.3; MANAGE 2.4 | Clause 6.1.2; Clause 9.1 |
| Treasury Board Directive AIA | Article 27 FRIA (analogue) | MAP 5.2 | Clause 6.1.2 |
| Quebec Law 25 automated decision notice | Article 26(11); Article 50 | MAP 5.1 | Annex A, Control A.9.2 |
| Voluntary Code principles | Code of Practice (Article 56) analogue | GOVERN cross-cut | Clause 5.1 |

Where cells are blank, the overlap is partial or the framework treats the issue obliquely. Counsel should review overlap determinations before relying on an aggregation.
