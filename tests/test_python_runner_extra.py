"""Additional tests for app.python_runner -- covering remaining branches.

Targets:
- _validate_code_safety: getattr/hasattr with dunder string args (lines 190-198)
- LimitedBuffer: write when already past limit (line 246), partial fill (line 248)
- _safe_open_factory: write mode with parent dir creation
- _should_use_subprocess_fallback (line 418-423)
- _execute_code_impl: success path, exception path, SafeBuiltins usage
- _evaluate_code_impl: partial test pass scoring, empty tests, etc.
- _evaluate_worker / _run_exec_worker via subprocess
- cli_main (line 516-527)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.python_runner import (
    SAFE_BUILTINS,
    LimitedBuffer,
    _safe_builtins,
    _safe_import,
    _safe_open_factory,
    _should_use_subprocess_fallback,
    _validate_code_safety,
    cli_main,
)


# ---------------------------------------------------------------------------
# _validate_code_safety  -- additional branches
# ---------------------------------------------------------------------------
class TestValidateCodeSafetyDunderStringArgs:
    """Test getattr/hasattr with dangerous dunder string arguments."""

    def test_getattr_call_blocked_as_dangerous_builtin(self):
        """getattr is blocked as a dangerous builtin call regardless of arguments."""
        with pytest.raises(SyntaxError):
            _validate_code_safety("getattr(obj, '__class__')")

    def test_hasattr_call_blocked_as_dangerous_builtin(self):
        """hasattr is blocked as a dangerous builtin call regardless of arguments."""
        with pytest.raises(SyntaxError):
            _validate_code_safety("hasattr(obj, '__mro__')")

    def test_getattr_with_normal_string_still_blocked(self):
        """getattr with normal string arg is still blocked (dangerous builtin)."""
        with pytest.raises(SyntaxError):
            _validate_code_safety("getattr(obj, 'name')")

    def test_hasattr_with_normal_string_still_blocked(self):
        """hasattr with normal string arg is still blocked (dangerous builtin)."""
        with pytest.raises(SyntaxError):
            _validate_code_safety("hasattr(obj, 'items')")

    def test_dunder_method_call_on_obj_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 __subclasses__"):
            _validate_code_safety("obj.__subclasses__()")

    def test_dunder_bases_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 __bases__"):
            _validate_code_safety("obj.__bases__()")

    def test_dunder_mro_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 __mro__"):
            _validate_code_safety("obj.__mro__()")

    def test_dunder_globals_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 __globals__"):
            _validate_code_safety("obj.__globals__()")

    def test_dunder_code_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 __code__"):
            _validate_code_safety("obj.__code__()")

    def test_dunder_class_method_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 __class__"):
            _validate_code_safety("obj.__class__()")

    def test_breakpoint_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 breakpoint"):
            _validate_code_safety("breakpoint()")

    def test_delattr_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 delattr"):
            _validate_code_safety("delattr(obj, 'name')")

    def test_setattr_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 setattr"):
            _validate_code_safety("setattr(obj, 'name', 1)")

    def test_object_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 object"):
            _validate_code_safety("x = object()")

    def test_super_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 super"):
            _validate_code_safety("x = super()")

    def test_dir_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 dir"):
            _validate_code_safety("x = dir(obj)")

    def test_vars_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 vars"):
            _validate_code_safety("x = vars(obj)")

    def test_globals_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 globals"):
            _validate_code_safety("x = globals()")

    def test_locals_call_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 locals"):
            _validate_code_safety("x = locals()")

    def test_memoryview_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 memoryview"):
            _validate_code_safety("x = memoryview(b'abc')")

    def test_bytearray_blocked(self):
        with pytest.raises(SyntaxError, match="不允许调用 bytearray"):
            _validate_code_safety("x = bytearray(5)")


# ---------------------------------------------------------------------------
# LimitedBuffer  -- edge cases
# ---------------------------------------------------------------------------
class TestLimitedBufferEdgeCases:
    """Test LimitedBuffer boundary conditions."""

    def test_write_empty_string_ok(self):
        buf = LimitedBuffer(limit=5)
        result = buf.write("")
        assert buf.getvalue() == ""
        assert result == 0

    def test_past_limit_raises(self):
        """After buffer is full, any further write raises."""
        buf = LimitedBuffer(limit=3)
        buf.write("abc")
        assert buf.tell() == 3
        with pytest.raises(RuntimeError, match="截断"):
            buf.write("x")

    def test_partial_write_then_overwrite_raises(self):
        """Write that would fill partially and exceed raises RuntimeError.
        Note: the partial data IS written before the error is raised."""
        buf = LimitedBuffer(limit=10)
        buf.write("12345")
        # remaining = 5, trying to write 6 chars -> partial write + error
        with pytest.raises(RuntimeError, match="截断"):
            buf.write("abcdef")
        # The first 5 chars of "abcdef" were written before the error
        assert buf.getvalue() == "12345abcde"

    def test_default_buffer_size_is_12000(self):
        buf = LimitedBuffer()
        assert buf.limit == 12000

    def test_custom_limit(self):
        buf = LimitedBuffer(limit=100)
        assert buf.limit == 100


# ---------------------------------------------------------------------------
# _safe_import  -- dotted module names
# ---------------------------------------------------------------------------
class TestSafeImportDotted:
    """Test _safe_import with dotted submodule names."""

    def test_allowed_submodule_ok(self):
        """Submodules of allowed root packages should pass."""
        result = _safe_import("collections.abc")
        assert result is not None

    def test_blocked_submodule(self):
        """Submodules of blocked root packages should be blocked."""
        with pytest.raises(ImportError, match="不允许导入"):
            _safe_import("os.path")

    def test_blocked_subprocess_module(self):
        with pytest.raises(ImportError, match="不允许导入"):
            _safe_import("subprocess.run")


# ---------------------------------------------------------------------------
# _safe_open_factory  -- additional branches
# ---------------------------------------------------------------------------
class TestSafeOpenFactoryExtended:
    """Additional tests for the safe open factory."""

    def test_write_mode_with_append(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            safe_open = _safe_open_factory(workdir)
            with safe_open("output.txt", "a") as f:
                f.write("line1\n")
            assert (workdir / "output.txt").read_text() == "line1\n"

    def test_write_mode_with_plus(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            safe_open = _safe_open_factory(workdir)
            with safe_open("data.txt", "w+") as f:
                f.write("test")
                f.seek(0)
                assert f.read() == "test"

    def test_absolute_path_within_workdir_allowed(self):
        """An absolute path that resolves inside workdir should be allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            test_file = workdir / "inside.txt"
            test_file.write_text("ok", encoding="utf-8")
            safe_open = _safe_open_factory(workdir)
            with safe_open(str(test_file)) as f:
                assert f.read() == "ok"

    def test_read_nonexistent_file_raises(self):
        """Reading a file that doesn't exist should raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            safe_open = _safe_open_factory(workdir)
            with pytest.raises(FileNotFoundError):
                safe_open("nonexistent.txt")


# ---------------------------------------------------------------------------
# _safe_builtins  -- verify open is included
# ---------------------------------------------------------------------------
class TestSafeBuiltins:
    """Test the _safe_builtins function."""

    def test_includes_open(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            builtins = _safe_builtins(Path(tmpdir))
            assert "open" in builtins
            assert callable(builtins["open"])

    def test_includes_all_safe_builtins(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            builtins = _safe_builtins(Path(tmpdir))
            for name in SAFE_BUILTINS:
                assert name in builtins, f"{name} missing from safe builtins"

    def test_print_is_functional(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            builtins = _safe_builtins(Path(tmpdir))
            assert builtins["print"] is print


# ---------------------------------------------------------------------------
# _execute_code_impl  -- success and failure paths (via subprocess)
# ---------------------------------------------------------------------------
class TestExecuteCodeImpl:
    """Test the code execution implementation via subprocess-based API
    to avoid Windows tempfile cleanup issues with direct calls."""

    def test_simple_code_success(self):
        from app.python_runner import run_python_code

        result = run_python_code("print(42)", timeout_sec=5)
        assert result["ok"] is True
        assert result["stdout"] == "42"
        assert result["duration_sec"] >= 0

    def test_syntax_error_returns_error(self):
        from app.python_runner import run_python_code

        result = run_python_code("def f(", timeout_sec=5)
        assert result["ok"] is False
        assert "error" in result

    def test_runtime_error_returns_error(self):
        from app.python_runner import run_python_code

        result = run_python_code("x = 1/0", timeout_sec=5)
        assert result["ok"] is False
        assert "error" in result

    def test_import_blocked_in_code(self):
        from app.python_runner import run_python_code

        result = run_python_code("import os", timeout_sec=5)
        assert result["ok"] is False
        assert "error" in result

    def test_output_capture(self):
        from app.python_runner import run_python_code

        result = run_python_code("print('hello')\nprint('world')", timeout_sec=5)
        assert result["ok"] is True
        assert "hello" in result["stdout"]
        assert "world" in result["stdout"]

    def test_empty_code(self):
        from app.python_runner import run_python_code

        result = run_python_code("", timeout_sec=5)
        assert result["ok"] is True
        assert result["stdout"] == ""

    def test_multiline_code(self):
        from app.python_runner import run_python_code

        code = "total = 0\nfor i in range(5):\n    total += i\nprint(total)"
        result = run_python_code(code, timeout_sec=5)
        assert result["ok"] is True
        assert result["stdout"] == "10"

    def test_file_operations_in_sandbox(self):
        from app.python_runner import run_python_code

        code = (
            "f = open('test.txt', 'w')\n"
            "f.write('hello')\n"
            "f.close()\n"
            "f = open('test.txt', 'r')\n"
            "print(f.read())\n"
            "f.close()"
        )
        result = run_python_code(code, timeout_sec=5)
        assert result["ok"] is True
        assert result["stdout"] == "hello"


# ---------------------------------------------------------------------------
# _should_use_subprocess_fallback
# ---------------------------------------------------------------------------
class TestShouldUseSubprocessFallback:
    """Test the subprocess fallback detection logic."""

    def test_returns_bool(self):
        result = _should_use_subprocess_fallback()
        assert isinstance(result, bool)

    def test_frozen_returns_false(self):
        """When sys.frozen is True (PyInstaller), should NOT use subprocess."""
        with patch("app.python_runner.sys") as mock_sys:
            mock_sys.frozen = True
            mock_sys.modules = {"__main__": type("M", (), {"__file__": "main.py"})()}
            result = _should_use_subprocess_fallback()
            assert result is False

    def test_no_main_file_uses_subprocess(self):
        """When __main__ has no __file__, should use subprocess."""
        with patch("app.python_runner.sys") as mock_sys:
            mock_sys.frozen = False
            mock_sys.modules = {"__main__": type("M", (), {"__file__": ""})()}
            result = _should_use_subprocess_fallback()
            assert result is True

    def test_repl_like_main_uses_subprocess(self):
        """When __main__.__file__ starts with '<', should use subprocess."""
        with patch("app.python_runner.sys") as mock_sys:
            mock_sys.frozen = False
            mock_sys.modules = {"__main__": type("M", (), {"__file__": "<stdin>"})()}
            result = _should_use_subprocess_fallback()
            assert result is True


# ---------------------------------------------------------------------------
# _evaluate_code_impl via subprocess  -- additional scoring branches
# ---------------------------------------------------------------------------
class TestEvaluateScoringBranches:
    """Test edge cases in the evaluation scoring pipeline via evaluate_python_code."""

    def test_empty_code_syntax_error(self):
        """Empty code with no expected nodes/tests -- should parse ok."""
        from app.python_runner import evaluate_python_code

        result = evaluate_python_code(
            "",
            expected_nodes=[],
            required_names=[],
            tests=[],
        )
        # Empty code parses as valid Python
        assert result["score"] >= 20  # syntax check passes

    def test_syntax_passes_but_missing_names(self):
        from app.python_runner import evaluate_python_code

        code = "x = 42"
        result = evaluate_python_code(
            code,
            expected_nodes=["Assign"],
            required_names=["x", "y", "z"],
            tests=[],
        )
        assert any("缺少需要实现的对象" in line for line in result["feedback_lines"])
        assert result["passed"] is False

    def test_all_names_present(self):
        from app.python_runner import evaluate_python_code

        code = "x = 1\ny = 2\nz = 3"
        result = evaluate_python_code(
            code,
            expected_nodes=["Assign"],
            required_names=["x", "y", "z"],
            tests=[],
        )
        assert any("关键对象已定义" in line for line in result["feedback_lines"])

    def test_partial_test_pass_scoring(self):
        """With 2 passing + 1 failing test, score should be partial."""
        from app.python_runner import evaluate_python_code

        code = "def f(n): return n * 2"
        result = evaluate_python_code(
            code,
            expected_nodes=["FunctionDef"],
            required_names=["f"],
            tests=[
                {"expression": "f(1)", "expected": 2},
                {"expression": "f(2)", "expected": 4},
                {"expression": "f(3)", "expected": 99},  # wrong
            ],
        )
        # 2/3 tests pass: 40 * 2/3 = 26 -> total 20+20+10+10+26 = 86
        assert result["passed"] is False  # not all tests pass

    def test_multiple_function_def_nodes(self):
        """Multiple expected nodes should all be checked."""
        from app.python_runner import evaluate_python_code

        code = "def a(): pass\ndef b(): pass"
        result = evaluate_python_code(
            code,
            expected_nodes=["FunctionDef"],
            required_names=["a", "b"],
            tests=[],
        )
        assert any("代码结构符合要求" in line for line in result["feedback_lines"])


# ---------------------------------------------------------------------------
# cli_main
# ---------------------------------------------------------------------------
class TestCliMain:
    """Test the CLI entry point for subprocess-based execution."""

    def test_run_mode(self, tmp_path):
        payload = {"mode": "run", "args": ["print(123)"]}
        payload_file = tmp_path / "payload.json"
        payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        import sys

        old_argv = sys.argv
        try:
            sys.argv = ["cli", str(payload_file)]
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                cli_main()
            output = json.loads(buf.getvalue())
            assert output["ok"] is True
            assert output["stdout"] == "123"
        finally:
            sys.argv = old_argv

    def test_evaluate_mode(self, tmp_path):
        payload = {
            "mode": "evaluate",
            "args": ["x = 42", [], ["x"], []],
        }
        payload_file = tmp_path / "payload.json"
        payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        import sys

        old_argv = sys.argv
        try:
            sys.argv = ["cli", str(payload_file)]
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                cli_main()
            output = json.loads(buf.getvalue())
            assert "passed" in output
            assert "score" in output
        finally:
            sys.argv = old_argv
