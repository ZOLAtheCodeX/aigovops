# aisia-runner

Executes AI System Impact Assessments (AISIAs) per ISO/IEC 42001:2023 Clause 6.1.4 and NIST AI RMF 1.0 MAP 1.1, 3.1, 3.2, 5.1. Emits `AISIA-section` artifacts.

## Status

Phase 3 minimum-viable implementation. Serves both iso42001 T1.2 and nist-ai-rmf T1.1 with a single codebase; rendering differences are controlled by a `framework` flag.

## Design stance

The plugin does NOT invent impacts. Impact identification is a judgment-bound activity requiring stakeholder consultation and domain expertise. The plugin accepts provided impact assessments, enriches each with computed scoring and control linkage, cross-references existing controls to `SoA-row` references, flags missing fields as row-level warnings, and optionally scaffolds empty placeholders for `(stakeholder, impact_dimension)` pairs without assessments so reviewers see coverage gaps.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | AI system info; must include `system_name` and `purpose`. |
| `affected_stakeholders` | list | yes | Non-empty list of strings or dicts with `name`. |
| `impact_assessments` | list | no | One entry per identified impact. Each needs `stakeholder_group`, `impact_dimension`; optional `severity`, `likelihood`, `impact_description`, `existing_controls`, `residual_severity`, `residual_likelihood`, `additional_controls_recommended`, `assessor`, `assessment_date`, `id`. |
| `impact_dimensions` | list | no | Dimensions to assess. Default: `fundamental-rights, group-fairness, societal, physical-safety`. |
| `risk_scoring_rubric` | dict | no | Must have `severity_scale` (or `impact_scale`) and `likelihood_scale`. Default: 5-level qualitative. |
| `soa_rows` | list | no | For cross-linking existing_controls to SoA rows. |
| `framework` | string | no | `iso42001` (default), `nist`, or `dual`. |
| `scaffold` | bool | no | Default False. Emit placeholder sections for uncovered pairs. |
| `reviewed_by` | string | no | |

Missing required fields raise `ValueError`. Missing optional fields surface as warnings.

## Physical-safety severity floor

When `impact_dimension == "physical-safety"`, a severity below `moderate` triggers a warning. This is enforced because physical-harm potential is a first-class safety concern under both frameworks; a minor or negligible physical-safety severity requires explicit justification rather than being silently accepted.

## Framework citation rendering

- **iso42001** (default): every section cites `Clause 6.1.4`, `A.5.2`, `A.5.3`, and either `A.5.4` (individual and group impacts) or `A.5.5` (societal).
- **nist**: every section cites `MAP 1.1`, `MAP 3.1`, `MAP 3.2`, `MAP 5.1`; physical-safety sections also cite `MEASURE 2.6`.
- **dual**: both citation families, suitable for organizations under both frameworks.

## Outputs

Structured AISIA dict with `timestamp`, `agent_signature`, `system_name`, `system_type`, `framework`, top-level `citations`, `stakeholders`, `dimensions`, `sections`, `scaffold_sections`, `warnings`, `summary`, `reviewed_by`.

Each `section` dict has: `id`, `stakeholder_group`, `impact_dimension`, `impact_description`, `severity`, `likelihood`, `existing_controls`, `residual_severity`, `residual_likelihood`, `additional_controls_recommended`, `assessor`, `assessment_date`, `citations`, `warnings`.

`render_markdown` produces an audit-ready document. CSV is not provided for AISIAs because the per-section prose and multi-control references do not compose well into tabular form; the Markdown is the submission format.

## Example

```python
from plugins.aisia_runner import plugin

inputs = {
    "system_description": {
        "system_name": "ED-Triage-Assist",
        "purpose": "Decision support for emergency department triage acuity assignment.",
        "intended_use": "RN reviews every suggestion; final acuity is RN decision.",
        "decision_authority": "decision-support",
    },
    "affected_stakeholders": [
        "Presenting patients",
        "ED clinical staff",
        {"name": "Protected patient subgroups", "protected_attributes": ["age", "race", "primary-language"]},
    ],
    "impact_assessments": [
        {
            "stakeholder_group": "Presenting patients",
            "impact_dimension": "physical-safety",
            "impact_description": "Incorrect triage acuity could delay emergent care.",
            "severity": "major",
            "likelihood": "unlikely",
            "existing_controls": ["A.6.2.4", "A.6.2.6"],
            "residual_severity": "moderate",
            "residual_likelihood": "rare",
            "assessor": "Clinical Informatics",
            "assessment_date": "2026-04-01",
        },
    ],
    "scaffold": True,
    "reviewed_by": "AI Governance Committee, 2026-Q2",
}

aisia = plugin.run_aisia(inputs)
print(plugin.render_markdown(aisia))
```

## Tests

```bash
python plugins/aisia-runner/tests/test_plugin.py
```

23 tests covering happy path, citation rendering in all three framework modes, physical-safety severity floor, missing-field warnings, SoA linking, scaffold emission, Markdown rendering, and no-em-dash enforcement.

## Related

- ISO/IEC 42001:2023, Clause 6.1.4 (AI system impact assessment)
- ISO/IEC 42001:2023, Annex A, Controls A.5.2, A.5.3, A.5.4, A.5.5
- NIST AI RMF 1.0 MAP 1.1, 3.1, 3.2, 5.1, MEASURE 2.6
- Runtime workflow: [aigovclaw/workflows/aisia-runner.md](https://github.com/ZOLAtheCodeX/aigovclaw/blob/main/workflows/aisia-runner.md)
- Skill references: [skills/iso42001/SKILL.md](../../skills/iso42001/SKILL.md) T1.2, [skills/nist-ai-rmf/SKILL.md](../../skills/nist-ai-rmf/SKILL.md) T1.1.
