"""Tests for data-register-builder plugin."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _minimal_dataset(**kwargs) -> dict:
    base = {
        "id": "DS-001",
        "name": "CandidateResumeCorpus-2026Q1",
        "purpose_stage": "training",
        "source": "internal",
        "system_refs": ["SYS-001"],
        "acquisition_method": "collected from internal ATS 2024-2026",
        "provenance_chain": [
            {"step": "extract", "tool": "ATS API"},
            {"step": "dedupe"},
            {"step": "redact PII"},
        ],
        "quality_checks": {
            "accuracy": {"status": "pass", "method": "sample audit"},
            "completeness": {"status": "pass"},
            "consistency": {"status": "pass"},
            "currency": {"status": "pass"},
            "validity": {"status": "pass"},
        },
        "representativeness_assessment": "Verified population coverage vs. US Bureau of Labor Statistics",
        "bias_assessment": {"examined_for_bias": True, "mitigation": "rebalanced"},
        "data_preparation_steps": ["dedupe", "redact PII", "tokenize"],
        "protected_attributes": ["age-range", "ethnicity-self-reported"],
        "data_category": "internal-sourced",
        "collection_date": "2025-12-01T00:00:00Z",
        "owner_role": "Data Protection Officer",
    }
    base.update(kwargs)
    return base


def _base_inputs(**kwargs) -> dict:
    base = {
        "data_inventory": [_minimal_dataset()],
        "ai_system_inventory": [{"system_ref": "SYS-001", "risk_tier": "limited"}],
        "retention_policy": {"internal-sourced": 730, "default": 365},
    }
    base.update(kwargs)
    return base


def test_happy_path_returns_required_fields():
    result = plugin.generate_data_register(_base_inputs())
    for f in ("timestamp", "agent_signature", "framework", "citations", "rows", "summary", "warnings"):
        assert f in result


def test_iso_framework_citations():
    result = plugin.generate_data_register(_base_inputs())
    row = result["rows"][0]
    assert "ISO/IEC 42001:2023, Annex A, Control A.7.2" in row["citations"]
    assert "ISO/IEC 42001:2023, Annex A, Control A.7.4" in row["citations"]


def test_eu_framework_cites_article_10():
    result = plugin.generate_data_register(_base_inputs(framework="eu-ai-act"))
    row = result["rows"][0]
    assert "EU AI Act, Article 10, Paragraph 1" in row["citations"]
    assert "EU AI Act, Article 10, Paragraph 3" in row["citations"]


def test_dual_framework_cites_both():
    result = plugin.generate_data_register(_base_inputs(framework="dual"))
    row = result["rows"][0]
    assert "ISO/IEC 42001:2023, Annex A, Control A.7.2" in row["citations"]
    assert "EU AI Act, Article 10, Paragraph 1" in row["citations"]


def test_retention_expiry_computed():
    result = plugin.generate_data_register(_base_inputs())
    row = result["rows"][0]
    # 2025-12-01 + 730 days = 2027-12-01 (approximately)
    assert row["retention_expiry_date"] is not None
    assert "2027-12-01" in row["retention_expiry_date"]


def test_high_risk_training_without_bias_warns():
    inputs = _base_inputs(framework="eu-ai-act")
    inputs["ai_system_inventory"] = [{"system_ref": "SYS-001", "risk_tier": "high"}]
    ds = _minimal_dataset()
    del ds["bias_assessment"]
    inputs["data_inventory"] = [ds]
    result = plugin.generate_data_register(inputs)
    text = " ".join(result["rows"][0]["warnings"])
    assert "bias_assessment" in text
    assert "Article 10(5)" in text


def test_scraped_training_for_high_risk_warns():
    inputs = _base_inputs(framework="eu-ai-act")
    inputs["ai_system_inventory"] = [{"system_ref": "SYS-001", "risk_tier": "high"}]
    inputs["data_inventory"] = [_minimal_dataset(source="scraped")]
    result = plugin.generate_data_register(inputs)
    text = " ".join(result["rows"][0]["warnings"])
    assert "scraping" in text.lower() or "scraped" in text.lower()
    assert "Article 10(2)" in text


def test_missing_quality_dimensions_warns():
    ds = _minimal_dataset()
    ds["quality_checks"] = {"accuracy": {"status": "pass"}}  # missing 4 dimensions
    inputs = _base_inputs()
    inputs["data_inventory"] = [ds]
    result = plugin.generate_data_register(inputs)
    text = " ".join(result["rows"][0]["warnings"])
    assert "quality_checks" in text
    assert "completeness" in text or "consistency" in text


def test_failed_quality_dimension_warns():
    ds = _minimal_dataset()
    ds["quality_checks"]["completeness"] = {"status": "fail", "detail": "missing 3% of labels"}
    inputs = _base_inputs()
    inputs["data_inventory"] = [ds]
    result = plugin.generate_data_register(inputs)
    text = " ".join(result["rows"][0]["warnings"])
    assert "completeness" in text
    assert "failed" in text.lower()


def test_missing_provenance_warns():
    ds = _minimal_dataset()
    del ds["provenance_chain"]
    inputs = _base_inputs()
    inputs["data_inventory"] = [ds]
    result = plugin.generate_data_register(inputs)
    text = " ".join(result["rows"][0]["warnings"])
    assert "provenance" in text.lower()


def test_missing_representativeness_for_training_eu_warns():
    ds = _minimal_dataset()
    del ds["representativeness_assessment"]
    inputs = _base_inputs(framework="eu-ai-act")
    inputs["data_inventory"] = [ds]
    result = plugin.generate_data_register(inputs)
    text = " ".join(result["rows"][0]["warnings"])
    assert "representativeness" in text.lower()
    assert "Article 10(3)" in text


def test_missing_acquisition_method_warns_for_training():
    ds = _minimal_dataset()
    del ds["acquisition_method"]
    inputs = _base_inputs()
    inputs["data_inventory"] = [ds]
    result = plugin.generate_data_register(inputs)
    text = " ".join(result["rows"][0]["warnings"])
    assert "acquisition_method" in text
    assert "A.7.3" in text


def test_protected_attrs_without_bias_assessment_warns():
    ds = _minimal_dataset()
    del ds["bias_assessment"]
    inputs = _base_inputs()
    inputs["data_inventory"] = [ds]
    result = plugin.generate_data_register(inputs)
    text = " ".join(result["rows"][0]["warnings"])
    assert "protected attributes" in text


def test_missing_owner_warns_unless_role_matrix():
    ds = _minimal_dataset()
    del ds["owner_role"]
    inputs = _base_inputs()
    inputs["data_inventory"] = [ds]
    inputs["role_matrix_lookup"] = {}
    result = plugin.generate_data_register(inputs)
    text = " ".join(result["rows"][0]["warnings"])
    assert "owner_role" in text


def test_owner_lookup_from_role_matrix():
    ds = _minimal_dataset()
    del ds["owner_role"]
    inputs = _base_inputs()
    inputs["data_inventory"] = [ds]
    inputs["role_matrix_lookup"] = {"data_governance": "Data Protection Officer"}
    result = plugin.generate_data_register(inputs)
    assert result["rows"][0]["owner_role"] == "Data Protection Officer"


def test_invalid_purpose_stage_raises():
    try:
        plugin.generate_data_register(_base_inputs(
            data_inventory=[_minimal_dataset(purpose_stage="meditation")]
        ))
    except ValueError as exc:
        assert "purpose_stage" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_invalid_source_raises():
    try:
        plugin.generate_data_register(_base_inputs(
            data_inventory=[_minimal_dataset(source="mystery-source")]
        ))
    except ValueError as exc:
        assert "source" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_invalid_framework_raises():
    try:
        plugin.generate_data_register(_base_inputs(framework="cobit"))
    except ValueError as exc:
        assert "framework" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_required_field_raises():
    bad = _minimal_dataset()
    del bad["id"]
    try:
        plugin.generate_data_register(_base_inputs(data_inventory=[bad]))
    except ValueError as exc:
        assert "id" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_empty_inventory_surfaces_warning():
    result = plugin.generate_data_register(_base_inputs(data_inventory=[]))
    text = " ".join(result["warnings"])
    assert "no datasets" in text.lower() or "empty" in text.lower()


def test_inference_stage_minimal_requirements():
    # Inference data doesn't need quality checks or representativeness.
    ds = _minimal_dataset(
        purpose_stage="inference",
        id="DS-INF-001",
    )
    ds.pop("quality_checks", None)
    ds.pop("representativeness_assessment", None)
    ds.pop("acquisition_method", None)
    inputs = _base_inputs(data_inventory=[ds])
    result = plugin.generate_data_register(inputs)
    # No quality/representativeness warnings expected for inference.
    row = result["rows"][0]
    warning_text = " ".join(row["warnings"])
    assert "quality_checks" not in warning_text
    assert "representativeness" not in warning_text


def test_render_markdown_sections():
    result = plugin.generate_data_register(_base_inputs())
    md = plugin.render_markdown(result)
    for section in ("# AI Data Register", "## Summary", "## Applicable Citations", "## Datasets"):
        assert section in md


def test_render_csv_header_and_row_count():
    result = plugin.generate_data_register(_base_inputs())
    csv = plugin.render_csv(result)
    lines = csv.strip().split("\n")
    assert lines[0].startswith("id,name,system_refs")
    assert len(lines) == 2  # header + 1 row


def test_no_em_dashes_in_output():
    result = plugin.generate_data_register(_base_inputs())
    md = plugin.render_markdown(result)
    csv = plugin.render_csv(result)
    assert "\u2014" not in md
    assert "\u2014" not in csv


def test_summary_counts():
    inputs = _base_inputs()
    inputs["data_inventory"] = [
        _minimal_dataset(id="D1", purpose_stage="training", source="internal"),
        _minimal_dataset(id="D2", purpose_stage="validation", source="public-open"),
        _minimal_dataset(id="D3", purpose_stage="inference", source="internal"),
    ]
    result = plugin.generate_data_register(inputs)
    counts = result["summary"]
    assert counts["purpose_counts"]["training"] == 1
    assert counts["purpose_counts"]["validation"] == 1
    assert counts["purpose_counts"]["inference"] == 1
    assert counts["source_counts"]["internal"] == 2
    assert counts["source_counts"]["public-open"] == 1


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
