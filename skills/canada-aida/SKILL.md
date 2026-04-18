---
name: canada-aida
version: 0.1.0
description: >
  Canada AI regulatory landscape navigation skill. Canada has no single
  in-force AI law. The Artificial Intelligence and Data Act (AIDA),
  tabled as Part 3 of Bill C-27 in June 2022, is still in parliamentary
  committee and is not yet law as of the validation date. Practitioners
  operating in Canada layer PIPEDA (in force), anticipate AIDA if it
  passes, apply sectoral instruments (OSFI Guideline E-23 for
  federally-regulated financial institutions), apply provincial privacy
  law (Quebec Law 25), and consider the non-binding Voluntary Code of
  Conduct on the Responsible Development and Management of Advanced
  Generative AI Systems. This skill helps a practitioner identify which
  instruments apply and which AIGovOps artifacts satisfy each obligation.
  Scope validated on 2026-04-18. Refreshed every 90 days under the
  framework-drift playbook.
frameworks:
  - Artificial Intelligence and Data Act (AIDA, Bill C-27, Part 3)
  - Personal Information Protection and Electronic Documents Act (PIPEDA)
  - OSFI Guideline E-23 (Model Risk Management)
  - Canada Directive on Automated Decision-Making (Treasury Board)
  - Quebec Law 25 (Act to modernize legislative provisions as regards the protection of personal information)
  - Canada Voluntary Code of Conduct on Advanced Generative AI Systems (2023)
tags:
  - ai-governance
  - canada
  - aida
  - pipeda
  - osfi
  - quebec-law-25
  - voluntary-code
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill is a NAVIGATION SKILL. Canada does not have a single in-force AI law. AIDA is tabled but not passed. The Canadian AI regulatory surface as of the validation date consists of:

1. AIDA (drafting) for high-impact AI systems.
2. PIPEDA (in force) for personal information processing by private-sector organizations.
3. OSFI Guideline E-23 (effective) for model risk management at federally-regulated financial institutions.
4. Treasury Board Directive on Automated Decision-Making (effective) for federal government use of AI.
5. Quebec Law 25 (in force in stages 2022 through 2024) for Quebec-resident data and automated decision-making.
6. Canada's Voluntary Code of Conduct on the Responsible Development and Management of Advanced Generative AI Systems (September 2023, non-binding).

The skill helps a Canadian-operating practitioner identify which of these instruments applies to a specific AI system and which AIGovOps artifacts satisfy each obligation. It does not author Canada-specific plugin logic. Canada is a secondary-priority jurisdiction under `docs/jurisdiction-scope.md`, and until AIDA passes there is no single controlling text to build a dedicated plugin against.

The authoritative machine-readable summary is [`regulatory-register.yaml`](regulatory-register.yaml). That file is the ground truth for "which Canadian instruments exist and what is their current status." This SKILL.md provides the human-facing navigation logic and the cross-skill operationalization map.

**Posture.** A Canadian-operating practitioner layers PIPEDA as the privacy baseline, anticipates AIDA through gap-assessment against the current draft text, applies OSFI Guideline E-23 if the organization is a federally-regulated financial institution, applies Quebec Law 25 for Quebec residents, and optionally signs the Voluntary Code if operating in generative AI. Federal-government deployments layer the Treasury Board Directive. The skill does not issue legal advice. AIDA applicability determinations, PIPEDA thresholds, and Quebec Law 25 territorial scope each require qualified Canadian counsel.

## Scope

**In scope.** Canadian AI regulatory instruments listed in `regulatory-register.yaml` as of the validation date:

- AIDA (Bill C-27, Part 3) as tabled, with anticipated obligations for high-impact AI systems.
- PIPEDA as applied to AI systems that process personal information.
- Proposed Consumer Privacy Protection Act (CPPA, Bill C-27, Part 1) as the anticipated PIPEDA replacement.
- Treasury Board Directive on Automated Decision-Making (federal government scope only).
- OSFI Guideline E-23 (federally-regulated financial institutions only).
- Quebec Law 25 automated decision-making provisions.
- Canada Voluntary Code of Conduct on Advanced Generative AI Systems.

**Out of scope.** This skill does not provide:

