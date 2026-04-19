# aisia-runner

Executes AI System Impact Assessments (AISIAs) per ISO/IEC 42001:2023 Clause 6.1.4 and NIST AI RMF 1.0 MAP 1.1, 3.1, 3.2, 5.1. Emits `AISIA-section` artifacts, enriches each section with cross-framework citations sourced from `crosswalk-matrix-builder`, and optionally verifies coverage of EU AI Act Article 27 Fundamental Rights Impact Assessment (FRIA) content elements.

## Status

Phase 4 implementation. Serves both iso42001 T1.2 and nist-ai-rmf T1.1 with a single codebase; rendering differences are controlled by a `framework` flag. Crosswalk enrichment and EU AI Act Article 27 FRIA coverage verification are additive and default-on.

## Design stance

The plugin does NOT invent impacts. Impact identification is a judgment-bound activity requiring stakeholder consultation and domain expertise. The plugin accepts provided impact assessments, enriches each with computed scoring and control linkage, cross-references existing controls to `SoA-row` references, flags missing fields as row-level warnings, and optionally scaffolds empty placeholders for `(stakeholder, impact_dimension)` pairs without assessments so reviewers see coverage gaps.

For EU AI Act Article 27 FRIA content, the plugin does NOT generate the missing content. It verifies presence of each Article 27(1)(a)-(f) element against supplied inputs and surfaces compliance gaps as warnings; the deployer remains accountable for FRIA content itself.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | AI system info; must include `system_name` and `purpose`. Optional: `process_description` (used for Art. 27(1)(a)). |
| `affected_stakeholders` | list | yes | Non-empty list of strings or dicts with `name`. Used for Art. 27(1)(c). |
| `impact_assessments` | list | no | One entry per identified impact. Each needs `stakeholder_group`, `impact_dimension`; optional `severity`, `likelihood`, `impact_description`, `existing_controls`, `residual_severity`, `residual_likelihood`, `additional_controls_recommended`, `assessor`, `assessment_date`, `id`, `process_description`. |
| `impact_dimensions` | list | no | Dimensions to assess. Default: `fundamental-rights, group-fairness, societal, physical-safety`. `human-oversight` is recognized as a valid dimension for Art. 27(1)(e) but is not in the default list. |
| `risk_scoring_rubric` | dict | no | Must have `severity_scale` (or `impact_scale`) and `likelihood_scale`. Default: 5-level qualitative. |
| `soa_rows` | list | no | For cross-linking existing_controls to SoA rows. |
| `framework` | string | no | `iso42001` (default), `nist`, or `dual`. |
| `scaffold` | bool | no | Default False. Emit placeholder sections for uncovered pairs. |
| `reviewed_by` | string | no | |
| `enrich_with_crosswalk` | bool | no | Default True. Attaches `cross_framework_coverage` to each section by pulling ISO `A.5.2`, `A.5.4`, and `A.5.5` anchor rows from `crosswalk-matrix-builder` and filtering to the configured target frameworks. |
| `crosswalk_target_frameworks` | list[str] | no | Default `["nist-ai-rmf", "eu-ai-act"]`. Entries must be valid framework ids from `crosswalk-matrix-builder/data/frameworks.yaml`. |
| `verify_eu_fria_coverage` | bool | no | Default True. Emits the `eu_fria_coverage` top-level block checking each Article 27(1)(a)-(f) element. |
| `assessment_period` | string | no | Period covered by the AISIA. Satisfies Art. 27(1)(b). |
| `frequency` | string | no | Review frequency. Satisfies Art. 27(1)(b). |
| `affected_persons` | structure | no | Categories of natural persons affected. Complements `affected_stakeholders` for Art. 27(1)(c). |
| `human_oversight` | structure | no | Human oversight measures. Satisfies Art. 27(1)(e). |
| `mitigations` | structure | no | Mitigations if risks materialise. Satisfies Art. 27(1)(f). |
| `risks_if_materialised` | structure | no | Response plans if risks materialise. Satisfies Art. 27(1)(f). |

Missing required fields raise `ValueError`. Missing optional fields surface as warnings.

## Physical-safety severity floor

When `impact_dimension == "physical-safety"`, a severity below `moderate` triggers a warning. This is enforced because physical-harm potential is a first-class safety concern under both frameworks; a minor or negligible physical-safety severity requires explicit justification rather than being silently accepted.

## Framework citation rendering

