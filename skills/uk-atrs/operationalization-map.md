# UK ATRS operationalization map

This document maps the eight canonical UK Algorithmic Transparency Recording Standard (ATRS) sections to AIGovOps artifacts and plugins. Use it to assemble ATRS record inputs from existing governance evidence rather than re-collecting information.

Status: 0.1.0. Aligned to ATRS Template v2.0 as of 2026-04-18.

## Operationalizability classes

- **Automatable (A).** End-to-end automation is feasible. The plugin can produce compliant output from structured input.
- **Hybrid (H).** Automation produces a draft. A human must review, complete, or approve before publication.
- **Human judgment required (J).** The section is judgment-bound. Automation assists information gathering at most.

## Section map

### Section: Owner and contact

Class: **Automatable.**

| ATRS field | Source | Artifact |
|---|---|---|
| Publishing organization | Organizational charter. | Static input. |
| Parent organization | Organizational charter. | Static input. |
| Contact point | Role matrix contact rows. | `role-matrix-generator` |
| Senior responsible owner | Role matrix accountable-owner row for the system. | `role-matrix-generator` |

Rule: if the role matrix lacks an accountable-owner row for the in-scope system, emit a warning and require human assignment.

### Section: Tool description

Class: **Automatable.**

| ATRS field | Source | Artifact |
|---|---|---|
| Name | AISIA system_description.system_name. | `aisia-runner` |
| Purpose | AISIA system_description.purpose. | `aisia-runner` |
| How the tool works | AISIA system_description.intended_use plus deployment_environment. | `aisia-runner` |
| Decision-subject scope | AISIA affected_stakeholders. | `aisia-runner` |
| Phase | System lifecycle state (development, pilot, production, retired). | Organizational input. |

### Section: Tool details

Class: **Hybrid.**

| ATRS field | Source | Artifact |
|---|---|---|
| Model family | Model card. | Caller input. |
| Model type | Model card. | Caller input. |
| System architecture | System architecture document. | Caller input. |
| Training data summary | Data register rows for training-stage data. | `data-register-builder` |
| Model performance metrics | MEASURE 2.x metrics for the in-scope system. | `metrics-collector` |
| Third-party components | SBOM or vendor register. | Caller input. |

Rule: training data summary is plain-English. Do not dump the data register. Summarize.

### Section: Impact assessment

Class: **Hybrid.**

| ATRS field | Source | Artifact |
|---|---|---|
| Assessments completed | DPIA identifier, EIA identifier, other assessment identifiers. | Caller input (internal GRC system). |
| Citizen-impact dimensions | AISIA impact dimensions (fundamental rights, group fairness, societal impact, physical safety). | `aisia-runner` |
| Severity | AISIA severity. | `aisia-runner` |
| Affected groups | AISIA affected_stakeholders filtered to citizen-facing groups. | `aisia-runner` |
| Consultation summary | Stakeholder engagement records. | Caller input. |

Rule: every assessment citation must resolve to a stable internal identifier so a reviewer can audit the underlying document. `DPIA-2026-03` is acceptable; `DPIA completed` is not.

### Section: Data

Class: **Automatable.** The data register already carries the load-bearing fields.

| ATRS field | Source | Artifact |
|---|---|---|
| Source | Data register rows filtered to the in-scope system. | `data-register-builder` |
| Processing basis | Data register processing_basis field. | `data-register-builder` |
| Data categories | Data register data_category plus protected_attributes. | `data-register-builder` |
| Collection method | Data register acquisition_method. | `data-register-builder` |
| Sharing | Data register sharing rows. | `data-register-builder` |
| Retention | Data register retention_days and retention_expiry. | `data-register-builder` |

### Section: Risks

Class: **Automatable.**

| ATRS field | Source | Artifact |
|---|---|---|
| Category | Risk register row category. | `risk-register-builder` |
| Description | Risk register row description. | `risk-register-builder` |
| Mitigation | Risk register row mitigation. | `risk-register-builder` |
| Residual risk | Risk register row residual tier after mitigation. | `risk-register-builder` |

Rule: filter the risk register to rows referencing the in-scope system. Do not publish the organization's full risk register.

### Section: Governance

Class: **Hybrid.**

| ATRS field | Source | Artifact |
|---|---|---|
| Oversight body | Role matrix governance-committee row. | `role-matrix-generator` |
| Escalation path | Incident response policy. | Caller input. |
| Review cadence | Management review schedule. | `management-review-packager` inputs. |
| Incident response | Incident response policy plus on-call reference. | Caller input. |
| Human oversight model | AISIA decision_authority field. | `aisia-runner` |

### Section: Benefits

Class: **Hybrid.**

| ATRS field | Source | Artifact |
|---|---|---|
| Benefit categories | AISIA benefits section. | `aisia-runner` |
| Measurement approach | Metrics collector threshold definitions for benefit KPIs. | `metrics-collector` |
| Realised benefits summary | Post-deployment metrics summary. | `metrics-collector` |

Rule: do not state a benefit without a measurement approach. An unmeasured benefit is not a benefit.

## Relationship to other frameworks

- **ISO/IEC 42001:2023.** Complements Clauses 6.1.4 (AI System Impact Assessment) and Annex A category A.7 (data for AI systems). AISIA and data register content feed directly into the ATRS Impact assessment and Data sections.
- **EU AI Act.** Not equivalent to Article 50 (transparency). Article 50 is user-facing disclosure: a person interacting with an AI system must be informed. ATRS is a public-sector transparency record about the tool itself. A system operating in both jurisdictions requires both artifacts.
- **NIST AI RMF 1.0.** No direct equivalent. Closest mapping is GOVERN 1.4 (transparency and accountability to stakeholders). Publishing an ATRS record is one form of GOVERN 1.4 evidence but does not discharge the function.

## Citation format

Every section citation emitted by the `uk-atrs-recorder` plugin follows the format:

`UK ATRS, Section <name>`

Examples:

- `UK ATRS, Section Owner and contact`
- `UK ATRS, Section Tool description`
- `UK ATRS, Section Impact assessment`

The top-level record citation list includes the authoritative gov.uk URL, the template version string (`ATRS Template v2.0`), and one citation per section.

## Template version tracking

The ATRS template is maintained by the UK Central Digital and Data Office. Revise this skill and the `uk-atrs-recorder` plugin when CDDO publishes a new template version. Pin the template version constant in `plugin.py` to the version this skill was validated against.

Current pinned version: `ATRS Template v2.0`.

Last validated: 2026-04-18.