- Legal advice. Canadian AI applicability analysis for a specific system requires qualified Canadian counsel, in particular for AIDA "high-impact" designation once the Act is in force, and for Quebec Law 25 extraterritorial scope.
- AIDA passage-timing predictions. The register records status as drafting with an estimated 2027-2028 effective window if the Act is passed. Practitioners should not rely on this estimate for planning.
- Province-by-province coverage beyond Quebec. Alberta's Personal Information Protection Act (PIPA) and British Columbia's PIPA operate alongside PIPEDA in their respective provinces. This skill flags the layering but does not operationalize it.
- Sector-specific financial-services regulation beyond OSFI Guideline E-23. Securities regulators (CSA), AMLATF (FINTRAC), and insurance regulators each have posture on AI use. Not in scope.
- Plugin-level operationalization. Canada is a secondary-priority jurisdiction and is also drafting-volatile on its central instrument. No Canada plugin ships at this version.

**Operating assumption.** The user organization either operates in Canada, processes personal information of Canadians at PIPEDA thresholds, deploys AI that affects Canadian residents, is a federally-regulated financial institution, is a federal government department or agency, or is a generative AI developer reaching Canadian users.

## Framework Reference

**Authoritative sources.**

- AIDA companion document (Innovation, Science and Economic Development Canada): https://ised-isde.canada.ca/site/innovation-better-canada/en/artificial-intelligence-and-data-act-aida-companion-document.
- Bill C-27 text (Parliament of Canada; AIDA is Part 3): https://www.parl.ca/DocumentViewer/en/44-1/bill/C-27.
- PIPEDA authoritative text and OPC guidance: https://www.priv.gc.ca/.
- Treasury Board Directive on Automated Decision-Making: https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai.html.
- OSFI Guideline E-23 (Model Risk Management): https://www.osfi-bsif.gc.ca/.
- Quebec Law 25 (Commission d'acces a l'information): https://www.cai.gouv.qc.ca/.
- Canada Voluntary Code of Conduct on Advanced Generative AI Systems: https://ised-isde.canada.ca/site/innovation-better-canada/en/voluntary-code-conduct-responsible-development-and-management-advanced-generative-ai-systems.

**Structure.** The Canadian AI regulatory space has four functional tiers:

1. **Privacy-rooted tier.** PIPEDA as the federal baseline for private-sector personal-information processing. Every Canadian-operating AI deployment that touches personal information touches this tier. The proposed CPPA under Bill C-27 Part 1 would replace and modernize PIPEDA when passed.
2. **Cross-cutting AI tier.** AIDA (drafting) for high-impact AI systems, expected to apply to providers and deployers. The Voluntary Code sits here as non-binding adjacent guidance for generative AI specifically.
3. **Sectoral tier.** OSFI Guideline E-23 for federally-regulated financial institutions. Treasury Board Directive on Automated Decision-Making for federal government deployments. Narrow populations; binding within scope.
4. **Provincial tier.** Quebec Law 25 for Quebec residents. Alberta and British Columbia PIPAs are substantially similar to PIPEDA for their provincial scopes. Quebec Law 25 is the most consequential provincial instrument for AI governance because of its automated decision-making notice requirement.

**Enforcement.** Primary enforcers:

- AIDA (once in force): Minister of Innovation, Science and Industry for an initial transition period, then the AIDA Commissioner once established under the regulations.
- PIPEDA: Office of the Privacy Commissioner of Canada (OPC). Complaint-driven and periodic audits.
- OSFI Guideline E-23: OSFI through its supervisory review program for federally-regulated financial institutions.
- Treasury Board Directive: Treasury Board of Canada Secretariat oversight; binding on federal departments under the Financial Administration Act.
- Quebec Law 25: Commission d'acces a l'information du Quebec (CAI). Administrative penalties and civil actions available.
- Voluntary Code: no enforcement. Signatories self-report.

**Related frameworks and cross-references.** The Canadian instruments overlap with:

