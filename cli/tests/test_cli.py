"""
Tests for the aigovops CLI.

Run directly:

    python3 cli/tests/test_cli.py

All tests are stdlib-only (+ PyYAML, already repo-wide).
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from cli import runner  # noqa: E402
from cli.loader import (  # noqa: E402
    OrganizationConfigError,
    load_organization,
)


EXAMPLE_ORG = REPO_ROOT / "examples" / "organization.example.yaml"
BIN = REPO_ROOT / "bin" / "aigovops"


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    """Invoke runner.main with captured stdout/stderr. Returns (rc, out, err)."""
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    try:
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            rc = runner.main(argv)
    except SystemExit as se:
        rc = int(se.code or 0)
    return rc, out_buf.getvalue(), err_buf.getvalue()


class DoctorTests(unittest.TestCase):
    def test_doctor_on_healthy_repo(self):
        """Doctor reports OK on every check except pre-existing audit gaps.

        The consistency audit surfaces repo-level gaps unrelated to the CLI
        (missing SKILL.md for planned skills). This test accepts either exit
        code and verifies every CLI-owned check (python, PyYAML, plugin
        imports) is OK.
        """
        rc, out, _ = _run_cli(["doctor"])
        self.assertIn("[OK] python version >= 3.10", out)
        self.assertIn("[OK] PyYAML importable", out)
        for name in runner.PLUGIN_DISPATCH:
            self.assertIn(f"[OK] plugin {name} importable", out)
        self.assertIn(rc, (0, 1))


class HelpTests(unittest.TestCase):
    def test_help_output(self):
        rc, out, _ = _run_cli(["--help"])
        # argparse emits help to stdout on --help, exits 0.
        self.assertEqual(rc, 0)
        for sub in ("run", "pack", "verify", "inspect", "doctor"):
            self.assertIn(sub, out)

    def test_invalid_subcommand_fails_cleanly(self):
        rc, out, err = _run_cli(["not-a-command"])
        # argparse emits an error to stderr and exits with code 2.
        self.assertNotEqual(rc, 0)
        # Must not dump a Python traceback.
        self.assertNotIn("Traceback", err)
        self.assertNotIn("Traceback", out)


class OrganizationLoaderTests(unittest.TestCase):
    def test_organization_yaml_load_succeeds(self):
        config = load_organization(EXAMPLE_ORG)
        self.assertIn("organization", config)
        self.assertEqual(config["organization"]["name"], "Acme HR Technologies")
        self.assertTrue(config.get("ai_systems"))

    def test_organization_yaml_load_fails_on_missing_required_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "broken.yaml"
            p.write_text("some_other_top: {}\n", encoding="utf-8")
            with self.assertRaises(OrganizationConfigError):
                load_organization(p)


class RunPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.mkdtemp(prefix="aigovops-test-")
        cls.output_dir = Path(cls._tmpdir) / "run1"
        cls._rc, _, cls._err = _run_cli(
            ["run", "--org", str(EXAMPLE_ORG), "--output", str(cls.output_dir)]
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_run_happy_path_demo_scenario(self):
        self.assertEqual(self._rc, 0, f"run failed: {self._err}")
        summary_path = self.output_dir / "run-summary.json"
        self.assertTrue(summary_path.is_file())
        summary = json.loads(summary_path.read_text())
        # After wiring all 34 plugins, the default run invokes 32 pipeline
        # plugins (cascade-impact-analyzer and crosswalk-matrix-builder are
        # query plugins and skipped unless --include-query-plugins is set).
        expected_count = 32
        total = summary["plugins_succeeded"] + summary["plugins_skipped"] + summary["plugins_failed"]
        self.assertEqual(total, expected_count,
                         f"expected {expected_count} plugins scheduled; got {total}")
        self.assertGreater(summary["plugins_succeeded"], 25)
        self.assertEqual(summary["plugins_failed"], 0)

    def test_run_summary_has_required_fields(self):
        summary_path = self.output_dir / "run-summary.json"
        self.assertTrue(summary_path.is_file())
        summary = json.loads(summary_path.read_text())
        for key in (
            "plugins_run",
            "plugins_succeeded",
            "plugins_failed",
            "plugins_skipped",
            "wall_clock_seconds",
            "timestamp",
            "organization_name",
        ):
            self.assertIn(key, summary, f"missing key: {key}")

    def test_output_directory_structure(self):
        self.assertTrue((self.output_dir / "artifacts").is_dir())
        self.assertTrue((self.output_dir / "errors").is_dir())
        self.assertTrue((self.output_dir / "run-summary.json").is_file())
        self.assertTrue((self.output_dir / "run-summary.md").is_file())

    def test_jurisdiction_specific_plugins_invoked_conditionally(self):
        summary = json.loads((self.output_dir / "run-summary.json").read_text())
        statuses = {r["plugin"]: r["status"] for r in summary["plugins"]}
        # usa-co is an operational jurisdiction -> colorado should run.
        self.assertEqual(statuses.get("colorado-ai-act-compliance"), "succeeded")
        # usa-nyc is operational -> nyc-ll144 should run (AEDT system).
        self.assertEqual(statuses.get("nyc-ll144-audit-packager"), "succeeded")
        # UK is not in scope -> uk-atrs-recorder skipped.
        self.assertEqual(statuses.get("uk-atrs-recorder"), "skipped")
        # Singapore not in scope -> skipped.
        self.assertEqual(statuses.get("singapore-magf-assessor"), "skipped")


class RunSkipAndErrorTests(unittest.TestCase):
    def test_run_with_skip_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, _ = _run_cli(
                [
                    "run",
                    "--org",
                    str(EXAMPLE_ORG),
                    "--output",
                    tmp,
                    "--skip-plugin",
                    "risk-register-builder",
                ]
            )
            self.assertEqual(rc, 0)
            summary = json.loads((Path(tmp) / "run-summary.json").read_text())
            statuses = {r["plugin"]: r["status"] for r in summary["plugins"]}
            self.assertEqual(statuses.get("risk-register-builder"), "skipped")

    def test_run_on_broken_plugin_continues(self):
        # Build a minimal organization with valid top-level shape but a
        # data_register dataset whose 'source' is an invalid enum. This
        # forces data-register-builder to raise, while leaving every
        # other plugin invocable.
        with tempfile.TemporaryDirectory() as tmp:
            bad_org = Path(tmp) / "bad.yaml"
            bad_org.write_text(
                "organization:\n"
                "  name: Tiny Co\n"
                "  headquarters_jurisdiction: usa-co\n"
                "  operational_jurisdictions: [usa-co]\n"
                "ai_systems:\n"
                "  - system_id: SYS-X\n"
                "    system_ref: SYS-X\n"
                "    system_name: SysX\n"
                "    intended_use: test\n"
                "    purpose: test\n"
                "    sector: HR\n"
                "    risk_tier: limited\n"
                "    jurisdiction: [usa-co]\n"
                "data_register_inputs:\n"
                "  data_inventory:\n"
                "    - id: DS1\n"
                "      name: Bad dataset\n"
                "      purpose_stage: training\n"
                "      source: not-a-valid-source\n",
                encoding="utf-8",
            )
            out_dir = Path(tmp) / "out"
            rc, _, _ = _run_cli(
                ["run", "--org", str(bad_org), "--output", str(out_dir)]
            )
            # CLI should exit 0 even when an individual plugin raises.
            self.assertEqual(rc, 0)
            summary = json.loads((out_dir / "run-summary.json").read_text())
            self.assertGreaterEqual(summary["plugins_failed"], 1)
            # Error file present for the failing plugin.
            errs = list((out_dir / "errors").glob("*.txt"))
            self.assertTrue(errs)


class BundlePackagerTests(unittest.TestCase):
    """Test that pack/verify/inspect delegate to evidence-bundle-packager when
    present, and emit a clean error when absent. The packager is developed
    by a separate subagent and may or may not be installed at test time."""

    def _packager_present(self) -> bool:
        return (REPO_ROOT / "plugins" / "evidence-bundle-packager" / "plugin.py").is_file()

    def test_pack_delegates_to_bundle_packager(self):
        rc, _, err = _run_cli(
            [
                "pack",
                "--artifacts",
                str(REPO_ROOT),
                "--output",
                "/tmp/aigovops-bundle",
            ]
        )
        if not self._packager_present():
            self.assertEqual(rc, 3)
            self.assertIn("evidence-bundle-packager", err)
        else:
            # Packager present: we only check the CLI invoked the delegate;
            # the delegate's behaviour is its own plugin's responsibility.
            self.assertIn(rc, (0, 4))

    def test_verify_delegates_to_bundle_packager(self):
        rc, _, err = _run_cli(["verify", "--bundle", "/tmp/aigovops-bundle"])
        if not self._packager_present():
            self.assertEqual(rc, 3)
            self.assertIn("evidence-bundle-packager", err)
        else:
            self.assertIn(rc, (0, 4))

    def test_inspect_delegates_to_bundle_packager(self):
        rc, _, err = _run_cli(["inspect", "--bundle", "/tmp/aigovops-bundle"])
        if not self._packager_present():
            self.assertEqual(rc, 3)
            self.assertIn("evidence-bundle-packager", err)
        else:
            self.assertIn(rc, (0, 4))


class WiredPluginsTests(unittest.TestCase):
    """Tests covering the 15 newly-wired plugins: gating, invocation, and
    graceful handling of minimal inputs.
    """

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.mkdtemp(prefix="aigovops-wired-")
        cls.output_dir = Path(cls._tmpdir) / "run"
        cls._rc, _, _ = _run_cli(
            ["run", "--org", str(EXAMPLE_ORG), "--output", str(cls.output_dir)]
        )
        cls.summary = json.loads(
            (cls.output_dir / "run-summary.json").read_text()
        )
        cls.status_by_plugin = {r["plugin"]: r["status"] for r in cls.summary["plugins"]}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_expected_total_plugins_in_default_run(self):
        """Default `run` schedules 32 plugins (all 34 minus 2 query plugins)."""
        total = (
            self.summary["plugins_succeeded"]
            + self.summary["plugins_skipped"]
            + self.summary["plugins_failed"]
        )
        self.assertEqual(total, 32)

    def test_supplier_vendor_assessor_runs(self):
        self.assertEqual(self.status_by_plugin.get("supplier-vendor-assessor"), "succeeded")

    def test_bias_evaluator_runs_with_minimal_inputs(self):
        self.assertEqual(self.status_by_plugin.get("bias-evaluator"), "succeeded")

    def test_robustness_evaluator_runs_with_minimal_inputs(self):
        self.assertEqual(self.status_by_plugin.get("robustness-evaluator"), "succeeded")

    def test_human_oversight_designer_runs(self):
        self.assertEqual(self.status_by_plugin.get("human-oversight-designer"), "succeeded")

    def test_system_event_logger_runs(self):
        self.assertEqual(self.status_by_plugin.get("system-event-logger"), "succeeded")

    def test_explainability_documenter_runs(self):
        self.assertEqual(self.status_by_plugin.get("explainability-documenter"), "succeeded")

    def test_incident_reporting_runs_always_with_warnings_on_empty_incidents(self):
        """incident-reporting is unconditional; with no incidents it emits
        warnings but the plugin call still succeeds."""
        self.assertEqual(self.status_by_plugin.get("incident-reporting"), "succeeded")
        incident_json = (
            self.output_dir / "artifacts" / "incident-reporting" / "incident-report.json"
        )
        self.assertTrue(incident_json.is_file())

    def test_genai_skipped_for_non_generative_systems(self):
        """The example org has a classical-ML system; genai-risk-register must skip."""
        entry = next(
            r for r in self.summary["plugins"] if r["plugin"] == "genai-risk-register"
        )
        self.assertEqual(entry["status"], "skipped")
        self.assertIn("generative", entry.get("reason", "").lower())

    def test_gpai_skipped_for_non_generative_systems(self):
        entry = next(
            r for r in self.summary["plugins"] if r["plugin"] == "gpai-obligations-tracker"
        )
        self.assertEqual(entry["status"], "skipped")

    def test_eu_conformity_skipped_when_no_eu_jurisdiction(self):
        entry = next(
            r for r in self.summary["plugins"] if r["plugin"] == "eu-conformity-assessor"
        )
        self.assertEqual(entry["status"], "skipped")

    def test_evidence_bundle_packager_runs_after_other_plugins(self):
        order = [r["plugin"] for r in self.summary["plugins"]]
        bundle_idx = order.index("evidence-bundle-packager")
        for earlier in (
            "ai-system-inventory-maintainer",
            "risk-register-builder",
            "soa-generator",
            "management-review-packager",
        ):
            self.assertLess(order.index(earlier), bundle_idx)

    def test_certification_readiness_runs_when_bundle_available(self):
        self.assertEqual(self.status_by_plugin.get("evidence-bundle-packager"), "succeeded")
        self.assertEqual(self.status_by_plugin.get("certification-readiness"), "succeeded")

    def test_certification_path_planner_runs_after_readiness(self):
        self.assertEqual(self.status_by_plugin.get("certification-path-planner"), "succeeded")
        order = [r["plugin"] for r in self.summary["plugins"]]
        self.assertLess(
            order.index("certification-readiness"),
            order.index("certification-path-planner"),
        )

    def test_query_plugins_not_invoked_by_default(self):
        """cascade-impact-analyzer and crosswalk-matrix-builder skip absent flag."""
        for q in ("cascade-impact-analyzer", "crosswalk-matrix-builder"):
            # Query plugins may be absent from the summary entirely, which is
            # equivalent to skipped.
            status = self.status_by_plugin.get(q)
            self.assertIn(status, (None, "skipped"))


class QueryPluginsOptInTest(unittest.TestCase):
    def test_query_plugins_invoked_with_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, _ = _run_cli([
                "run",
                "--org", str(EXAMPLE_ORG),
                "--output", tmp,
                "--include-query-plugins",
            ])
            self.assertEqual(rc, 0)
            summary = json.loads((Path(tmp) / "run-summary.json").read_text())
            statuses = {r["plugin"]: r["status"] for r in summary["plugins"]}
            self.assertEqual(statuses.get("cascade-impact-analyzer"), "succeeded")
            self.assertEqual(statuses.get("crosswalk-matrix-builder"), "succeeded")


class EUConformityGatingTest(unittest.TestCase):
    def test_eu_conformity_runs_when_eu_high_risk_present(self):
        """If the org has an EU jurisdiction plus a high-risk system,
        eu-conformity-assessor must run."""
        with tempfile.TemporaryDirectory() as tmp:
            bad_org = Path(tmp) / "eu.yaml"
            bad_org.write_text(
                "organization:\n"
                "  name: EuCo\n"
                "  headquarters_jurisdiction: eu\n"
                "  operational_jurisdictions: [eu]\n"
                "ai_systems:\n"
                "  - system_id: SYS-EU\n"
                "    system_ref: SYS-EU\n"
                "    system_name: EUScreen\n"
                "    intended_use: test\n"
                "    purpose: test\n"
                "    sector: employment\n"
                "    risk_tier: high-risk-annex-iii\n"
                "    annex_iii_category: 4-employment\n"
                "    jurisdiction: [eu]\n"
                "    lifecycle_state: in-service\n",
                encoding="utf-8",
            )
            out_dir = Path(tmp) / "out"
            rc, _, _ = _run_cli([
                "run", "--org", str(bad_org), "--output", str(out_dir)
            ])
            self.assertEqual(rc, 0)
            summary = json.loads((out_dir / "run-summary.json").read_text())
            statuses = {r["plugin"]: r["status"] for r in summary["plugins"]}
            self.assertEqual(statuses.get("eu-conformity-assessor"), "succeeded")


class GenAIGatingTest(unittest.TestCase):
    def test_genai_risk_register_runs_only_for_generative_systems(self):
        with tempfile.TemporaryDirectory() as tmp:
            org = Path(tmp) / "genai.yaml"
            org.write_text(
                "organization:\n"
                "  name: GenAICo\n"
                "  headquarters_jurisdiction: usa-ca\n"
                "ai_systems:\n"
                "  - system_id: SYS-G\n"
                "    system_ref: SYS-G\n"
                "    system_name: GenModel\n"
                "    intended_use: test\n"
                "    purpose: test\n"
                "    sector: general\n"
                "    risk_tier: limited-risk\n"
                "    model_type: transformer\n"
                "    is_generative: true\n"
                "    jurisdiction: [usa-ca]\n"
                "    lifecycle_state: in-service\n",
                encoding="utf-8",
            )
            out_dir = Path(tmp) / "out"
            rc, _, _ = _run_cli([
                "run", "--org", str(org), "--output", str(out_dir)
            ])
            self.assertEqual(rc, 0)
            summary = json.loads((out_dir / "run-summary.json").read_text())
            statuses = {r["plugin"]: r["status"] for r in summary["plugins"]}
            self.assertEqual(statuses.get("genai-risk-register"), "succeeded")
            self.assertEqual(statuses.get("gpai-obligations-tracker"), "succeeded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
