---
name: california-ai
version: 0.1.0
description: >
  California AI regulatory landscape navigation skill. California has
  no single controlling AI law. This skill helps practitioners
  identify which instruments apply to a specific AI system, using the
  machine-readable regulatory-register.yaml as the source of truth.
  Instruments covered include the CPPA Automated Decisionmaking
  Technology (ADMT) regulations, CCPA / CPRA as applied to AI, SB 942
  (California AI Transparency Act), AB 2013 (training data
  transparency), AB 1008, SB 1001, AB 1836, and the vetoed SB 1047.
  Scope validated on 2026-04-18. Refreshed every 90 days under the
  framework-drift playbook.
frameworks:
  - California Privacy Rights Act (CPRA) as amending CCPA
  - CPPA Automated Decisionmaking Technology regulations
  - California AI Transparency Act (SB 942)
  - California AB 2013 (Training Data Transparency)
tags:
  - ai-governance
  - california
  - us-state-ai
  - admt
  - cppa
  - cpra
  - generative-ai-transparency
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill is a NAVIGATION SKILL. California does not have a single controlling AI law. It has a constellation of overlapping obligations that a California-operating practitioner must layer based on the specific AI system and operating context. The skill helps the practitioner identify which instruments apply, in what combination, and which AIGovOps artifacts satisfy each obligation. It does not author California-specific plugin logic; California is a secondary-priority jurisdiction under `docs/jurisdiction-scope.md` and one plugin per state is not feasible.

The authoritative machine-readable summary is [`regulatory-register.yaml`](regulatory-register.yaml). That file is the ground truth for "which instruments exist and what is their current status." This SKILL.md provides the human-facing navigation logic and the cross-skill operationalization map.

**Posture.** A California-operating practitioner must layer CPPA ADMT regulations, CCPA / CPRA, SB 942 if generative AI content is distributed in California, AB 2013 if generative AI is trained for California distribution, and applicable sector-specific rules. The skill does not issue legal advice; specific applicability determinations require qualified California counsel, particularly for cross-border scope analysis and for the CPPA ADMT "significant decision" characterization.

## Scope

**In scope.** California AI regulatory instruments listed in `regulatory-register.yaml` as of the validation date:

- CPPA Automated Decisionmaking Technology (ADMT) regulations.
- CCPA as amended by CPRA, applied to AI profiling and automated decision-making.
- SB 942 (California AI Transparency Act).
- AB 2013 (training data transparency).
- AB 1008 (personal information in AI training data).
- SB 1001 (bot disclosure).
- AB 1836 (digital replicas of deceased personalities).
- SB 1047 (frontier AI safety) noted as VETOED and not applicable.
- California Attorney General AI guidance hub.
- Proposed 2025-2026 bills under active tracking.

**Out of scope.** This skill does not provide:

- Legal advice. California applicability analysis for a specific system requires qualified California counsel.
- Federal AI law analysis (NIST AI RMF, EEOC guidance, FTC consumer protection posture on AI, sectoral federal rules such as HIPAA or FCRA as applied to AI). Federal obligations operate alongside California law; the NIST skill covers the voluntary federal framework.
- Plugin-level operationalization. California is a secondary-priority jurisdiction; no California plugin ships at this version. Practitioners use existing AIGovOps plugins with California citations added to the `citations` fields of artifact records.
- Tracking of proposed bills beyond the register-level summary. The `framework-drift` playbook refreshes the register every 90 days; intra-quarter bill movement is not captured.

**Operating assumption.** The user organization either operates in California, processes California resident data at CCPA thresholds, deploys AI in California, or offers generative AI content to California users. Organizations outside California get crosswalk-only utility.

## Framework Reference

**Authoritative sources.**

- CPPA regulations (including ADMT): https://cppa.ca.gov/regulations/.
- California Civil Code, Part 4, Division 3, Title 1.81.5 (CCPA as amended): https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division=3.&part=4.&lawCode=CIV&title=1.81.5.
- California legislative information (for SB 942, AB 2013, AB 1008, SB 1001, AB 1836, SB 1047, and proposed bills): https://leginfo.legislature.ca.gov/.
- California Attorney General AI hub: https://oag.ca.gov/ai.

**Structure.** The California AI regulatory space has four functional tiers:

1. **Privacy-rooted tier.** CCPA / CPRA as the baseline, with the CPPA ADMT regulations as the AI-specific operationalization. Every California-operating AI deployment touches this tier.
2. **Generative-AI transparency tier.** SB 942 (watermarking and provenance for generative content) and AB 2013 (training data documentation) for generative AI providers and developers. Narrow in population; critical for GenAI vendors.
3. **Domain-specific tier.** AB 1836 (digital replicas of deceased personalities), SB 1001 (bot disclosure for commercial and electoral contexts). Narrow applicability; triggered by specific deployment contexts.
4. **Enforcement and proposed tier.** California Attorney General guidance, periodic enforcement letters, and the 2025-2026 proposed-bill pipeline. Non-binding but enforcement-relevant.

