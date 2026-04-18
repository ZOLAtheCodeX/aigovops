"""Tests for colorado-ai-act-compliance plugin."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


CITATION_PATTERN = re.compile(r"^Colorado SB 205, Section 6-1-17[0-9]{2}(\([^)]+\))*( .*)?$")


def _base_system(**extra):
    base = {
        "system_name": "TestSystem",
        "substantial_factor": True,
    }
    base.update(extra)
    return base


def _full_ia_inputs():
    return {
        "ia-purpose-use": "Described.",
        "ia-risk-analysis": "Analyzed.",
        "ia-data-description": "Described.",
        "ia-customization": "None.",
        "ia-metrics": "Accuracy, FPR, FNR by protected class.",
        "ia-transparency": "Consumer notice on screen at decision point.",
        "ia-oversight": "Documented human oversight process.",
    }


def _full_dev_docs():
    return {
        "doc-intended-uses": "Resume screening for US employers.",
        "doc-known-harms": "Disparate impact on protected classes.",
        "doc-training-data-summary": "20M resumes, 2015-2023.",
        "doc-data-governance": "Representativeness testing by class.",
        "doc-evaluation": "Bias audit methodology documented.",
        "doc-limitations": "Not validated for roles outside tech.",
        "doc-post-deployment": "Monthly drift and fairness reports.",
    }


# --- Happy paths ---


def test_happy_path_developer_employment():
    result = plugin.generate_compliance_record({
        "actor_role": "developer",
        "system_description": _base_system(developer_documentation=_full_dev_docs()),
        "consequential_decision_domains": ["employment"],
    })
    assert result["is_high_risk"] is True
    assert result["actor_role"] == "developer"
    assert any(o["applicability"] == "applies" for o in result["developer_obligations"])
    assert all(o["applicability"] == "not-applicable" for o in result["deployer_obligations"])
    assert result["impact_assessment_required"] is False


def test_happy_path_deployer_housing():
    result = plugin.generate_compliance_record({
        "actor_role": "deployer",
        "system_description": _base_system(
            impact_assessment_inputs=_full_ia_inputs(),
            consumer_notice_content={"text": "This decision uses AI."},
        ),
        "consequential_decision_domains": ["housing"],
    })
    assert result["is_high_risk"] is True
    assert all(o["applicability"] == "not-applicable" for o in result["developer_obligations"])
    assert any(o["applicability"] == "applies" for o in result["deployer_obligations"])
    assert result["impact_assessment_required"] is True
    assert result["consumer_notice_required"] is True
    assert result["consumer_appeal_required"] is True


def test_happy_path_both_financial_lending():
    result = plugin.generate_compliance_record({
        "actor_role": "both",
        "system_description": _base_system(
            developer_documentation=_full_dev_docs(),
            impact_assessment_inputs=_full_ia_inputs(),
            consumer_notice_content={"text": "Consumer notice."},
        ),
        "consequential_decision_domains": ["financial-lending"],
    })
    assert result["is_high_risk"] is True
    assert any(o["applicability"] == "applies" for o in result["developer_obligations"])
    assert any(o["applicability"] == "applies" for o in result["deployer_obligations"])
    assert result["impact_assessment_required"] is True


def test_non_high_risk_empty_domains():
    result = plugin.generate_compliance_record({
        "actor_role": "deployer",
        "system_description": _base_system(),
        "consequential_decision_domains": [],
    })
    assert result["is_high_risk"] is False
    assert result["impact_assessment_required"] is False
    assert result["consumer_notice_required"] is False
    assert result["consumer_appeal_required"] is False
    assert any("non-high-risk" in w for w in result["warnings"])


# --- Validation errors ---


def test_missing_actor_role_raises():
    try:
        plugin.generate_compliance_record({
            "system_description": _base_system(),
            "consequential_decision_domains": ["employment"],
        })
    except ValueError as e:
        assert "actor_role" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_invalid_actor_role_raises():
    try:
        plugin.generate_compliance_record({
            "actor_role": "vendor",
            "system_description": _base_system(),
            "consequential_decision_domains": ["employment"],
        })
    except ValueError as e:
        assert "actor_role" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_invalid_domain_raises():
    try:
        plugin.generate_compliance_record({
            "actor_role": "deployer",
            "system_description": _base_system(),
            "consequential_decision_domains": ["transportation"],
        })
    except ValueError as e:
        assert "transportation" in str(e)
    else:
        raise AssertionError("expected ValueError")


# --- Warning triggers ---


def test_incomplete_impact_assessment_inputs_warn():
    result = plugin.generate_compliance_record({
        "actor_role": "deployer",
        "system_description": _base_system(
            impact_assessment_inputs={"ia-purpose-use": "only this"},
            consumer_notice_content={"text": "Notice."},
        ),
        "consequential_decision_domains": ["health-care"],
    })
    assert any("Impact assessment content incomplete" in w for w in result["warnings"])


def test_missing_consumer_notice_content_warn():
    result = plugin.generate_compliance_record({
        "actor_role": "deployer",
        "system_description": _base_system(impact_assessment_inputs=_full_ia_inputs()),
        "consequential_decision_domains": ["insurance"],
    })
    assert any("consumer_notice_content absent" in w for w in result["warnings"])


# --- Obligation subset correctness ---


def test_developer_obligations_match_for_each_domain():
    for d in plugin.CONSEQUENTIAL_DOMAINS:
        result = plugin.generate_compliance_record({
            "actor_role": "developer",
            "system_description": _base_system(developer_documentation=_full_dev_docs()),
            "consequential_decision_domains": [d],
        })
        applying_ids = {o["id"] for o in result["developer_obligations"] if o["applicability"] == "applies"}
        expected = {o["id"] for o in plugin.DEVELOPER_OBLIGATIONS}
        assert applying_ids == expected, f"domain {d}: {applying_ids} != {expected}"


def test_deployer_obligations_match_for_each_domain():
    for d in plugin.CONSEQUENTIAL_DOMAINS:
        result = plugin.generate_compliance_record({
            "actor_role": "deployer",
            "system_description": _base_system(
                impact_assessment_inputs=_full_ia_inputs(),
                consumer_notice_content={"text": "Notice."},
            ),
            "consequential_decision_domains": [d],
        })
        applying_ids = {o["id"] for o in result["deployer_obligations"] if o["applicability"] == "applies"}
        expected = {o["id"] for o in plugin.DEPLOYER_OBLIGATIONS}
        assert applying_ids == expected, f"domain {d}: {applying_ids} != {expected}"


# --- CSV ---


def test_csv_row_count_matches_obligations():
    result = plugin.generate_compliance_record({
        "actor_role": "both",
        "system_description": _base_system(
            developer_documentation=_full_dev_docs(),
            impact_assessment_inputs=_full_ia_inputs(),
            consumer_notice_content={"text": "Notice."},
        ),
        "consequential_decision_domains": ["legal-services"],
    })
    csv_out = plugin.render_csv(result)
    lines = [ln for ln in csv_out.strip().split("\n") if ln]
    # header + dev obligations + dep obligations
    expected_rows = 1 + len(plugin.DEVELOPER_OBLIGATIONS) + len(plugin.DEPLOYER_OBLIGATIONS)
    assert len(lines) == expected_rows


# --- Style constraints ---


def test_rendered_markdown_has_no_emdash_or_emoji_or_hedging():
    result = plugin.generate_compliance_record({
        "actor_role": "both",
        "system_description": _base_system(
            developer_documentation=_full_dev_docs(),
            impact_assessment_inputs=_full_ia_inputs(),
            consumer_notice_content={"text": "Notice."},
        ),
        "consequential_decision_domains": ["education"],
    })
    md = plugin.render_markdown(result)
    csv_out = plugin.render_csv(result)
    combined = md + "\n" + csv_out
    assert "\u2014" not in combined, "em-dash present"
    hedging_phrases = [
        "may want to consider",
        "might be helpful to",
        "could potentially",
        "it is possible that",
        "you might find",
    ]
    lower = combined.lower()
    for phrase in hedging_phrases:
        assert phrase not in lower, f"hedging phrase present: {phrase}"
    # Basic emoji screen: no characters in supplementary planes common for emoji.
    for ch in combined:
        cp = ord(ch)
        assert not (0x1F300 <= cp <= 0x1FAFF), f"emoji code point present: U+{cp:X}"


def test_all_citations_match_format():
    result = plugin.generate_compliance_record({
        "actor_role": "both",
        "system_description": _base_system(
            developer_documentation=_full_dev_docs(),
            impact_assessment_inputs=_full_ia_inputs(),
            consumer_notice_content={"text": "Notice."},
        ),
        "consequential_decision_domains": ["essential-government"],
    })
    all_citations: list[str] = list(result["citations"])
    for o in result["developer_obligations"]:
        all_citations.append(o["citation"])
    for o in result["deployer_obligations"]:
        all_citations.append(o["citation"])
    for item in result["documentation_checklist"]:
        all_citations.append(item["citation"])

    for c in all_citations:
        assert CITATION_PATTERN.match(c), f"citation does not match format: {c!r}"


if __name__ == "__main__":
    import traceback

    failures = 0
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            try:
                obj()
                print(f"PASS {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL {name}: {e}")
                traceback.print_exc()
            except Exception as e:
                failures += 1
                print(f"ERROR {name}: {e}")
                traceback.print_exc()
    if failures:
        sys.exit(1)
    print("\nAll tests passed.")
