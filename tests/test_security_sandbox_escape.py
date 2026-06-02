"""Sandbox escape attempt tests for app.python_runner.

Tests known Python sandbox escape techniques including:
- __class__.__bases__ chain traversal
- type() reconstruction
- import via __import__
- eval/exec within user code
- file system access attempts
- network access attempts
- indirect attribute access tricks
"""

import pytest

from app.python_runner import (
    _safe_import,
    _safe_open_factory,
    _validate_code_safety,
)


# ---------------------------------------------------------------------------
# __class__.__bases__ chain attacks
# ---------------------------------------------------------------------------
class TestClassBasesChainEscape:
    """Test classic Python sandbox escape via __class__.__bases__ chain."""

    def test_dunder_class_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = ''.__class__")

    def test_dunder_bases_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = ''.__bases__")

    def test_dunder_subclasses_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = ''.__class__.__bases__[0].__subclasses__()")

    def test_dunder_mro_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = ''.__mro__")

    def test_chained_dunder_class_bases_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = ().__class__.__bases__[0]")

    def test_object_subclasses_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = object.__subclasses__")

    def test_type_bases_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = type.__bases__")

    def test_literal_string_bases_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = str.__bases__")

    def test_dunder_globals_via_func_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = [].__class__.__bases__[0].__subclasses__()[0].__init__.__globals__")

    def test_dunder_code_via_func_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = print.__code__")


# ---------------------------------------------------------------------------
# type() reconstruction attacks
# ---------------------------------------------------------------------------
class TestTypeReconstructionEscape:
    """Test escape via type() reconstruction to get arbitrary class access."""

    def test_type_call_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = type('X', (), {})")

    def test_type_from_bases_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = type('C', (object,), {})")

    def test_type_of_object_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = type(object)")

    def test_object_call_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = object()")

    def test_type_name_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = type.__name__")


# ---------------------------------------------------------------------------
# import via __import__ attacks
# ---------------------------------------------------------------------------
class TestImportViaDunderImport:
    """Test escape via __import__ builtin."""

    def test_dunder_import_string_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("s = '__import__'")

    def test_dunder_import_attr_blocked(self):
        """__import__() passes AST check but is blocked at runtime by _safe_import."""
        # Verify _safe_import blocks os module
        with pytest.raises(ImportError):
            _safe_import("os")

    def test_import_statement_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import os")

    def test_import_from_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("from os import system")

    def test_import_subprocess_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import subprocess")

    def test_import_shutil_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import shutil")

    def test_import_socket_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import socket")

    def test_import_ctypes_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import ctypes")

    def test_import_sys_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import sys")

    def test_import_io_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import io")

    def test_safe_import_blocks_os(self):
        with pytest.raises(ImportError):
            _safe_import("os")

    def test_safe_import_blocks_sys(self):
        with pytest.raises(ImportError):
            _safe_import("sys")

    def test_safe_import_blocks_subprocess(self):
        with pytest.raises(ImportError):
            _safe_import("subprocess")

    def test_safe_import_blocks_socket(self):
        with pytest.raises(ImportError):
            _safe_import("socket")

    def test_safe_import_blocks_ctypes(self):
        with pytest.raises(ImportError):
            _safe_import("ctypes")

    def test_safe_import_blocks_shutil(self):
        with pytest.raises(ImportError):
            _safe_import("shutil")


# ---------------------------------------------------------------------------
# eval/exec within user code
# ---------------------------------------------------------------------------
class TestEvalExecEscape:
    """Test that eval/exec/compile are blocked in user code."""

    def test_eval_call_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("eval('1+1')")

    def test_exec_call_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("exec('print(1)')")

    def test_compile_call_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("compile('1', '<s>', 'eval')")

    def test_eval_in_runtime_is_blocked(self):
        """eval() is blocked by AST safety check."""
        with pytest.raises(SyntaxError):
            _validate_code_safety("eval('1+1')")

    def test_exec_in_runtime_is_blocked(self):
        """exec() is blocked by AST safety check."""
        with pytest.raises(SyntaxError):
            _validate_code_safety("exec('print(1)')")

    def test_compile_in_runtime_is_blocked(self):
        """compile() is blocked by AST safety check."""
        with pytest.raises(SyntaxError):
            _validate_code_safety("compile('1', '<s>', 'eval')")


