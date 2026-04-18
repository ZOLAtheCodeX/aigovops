---
name: nyc-ll144
version: 0.1.0
description: >
  NYC Local Law 144 of 2021 governance skill. Operationalizes the
  annual independent bias audit, public-disclosure, and
  candidate-notice requirements for Automated Employment Decision
  Tools (AEDTs) used for NYC employment decisions, together with the
  implementing Department of Consumer and Worker Protection (DCWP)
  Final Rule at 6 RCNY Chapter 5, Subchapter T, Sections 5-300
  through 5-304. Scope validated against the published DCWP rule
  text on 2026-04-18.
frameworks:
  - NYC Local Law 144 of 2021
  - NYC DCWP AEDT Rules (6 RCNY, Chapter 5, Subchapter T)
tags:
  - ai-governance
  - nyc-ll144
  - bias-audit
  - employment-ai
  - aedt
  - disparate-impact
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes New York City Local Law 144 of 2021 (LL144) and the implementing Department of Consumer and Worker Protection (DCWP) Final Rule for organizations that use Automated Employment Decision Tools (AEDTs) to make employment decisions for NYC candidates or employees. LL144 took effect on 5 July 2023. Enforcement is by DCWP with civil penalties for each day of non-compliance. The law is narrow in subject but first-in-kind in the United States: it is the first enforceable municipal bias-audit mandate for hiring AI.

The skill pairs with the `nyc-ll144-audit-packager` plugin, which packages independent-auditor results into the public-disclosure bundle and candidate-notice checklist required by the DCWP Final Rule. The skill does not replace the independent auditor; under DCWP Section 5-301 the audit itself must be performed by an independent auditor against a defined candidate-pool dataset. The skill and plugin together reduce the operational cost of turning that audit into a compliant public posting and candidate notification.

## Scope

**In scope.** NYC Local Law 144 of 2021 and 6 RCNY Chapter 5, Subchapter T (DCWP AEDT Rules) as published, including:

- Applicability of the AEDT definition in DCWP Section 5-300 (substantially assists or replaces discretionary employment decisions, used for NYC candidates or NYC employees).
- The bias-audit requirement in Section 5-301 (selection-rate and impact-ratio calculations per required demographic categories, including intersectional race-by-sex breakdown).
- The annual re-audit cadence (audit_date + 365 days).
- The public-disclosure requirement in Section 5-304 (date of most recent audit, selection rates, impact ratios, distribution comparison, auditor identity).
- The candidate-notice requirement in Section 5-303 (AEDT-use notice, job-qualifications notice, data-type-source-retention information, 10 business days minimum notice).
- The exemption conditions and recordkeeping cross-references in Section 5-302.

**Out of scope.** This skill does not provide:

- Legal advice. "Substantially assists" determinations, role characterization (employer vs. employment agency vs. vendor), and NYC-use determinations require qualified New York employment counsel.
- The bias audit itself. Section 5-301 requires an independent auditor; the skill packages auditor output, it does not compute impact ratios from raw candidate data.
- Coverage of New York State labor law, EEOC Title VII federal obligations, or other state or federal civil-rights regimes that may apply alongside LL144. The skill is LL144-specific.
- Coverage of LL144 amendments or DCWP rule revisions after the validation date in the frontmatter. The `framework-drift` playbook governs refresh cadence.

**Operating assumption.** The user organization either uses AEDTs for NYC employment decisions or is evaluating tools that may fall within scope. Organizations with no NYC employment footprint get crosswalk-only utility (LL144 language for reference and for responding to NYC counterparties).

## Framework Reference

**Authoritative sources.**

- NYC Local Law 144 of 2021 (the enabling law): https://legistar.council.nyc.gov/LegislationDetail.aspx?ID=4344524.
- DCWP Final Rule, Automated Employment Decision Tools, codified at 6 RCNY Chapter 5, Subchapter T, Sections 5-300 through 5-304: https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/.
- DCWP AEDT enforcement page and public FAQ: https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page.

**Structure.**

- Section 5-300: Definitions, including AEDT, substantially assists, employer, employment agency, independent auditor, candidate for employment.
- Section 5-301: Bias audit requirements. Selection rates and impact ratios per required categories; intersectional breakdown required.
- Section 5-302: Prohibition on using an AEDT without a current bias audit. Annual cadence.
- Section 5-303: Notice to candidates and employees. AEDT-use notice and job-qualifications notice at least 10 business days before use; data-type-source-retention information on written request.
- Section 5-304: Public disclosure of audit results. Summary of the most recent audit, auditor identity, date, distribution comparison.

**Enforcement.** DCWP enforces. Civil penalty per violation per day. Each use of an AEDT without a current bias audit is a separate violation. The effective date is 5 July 2023; enforcement began the same day.

**Required categories.** DCWP Final Rule Section 5-301 requires selection rates and impact ratios across:

