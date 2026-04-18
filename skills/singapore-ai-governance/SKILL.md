---
name: singapore-ai-governance
version: 0.1.0
description: >
  Singapore AI governance skill. Operationalizes the Model AI Governance
  Framework, Second Edition (MAGF 2e, 2020) published jointly by IMDA and PDPC,
  with layered application of the MAS FEAT Principles (2018) for
  financial-services organizations, and a lookup mapping of the AI Verify
  (IMDA 2024) 11 ethics principles to MAGF pillars. Authoritative sources:
  https://www.pdpc.gov.sg/help-and-resources/2020/01/model-ai-governance-framework
  (MAGF 2e), https://aiverifyfoundation.sg/ (AI Verify Foundation),
  https://www.mas.gov.sg/ (FEAT and Veritas). Validated against the published
  MAGF 2e text on 2026-04-18.
frameworks:
  - Singapore Model AI Governance Framework, Second Edition (MAGF 2e)
  - MAS FEAT Principles (2018)
  - AI Verify (IMDA 2024)
tags:
  - ai-governance
  - singapore
  - magf
  - feat
  - ai-verify
  - apac
  - imda
  - pdpc
  - mas
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the Singapore AI governance landscape. Three instruments and one methodology matter:

1. **Model AI Governance Framework, Second Edition (MAGF 2e).** Non-binding guidance published jointly by the Infocomm Media Development Authority (IMDA) and the Personal Data Protection Commission (PDPC) in January 2020. Four pillars cover internal governance, human involvement, operations management, and stakeholder communication. Voluntary, influential across APAC.
2. **MAS FEAT Principles (2018).** Four principles (Fairness, Ethics, Accountability, Transparency) published by the Monetary Authority of Singapore (MAS) on 12 November 2018 for the use of Artificial Intelligence and Data Analytics (AIDA) in the Singapore financial services sector. Regulatory expectation for MAS-regulated entities (banks, insurers, capital-markets intermediaries). Not a statute, but supervisors expect conformance.
3. **AI Verify (IMDA 2024).** Technical testing framework operationalizing MAGF through 11 AI ethics principles and an open-source toolkit combining process checks with technical tests.
4. **Veritas (MAS, 2019 through 2022).** Open-source methodology for assessing FEAT compliance in financial AI. Separate from the AIGovOps plugin: Veritas-style fairness metrics require the Veritas toolkit.

Singapore is an influential framework-exporter in APAC. MAGF language is referenced by regional regulators, the ASEAN Guide on AI Governance and Ethics (2024), and multinational compliance programs. Organizations building APAC compliance maps use MAGF as the anchor.

## Scope

**In scope.**

- MAGF 2e as published (IMDA/PDPC, January 2020).
- MAS FEAT Principles (2018) sub-criteria as MAS-published.
- AI Verify (IMDA 2024) 11 ethics principles mapped to MAGF pillars as a static lookup.
- Relationship to ISO/IEC 42001:2023, NIST AI RMF 1.0, and the EU AI Act.

**Out of scope.**

- Legal advice. MAGF is non-binding; FEAT is a supervisory expectation for MAS-regulated entities. Application of any instrument to a specific organization requires qualified Singapore counsel.
- Veritas toolkit execution. Fairness metrics per Veritas require the Veritas repository and notebooks. This skill does not produce those metrics.
- MAS enforcement interpretation. Supervisory actions are fact-specific and regulator-led.
- AI Verify technical testing execution. The AI Verify toolkit produces technical test results; the plugin only maps principles to MAGF pillars.
- IMDA Generative AI Governance Framework (June 2024). Separate instrument, not operationalized in this release.

**Jurisdictional scope.** Singapore (direct), APAC (influential by citation), global (referenced as an anchor framework).

## Framework Reference

### MAGF 2e structure

| Pillar | Name | Scope |
|---|---|---|
| 1 | Internal Governance Structures and Measures | Clear roles and responsibilities; risk management and internal controls; staff training. |
| 2 | Determining the Level of Human Involvement in AI-Augmented Decision-Making | Probability-severity matrix; tier selection: human-in-the-loop, human-over-the-loop, human-out-of-the-loop. |
| 3 | Operations Management | Data accountability (lineage, quality, bias); algorithm selection and robustness; periodic tuning; explainability, reproducibility, auditability. |
| 4 | Stakeholder Interaction and Communication | Disclosure of AI use; feedback and decision-review mechanisms; acceptable-use policies. |

