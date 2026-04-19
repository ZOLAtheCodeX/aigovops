"""
Canonical demo inputs for integration tests.

One central place that shapes every plugin's inputs for cross-plugin data
flow tests. Tests should deep-copy these dicts before mutating them so
state never leaks between tests.

No em-dashes, no hedging, no emojis. Every string conforms to STYLE.md.
"""

from __future__ import annotations

import copy
from typing import Any


# ---------------------------------------------------------------------------
# Inventory and system fixtures
# ---------------------------------------------------------------------------

DEMO_INVENTORY_SYSTEM: dict[str, Any] = {
    "system_id": "SYS-001",
    "system_ref": "SYS-001",
    "system_name": "ResumeScreen",
    "intended_use": "Rank candidate resumes against a job posting to surface a reviewer queue.",
    "purpose": "Rank candidate resumes against a job posting.",
    "deployment_context": "Internal HR workflow. Human reviews every surfaced candidate.",
    "risk_tier": "limited",
    "decision_authority": "decision-support",
    "jurisdiction": ["usa-federal"],
    "lifecycle_state": "deployed",
    "sector": "employment",
    "data_processed": [
        "candidate resume text",
        "job posting text",
        "candidate-supplied demographic fields",
    ],
    "stakeholder_groups": ["Candidates", "HR reviewers"],
    "owner_role": "Head of AI Engineering",
    "operator_role": "HR Operations Manager",
    "model_family": "classical-ml",
    "training_data_provenance": "Historical applicant tracking system exports 2020 to 2024.",
    "post_market_monitoring_plan_ref": "PMM-SYS-001-2026",
    "risk_register_ref": "RR-SYS-001",
    "aisia_ref": "AISIA-SYS-001",
    "soa_ref": "SOA-SYS-001",
    "last_reviewed_date": "2026-03-01",
    "next_review_due_date": "2026-09-01",
    "system_type": "classical-ml",
    "reversibility": "outputs are suggestions; human makes every decision",
}


DEMO_EU_HIGH_RISK_SYSTEM: dict[str, Any] = {
    "system_id": "SYS-EU-HR-001",
    "system_name": "EUResumeScreen",
    "intended_use": "Resume screening and candidate ranking for HR in the EU.",
    "purpose": "Resume screening for EU employment.",
    "deployment_context": "EU hiring workflow with recruiter oversight.",
    "risk_tier": "high-risk-annex-iii",
    "decision_authority": "decision-support",
    "jurisdiction": ["eu"],
    "lifecycle_state": "deployed",
    "sector": "employment",
    "data_processed": ["candidate resume text"],
    "deployer_scope": True,
    "citations": ["EU AI Act, Article 6"],
}


DEMO_INVENTORY_INPUT: dict[str, Any] = {
    "systems": [copy.deepcopy(DEMO_INVENTORY_SYSTEM)],
    "operation": "validate",
    "enrich_with_crosswalk": False,
    "reviewed_by": "AI Governance Committee 2026-Q2",
}


# ---------------------------------------------------------------------------
# Risk register
# ---------------------------------------------------------------------------

DEMO_RISKS: list[dict[str, Any]] = [
    {
        "id": "RR-0001",
        "system_ref": "SYS-001",
        "category": "bias",
        "description": "Protected-group disparity in ranking outputs.",
        "likelihood": "possible",
        "impact": "major",
        "existing_controls": ["A.5.4", "A.7.4"],
        "treatment_option": "reduce",
        "owner_role": "AI Governance Officer",
    },
    {
        "id": "RR-0002",
        "system_ref": "SYS-001",
        "category": "privacy",
        "description": "Candidate PII exposure in inference telemetry.",
        "likelihood": "unlikely",
        "impact": "major",
        "existing_controls": ["A.7.5", "A.7.4"],
        "treatment_option": "reduce",
        "owner_role": "Data Protection Officer",
    },
]


