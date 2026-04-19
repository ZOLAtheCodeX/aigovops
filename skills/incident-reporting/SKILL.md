---
name: incident-reporting
version: 0.1.0
description: >
  External-facing AI incident reporting skill with statutory-deadline
  awareness. Distinct from internal Clause 10.2 nonconformity tracking.
  Covers EU AI Act Article 73 serious-incident reporting (2 / 10 / 15
  day deadlines), Colorado SB 205 Sections 6-1-1702(7) and 6-1-1703(7)
  90-day Attorney General disclosure, and NYC LL144 candidate-complaint
  disclosure under DCWP AEDT Rules. Composes with nonconformity-tracker
  (internal root cause) and audit-log-generator (Clause 9.1 evidence
  trail).
frameworks:
  - ISO/IEC 42001:2023
  - NIST AI RMF 1.0
  - EU AI Act (Regulation (EU) 2024/1689)
  - Colorado Senate Bill 24-205
  - NYC Local Law 144 of 2021
tags:
  - ai-governance
  - incident-reporting
  - serious-incident
  - regulatory-deadline
  - eu-ai-act
  - colorado-sb-205
  - nyc-ll144
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes external AI incident reporting with statutory-deadline enforcement. It is the external-facing sibling of the [`iso42001`](../iso42001/SKILL.md) Clause 10.2 nonconformity track. Clause 10.2 governs internal corrective action; this skill covers the authority-notification obligations that attach when a nonconformity is also a reportable incident under a jurisdiction-specific regime.

The skill pairs with the [`incident-reporting`](../../plugins/incident-reporting/) plugin. The plugin determines per-jurisdiction applicability, computes deadlines from `detected_at`, and assembles report-draft templates with required-content checklists. Practitioner completes the narrative and files with the competent authority. The plugin does not transmit reports.

Three regimes are shipped today with automated deadline computation:

- EU AI Act Article 73 (serious incident reporting: 2 / 10 / 15 day windows).
- Colorado SB 205 Sections 6-1-1702(7) and 6-1-1703(7) (90-day Attorney General disclosure).
- NYC LL144 candidate-complaint disclosure (30-day DCWP response window).

Additional jurisdictions declared in input surface as manual-review warnings rather than silent drops.

## Scope

**In scope.**

- EU AI Act Article 73 serious-incident reporting by providers and (via Article 26(5)) deployers, including the 2-day window for fatality and widespread infringement, 10-day window for serious physical harm and critical infrastructure disruption, and 15-day default window under Article 73, Paragraph 2.
- EU AI Act Article 20 corrective action and authority-notification obligation (provider duty to take immediate action and inform competent authorities, importers, and distributors).
- Colorado SB 205 Section 6-1-1702(7) developer disclosure of known or reasonably foreseeable algorithmic discrimination to the Attorney General and known deployers within 90 days of discovery.
- Colorado SB 205 Section 6-1-1703(7) deployer disclosure of algorithmic discrimination to the Attorney General within 90 days of discovery.
- NYC LL144 Section 20-872 and NYC DCWP AEDT Rules, Subchapter T, Section 5-303 candidate-complaint response obligations.
- ISO/IEC 42001:2023, Clause 10.2 framing as the internal corrective-action counterpart. The skill clarifies that Clause 10.2 alone does not discharge Article 73 or SB 205 obligations because ISO 42001 has no external-authority-notification deadline.
- NIST AI RMF MANAGE 4.3 (incidents and errors communicated to AI actors) as the informational counterpart in the NIST family.

**Out of scope.**

- Legal advice on whether a given nonconformity rises to the definitional threshold of a reportable incident under any listed regime. Threshold determinations (serious incident under Article 3(49), algorithmic discrimination under Section 6-1-1701(1), substantially-assists under DCWP Section 5-300) require qualified counsel.
- Actual transmission of reports to authorities. The plugin prepares drafts; filing is operational.
- Jurisdictions beyond the three shipped today (UK, Singapore, Canada, California). These are validated inputs and surface warnings, but automated deadline rules are not yet implemented.
- Sectoral incident-reporting regimes (HIPAA breach notification, GDPR Article 33, SEC cybersecurity disclosure). These operate alongside and are not crosswalked here.

**Operating assumption.** The user organization has detected a candidate incident and needs to determine which external-reporting obligations attach, within what timeframe, and with what content. The skill presumes that determination work has been initiated (detected_at is set); it does not detect incidents.

## Framework Reference

**Authoritative sources.**

