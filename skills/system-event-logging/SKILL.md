---
name: system-event-logging
version: 0.1.0
description: >
  System-operational event log schema, retention policy, and traceability
  structure for EU AI Act Article 12 (automatic recording of events over the
  lifetime of a high-risk AI system), Article 19 (log retention minimum 6
  months), ISO/IEC 42001:2023 Annex A Control A.6.2.8 (AI system recording of
  event logs), and NIST AI RMF MEASURE 2.8 (transparency and accountability).
  Distinct from the governance-event layer served by audit-log-generator.
frameworks:
  - EU AI Act (Regulation (EU) 2024/1689)
  - ISO/IEC 42001:2023
  - NIST AI RMF 1.0
tags:
  - ai-governance
  - system-event-logging
  - eu-ai-act
  - article-12
  - article-19
  - iso42001
  - annex-a-6-2-8
  - measure-2-8
  - retention
  - traceability
  - biometric
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the SYSTEM-OPERATIONAL event log as a single artifact that simultaneously satisfies EU AI Act Article 12 (automatic recording of events), Article 19 (log retention minimum 6 months), ISO/IEC 42001:2023 Annex A Control A.6.2.8 (AI system recording of event logs), and NIST AI RMF MEASURE 2.8 (transparency and accountability).

The artifact is DISTINCT from the governance-event artifact served by `audit-log-generator`:

- `audit-log-generator` records GOVERNANCE EVENTS: management decisions, review minutes, authority exercises, role assignments. It serves ISO/IEC 42001:2023 Clause 9.1 and Annex A Control A.6.2.3 evidence needs.
- `system-event-logging` specifies the SYSTEM-OPERATIONAL event log: inference requests, inference outputs, risk signals, drift signals, safety events, override actions, consumer complaints, auth events, config changes, model updates, data accesses, and biometric verifications. This is the log layer Article 12 has in mind.

The plugin SPECIFIES the schema, retention, and tamper-evidence plan. It does NOT emit runtime log entries, and it does NOT verify that log files exist on disk. Runtime logging is the MLOps pipeline's responsibility.

## Scope

**In scope.** Schema definition, retention policy, traceability structure, and tamper-evidence posture for the system-operational event log:

- Event category inventory and per-category field specification (Article 12(3) imposes a specific six-field list for remote biometric identification).
- Retention policy bound to Article 19 minimum (183 days) and sectoral overlays (finance, healthcare).
- Traceability mappings from event categories to Article 12(2)(a), (b), (c) purposes.
- Tamper-evidence method declaration for Article 26(6) deployer log-keeping duty.
- Schema version diff when a predecessor reference is supplied.
- Cross-framework crosswalk to ISO/IEC 42001:2023 Annex A Control A.6.2.8 and NIST AI RMF MEASURE 2.8.

**Out of scope.**

- Runtime log generation. That is an MLOps concern; this skill supplies the structure the pipeline populates.
- Log analytics, drift detection algorithms, threshold evaluation. `post-market-monitoring` defines the monitoring plan that consumes the log stream.
- Governance-event records. `audit-log-generator` handles those.
- Statutory incident reporting. `incident-reporting` emits Article 73 notifications when a logged safety event triggers a deadline.
- Evidence packaging. `evidence-bundle-packager` bundles the schema artifact with sibling artifacts and optionally HMAC-signs it.

**Operating assumption.** The organization has an AI system inventory, at least one assigned log-custodian role, and a storage substrate that supports tamper-evident append. The Article 12 duty cannot be operationalized without those.

## Framework Reference

**Authoritative sources.**

- EU AI Act (Regulation (EU) 2024/1689), Article 12 (Record-keeping), Article 19 (Automatically generated logs), Article 26, Paragraph 6 (Deployer obligations to keep logs), Article 79, Paragraph 1 (referenced by Article 12(2)(a)).
- ISO/IEC 42001:2023, Annex A, Control A.6.2.8 (AI system recording of event logs), Clause 7.5.3 (Control of documented information).
- NIST AI RMF 1.0, MEASURE 2.8 (risks associated with transparency and accountability).

**Relationship to other frameworks.**

- ISO A.6.2.8 satisfies Article 12(1) automatic-logging duty. Confidence: high.
- ISO A.6.2.8 combined with Clause 9.1 satisfies Article 12(2) traceability proportional to purpose. Confidence: high.
- ISO A.6.2.8 partially satisfies Article 12(3) biometric-verification field list (ISO does not enumerate the six biometric fields). Confidence: medium.
- Article 19(1) six-month floor is NOT satisfied by ISO 42001 alone; Clause 7.5.3 retention discipline is necessary but insufficient. Confidence: high.
- NIST MEASURE 2.8 is satisfied by the event-log schema and retention policy. Confidence: high.

## Operationalizable Controls

Two-tier operationalization. Tier 1 (Automatable) covers schema-specification outputs computable from structured input. Tier 2 (Hybrid) covers the version-diff and tamper-evidence selection where practitioner judgment confirms the determination.