DEMO_RISK_REGISTER_INPUT: dict[str, Any] = {
    "ai_system_inventory": [copy.deepcopy(DEMO_INVENTORY_SYSTEM)],
    "risks": copy.deepcopy(DEMO_RISKS),
    "framework": "iso42001",
    "reviewed_by": "AI Governance Committee 2026-Q2",
}


# ---------------------------------------------------------------------------
# SoA
# ---------------------------------------------------------------------------

DEMO_SOA_INPUT: dict[str, Any] = {
    "ai_system_inventory": [copy.deepcopy(DEMO_INVENTORY_SYSTEM)],
    "risk_register": [],  # Populated in tests from a risk register run.
    "exclusion_justifications": {
        "A.10.4": "No customer-facing AI services in AIMS scope.",
        "A.9.3": "No generative AI use in this scope.",
    },
    "reviewed_by": "AI Governance Committee 2026-Q2",
}


# ---------------------------------------------------------------------------
# AISIA
# ---------------------------------------------------------------------------

DEMO_AISIA_FULL_INPUT: dict[str, Any] = {
    "system_description": {
        "system_name": "ResumeScreen",
        "purpose": "Rank candidate resumes.",
        "intended_use": "Internal HR candidate ranking.",
        "decision_authority": "decision-support",
        "deployment_environment": "Internal HR workflow.",
        "reversibility": "outputs are suggestions",
        "system_type": "classical-ml",
        "process_description": (
            "Resumes are embedded, scored against a job posting, and ranked. "
            "The top candidates surface in a reviewer queue for a human HR "
            "reviewer to evaluate."
        ),
    },
    "affected_stakeholders": ["Candidates", "HR reviewers"],
    "assessment_period": "2026-Q2 through 2026-Q3",
    "frequency": "quarterly",
    "human_oversight": "HR reviewer reviews every surfaced candidate before any advance or reject decision.",
    "mitigations": "Quarterly equity audit plus PII redaction in telemetry.",
    "risks_if_materialised": "Candidate disparity complaint, follow-up fairness audit, retraining.",
    "impact_assessments": [
        {
            "stakeholder_group": "Candidates",
            "impact_dimension": "group-fairness",
            "impact_description": "Potential disparate impact across protected groups.",
            "severity": "major",
            "likelihood": "possible",
            "existing_controls": ["A.5.4"],
            "additional_controls_recommended": ["Quarterly equity audit"],
        },
        {
            "stakeholder_group": "Candidates",
            "impact_dimension": "human-oversight",
            "impact_description": "Reviewer may over-rely on rank order.",
            "severity": "moderate",
            "likelihood": "likely",
            "existing_controls": ["A.8.2"],
        },
    ],
    "verify_eu_fria_coverage": True,
    "reviewed_by": "AI Governance Committee 2026-Q2",
}


DEMO_AISIA_MINIMAL_INPUT: dict[str, Any] = {
    "system_description": {
        "system_name": "MinimalSystem",
        "purpose": "Trivial internal tool.",
    },
    "affected_stakeholders": ["Internal users"],
    "verify_eu_fria_coverage": True,
}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

DEMO_METRICS_INPUT: dict[str, Any] = {
    "ai_system_inventory": [copy.deepcopy(DEMO_INVENTORY_SYSTEM)],
    "measurements": [
        {
            "system_ref": "SYS-001",
            "metric_family": "fairness",
            "metric_id": "demographic_parity_difference",
            "value": 0.04,
            "window_start": "2026-04-01T00:00:00Z",
            "window_end": "2026-04-30T23:59:59Z",
            "measurement_method_ref": "METHOD-FAIRNESS-2026Q2",
            "test_set_ref": "TS-fairness-2026Q2",
        },
    ],
    "thresholds": {"demographic_parity_difference": {"operator": "max", "value": 0.05}},
    "reviewed_by": "AI Governance Committee 2026-Q2",
}


# ---------------------------------------------------------------------------
# Nonconformity
# ---------------------------------------------------------------------------

