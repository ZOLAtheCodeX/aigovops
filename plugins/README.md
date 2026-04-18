# Plugins

This directory contains AIGovOps plugins. A plugin is an executable unit (Python, shell, or other runtime) that produces a concrete governance artifact: an audit log entry, a Statement of Applicability row, a risk register entry, a gap assessment, or similar output.

Plugins differ from skills in execution semantics. A skill is loaded as knowledge by an agent. A plugin is invoked as code, either by an agent or directly by a user.

## Plugin index

| Plugin | Output Artifact | Status |
|---|---|---|
| [audit-log-generator](audit-log-generator/) | ISO 42001-compliant audit log (JSON + Markdown) | 0.1.0 |
| [role-matrix-generator](role-matrix-generator/) | ISO 42001-compliant role and responsibility matrix (JSON + Markdown + CSV) | 0.1.0 |
| [risk-register-builder](risk-register-builder/) | ISO 42001 and NIST AI RMF-compliant AI risk register (JSON + Markdown + CSV) | 0.1.0 |
| [soa-generator](soa-generator/) | ISO 42001-compliant Statement of Applicability (JSON + Markdown + CSV) | 0.1.0 |
| [aisia-runner](aisia-runner/) | ISO 42001 and NIST AI RMF-compliant AI System Impact Assessment (JSON + Markdown) | 0.1.0 |
| [nonconformity-tracker](nonconformity-tracker/) | ISO 42001 Clause 10.2 and NIST MANAGE 4.2 nonconformity and corrective-action records (JSON + Markdown) | 0.1.0 |
| [management-review-packager](management-review-packager/) | ISO 42001 Clause 9.3.2 management review input package (JSON + Markdown) | 0.1.0 |
| [metrics-collector](metrics-collector/) | NIST AI RMF MEASURE 2.x metrics + AI 600-1 overlay with threshold-breach routing (JSON + Markdown + CSV) | 0.1.0 |
| [gap-assessment](gap-assessment/) | Framework gap assessment for ISO 42001, NIST AI RMF, or EU AI Act (JSON + Markdown + CSV) | 0.1.0 |
| [data-register-builder](data-register-builder/) | ISO 42001 A.7 and EU AI Act Article 10 data register (JSON + Markdown + CSV) | 0.1.0 |
| [applicability-checker](applicability-checker/) | EU AI Act applicability by target date + system classification (JSON + Markdown) | 0.1.0 |
| [high-risk-classifier](high-risk-classifier/) | EU AI Act Article 5, 6, Annex I, Annex III risk-tier classification (JSON + Markdown) | 0.1.0 |
| [uk-atrs-recorder](uk-atrs-recorder/) | UK Algorithmic Transparency Recording Standard record, Tier 1 and Tier 2 (JSON + Markdown + CSV) | 0.1.0 |
| [colorado-ai-act-compliance](colorado-ai-act-compliance/) | Colorado SB 205 developer and deployer compliance record (JSON + Markdown + CSV) | 0.1.0 |
| [nyc-ll144-audit-packager](nyc-ll144-audit-packager/) | NYC Local Law 144 bias audit public-disclosure and candidate-notice bundle (JSON + Markdown + CSV) | 0.1.0 |
| [crosswalk-matrix-builder](crosswalk-matrix-builder/) | Cross-framework coverage, gap, or matrix query result (JSON + Markdown + CSV) | 0.1.0 |

## Plugin requirements

Every plugin must:

1. Live in a kebab-case directory under `plugins/`.
2. Contain a README.md describing inputs, outputs, and example invocation.
3. Produce deterministic output for deterministic input. Document any non-determinism in the README.
4. Use the citation formats defined in [STYLE.md](../STYLE.md) for any framework references in output.
5. Raise a clear error on missing or malformed input rather than producing degraded output.
6. Be registered in the plugin index above and in the repository [README.md](../README.md).

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full plugin submission checklist.

## Plugin-author contract

Every plugin in this catalogue follows the same structural contract. A new plugin author (human or tactical-lane agent per [AGENTS.md](../AGENTS.md)) should copy the pattern of any existing plugin and replicate the following invariants.

### File layout

```text
plugins/<plugin-name>/
├── plugin.py          Implementation.
├── README.md          Inputs, outputs, example, rule tables, related refs.
└── tests/
    └── test_plugin.py Pytest-compatible, also runnable standalone.
```

### Module-level constants

- `AGENT_SIGNATURE`: string of the form `"<plugin-name>/<semver>"`. Embedded in every emitted artifact so downstream consumers know which plugin version produced a record. Bump the version when output format changes materially, not for internal refactors.
- `REQUIRED_INPUT_FIELDS`: tuple of strings. Enumerated required keys in the top-level input dict.
- Enumerated value tuples: `VALID_<THING>` tuples for enum-style inputs (for example `VALID_FRAMEWORKS = ("iso42001", "nist", "dual")`). Validate against these and raise `ValueError` on mismatch.