- Race and ethnicity per the EEOC categories: Hispanic or Latino; White, Black or African American, Native Hawaiian or Pacific Islander, Asian, Native American or Alaska Native, Two or More Races (each as Not Hispanic or Latino).
- Sex: Male, Female.
- Intersectional: race and ethnicity by sex.

**Related frameworks and cross-references.**

- EEOC Uniform Guidelines on Employee Selection Procedures (29 CFR Part 1607): the four-fifths rule that LL144 operationalizes in impact-ratio form.
- Colorado AI Act (SB 205): a broader-scope analogue; covers algorithmic consumer decisions in any domain, not just employment. Listed as secondary-priority in `docs/jurisdiction-scope.md`.
- EU AI Act Annex III, Point 4 (employment, workers management): classifies AEDT-equivalent systems as high-risk, triggering the Article 9-15 obligations. An AEDT compliant with LL144 will satisfy the selection-rate disclosure piece of EU Annex III, Point 4 but not the full Article 9-15 obligations.
- ISO/IEC 42001:2023, Annex A, Control A.6.2.4 (data for AI systems) and Clause 6.1.3 (AI risk treatment): the management-system controls that produce the inputs to an LL144 audit.

## Operationalizable Controls

One Tier 1 operationalization. The law is narrow and the plugin surface is correspondingly narrow.

### T1.1 Bias-audit packaging and public disclosure (Sections 5-301, 5-303, 5-304)

Class: A. Artifact: `bias-audit-package` with NYC LL144 citations. Leverage: H. Consumer: `plugins/nyc-ll144-audit-packager`.

**Requirement summary.** An employer or employment agency that uses an AEDT for a NYC employment decision must:

1. Ensure a bias audit of the AEDT has been conducted within the preceding year by an independent auditor per Section 5-301.
2. Publish on its public-facing careers site (or equivalent) the summary of audit results per Section 5-304, including the date of the most recent audit, selection rates and impact ratios per required category, distribution comparison, and auditor identity.
3. Notify each candidate or employee at least 10 business days before use of the AEDT per Section 5-303, covering AEDT use, the job qualifications and characteristics the AEDT considers, and (on written request) the type and source of data and the retention policy.

**Plugin cross-reference.** The `nyc-ll144-audit-packager` plugin consumes the output of an independent auditor (selection rates per category, auditor identity, audit date, distribution comparison) and produces:

- The `public_disclosure_bundle`, ready to render as a posting.
- The `candidate_notices` list, ready to convert into the three required notice surfaces.
- `next_audit_due_by` at audit_date + 365 days.

The plugin emits warnings when required audit content is missing (auditor identity, intersectional breakdown, distribution comparison). It raises `ValueError` on structural gaps (missing required top-level field, invalid role).

**Auditor acceptance criteria.**

- Audit date present and no more than 365 days before the date of use.
- Auditor identity present and the auditor meets the Section 5-300 independence criterion.
- Selection rates present for race and ethnicity, sex, and intersectional categories.
- Impact ratios computed against the most-selected group per category.
- Distribution comparison present (historical baseline or test-pool).
- Public disclosure posted on the employer's or employment agency's careers site.
- Three candidate notices drafted, posted, or delivered per Section 5-303.

### Tier 2

LL144 is narrow enough that no Tier 2 beyond the above is in scope. Peripheral considerations that may come up in practice:

1. **Exemption analysis under Section 5-300.** The "substantially assists" threshold is a legal question. Counsel determination is required; the plugin records the caller's answer and does not attempt to infer it.
2. **Multi-tool architectures.** Where an AEDT is a component in a larger hiring pipeline, whether the pipeline as a whole is an AEDT is a judgment call. Skill documents the question; does not answer it.

## Output Standards

Outputs produced under this skill must meet the certification-grade quality bar in [STYLE.md](../../STYLE.md). Specifically:

- Citations match one of: `NYC LL144`, `NYC LL144 Final Rule, Section <n>`, `NYC DCWP AEDT Rules, Subchapter T`.
- No em-dashes (U+2014).
- No emojis.
- No hedging phrases (see STYLE.md for the prohibited list).
- Public disclosure language is definite, not conditional. Where a determination requires human judgment (applicability, substantially-assists, independent-auditor qualification), the output states `Requires human determination.` rather than hedging.

## Limitations

- The skill validation date in the frontmatter is the date the published DCWP Final Rule text was checked. Sub-rule guidance, FAQ updates, or rule amendments after that date are not reflected. The `framework-drift` playbook governs refresh cadence; this skill is tagged high-maintenance because NYC AEDT guidance continues to evolve.
- The skill does not conduct the bias audit. That is the independent auditor's role under Section 5-301. The plugin refuses to invent impact ratios from raw candidate data; it packages results produced by the auditor.
- Federal EEOC obligations, New York State Human Rights Law obligations, and related civil-rights regimes are out of scope. An AEDT that satisfies LL144 may still violate Title VII or state law; LL144 compliance is necessary, not sufficient.
- The skill does not track enforcement actions, settlements, or DCWP penalty assessments. Operational intelligence about DCWP enforcement posture is a separate information product not captured here.
