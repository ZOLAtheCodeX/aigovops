"""
AIGovOps: EU AI Act High-Risk Classifier Plugin

Classifies an AI system under EU AI Act Article 5 (prohibited), Article 6(1)
(high-risk via Annex I product-safety route), Article 6(2) and Annex III
(high-risk by use case), or as limited-risk or minimal-risk. Produces a
structured classification record with citation anchors.

Design stance: the plugin does NOT make the final classification decision.
Article 5 prohibited-practice determinations and Article 6(3) exception
determinations are legal calls requiring qualified counsel. The plugin
applies a deterministic rule set over the system description, returns a
classification with rationale, and explicitly flags cases that require
human legal review (rather than silently deciding).

Status: Phase 4 implementation. Closes the Tier 2 gap in the eu-ai-act
operationalization map.
"""

from __future__ import annotations

import csv
import importlib.util
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "high-risk-classifier/0.2.0"

_CROSSWALK_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder"

# Colorado SB 205 consequential-decision domains that bring a system into
# scope. Source: Colorado SB 205 Section 6-1-1701(3) and Section 6-1-1701(9).
COLORADO_SB205_DOMAINS = (
    "education",
    "employment",
    "financial-lending",
    "essential-government",
    "health-care",
    "housing",
    "insurance",
    "legal-services",
)

# Values accepted in ``actor_conformance_frameworks`` for Colorado SB 205
# safe-harbor analysis. These are the framework identifiers named in Section
# 6-1-1706(3).
VALID_SB205_CONFORMANCE_FRAMEWORKS = ("nist-ai-rmf", "iso42001")

VALID_SB205_ACTOR_ROLES = ("developer", "deployer", "both")

VALID_RISK_TIERS = (
    "prohibited",
    "high-risk-annex-iii",
    "high-risk-annex-i",
    "limited-risk",
    "minimal-risk",
    "requires-legal-review",
)

# Annex III categories (Article 6(2) + Annex III). Each category maps to a
# human-readable label and the sectors/intended uses that trigger it.
ANNEX_III_CATEGORIES = {
    "biometrics": {
        "label": "Point 1: Biometrics",
        "triggers": ("biometric identification", "biometric categorisation", "emotion recognition",
                     "face recognition", "facial identification"),
    },
    "critical-infrastructure": {
        "label": "Point 2: Critical infrastructure",
        "triggers": ("road traffic", "railway traffic", "water supply", "gas supply", "heating supply",
                     "electricity supply", "critical digital infrastructure"),
    },
    "education": {
        "label": "Point 3: Education and vocational training",
        "triggers": ("admission to educational institutions", "educational assessment",
                     "student evaluation", "assigning students to educational institutions",
                     "monitoring prohibited behaviour during tests"),
    },
    "employment-workers-management": {
        "label": "Point 4: Employment, workers management, and access to self-employment",
        "triggers": ("recruitment", "hiring", "resume screening", "candidate ranking",
                     "performance evaluation", "task allocation based on behaviour",
                     "monitoring workers", "termination decisions"),
    },
    "essential-services": {
        "label": "Point 5: Access to and enjoyment of essential private and public services",
        "triggers": ("eligibility for public assistance", "credit scoring", "creditworthiness",
                     "health insurance pricing", "life insurance pricing", "emergency first response",
                     "emergency calls triage"),
    },
    "law-enforcement": {
        "label": "Point 6: Law enforcement",
        "triggers": ("risk assessment for victims", "risk assessment for offenders",
                     "lie detector", "polygraph", "emotional state assessment during interviews",
                     "evidence reliability assessment", "predictive policing for individuals",
                     "profiling for crime analysis"),
    },
    "migration-asylum-border": {
        "label": "Point 7: Migration, asylum, and border control management",
        "triggers": ("lie detector at borders", "risk assessment for entry", "examination of asylum applications",
                     "document authenticity verification at borders", "identification at borders"),
    },
    "justice-democracy": {
        "label": "Point 8: Administration of justice and democratic processes",
        "triggers": ("assisting judicial authority research", "assisting judicial authority interpretation",
                     "influencing election outcomes", "influencing referenda outcomes"),
    },
}

