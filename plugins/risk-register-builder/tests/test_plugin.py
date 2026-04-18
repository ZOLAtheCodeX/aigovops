"""
Tests for the risk-register-builder plugin.

Runs under pytest or as a standalone script. No external dependencies.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _inventory() -> list:
    return [
        {"system_ref": "SYS-001", "system_name": "ResumeScreen", "risk_tier": "limited"},
        {"system_ref": "SYS-002", "system_name": "CS-GenAI-Assist", "risk_tier": "high"},
    ]


def _minimal_risk(system_ref="SYS-001", category="bias", description="Protected-group disparity in ranking outputs.") -> dict:
    return {"system_ref": system_ref, "category": category, "description": description}


def test_happy_path_returns_required_fields():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],
    })
    for f in ("timestamp", "agent_signature", "citations", "rows", "scaffold_rows", "warnings", "summary"):
        assert f in result


def test_inherent_score_computed_from_scales():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [{
            **_minimal_risk(),
            "likelihood": "likely",         # index 4
            "impact": "major",              # index 4
        }],
    })
    row = result["rows"][0]
    assert row["inherent_score"] == 16  # 4 * 4


def test_residual_score_computed_when_provided():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [{
            **_minimal_risk(),
            "likelihood": "likely",
            "impact": "major",
            "residual_likelihood": "unlikely",    # index 2
            "residual_impact": "moderate",        # index 3
        }],
    })
    row = result["rows"][0]
    assert row["inherent_score"] == 16
    assert row["residual_score"] == 6


def test_missing_likelihood_surfaces_warning_not_error():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],  # no likelihood or impact
    })
    row = result["rows"][0]
    assert row["inherent_score"] is None
    text = " ".join(row["warnings"])
    assert "likelihood" in text.lower() and "impact" in text.lower()


def test_unknown_system_ref_surfaces_warning():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk(system_ref="SYS-999")],
    })
    row = result["rows"][0]
    text = " ".join(row["warnings"])
    assert "SYS-999" in text
    assert row["system_name"] is None


def test_unknown_category_surfaces_warning():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk(category="made-up-category")],
    })
    row = result["rows"][0]
    text = " ".join(row["warnings"])
    assert "made-up-category" in text


def test_missing_owner_surfaces_warning():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],
    })
    row = result["rows"][0]
    text = " ".join(row["warnings"])
    assert "owner" in text.lower()


def test_role_matrix_lookup_fills_owner():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],
        "role_matrix_lookup": {"bias": "Chief Risk Officer"},
    })
    row = result["rows"][0]
    assert row["owner_role"] == "Chief Risk Officer"
    assert not any("owner" in w.lower() for w in row["warnings"])


def test_invalid_treatment_option_raises_value_error():
    try:
        plugin.generate_risk_register({
            "ai_system_inventory": _inventory(),
            "risks": [{**_minimal_risk(), "treatment_option": "ignore"}],
        })
    except ValueError as exc:
        assert "treatment_option" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_citations_iso_default():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [{**_minimal_risk(), "treatment_option": "reduce"}],
    })
    row = result["rows"][0]
    assert "ISO/IEC 42001:2023, Clause 6.1.2" in row["citations"]
    assert "ISO/IEC 42001:2023, Clause 6.1.3" in row["citations"]  # treatment_option present


def test_citations_nist_mode():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],
        "framework": "nist",
    })
    row = result["rows"][0]
    assert "MAP 4.1" in row["citations"]
    assert "MANAGE 1.2" in row["citations"]
    assert not any("ISO/IEC 42001" in c for c in row["citations"])


def test_citations_dual_mode_includes_both():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],
        "framework": "dual",
    })
    row = result["rows"][0]
    assert "MAP 4.1" in row["citations"]
    assert "ISO/IEC 42001:2023, Clause 6.1.2" in row["citations"]


def test_nist_retain_without_disclosure_surfaces_manage_1_4_warning():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [{**_minimal_risk(), "treatment_option": "retain"}],
        "framework": "nist",
    })
    row = result["rows"][0]
    text = " ".join(row["warnings"])
    assert "MANAGE 1.4" in text
    assert "retain" in text.lower()


def test_nist_retain_with_disclosure_adds_manage_1_4_citation():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [{
            **_minimal_risk(),
            "treatment_option": "retain",
            "negative_residual_disclosure_ref": "Adverse-Action-Notice-Template-2026",
        }],
        "framework": "nist",
    })
    row = result["rows"][0]
    assert "MANAGE 1.4" in row["citations"]


def test_existing_controls_linked_to_soa_when_provided():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [{
            **_minimal_risk(),
            "existing_controls": ["A.7.4", {"control_id": "A.5.4", "description": "AISIA completed 2026-Q1"}],
        }],
        "soa_rows": [
            {"control_id": "A.7.4", "row_ref": "SOA-ROW-012"},
            {"control_id": "A.5.4", "row_ref": "SOA-ROW-007"},
        ],
    })
    row = result["rows"][0]
    assert len(row["existing_controls"]) == 2
    assert row["existing_controls"][0]["control_id"] == "A.7.4"
    assert row["existing_controls"][0]["soa_row_ref"] == "SOA-ROW-012"
    assert row["existing_controls"][1]["control_id"] == "A.5.4"
    assert row["existing_controls"][1]["soa_row_ref"] == "SOA-ROW-007"


def test_scaffold_emits_placeholders_for_uncovered_pairs():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],   # covers SYS-001 / bias only
        "scaffold": True,
    })
    expected = (len(_inventory()) * len(plugin.DEFAULT_TAXONOMY_ISO)) - 1  # all pairs except SYS-001/bias
    assert len(result["scaffold_rows"]) == expected


def test_scaffold_off_by_default():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],
    })
    assert result["scaffold_rows"] == []


def test_missing_required_risk_field_raises():
    try:
        plugin.generate_risk_register({
            "ai_system_inventory": _inventory(),
            "risks": [{"system_ref": "SYS-001", "category": "bias"}],  # no description
        })
    except ValueError as exc:
        assert "description" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_inventory_raises():
    try:
        plugin.generate_risk_register({"risks": [_minimal_risk()]})
    except ValueError as exc:
        assert "ai_system_inventory" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_invalid_framework_raises():
    try:
        plugin.generate_risk_register({
            "ai_system_inventory": _inventory(),
            "risks": [_minimal_risk()],
            "framework": "cobit",
        })
    except ValueError as exc:
        assert "framework" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_empty_risks_surfaces_register_level_warning():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [],
    })
    text = " ".join(result["warnings"])
    assert "empty" in text.lower() or "no risks" in text.lower()


def test_auto_generated_ids_when_not_provided():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk(), _minimal_risk(category="privacy")],
    })
    assert result["rows"][0]["id"] == "RR-0001"
    assert result["rows"][1]["id"] == "RR-0002"


def test_provided_ids_preserved():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [{**_minimal_risk(), "id": "HR-BIAS-001"}],
    })
    assert result["rows"][0]["id"] == "HR-BIAS-001"


def test_render_markdown_contains_summary_and_rows_table():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [
            {**_minimal_risk(), "likelihood": "likely", "impact": "major", "treatment_option": "reduce", "owner_role": "CRO"},
            {**_minimal_risk(category="privacy"), "likelihood": "possible", "impact": "moderate", "treatment_option": "reduce", "owner_role": "DPO"},
        ],
    })
    md = plugin.render_markdown(result)
    for section in ("# AI Risk Register", "## Summary", "## Applicable Citations", "## Rows (sorted by residual risk descending)"):
        assert section in md
    assert "ResumeScreen" in md


def test_render_markdown_ordering_by_score():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [
            {**_minimal_risk(category="privacy"), "likelihood": "possible", "impact": "moderate"},   # 3*3=9
            {**_minimal_risk(category="bias"), "likelihood": "almost-certain", "impact": "major"},   # 5*4=20
        ],
    })
    md = plugin.render_markdown(result)
    # 'bias' row should appear before 'privacy' row in the sorted table
    bias_idx = md.find("| bias |")
    privacy_idx = md.find("| privacy |")
    assert bias_idx > 0 and privacy_idx > 0
    assert bias_idx < privacy_idx


def test_render_csv_header_and_row_count():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk(), _minimal_risk(category="privacy")],
    })
    csv = plugin.render_csv(result)
    lines = csv.strip().split("\n")
    assert lines[0].startswith("id,system_ref,system_name,category")
    assert len(lines) == 3  # header + 2 rows


def test_enrich_with_crosswalk_default_true():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],
    })
    row = result["rows"][0]
    assert "cross_framework_citations" in row
    assert isinstance(row["cross_framework_citations"], list)
    assert "crosswalk_summary" in result
    assert set(result["crosswalk_summary"]["target_frameworks"]) == {"nist-ai-rmf", "eu-ai-act"}


def test_enrich_with_crosswalk_false_skips():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],
        "enrich_with_crosswalk": False,
    })
    row = result["rows"][0]
    assert "cross_framework_citations" not in row
    assert "crosswalk_summary" not in result


def test_bias_category_maps_to_a_7_4():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk(category="bias")],
    })
    row = result["rows"][0]
    citations = row["cross_framework_citations"]
    anchors = {c["iso_anchor"] for c in citations if c.get("iso_anchor")}
    assert "A.7.4" in anchors, f"expected A.7.4 in anchors; got {anchors}"


def test_environmental_category_maps_to_nist_measure_2_12():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk(category="environmental")],
    })
    row = result["rows"][0]
    citations = row["cross_framework_citations"]
    # The environmental category has no ISO anchor; expect the NIST MEASURE
    # 2.12 fallback entry with iso_anchor=None.
    nist_refs = [
        c for c in citations
        if c.get("target_framework") == "nist-ai-rmf"
        and c.get("target_ref") == "MEASURE 2.12"
    ]
    assert nist_refs, f"expected MEASURE 2.12 citation; got {citations}"
    assert nist_refs[0]["iso_anchor"] is None


def test_invalid_target_framework_raises():
    try:
        plugin.generate_risk_register({
            "ai_system_inventory": _inventory(),
            "risks": [_minimal_risk()],
            "crosswalk_target_frameworks": ["not-a-framework"],
        })
    except ValueError as exc:
        assert "not-a-framework" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_graceful_failure_on_broken_crosswalk():
    # Monkey-patch the lazy-loader to simulate a broken crosswalk. The plugin
    # must emit a top-level warning and continue without 'cross_framework_citations'.
    original_loader = plugin._load_crosswalk_module

    def broken_loader():
        raise RuntimeError("simulated crosswalk failure")

    plugin._load_crosswalk_module = broken_loader
    try:
        result = plugin.generate_risk_register({
            "ai_system_inventory": _inventory(),
            "risks": [_minimal_risk()],
        })
    finally:
        plugin._load_crosswalk_module = original_loader

    warning_text = " ".join(result["warnings"])
    assert "simulated crosswalk failure" in warning_text
    # Rows must not carry citations when enrichment failed at load time.
    for row in result["rows"]:
        assert "cross_framework_citations" not in row


def test_output_has_no_em_dashes():
    result = plugin.generate_risk_register({
        "ai_system_inventory": _inventory(),
        "risks": [_minimal_risk()],
        "scaffold": True,
    })
    md = plugin.render_markdown(result)
    csv = plugin.render_csv(result)
    assert "\u2014" not in md
    assert "\u2014" not in csv


def _run_all():
    import inspect
    current_module = sys.modules[__name__]
    tests = [(n, o) for n, o in inspect.getmembers(current_module) if n.startswith("test_") and callable(o)]
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
