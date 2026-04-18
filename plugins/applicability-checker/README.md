# applicability-checker

Produces an EU AI Act applicability report for a system at a target date. Answers: "what provisions apply to my AI system today, what's pending, and what secondary instruments matter?"

## Status

Phase 3 implementation. 0.1.0. EU AI Act only; extension to NIST and ISO applicability is possible but not scoped here.

## Why this plugin exists

The EU AI Act's enforcement is staged through 2030. Different provisions apply on different dates. Organizations with AI systems in scope need a clear answer to "what do I need to comply with on date X?" without reading the Regulation and the enforcement timeline themselves every time.

The plugin reads the structured data in `skills/eu-ai-act/enforcement-timeline.yaml` and `skills/eu-ai-act/delegated-acts.yaml`, filters by the system's risk classification (high-risk, GPAI, Annex I product), and produces a grounded report with specific Article citations.

## Design stance

The plugin does NOT interpret legal applicability. The Regulation's applicability rules for a given system are data-driven from:

- The system's risk classification (booleans: `is_high_risk`, `is_gpai`, `is_systemic_risk_gpai`, `is_annex_i_product`).
- The target date.
- The enforcement timeline YAML.

Legal edge cases remain human determinations. The plugin surfaces the questions that need legal answers (Article 6(3) exception, Article 25 provider-deployer role flips, Annex I conformity-assessment procedure selection); it does not answer them.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `system_description` | dict | yes | Must include boolean `is_high_risk`; optional `is_gpai`, `is_systemic_risk_gpai`, `is_annex_i_product`, `placed_on_market_before`, `system_name`. |
| `target_date` | string | yes | ISO 8601 date (`YYYY-MM-DD`) or datetime. |
| `enforcement_timeline` | dict | yes | Loaded YAML from `skills/eu-ai-act/enforcement-timeline.yaml`. |
| `delegated_acts` | dict | no | Loaded YAML from `skills/eu-ai-act/delegated-acts.yaml`. When provided, the plugin filters relevant entries by system classification. |
| `reviewed_by` | string | no | |

## Outputs

Report dict with:

- `timestamp`, `agent_signature`, `framework` (`eu-ai-act`), `target_date`, `system_description_echo`, `reviewed_by`.
- `applicable_events`: enforcement events whose date is on or before `target_date`. Each event includes `date`, `phase`, `description`, `effective_provisions`, `citation`, and a computed `applies_to_system` boolean.
- `pending_events`: events after `target_date`, same fields. `applies_to_system` filters by the system's classification (GPAI events aren't relevant for non-GPAI systems, for example).
- `organizational_actions`: actions due from applicable and relevant events, each with `effective_from` date, `phase`, `action` text, and `citation`.
- `delegated_act_status`: filtered subset of delegated-acts entries (guidelines, harmonised standards, delegated acts, implementing acts) relevant to the system.
- `citations`: top-level citations for the report (`Article 113` always; `Article 6` if high-risk; `Article 51` if GPAI).
- `warnings`: register-level notes (pre-entry-into-force target date, pending-but-not-yet-applicable relevant events).
- `summary`: counts.

Two renderers: `check_applicability`, `render_markdown`.

CSV rendering is not provided because the report is narrative-heavy (actions lists, delegated-act entries) and does not compose well into a single table.

## Filtering logic (relevance determination)

Every event has a `phase`. The plugin filters `applies_to_system` by phase:

| Phase | Applies to system when |
|---|---|
| `entry-into-force` | always |
| `prohibited-practices-applicable` | always (Article 5 prohibitions apply regardless of risk tier) |
| `gpai-and-governance-applicable` | `system.is_gpai` is true |
| `core-obligations-applicable` | `system.is_high_risk` is true |
| `annex-i-extended-transition-ends` | `system.is_annex_i_product` is true |
| `codes-of-practice-expected` | `system.is_gpai` is true |
| `member-state-legacy-transition-sunset` | `system.placed_on_market_before` is before 2025-08-02 |
| (any other) | default applies (inclusive for planning) |

## Example

```python
import yaml
from plugins.applicability_checker import plugin

with open("skills/eu-ai-act/enforcement-timeline.yaml") as f:
    timeline = yaml.safe_load(f)
with open("skills/eu-ai-act/delegated-acts.yaml") as f:
    delegated = yaml.safe_load(f)

report = plugin.check_applicability({
    "system_description": {
        "system_name": "LoanDecisionAssist",
        "is_high_risk": True,
        "is_gpai": False,
        "is_annex_i_product": False,
    },
    "target_date": "2026-04-18",
    "enforcement_timeline": timeline,
    "delegated_acts": delegated,
    "reviewed_by": "AI Governance Committee 2026-Q2",
})

print(plugin.render_markdown(report))
```

Output: a report showing that prohibitions and GPAI-governance events are applicable (date-wise) but only prohibitions are relevant to this system; the core-obligations phase (2026-08-02) is pending and IS relevant; the organizational actions from Article 5 and the entry-into-force phase are due; the high-risk-classification guidelines from the delegated-acts tracker are listed as relevant secondary instruments.

## Tests

```bash
python plugins/applicability-checker/tests/test_plugin.py
```

26 tests covering date filtering for all enforcement events, system-specific relevance filtering (GPAI vs high-risk vs minimal-risk), organizational-action collection, delegated-act filtering, summary counts, input validation, pre-entry-into-force edge case, citations, and rendering.

## Related

- EU AI Act, Article 113 (entry into force and application)
- `skills/eu-ai-act/enforcement-timeline.yaml` (authoritative timeline data)
- `skills/eu-ai-act/delegated-acts.yaml` (tracked secondary instruments)
- Upstream: high-risk-classifier (Article 6 classification) produces the `is_high_risk` and `is_annex_i_product` inputs
- Downstream: AIGovClaw review queue (surfaces organizational_actions as tasks); management-review-packager (compliance-posture section references this report)
