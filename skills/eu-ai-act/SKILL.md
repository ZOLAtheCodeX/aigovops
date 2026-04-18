---
name: eu-ai-act
version: 0.2.0
description: >
  EU AI Act (Regulation (EU) 2024/1689) governance skill.
  Operationalizes the risk-tier classification (prohibited, high-risk,
  limited-risk, minimal-risk) in Articles 5 and 6 and Annex III, the
  requirements for high-risk AI systems in Articles 9 through 15, the
  obligations of providers, deployers, importers, and distributors in
  Articles 16 through 29, transparency obligations in Article 50, the
  general-purpose AI (GPAI) model obligations in Articles 51 through
  55, and the conformity assessment and post-market monitoring
  obligations in Articles 43 through 49 and Article 72. Validated
  against the published Official Journal text on 2026-04-18.
frameworks:
  - EU AI Act (Regulation (EU) 2024/1689)
tags:
  - ai-governance
  - eu-ai-act
  - ai-regulation
  - risk-tier-classification
  - gpai
  - conformity-assessment
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes Regulation (EU) 2024/1689, the EU AI Act, for organizations that deploy, import, distribute, or provide AI systems that fall within the Regulation's territorial scope. The Act was published in the Official Journal of the European Union on 12 July 2024. Enforcement is staged: prohibited practices apply from February 2025, GPAI obligations from August 2025, and high-risk system obligations from August 2026 with extended transition to 2027 for certain Annex III use cases.

The skill is companion to the `iso42001` and `nist-ai-rmf` skills in this catalogue. Six of seven EU AI Act Tier 1 operationalizations share a plugin with an iso42001 or nist-ai-rmf Tier 1 item; the plugin's `framework` flag switches to `eu-ai-act` rendering, producing Article-number citations instead of Clause or subcategory citations. This skill documents the EU-specific requirements that the shared plugins must satisfy and points at the `operationalization-map.md` in this directory for the full Article-to-plugin crosswalk.

## Scope

**In scope.** Regulation (EU) 2024/1689 (the EU AI Act) as published, including:

- Chapter II, Article 5: Prohibited AI practices (eight categories).
- Chapter III, Articles 6 through 29: High-risk AI systems and economic-actor obligations (providers, deployers, importers, distributors, authorised representatives).
- Chapter III, Section 2, Articles 9 through 15: Requirements for high-risk AI systems (risk management, data governance, technical documentation, record-keeping, transparency, human oversight, accuracy-robustness-cybersecurity).
- Chapter IV, Article 50: Transparency obligations for certain AI systems (AI-interaction disclosure, synthetic-content marking, deep-fake labeling).
- Chapter V, Articles 51 through 55: General-purpose AI model obligations, including systemic-risk classification.
- Chapter VII, Articles 43 through 49: Conformity assessment and the EU database for high-risk AI.
- Chapter IX, Articles 72 and 73: Post-market monitoring and serious-incident reporting.
- Annex III: Eight categories of high-risk use cases.

**Out of scope.** This skill does not provide:

- Legal advice. EU AI Act application requires qualified European Union counsel for matters including provider-deployer role determination, cross-border scope analysis, fundamental rights impact interpretation, and regulator engagement.
- Interpretation of national implementing measures. Member States implement aspects of the Regulation through national law; this skill covers the EU-level Regulation, not the Member-State transposition.
- Sector-specific EU AI regulation beyond the Act (for example, Digital Services Act, Digital Markets Act, Medical Device Regulation, Machinery Regulation) except insofar as the Act cross-references them (notably Annex I for product-safety high-risk classification).
- Certification-body procedures. Notified-body processes under Articles 28 and 29 are regulator-facing, not deployer-facing.

**Operating assumption.** The user organization either provides or deploys AI systems within the EU territorial scope, or it contracts with EU customers that require EU AI Act conformance. This skill presumes that commitment. For organizations not within scope, the skill provides crosswalk-only utility (EU AI Act language for communication with EU counterparties).

## Framework Reference

**Authoritative source.** Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 laying down harmonised rules on artificial intelligence (Artificial Intelligence Act), published in the Official Journal of the European Union on 12 July 2024. Available at https://eur-lex.europa.eu/eli/reg/2024/1689/oj.

**Structure.**

- Chapter I (Articles 1-4): General provisions (scope, definitions, AI literacy).
- Chapter II (Article 5): Prohibited AI practices.
- Chapter III (Articles 6-49): High-risk AI systems.
  - Section 1: Classification (Articles 6-7).
  - Section 2: Requirements for high-risk AI systems (Articles 8-15).
  - Section 3: Obligations of providers and deployers and other parties (Articles 16-27).
  - Section 4: Notifying authorities and notified bodies (Articles 28-39).
  - Section 5: Standards, conformity assessment, certificates, registration (Articles 40-49).
