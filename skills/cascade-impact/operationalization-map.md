# cascade-impact operationalization map

How each trigger in `plugins/cascade-impact-analyzer/data/cascade_schema.yaml` maps to the event emitter (source plugin) and the consumer plugins (target plugins). The cascade-impact-analyzer is an infrastructure plugin: it holds the declarative trigger-to-action registry, and the action-executor plugin (not yet shipped) consumes the output to dispatch actions under the declared authority modes.

Integration status is `deferred` for every consumer plugin at the 0.1.0 release. No plugin currently invokes `cascade_impact_analyzer.plugin.analyze_cascade` at runtime. This document is the future-work roadmap. Integration lands per-plugin as each plugin reaches a minor-version increment that justifies the additional dependency.

## framework-monitor.change-detected

**Emitter.** `framework-monitor` (not yet shipped). Detects deltas in tracked framework publications against the last known canonical version.

**Consumers.** `applicability-checker` (take-resolving-action, re-run), `management-review-packager` (ask-permission, notify).

**Citation family.** ISO/IEC 42001:2023, Clause 10.1 (continual improvement). ISO/IEC 42001:2023, Clause 9.3.2 (management review inputs).

**Integration status.** `deferred`. Framework-monitor is a candidate plugin for a future catalogue minor-version increment.

## ai-system-inventory.system-added

**Emitter.** `ai-system-inventory-maintainer` (shipped). Fires when a new AI system is added to the inventory.

**Consumers.** `applicability-checker`, `high-risk-classifier`, `risk-register-builder`, `data-register-builder`, `role-matrix-generator` (all take-resolving-action, re-run).

**Citation family.** ISO/IEC 42001:2023, Clause 4.3 (scope). EU AI Act, Article 6 (high-risk classification). ISO/IEC 42001:2023, Annex A, Control A.7.2 (data resources). ISO/IEC 42001:2023, Clause 5.3 (roles).

**Integration status.** `deferred`. `ai-system-inventory-maintainer/0.1.0` does not emit events. Integration targets `ai-system-inventory-maintainer/0.2.0`.

## high-risk-classifier.eu-annex-iii-match

**Emitter.** `high-risk-classifier` (shipped). Fires when a system matches one of the eight EU AI Act Annex III high-risk use-case categories.

**Consumers.** `aisia-runner` (take-resolving-action, re-run), `post-market-monitoring` (take-resolving-action, re-run).

**Citation family.** EU AI Act, Article 27 (FRIA). EU AI Act, Article 72 (post-market monitoring plan). EU AI Act, Annex III.

**Integration status.** `deferred`. `high-risk-classifier/0.1.0` does not emit events. Integration targets `high-risk-classifier/0.2.0`.

## high-risk-classifier.colorado-sb205-in-scope

**Emitter.** `high-risk-classifier` (shipped). Fires when a system makes a consequential decision under Colorado SB 205 Section 6-1-1701.

**Consumers.** `colorado-ai-act-compliance` (take-resolving-action, re-run).

**Citation family.** Colorado SB 205, Section 6-1-1701(3). Colorado SB 205, Section 6-1-1702(2). Colorado SB 205, Section 6-1-1703(4)(b).

**Integration status.** `deferred`. Targets `high-risk-classifier/0.2.0`.

## risk-register.risk-added

**Emitter.** `risk-register-builder` (shipped). Fires when a new risk row is added.

**Consumers.** `soa-generator`, `gap-assessment`, `certification-readiness` (all take-resolving-action, re-run).

**Citation family.** ISO/IEC 42001:2023, Clause 6.1.2 (AI risk assessment). ISO/IEC 42001:2023, Clause 6.1.3 (SoA). ISO/IEC 42001:2023, Clause 9.3 (management review).

**Integration status.** `deferred`. Targets `risk-register-builder/0.2.0`.

## risk-register.residual-score-exceeds-threshold

**Emitter.** `risk-register-builder` (shipped).

**Consumers.** `incident-reporting` (ask-permission), `management-review-packager` (ask-permission).

**Citation family.** ISO/IEC 42001:2023, Clause 6.1.4 (risk treatment). ISO/IEC 42001:2023, Clause 10.2. ISO/IEC 42001:2023, Clause 9.3.2.

**Integration status.** `deferred`.

## soa-generator.control-status-changed

**Emitter.** `soa-generator` (shipped). Fires when an Annex A control transitions status.

**Consumers.** `gap-assessment`, `certification-readiness`.

**Citation family.** ISO/IEC 42001:2023, Clause 6.1.3. ISO/IEC 42001:2023, Clause 6.1.2. ISO/IEC 42001:2023, Clause 9.3.

**Integration status.** `deferred`.

## gap-assessment.new-gap-detected

**Emitter.** `gap-assessment` (shipped).

**Consumers.** `certification-readiness` (ask-permission, trigger-downstream to a future certification-path-planner).

**Citation family.** ISO/IEC 42001:2023, Clause 6.1.2. ISO/IEC 42001:2023, Clause 9.3.

**Integration status.** `deferred`. The certification-path-planner plugin is a parallel track and not yet shipped.

## certification-readiness.not-ready

**Emitter.** `certification-readiness` (shipped).

**Consumers.** `gap-assessment` (ask-permission, trigger-downstream for remediation plan).

**Citation family.** ISO/IEC 42001:2023, Clause 9.3. ISO/IEC 42001:2023, Clause 10.1.

**Integration status.** `deferred`.

## certification-readiness.ready-with-conditions

**Emitter.** `certification-readiness` (shipped).

**Consumers.** `management-review-packager` (ask-permission, notify).

