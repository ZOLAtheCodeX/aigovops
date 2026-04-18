---
name: cross-framework-crosswalk
version: 0.1.0
description: >
  Machine-readable cross-framework coverage map for AI governance
  programs. Operationalizes 434 cited mapping entries across 14
  framework identifiers and 6 controlling frameworks (ISO/IEC
  42001:2023, NIST AI RMF 1.0, EU AI Act, UK ATRS, Colorado SB 205,
  NYC LL144, plus the 7 California instruments) via the
  crosswalk-matrix-builder plugin. The crosswalk answers four
  query shapes: coverage (what does a given control satisfy
  elsewhere), gaps (what does framework A leave uncovered against
  framework B), matrix (full cross-framework view), and pair
  (single-pair lookup). Every row cites a primary or practitioner
  source and carries a confidence rating.
frameworks:
  - ISO/IEC 42001:2023
  - NIST AI Risk Management Framework 1.0
  - NIST AI 600-1 Generative AI Profile
  - Regulation (EU) 2024/1689 (EU AI Act)
  - UK Algorithmic Transparency Recording Standard v2.1
  - Colorado SB 24-205 (Colorado AI Act)
  - NYC Local Law 144 of 2021 (AEDT)
  - CPPA Automated Decisionmaking Technology regulations
  - California Consumer Privacy Act / California Privacy Rights Act
  - California SB 942 (AI Transparency Act)
  - California AB 2013 (Training Data Transparency)
  - California AB 1008 (PII in AI systems)
  - California SB 1001 (Bot Disclosure Act)
  - California AB 1836 (Digital Replica of Deceased Personalities)
tags:
  - ai-governance
  - crosswalk
  - iso42001
  - nist-ai-rmf
  - eu-ai-act
  - uk-atrs
  - colorado-sb-205
  - nyc-ll144
  - california-ai
  - statutory-presumption
  - multi-framework
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the AIGovOps cross-framework crosswalk: a machine-readable, cited, auditable coverage map between the primary AI governance frameworks (ISO/IEC 42001:2023, NIST AI Risk Management Framework 1.0 (AI RMF 1.0)) and every secondary jurisdictional instrument shipped in the catalogue (EU AI Act, UK ATRS, Colorado SB 205, NYC LL144, and the 7 California instruments). The data surface contains 434 cited mapping entries across 7 YAML files, served by the `crosswalk-matrix-builder` plugin via four query types: coverage, gaps, matrix, and pair.

The crosswalk is the backbone artifact for running a multi-framework AI governance program without duplicating documentation. One implementation pass on ISO 42001 and NIST AI RMF covers the operational core of EU AI Act Chapter III, the UK ATRS transparency record, the Colorado SB 205 deployer duties, and the California Attorney General's 2024-12-18 AI guidance. The crosswalk names where that one pass does not cover, cites the authority for every claim, and flags confidence where the mapping is practitioner inference rather than primary-source text.

Primary users are ISO/IEC 42001 Lead Implementers running multi-jurisdiction programs, auditors verifying safe-harbor claims (Colorado SB 205 Section 6-1-1706(3) rebuttable presumption is the current canonical example), and program sponsors scoping framework overlays against a budgeted control baseline.

## Scope

**In scope.** Cross-framework coverage, gap, and matrix queries across the 14 framework identifiers defined in `plugins/crosswalk-matrix-builder/data/frameworks.yaml`. Specifically:

- 434 cited mapping rows across 7 YAML files under `plugins/crosswalk-matrix-builder/data/`.
- 7 relationship-vocabulary values (exact-match, partial-match, satisfies, partial-satisfaction, complementary, statutory-presumption, no-mapping).
- 3 confidence levels (high, medium, low) with evidentiary criteria per `data/SCHEMA.md`.
- 4 query types (coverage, gaps, matrix, pair) and the accompanying filter set (confidence floor, relationship whitelist).
- Top-level and per-row citations in the format declared in each framework's `citation_format` field.

**Out of scope.** The crosswalk does not:

- Interpret law. Every entry cites a published source. Author inference is flagged as `confidence: low` and requires an explicit `practitioner-inference` note.
- Invent relationships. The plugin does not run text-similarity heuristics. It loads YAML, enforces the seven invariants declared in `data/SCHEMA.md`, and answers structured queries.
- Conduct the management-system implementation. Consumer plugins (soa-generator, gap-assessment, risk-register-builder, audit-log-generator, aisia-runner, high-risk-classifier, nyc-ll144-audit-packager) produce the implementation artifacts and consume crosswalk results as a justification substrate.
- Track framework amendments in real time. The `framework-drift` playbook governs refresh cadence. The dataset is flagged as 90-day quarterly review.

## Framework Reference

**Authoritative sources.**

