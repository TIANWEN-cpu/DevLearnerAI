import ast
import io
import json
import multiprocessing as mp
import os
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path


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


class LimitedBuffer(io.StringIO):
    def __init__(self, limit: int = 12000):
        super().__init__()
        self.limit = limit

    def write(self, data):
        remaining = self.limit - self.tell()
        if remaining <= 0:
            raise RuntimeError("标准输出过长，已被截断。")
        if len(data) > remaining:
            super().write(data[:remaining])
            raise RuntimeError("标准输出过长，已被截断。")
        return super().write(data)


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".")[0]
    if root not in ALLOWED_IMPORTS:
        raise ImportError(f"当前练习环境不允许导入模块: {root}")
    return __import__(name, globals, locals, fromlist, level)


def _safe_open_factory(workdir: Path):
    def _safe_open(file, mode="r", *args, **kwargs):
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


def _safe_builtins(workdir: Path):
    return {
        "__import__": _safe_import,
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "Exception": Exception,
        "filter": filter,
        "float": float,
        "int": int,
        "isinstance": isinstance,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "open": _safe_open_factory(workdir),
        "print": print,
        "range": range,
        "reversed": reversed,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "type": type,
        "tuple": tuple,
        "TypeError": TypeError,
        "ValueError": ValueError,
        "zip": zip,
    }


def _execute_code_impl(code: str):
    started_at = time.time()
    previous_cwd = Path.cwd()
    try:
        with tempfile.TemporaryDirectory(prefix="devlearner-run-") as temp_dir:
            workdir = Path(temp_dir)
            os.chdir(workdir)
            stdout_buffer = LimitedBuffer()
            namespace = {
                "__builtins__": _safe_builtins(workdir),
                "__name__": "__main__",
            }
            with redirect_stdout(stdout_buffer):
                exec(compile(code, "<exercise-run>", "exec"), namespace, namespace)
            os.chdir(previous_cwd)
            return {
                "ok": True,
                "stdout": stdout_buffer.getvalue().strip(),
                "duration_sec": int(time.time() - started_at),
            }
    except Exception as exc:
        return {
            "ok": False,
            "stdout": "",
            "error": str(exc),
            "duration_sec": int(time.time() - started_at),
        }
    finally:
        os.chdir(previous_cwd)


def _evaluate_code_impl(code: str, expected_nodes, required_names, tests):
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
        with tempfile.TemporaryDirectory(prefix="devlearner-eval-") as temp_dir:
            workdir = Path(temp_dir)
            os.chdir(workdir)
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
            os.chdir(previous_cwd)
    except Exception as exc:
        return {
            "passed": False,
            "score": score,
            "feedback_lines": feedback + [f"运行失败: {exc}"],
            "stdout": stdout,
            "duration_sec": int(time.time() - started_at),
        }
    finally:
        os.chdir(previous_cwd)

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
            feedback.append(
                f"测试未通过: {test['expression']} 得到 {actual!r}，预期 {expected!r}"
            )

    if tests:
        score += int(40 * test_passed / len(tests))

    return {
        "passed": score >= 70
        and test_passed == len(tests)
        and not missing_nodes
        and not missing_names,
        "score": min(score, 100),
        "feedback_lines": feedback,
        "stdout": stdout,
        "duration_sec": int(time.time() - started_at),
    }


def _run_exec_worker(conn, code: str):
    conn.send(_execute_code_impl(code))
    conn.close()


def _evaluate_worker(conn, code: str, expected_nodes, required_names, tests):
    conn.send(_evaluate_code_impl(code, expected_nodes, required_names, tests))
    conn.close()


def _should_use_subprocess_fallback() -> bool:
    main_file = getattr(sys.modules.get("__main__"), "__file__", "")
    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        return False
    return not main_file or str(main_file).startswith("<")


def _run_via_subprocess(mode: str, args, timeout_sec: int):
    payload = {"mode": mode, "args": args}
    with tempfile.TemporaryDirectory(prefix="devlearner-runner-") as temp_dir:
        payload_path = Path(temp_dir) / "payload.json"
        payload_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

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
        return json.loads(completed.stdout)


def _run_with_timeout(target, mode: str, args, timeout_sec: int):
    if _should_use_subprocess_fallback():
        return _run_via_subprocess(mode, args, timeout_sec)

    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(target=target, args=(child_conn, *args))
    process.start()
    child_conn.close()

    try:
        if parent_conn.poll(timeout_sec):
            return parent_conn.recv()
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


def run_python_code(code: str, timeout_sec: int = 3):
    return _run_with_timeout(_run_exec_worker, "run", (code,), timeout_sec)


def evaluate_python_code(
    code: str, expected_nodes, required_names, tests, timeout_sec: int = 4
):
    return _run_with_timeout(
        _evaluate_worker,
        "evaluate",
        (code, list(expected_nodes), list(required_names), list(tests)),
        timeout_sec,
    )


def cli_main():
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
