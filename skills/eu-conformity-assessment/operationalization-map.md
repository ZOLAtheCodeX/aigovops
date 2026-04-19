# EU Conformity Assessment Operationalization Map

Working document for the `eu-conformity-assessment` skill. Maps each EU AI Act provision the skill covers to: the specific input field that supplies the evidence, the output block that surfaces the determination, the warning condition, and the producing AIGovOps plugin.

## Relationship to certification-readiness

The two skills have different consumers and different purposes.

| | certification-readiness | eu-conformity-assessment |
|---|---|---|
| Scope | Nine target certifications across five jurisdictions | EU AI Act conformity only |
| Output | Graduated readiness verdict (ready / partial / not-ready) | Per-Article structured assessment with declaration of conformity draft |
| Consumer | Auditor or compliance program manager preparing for an audit | Provider preparing to place an EU high-risk system on the market |
| Output artifacts | Readiness report (markdown + csv) | Procedure assessment + declaration of conformity template + CE marking record + registration record |
| Decision moment | Pre-audit gating | Pre-market placement |

A typical EU high-risk lifecycle uses both. The provider runs `certification-readiness` with `target_certification=eu-ai-act-internal-control` to verify the bundle is complete enough to attempt conformity, then runs `eu-conformity-assessment` to produce the regulatory artifacts the EU AI Act prescribes (declaration of conformity, CE marking record, EU database registration record).

## Per-Article mapping

### Article 43 (Conformity assessment procedures)

| Paragraph | Trigger | Skill output | Warning condition | Source plugin |
|---|---|---|---|---|
| 1 | Annex III Point 1 (biometrics) | `procedure_applicability.required_procedure` | Procedure misalignment for biometric system | high-risk-classifier |
| 2 | Annex III Points 2 to 8 | `procedure_applicability.required_procedure = annex-vi-internal-control` | Voluntary annex-vii without justification | high-risk-classifier |
| 3 | Annex I harmonised legislation product | `procedure_applicability.required_procedure = annex-i-harmonised-legislation` | Procedure mismatch | high-risk-classifier |
| 4 | Substantial modification | `surveillance_check.status = surveillance-mode` | None (informational) | input field `previous_assessment_ref` |

### Article 17 (Quality management system)

| Paragraph and Point | Skill output | Warning condition | Source plugin |
|---|---|---|---|
| 1, Point (a) | `qms_attestation` | `management-review-package` artifact missing from bundle | management-review-packager |
| 1, Point (i) | `qms_attestation` | `internal-audit-plan` artifact missing from bundle | internal-audit-planner |

### Article 22 (Authorised representative)

| Paragraph | Trigger | Skill output | Warning condition |
|---|---|---|---|
| 1 | `provider_identity.country` not in EU member states | embedded in `warnings` | `authorised_representative` field empty |

### Article 47 (EU declaration of conformity)

| Paragraph | Skill output field | Warning condition |
|---|---|---|
| 1 | `declaration_of_conformity_draft.provider_legal_name`, `provider_address`, `system_id`, `intended_use`, `procedure_applied`, `harmonised_standards_applied`, `notified_body_certificate_ref` | Any required field empty |
| 2 | `declaration_of_conformity_draft.signatory` | Signatory not supplied; provider must complete and sign |

### Article 48 (CE marking)

| Paragraph | Skill output | Warning condition |
|---|---|---|
| 1 | `ce_marking_check.location` | High-risk EU system without `ce_marking_location` specified |
| 2 | `ce_marking_check.location` (one of `system`, `packaging`, `documentation`) | None (informational) |
| 3 | `ce_marking_check.notified_body_id_present` | annex-vii procedure but no notified-body `body_id` |

### Article 49 (Registration in EU database)

| Paragraph | Trigger | Skill output | Warning condition |
|---|---|---|---|
| 1 | High-risk system not in Annex III Point 2 | `registration_check.status` | Empty `registration_status` input |
| 2 | Annex III Point 6 (law enforcement) | `registration_check.public_or_restricted = restricted` | None (informational) |

### Annex IV (Technical documentation)

The nine Annex IV documentation categories map to AIGovOps plugin outputs as follows.

