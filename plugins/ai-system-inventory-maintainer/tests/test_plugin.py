"""Tests for ai-system-inventory-maintainer plugin."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _minimal_system(**kwargs) -> dict:
    base = {
        "system_id": "SYS-001",
        "system_name": "ResumeScreen",
        "intended_use": "Rank candidate resumes against a job posting.",
        "deployment_context": "Internal HR employment decision workflow; human reviews every surfaced candidate.",
        "risk_tier": "limited-risk",
        "decision_authority": "decision-support",
        "jurisdiction": ["eu", "international"],
        "lifecycle_state": "deployed",
        "data_processed": ["candidate resume text", "job posting text"],
        "stakeholder_groups": ["candidates", "hiring managers"],
        "owner_role": "Head of People Operations",
        "operator_role": "HR Operations Analyst",
        "model_family": "classical-ml",
        "training_data_provenance": "internal-ATS 2024-2026",
        "post_market_monitoring_plan_ref": "PMM-2026-01",
        "risk_register_ref": "RR-2026-Q1",
        "aisia_ref": "AISIA-ResumeScreen-2026-03",
        "soa_ref": "SOA-2026-Q1",
        "last_reviewed_date": "2026-04-01",
        "next_review_due_date": "2026-10-01",
    }
    base.update(kwargs)
    return base


def _minimal_inputs(**kwargs) -> dict:
    base = {
        "systems": [_minimal_system()],
        "operation": "validate",
    }
    base.update(kwargs)
    return base


# 1. Happy path validate.
def test_happy_path_three_systems():
    systems = [
        _minimal_system(),
        _minimal_system(
            system_id="SYS-002",
            system_name="ClinicalTriage",
            jurisdiction=["usa-federal", "international"],
            risk_tier="high",
            deployment_context="Hospital triage decision support under clinician oversight.",
        ),
        _minimal_system(
            system_id="SYS-003",
            system_name="FraudDetect",
            jurisdiction=["singapore"],
            risk_tier="medium",
            sector="financial-services",
            deployment_context="Financial-services transaction fraud detection.",
        ),
    ]
    result = plugin.maintain_inventory({"systems": systems, "operation": "validate"})
    for f in ("timestamp", "agent_signature", "operation", "systems",
              "validation_findings", "regulatory_applicability_matrix",
              "citations", "warnings", "summary"):
        assert f in result, f"missing field {f}"
    assert result["summary"]["total_systems"] == 3


# 2. ValueError on missing systems list.
def test_missing_systems_raises():
    try:
        plugin.maintain_inventory({"operation": "validate"})
    except ValueError as exc:
        assert "systems" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 3. ValueError on non-list systems.
def test_non_list_systems_raises():
    try:
        plugin.maintain_inventory({"systems": "not a list"})
    except ValueError as exc:
        assert "list" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 4. Per-system validation finds missing required field.
def test_missing_required_field_produces_fail_finding():
    sys_bad = _minimal_system()
    del sys_bad["intended_use"]
    result = plugin.maintain_inventory({"systems": [sys_bad]})
    findings = result["validation_findings"]["SYS-001"]
    fails = [f for f in findings if f["level"] == "FAIL"]
    assert any(f["field"] == "intended_use" for f in fails)
    assert "SYS-001" in result["summary"]["systems_missing_required_fields"]


# 5. Per-system validation flags missing recommended as warning.
def test_missing_recommended_flags_warn():
    sys_bad = _minimal_system()
    del sys_bad["post_market_monitoring_plan_ref"]
    result = plugin.maintain_inventory({"systems": [sys_bad]})
    findings = result["validation_findings"]["SYS-001"]
    warns = [f for f in findings if f["level"] == "WARN"]
    assert any(f["field"] == "post_market_monitoring_plan_ref" for f in warns)


# 6. Invalid risk_tier raises.
def test_invalid_risk_tier_raises():
    sys_bad = _minimal_system(risk_tier="ultra-terrifying")
    try:
        plugin.maintain_inventory({"systems": [sys_bad]})
    except ValueError as exc:
        assert "risk_tier" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 7. Invalid decision_authority raises.
def test_invalid_decision_authority_raises():
    sys_bad = _minimal_system(decision_authority="telepathic")
    try:
        plugin.maintain_inventory({"systems": [sys_bad]})
    except ValueError as exc:
        assert "decision_authority" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 8. Invalid lifecycle_state raises.
def test_invalid_lifecycle_state_raises():
    sys_bad = _minimal_system(lifecycle_state="zombie")
    try:
        plugin.maintain_inventory({"systems": [sys_bad]})
    except ValueError as exc:
        assert "lifecycle_state" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 9. Decommission operation marks systems.
def test_decommission_operation_marks_systems():
    systems = [_minimal_system(), _minimal_system(system_id="SYS-002", system_name="SecondSys")]
    result = plugin.maintain_inventory({
        "systems": systems,
        "operation": "decommission",
        "decommission_system_ids": ["SYS-002"],
    })
    assert result["systems"][0]["lifecycle_state"] == "deployed"
    assert result["systems"][1]["lifecycle_state"] == "decommissioned"
    # Warning emitted so downstream plugins update.
    assert any("decommissioned" in w for w in result["warnings"])


# 10. Update operation with previous inventory produces diff.
def test_update_produces_diff():
    prior = [
        {"system_id": "SYS-001", "system_name": "ResumeScreen-OLD"},
        {"system_id": "SYS-REMOVED", "system_name": "GoneSys"},
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(prior, f)
        prior_path = f.name
    try:
        systems = [
            _minimal_system(),  # SYS-001 with modified name
            _minimal_system(system_id="SYS-NEW", system_name="NewSys"),
        ]
        result = plugin.maintain_inventory({
            "systems": systems,
            "operation": "update",
            "previous_inventory_ref": prior_path,
        })
        assert "version_diff" in result
        diff = result["version_diff"]
        assert "SYS-NEW" in diff["added"]
        assert "SYS-REMOVED" in diff["removed"]
        assert any(m["system_id"] == "SYS-001" for m in diff["modified"])
    finally:
        Path(prior_path).unlink(missing_ok=True)


# 11. Applicability for EU-scope system.
def test_applicability_eu_ai_act_for_eu_scope():
    s = _minimal_system(jurisdiction=["eu"], risk_tier="high-risk-annex-iii")
    result = plugin.maintain_inventory({"systems": [s]})
    frameworks = [e["framework"] for e in result["systems"][0]["regulatory_applicability"]]
    assert "eu-ai-act" in frameworks


# 12. Applicability for NYC employment.
def test_applicability_nyc_ll144_for_nyc_employment():
    s = _minimal_system(
        jurisdiction=["usa-nyc", "usa-federal"],
        deployment_context="Employment candidate screening pipeline for NYC-based roles.",
    )
    result = plugin.maintain_inventory({"systems": [s]})
    frameworks = [e["framework"] for e in result["systems"][0]["regulatory_applicability"]]
    assert "nyc-ll144" in frameworks


# 13. Applicability for Colorado housing.
def test_applicability_colorado_sb_205_for_co_housing():
    s = _minimal_system(
        jurisdiction=["usa-co"],
        deployment_context="Housing tenant-screening consequential-decision system.",
        sector="housing",
    )
    result = plugin.maintain_inventory({"systems": [s]})
    frameworks = [e["framework"] for e in result["systems"][0]["regulatory_applicability"]]
    assert "colorado-sb-205" in frameworks


# 14. Applicability applies ISO 42001 to every system.
def test_applicability_iso42001_every_system():
    systems = [
        _minimal_system(),
        _minimal_system(system_id="SYS-002", jurisdiction=["singapore"]),
        _minimal_system(system_id="SYS-003", jurisdiction=["usa-ca"]),
    ]
    result = plugin.maintain_inventory({"systems": systems})
    for row in result["systems"]:
        frameworks = [e["framework"] for e in row["regulatory_applicability"]]
        assert "iso42001" in frameworks


# 15. Warning when fully-automated Annex III system has no aisia_ref.
def test_warn_fully_automated_annex_iii_missing_aisia():
    s = _minimal_system(
        risk_tier="high-risk-annex-iii",
        decision_authority="fully-automated",
    )
    del s["aisia_ref"]
    result = plugin.maintain_inventory({"systems": [s]})
    findings = result["validation_findings"]["SYS-001"]
    msgs = " ".join(f["message"] for f in findings if f["level"] == "WARN")
    assert "aisia_ref" in msgs
    assert "Article 27" in msgs


# 16. Warning when EU high-risk lacks EU AI Act citations.
def test_warn_eu_high_risk_no_citations():
    s = _minimal_system(
        jurisdiction=["eu"],
        risk_tier="high-risk-annex-iii",
    )
    s["citations"] = ["ISO/IEC 42001:2023, Clause 4.3"]
    result = plugin.maintain_inventory({"systems": [s]})
    findings = result["validation_findings"]["SYS-001"]
    msgs = " ".join(f["message"] for f in findings if f["level"] == "WARN")
    assert "EU AI Act" in msgs


# 17. Crosswalk enrichment default True.
def test_crosswalk_enrichment_default_true():
    result = plugin.maintain_inventory(_minimal_inputs())
    assert "cross_framework_references" in result["systems"][0]


# 18. Crosswalk enrichment False: key absent.
def test_crosswalk_enrichment_false_omits_key():
    inputs = _minimal_inputs()
    inputs["enrich_with_crosswalk"] = False
    result = plugin.maintain_inventory(inputs)
    assert "cross_framework_references" not in result["systems"][0]


# 19. Citation format compliance (regex assert).
def test_citation_format_compliance():
    result = plugin.maintain_inventory(_minimal_inputs())
    # Every top-level citation must match a known STYLE.md prefix pattern.
    patterns = (
        r"^ISO/IEC 42001:2023, (Clause|Annex A, Control) ",
        r"^EU AI Act, Article ",
        r"^(GOVERN|MAP|MEASURE|MANAGE) \d",
        r"^Colorado SB 205, Section ",
        r"^NYC LL144",
        r"^UK ATRS, Section ",
        r"^Singapore MAGF 2e, ",
        r"^MAS FEAT Principles \(2018\), ",
    )
    for citation in result["citations"]:
        assert any(re.match(p, citation) for p in patterns), (
            f"citation {citation!r} does not match any STYLE.md prefix"
        )
    # Every per-system applicability citation must also match.
    for row in result["systems"]:
        for entry in row["regulatory_applicability"]:
            citation = entry["citation"]
            assert any(re.match(p, citation) for p in patterns), (
                f"applicability citation {citation!r} does not match"
            )


# 20. Markdown rendering has all required sections.
def test_render_markdown_sections():
    result = plugin.maintain_inventory(_minimal_inputs())
    md = plugin.render_markdown(result)
    for section in (
        "# AI System Inventory",
        "## Summary",
        "## Applicability matrix",
        "## Validation findings",
        "## Per-system details",
    ):
        assert section in md, f"markdown missing section {section!r}"


# 21. CSV row count matches systems count.
def test_render_csv_row_count():
    systems = [_minimal_system(), _minimal_system(system_id="SYS-002", system_name="Second")]
    result = plugin.maintain_inventory({"systems": systems, "operation": "validate"})
    csv_text = plugin.render_csv(result)
    lines = csv_text.strip().split("\n")
    assert lines[0].startswith("system_id,system_name,")
    assert len(lines) == 1 + len(systems)


# 22. No em-dash, emoji, hedging in rendered output.
def test_no_em_dash_no_hedging():
    result = plugin.maintain_inventory(_minimal_inputs())
    md = plugin.render_markdown(result)
    csv_text = plugin.render_csv(result)
    assert "\u2014" not in md
    assert "\u2014" not in csv_text
    # Hedging check.
    hedging = [
        "may want to consider",
        "might be helpful to",
        "could potentially",
        "it is possible that",
        "you might find",
    ]
    combined = (md + csv_text).lower()
    for phrase in hedging:
        assert phrase not in combined, f"hedging phrase {phrase!r} present in output"
    # Emoji sanity check: restrict to ASCII plus standard punctuation and
    # hyphens/colons/etc that appear in citations. A conservative check.
    for ch in md:
        cp = ord(ch)
        # Allow standard ASCII, newline, tab.
        if cp < 128:
            continue
        # Allow select Latin-1 supplements that may appear in source URLs
        # or proper names; fail on obvious emoji range.
        if 0x1F300 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF:
            raise AssertionError(f"emoji codepoint U+{cp:04X} present in markdown output")


# 23. nist_lifecycle_stage absent -> WARN with NIST AI RMF alignment message.
def test_nist_lifecycle_stage_recommended_warning_when_absent():
    s = _minimal_system()
    # Ensure not set.
    s.pop("nist_lifecycle_stage", None)
    result = plugin.maintain_inventory({"systems": [s]})
    findings = result["validation_findings"]["SYS-001"]
    warns = [f for f in findings if f["level"] == "WARN" and f["field"] == "nist_lifecycle_stage"]
    assert warns, "expected nist_lifecycle_stage WARN"
    assert any("NIST AI RMF" in f["message"] for f in warns)


# 24. nist_lifecycle_stage valid enum accepted, no WARN on this field.
def test_nist_lifecycle_stage_accepted_when_valid_enum():
    s = _minimal_system(nist_lifecycle_stage="deploy-and-use")
    result = plugin.maintain_inventory({"systems": [s]})
    findings = result["validation_findings"]["SYS-001"]
    warns_on_field = [
        f for f in findings
        if f["level"] == "WARN" and f["field"] == "nist_lifecycle_stage"
    ]
    assert not warns_on_field, f"unexpected WARN on populated field: {warns_on_field}"
    # Field survives on output.
    assert result["systems"][0].get("nist_lifecycle_stage") == "deploy-and-use"


# 25. nist_lifecycle_stage invalid enum raises ValueError.
def test_nist_lifecycle_stage_rejected_when_invalid_enum():
    s = _minimal_system(nist_lifecycle_stage="final-ascension")
    try:
        plugin.maintain_inventory({"systems": [s]})
    except ValueError as exc:
        assert "nist_lifecycle_stage" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 26. nist_lifecycle_stage coexists with lifecycle_state.
def test_nist_lifecycle_stage_coexists_with_lifecycle_state():
    s = _minimal_system(
        lifecycle_state="deployed",
        nist_lifecycle_stage="operate-and-monitor",
    )
    result = plugin.maintain_inventory({"systems": [s]})
    row = result["systems"][0]
    assert row.get("lifecycle_state") == "deployed"
    assert row.get("nist_lifecycle_stage") == "operate-and-monitor"


# 27. Top-level citations include NIST AI RMF Section 3 Figure 3 when any
# system has nist_lifecycle_stage populated.
def test_inventory_citations_include_nist_rmf_section_3_when_any_stage_populated():
    systems = [
        _minimal_system(),
        _minimal_system(
            system_id="SYS-002",
            system_name="Second",
            nist_lifecycle_stage="verify-and-validate",
        ),
    ]
    result = plugin.maintain_inventory({"systems": systems, "operation": "validate"})
    assert any(
        c == "NIST AI RMF 1.0, Section 3, Figure 3"
        for c in result["citations"]
    ), f"expected NIST AI RMF 1.0, Section 3, Figure 3 in citations; got {result['citations']}"


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
