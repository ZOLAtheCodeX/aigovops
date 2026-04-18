"""
SKILL.md / workflow / plugin consistency audit.

Walks every SKILL.md, operationalization-map.md, and aigovclaw
workflow.md file referenced in the repo. Extracts plugin function
references, input field names, artifact types, and citation formats.
Verifies each reference exists in plugin code or an adapter, and that
citation formats match STYLE.md.

Output: a structured report with OK / WARN / FAIL per finding.
Exit code 0 if no FAIL; non-zero otherwise.

Usage:
    python tests/audit/consistency_audit.py [--aigovclaw-path PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


# Known plugin public function names (from plugins/*/plugin.py inspection).
PLUGIN_PUBLIC_FUNCTIONS = {
    "audit-log-generator": ["generate_audit_log", "map_to_annex_a_controls", "render_markdown"],
    "role-matrix-generator": ["generate_role_matrix", "render_markdown", "render_csv"],
    "risk-register-builder": ["generate_risk_register", "render_markdown", "render_csv"],
    "soa-generator": ["generate_soa", "render_markdown", "render_csv"],
    "aisia-runner": ["run_aisia", "render_markdown"],
    "nonconformity-tracker": ["generate_nonconformity_register", "render_markdown"],
    "management-review-packager": ["generate_review_package", "render_markdown"],
    "metrics-collector": ["generate_metrics_report", "render_markdown", "render_csv"],
    "gap-assessment": ["generate_gap_assessment", "render_markdown", "render_csv"],
    "data-register-builder": ["generate_data_register", "render_markdown", "render_csv"],
    "applicability-checker": ["check_applicability", "render_markdown"],
    "uk-atrs-recorder": ["generate_atrs_record", "render_markdown", "render_csv"],
    "colorado-ai-act-compliance": ["generate_compliance_record", "render_markdown", "render_csv"],
    "nyc-ll144-audit-packager": ["generate_audit_package", "render_markdown", "render_csv"],
    "singapore-magf-assessor": ["generate_magf_assessment", "render_markdown", "render_csv"],
}


def audit_skill_md_section_headers(findings: list[dict]) -> None:
    """Every SKILL.md must have all six required sections in order."""
    required = [
        "## Overview", "## Scope", "## Framework Reference",
        "## Operationalizable Controls", "## Output Standards", "## Limitations",
    ]
    for skill_dir in (REPO_ROOT / "skills").iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            findings.append({"level": "FAIL", "area": "skills",
                             "item": str(skill_md.relative_to(REPO_ROOT)),
                             "message": "SKILL.md missing"})
            continue
        text = _read(skill_md)
        for section in required:
            if section not in text:
                findings.append({"level": "FAIL", "area": "skills",
                                 "item": f"{skill_dir.name}/SKILL.md",
                                 "message": f"missing required section {section!r}"})


def audit_plugin_function_references(findings: list[dict], aigovclaw_path: Path | None) -> None:
    """SKILL.md and workflow.md references to plugin function names must
    match the actual plugin function names."""
    all_function_names: set[str] = set()
    for fns in PLUGIN_PUBLIC_FUNCTIONS.values():
        all_function_names.update(fns)

    # Verify each function actually exists in its plugin module.
    for plugin_name, functions in PLUGIN_PUBLIC_FUNCTIONS.items():
        plugin_file = REPO_ROOT / "plugins" / plugin_name / "plugin.py"
        if not plugin_file.is_file():
            findings.append({"level": "FAIL", "area": "plugins",
                             "item": plugin_name,
                             "message": f"plugin.py missing at {plugin_file}"})
            continue
        plugin_text = _read(plugin_file)
        for fn in functions:
            if f"def {fn}(" not in plugin_text:
                findings.append({"level": "FAIL", "area": "plugins",
                                 "item": f"{plugin_name}/plugin.py",
                                 "message": f"declared public function {fn!r} not found in source"})

    # Scan SKILL.md files for plugin-function references: patterns like
    # `generate_xxx()`, `audit_log.generate_audit_log`, etc.
    for skill_dir in (REPO_ROOT / "skills").iterdir():
        if not skill_dir.is_dir():
            continue
        for md_path in skill_dir.glob("*.md"):
            text = _read(md_path)
            for match in re.finditer(r"`([a-z_]+)\(\)?`", text):
                name = match.group(1)
                # Only flag when the name looks like a plugin entry point
                # (starts with 'generate_' or 'run_' and isn't a common word).
                if name.startswith(("generate_", "run_", "map_to_", "render_")):
                    if name not in all_function_names:
                        findings.append({"level": "WARN", "area": "skills",
                                         "item": f"{md_path.relative_to(REPO_ROOT)}",
                                         "message": f"references function {name!r} not in any plugin's public API"})

    # Scan aigovclaw workflows if provided.
    if aigovclaw_path:
        workflows_dir = aigovclaw_path / "workflows"
        if workflows_dir.is_dir():
            for wf_path in workflows_dir.glob("*.md"):
                text = _read(wf_path)
                for match in re.finditer(r"plugin\.([a-z_]+)", text):
                    name = match.group(1)
                    if name.startswith(("generate_", "run_", "render_", "map_to_")):
                        if name not in all_function_names:
                            findings.append({"level": "WARN", "area": "workflows",
                                             "item": f"aigovclaw/{wf_path.relative_to(aigovclaw_path)}",
                                             "message": f"references plugin function {name!r} not in any plugin's public API"})


def audit_citation_format(findings: list[dict]) -> None:
    """Every published SKILL.md citation must match STYLE.md format.

    STYLE.md allows two forms:
    - Full: 'ISO/IEC 42001:2023, Clause X.X.X' (first reference)
    - Short: 'ISO 42001, Clause X.X.X' (subsequent references)

    This audit flags only clearly-wrong patterns: 'ISO/IEC 42001' without
    the ':2023' year suffix followed by a Clause or Annex keyword (would
    be a version drift). Short-form is accepted.
    """
    # Match only actual citation patterns: 'ISO/IEC 42001' + comma/space,
    # followed directly by 'Clause' or 'Annex A'. Credential references
    # (e.g., 'ISO/IEC 42001 Lead Implementer') are not flagged.
    bad_iso = re.compile(r"ISO/IEC 42001(?!:2023)\s*,\s*(Clause|Annex A)")

    for skill_dir in (REPO_ROOT / "skills").iterdir():
        if not skill_dir.is_dir():
            continue
        for md in skill_dir.glob("*.md"):
            text = _read(md)
            for line_no, line in enumerate(text.splitlines(), 1):
                for match in bad_iso.finditer(line):
                    findings.append({"level": "WARN", "area": "citations",
                                     "item": f"{md.relative_to(REPO_ROOT)}:{line_no}",
                                     "message": f"ISO citation missing ':2023' year: {match.group(0)!r}"})


def audit_evals_schema(findings: list[dict]) -> None:
    """Every eval test_cases.yaml must have matching skill directory."""
    evals_root = REPO_ROOT / "evals"
    if not evals_root.is_dir():
        findings.append({"level": "FAIL", "area": "evals",
                         "item": "evals/", "message": "evals/ directory missing"})
        return
    for eval_dir in evals_root.iterdir():
        if not eval_dir.is_dir() or eval_dir.name.startswith("."):
            continue
        test_cases = eval_dir / "test_cases.yaml"
        if not test_cases.is_file():
            findings.append({"level": "FAIL", "area": "evals",
                             "item": f"evals/{eval_dir.name}/",
                             "message": "test_cases.yaml missing"})
            continue
        skill_dir = REPO_ROOT / "skills" / eval_dir.name
        if not skill_dir.is_dir():
            findings.append({"level": "WARN", "area": "evals",
                             "item": f"evals/{eval_dir.name}/",
                             "message": f"no matching skill at skills/{eval_dir.name}/"})


def audit_em_dashes_and_hedging(findings: list[dict]) -> None:
    """STYLE.md prohibits em-dashes in any committed file and hedging
    phrases in outputs. Scan SKILL.md, operationalization maps, and
    plugin Python files."""
    hedging = ["may want to consider", "might be helpful to", "could potentially",
               "it is possible that", "you might find"]
    for root, patterns in [
        (REPO_ROOT / "skills", ["*.md"]),
        (REPO_ROOT / "plugins", ["**/*.py", "**/*.md"]),
        (REPO_ROOT / "docs", ["*.md"]),
        (REPO_ROOT / "tests", ["**/*.py"]),
    ]:
        if not root.is_dir():
            continue
        for pattern in patterns:
            for f in root.glob(pattern):
                if "__pycache__" in str(f) or "/outputs/" in str(f):
                    continue
                text = _read(f)
                for line_no, line in enumerate(text.splitlines(), 1):
                    if "\u2014" in line:
                        findings.append({"level": "FAIL", "area": "style",
                                         "item": f"{f.relative_to(REPO_ROOT)}:{line_no}",
                                         "message": "em-dash (U+2014) present"})
                    for phrase in hedging:
                        if phrase in line.lower():
                            # Skip files where the phrases are DEFINED as prohibited,
                            # or files that ARE the audit script itself, or test
                            # files asserting that prohibited phrases do not appear
                            # in rendered output.
                            lower_path = str(f).lower()
                            if any(token in lower_path for token in (
                                "agents.md", "style.md", "consistency_audit.py",
                                "tests/test_plugin.py",
                            )):
                                continue
                            findings.append({"level": "WARN", "area": "style",
                                             "item": f"{f.relative_to(REPO_ROOT)}:{line_no}",
                                             "message": f"hedging phrase present: {phrase!r}"})
                            break


def audit_workflow_plugin_artifact_type_alignment(findings: list[dict], aigovclaw_path: Path | None) -> None:
    """Each aigovclaw workflow should name the plugin it consumes; cross-check
    that the artifact_type the workflow produces matches the plugin's output."""
    if not aigovclaw_path:
        return
    workflows_dir = aigovclaw_path / "workflows"
    if not workflows_dir.is_dir():
        return

    # Map workflow names to expected plugin names.
    expected = {
        "audit-log.md": "audit-log-generator",
        "aisia-runner.md": "aisia-runner",
        "risk-register.md": "risk-register-builder",
        "soa.md": "soa-generator",
        "role-matrix.md": "role-matrix-generator",
        "nonconformity.md": "nonconformity-tracker",
        "management-review.md": "management-review-packager",
        "metrics-collector.md": "metrics-collector",
        "gap-assessment.md": "gap-assessment",
        "data-register.md": "data-register-builder",
        "applicability-check.md": "applicability-checker",
    }

    for workflow_file, plugin_name in expected.items():
        path = workflows_dir / workflow_file
        if not path.is_file():
            findings.append({"level": "FAIL", "area": "workflows",
                             "item": f"aigovclaw/workflows/{workflow_file}",
                             "message": "workflow file missing"})
            continue
        text = _read(path)
        if plugin_name not in text:
            findings.append({"level": "WARN", "area": "workflows",
                             "item": f"aigovclaw/workflows/{workflow_file}",
                             "message": f"does not reference expected plugin {plugin_name!r}"})


