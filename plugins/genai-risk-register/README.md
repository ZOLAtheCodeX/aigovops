# genai-risk-register

Operationalizes the NIST AI 600-1 (July 2024) Generative AI Profile's 12-risk catalogue as a dedicated GenAI risk register. Distinct from the general-purpose `risk-register-builder`, which operates over ISO/IEC 42001 and NIST AI RMF taxonomies. This plugin applies only to generative AI systems and cross-maps each risk to the AI RMF subcategories named in NIST AI 600-1 Appendix A, plus jurisdiction-specific obligations in the EU AI Act (Articles 50 and 55) and California statutes (SB 942, AB 2013, AB 1008).

## Status

0.1.0. Phase 4 implementation. Closes the GenAI-specific gap in the risk-register family.

## Design stance

The plugin does NOT invent risk evaluations. The practitioner supplies a likelihood, impact, and existing-mitigations record per risk. The plugin validates 12-risk coverage, computes per-risk NIST cross-references, flags residual-risk logic errors, escalates high-residual rows, and emits the artifact as JSON, Markdown, and CSV. The `is_generative` guard on `system_description` is load-bearing: non-generative systems must use `risk-register-builder`.

## NIST AI 600-1 risk catalogue

The 12 risks (`GENAI_RISKS`):

| risk_id | Description |
|---|---|
| `cbrn-information-capabilities` | GenAI producing uplift for chemical, biological, radiological, nuclear weapons. |
| `confabulation` | Fabricating plausible-sounding but incorrect or inconsistent outputs. |
| `dangerous-violent-hateful-content` | Model producing harmful content. |
| `data-privacy` | Training data memorization and extraction risks. |
| `environmental-impacts` | Energy and resource consumption of training and inference. |
| `harmful-bias-homogenization` | Amplified bias and reduced diversity of outputs. |
| `human-ai-configuration` | Over-reliance, automation bias, ill-calibrated trust. |
| `information-integrity` | Deepfakes, synthetic media, disinformation. |
| `information-security` | Prompt injection, jailbreak, model extraction. |
| `intellectual-property` | Training data IP infringement, generated-content IP attribution. |
| `obscene-degrading-abusive-content` | NCII, CSAM risks. |
| `value-chain-component-integration` | Supply chain risks specific to GenAI (fine-tuning base models, prompt injection via third-party tools). |

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | `is_generative` MUST be True. Other fields: `system_id`, `model_type`, `modality`, `training_data_scope`, `deployment_context`, `jurisdiction` (list of lowercase codes such as `eu`, `usa-ca`), `base_model_ref`. |
| `risk_evaluations` | list | yes | One dict per evaluated risk. See per-risk schema below. |
| `risks_not_applicable` | list | no | List of `{risk_id, rationale}` dicts. Risks marked not-applicable without a rationale emit a warning. |
| `cross_reference_refs` | dict | no | `gpai_obligations_ref`, `supplier_assessment_ref`, `bias_evaluation_ref`. Used to trigger jurisdiction-specific systemic-risk citations. |
| `previous_register_ref` | dict or list | no | Previous register output (or list of normalized rows) for version diff. |
| `enrich_with_crosswalk` | bool | no | Default True. |
| `reviewed_by` | string | no | Reviewer identity. |

### Per-risk evaluation schema

```python
{
    "risk_id": "cbrn-information-capabilities",
    "likelihood": "rare",
    "impact": "catastrophic",
    "inherent_score": 15,
    "existing_mitigations": [{"name": "...", "description": "...", "evidence_ref": "..."}],
    "mitigation_status": "partial",
    "residual_likelihood": "rare",
    "residual_impact": "major",
    "residual_score": 10,
    "owner_role": "AI Safety Lead",
    "review_date": "2026-04-18",
    "notes": "..."
}
```

Enums: `likelihood` in `VALID_LIKELIHOOD`, `impact` in `VALID_IMPACT`, `mitigation_status` in `VALID_MITIGATION_STATUSES`.

## Rule tables

### NIST subcategory mapping (Appendix A)

| risk_id | Subcategories |
|---|---|
| `cbrn-information-capabilities` | GOVERN 1.1, MAP 1.1, MEASURE 2.6 |
| `confabulation` | MEASURE 2.5, MEASURE 2.8 |
| `dangerous-violent-hateful-content` | MAP 5.1, MANAGE 2.2 |
| `data-privacy` | MEASURE 2.10 |
| `environmental-impacts` | MEASURE 2.12 |
| `harmful-bias-homogenization` | MEASURE 2.11 |
| `human-ai-configuration` | MANAGE 2.3, MEASURE 3.3 |
| `information-integrity` | MEASURE 2.7, MEASURE 2.8 |
| `information-security` | MEASURE 2.7 |
| `intellectual-property` | GOVERN 1.4, GOVERN 6.1 |
| `obscene-degrading-abusive-content` | MAP 5.1, MANAGE 2.2 |
| `value-chain-component-integration` | GOVERN 6.1, GOVERN 6.2 |

### Jurisdiction-triggered cross-references

