---
name: uk-atrs
version: 0.1.0
description: >
  UK Algorithmic Transparency Recording Standard (ATRS) skill. Operationalizes
  the UK Central Digital and Data Office transparency record template (Tier 1
  short public summary and Tier 2 detailed technical record) into an agent
  workflow that produces an audit-ready ATRS record for publication on
  gov.uk. First secondary-jurisdiction overlay per the AIGovOps
  jurisdiction-scope policy.
frameworks:
  - UK Algorithmic Transparency Recording Standard
tags:
  - ai-governance
  - uk
  - atrs
  - transparency
  - public-sector
  - tier-1
  - tier-2
author: AIGovOps Contributors
license: MIT
---

## Overview

The UK Algorithmic Transparency Recording Standard (ATRS) is the UK Government's standard for recording information about algorithmic tools used in public-sector decision-making. It turns a public-sector body's internal governance documentation into a published transparency record that citizens, journalists, and oversight bodies can read.

This skill operationalizes the ATRS template across both tiers. Tier 1 is a short, plain-English public summary aimed at a general audience. Tier 2 is a detailed technical record aimed at technical reviewers, oversight bodies, and regulators. A complete ATRS record is Tier 1 plus Tier 2 published together.

The skill is framework-agnostic in the sense that any agent runtime reading SKILL.md can load it (Hermes Agent, Claude Code, Codex CLI, Cursor, Jules). The runtime invokes the `uk-atrs-recorder` plugin to emit the structured record.

## Scope

**In scope.** UK public sector bodies publishing algorithmic transparency records per the ATRS template v2.0:

- UK Central Government departments (mandatory as of February 2024).
- Executive agencies, non-departmental public bodies, and arms-length bodies operating under a central department (mandatory by inheritance).
- Wider UK public sector (local authorities, NHS bodies, police forces) where the organization has adopted ATRS as guidance. Not mandatory in 2026.

**Out of scope.** The skill does not provide:

- Legal advice on UK Data Protection Act 2018 or UK GDPR compliance. Consult the Information Commissioner's Office (ICO) and qualified counsel.
- ICO AI auditing framework operationalization (separate instrument, not yet in this catalogue).
- Sector-specific UK regulation (financial services PRA and FCA rules, healthcare MHRA software-as-a-medical-device).
- Private-sector transparency obligations. The ATRS is a public-sector standard; private-sector actors may publish ATRS-style records voluntarily but are not within the standard's scope.
- Non-UK transparency regimes. EU AI Act Article 50 is a separate obligation addressed in the `eu-ai-act` skill.

**Operating assumption.** The user organization is a UK public-sector body producing or commissioning an algorithmic or AI-assisted tool that affects decisions about citizens or public services. The organization has committed to publishing an ATRS record.

## Framework Reference

**Authoritative source.** UK Government, Algorithmic Transparency Recording Standard, guidance for public sector bodies, published by the Central Digital and Data Office (CDDO, now part of the Department for Science, Innovation and Technology). The standard is open and free to use.

- Guidance: https://www.gov.uk/government/publications/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies
- Hub of published records: https://www.gov.uk/government/collections/algorithmic-transparency-recording-standard-hub

**Structure.** The ATRS template v2.0 organizes each record into eight canonical sections:

| Section | Content |
|---|---|
| Owner and contact | Publishing organization, parent organization, contact point for queries, senior responsible owner. |
| Tool description | Plain-English name, purpose, how the tool works, decision-subject scope, deployment phase. |
| Tool details | Model family, model type, system architecture, training data summary, performance metrics, third-party components. |
| Impact assessment | Assessments completed (DPIA, EIA, other), citizen-impact dimensions, severity, affected groups, consultation summary. |
| Data | Source, processing basis, data categories, collection method, sharing arrangements, retention. |
| Risks | Enumerated risks with category, description, mitigation, residual risk. |
| Governance | Oversight body, escalation path, review cadence, incident response, human oversight model. |
| Benefits | Benefit categories, measurement approach, realised benefits summary. |

**Tiers.**

- Tier 1 is the short public-facing summary. Minimum sections: Owner and contact, Tool description, Benefits.
- Tier 2 is the detailed technical record. All eight sections required.

Published ATRS records on gov.uk present Tier 1 and Tier 2 together.

## Operationalizable Controls

Every ATRS section maps to one or more AIGovOps artifacts. The skill pulls content from existing plugin outputs rather than re-collecting information. The mapping is the load-bearing insight: an organization with mature AIGovOps artifacts can emit an ATRS record with high coverage from existing evidence.

