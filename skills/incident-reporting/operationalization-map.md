# Incident Reporting Operationalization Map

Working document for the `incident-reporting` skill. Maps each external-reporting regime to its A/H/J operationalizability classification and the AIGovOps artifact vocabulary. Same methodology as `skills/iso42001/operationalization-map.md`.

**Validation status.** Section references validated against the EU AI Act (Regulation (EU) 2024/1689), Colorado SB 205 codification, and NYC DCWP AEDT Rules on 2026-04-18.

**Classification legend.**

- A: automatable. The plugin derives output deterministically from structured input.
- H: hybrid. The plugin assembles and validates; a human provides key substantive content.
- J: judgment. A qualified human (counsel, senior reviewer, external auditor) must decide.

**Leverage legend.**

- H: strong cost reduction from automation.
- M: moderate.
- L: low.

## EU AI Act Article 73: Serious incident reporting

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Article 3(49) serious-incident definition | Threshold determination | J | `incident-description` | L | Counsel determines serious-incident qualification. Plugin records the answer. |
| Article 73(6) 2-day deadline (fatality, widespread infringement) | Deadline computation | A | `deadline_matrix` | H | Plugin computes `detected_at + 2 days`. |
| Article 73(7) 10-day deadline (serious physical harm, critical infrastructure) | Deadline computation | A | `deadline_matrix` | H | Plugin computes `detected_at + 10 days`. |
| Article 73(2) 15-day default deadline | Deadline computation | A | `deadline_matrix` | H | Plugin computes `detected_at + 15 days`. |
| Required contents (system identity, nature, chain of events, corrective measures) | Draft template | H | `report_draft` | H | Plugin emits structured template with placeholders. Practitioner completes narrative. |
| Provider vs deployer actor role | Obligation assignment | J | `report_draft.actor` | M | Plugin records input; warns when missing and EU applies. |
| Transmission to EU AI Office via competent authority | Operational | N/A | external | N/A | Outside plugin. |

## EU AI Act Article 20: Corrective action and authority notification

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Provider duty of immediate corrective action | Operational posture | H | `report_draft.correction_plan` | M | Plugin propagates correction_plan into draft; does not mandate the action. |
| Authority notification when system presents risk under Article 79(1) | Notification trigger | J | `deadline_matrix` | L | Article 79 risk determination is counsel-side; plugin assembles the report on caller confirmation. |

## Colorado SB 205: Algorithmic discrimination disclosure

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Section 6-1-1701(1) algorithmic-discrimination definition | Threshold determination | J | `incident-description` | L | Counsel determines discrimination qualification. |
| Section 6-1-1701(3) consequential-decision domain | Applicability input | H | `report_draft.consequential_domains` | M | Plugin requires input; warns when absent. |
| Section 6-1-1702(7) 90-day developer disclosure | Deadline computation | A | `deadline_matrix` | H | Plugin computes `detected_at + 90 days`. |
| Section 6-1-1703(7) 90-day deployer disclosure | Deadline computation | A | `deadline_matrix` | H | Plugin computes `detected_at + 90 days`. |
| Required contents (detection, description, domain, evidence, mitigation) | Draft template | H | `report_draft` | H | Plugin emits template; practitioner completes evidence summary. |
| Transmission to Colorado Attorney General | Operational | N/A | external | N/A | Outside plugin. |

## NYC LL144: AEDT candidate-complaint disclosure

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Section 20-872 prohibition on use without current audit | Operational gate | H | external | M | Plugin surfaces `next_audit_due_by` via `nyc-ll144-audit-packager`; this plugin handles incident-side only. |
| DCWP Rules Section 5-303 candidate-notice complaint window | Deadline computation | A | `deadline_matrix` | M | Plugin computes `detected_at + 30 days` as the conventional investigation-response window. |
| Compliance-posture statement (reference current bias audit) | Draft template | H | `report_draft` | M | Plugin emits placeholder; practitioner references audit-packager output. |
| Transmission to DCWP and candidate | Operational | N/A | external | N/A | Outside plugin. |

## Composition with sibling plugins

### Internal counterpart: `nonconformity-tracker`

| Signal | Direction | Usage |
|---|---|---|
| Clause 10.2 nonconformity record created | nonconformity-tracker to incident-reporting | Caller determines whether the nonconformity is also a reportable incident. If yes, caller invokes incident-reporting with the same `detected_at`. |
| Root cause identified | nonconformity-tracker | Feeds the `chain of events` narrative in the EU Article 73 draft. |
| Corrective action complete | nonconformity-tracker | Feeds the `corrective measures` narrative in all three regimes. |
| Effectiveness review outcome | nonconformity-tracker | Supports any follow-up report to authorities. |

The internal and external tracks run in parallel. The internal Clause 10.2 record may remain open while the external report is filed; Article 73 and SB 205 clocks do not wait for internal closure.

### Audit trail: `audit-log-generator`

Every `report_drafts` entry is a documented-information event. The aigovclaw runtime routes one `audit-log-entry` per draft with the citation `ISO/IEC 42001:2023, Clause 7.5.2`, fulfilling the Clause 9.1 evidence-trail requirement for external-reporting decisions. The audit log records the draft's `deadline_iso`, `status at time of logging`, and `filing_recipient`.

### Risk register: `risk-register-builder`

A recurring or high-severity incident is a signal for post-market-monitoring risk recalibration. The `severity` and `impacted_persons_count` fields feed back into risk-register rows for the affected systems under NIST AI RMF MANAGE 4.1 and ISO/IEC 42001:2023 Clause 6.1.

### NIST AI RMF crosswalk: MANAGE 4.3 (informational)

MANAGE 4.3 establishes internal communication of incidents to AI actors. It is not an external-authority notification. The incident-reporting skill cites MANAGE 4.3 as the informational internal-communication counterpart; it does not discharge Article 73 or SB 205 obligations.

## Counts

- Automatable provisions (A): 7.
- Hybrid provisions (H): 8.
- Judgment-bound provisions (J): 4.
- External operational steps: 3.

Automation coverage is high for deadline computation and template assembly. Narrative content, threshold determinations, and transmission remain outside the plugin boundary.
