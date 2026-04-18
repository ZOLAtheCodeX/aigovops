---
name: internal-audit
version: 0.1.0
description: >
  ISO/IEC 42001:2023 Clause 9.2 internal audit operationalization.
  Turns the standard's internal-audit requirements into an agent-runnable
  workflow that produces an audit programme, schedule, criteria mapping,
  auditor impartiality assessment, and reporting structure for relevant
  management. Companion to the iso42001 skill; focused on Clause 9.2
  specifically.
frameworks:
  - ISO/IEC 42001:2023
tags:
  - ai-governance
  - iso42001
  - internal-audit
  - audit-programme
  - clause-9-2
  - aims
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes ISO/IEC 42001:2023 Clause 9.2 (Internal audit). It completes the Clause 9 to 10 pillar of the AIMS lifecycle together with the management-review-packager (Clause 9.3.2) and nonconformity-tracker (Clause 10.2) plugins.

Clause 9.2 requires the organization to conduct internal audits at planned intervals, to plan and maintain a programme, to define criteria and scope for each audit, to select auditors that ensure objectivity and impartiality, to report results to relevant management, and to retain documented information as evidence. This skill turns those requirements into executable plugin input and artifact fields.

The skill does not execute audits. It plans them. The plugin generates an audit programme, a schedule, a criteria mapping, and an impartiality assessment from structured organizational input. Human auditors then execute each cycle; findings flow into the nonconformity-tracker; aggregated results flow into the management-review-packager (Clause 9.3.2 category `audit_results`).

## Scope

**In scope.** ISO/IEC 42001:2023 Clause 9.2 (9.2.1 General and 9.2.2(a) through (e) Internal audit programme), including:

- Planning frequency, methods, responsibilities, reporting obligations (9.2.2(a)).
- Defining audit criteria and scope for each cycle (9.2.2(b)).
- Selecting auditors with documented impartiality posture (9.2.2(c)).
- Routing results to relevant management (9.2.2(d)).
- Retaining documented information per Clause 7.5.3 (9.2.2(e)).
- The downstream handoff into Clause 9.3 (management review consumes audit results).

**Out of scope.**

- Audit finding generation. The plugin does not invent findings.
- Lead Auditor judgment calls. Audit conclusions are judgment-bound.
- Certification audits (third-party audits). The plugin supports `audit_type: third-party` for programme structuring, but certification decisions remain with the certification body.
- Legal advice on jurisdictional audit requirements.

**Operating assumption.** The organization has an AIMS scope statement, a risk register, and a pool of candidate auditors (internal or external). Clause 9.2 cannot be operationalized without those inputs.

## Framework Reference

**Authoritative source.** ISO/IEC 42001:2023, Clause 9.2. The full standard text is copyrighted; purchase via the ISO store or a national standards body.

**Clause structure.**

- Clause 9.2.1 General: conduct audits at planned intervals.
- Clause 9.2.2 Internal audit programme: items (a) through (e) listed above.
- Clause 7.5.3 Control of documented information: retention of audit records.
- Clause 9.3 Management review: consumes audit results as an input category.

**Related subclauses and supporting documents.**

- ISO/IEC 42001:2023 Clause 6.1 (actions to address risks and opportunities) supplies the risk register used for audit prioritization per 9.2.2(a).
- ISO/IEC 42001:2023 Clause 10.2 (nonconformity and corrective action) consumes audit findings.
- ISO 19011:2018 (Guidelines for auditing management systems) informs auditor competence and audit methods even though it is not directly normative for ISO 42001.

**Relationship to other frameworks.**

- NIST AI RMF 1.0: MEASURE 4.1 (measurement feedback), MEASURE 4.2 (measurement informed by experts), MEASURE 4.3 (feedback mechanisms). Partial-match in both directions; NIST does not require a formal internal audit programme, but an ISO 42001 Clause 9.2 programme produces inputs that satisfy the intent of MEASURE 4.1 to 4.3 when findings feed risk updates and governance decisions. Confidence: medium.
- EU AI Act (Regulation (EU) 2024/1689) Article 17(1)(d): examination, test, and validation procedures as part of the provider's quality management system. ISO 9.2 internal audit partially satisfies this when the programme tests that AIMS procedures operate as designed. Confidence: high.
- EU AI Act Article 17(1)(k): record-keeping. ISO 9.2.2(e) retention of documented information as evidence of the audit programme satisfies this record-keeping obligation. Confidence: high.

## Operationalizable Controls

Single-tier operationalization: Clause 9.2 produces one primary artifact (the audit programme), with four supporting artifacts.

