---
name: supplier-vendor
version: 0.1.0
description: >
  Supplier and vendor governance skill. Operationalizes ISO/IEC 42001:2023
  Annex A category A.10 (Allocation of responsibilities, Suppliers,
  Customers) together with EU AI Act Article 25 (Responsibilities along
  the AI value chain), Article 26(a) (importer check obligations), and
  NYC Local Law 144 Final Rule Section 5-300 (auditor-independence
  criteria) into a structured vendor-assessment record and supply-chain
  graph.
frameworks:
  - ISO/IEC 42001:2023
  - EU AI Act (Regulation (EU) 2024/1689)
  - NYC Local Law 144 of 2021
  - NIST AI RMF 1.0
tags:
  - ai-governance
  - supplier-relationships
  - value-chain
  - auditor-independence
  - third-party-risk
  - annex-a-10
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes AI-supplier and AI-vendor governance. Three framework families converge on a single structured output: a supplier-risk record that names the vendor, reconciles the organization's value-chain role against the vendor's role, maps contractual obligations to ISO A.10 controls, and surfaces the NYC LL144 auditor-independence criteria when the vendor is an audit or evaluation service.

Framework convergence:

- **ISO/IEC 42001:2023, Annex A.10** requires allocation of responsibilities (A.10.2), documented third-party-supplier obligations (A.10.3), and customer commitments (A.10.4).
- **EU AI Act, Article 25** allocates responsibilities along the AI value chain: substantial modification by a deployer can re-classify the deployer as a provider (Art. 25(1)(c)); distributors verify conformity before placing on the market (Art. 25(3)); general-purpose AI model providers cooperate with downstream integrators (Art. 25(4)). Article 26(a) adds importer check duties.
- **NYC LL144 Final Rule, Section 5-300** requires the independent bias auditor to have no material financial interest in the AEDT, its developer, or its deployer, and prohibits audit-outcome-contingent compensation.

The `supplier-vendor-assessor` plugin is the primary operationalization. It validates a vendor description and contract summary, reconciles value-chain roles, maps the contract summary to ISO A.10 expectations, flags gaps, and emits an independence-criteria block for audit-service vendors.

## Scope

**In scope.**

- ISO/IEC 42001:2023, Annex A, Controls A.10.2, A.10.3, A.10.4.
- EU AI Act, Article 25 (all paragraphs) and Article 26, Paragraph 1, Point (a).
- NYC LL144 Final Rule, Section 5-300 independence criteria surfaced as a checklist for practitioner confirmation.
- NIST AI RMF 1.0 GOVERN 6.1 (third-party risk policies) and GOVERN 6.2 (contingency planning for third-party failure).
- Tiered supply-chain modeling (organization -> tier-1 vendor -> tier-2 sub-processors).

**Out of scope.**

- Risk rating of vendors. The plugin does not compute vendor risk scores; organizational risk appetite and evidence thresholds live in the risk register.
- Independence determination. The plugin surfaces the NYC LL144 criteria for practitioner confirmation but does not assert independence.
- Contract drafting. The plugin reads a structured contract summary; it does not author contract language.
- Procurement workflow orchestration. Vendor onboarding sequencing lives in the runtime agent.

## Framework Reference

| Sub-clause | Citation | Substance |
|---|---|---|
| ISO A.10.2 | `ISO/IEC 42001:2023, Annex A, Control A.10.2` | Documented allocation of responsibilities among provider, deployer, and third parties. |
| ISO A.10.3 | `ISO/IEC 42001:2023, Annex A, Control A.10.3` | Documented third-party-supplier obligations, including audit rights and incident notification. |
| ISO A.10.4 | `ISO/IEC 42001:2023, Annex A, Control A.10.4` | Organization's commitments to its customers regarding the AI systems it supplies. |
| EU AI Act Art. 25(1) | `EU AI Act, Article 25, Paragraph 1` | Value-chain responsibility allocation, including Art. 25(1)(c) re-classification on substantial modification. |
| EU AI Act Art. 25(3) | `EU AI Act, Article 25, Paragraph 3` | Distributor obligations, including Art. 25(3)(c) conformity verification. |
| EU AI Act Art. 25(4) | `EU AI Act, Article 25, Paragraph 4` | GPAI-model-provider cooperation duties to downstream integrators. |
| EU AI Act Art. 26(a) | `EU AI Act, Article 26, Paragraph 1, Point (a)` | Importer pre-market check obligations. |
| NYC LL144 5-300 | `NYC LL144 Final Rule, Section 5-300` | Independent auditor definition and independence criteria. |
| NIST GOVERN 6.1 | `NIST GOVERN 6.1` | Policies and procedures for third-party AI risk. |
| NIST GOVERN 6.2 | `NIST GOVERN 6.2` | Contingency processes for third-party failure or withdrawal. |

Authoritative NYC LL144 rule URL: https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/

## Operationalizable Controls

| Control | Class | Artifact | Plugin |
|---|---|---|---|
| A.10.2 Allocation of responsibilities | Hybrid | supplier-risk-record (role reconciliation block) | `supplier-vendor-assessor` |
| A.10.3 Suppliers | Hybrid | supplier-risk-record (assessment matrix, contract summary) | `supplier-vendor-assessor` |
| A.10.4 Customers | Hybrid | supplier-risk-record (customer commitments block; practitioner-authored) | `supplier-vendor-assessor` |
| EU Art. 25(1)(c) re-classification | Human judgment | warning flag + legal review hand-off | `supplier-vendor-assessor` |
| EU Art. 25(3)(c) distributor | Hybrid | reconciliation note | `supplier-vendor-assessor` |
| EU Art. 25(4) downstream integrator | Hybrid | reconciliation note | `supplier-vendor-assessor` |
| EU Art. 26(a) importer check | Hybrid | reconciliation note | `supplier-vendor-assessor` |
| NYC 5-300 independence criteria | Hybrid | independence-assessment block (practitioner-confirmed) | `supplier-vendor-assessor` |
| NIST GOVERN 6.1 | Hybrid | assessment matrix + warnings | `supplier-vendor-assessor` |
| NIST GOVERN 6.2 | Hybrid | financial-stability dimension warning | `supplier-vendor-assessor` |

Primary entry point: `assess_vendor()`. Renderers: `render_markdown()`, `render_csv()`.

## Output Standards

- All outputs follow STYLE.md citation formats verbatim.
- Every emitted assessment record carries `timestamp`, `agent_signature`, `framework`, `citations`, `warnings`, `summary`.
- Status values are drawn from the fixed vocabulary `addressed`, `partial`, `not-addressed`, `requires-practitioner-assessment`.
- Independence status is always `requires-practitioner-confirmation` at plugin output; final determination is a human act recorded in the consuming `nyc-ll144-audit-packager` bundle or management-review package.
- No em-dashes, no emojis, no hedging language per STYLE.md.
- Deterministic output for deterministic input except for the UTC `timestamp` field.

## Limitations

- The plugin does not rate vendors or compute risk levels. Risk rating belongs in the risk register.
- The plugin does not make the independence determination for NYC LL144 audits. It surfaces the criteria. The practitioner confirms.
- The plugin does not discover sub-processors. Tier-2 supply-chain entries are supplied by the caller. Each tier-2 vendor is flagged `tier-2-assessment-pending` until a nested assessment is produced.
- The plugin does not validate contract effective-date or expiry-date against system go-live dates; this cross-check belongs in the `ai-system-inventory-maintainer` plugin.
- The plugin does not author A.10.4 customer commitments. The customer-facing commitments are organization-authored and belong in the AI policy or the customer-facing terms.
