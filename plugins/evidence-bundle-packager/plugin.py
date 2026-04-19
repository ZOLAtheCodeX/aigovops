"""
AIGovOps: Evidence Bundle Packager Plugin

Takes a directory of plugin-emitted governance artifacts (audit logs, risk
registers, Statements of Applicability, AISIAs, nonconformity records,
management-review packages, metrics reports, and sibling outputs) and
produces a deterministic, optionally-signed evidence bundle. The bundle is
the unit of delivery for ISO/IEC 42001:2023 certification evidence
packages, EU AI Act Annex IV technical-documentation submissions,
regulatory supervisory-authority requests, and internal-audit working
papers.

Design stance: the plugin does NOT invent artifact content. It reads the
artifacts written by upstream plugins as-is, computes cryptographic
digests, copies them into a canonical layout, aggregates citations, infers
provenance edges from well-known upstream-to-downstream consumption
relationships, and optionally HMAC-signs the manifest and per-artifact
digests. Every structural determination is deterministic; every content-
level gap surfaces as a warning in the bundle report.

Public API:
    pack_bundle(inputs)    canonical entry point producing the bundle on disk
    verify_bundle(bundle_dir)   integrity check against manifest + signatures
    inspect_bundle(bundle_dir)  quick summary for CLI pretty-print
    render_markdown(bundle_report)  human-readable bundle overview
    render_csv(bundle_report)       one row per artifact with SHA-256

Status: Phase 3 minimum-viable implementation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import warnings as _warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_SIGNATURE = "evidence-bundle-packager/0.1.0"

BUNDLE_SCHEMA_VERSION = "1.0.0"

REQUIRED_INPUT_FIELDS = ("source_dir", "scope", "output_dir")

VALID_SIGNING_ALGORITHMS = ("hmac-sha256", "none")

VALID_INTENDED_RECIPIENTS = (
    "internal-audit",
    "external-auditor",
    "regulator",
    "stakeholder",
    "sponsor",
)

REQUIRED_SCOPE_FIELDS = (
    "organization",
    "aims_boundary",
    "systems_in_scope",
    "reporting_period_start",
    "reporting_period_end",
    "intended_recipient",
)

# Expected plugin-output file types per plugin, drawn from the catalogue.
# Unknown-plugin files are still included, but flagged in the manifest.
EXPECTED_ARTIFACT_TYPES: dict[str, list[str]] = {
    "audit-log-entry": [".json", ".md"],
    "risk-register": [".json", ".md", ".csv"],
    "role-matrix": [".json", ".md", ".csv"],
    "soa": [".json", ".md", ".csv"],
    "aisia": [".json", ".md"],
    "nonconformity-register": [".json", ".md"],
    "management-review-package": [".json", ".md"],
    "internal-audit-plan": [".json", ".md", ".csv"],
    "metrics-report": [".json", ".md", ".csv"],
    "gap-assessment": [".json", ".md", ".csv"],
    "data-register": [".json", ".md", ".csv"],
    "applicability-check": [".json", ".md"],
    "high-risk-classification": [".json", ".md"],
    "atrs-record": [".json", ".md", ".csv"],
    "colorado-compliance-record": [".json", ".md", ".csv"],
    "nyc-ll144-audit-package": [".json", ".md", ".csv"],
    "crosswalk": [".json", ".md", ".csv"],
    "magf-assessment": [".json", ".md", ".csv"],
    "ai-system-inventory": [".json", ".md", ".csv"],
}

# Map artifact-filename substrings to plugin names. Order matters: more
# specific prefixes come first.
_ARTIFACT_TO_PLUGIN: list[tuple[str, str, str]] = [
    ("ai-system-inventory", "ai-system-inventory-maintainer", "ai-system-inventory"),
    ("audit-log-entry", "audit-log-generator", "audit-log-entry"),
    ("role-matrix", "role-matrix-generator", "role-matrix"),
    ("risk-register", "risk-register-builder", "risk-register"),
    ("soa", "soa-generator", "soa"),
    ("aisia", "aisia-runner", "aisia"),
    ("nonconformity-register", "nonconformity-tracker", "nonconformity-register"),
    ("management-review-package", "management-review-packager", "management-review-package"),
    ("internal-audit-plan", "internal-audit-planner", "internal-audit-plan"),
    ("metrics-report", "metrics-collector", "metrics-report"),
    ("gap-assessment", "gap-assessment", "gap-assessment"),
    ("data-register", "data-register-builder", "data-register"),
    ("applicability-check", "applicability-checker", "applicability-check"),
    ("high-risk-classification", "high-risk-classifier", "high-risk-classification"),
    ("atrs-record", "uk-atrs-recorder", "atrs-record"),
    ("colorado-compliance-record", "colorado-ai-act-compliance", "colorado-compliance-record"),
    ("nyc-ll144-audit-package", "nyc-ll144-audit-packager", "nyc-ll144-audit-package"),
    ("magf-assessment", "singapore-magf-assessor", "magf-assessment"),
    ("crosswalk", "crosswalk-matrix-builder", "crosswalk"),
]

# Known provenance edges: (upstream_plugin, downstream_plugin, via_field).
# Edges emit only when BOTH endpoints have an artifact included in the bundle.
_PROVENANCE_EDGES: list[tuple[str, str, str]] = [
    ("ai-system-inventory-maintainer", "risk-register-builder", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "soa-generator", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "aisia-runner", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "audit-log-generator", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "gap-assessment", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "internal-audit-planner", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "metrics-collector", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "data-register-builder", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "uk-atrs-recorder", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "colorado-ai-act-compliance", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "nyc-ll144-audit-packager", "ai_system_inventory"),
    ("ai-system-inventory-maintainer", "singapore-magf-assessor", "ai_system_inventory"),
    ("risk-register-builder", "soa-generator", "risk_register"),
    ("risk-register-builder", "management-review-packager", "risk_register"),
    ("soa-generator", "management-review-packager", "soa"),
    ("aisia-runner", "management-review-packager", "aisia"),
    ("nonconformity-tracker", "management-review-packager", "nonconformity_register"),
    ("metrics-collector", "management-review-packager", "metrics_report"),
    ("internal-audit-planner", "management-review-packager", "internal_audit_plan"),
]

CITATION_PREFIXES = (
    "ISO/IEC 42001:2023, ",
    "ISO 42001, ",
    "EU AI Act, ",
    "GOVERN ",
    "MAP ",
    "MEASURE ",
    "MANAGE ",
    "Colorado SB 205, ",
    "UK ATRS, ",
    "NYC LL144",
    "Singapore MAGF 2e, ",
    "MAS FEAT Principles (2018), ",
    "AI Verify (IMDA 2024), ",
    "MAS Veritas",
    "CCPA Regulations (CPPA), ",
    "California Civil Code, ",
    "California Business and Professions Code, ",
    "California Attorney General Guidance",
    "Canada AIDA ",
    "AIDA Section ",
    "PIPEDA, ",
    "OSFI Guideline E-23, ",
    "Canada Directive on Automated Decision-Making, ",
    "Quebec Law 25, ",
    "Canada Voluntary AI Code (2023), ",
)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_json(obj: Any) -> bytes:
    """Deterministic JSON serialization for digests."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


