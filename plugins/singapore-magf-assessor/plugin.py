"""
AIGovOps: Singapore Model AI Governance Framework (MAGF) Assessor Plugin

Operationalizes the Singapore AI governance landscape:

1. Model AI Governance Framework, Second Edition (MAGF 2e, 2020). Non-binding
   guidance published jointly by the Infocomm Media Development Authority
   (IMDA) and the Personal Data Protection Commission (PDPC). Four pillars:
   Internal Governance Structures and Measures; Determining the Level of
   Human Involvement in AI-augmented Decision-Making; Operations Management;
   Stakeholder Interaction and Communication.
2. MAS FEAT Principles (2018). Fairness, Ethics, Accountability, and
   Transparency principles for the use of AI and Data Analytics (AIDA) in
   the Singapore financial services sector. Regulatory expectation for
   Monetary Authority of Singapore (MAS) regulated entities.
3. AI Verify (IMDA, launched 2022, updated 2024). Technical testing
   framework operationalizing MAGF through 11 ethics principles.
4. Veritas (MAS, 2019 through 2022). Open-source methodology for assessing
   FEAT compliance in financial AI, not produced by this plugin.

Design stance: the plugin takes a system description and organization type,
determines which Singapore instruments apply, and emits a pillar-by-pillar
structured assessment. It does not interpret MAS enforcement, does not
produce Veritas-style fairness metrics (that requires the Veritas toolkit),
and does not generate AI Verify technical test results.

Status: Phase 2 implementation. APAC influential-framework coverage per
docs/jurisdiction-scope.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "singapore-magf-assessor/0.1.0"

REQUIRED_INPUT_FIELDS = ("system_description", "organization_type")

VALID_ORG_TYPES = (
    "general",
    "financial-services",
    "healthcare",
    "government",
    "other",
)

VALID_HUMAN_INVOLVEMENT_TIERS = (
    "human-in-the-loop",
    "human-over-the-loop",
    "human-out-of-the-loop",
)

MAGF_PILLARS = (
    "internal-governance",
    "human-involvement",
    "operations-management",
    "stakeholder-communication",
)


# MAGF 2e pillar definitions. Citations anchor to the canonical published
# text: IMDA/PDPC Model AI Governance Framework, Second Edition, January 2020.
PILLAR_DEFINITIONS = {
    "internal-governance": {
        "name": "Internal Governance Structures and Measures",
        "description": (
            "Adapt existing or set up internal governance structures and measures "
            "to incorporate values, risks, and responsibilities relating to "
            "algorithmic decision-making. Covers clear roles and responsibilities, "
            "risk management and internal controls, and staff training."
        ),
        "citation": "Singapore MAGF 2e, Pillar Internal Governance Structures and Measures",
        "evidence_keys": (
            "role_assignments",
            "risk_controls",
            "staff_training",
        ),
    },
    "human-involvement": {
        "name": "Determining the Level of Human Involvement in AI-Augmented Decision-Making",
        "description": (
            "Identify an appropriate level of human involvement in decisions that "
            "use AI based on a risk matrix weighing probability and severity of "
            "harm. Three tiers are named: human-in-the-loop, human-over-the-loop, "
            "and human-out-of-the-loop."
        ),
        "citation": "Singapore MAGF 2e, Pillar Determining the Level of Human Involvement",
        "evidence_keys": (
            "human_involvement_tier",
            "risk_matrix",
            "escalation_process",
        ),
    },
    "operations-management": {
        "name": "Operations Management",
        "description": (
            "Manage the operational deployment of AI. Covers data accountability "
            "(lineage, quality, bias mitigation), algorithm selection and model "
            "robustness, periodic tuning and retraining, and explainability, "
            "reproducibility, and auditability of the deployed system."
        ),
        "citation": "Singapore MAGF 2e, Pillar Operations Management",
        "evidence_keys": (
            "data_lineage",
            "data_quality",
            "bias_mitigation",
            "model_robustness",
            "explainability",
            "reproducibility",
            "monitoring",
        ),
    },
    "stakeholder-communication": {
        "name": "Stakeholder Interaction and Communication",
        "description": (
            "Communicate with consumers and other stakeholders on the use of AI. "
            "Covers general disclosure of AI use, providing a mechanism for "
            "feedback and decision-review, and acceptable-use policies for "
            "stakeholders interacting with the system."
        ),
        "citation": "Singapore MAGF 2e, Pillar Stakeholder Interaction and Communication",
        "evidence_keys": (
            "disclosure_policy",
            "feedback_channel",
            "decision_review_process",
        ),
    },
}


# Human involvement tier expectations per MAGF 2e guidance.
HUMAN_INVOLVEMENT_NOTES = {
    "human-in-the-loop": (
        "Human retains full control; AI provides recommendations that a human "
        "reviews and acts on. Appropriate where probability and severity of harm "
        "are both high."
    ),
    "human-over-the-loop": (
        "Human monitors AI and can intervene at any point. Appropriate where one "
        "of probability or severity is high."
    ),
    "human-out-of-the-loop": (
        "AI acts autonomously without human intervention during operation. "
        "Appropriate only where probability and severity are both low."
    ),
}


# MAS FEAT Principles (2018). Four principles with MAS-published sub-criteria.
# Source: MAS, "Principles to Promote Fairness, Ethics, Accountability and
# Transparency (FEAT) in the Use of Artificial Intelligence and Data Analytics
# in Singapore's Financial Sector", 12 November 2018.
FEAT_PRINCIPLES = {
    "fairness": {
        "name": "Fairness",
        "description": (
            "Use of AIDA-driven decisions is justifiable, and individuals and "
            "groups are not systematically disadvantaged unless justified."
        ),
        "citation": "MAS FEAT Principles (2018), Principle Fairness",
        "sub_criteria": (
            "Justifiability: the data and models used are justifiable and regularly reviewed.",
            "Accuracy and bias: the AIDA-driven decisions are regularly reviewed so that models behave as designed and intended.",
            "Unintentional systematic disadvantage: individuals and groups are not systematically disadvantaged unless the decisions can be justified.",
        ),
        "evidence_key": "fairness_evidence",
    },
    "ethics": {
        "name": "Ethics",
        "description": (
            "AIDA-driven decisions are held to at least the same ethical "
            "standards as human-driven decisions."
        ),
        "citation": "MAS FEAT Principles (2018), Principle Ethics",
        "sub_criteria": (
            "Ethical standards: AIDA-driven decisions are held to at least the same ethical standards as human-driven decisions.",
            "Alignment with firm values: use of AIDA is aligned with the firm's ethical standards, values, and codes of conduct.",
            "Human-driven alternative: consideration is given to whether a human-driven decision would be more ethically appropriate.",
        ),
        "evidence_key": "ethics_evidence",
    },
    "accountability": {
        "name": "Accountability",
        "description": (
            "Use of AIDA in decision-making is approved by an appropriate "
            "internal authority, and firms are accountable to both internal "
            "and external stakeholders for AIDA-driven decisions."
        ),
        "citation": "MAS FEAT Principles (2018), Principle Accountability",
        "sub_criteria": (
            "Internal accountability: use of AIDA in decision-making is approved by an appropriate internal authority.",
            "External accountability: firms are accountable to external stakeholders, including for AIDA-driven decisions affecting them.",
            "Data subject rights: data subjects are provided channels to inquire about, submit appeals for, and request reviews of AIDA-driven decisions.",
            "Verification: AIDA-driven decisions are verifiable and explainable.",
        ),
        "evidence_key": "accountability_evidence",
    },
    "transparency": {
        "name": "Transparency",
        "description": (
            "To increase public confidence, firms using AIDA proactively "
            "disclose use, provide clear explanations, and communicate in a way "
            "that is easy to understand."
        ),
        "citation": "MAS FEAT Principles (2018), Principle Transparency",
        "sub_criteria": (
            "Proactive disclosure: use of AIDA is proactively disclosed to data subjects as part of general communication.",
            "Clear explanation: upon request, data subjects receive clear explanations of what data is used and how it affects them.",
            "Ease of understanding: communication is easy to understand.",
        ),
        "evidence_key": "transparency_evidence",
    },
}


# AI Verify (IMDA 2024) 11 ethics principles mapped to MAGF pillars.
# This is a static lookup table derived from the AI Verify Foundation
# framework documentation.
AI_VERIFY_PRINCIPLE_TO_PILLAR = {
    "accountability": ("internal-governance",),
    "data-governance": ("operations-management",),
    "human-agency-oversight": ("human-involvement",),
    "inclusive-growth": ("stakeholder-communication",),
    "privacy": ("operations-management",),
    "reproducibility": ("operations-management",),
    "robustness": ("operations-management",),
    "safety": ("operations-management",),
    "security": ("operations-management",),
    "transparency": ("stakeholder-communication",),
    "fairness": ("operations-management", "stakeholder-communication"),
}

AI_VERIFY_CITATION_PREFIX = "AI Verify (IMDA 2024), Principle"


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")

    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    org_type = inputs["organization_type"]
    if org_type not in VALID_ORG_TYPES:
        raise ValueError(
            f"organization_type must be one of {VALID_ORG_TYPES}; got {org_type!r}"
        )

    system_description = inputs["system_description"]
    if not isinstance(system_description, dict):
        raise ValueError("system_description must be a dict")

    tier = system_description.get("human_involvement_tier")
    if tier is not None and tier not in VALID_HUMAN_INVOLVEMENT_TIERS:
        raise ValueError(
            f"system_description.human_involvement_tier must be one of "
            f"{VALID_HUMAN_INVOLVEMENT_TIERS}; got {tier!r}"
        )


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _assess_evidence_presence(
    provided: dict[str, Any], keys: tuple[str, ...]
) -> tuple[list[str], list[str]]:
    """Return (present_refs, missing_keys) for the evidence keys."""
    present: list[str] = []
    missing: list[str] = []
    for k in keys:
        value = provided.get(k)
        if value:
            present.append(k)
        else:
            missing.append(k)
    return present, missing


def _assess_status(present_count: int, total: int) -> str:
    if present_count == 0:
        return "not-addressed"
    if present_count < total:
        return "partial"
    return "addressed"


def _evaluate_pillar(
    pillar_id: str, system_description: dict[str, Any]
) -> dict[str, Any]:
    definition = PILLAR_DEFINITIONS[pillar_id]
    evidence_inputs = system_description.get("pillar_evidence", {}).get(pillar_id, {})
    if not isinstance(evidence_inputs, dict):
        evidence_inputs = {}

    present, missing = _assess_evidence_presence(
        evidence_inputs, definition["evidence_keys"]
    )
    status = _assess_status(len(present), len(definition["evidence_keys"]))

    warnings: list[str] = []
    if not present:
        warnings.append(
            f"Pillar {pillar_id!r}: no evidence_refs provided for any of "
            f"{list(definition['evidence_keys'])}."
        )
    elif missing:
        warnings.append(
            f"Pillar {pillar_id!r}: incomplete documentation; missing evidence for "
            f"{missing}."
        )

    return {
        "id": pillar_id,
        "name": definition["name"],
        "description": definition["description"],
        "assessment_status": status,
        "evidence_refs": present,
        "warnings": warnings,
        "citation": definition["citation"],
    }


def _evaluate_feat_principle(
    principle_id: str, system_description: dict[str, Any]
) -> dict[str, Any]:
    definition = FEAT_PRINCIPLES[principle_id]
    feat_inputs = system_description.get("feat_evidence", {})
    if not isinstance(feat_inputs, dict):
        feat_inputs = {}
    evidence = feat_inputs.get(principle_id)

    warnings: list[str] = []
    evidence_refs: list[str] = []
    if isinstance(evidence, list) and evidence:
        evidence_refs = [str(e) for e in evidence]
        status = "addressed"
    elif isinstance(evidence, dict) and evidence:
        evidence_refs = sorted(evidence.keys())
        status = "addressed" if len(evidence_refs) >= len(definition["sub_criteria"]) else "partial"
        if status == "partial":
            warnings.append(
                f"FEAT principle {principle_id!r}: partial evidence; "
                f"{len(evidence_refs)} of {len(definition['sub_criteria'])} sub-criteria documented."
            )
    elif isinstance(evidence, str) and evidence:
        evidence_refs = [evidence]
        status = "partial"
        warnings.append(
            f"FEAT principle {principle_id!r}: single-string evidence; "
            "auditor expects per-sub-criterion documentation."
        )
    else:
        status = "not-addressed"
        warnings.append(
            f"FEAT principle {principle_id!r}: no evidence provided under "
            f"feat_evidence.{principle_id}."
        )

    return {
        "id": principle_id,
        "name": definition["name"],
        "description": definition["description"],
        "sub_criteria": list(definition["sub_criteria"]),
        "assessment_status": status,
        "evidence_refs": evidence_refs,
        "warnings": warnings,
        "citation": definition["citation"],
    }


def _derive_human_involvement_tier(
    system_description: dict[str, Any], warnings: list[str]
) -> dict[str, Any]:
    tier = system_description.get("human_involvement_tier")
    if tier is None:
        warnings.append(
            "human_involvement_tier absent. MAGF 2e Pillar 2 requires an "
            "explicit tier selection based on the probability-severity risk "
            "matrix. Defaulting to 'human-in-the-loop' for conservative "
            "posture; reviewer must confirm."
        )
        tier = "human-in-the-loop"

    return {
        "tier": tier,
        "note": HUMAN_INVOLVEMENT_NOTES[tier],
        "citation": "Singapore MAGF 2e, Pillar Determining the Level of Human Involvement",
    }


def _build_ai_verify_coverage() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for principle, pillars in AI_VERIFY_PRINCIPLE_TO_PILLAR.items():
        rows.append({
            "ai_verify_principle": principle,
            "magf_pillars": list(pillars),
            "citation": f"{AI_VERIFY_CITATION_PREFIX} {principle}",
        })
    return rows


def generate_magf_assessment(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Produce a Singapore MAGF assessment, extended with FEAT when applicable.

    Args:
        inputs: Dict with:
            system_description: dict. Optional keys: system_name,
                human_involvement_tier (one of VALID_HUMAN_INVOLVEMENT_TIERS),
                pillar_evidence (dict keyed by pillar id, each value a dict
                keyed by evidence_keys), feat_evidence (dict keyed by FEAT
                principle id for financial-services organizations).
            organization_type: one of VALID_ORG_TYPES.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, framework, organization_type,
        applicable_frameworks, pillars, human_involvement_tier,
        ai_verify_principles_coverage, feat_principles (only if
        financial-services), citations, warnings, reviewed_by, summary.

    Raises:
        ValueError: if required inputs are missing or invalid.
    """
    _validate(inputs)

    organization_type = inputs["organization_type"]
    system_description = inputs["system_description"]
    reviewed_by = inputs.get("reviewed_by")

    warnings: list[str] = []

    applicable_frameworks = ["magf"]
    if organization_type == "financial-services":
        applicable_frameworks.append("feat")

    pillars = [_evaluate_pillar(pid, system_description) for pid in MAGF_PILLARS]

    human_involvement = _derive_human_involvement_tier(system_description, warnings)

    ai_verify_coverage = _build_ai_verify_coverage()

    feat_principles: list[dict[str, Any]] | None = None
    if "feat" in applicable_frameworks:
        feat_principles = [
            _evaluate_feat_principle(pid, system_description)
            for pid in ("fairness", "ethics", "accountability", "transparency")
        ]
        for p in feat_principles:
            warnings.extend(p["warnings"])

    for p in pillars:
        warnings.extend(p["warnings"])

    citations: list[str] = [
        "Singapore MAGF 2e, Section Overview",
    ]
    for p in pillars:
        citations.append(p["citation"])
    citations.append(human_involvement["citation"])
    if feat_principles is not None:
        for fp in feat_principles:
            citations.append(fp["citation"])
    for row in ai_verify_coverage:
        citations.append(row["citation"])

    pillars_addressed = sum(1 for p in pillars if p["assessment_status"] == "addressed")
    summary: dict[str, Any] = {
        "organization_type": organization_type,
        "applicable_frameworks": list(applicable_frameworks),
        "pillar_count": len(pillars),
        "pillars_addressed": pillars_addressed,
        "pillars_partial": sum(1 for p in pillars if p["assessment_status"] == "partial"),
        "pillars_not_addressed": sum(1 for p in pillars if p["assessment_status"] == "not-addressed"),
        "human_involvement_tier": human_involvement["tier"],
        "warning_count": len(warnings),
    }
    if feat_principles is not None:
        summary["feat_principle_count"] = len(feat_principles)
        summary["feat_principles_addressed"] = sum(
            1 for fp in feat_principles if fp["assessment_status"] == "addressed"
        )

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "singapore-magf",
        "organization_type": organization_type,
        "applicable_frameworks": applicable_frameworks,
        "system_description_echo": system_description,
        "pillars": pillars,
        "human_involvement_tier": human_involvement,
        "ai_verify_principles_coverage": ai_verify_coverage,
        "citations": citations,
        "warnings": warnings,
        "reviewed_by": reviewed_by,
        "summary": summary,
    }
    if feat_principles is not None:
        output["feat_principles"] = feat_principles
    return output


