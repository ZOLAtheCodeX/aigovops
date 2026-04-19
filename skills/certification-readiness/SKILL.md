---
name: certification-readiness
version: 0.1.0
description: >
  Certification readiness assessment skill. Consumes an evidence bundle
  produced by the evidence-bundle-packager plugin and a target
  certification or conformity assessment, and returns a graduated
  readiness verdict (ready-with-high-confidence, ready-with-conditions,
  partially-ready, not-ready) with section-by-section evidence
  completeness, cross-framework citation coverage, specific gaps or
  blockers, and curated remediation recommendations. Maps to ISO/IEC
  42001:2023 Clauses 9.2 (internal audit), 9.3 (management review), and
  10.1 (continual improvement); EU AI Act Article 43 (conformity
  assessment procedures), Annex VI (internal control), and Annex VII
  (notified body); and Colorado SB 205 Section 6-1-1706(3) (safe-harbor
  rebuttable presumption test).
frameworks:
  - ISO/IEC 42001:2023
  - EU AI Act (Regulation (EU) 2024/1689)
  - Colorado SB 205
  - NYC LL144
  - Singapore MAGF 2e
  - UK Algorithmic Transparency Recording Standard
tags:
  - ai-governance
  - certification
  - readiness
  - consumer-plugin
  - audit-preparation
  - conformity-assessment
  - safe-harbor
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill closes the AI governance cycle. Every other skill in the catalogue produces an artifact; this skill consumes the packaged artifact set and answers the decisive question: is the organization ready to pass a specific certification or conformity assessment?

Readiness is graduated. The skill emits one of four verdicts:

- **ready-with-high-confidence.** Every critical required artifact is present, every evidence-strength threshold is met, no warnings on critical controls, and every expected citation appears in the bundle's citation summary.
- **ready-with-conditions.** All critical artifacts present, but one or more non-critical controls carry warnings. Conditions are listed explicitly.
- **partially-ready.** Some critical artifacts present but evidence gaps exist. Gaps are listed explicitly with recommended remediation and target plugin.
- **not-ready.** One or more critical required artifacts absent, or a target-specific blocker (for example, no ISO or NIST conformance claim when assessing Colorado SB 205 safe-harbor).

The skill is framework-agnostic in the sense that it can be loaded by any agent runtime that reads SKILL.md (Hermes Agent, Claude Code, Codex CLI, Cursor, Jules). The runtime invokes the `certification-readiness` plugin's `assess_readiness()` entry point. The authoritative runtime for AIGovOps is [aigovclaw](https://github.com/ZOLAtheCodeX/aigovclaw).

The plugin does not issue an audit opinion. Certification decisions require a qualified auditor or notified body.

## Scope

**In scope.** Readiness assessment against nine target certifications: ISO/IEC 42001:2023 Stage 1, Stage 2, and surveillance audits; EU AI Act Article 43 conformity assessment via internal control (Annex VI) and notified body (Annex VII); Colorado SB 205 Section 6-1-1706(3) safe-harbor rebuttable presumption; NYC Local Law 144 annual re-audit; Singapore MAGF 2e alignment; and UK ATRS publication readiness. The skill reads the MANIFEST.json, artifacts, and citation-summary.md of a bundle produced by `evidence-bundle-packager` and scores each required artifact for presence, evidence strength, and warnings.

**Out of scope.** Audit opinions. Legal opinions. Issuance of certificates. Bundle construction (use `evidence-bundle-packager` upstream). Remediation execution (the plugin names the `target_plugin` that produces missing evidence but does not run it). Fitness-for-purpose assessment of the underlying AI systems themselves (use `aisia-runner` and `high-risk-classifier` upstream).

**Operating assumption.** An evidence bundle has already been produced. The organization has selected one target certification for this assessment. The bundle was signed or at least packed deterministically.

## Framework Reference

The readiness verdict is grounded in published framework triggers, not heuristics.

**ISO/IEC 42001:2023, Clause 9.2 (Internal audit).** The standard requires the organization to conduct internal audits at planned intervals to provide information on whether the AIMS conforms to its own requirements and to the standard, and whether it is effectively implemented and maintained. The certification-readiness skill treats internal-audit-plan as a required artifact for every ISO target, and for Stage 2 it requires at least one completed cycle.

**ISO/IEC 42001:2023, Clause 9.3 (Management review).** Top management must review the AIMS at planned intervals. The skill requires management-review-package across every ISO target because the review is the gate that certifies the organization's own confidence in the AIMS before inviting an auditor.

**ISO/IEC 42001:2023, Clause 10.1 (Continual improvement).** For surveillance audits, the skill requires evidence of continual improvement cycles: updated risk register, management review after the Stage 2 certificate, and closed nonconformities.