- ISO/IEC 42001:2023 for the management-system backbone. AIDA's draft risk-management obligations align directly with ISO 42001 Clause 6.1.2 and Annex A risk-treatment controls.
- NIST AI RMF 1.0 MAP, MEASURE, and MANAGE subcategories as the functional analogue to AIDA's risk management, measurement, and mitigation duties.
- EU AI Act Chapter III high-risk obligations and Article 27 FRIA. AIDA's high-impact designation functionally parallels EU high-risk categorization. Artifacts produced in `dual` or `eu-ai-act` mode generally cover AIDA's anticipated risk-assessment surface.
- Colorado AI Act and CPPA ADMT regulations for the consumer-facing significant-decision surface. Quebec Law 25's automated decision-making notice requirement aligns closely with the CPPA ADMT pre-use notice duty.

## Operationalizable Controls

This skill is navigation-focused. It does not define its own plugins. The Tier 1 operationalizations are cross-references to existing plugins with Canadian citations added.

### T1.1 AIDA anticipated risk management

Class: H. Artifact: `AISIA-section` and `risk-register-row` with AIDA citations. Leverage: H. Consumer: `plugins/aisia-runner` and `plugins/risk-register-builder` with caller-supplied AIDA citations.

**Requirement summary.** AIDA (as drafted) requires persons responsible for high-impact AI systems to establish measures to identify, assess, and mitigate risks of harm or biased output; to monitor compliance with those measures; and to keep records. The draft aligns with ISO 42001 Clause 6.1.2 and NIST AI RMF MAP-MANAGE.

**Plugin cross-reference.** The `aisia-runner` plugin produces the AI-system-impact-assessment artifact. The `risk-register-builder` plugin produces the risk-register artifact. For Canadian mode, the caller adds `Canada AIDA (Bill C-27, Part 3), Section <n>` citations to the `citations` field of each record. The existing ISO 42001 and NIST content covers the substantive backbone. Once AIDA passes and the implementing regulations issue, this skill will update to cite the codified section numbers.

### T1.2 AIDA anticipated transparency and record-keeping

Class: A. Artifact: `audit-log-entry` and `data-register-row` with AIDA citations. Leverage: H. Consumer: `plugins/audit-log-generator` and `plugins/data-register-builder`.

**Requirement summary.** AIDA (as drafted) requires publication of a plain-language description of the high-impact AI system, its intended use, the types of content it generates or decisions it makes, and the measures taken to identify and mitigate risks. Records must be retained to demonstrate compliance.

**Plugin cross-reference.** The `audit-log-generator` records the publication event and the description reference. The `data-register-builder` produces the machine-readable surface of the description. Canadian citation format added to both.

### T1.3 PIPEDA personal information handling

Class: A. Artifact: `data-register-row` with PIPEDA citations. Leverage: H. Consumer: `plugins/data-register-builder`.

**Requirement summary.** PIPEDA requires private-sector organizations that collect, use, or disclose personal information in the course of commercial activities to obtain meaningful consent, limit collection to identified purposes, safeguard the information, and provide access on request.

**Plugin cross-reference.** The `data-register-builder` plugin produces the data-inventory surface. For PIPEDA mode, the caller adds `PIPEDA, Section <n>` citations. Most organizations already run PIPEDA compliance through an existing privacy program; AIGovOps extends coverage for AI-specific processing (training-data sources, inference logs, model-derived personal information).

### T1.4 OSFI Guideline E-23 model risk management

Class: H. Artifact: `risk-register-row` and `metrics-report` with OSFI E-23 citations. Leverage: H. Consumer: `plugins/risk-register-builder` and `plugins/metrics-collector`.

**Requirement summary.** OSFI Guideline E-23 requires federally-regulated financial institutions (banks, insurers, trust and loan companies) to implement a model risk management framework covering model identification, tiering by risk, independent validation, ongoing monitoring, and governance.

**Plugin cross-reference.** The `risk-register-builder` produces the model-inventory risk surface. The `metrics-collector` produces the ongoing-monitoring metrics surface. For OSFI mode, the caller adds `OSFI Guideline E-23, Paragraph <n>` citations. Applies only within the federally-regulated-financial-institution scope.

### T1.5 Quebec Law 25 automated decision-making notice

Class: A. Artifact: `audit-log-entry` with Quebec Law 25 citations. Leverage: M. Consumer: `plugins/audit-log-generator`.

