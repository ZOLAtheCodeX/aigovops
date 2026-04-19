---
name: human-oversight
version: 0.1.0
description: >
  Human oversight design and operation for AI systems. Operationalizes
  EU AI Act Article 14, ISO/IEC 42001:2023 Annex A controls A.9.2,
  A.9.3, and A.9.4, and NIST AI RMF MANAGE 2.3 into agent workflows
  that produce dedicated human-oversight design artifacts: ability
  coverage against Article 14(4)(a) through (e), override capability,
  biometric dual-assignment verification per Article 14(5), operator
  training posture, automation bias mitigations, and assigned oversight
  personnel. Distinct from the aisia-runner plugin which treats
  human-oversight as one impact dimension within a broader AISIA.
frameworks:
  - EU AI Act (Regulation (EU) 2024/1689)
  - ISO/IEC 42001:2023
  - NIST AI RMF 1.0
  - UK Algorithmic Transparency Recording Standard
tags:
  - human-oversight
  - eu-ai-act
  - article-14
  - iso42001
  - annex-a-9
  - nist-manage-2-3
  - override
  - biometric
  - automation-bias
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the dedicated human-oversight design artifact required by EU AI Act Article 14 for high-risk AI systems and recommended by ISO/IEC 42001:2023 Annex A controls A.9.2, A.9.3, and A.9.4 and NIST AI RMF MANAGE 2.3 for any AI system. The skill is loaded by an agent runtime that reads SKILL.md (Hermes Agent, Claude Code, Codex CLI, Cursor, Jules) and invokes the `human-oversight-designer` plugin to produce an audit-ready design.

The skill complements the `aisia-runner` plugin, which treats human-oversight as one impact dimension within a broader AI System Impact Assessment. This skill produces the standalone design with explicit ability coverage rows, per-control override evidence, biometric dual-assignment verification, training assessment, automation bias mitigations, and personnel assignments.

## Scope

**In scope.**

- EU AI Act Article 14, all five paragraphs.
- ISO/IEC 42001:2023 Annex A controls A.9.2 (Processes for responsible use), A.9.3 (Objectives for responsible use), A.9.4 (Intended use of the AI system).
- NIST AI RMF MANAGE 2.3 (mechanisms to prevent, disengage, override, or deactivate AI systems).
- UK ATRS Section Tool description, Section Impact assessment cross-references for human-oversight evidence within ATRS records.

**Out of scope.**

- Sector-specific oversight regulation (medical device safety boards, financial-services model risk committees) beyond the cross-framework citations.
- Detailed operator training curriculum design. The skill records training references and verifies the presence of curriculum and assessment evidence.
- Automated detection of automation bias in operator behaviour. The skill records design-time mitigations.
- Audit conclusions. The skill produces the design artifact a Lead Auditor evaluates.

## Framework Reference

**EU AI Act, Article 14 (Human oversight).** High-risk AI systems must be designed and developed to enable effective oversight by natural persons during use. Paragraph 1 sets the design obligation. Paragraph 2 sets the prevention-or-minimisation objective. Paragraph 3 requires oversight measures commensurate with the risks, level of autonomy, and context of use. Paragraph 4 enumerates the five abilities oversight personnel must be enabled to perform: (a) understand capacities and limitations, (b) remain aware of automation bias, (c) correctly interpret the output, (d) decide not to use or override, (e) intervene or stop. Paragraph 5 imposes a special two-person verification requirement for remote biometric identification systems.

**ISO/IEC 42001:2023.**

- Annex A, Control A.9.2 Processes for responsible use of AI systems.
- Annex A, Control A.9.3 Objectives for responsible use of AI systems.
- Annex A, Control A.9.4 Intended use of the AI system.

**NIST AI RMF 1.0.**

- MANAGE 2.3 Mechanisms are in place and applied to prevent, disengage, override, or deactivate existing AI systems.

**UK ATRS.**

- Section Tool description: documents the human role in operating the system.
- Section Impact assessment: includes the human-oversight design as evidence of mitigation.

## Operationalizable Controls

| Control | Class | Artifact | Plugin |
|---|---|---|---|
| EU AI Act Article 14(1)-(2) design and prevention objective | H | human-oversight-design | `human-oversight-designer` |
| EU AI Act Article 14(3) commensurate measures | H | human-oversight-design | `human-oversight-designer` |
| EU AI Act Article 14(4)(a) understand capacities | H | ability-row | `human-oversight-designer` |
| EU AI Act Article 14(4)(b) automation bias awareness | H | ability-row plus bias-mitigation rows | `human-oversight-designer` |
| EU AI Act Article 14(4)(c) correctly interpret output | H | ability-row | `human-oversight-designer` |
| EU AI Act Article 14(4)(d) decide not to use or override | A | override-control row | `human-oversight-designer` |
| EU AI Act Article 14(4)(e) intervene or stop | A | override-control row | `human-oversight-designer` |
| EU AI Act Article 14(5) biometric dual-assignment | A | biometric-dual-assignment-check | `human-oversight-designer` |
| ISO/IEC 42001:2023 Annex A, Control A.9.2 | H | human-oversight-design | `human-oversight-designer` |
| ISO/IEC 42001:2023 Annex A, Control A.9.3 | H | objectives section of human-oversight-design | `human-oversight-designer` |
| ISO/IEC 42001:2023 Annex A, Control A.9.4 | H | intended-use echo | `human-oversight-designer` |
| NIST AI RMF MANAGE 2.3 | A | override-control row | `human-oversight-designer` |

Class legend: A automatable, H hybrid (draft plus human review), J human judgment required.

The `human-oversight-designer` plugin produces the design artifact. The `role-matrix-generator` plugin assigns the oversight roles referenced. The `high-risk-classifier` plugin determines the risk tier that gates Article 14 applicability. The `nonconformity-tracker` and `incident-reporting` plugins consume override-exercised events at runtime.

## Output Standards

Outputs follow the AIGovOps citation format defined in [STYLE.md](../../STYLE.md):

- EU AI Act citations: `EU AI Act, Article 14, Paragraph X`.
- ISO/IEC 42001:2023 Annex A: `ISO/IEC 42001:2023, Annex A, Control A.9.X`.
- NIST AI RMF: `MANAGE 2.3`.
- UK ATRS: `UK ATRS, Section Tool description`, `UK ATRS, Section Impact assessment`.

Every emitted artifact contains a UTC `timestamp`, the `agent_signature` of the plugin that produced it, top-level `citations`, per-section `citations`, register-level `warnings`, and a `summary` block. Markdown rendering is required; CSV rendering is required for spreadsheet ingestion. No em-dashes, no emojis, no hedging language per STYLE.md.

## Limitations

- The plugin does not invent oversight measures. Missing Article 14(4) abilities surface as `REQUIRES PRACTITIONER ASSIGNMENT` placeholder rows with warnings.
- Override latency thresholds are configured for high-risk systems at 30 seconds. Domain-specific real-time decision contexts may require lower thresholds; the design artifact does not encode sector-specific tightening.
- Biometric dual-assignment checks count personnel with authoritative authority levels (`sole-authority`, `shared-authority`, `veto-authority`). Authority designation accuracy is the practitioner's responsibility.
- Operator training completion rates are recorded as input. The plugin does not verify the underlying training records.
- Automation bias mitigation effectiveness is not measured. The plugin records design-time measures.
- Cross-framework citations are sourced from the crosswalk-matrix-builder data files. Crosswalk gaps surface as crosswalk-side warnings.
