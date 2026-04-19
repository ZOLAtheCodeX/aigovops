# gpai-obligations-tracker

Operationalizes EU AI Act Articles 51 to 55 (general-purpose AI models, GPAI). The plugin distinguishes the universal Article 53 obligations that attach to every GPAI provider from the additional Article 55 obligations that attach only when the model has systemic risk under Article 51, wires the Article 54 authorised-representative check for non-EU providers, and emits a downstream-integrator posture for organisations integrating an upstream GPAI without meeting the substantial-modification re-classification threshold of Article 25(1)(c).

## Status

0.1.0. Phase 4 implementation. Closes the GPAI gap in the eu-ai-act operationalization map.

## Design stance

The plugin does NOT compute training compute, does NOT verify external documentation URLs, and does NOT make the legal determination that a copyright policy or training-data summary is adequate. It validates inputs, applies deterministic rules over the GPAI obligation surface, attaches citations, and surfaces gaps as warnings for practitioner action.

## Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `model_description` | dict | yes | `model_name` (required), `model_family`, `parameter_count`, `training_compute_flops` (number or `"unknown"`), `training_data_types`, `training_data_jurisdictions`, `modality`, `release_date`, `model_version`, `base_model_ref`. |
| `provider_role` | enum | yes | One of `eu-established-provider`, `non-eu-provider-with-representative`, `non-eu-provider-without-representative`, `downstream-integrator`. |
| `authorised_representative` | dict | conditional | Required when provider_role is `non-eu-provider-with-representative`. Fields: `name`, `eu_member_state`, `contact`. |
| `technical_documentation_ref` | string | no | Path or URL to Annex XI technical documentation. |
| `downstream_integrator_docs_ref` | string | no | Path or URL to Article 53(1)(b) documentation. |
| `copyright_policy_ref` | string | no | Path or URL to Article 53(1)(c) copyright policy. |
| `training_data_summary_ref` | string | no | Path or URL to Article 53(1)(d) training-data summary. |
| `designated_systemic_risk` | bool | no | Default False. True when the Commission has designated the model under Article 52. |
| `self_declared_below_threshold` | bool | no | Default False. Practitioner-confirmation flag for sub-threshold compute. |
| `systemic_risk_artifacts` | dict | conditional | Required when systemic-risk applies. Fields: `model_evaluation_ref`, `adversarial_testing_ref`, `systemic_risk_assessment_ref`, `cybersecurity_measures_ref`, `serious_incidents_log_ref`. |
| `code_of_practice_status` | enum | no | One of `signed-full`, `signed-partial`, `not-signed`, `not-applicable`. |
| `enrich_with_crosswalk` | bool | no | Default True. |
| `reviewed_by` | string | no | Reviewer identity. |

## Rule tables

### Systemic-risk classification (Article 51)

| Condition | Status | Citation |
|---|---|---|
| `designated_systemic_risk` is True | `designated-systemic-risk` | Article 52 |
| `training_compute_flops >= 10^25` | `presumed-systemic-risk` | Article 51, Paragraph 1, Point (a) |
| `training_compute_flops < 10^25` | `not-systemic-risk` (with confirmation warning) | Article 51, Paragraph 1 |
| `training_compute_flops` unknown or missing | `requires-assessment` (with warning) | Article 51, Paragraph 1; Annex XIII |

### Article 53 universal obligations

| Obligation | Required input | Status when reference present |
|---|---|---|
| Article 53(1)(a) Technical documentation per Annex XI | `technical_documentation_ref` | `present` |
| Article 53(1)(b) Documentation for downstream integrators | `downstream_integrator_docs_ref` | `present` |
| Article 53(1)(c) Copyright compliance policy | `copyright_policy_ref` | `present` |
| Article 53(1)(d) Training-data summary | `training_data_summary_ref` | `present` |

Missing references emit `missing-warning` status and a register-level warning.

### Article 54 authorised representative

| `provider_role` | `art_54_status` |
|---|---|
| `eu-established-provider` | `not-applicable` |
| `downstream-integrator` | `not-applicable` |
| `non-eu-provider-with-representative` | `satisfied` (when authorised_representative complete) or `incomplete` |
| `non-eu-provider-without-representative` | `non-compliant` (blocking warning emitted) |

