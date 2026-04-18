# cross-framework-crosswalk operationalization map

How the crosswalk serves each consumer plugin in the AIGovOps catalogue. The crosswalk is an infrastructure skill: it holds the cited coverage data, and the consumer plugins assemble implementation artifacts on top of it.

Integration status is `deferred` for every consumer plugin at the 0.1.0 crosswalk release. No plugin currently invokes `crosswalk_matrix_builder.plugin.build_matrix` at runtime. This document is the future-work roadmap. Integration lands per-plugin as each plugin reaches a minor-version increment that justifies the additional dependency.

## soa-generator

**Scenario.** The Statement of Applicability (SoA) generator produces one row per ISO/IEC 42001:2023 Annex A control. For each row, it must state implementation status, justification, and controlling framework references. When the caller operates in a multi-framework posture (for example, ISO 42001 plus NIST AI RMF), the generator should auto-populate the partial-implementation status on the basis of the crosswalk: if the target framework already covers the Annex A control at `exact-match` or `satisfies`, the SoA row starts at implemented with the cross-reference; if the target covers it at `partial-match` or `partial-satisfaction`, the row starts at partially-implemented with the gap cited.

**Query pattern.**

```python
from plugins.crosswalk_matrix_builder import plugin as crosswalk

for control in iso_42001_annex_a_controls:
    result = crosswalk.build_matrix({
        "query_type": "coverage",
        "source_framework": "iso42001",
        "source_ref": control.id,
        "confidence_min": "medium",
    })
    for row in result["mappings"]:
        soa_row.add_cross_reference(
            framework=row["target_framework"],
            ref=row["target_ref"],
            relationship=row["relationship"],
            citation=row["citation_sources"][0]["publication"],
        )
```

**Expected output shape.** `result["mappings"]` is a list of coverage rows. `result["summary"]["by_target_framework"]` gives a dict of counts per target framework, suitable for the SoA cover-page dashboard. `result["citations"]` is the top-level citation list (source framework citation plus every target-framework citation touched).

**Integration status.** `deferred`. `soa-generator/0.1.0` produces SoA rows without cross-framework auto-population. Integration targets `soa-generator/0.2.0`.

## gap-assessment

**Scenario.** The gap-assessment plugin produces a gap register for a program running against a target framework. Each gap row must name the source-framework clause that lacks a target-framework equivalent and cite the authority for the gap claim. The crosswalk answers exactly this question via `query_type: gaps`.

**Query pattern.**

```python
result = crosswalk.build_matrix({
    "query_type": "gaps",
    "source_framework": "eu-ai-act",
    "target_framework": "iso42001",
})

for gap in result["gaps"]:
    gap_register.add(
        source_ref=gap["source_ref"],
        source_title=gap["source_title"],
        explanation=gap["notes"],
        citation=gap["citation_sources"][0]["publication"],
    )
```

**Expected output shape.** `result["gaps"]` is a list of `no-mapping` rows. Each row carries the authoritative `notes` field explaining the gap (for example, why EU AI Act Article 43 conformity assessment has no ISO 42001 equivalent). `result["summary"]["gap_count"]` is the total count.

**Integration status.** `deferred`. `gap-assessment/0.1.0` produces gap rows against the caller's own analysis. Integration targets `gap-assessment/0.2.0`.

## aisia-runner

**Scenario.** The AI System Impact Assessment (AISIA) runner emits an impact assessment anchored on ISO/IEC 42001:2023 Clause 6.1.4. When the caller is operating an EU AI Act high-risk system, the emitted AISIA must satisfy EU AI Act Article 27 FRIA requirements. The crosswalk tells the runner whether the current AISIA format covers Article 27 at `satisfies` or only at `partial-satisfaction`, and in the latter case cites which additional fields the FRIA requires beyond the AISIA.

**Query pattern.**

```python
result = crosswalk.build_matrix({
    "query_type": "pair",
    "source_framework": "eu-ai-act",
    "source_ref": "Article 27",
    "target_framework": "iso42001",
    "target_ref": "Clause 6.1.4",
})

if result["pair"]:
    row = result["pair"][0]
    aisia.record_fria_posture(
        relationship=row["relationship"],
        gap_notes=row.get("notes") or "",
    )
```

