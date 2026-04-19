# GenAI risk profile operationalization map

Per-risk cross-plugin relationships for the NIST AI 600-1 12-risk catalogue. Read with [SKILL.md](SKILL.md).

## Per-risk cross-plugin matrix

| risk_id | NIST AI RMF subcategories | Sibling plugins for evidence |
|---|---|---|
| `cbrn-information-capabilities` | GOVERN 1.1, MAP 1.1, MEASURE 2.6 | `gpai-obligations-tracker` (Article 55(1)(a) when EU systemic-risk); `incident-reporting` on materialisation. |
| `confabulation` | MEASURE 2.5, MEASURE 2.8 | `robustness-evaluator` for state-of-the-art evaluation evidence. |
| `dangerous-violent-hateful-content` | MAP 5.1, MANAGE 2.2 | `system-event-logger` for content-moderation telemetry; `incident-reporting` on materialisation. |
| `data-privacy` | MEASURE 2.10 | `data-register-builder` for training-data inventory; `gpai-obligations-tracker` Article 53(1)(d) summary; California AB 2013 + AB 1008 when `usa-ca` jurisdiction. |
| `environmental-impacts` | MEASURE 2.12 | `metrics-collector` for energy and compute telemetry; `gpai-obligations-tracker` Annex XI energy-consumption disclosure. |
| `harmful-bias-homogenization` | MEASURE 2.11 | `bias-evaluator` for fairness-metric evidence (NYC LL144 four-fifths rule, EU AI Act Article 10(4), Singapore MAS Veritas). |
| `human-ai-configuration` | MANAGE 2.3, MEASURE 3.3 | `human-oversight-designer` for Article 14 oversight design and operator-training assessment. |
| `information-integrity` | MEASURE 2.7, MEASURE 2.8 | `system-event-logger` for synthetic-content marking telemetry; EU AI Act Article 50(2) and 50(4) when `eu` jurisdiction; California SB 942 when `usa-ca`. |
| `information-security` | MEASURE 2.7 | `system-event-logger` for prompt-injection and jailbreak telemetry; `gpai-obligations-tracker` Article 55(1)(a) when EU systemic-risk. |
| `intellectual-property` | GOVERN 1.4, GOVERN 6.1 | `gpai-obligations-tracker` Article 53(1)(c) copyright policy; California AB 2013 when `usa-ca`. |
| `obscene-degrading-abusive-content` | MAP 5.1, MANAGE 2.2 | `system-event-logger` for content-moderation telemetry; `incident-reporting` on materialisation. |
| `value-chain-component-integration` | GOVERN 6.1, GOVERN 6.2 | `supplier-vendor-assessor` for upstream-provider review; `gpai-obligations-tracker` Article 55(1)(d) when EU systemic-risk. |

## Cross-reference contract

The plugin reads three optional artifact references via `cross_reference_refs`:

- `gpai_obligations_ref`: when present and jurisdiction includes `eu`, attaches Article 55(1)(a) and 55(1)(d) citations to `information-security` and `value-chain-component-integration` respectively.
- `supplier_assessment_ref`: surfaces in the `value-chain-component-integration` row's existing-mitigations narrative (the plugin does not auto-link; the practitioner cites the artifact path).
- `bias_evaluation_ref`: surfaces in the `harmful-bias-homogenization` row's existing-mitigations narrative.

## Composition pipeline

A typical end-to-end GenAI governance pipeline:

1. `ai-system-inventory-maintainer` records the system with `is_generative = True`.
2. `gpai-obligations-tracker` (when EU GPAI provider or downstream integrator) classifies systemic-risk and produces the Article 53 to 55 obligations record.
3. `bias-evaluator` runs the fairness evaluation.
4. `supplier-vendor-assessor` reviews each upstream GenAI dependency.
5. `system-event-logger` captures operational telemetry.
6. `genai-risk-register` (this skill) consolidates the per-risk evaluations with cross-references to the artifacts above.
7. On critical residual flag: `incident-reporting` for deadline-aware regulatory filing; `management-review-packager` for documented review.

## Distinction from the general risk register

The general [`risk-register-builder`](../../plugins/risk-register-builder/) operates over an ISO 42001 / NIST AI RMF taxonomy (bias, robustness, privacy, security, accountability, transparency, environmental). It applies to every AI system, generative or not. The two registers are not redundant: the general register is the certification-audit primary artifact for ISO 42001 Clause 6.1.2 and NIST MAP 4.1; the GenAI register is a supplementary artifact for systems that NIST AI 600-1 applies to. A practitioner with a mixed AI portfolio runs both.
