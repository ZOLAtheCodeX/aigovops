# Certification Readiness Operationalization Map

Working document for the `certification-readiness` skill. Maps each target certification to the required artifact set, evidence strength floor, target-specific checks, and curated remediation actions.

## Target certifications

The skill supports nine target certifications. Each maps to a specific authoritative framework provision.

| Target enum | Framework provision | Primary trigger |
|---|---|---|
| `iso42001-stage1` | ISO/IEC 42001:2023 Clause 9.2 | Stage 1 is a document review audit. The reviewer confirms the AIMS design is complete and documented before Stage 2. |
| `iso42001-stage2` | ISO/IEC 42001:2023 Clauses 9.2, 9.3 | Stage 2 is the implementation audit. At least one full internal-audit cycle must be completed. |
| `iso42001-surveillance` | ISO/IEC 42001:2023 Clauses 10.1, 10.2 | Post-certificate surveillance audits focus on continual improvement evidence. |
| `eu-ai-act-internal-control` | EU AI Act Article 43, Annex VI | Internal-control conformity assessment route for high-risk systems under Article 6(2). |
| `eu-ai-act-notified-body` | EU AI Act Article 43, Annex VII | Notified-body conformity assessment route for high-risk systems under Article 6(1). |
| `colorado-sb205-safe-harbor` | Colorado SB 205 Section 6-1-1706(3) | Rebuttable presumption of reasonable care via ISO 42001 or NIST AI RMF conformance. |
| `nyc-ll144-annual-audit` | NYC LL144 Final Rule Section 5-301 | Annual bias audit and public disclosure obligation for AEDTs. |
| `singapore-magf-alignment` | Singapore MAGF 2e Pillar Internal Governance | Voluntary alignment demonstration against the four MAGF pillars. |
| `uk-atrs-publication` | UK ATRS Section Tool description | Public-sector publication readiness with Tier 1 fields populated. |

## Per-target required-artifact checklist

### ISO/IEC 42001 Stage 1

| Artifact | Critical | Produced by |
|---|---|---|
| ai-system-inventory | yes | ai-system-inventory-maintainer |
| role-matrix | yes | role-matrix-generator |
| risk-register | yes | risk-register-builder |
| soa | yes | soa-generator |
| audit-log-entry | yes | audit-log-generator |
| aisia | yes | aisia-runner |
| management-review-package | yes | management-review-packager |
| gap-assessment | yes | gap-assessment |
| internal-audit-plan | yes | internal-audit-planner |

### ISO/IEC 42001 Stage 2

Everything Stage 1 requires plus:

| Artifact | Critical | Produced by |
|---|---|---|
| nonconformity-register | yes | nonconformity-tracker |
| metrics-report | yes | metrics-collector |

Plus one target-specific check: `internal-audit-plan.audit_schedule[*].cycle_status == "completed"` for at least one cycle.

### ISO/IEC 42001 surveillance

Stage 2 set, plus evidence of continual improvement: updated risk register, management review conducted after Stage 2 certificate, closed nonconformities.

### EU AI Act internal-control

| Artifact | Critical | Produced by |
|---|---|---|
| aisia (FRIA complete per Art. 27) | yes | aisia-runner |
| risk-register (Art. 9) | yes | risk-register-builder |
| data-register (Art. 10) | yes | data-register-builder |
| audit-log-entry (Art. 12) | yes | audit-log-generator |
| soa (Art. 17) | yes | soa-generator |
| high-risk-classification (not Art. 5 prohibited) | yes | high-risk-classifier |

Plus target-specific check: `high-risk-classification.requires_legal_review == false` or `legal_review_completed == true`.

### EU AI Act notified-body

Internal-control set plus:

| Artifact | Critical | Produced by |
|---|---|---|
| supplier-vendor-assessment (Art. 25) | yes | supplier-vendor-assessor |
| metrics-report (post-market monitoring, Art. 72) | yes | metrics-collector |

### Colorado SB 205 safe-harbor

| Artifact | Critical | Produced by |
|---|---|---|
| high-risk-classification | yes | high-risk-classifier |
| colorado-compliance-record | yes | colorado-ai-act-compliance |
| aisia | yes | aisia-runner |
| soa | no | soa-generator |
| risk-register | no | risk-register-builder |
| audit-log-entry | no | audit-log-generator |

Target-specific check: actor_conformance_frameworks in colorado-compliance-record names `iso42001` or a NIST identifier, OR high-risk-classifier.sb205_assessment.section_6_1_1706_3_applies is `true`. If neither condition holds, the bundle is `not-ready` with blocker `sb205-conformance-missing`.

### NYC LL144 annual audit

