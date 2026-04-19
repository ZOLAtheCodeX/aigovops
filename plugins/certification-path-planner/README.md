# certification-path-planner

Consumer plugin. Reads a certification-readiness snapshot (a point-in-time gap verdict) and a target certification date, and produces a milestone-based path plan with per-milestone remediation sequence, risk-weighted prioritization, capacity-aware packing, recertification triggers, and per-remediation action requests ready for the action-executor.

This plugin is the journey/planning layer above `certification-readiness`. The readiness plugin answers "where are we today". The path planner answers "what sequence of actions, by what dates, gets us to the certification milestone, and what triggers the next recertification cycle".

The plugin does not execute any action. It emits an ActionRequest-shaped dict for each remediation; the action-executor consumes those requests. The plugin does not invent gaps or remediations. Every remediation in the plan is sourced from the readiness snapshot.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `current_readiness_ref` | path string or dict | yes | Readiness artifact produced by `certification-readiness`. Accepts a filesystem path to a JSON file, or the dict directly. |
| `target_certification` | enum | yes | One of `iso42001-stage1`, `iso42001-stage2`, `iso42001-surveillance`, `eu-ai-act-internal-control`, `eu-ai-act-notified-body`, `colorado-sb205-safe-harbor`, `nyc-ll144-annual-audit`, `singapore-magf-alignment`, `uk-atrs-publication`. |
| `target_date` | ISO date | yes | The certification milestone date. |
| `organization_capacity` | dict | no | Coarse effort-sizing inputs: `team_size_fte`, `weekly_hours_available`, `budget_envelope`. |
| `risk_register_ref` | path or dict | no | Risk register used to risk-weight remediations by inherent score. |
| `previous_plan_ref` | path or dict | no | Previous plan reference for version diff. |
| `hard_blockers` | list | no | Blocking conditions that cannot be planned around (for example, pending legal opinion). Accepts strings or dicts with `description` and `affected_gap_keys`. |
| `minimum_milestone_interval_weeks` | int | no | Default 4. Width of each milestone window. |
| `enrich_with_crosswalk` | bool | no | Default True. Attach cross-framework citations. |
| `reviewed_by` | string | no | Human reviewer name for the plan. |

## Outputs

The canonical entry point `plan_certification_path(inputs)` returns a dict with:

- `plan_id` (deterministic: `cert-path-<target>-<target_date>-<hash>`).
- `timestamp`, `agent_signature`, `target_certification`, `target_date`, `current_readiness_snapshot_ref`.
- `milestones`: ordered list. Each entry: `milestone_id`, `target_date`, `hours_required`, `remediation_action_requests`, `success_criteria`, `status` (one of `not-started`, `in-progress`, `blocked`, `complete`, `deferred`), `blocked_by`, `contains_snapshot_blocker`, `go_no_go_gate`, `citations`.
- `blockers`: hard blockers surfaced at plan level.
- `recertification_triggers`: future milestones for ongoing compliance (annual ISO surveillance, annual NYC LL144 re-audit, annual Colorado impact assessment refresh, EU harmonised-standards event trigger).
- `capacity_assessment`: per-milestone hours_required vs hours_available.
- `citations`, `warnings`, `summary` (milestone_count, remediation_count, total_hours, target_date_feasibility, recertification_trigger_count).
- `cross_framework_citations` (when `enrich_with_crosswalk=True`).

## Public API

- `plan_certification_path(inputs) -> dict`
- `render_markdown(plan) -> str`
- `render_csv(plan) -> str`

Every rendered Markdown carries the following callout near the top of the document:

> This certification path plan is informational. It does not constitute a commitment to any certification outcome. Certification decisions require a qualified auditor or notified body. Consult a Lead Implementer for formal path approval.

## Example

```python
from plugins.certification_path_planner import plugin

plan = plugin.plan_certification_path({
    "current_readiness_ref": "/tmp/aigovops-outputs/readiness-iso42001-stage2.json",
    "target_certification": "iso42001-stage2",
    "target_date": "2026-12-01",
    "organization_capacity": {
        "team_size_fte": 2,
        "weekly_hours_available": 30,
    },
    "minimum_milestone_interval_weeks": 4,
    "hard_blockers": [
        {
            "id": "HB-001",
            "description": "Pending external legal opinion on high-risk classification.",
            "affected_gap_keys": ["legal-review-pending"],
        },
    ],
    "reviewed_by": "Zola Valashiya",
})
print(plan["plan_id"])
print(plugin.render_markdown(plan))
```

