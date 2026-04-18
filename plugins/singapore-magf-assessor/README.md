# singapore-magf-assessor

Assesses an AI system against the Singapore Model AI Governance Framework, Second Edition (MAGF 2e). For organizations in the financial-services sector, layers the MAS FEAT Principles (2018) on top. Emits a pillar-by-pillar structured assessment with AI Verify principle coverage as a static lookup.

## Scope

- Singapore MAGF 2e (IMDA + PDPC, January 2020). Four pillars: Internal Governance Structures and Measures; Determining the Level of Human Involvement in AI-Augmented Decision-Making; Operations Management; Stakeholder Interaction and Communication.
- MAS FEAT Principles (2018). Four principles (Fairness, Ethics, Accountability, Transparency) with MAS-published sub-criteria. Applied only when `organization_type == "financial-services"`.
- AI Verify (IMDA 2024). Eleven ethics principles mapped to MAGF pillars as a static lookup table; the plugin does not run AI Verify technical tests.
- Veritas (MAS) is not implemented; the methodology requires the Veritas toolkit.

## Inputs

```python
{
    "system_description": {
        "system_name": "ResumeRank",
        "human_involvement_tier": "human-in-the-loop",
        "pillar_evidence": {
            "internal-governance": {"role_assignments": "...", "risk_controls": "...", "staff_training": "..."},
            "human-involvement": {"human_involvement_tier": "...", "risk_matrix": "...", "escalation_process": "..."},
            "operations-management": {"data_lineage": "...", "data_quality": "...", "bias_mitigation": "...",
                                      "model_robustness": "...", "explainability": "...", "reproducibility": "...",
                                      "monitoring": "..."},
            "stakeholder-communication": {"disclosure_policy": "...", "feedback_channel": "...",
                                          "decision_review_process": "..."},
        },
        "feat_evidence": {
            "fairness": {...}, "ethics": {...}, "accountability": {...}, "transparency": {...}
        }
    },
    "organization_type": "financial-services",
    "reviewed_by": "Zola Valashiya"
}
```

Required: `system_description`, `organization_type`.

## Valid enums

- `organization_type`: `general`, `financial-services`, `healthcare`, `government`, `other`.
- `human_involvement_tier`: `human-in-the-loop`, `human-over-the-loop`, `human-out-of-the-loop`.

## Outputs

`generate_magf_assessment(inputs)` returns:

| Field | Meaning |
|---|---|
| `applicable_frameworks` | `["magf"]` or `["magf", "feat"]` |
| `pillars` | 4 MAGF pillar evaluations, each with `assessment_status` (`addressed`, `partial`, `not-addressed`), `evidence_refs`, `warnings`, `citation` |
| `feat_principles` | present only if financial-services; 4 MAS FEAT principles, each with `sub_criteria`, `assessment_status`, `evidence_refs`, `warnings`, `citation` |
| `human_involvement_tier` | tier, note, and citation |
| `ai_verify_principles_coverage` | 11 AI Verify principles mapped to MAGF pillars |
| `citations` | register-level canonical citations |
| `warnings` | register-level content-gap warnings |
| `summary` | aggregate counts |

`render_markdown(assessment)` produces the audit-evidence Markdown rendering. `render_csv(assessment)` produces one row per pillar and one row per FEAT principle.

## Citation formats

- `Singapore MAGF 2e, Pillar <name>` or `Singapore MAGF 2e, Section <section>`
- `MAS FEAT Principles (2018), Principle <name>`
- `AI Verify (IMDA 2024), Principle <name>`

## Rule table

| Rule | Behavior |
|---|---|
| Applicability | `financial-services` -> MAGF plus FEAT. All other org types -> MAGF only. |
| Pillar status | `addressed` if every evidence key populated; `partial` if some; `not-addressed` if none. |
| FEAT status | `addressed` if evidence is a dict covering every sub-criterion; `partial` if fewer; `not-addressed` if absent. |
| Human involvement default | Missing tier defaults to `human-in-the-loop` with a warning. |
| Invalid inputs | ValueError on missing required fields, invalid enum values. |
| Content gaps | Surface as warnings at row and register level. |

## Example

```python
from plugin import generate_magf_assessment, render_markdown

inputs = {
    "organization_type": "general",
    "system_description": {
        "system_name": "HRScreen",
        "human_involvement_tier": "human-in-the-loop",
        "pillar_evidence": { ... },
    },
}
assessment = generate_magf_assessment(inputs)
print(render_markdown(assessment))
```

## Related

- Skill: `skills/singapore-ai-governance/`
- Crosswalk: `plugins/crosswalk-matrix-builder/data/singapore-magf-crosswalk.yaml`
- Eval: `evals/singapore-ai-governance/test_cases.yaml`
