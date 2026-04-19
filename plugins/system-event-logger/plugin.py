"""
AIGovOps: System Event Logger Plugin

Operationalizes the SYSTEM-OPERATIONAL event log schema, retention policy,
and traceability structure required by EU AI Act Article 12 (automatic
recording of events over the lifetime of a high-risk AI system), Article
19 (log retention minimum 6 months, longer where sectoral law requires),
ISO/IEC 42001:2023 Annex A Control A.6.2.8 (AI system recording of event
logs), and NIST AI RMF MEASURE 2.8 (transparency and accountability).

Distinct from `audit-log-generator`:
    audit-log-generator emits GOVERNANCE-EVENT records (management
    decisions, review minutes, authority exercises). That layer serves
    ISO/IEC 42001:2023 Clause 9.1 and Annex A Control A.6.2.3 evidence
    needs.

    system-event-logger specifies the SYSTEM-OPERATIONAL event log:
    inference request/output, drift signals, safety events, override
    actions, data-access events, biometric-verification records, and
    other system-level telemetry required for Article 12(2) traceability
    and Article 19 retention. It produces a SCHEMA artifact (shape,
    retention policy, tamper-evidence plan), NOT runtime log entries.

Design stance: the plugin does NOT generate log entries, does NOT verify
that log files exist on disk, and does NOT invent retention periods,
tamper-evidence methods, or traceability mappings. Every substantive
content field either comes from input, is computed deterministically
from input, or is flagged as requiring human input.

Public API:
    define_event_schema(inputs)    canonical entry point
    render_markdown(schema)        audit-evidence Markdown rendering
    render_csv(schema)             per-field CSV of the normalized schema

Status: Phase 3 minimum-viable implementation. 0.1.0.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "system-event-logger/0.1.0"

REQUIRED_INPUT_FIELDS = ("system_description", "event_schema", "retention_policy")

EU_ART_19_MIN_RETENTION_MONTHS = 6
EU_ART_19_MIN_RETENTION_DAYS = 183

VALID_EVENT_CATEGORIES = (
    "inference-request",
    "inference-output",
    "risk-signal",
    "drift-signal",
    "safety-event",
    "override-action",
    "consumer-complaint",
    "auth-event",
    "config-change",
    "model-update",
    "data-access",
    "biometric-verification",
)

VALID_RETENTION_POLICIES = (
    "eu-art-19-minimum",
    "eu-art-19-extended",
    "sectoral-finance",
    "sectoral-healthcare",
    "internal-only",
    "none",
)

BIOMETRIC_REQUIRED_FIELDS = (
    "start_datetime",
    "end_datetime",
    "reference_database",
    "input_data_ref",
    "verification_result",
    "operating_person_identity",
)

VALID_RISK_TIERS = (
    "minimal-risk",
    "limited-risk",
    "high-risk-annex-i",
    "high-risk-annex-iii",
    "general-purpose-ai",
    "prohibited",
    "out-of-scope",
)

VALID_LIFECYCLE_STATES = (
    "design",
    "development",
    "verification",
    "deployment",
    "in-service",
    "decommissioned",
)

VALID_TAMPER_EVIDENCE_METHODS = (
    "hash-chain",
    "hmac",
    "cryptographic-signing",
    "append-only-store",
    "external-notary",
)

# Article 12(2) traceability purposes. Every category declared in scope
# should map to at least one of these via traceability_mappings.
ART_12_2_PURPOSES = ("a", "b", "c")
ART_12_2_PURPOSE_TEXT = {
    "a": "identifying situations that may result in the AI system presenting a risk within the meaning of Article 79(1)",
    "b": "facilitating post-market monitoring per Article 72",
    "c": "monitoring the operation of high-risk AI systems per Article 26(5)",
}

CROSS_FRAMEWORK_SEL_REFERENCES: tuple[dict[str, Any], ...] = (
    {
        "target_framework": "iso42001",
        "target_ref": "A.6.2.8",
        "relationship": "satisfies",
        "confidence": "high",
        "note": "ISO/IEC 42001:2023 Annex A Control A.6.2.8 directly satisfies Article 12(1) automatic-logging duty.",
    },
    {
        "target_framework": "iso42001",
        "target_ref": "A.6.2.8; Clause 9.1",
        "relationship": "satisfies",
        "confidence": "high",
        "note": "A.6.2.8 event logging combined with Clause 9.1 monitoring delivers Article 12(2) traceability proportional to purpose.",
    },
    {
        "target_framework": "iso42001",
        "target_ref": "A.6.2.8; Clause 7.5.3",
        "relationship": "partial-satisfaction",
        "confidence": "high",
        "note": "ISO 42001 Clause 7.5.3 documented-information retention discipline partially satisfies Article 19; ISO does not set the six-month floor.",
    },
    {
        "target_framework": "nist-ai-rmf",
        "target_ref": "MEASURE 2.8",
        "relationship": "satisfies",
        "confidence": "high",
        "note": "NIST AI RMF MEASURE 2.8 transparency-and-accountability posture is satisfied by the event-log schema and retention policy.",
    },
)

# Sibling-plugin path for crosswalk-matrix-builder. Lazy-imported inside
# the enrichment helper so basic calls (enrich_with_crosswalk=False) pay
# no import cost and are unaffected by crosswalk-side failures.
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
    for key in ("system_id", "risk_tier", "jurisdiction", "remote_biometric_id", "sector", "lifecycle_state"):
        if key not in sd:
            raise ValueError(f"system_description missing required field {key!r}")
    if sd["risk_tier"] not in VALID_RISK_TIERS:
        raise ValueError(
            f"system_description.risk_tier must be one of {VALID_RISK_TIERS}; got {sd['risk_tier']!r}"
        )
    if not isinstance(sd["remote_biometric_id"], bool):
        raise ValueError("system_description.remote_biometric_id must be a bool")
    if sd["lifecycle_state"] not in VALID_LIFECYCLE_STATES:
        raise ValueError(
            f"system_description.lifecycle_state must be one of {VALID_LIFECYCLE_STATES}; got {sd['lifecycle_state']!r}"
        )

    event_schema = inputs["event_schema"]
    if not isinstance(event_schema, dict):
        raise ValueError("event_schema must be a dict keyed by event category")
    if not event_schema:
        raise ValueError("event_schema must not be empty")
    for category, fields_spec in event_schema.items():
        if category not in VALID_EVENT_CATEGORIES:
            raise ValueError(
                f"event_schema contains invalid category {category!r}; "
                f"must be one of {VALID_EVENT_CATEGORIES}"
            )
        if not isinstance(fields_spec, dict):
            raise ValueError(f"event_schema[{category!r}] must be a dict of field_name to field spec")
        for field_name, field_spec in fields_spec.items():
            if not isinstance(field_name, str) or not field_name:
                raise ValueError(
                    f"event_schema[{category!r}] contains invalid field name {field_name!r}"
                )
            if not isinstance(field_spec, dict):
                raise ValueError(
                    f"event_schema[{category!r}][{field_name!r}] must be a dict with type, required, description"
                )

    retention = inputs["retention_policy"]
    if not isinstance(retention, dict):
        raise ValueError("retention_policy must be a dict")
    for key in ("policy_name", "minimum_days", "maximum_days", "deletion_procedure_ref", "legal_basis_citation"):
        if key not in retention:
            raise ValueError(f"retention_policy missing required field {key!r}")
    if retention["policy_name"] not in VALID_RETENTION_POLICIES:
        raise ValueError(
            f"retention_policy.policy_name must be one of {VALID_RETENTION_POLICIES}; "
            f"got {retention['policy_name']!r}"
        )
    min_days = retention["minimum_days"]
    if not isinstance(min_days, int) or isinstance(min_days, bool) or min_days < 0:
        raise ValueError("retention_policy.minimum_days must be a non-negative int")
    max_days = retention["maximum_days"]
    if max_days is not None and (not isinstance(max_days, int) or isinstance(max_days, bool) or max_days < 0):
        raise ValueError("retention_policy.maximum_days must be a non-negative int or null")

    storage = inputs.get("log_storage")
    if storage is not None:
        if not isinstance(storage, dict):
            raise ValueError("log_storage, when provided, must be a dict")
        if "encryption_at_rest" in storage and not isinstance(storage["encryption_at_rest"], bool):
            raise ValueError("log_storage.encryption_at_rest must be a bool")
        tamper = storage.get("tamper_evidence_method")
        if tamper is not None and tamper != "" and tamper not in VALID_TAMPER_EVIDENCE_METHODS:
            raise ValueError(
                f"log_storage.tamper_evidence_method {tamper!r} is not a recognised method. "
                f"Must be one of {VALID_TAMPER_EVIDENCE_METHODS} or absent."
            )

    mappings = inputs.get("traceability_mappings")
    if mappings is not None:
        if not isinstance(mappings, dict):
            raise ValueError("traceability_mappings, when provided, must be a dict")
        for category, purposes in mappings.items():
            if category not in VALID_EVENT_CATEGORIES:
                raise ValueError(
                    f"traceability_mappings key {category!r} is not a valid event category"
                )
            if not isinstance(purposes, (list, tuple)):
                raise ValueError(
                    f"traceability_mappings[{category!r}] must be a list of Article 12(2) purpose letters"
                )
            for p in purposes:
                if p not in ART_12_2_PURPOSES:
                    raise ValueError(
                        f"traceability_mappings[{category!r}] contains invalid purpose {p!r}; "
                        f"must be one of {ART_12_2_PURPOSES}"
                    )

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_eu(system_description: dict[str, Any]) -> bool:
    jurisdiction = system_description.get("jurisdiction", "")
    if isinstance(jurisdiction, list):
        return any(str(j).lower() == "eu" or "eu" in str(j).lower() for j in jurisdiction)
    return "eu" in str(jurisdiction).lower()


def _is_high_risk(system_description: dict[str, Any]) -> bool:
    return system_description.get("risk_tier") in ("high-risk-annex-i", "high-risk-annex-iii")


def _assess_art_12_applicability(system_description: dict[str, Any]) -> dict[str, Any]:
    is_eu = _is_eu(system_description)
    is_hr = _is_high_risk(system_description)
    if is_eu and is_hr:
        status = "mandatory"
        rationale = (
            "System is EU-jurisdiction high-risk. EU AI Act Article 12 automatic-logging "
            "obligation applies for the lifetime of the system."
        )
    elif is_eu:
        status = "recommended-not-mandated"
        rationale = (
            "System is EU-jurisdiction but not high-risk. Article 12 does not mandate logging; "
            "event logging is recommended for post-market monitoring and incident diagnosis."
        )
    else:
        status = "recommended-not-mandated"
        rationale = (
            "System is non-EU. Article 12 does not directly apply; event logging is recommended "
            "to satisfy ISO/IEC 42001:2023 Annex A Control A.6.2.8 and NIST AI RMF MEASURE 2.8."
        )
    return {
        "status": status,
        "rationale": rationale,
        "jurisdiction": system_description.get("jurisdiction"),
        "risk_tier": system_description.get("risk_tier"),
        "citations": [
            "EU AI Act, Article 12, Paragraph 1",
        ],
    }


def _normalize_event_schema(event_schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten event_schema to a list of field-level rows for rendering and CSV."""
    rows: list[dict[str, Any]] = []
    for category in sorted(event_schema.keys()):
        fields_spec = event_schema[category]
        for field_name in sorted(fields_spec.keys()):
            spec = fields_spec[field_name] or {}
            rows.append({
                "category": category,
                "field_name": field_name,
                "type": spec.get("type", "REQUIRES PRACTITIONER ASSIGNMENT"),
                "required": bool(spec.get("required", False)),
                "description": spec.get("description", ""),
            })
    return rows


