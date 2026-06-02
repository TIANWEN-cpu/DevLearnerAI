"""Tests for app.utils.plugins -- Plugin architecture."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.utils.plugins import (
    Plugin,
    PluginInfo,
    PluginManager,
    PluginState,
    discover_plugins,
)

# ---------------------------------------------------------------------------
# Test plugin implementations
# ---------------------------------------------------------------------------


class SimplePlugin(Plugin):
    """A minimal test plugin."""

    def __init__(self, name: str = "simple", version: str = "1.0.0"):
        self._name = name
        self._version = version
        self.loaded = False
        self.readied = False
        self.unloaded = False
        self.app_ref = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def description(self) -> str:
        return "A test plugin"

    def on_load(self, app) -> None:
        self.loaded = True
        self.app_ref = app

    def on_ready(self, app) -> None:
        self.readied = True

    def on_unload(self, app) -> None:
        self.unloaded = True


class FailingPlugin(Plugin):
    """A plugin that fails on load."""

    @property
    def name(self) -> str:
        return "failing"

    def on_load(self, app) -> None:
        raise RuntimeError("load failure")


class DependentPlugin(Plugin):
    """A plugin that depends on another."""

    def __init__(self, deps: list[str] | None = None, name: str = "dependent"):
        self._deps = deps or []
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def dependencies(self) -> list[str]:
        return self._deps


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPluginInterface:
    """Test Plugin abstract interface."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Plugin()

    def test_simple_plugin_defaults(self):
        p = SimplePlugin()
        assert p.name == "simple"
        assert p.version == "1.0.0"
        assert p.description == "A test plugin"
        assert p.author == ""
        assert p.dependencies == []

    def test_repr(self):
        p = SimplePlugin()
        r = repr(p)
        assert "simple" in r
        assert "1.0.0" in r


class TestPluginState:
    """Test PluginState enum."""

    def test_all_states_exist(self):
        assert PluginState.REGISTERED.value == "registered"
        assert PluginState.LOADING.value == "loading"
        assert PluginState.LOADED.value == "loaded"
        assert PluginState.READY.value == "ready"
        assert PluginState.UNLOADING.value == "unloading"
        assert PluginState.UNLOADED.value == "unloaded"
        assert PluginState.ERROR.value == "error"


class TestPluginInfo:
    """Test PluginInfo metadata wrapper."""

    def test_initial_state(self):
        plugin = SimplePlugin()
        info = PluginInfo(plugin)
        assert info.state == PluginState.REGISTERED
        assert info.error is None
        assert info.is_healthy

    def test_healthy_states(self):
        info = PluginInfo(SimplePlugin())
        info.state = PluginState.LOADED
        assert info.is_healthy
        info.state = PluginState.ERROR
        assert not info.is_healthy
        info.state = PluginState.UNLOADED
        assert not info.is_healthy

    def test_name_property(self):
        info = PluginInfo(SimplePlugin(name="test"))
        assert info.name == "test"


