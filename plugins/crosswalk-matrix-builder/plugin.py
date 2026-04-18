"""crosswalk-matrix-builder plugin.

Machine-readable cross-framework coverage, gap, and matrix queries.

Data lives under ``data/`` as YAML (one file per source-target pair, or per
state jurisdiction). Every mapping row carries a deterministic id, a
relationship label, a confidence rating, and at least one citation.

The plugin does not invent relationships. All output is sourced from the
YAML data files. Invariants are enforced at load time; content-level gaps
(empty result sets) surface as warnings.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import yaml


AGENT_SIGNATURE = "crosswalk-matrix-builder/0.1.0"

REQUIRED_INPUT_FIELDS = ("query_type",)

VALID_QUERY_TYPES = ("coverage", "gaps", "matrix", "pair")

VALID_RELATIONSHIPS = (
    "exact-match",
    "partial-match",
    "satisfies",
    "partial-satisfaction",
    "complementary",
    "statutory-presumption",
    "no-mapping",
)

VALID_CONFIDENCE = ("high", "medium", "low")

SYMMETRIC_RELATIONSHIPS = ("exact-match", "partial-match", "complementary")

DATA_DIR = Path(__file__).parent / "data"

EM_DASH = "\u2014"


# ---------------------------------------------------------------------------
# Data loading and invariant enforcement
# ---------------------------------------------------------------------------


def _iter_mapping_files(data_dir: Path) -> Iterable[Path]:
    for path in sorted(data_dir.glob("*.yaml")):
        if path.name == "frameworks.yaml":
            continue
        yield path


def _scan_for_em_dash(value, context: str, file_name: str) -> None:
    if isinstance(value, str):
        if EM_DASH in value:
            raise ValueError(
                f"Em-dash (U+2014) found in {file_name} at {context}. "
                "Use a hyphen instead."
            )
    elif isinstance(value, dict):
        for k, v in value.items():
            _scan_for_em_dash(v, f"{context}.{k}", file_name)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _scan_for_em_dash(item, f"{context}[{i}]", file_name)


def load_crosswalk_data(data_dir: Path | None = None) -> dict:
    """Load all YAML files in the data directory and return a merged dict.

    Enforces every invariant declared in SCHEMA.md. Raises ValueError on the
    first violation with a specific message naming the file and entry id.
    """
    dir_path = data_dir if data_dir is not None else DATA_DIR
    frameworks_path = dir_path / "frameworks.yaml"
    if not frameworks_path.exists():
        raise ValueError(f"frameworks.yaml not found in {dir_path}")

    frameworks_doc = yaml.safe_load(frameworks_path.read_text(encoding="utf-8")) or {}
    frameworks = frameworks_doc.get("frameworks") or []
    _scan_for_em_dash(frameworks, "frameworks", "frameworks.yaml")
    framework_ids = {fw["id"] for fw in frameworks}

    all_mappings: list[dict] = []
    seen_ids: dict[str, str] = {}

    for path in _iter_mapping_files(dir_path):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        mappings = doc.get("mappings") or []
        _scan_for_em_dash(mappings, "mappings", path.name)
        for entry in mappings:
            _validate_entry(entry, path.name, framework_ids, seen_ids)
            entry["_source_file"] = path.name
            all_mappings.append(entry)
            seen_ids[entry["id"]] = path.name

    return {"frameworks": frameworks, "mappings": all_mappings}


def _validate_entry(
    entry: dict,
    file_name: str,
    framework_ids: set,
    seen_ids: dict[str, str],
) -> None:
    entry_id = entry.get("id")
    if not entry_id:
        raise ValueError(f"Mapping entry missing 'id' in {file_name}")

    # Invariant 2: globally unique id.
    if entry_id in seen_ids:
        raise ValueError(
            f"Duplicate mapping id '{entry_id}' in {file_name}; "
            f"first seen in {seen_ids[entry_id]}"
        )

    source_fw = entry.get("source_framework")
    target_fw = entry.get("target_framework")

    # Invariant 1: frameworks exist.
    if source_fw not in framework_ids:
        raise ValueError(
            f"Unknown source_framework '{source_fw}' in {file_name} "
            f"entry '{entry_id}'"
        )
    if target_fw not in framework_ids:
        raise ValueError(
            f"Unknown target_framework '{target_fw}' in {file_name} "
            f"entry '{entry_id}'"
        )

    relationship = entry.get("relationship")
    if relationship not in VALID_RELATIONSHIPS:
        raise ValueError(
            f"Invalid relationship '{relationship}' in {file_name} "
            f"entry '{entry_id}'"
        )

    confidence = entry.get("confidence")
    if confidence not in VALID_CONFIDENCE:
        raise ValueError(
            f"Invalid confidence '{confidence}' in {file_name} "
            f"entry '{entry_id}'"
        )

    citation_sources = entry.get("citation_sources") or []

    # Invariant 6: at least one citation.
    if not citation_sources:
        raise ValueError(
            f"Mapping entry '{entry_id}' in {file_name} has no "
            "citation_sources."
        )

    # Invariant 3: low confidence needs a citation source or a
    # practitioner-inference note.
    if confidence == "low":
        has_citation = any(
            (src.get("publication") or "").strip() for src in citation_sources
        )
        notes_field = (entry.get("notes") or "").lower()
        has_inference_note = "practitioner-inference" in notes_field
        if not (has_citation or has_inference_note):
            raise ValueError(
                f"Low-confidence entry '{entry_id}' in {file_name} needs a "
                "citation source or explicit 'practitioner-inference' note."
            )

    # Invariant 4: bidirectional: true only for symmetric relationships.
    if entry.get("bidirectional") is True and relationship not in SYMMETRIC_RELATIONSHIPS:
        raise ValueError(
            f"Entry '{entry_id}' in {file_name}: bidirectional=true is "
            f"not permitted for relationship '{relationship}'. Only "
            f"{SYMMETRIC_RELATIONSHIPS} may be bidirectional."
        )

    # Invariant 5: no-mapping needs non-empty notes.
    if relationship == "no-mapping":
        notes = (entry.get("notes") or "").strip()
        if not notes:
            raise ValueError(
                f"no-mapping entry '{entry_id}' in {file_name} requires a "
                "non-empty 'notes' field explaining the gap."
            )


# ---------------------------------------------------------------------------
# Public query entry point
# ---------------------------------------------------------------------------


def build_matrix(inputs: dict) -> dict:
    """Canonical entry point. Dispatches on ``query_type``."""
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")

    for field in REQUIRED_INPUT_FIELDS:
        if field not in inputs:
            raise ValueError(f"Missing required input field: '{field}'")

    query_type = inputs["query_type"]
    if query_type not in VALID_QUERY_TYPES:
        raise ValueError(
            f"Invalid query_type '{query_type}'. Must be one of "
            f"{VALID_QUERY_TYPES}."
        )

    data = load_crosswalk_data()
    framework_ids = {fw["id"] for fw in data["frameworks"]}
    framework_index = {fw["id"]: fw for fw in data["frameworks"]}

    source_framework = inputs.get("source_framework")
    target_framework = inputs.get("target_framework")
    source_ref = inputs.get("source_ref")
    target_ref = inputs.get("target_ref")
    confidence_min = inputs.get("confidence_min")
    relationship_filter = inputs.get("relationship_filter")

    if source_framework is not None and source_framework not in framework_ids:
        raise ValueError(
            f"Unknown source_framework '{source_framework}'. Must be one of "
            f"{sorted(framework_ids)}."
        )
    if target_framework is not None and target_framework not in framework_ids:
        raise ValueError(
            f"Unknown target_framework '{target_framework}'. Must be one of "
            f"{sorted(framework_ids)}."
        )
    if confidence_min is not None and confidence_min not in VALID_CONFIDENCE:
        raise ValueError(
            f"Invalid confidence_min '{confidence_min}'. Must be one of "
            f"{VALID_CONFIDENCE}."
        )
    if relationship_filter is not None:
        if not isinstance(relationship_filter, (list, tuple)):
            raise ValueError("relationship_filter must be a list or tuple")
        for rel in relationship_filter:
            if rel not in VALID_RELATIONSHIPS:
                raise ValueError(
                    f"Invalid relationship_filter value '{rel}'. Must be "
                    f"one of {VALID_RELATIONSHIPS}."
                )

    # Per-query required fields.
    if query_type == "coverage":
        if not source_framework:
            raise ValueError("query_type='coverage' requires 'source_framework'.")
        if not source_ref:
            raise ValueError("query_type='coverage' requires 'source_ref'.")
    elif query_type == "gaps":
        if not source_framework:
            raise ValueError("query_type='gaps' requires 'source_framework'.")
        if not target_framework:
            raise ValueError("query_type='gaps' requires 'target_framework'.")
    elif query_type == "matrix":
        if not source_framework:
            raise ValueError("query_type='matrix' requires 'source_framework'.")
    elif query_type == "pair":
        if not source_framework:
            raise ValueError("query_type='pair' requires 'source_framework'.")
        if not target_framework:
            raise ValueError("query_type='pair' requires 'target_framework'.")

    all_mappings = data["mappings"]
    warnings: list[str] = []

    if query_type == "coverage":
        result_mappings = [
            m
            for m in all_mappings
            if m["source_framework"] == source_framework
            and m["source_ref"] == source_ref
        ]
    elif query_type == "gaps":
        result_mappings = [
            m
            for m in all_mappings
            if m["source_framework"] == source_framework
            and m["target_framework"] == target_framework
            and m["relationship"] == "no-mapping"
        ]
    elif query_type == "matrix":
        result_mappings = [
            m for m in all_mappings if m["source_framework"] == source_framework
        ]
        if target_framework:
            result_mappings = [
                m for m in result_mappings if m["target_framework"] == target_framework
            ]
    else:  # pair
        result_mappings = [
            m
            for m in all_mappings
            if m["source_framework"] == source_framework
            and m["target_framework"] == target_framework
        ]
        if source_ref is not None:
            result_mappings = [m for m in result_mappings if m["source_ref"] == source_ref]
        if target_ref is not None:
            result_mappings = [m for m in result_mappings if m["target_ref"] == target_ref]

    # Apply confidence filter.
    if confidence_min is not None:
        min_idx = VALID_CONFIDENCE.index(confidence_min)
        # VALID_CONFIDENCE is ordered high, medium, low; "at least X" means
        # index <= min_idx.
        result_mappings = [
            m
            for m in result_mappings
            if VALID_CONFIDENCE.index(m["confidence"]) <= min_idx
        ]

    # Apply relationship filter.
    if relationship_filter is not None:
        allowed = set(relationship_filter)
        result_mappings = [m for m in result_mappings if m["relationship"] in allowed]

    # Empty result warning.
    if not result_mappings:
        warnings.append(
            f"Query returned zero mappings for query_type='{query_type}'. "
            "Verify source/target framework ids and refs."
        )

    # Sanitize internal-only fields for serialization.
    clean_results = [_strip_internal(m) for m in result_mappings]

    summary = _build_summary(query_type, clean_results)

    citations = _collect_citations(
        query_type, source_framework, target_framework, framework_index, clean_results
    )

    output: dict = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent_signature": AGENT_SIGNATURE,
        "query": {
            "query_type": query_type,
            "source_framework": source_framework,
            "source_ref": source_ref,
            "target_framework": target_framework,
            "target_ref": target_ref,
            "confidence_min": confidence_min,
            "relationship_filter": list(relationship_filter) if relationship_filter else None,
        },
        "citations": citations,
        "warnings": warnings,
        "summary": summary,
    }

    if "reviewed_by" in inputs and inputs["reviewed_by"]:
        output["reviewed_by"] = inputs["reviewed_by"]

    # Attach results under a per-query key plus a stable "mappings" alias used
    # by renderers.
    if query_type == "coverage":
        output["matches"] = clean_results
    elif query_type == "gaps":
        output["gaps"] = clean_results
    elif query_type == "matrix":
        output["matrix"] = clean_results
    else:
        output["pair"] = clean_results

    output["mappings"] = clean_results

    return output


def _strip_internal(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if not k.startswith("_")}


def _build_summary(query_type: str, mappings: list[dict]) -> dict:
    summary: dict = {"total": len(mappings)}

    if query_type == "coverage":
        per_target: dict[str, int] = {}
        for m in mappings:
            per_target[m["target_framework"]] = per_target.get(m["target_framework"], 0) + 1
        summary["by_target_framework"] = per_target
    elif query_type == "gaps":
        summary["gap_count"] = len(mappings)
    else:
        by_relationship: dict[str, int] = {}
        by_confidence: dict[str, int] = {}
        for m in mappings:
            rel = m["relationship"]
            conf = m["confidence"]
            by_relationship[rel] = by_relationship.get(rel, 0) + 1
            by_confidence[conf] = by_confidence.get(conf, 0) + 1
        summary["by_relationship"] = by_relationship
        summary["by_confidence"] = by_confidence

    return summary


def _collect_citations(
    query_type: str,
    source_framework: str | None,
    target_framework: str | None,
    framework_index: dict,
    mappings: list[dict],
) -> list[str]:
    citations: list[str] = []
    seen: set[str] = set()

    for fw_id in (source_framework, target_framework):
        if not fw_id:
            continue
        fw = framework_index.get(fw_id)
        if not fw:
            continue
        label = fw.get("citation_format") or fw.get("name")
        if label and label not in seen:
            citations.append(label)
            seen.add(label)

    # Matrix without target: include every distinct target framework seen
    # in the results.
    if query_type == "matrix" and target_framework is None:
        for m in mappings:
            fw = framework_index.get(m["target_framework"])
            if fw:
                label = fw.get("citation_format") or fw.get("name")
                if label and label not in seen:
                    citations.append(label)
                    seen.add(label)

    return citations


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_markdown(result: dict) -> str:
    lines: list[str] = []
    query = result.get("query", {})
    lines.append("# Crosswalk matrix result")
    lines.append("")
    lines.append(f"- Timestamp: {result.get('timestamp', '')}")
    lines.append(f"- Agent: {result.get('agent_signature', '')}")
    if result.get("reviewed_by"):
        lines.append(f"- Reviewed by: {result['reviewed_by']}")
    lines.append("")

    lines.append("## Query")
    lines.append("")
    lines.append(f"- query_type: {query.get('query_type')}")
    if query.get("source_framework"):
        lines.append(f"- source_framework: {query.get('source_framework')}")
    if query.get("source_ref"):
        lines.append(f"- source_ref: {query.get('source_ref')}")
    if query.get("target_framework"):
        lines.append(f"- target_framework: {query.get('target_framework')}")
    if query.get("target_ref"):
        lines.append(f"- target_ref: {query.get('target_ref')}")
    if query.get("confidence_min"):
        lines.append(f"- confidence_min: {query.get('confidence_min')}")
    if query.get("relationship_filter"):
        lines.append(f"- relationship_filter: {query.get('relationship_filter')}")
    lines.append("")

    # Summary section.
    summary = result.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- total: {summary.get('total', 0)}")
    if "gap_count" in summary:
        lines.append(f"- gap_count: {summary['gap_count']}")
    if "by_target_framework" in summary:
        lines.append("- by_target_framework:")
        for k, v in sorted(summary["by_target_framework"].items()):
            lines.append(f"  - {k}: {v}")
    if "by_relationship" in summary:
        lines.append("- by_relationship:")
        for k, v in sorted(summary["by_relationship"].items()):
            lines.append(f"  - {k}: {v}")
    if "by_confidence" in summary:
        lines.append("- by_confidence:")
        for k, v in sorted(summary["by_confidence"].items()):
            lines.append(f"  - {k}: {v}")
    lines.append("")

    # Citations.
    citations = result.get("citations", [])
    if citations:
        lines.append("## Citations")
        lines.append("")
        for c in citations:
            lines.append(f"- {c}")
        lines.append("")

    # Warnings.
    warnings = result.get("warnings", [])
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Mappings table.
    mappings = result.get("mappings", [])
    lines.append("## Mappings")
    lines.append("")
    if not mappings:
        lines.append("(no mapping rows)")
        lines.append("")
    else:
        lines.append(
            "| id | source | source_ref | target | target_ref | relationship | confidence |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for m in mappings:
            lines.append(
                "| {id} | {sf} | {sr} | {tf} | {tr} | {rel} | {conf} |".format(
                    id=m.get("id", ""),
                    sf=m.get("source_framework", ""),
                    sr=m.get("source_ref", ""),
                    tf=m.get("target_framework", ""),
                    tr=m.get("target_ref", ""),
                    rel=m.get("relationship", ""),
                    conf=m.get("confidence", ""),
                )
            )
        lines.append("")

    # Gap call-outs.
    gaps = [m for m in mappings if m.get("relationship") == "no-mapping"]
    if gaps:
        lines.append("## Gaps")
        lines.append("")
        for g in gaps:
            lines.append(
                f"- {g.get('id')}: {g.get('source_framework')} "
                f"{g.get('source_ref')} has no equivalent in "
                f"{g.get('target_framework')}."
            )
            notes = g.get("notes") or ""
            if notes:
                lines.append(f"  - notes: {notes}")
        lines.append("")

    return "\n".join(lines)


def render_csv(result: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    header = [
        "id",
        "source_framework",
        "source_ref",
        "source_title",
        "target_framework",
        "target_ref",
        "target_title",
        "relationship",
        "confidence",
        "citation_source",
        "notes",
    ]
    writer.writerow(header)
    for m in result.get("mappings", []):
        citations = m.get("citation_sources") or []
        citation_labels = "; ".join(
            (c.get("publication") or "").strip() for c in citations if c.get("publication")
        )
        writer.writerow(
            [
                m.get("id", ""),
                m.get("source_framework", ""),
                m.get("source_ref", ""),
                m.get("source_title", ""),
                m.get("target_framework", ""),
                m.get("target_ref", ""),
                m.get("target_title", ""),
                m.get("relationship", ""),
                m.get("confidence", ""),
                citation_labels,
                m.get("notes", "") or "",
            ]
        )
    return buf.getvalue()