**Expected output shape.** `result["pair"]` is a list of zero or one rows anchored at the EU AI Act Article 27 vs ISO 42001 Clause 6.1.4 pair. The `relationship` field tells the runner whether FRIA coverage is complete. The `notes` field cites the residual gap (typically Article 27's stakeholder-consultation and publication specifics).

**Integration status.** `deferred`. `aisia-runner/0.2.0` emits the AISIA without a FRIA posture callout. Integration targets `aisia-runner/0.3.0`.

## risk-register-builder

**Scenario.** The risk-register builder produces one row per identified AI risk. Each row must cite the controlling clauses from every framework in scope. The crosswalk enriches each row by taking the ISO 42001 clause the risk is anchored on and surfacing the NIST AI RMF subcategory, the EU AI Act article, and (where applicable) the Colorado SB 205 section.

**Query pattern.**

```python
for risk in risk_register:
    result = crosswalk.build_matrix({
        "query_type": "matrix",
        "source_framework": "iso42001",
    })
    for row in result["matrix"]:
        if row["source_ref"] == risk.iso_anchor:
            risk.add_citation(
                framework=row["target_framework"],
                ref=row["target_ref"],
                relationship=row["relationship"],
            )
```

In practice the caller caches the matrix result once per build rather than re-issuing per risk.

**Expected output shape.** `result["matrix"]` is the full ISO 42001 source matrix. `result["summary"]["by_relationship"]` gives the relationship distribution, suitable for a risk-register cover-page chart.

**Integration status.** `deferred`. `risk-register-builder/0.1.0` produces risk rows with ISO 42001 anchors only. Integration targets `risk-register-builder/0.2.0`.

## audit-log-generator

**Scenario.** The audit-log generator maps raw audit events to Annex A controls. When the audit log is consumed by a reviewer operating against NIST AI RMF or EU AI Act, each Annex A citation must carry the cross-framework equivalent. The crosswalk provides the equivalent list and the confidence rating for each edge.

**Query pattern.**

```python
for event in audit_events:
    for annex_a_ref in event.annex_a_refs:
        result = crosswalk.build_matrix({
            "query_type": "coverage",
            "source_framework": "iso42001",
            "source_ref": annex_a_ref,
            "confidence_min": "high",
        })
        event.enrich_with_cross_framework_refs(result["mappings"])
```

**Expected output shape.** `result["mappings"]` is the list of cross-framework equivalents for the named Annex A control, filtered to high-confidence rows only. The high-confidence filter is important for audit-log output because audit logs enter formal evidence packages.

**Integration status.** `deferred`. `audit-log-generator/0.1.0` emits Annex A citations without cross-framework enrichment. Integration targets `audit-log-generator/0.2.0`.

## high-risk-classifier

**Scenario.** The high-risk classifier determines whether an AI system is classified as high-risk under Colorado SB 205. When the classifier returns a high-risk determination for a deployer, it must advise on whether the Section 6-1-1706(3) rebuttable-presumption posture is available. The crosswalk answers this by surfacing the four statutory-presumption rows (Section 6-1-1706(3) vs ISO 42001, Section 6-1-1706(3) vs NIST AI RMF, Section 6-1-1706(4) vs ISO 42001 Annex A, Section 6-1-1706(4) vs NIST AI RMF).

**Query pattern.**

```python
result = crosswalk.build_matrix({
    "query_type": "matrix",
    "source_framework": "colorado-sb-205",
    "relationship_filter": ["statutory-presumption"],
})

classifier.advise_safe_harbor_posture(
    rows=result["mappings"],
    summary=result["summary"],
)
```

**Expected output shape.** `result["mappings"]` contains exactly the statutory-presumption rows from `colorado-sb205-crosswalk.yaml`. `result["summary"]["by_relationship"]` confirms the count. The classifier uses the rows to advise the deployer which framework conformance evidence supports the rebuttable-presumption argument.

**Integration status.** `deferred`. `high-risk-classifier/0.1.0` returns the high-risk determination without safe-harbor advice. Integration targets `high-risk-classifier/0.2.0`.

## nyc-ll144-audit-packager

**Scenario.** The NYC LL144 audit packager produces the public-disclosure bundle required by DCWP Final Rule Section 5-304. The bundle is strictly LL144-scoped, but callers working across frameworks benefit from seeing the ISO 42001 and NIST AI RMF equivalents for each LL144 section. The crosswalk provides the equivalents via coverage queries anchored on NYC LL144 sections.

**Query pattern.**

```python
for section in ("Section 5-301", "Section 5-303", "Section 5-304"):
    result = crosswalk.build_matrix({
        "query_type": "coverage",
        "source_framework": "nyc-ll144",
        "source_ref": section,
    })
    bundle.add_cross_framework_appendix(section, result["mappings"])
```

**Expected output shape.** `result["mappings"]` is the list of cross-framework equivalents for the named LL144 section (typically ISO 42001 Clause 6.1.3 and Annex A Control A.6.2.4 at `partial-match`, plus NIST AI RMF MEASURE 2.11 at `partial-match`).

**Integration status.** `deferred`. `nyc-ll144-audit-packager/0.1.0` emits the bundle without a cross-framework appendix. Integration targets `nyc-ll144-audit-packager/0.2.0`.
