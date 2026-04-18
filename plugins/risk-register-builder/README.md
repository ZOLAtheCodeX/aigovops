# risk-register-builder

Generates ISO/IEC 42001:2023 and NIST AI RMF 1.0-compliant AI risk register entries. A single plugin serves both frameworks; rendering differences are controlled by a `framework` flag.

## Status

Phase 3 minimum-viable implementation. Produces `risk-register-row` artifacts per:

- iso42001 skill Tier 1 T1.7 (Clauses 6.1.2 AI risk assessment, 6.1.3 AI risk treatment, 8.2 operational re-assessment).
- nist-ai-rmf skill T1.3 (MAP 4.1, MANAGE 1.2, MANAGE 1.3, MANAGE 1.4).

## Design stance

The plugin does NOT invent risks. Risk identification is a hybrid activity requiring domain expertise and stakeholder consultation per Clause 6.1.2; an agent that fabricates risks produces a register that audit will reject on sight. Instead, the plugin:

1. Validates provided risks against the required schema (system_ref, category, description) and the configured taxonomy.
2. Enriches each row with computed inherent and residual scores from the rubric.
3. Cross-links `existing_controls` entries to `soa_rows` when a control_id match exists.
4. Applies `role_matrix_lookup` defaults to fill missing owner assignments from a category-to-role mapping.
5. Flags every field that requires human completion with a specific warning rather than inventing a value.
6. Optionally scaffolds empty placeholders for `(system, category)` pairs that have no identified risk, so coverage gaps are visible.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `ai_system_inventory` | list of dicts | yes | Each dict has `system_ref`, `system_name`, optional `risk_tier`. |
| `risks` | list of dicts | no (warning if empty) | Each risk must have `system_ref`, `category`, `description`. Optional: `likelihood`, `impact`, `scoring_rationale`, `existing_controls`, `residual_likelihood`, `residual_impact`, `treatment_option`, `owner_role`, `planned_treatment_actions`, `negative_residual_disclosure_ref`, `id`. |
| `framework` | string | no | One of `iso42001` (default), `nist`, `dual`. Controls citation rendering. |
| `risk_taxonomy` | list of strings | no | Defaults depend on framework: ISO default vs. NIST trustworthy-AI defaults. |
| `risk_scoring_rubric` | dict | no | Must have `likelihood_scale` and `impact_scale` lists. Default: 5-level qualitative scales. |
| `soa_rows` | list of dicts | no | Each dict has `control_id` and optional `row_ref` for linking existing controls. |
| `role_matrix_lookup` | dict | no | Maps category to default `owner_role` when a risk has no owner set. |
| `scaffold` | bool | no | Default False. Emit placeholder rows for uncovered `(system, category)` pairs. |
| `reviewed_by` | string | no | Named reviewer of the register. |
| `enrich_with_crosswalk` | bool | no | Default True. When True, each row carries a `cross_framework_citations` list produced by the sibling `crosswalk-matrix-builder` plugin. |
| `crosswalk_target_frameworks` | list of strings | no | Default `["nist-ai-rmf", "eu-ai-act"]`. Target frameworks for crosswalk enrichment. Must be ids from `plugins/crosswalk-matrix-builder/data/frameworks.yaml`. Unknown ids raise `ValueError`. |

Invalid `treatment_option` or invalid `framework` raises `ValueError`. Missing required risk fields raise `ValueError` with the risk id (if set). Other validation surfaces as warnings.

## Default taxonomies

When `risk_taxonomy` is not supplied:

- `iso42001` or `dual`: `bias, robustness, privacy, security, accountability, transparency, environmental`.
- `nist`: NIST trustworthy-AI characteristics: `valid-and-reliable, safe, secure-and-resilient, accountable-and-transparent, explainable-and-interpretable, privacy-enhanced, fair-with-bias-managed`.

## Default rubric

5-level qualitative scales:

- `likelihood_scale`: `[rare, unlikely, possible, likely, almost-certain]` (indices 1-5).
- `impact_scale`: `[negligible, minor, moderate, major, catastrophic]` (indices 1-5).

Scores are computed as `likelihood_index * impact_index`, range 1-25. Provide custom scales of any length to use a different rubric; the multiplicative rule applies the same way.

## Outputs

A structured register dict:

