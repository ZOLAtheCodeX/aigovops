"""Tests for gap-assessment plugin."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _inventory() -> list:
    return [{"system_ref": "SYS-001", "system_name": "ResumeScreen"}]


def _iso_base() -> dict:
    return {"ai_system_inventory": _inventory(), "target_framework": "iso42001"}


def test_happy_path_iso_default_38_targets():
    result = plugin.generate_gap_assessment(_iso_base())
    assert result["target_framework"] == "iso42001"
    assert len(result["rows"]) == 38


def test_required_output_fields():
    result = plugin.generate_gap_assessment(_iso_base())
    for f in ("timestamp", "agent_signature", "target_framework", "citations", "rows", "summary", "warnings"):
        assert f in result


def test_iso_citation_format():
    result = plugin.generate_gap_assessment(_iso_base())
    for row in result["rows"]:
        assert row["citation"].startswith("ISO/IEC 42001:2023, Annex A, Control ")


def test_without_evidence_defaults_to_not_covered():
    result = plugin.generate_gap_assessment(_iso_base())
    # No evidence at all -> every row is not-covered with reviewer-decision marker
    assert all(r["classification"] == "not-covered" for r in result["rows"])
    assert all("REQUIRES REVIEWER DECISION" in r["justification"] for r in result["rows"])


def test_soa_rows_inform_coverage():
    inputs = _iso_base()
    inputs["soa_rows"] = [
        {"control_id": "A.5.4", "status": "included-implemented", "justification": "AISIA process active."},
        {"control_id": "A.7.4", "status": "included-partial", "justification": "Partial implementation."},
        {"control_id": "A.10.4", "status": "excluded", "justification": "No customer-facing AI."},
    ]
    result = plugin.generate_gap_assessment(inputs)
    by_id = {r["target_id"]: r for r in result["rows"]}
    assert by_id["A.5.4"]["classification"] == "covered"
    assert by_id["A.7.4"]["classification"] == "partially-covered"
    assert by_id["A.10.4"]["classification"] == "not-applicable"


def test_explicit_evidence_covers():
    inputs = _iso_base()
    inputs["current_state_evidence"] = {
        "A.6.2.3": ["DESIGN-DOC-2026-001"],
        "A.6.2.4": {"strength": "partial", "refs": ["V&V-REPORT-2026-Q1"]},
    }
    result = plugin.generate_gap_assessment(inputs)
    by_id = {r["target_id"]: r for r in result["rows"]}
    assert by_id["A.6.2.3"]["classification"] == "covered"
    assert by_id["A.6.2.4"]["classification"] == "partially-covered"


def test_manual_classification_overrides():
    inputs = _iso_base()
    inputs["manual_classifications"] = {
        "A.9.3": {"classification": "not-applicable", "justification": "Not used in this deployment."}
    }
    result = plugin.generate_gap_assessment(inputs)
    row = next(r for r in result["rows"] if r["target_id"] == "A.9.3")
    assert row["classification"] == "not-applicable"


def test_manual_classification_with_blank_justification_warns():
    inputs = _iso_base()
    inputs["manual_classifications"] = {"A.9.3": {"classification": "not-applicable", "justification": "   "}}
    result = plugin.generate_gap_assessment(inputs)
    row = next(r for r in result["rows"] if r["target_id"] == "A.9.3")
    assert any("blank justification" in w for w in row["warnings"])


def test_exclusion_justification_produces_not_applicable():
    inputs = _iso_base()
    inputs["exclusion_justifications"] = {"A.10.4": "No customer-facing AI."}
    result = plugin.generate_gap_assessment(inputs)
    row = next(r for r in result["rows"] if r["target_id"] == "A.10.4")
    assert row["classification"] == "not-applicable"


def test_blank_exclusion_warns_and_falls_through():
    inputs = _iso_base()
    inputs["exclusion_justifications"] = {"A.10.4": "   "}
    result = plugin.generate_gap_assessment(inputs)
    row = next(r for r in result["rows"] if r["target_id"] == "A.10.4")
    assert row["classification"] == "not-covered"
    assert any("blank" in w for w in row["warnings"])


def test_unknown_target_in_evidence_warns_register_level():
    inputs = _iso_base()
    inputs["current_state_evidence"] = {"A.99.99": ["FAKE-REF"]}
    result = plugin.generate_gap_assessment(inputs)
    assert any("A.99.99" in w for w in result["warnings"])


def test_nist_framework_requires_explicit_targets():
    inputs = {"ai_system_inventory": _inventory(), "target_framework": "nist"}
    try:
        plugin.generate_gap_assessment(inputs)
    except ValueError as exc:
        assert "targets" in str(exc).lower()
        return
    raise AssertionError("expected ValueError")


def test_nist_framework_with_targets_works():
    inputs = {
        "ai_system_inventory": _inventory(),
        "target_framework": "nist",
        "targets": [{"id": "GOVERN 1.1", "title": "Legal and regulatory requirements"}],
        "current_state_evidence": {"GOVERN 1.1": ["LEGAL-REGISTER-2026"]},
    }
    result = plugin.generate_gap_assessment(inputs)
    assert len(result["rows"]) == 1
    assert result["rows"][0]["classification"] == "covered"


def test_nist_citation_format():
    inputs = {
        "ai_system_inventory": _inventory(),
        "target_framework": "nist",
        "targets": [{"id": "MAP 4.1", "title": "Risk mapping"}],
    }
    result = plugin.generate_gap_assessment(inputs)
    assert result["rows"][0]["citation"] == "MAP 4.1"


def test_eu_ai_act_framework():
    inputs = {
        "ai_system_inventory": _inventory(),
        "target_framework": "eu-ai-act",
        "targets": [{"id": "Article 9", "title": "Risk management system"}],
    }
    result = plugin.generate_gap_assessment(inputs)
    assert result["rows"][0]["citation"] == "EU AI Act, Article 9"


def test_coverage_score_calculated():
    inputs = _iso_base()
    # Cover 19 of 38 fully, partial on 10, not-covered on 9
    inputs["current_state_evidence"] = {
        t["id"]: ["EV-REF"] for t in plugin.DEFAULT_ISO_TARGETS[:19]
    }
    inputs["current_state_evidence"].update({
        t["id"]: {"strength": "partial", "refs": ["EV-PARTIAL"]}
        for t in plugin.DEFAULT_ISO_TARGETS[19:29]
    })
    result = plugin.generate_gap_assessment(inputs)
    score = result["summary"]["coverage_score"]
    # covered=19, partial=10, not-covered=9. N/A=0. Score = (19 + 0.5*10) / (19+10+9) = 24/38 ≈ 0.632
    assert 0.62 < score < 0.65


def test_invalid_framework_raises():
    try:
        plugin.generate_gap_assessment({**_iso_base(), "target_framework": "cobit"})
    except ValueError as exc:
        assert "target_framework" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_invalid_manual_classification_raises():
    inputs = _iso_base()
    inputs["manual_classifications"] = {"A.5.4": "not-a-real-classification"}
    try:
        plugin.generate_gap_assessment(inputs)
    except ValueError as exc:
        assert "classification" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_classification_counts_correct():
    inputs = _iso_base()
    inputs["soa_rows"] = [
        {"control_id": "A.5.4", "status": "included-implemented"},
        {"control_id": "A.7.4", "status": "included-partial"},
        {"control_id": "A.10.4", "status": "excluded", "justification": "OOS"},
    ]
    result = plugin.generate_gap_assessment(inputs)
    counts = result["summary"]["classification_counts"]
    assert counts["covered"] == 1
    assert counts["partially-covered"] == 1
    assert counts["not-applicable"] == 1
    assert counts["not-covered"] == 35


def test_render_markdown_sections():
    result = plugin.generate_gap_assessment(_iso_base())
    md = plugin.render_markdown(result)
    for s in ("# Gap Assessment: iso42001", "## Summary", "## Applicable Citations", "## Gaps by classification"):
        assert s in md


def test_render_csv_header_and_row_count():
    inputs = _iso_base()
    inputs["surface_crosswalk_gaps"] = False
    result = plugin.generate_gap_assessment(inputs)
    csv = plugin.render_csv(result)
    lines = csv.strip().split("\n")
    assert lines[0].startswith("target_id,target_title,citation,classification")
    assert len(lines) == 39  # header + 38 rows


def test_custom_iso_targets_respected():
    inputs = _iso_base()
    inputs["targets"] = [
        {"id": "A.2.2", "title": "AI policy"},
        {"id": "A.6.2.8", "title": "AI system log recording"},
    ]
    result = plugin.generate_gap_assessment(inputs)
    assert len(result["rows"]) == 2


def test_surface_crosswalk_gaps_default_is_true():
    result = plugin.generate_gap_assessment(_iso_base())
    assert "crosswalk_gaps_surfaced" in result
    assert isinstance(result["crosswalk_gaps_surfaced"], list)


def test_surface_crosswalk_gaps_false_skips():
    inputs = _iso_base()
    inputs["surface_crosswalk_gaps"] = False
    result = plugin.generate_gap_assessment(inputs)
    assert "crosswalk_gaps_surfaced" not in result


def test_crosswalk_gaps_for_iso_target_includes_eu_gaps():
    inputs = _iso_base()
    inputs["crosswalk_reference_frameworks"] = ["eu-ai-act"]
    result = plugin.generate_gap_assessment(inputs)
    surfaced = result["crosswalk_gaps_surfaced"]
    eu_beyond_iso = [
        e for e in surfaced
        if e["reference_framework"] == "eu-ai-act"
        and e["direction"] == "reference-beyond-target"
    ]
    assert eu_beyond_iso, "expected at least one eu-ai-act reference-beyond-target entry"
    assert eu_beyond_iso[0]["gap_count"] >= 1
    assert eu_beyond_iso[0]["gaps"]
    first_gap = eu_beyond_iso[0]["gaps"][0]
    for key in ("source_ref", "source_title", "notes", "citation"):
        assert key in first_gap


def test_invalid_reference_framework_raises():
    inputs = _iso_base()
    inputs["crosswalk_reference_frameworks"] = ["not-a-real-framework"]
    try:
        plugin.generate_gap_assessment(inputs)
    except ValueError as exc:
        assert "crosswalk_reference_frameworks" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_graceful_failure_when_crosswalk_missing():
    # Simulate broken crosswalk load by monkey-patching the loader.
    original_loader = plugin._load_crosswalk_module
    original_cache = plugin._CROSSWALK_MODULE_CACHE
    plugin._CROSSWALK_MODULE_CACHE = None

    def _broken_loader():
        raise FileNotFoundError("simulated missing crosswalk plugin")

    plugin._load_crosswalk_module = _broken_loader
    try:
        result = plugin.generate_gap_assessment(_iso_base())
    finally:
        plugin._load_crosswalk_module = original_loader
        plugin._CROSSWALK_MODULE_CACHE = original_cache

    assert "crosswalk_gaps_surfaced" in result
    assert result["crosswalk_gaps_surfaced"] == []
    assert any(
        "Crosswalk gap surfacing skipped" in w for w in result["warnings"]
    )


def test_no_em_dashes_in_output():
    result = plugin.generate_gap_assessment(_iso_base())
    md = plugin.render_markdown(result)
    csv = plugin.render_csv(result)
    assert "\u2014" not in md
    assert "\u2014" not in csv


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