Citation format: `Singapore MAGF 2e, Pillar <name>` or `Singapore MAGF 2e, Section <section>`.

### MAS FEAT Principles (2018)

| Principle | Core idea |
|---|---|
| Fairness | Use of AIDA-driven decisions is justifiable; individuals and groups are not systematically disadvantaged without justification. |
| Ethics | AIDA-driven decisions are held to at least the same ethical standards as human-driven decisions. |
| Accountability | Use of AIDA is approved by appropriate internal authority; firms are accountable to internal and external stakeholders. |
| Transparency | Proactive disclosure; clear explanations on request; communication that is easy to understand. |

Citation format: `MAS FEAT Principles (2018), Principle <Fairness|Ethics|Accountability|Transparency>`.

### AI Verify (IMDA 2024) principles

11 ethics principles: accountability, data-governance, human-agency-oversight, inclusive-growth, privacy, reproducibility, robustness, safety, security, transparency, fairness. Citation format: `AI Verify (IMDA 2024), Principle <name>`.

### Authority and binding status

| Instrument | Authority | Scope | Binding status |
|---|---|---|---|
| MAGF 2e | IMDA + PDPC | General (all sectors) | Voluntary, influential |
| MAS FEAT Principles | MAS | Financial services | Supervisory expectation (not statute) |
| AI Verify | IMDA / AI Verify Foundation | General (technical testing) | Voluntary |
| Veritas | MAS | Financial services fairness | Methodology (voluntary toolkit) |

## Operationalizable Controls

The dedicated plugin is `singapore-magf-assessor`. It consumes a system description and organization type and produces a pillar-by-pillar structured assessment with MAS FEAT layering for financial-services organizations and AI Verify principle coverage as a lookup.

### T1.1 MAGF assessment

Class: H. Artifact: `magf-assessment` with Singapore citations. Leverage: H. Consumer: `plugins/singapore-magf-assessor`.

**Plugin contract.** Accepts `system_description` (dict), `organization_type` (enum from `general`, `financial-services`, `healthcare`, `government`, `other`), and optional `reviewed_by`. Emits `applicable_frameworks`, `pillars` (four entries), `human_involvement_tier`, `ai_verify_principles_coverage`, `feat_principles` (only when financial-services), citations, and warnings. Warnings surface content gaps; ValueError on structural input defects.

**Auditor acceptance criteria.**

- Every MAGF pillar carries an `assessment_status` of `addressed`, `partial`, or `not-addressed`.
- Human involvement tier is one of the three MAGF values; default to `human-in-the-loop` with an explicit warning when absent.
- For financial-services organizations, FEAT principles appear with MAS-accurate sub-criteria.
- Citations conform to the three declared formats (`Singapore MAGF 2e, ...`, `MAS FEAT Principles (2018), Principle ...`, `AI Verify (IMDA 2024), Principle ...`).

### Operationalization map: MAGF pillars to existing AIGovOps artifacts

| MAGF pillar | Existing artifact | Plugin |
|---|---|---|
| Internal Governance | role-matrix, audit-log | `role-matrix-generator`, `audit-log-generator` |
| Human Involvement | AISIA (human-oversight dimension) | `aisia-runner` |
| Operations Management | risk-register, metrics | `risk-register-builder`, `metrics-collector` |
| Stakeholder Communication | audit-log, data-register | `audit-log-generator`, `data-register-builder` |

See [operationalization-map.md](operationalization-map.md) for the per-pillar and per-FEAT crosswalk with ISO 42001 and NIST AI RMF citations.

### FEAT integration (financial-services only)

Each FEAT principle layers on top of the corresponding MAGF pillar and maps to ISO 42001 + AI Verify + NIST AI RMF:

