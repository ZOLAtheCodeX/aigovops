# NYC Local Law 144 of 2021 Operationalization Map

Working document for the `nyc-ll144` skill. Maps LL144 and the DCWP Final Rule (6 RCNY Chapter 5, Subchapter T) to the A/H/J operationalizability classification and the AIGovOps artifact vocabulary. Same methodology as `skills/iso42001/operationalization-map.md`, `skills/nist-ai-rmf/operationalization-map.md`, and `skills/eu-ai-act/operationalization-map.md`.

**Validation status.** Section references validated against the DCWP Final Rule text (https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/) and the enabling law on 2026-04-18.

**Classification legend.**

- A: automatable. The plugin derives the output deterministically from structured input.
- H: hybrid. The plugin assembles and validates, but a human provides key substantive content.
- J: judgment. A qualified human (counsel, auditor, senior reviewer) must decide.

**Leverage legend.**

- H: strong cost reduction from automation.
- M: moderate.
- L: low; narrow applicability or the automation surface is small.

## Section 5-300: Definitions

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| AEDT definition | Tool classification | J | `AISIA-section` | M | "Substantially assists" is the contested term. Counsel determines. The plugin records the caller's answer and the rationale. |
| Independent auditor | Auditor qualification | J | `audit-log-entry` | L | DCWP defines independence (no conflicting interest). Plugin consumes the identity string; it does not verify independence. |
| Candidate for employment | Scope of notice | H | `audit-log-entry` | L | Simple definition, captured as a configuration value. |

## Section 5-301: Bias audit requirements

The substantive operationalization core. The plugin's primary purpose is to package Section 5-301 output into Sections 5-303 and 5-304 deliverables.

| Provision | Theme | Class | Artifact | Leverage | AIGovOps plugin |
|---|---|---|---|---|---|
| Independent auditor performs audit | Audit execution | J | auditor output (external) | N/A | The audit itself is outside the plugin. Independent auditor uses their own methods. |
| Selection rates per required category | Statistic computation | A | `bias-audit-package` | H | Plugin packages auditor-supplied rates; it computes impact ratios and validates the required-category coverage. |
| Impact ratios per category | Statistic computation | A | `bias-audit-package` | H | Plugin divides each group rate by the most-selected group rate; rounds to 4 decimals. |
| Intersectional race-by-sex breakdown | Required category | A | `bias-audit-package` | H | Plugin warns if intersectional category absent. |
| Annual cadence | Time-based control | A | `bias-audit-package` | H | Plugin computes `audit_date + 365 days` as `next_audit_due_by`. |

## Section 5-302: Prohibition on use without current audit

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| No use of AEDT without current audit | Operational control | H | `bias-audit-package` + `audit-log-entry` | H | Plugin surfaces `next_audit_due_by`; a deployment gate (outside the plugin) blocks AEDT use after that date. |

## Section 5-303: Notice to candidates and employees

| Provision | Theme | Class | Artifact | Leverage | AIGovOps plugin |
|---|---|---|---|---|---|
| AEDT-use notice | Notice content | A | `bias-audit-package.candidate_notices[0]` | H | Plugin emits the required notice text and 10-business-day timing. |
| Job-qualifications notice | Notice content | A | `bias-audit-package.candidate_notices[1]` | H | Plugin emits the required notice text and 10-business-day timing. |
| Data type, source, retention information on request | Notice content | A | `bias-audit-package.candidate_notices[2]` | H | Plugin emits the required disclosure text. Operational delivery (30-day response on written request) is outside the plugin. |

## Section 5-304: Public disclosure of audit results

| Provision | Theme | Class | Artifact | Leverage | AIGovOps plugin |
|---|---|---|---|---|---|
| Summary of most recent audit | Disclosure content | A | `bias-audit-package.public_disclosure_bundle` | H | Plugin assembles the summary; selection rates, impact ratios, distribution comparison, date, auditor identity. |
| Publication on careers site | Delivery | H | external (website publication) | M | Plugin states the publication method; actual posting is operational. |

## Counts

| Class | Provisions |
|---|---|
| A | 8 |
| H | 4 |
| J | 3 |

Class split reflects the law's narrow scope and the plugin's corresponding narrow surface. Seven automatable or hybrid provisions map to a single plugin output artifact; three judgment calls remain human determinations.

## Plugin coverage summary

One plugin: `nyc-ll144-audit-packager`. The plugin's `generate_audit_package` function covers every automatable (A) provision above. The three hybrid (H) operational-delivery provisions (prohibition gate, 30-day response on written request, careers-site posting) are downstream of the plugin output and handled by the caller's operational workflows.

## Related frameworks crosswalk

| LL144 provision | EU AI Act analogue | ISO 42001 analogue | NIST AI RMF analogue |
|---|---|---|---|
| Section 5-301 bias audit | Article 10 data governance; Article 15(4) bias; Annex III, Point 4 | Annex A, Control A.6.2.4; Clause 6.1.3 | MEASURE 2.11 (fairness); MEASURE 2.12 (bias) |
| Section 5-303 candidate notice | Article 26(11) deployer information obligation; Article 50 transparency | Annex A, Control A.9.2 (transparency to affected parties) | GOVERN 6.2 (stakeholder engagement); MAP 5.2 (context specification) |
| Section 5-304 public disclosure | Article 26(8) logging and accessibility | Clause 9.1 (monitoring, measurement, analysis, evaluation) | MEASURE 3.3 (public reporting) |
| Section 5-302 annual cadence | Article 43 conformity re-assessment | Clause 10.2 (continual improvement) | MANAGE 4.3 (continuous improvement) |

An organization operating under ISO 42001 will produce the data-governance and monitoring records that feed an LL144 audit; it does not satisfy LL144 on its own because the LL144 audit must be performed by an independent auditor.