class TestPluginManager:
    """Test PluginManager."""

    def setup_method(self):
        self.pm = PluginManager()
        self.app = MagicMock()

    def test_register_and_count(self):
        assert self.pm.count == 0
        self.pm.register(SimplePlugin())
        assert self.pm.count == 1

    def test_register_duplicate_raises(self):
        self.pm.register(SimplePlugin("dup"))
        with pytest.raises(ValueError, match="已注册"):
            self.pm.register(SimplePlugin("dup"))

    def test_register_many(self):
        plugins = [SimplePlugin("a"), SimplePlugin("b"), SimplePlugin("c")]
        self.pm.register_many(plugins)
        assert self.pm.count == 3

    def test_register_many_skips_duplicates(self):
        self.pm.register(SimplePlugin("dup"))
        self.pm.register_many([SimplePlugin("dup"), SimplePlugin("new")])
        assert self.pm.count == 2

    def test_unregister(self):
        self.pm.register(SimplePlugin("test"))
        self.pm.unregister("test")
        assert self.pm.count == 0

    def test_unregister_nonexistent(self):
        self.pm.unregister("missing")  # should not raise

    def test_unregister_loaded_raises(self):
        self.pm.register(SimplePlugin("test"))
        self.pm.load_all(self.app)
        with pytest.raises(ValueError, match="无法注销"):
            self.pm.unregister("test")

    def test_get(self):
        p = SimplePlugin()
        self.pm.register(p)
        assert self.pm.get("simple") is p
        assert self.pm.get("missing") is None

    def test_get_info(self):
        self.pm.register(SimplePlugin())
        info = self.pm.get_info("simple")
        assert info is not None
        assert info.name == "simple"

    def test_all_plugins(self):
        self.pm.register(SimplePlugin("a"))
        self.pm.register(SimplePlugin("b"))
        all_p = self.pm.all_plugins()
        assert len(all_p) == 2

    def test_healthy_plugins(self):
        self.pm.register(SimplePlugin("a"))
        self.pm.register(FailingPlugin())
        self.pm.load_all(self.app)
        healthy = self.pm.healthy_plugins()
        assert len(healthy) == 1
        assert healthy[0].name == "a"

    def test_load_all_calls_on_load(self):
        p = SimplePlugin()
        self.pm.register(p)
        self.pm.load_all(self.app)
        assert p.loaded
        assert p.app_ref is self.app
        assert self.pm.is_loaded

    def test_ready_all_calls_on_ready(self):
        p = SimplePlugin()
        self.pm.register(p)
        self.pm.load_all(self.app)
        self.pm.ready_all(self.app)
        assert p.readied
        assert self.pm.is_ready

    def test_unload_all_calls_on_unload(self):
        p = SimplePlugin()
        self.pm.register(p)
        self.pm.load_all(self.app)
        self.pm.unload_all(self.app)
        assert p.unloaded
        assert not self.pm.is_loaded

    def test_failing_plugin_marks_error(self):
        self.pm.register(FailingPlugin())
        loaded = self.pm.load_all(self.app)
        assert loaded == []
        info = self.pm.get_info("failing")
        assert info.state == PluginState.ERROR
        assert info.error is not None

    def test_dependency_resolution(self):
        base = SimplePlugin("base")
        dep = DependentPlugin(deps=["base"])
        # Register in wrong order (dep first)
        self.pm.register(dep)
        self.pm.register(base)
        loaded = self.pm.load_all(self.app)
        # base should be loaded before dependent
        assert loaded.index("base") < loaded.index("dependent")

    def test_circular_dependency_raises(self):
        p1 = DependentPlugin(deps=["b"], name="a")
        p2 = DependentPlugin(deps=["a"], name="b")
        self.pm.register(p1)
        self.pm.register(p2)
        loaded = self.pm.load_all(self.app)
        assert loaded == []  # Should fail gracefully

    def test_missing_dependency_raises(self):
        dep = DependentPlugin(deps=["missing"])
        self.pm.register(dep)
        loaded = self.pm.load_all(self.app)
        assert loaded == []

    def test_status_summary(self):
        self.pm.register(SimplePlugin("ok"))
        self.pm.register(FailingPlugin())
        self.pm.load_all(self.app)
        summary = self.pm.status_summary()
        assert summary["ok"]["state"] == "loaded"
        assert summary["failing"]["state"] == "error"

    def test_load_from_directory_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loaded = self.pm.load_from_directory(Path(tmpdir), self.app)
            assert loaded == []

    def test_load_from_directory_nonexistent(self):
        loaded = self.pm.load_from_directory(Path("/nonexistent"), self.app)
        assert loaded == []

    def test_load_from_directory_with_plugin_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_code = """
from app.utils.plugins import Plugin

class TestDirPlugin(Plugin):
    @property
    def name(self):
        return "dir_plugin"
    def on_load(self, app):
        pass
"""
            plugin_file = Path(tmpdir) / "test_plugin.py"
            plugin_file.write_text(plugin_code, encoding="utf-8")

            loaded = self.pm.load_from_directory(Path(tmpdir), self.app)
            assert "dir_plugin" in loaded


class TestDiscoverPlugins:
    """Test plugin discovery functions."""

    def test_discover_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins = discover_plugins(Path(tmpdir))
            assert plugins == []

    def test_discover_nonexistent_directory(self):
        plugins = discover_plugins(Path("/nonexistent"))
        assert plugins == []

    def test_discover_ignores_underscore_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "_private.py").write_text("# skip", encoding="utf-8")
            plugins = discover_plugins(Path(tmpdir))
            assert plugins == []

    def test_discover_finds_plugin_class(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code = """
from app.utils.plugins import Plugin

class FoundPlugin(Plugin):
    @property
    def name(self):
        return "found"
"""
            (Path(tmpdir) / "found.py").write_text(code, encoding="utf-8")
            plugins = discover_plugins(Path(tmpdir))
            assert len(plugins) == 1
            assert plugins[0].name == "found"

    def test_discover_skips_broken_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Valid plugin
            code = """
from app.utils.plugins import Plugin
class GoodPlugin(Plugin):
    @property
    def name(self):
        return "good"
"""
            (Path(tmpdir) / "good.py").write_text(code, encoding="utf-8")
            # Broken file
            (Path(tmpdir) / "bad.py").write_text("import nonexistent_module_xyz", encoding="utf-8")
            plugins = discover_plugins(Path(tmpdir))
            assert len(plugins) == 1
            assert plugins[0].name == "good"
