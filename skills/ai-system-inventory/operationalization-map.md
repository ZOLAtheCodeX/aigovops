# AI System Inventory Operationalization Map

Working document for the `ai-system-inventory` skill. Maps the `ai-system-inventory-maintainer` plugin to every downstream consumer in the AIGovOps catalogue. The inventory is upstream-of-everything; this map enumerates exactly which downstream plugins consume which inventory fields, and which of their outputs change when the inventory changes.

## Downstream consumer matrix

| Downstream plugin | Inventory fields consumed | Effect when inventory changes |
|---|---|---|
| `soa-generator` | `system_id`, `risk_tier`, `jurisdiction`, `decision_authority`, `deployment_context` | SoA scope statement must update; excluded controls may need re-justification when new high-risk systems enter scope. |
| `risk-register-builder` | `system_id`, `risk_tier`, `deployment_context`, `stakeholder_groups`, `data_processed` | Risk rows must be added for new systems; existing rows re-tagged when tier changes. |
| `aisia-runner` | `system_id`, `intended_use`, `deployment_context`, `decision_authority`, `stakeholder_groups`, `data_processed`, `model_family` | A new AISIA is required for every new `deployed` system; `aisia_ref` populated back into the inventory. |
| `audit-log-generator` | `system_id`, `lifecycle_state`, `owner_role` | Lifecycle state transitions (proposed to deployed, deployed to decommissioned) produce audit-log entries. |
| `gap-assessment` | `system_id`, `risk_tier`, `jurisdiction` | Gap assessment scope changes when the in-scope system set changes. |
| `management-review-packager` | `summary.by_risk_tier`, `summary.by_lifecycle_state`, `version_diff` | Management review input package pulls the inventory-change summary. |
| `high-risk-classifier` | Produces `risk_tier` for inventory consumption; does not consume the inventory itself. | Runs before inventory maintenance for new systems; its output populates the `risk_tier` field. |
| `internal-audit-planner` | `system_id`, `risk_tier`, `jurisdiction` | Audit programme scope set by inventory; high-risk systems get deeper coverage. |
| `uk-atrs-recorder` | `system_id`, `system_name`, `intended_use`, `deployment_context`, `owner_role`, `operator_role` | Inventory fields map directly to ATRS Tier 1 sections. |
| `colorado-ai-act-compliance` | `system_id`, `risk_tier`, `jurisdiction`, `deployment_context` | Colorado SB 205 developer or deployer record derives consequential-decision flag from inventory context. |
| `nyc-ll144-audit-packager` | `system_id`, `deployment_context`, `jurisdiction` | NYC LL144 audit is triggered for systems with employment deployment context in NYC. |
| `singapore-magf-assessor` | `system_id`, `jurisdiction`, `sector` | MAGF pillar assessment scope set by inventory; MAS FEAT layered for financial-services entries. |
| `data-register-builder` | `system_id`, `risk_tier`, `training_data_provenance` | Data register entries link back to inventory system IDs; training-data-provenance field seeds source discovery. |
| `metrics-collector` | `system_id`, `risk_tier`, `lifecycle_state` | Per-system metrics attach to inventory IDs; lifecycle-state filters determine which systems are actively monitored. |

## ISO/IEC 42001:2023 mapping

Clause 4.3 (scope determination) is the primary anchor. The inventory is the implementation artifact for "the AI systems included in scope" that Clause 4.3 requires the organization to document.

Clause 7.5.1 (creating documented information) applies to every new inventory entry. Required-field validation enforces that the documented information is "appropriate for the purpose."

Clause 7.5.2 (updating documented information) applies to `operation='update'` runs. The version diff output is the evidence trail for "review and update as necessary."

Clause 7.5.3 (control of documented information) applies to retention of prior inventory snapshots. The organization supplies `previous_inventory_ref` pointing to the retained snapshot.

Annex A Control A.5 (AI system identification) is satisfied when the inventory captures the required identification fields (`system_id`, `system_name`, `intended_use`, `deployment_context`, `decision_authority`).

## NIST AI RMF 1.0 mapping

GOVERN 1.6 requires mechanisms to maintain an inventory of AI systems; the plugin is that mechanism. MAP 1.1 requires establishing the context in which an AI system operates; inventory fields `deployment_context`, `intended_use`, `stakeholder_groups`, `data_processed` populate the MAP 1.1 record.

## EU AI Act mapping

Article 11 (technical documentation) requires system identity fields that the inventory captures. For a high-risk AI system, the inventory row is extracted into the Annex IV technical documentation set.

Article 26 (deployer obligations) and Article 27 (fundamental-rights impact assessment) depend on knowing which AI systems the deployer operates. The inventory is the deployer-side source of truth.

## UK ATRS mapping

UK ATRS Section Tool description and Section Owner and contact consume inventory fields directly. The ATRS Tier 1 public record is a rendering of the inventory row plus additional public-impact text.

## Colorado SB 205 mapping

Colorado SB 205 Section 6-1-1701(3) defines consequential decisions. The inventory's `deployment_context` and `sector` fields drive the applicability matrix's Colorado entry; when a system is tagged as Colorado consequential-decision, the `colorado-ai-act-compliance` plugin is triggered downstream.

## Singapore mapping

Singapore MAGF 2e applies to every Singapore-scope system. MAS FEAT Principles layer on top for financial-services sector deployments. Both attachments are deterministic from the `jurisdiction` and `sector` fields.

## Priority-ranked backlog

The inventory maintainer plugin is Phase 3 minimum-viable implementation. Outstanding items, in operational-leverage order:

1. Wire the plugin into the aigovclaw Hermes Agent runtime as the first step of every governance workflow.
2. Add a sync mode that pushes inventory updates to downstream plugin caches (Phase 4 adapter work).
3. Add a scope-determination companion plugin that helps practitioners author the AIMS scope statement from the inventory.
4. Extend applicability logic to cover Canada AIDA when the bill passes (currently out of scope per `docs/jurisdiction-scope.md`).
