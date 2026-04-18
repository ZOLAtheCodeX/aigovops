---
name: colorado-ai-act
version: 0.1.0
description: >
  Colorado AI Act (Senate Bill 24-205) governance skill. Operationalizes the
  developer and deployer duties of reasonable care in section 6-1-1702 and
  section 6-1-1703, the impact assessment content mandated in section
  6-1-1703(3), the consumer notice and appeal rights in section 6-1-1703(4),
  the Attorney General enforcement mechanism in section 6-1-1706, and the
  affirmative defense for entities substantively following a recognized AI
  risk management framework in section 6-1-1706(4). Authoritative text
  published at https://leg.colorado.gov/bills/sb24-205. Validated against
  the signed session-law text on 2026-04-18.
frameworks:
  - Colorado Senate Bill 24-205 (Colorado AI Act)
tags:
  - ai-governance
  - colorado-ai-act
  - sb-205
  - us-state
  - consumer-protection
  - algorithmic-discrimination
  - impact-assessment
  - consequential-decisions
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes Colorado Senate Bill 24-205 (the Colorado AI Act) for developers and deployers of high-risk artificial intelligence systems that make, or are a substantial factor in making, consequential decisions concerning Colorado consumers. The bill was signed on 17 May 2024 and takes effect on 1 February 2026. As of the skill validation date (18 April 2026), the core requirements are in force.

Colorado is the first US state to pass comprehensive AI consumer-protection legislation imposing duties on both developers and deployers. The Act draws structural elements from the EU AI Act (risk-tier framing, impact assessment, developer/deployer separation) but operates within the Colorado Consumer Protection Act enforcement framework under exclusive Attorney General authority.

The skill is companion to `iso42001`, `nist-ai-rmf`, and `eu-ai-act` in this catalogue. Section 6-1-1706(4) provides an affirmative defense to enforcement when an actor substantively follows a nationally or internationally recognized AI risk management framework designated by the Attorney General; NIST AI RMF 1.0 and ISO/IEC 42001:2023 are the two frameworks AIGovOps operationalizes that are expected to qualify. Organizations already running the ISO 42001 or NIST AI RMF programs get significant leverage on Colorado compliance from their existing artifacts.

## Scope

**In scope.** Colorado Senate Bill 24-205 as enacted, including:

- Section 6-1-1701: Definitions, including `high-risk artificial intelligence system`, `consequential decision`, `algorithmic discrimination`, `developer`, `deployer`, `consumer`.
- Section 6-1-1702: Developer duties of reasonable care, documentation, public statements, and Attorney General and deployer disclosure.
- Section 6-1-1703: Deployer duties including risk management policy and program, impact assessment, consumer notice, adverse-decision explanation, and consumer right to appeal.
- Section 6-1-1704: Exemptions for specified entities (research context, small deployers, systems already subject to specified federal regimes).
- Section 6-1-1705: Interaction with other laws.
- Section 6-1-1706: Attorney General enforcement, rulemaking authority, and affirmative defense for entities following a recognized AI risk management framework.
- Section 6-1-1707: Applicability and effective date (1 February 2026).

**Out of scope.** This skill does not provide:

- Legal advice. The Act application to a specific organization, system, or decision requires qualified Colorado counsel. This includes determination of whether the AI system is a "substantial factor" in a consequential decision per section 6-1-1701(9), whether an affirmative defense is available under section 6-1-1706(4), and scope analysis for multi-state deployers.
- Attorney General rule text. The Attorney General has rulemaking authority under section 6-1-1706; implementing rules, once finalized, will require a skill update.
- Sector-specific cross-regulation. Financial, health, insurance, and employment regulators have overlapping authority; this skill covers the Act, not sectoral overlays.

**Jurisdictional scope.** The Act applies to developers and deployers that do business in Colorado or offer services to Colorado residents. Applicability is territorial (Colorado residents and Colorado-operating businesses) with an affirmative defense for entities that substantively follow a recognized AI risk management framework per section 6-1-1706(4). AIGovOps treats NIST AI RMF 1.0 and ISO/IEC 42001:2023 as the two most likely Attorney-General-designated frameworks. Confirm designation status with counsel before relying on the affirmative defense.

**Operating assumption.** The user organization either develops or deploys (or both) an AI system that makes, or is a substantial factor in making, a consequential decision as defined in section 6-1-1701. For organizations not within scope, the skill provides crosswalk-only utility (Colorado SB 205 language for communication with Colorado counterparties).

## Framework Reference

**Authoritative source.** Colorado Senate Bill 24-205, Concerning Consumer Protections in Interactions with Artificial Intelligence Systems, signed by Governor Jared Polis on 17 May 2024, Chapter 198, Session Laws of Colorado 2024. Codified at Colorado Revised Statutes, Title 6 (Consumer and Commercial Affairs), Article 1 (Consumer Protection), Part 17 (Artificial Intelligence). Authoritative text: https://leg.colorado.gov/bills/sb24-205.

