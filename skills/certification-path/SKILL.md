---
name: certification-path
version: 0.1.0
description: >
  Certification path planning skill. Consumes a certification-readiness
  snapshot and produces a milestone-based path plan with risk-weighted
  remediation sequencing, target dates, capacity-aware packing, and
  recertification triggers. Each remediation is emitted as an
  action-executor ActionRequest. Maps to ISO/IEC 42001:2023 Clauses 9.2
  (internal audit cadence for surveillance), 9.3 (management review as
  milestone gate), 10.1 (continual improvement); EU AI Act Article 43
  (conformity procedure planning surface) and Article 40 (harmonised
  standards surveillance trigger); Colorado SB 205 Section 6-1-1703(3)
  (annual impact-assessment refresh); and NYC LL144 Final Rule Section
  5-301 (annual re-audit cadence).
frameworks:
  - ISO/IEC 42001:2023
  - NIST AI RMF 1.0
  - EU AI Act (Regulation (EU) 2024/1689)
  - Colorado SB 205
  - NYC LL144
tags:
  - ai-governance
  - certification
  - path-planning
  - consumer-plugin
  - milestone-schedule
  - risk-weighted
  - recertification
author: AIGovOps Contributors
license: MIT
---

## Overview

This skill is the journey layer above `certification-readiness`. The readiness skill produces a point-in-time verdict with gaps, blockers, and remediations. The path skill takes that snapshot and a target certification date, sequences the remediations into dated milestones, risk-weights them, capacity-checks them against the team's weekly hours, and emits each remediation as an ActionRequest ready for the action-executor. It also schedules recertification triggers (ISO surveillance audits, NYC LL144 annual re-audit, Colorado annual impact-assessment refresh, EU harmonised-standards event trigger).

The skill does not execute any action. It does not invent gaps or remediations beyond those in the readiness snapshot. It does not issue an audit opinion or a commitment to any certification outcome.

Readiness snapshot in; dated milestone plan out. That is the contract.

## Scope

**In scope.** Path planning against the same nine target certifications supported by `certification-readiness`: ISO/IEC 42001:2023 Stage 1, Stage 2, and surveillance; EU AI Act Article 43 internal control (Annex VI) and notified body (Annex VII); Colorado SB 205 Section 6-1-1706(3) safe-harbor; NYC Local Law 144 annual re-audit; Singapore MAGF 2e alignment; UK ATRS publication. Milestone packing with capacity awareness. Risk-weighted prioritization when a risk register is supplied. Recertification trigger scheduling for annual cadences. Action-request emission in the action-executor contract shape.

**Out of scope.** Action execution. Audit opinion issuance. Generation of the missing artifacts themselves (the plan names the `target_plugin` that produces each artifact; the operator runs it via the action-executor). Budget or staffing allocation decisions. Negotiation of the target date with an external auditor.

**Operating assumption.** A certification-readiness snapshot exists. The operator has chosen a target date. Either the operator has supplied an organization_capacity dict (enabling capacity-aware packing) or is willing to accept a plan that packs every remediation into a single milestone.

## Framework Reference

The plan's citation anchors are published framework provisions, not heuristics.

**ISO/IEC 42001:2023, Clause 9.2 (Internal audit).** Clause 9.2 requires internal audits at planned intervals. The path planner emits surveillance-audit triggers at +12 and +24 months from the Stage 2 target date to operationalize this cadence.

**ISO/IEC 42001:2023, Clause 9.3 (Management review).** The management review is the go/no-go gate. The plan uses Clause 9.3 as the milestone-gate reference for Stage 2 targets.

**ISO/IEC 42001:2023, Clause 10.1 (Continual improvement).** The path plan is the planning surface that connects gap assessment to continual improvement. Every plan anchors in Clause 10.1.

**EU AI Act (Regulation (EU) 2024/1689), Article 40 (Harmonised standards).** Article 40 establishes that presumption of conformity for notified-body route requires alignment with harmonised standards. The plan emits a harmonised-standards-review event trigger for notified-body targets when the Commission publishes updates.