DEMO_NONCONFORMITY_INPUT: dict[str, Any] = {
    "records": [
        {
            "id": "NC-DEMO-001",
            "description": "Protected-group disparity detected in quarterly equity audit.",
            "source_citation": "ISO/IEC 42001:2023, Annex A, Control A.5.4",
            "detected_by": "Equity audit",
            "detection_date": "2026-03-20",
            "status": "investigated",
            "investigation_started_at": "2026-03-21",
        },
    ],
    "reviewed_by": "AI Governance Committee 2026-Q2",
}


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

DEMO_AUDIT_LOG_INPUT: dict[str, Any] = {
    "system_name": "ResumeScreen",
    "purpose": "Rank candidate resumes.",
    "risk_tier": "limited",
    "data_processed": ["resume text", "job posting text"],
    "deployment_context": "Internal HR workflow.",
    "governance_decisions": ["Deployed after Phase 2 review."],
    "responsible_parties": ["AI Governance Officer", "Head of AI Engineering"],
}


# ---------------------------------------------------------------------------
# Role matrix
# ---------------------------------------------------------------------------

DEMO_ORG_CHART: list[dict[str, Any]] = [
    {"role_name": "Chief Executive Officer"},
    {"role_name": "Chief Risk Officer", "reports_to": "Chief Executive Officer"},
    {"role_name": "AI Governance Officer", "reports_to": "Chief Risk Officer"},
    {"role_name": "Data Protection Officer", "reports_to": "Chief Risk Officer"},
    {"role_name": "Chief Information Security Officer", "reports_to": "Chief Risk Officer"},
    {"role_name": "Chief Technology Officer", "reports_to": "Chief Executive Officer"},
    {"role_name": "Head of AI Engineering", "reports_to": "Chief Technology Officer"},
    {"role_name": "Chief Legal Officer", "reports_to": "Chief Executive Officer"},
]


DEMO_AUTHORITY_REGISTER: dict[str, Any] = {
    "Chief Executive Officer": "Board Resolution 2024-01",
    "Chief Risk Officer": "Delegation of Authority Policy",
    "Chief Technology Officer": "Delegation of Authority Policy",
    "AI Governance Officer": "AI Governance Charter 2025",
    "Data Protection Officer": "GDPR Article 37 Appointment",
    "Chief Information Security Officer": "Information Security Policy",
    "Head of AI Engineering": "Job Description 2025",
    "Chief Legal Officer": "General Counsel Appointment",
}


# ---------------------------------------------------------------------------
# Management review
# ---------------------------------------------------------------------------

DEMO_MANAGEMENT_REVIEW_INPUT: dict[str, Any] = {
    "review_window": {"start": "2026-04-01", "end": "2026-06-30"},
    "attendees": [
        "Chief Executive Officer",
        "Chief Risk Officer",
        "AI Governance Officer",
        "Data Protection Officer",
    ],
    "previous_review_actions": "MR-2026-Q1-action-log",
    "external_internal_issues_changes": "CHG-log-2026-Q2",
    "aims_performance": {
        "source_ref": "KPI-report-2026-Q2",
        "trend_direction": "stable",
    },
    "audit_results": "IA-2026-Q2-report",
    "nonconformity_trends": {
        "source_ref": "NC-log-2026-Q2",
        "trend_direction": "improving",
    },
    "objective_fulfillment": "OBJ-status-2026-Q2",
    "stakeholder_feedback": ["HR operations: positive reception."],
    "ai_risks_and_opportunities": "RR-register-2026-Q2",
    "continual_improvement_opportunities": ["Automate reviewer training refresh."],
    "meeting_metadata": {"scheduled_date": "2026-07-15"},
    "reviewed_by": "AI Governance Committee 2026-Q2",
}


# ---------------------------------------------------------------------------
# Internal audit planner
# ---------------------------------------------------------------------------

