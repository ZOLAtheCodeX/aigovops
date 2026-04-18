"""
AIGovOps: AI System Inventory Maintainer Plugin

Produces a validated, versioned AI system inventory artifact that every
other AIGovOps plugin consumes as ``ai_system_inventory``. Closes the
loop that was previously left to practitioners maintaining a JSON file by
hand: this plugin validates required and recommended fields, tracks
lifecycle state, diffs versions, and computes a per-system regulatory
applicability matrix across jurisdictions.

Design stance: the plugin does NOT discover AI systems, assign risk
tiers, or verify that linked artifact references exist on disk. System
identification is an organizational responsibility per ISO/IEC 42001:2023
Clause 4.3 (scope determination) and Annex A Control A.5 (AI system
identification). The plugin validates an explicitly supplied inventory,
enriches it with computed applicability and optional cross-framework
references, and surfaces gaps as warnings rather than guessing.

Operations:

- ``validate``: pure validation pass. Default. No mutation of systems.
- ``update``: diff against ``previous_inventory_ref`` to emit a version
  diff (added, modified, removed, unchanged).
- ``decommission``: mark specified systems as ``decommissioned`` and
  warn downstream plugins to update their records.
- ``full-refresh``: validate every system and recompute applicability.
- ``create``: the same validation pass as ``validate`` but permits
  treating this as a first-publication timestamp.

Status: Phase 3 minimum-viable implementation.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "ai-system-inventory-maintainer/0.1.0"

REQUIRED_INPUT_FIELDS = ("systems",)

VALID_OPERATIONS = (
    "create",
    "update",
    "decommission",
    "validate",
    "full-refresh",
)

# Supports both EU AI Act tier vocabulary and ISO risk-scoring vocabulary so
# the same inventory can be shared between classifications.
VALID_RISK_TIERS = (
    "prohibited",
    "high-risk-annex-i",
    "high-risk-annex-iii",
    "limited-risk",
    "minimal-risk",
    "requires-legal-review",
    "low",
    "limited",
    "medium",
    "high",
)

VALID_DECISION_AUTHORITY = (
    "decision-support",
    "automated-with-human-oversight",
    "fully-automated",
    "advisory-only",
)

VALID_LIFECYCLE_STATE = (
    "proposed",
    "in-development",
    "pre-deployment-review",
    "deployed",
    "under-monitoring",
    "deprecated",
    "decommissioned",
)

REQUIRED_PER_SYSTEM_FIELDS = (
    "system_id",
    "system_name",
    "intended_use",
    "deployment_context",
    "risk_tier",
    "decision_authority",
    "jurisdiction",
    "lifecycle_state",
)

RECOMMENDED_PER_SYSTEM_FIELDS = (
    "data_processed",
    "stakeholder_groups",
    "owner_role",
    "operator_role",
    "model_family",
    "training_data_provenance",
    "post_market_monitoring_plan_ref",
    "risk_register_ref",
    "aisia_ref",
    "soa_ref",
    "last_reviewed_date",
    "next_review_due_date",
)

# Canonical jurisdiction identifiers per docs/jurisdiction-scope.md.
VALID_JURISDICTIONS = (
    "international",
    "eu",
    "uk",
    "usa-federal",
    "usa-co",
    "usa-nyc",
    "usa-ca",
    "canada",
    "canada-federal",
    "canada-quebec",
    "singapore",
)

# EU high-risk tier set; used for downstream applicability and citation checks.
EU_HIGH_RISK_TIERS = (
    "prohibited",
    "high-risk-annex-i",
    "high-risk-annex-iii",
)

# Sector vocabulary used for Singapore MAS FEAT and Colorado SB 205 overlays.
VALID_SECTORS = (
    "employment",
    "housing",
    "financial-services",
    "healthcare",
    "education",
    "law-enforcement",
    "critical-infrastructure",
    "public-sector",
    "other",
)

# Regex for STYLE.md citation prefixes; used in validation-stage lightweight
# compliance check.
CITATION_PREFIXES = (
    "ISO/IEC 42001:2023, ",
    "ISO 42001, ",
    "EU AI Act, ",
    "GOVERN ",
    "MAP ",
    "MEASURE ",
    "MANAGE ",
    "Colorado SB 205, ",
    "UK ATRS, ",
    "NYC LL144",
    "Singapore MAGF 2e, ",
    "MAS FEAT Principles (2018), ",
    "AI Verify (IMDA 2024), ",
    "MAS Veritas",
    "CCPA Regulations (CPPA), ",
    "California Civil Code, ",
    "California Business and Professions Code, ",
    "California Attorney General Guidance",
    "California SB 1047",
    "Canada AIDA ",
    "AIDA Section ",
    "PIPEDA, ",
    "CPPA (Bill C-27, Part 1), ",
    "OSFI Guideline E-23, ",
    "Canada Directive on Automated Decision-Making, ",
    "Quebec Law 25, ",
    "Canada Voluntary AI Code (2023), ",
    "NIST AI Risk Management Framework 1.0",
)

# Sibling-plugin path for crosswalk-matrix-builder. Matches the sibling-import
# pattern used by soa-generator.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------


def _structural_validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    systems = inputs["systems"]
    if not isinstance(systems, list):
        raise ValueError("systems must be a list")

    operation = inputs.get("operation", "validate")
    if operation not in VALID_OPERATIONS:
        raise ValueError(
            f"operation must be one of {VALID_OPERATIONS}; got {operation!r}"
        )

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")

    scope = inputs.get("organizational_scope")
    if scope is not None and not isinstance(scope, dict):
        raise ValueError("organizational_scope, when provided, must be a dict")

    for i, system in enumerate(systems):
        if not isinstance(system, dict):
            raise ValueError(f"systems[{i}] must be a dict")

        risk_tier = system.get("risk_tier")
        if risk_tier is not None and risk_tier not in VALID_RISK_TIERS:
            raise ValueError(
                f"systems[{i}] risk_tier must be one of {VALID_RISK_TIERS}; "
                f"got {risk_tier!r}"
            )

        decision_authority = system.get("decision_authority")
        if decision_authority is not None and decision_authority not in VALID_DECISION_AUTHORITY:
            raise ValueError(
                f"systems[{i}] decision_authority must be one of "
                f"{VALID_DECISION_AUTHORITY}; got {decision_authority!r}"
            )

        lifecycle_state = system.get("lifecycle_state")
        if lifecycle_state is not None and lifecycle_state not in VALID_LIFECYCLE_STATE:
            raise ValueError(
                f"systems[{i}] lifecycle_state must be one of "
                f"{VALID_LIFECYCLE_STATE}; got {lifecycle_state!r}"
            )

        jurisdiction = system.get("jurisdiction")
        if jurisdiction is not None and not isinstance(jurisdiction, (list, str)):
            raise ValueError(
                f"systems[{i}] jurisdiction must be a list or string; got "
                f"{type(jurisdiction).__name__}"
            )


def _normalize_jurisdictions(jurisdiction: Any) -> list[str]:
    if jurisdiction is None:
        return []
    if isinstance(jurisdiction, str):
        return [jurisdiction]
    return list(jurisdiction)


# ---------------------------------------------------------------------------
# Per-system content validation
# ---------------------------------------------------------------------------


def validate_system(system: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list of finding dicts for a single system.

    Each finding carries ``level`` (one of ``OK``, ``WARN``, ``FAIL``),
    ``field``, and ``message``. FAIL means a required field is missing;
    WARN means a recommended field is missing or a cross-field consistency
    rule flagged an issue; OK is emitted when the system passes every
    structural check.
    """
    findings: list[dict[str, Any]] = []

    # Required field coverage.
    for field in REQUIRED_PER_SYSTEM_FIELDS:
        value = system.get(field)
        if value is None or (isinstance(value, (str, list)) and len(value) == 0):
            findings.append({
                "level": "FAIL",
                "field": field,
                "message": (
                    f"required field {field!r} is missing or empty; every "
                    "inventory row must populate this field per ISO/IEC "
                    "42001:2023, Clause 4.3 and Annex A, Control A.5."
                ),
            })

    # Recommended field coverage (warnings only).
    for field in RECOMMENDED_PER_SYSTEM_FIELDS:
        if field not in system or system.get(field) in (None, "", [], {}):
            findings.append({
                "level": "WARN",
                "field": field,
                "message": (
                    f"recommended field {field!r} not set; audit evidence "
                    "quality improves when this field is populated."
                ),
            })

    # Jurisdiction value check (WARN for unknown to remain permissive).
    jurisdictions = _normalize_jurisdictions(system.get("jurisdiction"))
    for j in jurisdictions:
        if j not in VALID_JURISDICTIONS:
            findings.append({
                "level": "WARN",
                "field": "jurisdiction",
                "message": (
                    f"jurisdiction {j!r} is not in the canonical set "
                    f"{sorted(VALID_JURISDICTIONS)}; verify spelling or add "
                    "the jurisdiction to docs/jurisdiction-scope.md."
                ),
            })

    # Cross-reference link note (non-verifying: we do not walk the filesystem).
    for ref_field in ("aisia_ref", "risk_register_ref", "soa_ref", "post_market_monitoring_plan_ref"):
        if system.get(ref_field):
            findings.append({
                "level": "OK",
                "field": ref_field,
                "message": f"linked: {system.get(ref_field)}",
            })

    # Decision-authority consistency: fully-automated Annex III systems
    # require an AISIA reference.
    risk_tier = system.get("risk_tier")
    decision_authority = system.get("decision_authority")
    if (
        decision_authority == "fully-automated"
        and risk_tier in ("high-risk-annex-iii", "high-risk-annex-i")
        and not system.get("aisia_ref")
    ):
        findings.append({
            "level": "WARN",
            "field": "aisia_ref",
            "message": (
                "fully-automated high-risk system without aisia_ref populated; "
                "EU AI Act, Article 27 (fundamental-rights impact assessment) "
                "requires an AISIA before deployment."
            ),
        })

    # Jurisdiction consistency: EU-scope high-risk systems need EU AI Act
    # citations in their citations block.
    is_eu = any(j == "eu" for j in jurisdictions)
    if is_eu and risk_tier in EU_HIGH_RISK_TIERS:
        citations = system.get("citations") or []
        has_eu_citation = any(
            isinstance(c, str) and c.startswith("EU AI Act, ") for c in citations
        )
        if not has_eu_citation:
            findings.append({
                "level": "WARN",
                "field": "citations",
                "message": (
                    "EU-scope high-risk system without EU AI Act article "
                    "citations; Chapter III obligations require explicit "
                    "article references."
                ),
            })

    # Emit an OK summary finding when no FAIL found and no critical gaps.
    has_fail = any(f["level"] == "FAIL" for f in findings)
    if not has_fail:
        findings.append({
            "level": "OK",
            "field": "__summary__",
            "message": "all required fields populated; see WARN items for recommended gaps.",
        })

    return findings


