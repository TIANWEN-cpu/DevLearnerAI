"""Tests for app.python_runner -- sandbox safety boundaries.

These tests exercise the pure / side-effect-free helpers that form the
security boundary of the code-execution sandbox:

- ``_validate_code_safety`` -- AST pre-check
- ``LimitedBuffer``       -- stdout truncation
- ``_safe_import``        -- module whitelist
- ``_safe_open_factory``  -- path-escape rejection
"""

import tempfile
from pathlib import Path

import pytest

from app.python_runner import (
    ALLOWED_IMPORTS,
    LimitedBuffer,
    _safe_import,
    _safe_open_factory,
    _validate_code_safety,
)


# ---------------------------------------------------------------------------
# _validate_code_safety
# ---------------------------------------------------------------------------
class TestValidateCodeSafety:
    """AST-based safety checks on user-submitted code."""

    # -- safe code passes ------------------------------------------------

    def test_simple_print_passes(self):
        result = _validate_code_safety("print('hello')")
        assert result is None

    def test_arithmetic_passes(self):
        result = _validate_code_safety("x = 1 + 2\nprint(x)")
        assert result is None

    def test_function_def_passes(self):
        code = "def add(a, b):\n    return a + b\nprint(add(1, 2))"
        result = _validate_code_safety(code)
        assert result is None

    def test_list_comprehension_passes(self):
        result = _validate_code_safety("result = [x * 2 for x in range(5)]\nprint(result)")
        assert result is None

    # -- import statements blocked ---------------------------------------

    def test_import_os_blocked(self):
        with pytest.raises(SyntaxError, match="不允许使用 import"):
            _validate_code_safety("import os")

    def test_import_from_blocked(self):
        with pytest.raises(SyntaxError, match="不允许使用 import"):
            _validate_code_safety("from os import system")

    def test_import_sys_blocked(self):
        with pytest.raises(SyntaxError, match="不允许使用 import"):
            _validate_code_safety("import sys")

    # -- dangerous builtins calls blocked --------------------------------

    def test_eval_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 eval"):
            _validate_code_safety("eval('1+1')")

    def test_exec_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 exec"):
            _validate_code_safety("exec('print(1)')")

    def test_compile_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 compile"):
            _validate_code_safety("compile('1', '<s>', 'eval')")

    def test_getattr_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 getattr"):
            _validate_code_safety("getattr(object, '__class__')")

    def test_type_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 type"):
            _validate_code_safety("type('X', (), {})")

    # -- dangerous dunder attribute access blocked -----------------------

    def test_dunder_class_blocked(self):
        with pytest.raises(SyntaxError, match="不允许访问属性 __class__"):
            _validate_code_safety("x = object().__class__")

    def test_dunder_builtins_string_attr_blocked(self):
        """Accessing __builtins__ via attribute on an object is blocked."""
        with pytest.raises(SyntaxError, match="不允许访问属性 __builtins__"):
            _validate_code_safety("x = obj.__builtins__")

    def test_dunder_builtins_string_reference_blocked(self):
        """The string '__builtins__' appearing in a string constant is blocked."""
        with pytest.raises(SyntaxError, match="敏感双下划线"):
            _validate_code_safety("s = '__builtins__'")

    def test_dunder_subclasses_blocked(self):
        with pytest.raises(SyntaxError, match="不允许访问属性 __subclasses__"):
            _validate_code_safety("x = object.__subclasses__")

    # -- string-based __builtins__ reference blocked ---------------------

    def test_string_builtins_reference_blocked(self):
        with pytest.raises(SyntaxError, match="敏感双下划线"):
            _validate_code_safety("s = '__builtins__'")

    def test_string_import_reference_blocked(self):
        with pytest.raises(SyntaxError, match="敏感双下划线"):
            _validate_code_safety("s = '__import__'")


# ---------------------------------------------------------------------------
# LimitedBuffer
# ---------------------------------------------------------------------------
class TestLimitedBuffer:
    """Stdout truncation buffer."""

    def test_within_limit(self):
        buf = LimitedBuffer(limit=100)
        buf.write("hello")
        assert buf.getvalue() == "hello"

    def test_exactly_at_limit(self):
        buf = LimitedBuffer(limit=5)
        buf.write("abcde")
        assert buf.getvalue() == "abcde"

    def test_exceeds_limit_raises(self):
        buf = LimitedBuffer(limit=5)
        with pytest.raises(RuntimeError, match="截断"):
            buf.write("abcdef")

    def test_multiple_writes_until_limit(self):
        buf = LimitedBuffer(limit=10)
        buf.write("aaaa")  # 4
        buf.write("bbbb")  # 8
        with pytest.raises(RuntimeError, match="截断"):
            buf.write("ccc")  # would exceed 10

    def test_default_limit(self):
        buf = LimitedBuffer()
        assert buf.limit == 12000


# ---------------------------------------------------------------------------
# _safe_import
# ---------------------------------------------------------------------------
class TestSafeImport:
    """Module-import whitelist enforcement."""

    @pytest.mark.parametrize("module_name", sorted(ALLOWED_IMPORTS))
    def test_allowed_modules_importable(self, module_name):
        """Every module in the whitelist should be importable."""
        result = _safe_import(module_name)
        assert result is not None

    def test_blocked_os(self):
        with pytest.raises(ImportError, match="不允许导入"):
            _safe_import("os")

    def test_blocked_sys(self):
        with pytest.raises(ImportError, match="不允许导入"):
            _safe_import("sys")

    def test_blocked_subprocess(self):
        with pytest.raises(ImportError, match="不允许导入"):
            _safe_import("subprocess")

    def test_blocked_shutil(self):
        with pytest.raises(ImportError, match="不允许导入"):
            _safe_import("shutil")

    def test_blocked_socket(self):
        with pytest.raises(ImportError, match="不允许导入"):
            _safe_import("socket")


# ---------------------------------------------------------------------------
# _safe_open_factory
# ---------------------------------------------------------------------------
class TestSafeOpenFactory:
    """Path-escape rejection for sandboxed file operations."""

    def test_relative_path_allowed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            test_file = workdir / "hello.txt"
            test_file.write_text("ok", encoding="utf-8")
            safe_open = _safe_open_factory(workdir)
            with safe_open("hello.txt") as f:
                assert f.read() == "ok"

    def test_absolute_escape_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            safe_open = _safe_open_factory(workdir)
            with pytest.raises(PermissionError, match="临时工作目录"):
                safe_open("/etc/passwd")

    def test_relative_escape_with_dotdot_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            safe_open = _safe_open_factory(workdir)
            with pytest.raises(PermissionError, match="临时工作目录"):
                safe_open("../../etc/passwd")

    def test_write_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            safe_open = _safe_open_factory(workdir)
            with safe_open("subdir/nested/file.txt", "w") as f:
                f.write("created")
            assert (workdir / "subdir" / "nested" / "file.txt").read_text() == "created"
