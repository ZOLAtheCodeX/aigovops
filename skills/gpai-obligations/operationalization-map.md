# GPAI Obligations Operationalization Map

Working document for the `gpai-obligations` skill. Maps each EU AI Act GPAI provision (Articles 51 to 55) to its A/H/J operationalizability classification, the AIGovOps artifact vocabulary, and the relationship to existing catalogue plugins.

**Validation status.** Section references validated against EU AI Act (Regulation (EU) 2024/1689) on 2026-04-18.

**Classification legend.**

- A: automatable. The plugin derives output deterministically from structured input.
- H: hybrid. The plugin assembles and validates; a human provides key substantive content.
- J: judgment. A qualified human (counsel, evaluator, AI Office liaison) must decide.

**Leverage legend.** H: strong cost reduction from automation. M: moderate. L: low.

## Article 51: Classification of GPAI models with systemic risk

| Provision | Theme | Class | Plugin field | Leverage | Notes |
|---|---|---|---|---|---|
| Article 51(1) systemic-risk definition | Threshold determination | J | `systemic_risk_status` | L | Counsel determines whether high-impact-capability criterion applies. Plugin records the answer. |
| Article 51(1)(a) compute presumption (10^25 FLOPs) | Threshold computation | A | `model_description.training_compute_flops` | H | Plugin compares numeric input against the threshold constant. |
| Article 51(2) presumption-rebuttal procedure | Procedural | J | external | L | Outside plugin. Provider rebuts to Commission. |
| Annex XIII criteria (parameters, dataset size, modalities, market impact) | Multi-factor classification | H | `model_description` (echo) | M | Plugin echoes inputs but does not adjudicate. |

## Article 52: Procedure for systemic-risk designation

| Provision | Theme | Class | Plugin field | Leverage | Notes |
|---|---|---|---|---|---|
| Two-week notification window | Procedural | H | `designated_systemic_risk` | M | Plugin records designation; the two-week clock is operational. |

## Article 53: Universal GPAI provider obligations

| Provision | Theme | Class | Plugin field | Leverage | Notes |
|---|---|---|---|---|---|
| Article 53(1)(a) technical documentation per Annex XI | Documentation | H | `technical_documentation_ref` | H | Plugin records reference. Practitioner authors the Annex XI bundle. |
| Article 53(1)(b) downstream-integrator documentation | Documentation | H | `downstream_integrator_docs_ref` | H | Plugin records reference. |
| Article 53(1)(c) copyright compliance policy (Article 4(3) CDSM) | Policy authorship | H | `copyright_policy_ref` | M | Plugin records reference. Counsel drafts and reviews the policy. |
| Article 53(1)(d) training-data summary per Commission template | Disclosure | H | `training_data_summary_ref` | M | Plugin records reference. The Commission template format governs. |

## Article 54: Authorised representatives for non-EU providers

| Provision | Theme | Class | Plugin field | Leverage | Notes |
|---|---|---|---|---|---|
| Article 54(1) designation requirement | Operational gate | A | `provider_role`, `authorised_representative` | H | Plugin returns `non-compliant` when role is `non-eu-provider-without-representative`. |
| Article 54(1) representative content (name, MS, contact) | Content validation | A | `authorised_representative` | H | Plugin checks required fields. |

## Article 55: Systemic-risk additional obligations

| Provision | Theme | Class | Plugin field | Leverage | Notes |
|---|---|---|---|---|---|
| Article 55(1)(a) state-of-the-art model evaluation | Documentation | H | `systemic_risk_artifacts.model_evaluation_ref` | M | Adequacy of methodology is judgment. Plugin records reference. |
| Article 55(1)(a) adversarial testing | Documentation | H | `systemic_risk_artifacts.adversarial_testing_ref` | M | Same. |
| Article 55(1)(b) systemic-risk assessment and mitigation | Documentation | H | `systemic_risk_artifacts.systemic_risk_assessment_ref` | M | Plugin records reference. |
| Article 55(1)(c) serious-incident tracking and reporting | Documentation + filing | H | `systemic_risk_artifacts.serious_incidents_log_ref` | H | Plugin records the log reference. Filing flows through `incident-reporting`. |
| Article 55(1)(d) cybersecurity protection | Documentation | H | `systemic_risk_artifacts.cybersecurity_measures_ref` | M | Plugin records reference. |
| Article 55(2) Code of Practice adherence | Compliance presumption | A | `code_of_practice_status` | H | Plugin echoes enum; surfaces presumption note when `signed-full`. |

## Composition with sibling plugins

### Serious-incident filing: `incident-reporting`

| Signal | Direction | Usage |
|---|---|---|
| Article 55(1)(c) incidents log present | gpai-obligations-tracker to incident-reporting | When a serious incident is detected, the practitioner invokes `incident-reporting` with EU jurisdiction to compute the Article 73 deadline. |
| `severity` from incident description | incident-reporting | Drives the 2/10/15-day clock. |

### Substantial-modification analysis: `supplier-vendor-assessor`

| Signal | Direction | Usage |
|---|---|---|
| Downstream-integrator posture emitted | gpai-obligations-tracker to supplier-vendor-assessor | Caller invokes `supplier-vendor-assessor` with `deployer_modification_note` to assess whether modification triggers Article 25(1)(c) re-classification. |

### Cross-framework coverage: `crosswalk-matrix-builder`

| EU AI Act provision | Crosswalk relationship | Target |
|---|---|---|
| Article 53(1)(a) | satisfies (high) | ISO Clause 7.5 + A.6.2.7 |
| Article 53(1)(c) | no-mapping (high) | ISO 42001 has no copyright control |
| Article 53(1)(d) | partial-satisfaction (medium) | ISO A.7.2 + A.7.5 |
| Article 55(1)(a) | partial-satisfaction (high) | ISO A.6.2.4 + NIST MEASURE 2.5/2.7 |
| Article 55(1)(c) | partial-satisfaction (high) | ISO Clause 10.2 |

## Counts

- Automatable provisions (A): 5.
- Hybrid provisions (H): 11.
- Judgment-bound provisions (J): 3.

Automation coverage is high for systemic-risk classification, reference presence, and the authorised-representative check. Substantive content (Annex XI documentation body, copyright policy text, evaluation methodology) remains outside the plugin boundary.
