"""Code evaluation logic: SQL checking, keyword validation, Python execution."""

import logging
import re
import sqlite3
import time

from app.practice.exercise_loader import get_sql_query_fixtures
from app.practice.models import EvaluationResult, Exercise
from app.practice.normalizer import normalize_rows
from app.python_runner import evaluate_python_code

logger = logging.getLogger(__name__)


def validate_sql_side_effect(exercise_id: str, conn: sqlite3.Connection) -> bool:
    """Validate that a DDL exercise produced the expected schema changes."""
    if exercise_id == "db-design-enrollment-table":
        columns = {row[1] for row in conn.execute("PRAGMA table_info(enrollments)").fetchall()}
        return {"student_id", "course_id"}.issubset(columns)
    if exercise_id == "db-orders-foreign-key":
        columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()}
        foreign_keys = conn.execute("PRAGMA foreign_key_list(orders)").fetchall()
        return {"user_id"}.issubset(columns) and any(row[2] == "users" and row[3] == "user_id" for row in foreign_keys)
    if exercise_id == "db-create-index-users-email":
        indexes = conn.execute("PRAGMA index_list(users)").fetchall()
        for index in indexes:
            index_name = index[1]
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", index_name):
                continue
            indexed_columns = {row[2] for row in conn.execute(f"PRAGMA index_info([{index_name}])").fetchall()}
            if "email" in indexed_columns:
                return True
        return False
    if exercise_id == "db-add-column-migration":
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        return "last_login" in columns
    if exercise_id == "db-create-covering-index-report":
        indexes = conn.execute("PRAGMA index_list(reports)").fetchall()
        for index in indexes:
            index_name = index[1]
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", index_name):
                continue
            indexed_columns = [row[2] for row in conn.execute(f"PRAGMA index_info([{index_name}])").fetchall()]
            if indexed_columns and indexed_columns[:2] == ["created_at", "status"]:
                return True
        return False
    if exercise_id == "db-add-status-column-users":
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        return "status" in columns
    if exercise_id == "db-create-enrollment-foreign-key":
        columns = {row[1] for row in conn.execute("PRAGMA table_info(enrollments)").fetchall()}
        foreign_keys = conn.execute("PRAGMA foreign_key_list(enrollments)").fetchall()
        has_student_fk = any(row[2] == "students" and row[3] == "student_id" for row in foreign_keys)
        has_course_fk = any(row[2] == "courses" and row[3] == "course_id" for row in foreign_keys)
        return {"student_id", "course_id"}.issubset(columns) and has_student_fk and has_course_fk
    if exercise_id == "db-explain-users-query":
        rows = conn.execute("EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'a@example.com'").fetchall()
        return bool(rows)
    return False


def evaluate_sql_fixture(exercise: Exercise, code: str, fixture: dict) -> EvaluationResult:
    """Evaluate a SQL answer against a known fixture with setup/expected data."""
    start = time.time()
    normalized = " ".join(code.lower().split())
    feedback: list[str] = []
    score = 0

    if not normalized:
        return EvaluationResult(
            passed=False,
            score=0,
            feedback_lines=["答案为空，先把 SQL 写出来再提交。"],
            duration_sec=int(time.time() - start),
        )

    missing = [keyword for keyword in exercise.required_keywords if keyword.lower() not in normalized]
    if missing:
        feedback.append(f"还缺少这些关键结构: {', '.join(missing)}")
    else:
        score += 20
        feedback.append("关键 SQL 结构已经覆盖。")

    forbidden = [keyword for keyword in exercise.forbidden_keywords if keyword.lower() in normalized]
    if forbidden:
        feedback.append(f"出现了不建议使用的关键字: {', '.join(forbidden)}")
    else:
        score += 10

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        if fixture.get("setup"):
            conn.executescript(fixture["setup"])

        try:
            mode = fixture.get("mode", "query")
            if mode == "query":
                rows = conn.execute(code).fetchall()
                expected_rows = fixture.get("expected_rows", [])
                actual = normalize_rows(rows, fixture.get("ordered", False))
                expected = normalize_rows(expected_rows, fixture.get("ordered", False))
                if actual == expected:
                    score += 70
                    feedback.append("结果集和参考答案一致，已经通过真实数据库比对。")
                else:
                    feedback.append("SQL 能执行，但结果集和参考答案不一致。")
                    feedback.append(f"预期结果: {expected}")
                    feedback.append(f"你的结果: {actual}")
            elif mode == "script":
                conn.executescript(code)
                rows = conn.execute(fixture["check_sql"]).fetchall()
                actual = normalize_rows(rows, fixture.get("ordered", False))
                expected = normalize_rows(fixture.get("expected_rows", []), fixture.get("ordered", False))
                if actual == expected:
                    score += 70
                    feedback.append("脚本执行成功，落库后的结果和参考答案一致。")
                else:
                    feedback.append("脚本执行成功，但落库后的结果和参考答案不一致。")
                    feedback.append(f"预期结果: {expected}")
                    feedback.append(f"你的结果: {actual}")
            elif mode == "explain":
                plan_rows = conn.execute(code).fetchall()
                if plan_rows:
                    score += 70
                    feedback.append("EXPLAIN 查询执行成功，已经拿到执行计划结果。")
                else:
                    feedback.append("SQL 能执行，但没有返回执行计划结果。")
            else:
                conn.executescript(code)
                if validate_sql_side_effect(exercise.id, conn):
                    score += 70
                    feedback.append("数据库结构变更符合题目要求，已经通过真实校验。")
                else:
                    feedback.append("SQL 已执行，但数据库结构还没有达到题目要求。")
        except sqlite3.Error as exc:
            feedback.append(f"SQL 执行失败: {exc}")
    finally:
        conn.close()

    if ";" in code:
        score += 5
    return EvaluationResult(
        passed=score >= 70 and not missing and not forbidden and all("执行失败" not in item for item in feedback),
        score=min(score, 100),
        feedback_lines=feedback,
        duration_sec=int(time.time() - start),
    )