DEMO_INTERNAL_AUDIT_INPUT: dict[str, Any] = {
    "scope": {
        "aims_boundaries": "All production AI systems at Acme.",
        "systems_in_scope": ["ResumeScreen"],
        "clauses_in_scope": ["4.1", "6.1", "7.5", "8.3", "9.1", "10.2"],
        "annex_a_in_scope": ["A.2", "A.3", "A.5", "A.6", "A.7", "A.8"],
    },
    "audit_frequency_months": 12,
    "audit_criteria": [
        "ISO/IEC 42001:2023",
        "Acme AI Governance Policy v1.2",
    ],
    "auditor_pool": [
        {
            "name": "Alice",
            "role": "Lead Auditor",
            "independence_level": "independent",
            "qualifications": ["ISO 42001 Lead Auditor"],
        },
    ],
    "management_system_risk_register_ref": "RR-2026-Q1",
    "enrich_with_crosswalk": False,
}


# ---------------------------------------------------------------------------
# Gap assessment
# ---------------------------------------------------------------------------

DEMO_GAP_INPUT: dict[str, Any] = {
    "ai_system_inventory": [copy.deepcopy(DEMO_INVENTORY_SYSTEM)],
    "target_framework": "iso42001",
    "soa_rows": [],
    "scope_boundary": "All AI systems in HR processes.",
    "reviewed_by": "AI Governance Committee 2026-Q2",
}


# ---------------------------------------------------------------------------
# Data register
# ---------------------------------------------------------------------------

DEMO_DATA_REGISTER_INPUT: dict[str, Any] = {
    "data_inventory": [
        {
            "id": "DS-001",
            "name": "ResumeCorpus",
            "purpose_stage": "training",
            "source": "internal",
            "system_refs": ["SYS-001"],
            "sensitivity_class": "pii",
            "includes_bias_check": True,
        },
    ],
    "reviewed_by": "AI Governance Committee 2026-Q2",
}


# ---------------------------------------------------------------------------
# Applicability checker
# ---------------------------------------------------------------------------

