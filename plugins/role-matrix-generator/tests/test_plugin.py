"""
Tests for the role-matrix-generator plugin.

Runs under pytest or as a standalone script. No external dependencies.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _base_inputs() -> dict:
    return {
        "org_chart": [
            {"role_name": "Chief Executive Officer"},
            {"role_name": "Chief Risk Officer", "reports_to": "Chief Executive Officer"},
            {"role_name": "AI Governance Officer", "reports_to": "Chief Risk Officer"},
            {"role_name": "Data Protection Officer", "reports_to": "Chief Risk Officer"},
            {"role_name": "Chief Information Security Officer", "reports_to": "Chief Risk Officer"},
            {"role_name": "Head of AI Engineering", "reports_to": "Chief Technology Officer"},
            {"role_name": "Chief Technology Officer", "reports_to": "Chief Executive Officer"},
            {"role_name": "Chief Legal Officer", "reports_to": "Chief Executive Officer"},
        ],
        "role_assignments": {
            ("AI policy approval", "propose"): "AI Governance Officer",
            ("AI policy approval", "review"): "Chief Risk Officer",
            ("AI policy approval", "approve"): "Chief Executive Officer",
            ("AI policy approval", "consulted"): "Chief Legal Officer",
            ("AI policy approval", "informed"): "Head of AI Engineering",

            ("Risk acceptance", "propose"): "AI Governance Officer",
            ("Risk acceptance", "review"): "Chief Information Security Officer",
            ("Risk acceptance", "approve"): "Chief Risk Officer",
            ("Risk acceptance", "consulted"): "Data Protection Officer",
            ("Risk acceptance", "informed"): "Head of AI Engineering",

            ("SoA approval", "propose"): "AI Governance Officer",
            ("SoA approval", "review"): "Chief Information Security Officer",
            ("SoA approval", "approve"): "Chief Risk Officer",
            ("SoA approval", "consulted"): "Data Protection Officer",
            ("SoA approval", "informed"): "Head of AI Engineering",

            ("AISIA sign-off", "propose"): "Head of AI Engineering",
            ("AISIA sign-off", "review"): "AI Governance Officer",
            ("AISIA sign-off", "approve"): "Chief Risk Officer",
            ("AISIA sign-off", "consulted"): "Data Protection Officer",
            ("AISIA sign-off", "informed"): "Chief Executive Officer",

            ("Control implementation", "propose"): "Head of AI Engineering",
            ("Control implementation", "review"): "AI Governance Officer",
            ("Control implementation", "approve"): "Chief Technology Officer",
            ("Control implementation", "consulted"): "Chief Information Security Officer",
            ("Control implementation", "informed"): "Chief Risk Officer",

            ("Incident response", "propose"): "Chief Information Security Officer",
            ("Incident response", "review"): "AI Governance Officer",
            ("Incident response", "approve"): "Chief Risk Officer",
            ("Incident response", "consulted"): "Chief Legal Officer",
            ("Incident response", "informed"): "Chief Executive Officer",

            ("Audit programme approval", "propose"): "AI Governance Officer",
            ("Audit programme approval", "review"): "Chief Risk Officer",
            ("Audit programme approval", "approve"): "Chief Executive Officer",
            ("Audit programme approval", "consulted"): "Chief Legal Officer",
            ("Audit programme approval", "informed"): "Head of AI Engineering",

            ("External reporting", "propose"): "AI Governance Officer",
            ("External reporting", "review"): "Chief Legal Officer",
            ("External reporting", "approve"): "Chief Executive Officer",
            ("External reporting", "consulted"): "Chief Risk Officer",
            ("External reporting", "informed"): "Head of AI Engineering",
        },
        "authority_register": {
            "Chief Executive Officer": "Board Resolution 2024-01, CEO Authority",
            "Chief Risk Officer": "Delegation of Authority Policy, Section 4, Risk",
            "Chief Technology Officer": "Delegation of Authority Policy, Section 4, Technology",
            "AI Governance Officer": "AI Governance Charter 2025",
            "Data Protection Officer": "GDPR Article 37 Appointment Letter",
            "Chief Information Security Officer": "Information Security Policy, Section 2",
            "Head of AI Engineering": "Job Description 2025",
            "Chief Legal Officer": "General Counsel Appointment 2024",
        },
        "backup_assignments": {
            "Chief Executive Officer": "Chief Risk Officer",
            "Chief Risk Officer": "Chief Information Security Officer",
            "Chief Technology Officer": "Head of AI Engineering",
        },
        "reviewed_by": "AI Governance Committee, 2026-Q2",
    }


def test_happy_path_returns_all_required_fields():
    matrix = plugin.generate_role_matrix(_base_inputs())
    for f in ("timestamp", "agent_signature", "citations", "rows", "unassigned_rows", "warnings"):
        assert f in matrix, f"missing field {f}"
    assert matrix["agent_signature"].startswith("role-matrix-generator/")


def test_all_default_categories_and_activities_produce_rows():
    matrix = plugin.generate_role_matrix(_base_inputs())
    expected_rows = len(plugin.DEFAULT_DECISION_CATEGORIES) * len(plugin.DEFAULT_ACTIVITIES)
    assert len(matrix["rows"]) == expected_rows, (
        f"expected {expected_rows} rows; got {len(matrix['rows'])}"
    )


def test_every_row_carries_clause_5_3_and_a_3_2_citations():
    matrix = plugin.generate_role_matrix(_base_inputs())
    for row in matrix["rows"]:
        citations = row["citations"]
        assert any("Clause 5.3" in c for c in citations), f"row missing Clause 5.3: {row}"
        assert any("A.3.2" in c for c in citations), f"row missing A.3.2: {row}"


def test_soa_approval_rows_carry_clause_6_1_3():
    matrix = plugin.generate_role_matrix(_base_inputs())
    soa_rows = [r for r in matrix["rows"] if r["decision_category"] == "SoA approval"]
    for row in soa_rows:
        assert any("Clause 6.1.3" in c for c in row["citations"]), f"SoA row missing Clause 6.1.3: {row}"


def test_aisia_rows_carry_clause_6_1_4():
    matrix = plugin.generate_role_matrix(_base_inputs())
    aisia_rows = [r for r in matrix["rows"] if r["decision_category"] == "AISIA sign-off"]
    for row in aisia_rows:
        assert any("Clause 6.1.4" in c for c in row["citations"]), f"AISIA row missing Clause 6.1.4: {row}"


def test_every_decision_category_has_exactly_one_approver():
    matrix = plugin.generate_role_matrix(_base_inputs())
    approve_rows = [r for r in matrix["rows"] if r["activity"] == "approve"]
    categories = [r["decision_category"] for r in approve_rows]
    # All default categories present once
    assert len(categories) == len(plugin.DEFAULT_DECISION_CATEGORIES)
    assert set(categories) == set(plugin.DEFAULT_DECISION_CATEGORIES)


def test_missing_assignment_produces_unassigned_marker_and_list_entry():
    bad = _base_inputs()
    # Drop one assignment
    del bad["role_assignments"][("SoA approval", "approve")]
    matrix = plugin.generate_role_matrix(bad)
    soa_approve = [r for r in matrix["rows"]
                   if r["decision_category"] == "SoA approval" and r["activity"] == "approve"][0]
    assert soa_approve["role_name"] == plugin.UNASSIGNED_MARKER
    assert "SoA approval::approve" in matrix["unassigned_rows"]


def test_missing_approver_surfaces_warning():
    bad = _base_inputs()
    del bad["role_assignments"][("SoA approval", "approve")]
    matrix = plugin.generate_role_matrix(bad)
    warning_texts = " ".join(matrix["warnings"])
    assert "SoA approval" in warning_texts
    assert "approver" in warning_texts.lower() or "approve" in warning_texts.lower()


def test_unknown_role_in_assignments_surfaces_warning():
    bad = _base_inputs()
    bad["role_assignments"][("SoA approval", "approve")] = "Director of Unicorns"
    matrix = plugin.generate_role_matrix(bad)
    warning_texts = " ".join(matrix["warnings"])
    assert "Director of Unicorns" in warning_texts
    assert "org_chart" in warning_texts


def test_approver_missing_authority_basis_surfaces_warning():
    bad = _base_inputs()
    del bad["authority_register"]["Chief Executive Officer"]
    matrix = plugin.generate_role_matrix(bad)
    warning_texts = " ".join(matrix["warnings"])
    assert "Chief Executive Officer" in warning_texts
    assert "authority" in warning_texts.lower()


def test_approver_without_backup_surfaces_warning():
    bad = _base_inputs()
    del bad["backup_assignments"]["Chief Executive Officer"]
    matrix = plugin.generate_role_matrix(bad)
    warning_texts = " ".join(matrix["warnings"])
    assert "Chief Executive Officer" in warning_texts
    assert "backup" in warning_texts.lower()


def test_validate_requires_org_chart():
    bad = _base_inputs()
    del bad["org_chart"]
    try:
        plugin.generate_role_matrix(bad)
    except ValueError as exc:
        assert "org_chart" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_validate_rejects_non_list_org_chart():
    bad = _base_inputs()
    bad["org_chart"] = "not a list"
    try:
        plugin.generate_role_matrix(bad)
    except ValueError as exc:
        assert "org_chart" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_string_key_assignments_supported():
    inputs = _base_inputs()
    # Use string-key convention for one assignment, keep the rest as tuples.
    assignments = {}
    for k, v in inputs["role_assignments"].items():
        if k == ("AI policy approval", "approve"):
            assignments[f"{k[0]}::{k[1]}"] = v
        else:
            assignments[k] = v
    inputs["role_assignments"] = assignments
    matrix = plugin.generate_role_matrix(inputs)
    policy_approve = [r for r in matrix["rows"]
                      if r["decision_category"] == "AI policy approval" and r["activity"] == "approve"][0]
    assert policy_approve["role_name"] == "Chief Executive Officer"


def test_custom_decision_categories_respected():
    inputs = _base_inputs()
    inputs["decision_categories"] = ["AI policy approval", "Risk acceptance"]
    matrix = plugin.generate_role_matrix(inputs)
    cats = {r["decision_category"] for r in matrix["rows"]}
    assert cats == {"AI policy approval", "Risk acceptance"}


def test_render_markdown_has_required_sections():
    matrix = plugin.generate_role_matrix(_base_inputs())
    md = plugin.render_markdown(matrix)
    for section in (
        "# AI Governance Role and Responsibility Matrix",
        "## Applicable Citations",
        "## Assignments",
        "| Decision Category | Activity | Role |",
    ):
        assert section in md, f"markdown missing section {section!r}"


def test_render_markdown_surfaces_unassigned_rows():
    bad = _base_inputs()
    del bad["role_assignments"][("SoA approval", "approve")]
    matrix = plugin.generate_role_matrix(bad)
    md = plugin.render_markdown(matrix)
    assert "## Unassigned rows" in md
    assert "SoA approval::approve" in md


def test_render_csv_has_header_and_row_count_matches():
    matrix = plugin.generate_role_matrix(_base_inputs())
    csv = plugin.render_csv(matrix)
    lines = csv.strip().split("\n")
    assert lines[0] == "decision_category,activity,role_name,authority_basis,backup_role_name,citations"
    assert len(lines) == len(matrix["rows"]) + 1  # header + rows


def test_output_contains_no_em_dashes():
    matrix = plugin.generate_role_matrix(_base_inputs())
    md = plugin.render_markdown(matrix)
    csv = plugin.render_csv(matrix)
    assert "\u2014" not in md
    assert "\u2014" not in csv
    for row in matrix["rows"]:
        assert "\u2014" not in str(row), f"row contains em-dash: {row}"


def _run_all():
    import inspect
    current_module = sys.modules[__name__]
    tests = [(n, o) for n, o in inspect.getmembers(current_module) if n.startswith("test_") and callable(o)]
    failures: list[tuple[str, str]] = []
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
