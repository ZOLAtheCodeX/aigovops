# high-risk-classifier

Classifies an AI system under EU AI Act risk tiers: Article 5 prohibited, Article 6(1) high-risk via Annex I product-safety, Article 6(2) high-risk via Annex III, limited-risk (Article 50 transparency), or minimal-risk.

## Status

0.2.0. Phase 4 implementation plus Colorado SB 205 safe-harbor integration. Closes the Tier 2 EU AI Act operationalization gap identified in the eu-ai-act operationalization map and wires the `statutory-presumption` relationship rows from the crosswalk into deployer-facing classification output.

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
| `system_description` | dict | yes | Includes `system_name`, `intended_use`, `sector`; optional `description`, `deployment_context`, `data_processed`, `annex_i_product_type`, `annex_iii_self_declared` (list), `article_5_self_declared` (list), `article_6_3_exception_claimed` (bool), `deployer_scope` (bool), `system_type`, `consequential_decision_domains` (list of Colorado SB 205 domain tokens). |
| `reviewed_by` | string | no | |
| `assess_sb205_safe_harbor` | bool | no | Defaults to `True`. Runs the Colorado SB 205 safe-harbor assessment alongside EU AI Act classification. Set to `False` to skip entirely (no `sb205_assessment` key in output). |
| `actor_conformance_frameworks` | list[str] | no | Defaults to `[]`. Accepts `"nist-ai-rmf"` and `"iso42001"`. The frameworks the actor claims substantive conformance to. Empty list is valid; it means no claimed conformance and no safe-harbor available. |
| `actor_role_for_sb205` | string \| null | no | One of `"developer"`, `"deployer"`, `"both"`, or `null`. Required in practice when the system is in Colorado SB 205 scope; `null` surfaces an assessment warning. |

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
- `summary`: counts. Includes `sb205_in_scope` and `sb205_6_1_1706_3_applies` when the SB 205 assessment ran.
- `sb205_assessment`: present only when `assess_sb205_safe_harbor` is `True`. See below.

### `sb205_assessment` structure

When `assess_sb205_safe_harbor` is `True`, the result carries an `sb205_assessment` dict. Shape depends on whether the system is in Colorado SB 205 scope:

Out of scope:

```json
{
  "in_scope": false,
  "reason": "...",
  "safe_harbor_applicable": false
}
```

In scope:

```json
{
  "in_scope": true,
  "matched_domains": ["employment"],
  "actor_role": "deployer",
  "section_6_1_1706_3_applies": true,
  "section_6_1_1706_4_applies": true,
  "claimed_conformance": ["nist-ai-rmf"],
  "safe_harbor_citations": [
    {"section": "Colorado SB 205, Section 6-1-1706(3)", "presumption_target": "nist-ai-rmf"}
  ],
  "recommended_actions": [
    "Maintain NIST AI RMF conformance documentation",
    "If discrimination claim arises, invoke 6-1-1706(3) rebuttable presumption",
    "Continue Clause 9.2 internal audit (ISO) or continuous improvement practice (NIST MANAGE 4.2) to maintain presumption"
  ],
  "warnings": []
}
```

Section 6-1-1706(3) creates a rebuttable presumption of reasonable care against algorithmic-discrimination liability when an actor conforms substantively to NIST AI RMF or ISO/IEC 42001. Section 6-1-1706(4) extends the same posture to an affirmative-defense-on-cure pathway.

## Colorado SB 205 safe-harbor

Colorado SB 205 (the Colorado AI Act) names NIST AI RMF and ISO/IEC 42001 as recognized risk-management frameworks. Conformance establishes a rebuttable presumption of reasonable care under Section 6-1-1706(3) and supports the affirmative defense under Section 6-1-1706(4). This integration surfaces that legal posture in the same classification artifact that already reports EU AI Act risk tier, so a deployer in a Colorado consequential-decision domain sees one unified document instead of running the crosswalk separately.

Why it matters: the statutory-presumption rows in the crosswalk are the single most operationally valuable cross-framework mapping rows in the dataset. They convert conformance evidence into a defensible legal posture. The high-risk-classifier is the natural host for that surface because the classifier already knows whether the system is high-risk and already reports deployer-scope information.

The integration is additive. EU AI Act classification output is unchanged. If the crosswalk fails to load, the EU classification still renders and a top-level warning explains the skip.

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

### Example: Colorado employment deployer with NIST conformance

```python
result = plugin.classify({
    "system_description": {
        "system_name": "ResumeScreen",
        "intended_use": "Resume screening and candidate ranking for HR",
        "sector": "employment",
        "deployer_scope": True,
    },
    "actor_conformance_frameworks": ["nist-ai-rmf"],
    "actor_role_for_sb205": "deployer",
})
assert result["risk_tier"] == "high-risk-annex-iii"
sb205 = result["sb205_assessment"]
assert sb205["in_scope"] is True
assert sb205["section_6_1_1706_3_applies"] is True
assert sb205["safe_harbor_citations"] == [
    {
        "section": "Colorado SB 205, Section 6-1-1706(3)",
        "presumption_target": "nist-ai-rmf",
    },
]
```

The artifact now carries both the EU AI Act high-risk determination and the Colorado SB 205 safe-harbor citation in one record, which is the form deployers need for a defensible liability posture.

## Article 5 keyword matching

Article 5 matching uses conservative, high-recall keyword rules. The design bias is toward surfacing legal-review matches (false positives are caught in review; missed matches could mean deploying a prohibited system). Keywords cover social scoring, subliminal manipulation, untargeted facial scraping, and similar unambiguous triggers. Subtler cases (emotion recognition, biometric categorisation) use context-aware matchers that require both the practice term AND a context term (workplace, employees, students, school) to co-occur.

## Tests

```bash
python plugins/high-risk-classifier/tests/test_plugin.py
```

28 tests covering minimal-risk default, every Annex III category via keyword matching, self-declared Annex III, Article 6(3) exception handling, Article 5 matches (including context-aware emotion-recognition matcher), Article 5 precedence over Annex III, Annex I product-safety route, limited-risk triggers, citation generation, validation errors, rendering, and the Colorado SB 205 safe-harbor assessment (default-enabled, disabled-via-flag, out-of-scope, in-scope with no claimed conformance, in-scope with ISO 42001 conformance, and graceful failure when the sibling crosswalk plugin is unavailable).

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
