---
name: eu-conformity-assessment
version: 0.1.0
description: >
  EU AI Act conformity assessment skill. The procedure and declaration
  layer on top of an evidence bundle. Operationalizes Article 43
  (procedure selection between internal control and notified body),
  Annex VI (internal control content), Annex VII (notified body content),
  Article 47 (EU declaration of conformity template), Article 48 (CE
  marking), and Article 49 (EU database registration). Verifies the nine
  Annex IV technical-documentation categories against bundle artifact
  types, attests Article 17 QMS coverage via management-review and
  internal-audit artifacts, and emits a draft declaration the provider
  completes and signs. The skill never issues a certificate.
frameworks:
  - EU AI Act (Regulation (EU) 2024/1689)
  - ISO/IEC 42001:2023
tags:
  - ai-governance
  - eu-ai-act
  - conformity-assessment
  - ce-marking
  - declaration-of-conformity
  - eu-database-registration
  - consumer-plugin
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill closes the EU AI Act high-risk lifecycle. The provider has classified the system, populated the data register, completed the AISIA / FRIA, run risk and quality management, packaged the evidence bundle, and now must select the conformity assessment procedure under Article 43, populate the Annex IV technical documentation, draft the Article 47 declaration of conformity, affix the Article 48 CE marking, and register the system under Article 49.

The skill loads the `eu-conformity-assessor` plugin. The plugin's `assess_conformity_procedure()` entry point reads the system description, provider identity, requested procedure, and the evidence bundle, then emits a structured assessment with one block per regulatory obligation: procedure applicability, Annex IV completeness, QMS attestation, notified-body check (when applicable), declaration of conformity draft, CE marking check, and registration check.

Every determination cites a specific EU AI Act Article and Paragraph. The plugin does not issue a certificate. It does not sign the declaration. It does not affix the CE marking. It structures the procedure for the provider and surfaces every gap as a warning. Conformity decisions remain with the provider (Article 47 self-declaration) or with the notified body (Annex VII certificate).

This skill is parallel to `certification-readiness`. The two have different consumers. `certification-readiness` is general and supports nine target certifications across multiple jurisdictions; `eu-conformity-assessment` is EU-specific and produces the regulatory artifacts the EU AI Act prescribes (declaration of conformity, CE marking record, database registration record).

## Scope

**In scope.** Procedure selection per Article 43, Annex IV documentation completeness check (nine categories) against an evidence bundle, Article 17 QMS attestation via management-review and internal-audit artifact presence, notified body record check for Annex VII procedures, Article 47 EU declaration of conformity template generation populated from inputs, Article 48 CE marking location and notified-body identification check, Article 49 EU database registration check with restricted visibility flag for Annex III point 6 (law enforcement), Article 22 authorised representative check for non-EU providers, Article 43(4) surveillance / re-assessment comparison when a previous assessment reference is supplied.

**Out of scope.** Issuance of EU type-examination certificates (notified body responsibility per Annex VII). Signature on the declaration of conformity (provider responsibility per Article 47). Physical affixing of the CE marking (provider responsibility per Article 48). Submission to the EU database (provider responsibility per Article 49). Audit of the notified body itself. Verification that harmonised standards cited by the provider are in fact published in the Official Journal under Article 40.

**Operating assumption.** The provider has produced an evidence bundle via `evidence-bundle-packager`. The system has been classified by `high-risk-classifier`. The Annex III category is known. The risk tier is known. The provider has (or has appointed) an authorised representative if non-EU.

## Framework Reference

The skill is grounded in the published EU AI Act text.

**EU AI Act, Article 43, Paragraph 1.** Providers of high-risk AI systems listed in Annex III, Point 1 (biometric systems) must follow the conformity assessment procedure under Annex VII (notified body), unless they have applied harmonised standards covering the requirements set out in Chapter III, Section 2, in which case Annex VI (internal control) is permitted.

**EU AI Act, Article 43, Paragraph 2.** Providers of high-risk AI systems listed in Annex III, Points 2 to 8 follow the conformity assessment procedure under Annex VI (internal control). They may opt voluntarily to follow Annex VII; the skill flags the voluntary case as a warning so the provider's decision is documented.

**EU AI Act, Article 43, Paragraph 3.** When a high-risk AI system is a safety component of a product covered by the Union harmonisation legislation listed in Annex I (medical devices, machinery, toys, in vitro diagnostics, etc.), the conformity assessment follows that legislation's procedure with the AI Act-specific requirements integrated.

**EU AI Act, Article 43, Paragraph 4.** Substantial modifications to a high-risk AI system trigger a new conformity assessment.

**EU AI Act, Article 17, Paragraph 1.** The provider establishes a quality management system documented in policies, procedures, and instructions covering at least: a strategy for regulatory compliance (Point a), techniques for design and development (Point c), techniques for verification and validation (Point d), data management (Point f), risk management (Point g), post-market monitoring (Point h), and procedures for serious-incident reporting (Point i). The skill checks for the management-review-package and internal-audit-plan artifact types in the bundle as evidence the QMS exists and is being run.

