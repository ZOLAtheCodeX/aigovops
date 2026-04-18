# crosswalk-matrix-builder

Machine-readable cross-framework coverage, gap, and matrix queries over the AIGovOps crosswalk dataset. One plugin, one canonical data store, three query shapes (coverage, gaps, matrix, plus single-pair lookup).

## Status

0.1.0. Shipping.

## Design stance

The crosswalk is data, not code. Every mapping between two framework controls, articles, or sections lives as a row in a YAML file under `data/`. Every row carries a stable deterministic id, a relationship label from a fixed vocabulary, a confidence rating, and at least one citation source. The plugin does not infer relationships at runtime. It loads the YAML files, enforces seven machine-verifiable invariants, and answers structured queries.

This design makes the crosswalk auditable (every claim has a citation), maintainable (adding a framework pair means adding one YAML file, not writing code), and composable (other plugins such as soa-generator, gap-assessment, and management-review-packager can consume query results directly).

## Data scope

434 mapping entries across the following framework pairs, all versioned in `data/`:

| File | Pair | Rows |
|---|---|---|
| `iso42001-nist-ai-rmf.yaml` | ISO/IEC 42001 <-> NIST AI RMF | 72 |
| `iso42001-eu-ai-act.yaml` | ISO/IEC 42001 <-> EU AI Act | 88 |
| `iso42001-uk-atrs.yaml` | ISO/IEC 42001 <-> UK ATRS | 59 |
| `uk-atrs-nist-ai-rmf.yaml` | UK ATRS <-> NIST AI RMF | 59 |
| `colorado-sb205-crosswalk.yaml` | Colorado SB 205 -> ISO, NIST, EU AI Act | 54 |
| `nyc-ll144-crosswalk.yaml` | NYC LL144 -> ISO, NIST, EU AI Act | 36 |
| `california-crosswalk.yaml` | 7 California instruments -> ISO, NIST, EU AI Act | 66 |

Framework identifiers, jurisdictions, and citation formats are declared in `data/frameworks.yaml`. Row schema and invariants are documented in `data/SCHEMA.md`.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `query_type` | string | yes | One of `coverage`, `gaps`, `matrix`, `pair`. |
| `source_framework` | string | conditional | Required for `coverage`, `matrix`, `pair`, `gaps`. |
| `source_ref` | string | conditional | Required for `coverage`; optional narrowing for `pair`. |
| `target_framework` | string | conditional | Required for `gaps`, `pair`; optional for `matrix`. |
| `target_ref` | string | no | Optional narrowing for `pair`. |
| `confidence_min` | string | no | One of `high`, `medium`, `low`. Filters results to entries at or above the named level. |
| `relationship_filter` | list[str] | no | Restricts results to the listed relationship values. |
| `reviewed_by` | string | no | Reviewer attribution for the audit evidence chain. |

Per-query required fields:

- `coverage`: `source_framework`, `source_ref`.
- `gaps`: `source_framework`, `target_framework`.
- `matrix`: `source_framework` (and optionally `target_framework`).
- `pair`: `source_framework`, `target_framework` (typically with `source_ref` and `target_ref`).

## Outputs

Every result dict carries:

- `timestamp`: ISO 8601 UTC with `Z` suffix.
- `agent_signature`: `crosswalk-matrix-builder/0.1.0`.
- `query`: echo of the input query (for reproducibility and audit evidence).
- `citations`: top-level framework citation formats for the source and target.
- `warnings`: non-fatal notices. Populated if the result set is empty.
- `summary`: aggregate counts suitable for dashboard rendering.
- `reviewed_by`: present only when supplied.
- One of `matches` (coverage), `gaps` (gaps), `matrix` (matrix), or `pair` (pair), plus a stable `mappings` alias consumed by the renderers.

The summary dict is query-type specific:

- `coverage`: `total`, `by_target_framework`.
- `gaps`: `total`, `gap_count`.
- `matrix` / `pair`: `total`, `by_relationship`, `by_confidence`.

## Query examples

