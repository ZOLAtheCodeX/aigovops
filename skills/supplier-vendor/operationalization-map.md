# supplier-vendor Operationalization Map

Working document for the `supplier-vendor` skill. Maps every in-scope sub-clause to an operationalizability class, the plugin output block that realizes it, and the relationship to sibling plugins. Not a SKILL.md; does not follow SKILL.md section headers.

**Validation status.** Authored 2026-04-18. Clause references confirmed against ISO/IEC 42001:2023 Annex A; EU AI Act references confirmed against Regulation (EU) 2024/1689; NYC LL144 references confirmed against 6 RCNY Subchapter T, Section 5-300.

## Methodology

Same operationalizability classes as the `iso42001` skill: Automatable (A), Hybrid (H), Human judgment required (J).

## ISO/IEC 42001:2023, Annex A.10

| Sub-clause | Title | Class | Plugin output block | Notes |
|---|---|---|---|---|
| A.10.2 | Allocating responsibilities | H | `role_reconciliation` | Requires organization_role and vendor_role inputs. Allocation is an organizational decision; plugin records and cross-references. |
| A.10.3 | Suppliers | H | `assessment_matrix`, `warnings` | Mechanical status inference from `contract_summary`. Flags absent audit rights, absent DPA, excessive incident-notification windows. |
| A.10.4 | Customers | J | `role_reconciliation.notes` | The organization's commitments to its customers about AI systems are policy-authored. Plugin surfaces the obligation; does not draft commitments. |

## EU AI Act, Articles 25 and 26

| Provision | Title | Class | Plugin output block | Notes |
|---|---|---|---|---|
| Art. 25(1) | Value-chain responsibility allocation | H | `role_reconciliation.citations` | Art. 25(1)(c) substantial-modification re-classification surfaced as a warning when `deployer_modification_note` is provided. |
| Art. 25(3)(c) | Distributor conformity verification | H | `role_reconciliation.notes` | Triggered when organization_role is distributor and vendor_role is model-provider. |
| Art. 25(4) | Downstream-integrator cooperation duties | H | `role_reconciliation.notes` | Triggered when organization_role is downstream-integrator and vendor_role is model-provider. |
| Art. 26(1)(a) | Importer pre-market checks | H | `role_reconciliation.notes` | Triggered when organization_role is importer. |

## NYC Local Law 144 Final Rule

| Provision | Title | Class | Plugin output block | Notes |
|---|---|---|---|---|
| Section 5-300 | Independent auditor definition and criteria | H | `independence_assessment` | Plugin surfaces four criteria for practitioner confirmation. Status is always `requires-practitioner-confirmation` at plugin output. |

## NIST AI RMF 1.0

| Subcategory | Title | Class | Plugin output block |
|---|---|---|---|
| GOVERN 6.1 | Policies for third-party AI risk | H | top-level `citations` |
| GOVERN 6.2 | Contingency for third-party failure | H | `assessment_matrix.financial-stability` warning |

## Assessment-dimension matrix

Eight canonical dimensions. Status values are drawn from the fixed vocabulary `addressed`, `partial`, `not-addressed`, `requires-practitioner-assessment`.

| Dimension | Inference source | Mechanical? |
|---|---|---|
| technical-capability | practitioner | no |
| security-posture | practitioner | no |
| data-governance | `contract_summary.data_processing_agreement_included` | yes |
| contractual-obligations | `contract_summary.audit_rights_included` | yes |
| regulatory-alignment | practitioner | no |
| incident-response | `contract_summary.security_incident_notification_days` (threshold 15) | yes |
| financial-stability | practitioner | no |
| independence-and-impartiality | practitioner (plus independence block) | no |

## Relationship to sibling plugins

- **`role-matrix-generator`**: A.10.2 requires a named approver for supplier onboarding. The supplier-vendor assessment feeds the role matrix row for that decision. The role matrix in turn supplies the authority basis for approving supplier contracts.
- **`audit-log-generator`**: vendor-onboarding and vendor-offboarding are governance events under ISO A.10. Each supplier-vendor assessment is an audit-log candidate.
- **`ai-system-inventory-maintainer`**: the vendor's `ai_systems_they_supply` list cross-references the inventory's system IDs. Inventory cross-check belongs there, not here.
- **`nyc-ll144-audit-packager`**: consumes the `independence_assessment` block and attaches the practitioner-confirmed determination to the bias-audit public disclosure.
- **`crosswalk-matrix-builder`**: provides cross-framework citation enrichment for A.10.* and Article 25 mappings (3 new mappings added in the `iso42001-eu-ai-act.yaml` data file).
- **`risk-register-builder`**: third-party-risk entries reference the vendor assessment via the vendor_name or contract_id.

## Priority-ranked backlog

1. Basic assessment record for model-provider and bias-audit-service vendors. DONE in 0.1.0.
2. Tiered supply-chain mapping. DONE in 0.1.0 (structural; tier-2 nested assessment marked pending).
3. Cross-framework crosswalk enrichment for A.10 and Article 25. DONE in 0.1.0.
4. GPAI-model-provider cooperation obligations (Art. 25(4)) surfaced as structured downstream-integrator checks.
5. Customer-facing A.10.4 commitments template (Hybrid; practitioner draft scaffold) in 0.2.0.
6. Contract-effective-date to system go-live cross-check via `ai-system-inventory-maintainer` in a later release.
