"""Tests for crosswalk-matrix-builder plugin.

Pytest-compatible and standalone-runnable.
"""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

# Make the plugin directory importable whether invoked standalone or by
# pytest. Matches the pattern used by sibling plugins.
PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

import yaml  # noqa: E402

import plugin  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers for synthetic data invariant tests
# ---------------------------------------------------------------------------


def _write_frameworks(tmp: Path) -> None:
    (tmp / "frameworks.yaml").write_text(
        yaml.safe_dump(
            {
                "frameworks": [
                    {
                        "id": "iso42001",
                        "name": "ISO/IEC 42001:2023",
                        "citation_format": "ISO/IEC 42001:2023, Clause X.X.X",
                    },
                    {
                        "id": "nist-ai-rmf",
                        "name": "NIST AI Risk Management Framework 1.0",
                        "citation_format": "<FUNCTION> <Subcategory>",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def _valid_entry(overrides: dict | None = None) -> dict:
    entry = {
        "id": "iso42001--a-2-2--nist-ai-rmf--govern-1-1",
        "source_framework": "iso42001",
        "source_ref": "A.2.2",
        "source_title": "Policies for AI",
        "target_framework": "nist-ai-rmf",
        "target_ref": "GOVERN 1.1",
        "target_title": "Legal requirements",
        "relationship": "exact-match",
        "confidence": "high",
        "citation_sources": [{"publication": "NIST AI 600-1 Appendix A"}],
        "bidirectional": True,
    }
    if overrides:
        entry.update(overrides)
    return entry


def _write_mappings(tmp: Path, mappings: list[dict], file_name: str = "m.yaml") -> Path:
    path = tmp / file_name
    path.write_text(yaml.safe_dump({"mappings": mappings}), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Happy path: real data loads
# ---------------------------------------------------------------------------


class TestLoadRealData(unittest.TestCase):
    def test_load_crosswalk_data_succeeds(self):
        data = plugin.load_crosswalk_data()
        self.assertIn("frameworks", data)
        self.assertIn("mappings", data)
        self.assertGreater(len(data["frameworks"]), 0)
        self.assertGreater(len(data["mappings"]), 0)


# ---------------------------------------------------------------------------
# Invariants 1-7 (each raises ValueError)
# ---------------------------------------------------------------------------


class TestInvariants(unittest.TestCase):
    def test_invariant_1_framework_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            _write_frameworks(tmp)
            bad = _valid_entry({"source_framework": "unknown-framework"})
            _write_mappings(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_crosswalk_data(data_dir=tmp)
            self.assertIn("Unknown source_framework", str(cm.exception))

    def test_invariant_2_unique_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            _write_frameworks(tmp)
            e1 = _valid_entry()
            e2 = _valid_entry()  # same id
            _write_mappings(tmp, [e1], "a.yaml")
            _write_mappings(tmp, [e2], "b.yaml")
            with self.assertRaises(ValueError) as cm:
                plugin.load_crosswalk_data(data_dir=tmp)
            self.assertIn("Duplicate mapping id", str(cm.exception))

    def test_invariant_3_low_confidence_needs_citation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            _write_frameworks(tmp)
            bad = _valid_entry(
                {
                    "confidence": "low",
                    "citation_sources": [{"publication": ""}],
                    "notes": "",
                }
            )
            _write_mappings(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_crosswalk_data(data_dir=tmp)
            self.assertIn("Low-confidence", str(cm.exception))

    def test_invariant_4_bidirectional_only_on_symmetric(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            _write_frameworks(tmp)
            bad = _valid_entry(
                {"relationship": "satisfies", "bidirectional": True}
            )
            _write_mappings(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_crosswalk_data(data_dir=tmp)
            self.assertIn("bidirectional", str(cm.exception))

    def test_invariant_5_no_mapping_needs_notes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            _write_frameworks(tmp)
            bad = _valid_entry(
                {
                    "relationship": "no-mapping",
                    "target_ref": "",
                    "bidirectional": False,
                    "notes": "",
                }
            )
            _write_mappings(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_crosswalk_data(data_dir=tmp)
            self.assertIn("no-mapping", str(cm.exception))

    def test_invariant_6_citation_required(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            _write_frameworks(tmp)
            bad = _valid_entry({"citation_sources": []})
            _write_mappings(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_crosswalk_data(data_dir=tmp)
            self.assertIn("citation_sources", str(cm.exception))

    def test_invariant_7_no_em_dash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            _write_frameworks(tmp)
            bad = _valid_entry({"notes": "This has an em\u2014dash in it."})
            _write_mappings(tmp, [bad])
            with self.assertRaises(ValueError) as cm:
                plugin.load_crosswalk_data(data_dir=tmp)
            self.assertIn("Em-dash", str(cm.exception))


# ---------------------------------------------------------------------------
# Query behavior on real data
# ---------------------------------------------------------------------------


class TestQueries(unittest.TestCase):
    def test_query_coverage_returns_iso_a_6_2_4_mappings(self):
        result = plugin.build_matrix(
            {
                "query_type": "coverage",
                "source_framework": "iso42001",
                "source_ref": "A.6.2.4",
            }
        )
        # At least the 3 NIST AI RMF subcategory matches exist.
        self.assertGreaterEqual(len(result["matches"]), 3)
        # Summary groups by target framework.
        self.assertIn("by_target_framework", result["summary"])
        self.assertIn("nist-ai-rmf", result["summary"]["by_target_framework"])
        self.assertGreaterEqual(
            result["summary"]["by_target_framework"]["nist-ai-rmf"], 3
        )

    def test_query_gaps_iso_to_nist(self):
        result = plugin.build_matrix(
            {
                "query_type": "gaps",
                "source_framework": "iso42001",
                "target_framework": "nist-ai-rmf",
            }
        )
        self.assertEqual(len(result["gaps"]), 6)
        for gap in result["gaps"]:
            self.assertEqual(gap["relationship"], "no-mapping")
            self.assertEqual(gap["target_ref"], "")
        self.assertEqual(result["summary"]["gap_count"], 6)

    def test_query_matrix_iso_to_eu_ai_act(self):
        # The EU AI Act file contains 90 entries total across both
        # directions. A directional matrix query for eu-ai-act -> iso42001
        # returns 80; the reverse direction (iso42001 -> eu-ai-act) holds
        # the remaining 10 (8 original plus 2 Clause 9.2 mappings added
        # by the internal-audit-planner plugin). Combined count = 90.
        forward = plugin.build_matrix(
            {
                "query_type": "matrix",
                "source_framework": "eu-ai-act",
                "target_framework": "iso42001",
            }
        )
        reverse = plugin.build_matrix(
            {
                "query_type": "matrix",
                "source_framework": "iso42001",
                "target_framework": "eu-ai-act",
            }
        )
        self.assertEqual(len(forward["matrix"]) + len(reverse["matrix"]), 90)
        self.assertIn("by_relationship", forward["summary"])
        # Across both directions the file carries 23 no-mapping entries.
        total_gaps = forward["summary"]["by_relationship"].get(
            "no-mapping", 0
        ) + reverse["summary"]["by_relationship"].get("no-mapping", 0)
        self.assertEqual(total_gaps, 23)

    def test_query_pair_specific_mapping(self):
        result = plugin.build_matrix(
            {
                "query_type": "pair",
                "source_framework": "iso42001",
                "source_ref": "A.2.2",
                "target_framework": "nist-ai-rmf",
                "target_ref": "GOVERN 1.1",
            }
        )
        self.assertEqual(len(result["pair"]), 1)
        self.assertEqual(
            result["pair"][0]["id"],
            "iso42001--a-2-2--nist-ai-rmf--govern-1-1",
        )


# ---------------------------------------------------------------------------
# Validation errors on build_matrix inputs
# ---------------------------------------------------------------------------


class TestInputValidation(unittest.TestCase):
    def test_missing_query_type_raises(self):
        with self.assertRaises(ValueError):
            plugin.build_matrix({})

    def test_invalid_query_type_raises(self):
        with self.assertRaises(ValueError):
            plugin.build_matrix({"query_type": "nonsense"})

    def test_invalid_framework_id_raises(self):
        with self.assertRaises(ValueError):
            plugin.build_matrix(
                {
                    "query_type": "coverage",
                    "source_framework": "not-a-real-framework",
                    "source_ref": "A.2.2",
                }
            )

    def test_invalid_relationship_filter_raises(self):
        with self.assertRaises(ValueError):
            plugin.build_matrix(
                {
                    "query_type": "matrix",
                    "source_framework": "iso42001",
                    "relationship_filter": ["not-a-relationship"],
                }
            )


# ---------------------------------------------------------------------------
# Filter behavior
# ---------------------------------------------------------------------------


class TestFilters(unittest.TestCase):
    def test_confidence_filter_applies(self):
        result = plugin.build_matrix(
            {
                "query_type": "matrix",
                "source_framework": "iso42001",
                "target_framework": "nist-ai-rmf",
                "confidence_min": "high",
            }
        )
        for m in result["matrix"]:
            self.assertEqual(m["confidence"], "high")

    def test_relationship_filter_applies(self):
        result = plugin.build_matrix(
            {
                "query_type": "matrix",
                "source_framework": "colorado-sb-205",
                "relationship_filter": ["satisfies", "partial-satisfaction"],
            }
        )
        self.assertGreater(len(result["matrix"]), 0)
        for m in result["matrix"]:
            self.assertIn(m["relationship"], ("satisfies", "partial-satisfaction"))

    def test_empty_result_emits_warning(self):
        result = plugin.build_matrix(
            {
                "query_type": "coverage",
                "source_framework": "iso42001",
                "source_ref": "Z.99.99",
            }
        )
        self.assertEqual(result["matches"], [])
        self.assertTrue(
            any("zero mappings" in w for w in result["warnings"]),
            msg=f"warnings: {result['warnings']}",
        )


# ---------------------------------------------------------------------------
# Output contract and rendering
# ---------------------------------------------------------------------------


class TestOutputContract(unittest.TestCase):
    def test_output_has_required_fields(self):
        result = plugin.build_matrix(
            {
                "query_type": "coverage",
                "source_framework": "iso42001",
                "source_ref": "A.6.2.4",
                "reviewed_by": "J. Doe",
            }
        )
        for field in ("timestamp", "agent_signature", "citations", "warnings", "summary"):
            self.assertIn(field, result, msg=f"missing field {field}")
        self.assertTrue(result["timestamp"].endswith("Z"))
        self.assertEqual(result["agent_signature"], plugin.AGENT_SIGNATURE)
        self.assertEqual(result["reviewed_by"], "J. Doe")


class TestRendering(unittest.TestCase):
    def test_render_markdown_has_required_sections(self):
        result = plugin.build_matrix(
            {
                "query_type": "coverage",
                "source_framework": "iso42001",
                "source_ref": "A.6.2.4",
            }
        )
        md = plugin.render_markdown(result)
        self.assertIn("# Crosswalk matrix result", md)
        self.assertIn("## Query", md)
        self.assertIn("## Summary", md)
        self.assertIn("## Mappings", md)
        self.assertIn("query_type: coverage", md)
        # Mappings table has a header row.
        self.assertIn("| id |", md)

    def test_render_csv_header_and_row_count(self):
        result = plugin.build_matrix(
            {
                "query_type": "matrix",
                "source_framework": "eu-ai-act",
                "target_framework": "iso42001",
            }
        )
        csv_text = plugin.render_csv(result)
        lines = [line for line in csv_text.splitlines() if line.strip()]
        # Header + one row per mapping.
        self.assertEqual(lines[0].split(",")[0], "id")
        self.assertEqual(len(lines) - 1, len(result["matrix"]))

    def test_render_no_em_dash(self):
        result = plugin.build_matrix(
            {
                "query_type": "matrix",
                "source_framework": "iso42001",
                "target_framework": "nist-ai-rmf",
            }
        )
        md = plugin.render_markdown(result)
        csv_text = plugin.render_csv(result)
        self.assertNotIn("\u2014", md)
        self.assertNotIn("\u2014", csv_text)


# ---------------------------------------------------------------------------
# Statutory-presumption support
# ---------------------------------------------------------------------------


class TestStatutoryPresumption(unittest.TestCase):
    def test_statutory_presumption_relationship_supported(self):
        result = plugin.build_matrix(
            {
                "query_type": "matrix",
                "source_framework": "colorado-sb-205",
                "relationship_filter": ["statutory-presumption"],
            }
        )
        # Colorado has 4 statutory-presumption entries (C16 / C17 pairs
        # against ISO and NIST).
        self.assertEqual(len(result["matrix"]), 4)
        for m in result["matrix"]:
            self.assertEqual(m["relationship"], "statutory-presumption")
        self.assertEqual(
            result["summary"]["by_relationship"].get("statutory-presumption"), 4
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
