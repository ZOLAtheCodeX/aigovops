"""
AIGovOps: Supplier and Vendor Assessor Plugin

Operationalizes ISO/IEC 42001:2023 Annex A category A.10 (Allocation of
responsibilities, Suppliers, Customers) together with EU AI Act Article 25
(Responsibilities along the AI value chain) and NYC Local Law 144 Final
Rule Section 5-300 auditor-independence requirements. Produces a formal
supplier-risk record structured for audit evidence and for onward use in
role matrices, audit logs, and evidence bundles.

Design stance: the plugin does NOT rate vendors, compute risk scores, or
invent assessment outcomes. Vendor selection, independence determination,
and risk acceptance are organizational decisions per Clause 5.3 and
A.10.2. The plugin validates structured inputs, maps them deterministically
to ISO, EU AI Act, and NYC LL144 obligations, flags gaps as warnings, and
surfaces the independence-assertion criteria that a practitioner must
confirm for audit-service vendors.

Status: Phase 3 minimum-viable implementation. 0.1.0.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "supplier-vendor-assessor/0.1.0"

REQUIRED_INPUT_FIELDS = ("vendor_description", "vendor_role", "organization_role")

VALID_VENDOR_ROLES = (
    "model-provider",
    "training-data-provider",
    "mlops-platform",
    "deployment-infrastructure",
    "evaluation-service",
    "bias-audit-service",
    "red-team-service",
    "content-moderation-service",
    "monitoring-service",
    "adjudicator-human-in-loop",
)

VALID_ORGANIZATION_ROLES = (
    "provider",
    "deployer",
    "distributor",
    "importer",
    "authorized-representative",
    "downstream-integrator",
)

VALID_ASSESSMENT_DIMENSIONS = (
    "technical-capability",
    "security-posture",
    "data-governance",
    "contractual-obligations",
    "regulatory-alignment",
    "incident-response",
    "financial-stability",
    "independence-and-impartiality",
)

VALID_ASSESSMENT_STATUSES = (
    "addressed",
    "partial",
    "not-addressed",
    "requires-practitioner-assessment",
)

INDEPENDENCE_REQUIRED_ROLES = (
    "bias-audit-service",
    "red-team-service",
    "evaluation-service",
)

INDEPENDENCE_CRITERIA = (
    "no material financial interest in the AEDT",
    "no material financial interest in its developer or deployer",
    "compensation not contingent on audit outcome",
    "prior engagements disclosed",
)

# Conservative incident-notification threshold. A vendor SLA permitting more
# than this many days to notify the deployer of a security incident is flagged
# for practitioner review against ISO A.10.3 and EU AI Act Article 26(5)
# downstream-notification expectations.
INCIDENT_NOTIFICATION_THRESHOLD_DAYS = 15

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily inside
# the enrichment helper so basic calls (enrich_with_crosswalk=False) pay no
# import cost.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    vendor_description = inputs["vendor_description"]
    if not isinstance(vendor_description, dict):
        raise ValueError("vendor_description must be a dict")
    for req in ("vendor_name",):
        if req not in vendor_description or not vendor_description[req]:
            raise ValueError(f"vendor_description missing required field {req!r}")

    vendor_role = inputs["vendor_role"]
    if vendor_role not in VALID_VENDOR_ROLES:
        raise ValueError(
            f"vendor_role must be one of {VALID_VENDOR_ROLES}; got {vendor_role!r}"
        )

    organization_role = inputs["organization_role"]
    if organization_role not in VALID_ORGANIZATION_ROLES:
        raise ValueError(
            f"organization_role must be one of {VALID_ORGANIZATION_ROLES}; got {organization_role!r}"
        )

    dims = inputs.get("assessment_dimensions")
    if dims is not None:
        if not isinstance(dims, list):
            raise ValueError("assessment_dimensions, when provided, must be a list")
        for d in dims:
            if d not in VALID_ASSESSMENT_DIMENSIONS:
                raise ValueError(
                    f"assessment_dimensions entry {d!r} not in {VALID_ASSESSMENT_DIMENSIONS}"
                )

    contract_summary = inputs.get("contract_summary")
    if contract_summary is not None and not isinstance(contract_summary, dict):
        raise ValueError("contract_summary, when provided, must be a dict")

    sub_processors = inputs.get("sub_processors")
    if sub_processors is not None and not isinstance(sub_processors, list):
        raise ValueError("sub_processors, when provided, must be a list")

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")

    independence = inputs.get("independence_check_required")
    if independence is not None and not isinstance(independence, bool):
        raise ValueError("independence_check_required, when provided, must be a bool")


def _build_role_reconciliation(
    organization_role: str,
    vendor_role: str,
    deployer_modification_note: str | None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Return (role_reconciliation_dict, warnings, citations)."""
    warnings: list[str] = []
    citations: list[str] = []
    notes: list[str] = []

    # EU Art. 25(1)(c): deployer who substantially modifies a high-risk system
    # may be re-classified as a provider.
    if organization_role == "deployer" and deployer_modification_note:
        warnings.append(
            "Per EU AI Act Art. 25(1)(c), substantial modification may re-classify organization "
            "as a provider. Confirm legal review."
        )
        citations.append("EU AI Act, Article 25, Paragraph 1")
        notes.append(
            f"Deployer-modification note recorded: {deployer_modification_note}"
        )

    # EU Art. 25(3)(c): distributor obligations when distributing a model-provider's system.
    if organization_role == "distributor" and vendor_role == "model-provider":
        citations.append("EU AI Act, Article 25, Paragraph 3")
        notes.append(
            "Distributor distributing a model-provider's system. Article 25(3)(c) obligations apply: "
            "verify CE marking, verify required documentation and instructions, act against non-conformity."
        )

    # EU Art. 26(a): importer check obligations.
    if organization_role == "importer":
        citations.append("EU AI Act, Article 26, Paragraph 1")
        notes.append(
            "Importer obligations apply. Article 26(a) check obligations: verify conformity assessment, "
            "technical documentation, CE marking, and authorized-representative designation before placing on EU market."
        )

    # Downstream integrator of a general-purpose AI model under Art. 25(4).
    if organization_role == "downstream-integrator" and vendor_role == "model-provider":
        citations.append("EU AI Act, Article 25, Paragraph 4")
        notes.append(
            "Downstream integrator of a general-purpose AI model. Article 25(4) cooperation obligations apply: "
            "upstream model provider must supply the information and documentation needed to integrate safely."
        )

    return (
        {
            "organization_role": organization_role,
            "vendor_role": vendor_role,
            "deployer_modification_note": deployer_modification_note,
            "notes": notes,
        },
        warnings,
        citations,
    )