def _classify_artifact(filename: str) -> tuple[str | None, str | None]:
    """Return (plugin_name, artifact_type) for a filename, or (None, None)."""
    lower = filename.lower()
    for prefix, plugin_name, artifact_type in _ARTIFACT_TO_PLUGIN:
        if prefix in lower:
            return plugin_name, artifact_type
    return None, None


def _read_artifact_metadata(path: Path) -> dict[str, Any]:
    """Return {agent_signature, emitted_at, citations} from a JSON artifact.

    For non-JSON or malformed files, returns empty-value dict.
    """
    result: dict[str, Any] = {
        "agent_signature": None,
        "emitted_at": None,
        "citations": [],
    }
    if path.suffix.lower() != ".json":
        return result
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return result
    if not isinstance(data, dict):
        return result
    result["agent_signature"] = data.get("agent_signature")
    result["emitted_at"] = data.get("timestamp") or data.get("generated_at")
    # Aggregate citations: top-level plus any row-level.
    citations: list[str] = []
    top = data.get("citations")
    if isinstance(top, list):
        citations.extend(str(c) for c in top if isinstance(c, str))
    for row_key in ("rows", "records", "sections", "systems", "matrix"):
        rows = data.get(row_key)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    row_c = row.get("citations")
                    if isinstance(row_c, list):
                        citations.extend(str(c) for c in row_c if isinstance(c, str))
    result["citations"] = citations
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_inputs(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("inputs must be a dict")
    missing = [f for f in REQUIRED_INPUT_FIELDS if f not in inputs]
    if missing:
        raise ValueError(f"inputs missing required fields: {sorted(missing)}")

    source_dir = Path(inputs["source_dir"])
    if not source_dir.is_dir():
        raise ValueError(f"source_dir {source_dir!s} is not a readable directory")

    scope = inputs["scope"]
    if not isinstance(scope, dict):
        raise ValueError("scope must be a dict")
    scope_missing = [f for f in REQUIRED_SCOPE_FIELDS if f not in scope]
    if scope_missing:
        raise ValueError(f"scope missing required fields: {sorted(scope_missing)}")

    intended_recipient = scope.get("intended_recipient")
    if intended_recipient not in VALID_INTENDED_RECIPIENTS:
        raise ValueError(
            f"scope.intended_recipient must be one of {VALID_INTENDED_RECIPIENTS}; "
            f"got {intended_recipient!r}"
        )

    algorithm = inputs.get("signing_algorithm", "hmac-sha256")
    if algorithm not in VALID_SIGNING_ALGORITHMS:
        raise ValueError(
            f"signing_algorithm must be one of {VALID_SIGNING_ALGORITHMS}; got {algorithm!r}"
        )


def _scan_source(source_dir: Path) -> list[Path]:
    """Return a sorted list of artifact files found under source_dir.

    Accepts both flat directories (single output dir per plugin) and nested
    layouts (Hermes Agent memory path: ~/.hermes/memory/aigovclaw/<type>/*.json).
    """
    files: list[Path] = []
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".json", ".md", ".csv"):
            continue
        if path.name.startswith("."):
            continue
        # Skip a top-level summary that is not a plugin output.
        if path.name.lower() == "summary.md" and path.parent == source_dir:
            continue
        files.append(path)
    return files


