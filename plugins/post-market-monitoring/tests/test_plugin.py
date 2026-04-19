"""Tests for the post-market-monitoring plugin. Runs under pytest or standalone."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _eu_high_risk_system() -> dict:
    return {
        "system_id": "ResumeScreen-2026",
        "system_name": "Acme ResumeScreen",
        "intended_use": "Initial CV screening for hiring funnel",
        "risk_tier": "high-risk-annex-iii",
        "jurisdiction": "eu",
        "deployment_context": "Production HR pipeline",
        "lifecycle_state": "in-service",
    }


def _iso_only_system() -> dict:
    return {
        "system_id": "InternalAssistant-2026",
        "system_name": "Acme Internal Assistant",
        "intended_use": "Internal knowledge retrieval",
        "risk_tier": "limited-risk",
        "jurisdiction": "us",
        "deployment_context": "Internal employee tool",
        "lifecycle_state": "in-service",
    }


def _full_eu_inputs(**overrides) -> dict:
    base = {
        "system_description": _eu_high_risk_system(),
        "monitoring_scope": {
            "dimensions_monitored": [
                "accuracy",
                "robustness",
                "cybersecurity",
                "drift",
                "bias-fairness",
                "privacy-leakage",
                "user-feedback",
                "incident-rate",
                "safety-events",
            ],
            # Article 14 (human oversight) is operationalized via the
            # human-review-sampling METHOD applied across multiple
            # dimensions (bias-fairness, accuracy). We omit Article 14
            # from the in-scope list because the dimension-mapping table
            # does not pick up method-level coverage.
            "chapter_iii_requirements_in_scope": [
                "Article 9", "Article 10", "Article 13", "Article 15", "Article 26",
            ],
            "systems_in_program": ["ResumeScreen-2026"],
        },
        "cadence": {
            "accuracy": "monthly",
            "robustness": "monthly",
            "cybersecurity": "weekly",
            "drift": "weekly",
            "bias-fairness": "quarterly",
            "privacy-leakage": "monthly",
            "user-feedback": "continuous",
            "incident-rate": "continuous",
            "safety-events": "event-driven",
        },
        "data_collection": [
            {"dimension": "accuracy", "method": "telemetry", "source_system": "ml-platform", "retention_days": 365, "owner_role": "ML Ops Lead"},
            {"dimension": "robustness", "method": "red-team-engagement", "source_system": "external-vendor", "retention_days": 730, "owner_role": "Security Engineer"},
            {"dimension": "cybersecurity", "method": "logs", "source_system": "siem", "retention_days": 365, "owner_role": "Security Engineer"},
            {"dimension": "drift", "method": "telemetry", "source_system": "ml-platform", "retention_days": 365, "owner_role": "ML Ops Lead"},
            {"dimension": "bias-fairness", "method": "human-review-sampling", "source_system": "fairness-suite", "retention_days": 730, "owner_role": "Responsible AI Lead"},
            {"dimension": "privacy-leakage", "method": "telemetry", "source_system": "dlp", "retention_days": 365, "owner_role": "Privacy Officer"},
            {"dimension": "user-feedback", "method": "user-survey", "source_system": "feedback-portal", "retention_days": 365, "owner_role": "Product Manager"},
            {"dimension": "incident-rate", "method": "complaints-channel", "source_system": "ticketing", "retention_days": 365, "owner_role": "Incident Manager"},
            {"dimension": "safety-events", "method": "logs", "source_system": "ops-logs", "retention_days": 730, "owner_role": "Incident Manager"},
        ],
        "thresholds": {
            "accuracy": {"lower_bound": 0.85, "trigger_action": "investigate", "escalation_path": "nonconformity-tracker"},
            "drift": {"upper_bound": 0.15, "trigger_action": "review-and-retrain", "escalation_path": "nonconformity-tracker"},
            "bias-fairness": {"upper_bound": 0.10, "trigger_action": "investigate", "escalation_path": "management-review"},
        },
        "responsibilities": {
            "ML Ops Lead": "Owns telemetry pipelines and accuracy/drift monitoring",
            "Responsible AI Lead": "Owns bias-fairness audit cycle",
        },
        "trigger_catalogue": [
            {
                "trigger_name": "drift-beyond-bound",
                "detection_method": "telemetry",
                "threshold_rule": "drift > 0.15 over 7-day window",
                "escalation_path_enum": "nonconformity-tracker",
                "notification_recipients": ["ML Ops Lead", "AI Governance Officer"],
            },
            {
                "trigger_name": "safety-event-serious-physical-harm",
                "detection_method": "complaints-channel",
                "threshold_rule": "any reported serious physical harm",
                "escalation_path_enum": "incident-reporting",
                "severity": "serious-physical-harm",
                "notification_recipients": ["Incident Manager", "Legal Counsel"],
            },
        ],
        "plan_review_interval_months": 12,
        "enrich_with_crosswalk": False,
    }
    base.update(overrides)
    return base


def _iso_only_inputs(**overrides) -> dict:
    base = {
        "system_description": _iso_only_system(),
        "monitoring_scope": {
            "dimensions_monitored": ["accuracy", "user-feedback", "incident-rate"],
            "chapter_iii_requirements_in_scope": [],
            "systems_in_program": ["InternalAssistant-2026"],
        },
        "cadence": "annual",
        "data_collection": [
            {"dimension": "accuracy", "method": "telemetry", "source_system": "ml-platform", "retention_days": 365, "owner_role": "ML Ops Lead"},
            {"dimension": "user-feedback", "method": "user-survey", "source_system": "feedback-portal", "retention_days": 365, "owner_role": "Product Manager"},
            {"dimension": "incident-rate", "method": "complaints-channel", "source_system": "ticketing", "retention_days": 365, "owner_role": "Incident Manager"},
        ],
        "thresholds": {},
        "enrich_with_crosswalk": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Happy path EU high-risk-annex-iii.
# ---------------------------------------------------------------------------
def test_happy_path_eu_high_risk_full_chapter_iii_coverage():
    result = plugin.generate_monitoring_plan(_full_eu_inputs())
    for f in (
        "timestamp", "agent_signature", "framework", "plan_id", "plan_version",
        "system_description_echo", "monitoring_plan", "per_dimension_monitoring",
        "trigger_catalogue", "chapter_iii_alignment", "continuous_improvement_loop",
        "review_schedule", "citations", "warnings", "summary",
    ):
        assert f in result, f"missing required field {f!r}"
    assert result["framework"] == "eu-ai-act,iso42001,nist"
    assert result["agent_signature"] == "post-market-monitoring/0.1.0"
    # Chapter III alignment present and no missing-coverage warnings.
    coverage_warnings = [w for w in result["warnings"] if "Chapter III requirement" in w]
    assert coverage_warnings == [], f"unexpected Chapter III warnings: {coverage_warnings}"


# ---------------------------------------------------------------------------
# 2. Happy path ISO-only.
# ---------------------------------------------------------------------------
def test_happy_path_iso_only_no_chapter_iii_block():
    result = plugin.generate_monitoring_plan(_iso_only_inputs())
    assert "chapter_iii_alignment" not in result
    cited = " ".join(result["citations"])
    assert "ISO/IEC 42001:2023, Clause 9.1" in cited
    assert "ISO/IEC 42001:2023, Annex A, Control A.6.2.6" in cited


# ---------------------------------------------------------------------------
# 3. Chapter III gap warning.
# ---------------------------------------------------------------------------
def test_chapter_iii_gap_warning_when_art_15_lacks_accuracy_dimension():
    inputs = _full_eu_inputs()
    inputs["monitoring_scope"] = {
        "dimensions_monitored": ["bias-fairness"],
        "chapter_iii_requirements_in_scope": ["Article 15"],
        "systems_in_program": ["ResumeScreen-2026"],
    }
    inputs["cadence"] = "quarterly"
    inputs["data_collection"] = [
        {"dimension": "bias-fairness", "method": "audit-sampling", "source_system": "fairness-suite", "retention_days": 730, "owner_role": "Responsible AI Lead"},
    ]
    inputs["thresholds"] = {}
    inputs["trigger_catalogue"] = []
    result = plugin.generate_monitoring_plan(inputs)
    text = " ".join(result["warnings"])
    assert "Chapter III requirement 'Article 15' declared in scope but no plan dimension monitors it" in text


# ---------------------------------------------------------------------------
# 4-6. Required field validation.
# ---------------------------------------------------------------------------
def test_missing_system_description_raises_value_error():
    inputs = _full_eu_inputs()
    del inputs["system_description"]
    try:
        plugin.generate_monitoring_plan(inputs)
    except ValueError as exc:
        assert "system_description" in str(exc)
        return
    raise AssertionError("expected ValueError on missing system_description")


def test_missing_monitoring_scope_raises_value_error():
    inputs = _full_eu_inputs()
    del inputs["monitoring_scope"]
    try:
        plugin.generate_monitoring_plan(inputs)
    except ValueError as exc:
        assert "monitoring_scope" in str(exc)
        return
    raise AssertionError("expected ValueError on missing monitoring_scope")


def test_missing_cadence_raises_value_error():
    inputs = _full_eu_inputs()
    del inputs["cadence"]
    try:
        plugin.generate_monitoring_plan(inputs)
    except ValueError as exc:
        assert "cadence" in str(exc)
        return
    raise AssertionError("expected ValueError on missing cadence")


# ---------------------------------------------------------------------------
# 7. Invalid dimension.
# ---------------------------------------------------------------------------
def test_invalid_dimension_raises_value_error():
    inputs = _iso_only_inputs()
    inputs["monitoring_scope"]["dimensions_monitored"] = ["accuracy", "made-up-dimension"]
    try:
        plugin.generate_monitoring_plan(inputs)
    except ValueError as exc:
        assert "made-up-dimension" in str(exc) or "dimensions_monitored" in str(exc)
        return
    raise AssertionError("expected ValueError on invalid dimension")


# ---------------------------------------------------------------------------
# 8. Invalid cadence enum.
# ---------------------------------------------------------------------------
def test_invalid_cadence_raises_value_error():
    inputs = _iso_only_inputs()
    inputs["cadence"] = "fortnightly"
    try:
        plugin.generate_monitoring_plan(inputs)
    except ValueError as exc:
        assert "cadence" in str(exc)
        return
    raise AssertionError("expected ValueError on invalid cadence enum")


# ---------------------------------------------------------------------------
# 9. Dimension without data_collection emits placeholder + warning.
# ---------------------------------------------------------------------------
def test_dimension_without_data_collection_emits_placeholder_and_warning():
    inputs = _iso_only_inputs()
    inputs["monitoring_scope"]["dimensions_monitored"] = ["accuracy", "drift"]
    inputs["data_collection"] = [
        {"dimension": "accuracy", "method": "telemetry", "source_system": "ml-platform", "retention_days": 365, "owner_role": "ML Ops Lead"},
    ]
    result = plugin.generate_monitoring_plan(inputs)
    rows_for_drift = [r for r in result["per_dimension_monitoring"] if r["dimension"] == "drift"]
    assert rows_for_drift, "expected a placeholder row for drift"
    assert rows_for_drift[0]["method"] == "REQUIRES PRACTITIONER ASSIGNMENT"
    text = " ".join(result["warnings"])
    assert "drift" in text and "REQUIRES PRACTITIONER ASSIGNMENT" in text


# ---------------------------------------------------------------------------
# 10. Threshold without escalation_path warns.
# ---------------------------------------------------------------------------
def test_threshold_without_escalation_path_warns():
    inputs = _iso_only_inputs()
    inputs["thresholds"] = {"accuracy": {"lower_bound": 0.85, "trigger_action": "investigate"}}
    result = plugin.generate_monitoring_plan(inputs)
    text = " ".join(result["warnings"])
    assert "escalation_path" in text and "accuracy" in text


# ---------------------------------------------------------------------------
# 11. Trigger drift-beyond-bound routes to nonconformity-tracker.
# ---------------------------------------------------------------------------
def test_trigger_drift_beyond_bound_maps_to_nonconformity_tracker():
    result = plugin.generate_monitoring_plan(_full_eu_inputs())
    drift_triggers = [t for t in result["trigger_catalogue"] if "drift" in t["trigger_name"]]
    assert drift_triggers, "expected drift-beyond-bound trigger"
    assert drift_triggers[0]["escalation_path"] == "nonconformity-tracker"
    citations = " ".join(drift_triggers[0]["citations"])
    assert "ISO/IEC 42001:2023, Clause 10.2" in citations


# ---------------------------------------------------------------------------
# 12. Trigger safety-event with serious-physical-harm routes to incident-reporting.
# ---------------------------------------------------------------------------
def test_trigger_safety_event_serious_harm_maps_to_incident_reporting():
    result = plugin.generate_monitoring_plan(_full_eu_inputs())
    safety_triggers = [t for t in result["trigger_catalogue"] if "safety-event" in t["trigger_name"]]
    assert safety_triggers, "expected safety-event trigger"
    assert safety_triggers[0]["escalation_path"] == "incident-reporting"
    citations = " ".join(safety_triggers[0]["citations"])
    assert "EU AI Act, Article 73" in citations


# ---------------------------------------------------------------------------
# 13. Continuous improvement loop diff when previous_plan_ref supplied.
# ---------------------------------------------------------------------------
def test_continuous_improvement_loop_diff_when_previous_plan_ref_supplied():
    inputs = _full_eu_inputs(previous_plan_ref="pmm-ResumeScreen-2026-2025-04-18")
    result = plugin.generate_monitoring_plan(inputs)
    cil = result["continuous_improvement_loop"]
    assert cil["previous_plan_ref"] == "pmm-ResumeScreen-2026-2025-04-18"
    assert cil["diff_notes"], "expected diff_notes when previous_plan_ref supplied"
    assert cil["new_triggers_added"], "expected new_triggers_added population"
    assert cil["cadence_changes"], "expected cadence_changes population"
    # Plan version bumped because there is a predecessor.
    assert result["plan_version"] != "1.0"


# ---------------------------------------------------------------------------
# 14. review_schedule next-review-dates computed from cadence.
# ---------------------------------------------------------------------------
def test_review_schedule_next_review_dates_track_cadence():
    inputs = _iso_only_inputs(cadence="weekly")
    result = plugin.generate_monitoring_plan(inputs)
    today = datetime.now(timezone.utc).date()
    expected = (today + timedelta(days=7)).isoformat()
    for entry in result["review_schedule"]["per_dimension"]:
        assert entry["next_review_date"] == expected


# ---------------------------------------------------------------------------
# 15. plan_review_interval_months=12 -> next full review approx today + 365d.
# ---------------------------------------------------------------------------
def test_next_full_plan_review_date_uses_interval():
    result = plugin.generate_monitoring_plan(_iso_only_inputs(plan_review_interval_months=12))
    next_full = result["review_schedule"]["next_full_plan_review_date"]
    parsed = datetime.fromisoformat(next_full).date()
    today = datetime.now(timezone.utc).date()
    delta = (parsed - today).days
    assert 360 <= delta <= 370, f"expected ~365d ahead; got {delta}"


# ---------------------------------------------------------------------------
# 16. Multi-system plan covers all systems_in_program.
# ---------------------------------------------------------------------------
def test_multi_system_plan_enumerates_all_systems():
    inputs = _iso_only_inputs()
    inputs["monitoring_scope"]["systems_in_program"] = ["A", "B", "C"]
    result = plugin.generate_monitoring_plan(inputs)
    assert result["monitoring_plan"]["covered_systems"] == ["A", "B", "C"]
    assert result["summary"]["covered_systems_count"] == 3


# ---------------------------------------------------------------------------
# 17. UK jurisdiction system carries UK ATRS Section 4.3 citation.
# ---------------------------------------------------------------------------
def test_uk_jurisdiction_emits_uk_atrs_citation():
    inputs = _iso_only_inputs()
    inputs["system_description"]["jurisdiction"] = "uk"
    result = plugin.generate_monitoring_plan(inputs)
    assert any("UK ATRS" in c for c in result["citations"])


# ---------------------------------------------------------------------------
# 18. Crosswalk enrichment default True populates cross_framework_citations.
# ---------------------------------------------------------------------------
def test_crosswalk_enrichment_default_true_populates_citations():
    inputs = _iso_only_inputs()
    del inputs["enrich_with_crosswalk"]
    result = plugin.generate_monitoring_plan(inputs)
    assert "cross_framework_citations" in result
    text = " ".join(result["cross_framework_citations"])
    assert "MANAGE 4.1" in text
    assert "MANAGE 4.2" in text


# ---------------------------------------------------------------------------
# 19. enrich_with_crosswalk False omits the key.
# ---------------------------------------------------------------------------
def test_crosswalk_enrichment_false_omits_key():
    result = plugin.generate_monitoring_plan(_iso_only_inputs(enrich_with_crosswalk=False))
    assert "cross_framework_citations" not in result


# ---------------------------------------------------------------------------
# 20. Citation format compliance.
# ---------------------------------------------------------------------------
def test_all_citations_match_style_format():
    result = plugin.generate_monitoring_plan(_full_eu_inputs())
    iso_re = re.compile(
        r"^ISO/IEC 42001:2023, (Clause \d+(\.\d+)*(\([a-z0-9]+\))?|Annex A, Control A\.\d+(\.\d+)*)$"
    )
    eu_re = re.compile(r"^EU AI Act, Article \d+(, Paragraph \d+)?(, Point \([a-z]\))?$")
    nist_re = re.compile(r"^NIST AI RMF, (GOVERN|MAP|MEASURE|MANAGE) \d+(\.\d+)*$")
    uk_re = re.compile(r"^UK ATRS, Section .+$")
    for c in result["citations"]:
        assert (
            iso_re.match(c) or eu_re.match(c) or nist_re.match(c) or uk_re.match(c)
        ), f"citation does not match STYLE.md: {c!r}"


# ---------------------------------------------------------------------------
# 21. No em-dash, emoji, or hedging in rendered output.
# ---------------------------------------------------------------------------
def test_rendered_output_has_no_em_dash_no_emoji_no_hedging():
    result = plugin.generate_monitoring_plan(_full_eu_inputs())
    md = plugin.render_markdown(result)
    assert "\u2014" not in md, "em-dash found in rendered Markdown"
    emoji_blocks = [(0x1F300, 0x1FAFF), (0x2600, 0x27BF)]
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
# 22. Markdown rendering required sections.
# ---------------------------------------------------------------------------
def test_render_markdown_required_sections():
    result = plugin.generate_monitoring_plan(_full_eu_inputs())
    md = plugin.render_markdown(result)
    for section in (
        "# Post-Market Monitoring Plan",
        "## Plan overview",
        "## Per-dimension monitoring",
        "## Trigger catalogue",
        "## Chapter III alignment",
        "## Review schedule",
        "## Continuous improvement loop",
        "## Warnings",
    ):
        assert section in md, f"missing section {section!r}"


# ---------------------------------------------------------------------------
# 23. CSV row count matches per_dimension_monitoring length.
# ---------------------------------------------------------------------------
def test_csv_row_count_matches_per_dimension_length():
    result = plugin.generate_monitoring_plan(_full_eu_inputs())
    csv_text = plugin.render_csv(result)
    lines = [ln for ln in csv_text.splitlines() if ln.strip()]
    assert len(lines) == 1 + len(result["per_dimension_monitoring"])


# ---------------------------------------------------------------------------
# 24. Graceful failure when crosswalk loader raises -> warning, plan still generated.
# ---------------------------------------------------------------------------
def test_crosswalk_load_failure_emits_warning_plan_still_returned(monkeypatch=None):
    # Monkey-patch the loader to raise. Standalone runner has no
    # monkeypatch; do it manually.
    original = plugin._load_crosswalk_module

    def boom():
        raise RuntimeError("simulated crosswalk failure")

    plugin._load_crosswalk_module = boom  # type: ignore[assignment]
    try:
        inputs = _iso_only_inputs()
        del inputs["enrich_with_crosswalk"]
        result = plugin.generate_monitoring_plan(inputs)
        assert "cross_framework_citations" in result, "plan should still be generated"
        text = " ".join(result["warnings"])
        assert "Crosswalk plugin unavailable" in text or "simulated crosswalk failure" in text
    finally:
        plugin._load_crosswalk_module = original  # type: ignore[assignment]


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
