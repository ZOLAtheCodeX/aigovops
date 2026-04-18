# Singapore AI Governance operationalization map

Cross-framework mapping from Singapore MAGF 2e pillars and MAS FEAT Principles to AIGovOps artifact types and plugins. Read [SKILL.md](SKILL.md) first for scope and definitions.

## MAGF pillars to AIGovOps artifacts

| MAGF pillar | Requirement | AIGovOps artifact | Plugin | Mode |
|---|---|---|---|---|
| Pillar 1 Internal Governance | Roles and responsibilities | role-matrix | `role-matrix-generator` | default |
| Pillar 1 Internal Governance | Risk management and internal controls | risk-register | `risk-register-builder` | default |
| Pillar 1 Internal Governance | Staff training and audit events | audit-log | `audit-log-generator` | default |
| Pillar 2 Human Involvement | Probability-severity matrix; tier selection | AISIA human-oversight dimension | `aisia-runner` | default |
| Pillar 2 Human Involvement | Escalation process | audit-log | `audit-log-generator` | default |
| Pillar 3 Operations Management | Data lineage, quality, bias | data-register | `data-register-builder` | default |
| Pillar 3 Operations Management | Model robustness, drift, bias metrics | metrics | `metrics-collector` | default |
| Pillar 3 Operations Management | Risk treatment and SoA | risk-register plus SoA | `risk-register-builder`, `soa-generator` | default |
| Pillar 4 Stakeholder Communication | Disclosure of AI use | audit-log | `audit-log-generator` | default |
| Pillar 4 Stakeholder Communication | Data subject channels; decision-review | audit-log; data-register | `audit-log-generator`, `data-register-builder` | default |
| Cross-pillar | Pillar-by-pillar assessment | magf-assessment | `singapore-magf-assessor` | default |

## MAGF Pillar 1 Internal Governance to ISO 42001 and NIST AI RMF

| MAGF expectation | ISO 42001 anchor | NIST AI RMF anchor |
|---|---|---|
| Clear roles and responsibilities | Clause 5.3; Annex A.3.2 | GOVERN 2.1 |
| AI risk management and internal controls | Clause 6.1; Annex A.5.2 | GOVERN 1.4; MAP 1.1 |
| Staff training | Clause 7.2; Annex A.4.3 | GOVERN 2.2 |

## MAGF Pillar 2 Human Involvement to ISO 42001 and NIST AI RMF

| MAGF expectation | ISO 42001 anchor | NIST AI RMF anchor | EU AI Act parallel |
|---|---|---|---|
| Probability-severity matrix | Clause 6.1.2; Annex A.5.2 | MAP 5.1; MAP 5.2 | Article 14(2) |
| Tier selection (in / over / out of the loop) | Annex A.9.2 | MANAGE 2.3 | Article 14(4) |
| Escalation process | Annex A.6.2.8 | MANAGE 2.3 | Article 14(4)(b) |

## MAGF Pillar 3 Operations Management to ISO 42001 and NIST AI RMF

| MAGF expectation | ISO 42001 anchor | NIST AI RMF anchor |
|---|---|---|
| Data lineage | Annex A.7.4 | MAP 4.1; MEASURE 2.1 |
| Data quality | Annex A.7.4 | MEASURE 2.7 |
| Bias mitigation | Annex A.7.4; Annex A.6.2.4 | MEASURE 2.11 |
| Model robustness | Annex A.6.2.4 | MEASURE 2.7 |
| Explainability | Annex A.8.2 | MEASURE 2.9 |
| Reproducibility | Annex A.6.2.6 | MEASURE 2.5 |
| Monitoring and tuning | Annex A.9.3; Annex A.9.4 | MANAGE 4.1 |

## MAGF Pillar 4 Stakeholder Communication to ISO 42001 and NIST AI RMF

| MAGF expectation | ISO 42001 anchor | NIST AI RMF anchor |
|---|---|---|
| General disclosure of AI use | Annex A.8.2 | GOVERN 5.1 |
| Feedback and decision-review mechanism | Annex A.9.2 | MANAGE 4.1 |
| Acceptable-use policy | Annex A.8.3 | GOVERN 5.1 |

## MAS FEAT Principles to ISO 42001, NIST AI RMF, and AI Verify

| FEAT principle | ISO 42001 anchor | NIST AI RMF anchor | AI Verify principle |
|---|---|---|---|
| Fairness | Annex A.6.2.4; Annex A.7.3 | MEASURE 2.11 | fairness |
| Ethics | Clause 5; Annex A.3 | GOVERN 1.1; GOVERN 3.2 | inclusive-growth |
| Accountability | Clause 5.3; Annex A.3.3 | GOVERN 1.2 | accountability |
| Transparency | Annex A.8.2 | MEASURE 2.8 | transparency |

## AI Verify (IMDA 2024) 11 principles to MAGF pillars

| AI Verify principle | MAGF pillar |
|---|---|
| accountability | Internal Governance |
| data-governance | Operations Management |
| human-agency-oversight | Human Involvement |
| inclusive-growth | Stakeholder Communication |
| privacy | Operations Management |
| reproducibility | Operations Management |
| robustness | Operations Management |
| safety | Operations Management |
| security | Operations Management |
| transparency | Stakeholder Communication |
| fairness | Operations Management + Stakeholder Communication |

## Veritas relationship

MAS Veritas is a methodology for computing FEAT metrics in financial AI. Not produced by this plugin. The Veritas open-source toolkit at https://github.com/mas-veritas2/veritastoolkit provides notebooks and reference implementations for Fairness (Phase 1, 2019), Ethics and Accountability (Phase 2, 2021), and Transparency (Phase 3, 2022). Practitioners needing Veritas-style fairness metrics run the Veritas toolkit and attach its outputs as evidence_refs in the MAGF assessment.

## Leverage points for dual-regime organizations

Organizations already operating under ISO 42001 or NIST AI RMF have strong leverage on Singapore MAGF and FEAT:

1. **Governance.** ISO Clause 5 and NIST GOVERN satisfy MAGF Pillar 1.
2. **Impact assessment.** ISO Clause 8.2 (AISIA) plus a MAGF Pillar 2 addendum documents probability-severity and human-involvement tier.
3. **Data and model controls.** ISO Annex A.7 and A.6 plus NIST MAP and MEASURE functions cover MAGF Pillar 3.
4. **Transparency.** ISO Annex A.8.2 plus NIST MEASURE 2.8 cover MAGF Pillar 4 and FEAT Transparency.
5. **Fairness (financial services).** NIST MEASURE 2.11 plus the Veritas toolkit covers FEAT Fairness sub-criteria.