**Requirement summary.** Quebec Law 25 requires an organization that uses personal information to render a decision based exclusively on automated processing to inform the individual of the decision and of the right to obtain the information used to render the decision, the reasons and principal factors that led to the decision, and the right to have the personal information corrected and to submit observations for review.

**Plugin cross-reference.** The `audit-log-generator` records the notice-delivery event. The notice text itself is a legal drafting responsibility outside the plugin. Quebec citation format added.

### T1.6 Voluntary Code self-assessment

Class: A. Artifact: `gap-assessment` with target framework `ca-voluntary-code`. Leverage: M. Consumer: `plugins/gap-assessment`.

**Requirement summary.** The Canada Voluntary Code of Conduct on Advanced Generative AI Systems (September 2023) sets six principles: accountability, safety, fairness and equity, transparency, human oversight and monitoring, validity and robustness. Non-binding. Signatories commit to measures against each principle.

**Plugin cross-reference.** The `gap-assessment` plugin produces a gap-analysis artifact against the six principles when invoked with `target_framework="ca-voluntary-code"`. Canadian citation format added.

### T1.7 Treasury Board Directive on Automated Decision-Making

Class: A. Artifact: `AISIA-section` with Treasury Board Directive citations. Leverage: M. Consumer: `plugins/aisia-runner`.

**Requirement summary.** The Directive on Automated Decision-Making binds federal departments to complete an Algorithmic Impact Assessment (AIA) for automated decision systems, apply proportional controls by impact level, provide notice, and maintain audit trails.

**Plugin cross-reference.** The `aisia-runner` produces the AI-system-impact-assessment artifact. For federal deployments, the caller maps the AIGovOps AISIA fields onto the Government of Canada AIA questionnaire. Applies only to federal government deployments.

### Tier 2

Tier 2 includes:

1. Provincial PIPAs (Alberta, British Columbia) where Canadian-operating organizations may need parallel compliance. Substantially similar to PIPEDA for the AI-processing surface; the baseline privacy program covers it.
2. CPPA if Bill C-27 Part 1 is passed. Register entry tracks its status. When CPPA replaces PIPEDA, the T1.3 mapping updates.
3. Sector-adjacent financial-services guidance (CSA, FINTRAC, AMF Quebec). Tracked in the register without per-instrument operationalization.

## Output Standards

Outputs produced under this skill must meet the certification-grade quality bar in [STYLE.md](../../STYLE.md). Specifically:

- AIDA (draft): `Canada AIDA (Bill C-27, Part 3), Section <n>`.
- AIDA (once in force): `AIDA Section <n>`.
- PIPEDA: `PIPEDA, Section <n>`.
- Consumer Privacy Protection Act (proposed): `CPPA (Bill C-27, Part 1), Section <n>`.
- OSFI Guideline E-23: `OSFI Guideline E-23, Paragraph <n>`.
- Treasury Board Directive on Automated Decision-Making: `Canada Directive on Automated Decision-Making, Subsection <n>`.
- Quebec Law 25: `Quebec Law 25, Section <n>`.
- Canada Voluntary Code: `Canada Voluntary AI Code (2023), Principle <n>`.
- No em-dashes (U+2014).
- No emojis.
- No hedging phrases (see STYLE.md prohibited list).
- Where applicability is contested, the output states `Requires human determination.` rather than hedging.

## Limitations

- **High maintenance. AIDA is still in drafting.** The skill is tagged high-maintenance because AIDA parliamentary progress requires quarterly tracking. The framework-drift playbook refreshes `regulatory-register.yaml` every 90 days. When AIDA receives Royal Assent the register updates to effective status and the citation format drops the `(Bill C-27, Part 3)` qualifier.
- **No Canada plugin.** Canada is secondary-priority per `docs/jurisdiction-scope.md`, and AIDA is not yet in force. No Canada-specific plugin exists. Practitioners use existing plugins with Canadian citations added.
- **AIDA passage timing is unknown.** The register records a 2027-2028 estimated effective window if the Act is passed. The estimate is not authoritative. Practitioners doing gap-assessment against AIDA must treat the draft as volatile; committee amendments have shifted the definition of high-impact AI system, the enforcement regime, and the risk-management duty in successive revisions.
- **Provincial coverage is Quebec-only in this skill.** Alberta and British Columbia PIPAs operate on substantially-similar privacy terrain but are not operationalized row-by-row here. Practitioners in those provinces should treat PIPEDA mappings as a baseline with province-specific counsel review.
- **OSFI Guideline E-23 is narrow.** It applies only to federally-regulated financial institutions. Provincially-regulated institutions (credit unions in most provinces, insurance companies chartered provincially) follow provincial regulator posture, which varies.
- **Voluntary Code is not binding.** Signing is marketing-adjacent. Regulators may reference the Code as an expectation benchmark, but non-signatories are not in violation of any law by not signing.
- **Treasury Board Directive binds only federal government.** Private-sector organizations are not within scope.

