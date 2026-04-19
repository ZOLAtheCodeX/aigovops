---
name: cascade-impact
version: 0.1.0
description: >
  Cascade impact analysis for AI governance programs. When a trigger event
  occurs (regulatory change, risk register update, completed action,
  threshold breach, serious incident), this skill computes the tree of
  downstream actions that should fire across the AIGovOps plugin
  catalogue, with per-action authority, citations, and hop-count
  depth. Operationalizes the AIGovOS "cascade" concept as a declarative
  YAML registry served by the cascade-impact-analyzer plugin.
frameworks:
  - ISO/IEC 42001:2023
  - NIST AI Risk Management Framework 1.0
  - Regulation (EU) 2024/1689 (EU AI Act)
  - Colorado SB 24-205 (Colorado AI Act)
  - NYC Local Law 144 of 2021 (AEDT)
tags:
  - ai-governance
  - cascade
  - event-driven
  - iso42001
  - nist-ai-rmf
  - eu-ai-act
  - action-executor
  - pdca
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill operationalizes the cascade concept: when a trigger event occurs in an AI governance program, which plugins must re-run, which stakeholders must be notified, and with what authority posture. The data surface is a declarative YAML registry (`plugins/cascade-impact-analyzer/data/cascade_schema.yaml`) served by the `cascade-impact-analyzer` plugin via one canonical entry point (`analyze_cascade`). The registry seeds 22 cascades spanning the core AIGovOps lifecycle triggers.

Cascade analysis is the missing link between detection and action. The AIGovOps catalogue already contains plugins that detect governance-relevant state changes (framework-monitor, metrics-collector, risk-register-builder, gap-assessment, certification-readiness, bias-evaluator, post-market-monitoring, evidence-bundle-packager) and plugins that produce implementation artifacts in response (soa-generator, aisia-runner, incident-reporting, management-review-packager, nonconformity-tracker). The cascade registry names the edges between detectors and producers, with citations, authority posture, and a depth cap.

Primary users are ISO/IEC 42001 Lead Implementers running continuous-improvement loops under Clause 10.1, program managers wiring detection-to-action routing, and agent-runtime operators configuring the `action-executor` plugin (not yet shipped) that will dispatch cascade outputs under human-in-the-loop or take-resolving-action authority.

## Scope

**In scope.** Cascade trigger-to-action mapping across the 32-plugin AIGovOps catalogue. Specifically:

- 22 seeded cascades covering framework changes, AI system inventory updates, high-risk classification, risk register updates, SoA status transitions, gap detection, certification readiness verdicts, metrics threshold breaches, nonconformity closures, serious incidents, post-market dimension drift, supplier changes, internal audit findings, management review closure, GPAI systemic-risk designation, human-oversight ability gaps, disparate-impact detection, evidence bundle packing, and evidence bundle signature mismatches.
- Three authority modes (`ask-permission`, `take-resolving-action`, `autonomous`) governing dispatch posture.
- Three priority bands (`high`, `medium`, `low`) governing flat-action-list ordering.
- Recursive cascade chaining up to `DEFAULT_MAX_DEPTH` (5) hops.
- Depth caps at the action level via `max_hops_further`.
- Authority-filter preview mode.

**Out of scope.** The cascade registry does not:

- Dispatch actions. The action-executor plugin (not yet shipped) consumes the output and performs dispatch.
- Evaluate condition guards. `condition` and `trigger_conditions` are carried forward as free-text. A future integration with the applicability-checker condition evaluator may change this.
- Orchestrate PDCA cycles. A future PDCA orchestrator (not yet shipped) will consume cascade outputs to produce sequenced Plan-Do-Check-Act loops.
- Invent cascades. The plugin refuses to surface any cascade not declared in `cascade_schema.yaml`.

## Framework Reference

**Authoritative sources.**

- ISO/IEC 42001:2023, Information technology, Artificial intelligence, Management system: https://www.iso.org/standard/81230.html. Clause 10.1 continual improvement anchors the cascade pattern. Clause 9.3 management review consumes cascade outputs. Clause 10.2 nonconformity and corrective action is a primary cascade target.
- NIST AI Risk Management Framework 1.0: https://www.nist.gov/itl/ai-risk-management-framework. MEASURE functions (2.5, 2.7, 2.11) anchor the metrics-based triggers; MANAGE 4.1 and 4.2 anchor the post-market and nonconformity triggers.
- Regulation (EU) 2024/1689 (EU AI Act): https://eur-lex.europa.eu/eli/reg/2024/1689/oj. Article 27 FRIA, Article 72 post-market monitoring, Article 73 serious-incident reporting, Article 55 GPAI systemic-risk obligations.
- Colorado SB 24-205 (Colorado AI Act): https://leg.colorado.gov/bills/sb24-205. Section 6-1-1701 consequential decision scope triggers the colorado-ai-act-compliance re-run.
- NYC Local Law 144 of 2021 and DCWP AEDT Final Rule: https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/. Section 5-301 four-fifths rule triggers the nyc-ll144-audit-packager re-run when the system is in scope for Local Law 144.

