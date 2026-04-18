"""Tests for the aisia-runner plugin. Runs under pytest or standalone."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _system() -> dict:
    return {
        "system_name": "ED-Triage-Assist",
        "purpose": "Suggest ED triage acuity (ESI 1-5) from chief complaint and vitals.",
        "intended_use": "Decision support for triage RN; RN assigns final acuity.",
        "decision_authority": "decision-support",
        "deployment_environment": "Tertiary-care hospital ED.",
        "system_type": "classical-ml",
    }


def _stakeholders() -> list:
    return [
        "Presenting patients",
        "ED clinical staff",
        {"name": "Protected patient subgroups", "protected_attributes": ["age", "race", "primary-language"]},
    ]


def _base_inputs() -> dict:
    return {
        "system_description": _system(),
        "affected_stakeholders": _stakeholders(),
        "impact_assessments": [
            {
                "stakeholder_group": "Presenting patients",
                "impact_dimension": "physical-safety",
                "impact_description": "Incorrect triage acuity could delay emergent care.",
                "severity": "major",
                "likelihood": "unlikely",
                "existing_controls": ["A.6.2.4"],
                "residual_severity": "moderate",
                "residual_likelihood": "unlikely",
                "assessor": "Clinical Informatics",
                "assessment_date": "2026-04-01",
            },
        ],
    }


def test_happy_path_returns_required_fields():
    result = plugin.run_aisia(_base_inputs())
    for f in ("timestamp", "agent_signature", "system_name", "citations", "sections", "summary"):
        assert f in result


def test_section_includes_iso_citations_by_default():
    result = plugin.run_aisia(_base_inputs())
    s = result["sections"][0]
    assert any("Clause 6.1.4" in c for c in s["citations"])
    assert any("A.5.2" in c for c in s["citations"])


def test_physical_safety_dimension_cites_a_5_4():
    result = plugin.run_aisia(_base_inputs())
    s = result["sections"][0]
    assert any("A.5.4" in c for c in s["citations"])


def test_societal_dimension_cites_a_5_5():
    inputs = _base_inputs()
    inputs["impact_assessments"] = [{
        "stakeholder_group": "ED clinical staff",
        "impact_dimension": "societal",
        "impact_description": "Staff workload effects.",
        "severity": "minor",
        "likelihood": "possible",
        "existing_controls": ["A.6.2.6"],
    }]
    result = plugin.run_aisia(inputs)
    s = result["sections"][0]
    assert any("A.5.5" in c for c in s["citations"])


def test_nist_framework_emits_map_citations():
    inputs = _base_inputs()
    inputs["framework"] = "nist"
    result = plugin.run_aisia(inputs)
    s = result["sections"][0]
    assert "MAP 1.1" in s["citations"]
    assert not any("ISO/IEC 42001" in c for c in s["citations"])


def test_nist_physical_safety_adds_measure_2_6():
    inputs = _base_inputs()
    inputs["framework"] = "nist"
    result = plugin.run_aisia(inputs)
    s = result["sections"][0]
    assert "MEASURE 2.6" in s["citations"]


def test_dual_framework_carries_both_citation_families():
    inputs = _base_inputs()
    inputs["framework"] = "dual"
    result = plugin.run_aisia(inputs)
    s = result["sections"][0]
    assert "MAP 1.1" in s["citations"]
    assert any("Clause 6.1.4" in c for c in s["citations"])


def test_physical_safety_severity_floor_warning():
    inputs = _base_inputs()
    inputs["impact_assessments"][0]["severity"] = "minor"  # below moderate
    result = plugin.run_aisia(inputs)
    text = " ".join(result["sections"][0]["warnings"])
    assert "moderate" in text.lower()


def test_missing_severity_surfaces_warning():
    inputs = _base_inputs()
    del inputs["impact_assessments"][0]["severity"]
    result = plugin.run_aisia(inputs)
    text = " ".join(result["sections"][0]["warnings"])
    assert "severity" in text.lower()


def test_empty_impact_description_warns():
    inputs = _base_inputs()
    inputs["impact_assessments"][0]["impact_description"] = ""
    result = plugin.run_aisia(inputs)
    text = " ".join(result["sections"][0]["warnings"])
    assert "description" in text.lower()


def test_no_controls_present_warns():
    inputs = _base_inputs()
    inputs["impact_assessments"][0]["existing_controls"] = []
    inputs["impact_assessments"][0].pop("additional_controls_recommended", None)
    result = plugin.run_aisia(inputs)
    text = " ".join(result["sections"][0]["warnings"])
    assert "control" in text.lower()


def test_unknown_stakeholder_warns():
    inputs = _base_inputs()
    inputs["impact_assessments"][0]["stakeholder_group"] = "Not in list"
    result = plugin.run_aisia(inputs)
    text = " ".join(result["sections"][0]["warnings"])
    assert "Not in list" in text


def test_soa_linking_when_rows_provided():
    inputs = _base_inputs()
    inputs["soa_rows"] = [{"control_id": "A.6.2.4", "row_ref": "SOA-ROW-004"}]
    result = plugin.run_aisia(inputs)
    ctrl = result["sections"][0]["existing_controls"][0]
    assert ctrl["soa_row_ref"] == "SOA-ROW-004"


def test_scaffold_emits_gaps_per_stakeholder_dimension():
    inputs = _base_inputs()
    inputs["scaffold"] = True
    result = plugin.run_aisia(inputs)
    # 3 stakeholders x 4 dimensions - 1 provided = 11 scaffold entries
    assert len(result["scaffold_sections"]) == 11


def test_scaffold_off_by_default():
    result = plugin.run_aisia(_base_inputs())
    assert result["scaffold_sections"] == []


def test_empty_impact_assessments_warns():
    inputs = _base_inputs()
    inputs["impact_assessments"] = []
    result = plugin.run_aisia(inputs)
    text = " ".join(result["warnings"])
    assert "empty" in text.lower() or "no impact" in text.lower()


def test_missing_system_description_raises():
    try:
        plugin.run_aisia({"affected_stakeholders": ["A"]})
    except ValueError as exc:
        assert "system_description" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_stakeholders_raises():
    try:
        plugin.run_aisia({"system_description": _system(), "affected_stakeholders": []})
    except ValueError as exc:
        assert "affected_stakeholders" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_invalid_framework_raises():
    inputs = _base_inputs()
    inputs["framework"] = "cobit"
    try:
        plugin.run_aisia(inputs)
    except ValueError as exc:
        assert "framework" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_stakeholder_group_in_entry_raises():
    inputs = _base_inputs()
    del inputs["impact_assessments"][0]["stakeholder_group"]
    try:
        plugin.run_aisia(inputs)
    except ValueError as exc:
        assert "stakeholder_group" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_render_markdown_has_required_sections():
    result = plugin.run_aisia(_base_inputs())
    md = plugin.render_markdown(result)
    for s in ("# AI System Impact Assessment:", "## Summary", "## Applicable Citations", "## Sections"):
        assert s in md


def test_render_markdown_includes_impact_description():
    result = plugin.run_aisia(_base_inputs())
    md = plugin.render_markdown(result)
    assert "Incorrect triage acuity" in md


def test_output_no_em_dashes():
    result = plugin.run_aisia(_base_inputs())
    md = plugin.render_markdown(result)
    assert "\u2014" not in md


def _run_all():
    import inspect
    tests = [(n, o) for n, o in inspect.getmembers(sys.modules[__name__]) if n.startswith("test_") and callable(o)]
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
