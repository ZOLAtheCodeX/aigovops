"""
AIGovOps: Certification Path Planner Plugin.

Consumes a certification-readiness snapshot (a point-in-time verdict with
gaps, blockers, and remediations) and produces a milestone schedule with
per-milestone remediation sequence, target dates, risk-weighted
prioritization, and recertification triggers. Each remediation is expressed
as an action request ready for the action-executor.

This plugin is the journey/planning layer above certification-readiness.
certification-readiness says "where are we today"; certification-path-
planner says "what sequence of actions, by what dates, will get us to the
certification milestone, and what triggers the next recertification cycle".

The plugin never invents new gaps or remediations. It consumes the
readiness snapshot, sequences the existing remediations into milestone
windows, annotates them with owner roles and action-request shape, and
emits scheduled future milestones for known recertification cadences.

Public API:
    plan_certification_path(inputs)  canonical entry point
    render_markdown(plan)            human-readable plan
    render_csv(plan)                 one row per milestone
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "certification-path-planner/0.1.0"

REQUIRED_INPUT_FIELDS = (
    "current_readiness_ref",
    "target_certification",
    "target_date",
)

VALID_TARGET_CERTIFICATIONS = (
    "iso42001-stage1",
    "iso42001-stage2",
    "iso42001-surveillance",
    "eu-ai-act-internal-control",
    "eu-ai-act-notified-body",
    "colorado-sb205-safe-harbor",
    "nyc-ll144-annual-audit",
    "singapore-magf-alignment",
    "uk-atrs-publication",
)

VALID_MILESTONE_STATUSES = (
    "not-started",
    "in-progress",
    "blocked",
    "complete",
    "deferred",
)

DEFAULT_MILESTONE_INTERVAL_WEEKS = 4

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily inside
# the enrichment helper.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))

# Coarse effort heuristic per gap size category. Expressed in hours.
_EFFORT_HOURS = {"small": 8, "medium": 40, "large": 160}

# Gap-key to size mapping. Drives capacity estimation without asking the
# caller for per-gap sizing.
_GAP_SIZE_MAP: dict[str, str] = {
    "missing-ai-system-inventory": "large",
    "missing-role-matrix": "medium",
    "missing-risk-register": "large",
    "missing-soa": "large",
    "missing-audit-log-entry": "small",
    "missing-aisia": "large",
    "missing-nonconformity-register": "medium",
    "missing-management-review-package": "medium",
    "missing-internal-audit-plan": "medium",
    "missing-metrics-report": "medium",
    "missing-gap-assessment": "medium",
    "missing-data-register": "large",
    "missing-high-risk-classification": "medium",
    "missing-atrs-record": "medium",
    "missing-colorado-compliance-record": "medium",
    "missing-nyc-ll144-audit-package": "large",
    "missing-magf-assessment": "medium",
    "missing-supplier-vendor-assessment": "medium",
    "legal-review-pending": "medium",
    "internal-audit-not-completed": "large",
    "imminent-reaudit-due": "large",
    "sb205-conformance-missing": "medium",
    "atrs-tier1-incomplete": "small",
    "missing-citation": "small",
    "warning-on-critical-control": "small",
}

# Action authority by gap class. Routine re-runs against a known artifact
# source may be taken as resolving action; most gaps require the human to
# approve before the action is taken.
_ACTION_AUTHORITY_BY_GAP: dict[str, str] = {
    "missing-gap-assessment": "take-resolving-action",
    "missing-citation": "take-resolving-action",
    "warning-on-critical-control": "take-resolving-action",
    "missing-audit-log-entry": "take-resolving-action",
}

# Legal disclaimer rendered into every markdown output.
_LEGAL_DISCLAIMER = (
    "> This certification path plan is informational. It does not "
    "constitute a commitment to any certification outcome. Certification "
    "decisions require a qualified auditor or notified body. Consult a "
    "Lead Implementer for formal path approval."
)

# Canonical top-level citations applicable to the plan itself.
_PLAN_CITATIONS_BY_TARGET: dict[str, tuple[str, ...]] = {
    "iso42001-stage1": (
        "ISO/IEC 42001:2023, Clause 9.2",
        "ISO/IEC 42001:2023, Clause 10.1",
    ),
    "iso42001-stage2": (
        "ISO/IEC 42001:2023, Clause 9.2",
        "ISO/IEC 42001:2023, Clause 9.3",
        "ISO/IEC 42001:2023, Clause 10.1",
        "ISO/IEC 42001:2023, Clause 10.2",
    ),
    "iso42001-surveillance": (
        "ISO/IEC 42001:2023, Clause 9.3",
        "ISO/IEC 42001:2023, Clause 10.1",
    ),
    "eu-ai-act-internal-control": (
        "EU AI Act, Article 43",
        "EU AI Act, Annex VI",
    ),
    "eu-ai-act-notified-body": (
        "EU AI Act, Article 43",
        "EU AI Act, Annex VII",
    ),
    "colorado-sb205-safe-harbor": (
        "Colorado SB 205, Section 6-1-1706(3)",
        "Colorado SB 205, Section 6-1-1706(4)",
    ),
    "nyc-ll144-annual-audit": (
        "NYC LL144 Final Rule, Section 5-301",
        "NYC LL144 Final Rule, Section 5-304",
    ),
    "singapore-magf-alignment": (
        "Singapore MAGF 2e, Pillar Internal Governance Structures and Measures",
    ),
    "uk-atrs-publication": (
        "UK ATRS, Section Tool description",
        "UK ATRS, Section Impact assessment",
    ),
}

# Cross-framework references emitted when enrich_with_crosswalk is True.
# Anchored on ISO/IEC 42001 Clause 10.1 continual improvement and Clause
# 9.3.2 management review, which are the planning surfaces the plan
# connects the readiness snapshot to.
_CROSS_FRAMEWORK_CITATIONS = (
    {
        "target_framework": "eu-ai-act",
        "target_ref": "Article 43",
        "relationship": "partial-satisfaction",
        "confidence": "high",
        "note": (
            "ISO Clause 10.1 continual improvement and Clause 9.3.2 "
            "management review satisfy, in part, the EU AI Act Article "
            "43 conformity-procedure planning posture for the "
            "internal-control route. The path plan is the planning "
            "surface connecting gap assessment to Clause 10.1."
        ),
    },
    {
        "target_framework": "nist-ai-rmf",
        "target_ref": "MANAGE 4.1",
        "relationship": "partial-match",
        "confidence": "medium",
        "note": (
            "NIST MANAGE 4.1 continual monitoring aligns with ISO "
            "Clause 10.1 and the milestone-based plan surfaces "
            "remediation tracking in the MANAGE function."
        ),
    },
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _parse_iso_date(value: str) -> date:
    """Parse an ISO date (YYYY-MM-DD) or datetime to date."""
    s = str(value).strip()
    if "T" in s or " " in s:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.date()
        except ValueError as exc:
            raise ValueError(f"invalid ISO datetime: {value!r}") from exc
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise ValueError(f"invalid ISO date: {value!r}") from exc


def _validate_inputs(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    target = inputs["target_certification"]
    if target not in VALID_TARGET_CERTIFICATIONS:
        raise ValueError(
            f"target_certification must be one of {VALID_TARGET_CERTIFICATIONS}; got {target!r}"
        )

    # target_date must parse as ISO date.
    _parse_iso_date(inputs["target_date"])

    readiness_ref = inputs["current_readiness_ref"]
    if not isinstance(readiness_ref, (str, dict)):
        raise ValueError(
            "current_readiness_ref must be a path string or a readiness dict"
        )

    capacity = inputs.get("organization_capacity")
    if capacity is not None:
        if not isinstance(capacity, dict):
            raise ValueError("organization_capacity, when provided, must be a dict")
        for num_field in ("team_size_fte", "weekly_hours_available"):
            if num_field in capacity and not isinstance(capacity[num_field], (int, float)):
                raise ValueError(
                    f"organization_capacity.{num_field} must be a number"
                )

    interval = inputs.get("minimum_milestone_interval_weeks")
    if interval is not None:
        if not isinstance(interval, int) or isinstance(interval, bool) or interval < 1:
            raise ValueError(
                "minimum_milestone_interval_weeks must be a positive int"
            )

    hard_blockers = inputs.get("hard_blockers")
    if hard_blockers is not None and not isinstance(hard_blockers, list):
        raise ValueError("hard_blockers, when provided, must be a list")

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")


# ---------------------------------------------------------------------------
# Readiness snapshot loading
# ---------------------------------------------------------------------------


def _load_readiness_snapshot(ref: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """Return (snapshot_dict_or_none, warnings). Accepts path or dict."""
    warnings: list[str] = []
    if isinstance(ref, dict):
        return ref, warnings
    path = Path(str(ref))
    if not path.exists():
        warnings.append(
            f"current_readiness_ref {path!s} does not exist. Plan produced "
            "with empty remediation set."
        )
        return None, warnings
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        warnings.append(
            f"current_readiness_ref {path!s} could not be parsed as JSON: {exc}"
        )
        return None, warnings
    if not isinstance(data, dict):
        warnings.append(
            f"current_readiness_ref {path!s} did not contain a top-level JSON object."
        )
        return None, warnings
    return data, warnings


# ---------------------------------------------------------------------------
# Risk-weighted prioritization
# ---------------------------------------------------------------------------


def _load_risk_register(ref: Any) -> dict[str, Any] | None:
    """Optional risk register lookup. Accepts dict or path."""
    if ref is None:
        return None
    if isinstance(ref, dict):
        return ref
    path = Path(str(ref))
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _max_inherent_risk_for_gap(
    gap: dict[str, Any],
    risk_register: dict[str, Any] | None,
) -> int:
    """Inherent risk score attached to a gap. Zero when no register supplied."""
    if not risk_register:
        return 0
    artifact_type = gap.get("artifact_type") or ""
    citation = gap.get("citation") or ""
    risks = risk_register.get("risks") or risk_register.get("rows") or []
    if not isinstance(risks, list):
        return 0
    best = 0
    for r in risks:
        if not isinstance(r, dict):
            continue
        score = r.get("inherent_risk_score") or r.get("inherent_score") or 0
        try:
            numeric = int(score)
        except (TypeError, ValueError):
            continue
        # Link by artifact type (for example, risk mentions SoA control).
        anchors = (
            r.get("controls_affected")
            or r.get("annex_a_controls")
            or r.get("citations")
            or []
        )
        if not isinstance(anchors, list):
            continue
        anchors_text = " ".join(str(a) for a in anchors).lower()
        if (
            artifact_type and artifact_type.lower() in anchors_text
        ) or (
            citation and citation.lower() in anchors_text
        ):
            if numeric > best:
                best = numeric
    return best


def _target_date_urgency_weight(target_date: date) -> int:
    """Return urgency weight based on weeks-to-target."""
    today = _today_utc()
    days = (target_date - today).days
    if days < 0:
        return 30
    if days < 14:
        return 25
    if days < 60:
        return 15
    if days < 180:
        return 5
    return 0


def _priority_score(
    gap: dict[str, Any],
    is_blocker: bool,
    severity_hint: int,
    risk_register: dict[str, Any] | None,
    target_date: date,
) -> int:
    """Compute priority_score = blocker_severity*10 + inherent_max + urgency_weight."""
    blocker_component = (10 if is_blocker else 0) * 10
    severity_component = severity_hint * 10
    risk_component = _max_inherent_risk_for_gap(gap, risk_register)
    urgency_component = _target_date_urgency_weight(target_date)
    return blocker_component + severity_component + risk_component + urgency_component


# ---------------------------------------------------------------------------
# Action request construction
# ---------------------------------------------------------------------------


def _build_action_request(
    remediation: dict[str, Any],
    is_blocker: bool,
) -> dict[str, Any]:
    """Emit an ActionRequest-shaped dict for the action-executor."""
    gap_key = remediation.get("gap_key", "")
    target_plugin = remediation.get("target_plugin") or "practitioner-review"
    authority = _ACTION_AUTHORITY_BY_GAP.get(gap_key, "ask-permission")
    rationale = remediation.get(
        "gap_description",
        "Remediation derived from certification-readiness snapshot.",
    )
    args: dict[str, Any] = {
        "owner_role": remediation.get("owner_role", "AIMS Owner"),
        "suggested_deadline": remediation.get("suggested_deadline", ""),
        "recommended_action": remediation.get("recommended_action", ""),
    }
    return {
        "action_type": "invoke-plugin",
        "target_plugin": target_plugin,
        "args": args,
        "rationale": rationale,
        "authority": authority,
        "source_gap_key": gap_key,
        "source_is_blocker": is_blocker,
    }


# ---------------------------------------------------------------------------
# Milestone packing
# ---------------------------------------------------------------------------


def _milestone_window_dates(
    target_date: date,
    milestone_index_from_end: int,
    interval_weeks: int,
) -> date:
    """Return the target date for a milestone N steps before the final date."""
    days = milestone_index_from_end * interval_weeks * 7
    return target_date - timedelta(days=days)


def _gap_effort_hours(gap_key: str) -> int:
    size = _GAP_SIZE_MAP.get(gap_key, "medium")
    return _EFFORT_HOURS[size]


def _hard_blockers_to_struct(raw: list[Any] | None) -> list[dict[str, Any]]:
    """Normalize hard_blockers to a list of dicts."""
    if not raw:
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            out.append({"description": item, "affected_gap_keys": []})
        elif isinstance(item, dict):
            normalized = {
                "description": item.get("description") or item.get("reason") or "unspecified hard blocker",
                "affected_gap_keys": list(item.get("affected_gap_keys") or []),
            }
            if item.get("id"):
                normalized["id"] = item["id"]
            out.append(normalized)
    return out


def _recertification_triggers_for_target(
    target: str,
    target_date: date,
) -> list[dict[str, Any]]:
    """Return scheduled future milestones for known recertification cadences."""
    triggers: list[dict[str, Any]] = []
    if target == "iso42001-stage2":
        triggers.append({
            "trigger_type": "surveillance-audit",
            "cadence": "annual",
            "scheduled_date": (target_date + timedelta(days=365)).isoformat(),
            "citation": "ISO/IEC 42001:2023, Clause 9.2",
            "note": "First surveillance audit 12 months after Stage 2 certificate.",
        })
        triggers.append({
            "trigger_type": "surveillance-audit",
            "cadence": "annual",
            "scheduled_date": (target_date + timedelta(days=730)).isoformat(),
            "citation": "ISO/IEC 42001:2023, Clause 9.2",
            "note": "Second surveillance audit 24 months after Stage 2 certificate.",
        })
    elif target == "eu-ai-act-notified-body":
        triggers.append({
            "trigger_type": "harmonised-standards-review",
            "cadence": "event-driven",
            "scheduled_date": "",
            "citation": "EU AI Act, Article 40",
            "note": (
                "Surveillance triggered when the Commission publishes updated "
                "harmonised standards or after a major system modification."
            ),
        })
    elif target == "colorado-sb205-safe-harbor":
        triggers.append({
            "trigger_type": "impact-assessment-refresh",
            "cadence": "annual",
            "scheduled_date": (target_date + timedelta(days=365)).isoformat(),
            "citation": "Colorado SB 205, Section 6-1-1703(3)",
            "note": "Impact assessment refreshed annually per statute.",
        })
    elif target == "nyc-ll144-annual-audit":
        triggers.append({
            "trigger_type": "annual-reaudit",
            "cadence": "annual",
            "scheduled_date": (target_date + timedelta(days=365)).isoformat(),
            "citation": "NYC LL144 Final Rule, Section 5-301",
            "note": "Annual bias audit must be re-run within 12 months.",
        })
    return triggers


# ---------------------------------------------------------------------------
# Crosswalk enrichment
# ---------------------------------------------------------------------------


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_cpp", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_cross_framework_citations() -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    try:
        _load_crosswalk_module()
    except Exception as exc:
        warnings.append(
            f"Crosswalk plugin unavailable ({type(exc).__name__}: {exc}); "
            "cross_framework_citations use hard-coded values."
        )
    return ([dict(ref) for ref in _CROSS_FRAMEWORK_CITATIONS], warnings)


# ---------------------------------------------------------------------------
# Plan id
# ---------------------------------------------------------------------------


def _plan_id(target: str, target_date: date, readiness_ref: Any) -> str:
    basis = f"{target}|{target_date.isoformat()}|{readiness_ref!r}"
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:8]
    return f"cert-path-{target}-{target_date.isoformat()}-{digest}"


# ---------------------------------------------------------------------------
# Core entry point
# ---------------------------------------------------------------------------


def plan_certification_path(inputs: dict[str, Any]) -> dict[str, Any]:
    """Plan a milestone sequence from today to a target certification date.

    Args:
        inputs: Dict with current_readiness_ref (required, path or dict),
            target_certification (required, enum), target_date (required,
            ISO date), organization_capacity (optional), risk_register_ref
            (optional), previous_plan_ref (optional), hard_blockers
            (optional), minimum_milestone_interval_weeks (optional),
            enrich_with_crosswalk (optional, default True), reviewed_by
            (optional).

    Returns:
        Dict with plan_id, timestamp, agent_signature, target_certification,
        target_date, current_readiness_snapshot_ref, milestones, blockers,
        recertification_triggers, capacity_assessment, citations, warnings,
        summary, and optionally cross_framework_citations.

    Raises:
        ValueError: on structural input problems.
    """
    _validate_inputs(inputs)

    target = inputs["target_certification"]
    target_date = _parse_iso_date(inputs["target_date"])
    readiness_ref = inputs["current_readiness_ref"]
    interval_weeks = int(
        inputs.get("minimum_milestone_interval_weeks", DEFAULT_MILESTONE_INTERVAL_WEEKS)
    )
    hard_blockers = _hard_blockers_to_struct(inputs.get("hard_blockers"))
    capacity = inputs.get("organization_capacity") or {}
    weekly_hours = capacity.get("weekly_hours_available")
    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True
    reviewed_by = inputs.get("reviewed_by")

    warnings: list[str] = []

    # Target date sanity.
    today = _today_utc()
    if target_date < today:
        warnings.append(
            "target date is too close or past; plan may not be achievable. "
            f"target_date={target_date.isoformat()}, today={today.isoformat()}."
        )
    elif (target_date - today).days < 7:
        warnings.append(
            "target date is too close or past; plan may not be achievable. "
            f"target_date is within 7 days of today ({today.isoformat()})."
        )

    snapshot, snapshot_warnings = _load_readiness_snapshot(readiness_ref)
    warnings.extend(snapshot_warnings)

    risk_register = _load_risk_register(inputs.get("risk_register_ref"))

    # Extract gaps, blockers, remediations from the snapshot. Do NOT invent.
    snapshot_gaps: list[dict[str, Any]] = []
    snapshot_blockers: list[dict[str, Any]] = []
    snapshot_remediations: list[dict[str, Any]] = []
    snapshot_ref_id: str | None = None
    if snapshot is not None:
        snapshot_gaps = list(snapshot.get("gaps") or [])
        snapshot_blockers = list(snapshot.get("blockers") or [])
        snapshot_remediations = list(snapshot.get("remediations") or [])
        snapshot_ref_id = (
            snapshot.get("bundle_id_ref")
            or snapshot.get("agent_signature")
            or snapshot.get("timestamp")
        )

    # Build a unified remediation work-item list. Each item carries its
    # priority score, authority, and action-request shape. No invention.
    blocker_keys = {b.get("gap_key") for b in snapshot_blockers if isinstance(b, dict)}
    work_items: list[dict[str, Any]] = []
    for rem in snapshot_remediations:
        if not isinstance(rem, dict):
            continue
        gap_key = rem.get("gap_key", "")
        is_blocker = gap_key in blocker_keys
        severity_hint = 3 if is_blocker else 1
        score = _priority_score(
            {"artifact_type": "", "citation": ""} | {
                "artifact_type": next(
                    (b.get("artifact_type") or "" for b in snapshot_blockers if b.get("gap_key") == gap_key),
                    next(
                        (g.get("artifact_type") or "" for g in snapshot_gaps if g.get("gap_key") == gap_key),
                        "",
                    ),
                ),
                "citation": next(
                    (g.get("citation") or "" for g in snapshot_gaps if g.get("gap_key") == gap_key),
                    "",
                ),
            },
            is_blocker,
            severity_hint,
            risk_register,
            target_date,
        )
        action_request = _build_action_request(rem, is_blocker)
        # Hard-blocker propagation.
        blocked_by: list[str] = []
        for hb in hard_blockers:
            if gap_key in hb.get("affected_gap_keys", []):
                blocked_by.append(hb.get("description", "unspecified hard blocker"))
        work_items.append({
            "gap_key": gap_key,
            "is_blocker": is_blocker,
            "priority_score": score,
            "effort_hours": _gap_effort_hours(gap_key),
            "action_request": action_request,
            "success_criteria": rem.get(
                "gap_description",
                "Gap resolved in next readiness snapshot.",
            ),
            "blocked_by": blocked_by,
        })

    # Sort by priority score descending; stable on input order.
    work_items.sort(key=lambda w: -w["priority_score"])

    # Pack into milestone windows. Working BACKWARDS from target_date.
    # Milestone index 0 is the final milestone (certification date).
    capacity_budget = None
    if isinstance(weekly_hours, (int, float)) and weekly_hours > 0:
        capacity_budget = float(weekly_hours) * interval_weeks

    milestones: list[dict[str, Any]] = []
    current_milestone_items: list[dict[str, Any]] = []
    current_milestone_hours = 0.0
    capacity_exceeded_notes: list[str] = []

    def _flush_milestone() -> None:
        nonlocal current_milestone_items, current_milestone_hours
        if not current_milestone_items:
            return
        milestone_index = len(milestones)
        milestones.append({
            "milestone_index": milestone_index,
            "items": current_milestone_items,
            "hours_required": current_milestone_hours,
        })
        current_milestone_items = []
        current_milestone_hours = 0.0

    for item in work_items:
        item_hours = float(item["effort_hours"])
        if capacity_budget is not None and (
            current_milestone_hours + item_hours > capacity_budget
            and current_milestone_items
        ):
            _flush_milestone()
        current_milestone_items.append(item)
        current_milestone_hours += item_hours
        if capacity_budget is not None and item_hours > capacity_budget:
            capacity_exceeded_notes.append(
                f"plan overruns team capacity at milestone {len(milestones)}; "
                f"consider deferring {item['gap_key']!r}"
            )
    _flush_milestone()

    # Assign target dates working backwards from target_date.
    # Final milestone (the certification date itself) is the last in the list;
    # we reverse-index so index 0 is the earliest upcoming milestone.
    num_milestones = len(milestones)
    enriched_milestones: list[dict[str, Any]] = []
    for i, ms in enumerate(milestones):
        steps_from_end = (num_milestones - 1) - i
        ms_date = _milestone_window_dates(target_date, steps_from_end, interval_weeks)
        milestone_id = f"M{i + 1:02d}"
        has_blocker = any(it["blocked_by"] for it in ms["items"])
        has_source_blocker = any(it["is_blocker"] for it in ms["items"])
        status = "blocked" if has_blocker else ("not-started")
        remediation_action_requests = [it["action_request"] for it in ms["items"]]
        success_criteria = [it["success_criteria"] for it in ms["items"]]
        go_no_go_gate = (
            "Blocked by external hard blocker; cannot proceed until cleared."
            if has_blocker
            else (
                "Proceed to next milestone when all remediation action "
                "requests have returned success and a fresh "
                "certification-readiness run reports no new blockers for "
                "the items in this milestone."
            )
        )
        enriched_milestones.append({
            "milestone_id": milestone_id,
            "target_date": ms_date.isoformat(),
            "hours_required": ms["hours_required"],
            "remediation_action_requests": remediation_action_requests,
            "success_criteria": success_criteria,
            "status": status,
            "blocked_by": sorted({b for it in ms["items"] for b in it["blocked_by"]}),
            "contains_snapshot_blocker": has_source_blocker,
            "go_no_go_gate": go_no_go_gate,
            "citations": list(_PLAN_CITATIONS_BY_TARGET.get(target, ())),
        })

    # Capacity assessment: per-milestone hours vs hours available in the
    # interval window.
    capacity_assessment = {
        "weekly_hours_available": weekly_hours,
        "interval_weeks": interval_weeks,
        "hours_available_per_milestone": capacity_budget,
        "per_milestone": [
            {
                "milestone_id": m["milestone_id"],
                "hours_required": m["hours_required"],
                "hours_available": capacity_budget,
                "exceeds_capacity": (
                    capacity_budget is not None
                    and m["hours_required"] > capacity_budget
                ),
            }
            for m in enriched_milestones
        ],
    }
    for note in capacity_exceeded_notes:
        warnings.append(note)
    if capacity_budget is not None:
        for entry in capacity_assessment["per_milestone"]:
            if entry["exceeds_capacity"] and not any(
                entry["milestone_id"] in w for w in warnings
            ):
                warnings.append(
                    f"plan overruns team capacity at milestone {entry['milestone_id']}; "
                    "consider deferring a remediation"
                )

    # Recertification triggers.
    triggers = _recertification_triggers_for_target(target, target_date)

    # Citations.
    citations = list(_PLAN_CITATIONS_BY_TARGET.get(target, ()))

    # Cross-framework enrichment.
    cross_framework_citations: list[dict[str, Any]] = []
    if enrich:
        refs, enrich_warnings = _build_cross_framework_citations()
        cross_framework_citations = refs
        warnings.extend(enrich_warnings)

    summary = {
        "milestone_count": len(enriched_milestones),
        "total_hours": sum(m["hours_required"] for m in enriched_milestones),
        "target_date_feasibility": (
            "not-feasible"
            if target_date < today
            else (
                "tight"
                if (target_date - today).days < 7
                else (
                    "capacity-constrained"
                    if any(
                        entry["exceeds_capacity"]
                        for entry in capacity_assessment["per_milestone"]
                    )
                    else "feasible"
                )
            )
        ),
        "remediation_count": sum(
            len(m["remediation_action_requests"]) for m in enriched_milestones
        ),
        "hard_blocker_count": len(hard_blockers),
        "recertification_trigger_count": len(triggers),
    }

    plan: dict[str, Any] = {
        "plan_id": _plan_id(target, target_date, readiness_ref),
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "target_certification": target,
        "target_date": target_date.isoformat(),
        "current_readiness_snapshot_ref": snapshot_ref_id
        or (readiness_ref if isinstance(readiness_ref, str) else "inline-dict"),
        "milestones": enriched_milestones,
        "blockers": hard_blockers,
        "recertification_triggers": triggers,
        "capacity_assessment": capacity_assessment,
        "citations": citations,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": reviewed_by,
    }
    if enrich:
        plan["cross_framework_citations"] = cross_framework_citations

    return plan


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_markdown(plan: dict[str, Any]) -> str:
    """Render the certification path plan as Markdown."""
    required = (
        "plan_id",
        "timestamp",
        "agent_signature",
        "target_certification",
        "target_date",
        "milestones",
        "summary",
    )
    missing = [k for k in required if k not in plan]
    if missing:
        raise ValueError(f"plan missing required fields: {missing}")

    lines: list[str] = []
    lines.append("# Certification Path Plan")
    lines.append("")
    lines.append(_LEGAL_DISCLAIMER)
    lines.append("")
    lines.append(f"**Plan id:** {plan['plan_id']}")
    lines.append(f"**Target certification:** {plan['target_certification']}")
    lines.append(f"**Target date:** {plan['target_date']}")
    lines.append(f"**Generated at (UTC):** {plan['timestamp']}")
    lines.append(f"**Generated by:** {plan['agent_signature']}")
    if plan.get("current_readiness_snapshot_ref"):
        lines.append(f"**Readiness snapshot:** {plan['current_readiness_snapshot_ref']}")
    if plan.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {plan['reviewed_by']}")

    summary = plan["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Milestones: {summary['milestone_count']}",
        f"- Remediations: {summary['remediation_count']}",
        f"- Total hours: {summary['total_hours']}",
        f"- Hard blockers: {summary['hard_blocker_count']}",
        f"- Recertification triggers: {summary['recertification_trigger_count']}",
        f"- Target date feasibility: {summary['target_date_feasibility']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in plan.get("citations", []):
        lines.append(f"- {c}")

    lines.extend(["", "## Milestones", ""])
    if not plan["milestones"]:
        lines.append("_No milestones planned. Readiness snapshot had no remediations._")
    for ms in plan["milestones"]:
        lines.extend([
            f"### {ms['milestone_id']}: {ms['target_date']}",
            "",
            f"**Status:** {ms['status']}",
            f"**Hours required:** {ms['hours_required']}",
            f"**Go/no-go gate:** {ms['go_no_go_gate']}",
        ])
        if ms.get("blocked_by"):
            lines.append(f"**Blocked by:** {', '.join(ms['blocked_by'])}")
        lines.extend(["", "**Remediation action requests:**", ""])
        if ms["remediation_action_requests"]:
            for ar in ms["remediation_action_requests"]:
                rationale = ar.get("rationale", "").replace("\n", " ")
                lines.append(
                    f"- [{ar['source_gap_key']}] action_type={ar['action_type']}; "
                    f"target_plugin={ar['target_plugin']}; authority={ar['authority']}. "
                    f"Rationale: {rationale}"
                )
        else:
            lines.append("- (none)")
        lines.extend(["", "**Success criteria:**", ""])
        for sc in ms["success_criteria"]:
            lines.append(f"- {sc}")
        lines.extend(["", "**Citations:**", ""])
        for c in ms["citations"]:
            lines.append(f"- {c}")
        lines.append("")

    if plan.get("blockers"):
        lines.extend(["", "## Hard blockers", ""])
        for b in plan["blockers"]:
            affected = ", ".join(b.get("affected_gap_keys", [])) or "none declared"
            lines.append(f"- {b['description']} (affects: {affected})")

    if plan.get("recertification_triggers"):
        lines.extend(["", "## Recertification triggers", ""])
        for t in plan["recertification_triggers"]:
            scheduled = t.get("scheduled_date") or "event-driven"
            lines.append(
                f"- {t['trigger_type']} ({t['cadence']}): scheduled {scheduled}; "
                f"citation: {t['citation']}. {t['note']}"
            )

    cap = plan.get("capacity_assessment") or {}
    lines.extend(["", "## Capacity assessment", ""])
    lines.append(
        f"- Weekly hours available: {cap.get('weekly_hours_available')}"
    )
    lines.append(f"- Interval weeks: {cap.get('interval_weeks')}")
    lines.append(
        f"- Hours available per milestone: {cap.get('hours_available_per_milestone')}"
    )
    for entry in cap.get("per_milestone", []):
        lines.append(
            f"  - {entry['milestone_id']}: required {entry['hours_required']}, "
            f"available {entry['hours_available']}, "
            f"exceeds={entry['exceeds_capacity']}"
        )

    cfc = plan.get("cross_framework_citations") or []
    if cfc:
        lines.extend(["", "## Cross-framework citations", ""])
        for r in cfc:
            lines.append(
                f"- {r['target_framework']} {r['target_ref']}: "
                f"{r['relationship']} (confidence: {r['confidence']}). {r['note']}"
            )

    if plan.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in plan["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(plan: dict[str, Any]) -> str:
    """Render one row per milestone."""
    if "milestones" not in plan:
        raise ValueError("plan missing required field 'milestones'")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "milestone_id",
        "target_date",
        "status",
        "hours_required",
        "remediation_count",
        "blocked_by",
        "success_criteria",
        "citations",
    ])
    for ms in plan["milestones"]:
        writer.writerow([
            ms.get("milestone_id", ""),
            ms.get("target_date", ""),
            ms.get("status", ""),
            ms.get("hours_required", ""),
            len(ms.get("remediation_action_requests", [])),
            "; ".join(ms.get("blocked_by", [])),
            "; ".join(ms.get("success_criteria", [])),
            "; ".join(ms.get("citations", [])),
        ])
    return buf.getvalue()


__all__ = [
    "AGENT_SIGNATURE",
    "REQUIRED_INPUT_FIELDS",
    "VALID_TARGET_CERTIFICATIONS",
    "VALID_MILESTONE_STATUSES",
    "DEFAULT_MILESTONE_INTERVAL_WEEKS",
    "plan_certification_path",
    "render_markdown",
    "render_csv",
]
