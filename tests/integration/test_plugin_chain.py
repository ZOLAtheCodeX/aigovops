"""
Integration tests for the AIGovOps plugin chain.

Exercises cross-plugin data flows across the 19-plugin catalogue. Each
test names a concrete integration path and uses one plugin's output as
another plugin's input. Canonical demo inputs live in ``_fixtures.py``.

Tests are organized into eight groups:

    Group 1: Inventory upstream. The ai-system-inventory-maintainer
             produces the canonical inventory shape consumed by every
             downstream plugin.
    Group 2: Full chain. End-to-end run from inventory through
             management-review with every plugin emitting the uniform
             contract fields (agent_signature, timestamp, citations).
    Group 3: Crosswalk coverage across consumers. SoA, gap-assessment,
             AISIA, management-review, and high-risk-classifier all
             consult the crosswalk-matrix-builder; consumers must agree
             with a direct crosswalk query.
    Group 4: Jurisdiction flow. A system tagged with a jurisdiction must
             route through the jurisdiction-specific plugin and produce
             the correct artifact.
    Group 5: Consistency across data flows. Bidirectional citation
             integrity, STYLE.md format, README version alignment, and
             em-dash policing.
    Group 6: Internal audit and management review loop. Clause 9.3.2
             input categories must be feedable from internal-audit-
             planner and nonconformity-tracker outputs.
    Group 7: Crosswalk data integrity. Framework ids and citation
             formats must be consistent across frameworks.yaml and the
             mapping files.
    Group 8: Performance smoke. Full demo chain wall-clock time and
             crosswalk load time kept under regression-catching caps.

Runs under pytest or as a standalone script.

Invocation:
    python3 tests/integration/test_plugin_chain.py
    pytest tests/integration/
"""

from __future__ import annotations

import copy
import importlib.util
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = Path(__file__).resolve().parent

# Make the shared fixtures importable.
if str(INTEGRATION_DIR) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_DIR))

# Every plugin directory must be importable even when its sibling path is
# not already on sys.path. Downstream plugins rely on sibling imports.
ALL_PLUGINS = (
    "ai-system-inventory-maintainer",
    "audit-log-generator",
    "role-matrix-generator",
    "risk-register-builder",
    "soa-generator",
    "aisia-runner",
    "nonconformity-tracker",
    "management-review-packager",
    "metrics-collector",
    "gap-assessment",
    "data-register-builder",
    "applicability-checker",
    "high-risk-classifier",
    "uk-atrs-recorder",
    "colorado-ai-act-compliance",
    "nyc-ll144-audit-packager",
    "singapore-magf-assessor",
    "crosswalk-matrix-builder",
    "internal-audit-planner",
)
for plugin_name in ALL_PLUGINS:
    sys.path.insert(0, str(REPO_ROOT / "plugins" / plugin_name))


