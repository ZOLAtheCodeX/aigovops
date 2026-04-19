# explainability-documenter

Produces a dedicated explainability documentation artifact operationalizing four obligations:

- NIST AI RMF, MEASURE 2.9 (model is explained and interpretable; functionality, outputs, and associated risks are characterised).
- EU AI Act, Article 86 (right to explanation of individual decisions for affected persons of high-risk AI systems with legal or similarly significant effect).
- ISO/IEC 42001:2023, Annex A, Control A.8.2 (system documentation and information for interested parties about AI systems).
- UK Algorithmic Transparency Recording Standard, Section Tool details (model performance and explainability signals).

## Public API

- `document_explainability(inputs: dict) -> dict`
- `render_markdown(documentation: dict) -> str`
- `render_csv(documentation: dict) -> str`

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | Includes `system_name`, `purpose`, `decision_authority`, `decision_effects` (list from `legal`, `financial`, `safety-related`, `opportunity-related`, `reputation-related`, `none`, `legal-effect`, `similarly-significant-effect`), `jurisdiction`. |
| `model_type` | str | yes | One of `linear`, `tree-based`, `kernel`, `neural-network`, `deep-neural-network`, `transformer`, `ensemble`, `rule-based`, `hybrid`. |
| `explanation_methods` | list[dict] | yes | Each entry: `method`, `scope`, `target_audience`, `implementation_status`, `evidence_ref`, `known_limitations`, optional `target_date`. |
| `intrinsic_interpretability_claim` | bool | no | Default `False`. Required `True` for an intrinsic-interpretable classification on linear, tree-based, or rule-based models. |
| `art_86_response_template_ref` | str | no | Path to template for responding to individual explanation requests. |
| `previous_documentation_ref` | str | no | Reference to prior documentation artifact for version diff. |
| `enrich_with_crosswalk` | bool | no | Default `True`. Pulls cross-framework citations for the explainability anchors. |
| `crosswalk_target_frameworks` | list[str] | no | Defaults to `["nist-ai-rmf", "eu-ai-act"]`. |
| `reviewed_by` | str | no | Reviewer identifier echoed into the artifact. |

## Output

Returns a dict with `timestamp`, `agent_signature`, `framework`, `system_description_echo`, `model_type_classification`, `methods_coverage`, `scope_coverage`, `audience_coverage`, `art_86_applicability`, `art_86_readiness`, `limitations_documentation_assessment`, `citations`, `warnings`, `summary`, `reviewed_by`. When `previous_documentation_ref` is supplied, includes `schema_diff_summary`. When crosswalk enrichment runs, includes `cross_framework_citations`.

## Rule table

| Rule | Trigger | Effect |
|---|---|---|
| Intrinsic compatibility | `intrinsic_interpretability_claim=True` and `model_type` not in `{linear, tree-based, rule-based}` | Warning: incompatibility flagged. |
| Post-hoc requirement | `model_type` in `{neural-network, deep-neural-network, transformer, ensemble, kernel, hybrid}` and no post-hoc method declared | Warning per MEASURE 2.9. |
| Global-scope coverage | No method covers global scope | Warning per MEASURE 2.9. |
| Local-scope coverage | No method covers local scope | Warning per Article 86. |
| Affected-persons audience | `decision_effects` intersects `{legal, legal-effect, similarly-significant-effect}` and audience lacks `affected-persons` | BLOCKING warning per Article 86. |
| Deployer or operator audience | High-risk effect and audience lacks both `deployers` and `operators` | Warning per Article 13(3)(b). |
| Art. 86 template | Article 86 applies and `art_86_response_template_ref` empty | Warning. |
| Limitation transparency | Any method with empty `known_limitations` | Warning per MEASURE 2.9. |
| not-applicable rationale | `implementation_status=not-applicable` and `known_limitations` empty | Warning. |
| planned target date | `implementation_status=planned` and no `target_date` | Warning. |

## Anti-hallucination invariants

The plugin does not invent explanation methods. The plugin does not verify that `evidence_ref` paths exist. Each declared method is echoed verbatim with its scope, audience, status, and limitations. The plugin computes only deterministic coverage and consistency checks.

## Citations

Citations carried at top level:

- `NIST AI RMF, MEASURE 2.9`
- `ISO/IEC 42001:2023, Annex A, Control A.8.2`
- `ISO/IEC TR 24028:2020`
- `EU AI Act, Article 86, Paragraph 1` (when applicable)
- `EU AI Act, Article 13, Paragraph 3, Point (b)` (when applicable)
- `UK ATRS, Section Tool details` (when UK jurisdiction)

## Example

```python
from plugins.explainability_documenter.plugin import document_explainability, render_markdown

inputs = {
    "system_description": {
        "system_name": "Credit decisioning model",
        "purpose": "Consumer credit decisions",
        "decision_authority": "automated-with-human-review",
        "decision_effects": ["legal", "financial"],
        "jurisdiction": "eu",
    },
    "model_type": "tree-based",
    "explanation_methods": [
        {
            "method": "intrinsic-decision-path",
            "scope": "both",
            "target_audience": ["developers", "deployers", "affected-persons"],
            "implementation_status": "implemented",
            "evidence_ref": "docs/decision-path-export.pdf",
            "known_limitations": [
                "Shallow trees lose interaction effects",
                "Paths do not quantify uncertainty",
            ],
        },
    ],
    "intrinsic_interpretability_claim": True,
    "art_86_response_template_ref": "templates/art86-response.md",
}

doc = document_explainability(inputs)
print(render_markdown(doc))
```

## Composition

| Sibling plugin | Relationship |
|---|---|
| `aisia-runner` | Touches explainability inside the impact dimension assessment; this plugin produces the dedicated explainability artifact that AISIA cross-references. |
| `soa-generator` | Cites Annex A Control A.8.2 at SoA-row level; this plugin produces the A.8.2 content. |
| `audit-log-generator` | Records explainability documentation events as governance audit log entries. |
| `risk-register-builder` | Consumes `known_limitations` as risk inputs for explanation-method residual risk. |
| `crosswalk-matrix-builder` | Source of `cross_framework_citations` enrichment. |

## Determinism

Output is deterministic for deterministic input apart from the `timestamp` field.