## Navigation flow

For a Canadian-operating practitioner determining applicability, the decision tree is:

1. **Is the organization a federal government department or agency?** If yes, the Treasury Board Directive on Automated Decision-Making applies. Proceed to T1.7. Continue through the rest of the tree for any adjacent privacy or sectoral exposure.
2. **Is the organization a federally-regulated financial institution (bank, insurer, trust or loan company)?** If yes, OSFI Guideline E-23 applies. Proceed to T1.4.
3. **Does the organization collect, use, or disclose personal information in the course of commercial activities in Canada?** If yes, PIPEDA applies. Proceed to T1.3. Also check: do operations touch Quebec residents? If yes, Quebec Law 25 applies. Proceed to T1.5.
4. **Is the AI system likely to be designated a high-impact AI system under AIDA once in force?** Draft criteria include use in employment, provision of services, moderation of content, biometric processing, and health or safety. If yes, begin AIDA gap-assessment now. Proceed to T1.1 and T1.2. Treat as anticipatory; not a current legal obligation.
5. **Is the organization a developer or deployer of advanced generative AI systems operating in Canada?** If yes, consider signing the Voluntary Code and run a gap-assessment against its six principles. Proceed to T1.6.
6. **Is the AI system making decisions based exclusively on automated processing about a Quebec resident?** If yes, the Quebec Law 25 automated decision-making notice is mandatory. Proceed to T1.5.

Multiple tiers can apply to the same system. Layer, do not substitute. A federally-regulated bank deploying a generative AI system for Quebec residents layers OSFI Guideline E-23, PIPEDA, Quebec Law 25, the Voluntary Code if signed, and prospectively AIDA.

## Jurisdiction

- Canadian residents and Canadian personal information subjects.
- Organizations that collect, use, or disclose personal information in the course of commercial activities in Canada (PIPEDA test).
- Organizations that offer AI products or services to Canadians or deploy AI systems affecting Canadians (AIDA anticipated extraterritorial reach).
- Federally-regulated financial institutions (OSFI scope).
- Federal government departments and agencies (Treasury Board Directive scope).
- Organizations processing personal information of Quebec residents (Quebec Law 25 scope; extraterritorial in practice).

AIDA's extraterritorial reach, once in force, is expected to parallel PIPEDA's: the test is whether the AI system has a real and substantial connection to Canada, not whether the provider is physically located in Canada.

## Maintenance

This skill is tagged high-maintenance. The framework-drift playbook review cadence is every 90 days. Triggers for an off-cycle refresh:

1. AIDA parliamentary progress (committee vote, third reading, Royal Assent, regulation-making notice).
2. Material OSFI Guideline E-23 amendment.
3. CPPA (Bill C-27 Part 1) passage or material amendment.
4. Quebec Law 25 regulation-making or CAI guidance on automated decision-making.
5. New Voluntary Code signatory tranche or code revision.

The register (`regulatory-register.yaml`) is the first file updated in any refresh. The SKILL.md follows only when the navigation flow or operationalization mapping changes.

## Non-goals

- The skill does not substitute for a PIPEDA compliance review by qualified privacy counsel.
- The skill does not substitute for OSFI supervisory engagement or internal model validation at federally-regulated financial institutions.
- The skill does not predict AIDA passage timing. Practitioners who rely on the 2027-2028 estimate for contractual commitments do so at their own risk.
- The skill does not cover Canadian securities-law AI posture (CSA staff notices) or AML AI posture (FINTRAC guidance).