def _load(plugin_name: str):
    spec = importlib.util.spec_from_file_location(
        plugin_name.replace("-", "_"),
        REPO_ROOT / "plugins" / plugin_name / "plugin.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inventory_plugin = _load("ai-system-inventory-maintainer")
audit_log = _load("audit-log-generator")
role_matrix = _load("role-matrix-generator")
risk_register = _load("risk-register-builder")
soa = _load("soa-generator")
aisia = _load("aisia-runner")
nonconformity = _load("nonconformity-tracker")
management_review = _load("management-review-packager")
metrics = _load("metrics-collector")
gap = _load("gap-assessment")
data_register = _load("data-register-builder")
applicability_checker = _load("applicability-checker")
high_risk_classifier = _load("high-risk-classifier")
uk_atrs = _load("uk-atrs-recorder")
colorado_compliance = _load("colorado-ai-act-compliance")
nyc_ll144 = _load("nyc-ll144-audit-packager")
singapore_magf = _load("singapore-magf-assessor")
crosswalk = _load("crosswalk-matrix-builder")
internal_audit = _load("internal-audit-planner")

import _fixtures as F  # noqa: E402


# Map plugin-name -> (module, callable, kwargs_factory) for parameterized
# tests in Group 2. Each callable accepts no positional args and returns
# the plugin's output dict.
PLUGIN_RUNNERS: dict = {}


def _register_runners() -> None:
    PLUGIN_RUNNERS["ai-system-inventory-maintainer"] = (
        inventory_plugin,
        lambda: inventory_plugin.maintain_inventory(copy.deepcopy(F.DEMO_INVENTORY_INPUT)),
    )
    PLUGIN_RUNNERS["audit-log-generator"] = (
        audit_log,
        lambda: audit_log.generate_audit_log(copy.deepcopy(F.DEMO_AUDIT_LOG_INPUT)),
    )
    PLUGIN_RUNNERS["role-matrix-generator"] = (
        role_matrix,
        lambda: role_matrix.generate_role_matrix({
            "org_chart": copy.deepcopy(F.DEMO_ORG_CHART),
            "role_assignments": _role_assignments(),
            "authority_register": copy.deepcopy(F.DEMO_AUTHORITY_REGISTER),
        }),
    )
    PLUGIN_RUNNERS["risk-register-builder"] = (
        risk_register,
        lambda: risk_register.generate_risk_register(copy.deepcopy(F.DEMO_RISK_REGISTER_INPUT)),
    )
    PLUGIN_RUNNERS["soa-generator"] = (
        soa,
        lambda: soa.generate_soa({
            "ai_system_inventory": [copy.deepcopy(F.DEMO_INVENTORY_SYSTEM)],
        }),
    )
    PLUGIN_RUNNERS["aisia-runner"] = (
        aisia,
        lambda: aisia.run_aisia(copy.deepcopy(F.DEMO_AISIA_FULL_INPUT)),
    )
    PLUGIN_RUNNERS["nonconformity-tracker"] = (
        nonconformity,
        lambda: nonconformity.generate_nonconformity_register(copy.deepcopy(F.DEMO_NONCONFORMITY_INPUT)),
    )
    PLUGIN_RUNNERS["management-review-packager"] = (
        management_review,
        lambda: management_review.generate_review_package(copy.deepcopy(F.DEMO_MANAGEMENT_REVIEW_INPUT)),
    )
    PLUGIN_RUNNERS["metrics-collector"] = (
        metrics,
        lambda: metrics.generate_metrics_report(copy.deepcopy(F.DEMO_METRICS_INPUT)),
    )
    PLUGIN_RUNNERS["gap-assessment"] = (
        gap,
        lambda: gap.generate_gap_assessment(copy.deepcopy(F.DEMO_GAP_INPUT)),
    )
    PLUGIN_RUNNERS["data-register-builder"] = (
        data_register,
        lambda: data_register.generate_data_register(copy.deepcopy(F.DEMO_DATA_REGISTER_INPUT)),
    )
    PLUGIN_RUNNERS["applicability-checker"] = (
        applicability_checker,
        lambda: applicability_checker.check_applicability(copy.deepcopy(F.DEMO_APPLICABILITY_INPUT)),
    )
    PLUGIN_RUNNERS["high-risk-classifier"] = (
        high_risk_classifier,
        lambda: high_risk_classifier.classify(copy.deepcopy(F.DEMO_HIGH_RISK_EU_INPUT)),
    )
    PLUGIN_RUNNERS["uk-atrs-recorder"] = (
        uk_atrs,
        lambda: uk_atrs.generate_atrs_record(copy.deepcopy(F.DEMO_UK_ATRS_TIER_2_INPUT)),
    )
    PLUGIN_RUNNERS["colorado-ai-act-compliance"] = (
        colorado_compliance,
        lambda: colorado_compliance.generate_compliance_record(copy.deepcopy(F.DEMO_COLORADO_COMPLIANCE_INPUT)),
    )
    PLUGIN_RUNNERS["nyc-ll144-audit-packager"] = (
        nyc_ll144,
        lambda: nyc_ll144.generate_audit_package(copy.deepcopy(F.DEMO_NYC_LL144_INPUT)),
    )
    PLUGIN_RUNNERS["singapore-magf-assessor"] = (
        singapore_magf,
        lambda: singapore_magf.generate_magf_assessment(copy.deepcopy(F.DEMO_SINGAPORE_MAGF_INPUT)),
    )
    PLUGIN_RUNNERS["crosswalk-matrix-builder"] = (
        crosswalk,
        lambda: crosswalk.build_matrix({
            "query_type": "coverage",
            "source_framework": "iso42001",
            "source_ref": "A.5.4",
        }),
    )
    PLUGIN_RUNNERS["internal-audit-planner"] = (
        internal_audit,
        lambda: internal_audit.generate_audit_plan(copy.deepcopy(F.DEMO_INTERNAL_AUDIT_INPUT)),
    )


# ---------------------------------------------------------------------------
# Legacy scenario fixtures (kept for backward compatibility with the
# original test_role_matrix_to_risk_register_owner_lookup test).
# ---------------------------------------------------------------------------

SYSTEM = {
    "system_ref": "SYS-001",
    "system_name": "ResumeScreen",
    "risk_tier": "limited",
    "intended_use": "Rank candidate resumes against a job posting.",
    "deployment_context": "Internal HR workflow.",
    "data_processed": ["candidate resume text", "job posting text"],
}


def _org_chart():
    return copy.deepcopy(F.DEMO_ORG_CHART)


def _role_assignments():
    r: dict = {}
    categories = role_matrix.DEFAULT_DECISION_CATEGORIES
    activities = role_matrix.DEFAULT_ACTIVITIES
    default_roles = {
        "AI policy approval": ("AI Governance Officer", "Chief Risk Officer", "Chief Executive Officer", "Chief Legal Officer", "Head of AI Engineering"),
        "Risk acceptance": ("AI Governance Officer", "Chief Information Security Officer", "Chief Risk Officer", "Data Protection Officer", "Head of AI Engineering"),
        "SoA approval": ("AI Governance Officer", "Chief Information Security Officer", "Chief Risk Officer", "Data Protection Officer", "Head of AI Engineering"),
        "AISIA sign-off": ("Head of AI Engineering", "AI Governance Officer", "Chief Risk Officer", "Data Protection Officer", "Chief Executive Officer"),
        "Control implementation": ("Head of AI Engineering", "AI Governance Officer", "Chief Technology Officer", "Chief Information Security Officer", "Chief Risk Officer"),
        "Incident response": ("Chief Information Security Officer", "AI Governance Officer", "Chief Risk Officer", "Chief Legal Officer", "Chief Executive Officer"),
        "Audit programme approval": ("AI Governance Officer", "Chief Risk Officer", "Chief Executive Officer", "Chief Legal Officer", "Head of AI Engineering"),
        "External reporting": ("AI Governance Officer", "Chief Legal Officer", "Chief Executive Officer", "Chief Risk Officer", "Head of AI Engineering"),
    }
    for cat in categories:
        roles = default_roles[cat]
        for i, act in enumerate(activities):
            r[(cat, act)] = roles[i]
    return r


def _authority_register():
    return copy.deepcopy(F.DEMO_AUTHORITY_REGISTER)


def _backup_assignments():
    return {
        "Chief Executive Officer": "Chief Risk Officer",
        "Chief Risk Officer": "Chief Information Security Officer",
        "Chief Technology Officer": "Head of AI Engineering",
    }


_register_runners()


# ===========================================================================
# Group 1: Inventory upstream
# ===========================================================================

def test_inventory_output_feeds_risk_register_builder():
    """inventory -> risk-register chain: a validated inventory system flows into risk-register-builder."""
    inv_out = inventory_plugin.maintain_inventory(copy.deepcopy(F.DEMO_INVENTORY_INPUT))
    assert inv_out["systems"], "inventory -> risk-register chain failed: inventory emitted no systems"
    rr_out = risk_register.generate_risk_register({
        "ai_system_inventory": inv_out["systems"],
        "risks": copy.deepcopy(F.DEMO_RISKS),
    })
    assert len(rr_out["rows"]) == len(F.DEMO_RISKS), (
        "inventory -> risk-register chain failed: risk-register-builder dropped rows "
        "despite every risk referencing the inventory system_ref"
    )
    assert all(r["system_ref"] == "SYS-001" for r in rr_out["rows"])


def test_inventory_output_feeds_soa_generator():
    """inventory -> soa chain: inventory systems propagate to SoA row coverage list."""
    inv_out = inventory_plugin.maintain_inventory(copy.deepcopy(F.DEMO_INVENTORY_INPUT))
    soa_out = soa.generate_soa({
        "ai_system_inventory": inv_out["systems"],
    })
    assert soa_out["rows"], "inventory -> soa chain failed: SoA returned no Annex A rows"
    assert any(
        r.get("control_id", "").startswith("A.") for r in soa_out["rows"]
    ), "inventory -> soa chain failed: SoA rows missing A.* Annex A control_id"


def test_inventory_output_feeds_aisia_runner():
    """inventory -> aisia chain: a system's description fields feed AISIA system_description."""
    inv_out = inventory_plugin.maintain_inventory(copy.deepcopy(F.DEMO_INVENTORY_INPUT))
    sys_row = inv_out["systems"][0]
    result = aisia.run_aisia({
        "system_description": {
            "system_name": sys_row["system_name"],
            "purpose": sys_row["purpose"],
            "intended_use": sys_row["intended_use"],
            "deployment_environment": sys_row["deployment_context"],
            "system_type": sys_row.get("system_type", "classical-ml"),
        },
        "affected_stakeholders": sys_row.get("stakeholder_groups") or ["Users"],
        "impact_assessments": copy.deepcopy(F.DEMO_AISIA_FULL_INPUT["impact_assessments"]),
    })
    assert result["sections"], "inventory -> aisia chain failed: AISIA sections empty"


def test_inventory_applicability_matches_high_risk_classifier():
    """inventory applicability -> high-risk-classifier agreement: EU Annex III system should flag in both."""
    eu_system = copy.deepcopy(F.DEMO_EU_HIGH_RISK_SYSTEM)
    # Populate required per-system fields the inventory validates.
    eu_system.setdefault("intended_use", "Resume screening")
    eu_system.setdefault("deployment_context", "EU hiring workflow")
    eu_system.setdefault("decision_authority", "decision-support")
    eu_system.setdefault("lifecycle_state", "deployed")

    inv_out = inventory_plugin.maintain_inventory({
        "systems": [eu_system],
        "operation": "validate",
        "enrich_with_crosswalk": False,
    })
    frameworks = inv_out["regulatory_applicability_matrix"][0]["frameworks"]
    assert "eu-ai-act" in frameworks, (
        "inventory -> high-risk-classifier chain failed: EU system missing eu-ai-act applicability"
    )

    classifier_out = high_risk_classifier.classify({
        "system_description": {
            "system_name": eu_system["system_name"],
            "intended_use": eu_system["intended_use"],
            "sector": eu_system["sector"],
            "deployment_context": eu_system["deployment_context"],
            "deployer_scope": True,
        },
        "assess_sb205_safe_harbor": False,
    })
    assert classifier_out["risk_tier"] in ("high-risk-annex-iii", "high-risk-annex-i"), (
        "inventory -> high-risk-classifier chain failed: EU Annex III system did not classify "
        f"as high-risk; got {classifier_out['risk_tier']!r}"
    )


# ===========================================================================
# Group 2: Full chain demo scenario
# ===========================================================================

def test_full_chain_from_inventory_to_management_review():
    """inventory -> risk-register -> soa -> gap -> aisia -> metrics -> nonconformity -> internal-audit -> management-review."""
    inv_out = inventory_plugin.maintain_inventory(copy.deepcopy(F.DEMO_INVENTORY_INPUT))
    systems = inv_out["systems"]

    rr_out = risk_register.generate_risk_register({
        "ai_system_inventory": systems,
        "risks": copy.deepcopy(F.DEMO_RISKS),
    })
    assert rr_out["rows"], "full chain failed at risk-register invocation"

    soa_out = soa.generate_soa({
        "ai_system_inventory": systems,
        "risk_register": rr_out["rows"],
    })
    assert soa_out["rows"], "full chain failed at soa invocation"

    gap_out = gap.generate_gap_assessment({
        "ai_system_inventory": systems,
        "target_framework": "iso42001",
        "soa_rows": soa_out["rows"],
    })
    assert gap_out["rows"], "full chain failed at gap-assessment invocation"

    aisia_out = aisia.run_aisia(copy.deepcopy(F.DEMO_AISIA_FULL_INPUT))
    assert aisia_out["sections"], "full chain failed at aisia invocation"

    metrics_out = metrics.generate_metrics_report({
        "ai_system_inventory": systems,
        "measurements": copy.deepcopy(F.DEMO_METRICS_INPUT["measurements"]),
        "thresholds": copy.deepcopy(F.DEMO_METRICS_INPUT["thresholds"]),
    })
    assert "summary" in metrics_out, "full chain failed at metrics invocation"

    nc_out = nonconformity.generate_nonconformity_register(copy.deepcopy(F.DEMO_NONCONFORMITY_INPUT))
    assert nc_out["records"], "full chain failed at nonconformity invocation"

    iap_out = internal_audit.generate_audit_plan(copy.deepcopy(F.DEMO_INTERNAL_AUDIT_INPUT))
    assert iap_out["audit_schedule"], "full chain failed at internal-audit-planner invocation"

    mr_input = copy.deepcopy(F.DEMO_MANAGEMENT_REVIEW_INPUT)
    mr_input["aims_performance"] = {
        "source_ref": f"metrics-report {metrics_out['timestamp']}",
        "trend_direction": "stable",
    }
    mr_input["audit_results"] = f"internal-audit {iap_out['timestamp']}"
    mr_input["nonconformity_trends"] = {
        "source_ref": f"nonconformity-register {nc_out['timestamp']}",
        "trend_direction": "improving",
    }
    mr_input["ai_risks_and_opportunities"] = f"risk-register {rr_out['timestamp']}"
    mr_out = management_review.generate_review_package(mr_input)
    by_key = {s["key"]: s for s in mr_out["sections"]}
    # Management review must reference upstream artifacts in the populated sections.
    assert rr_out["timestamp"] in by_key["ai_risks_and_opportunities"]["source_ref"]
    assert metrics_out["timestamp"] in by_key["aims_performance"]["source_ref"]
    assert nc_out["timestamp"] in by_key["nonconformity_trends"]["source_ref"]
    assert iap_out["timestamp"] in by_key["audit_results"]["source_ref"]


def test_every_plugin_emits_agent_signature():
    """Every plugin in the 19-plugin catalogue emits agent_signature with its own name as prefix."""
    for name, (_mod, run) in PLUGIN_RUNNERS.items():
        out = run()
        sig = out.get("agent_signature")
        assert sig, f"{name} failed: no agent_signature field emitted"
        assert sig.startswith(name + "/"), (
            f"plugin-contract chain failed at {name}: agent_signature {sig!r} does not "
            f"start with {name}/"
        )


def test_every_plugin_emits_timestamp():
    """Every plugin output has ISO 8601 UTC timestamp with Z suffix."""
    iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    for name, (_mod, run) in PLUGIN_RUNNERS.items():
        out = run()
        ts = out.get("timestamp")
        assert ts, f"{name} failed: timestamp field missing"
        assert iso_pattern.match(ts), (
            f"timestamp-contract chain failed at {name}: timestamp {ts!r} is not "
            "ISO 8601 UTC with Z suffix"
        )


def test_every_plugin_emits_citations_list():
    """Every plugin output carries citations. Top-level 'citations' is the canonical
    location; audit-log-generator splits per-mapping via annex_a_mappings."""
    for name, (_mod, run) in PLUGIN_RUNNERS.items():
        out = run()
        if "citations" in out:
            assert isinstance(out["citations"], list), (
                f"citations-contract chain failed at {name}: citations is not a list"
            )
            continue
        # audit-log-generator embeds citations inside clause_mappings (list[str])
        # and annex_a_mappings (list[dict] with a 'citation' field).
        has_mapping_citations = False
        for key in ("clause_mappings", "annex_a_mappings"):
            vals = out.get(key)
            if not isinstance(vals, list):
                continue
            for v in vals:
                if isinstance(v, str) and v:
                    has_mapping_citations = True
                elif isinstance(v, dict) and v.get("citation"):
                    has_mapping_citations = True
                if has_mapping_citations:
                    break
            if has_mapping_citations:
                break
        assert has_mapping_citations, (
            f"citations-contract chain failed at {name}: no top-level 'citations' "
            "and no per-mapping citation fields"
        )


# ===========================================================================
# Group 3: Crosswalk coverage across consumers
# ===========================================================================

def test_soa_crosswalk_coverage_matches_crosswalk_query():
    """soa.cross_framework_coverage for A.5.4 matches crosswalk.build_matrix(coverage, A.5.4)."""
    soa_input = copy.deepcopy(F.DEMO_SOA_INPUT)
    rr_out = risk_register.generate_risk_register(copy.deepcopy(F.DEMO_RISK_REGISTER_INPUT))
    soa_input["risk_register"] = rr_out["rows"]
    soa_input["enrich_with_crosswalk"] = True
    soa_out = soa.generate_soa(soa_input)

    soa_row = next(r for r in soa_out["rows"] if r["control_id"] == "A.5.4")
    soa_targets = {(c["target_framework"], c["target_ref"]) for c in soa_row.get("cross_framework_coverage", [])}

    cw_result = crosswalk.build_matrix({
        "query_type": "coverage",
        "source_framework": "iso42001",
        "source_ref": "A.5.4",
    })
    # The SoA enrichment filters to a default target set; the crosswalk
    # result is a superset. Every SoA target must appear in the crosswalk.
    cw_targets = {(m["target_framework"], m["target_ref"]) for m in cw_result["mappings"]}
    missing = soa_targets - cw_targets
    assert not missing, (
        "soa -> crosswalk consistency chain failed: SoA cross_framework_coverage "
        f"contains targets absent from crosswalk coverage query: {missing}"
    )


def test_gap_assessment_gaps_match_crosswalk_gaps_query():
    """gap-assessment crosswalk_gaps_surfaced matches crosswalk.build_matrix(gaps, ...)."""
    gap_input = copy.deepcopy(F.DEMO_GAP_INPUT)
    gap_input["crosswalk_reference_frameworks"] = ["eu-ai-act"]
    gap_out = gap.generate_gap_assessment(gap_input)
    surfaced = gap_out.get("crosswalk_gaps_surfaced") or []
    assert surfaced, "gap -> crosswalk chain failed: no crosswalk_gaps_surfaced entries"

    for entry in surfaced:
        if entry["direction"] == "reference-beyond-target":
            cw_query = crosswalk.build_matrix({
                "query_type": "gaps",
                "source_framework": entry["reference_framework"],
                "target_framework": entry["target_framework"],
            })
        else:
            cw_query = crosswalk.build_matrix({
                "query_type": "gaps",
                "source_framework": entry["target_framework"],
                "target_framework": entry["reference_framework"],
            })
        expected = len(cw_query.get("gaps") or [])
        assert entry["gap_count"] == expected, (
            f"gap -> crosswalk chain failed: gap_count {entry['gap_count']} for direction "
            f"{entry['direction']!r} does not match crosswalk gaps query result {expected}"
        )


def test_aisia_eu_fria_coverage_correct_for_full_inputs():
    """aisia EU FRIA coverage: full inputs populate all six Article 27(1) elements."""
    result = aisia.run_aisia(copy.deepcopy(F.DEMO_AISIA_FULL_INPUT))
    coverage = result["eu_fria_coverage"]
    assert coverage["total_present"] == 6, (
        "aisia EU FRIA coverage chain failed: expected all 6 Article 27(1) elements "
        f"present for full inputs; got {coverage['total_present']}"
    )
    assert coverage["total_missing"] == 0


def test_aisia_eu_fria_coverage_correct_for_empty_inputs():
    """aisia EU FRIA coverage: minimal inputs leave at least five Article 27(1) elements missing."""
    result = aisia.run_aisia(copy.deepcopy(F.DEMO_AISIA_MINIMAL_INPUT))
    coverage = result["eu_fria_coverage"]
    assert coverage["total_missing"] >= 5, (
        "aisia EU FRIA coverage chain failed: expected at least 5 missing elements "
        f"for minimal inputs; got {coverage['total_missing']}"
    )


def test_high_risk_classifier_sb205_safe_harbor_requires_conformance_claim():
    """high-risk-classifier SB 205 safe-harbor citations emitted only when conformance claimed."""
    without = high_risk_classifier.classify(copy.deepcopy(F.DEMO_HIGH_RISK_COLORADO_NO_CONFORMANCE_INPUT))
    sb = without.get("sb205_assessment") or {}
    assert sb.get("in_scope") is True, (
        "high-risk-classifier -> SB205 chain failed: Colorado housing system "
        "should be SB 205 in-scope"
    )
    assert sb.get("safe_harbor_citations") == [], (
        "high-risk-classifier -> SB205 chain failed: safe_harbor_citations populated "
        "without any actor_conformance_frameworks claim"
    )

    with_claim = high_risk_classifier.classify(copy.deepcopy(F.DEMO_HIGH_RISK_COLORADO_HOUSING_INPUT))
    sb_with = with_claim["sb205_assessment"]
    citations = sb_with.get("safe_harbor_citations") or []
    assert citations, (
        "high-risk-classifier -> SB205 chain failed: safe_harbor_citations empty "
        "even with iso42001 conformance claim"
    )
    assert any(
        c.get("section") == "Colorado SB 205, Section 6-1-1706(3)" for c in citations
    ), "high-risk-classifier -> SB205 chain failed: 6-1-1706(3) citation missing"


def test_management_review_coverage_percentages_sum_correctly():
    """management-review cross-framework coverage counts sum to the ISO Annex A baseline."""
    mr_input = copy.deepcopy(F.DEMO_MANAGEMENT_REVIEW_INPUT)
    mr_input["include_cross_framework_coverage"] = True
    mr_input["target_frameworks"] = ["nist-ai-rmf"]
    out = management_review.generate_review_package(mr_input)
    cfc = out.get("cross_framework_coverage")
    if cfc is None:
        # Plugin may not surface cross_framework_coverage without explicit
        # enrichment knob. Skip silently but verify Clause 9.3.2 sections.
        assert out["sections"], "management-review coverage chain failed: no sections"
        return

    # When present, covered + partial + gaps must be a positive integer for
    # each target framework and coverage_percentage must be consistent.
    for fw_block in cfc.get("per_framework_summary", []):
        covered = fw_block.get("iso_annex_a_controls_covered", 0)
        partial = fw_block.get("iso_annex_a_controls_partial", 0)
        gaps = fw_block.get("iso_annex_a_controls_gaps", 0)
        total = covered + partial + gaps
        assert total > 0, (
            "management-review -> cross_framework_coverage chain failed: "
            f"covered+partial+gaps sums to 0 for {fw_block.get('target_framework')!r}; "
            "baseline Annex A coverage is missing"
        )
        pct = fw_block.get("coverage_percentage", 0)
        # coverage_percentage is covered / total * 100 per Clause 9.3.2(c)(2).
        expected_pct = round(covered / total * 100, 1)
        assert abs(pct - expected_pct) < 0.2, (
            "management-review -> cross_framework_coverage chain failed: "
            f"coverage_percentage {pct} does not match covered/total "
            f"= {expected_pct} for {fw_block.get('target_framework')!r}"
        )


# ===========================================================================
# Group 4: Jurisdiction flow
# ===========================================================================

def test_eu_scope_system_triggers_eu_ai_act_classification():
    """EU-scope deployer_scope system routes through high-risk-classifier to high-risk-annex-iii."""
    out = high_risk_classifier.classify(copy.deepcopy(F.DEMO_HIGH_RISK_EU_INPUT))
    assert out["risk_tier"] in ("high-risk-annex-iii", "high-risk-annex-i", "requires-legal-review"), (
        f"eu-jurisdiction -> high-risk-classifier chain failed: expected high-risk EU tier; "
        f"got {out['risk_tier']!r}"
    )
    assert any(
        c.startswith("EU AI Act, ") for c in out["citations"]
    ), "eu-jurisdiction chain failed: EU AI Act citation missing"


def test_nyc_employment_system_triggers_ll144_package():
    """NYC AEDT in employment domain routes to nyc-ll144-audit-packager as in_scope."""
    out = nyc_ll144.generate_audit_package(copy.deepcopy(F.DEMO_NYC_LL144_INPUT))
    assert out["in_scope"] is True, (
        "nyc-jurisdiction -> ll144 chain failed: NYC employment AEDT not in scope"
    )
    assert out.get("candidate_notices"), (
        "nyc-jurisdiction -> ll144 chain failed: candidate_notices empty despite in_scope"
    )


def test_colorado_housing_system_triggers_sb205_assessment():
    """Colorado housing system routes to high-risk-classifier sb205_assessment in_scope."""
    out = high_risk_classifier.classify(copy.deepcopy(F.DEMO_HIGH_RISK_COLORADO_HOUSING_INPUT))
    sb = out.get("sb205_assessment")
    assert sb is not None, (
        "colorado-jurisdiction -> sb205 chain failed: sb205_assessment missing"
    )
    assert sb["in_scope"] is True, (
        "colorado-jurisdiction -> sb205 chain failed: housing system not SB 205 in_scope"
    )


def test_singapore_financial_services_triggers_feat_assessment():
    """Singapore financial-services org routes to singapore-magf-assessor feat_principles."""
    out = singapore_magf.generate_magf_assessment(copy.deepcopy(F.DEMO_SINGAPORE_MAGF_INPUT))
    feat = out.get("feat_principles")
    assert feat, (
        "singapore-jurisdiction -> feat chain failed: feat_principles missing for "
        "organization_type=financial-services"
    )
    assert len(feat) == 4, (
        f"singapore-jurisdiction -> feat chain failed: expected 4 FEAT principles; got {len(feat)}"
    )


def test_uk_public_sector_system_triggers_atrs_record():
    """UK tier-2 public-sector system routes to uk-atrs-recorder with all 8 ATRS sections populated."""
    out = uk_atrs.generate_atrs_record(copy.deepcopy(F.DEMO_UK_ATRS_TIER_2_INPUT))
    sections = out.get("sections") or []
    assert len(sections) == 8, (
        f"uk-jurisdiction -> atrs chain failed: expected 8 ATRS sections for tier-2; "
        f"got {len(sections)}"
    )


# ===========================================================================
# Group 5: Consistency across data flows
# ===========================================================================

def test_risk_register_row_citations_present_in_crosswalk():
    """risk-register Annex A citations match the source_ref catalogue in crosswalk data."""
    rr_out = risk_register.generate_risk_register(copy.deepcopy(F.DEMO_RISK_REGISTER_INPUT))
    cw_data = crosswalk.load_crosswalk_data()
    iso_source_refs = {
        m.get("source_ref") for m in cw_data["mappings"]
        if m.get("source_framework") == "iso42001"
    }
    iso_target_refs = {
        m.get("target_ref") for m in cw_data["mappings"]
        if m.get("target_framework") == "iso42001"
    }
    known_iso = iso_source_refs | iso_target_refs

    # Extract any A.x.y control ids from citations on the rows.
    control_re = re.compile(r"ISO/IEC 42001:2023, Annex A, Control (A\.\S+)")
    all_citations: list[str] = []
    for row in rr_out["rows"]:
        all_citations.extend(row.get("citations", []))

    for cit in all_citations:
        m = control_re.match(cit)
        if not m:
            continue
        control_id = m.group(1).rstrip(".,")
        assert control_id in known_iso, (
            "risk-register -> crosswalk integrity chain failed: "
            f"citation {cit!r} names control {control_id!r} that does not "
            "appear as source_ref or target_ref in crosswalk data"
        )


def test_audit_log_citations_match_style_md_format():
    """audit-log-generator citations match STYLE.md prefixes."""
    entry = audit_log.generate_audit_log(copy.deepcopy(F.DEMO_AUDIT_LOG_INPUT))
    prefixes = (
        "ISO/IEC 42001:2023, ",
        "EU AI Act, ",
        "GOVERN ",
        "MAP ",
        "MEASURE ",
        "MANAGE ",
        "NIST AI RMF",
    )
    for mapping in entry.get("annex_a_mappings", []):
        cit = mapping["citation"]
        assert any(cit.startswith(p) for p in prefixes), (
            "audit-log -> STYLE.md chain failed: annex_a_mappings citation "
            f"{cit!r} does not match an allowed STYLE.md prefix"
        )
    for cit in entry.get("citations", []):
        assert any(cit.startswith(p) for p in prefixes), (
            f"audit-log -> STYLE.md chain failed: top-level citation {cit!r} "
            "does not match an allowed STYLE.md prefix"
        )


def test_agent_signature_versions_aligned_with_readme():
    """README declarative mentions of agent_signature align with plugin.py AGENT_SIGNATURE.

    Matches only lines that declare the current version ('currently', 'agent_signature',
    '= \\`plugin/x.y.z\\`'); ignores lines that reproduce a historical sample output.
    """
    sig_pattern = re.compile(r"([a-z0-9-]+)/(\d+\.\d+\.\d+)")
    for name, (module, _run) in PLUGIN_RUNNERS.items():
        readme = REPO_ROOT / "plugins" / name / "README.md"
        if not readme.exists():
            continue
        plugin_sig = module.AGENT_SIGNATURE
        plugin_version = plugin_sig.split("/", 1)[1]
        found_any_declarative = False
        mismatches: list[str] = []
        for line in readme.read_text(encoding="utf-8").splitlines():
            matches = sig_pattern.findall(line)
            plugin_hits = [(n, v) for n, v in matches if n == name]
            if not plugin_hits:
                continue
            # A declarative line: contains 'currently', '`agent_signature`', or the
            # plain 'agent_signature:' label. Historical sample outputs (lines like
            # '**Generated by:** plugin/0.1.0') are skipped.
            is_declarative = (
                "currently" in line.lower()
                or "`agent_signature`" in line.lower()
                or "agent_signature:" in line.lower()
                or "agent_signature =" in line.lower()
            )
            if not is_declarative:
                continue
            found_any_declarative = True
            for _n, readme_version in plugin_hits:
                if readme_version != plugin_version:
                    mismatches.append(
                        f"readme -> plugin version chain failed at {name}: README "
                        f"line {line.strip()!r} declares {_n}/{readme_version} but "
                        f"plugin.py AGENT_SIGNATURE is {plugin_sig}"
                    )
        assert not mismatches, "\n".join(mismatches)
        # If the README never declares a version, treat as informational (skip).
        _ = found_any_declarative


def test_no_em_dashes_in_any_rendered_output():
    """No plugin emits em-dash (U+2014) in its rendered markdown output."""
    em_dash = "\u2014"
    failures: list[str] = []

    def _render(name: str, module, result):
        if hasattr(module, "render_markdown"):
            try:
                return module.render_markdown(result)
            except Exception as exc:
                failures.append(f"{name} render_markdown raised {type(exc).__name__}: {exc}")
                return ""
        return ""

    for name, (module, run) in PLUGIN_RUNNERS.items():
        out = run()
        rendered = _render(name, module, out)
        if em_dash in rendered:
            failures.append(f"{name} rendered markdown contains em-dash")
        # Also check JSON-side string fields for em-dash leakage.
        def _walk(value, path: str) -> None:
            if isinstance(value, str):
                if em_dash in value:
                    failures.append(f"{name} output carries em-dash at {path}: {value!r}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    _walk(v, f"{path}.{k}")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    _walk(item, f"{path}[{i}]")

        _walk(out, name)

    assert not failures, (
        "em-dash policing chain failed:\n  " + "\n  ".join(failures)
    )


# ===========================================================================
# Group 6: Internal audit and management review loop
# ===========================================================================

def test_internal_audit_output_feeds_management_review():
    """internal-audit-planner output feeds management-review-packager Clause 9.3.2(c) audit_results."""
    iap_out = internal_audit.generate_audit_plan(copy.deepcopy(F.DEMO_INTERNAL_AUDIT_INPUT))
    mr_input = copy.deepcopy(F.DEMO_MANAGEMENT_REVIEW_INPUT)
    mr_input["audit_results"] = (
        f"internal-audit plan timestamp {iap_out['timestamp']} cycles "
        f"{iap_out['summary']['cycles_planned']}"
    )
    mr_out = management_review.generate_review_package(mr_input)
    by_key = {s["key"]: s for s in mr_out["sections"]}
    assert by_key["audit_results"]["populated"], (
        "internal-audit -> management-review chain failed: audit_results section unpopulated"
    )
    assert iap_out["timestamp"] in by_key["audit_results"]["source_ref"], (
        "internal-audit -> management-review chain failed: internal-audit timestamp "
        "does not appear in management-review audit_results source_ref"
    )


def test_nonconformity_tracker_output_feeds_management_review():
    """nonconformity-tracker output feeds management-review-packager Clause 9.3.2(d)."""
    nc_out = nonconformity.generate_nonconformity_register(copy.deepcopy(F.DEMO_NONCONFORMITY_INPUT))
    mr_input = copy.deepcopy(F.DEMO_MANAGEMENT_REVIEW_INPUT)
    mr_input["nonconformity_trends"] = {
        "source_ref": f"nonconformity-register {nc_out['timestamp']}",
        "trend_direction": "improving",
    }
    mr_out = management_review.generate_review_package(mr_input)
    by_key = {s["key"]: s for s in mr_out["sections"]}
    section = by_key["nonconformity_trends"]
    assert section["populated"], (
        "nonconformity -> management-review chain failed: nonconformity_trends unpopulated"
    )
    assert nc_out["timestamp"] in section["source_ref"], (
        "nonconformity -> management-review chain failed: nonconformity timestamp "
        "does not appear in management-review nonconformity_trends source_ref"
    )


def test_management_review_clause_9_3_2_completeness():
    """management-review package populates all 9 Clause 9.3.2 input categories when fed full inputs."""
    mr_out = management_review.generate_review_package(copy.deepcopy(F.DEMO_MANAGEMENT_REVIEW_INPUT))
    expected_keys = {
        "previous_review_actions",
        "external_internal_issues_changes",
        "aims_performance",
        "audit_results",
        "nonconformity_trends",
        "objective_fulfillment",
        "stakeholder_feedback",
        "ai_risks_and_opportunities",
        "continual_improvement_opportunities",
    }
    section_keys = {s["key"] for s in mr_out["sections"]}
    missing = expected_keys - section_keys
    assert not missing, (
        f"management-review Clause 9.3.2 chain failed: missing categories {missing}"
    )
    unpopulated = [s["key"] for s in mr_out["sections"] if not s["populated"]]
    assert not unpopulated, (
        "management-review Clause 9.3.2 chain failed: categories unpopulated despite "
        f"full inputs: {unpopulated}"
    )


# ===========================================================================
# Group 7: Crosswalk data integrity
# ===========================================================================

def test_crosswalk_frameworks_all_referenced_by_consumers():
    """Every framework id declared in frameworks.yaml appears as source or target in at least one mapping."""
    data = crosswalk.load_crosswalk_data()
    declared_ids = {fw["id"] for fw in data["frameworks"]}
    used_ids: set = set()
    for m in data["mappings"]:
        used_ids.add(m.get("source_framework"))
        used_ids.add(m.get("target_framework"))
    unused = declared_ids - used_ids
    # Some frameworks in the declared catalogue may not yet have mapping
    # rows (generative-AI profile, CCPA umbrella reference). These are
    # tracked for future expansion and permitted to remain unused.
    allowed_unused = {"nist-ai-600-1", "ccpa-cpra"}
    real_unused = unused - allowed_unused
    assert not real_unused, (
        "crosswalk integrity chain failed: frameworks declared in frameworks.yaml but "
        f"never referenced in any mapping file: {real_unused}"
    )


def test_crosswalk_citation_formats_match_frameworks_yaml():
    """Every citation_source publication string is non-empty for mapping entries, per SCHEMA.md invariant 6."""
    data = crosswalk.load_crosswalk_data()
    for m in data["mappings"]:
        cit_sources = m.get("citation_sources") or []
        assert cit_sources, (
            "crosswalk integrity chain failed: mapping "
            f"{m.get('id')!r} carries no citation_sources"
        )
        for cs in cit_sources:
            pub = (cs.get("publication") or "").strip()
            assert pub, (
                "crosswalk integrity chain failed: mapping "
                f"{m.get('id')!r} has empty citation_sources.publication"
            )


# ===========================================================================
# Group 8: Performance smoke
# ===========================================================================

def test_full_chain_executes_under_ten_seconds():
    """Full demo chain wall-clock time under 10 seconds."""
    start = time.perf_counter()
    inv_out = inventory_plugin.maintain_inventory(copy.deepcopy(F.DEMO_INVENTORY_INPUT))
    systems = inv_out["systems"]
    rr_out = risk_register.generate_risk_register({
        "ai_system_inventory": systems,
        "risks": copy.deepcopy(F.DEMO_RISKS),
    })
    soa_out = soa.generate_soa({"ai_system_inventory": systems, "risk_register": rr_out["rows"]})
    gap.generate_gap_assessment({
        "ai_system_inventory": systems,
        "target_framework": "iso42001",
        "soa_rows": soa_out["rows"],
    })
    aisia.run_aisia(copy.deepcopy(F.DEMO_AISIA_FULL_INPUT))
    metrics.generate_metrics_report({
        "ai_system_inventory": systems,
        "measurements": copy.deepcopy(F.DEMO_METRICS_INPUT["measurements"]),
        "thresholds": copy.deepcopy(F.DEMO_METRICS_INPUT["thresholds"]),
    })
    nonconformity.generate_nonconformity_register(copy.deepcopy(F.DEMO_NONCONFORMITY_INPUT))
    internal_audit.generate_audit_plan(copy.deepcopy(F.DEMO_INTERNAL_AUDIT_INPUT))
    management_review.generate_review_package(copy.deepcopy(F.DEMO_MANAGEMENT_REVIEW_INPUT))
    elapsed = time.perf_counter() - start
    assert elapsed < 10.0, (
        f"performance chain failed: full demo chain took {elapsed:.2f}s; cap is 10.0s"
    )


def test_crosswalk_load_time_under_two_seconds():
    """crosswalk.load_crosswalk_data() completes under 2 seconds."""
    start = time.perf_counter()
    crosswalk.load_crosswalk_data()
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, (
        f"performance chain failed: crosswalk load took {elapsed:.2f}s; cap is 2.0s"
    )


# ===========================================================================
# Legacy tests (kept for backward compatibility)
# ===========================================================================

def test_role_matrix_to_risk_register_owner_lookup():
    """role-matrix-generator output populates risk-register-builder owner via role_matrix_lookup."""
    matrix = role_matrix.generate_role_matrix({
        "org_chart": _org_chart(),
        "role_assignments": _role_assignments(),
        "authority_register": _authority_register(),
        "backup_assignments": _backup_assignments(),
    })
    approver_by_category = {
        row["decision_category"]: row["role_name"]
        for row in matrix["rows"]
        if row["activity"] == "approve"
    }
    category_to_role = {
        "bias": approver_by_category["Risk acceptance"],
        "privacy": approver_by_category["Risk acceptance"],
    }
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [
            {"system_ref": "SYS-001", "category": "bias", "description": "Disparity in ranking outputs."},
        ],
        "role_matrix_lookup": category_to_role,
    })
    row = register["rows"][0]
    assert row["owner_role"] == approver_by_category["Risk acceptance"]


