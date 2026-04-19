---
name: explainability-documentation
version: 0.1.0
description: >
  Dedicated explainability documentation skill. Operationalizes NIST AI RMF
  1.0 MEASURE 2.9 (model is explained and interpretable; functionality,
  outputs, and associated risks are characterised), EU AI Act Article 86
  (right to explanation of individual decisions for affected persons of
  high-risk AI systems with legal or similarly significant effect),
  ISO/IEC 42001:2023 Annex A Control A.8.2 (system documentation and
  information for interested parties), and UK Algorithmic Transparency
  Recording Standard Section Tool details (model performance and
  explainability signals). Pairs with the explainability-documenter plugin.
frameworks:
  - NIST AI RMF 1.0
  - EU AI Act (Regulation (EU) 2024/1689)
  - ISO/IEC 42001:2023
  - UK Algorithmic Transparency Recording Standard
tags:
  - ai-governance
  - explainability
  - interpretability
  - transparency
  - right-to-explanation
  - measure-2-9
  - article-86
  - iso-a-8-2
  - uk-atrs
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the dedicated explainability documentation artifact a notified body, ISO 42001 lead auditor, NIST AI RMF practitioner, or UK ATRS reviewer expects to find as audit evidence for explainability obligations. The artifact carries a model-type classification (intrinsic interpretable, post-hoc covered, post-hoc missing), a per-method coverage record (scope, target audience, implementation status, evidence reference, known limitations), an Art. 86 applicability and readiness assessment, and a limitations transparency assessment.

The skill pairs with the [`explainability-documenter`](../../plugins/explainability-documenter/) plugin. The plugin echoes practitioner-declared methods, computes coverage and consistency checks against the four frameworks, attaches citations, and emits warnings on coverage gaps. It does not invent methods or limitations and does not verify evidence references.

## Scope

**In scope.**

- NIST AI RMF MEASURE 2.9 explanation methodology characterisation, interpretability scope (global, local, both), target audience, and known limitations.
- EU AI Act Article 86 right to explanation of individual decisions for affected persons of high-risk AI systems producing legal or similarly significant effects.
- EU AI Act Article 13 instructions-for-use coverage when deployer or operator audience is required for a high-risk system.
- ISO/IEC 42001:2023 Annex A Control A.8.2 user-facing documentation content for the explainability dimension.
- UK ATRS Section Tool details model performance and explainability signal disclosure when the system has UK public-sector jurisdiction.
- Composition with `aisia-runner` (cross-reference from impact dimension), `soa-generator` (A.8.2 row content), `audit-log-generator` (governance event recording), `risk-register-builder` (limitation-derived risks).

**Out of scope.**

- Selection of which explanation method to deploy. The skill records the practitioner's selection and assesses coverage; it does not advise on method choice.
- Explanation method execution. The MLOps and ML-research pipelines run SHAP, LIME, integrated gradients, counterfactuals, and similar methods. The plugin records the outputs and references the evidence.
- Verification that `evidence_ref` paths exist. The plugin treats evidence references as opaque pointers.
- Article 86 response generation for a specific affected-person request. The skill records the template reference; case-by-case responses are runtime activity outside this artifact.
- General explainability research. The skill captures the audit-evidence dimension of explainability, not the research literature.

**Operating assumption.** The user organization has selected explanation methods and produced evidence for each. The skill structures the documentation in audit-ready form with the correct citations, coverage checks, and Art. 86 readiness signal.

## Framework Reference

**Authoritative sources.**

- NIST AI Risk Management Framework 1.0 (AI RMF 1.0), MEASURE 2.9: https://www.nist.gov/itl/ai-risk-management-framework.
- EU AI Act, Regulation (EU) 2024/1689, Article 86: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689.
- EU AI Act, Article 13 (instructions for use): same source.
- ISO/IEC 42001:2023, Annex A, Control A.8.2 (System documentation and information for users).
- UK Algorithmic Transparency Recording Standard, Section Tool details: https://www.gov.uk/government/publications/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies.
- ISO/IEC TR 24028:2020 (overview of trustworthiness in AI; informative reference for interpretability vocabulary).

**Coverage map.**

