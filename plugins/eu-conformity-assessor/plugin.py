"""
AIGovOps: EU AI Act Conformity Assessor Plugin.

Operationalizes EU AI Act Article 43 (conformity assessment procedures),
Annex VI (internal control), Annex VII (notified body assessment),
Article 47 (EU declaration of conformity), Article 48 (CE marking), and
Article 49 (EU database registration). The plugin is the procedure and
declaration layer on top of the evidence-bundle-packager output.

Design stance: the plugin does NOT issue conformity certificates, sign
declarations of conformity, or affix CE markings. It structures the
procedure for the provider, verifies that the evidence bundle supplies
the Annex IV technical documentation content set, emits a TEMPLATE
declaration of conformity that the provider must complete and sign, and
flags every gap as a warning. Every determination cites a specific
Article or Annex paragraph.

Public API:
    assess_conformity_procedure(inputs)  canonical entry point
    render_markdown(assessment)          human-readable report
    render_csv(assessment)                one row per Annex IV category
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "eu-conformity-assessor/0.1.0"

REQUIRED_INPUT_FIELDS = ("system_description", "provider_identity", "procedure_requested")

VALID_PROCEDURES = (
    "annex-vi-internal-control",
    "annex-vii-notified-body",
    "annex-i-harmonised-legislation",
    "none-exempt",
)

VALID_ANNEX_III_POINTS = (
    "1-biometrics",
    "2-critical-infrastructure",
    "3-education",
    "4-employment",
    "5-essential-services",
    "6-law-enforcement",
    "7-migration",
    "8-justice",
)

VALID_CE_MARKING_LOCATIONS = ("system", "packaging", "documentation")

# Annex IV technical documentation categories. Every high-risk provider must
# produce evidence under each category before conformity assessment.
ANNEX_IV_REQUIRED_DOCS = (
    "general-description",
    "design-documentation",
    "development-process",
    "monitoring-control",
    "detailed-testing",
    "risk-management",
    "change-log",
    "instructions-for-use",
    "references-to-harmonised-standards",
)

# Mapping of each Annex IV category to the AIGovOps plugin(s) that produce
# the supporting artifact and to the manifest artifact_type(s) that count
# as evidence of completeness.
DOC_CATEGORY_REQUIRED_ARTIFACTS: dict[str, dict[str, Any]] = {
    "general-description": {
        "artifact_types": ("ai-system-inventory",),
        "producing_plugin": "ai-system-inventory-maintainer",
        "citation": "EU AI Act, Annex IV, Point 1",
    },
    "design-documentation": {
        "artifact_types": ("ai-system-inventory", "high-risk-classification"),
        "producing_plugin": "ai-system-inventory-maintainer",
        "citation": "EU AI Act, Annex IV, Point 2",
    },
    "development-process": {
        "artifact_types": ("audit-log-entry",),
        "producing_plugin": "audit-log-generator",
        "citation": "EU AI Act, Annex IV, Point 2",
    },
    "monitoring-control": {
        "artifact_types": ("metrics-report",),
        "producing_plugin": "post-market-monitoring",
        "citation": "EU AI Act, Annex IV, Point 3",
    },
    "detailed-testing": {
        "artifact_types": ("metrics-report",),
        "producing_plugin": "robustness-evaluator",
        "citation": "EU AI Act, Annex IV, Point 6",
    },
    "risk-management": {
        "artifact_types": ("risk-register", "aisia"),
        "producing_plugin": "risk-register-builder",
        "citation": "EU AI Act, Annex IV, Point 5",
    },
    "change-log": {
        "artifact_types": ("audit-log-entry",),
        "producing_plugin": "audit-log-generator",
        "citation": "EU AI Act, Annex IV, Point 2",
    },
    "instructions-for-use": {
        "artifact_types": ("ai-system-inventory",),
        "producing_plugin": "ai-system-inventory-maintainer",
        "citation": "EU AI Act, Annex IV, Point 4",
    },
    "references-to-harmonised-standards": {
        "artifact_types": ("soa",),
        "producing_plugin": "soa-generator",
        "citation": "EU AI Act, Annex IV, Point 7",
    },
}

# QMS attestation: Article 17 requires management review and internal audit
# evidence. These artifact types must appear in the bundle.
_QMS_REQUIRED_ARTIFACT_TYPES = ("management-review-package", "internal-audit-plan")

# EU member state country codes, for authorised-representative non-EU check.
_EU_MEMBER_STATES = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE",
})


# Sibling crosswalk module lookup, identical to soa-generator pattern.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_inputs(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    system_description = inputs["system_description"]
    if not isinstance(system_description, dict):
        raise ValueError("system_description must be a dict")

    provider_identity = inputs["provider_identity"]
    if not isinstance(provider_identity, dict):
        raise ValueError("provider_identity must be a dict")

    procedure = inputs["procedure_requested"]
    if procedure not in VALID_PROCEDURES:
        raise ValueError(
            f"procedure_requested must be one of {VALID_PROCEDURES}; got {procedure!r}"
        )

    annex_iii_category = system_description.get("annex_iii_category")
    if annex_iii_category is not None and annex_iii_category not in VALID_ANNEX_III_POINTS:
        raise ValueError(
            f"system_description.annex_iii_category must be one of {VALID_ANNEX_III_POINTS}; "
            f"got {annex_iii_category!r}"
        )

    ce_location = inputs.get("ce_marking_location")
    if ce_location is not None and ce_location not in VALID_CE_MARKING_LOCATIONS:
        raise ValueError(
            f"ce_marking_location must be one of {VALID_CE_MARKING_LOCATIONS}; "
            f"got {ce_location!r}"
        )

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")


# ---------------------------------------------------------------------------
# Bundle introspection
# ---------------------------------------------------------------------------


def _load_bundle_manifest(bundle_ref: str | None) -> tuple[dict[str, Any] | None, list[str]]:
    """Read MANIFEST.json from an evidence bundle directory. Returns (manifest, warnings)."""
    warnings: list[str] = []
    if not bundle_ref:
        return None, warnings
    bundle_dir = Path(bundle_ref)
    if not bundle_dir.is_dir():
        warnings.append(
            f"evidence_bundle_ref {bundle_ref!r} is not a readable directory. "
            "Annex IV completeness cannot be verified."
        )
        return None, warnings
    manifest_path = bundle_dir / "MANIFEST.json"
    if not manifest_path.is_file():
        warnings.append(
            f"evidence_bundle_ref {bundle_ref!r} is missing MANIFEST.json. "
            "Annex IV completeness cannot be verified."
        )
        return None, warnings
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        warnings.append(f"MANIFEST.json could not be parsed: {exc}")
        return None, warnings
    if not isinstance(data, dict):
        warnings.append("MANIFEST.json did not contain a JSON object at the top level.")
        return None, warnings
    return data, warnings


def _artifact_types_present(manifest: dict[str, Any] | None) -> set[str]:
    if manifest is None:
        return set()
    present: set[str] = set()
    for entry in manifest.get("artifacts", []):
        atype = entry.get("artifact_type")
        if atype:
            present.add(atype)
    return present


# ---------------------------------------------------------------------------
# Procedure applicability
# ---------------------------------------------------------------------------


_BIOMETRIC_HARMONISED_STANDARDS = (
    "iso/iec 19795",
    "iso/iec 30107",
    "en 17529",
)


def _has_biometric_harmonised_standard(standards: list[Any]) -> bool:
    if not standards:
        return False
    lower = [str(s).lower() for s in standards]
    return any(
        any(marker in entry for marker in _BIOMETRIC_HARMONISED_STANDARDS)
        for entry in lower
    )


def _assess_procedure_applicability(
    system_description: dict[str, Any],
    procedure_requested: str,
    harmonised_standards: list[Any],
) -> tuple[dict[str, Any], list[str]]:
    """Return (applicability_record, warnings)."""
    warnings: list[str] = []
    annex_iii_category = system_description.get("annex_iii_category")
    annex_i_legislation = system_description.get("annex_i_legislation") or []

    required_procedure: str | None = None
    rationale_citations: list[str] = []

    if annex_i_legislation:
        required_procedure = "annex-i-harmonised-legislation"
        rationale_citations.append("EU AI Act, Article 43, Paragraph 3")
        if procedure_requested != "annex-i-harmonised-legislation":
            warnings.append(
                "Annex I harmonised legislation applies; procedure_requested must be "
                "annex-i-harmonised-legislation per EU AI Act, Article 43, Paragraph 3."
            )
    elif annex_iii_category == "1-biometrics":
        if _has_biometric_harmonised_standard(harmonised_standards):
            required_procedure = "annex-vi-internal-control"
            rationale_citations.append("EU AI Act, Article 43, Paragraph 1")
            if procedure_requested == "annex-vii-notified-body":
                warnings.append(
                    "Biometric system with harmonised standards applied permits "
                    "annex-vi-internal-control per EU AI Act, Article 43, Paragraph 1. "
                    "annex-vii-notified-body is optional, not required."
                )
        else:
            required_procedure = "annex-vii-notified-body"
            rationale_citations.append("EU AI Act, Article 43, Paragraph 1")
            if procedure_requested != "annex-vii-notified-body":
                warnings.append(
                    "Biometric system without harmonised standards requires "
                    "annex-vii-notified-body per EU AI Act, Article 43, Paragraph 1. "
                    f"procedure_requested={procedure_requested!r} is blocking."
                )
    elif annex_iii_category in {
        "2-critical-infrastructure",
        "3-education",
        "4-employment",
        "5-essential-services",
        "6-law-enforcement",
        "7-migration",
        "8-justice",
    }:
        required_procedure = "annex-vi-internal-control"
        rationale_citations.append("EU AI Act, Article 43, Paragraph 2")
        if procedure_requested == "annex-vii-notified-body":
            warnings.append(
                f"Annex III category {annex_iii_category!r} defaults to "
                "annex-vi-internal-control per EU AI Act, Article 43, Paragraph 2. "
                "annex-vii-notified-body requires voluntary justification."
            )

    if not rationale_citations:
        rationale_citations.append("EU AI Act, Article 43")

    return (
        {
            "procedure_requested": procedure_requested,
            "required_procedure": required_procedure,
            "aligned": required_procedure == procedure_requested or required_procedure is None,
            "annex_iii_category": annex_iii_category,
            "annex_i_legislation": annex_i_legislation,
            "citations": rationale_citations,
        },
        warnings,
    )


# ---------------------------------------------------------------------------
# Annex IV completeness
# ---------------------------------------------------------------------------


def _assess_annex_iv_completeness(
    present_artifact_types: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (per-category rows, warnings)."""
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for category in ANNEX_IV_REQUIRED_DOCS:
        spec = DOC_CATEGORY_REQUIRED_ARTIFACTS[category]
        accepted = spec["artifact_types"]
        present = any(atype in present_artifact_types for atype in accepted)
        row = {
            "category": category,
            "status": "present" if present else "missing",
            "accepted_artifact_types": list(accepted),
            "recommended_producing_plugin": spec["producing_plugin"],
            "citation": spec["citation"],
        }
        rows.append(row)
        if not present:
            warnings.append(
                f"Annex IV category {category!r} has no supporting artifact in the "
                f"evidence bundle. Run {spec['producing_plugin']!r} to produce it. "
                f"Citation: {spec['citation']}."
            )
    return rows, warnings


