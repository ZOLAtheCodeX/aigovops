# aigovops CLI

The `aigovops` command-line interface orchestrates the full AIGovOps AI Management System (AIMS) pipeline against a single organization configuration file. One command produces every artifact the catalogue knows how to emit: inventory, risk register, data register, role matrix, supplier-vendor assessment, bias and robustness evaluations, human-oversight design, Statement of Applicability, AISIA, audit log, metrics report, post-market-monitoring plan, system-event-logger schema, explainability documentation, GenAI risk register, GPAI-obligations assessment, incident-reporting template, nonconformity register, internal audit plan, gap assessment, management review package, jurisdiction-specific records, evidence bundle, certification-readiness report, and certification-path plan.

## Install

The CLI is a stdlib-only Python 3.10+ script with PyYAML as its sole dependency. Put the executable on your PATH:

```bash
# From the repo root:
export PATH="$PWD/bin:$PATH"

# Or symlink into a directory already on PATH:
ln -s "$PWD/bin/aigovops" /usr/local/bin/aigovops
```

## Quickstart

```bash
aigovops doctor
aigovops run --org examples/organization.example.yaml --output /tmp/run1
ls /tmp/run1/artifacts/
```

`aigovops doctor` verifies the environment (Python version, PyYAML availability, every plugin importable, catalogue consistency audit). `aigovops run` executes the full pipeline and writes a `run-summary.json` plus per-plugin artifacts under `artifacts/`.

## Subcommands

### run

```bash
aigovops run --org <organization.yaml> --output <dir>
             [--skip-plugin <name>]
             [--framework iso42001|nist-ai-rmf|eu-ai-act]
             [--include-crosswalk-export]
             [--include-query-plugins]
```

Reads `organization.yaml`, runs every applicable plugin in topological order, writes artifacts to `<dir>/artifacts/<plugin-name>/`, and writes `run-summary.json` plus `run-summary.md` at the top of `<dir>`.

- `--skip-plugin` can be repeated to skip multiple plugins. Accepts any plugin name in the catalogue.
- `--framework` overrides the gap-assessment target framework.
- `--include-crosswalk-export` additionally invokes `crosswalk-matrix-builder`.
- `--include-query-plugins` invokes the query plugins (`cascade-impact-analyzer`, `crosswalk-matrix-builder`) with default inputs for validation. Query plugins are not invoked by default because they are query-oriented rather than pipeline-producing.

Plugin failures are captured in `<dir>/errors/<plugin-name>.txt`; the run continues regardless so a single malformed input does not block the whole pipeline.

### pack, verify, inspect

```bash
aigovops pack --artifacts <dir> --output <bundle-dir>
              [--signing-algorithm hmac-sha256]
              [--scope-file scope.yaml]
aigovops verify --bundle <bundle-dir>
aigovops inspect --bundle <bundle-dir>
```

These delegate to the `evidence-bundle-packager` plugin. If that plugin is not present in the catalogue, the CLI emits a clean error and exits non-zero.

### doctor

```bash
aigovops doctor
```

Sanity-checks Python version, PyYAML, every plugin's importability, and the catalogue consistency audit. Prints `[OK]` / `[FAIL]` per check. Exits 0 when all checks pass, 1 otherwise.

## organization.yaml schema reference

The top-level mapping has these sections. Only `organization` is required; every other section has sensible defaults.

