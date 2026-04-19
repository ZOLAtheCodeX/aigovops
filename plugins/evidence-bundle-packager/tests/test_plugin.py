"""Tests for the evidence-bundle-packager plugin. Runs under pytest or standalone."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_OUTPUTS = REPO_ROOT / "examples" / "demo-scenario" / "outputs"


def _scope() -> dict:
    return {
        "organization": "Acme Health Inc.",
        "aims_boundary": "All AI systems operated by the Acme Health AIMS core team.",
        "systems_in_scope": ["SYS-001", "SYS-002", "SYS-003"],
        "reporting_period_start": "2026-01-01",
        "reporting_period_end": "2026-03-31",
        "intended_recipient": "external-auditor",
    }


def _make_source_dir(tmp: Path) -> Path:
    source = tmp / "source"
    source.mkdir(parents=True, exist_ok=True)
    for f in DEMO_OUTPUTS.iterdir():
        if f.is_file() and f.name != "summary.md":
            shutil.copy2(f, source / f.name)
    return source


def _inputs(tmp: Path, **overrides) -> dict:
    base = {
        "source_dir": str(_make_source_dir(tmp)),
        "scope": _scope(),
        "output_dir": str(tmp / "out"),
        "signing_algorithm": "none",
        "include_source_crosswalk": False,
    }
    base.update(overrides)
    return base


# 1. Happy path: hmac-sha256 signing.
def test_happy_path_hmac_signing():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        os.environ["AIGOVOPS_BUNDLE_SIGNING_KEY"] = "test-key-12345"
        try:
            report = plugin.pack_bundle(_inputs(tmp, signing_algorithm="hmac-sha256"))
        finally:
            os.environ.pop("AIGOVOPS_BUNDLE_SIGNING_KEY", None)
        assert report["signatures"]["algorithm"] == "hmac-sha256"
        assert "manifest_hmac" in report["signatures"]
        assert "artifact_hmacs" in report["signatures"]
        assert report["summary"]["artifact_count"] > 0


# 2. Happy path: signing_algorithm='none'.
def test_happy_path_signing_none():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        report = plugin.pack_bundle(_inputs(tmp, signing_algorithm="none"))
        assert report["signatures"]["algorithm"] == "none"
        assert "manifest_sha256" in report["signatures"]
        assert "manifest_hmac" not in report["signatures"]


# 3. ValueError on missing source_dir.
def test_missing_source_dir_raises():
    try:
        plugin.pack_bundle({"scope": _scope(), "output_dir": "/tmp/x"})
    except ValueError as exc:
        assert "source_dir" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 4. ValueError on missing scope.
def test_missing_scope_raises():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        source = _make_source_dir(tmp)
        try:
            plugin.pack_bundle({"source_dir": str(source), "output_dir": str(tmp / "out")})
        except ValueError as exc:
            assert "scope" in str(exc)
            return
    raise AssertionError("expected ValueError")


# 5. ValueError on missing output_dir.
def test_missing_output_dir_raises():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        source = _make_source_dir(tmp)
        try:
            plugin.pack_bundle({"source_dir": str(source), "scope": _scope()})
        except ValueError as exc:
            assert "output_dir" in str(exc)
            return
    raise AssertionError("expected ValueError")


# 6. ValueError on invalid signing_algorithm.
def test_invalid_signing_algorithm_raises():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        try:
            plugin.pack_bundle(_inputs(tmp, signing_algorithm="rsa-pss"))
        except ValueError as exc:
            assert "signing_algorithm" in str(exc)
            return
    raise AssertionError("expected ValueError")


# 7. ValueError on invalid intended_recipient.
def test_invalid_intended_recipient_raises():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        scope = _scope()
        scope["intended_recipient"] = "the-public"
        try:
            plugin.pack_bundle(_inputs(tmp, scope=scope))
        except ValueError as exc:
            assert "intended_recipient" in str(exc)
            return
    raise AssertionError("expected ValueError")


# 8. Warning emitted when HMAC key env var absent; downgraded to none.
def test_hmac_key_missing_downgrades_to_none():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        os.environ.pop("AIGOVOPS_BUNDLE_SIGNING_KEY", None)
        report = plugin.pack_bundle(_inputs(tmp, signing_algorithm="hmac-sha256"))
        assert report["signatures"]["algorithm"] == "none"
        assert any("not set" in w for w in report["warnings"])


# 9. MANIFEST includes every plugin file from source_dir.
def test_manifest_includes_every_file():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        source = _make_source_dir(tmp)
        report = plugin.pack_bundle(_inputs(tmp))
        # Count source files that the plugin would include (json/md/csv, no summary.md).
        source_files = [
            f for f in source.iterdir()
            if f.is_file() and f.suffix.lower() in (".json", ".md", ".csv")
            and f.name != "summary.md"
        ]
        assert report["summary"]["artifact_count"] == len(source_files)


# 10. MANIFEST's sha256 values match actual file hashes.
def test_manifest_sha256_matches_file_hashes():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        report = plugin.pack_bundle(_inputs(tmp))
        bundle_dir = Path(report["bundle_path"])
        import hashlib
        for entry in report["manifest"]["artifacts"]:
            abs_path = bundle_dir / entry["path"]
            h = hashlib.sha256(abs_path.read_bytes()).hexdigest()
            assert h == entry["sha256"], f"mismatch on {entry['path']}"


# 11. citation-summary.md enumerates unique citations (no duplicates).
def test_citation_summary_deduplicates():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        report = plugin.pack_bundle(_inputs(tmp))
        bundle_dir = Path(report["bundle_path"])
        text = (bundle_dir / "citation-summary.md").read_text(encoding="utf-8")
        # Flatten all citations and ensure uniqueness within each framework.
        for framework, entries in report["citation_groups"].items():
            assert len(entries) == len(set(entries)), (
                f"duplicate citations in framework {framework}"
            )
        assert "## Citations by framework" in text
        assert "## Coverage of primary instruments" in text


# 12. provenance-chain includes inventory-to-risk-register edge when both present.
def test_provenance_includes_inventory_to_risk_register_edge():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        source = _make_source_dir(tmp)
        # Add a fake ai-system-inventory file so both endpoints exist.
        (source / "ai-system-inventory.json").write_text(
            json.dumps({
                "timestamp": "2026-04-18T00:00:00Z",
                "agent_signature": "ai-system-inventory-maintainer/0.1.0",
                "citations": ["ISO/IEC 42001:2023, Clause 4.3"],
                "systems": [],
            }),
            encoding="utf-8",
        )
        report = plugin.pack_bundle(_inputs(tmp))
        edges = report["provenance"]["edges"]
        found = any(
            e["from"] == "ai-system-inventory-maintainer"
            and e["to"] == "risk-register-builder"
            for e in edges
        )
        assert found, f"expected inventory->risk-register edge; got {edges}"


# 13. signatures.json present with correct shape.
def test_signatures_file_shape():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        os.environ["AIGOVOPS_BUNDLE_SIGNING_KEY"] = "sig-test"
        try:
            report = plugin.pack_bundle(_inputs(tmp, signing_algorithm="hmac-sha256"))
        finally:
            os.environ.pop("AIGOVOPS_BUNDLE_SIGNING_KEY", None)
        bundle_dir = Path(report["bundle_path"])
        sig = json.loads((bundle_dir / "signatures.json").read_text(encoding="utf-8"))
        assert sig["algorithm"] == "hmac-sha256"
        assert "manifest_sha256" in sig
        assert "manifest_hmac" in sig
        assert "artifact_hmacs" in sig
        assert sig["key_id"] == "env:AIGOVOPS_BUNDLE_SIGNING_KEY"


# 14. verify_bundle returns 'verified' when bundle is untampered.
def test_verify_verified():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        os.environ["AIGOVOPS_BUNDLE_SIGNING_KEY"] = "verify-test"
        try:
            report = plugin.pack_bundle(_inputs(tmp, signing_algorithm="hmac-sha256"))
            findings = plugin.verify_bundle(report["bundle_path"])
        finally:
            os.environ.pop("AIGOVOPS_BUNDLE_SIGNING_KEY", None)
        assert findings["overall"] == "verified", findings


# 15. verify_bundle returns signature-mismatch when an artifact is mutated post-pack.
def test_verify_signature_mismatch_on_mutation():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        os.environ["AIGOVOPS_BUNDLE_SIGNING_KEY"] = "verify-mutate"
        try:
            report = plugin.pack_bundle(_inputs(tmp, signing_algorithm="hmac-sha256"))
            bundle_dir = Path(report["bundle_path"])
            first_artifact = Path(bundle_dir) / report["manifest"]["artifacts"][0]["path"]
            first_artifact.write_text(
                first_artifact.read_text(encoding="utf-8") + "\nTAMPERED\n",
                encoding="utf-8",
            )
            findings = plugin.verify_bundle(report["bundle_path"])
        finally:
            os.environ.pop("AIGOVOPS_BUNDLE_SIGNING_KEY", None)
        assert findings["overall"] == "signature-mismatch", findings
        assert len(findings["mutated_artifacts"]) >= 1


# 16. verify_bundle returns drift-detected when an artifact is deleted post-pack.
def test_verify_drift_on_delete():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        os.environ["AIGOVOPS_BUNDLE_SIGNING_KEY"] = "verify-delete"
        try:
            report = plugin.pack_bundle(_inputs(tmp, signing_algorithm="hmac-sha256"))
            bundle_dir = Path(report["bundle_path"])
            first_artifact = Path(bundle_dir) / report["manifest"]["artifacts"][0]["path"]
            first_artifact.unlink()
            findings = plugin.verify_bundle(report["bundle_path"])
        finally:
            os.environ.pop("AIGOVOPS_BUNDLE_SIGNING_KEY", None)
        assert findings["overall"] == "drift-detected", findings
        assert len(findings["missing_artifacts"]) >= 1


# 17. inspect_bundle returns a quick summary.
def test_inspect_bundle():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        report = plugin.pack_bundle(_inputs(tmp))
        summary = plugin.inspect_bundle(report["bundle_path"])
        assert summary["bundle_id"] == report["bundle_id"]
        assert summary["artifact_count"] == report["summary"]["artifact_count"]
        assert "scope" in summary
        assert "citations_unique_count" in summary
        assert "age_seconds" in summary


# 18. Deterministic bundle content: pack twice, differences only in timestamps.
def test_deterministic_pack():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        os.environ["AIGOVOPS_BUNDLE_SIGNING_KEY"] = "det"
        try:
            inputs1 = _inputs(tmp, bundle_id="fixed-bundle-id-1",
                              signing_algorithm="hmac-sha256")
            report1 = plugin.pack_bundle(inputs1)
            inputs2 = dict(inputs1)
            inputs2["bundle_id"] = "fixed-bundle-id-2"
            inputs2["output_dir"] = str(tmp / "out2")
            # Must re-create the source dir since _inputs did it for the first call.
            inputs2["source_dir"] = inputs1["source_dir"]
            report2 = plugin.pack_bundle(inputs2)
        finally:
            os.environ.pop("AIGOVOPS_BUNDLE_SIGNING_KEY", None)
        # Artifact SHA-256 digests should be identical across packs.
        arts1 = {e["path"].split("/", 1)[1]: e["sha256"]
                 for e in report1["manifest"]["artifacts"]}
        arts2 = {e["path"].split("/", 1)[1]: e["sha256"]
                 for e in report2["manifest"]["artifacts"]}
        assert arts1 == arts2, "artifact hashes should be deterministic"
        # Citation groups identical.
        assert report1["citation_groups"] == report2["citation_groups"]


# 19. include_source_crosswalk=True copies all 9 crosswalk YAML files.
def test_include_source_crosswalk_copies_all():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        report = plugin.pack_bundle(_inputs(tmp, include_source_crosswalk=True))
        bundle_dir = Path(report["bundle_path"])
        crosswalk_dir = bundle_dir / "crosswalk"
        assert crosswalk_dir.is_dir()
        copied = sorted(f.name for f in crosswalk_dir.glob("*.yaml"))
        assert len(copied) == 9, f"expected 9 crosswalk yaml files; got {len(copied)}: {copied}"


# 20. render_markdown has all required sections.
def test_render_markdown_has_all_sections():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        report = plugin.pack_bundle(_inputs(tmp))
        md = plugin.render_markdown(report)
        for section in ("# Bundle overview", "## Scope", "## Artifact list",
                        "## Citation summary", "## Provenance", "## Signatures",
                        "## Warnings"):
            assert section in md, f"missing section {section!r}"


# 21. render_csv has one row per artifact with SHA-256 column.
def test_render_csv_row_per_artifact():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        report = plugin.pack_bundle(_inputs(tmp))
        csv = plugin.render_csv(report)
        lines = csv.strip().splitlines()
        header = lines[0]
        assert "sha256" in header
        # Number of data rows == artifact count.
        assert len(lines) - 1 == report["summary"]["artifact_count"]


# 22. No em-dash, emoji, or hedging in rendered output.
def test_no_prohibited_language_in_output():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        report = plugin.pack_bundle(_inputs(tmp))
        md = plugin.render_markdown(report)
        bundle_dir = Path(report["bundle_path"])
        readme = (bundle_dir / "README.md").read_text(encoding="utf-8")
        cit_summary = (bundle_dir / "citation-summary.md").read_text(encoding="utf-8")
        for text in (md, readme, cit_summary):
            assert "\u2014" not in text, "em-dash found in rendered output"
            for phrase in ("may want to consider", "might be helpful to",
                           "could potentially", "it is possible that"):
                assert phrase not in text.lower(), (
                    f"hedging phrase {phrase!r} found in rendered output"
                )


def _run_all():
    import inspect
    tests = [(n, o) for n, o in inspect.getmembers(sys.modules[__name__])
             if n.startswith("test_") and callable(o)]
    failures = []
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:
            failures.append((name, f"{type(exc).__name__}: {exc}"))
    print(f"Ran {len(tests)} tests: {len(tests) - len(failures)} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
