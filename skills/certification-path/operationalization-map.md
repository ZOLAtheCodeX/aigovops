# Certification Path Operationalization Map

Working document for the `certification-path` skill. Maps each milestone in a path plan to the action-executor action that fires, the target plugin that produces the missing artifact, and the authority class the action-executor applies.

## Milestone lifecycle

Each milestone in a path plan carries:

- A `milestone_id` (for example, `M01`, `M02`).
- A `target_date` derived backwards from the certification target date in windows of `minimum_milestone_interval_weeks`.
- A list of `remediation_action_requests` in ActionRequest shape.
- A `go_no_go_gate` string describing the advancement criterion.
- A `status` (`not-started`, `in-progress`, `blocked`, `complete`, `deferred`).
- Hard-blocker propagation: milestones carrying a remediation whose `gap_key` is in a hard-blocker's `affected_gap_keys` are marked `blocked`.

## Per-gap ActionRequest mapping

The plugin does not invent remediation language. Each ActionRequest is built from the readiness snapshot's remediation row plus the authority class below.

| Gap key | Target plugin | Authority |
|---|---|---|
| `missing-ai-system-inventory` | ai-system-inventory-maintainer | ask-permission |
| `missing-role-matrix` | role-matrix-generator | ask-permission |
| `missing-risk-register` | risk-register-builder | ask-permission |
| `missing-soa` | soa-generator | ask-permission |
| `missing-audit-log-entry` | audit-log-generator | take-resolving-action |
| `missing-aisia` | aisia-runner | ask-permission |
| `missing-nonconformity-register` | nonconformity-tracker | ask-permission |
| `missing-management-review-package` | management-review-packager | ask-permission |
| `missing-internal-audit-plan` | internal-audit-planner | ask-permission |
| `missing-metrics-report` | metrics-collector | ask-permission |
| `missing-gap-assessment` | gap-assessment | take-resolving-action |
| `missing-data-register` | data-register-builder | ask-permission |
| `missing-high-risk-classification` | high-risk-classifier | ask-permission |
| `missing-atrs-record` | uk-atrs-recorder | ask-permission |
| `missing-colorado-compliance-record` | colorado-ai-act-compliance | ask-permission |
| `missing-nyc-ll144-audit-package` | nyc-ll144-audit-packager | ask-permission |
| `missing-magf-assessment` | singapore-magf-assessor | ask-permission |
| `missing-supplier-vendor-assessment` | supplier-vendor-assessor | ask-permission |
| `legal-review-pending` | high-risk-classifier | ask-permission |
| `internal-audit-not-completed` | internal-audit-planner | ask-permission |
| `imminent-reaudit-due` | nyc-ll144-audit-packager | ask-permission |
| `sb205-conformance-missing` | colorado-ai-act-compliance | ask-permission |
| `atrs-tier1-incomplete` | uk-atrs-recorder | ask-permission |
| `missing-citation` | practitioner-review | take-resolving-action |
| `warning-on-critical-control` | practitioner-review | take-resolving-action |

`take-resolving-action` classes are items where a re-run against already-known inputs is low-risk and the operator has pre-approved the pattern: re-running gap-assessment after an upstream artifact changed, regenerating an audit log entry for a recorded AIMS event, re-propagating a citation from an originating artifact.

`ask-permission` is the default. Novel remediations or organizational decisions (who owns the risk register, which controls are excluded from the SoA) always require human approval.

## Per-target recertification trigger mapping

| Target | Trigger type | Scheduled date | Target plugin after trigger |
|---|---|---|---|
| `iso42001-stage2` | surveillance-audit (first) | target_date + 365 days | certification-readiness (`target=iso42001-surveillance`) |
| `iso42001-stage2` | surveillance-audit (second) | target_date + 730 days | certification-readiness (`target=iso42001-surveillance`) |
| `eu-ai-act-notified-body` | harmonised-standards-review | event-driven | eu-conformity-assessor |
| `colorado-sb205-safe-harbor` | impact-assessment-refresh | target_date + 365 days | aisia-runner + colorado-ai-act-compliance |
| `nyc-ll144-annual-audit` | annual-reaudit | target_date + 365 days | nyc-ll144-audit-packager |

Singapore MAGF alignment, UK ATRS publication, ISO Stage 1, and ISO surveillance do not emit recertification triggers from a single path plan run. Stage 1 triggers the Stage 2 plan; surveillance triggers the next surveillance window through its own path plan.

## Hard-blocker propagation

Hard blockers are operator-declared conditions that cannot be planned around. Examples:

- Pending external legal opinion.
- Pending regulator guidance.
- Budget freeze until fiscal-year rollover.
- Dependency on a third-party audit that has not yet scheduled.

Each hard-blocker declares its `description`, optional `id`, and `affected_gap_keys`. Every milestone carrying a remediation whose gap_key appears in the blocker's `affected_gap_keys` is marked `status="blocked"` and carries the blocker description in `blocked_by`.

Hard blockers do NOT remove the milestone from the plan. The plan continues to carry the milestone for tracking; the operator clears the hard blocker, reruns the planner, and the status transitions to `not-started`.

## Capacity assessment

When `organization_capacity.weekly_hours_available` is supplied, the planner calculates:

- `hours_available_per_milestone = weekly_hours_available * minimum_milestone_interval_weeks`.
- `hours_required` per milestone is the sum of coarse effort hours across items (small=8h, medium=40h, large=160h).
- `exceeds_capacity` is true whenever hours_required > hours_available for a milestone.

Capacity overruns generate warnings but do not halt plan generation. The operator has the information and decides whether to defer, split remediations further, or increase capacity.

## Decision table

| Input condition | Output condition |
|---|---|
| Readiness snapshot has zero remediations | Empty `milestones` list; warnings empty; recertification_triggers still emitted per target. |
| `target_date < today` | Warning; `summary.target_date_feasibility="not-feasible"`. |
| `target_date < today + 7 days` | Warning; `summary.target_date_feasibility="tight"`. |
| No organization_capacity supplied | No capacity warnings; every milestone reports `hours_available=null`. |
| Capacity supplied; single large item exceeds budget | Warning `plan overruns team capacity at milestone <id>`. |
| `hard_blockers` includes a gap_key present in a milestone | Milestone status set to `blocked`. |
| `enrich_with_crosswalk=True` (default) and crosswalk plugin unavailable | `cross_framework_citations` present with hard-coded values; warning emitted. |
| `enrich_with_crosswalk=False` | `cross_framework_citations` omitted from output. |
