# evidence-bundle-packager

Takes a directory of AIGovOps plugin artifacts and produces a deterministic, optionally-signed evidence bundle. The bundle is the unit of delivery for audits, attestations, and regulatory submissions. Auditors consume this bundle, not the running system.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `source_dir` | string (path) | yes | Directory containing plugin outputs. Flat layout (like `examples/demo-scenario/outputs/`) or nested layout (like `~/.hermes/memory/aigovclaw/<type>/*.json`). |
| `scope` | dict | yes | Dict with `organization`, `aims_boundary`, `systems_in_scope`, `reporting_period_start`, `reporting_period_end`, `intended_recipient`. |
| `output_dir` | string (path) | yes | Parent directory under which the bundle directory is created. |
| `bundle_id` | string | no | If absent, generated as `aigovops-bundle-<ISO-timestamp>-<6-char-hash>`. |
| `signing_algorithm` | enum | no | `"hmac-sha256"` (default) or `"none"`. |
| `signing_key_env` | string | no | Environment variable name holding the HMAC key. Default `AIGOVOPS_BUNDLE_SIGNING_KEY`. |
| `include_source_crosswalk` | bool | no | Default `True`. Copies the crosswalk-matrix-builder data files into `bundle/crosswalk/` for provenance. |
| `reviewed_by` | string | no | Human reviewer name for bundle-level attribution. |

`scope.intended_recipient` must be one of: `internal-audit`, `external-auditor`, `regulator`, `stakeholder`, `sponsor`.

## Outputs

The plugin writes a bundle directory under `output_dir/bundle_id/` containing:

- `MANIFEST.json`: canonical artifact list with SHA-256 per file, plus scope and plugin inclusion metadata.
- `citation-summary.md`: aggregated unique citations across all included artifacts, grouped by framework.
- `provenance-chain.json`: plugin-to-plugin consumption edges inferred from well-known upstream relationships.
- `signatures.json`: algorithm, manifest SHA-256, manifest HMAC, per-artifact HMACs (when signing is enabled).
- `README.md`: auditor-facing bundle overview.
- `artifacts/<plugin-name>/<filename>`: every plugin output from `source_dir`, routed to its plugin subdirectory.
- `crosswalk/*.yaml`: the 9 crosswalk data files when `include_source_crosswalk=True`.

## Public API

- `pack_bundle(inputs) -> dict`: produce the bundle on disk. Returns a report dict with `bundle_id`, `bundle_path`, `manifest`, `signatures`, `provenance`, `citation_groups`, `coverage_counts`, `warnings`, `summary`.
- `verify_bundle(bundle_dir, signing_key_env=...) -> dict`: integrity check. Returns a findings dict with `manifest_sha256_matches`, `artifact_hmacs_match`, `missing_artifacts`, `extra_artifacts`, `mutated_artifacts`, `warnings`, `overall`. `overall` is one of `verified`, `drift-detected`, `signature-mismatch`, `signing-disabled`.
- `inspect_bundle(bundle_dir) -> dict`: quick summary for CLI pretty-print.
- `render_markdown(bundle_report) -> str`
- `render_csv(bundle_report) -> str`

## Example

```python
import os
from plugins.evidence_bundle_packager import plugin

os.environ["AIGOVOPS_BUNDLE_SIGNING_KEY"] = "<hex-key>"

report = plugin.pack_bundle({
    "source_dir": "examples/demo-scenario/outputs",
    "scope": {
        "organization": "Acme Health Inc.",
        "aims_boundary": "All AI systems in the Acme Health AIMS",
        "systems_in_scope": ["SYS-001", "SYS-002"],
        "reporting_period_start": "2026-01-01",
        "reporting_period_end": "2026-03-31",
        "intended_recipient": "external-auditor",
    },
    "output_dir": "/tmp/aigovops-bundles",
    "signing_algorithm": "hmac-sha256",
    "include_source_crosswalk": True,
    "reviewed_by": "Lead Implementer",
})

findings = plugin.verify_bundle(report["bundle_path"])
assert findings["overall"] == "verified"
```

## Rule tables

### Artifact classification

Input filenames are matched against a prefix table to determine the originating plugin and artifact type. Matching is case-insensitive substring match. Order matters: more specific prefixes match first.