| Section | Required | Used by | Notes |
|---|---|---|---|
| `organization` | yes | all | Must include `name`. Optional: `industry`, `headquarters_jurisdiction`, `operational_jurisdictions`. |
| `aims_boundary` | no | inventory, internal-audit, gap-assessment | `description`, `scope_inclusions`, `scope_exclusions`. |
| `ai_systems` | yes in practice | every system-scoped plugin | List of AI system dicts. See `plugins/ai-system-inventory-maintainer/README.md` for the full field list. |
| `risk_register_inputs` | no | risk-register-builder | `risks`, `framework`. |
| `data_register_inputs` | no | data-register-builder | `data_inventory` list with `id`, `name`, `purpose_stage`, `source`. |
| `role_matrix_inputs` | no | role-matrix-generator | `org_chart`, `role_assignments`, `authority_register`, optional `backup_assignments`. |
| `soa_inputs` | no | soa-generator | `exclusion_justifications`, `implementation_plans`, `scope_notes`. |
| `aisia_inputs` | no | aisia-runner | `affected_stakeholders`, `impact_assessments`, `framework`. |
| `governance_decisions` | no | audit-log-generator | List of free-text governance event strings. |
| `audit_log_inputs` | no | audit-log-generator | `responsible_parties`. |
| `metrics_inputs` | no | metrics-collector | `measurements`, `thresholds`, `framework`. |
| `nonconformity_inputs` | no | nonconformity-tracker | `records`. |
| `internal_audit_inputs` | no | internal-audit-planner | `audit_frequency_months`, `audit_criteria`, optional `scope`. |
| `gap_assessment_inputs` | no | gap-assessment | `target_framework`, optional `scope_boundary`, `targets`. |
| `management_review_inputs` | no | management-review-packager | `review_window`, `attendees`, `meeting_metadata`, and the other Clause 9.3.2 inputs. |
| `colorado_inputs` | no | colorado-ai-act-compliance | `actor_role`, `consequential_decision_domains`. |
| `nyc_inputs` | no | nyc-ll144-audit-packager | `employer_role`, `audit_data`. |
| `uk_atrs_inputs` | no | uk-atrs-recorder | `tier`, `tool_description`, `owner`. |
| `singapore_inputs` | no | singapore-magf-assessor | `system_description`, `organization_type`. |
| `supplier_vendor_inputs` | no | supplier-vendor-assessor | `vendors` (list), `vendor_role`, `organization_role`, optional `contract_summary`. |
| `bias_evaluator_inputs` | no | bias-evaluator | `evaluation_data.per_group_counts`, `protected_attributes`, `metrics_to_compute`, `jurisdiction_rules`. |
| `robustness_evaluator_inputs` | no | robustness-evaluator | `evaluation_scope` (with `dimensions`), `evaluation_results`, optional `backup_plan_ref`. |
| `human_oversight_inputs` | no | human-oversight-designer | `oversight_design` (mode, ability coverage, override controls), `assigned_oversight_personnel`. |
| `system_event_logger_inputs` | no | system-event-logger | `event_schema` (non-empty mapping keyed by event category), `retention_policy`, optional `log_storage` and `traceability_mappings`. |
| `explainability_inputs` | no | explainability-documenter | `model_type`, `explanation_methods`, `intrinsic_interpretability_claim`. |
| `genai_risk_register_inputs` | no | genai-risk-register | `risk_evaluations` (one entry per NIST GenAI risk), optional `risks_not_applicable`. |
| `gpai_inputs` | no | gpai-obligations-tracker | `model_description`, `provider_role`, optional `systemic_risk_artifacts`, `code_of_practice_status`. |
| `incident_reporting_inputs` | no | incident-reporting | `incidents` (list), `applicable_jurisdictions`, `severity`, `actor_role`. |
| `eu_conformity_inputs` | no | eu-conformity-assessor | `procedure_requested`, `provider_identity`, `harmonised_standards_applied`, `registration_status`. |
| `evidence_bundle_inputs` | no | evidence-bundle-packager | `scope` (reporting period, intended recipient), `signing_algorithm`, `include_source_crosswalk`. |
| `certification_readiness_inputs` | no | certification-readiness | `target_certification`, `scope_overrides`. |
| `certification_path_planner_inputs` | no | certification-path-planner | `target_certification`, `target_date`, `organization_capacity`. |
| `cascade_impact_inputs` | no | cascade-impact-analyzer | `trigger_event.event`. Query plugin. |
| `crosswalk_inputs` | no | crosswalk-matrix-builder | `query_type`, `source_framework`, `target_framework`, optional `source_ref`. Query plugin. |

Jurisdiction-specific plugins run only when the relevant jurisdiction (`usa-co`, `usa-nyc`, `uk`, `singapore`) appears in `headquarters_jurisdiction`, `operational_jurisdictions`, or any AI system's `jurisdiction`.

See `examples/organization.example.yaml` for a complete, annotated template.

## Output directory layout

```text
<output>/
  run-summary.json
  run-summary.md
  artifacts/
    ai-system-inventory-maintainer/
      inventory.json
      inventory.md
      inventory.csv
    risk-register-builder/
      risk-register.json
      risk-register.md
      risk-register.csv
    ...
  errors/
    <plugin-name>.txt   (per-failed-plugin; empty directory if no failures)
```

`run-summary.json` contains: `organization_name`, `timestamp`, `plugins_run`, `plugins_succeeded`, `plugins_failed`, `plugins_skipped`, `wall_clock_seconds`, `jurisdictions_detected`, and a `plugins[]` array with per-plugin status, duration, and (on failure) the error message.

