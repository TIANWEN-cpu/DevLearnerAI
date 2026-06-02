"""Extended tests for app.python_runner covering subprocess, CLI, and evaluate paths.

Targets:
- _run_via_subprocess (lines 503-545)
- _run_with_timeout subprocess fallback path (line 550)
- _run_with_timeout timeout/kill path (lines 561-566)
- _evaluate_code_impl test evaluation branches (lines 453-466)
- _run_exec_worker / _evaluate_worker (lines 479-486)
- cli_main run/evaluate modes (line 637)
"""

import json
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# _run_via_subprocess
# ---------------------------------------------------------------------------
class TestRunViaSubprocess:
    """Test the _run_via_subprocess function (lines 503-545)."""

    def test_run_via_subprocess_success(self):
        from app.python_runner import _run_via_subprocess

        expected = {"ok": True, "stdout": "hello", "duration_sec": 0}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(expected, ensure_ascii=False)

        with patch("app.python_runner.subprocess.run", return_value=mock_result):
            result = _run_via_subprocess("run", ("print('hello')",), 5)

        assert result["ok"] is True

    def test_run_via_subprocess_failure(self):
        from app.python_runner import _run_via_subprocess

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "some error"

        with patch("app.python_runner.subprocess.run", return_value=mock_result):
            result = _run_via_subprocess("run", ("bad code",), 5)

        assert result["ok"] is False
        assert result["passed"] is False
        assert result["score"] == 0
        assert "some error" in result["error"]

    def test_run_via_subprocess_empty_stderr(self):
        from app.python_runner import _run_via_subprocess

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = ""

        with patch("app.python_runner.subprocess.run", return_value=mock_result):
            result = _run_via_subprocess("run", ("bad code",), 5)

        assert result["ok"] is False


# ---------------------------------------------------------------------------
# _run_with_timeout - subprocess fallback path
# ---------------------------------------------------------------------------
class TestRunWithTimeoutSubprocess:
    """Test _run_with_timeout when subprocess fallback is needed (line 549-550)."""

    def test_subprocess_fallback_triggered(self):
        from app.python_runner import _run_exec_worker, _run_with_timeout

        expected = {"ok": True, "stdout": "x", "duration_sec": 0}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(expected, ensure_ascii=False)

        with (
            patch("app.python_runner._should_use_subprocess_fallback", return_value=True),
            patch("app.python_runner.subprocess.run", return_value=mock_result),
        ):
            result = _run_with_timeout(_run_exec_worker, "run", ("code",), 5)

        assert result["ok"] is True


# ---------------------------------------------------------------------------
# _run_with_timeout - timeout and kill path
# ---------------------------------------------------------------------------
class TestRunWithTimeoutKill:
    """Test _run_with_timeout timeout/kill branches (lines 559-566)."""

    def test_timeout_returns_timeout_result(self):
        from app.python_runner import _run_exec_worker, _run_with_timeout

        mock_parent_conn = MagicMock()
        mock_parent_conn.poll.return_value = False

        mock_process = MagicMock()
        mock_process.is_alive.return_value = False

        mock_ctx = MagicMock()
        mock_ctx.Pipe.return_value = (mock_parent_conn, MagicMock())
        mock_ctx.Process.return_value = mock_process

        with (
            patch("app.python_runner._should_use_subprocess_fallback", return_value=False),
            patch("app.python_runner.mp.get_context", return_value=mock_ctx),
        ):
            result = _run_with_timeout(_run_exec_worker, "run", ("code",), 1)

        assert result["ok"] is False
        assert result["passed"] is False
        assert result["score"] == 0

    def test_timeout_process_still_alive_after_terminate(self):
        from app.python_runner import _run_exec_worker, _run_with_timeout

        mock_parent_conn = MagicMock()
        mock_parent_conn.poll.return_value = False

        mock_process = MagicMock()
        mock_process.is_alive.return_value = True

        mock_ctx = MagicMock()
        mock_ctx.Process.return_value = mock_process
        mock_ctx.Pipe.return_value = (mock_parent_conn, MagicMock())

        with (
            patch("app.python_runner._should_use_subprocess_fallback", return_value=False),
            patch("app.python_runner.mp.get_context", return_value=mock_ctx),
        ):
            result = _run_with_timeout(_run_exec_worker, "run", ("code",), 1)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert result["ok"] is False

    def test_success_returns_recv_data(self):
        from app.python_runner import _run_exec_worker, _run_with_timeout

        expected = {"ok": True, "stdout": "done", "duration_sec": 0}

        mock_parent_conn = MagicMock()
        mock_parent_conn.poll.return_value = True
        mock_parent_conn.recv.return_value = expected

        mock_process = MagicMock()

        mock_ctx = MagicMock()
        mock_ctx.Process.return_value = mock_process
        mock_ctx.Pipe.return_value = (mock_parent_conn, MagicMock())

        with (
            patch("app.python_runner._should_use_subprocess_fallback", return_value=False),
            patch("app.python_runner.mp.get_context", return_value=mock_ctx),
        ):
            result = _run_with_timeout(_run_exec_worker, "run", ("code",), 5)

        assert result["ok"] is True
        assert result["stdout"] == "done"


