---
name: gpai-obligations
version: 0.1.0
description: >
  General-purpose AI (GPAI) obligations skill operationalizing EU AI Act
  Articles 51 to 55 and the related Annexes XI and XIII. Distinguishes
  the universal Article 53 obligations that attach to every GPAI provider
  from the additional Article 55 obligations that attach when a model has
  systemic risk under Article 51. Wires the Article 54 authorised-
  representative check for non-EU providers and emits a downstream-
  integrator posture for organisations integrating an upstream GPAI without
  meeting the substantial-modification re-classification threshold of
  Article 25(1)(c). Composes with incident-reporting (Article 55(1)(c)
  serious-incident filing) and supplier-vendor-assessor (substantial-
  modification analysis).
frameworks:
  - EU AI Act (Regulation (EU) 2024/1689)
  - ISO/IEC 42001:2023
  - NIST AI RMF 1.0
tags:
  - ai-governance
  - eu-ai-act
  - gpai
  - general-purpose-ai
  - systemic-risk
  - foundation-models
  - copyright
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the EU AI Act's general-purpose AI (GPAI) regime: Articles 51 to 55 plus Annexes XI and XIII. GPAI is increasingly the upstream of every organisation's AI stack. Most enterprises are downstream integrators of a GPAI rather than providers of one, which makes the distinction between the universal Article 53 obligations and the systemic-risk-only Article 55 obligations load-bearing for compliance scoping.

The skill pairs with the [`gpai-obligations-tracker`](../../plugins/gpai-obligations-tracker/) plugin. The plugin classifies systemic-risk status under Article 51 (compute threshold or Commission designation), evaluates Article 53 universal obligations against the references the practitioner supplies, runs the Article 54 authorised-representative check for non-EU providers, and emits Article 55 obligations only when systemic risk applies.

## Scope

**In scope.**

- Article 51 GPAI systemic-risk classification (compute presumption at 10^25 FLOPs, Commission designation under Article 52, Annex XIII criteria).
- Article 52 procedural notification to the Commission within two weeks of meeting the threshold or receiving designation.
- Article 53 universal obligations for every GPAI provider: technical documentation per Annex XI, downstream-integrator documentation, copyright compliance policy (with Article 4(3) of Directive (EU) 2019/790 reservation of rights), and training-data summary per Commission template.
- Article 54 authorised-representative obligation for non-EU GPAI providers placing models on the EU market.
- Article 55 systemic-risk additional obligations: state-of-the-art model evaluation with adversarial testing, systemic-risk assessment and mitigation at Union level, serious-incident tracking and reporting to the AI Office, cybersecurity protection for the model and its physical infrastructure, and Article 55(2) AI Office Codes of Practice (compliance presumption pathway).
- Downstream-integrator posture for organisations consuming an upstream GPAI without substantial modification under Article 25(1)(c).

**Out of scope.**

- Substantial-modification re-classification under Article 25(1)(c). The skill flags the question and refers to [`supplier-vendor-assessor`](../supplier-vendor/SKILL.md).
- Legal adequacy review of a copyright policy or training-data summary. The skill records that a reference is present; counsel reviews the substance.
- Adequacy review of model evaluations. State-of-the-art is a moving target; the skill records the reference and surfaces the obligation.
- Estimation of `training_compute_flops` from architecture. The skill refuses to guess; unknown compute returns `requires-assessment`.
- Transmission of serious-incident notifications to the AI Office. The [`incident-reporting`](../incident-reporting/SKILL.md) skill prepares deadline-aware drafts; filing is operational.

**Operating assumption.** The user organisation has identified that it provides or integrates a GPAI model and needs to determine which obligations attach.

## Framework Reference

**Authoritative sources.**

- EU AI Act, Regulation (EU) 2024/1689: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689. Articles 51 (systemic-risk classification), 52 (designation procedure), 53 (universal GPAI provider obligations), 54 (authorised representatives for non-EU providers), and 55 (systemic-risk additional obligations). Annex XI (technical documentation content), Annex XIII (systemic-risk classification criteria).
- Directive (EU) 2019/790 on Copyright in the Digital Single Market, Article 4(3) (text and data mining reservation of rights), referenced by Article 53(1)(c).
- AI Office Codes of Practice (Article 55(2)) once published. Adherence creates a rebuttable presumption of compliance with Article 55(1) until a harmonised standard is published.

**Article 51 systemic-risk pathways.**