# ---------------------------------------------------------------------------
# QMS attestation (Art. 17)
# ---------------------------------------------------------------------------


def _assess_qms_attestation(
    present_artifact_types: set[str],
    manifest_loaded: bool,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if not manifest_loaded:
        return (
            {
                "status": "not-evaluated",
                "required_artifact_types": list(_QMS_REQUIRED_ARTIFACT_TYPES),
                "missing_artifact_types": list(_QMS_REQUIRED_ARTIFACT_TYPES),
                "citations": [
                    "EU AI Act, Article 17, Paragraph 1, Point (a)",
                    "EU AI Act, Article 17, Paragraph 1, Point (i)",
                ],
            },
            warnings,
        )
    missing = [
        atype for atype in _QMS_REQUIRED_ARTIFACT_TYPES
        if atype not in present_artifact_types
    ]
    status = "satisfied" if not missing else "gaps-present"
    if missing:
        warnings.append(
            "Art. 17 QMS obligations require management-review and internal-audit "
            f"artifacts in the bundle. Missing: {missing}. "
            "Citation: EU AI Act, Article 17, Paragraph 1, Point (a) and Point (i)."
        )
    return (
        {
            "status": status,
            "required_artifact_types": list(_QMS_REQUIRED_ARTIFACT_TYPES),
            "missing_artifact_types": missing,
            "citations": [
                "EU AI Act, Article 17, Paragraph 1, Point (a)",
                "EU AI Act, Article 17, Paragraph 1, Point (i)",
            ],
        },
        warnings,
    )


# ---------------------------------------------------------------------------
# Notified body (Annex VII)
# ---------------------------------------------------------------------------


def _assess_notified_body(
    procedure_requested: str,
    notified_body: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    if procedure_requested != "annex-vii-notified-body":
        return None, warnings
    if not notified_body:
        warnings.append(
            "procedure_requested=annex-vii-notified-body but notified_body input is "
            "empty. Citation: EU AI Act, Annex VII."
        )
        return (
            {
                "status": "missing",
                "body_id": None,
                "name": None,
                "certificate_ref": None,
                "citations": ["EU AI Act, Annex VII"],
            },
            warnings,
        )
    body_id = notified_body.get("body_id")
    name = notified_body.get("name")
    certificate_ref = notified_body.get("certificate_ref")
    if not body_id:
        warnings.append(
            "Notified body identification number required for CE marking per "
            "EU AI Act, Article 48, Paragraph 3."
        )
    if not certificate_ref:
        warnings.append(
            "Notified body certificate_ref missing. EU type-examination certificate "
            "must be referenced in the declaration of conformity per "
            "EU AI Act, Article 47, Paragraph 1."
        )
    status = "complete" if (body_id and certificate_ref) else "incomplete"
    return (
        {
            "status": status,
            "body_id": body_id,
            "name": name,
            "certificate_ref": certificate_ref,
            "citations": ["EU AI Act, Annex VII", "EU AI Act, Article 48, Paragraph 3"],
        },
        warnings,
    )


# ---------------------------------------------------------------------------
# EU declaration of conformity (Art. 47)
# ---------------------------------------------------------------------------


def _build_declaration_of_conformity_draft(
    system_description: dict[str, Any],
    provider_identity: dict[str, Any],
    procedure_requested: str,
    harmonised_standards: list[Any],
    notified_body: dict[str, Any] | None,
    reviewed_by: str | None,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    provider_name = provider_identity.get("legal_name")
    provider_address = provider_identity.get("address")
    system_id = system_description.get("system_id")
    intended_use = system_description.get("intended_use")
    signatory = reviewed_by or provider_identity.get("signatory")

    if not provider_name:
        warnings.append(
            "Declaration of conformity missing provider legal_name. "
            "Citation: EU AI Act, Article 47, Paragraph 1."
        )
    if not provider_address:
        warnings.append(
            "Declaration of conformity missing provider address. "
            "Citation: EU AI Act, Article 47, Paragraph 1."
        )
    if not system_id:
        warnings.append(
            "Declaration of conformity missing system_id. "
            "Citation: EU AI Act, Article 47, Paragraph 1."
        )
    if not intended_use:
        warnings.append(
            "Declaration of conformity missing intended_use. "
            "Citation: EU AI Act, Article 47, Paragraph 1."
        )
    if not signatory:
        warnings.append(
            "Declaration of conformity missing signatory. The provider must sign "
            "the declaration. Citation: EU AI Act, Article 47, Paragraph 2."
        )

    certificate_ref = None
    if procedure_requested == "annex-vii-notified-body" and notified_body:
        certificate_ref = notified_body.get("certificate_ref")

    draft = {
        "template_status": "DRAFT_REQUIRES_PROVIDER_SIGNATURE",
        "provider_legal_name": provider_name,
        "provider_address": provider_address,
        "system_id": system_id,
        "intended_use": intended_use,
        "procedure_applied": procedure_requested,
        "harmonised_standards_applied": list(harmonised_standards or []),
        "notified_body_certificate_ref": certificate_ref,
        "statement_of_conformity": (
            "The provider declares under sole responsibility that the AI system "
            "identified above conforms with Regulation (EU) 2024/1689 and with "
            "applicable Union harmonisation legislation."
        ),
        "date_of_issue": _utc_now_iso(),
        "signatory": signatory,
        "citations": [
            "EU AI Act, Article 47, Paragraph 1",
            "EU AI Act, Article 47, Paragraph 2",
        ],
    }
    return draft, warnings


# ---------------------------------------------------------------------------
# CE marking (Art. 48)
# ---------------------------------------------------------------------------


def _assess_ce_marking(
    system_description: dict[str, Any],
    procedure_requested: str,
    ce_marking_location: str | None,
    notified_body: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    ce_required = bool(system_description.get("ce_marking_required", True))
    risk_tier = str(system_description.get("risk_tier", "")).lower()
    if risk_tier in ("prohibited", "minimal-risk", "minimal"):
        ce_required = False

    citations = [
        "EU AI Act, Article 48, Paragraph 1",
        "EU AI Act, Article 48, Paragraph 2",
    ]
    if procedure_requested == "annex-vii-notified-body":
        citations.append("EU AI Act, Article 48, Paragraph 3")

    if ce_required and not ce_marking_location:
        warnings.append(
            "CE marking location not specified for a high-risk system intended for "
            "the EU market. Citation: EU AI Act, Article 48, Paragraph 1."
        )

    notified_body_id_required = procedure_requested == "annex-vii-notified-body"
    notified_body_id_present = bool(notified_body and notified_body.get("body_id"))
    if notified_body_id_required and not notified_body_id_present:
        warnings.append(
            "Notified body identification number must follow the CE marking when "
            "annex-vii-notified-body procedure applies. Citation: "
            "EU AI Act, Article 48, Paragraph 3."
        )

    return (
        {
            "ce_marking_required": ce_required,
            "location": ce_marking_location,
            "notified_body_id_required": notified_body_id_required,
            "notified_body_id_present": notified_body_id_present,
            "citations": citations,
        },
        warnings,
    )


# ---------------------------------------------------------------------------
# EU database registration (Art. 49)
# ---------------------------------------------------------------------------


def _assess_registration(
    system_description: dict[str, Any],
    registration_status: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    annex_iii_category = system_description.get("annex_iii_category")
    risk_tier = str(system_description.get("risk_tier", "")).lower()

    # Exemption: Annex III point 2 (critical infrastructure).
    if annex_iii_category == "2-critical-infrastructure":
        return (
            {
                "status": "not-required",
                "rationale": (
                    "Annex III point 2 (critical infrastructure) is exempt from "
                    "Article 49 registration."
                ),
                "entry_id": None,
                "registration_date": None,
                "public_or_restricted": None,
                "citations": [
                    "EU AI Act, Article 49, Paragraph 1",
                    "EU AI Act, Article 49, Paragraph 2",
                ],
            },
            warnings,
        )

    registration_required = risk_tier in ("high-risk", "high") or bool(annex_iii_category)
    if not registration_required:
        return (
            {
                "status": "not-required",
                "rationale": "System is not high-risk; Article 49 registration does not apply.",
                "entry_id": None,
                "registration_date": None,
                "public_or_restricted": None,
                "citations": ["EU AI Act, Article 49, Paragraph 1"],
            },
            warnings,
        )

    entry_id = None
    registration_date = None
    public_or_restricted = "public"
    if annex_iii_category == "6-law-enforcement":
        public_or_restricted = "restricted"

    if not registration_status:
        warnings.append(
            "Art. 49 registration required before placing on market. No "
            "registration_status supplied. Citation: EU AI Act, Article 49, Paragraph 1."
        )
        return (
            {
                "status": "missing",
                "rationale": "High-risk system requires EU database registration before market placement.",
                "entry_id": None,
                "registration_date": None,
                "public_or_restricted": public_or_restricted,
                "citations": [
                    "EU AI Act, Article 49, Paragraph 1",
                    "EU AI Act, Article 49, Paragraph 2",
                ],
            },
            warnings,
        )

    entry_id = registration_status.get("eu_database_entry_id")
    registration_date = registration_status.get("registration_date")
    supplied_visibility = registration_status.get("public_or_restricted")
    if supplied_visibility:
        public_or_restricted = supplied_visibility

    if not entry_id:
        warnings.append(
            "registration_status.eu_database_entry_id missing. Citation: "
            "EU AI Act, Article 49, Paragraph 1."
        )
    if not registration_date:
        warnings.append(
            "registration_status.registration_date missing. Citation: "
            "EU AI Act, Article 49, Paragraph 1."
        )

    status = "registered" if entry_id and registration_date else "incomplete"
    return (
        {
            "status": status,
            "rationale": "High-risk system registration status captured from inputs.",
            "entry_id": entry_id,
            "registration_date": registration_date,
            "public_or_restricted": public_or_restricted,
            "citations": [
                "EU AI Act, Article 49, Paragraph 1",
                "EU AI Act, Article 49, Paragraph 2",
            ],
        },
        warnings,
    )


# ---------------------------------------------------------------------------
# Authorised representative (Art. 22) check
# ---------------------------------------------------------------------------


def _assess_authorised_representative(provider_identity: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    country = str(provider_identity.get("country") or "").upper()
    if not country:
        warnings.append(
            "provider_identity.country not supplied; authorised representative "
            "requirement cannot be evaluated. Citation: EU AI Act, Article 22."
        )
        return warnings
    if country in _EU_MEMBER_STATES:
        return warnings
    rep = provider_identity.get("authorised_representative")
    if not rep or not isinstance(rep, dict) or not rep.get("legal_name"):
        warnings.append(
            f"Non-EU provider (country={country!r}) must appoint an authorised "
            "representative established in the Union. Citation: "
            "EU AI Act, Article 22, Paragraph 1."
        )
    return warnings


# ---------------------------------------------------------------------------
# Surveillance comparison
# ---------------------------------------------------------------------------


def _assess_surveillance(previous_assessment_ref: str | None) -> dict[str, Any] | None:
    if not previous_assessment_ref:
        return None
    return {
        "status": "surveillance-mode",
        "previous_assessment_ref": previous_assessment_ref,
        "note": (
            "Re-assessment compared against prior determination. Provider must "
            "confirm that substantial modifications since the prior assessment "
            "have been re-evaluated per EU AI Act, Article 43, Paragraph 4."
        ),
        "citations": ["EU AI Act, Article 43, Paragraph 4"],
    }


# ---------------------------------------------------------------------------
# Crosswalk enrichment
# ---------------------------------------------------------------------------


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.is_file():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_eu_conformity_crosswalk_plugin", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _collect_cross_framework_citations() -> tuple[list[dict[str, Any]], list[str]]:
    """Return (citation rows, warnings). Rows carry EU Article/Annex -> ISO mappings."""
    warnings: list[str] = []
    try:
        crosswalk = _load_crosswalk_module()
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        warnings.append(f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}")
        return [], warnings

    targets = {
        "Annex IV",
        "Annex VI",
        "Annex VII",
        "Article 43",
        "Article 47",
        "Article 48",
        "Article 49",
        "Article 17",
    }
    rows: list[dict[str, Any]] = []
    for m in data.get("mappings", []):
        if m.get("source_framework") != "eu-ai-act":
            continue
        source_ref = m.get("source_ref") or ""
        if not any(token in source_ref for token in targets):
            continue
        rows.append({
            "eu_ai_act_ref": source_ref,
            "eu_ai_act_title": m.get("source_title"),
            "target_framework": m.get("target_framework"),
            "target_ref": m.get("target_ref"),
            "relationship": m.get("relationship"),
            "confidence": m.get("confidence"),
        })
    return rows, warnings


# ---------------------------------------------------------------------------
# Canonical entry point
# ---------------------------------------------------------------------------


def assess_conformity_procedure(inputs: dict[str, Any]) -> dict[str, Any]:
    """Assess the EU AI Act conformity assessment procedure for a high-risk system.

    Args:
        inputs: Dict with system_description, provider_identity, and
            procedure_requested (required). Optional evidence_bundle_ref,
            notified_body, harmonised_standards_applied, ce_marking_location,
            registration_status, previous_assessment_ref,
            enrich_with_crosswalk (default True), reviewed_by.

    Returns:
        Dict with timestamp, agent_signature, framework, system_description_echo,
        procedure_selected, procedure_applicability, annex_iv_completeness,
        qms_attestation, notified_body_check (when applicable),
        declaration_of_conformity_draft, ce_marking_check, registration_check,
        surveillance_check (when applicable), citations, warnings, summary,
        cross_framework_citations (when enriched), reviewed_by.

    Raises:
        ValueError: on structural input problems.
    """
    _validate_inputs(inputs)

    system_description = inputs["system_description"]
    provider_identity = inputs["provider_identity"]
    procedure_requested = inputs["procedure_requested"]
    evidence_bundle_ref = inputs.get("evidence_bundle_ref")
    notified_body = inputs.get("notified_body")
    harmonised_standards = list(inputs.get("harmonised_standards_applied") or [])
    ce_marking_location = inputs.get("ce_marking_location")
    registration_status = inputs.get("registration_status")
    previous_assessment_ref = inputs.get("previous_assessment_ref")
    reviewed_by = inputs.get("reviewed_by")
    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True

    all_warnings: list[str] = []

    # Authorised representative (Art. 22).
    all_warnings.extend(_assess_authorised_representative(provider_identity))

    # Bundle introspection for Annex IV and QMS.
    manifest, manifest_warnings = _load_bundle_manifest(evidence_bundle_ref)
    all_warnings.extend(manifest_warnings)
    present_artifact_types = _artifact_types_present(manifest)
    manifest_loaded = manifest is not None

    # Procedure applicability (Art. 43).
    procedure_applicability, proc_warnings = _assess_procedure_applicability(
        system_description, procedure_requested, harmonised_standards
    )
    all_warnings.extend(proc_warnings)

    # Annex IV completeness.
    annex_iv_rows, annex_iv_warnings = _assess_annex_iv_completeness(
        present_artifact_types if manifest_loaded else set()
    )
    if manifest_loaded:
        all_warnings.extend(annex_iv_warnings)
    else:
        # Emit a single umbrella warning instead of nine when bundle absent.
        all_warnings.append(
            "Annex IV completeness not evaluated: evidence_bundle_ref missing or "
            "unreadable. Citation: EU AI Act, Annex IV."
        )

    # QMS attestation (Art. 17).
    qms_attestation, qms_warnings = _assess_qms_attestation(
        present_artifact_types, manifest_loaded
    )
    all_warnings.extend(qms_warnings)

    # Notified body (Annex VII).
    notified_body_check, nb_warnings = _assess_notified_body(
        procedure_requested, notified_body
    )
    all_warnings.extend(nb_warnings)

    # Declaration of conformity (Art. 47).
    declaration_draft, doc_warnings = _build_declaration_of_conformity_draft(
        system_description, provider_identity, procedure_requested,
        harmonised_standards, notified_body, reviewed_by,
    )
    all_warnings.extend(doc_warnings)

    # CE marking (Art. 48).
    ce_marking_check, ce_warnings = _assess_ce_marking(
        system_description, procedure_requested, ce_marking_location, notified_body
    )
    all_warnings.extend(ce_warnings)

    # EU database registration (Art. 49).
    registration_check, reg_warnings = _assess_registration(
        system_description, registration_status
    )
    all_warnings.extend(reg_warnings)

    # Surveillance (Art. 43(4)).
    surveillance_check = _assess_surveillance(previous_assessment_ref)

    # Crosswalk enrichment.
    cross_framework_citations: list[dict[str, Any]] | None = None
    if enrich:
        crosswalk_rows, crosswalk_warnings = _collect_cross_framework_citations()
        cross_framework_citations = crosswalk_rows
        all_warnings.extend(crosswalk_warnings)

    citations = [
        "EU AI Act, Article 43, Paragraph 1",
        "EU AI Act, Article 43, Paragraph 2",
        "EU AI Act, Article 43, Paragraph 3",
        "EU AI Act, Article 47, Paragraph 1",
        "EU AI Act, Article 48, Paragraph 1",
        "EU AI Act, Article 49, Paragraph 1",
        "EU AI Act, Annex IV",
        "EU AI Act, Annex VI",
        "EU AI Act, Annex VII",
        "EU AI Act, Article 17, Paragraph 1, Point (a)",
    ]

    summary = {
        "framework": "eu-ai-act",
        "procedure_requested": procedure_requested,
        "procedure_aligned": procedure_applicability["aligned"],
        "annex_iv_categories_total": len(annex_iv_rows),
        "annex_iv_categories_present": sum(1 for r in annex_iv_rows if r["status"] == "present"),
        "annex_iv_categories_missing": sum(1 for r in annex_iv_rows if r["status"] == "missing"),
        "qms_status": qms_attestation["status"],
        "notified_body_status": notified_body_check["status"] if notified_body_check else "not-applicable",
        "ce_marking_required": ce_marking_check["ce_marking_required"],
        "registration_status": registration_check["status"],
        "warning_count": len(all_warnings),
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "eu-ai-act",
        "system_description_echo": dict(system_description),
        "procedure_selected": procedure_requested,
        "procedure_applicability": procedure_applicability,
        "annex_iv_completeness": annex_iv_rows,
        "qms_attestation": qms_attestation,
        "notified_body_check": notified_body_check,
        "declaration_of_conformity_draft": declaration_draft,
        "ce_marking_check": ce_marking_check,
        "registration_check": registration_check,
        "surveillance_check": surveillance_check,
        "citations": citations,
        "warnings": all_warnings,
        "summary": summary,
        "reviewed_by": reviewed_by,
    }
    if cross_framework_citations is not None:
        output["cross_framework_citations"] = cross_framework_citations
    return output


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


_LEGAL_DISCLAIMER = (
    "> This conformity assessment report is informational. It does not "
    "constitute an audit opinion, a notified-body certificate, or legal "
    "advice. Conformity determinations require the provider's own "
    "declaration (Article 47) and, where applicable, a notified body."
)


def render_markdown(assessment: dict[str, Any]) -> str:
    required = (
        "timestamp", "agent_signature", "framework", "procedure_selected",
        "procedure_applicability", "annex_iv_completeness", "qms_attestation",
        "declaration_of_conformity_draft", "ce_marking_check",
        "registration_check", "summary",
    )
    missing = [k for k in required if k not in assessment]
    if missing:
        raise ValueError(f"assessment missing required fields: {missing}")

    lines: list[str] = []
    lines.append("# EU AI Act Conformity Assessment Report")
    lines.append("")
    lines.append(_LEGAL_DISCLAIMER)
    lines.append("")
    lines.append(f"**Framework:** {assessment['framework']}")
    lines.append(f"**Procedure selected:** {assessment['procedure_selected']}")
    lines.append(f"**Generated at (UTC):** {assessment['timestamp']}")
    lines.append(f"**Generated by:** {assessment['agent_signature']}")
    if assessment.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {assessment['reviewed_by']}")

    summary = assessment["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Procedure requested: {summary['procedure_requested']}",
        f"- Procedure aligned with Article 43: {summary['procedure_aligned']}",
        f"- Annex IV categories present: {summary['annex_iv_categories_present']}/"
        f"{summary['annex_iv_categories_total']}",
        f"- QMS attestation status: {summary['qms_status']}",
        f"- Notified body status: {summary['notified_body_status']}",
        f"- CE marking required: {summary['ce_marking_required']}",
        f"- Registration status: {summary['registration_status']}",
        f"- Warnings: {summary['warning_count']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in assessment.get("citations", []):
        lines.append(f"- {c}")

    # Procedure applicability.
    proc = assessment["procedure_applicability"]
    lines.extend([
        "",
        "## Procedure applicability",
        "",
        f"- Procedure requested: {proc['procedure_requested']}",
        f"- Required procedure per Article 43: {proc.get('required_procedure') or 'not-determined'}",
        f"- Aligned: {proc['aligned']}",
        f"- Annex III category: {proc.get('annex_iii_category') or 'not-applicable'}",
        f"- Annex I legislation: {', '.join(proc.get('annex_i_legislation') or []) or 'not-applicable'}",
    ])
    for c in proc.get("citations", []):
        lines.append(f"- Citation: {c}")

    # Annex IV completeness.
    lines.extend([
        "",
        "## Annex IV completeness",
        "",
        "| Category | Status | Accepted artifact types | Recommended plugin | Citation |",
        "|---|---|---|---|---|",
    ])
    for row in assessment["annex_iv_completeness"]:
        accepted = ", ".join(row["accepted_artifact_types"])
        lines.append(
            f"| {row['category']} | {row['status']} | {accepted} | "
            f"{row['recommended_producing_plugin']} | {row['citation']} |"
        )

    # QMS attestation.
    qms = assessment["qms_attestation"]
    lines.extend([
        "",
        "## QMS attestation",
        "",
        f"- Status: {qms['status']}",
        f"- Required artifact types: {', '.join(qms['required_artifact_types'])}",
        f"- Missing artifact types: {', '.join(qms['missing_artifact_types']) or 'none'}",
    ])
    for c in qms.get("citations", []):
        lines.append(f"- Citation: {c}")

    # Notified body.
    nb = assessment.get("notified_body_check")
    if nb:
        lines.extend([
            "",
            "## Notified body check",
            "",
            f"- Status: {nb['status']}",
            f"- Body id: {nb.get('body_id') or 'missing'}",
            f"- Name: {nb.get('name') or 'missing'}",
            f"- Certificate ref: {nb.get('certificate_ref') or 'missing'}",
        ])
        for c in nb.get("citations", []):
            lines.append(f"- Citation: {c}")

    # Declaration of conformity.
    doc = assessment["declaration_of_conformity_draft"]
    lines.extend([
        "",
        "## Declaration of conformity",
        "",
        f"- Template status: {doc['template_status']}",
        f"- Provider legal name: {doc.get('provider_legal_name') or 'missing'}",
        f"- Provider address: {doc.get('provider_address') or 'missing'}",
        f"- System id: {doc.get('system_id') or 'missing'}",
        f"- Intended use: {doc.get('intended_use') or 'missing'}",
        f"- Procedure applied: {doc.get('procedure_applied')}",
        f"- Harmonised standards applied: {', '.join(doc.get('harmonised_standards_applied') or []) or 'none'}",
        f"- Notified body certificate ref: {doc.get('notified_body_certificate_ref') or 'not-applicable'}",
        f"- Statement of conformity: {doc.get('statement_of_conformity')}",
        f"- Date of issue: {doc.get('date_of_issue')}",
        f"- Signatory: {doc.get('signatory') or 'missing'}",
    ])
    for c in doc.get("citations", []):
        lines.append(f"- Citation: {c}")

    # CE marking.
    ce = assessment["ce_marking_check"]
    lines.extend([
        "",
        "## CE marking",
        "",
        f"- CE marking required: {ce['ce_marking_required']}",
        f"- Location: {ce.get('location') or 'not-specified'}",
        f"- Notified body id required: {ce['notified_body_id_required']}",
        f"- Notified body id present: {ce['notified_body_id_present']}",
    ])
    for c in ce.get("citations", []):
        lines.append(f"- Citation: {c}")

    # Registration.
    reg = assessment["registration_check"]
    lines.extend([
        "",
        "## Registration",
        "",
        f"- Status: {reg['status']}",
        f"- Rationale: {reg['rationale']}",
        f"- Entry id: {reg.get('entry_id') or 'not-supplied'}",
        f"- Registration date: {reg.get('registration_date') or 'not-supplied'}",
        f"- Public or restricted: {reg.get('public_or_restricted') or 'not-applicable'}",
    ])
    for c in reg.get("citations", []):
        lines.append(f"- Citation: {c}")

    # Surveillance.
    surv = assessment.get("surveillance_check")
    if surv:
        lines.extend([
            "",
            "## Surveillance",
            "",
            f"- Status: {surv['status']}",
            f"- Previous assessment ref: {surv['previous_assessment_ref']}",
            f"- Note: {surv['note']}",
        ])
        for c in surv.get("citations", []):
            lines.append(f"- Citation: {c}")

    # Cross-framework citations.
    cross = assessment.get("cross_framework_citations")
    if cross:
        lines.extend([
            "",
            "## Cross-framework citations",
            "",
            "| EU AI Act ref | Target framework | Target ref | Relationship | Confidence |",
            "|---|---|---|---|---|",
        ])
        for row in cross:
            lines.append(
                f"| {row.get('eu_ai_act_ref', '')} | {row.get('target_framework', '')} | "
                f"{row.get('target_ref', '')} | {row.get('relationship', '')} | "
                f"{row.get('confidence', '')} |"
            )

    # Warnings.
    warnings = assessment.get("warnings") or []
    lines.extend(["", "## Warnings", ""])
    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("No warnings.")
    lines.append("")

    return "\n".join(lines)


def render_csv(assessment: dict[str, Any]) -> str:
    if "annex_iv_completeness" not in assessment:
        raise ValueError("assessment missing 'annex_iv_completeness' field")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "category", "status", "accepted_artifact_types",
        "recommended_producing_plugin", "citation",
    ])
    for row in assessment["annex_iv_completeness"]:
        writer.writerow([
            row.get("category", ""),
            row.get("status", ""),
            "; ".join(row.get("accepted_artifact_types") or []),
            row.get("recommended_producing_plugin", ""),
            row.get("citation", ""),
        ])
    return buf.getvalue()


__all__ = [
    "AGENT_SIGNATURE",
    "REQUIRED_INPUT_FIELDS",
    "VALID_PROCEDURES",
    "VALID_ANNEX_III_POINTS",
    "ANNEX_IV_REQUIRED_DOCS",
    "DOC_CATEGORY_REQUIRED_ARTIFACTS",
    "assess_conformity_procedure",
    "render_markdown",
    "render_csv",
]