**Enforcement.** Primary enforcers:

- CPPA: CCPA / CPRA, including the ADMT regulations.
- California Attorney General: statutory civil rights, consumer protection, and cross-cutting AI application of existing law.
- California Privacy Protection Agency and California Department of Justice can coordinate on ADMT enforcement.
- Private right of action exists under CCPA / CPRA for enumerated data-breach fact patterns; ADMT compliance is agency-enforced.

**Related frameworks and cross-references.** The California instruments overlap with:

- EU AI Act high-risk obligations (Chapter III, Articles 9-15) and the Article 27 FRIA. A California significant-decision AI system will often also be an EU Annex III high-risk use case. Artifacts produced for one (AISIA with FRIA content, data register with Annex IV coverage) generally satisfy the other.
- NIST AI RMF MAP, MEASURE, and MANAGE subcategories for the risk-management backbone.
- ISO/IEC 42001:2023 Annex A controls for the management-system foundation.
- Colorado AI Act (SB 205): broader scope than California's current per-topic rules; the two state regimes will interoperate awkwardly for multi-state deployments.
- NYC Local Law 144: LL144 is narrower (employment AEDT only) but stricter in one respect (mandatory independent audit); a California AI system used for NYC employment decisions faces both.

## Operationalizable Controls

This skill is navigation-focused; it does not define its own plugins. The Tier 1 operationalizations are cross-references to existing plugins with California citations added.

### T1.1 Automated decision-making risk assessment (CPPA ADMT)

Class: H. Artifact: `AISIA-section` with CPPA ADMT citations. Leverage: H. Consumer: `plugins/aisia-runner` with caller-supplied California citations.

**Requirement summary.** The CPPA ADMT regulations require covered businesses that use ADMT for significant decisions about California residents to perform a risk assessment, provide pre-use notice, honor access requests, and provide an opt-out in most contexts. "Significant decisions" include employment, housing, credit, education access, and healthcare access.

**Plugin cross-reference.** The `aisia-runner` plugin produces the risk-assessment artifact. For California mode, the caller adds `CCPA Regulations (CPPA), Section <section>` citations to the `citations` field of the AISIA record. California-specific dimensions to cover: the enumerated significant-decision categories, the opt-out mechanism, the human-review option, and the risk-assessment retention period per the applicable CPPA section.

### T1.2 Training data documentation (AB 2013)

Class: A. Artifact: `data-register-row` with AB 2013 citations. Leverage: H. Consumer: `plugins/data-register-builder`.

**Requirement summary.** AB 2013 requires developers of generative AI systems made available to Californians to publish, on the developer's website, documentation describing training data sources, purposes, and protection measures.

**Plugin cross-reference.** The `data-register-builder` plugin produces the backbone of the required disclosure. For AB 2013 mode, the caller uses the plugin's EU AI Act Article 10 field set (Annex IV data-governance documentation) and adds California citations.

### T1.3 Generative content provenance (SB 942)

Class: A and H. Artifact: `audit-log-entry` plus deployment-time provenance metadata. Leverage: M. Consumer: `plugins/audit-log-generator` with California citations.

**Requirement summary.** SB 942 requires covered generative AI providers to make a free AI-detection tool available and to include manifest and latent provenance disclosures on generated content.

**Plugin cross-reference.** The audit-log-generator records the provenance-insertion event. Deployment-time watermarking is an operational responsibility outside the plugin; the plugin records the fact that watermarking was applied and the mechanism reference.

### T1.4 Bot disclosure for commercial and electoral contexts (SB 1001)

Class: A. Artifact: `role-matrix` with SB 1001 citations. Leverage: L. Consumer: `plugins/role-matrix-generator`.

**Requirement summary.** SB 1001 requires disclosure when an automated bot is used to communicate with Californians to incentivize a commercial transaction or influence an election.

**Plugin cross-reference.** The role-matrix-generator encodes the bot-disclosure responsibility in the deployer's role matrix. The actual disclosure is an operational implementation in the conversational interface.

### T1.5 Digital replica consent (AB 1836)

Class: J. Artifact: `AISIA-section` with AB 1836 citations. Leverage: L. Consumer: `plugins/aisia-runner`.

**Requirement summary.** AB 1836 requires consent of the estate for use of a deceased personality's likeness in an AI-generated digital replica.