# ---------------------------------------------------------------------------
# File system access attempts
# ---------------------------------------------------------------------------
class TestFileSystemAccessEscape:
    """Test that file system access is restricted."""

    def test_open_sandboxed_to_workdir(self):
        """Opening system files passes AST check but is blocked at runtime by _safe_open_factory."""
        _validate_code_safety("f = open('test.txt')\nprint(f.read())")

    def test_open_dotdot_escape_blocked(self):
        """Path traversal is blocked by _safe_open_factory."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            safe_open = _safe_open_factory(workdir)
            with pytest.raises(PermissionError):
                safe_open("../../etc/passwd")

    def test_open_windows_system_path_blocked(self):
        """Absolute system paths are blocked by _safe_open_factory."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            safe_open = _safe_open_factory(workdir)
            with pytest.raises(PermissionError):
                safe_open("C:\\Windows\\System32\\drivers\\etc\\hosts")

    def test_safe_open_blocks_absolute_escape(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            safe_open = _safe_open_factory(workdir)
            with pytest.raises(PermissionError):
                safe_open("/etc/passwd")

    def test_safe_open_blocks_dotdot_escape(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            safe_open = _safe_open_factory(workdir)
            with pytest.raises(PermissionError):
                safe_open("../../../etc/passwd")

    def test_safe_open_allows_workdir_files(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            (workdir / "test.txt").write_text("ok", encoding="utf-8")
            safe_open = _safe_open_factory(workdir)
            with safe_open("test.txt") as f:
                assert f.read() == "ok"


# ---------------------------------------------------------------------------
# Network access attempts
# ---------------------------------------------------------------------------
class TestNetworkAccessEscape:
    """Test that network access is blocked."""

    def test_import_socket_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import socket")

    def test_import_urllib_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import urllib")

    def test_import_http_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import http")

    def test_import_ftplib_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import ftplib")

    def test_import_smtplib_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import smtplib")

    def test_import_requests_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("import requests")

    def test_safe_import_blocks_socket(self):
        with pytest.raises(ImportError):
            _safe_import("socket")

    def test_safe_import_blocks_urllib(self):
        with pytest.raises(ImportError):
            _safe_import("urllib")

    def test_safe_import_blocks_http(self):
        with pytest.raises(ImportError):
            _safe_import("http")


# ---------------------------------------------------------------------------
# Indirect / obfuscated escape attempts
# ---------------------------------------------------------------------------
class TestIndirectEscapeAttempts:
    """Test indirect and obfuscated sandbox escape techniques."""

    def test_getattr_with_dunder_string_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("getattr(obj, '__class__')")

    def test_hasattr_with_dunder_string_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("hasattr(obj, '__class__')")

    def test_setattr_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("setattr(obj, 'name', 1)")

    def test_delattr_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("delattr(obj, 'name')")

    def test_dir_call_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("dir(obj)")

    def test_vars_call_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("vars(obj)")

    def test_globals_call_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("globals()")

    def test_locals_call_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("locals()")

    def test_breakpoint_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("breakpoint()")

    def test_bytearray_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("bytearray(5)")

    def test_memoryview_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("memoryview(b'abc')")

    def test_dunder_builtins_string_reference_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("s = '__builtins__'")

    def test_dunder_globals_attr_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = obj.__globals__")

    def test_dunder_loader_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = obj.__loader__")

    def test_dunder_spec_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = obj.__spec__")

    def test_dunder_file_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = obj.__file__")

    def test_dunder_self_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = obj.__self__")

    def test_dunder_func_blocked(self):
        with pytest.raises(SyntaxError):
            _validate_code_safety("x = obj.__func__")


# ---------------------------------------------------------------------------
# Additional DANGEROUS_ATTRS coverage
# ---------------------------------------------------------------------------
class TestDangerousDunderMethods:
    """Ensure all dunder methods in _DANGEROUS_ATTRS are blocked."""

    @pytest.mark.parametrize(
        "dunder_attr",
        [
            "__class__",
            "__bases__",
            "__subclasses__",
            "__mro__",
            "__builtins__",
            "__globals__",
            "__code__",
            "__import__",
            "__loader__",
            "__spec__",
            "__file__",
            "__name__",
            "__self__",
            "__func__",
            "__qualname__",
            "__module__",
        ],
    )
    def test_dangerous_dunder_blocked(self, dunder_attr):
        with pytest.raises(SyntaxError):
            _validate_code_safety(f"x = obj.{dunder_attr}")
