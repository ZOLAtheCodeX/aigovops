"""
AIGovOps: Human Oversight Designer Plugin

Operationalizes EU AI Act Article 14 (Human oversight), ISO/IEC 42001:2023
Annex A controls A.9.2 (Processes for responsible use of AI systems), A.9.3
(Objectives for responsible use), and A.9.4 (Intended use of the AI system),
NIST AI RMF MANAGE 2.3 (mechanisms to prevent, disengage, override, or
deactivate AI systems), and UK ATRS Section 2.2 (Decision making process)
and Section 4.4 (Redress and appeal).

Distinct from the aisia-runner plugin which treats human-oversight as one
impact dimension within a broader AISIA. This plugin produces the
dedicated human-oversight design artifact: ability coverage against
Article 14(4)(a) through (e), override capability assessment, biometric
dual-assignment verification per Article 14(5), operator training
posture, automation bias mitigations, and assigned oversight personnel.

Design stance: the plugin does NOT invent oversight measures, override
controls, training programmes, or personnel assignments. Each substantive
field comes from input or is computed deterministically from input. Gaps
surface as warnings; missing Article 14(4) abilities surface as
placeholder rows marked REQUIRES PRACTITIONER ASSIGNMENT.

Status: Phase 4 implementation. Closes the dedicated human-oversight
design-artifact gap in the eu-ai-act operationalization map.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "human-oversight-designer/0.1.0"

REQUIRED_INPUT_FIELDS = ("system_description", "oversight_design")

# Article 14(4)(a) through (e) abilities. Each ability is an oversight
# capability the persons assigned to oversight must be enabled to
# perform.
ART_14_4_ABILITIES = (
    "understand",
    "awareness-of-automation-bias",
    "correctly-interpret",
    "decide-not-to-use",
    "intervene-or-stop",
)

ART_14_4_ABILITY_LABELS: dict[str, str] = {
    "understand": "Article 14(4)(a): properly understand capacities and limitations",
    "awareness-of-automation-bias": "Article 14(4)(b): remain aware of automation bias",
    "correctly-interpret": "Article 14(4)(c): correctly interpret the output",
    "decide-not-to-use": "Article 14(4)(d): decide not to use, disregard, override, or reverse",
    "intervene-or-stop": "Article 14(4)(e): intervene or interrupt via stop button",
}

VALID_OVERSIGHT_AUTHORITY_LEVELS = (
    "sole-authority",
    "shared-authority",
    "veto-authority",
    "advisory-only",
    "observer-only",
)

AUTHORITATIVE_AUTHORITY_LEVELS = (
    "sole-authority",
    "shared-authority",
    "veto-authority",
)

VALID_OVERSIGHT_MODES = (
    "human-in-the-loop",
    "human-on-the-loop",
    "human-out-of-the-loop-with-escalation",
    "fully-automated-unauthorised",
)

VALID_OVERRIDE_CONTROL_TYPES = (
    "stop-button",
    "kill-switch",
    "delay-and-review",
    "human-approval-required",
)

BIOMETRIC_SPECIAL_ASSIGNMENTS_MIN = 2

OVERRIDE_LATENCY_THRESHOLD_SECONDS = 30

OVERRIDE_TEST_FRESHNESS_DAYS = 365

OPERATOR_TRAINING_COMPLETION_FLOOR = 80.0

PRACTITIONER_PLACEHOLDER = "REQUIRES PRACTITIONER ASSIGNMENT"

HIGH_RISK_TIERS = ("high-risk-annex-i", "high-risk-annex-iii")

# Sibling-plugin path for crosswalk-matrix-builder. Imported lazily so
# enrich_with_crosswalk=False calls pay no import cost and are unaffected
# by crosswalk load failures.
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

    system = inputs["system_description"]
    if not isinstance(system, dict):
        raise ValueError("system_description must be a dict")
    for req in ("system_id", "system_name", "intended_use", "risk_tier"):
        if req not in system:
            raise ValueError(f"system_description missing required field: {req}")

    biometric_flag = system.get("biometric_identification_system", False)
    if not isinstance(biometric_flag, bool):
        raise ValueError("system_description.biometric_identification_system must be a bool")

    design = inputs["oversight_design"]
    if not isinstance(design, dict):
        raise ValueError("oversight_design must be a dict")

    mode = design.get("mode")
    if mode not in VALID_OVERSIGHT_MODES:
        raise ValueError(
            f"oversight_design.mode must be one of {VALID_OVERSIGHT_MODES}; got {mode!r}"
        )

    ability_coverage = design.get("ability_coverage")
    if ability_coverage is not None and not isinstance(ability_coverage, dict):
        raise ValueError("oversight_design.ability_coverage, when provided, must be a dict")

    override_controls = design.get("override_controls")
    if override_controls is not None and not isinstance(override_controls, list):
        raise ValueError("oversight_design.override_controls, when provided, must be a list")
    for i, ctrl in enumerate(override_controls or []):
        if not isinstance(ctrl, dict):
            raise ValueError(f"oversight_design.override_controls[{i}] must be a dict")
        ctrl_type = ctrl.get("control_type")
        if ctrl_type is not None and ctrl_type not in VALID_OVERRIDE_CONTROL_TYPES:
            raise ValueError(
                f"oversight_design.override_controls[{i}].control_type must be one of "
                f"{VALID_OVERRIDE_CONTROL_TYPES}; got {ctrl_type!r}"
            )

    operator_training = design.get("operator_training")
    if operator_training is not None and not isinstance(operator_training, dict):
        raise ValueError("oversight_design.operator_training, when provided, must be a dict")

    bias_mitigations = design.get("automation_bias_mitigations")
    if bias_mitigations is not None and not isinstance(bias_mitigations, list):
        raise ValueError("oversight_design.automation_bias_mitigations, when provided, must be a list")

    escalation_paths = design.get("escalation_paths")
    if escalation_paths is not None and not isinstance(escalation_paths, list):
        raise ValueError("oversight_design.escalation_paths, when provided, must be a list")

    personnel = inputs.get("assigned_oversight_personnel")
    if personnel is not None:
        if not isinstance(personnel, list):
            raise ValueError("assigned_oversight_personnel, when provided, must be a list")
        for i, person in enumerate(personnel):
            if not isinstance(person, dict):
                raise ValueError(f"assigned_oversight_personnel[{i}] must be a dict")
            authority = person.get("authority_level")
            if authority not in VALID_OVERSIGHT_AUTHORITY_LEVELS:
                raise ValueError(
                    f"assigned_oversight_personnel[{i}].authority_level must be one of "
                    f"{VALID_OVERSIGHT_AUTHORITY_LEVELS}; got {authority!r}"
                )

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is not None and not isinstance(enrich, bool):
        raise ValueError("enrich_with_crosswalk, when provided, must be a bool")


def _is_high_risk(risk_tier: str | None) -> bool:
    return risk_tier in HIGH_RISK_TIERS


def _parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _assess_ability_coverage(
    ability_coverage: dict[str, Any] | None,
    art_14_applies: bool,
) -> tuple[list[dict[str, Any]], list[str], str]:
    """Return (per-ability rows, warnings, status)."""
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    coverage = ability_coverage or {}
    enabled_count = 0

    for ability in ART_14_4_ABILITIES:
        entry = coverage.get(ability) if isinstance(coverage, dict) else None
        if not isinstance(entry, dict):
            rows.append({
                "ability": ability,
                "label": ART_14_4_ABILITY_LABELS[ability],
                "enabled": False,
                "mechanism": PRACTITIONER_PLACEHOLDER,
                "evidence_ref": PRACTITIONER_PLACEHOLDER,
            })
            if art_14_applies:
                warnings.append(
                    f"Article 14(4) ability '{ability}' not documented. "
                    "Practitioner assignment required before the design is audit-ready."
                )
            continue

        enabled = bool(entry.get("enabled", False))
        mechanism = entry.get("mechanism") or PRACTITIONER_PLACEHOLDER
        evidence_ref = entry.get("evidence_ref") or PRACTITIONER_PLACEHOLDER
        rows.append({
            "ability": ability,
            "label": ART_14_4_ABILITY_LABELS[ability],
            "enabled": enabled,
            "mechanism": mechanism,
            "evidence_ref": evidence_ref,
        })
        if enabled:
            enabled_count += 1
        elif art_14_applies:
            warnings.append(
                f"Article 14(4) ability '{ability}' is documented but disabled. "
                "Enable the ability or justify non-applicability before deployment."
            )

    if not art_14_applies:
        status = "not-mandated"
    elif enabled_count == len(ART_14_4_ABILITIES):
        status = "full-coverage"
    elif enabled_count == 0:
        status = "no-coverage"
    else:
        status = "partial-coverage"

    return rows, warnings, status


def _assess_override_controls(
    override_controls: list[dict[str, Any]] | None,
    risk_tier: str | None,
    now: datetime,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (per-control rows, warnings)."""
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    controls = override_controls or []

    if not controls:
        warnings.append(
            "Article 14(4)(d) and 14(4)(e): no override_controls documented. "
            "At least one override control (stop-button, kill-switch, delay-and-review, "
            "or human-approval-required) is required."
        )
        return rows, warnings

    high_risk = _is_high_risk(risk_tier)
    freshness_threshold = now - timedelta(days=OVERRIDE_TEST_FRESHNESS_DAYS)

    for i, ctrl in enumerate(controls):
        control_name = ctrl.get("control_name") or f"override-{i + 1:02d}"
        control_type = ctrl.get("control_type") or PRACTITIONER_PLACEHOLDER
        latency = ctrl.get("activation_latency_seconds")
        tested_date_raw = ctrl.get("tested_date")
        tested_by = ctrl.get("tested_by") or PRACTITIONER_PLACEHOLDER

        ctrl_warnings: list[str] = []

        if latency is None:
            ctrl_warnings.append(
                f"Override control '{control_name}' has no activation_latency_seconds documented."
            )
        elif isinstance(latency, (int, float)) and high_risk and latency > OVERRIDE_LATENCY_THRESHOLD_SECONDS:
            ctrl_warnings.append(
                f"Override control '{control_name}' latency {latency}s exceeds "
                f"{OVERRIDE_LATENCY_THRESHOLD_SECONDS}s. Override latency may be inadequate "
                "for real-time decision contexts on high-risk systems."
            )

        tested_date = _parse_iso_date(tested_date_raw)
        if tested_date is None:
            ctrl_warnings.append(
                f"Override control '{control_name}' has no tested_date documented. "
                "Per-control test evidence is required for audit readiness."
            )
        else:
            if tested_date.tzinfo is None:
                tested_date = tested_date.replace(tzinfo=timezone.utc)
            if tested_date < freshness_threshold:
                ctrl_warnings.append(
                    f"Override control '{control_name}' last tested {tested_date_raw}; "
                    "Override control not tested in the last 12 months."
                )

        if tested_by == PRACTITIONER_PLACEHOLDER:
            ctrl_warnings.append(
                f"Override control '{control_name}' has no tested_by attribution."
            )

        warnings.extend(ctrl_warnings)
        rows.append({
            "control_name": control_name,
            "control_type": control_type,
            "activation_latency_seconds": latency,
            "tested_date": tested_date_raw,
            "tested_by": tested_by,
            "warnings": ctrl_warnings,
        })

    return rows, warnings


