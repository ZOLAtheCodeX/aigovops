# management-review-packager

Composes the ISO/IEC 42001:2023 Clause 9.3.2 management review input package from organizational sources of record.

## Status

Phase 3 minimum-viable implementation. Produces `review-minutes` preamble artifacts per the iso42001 skill Tier 1 T1.4.

## Design stance

The plugin is an aggregator, not a synthesizer. Every Clause 9.3.2 input category is populated from a supplied source-of-record reference (a KPI report ID, a risk register reference, a nonconformity log reference, and so on), never from narrative summaries the plugin invented. Empty categories surface warnings so the reviewer knows exactly which inputs need to be produced before the package is distributed to attendees.

The meeting itself (Clause 9.3.1) is human; the review outputs (Clause 9.3.3) are captured separately. This plugin assembles only the pre-read.

## Input categories

The plugin emits sections in this fixed order (matching Clause 9.3.2 structure):

1. Status of actions from previous management reviews: `previous_review_actions` (cites 9.3.2(a))
2. Changes in external and internal issues: `external_internal_issues_changes` (cites Clause 4.1)
3. Information on AIMS performance: `aims_performance` (cites Clause 9.1)
4. Internal audit results: `audit_results` (cites Clause 9.2)
5. Nonconformity and corrective-action trends: `nonconformity_trends` (cites Clause 10.2)
6. Fulfillment of AI objectives: `objective_fulfillment` (cites Clause 6.2)
7. Feedback from interested parties: `stakeholder_feedback` (cites Clause 4.2)
8. AI risks and opportunities: `ai_risks_and_opportunities` (cites Clause 6.1)
9. Opportunities for continual improvement: `continual_improvement_opportunities` (cites Clause 10.1)

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `review_window` | dict | yes | `{start, end}` as ISO dates. |
| `attendees` | list | yes | Non-empty list of role names. |
| Each category key above | string, list, or dict | no but recommended | String = source_ref; list = items; dict = `{source_ref, trend_direction, breach_flags}`. |
| `meeting_metadata` | dict | no | `{scheduled_date, location, ...}`. |
| `reviewed_by` | string | no | Prepared-for-review-by attribution. |

Missing `review_window` or empty `attendees` raise `ValueError`. Missing categories surface per-category warnings and mark the section as not populated.

## Outputs

Package dict with `timestamp`, `agent_signature`, `citations`, `review_window`, `attendees`, `meeting_metadata`, `sections`, `distribution_hook`, `summary`, `warnings`, `reviewed_by`.

- `sections`: 9 section dicts in fixed order, each with `key`, `title`, `citation`, `source_ref`, `trend_direction`, `breach_flags`, `populated`.
- `distribution_hook`: audit-log-entry hook for the package distribution event, citing Clause 7.5.3. The aigovclaw runtime routes this to the audit-log workflow automatically.
- `summary`: counts of populated vs unpopulated categories plus attendee count.

## Renderers

- `generate_review_package(inputs)`: the structured dict above.
- `render_markdown(package)`: human-readable document suitable for distribution to attendees.

CSV is not provided because the package is prose-heavy and not tabular; Markdown is the canonical submission format.

## Example

```python
from plugins.management_review_packager import plugin

inputs = {
    "review_window": {"start": "2026-01-01", "end": "2026-03-31"},
    "attendees": ["CRO", "CISO", "DPO", "AI Governance Officer"],
    "previous_review_actions": "MR-2025-Q4-action-log",
    "aims_performance": {
        "source_ref": "KPI-report-2026-Q1",
        "trend_direction": "stable",
        "breach_flags": ["latency-p95-over-target"],
    },
    "audit_results": "IA-2026-Q1-report",
    "nonconformity_trends": {"source_ref": "NC-log-2026-Q1", "trend_direction": "improving"},
    "objective_fulfillment": "OBJ-status-2026-Q1",
    "stakeholder_feedback": ["Customer advocate concern A", "Regulator inquiry B"],
    "ai_risks_and_opportunities": "RR-register-2026-03-31",
    "continual_improvement_opportunities": "CI-opportunities-2026-Q1",
    "reviewed_by": "AI Governance Committee",
}

package = plugin.generate_review_package(inputs)
print(plugin.render_markdown(package))
```

## Tests

```bash
python plugins/management-review-packager/tests/test_plugin.py
```

17 tests covering happy path, all 9 required categories, populated and unpopulated states, source_ref / trend_direction / breach_flags, distribution_hook emission, validation errors (missing window, empty attendees), Markdown rendering, and no-em-dash enforcement.

## Related

- ISO/IEC 42001:2023, Clause 9.3.2 (inputs)
- ISO/IEC 42001:2023, Clause 9.3.1 (review itself, human-driven; out of scope)
- ISO/IEC 42001:2023, Clause 9.3.3 (outputs; captured separately)
- ISO/IEC 42001:2023, Clause 7.5.3 (distribution evidence)
- Upstream: audit-log-generator, risk-register-builder, nonconformity-tracker outputs feed this package
- Skill reference: [skills/iso42001/SKILL.md](../../skills/iso42001/SKILL.md) T1.4
