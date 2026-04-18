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


# --- Colorado SB 205 safe-harbor assessment ---

def test_sb205_assessment_default_enabled():
    # Employment is a Colorado SB 205 consequential-decision domain.
    sys = _minimal_system(
        system_name="ResumeScreen",
        intended_use="Resume screening and candidate ranking for HR",
        sector="employment",
    )
    result = plugin.classify({
        "system_description": sys,
        "actor_conformance_frameworks": ["nist-ai-rmf"],
        "actor_role_for_sb205": "deployer",
    })
    assert "sb205_assessment" in result
    sb205 = result["sb205_assessment"]
    assert sb205["in_scope"] is True
    assert "employment" in sb205["matched_domains"]
    assert sb205["section_6_1_1706_3_applies"] is True
    assert sb205["section_6_1_1706_4_applies"] is True
    assert any(
        c["presumption_target"] == "nist-ai-rmf"
        for c in sb205["safe_harbor_citations"]
    )
    assert all(
        c["section"] == "Colorado SB 205, Section 6-1-1706(3)"
        for c in sb205["safe_harbor_citations"]
    )
    # EU classification output remains intact.
    assert result["risk_tier"] == "high-risk-annex-iii"


def test_sb205_assessment_disabled_via_flag():
    sys = _minimal_system(
        system_name="ResumeScreen",
        intended_use="Resume screening",
        sector="employment",
    )
    result = plugin.classify({
        "system_description": sys,
        "assess_sb205_safe_harbor": False,
        "actor_conformance_frameworks": ["nist-ai-rmf"],
        "actor_role_for_sb205": "deployer",
    })
    assert "sb205_assessment" not in result
    assert result["risk_tier"] == "high-risk-annex-iii"


def test_sb205_out_of_scope_system():
    sys = _minimal_system(
        system_name="InternalBot",
        intended_use="Internal back-office automation",
        sector="internal-operations",
    )
    result = plugin.classify({
        "system_description": sys,
        "actor_conformance_frameworks": ["nist-ai-rmf"],
        "actor_role_for_sb205": "deployer",
    })
    assert "sb205_assessment" in result
    sb205 = result["sb205_assessment"]
    assert sb205["in_scope"] is False
    assert sb205["safe_harbor_applicable"] is False
    assert "reason" in sb205


def test_sb205_in_scope_no_conformance_warns():
    sys = _minimal_system(
        system_name="LoanScore",
        intended_use="Credit scoring and creditworthiness evaluation",
        sector="financial-lending",
    )
    result = plugin.classify({
        "system_description": sys,
        "actor_conformance_frameworks": [],
        "actor_role_for_sb205": "deployer",
    })
    sb205 = result["sb205_assessment"]
    assert sb205["in_scope"] is True
    assert sb205["section_6_1_1706_3_applies"] is False
    assert sb205["section_6_1_1706_4_applies"] is False
    assert sb205["safe_harbor_citations"] == []
    assert any(
        "safe-harbor not available" in w.lower()
        or "no claimed conformance" in w.lower()
        for w in sb205["warnings"]
    )


def test_sb205_in_scope_iso42001_conformance_safe_harbor():
    sys = _minimal_system(
        system_name="InsuranceRater",
        intended_use="Life insurance pricing with automated decisioning",
        sector="insurance",
    )
    result = plugin.classify({
        "system_description": sys,
        "actor_conformance_frameworks": ["iso42001"],
        "actor_role_for_sb205": "deployer",
    })
    sb205 = result["sb205_assessment"]
    assert sb205["in_scope"] is True
    assert sb205["section_6_1_1706_3_applies"] is True
    assert any(
        c["presumption_target"] == "iso42001"
        for c in sb205["safe_harbor_citations"]
    )
    assert all(
        c["section"] == "Colorado SB 205, Section 6-1-1706(3)"
        for c in sb205["safe_harbor_citations"]
    )


def test_sb205_graceful_failure_on_broken_crosswalk():
    # Force a crosswalk load failure by temporarily pointing the loader at
    # a path that does not exist. The EU classification must still render.
    import importlib.util as _util
    from pathlib import Path as _Path

    original_loader = plugin._load_crosswalk_module

    def _broken_loader():
        bogus = _Path("/nonexistent/crosswalk-matrix-builder/plugin.py")
        spec = _util.spec_from_file_location("_bogus", bogus)
        # Force an ImportError path inside _assess_sb205_safe_harbor.
        raise ImportError(f"crosswalk plugin not found at {bogus}")

    try:
        # Patch the top-level symbol used as a default argument binding.
        plugin._load_crosswalk_module = _broken_loader
        sys_desc = _minimal_system(
            system_name="EmploymentScreen",
            intended_use="Resume screening",
            sector="employment",
        )
        # Call the internal assessor directly with the broken loader to
        # exercise the graceful-failure branch end-to-end.
        assessment, warnings = plugin._assess_sb205_safe_harbor(
            system=sys_desc,
            actor_conformance_frameworks=["nist-ai-rmf"],
            actor_role="deployer",
            crosswalk_module_loader=_broken_loader,
        )
        assert assessment is None
        assert any("crosswalk" in w.lower() for w in warnings)

        # Sanity: end-to-end classify still succeeds even if we cannot
        # patch the lazy loader inside classify's default path. The EU
        # classification output is the primary invariant.
        result = plugin.classify({
            "system_description": sys_desc,
            "actor_conformance_frameworks": ["nist-ai-rmf"],
            "actor_role_for_sb205": "deployer",
        })
        assert result["risk_tier"] == "high-risk-annex-iii"
        assert "citations" in result
    finally:
        plugin._load_crosswalk_module = original_loader


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
