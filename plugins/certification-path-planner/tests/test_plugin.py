"""Tests for certification-path-planner plugin. Runs under pytest or standalone."""

from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


# ---------------------------------------------------------------------------
# Synthetic readiness snapshot helpers
# ---------------------------------------------------------------------------


def _future_date(days: int) -> str:
    d = datetime.now(timezone.utc).date() + timedelta(days=days)
    return d.isoformat()


def _past_date(days: int) -> str:
    d = datetime.now(timezone.utc).date() - timedelta(days=days)
    return d.isoformat()


def _readiness_snapshot(
    gaps: list[dict] | None = None,
    blockers: list[dict] | None = None,
    remediations: list[dict] | None = None,
    bundle_id: str = "bundle-abc123",
) -> dict:
    return {
        "timestamp": "2026-04-18T12:00:00Z",
        "agent_signature": "certification-readiness/0.1.0",
        "bundle_id_ref": bundle_id,
        "target_certification": "iso42001-stage2",
        "readiness_level": "partially-ready",
        "gaps": gaps or [],
        "blockers": blockers or [],
        "remediations": remediations or [],
    }


def _remediation(gap_key: str, target_plugin: str = "soa-generator") -> dict:
    return {
        "gap_key": gap_key,
        "gap_description": f"Synthetic description for {gap_key}.",
        "recommended_action": f"Run {target_plugin}.",
        "owner_role": "AIMS Owner",
        "target_plugin": target_plugin,
        "suggested_deadline": _future_date(30),
    }


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class HappyPathTests(unittest.TestCase):
    def test_happy_path_iso42001_stage2(self):
        snapshot = _readiness_snapshot(
            remediations=[
                _remediation("missing-soa"),
                _remediation("missing-risk-register", "risk-register-builder"),
                _remediation("missing-management-review-package", "management-review-packager"),
            ],
        )
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage2",
            "target_date": _future_date(180),
        })
        self.assertIn("plan_id", plan)
        self.assertTrue(plan["plan_id"].startswith("cert-path-iso42001-stage2-"))
        self.assertEqual(plan["agent_signature"], plugin.AGENT_SIGNATURE)
        self.assertEqual(plan["target_certification"], "iso42001-stage2")
        self.assertTrue(plan["milestones"])
        self.assertIn("summary", plan)
        self.assertGreater(plan["summary"]["milestone_count"], 0)
        self.assertEqual(
            plan["summary"]["remediation_count"], 3,
        )

    def test_all_required_top_level_fields_present(self):
        snapshot = _readiness_snapshot(remediations=[_remediation("missing-soa")])
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(90),
        })
        for field in (
            "plan_id", "timestamp", "agent_signature", "target_certification",
            "target_date", "current_readiness_snapshot_ref", "milestones",
            "blockers", "recertification_triggers", "capacity_assessment",
            "citations", "warnings", "summary",
        ):
            self.assertIn(field, plan, f"missing field {field}")


# ---------------------------------------------------------------------------
# Risk-weighted ordering
# ---------------------------------------------------------------------------


class RiskWeightedOrderingTests(unittest.TestCase):
    def test_blockers_sort_ahead_of_gaps(self):
        snapshot = _readiness_snapshot(
            gaps=[{"gap_key": "missing-audit-log-entry", "artifact_type": "audit-log-entry"}],
            blockers=[{"gap_key": "missing-soa", "artifact_type": "soa"}],
            remediations=[
                _remediation("missing-audit-log-entry", "audit-log-generator"),
                _remediation("missing-soa"),
            ],
        )
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(120),
            "organization_capacity": {"weekly_hours_available": 2},  # force split
        })
        # Highest priority (blocker) must appear in the first milestone.
        first = plan["milestones"][0]
        first_keys = [
            ar["source_gap_key"] for ar in first["remediation_action_requests"]
        ]
        self.assertIn("missing-soa", first_keys)

    def test_risk_register_score_boosts_priority(self):
        snapshot = _readiness_snapshot(
            gaps=[
                {"gap_key": "missing-soa", "artifact_type": "soa"},
                {"gap_key": "missing-risk-register", "artifact_type": "risk-register"},
            ],
            remediations=[
                _remediation("missing-soa"),
                _remediation("missing-risk-register", "risk-register-builder"),
            ],
        )
        # Attach a high-inherent-risk entry that anchors to "risk-register".
        risk_register = {
            "risks": [
                {
                    "id": "R-001",
                    "inherent_risk_score": 25,
                    "controls_affected": ["risk-register"],
                },
            ],
        }
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(120),
            "risk_register_ref": risk_register,
            "organization_capacity": {"weekly_hours_available": 2},
        })
        first_keys = [
            ar["source_gap_key"]
            for ar in plan["milestones"][0]["remediation_action_requests"]
        ]
        self.assertIn("missing-risk-register", first_keys)


