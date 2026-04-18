"""Tests for the soa-generator plugin. Runs under pytest or standalone."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _inventory() -> list:
    return [{"system_ref": "SYS-001", "system_name": "ResumeScreen", "risk_tier": "limited"}]


def _base_inputs() -> dict:
    return {"ai_system_inventory": _inventory()}


def test_happy_path_returns_required_fields():
    result = plugin.generate_soa(_base_inputs())
    for f in ("timestamp", "agent_signature", "citations", "rows", "summary", "warnings"):
        assert f in result


def test_default_produces_38_rows():
    result = plugin.generate_soa(_base_inputs())
    assert len(result["rows"]) == 38


def test_all_default_controls_present():
    result = plugin.generate_soa(_base_inputs())
    ids = [r["control_id"] for r in result["rows"]]
    assert "A.2.2" in ids
    assert "A.10.4" in ids
    assert len(set(ids)) == len(ids)  # no duplicates


def test_every_row_has_citation():
    result = plugin.generate_soa(_base_inputs())
    for row in result["rows"]:
        assert row["citation"].startswith("ISO/IEC 42001:2023, Annex A, Control ")


def test_empty_risk_register_emits_register_level_warning():
    result = plugin.generate_soa(_base_inputs())
    text = " ".join(result["warnings"])
    assert "risk register" in text.lower() or "risk_register" in text.lower()


def test_linked_risk_register_marks_included_implemented():
    inputs = _base_inputs()
    inputs["risk_register"] = [{
        "id": "RR-0001",
        "existing_controls": [{"control_id": "A.7.4"}],
    }]
    result = plugin.generate_soa(inputs)
    a_7_4 = next(r for r in result["rows"] if r["control_id"] == "A.7.4")
    assert a_7_4["status"] == "included-implemented"
    assert "RR-0001" in a_7_4["linked_risks"]


def test_exclusion_justification_produces_excluded_status():
    inputs = _base_inputs()
    inputs["exclusion_justifications"] = {
        "A.10.4": "No customer-facing AI services in AIMS scope per ai_system_inventory."
    }
    result = plugin.generate_soa(inputs)
    a_10_4 = next(r for r in result["rows"] if r["control_id"] == "A.10.4")
    assert a_10_4["status"] == "excluded"
    assert "customer-facing" in a_10_4["justification"]


def test_exclusion_with_blank_justification_warns():
    inputs = _base_inputs()
    inputs["exclusion_justifications"] = {"A.10.4": "   "}
    result = plugin.generate_soa(inputs)
    a_10_4 = next(r for r in result["rows"] if r["control_id"] == "A.10.4")
    assert a_10_4["status"] == "excluded"
    warning_text = " ".join(a_10_4["warnings"])
    assert "blank" in warning_text.lower() or "justification" in warning_text.lower()


def test_implementation_plan_produces_planned_status():
    inputs = _base_inputs()
    inputs["implementation_plans"] = {
        "A.4.3": {"plan_ref": "PLAN-DATA-2026Q3", "target_date": "2026-09-30", "status": "planned"}
    }
    result = plugin.generate_soa(inputs)
    a_4_3 = next(r for r in result["rows"] if r["control_id"] == "A.4.3")
    assert a_4_3["status"] == "included-planned"
    assert a_4_3["implementation_plan_ref"] == "PLAN-DATA-2026Q3"


def test_partial_implementation_status():
    inputs = _base_inputs()
    inputs["implementation_plans"] = {
        "A.5.4": {"plan_ref": "PLAN-AISIA-2026Q2", "target_date": "2026-06-30", "status": "partial"}
    }
    result = plugin.generate_soa(inputs)
    row = next(r for r in result["rows"] if r["control_id"] == "A.5.4")
    assert row["status"] == "included-partial"


def test_planned_without_target_date_warns():
    inputs = _base_inputs()
    inputs["implementation_plans"] = {"A.4.3": {"plan_ref": "PLAN-INCOMPLETE"}}
    result = plugin.generate_soa(inputs)
    row = next(r for r in result["rows"] if r["control_id"] == "A.4.3")
    warning_text = " ".join(row["warnings"])
    assert "target_date" in warning_text


def test_unknown_control_in_exclusion_justifications_warns():
    inputs = _base_inputs()
    inputs["exclusion_justifications"] = {"A.99.99": "fake control"}
    result = plugin.generate_soa(inputs)
    warning_text = " ".join(result["warnings"])
    assert "A.99.99" in warning_text


def test_no_evidence_defaults_to_excluded_with_warning():
    inputs = _base_inputs()
    result = plugin.generate_soa(inputs)
    # Without risk register, plans, or exclusions, every control is excluded-with-review-required.
    unresolved = [r for r in result["rows"] if "REQUIRES REVIEWER DECISION" in r["justification"]]
    assert len(unresolved) == 38


def test_scope_note_attached_when_provided():
    inputs = _base_inputs()
    inputs["scope_notes"] = {"A.5.4": "Applies to SYS-001 ResumeScreen only."}
    result = plugin.generate_soa(inputs)
    row = next(r for r in result["rows"] if r["control_id"] == "A.5.4")
    assert "ResumeScreen" in row["scope_note"]


def test_status_counts_in_summary():
    inputs = _base_inputs()
    inputs["exclusion_justifications"] = {"A.10.4": "Out of scope"}
    inputs["implementation_plans"] = {
        "A.5.4": {"plan_ref": "P1", "target_date": "2026-06-30", "status": "planned"}
    }
    inputs["risk_register"] = [{"id": "RR-0001", "existing_controls": [{"control_id": "A.7.4"}]}]
    result = plugin.generate_soa(inputs)
    counts = result["summary"]["status_counts"]
    assert counts["included-implemented"] == 1
    assert counts["included-planned"] == 1
    assert counts["excluded"] >= 2


def test_custom_annex_a_controls_respected():
    inputs = _base_inputs()
    inputs["annex_a_controls"] = [
        {"control_id": "A.2.2", "control_title": "AI policy"},
        {"control_id": "A.6.2.8", "control_title": "AI system log recording"},
    ]
    result = plugin.generate_soa(inputs)
    assert len(result["rows"]) == 2


def test_missing_ai_system_inventory_raises():
    try:
        plugin.generate_soa({})
    except ValueError as exc:
        assert "ai_system_inventory" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_annex_a_entry_must_have_control_id():
    inputs = _base_inputs()
    inputs["annex_a_controls"] = [{"control_title": "Missing ID"}]
    try:
        plugin.generate_soa(inputs)
    except ValueError as exc:
        assert "control_id" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_render_markdown_has_required_sections():
    result = plugin.generate_soa(_base_inputs())
    md = plugin.render_markdown(result)
    for section in ("# Statement of Applicability", "## Summary", "## Applicable Citation", "## Rows"):
        assert section in md


def test_render_csv_header_and_rows():
    result = plugin.generate_soa(_base_inputs())
    csv = plugin.render_csv(result)
    lines = csv.strip().split("\n")
    assert lines[0].startswith("control_id,control_title,status")
    assert len(lines) == 39  # header + 38 rows


def test_no_em_dashes_in_output():
    result = plugin.generate_soa(_base_inputs())
    md = plugin.render_markdown(result)
    csv = plugin.render_csv(result)
    assert "\u2014" not in md
    assert "\u2014" not in csv


def test_citation_format_matches_style_md():
    result = plugin.generate_soa(_base_inputs())
    for row in result["rows"]:
        assert row["citation"].startswith("ISO/IEC 42001:2023, Annex A, Control ")


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
