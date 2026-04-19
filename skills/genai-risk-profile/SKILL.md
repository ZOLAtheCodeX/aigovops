---
name: genai-risk-profile
version: 0.1.0
description: >
  GenAI risk-profile skill operationalizing the NIST AI 600-1 (July 2024)
  Generative AI Profile's 12-risk catalogue. Distinct from the general
  ISO/IEC 42001 + NIST AI RMF risk register: this skill applies only to
  generative AI systems and crossmaps each NIST AI 600-1 risk to AI RMF
  subcategories (Appendix A), EU AI Act obligations (Articles 50 and 55),
  and California statutes (SB 942 transparency, AB 2013 training data,
  AB 1008 personal information). Composes with gpai-obligations-tracker
  for EU GPAI coverage, bias-evaluator for harmful-bias evidence,
  supplier-vendor-assessor for value-chain upstream review, and
  system-event-logger for information-integrity and information-security
  operational telemetry.
frameworks:
  - NIST AI 600-1 Generative AI Profile (2024-07)
  - NIST AI RMF 1.0
  - EU AI Act (Regulation (EU) 2024/1689)
  - California Business and Professions Code Section 22757 (SB 942)
  - California AB 2013 (Training Data Transparency)
  - California Civil Code Section 1798.140(v) (AB 1008)
tags:
  - ai-governance
  - generative-ai
  - nist-ai-600-1
  - risk-register
  - eu-ai-act
  - california
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the NIST AI 600-1 (July 2024) Generative AI Profile, which adds 12 GenAI-specific risks on top of the trustworthy-AI characteristics in the AI RMF 1.0. The skill is a sibling of the general-purpose risk-register skill, not a replacement: a single AI portfolio commonly carries both a general AI risk register (ISO 42001 / AI RMF taxonomy, all systems) and a GenAI risk register (this skill, generative systems only). The two registers exist in parallel because the NIST AI 600-1 risk taxonomy is GenAI-specific and does not map cleanly onto the trustworthy-AI characteristics.

The skill pairs with the [`genai-risk-register`](../../plugins/genai-risk-register/) plugin. The plugin enforces the `is_generative` guard, validates 12-risk coverage, computes per-risk NIST AI RMF subcategory cross-references, applies jurisdiction-specific citations (EU and California), checks residual-risk logic, escalates high-residual rows, and emits the artifact as JSON, Markdown, and CSV.

## Scope

**In scope.**

- The 12 NIST AI 600-1 risks: CBRN information capabilities, confabulation, dangerous-violent-hateful content, data privacy, environmental impacts, harmful bias and homogenization, human-AI configuration, information integrity, information security, intellectual property, obscene-degrading-abusive content, value chain and component integration.
- Per-risk mapping to NIST AI RMF subcategories per Appendix A.
- Jurisdiction-specific cross-references: EU AI Act Articles 50(2) and 50(4) (synthetic content marking and deepfake labelling), Article 55(1)(a) and 55(1)(d) (systemic-risk model evaluation and cybersecurity, when paired with a GPAI artifact); California SB 942 (Cal. Bus. & Prof. Code Section 22757), AB 2013, AB 1008.
- Residual-risk logic checks: residual greater than inherent, implemented mitigation that does not reduce score, residual greater than or equal to 15 on the 5x5 scale.
- Coverage check: the practitioner must evaluate every one of the 12 risks or mark it not-applicable with a rationale.
- Version diff against a prior register.

**Out of scope.**

- Generic AI risk register (use [`risk-register-builder`](../../plugins/risk-register-builder/) for non-generative systems).
- The legal adequacy of a stated mitigation. The plugin records status; counsel reviews substance.
- The decision that a system is or is not generative. The skill assumes the practitioner has already classified the system. If `is_generative != True`, the plugin refuses with `ValueError`.
- Filing of incident reports when a critical residual flag fires. The skill emits an escalation recommendation; [`incident-reporting`](../incident-reporting/SKILL.md) handles deadline-aware filing.
- Substantive bias measurement. The skill records that a bias evaluation exists; [`bias-evaluation`](../bias-evaluation/SKILL.md) computes the metrics.

**Operating assumption.** The user organisation operates one or more generative AI systems and needs a GenAI-specific risk register that an ISO 42001 Lead Auditor or NIST AI RMF practitioner accepts as audit evidence.

## Framework Reference

**Authoritative sources.**

- NIST AI 600-1, Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile (2024-07): https://airc.nist.gov/airmf-resources/. Section 2 enumerates the 12 GenAI risks. Appendix A maps each risk to AI RMF 1.0 subcategories.
- NIST AI Risk Management Framework 1.0 (2023-01): https://www.nist.gov/itl/ai-risk-management-framework. Subcategories cited per Appendix A mapping.
- EU AI Act (Regulation (EU) 2024/1689): https://eur-lex.europa.eu/eli/reg/2024/1689/oj. Article 50(2) (machine-readable marking of synthetic content), Article 50(4) (deepfake labelling), Article 55(1)(a) and 55(1)(d) (systemic-risk model evaluation and cybersecurity).
- California Business and Professions Code Section 22757 (SB 942 AI Transparency Act): https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB942.
- California AB 2013 (Training Data Transparency): https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202320240AB2013.
- California Civil Code Section 1798.140(v) (AB 1008): personal information definition extended to AI-system outputs.

**12-risk catalogue (NIST AI 600-1 Section 2).**