# ---------------------------------------------------------------------------
# Milestone packing and capacity
# ---------------------------------------------------------------------------


class MilestonePackingTests(unittest.TestCase):
    def test_packing_within_capacity_single_milestone(self):
        snapshot = _readiness_snapshot(
            remediations=[_remediation("missing-audit-log-entry", "audit-log-generator")],
        )
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(60),
            "organization_capacity": {"weekly_hours_available": 40},
            "minimum_milestone_interval_weeks": 4,
        })
        # Small gap (8h) fits easily in 40*4=160 hours.
        self.assertEqual(len(plan["milestones"]), 1)

    def test_capacity_splits_work_into_multiple_milestones(self):
        snapshot = _readiness_snapshot(
            remediations=[
                _remediation("missing-soa"),            # 160h
                _remediation("missing-risk-register", "risk-register-builder"),  # 160h
            ],
        )
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(180),
            "organization_capacity": {"weekly_hours_available": 40},
            "minimum_milestone_interval_weeks": 4,
        })
        # 160h capacity per milestone; two large items should split across two.
        self.assertEqual(len(plan["milestones"]), 2)

    def test_capacity_exceeded_warning_emitted(self):
        # A single large item exceeds a 4h/week budget.
        snapshot = _readiness_snapshot(
            remediations=[_remediation("missing-soa")],
        )
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(60),
            "organization_capacity": {"weekly_hours_available": 4},
            "minimum_milestone_interval_weeks": 4,
        })
        self.assertTrue(any(
            "overruns team capacity" in w for w in plan["warnings"]
        ))


# ---------------------------------------------------------------------------
# Hard-blocker propagation
# ---------------------------------------------------------------------------


class HardBlockerTests(unittest.TestCase):
    def test_hard_blocker_marks_milestone_blocked(self):
        snapshot = _readiness_snapshot(
            remediations=[_remediation("legal-review-pending", "high-risk-classifier")],
        )
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "eu-ai-act-internal-control",
            "target_date": _future_date(120),
            "hard_blockers": [
                {
                    "id": "HB-001",
                    "description": "Pending external legal opinion from outside counsel.",
                    "affected_gap_keys": ["legal-review-pending"],
                },
            ],
        })
        self.assertTrue(plan["blockers"])
        self.assertEqual(plan["blockers"][0]["id"], "HB-001")
        # Milestone carrying the affected remediation must be marked blocked.
        affected_milestones = [
            m for m in plan["milestones"]
            if any(
                ar["source_gap_key"] == "legal-review-pending"
                for ar in m["remediation_action_requests"]
            )
        ]
        self.assertTrue(affected_milestones)
        for m in affected_milestones:
            self.assertEqual(m["status"], "blocked")

    def test_hard_blocker_string_form_accepted(self):
        snapshot = _readiness_snapshot(
            remediations=[_remediation("missing-soa")],
        )
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(120),
            "hard_blockers": ["Budget freeze until FY27"],
        })
        self.assertEqual(plan["blockers"][0]["description"], "Budget freeze until FY27")


# ---------------------------------------------------------------------------
# Recertification trigger scheduling
# ---------------------------------------------------------------------------


class RecertificationTriggerTests(unittest.TestCase):
    def test_iso42001_stage2_schedules_two_surveillance_audits(self):
        snapshot = _readiness_snapshot(remediations=[_remediation("missing-soa")])
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage2",
            "target_date": _future_date(180),
        })
        trigger_types = [t["trigger_type"] for t in plan["recertification_triggers"]]
        self.assertEqual(
            trigger_types.count("surveillance-audit"), 2,
        )

    def test_nyc_ll144_schedules_annual_reaudit(self):
        snapshot = _readiness_snapshot(remediations=[_remediation("missing-nyc-ll144-audit-package", "nyc-ll144-audit-packager")])
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "nyc-ll144-annual-audit",
            "target_date": _future_date(90),
        })
        triggers = plan["recertification_triggers"]
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]["trigger_type"], "annual-reaudit")

    def test_colorado_sb205_schedules_annual_impact_refresh(self):
        snapshot = _readiness_snapshot(remediations=[_remediation("sb205-conformance-missing", "colorado-ai-act-compliance")])
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "colorado-sb205-safe-harbor",
            "target_date": _future_date(90),
        })
        trigger_types = [t["trigger_type"] for t in plan["recertification_triggers"]]
        self.assertIn("impact-assessment-refresh", trigger_types)


# ---------------------------------------------------------------------------
# Target-date warnings
# ---------------------------------------------------------------------------