| Tier | Sub-clause | Artifact | Plugin field | Classification |
|---|---|---|---|---|
| T1.1 | 9.2.2(a) | Audit programme (frequency, methods, responsibilities, reporting) | `audit_schedule`, `summary` | Automatable |
| T1.2 | 9.2.2(b) | Audit criteria and scope definition per cycle | `criteria_mapping`, `audit_schedule[].scope_this_cycle`, `audit_schedule[].audit_criteria` | Automatable |
| T1.3 | 9.2.2(c) | Auditor selection and impartiality assessment | `impartiality_assessment`, `auditor_pool` input | Hybrid (plugin flags conflicts; human reassigns) |
| T1.4 | 9.2.2(d) | Reporting routing to relevant management | `audit_schedule[].reporting_recipients` | Automatable |
| T1.5 | 9.2.2(e) | Retention of documented information | Clause 7.5.3 citation on every schedule entry | Automatable |

### Classification definitions

- **Automatable.** End-to-end automation feasible. Plugin produces compliant output from structured input without human intervention in the common case.
- **Hybrid.** Plugin produces a draft or scaffold; human review is required before the output becomes audit evidence. Impartiality reassignment is the canonical hybrid step in this skill.
- **Human judgment required.** Not applicable in Clause 9.2. Findings generation is judgment-bound but is out of scope for this skill.

### How this complements Clause 9.3

Clause 9.3 (management review) consumes Clause 9.2 audit results as one of its required input categories. The management-review-packager plugin has a dedicated `audit_results` category in its Clause 9.3.2 input package. The internal-audit-planner plugin output feeds that category directly: the `summary` and `audit_schedule` fields are the source of record for Clause 9.3.2 inputs. Together, Clause 9.2 (this skill) and Clause 9.3 (the management-review-packager skill/plugin) form the performance-evaluation half of the AIMS lifecycle; Clause 10 (continual improvement, including the nonconformity-tracker) closes the loop.

## Output Standards

**Artifact type.** Internal audit programme, schedule, criteria mapping, impartiality assessment.

**Format.** Structured dict (JSON-serializable). Renderers emit Markdown (audit evidence package) and CSV (schedule spreadsheet).

**Citation format.** All ISO citations match STYLE.md: `ISO/IEC 42001:2023, Clause X.X.X` or `ISO/IEC 42001:2023, Clause X.X.X(a)` for sub-items. NIST citations use `<FUNCTION> <Subcategory>`. EU AI Act citations use `EU AI Act, Article XX, Paragraph X, Point (x)`.

**Canonical top-level citations emitted.**

- ISO/IEC 42001:2023, Clause 9.2.1
- ISO/IEC 42001:2023, Clause 9.2.2(a)
- ISO/IEC 42001:2023, Clause 9.2.2(b)
- ISO/IEC 42001:2023, Clause 9.2.2(c)
- ISO/IEC 42001:2023, Clause 9.2.2(d)
- ISO/IEC 42001:2023, Clause 9.2.2(e)
- ISO/IEC 42001:2023, Clause 7.5.3
- ISO/IEC 42001:2023, Clause 9.3

**Input schema.** See the plugin README for the full input dict contract.

**Output schema.** Top-level keys: `timestamp`, `agent_signature`, `framework`, `reviewed_by`, `scope_echo`, `audit_schedule`, `scope_coverage_summary`, `impartiality_assessment`, `criteria_mapping`, `citations`, `warnings`, `summary`, optional `cross_framework_audit_references`.

**Jurisdiction.** International. Clause 9.2 is jurisdiction-neutral; it applies wherever the AIMS is implemented. Per [docs/jurisdiction-scope.md](../../docs/jurisdiction-scope.md), ISO/IEC 42001:2023 is a primary (international) instrument.

## Limitations

- **The plugin does not execute audits.** It plans them. Findings are produced by human auditors working against the criteria the plugin emits.
- **The plugin does not author findings.** Root-cause analysis, nonconformity classification, and corrective-action selection are judgment-bound activities handled by the nonconformity-tracker plugin on the basis of auditor-supplied input.
- **Impartiality check is structural, not substantive.** The plugin flags a conflict when an auditor's declared `own_areas` overlap the cycle scope or when `independence_level: insufficient` is declared. It cannot detect undisclosed conflicts.
- **Scheduling is deterministic.** Planned start and end dates are computed from `audit_frequency_months` anchored at the generation date. Calendar conflicts, holidays, and resource constraints are out of scope; organizations adjust the schedule manually.
- **Prior-findings weighting is heuristic.** Severity-weighted risk scores (`critical=100, major=30, minor=10, observation=3`) are a deterministic ordering rule, not a risk-assessment methodology. Organizations with a mature risk register should pass `management_system_risk_register_ref` so the criteria mapping echoes the authoritative risk-weighting source.
- **Non-goals.** The plugin does not produce audit findings without input evidence. It does not issue certification decisions. It does not substitute for Lead Auditor judgment.

### Maintenance

ISO/IEC 42001:2023 is stable. Clause 9.2 has no errata or amendment published as of the version date of this skill (see SKILL.md `version`). Between standard revisions the skill requires no clause-text updates; plugin output evolves as the surrounding AIMS lifecycle (risk register, nonconformity tracker) evolves.
