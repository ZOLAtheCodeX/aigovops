"""
Runner and subcommand implementations for the aigovops CLI.

Public entry point: main(argv).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGINS_ROOT = REPO_ROOT / "plugins"


# Plugin dispatch table. For each plugin we record:
#   entry_function: the function to call on the loaded plugin module.
#   renderers: list of (render_function_name, output_filename) pairs.
#   output_filename_stem: stem for the JSON output.
PLUGIN_DISPATCH: dict[str, dict[str, Any]] = {
    "ai-system-inventory-maintainer": {
        "entry": "maintain_inventory",
        "stem": "inventory",
        "renderers": [("render_markdown", "inventory.md"), ("render_csv", "inventory.csv")],
    },
    "applicability-checker": {
        "entry": "check_applicability",
        "stem": "applicability",
        "renderers": [("render_markdown", "applicability.md")],
    },
    "high-risk-classifier": {
        "entry": "classify",
        "stem": "high-risk-classification",
        "renderers": [
            ("render_markdown", "high-risk-classification.md"),
            ("render_csv", "high-risk-classification.csv"),
        ],
    },
    "risk-register-builder": {
        "entry": "generate_risk_register",
        "stem": "risk-register",
        "renderers": [
            ("render_markdown", "risk-register.md"),
            ("render_csv", "risk-register.csv"),
        ],
    },
    "data-register-builder": {
        "entry": "generate_data_register",
        "stem": "data-register",
        "renderers": [
            ("render_markdown", "data-register.md"),
            ("render_csv", "data-register.csv"),
        ],
    },
    "role-matrix-generator": {
        "entry": "generate_role_matrix",
        "stem": "role-matrix",
        "renderers": [
            ("render_markdown", "role-matrix.md"),
            ("render_csv", "role-matrix.csv"),
        ],
    },
    "soa-generator": {
        "entry": "generate_soa",
        "stem": "soa",
        "renderers": [("render_markdown", "soa.md"), ("render_csv", "soa.csv")],
    },
    "aisia-runner": {
        "entry": "run_aisia",
        "stem": "aisia",
        "renderers": [("render_markdown", "aisia.md")],
    },
    "audit-log-generator": {
        "entry": "generate_audit_log",
        "stem": "audit-log-entry",
        "renderers": [("render_markdown", "audit-log-entry.md")],
    },
    "metrics-collector": {
        "entry": "generate_metrics_report",
        "stem": "metrics-report",
        "renderers": [
            ("render_markdown", "metrics-report.md"),
            ("render_csv", "metrics-report.csv"),
        ],
    },
    "nonconformity-tracker": {
        "entry": "generate_nonconformity_register",
        "stem": "nonconformity-register",
        "renderers": [("render_markdown", "nonconformity-register.md")],
    },
    "internal-audit-planner": {
        "entry": "generate_audit_plan",
        "stem": "internal-audit-plan",
        "renderers": [
            ("render_markdown", "internal-audit-plan.md"),
            ("render_csv", "internal-audit-plan.csv"),
        ],
    },
    "post-market-monitoring": {
        "entry": "generate_monitoring_plan",
        "stem": "post-market-monitoring-plan",
        "renderers": [
            ("render_markdown", "post-market-monitoring-plan.md"),
            ("render_csv", "post-market-monitoring-plan.csv"),
        ],
    },
    "gap-assessment": {
        "entry": "generate_gap_assessment",
        "stem": "gap-assessment",
        "renderers": [
            ("render_markdown", "gap-assessment.md"),
            ("render_csv", "gap-assessment.csv"),
        ],
    },
    "management-review-packager": {
        "entry": "generate_review_package",
        "stem": "management-review-package",
        "renderers": [("render_markdown", "management-review-package.md")],
    },
    "uk-atrs-recorder": {
        "entry": "generate_atrs_record",
        "stem": "uk-atrs-record",
        "renderers": [
            ("render_markdown", "uk-atrs-record.md"),
            ("render_csv", "uk-atrs-record.csv"),
        ],
    },
    "colorado-ai-act-compliance": {
        "entry": "generate_compliance_record",
        "stem": "colorado-compliance",
        "renderers": [
            ("render_markdown", "colorado-compliance.md"),
            ("render_csv", "colorado-compliance.csv"),
        ],
    },
    "nyc-ll144-audit-packager": {
        "entry": "generate_audit_package",
        "stem": "nyc-ll144-audit",
        "renderers": [
            ("render_markdown", "nyc-ll144-audit.md"),
            ("render_csv", "nyc-ll144-audit.csv"),
        ],
    },
    "singapore-magf-assessor": {
        "entry": "generate_magf_assessment",
        "stem": "singapore-magf",
        "renderers": [
            ("render_markdown", "singapore-magf.md"),
            ("render_csv", "singapore-magf.csv"),
        ],
    },
    "crosswalk-matrix-builder": {
        "entry": "build_matrix",
        "stem": "crosswalk",
        "renderers": [
            ("render_markdown", "crosswalk.md"),
            ("render_csv", "crosswalk.csv"),
        ],
    },
    "supplier-vendor-assessor": {
        "entry": "assess_vendor",
        "stem": "supplier-vendor-assessment",
        "renderers": [
            ("render_markdown", "supplier-vendor-assessment.md"),
            ("render_csv", "supplier-vendor-assessment.csv"),
        ],
    },
    "bias-evaluator": {
        "entry": "evaluate_bias",
        "stem": "bias-evaluation",
        "renderers": [
            ("render_markdown", "bias-evaluation.md"),
            ("render_csv", "bias-evaluation.csv"),
        ],
    },
    "robustness-evaluator": {
        "entry": "evaluate_robustness",
        "stem": "robustness-evaluation",
        "renderers": [
            ("render_markdown", "robustness-evaluation.md"),
            ("render_csv", "robustness-evaluation.csv"),
        ],
    },
    "human-oversight-designer": {
        "entry": "design_human_oversight",
        "stem": "human-oversight-design",
        "renderers": [
            ("render_markdown", "human-oversight-design.md"),
            ("render_csv", "human-oversight-design.csv"),
        ],
    },
    "system-event-logger": {
        "entry": "define_event_schema",
        "stem": "system-event-schema",
        "renderers": [
            ("render_markdown", "system-event-schema.md"),
            ("render_csv", "system-event-schema.csv"),
        ],
    },
    "explainability-documenter": {
        "entry": "document_explainability",
        "stem": "explainability-documentation",
        "renderers": [
            ("render_markdown", "explainability-documentation.md"),
            ("render_csv", "explainability-documentation.csv"),
        ],
    },
    "genai-risk-register": {
        "entry": "generate_genai_risk_register",
        "stem": "genai-risk-register",
        "renderers": [
            ("render_markdown", "genai-risk-register.md"),
            ("render_csv", "genai-risk-register.csv"),
        ],
    },
    "gpai-obligations-tracker": {
        "entry": "assess_gpai_obligations",
        "stem": "gpai-obligations",
        "renderers": [
            ("render_markdown", "gpai-obligations.md"),
            ("render_csv", "gpai-obligations.csv"),
        ],
    },
    "incident-reporting": {
        "entry": "generate_incident_report",
        "stem": "incident-report",
        "renderers": [
            ("render_markdown", "incident-report.md"),
            ("render_csv", "incident-report.csv"),
        ],
    },
    "eu-conformity-assessor": {
        "entry": "assess_conformity_procedure",
        "stem": "eu-conformity-assessment",
        "renderers": [
            ("render_markdown", "eu-conformity-assessment.md"),
            ("render_csv", "eu-conformity-assessment.csv"),
        ],
    },
    "certification-readiness": {
        "entry": "assess_readiness",
        "stem": "certification-readiness",
        "renderers": [
            ("render_markdown", "certification-readiness.md"),
            ("render_csv", "certification-readiness.csv"),
        ],
    },
    "certification-path-planner": {
        "entry": "plan_certification_path",
        "stem": "certification-path-plan",
        "renderers": [
            ("render_markdown", "certification-path-plan.md"),
            ("render_csv", "certification-path-plan.csv"),
        ],
    },
    "evidence-bundle-packager": {
        "entry": "pack_bundle",
        "stem": "evidence-bundle-report",
        "renderers": [
            ("render_markdown", "evidence-bundle-report.md"),
            ("render_csv", "evidence-bundle-report.csv"),
        ],
    },
    "cascade-impact-analyzer": {
        "entry": "analyze_cascade",
        "stem": "cascade-impact-analysis",
        "renderers": [
            ("render_markdown", "cascade-impact-analysis.md"),
            ("render_csv", "cascade-impact-analysis.csv"),
        ],
    },
}


# Topological execution order.
#
# Plugin placement honours data dependencies:
# - inventory is the source of truth and runs first
# - supplier / bias / robustness / oversight feed downstream SOA and AISIA
# - SOA consumes risk-register + evaluation signals
# - AISIA consumes SOA row refs
# - system-event-logger, explainability, GPAI and genai-risk run alongside
#   other system-scoped plugins
# - incident-reporting runs unconditionally (template-prep)
# - certification-readiness runs after evidence-bundle-packager
# - certification-path-planner consumes certification-readiness output
# - management-review-packager runs near-last to summarise
# - jurisdiction-specific plugins run conditionally
# - evidence-bundle-packager packs every preceding artifact
# - cascade-impact-analyzer and crosswalk-matrix-builder are QUERY plugins;
#   they are NOT invoked by default `run` because they are query-oriented
#   rather than pipeline-producing. Users can opt in with
#   --include-query-plugins to validate them against a default trigger.
EXECUTION_ORDER: tuple[str, ...] = (
    "ai-system-inventory-maintainer",
    "applicability-checker",
    "high-risk-classifier",
    "risk-register-builder",
    "data-register-builder",
    "role-matrix-generator",
    "supplier-vendor-assessor",
    "bias-evaluator",
    "robustness-evaluator",
    "human-oversight-designer",
    "soa-generator",
    "aisia-runner",
    "audit-log-generator",
    "metrics-collector",
    "post-market-monitoring",
    "system-event-logger",
    "explainability-documenter",
    "genai-risk-register",
    "gpai-obligations-tracker",
    "incident-reporting",
    "nonconformity-tracker",
    "internal-audit-planner",
    "gap-assessment",
    "uk-atrs-recorder",
    "colorado-ai-act-compliance",
    "nyc-ll144-audit-packager",
    "singapore-magf-assessor",
    "eu-conformity-assessor",
    "management-review-packager",
    "evidence-bundle-packager",
    "certification-readiness",
    "certification-path-planner",
)


JURISDICTION_PLUGINS = {
    "uk-atrs-recorder": ("uk",),
    "colorado-ai-act-compliance": ("usa-co",),
    "nyc-ll144-audit-packager": ("usa-nyc",),
    "singapore-magf-assessor": ("singapore",),
    "eu-conformity-assessor": ("eu",),
}


# Query plugins: registered in the catalog but not invoked by default `run`.
# Opt in with --include-query-plugins.
QUERY_PLUGINS: tuple[str, ...] = (
    "cascade-impact-analyzer",
    "crosswalk-matrix-builder",
)


# ---------------------------------------------------------------------------
# Plugin loading
# ---------------------------------------------------------------------------


def load_plugin_module(plugin_name: str):
    """Import a plugin's plugin.py by file path."""
    plugin_path = PLUGINS_ROOT / plugin_name / "plugin.py"
    if not plugin_path.exists():
        raise ModuleNotFoundError(f"plugin not found: {plugin_name} at {plugin_path}")
    module_name = f"aigovops_plugin_{plugin_name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, plugin_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build import spec for {plugin_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def try_load_bundle_packager():
    """Return the evidence-bundle-packager module if available, else None."""
    try:
        return load_plugin_module("evidence-bundle-packager")
    except (ModuleNotFoundError, ImportError):
        return None


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Run subcommand
# ---------------------------------------------------------------------------