| Artifact | Critical | Produced by |
|---|---|---|
| nyc-ll144-audit-package | yes | nyc-ll144-audit-packager |

Target-specific check: `next_audit_due_by` must be at least 30 days out. If less than 30 days, the bundle is `ready-with-conditions` with condition `imminent-reaudit-due`.

### Singapore MAGF alignment

| Artifact | Critical | Produced by |
|---|---|---|
| magf-assessment | yes | singapore-magf-assessor |

### UK ATRS publication

| Artifact | Critical | Produced by |
|---|---|---|
| atrs-record (Tier 1 populated) | yes | uk-atrs-recorder |

Target-specific check: four Tier 1 sections populated: `owner_and_contact`, `tool_description`, `tool_details`, `impact_assessment`.

## Canonical citation expectations

Every target has a minimum citation set that MUST appear in the bundle's citation-summary.md.

| Target | Expected citations |
|---|---|
| `iso42001-stage1` | Clauses 6.1.2, 6.1.3, 9.2, 9.3 |
| `iso42001-stage2` | Clauses 6.1.2, 6.1.3, 9.2, 9.3, 10.2 |
| `iso42001-surveillance` | Clauses 9.2, 9.3, 10.1, 10.2 |
| `eu-ai-act-internal-control` | Articles 9, 10, 12, 17, 27, 43 |
| `eu-ai-act-notified-body` | Articles 9, 10, 12, 17, 25, 27, 43 |
| `colorado-sb205-safe-harbor` | Section 6-1-1706(3) |
| `nyc-ll144-annual-audit` | NYC LL144 |
| `singapore-magf-alignment` | Pillar Internal Governance Structures and Measures |
| `uk-atrs-publication` | Section Tool description |

## Per-gap remediation mapping

The plugin never invents remediation language. Every gap_key maps to a curated string. Unmapped gaps fall back to `"Requires practitioner judgment; escalate to Lead Implementer."`.

| Gap key | Remediation |
|---|---|
| `missing-ai-system-inventory` | Run ai-system-inventory-maintainer. |
| `missing-role-matrix` | Run role-matrix-generator with current RACI. |
| `missing-risk-register` | Run risk-register-builder against inventory and treatment decisions. |
| `missing-soa` | Run soa-generator over Annex A with exclusion justifications. |
| `missing-audit-log-entry` | Run audit-log-generator at the AIMS cadence. |
| `missing-aisia` | Run aisia-runner; complete FRIA for Article 27 systems. |
| `missing-nonconformity-register` | Run nonconformity-tracker with owners and due dates. |
| `missing-management-review-package` | Run management-review-packager over nine Clause 9.3.2 inputs. |
| `missing-internal-audit-plan` | Run internal-audit-planner; schedule one full cycle before Stage 2. |
| `missing-metrics-report` | Run metrics-collector over the reporting period. |
| `missing-gap-assessment` | Run gap-assessment against the target framework. |
| `missing-data-register` | Run data-register-builder for every in-scope dataset. |
| `missing-high-risk-classification` | Run high-risk-classifier per system. |
| `missing-atrs-record` | Run uk-atrs-recorder with Tier 1 fields. |
| `missing-colorado-compliance-record` | Run colorado-ai-act-compliance with actor role declared. |
| `missing-nyc-ll144-audit-package` | Run nyc-ll144-audit-packager with independent auditor. |
| `missing-magf-assessment` | Run singapore-magf-assessor over four pillars. |
| `missing-supplier-vendor-assessment` | Run supplier-vendor-assessor per third-party component. |
| `legal-review-pending` | Complete legal review before technical-documentation submission. |
| `internal-audit-not-completed` | Complete one full internal-audit cycle and close nonconformities. |
| `imminent-reaudit-due` | Schedule the annual re-audit with an independent auditor. |
| `sb205-conformance-missing` | Declare ISO 42001 or NIST AI RMF conformance in colorado-compliance-record. |
| `atrs-tier1-incomplete` | Populate all four Tier 1 sections. |
| `missing-citation` | Add the canonical citation to the originating artifact and rerun. |
| `warning-on-critical-control` | Clear the warning in the originating artifact and rerun. |

## Readiness-level decision table

| Precondition | Readiness |
|---|---|
| MANIFEST.json absent | `not-ready` |
| Any critical required artifact absent | `not-ready` |
| Target-specific blocker triggered | `not-ready` |
| Critical artifact present, strength below minimum, strict_mode=True | `not-ready` |
| Non-critical required artifact absent | `partially-ready` |
| Target-specific gap triggered | `partially-ready` |
| Critical artifact with warnings, strict_mode=False | `ready-with-conditions` |
| Everything satisfied | `ready-with-high-confidence` |