| Category | Annex IV reference | Producing plugin | Manifest artifact_type accepted as evidence |
|---|---|---|---|
| general-description | Annex IV, Point 1 | ai-system-inventory-maintainer | `ai-system-inventory` |
| design-documentation | Annex IV, Point 2 | ai-system-inventory-maintainer | `ai-system-inventory`, `high-risk-classification` |
| development-process | Annex IV, Point 2 | audit-log-generator | `audit-log-entry` |
| monitoring-control | Annex IV, Point 3 | post-market-monitoring | `metrics-report` |
| detailed-testing | Annex IV, Point 6 | robustness-evaluator | `metrics-report` |
| risk-management | Annex IV, Point 5 | risk-register-builder | `risk-register`, `aisia` |
| change-log | Annex IV, Point 2 | audit-log-generator | `audit-log-entry` |
| instructions-for-use | Annex IV, Point 4 | ai-system-inventory-maintainer | `ai-system-inventory` |
| references-to-harmonised-standards | Annex IV, Point 7 | soa-generator | `soa` |

### Annex VI (Internal control)

| Annex VI element | Skill output | Source artifact |
|---|---|---|
| Technical documentation per Annex IV | `annex_iv_completeness` (nine rows) | Bundle artifact types |
| QMS per Article 17 | `qms_attestation` | `management-review-package`, `internal-audit-plan` |
| Examination of the system | Provider responsibility (not automated) | Provider attestation |
| EU declaration of conformity | `declaration_of_conformity_draft` | `provider_identity` + `system_description` + `harmonised_standards_applied` |

### Annex VII (Notified body)

| Annex VII element | Skill output | Warning condition |
|---|---|---|
| QMS review by notified body | `qms_attestation` (provider self-check before submission) | Missing artifacts |
| Technical documentation review | `annex_iv_completeness` (provider self-check before submission) | Missing categories |
| Type-examination certificate | `notified_body_check.certificate_ref` | Empty `notified_body` input or missing `certificate_ref` |
| Notified body identification | `notified_body_check.body_id` and `ce_marking_check.notified_body_id_present` | Missing `body_id` |

## ISO/IEC 42001:2023 cross-reference

The crosswalk-matrix-builder data file `iso42001-eu-ai-act.yaml` carries the canonical mappings consumed when `enrich_with_crosswalk=True`.

| EU AI Act provision | ISO/IEC 42001:2023 reference | Relationship | Confidence |
|---|---|---|---|
| Annex IV (Technical documentation) | Clause 7.5, Annex A Control A.6.2.7 | satisfies | high |
| Annex VI (Internal control) | Clause 9.2 + Clause 9.3 | partial-satisfaction | high |
| Article 17 QMS | Clause 9.2, Clause 9.3 | satisfies | high |
| Article 47 (Declaration of conformity) | (no ISO equivalent) | no-mapping | high |
| Article 48 (CE marking) | (no ISO equivalent) | no-mapping | high |
| Article 49 (EU database registration) | (no ISO equivalent) | no-mapping | high |
| Annex VII (Notified body) | (no ISO equivalent) | no-mapping | high |

ISO 42001 is a management-system standard. The product-conformity artefacts (declaration of conformity, CE marking, EU database registration) have no ISO management-system counterpart and remain regulator-side obligations.

## Decision tree for procedure selection

```
                        +-------------------------------+
                        | annex_i_legislation populated?|
                        +-------------------------------+
                          | yes              | no
                          v                  v
                annex-i-harmonised   +----------------------------+
                  -legislation       | annex_iii_category == 1?   |
                                     +----------------------------+
                                       | yes              | no
                                       v                  v
                              +------------------+   annex-vi-internal
                              | biometric        |   -control (default)
                              | harmonised       |
                              | standard cited?  |
                              +------------------+
                                | yes      | no
                                v          v
                       annex-vi-     annex-vii-notified
                       internal-     -body (required)
                       control
                       (permitted)
```

The plugin's `_assess_procedure_applicability` helper implements this tree deterministically and emits a warning when `procedure_requested` does not match the required procedure.

## Anti-hallucination invariants

1. The plugin never issues a conformity certificate. Notified-body certificates are referenced only when supplied as input.
2. The plugin never signs the declaration of conformity. The signatory field is populated for the provider's review; the provider signs.
3. The plugin never affixes the CE marking. It checks that the location is specified and that the notified-body identification is present when required.
4. The plugin never submits the registration record to the EU database. It checks that the registration status is captured.
5. Every determination cites a specific EU AI Act Article and Paragraph. Citations follow STYLE.md format exactly.