- Chapter IV (Article 50): Transparency obligations for certain AI systems.
- Chapter V (Articles 51-56): General-purpose AI models.
- Chapter VI (Articles 57-63): Measures in support of innovation (regulatory sandboxes, real-world testing).
- Chapter VII (Articles 64-70): Governance at Union and Member-State level.
- Chapter IX (Articles 72-73): Post-market monitoring and incident reporting (numbered in the published text within the chapter structure).
- Chapter X-XII (Articles 85-113): Codes of conduct, confidentiality, penalties, final provisions.
- Annexes I-XIII: Lists, templates, and technical specifications including Annex III (high-risk use cases) and Annex IX (Union harmonisation legislation on which product-safety high-risk classification relies).

**Enforcement timeline.**

- 2 February 2025: Prohibitions in Article 5 and general provisions in Chapter I apply.
- 2 August 2025: GPAI model obligations (Chapter V), governance provisions (Chapter VII, Section 1), and penalty provisions apply.
- 2 August 2026: Majority of remaining provisions apply, including Article 6(2) Annex III classification and Articles 9 through 15 requirements.
- 2 August 2027: Extended transition for certain Annex III use cases integrated with product-safety frameworks (Annex I).

**Related frameworks and cross-references.**

- Annex I product-safety harmonisation legislation (Medical Device Regulation, Machinery Regulation, Radio Equipment Directive, and others): determines Article 6(1) high-risk classification.
- ISO/IEC 42001:2023: strong operationalization overlap across Articles 9 (risk management), 10 (data governance), 11 (technical documentation), 12 (record-keeping), 14 (human oversight), 15 (accuracy, robustness, cybersecurity). An organization operating under ISO 42001 will satisfy most of the Act's process requirements for high-risk systems.
- NIST AI RMF 1.0: overlap across MAP, MEASURE, and MANAGE subcategories. US-based providers using NIST will find MEASURE 2.x particularly well-aligned with Article 15.

**Cross-skill operationalization.** The `operationalization-map.md` in this directory enumerates Article-to-plugin mappings. Seven of the nine existing AIGovOps plugins gain an `eu-ai-act` rendering mode that emits Article citations.

## Operationalizable Controls

Seven Tier 1 operationalizations are detailed below. Six cross-reference existing plugins from the iso42001 and nist-ai-rmf skills via the `framework: eu-ai-act` mode. One (T1.6 high-risk classification) is EU-distinctive and documented here as a future plugin scope.

### T1.1 Fundamental Rights Impact Assessment (Article 27) and system impact assessment (Article 9 linkage)

Class: H. Artifact: `AISIA-section` with Article 27 schema. Leverage: H. Consumer: `plugins/aisia-runner` in `framework: eu-ai-act` mode.

**Requirement summary.** Article 27 requires deployers of high-risk AI systems listed in Annex III to perform a Fundamental Rights Impact Assessment (FRIA) before first deployment, covering the intended purpose, duration and frequency of use, categories of natural persons likely to be affected, specific risks of harm, human oversight measures, and measures to be taken in the event of materialisation of risks. Article 9 requires that a risk management system be established, implemented, documented, and maintained for high-risk AI systems throughout their life cycle. FRIA outputs feed the Article 9 risk management system.

**Cross-reference.** The plugin is `aisia-runner`. In `framework: eu-ai-act` mode the emitted sections cite `EU AI Act, Article 27, Paragraph X` for the deployer obligation and `EU AI Act, Article 9, Paragraph X` for the upstream risk-management linkage. EU-specific dimensions include:

- Enumeration of fundamental rights at risk (dignity, privacy, non-discrimination, fair trial, freedom of expression, and so on per the EU Charter of Fundamental Rights).
- Documentation of the deployer's human oversight arrangement per Article 14 (cross-cutting with T1.4).
- Identification of natural-person categories likely to be affected, with particular attention to vulnerable groups.

**Auditor acceptance criteria (EU-specific additions).**

- The FRIA is dated before first use of the system per Article 27(1).
- The FRIA covers every category listed in Article 27(1)(a) through (g).
- The FRIA is notified to the market surveillance authority where required.
- The FRIA is revisited when a significant change occurs.

### T1.2 Risk management system (Article 9)

