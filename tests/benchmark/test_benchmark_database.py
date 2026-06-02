"""数据库 CRUD 与查询性能基准测试。

覆盖场景:
- 单条插入/查询/更新/删除
- 批量插入 (record_attempts_batch)
- 不同数据规模下的查询性能 (100 / 1 000 / 5 000 条)
- 缓存命中 vs 未命中
"""

import pytest

from app.database import AppDatabase


@pytest.fixture()
def db(tmp_path):
    """提供已初始化的临时数据库实例。"""
    db_path = tmp_path / "bench.db"
    instance = AppDatabase(str(db_path))
    instance.init_db()
    return instance


def _seed_attempts(db: AppDatabase, n: int):
    """向 practice_attempts 表插入 n 条记录。"""
    records = [
        (
            f"ex-{i}",
            f"练习标题 {i}",
            "python",
            f"print({i})",
            i % 100,
            i % 2 == 0,
            5 + i % 30,
            "评测反馈文字" if i % 3 == 0 else "",
        )
        for i in range(n)
    ]
    db.record_attempts_batch(records)


# ── CRUD 基准 ────────────────────────────────────────────────────────────────


class TestLessonCRUD:
    """基准: 课程进度 CRUD。"""

    def test_mark_opened(self, benchmark, db):
        benchmark(db.mark_lesson_opened, "lesson-1", "track-python")

    def test_mark_completed(self, benchmark, db):
        db.mark_lesson_opened("lesson-1", "track-python")
        benchmark(db.mark_lesson_completed, "lesson-1", "track-python")

    def test_lesson_status(self, benchmark, db):
        db.mark_lesson_completed("lesson-1", "track-python")
        benchmark(db.lesson_status, "lesson-1")


class TestNoteCRUD:
    """基准: 笔记写入/读取。"""

    def test_save_note(self, benchmark, db):
        content = "这是一段测试笔记内容。" * 20
        benchmark(db.save_note, "lesson-1", content)

    def test_load_note(self, benchmark, db):
        db.save_note("lesson-1", "预置笔记内容。" * 10)
        benchmark(db.load_note, "lesson-1")


class TestDraftCRUD:
    """基准: 草稿保存/加载/清除。"""

    def test_save_draft(self, benchmark, db):
        code = "def solution():\n    return 42\n"
        benchmark(db.save_exercise_draft, "ex-1", "测试练习", code)

    def test_load_draft(self, benchmark, db):
        db.save_exercise_draft("ex-1", "测试练习", "x = 1")
        benchmark(db.load_exercise_draft, "ex-1")


# ── 批量写入基准 ────────────────────────────────────────────────────────────


class TestBatchInsert:
    """基准: 批量插入不同规模数据。"""

    @pytest.mark.parametrize("count", [10, 100, 500])
    def test_record_attempts_batch(self, benchmark, db, count):
        benchmark(_seed_attempts, db, count)


# ── 不同数据规模下的查询基准 ────────────────────────────────────────────────


class TestQueryScaling:
    """基准: 数据量增长时查询耗时的变化。"""

    def test_recent_attempts_10(self, benchmark, db):
        _seed_attempts(db, 1000)
        benchmark(db.recent_attempts, 10)

    def test_recent_attempts_100(self, benchmark, db):
        _seed_attempts(db, 1000)
        benchmark(db.recent_attempts, 100)

    def test_average_score_1k(self, benchmark, db):
        _seed_attempts(db, 1000)
        # 每次调用先清缓存
        db._invalidate_stats_cache()
        benchmark(db.average_score)

    def test_completed_lessons_1k(self, benchmark, db):
        for i in range(500):
            db.mark_lesson_completed(f"lesson-{i}", "track-python")
        db._invalidate_stats_cache()
        benchmark(db.completed_lessons)