**Plugin cross-reference.** The aisia-runner records the consent determination. The determination itself is legal judgment and is out of scope for automation.

### Tier 2

Tier 2 operationalizations are the non-ADMT CCPA / CPRA obligations as they apply to AI (profiling disclosures, sensitive-personal-information limits, AI-related right-to-know fulfillment). These are already covered by the organization's baseline privacy program; the California AI skill does not duplicate that coverage. Track:

1. AB 1008 interaction with AB 2013: personal information in training data is subject to CCPA consumer rights. Organizations must reconcile AB 2013's publication obligation with CCPA's deletion and correction rights.
2. CA AG guidance updates. These are enforcement posture signals, not new rulemaking, but they shape practical compliance.
3. The 2025-2026 proposed-bill pipeline. See `regulatory-register.yaml` proposed-2025-2026 entry.

## Output Standards

Outputs produced under this skill must meet the certification-grade quality bar in [STYLE.md](../../STYLE.md). Specifically:

- CPPA ADMT citations: `CCPA Regulations (CPPA), Section <section>`.
- CCPA / CPRA statutory citations: `California Civil Code, Section 1798.<section>`.
- California Business and Professions Code citations (SB 942, AB 2013): `California Business and Professions Code, Section <section>`.
- California Attorney General guidance: `California Attorney General Guidance (YYYY-MM-DD)`.
- No em-dashes (U+2014).
- No emojis.
- No hedging phrases (see STYLE.md prohibited list).
- Where applicability is contested, the output states `Requires human determination.` rather than hedging.

## Limitations

- **High maintenance.** This skill is tagged high-maintenance because California AI law evolves rapidly. The `framework-drift` playbook refreshes the `regulatory-register.yaml` every 90 days. Between refreshes, newly signed or amended legislation is not reflected.
- **No California plugin.** California is secondary-priority per `docs/jurisdiction-scope.md`. No California-specific plugin exists. Practitioners use the existing plugins with California citations added.
- **Applicability is context-dependent.** "Covered business" under CCPA, "developer" under AB 2013, and "significant decision" under CPPA ADMT each have specific statutory and regulatory tests. The skill points at those tests; it does not apply them to a specific factual scenario.
- **Enforcement posture changes.** The California Attorney General's enforcement priorities shift with the administration. Operational compliance posture should account for the current AG guidance, not historical guidance.
- **Federal pre-emption is unresolved in multiple areas.** Several California instruments face pre-emption arguments; the skill does not resolve pre-emption questions.
- **SB 1047 was vetoed.** The register records this explicitly. A successor frontier-safety bill is under discussion; when it becomes law, a new register entry will replace the SB 1047 entry.

## Navigation flow

For a practitioner determining applicability, the decision tree is:

1. **Does the system make automated decisions with legal or significant effects on California residents?** If yes, the CPPA ADMT regulations apply. Proceed to T1.1.
2. **Is the system a generative AI system trained on third-party or scraped data and made available to Californians?** If yes, AB 2013 applies. Proceed to T1.2.
3. **Does the system generate AI content distributed to Californians?** If yes, SB 942 watermarking and provenance applies. Proceed to T1.3.
4. **Is the system an automated bot used for commercial transactions or election influence?** If yes, SB 1001 disclosure applies. Proceed to T1.4.
5. **Does the system generate a digital replica of a deceased personality?** If yes, AB 1836 consent applies. Proceed to T1.5.
6. **Does the system process personal information of California residents at CCPA thresholds?** If yes, CCPA / CPRA baseline obligations apply, including AI-specific overlays via AB 1008. Use the organization's existing privacy program artifacts.
7. **Has the California AG issued guidance relevant to your sector?** Read and incorporate.

Multiple tiers can apply to the same system. Layer, do not substitute.

## Jurisdiction

- California residents (natural persons).
- Businesses that meet CCPA covered-business thresholds regardless of physical location.
- Businesses that offer goods, services, or AI content to California residents.
- Businesses that deploy ADMT for significant decisions about California residents, regardless of the business's own location.

The extraterritorial reach is significant. A business outside California that offers a hiring AI to a California-operating customer may face direct CPPA ADMT obligations for the California employment decisions its customer makes with the tool.

## Maintenance

This skill is tagged high-maintenance. The framework-drift playbook review cadence is every 90 days. Triggers for an off-cycle refresh:

1. New California AI bill signed into law.
2. Material CPPA ADMT rulemaking amendment.
3. Material California AG AI guidance letter.
4. Federal pre-emption ruling affecting a California AI instrument.

The register (`regulatory-register.yaml`) is the first file updated in any refresh. The SKILL.md follows only when the navigation flow or operationalization mapping changes.