- ISO/IEC 42001:2023, Information technology, Artificial intelligence, Management system: https://www.iso.org/standard/81230.html.
- NIST AI Risk Management Framework 1.0 and NIST AI 600-1 Generative AI Profile: https://www.nist.gov/itl/ai-risk-management-framework and https://airc.nist.gov/airmf-resources/.
- Regulation (EU) 2024/1689 (EU AI Act): https://eur-lex.europa.eu/eli/reg/2024/1689/oj.
- UK Algorithmic Transparency Recording Standard v2.1: https://www.gov.uk/government/publications/algorithmic-transparency-recording-standard-guidance-for-public-sector-bodies.
- Colorado SB 24-205 (Colorado AI Act): https://leg.colorado.gov/bills/sb24-205. Operative 2026-06-30.
- NYC Local Law 144 of 2021 and DCWP AEDT Final Rule: https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/.
- CPPA Automated Decisionmaking Technology regulations: https://cppa.ca.gov/regulations/.
- California Legislative Information portal (SB 942, AB 2013, AB 1008, SB 1001, AB 1836, CCPA/CPRA): https://leginfo.legislature.ca.gov/.

**14 framework identifiers enumerated.** Source of truth: `plugins/crosswalk-matrix-builder/data/frameworks.yaml`.

| Identifier | Name | Jurisdiction |
|---|---|---|
| `iso42001` | ISO/IEC 42001:2023 | international |
| `nist-ai-rmf` | NIST AI Risk Management Framework 1.0 | usa-federal |
| `nist-ai-600-1` | NIST AI 600-1 Generative AI Profile | usa-federal |
| `eu-ai-act` | Regulation (EU) 2024/1689 (EU AI Act) | eu |
| `uk-atrs` | UK Algorithmic Transparency Recording Standard v2.1 | uk |
| `colorado-sb-205` | Colorado SB 24-205 (Colorado AI Act) | usa-co |
| `nyc-ll144` | NYC Local Law 144 of 2021 (AEDT) | usa-nyc |
| `cppa-admt` | CPPA Automated Decisionmaking Technology regulations | usa-ca |
| `ccpa-cpra` | California Consumer Privacy Act / California Privacy Rights Act | usa-ca |
| `ca-sb-942` | California AI Transparency Act (SB 942) | usa-ca |
| `ca-ab-2013` | California Training Data Transparency (AB 2013) | usa-ca |
| `ca-ab-1008` | California AB 1008 (PII in AI systems) | usa-ca |
| `ca-sb-1001` | California Bot Disclosure Act (SB 1001) | usa-ca |
| `ca-ab-1836` | California Digital Replica of Deceased Personalities Act (AB 1836) | usa-ca |

**Data scope.** 434 cited mapping rows across 7 files:

| File | Pair | Rows |
|---|---|---|
| `iso42001-nist-ai-rmf.yaml` | ISO 42001 vs NIST AI RMF | 72 |
| `iso42001-eu-ai-act.yaml` | ISO 42001 vs EU AI Act | 88 |
| `iso42001-uk-atrs.yaml` | ISO 42001 vs UK ATRS | 59 |
| `uk-atrs-nist-ai-rmf.yaml` | UK ATRS vs NIST AI RMF | 59 |
| `colorado-sb205-crosswalk.yaml` | Colorado SB 205 vs ISO, NIST, EU AI Act | 54 |
| `nyc-ll144-crosswalk.yaml` | NYC LL144 vs ISO, NIST, EU AI Act | 36 |
| `california-crosswalk.yaml` | 7 California instruments vs ISO, NIST, EU AI Act | 66 |

## Operationalizable Controls

One Tier 1 operationalization. The skill is an infrastructure skill: it serves the other skills and plugins. The operationalization is the query pattern and the downstream plugin-integration roadmap.

### T1.1 Cross-framework query and consumer-plugin integration

Class: A. Artifact: query result with top-level citations, per-row citations, summary counts, and warnings. Leverage: H. Consumer: all downstream plugins listed below.

**Requirement summary.** The crosswalk supports every plugin in the catalogue that must answer the question "does implementing X against framework A cover me against framework B". The canonical query pattern is:

```python
from plugins.crosswalk_matrix_builder import plugin

result = plugin.build_matrix({
    "query_type": "coverage",
    "source_framework": "iso42001",
    "source_ref": "A.6.2.4",
})
```

The consumer plugins consume `result["mappings"]` directly. Each row is self-describing: `source_framework`, `source_ref`, `target_framework`, `target_ref`, `relationship`, `confidence`, `citation_sources`, `notes`.

**Operationalization map (per consumer plugin).**

See `operationalization-map.md` in this directory for the per-plugin scenario, query pattern, and integration status. The seven consumer plugins are:

