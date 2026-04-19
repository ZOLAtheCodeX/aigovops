# aigovops CLI

The `aigovops` command-line interface orchestrates the full AIGovOps AI Management System (AIMS) pipeline against a single organization configuration file. One command produces every artifact the catalogue knows how to emit: inventory, risk register, Statement of Applicability, AISIA, audit log, metrics report, nonconformity register, internal audit plan, gap assessment, management review package, and any applicable jurisdiction-specific records.

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
```

Reads `organization.yaml`, runs every applicable plugin in topological order, writes artifacts to `<dir>/artifacts/<plugin-name>/`, and writes `run-summary.json` plus `run-summary.md` at the top of `<dir>`.

- `--skip-plugin` can be repeated to skip multiple plugins.
- `--framework` overrides the gap-assessment target framework.
- `--include-crosswalk-export` additionally invokes `crosswalk-matrix-builder`.

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

The CLI runs plugins in this topological order. Downstream plugins consume upstream artifacts (for example, `soa-generator` reads the risk register; `management-review-packager` summarizes everything else).

1. ai-system-inventory-maintainer
2. applicability-checker
3. high-risk-classifier
4. risk-register-builder
5. data-register-builder
6. role-matrix-generator
7. soa-generator
8. aisia-runner
9. audit-log-generator
10. metrics-collector
11. nonconformity-tracker
12. internal-audit-planner
13. gap-assessment
14. uk-atrs-recorder (if UK in scope)
15. colorado-ai-act-compliance (if usa-co in scope)
16. nyc-ll144-audit-packager (if usa-nyc in scope)
17. singapore-magf-assessor (if Singapore in scope)
18. management-review-packager
19. crosswalk-matrix-builder (only with `--include-crosswalk-export`)

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

Fourteen tests cover doctor, help, organization loading, end-to-end runs, skip semantics, error resilience, output structure, jurisdiction gating, and bundle-packager delegation.