def _independence_assessment(vendor_role: str) -> dict[str, Any]:
    warnings: list[str] = []
    if vendor_role not in INDEPENDENCE_REQUIRED_ROLES:
        warnings.append(
            f"Independence check requested for vendor_role {vendor_role!r} which is not in the "
            f"canonical list {list(INDEPENDENCE_REQUIRED_ROLES)}; confirm scope with practitioner."
        )
    return {
        "required_by": ["NYC LL144 Final Rule, Section 5-300"],
        "criteria": list(INDEPENDENCE_CRITERIA),
        "status": "requires-practitioner-confirmation",
        "warnings": warnings,
    }


def _assess_dimension(
    dimension: str,
    contract_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return {name, status, evidence_refs, warnings} for a single dimension."""
    evidence_refs: list[str] = []
    warnings: list[str] = []
    status: str = "requires-practitioner-assessment"

    contract = contract_summary or {}

    if dimension == "contractual-obligations":
        contract_id = contract.get("contract_id")
        audit_rights = contract.get("audit_rights_included")
        if audit_rights is True:
            status = "addressed"
            if contract_id:
                evidence_refs.append(f"contract:{contract_id}")
        elif audit_rights is False:
            status = "partial"
            warnings.append(
                "contract.audit_rights_included is False; ISO/IEC 42001:2023, Annex A, Control A.10.3 "
                "expects supplier contracts to grant audit rights for AI-system obligations. Document justification "
                "or renegotiate."
            )
        else:
            status = "not-addressed"
            warnings.append(
                "contract.audit_rights_included not specified; cannot verify A.10.3 audit-rights expectation."
            )

    elif dimension == "data-governance":
        dpa = contract.get("data_processing_agreement_included")
        if dpa is True:
            status = "addressed"
        elif dpa is False:
            status = "not-addressed"
            warnings.append(
                "contract.data_processing_agreement_included is False; vendors handling personal or training data "
                "require a DPA per A.10.3 and applicable data-protection law."
            )
        else:
            status = "requires-practitioner-assessment"
            warnings.append(
                "contract.data_processing_agreement_included not specified; practitioner must confirm DPA status."
            )

    elif dimension == "incident-response":
        notification_days = contract.get("security_incident_notification_days")
        if notification_days is None:
            status = "not-addressed"
            warnings.append(
                "contract.security_incident_notification_days not specified; A.10.3 and Article 26(5) require "
                "defined vendor-to-deployer incident notification timing."
            )
        else:
            try:
                days = int(notification_days)
            except (TypeError, ValueError):
                days = None
            if days is None:
                status = "requires-practitioner-assessment"
                warnings.append(
                    "contract.security_incident_notification_days is not an integer; fix the contract summary."
                )
            elif days <= INCIDENT_NOTIFICATION_THRESHOLD_DAYS:
                status = "addressed"
            else:
                status = "partial"
                warnings.append(
                    f"contract.security_incident_notification_days is {days}, exceeding the "
                    f"{INCIDENT_NOTIFICATION_THRESHOLD_DAYS}-day conservative threshold. Practitioner may accept or "
                    "renegotiate; document the justification."
                )

    elif dimension == "regulatory-alignment":
        status = "requires-practitioner-assessment"
        warnings.append(
            "regulatory-alignment requires practitioner review of vendor regulatory posture against applicable frameworks."
        )

    elif dimension == "technical-capability":
        status = "requires-practitioner-assessment"
        warnings.append(
            "technical-capability requires practitioner review of vendor engineering maturity and validation evidence."
        )

    elif dimension == "security-posture":
        status = "requires-practitioner-assessment"
        warnings.append(
            "security-posture requires practitioner review of vendor security certifications and attestations."
        )

    elif dimension == "financial-stability":
        status = "requires-practitioner-assessment"
        warnings.append(
            "financial-stability requires practitioner review of vendor financial condition; NIST GOVERN 6.2 "
            "contingency planning applies."
        )

    elif dimension == "independence-and-impartiality":
        status = "requires-practitioner-assessment"
        warnings.append(
            "independence-and-impartiality requires practitioner confirmation per NYC LL144 Section 5-300 criteria."
        )

    return {
        "name": dimension,
        "status": status,
        "evidence_refs": evidence_refs,
        "warnings": warnings,
    }


def _build_supply_chain_graph(
    organization_role: str,
    vendor_description: dict[str, Any],
    sub_processors: list[dict[str, Any]],
) -> dict[str, Any]:
    tiers: list[dict[str, Any]] = []
    for sp in sub_processors:
        if not isinstance(sp, dict):
            tiers.append({"tier_2_assessment": "tier-2-assessment-pending", "raw": sp})
            continue
        tiers.append(
            {
                "vendor_name": sp.get("vendor_name"),
                "vendor_type": sp.get("vendor_type"),
                "jurisdiction_of_establishment": sp.get("jurisdiction_of_establishment"),
                "products_services": sp.get("products_services") or [],
                "tier_2_assessment": "tier-2-assessment-pending",
            }
        )
    return {
        "organization": {"role": organization_role},
        "tier_1_vendor": {
            "vendor_name": vendor_description.get("vendor_name"),
            "vendor_type": vendor_description.get("vendor_type"),
            "jurisdiction_of_establishment": vendor_description.get("jurisdiction_of_establishment"),
        },
        "tier_2_sub_processors": tiers,
    }


def _base_citations() -> list[str]:
    return [
        "ISO/IEC 42001:2023, Annex A, Control A.10.2",
        "ISO/IEC 42001:2023, Annex A, Control A.10.3",
        "ISO/IEC 42001:2023, Annex A, Control A.10.4",
        "NIST GOVERN 6.1",
        "NIST GOVERN 6.2",
    ]


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_supplier", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _crosswalk_enrich() -> tuple[list[dict[str, Any]], list[str]]:
    """Return (mappings, warnings) for A.10.* source_refs across all loaded targets."""
    try:
        crosswalk = _load_crosswalk_module()
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return ([], [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"])

    filtered: list[dict[str, Any]] = []
    for m in data.get("mappings", []):
        source_ref = str(m.get("source_ref") or "")
        source_framework = m.get("source_framework")
        if source_framework == "iso42001" and source_ref.startswith("A.10"):
            filtered.append(
                {
                    "source_framework": source_framework,
                    "source_ref": source_ref,
                    "target_framework": m.get("target_framework"),
                    "target_ref": m.get("target_ref"),
                    "relationship": m.get("relationship"),
                    "confidence": m.get("confidence"),
                }
            )
        elif source_framework == "eu-ai-act" and source_ref.startswith("Article 25"):
            filtered.append(
                {
                    "source_framework": source_framework,
                    "source_ref": source_ref,
                    "target_framework": m.get("target_framework"),
                    "target_ref": m.get("target_ref"),
                    "relationship": m.get("relationship"),
                    "confidence": m.get("confidence"),
                }
            )
    return (filtered, [])


def assess_vendor(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Produce a supplier-vendor assessment record.

    Args:
        inputs: Dict with:
            vendor_description (required): dict with vendor_name,
                vendor_type, jurisdiction_of_establishment, products_services,
                ai_systems_they_supply.
            vendor_role (required): one of VALID_VENDOR_ROLES.
            organization_role (required): one of VALID_ORGANIZATION_ROLES.
            contract_summary (optional): dict with contract metadata.
            assessment_dimensions (optional): list from VALID_ASSESSMENT_DIMENSIONS.
                Defaults to all eight.
            independence_check_required (optional): bool. Defaults True for
                bias-audit-service, red-team-service, evaluation-service; False otherwise.
            deployer_modification_note (optional): string describing substantial
                modification per EU AI Act Art. 25(1)(c).
            sub_processors (optional): list of vendor-description dicts.
            enrich_with_crosswalk (optional): bool, default True.
            reviewed_by (optional): reviewer identity.

    Returns:
        Dict with timestamp, agent_signature, framework, vendor_description_echo,
        role_reconciliation, assessment_matrix, independence_assessment (when
        required), supply_chain_graph (when sub_processors present), citations,
        warnings, summary, cross_framework_citations (when enriched).

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    vendor_description = inputs["vendor_description"]
    vendor_role = inputs["vendor_role"]
    organization_role = inputs["organization_role"]
    contract_summary = inputs.get("contract_summary") or {}
    dimensions = list(inputs.get("assessment_dimensions") or VALID_ASSESSMENT_DIMENSIONS)
    sub_processors = inputs.get("sub_processors") or []
    deployer_modification_note = inputs.get("deployer_modification_note")
    reviewed_by = inputs.get("reviewed_by")

    independence_required = inputs.get("independence_check_required")
    if independence_required is None:
        independence_required = vendor_role in INDEPENDENCE_REQUIRED_ROLES

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True

    warnings: list[str] = []
    citations: list[str] = list(_base_citations())

    # Role reconciliation.
    role_reconciliation, role_warnings, role_citations = _build_role_reconciliation(
        organization_role, vendor_role, deployer_modification_note
    )
    warnings.extend(role_warnings)
    for c in role_citations:
        if c not in citations:
            citations.append(c)

    # Contract-summary sanity check.
    if not contract_summary:
        warnings.append(
            "contract_summary is empty; mechanical status inference across contractual-obligations, "
            "data-governance, and incident-response dimensions is not possible. Supply the contract summary "
            "or accept practitioner-assessment placeholders."
        )

    # Per-dimension assessment matrix.
    assessment_matrix: list[dict[str, Any]] = []
    for dim in dimensions:
        assessment_matrix.append(_assess_dimension(dim, contract_summary))

    # Independence assessment.
    independence_assessment: dict[str, Any] | None = None
    if independence_required:
        independence_assessment = _independence_assessment(vendor_role)
        if "NYC LL144 Final Rule, Section 5-300" not in citations:
            citations.append("NYC LL144 Final Rule, Section 5-300")

    # Supply chain graph.
    supply_chain_graph: dict[str, Any] | None = None
    if sub_processors:
        supply_chain_graph = _build_supply_chain_graph(
            organization_role, vendor_description, sub_processors
        )

    # Vendor-description echo (defensive copy of key fields).
    vendor_description_echo = {
        "vendor_name": vendor_description.get("vendor_name"),
        "vendor_type": vendor_description.get("vendor_type"),
        "jurisdiction_of_establishment": vendor_description.get("jurisdiction_of_establishment"),
        "products_services": list(vendor_description.get("products_services") or []),
        "ai_systems_they_supply": list(vendor_description.get("ai_systems_they_supply") or []),
    }

    # Consistency warnings.
    if vendor_description.get("vendor_type") and vendor_description["vendor_type"] != vendor_role:
        warnings.append(
            f"vendor_description.vendor_type ({vendor_description['vendor_type']!r}) differs from "
            f"vendor_role ({vendor_role!r}); reconcile before audit use."
        )

    # Aggregate per-dimension warnings at the register level for visibility.
    for row in assessment_matrix:
        for w in row["warnings"]:
            warnings.append(f"[{row['name']}] {w}")

    # Summary.
    status_counts: dict[str, int] = dict.fromkeys(VALID_ASSESSMENT_STATUSES, 0)
    for row in assessment_matrix:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    summary = {
        "dimensions_assessed": len(assessment_matrix),
        "status_counts": status_counts,
        "independence_check_required": bool(independence_required),
        "sub_processor_count": len(sub_processors),
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "iso42001,eu-ai-act",
        "vendor_description_echo": vendor_description_echo,
        "role_reconciliation": role_reconciliation,
        "assessment_matrix": assessment_matrix,
        "citations": citations,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": reviewed_by,
    }
    if independence_assessment is not None:
        output["independence_assessment"] = independence_assessment
    if supply_chain_graph is not None:
        output["supply_chain_graph"] = supply_chain_graph

    if enrich:
        mappings, enrich_warnings = _crosswalk_enrich()
        output["cross_framework_citations"] = mappings
        warnings.extend(enrich_warnings)

    return output


def render_markdown(assessment: dict[str, Any]) -> str:
    """Render a supplier-vendor assessment as a Markdown document."""
    required = (
        "timestamp",
        "agent_signature",
        "vendor_description_echo",
        "role_reconciliation",
        "assessment_matrix",
        "citations",
        "warnings",
        "summary",
    )
    missing = [k for k in required if k not in assessment]
    if missing:
        raise ValueError(f"assessment missing required fields: {missing}")

    vde = assessment["vendor_description_echo"]
    rr = assessment["role_reconciliation"]
    summary = assessment["summary"]

    lines = [
        "# Supplier and Vendor Assessment",
        "",
        f"**Generated at (UTC):** {assessment['timestamp']}",
        f"**Generated by:** {assessment['agent_signature']}",
        f"**Framework:** {assessment.get('framework', 'iso42001,eu-ai-act')}",
    ]
    if assessment.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {assessment['reviewed_by']}")

    lines.extend(
        [
            "",
            "## Vendor overview",
            "",
            f"- Vendor name: {vde.get('vendor_name') or ''}",
            f"- Vendor type: {vde.get('vendor_type') or ''}",
            f"- Jurisdiction of establishment: {vde.get('jurisdiction_of_establishment') or ''}",
            f"- Products and services: {', '.join(vde.get('products_services') or []) or 'none listed'}",
            f"- AI systems supplied: {', '.join(vde.get('ai_systems_they_supply') or []) or 'none listed'}",
            "",
            "## Role reconciliation",
            "",
            f"- Organization role: {rr.get('organization_role')}",
            f"- Vendor role: {rr.get('vendor_role')}",
        ]
    )
    if rr.get("deployer_modification_note"):
        lines.append(f"- Deployer modification note: {rr['deployer_modification_note']}")
    if rr.get("notes"):
        lines.append("")
        lines.append("**Reconciliation notes:**")
        lines.append("")
        for note in rr["notes"]:
            lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Dimensions assessed: {summary['dimensions_assessed']}",
            "- Status counts: "
            + ", ".join(f"{k}={v}" for k, v in summary["status_counts"].items()),
            f"- Independence check required: {summary['independence_check_required']}",
            f"- Sub-processor count: {summary['sub_processor_count']}",
            "",
            "## Applicable Citations",
            "",
        ]
    )
    for c in assessment["citations"]:
        lines.append(f"- {c}")

    lines.extend(
        [
            "",
            "## Assessment matrix",
            "",
            "| Dimension | Status | Evidence refs | Warning count |",
            "|---|---|---|---|",
        ]
    )
    for row in assessment["assessment_matrix"]:
        ev = ", ".join(row.get("evidence_refs") or []) or ""
        wcount = len(row.get("warnings") or [])
        lines.append(
            f"| {row['name']} | {row['status']} | {ev} | {wcount} |"
        )

    if assessment.get("independence_assessment"):
        ia = assessment["independence_assessment"]
        lines.extend(
            [
                "",
                "## Independence check",
                "",
                f"- Status: {ia['status']}",
                f"- Required by: {', '.join(ia.get('required_by') or [])}",
                "",
                "**Criteria:**",
                "",
            ]
        )
        for c in ia.get("criteria") or []:
            lines.append(f"- {c}")

    if assessment.get("supply_chain_graph"):
        scg = assessment["supply_chain_graph"]
        lines.extend(
            [
                "",
                "## Supply chain",
                "",
                f"- Organization role: {scg['organization']['role']}",
                f"- Tier 1 vendor: {scg['tier_1_vendor'].get('vendor_name')} "
                f"({scg['tier_1_vendor'].get('vendor_type')})",
                "",
                "**Tier 2 sub-processors:**",
                "",
            ]
        )
        for sp in scg["tier_2_sub_processors"]:
            lines.append(
                f"- {sp.get('vendor_name') or '(unnamed)'} "
                f"[{sp.get('vendor_type') or 'unspecified'}]: {sp.get('tier_2_assessment')}"
            )

    if assessment.get("cross_framework_citations"):
        lines.extend(["", "## Cross-framework citations", ""])
        for m in assessment["cross_framework_citations"]:
            lines.append(
                f"- {m.get('source_framework')} {m.get('source_ref')} -> "
                f"{m.get('target_framework')} {m.get('target_ref')} "
                f"({m.get('relationship')}, {m.get('confidence')})"
            )

    if assessment.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in assessment["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(assessment: dict[str, Any]) -> str:
    """Render the assessment matrix as CSV.

    Columns: dimension, status, evidence_refs, warnings_count, warnings.
    One row per assessment_matrix entry.
    """
    if "assessment_matrix" not in assessment:
        raise ValueError("assessment missing 'assessment_matrix' field")
    header = "dimension,status,evidence_refs,warnings_count,warnings"
    lines = [header]
    for row in assessment["assessment_matrix"]:
        fields = [
            _csv_escape(str(row.get("name", ""))),
            _csv_escape(str(row.get("status", ""))),
            _csv_escape("; ".join(row.get("evidence_refs") or [])),
            _csv_escape(str(len(row.get("warnings") or []))),
            _csv_escape(" | ".join(row.get("warnings") or [])),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
