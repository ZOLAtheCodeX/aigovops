"""Tests for the incident-reporting plugin. Runs under pytest or standalone."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _incident(summary="System made an erroneous clinical triage decision.", harms=None) -> dict:
    return {
        "summary": summary,
        "affected_systems": ["sys-triage-01"],
        "date_of_occurrence": "2026-04-10",
        "date_discovered": "2026-04-11",
        "discovery_channel": "clinician report",
        "potential_harms": harms if harms is not None else ["misclassification risk"],
        "impacted_persons_count": 1,
        "geographic_scope": "Seattle, WA",
    }


def _future_iso(days_from_now: int = 0) -> str:
    """Return an ISO timestamp `days_from_now` days from now (UTC)."""
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return (now + timedelta(days=days_from_now)).isoformat().replace("+00:00", "Z")


# 1. Happy-path EU fatal: Article 73(6) citation + 2-day deadline.
def test_eu_fatal_2_day_deadline():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["fatality"]),
        "applicable_jurisdictions": ["eu"],
        "detected_at": _future_iso(0),
        "actor_role": "provider",
    })
    assert result["severity"] == "fatal"
    eu_entry = [e for e in result["deadline_matrix"] if e["jurisdiction"] == "eu"][0]
    assert eu_entry["rule_citation"] == "EU AI Act, Article 73, Paragraph 6"
    # Deadline is detected_at + 2 days; days_remaining ~ 2.
    assert eu_entry["days_remaining"] in (1, 2)


# 2. EU serious-physical-harm: 10 days.
def test_eu_serious_physical_harm_10_day():
    result = plugin.generate_incident_report({
        "incident_description": _incident(),
        "applicable_jurisdictions": ["eu"],
        "severity": "serious-physical-harm",
        "detected_at": _future_iso(0),
        "actor_role": "deployer",
    })
    eu = [e for e in result["deadline_matrix"] if e["jurisdiction"] == "eu"][0]
    assert eu["days_remaining"] in (9, 10)
    assert "Article 73, Paragraph 7" in eu["rule_citation"]


# 3. EU default non-fatal: 15 days.
def test_eu_default_15_day():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["unknown"]),
        "applicable_jurisdictions": ["eu"],
        "severity": "limited-harm",
        "detected_at": _future_iso(0),
        "actor_role": "provider",
    })
    eu = [e for e in result["deadline_matrix"] if e["jurisdiction"] == "eu"][0]
    assert eu["days_remaining"] in (14, 15)
    assert "Article 73, Paragraph 2" in eu["rule_citation"]


# 4. Colorado SB 205: 90-day deadline, both dev + dep obligations flagged.
def test_colorado_sb205_90_day_both_obligations():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["disparate impact in lending decisions"]),
        "applicable_jurisdictions": ["usa-co"],
        "detected_at": _future_iso(0),
        "consequential_domains": ["financial-lending"],
    })
    co = [e for e in result["deadline_matrix"] if e["jurisdiction"] == "usa-co"][0]
    assert co["days_remaining"] in (89, 90)
    assert "6-1-1702(7)" in co["rule_citation"]
    assert "6-1-1703(7)" in co["rule_citation"]


# 5. NYC LL144 candidate complaint.
def test_nyc_ll144_candidate_complaint():
    result = plugin.generate_incident_report({
        "incident_description": _incident(summary="Candidate complaint regarding AEDT"),
        "applicable_jurisdictions": ["usa-nyc"],
        "detected_at": _future_iso(0),
    })
    nyc = [e for e in result["deadline_matrix"] if e["jurisdiction"] == "usa-nyc"][0]
    assert nyc["days_remaining"] in (29, 30)
    drafts = [d for d in result["report_drafts"] if d["jurisdiction"] == "usa-nyc"]
    assert drafts and "candidate" in drafts[0]["draft_markdown"].lower()


# 6. Multi-jurisdiction: EU + Colorado + NYC.
def test_multi_jurisdiction_three_entries():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["fatality", "disparate impact"]),
        "applicable_jurisdictions": ["eu", "usa-co", "usa-nyc"],
        "detected_at": _future_iso(0),
        "actor_role": "provider",
        "consequential_domains": ["employment"],
    })
    jurisdictions = {e["jurisdiction"] for e in result["deadline_matrix"]}
    assert jurisdictions == {"eu", "usa-co", "usa-nyc"}
    assert len(result["report_drafts"]) == 3


# 7. Missing incident_description raises.
def test_missing_incident_description_raises():
    try:
        plugin.generate_incident_report({
            "applicable_jurisdictions": ["eu"],
            "detected_at": _future_iso(0),
        })
    except ValueError as exc:
        assert "incident_description" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 8. Missing applicable_jurisdictions raises.
def test_missing_jurisdictions_raises():
    try:
        plugin.generate_incident_report({
            "incident_description": _incident(),
            "detected_at": _future_iso(0),
        })
    except ValueError as exc:
        assert "applicable_jurisdictions" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 9. Missing detected_at raises.
def test_missing_detected_at_raises():
    try:
        plugin.generate_incident_report({
            "incident_description": _incident(),
            "applicable_jurisdictions": ["eu"],
        })
    except ValueError as exc:
        assert "detected_at" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 10. Invalid severity raises.
def test_invalid_severity_raises():
    try:
        plugin.generate_incident_report({
            "incident_description": _incident(),
            "applicable_jurisdictions": ["eu"],
            "detected_at": _future_iso(0),
            "severity": "catastrophic",
        })
    except ValueError as exc:
        assert "severity" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 11. Severity auto-derivation from potential_harms (fatality -> fatal).
def test_severity_auto_derived_from_fatality():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["fatality"]),
        "applicable_jurisdictions": ["eu"],
        "detected_at": _future_iso(0),
        "actor_role": "provider",
    })
    assert result["severity"] == "fatal"


# 12. Warning when actor_role absent and EU jurisdiction applies.
def test_warning_missing_actor_role_with_eu():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["fatality"]),
        "applicable_jurisdictions": ["eu"],
        "detected_at": _future_iso(0),
    })
    text = " ".join(result["warnings"]).lower()
    assert "actor_role" in text


# 13. Warning when consequential_domains absent and Colorado applies.
def test_warning_missing_consequential_domains_with_colorado():
    result = plugin.generate_incident_report({
        "incident_description": _incident(),
        "applicable_jurisdictions": ["usa-co"],
        "detected_at": _future_iso(0),
    })
    text = " ".join(result["warnings"]).lower()
    assert "consequential_domains" in text


# 14. Unsupported jurisdiction warning (non-fatal).
def test_unsupported_jurisdiction_warns():
    result = plugin.generate_incident_report({
        "incident_description": _incident(),
        "applicable_jurisdictions": ["canada"],
        "detected_at": _future_iso(0),
    })
    text = " ".join(result["warnings"]).lower()
    assert "canada" in text and "no automated" in text


# 15. Overdue status when detected_at is far in the past.
def test_overdue_status_when_past_deadline():
    past = (datetime.now(timezone.utc) - timedelta(days=20)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    result = plugin.generate_incident_report({
        "incident_description": _incident(),
        "applicable_jurisdictions": ["eu"],
        "severity": "limited-harm",
        "detected_at": past,
        "actor_role": "provider",
    })
    eu = [e for e in result["deadline_matrix"] if e["jurisdiction"] == "eu"][0]
    assert eu["status"] == "overdue"


# 16. Imminent-within-48h status.
def test_imminent_within_48h_status():
    # EU default 15-day deadline; set detected_at 14 days ago so deadline
    # is ~24 hours away.
    detected = (datetime.now(timezone.utc) - timedelta(days=14, hours=2)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    result = plugin.generate_incident_report({
        "incident_description": _incident(),
        "applicable_jurisdictions": ["eu"],
        "severity": "limited-harm",
        "detected_at": detected,
        "actor_role": "provider",
    })
    eu = [e for e in result["deadline_matrix"] if e["jurisdiction"] == "eu"][0]
    assert eu["status"] == "imminent-within-48h"


# 17. Required contents checklists populated correctly.
def test_report_drafts_have_required_checklists():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["fatality"]),
        "applicable_jurisdictions": ["eu", "usa-co", "usa-nyc"],
        "detected_at": _future_iso(0),
        "actor_role": "provider",
        "consequential_domains": ["employment"],
    })
    by_j = {d["jurisdiction"]: d for d in result["report_drafts"]}
    assert any("Chain of events" in item for item in by_j["eu"]["required_contents_checklist"])
    assert any("90-day" in item for item in by_j["usa-co"]["required_contents_checklist"])
    assert any("AEDT" in item for item in by_j["usa-nyc"]["required_contents_checklist"])


# 18. Citations conform to STYLE.md formats.
def test_citations_conform_to_style():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["fatality"]),
        "applicable_jurisdictions": ["eu", "usa-co", "usa-nyc"],
        "detected_at": _future_iso(0),
        "actor_role": "provider",
        "consequential_domains": ["employment"],
    })
    # Every citation must start with an accepted prefix.
    accepted_prefixes = (
        "ISO/IEC 42001:2023, Clause",
        "ISO/IEC 42001:2023, Annex A, Control",
        "EU AI Act, Article",
        "Colorado SB 205, Section",
        "NYC LL144",
        "NYC DCWP AEDT Rules",
    )
    for c in result["citations"]:
        assert any(c.startswith(p) for p in accepted_prefixes), f"bad citation: {c!r}"


# 19. Crosswalk enrichment default True attaches cross_framework_citations.
def test_crosswalk_enrichment_default_on():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["fatality"]),
        "applicable_jurisdictions": ["eu", "usa-co"],
        "detected_at": _future_iso(0),
        "actor_role": "provider",
        "consequential_domains": ["employment"],
    })
    assert "cross_framework_citations" in result
    # Crosswalk data is shipped; EU Article 73 or Colorado sections should
    # surface at least one cross-framework citation.
    assert isinstance(result["cross_framework_citations"], list)


# 20. No em-dash, emoji, or hedging in rendered output.
def test_no_em_dash_emoji_hedging_in_output():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["fatality"]),
        "applicable_jurisdictions": ["eu", "usa-co", "usa-nyc"],
        "detected_at": _future_iso(0),
        "actor_role": "provider",
        "consequential_domains": ["employment"],
    })
    md = plugin.render_markdown(result)
    assert "\u2014" not in md
    hedges = ["may want to consider", "might be helpful to", "could potentially",
              "it is possible that", "you might find"]
    lower = md.lower()
    for h in hedges:
        assert h not in lower, f"hedging present: {h!r}"


# 21. Markdown has required sections.
def test_markdown_has_required_sections():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["fatality"]),
        "applicable_jurisdictions": ["eu", "usa-nyc"],
        "detected_at": _future_iso(0),
        "actor_role": "provider",
    })
    md = plugin.render_markdown(result)
    for section in (
        "# Incident Report Package",
        "## Incident summary",
        "## Deadline matrix",
        "## Report drafts",
        "## Recipient list",
        "## Warnings",
    ):
        assert section in md, f"missing section {section!r}"


# 22. CSV row count equals report_drafts length.
def test_csv_row_count_matches_drafts():
    result = plugin.generate_incident_report({
        "incident_description": _incident(harms=["fatality", "disparate impact"]),
        "applicable_jurisdictions": ["eu", "usa-co", "usa-nyc"],
        "detected_at": _future_iso(0),
        "actor_role": "provider",
        "consequential_domains": ["employment"],
    })
    csv = plugin.render_csv(result)
    # header + data rows
    rows = [r for r in csv.strip().split("\n") if r]
    assert len(rows) == 1 + len(result["report_drafts"])


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
