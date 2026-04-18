"""Tests for the nonconformity-tracker plugin. Runs under pytest or standalone."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _base_record(status="detected") -> dict:
    return {
        "description": "Protected-group disparity of 0.18 in advance rate, exceeds organizational tolerance 0.05.",
        "source_citation": "ISO/IEC 42001:2023, Annex A, Control A.5.4",
        "detected_by": "Clinical Informatics Equity Audit",
        "detection_date": "2026-03-20",
        "detection_method": "Scheduled quarterly equity audit",
        "status": status,
    }


def test_happy_path_returns_required_fields():
    result = plugin.generate_nonconformity_register({"records": [_base_record()]})
    for f in ("timestamp", "agent_signature", "citations", "records", "state_summary", "audit_log_events", "summary"):
        assert f in result


def test_invalid_status_raises():
    try:
        plugin.generate_nonconformity_register({"records": [{**_base_record(), "status": "nowhere"}]})
    except ValueError as exc:
        assert "status" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_required_record_field_raises():
    record = _base_record()
    del record["detected_by"]
    try:
        plugin.generate_nonconformity_register({"records": [record]})
    except ValueError as exc:
        assert "detected_by" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_detected_state_has_no_invariant_warnings():
    result = plugin.generate_nonconformity_register({"records": [_base_record("detected")]})
    assert result["records"][0]["warnings"] == []


def test_root_cause_state_requires_root_cause_text():
    result = plugin.generate_nonconformity_register({
        "records": [_base_record("root-cause-identified")],  # no root_cause set
    })
    text = " ".join(result["records"][0]["warnings"])
    assert "root_cause" in text.lower()


def test_corrective_action_planned_requires_actions_list():
    result = plugin.generate_nonconformity_register({
        "records": [{**_base_record("corrective-action-planned"), "root_cause": "root cause text", "root_cause_analysis_date": "2026-03-25"}],
    })
    text = " ".join(result["records"][0]["warnings"])
    assert "corrective_actions" in text.lower()


def test_corrective_action_must_have_owner_target_date():
    result = plugin.generate_nonconformity_register({
        "records": [{
            **_base_record("corrective-action-planned"),
            "root_cause": "root cause text",
            "root_cause_analysis_date": "2026-03-25",
            "corrective_actions": [{"action": "Retrain classifier"}],  # no owner, no target_date
        }],
    })
    text = " ".join(result["records"][0]["warnings"])
    assert "owner" in text.lower()
    assert "target_date" in text.lower()


def test_closed_without_effectiveness_fields_surfaces_warnings():
    result = plugin.generate_nonconformity_register({
        "records": [{**_base_record("closed"), "closed_at": "2026-04-30", "closed_by": "CRO"}],
    })
    text = " ".join(result["records"][0]["warnings"])
    assert "effectiveness_review_date" in text.lower()
    assert "effectiveness_outcome" in text.lower()


def test_closed_with_ineffective_outcome_raises_warning():
    result = plugin.generate_nonconformity_register({
        "records": [{
            **_base_record("closed"),
            "root_cause": "rc",
            "root_cause_analysis_date": "2026-03-25",
            "corrective_actions": [{"action": "x", "owner": "y", "target_date": "2026-04-01", "completed_at": "2026-04-15"}],
            "effectiveness_review_date": "2026-04-30",
            "effectiveness_outcome": "ineffective",
            "effectiveness_reviewer": "CRO",
            "closed_at": "2026-04-30",
            "closed_by": "CRO",
        }],
    })
    text = " ".join(result["records"][0]["warnings"])
    assert "ineffective" in text.lower()
    assert "reopen" in text.lower()


def test_state_history_emits_audit_log_events():
    result = plugin.generate_nonconformity_register({
        "records": [{
            **_base_record("closed"),
            "root_cause": "rc",
            "root_cause_analysis_date": "2026-03-25",
            "corrective_actions": [{"action": "x", "owner": "y", "target_date": "2026-04-01", "completed_at": "2026-04-15"}],
            "effectiveness_review_date": "2026-04-30",
            "effectiveness_outcome": "effective",
            "effectiveness_reviewer": "CRO",
            "closed_at": "2026-04-30",
            "closed_by": "CRO",
            "state_history": [
                {"state": "detected", "at": "2026-03-20", "by": "auditor"},
                {"state": "investigated", "at": "2026-03-22", "by": "AI Governance Officer"},
                {"state": "root-cause-identified", "at": "2026-03-25", "by": "AI Governance Officer"},
                {"state": "closed", "at": "2026-04-30", "by": "CRO"},
            ],
        }],
    })
    assert len(result["audit_log_events"]) == 4
    events = result["audit_log_events"]
    assert events[0]["event"] == "nonconformity-transition-to-detected"
    assert events[-1]["event"] == "nonconformity-transition-to-closed"
    assert all(e["citation"] == "ISO/IEC 42001:2023, Clause 7.5.2" for e in events)


def test_state_history_backward_movement_warns():
    result = plugin.generate_nonconformity_register({
        "records": [{
            **_base_record("investigated"),
            "investigation_started_at": "2026-03-22",
            "state_history": [
                {"state": "root-cause-identified", "at": "2026-03-25"},
                {"state": "detected", "at": "2026-04-01"},  # backward
            ],
        }],
    })
    text = " ".join(result["records"][0]["warnings"])
    assert "backward" in text.lower()


def test_iso_framework_default_citations():
    result = plugin.generate_nonconformity_register({"records": [_base_record()]})
    assert "ISO/IEC 42001:2023, Clause 10.2" in result["citations"]
    assert "MANAGE 4.2" not in result["citations"]


def test_nist_framework_adds_manage_4_2():
    result = plugin.generate_nonconformity_register({"records": [_base_record()], "framework": "nist"})
    assert "MANAGE 4.2" in result["citations"]
    record = result["records"][0]
    assert "MANAGE 4.2" in record["citations"]
    assert not any("ISO/IEC 42001" in c for c in record["citations"])


def test_dual_framework_includes_both():
    result = plugin.generate_nonconformity_register({"records": [_base_record()], "framework": "dual"})
    record = result["records"][0]
    assert "MANAGE 4.2" in record["citations"]
    assert any("Clause 10.2" in c for c in record["citations"])


def test_state_summary_counts():
    records = [_base_record("detected"), _base_record("investigated"), _base_record("closed")]
    records[1]["investigation_started_at"] = "2026-03-22"
    records[2].update({
        "root_cause": "rc",
        "root_cause_analysis_date": "2026-03-25",
        "corrective_actions": [{"action": "x", "owner": "y", "target_date": "2026-04-01", "completed_at": "2026-04-15"}],
        "effectiveness_review_date": "2026-04-30",
        "effectiveness_outcome": "effective",
        "effectiveness_reviewer": "CRO",
        "closed_at": "2026-04-30",
        "closed_by": "CRO",
    })
    result = plugin.generate_nonconformity_register({"records": records})
    assert result["summary"]["state_counts"]["detected"] == 1
    assert result["summary"]["state_counts"]["investigated"] == 1
    assert result["summary"]["state_counts"]["closed"] == 1
    assert result["summary"]["open_records"] == 2
    assert result["summary"]["closed_records"] == 1


def test_auto_id_generation():
    result = plugin.generate_nonconformity_register({"records": [_base_record(), _base_record()]})
    assert result["records"][0]["id"] == "NC-0001"
    assert result["records"][1]["id"] == "NC-0002"


def test_provided_id_preserved():
    result = plugin.generate_nonconformity_register({"records": [{**_base_record(), "id": "NC-CUSTOM"}]})
    assert result["records"][0]["id"] == "NC-CUSTOM"


def test_empty_records_warns():
    result = plugin.generate_nonconformity_register({"records": []})
    text = " ".join(result["warnings"])
    assert "empty" in text.lower() or "no nonconformity" in text.lower()


def test_render_markdown_sections():
    result = plugin.generate_nonconformity_register({"records": [_base_record()]})
    md = plugin.render_markdown(result)
    for section in ("# Nonconformity and Corrective Action Register", "## Summary", "## Applicable Citations", "## Records"):
        assert section in md


def test_render_markdown_includes_record_content():
    result = plugin.generate_nonconformity_register({"records": [_base_record()]})
    md = plugin.render_markdown(result)
    assert "Clinical Informatics" in md
    assert "A.5.4" in md


def test_no_em_dashes_in_output():
    result = plugin.generate_nonconformity_register({"records": [_base_record()]})
    md = plugin.render_markdown(result)
    assert "\u2014" not in md


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