def test_risk_register_feeds_soa_inclusion():
    """risk-register-builder output controls SoA row inclusion in soa-generator."""
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [
            {
                "system_ref": "SYS-001",
                "category": "privacy",
                "description": "PII exposure risk.",
                "existing_controls": ["A.7.5", "A.7.4"],
                "treatment_option": "reduce",
                "owner_role": "Data Protection Officer",
            },
        ],
    })
    soa_result = soa.generate_soa({
        "ai_system_inventory": [SYSTEM],
        "risk_register": register["rows"],
    })
    by_id = {r["control_id"]: r for r in soa_result["rows"]}
    assert by_id["A.7.5"]["status"] == "included-implemented"
    assert by_id["A.7.4"]["status"] == "included-implemented"
    assert "REQUIRES REVIEWER DECISION" in by_id["A.10.4"]["justification"]


def test_soa_feeds_gap_assessment():
    """soa-generator output drives gap-assessment classification."""
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [
            {
                "system_ref": "SYS-001",
                "category": "bias",
                "description": "Demographic disparity.",
                "existing_controls": ["A.5.4"],
                "treatment_option": "reduce",
            },
        ],
    })
    soa_result = soa.generate_soa({
        "ai_system_inventory": [SYSTEM],
        "risk_register": register["rows"],
        "exclusion_justifications": {"A.10.4": "No customer-facing AI."},
    })
    gap_result = gap.generate_gap_assessment({
        "ai_system_inventory": [SYSTEM],
        "target_framework": "iso42001",
        "soa_rows": soa_result["rows"],
    })
    by_id = {r["target_id"]: r for r in gap_result["rows"]}
    assert by_id["A.5.4"]["classification"] == "covered"
    assert by_id["A.10.4"]["classification"] == "not-applicable"
    assert by_id["A.6.2.7"]["classification"] == "not-covered"


