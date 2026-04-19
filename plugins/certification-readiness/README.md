# certification-readiness

Consumer plugin. Reads an evidence bundle produced by `evidence-bundle-packager` and a target certification, and returns a graduated readiness verdict with section-by-section evidence completeness, crosswalk coverage where applicable, specific gaps or blockers, and curated remediation recommendations.

This is the first CONSUMER plugin in the AIGovOps catalogue. Every other plugin in the catalogue produces an artifact; this one reads the artifact set and answers the decisive question: is the organization ready to pass a given certification or conformity assessment?

The plugin does NOT issue an audit opinion. Certification decisions require a qualified auditor or notified body. This plugin produces the graded verdict, the supporting evidence, and the remediation list.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `bundle_path` | string (path) | yes | Path to an evidence bundle directory (output of `evidence-bundle-packager.pack_bundle`). |
| `target_certification` | enum | yes | One of `iso42001-stage1`, `iso42001-stage2`, `iso42001-surveillance`, `eu-ai-act-internal-control`, `eu-ai-act-notified-body`, `colorado-sb205-safe-harbor`, `nyc-ll144-annual-audit`, `singapore-magf-alignment`, `uk-atrs-publication`. |
| `scope_overrides` | dict | no | Optional `strict_mode` (bool, default False), `jurisdiction_restriction` (string), `minimum_evidence_strength` (one of `strong`, `adequate`, `weak`, `absent`; default `adequate`). |
| `reviewed_by` | string | no | Human reviewer name for the report. |
| `remediation_deadline_days` | int | no | Default 90. Used to compute suggested remediation dates. |

`strict_mode=True` elevates any warning on a critical required artifact from a condition into a blocker.

## Outputs

The canonical entry point `assess_readiness(inputs)` returns a dict with:

- `timestamp`, `agent_signature`, `target_certification`, `bundle_id_ref`.
- `readiness_level`: one of `ready-with-high-confidence`, `ready-with-conditions`, `partially-ready`, `not-ready`.
- `evidence_completeness`: list of `{required_artifact, critical, present, evidence_strength, gap_notes}` rows.
- `crosswalk_coverage`: present for ISO and EU targets. One row per expected citation with coverage status.
- `conditions`: list of `{gap_key, description, artifact_type}` when readiness is `ready-with-conditions`.
- `gaps`: list of non-blocker gaps driving `partially-ready`.
- `blockers`: list of blockers driving `not-ready`.
- `remediations`: list of `{gap_key, gap_description, recommended_action, owner_role, target_plugin, suggested_deadline}`.
- `citations`, `warnings`, `summary`, `reviewed_by`.

## Public API

- `assess_readiness(inputs) -> dict`
- `render_markdown(report) -> str`
- `render_csv(report) -> str`

Every rendered markdown carries the following callout near the top of the document:

> This readiness report is informational. It does not constitute an audit opinion or legal advice. Certification decisions require a qualified auditor or notified body.

## Example

```python
from plugins.certification_readiness import plugin

report = plugin.assess_readiness({
    "bundle_path": "/tmp/aigovops-bundles/aigovops-bundle-2026-04-18T12:00:00Z-abc123",
    "target_certification": "iso42001-stage1",
    "scope_overrides": {"strict_mode": False, "minimum_evidence_strength": "adequate"},
    "reviewed_by": "Zola Valashiya",
})
print(report["readiness_level"])
print(plugin.render_markdown(report))
```

## Rule tables

### Readiness level derivation

| Condition | Readiness |
|---|---|
| MANIFEST.json absent from `bundle_path` | `not-ready` |
| Any critical required artifact absent | `not-ready` |
| Critical artifact present but strength below minimum (strict mode) | `not-ready` |
| Non-critical required artifact absent | `partially-ready` (listed as gap) |
| Target-specific blocker triggered (for example, Colorado safe-harbor conformance missing) | `not-ready` |
| Target-specific gap triggered (for example, EU legal review pending) | `partially-ready` |
| Critical artifact present with warnings (non-strict) | `ready-with-conditions` |
| Every requirement satisfied, no warnings | `ready-with-high-confidence` |

### Per-target required artifacts

| Target | Required artifacts (critical in bold) |
|---|---|
| `iso42001-stage1` | **ai-system-inventory, role-matrix, risk-register, soa, audit-log-entry, aisia, management-review-package, gap-assessment, internal-audit-plan** |
| `iso42001-stage2` | Stage 1 set plus **nonconformity-register, metrics-report**, and a completed internal-audit cycle |
| `iso42001-surveillance` | Stage 2 set with management-review after the Stage 2 certificate issued |
| `eu-ai-act-internal-control` | **aisia (FRIA complete), risk-register, data-register, audit-log-entry, soa, high-risk-classification** |
| `eu-ai-act-notified-body` | Internal-control set plus **supplier-vendor-assessment, metrics-report** |
| `colorado-sb205-safe-harbor` | **high-risk-classification, colorado-compliance-record, aisia**; SoA, risk-register, audit-log supporting |
| `nyc-ll144-annual-audit` | **nyc-ll144-audit-package** with `next_audit_due_by` >= today + 30 days |
| `singapore-magf-alignment` | **magf-assessment** for each applicable system |
| `uk-atrs-publication` | **atrs-record** with Tier 1 fields populated |

### Target-specific checks

- `iso42001-stage2`: internal-audit-plan must carry an `audit_schedule` cycle with `cycle_status="completed"`.
- `eu-ai-act-internal-control` and `eu-ai-act-notified-body`: high-risk-classification output must set `requires_legal_review: false` or expose `legal_review_completed: true`.
- `colorado-sb205-safe-harbor`: either colorado-compliance-record.actor_conformance_frameworks names `iso42001` or a NIST identifier, or high-risk-classification.sb205_assessment.section_6_1_1706_3_applies is `true`.
- `nyc-ll144-annual-audit`: next_audit_due_by less than 30 days out surfaces as `ready-with-conditions`.
- `uk-atrs-publication`: four Tier 1 sections must each be populated (`owner_and_contact`, `tool_description`, `tool_details`, `impact_assessment`).

### Remediation mapping

The plugin never invents remediation language. Every gap_key maps to a curated recommended_action string. Unmapped gaps fall back to `"Requires practitioner judgment; escalate to Lead Implementer."`. Every remediation carries the `target_plugin` that would produce the missing evidence.

## Prohibited output content

- No em-dashes (U+2014).
- No emojis.
- No hedging.

## Related references

- ISO/IEC 42001:2023, Clause 9.2 (Internal audit): readiness against Stage 1 and Stage 2 review.
- ISO/IEC 42001:2023, Clause 9.3 (Management review): the review gate before surveillance audits.
- ISO/IEC 42001:2023, Clause 10.1 (Continual improvement): the loop closing Stage 2 and surveillance.
- EU AI Act, Article 43 (Conformity assessment procedures): the legal anchor for internal-control and notified-body readiness.
- EU AI Act, Annex VI and Annex VII: internal control and notified body procedural references.
- Colorado SB 205, Section 6-1-1706(3): the statutory-presumption trigger the safe-harbor target tests against.
