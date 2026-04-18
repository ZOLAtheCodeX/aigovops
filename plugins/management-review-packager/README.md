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
| `include_crosswalk_coverage` | bool | no | Default `True`. Attaches the `cross_framework_coverage` section sourced from the crosswalk-matrix-builder plugin. Set `False` for ISO-only packages. |
| `crosswalk_target_frameworks` | list | no | Default `["nist-ai-rmf", "eu-ai-act", "uk-atrs"]`. Framework ids to compute ISO Annex A coverage against. |
| `jurisdictions` | list | no | Jurisdiction ids (e.g. `"eu"`, `"uk"`, `"us-federal"`, `"us-colorado"`, `"us-california"`, `"us-nyc"`, `"singapore"`) used to produce the jurisdictional-posture subsection. |

Missing `review_window` or empty `attendees` raise `ValueError`. Missing categories surface per-category warnings and mark the section as not populated.

## Outputs

Package dict with `timestamp`, `agent_signature`, `citations`, `review_window`, `attendees`, `meeting_metadata`, `sections`, `distribution_hook`, `summary`, `warnings`, `reviewed_by`, and (when enrichment ran) `cross_framework_coverage`.

- `sections`: 9 section dicts in fixed order, each with `key`, `title`, `citation`, `source_ref`, `trend_direction`, `breach_flags`, `populated`.
- `distribution_hook`: audit-log-entry hook for the package distribution event, citing Clause 7.5.3. The aigovclaw runtime routes this to the audit-log workflow automatically.
- `summary`: counts of populated vs unpopulated categories plus attendee count.
- `cross_framework_coverage`: ISO Annex A coverage against each target framework, with covered / partial / gap counts, coverage percentage, top ISO gaps per target, an overall alignment label (`strong`, `moderate`, `limited`), and (when `jurisdictions` is set) a `jurisdictional_posture` list naming applicable frameworks and their coverage status per jurisdiction.

### Cross-framework coverage shape

```python
"cross_framework_coverage": {
    "target_frameworks": ["nist-ai-rmf", "eu-ai-act", "uk-atrs"],
    "per_framework_summary": [
        {
            "target_framework": "nist-ai-rmf",
            "iso_annex_a_controls_covered": 28,
            "iso_annex_a_controls_partial": 10,
            "iso_annex_a_controls_gaps": 0,
            "coverage_percentage": 73.7,
            "top_gaps": [],
        },
        # ...
    ],
    "overall_multi_framework_alignment": "moderate",
    "average_coverage_percentage": 71.3,
    "jurisdictional_posture": [
        {
            "jurisdiction": "eu",
            "applicable_frameworks": ["eu-ai-act", "iso42001"],
            "framework_coverage": [
                {"framework": "eu-ai-act", "coverage_percentage": 50.9, "status": "moderate"},
                {"framework": "iso42001", "coverage_percentage": 0.0, "status": "limited"},
            ],
        },
        # ...
    ],
}
```

Counting rules: a control is counted as `covered` if any mapping to the target is `exact-match` or `satisfies`; as `partial` if any mapping is `partial-match`, `partial-satisfaction`, `complementary`, or `statutory-presumption`; as a `gap` only when every mapping to the target is `no-mapping`. Coverage percentage is `covered / (covered + partial + gap) * 100`.

Graceful failure: if the crosswalk plugin cannot load or its data files fail invariants, `cross_framework_coverage` is omitted and a single warning is appended naming the failure type. The rest of the package renders unchanged.

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
    "crosswalk_target_frameworks": ["nist-ai-rmf", "eu-ai-act", "uk-atrs"],
    "jurisdictions": ["eu", "uk", "us-federal"],
}

package = plugin.generate_review_package(inputs)
print(plugin.render_markdown(package))
```

### Clause 9.3.2 package with multi-framework posture

When `include_crosswalk_coverage` is on (the default), the rendered Markdown adds a "Cross-framework coverage summary" section with one row per target framework and a top-ISO-gap list for each, followed by a "Jurisdictional posture" subsection showing which frameworks apply in each jurisdiction the organization operates in and the coverage status there. Top management sees at Clause 9.3.2 review whether the AIMS is multi-jurisdiction-ready: a UK-only program with a strong UK ATRS posture but a limited EU AI Act posture reads as `limited` overall, flagging a conformity gap before the review discusses objectives for the next cycle. If `uk-atrs` is in the target list, the Markdown also emits a dedicated "UK ATRS posture" subsection with the same counts surfaced directly under the coverage table.

## Tests

```bash
python plugins/management-review-packager/tests/test_plugin.py
```

22 tests covering happy path, all 9 required categories, populated and unpopulated states, source_ref / trend_direction / breach_flags, distribution_hook emission, validation errors (missing window, empty attendees), Markdown rendering, no-em-dash enforcement, and cross-framework coverage (default-on, explicit opt-out, coverage-count consistency, top-gap identification, and graceful failure when the crosswalk plugin is unavailable).

## Related

- ISO/IEC 42001:2023, Clause 9.3.2 (inputs)
- ISO/IEC 42001:2023, Clause 9.3.1 (review itself, human-driven; out of scope)
- ISO/IEC 42001:2023, Clause 9.3.3 (outputs; captured separately)
- ISO/IEC 42001:2023, Clause 7.5.3 (distribution evidence)
- Upstream: audit-log-generator, risk-register-builder, nonconformity-tracker outputs feed this package
- Skill reference: [skills/iso42001/SKILL.md](../../skills/iso42001/SKILL.md) T1.4