class TargetDateWarningTests(unittest.TestCase):
    def test_target_date_past_warning(self):
        snapshot = _readiness_snapshot(remediations=[_remediation("missing-soa")])
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _past_date(5),
        })
        self.assertTrue(any(
            "target date is too close or past" in w for w in plan["warnings"]
        ))
        self.assertEqual(plan["summary"]["target_date_feasibility"], "not-feasible")

    def test_target_date_too_close_warning(self):
        snapshot = _readiness_snapshot(remediations=[_remediation("missing-soa")])
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(3),
        })
        self.assertTrue(any(
            "target date is too close or past" in w for w in plan["warnings"]
        ))
        self.assertEqual(plan["summary"]["target_date_feasibility"], "tight")


# ---------------------------------------------------------------------------
# Action-request shape
# ---------------------------------------------------------------------------


class ActionRequestShapeTests(unittest.TestCase):
    def test_action_request_contract(self):
        snapshot = _readiness_snapshot(
            remediations=[
                _remediation("missing-soa"),
                _remediation("missing-gap-assessment", "gap-assessment"),
            ],
        )
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(120),
        })
        for ms in plan["milestones"]:
            for ar in ms["remediation_action_requests"]:
                self.assertIn("action_type", ar)
                self.assertEqual(ar["action_type"], "invoke-plugin")
                self.assertIn("target_plugin", ar)
                self.assertIn("args", ar)
                self.assertIn("rationale", ar)
                self.assertIn("authority", ar)
                self.assertIn(ar["authority"], ("ask-permission", "take-resolving-action"))

    def test_routine_gap_uses_take_resolving_action(self):
        snapshot = _readiness_snapshot(
            remediations=[_remediation("missing-gap-assessment", "gap-assessment")],
        )
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(120),
        })
        action_request = plan["milestones"][0]["remediation_action_requests"][0]
        self.assertEqual(action_request["authority"], "take-resolving-action")


# ---------------------------------------------------------------------------
# Citations and anti-hallucination
# ---------------------------------------------------------------------------


class CitationsTests(unittest.TestCase):
    def test_citations_use_canonical_formats(self):
        snapshot = _readiness_snapshot(remediations=[_remediation("missing-soa")])
        for target in (
            "iso42001-stage2",
            "eu-ai-act-internal-control",
            "colorado-sb205-safe-harbor",
            "nyc-ll144-annual-audit",
        ):
            plan = plugin.plan_certification_path({
                "current_readiness_ref": snapshot,
                "target_certification": target,
                "target_date": _future_date(180),
            })
            for c in plan["citations"]:
                prefix_ok = (
                    c.startswith("ISO/IEC 42001:2023, Clause ")
                    or c.startswith("ISO/IEC 42001:2023, Annex A")
                    or c.startswith("EU AI Act, Article ")
                    or c.startswith("EU AI Act, Annex ")
                    or c.startswith("Colorado SB 205, Section ")
                    or c.startswith("NYC LL144")
                    or c.startswith("Singapore MAGF 2e")
                    or c.startswith("UK ATRS, Section ")
                )
                self.assertTrue(
                    prefix_ok,
                    msg=f"citation {c!r} does not match STYLE.md prefix",
                )

    def test_no_invention_of_gaps_outside_snapshot(self):
        # Empty remediations in the snapshot must produce zero remediation
        # action requests.
        snapshot = _readiness_snapshot(remediations=[])
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(120),
        })
        self.assertEqual(plan["summary"]["remediation_count"], 0)
        self.assertEqual(plan["milestones"], [])


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class RenderingTests(unittest.TestCase):
    def _make_plan(self):
        snapshot = _readiness_snapshot(
            remediations=[
                _remediation("missing-soa"),
                _remediation("missing-audit-log-entry", "audit-log-generator"),
            ],
        )
        return plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage2",
            "target_date": _future_date(180),
        })

    def test_markdown_has_required_sections_and_legal_disclaimer(self):
        plan = self._make_plan()
        md = plugin.render_markdown(plan)
        for section in (
            "# Certification Path Plan",
            "## Summary",
            "## Applicable Citations",
            "## Milestones",
            "## Capacity assessment",
        ):
            self.assertIn(section, md)
        self.assertIn(
            "This certification path plan is informational.", md,
        )
        self.assertIn("qualified auditor or notified body", md)

    def test_markdown_no_em_dashes(self):
        plan = self._make_plan()
        md = plugin.render_markdown(plan)
        self.assertNotIn("\u2014", md)

    def test_csv_row_count_matches_milestone_count(self):
        plan = self._make_plan()
        csv_text = plugin.render_csv(plan)
        rows = list(csv.reader(io.StringIO(csv_text)))
        self.assertGreater(len(rows), 1)
        # Row count = header + one-per-milestone.
        self.assertEqual(len(rows) - 1, len(plan["milestones"]))


