"""Python 代码执行沙箱模块。

提供安全的 Python 代码执行和评测环境，通过 AST 预检、受限内置函数、
临时目录隔离、输出限制、超时控制和进程隔离等多层防护机制，确保用户
提交的练习代码不会对宿主系统造成损害。
"""

import ast
import io
import json
import logging
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ALLOWED_IMPORTS = {
    "argparse",
    "collections",
    "datetime",
    "functools",
    "itertools",
    "json",
    "logging",
    "math",
    "pathlib",
    "re",
    "statistics",
}

REPO_ROOT = Path(__file__).resolve().parent.parent

_WIN32_RETRY_ATTEMPTS = 3
_WIN32_RETRY_DELAY = 0.15


@contextmanager
def _safe_temp_dir(prefix: str):
    """Create a temporary directory with retry logic for Windows file lock errors.

    On Windows, antivirus (Windows Defender) may newly-created temp directories
    for scanning, causing WinError 32 ("another process is using this file").
    This context manager retries directory creation and cleanup on such errors.
    """
    for attempt in range(_WIN32_RETRY_ATTEMPTS):
        try:
            temp_dir = tempfile.mkdtemp(prefix=prefix)
            break
        except OSError:
            if attempt < _WIN32_RETRY_ATTEMPTS - 1:
                time.sleep(_WIN32_RETRY_DELAY)
            else:
                raise
    try:
        yield temp_dir
    finally:
        for attempt in range(_WIN32_RETRY_ATTEMPTS):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                break
            except OSError:
                if attempt < _WIN32_RETRY_ATTEMPTS - 1:
                    time.sleep(_WIN32_RETRY_DELAY)
                else:
                    shutil.rmtree(temp_dir, ignore_errors=True)


_DANGEROUS_ATTRS = frozenset(
    {
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
        "__init_subclass__",
        "__set_name__",
        "__new__",
        "__init__",
        "__del__",
        "__repr__",
        "__str__",
        "__bytes__",
        "__format__",
        "__lt__",
        "__le__",
        "__eq__",
        "__ne__",
        "__gt__",
        "__ge__",
        "__hash__",
        "__bool__",
        "__getattr__",
        "__setattr__",
        "__delattr__",
        "__dir__",
        "__get__",
        "__set__",
        "__delete__",
        "__class_getitem__",
        "__instancecheck__",
        "__subclasscheck__",
        "__call__",
        "__len__",
        "__getitem__",
        "__setitem__",
        "__delitem__",
        "__iter__",
        "__next__",
        "__contains__",
        "__abs__",
        "__neg__",
        "__pos__",
        "__invert__",
        "__add__",
        "__sub__",
        "__mul__",
        "__truediv__",
        "__floordiv__",
        "__mod__",
        "__pow__",
        "__lshift__",
        "__rshift__",
        "__and__",
        "__or__",
        "__xor__",
        "__radd__",
        "__rsub__",
        "__rmul__",
        "__rtruediv__",
        "__rfloordiv__",
        "__rmod__",
        "__rpow__",
        "__rlshift__",
        "__rrshift__",
        "__rand__",
        "__ror__",
        "__rxor__",
        "__iadd__",
        "__isub__",
        "__imul__",
        "__itruediv__",
        "__ifloordiv__",
        "__imod__",
        "__ipow__",
        "__ilshift__",
        "__irshift__",
        "__iand__",
        "__ior__",
        "__ixor__",
        "__int__",
        "__float__",
        "__complex__",
        "__round__",
        "__trunc__",
        "__floor__",
        "__ceil__",
        "__enter__",
        "__exit__",
        "__await__",
        "__aiter__",
        "__anext__",
        "__aenter__",
        "__aexit__",
    }
)

_DANGEROUS_BUILTINS_CALLS = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "breakpoint",
        "getattr",
        "hasattr",
        "delattr",
        "setattr",
        "type",
        "object",
        "super",
        "dir",
        "vars",
        "globals",
        "locals",
        "memoryview",
        "bytearray",
    }
)


