"""
AIGovOps: Colorado AI Act (SB 205) Compliance Plugin

Operationalizes Colorado Senate Bill 24-205, "Concerning Consumer Protections
in Interactions with Artificial Intelligence Systems", signed 17 May 2024,
effective 1 February 2026. Codified at Colorado Revised Statutes, Title 6,
Article 1, Part 17 (sections 6-1-1701 through 6-1-1707).

The plugin takes an actor description (developer, deployer, or both) and a
set of consequential-decision domains, and produces a structured compliance
record enumerating the obligations that apply, the documentation required,
the consumer notice and appeal posture, and the citation map.

Design stance: the plugin does NOT decide whether a given AI system is
high-risk in contested cases. High-risk turns on "a substantial factor in
making a consequential decision" (section 6-1-1701(9)), which is a
fact-dependent determination. The plugin treats any non-empty set of
declared consequential-decision domains as high-risk for rule-application
purposes and surfaces a warning when the input does not include an explicit
decision-influence declaration. Legal determination of substantial-factor
status remains with qualified Colorado counsel.

Status: Phase 2 implementation. USA state-level secondary jurisdiction
coverage per docs/jurisdiction-scope.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "colorado-ai-act-compliance/0.1.0"

REQUIRED_INPUT_FIELDS = (
    "actor_role",
    "system_description",
    "consequential_decision_domains",
)

VALID_ACTOR_ROLES = ("developer", "deployer", "both")

CONSEQUENTIAL_DOMAINS = (
    "education",
    "employment",
    "financial-lending",
    "essential-government",
    "health-care",
    "housing",
    "insurance",
    "legal-services",
)

# Domain citation map: each domain anchors to section 6-1-1701(3) which
# enumerates the consequential-decision categories.
DOMAIN_CITATION = "Colorado SB 205, Section 6-1-1701(3)"


# Developer obligations under section 6-1-1702.
DEVELOPER_OBLIGATIONS = (
    {
        "id": "dev-reasonable-care",
        "title": "Duty of reasonable care to protect consumers from algorithmic discrimination",
        "citation": "Colorado SB 205, Section 6-1-1702(1)",
    },
    {
        "id": "dev-deployer-documentation",
        "title": "Provide deployer documentation covering intended uses, known harmful or inappropriate uses, training data summary, evaluation methods, and risk mitigations",
        "citation": "Colorado SB 205, Section 6-1-1702(2)",
    },
    {
        "id": "dev-public-statement",
        "title": "Publish and maintain a public statement summarizing the types of high-risk AI systems developed and how known or reasonably foreseeable risks of algorithmic discrimination are managed",
        "citation": "Colorado SB 205, Section 6-1-1702(3)",
    },
    {
        "id": "dev-ag-and-deployer-disclosure",
        "title": "Disclose known or reasonably foreseeable algorithmic discrimination to the Attorney General and known deployers within 90 days of discovery",
        "citation": "Colorado SB 205, Section 6-1-1702(4)",
    },
    {
        "id": "dev-post-deployment-monitoring",
        "title": "Maintain post-deployment monitoring support for deployers, including information sufficient for impact assessment updates",
        "citation": "Colorado SB 205, Section 6-1-1702(2)(b)",
    },
    {
        "id": "dev-data-governance",
        "title": "Document data governance measures covering training datasets, including suitability, representativeness, and mitigation of foreseeable discriminatory outcomes",
        "citation": "Colorado SB 205, Section 6-1-1702(2)(c)",
    },
)


# Deployer obligations under section 6-1-1703.
DEPLOYER_OBLIGATIONS = (
    {
        "id": "dep-reasonable-care",
        "title": "Duty of reasonable care to protect consumers from algorithmic discrimination arising from the intended and contracted uses of the high-risk AI system",
        "citation": "Colorado SB 205, Section 6-1-1703(1)",
    },
    {
        "id": "dep-risk-management-policy",
        "title": "Implement a risk management policy and program governing deployment of the high-risk AI system; reviewed and updated at least annually",
        "citation": "Colorado SB 205, Section 6-1-1703(2)",
    },
    {
        "id": "dep-impact-assessment",
        "title": "Complete an impact assessment before deployment and annually thereafter, and within 90 days of any intentional and substantial modification",
        "citation": "Colorado SB 205, Section 6-1-1703(3)",
    },
    {
        "id": "dep-consumer-notice",
        "title": "Provide consumer notice of use of a high-risk AI system to make, or be a substantial factor in making, a consequential decision concerning the consumer",
        "citation": "Colorado SB 205, Section 6-1-1703(4)(a)",
    },
    {
        "id": "dep-adverse-decision-explanation",
        "title": "When a consequential decision is adverse to the consumer, disclose the principal reason(s), the degree to which the AI system contributed, and the source categories of personal data used",
        "citation": "Colorado SB 205, Section 6-1-1703(4)(b)",
    },
    {
        "id": "dep-consumer-appeal",
        "title": "Provide the consumer an opportunity to correct incorrect personal data and an opportunity to appeal an adverse consequential decision for human review, where technically feasible",
        "citation": "Colorado SB 205, Section 6-1-1703(4)(c)",
    },
    {
        "id": "dep-public-statement",
        "title": "Publish and maintain a public statement summarizing deployed high-risk AI systems and how risks of algorithmic discrimination are managed",
        "citation": "Colorado SB 205, Section 6-1-1703(5)",
    },
    {
        "id": "dep-ag-disclosure",
        "title": "Disclose discovered algorithmic discrimination to the Attorney General within 90 days of discovery",
        "citation": "Colorado SB 205, Section 6-1-1703(6)",
    },
)


# Impact assessment required content under section 6-1-1703(3).
IMPACT_ASSESSMENT_CONTENT = (
    {"id": "ia-purpose-use", "title": "Statement of the purpose, intended use cases, deployment context, and benefits of the system"},
    {"id": "ia-risk-analysis", "title": "Analysis of known or reasonably foreseeable risks of algorithmic discrimination and mitigation steps"},
    {"id": "ia-data-description", "title": "Description of the categories of data processed as inputs and the outputs produced"},
    {"id": "ia-customization", "title": "If applicable, a description of the system's customization for the deployer's use"},
    {"id": "ia-metrics", "title": "Metrics used to evaluate system performance and limitations"},
    {"id": "ia-transparency", "title": "Description of transparency measures, including whether and how consumers are notified"},
    {"id": "ia-oversight", "title": "Description of post-deployment monitoring and user safeguards, including human oversight processes"},
)

IMPACT_ASSESSMENT_CITATION = "Colorado SB 205, Section 6-1-1703(3)"


# Developer documentation checklist under section 6-1-1702(2).
DEVELOPER_DOCUMENTATION_CONTENT = (
    {"id": "doc-intended-uses", "title": "Intended uses of the high-risk AI system"},
    {"id": "doc-known-harms", "title": "Known or reasonably foreseeable harmful or inappropriate uses"},
    {"id": "doc-training-data-summary", "title": "Summary of the types of data used to train the system"},
    {"id": "doc-data-governance", "title": "Data governance measures applied to training data, including suitability and representativeness"},
    {"id": "doc-evaluation", "title": "Methods used to evaluate performance and mitigate algorithmic discrimination risks"},
    {"id": "doc-limitations", "title": "Known limitations of the system"},
    {"id": "doc-post-deployment", "title": "Post-deployment monitoring information sufficient for deployer impact assessments"},
)

DEVELOPER_DOC_CITATION = "Colorado SB 205, Section 6-1-1702(2)"


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    actor_role = inputs["actor_role"]
    if actor_role not in VALID_ACTOR_ROLES:
        raise ValueError(
            f"actor_role must be one of {VALID_ACTOR_ROLES}; got {actor_role!r}"
        )

    system_description = inputs["system_description"]
    if not isinstance(system_description, dict):
        raise ValueError("system_description must be a dict")

    domains = inputs["consequential_decision_domains"]
    if not isinstance(domains, list):
        raise ValueError("consequential_decision_domains must be a list")
    for d in domains:
        if d not in CONSEQUENTIAL_DOMAINS:
            raise ValueError(
                f"consequential_decision_domains entry {d!r} is not in {CONSEQUENTIAL_DOMAINS}"
            )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _derive_is_high_risk(
    actor_role: str,
    domains: list[str],
    system_description: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Derive high-risk classification and warnings.

    High-risk requires two conditions under section 6-1-1701(9):
    (a) deployment in a consequential-decision domain, and
    (b) the system makes, or is a substantial factor in making, the decision.

    The plugin treats any non-empty domain list as meeting (a). Condition
    (b) is a legal determination; the plugin accepts an explicit
    `substantial_factor` boolean in system_description and defaults to True
    when domains are declared, with a warning if the caller did not state it.
    """
    warnings: list[str] = []
    if not domains:
        return False, warnings

    substantial_factor = system_description.get("substantial_factor")
    if substantial_factor is None:
        warnings.append(
            "system_description.substantial_factor not declared; defaulting to True because "
            "consequential-decision domains are declared. Confirm with counsel per section 6-1-1701(9)."
        )
        return True, warnings

    if not isinstance(substantial_factor, bool):
        warnings.append(
            "system_description.substantial_factor present but not a boolean; treating as True."
        )
        return True, warnings

    if substantial_factor is False:
        warnings.append(
            "system_description.substantial_factor is False despite consequential-decision domains "
            "being declared. Plugin classifies as non-high-risk on that basis; confirm with counsel."
        )
        return False, warnings

    return True, warnings


