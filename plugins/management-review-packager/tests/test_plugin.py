"""Tests for the management-review-packager plugin."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _window() -> dict:
    return {"start": "2026-01-01", "end": "2026-03-31"}


def _attendees() -> list:
    return ["Chief Risk Officer", "AI Governance Officer", "DPO"]


def _base_inputs() -> dict:
    return {"review_window": _window(), "attendees": _attendees()}


def test_happy_path_required_fields():
    result = plugin.generate_review_package(_base_inputs())
    for f in ("timestamp", "agent_signature", "citations", "sections", "distribution_hook", "summary", "warnings"):
        assert f in result


def test_all_nine_clause_9_3_2_categories_present():
    result = plugin.generate_review_package(_base_inputs())
    assert len(result["sections"]) == 9


def test_unpopulated_categories_surface_warnings():
    result = plugin.generate_review_package(_base_inputs())
    # No inputs supplied for any category => 9 warnings
    assert len([w for w in result["warnings"] if "not populated" in w]) == 9
    for section in result["sections"]:
        assert not section["populated"]


def test_populated_category_no_warning():
    inputs = _base_inputs()
    inputs["previous_review_actions"] = "MR-2025-Q4-action-log"
    result = plugin.generate_review_package(inputs)
    prev = next(s for s in result["sections"] if s["key"] == "previous_review_actions")
    assert prev["populated"] is True
    assert prev["source_ref"] == "MR-2025-Q4-action-log"


def test_dict_input_captures_trend_and_breach_flags():
    inputs = _base_inputs()
    inputs["aims_performance"] = {
        "source_ref": "KPI-report-2026-Q1",
        "trend_direction": "stable",
        "breach_flags": ["latency-p95-over-target"],
    }
    result = plugin.generate_review_package(inputs)
    perf = next(s for s in result["sections"] if s["key"] == "aims_performance")
    assert perf["populated"]
    assert perf["trend_direction"] == "stable"
    assert "latency-p95-over-target" in perf["breach_flags"]


def test_distribution_hook_has_citation_and_list():
    result = plugin.generate_review_package(_base_inputs())
    hook = result["distribution_hook"]
    assert hook["event"] == "management-review-input-package-distributed"
    assert hook["citation"] == "ISO/IEC 42001:2023, Clause 7.5.3"
    assert hook["distribution_list"] == _attendees()


def test_summary_populated_counts():
    inputs = _base_inputs()
    inputs["previous_review_actions"] = "x"
    inputs["audit_results"] = "y"
    result = plugin.generate_review_package(inputs)
    assert result["summary"]["populated_categories"] == 2
    assert result["summary"]["unpopulated_categories"] == 7


def test_missing_review_window_raises():
    try:
        plugin.generate_review_package({"attendees": _attendees()})
    except ValueError as exc:
        assert "review_window" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_empty_attendees_raises():
    try:
        plugin.generate_review_package({"review_window": _window(), "attendees": []})
    except ValueError as exc:
        assert "attendees" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_malformed_review_window_raises():
    try:
        plugin.generate_review_package({"review_window": {"start": "2026-01-01"}, "attendees": _attendees()})
    except ValueError as exc:
        assert "review_window" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_section_ordering_matches_clause_order():
    result = plugin.generate_review_package(_base_inputs())
    keys = [s["key"] for s in result["sections"]]
    expected = [c[0] for c in plugin.INPUT_CATEGORIES]
    assert keys == expected


def test_every_section_carries_citation():
    result = plugin.generate_review_package(_base_inputs())
    for section in result["sections"]:
        assert "citation" in section
        assert section["citation"]  # non-empty


def test_render_markdown_sections():
    inputs = _base_inputs()
    inputs["previous_review_actions"] = "MR-2025-Q4"
    result = plugin.generate_review_package(inputs)
    md = plugin.render_markdown(result)
    for s in ("# Management Review Input Package", "## Attendees", "## Applicable Citations", "## Summary", "## Input Categories", "## Distribution audit-log hook"):
        assert s in md


def test_render_markdown_lists_attendees():
    result = plugin.generate_review_package(_base_inputs())
    md = plugin.render_markdown(result)
    for a in _attendees():
        assert a in md


def test_render_markdown_has_warnings_when_empty():
    result = plugin.generate_review_package(_base_inputs())
    md = plugin.render_markdown(result)
    assert "## Warnings" in md


def test_no_em_dashes_in_output():
    inputs = _base_inputs()
    inputs["previous_review_actions"] = "x"
    result = plugin.generate_review_package(inputs)
    md = plugin.render_markdown(result)
    assert "\u2014" not in md


def test_list_input_populated_preserved_as_items():
    inputs = _base_inputs()
    inputs["stakeholder_feedback"] = ["Customer advocate concern A", "Regulator inquiry B"]
    result = plugin.generate_review_package(inputs)
    feedback = next(s for s in result["sections"] if s["key"] == "stakeholder_feedback")
    assert feedback["populated"]
    assert feedback["items"] == ["Customer advocate concern A", "Regulator inquiry B"]


def test_include_crosswalk_coverage_default_true():
    result = plugin.generate_review_package(_base_inputs())
    assert "cross_framework_coverage" in result
    cfc = result["cross_framework_coverage"]
    assert cfc["target_frameworks"] == ["nist-ai-rmf", "eu-ai-act", "uk-atrs"]
    assert len(cfc["per_framework_summary"]) == 3


def test_include_crosswalk_coverage_false_skips():
    inputs = _base_inputs()
    inputs["include_crosswalk_coverage"] = False
    result = plugin.generate_review_package(inputs)
    assert "cross_framework_coverage" not in result


def test_coverage_counts_sum_correctly():
    result = plugin.generate_review_package(_base_inputs())
    per_fw = result["cross_framework_coverage"]["per_framework_summary"]
    assert per_fw, "expected at least one per_framework_summary entry"
    totals = set()
    for entry in per_fw:
        total = (
            entry["iso_annex_a_controls_covered"]
            + entry["iso_annex_a_controls_partial"]
            + entry["iso_annex_a_controls_gaps"]
        )
        assert total > 0, f"expected non-zero total for {entry['target_framework']}"
        if total:
            covered = entry["iso_annex_a_controls_covered"]
            expected_pct = round(covered / total * 100, 1)
            assert entry["coverage_percentage"] == expected_pct
        totals.add(total)
    # Per-framework totals need not all be identical because the crosswalk
    # YAMLs cover different ISO control subsets; assert each is internally
    # consistent which is what the coverage math requires.


def test_top_gaps_lists_uncovered_iso_controls():
    inputs = _base_inputs()
    inputs["crosswalk_target_frameworks"] = ["eu-ai-act"]
    result = plugin.generate_review_package(inputs)
    per_fw = result["cross_framework_coverage"]["per_framework_summary"]
    eu_entry = next(e for e in per_fw if e["target_framework"] == "eu-ai-act")
    # A.2.4 has no-mapping to eu-ai-act in iso42001-eu-ai-act.yaml.
    assert "A.2.4" in eu_entry["top_gaps"]
    assert eu_entry["iso_annex_a_controls_gaps"] >= 1


def test_graceful_failure(monkeypatch=None):
    # Force the crosswalk loader to raise; the package must still render.
    original = plugin._load_crosswalk_module

    def _boom():
        raise RuntimeError("simulated crosswalk failure")

    plugin._load_crosswalk_module = _boom
    try:
        result = plugin.generate_review_package(_base_inputs())
    finally:
        plugin._load_crosswalk_module = original
    # cross_framework_coverage is absent because enrichment failed.
    assert "cross_framework_coverage" not in result
    # A warning was emitted naming the failure.
    assert any(
        "Cross-framework coverage skipped" in w for w in result["warnings"]
    )
    # Markdown still renders.
    md = plugin.render_markdown(result)
    assert "# Management Review Input Package" in md


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