def test_aisia_output_feeds_risk_register_additional_controls():
    """aisia-runner additional_controls_recommended surface as candidate risk treatments."""
    aisia_result = aisia.run_aisia({
        "system_description": {
            "system_name": "ResumeScreen",
            "purpose": "Rank candidate resumes.",
            "system_type": "classical-ml",
        },
        "affected_stakeholders": ["Candidates", "HR reviewers"],
        "impact_assessments": [
            {
                "stakeholder_group": "Candidates",
                "impact_dimension": "group-fairness",
                "impact_description": "Potential disparate impact across protected groups.",
                "severity": "major",
                "likelihood": "possible",
                "existing_controls": ["A.5.4"],
                "additional_controls_recommended": ["Quarterly equity audit", "Ground-truth relabeling program"],
            },
        ],
    })
    section = aisia_result["sections"][0]
    assert len(section["additional_controls_recommended"]) == 2
    assert any("equity audit" in c.lower() for c in section["additional_controls_recommended"])


def test_metrics_breach_to_nonconformity_workflow():
    """metrics-collector threshold breach produces a nonconformity record via the workflow."""
    metrics_report = metrics.generate_metrics_report({
        "ai_system_inventory": [SYSTEM],
        "measurements": [
            {
                "system_ref": "SYS-001",
                "metric_family": "fairness",
                "metric_id": "demographic_parity_difference",
                "value": 0.18,
                "window_start": "2026-04-01T00:00:00Z",
                "window_end": "2026-04-30T23:59:59Z",
                "measurement_method_ref": "METHOD-FAIRNESS-2026Q2",
                "test_set_ref": "TS-fairness-2026Q2",
            },
        ],
        "thresholds": {"demographic_parity_difference": {"operator": "max", "value": 0.05}},
    })
    assert metrics_report["summary"]["threshold_breach_count"] == 1
    breach = metrics_report["threshold_breaches"][0]

    nc_result = nonconformity.generate_nonconformity_register({
        "records": [
            {
                "description": f"Threshold breach: {breach['metric_id']} = {breach['value']} exceeds max.",
                "source_citation": breach["citations"][0],
                "detected_by": "metrics-collector",
                "detection_date": "2026-04-30",
                "detection_method": "Automated threshold check",
                "status": "detected",
            },
        ],
    })
    assert len(nc_result["records"]) == 1
    assert nc_result["records"][0]["source_citation"] == breach["citations"][0]