def _collect_obligations(
    obligations: tuple[dict[str, str], ...],
    applicable: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "id": o["id"],
            "title": o["title"],
            "citation": o["citation"],
            "applicability": "applies" if applicable else "not-applicable",
        }
        for o in obligations
    ]


def _evaluate_documentation_checklist(
    items: tuple[dict[str, str], ...],
    provided_keys: set[str],
    citation: str,
) -> list[dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "present": item["id"] in provided_keys,
            "citation": citation,
        }
        for item in items
    ]


def generate_compliance_record(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Produce a Colorado SB 205 compliance record for the declared actor role.

    Args:
        inputs: Dict with:
            actor_role: one of 'developer', 'deployer', 'both'.
            system_description: dict with at minimum system_name; optional
                substantial_factor bool; optional impact_assessment_inputs
                dict keyed by impact assessment item ids; optional
                developer_documentation dict keyed by developer doc item
                ids; optional consumer_notice_content dict with notice
                details.
            consequential_decision_domains: list from CONSEQUENTIAL_DOMAINS.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, framework, actor_role,
        consequential_decision_domains, is_high_risk, developer_obligations,
        deployer_obligations, impact_assessment_required,
        consumer_notice_required, consumer_appeal_required,
        documentation_checklist, warnings, citations, reviewed_by, summary.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    actor_role = inputs["actor_role"]
    system_description = inputs["system_description"]
    domains = list(inputs["consequential_decision_domains"])
    reviewed_by = inputs.get("reviewed_by")

    is_high_risk, hr_warnings = _derive_is_high_risk(actor_role, domains, system_description)
    warnings: list[str] = list(hr_warnings)

    developer_applies = actor_role in ("developer", "both") and is_high_risk
    deployer_applies = actor_role in ("deployer", "both") and is_high_risk

    developer_obligations = _collect_obligations(DEVELOPER_OBLIGATIONS, developer_applies)
    deployer_obligations = _collect_obligations(DEPLOYER_OBLIGATIONS, deployer_applies)

    impact_assessment_required = deployer_applies
    consumer_notice_required = deployer_applies
    consumer_appeal_required = deployer_applies

    documentation_checklist: list[dict[str, Any]] = []

    if developer_applies:
        provided_dev_docs = set((system_description.get("developer_documentation") or {}).keys())
        dev_checklist = _evaluate_documentation_checklist(
            DEVELOPER_DOCUMENTATION_CONTENT, provided_dev_docs, DEVELOPER_DOC_CITATION
        )
        documentation_checklist.extend(dev_checklist)
        missing_dev = [x for x in dev_checklist if not x["present"]]
        if missing_dev:
            warnings.append(
                f"Developer documentation incomplete: {len(missing_dev)} of "
                f"{len(dev_checklist)} required items missing under section 6-1-1702(2)."
            )

    if deployer_applies:
        provided_ia = set((system_description.get("impact_assessment_inputs") or {}).keys())
        ia_checklist = _evaluate_documentation_checklist(
            IMPACT_ASSESSMENT_CONTENT, provided_ia, IMPACT_ASSESSMENT_CITATION
        )
        documentation_checklist.extend(ia_checklist)
        missing_ia = [x for x in ia_checklist if not x["present"]]
        if missing_ia:
            warnings.append(
                f"Impact assessment content incomplete: {len(missing_ia)} of "
                f"{len(ia_checklist)} required items missing under section 6-1-1703(3)."
            )

        consumer_notice_content = system_description.get("consumer_notice_content")
        if not consumer_notice_content:
            warnings.append(
                "consumer_notice_content absent. Deployer must provide consumer notice at or before "
                "use of the system per section 6-1-1703(4)(a)."
            )

    if not is_high_risk:
        warnings.append(
            "System classified as non-high-risk. Confirm that no consequential decisions are made, "
            "and that the system is not a substantial factor in any consequential decision, per "
            "section 6-1-1701(9). Re-run classification if scope changes."
        )

    citations: list[str] = [
        "Colorado SB 205, Section 6-1-1701 (definitions)",
        "Colorado SB 205, Section 6-1-1706 (attorney general enforcement)",
    ]
    if domains:
        citations.append(DOMAIN_CITATION)
    if developer_applies:
        citations.append("Colorado SB 205, Section 6-1-1702")
    if deployer_applies:
        citations.append("Colorado SB 205, Section 6-1-1703")
    # Safe harbor citation is always surfaced; section 6-1-1706(4) provides
    # an affirmative defense when a recognized framework is substantively
    # followed.
    citations.append("Colorado SB 205, Section 6-1-1706(4) (affirmative defense: recognized AI risk management framework)")

    summary = {
        "actor_role": actor_role,
        "is_high_risk": is_high_risk,
        "domain_count": len(domains),
        "developer_obligation_count": sum(1 for o in developer_obligations if o["applicability"] == "applies"),
        "deployer_obligation_count": sum(1 for o in deployer_obligations if o["applicability"] == "applies"),
        "impact_assessment_required": impact_assessment_required,
        "consumer_notice_required": consumer_notice_required,
        "consumer_appeal_required": consumer_appeal_required,
        "documentation_item_count": len(documentation_checklist),
        "documentation_items_missing": sum(1 for d in documentation_checklist if not d["present"]),
        "warning_count": len(warnings),
    }

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "colorado-sb-205",
        "actor_role": actor_role,
        "system_description_echo": system_description,
        "consequential_decision_domains": domains,
        "is_high_risk": is_high_risk,
        "developer_obligations": developer_obligations,
        "deployer_obligations": deployer_obligations,
        "impact_assessment_required": impact_assessment_required,
        "consumer_notice_required": consumer_notice_required,
        "consumer_appeal_required": consumer_appeal_required,
        "documentation_checklist": documentation_checklist,
        "warnings": warnings,
        "citations": citations,
        "reviewed_by": reviewed_by,
        "summary": summary,
    }


