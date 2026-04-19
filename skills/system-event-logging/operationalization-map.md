# System-event-logging operationalization map

Per-framework mapping from authoritative-source text to `system-event-logger` plugin input and output fields, plus the relationship to sibling plugins in the AIGovOps catalogue.

## Scope

This map covers EU AI Act Articles 12 and 19, Article 26 Paragraph 6 (deployer log duty), ISO/IEC 42001:2023 Annex A Control A.6.2.8 and Clause 7.5.3, and NIST AI RMF MEASURE 2.8. It records the distinction between this skill (system-operational events) and `audit-log-generator` (governance events).

## EU AI Act Article 12

| Sub-paragraph | Authoritative text (summary) | Plugin field | Plugin logic |
|---|---|---|---|
| 12(1) | Technical capability to record events automatically over the lifetime of the system. | `event_schema_normalized`; `art_12_applicability.status` | High-risk EU systems emit `status=mandatory`; others emit `recommended-not-mandated`. |
| 12(2)(a) | Traceability for identifying situations that may result in risk per Article 79(1). | `traceability_coverage.per_purpose[purpose=a]` | Warns if no event category maps to purpose (a). |
| 12(2)(b) | Traceability for facilitating post-market monitoring per Article 72. | `traceability_coverage.per_purpose[purpose=b]` | Warns if no event category maps to purpose (b). |
| 12(2)(c) | Traceability for monitoring operation per Article 26(5). | `traceability_coverage.per_purpose[purpose=c]` | Warns if no event category maps to purpose (c). |
| 12(3) | Remote biometric identification systems must log start/end date/time, reference database, input data, verification results, operating person identity. | `biometric_art_12_3_check` | Emitted only when `remote_biometric_id=True`. Six-field presence check; blocking warning per missing field. |

## EU AI Act Article 19

| Sub-paragraph | Authoritative text (summary) | Plugin field | Plugin logic |
|---|---|---|---|
| 19(1) | Providers (or deployers using modified systems) shall keep logs for at least six months, unless Union or national law requires longer. | `retention_policy_assessment.eu_art_19_floor_satisfied` | Requires `retention_policy.minimum_days >= 183` for EU high-risk systems. Below emits blocking warning. `policy_name="none"` emits blocking warning. |
| 19(2) | Financial-services retention periods in sectoral law override. | `retention_policy_assessment.citations` | `policy_name=sectoral-finance` adds `EU AI Act, Article 19, Paragraph 2` citation. Empty `legal_basis_citation` on sectoral policies emits a warning. |

## EU AI Act Article 26, Paragraph 6

Deployer duty to keep automatically generated logs for at least six months. Drives the tamper-evidence expectation: logs held for statutory retention must be tamper-evident to retain evidentiary value.

| Plugin field | Plugin logic |
|---|---|
| `tamper_evidence_assessment.tamper_evidence_present` | Warns when `log_storage.tamper_evidence_method` is absent or empty. |
| `tamper_evidence_assessment.citations` | Always emits `EU AI Act, Article 26, Paragraph 6` and `ISO/IEC 42001:2023, Annex A, Control A.6.2.8`. |

## ISO/IEC 42001:2023 Annex A Control A.6.2.8

AI system recording of event logs. The control requires the organization to design AI systems to record events enabling identification of situations of concern.

| Requirement | Plugin field | Plugin logic |
|---|---|---|
| Event recording design | `event_schema_normalized` | Per-field rows derived from input `event_schema`. |
| Traceability coverage | `traceability_coverage` | Per Article 12(2) purpose mapping. ISO does not enumerate the three purposes; alignment is via the EU mapping. |
| Retention discipline | `retention_policy_assessment` | ISO Clause 7.5.3 applies to the plan; Article 19 sets the minimum floor. |

## NIST AI RMF MEASURE 2.8

Risks associated with transparency and accountability. The event-log schema and retention policy together satisfy the MEASURE 2.8 accountability posture.

| Subcategory | Plugin field |
|---|---|
| MEASURE 2.8 | Top-level `citations`; `cross_framework_citations` when enriched. |

## Relationship to sibling plugins

### audit-log-generator (DIFFERENT event layer)

- `audit-log-generator` records governance events: management decisions, authority exercises, review minutes. ISO/IEC 42001:2023 Clause 9.1 and Annex A Control A.6.2.3.
- `system-event-logger` records system-operational events: inference, drift, safety, biometric verification. EU AI Act Article 12 and ISO Annex A Control A.6.2.8.
- The two layers are complementary, not redundant. An evidence bundle for a high-risk EU system contains BOTH.

### evidence-bundle-packager (logs in bundle)

The schema artifact produced by `system-event-logger` is bundled with the runtime log archive by `evidence-bundle-packager`. The schema is the contract the archive must satisfy. The bundle optionally HMAC-signs both the schema and the archive digests per the tamper-evidence posture declared here.

### post-market-monitoring (monitoring plan references event logs)

`post-market-monitoring` names the dimensions monitored, the cadence, and the threshold rules. `system-event-logger` specifies the event categories and fields the monitoring plan's `data_collection.method=logs` entries consume. A drift-signal threshold breach flows from the log stream, through the monitoring plan, to the `nonconformity-tracker` or `incident-reporting` escalation path.

### incident-reporting (log-driven statutory notification)

A safety-event logged per this schema can trigger EU AI Act Article 73, Colorado SB 205 Section 6-1-1702(7), or NYC LL144 candidate-complaint notification. The schema here carries the field structure the incident report consumes.

## Per-category to Article 12(2) purpose routing

| Event category | Typical Article 12(2) purpose |
|---|---|
| `inference-request`, `inference-output` | (c) monitoring operation |
| `risk-signal`, `drift-signal` | (a) identifying risk situations; (b) facilitating post-market monitoring |
| `safety-event` | (a) identifying risk situations |
| `override-action` | (c) monitoring operation |
| `consumer-complaint` | (a) identifying risk situations |
| `auth-event` | (c) monitoring operation |
| `config-change`, `model-update` | (b) facilitating post-market monitoring |
| `data-access` | (c) monitoring operation |
| `biometric-verification` | (a) identifying risk situations (plus Article 12(3) field-list duty) |

Practitioners override the defaults by supplying the mapping explicitly in `traceability_mappings`.
