# audit-log-generator

Generates ISO/IEC 42001:2023-compliant audit log entries from AI system descriptions.

## Status

Stub. Function signatures and docstrings only. Implementation in Phase 3.

## Inputs

A single dictionary describing an AI system and a governance event:

| Field | Type | Required | Description |
|---|---|---|---|
| `system_name` | string | yes | Identifier of the AI system. |
| `purpose` | string | yes | Intended use and decision context. |
| `risk_tier` | string | yes | Risk tier classification (for example `high`, `limited`, `minimal`). |
| `data_processed` | list | yes | Categories of data the system processes. |
| `deployment_context` | string | yes | Where and how the system is deployed. |
| `governance_decisions` | list | yes | Decisions made in the governance event being logged. |
| `responsible_parties` | list | yes | Parties accountable for the decisions. |

## Outputs

A structured audit log entry containing:

- `clause_mappings`: every applicable ISO 42001 clause and Annex A control, cited per [STYLE.md](../../STYLE.md).
- `timestamp`: ISO 8601 timestamp of the governance event.
- `evidence_items`: list of evidence references supporting the audit log entry.
- `human_readable_summary`: natural-language summary suitable for inclusion in an audit evidence package.

Output is produced in two formats: a JSON object for programmatic consumption and a Markdown rendering for human review.

## Example invocation

Phase 3.

## Related

- ISO/IEC 42001:2023, Clause 9 (Performance evaluation)
- ISO/IEC 42001:2023, Clause 7.5 (Documented information)
- ISO/IEC 42001:2023, Annex A, Control A.4.6 (Documentation of AI system)
