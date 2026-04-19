"""Audit tests for plugins/rmf-function-map.yaml.

Cross-checks the NIST AI RMF four-function tagging catalogue against the
plugin directories on disk. Runs under pytest or standalone.

Invariants enforced:

1. YAML parses cleanly.
2. Top-level ``functions:`` dict has exactly the four canonical keys
   ``govern``, ``map``, ``measure``, ``manage``.
3. Every plugin directory under ``plugins/`` (excluding the
   ``crosswalk-matrix-builder/data/`` subtree and non-plugin files)
   appears as a key under ``plugin_tags``.
4. Every key under ``plugin_tags`` corresponds to a real plugin
   directory.
5. Every ``primary`` value is contained in that plugin's ``functions``
   list.
6. Every value inside any plugin's ``functions`` list is a key in the
   top-level ``functions:`` dict.

Citation source: NIST AI Risk Management Framework 1.0, Section 5.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml  # PyYAML is the single extra dependency beyond stdlib.

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGINS_DIR = REPO_ROOT / "plugins"
MAP_PATH = PLUGINS_DIR / "rmf-function-map.yaml"

CANONICAL_FUNCTIONS = {"govern", "map", "measure", "manage"}


def _load_map() -> dict:
    with MAP_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _plugin_dirs_on_disk() -> set[str]:
    """Return the set of real plugin directory names on disk.

    Excludes the ``crosswalk-matrix-builder/data/`` subtree (not a
    plugin) and any top-level non-directory files.
    """
    names: set[str] = set()
    for entry in PLUGINS_DIR.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("_") or entry.name.startswith("."):
            continue
        names.add(entry.name)
    return names


# Test 1: YAML parses cleanly and has the expected top-level shape.
def test_rmf_function_map_yaml_parses():
    data = _load_map()
    assert isinstance(data, dict), "top-level YAML must be a mapping"
    assert "functions" in data, "missing top-level 'functions' dict"
    assert "plugin_tags" in data, "missing top-level 'plugin_tags' dict"
    assert isinstance(data["functions"], dict)
    assert isinstance(data["plugin_tags"], dict)


# Test 2: The four canonical function keys are present and no others.
def test_rmf_function_map_has_four_canonical_functions():
    data = _load_map()
    keys = set(data["functions"].keys())
    assert keys == CANONICAL_FUNCTIONS, (
        f"functions keys must equal {CANONICAL_FUNCTIONS}; got {keys}"
    )
    # Each function entry must carry description + citation.
    for fn, spec in data["functions"].items():
        assert "description" in spec, f"function {fn!r} missing description"
        assert "citation" in spec, f"function {fn!r} missing citation"
        assert spec["citation"].startswith("NIST AI RMF 1.0, Section 5"), (
            f"function {fn!r} citation must cite NIST AI RMF 1.0, Section 5; "
            f"got {spec['citation']!r}"
        )


# Test 3: Every plugin directory on disk is tagged in plugin_tags.
def test_every_plugin_directory_is_tagged():
    data = _load_map()
    on_disk = _plugin_dirs_on_disk()
    tagged = set(data["plugin_tags"].keys())
    missing = on_disk - tagged
    assert not missing, (
        f"plugin directories on disk not tagged in rmf-function-map.yaml: "
        f"{sorted(missing)}"
    )


# Test 4: Every plugin_tags entry corresponds to a real directory.
def test_every_tag_entry_has_directory():
    data = _load_map()
    on_disk = _plugin_dirs_on_disk()
    tagged = set(data["plugin_tags"].keys())
    orphan = tagged - on_disk
    assert not orphan, (
        f"plugin_tags entries with no matching directory under plugins/: "
        f"{sorted(orphan)}"
    )


# Test 5: Every 'primary' value is in that plugin's functions list.
def test_primary_is_in_functions_list():
    data = _load_map()
    offenders: list[str] = []
    for plugin_name, spec in data["plugin_tags"].items():
        primary = spec.get("primary")
        functions = spec.get("functions", [])
        if primary is None:
            offenders.append(f"{plugin_name}: missing 'primary'")
            continue
        if not isinstance(functions, list) or not functions:
            offenders.append(f"{plugin_name}: missing or empty 'functions'")
            continue
        if primary not in functions:
            offenders.append(
                f"{plugin_name}: primary={primary!r} not in functions={functions!r}"
            )
    assert not offenders, "primary/functions invariant violations: " + "; ".join(offenders)


# Test 6: Every function value referenced by any plugin is a canonical key.
def test_plugin_functions_reference_canonical_keys_only():
    data = _load_map()
    canonical = set(data["functions"].keys())
    offenders: list[str] = []
    for plugin_name, spec in data["plugin_tags"].items():
        for fn in spec.get("functions", []):
            if fn not in canonical:
                offenders.append(f"{plugin_name}: unknown function {fn!r}")
        primary = spec.get("primary")
        if primary is not None and primary not in canonical:
            offenders.append(f"{plugin_name}: unknown primary {primary!r}")
    assert not offenders, "canonical-key invariant violations: " + "; ".join(offenders)


def _run_all():
    import inspect
    tests = [
        (n, o) for n, o in inspect.getmembers(sys.modules[__name__])
        if n.startswith("test_") and callable(o)
    ]
    failures: list[tuple[str, str]] = []
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            failures.append((name, f"{type(exc).__name__}: {exc}"))
    print(f"Ran {len(tests)} tests: {len(tests) - len(failures)} passed, {len(failures)} failed")
    for name, reason in failures:
        print(f"  FAIL {name}: {reason}")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    _run_all()
