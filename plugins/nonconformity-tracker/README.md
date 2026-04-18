# nonconformity-tracker

Validates and enriches ISO/IEC 42001:2023 Clause 10.2 nonconformity records and their corrective-action lifecycle. Dual-framework support for NIST AI RMF MANAGE 4.2 via the `framework` flag.

## Status

Phase 3 minimum-viable implementation. Produces `nonconformity-record` artifacts per the iso42001 skill Tier 1 T1.5 and the nist-ai-rmf skill T1.7.

## Design stance

The plugin does NOT invent nonconformity content. Root-cause analysis, corrective action selection, and effectiveness evaluation are judgment-bound activities. The plugin enforces the Clause 10.2 workflow-state machine: each state has invariants (for example, status=closed requires effectiveness_review_date, effectiveness_outcome, and effectiveness_reviewer), and missing invariants surface as per-record warnings. State transitions are inferred from `state_history` and emitted as audit-log-entry hooks citing Clause 7.5.2.

## Workflow states

In order:

1. `detected` (initial)
2. `investigated`
3. `root-cause-identified`
4. `corrective-action-planned`
5. `corrective-action-in-progress`
6. `corrective-action-complete`
7. `effectiveness-reviewed`
8. `closed`

Closure with `effectiveness_outcome: ineffective` surfaces a Clause 10.2 violation warning ("reopen at investigated or root-cause-identified"). A corrective action that did not eliminate the cause is not closable.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `records` | list | yes | Each record has `description`, `source_citation`, `detected_by`, `detection_date`, `status`. Optional fields below. |
| `framework` | string | no | `iso42001` (default), `nist`, or `dual`. |
| `reviewed_by` | string | no | |

### Optional record fields

- `id` (auto-generated `NC-NNNN` if missing)
- `detection_method`
- `investigation_started_at`
- `root_cause`, `root_cause_analysis_date`
- `corrective_actions`: list of `{action, owner, target_date, completed_at}`
- `effectiveness_review_date`, `effectiveness_outcome`, `effectiveness_reviewer`
- `closed_at`, `closed_by`
- `risk_register_updates`: list of risk row refs created or modified as a result
- `improvement_outcome`: NIST MANAGE 4.2 continual-improvement positive direction
- `state_history`: list of `{state, at, by}` transitions for audit-log derivation

Invalid `status` raises `ValueError`. Invalid framework raises `ValueError`. Missing required fields raise `ValueError` with the record id if known. Other gaps surface as warnings.

## Outputs

A structured register dict with `timestamp`, `agent_signature`, `framework`, `citations`, `records`, `state_summary`, `audit_log_events`, `warnings`, `summary`, `reviewed_by`. Each record carries its own `citations` and `warnings`.

Two renderers: `generate_nonconformity_register`, `render_markdown`.

## Audit log derivation

For every entry in a record's `state_history`, the plugin emits a synthetic `audit_log_events` entry of the form:

```python
{
    "event": "nonconformity-transition-to-<state>",
    "timestamp": <at>,
    "actor": <by>,
    "nonconformity_id": <record id>,
    "citation": "ISO/IEC 42001:2023, Clause 7.5.2",
}
```

The aigovclaw runtime routes these to the audit-log workflow so that documented-information control over nonconformity lifecycle is logged per Clause 7.5.2 automatically.

## Tests

```bash
python plugins/nonconformity-tracker/tests/test_plugin.py
```

21 tests covering happy path, invalid states, all per-state invariant warnings, state_history audit-log derivation, framework modes, backward-state-transition warnings, state summary counts, and no-em-dash enforcement.

## Related

- ISO/IEC 42001:2023, Clause 10.2
- ISO/IEC 42001:2023, Clause 7.5.2 (documented information for state transitions)
- NIST AI RMF 1.0, MANAGE 4.2
- Skill references: [skills/iso42001/SKILL.md](../../skills/iso42001/SKILL.md) T1.5; [skills/nist-ai-rmf/SKILL.md](../../skills/nist-ai-rmf/SKILL.md) T1.7
- Upstream: risk-register-builder (creates risks from detected nonconformities); aisia-runner (high-residual sections may trigger nonconformities)
- Downstream: management-review-packager consumes the register as a Clause 9.3.2 input