def _assess_biometric_dual_assignment(
    biometric: bool,
    personnel: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not biometric:
        return None
    authoritative = [
        p for p in personnel
        if p.get("authority_level") in AUTHORITATIVE_AUTHORITY_LEVELS
    ]
    satisfied = len(authoritative) >= BIOMETRIC_SPECIAL_ASSIGNMENTS_MIN
    warnings: list[str] = []
    if not satisfied:
        warnings.append(
            "Article 14(5) requires at least 2 natural persons with authority "
            "and competence for remote biometric identification verification. "
            f"Documented authoritative personnel count: {len(authoritative)}."
        )
    return {
        "required_minimum": BIOMETRIC_SPECIAL_ASSIGNMENTS_MIN,
        "authoritative_personnel_count": len(authoritative),
        "authoritative_personnel": authoritative,
        "satisfied": satisfied,
        "warnings": warnings,
        "citation": "EU AI Act, Article 14, Paragraph 5",
    }


def _assess_mode(mode: str, art_14_applies: bool) -> dict[str, Any]:
    blocking = False
    findings: list[str] = []
    if mode == "fully-automated-unauthorised" and art_14_applies:
        blocking = True
        findings.append(
            "Fully-automated mode without oversight is non-compliant with "
            "Article 14 for high-risk systems."
        )
    return {
        "mode": mode,
        "blocking_finding": blocking,
        "findings": findings,
        "citation": "EU AI Act, Article 14, Paragraph 1",
    }


def _assess_operator_training(
    training: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    training = training or {}
    completion_rate = training.get("completion_rate_percent")
    annual_refresh = training.get("annual_refresh", False)

    if completion_rate is None:
        warnings.append(
            "Operator training completion_rate_percent not documented. "
            "Coverage of operator training is required for audit readiness."
        )
    else:
        try:
            rate_value = float(completion_rate)
        except (TypeError, ValueError):
            rate_value = None
            warnings.append(
                "Operator training completion_rate_percent is not a numeric value."
            )
        if rate_value is not None and rate_value < OPERATOR_TRAINING_COMPLETION_FLOOR:
            warnings.append(
                f"Operator training completion rate {rate_value} percent "
                "below 80 percent may compromise oversight effectiveness."
            )

    if not annual_refresh:
        warnings.append(
            "Annual oversight training refresh recommended."
        )

    assessment = {
        "curriculum_ref": training.get("curriculum_ref") or PRACTITIONER_PLACEHOLDER,
        "assessment_ref": training.get("assessment_ref") or PRACTITIONER_PLACEHOLDER,
        "completion_rate_percent": completion_rate,
        "annual_refresh": annual_refresh,
        "warnings": warnings,
        "citation": "ISO/IEC 42001:2023, Annex A, Control A.9.2",
    }
    return assessment, warnings


def _assess_automation_bias(
    mitigations: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    mitigations = mitigations or []
    warnings: list[str] = []
    if not mitigations:
        warnings.append(
            "Article 14(4)(b) automation bias awareness measures not documented. "
            "At least one automation_bias_mitigation is required."
        )
    rows: list[dict[str, Any]] = []
    for i, m in enumerate(mitigations):
        if not isinstance(m, dict):
            warnings.append(
                f"automation_bias_mitigations[{i}] is not a dict and was skipped."
            )
            continue
        rows.append({
            "mitigation_name": m.get("mitigation_name") or PRACTITIONER_PLACEHOLDER,
            "rationale": m.get("rationale") or PRACTITIONER_PLACEHOLDER,
            "reference": m.get("reference") or PRACTITIONER_PLACEHOLDER,
        })
    return rows, warnings


def _build_citations(jurisdiction: str | None, art_14_applies: bool) -> list[str]:
    citations: list[str] = []
    if art_14_applies:
        citations.extend([
            "EU AI Act, Article 14, Paragraph 1",
            "EU AI Act, Article 14, Paragraph 2",
            "EU AI Act, Article 14, Paragraph 3",
            "EU AI Act, Article 14, Paragraph 4",
            "EU AI Act, Article 14, Paragraph 5",
        ])
    citations.extend([
        "ISO/IEC 42001:2023, Annex A, Control A.9.2",
        "ISO/IEC 42001:2023, Annex A, Control A.9.3",
        "ISO/IEC 42001:2023, Annex A, Control A.9.4",
        "MANAGE 2.3",
    ])
    if (jurisdiction or "").lower().startswith("uk"):
        citations.append("UK ATRS, Section Tool description")
        citations.append("UK ATRS, Section Impact assessment")
    return citations


def _load_crosswalk_module():
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_human_oversight", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _enrich_with_crosswalk() -> tuple[list[dict[str, Any]], list[str]]:
    """Pull EU AI Act Article 14 source rows from the crosswalk."""
    try:
        crosswalk = _load_crosswalk_module()
        data = crosswalk.load_crosswalk_data()
    except Exception as exc:
        return [], [
            f"Crosswalk enrichment skipped: {type(exc).__name__}: {exc}"
        ]

    collected: list[dict[str, Any]] = []
    for m in data.get("mappings", []):
        if m.get("source_framework") != "eu-ai-act":
            continue
        source_ref = str(m.get("source_ref", ""))
        if "Article 14" not in source_ref:
            continue
        citations = m.get("citation_sources") or []
        citation_label = ""
        if citations:
            citation_label = (citations[0].get("publication") or "").strip()
        collected.append({
            "source_ref": source_ref,
            "source_title": m.get("source_title"),
            "target_framework": m.get("target_framework"),
            "target_ref": m.get("target_ref"),
            "target_title": m.get("target_title"),
            "relationship": m.get("relationship"),
            "confidence": m.get("confidence"),
            "citation": citation_label,
        })
    return collected, []


def design_human_oversight(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Produce a human-oversight design artifact per EU AI Act Article 14,
    ISO/IEC 42001:2023 Annex A controls A.9.2 to A.9.4, and NIST AI RMF
    MANAGE 2.3.

    Args:
        inputs: dict with required keys system_description and oversight_design.
            system_description: dict with system_id, system_name, intended_use,
                                risk_tier, optional jurisdiction, deployment_context,
                                decision_authority, biometric_identification_system.
            oversight_design: dict with mode, ability_coverage, override_controls,
                              operator_training, automation_bias_mitigations,
                              escalation_paths.
            assigned_oversight_personnel: list of {person_role, authority_level,
                                          training_evidence_ref}. Required when
                                          system is high-risk.
            previous_design_ref: optional version-tracking reference.
            enrich_with_crosswalk: bool (default True).
            reviewed_by: optional reviewer name.

    Returns:
        Dict with timestamp, agent_signature, framework, system_description_echo,
        art_14_applicability, ability_coverage_assessment, override_capability_assessment,
        biometric_dual_assignment_check (when applicable), mode_validation,
        operator_training_assessment, automation_bias_mitigations_echo,
        oversight_personnel, citations, warnings, summary,
        cross_framework_citations (when enriched), reviewed_by.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)

    system = inputs["system_description"]
    design = inputs["oversight_design"]
    risk_tier = system.get("risk_tier")
    biometric = bool(system.get("biometric_identification_system", False))
    jurisdiction = system.get("jurisdiction")
    art_14_applies = _is_high_risk(risk_tier)
    art_14_applicability = "applies" if art_14_applies else "not-mandated-but-recommended"

    personnel = inputs.get("assigned_oversight_personnel") or []
    warnings: list[str] = []

    if art_14_applies and not personnel:
        warnings.append(
            "assigned_oversight_personnel is required for high-risk systems "
            "per Article 14. Assign at least one accountable person."
        )

    ability_rows, ability_warnings, ability_status = _assess_ability_coverage(
        design.get("ability_coverage"), art_14_applies
    )
    warnings.extend(ability_warnings)

    now = datetime.now(timezone.utc)
    override_rows, override_warnings = _assess_override_controls(
        design.get("override_controls"), risk_tier, now
    )
    warnings.extend(override_warnings)

    biometric_check = _assess_biometric_dual_assignment(biometric, personnel)
    if biometric_check is not None:
        warnings.extend(biometric_check.get("warnings", []))

    mode_validation = _assess_mode(design["mode"], art_14_applies)
    warnings.extend(mode_validation["findings"])

    training_assessment, training_warnings = _assess_operator_training(
        design.get("operator_training")
    )
    warnings.extend(training_warnings)

    bias_rows, bias_warnings = _assess_automation_bias(
        design.get("automation_bias_mitigations")
    )
    warnings.extend(bias_warnings)

    citations = _build_citations(jurisdiction, art_14_applies)

    enrich = inputs.get("enrich_with_crosswalk")
    if enrich is None:
        enrich = True
    cross_framework_citations: list[dict[str, Any]] | None = None
    if enrich:
        cross_framework_citations, crosswalk_warnings = _enrich_with_crosswalk()
        warnings.extend(crosswalk_warnings)

    summary = {
        "art_14_applicability": art_14_applicability,
        "ability_status": ability_status,
        "abilities_enabled": sum(1 for r in ability_rows if r["enabled"]),
        "abilities_total": len(ART_14_4_ABILITIES),
        "override_control_count": len(override_rows),
        "biometric_dual_assignment_satisfied": (
            biometric_check.get("satisfied") if biometric_check else None
        ),
        "mode": design["mode"],
        "mode_blocking": mode_validation["blocking_finding"],
        "automation_bias_mitigation_count": len(bias_rows),
        "personnel_count": len(personnel),
        "warning_count": len(warnings),
    }

    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "eu-ai-act,iso42001,nist",
        "system_description_echo": system,
        "art_14_applicability": art_14_applicability,
        "ability_coverage_assessment": {
            "status": ability_status,
            "rows": ability_rows,
            "citation": "EU AI Act, Article 14, Paragraph 4",
        },
        "override_capability_assessment": {
            "rows": override_rows,
            "citation": "EU AI Act, Article 14, Paragraph 4",
        },
        "mode_validation": mode_validation,
        "operator_training_assessment": training_assessment,
        "automation_bias_mitigations_echo": bias_rows,
        "escalation_paths": design.get("escalation_paths") or [],
        "oversight_personnel": personnel,
        "previous_design_ref": inputs.get("previous_design_ref"),
        "citations": citations,
        "warnings": warnings,
        "summary": summary,
        "reviewed_by": inputs.get("reviewed_by"),
    }

    if biometric_check is not None:
        output["biometric_dual_assignment_check"] = biometric_check

    if cross_framework_citations is not None:
        output["cross_framework_citations"] = cross_framework_citations

    return output


def render_markdown(design: dict[str, Any]) -> str:
    """Render a human-oversight design artifact as Markdown."""
    required = (
        "timestamp", "agent_signature", "system_description_echo",
        "art_14_applicability", "ability_coverage_assessment",
        "override_capability_assessment", "mode_validation",
        "operator_training_assessment", "citations", "warnings", "summary",
    )
    missing = [k for k in required if k not in design]
    if missing:
        raise ValueError(f"design missing required fields: {missing}")

    sys_desc = design["system_description_echo"]
    lines = [
        f"# Human Oversight Design: {sys_desc.get('system_name', 'unknown system')}",
        "",
        f"**Generated at (UTC):** {design['timestamp']}",
        f"**Generated by:** {design['agent_signature']}",
        f"**System ID:** {sys_desc.get('system_id', 'unknown')}",
        f"**Risk tier:** {sys_desc.get('risk_tier', 'unknown')}",
    ]
    if design.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {design['reviewed_by']}")
    if design.get("previous_design_ref"):
        lines.append(f"**Previous design ref:** {design['previous_design_ref']}")

    lines.extend([
        "",
        "## Applicability",
        "",
        f"- Article 14 applicability: {design['art_14_applicability']}",
        f"- Citation: EU AI Act, Article 14",
        "",
        "## Ability coverage",
        "",
        f"Status: {design['ability_coverage_assessment']['status']}",
        "",
        "| Ability | Label | Enabled | Mechanism | Evidence ref |",
        "|---|---|---|---|---|",
    ])
    for row in design["ability_coverage_assessment"]["rows"]:
        lines.append(
            f"| {row['ability']} | {row['label']} | {row['enabled']} | "
            f"{row['mechanism']} | {row['evidence_ref']} |"
        )

    lines.extend([
        "",
        "## Override capability",
        "",
        "| Control name | Control type | Latency (s) | Tested date | Tested by |",
        "|---|---|---|---|---|",
    ])
    for row in design["override_capability_assessment"]["rows"]:
        lines.append(
            f"| {row['control_name']} | {row['control_type']} | "
            f"{row.get('activation_latency_seconds')} | {row.get('tested_date')} | "
            f"{row.get('tested_by')} |"
        )
    if not design["override_capability_assessment"]["rows"]:
        lines.append("| (none) | (none) | (none) | (none) | (none) |")

    if "biometric_dual_assignment_check" in design:
        check = design["biometric_dual_assignment_check"]
        lines.extend([
            "",
            "## Biometric dual-assignment",
            "",
            f"- Required minimum: {check['required_minimum']}",
            f"- Authoritative personnel count: {check['authoritative_personnel_count']}",
            f"- Satisfied: {check['satisfied']}",
            f"- Citation: {check['citation']}",
        ])

    mv = design["mode_validation"]
    lines.extend([
        "",
        "## Mode validation",
        "",
        f"- Mode: {mv['mode']}",
        f"- Blocking finding: {mv['blocking_finding']}",
        f"- Citation: {mv['citation']}",
    ])
    for finding in mv.get("findings", []):
        lines.append(f"- Finding: {finding}")

    training = design["operator_training_assessment"]
    lines.extend([
        "",
        "## Operator training",
        "",
        f"- Curriculum ref: {training['curriculum_ref']}",
        f"- Assessment ref: {training['assessment_ref']}",
        f"- Completion rate (percent): {training['completion_rate_percent']}",
        f"- Annual refresh: {training['annual_refresh']}",
        f"- Citation: {training['citation']}",
        "",
        "## Automation bias",
        "",
        "| Mitigation | Rationale | Reference |",
        "|---|---|---|",
    ])
    for row in design["automation_bias_mitigations_echo"]:
        lines.append(
            f"| {row['mitigation_name']} | {row['rationale']} | {row['reference']} |"
        )
    if not design["automation_bias_mitigations_echo"]:
        lines.append("| (none) | (none) | (none) |")

    lines.extend([
        "",
        "## Oversight personnel",
        "",
        "| Role | Authority level | Training evidence ref |",
        "|---|---|---|",
    ])
    for person in design.get("oversight_personnel", []):
        lines.append(
            f"| {person.get('person_role', '')} | {person.get('authority_level', '')} | "
            f"{person.get('training_evidence_ref', '')} |"
        )
    if not design.get("oversight_personnel"):
        lines.append("| (none) | (none) | (none) |")

    if design.get("escalation_paths"):
        lines.extend([
            "",
            "## Escalation paths",
            "",
            "| Trigger | Recipient role | Response SLA (hours) |",
            "|---|---|---|",
        ])
        for path in design["escalation_paths"]:
            lines.append(
                f"| {path.get('trigger_condition', '')} | "
                f"{path.get('recipient_role', '')} | "
                f"{path.get('response_sla_hours', '')} |"
            )

    lines.extend([
        "",
        "## Citations",
        "",
    ])
    for c in design["citations"]:
        lines.append(f"- {c}")

    if design.get("cross_framework_citations"):
        lines.extend(["", "## Cross-framework citations", ""])
        for entry in design["cross_framework_citations"]:
            lines.append(
                f"- {entry.get('source_ref')} -> {entry.get('target_framework')} "
                f"{entry.get('target_ref')} ({entry.get('relationship')})"
            )

    lines.extend(["", "## Warnings", ""])
    if design["warnings"]:
        for w in design["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("- (no warnings)")

    lines.append("")
    return "\n".join(lines)


def render_csv(design: dict[str, Any]) -> str:
    """Render the human-oversight design as CSV.

    One header row plus one row per ability_coverage entry, one row per
    override_control, and one row per oversight_personnel entry.
    """
    if "ability_coverage_assessment" not in design:
        raise ValueError("design missing 'ability_coverage_assessment' field")

    lines = ["section,key,value_a,value_b,value_c"]

    for row in design["ability_coverage_assessment"]["rows"]:
        lines.append(",".join([
            "ability",
            _csv_escape(row["ability"]),
            _csv_escape(str(row["enabled"])),
            _csv_escape(row["mechanism"]),
            _csv_escape(row["evidence_ref"]),
        ]))

    for row in design.get("override_capability_assessment", {}).get("rows", []):
        lines.append(",".join([
            "override",
            _csv_escape(row["control_name"]),
            _csv_escape(row["control_type"]),
            _csv_escape(str(row.get("activation_latency_seconds", ""))),
            _csv_escape(str(row.get("tested_date", "") or "")),
        ]))

    for person in design.get("oversight_personnel", []):
        lines.append(",".join([
            "personnel",
            _csv_escape(person.get("person_role", "")),
            _csv_escape(person.get("authority_level", "")),
            _csv_escape(person.get("training_evidence_ref", "")),
            "",
        ]))

    for row in design.get("automation_bias_mitigations_echo", []):
        lines.append(",".join([
            "bias-mitigation",
            _csv_escape(row["mitigation_name"]),
            _csv_escape(row["rationale"]),
            _csv_escape(row["reference"]),
            "",
        ]))

    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value
