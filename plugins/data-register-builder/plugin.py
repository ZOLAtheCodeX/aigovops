"""
AIGovOps: AI Data Register Builder Plugin

Generates data-register rows for AI system training, validation, testing,
and inference datasets. Serves ISO/IEC 42001:2023 Annex A category A.7
(Data for AI systems: A.7.2 through A.7.6) and EU AI Act Article 10
(Data and data governance).

Design stance: the plugin does NOT discover datasets, compute quality
metrics, or analyze provenance. Dataset identification and profiling
live in the data engineering stack. The plugin validates supplied
dataset entries against the framework requirements, enriches with
computed fields (retention expiry, framework citations), flags
compliance gaps per-row as warnings, and emits a structured data
register.

Status: Phase 3 implementation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

AGENT_SIGNATURE = "data-register-builder/0.1.0"

VALID_PURPOSE_STAGES = (
    "training",
    "validation",
    "testing",
    "inference",
    "reference",
    "benchmark",
)

VALID_SOURCES = (
    "internal",
    "public-open",
    "public-license",
    "third-party-contract",
    "scraped",
    "synthesized",
    "other",
)

VALID_FRAMEWORKS = ("iso42001", "eu-ai-act", "dual")

# Core quality-check dimensions per Article 10(3) and A.7.4.
QUALITY_DIMENSIONS = (
    "accuracy",
    "completeness",
    "consistency",
    "currency",
    "validity",
)

REQUIRED_INPUT_FIELDS = ("data_inventory",)
REQUIRED_DATASET_FIELDS = ("id", "name", "purpose_stage", "source")


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    inventory = inputs["data_inventory"]
    if not isinstance(inventory, list):
        raise ValueError("data_inventory must be a list")

    for i, d in enumerate(inventory):
        if not isinstance(d, dict):
            raise ValueError(f"data_inventory[{i}] must be a dict")
        missing_fields = [f for f in REQUIRED_DATASET_FIELDS if f not in d]
        if missing_fields:
            raise ValueError(
                f"data_inventory[{i}] missing required fields {sorted(missing_fields)}"
            )
        if d["purpose_stage"] not in VALID_PURPOSE_STAGES:
            raise ValueError(
                f"data_inventory[{i}] purpose_stage must be one of {VALID_PURPOSE_STAGES}; "
                f"got {d['purpose_stage']!r}"
            )
        if d["source"] not in VALID_SOURCES:
            raise ValueError(
                f"data_inventory[{i}] source must be one of {VALID_SOURCES}; "
                f"got {d['source']!r}"
            )

    framework = inputs.get("framework", "iso42001")
    if framework not in VALID_FRAMEWORKS:
        raise ValueError(f"framework must be one of {VALID_FRAMEWORKS}; got {framework!r}")

    retention_policy = inputs.get("retention_policy")
    if retention_policy is not None and not isinstance(retention_policy, dict):
        raise ValueError("retention_policy must be a dict mapping data_category to retention_days")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _iso_citations(purpose_stage: str) -> list[str]:
    base = ["ISO/IEC 42001:2023, Annex A, Control A.7.2"]
    if purpose_stage in ("training", "validation", "testing"):
        base.extend([
            "ISO/IEC 42001:2023, Annex A, Control A.7.3",
            "ISO/IEC 42001:2023, Annex A, Control A.7.4",
            "ISO/IEC 42001:2023, Annex A, Control A.7.5",
            "ISO/IEC 42001:2023, Annex A, Control A.7.6",
        ])
    return base


def _eu_citations(purpose_stage: str, includes_bias_check: bool) -> list[str]:
    base = ["EU AI Act, Article 10, Paragraph 1", "EU AI Act, Article 10, Paragraph 2"]
    if purpose_stage in ("training", "validation", "testing"):
        base.append("EU AI Act, Article 10, Paragraph 3")
        base.append("EU AI Act, Article 10, Paragraph 4")
    if includes_bias_check:
        base.append("EU AI Act, Article 10, Paragraph 5")
    return base


def _compute_retention_expiry(
    collection_date: str | None, retention_days: int | None
) -> str | None:
    if not collection_date or retention_days is None:
        return None
    try:
        dt = datetime.fromisoformat(collection_date.replace("Z", "+00:00"))
    except ValueError:
        return None
    expiry = dt + timedelta(days=int(retention_days))
    return expiry.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_high_risk_system(system_refs: list[str], high_risk_systems: set[str]) -> bool:
    return any(ref in high_risk_systems for ref in system_refs)


def _quality_check_warnings(
    dataset: dict[str, Any], purpose_stage: str, framework: str
) -> list[str]:
    """Quality-check dimensions per A.7.4 and Article 10(3)."""
    warnings: list[str] = []
    quality = dataset.get("quality_checks") or {}
    if purpose_stage in ("training", "validation", "testing"):
        missing = [d for d in QUALITY_DIMENSIONS if d not in quality]
        if missing:
            warnings.append(
                f"quality_checks missing dimensions {sorted(missing)}; "
                "Article 10(3) and A.7.4 require training/validation/testing data to satisfy accuracy, "
                "completeness, consistency, currency, and validity checks."
            )
        for dim, result in quality.items():
            if isinstance(result, dict) and result.get("status") == "fail":
                warnings.append(
                    f"quality dimension {dim!r} marked as failed: {result.get('detail', 'no detail')}; "
                    "Article 10(3) requires data to be relevant, sufficiently representative, and free of errors."
                )
    return warnings


def _enrich_dataset(
    dataset: dict[str, Any],
    framework: str,
    high_risk_systems: set[str],
    retention_policy: dict[str, Any],
    role_matrix_lookup: dict[str, str],
    index: int,
) -> dict[str, Any]:
    warnings: list[str] = []
    purpose_stage = dataset["purpose_stage"]
    source = dataset["source"]
    system_refs = dataset.get("system_refs") or []
    protected_attrs = dataset.get("protected_attributes") or []
    includes_bias_check = bool(dataset.get("bias_assessment"))

    # Article 10(5) bias examination for high-risk systems training data.
    touches_high_risk = _is_high_risk_system(system_refs, high_risk_systems)
    if framework in ("eu-ai-act", "dual") and touches_high_risk and purpose_stage == "training":
        if not includes_bias_check:
            warnings.append(
                "high-risk system training data without a bias_assessment; "
                "Article 10(5) requires bias examination for high-risk AI systems."
            )

    # Scraped + training + high-risk = Article 10(2) data-governance concern.
    if source == "scraped" and purpose_stage == "training" and touches_high_risk:
        warnings.append(
            "training data acquired by scraping for a high-risk AI system; "
            "Article 10(2) requires documented data-governance practices examining source, origin, "
            "and intended purpose. Document acquisition legality and purpose-compatibility."
        )

    # Acquisition method required by A.7.3 for training/validation/testing.
    if purpose_stage in ("training", "validation", "testing") and not dataset.get("acquisition_method"):
        warnings.append(
            "acquisition_method not set; A.7.3 requires documenting how data was acquired "
            "(purchased, licensed, collected, synthesized, and so on)."
        )

    # Provenance chain required by A.7.5.
    if not dataset.get("provenance_chain"):
        warnings.append(
            "provenance_chain not set; A.7.5 requires data provenance tracking. "
            "Provide at minimum the originating source and any transformation steps."
        )

    # Data preparation steps by A.7.6.
    if purpose_stage in ("training", "validation", "testing") and not dataset.get("data_preparation_steps"):
        warnings.append(
            "data_preparation_steps not set; A.7.6 requires documenting preparation "
            "(cleaning, normalization, feature engineering, labeling)."
        )

    # Representativeness per Article 10(3) and A.7.4.
    if purpose_stage == "training" and framework in ("eu-ai-act", "dual"):
        if not dataset.get("representativeness_assessment"):
            warnings.append(
                "representativeness_assessment not set for training data; "
                "Article 10(3) requires training data to be sufficiently representative."
            )

    # Quality check dimensions.
    warnings.extend(_quality_check_warnings(dataset, purpose_stage, framework))

    # Retention policy lookup: use dataset data_category -> retention_policy map.
    data_category = dataset.get("data_category", "default")
    retention_days = retention_policy.get(data_category) or retention_policy.get("default")
    retention_expiry = _compute_retention_expiry(dataset.get("collection_date"), retention_days)

    # Owner lookup from role matrix if not set.
    owner_role = dataset.get("owner_role")
    if not owner_role and role_matrix_lookup:
        owner_role = role_matrix_lookup.get("data_governance")
    if not owner_role:
        warnings.append(
            "owner_role not set; every dataset must have an assigned data owner "
            "per role matrix and Clause 5.3."
        )

    # Protected-attribute notice for fairness concerns.
    if protected_attrs and purpose_stage == "training" and not includes_bias_check:
        warnings.append(
            f"training data contains protected attributes {list(protected_attrs)} but no "
            "bias_assessment is documented; fairness analysis required."
        )

    # Framework citations.
    if framework == "iso42001":
        citations = _iso_citations(purpose_stage)
    elif framework == "eu-ai-act":
        citations = _eu_citations(purpose_stage, includes_bias_check)
    else:
        citations = _eu_citations(purpose_stage, includes_bias_check) + _iso_citations(purpose_stage)

    return {
        "id": dataset["id"],
        "name": dataset["name"],
        "system_refs": system_refs,
        "purpose_stage": purpose_stage,
        "source": source,
        "acquisition_method": dataset.get("acquisition_method"),
        "provenance_chain": dataset.get("provenance_chain") or [],
        "quality_checks": dataset.get("quality_checks") or {},
        "representativeness_assessment": dataset.get("representativeness_assessment"),
        "bias_assessment": dataset.get("bias_assessment"),
        "data_preparation_steps": dataset.get("data_preparation_steps") or [],
        "protected_attributes": protected_attrs,
        "data_category": data_category,
        "collection_date": dataset.get("collection_date"),
        "retention_days": retention_days,
        "retention_expiry_date": retention_expiry,
        "owner_role": owner_role,
        "citations": citations,
        "warnings": warnings,
    }


def generate_data_register(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a structured AI data register covering training, validation,
    testing, and operational datasets.

    Args:
        inputs: Dict with:
            data_inventory: list of dataset dicts. Each requires id, name,
                            purpose_stage, source. Optional: system_refs,
                            acquisition_method, provenance_chain,
                            quality_checks, representativeness_assessment,
                            bias_assessment, data_preparation_steps,
                            protected_attributes, data_category,
                            collection_date, owner_role.
            ai_system_inventory: optional list for high-risk determination.
                                 Each entry with system_ref and risk_tier.
            retention_policy: dict mapping data_category to retention_days,
                              with optional 'default' key.
            role_matrix_lookup: dict mapping role categories to role names
                                (for owner default).
            framework: 'iso42001' (default), 'eu-ai-act', 'dual'.
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, framework, citations, rows,
        summary, warnings, reviewed_by.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    framework = inputs.get("framework", "iso42001")
    retention_policy = inputs.get("retention_policy") or {}
    role_matrix_lookup = inputs.get("role_matrix_lookup") or {}
    ai_system_inventory = inputs.get("ai_system_inventory") or []
    high_risk_systems = {
        s.get("system_ref") for s in ai_system_inventory
        if isinstance(s, dict) and s.get("risk_tier") == "high"
    }

    rows: list[dict[str, Any]] = []
    purpose_counts: dict[str, int] = dict.fromkeys(VALID_PURPOSE_STAGES, 0)
    source_counts: dict[str, int] = dict.fromkeys(VALID_SOURCES, 0)

    for i, dataset in enumerate(inputs["data_inventory"]):
        row = _enrich_dataset(
            dataset, framework, high_risk_systems, retention_policy, role_matrix_lookup, i + 1
        )
        rows.append(row)
        purpose_counts[row["purpose_stage"]] = purpose_counts.get(row["purpose_stage"], 0) + 1
        source_counts[row["source"]] = source_counts.get(row["source"], 0) + 1

    register_warnings: list[str] = []
    if not rows:
        register_warnings.append(
            "No datasets provided. An empty data register is acceptable only when no AI systems "
            "are in scope; document the detection-scope if so."
        )

    # Top-level citations.
    top_citations: list[str] = []
    if framework in ("iso42001", "dual"):
        top_citations.extend([
            "ISO/IEC 42001:2023, Annex A, Control A.7.2",
            "ISO/IEC 42001:2023, Annex A, Control A.7.3",
            "ISO/IEC 42001:2023, Annex A, Control A.7.4",
            "ISO/IEC 42001:2023, Annex A, Control A.7.5",
            "ISO/IEC 42001:2023, Annex A, Control A.7.6",
        ])
    if framework in ("eu-ai-act", "dual"):
        top_citations.append("EU AI Act, Article 10")

    summary = {
        "total_datasets": len(rows),
        "purpose_counts": purpose_counts,
        "source_counts": source_counts,
        "datasets_with_warnings": sum(1 for r in rows if r["warnings"]),
        "datasets_touching_high_risk": sum(1 for r in rows if _is_high_risk_system(r["system_refs"], high_risk_systems)),
    }

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": framework,
        "citations": top_citations,
        "rows": rows,
        "summary": summary,
        "warnings": register_warnings,
        "reviewed_by": inputs.get("reviewed_by"),
    }


def render_markdown(register: dict[str, Any]) -> str:
    required = ("timestamp", "agent_signature", "citations", "rows", "summary")
    missing = [k for k in required if k not in register]
    if missing:
        raise ValueError(f"register missing required fields: {missing}")

    lines = [
        "# AI Data Register",
        "",
        f"**Generated at (UTC):** {register['timestamp']}",
        f"**Generated by:** {register['agent_signature']}",
        f"**Framework:** {register.get('framework', 'iso42001')}",
    ]
    if register.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {register['reviewed_by']}")
    summary = register["summary"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Total datasets: {summary['total_datasets']}",
        f"- Purpose counts: " + ", ".join(f"{k}={v}" for k, v in summary["purpose_counts"].items() if v),
        f"- Source counts: " + ", ".join(f"{k}={v}" for k, v in summary["source_counts"].items() if v),
        f"- Datasets with warnings: {summary['datasets_with_warnings']}",
        f"- Datasets touching high-risk systems: {summary['datasets_touching_high_risk']}",
        "",
        "## Applicable Citations",
        "",
    ])
    for c in register["citations"]:
        lines.append(f"- {c}")

    lines.extend(["", "## Datasets", ""])
    if not register["rows"]:
        lines.append("_No datasets recorded._")
    else:
        lines.append("| ID | Name | Stage | Source | Owner | Expiry |")
        lines.append("|---|---|---|---|---|---|")
        for row in register["rows"]:
            lines.append(
                f"| {row['id']} | {row['name']} | {row['purpose_stage']} | {row['source']} | "
                f"{row.get('owner_role') or ''} | {row.get('retention_expiry_date') or ''} |"
            )

    row_warnings = [(r["id"], w) for r in register["rows"] for w in r["warnings"]]
    if row_warnings or register.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in register.get("warnings", []):
            lines.append(f"- (register) {w}")
        for rid, w in row_warnings:
            lines.append(f"- ({rid}) {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(register: dict[str, Any]) -> str:
    if "rows" not in register:
        raise ValueError("register missing 'rows' field")
    header = (
        "id,name,system_refs,purpose_stage,source,acquisition_method,"
        "data_category,collection_date,retention_days,retention_expiry,"
        "owner_role,protected_attributes,citations"
    )
    lines = [header]
    for r in register["rows"]:
        fields = [
            _csv_escape(str(r.get("id", ""))),
            _csv_escape(str(r.get("name", ""))),
            _csv_escape("; ".join(r.get("system_refs", []))),
            _csv_escape(str(r.get("purpose_stage", ""))),
            _csv_escape(str(r.get("source", ""))),
            _csv_escape(str(r.get("acquisition_method", "") or "")),
            _csv_escape(str(r.get("data_category", "") or "")),
            _csv_escape(str(r.get("collection_date", "") or "")),
            _csv_escape(str(r.get("retention_days", "") or "")),
            _csv_escape(str(r.get("retention_expiry_date", "") or "")),
            _csv_escape(str(r.get("owner_role", "") or "")),
            _csv_escape("; ".join(str(p) for p in r.get("protected_attributes", []))),
            _csv_escape("; ".join(r.get("citations", []))),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
