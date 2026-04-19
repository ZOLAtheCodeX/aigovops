"""cascade-impact-analyzer plugin.

Operationalizes the AIGovOps cascade concept. Given a trigger event (for
example, a regulatory change, a risk register update, a completed action),
computes the tree of downstream actions that should fire across the
AIGovOps plugin catalogue.

The plugin is data-driven: cascades live in ``data/cascade_schema.yaml``
and are loaded at invocation time with full invariant validation. The
plugin does not invent cascades and does not dispatch actions; it
produces an auditable action tree for the action-executor to consume.

See ``data/SCHEMA.md`` for the cascade schema reference.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


AGENT_SIGNATURE = "cascade-impact-analyzer/0.1.0"

REQUIRED_INPUT_FIELDS = ("trigger_event",)

VALID_EVENT_SEVERITIES = ("info", "warning", "critical")

VALID_AUTHORITIES = ("ask-permission", "take-resolving-action", "autonomous")

VALID_PRIORITIES = ("high", "medium", "low")

# Priority weights for flat-list ordering. Lower value means earlier.
_PRIORITY_WEIGHT = {"high": 0, "medium": 1, "low": 2}

DEFAULT_MAX_DEPTH = 5

# The full AIGovOps plugin catalogue. Any target_plugin in a cascade must
# appear here. Kept in sync with plugins/README.md and the repository
# README.md. The presence of a plugin in this tuple does not imply the
# plugin currently exposes a cascade endpoint; it is the namespace of
# valid targets.
VALID_TARGET_PLUGINS = (
    "ai-system-inventory-maintainer",
    "risk-register-builder",
    "soa-generator",
    "aisia-runner",
    "gap-assessment",
    "certification-readiness",
    "audit-log-generator",
    "management-review-packager",
    "internal-audit-planner",
    "nonconformity-tracker",
    "incident-reporting",
    "metrics-collector",
    "post-market-monitoring",
    "high-risk-classifier",
    "applicability-checker",
    "role-matrix-generator",
    "data-register-builder",
    "supplier-vendor-assessor",
    "robustness-evaluator",
    "bias-evaluator",
    "human-oversight-designer",
    "eu-conformity-assessor",
    "gpai-obligations-tracker",
    "system-event-logger",
    "explainability-documenter",
    "genai-risk-register",
    "evidence-bundle-packager",
    "crosswalk-matrix-builder",
    "uk-atrs-recorder",
    "colorado-ai-act-compliance",
    "nyc-ll144-audit-packager",
    "singapore-magf-assessor",
)

# Citation prefix patterns accepted for STYLE.md compliance. A citation is
# valid when it starts with one of these prefixes. The list is deliberately
# permissive on the suffix; the detailed format matching lives in per-row
# STYLE.md governance.
_CITATION_PREFIXES = (
    "ISO/IEC 42001:2023, Clause",
    "ISO/IEC 42001:2023, Annex A, Control",
    "ISO 42001, Clause",
    "GOVERN ",
    "MAP ",
    "MEASURE ",
    "MANAGE ",
    "EU AI Act, Article",
    "EU AI Act, Annex",
    "EU AI Act, Recital",
    "UK ATRS, Section",
    "Colorado SB 205, Section",
    "NYC LL144",
    "NYC DCWP AEDT Rules",
    "NIST AI 600-1, Section",
    "CCPA Regulations (CPPA), Section",
    "California Civil Code, Section",
    "California Business and Professions Code, Section",
    "Canada AIDA",
    "AIDA Section",
    "PIPEDA",
    "OSFI Guideline E-23",
    "Canada Directive on Automated Decision-Making",
    "Quebec Law 25",
    "Canada Voluntary AI Code",
    "Singapore MAGF 2e",
    "MAS FEAT Principles",
    "AI Verify (IMDA 2024)",
    "MAS Veritas",
)

DATA_DIR = Path(__file__).parent / "data"

EM_DASH = "\u2014"


# ---------------------------------------------------------------------------
# Data loading and invariant enforcement
# ---------------------------------------------------------------------------


def _scan_for_em_dash(value: Any, context: str) -> None:
    if isinstance(value, str):
        if EM_DASH in value:
            raise ValueError(
                f"Em-dash (U+2014) found in cascade_schema.yaml at {context}. "
                "Use a hyphen, colon, comma, parentheses, or two sentences instead."
            )
    elif isinstance(value, dict):
        for k, v in value.items():
            _scan_for_em_dash(v, f"{context}.{k}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _scan_for_em_dash(item, f"{context}[{i}]")


def _citation_is_valid(citation: str) -> bool:
    if not isinstance(citation, str) or not citation.strip():
        return False
    return any(citation.startswith(prefix) for prefix in _CITATION_PREFIXES)


def _validate_cascade(cascade: dict, seen_ids: set, seen_events: set) -> None:
    cid = cascade.get("id")
    if not cid or not isinstance(cid, str):
        raise ValueError(f"Cascade missing 'id': {cascade!r}")
    if cid in seen_ids:
        raise ValueError(f"Duplicate cascade id '{cid}'")

    trigger = cascade.get("trigger")
    if not isinstance(trigger, dict):
        raise ValueError(f"Cascade '{cid}' missing or invalid 'trigger' block")

    event = trigger.get("event")
    if not event or not isinstance(event, str):
        raise ValueError(f"Cascade '{cid}' has no trigger.event")
    if event in seen_events:
        raise ValueError(
            f"Cascade '{cid}' duplicates trigger event '{event}'. "
            "Exactly one cascade per event is permitted."
        )

    priority = cascade.get("priority")
    if priority not in VALID_PRIORITIES:
        raise ValueError(
            f"Cascade '{cid}' has invalid priority '{priority}'. "
            f"Must be one of {VALID_PRIORITIES}."
        )

    top_citations = cascade.get("citations") or []
    if not isinstance(top_citations, list):
        raise ValueError(f"Cascade '{cid}' top-level citations must be a list")
    for c in top_citations:
        if not _citation_is_valid(c):
            raise ValueError(
                f"Cascade '{cid}' top-level citation '{c}' does not match "
                "any STYLE.md prefix."
            )

    actions = cascade.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError(f"Cascade '{cid}' must declare at least one action")

    for idx, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValueError(f"Cascade '{cid}' action[{idx}] must be a dict")
        target = action.get("target_plugin")
        if target not in VALID_TARGET_PLUGINS:
            raise ValueError(
                f"Cascade '{cid}' action[{idx}] target_plugin '{target}' is not "
                f"in the AIGovOps catalogue. Must be one of {sorted(VALID_TARGET_PLUGINS)}."
            )
        authority = action.get("authority")
        if authority not in VALID_AUTHORITIES:
            raise ValueError(
                f"Cascade '{cid}' action[{idx}] has invalid authority '{authority}'. "
                f"Must be one of {VALID_AUTHORITIES}."
            )
        max_hops = action.get("max_hops_further", 3)
        if not isinstance(max_hops, int) or max_hops < 0:
            raise ValueError(
                f"Cascade '{cid}' action[{idx}] max_hops_further must be a "
                f"non-negative integer, got {max_hops!r}."
            )
        action_citations = action.get("citations") or []
        if not isinstance(action_citations, list) or not action_citations:
            raise ValueError(
                f"Cascade '{cid}' action[{idx}] must carry at least one citation"
            )
        for c in action_citations:
            if not _citation_is_valid(c):
                raise ValueError(
                    f"Cascade '{cid}' action[{idx}] citation '{c}' does not "
                    "match any STYLE.md prefix."
                )
        if not action.get("action_type"):
            raise ValueError(
                f"Cascade '{cid}' action[{idx}] missing action_type"
            )
        if not action.get("rationale"):
            raise ValueError(
                f"Cascade '{cid}' action[{idx}] missing rationale"
            )

    seen_ids.add(cid)
    seen_events.add(event)


def load_cascade_schema(data_dir: Path | None = None) -> dict:
    """Load cascade_schema.yaml and return the validated registry.

    Enforces every invariant declared in ``data/SCHEMA.md``. Raises
    ``ValueError`` on the first violation with a specific message naming
    the cascade id. The output is an in-memory dict with an index keyed
    by trigger event id for O(1) lookup.
    """
    dir_path = data_dir if data_dir is not None else DATA_DIR
    schema_path = dir_path / "cascade_schema.yaml"
    if not schema_path.exists():
        raise ValueError(f"cascade_schema.yaml not found in {dir_path}")

    doc = yaml.safe_load(schema_path.read_text(encoding="utf-8")) or {}
    _scan_for_em_dash(doc, "cascade_schema")

    cascades = doc.get("cascades") or []
    if not isinstance(cascades, list):
        raise ValueError("cascade_schema.yaml 'cascades' must be a list")

    seen_ids: set = set()
    seen_events: set = set()
    for cascade in cascades:
        _validate_cascade(cascade, seen_ids, seen_events)

    by_event: dict[str, dict] = {c["trigger"]["event"]: c for c in cascades}

    # Invariant 9: no self-cycles. A cascade must not name an action whose
    # target_plugin equals the cascade's own source_plugin. Deeper cross-
    # cascade loops are legitimate governance loops (gap to readiness to
    # remediation back to gap) and are broken at runtime by the visited
    # set in _expand_cascade.
    for cascade in cascades:
        source = cascade["trigger"].get("source_plugin")
        for action in cascade.get("actions", []):
            if source and action["target_plugin"] == source:
                raise ValueError(
                    f"Self-cycle in cascade '{cascade['id']}': action targets "
                    f"its own source_plugin '{source}'."
                )

    return {"cascades": cascades, "by_event": by_event}


# ---------------------------------------------------------------------------
# Analysis entry point
# ---------------------------------------------------------------------------


def analyze_cascade(inputs: dict) -> dict:
    """Canonical entry point. Compute the downstream action tree for a
    trigger event.

    Args:
        inputs: dict with the following keys:
            trigger_event (required): dict with ``event`` (required),
                ``source_plugin`` (optional), and ``context_data`` (optional dict).
            max_depth (optional, default DEFAULT_MAX_DEPTH): recursion cap.
            authority_filter (optional): list of authority modes to include.
            severity (optional, default 'info'): event severity enum.
            reviewed_by (optional): reviewer name.

    Returns:
        dict with ``timestamp``, ``agent_signature``, ``trigger``,
        ``cascade_tree``, ``flat_action_list``, ``summary``, ``citations``,
        ``warnings``.

    Raises:
        ValueError: on structural input errors.
    """
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")

    for field in REQUIRED_INPUT_FIELDS:
        if field not in inputs:
            raise ValueError(f"Missing required input field: '{field}'")

    trigger_event = inputs["trigger_event"]
    if not isinstance(trigger_event, dict):
        raise ValueError("trigger_event must be a dict")
    event_id = trigger_event.get("event")
    if not event_id or not isinstance(event_id, str):
        raise ValueError("trigger_event.event is required and must be a string")

    severity = inputs.get("severity", "info")
    if severity not in VALID_EVENT_SEVERITIES:
        raise ValueError(
            f"Invalid severity '{severity}'. Must be one of {VALID_EVENT_SEVERITIES}."
        )

    max_depth = inputs.get("max_depth", DEFAULT_MAX_DEPTH)
    if not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError(
            f"max_depth must be a non-negative integer, got {max_depth!r}"
        )

    authority_filter = inputs.get("authority_filter")
    if authority_filter is not None:
        if not isinstance(authority_filter, (list, tuple)):
            raise ValueError("authority_filter must be a list or tuple")
        for a in authority_filter:
            if a not in VALID_AUTHORITIES:
                raise ValueError(
                    f"Invalid authority_filter value '{a}'. Must be one of {VALID_AUTHORITIES}."
                )
        authority_set = set(authority_filter)
    else:
        authority_set = None

    registry = load_cascade_schema()
    by_event = registry["by_event"]

    warnings: list[str] = []

    root_cascade = by_event.get(event_id)
    if root_cascade is None:
        return {
            "timestamp": _utc_now_iso(),
            "agent_signature": AGENT_SIGNATURE,
            "trigger": {
                "event": event_id,
                "source_plugin": trigger_event.get("source_plugin"),
                "context_data": trigger_event.get("context_data") or {},
                "severity": severity,
            },
            "matched_cascades": [],
            "cascade_tree": [],
            "flat_action_list": [],
            "summary": {
                "total_actions": 0,
                "by_authority": {},
                "by_target_plugin": {},
                "max_depth_reached": 0,
            },
            "citations": [],
            "warnings": [f"No cascade defined for event '{event_id}'"],
            "reviewed_by": inputs.get("reviewed_by"),
        }

    # Build tree.
    visited: set[tuple[str, str]] = set()
    tree_nodes = _expand_cascade(
        cascade=root_cascade,
        by_event=by_event,
        hop=0,
        max_depth=max_depth,
        parent_max_hops=None,
        visited=visited,
        authority_filter=authority_set,
    )

    # Flat list: traverse tree in priority-then-hop order.
    flat = _flatten(tree_nodes)
    flat_sorted = sorted(
        flat,
        key=lambda a: (
            _PRIORITY_WEIGHT.get(a.get("priority", "medium"), 1),
            a.get("hop_count", 0),
            a.get("target_plugin", ""),
        ),
    )

    # Summary.
    by_authority: dict[str, int] = {}
    by_target: dict[str, int] = {}
    max_reached = 0
    for node in flat_sorted:
        a = node.get("authority", "")
        t = node.get("target_plugin", "")
        by_authority[a] = by_authority.get(a, 0) + 1
        by_target[t] = by_target.get(t, 0) + 1
        if node.get("hop_count", 0) > max_reached:
            max_reached = node["hop_count"]

    # Citations aggregated from all surfaced nodes and the root cascade.
    citations: list[str] = []
    seen_c: set[str] = set()
    for c in root_cascade.get("citations") or []:
        if c not in seen_c:
            citations.append(c)
            seen_c.add(c)
    for node in flat_sorted:
        for c in node.get("citations") or []:
            if c not in seen_c:
                citations.append(c)
                seen_c.add(c)

    if not flat_sorted and authority_set is not None:
        warnings.append(
            "All matched actions were filtered out by authority_filter. "
            "Relax the filter or verify the cascade schema."
        )

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "trigger": {
            "event": event_id,
            "source_plugin": trigger_event.get("source_plugin") or root_cascade["trigger"].get("source_plugin"),
            "context_data": trigger_event.get("context_data") or {},
            "severity": severity,
        },
        "matched_cascades": [root_cascade["id"]],
        "cascade_tree": tree_nodes,
        "flat_action_list": flat_sorted,
        "summary": {
            "total_actions": len(flat_sorted),
            "by_authority": by_authority,
            "by_target_plugin": by_target,
            "max_depth_reached": max_reached,
        },
        "citations": citations,
        "warnings": warnings,
        "reviewed_by": inputs.get("reviewed_by"),
    }


def _expand_cascade(
    cascade: dict,
    by_event: dict,
    hop: int,
    max_depth: int,
    parent_max_hops: int | None,
    visited: set,
    authority_filter: set | None,
) -> list[dict]:
    nodes: list[dict] = []
    cid = cascade["id"]
    priority = cascade.get("priority", "medium")
    for action in cascade.get("actions", []):
        target = action["target_plugin"]
        authority = action["authority"]

        # Authority filter: drop actions whose authority is not in the filter.
        if authority_filter is not None and authority not in authority_filter:
            continue

        key = (cid, target)
        if key in visited:
            # Already expanded on this branch; break the chain.
            continue

        node = {
            "cascade_id": cid,
            "priority": priority,
            "hop_count": hop,
            "action_type": action.get("action_type"),
            "target_plugin": target,
            "rationale": action.get("rationale"),
            "authority": authority,
            "max_hops_further": action.get("max_hops_further", 3),
            "citations": list(action.get("citations") or []),
            "delay_seconds": action.get("delay_seconds", 0),
            "condition": action.get("condition"),
            "children": [],
        }

        # Recurse into downstream cascades whose source_plugin matches this
        # action's target_plugin. Stop when hop+1 >= max_depth or when the
        # action's own max_hops_further is exhausted.
        next_hop = hop + 1
        remaining_from_action = action.get("max_hops_further", 3)
        if next_hop < max_depth and remaining_from_action > 0:
            new_visited = visited | {key}
            for next_event, next_cascade in by_event.items():
                next_source = next_cascade.get("trigger", {}).get("source_plugin")
                if next_source == target:
                    child_nodes = _expand_cascade(
                        cascade=next_cascade,
                        by_event=by_event,
                        hop=next_hop,
                        max_depth=min(max_depth, next_hop + remaining_from_action),
                        parent_max_hops=remaining_from_action - 1,
                        visited=new_visited,
                        authority_filter=authority_filter,
                    )
                    node["children"].extend(child_nodes)

        nodes.append(node)
    return nodes


def _flatten(tree_nodes: list[dict]) -> list[dict]:
    flat: list[dict] = []
    for node in tree_nodes:
        flat.append(node)
        flat.extend(_flatten(node.get("children", [])))
    return flat


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_markdown(analysis: dict) -> str:
    """Render a cascade analysis as Markdown."""
    required = (
        "timestamp",
        "agent_signature",
        "trigger",
        "cascade_tree",
        "flat_action_list",
        "summary",
    )
    missing = [k for k in required if k not in analysis]
    if missing:
        raise ValueError(f"analysis missing required fields: {missing}")

    trigger = analysis["trigger"]
    summary = analysis["summary"]

    lines: list[str] = []
    lines.append("# Cascade impact analysis")
    lines.append("")
    lines.append(f"- Timestamp: {analysis['timestamp']}")
    lines.append(f"- Agent: {analysis['agent_signature']}")
    if analysis.get("reviewed_by"):
        lines.append(f"- Reviewed by: {analysis['reviewed_by']}")
    lines.append("")

    lines.append("## Trigger")
    lines.append("")
    lines.append(f"- event: {trigger.get('event')}")
    lines.append(f"- source_plugin: {trigger.get('source_plugin') or ''}")
    lines.append(f"- severity: {trigger.get('severity')}")
    ctx = trigger.get("context_data") or {}
    if ctx:
        lines.append("- context_data:")
        for k, v in sorted(ctx.items()):
            lines.append(f"  - {k}: {v}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- total_actions: {summary.get('total_actions', 0)}")
    lines.append(f"- max_depth_reached: {summary.get('max_depth_reached', 0)}")
    ba = summary.get("by_authority") or {}
    if ba:
        lines.append("- by_authority:")
        for k, v in sorted(ba.items()):
            lines.append(f"  - {k}: {v}")
    bt = summary.get("by_target_plugin") or {}
    if bt:
        lines.append("- by_target_plugin:")
        for k, v in sorted(bt.items()):
            lines.append(f"  - {k}: {v}")
    lines.append("")

    citations = analysis.get("citations") or []
    if citations:
        lines.append("## Citations")
        lines.append("")
        for c in citations:
            lines.append(f"- {c}")
        lines.append("")

    warnings = analysis.get("warnings") or []
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## Cascade tree")
    lines.append("")
    tree = analysis.get("cascade_tree") or []
    if not tree:
        lines.append("(no actions)")
        lines.append("")
    else:
        for node in tree:
            _render_tree_node(node, depth=0, lines=lines)
        lines.append("")

    lines.append("## Flat action list")
    lines.append("")
    flat = analysis.get("flat_action_list") or []
    if not flat:
        lines.append("(no actions)")
    else:
        lines.append(
            "| priority | hop | target_plugin | action_type | authority | rationale |"
        )
        lines.append("|---|---|---|---|---|---|")
        for a in flat:
            rationale = (a.get("rationale") or "").replace("|", "\\|")
            lines.append(
                "| {p} | {h} | {t} | {at} | {au} | {r} |".format(
                    p=a.get("priority", ""),
                    h=a.get("hop_count", 0),
                    t=a.get("target_plugin", ""),
                    at=a.get("action_type", ""),
                    au=a.get("authority", ""),
                    r=rationale,
                )
            )
    lines.append("")

    return "\n".join(lines)


def _render_tree_node(node: dict, depth: int, lines: list[str]) -> None:
    indent = "  " * depth
    lines.append(
        f"{indent}- [{node.get('priority','')}/hop{node.get('hop_count',0)}] "
        f"{node.get('target_plugin','')} "
        f"({node.get('action_type','')}, {node.get('authority','')}): "
        f"{node.get('rationale','')}"
    )
    for child in node.get("children") or []:
        _render_tree_node(child, depth + 1, lines)


def render_csv(analysis: dict) -> str:
    """Render the flat action list as CSV. One row per action."""
    if "flat_action_list" not in analysis:
        raise ValueError("analysis missing 'flat_action_list'")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "cascade_id",
            "priority",
            "hop_count",
            "target_plugin",
            "action_type",
            "authority",
            "rationale",
            "max_hops_further",
            "delay_seconds",
            "condition",
            "citations",
        ]
    )
    for a in analysis["flat_action_list"]:
        writer.writerow(
            [
                a.get("cascade_id", ""),
                a.get("priority", ""),
                a.get("hop_count", 0),
                a.get("target_plugin", ""),
                a.get("action_type", ""),
                a.get("authority", ""),
                a.get("rationale", ""),
                a.get("max_hops_further", ""),
                a.get("delay_seconds", 0),
                a.get("condition") or "",
                "; ".join(a.get("citations") or []),
            ]
        )
    return buf.getvalue()