| risk_id | Definition |
|---|---|
| `cbrn-information-capabilities` | GenAI uplift for chemical, biological, radiological, nuclear weapons. |
| `confabulation` | Plausible but incorrect or inconsistent outputs. |
| `dangerous-violent-hateful-content` | Model production of harmful content. |
| `data-privacy` | Training-data memorization and extraction. |
| `environmental-impacts` | Energy and resource consumption. |
| `harmful-bias-homogenization` | Amplified bias and reduced output diversity. |
| `human-ai-configuration` | Over-reliance, automation bias, ill-calibrated trust. |
| `information-integrity` | Deepfakes, synthetic media, disinformation. |
| `information-security` | Prompt injection, jailbreak, model extraction. |
| `intellectual-property` | Training-data IP infringement; output attribution. |
| `obscene-degrading-abusive-content` | NCII, CSAM. |
| `value-chain-component-integration` | GenAI-specific supply-chain risks. |

## Operationalizable Controls

The skill operationalizes one Tier 1 capability: GenAI risk evaluation and registration. It composes with five siblings.

**Tier 1: GenAI risk evaluation and registration.**

- Input: system description (with `is_generative = True`), per-risk evaluations (likelihood, impact, mitigations, residual scoring, owner), optional cross-reference refs (gpai-obligations, supplier-assessment, bias-evaluation), optional previous register for diff.
- Processing: 12-risk coverage check; per-risk normalization; NIST AI RMF subcategory mapping (Appendix A); jurisdiction-specific citation overlay (EU + California); residual-risk logic checks; high-residual escalation flagging; optional crosswalk enrichment.
- Output: per-risk normalized rows with citations and warnings, coverage assessment, per-risk NIST coverage map, jurisdiction cross-references, residual flags, version diff (when applicable), summary.
- Plugin: `generate_genai_risk_register()`, `render_markdown()`, `render_csv()`.

**Composition with GPAI obligations.** When the system is a general-purpose AI under EU AI Act Article 51, run [`gpai-obligations`](../gpai-obligations/SKILL.md) first and pass the resulting artifact path as `cross_reference_refs.gpai_obligations_ref`. The plugin then attaches Article 55(1)(a) and 55(1)(d) citations to the `information-security` and `value-chain-component-integration` rows respectively.

**Composition with bias evaluation.** The `harmful-bias-homogenization` row should reference an executed bias evaluation. Run [`bias-evaluation`](../bias-evaluation/SKILL.md), then pass the artifact path as `cross_reference_refs.bias_evaluation_ref`. The skill does not compute fairness metrics itself.

**Composition with supplier and vendor governance.** The `value-chain-component-integration` row should reference an upstream-provider assessment. Run [`supplier-vendor`](../supplier-vendor/SKILL.md) for each upstream GenAI dependency (base models, fine-tuning datasets, third-party tool integrations) and pass the artifact path as `cross_reference_refs.supplier_assessment_ref`.

**Composition with operational telemetry.** The `information-integrity` and `information-security` rows draw evidence from operational logs. Run [`system-event-logging`](../system-event-logging/SKILL.md) and reference the relevant log streams in the row's `existing_mitigations[*].evidence_ref`.

**Composition with incident reporting.** A residual score >= 15 on the 5x5 scale fires a critical flag with escalation to incident-reporting and management-review. When a flagged risk materialises, run [`incident-reporting`](../incident-reporting/SKILL.md) to compute deadline-aware filings under EU AI Act Article 73 and adjacent regimes.

See [`operationalization-map.md`](operationalization-map.md) for the per-risk cross-plugin relationships.

## Output Standards

All citations follow [STYLE.md](../../STYLE.md):

- `NIST AI 600-1, Section <section>` for risk definitions; `NIST AI 600-1, Appendix A` for subcategory mapping.
- `NIST AI RMF, <FUNCTION> <Subcategory>` per risk.
- `EU AI Act, Article 50, Paragraph 2` and `Article 50, Paragraph 4` for synthetic-content obligations.
- `EU AI Act, Article 55, Paragraph 1, Point (a)` and `Point (d)` for systemic-risk obligations (only when paired with `gpai_obligations_ref`).
- `Cal. Bus. & Prof. Code Section 22757` for SB 942.
- `California AB 2013, Section <section>` for training-data transparency.
- `Cal. Civ. Code Section 1798.140(v)` for AB 1008.

No em-dashes. No emojis. No hedging. Every per-risk row carries citations, NIST subcategory refs, and warnings.

## Limitations

1. **Generative-only.** The plugin refuses non-generative systems. For a general AI risk register that covers traditional ML, rule-based classifiers, and other non-generative AI, use [`risk-register-builder`](../../plugins/risk-register-builder/).
2. **No metric computation.** The plugin does not compute bias metrics, robustness scores, or privacy-leakage probabilities. Each per-risk row references an external evaluation artifact.
3. **No legal adequacy review.** The plugin records that a mitigation has a status; counsel reviews whether the mitigation actually meets the underlying obligation.
4. **Residual scoring is a 5x5 scale.** Likelihood and impact each have five levels (1-5); the score is their product. Maximum is 25. The 15 threshold maps to "almost-certain x major" or "likely x catastrophic" or higher.
5. **No automated incident filing.** Critical residual flags emit an escalation recommendation only. The practitioner runs `incident-reporting` when a flagged risk materialises.
6. **Jurisdiction codes are lowercase strings.** The plugin recognises `eu` and `usa-ca`. Other jurisdictions do not trigger jurisdiction-specific citations; this is by design (no over-reach).
