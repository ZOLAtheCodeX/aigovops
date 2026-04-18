# gap-assessment

Assesses an organization's current AIMS state against a target framework (ISO 42001, NIST AI RMF, EU AI Act) and produces a structured gap report with classification and next-step recommendation per control or subcategory.

## Status

Phase 3 minimum-viable implementation. Serves the aigovclaw `gap-assessment` runtime workflow; this plugin replaces the workflow's stub state.

## Design stance

The plugin does NOT infer coverage without evidence. Every classification is grounded in one of:

1. An SoA row from a prior `soa-generator` emission (ISO 42001 only; the SoA's `status` is the authoritative inclusion signal).
2. An explicit evidence reference in `current_state_evidence`.
3. A manual classification override (organizational decision, typically for not-applicable).
4. An explicit exclusion justification.

Controls with no evidence default to `not-covered` with a `REQUIRES REVIEWER DECISION` justification. Same "no silent guessing" stance as `soa-generator` and `role-matrix-generator`.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `ai_system_inventory` | list | yes | Systems in scope. |
| `target_framework` | string | yes | `iso42001`, `nist`, or `eu-ai-act`. |
| `targets` | list | required for nist/eu-ai-act; optional for iso42001 (defaults to 38 Annex A controls) | List of `{id, title}` dicts or id strings. |
| `soa_rows` | list | no | Prior `soa-generator` output; used for iso42001 coverage inference. |
| `current_state_evidence` | dict | no | Maps target_id to a list of refs, a single ref string, or `{refs, strength, justification}` where strength is `full` or `partial`. |
| `manual_classifications` | dict | no | Maps target_id to classification string or `{classification, justification}`. |
| `exclusion_justifications` | dict | no | Maps target_id to justification text for not-applicable. |
| `scope_boundary` | string | no | AIMS scope description for report context. |
| `reviewed_by` | string | no | |

Invalid `target_framework` or invalid classification value raises `ValueError`. Missing `targets` for nist or eu-ai-act raises `ValueError`. Content gaps surface as warnings.

## Classification precedence

For each target, in order:

1. `manual_classifications[target_id]` overrides everything (organizational decision).
2. `exclusion_justifications[target_id]` (non-blank) → `not-applicable`.
3. `soa_rows[target_id]` (iso42001 only) status mapped: `included-implemented` → covered; `included-partial` → partially-covered; `included-planned` → not-covered; `excluded` → not-applicable.
4. `current_state_evidence[target_id]` present → `covered` (or `partially-covered` if strength is `partial`).
5. Default: `not-covered` with `REQUIRES REVIEWER DECISION`.

## Outputs

Assessment dict with:

- `timestamp`, `agent_signature`, `target_framework`, `scope_boundary`, top-level `citations`, `reviewed_by`.
- `rows`: one per target with `target_id`, `target_title`, `citation`, `classification`, `justification`, `next_step`, per-row `warnings`.
- `summary`: `target_framework`, `total_targets`, `classification_counts`, `targets_with_warnings`, `coverage_score` (weighted ratio: covered plus half of partially-covered, divided by total applicable).
- `warnings`: register-level warnings (unknown target ids in evidence, and so on).

Three renderers: `generate_gap_assessment`, `render_markdown`, `render_csv`.

## Example

```python
from plugins.gap_assessment import plugin

inputs = {
    "ai_system_inventory": [{"system_ref": "SYS-001", "system_name": "ResumeScreen"}],
    "target_framework": "iso42001",
    "soa_rows": [
        {"control_id": "A.5.4", "status": "included-implemented", "justification": "AISIA process active."},
        {"control_id": "A.7.4", "status": "included-partial", "justification": "Partial data-quality implementation."},
        {"control_id": "A.10.4", "status": "excluded", "justification": "No customer-facing AI."},
    ],
    "current_state_evidence": {
        "A.3.2": ["ROLE-MATRIX-2026-Q2"],
        "A.6.2.3": {"strength": "partial", "refs": ["DESIGN-DOC-2026-001"], "justification": "Partial: deployment docs pending."},
    },
    "exclusion_justifications": {
        "A.9.3": "No generative use in AIMS scope.",
    },
    "scope_boundary": "All AI systems in HR processes.",
    "reviewed_by": "AI Governance Committee, 2026-Q2",
}

assessment = plugin.generate_gap_assessment(inputs)
print(plugin.render_markdown(assessment))
```

## Coverage score

The coverage score is a simple weighted ratio intended as a high-level executive dashboard metric. It is not a certification readiness indicator. Formula:

```text
coverage_score = (covered + 0.5 * partially-covered) / (covered + partially-covered + not-covered)
```

`not-applicable` is excluded from both numerator and denominator, so scope-appropriate exclusions do not penalize the score.

## Framework defaults

- **iso42001**: ships with 38 default Annex A controls (same list as `soa-generator`). Verify against standard per `docs/lead-implementer-review.md`.
- **nist**: no embedded default. Caller must supply `targets` (typically the ~72-subcategory list).
- **eu-ai-act**: no embedded default. Caller supplies `targets` with article identifiers. The `eu-ai-act` skill in `skills/` provides the canonical article list once populated.

## Tests

```bash
python plugins/gap-assessment/tests/test_plugin.py
```

23 tests covering all three target frameworks, all four classification sources with precedence, SoA status mapping, evidence strength semantics, coverage score calculation, unknown-id register warnings, Markdown and CSV rendering, and no-em-dash enforcement.

## Related

- ISO/IEC 42001:2023, Clause 6.1.2 (AI risk assessment), Clause 6.1.3 (AI risk treatment)
- NIST AI RMF 1.0, MAP 4.1, MANAGE 1.2
- EU AI Act, Article 9 (risk management for high-risk AI systems)
- Upstream: `soa-generator` emissions (ISO 42001); skill registry for target enumeration
- Downstream: implementation backlog derived from `not-covered` and `partially-covered` rows; management review package consumes coverage score as a Clause 9.3.2 AIMS-performance signal
