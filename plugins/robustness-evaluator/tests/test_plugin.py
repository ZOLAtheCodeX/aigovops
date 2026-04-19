"""Tests for the robustness-evaluator plugin. Runs under pytest or standalone."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plugin  # noqa: E402


def _system(high_risk: bool = True, continuous_learning: bool = False) -> dict:
    return {
        "system_id": "sys-triage-eu",
        "system_name": "Clinical triage AI",
        "risk_tier": "high" if high_risk else "limited",
        "jurisdiction": "eu",
        "continuous_learning": continuous_learning,
    }


def _scope(dims, indep: str = "third-party-audit") -> dict:
    return {
        "dimensions": list(dims),
        "evaluation_date": "2026-04-15",
        "evaluator_identity": "ACME Independent Evaluators GmbH",
        "evaluator_independence": indep,
    }


def _accuracy_pass() -> dict:
    return {
        "test_method": "holdout",
        "dataset_ref": "test-data-2026-04-10",
        "primary_metric": "F1",
        "metric_value": 0.82,
        "declared_threshold": 0.75,
        "pass": True,
        "evidence_ref": "reports/accuracy-eval-2026-04-10.pdf",
    }


def _robustness_pass() -> dict:
    return {
        "test_method": "stress-test",
        "dataset_ref": "stress-2026-04-10",
        "resilience_level": "verified-adequate",
        "evidence_ref": "reports/robustness-eval-2026-04-10.pdf",
    }


def _cybersecurity_pass() -> dict:
    return {
        "test_method": "red-team-engagement",
        "resilience_level": "verified-adequate",
        "attack_types_tested": ["prompt-injection", "evasion"],
        "evidence_ref": "reports/cyber-2026-04-10.pdf",
    }


# 1. Happy path.
def test_happy_path_full_compliance_posture():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe-design.pdf",
        "concept_drift_monitoring_ref": "docs/drift-plan.pdf",
    })
    for f in (
        "timestamp",
        "agent_signature",
        "framework",
        "system_description_echo",
        "evaluation_scope_echo",
        "dimension_assessments",
        "art_15_2_declaration_status",
        "backup_plan_status",
        "concept_drift_monitoring_status",
        "citations",
        "warnings",
        "summary",
    ):
        assert f in result
    assert result["summary"]["blocking_warnings"] == 0
    assert result["agent_signature"] == "robustness-evaluator/0.1.0"


# 2. Accuracy fails threshold.
def test_accuracy_fails_threshold_reports_failure():
    failing = _accuracy_pass()
    failing.update({"metric_value": 0.60, "pass": False})
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"]),
        "evaluation_results": {
            "accuracy": failing,
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    assert "accuracy" in result["summary"]["failed_dimensions"]
    acc = next(a for a in result["dimension_assessments"] if a["dimension"] == "accuracy")
    assert any("Article 15(1)" in w or "Article 15, Paragraph 1" in w or "tri-requirement" in w for w in acc["warnings"])


# 3. Adversarial posture aggregation.
def test_adversarial_posture_worst_of():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope([
            "accuracy",
            "robustness",
            "cybersecurity",
            "adversarial-robustness",
            "data-poisoning-resistance",
            "model-evasion-resistance",
            "confidentiality",
        ]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
            "adversarial-robustness": {
                "test_method": "red-team-engagement",
                "resilience_level": "verified-strong",
                "evidence_ref": "r1",
            },
            "data-poisoning-resistance": {
                "test_method": "poisoning-simulation",
                "resilience_level": "verified-adequate",
                "evidence_ref": "r2",
            },
            "model-evasion-resistance": {
                "test_method": "evasion-attack-simulation",
                "resilience_level": "verified-weak",
                "evidence_ref": "r3",
            },
            "confidentiality": {
                "test_method": "membership-inference-test",
                "resilience_level": "verified-adequate",
                "evidence_ref": "r4",
            },
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    assert "adversarial_posture" in result
    assert result["adversarial_posture"]["overall_adversarial_posture"] == "verified-weak"
    assert result["summary"]["overall_adversarial_posture"] == "verified-weak"


# 4. Missing accuracy for EU high-risk.
def test_missing_accuracy_high_risk_emits_blocking_warning():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["robustness", "cybersecurity"]),
        "evaluation_results": {
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    blockers = [w for w in result["warnings"] if w.startswith("BLOCKING")]
    assert any("'accuracy'" in w for w in blockers)


# 5. Missing backup_plan_ref for EU high-risk.
def test_missing_backup_plan_ref_high_risk_warns():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
    })
    text = " ".join(result["warnings"])
    assert "backup_plan_ref" in text
    assert "Article 15, Paragraph 3" in text
    assert result["backup_plan_status"]["satisfied"] is False


# 6. Missing concept_drift_monitoring_ref with continuous-learning-controls dim.
def test_missing_concept_drift_ref_with_continuous_learning_warns():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True, continuous_learning=True),
        "evaluation_scope": _scope([
            "accuracy", "robustness", "cybersecurity", "continuous-learning-controls",
        ]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
            "continuous-learning-controls": {
                "test_method": "stress-test",
                "resilience_level": "verified-adequate",
                "evidence_ref": "r-cl",
            },
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    text = " ".join(result["warnings"])
    assert "concept_drift_monitoring_ref" in text
    assert "Paragraph 5" in text


# 7. Non-high-risk system.
def test_non_high_risk_system_marks_recommended_not_mandated():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=False),
        "evaluation_scope": _scope(["accuracy"]),
        "evaluation_results": {"accuracy": _accuracy_pass()},
    })
    assert result["art_15_applicability"] == "recommended-not-mandated"
    assert result["summary"]["blocking_warnings"] == 0


# 8. Internal-team independence emits Article 43 note.
def test_internal_team_independence_note():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"], indep="internal-team"),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    assert result["evaluator_independence_note"] is not None
    assert "Article 43" in result["evaluator_independence_note"]


# 9. Third-party audit independence: no note.
def test_third_party_audit_no_note():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"], indep="third-party-audit"),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    assert result["evaluator_independence_note"] is None


# 10. Trend delta against previous evaluation.
def test_trend_delta_computed():
    previous = {
        "dimension_assessments": [
            {"dimension": "accuracy", "metric_value": 0.70, "declared_threshold": 0.75, "pass": False},
            {"dimension": "robustness", "resilience_level": "verified-weak"},
        ]
    }
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),  # 0.82
            "robustness": _robustness_pass(),  # verified-adequate
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
        "previous_evaluation_ref": previous,
    })
    assert "trend_delta" in result
    by_dim = {d["dimension"]: d for d in result["trend_delta"]}
    assert by_dim["accuracy"]["trend"] == "improving"
    assert by_dim["robustness"]["trend"] == "improving"
    assert by_dim["cybersecurity"]["trend"] == "new"


# 11. ValueError on missing system_description.
def test_missing_system_description_raises():
    try:
        plugin.evaluate_robustness({
            "evaluation_scope": _scope(["accuracy"]),
            "evaluation_results": {"accuracy": _accuracy_pass()},
        })
    except ValueError as exc:
        assert "system_description" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 12. ValueError on missing evaluation_scope.
def test_missing_evaluation_scope_raises():
    try:
        plugin.evaluate_robustness({
            "system_description": _system(),
            "evaluation_results": {"accuracy": _accuracy_pass()},
        })
    except ValueError as exc:
        assert "evaluation_scope" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 13. ValueError on missing evaluation_results.
def test_missing_evaluation_results_raises():
    try:
        plugin.evaluate_robustness({
            "system_description": _system(),
            "evaluation_scope": _scope(["accuracy"]),
        })
    except ValueError as exc:
        assert "evaluation_results" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 14. Invalid dimension enum.
def test_invalid_dimension_raises():
    try:
        plugin.evaluate_robustness({
            "system_description": _system(),
            "evaluation_scope": {
                "dimensions": ["not-a-dimension"],
                "evaluation_date": "2026-04-15",
                "evaluator_identity": "x",
                "evaluator_independence": "internal-team",
            },
            "evaluation_results": {},
        })
    except ValueError as exc:
        assert "not-a-dimension" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 15. Invalid test_method.
def test_invalid_test_method_raises():
    try:
        plugin.evaluate_robustness({
            "system_description": _system(),
            "evaluation_scope": _scope(["accuracy"]),
            "evaluation_results": {
                "accuracy": {**_accuracy_pass(), "test_method": "not-a-method"},
            },
        })
    except ValueError as exc:
        assert "test_method" in str(exc)
        return
    raise AssertionError("expected ValueError")


# 16. art_15_2_declaration_status emitted when accuracy evaluated.
def test_art_15_2_declaration_emitted_when_accuracy_evaluated():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    decl = result["art_15_2_declaration_status"]
    assert decl is not None
    assert decl["primary_metric"] == "F1"
    assert decl["metric_value"] == 0.82
    assert decl["declared_threshold"] == 0.75
    assert decl["citation"] == "EU AI Act, Article 15, Paragraph 2"


# 17. Crosswalk default True attaches cross_framework_citations.
def test_crosswalk_default_true_attaches_citations():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    assert "cross_framework_citations" in result
    assert isinstance(result["cross_framework_citations"], list)
    # Must contain at least the Article 15 mappings shipped in crosswalk data.
    refs = [r["source_ref"] for r in result["cross_framework_citations"]]
    assert any("Article 15" in r for r in refs)


# 18. Crosswalk False: key absent.
def test_crosswalk_false_omits_key():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
        "enrich_with_crosswalk": False,
    })
    assert "cross_framework_citations" not in result


# 19. Citation format compliance.
def test_citation_format_compliance():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    for c in result["citations"]:
        assert (
            c.startswith("EU AI Act, Article ")
            or c.startswith("ISO/IEC 42001:2023")
            or c.startswith("MEASURE ")
            or c.startswith("UK ATRS, Section ")
            or c.startswith("Colorado SB 205, Section ")
        ), f"citation {c!r} does not match STYLE.md prefix"
    for a in result["dimension_assessments"]:
        for c in a["citations"]:
            assert (
                c.startswith("EU AI Act, Article ")
                or c.startswith("ISO/IEC 42001:2023")
                or c.startswith("MEASURE ")
            ), f"dimension citation {c!r} does not match STYLE.md prefix"


# 20. No em-dash, emoji, hedging in rendered output.
def test_no_em_dash_emoji_hedging_in_render():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    md = plugin.render_markdown(result)
    assert "\u2014" not in md
    hedging = [
        "may want to consider",
        "might be helpful to",
        "could potentially",
        "it is possible that",
        "you might find",
    ]
    lower = md.lower()
    for h in hedging:
        assert h not in lower


# 21. Markdown has required sections.
def test_render_markdown_required_sections():
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope([
            "accuracy", "robustness", "cybersecurity", "adversarial-robustness",
        ]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
            "adversarial-robustness": {
                "test_method": "red-team-engagement",
                "resilience_level": "verified-adequate",
                "evidence_ref": "r-adv",
            },
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    md = plugin.render_markdown(result)
    for section in (
        "## Scope",
        "## Dimension assessments",
        "## Adversarial posture",
        "## Article 15(2) declaration action",
        "## Backup plan status",
        "## Concept drift status",
        "## Warnings",
    ):
        assert section in md, f"missing section {section!r}"


# 22. CSV row count matches dimension count.
def test_render_csv_row_count_matches_dimensions():
    dims = ["accuracy", "robustness", "cybersecurity", "fail-safe-design"]
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(dims),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
            "fail-safe-design": {
                "test_method": "stress-test",
                "resilience_level": "verified-adequate",
                "evidence_ref": "r-fs",
            },
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    csv_text = plugin.render_csv(result)
    lines = [ln for ln in csv_text.strip().splitlines() if ln.strip()]
    # 1 header + len(dims) rows.
    assert len(lines) == 1 + len(dims)


# 23. Graceful crosswalk failure produces top-level warning, evaluation still produced.
def test_graceful_crosswalk_failure(monkeypatch):
    def boom():
        raise RuntimeError("simulated crosswalk load failure")

    monkeypatch.setattr(plugin, "_load_crosswalk_module", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    result = plugin.evaluate_robustness({
        "system_description": _system(high_risk=True),
        "evaluation_scope": _scope(["accuracy", "robustness", "cybersecurity"]),
        "evaluation_results": {
            "accuracy": _accuracy_pass(),
            "robustness": _robustness_pass(),
            "cybersecurity": _cybersecurity_pass(),
        },
        "backup_plan_ref": "docs/fail-safe.pdf",
    })
    assert any("Crosswalk enrichment skipped" in w for w in result["warnings"])
    # Evaluation still produced with all required fields.
    assert "dimension_assessments" in result
    assert result["summary"]["dimensions_evaluated"] == 3


def _run_all():
    import inspect

    tests = [
        (n, o)
        for n, o in inspect.getmembers(sys.modules[__name__])
        if n.startswith("test_") and callable(o)
    ]
    failures = []

    class _MP:
        def __init__(self):
            self._undo = []

        def setattr(self, target, name, value):
            old = getattr(target, name)
            self._undo.append(lambda t=target, n=name, o=old: setattr(t, n, o))
            setattr(target, name, value)

        def undo(self):
            for u in self._undo:
                u()

    for name, fn in tests:
        try:
            sig = inspect.signature(fn)
            if "monkeypatch" in sig.parameters:
                mp = _MP()
                try:
                    fn(mp)
                finally:
                    mp.undo()
            else:
                fn()
        except Exception as exc:
            failures.append((name, f"{type(exc).__name__}: {exc}"))
    print(f"Ran {len(tests)} tests: {len(tests) - len(failures)} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
