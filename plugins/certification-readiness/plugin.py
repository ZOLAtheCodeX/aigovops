"""
AIGovOps: Certification Readiness Assessor Plugin.

Consumes an evidence bundle produced by evidence-bundle-packager and a
target certification, and returns a graduated readiness determination with
section-by-section evidence completeness, crosswalk coverage where
applicable, specific gaps or blockers, and curated remediation
recommendations.

This is the first CONSUMER plugin in the AIGovOps catalogue. It reads
artifacts rather than producing them. The plugin does not issue an audit
opinion. Certification decisions remain the responsibility of a qualified
auditor or notified body. The plugin produces the graded readiness
verdict, the supporting evidence, and the remediation list; nothing more.

Public API:
    assess_readiness(inputs)  canonical entry point
    render_markdown(report)   human-readable readiness report
    render_csv(report)        spreadsheet-ingestible gaps + remediations
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "certification-readiness/0.1.0"

REQUIRED_INPUT_FIELDS = ("bundle_path", "target_certification")

VALID_TARGETS = (
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

VALID_READINESS_LEVELS = (
    "ready-with-high-confidence",
    "ready-with-conditions",
    "partially-ready",
    "not-ready",
)

VALID_EVIDENCE_STRENGTH = ("strong", "adequate", "weak", "absent")

VALID_MINIMUM_STRENGTH = VALID_EVIDENCE_STRENGTH

# Strength ordering for comparisons. Higher index is stronger.
_STRENGTH_RANK = {name: idx for idx, name in enumerate(("absent", "weak", "adequate", "strong"))}

# Per-target required artifact sets. Values are lists of artifact types as
# classified by evidence-bundle-packager, paired with a criticality flag.
# Criticality=True means a missing artifact is a blocker; Criticality=False
# means a missing artifact is a gap (partially-ready) but not a hard block.
_TARGET_REQUIRED_ARTIFACTS: dict[str, list[dict[str, Any]]] = {
    "iso42001-stage1": [
        {"artifact_type": "ai-system-inventory", "critical": True},
        {"artifact_type": "role-matrix", "critical": True},
        {"artifact_type": "risk-register", "critical": True},
        {"artifact_type": "soa", "critical": True},
        {"artifact_type": "audit-log-entry", "critical": True},
        {"artifact_type": "aisia", "critical": True},
        {"artifact_type": "management-review-package", "critical": True},
        {"artifact_type": "gap-assessment", "critical": True},
        {"artifact_type": "internal-audit-plan", "critical": True},
    ],
    "iso42001-stage2": [
        {"artifact_type": "ai-system-inventory", "critical": True},
        {"artifact_type": "role-matrix", "critical": True},
        {"artifact_type": "risk-register", "critical": True},
        {"artifact_type": "soa", "critical": True},
        {"artifact_type": "audit-log-entry", "critical": True},
        {"artifact_type": "aisia", "critical": True},
        {"artifact_type": "management-review-package", "critical": True},
        {"artifact_type": "gap-assessment", "critical": True},
        {"artifact_type": "internal-audit-plan", "critical": True},
        {"artifact_type": "nonconformity-register", "critical": True},
        {"artifact_type": "metrics-report", "critical": True},
    ],
    "iso42001-surveillance": [
        {"artifact_type": "ai-system-inventory", "critical": True},
        {"artifact_type": "role-matrix", "critical": True},
        {"artifact_type": "risk-register", "critical": True},
        {"artifact_type": "soa", "critical": True},
        {"artifact_type": "audit-log-entry", "critical": True},
        {"artifact_type": "aisia", "critical": False},
        {"artifact_type": "management-review-package", "critical": True},
        {"artifact_type": "gap-assessment", "critical": False},
        {"artifact_type": "internal-audit-plan", "critical": True},
        {"artifact_type": "nonconformity-register", "critical": True},
        {"artifact_type": "metrics-report", "critical": True},
    ],
    "eu-ai-act-internal-control": [
        {"artifact_type": "aisia", "critical": True},
        {"artifact_type": "risk-register", "critical": True},
        {"artifact_type": "data-register", "critical": True},
        {"artifact_type": "audit-log-entry", "critical": True},
        {"artifact_type": "soa", "critical": True},
        {"artifact_type": "high-risk-classification", "critical": True},
    ],
    "eu-ai-act-notified-body": [
        {"artifact_type": "aisia", "critical": True},
        {"artifact_type": "risk-register", "critical": True},
        {"artifact_type": "data-register", "critical": True},
        {"artifact_type": "audit-log-entry", "critical": True},
        {"artifact_type": "soa", "critical": True},
        {"artifact_type": "high-risk-classification", "critical": True},
        {"artifact_type": "supplier-vendor-assessment", "critical": True},
        {"artifact_type": "metrics-report", "critical": True},
    ],
    "colorado-sb205-safe-harbor": [
        {"artifact_type": "high-risk-classification", "critical": True},
        {"artifact_type": "colorado-compliance-record", "critical": True},
        {"artifact_type": "aisia", "critical": True},
        {"artifact_type": "soa", "critical": False},
        {"artifact_type": "risk-register", "critical": False},
        {"artifact_type": "audit-log-entry", "critical": False},
    ],
    "nyc-ll144-annual-audit": [
        {"artifact_type": "nyc-ll144-audit-package", "critical": True},
    ],
    "singapore-magf-alignment": [
        {"artifact_type": "magf-assessment", "critical": True},
    ],
    "uk-atrs-publication": [
        {"artifact_type": "atrs-record", "critical": True},
    ],
}

# Canonical citations expected per target. Missing citations emit gaps.
_TARGET_EXPECTED_CITATIONS: dict[str, tuple[str, ...]] = {
    "iso42001-stage1": (
        "ISO/IEC 42001:2023, Clause 6.1.2",
        "ISO/IEC 42001:2023, Clause 6.1.3",
        "ISO/IEC 42001:2023, Clause 9.2",
        "ISO/IEC 42001:2023, Clause 9.3",
    ),
    "iso42001-stage2": (
        "ISO/IEC 42001:2023, Clause 6.1.2",
        "ISO/IEC 42001:2023, Clause 6.1.3",
        "ISO/IEC 42001:2023, Clause 9.2",
        "ISO/IEC 42001:2023, Clause 9.3",
        "ISO/IEC 42001:2023, Clause 10.2",
    ),
    "iso42001-surveillance": (
        "ISO/IEC 42001:2023, Clause 9.2",
        "ISO/IEC 42001:2023, Clause 9.3",
        "ISO/IEC 42001:2023, Clause 10.1",
        "ISO/IEC 42001:2023, Clause 10.2",
    ),
    "eu-ai-act-internal-control": (
        "EU AI Act, Article 9",
        "EU AI Act, Article 10",
        "EU AI Act, Article 12",
        "EU AI Act, Article 17",
        "EU AI Act, Article 27",
        "EU AI Act, Article 43",
    ),
    "eu-ai-act-notified-body": (
        "EU AI Act, Article 9",
        "EU AI Act, Article 10",
        "EU AI Act, Article 12",
        "EU AI Act, Article 17",
        "EU AI Act, Article 25",
        "EU AI Act, Article 27",
        "EU AI Act, Article 43",
    ),
    "colorado-sb205-safe-harbor": (
        "Colorado SB 205, Section 6-1-1706(3)",
    ),
    "nyc-ll144-annual-audit": (
        "NYC LL144",
    ),
    "singapore-magf-alignment": (
        "Singapore MAGF 2e, Pillar Internal Governance Structures and Measures",
    ),
    "uk-atrs-publication": (
        "UK ATRS, Section Tool description",
    ),
}

# Mapping of missing-artifact-type to the plugin that produces it. Used by
# the remediation engine for the target_plugin field.
_ARTIFACT_TO_PLUGIN: dict[str, str] = {
    "ai-system-inventory": "ai-system-inventory-maintainer",
    "role-matrix": "role-matrix-generator",
    "risk-register": "risk-register-builder",
    "soa": "soa-generator",
    "audit-log-entry": "audit-log-generator",
    "aisia": "aisia-runner",
    "nonconformity-register": "nonconformity-tracker",
    "management-review-package": "management-review-packager",
    "internal-audit-plan": "internal-audit-planner",
    "metrics-report": "metrics-collector",
    "gap-assessment": "gap-assessment",
    "data-register": "data-register-builder",
    "applicability-check": "applicability-checker",
    "high-risk-classification": "high-risk-classifier",
    "atrs-record": "uk-atrs-recorder",
    "colorado-compliance-record": "colorado-ai-act-compliance",
    "nyc-ll144-audit-package": "nyc-ll144-audit-packager",
    "magf-assessment": "singapore-magf-assessor",
    "supplier-vendor-assessment": "supplier-vendor-assessor",
}

# Curated remediation actions by gap type. The plugin never invents
# remediation language; unmapped gaps fall back to an explicit escalation
# string.
_REMEDIATION_BY_GAP: dict[str, str] = {
    "missing-ai-system-inventory": "Run ai-system-inventory-maintainer against the organization's system catalogue and include its output in the next bundle.",
    "missing-role-matrix": "Run role-matrix-generator with the current RACI assignments and include its output in the next bundle.",
    "missing-risk-register": "Run risk-register-builder against the AI system inventory and risk treatment decisions.",
    "missing-soa": "Run soa-generator against the Annex A control list, applying the organization's exclusion justifications.",
    "missing-audit-log-entry": "Run audit-log-generator at the cadence defined in the AIMS (every significant AIMS event per Clause 7.5.3).",
    "missing-aisia": "Run aisia-runner for every in-scope AI system. Complete FRIA sections for systems covered by EU AI Act Article 27.",
    "missing-nonconformity-register": "Run nonconformity-tracker; open records for every known nonconformity with owners and due dates.",
    "missing-management-review-package": "Run management-review-packager assembling the nine Clause 9.3.2(a)-(i) input categories.",
    "missing-internal-audit-plan": "Run internal-audit-planner; schedule at least one full audit cycle before Stage 2.",
    "missing-metrics-report": "Run metrics-collector over the reporting period; populate NIST MEASURE 2.x subcategories.",
    "missing-gap-assessment": "Run gap-assessment against the target framework (iso42001 for ISO certification; eu-ai-act for EU conformity).",
    "missing-data-register": "Run data-register-builder covering every dataset touched by an in-scope AI system (Article 10 + A.7).",
    "missing-high-risk-classification": "Run high-risk-classifier for every in-scope system covering Article 5, 6, Annex I, Annex III.",
    "missing-atrs-record": "Run uk-atrs-recorder for each public-sector-deployed system with Tier 1 fields populated.",
    "missing-colorado-compliance-record": "Run colorado-ai-act-compliance for every system within Colorado SB 205 scope with the actor role declared.",
    "missing-nyc-ll144-audit-package": "Run nyc-ll144-audit-packager against the AEDT; confirm auditor independence and schedule the annual re-audit.",
    "missing-magf-assessment": "Run singapore-magf-assessor covering all four MAGF 2e pillars.",
    "missing-supplier-vendor-assessment": "Run supplier-vendor-assessor for every third-party component in the AI supply chain (EU AI Act Article 25).",
    "legal-review-pending": "Complete the legal review of high-risk classification before submitting technical documentation.",
    "internal-audit-not-completed": "Complete one full internal-audit cycle and close the resulting nonconformities before Stage 2.",
    "imminent-reaudit-due": "Schedule the annual NYC LL144 re-audit with an independent auditor now; Section 5-304 requires 10-business-day public notice before the audit-date expiry.",
    "sb205-conformance-missing": "Declare ISO/IEC 42001 or NIST AI RMF conformance in the colorado-compliance-record.actor_conformance_frameworks field and include the supporting SoA, risk-register, and audit-log in the bundle.",
    "atrs-tier1-incomplete": "Populate all UK ATRS Tier 1 fields (Owner and contact, Tool description, Tool details, Impact assessment) before Cabinet Office publication.",
    "missing-citation": "Add the missing canonical citation to the upstream artifact; rerun the originating plugin so the citation propagates into the next bundle.",
    "warning-on-critical-control": "Clear the warning in the originating artifact; rerun the originating plugin with corrected input.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _today_utc() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _validate_inputs(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    target = inputs["target_certification"]
    if target not in VALID_TARGETS:
        raise ValueError(
            f"target_certification must be one of {VALID_TARGETS}; got {target!r}"
        )

    bundle_path = Path(inputs["bundle_path"])
    if not bundle_path.exists():
        raise ValueError(f"bundle_path {bundle_path!s} does not exist")
    if not bundle_path.is_dir():
        raise ValueError(f"bundle_path {bundle_path!s} is not a directory")

    overrides = inputs.get("scope_overrides")
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise ValueError("scope_overrides, when provided, must be a dict")
        strict = overrides.get("strict_mode")
        if strict is not None and not isinstance(strict, bool):
            raise ValueError("scope_overrides.strict_mode must be a bool")
        min_strength = overrides.get("minimum_evidence_strength")
        if min_strength is not None and min_strength not in VALID_MINIMUM_STRENGTH:
            raise ValueError(
                f"scope_overrides.minimum_evidence_strength must be one of "
                f"{VALID_MINIMUM_STRENGTH}; got {min_strength!r}"
            )

    deadline = inputs.get("remediation_deadline_days")
    if deadline is not None and (not isinstance(deadline, int) or deadline < 0):
        raise ValueError("remediation_deadline_days must be a non-negative int")


# ---------------------------------------------------------------------------
# Bundle loading
# ---------------------------------------------------------------------------


def _load_bundle_packager():
    """Sibling-import the evidence-bundle-packager plugin."""
    plugin_path = (
        Path(__file__).resolve().parent.parent
        / "evidence-bundle-packager"
        / "plugin.py"
    )
    if not plugin_path.is_file():
        raise FileNotFoundError(f"evidence-bundle-packager/plugin.py not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_cert_readiness_bundle_packager", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_manifest(bundle_dir: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load MANIFEST.json. Returns (manifest_or_none, warnings)."""
    warnings: list[str] = []
    manifest_path = bundle_dir / "MANIFEST.json"
    if not manifest_path.is_file():
        warnings.append(
            f"bundle_path {bundle_dir!s} is not a recognizable evidence bundle: "
            "MANIFEST.json is absent. Readiness cannot be assessed."
        )
        return None, warnings
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        warnings.append(f"MANIFEST.json could not be parsed: {exc}")
        return None, warnings
    if not isinstance(manifest, dict):
        warnings.append("MANIFEST.json did not contain a JSON object at the top level.")
        return None, warnings
    return manifest, warnings