# Article 5 prohibited-practice triggers. These are flags not hard rules because
# the determination is legal, but the plugin surfaces any match for explicit
# human review.
ARTICLE_5_TRIGGERS = {
    "subliminal-manipulation": (
        "Article 5(1)(a): subliminal, purposefully manipulative, or deceptive techniques with objective "
        "or effect of materially distorting behaviour and causing significant harm."
    ),
    "vulnerability-exploitation": (
        "Article 5(1)(b): exploiting vulnerabilities of natural persons due to age, disability, or specific "
        "social or economic situation to materially distort behaviour causing significant harm."
    ),
    "social-scoring": (
        "Article 5(1)(c): social scoring of natural persons by public authorities or on their behalf."
    ),
    "real-time-biometric-public": (
        "Article 5(1)(d): real-time remote biometric identification in publicly accessible spaces "
        "for law-enforcement purposes (narrow exceptions apply)."
    ),
    "predictive-policing-profiling": (
        "Article 5(1)(e): predictive policing based solely on profiling or personality-trait assessment."
    ),
    "emotion-recognition-workplace-education": (
        "Article 5(1)(f): emotion recognition in workplace or education (narrow medical/safety exceptions)."
    ),
    "biometric-categorisation-sensitive": (
        "Article 5(1)(g): biometric categorisation by sensitive characteristics (race, political opinions, "
        "trade-union membership, religion, sexual orientation, and so on)."
    ),
    "untargeted-facial-scraping": (
        "Article 5(1)(h): untargeted scraping of facial images from internet or CCTV for facial recognition databases."
    ),
}

REQUIRED_INPUT_FIELDS = ("system_description",)
REQUIRED_SYSTEM_FIELDS = ("system_name", "intended_use", "sector")

VALID_INPUT_FIELDS = (
    "system_description",
    "reviewed_by",
    "assess_sb205_safe_harbor",
    "actor_conformance_frameworks",
    "actor_role_for_sb205",
)