def run_plugin(
    plugin_name: str,
    build_inputs: Callable[[], dict[str, Any]],
    output_root: Path,
    errors_root: Path,
) -> dict[str, Any]:
    """Invoke a plugin, write artifacts, return a summary entry.

    Never raises; catches and records errors.
    """
    record: dict[str, Any] = {
        "plugin": plugin_name,
        "status": "unknown",
        "started_at": utc_now_iso(),
        "output_files": [],
        "error": None,
    }
    start = time.monotonic()
    try:
        module = load_plugin_module(plugin_name)
        inputs = build_inputs()
        dispatch = PLUGIN_DISPATCH[plugin_name]
        entry = getattr(module, dispatch["entry"])
        result = entry(inputs)
        out_dir = output_root / plugin_name
        json_path = out_dir / f"{dispatch['stem']}.json"
        write_json(json_path, result)
        record["output_files"].append(str(json_path.relative_to(output_root.parent)))
        for render_name, filename in dispatch["renderers"]:
            render_fn = getattr(module, render_name, None)
            if render_fn is None:
                continue
            try:
                rendered = render_fn(result)
            except Exception as exc:
                record.setdefault("warnings", []).append(
                    f"{render_name} failed: {exc}"
                )
                continue
            rpath = out_dir / filename
            write_text(rpath, rendered)
            record["output_files"].append(str(rpath.relative_to(output_root.parent)))
        record["status"] = "succeeded"
        record["result_summary"] = _result_summary(result)
    except Exception as exc:
        record["status"] = "failed"
        record["error"] = f"{type(exc).__name__}: {exc}"
        errors_root.mkdir(parents=True, exist_ok=True)
        err_path = errors_root / f"{plugin_name}.txt"
        err_path.write_text(
            f"Plugin: {plugin_name}\n"
            f"Exception: {type(exc).__name__}: {exc}\n\n"
            f"{traceback.format_exc()}",
            encoding="utf-8",
        )
        sys.stderr.write(f"[aigovops] plugin failed: {plugin_name}: {exc}\n")
    record["finished_at"] = utc_now_iso()
    record["duration_seconds"] = round(time.monotonic() - start, 4)
    return record


