"""Tests for nyc-ll144-audit-packager plugin."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _aedt_in_scope() -> dict:
    return {
        "tool_name": "ResumeScreen-X",
        "vendor": "HireTech Inc.",
        "decision_category": "screen",
        "substantially_assists_decision": True,
        "used_for_nyc_candidates_or_employees": True,
    }


def _aedt_out_of_scope() -> dict:
    return {
        "tool_name": "GrammarCheckPro",
        "vendor": "WriterCo",
        "decision_category": "other",
        "substantially_assists_decision": False,
        "used_for_nyc_candidates_or_employees": True,
    }


def _full_audit_data() -> dict:
    return {
        "audit_date": "2026-04-01",
        "auditor_identity": "Doe and Associates, Independent Auditor",
        "selection_rates": {
            "race_ethnicity": {
                "White (Not Hispanic or Latino)": 0.40,
                "Black or African American (Not Hispanic or Latino)": 0.32,
                "Hispanic or Latino": 0.30,
                "Asian (Not Hispanic or Latino)": 0.38,
            },
            "sex": {
                "Male": 0.37,
                "Female": 0.34,
            },
            "intersectional": {
                "White Male": 0.42,
                "White Female": 0.38,
                "Black Male": 0.31,
                "Black Female": 0.33,
                "Hispanic Male": 0.29,
                "Hispanic Female": 0.31,
            },
        },
        "distribution_comparison": {
            "baseline": "applicant pool 2025 Q4",
            "pool_size": 2400,
        },
    }


def _minimal_audit_data() -> dict:
    return {
        "audit_date": "2026-04-01",
        "auditor_identity": "Doe and Associates, Independent Auditor",
        "selection_rates": {
            "race_ethnicity": {
                "White (Not Hispanic or Latino)": 0.40,
                "Black or African American (Not Hispanic or Latino)": 0.30,
            },
            "sex": {"Male": 0.37, "Female": 0.34},
        },
        "distribution_comparison": {"baseline": "applicant pool 2025 Q4"},
    }


# --- Happy path ---

def test_happy_path_returns_required_fields():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": _full_audit_data(),
    })
    for f in (
        "timestamp",
        "agent_signature",
        "framework",
        "in_scope",
        "applicability_rationale",
        "aedt_description_echo",
        "employer_role",
        "audit_date",
        "next_audit_due_by",
        "auditor_identity",
        "selection_rates_analysis",
        "public_disclosure_bundle",
        "candidate_notices",
        "citations",
        "warnings",
        "summary",
    ):
        assert f in result
    assert result["in_scope"] is True
    assert result["agent_signature"] == "nyc-ll144-audit-packager/0.1.0"


def test_happy_path_resume_screening_tool_in_scope():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": _full_audit_data(),
    })
    assert result["in_scope"] is True
    # Candidate notices required in scope.
    assert len(result["candidate_notices"]) == 3
    notice_ids = {n["notice_id"] for n in result["candidate_notices"]}
    assert "aedt-use-notice" in notice_ids
    assert "job-qualifications-notice" in notice_ids
    assert "data-type-source-retention" in notice_ids


# --- Applicability: out of scope ---

def test_aedt_not_in_scope_when_not_substantially_assisting():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_out_of_scope(),
        "employer_role": "employer",
        "audit_data": _full_audit_data(),
    })
    assert result["in_scope"] is False
    assert result["candidate_notices"] == []
    joined = " ".join(result["warnings"])
    assert "out of scope" in joined.lower()


# --- Validation errors ---

def test_missing_aedt_description_raises():
    try:
        plugin.generate_audit_package({
            "employer_role": "employer",
            "audit_data": _full_audit_data(),
        })
    except ValueError as exc:
        assert "aedt_description" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_employer_role_raises():
    try:
        plugin.generate_audit_package({
            "aedt_description": _aedt_in_scope(),
            "audit_data": _full_audit_data(),
        })
    except ValueError as exc:
        assert "employer_role" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_invalid_employer_role_raises():
    try:
        plugin.generate_audit_package({
            "aedt_description": _aedt_in_scope(),
            "employer_role": "vendor",
            "audit_data": _full_audit_data(),
        })
    except ValueError as exc:
        assert "employer_role" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_audit_data_raises():
    try:
        plugin.generate_audit_package({
            "aedt_description": _aedt_in_scope(),
            "employer_role": "employer",
        })
    except ValueError as exc:
        assert "audit_data" in str(exc)
        return
    raise AssertionError("expected ValueError")


# --- Warnings for content gaps ---

def test_missing_intersectional_warns():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": _minimal_audit_data(),  # no intersectional
    })
    joined = " ".join(result["warnings"])
    assert "intersectional" in joined.lower()


def test_single_group_category_warns():
    audit_data = _full_audit_data()
    audit_data["selection_rates"]["solo"] = {"SoloGroup": 0.5}
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": audit_data,
    })
    joined = " ".join(result["warnings"])
    assert "fewer than 2" in joined or "single-group" in joined.lower()


def test_missing_auditor_identity_warns():
    audit_data = _full_audit_data()
    del audit_data["auditor_identity"]
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": audit_data,
    })
    joined = " ".join(result["warnings"])
    assert "auditor_identity" in joined


# --- Impact ratio computation ---

def test_impact_ratio_computed_correctly():
    audit_data = _full_audit_data()
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": audit_data,
    })
    race_analysis = result["selection_rates_analysis"]["race_ethnicity"]
    # White is highest at 0.40. Black = 0.32 -> ratio 0.8. Hispanic = 0.30 -> 0.75. Asian = 0.38 -> 0.95.
    assert race_analysis["most_selected_group"] == "White (Not Hispanic or Latino)"
    assert race_analysis["most_selected_rate"] == 0.40
    ratios = race_analysis["impact_ratios"]
    assert ratios["White (Not Hispanic or Latino)"] == 1.0
    assert ratios["Black or African American (Not Hispanic or Latino)"] == 0.8
    assert ratios["Hispanic or Latino"] == 0.75
    assert ratios["Asian (Not Hispanic or Latino)"] == 0.95


# --- Next audit due by ---

def test_next_audit_due_by_is_365_days_later():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": _full_audit_data(),
    })
    # 2026-04-01 + 365 days = 2027-04-01
    assert result["next_audit_due_by"] == "2027-04-01"


# --- Citations ---

def test_citations_conform_to_declared_format():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": _full_audit_data(),
    })
    for c in result["citations"]:
        # Each citation must start with one of the declared prefixes.
        ok = (
            c == "NYC LL144"
            or c.startswith("NYC LL144 Final Rule, Section ")
            or c.startswith("NYC DCWP AEDT Rules, Subchapter T")
        )
        assert ok, f"unexpected citation format: {c!r}"


def test_citations_include_core_references():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": _full_audit_data(),
    })
    assert "NYC LL144" in result["citations"]
    assert any(c.startswith("NYC LL144 Final Rule, Section 5-301") for c in result["citations"])
    assert any(c.startswith("NYC DCWP AEDT Rules, Subchapter T") for c in result["citations"])


# --- Rendering ---

def test_render_markdown_sections():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": _full_audit_data(),
    })
    md = plugin.render_markdown(result)
    for section in (
        "# NYC Local Law 144 Audit Package:",
        "## Applicability determination",
        "## Summary",
        "## Applicable citations",
        "## Public disclosure bundle",
        "### Selection rates and impact ratios",
        "## Required candidate notices",
    ):
        assert section in md


def test_render_csv_has_header_and_rows():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": _full_audit_data(),
    })
    csv = plugin.render_csv(result)
    lines = [line for line in csv.splitlines() if line]
    assert lines[0] == "category,group,selection_rate,impact_ratio,most_selected_group,audit_date"
    # At least one data row per category group combination (4 race + 2 sex + 6 intersectional = 12).
    assert len(lines) - 1 == 12


def test_no_em_dashes_in_rendered_markdown():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": _full_audit_data(),
    })
    md = plugin.render_markdown(result)
    assert "\u2014" not in md


def test_no_emojis_or_hedging_in_rendered_markdown():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employer",
        "audit_data": _full_audit_data(),
    })
    md = plugin.render_markdown(result).lower()
    for phrase in (
        "may want to consider",
        "might be helpful to",
        "could potentially",
        "it is possible that",
        "you might find",
    ):
        assert phrase not in md


# --- Employment agency role ---

def test_employment_agency_role_in_scope():
    result = plugin.generate_audit_package({
        "aedt_description": _aedt_in_scope(),
        "employer_role": "employment-agency",
        "audit_data": _full_audit_data(),
    })
    assert result["in_scope"] is True
    assert result["employer_role"] == "employment-agency"


def _run_all():
    import inspect

    tests = [
        (n, o)
        for n, o in inspect.getmembers(sys.modules[__name__])
        if n.startswith("test_") and callable(o)
    ]
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