**Citation family.** ISO/IEC 42001:2023, Clause 9.3. ISO/IEC 42001:2023, Clause 9.3.2.

**Integration status.** `deferred`.

## metrics-collector.threshold-breach

**Emitter.** `metrics-collector` (shipped).

**Consumers.** `nonconformity-tracker` (take-resolving-action, re-run to open a nonconformity), `incident-reporting` (ask-permission, evaluate), `post-market-monitoring` (take-resolving-action, trigger-downstream).

**Citation family.** MEASURE 2.7. ISO/IEC 42001:2023, Clause 10.2. EU AI Act, Article 73. EU AI Act, Article 72.

**Integration status.** `deferred`.

## nonconformity-tracker.closed

**Emitter.** `nonconformity-tracker` (shipped).

**Consumers.** `management-review-packager` (take-resolving-action, re-run; closed nonconformities are mandatory 9.3.2 inputs), `audit-log-generator` (take-resolving-action, log).

**Citation family.** ISO/IEC 42001:2023, Clause 10.2. ISO/IEC 42001:2023, Clause 9.3.2. ISO/IEC 42001:2023, Clause 7.5.3.

**Integration status.** `deferred`.

## incident-reporting.serious-incident

**Emitter.** `incident-reporting` (shipped).

**Consumers.** `management-review-packager` (ask-permission), `supplier-vendor-assessor` (ask-permission), `evidence-bundle-packager` (ask-permission, pack bundle for regulator submission).

**Citation family.** EU AI Act, Article 73. ISO/IEC 42001:2023, Clause 9.3.2. ISO/IEC 42001:2023, Annex A, Control A.10.3.

**Integration status.** `deferred`.

## post-market-monitoring.dimension-drift

**Emitter.** `post-market-monitoring` (shipped).

**Consumers.** `bias-evaluator` (condition: dimension is fairness-related), `robustness-evaluator` (condition: dimension is robustness-related), `risk-register-builder` (re-evaluate).

**Citation family.** EU AI Act, Article 72. MEASURE 2.7. MEASURE 2.11. ISO/IEC 42001:2023, Clause 6.1.4.

**Integration status.** `deferred`.

## supplier-vendor-assessor.vendor-changed

**Emitter.** `supplier-vendor-assessor` (shipped).

**Consumers.** `risk-register-builder`, `soa-generator`, `audit-log-generator`.

**Citation family.** EU AI Act, Article 25. ISO/IEC 42001:2023, Annex A, Control A.10.2. ISO/IEC 42001:2023, Annex A, Control A.10.3. ISO/IEC 42001:2023, Clause 7.5.3.

**Integration status.** `deferred`.

## internal-audit-planner.finding-raised

**Emitter.** `internal-audit-planner` (shipped).

**Consumers.** `nonconformity-tracker` (take-resolving-action, open), `management-review-packager` (take-resolving-action, trigger-downstream, add-input).

**Citation family.** ISO/IEC 42001:2023, Clause 9.2. ISO/IEC 42001:2023, Clause 10.2. ISO/IEC 42001:2023, Clause 9.3.2.

**Integration status.** `deferred`.

## management-review-packager.review-closed

**Emitter.** `management-review-packager` (shipped).

**Consumers.** `audit-log-generator` (take-resolving-action, log), `risk-register-builder` (ask-permission, update-if-needed).

**Citation family.** ISO/IEC 42001:2023, Clause 9.3. ISO/IEC 42001:2023, Clause 9.3.3. ISO/IEC 42001:2023, Clause 7.5.3.

**Integration status.** `deferred`.

## gpai-obligations-tracker.systemic-risk-designated

**Emitter.** `gpai-obligations-tracker` (shipped).

**Consumers.** `incident-reporting` (ask-permission, setup-channel for Article 55(1)(c)), `supplier-vendor-assessor` (ask-permission, re-evaluate downstream integrators).

**Citation family.** EU AI Act, Article 51. EU AI Act, Article 55. EU AI Act, Article 55, Paragraph 1, Point (c).

**Integration status.** `deferred`.

## human-oversight-designer.ability-gap

**Emitter.** `human-oversight-designer` (shipped).

**Consumers.** `risk-register-builder` (take-resolving-action, open-risk), `management-review-packager` (ask-permission, notify).

**Citation family.** EU AI Act, Article 14. ISO/IEC 42001:2023, Clause 9.3.2.

**Integration status.** `deferred`.

## bias-evaluator.disparate-impact-detected

**Emitter.** `bias-evaluator` (shipped).

**Consumers.** `nonconformity-tracker` (ask-permission), `incident-reporting` (ask-permission), `nyc-ll144-audit-packager` (ask-permission, condition: `jurisdiction == 'usa-nyc'`).

**Citation family.** MEASURE 2.11. NYC LL144. NYC LL144 Final Rule, Section 5-301. ISO/IEC 42001:2023, Clause 10.2.

**Integration status.** `deferred`.

## evidence-bundle-packager.bundle-packed

**Emitter.** `evidence-bundle-packager` (shipped).

**Consumers.** `certification-readiness` (take-resolving-action, re-assess).

**Citation family.** ISO/IEC 42001:2023, Clause 7.5.3. ISO/IEC 42001:2023, Clause 9.3.

**Integration status.** `deferred`.

## evidence-bundle-packager.signature-mismatch

**Emitter.** `evidence-bundle-packager` (shipped).

**Consumers.** `incident-reporting` (ask-permission), `management-review-packager` (ask-permission).

**Citation family.** ISO/IEC 42001:2023, Clause 7.5.3. ISO/IEC 42001:2023, Clause 10.2. ISO/IEC 42001:2023, Clause 9.3.2.

**Integration status.** `deferred`.