**Structure.**

- Section 6-1-1701: Definitions.
- Section 6-1-1702: Developer duty of reasonable care.
- Section 6-1-1703: Deployer duty of reasonable care.
- Section 6-1-1704: Exemptions.
- Section 6-1-1705: Relationship to other laws.
- Section 6-1-1706: Attorney General enforcement and affirmative defense.
- Section 6-1-1707: Effective date.

**Key definitions (section 6-1-1701).**

- `high-risk artificial intelligence system`: an AI system that, when deployed, makes, or is a substantial factor in making, a consequential decision.
- `consequential decision`: a decision that has a material legal or similarly significant effect on the provision, denial, or cost or terms of any of: education enrollment or opportunity, employment or employment opportunity, financial or lending service, essential government service, health-care service, housing, insurance, or legal service.
- `algorithmic discrimination`: any condition in which the use of an AI system results in unlawful differential treatment or impact that disfavors an individual or group on the basis of a classification protected under state or federal law.
- `developer`: a person doing business in Colorado that develops or intentionally and substantially modifies an AI system.
- `deployer`: a person doing business in Colorado that deploys a high-risk AI system.
- `consumer`: an individual who is a Colorado resident.

**Enforcement.** Exclusive enforcement by the Colorado Attorney General under section 6-1-1706. Violations constitute a deceptive trade practice under the Colorado Consumer Protection Act. No private right of action. Attorney General has rulemaking authority.

**Affirmative defense.** Section 6-1-1706(4) provides an affirmative defense to enforcement when the actor discovers and cures a violation as a result of: (a) feedback from a deployer or internal testing, or (b) adherence to the latest published version of a nationally or internationally recognized risk management framework that is designated in rules by the Attorney General. NIST AI RMF 1.0 and ISO/IEC 42001:2023 are the leading candidates for designation; final designation is pending rulemaking.

**Related frameworks.**

- ISO/IEC 42001:2023: strong operationalization overlap across Clause 6.1 (risk assessment), Clause 8.2 (AI system impact assessment), Clause 9 (performance evaluation), Annex A Controls A.2-A.10 (governance, risk treatment, data, transparency).
- NIST AI RMF 1.0: overlap across GOVERN (policy, accountability), MAP (context, impact), MEASURE (testing, bias), MANAGE (risk response, incidents).
- EU AI Act: structural parallel on developer/deployer (provider/deployer) split, impact assessment, consumer transparency. Colorado's scope is narrower (consumer-protection framing; no prohibited-practices tier; no conformity-assessment regime; no GPAI treatment).

## Operationalizable Controls

One Tier 1 operationalization is detailed below, consumed by the dedicated `colorado-ai-act-compliance` plugin. Additional operationalizations from `iso42001` and `nist-ai-rmf` skills are reusable under the affirmative-defense pathway.

### T1.1 Developer and deployer compliance record

Class: H. Artifact: `compliance-record` with Colorado SB 205 citations. Leverage: H. Consumer: `plugins/colorado-ai-act-compliance`.

**Requirement summary.** Section 6-1-1702 imposes on developers a duty of reasonable care to protect consumers from known or reasonably foreseeable risks of algorithmic discrimination; a duty to provide deployer documentation covering intended uses, known harmful or inappropriate uses, training data summary, data governance, evaluation, and post-deployment monitoring support; a duty to publish a public statement on system types and discrimination risk management; and a duty to disclose discovered algorithmic discrimination to the Attorney General and known deployers within 90 days. Section 6-1-1703 imposes on deployers a parallel duty of reasonable care; a duty to implement a risk management policy and program; a duty to complete an impact assessment before deployment, annually thereafter, and within 90 days of intentional and substantial modification; a duty to provide consumer notice when an AI system is used to make or be a substantial factor in a consequential decision; a duty to disclose, on adverse decisions, the principal reasons and the degree of AI contribution; and a duty to provide a consumer appeal for human review where technically feasible.

**Plugin contract.** The `colorado-ai-act-compliance` plugin accepts `actor_role` (developer, deployer, both), a `system_description` dict, and a list of `consequential_decision_domains` drawn from section 6-1-1701(3). It emits a structured record with applicability-flagged obligations, a documentation checklist, and a citation map. Warnings surface content gaps rather than fatal errors, consistent with the plugin-author contract.

**Auditor acceptance criteria.**

- For developers: the emitted record enumerates all six section 6-1-1702 obligations and the developer documentation checklist items under section 6-1-1702(2). All citations match `Colorado SB 205, Section <section>`.
- For deployers: the emitted record enumerates all eight section 6-1-1703 obligations, the seven impact assessment content items under section 6-1-1703(3), and asserts consumer notice and appeal requirements under section 6-1-1703(4).
- Non-high-risk paths emit an explicit confirmation warning rather than silently producing an empty record.

### Tier 2

Tier 2 operationalizations are lower-frequency. Abbreviated guidance; full plugin treatment as user demand confirms.