Coverage of ISO/IEC 42001 Annex A Control A.6.2.4 across every framework in the dataset:

```python
from plugins.crosswalk_matrix_builder import plugin  # or: import plugin

result = plugin.build_matrix({
    "query_type": "coverage",
    "source_framework": "iso42001",
    "source_ref": "A.6.2.4",
})
# result["matches"] lists every mapping anchored at ISO A.6.2.4.
# result["summary"]["by_target_framework"] counts matches per target.
```

Gaps from EU AI Act to ISO/IEC 42001:

```python
result = plugin.build_matrix({
    "query_type": "gaps",
    "source_framework": "eu-ai-act",
    "target_framework": "iso42001",
})
# result["gaps"] contains every no-mapping entry where EU AI Act has
# no ISO 42001 equivalent. Each entry's notes field explains the gap.
```

Full Colorado SB 205 crosswalk matrix against all target frameworks:

```python
result = plugin.build_matrix({
    "query_type": "matrix",
    "source_framework": "colorado-sb-205",
})
# result["matrix"] contains every row with colorado-sb-205 as source.
# result["summary"]["by_relationship"] counts satisfies,
# partial-satisfaction, complementary, statutory-presumption,
# and no-mapping entries.
```

Narrow single-pair lookup:

```python
result = plugin.build_matrix({
    "query_type": "pair",
    "source_framework": "iso42001",
    "source_ref": "A.2.2",
    "target_framework": "nist-ai-rmf",
    "target_ref": "GOVERN 1.1",
})
# result["pair"] is a list of zero or one rows.
```

## Relationship vocabulary

| Value | Meaning |
|---|---|
| `exact-match` | Source and target express equivalent intent with equivalent scope. Bidirectional. |
| `partial-match` | Substantial overlap. Source covers some aspects of target or vice versa. Bidirectional. |
| `satisfies` | Implementing the target satisfies the source requirement. Asymmetric. |
| `partial-satisfaction` | Implementing the target partially satisfies the source; additional controls required for full satisfaction. Asymmetric. |
| `complementary` | Related but not equivalent. Both address adjacent concerns. Bidirectional. |
| `statutory-presumption` | Implementing the target creates a rebuttable statutory presumption of compliance with the source. See Colorado SB 205 Section 6-1-1706(3). Asymmetric. |
| `no-mapping` | Explicit gap finding. Documented here so downstream plugins can surface the gap. |

See `data/SCHEMA.md` for the full invariants and citation-format requirements.

## Relationship to other plugins

- `soa-generator` consumes coverage queries to populate per-control justifications citing the satisfying target-framework reference.
- `gap-assessment` consumes gaps queries to seed the gap register with cited gap explanations rather than re-deriving them.
- `management-review-packager` can include coverage summaries as an input to the management-review data pack.
- `colorado-ai-act-compliance` uses the Colorado statutory-presumption rows to cite the ISO/NIST safe-harbor under Section 6-1-1706(3) and Section 6-1-1706(4).

## Tests

```bash
python3 plugins/crosswalk-matrix-builder/tests/test_plugin.py
```

Tests exercise every invariant, every query type, every filter, both renderers, the no-em-dash rule, and the statutory-presumption path. Twenty-four tests total.

## Related references

- NIST AI 600-1 Generative AI Profile, Appendix A (primary ISO 42001 to NIST AI RMF mapping): https://airc.nist.gov/airmf-resources/
- ISO/IEC 23894:2023, AI risk management guidance: https://www.iso.org/standard/77304.html
- CEN-CENELEC JTC 21, European harmonized-standards work program: https://www.cencenelec.eu/areas-of-work/cen-cenelec-topics/artificial-intelligence/
- ENISA, Multilayer Framework for Good Cybersecurity Practices for AI (2023) and follow-on AI risk mappings.
- Schellman, BDO, A-LIGN, KPMG, PwC, Deloitte, IAPP, Gibson Dunn, Davis Wright Tremaine, Perkins Coie, Orrick practitioner crosswalks cited in the per-file `citation_sources`.
