# EU AI Act (Regulation (EU) 2024/1689) Operationalization Map

Working document for the `eu-ai-act` skill. Maps the Act's main provisions to the A/H/J operationalizability classification and the AIGovOps artifact vocabulary. Same methodology as `skills/iso42001/operationalization-map.md` and `skills/nist-ai-rmf/operationalization-map.md`.

**Validation status.** Article and Paragraph references validated by Zola Valashiya (LL.M Innovation and Technology Law; AIGP) on 2026-04-18 against the published Official Journal text of Regulation (EU) 2024/1689.

**Regulation context.** The EU AI Act was published in the Official Journal of the European Union on 12 July 2024 as Regulation (EU) 2024/1689. Enforcement is staged through 2030, with prohibitions applying from February 2025, general-purpose AI obligations from August 2025, and high-risk system obligations from August 2026 (with extended transition for some Annex III use cases to 2027).

**Crosswalk posture.** EU AI Act requirements for high-risk AI systems overlap substantially with ISO 42001 Annex A controls and with NIST AI RMF MAP and MEASURE subcategories. Operationalizations of risk management, data governance, technical documentation, human oversight, and post-market monitoring are shared with the other skills where requirements align.

## Chapter I: General provisions (Articles 1 through 4)

Scope, objectives, definitions, AI literacy. Largely narrative; no direct operationalization. The `SKILL.md` cites these in the Scope section.

## Chapter II: Prohibited AI practices (Article 5)

Eight categories of AI practices prohibited outright. Operationalization is a classification check at system onboarding: does the proposed use fall under Article 5? If yes, refuse; if no, proceed to Article 6 risk-tier determination.

| Article | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| 5(1)(a) | Subliminal manipulation causing harm | J | `AISIA-section` | M | Classification of whether a system does this is judgment; AISIA documents the determination. |
| 5(1)(b) | Exploitation of vulnerabilities (age, disability, socioeconomic) | J | `AISIA-section` | M | Same. |
| 5(1)(c) | Social scoring by public authorities | J | `AISIA-section` | L | Narrow applicability; most orgs n/a. |
| 5(1)(d) | Real-time remote biometric identification in public spaces (law-enforcement narrow exceptions) | J | `AISIA-section` | L | Mostly n/a. |
| 5(1)(e) | Predictive policing based solely on profiling | J | `AISIA-section` | L | Narrow. |
| 5(1)(f) | Emotion recognition in workplace and education (narrow exceptions) | H | `AISIA-section` | M | Many HR and edtech systems touch this; classification is hybrid. |
| 5(1)(g) | Biometric categorisation by sensitive characteristics | H | `AISIA-section` | M | Same. |
| 5(1)(h) | Untargeted scraping of facial images for facial recognition databases | H | `audit-log-entry` | M | Data-acquisition pipeline classification. |

**Class split Chapter II:** J 5, H 3, A 0. Prohibited practice classification is human judgment; automation at most documents the determination.

## Chapter III: High-risk AI systems (Articles 6 through 29)

The substantive compliance core of the Act for the majority of enterprise deployments.

### Article 6 and Annex III: High-risk classification

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Article 6(1) | Product safety high-risk determination (Annex I products) | H | `AISIA-section` | H | Structured classification based on product type and CE-mark applicability. |
| Article 6(2), Annex III | High-risk use-case determination | H | `AISIA-section` | H | Eight Annex III categories (biometrics, critical infrastructure, education, employment, essential services, law enforcement, migration, administration of justice). Structured classification feasible. |
| Article 6(3) | Exception to Annex III classification when system is not significant risk | H | `AISIA-section` | M | Organization-specific analysis; agent documents the reasoning. |

### Articles 9 through 15: Requirements for high-risk AI systems

These seven articles are where AIGovOps has the strongest operationalization leverage: each maps to an existing ISO 42001 Annex A control family and an existing AIGovOps plugin.

