# Jurisdiction scope

**Status:** locked-in 2026-04-18. This document governs which jurisdictions AIGovOps operationalizes directly and which it treats as derivative.

## The rule

AIGovOps operationalizes frameworks that meet at least one of these criteria:

1. **Controlling regulation.** An enforceable law in a jurisdiction where AI systems face real compliance risk.
2. **Influential framework.** A non-binding framework whose text is referenced by controlling regulations in other jurisdictions or by the major certification bodies.

Jurisdictions that do not meet either criterion are treated as **derivative**. Practitioners working in those jurisdictions can map their local requirements onto AIGovOps artifacts by reading the plugin outputs, but AIGovOps does not ship a dedicated skill or plugin for every local regulator.

## Primary jurisdictions

These receive first-class skills, plugins, and eval coverage. They are the default targets for every plugin's `framework` parameter.

| Jurisdiction | Instrument | Rationale |
|---|---|---|
| USA | NIST AI RMF 1.0 + AI 600-1 Generative AI Profile | Most-referenced voluntary AI governance framework globally. Federal contractor baseline emerging. |
| EU | EU AI Act (Regulation (EU) 2024/1689); Articles 5, 6, 50; Annex I; Annex III; Articles 26-27; Articles 51-55 (GPAI obligations) | Directly applicable law for any AI system within EU territorial scope. Extraterritorial reach. GPAI obligations covered by `gpai-obligations-tracker` plugin and `gpai-obligations` skill. |
| International | ISO/IEC 42001:2023 | Certification-grade AI management system standard. Referenced by every other jurisdiction-specific framework as the operational baseline. |

## Secondary jurisdictions (next-tier coverage)

These are on the roadmap once primary coverage is stable. Each becomes its own plugin-and-skill pair when sponsor demand or grant scope supports the build.

| Jurisdiction | Instrument | Why secondary |
|---|---|---|
| UK | UK AI Safety Institute evaluations framework; UK Algorithmic Transparency Recording Standard (ATRS, shipping, plugin `uk-atrs-recorder`); ICO AI auditing framework | Post-Brexit divergence from EU. Influential through AI Safety Institute; non-binding but referenced. |
| USA state: New York City | Local Law 144 (bias audit, shipping, plugin `nyc-ll144-audit-packager`) | Enforceable. First US bias-audit requirement. Narrow scope (employment decisions). |
| USA state: California | CPPA ADMT regulations, CCPA/CPRA, SB 942, AB 2013, AB 1008, SB 1001, AB 1836 (primer skill `california-ai`; no plugin yet, California is a constellation rather than a single controlling instrument) | Enforceable in parts; large market. The primer skill navigates which instrument applies to which AI system. |
| USA state: Colorado | Colorado AI Act (SB 205, shipping, plugin `colorado-ai-act-compliance`) | Enforceable. First US comprehensive AI consumer protection law. |
| Canada | AIDA (Bill C-27, Part 3, drafting), PIPEDA (in force), OSFI Guideline E-23 (federally-regulated financial institutions), Treasury Board Directive on Automated Decision-Making (federal government), Quebec Law 25, Canada Voluntary AI Code 2023 (primer skill `canada-aida`; no plugin yet, Canada is a layered constellation and AIDA is still drafting) | Enforceable in parts; AIDA drafting-volatile. The primer skill navigates which instrument applies to which AI system. |
| Singapore | Model AI Governance Framework (IMDA/PDPC MAGF 2e), MAS FEAT Principles, AI Verify (shipping, plugin `singapore-magf-assessor` + skill `singapore-ai-governance`) | Influential in APAC. Referenced by regional regulators and multinational compliance programs. |

## Tertiary and derivative

Not built in. Practitioners working in these contexts can map their local requirements onto AIGovOps artifact fields without AIGovOps shipping dedicated support.

Examples: Japan METI AI governance guidelines, Australia AI Ethics Framework, Korea AI Act (drafting), Brazil LGPD applied to AI, Council of Europe Convention on AI, OECD AI Principles, G7 Hiroshima AI Process Code of Conduct.

Reason: these are either subsumed by the primary frameworks (OECD principles underlie almost every other framework), apply narrowly to specific actor types, or are still in drafting with volatile text.

If one of these jumps in enforceability, it can graduate to secondary.

## How this shapes plugin authoring

- Every plugin accepting a `framework` parameter supports at minimum `iso42001`, `nist`, and `dual`. Plugins that operationalize EU-specific text also accept `eu-ai-act`.
- New framework parameters (UK, Singapore, Colorado, NYC LL144, and similar) require a sponsor or grant before they ship. No speculative jurisdiction expansion.
- Citations from tertiary jurisdictions may appear in plugin output `citations` lists where a practitioner has added them to the input, but the plugin itself does not author them.
- The cross-framework crosswalk at `plugins/crosswalk-matrix-builder/` is the canonical surface for auditors, grant reviewers, and sponsors to verify which frameworks a given control satisfies. The crosswalk holds 434 cited mapping rows across the 14 framework identifiers listed in `plugins/crosswalk-matrix-builder/data/frameworks.yaml`, each row carrying a relationship label, confidence rating, and at least one citation source. Secondary-jurisdiction expansion is coherent only because the crosswalk is the backbone: one implementation pass against ISO 42001 and NIST AI RMF generates auditable coverage claims against EU AI Act Chapter III, UK ATRS, Colorado SB 205, NYC LL144, and the 7 California instruments, so AIGovOps does not need to ship per-jurisdiction duplicate documentation for each secondary overlay.

## How this shapes grant and sponsorship targeting

- Grant applications and sponsored-development targets prioritize the primary three jurisdictions before expanding.
- Secondary expansion is sponsor-driven: an organization funds the specific overlay it needs. Code stays MIT.
- Tertiary expansion is derivative by default and only graduates on external pressure (for example, Korea AI Act enters force; Canada AIDA passes).

## Revision process

This document is revised when any of the following occur:

1. A primary instrument is amended in a material way (EU AI Act delegated act, NIST AI RMF 2.0, ISO 42001 revision).
2. A secondary instrument becomes enforceable or gains citation in primary instruments.
3. A tertiary instrument graduates to secondary based on external pressure.
4. A new jurisdiction ships a framework meeting the criteria above.

Revisions are committed with a tracking issue explaining the trigger.

Last updated: 2026-04-18.
