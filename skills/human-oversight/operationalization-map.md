# Human Oversight Operationalization Map

Working document for the `human-oversight` skill. Maps each Article 14(4) ability and each override-control category to the plugin that operationalizes it and to sibling plugins consumed at runtime. Companion to [SKILL.md](SKILL.md).

## Methodology

For each oversight requirement, four dimensions are captured.

**Operationalizability class.**

- **A (automatable):** end-to-end automation is feasible. The plugin produces compliant output from structured input.
- **H (hybrid):** automation produces a draft or scaffold that a human must complete, review, or approve.
- **J (human judgment required):** the requirement is judgment-bound. Automation assists information gathering only.

**Artifact.** The concrete deliverable produced.

**Plugin.** The AIGovOps plugin that produces the artifact.

**Runtime consumers.** Sibling plugins that consume the artifact during operation.

## Article 14(4) abilities

| Ability | Citation | Class | Artifact | Producer plugin | Runtime consumers |
|---|---|---|---|---|---|
| (a) understand capacities and limitations | EU AI Act, Article 14, Paragraph 4(a) | H | ability-row plus model card reference | `human-oversight-designer` | `aisia-runner` (impact assessment), `role-matrix-generator` (training reference) |
| (b) awareness of automation bias | EU AI Act, Article 14, Paragraph 4(b) | H | ability-row plus bias-mitigation rows | `human-oversight-designer` | `aisia-runner`, `metrics-collector` (bias drift metrics) |
| (c) correctly interpret output | EU AI Act, Article 14, Paragraph 4(c) | H | ability-row plus interpretability evidence | `human-oversight-designer` | `aisia-runner` |
| (d) decide not to use, disregard, override, or reverse | EU AI Act, Article 14, Paragraph 4(d) | A | override-control row (control_type=delay-and-review or human-approval-required) | `human-oversight-designer` | `nonconformity-tracker` (override events), `audit-log-generator` |
| (e) intervene or stop | EU AI Act, Article 14, Paragraph 4(e) | A | override-control row (control_type=stop-button or kill-switch) | `human-oversight-designer` | `nonconformity-tracker`, `incident-reporting` |

## Article 14(5) biometric dual-assignment

| Requirement | Citation | Class | Artifact | Producer plugin | Runtime consumers |
|---|---|---|---|---|---|
| Two natural persons with authority and competence verify each remote biometric identification result | EU AI Act, Article 14, Paragraph 5 | A | biometric-dual-assignment-check | `human-oversight-designer` | `audit-log-generator`, `incident-reporting` |

## Override-control categories

| Control type | Citation | Class | Producer plugin | Runtime consumers |
|---|---|---|---|---|
| stop-button | EU AI Act, Article 14, Paragraph 4(e); MANAGE 2.3 | A | `human-oversight-designer` | `incident-reporting`, `nonconformity-tracker` |
| kill-switch | EU AI Act, Article 14, Paragraph 4(e); MANAGE 2.3 | A | `human-oversight-designer` | `incident-reporting`, `nonconformity-tracker` |
| delay-and-review | EU AI Act, Article 14, Paragraph 4(d); MANAGE 2.3 | A | `human-oversight-designer` | `audit-log-generator`, `nonconformity-tracker` |
| human-approval-required | EU AI Act, Article 14, Paragraph 4(d); MANAGE 2.3 | A | `human-oversight-designer` | `audit-log-generator` |

## ISO/IEC 42001:2023 Annex A controls A.9.2 to A.9.4

| Control | Citation | Class | Artifact | Producer plugin |
|---|---|---|---|---|
| A.9.2 Processes for responsible use of AI systems | ISO/IEC 42001:2023, Annex A, Control A.9.2 | H | human-oversight-design | `human-oversight-designer` |
| A.9.3 Objectives for responsible use | ISO/IEC 42001:2023, Annex A, Control A.9.3 | H | objectives section of human-oversight-design | `human-oversight-designer` |
| A.9.4 Intended use of the AI system | ISO/IEC 42001:2023, Annex A, Control A.9.4 | H | intended-use echo within human-oversight-design | `human-oversight-designer` |

## Cross-plugin composition

A complete human-oversight implementation chains the following plugins.

1. `high-risk-classifier` produces the `risk_tier` that determines whether Article 14 applies.
2. `role-matrix-generator` produces the role-to-authority mapping consumed as `assigned_oversight_personnel` input.
3. `human-oversight-designer` produces the design artifact.
4. `aisia-runner` (optional) emits an impact section per stakeholder consuming the design as evidence for the human-oversight impact dimension.
5. `audit-log-generator` records design approval and operational override events.
6. `nonconformity-tracker` records overrides exercised that constitute nonconformities.
7. `incident-reporting` routes safety incidents triggered through the override paths to regulators.

## Open questions

- Real-time decision contexts (autonomous vehicles, medical devices) may require sub-second override latency. The plugin's 30-second default flag is a conservative high-risk-system warning; sector-specific tightening is left to the practitioner.
- Article 14(5) two-person verification: the plugin counts authoritative-authority-level personnel. Whether the two persons must operate sequentially or independently is left to operational policy.
- Annual training refresh: the plugin emits a recommendation warning when `annual_refresh=False`. Sector practice in healthcare and financial services often requires more frequent refresh (semi-annual or quarterly); the plugin records the documented cadence rather than enforcing one.
