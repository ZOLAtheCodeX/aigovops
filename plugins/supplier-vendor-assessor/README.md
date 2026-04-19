# supplier-vendor-assessor

Operationalizes ISO/IEC 42001:2023 Annex A category A.10 (Allocation of responsibilities, Suppliers, Customers), EU AI Act Article 25 (Responsibilities along the AI value chain), and NYC LL144 Final Rule Section 5-300 auditor-independence requirements. Produces a formal supplier-risk record structured for audit evidence.

## Output artifact

Supplier-vendor assessment record with role reconciliation, per-dimension assessment matrix, optional independence-assessment block, optional supply-chain graph, and cross-framework citation enrichment. Emitted as JSON, Markdown, and CSV.

## Scope

- ISO/IEC 42001:2023, Annex A, Controls A.10.2, A.10.3, A.10.4.
- EU AI Act, Article 25 (value-chain responsibilities) and Article 26(a) (importer check obligations).
- NYC LL144 Final Rule, Section 5-300 (auditor-independence criteria).
- NIST GOVERN 6.1 (third-party risk policies) and GOVERN 6.2 (third-party contingency planning).

## Public API

- `assess_vendor(inputs: dict) -> dict`: canonical entry point.
- `render_markdown(assessment: dict) -> str`
- `render_csv(assessment: dict) -> str`

## Inputs

| Field | Required | Type | Notes |
|---|---|---|---|
| `vendor_description` | yes | dict | Must include `vendor_name`. Recommended: `vendor_type`, `jurisdiction_of_establishment`, `products_services`, `ai_systems_they_supply`. |
| `vendor_role` | yes | enum | One of `model-provider`, `training-data-provider`, `mlops-platform`, `deployment-infrastructure`, `evaluation-service`, `bias-audit-service`, `red-team-service`, `content-moderation-service`, `monitoring-service`, `adjudicator-human-in-loop`. |
| `organization_role` | yes | enum | EU AI Act vocabulary: `provider`, `deployer`, `distributor`, `importer`, `authorized-representative`, `downstream-integrator`. |
| `contract_summary` | no | dict | Fields include `contract_id`, `effective_date`, `expiry_date`, `auto_renew`, `termination_notice_days`, `sla_summary`, `audit_rights_included`, `security_incident_notification_days`, `data_processing_agreement_included`, `liability_cap`. |
| `assessment_dimensions` | no | list | Subset of the eight canonical dimensions. Defaults to all eight. |
| `independence_check_required` | no | bool | Defaults True for `bias-audit-service`, `red-team-service`, `evaluation-service`; False otherwise. |
| `deployer_modification_note` | no | string | If provided with `organization_role=deployer`, triggers EU AI Act Art. 25(1)(c) re-classification warning. |
| `sub_processors` | no | list[dict] | Tiered supply chain. Each entry follows the `vendor_description` schema. |
| `enrich_with_crosswalk` | no | bool | Default True. Attaches `cross_framework_citations` list. |
| `reviewed_by` | no | string | Reviewer identity for the assessment. |

## Assessment dimensions

| Dimension | Mechanical status inference from `contract_summary` |
|---|---|
| `contractual-obligations` | `audit_rights_included=True` -> addressed; False -> partial with warning; absent -> not-addressed. |
| `data-governance` | `data_processing_agreement_included=True` -> addressed; False -> not-addressed; absent -> requires-practitioner-assessment. |
| `incident-response` | `security_incident_notification_days <= 15` -> addressed; higher -> partial with warning; absent -> not-addressed. |
| `technical-capability` | requires-practitioner-assessment. |
| `security-posture` | requires-practitioner-assessment. |
| `regulatory-alignment` | requires-practitioner-assessment. |
| `financial-stability` | requires-practitioner-assessment (NIST GOVERN 6.2 contingency). |
| `independence-and-impartiality` | requires-practitioner-assessment (see independence block). |

## Rule tables

**Role reconciliation.**

| Organization role | Vendor role | Trigger condition | Effect |
|---|---|---|---|
| deployer | any | `deployer_modification_note` is non-empty | Warning: Art. 25(1)(c) re-classification check; cite Art. 25(1). |
| distributor | model-provider | always | Note: Art. 25(3)(c) distributor obligations apply. |
| importer | any | always | Note: Art. 26(a) pre-market check obligations apply. |
| downstream-integrator | model-provider | always | Note: Art. 25(4) cooperation duties apply. |

**Independence check.** Emits an `independence_assessment` dict with the four NYC LL144 criteria when the vendor role is `bias-audit-service`, `red-team-service`, or `evaluation-service`, or when the caller sets `independence_check_required=True`. The plugin does NOT make the determination; it surfaces the criteria for practitioner confirmation. Status is always `requires-practitioner-confirmation` at plugin output.

## Example

```python
from plugins.supplier_vendor_assessor import plugin

result = plugin.assess_vendor({
    "vendor_description": {
        "vendor_name": "Acme Foundation Models Inc.",
        "vendor_type": "model-provider",
        "jurisdiction_of_establishment": "US-DE",
        "products_services": ["foundation-model-api"],
        "ai_systems_they_supply": ["SYS-001"],
    },
    "vendor_role": "model-provider",
    "organization_role": "downstream-integrator",
    "contract_summary": {
        "contract_id": "MSA-2026-001",
        "audit_rights_included": True,
        "security_incident_notification_days": 10,
        "data_processing_agreement_included": True,
    },
})
print(plugin.render_markdown(result))
```

## Outputs

| Key | Always present | Notes |
|---|---|---|
| `timestamp`, `agent_signature`, `framework` | yes | Artifact header. |
| `vendor_description_echo` | yes | Defensive copy of key vendor fields. |
| `role_reconciliation` | yes | Organization-role, vendor-role, reconciliation notes. |
| `assessment_matrix` | yes | One entry per dimension assessed. |
| `independence_assessment` | conditional | Present when `independence_check_required`. |
| `supply_chain_graph` | conditional | Present when `sub_processors` non-empty. |
| `cross_framework_citations` | conditional | Present when `enrich_with_crosswalk=True`. |
| `citations` | yes | A.10.2, A.10.3, A.10.4, NIST GOVERN 6.1, GOVERN 6.2 baseline; Art. 25/26 and NYC 5-300 when triggered. |
| `warnings` | yes | Register-level and per-dimension warnings flattened. |
| `summary` | yes | Dimension counts and flags. |

## Anti-hallucination

The plugin does not rate vendors, compute risk levels, or invent independence determinations. Every status either comes from inputs or is `requires-practitioner-assessment`. Every citation is emitted verbatim in the STYLE.md-approved format.

## Related

- `role-matrix-generator`: suppliers appear in the role matrix for certain decisions per A.10.2.
- `audit-log-generator`: vendor-onboarding and vendor-offboarding are governance events.
- `nyc-ll144-audit-packager`: consumes the independence assertion for public disclosure.
- `crosswalk-matrix-builder`: provides cross-framework citation enrichment.