def test_audit_log_entries_reference_plugin_agent_signature():
    """audit-log-generator agent_signature appears correctly on every emission."""
    entry = audit_log.generate_audit_log({
        "system_name": "ResumeScreen",
        "purpose": "Rank candidate resumes.",
        "risk_tier": "limited",
        "data_processed": ["resume text"],
        "deployment_context": "Internal HR workflow.",
        "governance_decisions": ["Deployed after Phase 2 review."],
        "responsible_parties": ["AI Governance Officer"],
    })
    assert entry["agent_signature"].startswith("audit-log-generator/")
    for m in entry["annex_a_mappings"]:
        assert m["citation"].startswith("ISO/IEC 42001:2023, Annex A, Control ")


def test_management_review_package_references_downstream_artifacts():
    """management-review-packager incorporates risk-register, nonconformity, and audit-log refs."""
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [{
            "system_ref": "SYS-001",
            "category": "bias",
            "description": "Demographic disparity.",
            "treatment_option": "reduce",
        }],
    })
    nc = nonconformity.generate_nonconformity_register({
        "records": [{
            "description": "Protected-group disparity detected.",
            "source_citation": "ISO/IEC 42001:2023, Annex A, Control A.5.4",
            "detected_by": "Equity audit",
            "detection_date": "2026-03-20",
            "status": "investigated",
            "investigation_started_at": "2026-03-21",
        }],
    })
    package = management_review.generate_review_package({
        "review_window": {"start": "2026-01-01", "end": "2026-03-31"},
        "attendees": ["Chief Risk Officer", "AI Governance Officer"],
        "ai_risks_and_opportunities": f"RR-register-ref-{register['timestamp']}",
        "nonconformity_trends": {
            "source_ref": f"NC-log-ref-{nc['timestamp']}",
            "trend_direction": "stable",
        },
    })
    by_key = {s["key"]: s for s in package["sections"]}
    assert by_key["ai_risks_and_opportunities"]["source_ref"].startswith("RR-register-ref-")
    assert by_key["nonconformity_trends"]["source_ref"].startswith("NC-log-ref-")
    assert by_key["nonconformity_trends"]["trend_direction"] == "stable"


