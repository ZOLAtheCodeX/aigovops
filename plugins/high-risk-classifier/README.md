# high-risk-classifier

Classifies an AI system under EU AI Act risk tiers: Article 5 prohibited, Article 6(1) high-risk via Annex I product-safety, Article 6(2) high-risk via Annex III, limited-risk (Article 50 transparency), or minimal-risk.

## Status

Phase 4 implementation. Closes the Tier 2 EU AI Act operationalization gap identified in the eu-ai-act operationalization map.

## Design stance

The plugin does NOT make final legal classifications. Article 5 prohibited-practice determinations and Article 6(3) exception claims require qualified legal counsel. The plugin:

- Screens the system description against the Article 5 prohibited-practice categories and Annex III high-risk categories using a deterministic rule set.
- For any match, classifies the result as `requires-legal-review` rather than silently deciding.
- Provides citation anchors, rationale, and explicit matches so legal review has the evidence it needs.

## Classification precedence

1. Article 5 prohibited-practice match → `requires-legal-review` (legal call).
2. Annex I product-safety route declared → `high-risk-annex-i`.
3. Annex III match without Article 6(3) exception claim → `high-risk-annex-iii`.
4. Annex III match with Article 6(3) exception claim → `requires-legal-review` (exception validation is legal).
5. Article 50 transparency trigger without high-risk → `limited-risk`.
6. None of the above → `minimal-risk`.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | Includes `system_name`, `intended_use`, `sector`; optional `description`, `deployment_context`, `data_processed`, `annex_i_product_type`, `annex_iii_self_declared` (list), `article_5_self_declared` (list), `article_6_3_exception_claimed` (bool), `deployer_scope` (bool), `system_type`. |
| `reviewed_by` | string | no | |

### Self-declaration fields

Organizations with clear knowledge of their system's classification can self-declare:

- `annex_iii_self_declared`: list of Annex III category keys (`biometrics`, `critical-infrastructure`, `education`, `employment-workers-management`, `essential-services`, `law-enforcement`, `migration-asylum-border`, `justice-democracy`). Bypasses keyword matching for declared categories.
- `article_5_self_declared`: list of Article 5 category keys. Same bypass pattern.
- `annex_i_product_type`: string naming the Annex I legislation (Medical Device Regulation, Machinery Regulation, and so on). Triggers Article 6(1) high-risk.
- `article_6_3_exception_claimed`: True if the organization has analyzed Article 6(3) and believes the system does not pose significant risk. The plugin does not accept this claim silently; it flags for legal review.

## Outputs

Structured classification record with:

- `timestamp`, `agent_signature`, `framework`, `system_description_echo`, `reviewed_by`.
- `risk_tier`: one of `prohibited`, `high-risk-annex-iii`, `high-risk-annex-i`, `limited-risk`, `minimal-risk`, `requires-legal-review`.
- `rationale`: multi-paragraph explanation.
- `annex_iii_matches`: list of matched Annex III categories with source (`self-declared` or `keyword-match`).
- `article_5_matches`: list of matched Article 5 prohibition categories.
- `annex_i_match`: dict when Annex I product-safety route applies, else null.
- `requires_legal_review`: bool.
- `citations`: list of EU AI Act Article references.
- `warnings`: register-level issues.
- `summary`: counts.

## Example

```python
from plugins.high_risk_classifier import plugin

result = plugin.classify({
    "system_description": {
        "system_name": "ResumeScreen",
        "intended_use": "Resume screening and candidate ranking for HR",
        "sector": "HR",
        "deployer_scope": True,
    },
})
print(result["risk_tier"])
# "high-risk-annex-iii"
print(plugin.render_markdown(result))
```

Expected output: high-risk-annex-iii classification with matches against the `employment-workers-management` Annex III category. Citations include Article 6(2), Annex III, plus Articles 26 and 27 because `deployer_scope` is True.

## Article 5 keyword matching

Article 5 matching uses conservative, high-recall keyword rules. The design bias is toward surfacing legal-review matches (false positives are caught in review; missed matches could mean deploying a prohibited system). Keywords cover social scoring, subliminal manipulation, untargeted facial scraping, and similar unambiguous triggers. Subtler cases (emotion recognition, biometric categorisation) use context-aware matchers that require both the practice term AND a context term (workplace, employees, students, school) to co-occur.

## Tests

```bash
python plugins/high-risk-classifier/tests/test_plugin.py
```

22 tests covering minimal-risk default, every Annex III category via keyword matching, self-declared Annex III, Article 6(3) exception handling, Article 5 matches (including context-aware emotion-recognition matcher), Article 5 precedence over Annex III, Annex I product-safety route, limited-risk triggers, citation generation, validation errors, and rendering.

## Related

- EU AI Act, Article 5 (prohibited practices)
- EU AI Act, Article 6 (classification rules for high-risk)
- EU AI Act, Annex I (Union harmonisation legislation list)
- EU AI Act, Annex III (high-risk AI systems list)
- EU AI Act, Article 50 (transparency obligations)
- EU AI Act, Articles 26-27 (deployer obligations + FRIA)
- Skill reference: `skills/eu-ai-act/operationalization-map.md` Tier 2 item "high-risk-classification engine"
- Upstream: AI system inventory workflow
- Downstream: `applicability-checker` consumes the classification to determine which provisions apply; `aisia-runner` runs the FRIA for high-risk deployers; `risk-register-builder` produces Article 9 risk register for high-risk systems
