---
name: ai-system-inventory
version: 0.1.0
description: >
  AI system inventory operationalization skill. Upstream of every other
  AIGovOps plugin. Produces a validated, versioned inventory artifact
  that captures every AI system in the AIMS scope with the fields
  required by ISO/IEC 42001:2023 Clause 4.3 (scope determination),
  Clause 7.5 (documented information), and Annex A Control A.5 (AI
  system identification and impact assessment inputs), NIST AI RMF
  GOVERN 1.6 (AI inventory), EU AI Act Article 11 (technical
  documentation), UK ATRS Section Tool description, and Colorado SB 205
  consequential-decision scoping.
frameworks:
  - ISO/IEC 42001:2023
  - NIST AI RMF 1.0
  - EU AI Act (Regulation (EU) 2024/1689)
  - UK Algorithmic Transparency Recording Standard
  - Colorado Senate Bill 24-205
tags:
  - ai-governance
  - ai-inventory
  - scope-determination
  - documented-information
  - iso42001
  - nist-ai-rmf
  - eu-ai-act
  - lifecycle
  - aims
author: AIGovOps Contributors
license: MIT
---

## Overview

The AI system inventory is the upstream-of-everything artifact in an AI Management System. Every downstream plugin in this catalogue consumes `ai_system_inventory` as an input: the Statement of Applicability generator, the risk register builder, the AISIA runner, the audit log generator, the gap assessment tool, the management-review packager, the internal-audit planner, the metrics collector, the UK ATRS recorder, the Colorado SB 205 compliance record builder, the NYC LL144 audit packager, the Singapore MAGF assessor, the data-register builder, and the high-risk classifier. None of those plugins maintain the inventory. They read it and trust that its contents have been validated.

This skill and its paired `ai-system-inventory-maintainer` plugin close that loop. The plugin validates every inventory entry against required and recommended field sets, tags each system with the regulatory regimes that apply to it, tracks lifecycle state transitions, and diffs new inventory revisions against prior ones so the organization retains version history. The output is an inventory artifact a practicing ISO/IEC 42001 Lead Auditor would accept as audit evidence for Clause 4.3 scope determination and Clause 7.5 documented-information control.

This skill does not assign risk tiers. Risk-tier classification against the EU AI Act Article 5, 6, and Annex taxonomies is the job of the `high-risk-classifier` plugin. The inventory consumes the resulting risk-tier value and supports both EU AI Act vocabulary (`prohibited`, `high-risk-annex-i`, `high-risk-annex-iii`, `limited-risk`, `minimal-risk`, `requires-legal-review`) and ISO-style risk vocabulary (`low`, `limited`, `medium`, `high`), so the same inventory row can be shared between an EU compliance workflow and an ISO 42001 risk register.

## Scope

**In scope.** The organizational AIMS boundary as defined at Clause 4.3 scope determination time. Every AI system in that boundary, captured as a per-system inventory row with required fields for unambiguous identification and recommended fields for downstream artifact generation. Lifecycle states covering the full journey from proposal through decommissioning. Jurisdictional coverage across the primary and secondary jurisdictions defined in `docs/jurisdiction-scope.md` (international, EU, UK, USA federal, USA Colorado, USA NYC, USA California, Canada, Singapore).

**Out of scope.** Discovery of AI systems within the organization. Practitioners must supply the inventory; the plugin does not walk repositories, scan cloud accounts, or crawl vendor lists. Risk-tier assignment. Legal advice on which regulatory regime applies to a specific organization. Verification that linked artifact references (`aisia_ref`, `soa_ref`, `risk_register_ref`) resolve to real files on disk.

**Lifecycle states supported.** `proposed`, `in-development`, `pre-deployment-review`, `deployed`, `under-monitoring`, `deprecated`, `decommissioned`. The `decommissioned` state triggers a register-level warning so downstream plugins update their artifacts accordingly.

## Framework Reference

The inventory is grounded in five framework anchors.

**ISO/IEC 42001:2023.** Clause 4.3 (determining the scope of the AIMS) requires the organization to document the boundary of the management system, which presupposes knowing which AI systems fall inside it. Clause 7.5 (documented information) requires creating, updating, and retaining records in a controlled manner; the inventory is the master record of in-scope AI systems. Annex A Control A.5 (AI system identification and impact assessment) depends on the inventory for the object of every impact assessment.

**NIST AI RMF 1.0.** GOVERN 1.6 calls for maintaining a catalogue of AI systems used or developed by the organization with enough detail to support risk management. The inventory is that catalogue.

**EU AI Act (Regulation (EU) 2024/1689).** Article 11 (technical documentation for high-risk AI systems) requires system identification fields that the inventory captures. For providers and deployers, the inventory is the registry from which technical documentation is extracted.

