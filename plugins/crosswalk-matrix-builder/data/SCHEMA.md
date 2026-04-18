# Crosswalk data schema

Canonical format for every cross-framework mapping entry in AIGovOps. Every `.yaml` file under `data/` conforms to this schema.

## File layout

```text
plugins/crosswalk-matrix-builder/data/
  SCHEMA.md                              this document
  frameworks.yaml                        framework-level metadata (id, name, version, jurisdiction, url)
  iso42001-nist-ai-rmf.yaml             ISO <-> NIST mappings (primary research source: NIST AI 600-1 Appendix A)
  iso42001-eu-ai-act.yaml                EU AI Act <-> ISO 42001
  iso42001-uk-atrs.yaml                  UK ATRS <-> ISO 42001
  uk-atrs-nist-ai-rmf.yaml               UK ATRS <-> NIST AI RMF
  colorado-sb205-crosswalk.yaml          Colorado SB 205 -> ISO + NIST + EU AI Act
  nyc-ll144-crosswalk.yaml               NYC LL144 -> ISO + NIST + EU AI Act
  california-crosswalk.yaml              7 California instruments -> ISO + NIST + EU AI Act
```

Rationale: one file per source-target pair keeps per-pair diffs reviewable; one file per USA state law (with multiple target frameworks in rows) keeps jurisdiction-scope work bundled.

## frameworks.yaml

Canonical framework identifiers used in every mapping file. A framework name appearing in a mapping must exist here.

```yaml
frameworks:
  - id: iso42001
    name: "ISO/IEC 42001:2023"
    jurisdiction: international
    authority: "ISO/IEC"
    published: "2023-12"
    url: "https://www.iso.org/standard/81230.html"
    citation_format: "ISO/IEC 42001:2023, Clause X.X.X"
    annex_a_citation_format: "ISO/IEC 42001:2023, Annex A, Control A.X.Y"

  - id: nist-ai-rmf
    name: "NIST AI Risk Management Framework 1.0"
    jurisdiction: usa-federal
    authority: "NIST"
    published: "2023-01"
    url: "https://www.nist.gov/itl/ai-risk-management-framework"
    citation_format: "<FUNCTION> <Subcategory>"

  - id: nist-ai-600-1
    name: "NIST AI 600-1 Generative AI Profile"
    jurisdiction: usa-federal
    authority: "NIST"
    published: "2024-07"
    url: "https://airc.nist.gov/airmf-resources/"
    citation_format: "NIST AI 600-1, Section <section>"

  - id: eu-ai-act
    name: "Regulation (EU) 2024/1689 (EU AI Act)"
    jurisdiction: eu
    authority: "European Parliament and Council"
    published: "2024-06"
    url: "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"
    citation_format: "EU AI Act, Article XX, Paragraph X"
    annex_citation_format: "EU AI Act, Annex <N>, <category>"

  - id: uk-atrs
    name: "UK Algorithmic Transparency Recording Standard v2.1"
    jurisdiction: uk
    authority: "UK CDDO / DSIT"
    published: "2024-01"
    url: "https://www.gov.uk/government/publications/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies"
    citation_format: "UK ATRS, Section <name>"

  - id: colorado-sb-205
    name: "Colorado SB24-205 (Colorado AI Act)"
    jurisdiction: usa-co
    authority: "Colorado General Assembly"
    published: "2024-05"
    operative: "2026-06-30"
    url: "https://leg.colorado.gov/bills/sb24-205"
    citation_format: "Colorado SB 205, Section <section>"

  - id: nyc-ll144
    name: "NYC Local Law 144 (AEDT)"
    jurisdiction: usa-nyc
    authority: "NYC Council; NYC DCWP"
    published: "2021-12"
    operative: "2023-07-05"
    url: "https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/"
    citation_format: "NYC LL144"
    rule_citation_format: "NYC DCWP AEDT Rules, 6 RCNY Section 5-<n>"

  - id: cppa-admt
    name: "CPPA Automated Decisionmaking Technology regulations"
    jurisdiction: usa-ca
    authority: "California Privacy Protection Agency"
    published: "2025-09"
    operative: "2026-01-01"
    url: "https://cppa.ca.gov/regulations/"
    citation_format: "Cal. Code Regs. tit. 11, Section 7<nnn>"

  - id: ccpa-cpra
    name: "California Consumer Privacy Act / California Privacy Rights Act"
    jurisdiction: usa-ca
    citation_format: "Cal. Civ. Code Section 1798.<nnn>"

  - id: ca-sb-942
    name: "California AI Transparency Act"
    jurisdiction: usa-ca
    published: "2024-09"
    url: "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240SB942"
    citation_format: "Cal. Bus. & Prof. Code Section <nnn>"

  - id: ca-ab-2013
    name: "California Training Data Transparency"
    jurisdiction: usa-ca
    published: "2024-09"
    url: "https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202320240AB2013"
    citation_format: "California AB 2013, Section <section>"

  - id: ca-ab-1008
    name: "California AB 1008 (PII in AI systems)"
    jurisdiction: usa-ca
    published: "2024-09"
    citation_format: "Cal. Civ. Code Section 1798.140(v)"

  - id: ca-sb-1001
    name: "California Bot Disclosure Act"
    jurisdiction: usa-ca
    published: "2018"
    citation_format: "Cal. Bus. & Prof. Code Section 17940"

  - id: ca-ab-1836
    name: "California Digital Replica of Deceased Personalities Act"
    jurisdiction: usa-ca
    published: "2024-09"
    citation_format: "Cal. Civ. Code Section 3344.1"
```

