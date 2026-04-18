"""Tests for high-risk-classifier plugin."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _minimal_system(**kwargs) -> dict:
    base = {
        "system_name": "TestSystem",
        "intended_use": "Internal back-office automation",
        "sector": "internal-operations",
        "deployment_context": "Internal intranet, no customer-facing use",
        "data_processed": ["transactional metadata"],
    }
    base.update(kwargs)
    return base


# --- Minimal-risk default ---

def test_minimal_risk_default():
    result = plugin.classify({"system_description": _minimal_system()})
    assert result["risk_tier"] == "minimal-risk"
    assert result["requires_legal_review"] is False


# --- Annex III categories ---

def test_employment_triggers_high_risk_annex_iii():
    sys = _minimal_system(
        system_name="ResumeScreen",
        intended_use="Resume screening and candidate ranking for HR",
        sector="HR",
    )
    result = plugin.classify({"system_description": sys})
    assert result["risk_tier"] == "high-risk-annex-iii"
    assert any(m["category"] == "employment-workers-management" for m in result["annex_iii_matches"])


def test_credit_scoring_triggers_essential_services():
    sys = _minimal_system(
        system_name="LoanScore",
        intended_use="Credit scoring and creditworthiness evaluation",
        sector="financial-services",
    )
    result = plugin.classify({"system_description": sys})
    assert result["risk_tier"] == "high-risk-annex-iii"
    assert any(m["category"] == "essential-services" for m in result["annex_iii_matches"])


def test_biometric_identification_triggers_biometrics_category():
    sys = _minimal_system(
        system_name="FaceLogin",
        intended_use="Biometric identification of employees for building access",
        sector="physical-security",
    )
    result = plugin.classify({"system_description": sys})
    assert result["risk_tier"] == "high-risk-annex-iii"
    assert any(m["category"] == "biometrics" for m in result["annex_iii_matches"])


def test_self_declared_annex_iii_respected():
    sys = _minimal_system(
        annex_iii_self_declared=["law-enforcement"],
    )
    result = plugin.classify({"system_description": sys})
    assert result["risk_tier"] == "high-risk-annex-iii"
    assert any(m["category"] == "law-enforcement" for m in result["annex_iii_matches"])


# --- Article 6(3) exception handling ---

def test_article_6_3_exception_surfaces_legal_review():
    sys = _minimal_system(
        system_name="ResumeScreen",
        intended_use="Resume screening",
        sector="HR",
        article_6_3_exception_claimed=True,
    )
    result = plugin.classify({"system_description": sys})
    assert result["risk_tier"] == "requires-legal-review"
    assert result["requires_legal_review"] is True
    assert "Article 6(3) exception claimed" in " ".join(result["warnings"])


# --- Article 5 prohibited-practice flags ---

def test_article_5_match_surfaces_legal_review():
    sys = _minimal_system(
        system_name="EmotionDetect",
        intended_use="Emotion recognition for employees during meetings",
        sector="HR-monitoring",
    )
    result = plugin.classify({"system_description": sys})
    assert result["risk_tier"] == "requires-legal-review"
    assert result["requires_legal_review"] is True
    assert any(m["category"] == "emotion-recognition-workplace-education"
               for m in result["article_5_matches"])


def test_self_declared_article_5():
    sys = _minimal_system(
        article_5_self_declared=["social-scoring"],
    )
    result = plugin.classify({"system_description": sys})
    assert result["risk_tier"] == "requires-legal-review"
    assert any(m["category"] == "social-scoring" for m in result["article_5_matches"])


def test_article_5_takes_precedence_over_annex_iii():
    # If both Article 5 and Annex III would match, Article 5 wins.
    sys = _minimal_system(
        system_name="Conflicted",
        intended_use="Resume screening with emotion recognition for employees",
        sector="HR",
    )
    result = plugin.classify({"system_description": sys})
    # Article 5 match flags legal review.
    assert result["risk_tier"] == "requires-legal-review"
    assert len(result["article_5_matches"]) > 0


# --- Annex I product-safety route ---

def test_annex_i_product_type_triggers_article_6_1():
    sys = _minimal_system(
        system_name="MedicalDevice",
        intended_use="AI in a CE-marked medical device",
        sector="medical-devices",
        annex_i_product_type="Medical Device Regulation (EU) 2017/745",
    )
    result = plugin.classify({"system_description": sys})
    assert result["risk_tier"] == "high-risk-annex-i"
    assert result["annex_i_match"] is not None


# --- Limited-risk / Article 50 transparency ---

def test_chatbot_triggers_limited_risk():
    sys = _minimal_system(
        system_name="CustomerBot",
        intended_use="Customer support chatbot",
        sector="customer-service",
    )
    result = plugin.classify({"system_description": sys})
    assert result["risk_tier"] == "limited-risk"
    assert any("Article 50" in c for c in result["citations"])


def test_generative_ai_triggers_transparency():
    sys = _minimal_system(
        system_name="ImageGen",
        intended_use="Generative AI for marketing images",
        sector="marketing",
        system_type="generative-ai",
    )
    result = plugin.classify({"system_description": sys})
    assert result["risk_tier"] == "limited-risk"


# --- Citations ---

def test_high_risk_annex_iii_cites_article_6_2():
    sys = _minimal_system(
        intended_use="Resume screening",
        sector="HR",
    )
    result = plugin.classify({"system_description": sys})
    assert "EU AI Act, Article 6(2)" in result["citations"]
    assert "EU AI Act, Annex III" in result["citations"]


def test_article_5_match_cites_article_5():
    sys = _minimal_system(
        article_5_self_declared=["social-scoring"],
    )
    result = plugin.classify({"system_description": sys})
    assert any("Article 5" in c for c in result["citations"])


def test_deployer_scope_cites_article_27():
    sys = _minimal_system(
        intended_use="Resume screening",
        sector="HR",
        deployer_scope=True,
    )
    result = plugin.classify({"system_description": sys})
    assert "EU AI Act, Article 27" in result["citations"]
    assert "EU AI Act, Article 26" in result["citations"]


# --- Validation ---

def test_missing_system_description_raises():
    try:
        plugin.classify({})
    except ValueError as exc:
        assert "system_description" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_missing_required_system_field_raises():
    try:
        plugin.classify({"system_description": {"system_name": "X"}})
    except ValueError as exc:
        assert "intended_use" in str(exc) or "sector" in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_non_dict_inputs_raises():
    try:
        plugin.classify("not-a-dict")
    except ValueError as exc:
        assert "dict" in str(exc)
        return
    raise AssertionError("expected ValueError")


# --- Rendering ---

def test_render_markdown_sections():
    sys = _minimal_system(
        intended_use="Resume screening",
        sector="HR",
    )
    result = plugin.classify({"system_description": sys})
    md = plugin.render_markdown(result)
    for section in ("# EU AI Act Risk-Tier Classification:", "## Rationale",
                    "## Applicable Citations", "## Annex III high-risk category matches"):
        assert section in md


def test_render_markdown_article_5_section():
    sys = _minimal_system(article_5_self_declared=["social-scoring"])
    result = plugin.classify({"system_description": sys})
    md = plugin.render_markdown(result)
    assert "## Article 5 prohibited-practice flags" in md


def test_no_em_dashes():
    sys = _minimal_system(intended_use="Resume screening", sector="HR")
    result = plugin.classify({"system_description": sys})
    md = plugin.render_markdown(result)
    assert "\u2014" not in md


# --- Summary ---

def test_summary_counts_present():
    sys = _minimal_system(intended_use="Resume screening and candidate ranking", sector="HR")
    result = plugin.classify({"system_description": sys})
    assert result["summary"]["annex_iii_match_count"] >= 1
    assert result["summary"]["risk_tier"] == "high-risk-annex-iii"


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
