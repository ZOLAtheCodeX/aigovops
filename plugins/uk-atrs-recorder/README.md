# uk-atrs-recorder

Generates a structured UK Algorithmic Transparency Recording Standard (ATRS) transparency record for a public-sector algorithmic or AI-assisted decision-making tool.

Status: 0.1.0. First secondary-jurisdiction overlay per the [jurisdiction-scope policy](../../docs/jurisdiction-scope.md).

## Framework

Authoritative source: [UK Algorithmic Transparency Recording Standard, guidance for public sector bodies](https://www.gov.uk/government/publications/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies).

The ATRS is mandatory for UK Central Government departments (from February 2024) and encouraged for the wider UK public sector. Records are published on the [ATRS Hub](https://www.gov.uk/government/collections/algorithmic-transparency-recording-standard-hub).

Two tiers:

- **Tier 1.** Short, plain-English public summary covering owner, tool description, and benefits.
- **Tier 2.** Detailed technical record covering all eight canonical sections.

## Inputs

| Field | Required | Shape | Purpose |
|---|---|---|---|
| `tier` | yes | `"tier-1"` or `"tier-2"` | Selects the record depth. |
| `owner` | yes | dict | `organization`, `parent_organization`, `contact_point`, `senior_responsible_owner`. |
| `tool_description` | yes | dict | `name`, `purpose`, `how_tool_works`, `decision_subject_scope`, `phase`. |
| `tool_details` | tier-2 | dict | `model_family`, `model_type`, `system_architecture`, `training_data_summary`, `model_performance_metrics`, `third_party_components`. |
| `impact_assessment` | tier-2 | dict | `assessments_completed`, `citizen_impact_dimensions`, `severity`, `affected_groups`, `consultation_summary`. |
| `data` | tier-2 | dict | `source`, `processing_basis`, `data_categories`, `collection_method`, `sharing`, `retention`. |
| `risks` | tier-2 | list of dicts | Each: `category`, `description`, `mitigation`, `residual_risk`. |
| `governance` | tier-2 | dict | `oversight_body`, `escalation_path`, `review_cadence`, `incident_response`, `human_oversight_model`. |
| `benefits` | recommended | dict | `benefit_categories`, `measurement_approach`, `realised_benefits_summary`. |
| `reviewed_by` | optional | string | Reviewer attribution. |

Structural problems (missing required field, wrong type, invalid tier) raise `ValueError`. Content gaps surface as per-section `warnings`.

## Outputs

`generate_atrs_record(inputs)` returns a dict:

```text
timestamp: ISO 8601 UTC
agent_signature: "uk-atrs-recorder/0.1.0"
tier: "tier-1" | "tier-2"
template_version: "ATRS Template v2.0"
source_url: canonical gov.uk URL
sections: list of 8 dicts, one per ATRS section, each with:
  section: section name
  content: section-specific fields
  citations: ["UK ATRS, Section <name>"]
  warnings: list of gap descriptions
citations: top-level list (URL + template version + one per section)
summary: tier, total_sections, sections_with_warnings, total_warnings
warnings: record-level warnings (missing required sections for tier)
reviewed_by: input echo
```

`render_markdown(record)` produces a human-readable Markdown report suitable for audit evidence.

`render_csv(record)` produces a spreadsheet-ingestible CSV with one row per section (columns: `section`, `citation`, `warning_count`, `content_summary`).

## Rules

| Rule | Behaviour |
|---|---|
| Required section gating | Tier 1 requires Owner, Tool description, Benefits. Tier 2 requires all eight sections. |
| Missing required section | Surfaces a record-level warning, not a ValueError. Auditor judgment required. |
| Missing required sub-field | Surfaces a section-level warning naming the field. |
| Citation format | Every section emits `UK ATRS, Section <name>`. No other format accepted. |
| Anti-hallucination | Owner, tool description, risks, and data categories are never invented. Missing content is flagged, not filled. |

## Citation format

- Section-level: `UK ATRS, Section <name>` (for example `UK ATRS, Section Tool description`).
- Top-level: the canonical gov.uk URL plus the template version string plus one citation per section.

## Example

```python
from plugin import generate_atrs_record, render_markdown

record = generate_atrs_record({
    "tier": "tier-1",
    "owner": {
        "organization": "Department for Work and Pensions",
        "contact_point": "atrs@dwp.gov.uk",
    },
    "tool_description": {
        "name": "Benefits Eligibility Decision Support",
        "purpose": "Risk-score benefits applications for caseworker review.",
        "how_tool_works": "Gradient-boosted model scores applications; caseworker decides.",
    },
    "benefits": {
        "benefit_categories": ["processing throughput", "decision consistency"],
        "measurement_approach": "Compare median handling time and reversal rate.",
    },
})
print(render_markdown(record))
```

## Related

- Skill: [`skills/uk-atrs/SKILL.md`](../../skills/uk-atrs/SKILL.md)
- Eval: [`evals/uk-atrs/test_cases.yaml`](../../evals/uk-atrs/test_cases.yaml)
- Jurisdiction policy: [`docs/jurisdiction-scope.md`](../../docs/jurisdiction-scope.md)

## Tests

```bash
python3 plugins/uk-atrs-recorder/tests/test_plugin.py
```

Coverage: 15 tests covering happy-path tier-1 and tier-2, structural ValueError on each required field and on invalid tier, warning emission for missing tier-2 sections and missing impact-assessment references, CSV header plus row count, Markdown section completeness, prohibited-content grep (em-dash, emoji, hedging), and citation-format conformance.