def render_markdown(record: dict[str, Any]) -> str:
    required = (
        "timestamp",
        "actor_role",
        "is_high_risk",
        "developer_obligations",
        "deployer_obligations",
        "citations",
    )
    missing = [k for k in required if k not in record]
    if missing:
        raise ValueError(f"record missing required fields: {missing}")

    sys_desc = record.get("system_description_echo", {})
    system_name = sys_desc.get("system_name", "unknown system")

    lines = [
        f"# Colorado SB 205 Compliance Record: {system_name}",
        "",
        f"**Generated at (UTC):** {record['timestamp']}",
        f"**Generated by:** {record['agent_signature']}",
        f"**Actor role:** {record['actor_role']}",
        f"**High-risk classification:** {record['is_high_risk']}",
        f"**Consequential-decision domains:** {', '.join(record['consequential_decision_domains']) or 'none declared'}",
        f"**Impact assessment required:** {record['impact_assessment_required']}",
        f"**Consumer notice required:** {record['consumer_notice_required']}",
        f"**Consumer appeal required:** {record['consumer_appeal_required']}",
    ]
    if record.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {record['reviewed_by']}")

    lines.extend(["", "## Applicable Citations", ""])
    for c in record["citations"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Developer obligations", ""])
    if not record["developer_obligations"]:
        lines.append("_No developer obligations enumerated._")
    for o in record["developer_obligations"]:
        lines.append(f"- [{o['applicability']}] {o['title']} ({o['citation']})")

    lines.extend(["", "## Deployer obligations", ""])
    if not record["deployer_obligations"]:
        lines.append("_No deployer obligations enumerated._")
    for o in record["deployer_obligations"]:
        lines.append(f"- [{o['applicability']}] {o['title']} ({o['citation']})")

    checklist = record.get("documentation_checklist") or []
    if checklist:
        lines.extend(["", "## Documentation checklist", ""])
        for item in checklist:
            status = "present" if item["present"] else "missing"
            lines.append(f"- [{status}] {item['title']} ({item['citation']})")

    if record.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in record["warnings"]:
            lines.append(f"- {w}")

    summary = record.get("summary", {})
    if summary:
        lines.extend(["", "## Summary", ""])
        for k in (
            "actor_role",
            "is_high_risk",
            "domain_count",
            "developer_obligation_count",
            "deployer_obligation_count",
            "impact_assessment_required",
            "consumer_notice_required",
            "consumer_appeal_required",
            "documentation_item_count",
            "documentation_items_missing",
            "warning_count",
        ):
            if k in summary:
                lines.append(f"- {k}: {summary[k]}")

    lines.append("")
    return "\n".join(lines)


def render_csv(record: dict[str, Any]) -> str:
    """Emit obligations as CSV rows: one row per obligation (developer + deployer)."""
    required = ("developer_obligations", "deployer_obligations")
    missing = [k for k in required if k not in record]
    if missing:
        raise ValueError(f"record missing required fields: {missing}")

    header = "obligation_id,actor_role,title,applicability,citation"
    rows = [header]
    for o in record["developer_obligations"]:
        rows.append(
            _csv_row([o["id"], "developer", o["title"], o["applicability"], o["citation"]])
        )
    for o in record["deployer_obligations"]:
        rows.append(
            _csv_row([o["id"], "deployer", o["title"], o["applicability"], o["citation"]])
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