def _validate_code_safety(code_str: str) -> None:
    """Raise SyntaxError if *code_str* contains patterns unsafe for the sandbox."""
    tree = ast.parse(code_str)
    for node in ast.walk(tree):
        # Block access to dangerous dunder attributes
        if isinstance(node, ast.Attribute) and node.attr in _DANGEROUS_ATTRS:
            raise SyntaxError(f"安全限制: 不允许访问属性 {node.attr}（第 {node.lineno} 行）")
        # Block import statements
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise SyntaxError(f"安全限制: 不允许使用 import 语句（第 {node.lineno} 行），请使用内置函数。")
        # Block dangerous function calls
        if isinstance(node, ast.Call):
            func = node.func
            # Direct calls: eval(), exec(), type(), getattr(), etc.
            if isinstance(func, ast.Name) and func.id in _DANGEROUS_BUILTINS_CALLS:
                raise SyntaxError(f"安全限制: 不允许调用 {func.id}()（第 {node.lineno} 行）。")
            # Method calls on dangerous dunder attributes
            if isinstance(func, ast.Attribute) and func.attr in (
                "__subclasses__",
                "__bases__",
                "__mro__",
                "__globals__",
                "__code__",
                "__class__",
            ):
                raise SyntaxError(f"安全限制: 不允许调用 {func.attr}()（第 {node.lineno} 行）。")
            # Block getattr/hasattr with dangerous dunder string args
            if isinstance(func, ast.Name) and func.id in ("getattr", "hasattr"):
                if len(node.args) >= 2:
                    arg = node.args[1]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if arg.value.startswith("__") and arg.value.endswith("__"):
                            raise SyntaxError(
                                f"安全限制: 不允许通过 {func.id}() 访问双下划线属性 "
                                f"'{arg.value}'（第 {node.lineno} 行）。"
                            )
        # Block raw __builtins__ string references (could be used with join/chr tricks)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value
            if "__builtins__" in val or "__import__" in val:
                raise SyntaxError(f"安全限制: 不允许使用包含敏感双下划线属性的字符串（第 {node.lineno} 行）。")


SAFE_BUILTINS = {
    "print": print,
    "len": len,
    "range": range,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "sorted": sorted,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "sum": sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "isinstance": isinstance,
    "all": all,
    "any": any,
    "reversed": reversed,
    "Exception": Exception,
    "TypeError": TypeError,
    "ValueError": ValueError,
}


class LimitedBuffer(io.StringIO):
    """限制写入量的字符串缓冲区。

    当写入数据超过指定限制时抛出 RuntimeError，防止标准输出过大
    导致内存滥用。

    Attributes:
        limit: 最大写入字节数，默认 12000。
    """

    def __init__(self, limit: int = 12000):
        """初始化限制缓冲区。

        Args:
            limit: 最大写入字节数，默认 12000。
        """
        super().__init__()
        self.limit = limit

    def write(self, data: str) -> int:
        remaining = self.limit - self.tell()
        if remaining <= 0:
            raise RuntimeError("标准输出过长，已被截断。")
        if len(data) > remaining:
            super().write(data[:remaining])
            raise RuntimeError("标准输出过长，已被截断。")
        return super().write(data)