- `soa-generator`: coverage queries to auto-populate partial-implementation status when the target framework covers a control.
- `gap-assessment`: gaps queries to surface uncovered controls into the gap register.
- `aisia-runner`: coverage queries anchored on ISO 42001 Clause 6.1.4 against `eu-ai-act` to confirm whether the emitted impact-assessment format satisfies EU AI Act Article 27 FRIA requirements.
- `risk-register-builder`: pair and matrix queries to enrich each risk-register row with the citation into the appropriate target-framework clause.
- `audit-log-generator`: coverage queries to enrich each Annex A citation with cross-framework equivalents (NIST subcategory, EU AI Act article).
- `high-risk-classifier`: matrix queries on `colorado-sb-205` to confirm that the Section 6-1-1706(3) statutory-presumption rows are present when advising on deployer safe-harbor posture.
- `nyc-ll144-audit-packager`: coverage queries anchored on NYC LL144 sections to cite the ISO 42001 and NIST AI RMF equivalents in the public-disclosure bundle.

**Relationship vocabulary.**

Seven canonical values, defined in `plugins/crosswalk-matrix-builder/data/SCHEMA.md`. The plugin enforces the vocabulary at load time.

| Value | Semantics | Symmetry |
|---|---|---|
| `exact-match` | Source and target express equivalent intent with equivalent scope. | bidirectional allowed |
| `partial-match` | Substantial overlap. Source covers some aspects of target or vice versa. | bidirectional allowed |
| `satisfies` | Implementing the target satisfies the source requirement. | asymmetric |
| `partial-satisfaction` | Implementing the target partially satisfies the source. Additional controls required for full satisfaction. | asymmetric |
| `complementary` | Related but not equivalent. Both address adjacent concerns. | bidirectional allowed |
| `statutory-presumption` | A statute explicitly recognizes conformance with the target as rebuttable evidence of compliance with the source. | asymmetric |
| `no-mapping` | Explicit gap finding. The source has no equivalent in the target. Requires a non-empty `notes` field. | asymmetric |

**Statutory-presumption (special case).**

The `statutory-presumption` relationship is reserved for the narrow case where a statute names another framework and assigns legal effect to conformance with it. Colorado SB 205 Section 6-1-1706(3) is the only currently-shipped instance: conformance with the NIST AI RMF or ISO/IEC 42001:2023 creates a rebuttable presumption of reasonable care for a deployer defending against an attorney-general action. Section 6-1-1706(4) extends the same posture to the affirmative-defense-on-cure pathway.

This relationship is encoded as its own vocabulary value, not folded into `satisfies`, because the legal effect is statutory and asymmetric: the statute names the framework, and the framework does not name the statute. Downstream plugins (`colorado-ai-act-compliance`, `high-risk-classifier`) must cite the statutory-presumption rows by id when advising on deployer liability posture. Treating these rows as ordinary `satisfies` edges would obscure the affirmative-defense semantics and create audit risk.

**Confidence calibration.**

Three levels, criteria declared in `data/SCHEMA.md`. Summary for this skill:

| Level | Evidentiary criterion | Use for |
|---|---|---|
| `high` | Primary-source citation (NIST AI 600-1 Appendix A; ENISA published mapping; CEN-CENELEC JTC 21 harmonised-standards crosswalk; the statute itself). | Formal attestation, audit evidence, safe-harbor claims. |
| `medium` | Published practitioner crosswalk from a recognized firm (Schellman, BDO, A-LIGN, KPMG, PwC, Deloitte, IAPP, Gibson Dunn, DWT, Perkins Coie, Orrick) with logical derivation. | Operational program decisions, gap registers, SoA justifications. |
| `low` | Author inference with no published source. Flagged `practitioner-inference`. | Internal working drafts only. Not acceptable as audit evidence. |

Medium-confidence is adequate for most operational decisions. High-confidence is the bar for formal attestation and for any artifact entering an audit evidence package. Low-confidence rows are rare by design; the plugin refuses to load any low-confidence entry that lacks a citation or an explicit `practitioner-inference` note.

**Citations format.**

