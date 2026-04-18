import pytest
import sys
import os
import importlib.util

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import from plugin.py directly using importlib as module path has hyphens
plugin_path = os.path.join(os.path.dirname(__file__), "plugin.py")
spec = importlib.util.spec_from_file_location("plugin", plugin_path)
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)

def test_generate_audit_log_not_implemented():
    with pytest.raises(NotImplementedError) as exc_info:
        plugin.generate_audit_log({})
    assert str(exc_info.value) == "Implementation in Phase 3"

def test_map_to_annex_a_controls_not_implemented():
    with pytest.raises(NotImplementedError) as exc_info:
        plugin.map_to_annex_a_controls({})
    assert str(exc_info.value) == "Implementation in Phase 3"