- **iso42001** (default): every section cites `Clause 6.1.4`, `A.5.2`, `A.5.3`, and either `A.5.4` (individual and group impacts) or `A.5.5` (societal).
- **nist**: every section cites `MAP 1.1`, `MAP 3.1`, `MAP 3.2`, `MAP 5.1`; physical-safety sections also cite `MEASURE 2.6`.
- **dual**: both citation families, suitable for organizations under both frameworks.

## Cross-framework coverage per section

When `enrich_with_crosswalk` is True (default), each section gains a `cross_framework_coverage` list. Entries are sourced from `crosswalk-matrix-builder` rows where `source_framework=iso42001` and `source_ref` is one of `A.5.2`, `A.5.4`, or `A.5.5` (the impact-assessment anchor controls). Each entry has:

- `target_framework` (for example `nist-ai-rmf`, `eu-ai-act`)
- `target_ref` (for example `MAP 5.1`, `Article 27`)
- `target_title`
- `relationship` (`exact-match`, `partial-match`, `satisfies`, `partial-satisfaction`, `complementary`, `statutory-presumption`, `no-mapping`)
- `confidence` (`high`, `medium`, `low`)
- `citation` (publication string from the crosswalk row)

Sections with no crosswalk match emit a row-level warning `No cross-framework coverage found for impact_dimension=<X>` so reviewers can see gaps explicitly.

Performance note: the crosswalk data is loaded once per `run_aisia` call, indexed by `source_ref`, and filtered in-memory. The plugin does not invoke `build_matrix()` per section.

## EU AI Act Article 27 FRIA coverage verification

Article 27(1) of the EU AI Act requires deployers of high-risk AI systems to perform a Fundamental Rights Impact Assessment containing six content elements. When `verify_eu_fria_coverage` is True (default), the plugin emits a top-level `eu_fria_coverage` block reporting presence of each element:

| Key | Article 27(1) element | Satisfied by |
|---|---|---|
| `article_27_1_a_process_description` | Process description | `system_description.process_description` or any section with `process_description` |
| `article_27_1_b_period_frequency` | Period or frequency | Top-level `assessment_period` or `frequency` |
| `article_27_1_c_affected_persons` | Categories of affected persons | `affected_stakeholders` (non-empty) or `affected_persons` |
| `article_27_1_d_harms` | Specific risks of harm | Any section with `severity`, `likelihood`, and a non-empty `impact_description` |
| `article_27_1_e_human_oversight` | Human oversight measures | Top-level `human_oversight` or a section with `impact_dimension=human-oversight` |
| `article_27_1_f_if_materialised` | Measures if risks materialise | Top-level `mitigations` or `risks_if_materialised` |

Each entry has:

```python
{"present": bool, "evidence_refs": list[str]}
```

The block also carries `total_present`, `total_missing`, `compliance_gap` (list of missing element keys), `warnings` (one line per missing element), and a `citation` field set to `EU AI Act, Article 27, Paragraph 1`.

When `verify_eu_fria_coverage` is False, the `eu_fria_coverage` key is absent from output.

## Graceful failure

If the sibling crosswalk plugin fails to load (for example a missing data directory), AISIA generation succeeds with a top-level warning `Crosswalk enrichment skipped: <reason>` and sections are emitted without the `cross_framework_coverage` key. Article 27 FRIA coverage verification is independent of crosswalk loading and runs either way when `verify_eu_fria_coverage` is True.

## Outputs

Structured AISIA dict with `timestamp`, `agent_signature`, `system_name`, `system_type`, `framework`, top-level `citations`, `stakeholders`, `dimensions`, `sections`, `scaffold_sections`, `warnings`, `summary`, `reviewed_by`. When enrichment ran, includes `crosswalk_summary` with `target_frameworks`, `sections_with_coverage`, `sections_without_coverage`, `total_mappings_included`. When Article 27 verification ran, includes `eu_fria_coverage`.

Each `section` dict has: `id`, `stakeholder_group`, `impact_dimension`, `impact_description`, `severity`, `likelihood`, `existing_controls`, `residual_severity`, `residual_likelihood`, `additional_controls_recommended`, `assessor`, `assessment_date`, `process_description`, `citations`, `warnings`, and (when enrichment ran) `cross_framework_coverage`.

`render_markdown` produces an audit-ready document including per-section "Cross-framework coverage" subsections and a top-level "EU AI Act Article 27 FRIA coverage" table. CSV is not provided for AISIAs because the per-section prose and multi-control references do not compose well into tabular form.

