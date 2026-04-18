"""Tests for uk-atrs-recorder plugin."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _tier_1_inputs(**overrides) -> dict:
    base = {
        "tier": "tier-1",
        "owner": {
            "organization": "Department for Work and Pensions",
            "parent_organization": "UK Government",
            "contact_point": "atrs@dwp.gov.uk",
            "senior_responsible_owner": "DWP Digital Director",
        },
        "tool_description": {
            "name": "Benefits Eligibility Decision Support",
            "purpose": "Risk-score benefits applications for caseworker review.",
            "how_tool_works": "Gradient-boosted model scores applications; caseworker decides.",
            "decision_subject_scope": "Working-age benefits applicants.",
            "phase": "production",
        },
        "benefits": {
            "benefit_categories": ["processing throughput", "decision consistency"],
            "measurement_approach": "Compare median handling time and reversal rate month-over-month.",
        },
    }
    base.update(overrides)
    return base


def _tier_2_inputs(**overrides) -> dict:
    base = _tier_1_inputs(tier="tier-2")
    base.update({
        "tool_details": {
            "model_family": "gradient-boosted trees",
            "model_type": "binary classifier",
            "system_architecture": "batch scoring service behind internal API",
            "training_data_summary": "Five years of anonymised claims with outcome labels.",
            "model_performance_metrics": {"auc_roc": 0.87, "f1": 0.72},
            "third_party_components": ["xgboost v2.0"],
        },
        "impact_assessment": {
            "assessments_completed": ["DPIA-2026-03", "EIA-2026-03"],
            "citizen_impact_dimensions": ["financial", "access to benefits"],
            "severity": "medium",
            "affected_groups": ["working-age claimants", "disability claimants"],
            "consultation_summary": "Consulted with disability rights advocates Feb 2026.",
        },
        "data": {
            "source": "DWP internal claims database",
            "processing_basis": "UK GDPR Article 6(1)(e) public task",
            "data_categories": ["claim history", "household composition", "income"],
            "collection_method": "submitted on application forms",
            "sharing": [{"recipient": "HMRC", "purpose": "income verification"}],
            "retention": "7 years post-decision",
        },
        "risks": [
            {
                "category": "equity",
                "description": "Potential disparity across disability status.",
                "mitigation": "Equality Impact Assessment with quarterly monitoring.",
                "residual_risk": "low",
            },
            {
                "category": "data quality",
                "description": "Missing-field rate may bias scoring.",
                "mitigation": "Data completeness checks at ingestion.",
                "residual_risk": "low",
            },
            {
                "category": "explainability",
                "description": "Caseworkers may not understand score drivers.",
                "mitigation": "SHAP-value summaries displayed with each score.",
                "residual_risk": "medium",
            },
        ],
        "governance": {
            "oversight_body": "DWP AI Ethics Committee",
            "escalation_path": "Caseworker to Senior Caseworker to Ethics Committee",
            "review_cadence": "quarterly",
            "incident_response": "Incident Management Team with 48-hour SLA",
            "human_oversight_model": "caseworker-in-the-loop; tool does not auto-decide",
        },
    })
    base.update(overrides)
    return base


def test_tier_1_happy_path_returns_required_fields():
    result = plugin.generate_atrs_record(_tier_1_inputs())
    for f in (
        "timestamp", "agent_signature", "tier", "template_version",
        "source_url", "sections", "citations", "summary", "warnings",
    ):
        assert f in result
    assert result["tier"] == "tier-1"
    assert len(result["sections"]) == len(plugin.ATRS_SECTIONS)


def test_tier_2_happy_path_all_sections_populated():
    result = plugin.generate_atrs_record(_tier_2_inputs())
    assert result["tier"] == "tier-2"
    sections_by_name = {s["section"]: s for s in result["sections"]}
    for name in plugin.ATRS_SECTIONS:
        assert name in sections_by_name
    # Every required tier-2 section should have zero or few warnings.
    tool_details = sections_by_name["Tool details"]
    assert tool_details["content"]["model_family"] == "gradient-boosted trees"
    risks = sections_by_name["Risks"]
    assert len(risks["content"]["risks"]) == 3


def test_missing_tier_raises():
    inputs = _tier_1_inputs()
    del inputs["tier"]
    try:
        plugin.generate_atrs_record(inputs)
    except ValueError as exc:
        assert "tier" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_tool_description_raises():
    inputs = _tier_1_inputs()
    del inputs["tool_description"]
    try:
        plugin.generate_atrs_record(inputs)
    except ValueError as exc:
        assert "tool_description" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_owner_raises():
    inputs = _tier_1_inputs()
    del inputs["owner"]
    try:
        plugin.generate_atrs_record(inputs)
    except ValueError as exc:
        assert "owner" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_invalid_tier_raises():
    inputs = _tier_1_inputs(tier="tier-3")
    try:
        plugin.generate_atrs_record(inputs)
    except ValueError as exc:
        assert "tier" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_tier_2_missing_required_sections_warns():
    # Tier 2 without tool_details, impact_assessment, data, risks, governance.
    inputs = _tier_1_inputs(tier="tier-2")
    result = plugin.generate_atrs_record(inputs)
    record_warnings = " ".join(result["warnings"])
    assert "Tool details" in record_warnings
    assert "Impact assessment" in record_warnings
    assert "Data" in record_warnings
    assert "Risks" in record_warnings
    assert "Governance" in record_warnings


def test_impact_assessment_missing_assessments_warns():
    inputs = _tier_2_inputs()
    inputs["impact_assessment"] = {
        "citizen_impact_dimensions": ["financial"],
    }
    result = plugin.generate_atrs_record(inputs)
    ia = next(s for s in result["sections"] if s["section"] == "Impact assessment")
    text = " ".join(ia["warnings"])
    assert "assessments_completed" in text


def test_csv_header_and_row_count():
    result = plugin.generate_atrs_record(_tier_2_inputs())
    csv = plugin.render_csv(result)
    lines = csv.strip().split("\n")
    assert lines[0] == "section,citation,warning_count,content_summary"
    # Header + 8 sections.
    assert len(lines) == 1 + len(plugin.ATRS_SECTIONS)


def test_markdown_contains_every_section():
    result = plugin.generate_atrs_record(_tier_2_inputs())
    md = plugin.render_markdown(result)
    for name in plugin.ATRS_SECTIONS:
        assert f"## {name}" in md


def test_no_em_dash_no_emoji_no_hedging_in_output():
    result = plugin.generate_atrs_record(_tier_2_inputs())
    md = plugin.render_markdown(result)
    csv = plugin.render_csv(result)
    assert "\u2014" not in md
    assert "\u2014" not in csv
    # No emoji: scan for any char outside the Basic Multilingual Plane common range.
    emoji_pattern = re.compile(
        "[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u27BF]"
    )
    assert not emoji_pattern.search(md)
    assert not emoji_pattern.search(csv)
    hedging = [
        "may want to consider", "might be helpful to", "could potentially",
        "it is possible that", "you might find",
    ]
    md_lower = md.lower()
    for phrase in hedging:
        assert phrase not in md_lower


def test_citations_conform_to_uk_atrs_format():
    result = plugin.generate_atrs_record(_tier_2_inputs())
    pattern = re.compile(r"^UK ATRS, Section [A-Z].+$")
    # Every section's citation must match.
    for section in result["sections"]:
        for c in section["citations"]:
            assert pattern.match(c), f"bad citation: {c!r}"
    # Top-level citations include the URL, template version, and one per section.
    top = result["citations"]
    assert plugin.ATRS_STANDARD_URL in top
    assert plugin.ATRS_TEMPLATE_VERSION in top
    section_citations = [c for c in top if c.startswith("UK ATRS, Section ")]
    assert len(section_citations) == len(plugin.ATRS_SECTIONS)


def test_owner_missing_contact_point_warns():
    inputs = _tier_1_inputs()
    inputs["owner"] = {"organization": "DWP"}
    result = plugin.generate_atrs_record(inputs)
    owner_section = next(s for s in result["sections"] if s["section"] == "Owner and contact")
    text = " ".join(owner_section["warnings"])
    assert "contact_point" in text


def test_tool_description_missing_purpose_warns():
    inputs = _tier_1_inputs()
    inputs["tool_description"] = {"name": "X"}
    result = plugin.generate_atrs_record(inputs)
    td = next(s for s in result["sections"] if s["section"] == "Tool description")
    text = " ".join(td["warnings"])
    assert "purpose" in text


def test_top_level_citations_include_source_url():
    result = plugin.generate_atrs_record(_tier_1_inputs())
    assert plugin.ATRS_STANDARD_URL in result["citations"]
    assert plugin.ATRS_TEMPLATE_VERSION in result["citations"]


def _run_all():
    import inspect
    tests = [(n, o) for n, o in inspect.getmembers(sys.modules[__name__])
             if n.startswith("test_") and callable(o)]
    failures = []
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:
            failures.append((name, f"{type(exc).__name__}: {exc}"))
    print(f"Ran {len(tests)} tests: {len(tests) - len(failures)} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