| Tier | Sub-clause / Article | Artifact | Plugin field | Classification |
|---|---|---|---|---|
| T1.1 | Article 12(1); ISO A.6.2.8 | Event schema normalized to per-field rows | `event_schema_normalized` | Automatable |
| T1.2 | Article 12(2) | Per-purpose traceability coverage map | `traceability_coverage` | Automatable |
| T1.3 | Article 12(3) | Biometric six-field check | `biometric_art_12_3_check` | Automatable |
| T1.4 | Article 19(1), (2) | Retention policy assessment with floor check | `retention_policy_assessment` | Automatable |
| T2.1 | Article 26(6); ISO A.6.2.8 | Tamper-evidence method declaration | `tamper_evidence_assessment` | Hybrid (plugin records method; practitioner selects and validates) |
| T2.2 | ISO A.6.2.8 | Schema diff against predecessor | `schema_diff_summary` | Hybrid (plugin scaffolds the link; practitioner authors substantive diff) |

### Event category catalogue

| Category | Typical fields |
|---|---|
| `inference-request` | request_id, timestamp, input_hash, subject_id |
| `inference-output` | request_id, output_hash, confidence, latency_ms |
| `risk-signal`, `drift-signal` | metric, value, threshold, timestamp |
| `safety-event` | severity, description, affected_subjects, timestamp |
| `override-action` | operator_id, override_reason, overridden_output_ref, timestamp |
| `consumer-complaint` | complaint_id, subject_id, category, receipt_timestamp |
| `auth-event` | principal, action, result, timestamp |
| `config-change`, `model-update` | version_before, version_after, actor, timestamp |
| `data-access` | accessor, data_ref, purpose, timestamp |
| `biometric-verification` | start_datetime, end_datetime, reference_database, input_data_ref, verification_result, operating_person_identity |

The biometric-verification row enumerates the six fields Article 12(3) explicitly requires.

## Output Standards

**Artifact type.** System-operational event log schema definition with per-field rows, traceability coverage map, retention policy assessment, biometric six-field check (when applicable), tamper-evidence assessment, and schema diff block (when applicable).

**Format.** Structured dict (JSON-serializable). Renderers emit Markdown (audit evidence package) and CSV (per-field spreadsheet).

**Citation format.** All citations match STYLE.md exactly. EU AI Act citations use `EU AI Act, Article XX, Paragraph X`. ISO citations use `ISO/IEC 42001:2023, Annex A, Control A.X.Y`. NIST citations use `NIST AI RMF, <FUNCTION> <Subcategory>`.

**Canonical top-level citations emitted.**

- EU AI Act, Article 12, Paragraph 1
- EU AI Act, Article 12, Paragraph 2
- EU AI Act, Article 12, Paragraph 3 (when `remote_biometric_id=True`)
- EU AI Act, Article 19, Paragraph 1
- EU AI Act, Article 19, Paragraph 2 (when `policy_name=sectoral-finance`)
- EU AI Act, Article 26, Paragraph 6
- EU AI Act, Article 79, Paragraph 1
- ISO/IEC 42001:2023, Annex A, Control A.6.2.8
- NIST AI RMF, MEASURE 2.8

**Input schema.** See the plugin README for the full input dict contract.

**Output schema.** Top-level keys: `timestamp`, `agent_signature`, `framework`, `system_description_echo`, `art_12_applicability`, `event_schema_normalized`, `traceability_coverage`, `retention_policy_assessment`, `tamper_evidence_assessment`, `citations`, `warnings`, `summary`, `reviewed_by`. Conditional keys: `biometric_art_12_3_check`, `schema_diff_summary`, `cross_framework_citations`, `cross_framework_references`.

**Jurisdiction.** Multi-jurisdiction. Article 12 mandatory obligation applies to EU high-risk systems; recommended-not-mandated elsewhere. ISO A.6.2.8 applies wherever the AIMS is implemented. NIST MEASURE 2.8 is voluntary worldwide.

## Limitations

- **The plugin produces the schema, not the logs.** Runtime log generation, capture, ingest, and storage are MLOps responsibilities. The plugin emits the structure those activities populate.
- **Tamper-evidence method selection is judgment-bound.** The plugin accepts five recognised methods (`hash-chain`, `hmac`, `cryptographic-signing`, `append-only-store`, `external-notary`) and records the declaration. It does not verify the method is correctly implemented; auditor judgment required.
- **No retention-clock enforcement.** The plugin records the retention policy; deletion execution is the log-custodian's responsibility and falls under Article 19 and ISO Clause 7.5.3.
- **Biometric field check is field-presence only.** The plugin checks that the six Article 12(3) fields appear in the `biometric-verification` category. It does not verify the field semantics or the data quality of the recorded values.
- **Sectoral retention citations are practitioner-supplied.** Sectoral finance and healthcare regimes vary across Member States; the plugin accepts any citation string and does not validate the regulatory reference.
- **Schema diff is scaffolded, not inferred.** The plugin records the predecessor link and the current category inventory. Substantive category-and-field diff authoring is a practitioner responsibility.

### Maintenance

EU AI Act Articles 12, 19, and 26 are in force. ISO/IEC 42001:2023 Annex A Control A.6.2.8 is stable. NIST AI RMF MEASURE 2.8 is stable in version 1.0. The skill requires no clause-text update between standard revisions; plugin schema is aligned to the published Article 12(3) field list.