1. **Algorithmic discrimination incident log (section 6-1-1702(4), 6-1-1703(6)).** Developer and deployer disclosure to the Attorney General within 90 days. Cross-reference: `plugins/audit-log-generator` can log the disclosure event; a future rendering mode may add `framework: colorado-sb-205`.
2. **Impact assessment-to-risk-register linkage.** Impact assessment outputs feed the deployer risk management program. Cross-reference: `plugins/risk-register-builder` rows can carry Colorado SB 205 Section 6-1-1703(2) citations alongside ISO or NIST citations in a future dual or triple mode.
3. **Affirmative-defense evidence package.** An evidence bundle demonstrating substantive adherence to NIST AI RMF or ISO 42001 for section 6-1-1706(4) purposes. Cross-reference: combine `plugins/gap-assessment` (framework gap view), `plugins/soa-generator` (Statement of Applicability), and `plugins/audit-log-generator` (control-implementation events).

### Tier 3

Judgment-bound provisions. This skill is prescriptive; the plugin does not attempt to automate.

- Section 6-1-1701(9) "substantial factor" determination in contested fact patterns.
- Section 6-1-1704 exemption eligibility for specific entities.
- Section 6-1-1706(4) affirmative-defense qualification, including whether specific implementation is "substantive."
- Interaction with federal regimes (HIPAA, FCRA, ECOA, Title VII, ADA, GLBA) and with Colorado sector-specific regulators.

## Output Standards

All outputs produced by this skill, or by `colorado-ai-act-compliance` in the default mode, conform to the output standards defined in the [iso42001 skill Output Standards section](../iso42001/SKILL.md). The following Colorado-specific additions apply.

**Citation format.** Per [STYLE.md](../../STYLE.md): `Colorado SB 205, Section <section>` (for example `Colorado SB 205, Section 6-1-1703(3)`). Sub-paragraph references use parentheses as in the codified text (for example `Section 6-1-1703(4)(b)`). Short-form references `SB 205 s. 6-1-1703(3)` are acceptable in tabular contexts.

**Effective-date annotation.** Outputs generated before 1 February 2026 carry an explicit "planning; effective 1 February 2026" annotation. Outputs generated on or after that date do not require the annotation.

**Actor-role labeling.** Every compliance-record output identifies the actor role (developer, deployer, or both). Obligations are tagged with the role to which they apply; cross-role obligations (for example the Attorney General disclosure duty) carry both.

**Affirmative-defense cross-reference.** When a compliance record is produced for an organization that also maintains an ISO 42001 AIMS or a NIST AI RMF profile, the record should be packaged with the relevant `gap-assessment` output and `soa-generator` output. The `colorado-ai-act-compliance` plugin emits a `citations` list that always includes section 6-1-1706(4) to anchor this linkage.

**Schema pointers.**

- Input schema: see [`plugins/colorado-ai-act-compliance/README.md`](../../plugins/colorado-ai-act-compliance/README.md) for field-by-field input documentation.
- Output schema: defined by the plugin's `generate_compliance_record` return shape; human-readable rendering via `render_markdown`; spreadsheet-ingestible via `render_csv`.
- Cross-framework mapping: see [`operationalization-map.md`](operationalization-map.md) in this directory.

## Limitations

**This skill does not produce Colorado SB 205 compliance.** Compliance requires substantive implementation (reasonable-care duty, policy and program establishment, impact assessment completion, consumer notice delivery, appeal process standup, disclosure processes). The plugin outputs the structured obligations and documentation checklist; execution is the organization's responsibility.

**This skill does not provide legal advice.** Application of the Act to a specific organization, system, or decision requires qualified Colorado counsel. This includes substantial-factor determination, exemption eligibility, affirmative-defense qualification, multi-state scope analysis, and sector-specific cross-regulation.

**Attorney General rulemaking is pending.** The Attorney General has rulemaking authority under section 6-1-1706. Implementing rules, once finalized, may refine terminology, impact assessment content, disclosure timing, and the list of designated recognized AI risk management frameworks under section 6-1-1706(4). This skill will be updated when rules publish.

**Federal preemption and sector regulators.** The Act coexists with federal consumer-protection, civil-rights, and sector-specific regimes. Practitioners deploying in healthcare (HIPAA), finance (FCRA, ECOA, GLBA), employment (Title VII, ADA), and housing (Fair Housing Act) must satisfy both frameworks. The Act does not preempt federal law, and federal sector regulators retain authority.

**Multi-state scope.** Organizations deploying across US states face a patchwork. New York City Local Law 144 applies narrowly to employment bias audits. Several states have introduced but not passed comprehensive AI laws as of 2026. Colorado is currently the sole state with enacted comprehensive AI consumer-protection law.

**Territorial scope is consumer-residence-based.** Applicability turns on whether the consumer is a Colorado resident and whether the actor does business in or offers services to Colorado. Non-Colorado deployments of the same system do not fall under the Act; separate jurisdictional analysis required per deployment geography.