**UK Algorithmic Transparency Recording Standard.** Section Tool description and Section Owner and contact map directly to inventory fields (system name, owner role, intended use). The inventory is Tier 1 public-facing source material.

**Colorado SB 205.** Section 6-1-1701(3) defines consequential decisions; an inventory that flags which systems operate in consequential-decision domains is the scoping artifact for Colorado developer and deployer obligations.

## Operationalizable Controls

The plugin output maps to specific ISO/IEC 42001:2023 sub-clauses and NIST AI RMF subcategories.

| Output component | ISO/IEC 42001:2023 | NIST AI RMF 1.0 | Notes |
|---|---|---|---|
| Per-system required fields populated | Clause 7.5.1 | GOVERN 1.6 | Creating documented information. |
| Version diff on update | Clause 7.5.2 | GOVERN 1.6 | Updating documented information. Added, modified, removed, unchanged. |
| Retention of prior inventory | Clause 7.5.3 | GOVERN 1.6 | Organization retains the prior JSON for retrieval and audit. |
| Lifecycle state transitions | Clause 6.2 | GOVERN 1.7 | Decommissioning procedures. Triggers downstream updates. |
| Regulatory applicability per system | Clause 4.3 | MAP 1.1 | Context determination by jurisdiction and sector. |
| Cross-framework references | Annex A Control A.2.3 | GOVERN 1.1 | Alignment with other organizational frameworks. |

## Output Standards

**Canonical shape.** Every run produces a dict with `timestamp`, `agent_signature`, `operation`, `reviewed_by`, `systems`, `validation_findings`, `regulatory_applicability_matrix`, `citations`, `warnings`, `summary`, and when `operation='update'`, a `version_diff` block. Field names are stable across versions to support adapter-layer integration with GRC platforms and structured workspace tools.

**Citation formats.** ISO citations use `ISO/IEC 42001:2023, Clause X.X.X` or `ISO/IEC 42001:2023, Annex A, Control A.X.Y`. NIST uses `<FUNCTION> <Subcategory>`. EU AI Act uses `EU AI Act, Article XX` or `EU AI Act, Chapter III` for the high-risk obligation bundle. Colorado uses `Colorado SB 205, Section 6-1-1701(3)`. UK ATRS uses `UK ATRS, Section <name>`. NYC uses `NYC LL144 Final Rule, Section 5-301`. Singapore uses `Singapore MAGF 2e, Pillar <name>` and `MAS FEAT Principles (2018), Principle <name>`. Every citation in output matches `STYLE.md` prefixes; plugin tests enforce this via regex.

**Multi-framework applicability calculation.** For each system the plugin computes an ordered list of applicable frameworks based on the jurisdiction list, risk tier, deployment context, and sector. ISO 42001 applies to every system as the international baseline. NIST AI RMF attaches when jurisdiction contains any `usa-*` value. EU AI Act attaches when jurisdiction contains `eu`, with the specific citation depending on risk tier. Secondary-jurisdiction frameworks (Colorado, NYC, UK, Singapore) attach only when both jurisdiction and context match. Every attachment carries a deterministic rationale.

**Markdown and CSV renderings.** `render_markdown()` produces sections `# AI System Inventory`, `## Summary`, `## Applicable Citations`, `## Applicability matrix`, `## Validation findings`, `## Per-system details`, and when present `## Version diff` and `## Warnings`. `render_csv()` produces a one-row-per-system table suitable for spreadsheet ingestion. Neither renderer emits em-dashes, emojis, or hedging language.

## Limitations

The plugin does not discover AI systems in the organization. Practitioners must supply the inventory; discovery belongs to the data engineering and IT asset management stacks. The plugin does not verify that artifact references (`aisia_ref`, `risk_register_ref`, `soa_ref`, `post_market_monitoring_plan_ref`) point to real files or URLs. Reference resolution is out of scope. The plugin does not prescribe risk-tier assignments. Use the `high-risk-classifier` plugin for EU AI Act classification; feed the resulting tier into the inventory.

The plugin does not interpret the organizational-scope definition. If the organization asserts that a given AI system is out of scope, the plugin trusts that assertion and does not emit warnings about the exclusion. Out-of-scope justifications belong in the AIMS scope statement, not in the inventory.

The plugin does not fetch remote URLs for `previous_inventory_ref`. The previous-inventory diff requires a local JSON file supplied as a path.

Legal disclaimer. This skill and its paired plugin produce audit-preparation artifacts grounded in the cited frameworks. They do not constitute legal advice on whether a specific AI system is subject to a specific regulation. Consult qualified counsel for jurisdiction-specific determinations.