| Pathway | Trigger | Result |
|---|---|---|
| Compute presumption | Cumulative training compute > 10^25 FLOPs | `presumed-systemic-risk` |
| Commission designation | Decision per Annex XIII criteria | `designated-systemic-risk` |
| Below threshold | Compute < 10^25 FLOPs and no designation | `not-systemic-risk` (with confirmation that no other Annex XIII criterion applies) |
| Unknown compute | Value missing or non-numeric | `requires-assessment` |

## Operationalizable Controls

The skill operationalizes one Tier 1 capability: GPAI obligations triage. It composes with three siblings.

**Tier 1: GPAI obligations triage.**

- Input: model description (including training compute), provider role, Article 53 documentation references, optional systemic-risk artifacts (model evaluation, adversarial testing, risk assessment, cybersecurity measures, incidents log), optional code-of-practice status.
- Processing: Article 51 classification; Article 53 universal-obligation evaluation; Article 54 authorised-representative check; Article 55 systemic-risk obligation evaluation (only when applicable); downstream-integrator posture.
- Output: per-obligation status with citation, top-level systemic-risk status, summary counts, register-level warnings for missing references.
- Plugin: `assess_gpai_obligations()`, `render_markdown()`, `render_csv()`.

**Composition with serious-incident filing.** When systemic-risk applies, Article 55(1)(c) requires tracking and reporting of serious incidents to the AI Office. The [`incident-reporting`](../incident-reporting/SKILL.md) skill provides the deadline-aware filing pathway under Article 73. The GPAI tracker records that the incidents log exists; the incident-reporting plugin computes the filing deadline when an incident occurs.

**Composition with supplier and vendor governance.** A downstream integrator that substantially modifies an upstream GPAI may be re-classified as a provider under Article 25(1)(c). The substantial-modification analysis is the responsibility of [`supplier-vendor-assessor`](../supplier-vendor/SKILL.md). The GPAI tracker emits a posture pointing to that plugin rather than making the legal call.

**Composition with cross-framework crosswalk.** Several GPAI obligations partially map to ISO/IEC 42001:2023 controls. Article 53(1)(a) technical documentation maps to Clause 7.5 + A.6.2.7 (satisfies, high). Article 53(1)(d) training-data summary maps partially to A.7.2 + A.7.5. Article 55(1)(a) model evaluation and adversarial testing maps partially to A.6.2.4 plus NIST MEASURE 2.5 and 2.7. Article 55(1)(c) serious-incident tracking maps partially to ISO Clause 10.2. Article 53(1)(c) copyright policy has no ISO 42001 equivalent; it is an EU-specific IP obligation outside ISO scope.

See [`operationalization-map.md`](operationalization-map.md) for the per-article mapping.

## Output Standards

All outputs carry citations in [STYLE.md](../../STYLE.md) format:

- `EU AI Act, Article 51, Paragraph <n>` and `EU AI Act, Article 51, Paragraph 1, Point (a)` for the compute pathway.
- `EU AI Act, Article 52` for designation references.
- `EU AI Act, Article 53, Paragraph 1, Point (a)` through `(d)` for the four universal obligations.
- `EU AI Act, Article 54, Paragraph 1` for the authorised-representative obligation.
- `EU AI Act, Article 55, Paragraph 1, Point (a)` through `(d)` and `Article 55, Paragraph 2` for systemic-risk obligations and the Code of Practice presumption.
- `EU AI Act, Annex XI` referenced by Article 53(1)(a).
- `EU AI Act, Annex XIII` referenced by Article 51 systemic-risk criteria.

No em-dashes. No emojis. No hedging. Every per-obligation row carries a status and a citation. Missing inputs produce explicit warnings rather than silent gap-filling.

## Limitations

1. **No URL verification.** A reference is `present` when the input string is non-empty. The plugin does not fetch, parse, or validate the referenced document. Practitioner is responsible for ensuring the referenced artifact exists and is current.
2. **No compute estimation.** The plugin refuses to estimate `training_compute_flops` from architecture or parameter count. Unknown compute returns `requires-assessment`.
3. **No legal adequacy review.** The plugin does not adjudicate whether a copyright policy meets Article 53(1)(c), whether a training-data summary meets the Commission template, or whether evaluations are state-of-the-art.
4. **Downstream-integrator scope is narrow.** Substantial-modification analysis under Article 25(1)(c) is out of scope. The plugin emits a posture pointing to `supplier-vendor-assessor`.
5. **Codes of Practice are dynamic.** The Article 55(2) presumption depends on AI Office-convened Codes of Practice that are still emerging. The plugin echoes the input enum and notes the presumption pathway; the practitioner confirms which Code is in scope and which sections were signed.