| Article | Theme | Class | Artifact | Leverage | ISO 42001 crosswalk | AIGovOps plugin |
|---|---|---|---|---|---|---|
| Article 9 | Risk management system | H | `risk-register-row` | H | Clause 6.1.2, 6.1.3, 8.2 | `risk-register-builder` |
| Article 10 | Data and data governance | H | `audit-log-entry`, (data-register) | H | Annex A A.7 (A.7.2, A.7.3, A.7.4, A.7.5, A.7.6) | Future `data-register-builder`; `audit-log-generator` for provenance events |
| Article 11 | Technical documentation | H | `audit-log-entry` | H | Annex A A.6.2.3, A.6.2.7 | `audit-log-generator` |
| Article 12 | Record-keeping (automatic logs) | A | `audit-log-entry` | H | Annex A A.6.2.8 | `audit-log-generator` (AI system event mode) |
| Article 13 | Transparency and provision of information to deployers | H | (user-doc) | M | Annex A A.8.2 | Future `user-documentation-generator` |
| Article 14 | Human oversight | H | `role-matrix` | H | Annex A A.3.2; NIST MAP 3.5 | `role-matrix-generator` |
| Article 15 | Accuracy, robustness, and cybersecurity | H | `KPI` | H | Annex A A.6.2.4, A.6.2.6; NIST MEASURE 2.5, 2.6, 2.7 | `metrics-collector` |

**Class split Articles 9-15:** J 0, H 6, A 1. Dense operationalization territory. Every article has an existing AIGovOps plugin or a clearly-scoped future one.

### Articles 16 through 29: Obligations of economic actors

Provider, deployer, importer, distributor, authorised representative roles. Each role has a differentiated obligation set.

| Article | Actor | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Article 16 | Providers: general obligations | H | Multiple | H | Umbrella. Breaks down into Articles 17-21. |
| Article 17 | Providers: quality management system | H | (QMS-doc) | M | Integrates with ISO 9001 or equivalent if present. |
| Article 18 | Providers: documentation retention | A | `audit-log-entry` | M | 10-year retention per. |
| Article 19 | Providers: automatically generated logs | A | `audit-log-entry` | M | Cross-references Article 12. |
| Article 20 | Providers: corrective actions | H | `nonconformity-record` | H | Crosswalk: ISO 42001 Clause 10.2; plugin: `nonconformity-tracker`. |
| Article 21 | Providers: cooperation with authorities | H | `audit-log-entry` | M | Logged request-response cycles. |
| Article 22 | Authorised representatives for non-EU providers | H | `role-matrix` | M | Role assignment. |
| Article 23 | Importers | H | (supplier-register) | M | Supply-chain governance. |
| Article 24 | Distributors | H | (supplier-register) | M | Same. |
| Article 25 | Provider-deployer obligation flips | J | N/A | M | Legal determination. |
| Article 26 | Deployers: obligations | H | Multiple | H | Umbrella. |
| Article 27 | Deployers: fundamental rights impact assessment (FRIA) | H | `AISIA-section` | H | Strong overlap with AISIA. Crosswalk to ISO 42001 Clause 6.1.4. |
| Article 28 | Notifying authorities | J | N/A | L | Regulator-side; orgs generally not concerned. |
| Article 29 | Notified bodies | J | N/A | L | Same. |

**Class split Articles 16-29:** J 4, H 9, A 2.

## Chapter IV: Transparency obligations for certain AI systems (Article 50)

| Article | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Article 50(1) | Disclosure when interacting with AI | H | (user-doc) | M | |
| Article 50(2) | Marking of synthetic audio, image, video, text | H | `KPI` | H | Measurable by `metrics-collector`'s information-integrity family (AI 600-1 overlay crosswalk). |
| Article 50(3) | Emotion recognition and biometric categorisation disclosure | H | (user-doc) | M | |
| Article 50(4) | Deep fake labeling | H | `audit-log-entry` | M | |

## Chapter V: General-purpose AI models (Articles 51 through 55)

Providers of GPAI models (foundation models, LLMs) have a distinct obligation set that cuts across the deployer-facing article structure.

| Article | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Article 51 | Classification of GPAI models with systemic risk | H | `AISIA-section` | H | Structured threshold check (compute FLOPs, capability evaluation). |
| Article 52 | Procedure for classifying as systemic risk | H | `audit-log-entry` | M | Notification to Commission. |
| Article 53 | Obligations for providers of GPAI models (documentation, training-data summary, copyright policy) | H | `audit-log-entry`, (data-register) | H | Strong operationalization target. |
| Article 54 | Authorised representatives of non-EU GPAI providers | H | `role-matrix` | M | Role assignment. |
| Article 55 | Additional obligations for systemic-risk GPAI | H | Multiple | H | Model evaluation, adversarial testing, serious-incident tracking, cybersecurity. Crosswalk: NIST MEASURE 2.7, AI 600-1. |

**Class split Articles 51-55:** J 0, H 5, A 0. GPAI obligations are hybrid automation with strong MLOps overlap.

## Chapter VI through IX: Conformity assessment, post-market monitoring, governance