### Public API

- `generate_<artifact>(inputs: dict) -> dict`: the canonical entry point. Takes a dict, returns a structured dict. Must validate and enrich, not hallucinate.
- `render_markdown(artifact: dict) -> str`: human-readable rendering for audit evidence packages. Required.
- `render_csv(artifact: dict) -> str`: spreadsheet-ingestible rendering. Required when the artifact has a natural tabular form; optional for prose-heavy artifacts (AISIAs and management review packages skip CSV).

### Validation stance

Structural problems raise `ValueError`. These are programmer errors or caller mistakes:

- Missing required input fields.
- Wrong types (`risks` is a string instead of a list, for example).
- Invalid enum values (unknown framework, unknown status, unknown treatment option).

Content gaps surface as per-row or per-record `warnings` lists inside the output dict. These are organizational inputs the human needs to correct:

- Missing likelihood or impact scoring.
- Missing owner assignment.
- Empty justifications.
- Referenced IDs not found in the relevant inventory.

This split is load-bearing. A plugin that raises `ValueError` on content gaps would halt on the first missing field; a plugin that silently fills in defaults would produce audit evidence the auditor rejects. Warnings let the human see all gaps at once and correct them in bulk.

### Anti-hallucination invariants

1. The plugin does not invent risks, impacts, role assignments, control applicability, or any other organizational decision. Every substantive content field either comes from input, or is computed deterministically from input, or is flagged as requiring human input.
2. When a rule-based inference is possible (for example, "if the risk register references this control, it is included in the SoA"), the inference is explicit, deterministic, and documented in the README's rule table.
3. When no evidence supports a determination, the plugin emits a placeholder (for example, `REQUIRES HUMAN ASSIGNMENT`, `REQUIRES REVIEWER DECISION`) and surfaces a warning. It never silently guesses.

### Output contract

Every emitted artifact dict includes:

- `timestamp`: ISO 8601 UTC with seconds precision, suffix `Z`.
- `agent_signature`: the constant above.
- `citations`: top-level list of canonical framework citations applicable to the artifact as a whole.
- Row or section level `citations`: each row carries the specific citations applicable to that row.
- `warnings`: register-level list of warnings about the input or the assembly.
- `summary`: aggregate counts suitable for dashboard rendering.

### Adapter-friendly design

Plugin outputs are structured dicts with stable field names. The design target is a future adapter layer that pushes artifacts into external systems (GRC platforms, structured workspace tools, ticketing systems) without plugins needing to know about the target. Keep field names stable across versions; if a field's meaning changes, rename rather than repurpose. The `agent_signature` makes version-aware adapter mapping possible.

### Citation format

Every citation string matches [STYLE.md](../STYLE.md) exactly:

- ISO clauses: `ISO/IEC 42001:2023, Clause X.X.X`.
- ISO Annex A: `ISO/IEC 42001:2023, Annex A, Control A.X.Y`.
- NIST: `<FUNCTION> <Subcategory>` (for example `GOVERN 1.1`, `MEASURE 2.7`).
- EU AI Act: `EU AI Act, Article XX, Paragraph X`.

Tests explicitly assert the prefix format so drift is caught at review time.

### Dual-framework support

When a plugin serves both ISO 42001 and NIST AI RMF (four of the seven existing plugins do), accept a `framework` input: one of `iso42001` (default), `nist`, `dual`. Rows carry either one citation family, the other, or both. Never silently emit ISO citations when the caller asked for NIST.

### Prohibited output content (enforced by tests)

- No em-dashes (U+2014). A dedicated test asserts this.
- No emojis. Plain text only.
- No hedging language. Definite determinations; explicit escalation when judgment is required.

### Tests

A `test_plugin.py` file runs under pytest or as a standalone script. No external dependencies beyond the Python standard library. Minimum coverage:

1. Happy-path test verifying all required output fields are present.
2. One test per validation error path (`ValueError` raised on each structural problem).
3. One test per warning trigger condition.
4. Citation format compliance test (assert the STYLE.md prefix on every emitted citation).
5. Rendering tests (Markdown has required sections; CSV has header and correct row count).
6. No-em-dash assertion on the full rendered output.

All tests must pass before the plugin is registered in the plugin index.

### Reference implementations

- Simple rule-table mapping: [audit-log-generator](audit-log-generator/).
- Warning-heavy validation (no invention): [role-matrix-generator](role-matrix-generator/).
- Dual-framework rendering: [risk-register-builder](risk-register-builder/) and [aisia-runner](aisia-runner/).
- State-machine validation: [nonconformity-tracker](nonconformity-tracker/).
- Pure aggregator: [management-review-packager](management-review-packager/).
- Precedence-rule-driven inference: [soa-generator](soa-generator/).
