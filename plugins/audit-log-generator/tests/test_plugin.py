"""
Tests for the audit-log-generator plugin.

Runs under pytest (if installed) or as a standalone script. No external
dependencies beyond the Python standard library.

Invocation:
    pytest plugins/audit-log-generator/tests/
    or
    python plugins/audit-log-generator/tests/test_plugin.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _base_input() -> dict:
    return {
        "system_name": "TestSystem",
        "purpose": "Decision support for internal process.",
        "risk_tier": "limited",
        "data_processed": ["transactional metadata", "user text"],
        "deployment_context": "Internal back-office tool, human-in-the-loop.",
        "governance_decisions": ["Deployed to production after Phase 2 review."],
        "responsible_parties": ["AI Governance Officer", "System Owner"],
    }


def test_happy_path_returns_all_required_fields():
    entry = plugin.generate_audit_log(_base_input())
    for field in ("timestamp", "system_name", "clause_mappings", "annex_a_mappings",
                  "evidence_items", "human_readable_summary", "agent_signature"):
        assert field in entry, f"missing field {field}"
    assert entry["system_name"] == "TestSystem"
    assert entry["agent_signature"].startswith("audit-log-generator/")


def test_timestamp_is_iso8601_utc():
    entry = plugin.generate_audit_log(_base_input())
    ts = entry["timestamp"]
    assert ts.endswith("Z"), f"timestamp must end with Z (UTC): got {ts}"
    # Basic shape check: YYYY-MM-DDTHH:MM:SSZ
    assert len(ts) == 20, f"timestamp must be 20 chars (seconds precision): got {len(ts)}"


def test_missing_required_field_raises_value_error():
    bad = _base_input()
    del bad["risk_tier"]
    try:
        plugin.generate_audit_log(bad)
    except ValueError as exc:
        assert "risk_tier" in str(exc)
        return
    raise AssertionError("expected ValueError for missing risk_tier")


def test_invalid_risk_tier_raises_value_error():
    bad = _base_input()
    bad["risk_tier"] = "medium"  # not a valid tier
    try:
        plugin.generate_audit_log(bad)
    except ValueError as exc:
        assert "risk_tier" in str(exc)
        return
    raise AssertionError("expected ValueError for invalid risk_tier")


def test_high_risk_tier_adds_clause_6_1_4():
    hi = _base_input()
    hi["risk_tier"] = "high"
    entry = plugin.generate_audit_log(hi)
    assert any("Clause 6.1.4" in c for c in entry["clause_mappings"]), (
        f"high risk tier must add Clause 6.1.4 citation; got {entry['clause_mappings']}"
    )


def test_high_risk_tier_adds_annex_a_5_4_and_6_2_6():
    hi = _base_input()
    hi["risk_tier"] = "high"
    entry = plugin.generate_audit_log(hi)
    ids = [m["control_id"] for m in entry["annex_a_mappings"]]
    assert "A.5.4" in ids, f"high risk tier must map A.5.4; got {ids}"
    assert "A.6.2.6" in ids, f"high risk tier must map A.6.2.6; got {ids}"


def test_sensitive_data_triggers_a_7_controls():
    sensitive = _base_input()
    sensitive["data_processed"] = ["candidate resume text", "PII fields"]
    entry = plugin.generate_audit_log(sensitive)
    ids = [m["control_id"] for m in entry["annex_a_mappings"]]
    assert "A.7.2" in ids, f"sensitive data must map A.7.2; got {ids}"
    assert "A.7.5" in ids, f"sensitive data must map A.7.5; got {ids}"


def test_high_impact_deployment_triggers_a_5_5():
    clinical = _base_input()
    clinical["deployment_context"] = "Hospital clinical decision support for ED triage."
    entry = plugin.generate_audit_log(clinical)
    ids = [m["control_id"] for m in entry["annex_a_mappings"]]
    assert "A.5.5" in ids, f"clinical deployment must map A.5.5; got {ids}"


def test_always_maps_a_6_2_3_and_a_6_2_8():
    entry = plugin.generate_audit_log(_base_input())
    ids = [m["control_id"] for m in entry["annex_a_mappings"]]
    assert "A.6.2.3" in ids
    assert "A.6.2.8" in ids


def test_responsible_parties_triggers_a_3_2():
    entry = plugin.generate_audit_log(_base_input())
    ids = [m["control_id"] for m in entry["annex_a_mappings"]]
    assert "A.3.2" in ids


def test_citation_format_matches_style_md():
    entry = plugin.generate_audit_log(_base_input())
    for clause in entry["clause_mappings"]:
        assert clause.startswith("ISO/IEC 42001:2023, Clause "), (
            f"clause citation must match STYLE.md format; got {clause}"
        )
    for m in entry["annex_a_mappings"]:
        assert m["citation"].startswith("ISO/IEC 42001:2023, Annex A, Control "), (
            f"Annex A citation must match STYLE.md format; got {m['citation']}"
        )


def test_map_to_annex_a_controls_returns_dicts_with_required_fields():
    mappings = plugin.map_to_annex_a_controls(_base_input())
    assert isinstance(mappings, list)
    assert len(mappings) > 0
    for m in mappings:
        assert set(m.keys()) == {"control_id", "citation", "rationale"}


def test_no_duplicate_annex_a_mappings():
    entry = plugin.generate_audit_log(_base_input())
    ids = [m["control_id"] for m in entry["annex_a_mappings"]]
    assert len(ids) == len(set(ids)), f"duplicates in annex_a_mappings: {ids}"


def test_render_markdown_includes_required_sections():
    entry = plugin.generate_audit_log(_base_input())
    rendered = plugin.render_markdown(entry)
    for section in ("# AI Governance Audit Log Entry", "## Summary",
                    "## Applicable Main-Body Clauses", "## Applicable Annex A Controls",
                    "## Evidence Items"):
        assert section in rendered, f"rendered markdown missing section {section!r}"
    assert entry["system_name"] in rendered
    assert entry["timestamp"] in rendered


def test_render_markdown_missing_fields_raises():
    try:
        plugin.render_markdown({"system_name": "X"})
    except ValueError as exc:
        assert "missing required fields" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_empty_governance_decisions_handled():
    empty = _base_input()
    empty["governance_decisions"] = []
    entry = plugin.generate_audit_log(empty)
    assert entry["evidence_items"] == []
    # Clause 9.3 should not be added for empty governance decisions
    assert not any("Clause 9.3" in c for c in entry["clause_mappings"])


def test_non_list_data_processed_raises():
    bad = _base_input()
    bad["data_processed"] = "not a list"
    try:
        plugin.generate_audit_log(bad)
    except ValueError as exc:
        assert "data_processed" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_output_contains_no_em_dashes_or_emojis():
    # Enforce STYLE.md at runtime: output strings must be em-dash-free.
    entry = plugin.generate_audit_log(_base_input())
    rendered = plugin.render_markdown(entry)
    assert "\u2014" not in rendered, "rendered output contains em-dash"
    assert "\u2014" not in entry["human_readable_summary"], "summary contains em-dash"
    for m in entry["annex_a_mappings"]:
        assert "\u2014" not in m["rationale"], f"rationale contains em-dash: {m}"


def test_enrich_with_crosswalk_default_true():
    entry = plugin.generate_audit_log(_base_input())
    assert "cross_framework_citations" in entry, (
        "enrich_with_crosswalk defaults to True; cross_framework_citations must be present"
    )
    assert "citation_coverage" in entry, "citation_coverage must be present when enrichment runs"
    assert "crosswalk_summary" in entry, "crosswalk_summary must be present when enrichment runs"
    cov = entry["citation_coverage"]
    assert cov["primary_framework"] == "iso42001"
    assert "nist-ai-rmf" in cov["enrichment_target_frameworks"]
    assert "eu-ai-act" in cov["enrichment_target_frameworks"]
    assert cov["citations_added_count"] == len(entry["cross_framework_citations"])
    cs = entry["crosswalk_summary"]
    assert set(cs["target_frameworks"]) == {"nist-ai-rmf", "eu-ai-act"}
    assert cs["total_citations_added"] == len(entry["cross_framework_citations"])


def test_enrich_with_crosswalk_false_skips():
    inp = _base_input()
    inp["enrich_with_crosswalk"] = False
    entry = plugin.generate_audit_log(inp)
    assert "cross_framework_citations" not in entry, (
        "cross_framework_citations must be absent when enrich_with_crosswalk=False"
    )
    assert "citation_coverage" not in entry
    assert "crosswalk_summary" not in entry


def test_clause_9_1_has_nist_manage_4_1_cross_ref():
    # High-risk event emits Annex A controls A.6.2.6 (operational monitoring),
    # which crosswalks to NIST AI RMF MANAGE 4.1. The event also carries the
    # primary Clause 9.1 citation, so the enriched event is interpretable by
    # a NIST AI RMF practitioner via the MANAGE 4.1 post-deployment monitoring
    # equivalent.
    hi = _base_input()
    hi["risk_tier"] = "high"
    entry = plugin.generate_audit_log(hi)
    assert any("Clause 9.1" in c for c in entry["clause_mappings"]), (
        "event must carry the primary Clause 9.1 citation"
    )
    refs = entry.get("cross_framework_citations") or []
    nist_targets = [
        r["target_ref"] for r in refs if r.get("target_framework") == "nist-ai-rmf"
    ]
    assert any("MANAGE 4.1" in t for t in nist_targets), (
        f"expected NIST MANAGE 4.1 cross-ref for high-risk event; got {nist_targets}"
    )


def test_invalid_target_framework_raises():
    inp = _base_input()
    inp["crosswalk_target_frameworks"] = ["nist-ai-rmf", "not-a-real-framework"]
    try:
        plugin.generate_audit_log(inp)
    except ValueError as exc:
        assert "not-a-real-framework" in str(exc)
        return
    raise AssertionError("expected ValueError for unknown crosswalk target framework")


def test_graceful_failure(monkeypatch=None):
    # Monkey-patch the crosswalk loader to raise, confirming the plugin still
    # returns a renderable entry with a warning instead of propagating the
    # error.
    original = plugin._load_crosswalk_module

    def boom():
        raise RuntimeError("simulated crosswalk load failure")

    plugin._load_crosswalk_module = boom  # type: ignore[assignment]
    try:
        entry = plugin.generate_audit_log(_base_input())
        assert "warnings" in entry, "graceful failure must surface warnings on the entry"
        assert any("Crosswalk enrichment skipped" in w for w in entry["warnings"])
        # The entry is still renderable.
        rendered = plugin.render_markdown(entry)
        assert "# AI Governance Audit Log Entry" in rendered
        assert "\u2014" not in rendered
        # Crosswalk summary is present with zero counts.
        assert entry["crosswalk_summary"]["events_enriched"] == 0
        assert entry["crosswalk_summary"]["total_citations_added"] == 0
    finally:
        plugin._load_crosswalk_module = original  # type: ignore[assignment]


def _run_all():
    import inspect
    current_module = sys.modules[__name__]
    tests = [
        (name, obj) for name, obj in inspect.getmembers(current_module)
        if name.startswith("test_") and callable(obj)
    ]
    failures: list[tuple[str, str]] = []
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:
            failures.append((name, f"{type(exc).__name__}: {exc}"))
    total = len(tests)
    passed = total - len(failures)
    print(f"Ran {total} tests: {passed} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
