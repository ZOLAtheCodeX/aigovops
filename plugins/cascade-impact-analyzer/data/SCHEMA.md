# cascade_schema.yaml

Canonical schema for the AIGovOps cascade registry. One YAML file under `data/cascade_schema.yaml` encodes every cascade the `cascade-impact-analyzer` plugin knows how to trace. Every cascade names a trigger event, the downstream actions that fire from it, the authority each action carries, and the citations that justify the cascade's existence.

This schema does not encode runtime dispatch (the `action-executor` plugin is a separate concern) and does not encode multi-step orchestration (PDCA orchestration is a separate concern). It is the pure data surface: trigger to downstream-action mapping.

## File layout

```text
plugins/cascade-impact-analyzer/data/
  SCHEMA.md                              this document
  cascade_schema.yaml                    seeded cascade registry
```

## Top-level structure

```yaml
cascades:
  - id: <unique-slug>
    trigger:
      event: <event-id>
      source_plugin: <plugin-name>
      trigger_conditions: [<free-text rule expressions>]
    description: <human-readable>
    priority: high | medium | low
    actions:
      - action_type: <action-type>
        target_plugin: <plugin-name>
        rationale: <why this action fires>
        authority: ask-permission | take-resolving-action | autonomous
        max_hops_further: <int>
        citations: [<framework-citation>]
        delay_seconds: <int>
        condition: <optional free-text predicate>
    citations: [<framework-citation>]
```

## Field reference

### `id`

Stable, deterministic slug. Unique across the cascade registry. Format: `<source-plugin>.<event-name>` is recommended (for example `risk-register.risk-added`). Enables reference from skills, workflows, and other plugins.

### `trigger`

Every cascade has exactly one trigger block.

- `event` (required): event identifier. Matches the event id the source plugin emits. Convention: `<plugin-name>.<event-kind>` (for example `framework-monitor.change-detected`, `high-risk-classifier.eu-annex-iii-match`).
- `source_plugin` (optional): the plugin that emits the event. Used for human-readable rendering and for the per-trigger operationalization map.
- `trigger_conditions` (optional): list of free-text rule expressions. Machine-readable conditions are out of scope for 0.1.0. The plugin does not evaluate these at runtime. Conditions are carried forward in the output so a future action-executor can gate dispatch.

### `description`

One-sentence plain-English explanation of the cascade. Rendered in Markdown output.

### `priority`

One of `high`, `medium`, `low`. Governs the flat-action-list ordering produced by `analyze_cascade`. `high` cascades surface their actions before `medium`, before `low`. Within a priority band, actions are ordered by hop count (ascending).

### `actions`

List of `Action` records. Every action names its target, why it fires, and the authority posture the action-executor must adopt when dispatching it.

| Field | Required | Meaning |
|---|---|---|
| `action_type` | yes | Vocabulary from the future `action-executor` plugin. Typical values: `re-run-plugin`, `notification`, `trigger-downstream`, `file-update`, `log`. Free-text for 0.1.0; enum when action-executor lands. |
| `target_plugin` | yes | The plugin the action hits. Must be in the AIGovOps catalogue. Validated at load time. |
| `rationale` | yes | Plain-English reason this action fires. Rendered next to the action in Markdown output. |
| `authority` | yes | One of `ask-permission`, `take-resolving-action`, `autonomous`. Controls whether the action-executor is permitted to dispatch without human-in-the-loop. |
| `max_hops_further` | yes | Integer. Cascade-depth limit measured from this action node. A node with `max_hops_further: 3` may cascade three more hops before forced termination. Defaults to 3 when omitted. |
| `citations` | yes | List of framework-citation strings in STYLE.md format. Justifies the cascade at the action-level granularity. |
| `delay_seconds` | no | Integer pre-delay before dispatch. `0` by default. |
| `condition` | no | Free-text guard. Not evaluated by the plugin. Carried forward in output. |

### `citations` (top-level)

Top-level citations justify the existence of the cascade as a whole. Rendered in the top-of-Markdown citations section. STYLE.md formats only.

## Authority vocabulary

| Value | Semantics | Example |
|---|---|---|
| `ask-permission` | Human-in-the-loop required before dispatch. Action-executor surfaces the proposal and waits. | Notifying the management review packager that a cascade has consequences for the next review cycle. |
| `take-resolving-action` | Dispatch without prompting when the trigger condition is met, provided the cascade authority chain is intact. The action resolves a known obligation (for example, a re-run after an applicability-relevant inventory change). | Re-running `applicability-checker` after a system is added to the inventory. |
| `autonomous` | Reserved. No cascades in the 0.1.0 seed set use this. Reserved for mechanical bookkeeping actions (for example, log rotation). | Reserved. |

## Action-type vocabulary

The action-executor plugin will pin the enum. For 0.1.0, free-text values are permitted, but the following values are recognized:

| Value | Meaning |
|---|---|
| `re-run-plugin` | Re-invoke the target plugin with current inputs. |
| `trigger-downstream` | Emit a new event that other cascades listen for. Used to chain cascades explicitly. |
| `notification` | Add the target plugin to the notification queue without re-running it. |
| `file-update` | Mutate a file under the target plugin's scope. |
| `log` | Append a record to the audit log. |

## Invariants (machine-verified at load time)

1. Every `cascades[].id` is unique across the registry.
2. Every `trigger.event` is unique across the registry (one cascade per event). Multiple actions per cascade is how fan-out is expressed.
3. Every `target_plugin` exists in the AIGovOps plugin catalogue (validated against the `VALID_TARGET_PLUGINS` tuple in `plugin.py`).
4. Every `authority` value is in `VALID_AUTHORITIES`.
5. Every `priority` value is in `VALID_PRIORITIES`.
6. Every citation (top-level or action-level) matches one of the STYLE.md prefix patterns.
7. `max_hops_further` is a non-negative integer.
8. No em-dashes (U+2014). No emojis. Hyphens only.
9. No self-cycles at the schema level. A cascade must not name an action whose `target_plugin` equals the cascade's own `source_plugin`. Legitimate cross-cascade governance loops (gap -> readiness -> remediation -> gap) are permitted and are broken at runtime by the `(cascade_id, target_plugin)` visited set in the action-tree expander.

Plugin tests enforce all nine invariants.

## Relationship to other AIGovOps artifacts

- `crosswalk-matrix-builder` answers "does implementing X cover Y across frameworks". This plugin answers "when X changes, what fires next in my governance program".
- `applicability-checker` answers "which framework sections apply to this system". This plugin answers "when applicability changes, which plugins must re-run".
- The `action-executor` plugin (not yet shipped) will consume `analyze_cascade` output and dispatch actions under their authority modes.
- The `certification-path-planner` plugin (not yet shipped) will consume `analyze_cascade` output when `certification-readiness.not-ready` fires, to produce a remediation plan.
- The PDCA orchestrator (not yet shipped) will consume `analyze_cascade` output to produce a sequenced Plan-Do-Check-Act loop.

Last updated: 2026-04-18.