def evaluate_sql(exercise: Exercise, code: str) -> EvaluationResult:
    """Dispatch SQL evaluation to the appropriate backend."""
    fixture = get_sql_query_fixtures().get(exercise.id)
    if fixture:
        return evaluate_sql_fixture(exercise, code, fixture)
    if exercise.id in {
        "db-design-enrollment-table",
        "db-orders-foreign-key",
        "db-create-index-users-email",
        "db-add-column-migration",
        "db-create-covering-index-report",
        "db-add-status-column-users",
        "db-create-enrollment-foreign-key",
        "db-explain-users-query",
    }:
        ddl_fixture: dict = {"setup": "", "mode": "ddl"}
        if exercise.id == "db-orders-foreign-key":
            ddl_fixture["setup"] = "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);"
        elif exercise.id == "db-create-index-users-email":
            ddl_fixture["setup"] = "CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT);"
        elif exercise.id == "db-add-column-migration":
            ddl_fixture["setup"] = "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);"
        elif exercise.id == "db-create-covering-index-report":
            ddl_fixture["setup"] = (
                "CREATE TABLE reports(id INTEGER PRIMARY KEY, created_at TEXT, status TEXT, owner_id INTEGER);"
            )
        elif exercise.id == "db-add-status-column-users":
            ddl_fixture["setup"] = "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);"
        elif exercise.id == "db-create-enrollment-foreign-key":
            ddl_fixture["setup"] = """
                CREATE TABLE students(id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE courses(id INTEGER PRIMARY KEY, title TEXT);
            """
        elif exercise.id == "db-explain-users-query":
            return evaluate_sql_fixture(exercise, code, get_sql_query_fixtures()["db-explain-users-query"])
        return evaluate_sql_fixture(exercise, code, ddl_fixture)

    # Fallback: keyword-only structural check
    start = time.time()
    normalized = " ".join(code.lower().split())
    feedback: list[str] = []
    score = 0

    feedback.append("当前为 SQL 结构训练题，本轮先检查查询结构，暂不执行真实数据库结果比对。")

    if normalized:
        score += 20
        feedback.append("已提交 SQL 答案。")
    else:
        feedback.append("答案为空，先写出查询语句。")

    missing = [keyword for keyword in exercise.required_keywords if keyword.lower() not in normalized]
    if not missing:
        score += 50
        feedback.append("关键 SQL 结构完整。")
    else:
        feedback.append(f"缺少关键结构: {', '.join(missing)}")

    forbidden = [keyword for keyword in exercise.forbidden_keywords if keyword.lower() in normalized]
    if forbidden:
        feedback.append(f"出现了不建议使用的关键字: {', '.join(forbidden)}")
    else:
        score += 20
        feedback.append("没有使用禁用关键字。")

    if ";" in code:
        score += 10
        feedback.append("语句结束符处理规范。")

    return EvaluationResult(
        passed=score >= 70 and not missing,
        score=min(score, 100),
        feedback_lines=feedback,
        duration_sec=int(time.time() - start),
    )


def evaluate_keyword_code(exercise: Exercise, code: str) -> EvaluationResult:
    """Evaluate C/C# code by checking for required keywords/structures."""
    start = time.time()
    normalized = " ".join(code.lower().split())
    feedback: list[str] = []
    score = 0

    feedback.append("当前为结构训练题，本轮先检查关键结构，暂不执行真实编译运行。")

    if normalized:
        score += 20
        feedback.append("已提交代码草稿。")
    else:
        feedback.append("答案为空，先把函数签名和核心结构写出来。")

    missing = [keyword for keyword in exercise.required_keywords if keyword.lower() not in normalized]
    if not missing:
        score += 50
        feedback.append("关键结构已经覆盖。")
    else:
        feedback.append(f"还缺少这些关键结构: {', '.join(missing)}")

    forbidden = [keyword for keyword in exercise.forbidden_keywords if keyword.lower() in normalized]
    if forbidden:
        feedback.append(f"出现了不建议使用的关键字: {', '.join(forbidden)}")
    else:
        score += 20
        feedback.append("没有出现禁用关键字。")

    if ";" in code or "{" in code:
        score += 10
        feedback.append("代码书写格式看起来像目标语言。")

    return EvaluationResult(
        passed=score >= 70 and not missing,
        score=min(score, 100),
        feedback_lines=feedback,
        duration_sec=int(time.time() - start),
    )


def evaluate_python(exercise: Exercise, code: str) -> EvaluationResult:
    """Evaluate Python code using the python_runner sandbox."""
    result = evaluate_python_code(
        code,
        exercise.expected_nodes,
        exercise.required_names,
        exercise.tests,
    )
    return EvaluationResult(
        passed=bool(result["passed"]),
        score=int(result["score"]),
        feedback_lines=list(result["feedback_lines"]),
        stdout=str(result.get("stdout", "")),
        duration_sec=int(result.get("duration_sec", 0)),
    )