Every query result carries a top-level `citations` list (one per framework touched, in that framework's declared citation format) and per-row `citation_sources` (publication plus optional URL plus date). Citation formats match the STYLE.md canonical formats for each framework. The plugin does not rewrite citations; it passes through the formats declared in `data/frameworks.yaml`.

**Input schema.**

See `plugins/crosswalk-matrix-builder/plugin.py` and `plugins/crosswalk-matrix-builder/README.md`. Per-query required fields:

- `coverage`: `source_framework`, `source_ref`.
- `gaps`: `source_framework`, `target_framework`.
- `matrix`: `source_framework` (optionally `target_framework`).
- `pair`: `source_framework`, `target_framework` (typically with `source_ref` and `target_ref`).

Optional across all queries: `confidence_min`, `relationship_filter`, `reviewed_by`.

**Output structure.**

See `plugins/crosswalk-matrix-builder/plugin.py`. Every result dict carries: `timestamp`, `agent_signature`, `query`, `citations`, `warnings`, `summary`, plus a per-query-type key (`matches`, `gaps`, `matrix`, `pair`) and the stable `mappings` alias consumed by renderers. `render_markdown` and `render_csv` produce the auditor-facing surfaces.

**Jurisdiction coverage.** The 14 framework identifiers map to 7 jurisdictions:

| Jurisdiction | Framework identifiers | Notes |
|---|---|---|
| international | `iso42001` | Certification baseline. |
| eu | `eu-ai-act` | Directly applicable law; extraterritorial reach. |
| uk | `uk-atrs` | Non-binding transparency standard for public sector. |
| usa-federal | `nist-ai-rmf`, `nist-ai-600-1` | Voluntary. Federal contractor baseline emerging. |
| usa-co | `colorado-sb-205` | Enforceable. Operative 2026-06-30. Statutory-presumption surface. |
| usa-nyc | `nyc-ll144` | Enforceable since 2023-07-05. Narrow (employment). |
| usa-ca | `cppa-admt`, `ccpa-cpra`, `ca-sb-942`, `ca-ab-2013`, `ca-ab-1008`, `ca-sb-1001`, `ca-ab-1836` | California is a constellation of 7 instruments, not a single law. The `california-crosswalk.yaml` file anchors each instrument against ISO, NIST, and EU AI Act. |

## Output Standards

Outputs produced under this skill must meet the certification-grade quality bar in [STYLE.md](../../STYLE.md). Specifically:

- Top-level citations use the exact `citation_format` declared in `frameworks.yaml` for each framework. ISO uses `ISO/IEC 42001:2023, Clause X.X.X` or `ISO/IEC 42001:2023, Annex A, Control A.X.Y`. NIST uses `<FUNCTION> <Subcategory>`. EU AI Act uses `EU AI Act, Article XX, Paragraph X`. UK ATRS uses `UK ATRS, Section <name>`. Colorado SB 205 uses `Colorado SB 205, Section <section>`. NYC LL144 uses the three-form prefix declared in STYLE.md. California uses the per-instrument format per STYLE.md.
- Every mapping row surfaced in a result carries at least one `citation_sources` entry.
- No em-dashes (U+2014). No emojis. No hedging phrases.
- Empty result sets emit a warning. They do not fail the query.
- Low-confidence rows surface in output only if the caller set `confidence_min: low`. The default query pattern does not surface them.

## Maintenance

The crosswalk data is high-touch. It is flagged for quarterly framework-drift review on a 90-day cadence. Review triggers:

- NIST AI RMF is expected to iterate toward 2.0; mapping edges into NIST subcategories are refreshed when NIST publishes.
- EU AI Act delegated acts and implementing acts publish continuously. Articles 6, 40, 43, and 47-48 carry the highest delta risk through 2026.
- CEN-CENELEC JTC 21 harmonised standards land through 2026. Each landed standard may change the `satisfies` edges against EU AI Act.
- California legislative sessions produce new AI bills every year. The `california-crosswalk.yaml` file is the highest-churn file in the dataset.
- Colorado SB 205 operative date 2026-06-30 may trigger Attorney General rulemaking that changes the statutory-presumption semantics.

Refresh process: on each quarterly review, re-run the `consistency_audit.py` audit, re-validate at least the top-5 highest-use mapping pairs against primary sources, and update the `date` field in `citation_sources` where a revised primary source landed.

## Limitations

- The crosswalk does not interpret law or invent mappings. Every entry cites a source. Practitioner judgment remains required for edge cases, for any `confidence: medium` row, and for all `confidence: low` rows.
- Medium-confidence rows reflect a specific practitioner-firm analysis at a specific date. Where the date predates a material amendment to either framework, the row is stale by definition. The 90-day review cadence mitigates but does not eliminate this.
- The statutory-presumption rows encode Colorado SB 205 Section 6-1-1706(3) and Section 6-1-1706(4) as currently drafted. Colorado Attorney General rulemaking after the 2026-06-30 operative date may narrow or widen the presumption. The skill does not track enforcement actions or settlements; operational intelligence about Colorado AG enforcement posture is a separate information product.
- The California crosswalk anchors against 7 instruments. It does not attempt to anchor against the CPPA regulatory text line-by-line; CPPA ADMT regulations are cited at the section level.
- The crosswalk does not replace the `framework-drift` playbook. The skill is the data surface; the playbook is the refresh process.