- `timestamp`, `agent_signature`, `framework`, `taxonomy`, `citations` (top-level).
- `rows`: one dict per enriched risk with `id`, `system_ref`, `system_name`, `category`, `description`, `likelihood`, `impact`, `inherent_score`, `scoring_rationale`, `existing_controls`, `residual_*`, `treatment_option`, `owner_role`, `planned_treatment_actions`, `negative_residual_disclosure_ref`, `citations`, per-row `warnings`.
- `scaffold_rows`: placeholder rows when `scaffold=True`.
- `warnings`: register-level warnings (for example empty register).
- `summary`: counts of rows, systems covered, rows with warnings, scaffold placeholders.
- `reviewed_by`: echoed from input.

Three rendering functions:

- `generate_risk_register(inputs)`: the structured dict.
- `render_markdown(register)`: document with summary, citations, sorted rows table (by residual risk descending), a per-row cross-framework citations subsection when enrichment ran, crosswalk summary, coverage-gap list if scaffolded, and warnings.
- `render_csv(register)`: CSV for spreadsheet ingestion. When enrichment ran, three columns are appended: `crosswalk_nist_ref` (first NIST match target_ref), `crosswalk_eu_ai_act_ref` (first EU AI Act match target_ref), `crosswalk_iso_anchor` (the ISO Annex A control used as intermediate anchor).

## Cross-framework enrichment

When `enrich_with_crosswalk` is True (default), each row gains a `cross_framework_citations` list. The builder does not re-derive mappings; it loads the `crosswalk-matrix-builder` data once per invocation and filters in-memory. Each entry is:

```json
{
  "target_framework": "nist-ai-rmf",
  "target_ref": "MEASURE 2.11",
  "target_title": "Fairness and bias evaluated",
  "iso_anchor": "A.7.4",
  "relationship": "partial-match",
  "confidence": "high",
  "citation": "NIST AI 600-1 Appendix A"
}
```

The builder maps each risk `category` to its most relevant ISO/IEC 42001 Annex A controls, then looks up the crosswalk for each anchor against the target frameworks:

| Category | ISO anchors | NIST fallback |
|---|---|---|
| `bias` | `A.7.4`, `A.6.2.4`, `A.5.2` | (none) |
| `robustness` | `A.6.2.4`, `A.6.2.5` | (none) |
| `privacy` | `A.7.5`, `A.7.2` | (none) |
| `security` | `A.6.2.5` | (none) |
| `accountability` | `A.3.2`, `A.10.2` | (none) |
| `transparency` | `A.8.2`, `A.8.5` | (none) |
| `environmental` | (no ISO anchor) | `MEASURE 2.12` |
| `safety` | `A.5.2`, `A.6.2.4` | `MEASURE 2.6` |
| `explainability` | `A.8.2`, `A.6.2.3` | `MEASURE 2.9` |
| `human-oversight` | `A.9.2` | (none) |

Where a category has no ISO anchor (for example `environmental`), the enrichment surfaces the NIST-sourced `no-mapping` entry for the relevant subcategory so the reviewer sees that the ISO framework has no direct control and the NIST framework carries the obligation alone.

Categories outside this table get no enriched citations and the row carries a warning.

The top-level `crosswalk_summary` dict echoes the target frameworks and counts:

```json
{
  "target_frameworks": ["nist-ai-rmf", "eu-ai-act"],
  "rows_with_enriched_citations": 2,
  "total_citations_added": 11
}
```

If crosswalk data is missing or invariant-invalid, enrichment is skipped with a register-level warning and rows remain without the `cross_framework_citations` key.

## Framework-specific behavior

**ISO 42001 mode (`framework: iso42001`):**

Rows cite `ISO/IEC 42001:2023, Clause 6.1.2` (always) and `Clause 8.2` (always). Adds `Clause 6.1.3` when `treatment_option` is set.

**NIST mode (`framework: nist`):**

Rows cite `MAP 4.1`, `MANAGE 1.2`, `MANAGE 1.3`. Adds `MANAGE 1.4` when `negative_residual_disclosure_ref` is set. If `treatment_option == "retain"` and no disclosure ref, surfaces a warning that MANAGE 1.4 requires disclosure of retained negative residual risks.

**Dual mode (`framework: dual`):**

Rows carry both citation families plus top-level citations from both frameworks. Appropriate for organizations operating under both standards.

## Example