def _index_artifacts_by_type(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Group manifest artifact entries by classified artifact type."""
    by_type: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest.get("artifacts", []):
        atype = entry.get("artifact_type")
        if not atype:
            continue
        by_type.setdefault(atype, []).append(entry)
    return by_type


def _load_artifact_json(bundle_dir: Path, entry: dict[str, Any]) -> dict[str, Any] | None:
    """Return the parsed JSON artifact, or None if not JSON or unreadable."""
    rel = entry.get("path")
    if not rel:
        return None
    if not str(rel).lower().endswith(".json"):
        return None
    abs_path = bundle_dir / rel
    if not abs_path.is_file():
        return None
    try:
        data = json.loads(abs_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _extract_citations_from_bundle(bundle_dir: Path) -> set[str]:
    """Pull unique citations from citation-summary.md.

    The evidence-bundle-packager writes enumerated citations under per-
    framework headings in that file. We parse every numbered line to
    assemble the full set.
    """
    summary_path = bundle_dir / "citation-summary.md"
    found: set[str] = set()
    if not summary_path.is_file():
        return found
    try:
        text = summary_path.read_text(encoding="utf-8")
    except OSError:
        return found
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Numbered list entries: "1. <citation>".
        first_dot = line.find(". ")
        if first_dot > 0 and line[:first_dot].isdigit():
            found.add(line[first_dot + 2:].strip())
    return found


# ---------------------------------------------------------------------------
# Evidence scoring
# ---------------------------------------------------------------------------


def _strength_from_artifact(
    artifact_json: dict[str, Any] | None,
    entries: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    """Compute evidence strength from a parsed artifact JSON and its manifest entries.

    Strength ladder:
    - strong: artifact present, has agent_signature, has at least one
      citation, zero warnings.
    - adequate: artifact present, at most one content-level warning, or
      missing citations but otherwise complete.
    - weak: artifact present but has multiple warnings or no citations.
    - absent: no artifact entries at all.
    """
    gap_notes: list[str] = []
    if not entries:
        return "absent", ["No artifact present in the bundle for this required type."]

    if artifact_json is None:
        # Non-JSON artifact (markdown or csv) is present but we cannot
        # introspect warnings. Treat as adequate; the underlying plugin's
        # determination is opaque to us.
        return "adequate", []

    warnings = artifact_json.get("warnings")
    warning_count = 0
    if isinstance(warnings, list):
        warning_count = len([w for w in warnings if w])
    citations = artifact_json.get("citations")
    has_citations = isinstance(citations, list) and any(citations)
    has_signature = bool(artifact_json.get("agent_signature"))

    if warning_count == 0 and has_citations and has_signature:
        return "strong", []
    if warning_count == 0 and has_signature:
        gap_notes.append("Artifact has no top-level citations list.")
        return "adequate", gap_notes
    if warning_count <= 1:
        gap_notes.append(f"Artifact carries {warning_count} warning(s).")
        return "adequate", gap_notes
    gap_notes.append(f"Artifact carries {warning_count} warning(s); evidence weak.")
    return "weak", gap_notes


def _strength_meets_minimum(actual: str, minimum: str) -> bool:
    return _STRENGTH_RANK.get(actual, 0) >= _STRENGTH_RANK.get(minimum, 0)


# ---------------------------------------------------------------------------
# Special-case target logic
# ---------------------------------------------------------------------------


def _check_iso42001_stage2_audit_cycle(
    artifacts_by_type: dict[str, list[dict[str, Any]]],
    bundle_dir: Path,
) -> tuple[bool, list[str]]:
    """Return (has_completed_cycle, notes)."""
    notes: list[str] = []
    entries = artifacts_by_type.get("internal-audit-plan", [])
    if not entries:
        return False, ["No internal-audit-plan artifact in bundle."]
    for entry in entries:
        artifact = _load_artifact_json(bundle_dir, entry)
        if artifact is None:
            continue
        schedule = artifact.get("audit_schedule")
        if isinstance(schedule, list):
            for cycle in schedule:
                if isinstance(cycle, dict) and cycle.get("cycle_status") == "completed":
                    return True, []
    notes.append(
        "internal-audit-plan carries no audit_schedule cycle with cycle_status='completed'; "
        "Stage 2 requires at least one completed cycle."
    )
    return False, notes


def _check_eu_ai_act_legal_review(
    artifacts_by_type: dict[str, list[dict[str, Any]]],
    bundle_dir: Path,
) -> tuple[bool, list[str]]:
    """Return (legal_review_cleared, notes)."""
    notes: list[str] = []
    entries = artifacts_by_type.get("high-risk-classification", [])
    if not entries:
        return False, ["No high-risk-classification artifact in bundle."]
    for entry in entries:
        artifact = _load_artifact_json(bundle_dir, entry)
        if artifact is None:
            continue
        requires = artifact.get("requires_legal_review")
        if requires is False:
            return True, []
        legal_completed = artifact.get("legal_review_completed")
        if legal_completed is True:
            return True, []
        if requires is True:
            notes.append(
                "high-risk-classification.requires_legal_review=true and no legal_review_completed=true indicator present."
            )
            return False, notes
    notes.append(
        "high-risk-classification artifact did not expose a requires_legal_review or legal_review_completed field."
    )
    return False, notes


def _check_sb205_conformance(
    artifacts_by_type: dict[str, list[dict[str, Any]]],
    bundle_dir: Path,
) -> tuple[bool, list[str]]:
    """Return (safe_harbor_available, notes).

    Colorado SB 205 Section 6-1-1706(3) recognizes conformance with
    ISO/IEC 42001 or NIST AI RMF as a rebuttable presumption of reasonable
    care. The bundle must either have colorado-compliance-record with
    actor_conformance_frameworks naming iso42001 or nist-ai-rmf, or the
    high-risk-classifier output must flag section_6_1_1706_3_applies.
    """
    notes: list[str] = []
    safe_harbor = False

    colorado_entries = artifacts_by_type.get("colorado-compliance-record", [])
    for entry in colorado_entries:
        artifact = _load_artifact_json(bundle_dir, entry)
        if artifact is None:
            continue
        actor_frameworks = artifact.get("actor_conformance_frameworks")
        if isinstance(actor_frameworks, list):
            names = [str(f).lower() for f in actor_frameworks]
            if any("iso42001" in n or "iso 42001" in n for n in names):
                safe_harbor = True
                break
            if any("nist" in n for n in names):
                safe_harbor = True
                break

    if not safe_harbor:
        hrc_entries = artifacts_by_type.get("high-risk-classification", [])
        for entry in hrc_entries:
            artifact = _load_artifact_json(bundle_dir, entry)
            if artifact is None:
                continue
            sb205 = artifact.get("sb205_assessment")
            if isinstance(sb205, dict) and sb205.get("section_6_1_1706_3_applies") is True:
                safe_harbor = True
                break

    if not safe_harbor:
        notes.append(
            "Neither colorado-compliance-record.actor_conformance_frameworks nor "
            "high-risk-classification.sb205_assessment.section_6_1_1706_3_applies "
            "establishes ISO 42001 or NIST AI RMF conformance. Safe-harbor presumption not available."
        )
    return safe_harbor, notes


def _check_nyc_ll144_reaudit(
    artifacts_by_type: dict[str, list[dict[str, Any]]],
    bundle_dir: Path,
) -> tuple[str, list[str]]:
    """Return (status, notes). Status is 'ok', 'imminent', or 'unknown'."""
    notes: list[str] = []
    entries = artifacts_by_type.get("nyc-ll144-audit-package", [])
    if not entries:
        return "unknown", ["No nyc-ll144-audit-package artifact in bundle."]
    now = _today_utc()
    for entry in entries:
        artifact = _load_artifact_json(bundle_dir, entry)
        if artifact is None:
            continue
        summary = artifact.get("summary")
        next_due: str | None = None
        if isinstance(summary, dict):
            next_due = summary.get("next_audit_due_by")
        if not next_due:
            next_due = artifact.get("next_audit_due_by")
        if not next_due:
            continue
        try:
            due_dt = datetime.fromisoformat(str(next_due).replace("Z", "+00:00"))
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        delta = due_dt - now
        if delta < timedelta(days=30):
            notes.append(
                f"next_audit_due_by={next_due} is within 30 days; schedule the annual re-audit now."
            )
            return "imminent", notes
        return "ok", notes
    return "unknown", ["nyc-ll144-audit-package did not expose next_audit_due_by."]


def _check_atrs_tier1(
    artifacts_by_type: dict[str, list[dict[str, Any]]],
    bundle_dir: Path,
) -> tuple[bool, list[str]]:
    """Return (tier1_populated, notes). Tier 1 fields must all be populated."""
    notes: list[str] = []
    entries = artifacts_by_type.get("atrs-record", [])
    if not entries:
        return False, ["No atrs-record artifact in bundle."]
    tier1_sections = (
        "owner_and_contact",
        "tool_description",
        "tool_details",
        "impact_assessment",
    )
    for entry in entries:
        artifact = _load_artifact_json(bundle_dir, entry)
        if artifact is None:
            continue
        # Tier 1 population may appear under several shapes.
        sections = artifact.get("sections") or artifact.get("tier1") or artifact
        populated = 0
        for key in tier1_sections:
            value = sections.get(key) if isinstance(sections, dict) else None
            if value:
                populated += 1
        if populated >= len(tier1_sections):
            return True, []
        notes.append(
            f"atrs-record has {populated}/{len(tier1_sections)} Tier 1 sections populated."
        )
        return False, notes
    return False, ["atrs-record artifact did not expose Tier 1 sections."]


# ---------------------------------------------------------------------------
# Remediation engine
# ---------------------------------------------------------------------------


def _owner_from_role_matrix(
    artifacts_by_type: dict[str, list[dict[str, Any]]],
    bundle_dir: Path,
    fallback: str = "AIMS Owner",
) -> str:
    """Best-effort role extraction from the bundle's role-matrix artifact."""
    entries = artifacts_by_type.get("role-matrix", [])
    for entry in entries:
        artifact = _load_artifact_json(bundle_dir, entry)
        if artifact is None:
            continue
        rows = artifact.get("rows") or artifact.get("roles")
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                role_name = row.get("role") or row.get("role_name")
                if role_name:
                    return str(role_name)
    return fallback


def _build_remediation(
    gap_key: str,
    gap_description: str,
    owner_role: str,
    remediation_deadline_days: int,
) -> dict[str, Any]:
    recommended = _REMEDIATION_BY_GAP.get(
        gap_key,
        "Requires practitioner judgment; escalate to Lead Implementer.",
    )
    # Derive target_plugin from gap_key.
    target_plugin = ""
    if gap_key.startswith("missing-"):
        artifact_type = gap_key[len("missing-"):]
        target_plugin = _ARTIFACT_TO_PLUGIN.get(artifact_type, "")
    if not target_plugin:
        target_plugin = _INFERRED_TARGET_PLUGIN.get(gap_key, "practitioner-review")

    deadline_iso = (_today_utc() + timedelta(days=remediation_deadline_days)).date().isoformat()
    return {
        "gap_key": gap_key,
        "gap_description": gap_description,
        "recommended_action": recommended,
        "owner_role": owner_role,
        "target_plugin": target_plugin,
        "suggested_deadline": deadline_iso,
    }


_INFERRED_TARGET_PLUGIN: dict[str, str] = {
    "legal-review-pending": "high-risk-classifier",
    "internal-audit-not-completed": "internal-audit-planner",
    "imminent-reaudit-due": "nyc-ll144-audit-packager",
    "sb205-conformance-missing": "colorado-ai-act-compliance",
    "atrs-tier1-incomplete": "uk-atrs-recorder",
    "missing-citation": "practitioner-review",
    "warning-on-critical-control": "practitioner-review",
}


# ---------------------------------------------------------------------------
# Core assessment
# ---------------------------------------------------------------------------


def assess_readiness(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Assess evidence-bundle readiness against a target certification.

    Args:
        inputs: Dict with bundle_path (required), target_certification
            (required). Optional scope_overrides (strict_mode,
            jurisdiction_restriction, minimum_evidence_strength), reviewed_by,
            remediation_deadline_days (default 90).

    Returns:
        Dict with timestamp, agent_signature, target_certification,
        bundle_id_ref, readiness_level, evidence_completeness,
        crosswalk_coverage (when applicable), conditions, gaps, blockers,
        remediations, citations, warnings, summary, reviewed_by.

    Raises:
        ValueError: on structural input problems.
    """
    _validate_inputs(inputs)

    bundle_dir = Path(inputs["bundle_path"]).resolve()
    target = inputs["target_certification"]
    overrides = inputs.get("scope_overrides") or {}
    strict_mode = bool(overrides.get("strict_mode", False))
    minimum_strength = overrides.get("minimum_evidence_strength", "adequate")
    remediation_deadline_days = int(inputs.get("remediation_deadline_days", 90))
    reviewed_by = inputs.get("reviewed_by")

    warnings_list: list[str] = []
    gaps: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    conditions: list[dict[str, Any]] = []
    remediations: list[dict[str, Any]] = []

    manifest, manifest_warnings = _load_manifest(bundle_dir)
    warnings_list.extend(manifest_warnings)

    bundle_id_ref = None
    artifacts_by_type: dict[str, list[dict[str, Any]]] = {}
    bundle_citations: set[str] = set()

    if manifest is not None:
        bundle_id_ref = manifest.get("bundle_id")
        artifacts_by_type = _index_artifacts_by_type(manifest)
        bundle_citations = _extract_citations_from_bundle(bundle_dir)

    required = _TARGET_REQUIRED_ARTIFACTS.get(target, [])
    evidence_completeness: list[dict[str, Any]] = []
    owner_role_guess = _owner_from_role_matrix(artifacts_by_type, bundle_dir)

    for requirement in required:
        artifact_type = requirement["artifact_type"]
        is_critical = requirement["critical"]
        entries = artifacts_by_type.get(artifact_type, [])
        artifact_json = None
        if entries:
            artifact_json = _load_artifact_json(bundle_dir, entries[0])
        strength, notes = _strength_from_artifact(artifact_json, entries)
        row = {
            "required_artifact": artifact_type,
            "critical": is_critical,
            "present": bool(entries),
            "evidence_strength": strength,
            "gap_notes": notes,
        }
        evidence_completeness.append(row)

        if not entries:
            description = (
                f"Required artifact {artifact_type!r} is absent from the bundle."
            )
            gap_key = f"missing-{artifact_type}"
            remediation = _build_remediation(
                gap_key, description, owner_role_guess, remediation_deadline_days
            )
            remediations.append(remediation)
            if is_critical:
                blockers.append({
                    "gap_key": gap_key,
                    "description": description,
                    "artifact_type": artifact_type,
                })
            else:
                gaps.append({
                    "gap_key": gap_key,
                    "description": description,
                    "artifact_type": artifact_type,
                })
            continue

        # Evidence-strength floor check.
        if not _strength_meets_minimum(strength, minimum_strength):
            description = (
                f"Artifact {artifact_type!r} present but evidence strength "
                f"{strength!r} is below minimum {minimum_strength!r}."
            )
            gap_key = "warning-on-critical-control" if is_critical else "warning-on-critical-control"
            remediation = _build_remediation(
                gap_key, description, owner_role_guess, remediation_deadline_days
            )
            remediations.append(remediation)
            if is_critical:
                if strict_mode:
                    blockers.append({
                        "gap_key": gap_key,
                        "description": description,
                        "artifact_type": artifact_type,
                    })
                else:
                    conditions.append({
                        "gap_key": gap_key,
                        "description": description,
                        "artifact_type": artifact_type,
                    })
            else:
                conditions.append({
                    "gap_key": gap_key,
                    "description": description,
                    "artifact_type": artifact_type,
                })
            continue

        # Adequate-or-better artifact with warnings still surfaces a condition
        # when critical.
        if artifact_json is not None:
            wlist = artifact_json.get("warnings")
            if isinstance(wlist, list) and any(wlist):
                description = (
                    f"Artifact {artifact_type!r} present with "
                    f"{len([w for w in wlist if w])} content warning(s)."
                )
                gap_key = "warning-on-critical-control"
                remediation = _build_remediation(
                    gap_key, description, owner_role_guess, remediation_deadline_days
                )
                remediations.append(remediation)
                if is_critical:
                    if strict_mode:
                        blockers.append({
                            "gap_key": gap_key,
                            "description": description,
                            "artifact_type": artifact_type,
                        })
                    else:
                        conditions.append({
                            "gap_key": gap_key,
                            "description": description,
                            "artifact_type": artifact_type,
                        })
                else:
                    conditions.append({
                        "gap_key": gap_key,
                        "description": description,
                        "artifact_type": artifact_type,
                    })

    # Target-specific special logic.
    crosswalk_coverage: list[dict[str, Any]] = []
    if target == "iso42001-stage2":
        cycle_ok, cycle_notes = _check_iso42001_stage2_audit_cycle(artifacts_by_type, bundle_dir)
        if not cycle_ok:
            description = (
                cycle_notes[0] if cycle_notes
                else "No completed internal-audit cycle present in bundle."
            )
            gap_key = "internal-audit-not-completed"
            blockers.append({
                "gap_key": gap_key,
                "description": description,
                "artifact_type": "internal-audit-plan",
            })
            remediations.append(_build_remediation(
                gap_key, description, owner_role_guess, remediation_deadline_days
            ))

    if target in ("eu-ai-act-internal-control", "eu-ai-act-notified-body"):
        cleared, legal_notes = _check_eu_ai_act_legal_review(artifacts_by_type, bundle_dir)
        if not cleared:
            description = (
                legal_notes[0] if legal_notes
                else "Legal review of high-risk classification not confirmed."
            )
            gap_key = "legal-review-pending"
            gaps.append({
                "gap_key": gap_key,
                "description": description,
                "artifact_type": "high-risk-classification",
            })
            remediations.append(_build_remediation(
                gap_key, description, owner_role_guess, remediation_deadline_days
            ))

    if target == "colorado-sb205-safe-harbor":
        safe_harbor, sb205_notes = _check_sb205_conformance(artifacts_by_type, bundle_dir)
        if not safe_harbor:
            description = (
                sb205_notes[0] if sb205_notes
                else "Colorado SB 205 safe-harbor conformance not established."
            )
            gap_key = "sb205-conformance-missing"
            blockers.append({
                "gap_key": gap_key,
                "description": description,
                "artifact_type": "colorado-compliance-record",
            })
            remediations.append(_build_remediation(
                gap_key, description, owner_role_guess, remediation_deadline_days
            ))

    if target == "nyc-ll144-annual-audit":
        status, ll144_notes = _check_nyc_ll144_reaudit(artifacts_by_type, bundle_dir)
        if status == "imminent":
            description = ll144_notes[0] if ll144_notes else "Annual re-audit is imminent."
            gap_key = "imminent-reaudit-due"
            conditions.append({
                "gap_key": gap_key,
                "description": description,
                "artifact_type": "nyc-ll144-audit-package",
            })
            remediations.append(_build_remediation(
                gap_key, description, owner_role_guess, remediation_deadline_days
            ))
        elif status == "unknown":
            for note in ll144_notes:
                warnings_list.append(note)

    if target == "uk-atrs-publication":
        tier1_ok, atrs_notes = _check_atrs_tier1(artifacts_by_type, bundle_dir)
        if not tier1_ok:
            description = atrs_notes[0] if atrs_notes else "UK ATRS Tier 1 not fully populated."
            gap_key = "atrs-tier1-incomplete"
            gaps.append({
                "gap_key": gap_key,
                "description": description,
                "artifact_type": "atrs-record",
            })
            remediations.append(_build_remediation(
                gap_key, description, owner_role_guess, remediation_deadline_days
            ))

    # Citation verification.
    expected_citations = _TARGET_EXPECTED_CITATIONS.get(target, ())
    missing_citations: list[str] = []
    for expected in expected_citations:
        if not any(expected in c for c in bundle_citations):
            missing_citations.append(expected)
    for miss in missing_citations:
        description = f"Canonical citation missing from bundle citation-summary: {miss!r}."
        gap_key = "missing-citation"
        gaps.append({
            "gap_key": gap_key,
            "description": description,
            "artifact_type": "citation",
            "citation": miss,
        })
        remediations.append(_build_remediation(
            gap_key, description, owner_role_guess, remediation_deadline_days
        ))

    # Cross-framework coverage block (ISO + EU targets only).
    if target.startswith("iso42001") or target.startswith("eu-ai-act"):
        for expected in expected_citations:
            found_in: list[str] = []
            for artifact_type, entries in artifacts_by_type.items():
                for entry in entries:
                    artifact = _load_artifact_json(bundle_dir, entry)
                    if not artifact:
                        continue
                    cits = artifact.get("citations")
                    if isinstance(cits, list) and any(expected in str(c) for c in cits):
                        found_in.append(entry.get("plugin") or artifact_type)
                        break
            crosswalk_coverage.append({
                "citation_expected": expected,
                "found_in_artifact": sorted(set(found_in)),
                "coverage_status": "covered" if found_in else "not-covered",
            })

    # Readiness-level computation.
    if manifest is None:
        readiness_level = "not-ready"
    elif blockers:
        readiness_level = "not-ready"
    elif gaps:
        readiness_level = "partially-ready"
    elif conditions:
        readiness_level = "ready-with-conditions"
    else:
        readiness_level = "ready-with-high-confidence"

    summary = {
        "target_certification": target,
        "readiness_level": readiness_level,
        "blocker_count": len(blockers),
        "gap_count": len(gaps),
        "condition_count": len(conditions),
        "remediation_count": len(remediations),
        "required_artifact_count": len(required),
        "artifacts_present": sum(1 for r in evidence_completeness if r["present"]),
        "missing_citation_count": len(missing_citations),
        "strict_mode": strict_mode,
        "minimum_evidence_strength": minimum_strength,
    }

    # Citations applicable to the readiness report itself.
    citations = _readiness_report_citations(target)

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "target_certification": target,
        "bundle_id_ref": bundle_id_ref,
        "readiness_level": readiness_level,
        "evidence_completeness": evidence_completeness,
        "crosswalk_coverage": crosswalk_coverage,
        "conditions": conditions,
        "gaps": gaps,
        "blockers": blockers,
        "remediations": remediations,
        "citations": citations,
        "warnings": warnings_list,
        "summary": summary,
        "reviewed_by": reviewed_by,
    }


def _readiness_report_citations(target: str) -> list[str]:
    """Citations that anchor the readiness report itself, not the evidence within."""
    if target.startswith("iso42001"):
        return [
            "ISO/IEC 42001:2023, Clause 9.2",
            "ISO/IEC 42001:2023, Clause 9.3",
            "ISO/IEC 42001:2023, Clause 10.1",
        ]
    if target == "eu-ai-act-internal-control":
        return [
            "EU AI Act, Article 43",
            "EU AI Act, Annex VI",
        ]
    if target == "eu-ai-act-notified-body":
        return [
            "EU AI Act, Article 43",
            "EU AI Act, Annex VII",
        ]
    if target == "colorado-sb205-safe-harbor":
        return [
            "Colorado SB 205, Section 6-1-1706(3)",
            "Colorado SB 205, Section 6-1-1706(4)",
        ]
    if target == "nyc-ll144-annual-audit":
        return [
            "NYC LL144 Final Rule, Section 5-301",
            "NYC LL144 Final Rule, Section 5-304",
        ]
    if target == "singapore-magf-alignment":
        return [
            "Singapore MAGF 2e, Pillar Internal Governance Structures and Measures",
        ]
    if target == "uk-atrs-publication":
        return [
            "UK ATRS, Section Tool description",
            "UK ATRS, Section Impact assessment",
        ]
    return []


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


_LEGAL_DISCLAIMER = (
    "> This readiness report is informational. It does not constitute an "
    "audit opinion or legal advice. Certification decisions require a "
    "qualified auditor or notified body."
)


def render_markdown(report: dict[str, Any]) -> str:
    """Render a readiness report as Markdown, with the legal disclaimer callout."""
    required = (
        "timestamp", "agent_signature", "target_certification",
        "readiness_level", "evidence_completeness", "summary",
    )
    missing = [k for k in required if k not in report]
    if missing:
        raise ValueError(f"report missing required fields: {missing}")

    lines: list[str] = []
    lines.append("# Certification Readiness Report")
    lines.append("")
    lines.append(_LEGAL_DISCLAIMER)
    lines.append("")
    lines.append(f"**Target certification:** {report['target_certification']}")
    lines.append(f"**Readiness level:** {report['readiness_level']}")
    lines.append(f"**Generated at (UTC):** {report['timestamp']}")
    lines.append(f"**Generated by:** {report['agent_signature']}")
    if report.get("bundle_id_ref"):
        lines.append(f"**Bundle id:** {report['bundle_id_ref']}")
    if report.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {report['reviewed_by']}")

    summary = report["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Required artifacts: {summary['required_artifact_count']}",
        f"- Artifacts present: {summary['artifacts_present']}",
        f"- Blockers: {summary['blocker_count']}",
        f"- Gaps: {summary['gap_count']}",
        f"- Conditions: {summary['condition_count']}",
        f"- Remediations: {summary['remediation_count']}",
        f"- Missing citations: {summary['missing_citation_count']}",
        f"- Strict mode: {summary['strict_mode']}",
        f"- Minimum evidence strength: {summary['minimum_evidence_strength']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in report.get("citations", []):
        lines.append(f"- {c}")

    lines.extend(["", "## Evidence completeness", "", "| Required artifact | Critical | Present | Evidence strength | Notes |", "|---|---|---|---|---|"])
    for row in report["evidence_completeness"]:
        notes = "; ".join(row.get("gap_notes", [])).replace("|", "\\|") or ""
        lines.append(
            f"| {row['required_artifact']} | {row['critical']} | {row['present']} | "
            f"{row['evidence_strength']} | {notes} |"
        )

    crosswalk = report.get("crosswalk_coverage") or []
    if crosswalk:
        lines.extend(["", "## Crosswalk coverage", "", "| Expected citation | Coverage status | Found in |", "|---|---|---|"])
        for row in crosswalk:
            found = ", ".join(row["found_in_artifact"]) if row["found_in_artifact"] else ""
            lines.append(
                f"| {row['citation_expected']} | {row['coverage_status']} | {found} |"
            )

    if report.get("blockers"):
        lines.extend(["", "## Blockers", ""])
        for b in report["blockers"]:
            lines.append(f"- [{b['gap_key']}] {b['description']}")

    if report.get("gaps"):
        lines.extend(["", "## Gaps", ""])
        for g in report["gaps"]:
            lines.append(f"- [{g['gap_key']}] {g['description']}")

    if report.get("conditions"):
        lines.extend(["", "## Conditions", ""])
        for c in report["conditions"]:
            lines.append(f"- [{c['gap_key']}] {c['description']}")

    if report.get("remediations"):
        lines.extend([
            "",
            "## Remediations",
            "",
            "| Gap | Recommended action | Owner role | Target plugin | Suggested deadline |",
            "|---|---|---|---|---|",
        ])
        for r in report["remediations"]:
            desc = r["gap_description"].replace("|", "\\|")
            action = r["recommended_action"].replace("|", "\\|")
            lines.append(
                f"| {desc} | {action} | {r['owner_role']} | {r['target_plugin']} | {r['suggested_deadline']} |"
            )

    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in report["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(report: dict[str, Any]) -> str:
    """Render gaps, blockers, conditions, and remediations as CSV rows."""
    if "remediations" not in report:
        raise ValueError("report missing required field 'remediations'")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "row_kind", "gap_key", "description_or_action",
        "artifact_type", "owner_role", "target_plugin", "suggested_deadline",
    ])
    for b in report.get("blockers", []):
        writer.writerow([
            "blocker", b.get("gap_key", ""), b.get("description", ""),
            b.get("artifact_type", ""), "", "", "",
        ])
    for g in report.get("gaps", []):
        writer.writerow([
            "gap", g.get("gap_key", ""), g.get("description", ""),
            g.get("artifact_type", ""), "", "", "",
        ])
    for c in report.get("conditions", []):
        writer.writerow([
            "condition", c.get("gap_key", ""), c.get("description", ""),
            c.get("artifact_type", ""), "", "", "",
        ])
    for r in report.get("remediations", []):
        writer.writerow([
            "remediation", r.get("gap_key", ""), r.get("recommended_action", ""),
            "", r.get("owner_role", ""), r.get("target_plugin", ""),
            r.get("suggested_deadline", ""),
        ])
    return buf.getvalue()


__all__ = [
    "AGENT_SIGNATURE",
    "REQUIRED_INPUT_FIELDS",
    "VALID_TARGETS",
    "VALID_READINESS_LEVELS",
    "VALID_EVIDENCE_STRENGTH",
    "assess_readiness",
    "render_markdown",
    "render_csv",
]
