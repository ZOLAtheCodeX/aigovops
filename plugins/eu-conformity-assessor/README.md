# eu-conformity-assessor

EU AI Act conformity assessment plugin. Operationalizes Article 43 (procedure selection), Annex VI (internal control), Annex VII (notified body), Article 47 (EU declaration of conformity), Article 48 (CE marking), and Article 49 (EU database registration).

The plugin is the procedure and declaration layer on top of an evidence bundle produced by `evidence-bundle-packager`. It does NOT issue conformity certificates, sign declarations of conformity, or affix CE markings. It structures the procedure for the provider, verifies the Annex IV technical documentation content set against the bundle, emits a TEMPLATE declaration of conformity for the provider to complete and sign, and flags every gap as a warning with a specific Article or Annex citation.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | `system_id`, `risk_tier`, `intended_use`, `sector`, `annex_iii_category` (enum from `VALID_ANNEX_III_POINTS` when applicable), `annex_i_legislation` (list when applicable), `ce_marking_required` (bool). |
| `provider_identity` | dict | yes | `legal_name`, `address`, `country` (ISO-2), `authorised_representative` (dict, required for non-EU providers per Article 22), `contact`. |
| `procedure_requested` | enum | yes | One of `annex-vi-internal-control`, `annex-vii-notified-body`, `annex-i-harmonised-legislation`, `none-exempt`. |
| `evidence_bundle_ref` | string (path) | no | Path to the evidence bundle for Annex IV completeness verification. |
| `notified_body` | dict | conditional | Required when `procedure_requested=annex-vii-notified-body`. `body_id`, `name`, `certificate_ref`. |
| `harmonised_standards_applied` | list | no | ISO/IEC or EN standards cited (drives biometric Article 43(1) exception). |
| `ce_marking_location` | enum | no | One of `system`, `packaging`, `documentation`. |
| `registration_status` | dict | no | `eu_database_entry_id`, `registration_date`, `public_or_restricted`. |
| `previous_assessment_ref` | string | no | For surveillance / re-assessment per Article 43(4). |
| `enrich_with_crosswalk` | bool | no | Default True. Adds `cross_framework_citations` to ISO 42001. |
| `reviewed_by` | string | no | Reviewer name; populates declaration `signatory` field when present. |

## Outputs

The canonical entry point `assess_conformity_procedure(inputs)` returns a dict with:

- `timestamp`, `agent_signature`, `framework` (fixed: `eu-ai-act`), `system_description_echo`.
- `procedure_selected`, `procedure_applicability` (Article 43 alignment check).
- `annex_iv_completeness`: list of nine per-category rows (`category`, `status`, `accepted_artifact_types`, `recommended_producing_plugin`, `citation`).
- `qms_attestation`: Article 17 management-review and internal-audit presence check.
- `notified_body_check`: present when `procedure_requested=annex-vii-notified-body`.
- `declaration_of_conformity_draft`: Article 47 template populated from inputs. Provider must sign.
- `ce_marking_check`: Article 48 location and notified-body identification verification.
- `registration_check`: Article 49 EU database registration status and visibility (public or restricted).
- `surveillance_check`: present when `previous_assessment_ref` supplied.
- `citations`, `warnings`, `summary`, `cross_framework_citations` (when enriched), `reviewed_by`.

## Public API

- `assess_conformity_procedure(inputs) -> dict`
- `render_markdown(assessment) -> str`
- `render_csv(assessment) -> str`

CSV emits one row per Annex IV category. Markdown carries every section header listed under Outputs above plus a legal disclaimer callout near the top.

## Rule tables

### Procedure selection (Article 43)

| Annex III category | Standards applied | Required procedure | Citation |
|---|---|---|---|
| 1-biometrics | none | `annex-vii-notified-body` | Article 43, Paragraph 1 |
| 1-biometrics | biometric harmonised standard | `annex-vi-internal-control` permitted | Article 43, Paragraph 1 |
| 2 to 8 | n/a | `annex-vi-internal-control` (default) | Article 43, Paragraph 2 |
| `annex_i_legislation` populated | n/a | `annex-i-harmonised-legislation` | Article 43, Paragraph 3 |

### Annex IV documentation categories

| Category | Producing plugin | Citation |
|---|---|---|
| general-description | ai-system-inventory-maintainer | Annex IV, Point 1 |
| design-documentation | ai-system-inventory-maintainer | Annex IV, Point 2 |
| development-process | audit-log-generator | Annex IV, Point 2 |
| monitoring-control | post-market-monitoring | Annex IV, Point 3 |
| detailed-testing | robustness-evaluator | Annex IV, Point 6 |
| risk-management | risk-register-builder | Annex IV, Point 5 |
| change-log | audit-log-generator | Annex IV, Point 2 |
| instructions-for-use | ai-system-inventory-maintainer | Annex IV, Point 4 |
| references-to-harmonised-standards | soa-generator | Annex IV, Point 7 |

### Registration (Article 49)

| Annex III category | Registration required | Visibility |
|---|---|---|
| 2-critical-infrastructure | no (exempt) | n/a |
| 6-law-enforcement | yes | restricted |
| All other categories | yes | public |

## Example

```python
from plugins.eu_conformity_assessor import plugin

assessment = plugin.assess_conformity_procedure({
    "system_description": {
        "system_id": "AISYS-001",
        "risk_tier": "high-risk",
        "intended_use": "Resume screening for EU job applicants",
        "sector": "employment",
        "annex_iii_category": "4-employment",
        "ce_marking_required": True,
    },
    "provider_identity": {
        "legal_name": "Acme Healthcare AI BV",
        "address": "Keizersgracht 1, 1015 CJ Amsterdam, Netherlands",
        "country": "NL",
        "contact": "compliance@acme.eu",
    },
    "procedure_requested": "annex-vi-internal-control",
    "evidence_bundle_ref": "/tmp/aigovops-bundles/aigovops-bundle-2026-04-18T12:00:00Z-abc123",
    "ce_marking_location": "system",
    "registration_status": {
        "eu_database_entry_id": "EU-DB-12345",
        "registration_date": "2026-04-01",
        "public_or_restricted": "public",
    },
    "reviewed_by": "Zola Valashiya",
})
print(plugin.render_markdown(assessment))
```

## Related

- `evidence-bundle-packager`: produces the bundle this plugin reads for Annex IV completeness.
- `certification-readiness`: parallel consumer plugin. Cert-readiness is general (nine certifications); this plugin is EU-specific (procedure + declaration + CE + registration).
- `high-risk-classifier`: produces the Annex III classification this plugin echoes.
- `crosswalk-matrix-builder`: source of the cross-framework citations enrichment.
