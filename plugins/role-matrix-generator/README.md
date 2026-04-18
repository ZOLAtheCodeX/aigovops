# role-matrix-generator

Generates ISO/IEC 42001:2023-compliant role and responsibility matrices for AI governance decisions.

## Status

Phase 3 minimum-viable implementation. Produces `role-matrix` artifacts per the iso42001 skill Tier 1 T1.6 operationalization and the nist-ai-rmf skill T1.4. Implements Clause 5.3 (roles, responsibilities, authorities) and Annex A Control A.3.2.

## Design stance

This plugin does NOT invent role assignments. Role assignment is an organizational decision that belongs to top management per Clause 5.3. The plugin validates an explicit input RACI, enriches it with authority basis references from the supplied authority register, and marks any unassigned (decision_category, activity) pair as "requires human assignment". An organization gets a draft matrix from which to work, not a hallucinated assignment.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `org_chart` | list of dicts | yes | Each dict has `role_name` (string) and optional `reports_to` (string). |
| `role_assignments` | dict | yes | Keys are either `(decision_category, activity)` tuples or `"<category>::<activity>"` strings. Values are `role_name` strings that must be present in `org_chart`. |
| `authority_register` | dict | yes | Maps `role_name` to `authority_basis` string (organizational policy reference, job description reference, or delegation record). |
| `decision_categories` | list | no | Defaults to the standard 8-category set. |
| `activities` | list | no | Defaults to `propose, review, approve, consulted, informed`. |
| `backup_assignments` | dict | no | Maps `role_name` to `backup_role_name`. Required for continuity; missing backups on approval roles surface a warning. |
| `reviewed_by` | string | no | Named reviewer of the matrix. |

Missing required fields raise `ValueError`. No silent defaults.

## Default decision categories

When `decision_categories` is not supplied, the plugin uses the following eight categories from the iso42001 skill T1.6 operationalization:

1. AI policy approval (enables Clause 5.2)
2. Risk acceptance (enables Clause 6.1.3)
3. SoA approval (enables Clause 6.1.3)
4. AISIA sign-off (enables Clause 6.1.4)
5. Control implementation (enables Clause 8.3)
6. Incident response (enables Clause 10.2)
7. Audit programme approval (enables Clause 9.2.2)
8. External reporting (enables Annex A, Control A.8.3)

## Outputs

A structured matrix dict with:

- `timestamp`: ISO 8601 UTC at generation.
- `agent_signature`: `role-matrix-generator/0.1.0`.
- `citations`: top-level citation anchors (Clause 5.3 and A.3.2).
- `rows`: one dict per `(decision_category, activity)` pair. Each row has `decision_category`, `activity`, `role_name`, `authority_basis`, `backup_role_name`, and `citations`.
- `unassigned_rows`: list of `"<category>::<activity>"` keys where no assignment was provided.
- `warnings`: list of warning strings. Common warnings include unknown roles, missing authority basis, missing backups on approval roles, multiple approvers per category, and missing approvers entirely.

Three rendering functions:

- `generate_role_matrix(inputs)`: the structured dict above.
- `render_markdown(matrix)`: human-readable Markdown document with assignments table, unassigned-rows section, and warnings section.
- `render_csv(matrix)`: CSV for spreadsheet ingestion.

## Example

```python
from plugins.role_matrix_generator import plugin

inputs = {
    "org_chart": [
        {"role_name": "Chief Executive Officer"},
        {"role_name": "Chief Risk Officer"},
        {"role_name": "AI Governance Officer"},
    ],
    "role_assignments": {
        ("AI policy approval", "propose"): "AI Governance Officer",
        ("AI policy approval", "review"): "Chief Risk Officer",
        ("AI policy approval", "approve"): "Chief Executive Officer",
        # ... fill remaining (category, activity) slots
    },
    "authority_register": {
        "Chief Executive Officer": "Board Resolution 2024-01",
        "Chief Risk Officer": "Delegation of Authority Policy",
        "AI Governance Officer": "AI Governance Charter 2025",
    },
    "backup_assignments": {
        "Chief Executive Officer": "Chief Risk Officer",
    },
    "reviewed_by": "AI Governance Committee, 2026-Q2",
}

matrix = plugin.generate_role_matrix(inputs)
print(plugin.render_markdown(matrix))
```

## Validation semantics

The plugin enforces four certification-grade invariants and surfaces each violation as a warning rather than silently hallucinating:

1. Every (decision_category, activity) pair either has an assignment or is marked `REQUIRES HUMAN ASSIGNMENT` and appears in `unassigned_rows`.
2. Every assigned role must appear in `org_chart`. Unknown roles surface a warning.
3. Every approver role must have an entry in `authority_register`. Missing authority basis on an approve-activity row surfaces a warning; authority basis on approval rows is not optional per Clause 5.3.
4. Every role with approval authority must have a backup defined. Continuity is a governance requirement; missing backups surface a warning.

Additional cross-check: every decision category must have exactly one approve-activity role. Categories with zero approvers or multiple approvers surface warnings.

Warnings do not fail the workflow. They are rendered in the output Markdown and surfaced to the review queue so the human owner can correct the input and regenerate.

## Tests

```bash
python plugins/role-matrix-generator/tests/test_plugin.py
```

Runs 19 tests covering happy path, all validation error paths, citation format compliance per STYLE.md, each warning trigger condition, rendering (Markdown and CSV), and output-content enforcement (no em-dashes).

## Related

- ISO/IEC 42001:2023, Clause 5.3 (Roles, responsibilities, and authorities)
- ISO/IEC 42001:2023, Annex A, Control A.3.2 (AI roles and responsibilities)
- NIST AI RMF 1.0, GOVERN 2.1 (Accountability structures)
- Skill reference: [skills/iso42001/SKILL.md](../../skills/iso42001/SKILL.md) section T1.6
- Companion plugin: [plugins/audit-log-generator](../audit-log-generator/) for governance event logging