| FEAT principle | MAGF pillar | ISO 42001 anchor | NIST AI RMF anchor | AI Verify anchor |
|---|---|---|---|---|
| Fairness | Operations Management | Annex A.6.2.4, A.7.3 | MEASURE 2.11 | fairness |
| Ethics | Internal Governance | Clause 5; Annex A.3 | GOVERN 1.1, GOVERN 3.2 | inclusive-growth |
| Accountability | Internal Governance; Stakeholder Communication | Clause 5.3; Annex A.3.3 | GOVERN 1.2 | accountability |
| Transparency | Stakeholder Communication | Annex A.8.2 | MEASURE 2.8 | transparency |

### Tier 2 operationalizations

Lower-frequency controls, abbreviated guidance:

1. **Data governance evidence for Pillar 3.** Use `data-register-builder` to produce the ISO A.7 / EU AI Act Article 10 register; MAGF data accountability is a subset.
2. **Risk register anchored on MAGF Pillar 3.** Use `risk-register-builder` with MAGF-tagged rows; the MAGF operations management pillar maps onto ISO 42001 Annex A.6 risk treatment.
3. **AI Verify toolkit integration.** When the user runs the AI Verify open-source toolkit separately, the plugin output can carry toolkit result references in evidence_refs.

### Tier 3 judgment-bound

- Whether a specific MAS-regulated firm's implementation is supervisor-acceptable under FEAT.
- Whether a given human-involvement tier is appropriate for a specific probability-severity matrix.
- Whether the firm needs to run Veritas-style fairness metrics or a lighter proxy.

## Output Standards

All outputs produced by this skill, or by `singapore-magf-assessor` in the default mode, conform to [STYLE.md](../../STYLE.md).

### Citation formats

- `Singapore MAGF 2e, Section <section>` or `Singapore MAGF 2e, Pillar <name>`
- `MAS FEAT Principles (2018), Principle <Fairness|Ethics|Accountability|Transparency>`
- `AI Verify (IMDA 2024), Principle <name>` (one of the 11)
- `MAS Veritas (2022)` for any reference to the methodology

### Actor-role labeling

Every assessment identifies the `organization_type`. Financial-services organizations receive the FEAT layer; all other types receive MAGF-only.

### Schema pointers

- Input schema: see [`plugins/singapore-magf-assessor/README.md`](../../plugins/singapore-magf-assessor/README.md).
- Output schema: `generate_magf_assessment` return shape.
- Markdown rendering: `render_markdown`. CSV rendering: `render_csv`.
- Cross-framework mapping: see [`operationalization-map.md`](operationalization-map.md).

### Jurisdiction scope

Singapore (direct), APAC (influential via MAGF citation in ASEAN Guide and regional regulator statements), global (MAGF is referenced as a common anchor in multinational compliance programs).

### Maintenance

Flagged for quarterly drift review. AI Verify updates annually; FEAT interpretation through Veritas updates periodically. The IMDA Generative AI Governance Framework (June 2024) is a candidate for a follow-on skill once sponsor demand supports the build.

## Limitations

**This skill does not produce MAGF, FEAT, or AI Verify compliance.** Compliance requires substantive implementation. The plugin outputs the structured assessment and citation map; execution is the organization's responsibility.

**This skill does not provide legal advice.** Application of MAGF, FEAT, or AI Verify to a specific organization, system, or decision requires qualified Singapore counsel. MAGF is non-binding; FEAT is a supervisory expectation, not a statute. Legal application is out of scope.

**This skill does not produce Veritas-style fairness metrics.** The Veritas methodology requires the open-source Veritas toolkit. The plugin surfaces FEAT fairness sub-criteria and evidence presence; it does not compute bias metrics.

**This skill does not execute AI Verify technical tests.** The AI Verify toolkit runs technical tests against the deployed model. The plugin only maps the 11 principles to MAGF pillars as a static lookup.

**Non-goals.** The plugin does not interpret MAS enforcement; it does not produce Veritas-style fairness metrics; it does not run AI Verify technical tests.

**Sector scope.** FEAT applies to MAS-regulated financial-services entities. Organizations that are not MAS-regulated but are adjacent (for example, fintechs below MAS licensing thresholds) should still consider FEAT as best practice; the plugin does not determine MAS licensing status.

**APAC positioning.** MAGF is influential but non-binding outside Singapore. Practitioners mapping APAC compliance across Singapore, Hong Kong, Japan, Korea, and Australia should treat MAGF as the anchor and layer jurisdiction-specific instruments separately.