def render_markdown(assessment: dict[str, Any]) -> str:
    required = (
        "timestamp",
        "organization_type",
        "applicable_frameworks",
        "pillars",
        "human_involvement_tier",
        "ai_verify_principles_coverage",
        "citations",
    )
    missing = [k for k in required if k not in assessment]
    if missing:
        raise ValueError(f"assessment missing required fields: {missing}")

    sys_desc = assessment.get("system_description_echo", {})
    system_name = sys_desc.get("system_name", "unknown system")

    lines = [
        f"# Singapore MAGF Assessment: {system_name}",
        "",
        f"**Generated at (UTC):** {assessment['timestamp']}",
        f"**Generated by:** {assessment['agent_signature']}",
        f"**Organization type:** {assessment['organization_type']}",
        f"**Applicable frameworks:** {', '.join(assessment['applicable_frameworks'])}",
        f"**Human involvement tier:** {assessment['human_involvement_tier']['tier']}",
    ]
    if assessment.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {assessment['reviewed_by']}")

    lines.extend(["", "## MAGF Pillars", ""])
    for p in assessment["pillars"]:
        lines.append(f"### {p['name']}")
        lines.append("")
        lines.append(f"- Assessment status: {p['assessment_status']}")
        lines.append(f"- Evidence refs: {', '.join(p['evidence_refs']) or 'none'}")
        lines.append(f"- Citation: {p['citation']}")
        lines.append(f"- Description: {p['description']}")
        lines.append("")

    lines.extend(["## Human Involvement Tier", ""])
    hi = assessment["human_involvement_tier"]
    lines.append(f"- Tier: {hi['tier']}")
    lines.append(f"- Note: {hi['note']}")
    lines.append(f"- Citation: {hi['citation']}")
    lines.append("")

    if "feat_principles" in assessment:
        lines.extend(["## MAS FEAT Principles (Financial Services)", ""])
        for fp in assessment["feat_principles"]:
            lines.append(f"### {fp['name']}")
            lines.append("")
            lines.append(f"- Assessment status: {fp['assessment_status']}")
            lines.append(f"- Evidence refs: {', '.join(fp['evidence_refs']) or 'none'}")
            lines.append(f"- Citation: {fp['citation']}")
            lines.append(f"- Description: {fp['description']}")
            lines.append("- Sub-criteria:")
            for sc in fp["sub_criteria"]:
                lines.append(f"  - {sc}")
            lines.append("")

    lines.extend(["## AI Verify Principle Coverage", ""])
    for row in assessment["ai_verify_principles_coverage"]:
        lines.append(
            f"- {row['ai_verify_principle']}: MAGF pillars "
            f"{', '.join(row['magf_pillars'])} ({row['citation']})"
        )
    lines.append("")

    lines.extend(["## Citations", ""])
    for c in assessment["citations"]:
        lines.append(f"- {c}")
    lines.append("")

    if assessment.get("warnings"):
        lines.extend(["## Warnings", ""])
        for w in assessment["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    summary = assessment.get("summary", {})
    if summary:
        lines.extend(["## Summary", ""])
        for k, v in summary.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    return "\n".join(lines)


def render_csv(assessment: dict[str, Any]) -> str:
    """One row per pillar, plus one row per FEAT principle if applicable."""
    required = ("pillars",)
    missing = [k for k in required if k not in assessment]
    if missing:
        raise ValueError(f"assessment missing required fields: {missing}")

    header = "kind,id,name,assessment_status,evidence_refs,citation"
    rows = [header]
    for p in assessment["pillars"]:
        rows.append(
            _csv_row([
                "magf-pillar",
                p["id"],
                p["name"],
                p["assessment_status"],
                ";".join(p["evidence_refs"]),
                p["citation"],
            ])
        )
    for fp in assessment.get("feat_principles", []) or []:
        rows.append(
            _csv_row([
                "feat-principle",
                fp["id"],
                fp["name"],
                fp["assessment_status"],
                ";".join(fp["evidence_refs"]),
                fp["citation"],
            ])
        )
    return "\n".join(rows) + "\n"


def _csv_row(fields: list[str]) -> str:
    out = []
    for f in fields:
        s = str(f)
        if "," in s or '"' in s or "\n" in s:
            s = '"' + s.replace('"', '""') + '"'
        out.append(s)
    return ",".join(out)