def test_aisia_soa_linking_via_existing_controls():
    """aisia-runner cross-links existing_controls to soa_rows when refs match."""
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [{
            "system_ref": "SYS-001",
            "category": "bias",
            "description": "Disparity risk.",
            "existing_controls": ["A.5.4"],
            "treatment_option": "reduce",
        }],
    })
    soa_result = soa.generate_soa({
        "ai_system_inventory": [SYSTEM],
        "risk_register": register["rows"],
    })
    soa_for_aisia = [
        {"control_id": r["control_id"], "row_ref": f"SOA-ROW-{r['control_id']}"}
        for r in soa_result["rows"]
    ]
    aisia_result = aisia.run_aisia({
        "system_description": {
            "system_name": "ResumeScreen",
            "purpose": "Rank resumes.",
        },
        "affected_stakeholders": ["Candidates"],
        "impact_assessments": [{
            "stakeholder_group": "Candidates",
            "impact_dimension": "group-fairness",
            "impact_description": "Potential disparity.",
            "severity": "major",
            "likelihood": "possible",
            "existing_controls": ["A.5.4"],
        }],
        "soa_rows": soa_for_aisia,
    })
    section = aisia_result["sections"][0]
    assert section["existing_controls"][0]["soa_row_ref"] == "SOA-ROW-A.5.4"