def _validate(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")
    system = inputs["system_description"]
    if not isinstance(system, dict):
        raise ValueError("system_description must be a dict")
    missing_sys = [f for f in REQUIRED_SYSTEM_FIELDS if f not in system]
    if missing_sys:
        raise ValueError(f"system_description missing required fields: {sorted(missing_sys)}")

    assess_flag = inputs.get("assess_sb205_safe_harbor", True)
    if not isinstance(assess_flag, bool):
        raise ValueError("assess_sb205_safe_harbor must be a bool")

    frameworks = inputs.get("actor_conformance_frameworks", [])
    if not isinstance(frameworks, list):
        raise ValueError("actor_conformance_frameworks must be a list")
    for fw in frameworks:
        if fw not in VALID_SB205_CONFORMANCE_FRAMEWORKS:
            raise ValueError(
                f"Invalid actor_conformance_frameworks value '{fw}'. "
                f"Must be one of {VALID_SB205_CONFORMANCE_FRAMEWORKS}."
            )

    role = inputs.get("actor_role_for_sb205")
    if role is not None and role not in VALID_SB205_ACTOR_ROLES:
        raise ValueError(
            f"Invalid actor_role_for_sb205 '{role}'. "
            f"Must be one of {VALID_SB205_ACTOR_ROLES} or None."
        )


def _emotion_recognition_workplace_education_matcher(text: str) -> tuple[str, ...]:
    """Article 5(1)(f) matcher: emotion recognition in workplace or education context.

    Match when the text mentions emotion recognition/detection AND a workplace
    or education context cue. Biases toward surfacing; caller confirms or
    denies via legal review."""
    lower = text.lower()
    emo_cues = ("emotion recognition", "emotion detection", "mood detection",
                "affect detection", "facial expression analysis")
    ctx_cues = ("employee", "workplace", "office", "staff", "worker",
                "student", "pupil", "classroom", "school", "education",
                "university", "college", "meeting", "class ")
    if any(e in lower for e in emo_cues) and any(c in lower for c in ctx_cues):
        return ("emotion recognition + workplace/education context",)
    return ()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _match_triggers(text: str, triggers: tuple[str, ...]) -> list[str]:
    text_lower = text.lower()
    return [t for t in triggers if t in text_lower]


def _screen_article_5(system: dict[str, Any]) -> list[dict[str, str]]:
    """Return a list of Article 5 matches. Each match is a legal-review hit."""
    matches: list[dict[str, str]] = []
    combined_text = " ".join([
        str(system.get("intended_use", "")),
        str(system.get("description", "")),
        str(system.get("deployment_context", "")),
        " ".join(str(x) for x in (system.get("data_processed") or [])),
    ])
    flagged_categories = system.get("article_5_self_declared") or []

    for cat_key, explanation in ARTICLE_5_TRIGGERS.items():
        # Caller can self-declare (cleanest); keyword match is fallback signal.
        if cat_key in flagged_categories:
            matches.append({"category": cat_key, "explanation": explanation, "source": "self-declared"})
            continue
        # Simple keyword match for obvious cases. Some categories use custom
        # matchers (context-aware) that return a tuple of match-descriptions;
        # presence of any element indicates a match.
        if cat_key == "emotion-recognition-workplace-education":
            custom_matches = _emotion_recognition_workplace_education_matcher(combined_text)
            if custom_matches:
                matches.append({"category": cat_key, "explanation": explanation,
                                "source": "context-aware-match",
                                "match_detail": custom_matches[0]})
            continue

        keywords = {
            "subliminal-manipulation": ("subliminal",),
            "vulnerability-exploitation": ("exploit", "manipulate vulnerable"),
            "social-scoring": ("social scoring", "citizen score"),
            "real-time-biometric-public": ("real-time biometric", "live facial recognition in public"),
            "predictive-policing-profiling": ("predictive policing", "crime prediction based on profile"),
            "biometric-categorisation-sensitive": ("categorise by race", "categorise by ethnicity", "categorise by religion", "categorise by sexual orientation", "categorise by political", "biometric categorisation by sensitive"),
            "untargeted-facial-scraping": ("scrape facial", "scraped facial", "untargeted facial"),
        }.get(cat_key, ())
        if any(kw in combined_text.lower() for kw in keywords):
            matches.append({"category": cat_key, "explanation": explanation, "source": "keyword-match"})
    return matches


def _match_annex_iii(system: dict[str, Any]) -> list[dict[str, str]]:
    """Return Annex III category matches."""
    matches: list[dict[str, str]] = []
    combined_text = " ".join([
        str(system.get("intended_use", "")),
        str(system.get("description", "")),
        str(system.get("deployment_context", "")),
        str(system.get("sector", "")),
    ])
    self_declared = system.get("annex_iii_self_declared") or []

    for cat_key, meta in ANNEX_III_CATEGORIES.items():
        if cat_key in self_declared:
            matches.append({"category": cat_key, "label": meta["label"], "source": "self-declared"})
            continue
        hits = _match_triggers(combined_text, meta["triggers"])
        if hits:
            matches.append({
                "category": cat_key,
                "label": meta["label"],
                "source": "keyword-match",
                "triggers_matched": hits,
            })
    return matches


def _screen_annex_i(system: dict[str, Any]) -> dict[str, Any] | None:
    """Return Annex I product-safety determination if caller declared it."""
    product_type = system.get("annex_i_product_type")
    if not product_type:
        return None
    return {
        "product_type": product_type,
        "explanation": (
            f"System declared as a safety component of, or itself covered by, "
            f"Union harmonisation legislation listed in Annex I (product type: {product_type}). "
            "Article 6(1) high-risk applies; subject to conformity assessment under Annex I legislation."
        ),
    }


def _load_crosswalk_module():
    """Import the sibling crosswalk-matrix-builder plugin module.

    Lazy import so classification with assess_sb205_safe_harbor=False does
    not pay the YAML-load cost and is immune to crosswalk-side failures.
    """
    plugin_path = _CROSSWALK_DIR / "plugin.py"
    if not plugin_path.exists():
        raise ImportError(f"crosswalk plugin not found at {plugin_path}")
    spec = importlib.util.spec_from_file_location(
        "_aigovops_crosswalk_plugin_hrc", plugin_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _system_in_sb205_scope(system: dict[str, Any]) -> tuple[bool, list[str]]:
    """Determine whether the system operates in a Colorado SB 205
    consequential-decision domain.

    Returns (in_scope, matched_domains). Matching prefers the explicit
    ``consequential_decision_domains`` list. If absent, falls back to the
    ``sector`` field and matches on substring.
    """
    declared = system.get("consequential_decision_domains")
    if isinstance(declared, list) and declared:
        matched = [d for d in declared if d in COLORADO_SB205_DOMAINS]
        return (bool(matched), matched)

    sector = str(system.get("sector", "")).lower()
    # Sector-string fallback mapping. Conservative: exact-token or clear
    # substring alignments only.
    sector_to_domain = {
        "education": "education",
        "employment": "employment",
        "hr": "employment",
        "human-resources": "employment",
        "financial-lending": "financial-lending",
        "lending": "financial-lending",
        "credit": "financial-lending",
        "government": "essential-government",
        "essential-government": "essential-government",
        "health-care": "health-care",
        "healthcare": "health-care",
        "health": "health-care",
        "housing": "housing",
        "insurance": "insurance",
        "legal-services": "legal-services",
        "legal": "legal-services",
    }
    matched: list[str] = []
    for token, domain in sector_to_domain.items():
        if token in sector and domain not in matched:
            matched.append(domain)
    return (bool(matched), matched)


def _assess_sb205_safe_harbor(
    system: dict[str, Any],
    actor_conformance_frameworks: list[str],
    actor_role: str | None,
    crosswalk_module_loader=_load_crosswalk_module,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Run the Colorado SB 205 safe-harbor assessment.

    Returns (assessment_dict_or_None, top_level_warnings). If the sibling
    crosswalk plugin fails to load, returns (None, [warning]) so the EU
    classification output remains intact.
    """
    top_level_warnings: list[str] = []
    in_scope, matched_domains = _system_in_sb205_scope(system)

    if not in_scope:
        return (
            {
                "in_scope": False,
                "reason": (
                    "System is not deployed in a Colorado SB 205 "
                    "consequential-decision domain (education, employment, "
                    "financial-lending, essential-government, health-care, "
                    "housing, insurance, legal-services)."
                ),
                "safe_harbor_applicable": False,
            },
            top_level_warnings,
        )

    try:
        crosswalk = crosswalk_module_loader()
        presumption_result = crosswalk.build_matrix({
            "query_type": "matrix",
            "source_framework": "colorado-sb-205",
            "relationship_filter": ["statutory-presumption"],
        })
    except Exception as exc:
        top_level_warnings.append(
            f"Colorado SB 205 safe-harbor assessment skipped: crosswalk "
            f"load failed ({type(exc).__name__}: {exc}). EU AI Act "
            "classification is unaffected."
        )
        return (None, top_level_warnings)

    presumption_rows = presumption_result.get("mappings", [])
    target_frameworks_in_data = {
        row.get("target_framework") for row in presumption_rows
    }

    warnings: list[str] = []
    citations: list[dict[str, str]] = []
    recommended_actions: list[str] = []

    claimed = list(actor_conformance_frameworks)
    has_claim = bool(claimed)

    # Section 6-1-1706(3) applies when the actor claims NIST or ISO
    # conformance AND occupies a deployer role (or both). Developers are
    # covered by the same presumption language in the statute; a developer
    # who is not also a deployer still benefits from conformance evidence
    # for 6-1-1702(1) reasonable-care defence.
    role_qualifies_for_6_1_1706_3 = actor_role in ("deployer", "both", "developer")

    section_6_1_1706_3_applies = False
    section_6_1_1706_4_applies = False

    for fw in claimed:
        if fw in target_frameworks_in_data:
            if role_qualifies_for_6_1_1706_3:
                section_6_1_1706_3_applies = True
            # Section 6-1-1706(4) affirmative defense attaches to any actor
            # who conforms to a recognized framework and cures the
            # violation. Role-independent.
            section_6_1_1706_4_applies = True
            citations.append({
                "section": "Colorado SB 205, Section 6-1-1706(3)",
                "presumption_target": fw,
            })

    if not has_claim:
        warnings.append(
            "No claimed conformance to NIST AI RMF or ISO 42001 provided. "
            "Colorado SB 205 safe-harbor not available. Consider conforming "
            "to gain Section 6-1-1706(3) rebuttable presumption."
        )
    else:
        if actor_role is None:
            warnings.append(
                "actor_role_for_sb205 not provided. Section 6-1-1706(3) "
                "presumption determination requires role designation "
                "(developer, deployer, or both)."
            )
        if "nist-ai-rmf" in claimed:
            recommended_actions.append(
                "Maintain NIST AI RMF conformance documentation"
            )
        if "iso42001" in claimed:
            recommended_actions.append(
                "Maintain ISO/IEC 42001 AIMS conformance documentation and "
                "Clause 9.2 internal audit records"
            )
        if section_6_1_1706_3_applies:
            recommended_actions.append(
                "If discrimination claim arises, invoke 6-1-1706(3) "
                "rebuttable presumption"
            )
        recommended_actions.append(
            "Continue Clause 9.2 internal audit (ISO) or continuous "
            "improvement practice (NIST MANAGE 4.2) to maintain presumption"
        )

    assessment = {
        "in_scope": True,
        "matched_domains": matched_domains,
        "actor_role": actor_role,
        "section_6_1_1706_3_applies": section_6_1_1706_3_applies,
        "section_6_1_1706_4_applies": section_6_1_1706_4_applies,
        "claimed_conformance": claimed,
        "safe_harbor_citations": citations,
        "recommended_actions": recommended_actions,
        "warnings": warnings,
    }
    return (assessment, top_level_warnings)


def classify(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Classify an AI system under EU AI Act risk tiers and, when in scope,
    assess Colorado SB 205 safe-harbor posture.

    Args:
        inputs: Dict with:
            system_description: dict with required system_name, intended_use,
                                sector; optional description, deployment_context,
                                data_processed, annex_i_product_type,
                                annex_iii_self_declared (list of category keys),
                                article_5_self_declared (list),
                                article_6_3_exception_claimed (bool),
                                consequential_decision_domains (list, optional).
            reviewed_by: optional string.
            assess_sb205_safe_harbor: bool (default True). Set to False to
                                skip the Colorado SB 205 safe-harbor
                                assessment entirely.
            actor_conformance_frameworks: list[str] (default []). Names the
                                frameworks the actor claims conformance to.
                                Accepted values: "nist-ai-rmf", "iso42001".
            actor_role_for_sb205: str | None (default None). One of
                                "developer", "deployer", "both", or None.

    Returns:
        Dict with timestamp, agent_signature, risk_tier, rationale,
        annex_iii_matches, article_5_matches, annex_i_match, citations,
        requires_legal_review, warnings, reviewed_by, summary. Includes
        sb205_assessment when assess_sb205_safe_harbor is True.

    Raises:
        ValueError: if required inputs are missing or malformed.
    """
    _validate(inputs)
    system = inputs["system_description"]
    warnings: list[str] = []

    article_5_matches = _screen_article_5(system)
    annex_iii_matches = _match_annex_iii(system)
    annex_i_match = _screen_annex_i(system)

    # Classification logic in precedence order.
    requires_legal_review = False
    rationale_parts: list[str] = []
    citations: list[str] = ["EU AI Act, Article 6"]

    if article_5_matches:
        # Prohibited practice flagged: always requires legal review.
        risk_tier = "requires-legal-review"
        requires_legal_review = True
        cats = ", ".join(m["category"] for m in article_5_matches)
        rationale_parts.append(
            f"Article 5 prohibited-practice categories flagged: {cats}. "
            "Determination is a legal call; the plugin does not auto-classify as 'prohibited'. "
            "Legal review required before any deployment decision."
        )
        citations.insert(0, "EU AI Act, Article 5")
        warnings.append(
            "system matches Article 5 prohibited-practice triggers; legal review required."
        )
    elif annex_i_match:
        risk_tier = "high-risk-annex-i"
        rationale_parts.append(annex_i_match["explanation"])
        citations.append("EU AI Act, Article 6(1)")
        citations.append("EU AI Act, Annex I")
    elif annex_iii_matches:
        # Check Article 6(3) exception claim.
        if system.get("article_6_3_exception_claimed"):
            risk_tier = "requires-legal-review"
            requires_legal_review = True
            cats = ", ".join(m["category"] for m in annex_iii_matches)
            rationale_parts.append(
                f"System matches Annex III categories: {cats}. Caller has claimed Article 6(3) "
                "exception (system does not pose significant risk of harm). This determination "
                "requires legal review and documented analysis before it is accepted. The plugin "
                "flags the exception claim rather than auto-accepting it."
            )
            citations.insert(0, "EU AI Act, Article 6(3)")
            citations.append("EU AI Act, Article 6(2)")
            citations.append("EU AI Act, Annex III")
            warnings.append(
                "Article 6(3) exception claimed but not yet validated. Claim requires documented "
                "analysis per Article 6(3) criteria before classification defaults to high-risk."
            )
        else:
            risk_tier = "high-risk-annex-iii"
            cats = ", ".join(m["category"] for m in annex_iii_matches)
            rationale_parts.append(
                f"System matches Annex III high-risk categories: {cats}. "
                "Article 6(2) classifies as high-risk; Chapter III requirements apply."
            )
            citations.append("EU AI Act, Article 6(2)")
            citations.append("EU AI Act, Annex III")
    else:
        # Check transparency-only triggers (Article 50).
        if _has_transparency_obligation(system):
            risk_tier = "limited-risk"
            rationale_parts.append(
                "System triggers Article 50 transparency obligations (interaction with AI, "
                "synthetic content marking, deep-fake labelling, emotion recognition disclosure) "
                "but does not meet high-risk criteria."
            )
            citations.append("EU AI Act, Article 50")
        else:
            risk_tier = "minimal-risk"
            rationale_parts.append(
                "System does not meet Article 5 prohibited-practice criteria, Article 6(1) "
                "product-safety route, or Article 6(2)/Annex III categories, and does not trigger "
                "Article 50 transparency obligations. Voluntary best-practice adoption recommended; "
                "no mandatory Chapter III obligations."
            )

    if risk_tier in ("high-risk-annex-iii", "high-risk-annex-i"):
        # Article 27 FRIA requirement for deployers of high-risk systems.
        if system.get("deployer_scope"):
            rationale_parts.append(
                "Deployer obligations apply per Article 26. Article 27 Fundamental Rights Impact "
                "Assessment required before first deployment if deployer is in scope."
            )
            citations.append("EU AI Act, Article 26")
            citations.append("EU AI Act, Article 27")

    # Colorado SB 205 safe-harbor assessment. Additive to EU classification.
    assess_sb205 = inputs.get("assess_sb205_safe_harbor", True)
    sb205_assessment = None
    if assess_sb205:
        sb205_assessment, sb205_top_warnings = _assess_sb205_safe_harbor(
            system=system,
            actor_conformance_frameworks=inputs.get(
                "actor_conformance_frameworks", []
            ),
            actor_role=inputs.get("actor_role_for_sb205"),
        )
        warnings.extend(sb205_top_warnings)

    # Always cite Article 6 as the classification home.
    output: dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "framework": "eu-ai-act",
        "system_description_echo": system,
        "risk_tier": risk_tier,
        "rationale": "\n\n".join(rationale_parts),
        "annex_iii_matches": annex_iii_matches,
        "article_5_matches": article_5_matches,
        "annex_i_match": annex_i_match,
        "requires_legal_review": requires_legal_review,
        "citations": citations,
        "warnings": warnings,
        "reviewed_by": inputs.get("reviewed_by"),
        "summary": {
            "risk_tier": risk_tier,
            "requires_legal_review": requires_legal_review,
            "annex_iii_match_count": len(annex_iii_matches),
            "article_5_flag_count": len(article_5_matches),
        },
    }

    if sb205_assessment is not None:
        output["sb205_assessment"] = sb205_assessment
        output["summary"]["sb205_in_scope"] = sb205_assessment.get("in_scope", False)
        output["summary"]["sb205_6_1_1706_3_applies"] = sb205_assessment.get(
            "section_6_1_1706_3_applies", False
        )

    return output


def _has_transparency_obligation(system: dict[str, Any]) -> bool:
    combined = " ".join([
        str(system.get("intended_use", "")),
        str(system.get("description", "")),
        str(system.get("system_type", "")),
    ]).lower()
    return any(t in combined for t in (
        "chatbot", "conversational ai", "synthetic media", "deep fake", "generative ai",
        "emotion recognition", "biometric categorisation",
    ))


def render_markdown(result: dict[str, Any]) -> str:
    required = ("timestamp", "risk_tier", "rationale", "citations")
    missing = [k for k in required if k not in result]
    if missing:
        raise ValueError(f"result missing required fields: {missing}")

    sys_desc = result.get("system_description_echo", {})
    lines = [
        f"# EU AI Act Risk-Tier Classification: {sys_desc.get('system_name', 'unknown system')}",
        "",
        f"**Generated at (UTC):** {result['timestamp']}",
        f"**Generated by:** {result['agent_signature']}",
        f"**Risk tier:** {result['risk_tier']}",
        f"**Requires legal review:** {result.get('requires_legal_review', False)}",
    ]
    if result.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {result['reviewed_by']}")
    lines.extend([
        "",
        "## Rationale",
        "",
        result["rationale"],
        "",
        "## Applicable Citations",
        "",
    ])
    for c in result["citations"]:
        lines.append(f"- {c}")

    if result.get("article_5_matches"):
        lines.extend(["", "## Article 5 prohibited-practice flags", ""])
        for m in result["article_5_matches"]:
            lines.append(f"- **{m['category']}** ({m['source']}): {m['explanation']}")

    if result.get("annex_iii_matches"):
        lines.extend(["", "## Annex III high-risk category matches", ""])
        for m in result["annex_iii_matches"]:
            triggers = m.get("triggers_matched") or []
            trigger_text = f" (matched: {', '.join(triggers)})" if triggers else ""
            lines.append(f"- **{m['label']}** ({m['source']}){trigger_text}")

    if result.get("annex_i_match"):
        lines.extend(["", "## Annex I product-safety route", ""])
        m = result["annex_i_match"]
        lines.append(f"- Product type: {m['product_type']}")
        lines.append(f"- {m['explanation']}")

    sb205 = result.get("sb205_assessment")
    if sb205 is not None:
        lines.extend(["", "## Colorado SB 205 safe-harbor assessment", ""])
        lines.append(f"- In scope: {sb205.get('in_scope', False)}")
        if sb205.get("in_scope"):
            domains = sb205.get("matched_domains") or []
            if domains:
                lines.append(
                    f"- Matched consequential-decision domains: {', '.join(domains)}"
                )
            lines.append(f"- Actor role: {sb205.get('actor_role')}")
            claimed = sb205.get("claimed_conformance") or []
            lines.append(
                "- Claimed conformance: "
                + (", ".join(claimed) if claimed else "(none)")
            )
            lines.append(
                f"- Section 6-1-1706(3) applies: "
                f"{sb205.get('section_6_1_1706_3_applies', False)}"
            )
            lines.append(
                f"- Section 6-1-1706(4) applies: "
                f"{sb205.get('section_6_1_1706_4_applies', False)}"
            )
            citations_sb = sb205.get("safe_harbor_citations") or []
            if citations_sb:
                lines.extend(["", "### Safe-harbor citations", ""])
                for c in citations_sb:
                    lines.append(
                        f"- {c.get('section')} "
                        f"(presumption target: {c.get('presumption_target')})"
                    )
            actions = sb205.get("recommended_actions") or []
            if actions:
                lines.extend(["", "### Recommended actions", ""])
                for a in actions:
                    lines.append(f"- {a}")
            sb_warnings = sb205.get("warnings") or []
            if sb_warnings:
                lines.extend(["", "### Assessment warnings", ""])
                for w in sb_warnings:
                    lines.append(f"- {w}")
        else:
            reason = sb205.get("reason")
            if reason:
                lines.append(f"- Reason: {reason}")
            lines.append(
                f"- Safe-harbor applicable: "
                f"{sb205.get('safe_harbor_applicable', False)}"
            )

    if result.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in result["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)


def render_csv(result: dict[str, Any]) -> str:
    """Render a single-row CSV summary of the classification result.

    Columns cover the EU AI Act classification outputs plus the Colorado
    SB 205 safe-harbor summary columns. Consumers that only need a compact
    audit-log row rather than the full markdown artifact use this renderer.
    """
    required = ("timestamp", "risk_tier")
    missing = [k for k in required if k not in result]
    if missing:
        raise ValueError(f"result missing required fields: {missing}")

    sys_desc = result.get("system_description_echo", {})
    sb205 = result.get("sb205_assessment") or {}
    claimed = sb205.get("claimed_conformance") or []

    buf = io.StringIO()
    writer = csv.writer(buf)
    header = [
        "timestamp",
        "agent_signature",
        "system_name",
        "risk_tier",
        "requires_legal_review",
        "annex_iii_match_count",
        "article_5_flag_count",
        "sb205_in_scope",
        "sb205_6_1_1706_3_applies",
        "sb205_claimed_conformance",
    ]
    writer.writerow(header)
    writer.writerow([
        result.get("timestamp", ""),
        result.get("agent_signature", ""),
        sys_desc.get("system_name", ""),
        result.get("risk_tier", ""),
        result.get("requires_legal_review", False),
        len(result.get("annex_iii_matches") or []),
        len(result.get("article_5_matches") or []),
        sb205.get("in_scope", False) if result.get("sb205_assessment") else "",
        sb205.get("section_6_1_1706_3_applies", False)
        if result.get("sb205_assessment")
        else "",
        "|".join(claimed),
    ])
    return buf.getvalue()
