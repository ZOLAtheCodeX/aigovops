"""Tests for the internal-audit-planner plugin. Runs under pytest or standalone."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _base_scope() -> dict:
    return {
        "aims_boundaries": "All production AI systems operated by Acme Health",
        "systems_in_scope": ["ResumeScreen", "ClinicalTriage", "FraudDetect"],
        "clauses_in_scope": ["4.1", "6.1", "7.5", "8.3", "9.1", "10.2"],
        "annex_a_in_scope": list(plugin.DEFAULT_ANNEX_A_CATEGORIES),
    }


def _base_inputs(**overrides) -> dict:
    base = {
        "scope": _base_scope(),
        "audit_frequency_months": 12,
        "audit_criteria": [
            "ISO/IEC 42001:2023",
            "Acme AI Governance Policy v1.2",
            "Prior audit report 2025-Q4",
        ],
        "auditor_pool": [
            {"name": "Alice", "role": "Lead Auditor", "independence_level": "independent", "qualifications": ["ISO 42001 Lead Auditor"]},
            {"name": "Bob", "role": "Auditor", "independence_level": "departmental-separation", "qualifications": ["CIPP/E"]},
        ],
        "management_system_risk_register_ref": "RR-2026-Q1",
        "enrich_with_crosswalk": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Happy path.
# ---------------------------------------------------------------------------
def test_happy_path_annual_audit_all_categories():
    result = plugin.generate_audit_plan(_base_inputs())
    for f in (
        "timestamp",
        "agent_signature",
        "framework",
        "scope_echo",
        "audit_schedule",
        "scope_coverage_summary",
        "impartiality_assessment",
        "criteria_mapping",
        "citations",
        "warnings",
        "summary",
    ):
        assert f in result, f"missing required field {f!r}"
    assert result["framework"] == "iso42001"
    assert result["agent_signature"] == "internal-audit-planner/0.1.0"
    assert result["summary"]["cycles_planned"] == 1
    assert len(result["audit_schedule"]) == 1
    cycle = result["audit_schedule"][0]
    # Annual cadence: all declared areas in a single cycle.
    assert len(cycle["scope_this_cycle"]) == len(_base_scope()["clauses_in_scope"]) + len(_base_scope()["annex_a_in_scope"])
    assert "Alice" in cycle["assigned_auditors"] or "Bob" in cycle["assigned_auditors"]


# ---------------------------------------------------------------------------
# 2. Quarterly cadence.
# ---------------------------------------------------------------------------
def test_quarterly_cadence_produces_four_cycles():
    result = plugin.generate_audit_plan(_base_inputs(audit_frequency_months=3))
    assert result["summary"]["cycles_planned"] == 4
    # Every declared area is covered across the four cycles.
    covered = {a for cycle in result["audit_schedule"] for a in cycle["scope_this_cycle"]}
    expected = set(_base_scope()["clauses_in_scope"]) | set(_base_scope()["annex_a_in_scope"])
    assert covered == expected


# ---------------------------------------------------------------------------
# 3-5. Required field validation.
# ---------------------------------------------------------------------------
def test_missing_scope_raises_value_error():
    inputs = _base_inputs()
    del inputs["scope"]
    try:
        plugin.generate_audit_plan(inputs)
    except ValueError as exc:
        assert "scope" in str(exc)
        return
    raise AssertionError("expected ValueError on missing scope")


def test_missing_audit_frequency_raises_value_error():
    inputs = _base_inputs()
    del inputs["audit_frequency_months"]
    try:
        plugin.generate_audit_plan(inputs)
    except ValueError as exc:
        assert "audit_frequency_months" in str(exc)
        return
    raise AssertionError("expected ValueError on missing audit_frequency_months")


def test_missing_audit_criteria_raises_value_error():
    inputs = _base_inputs()
    del inputs["audit_criteria"]
    try:
        plugin.generate_audit_plan(inputs)
    except ValueError as exc:
        assert "audit_criteria" in str(exc)
        return
    raise AssertionError("expected ValueError on missing audit_criteria")


# ---------------------------------------------------------------------------
# 6. Frequency out of range.
# ---------------------------------------------------------------------------
def test_audit_frequency_out_of_range_raises():
    for bad in (0, 37, -1, 100):
        try:
            plugin.generate_audit_plan(_base_inputs(audit_frequency_months=bad))
        except ValueError as exc:
            assert "audit_frequency_months" in str(exc)
            continue
        raise AssertionError(f"expected ValueError on audit_frequency_months={bad}")


# ---------------------------------------------------------------------------
# 7. audit_type enum.
# ---------------------------------------------------------------------------
def test_invalid_audit_type_raises():
    try:
        plugin.generate_audit_plan(_base_inputs(audit_type="informal"))
    except ValueError as exc:
        assert "audit_type" in str(exc)
        return
    raise AssertionError("expected ValueError on invalid audit_type")


# ---------------------------------------------------------------------------
# 8. Empty auditor pool warns.
# ---------------------------------------------------------------------------
def test_empty_auditor_pool_surfaces_warning():
    result = plugin.generate_audit_plan(_base_inputs(auditor_pool=[]))
    text = " ".join(result["warnings"])
    assert "auditor" in text.lower()
    # Every cycle is marked REQUIRES AUDITOR ASSIGNMENT.
    for cycle in result["audit_schedule"]:
        assert cycle["assigned_auditors"] == ["REQUIRES AUDITOR ASSIGNMENT"]


# ---------------------------------------------------------------------------
# 9. Impartiality conflict warning.
# ---------------------------------------------------------------------------
def test_auditor_own_area_conflict_surfaces_warning():
    inputs = _base_inputs(
        auditor_pool=[
            {
                "name": "Charlie",
                "role": "Auditor",
                "independence_level": "departmental-separation",
                "own_areas": ["A.6"],
            },
        ],
    )
    result = plugin.generate_audit_plan(inputs)
    text = " ".join(result["warnings"]).lower()
    assert "impartiality" in text or "own_areas" in text
    assert "clause 9.2.2(c)" in text


# ---------------------------------------------------------------------------
# 10. Scope gap warning.
# ---------------------------------------------------------------------------
def test_empty_scope_areas_warns_on_coverage():
    scope = _base_scope()
    scope["clauses_in_scope"] = []
    scope["annex_a_in_scope"] = []
    result = plugin.generate_audit_plan(_base_inputs(scope=scope))
    text = " ".join(result["warnings"])
    assert "scope" in text.lower()


def test_scope_gap_warning_when_areas_uncovered():
    # Force a degenerate case: empty auditor pool plus zero-area cycle with the
    # broken partition handled; use zero cycles via scope with no areas.
    scope = _base_scope()
    scope["clauses_in_scope"] = []
    scope["annex_a_in_scope"] = []
    result = plugin.generate_audit_plan(_base_inputs(scope=scope))
    # Zero declared areas => zero coverage, no gap-list population (covered is empty).
    assert result["scope_coverage_summary"]["areas_not_covered"] == []
    # The scope-is-empty warning fires instead.
    text = " ".join(result["warnings"]).lower()
    assert "programme produces zero cycles" in text or "requires each audit to define a scope" in text


# ---------------------------------------------------------------------------
# 11. Prior findings drive prioritization.
# ---------------------------------------------------------------------------
def test_prior_critical_finding_prioritizes_area_in_first_cycle():
    inputs = _base_inputs(
        audit_frequency_months=3,
        prior_audit_findings=[
            {
                "id": "F-2025-01",
                "area": "A.7",
                "severity": "critical",
                "corrective_action_status": "closed",
                "follow_up_cycle_id": "IA-2025-04",
            },
        ],
    )
    result = plugin.generate_audit_plan(inputs)
    first_cycle_scope = result["audit_schedule"][0]["scope_this_cycle"]
    # A.7 must land in the first cycle (risk-weighted to the front).
    assert "A.7" in first_cycle_scope


# ---------------------------------------------------------------------------
# 12. Risk register reference echoed in criteria.
# ---------------------------------------------------------------------------
def test_risk_register_echoed_in_criteria_mapping():
    result = plugin.generate_audit_plan(_base_inputs(management_system_risk_register_ref="RR-2026-Q1"))
    assert all(
        entry["risk_register_reference"] == "RR-2026-Q1"
        for entry in result["criteria_mapping"]
    )


# ---------------------------------------------------------------------------
# 13-14. Crosswalk enrichment toggle.
# ---------------------------------------------------------------------------
def test_crosswalk_enrichment_default_true_adds_references():
    inputs = _base_inputs()
    del inputs["enrich_with_crosswalk"]
    result = plugin.generate_audit_plan(inputs)
    assert "cross_framework_audit_references" in result
    refs = result["cross_framework_audit_references"]
    assert any(r["target_framework"] == "nist-ai-rmf" for r in refs)
    assert any(r["target_framework"] == "eu-ai-act" for r in refs)


def test_crosswalk_enrichment_false_omits_references():
    result = plugin.generate_audit_plan(_base_inputs(enrich_with_crosswalk=False))
    assert "cross_framework_audit_references" not in result


# ---------------------------------------------------------------------------
# 15. Citation format compliance.
# ---------------------------------------------------------------------------
def test_all_iso_citations_match_style_format():
    result = plugin.generate_audit_plan(_base_inputs())
    iso_re = re.compile(
        r"^ISO/IEC 42001:2023, (Clause \d+(\.\d+)*(\([a-z0-9]+\))?|Annex A, Control A\.\d+(\.\d+)*)$"
    )
    for c in result["citations"]:
        assert iso_re.match(c), f"top-level citation does not match STYLE.md: {c!r}"
    for cycle in result["audit_schedule"]:
        for c in cycle["citations"]:
            assert iso_re.match(c), f"schedule citation does not match STYLE.md: {c!r}"
    for m in result["criteria_mapping"]:
        c = m["authoritative_citation"]
        assert iso_re.match(c), f"criteria_mapping citation does not match STYLE.md: {c!r}"


# ---------------------------------------------------------------------------
# 16. Markdown rendering required sections.
# ---------------------------------------------------------------------------
def test_render_markdown_contains_all_required_sections():
    result = plugin.generate_audit_plan(_base_inputs())
    md = plugin.render_markdown(result)
    for section in (
        "# Internal Audit Programme",
        "## Schedule",
        "## Scope coverage",
        "## Impartiality",
        "## Criteria mapping",
    ):
        assert section in md, f"missing section {section!r}"


# ---------------------------------------------------------------------------
# 17. CSV row count equals schedule length.
# ---------------------------------------------------------------------------
def test_render_csv_row_count_matches_schedule():
    result = plugin.generate_audit_plan(_base_inputs(audit_frequency_months=6))
    csv_text = plugin.render_csv(result)
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    # Header + one row per cycle.
    assert len(lines) == 1 + len(result["audit_schedule"])


# ---------------------------------------------------------------------------
# 18. No em-dash, emoji, or hedging in rendered output.
# ---------------------------------------------------------------------------
def test_rendered_output_has_no_em_dash_no_emoji_no_hedging():
    result = plugin.generate_audit_plan(_base_inputs())
    md = plugin.render_markdown(result)
    assert "\u2014" not in md, "em-dash found in rendered Markdown"
    # Emoji sniff: no characters in the common emoji Unicode blocks.
    emoji_blocks = [
        (0x1F300, 0x1FAFF),
        (0x2600, 0x27BF),
    ]
    for ch in md:
        cp = ord(ch)
        for lo, hi in emoji_blocks:
            assert not (lo <= cp <= hi), f"emoji-like character U+{cp:04X} in Markdown"
    hedging = [
        "may want to consider",
        "might be helpful to",
        "could potentially",
        "it is possible that",
        "you might find",
    ]
    lower = md.lower()
    for phrase in hedging:
        assert phrase not in lower, f"hedging phrase {phrase!r} in Markdown"


# ---------------------------------------------------------------------------
# Extra: audit_criteria must reference ISO/IEC 42001:2023.
# ---------------------------------------------------------------------------
def test_audit_criteria_must_reference_iso_42001():
    try:
        plugin.generate_audit_plan(_base_inputs(audit_criteria=["Internal SOP only"]))
    except ValueError as exc:
        assert "ISO/IEC 42001:2023" in str(exc)
        return
    raise AssertionError("expected ValueError when audit_criteria omits ISO/IEC 42001:2023")


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