## Example: AISIA run verifying EU Article 27 FRIA coverage

```python
from plugins.aisia_runner import plugin

inputs = {
    "system_description": {
        "system_name": "ED-Triage-Assist",
        "purpose": "Decision support for emergency department triage acuity assignment.",
        "intended_use": "RN reviews every suggestion; final acuity is RN decision.",
        "decision_authority": "decision-support",
        "process_description": (
            "Ingest chief-complaint text and vitals; gradient-boosted decision tree; "
            "output suggested ESI acuity; RN reviews and assigns final acuity."
        ),
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
        {
            "stakeholder_group": "Protected patient subgroups",
            "impact_dimension": "group-fairness",
            "impact_description": "Subgroup undertriage risk from training-data representation gaps.",
            "severity": "major",
            "likelihood": "possible",
            "existing_controls": ["A.6.2.4"],
            "residual_severity": "moderate",
            "residual_likelihood": "unlikely",
        },
    ],
    "assessment_period": "2026-Q2",
    "frequency": "annual and on material change",
    "affected_persons": [
        {"category": "presenting patients", "estimated_count_per_year": 45000},
    ],
    "human_oversight": {
        "measures": "RN reviews every suggestion; monthly override-rate audit.",
        "owner": "ED Clinical Informatics",
    },
    "mitigations": [
        "Monthly override-rate review.",
        "Quarterly subgroup-performance review.",
    ],
    "risks_if_materialised": {
        "incident_response": "Revert to non-assisted triage; notify AI Governance Committee within 24 hours.",
    },
    "crosswalk_target_frameworks": ["nist-ai-rmf", "eu-ai-act"],
    "verify_eu_fria_coverage": True,
    "reviewed_by": "AI Governance Committee, 2026-Q2",
}

aisia = plugin.run_aisia(inputs)

fria = aisia["eu_fria_coverage"]
print(f"Article 27 FRIA: {fria['total_present']}/6 elements present")
for key in fria["compliance_gap"]:
    print(f"  gap: {key}")

for section in aisia["sections"]:
    coverage = section.get("cross_framework_coverage", [])
    print(f"{section['id']} ({section['impact_dimension']}): {len(coverage)} cross-framework mappings")

print(plugin.render_markdown(aisia))
```

Example sample output for the FRIA block when all six elements are present:

```text
Article 27 FRIA: 6/6 elements present
AISIA-0001 (physical-safety): 4 cross-framework mappings
AISIA-0002 (group-fairness): 4 cross-framework mappings
```

If the caller omits `assessment_period`, `frequency`, `mitigations`, and `risks_if_materialised`, the FRIA block reports `total_missing: 2` and `compliance_gap: ["article_27_1_b_period_frequency", "article_27_1_f_if_materialised"]` with matching warnings citing `EU AI Act, Article 27, Paragraph 1(b)` and `EU AI Act, Article 27, Paragraph 1(f)`.

## Tests

```bash
python plugins/aisia-runner/tests/test_plugin.py
```

30 tests covering happy path, citation rendering in all three framework modes, physical-safety severity floor, missing-field warnings, SoA linking, scaffold emission, Markdown rendering, no-em-dash enforcement, crosswalk enrichment (on by default, opt-out works, graceful failure on crosswalk-side error), target-framework validation, and EU AI Act Article 27 FRIA coverage verification (all-present, partial-missing, opt-out).

## Related

- ISO/IEC 42001:2023, Clause 6.1.4 (AI system impact assessment)
- ISO/IEC 42001:2023, Annex A, Controls A.5.2, A.5.3, A.5.4, A.5.5
- NIST AI RMF 1.0 MAP 1.1, 3.1, 3.2, 5.1, MEASURE 2.6
- EU AI Act, Article 27, Paragraph 1(a)-(f) (FRIA content)
- Sibling plugin: [crosswalk-matrix-builder](../crosswalk-matrix-builder/README.md)
- Runtime workflow: [aigovclaw/workflows/aisia-runner.md](https://github.com/ZOLAtheCodeX/aigovclaw/blob/main/workflows/aisia-runner.md)
- Skill references: [skills/iso42001/SKILL.md](../../skills/iso42001/SKILL.md) T1.2, [skills/nist-ai-rmf/SKILL.md](../../skills/nist-ai-rmf/SKILL.md) T1.1, [skills/cross-framework-crosswalk/operationalization-map.md](../../skills/cross-framework-crosswalk/operationalization-map.md) AISIA runner section.
