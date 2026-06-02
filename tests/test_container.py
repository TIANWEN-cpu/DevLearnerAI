"""Tests for app.utils.container -- Dependency injection container."""

import threading
from unittest.mock import MagicMock

import pytest

from app.utils.container import (
    Container,
    Depends,
    get_container,
    inject,
    set_container,
)


class TestContainer:
    """Test Container registration and resolution."""

    def setup_method(self):
        self.container = Container()

    def test_register_and_resolve_instance(self):
        instance = {"key": "value"}
        self.container.register_instance("config", instance)
        assert self.container.resolve("config") is instance

    def test_register_and_resolve_factory(self):
        self.container.register_factory("db", lambda: {"type": "sqlite"})
        result = self.container.resolve("db")
        assert result == {"type": "sqlite"}

    def test_factory_creates_new_instance_each_time(self):
        call_count = [0]

        def factory():
            call_count[0] += 1
            return {"call": call_count[0]}

        self.container.register_factory("svc", factory, singleton=False)
        r1 = self.container.resolve("svc")
        r2 = self.container.resolve("svc")
        assert r1 is not r2
        assert call_count[0] == 2

    def test_singleton_factory(self):
        call_count = [0]

        def factory():
            call_count[0] += 1
            return {"call": call_count[0]}

        self.container.register_factory("svc", factory, singleton=True)
        r1 = self.container.resolve("svc")
        r2 = self.container.resolve("svc")
        assert r1 is r2
        assert call_count[0] == 1

    def test_register_class(self):
        self.container.register_class("mock", MagicMock, singleton=False)
        result = self.container.resolve("mock")
        assert isinstance(result, MagicMock)

    def test_register_class_singleton(self):
        self.container.register_class("mock", MagicMock, singleton=True)
        r1 = self.container.resolve("mock")
        r2 = self.container.resolve("mock")
        assert r1 is r2

    def test_resolve_unregistered_raises(self):
        with pytest.raises(KeyError, match="未注册"):
            self.container.resolve("nonexistent")

    def test_resolve_or_none(self):
        assert self.container.resolve_or_none("missing") is None
        self.container.register_instance("existing", 42)
        assert self.container.resolve_or_none("existing") == 42

    def test_resolve_or_default(self):
        assert self.container.resolve_or_default("missing", "fallback") == "fallback"
        self.container.register_instance("existing", 42)
        assert self.container.resolve_or_default("existing") == 42

    def test_resolve_type(self):
        self.container.register_instance("db", MagicMock())
        result = self.container.resolve_type("db", MagicMock)
        assert isinstance(result, MagicMock)

    def test_resolve_type_mismatch_raises(self):
        self.container.register_instance("db", "not_a_mock")
        with pytest.raises(TypeError, match="类型不匹配"):
            self.container.resolve_type("db", MagicMock)

    def test_unregister(self):
        self.container.register_instance("svc", 42)
        assert self.container.is_registered("svc")
        self.container.unregister("svc")
        assert not self.container.is_registered("svc")

    def test_unregister_nonexistent(self):
        self.container.unregister("missing")  # should not raise

    def test_is_registered(self):
        assert not self.container.is_registered("svc")
        self.container.register_instance("svc", 42)
        assert self.container.is_registered("svc")

    def test_registered_names(self):
        self.container.register_instance("a", 1)
        self.container.register_instance("b", 2)
        names = self.container.registered_names()
        assert set(names) == {"a", "b"}

    def test_registered_count(self):
        assert self.container.registered_count() == 0
        self.container.register_instance("a", 1)
        self.container.register_instance("b", 2)
        assert self.container.registered_count() == 2

    def test_cached_singleton_names(self):
        self.container.register_factory("svc", lambda: object(), singleton=True)
        assert len(self.container.cached_singleton_names()) == 0
        self.container.resolve("svc")
        assert "svc" in self.container.cached_singleton_names()

    def test_tags(self):
        self.container.register_instance("db1", "a", tags=["database", "primary"])
        self.container.register_instance("db2", "b", tags=["database"])
        self.container.register_instance("cache", "c", tags=["cache"])
        db_services = self.container.resolve_by_tag("database")
        assert set(db_services.keys()) == {"db1", "db2"}

    def test_clear(self):
        self.container.register_instance("a", 1)
        self.container.register_factory("b", lambda: 2, singleton=True)
        self.container.resolve("b")  # cache it
        self.container.clear()
        assert self.container.registered_count() == 0
        assert len(self.container.cached_singleton_names()) == 0

    def test_reset_singletons(self):
        call_count = [0]

        def factory():
            call_count[0] += 1
            return call_count[0]

        self.container.register_factory("svc", factory, singleton=True)
        assert self.container.resolve("svc") == 1
        self.container.reset_singletons()
        assert self.container.resolve("svc") == 2

    def test_thread_safety(self):
        self.container.register_factory("counter", lambda: object(), singleton=True)
        results = []
        lock = threading.Lock()

        def resolve_it():
            result = self.container.resolve("counter")
            with lock:
                results.append(id(result))

        threads = [threading.Thread(target=resolve_it) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Singleton should return same instance from all threads
        assert len(set(results)) == 1


class TestDepends:
    """Test Depends descriptor."""

    def test_creation(self):
        d = Depends("db")
        assert d.service_name == "db"
        # Default is the module-level sentinel
        from app.utils.container import _SENTINEL

        assert d.default is _SENTINEL

    def test_with_default(self):
        d = Depends("db", default=None)
        assert d.default is None

    def test_repr(self):
        d = Depends("my_svc")
        assert "my_svc" in repr(d)


class TestInject:
    """Test inject decorator."""

    def test_basic_injection(self):
        container = Container()
        container.register_instance("db", "mock_db")
        set_container(container)

        @inject
        def create_widget(db=Depends("db")):  # noqa: B008
            return f"widget_with_{db}"

        result = create_widget()
        assert result == "widget_with_mock_db"

    def test_explicit_arg_overrides_injection(self):
        container = Container()
        container.register_instance("db", "injected_db")
        set_container(container)

        @inject
        def create_widget(db=Depends("db")):  # noqa: B008
            return f"widget_with_{db}"

        result = create_widget(db="explicit_db")
        assert result == "widget_with_explicit_db"

    def test_missing_dependency_uses_default(self):
        container = Container()
        set_container(container)

        @inject
        def func(db=Depends("missing", default="fallback")):  # noqa: B008
            return db

        result = func()
        assert result == "fallback"

    def test_preserves_function_name(self):
        @inject
        def my_function(x=Depends("x")):  # noqa: B008
            pass

        assert my_function.__name__ == "my_function"

    def test_cleanup(self):
        """Reset global container to avoid test pollution."""
        set_container(Container())


class TestGlobalContainer:
    """Test global container functions."""

    def test_get_container_creates_default(self):
        from app.utils import container as container_mod

        container_mod._default_container = None
        c = get_container()
        assert isinstance(c, Container)
        # cleanup
        container_mod._default_container = None

    def test_set_container(self):
        custom = Container()
        custom.register_instance("test", 42)
        set_container(custom)
        assert get_container().resolve("test") == 42
        # cleanup
        set_container(Container())