**EU AI Act, Article 43 (Conformity assessment procedures).** Article 43 is the procedural anchor for internal-control (Annex VI) and notified-body (Annex VII) targets. The plan cites Article 43 as the top-level citation for both EU AI Act targets.

**Colorado SB 205, Section 6-1-1703(3).** The statute requires the deployer to refresh the impact assessment annually. The plan emits an impact-assessment-refresh trigger at +12 months from the safe-harbor target date.

**NYC LL144 Final Rule, Section 5-301.** The Final Rule requires an annual bias re-audit. The plan emits an annual-reaudit trigger at +12 months.

**Source links.**

- ISO/IEC 42001:2023 clauses are purchased from the ISO store.
- EU AI Act: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ%3AL_202401689.
- Colorado SB 205: https://leg.colorado.gov/bills/sb24-205.
- NYC LL144 Final Rule: https://rules.cityofnewyork.us/rule/automated-employment-decision-tools/.

## Operationalizable Controls

The plan maps each milestone to an action-executor invocation. See `operationalization-map.md` for the per-milestone mapping of actions that fire.

| Plan element | ISO/IEC 42001:2023 | EU AI Act | Colorado SB 205 | NYC LL144 |
|---|---|---|---|---|
| Milestone target date derivation | Clause 10.1 | Article 43 | Section 6-1-1706(3) | Final Rule Section 5-301 |
| Risk-weighted prioritization | Clauses 6.1.2, 6.1.3 | Article 9 | Section 6-1-1702(1) | Final Rule Section 5-302 |
| Capacity assessment | Clause 7.1 | Article 17 | Section 6-1-1702(3) | Final Rule Section 5-303 |
| Recertification trigger scheduling | Clauses 9.2, 9.3 | Articles 40, 43 | Section 6-1-1703(3) | Final Rule Section 5-301 |
| ActionRequest emission | Clause 8.1 | Article 17 | Section 6-1-1703(2) | Final Rule Section 5-304 |

## Output Standards

Every plan output carries:

- `plan_id` (deterministic: `cert-path-<target>-<target_date>-<hash>`).
- `timestamp` (ISO 8601 UTC, seconds precision, suffix `Z`).
- `agent_signature` (`certification-path-planner/0.1.0`).
- `target_certification`, `target_date`, `current_readiness_snapshot_ref`.
- `milestones`: ordered list with `milestone_id`, `target_date`, `hours_required`, `remediation_action_requests`, `success_criteria`, `status`, `blocked_by`, `contains_snapshot_blocker`, `go_no_go_gate`, `citations`.
- `blockers`: hard blockers unresolved at plan time.
- `recertification_triggers`: future milestones for ongoing compliance.
- `capacity_assessment`: per-milestone hours_required vs hours_available.
- `citations`, `warnings`, `summary`.
- `cross_framework_citations` when `enrich_with_crosswalk=True` (default).

The rendered Markdown carries a legal disclaimer callout:

> This certification path plan is informational. It does not constitute a commitment to any certification outcome. Certification decisions require a qualified auditor or notified body. Consult a Lead Implementer for formal path approval.

The rendered CSV has one row per milestone with columns `milestone_id`, `target_date`, `status`, `hours_required`, `remediation_count`, `blocked_by`, `success_criteria`, `citations`.

## Limitations

1. The plugin does not execute action requests. An action-executor consumes the emitted ActionRequest list.
2. Effort sizing is coarse (small=8h, medium=40h, large=160h per gap). Organizations with a fine-grained effort estimate should post-process the plan against their own model.
3. Risk-weighting requires a risk register. Without one, prioritization reduces to blocker-vs-gap plus target-date urgency.
4. Recertification triggers are hard-coded per target. The plugin does not detect a new cadence introduced by a regulator mid-cycle.
5. The plugin does not diff against a `previous_plan_ref` in this version; the field is accepted but not yet used. Future versions will surface added, removed, and reshuffled milestones.