# ---------------------------------------------------------------------------
# Crosswalk enrichment
# ---------------------------------------------------------------------------


class CrosswalkEnrichmentTests(unittest.TestCase):
    def test_crosswalk_enabled_by_default(self):
        snapshot = _readiness_snapshot(remediations=[_remediation("missing-soa")])
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(120),
        })
        self.assertIn("cross_framework_citations", plan)
        self.assertTrue(plan["cross_framework_citations"])

    def test_crosswalk_disabled(self):
        snapshot = _readiness_snapshot(remediations=[_remediation("missing-soa")])
        plan = plugin.plan_certification_path({
            "current_readiness_ref": snapshot,
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(120),
            "enrich_with_crosswalk": False,
        })
        self.assertNotIn("cross_framework_citations", plan)

    def test_graceful_crosswalk_failure(self):
        # Monkeypatch the loader to simulate failure.
        original = plugin._load_crosswalk_module
        plugin._load_crosswalk_module = lambda: (_ for _ in ()).throw(
            ImportError("simulated failure")
        )
        try:
            snapshot = _readiness_snapshot(remediations=[_remediation("missing-soa")])
            plan = plugin.plan_certification_path({
                "current_readiness_ref": snapshot,
                "target_certification": "iso42001-stage1",
                "target_date": _future_date(120),
            })
            # Enrichment still returns hard-coded values, but a warning is
            # present about the fallback.
            self.assertIn("cross_framework_citations", plan)
            self.assertTrue(any(
                "Crosswalk plugin unavailable" in w for w in plan["warnings"]
            ))
        finally:
            plugin._load_crosswalk_module = original


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class ValidationErrorTests(unittest.TestCase):
    def test_missing_required_fields_raises(self):
        with self.assertRaises(ValueError):
            plugin.plan_certification_path({})

    def test_missing_current_readiness_ref_raises(self):
        with self.assertRaises(ValueError):
            plugin.plan_certification_path({
                "target_certification": "iso42001-stage1",
                "target_date": _future_date(60),
            })

    def test_invalid_target_certification_raises(self):
        with self.assertRaises(ValueError):
            plugin.plan_certification_path({
                "current_readiness_ref": _readiness_snapshot(),
                "target_certification": "bogus-target",
                "target_date": _future_date(60),
            })

    def test_invalid_target_date_raises(self):
        with self.assertRaises(ValueError):
            plugin.plan_certification_path({
                "current_readiness_ref": _readiness_snapshot(),
                "target_certification": "iso42001-stage1",
                "target_date": "not-a-date",
            })

    def test_invalid_capacity_type_raises(self):
        with self.assertRaises(ValueError):
            plugin.plan_certification_path({
                "current_readiness_ref": _readiness_snapshot(),
                "target_certification": "iso42001-stage1",
                "target_date": _future_date(60),
                "organization_capacity": {"weekly_hours_available": "forty"},
            })

    def test_invalid_interval_raises(self):
        with self.assertRaises(ValueError):
            plugin.plan_certification_path({
                "current_readiness_ref": _readiness_snapshot(),
                "target_certification": "iso42001-stage1",
                "target_date": _future_date(60),
                "minimum_milestone_interval_weeks": 0,
            })


# ---------------------------------------------------------------------------
# File-path readiness ref
# ---------------------------------------------------------------------------


class FilePathReadinessTests(unittest.TestCase):
    def test_readiness_loaded_from_json_file(self):
        snapshot = _readiness_snapshot(
            remediations=[_remediation("missing-soa")],
            bundle_id="bundle-from-disk",
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
        ) as fh:
            json.dump(snapshot, fh)
            tmp_path = fh.name
        try:
            plan = plugin.plan_certification_path({
                "current_readiness_ref": tmp_path,
                "target_certification": "iso42001-stage1",
                "target_date": _future_date(120),
            })
            self.assertEqual(plan["current_readiness_snapshot_ref"], "bundle-from-disk")
            self.assertEqual(plan["summary"]["remediation_count"], 1)
        finally:
            Path(tmp_path).unlink()

    def test_missing_readiness_path_emits_warning(self):
        plan = plugin.plan_certification_path({
            "current_readiness_ref": "/nonexistent/path/readiness.json",
            "target_certification": "iso42001-stage1",
            "target_date": _future_date(120),
        })
        self.assertTrue(any(
            "does not exist" in w for w in plan["warnings"]
        ))


if __name__ == "__main__":
    unittest.main()
