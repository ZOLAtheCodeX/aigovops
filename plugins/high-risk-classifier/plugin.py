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

from datetime import datetime, timezone
from typing import Any

AGENT_SIGNATURE = "high-risk-classifier/0.1.0"

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


def classify(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Classify an AI system under EU AI Act risk tiers.

    Args:
        inputs: Dict with:
            system_description: dict with required system_name, intended_use,
                                sector; optional description, deployment_context,
                                data_processed, annex_i_product_type,
                                annex_iii_self_declared (list of category keys),
                                article_5_self_declared (list),
                                article_6_3_exception_claimed (bool).
            reviewed_by: optional string.

    Returns:
        Dict with timestamp, agent_signature, risk_tier, rationale,
        annex_iii_matches, article_5_matches, annex_i_match, citations,
        requires_legal_review flag, warnings, reviewed_by.

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

    # Always cite Article 6 as the classification home.
    return {
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

    if result.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for w in result["warnings"]:
            lines.append(f"- {w}")

    lines.append("")
    return "\n".join(lines)