## Rule tables

### Priority scoring

For each remediation in the readiness snapshot, `priority_score` is:

```text
priority_score = (gap_blocker_severity * 10) + risk_inherent_score_max + target_date_urgency_weight
```

- `gap_blocker_severity`: 3 when the readiness snapshot lists the gap as a blocker, 1 otherwise. Multiplied by 10.
- `risk_inherent_score_max`: the maximum inherent-risk score on any register entry that anchors to the gap's artifact type or citation. Zero when no risk register is supplied.
- `target_date_urgency_weight`: 30 (past), 25 (less than 14 days), 15 (less than 60 days), 5 (less than 180 days), 0 otherwise.

Remediations are sorted by priority_score descending. Ties retain snapshot input order.

### Milestone packing

Milestones are built BACKWARDS from `target_date` in windows of width `minimum_milestone_interval_weeks`. Work items are placed in priority order. When `organization_capacity.weekly_hours_available` is provided, the packer closes a milestone whenever adding the next item would push the milestone over the per-interval hour budget. A single item larger than the budget emits a `plan overruns team capacity` warning.

Coarse effort heuristic per gap size: small=8h, medium=40h, large=160h. The plugin does not accept per-gap sizing from the caller.

### Recertification triggers

| Target | Trigger | Cadence | Citation |
|---|---|---|---|
| `iso42001-stage2` | surveillance-audit (first) | +12 months | ISO/IEC 42001:2023, Clause 9.2 |
| `iso42001-stage2` | surveillance-audit (second) | +24 months | ISO/IEC 42001:2023, Clause 9.2 |
| `eu-ai-act-notified-body` | harmonised-standards-review | event-driven | EU AI Act, Article 40 |
| `colorado-sb205-safe-harbor` | impact-assessment-refresh | +12 months | Colorado SB 205, Section 6-1-1703(3) |
| `nyc-ll144-annual-audit` | annual-reaudit | +12 months | NYC LL144 Final Rule, Section 5-301 |

### Action authority routing

| Gap key class | Authority |
|---|---|
| Routine re-runs (`missing-gap-assessment`, `missing-citation`, `missing-audit-log-entry`, `warning-on-critical-control`) | `take-resolving-action` |
| Every other gap | `ask-permission` |

### Status derivation

| Condition | Milestone status |
|---|---|
| Any item on the milestone is in `hard_blockers.affected_gap_keys` | `blocked` |
| Otherwise | `not-started` |

### Warnings

- `target date is too close or past` when `target_date < today + 7 days`.
- `plan overruns team capacity at milestone <X>` when milestone hours exceed the interval budget.
- `Crosswalk plugin unavailable` when the sibling crosswalk plugin cannot be imported; the plan still emits hard-coded cross-framework citations.

## Anti-hallucination invariants

1. The plugin does not invent gaps, remediations, or action requests not present in the readiness snapshot. Pass a snapshot with empty `remediations` and the plan emits zero milestones.
2. Recertification triggers are driven solely by the `target_certification` value, not by bundle content.
3. Priority score inputs are deterministic: blocker flag, risk register anchor match, and target-date urgency. No content-based ranking.

## Prohibited output content

- No em-dashes (U+2014).
- No emojis.
- No hedging.

## Related references

- ISO/IEC 42001:2023, Clause 9.2 (Internal audit): the surveillance-audit cadence for Stage 2 path plans.
- ISO/IEC 42001:2023, Clause 9.3 (Management review): the review gate before each surveillance cycle.
- ISO/IEC 42001:2023, Clause 10.1 (Continual improvement): the planning surface this plugin connects gap assessment to.
- EU AI Act, Article 40 (Harmonised standards): trigger for EU notified-body surveillance.
- EU AI Act, Article 43 (Conformity assessment procedures): the procedural anchor for internal-control and notified-body targets.
- Colorado SB 205, Section 6-1-1703(3): annual impact-assessment refresh statutory basis.
- NYC LL144 Final Rule, Section 5-301: annual bias audit cadence.