### Article 55 systemic-risk additional obligations

Emitted only when systemic-risk classification is `presumed-systemic-risk` or `designated-systemic-risk` AND provider_role is not `downstream-integrator`.

| Obligation | Required references | Status |
|---|---|---|
| Article 55(1)(a) Model evaluation and adversarial testing | `model_evaluation_ref` AND `adversarial_testing_ref` | `present`, `partial`, or `missing` |
| Article 55(1)(b) Systemic-risk assessment and mitigation | `systemic_risk_assessment_ref` | `present` or `missing` |
| Article 55(1)(c) Serious incident tracking | `serious_incidents_log_ref` | `present` or `missing` |
| Article 55(1)(d) Cybersecurity measures | `cybersecurity_measures_ref` | `present` or `missing` |
| Article 55(2) Code of Practice adherence | `code_of_practice_status` | echoed enum value (compliance presumption note when `signed-full`) |

## Outputs

Structured dict with `timestamp`, `agent_signature`, `framework`, `model_description_echo`, `provider_role`, `systemic_risk_status`, `art_53_obligations`, `art_54_status`, `art_55_obligations` (when applicable), `downstream_integrator_posture` (when applicable), `code_of_practice_status`, `citations`, `cross_framework_citations` (when enriched), `warnings`, `summary`, `reviewed_by`.

Three renderers: `assess_gpai_obligations`, `render_markdown`, `render_csv`.

## Example

```python
import plugin

result = plugin.assess_gpai_obligations({
    "model_description": {
        "model_name": "ExampleLM-Foundation",
        "model_family": "ExampleLM",
        "parameter_count": "70B",
        "training_compute_flops": 3e25,
        "modality": "text",
    },
    "provider_role": "non-eu-provider-with-representative",
    "authorised_representative": {
        "name": "EU Rep GmbH",
        "eu_member_state": "DE",
        "contact": "rep@example.eu",
    },
    "technical_documentation_ref": "/docs/annex-xi.md",
    "downstream_integrator_docs_ref": "/docs/integrator-guide.md",
    "copyright_policy_ref": "/policies/copyright.md",
    "training_data_summary_ref": "/docs/training-data-summary.md",
    "systemic_risk_artifacts": {
        "model_evaluation_ref": "/eval/sota.json",
        "adversarial_testing_ref": "/eval/adversarial.md",
        "systemic_risk_assessment_ref": "/risk/sra.md",
        "cybersecurity_measures_ref": "/security/measures.md",
        "serious_incidents_log_ref": "/ops/incidents.log",
    },
    "code_of_practice_status": "signed-full",
})
print(plugin.render_markdown(result))
```

## Anti-hallucination invariants

1. The plugin does not verify external URLs. A reference is recorded as `present` if the input string is non-empty; the practitioner is responsible for confirming the referenced document exists, is current, and meets the underlying obligation.
2. The plugin does not estimate `training_compute_flops`. If the value is unknown or non-numeric, `systemic_risk_status` is `requires-assessment`.
3. The plugin does not assign Article 55 obligations to downstream integrators. Substantial-modification re-classification under Article 25(1)(c) is out of scope; refer to `supplier-vendor-assessor`.
4. The plugin does not legally adjudicate Code of Practice adequacy. It echoes the input value and notes the Article 55(2) presumption when `signed-full`.

## Composition with other plugins

- `incident-reporting` for Article 55(1)(c) serious-incident filing under Article 73 (the deadline-aware downstream of the GPAI tracker's incident-tracking obligation).
- `supplier-vendor-assessor` for substantial-modification analysis under Article 25(1)(c) when a downstream integrator's modifications are material.
- `crosswalk-matrix-builder` for cross-framework coverage of Article 53(1)(a) (ISO Clause 7.5 + A.6.2.7), Article 53(1)(d) (ISO A.7.2 + A.7.5), Article 55(1)(a) (ISO A.6.2.4 + NIST MEASURE 2.5/2.7), and Article 55(1)(c) (ISO Clause 10.2).

## Citation formats

All citations follow [STYLE.md](../../STYLE.md). Article 53(1)(a)-style references use the form `EU AI Act, Article 53, Paragraph 1, Point (a)`.
