"""Tests for applicability-checker plugin."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _timeline() -> dict:
    return {
        "enforcement_events": [
            {
                "date": "2024-08-01",
                "phase": "entry-into-force",
                "description": "Regulation enters into force.",
                "effective_provisions": ["Article 1", "Article 3"],
                "citation": "EU AI Act, Article 113",
                "organizational_actions": [],
            },
            {
                "date": "2025-02-02",
                "phase": "prohibited-practices-applicable",
                "description": "Article 5 prohibitions apply.",
                "effective_provisions": ["Article 5"],
                "citation": "EU AI Act, Article 113(a)",
                "organizational_actions": [
                    "Review AI systems against Article 5 prohibitions.",
                ],
            },
            {
                "date": "2025-08-02",
                "phase": "gpai-and-governance-applicable",
                "description": "GPAI obligations apply.",
                "effective_provisions": ["Chapter V"],
                "citation": "EU AI Act, Article 113(b)",
                "organizational_actions": [
                    "GPAI providers: establish technical documentation.",
                ],
            },
            {
                "date": "2026-08-02",
                "phase": "core-obligations-applicable",
                "description": "Core high-risk obligations apply.",
                "effective_provisions": ["Articles 9-15", "Articles 16-27"],
                "citation": "EU AI Act, Article 113",
                "organizational_actions": [
                    "Classify every AI system via Article 6.",
                    "Complete FRIA for high-risk systems via Article 27.",
                ],
            },
            {
                "date": "2027-08-02",
                "phase": "annex-i-extended-transition-ends",
                "description": "Extended transition ends for Annex I-route high-risk.",
                "effective_provisions": ["Article 6(1)"],
                "citation": "EU AI Act, Article 113(c)",
                "organizational_actions": [],
            },
        ],
        "continuously_applicable": ["Article 3", "Article 113"],
    }


def _delegated() -> dict:
    return {
        "guidelines_and_codes": [
            {
                "id": "guidelines-high-risk-classification",
                "empowering_article": "Article 96",
                "subject": "Guidelines on high-risk classification",
                "status": "expected",
            },
            {
                "id": "code-of-practice-gpai",
                "empowering_article": "Article 56",
                "subject": "Code of practice for general-purpose AI models",
                "status": "drafting",
            },
        ],
        "harmonised_standards": [
            {
                "id": "iso-42001-harmonised",
                "empowering_article": "Article 40",
                "subject": "ISO 42001 as harmonised standard for Chapter III",
                "status": "in development",
            },
        ],
        "delegated_acts": [
            {
                "id": "gpai-flop-threshold",
                "empowering_article": "Article 51(3)",
                "subject": "GPAI systemic-risk threshold",
                "status": "baseline",
            },
        ],
        "implementing_acts": [],
        "high_priority_monitors": ["code-of-practice-gpai"],
    }


def _system_high_risk() -> dict:
    return {"system_name": "LoanScore", "is_high_risk": True, "is_gpai": False}


def _system_gpai() -> dict:
    return {"system_name": "FoundationModel-1", "is_high_risk": False, "is_gpai": True}


def _system_minimal_risk() -> dict:
    return {"system_name": "SpellCheck", "is_high_risk": False, "is_gpai": False}


# --- Happy path ---

def test_happy_path_returns_required_fields():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2026-04-18",
        "enforcement_timeline": _timeline(),
    })
    for f in ("timestamp", "agent_signature", "target_date",
              "applicable_events", "pending_events",
              "organizational_actions", "summary", "citations", "warnings"):
        assert f in result


# --- Applicable event filtering by date ---

def test_entry_into_force_applicable_after_2024_08_01():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2025-01-01",
        "enforcement_timeline": _timeline(),
    })
    phases = [e["phase"] for e in result["applicable_events"]]
    assert "entry-into-force" in phases
    # Not yet: prohibitions
    assert "prohibited-practices-applicable" not in phases


def test_prohibitions_applicable_after_2025_02_02():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2025-03-01",
        "enforcement_timeline": _timeline(),
    })
    phases = [e["phase"] for e in result["applicable_events"]]
    assert "prohibited-practices-applicable" in phases


def test_core_obligations_applicable_after_2026_08_02():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2027-01-01",
        "enforcement_timeline": _timeline(),
    })
    phases = [e["phase"] for e in result["applicable_events"]]
    assert "core-obligations-applicable" in phases


def test_pending_events_are_after_target():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2025-03-01",
        "enforcement_timeline": _timeline(),
    })
    pending_phases = [e["phase"] for e in result["pending_events"]]
    assert "core-obligations-applicable" in pending_phases
    assert "annex-i-extended-transition-ends" in pending_phases


# --- System-specific relevance ---

def test_gpai_phase_relevant_only_for_gpai():
    # 2026-01-01: GPAI phase is applicable date-wise but only relevant for GPAI systems.
    hr_result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2026-01-01",
        "enforcement_timeline": _timeline(),
    })
    gpai_event_in_applicable_hr = next(
        (e for e in hr_result["applicable_events"] if e["phase"] == "gpai-and-governance-applicable"),
        None,
    )
    assert gpai_event_in_applicable_hr is not None
    assert gpai_event_in_applicable_hr["applies_to_system"] is False

    gpai_result = plugin.check_applicability({
        "system_description": _system_gpai(),
        "target_date": "2026-01-01",
        "enforcement_timeline": _timeline(),
    })
    gpai_event_in_applicable_gpai = next(
        (e for e in gpai_result["applicable_events"] if e["phase"] == "gpai-and-governance-applicable"),
        None,
    )
    assert gpai_event_in_applicable_gpai is not None
    assert gpai_event_in_applicable_gpai["applies_to_system"] is True


def test_core_obligations_relevant_only_for_high_risk():
    # 2027 - core obligations applicable by date; system not high-risk should mark not-relevant.
    result = plugin.check_applicability({
        "system_description": _system_minimal_risk(),
        "target_date": "2027-01-01",
        "enforcement_timeline": _timeline(),
    })
    core = next(e for e in result["applicable_events"] if e["phase"] == "core-obligations-applicable")
    assert core["applies_to_system"] is False


def test_core_obligations_applies_to_high_risk():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2027-01-01",
        "enforcement_timeline": _timeline(),
    })
    core = next(e for e in result["applicable_events"] if e["phase"] == "core-obligations-applicable")
    assert core["applies_to_system"] is True


def test_prohibitions_apply_to_every_system():
    result = plugin.check_applicability({
        "system_description": _system_minimal_risk(),
        "target_date": "2025-03-01",
        "enforcement_timeline": _timeline(),
    })
    prohibitions = next(e for e in result["applicable_events"] if e["phase"] == "prohibited-practices-applicable")
    assert prohibitions["applies_to_system"] is True


# --- Organizational actions ---

def test_organizational_actions_collected_from_applicable_events():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2027-01-01",
        "enforcement_timeline": _timeline(),
    })
    actions_text = " ".join(a["action"] for a in result["organizational_actions"])
    assert "Article 5 prohibitions" in actions_text
    assert "FRIA" in actions_text
    assert "Article 6" in actions_text


def test_actions_skip_gpai_for_non_gpai_system():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2026-01-01",
        "enforcement_timeline": _timeline(),
    })
    actions_text = " ".join(a["action"] for a in result["organizational_actions"])
    # GPAI action should not appear for non-GPAI system.
    assert "GPAI providers" not in actions_text


def test_actions_include_gpai_for_gpai_system():
    result = plugin.check_applicability({
        "system_description": _system_gpai(),
        "target_date": "2026-01-01",
        "enforcement_timeline": _timeline(),
    })
    actions_text = " ".join(a["action"] for a in result["organizational_actions"])
    assert "GPAI providers" in actions_text


# --- Delegated acts filtering ---

def test_delegated_acts_filtered_for_gpai_system():
    result = plugin.check_applicability({
        "system_description": _system_gpai(),
        "target_date": "2026-04-18",
        "enforcement_timeline": _timeline(),
        "delegated_acts": _delegated(),
    })
    codes = result["delegated_act_status"]["guidelines_and_codes"]
    codes_ids = [c["id"] for c in codes]
    assert "code-of-practice-gpai" in codes_ids


def test_delegated_acts_filtered_for_non_gpai_system():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2026-04-18",
        "enforcement_timeline": _timeline(),
        "delegated_acts": _delegated(),
    })
    codes = result["delegated_act_status"]["guidelines_and_codes"]
    codes_ids = [c["id"] for c in codes]
    # GPAI code of practice not relevant to non-GPAI high-risk system.
    assert "code-of-practice-gpai" not in codes_ids
    # High-risk classification guidance is relevant.
    assert "guidelines-high-risk-classification" in codes_ids


# --- Summary counts ---

def test_summary_counts_correct():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2027-01-01",
        "enforcement_timeline": _timeline(),
    })
    summary = result["summary"]
    # Timeline has 5 events; 2027-01-01 applies: entry-into-force (2024), prohibitions (2025),
    # gpai-gov (2025), core-obligations (2026). Pending: annex-i-extended (2027-08).
    assert summary["applicable_event_count"] == 4
    assert summary["pending_event_count"] == 1


# --- Validation ---

def test_missing_target_date_raises():
    try:
        plugin.check_applicability({
            "system_description": _system_high_risk(),
            "enforcement_timeline": _timeline(),
        })
    except ValueError as exc:
        assert "target_date" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_invalid_target_date_raises():
    try:
        plugin.check_applicability({
            "system_description": _system_high_risk(),
            "target_date": "not-a-date",
            "enforcement_timeline": _timeline(),
        })
    except ValueError as exc:
        assert "target_date" in str(exc) or "ISO" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_enforcement_timeline_raises():
    try:
        plugin.check_applicability({
            "system_description": _system_high_risk(),
            "target_date": "2026-01-01",
        })
    except ValueError as exc:
        assert "enforcement_timeline" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_malformed_timeline_raises():
    try:
        plugin.check_applicability({
            "system_description": _system_high_risk(),
            "target_date": "2026-01-01",
            "enforcement_timeline": {"not_enforcement_events": []},
        })
    except ValueError as exc:
        assert "enforcement_events" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_pre_entry_into_force_target_date_warns():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2024-01-01",  # Before entry-into-force
        "enforcement_timeline": _timeline(),
    })
    assert "No enforcement events" in " ".join(result["warnings"])


def test_pending_relevant_warning():
    # Target date 2026 with a high-risk system: pending 2027 annex-i applies only to annex-i.
    # So pending_relevant should be 0 for a non-annex-i high-risk system.
    result = plugin.check_applicability({
        "system_description": {**_system_high_risk(), "is_annex_i_product": False},
        "target_date": "2026-09-01",
        "enforcement_timeline": _timeline(),
    })
    # Pending events include 2027 annex-i; shouldn't be relevant.
    pending_relevant = [e for e in result["pending_events"] if e["applies_to_system"]]
    assert len(pending_relevant) == 0


# --- Citations ---

def test_citations_include_article_113_always():
    result = plugin.check_applicability({
        "system_description": _system_minimal_risk(),
        "target_date": "2026-04-18",
        "enforcement_timeline": _timeline(),
    })
    assert any("Article 113" in c for c in result["citations"])


def test_citations_include_article_6_for_high_risk():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2026-04-18",
        "enforcement_timeline": _timeline(),
    })
    assert any("Article 6" in c for c in result["citations"])


def test_citations_include_article_51_for_gpai():
    result = plugin.check_applicability({
        "system_description": _system_gpai(),
        "target_date": "2026-04-18",
        "enforcement_timeline": _timeline(),
    })
    assert any("Article 51" in c for c in result["citations"])


# --- Rendering ---

def test_render_markdown_sections():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2026-04-18",
        "enforcement_timeline": _timeline(),
        "delegated_acts": _delegated(),
    })
    md = plugin.render_markdown(result)
    for section in ("# EU AI Act Applicability Report:", "## Summary",
                    "## Applicable Citations", "## Applicable enforcement events",
                    "## Pending events", "## Organizational actions due"):
        assert section in md


def test_no_em_dashes_in_output():
    result = plugin.check_applicability({
        "system_description": _system_high_risk(),
        "target_date": "2026-04-18",
        "enforcement_timeline": _timeline(),
    })
    md = plugin.render_markdown(result)
    assert "\u2014" not in md


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