def _result_summary(result: Any) -> Any:
    if isinstance(result, dict) and "summary" in result:
        return result["summary"]
    return None


def cmd_run(args: argparse.Namespace) -> int:
    from cli.loader import (
        OrganizationConfigError,
        any_system_applies,
        ai_systems,
        build_aisia_inputs,
        build_applicability_inputs,
        build_audit_log_inputs,
        build_bias_evaluator_inputs,
        build_cascade_impact_inputs,
        build_certification_path_planner_inputs,
        build_certification_readiness_inputs,
        build_colorado_inputs,
        build_crosswalk_inputs,
        build_data_register_inputs,
        build_eu_conformity_inputs,
        build_evidence_bundle_inputs,
        build_explainability_inputs,
        build_gap_assessment_inputs,
        build_genai_risk_register_inputs,
        build_gpai_inputs,
        build_high_risk_inputs,
        build_human_oversight_inputs,
        build_incident_reporting_inputs,
        build_internal_audit_inputs,
        build_inventory_inputs,
        build_management_review_inputs,
        build_metrics_inputs,
        build_nonconformity_inputs,
        build_nyc_inputs,
        build_post_market_monitoring_inputs,
        build_risk_register_inputs,
        build_robustness_evaluator_inputs,
        build_role_matrix_inputs,
        build_singapore_inputs,
        build_soa_inputs,
        build_supplier_vendor_inputs,
        build_system_event_logger_inputs,
        build_uk_atrs_inputs,
        has_eu_high_risk_system,
        has_generative_system,
        has_gpai_model,
        jurisdictions,
        load_organization,
        organization_name,
    )

    try:
        config = load_organization(args.org)
    except (OrganizationConfigError, FileNotFoundError) as exc:
        sys.stderr.write(f"[aigovops] error loading organization.yaml: {exc}\n")
        return 2

    output_root = Path(args.output).resolve()
    artifacts_root = output_root / "artifacts"
    errors_root = output_root / "errors"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    errors_root.mkdir(parents=True, exist_ok=True)

    skip = set(args.skip_plugin or [])
    include_crosswalk = bool(getattr(args, "include_crosswalk_export", False))
    include_query = bool(getattr(args, "include_query_plugins", False))

    wall_start = time.monotonic()
    run_records: list[dict[str, Any]] = []
    skipped: list[str] = []

    # Shared state between plugins.
    shared: dict[str, Any] = {}

    jur = set(jurisdictions(config))

    def _plan_should_run(name: str) -> tuple[bool, str]:
        if name in skip:
            return False, "skipped by --skip-plugin"
        # Query plugins never run automatically.
        if name in QUERY_PLUGINS:
            if name == "crosswalk-matrix-builder" and include_crosswalk:
                return True, ""
            if include_query:
                return True, ""
            return (
                False,
                f"{name} is a query plugin; invoke with --include-query-plugins",
            )
        if not ai_systems(config):
            return False, "no ai_systems defined in organization.yaml"
        if name in JURISDICTION_PLUGINS:
            matches = any(j in jur or any_system_applies(config, j) for j in JURISDICTION_PLUGINS[name])
            if not matches:
                return False, f"jurisdiction {JURISDICTION_PLUGINS[name]} not in scope"
        # eu-conformity-assessor additionally requires at least one high-risk system.
        if name == "eu-conformity-assessor" and not has_eu_high_risk_system(config):
            return False, "no EU-high-risk systems in scope"
        # gpai-obligations-tracker requires at least one GPAI model.
        if name == "gpai-obligations-tracker" and not has_gpai_model(config):
            return False, "no GPAI model (generative + transformer/DNN) in scope"
        # genai-risk-register requires at least one generative system.
        if name == "genai-risk-register" and not has_generative_system(config):
            return False, "no generative AI systems in scope"
        # certification-readiness requires evidence-bundle-packager to have produced a bundle.
        if name == "certification-readiness" and not shared.get("bundle_path"):
            return False, "no evidence bundle available; evidence-bundle-packager did not succeed"
        # certification-path-planner requires certification-readiness snapshot.
        if name == "certification-path-planner" and not shared.get("readiness_snapshot"):
            return False, "no readiness snapshot available; certification-readiness did not succeed"
        if args.framework and name == "gap-assessment":
            # Framework arg overrides gap-assessment target_framework below.
            return True, ""
        return True, ""

    # Builders that depend on prior state.
    def inputs_for(name: str) -> dict[str, Any]:
        if name == "ai-system-inventory-maintainer":
            return build_inventory_inputs(config)
        if name == "applicability-checker":
            return build_applicability_inputs(config)
        if name == "high-risk-classifier":
            return build_high_risk_inputs(config)
        if name == "risk-register-builder":
            return build_risk_register_inputs(config)
        if name == "data-register-builder":
            return build_data_register_inputs(config)
        if name == "role-matrix-generator":
            return build_role_matrix_inputs(config)
        if name == "soa-generator":
            rr = shared.get("risk_register_rows", [])
            return build_soa_inputs(config, risk_register=rr)
        if name == "aisia-runner":
            rows = shared.get("soa_rows", [])
            return build_aisia_inputs(config, soa_rows=rows)
        if name == "audit-log-generator":
            return build_audit_log_inputs(config)
        if name == "metrics-collector":
            return build_metrics_inputs(config)
        if name == "nonconformity-tracker":
            return build_nonconformity_inputs(config)
        if name == "internal-audit-planner":
            return build_internal_audit_inputs(config)
        if name == "post-market-monitoring":
            return build_post_market_monitoring_inputs(config)
        if name == "gap-assessment":
            rows = shared.get("soa_rows", [])
            gi = build_gap_assessment_inputs(config, soa_rows=rows)
            if args.framework:
                gi["target_framework"] = args.framework
            return gi
        if name == "management-review-packager":
            return build_management_review_inputs(
                config,
                metrics_summary=shared.get("metrics_summary_ref", ""),
                nc_summary=shared.get("nc_summary_ref", ""),
                risks_summary=shared.get("risks_summary_ref", ""),
            )
        if name == "uk-atrs-recorder":
            return build_uk_atrs_inputs(config)
        if name == "colorado-ai-act-compliance":
            return build_colorado_inputs(config)
        if name == "nyc-ll144-audit-packager":
            return build_nyc_inputs(config)
        if name == "singapore-magf-assessor":
            return build_singapore_inputs(config)
        if name == "crosswalk-matrix-builder":
            return build_crosswalk_inputs(config)
        if name == "supplier-vendor-assessor":
            return build_supplier_vendor_inputs(config)
        if name == "bias-evaluator":
            return build_bias_evaluator_inputs(config)
        if name == "robustness-evaluator":
            return build_robustness_evaluator_inputs(config)
        if name == "human-oversight-designer":
            return build_human_oversight_inputs(config)
        if name == "system-event-logger":
            return build_system_event_logger_inputs(config)
        if name == "explainability-documenter":
            return build_explainability_inputs(config)
        if name == "genai-risk-register":
            return build_genai_risk_register_inputs(config)
        if name == "gpai-obligations-tracker":
            return build_gpai_inputs(config)
        if name == "incident-reporting":
            return build_incident_reporting_inputs(config)
        if name == "eu-conformity-assessor":
            ec_inputs = build_eu_conformity_inputs(config)
            if shared.get("bundle_path"):
                ec_inputs.setdefault("evidence_bundle_ref", str(shared["bundle_path"]))
            return ec_inputs
        if name == "evidence-bundle-packager":
            bundle_output_dir = output_root / "bundles"
            return build_evidence_bundle_inputs(
                config,
                artifacts_root=artifacts_root,
                bundle_output_dir=bundle_output_dir,
            )
        if name == "certification-readiness":
            return build_certification_readiness_inputs(
                config, bundle_path=shared.get("bundle_path")
            )
        if name == "certification-path-planner":
            return build_certification_path_planner_inputs(
                config, readiness_snapshot=shared.get("readiness_snapshot") or {}
            )
        if name == "cascade-impact-analyzer":
            return build_cascade_impact_inputs(config)
        raise KeyError(name)

    order = list(EXECUTION_ORDER)
    # Append query plugins when explicitly opted in.
    for q in QUERY_PLUGINS:
        if q in order:
            continue
        if q == "crosswalk-matrix-builder" and (include_crosswalk or include_query):
            order.append(q)
        elif q != "crosswalk-matrix-builder" and include_query:
            order.append(q)

    for name in order:
        should_run, reason = _plan_should_run(name)
        if not should_run:
            skipped.append(name)
            run_records.append(
                {
                    "plugin": name,
                    "status": "skipped",
                    "reason": reason,
                }
            )
            continue
        record = run_plugin(name, lambda n=name: inputs_for(n), artifacts_root, errors_root)
        run_records.append(record)

        # Capture downstream dependencies from successful outputs.
        if record["status"] == "succeeded":
            json_path = artifacts_root / name / f"{PLUGIN_DISPATCH[name]['stem']}.json"
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                data = None
            if name == "risk-register-builder" and isinstance(data, dict):
                shared["risk_register_rows"] = data.get("rows") or []
                shared["risks_summary_ref"] = (
                    f"risk-register.json with {len(shared['risk_register_rows'])} rows"
                )
            if name == "soa-generator" and isinstance(data, dict):
                shared["soa_rows"] = data.get("rows") or []
            if name == "metrics-collector" and isinstance(data, dict):
                summary = data.get("summary") or {}
                shared["metrics_summary_ref"] = (
                    f"metrics-report.json with {summary.get('total_kpi_records', 0)} KPIs, "
                    f"{summary.get('threshold_breach_count', 0)} breaches"
                )
            if name == "nonconformity-tracker" and isinstance(data, dict):
                summary = data.get("summary") or {}
                shared["nc_summary_ref"] = (
                    f"nonconformity-register.json with {summary.get('total_records', 0)} records"
                )
            if name == "evidence-bundle-packager" and isinstance(data, dict):
                bp = data.get("bundle_path")
                if bp:
                    shared["bundle_path"] = bp
            if name == "certification-readiness" and isinstance(data, dict):
                shared["readiness_snapshot"] = data

    wall = round(time.monotonic() - wall_start, 4)
    succeeded = sum(1 for r in run_records if r["status"] == "succeeded")
    failed = sum(1 for r in run_records if r["status"] == "failed")
    skipped_count = sum(1 for r in run_records if r["status"] == "skipped")

    summary = {
        "organization_name": organization_name(config),
        "timestamp": utc_now_iso(),
        "plugins_run": succeeded + failed,
        "plugins_succeeded": succeeded,
        "plugins_failed": failed,
        "plugins_skipped": skipped_count,
        "wall_clock_seconds": wall,
        "jurisdictions_detected": sorted(jur),
        "plugins": run_records,
    }
    write_json(output_root / "run-summary.json", summary)
    write_text(output_root / "run-summary.md", _render_summary_md(summary))

    if failed:
        sys.stderr.write(
            f"[aigovops] run complete with {failed} failure(s); "
            f"see {output_root / 'errors'} for details\n"
        )
    else:
        sys.stderr.write(
            f"[aigovops] run complete: {succeeded} succeeded, "
            f"{skipped_count} skipped, 0 failures in {wall}s\n"
        )
    return 0