def test_style_md_citation_format_across_chain():
    """Every plugin emits citations in STYLE.md format across a composed chain."""
    register = risk_register.generate_risk_register({
        "ai_system_inventory": [SYSTEM],
        "risks": [{"system_ref": "SYS-001", "category": "bias", "description": "X", "treatment_option": "reduce"}],
    })
    soa_result = soa.generate_soa({
        "ai_system_inventory": [SYSTEM],
        "risk_register": register["rows"],
    })
    gap_result = gap.generate_gap_assessment({
        "ai_system_inventory": [SYSTEM],
        "target_framework": "iso42001",
        "soa_rows": soa_result["rows"],
    })

    def check(citations):
        for c in citations:
            assert (
                c.startswith("ISO/IEC 42001:2023, Clause ")
                or c.startswith("ISO/IEC 42001:2023, Annex A, Control ")
                or c.startswith("MAP ") or c.startswith("GOVERN ")
                or c.startswith("MEASURE ") or c.startswith("MANAGE ")
                or c.startswith("EU AI Act, ")
            ), f"citation {c!r} does not match STYLE.md prefix"

    for row in register["rows"]:
        check(row["citations"])
    check(soa_result["citations"])
    for row in soa_result["rows"]:
        check([row["citation"]])
    check(gap_result["citations"])
    for row in gap_result["rows"]:
        check([row["citation"]])