| Jurisdiction | Risk | Citations added |
|---|---|---|
| `eu` | `information-integrity` | EU AI Act Article 50(2), 50(4) |
| `eu` + `gpai_obligations_ref` | `information-security` | EU AI Act Article 55(1)(a) |
| `eu` + `gpai_obligations_ref` | `value-chain-component-integration` | EU AI Act Article 55(1)(d) |
| `usa-ca` | `information-integrity` | Cal. Bus. & Prof. Code Section 22757 (SB 942) |
| `usa-ca` | `data-privacy` | California AB 2013 Section 1; Cal. Civ. Code Section 1798.140(v) (AB 1008) |
| `usa-ca` | `intellectual-property` | California AB 2013 Section 1 |

### Residual risk logic checks

| Condition | Action |
|---|---|
| `residual_score > inherent_score` | Warning: check mitigation logic. |
| `mitigation_status = implemented` AND `residual_score == inherent_score` | Warning: implemented mitigation should lower residual risk. |
| `residual_score >= 15` (5x5 scale; max 25) | Critical flag + escalation to incident-reporting + management-review. |

### Coverage check

Expected: an evaluation entry for each of the 12 GenAI risks, unless listed in `risks_not_applicable` with a non-empty rationale. Missing or rationale-less entries emit a warning. The plugin does not refuse to render an incomplete register; it surfaces gaps for the practitioner to close.

## Outputs

Structured dict with `timestamp`, `agent_signature`, `framework`, `system_description_echo`, `risk_evaluations_normalized`, `coverage_assessment`, `per_risk_nist_coverage`, `jurisdiction_cross_references`, `residual_risk_flags`, `version_diff` (when `previous_register_ref` supplied), `citations`, `cross_framework_citations` (when enriched), `warnings`, `summary`, `reviewed_by`.

Three renderers: `generate_genai_risk_register`, `render_markdown`, `render_csv`.

## Example

```python
import plugin

result = plugin.generate_genai_risk_register({
    "system_description": {
        "system_id": "genai-001",
        "model_type": "LLM",
        "modality": "text",
        "is_generative": True,
        "training_data_scope": "public-web + curated",
        "deployment_context": "customer-facing chatbot",
        "jurisdiction": ["eu", "usa-ca"],
        "base_model_ref": "ExampleLM-7B",
    },
    "risk_evaluations": [
        {
            "risk_id": "confabulation",
            "likelihood": "likely",
            "impact": "moderate",
            "inherent_score": 12,
            "mitigation_status": "implemented",
            "existing_mitigations": [{"name": "RAG", "description": "retrieval grounding"}],
            "residual_likelihood": "possible",
            "residual_impact": "minor",
            "residual_score": 6,
            "owner_role": "ML Lead",
            "review_date": "2026-04-18",
        },
        # ... 11 more risks ...
    ],
    "cross_reference_refs": {"gpai_obligations_ref": "/artifacts/gpai.json"},
})
print(plugin.render_markdown(result))
```

## Anti-hallucination invariants

1. The plugin refuses non-generative systems via the `is_generative` guard. Use `risk-register-builder` for non-generative AI.
2. The plugin does not invent risk evaluations. Likelihood, impact, mitigations, owner, and review date are practitioner-supplied.
3. The plugin computes `inherent_score` and `residual_score` only when both axes are present and valid. Otherwise the field is None and a warning is emitted.
4. The plugin does not adjudicate the legal adequacy of a mitigation. Status enums (`implemented`, `partial`, etc.) are recorded as input.
5. The plugin does not file incident reports. Critical residual flags emit an escalation recommendation; the `incident-reporting` plugin handles deadline-aware filing.

## Composition with other plugins

- `gpai-obligations-tracker` for EU AI Act Article 53 to 55 coverage when the system is a GPAI; supply the artifact path as `cross_reference_refs.gpai_obligations_ref`.
- `bias-evaluator` for the `harmful-bias-homogenization` evaluation evidence (NYC LL144 four-fifths rule and adjacent metrics).
- `supplier-vendor-assessor` for `value-chain-component-integration` upstream-provider review.
- `system-event-logger` for `information-integrity` and `information-security` operational evidence.
- `incident-reporting` when a residual flag fires.
- `management-review-packager` for periodic register review.
- `crosswalk-matrix-builder` for cross-framework subcategory coverage.

## Citation formats

All citations follow [STYLE.md](../../STYLE.md):

- `NIST AI 600-1, Section <section>` and `NIST AI 600-1, Appendix A`.
- `NIST AI RMF, <FUNCTION> <Subcategory>` per risk.
- `EU AI Act, Article 50, Paragraph <n>` for synthetic content marking and deepfake labelling.
- `EU AI Act, Article 55, Paragraph 1, Point (<letter>)` for systemic-risk obligations.
- `Cal. Bus. & Prof. Code Section 22757` for CA SB 942.
- `California AB 2013, Section <section>` for training-data transparency.
- `Cal. Civ. Code Section 1798.140(v)` for CA AB 1008.
