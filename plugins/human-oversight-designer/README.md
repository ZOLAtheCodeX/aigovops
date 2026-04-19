# human-oversight-designer

Operationalizes EU AI Act Article 14 (Human oversight), ISO/IEC 42001:2023 Annex A controls A.9.2 (Processes for responsible use), A.9.3 (Objectives for responsible use), and A.9.4 (Intended use), and NIST AI RMF MANAGE 2.3 (mechanisms to prevent, disengage, override, or deactivate AI systems). Produces the dedicated human-oversight design artifact for an AI system.

This plugin is the design-artifact complement to `aisia-runner`, which treats human-oversight as one impact dimension within a broader AISIA. Use this plugin when the deliverable is the standalone Article 14 design with ability coverage, override capability, biometric dual-assignment verification, operator training posture, automation bias mitigations, and assigned oversight personnel.

## Inputs

| Field | Required | Type | Description |
|---|---|---|---|
| `system_description` | yes | dict | Must contain `system_id`, `system_name`, `intended_use`, `risk_tier`. Optional `jurisdiction`, `deployment_context`, `decision_authority`, `biometric_identification_system` (bool, default False). |
| `oversight_design` | yes | dict | Must contain `mode`, optional `ability_coverage`, `override_controls`, `operator_training`, `automation_bias_mitigations`, `escalation_paths`. |
| `assigned_oversight_personnel` | conditional | list[dict] | Required for high-risk systems. Each entry: `person_role`, `authority_level`, `training_evidence_ref`. |
| `previous_design_ref` | optional | string | Version-tracking reference to a prior design. |
| `enrich_with_crosswalk` | optional | bool | Default True. When True, attaches `cross_framework_citations` from the crosswalk-matrix-builder. |
| `reviewed_by` | optional | string | Reviewer attribution for the artifact. |

### Enums

- `mode` (oversight_design): one of `human-in-the-loop`, `human-on-the-loop`, `human-out-of-the-loop-with-escalation`, `fully-automated-unauthorised`. The last value is a compliance-violation flag for high-risk systems.
- `authority_level` (assigned_oversight_personnel): one of `sole-authority`, `shared-authority`, `veto-authority`, `advisory-only`, `observer-only`.
- `control_type` (override_controls): one of `stop-button`, `kill-switch`, `delay-and-review`, `human-approval-required`.
- Article 14(4) abilities (keys of `ability_coverage`): `understand`, `awareness-of-automation-bias`, `correctly-interpret`, `decide-not-to-use`, `intervene-or-stop`.

## Public API

- `design_human_oversight(inputs: dict) -> dict`
- `render_markdown(design: dict) -> str`
- `render_csv(design: dict) -> str`

## Outputs

The output dict contains:

- `timestamp`, `agent_signature`, `framework` (fixed: `eu-ai-act,iso42001,nist`).
- `system_description_echo`.
- `art_14_applicability` (`applies` or `not-mandated-but-recommended`).
- `ability_coverage_assessment` with per-ability rows and status (`full-coverage`, `partial-coverage`, `no-coverage`, `not-mandated`).
- `override_capability_assessment` with per-control rows and per-control warnings.
- `biometric_dual_assignment_check` when the system is a biometric identification system.
- `mode_validation` with blocking-finding flag.
- `operator_training_assessment`.
- `automation_bias_mitigations_echo`.
- `escalation_paths`, `oversight_personnel`.
- `citations`, `warnings`, `summary`.
- `cross_framework_citations` when crosswalk enrichment ran.
- `reviewed_by`.

## Rule table

| Rule | Trigger | Result |
|---|---|---|
| Article 14 applicability | `risk_tier` in {high-risk-annex-i, high-risk-annex-iii} | `art_14_applicability=applies` |
| Ability coverage | Article 14 applies and any of the 5 abilities not enabled | warning per missing ability, status partial-coverage or no-coverage |
| Override required | no override_controls listed | warning citing Article 14(4)(d) and 14(4)(e) |
| Override latency | high-risk system and `activation_latency_seconds` > 30 | warning per-control |
| Override staleness | `tested_date` not within last 365 days | warning per-control |
| Biometric dual-assignment | `biometric_identification_system=True` and authoritative personnel < 2 | blocking warning citing Article 14(5) |
| Mode compliance | `mode=fully-automated-unauthorised` and Article 14 applies | blocking finding |
| Training completion | `completion_rate_percent` < 80 | warning |
| Annual refresh | `annual_refresh=False` | warning |
| Automation bias | no automation_bias_mitigations listed | warning citing Article 14(4)(b) |

## Citations

- `EU AI Act, Article 14, Paragraph 1` through `Paragraph 5` (when Article 14 applies).
- `ISO/IEC 42001:2023, Annex A, Control A.9.2`, `A.9.3`, `A.9.4`.
- `MANAGE 2.3` (NIST AI RMF 1.0).
- `UK ATRS, Section Tool description` and `Section Impact assessment` (UK jurisdiction only).

## Example invocation

```python
from plugins.human_oversight_designer import plugin

result = plugin.design_human_oversight({
    "system_description": {
        "system_id": "SYS-001",
        "system_name": "ResumeScreen",
        "intended_use": "Rank candidates for human reviewer.",
        "risk_tier": "high-risk-annex-iii",
        "jurisdiction": "EU",
        "biometric_identification_system": False,
    },
    "oversight_design": {
        "mode": "human-in-the-loop",
        "ability_coverage": {
            "understand": {"enabled": True, "mechanism": "model card",
                           "evidence_ref": "docs/modelcard.md"},
            "awareness-of-automation-bias": {"enabled": True,
                "mechanism": "operator training", "evidence_ref": "docs/training.md"},
            "correctly-interpret": {"enabled": True,
                "mechanism": "interpretability dashboard", "evidence_ref": "docs/dash.md"},
            "decide-not-to-use": {"enabled": True,
                "mechanism": "policy override", "evidence_ref": "docs/policy.md"},
            "intervene-or-stop": {"enabled": True,
                "mechanism": "stop button", "evidence_ref": "docs/stop.md"},
        },
        "override_controls": [
            {"control_name": "stop-button-1", "control_type": "stop-button",
             "activation_latency_seconds": 2, "tested_date": "2026-04-01",
             "tested_by": "QA Engineer"},
        ],
        "operator_training": {
            "curriculum_ref": "docs/curriculum.md",
            "assessment_ref": "docs/assessment.md",
            "completion_rate_percent": 95,
            "annual_refresh": True,
        },
        "automation_bias_mitigations": [
            {"mitigation_name": "confidence-display",
             "rationale": "Show prediction confidence.",
             "reference": "docs/ui-spec.md"},
        ],
    },
    "assigned_oversight_personnel": [
        {"person_role": "HR Reviewer", "authority_level": "sole-authority",
         "training_evidence_ref": "docs/hr.md"},
    ],
})

print(plugin.render_markdown(result))
```

## Determinism

Output is deterministic for deterministic input apart from the `timestamp` field. `cross_framework_citations` is sourced from the crosswalk YAML data files; updates to those files alter enriched output.

## Related plugins and skills

- `aisia-runner`: human-oversight as one impact dimension within a broader AISIA.
- `role-matrix-generator`: assigns the oversight roles referenced in `assigned_oversight_personnel`.
- `high-risk-classifier`: determines `risk_tier`.
- `nonconformity-tracker`: records overrides exercised during operation.
- `incident-reporting`: routes safety incidents triggered via override paths.
- `skills/human-oversight/SKILL.md`: skill operationalizing the same controls.
