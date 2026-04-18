# ai-system-inventory-maintainer

Produces a validated, versioned AI system inventory artifact that every other AIGovOps plugin consumes as `ai_system_inventory`. Closes the loop left by all downstream plugins: they read an inventory, none of them help maintain it.

## What this plugin does

1. Validates every system against required and recommended field sets.
2. Enforces enum values for `risk_tier`, `decision_authority`, `lifecycle_state`.
3. Tags each system with jurisdictional applicability across ISO 42001, NIST AI RMF, EU AI Act, Colorado SB 205, NYC LL144, UK ATRS, and Singapore MAGF 2e plus MAS FEAT.
4. Diffs against a prior inventory to track added, modified, removed, unchanged systems.
5. Emits a decommission warning so downstream plugins (SoA, risk register, audit log) know to update their records.
6. Optionally enriches each system with cross-framework references sourced from the `crosswalk-matrix-builder` data.

## What this plugin does NOT do

- Discover AI systems. The organization must supply the inventory.
- Verify that linked artifact refs (`aisia_ref`, `soa_ref`, `risk_register_ref`) exist. Referenced-artifact resolution is out of scope.
- Assign risk tiers. Use the `high-risk-classifier` plugin for EU AI Act Article 5/6/Annex I/Annex III classification.

## Public API

- `maintain_inventory(inputs: dict) -> dict`
- `validate_system(system: dict) -> list[dict]`
- `render_markdown(inventory: dict) -> str`
- `render_csv(inventory: dict) -> str`

## Input

| Field | Required | Description |
|---|---|---|
| `systems` | yes | List of system dicts. |
| `operation` | no | One of `create`, `update`, `decommission`, `validate`, `full-refresh`. Default `validate`. |
| `previous_inventory_ref` | no | Path to a prior inventory JSON file. Used for diff when `operation='update'`. |
| `decommission_system_ids` | no | List of `system_id` values to mark decommissioned when `operation='decommission'`. |
| `organizational_scope` | no | Dict with in-scope jurisdictions, sectors, decision domains. Used for applicability scoping. |
| `enrich_with_crosswalk` | no | Bool. Default `True`. Attaches `cross_framework_references` per system. |
| `reviewed_by` | no | String. |

### Per-system required fields

`system_id`, `system_name`, `intended_use`, `deployment_context`, `risk_tier`, `decision_authority`, `jurisdiction`, `lifecycle_state`.

### Per-system recommended fields

`data_processed`, `stakeholder_groups`, `owner_role`, `operator_role`, `model_family`, `training_data_provenance`, `post_market_monitoring_plan_ref`, `risk_register_ref`, `aisia_ref`, `soa_ref`, `last_reviewed_date`, `next_review_due_date`.

## Output

Dict with `timestamp`, `agent_signature`, `operation`, `reviewed_by`, `systems`, `validation_findings`, `regulatory_applicability_matrix`, `citations`, `warnings`, `summary`, and `version_diff` when `operation='update'`.

## Applicability rules (deterministic)

| Jurisdiction or context | Framework attached | Citation |
|---|---|---|
| Every system | `iso42001` | `ISO/IEC 42001:2023, Clause 4.3` |
| `jurisdiction` contains `usa-*` | `nist-ai-rmf` | `GOVERN 1.1` |
| `jurisdiction` contains `eu`, `risk_tier='prohibited'` | `eu-ai-act` | `EU AI Act, Article 5` |
| `jurisdiction` contains `eu`, `risk_tier='high-risk-annex-i'` or `'high-risk-annex-iii'` | `eu-ai-act` | `EU AI Act, Chapter III` |
| `jurisdiction` contains `eu`, other tiers | `eu-ai-act` | `EU AI Act, Article 50` |
| `jurisdiction` contains `usa-nyc` AND context mentions employment | `nyc-ll144` | `NYC LL144 Final Rule, Section 5-301` |
| `jurisdiction` contains `usa-co` AND context is consequential | `colorado-sb-205` | `Colorado SB 205, Section 6-1-1701(3)` |
| `jurisdiction` contains `singapore` | `singapore-magf-2e` | `Singapore MAGF 2e, Pillar Internal Governance Structures and Measures` |
| `jurisdiction` contains `singapore` AND `sector='financial-services'` | `mas-feat` | `MAS FEAT Principles (2018), Principle Accountability` |
| `jurisdiction` contains `uk` AND public-sector | `uk-atrs` | `UK ATRS, Section Tool description` |

## Validation rules

- FAIL: required field missing.
- WARN: recommended field missing, unknown jurisdiction value, or cross-field consistency issue (fully-automated Annex III without `aisia_ref`; EU high-risk without EU AI Act citations).
- OK: linked-artifact reference acknowledged; top-level summary when no FAIL present.

## Citation format

All citations match `STYLE.md` prefixes. CI enforces regex compliance on citation strings.

## Related

- `skills/ai-system-inventory/SKILL.md` - skill pairing.
- `plugins/soa-generator/` - consumes this inventory.
- `plugins/risk-register-builder/` - consumes this inventory.
- `plugins/high-risk-classifier/` - produces the risk tier value used here.
- `plugins/crosswalk-matrix-builder/` - supplies the cross-framework references when `enrich_with_crosswalk=True`.

## Determinism

Given the same input, the plugin produces the same output except for the `timestamp` field.
