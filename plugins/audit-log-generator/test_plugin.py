import importlib.util
import sys
import pytest
from pathlib import Path

# Load the plugin module dynamically since its path contains hyphens
# Use an absolute path relative to this file to ensure it works regardless of pytest's execution directory
current_dir = Path(__file__).parent
plugin_path = current_dir / "plugin.py"

spec = importlib.util.spec_from_file_location("plugin", str(plugin_path))
plugin = importlib.util.module_from_spec(spec)
sys.modules["plugin"] = plugin
spec.loader.exec_module(plugin)

def test_generate_audit_log_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="Implementation in Phase 3"):
        plugin.generate_audit_log({})

def test_map_to_annex_a_controls_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="Implementation in Phase 3"):
        plugin.map_to_annex_a_controls({})
