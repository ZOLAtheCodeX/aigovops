# incident-reporting

Regulatory-deadline-aware external incident reporting. Distinct from the [`nonconformity-tracker`](../nonconformity-tracker/) plugin, which records internal ISO/IEC 42001:2023 Clause 10.2 corrective-action lifecycle. This plugin prepares external authority notifications governed by statutory deadlines.

## Status

0.1.0. Ships EU AI Act Article 73, Colorado SB 205 Sections 6-1-1702(7) and 6-1-1703(7), and NYC LL144 candidate-complaint coverage. Other jurisdictions declared in `applicable_jurisdictions` emit a manual-review warning rather than silently dropping.

## Design stance

The plugin does NOT write the practitioner's narrative and does NOT transmit reports. It determines per-jurisdiction applicability, computes filing deadlines from `detected_at` plus statutory windows, assembles report-draft templates populated with the echoed incident description, and emits required-content checklists for every draft. Practitioner completes the narrative and files with the competent authority.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `incident_description` | dict | yes | `summary`, `affected_systems`, `date_of_occurrence`, `date_discovered`, `discovery_channel`, `potential_harms`, `impacted_persons_count`, `geographic_scope`. |
| `applicable_jurisdictions` | list | yes | Non-empty subset of VALID_JURISDICTIONS. |
| `detected_at` | ISO 8601 | yes | Clock start for deadline computation. |
| `severity` | enum | no | Defaults to auto-derivation from `potential_harms`. |
| `actor_role` | enum | conditional | Required when EU AI Act jurisdiction applies (`provider` or `deployer`). |
| `consequential_domains` | list | conditional | Needed for Colorado SB 205 applicability. |
| `already_reported_to` | list | no | Follow-up reports. |
| `containment_actions_taken` | list | no | |
| `correction_plan` | string | no | |
| `organization_contact` | string | no | |
| `enrich_with_crosswalk` | bool | no | Default True. |
| `reviewed_by` | string | no | |

## Deadline rules

| Jurisdiction | Severity | Days | Rule citation | Recipient |
|---|---|---|---|---|
| EU | fatal | 2 | EU AI Act, Article 73, Paragraph 6 | EU AI Office via national competent authority |
| EU | widespread-infringement | 2 | EU AI Act, Article 73, Paragraph 6 | EU AI Office via national competent authority |
| EU | serious-physical-harm | 10 | EU AI Act, Article 73, Paragraph 7 | EU AI Office via national competent authority |
| EU | critical-infrastructure-disruption | 10 | EU AI Act, Article 73, Paragraph 7 | EU AI Office via national competent authority |
| EU | limited-harm / no-harm / other | 15 | EU AI Act, Article 73, Paragraph 2 | EU AI Office via national competent authority |
| usa-co | any | 90 | Colorado SB 205, Section 6-1-1702(7); Section 6-1-1703(7) | Colorado Attorney General |
| usa-nyc | candidate complaint | 30 | NYC DCWP AEDT Rules, Subchapter T, Section 5-303 | NYC DCWP |

## Outputs

Structured dict with `timestamp`, `agent_signature`, `framework`, `incident_description_echo`, `severity`, `actor_role`, `applicable_jurisdictions`, `detected_at`, `deadline_matrix`, `report_drafts`, `citations`, `cross_framework_citations`, `warnings`, `summary`, `reviewed_by`.

`deadline_matrix` entries carry `{jurisdiction, rule_citation, deadline_iso, days_remaining, status, filing_recipient}`. Status values: `future`, `imminent-within-48h`, `overdue`. Recomputed each invocation against current wall-clock UTC time; not persisted.

`report_drafts` entries carry `{jurisdiction, template_name, draft_markdown, required_recipient, required_contents_checklist, warnings}`.

Three renderers: `generate_incident_report`, `render_markdown`, `render_csv`.

## Example

```python
import plugins.incident_reporting.plugin as ir

result = ir.generate_incident_report({
    "incident_description": {
        "summary": "Triage model erroneously de-prioritized a critical case.",
        "affected_systems": ["sys-triage-01"],
        "date_of_occurrence": "2026-04-10",
        "date_discovered": "2026-04-11",
        "discovery_channel": "clinician incident report",
        "potential_harms": ["fatality"],
        "impacted_persons_count": 1,
        "geographic_scope": "EU (Germany, Spain)",
    },
    "applicable_jurisdictions": ["eu", "usa-co"],
    "detected_at": "2026-04-11T14:00:00Z",
    "actor_role": "provider",
    "consequential_domains": ["health-care"],
    "organization_contact": "governance@example.com",
})
print(ir.render_markdown(result))
```

## Tests

```bash
python3 plugins/incident-reporting/tests/test_plugin.py
```

22 tests covering happy-path per jurisdiction, deadline-severity matrix, validation errors, severity auto-derivation, applicability warnings, status recomputation (future, imminent-within-48h, overdue), required-contents checklists, citation-format compliance, crosswalk enrichment, rendering, and anti-pattern suppression (no em-dashes, no hedging).

## Related

- Internal counterpart: [`nonconformity-tracker`](../nonconformity-tracker/) for Clause 10.2 root-cause analysis and corrective-action state machine.
- Upstream: [`audit-log-generator`](../audit-log-generator/) records a documented-information event for each external filing per Clause 7.5.2.
- Frameworks: ISO/IEC 42001:2023 Clause 10.2, EU AI Act Articles 20 and 73, Colorado SB 205 Sections 6-1-1702(7) and 6-1-1703(7), NYC LL144 and DCWP AEDT Rules Section 5-303, NIST AI RMF MANAGE 4.3 (informational).
- Skill: [skills/incident-reporting/SKILL.md](../../skills/incident-reporting/SKILL.md).
