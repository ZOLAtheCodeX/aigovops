"""Tests for cascade-impact-analyzer plugin.

Pytest-compatible and standalone-runnable.
"""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

# Make the plugin directory importable.
PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

import yaml  # noqa: E402

import plugin  # noqa: E402


# ---------------------------------------------------------------------------
# Synthetic-data helpers
# ---------------------------------------------------------------------------


def _minimal_cascade(overrides: dict | None = None) -> dict:
    c = {
        "id": "test.cascade",
        "trigger": {
            "event": "test.cascade",
            "source_plugin": "risk-register-builder",
        },
        "description": "test",
        "priority": "medium",
        "actions": [
            {
                "action_type": "re-run-plugin",
                "target_plugin": "soa-generator",
                "rationale": "test",
                "authority": "take-resolving-action",
                "max_hops_further": 2,
                "citations": ["ISO/IEC 42001:2023, Clause 6.1.3"],
            }
        ],
        "citations": ["ISO/IEC 42001:2023, Clause 6.1.2"],
    }
    if overrides:
        c.update(overrides)
    return c


def _write_schema(tmp: Path, cascades: list[dict]) -> None:
    (tmp / "cascade_schema.yaml").write_text(
        yaml.safe_dump({"cascades": cascades}), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


class TestModuleConstants(unittest.TestCase):
    def test_agent_signature(self):
        self.assertEqual(plugin.AGENT_SIGNATURE, "cascade-impact-analyzer/0.1.0")

    def test_required_input_fields(self):
        self.assertEqual(plugin.REQUIRED_INPUT_FIELDS, ("trigger_event",))

    def test_valid_severities(self):
        self.assertEqual(
            plugin.VALID_EVENT_SEVERITIES, ("info", "warning", "critical")
        )

    def test_default_max_depth(self):
        self.assertEqual(plugin.DEFAULT_MAX_DEPTH, 5)


# ---------------------------------------------------------------------------
# Real-data load
# ---------------------------------------------------------------------------


class TestLoadRealSchema(unittest.TestCase):
    def test_load_succeeds(self):
        reg = plugin.load_cascade_schema()
        self.assertIn("cascades", reg)
        self.assertIn("by_event", reg)
        self.assertGreaterEqual(len(reg["cascades"]), 20)

    def test_every_seeded_event_matches(self):
        reg = plugin.load_cascade_schema()
        # Each cascade's trigger event must resolve via analyze_cascade to
        # that cascade and return a non-empty flat_action_list.
        for cascade in reg["cascades"]:
            event = cascade["trigger"]["event"]
            result = plugin.analyze_cascade({"trigger_event": {"event": event}})
            self.assertEqual(
                result["matched_cascades"],
                [cascade["id"]],
                f"event {event} did not match its seeded cascade",
            )
            self.assertGreater(
                len(result["flat_action_list"]),
                0,
                f"event {event} produced empty flat_action_list",
            )


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------


class TestInvariants(unittest.TestCase):
    def test_unknown_target_plugin_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bad = _minimal_cascade()
            bad["actions"][0]["target_plugin"] = "not-a-real-plugin"
            _write_schema(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_cascade_schema(data_dir=tmp)
            self.assertIn("not in the AIGovOps catalogue", str(cm.exception))

    def test_invalid_authority_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bad = _minimal_cascade()
            bad["actions"][0]["authority"] = "delegate"
            _write_schema(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_cascade_schema(data_dir=tmp)
            self.assertIn("invalid authority", str(cm.exception))

    def test_invalid_priority_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bad = _minimal_cascade({"priority": "urgent"})
            _write_schema(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_cascade_schema(data_dir=tmp)
            self.assertIn("invalid priority", str(cm.exception))

    def test_duplicate_id_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            a = _minimal_cascade()
            b = _minimal_cascade()
            b["trigger"] = {
                "event": "other.event",
                "source_plugin": "risk-register-builder",
            }
            _write_schema(tmp, [a, b])
            with self.assertRaises(ValueError) as cm:
                plugin.load_cascade_schema(data_dir=tmp)
            self.assertIn("Duplicate cascade id", str(cm.exception))

    def test_duplicate_event_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            a = _minimal_cascade()
            b = _minimal_cascade({"id": "test.other"})
            _write_schema(tmp, [a, b])
            with self.assertRaises(ValueError) as cm:
                plugin.load_cascade_schema(data_dir=tmp)
            self.assertIn("duplicates trigger event", str(cm.exception))

    def test_missing_citation_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bad = _minimal_cascade()
            bad["actions"][0]["citations"] = []
            _write_schema(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_cascade_schema(data_dir=tmp)
            self.assertIn("at least one citation", str(cm.exception))

    def test_bad_citation_prefix_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bad = _minimal_cascade()
            bad["actions"][0]["citations"] = ["Some invented framework, Rule 1"]
            _write_schema(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_cascade_schema(data_dir=tmp)
            self.assertIn("does not", str(cm.exception))

    def test_em_dash_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bad = _minimal_cascade()
            bad["description"] = "bad \u2014 dash"
            _write_schema(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_cascade_schema(data_dir=tmp)
            self.assertIn("Em-dash", str(cm.exception))

    def test_negative_max_hops_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bad = _minimal_cascade()
            bad["actions"][0]["max_hops_further"] = -1
            _write_schema(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_cascade_schema(data_dir=tmp)
            self.assertIn("non-negative", str(cm.exception))

    def test_self_cycle_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bad = _minimal_cascade()
            # source_plugin == target_plugin creates a self-cycle.
            bad["trigger"]["source_plugin"] = "soa-generator"
            _write_schema(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_cascade_schema(data_dir=tmp)
            self.assertIn("Self-cycle", str(cm.exception))


# ---------------------------------------------------------------------------
# analyze_cascade behavior
# ---------------------------------------------------------------------------


class TestAnalyzeCascade(unittest.TestCase):
    def test_missing_trigger_event_raises(self):
        with self.assertRaises(ValueError):
            plugin.analyze_cascade({})

    def test_non_dict_inputs_raises(self):
        with self.assertRaises(ValueError):
            plugin.analyze_cascade("not a dict")  # type: ignore[arg-type]

    def test_non_dict_trigger_event_raises(self):
        with self.assertRaises(ValueError):
            plugin.analyze_cascade({"trigger_event": "oops"})

    def test_missing_event_id_raises(self):
        with self.assertRaises(ValueError):
            plugin.analyze_cascade({"trigger_event": {}})

    def test_invalid_severity_raises(self):
        with self.assertRaises(ValueError):
            plugin.analyze_cascade(
                {
                    "trigger_event": {"event": "framework-monitor.change-detected"},
                    "severity": "emergency",
                }
            )

    def test_invalid_max_depth_raises(self):
        with self.assertRaises(ValueError):
            plugin.analyze_cascade(
                {
                    "trigger_event": {"event": "framework-monitor.change-detected"},
                    "max_depth": -1,
                }
            )

    def test_invalid_authority_filter_raises(self):
        with self.assertRaises(ValueError):
            plugin.analyze_cascade(
                {
                    "trigger_event": {"event": "framework-monitor.change-detected"},
                    "authority_filter": ["delegate"],
                }
            )

    def test_unmatched_trigger_returns_warning(self):
        result = plugin.analyze_cascade(
            {"trigger_event": {"event": "no.such.event"}}
        )
        self.assertEqual(result["matched_cascades"], [])
        self.assertEqual(result["flat_action_list"], [])
        self.assertEqual(result["cascade_tree"], [])
        self.assertTrue(
            any("No cascade defined" in w for w in result["warnings"])
        )

    def test_risk_register_risk_added_fans_out_three(self):
        result = plugin.analyze_cascade(
            {"trigger_event": {"event": "risk-register.risk-added"}}
        )
        # Hop-0 fan-out is three direct actions from the cascade.
        hop_zero = [a for a in result["flat_action_list"] if a["hop_count"] == 0]
        self.assertEqual(len(hop_zero), 3)
        targets = {a["target_plugin"] for a in hop_zero}
        self.assertEqual(
            targets,
            {"soa-generator", "gap-assessment", "certification-readiness"},
        )

    def test_high_risk_annex_iii_hits_aisia_at_hop_one_or_zero(self):
        result = plugin.analyze_cascade(
            {"trigger_event": {"event": "high-risk-classifier.eu-annex-iii-match"}}
        )
        aisia_nodes = [
            a for a in result["flat_action_list"]
            if a["target_plugin"] == "aisia-runner"
        ]
        self.assertGreater(len(aisia_nodes), 0)
        self.assertEqual(aisia_nodes[0]["hop_count"], 0)

    def test_flat_list_respects_priority_ordering(self):
        # risk-register.residual-score-exceeds-threshold is priority=high.
        # All its actions should appear before any low-priority action.
        result = plugin.analyze_cascade(
            {
                "trigger_event": {
                    "event": "risk-register.residual-score-exceeds-threshold"
                }
            }
        )
        priorities = [a.get("priority") for a in result["flat_action_list"]]
        # Within a single cascade run, priorities should be non-decreasing.
        weights = [plugin._PRIORITY_WEIGHT[p] for p in priorities]
        self.assertEqual(weights, sorted(weights))

    def test_authority_filter_drops_nodes(self):
        unfiltered = plugin.analyze_cascade(
            {"trigger_event": {"event": "incident-reporting.serious-incident"}}
        )
        self.assertGreater(unfiltered["summary"]["total_actions"], 0)
        filtered = plugin.analyze_cascade(
            {
                "trigger_event": {"event": "incident-reporting.serious-incident"},
                "authority_filter": ["take-resolving-action"],
            }
        )
        # All seeded incident-reporting.serious-incident actions are
        # ask-permission, so the filter collapses the result.
        self.assertEqual(filtered["summary"]["total_actions"], 0)
        self.assertTrue(any("authority_filter" in w for w in filtered["warnings"]))

    def test_max_depth_zero_returns_no_actions(self):
        result = plugin.analyze_cascade(
            {
                "trigger_event": {"event": "ai-system-inventory.system-added"},
                "max_depth": 0,
            }
        )
        # max_depth=0 still returns the root actions (hop 0) but no children.
        self.assertGreater(len(result["flat_action_list"]), 0)
        max_hop = max(a["hop_count"] for a in result["flat_action_list"])
        self.assertEqual(max_hop, 0)

    def test_summary_counts_match_flat_list(self):
        result = plugin.analyze_cascade(
            {"trigger_event": {"event": "metrics-collector.threshold-breach"}}
        )
        total = sum(result["summary"]["by_target_plugin"].values())
        self.assertEqual(total, result["summary"]["total_actions"])
        total2 = sum(result["summary"]["by_authority"].values())
        self.assertEqual(total2, result["summary"]["total_actions"])

    def test_citations_aggregated_and_unique(self):
        result = plugin.analyze_cascade(
            {"trigger_event": {"event": "ai-system-inventory.system-added"}}
        )
        self.assertGreater(len(result["citations"]), 0)
        self.assertEqual(len(result["citations"]), len(set(result["citations"])))

    def test_output_contains_required_top_level_fields(self):
        result = plugin.analyze_cascade(
            {"trigger_event": {"event": "framework-monitor.change-detected"}}
        )
        for field in (
            "timestamp",
            "agent_signature",
            "trigger",
            "matched_cascades",
            "cascade_tree",
            "flat_action_list",
            "summary",
            "citations",
            "warnings",
        ):
            self.assertIn(field, result)
        self.assertEqual(
            result["agent_signature"], "cascade-impact-analyzer/0.1.0"
        )


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


class TestRenderMarkdown(unittest.TestCase):
    def _sample(self) -> dict:
        return plugin.analyze_cascade(
            {"trigger_event": {"event": "risk-register.risk-added"}}
        )

    def test_markdown_has_all_sections(self):
        md = plugin.render_markdown(self._sample())
        for section in (
            "# Cascade impact analysis",
            "## Trigger",
            "## Summary",
            "## Citations",
            "## Cascade tree",
            "## Flat action list",
        ):
            self.assertIn(section, md)

    def test_markdown_no_em_dash(self):
        md = plugin.render_markdown(self._sample())
        self.assertNotIn("\u2014", md)

    def test_markdown_missing_fields_raises(self):
        with self.assertRaises(ValueError):
            plugin.render_markdown({"timestamp": "x"})


class TestRenderCSV(unittest.TestCase):
    def test_csv_row_count_matches_flat_list(self):
        result = plugin.analyze_cascade(
            {"trigger_event": {"event": "ai-system-inventory.system-added"}}
        )
        csv_text = plugin.render_csv(result)
        lines = [ln for ln in csv_text.splitlines() if ln.strip()]
        # header + N rows
        self.assertEqual(len(lines), 1 + len(result["flat_action_list"]))

    def test_csv_no_em_dash(self):
        result = plugin.analyze_cascade(
            {"trigger_event": {"event": "ai-system-inventory.system-added"}}
        )
        csv_text = plugin.render_csv(result)
        self.assertNotIn("\u2014", csv_text)

    def test_csv_header_fields(self):
        result = plugin.analyze_cascade(
            {"trigger_event": {"event": "framework-monitor.change-detected"}}
        )
        csv_text = plugin.render_csv(result)
        header = csv_text.splitlines()[0]
        for col in (
            "cascade_id",
            "priority",
            "hop_count",
            "target_plugin",
            "action_type",
            "authority",
            "rationale",
            "citations",
        ):
            self.assertIn(col, header)

    def test_csv_missing_field_raises(self):
        with self.assertRaises(ValueError):
            plugin.render_csv({"timestamp": "x"})


# ---------------------------------------------------------------------------
# Seeded-count sanity
# ---------------------------------------------------------------------------


class TestSeededCascadeCount(unittest.TestCase):
    def test_at_least_twenty_cascades(self):
        reg = plugin.load_cascade_schema()
        self.assertGreaterEqual(len(reg["cascades"]), 20)

    def test_all_target_plugins_in_catalogue(self):
        reg = plugin.load_cascade_schema()
        for cascade in reg["cascades"]:
            for action in cascade["actions"]:
                self.assertIn(
                    action["target_plugin"], plugin.VALID_TARGET_PLUGINS
                )


if __name__ == "__main__":
    unittest.main()