```python
from plugins.risk_register_builder import plugin

inputs = {
    "ai_system_inventory": [
        {"system_ref": "SYS-001", "system_name": "ResumeScreen", "risk_tier": "limited"},
    ],
    "risks": [
        {
            "system_ref": "SYS-001",
            "category": "bias",
            "description": "Protected-group disparity in ranking outputs.",
            "likelihood": "possible",
            "impact": "major",
            "scoring_rationale": ["Quarterly equity audit 2026-Q1 output"],
            "existing_controls": ["A.5.4", "A.7.4"],
            "residual_likelihood": "unlikely",
            "residual_impact": "moderate",
            "treatment_option": "reduce",
            "owner_role": "AI Governance Officer",
            "planned_treatment_actions": ["Retrain with balanced dataset", "Quarterly equity audit"],
        },
    ],
    "soa_rows": [
        {"control_id": "A.5.4", "row_ref": "SOA-ROW-007"},
        {"control_id": "A.7.4", "row_ref": "SOA-ROW-012"},
    ],
}

register = plugin.generate_risk_register(inputs)
print(plugin.render_markdown(register))
```

With default `enrich_with_crosswalk=True`, the `bias` row above carries citations similar to:

```json
{
  "id": "RR-0001",
  "category": "bias",
  "cross_framework_citations": [
    {
      "target_framework": "nist-ai-rmf",
      "target_ref": "MEASURE 2.11",
      "target_title": "Fairness and bias evaluated",
      "iso_anchor": "A.7.4",
      "relationship": "partial-match",
      "confidence": "high",
      "citation": "NIST AI 600-1 Appendix A"
    },
    {
      "target_framework": "eu-ai-act",
      "target_ref": "Article 10, Paragraph 4",
      "target_title": "Data and data governance: bias detection and correction",
      "iso_anchor": "A.7.4",
      "relationship": "partial-match",
      "confidence": "high",
      "citation": "EU AI Act Official Journal"
    }
  ]
}
```

The pattern reads: "the bias category anchors on ISO/IEC 42001 Annex A, Control A.7.4 (Quality of data), which maps to NIST AI RMF MEASURE 2.11 and EU AI Act, Article 10, Paragraph 4." The reviewer sees one row per identified risk with all three framework citations attached.

## Scoring semantics

Scoring is multiplicative and deterministic. For the default 5-level rubric:

| likelihood \ impact | negligible(1) | minor(2) | moderate(3) | major(4) | catastrophic(5) |
|---|---|---|---|---|---|
| rare(1) | 1 | 2 | 3 | 4 | 5 |
| unlikely(2) | 2 | 4 | 6 | 8 | 10 |
| possible(3) | 3 | 6 | 9 | 12 | 15 |
| likely(4) | 4 | 8 | 12 | 16 | 20 |
| almost-certain(5) | 5 | 10 | 15 | 20 | 25 |

Organizations that use weighted scoring, additive scoring, or non-square matrices can override by supplying a full `risk_scoring_rubric` with their preferred scale lists. The multiplicative rule applies to index positions; reordering the scale reorders the scores.

## Tests

```bash
python plugins/risk-register-builder/tests/test_plugin.py
```

Runs 33 tests covering happy path, all validation error paths, score computation for inherent and residual, citation rendering in all three framework modes, MANAGE 1.4 disclosure handling for retain treatments, control-to-SoA linking, scaffold emission, Markdown ordering by residual risk, CSV rendering, cross-framework crosswalk enrichment (default-on, opt-out, category-to-ISO-anchor mapping, NIST fallback for no-ISO-anchor categories, invalid target framework rejection, graceful failure on broken crosswalk), and no-em-dash enforcement.

## Related

- ISO/IEC 42001:2023, Clause 6.1.2 (AI risk assessment)
- ISO/IEC 42001:2023, Clause 6.1.3 (AI risk treatment)
- ISO/IEC 42001:2023, Clause 8.2 (operational re-assessment)
- ISO/IEC 23894:2023 (AI risk management guidance)
- NIST AI RMF 1.0 MAP 4.1, MANAGE 1.2, MANAGE 1.3, MANAGE 1.4
- Skill references: [skills/iso42001/SKILL.md](../../skills/iso42001/SKILL.md) section T1.7, [skills/nist-ai-rmf/SKILL.md](../../skills/nist-ai-rmf/SKILL.md) section T1.3
- Companion plugins: [audit-log-generator](../audit-log-generator/), [role-matrix-generator](../role-matrix-generator/)
