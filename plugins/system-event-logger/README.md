# system-event-logger

Produces the SYSTEM-OPERATIONAL event log schema, retention policy, and traceability structure required by EU AI Act Article 12 (automatic recording of events), Article 19 (log retention minimum 6 months), ISO/IEC 42001:2023 Annex A Control A.6.2.8 (AI system recording of event logs), and NIST AI RMF MEASURE 2.8 (transparency and accountability).

## Distinct from `audit-log-generator`

- `audit-log-generator` emits GOVERNANCE-EVENT records: management decisions, review minutes, authority exercises. That layer serves ISO/IEC 42001:2023 Clause 9.1 and Annex A Control A.6.2.3 evidence needs.
- `system-event-logger` specifies the SYSTEM-OPERATIONAL event log: inference request/output, drift signals, safety events, override actions, data-access events, biometric-verification records. It produces a SCHEMA artifact (shape, retention policy, tamper-evidence plan), NOT runtime log entries.

## Public API

| Function | Purpose |
|---|---|
| `define_event_schema(inputs)` | Canonical entry point. Returns the schema definition artifact. |
| `render_markdown(schema)` | Human-readable rendering for audit evidence packages. |
| `render_csv(schema)` | Per-field CSV of the normalized schema. |

## Input contract

Top-level keys:

| Key | Required | Description |
|---|---|---|
| `system_description` | yes | Dict with `system_id`, `risk_tier`, `jurisdiction`, `remote_biometric_id` (bool), `sector`, `lifecycle_state`. |
| `event_schema` | yes | Dict keyed by event category (one of `VALID_EVENT_CATEGORIES`). Each value is a dict of field_name to field spec `{type, required, description}`. |
| `retention_policy` | yes | Dict with `policy_name` (enum), `minimum_days`, `maximum_days`, `deletion_procedure_ref`, `legal_basis_citation`. |
| `log_storage` | no | Dict with `storage_system`, `encryption_at_rest`, `access_controls_ref`, `tamper_evidence_method` (one of `hash-chain`, `hmac`, `cryptographic-signing`, `append-only-store`, `external-notary`). |
| `traceability_mappings` | no | Dict mapping event category to a list of Article 12(2) purpose letters (`a`, `b`, `c`). |
| `previous_schema_ref` | no | Opaque reference to a predecessor schema for version diff. |
| `enrich_with_crosswalk` | no | Bool, default True. |
| `reviewed_by` | no | Human reviewer attribution string. |

## Rules

| Rule | Trigger | Outcome |
|---|---|---|
| Art. 12 applicability | EU + high-risk | `art_12_applicability.status = mandatory` |
| Art. 12(3) biometric fields | `remote_biometric_id=True` | Check 6 required fields on the `biometric-verification` category. Missing field emits a blocking warning. |
| Art. 12(2) traceability coverage | any input | Each of (a), (b), (c) must map to at least one event category. Missing purpose emits a warning citing the point. |
| Art. 19(1) six-month floor | EU high-risk | `retention_policy.minimum_days >= 183`. Below emits a blocking warning. |
| Art. 19(1) policy none | `policy_name = "none"` | Blocking warning; incompatible with any high-risk deployment. |
| Art. 19(2) sectoral citation | `policy_name = sectoral-finance` or `sectoral-healthcare` | `legal_basis_citation` must be non-empty. Empty emits a warning. |
| Art. 26(6) tamper evidence | no `tamper_evidence_method` | Warning citing deployer log-keeping duty. |
| Schema diff | `previous_schema_ref` supplied | `schema_diff_summary` block emitted with scaffold for practitioner review. |

## Output contract

Top-level keys: `timestamp`, `agent_signature`, `framework`, `system_description_echo`, `art_12_applicability`, `event_schema_normalized`, `traceability_coverage`, `retention_policy_assessment`, `tamper_evidence_assessment`, `citations`, `warnings`, `summary`, `reviewed_by`. Conditional keys: `biometric_art_12_3_check` (when `remote_biometric_id=True`), `schema_diff_summary` (when `previous_schema_ref` supplied), `cross_framework_citations` and `cross_framework_references` (when `enrich_with_crosswalk=True`).

## Anti-hallucination invariants

1. The plugin specs the schema. It does NOT generate actual log entries.
2. The plugin does NOT verify that log files exist on disk.
3. Missing fields surface as warnings. The plugin does not fabricate defaults for retention, tamper evidence, or traceability mappings.

## Example invocation

```python
from plugins.system_event_logger import plugin as sel

schema = sel.define_event_schema({
    "system_description": {
        "system_id": "SYS-001",
        "risk_tier": "high-risk-annex-iii",
        "jurisdiction": "eu",
        "remote_biometric_id": False,
        "sector": "employment",
        "lifecycle_state": "in-service",
    },
    "event_schema": {
        "inference-request": {
            "request_id": {"type": "string", "required": True, "description": "unique request id"},
            "timestamp": {"type": "datetime", "required": True, "description": "UTC request time"},
        },
        "drift-signal": {
            "metric": {"type": "string", "required": True, "description": "drift metric name"},
            "value": {"type": "float", "required": True, "description": "drift value"},
        },
        "safety-event": {
            "severity": {"type": "string", "required": True, "description": "severity tier"},
        },
    },
    "retention_policy": {
        "policy_name": "eu-art-19-minimum",
        "minimum_days": 200,
        "maximum_days": 730,
        "deletion_procedure_ref": "DEL-PROC-001",
        "legal_basis_citation": "EU AI Act, Article 19, Paragraph 1",
    },
    "log_storage": {
        "storage_system": "encrypted-cloud-bucket",
        "encryption_at_rest": True,
        "access_controls_ref": "IAM-POLICY-001",
        "tamper_evidence_method": "hash-chain",
    },
    "traceability_mappings": {
        "drift-signal": ["a"],
        "safety-event": ["a", "b"],
        "inference-request": ["c"],
    },
})
```

## Related

- `audit-log-generator`: governance-event layer.
- `evidence-bundle-packager`: bundles the schema artifact with other governance artifacts.
- `post-market-monitoring`: references the event log as an evidence stream.

## Determinism

Schema output is deterministic except for the `timestamp` field, which reflects the generation time.