DEMO_APPLICABILITY_INPUT: dict[str, Any] = {
    "system_description": {
        "system_name": "ResumeScreen",
        "sector": "employment",
        "deployment_context": "Internal HR workflow.",
        "jurisdiction": ["eu"],
        "risk_tier": "high-risk-annex-iii",
    },
    "target_date": "2027-08-02",
    "enforcement_timeline": {
        "enforcement_events": [
            {
                "event_id": "eu-aia-high-risk",
                "date": "2026-08-02",
                "article_ref": "EU AI Act, Article 113",
                "description": "High-risk obligations enter into application.",
                "applies_to_risk_tiers": ["high-risk-annex-iii"],
                "applies_to_jurisdictions": ["eu"],
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# High-risk classifier
# ---------------------------------------------------------------------------

DEMO_HIGH_RISK_EU_INPUT: dict[str, Any] = {
    "system_description": {
        "system_name": "EUResumeScreen",
        "intended_use": "Resume screening and candidate ranking for EU employment.",
        "sector": "employment",
        "deployment_context": "EU hiring workflow.",
        "data_processed": ["candidate resume text"],
        "deployer_scope": True,
    },
    "assess_sb205_safe_harbor": False,
}


DEMO_HIGH_RISK_COLORADO_HOUSING_INPUT: dict[str, Any] = {
    "system_description": {
        "system_name": "HousingScore",
        "intended_use": "Score tenant applications for Colorado landlords.",
        "sector": "housing",
        "deployment_context": "Colorado residential leasing workflow.",
        "consequential_decision_domains": ["housing"],
    },
    "actor_conformance_frameworks": ["iso42001"],
    "actor_role_for_sb205": "deployer",
}


DEMO_HIGH_RISK_COLORADO_NO_CONFORMANCE_INPUT: dict[str, Any] = {
    "system_description": {
        "system_name": "HousingScore",
        "intended_use": "Score tenant applications for Colorado landlords.",
        "sector": "housing",
        "deployment_context": "Colorado residential leasing workflow.",
        "consequential_decision_domains": ["housing"],
    },
    "actor_conformance_frameworks": [],
    "actor_role_for_sb205": "deployer",
}


# ---------------------------------------------------------------------------
# NYC LL144
# ---------------------------------------------------------------------------

DEMO_NYC_LL144_INPUT: dict[str, Any] = {
    "aedt_description": {
        "tool_name": "ResumeScreen-NYC",
        "vendor": "HireTech Inc.",
        "decision_category": "screen",
        "substantially_assists_decision": True,
        "used_for_nyc_candidates_or_employees": True,
    },
    "employer_role": "employer",
    "audit_data": {
        "audit_date": "2026-04-01",
        "auditor_identity": "Doe and Associates, Independent Auditor",
        "selection_rates": {
            "race_ethnicity": {
                "White (Not Hispanic or Latino)": 0.40,
                "Black or African American (Not Hispanic or Latino)": 0.32,
                "Hispanic or Latino": 0.30,
                "Asian (Not Hispanic or Latino)": 0.38,
            },
            "sex": {"Male": 0.37, "Female": 0.34},
        },
        "distribution_comparison": {"baseline": "applicant pool 2025 Q4"},
    },
}


# ---------------------------------------------------------------------------
# Colorado AI Act compliance
# ---------------------------------------------------------------------------

DEMO_COLORADO_COMPLIANCE_INPUT: dict[str, Any] = {
    "actor_role": "deployer",
    "system_description": {
        "system_name": "HousingScore",
        "substantial_factor": True,
        "impact_assessment_inputs": {
            "ia-purpose-use": "Described.",
            "ia-risk-analysis": "Analyzed.",
            "ia-data-description": "Described.",
            "ia-customization": "None.",
            "ia-metrics": "Accuracy, FPR, FNR by protected class.",
            "ia-transparency": "Consumer notice on screen at decision point.",
            "ia-oversight": "Documented human oversight process.",
        },
        "consumer_notice_content": {"text": "This decision uses AI."},
    },
    "consequential_decision_domains": ["housing"],
}


# ---------------------------------------------------------------------------
# Singapore MAGF
# ---------------------------------------------------------------------------

DEMO_SINGAPORE_MAGF_INPUT: dict[str, Any] = {
    "organization_type": "financial-services",
    "system_description": {
        "system_name": "CreditScore",
        "human_involvement_tier": "human-in-the-loop",
        "pillar_evidence": {
            "internal-governance": {
                "role_assignments": "AI governance committee chartered.",
                "risk_controls": "Annual AI risk review procedure.",
                "staff_training": "Quarterly AI ethics training log.",
            },
            "human-involvement": {
                "human_involvement_tier": "human-in-the-loop",
                "risk_matrix": "Documented probability-severity matrix.",
                "escalation_process": "Escalation to senior reviewer.",
            },
            "operations-management": {
                "data_lineage": "End-to-end data lineage captured.",
                "data_quality": "Monthly data quality monitoring.",
                "bias_mitigation": "Protected-class parity testing.",
                "model_robustness": "Adversarial robustness testing.",
                "explainability": "SHAP explanations generated per decision.",
                "reproducibility": "Model artifacts versioned and hashed.",
                "monitoring": "Drift and performance dashboards.",
            },
            "stakeholder-communication": {
                "disclosure_policy": "Public AI use disclosure page.",
                "feedback_channel": "Consumer contact form.",
                "decision_review_process": "Documented decision-review workflow.",
            },
        },
        "feat_evidence": {
            "fairness": {
                "justifiability": "Model features documented.",
                "accuracy_bias": "Regular review of accuracy and bias metrics.",
                "systematic_disadvantage": "Protected-class disparate-impact testing.",
            },
            "ethics": {
                "ethical_standards": "Decisions benchmarked against human baseline.",
                "alignment": "Model aligned with firm code of conduct.",
                "human_alternative": "Escalation path to human underwriter.",
            },
            "accountability": {
                "internal_approval": "Model approved by credit risk committee.",
                "external_accountability": "Customer notice covers AI decisions.",
                "data_subject_rights": "Appeal channel for adverse decisions.",
                "verification": "Reason codes produced per decision.",
            },
            "transparency": {
                "proactive_disclosure": "AI use disclosed at account opening.",
                "clear_explanation": "Reason codes returned on adverse action notice.",
                "ease_of_understanding": "Plain-language explanation template.",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# UK ATRS tier-2
# ---------------------------------------------------------------------------

DEMO_UK_ATRS_TIER_2_INPUT: dict[str, Any] = {
    "tier": "tier-2",
    "owner": {
        "organization": "Department for Work and Pensions",
        "parent_organization": "UK Government",
        "contact_point": "atrs@dwp.gov.uk",
        "senior_responsible_owner": "DWP Digital Director",
    },
    "tool_description": {
        "name": "Benefits Eligibility Decision Support",
        "purpose": "Risk-score benefits applications.",
        "how_tool_works": "Gradient-boosted model scores applications.",
        "decision_subject_scope": "Working-age benefits applicants.",
        "phase": "production",
    },
    "tool_details": {
        "model_family": "gradient-boosted trees",
        "model_type": "binary classifier",
        "system_architecture": "batch scoring service.",
        "training_data_summary": "Five years of claims with outcome labels.",
        "model_performance_metrics": {"auc_roc": 0.87, "f1": 0.72},
        "third_party_components": ["xgboost v2.0"],
    },
    "impact_assessment": {
        "assessments_completed": ["DPIA-2026-03", "EIA-2026-03"],
        "citizen_impact_dimensions": ["financial", "access to benefits"],
        "severity": "medium",
        "affected_groups": ["working-age claimants"],
        "consultation_summary": "Consulted with disability rights advocates Feb 2026.",
    },
    "data": {
        "source": "DWP internal claims database",
        "processing_basis": "UK GDPR Article 6(1)(e) public task",
        "data_categories": ["claim history", "household composition"],
        "collection_method": "submitted on application forms",
        "sharing": [{"recipient": "HMRC", "purpose": "income verification"}],
        "retention": "7 years post-decision",
    },
    "risks": [
        {
            "category": "equity",
            "description": "Potential disparity across disability status.",
            "mitigation": "Equality Impact Assessment with quarterly monitoring.",
            "residual_risk": "low",
        },
    ],
    "governance": {
        "assurance_activities": ["DPIA reviewed"],
        "escalation_process": "Documented escalation path.",
    },
    "benefits": {
        "benefit_categories": ["processing throughput"],
        "measurement_approach": "Month-over-month handling time.",
    },
}


__all__ = [
    "DEMO_INVENTORY_SYSTEM",
    "DEMO_EU_HIGH_RISK_SYSTEM",
    "DEMO_INVENTORY_INPUT",
    "DEMO_RISKS",
    "DEMO_RISK_REGISTER_INPUT",
    "DEMO_SOA_INPUT",
    "DEMO_AISIA_FULL_INPUT",
    "DEMO_AISIA_MINIMAL_INPUT",
    "DEMO_METRICS_INPUT",
    "DEMO_NONCONFORMITY_INPUT",
    "DEMO_AUDIT_LOG_INPUT",
    "DEMO_ORG_CHART",
    "DEMO_AUTHORITY_REGISTER",
    "DEMO_MANAGEMENT_REVIEW_INPUT",
    "DEMO_INTERNAL_AUDIT_INPUT",
    "DEMO_GAP_INPUT",
    "DEMO_DATA_REGISTER_INPUT",
    "DEMO_APPLICABILITY_INPUT",
    "DEMO_HIGH_RISK_EU_INPUT",
    "DEMO_HIGH_RISK_COLORADO_HOUSING_INPUT",
    "DEMO_HIGH_RISK_COLORADO_NO_CONFORMANCE_INPUT",
    "DEMO_NYC_LL144_INPUT",
    "DEMO_COLORADO_COMPLIANCE_INPUT",
    "DEMO_SINGAPORE_MAGF_INPUT",
    "DEMO_UK_ATRS_TIER_2_INPUT",
]
