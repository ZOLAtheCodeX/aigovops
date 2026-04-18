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
| EU | EU AI Act (Regulation (EU) 2024/1689); Articles 5, 6, 50; Annex I; Annex III; Articles 26-27 | Directly applicable law for any AI system within EU territorial scope. Extraterritorial reach. |
| International | ISO/IEC 42001:2023 | Certification-grade AI management system standard. Referenced by every other jurisdiction-specific framework as the operational baseline. |

## Secondary jurisdictions (next-tier coverage)

These are on the roadmap once primary coverage is stable. Each becomes its own plugin-and-skill pair when sponsor demand or grant scope supports the build.

| Jurisdiction | Instrument | Why secondary |
|---|---|---|
| UK | UK AI Safety Institute evaluations framework; UK Algorithmic Transparency Recording Standard (ATRS); ICO AI auditing framework | Post-Brexit divergence from EU. Influential through AI Safety Institute; non-binding but referenced. |
| USA state: New York City | Local Law 144 (bias audit) | Enforceable. First US bias-audit requirement. Narrow scope (employment decisions). |
| USA state: Colorado | Colorado AI Act (SB 205) | Enforceable. First US comprehensive AI consumer protection law. |
| Canada | Artificial Intelligence and Data Act (AIDA) | Legislative progress uncertain; framework language already influential. |
| Singapore | Model AI Governance Framework (MAS / IMDA) | Influential in APAC. Referenced by regional regulators and multinational compliance programs. |

## Tertiary and derivative

Not built in. Practitioners working in these contexts can map their local requirements onto AIGovOps artifact fields without AIGovOps shipping dedicated support.

Examples: Japan METI AI governance guidelines, Australia AI Ethics Framework, Korea AI Act (drafting), Brazil LGPD applied to AI, Council of Europe Convention on AI, OECD AI Principles, G7 Hiroshima AI Process Code of Conduct.

Reason: these are either subsumed by the primary frameworks (OECD principles underlie almost every other framework), apply narrowly to specific actor types, or are still in drafting with volatile text.

If one of these jumps in enforceability, it can graduate to secondary.

## How this shapes plugin authoring

- Every plugin accepting a `framework` parameter supports at minimum `iso42001`, `nist`, and `dual`. Plugins that operationalize EU-specific text also accept `eu-ai-act`.
- New framework parameters (UK, Singapore, Colorado, NYC LL144, and similar) require a sponsor or grant before they ship. No speculative jurisdiction expansion.
- Citations from tertiary jurisdictions may appear in plugin output `citations` lists where a practitioner has added them to the input, but the plugin itself does not author them.

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
