# cascade-impact-analyzer

Operationalizes the AIGovOps cascade concept. Given a trigger event (regulatory change, risk register update, completed action, threshold breach, serious incident), computes the tree of downstream actions that should fire across the AIGovOps plugin catalogue.

The plugin is data-driven. The cascade registry lives in `data/cascade_schema.yaml`. Every cascade names a trigger event, the downstream actions that fire from it, the authority each action carries, and the citations that justify the cascade's existence. The plugin does not invent cascades and does not dispatch actions. It produces an auditable action tree that a future `action-executor` plugin can consume.

See `data/SCHEMA.md` for the cascade schema reference.

## Output artifact

A cascade-impact analysis dict with:

- `timestamp`: ISO 8601 UTC.
- `agent_signature`: `cascade-impact-analyzer/0.1.0`.
- `trigger`: the trigger event that was analyzed.
- `matched_cascades`: list of cascade ids that matched the trigger.
- `cascade_tree`: nested structure of action nodes with children.
- `flat_action_list`: linearized, priority-ordered list of actions with hop counts.
- `summary`: aggregate counts by authority, by target plugin, and max depth reached.
- `citations`: aggregated citations from every surfaced node.
- `warnings`: content gaps (for example, no cascade for the trigger).

## Inputs

Top-level input dict:

| Field | Required | Meaning |
|---|---|---|
| `trigger_event` | yes | Dict with `event` (required), `source_plugin` (optional), `context_data` (optional dict). |
| `max_depth` | no | Recursion cap on cascade chaining. Default `DEFAULT_MAX_DEPTH` (5). |
| `authority_filter` | no | List of authority modes (`ask-permission`, `take-resolving-action`, `autonomous`) to include. Actions whose authority is not in the filter are dropped from the tree and the flat list. |
| `severity` | no | Event severity: `info`, `warning`, `critical`. Default `info`. Carried forward in output. |
| `reviewed_by` | no | Reviewer name. |

## Example

```python
from plugins.cascade_impact_analyzer import plugin

result = plugin.analyze_cascade({
    "trigger_event": {
        "event": "risk-register.risk-added",
        "source_plugin": "risk-register-builder",
    },
})

print(result["summary"])
# {'total_actions': 3, 'by_authority': {'take-resolving-action': 3},
#  'by_target_plugin': {'soa-generator': 1, 'gap-assessment': 1,
#  'certification-readiness': 1}, 'max_depth_reached': 0}

print(plugin.render_markdown(result))
```

## Public API

| Function | Purpose |
|---|---|
| `analyze_cascade(inputs) -> dict` | Canonical entry point. |
| `load_cascade_schema() -> dict` | Load and validate `data/cascade_schema.yaml`. Returns `{cascades, by_event}`. |
| `render_markdown(analysis) -> str` | Markdown rendering for audit evidence. |
| `render_csv(analysis) -> str` | CSV rendering. One row per action in the flat list. |

## Authority vocabulary

| Value | Semantics |
|---|---|
| `ask-permission` | Human-in-the-loop required before dispatch. |
| `take-resolving-action` | Dispatch without prompting when the trigger condition is met. |
| `autonomous` | Reserved. No seeded cascades use this value. |

## Seeded cascades

22 cascades at 0.1.0 cover the core AIGovOps lifecycle triggers: framework changes, AI system inventory updates, high-risk classification, risk register updates, SoA status changes, gap detection, certification readiness verdicts, metrics threshold breaches, nonconformity closures, serious incidents, post-market drift, supplier changes, internal audit findings, management review closure, GPAI systemic-risk designation, human-oversight ability gaps, disparate-impact detection, evidence bundle packing, and evidence bundle signature mismatches.

See `data/cascade_schema.yaml` for the canonical list.

## Rule table

| Event | Priority | Downstream targets (hop 0) | Citation family |
|---|---|---|---|
| `framework-monitor.change-detected` | high | applicability-checker, management-review-packager | ISO 42001 Clause 10.1 |
| `ai-system-inventory.system-added` | high | applicability-checker, high-risk-classifier, risk-register-builder, data-register-builder, role-matrix-generator | ISO 42001 Clause 4.3 |
| `high-risk-classifier.eu-annex-iii-match` | high | aisia-runner, post-market-monitoring | EU AI Act Article 27, Article 72 |
| `risk-register.risk-added` | high | soa-generator, gap-assessment, certification-readiness | ISO 42001 Clause 6.1.2 |
| `metrics-collector.threshold-breach` | high | nonconformity-tracker, incident-reporting, post-market-monitoring | MEASURE 2.7 |
| `incident-reporting.serious-incident` | high | management-review-packager, supplier-vendor-assessor, evidence-bundle-packager | EU AI Act Article 73 |
| `bias-evaluator.disparate-impact-detected` | high | nonconformity-tracker, incident-reporting, nyc-ll144-audit-packager | MEASURE 2.11, NYC LL144 |

## Related artifacts

- `plugins/crosswalk-matrix-builder/`: answers "does implementing X cover Y across frameworks". This plugin answers "when X changes, what fires next".
- `plugins/applicability-checker/`: answers "which framework sections apply to this system". This plugin answers "when applicability changes, which plugins must re-run".
- `skills/cascade-impact/`: skill documentation and operationalization map.
- `evals/cascade-impact/test_cases.yaml`: validated test cases.

## Determinism

Output is deterministic for a given input dict except for the `timestamp` field, which is UTC-now. Holding timestamp constant, the action tree, flat list, summary counts, and citations are stable.

## Limitations

- The plugin does not dispatch actions. The action-executor plugin (not yet shipped) consumes this output and performs dispatch under the declared authority modes.
- The plugin does not evaluate `condition` guards or `trigger_conditions`. These are carried forward as free-text. A future integration with the `applicability-checker` condition evaluator may change this.
- The plugin does not compose cascades across plugin boundaries automatically. Cross-cascade recursion relies on the convention that a downstream cascade names its upstream source plugin in `trigger.source_plugin`.
- Runtime cycles are broken via the `(cascade_id, target_plugin)` visited set. No warning is raised when a cycle is broken; downstream auditing of cascade determinism is a separate information product.