## Orchestration order

The CLI runs plugins in this topological order. Downstream plugins consume upstream artifacts (for example, `soa-generator` reads the risk register; `evidence-bundle-packager` packs every preceding artifact; `certification-readiness` reads the packed bundle; `certification-path-planner` reads the readiness snapshot; `management-review-packager` summarizes everything else).

| # | Plugin | Gating condition |
|---|---|---|
| 1 | ai-system-inventory-maintainer | always (source of truth) |
| 2 | applicability-checker | if ai_systems present |
| 3 | high-risk-classifier | if ai_systems present |
| 4 | risk-register-builder | if ai_systems present |
| 5 | data-register-builder | if ai_systems present |
| 6 | role-matrix-generator | if ai_systems present |
| 7 | supplier-vendor-assessor | if ai_systems present |
| 8 | bias-evaluator | if ai_systems present |
| 9 | robustness-evaluator | if ai_systems present |
| 10 | human-oversight-designer | if ai_systems present |
| 11 | soa-generator | if ai_systems present |
| 12 | aisia-runner | if ai_systems present |
| 13 | audit-log-generator | if ai_systems present |
| 14 | metrics-collector | if ai_systems present |
| 15 | post-market-monitoring | if ai_systems present |
| 16 | system-event-logger | if ai_systems present |
| 17 | explainability-documenter | if ai_systems present |
| 18 | genai-risk-register | if at least one ai_system has `is_generative: true` |
| 19 | gpai-obligations-tracker | if at least one ai_system is a GPAI candidate (generative + transformer/DNN) |
| 20 | incident-reporting | unconditional (template-prep; warns when no incidents declared) |
| 21 | nonconformity-tracker | if ai_systems present |
| 22 | internal-audit-planner | if ai_systems present |
| 23 | gap-assessment | if ai_systems present |
| 24 | uk-atrs-recorder | if UK in scope |
| 25 | colorado-ai-act-compliance | if usa-co in scope |
| 26 | nyc-ll144-audit-packager | if usa-nyc in scope |
| 27 | singapore-magf-assessor | if Singapore in scope |
| 28 | eu-conformity-assessor | if EU in scope AND at least one high-risk system |
| 29 | management-review-packager | if ai_systems present |
| 30 | evidence-bundle-packager | after all preceding artifacts are produced |
| 31 | certification-readiness | if evidence-bundle-packager succeeded |
| 32 | certification-path-planner | if certification-readiness succeeded |
| Q1 | cascade-impact-analyzer | query plugin; only with `--include-query-plugins` |
| Q2 | crosswalk-matrix-builder | query plugin; only with `--include-crosswalk-export` or `--include-query-plugins` |

Query plugins (`cascade-impact-analyzer`, `crosswalk-matrix-builder`) are registered in the catalog but not invoked by default. They are query-oriented rather than pipeline-producing. Pass `--include-query-plugins` to invoke them with default inputs for validation.

## Troubleshooting

- `FileNotFoundError: cli/runner.py` when running `aigovops` from an unusual path: the `bin/aigovops` shim walks up from its own location to find the repo root. If you have copied the file without its repo, place it back under `<repo>/bin/aigovops` or symlink.
- `organization.yaml missing required top-level fields: ['organization']`: the YAML must have a top-level `organization:` mapping with at minimum a `name`.
- A single plugin fails but the run exits 0: this is intentional. Per-plugin failures are recorded in `errors/<plugin>.txt` and summarized in `run-summary.json`; the pipeline continues so partial artifacts are still produced.
- `aigovops doctor` reports a consistency-audit FAIL: this surfaces pre-existing gaps in the catalogue (for example, planned skills without a SKILL.md). Unrelated to CLI health.
- `evidence-bundle-packager plugin not yet shipped`: the `pack`, `verify`, and `inspect` subcommands require that plugin; install or wait for it to land.

## Tests

```bash
python3 cli/tests/test_cli.py
```

Thirty-two tests cover doctor, help, organization loading, end-to-end runs, skip semantics, error resilience, output structure, jurisdiction gating, bundle-packager delegation, per-plugin gating (generative / GPAI / EU high-risk), ordering invariants (evidence-bundle-packager after producers; certification-path-planner after certification-readiness), incident-reporting unconditional behaviour, and opt-in query-plugin invocation.