| Provision | Theme | Plugin field |
|---|---|---|
| NIST AI RMF, MEASURE 2.9 | Explanation methodology, interpretability scope, audience, limitations | `model_type_classification`, `methods_coverage`, `scope_coverage`, `limitations_documentation_assessment` |
| EU AI Act, Article 86, Paragraph 1 | Right to explanation of individual decisions for affected persons | `art_86_applicability`, `art_86_readiness` |
| EU AI Act, Article 13, Paragraph 3, Point (b) | Instructions for use sufficient for deployers | `audience_coverage.deployer_or_operator_covered` |
| ISO/IEC 42001:2023, Annex A, Control A.8.2 | Information for interested parties | `methods_coverage` (audience field), `system_description_echo` |
| UK ATRS, Section Tool details | Model performance and explainability disclosure | top-level `citations` (when UK jurisdiction) |

## Operationalizable Controls

The skill operationalizes one Tier 1 capability and composes with four siblings.

**Tier 1: explainability documentation artifact.**

- Input: system_description (with decision_effects), model_type, explanation_methods (each with scope, target_audience, implementation_status, evidence_ref, known_limitations), optional intrinsic_interpretability_claim, optional art_86_response_template_ref, optional previous_documentation_ref.
- Processing: model-type classification (intrinsic vs post-hoc), per-method echo, scope coverage check (global, local), audience coverage check (with Art. 86 affected-persons enforcement), Art. 86 applicability and readiness, limitations transparency assessment, optional schema diff against previous reference, optional crosswalk enrichment.
- Output: `model_type_classification`, `methods_coverage`, `scope_coverage`, `audience_coverage`, `art_86_applicability`, `art_86_readiness`, `limitations_documentation_assessment`, `schema_diff_summary` (when applicable), `citations`, `cross_framework_citations` (when enriched), `warnings`, `summary`.
- Plugin: `document_explainability()`, `render_markdown()`, `render_csv()`.

**Composition with `aisia-runner`.** AISIA touches explainability as part of the impact dimension. This skill produces the dedicated artifact AISIA cross-references. A high-risk-system AISIA without an `explainability-documenter` artifact reference is incomplete.

**Composition with `soa-generator`.** ISO 42001 Annex A Control A.8.2 appears as one row in the SoA. This skill produces the substantive A.8.2 content that the SoA row points to as evidence of inclusion.

**Composition with `audit-log-generator`.** Each invocation of `document_explainability()` is a governance event suitable for audit-log capture. The audit-log-generator records the event reference, the governance decisions encoded in method selection, and the responsible parties.

**Composition with `risk-register-builder`.** Each non-empty `known_limitations` entry is a candidate residual risk for the AI risk register. The risk-register-builder consumes the limitations as risk inputs.

See [`operationalization-map.md`](operationalization-map.md) for per-method cross-plugin relationships.

## Output Standards

All outputs carry citations in [STYLE.md](../../STYLE.md) format:

- `NIST AI RMF, MEASURE 2.9`
- `ISO/IEC 42001:2023, Annex A, Control A.8.2`
- `ISO/IEC TR 24028:2020`
- `EU AI Act, Article 86, Paragraph 1` (when applicable)
- `EU AI Act, Article 13, Paragraph 3, Point (b)` (when applicable)
- `UK ATRS, Section Tool details` (when UK jurisdiction)

Model-type classification uses a fixed four-value vocabulary: `intrinsic-interpretable`, `post-hoc-covered`, `post-hoc-missing`, `post-hoc-required`. Scope vocabulary: `global`, `local`, `both`. Audience vocabulary: `developers`, `deployers`, `operators`, `auditors`, `affected-persons`, `regulators`, `end-users`. Implementation status vocabulary: `implemented`, `planned`, `not-applicable`. The plugin emits BLOCKING warnings for missing affected-persons audience on a system with legal or similarly significant effect, and non-blocking warnings for missing global or local scope coverage, missing limitations, missing Art. 86 response template, and missing planned target dates. No em-dashes. No emojis. No hedging.

## Limitations

1. **No method execution.** The plugin records and assesses precomputed methods. Method execution is the MLOps and ML-research pipelines' responsibility.
2. **No evidence verification.** The plugin treats `evidence_ref` as an opaque pointer. The reviewer verifies the reference resolves to a real artifact.
3. **No method recommendation.** The plugin does not advise which explanation method to deploy. Method selection requires domain judgment about model family, audience, and decision context.
4. **No Art. 86 response generation.** The plugin records the template reference and assesses readiness. Generating a specific response to an individual affected-person request is runtime activity outside this artifact.
5. **No automated cross-system aggregation.** The plugin records one system per invocation. Portfolio-level explainability posture requires aggregation outside the plugin.