# ---------------------------------------------------------------------------
# Applicability matrix
# ---------------------------------------------------------------------------


def _compute_applicability(system: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the list of frameworks applicable to this system.

    Each entry is a dict with ``framework``, ``citation``, ``rationale``.
    """
    entries: list[dict[str, Any]] = []
    jurisdictions = _normalize_jurisdictions(system.get("jurisdiction"))
    risk_tier = system.get("risk_tier")
    deployment_context = (system.get("deployment_context") or "").lower()
    sector = (system.get("sector") or "").lower()

    # ISO 42001 applies to every system as the international baseline.
    entries.append({
        "framework": "iso42001",
        "citation": "ISO/IEC 42001:2023, Clause 4.3",
        "rationale": (
            "ISO/IEC 42001:2023 applies to every AI system in the AIMS "
            "scope as the international management-system baseline."
        ),
    })

    # NIST AI RMF applies to every USA federal or contractor system (de facto).
    if any(j.startswith("usa") for j in jurisdictions):
        entries.append({
            "framework": "nist-ai-rmf",
            "citation": "GOVERN 1.1",
            "rationale": (
                "NIST AI Risk Management Framework 1.0 is the de facto USA "
                "federal and contractor baseline. Applies to USA-scope "
                "systems."
            ),
        })

    # EU AI Act for EU-scope systems.
    if "eu" in jurisdictions:
        if risk_tier == "prohibited":
            entries.append({
                "framework": "eu-ai-act",
                "citation": "EU AI Act, Article 5",
                "rationale": (
                    "Prohibited practice under EU AI Act, Article 5. "
                    "Placing on market or putting into service is "
                    "prohibited."
                ),
            })
        elif risk_tier in ("high-risk-annex-i", "high-risk-annex-iii"):
            entries.append({
                "framework": "eu-ai-act",
                "citation": "EU AI Act, Chapter III",
                "rationale": (
                    "High-risk AI system under EU AI Act, Article 6. "
                    "Chapter III obligations apply (risk management, data "
                    "governance, technical documentation, record-keeping, "
                    "transparency, human oversight, accuracy, robustness, "
                    "cybersecurity)."
                ),
            })
        else:
            entries.append({
                "framework": "eu-ai-act",
                "citation": "EU AI Act, Article 50",
                "rationale": (
                    "Non-high-risk EU-scope AI system. Article 50 "
                    "transparency obligations apply where the system "
                    "interacts with natural persons."
                ),
            })

    # NYC LL144 for NYC employment systems.
    is_nyc = "usa-nyc" in jurisdictions
    mentions_employment = (
        "employment" in deployment_context
        or "hiring" in deployment_context
        or "candidate" in deployment_context
        or sector == "employment"
    )
    if is_nyc and mentions_employment:
        entries.append({
            "framework": "nyc-ll144",
            "citation": "NYC LL144 Final Rule, Section 5-301",
            "rationale": (
                "Automated Employment Decision Tool used to screen "
                "candidates for employment or promotion in NYC. Annual "
                "bias audit and candidate notice required."
            ),
        })

    # Colorado SB 205 for Colorado consequential-decision systems.
    is_co = "usa-co" in jurisdictions
    consequential_domains = (
        "employment", "housing", "education", "financial",
        "healthcare", "insurance", "legal", "government",
    )
    mentions_consequential = any(d in deployment_context for d in consequential_domains) or sector in consequential_domains
    if is_co and mentions_consequential:
        entries.append({
            "framework": "colorado-sb-205",
            "citation": "Colorado SB 205, Section 6-1-1701(3)",
            "rationale": (
                "Consequential-decision system under Colorado SB 205. "
                "Developer and deployer obligations apply. Conformance "
                "with NIST AI RMF 1.0 or ISO/IEC 42001:2023 creates a "
                "rebuttable presumption of reasonable care per Section "
                "6-1-1706(3)."
            ),
        })

    # Singapore MAS FEAT on top of MAGF for financial-services deployments.
    is_sg = "singapore" in jurisdictions
    if is_sg:
        entries.append({
            "framework": "singapore-magf-2e",
            "citation": "Singapore MAGF 2e, Pillar Internal Governance Structures and Measures",
            "rationale": (
                "Singapore Model AI Governance Framework (IMDA/PDPC MAGF "
                "2e) applies to AI systems operated in Singapore."
            ),
        })
        if sector == "financial-services" or "financial" in deployment_context:
            entries.append({
                "framework": "mas-feat",
                "citation": "MAS FEAT Principles (2018), Principle Accountability",
                "rationale": (
                    "MAS FEAT Principles (Fairness, Ethics, Accountability, "
                    "Transparency) layer on top of MAGF for financial-"
                    "services AI deployments in Singapore."
                ),
            })

    # UK ATRS for UK public-sector systems.
    is_uk = "uk" in jurisdictions
    if is_uk and (sector == "public-sector" or "public" in deployment_context or "government" in deployment_context):
        entries.append({
            "framework": "uk-atrs",
            "citation": "UK ATRS, Section Tool description",
            "rationale": (
                "UK public-sector AI system. Algorithmic Transparency "
                "Recording Standard Tier 1 record required."
            ),
        })

    return entries


# ---------------------------------------------------------------------------
# Diff for version tracking
# ---------------------------------------------------------------------------


def _load_previous_inventory(ref: str) -> list[dict[str, Any]]:
    """Load a previous inventory from a path. Out-of-repo URLs are not fetched."""
    path = Path(ref)
    if not path.exists():
        raise ValueError(
            f"previous_inventory_ref {ref!r} is not a readable path. "
            "URL fetch is out of scope; supply a local JSON file."
        )
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if isinstance(data, dict) and "systems" in data:
        data = data["systems"]
    if not isinstance(data, list):
        raise ValueError(
            f"previous_inventory_ref {ref!r} must contain a list of systems "
            "(optionally under a top-level 'systems' key)."
        )
    return data


def _compare_systems(new_system: dict[str, Any], old_system: dict[str, Any]) -> list[str]:
    """Return field names that differ between new and old system dicts."""
    changed: list[str] = []
    all_fields = set(new_system.keys()) | set(old_system.keys())
    internal = {"regulatory_applicability", "validation_findings", "cross_framework_references"}
    for field in all_fields - internal:
        if new_system.get(field) != old_system.get(field):
            changed.append(field)
    return sorted(changed)


def _diff_inventory(
    new_systems: list[dict[str, Any]],
    previous_systems: list[dict[str, Any]],
) -> dict[str, Any]:
    new_by_id = {s.get("system_id"): s for s in new_systems if s.get("system_id")}
    old_by_id = {s.get("system_id"): s for s in previous_systems if s.get("system_id")}

    added = sorted(set(new_by_id) - set(old_by_id))
    removed = sorted(set(old_by_id) - set(new_by_id))
    common = set(new_by_id) & set(old_by_id)

    modified: list[dict[str, Any]] = []
    unchanged: list[str] = []
    for sid in sorted(common):
        diffs = _compare_systems(new_by_id[sid], old_by_id[sid])
        if diffs:
            modified.append({"system_id": sid, "changed_fields": diffs})
        else:
            unchanged.append(sid)

    return {
        "added": added,
        "modified": modified,
        "removed": removed,
        "unchanged": unchanged,
    }


# ---------------------------------------------------------------------------
# Crosswalk enrichment (opt-out)
# ---------------------------------------------------------------------------


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_inventory", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enrich_with_crosswalk(
    systems: list[dict[str, Any]],
) -> list[str]:
    """Attach ``cross_framework_references`` to each system in-place.

    Returns a list of top-level warnings if the crosswalk data fails to
    load.
    """
    try:
        crosswalk = _load_crosswalk_module()
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:  # noqa: BLE001
        return [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"]

    # Index by source_framework and source_ref for quick lookup.
    by_source: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for m in data.get("mappings", []):
        key = (m.get("source_framework"), m.get("source_ref"))
        by_source.setdefault(key, []).append(m)

    for system in systems:
        refs: list[dict[str, Any]] = []
        applicability = system.get("regulatory_applicability") or []
        seen: set[tuple[str, str, str]] = set()

        for entry in applicability:
            framework = entry.get("framework")
            citation = entry.get("citation") or ""
            # Look up crosswalk rows where this applicability framework is
            # the source_framework and the citation prefix matches.
            for (src_fw, src_ref), matches in by_source.items():
                if src_fw != framework:
                    continue
                if src_ref and src_ref not in citation and citation not in src_ref:
                    continue
                for m in matches:
                    key = (
                        m.get("source_framework") or "",
                        m.get("target_framework") or "",
                        m.get("target_ref") or "",
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    citation_sources = m.get("citation_sources") or []
                    citation_label = ""
                    if citation_sources:
                        citation_label = (citation_sources[0].get("publication") or "").strip()
                    refs.append({
                        "framework": m.get("target_framework"),
                        "citation": m.get("target_ref"),
                        "relationship": m.get("relationship"),
                        "applicability_rationale": (
                            f"mapped from {m.get('source_framework')} "
                            f"{m.get('source_ref')} per {citation_label or 'crosswalk-matrix-builder data'}."
                        ),
                    })
        system["cross_framework_references"] = refs

    return []


# ---------------------------------------------------------------------------
# Canonical entry point
# ---------------------------------------------------------------------------


def maintain_inventory(inputs: dict[str, Any]) -> dict[str, Any]:
    """Produce a validated, versioned AI system inventory artifact.

    Args:
        inputs: Dict with:
            systems (required): list of AI system dicts.
            operation: one of VALID_OPERATIONS; default 'validate'.
            previous_inventory_ref: path to prior inventory JSON for diff.
            organizational_scope: dict with jurisdictions, sectors,
                decision_domains used for applicability scoping.
            enrich_with_crosswalk: bool; default True. When True, attach
                cross_framework_references per system.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, operation, reviewed_by,
        systems (enriched), version_diff (when operation='update'),
        validation_findings (per system), regulatory_applicability_matrix,
        citations, warnings, summary.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _structural_validate(inputs)

    operation = inputs.get("operation", "validate")
    systems_input: list[dict[str, Any]] = [dict(s) for s in inputs["systems"]]
    decommission_target_ids = inputs.get("decommission_system_ids") or []

    # Operation-specific mutation.
    if operation == "decommission":
        target_ids = set(decommission_target_ids)
        if not target_ids:
            target_ids = {s.get("system_id") for s in systems_input if s.get("system_id")}
        for s in systems_input:
            if s.get("system_id") in target_ids:
                s["lifecycle_state"] = "decommissioned"

    # Per-system validation and applicability.
    findings_per_system: dict[str, list[dict[str, Any]]] = {}
    register_warnings: list[str] = []

    for system in systems_input:
        sid = system.get("system_id") or f"<index-{systems_input.index(system)}>"
        findings = validate_system(system)
        findings_per_system[sid] = findings
        # Attach an applicability list to the system row.
        system["regulatory_applicability"] = _compute_applicability(system)

    # Operation-specific: decommission warning.
    if operation == "decommission":
        decommissioned = [s for s in systems_input if s.get("lifecycle_state") == "decommissioned"]
        if decommissioned:
            register_warnings.append(
                f"{len(decommissioned)} system(s) marked decommissioned. "
                "Downstream plugins (soa-generator, risk-register-builder, "
                "audit-log-generator) must update their records to reflect "
                "the lifecycle change. Trigger a management-review-packager "
                "run per Clause 9.3.2."
            )

    # Version diff.
    version_diff: dict[str, Any] | None = None
    previous_ref = inputs.get("previous_inventory_ref")
    if operation == "update" and previous_ref:
        previous = _load_previous_inventory(previous_ref)
        version_diff = _diff_inventory(systems_input, previous)
    elif operation == "update" and not previous_ref:
        register_warnings.append(
            "operation='update' requires previous_inventory_ref to produce "
            "a diff; version_diff omitted."
        )

    # Crosswalk enrichment (opt-out).
    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True
    if enrich:
        crosswalk_warnings = _enrich_with_crosswalk(systems_input)
        register_warnings.extend(crosswalk_warnings)

    # Summary computation.
    by_risk_tier: dict[str, int] = {}
    by_jurisdiction: dict[str, int] = {}
    by_lifecycle_state: dict[str, int] = {}
    systems_missing_required: list[str] = []
    systems_with_warnings: list[str] = []
    applicability_matrix: list[dict[str, Any]] = []

    for system in systems_input:
        sid = system.get("system_id") or "<unknown>"
        tier = system.get("risk_tier") or "<unset>"
        lifecycle = system.get("lifecycle_state") or "<unset>"
        by_risk_tier[tier] = by_risk_tier.get(tier, 0) + 1
        by_lifecycle_state[lifecycle] = by_lifecycle_state.get(lifecycle, 0) + 1
        for j in _normalize_jurisdictions(system.get("jurisdiction")):
            by_jurisdiction[j] = by_jurisdiction.get(j, 0) + 1
        findings = findings_per_system.get(sid, [])
        if any(f["level"] == "FAIL" for f in findings):
            systems_missing_required.append(sid)
        if any(f["level"] == "WARN" for f in findings):
            systems_with_warnings.append(sid)
        applicability_matrix.append({
            "system_id": sid,
            "system_name": system.get("system_name"),
            "frameworks": [e["framework"] for e in system.get("regulatory_applicability", [])],
            "entries": system.get("regulatory_applicability", []),
        })

    # Top-level citations.
    citations: list[str] = [
        "ISO/IEC 42001:2023, Clause 4.3",
        "ISO/IEC 42001:2023, Clause 7.5.1",
        "ISO/IEC 42001:2023, Clause 7.5.2",
        "ISO/IEC 42001:2023, Clause 7.5.3",
        "ISO/IEC 42001:2023, Annex A, Control A.5.2",
        "GOVERN 1.6",
        "EU AI Act, Article 11",
    ]

    summary = {
        "total_systems": len(systems_input),
        "by_risk_tier": by_risk_tier,
        "by_jurisdiction": by_jurisdiction,
        "by_lifecycle_state": by_lifecycle_state,
        "systems_missing_required_fields": systems_missing_required,
        "systems_with_warnings": systems_with_warnings,
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "operation": operation,
        "reviewed_by": inputs.get("reviewed_by"),
        "systems": systems_input,
        "validation_findings": findings_per_system,
        "regulatory_applicability_matrix": applicability_matrix,
        "citations": citations,
        "warnings": register_warnings,
        "summary": summary,
    }
    if version_diff is not None:
        output["version_diff"] = version_diff
    return output


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_markdown(inventory: dict[str, Any]) -> str:
    required = ("timestamp", "agent_signature", "operation", "systems", "summary")
    missing = [k for k in required if k not in inventory]
    if missing:
        raise ValueError(f"inventory missing required fields: {missing}")

    lines: list[str] = [
        "# AI System Inventory",
        "",
        f"**Generated at (UTC):** {inventory['timestamp']}",
        f"**Generated by:** {inventory['agent_signature']}",
        f"**Operation:** {inventory['operation']}",
    ]
    if inventory.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {inventory['reviewed_by']}")

    summary = inventory["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Total systems: {summary['total_systems']}",
        f"- By risk tier: {', '.join(f'{k}={v}' for k, v in summary['by_risk_tier'].items()) or 'none'}",
        f"- By jurisdiction: {', '.join(f'{k}={v}' for k, v in summary['by_jurisdiction'].items()) or 'none'}",
        f"- By lifecycle state: {', '.join(f'{k}={v}' for k, v in summary['by_lifecycle_state'].items()) or 'none'}",
        f"- Systems missing required fields: {len(summary['systems_missing_required_fields'])}",
        f"- Systems with warnings: {len(summary['systems_with_warnings'])}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in inventory.get("citations", []):
        lines.append(f"- {c}")

    lines.extend(["", "## Applicability matrix", ""])
    matrix = inventory.get("regulatory_applicability_matrix", [])
    if not matrix:
        lines.append("(no systems in inventory)")
    else:
        lines.append("| System ID | System Name | Applicable Frameworks |")
        lines.append("|---|---|---|")
        for entry in matrix:
            frameworks = ", ".join(entry.get("frameworks", [])) or "(none computed)"
            lines.append(
                f"| {entry.get('system_id', '')} | {entry.get('system_name', '') or ''} | {frameworks} |"
            )

    lines.extend(["", "## Validation findings", ""])
    findings_map = inventory.get("validation_findings", {})
    if not findings_map:
        lines.append("(no validation findings recorded)")
    else:
        for sid, findings in findings_map.items():
            lines.append(f"### {sid}")
            lines.append("")
            for f in findings:
                lines.append(f"- [{f['level']}] {f.get('field', '')}: {f.get('message', '')}")
            lines.append("")

    lines.extend(["## Per-system details", ""])
    for system in inventory["systems"]:
        sid = system.get("system_id", "<unknown>")
        lines.append(f"### {sid}: {system.get('system_name', '')}")
        lines.append("")
        lines.append(f"- Intended use: {system.get('intended_use', '')}")
        lines.append(f"- Deployment context: {system.get('deployment_context', '')}")
        lines.append(f"- Risk tier: {system.get('risk_tier', '')}")
        lines.append(f"- Decision authority: {system.get('decision_authority', '')}")
        j = _normalize_jurisdictions(system.get("jurisdiction"))
        lines.append(f"- Jurisdiction: {', '.join(j) or '(unset)'}")
        lines.append(f"- Lifecycle state: {system.get('lifecycle_state', '')}")
        lines.append(f"- Owner role: {system.get('owner_role', '')}")
        refs = system.get("cross_framework_references")
        if refs is not None:
            lines.append(f"- Cross-framework references: {len(refs)} entries")
        lines.append("")

    diff = inventory.get("version_diff")
    if diff is not None:
        lines.extend(["## Version diff", ""])
        lines.append(f"- Added: {', '.join(diff.get('added', [])) or 'none'}")
        lines.append(f"- Removed: {', '.join(diff.get('removed', [])) or 'none'}")
        lines.append(f"- Unchanged: {', '.join(diff.get('unchanged', [])) or 'none'}")
        modified = diff.get("modified", [])
        if modified:
            lines.append("- Modified:")
            for m in modified:
                lines.append(
                    f"  - {m['system_id']}: {', '.join(m['changed_fields'])}"
                )
        else:
            lines.append("- Modified: none")
        lines.append("")

    warnings = inventory.get("warnings", [])
    if warnings:
        lines.extend(["## Warnings", ""])
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def render_csv(inventory: dict[str, Any]) -> str:
    if "systems" not in inventory:
        raise ValueError("inventory missing 'systems' field")
    header = (
        "system_id,system_name,risk_tier,decision_authority,jurisdiction,"
        "lifecycle_state,intended_use,deployment_context,owner_role,"
        "aisia_ref,risk_register_ref,soa_ref,applicable_frameworks"
    )
    lines = [header]
    for system in inventory["systems"]:
        jurisdictions = "; ".join(_normalize_jurisdictions(system.get("jurisdiction")))
        frameworks = "; ".join(
            e.get("framework", "") for e in system.get("regulatory_applicability", [])
        )
        fields = [
            _csv_escape(str(system.get("system_id", ""))),
            _csv_escape(str(system.get("system_name", "") or "")),
            _csv_escape(str(system.get("risk_tier", "") or "")),
            _csv_escape(str(system.get("decision_authority", "") or "")),
            _csv_escape(jurisdictions),
            _csv_escape(str(system.get("lifecycle_state", "") or "")),
            _csv_escape(str(system.get("intended_use", "") or "")),
            _csv_escape(str(system.get("deployment_context", "") or "")),
            _csv_escape(str(system.get("owner_role", "") or "")),
            _csv_escape(str(system.get("aisia_ref", "") or "")),
            _csv_escape(str(system.get("risk_register_ref", "") or "")),
            _csv_escape(str(system.get("soa_ref", "") or "")),
            _csv_escape(frameworks),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value


__all__ = [
    "AGENT_SIGNATURE",
    "REQUIRED_INPUT_FIELDS",
    "VALID_OPERATIONS",
    "VALID_RISK_TIERS",
    "VALID_DECISION_AUTHORITY",
    "VALID_LIFECYCLE_STATE",
    "REQUIRED_PER_SYSTEM_FIELDS",
    "RECOMMENDED_PER_SYSTEM_FIELDS",
    "VALID_JURISDICTIONS",
    "maintain_inventory",
    "validate_system",
    "render_markdown",
    "render_csv",
]