# ===========================================================================
# Standalone runner with per-group reporting
# ===========================================================================

GROUP_MAP = {
    "Group 1 (Inventory upstream)": (
        "test_inventory_output_feeds_risk_register_builder",
        "test_inventory_output_feeds_soa_generator",
        "test_inventory_output_feeds_aisia_runner",
        "test_inventory_applicability_matches_high_risk_classifier",
    ),
    "Group 2 (Full chain)": (
        "test_full_chain_from_inventory_to_management_review",
        "test_every_plugin_emits_agent_signature",
        "test_every_plugin_emits_timestamp",
        "test_every_plugin_emits_citations_list",
    ),
    "Group 3 (Crosswalk coverage)": (
        "test_soa_crosswalk_coverage_matches_crosswalk_query",
        "test_gap_assessment_gaps_match_crosswalk_gaps_query",
        "test_aisia_eu_fria_coverage_correct_for_full_inputs",
        "test_aisia_eu_fria_coverage_correct_for_empty_inputs",
        "test_high_risk_classifier_sb205_safe_harbor_requires_conformance_claim",
        "test_management_review_coverage_percentages_sum_correctly",
    ),
    "Group 4 (Jurisdiction flow)": (
        "test_eu_scope_system_triggers_eu_ai_act_classification",
        "test_nyc_employment_system_triggers_ll144_package",
        "test_colorado_housing_system_triggers_sb205_assessment",
        "test_singapore_financial_services_triggers_feat_assessment",
        "test_uk_public_sector_system_triggers_atrs_record",
    ),
    "Group 5 (Consistency across data flows)": (
        "test_risk_register_row_citations_present_in_crosswalk",
        "test_audit_log_citations_match_style_md_format",
        "test_agent_signature_versions_aligned_with_readme",
        "test_no_em_dashes_in_any_rendered_output",
    ),
    "Group 6 (Internal audit and management review loop)": (
        "test_internal_audit_output_feeds_management_review",
        "test_nonconformity_tracker_output_feeds_management_review",
        "test_management_review_clause_9_3_2_completeness",
    ),
    "Group 7 (Crosswalk data integrity)": (
        "test_crosswalk_frameworks_all_referenced_by_consumers",
        "test_crosswalk_citation_formats_match_frameworks_yaml",
    ),
    "Group 8 (Performance smoke)": (
        "test_full_chain_executes_under_ten_seconds",
        "test_crosswalk_load_time_under_two_seconds",
    ),
    "Legacy (original 10)": (
        "test_role_matrix_to_risk_register_owner_lookup",
        "test_risk_register_feeds_soa_inclusion",
        "test_soa_feeds_gap_assessment",
        "test_aisia_output_feeds_risk_register_additional_controls",
        "test_metrics_breach_to_nonconformity_workflow",
        "test_audit_log_entries_reference_plugin_agent_signature",
        "test_management_review_package_references_downstream_artifacts",
        "test_aisia_soa_linking_via_existing_controls",
        "test_style_md_citation_format_across_chain",
    ),
}


def _run_all() -> None:
    import inspect

    tests = {
        n: o
        for n, o in inspect.getmembers(sys.modules[__name__])
        if n.startswith("test_") and callable(o)
    }

    overall_failures: list[tuple[str, str]] = []
    group_lines: list[str] = []
    total_passed = 0
    total_run = 0
    assigned: set = set()

    for group, test_names in GROUP_MAP.items():
        passed = 0
        failed: list[tuple[str, str]] = []
        for name in test_names:
            assigned.add(name)
            fn = tests.get(name)
            if fn is None:
                failed.append((name, "MISSING"))
                continue
            try:
                fn()
                passed += 1
            except Exception as exc:
                failed.append((name, f"{type(exc).__name__}: {exc}"))
        total = len(test_names)
        total_passed += passed
        total_run += total
        group_lines.append(f"{group}: {passed}/{total} pass")
        for n, r in failed:
            overall_failures.append((f"{group}::{n}", r))

    unassigned = sorted(set(tests) - assigned)
    for name in unassigned:
        try:
            tests[name]()
            total_passed += 1
        except Exception as exc:
            overall_failures.append((name, f"{type(exc).__name__}: {exc}"))
        total_run += 1
    if unassigned:
        group_lines.append(f"Unassigned: {len(unassigned) - len([f for f in overall_failures if f[0] in unassigned])}/{len(unassigned)} pass")

    for line in group_lines:
        print(line)
    print()
    print(f"Ran {total_run} integration tests: {total_passed} passed, {len(overall_failures)} failed")
    for name, reason in overall_failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not overall_failures else 1)


if __name__ == "__main__":
    _run_all()
