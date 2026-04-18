# California AI Operationalization Map

Working document for the `california-ai` skill. Maps each instrument in `regulatory-register.yaml` to AIGovOps plugin artifacts and the A/H/J operationalizability classification. Same methodology as the other skills in this repository.

**Validation status.** Register entries and section references validated on 2026-04-18 against the California Legislative Information portal (https://leginfo.legislature.ca.gov/) and the CPPA regulations portal (https://cppa.ca.gov/regulations/).

**Design stance.** California is a secondary-priority jurisdiction under `docs/jurisdiction-scope.md`. No California-specific plugin ships. Practitioners use the existing primary-jurisdiction plugins (iso42001, NIST AI RMF, EU AI Act) with California citations added to the `citations` fields of artifact records. This map records which plugin produces which California-relevant output, and what California-specific additions the caller must supply.

## CPPA Automated Decisionmaking Technology (ADMT) regulations

| Obligation | Class | Artifact | AIGovOps plugin | California-specific additions |
|---|---|---|---|---|
| Pre-use notice of ADMT for significant decisions | A | `AISIA-section` | `aisia-runner` | Pre-use notice timing per CPPA section; enumeration of significant decision categories; opt-out URL |
| Access request handling | H | `data-register-row` | `data-register-builder` | Access-request response SLA; data-subject-rights fulfillment linkage |
| Opt-out of ADMT for significant decisions | A | `role-matrix` | `role-matrix-generator` | Human-review alternative pathway; identity of reviewer |
| Risk assessment for high-risk ADMT processing | H | `AISIA-section` | `aisia-runner` | CPPA risk-assessment retention period; submission-on-request mechanism |
| Significant-decision categorization | J | `AISIA-section` | `aisia-runner` | Counsel determination for ambiguous categories (education access, healthcare access edge cases) |

Citation format: `CCPA Regulations (CPPA), Section <section>`.

## CCPA as amended by CPRA

| Obligation | Class | Artifact | AIGovOps plugin | California-specific additions |
|---|---|---|---|---|
| Notice at collection | A | `data-register-row` | `data-register-builder` | California resident categorization; purpose-of-use per CCPA section |
| Right to know, right to delete, right to correct | H | `data-register-row` | `data-register-builder` | Consumer-request workflow linkage |
| Right to limit use of sensitive personal information | A | `data-register-row` | `data-register-builder` | Sensitive-PI inventory; limit-use mechanism |
| Profiling disclosure (via CPPA ADMT) | A | `AISIA-section` | `aisia-runner` | See ADMT row above |

Citation format: `California Civil Code, Section 1798.<section>`.

Baseline privacy program typically already addresses CCPA. AIGovOps artifacts extend that coverage for AI-specific processing.

## SB 942 California AI Transparency Act

| Obligation | Class | Artifact | AIGovOps plugin | California-specific additions |
|---|---|---|---|---|
| Provide free AI-detection tool | J | external (operational) | N/A | Outside plugin scope. Operational responsibility. |
| Include manifest provenance disclosure | A | `audit-log-entry` | `audit-log-generator` | Provenance-insertion event record with mechanism reference |
| Include latent provenance disclosure | A | `audit-log-entry` | `audit-log-generator` | Watermarking-mechanism reference |
| Licensee contract requirements | H | external (legal) | N/A | Contract-template responsibility outside the catalogue |

Citation format: `California Business and Professions Code, Section <section>`.

Applies to generative AI providers reaching California users. Implementation of watermarking and detection tooling is an operational responsibility; AIGovOps records the fact of implementation.

## AB 2013 California Training Data Transparency

| Obligation | Class | Artifact | AIGovOps plugin | California-specific additions |
|---|---|---|---|---|
| Publish training-data source documentation | A | `data-register-row` | `data-register-builder` | California-user-population scope assertion |
| Publish training-data purpose documentation | A | `data-register-row` | `data-register-builder` | Training-purpose taxonomy |
| Publish training-data protection documentation | A | `data-register-row` | `data-register-builder` | Protection-measures roll-up from ISO/IEC 42001 Annex A, A.7 |

Citation format: `California Business and Professions Code, Section <section>`.

AB 2013 obligations align tightly with EU AI Act Annex IV (training data documentation for GPAI). Practitioners who produce the Annex IV documentation satisfy most of AB 2013 with a California-scope annotation.

## AB 1008 Personal Information in AI Training Data

| Obligation | Class | Artifact | AIGovOps plugin | California-specific additions |
|---|---|---|---|---|
| Treat training-data personal information as personal information under CCPA | H | `data-register-row` | `data-register-builder` | Cross-reference from training-data register to CCPA consumer-rights surface |
| Respect CCPA consumer rights over training-data personal information | H | `data-register-row` | `data-register-builder` | Deletion and correction workflows applied to training snapshots where feasible |

Citation format: `California Civil Code, Section 1798.<section>`.

AB 1008 creates a tension with AB 2013: AB 2013 requires publishing training-data documentation while AB 1008 preserves consumer deletion and correction rights over the underlying personal information. The reconciliation is that the published documentation describes the data in aggregate terms; the consumer-rights surface operates at the individual-record level.

## SB 1001 Bot Disclosure

| Obligation | Class | Artifact | AIGovOps plugin | California-specific additions |
|---|---|---|---|---|
| Disclose automated-bot use for commercial or electoral communication | A | `role-matrix` | `role-matrix-generator` | Bot-disclosure responsibility row in deployer matrix |

Citation format: `California Business and Professions Code, Section 17940 et seq.`.

Narrow in applicability (commercial transactions and election influence). Many conversational-AI deployments default to disclosure anyway; the role matrix captures the responsibility.

## AB 1836 Digital Replicas of Deceased Personalities

| Obligation | Class | Artifact | AIGovOps plugin | California-specific additions |
|---|---|---|---|---|
| Obtain estate consent for digital replica | J | `AISIA-section` | `aisia-runner` | Consent-documentation reference |

Citation format: `California Civil Code, Section 3344.1`.

Legal judgment. AIGovOps records the determination; it does not determine.

## SB 1047 (VETOED)

Not applicable. Register entry records the veto explicitly so practitioners do not apply it.

## California Attorney General AI Guidance

| Obligation | Class | Artifact | AIGovOps plugin | California-specific additions |
|---|---|---|---|---|
| Read periodic AG guidance; incorporate | H | `audit-log-entry` | `audit-log-generator` | Guidance-received event with link and incorporation-decision record |

Citation format: `California Attorney General Guidance (YYYY-MM-DD)`.

Not binding rulemaking. Relevant to enforcement posture.

## Proposed 2025-2026 bills

Tracked in the register. Not operationalized until signed into law. The framework-drift playbook refresh checks for new-law triggers.

## Counts across the skill

| Class | Obligations |
|---|---|
| A | 15 |
| H | 10 |
| J | 5 |

The California footprint is larger than NYC LL144 because California spans multiple instruments. Most obligations map to plugins that already exist for primary-jurisdiction frameworks; California adds citations and scope annotations rather than new plugin logic.

## Cross-jurisdictional consolidation

A California-operating AI system often also falls under EU AI Act and NIST AI RMF. The table below shows overlap. Practitioners who produce the EU AI Act and NIST artifacts in `dual` mode capture most California-specific content through citation extension.

| California instrument | EU AI Act analogue | NIST AI RMF analogue | ISO 42001 analogue |
|---|---|---|---|
| CPPA ADMT risk assessment | Article 9 risk management; Article 27 FRIA | MAP 5.2; MEASURE 2.11 | Clause 6.1.2; Annex A, Control A.6.2.4 |
| AB 2013 training data documentation | Article 10; Annex IV | MAP 4.1 | Annex A, Control A.7 |
| SB 942 content provenance | Article 50 transparency | MANAGE 4.3 | Annex A, Control A.9 |
| CPPA ADMT pre-use notice | Article 26(11); Article 50 | MAP 5.1 | Annex A, Control A.9.2 |
| AB 1008 training-data PII | Article 10(5) (CCPA-analogue through GDPR intersection) | MAP 4.1 | Annex A, Control A.7 |

Where cells are blank, the overlap is partial or the framework treats the issue obliquely. Counsel should review overlap determinations before relying on an aggregation.