## Mapping entry

Every row in every mapping file conforms to this structure:

```yaml
- id: <stable-deterministic-id>
  source_framework: <framework-id>
  source_ref: "<clause/article/section>"
  source_title: "<title or short description>"
  target_framework: <framework-id>
  target_ref: "<clause/article/section>"
  target_title: "<title or short description>"
  relationship: exact-match | partial-match | satisfies | partial-satisfaction | complementary | statutory-presumption | no-mapping
  confidence: high | medium | low
  citation_sources:
    - publication: "<name>"
      url: "<optional>"
      date: "<YYYY-MM or YYYY>"
  notes: "<optional free-text caveat>"
  bidirectional: true | false
```

### `id` field

Stable deterministic id: `<source_framework>--<source_ref_slug>--<target_framework>--<target_ref_slug>`. Slugs lowercased with dots and spaces collapsed to hyphens. Example: `iso42001--a-2-2--nist-ai-rmf--govern-1-1`. Enables referencing from plugins, docs, and other crosswalk files.

### Relationship vocabulary

| Value | Meaning |
|---|---|
| `exact-match` | Source and target express equivalent intent with equivalent scope. |
| `partial-match` | Substantial overlap. Source covers some aspects of target or vice versa. |
| `satisfies` | Source requirement is satisfied by implementing target. Asymmetric. |
| `partial-satisfaction` | Source requirement is partially satisfied by target. Implementation of additional controls required for full satisfaction. |
| `complementary` | Relevant but not equivalent. Both address a related concern from different angles. |
| `statutory-presumption` | Implementing target creates a rebuttable presumption of compliance with source (e.g., Colorado SB 205 Section 6-1-1706(3) safe-harbor). Asymmetric. |
| `no-mapping` | Explicit gap finding. The source has no equivalent in target, documented here so downstream plugins can surface the gap. |

`bidirectional: true` means the reverse mapping (target-to-source) holds with the same relationship. For asymmetric relationships (`satisfies`, `partial-satisfaction`, `statutory-presumption`) this is always false.

### Confidence

| Value | Criteria |
|---|---|
| `high` | Explicit citation in a primary source (NIST AI 600-1 Appendix A; ENISA published mapping; CEN-CENELEC JTC 21 published crosswalk; the statute itself). |
| `medium` | Published practitioner crosswalk (Schellman, BDO, A-LIGN, KPMG, PwC, Deloitte, IAPP, Gibson Dunn, DWT, Perkins Coie, Orrick) with logical derivation. |
| `low` | Author inference with no published source. Flagged `practitioner-inference` in citation. |

### Citation sources

At least one entry required. For primary sources (e.g., the statute itself), url is optional if the publication name is self-identifying. For practitioner sources, url is encouraged.

## Gap entry (bidirectional gap analysis)

A `no-mapping` entry is how gaps are encoded. The `source_ref` is the framework control with no equivalent; the `target_framework` is the framework checked for coverage; `target_ref` is empty string; `notes` names the gap and why it exists.

```yaml
- id: iso42001--a-2-4--nist-ai-rmf--no-equivalent
  source_framework: iso42001
  source_ref: "A.2.4"
  source_title: "Review of the AI policy"
  target_framework: nist-ai-rmf
  target_ref: ""
  target_title: ""
  relationship: no-mapping
  confidence: high
  citation_sources:
    - publication: "NIST AI 600-1 Appendix A"
      date: "2024-07"
  notes: "NIST AI RMF does not mandate periodic policy review cycles. This is a management-system artifact inherited from ISO 27001 structure. Closest analog is GOVERN 1.7 (decommissioning), which is not equivalent."
  bidirectional: false
```

## Machine-verifiable invariants

These must hold for every mapping file:

1. Every `source_framework` and `target_framework` exists in `frameworks.yaml`.
2. Every `id` is unique across all mapping files combined.
3. Every `confidence: low` entry has at least one citation source or explicit `practitioner-inference` note.
4. `bidirectional: true` only permitted for `exact-match`, `partial-match`, or `complementary` relationships.
5. Every `no-mapping` entry has a non-empty `notes` field explaining the gap.
6. Every citation format referenced in a mapping entry conforms to the `citation_format` declared for the framework in `frameworks.yaml`.
7. No em-dashes (U+2014). No emojis. Hyphens only.

Plugin tests enforce all seven invariants.

Last updated: 2026-04-18.