- EU AI Act, Regulation (EU) 2024/1689: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689. Articles 20 (corrective action and authority notification), 26(5) (deployer notification trigger), and 73 (serious incident reporting by providers).
- Colorado Senate Bill 24-205, codified at Colorado Revised Statutes Title 6, Article 1, Part 17, Sections 6-1-1701 through 6-1-1707. Sections 6-1-1702(7) and 6-1-1703(7) govern the 90-day Attorney General disclosure.
- NYC Local Law 144 of 2021 and NYC DCWP AEDT Rules (6 RCNY Chapter 5, Subchapter T, Sections 5-300 through 5-304): https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/.
- ISO/IEC 42001:2023, Clause 10.2 (Nonconformity and corrective action).
- NIST AI Risk Management Framework 1.0 (AI RMF 1.0), MANAGE 4.3 (informational counterpart on incident communication).

**Deadline matrix (summary).**

| Regime | Severity | Days from `detected_at` | Recipient |
|---|---|---|---|
| EU AI Act, Article 73, Paragraph 6 | fatal, widespread infringement | 2 | EU AI Office via national competent authority |
| EU AI Act, Article 73, Paragraph 7 | serious physical harm, critical infrastructure disruption | 10 | EU AI Office via national competent authority |
| EU AI Act, Article 73, Paragraph 2 | default (other serious incidents) | 15 | EU AI Office via national competent authority |
| Colorado SB 205, Section 6-1-1702(7) | developer algorithmic discrimination disclosure | 90 | Colorado Attorney General and known deployers |
| Colorado SB 205, Section 6-1-1703(7) | deployer algorithmic discrimination disclosure | 90 | Colorado Attorney General |
| NYC DCWP AEDT Rules, Section 5-303 | AEDT candidate complaint | 30 | NYC DCWP |

## Operationalizable Controls

The skill operationalizes one Tier 1 capability: regulatory-deadline-aware external incident reporting. It composes with two siblings.

**Tier 1: deadline-aware report drafting.**

- Input: detected_at, incident description with potential harms, applicable jurisdictions, actor role, consequential domains (for Colorado), containment actions, correction plan.
- Processing: applicability determination per jurisdiction; deadline computation (`detected_at + days`); status recomputation (`future`, `imminent-within-48h`, `overdue`); template assembly; required-contents checklist emission.
- Output: `deadline_matrix` and `report_drafts` per applicable jurisdiction, with practitioner-completion placeholders surfaced as warnings.
- Plugin: `generate_incident_report()`, `render_markdown()`, `render_csv()`.

**Composition with internal counterpart.** The [`nonconformity-tracker`](../../plugins/nonconformity-tracker/) plugin records the Clause 10.2 internal root-cause and corrective-action lifecycle. The internal record and the external report are produced in parallel, not sequentially. A nonconformity that qualifies as a reportable incident must not wait for internal closure before external filing; the Article 73 and SB 205 clocks run independently.

**Composition with audit-log-generator.** Every external filing event is a documented-information event under ISO/IEC 42001:2023, Clause 7.5.2. The aigovclaw runtime routes `report_drafts` entries to [`audit-log-generator`](../../plugins/audit-log-generator/) so that the evidence trail for Clause 9.1 monitoring, measurement, analysis and evaluation records the external-reporting decision and its timestamp.

**Composition with risk-register-builder.** A recurring incident surfaces a residual-risk increase. The risk register consumes the `severity` and `impacted_persons_count` signals for post-market-monitoring recalibration.

See [`operationalization-map.md`](operationalization-map.md) for the per-regime mapping.

## Output Standards

All outputs carry citations in [STYLE.md](../../STYLE.md) format:

- `EU AI Act, Article 73, Paragraph <n>`
- `Colorado SB 205, Section 6-1-1702(7)` and `Colorado SB 205, Section 6-1-1703(7)`
- `NYC LL144` and `NYC DCWP AEDT Rules, Subchapter T, Section 5-303`
- `ISO/IEC 42001:2023, Clause 10.2`
- `MANAGE 4.3` (NIST AI RMF, informational)

Report drafts carry explicit `Requires practitioner completion: <field>` placeholders for any narrative content the plugin refuses to invent. No em-dashes. No emojis. No hedging language. Status values are binary in the reporting posture: a filing is `future`, `imminent-within-48h`, or `overdue`.

## Limitations

1. **No transmission.** The plugin prepares drafts; practitioner files. No authority integrations exist.
2. **Threshold determinations remain human.** "Serious incident" under Article 3(49), "algorithmic discrimination" under Section 6-1-1701(1), and "substantially assists" under DCWP Section 5-300 are legal determinations. The plugin records the caller's answer.
3. **Three regimes today.** UK, Singapore, Canada, and California are validated jurisdictional inputs but surface manual-review warnings rather than automated deadline rules.
4. **Status is wall-clock dependent.** `status` is recomputed each invocation. Between invocations a `future` entry can become `imminent-within-48h` or `overdue`. Do not cache status.
5. **No drift tracking on statutory amendments.** Amendments to Article 73, SB 205, or DCWP rules are tracked via the `framework-drift` playbook, not inside the plugin. Confirm deadline values against current statute before filing.