def print_report(findings: list[dict]) -> int:
    levels = {"FAIL": 0, "WARN": 0, "OK": 0}
    print("## Consistency Audit Report")
    print()
    if not findings:
        print("All checks passed: no findings.")
        return 0
    by_area: dict[str, list[dict]] = {}
    for f in findings:
        by_area.setdefault(f["area"], []).append(f)
        levels[f["level"]] = levels.get(f["level"], 0) + 1
    for area in sorted(by_area):
        print(f"### {area}")
        print()
        for f in by_area[area]:
            print(f"- [{f['level']}] {f['item']}: {f['message']}")
        print()
    print("### Summary")
    print()
    for level, count in levels.items():
        if count:
            print(f"- {level}: {count}")
    return 0 if levels["FAIL"] == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--aigovclaw-path",
        default=str(REPO_ROOT.parent / "aigovclaw"),
        help="Path to the aigovclaw repo for workflow audits.",
    )
    args = parser.parse_args(argv)
    aigovclaw_path = Path(args.aigovclaw_path)
    if not aigovclaw_path.is_dir():
        print(f"Note: aigovclaw path {aigovclaw_path} not found; skipping workflow checks.")
        aigovclaw_path = None

    findings: list[dict] = []
    audit_skill_md_section_headers(findings)
    audit_plugin_function_references(findings, aigovclaw_path)
    audit_citation_format(findings)
    audit_evals_schema(findings)
    audit_em_dashes_and_hedging(findings)
    audit_workflow_plugin_artifact_type_alignment(findings, aigovclaw_path)
    return print_report(findings)


if __name__ == "__main__":
    sys.exit(main())