**EU AI Act, Annex IV.** The technical documentation set has nine prescribed content categories. The skill maps each category to the AIGovOps plugin that produces the supporting artifact and verifies the category is satisfied by inspecting the bundle's MANIFEST.json.

**EU AI Act, Annex VI.** Internal control conformity assessment requires the provider to: (1) maintain the technical documentation per Annex IV, (2) operate the QMS per Article 17, (3) examine the AI system itself, and (4) draw up the EU declaration of conformity per Article 47.

**EU AI Act, Annex VII.** EU type-examination by a notified body. The notified body reviews the QMS, the technical documentation, and tests the AI system. The notified body issues an EU type-examination certificate referenced in the declaration of conformity and in the CE marking under Article 48.

**EU AI Act, Article 47, Paragraph 1.** The EU declaration of conformity is drawn up in writing in machine-readable format, signed by the provider, and contains: provider name and address, AI system identity, statement of conformity with the EU AI Act, references to standards applied, references to any notified-body certificate, date of issue, signatory.

**EU AI Act, Article 48.** CE marking is affixed visibly, legibly, and indelibly to the AI system. When physical appending is impossible, the marking is on packaging or accompanying documentation. Paragraph 3 requires the notified body identification number to follow the CE marking when the Annex VII procedure was applied.

**EU AI Act, Article 49, Paragraph 1.** Providers of high-risk AI systems must register the system in the EU database before placing it on the market, except for Annex III, Point 2 (critical infrastructure). Paragraph 2 provides that registration entries are public, except for entries relating to Annex III, Point 6 (law enforcement), which are restricted.

**EU AI Act, Article 22, Paragraph 1.** Providers established outside the Union must, by written mandate, appoint an authorised representative established in the Union before placing the system on the EU market.

**Source.** [EUR-Lex consolidated text of Regulation (EU) 2024/1689](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ%3AL_202401689).

## Operationalizable Controls

The plugin's output maps to specific Articles, Annex points, and ISO 42001 clauses. See `operationalization-map.md` in this directory for the per-Article mapping.

| Output block | EU AI Act provision | ISO/IEC 42001:2023 cross-reference |
|---|---|---|
| Procedure applicability | Article 43, Paragraphs 1, 2, 3 | Clause 9.2 (internal audit) for Annex VI route |
| Annex IV completeness | Annex IV, Points 1 to 7 | Clause 7.5 (documented information), Annex A Control A.6.2.7 |
| QMS attestation | Article 17, Paragraph 1, Points (a) and (i) | Clause 9.2, Clause 9.3 |
| Notified body check | Annex VII | No ISO equivalent (regulatory) |
| Declaration of conformity | Article 47, Paragraphs 1, 2 | No ISO equivalent (regulatory) |
| CE marking | Article 48, Paragraphs 1, 2, 3 | No ISO equivalent (regulatory) |
| Registration | Article 49, Paragraphs 1, 2 | No ISO equivalent (regulatory) |
| Authorised representative | Article 22, Paragraph 1 | No ISO equivalent (regulatory) |

## Output Standards

Every plugin output carries:

- `timestamp` (ISO 8601 UTC, seconds precision, suffix `Z`).
- `agent_signature` (`eu-conformity-assessor/0.1.0`).
- `framework` (fixed string `eu-ai-act`).
- `procedure_selected`, `procedure_applicability`, `annex_iv_completeness`, `qms_attestation`, `notified_body_check` (when applicable), `declaration_of_conformity_draft`, `ce_marking_check`, `registration_check`, `surveillance_check` (when applicable).
- `citations` (top-level), `warnings`, `summary`, `cross_framework_citations` (when enriched), `reviewed_by`.

The rendered Markdown carries a legal disclaimer callout near the top:

> This conformity assessment report is informational. It does not constitute an audit opinion, a notified-body certificate, or legal advice. Conformity determinations require the provider's own declaration (Article 47) and, where applicable, a notified body.

The rendered CSV emits one row per Annex IV category (nine rows when complete) with status, accepted artifact types, recommended producing plugin, and citation.

## Limitations

1. The plugin does not verify that harmonised standards cited by the provider are published in the Official Journal under Article 40. The provider is responsible for citing only standards in force.
2. The plugin does not verify the notified body's accreditation or current authorisation status. The provider verifies notified-body status before engagement.
3. The plugin does not detect substantial modifications under Article 43(4) automatically. The provider must supply `previous_assessment_ref` to trigger surveillance comparison.
4. The plugin does not write to the EU database. It produces the registration record content; the provider submits it.
5. The plugin does not sign the declaration of conformity. The `signatory` field is populated from `reviewed_by` or from `provider_identity.signatory` for provider review; the actual signature is the provider's responsibility.
6. The Annex IV mapping uses the AIGovOps plugin catalogue as the inferred source of the supporting artifact. Providers using non-AIGovOps tooling must manually verify their artifact equivalents satisfy each Annex IV category.