# ---------------------------------------------------------------------------
# _evaluate_code_impl - using evaluate_python_code which uses subprocess
# ---------------------------------------------------------------------------
class TestEvaluateCodeImplExtended:
    """Test evaluate_python_code which covers _evaluate_code_impl through subprocess."""

    def test_syntax_error_returns_immediately(self):
        """Syntax errors should return immediately with score 0."""
        from app.python_runner import _evaluate_code_impl

        result = _evaluate_code_impl("def (", [], [], [])
        assert result["passed"] is False
        assert result["score"] == 0

    def test_evaluate_simple_code(self):
        """evaluate_python_code should work through the subprocess path."""
        from app.python_runner import evaluate_python_code

        result = evaluate_python_code(
            "x = 1",
            expected_nodes=[],
            required_names=["x"],
            tests=[{"expression": "x", "expected": 1}],
            timeout_sec=10,
        )
        assert "passed" in result
        assert "score" in result

    def test_evaluate_with_function(self):
        """Evaluate code with function definition - verifies result structure."""
        from app.python_runner import evaluate_python_code

        result = evaluate_python_code(
            "def add(a, b):\n    return a + b",
            expected_nodes=["FunctionDef"],
            required_names=["add"],
            tests=[
                {"expression": "add(1, 2)", "expected": 3},
                {"expression": "add(0, 0)", "expected": 0},
            ],
            timeout_sec=10,
        )
        # Result should have all expected keys
        assert "passed" in result
        assert "score" in result
        assert "feedback_lines" in result
        assert isinstance(result["feedback_lines"], list)

    def test_evaluate_syntax_error(self):
        from app.python_runner import evaluate_python_code

        result = evaluate_python_code("def (", [], [], [], timeout_sec=10)
        assert result["passed"] is False
        assert result["score"] == 0

    def test_evaluate_missing_names(self):
        from app.python_runner import evaluate_python_code

        result = evaluate_python_code(
            "x = 1",
            [],
            ["foo"],
            [],
            timeout_sec=10,
        )
        assert result["passed"] is False

    def test_evaluate_test_mismatch(self):
        from app.python_runner import evaluate_python_code

        result = evaluate_python_code(
            "x = 1",
            [],
            ["x"],
            [{"expression": "x", "expected": 999}],
            timeout_sec=10,
        )
        assert result["passed"] is False

    def test_evaluate_partial_tests(self):
        from app.python_runner import evaluate_python_code

        result = evaluate_python_code(
            "x = 1\ny = 2",
            [],
            ["x", "y"],
            [
                {"expression": "x", "expected": 1},
                {"expression": "y", "expected": 999},
            ],
            timeout_sec=10,
        )
        assert result["score"] < 100


# ---------------------------------------------------------------------------
# _run_exec_worker and _evaluate_worker
# ---------------------------------------------------------------------------
class TestWorkers:
    """Test the worker functions (lines 477-486)."""

    def test_run_exec_worker(self):
        from app.python_runner import _run_exec_worker

        mock_conn = MagicMock()
        with patch("app.python_runner._execute_code_impl", return_value={"ok": True}):
            _run_exec_worker(mock_conn, "x = 1")

        mock_conn.send.assert_called_once_with({"ok": True})
        mock_conn.close.assert_called_once()

    def test_evaluate_worker(self):
        from app.python_runner import _evaluate_worker

        mock_conn = MagicMock()
        with patch("app.python_runner._evaluate_code_impl", return_value={"passed": True}):
            _evaluate_worker(mock_conn, "code", [], [], [])

        mock_conn.send.assert_called_once_with({"passed": True})
        mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# cli_main
# ---------------------------------------------------------------------------
class TestCliMain:
    """Test cli_main modes (line 628-633)."""

    def test_cli_main_run_mode_success(self, tmp_path):
        from app.python_runner import cli_main

        payload = {
            "mode": "run",
            "args": ["x = 1 + 2"],
        }
        payload_path = tmp_path / "payload_run.json"
        payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        with patch("sys.argv", ["cli", str(payload_path)]), patch("builtins.print") as mock_print:
            cli_main()
            assert mock_print.called
            output = mock_print.call_args[0][0]
            result = json.loads(output)
            assert "ok" in result

    def test_cli_main_evaluate_mode(self, tmp_path):
        from app.python_runner import cli_main

        payload = {
            "mode": "evaluate",
            "args": ["x = 1", [], ["x"], [{"expression": "x", "expected": 1}]],
        }
        payload_path = tmp_path / "payload_eval.json"
        payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        with patch("sys.argv", ["cli", str(payload_path)]), patch("builtins.print") as mock_print:
            cli_main()
            assert mock_print.called
            output = mock_print.call_args[0][0]
            result = json.loads(output)
            assert "passed" in result
            assert "score" in result
