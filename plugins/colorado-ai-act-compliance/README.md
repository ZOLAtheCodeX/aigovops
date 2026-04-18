# colorado-ai-act-compliance

Operationalizes Colorado Senate Bill 24-205 (Colorado AI Act), "Concerning Consumer Protections in Interactions with Artificial Intelligence Systems." Signed 17 May 2024. Effective 1 February 2026. Codified at Colorado Revised Statutes, Title 6, Article 1, Part 17 (sections 6-1-1701 through 6-1-1707).

The plugin takes an actor description (developer, deployer, or both) and a set of consequential-decision domains, and produces a structured compliance record enumerating the obligations that apply, the documentation required, the consumer notice and appeal posture, and the citation map.

## Inputs

| Field | Type | Required | Notes |
|---|---|---|---|
| `actor_role` | string | yes | One of `developer`, `deployer`, `both`. |
| `system_description` | dict | yes | Must include `system_name`. Optional: `substantial_factor` (bool), `impact_assessment_inputs` (dict keyed by impact assessment item ids), `developer_documentation` (dict keyed by developer doc item ids), `consumer_notice_content` (dict). |
| `consequential_decision_domains` | list | yes | Zero or more of: `education`, `employment`, `financial-lending`, `essential-government`, `health-care`, `housing`, `insurance`, `legal-services`. |
| `reviewed_by` | string | no | Echoed into the output record. |

## Outputs

Dict with:

- `actor_role`, `consequential_decision_domains`, `is_high_risk`
- `developer_obligations`, `deployer_obligations` (list; each item has `id`, `title`, `citation`, `applicability` of `applies` or `not-applicable`)
- `impact_assessment_required`, `consumer_notice_required`, `consumer_appeal_required` (booleans)
- `documentation_checklist` (list; each item has `present` flag and citation)
- `warnings` (list; content gaps or classification-confirmation prompts)
- `citations` (list; Colorado SB 205 section anchors)
- `summary`, `timestamp`, `agent_signature`, `framework`

## Classification precedence

1. `actor_role == developer` and `consequential_decision_domains` non-empty: developer obligations apply; developer documentation checklist emitted.
2. `actor_role == deployer` and `consequential_decision_domains` non-empty: deployer obligations apply; impact assessment checklist emitted; consumer notice and appeal required.
3. `actor_role == both`: union of developer and deployer obligations.
4. `consequential_decision_domains` empty: `is_high_risk` is False; minimal obligations; warning emitted to confirm non-applicability.

## High-risk determination stance

Under section 6-1-1701(9), high-risk requires both (a) consequential-decision use and (b) the system making, or being a substantial factor in making, the decision. The plugin treats any non-empty domain list as meeting (a). Condition (b) is taken from `system_description.substantial_factor`:

- Absent: default True, warning emitted to confirm with counsel.
- False: `is_high_risk` is False, warning emitted.
- True: `is_high_risk` is True.

Legal determination of substantial-factor status remains with qualified Colorado counsel.

## Citation format

All citations use `Colorado SB 205, Section <section>` (for example `Colorado SB 205, Section 6-1-1703(3)`) per [STYLE.md](../../STYLE.md).

## Example invocation

```python
from plugins.colorado_ai_act_compliance import plugin

record = plugin.generate_compliance_record({
    "actor_role": "deployer",
    "system_description": {
        "system_name": "ResumeRank",
        "substantial_factor": True,
        "impact_assessment_inputs": {
            "ia-purpose-use": "Rank applicants by role fit.",
            "ia-risk-analysis": "Documented.",
            "ia-data-description": "Resumes, application metadata.",
            "ia-customization": "Per employer role taxonomy.",
            "ia-metrics": "Accuracy, FPR, FNR by protected class.",
            "ia-transparency": "Pre-decision consumer notice.",
            "ia-oversight": "Recruiter review before hire decision.",
        },
        "consumer_notice_content": {
            "text": "This hiring process uses an AI system.",
            "delivery": "candidate portal, application stage 1",
        },
    },
    "consequential_decision_domains": ["employment"],
    "reviewed_by": "Zola Valashiya (AIGP; LL.M)",
})

print(plugin.render_markdown(record))
print(plugin.render_csv(record))
```

## Related references

- [skills/colorado-ai-act/SKILL.md](../../skills/colorado-ai-act/SKILL.md) for the operationalization context.
- [skills/colorado-ai-act/operationalization-map.md](../../skills/colorado-ai-act/operationalization-map.md) for cross-framework mappings.
- Colorado SB 24-205 bill text: https://leg.colorado.gov/bills/sb24-205

## Tests

```
python3 plugins/colorado-ai-act-compliance/tests/test_plugin.py
```

14 tests cover: happy paths for developer, deployer, and both roles; non-high-risk path; validation errors on missing and invalid inputs; warning triggers for incomplete impact assessment and missing consumer notice; obligation-subset correctness per domain; CSV row count; style constraints (no em-dash, no emoji, no hedging); citation format.