| Filename substring | Plugin | Artifact type |
|---|---|---|
| `ai-system-inventory` | ai-system-inventory-maintainer | ai-system-inventory |
| `audit-log-entry` | audit-log-generator | audit-log-entry |
| `role-matrix` | role-matrix-generator | role-matrix |
| `risk-register` | risk-register-builder | risk-register |
| `soa` | soa-generator | soa |
| `aisia` | aisia-runner | aisia |
| `nonconformity-register` | nonconformity-tracker | nonconformity-register |
| `management-review-package` | management-review-packager | management-review-package |
| `internal-audit-plan` | internal-audit-planner | internal-audit-plan |
| `metrics-report` | metrics-collector | metrics-report |
| `gap-assessment` | gap-assessment | gap-assessment |
| `data-register` | data-register-builder | data-register |
| `applicability-check` | applicability-checker | applicability-check |
| `high-risk-classification` | high-risk-classifier | high-risk-classification |
| `atrs-record` | uk-atrs-recorder | atrs-record |
| `colorado-compliance-record` | colorado-ai-act-compliance | colorado-compliance-record |
| `nyc-ll144-audit-package` | nyc-ll144-audit-packager | nyc-ll144-audit-package |
| `magf-assessment` | singapore-magf-assessor | magf-assessment |
| `crosswalk` | crosswalk-matrix-builder | crosswalk |

Unclassified files are copied under `artifacts/unknown-plugin/` and flagged in the manifest warnings.

### Provenance edges

The plugin emits an edge only when both endpoints have an artifact in the bundle. Edges are deterministic, not speculative.

| From | To | Via field |
|---|---|---|
| ai-system-inventory-maintainer | risk-register-builder | ai_system_inventory |
| ai-system-inventory-maintainer | soa-generator | ai_system_inventory |
| ai-system-inventory-maintainer | aisia-runner | ai_system_inventory |
| ai-system-inventory-maintainer | audit-log-generator | ai_system_inventory |
| risk-register-builder | soa-generator | risk_register |
| risk-register-builder | management-review-packager | risk_register |
| soa-generator | management-review-packager | soa |
| aisia-runner | management-review-packager | aisia |
| nonconformity-tracker | management-review-packager | nonconformity_register |
| metrics-collector | management-review-packager | metrics_report |
| internal-audit-planner | management-review-packager | internal_audit_plan |

See `plugin.py` for the full list.

### Signing semantics

- `signing_algorithm="hmac-sha256"` (default): reads the HMAC key from `os.environ[signing_key_env]`. Computes HMAC-SHA256 over the manifest SHA-256 and over every artifact's SHA-256. Records `manifest_hmac`, `artifact_hmacs`, `key_id`.
- `signing_algorithm="none"`: records `manifest_sha256` only. No HMAC fields.
- HMAC key missing at pack time: plugin emits a warning, downgrades algorithm to `"none"`, and writes the bundle. This is a content gap, not a structural error.

### Verification semantics

`verify_bundle` returns one of:

- `verified`: manifest SHA-256 matches, every artifact file present, every per-file SHA-256 matches, every HMAC verifies.
- `drift-detected`: at least one artifact listed in the manifest is missing from disk.
- `signature-mismatch`: at least one artifact's content has changed since packing (SHA-256 mismatch), or HMACs do not verify.
- `signing-disabled`: bundle was packed with `signing_algorithm="none"` and integrity survives; HMAC verification is not applicable.

## Determinism

Bundle bytes are identical for identical inputs except for fields that reference absolute time (`generated_at`, `signed_at`). Artifact SHA-256 digests are deterministic; HMAC inputs are deterministic. Every dict in `MANIFEST.json`, `provenance-chain.json`, and `signatures.json` is serialized with sorted keys.

## Prohibited output content

- No em-dashes (U+2014). Tests enforce.
- No emojis.
- No hedging.

## Related references

- ISO/IEC 42001:2023, Clause 7.5.3 (control of documented information): retention, protection, disposition.
- NIST AI RMF 1.0, MANAGE 4.2 (continual improvement measurement feedback captured).
- EU AI Act, Article 11 + Annex IV (technical documentation bundle for high-risk systems).
- EU AI Act, Article 12 (automatic logging) and Article 19 (retention minimum 6 months).
- UK ATRS, Section Impact assessment (documentation and review expectations).
