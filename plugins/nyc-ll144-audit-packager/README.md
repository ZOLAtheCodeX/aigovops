# nyc-ll144-audit-packager

Packages the results of an independent bias audit of an Automated Employment Decision Tool (AEDT) into the public-disclosure bundle and candidate-notice checklist required by NYC Local Law 144 of 2021 (LL144) and the implementing Department of Consumer and Worker Protection (DCWP) Final Rule.

## Status

Phase 3 implementation. 0.1.0. Secondary-jurisdiction coverage under the policy in [docs/jurisdiction-scope.md](../../docs/jurisdiction-scope.md).

## What the plugin does and does not do

The plugin does NOT conduct the bias audit. Under DCWP Final Rule Section 5-301 the audit must be performed by an independent auditor against a defined candidate-pool dataset; the auditor computes selection rates and impact ratios. This plugin takes those already-computed results and formats them into:

1. The public-disclosure bundle required by Section 5-304.
2. The candidate-notice checklist required by Section 5-303.
3. The annual re-audit cadence flag (audit_date + 365 days).

Applicability (is the tool an AEDT in scope?) is derived deterministically from three caller-supplied inputs: whether the tool substantially assists or replaces discretionary employment decisions, whether it is used for NYC candidates or NYC employees, and the caller's role. The "substantially assists" determination remains human judgment per Section 5-300; the plugin records the caller's answer and records the applicability rationale.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `aedt_description` | dict | yes | Must include `tool_name`, `substantially_assists_decision` (bool), `used_for_nyc_candidates_or_employees` (bool). Optional: `vendor`, `decision_category`. |
| `employer_role` | string | yes | One of `employer`, `employment-agency`. |
| `audit_data` | dict | yes | `audit_date` (ISO date), `auditor_identity`, `selection_rates` (dict), `distribution_comparison`. |
| `reviewed_by` | string | no | Reviewer for audit evidence chain. |

The `audit_data.selection_rates` shape:

```python
{
  "race_ethnicity": {"<group name>": <selection rate 0..1>, ...},
  "sex": {"Male": 0.37, "Female": 0.34},
  "intersectional": {"<group x sex>": <rate>, ...}
}
```

Race and ethnicity categories must follow the DCWP category list (Hispanic or Latino; White, Black, Native Hawaiian or Pacific Islander, Asian, Native American or Alaska Native, Two or More Races, each Not Hispanic or Latino). The plugin does not validate category spelling; it reports whatever it receives.

## Outputs

Package dict with:

- `timestamp`, `agent_signature`, `framework` (`nyc-ll144`), `reviewed_by`.
- `in_scope` (bool), `applicability_rationale` (list of plain-English bullets).
- `aedt_description_echo`, `employer_role`, `audit_date`, `next_audit_due_by`, `auditor_identity`.
- `selection_rates_analysis`: per-category dict with `selection_rates`, `most_selected_group`, `most_selected_rate`, `impact_ratios`.
- `distribution_comparison`: pass-through of the caller-supplied baseline.
- `public_disclosure_bundle`: ready-to-publish dict per Section 5-304.
- `candidate_notices`: list of required notices per Section 5-303 (empty when out of scope).
- `citations`: list, each matching one of the declared LL144 / DCWP prefixes.
- `warnings`: content-gap warnings.
- `summary`: counts.

Three renderers: `generate_audit_package`, `render_markdown`, `render_csv`.

## Warning rules

The plugin surfaces but does not halt on the following content gaps:

- `audit_data.audit_date` missing: blocks disclosure and next-audit-due calculation.
- `audit_data.auditor_identity` missing: blocks public disclosure (Section 5-304 requires auditor identity).
- `audit_data.selection_rates.intersectional` missing: required by Section 5-301.
- Any selection-rate category with fewer than two groups: impact ratio is undefined.
- `audit_data.distribution_comparison` missing: required historical baseline.

## Validation errors (ValueError)

- Missing required top-level field (`aedt_description`, `employer_role`, `audit_data`).
- `employer_role` not in `(employer, employment-agency)`.
- `audit_data.audit_date` not ISO 8601.
- `aedt_description` not a dict or `audit_data` not a dict.

## Citations

Every emitted citation matches one of:

- `NYC LL144` (for the law itself).
- `NYC LL144 Final Rule, Section <n>` (for the implementing final rule sections 5-300 through 5-304).
- `NYC DCWP AEDT Rules, Subchapter T` (for the implementing regulation chapter).

## Example invocation

```python
from plugins.nyc_ll144_audit_packager import plugin

package = plugin.generate_audit_package({
    "aedt_description": {
        "tool_name": "ResumeScreen-X",
        "vendor": "HireTech Inc.",
        "decision_category": "screen",
        "substantially_assists_decision": True,
        "used_for_nyc_candidates_or_employees": True,
    },
    "employer_role": "employer",
    "audit_data": {
        "audit_date": "2026-04-01",
        "auditor_identity": "Doe and Associates, Independent Auditor",
        "selection_rates": {
            "race_ethnicity": {
                "White (Not Hispanic or Latino)": 0.40,
                "Black or African American (Not Hispanic or Latino)": 0.32,
                "Hispanic or Latino": 0.30,
            },
            "sex": {"Male": 0.37, "Female": 0.34},
            "intersectional": {
                "White Male": 0.42,
                "White Female": 0.38,
                "Black Male": 0.31,
                "Black Female": 0.33,
            },
        },
        "distribution_comparison": {"baseline": "applicant pool 2025 Q4"},
    },
})

print(plugin.render_markdown(package))
```

## Authoritative sources

- NYC Local Law 144 of 2021 (the law): https://legistar.council.nyc.gov/LegislationDetail.aspx?ID=4344524.
- NYC DCWP Final Rule, Automated Employment Decision Tools: https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/.
- NYC DCWP AEDT enforcement and FAQ: https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page.