def _safe_import(
    name: str,
    globals: dict[str, Any] | None = None,
    locals: dict[str, Any] | None = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> Any:
    """受限的 __import__ 替代函数。

    仅允许导入白名单中的模块，拒绝其他模块的导入请求。
    """
    root = name.split(".")[0]
    if root not in ALLOWED_IMPORTS:
        raise ImportError(f"当前练习环境不允许导入模块: {root}")
    return __import__(name, globals, locals, fromlist, level)


def _safe_open_factory(workdir: Path) -> Callable[..., Any]:
    """创建受限的 open() 函数工厂。

    返回的 open 函数仅允许访问指定工作目录内的文件，
    拒绝目录逃逸的访问请求。

    Args:
        workdir: 允许访问的工作目录路径。

    Returns:
        受限的 open 函数。
    """

    def _safe_open(file: str | Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        target = Path(file)
        if target.is_absolute():
            resolved = target.resolve()
        else:
            resolved = (workdir / target).resolve()

        if workdir != resolved and workdir not in resolved.parents:
            raise PermissionError("练习环境只允许访问临时工作目录内的文件。")

        if any(flag in mode for flag in ("a", "w", "x", "+")):
            resolved.parent.mkdir(parents=True, exist_ok=True)

        return open(resolved, mode, *args, **kwargs)

    return _safe_open


def _safe_builtins(workdir: Path) -> dict[str, Any]:
    """构建受限的内置函数字典。

    基于 SAFE_BUILTINS 白名单，并将 open() 替换为受限版本。

    Args:
        workdir: 文件操作允许的工作目录。

    Returns:
        受限内置函数字典。
    """
    builtins = dict(SAFE_BUILTINS)
    builtins["open"] = _safe_open_factory(workdir)
    return builtins


def _execute_code_impl(code: str) -> dict[str, Any]:
    """在受限环境中执行 Python 代码（实际实现）。

    执行流程: 安全验证 -> 创建临时目录 -> 受限环境执行 -> 收集输出。

    Args:
        code: 要执行的 Python 代码字符串。

    Returns:
        包含 ok、stdout、error、duration_sec 键的结果字典。
    """
    started_at = time.time()
    previous_cwd = Path.cwd()
    try:
        _validate_code_safety(code)
        with _safe_temp_dir(prefix="devlearner-run-") as temp_dir:
            workdir = Path(temp_dir)
            os.chdir(workdir)
            try:
                stdout_buffer = LimitedBuffer()
                namespace = {
                    "__builtins__": _safe_builtins(workdir),
                    "__name__": "__main__",
                }
                with redirect_stdout(stdout_buffer):
                    exec(compile(code, "<exercise-run>", "exec"), namespace, namespace)
                return {
                    "ok": True,
                    "stdout": stdout_buffer.getvalue().strip(),
                    "duration_sec": int(time.time() - started_at),
                }
            finally:
                os.chdir(previous_cwd)
    except Exception as exc:
        logger.debug("代码执行异常: %s", exc)
        os.chdir(previous_cwd)
        return {
            "ok": False,
            "stdout": "",
            "error": str(exc),
            "duration_sec": int(time.time() - started_at),
        }
    finally:
        os.chdir(previous_cwd)


def _evaluate_code_impl(
    code: str,
    expected_nodes: list[str],
    required_names: list[str],
    tests: list[dict[str, Any]],
) -> dict[str, Any]:
    """在受限环境中评测 Python 代码（实际实现）。

    评测流程: 语法检查 -> 结构检查 -> 安全执行 -> 对象检查 -> 测试用例求值。
    评分维度: 语法 20 分 + 结构 20 分 + 执行 10 分 + 对象 10 分 + 测试 40 分。

    Args:
        code: 要评测的 Python 代码字符串。
        expected_nodes: 期望的 AST 节点类型列表。
        required_names: 期望在命名空间中定义的名称列表。
        tests: 测试用例列表，每项包含 expression 和 expected。

    Returns:
        包含 passed、score、feedback_lines、stdout、duration_sec 键的结果字典。
    """
    started_at = time.time()
    previous_cwd = Path.cwd()
    feedback = []
    score = 0
    stdout = ""

    try:
        tree = ast.parse(code)
        score += 20
        feedback.append("语法检查通过。")
    except SyntaxError as exc:
        return {
            "passed": False,
            "score": 0,
            "feedback_lines": [f"语法错误: 第 {exc.lineno} 行附近需要修正。"],
            "stdout": "",
            "duration_sec": int(time.time() - started_at),
        }

    missing_nodes = [
        node_name
        for node_name in expected_nodes
        if not any(type(node).__name__ == node_name for node in ast.walk(tree))
    ]
    if missing_nodes:
        feedback.append(f"结构还不完整，缺少: {', '.join(missing_nodes)}")
    else:
        score += 20
        feedback.append("代码结构符合要求。")

    try:
        _validate_code_safety(code)
        with _safe_temp_dir(prefix="devlearner-eval-") as temp_dir:
            workdir = Path(temp_dir)
            os.chdir(workdir)
            try:
                stdout_buffer = LimitedBuffer()
                namespace = {
                    "__builtins__": _safe_builtins(workdir),
                    "__name__": "__main__",
                }
                with redirect_stdout(stdout_buffer):
                    exec(compile(tree, "<exercise>", "exec"), namespace, namespace)
                stdout = stdout_buffer.getvalue().strip()
                score += 10
                feedback.append("代码可成功执行。")
            finally:
                os.chdir(previous_cwd)
    except Exception as exc:
        logger.debug("代码评测执行异常: %s", exc)
        os.chdir(previous_cwd)
        return {
            "passed": False,
            "score": score,
            "feedback_lines": feedback + [f"运行失败: {exc}"],
            "stdout": stdout,
            "duration_sec": int(time.time() - started_at),
        }

    missing_names = [name for name in required_names if name not in namespace]
    if missing_names:
        feedback.append(f"缺少需要实现的对象: {', '.join(missing_names)}")
    else:
        score += 10
        feedback.append("关键对象已定义。")

    test_passed = 0
    for test in tests:
        try:
            actual = eval(test["expression"], namespace, namespace)
        except Exception as exc:
            feedback.append(f"测试 `{test['expression']}` 执行失败: {exc}")
            continue
        expected = test["expected"]
        if actual == expected:
            test_passed += 1
            feedback.append(f"测试通过: {test['expression']} == {expected!r}")
        else:
            feedback.append(f"测试未通过: {test['expression']} 得到 {actual!r}，预期 {expected!r}")

    if tests:
        score += int(40 * test_passed / len(tests))

    return {
        "passed": score >= 70 and test_passed == len(tests) and not missing_nodes and not missing_names,
        "score": min(score, 100),
        "feedback_lines": feedback,
        "stdout": stdout,
        "duration_sec": int(time.time() - started_at),
    }


def _run_exec_worker(conn: Any, code: str) -> None:
    """子进程工作函数：执行代码并通过 Pipe 返回结果。"""
    conn.send(_execute_code_impl(code))
    conn.close()


def _evaluate_worker(
    conn: Any,
    code: str,
    expected_nodes: list[str],
    required_names: list[str],
    tests: list[dict[str, Any]],
) -> None:
    """子进程工作函数：评测代码并通过 Pipe 返回结果。"""
    conn.send(_evaluate_code_impl(code, expected_nodes, required_names, tests))
    conn.close()


def _should_use_subprocess_fallback() -> bool:
    """判断是否需要使用子进程回退方案。

    当无法使用 multiprocessing（如在交互式环境或某些嵌入场景中）时，
    回退到 subprocess 方案。
    """
    main_file = getattr(sys.modules.get("__main__"), "__file__", "")
    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        return False
    return not main_file or str(main_file).startswith("<")


def _run_via_subprocess(mode: str, args: tuple[Any, ...], timeout_sec: int) -> dict[str, Any]:
    payload = {"mode": mode, "args": args}
    with _safe_temp_dir(prefix="devlearner-runner-") as temp_dir:
        payload_path = Path(temp_dir) / "payload.json"
        payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        is_frozen = getattr(sys, "frozen", False)
        if is_frozen:
            cmd = [
                sys.executable,
                "-X",
                "utf8",
                str(payload_path),
            ]
        else:
            cmd = [
                sys.executable,
                "-X",
                "utf8",
                "-c",
                "from app.python_runner import cli_main; cli_main()",
                str(payload_path),
            ]

        completed = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec + 1,
        )
        if completed.returncode != 0:
            return {
                "ok": False,
                "passed": False,
                "score": 0,
                "feedback_lines": [completed.stderr.strip() or "子进程执行失败。"],
                "stdout": "",
                "error": completed.stderr.strip() or "子进程执行失败。",
                "duration_sec": timeout_sec,
            }
        return json.loads(completed.stdout)  # type: ignore[no-any-return]


def _run_with_timeout(
    target: Callable[..., None],
    mode: str,
    args: tuple[Any, ...],
    timeout_sec: int,
) -> dict[str, Any]:
    if _should_use_subprocess_fallback():
        return _run_via_subprocess(mode, args, timeout_sec)

    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(target=target, args=(child_conn, *args))
    process.start()
    child_conn.close()

    try:
        if parent_conn.poll(timeout_sec):
            return parent_conn.recv()  # type: ignore[no-any-return]
        process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join()
        return {
            "ok": False,
            "passed": False,
            "score": 0,
            "feedback_lines": [f"执行超时，已在 {timeout_sec} 秒后终止。"],
            "stdout": "",
            "error": f"执行超时，已在 {timeout_sec} 秒后终止。",
            "duration_sec": timeout_sec,
        }
    finally:
        parent_conn.close()


def run_python_code(code: str, timeout_sec: int = 3) -> dict[str, Any]:
    """在沙箱中执行 Python 代码。

    通过子进程隔离执行，支持超时控制。

    Args:
        code: 要执行的 Python 代码字符串。
        timeout_sec: 执行超时秒数，默认 3 秒。

    Returns:
        包含 ok、stdout、error、duration_sec 键的结果字典。
    """
    import time as _time

    start = _time.perf_counter()
    logger.info("Starting code execution: code_len=%d timeout=%ds", len(code), timeout_sec)
    result = _run_with_timeout(_run_exec_worker, "run", (code,), timeout_sec)
    elapsed_ms = (_time.perf_counter() - start) * 1000
    success = result.get("ok", False)
    logger.info(
        "Code execution completed: ok=%s duration_sec=%d elapsed_ms=%.1f",
        success,
        result.get("duration_sec", 0),
        elapsed_ms,
    )
    from app.utils.metrics import get_metrics

    get_metrics().record_code_execution(success, exit_code=0 if success else 1, elapsed_ms=elapsed_ms)
    return result


def evaluate_python_code(
    code: str,
    expected_nodes: list[str],
    required_names: list[str],
    tests: list[dict[str, object]],
    timeout_sec: int = 4,
) -> dict[str, object]:
    """在沙箱中评测 Python 代码。

    执行语法检查、结构检查、安全执行和测试用例验证，
    返回综合评测结果。

    Args:
        code: 要评测的 Python 代码字符串。
        expected_nodes: 期望的 AST 节点类型列表。
        required_names: 期望在命名空间中定义的名称列表。
        tests: 测试用例列表，每项包含 expression 和 expected。
        timeout_sec: 评测超时秒数，默认 4 秒。

    Returns:
        包含 passed、score、feedback_lines、stdout、duration_sec 键的结果字典。
    """
    import time as _time

    start = _time.perf_counter()
    logger.info(
        "Starting code evaluation: code_len=%d nodes=%d names=%d tests=%d timeout=%ds",
        len(code),
        len(expected_nodes),
        len(required_names),
        len(tests),
        timeout_sec,
    )
    result = _run_with_timeout(
        _evaluate_worker,
        "evaluate",
        (code, list(expected_nodes), list(required_names), list(tests)),
        timeout_sec,
    )
    elapsed_ms = (_time.perf_counter() - start) * 1000
    passed = result.get("passed", False)
    score = result.get("score", 0)
    logger.info(
        "Code evaluation completed: passed=%s score=%d elapsed_ms=%.1f",
        passed,
        score,
        elapsed_ms,
    )
    from app.utils.metrics import get_metrics

    get_metrics().record_exercise_attempt(
        exercise_id="eval",
        passed=bool(passed),
        score=int(score),
        elapsed_ms=elapsed_ms,
    )
    return result


def cli_main() -> None:
    """命令行入口点，供子进程回退方案调用。

    从 JSON payload 文件读取模式和参数，执行对应操作后输出 JSON 结果。
    """
    payload_path = Path(sys.argv[-1])
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    mode = payload["mode"]
    args = payload["args"]

    if mode == "run":
        result = _execute_code_impl(*args)
    else:
        result = _evaluate_code_impl(*args)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    cli_main()