def _render_summary_md(summary: dict[str, Any]) -> str:
    lines = [
        "# AIGovOps run summary",
        "",
        f"Organization: {summary['organization_name']}",
        f"Timestamp: {summary['timestamp']}",
        f"Wall clock (seconds): {summary['wall_clock_seconds']}",
        f"Jurisdictions detected: {', '.join(summary['jurisdictions_detected']) or 'none'}",
        "",
        "## Counts",
        "",
        f"- Plugins run: {summary['plugins_run']}",
        f"- Succeeded: {summary['plugins_succeeded']}",
        f"- Failed: {summary['plugins_failed']}",
        f"- Skipped: {summary['plugins_skipped']}",
        "",
        "## Per-plugin results",
        "",
        "| Plugin | Status | Duration (s) | Notes |",
        "|---|---|---|---|",
    ]
    for r in summary["plugins"]:
        duration = r.get("duration_seconds", "")
        notes = r.get("reason") or r.get("error") or ""
        escaped_notes = notes.replace("|", "\\|")
        lines.append(
            f"| {r['plugin']} | {r['status']} | {duration} | {escaped_notes} |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Pack / Verify / Inspect subcommands (delegated to evidence-bundle-packager)
# ---------------------------------------------------------------------------


_BUNDLE_MISSING_MSG = (
    "evidence-bundle-packager plugin not yet shipped; "
    "run `aigovops run` without pack first."
)


def cmd_pack(args: argparse.Namespace) -> int:
    module = try_load_bundle_packager()
    if module is None or not hasattr(module, "pack_bundle"):
        sys.stderr.write(f"[aigovops] {_BUNDLE_MISSING_MSG}\n")
        return 3
    pack_inputs: dict[str, Any] = {
        "artifacts_dir": str(Path(args.artifacts).resolve()),
        "output_dir": str(Path(args.output).resolve()),
        "signing_algorithm": args.signing_algorithm,
    }
    if args.scope_file:
        pack_inputs["scope_file"] = str(Path(args.scope_file).resolve())
    try:
        result = module.pack_bundle(pack_inputs)
    except Exception as exc:
        sys.stderr.write(f"[aigovops] pack failed: {exc}\n")
        return 4
    sys.stdout.write(json.dumps(result, indent=2, default=str) + "\n")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    module = try_load_bundle_packager()
    if module is None or not hasattr(module, "verify_bundle"):
        sys.stderr.write(f"[aigovops] {_BUNDLE_MISSING_MSG}\n")
        return 3
    try:
        result = module.verify_bundle({"bundle_dir": str(Path(args.bundle).resolve())})
    except Exception as exc:
        sys.stderr.write(f"[aigovops] verify failed: {exc}\n")
        return 4
    sys.stdout.write(json.dumps(result, indent=2, default=str) + "\n")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    module = try_load_bundle_packager()
    if module is None or not hasattr(module, "inspect_bundle"):
        sys.stderr.write(f"[aigovops] {_BUNDLE_MISSING_MSG}\n")
        return 3
    try:
        result = module.inspect_bundle({"bundle_dir": str(Path(args.bundle).resolve())})
    except Exception as exc:
        sys.stderr.write(f"[aigovops] inspect failed: {exc}\n")
        return 4
    sys.stdout.write(json.dumps(result, indent=2, default=str) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Doctor subcommand
# ---------------------------------------------------------------------------


def cmd_doctor(args: argparse.Namespace) -> int:
    results: list[tuple[str, bool, str]] = []

    # Python version.
    pv = sys.version_info
    ok_py = pv >= (3, 10)
    results.append(
        (
            "python version >= 3.10",
            ok_py,
            f"detected {pv.major}.{pv.minor}.{pv.micro}",
        )
    )

    # PyYAML.
    try:
        import yaml  # noqa: F401

        results.append(("PyYAML importable", True, f"version {yaml.__version__}"))
    except Exception as exc:
        results.append(("PyYAML importable", False, str(exc)))

    # Every plugin importable.
    for plugin_name in PLUGIN_DISPATCH:
        try:
            module = load_plugin_module(plugin_name)
            entry = PLUGIN_DISPATCH[plugin_name]["entry"]
            if not hasattr(module, entry):
                results.append(
                    (
                        f"plugin {plugin_name} importable",
                        False,
                        f"missing entry function {entry}",
                    )
                )
            else:
                results.append((f"plugin {plugin_name} importable", True, "ok"))
        except Exception as exc:
            results.append((f"plugin {plugin_name} importable", False, str(exc)))

    # Consistency audit.
    audit_path = REPO_ROOT / "tests" / "audit" / "consistency_audit.py"
    if audit_path.exists():
        try:
            spec = importlib.util.spec_from_file_location(
                "_consistency_audit", audit_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "main"):
                import io
                import contextlib

                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    try:
                        rc = module.main()
                    except SystemExit as se:
                        rc = int(se.code or 0)
                ok = rc == 0
                results.append(("consistency audit", ok, "exit 0" if ok else f"exit {rc}"))
            else:
                results.append(
                    ("consistency audit", True, "audit module has no main(); skipped")
                )
        except Exception as exc:
            results.append(("consistency audit", False, str(exc)))
    else:
        results.append(("consistency audit", True, "audit script not present; skipped"))

    all_ok = all(ok for _, ok, _ in results)
    for label, ok, detail in results:
        status = "OK" if ok else "FAIL"
        sys.stdout.write(f"[{status}] {label}: {detail}\n")
    return 0 if all_ok else 1


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aigovops",
        description="AIGovOps unified CLI: orchestrate the AIMS pipeline from one organization.yaml.",
    )
    sub = parser.add_subparsers(dest="cmd", metavar="subcommand")

    p_run = sub.add_parser(
        "run",
        help="Run the full AIMS pipeline against an organization.yaml.",
    )
    p_run.add_argument("--org", required=True, help="path to organization.yaml")
    p_run.add_argument("--output", required=True, help="output directory")
    p_run.add_argument(
        "--skip-plugin",
        action="append",
        default=[],
        help="plugin name to skip (repeatable)",
    )
    p_run.add_argument(
        "--framework",
        default=None,
        help="override target_framework for gap-assessment (iso42001|nist-ai-rmf|eu-ai-act)",
    )
    p_run.add_argument(
        "--include-crosswalk-export",
        action="store_true",
        help="include crosswalk-matrix-builder in the run",
    )
    p_run.add_argument(
        "--include-query-plugins",
        action="store_true",
        help=(
            "invoke query plugins (cascade-impact-analyzer, "
            "crosswalk-matrix-builder) with default inputs for validation"
        ),
    )
    p_run.set_defaults(func=cmd_run)

    p_pack = sub.add_parser(
        "pack", help="Pack generated artifacts into a signed evidence bundle."
    )
    p_pack.add_argument("--artifacts", required=True)
    p_pack.add_argument("--output", required=True)
    p_pack.add_argument("--signing-algorithm", default="hmac-sha256")
    p_pack.add_argument("--scope-file", default=None)
    p_pack.set_defaults(func=cmd_pack)

    p_verify = sub.add_parser("verify", help="Verify a signed evidence bundle.")
    p_verify.add_argument("--bundle", required=True)
    p_verify.set_defaults(func=cmd_verify)

    p_inspect = sub.add_parser(
        "inspect", help="Print a summary of an evidence bundle."
    )
    p_inspect.add_argument("--bundle", required=True)
    p_inspect.set_defaults(func=cmd_inspect)

    p_doctor = sub.add_parser(
        "doctor", help="Sanity check the local environment and plugin catalogue."
    )
    p_doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help(sys.stderr)
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