| ATRS Section | AIGovOps artifact source | Operationalization class |
|---|---|---|
| Owner and contact | `role-matrix-generator` rows (senior responsible owner, contact points). | Automatable. |
| Tool description | `aisia-runner` system description fields (name, purpose, intended use, decision authority). | Automatable. |
| Tool details | `soa-generator` rows where technical controls apply plus model-card-style inputs. | Hybrid. Model-family and architecture are caller inputs; plugin assembles. |
| Impact assessment | `aisia-runner` impact dimensions (fundamental rights, group fairness, societal impact, physical safety) plus DPIA or EIA references. | Hybrid. The AISIA supplies the dimensions; the DPIA and EIA references are caller inputs. |
| Data | `data-register-builder` outputs. Source, processing basis, categories, sharing, retention are first-class in the data register. | Automatable when the data register already exists. |
| Risks | `risk-register-builder` rows filtered to the in-scope system. Categories, descriptions, mitigations, residual risks map directly. | Automatable. |
| Governance | `audit-log-generator` entries plus `role-matrix-generator` oversight rows plus incident response policy reference. | Hybrid. Review cadence and escalation path are organizational inputs. |
| Benefits | `aisia-runner` benefits section plus measurement-approach inputs. | Hybrid. Realised benefits require post-deployment measurement data. |

**Canonical workflow.** An agent tasked with producing an ATRS record for system `SYS-X` should:

1. Pull the role matrix row for `SYS-X` to populate Owner and contact.
2. Pull the AISIA for `SYS-X` to populate Tool description and Impact assessment and Benefits.
3. Pull the data register rows referencing `SYS-X` to populate Data.
4. Pull the risk register rows referencing `SYS-X` to populate Risks.
5. Assemble model-family, architecture, and performance metrics from model documentation to populate Tool details.
6. Assemble oversight body, escalation path, review cadence from governance documentation to populate Governance.
7. Invoke `generate_atrs_record` with the assembled inputs.
8. Review warnings. Resolve all content gaps before publication.

**Citation format.** Every section citation in the output is exactly `UK ATRS, Section <name>` (for example `UK ATRS, Section Tool description`). The top-level record citation includes the authoritative gov.uk URL and the template version string.

## Output Standards

ATRS records produced by this skill must be acceptable as-is for publication on gov.uk. This means:

- Plain-English prose in Tier 1. No jargon without a plain-English gloss.
- Technical precision in Tier 2. Model family, architecture, and performance metrics stated concretely.
- Every cited assessment (DPIA, EIA) referenced by a stable internal identifier so reviewers can audit the underlying document.
- Every risk stated with a category, a description, a mitigation, and a residual-risk tier. No vague risks.
- Every benefit stated with a measurement approach. No unmeasured benefits.
- No em-dashes, no emojis, no hedging. Definite determinations throughout.
- Senior responsible owner named. Contact point is a routable government email address.

See `STYLE.md` in the repository root for the canonical quality standard.

## Limitations

- The plugin does not discover the organization's governance artifacts. The caller must assemble the inputs. A future adapter layer may pull directly from a GRC platform; that is out of scope for 0.1.0.
- The plugin does not validate content accuracy. Owner names, contact points, and risk descriptions are accepted as supplied. An auditor or reviewer must verify accuracy before publication.
- Content gaps surface as warnings, not errors. An ATRS record with warnings is not publication-ready; the caller must resolve every warning or document why resolution is not possible.
- The template version is pinned to `ATRS Template v2.0` as of 2026-04-18. Revise the skill and plugin when CDDO publishes a new template version.
- Not equivalent to EU AI Act Article 50 (user-facing transparency disclosure). Article 50 addresses user-facing labelling of AI-generated content and interaction with an AI system. ATRS is a public transparency record about the tool itself. A system operating in both jurisdictions needs both artifacts.
- No direct equivalent in NIST AI RMF 1.0. The closest mapping is GOVERN 1.4 (transparency and accountability). Publishing an ATRS record contributes to GOVERN 1.4 evidence but is not a substitute for it.
- Complements, does not replace, ISO/IEC 42001:2023 Clauses 6.1.4 (AI System Impact Assessment) and Annex A category A.7 (data for AI systems). An organization pursuing ISO 42001 certification can reuse AISIA and data register content in its ATRS record.

## Jurisdiction

UK public sector. UK Central Government departments (mandatory). Wider UK public sector (encouraged but not mandatory as of 2026). Private sector is out of scope. Non-UK jurisdictions are out of scope.

## Input schema

See the `generate_atrs_record` docstring in `plugins/uk-atrs-recorder/plugin.py` for the exact input dict shape and required fields.

## Output structure

See `render_markdown` and `render_csv` in `plugins/uk-atrs-recorder/plugin.py` for the exact rendering contract.
