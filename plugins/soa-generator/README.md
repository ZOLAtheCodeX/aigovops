# soa-generator

Generates ISO/IEC 42001:2023-compliant Statements of Applicability (SoAs).

## Status

0.2.0. Produces `SoA-row` artifacts per the iso42001 skill Tier 1 T1.1 (Clause 6.1.3). Ships with the full 38-control default Annex A list authored against the operationalization map; IDs and titles require standard-text verification for certification-grade submission. As of 0.2.0, each row is enriched by default with equivalent controls in target frameworks (NIST AI RMF, EU AI Act) via the `crosswalk-matrix-builder` plugin; enrichment is opt-out via `enrich_with_crosswalk: False`.

## Design stance

The plugin does NOT invent applicability. It reads the organization's risk register, implementation plans, explicit exclusion justifications, and scope notes, then computes one `SoA-row` per Annex A control with status derived from those inputs. Controls that lack evidence on either side (no risk linkage, no plan, no exclusion justification) are emitted with `status: excluded` and a `REQUIRES REVIEWER DECISION` justification so the human sees exactly what needs attention.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `ai_system_inventory` | list | yes | AI systems in AIMS scope. |
| `risk_register` | list | no | List of risk-register-row dicts (from `risk-register-builder`). Controls referenced in `existing_controls` of any row are marked `included-implemented`. |
| `annex_a_controls` | list | no | Custom list of `{control_id, control_title}` dicts or control_id strings. Defaults to the embedded 38-control list. |
| `implementation_plans` | dict | no | Maps control_id to a plan reference (string) or dict with `plan_ref`, `target_date`, `status` in `{planned, partial}`. |
| `exclusion_justifications` | dict | no | Maps control_id to exclusion justification text. |
| `scope_notes` | dict | no | Maps control_id to a subset-of-systems scope note. |
| `reviewed_by` | string | no | Named reviewer of the SoA. |
| `enrich_with_crosswalk` | bool | no | Default `True`. When `True`, each SoA row is enriched with equivalent controls in target frameworks via the `crosswalk-matrix-builder` plugin. Set to `False` to reproduce the pre-0.2.0 output shape. |
| `crosswalk_target_frameworks` | list[str] | no | Default `["nist-ai-rmf", "eu-ai-act"]`. Framework ids to include in cross-framework coverage. Accepted values: `iso42001`, `nist-ai-rmf`, `eu-ai-act`, `uk-atrs`, `colorado-sb-205`, `nyc-ll144`, `cppa-admt`, `ccpa-cpra`, `ca-sb-942`, `ca-ab-2013`, `ca-ab-1008`, `ca-sb-1001`, `ca-ab-1836`. Unknown ids raise `ValueError`. |

Malformed inputs raise `ValueError`. Missing evidence surfaces as warnings, not errors.

## Status derivation rules

For each Annex A control, the plugin applies these rules in order:

1. If `exclusion_justifications[control_id]` is present and non-blank, status is `excluded` with the supplied justification.
2. Otherwise, if `implementation_plans[control_id]` has `status: partial`, status is `included-partial`.
3. Otherwise, if `implementation_plans[control_id]` is present, status is `included-planned` (warns if no `target_date`).
4. Otherwise, if any `risk_register` row references the control in `existing_controls`, status is `included-implemented` with the linked risk IDs in the justification.
5. Otherwise, status is `excluded` with `REQUIRES REVIEWER DECISION` and a warning that no evidence was found.

This precedence is deliberate: explicit organizational decisions (justifications, plans) override inferred inclusion from risk linkage. An organization that has decided to exclude a control should not be contradicted by an agent.

## Outputs

A structured SoA dict:

- `timestamp`, `agent_signature`, top-level `citations`, `reviewed_by`.
- `rows`: one per Annex A control with `control_id`, `control_title`, `citation`, `status`, `justification`, `implementation_plan_ref`, `scope_note`, `last_reviewed`, `reviewed_by`, `linked_risks`, per-row `warnings`, and (when `enrich_with_crosswalk=True`) `cross_framework_coverage`.
- `summary`: `total_controls`, `status_counts` (per status), `controls_with_warnings`, `risk_register_rows_referenced`.
- `warnings`: register-level cross-check warnings (unknown controls referenced, empty risk register, crosswalk load failures).
- `crosswalk_summary`: only present when `enrich_with_crosswalk=True`. See below.

Three rendering functions: `generate_soa`, `render_markdown`, `render_csv`.

### `cross_framework_coverage` (per row)