Class: H. Artifact: `risk-register-row` with Article 9 citations. Leverage: H. Consumer: `plugins/risk-register-builder` in `framework: eu-ai-act` or `dual` mode.

**Cross-reference.** The plugin is `risk-register-builder`. In `framework: eu-ai-act` mode rows cite `EU AI Act, Article 9`. Article 9(2) specifies the risk management system as a continuous iterative process running throughout the life cycle of the high-risk AI system, comprising: identification and analysis of risks; estimation and evaluation of risks under intended use and under reasonably foreseeable misuse; evaluation of risks based on post-market monitoring data; and adoption of risk management measures.

**EU-specific additions.**

- Residual risks must be disclosed to deployers per Article 9(5) when they cannot be further mitigated. The `negative_residual_disclosure_ref` field already present in the plugin (for NIST MANAGE 1.4) also satisfies this EU requirement.
- Testing obligations under Article 9(6) through (8): testing must be performed prior to placing the system on the market or putting it into service, against preliminarily defined metrics and probabilistic thresholds. Cross-link to metrics-collector outputs in the scoring_rationale.

### T1.3 Technical documentation (Article 11) and automatic record-keeping (Article 12)

Class: A and H. Artifact: `audit-log-entry` with Article 11 and Article 12 citations. Leverage: H. Consumer: `plugins/audit-log-generator` in `framework: eu-ai-act` mode.

**Cross-reference.** The plugin is `audit-log-generator`. Article 11 requires providers to draw up technical documentation of the high-risk AI system before placing it on the market, keep it up to date, and make it available to national competent authorities upon reasoned request. Annex IV specifies the minimum content of the technical documentation. Article 12 requires automatic logging of events throughout the system's life cycle, with logs kept for a period appropriate to the intended purpose and at least six months.

**EU-specific additions.**

- Annex IV coverage check: every listed element (general description; detailed description of elements and development process; information about the monitoring, functioning, and control; risk management system description; and so on) must be addressed in the documentation package.
- Six-month minimum log retention per Article 12(1). Organizations with longer retention policies honor the stricter policy.
- Automatic-log event types per Article 12(2) must include at minimum: recording of the period of each use, the reference database against which input data was checked (where applicable), input data for which the match yielded high-risk output, and identification of the natural persons involved in the verification of results.

### T1.4 Human oversight (Article 14)

Class: H. Artifact: `role-matrix` with Article 14 citations. Leverage: H. Consumer: `plugins/role-matrix-generator` in `framework: eu-ai-act` mode.

**Cross-reference.** The plugin is `role-matrix-generator`. Article 14(1) requires that high-risk AI systems be designed and developed in such a way that they can be effectively overseen by natural persons during their period of use. Article 14(4) specifies that human oversight measures must enable the natural persons concerned to understand the system's capacities and limitations, monitor its operation, correctly interpret its output, decide not to use the output or override it, and intervene in the system's operation or interrupt it.

**EU-specific additions.**

