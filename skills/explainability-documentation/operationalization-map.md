# Explainability Documentation Operationalization Map

Working document for the `explainability-documentation` skill. Maps each NIST AI RMF MEASURE 2.9 element, EU AI Act Article 86 paragraph, ISO/IEC 42001 Annex A Control A.8.2 element, and UK ATRS Section Tool details signal to the A/H/J operationalizability classification and the AIGovOps artifact vocabulary. Same methodology as `skills/iso42001/operationalization-map.md` and `skills/robustness-evaluation/operationalization-map.md`.

**Validation status.** Section references validated against NIST AI RMF 1.0, EU AI Act (Regulation (EU) 2024/1689), ISO/IEC 42001:2023 Annex A, and UK ATRS Template v2.0 on 2026-04-18.

**Classification legend.**

- A: automatable. The plugin derives output deterministically from structured input.
- H: hybrid. The plugin assembles and validates; a human provides key substantive content.
- J: judgment. A qualified human (counsel, notified body, senior reviewer) must decide.

**Leverage legend.**

- H: strong cost reduction from automation.
- M: moderate.
- L: low.

## NIST AI RMF MEASURE 2.9

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| MEASURE 2.9 (methodology) | Explanation methodology characterisation (intrinsic vs post-hoc) | A | `model_type_classification` | H | Plugin classifies into intrinsic-interpretable, post-hoc-covered, post-hoc-required, post-hoc-missing using model_type and intrinsic_interpretability_claim. |
| MEASURE 2.9 (scope) | Interpretability scope: global vs local | A | `scope_coverage` | H | Plugin verifies at least one method covers global scope and at least one covers local scope; missing scope emits framework-cited warning. |
| MEASURE 2.9 (audience) | Target audience: developers, deployers, subjects of decisions | A | `audience_coverage` | H | Plugin verifies audience composition; affected-persons enforced as BLOCKING for high-risk decisions. |
| MEASURE 2.9 (limitations) | Known limitations of each explanation method | H | `limitations_documentation_assessment` | M | Plugin enforces non-empty `known_limitations` per method; absent rationale emits warning. |

## EU AI Act Article 86

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Article 86, Paragraph 1 | Right to explanation of individual decisions for affected persons of high-risk systems with legal or similarly significant effect | H | `art_86_applicability`, `art_86_readiness` | M | Plugin computes applicability from `decision_effects`; emits readiness signal across template, audience, and local-scope dimensions. |
| Article 86 (response template) | Template for responding to individual explanation requests | H | `art_86_response_template_ref` echo | M | Plugin records the reference and emits warning when applicable but missing. Template authorship is human-side. |
| Article 13, Paragraph 3, Point (b) (cross-reference) | Instructions for use sufficient for deployers | A | `audience_coverage.deployer_or_operator_covered` | M | Plugin enforces deployer or operator audience for high-risk systems. |

## ISO/IEC 42001:2023 Annex A Control A.8.2

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| A.8.2 (system documentation) | Information for interested parties about the AI system | H | `system_description_echo`, `methods_coverage` (audience field) | M | Plugin echoes `system_description` and per-method audience composition. Substantive content of A.8.2 documentation lives in the methods coverage table. |
| A.8.5 (cross-reference) | Information for interested parties (broader) | H | `audience_coverage.audiences_covered` | L | Plugin records audience breadth; A.8.5 broader information-for-interested-parties content lives in adjacent artifacts (uk-atrs-recorder, soa-generator). |

## UK ATRS Section Tool details

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Section Tool details (model performance and explainability signals) | Explainability disclosure in the public ATRS record | H | external (ATRS record) | L | Plugin appends `UK ATRS, Section Tool details` to top-level citations when UK jurisdiction; the actual ATRS record is produced by `uk-atrs-recorder`. |

## ISO/IEC TR 24028:2020

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| TR 24028:2020 trustworthiness reference | Vocabulary for interpretability and explainability | A | top-level citation | L | Plugin appends the technical-report reference as informative anchor for interpretability vocabulary. |

## Composition with sibling plugins

| Sibling plugin | Direction | Relationship |
|---|---|---|
| `aisia-runner` | reads | The dedicated explainability artifact is cross-referenced from the AISIA impact-dimension assessment. AISIA touches explainability; this plugin produces the dedicated artifact. |
| `soa-generator` | cites | The Annex A Control A.8.2 SoA row points to the explainability artifact as evidence of inclusion. |
| `audit-log-generator` | records | Each invocation is a governance event recorded as an audit-log entry with Annex A control mapping including A.8.2. |
| `risk-register-builder` | consumes | Each non-empty `known_limitations` entry is a candidate residual risk surfaced into the AI risk register. |
| `crosswalk-matrix-builder` | enriches | Source of `cross_framework_citations` for MEASURE 2.9, A.8.2, and Article 86 anchors. |

## Per-method cross-plugin relationships

| Explanation method | Primary anchor | Cross-plugin consumers |
|---|---|---|
| `intrinsic-coefficients` | MEASURE 2.9 (intrinsic) | soa-generator (A.8.2 evidence), audit-log-generator (governance event) |
| `intrinsic-decision-path` | MEASURE 2.9 (intrinsic) | soa-generator, audit-log-generator |
| `shap` | MEASURE 2.9 (post-hoc local) | risk-register-builder (approximation-error limitations) |
| `lime` | MEASURE 2.9 (post-hoc local) | risk-register-builder (local-fidelity limitations) |
| `integrated-gradients` | MEASURE 2.9 (post-hoc local) | risk-register-builder (gradient-sensitivity limitations) |
| `attention-visualization` | MEASURE 2.9 (post-hoc local) | risk-register-builder (attention-faithfulness limitations) |
| `counterfactual` | MEASURE 2.9 (post-hoc local) + Article 86 | aisia-runner (affected-persons evidence), audit-log-generator |
| `feature-importance-global` | MEASURE 2.9 (post-hoc global) | soa-generator |
| `feature-importance-local` | MEASURE 2.9 (post-hoc local) + Article 86 | aisia-runner |
| `surrogate-model` | MEASURE 2.9 (post-hoc both) | risk-register-builder (surrogate-fidelity limitations) |
| `prototype-retrieval` | MEASURE 2.9 (post-hoc local) | aisia-runner (affected-persons evidence) |
| `model-card-only` | A.8.2 documentation | soa-generator (insufficient on its own for Article 86 readiness) |
