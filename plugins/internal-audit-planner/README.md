# internal-audit-planner

Operationalizes ISO/IEC 42001:2023 Clause 9.2 (Internal audit). Plans the internal audit programme, schedule, criteria mapping, and impartiality assessment for an AI Management System (AIMS).

## Status

Phase 3 minimum-viable implementation. Completes the ISO Clause 9-10 pillar alongside [management-review-packager](../management-review-packager/) (Clause 9.3.2) and [nonconformity-tracker](../nonconformity-tracker/) (Clause 10.2).

## Design stance

The plugin plans; it does not conduct. It never invents audit findings. It emits a programme, schedule, criteria mapping, and impartiality assessment from structured organizational input. Content gaps (unassigned auditors, scope gaps, impartiality conflicts, prior audits without recorded follow-up) surface as warnings. Structural problems raise `ValueError`.

## What Clause 9.2 requires

- **9.2.1 General.** Conduct internal audits at planned intervals to determine whether the AIMS conforms to (a) the organization's own requirements, (b) the requirements of ISO/IEC 42001:2023, and (c) is effectively implemented and maintained.
- **9.2.2(a).** Plan, establish, implement and maintain an audit programme including frequency, methods, responsibilities, planning, reporting requirements, taking into consideration importance of processes and results of previous audits.
- **9.2.2(b).** Define audit criteria and scope for each audit.
- **9.2.2(c).** Select auditors and conduct audits to ensure objectivity and impartiality.
- **9.2.2(d).** Ensure that results of audits are reported to relevant management.
- **9.2.2(e).** Retain documented information as evidence of the audit programme and audit results.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `scope` | dict | yes | `aims_boundaries` (str), `systems_in_scope` (list), `clauses_in_scope` (list of clause numbers like `"6.1"`), `annex_a_in_scope` (list of category ids like `"A.6"`). |
| `audit_frequency_months` | int | yes | Integer in 1 to 36. Typical value 12 for annual. |
| `audit_criteria` | list | yes | Non-empty list of criteria documents. Must include `"ISO/IEC 42001:2023"`. |
| `audit_type` | str | no | One of `first-party` (default), `second-party`, `third-party`. |
| `auditor_pool` | list | no | List of dicts `{name, role, independence_level, qualifications, own_areas}`. |
| `prior_audit_findings` | list | no | List of dicts with `id`, `area`, `severity`, `corrective_action_status`, `follow_up_cycle_id`. Drives risk-weighted prioritization per 9.2.2(a). |
| `management_system_risk_register_ref` | str | no | Echoed into `criteria_mapping`. |
| `reporting_recipients` | list | no | Default `["AI Governance Officer", "Top Management"]`. |
| `reviewed_by` | str | no | |
| `enrich_with_crosswalk` | bool | no | Default `True`. Adds `cross_framework_audit_references` (NIST MEASURE 4.1 to 4.3 and EU AI Act Article 17(1)(d) and 17(1)(k)). |

### Enums

- `VALID_AUDIT_TYPES = ("first-party", "second-party", "third-party")`
- `VALID_METHODS = ("document-review", "interview", "observation", "technical-test", "sampling", "re-performance")`
- `VALID_IMPARTIALITY_TIERS = ("independent", "departmental-separation", "management-delegated", "insufficient")`
- `DEFAULT_ANNEX_A_CATEGORIES = ("A.2", "A.3", "A.4", "A.5", "A.6", "A.7", "A.8", "A.9", "A.10")`

## Outputs

A structured plan dict with:

- `timestamp`, `agent_signature`, `framework` (fixed: `"iso42001"`), `reviewed_by`.
- `scope_echo`: the scope input echoed back verbatim.
- `audit_schedule`: one entry per planned cycle with `cycle_id`, `planned_start_date`, `planned_end_date`, `scope_this_cycle`, `assigned_auditors`, `audit_type`, `audit_criteria`, `methods_selected`, `reporting_recipients`, `citations`.
- `scope_coverage_summary`: counts and uncovered-area list.
- `impartiality_assessment`: per-tier counts and per-cycle independence posture per 9.2.2(c).
- `criteria_mapping`: per-scope-area mapping to authoritative citation, audit criteria documents, and risk register reference (9.2.2(b)).
- `citations`: top-level canonical citations (Clause 9.2.1, 9.2.2(a) through (e), 7.5.3, 9.3).
- `warnings`: register-level warnings.
- `summary`: counts for dashboard rendering.
- `cross_framework_audit_references` (only when `enrich_with_crosswalk: True`): NIST MEASURE 4.1 to 4.3 and EU AI Act Article 17(1)(d) and 17(1)(k).

Three renderers: `generate_audit_plan`, `render_markdown`, `render_csv`.

## Warning surface

- Empty `auditor_pool`: every cycle is flagged `REQUIRES AUDITOR ASSIGNMENT`.
- Auditor assigned to an area they declare as `own_areas`, or any auditor with `independence_level: insufficient`: impartiality-conflict warning naming the auditor and area.
- Scope gaps: any declared clause or Annex A category not placed in any cycle.
- Prior audit findings with `corrective_action_status` open or absent and no `follow_up_cycle_id`: not-followed-up warning.
- `management_system_risk_register_ref` not provided: risk-weighting input gap warning.

Structural problems (missing required fields, invalid enums, frequency out of range, `audit_criteria` that omits ISO/IEC 42001:2023) raise `ValueError`.

## Rule table

| Input condition | Output behaviour |
|---|---|
| `audit_frequency_months` >= 12 | Programme has 1 cycle covering all areas. |
| `audit_frequency_months` < 12 | Programme has `12 // freq_months` cycles; declared areas are partitioned across cycles after risk-weighted ordering. |
| Prior finding severity `critical` on area X | Area X moves to the front of the ordered scope list. |
| Cycle scope contains any `A.7` or `A.8` area | `technical-test` added to `methods_selected`. |
| `enrich_with_crosswalk: True` (default) | Output adds `cross_framework_audit_references`. |

## Tests

```bash
python plugins/internal-audit-planner/tests/test_plugin.py
```

20 tests covering happy path, quarterly cadence, validation errors (missing scope, missing frequency, missing criteria, frequency out of range, invalid audit_type, criteria omitting ISO 42001), warning surfaces (empty auditor pool, impartiality conflict, empty scope), prior-findings risk prioritization, risk register echo, crosswalk enrichment toggle, citation format compliance, Markdown section completeness, CSV row count, and no-em-dash, no-emoji, no-hedging enforcement on rendered output.

## Related

- ISO/IEC 42001:2023, Clauses 9.2.1, 9.2.2(a) through (e), 7.5.3, 9.3.
- NIST AI RMF 1.0, MEASURE 4.1 through 4.3.
- EU AI Act (Regulation (EU) 2024/1689), Article 17, Paragraph 1, Points (d) and (k).
- Skill references: [skills/internal-audit/SKILL.md](../../skills/internal-audit/SKILL.md); [skills/iso42001/SKILL.md](../../skills/iso42001/SKILL.md).
- Upstream inputs: nonconformity-tracker (open findings), risk-register-builder (risk-weighting anchor), metrics-collector (prior-cycle observation data).
- Downstream consumer: management-review-packager (Clause 9.3.2 `audit_results` category).
