"""
AIGovOps: Post-Market Monitoring Plan Plugin

Operationalizes EU AI Act Article 72 (Post-market monitoring system and
plan), ISO/IEC 42001:2023 Clause 9.1 (Monitoring, measurement, analysis,
evaluation), NIST AI RMF 1.0 MANAGE 4.1 (post-deployment monitoring
planned), and MANAGE 4.2 (continual improvement activities integrated).
UK ATRS Section 4.3 (Incident response and monitoring) is the UK
transparency counterpart for uk-jurisdiction systems.

Distinct from sibling plugins:
- metrics-collector: point-in-time KPI MEASUREMENT against a catalogue.
- nonconformity-tracker: ISO Clause 10.2 internal corrective-action
  response when monitoring detects an issue.
- incident-reporting: external statutory notification when an incident
  triggers Article 73 (or Colorado, NYC) deadlines.

This plugin is the PLAN itself. It declares what is monitored, at what
cadence, by what method, with what threshold, and how observed signals
route to the correct response mechanism via the trigger catalogue. The
plan is the artifact regulators expect under EU Art. 72(4) (part of the
technical documentation referred to in Article 11) and ISO Clause 9.1
(documented monitoring scheme).

Design stance: the plugin does NOT invent thresholds, owners, or data
collection methods. Every substantive content field comes from input or
is computed deterministically. Dimensions declared in scope without a
matching data_collection entry produce a placeholder row and a warning.

Status: Phase 3 minimum-viable implementation. 0.1.0.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "post-market-monitoring/0.1.0"

REQUIRED_INPUT_FIELDS = ("system_description", "monitoring_scope", "cadence")

VALID_CADENCES = (
    "continuous",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "annual",
    "event-driven",
    "mixed",
)

VALID_DIMENSIONS = (
    "accuracy",
    "robustness",
    "cybersecurity",
    "drift",
    "bias-fairness",
    "privacy-leakage",
    "availability",
    "latency",
    "throughput",
    "user-feedback",
    "incident-rate",
    "safety-events",
    "explainability-signals",
)

VALID_DATA_COLLECTION_METHODS = (
    "telemetry",
    "logs",
    "human-review-sampling",
    "user-survey",
    "complaints-channel",
    "shadow-deployment",
    "canary-analysis",
    "audit-sampling",
    "red-team-engagement",
)

VALID_ESCALATION_PATHS = (
    "nonconformity-tracker",
    "incident-reporting",
    "management-review",
    "risk-register-update",
    "corrective-action-plan",
    "system-decommission",
)

DEFAULT_PLAN_REVIEW_INTERVAL_MONTHS = 12

VALID_RISK_TIERS = (
    "minimal-risk",
    "limited-risk",
    "high-risk-annex-i",
    "high-risk-annex-iii",
    "general-purpose-ai",
    "prohibited",
    "out-of-scope",
)

# Chapter III (Articles 8 to 15) requirement to monitoring-dimension
# alignment per EU AI Act conformity-assessment practice.
CHAPTER_III_DIMENSION_MAP: dict[str, tuple[str, ...]] = {
    "Article 9": ("drift", "bias-fairness", "incident-rate"),
    "Article 10": ("privacy-leakage", "bias-fairness"),
    "Article 13": ("user-feedback",),
    "Article 14": ("human-review-sampling",),
    "Article 15": ("accuracy", "robustness", "cybersecurity", "availability", "latency"),
    "Article 26": ("incident-rate",),
}

# Per-dimension cadence mapping for next-review-date calculation. Mixed
# cadences are computed per dimension from a dict input.
_CADENCE_DAYS: dict[str, int] = {
    "continuous": 1,
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
    "annual": 365,
    "event-driven": 0,
    "mixed": 30,
}

# Cross-framework references emitted when enrich_with_crosswalk is True.
# Mirrors the relationships asserted in the crosswalk data files.
CROSS_FRAMEWORK_PMM_REFERENCES: tuple[dict[str, Any], ...] = (
    {
        "target_framework": "nist-ai-rmf",
        "target_ref": "MANAGE 4.1",
        "relationship": "exact-match",
        "confidence": "high",
        "note": "Post-deployment monitoring planned. ISO Clause 9.1 monitoring scheme aligns with NIST MANAGE 4.1 post-deployment monitoring posture.",
    },
    {
        "target_framework": "nist-ai-rmf",
        "target_ref": "MANAGE 4.2",
        "relationship": "partial-match",
        "confidence": "high",
        "note": "Continual improvement activities integrated. NIST MANAGE 4.2 covers update integration; ISO Clause 9.1 anchors the monitoring evidence stream that feeds those updates.",
    },
    {
        "target_framework": "eu-ai-act",
        "target_ref": "Article 72, Paragraph 1",
        "relationship": "satisfies",
        "confidence": "high",
        "note": "Post-market monitoring system establishment. ISO Clause 9.1 provides the management-system-side monitoring scheme that satisfies Article 72(1).",
    },
    {
        "target_framework": "eu-ai-act",
        "target_ref": "Article 72, Paragraph 2",
        "relationship": "satisfies",
        "confidence": "high",
        "note": "Continuous compliance evaluation. ISO Clause 9.1 plus Annex A Control A.6.2.6 (operation and monitoring) satisfy the continuous-evaluation expectation.",
    },
    {
        "target_framework": "eu-ai-act",
        "target_ref": "Article 72, Paragraph 4",
        "relationship": "satisfies",
        "confidence": "high",
        "note": "Plan as part of technical documentation. ISO Clauses 7.5.3 and Annex A.6.2.7 supply the documented-monitoring-plan substrate Article 72(4) expects.",
    },
)

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    sd = inputs["system_description"]
    if not isinstance(sd, dict):
        raise ValueError("system_description must be a dict")
    for key in (
        "system_id",
        "system_name",
        "intended_use",
        "risk_tier",
        "jurisdiction",
        "deployment_context",
        "lifecycle_state",
    ):
        if key not in sd:
            raise ValueError(f"system_description missing required field {key!r}")
    if sd["risk_tier"] not in VALID_RISK_TIERS:
        raise ValueError(
            f"system_description.risk_tier must be one of {VALID_RISK_TIERS}; got {sd['risk_tier']!r}"
        )

    scope = inputs["monitoring_scope"]
    if not isinstance(scope, dict):
        raise ValueError("monitoring_scope must be a dict")
    for key in ("dimensions_monitored", "chapter_iii_requirements_in_scope", "systems_in_program"):
        if key not in scope:
            raise ValueError(f"monitoring_scope missing required field {key!r}")
    if not isinstance(scope["dimensions_monitored"], list):
        raise ValueError("monitoring_scope.dimensions_monitored must be a list")
    for d in scope["dimensions_monitored"]:
        if d not in VALID_DIMENSIONS:
            raise ValueError(
                f"monitoring_scope.dimensions_monitored contains invalid dimension {d!r}; "
                f"must be one of {VALID_DIMENSIONS}"
            )
    if not isinstance(scope["chapter_iii_requirements_in_scope"], list):
        raise ValueError("monitoring_scope.chapter_iii_requirements_in_scope must be a list")
    if not isinstance(scope["systems_in_program"], list):
        raise ValueError("monitoring_scope.systems_in_program must be a list")

    cadence = inputs["cadence"]
    if isinstance(cadence, str):
        if cadence not in VALID_CADENCES:
            raise ValueError(
                f"cadence must be one of {VALID_CADENCES}; got {cadence!r}"
            )
    elif isinstance(cadence, dict):
        for dim, c in cadence.items():
            if dim not in VALID_DIMENSIONS:
                raise ValueError(
                    f"cadence dict key {dim!r} is not a valid dimension; must be one of {VALID_DIMENSIONS}"
                )
            if c not in VALID_CADENCES:
                raise ValueError(
                    f"cadence for dimension {dim!r} must be one of {VALID_CADENCES}; got {c!r}"
                )
    else:
        raise ValueError("cadence must be a string enum or a dict mapping dimension to cadence")

    dc = inputs.get("data_collection")
    if dc is not None:
        if not isinstance(dc, list):
            raise ValueError("data_collection, when provided, must be a list of dicts")
        for i, entry in enumerate(dc):
            if not isinstance(entry, dict):
                raise ValueError(f"data_collection[{i}] must be a dict")
            method = entry.get("method")
            if method is not None and method not in VALID_DATA_COLLECTION_METHODS:
                raise ValueError(
                    f"data_collection[{i}].method invalid {method!r}; must be one of {VALID_DATA_COLLECTION_METHODS}"
                )
            dim = entry.get("dimension")
            if dim is not None and dim not in VALID_DIMENSIONS:
                raise ValueError(
                    f"data_collection[{i}].dimension invalid {dim!r}; must be one of {VALID_DIMENSIONS}"
                )

    thresholds = inputs.get("thresholds")
    if thresholds is not None:
        if not isinstance(thresholds, dict):
            raise ValueError("thresholds must be a dict mapping dimension to threshold spec")
        for dim, spec in thresholds.items():
            if dim not in VALID_DIMENSIONS:
                raise ValueError(
                    f"thresholds key {dim!r} is not a valid dimension; must be one of {VALID_DIMENSIONS}"
                )
            if not isinstance(spec, dict):
                raise ValueError(f"thresholds[{dim!r}] must be a dict")
            ep = spec.get("escalation_path")
            if ep is not None and ep not in VALID_ESCALATION_PATHS:
                raise ValueError(
                    f"thresholds[{dim!r}].escalation_path invalid {ep!r}; must be one of {VALID_ESCALATION_PATHS}"
                )

    triggers = inputs.get("trigger_catalogue")
    if triggers is not None:
        if not isinstance(triggers, list):
            raise ValueError("trigger_catalogue, when provided, must be a list of dicts")
        for i, t in enumerate(triggers):
            if not isinstance(t, dict):
                raise ValueError(f"trigger_catalogue[{i}] must be a dict")
            ep = t.get("escalation_path_enum") or t.get("escalation_path")
            if ep is not None and ep not in VALID_ESCALATION_PATHS:
                raise ValueError(
                    f"trigger_catalogue[{i}] escalation path invalid {ep!r}; must be one of {VALID_ESCALATION_PATHS}"
                )

    interval = inputs.get("plan_review_interval_months", DEFAULT_PLAN_REVIEW_INTERVAL_MONTHS)
    if not isinstance(interval, int) or isinstance(interval, bool) or interval < 1 or interval > 60:
        raise ValueError(
            f"plan_review_interval_months must be an int in 1 to 60; got {interval!r}"
        )

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _resolve_cadence(cadence: Any, dimension: str) -> str:
    if isinstance(cadence, dict):
        return cadence.get(dimension, "event-driven")
    return cadence


def _next_review_date(today: date, cadence_value: str) -> str:
    days = _CADENCE_DAYS.get(cadence_value, 30)
    if days <= 0:
        return "on-trigger"
    return (today + timedelta(days=days)).isoformat()


def _is_eu_high_risk(system_description: dict[str, Any]) -> bool:
    jurisdiction = system_description.get("jurisdiction", "")
    if isinstance(jurisdiction, list):
        jur_str = ",".join(j.lower() for j in jurisdiction)
    else:
        jur_str = str(jurisdiction).lower()
    if "eu" not in jur_str:
        return False
    return system_description.get("risk_tier") in ("high-risk-annex-i", "high-risk-annex-iii")


def _has_uk_jurisdiction(system_description: dict[str, Any]) -> bool:
    jurisdiction = system_description.get("jurisdiction", "")
    if isinstance(jurisdiction, list):
        return any(str(j).lower() == "uk" for j in jurisdiction)
    return "uk" in str(jurisdiction).lower()


def _build_per_dimension_rows(
    monitoring_scope: dict[str, Any],
    cadence: Any,
    data_collection: list[dict[str, Any]],
    thresholds: dict[str, Any],
    today: date,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Build per-dimension monitoring rows. Returns (rows, warnings)."""
    warnings: list[str] = []
    by_dim_methods: dict[str, list[dict[str, Any]]] = {}
    for entry in data_collection:
        d = entry.get("dimension")
        if not d:
            continue
        by_dim_methods.setdefault(d, []).append(entry)

    rows: list[dict[str, Any]] = []
    for dimension in monitoring_scope["dimensions_monitored"]:
        cadence_value = _resolve_cadence(cadence, dimension)
        threshold_spec = thresholds.get(dimension) if isinstance(thresholds, dict) else None
        escalation_path = None
        if isinstance(threshold_spec, dict):
            escalation_path = threshold_spec.get("escalation_path")
            if threshold_spec and escalation_path is None:
                warnings.append(
                    f"threshold for dimension {dimension!r} has no escalation_path. "
                    "ISO/IEC 42001:2023, Clause 9.1 expects results to be analysed; assign an escalation_path."
                )

        method_entries = by_dim_methods.get(dimension)
        if not method_entries:
            warnings.append(
                f"dimension {dimension!r} declared in monitoring_scope but no data_collection entry. "
                "EU AI Act, Article 72, Paragraph 3 (template) requires methods for data collection. "
                "Placeholder REQUIRES PRACTITIONER ASSIGNMENT emitted."
            )
            rows.append({
                "dimension": dimension,
                "cadence": cadence_value,
                "method": "REQUIRES PRACTITIONER ASSIGNMENT",
                "data_source": "REQUIRES PRACTITIONER ASSIGNMENT",
                "retention_days": None,
                "owner_role": "REQUIRES PRACTITIONER ASSIGNMENT",
                "threshold": threshold_spec,
                "escalation_path": escalation_path,
                "indicator_description": (
                    f"Monitoring indicator for {dimension}. Practitioner assignment required."
                ),
                "next_review_date": _next_review_date(today, cadence_value),
                "citations": [
                    "ISO/IEC 42001:2023, Clause 9.1",
                    "EU AI Act, Article 72, Paragraph 3",
                ],
            })
            continue

        for entry in method_entries:
            owner = entry.get("owner_role") or "REQUIRES PRACTITIONER ASSIGNMENT"
            if owner == "REQUIRES PRACTITIONER ASSIGNMENT":
                warnings.append(
                    f"data_collection entry for dimension {dimension!r} missing owner_role. "
                    "ISO/IEC 42001:2023, Clause 9.1 expects responsibilities to be defined."
                )
            rows.append({
                "dimension": dimension,
                "cadence": cadence_value,
                "method": entry.get("method", "REQUIRES PRACTITIONER ASSIGNMENT"),
                "data_source": entry.get("source_system", "REQUIRES PRACTITIONER ASSIGNMENT"),
                "retention_days": entry.get("retention_days"),
                "owner_role": owner,
                "threshold": threshold_spec,
                "escalation_path": escalation_path,
                "indicator_description": entry.get(
                    "indicator_description",
                    f"Monitoring indicator for {dimension} via {entry.get('method', 'method TBD')}.",
                ),
                "next_review_date": _next_review_date(today, cadence_value),
                "citations": [
                    "ISO/IEC 42001:2023, Clause 9.1",
                    "ISO/IEC 42001:2023, Annex A, Control A.6.2.6",
                    "NIST AI RMF, MANAGE 4.1",
                ],
            })
    return rows, warnings