## Operationalizable Controls

One Tier 1 operationalization. The skill is an infrastructure skill: it serves the other skills and plugins in the AIGovOps catalogue. The operationalization is the per-trigger cascade pattern and the per-consumer-plugin integration roadmap.

### T1.1 Trigger-to-action cascade analysis

Class: A. Artifact: cascade-impact analysis dict with cascade tree, flat action list, summary counts, and citations. Leverage: H. Consumer: the action-executor plugin (not yet shipped) plus every AIGovOps plugin named as a `target_plugin` in `cascade_schema.yaml`.

**Requirement summary.** The cascade registry supports every plugin in the catalogue that must answer the question "when event X occurs, what fires next in my governance program". The canonical query pattern is:

```python
from plugins.cascade_impact_analyzer import plugin

result = plugin.analyze_cascade({
    "trigger_event": {
        "event": "risk-register.risk-added",
        "source_plugin": "risk-register-builder",
        "context_data": {"risk_id": "R-2026-042"},
    },
})
```

The consumer reads `result["flat_action_list"]` for the priority-ordered sequence of actions and `result["cascade_tree"]` for the nested structure. Each node is self-describing: `cascade_id`, `hop_count`, `target_plugin`, `action_type`, `authority`, `rationale`, `citations`.

**Operationalization map (per consumer plugin).**

See `operationalization-map.md` in this directory for the per-trigger mapping to event emitters and consumers.

**Authority vocabulary.**

| Value | Semantics |
|---|---|
| `ask-permission` | Human-in-the-loop required before dispatch. The action-executor surfaces the proposal and waits. |
| `take-resolving-action` | Dispatch without prompting when the trigger condition is met. The action resolves a known governance obligation. |
| `autonomous` | Reserved. No seeded cascades use this value. Reserved for mechanical bookkeeping (log rotation). |

**Priority vocabulary.**

`high`, `medium`, `low`. Governs flat-action-list ordering. High-priority cascades surface their actions before medium before low. Within a priority band, actions are ordered by hop count ascending, then by target_plugin alphabetically.

**Input schema.**

See `plugins/cascade-impact-analyzer/plugin.py` and `plugins/cascade-impact-analyzer/README.md`. Required: `trigger_event` with `event`. Optional: `max_depth`, `authority_filter`, `severity`, `reviewed_by`.

**Output structure.**

Every result dict carries: `timestamp`, `agent_signature`, `trigger`, `matched_cascades`, `cascade_tree`, `flat_action_list`, `summary`, `citations`, `warnings`. `render_markdown` and `render_csv` produce the auditor-facing surfaces.

## Output Standards

Outputs produced under this skill meet the certification-grade quality bar in [STYLE.md](../../STYLE.md). Specifically:

- Every cascade carries at least one top-level citation in STYLE.md format.
- Every action carries at least one citation in STYLE.md format.
- No em-dashes (U+2014). No emojis. No hedging phrases.
- Unmatched triggers emit a warning. They do not fail the query.
- The plugin refuses to load any cascade with an unknown target_plugin, an invalid authority value, an invalid priority value, a missing citation, a non-STYLE.md citation prefix, an em-dash, a duplicate id, a duplicate event, or a self-cycle.

## Limitations

- The skill does not dispatch actions. The action-executor plugin (not yet shipped) is the dispatch layer.
- The skill does not evaluate condition guards. Conditions are carried forward as free-text for the action-executor or a future condition evaluator to interpret.
- The 22 seeded cascades cover the core AIGovOps lifecycle triggers. Jurisdiction-specific cascades (for example, per-state Colorado operative-date transitions, per-jurisdiction California instrument operative-date transitions) are out of scope for 0.1.0 and will be added as the catalogue matures.
- Runtime cycles in legitimate governance loops (gap to readiness to remediation back to gap) are broken via the `(cascade_id, target_plugin)` visited set. The plugin does not surface a warning when a cycle is broken; auditing cycle behavior is a separate information product.
- The 0.1.0 authority vocabulary treats `autonomous` as reserved. No seeded cascade uses it. Extending the catalogue to include mechanical bookkeeping cascades (log rotation, cache refresh) is deferred.