def _check_biometric_requirements(
    system_description: dict[str, Any],
    event_schema: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    if not system_description.get("remote_biometric_id"):
        return None, warnings
    biometric_spec = event_schema.get("biometric-verification")
    present_fields: list[str] = []
    missing_fields: list[str] = []
    if not isinstance(biometric_spec, dict):
        warnings.append(
            "System is a remote biometric identification system but event_schema has no "
            "'biometric-verification' category. EU AI Act, Article 12, Paragraph 3 requires "
            "six specific fields; supply a biometric-verification category."
        )
        missing_fields = list(BIOMETRIC_REQUIRED_FIELDS)
    else:
        for required_field in BIOMETRIC_REQUIRED_FIELDS:
            if required_field in biometric_spec:
                present_fields.append(required_field)
            else:
                missing_fields.append(required_field)
        for missing in missing_fields:
            warnings.append(
                f"Biometric-verification field {missing!r} absent. "
                "EU AI Act, Article 12, Paragraph 3 requires this field for remote biometric identification systems."
            )
    return (
        {
            "applicable": True,
            "required_fields": list(BIOMETRIC_REQUIRED_FIELDS),
            "present_fields": present_fields,
            "missing_fields": missing_fields,
            "satisfied": not missing_fields,
            "citations": ["EU AI Act, Article 12, Paragraph 3"],
        },
        warnings,
    )


def _assess_traceability_coverage(
    event_schema: dict[str, Any],
    traceability_mappings: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    mappings = traceability_mappings or {}
    covered_categories_by_purpose: dict[str, list[str]] = {p: [] for p in ART_12_2_PURPOSES}
    for category, purposes in mappings.items():
        if category not in event_schema:
            warnings.append(
                f"traceability_mappings references category {category!r} not present in event_schema"
            )
            continue
        for p in purposes:
            covered_categories_by_purpose[p].append(category)

    per_purpose: list[dict[str, Any]] = []
    for p in ART_12_2_PURPOSES:
        covered = sorted(set(covered_categories_by_purpose[p]))
        per_purpose.append({
            "purpose": p,
            "purpose_text": ART_12_2_PURPOSE_TEXT[p],
            "covered_categories": covered,
            "covered": bool(covered),
            "citation": f"EU AI Act, Article 12, Paragraph 2, Point ({p})",
        })
        if not covered:
            warnings.append(
                f"No event category maps to EU AI Act, Article 12, Paragraph 2, Point ({p}) "
                f"({ART_12_2_PURPOSE_TEXT[p]}). Supply traceability_mappings for at least one category."
            )

    return (
        {
            "per_purpose": per_purpose,
            "all_purposes_covered": all(entry["covered"] for entry in per_purpose),
            "citations": ["EU AI Act, Article 12, Paragraph 2"],
        },
        warnings,
    )


def _assess_retention_policy(
    system_description: dict[str, Any],
    retention_policy: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    is_eu_hr = _is_eu(system_description) and _is_high_risk(system_description)
    policy_name = retention_policy.get("policy_name")
    minimum_days = retention_policy.get("minimum_days", 0)
    legal_basis = retention_policy.get("legal_basis_citation") or ""

    floor_satisfied = minimum_days >= EU_ART_19_MIN_RETENTION_DAYS
    assessment: dict[str, Any] = {
        "policy_name": policy_name,
        "minimum_days": minimum_days,
        "maximum_days": retention_policy.get("maximum_days"),
        "deletion_procedure_ref": retention_policy.get("deletion_procedure_ref"),
        "legal_basis_citation": legal_basis,
        "eu_art_19_minimum_days": EU_ART_19_MIN_RETENTION_DAYS,
        "eu_art_19_floor_satisfied": floor_satisfied,
        "applicable_regime": "eu-high-risk" if is_eu_hr else "other",
        "citations": ["EU AI Act, Article 19, Paragraph 1"],
    }

    if policy_name == "none":
        if is_eu_hr:
            warnings.append(
                "retention_policy.policy_name is 'none' for an EU high-risk system. "
                "EU AI Act, Article 19, Paragraph 1 requires at least six months of log retention. "
                "Blocking: change policy_name to 'eu-art-19-minimum' or an extended policy."
            )
        else:
            warnings.append(
                "retention_policy.policy_name is 'none'. Logs will not be retained. "
                "This is incompatible with ISO/IEC 42001:2023 Annex A Control A.6.2.8 evidence expectations."
            )

    if is_eu_hr and not floor_satisfied and policy_name != "none":
        warnings.append(
            f"retention_policy.minimum_days={minimum_days} is below EU AI Act, Article 19, "
            f"Paragraph 1 six-month floor ({EU_ART_19_MIN_RETENTION_DAYS} days). "
            "Blocking for high-risk EU systems. Increase minimum_days or cite a Union or national "
            "law that shortens retention (no such provision exists in the AI Act itself)."
        )

    if policy_name in ("sectoral-finance", "sectoral-healthcare") and not str(legal_basis).strip():
        warnings.append(
            f"retention_policy.policy_name={policy_name!r} indicates sectoral retention, "
            "but legal_basis_citation is empty. EU AI Act, Article 19, Paragraph 2 requires that "
            "sectoral periods be justified by the governing sectoral regulation; supply the citation."
        )

    if policy_name == "sectoral-finance":
        assessment["citations"].append("EU AI Act, Article 19, Paragraph 2")

    return assessment, warnings


def _assess_tamper_evidence(log_storage: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    storage = log_storage or {}
    method = storage.get("tamper_evidence_method")
    has_method = bool(method and str(method).strip())
    assessment = {
        "storage_system": storage.get("storage_system"),
        "encryption_at_rest": storage.get("encryption_at_rest"),
        "access_controls_ref": storage.get("access_controls_ref"),
        "tamper_evidence_method": method if has_method else None,
        "tamper_evidence_present": has_method,
        "citations": [
            "EU AI Act, Article 26, Paragraph 6",
            "ISO/IEC 42001:2023, Annex A, Control A.6.2.8",
        ],
    }
    if not has_method:
        warnings.append(
            "log_storage.tamper_evidence_method is absent or empty. EU AI Act, Article 26, "
            "Paragraph 6 deployer duty to keep logs implies tamper-evident storage; specify "
            "hash-chain, hmac, cryptographic-signing, append-only-store, or external-notary."
        )
    return assessment, warnings


def _build_schema_diff(
    previous_schema_ref: str | None,
    current_event_schema: dict[str, Any],
) -> dict[str, Any] | None:
    """Build the diff block when previous_schema_ref is supplied.

    The previous schema content is referenced, not loaded. Downstream
    tooling resolves the reference; the plugin records the link, plus a
    high-level scaffold of current categories. Substantive diff authoring
    is a practitioner responsibility.
    """
    if not previous_schema_ref:
        return None
    return {
        "previous_schema_ref": previous_schema_ref,
        "current_schema_categories": sorted(current_event_schema.keys()),
        "added_categories": [],
        "removed_categories": [],
        "removed_fields": [],
        "changed_types": [],
        "diff_notes": [
            f"Schema references predecessor {previous_schema_ref}. "
            "Substantive category-and-field diff authoring is a practitioner responsibility; "
            "this scaffold records the link and current category inventory."
        ],
        "citations": ["ISO/IEC 42001:2023, Annex A, Control A.6.2.8"],
    }


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_sel", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_cross_framework_citations() -> tuple[list[str], list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    try:
        _load_crosswalk_module()
    except Exception as exc:
        warnings.append(
            f"Crosswalk plugin unavailable ({type(exc).__name__}: {exc}); "
            "cross_framework_citations use hard-coded values."
        )
    refs = [dict(r) for r in CROSS_FRAMEWORK_SEL_REFERENCES]
    flat = [f"{r['target_framework']}: {r['target_ref']} ({r['relationship']})" for r in refs]
    return flat, refs, warnings


# ---------------------------------------------------------------------------
# Canonical entry point
# ---------------------------------------------------------------------------


def define_event_schema(inputs: dict[str, Any]) -> dict[str, Any]:
    """Produce the system-operational event log schema definition artifact.

    See module docstring for design stance and input contract. The plugin
    specs the schema; it does NOT generate actual log entries and does
    NOT verify log files exist on disk.

    Raises:
        ValueError: on missing or malformed required inputs.
    """
    _validate(inputs)

    sd = dict(inputs["system_description"])
    event_schema = inputs["event_schema"]
    retention_policy = inputs["retention_policy"]
    log_storage = inputs.get("log_storage")
    traceability_mappings = inputs.get("traceability_mappings")
    previous_schema_ref = inputs.get("previous_schema_ref")
    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True
    reviewed_by = inputs.get("reviewed_by")

    warnings: list[str] = []

    art_12_applicability = _assess_art_12_applicability(sd)
    event_schema_normalized = _normalize_event_schema(event_schema)

    biometric_check, bio_warnings = _check_biometric_requirements(sd, event_schema)
    warnings.extend(bio_warnings)

    traceability_coverage, trace_warnings = _assess_traceability_coverage(
        event_schema, traceability_mappings
    )
    warnings.extend(trace_warnings)

    retention_assessment, retention_warnings = _assess_retention_policy(sd, retention_policy)
    warnings.extend(retention_warnings)

    tamper_assessment, tamper_warnings = _assess_tamper_evidence(log_storage)
    warnings.extend(tamper_warnings)

    schema_diff = _build_schema_diff(previous_schema_ref, event_schema)

    citations: list[str] = [
        "EU AI Act, Article 12, Paragraph 1",
        "EU AI Act, Article 12, Paragraph 2",
        "EU AI Act, Article 19, Paragraph 1",
        "EU AI Act, Article 26, Paragraph 6",
        "EU AI Act, Article 79, Paragraph 1",
        "ISO/IEC 42001:2023, Annex A, Control A.6.2.8",
        "NIST AI RMF, MEASURE 2.8",
    ]
    if sd.get("remote_biometric_id"):
        citations.append("EU AI Act, Article 12, Paragraph 3")
    if retention_policy.get("policy_name") == "sectoral-finance":
        citations.append("EU AI Act, Article 19, Paragraph 2")

    cross_framework_citations: list[str] = []
    cross_framework_refs: list[dict[str, Any]] = []
    if enrich:
        cross_framework_citations, cross_framework_refs, enrich_warnings = (
            _build_cross_framework_citations()
        )
        warnings.extend(enrich_warnings)

    summary = {
        "system_id": sd.get("system_id"),
        "art_12_applicability": art_12_applicability["status"],
        "event_category_count": len(event_schema),
        "event_field_count": len(event_schema_normalized),
        "retention_policy": retention_policy.get("policy_name"),
        "retention_minimum_days": retention_policy.get("minimum_days"),
        "eu_art_19_floor_satisfied": retention_assessment["eu_art_19_floor_satisfied"],
        "biometric_applicable": biometric_check is not None,
        "biometric_satisfied": biometric_check["satisfied"] if biometric_check else None,
        "traceability_purposes_covered": sum(
            1 for entry in traceability_coverage["per_purpose"] if entry["covered"]
        ),
        "tamper_evidence_present": tamper_assessment["tamper_evidence_present"],
        "warning_count": len(warnings),
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "eu-ai-act,iso42001,nist",
        "system_description_echo": sd,
        "art_12_applicability": art_12_applicability,
        "event_schema_normalized": event_schema_normalized,
        "traceability_coverage": traceability_coverage,
        "retention_policy_assessment": retention_assessment,
        "tamper_evidence_assessment": tamper_assessment,
        "citations": citations,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": reviewed_by,
    }
    if biometric_check is not None:
        output["biometric_art_12_3_check"] = biometric_check
    if schema_diff is not None:
        output["schema_diff_summary"] = schema_diff
    if enrich:
        output["cross_framework_citations"] = cross_framework_citations
        output["cross_framework_references"] = cross_framework_refs
    return output


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_markdown(schema: dict[str, Any]) -> str:
    """Render a system-event-log schema definition as Markdown audit evidence."""
    required = (
        "timestamp",
        "agent_signature",
        "system_description_echo",
        "art_12_applicability",
        "event_schema_normalized",
        "traceability_coverage",
        "retention_policy_assessment",
        "tamper_evidence_assessment",
        "citations",
        "summary",
    )
    missing = [k for k in required if k not in schema]
    if missing:
        raise ValueError(f"schema missing required fields: {missing}")

    sd = schema["system_description_echo"]
    applicability = schema["art_12_applicability"]
    retention = schema["retention_policy_assessment"]
    tamper = schema["tamper_evidence_assessment"]
    traceability = schema["traceability_coverage"]

    lines: list[str] = [
        "# System-operational event log schema",
        "",
        f"**Generated at (UTC):** {schema['timestamp']}",
        f"**Generated by:** {schema['agent_signature']}",
        f"**Framework:** {schema.get('framework', 'eu-ai-act,iso42001,nist')}",
        f"**System ID:** {sd.get('system_id', 'not set')}",
    ]
    if schema.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {schema['reviewed_by']}")

    lines.extend([
        "",
        "## Applicability",
        "",
        f"- Status: {applicability.get('status')}",
        f"- Risk tier: {applicability.get('risk_tier')}",
        f"- Jurisdiction: {applicability.get('jurisdiction')}",
        f"- Rationale: {applicability.get('rationale')}",
        "",
        "## Event schema",
        "",
    ])
    if not schema["event_schema_normalized"]:
        lines.append("_No event categories declared._")
    else:
        lines.append("| Category | Field | Type | Required | Description |")
        lines.append("|---|---|---|---|---|")
        for row in schema["event_schema_normalized"]:
            desc = (row.get("description") or "").replace("|", "\\|")
            req = "yes" if row.get("required") else "no"
            lines.append(
                f"| {row['category']} | {row['field_name']} | {row.get('type', '')} | {req} | {desc} |"
            )

    if "biometric_art_12_3_check" in schema:
        bio = schema["biometric_art_12_3_check"]
        lines.extend(["", "## Biometric Article 12(3) check", ""])
        lines.append(f"- Satisfied: {'yes' if bio.get('satisfied') else 'no'}")
        lines.append(f"- Required fields: {', '.join(bio.get('required_fields') or [])}")
        lines.append(f"- Present fields: {', '.join(bio.get('present_fields') or []) or 'none'}")
        lines.append(f"- Missing fields: {', '.join(bio.get('missing_fields') or []) or 'none'}")
        lines.append(f"- Citation: {', '.join(bio.get('citations') or [])}")

    lines.extend(["", "## Traceability", ""])
    lines.append("| Article 12(2) point | Purpose | Covered categories | Covered |")
    lines.append("|---|---|---|---|")
    for entry in traceability.get("per_purpose", []):
        covered = ", ".join(entry.get("covered_categories") or []) or "none"
        covered_text = "yes" if entry.get("covered") else "no"
        lines.append(
            f"| ({entry['purpose']}) | {entry['purpose_text']} | {covered} | {covered_text} |"
        )

    lines.extend(["", "## Retention policy", ""])
    lines.append(f"- Policy name: {retention.get('policy_name')}")
    lines.append(f"- Minimum days: {retention.get('minimum_days')}")
    lines.append(f"- Maximum days: {retention.get('maximum_days')}")
    lines.append(f"- EU Article 19(1) floor satisfied: {'yes' if retention.get('eu_art_19_floor_satisfied') else 'no'}")
    lines.append(f"- Deletion procedure ref: {retention.get('deletion_procedure_ref') or 'not set'}")
    lines.append(f"- Legal basis citation: {retention.get('legal_basis_citation') or 'not set'}")

    lines.extend(["", "## Tamper evidence", ""])
    lines.append(f"- Storage system: {tamper.get('storage_system') or 'not set'}")
    lines.append(f"- Encryption at rest: {tamper.get('encryption_at_rest')}")
    lines.append(f"- Access controls ref: {tamper.get('access_controls_ref') or 'not set'}")
    lines.append(f"- Tamper-evidence method: {tamper.get('tamper_evidence_method') or 'not set'}")
    lines.append(f"- Present: {'yes' if tamper.get('tamper_evidence_present') else 'no'}")

    if "schema_diff_summary" in schema:
        diff = schema["schema_diff_summary"]
        lines.extend(["", "## Schema diff", ""])
        lines.append(f"- Previous schema ref: {diff.get('previous_schema_ref')}")
        lines.append(f"- Current categories: {', '.join(diff.get('current_schema_categories') or [])}")
        if diff.get("diff_notes"):
            lines.append("")
            lines.append("**Notes:**")
            lines.append("")
            for n in diff["diff_notes"]:
                lines.append(f"- {n}")

    lines.extend(["", "## Applicable citations", ""])
    for c in schema["citations"]:
        lines.append(f"- {c}")

    if schema.get("cross_framework_citations"):
        lines.extend(["", "## Cross-framework citations", ""])
        for c in schema["cross_framework_citations"]:
            lines.append(f"- {c}")

    lines.extend(["", "## Warnings", ""])
    if schema.get("warnings"):
        for w in schema["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("_No warnings._")

    lines.append("")
    return "\n".join(lines)


def render_csv(schema: dict[str, Any]) -> str:
    """Render the normalized event-schema rows as CSV (one row per field)."""
    if "event_schema_normalized" not in schema:
        raise ValueError("schema missing required field 'event_schema_normalized'")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["category", "field_name", "type", "required", "description"])
    for row in schema["event_schema_normalized"]:
        writer.writerow([
            row.get("category", ""),
            row.get("field_name", ""),
            row.get("type", ""),
            "yes" if row.get("required") else "no",
            row.get("description", ""),
        ])
    return buf.getvalue()


__all__ = [
    "AGENT_SIGNATURE",
    "REQUIRED_INPUT_FIELDS",
    "EU_ART_19_MIN_RETENTION_MONTHS",
    "EU_ART_19_MIN_RETENTION_DAYS",
    "VALID_EVENT_CATEGORIES",
    "VALID_RETENTION_POLICIES",
    "BIOMETRIC_REQUIRED_FIELDS",
    "define_event_schema",
    "render_markdown",
    "render_csv",
]