**EU AI Act (Regulation (EU) 2024/1689), Article 43 (Conformity assessment procedures).** Article 43 prescribes two conformity assessment routes for high-risk AI systems: internal control (Annex VI, for systems covered by Article 6(2)) and notified body (Annex VII, for systems covered by Article 6(1)). The skill offers a separate target for each.

**EU AI Act, Annex VI (Internal control).** Procedurally, internal control requires the provider to maintain the technical documentation set per Article 11 and Annex IV, the QMS per Article 17, and the post-market monitoring per Article 72. The skill's `eu-ai-act-internal-control` target verifies that each of these artifact types is present in the bundle.

**EU AI Act, Annex VII (Notified body).** For systems under Annex VII, notified-body involvement adds supplier and vendor assessment and post-market monitoring to the internal-control set. The `eu-ai-act-notified-body` target adds those requirements.

**Colorado SB 205, Section 6-1-1706(3).** Colorado SB 205 names conformance with ISO/IEC 42001 or NIST AI RMF as a rebuttable presumption of reasonable care for a deployer defending against an attorney-general action. The `colorado-sb205-safe-harbor` target specifically checks this: either the colorado-compliance-record declares actor-conformance with ISO 42001 or NIST AI RMF, or the high-risk-classifier's sb205_assessment flags section_6_1_1706_3_applies.

**Colorado SB 205, Section 6-1-1706(4).** The affirmative-defense-on-cure pathway requires the same conformance posture plus evidence of cure.

**NYC LL144 Final Rule, Section 5-301 and 5-304.** The annual re-audit requirement drives the `nyc-ll144-annual-audit` target. If the next_audit_due_by date is less than 30 days out, the skill flags an imminent re-audit as a condition.

**Source links.**

- ISO/IEC 42001:2023 clauses are purchased from the ISO store; no open URL.
- NIST AI RMF 1.0: https://www.nist.gov/itl/ai-risk-management-framework.
- EU AI Act: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ%3AL_202401689.
- Colorado SB 205: https://leg.colorado.gov/bills/sb24-205.
- NYC LL144 Final Rule: https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/.

## Operationalizable Controls

The plugin's output maps to specific clauses, controls, subcategories, and articles. See `operationalization-map.md` in this directory for the full mapping.

| Readiness verdict driver | ISO/IEC 42001:2023 | EU AI Act | Colorado SB 205 | NYC LL144 |
|---|---|---|---|---|
| Required artifact presence check | Clauses 6.1.2, 6.1.3, 7.5.1, 7.5.3 | Articles 9, 10, 11, 12, 17 | Sections 6-1-1703(2), 6-1-1706(3) | Final Rule Section 5-301 |
| Evidence strength floor | Clause 9.2 | Article 43 | Section 6-1-1706(3) | Section 5-303 |
| Crosswalk citation coverage | Clauses 4.2, 4.3 | Article 11, Annex IV | Section 6-1-1706(3) | Section 5-302 |
| Blocker or gap escalation | Clause 10.1, 10.2 | Article 43 | Section 6-1-1706(3) | Section 5-304 |
| Remediation routing | Clause 6.2 | Article 17 | Section 6-1-1703(3) | Section 5-301 |

## Output Standards

Every plugin output carries:

- `timestamp` (ISO 8601 UTC, seconds precision, suffix `Z`).
- `agent_signature` (`certification-readiness/0.1.0`).
- `target_certification` (the enum input).
- `bundle_id_ref` (the bundle_id read from MANIFEST.json).
- `readiness_level` (the graduated verdict).
- `evidence_completeness`, `crosswalk_coverage`, `conditions`, `gaps`, `blockers`, `remediations`, `citations`, `warnings`, `summary`, `reviewed_by`.

The rendered Markdown carries a legal disclaimer callout:

> This readiness report is informational. It does not constitute an audit opinion or legal advice. Certification decisions require a qualified auditor or notified body.

The rendered CSV has one row per gap, blocker, condition, and remediation with a `row_kind` column and columns for owner_role, target_plugin, and suggested_deadline.

## Limitations

1. The plugin does not verify signatures on the bundle; it trusts that `evidence-bundle-packager.verify_bundle()` has been run upstream. Combine the two plugins when the bundle origin is not directly controlled.
2. Evidence-strength scoring is coarse (four levels). Strong signals of strength (complete FRIA coverage, every Annex A control mapped, every NIST subcategory with a measurement) are not separable from merely "adequate" signals at this version.
3. The Colorado SB 205 safe-harbor check is rebuttable. The plugin cannot assess whether a specific Colorado Attorney General action would be successfully defeated, only whether the statutory conformance claim is present in the bundle.
4. The plugin does not generate missing evidence. Remediation entries name the target plugin; the operator runs it.
5. Every substantive determination is grounded in artifact data. The plugin never hallucinates remediation language; unmapped gaps fall back to a "requires practitioner judgment" escalation string.