# ---------------------------------------------------------------------------
# Bundle id
# ---------------------------------------------------------------------------


def _generate_bundle_id(scope: dict[str, Any]) -> str:
    ts = _utc_now_iso()
    digest_input = json.dumps(scope, sort_keys=True).encode("utf-8") + ts.encode("utf-8")
    short = hashlib.sha256(digest_input).hexdigest()[:6]
    return f"aigovops-bundle-{ts}-{short}"


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def _build_provenance(included_plugins: set[str], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    seen_plugin = set()
    for art in artifacts:
        plugin_name = art.get("plugin")
        if not plugin_name or plugin_name in seen_plugin:
            continue
        seen_plugin.add(plugin_name)
        nodes.append({"plugin": plugin_name, "output": art["path"]})

    edges: list[dict[str, Any]] = []
    for upstream, downstream, via in _PROVENANCE_EDGES:
        if upstream in included_plugins and downstream in included_plugins:
            edges.append({
                "from": upstream,
                "to": downstream,
                "via_field": via,
            })

    return {
        "nodes": sorted(nodes, key=lambda n: n["plugin"]),
        "edges": sorted(edges, key=lambda e: (e["from"], e["to"], e["via_field"])),
        "derived_from_artifact_refs": True,
    }


# ---------------------------------------------------------------------------
# Citation aggregation
# ---------------------------------------------------------------------------


def _aggregate_citations(all_citations: list[str]) -> dict[str, list[str]]:
    """Group a list of citations by framework prefix. Deduplicated. Sorted."""
    groups: dict[str, list[str]] = {
        "ISO/IEC 42001:2023": [],
        "NIST AI RMF 1.0": [],
        "EU AI Act": [],
        "UK ATRS": [],
        "Colorado SB 205": [],
        "NYC LL144": [],
        "Singapore MAGF 2e": [],
        "MAS FEAT": [],
        "AI Verify": [],
        "MAS Veritas": [],
        "California": [],
        "Canada": [],
        "Other": [],
    }
    seen: set[str] = set()
    for raw in all_citations:
        if not isinstance(raw, str):
            continue
        citation = raw.strip()
        if not citation or citation in seen:
            continue
        seen.add(citation)
        if citation.startswith("ISO/IEC 42001:2023") or citation.startswith("ISO 42001"):
            groups["ISO/IEC 42001:2023"].append(citation)
        elif citation.startswith(("GOVERN ", "MAP ", "MEASURE ", "MANAGE ")):
            groups["NIST AI RMF 1.0"].append(citation)
        elif citation.startswith("EU AI Act"):
            groups["EU AI Act"].append(citation)
        elif citation.startswith("UK ATRS"):
            groups["UK ATRS"].append(citation)
        elif citation.startswith("Colorado SB 205"):
            groups["Colorado SB 205"].append(citation)
        elif citation.startswith("NYC LL144") or citation.startswith("NYC DCWP"):
            groups["NYC LL144"].append(citation)
        elif citation.startswith("Singapore MAGF"):
            groups["Singapore MAGF 2e"].append(citation)
        elif citation.startswith("MAS FEAT"):
            groups["MAS FEAT"].append(citation)
        elif citation.startswith("AI Verify"):
            groups["AI Verify"].append(citation)
        elif citation.startswith("MAS Veritas"):
            groups["MAS Veritas"].append(citation)
        elif citation.startswith(("CCPA", "California ")):
            groups["California"].append(citation)
        elif citation.startswith(("Canada ", "AIDA ", "PIPEDA", "OSFI ", "Quebec ")):
            groups["Canada"].append(citation)
        else:
            groups["Other"].append(citation)
    return {k: sorted(v) for k, v in groups.items() if v}


def _coverage_counts(groups: dict[str, list[str]]) -> dict[str, int]:
    """Compute a count of unique references per primary instrument."""
    counts: dict[str, int] = {
        "iso42001_clauses_and_controls": 0,
        "nist_subcategories": 0,
        "eu_ai_act_articles": 0,
        "uk_atrs_sections": 0,
        "colorado_sb205_sections": 0,
        "nyc_ll144_sections": 0,
        "singapore_magf_pillars": 0,
    }
    counts["iso42001_clauses_and_controls"] = len(groups.get("ISO/IEC 42001:2023", []))
    counts["nist_subcategories"] = len(groups.get("NIST AI RMF 1.0", []))
    counts["eu_ai_act_articles"] = len(groups.get("EU AI Act", []))
    counts["uk_atrs_sections"] = len(groups.get("UK ATRS", []))
    counts["colorado_sb205_sections"] = len(groups.get("Colorado SB 205", []))
    counts["nyc_ll144_sections"] = len(groups.get("NYC LL144", []))
    counts["singapore_magf_pillars"] = len(groups.get("Singapore MAGF 2e", []))
    return counts


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------


def _hmac_hex(key: bytes, data: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Crosswalk copy
# ---------------------------------------------------------------------------


_CROSSWALK_DATA_DIR = Path(__file__).resolve().parent.parent / "crosswalk-matrix-builder" / "data"


def _copy_crosswalk(target_dir: Path) -> list[str]:
    """Copy crosswalk data YAML files into the bundle. Returns list of copied filenames."""
    if not _CROSSWALK_DATA_DIR.is_dir():
        return []
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for src in sorted(_CROSSWALK_DATA_DIR.glob("*.yaml")):
        dst = target_dir / src.name
        shutil.copy2(src, dst)
        copied.append(src.name)
    return sorted(copied)


# ---------------------------------------------------------------------------
# Canonical entry point
# ---------------------------------------------------------------------------


def pack_bundle(inputs: dict[str, Any]) -> dict[str, Any]:
    """Produce a deterministic evidence bundle from a directory of plugin outputs.

    Args:
        inputs: Dict with source_dir, scope, output_dir (required). Optional
            bundle_id, signing_algorithm (default 'hmac-sha256'),
            signing_key_env (default 'AIGOVOPS_BUNDLE_SIGNING_KEY'),
            include_source_crosswalk (default True), reviewed_by.

    Returns:
        A bundle-report dict with bundle_id, bundle_path, manifest, signatures,
        citation_groups, coverage_counts, provenance, warnings, summary.

    Raises:
        ValueError: on structural input problems.
    """
    _validate_inputs(inputs)

    source_dir = Path(inputs["source_dir"]).resolve()
    output_dir = Path(inputs["output_dir"]).resolve()
    scope = dict(inputs["scope"])
    bundle_id = inputs.get("bundle_id") or _generate_bundle_id(scope)
    algorithm = inputs.get("signing_algorithm", "hmac-sha256")
    signing_key_env = inputs.get("signing_key_env", "AIGOVOPS_BUNDLE_SIGNING_KEY")
    include_crosswalk = inputs.get("include_source_crosswalk", True)

    bundle_dir = output_dir / bundle_id
    artifacts_dir = bundle_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    warnings_list: list[str] = []

    # Scan source artifacts.
    source_files = _scan_source(source_dir)
    if not source_files:
        warnings_list.append(
            "source_dir contained zero artifact files with .json, .md, or .csv "
            "extensions. Bundle produced with empty artifact list."
        )

    # Copy and manifest-ify each file.
    artifact_entries: list[dict[str, Any]] = []
    included_plugins: set[str] = set()
    all_citations: list[str] = []

    for src in source_files:
        plugin_name, artifact_type = _classify_artifact(src.name)
        if plugin_name is None:
            plugin_name = "unknown-plugin"
            warnings_list.append(
                f"artifact {src.name!r} could not be classified to a known plugin; "
                "copied under artifacts/unknown-plugin/ and flagged in manifest."
            )
        dest_dir = artifacts_dir / plugin_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        shutil.copy2(src, dest)

        meta = _read_artifact_metadata(dest)
        sha = _sha256_file(dest)
        size = dest.stat().st_size

        rel_path = str(dest.relative_to(bundle_dir)).replace(os.sep, "/")
        entry = {
            "path": rel_path,
            "plugin": plugin_name,
            "agent_signature": meta["agent_signature"],
            "sha256": sha,
            "size_bytes": size,
            "artifact_type": artifact_type,
            "emitted_at": meta["emitted_at"],
        }
        artifact_entries.append(entry)
        if plugin_name != "unknown-plugin":
            included_plugins.add(plugin_name)
        all_citations.extend(meta["citations"])

        if meta["agent_signature"] is None and src.suffix.lower() == ".json":
            warnings_list.append(
                f"artifact {rel_path!r} has no agent_signature field; downstream "
                "version-aware adapter routing is not possible for this artifact."
            )

    artifact_entries.sort(key=lambda e: e["path"])

    # Compute missing plugins relative to the catalogue.
    all_catalogue_plugins = {p for _, p, _ in _ARTIFACT_TO_PLUGIN}
    missing_plugins = sorted(all_catalogue_plugins - included_plugins)

    # Aggregate citations.
    citation_groups = _aggregate_citations(all_citations)
    citations_unique = sum(len(v) for v in citation_groups.values())
    coverage_counts = _coverage_counts(citation_groups)

    # Copy crosswalk when requested.
    crosswalk_files: list[str] = []
    if include_crosswalk:
        crosswalk_files = _copy_crosswalk(bundle_dir / "crosswalk")

    # Build MANIFEST.
    manifest = {
        "bundle_schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_id": bundle_id,
        "generated_at": _utc_now_iso(),
        "generated_by": AGENT_SIGNATURE,
        "scope": scope,
        "artifact_count": len(artifact_entries),
        "artifacts": artifact_entries,
        "included_plugins": sorted(included_plugins),
        "missing_plugins": missing_plugins,
        "citations_unique_count": citations_unique,
        "crosswalk_files_included": crosswalk_files,
    }
    manifest_bytes = _canonical_json(manifest)
    manifest_path = bundle_dir / "MANIFEST.json"
    manifest_path.write_bytes(manifest_bytes)
    manifest_sha = _sha256_bytes(manifest_bytes)

    # Provenance chain.
    provenance = _build_provenance(included_plugins, artifact_entries)
    provenance_path = bundle_dir / "provenance-chain.json"
    provenance_path.write_bytes(_canonical_json(provenance))

    # Citation summary markdown.
    citation_summary_md = _render_citation_summary(
        bundle_id=bundle_id,
        scope=scope,
        citation_groups=citation_groups,
        coverage_counts=coverage_counts,
    )
    (bundle_dir / "citation-summary.md").write_text(citation_summary_md, encoding="utf-8")

    # Signatures.
    signatures: dict[str, Any] = {
        "algorithm": algorithm,
        "manifest_sha256": manifest_sha,
        "signed_at": _utc_now_iso(),
    }
    effective_algorithm = algorithm
    if algorithm == "hmac-sha256":
        key_material = os.environ.get(signing_key_env)
        if not key_material:
            warnings_list.append(
                f"signing_algorithm='hmac-sha256' but environment variable "
                f"{signing_key_env!r} is not set. Signing downgraded to 'none'. "
                "Supply the HMAC key and re-pack to produce a signed bundle."
            )
            effective_algorithm = "none"
            signatures["algorithm"] = "none"
        else:
            key_bytes = key_material.encode("utf-8")
            signatures["key_id"] = f"env:{signing_key_env}"
            signatures["manifest_hmac"] = _hmac_hex(key_bytes, manifest_sha.encode("ascii"))
            artifact_hmacs: dict[str, str] = {}
            for entry in artifact_entries:
                artifact_hmacs[entry["path"]] = _hmac_hex(key_bytes, entry["sha256"].encode("ascii"))
            signatures["artifact_hmacs"] = dict(sorted(artifact_hmacs.items()))

    (bundle_dir / "signatures.json").write_bytes(_canonical_json(signatures))

    # README.
    readme_md = _render_bundle_readme(
        bundle_id=bundle_id,
        scope=scope,
        artifact_count=len(artifact_entries),
        included_plugins=sorted(included_plugins),
        missing_plugins=missing_plugins,
        algorithm=effective_algorithm,
        reviewed_by=inputs.get("reviewed_by"),
        warnings_list=warnings_list,
    )
    (bundle_dir / "README.md").write_text(readme_md, encoding="utf-8")

    summary = {
        "bundle_id": bundle_id,
        "artifact_count": len(artifact_entries),
        "included_plugin_count": len(included_plugins),
        "missing_plugin_count": len(missing_plugins),
        "citations_unique_count": citations_unique,
        "coverage_counts": coverage_counts,
        "signing_algorithm": effective_algorithm,
    }

    return {
        "timestamp": _utc_now_iso(),
        "agent_signature": AGENT_SIGNATURE,
        "bundle_id": bundle_id,
        "bundle_path": str(bundle_dir),
        "scope": scope,
        "manifest": manifest,
        "signatures": signatures,
        "provenance": provenance,
        "citation_groups": citation_groups,
        "coverage_counts": coverage_counts,
        "warnings": warnings_list,
        "summary": summary,
        "reviewed_by": inputs.get("reviewed_by"),
    }


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def verify_bundle(
    bundle_dir: str | Path,
    signing_key_env: str = "AIGOVOPS_BUNDLE_SIGNING_KEY",
) -> dict[str, Any]:
    """Verify an evidence bundle on disk.

    Returns a findings dict with bundle_id, manifest_sha256_matches,
    artifact_hmacs_match, missing_artifacts, extra_artifacts, warnings,
    overall.
    """
    bundle_dir = Path(bundle_dir)
    if not bundle_dir.is_dir():
        raise ValueError(f"bundle_dir {bundle_dir!s} is not a directory")
    manifest_path = bundle_dir / "MANIFEST.json"
    signatures_path = bundle_dir / "signatures.json"
    if not manifest_path.is_file():
        raise ValueError(f"MANIFEST.json missing from {bundle_dir!s}")
    if not signatures_path.is_file():
        raise ValueError(f"signatures.json missing from {bundle_dir!s}")

    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    signatures = json.loads(signatures_path.read_text(encoding="utf-8"))
    warnings_out: list[str] = []

    # Manifest self-check: the sha256 recorded in signatures should match
    # the current manifest bytes.
    current_manifest_sha = _sha256_bytes(manifest_bytes)
    manifest_sha_matches = current_manifest_sha == signatures.get("manifest_sha256")

    # Artifact presence + per-file hash check.
    missing: list[str] = []
    extra: list[str] = []
    mutated_artifacts: list[str] = []

    manifest_paths = {e["path"] for e in manifest.get("artifacts", [])}
    for entry in manifest.get("artifacts", []):
        abs_path = bundle_dir / entry["path"]
        if not abs_path.is_file():
            missing.append(entry["path"])
            continue
        actual_sha = _sha256_file(abs_path)
        if actual_sha != entry["sha256"]:
            mutated_artifacts.append(entry["path"])

    # Extra artifacts on disk that the manifest does not claim.
    artifacts_root = bundle_dir / "artifacts"
    if artifacts_root.is_dir():
        for path in artifacts_root.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(bundle_dir)).replace(os.sep, "/")
            if rel not in manifest_paths:
                extra.append(rel)

    # HMAC verification (when algorithm is hmac-sha256).
    algorithm = signatures.get("algorithm", "none")
    artifact_hmacs_match: bool | None = None
    if algorithm == "hmac-sha256":
        key_material = os.environ.get(signing_key_env)
        if not key_material:
            warnings_out.append(
                f"signature algorithm is 'hmac-sha256' but {signing_key_env!r} "
                "is not set; HMAC verification skipped."
            )
            artifact_hmacs_match = None
        else:
            key_bytes = key_material.encode("utf-8")
            expected_manifest_hmac = _hmac_hex(
                key_bytes, current_manifest_sha.encode("ascii")
            )
            if expected_manifest_hmac != signatures.get("manifest_hmac"):
                artifact_hmacs_match = False
            else:
                # Per-artifact HMAC check.
                expected_artifact_hmacs = signatures.get("artifact_hmacs", {})
                all_match = True
                for entry in manifest.get("artifacts", []):
                    rel = entry["path"]
                    expected = _hmac_hex(key_bytes, entry["sha256"].encode("ascii"))
                    recorded = expected_artifact_hmacs.get(rel)
                    if recorded != expected:
                        all_match = False
                        break
                artifact_hmacs_match = all_match and not mutated_artifacts

    # Overall determination.
    if algorithm == "none":
        overall = "signing-disabled"
        if missing or mutated_artifacts:
            overall = "drift-detected"
        if mutated_artifacts and not missing:
            overall = "signature-mismatch"
    else:
        if mutated_artifacts:
            overall = "signature-mismatch"
        elif missing:
            overall = "drift-detected"
        elif artifact_hmacs_match is False:
            overall = "signature-mismatch"
        elif not manifest_sha_matches:
            overall = "signature-mismatch"
        else:
            overall = "verified"

    return {
        "bundle_id": manifest.get("bundle_id"),
        "manifest_sha256_matches": manifest_sha_matches,
        "artifact_hmacs_match": artifact_hmacs_match,
        "missing_artifacts": sorted(missing),
        "extra_artifacts": sorted(extra),
        "mutated_artifacts": sorted(mutated_artifacts),
        "warnings": warnings_out,
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# Inspect
# ---------------------------------------------------------------------------


def inspect_bundle(bundle_dir: str | Path) -> dict[str, Any]:
    """Return a quick summary dict for CLI pretty-print."""
    bundle_dir = Path(bundle_dir)
    manifest_path = bundle_dir / "MANIFEST.json"
    if not manifest_path.is_file():
        raise ValueError(f"MANIFEST.json missing from {bundle_dir!s}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    generated_at = manifest.get("generated_at") or ""
    age_seconds: int | None = None
    if generated_at:
        try:
            gen = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_seconds = int((now - gen).total_seconds())
        except ValueError:
            age_seconds = None

    return {
        "bundle_id": manifest.get("bundle_id"),
        "scope": manifest.get("scope", {}),
        "artifact_count": manifest.get("artifact_count", 0),
        "included_plugins": manifest.get("included_plugins", []),
        "citations_unique_count": manifest.get("citations_unique_count", 0),
        "generated_at": generated_at,
        "age_seconds": age_seconds,
    }


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_citation_summary(
    *,
    bundle_id: str,
    scope: dict[str, Any],
    citation_groups: dict[str, list[str]],
    coverage_counts: dict[str, int],
) -> str:
    lines: list[str] = [
        "# Citation Summary",
        "",
        f"**Bundle ID:** {bundle_id}",
        f"**Organization:** {scope.get('organization', '')}",
        f"**AIMS boundary:** {scope.get('aims_boundary', '')}",
        f"**Reporting period:** {scope.get('reporting_period_start', '')} to {scope.get('reporting_period_end', '')}",
        f"**Intended recipient:** {scope.get('intended_recipient', '')}",
        "",
        "## Citations by framework",
        "",
    ]
    if not citation_groups:
        lines.append("No citations aggregated across artifacts.")
        lines.append("")
    for framework in sorted(citation_groups.keys()):
        entries = citation_groups[framework]
        lines.append(f"### {framework}")
        lines.append("")
        for i, c in enumerate(entries, 1):
            lines.append(f"{i}. {c}")
        lines.append("")

    lines.extend([
        "## Coverage of primary instruments",
        "",
        f"- ISO/IEC 42001:2023 clauses and controls cited: {coverage_counts.get('iso42001_clauses_and_controls', 0)}",
        f"- NIST AI RMF 1.0 subcategories cited: {coverage_counts.get('nist_subcategories', 0)}",
        f"- EU AI Act articles cited: {coverage_counts.get('eu_ai_act_articles', 0)}",
        f"- UK ATRS sections cited: {coverage_counts.get('uk_atrs_sections', 0)}",
        f"- Colorado SB 205 sections cited: {coverage_counts.get('colorado_sb205_sections', 0)}",
        f"- NYC LL144 sections cited: {coverage_counts.get('nyc_ll144_sections', 0)}",
        f"- Singapore MAGF pillars cited: {coverage_counts.get('singapore_magf_pillars', 0)}",
        "",
        "## Provenance",
        "",
        "See provenance-chain.json for the plugin-to-plugin artifact graph and consumption edges.",
        "",
    ])
    return "\n".join(lines)


def _render_bundle_readme(
    *,
    bundle_id: str,
    scope: dict[str, Any],
    artifact_count: int,
    included_plugins: list[str],
    missing_plugins: list[str],
    algorithm: str,
    reviewed_by: str | None,
    warnings_list: list[str],
) -> str:
    lines = [
        "# Evidence Bundle",
        "",
        f"**Bundle ID:** {bundle_id}",
        f"**Organization:** {scope.get('organization', '')}",
        f"**AIMS boundary:** {scope.get('aims_boundary', '')}",
        f"**Reporting period:** {scope.get('reporting_period_start', '')} to {scope.get('reporting_period_end', '')}",
        f"**Intended recipient:** {scope.get('intended_recipient', '')}",
        f"**Signing algorithm:** {algorithm}",
    ]
    if reviewed_by:
        lines.append(f"**Reviewed by:** {reviewed_by}")
    lines.extend([
        "",
        "## Who this bundle is for",
        "",
        "This bundle is the unit of delivery for audit, attestation, and regulatory submission. "
        "It contains every governance artifact produced during the reporting period above, with "
        "cryptographic digests for every file and optional HMAC-SHA256 signatures over those "
        "digests. Auditors consume this bundle, not the running system.",
        "",
        "## What this bundle contains",
        "",
        f"- {artifact_count} artifact file(s) under artifacts/.",
        f"- {len(included_plugins)} upstream plugin(s) contributed: {', '.join(included_plugins) or 'none'}.",
        f"- {len(missing_plugins)} catalogue plugin(s) with no artifacts in this bundle.",
        "- MANIFEST.json: canonical artifact list with SHA-256 per file.",
        "- citation-summary.md: aggregated framework citations across all artifacts.",
        "- provenance-chain.json: plugin-to-plugin consumption edges.",
        "- signatures.json: manifest and per-artifact HMACs (when signing is enabled).",
        "- crosswalk/: copy of the crosswalk-matrix-builder data files for provenance (when included).",
        "",
        "## How to verify this bundle",
        "",
        "Run `verify_bundle(<bundle_dir>)` from evidence-bundle-packager with the same signing key "
        "in the environment variable that was used for packing. The function returns `verified` "
        "when every file hash matches and every HMAC verifies. `drift-detected` indicates an "
        "artifact listed in the manifest is missing on disk. `signature-mismatch` indicates an "
        "artifact's content has changed since packing.",
        "",
        "## How to read this bundle",
        "",
        "1. Start with README.md for scope and recipient.",
        "2. Read citation-summary.md for the framework coverage snapshot.",
        "3. Read each artifact under artifacts/<plugin-name>/ in plugin-alphabetical order.",
        "4. Consult provenance-chain.json when an artifact references a concept defined in an "
        "upstream artifact.",
        "5. If the bundle includes a crosswalk/ directory, use it to map citations across frameworks.",
        "",
    ])
    if warnings_list:
        lines.extend([
            "## Warnings",
            "",
        ])
        for w in warnings_list:
            lines.append(f"- {w}")
        lines.append("")
    lines.extend([
        "## Legal notice",
        "",
        "This bundle is audit-preparation evidence. It does not constitute legal advice. "
        "Consult qualified counsel for jurisdiction-specific determinations.",
        "",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Renderers (public API)
# ---------------------------------------------------------------------------


def render_markdown(bundle_report: dict[str, Any]) -> str:
    """Render a bundle report as Markdown with all required sections."""
    required = ("bundle_id", "scope", "manifest", "signatures", "provenance",
                "citation_groups", "warnings", "summary")
    missing = [k for k in required if k not in bundle_report]
    if missing:
        raise ValueError(f"bundle_report missing required fields: {missing}")

    scope = bundle_report["scope"]
    manifest = bundle_report["manifest"]
    signatures = bundle_report["signatures"]
    summary = bundle_report["summary"]
    provenance = bundle_report["provenance"]
    citation_groups = bundle_report["citation_groups"]

    lines: list[str] = [
        "# Bundle overview",
        "",
        f"**Bundle ID:** {bundle_report['bundle_id']}",
        f"**Generated at (UTC):** {manifest.get('generated_at', '')}",
        f"**Generated by:** {manifest.get('generated_by', '')}",
        f"**Schema version:** {manifest.get('bundle_schema_version', '')}",
    ]
    if bundle_report.get("reviewed_by"):
        lines.append(f"**Reviewed by:** {bundle_report['reviewed_by']}")
    lines.extend([
        "",
        "## Scope",
        "",
        f"- Organization: {scope.get('organization', '')}",
        f"- AIMS boundary: {scope.get('aims_boundary', '')}",
        f"- Systems in scope: {', '.join(scope.get('systems_in_scope', [])) if isinstance(scope.get('systems_in_scope'), list) else scope.get('systems_in_scope', '')}",
        f"- Reporting period: {scope.get('reporting_period_start', '')} to {scope.get('reporting_period_end', '')}",
        f"- Intended recipient: {scope.get('intended_recipient', '')}",
        "",
        "## Artifact list",
        "",
        f"Total artifacts: {summary.get('artifact_count', 0)}",
        "",
        "| Path | Plugin | Artifact type | SHA-256 |",
        "|---|---|---|---|",
    ])
    for entry in manifest.get("artifacts", []):
        lines.append(
            f"| {entry['path']} | {entry.get('plugin', '')} | "
            f"{entry.get('artifact_type', '') or ''} | {entry['sha256'][:16]}... |"
        )

    lines.extend([
        "",
        "## Citation summary",
        "",
    ])
    if not citation_groups:
        lines.append("No citations aggregated across artifacts.")
    else:
        for framework in sorted(citation_groups.keys()):
            lines.append(f"### {framework}")
            lines.append("")
            for c in citation_groups[framework]:
                lines.append(f"- {c}")
            lines.append("")

    lines.extend([
        "## Provenance",
        "",
        f"- Nodes: {len(provenance.get('nodes', []))}",
        f"- Edges: {len(provenance.get('edges', []))}",
        "",
    ])
    edges = provenance.get("edges", [])
    if edges:
        lines.append("| From | To | Via field |")
        lines.append("|---|---|---|")
        for edge in edges:
            lines.append(f"| {edge['from']} | {edge['to']} | {edge['via_field']} |")
        lines.append("")

    lines.extend([
        "## Signatures",
        "",
        f"- Algorithm: {signatures.get('algorithm', '')}",
        f"- Manifest SHA-256: {signatures.get('manifest_sha256', '')}",
    ])
    if signatures.get("manifest_hmac"):
        lines.append(f"- Manifest HMAC: {signatures['manifest_hmac']}")
        lines.append(f"- Key ID: {signatures.get('key_id', '')}")
    lines.append("")

    lines.extend([
        "## Warnings",
        "",
    ])
    if bundle_report["warnings"]:
        for w in bundle_report["warnings"]:
            lines.append(f"- {w}")
    else:
        lines.append("No warnings.")
    lines.append("")

    return "\n".join(lines)


def render_csv(bundle_report: dict[str, Any]) -> str:
    """Render one row per artifact with SHA-256 column."""
    if "manifest" not in bundle_report:
        raise ValueError("bundle_report missing 'manifest' field")
    manifest = bundle_report["manifest"]
    header = "path,plugin,agent_signature,artifact_type,sha256,size_bytes,emitted_at"
    lines = [header]
    for entry in manifest.get("artifacts", []):
        fields = [
            _csv_escape(str(entry.get("path", ""))),
            _csv_escape(str(entry.get("plugin", "") or "")),
            _csv_escape(str(entry.get("agent_signature", "") or "")),
            _csv_escape(str(entry.get("artifact_type", "") or "")),
            _csv_escape(str(entry.get("sha256", ""))),
            _csv_escape(str(entry.get("size_bytes", ""))),
            _csv_escape(str(entry.get("emitted_at", "") or "")),
        ]
        lines.append(",".join(fields))
    return "\n".join(lines) + "\n"


def _csv_escape(value: str) -> str:
    if any(ch in value for ch in (",", '"', "\n")):
        return '"' + value.replace('"', '""') + '"'
    return value


__all__ = [
    "AGENT_SIGNATURE",
    "BUNDLE_SCHEMA_VERSION",
    "REQUIRED_INPUT_FIELDS",
    "VALID_SIGNING_ALGORITHMS",
    "VALID_INTENDED_RECIPIENTS",
    "EXPECTED_ARTIFACT_TYPES",
    "pack_bundle",
    "verify_bundle",
    "inspect_bundle",
    "render_markdown",
    "render_csv",
]
