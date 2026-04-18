# data-register-builder

Produces AI data register rows covering training, validation, testing, inference, reference, and benchmark datasets. Serves ISO/IEC 42001:2023 Annex A category A.7 (A.7.2 through A.7.6) and EU AI Act Article 10 (Data and data governance).

## Status

Phase 3 implementation. 0.1.0.

## Design stance

The plugin does NOT discover datasets, compute quality metrics, or analyze provenance. Dataset identification and profiling live in the data engineering stack. The plugin validates supplied dataset entries against framework requirements, enriches with computed fields (retention expiry, framework citations), flags compliance gaps per-row as warnings, and emits a structured register.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `data_inventory` | list of dicts | yes | Dataset entries. Each entry requires `id`, `name`, `purpose_stage`, `source`. See below for optional fields. |
| `ai_system_inventory` | list of dicts | no | Used for high-risk determination. Each entry with `system_ref` and `risk_tier`. |
| `retention_policy` | dict | no | Maps `data_category` to `retention_days`. Optional `default` key applies to uncategorized datasets. |
| `role_matrix_lookup` | dict | no | Maps role category strings (like `data_governance`) to role name for owner default. |
| `framework` | string | no | `iso42001` (default), `eu-ai-act`, or `dual`. |
| `reviewed_by` | string | no | |

### Per-dataset optional fields

- `system_refs`: list of AI system identifiers using this dataset.
- `acquisition_method`: required by A.7.3 for training/validation/testing.
- `provenance_chain`: list of transformation steps (A.7.5).
- `quality_checks`: dict with `accuracy`, `completeness`, `consistency`, `currency`, `validity` each as `{status, detail, method}`. Required for training/validation/testing (A.7.4, Article 10(3)).
- `representativeness_assessment`: string; required for training data under Article 10(3).
- `bias_assessment`: dict with `examined_for_bias`, `mitigation`, `method_ref`. Required for high-risk training data (Article 10(5)).
- `data_preparation_steps`: list of preparation steps (A.7.6).
- `protected_attributes`: list of protected-attribute names present.
- `data_category`: for retention lookup.
- `collection_date`: ISO 8601. Combined with retention_policy to compute `retention_expiry_date`.
- `owner_role`: data owner per Clause 5.3.

## Validation and warnings

Structural errors raise `ValueError`:

- Missing `id`, `name`, `purpose_stage`, or `source` on any dataset.
- Invalid `purpose_stage` (must be one of `training`, `validation`, `testing`, `inference`, `reference`, `benchmark`).
- Invalid `source` (must be one of `internal`, `public-open`, `public-license`, `third-party-contract`, `scraped`, `synthesized`, `other`).
- Invalid `framework`.

Content gaps surface as per-row warnings. Examples:

- Training data missing quality-check dimensions: warn citing Article 10(3) and A.7.4.
- Training data with `source: scraped` touching a high-risk system: warn citing Article 10(2).
- High-risk training data missing `bias_assessment`: warn citing Article 10(5).
- Missing `acquisition_method` for training/validation/testing: warn citing A.7.3.
- Missing `provenance_chain`: warn citing A.7.5.
- Protected attributes present without `bias_assessment`: warn.
- Missing `owner_role` when `role_matrix_lookup` has no fallback: warn citing Clause 5.3.

## Outputs

A structured register dict with:

- `timestamp`, `agent_signature`, `framework`, top-level `citations`, `reviewed_by`.
- `rows`: one per dataset with all input fields echoed plus computed `retention_expiry_date`, `citations`, and per-row `warnings`.
- `summary`: `total_datasets`, `purpose_counts`, `source_counts`, `datasets_with_warnings`, `datasets_touching_high_risk`.
- `warnings`: register-level warnings.

Three renderers: `generate_data_register`, `render_markdown`, `render_csv`.

## Citation behavior

**iso42001 mode**: every row cites `Annex A, Control A.7.2`. Training/validation/testing rows additionally cite A.7.3, A.7.4, A.7.5, A.7.6.

**eu-ai-act mode**: every row cites `Article 10, Paragraph 1` and `Paragraph 2`. Training/validation/testing rows additionally cite `Paragraph 3` and `Paragraph 4`. Rows with a bias_assessment additionally cite `Paragraph 5`.

**dual mode**: both citation families.

## Example

```python
from plugins.data_register_builder import plugin

inputs = {
    "data_inventory": [
        {
            "id": "DS-001",
            "name": "CandidateResumeCorpus-2026Q1",
            "purpose_stage": "training",
            "source": "internal",
            "system_refs": ["SYS-001"],
            "acquisition_method": "collected from internal ATS",
            "provenance_chain": [
                {"step": "extract", "tool": "ATS API"},
                {"step": "redact PII"},
            ],
            "quality_checks": {
                "accuracy": {"status": "pass"},
                "completeness": {"status": "pass"},
                "consistency": {"status": "pass"},
                "currency": {"status": "pass"},
                "validity": {"status": "pass"},
            },
            "representativeness_assessment": "Verified vs US BLS labor stats.",
            "bias_assessment": {"examined_for_bias": True, "mitigation": "rebalanced"},
            "data_preparation_steps": ["dedupe", "tokenize"],
            "protected_attributes": ["age-range"],
            "data_category": "internal-sourced",
            "collection_date": "2025-12-01T00:00:00Z",
            "owner_role": "Data Protection Officer",
        },
    ],
    "ai_system_inventory": [{"system_ref": "SYS-001", "risk_tier": "limited"}],
    "retention_policy": {"internal-sourced": 730},
    "framework": "dual",
}

register = plugin.generate_data_register(inputs)
print(plugin.render_markdown(register))
```

## Tests

```bash
python plugins/data-register-builder/tests/test_plugin.py
```

25 tests covering framework modes, retention expiry computation, all warning triggers (high-risk without bias, scraped training, missing quality dimensions, failed quality dimensions, missing provenance, missing representativeness, missing acquisition method, protected attributes without bias check, missing owner), validation errors, inference-stage exemptions, CSV rendering, and no-em-dash enforcement.

## Related

- ISO/IEC 42001:2023, Annex A, Controls A.7.2 through A.7.6
- EU AI Act, Article 10 (Data and data governance)
- NIST AI RMF 1.0, MEASURE 2.9 (privacy) and MAP 2.2 (information about AI system context)
- Upstream: data engineering pipelines, data-catalog tools, DLP scanners
- Downstream: audit-log-generator (data-lifecycle events), risk-register-builder (data-quality risks become register entries), aisia-runner (data sources inform AISIA context)