When enrichment is on (default), each row carries a list of equivalent controls in the configured target frameworks, sourced from `crosswalk-matrix-builder`. Each entry:

```python
{
    "target_framework": "nist-ai-rmf",
    "target_ref": "MEASURE 2.5",
    "target_title": "AI system deemed valid and reliable",
    "relationship": "exact-match",
    "confidence": "high",
    "citation": "NIST AI 600-1 Appendix A",
}
```

If a row has no matches in any target framework, `cross_framework_coverage` is an empty list and a row-level warning `"No cross-framework coverage found for A.X.Y in target_frameworks=[...]"` is emitted.

If the crosswalk plugin fails to load (missing data, invariant violation), SoA generation is not aborted: a top-level warning `"Crosswalk enrichment skipped: <reason>"` is emitted, the `cross_framework_coverage` key is absent from every row, and `crosswalk_summary` reports zeroes.

### `crosswalk_summary` (top level)

```python
{
    "target_frameworks": ["nist-ai-rmf", "eu-ai-act"],
    "rows_with_coverage": 23,
    "rows_without_coverage": 15,
    "total_mappings_included": 61,
}
```

`rows_with_coverage + rows_without_coverage` equals the total SoA row count.

## Opt-out

Passing `enrich_with_crosswalk: False` reproduces the pre-0.2.0 output shape: rows carry no `cross_framework_coverage` key and the top-level dict has no `crosswalk_summary`.

## Example

```python
from plugins.soa_generator import plugin

inputs = {
    "ai_system_inventory": [{"system_ref": "SYS-001", "system_name": "ResumeScreen", "risk_tier": "limited"}],
    "risk_register": [
        {"id": "RR-0001", "existing_controls": [{"control_id": "A.5.4"}, {"control_id": "A.7.4"}]},
    ],
    "implementation_plans": {
        "A.6.2.6": {"plan_ref": "PLAN-MONITOR-2026Q3", "target_date": "2026-09-30", "status": "planned"},
    },
    "exclusion_justifications": {
        "A.10.4": "No customer-facing AI services in AIMS scope per SYS-001 being an internal HR tool.",
    },
    "reviewed_by": "AI Governance Committee, 2026-Q2",
}

soa = plugin.generate_soa(inputs)
print(plugin.render_markdown(soa))
```

### Enriched row example (NIST + EU AI Act)

With the default `enrich_with_crosswalk=True` and `crosswalk_target_frameworks=["nist-ai-rmf", "eu-ai-act"]`, row `A.6.2.4` carries:

```python
{
    "control_id": "A.6.2.4",
    "control_title": "AI system verification and validation",
    "citation": "ISO/IEC 42001:2023, Annex A, Control A.6.2.4",
    "status": "excluded",
    "justification": "REQUIRES REVIEWER DECISION: ...",
    "cross_framework_coverage": [
        {
            "target_framework": "nist-ai-rmf",
            "target_ref": "MEASURE 1.1",
            "target_title": "Metrics for measurement identified",
            "relationship": "exact-match",
            "confidence": "high",
            "citation": "NIST AI 600-1 Appendix A",
        },
        {
            "target_framework": "nist-ai-rmf",
            "target_ref": "MEASURE 2.5",
            "target_title": "AI system deemed valid and reliable",
            "relationship": "exact-match",
            "confidence": "high",
            "citation": "NIST AI 600-1 Appendix A",
        },
    ],
    ...
}
```

## Tests

```bash
python plugins/soa-generator/tests/test_plugin.py
```

28 tests covering happy path, 38-row default emission, every precedence rule, warnings on blank justifications and plans without target dates, unknown-control cross-checks, Markdown and CSV rendering, no-em-dash enforcement, and the crosswalk enrichment contract (default-on, opt-out, target-framework filter, invalid target rejection, summary counts, graceful failure on broken data).

## Related

- ISO/IEC 42001:2023, Clause 6.1.3 (AI risk treatment; Statement of Applicability)
- Upstream: [risk-register-builder](../risk-register-builder/) outputs feed the inclusion inferences.
- Upstream: [crosswalk-matrix-builder](../crosswalk-matrix-builder/) supplies the cross-framework coverage rows.
- Skill reference: [skills/iso42001/SKILL.md](../../skills/iso42001/SKILL.md) section T1.1.
- Integration pattern: [skills/cross-framework-crosswalk/operationalization-map.md](../../skills/cross-framework-crosswalk/operationalization-map.md) section `soa-generator`.