def _build_trigger_catalogue(
    raw_triggers: list[dict[str, Any]],
    per_dimension_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize the trigger catalogue and attach framework citations."""
    catalogue: list[dict[str, Any]] = []
    for t in raw_triggers:
        ep = t.get("escalation_path_enum") or t.get("escalation_path")
        citations = _citations_for_escalation(ep, t)
        catalogue.append({
            "trigger_name": t.get("trigger_name", "REQUIRES PRACTITIONER ASSIGNMENT"),
            "detection_method": t.get("detection_method", "REQUIRES PRACTITIONER ASSIGNMENT"),
            "threshold_rule": t.get("threshold_rule", "REQUIRES PRACTITIONER ASSIGNMENT"),
            "escalation_path": ep,
            "notification_recipients": list(t.get("notification_recipients") or []),
            "citations": citations,
        })

    # Synthesize default triggers for any threshold-bearing dimension not
    # already represented in the trigger catalogue.
    represented = {t.get("trigger_name") for t in catalogue}
    for row in per_dimension_rows:
        if row.get("threshold") and row.get("escalation_path"):
            synth_name = f"{row['dimension']}-threshold-breach"
            if synth_name in represented:
                continue
            catalogue.append({
                "trigger_name": synth_name,
                "detection_method": row.get("method"),
                "threshold_rule": row.get("threshold"),
                "escalation_path": row.get("escalation_path"),
                "notification_recipients": [],
                "citations": _citations_for_escalation(row.get("escalation_path"), {}),
            })
    return catalogue


def _citations_for_escalation(escalation_path: str | None, trigger: dict[str, Any]) -> list[str]:
    """Return the framework citation(s) that justify the routing decision."""
    citations: list[str] = ["ISO/IEC 42001:2023, Clause 9.1"]
    if escalation_path == "incident-reporting":
        citations.append("EU AI Act, Article 73")
        severity = (trigger.get("severity") or "").lower()
        if severity in ("serious-physical-harm", "fatal", "widespread-infringement"):
            citations.append("EU AI Act, Article 73, Paragraph 6")
    elif escalation_path == "nonconformity-tracker":
        citations.append("ISO/IEC 42001:2023, Clause 10.2")
    elif escalation_path == "management-review":
        citations.append("ISO/IEC 42001:2023, Clause 9.3")
    elif escalation_path == "risk-register-update":
        citations.append("ISO/IEC 42001:2023, Clause 6.1.2")
    elif escalation_path == "corrective-action-plan":
        citations.append("ISO/IEC 42001:2023, Clause 10.2")
    elif escalation_path == "system-decommission":
        citations.append("NIST AI RMF, MANAGE 4.2")
    return citations


def _build_chapter_iii_alignment(
    system_description: dict[str, Any],
    monitoring_scope: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Return (alignment_block, warnings). Block is None when not EU high-risk."""
    if not _is_eu_high_risk(system_description):
        return None, []

    warnings: list[str] = []
    requirements = monitoring_scope.get("chapter_iii_requirements_in_scope") or []
    dimensions_monitored = set(monitoring_scope.get("dimensions_monitored") or [])
    per_article: list[dict[str, Any]] = []
    for req in requirements:
        # Normalize to "Article X" key.
        key = None
        for candidate in CHAPTER_III_DIMENSION_MAP:
            if candidate in str(req):
                key = candidate
                break
        relevant_dims = CHAPTER_III_DIMENSION_MAP.get(key, ()) if key else ()
        covered = sorted(dimensions_monitored.intersection(relevant_dims))
        if relevant_dims and not covered:
            warnings.append(
                f"Chapter III requirement {req!r} declared in scope but no plan dimension monitors it"
            )
        per_article.append({
            "chapter_iii_article": req,
            "expected_dimensions": list(relevant_dims),
            "monitored_dimensions": covered,
            "covered": bool(covered) if relevant_dims else None,
            "citations": [f"EU AI Act, {req}"] if key else [f"EU AI Act, {req}"],
        })

    block = {
        "applicable": True,
        "risk_tier": system_description.get("risk_tier"),
        "jurisdiction": system_description.get("jurisdiction"),
        "per_article": per_article,
        "citations": [
            "EU AI Act, Article 72, Paragraph 2",
            "EU AI Act, Article 11",
        ],
    }
    return block, warnings


def _build_continuous_improvement_loop(
    previous_plan_ref: str | None,
    current_plan_id: str,
    current_triggers: list[dict[str, Any]],
    current_per_dim: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the continuous-improvement loop block.

    NIST MANAGE 4.2 expects integration of measurable improvement
    activities. When previous_plan_ref is supplied we record the link and
    emit an empty-by-default diff structure that downstream tooling fills
    in. Diff inference is intentionally not attempted here; we only
    record the plan-to-plan reference.
    """
    if not previous_plan_ref:
        return {
            "previous_plan_ref": None,
            "current_plan_id": current_plan_id,
            "diff_notes": [],
            "new_triggers_added": [],
            "closed_triggers": [],
            "cadence_changes": [],
            "citation": "NIST AI RMF, MANAGE 4.2",
        }
    return {
        "previous_plan_ref": previous_plan_ref,
        "current_plan_id": current_plan_id,
        "diff_notes": [
            f"Successor to {previous_plan_ref}. Diff requires practitioner review.",
        ],
        "new_triggers_added": [t.get("trigger_name") for t in current_triggers],
        "closed_triggers": [],
        "cadence_changes": [
            {"dimension": r["dimension"], "current_cadence": r["cadence"]}
            for r in current_per_dim
        ],
        "citation": "NIST AI RMF, MANAGE 4.2",
    }


def _build_review_schedule(
    per_dimension_rows: list[dict[str, Any]],
    plan_review_interval_months: int,
    today: date,
) -> dict[str, Any]:
    next_full = today + timedelta(days=int(plan_review_interval_months * 30.4375))
    return {
        "per_dimension": [
            {
                "dimension": r["dimension"],
                "cadence": r["cadence"],
                "next_review_date": r["next_review_date"],
            }
            for r in per_dimension_rows
        ],
        "next_full_plan_review_date": next_full.isoformat(),
        "plan_review_interval_months": plan_review_interval_months,
        "citations": [
            "ISO/IEC 42001:2023, Clause 9.1",
            "EU AI Act, Article 72, Paragraph 1",
        ],
    }


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_pmm", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_cross_framework_citations() -> tuple[list[str], list[dict[str, Any]], list[str]]:
    """Return (flat citations list, structured refs, warnings).

    Mirrors internal-audit-planner pattern: hard-coded references, with
    crosswalk module loaded only to validate availability. If the
    crosswalk fails to load we still return the references but emit a
    warning.
    """
    warnings: list[str] = []
    try:
        _load_crosswalk_module()
    except Exception as exc:
        warnings.append(
            f"Crosswalk plugin unavailable ({type(exc).__name__}: {exc}); "
            "cross_framework_citations use hard-coded values."
        )
    refs = [dict(r) for r in CROSS_FRAMEWORK_PMM_REFERENCES]
    flat = [f"{r['target_framework']}: {r['target_ref']} ({r['relationship']})" for r in refs]
    return flat, refs, warnings


# ---------------------------------------------------------------------------
# Canonical entry point
# ---------------------------------------------------------------------------


def generate_monitoring_plan(inputs: dict[str, Any]) -> dict[str, Any]:
    """Generate a post-market monitoring plan artifact.

    See module docstring for design stance and input contract.

    Raises:
        ValueError: on missing or malformed required inputs.
    """
    _validate(inputs)

    sd = inputs["system_description"]
    monitoring_scope = inputs["monitoring_scope"]
    cadence = inputs["cadence"]
    data_collection = list(inputs.get("data_collection") or [])
    thresholds = dict(inputs.get("thresholds") or {})
    responsibilities = dict(inputs.get("responsibilities") or {})
    previous_plan_ref = inputs.get("previous_plan_ref")
    plan_review_interval_months = int(
        inputs.get("plan_review_interval_months", DEFAULT_PLAN_REVIEW_INTERVAL_MONTHS)
    )
    raw_triggers = list(inputs.get("trigger_catalogue") or [])
    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True
    reviewed_by = inputs.get("reviewed_by")

    today = _today()
    warnings: list[str] = []

    plan_id = f"pmm-{sd['system_id']}-{today.isoformat()}"
    plan_version = "1.1" if previous_plan_ref else "1.0"
    covered_systems = list(monitoring_scope.get("systems_in_program") or [sd["system_id"]])

    per_dimension_rows, dim_warnings = _build_per_dimension_rows(
        monitoring_scope, cadence, data_collection, thresholds, today
    )
    warnings.extend(dim_warnings)

    trigger_catalogue = _build_trigger_catalogue(raw_triggers, per_dimension_rows)

    chapter_iii_alignment, ch3_warnings = _build_chapter_iii_alignment(sd, monitoring_scope)
    warnings.extend(ch3_warnings)

    continuous_improvement_loop = _build_continuous_improvement_loop(
        previous_plan_ref, plan_id, trigger_catalogue, per_dimension_rows
    )

    review_schedule = _build_review_schedule(
        per_dimension_rows, plan_review_interval_months, today
    )

    monitoring_plan = {
        "plan_id": plan_id,
        "plan_version": plan_version,
        "covered_systems": covered_systems,
        "responsibilities": responsibilities,
        "previous_plan_ref": previous_plan_ref,
        "established_on": today.isoformat(),
    }

    citations: list[str] = [
        "EU AI Act, Article 72, Paragraph 1",
        "EU AI Act, Article 72, Paragraph 2",
        "EU AI Act, Article 72, Paragraph 4",
        "EU AI Act, Article 11",
        "ISO/IEC 42001:2023, Clause 9.1",
        "ISO/IEC 42001:2023, Annex A, Control A.6.2.6",
        "NIST AI RMF, MANAGE 4.1",
        "NIST AI RMF, MANAGE 4.2",
    ]
    if _has_uk_jurisdiction(sd):
        citations.append("UK ATRS, Section Risks")

    cross_framework_citations: list[str] = []
    cross_framework_refs: list[dict[str, Any]] = []
    if enrich:
        cross_framework_citations, cross_framework_refs, enrich_warnings = (
            _build_cross_framework_citations()
        )
        warnings.extend(enrich_warnings)

    summary = {
        "plan_id": plan_id,
        "plan_version": plan_version,
        "covered_systems_count": len(covered_systems),
        "dimensions_monitored_count": len(monitoring_scope.get("dimensions_monitored", [])),
        "per_dimension_row_count": len(per_dimension_rows),
        "trigger_count": len(trigger_catalogue),
        "warning_count": len(warnings),
        "chapter_iii_in_scope": chapter_iii_alignment is not None,
        "next_full_plan_review_date": review_schedule["next_full_plan_review_date"],
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "eu-ai-act,iso42001,nist",
        "plan_id": plan_id,
        "plan_version": plan_version,
        "system_description_echo": dict(sd),
        "monitoring_plan": monitoring_plan,
        "per_dimension_monitoring": per_dimension_rows,
        "trigger_catalogue": trigger_catalogue,
        "continuous_improvement_loop": continuous_improvement_loop,
        "review_schedule": review_schedule,
        "citations": citations,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": reviewed_by,
    }
    if chapter_iii_alignment is not None:
        output["chapter_iii_alignment"] = chapter_iii_alignment
    if enrich:
        output["cross_framework_citations"] = cross_framework_citations
        output["cross_framework_references"] = cross_framework_refs
    return output


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_markdown(plan: dict[str, Any]) -> str:
    """Render a post-market monitoring plan as Markdown audit evidence."""
    required = (
        "timestamp",
        "agent_signature",
        "plan_id",
        "monitoring_plan",
        "per_dimension_monitoring",
        "trigger_catalogue",
        "review_schedule",
        "continuous_improvement_loop",
        "citations",
        "summary",
    )
    missing = [k for k in required if k not in plan]
    if missing:
        raise ValueError(f"plan missing required fields: {missing}")

    sd = plan.get("system_description_echo", {})
    mp = plan["monitoring_plan"]
    summary = plan["summary"]

    lines: list[str] = [
        "# Post-Market Monitoring Plan",
        "",
        f"**Generated at (UTC):** {plan['timestamp']}",
        f"**Generated by:** {plan['agent_signature']}",
        f"**Framework:** {plan.get('framework', 'eu-ai-act,iso42001,nist')}",
        f"**Plan ID:** {plan['plan_id']}",
        f"**Plan version:** {plan.get('plan_version', '1.0')}",
    ]
    if plan.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {plan['reviewed_by']}")

    lines.extend([
        "",
        "## Plan overview",
        "",
        f"- System ID: {sd.get('system_id', 'not set')}",
        f"- System name: {sd.get('system_name', 'not set')}",
        f"- Intended use: {sd.get('intended_use', 'not set')}",
        f"- Risk tier: {sd.get('risk_tier', 'not set')}",
        f"- Jurisdiction: {sd.get('jurisdiction', 'not set')}",
        f"- Lifecycle state: {sd.get('lifecycle_state', 'not set')}",
        f"- Covered systems: {', '.join(mp.get('covered_systems', [])) or 'none'}",
        f"- Established on: {mp.get('established_on', 'not set')}",
        f"- Previous plan ref: {mp.get('previous_plan_ref') or 'none (initial plan)'}",
        "",
        "## Per-dimension monitoring",
        "",
    ])
    if not plan["per_dimension_monitoring"]:
        lines.append("_No dimensions monitored in this plan._")
    else:
        lines.append("| Dimension | Cadence | Method | Data source | Owner | Threshold | Escalation | Next review |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in plan["per_dimension_monitoring"]:
            threshold_text = "set" if r.get("threshold") else "not set"
            escalation = r.get("escalation_path") or "not set"
            lines.append(
                f"| {r['dimension']} | {r['cadence']} | {r['method']} | "
                f"{r['data_source']} | {r['owner_role']} | {threshold_text} | "
                f"{escalation} | {r['next_review_date']} |"
            )

    lines.extend(["", "## Trigger catalogue", ""])
    if not plan["trigger_catalogue"]:
        lines.append("_No triggers defined._")
    else:
        lines.append("| Trigger | Detection | Escalation path | Recipients | Citations |")
        lines.append("|---|---|---|---|---|")
        for t in plan["trigger_catalogue"]:
            recipients = ", ".join(t.get("notification_recipients") or []) or "not set"
            citations_text = "; ".join(t.get("citations") or [])
            lines.append(
                f"| {t['trigger_name']} | {t.get('detection_method', 'not set')} | "
                f"{t.get('escalation_path') or 'not set'} | {recipients} | {citations_text} |"
            )

    if plan.get("chapter_iii_alignment"):
        ch3 = plan["chapter_iii_alignment"]
        lines.extend(["", "## Chapter III alignment", ""])
        lines.append(f"- Risk tier: {ch3.get('risk_tier')}")
        lines.append(f"- Jurisdiction: {ch3.get('jurisdiction')}")
        lines.append("")
        lines.append("| Chapter III article | Expected dimensions | Monitored dimensions | Covered |")
        lines.append("|---|---|---|---|")
        for entry in ch3.get("per_article", []):
            expected = ", ".join(entry.get("expected_dimensions") or []) or "not mapped"
            monitored = ", ".join(entry.get("monitored_dimensions") or []) or "none"
            covered = entry.get("covered")
            covered_text = "yes" if covered else ("no" if covered is False else "not mapped")
            lines.append(
                f"| {entry['chapter_iii_article']} | {expected} | {monitored} | {covered_text} |"
            )

    rs = plan["review_schedule"]
    lines.extend(["", "## Review schedule", ""])
    lines.append(f"- Next full plan review date: {rs['next_full_plan_review_date']}")
    lines.append(f"- Plan review interval (months): {rs['plan_review_interval_months']}")
    lines.append("")
    lines.append("| Dimension | Cadence | Next review |")
    lines.append("|---|---|---|")
    for entry in rs.get("per_dimension", []):
        lines.append(f"| {entry['dimension']} | {entry['cadence']} | {entry['next_review_date']} |")

    cil = plan["continuous_improvement_loop"]
    lines.extend(["", "## Continuous improvement loop", ""])
    lines.append(f"- Previous plan ref: {cil.get('previous_plan_ref') or 'none'}")
    lines.append(f"- Current plan ID: {cil.get('current_plan_id')}")
    lines.append(f"- Citation: {cil.get('citation')}")
    if cil.get("diff_notes"):
        lines.append("")
        lines.append("**Diff notes:**")
        lines.append("")
        for n in cil["diff_notes"]:
            lines.append(f"- {n}")

    lines.extend(["", "## Applicable citations", ""])
    for c in plan["citations"]:
        lines.append(f"- {c}")

    if plan.get("cross_framework_citations"):
        lines.extend(["", "## Cross-framework citations", ""])
        for c in plan["cross_framework_citations"]:
            lines.append(f"- {c}")

    lines.extend(["", "## Warnings", ""])
    if plan.get("warnings"):
        for w in plan["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("_No warnings._")

    lines.append("")
    return "\n".join(lines)


def render_csv(plan: dict[str, Any]) -> str:
    """Render the per-dimension monitoring rows as CSV."""
    if "per_dimension_monitoring" not in plan:
        raise ValueError("plan missing required field 'per_dimension_monitoring'")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "dimension",
        "cadence",
        "method",
        "data_source",
        "retention_days",
        "owner_role",
        "threshold_set",
        "escalation_path",
        "next_review_date",
        "citations",
    ])
    for r in plan["per_dimension_monitoring"]:
        writer.writerow([
            r.get("dimension", ""),
            r.get("cadence", ""),
            r.get("method", ""),
            r.get("data_source", ""),
            r.get("retention_days") if r.get("retention_days") is not None else "",
            r.get("owner_role", ""),
            "yes" if r.get("threshold") else "no",
            r.get("escalation_path") or "",
            r.get("next_review_date", ""),
            "; ".join(r.get("citations") or []),
        ])
    return buf.getvalue()
