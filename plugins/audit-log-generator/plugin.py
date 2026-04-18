"""
AIGovOps: Audit Log Generator Plugin

Generates ISO/IEC 42001:2023-compliant audit log entries from AI system
governance events.

This plugin operationalizes the audit-log-entry artifact type defined in the
iso42001 skill's operationalization map. It produces records suitable for the
`audit-log-entry` artifact described in skills/iso42001/SKILL.md, specifically
in service of Clause 9.1 (monitoring and performance evaluation) and Annex A
controls A.6.2.3 (design and development documentation), A.6.2.8 (AI system
log recording), and A.3.2 (AI roles).

Status: Phase 3 minimum-viable implementation. Validates inputs, performs
rule-based Annex A control mapping, emits structured audit log entries in
both dict (for JSON serialization) and Markdown forms. Rendering to PDF or
DOCX is deferred to a separate rendering plugin per the Output Standards
section of the iso42001 skill.

Version 0.2.0 adds optional cross-framework enrichment via the sibling
crosswalk-matrix-builder plugin: every primary ISO 42001 citation (main-body
clause or Annex A control) is resolved against the crosswalk data and the
resulting cross-framework equivalents are attached to each event under
`cross_framework_citations`. This lets a single audit-log entry serve ISO,
NIST AI RMF, and EU AI Act reviewers simultaneously.

Style: all citations use the STYLE.md format. No em-dashes, no emojis, no
hedging language in output strings.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "audit-log-generator/0.2.0"

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily inside
# the enrichment helper so basic audit-log calls (enrich_with_crosswalk=False)
# pay no import cost and are unaffected by crosswalk load failures.
_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"
if str(_CROSSWALK_DIR) not in sys.path:
    sys.path.insert(0, str(_CROSSWALK_DIR))

# Framework ids accepted in crosswalk_target_frameworks. Sourced from
# plugins/crosswalk-matrix-builder/data/frameworks.yaml.
VALID_CROSSWALK_TARGET_FRAMEWORKS = (
    "iso42001",
    "nist-ai-rmf",
    "eu-ai-act",
    "uk-atrs",
    "colorado-sb-205",
    "nyc-ll144",
    "cppa-admt",
    "ccpa-cpra",
    "ca-sb-942",
    "ca-ab-2013",
    "ca-ab-1008",
    "ca-sb-1001",
    "ca-ab-1836",
)

DEFAULT_CROSSWALK_TARGET_FRAMEWORKS = ("nist-ai-rmf", "eu-ai-act")

REQUIRED_INPUT_FIELDS = (
    "system_name",
    "purpose",
    "risk_tier",
    "data_processed",
    "deployment_context",
    "governance_decisions",
    "responsible_parties",
)

VALID_RISK_TIERS = ("minimal", "limited", "high", "unacceptable")

# Classifiers used by map_to_annex_a_controls. Each entry is
# (predicate, control_id, rationale_template). Predicates receive the
# system_description dict and return a bool.
_CONTROL_RULES = (
    (
        lambda s: True,
        "A.6.2.3",
        "AI system design and development documentation is required for every AI system in AIMS scope.",
    ),
    (
        lambda s: True,
        "A.6.2.8",
        "AI system log recording applies to every deployed AI system.",
    ),
    (
        lambda s: bool(s.get("responsible_parties")),
        "A.3.2",
        "AI-specific roles and responsibilities are documented; responsible parties are named in the input.",
    ),
    (
        lambda s: s.get("risk_tier") == "high",
        "A.5.4",
        "Risk tier is high; AI system impact on individuals and groups must be assessed per Clause 6.1.4 and documented under Annex A, Control A.5.4.",
    ),
    (
        lambda s: s.get("risk_tier") in ("high", "limited"),
        "A.6.2.4",
        "Verification and validation activities apply to AI systems at limited and high risk tiers.",
    ),
    (
        lambda s: s.get("risk_tier") == "high",
        "A.6.2.6",
        "Operational monitoring applies to deployed AI systems at high risk tier.",
    ),
    (
        lambda s: _has_sensitive_data(s),
        "A.7.2",
        "Data for development and enhancement of AI systems is in scope; sensitive data categories referenced in data_processed.",
    ),
    (
        lambda s: _has_sensitive_data(s),
        "A.7.5",
        "Data provenance tracking applies; sensitive data categories referenced in data_processed.",
    ),
    (
        lambda s: _is_high_impact_context(s),
        "A.5.5",
        "Deployment context implies broader societal impact; societal impact assessment applies per Annex A, Control A.5.5.",
    ),
    (
        lambda s: bool(s.get("governance_decisions")),
        "A.8.3",
        "Governance decisions are present and may constitute external reporting events; external reporting control applies where decisions are communicated outside the organization.",
    ),
)


def _has_sensitive_data(system_description: dict[str, Any]) -> bool:
    """Return True if data_processed references categories typically treated as sensitive."""
    sensitive_markers = (
        "pii",
        "personal",
        "health",
        "medical",
        "financial",
        "biometric",
        "genetic",
        "children",
        "minor",
        "protected",
    )
    items = system_description.get("data_processed") or []
    text = " ".join(str(x).lower() for x in items)
    return any(marker in text for marker in sensitive_markers)


def _is_high_impact_context(system_description: dict[str, Any]) -> bool:
    """Return True if deployment_context suggests broader societal or high-stakes impact."""
    high_impact_markers = (
        "clinical",
        "healthcare",
        "medical",
        "hospital",
        "emergency",
        "lending",
        "credit",
        "employment",
        "hr ",
        " hr",
        "hiring",
        "criminal",
        "law enforcement",
        "judicial",
        "education",
        "immigration",
        "public",
        "welfare",
    )
    context = str(system_description.get("deployment_context", "")).lower()
    return any(marker in context for marker in high_impact_markers)


def _validate(system_description: dict[str, Any]) -> None:
    """Raise ValueError if required fields are missing or malformed. No silent defaults."""
    if not isinstance(system_description, dict):
        raise ValueError("system_description must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in system_description]
    if missing:
        raise ValueError(f"system_description missing required fields: {sorted(missing)}")
    risk_tier = system_description.get("risk_tier")
    if risk_tier not in VALID_RISK_TIERS:
        raise ValueError(
            f"risk_tier must be one of {VALID_RISK_TIERS}; got {risk_tier!r}"
        )
    if not isinstance(system_description.get("data_processed"), list):
        raise ValueError("data_processed must be a list")
    if not isinstance(system_description.get("governance_decisions"), list):
        raise ValueError("governance_decisions must be a list")
    if not isinstance(system_description.get("responsible_parties"), list):
        raise ValueError("responsible_parties must be a list")

    enrich = system_description.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")

    targets = system_description.get("crosswalk_target_frameworks")
    if targets is not None:
        if not isinstance(targets, list):
            raise ValueError("crosswalk_target_frameworks, when provided, must be a list of framework ids")
        for t in targets:
            if not isinstance(t, str):
                raise ValueError(
                    f"crosswalk_target_frameworks entries must be strings; got {type(t).__name__}"
                )
            if t not in VALID_CROSSWALK_TARGET_FRAMEWORKS:
                raise ValueError(
                    f"Unknown crosswalk target framework '{t}'. "
                    f"Must be one of {sorted(VALID_CROSSWALK_TARGET_FRAMEWORKS)}."
                )


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string with seconds precision."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _annex_a_citation(control_id: str) -> str:
    """Format an Annex A control citation per STYLE.md."""
    return f"ISO/IEC 42001:2023, Annex A, Control {control_id}"


def _clause_citation(clause: str) -> str:
    """Format a main-body clause citation per STYLE.md."""
    return f"ISO/IEC 42001:2023, Clause {clause}"


def map_to_annex_a_controls(system_description: dict[str, Any]) -> list[dict[str, str]]:
    """
    Map an AI system description to applicable ISO 42001 Annex A controls.

    Args:
        system_description: Dict containing system_name, purpose, risk_tier,
                            data_processed, deployment_context,
                            governance_decisions, responsible_parties.

    Returns:
        List of dicts, each with:
            control_id: Annex A control identifier (for example "A.6.2.4").
            citation: Full STYLE.md citation string.
            rationale: Why this control applies to the described system.

    Raises:
        ValueError: if required input fields are missing or malformed.
    """
    _validate(system_description)
    mappings: list[dict[str, str]] = []
    seen: set[str] = set()
    for predicate, control_id, rationale in _CONTROL_RULES:
        if control_id in seen:
            continue
        try:
            if predicate(system_description):
                mappings.append(
                    {
                        "control_id": control_id,
                        "citation": _annex_a_citation(control_id),
                        "rationale": rationale,
                    }
                )
                seen.add(control_id)
        except Exception as exc:
            # Predicates operate on validated input; a predicate failure here
            # is an internal error, not a user-input error.
            raise RuntimeError(f"Control rule evaluation failed for {control_id}: {exc}") from exc
    return mappings


def _load_crosswalk_module():
    """Import the sibling crosswalk-matrix-builder plugin module.

    Lazy import so audit-log generation with enrich_with_crosswalk=False does
    not pay the YAML-load cost and is immune to crosswalk-side failures.
    """
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _derive_crosswalk_source_ref(citation: str) -> str | None:
    """Convert a STYLE.md citation into a crosswalk source_ref key.

    Examples:
        'ISO/IEC 42001:2023, Clause 9.1' -> 'Clause 9.1'
        'ISO/IEC 42001:2023, Annex A, Control A.6.2.6' -> 'A.6.2.6'

    Returns None if the citation does not match either expected form.
    """
    if not isinstance(citation, str):
        return None
    annex_prefix = "ISO/IEC 42001:2023, Annex A, Control "
    clause_prefix = "ISO/IEC 42001:2023, Clause "
    if citation.startswith(annex_prefix):
        return citation[len(annex_prefix):].strip()
    if citation.startswith(clause_prefix):
        return "Clause " + citation[len(clause_prefix):].strip()
    return None


def _enrich_events_with_crosswalk(
    events: list[dict[str, Any]],
    target_frameworks: list[str],
) -> tuple[list[str], dict[str, int]]:
    """Attach cross_framework_citations and citation_coverage to each event in-place.

    Returns (top_level_warnings, summary_counts). On crosswalk load failure,
    returns a single warning and leaves events unenriched (no key added).
    """
    try:
        crosswalk = _load_crosswalk_module()
    except Exception as exc:
        return (
            [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"],
            {"events_enriched": 0, "total_citations_added": 0},
        )

    try:
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return (
            [f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"],
            {"events_enriched": 0, "total_citations_added": 0},
        )

    # Index ISO 42001 mappings by source_ref for O(1) lookup per citation.
    by_source_ref: dict[str, list[dict[str, Any]]] = {}
    for m in data.get("mappings", []):
        if m.get("source_framework") != "iso42001":
            continue
        by_source_ref.setdefault(m["source_ref"], []).append(m)

    allowed = set(target_frameworks)
    events_enriched = 0
    total_added = 0

    for event in events:
        primary_citations: list[str] = []
        primary_citations.extend(event.get("clause_mappings") or [])
        for ann in event.get("annex_a_mappings") or []:
            if isinstance(ann, dict) and ann.get("citation"):
                primary_citations.append(ann["citation"])

        enriched: list[dict[str, Any]] = []
        for citation in primary_citations:
            source_ref = _derive_crosswalk_source_ref(citation)
            if source_ref is None:
                continue
            for m in by_source_ref.get(source_ref, []):
                if m.get("target_framework") not in allowed:
                    continue
                citations = m.get("citation_sources") or []
                citation_source = ""
                if citations:
                    citation_source = (citations[0].get("publication") or "").strip()
                enriched.append({
                    "target_framework": m.get("target_framework"),
                    "target_ref": m.get("target_ref"),
                    "target_title": m.get("target_title"),
                    "relationship": m.get("relationship"),
                    "confidence": m.get("confidence"),
                    "citation_source": citation_source,
                })

        event["cross_framework_citations"] = enriched
        event["citation_coverage"] = {
            "primary_framework": "iso42001",
            "enrichment_target_frameworks": list(target_frameworks),
            "citations_added_count": len(enriched),
        }
        if enriched:
            events_enriched += 1
            total_added += len(enriched)

    return (
        [],
        {
            "events_enriched": events_enriched,
            "total_citations_added": total_added,
        },
    )


def generate_audit_log(system_description: dict[str, Any]) -> dict[str, Any]:
    """
    Generate an ISO/IEC 42001:2023-compliant audit log entry for an AI system
    governance event.

    Args:
        system_description: Dict containing system_name, purpose, risk_tier,
                            data_processed, deployment_context,
                            governance_decisions, responsible_parties.
                            Optional: enrich_with_crosswalk (bool, default
                            True), crosswalk_target_frameworks (list of
                            framework ids, default ['nist-ai-rmf',
                            'eu-ai-act']).

    Returns:
        Dict containing:
            timestamp: ISO 8601 UTC timestamp of log generation.
            system_name: echoed from input.
            clause_mappings: list of main-body Clause citations applicable
                             to this event (for example Clause 9.1 for
                             monitoring and Clause 7.5 for documented
                             information).
            annex_a_mappings: list of Annex A control dicts from
                              map_to_annex_a_controls.
            evidence_items: list of decisions, each with its citation
                            anchor.
            human_readable_summary: natural-language summary suitable for
                                    inclusion in an audit evidence package.
            agent_signature: identifier of the generating agent.
            cross_framework_citations: (when enrichment runs) list of
                                       cross-framework equivalents for every
                                       primary citation on this event.
            citation_coverage: (when enrichment runs) per-event summary with
                               primary_framework, enrichment_target_frameworks,
                               citations_added_count.
            crosswalk_summary: (when enrichment runs) top-level summary of
                               target_frameworks, events_enriched, and
                               total_citations_added.
            warnings: (when enrichment fails gracefully) list of warning
                      strings; absent otherwise.

    Raises:
        ValueError: if required input fields are missing or malformed, or
                    if crosswalk_target_frameworks references an unknown
                    framework id.
    """
    _validate(system_description)

    annex_a_mappings = map_to_annex_a_controls(system_description)

    clause_mappings = [
        _clause_citation("7.5.2"),
        _clause_citation("9.1"),
    ]
    if system_description.get("governance_decisions"):
        # Governance decisions imply a Clause 9.3 management-review connection
        # and a Clause 5.3 authority reference.
        clause_mappings.append(_clause_citation("5.3"))
        clause_mappings.append(_clause_citation("9.3"))
    if system_description.get("risk_tier") == "high":
        # High risk tier implies Clause 6.1.4 AISIA trigger.
        clause_mappings.append(_clause_citation("6.1.4"))

    evidence_items = [
        {
            "decision": str(decision),
            "citation_anchor": _clause_citation("9.3"),
        }
        for decision in system_description["governance_decisions"]
    ]

    responsible_parties_str = ", ".join(
        str(p) for p in system_description["responsible_parties"]
    )
    summary = (
        f"AI governance event recorded for system {system_description['system_name']}. "
        f"System purpose: {system_description['purpose']}. "
        f"Risk tier: {system_description['risk_tier']}. "
        f"Deployment context: {system_description['deployment_context']}. "
        f"Responsible parties: {responsible_parties_str}. "
        f"Applicable Annex A controls: {', '.join(m['control_id'] for m in annex_a_mappings)}."
    )

    entry: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "system_name": system_description["system_name"],
        "clause_mappings": clause_mappings,
        "annex_a_mappings": annex_a_mappings,
        "evidence_items": evidence_items,
        "human_readable_summary": summary,
        "agent_signature": AGENT_SIGNATURE,
    }

    # Optional crosswalk enrichment (opt-out, default on). Treat this single
    # entry as a one-event batch so the same helper serves multi-event
    # callers once that becomes a use case.
    enrich = system_description.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True
    target_frameworks = list(
        system_description.get("crosswalk_target_frameworks") or DEFAULT_CROSSWALK_TARGET_FRAMEWORKS
    )

    if enrich:
        events = [entry]
        warnings, counts = _enrich_events_with_crosswalk(events, target_frameworks)
        if warnings:
            entry["warnings"] = warnings
        entry["crosswalk_summary"] = {
            "target_frameworks": target_frameworks,
            "events_enriched": counts["events_enriched"],
            "total_citations_added": counts["total_citations_added"],
        }

    return entry


def render_markdown(audit_log: dict[str, Any]) -> str:
    """
    Render an audit log dict as a human-readable Markdown document.

    Args:
        audit_log: The dict returned by generate_audit_log.

    Returns:
        A Markdown string suitable for inclusion in an audit evidence package.
    """
    required = ("timestamp", "system_name", "clause_mappings", "annex_a_mappings", "evidence_items", "human_readable_summary")
    missing = [k for k in required if k not in audit_log]
    if missing:
        raise ValueError(f"audit_log missing required fields: {missing}")

    lines = [
        "# AI Governance Audit Log Entry",
        "",
        f"**System:** {audit_log['system_name']}",
        f"**Timestamp (UTC):** {audit_log['timestamp']}",
        f"**Generated by:** {audit_log.get('agent_signature', 'unknown')}",
        "",
        "## Summary",
        "",
        audit_log["human_readable_summary"],
        "",
        "## Applicable Main-Body Clauses",
        "",
    ]
    for citation in audit_log["clause_mappings"]:
        lines.append(f"- {citation}")
    lines.extend(["", "## Applicable Annex A Controls", ""])
    if not audit_log["annex_a_mappings"]:
        lines.append("- None identified for this event.")
    else:
        for mapping in audit_log["annex_a_mappings"]:
            lines.append(f"- **{mapping['control_id']}** ({mapping['citation']}): {mapping['rationale']}")
    lines.extend(["", "## Evidence Items", ""])
    if not audit_log["evidence_items"]:
        lines.append("- No governance decisions referenced.")
    else:
        for item in audit_log["evidence_items"]:
            lines.append(f"- {item['decision']} [{item['citation_anchor']}]")

    # Cross-framework references section emitted only when enrichment ran.
    if "cross_framework_citations" in audit_log:
        lines.extend(["", "## Cross-framework references", ""])
        refs = audit_log.get("cross_framework_citations") or []
        if not refs:
            lines.append("- (no cross-framework citations found for target frameworks)")
        else:
            for ref in refs:
                conf = ref.get("confidence") or ""
                badge = f"[{conf}]" if conf else ""
                source = ref.get("citation_source") or ""
                source_suffix = f" ({source})" if source else ""
                lines.append(
                    f"- {ref.get('target_framework')} -> {ref.get('target_ref')} "
                    f"({ref.get('relationship')}) {badge}{source_suffix}".rstrip()
                )

        coverage = audit_log.get("citation_coverage") or {}
        if coverage:
            lines.extend(["", "### Citation coverage", ""])
            lines.append(f"- primary_framework: {coverage.get('primary_framework', '')}")
            targets = coverage.get("enrichment_target_frameworks") or []
            lines.append(f"- enrichment_target_frameworks: {', '.join(targets)}")
            lines.append(f"- citations_added_count: {coverage.get('citations_added_count', 0)}")

    if audit_log.get("crosswalk_summary"):
        cs = audit_log["crosswalk_summary"]
        lines.extend([
            "",
            "## Crosswalk summary",
            "",
            f"- target_frameworks: {', '.join(cs.get('target_frameworks', []))}",
            f"- events_enriched: {cs.get('events_enriched', 0)}",
            f"- total_citations_added: {cs.get('total_citations_added', 0)}",
        ])

    if audit_log.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in audit_log["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(audit_log: dict[str, Any]) -> str:
    """Render a single audit log entry as CSV.

    Emits one row per Annex A control mapping. When crosswalk enrichment
    ran, adds three columns:
      - crosswalk_nist_ref: first NIST AI RMF equivalent target_ref (if any)
      - crosswalk_eu_ai_act_ref: first EU AI Act equivalent target_ref (if any)
      - crosswalk_additional_count: count of remaining equivalents elided from the row
    """
    required = ("timestamp", "system_name", "clause_mappings", "annex_a_mappings")
    missing = [k for k in required if k not in audit_log]
    if missing:
        raise ValueError(f"audit_log missing required fields: {missing}")

    enriched = "cross_framework_citations" in audit_log
    # Build per-Annex-A indexed view of the event's cross-framework citations
    # so each row can surface the crosswalk hits that derive from that control.
    refs_by_source: dict[str, list[dict[str, Any]]] = {}
    if enriched:
        for ref in audit_log.get("cross_framework_citations") or []:
            # Bucket each ref under its target framework for row-wise flattening.
            refs_by_source.setdefault(ref.get("target_framework") or "", []).append(ref)

    header_cols = [
        "timestamp",
        "system_name",
        "control_id",
        "citation",
        "clause_mappings",
        "rationale",
    ]
    if enriched:
        header_cols.extend([
            "crosswalk_nist_ref",
            "crosswalk_eu_ai_act_ref",
            "crosswalk_additional_count",
        ])
    header = ",".join(header_cols)
    lines = [header]

    clause_joined = "; ".join(audit_log.get("clause_mappings") or [])

    all_refs = audit_log.get("cross_framework_citations") or []
    nist_ref = ""
    eu_ref = ""
    flattened = 0
    for ref in all_refs:
        tf = ref.get("target_framework")
        if tf == "nist-ai-rmf" and not nist_ref:
            nist_ref = ref.get("target_ref") or ""
            flattened += 1
        elif tf == "eu-ai-act" and not eu_ref:
            eu_ref = ref.get("target_ref") or ""
            flattened += 1
    elided = max(0, len(all_refs) - flattened)

    for mapping in audit_log["annex_a_mappings"]:
        fields = [
            _csv_escape(str(audit_log.get("timestamp", ""))),
            _csv_escape(str(audit_log.get("system_name", ""))),
            _csv_escape(str(mapping.get("control_id", ""))),
            _csv_escape(str(mapping.get("citation", ""))),
            _csv_escape(clause_joined),
            _csv_escape(str(mapping.get("rationale", ""))),
        ]
        if enriched:
            fields.extend([
                _csv_escape(nist_ref),
                _csv_escape(eu_ref),
                _csv_escape(str(elided)),
            ])
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