| Provision | Theme | Class | Artifact | Leverage | Notes |
|---|---|---|---|---|---|
| Article 43 | Conformity assessment procedures | H | (conformity-assessment-doc) | M | |
| Article 44 | Certificates | A | `audit-log-entry` | M | |
| Article 47 | EU declaration of conformity | A | `audit-log-entry` | M | |
| Article 48 | CE marking | A | `audit-log-entry` | L | |
| Article 49 | EU database for high-risk AI | A | `audit-log-entry` | M | |
| Article 72 | Post-market monitoring | A | `KPI`, `audit-log-entry` | H | Crosswalk: NIST MANAGE 4.1; plugin: `metrics-collector`. |
| Article 73 | Reporting of serious incidents | A | `audit-log-entry` | H | Crosswalk: ISO 42001 Annex A A.8.4. |

## Priority-ranked operationalization backlog

Ranked by leverage and cross-weighted against shared operationalizations with iso42001 and nist-ai-rmf.

### Tier 1 (EU AI Act plugin priority, heavy reuse)

1. **Article 27: Fundamental Rights Impact Assessment (FRIA).** Shared with iso42001 T1.2 AISIA and nist-ai-rmf T1.1. `aisia-runner` gains an `eu-ai-act` framework mode that renders FRIA-specific citations.
2. **Article 9: Risk management system.** Shared with iso42001 T1.7 and nist-ai-rmf T1.3 risk register. `risk-register-builder` adds EU AI Act citation mode.
3. **Articles 11 and 12: Technical documentation and automatic logs.** Shared with iso42001 T1.3 documented information control. `audit-log-generator` serves with an EU-AI-Act rendering mode.
4. **Article 14: Human oversight.** Shared with iso42001 T1.6 role matrix and NIST GOVERN 2.1. `role-matrix-generator` adds EU AI Act citation mode.
5. **Article 15: Accuracy, robustness, cybersecurity.** Shared with NIST MEASURE 2.5, 2.6, 2.7. `metrics-collector` adds EU AI Act mode.
6. **Article 20: Corrective actions.** Shared with iso42001 T1.5 nonconformity. `nonconformity-tracker` adds EU AI Act mode.
7. **Article 72: Post-market monitoring.** Shared with NIST MANAGE 4.1. `metrics-collector` monitoring views surface here.

### Tier 2 (EU-AI-Act-specific, new plugin work)

- **Article 6 and Annex III: High-risk classification engine.** Distinct plugin: takes a system description and returns risk tier and Annex III category. High value because every EU deployment needs this classification.
- **Article 53: GPAI provider documentation.** Training-data summary, copyright policy, model card. Integrates with AI 600-1 overlay of `metrics-collector`.
- **Article 50: Transparency disclosures.** Automated detection of whether a system's UX includes the required disclosures.

### Tier 3 (judgment-bound)

- Article 5 prohibited-practice classification.
- Article 25 provider-deployer role flip determination.
- Conformity-assessment procedure selection.

## Open design questions

Item 1 in prior versions of this map concerned Article and Paragraph verification and was resolved in the Lead Implementer validation pass on 2026-04-18. Remaining items are design questions carried forward into Phase 4 planning:

1. **FRIA versus AISIA.** Article 27 FRIA is strongly aligned with ISO 42001 AISIA but has EU-specific dimension requirements (fundamental rights enumeration, deployer-specific context). `aisia-runner` should add an `eu-ai-act` rendering mode that enforces the Article 27 schema.
2. **High-risk classification engine design.** Article 6 and Annex III classification is structured enough to merit a dedicated plugin. Draft contract: takes a system description with `intended_use`, `sector`, `data_processed`, `decision_authority`; returns `{risk_tier, annex_iii_category, rationale, citations}`.
3. **GPAI threshold calibration.** The Act references compute-FLOP thresholds and capability tests for systemic-risk classification. These thresholds may be updated by delegated acts; the classification plugin must read a current-thresholds config rather than hard-coding.
4. **EU AI Act database submission.** Article 49 requires certain high-risk systems to be registered in an EU database. The audit-log workflow should emit a hook for the submission event; the actual submission is through the EU's UI or API, not automated here in Phase 3.
5. **Enforcement timeline tracking.** Different articles apply from different dates. The skill should track applicability-by-date so that pre-effective-date drafts are not falsely flagged as non-compliant.

## Next step

Populate the `SKILL.md` body against this map. Priority: Tier 1 items first (because they reuse existing plugins via framework-mode extension), then Tier 2 (EU-AI-Act-distinctive plugins).
