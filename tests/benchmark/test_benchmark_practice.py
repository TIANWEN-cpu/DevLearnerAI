"""练习评测与答案标准化性能基准测试。

覆盖场景:
- evaluate_keyword_code 各种规模关键词匹配
- evaluate_sql_fixture 轻量评测路径
- normalize_rows 不同数据规模
- Exercise 构建开销
"""

from app.practice.evaluator import evaluate_keyword_code, evaluate_sql_fixture
from app.practice.models import Exercise
from app.practice.normalizer import normalize_rows

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_exercise_keyword(n_required: int = 5, n_forbidden: int = 2) -> Exercise:
    """构造仅含关键词约束的练习。"""
    return Exercise(
        id="bench-kw",
        title="基准测试练习",
        track_id="python",
        difficulty="基础",
        prompt="实现指定功能。",
        lesson_id="lesson-1",
        required_keywords=[f"keyword_{i}" for i in range(n_required)],
        forbidden_keywords=[f"bad_{i}" for i in range(n_forbidden)],
    )


def _make_code_with_keywords(n: int = 10) -> str:
    """构造包含 n 个 keyword_N 的代码字符串。"""
    parts = [f"# keyword_{i}\nresult = {i}" for i in range(n)]
    return "\n".join(parts)


# ── 关键词评测基准 ───────────────────────────────────────────────────────────


class TestKeywordEvaluation:
    """基准: evaluate_keyword_code 不同规模。"""

    def test_keyword_eval_small(self, benchmark):
        """少量关键词 (5 required, 2 forbidden)。"""
        exercise = _make_exercise_keyword(5, 2)
        code = _make_code_with_keywords(8)
        benchmark(evaluate_keyword_code, exercise, code)

    def test_keyword_eval_medium(self, benchmark):
        """中等关键词 (20 required, 5 forbidden)。"""
        exercise = _make_exercise_keyword(20, 5)
        code = _make_code_with_keywords(25)
        benchmark(evaluate_keyword_code, exercise, code)

    def test_keyword_eval_large(self, benchmark):
        """大量关键词 (50 required, 10 forbidden)。"""
        exercise = _make_exercise_keyword(50, 10)
        code = _make_code_with_keywords(60)
        benchmark(evaluate_keyword_code, exercise, code)


# ── SQL 评测基准 ─────────────────────────────────────────────────────────────


class TestSqlEvaluation:
    """基准: evaluate_sql_fixture。"""

    def _make_sql_exercise(self) -> Exercise:
        return Exercise(
            id="bench-sql",
            title="SQL 基准",
            track_id="database",
            difficulty="基础",
            prompt="写出查询。",
            lesson_id="lesson-sql-1",
            required_keywords=["SELECT", "FROM"],
            forbidden_keywords=["DELETE"],
        )

    def test_sql_fixture_query(self, benchmark):
        """查询模式评测。"""
        exercise = self._make_sql_exercise()
        fixture = {
            "setup": "CREATE TABLE t(id INTEGER, name TEXT); INSERT INTO t VALUES (1, 'a');",
            "mode": "query",
            "expected_rows": [[1, "a"]],
            "ordered": True,
        }
        code = "SELECT id, name FROM t"
        benchmark(evaluate_sql_fixture, exercise, code, fixture)

    def test_sql_fixture_script(self, benchmark):
        """脚本模式评测。"""
        exercise = self._make_sql_exercise()
        fixture = {
            "setup": "CREATE TABLE t(id INTEGER, name TEXT);",
            "mode": "script",
            "check_sql": "SELECT COUNT(*) FROM t",
            "expected_rows": [[3]],
        }
        code = "INSERT INTO t VALUES (1, 'a'); INSERT INTO t VALUES (2, 'b'); INSERT INTO t VALUES (3, 'c');"
        benchmark(evaluate_sql_fixture, exercise, code, fixture)


# ── normalize_rows 基准 ─────────────────────────────────────────────────────


class TestNormalizeRows:
    """基准: normalize_rows 不同数据规模。"""

    def test_normalize_10_rows(self, benchmark):
        rows = [(i, f"name_{i}", i * 1.5) for i in range(10)]
        benchmark(normalize_rows, rows, False)

    def test_normalize_100_rows(self, benchmark):
        rows = [(i, f"name_{i}", i * 1.5) for i in range(100)]
        benchmark(normalize_rows, rows, False)

    def test_normalize_1000_rows(self, benchmark):
        rows = [(i, f"name_{i}", i * 1.5) for i in range(1000)]
        benchmark(normalize_rows, rows, False)

    def test_normalize_1000_rows_ordered(self, benchmark):
        rows = [(i, f"name_{i}", i * 1.5) for i in range(1000)]
        benchmark(normalize_rows, rows, True)

    def test_normalize_10000_rows(self, benchmark):
        rows = [(i, f"name_{i}", i * 1.5, f"extra_{i}") for i in range(10000)]
        benchmark(normalize_rows, rows, False)


# ── Exercise 构建基准 ────────────────────────────────────────────────────────


class TestExerciseConstruction:
    """基准: Exercise 数据类构建。"""

    def test_exercise_minimal(self, benchmark):
        def build():
            return Exercise(
                id="ex-1",
                title="练习",
                track_id="python",
                difficulty="基础",
                prompt="实现。",
                lesson_id="l1",
            )

        benchmark(build)

    def test_exercise_full(self, benchmark):
        def build():
            return Exercise(
                id="ex-full",
                title="完整练习定义",
                track_id="python",
                difficulty="进阶",
                prompt="实现一个完整的排序算法。" * 10,
                lesson_id="l-full",
                hints=[f"提示 {i}" for i in range(10)],
                starter_code="def sort(arr):\n    pass\n",
                expected_nodes=["FunctionDef", "For", "If"],
                required_names=["sort"],
                tests=[{"expression": f"sort([{i}])", "expected": [i]} for i in range(20)],
                required_keywords=["def", "for", "if", "return"],
                forbidden_keywords=["sort("],
            )

        benchmark(build)