- Every decision category in the role matrix must identify the natural person (not a team or role in the abstract, per the role matrix's authority_basis requirement) with the authority to override or interrupt the system.
- Training of the oversight person per Article 14(4)(a) must be documented; cross-link to the training-record artifact (see iso42001 Clause 7.2 crosswalk).
- For systems listed in Annex III point 1(a) (biometric identification), two natural persons must verify outputs per Article 14(5) where the context requires.

### T1.5 Accuracy, robustness, and cybersecurity (Article 15)

Class: A. Artifact: `KPI` with Article 15 citations. Leverage: H. Consumer: `plugins/metrics-collector` in `framework: eu-ai-act` or `dual` mode.

**Cross-reference.** The plugin is `metrics-collector`. Article 15 requires high-risk AI systems to achieve an appropriate level of accuracy, robustness, and cybersecurity and to perform consistently in those respects throughout their life cycle. Accuracy levels and relevant accuracy metrics must be declared in the accompanying instructions for use per Article 15(3). Robustness measures must protect against errors, faults, and inconsistencies; cybersecurity measures must be appropriate to the relevant circumstances and risks.

**EU-specific additions.**

- Accuracy metric declaration per Article 15(3): the metrics report must include per-system accuracy figures suitable for inclusion in the instructions-for-use document delivered to deployers.
- Feedback loops and bias risks per Article 15(4): where a high-risk AI system continues to learn after being placed on the market, appropriate measures must address bias that may be introduced by the output of the system influencing future inputs. The metrics-collector's fairness family plus drift monitoring addresses this.
- Cybersecurity resilience against attempts to alter the use, outputs, or performance per Article 15(5): the security-resilience metric family covers this; adversarial-robustness testing satisfies Article 15(5) evidence needs.

### T1.6 Risk-tier and Annex III classification (Articles 5, 6; Annex III)

Class: H. Artifact: classification record plus `AISIA-section`. Leverage: H. Consumer: future `plugins/high-risk-classifier` (Phase 4 scope); the `gap-assessment` plugin accepts `target_framework: eu-ai-act` today and can be used as an interim classification surface.

**Requirement summary.** Every AI system in scope must first be classified against Article 5 (prohibited) and then against Article 6 (high-risk). Article 6(1) refers to AI systems intended to be used as a safety component of a product covered by Union harmonisation legislation listed in Annex I, subject to conformity assessment under that legislation. Article 6(2) refers to AI systems listed in Annex III. Article 6(3) provides an exception for Annex III systems that do not pose a significant risk of harm.

**EU-distinctive design note.** Unlike the other Tier 1 items, this operationalization does not share a plugin with iso42001 or nist-ai-rmf. A dedicated `high-risk-classifier` plugin is planned for Phase 4. Its draft contract:

- **Input**: system description with `intended_use`, `sector`, `data_processed`, `decision_authority`, `annex_i_product_type` (optional), `member_state_deployment_scope`.
- **Output**: classification record with `risk_tier` (prohibited | high-risk | limited-risk | minimal-risk), `annex_iii_category` (None or one of the eight), `article_6_1_path` (True if Annex I product-safety route), `rationale`, `citations`.
- **Output side-effect**: when `risk_tier == 'prohibited'`, raises a classification error; when `high-risk`, triggers the Article 27 FRIA workflow.

Until the plugin exists, organizations use the `gap-assessment` plugin with `target_framework: eu-ai-act` and an explicit `targets` list covering Articles 9-15 as a high-risk-compliance gap view.

### T1.7 Post-market monitoring and serious-incident reporting (Articles 72 and 73)

Class: A. Artifact: `KPI` and `audit-log-entry` with Article 72 and 73 citations. Leverage: H. Consumer: `plugins/metrics-collector` for ongoing monitoring KPIs; `plugins/audit-log-generator` for serious-incident reporting events.

**Cross-reference.** Article 72 requires providers of high-risk AI systems to establish and document a post-market monitoring system proportionate to the nature of the AI technologies and the risks of the system. Article 73 requires providers to report serious incidents to the market surveillance authority of the Member State where the incident occurred. Reporting timelines: within 15 days of awareness in the general case; within 2 days for incidents involving death or serious harm to property or environment; within 10 days for incidents involving cybersecurity breaches or serious harm to a person's fundamental rights.

**EU-specific additions.**

- Post-market monitoring plan per Article 72(1) must be documented as part of the technical documentation (Article 11 linkage).
- Serious-incident reporting deadlines per Article 73 require the audit-log entry to carry a `reported_to_authority_at` timestamp and a `member_state_authority_ref` identifying the receiving regulator.
- Where the serious incident is related to fundamental rights under Article 73(2)(c), additional notification to fundamental rights protection authorities may apply.

### Tier 2

Tier 2 operationalizations are valuable but lower-frequency or narrower-scope than Tier 1. Abbreviated guidance; full plugin treatment as user demand confirms.

1. **GPAI documentation (Article 53).** Training-data summary, copyright policy, model card. Future `plugins/gpai-documentation-generator` or a rendering mode of the audit-log-generator.
2. **GPAI systemic-risk classification (Article 51).** Compute-FLOP threshold check plus capability evaluation. Dedicated plugin if GPAI-provider adoption warrants.
3. **Annex III classification details (per category).** Eight Annex III categories each imply category-specific documentation. Integrates with T1.6 high-risk classifier.
4. **Provider corrective actions (Article 20).** Shared with `nonconformity-tracker` in `framework: eu-ai-act` mode.
5. **Importer and distributor obligations (Articles 23, 24).** Supplier register operationalizations; shared with iso42001 Annex A A.10.
6. **Deployer obligations (Article 26).** Cross-cutting deployer obligations; most already covered by iso42001 AIMS operationalizations.
7. **Transparency obligations (Article 50).** Disclosure detection at system UX boundary; partial coverage via metrics-collector's information-integrity family (AI 600-1 overlay) and the audit-log-generator for disclosure events.
8. **Conformity assessment (Articles 43-49).** Procedure selection; submission to notified body. Regulator-interface work; not fully operationalizable by AIGovOps but the documentation package can be assembled via audit-log-generator.
9. **CE marking (Article 48) and EU database registration (Article 49).** Document-event recording via audit-log-generator; actual submission is via EU-operated interfaces.

### Tier 3

Judgment-bound provisions. This skill is prescriptive; plugins do not attempt to automate.

- Article 5 prohibited-practice classification: per-practice determination requires legal analysis.
- Article 25 provider-deployer role flips: legal determination.
- Article 28 and 29 notifying-authority and notified-body operations: regulator-side, not organization-side.
- Article 43 conformity-assessment procedure selection: legal and regulatory judgment.
- Articles 57 through 63 regulatory sandboxes and real-world testing: negotiated with competent authorities.
- Articles 85 through 99 penalties and remedies: legal exposure analysis.

## Output Standards

All outputs produced by this skill, or by plugins in `framework: eu-ai-act` mode, conform to the output standards defined in the [iso42001 skill Output Standards section](../iso42001/SKILL.md). The following EU-specific additions apply.

**Citation format.** Per [STYLE.md](../../STYLE.md): `EU AI Act, Article XX, Paragraph X` on first reference; `EU AI Act, Art. XX(X)` for concise in-row references acceptable. Recitals: `EU AI Act, Recital XX`. Annexes: `EU AI Act, Annex X, Point Y` or `EU AI Act, Annex III, Point 1(a)` for sub-points.

**Applicability dating.** Every output that asserts a compliance obligation includes the effective date of the obligation per the enforcement timeline. A 2026 output citing Article 9 carries the annotation `effective from 2 August 2026` where the output is intended for pre-effective-date planning.

**Dual and triple-framework rendering.** Organizations commonly operate under multiple frameworks. Plugins supporting `framework: dual` treat the two-framework case as iso+nist; for iso+eu or nist+eu combinations, use the plugin's `framework: eu-ai-act` mode and post-process to add the co-framework citations. A future `framework: triple` mode is planned when demand warrants.

**Member-State-specific adaptations.** Where the Regulation delegates implementation to Member States (for example, language requirements for documentation or local market-surveillance authority identification), outputs include a configurable `member_state` field. The skill does not prescribe specific Member-State adaptations; organizations configure these per their deployment scope.

**Machine-translated documentation note.** The EU AI Act is published in all official EU languages; each language version is equally authentic. This skill's outputs use English. Organizations required to submit documentation in a specific Member-State language should treat this skill's outputs as source material for translation by qualified translators, not as a substitute for language-specific regulatory submission.

## Limitations

**This skill does not produce EU AI Act conformity.** Conformity assessment under Articles 43 through 49 is a regulatory process involving notified bodies (for some high-risk categories) and the EU database. The skill produces artifacts that satisfy the technical documentation, risk management, human oversight, and post-market monitoring requirements that conformity assessment evaluates.

**This skill does not provide legal advice.** EU AI Act application, cross-border scope analysis, provider-deployer determination, Member-State transposition interpretation, fundamental rights impact interpretation, and regulator engagement require qualified European Union counsel. The skill surfaces the EU-specific requirements; legal determination remains human.

**Article 6(3) exception determinations are human.** The Article 6(3) exception (Annex III systems not posing significant risk) requires organization-specific analysis and documentation. The skill's gap-assessment can surface that the determination is needed; it does not make the determination.

**Regulatory revisions follow.** The EU AI Act contemplates delegated acts and implementing acts under Articles 6, 47, 50, 51, 52, 72, and others. These can modify thresholds, procedures, and categorizations over the life of the Regulation. The framework-monitor workflow surfaces detected changes; skill updates follow the AGENTS.md change-update protocol.

**GPAI threshold calibration is external.** Article 51 compute-FLOP thresholds for systemic-risk classification may be updated by delegated acts. Any GPAI-classification plugin must read a current-thresholds configuration from an external source rather than hard-coding the thresholds.

**Member-State national implementation is out of scope.** Organizations with deployments in multiple Member States face potentially divergent national-level rules where Member States exercise discretion afforded by the Regulation. This skill covers the EU-level Regulation; Member-State-specific rules require national counsel and national skill extensions.

**Enforcement is staged through 2027.** Pre-effective-date outputs are planning artifacts, not compliance evidence. The skill accepts a `planning_mode` flag on future integrations; until then, outputs cited against provisions not yet in force carry an explicit "planning; effective DD Month YYYY" annotation.

**Cross-framework interaction depends on the co-framework skill.** Organizations subject to GDPR, DSA, DMA, sector-specific regulation (MDR, MiFID II, and others) have obligations beyond the AI Act. This skill does not address them; the relevant sector skills would.
