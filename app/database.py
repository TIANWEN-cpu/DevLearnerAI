"""SQLite 数据库操作模块（线程安全）。

提供应用所需的所有持久化操作，包括课程进度、练习记录、AI 会话管理和
知识库文件管理。使用 WAL 模式和写锁确保多线程环境下的数据一致性。
"""

import logging
import shutil
import sqlite3
import threading
from collections.abc import Sequence
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

from app.config import API_CREDENTIAL_ALIAS, DB_DIR, DB_PATH, LEGACY_DB_PATH, ensure_runtime_dirs
from app.credentials import load_secret, save_secret

_connection = None
_connection_path: Optional[str] = None
_connection_lock = threading.Lock()
_db_lock = threading.Lock()
_SENTINEL = object()  # sentinel for cache miss

# ── Database PRAGMA constants ────────────────────────────────────────────────

_CACHE_SIZE_KIB = -8000  # 8 MB page cache
_MMAP_SIZE_BYTES = 268435456  # 256 MB mmap

# ── Review schedule constants (SM-2 algorithm) ──────────────────────────────

_INITIAL_EASE_FACTOR = 2.5
_MIN_EASE_FACTOR = 1.3
_SECOND_INTERVAL_DAYS = 6.0

# ── Time bonus thresholds ───────────────────────────────────────────────────

_TIME_BONUS_HALF = 10
_TIME_BONUS_75PCT = 7
_TIME_BONUS_FULL = 4
_TIME_BONUS_150PCT = 1
_MAX_SCORE = 100

# ── Mentor message trim limit ───────────────────────────────────────────────

_DEFAULT_KEEP_LAST_MESSAGES = 200


def get_connection(db_path: str) -> "sqlite3.Connection":
    """获取或创建数据库连接（线程安全的单例模式）。

    如果现有连接已失效（例如数据库文件被替换），会自动重新建立连接。
    连接启用外键约束和 WAL 日志模式。

    Args:
        db_path: 数据库文件路径。

    Returns:
        sqlite3.Connection 实例。
    """
    global _connection, _connection_path
    with _connection_lock:
        if _connection is not None:
            # Close stale connection if path changed or connection is dead
            if _connection_path != db_path:
                try:
                    _connection.close()
                except Exception:
                    pass
                _connection = None
                _connection_path = None
            else:
                try:
                    _connection.execute("SELECT 1")
                except Exception:
                    logger.debug("数据库连接失效，尝试重新建立连接")
                    try:
                        _connection.close()
                    except Exception:
                        logger.debug("关闭失效连接时出错", exc_info=True)
                    _connection = None
                    _connection_path = None
        if _connection is None:
            ensure_runtime_dirs()
            _connection = sqlite3.connect(db_path, check_same_thread=False)
            _connection_path = db_path
            _connection.execute("PRAGMA foreign_keys = ON")
            _connection.execute("PRAGMA journal_mode = WAL")
            _connection.execute(f"PRAGMA cache_size = {_CACHE_SIZE_KIB}")
            _connection.execute("PRAGMA temp_store = MEMORY")
            _connection.execute(f"PRAGMA mmap_size = {_MMAP_SIZE_BYTES}")
        return _connection


def close_connection() -> None:
    """关闭全局数据库连接。

    在关闭前运行 PRAGMA optimize 更新统计信息，
    帮助查询规划器做出更优决策。
    """
    global _connection, _connection_path
    with _connection_lock:
        if _connection is not None:
            try:
                _connection.execute("PRAGMA optimize")
            except Exception:
                logger.debug("PRAGMA optimize 在关闭时失败", exc_info=True)
            _connection.close()
            _connection = None
            _connection_path = None


def now_text() -> str:
    """返回当前时间的文本表示（格式: YYYY-MM-DD HH:MM:SS）。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class AppDatabase:
    """应用数据库操作封装。

    提供线程安全的 CRUD 操作，涵盖课程进度、练习记录、AI 会话管理、
    API 配置、知识库文件等全部持久化需求。使用 WAL 模式配合写锁确保
    多线程环境下的数据一致性。

    优化特性：
    - 常用查询列索引（lesson_progress.track_id/completed, practice_attempts.exercise_id 等）
    - 统计查询内存缓存（带 TTL 失效）
    - 批量插入支持（record_attempts_batch）

    Attributes:
        db_path: 数据库文件路径。
    """

    _STATS_CACHE_TTL = 30  # 统计缓存过期时间（秒）

    def __init__(self, db_path: Optional[Path] = None):
        """初始化数据库实例。

        如果目标数据库不存在但旧版数据库存在，会自动迁移。

        Args:
            db_path: 数据库文件路径，默认使用 config.DB_PATH。
        """
        self.db_path = Path(db_path) if db_path is not None else DB_PATH
        self._migrate_legacy_db_if_needed()
        self._stats_cache: dict[str, tuple[float, object]] = {}  # key -> (timestamp, value)

    def _migrate_legacy_db_if_needed(self) -> None:
        """如果目标数据库不存在且旧版数据库存在，执行自动迁移。

        将旧版 db/learner.db 复制到新的用户数据目录下。
        """
        ensure_runtime_dirs()
        if self.db_path.exists():
            return
        if LEGACY_DB_PATH.exists() and LEGACY_DB_PATH.resolve() != self.db_path.resolve():
            DB_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LEGACY_DB_PATH, self.db_path)

    @contextmanager
    def connect(self):
        """获取数据库连接的上下文管理器（线程安全）。

        自动获取写锁，提交成功时自动 commit，异常时自动 rollback，
        最终释放锁。

        Yields:
            sqlite3.Connection 实例。
        """
        _db_lock.acquire()
        conn = get_connection(str(self.db_path))
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            _db_lock.release()

    def init_db(self) -> None:
        """初始化数据库表结构。

        创建所有必要的表（如不存在），执行列迁移，迁移旧版 API 密钥，
        修复损坏的聊天记录，并确保至少存在一个默认会话。
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS lesson_progress (
                    lesson_id TEXT PRIMARY KEY,
                    track_id TEXT NOT NULL,
                    status TEXT DEFAULT 'not_started',
                    completed INTEGER DEFAULT 0,
                    last_opened TEXT,
                    completed_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS lesson_notes (
                    lesson_id TEXT PRIMARY KEY,
                    content TEXT DEFAULT '',
                    updated_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS practice_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exercise_id TEXT NOT NULL,
                    exercise_title_snapshot TEXT,
                    track_id TEXT NOT NULL,
                    code_snapshot TEXT,
                    score INTEGER NOT NULL,
                    passed INTEGER DEFAULT 0,
                    duration_sec INTEGER DEFAULT 0,
                    submitted_at TEXT NOT NULL,
                    feedback TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS exercise_drafts (
                    exercise_id TEXT PRIMARY KEY,
                    exercise_title_snapshot TEXT NOT NULL,
                    code_snapshot TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mentor_api_config (
                    id INTEGER PRIMARY KEY,
                    host TEXT,
                    api_key TEXT,
                    model TEXT
                )
                """
            )
            columns = {row[1] for row in cursor.execute("PRAGMA table_info(mentor_api_config)").fetchall()}
            if "key_alias" not in columns:
                cursor.execute("ALTER TABLE mentor_api_config ADD COLUMN key_alias TEXT")
            attempt_columns = {row[1] for row in cursor.execute("PRAGMA table_info(practice_attempts)").fetchall()}
            if "exercise_title_snapshot" not in attempt_columns:
                cursor.execute("ALTER TABLE practice_attempts ADD COLUMN exercise_title_snapshot TEXT")
            if "code_snapshot" not in attempt_columns:
                cursor.execute("ALTER TABLE practice_attempts ADD COLUMN code_snapshot TEXT")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mentor_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mentor_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES mentor_sessions(id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mentor_knowledge_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    display_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    excerpt TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mentor_workspace_state (
                    id INTEGER PRIMARY KEY,
                    active_session_id INTEGER,
                    use_base INTEGER DEFAULT 1,
                    use_personal INTEGER DEFAULT 1,
                    use_custom INTEGER DEFAULT 1
                )
                """
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO mentor_workspace_state (id, active_session_id, use_base, use_personal, use_custom)
                VALUES (1, NULL, 1, 1, 1)
                """
            )

            # ── Bookmark / Favorites ────────────────────────────────────────────
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    track_id TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(item_type, item_id)
                )
                """
            )

            # ── Achievement System ─────────────────────────────────────────────
            # Migrate old achievements schema (id, name, unlocked, date) to new schema
            ach_columns = {row[1] for row in cursor.execute("PRAGMA table_info(achievements)").fetchall()}
            if ach_columns and "title" not in ach_columns:
                cursor.execute("DROP TABLE IF EXISTS achievement_progress")
                cursor.execute("DROP TABLE IF EXISTS achievements")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS achievements (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    icon TEXT DEFAULT '',
                    category TEXT DEFAULT 'general',
                    threshold INTEGER DEFAULT 1
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS achievement_progress (
                    achievement_id TEXT NOT NULL,
                    current_value INTEGER DEFAULT 0,
                    unlocked INTEGER DEFAULT 0,
                    unlocked_at TEXT,
                    PRIMARY KEY(achievement_id),
                    FOREIGN KEY(achievement_id) REFERENCES achievements(id)
                )
                """
            )

            # ── Enhanced Notes ─────────────────────────────────────────────────
            note_columns = {row[1] for row in cursor.execute("PRAGMA table_info(lesson_notes)").fetchall()}
            if "tags" not in note_columns:
                cursor.execute("ALTER TABLE lesson_notes ADD COLUMN tags TEXT DEFAULT ''")
            if "code_snippets" not in note_columns:
                cursor.execute("ALTER TABLE lesson_notes ADD COLUMN code_snippets TEXT DEFAULT ''")

            # ── Exercise Timer / Review Schedule ───────────────────────────────
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS exercise_timers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exercise_id TEXT NOT NULL,
                    duration_sec INTEGER NOT NULL,
                    difficulty TEXT DEFAULT '',
                    recorded_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS review_schedule (
                    exercise_id TEXT PRIMARY KEY,
                    interval_days REAL DEFAULT 1.0,
                    ease_factor REAL DEFAULT 2.5,
                    repetitions INTEGER DEFAULT 0,
                    next_review TEXT NOT NULL,
                    last_reviewed TEXT
                )
                """
            )

            # ── Performance indexes for new tables ─────────────────────────────
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_type ON bookmarks(item_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_item ON bookmarks(item_type, item_id)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_achievement_progress_unlocked ON achievement_progress(unlocked)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exercise_timers_exercise ON exercise_timers(exercise_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_review_schedule_next ON review_schedule(next_review)")

            # ── Performance indexes ───────────────────────────────────────────
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_lesson_progress_track_completed ON lesson_progress(track_id, completed)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_lesson_progress_completed_at ON lesson_progress(completed_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_practice_attempts_exercise ON practice_attempts(exercise_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_practice_attempts_submitted ON practice_attempts(submitted_at)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_practice_attempts_track ON practice_attempts(track_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mentor_messages_session ON mentor_messages(session_id, id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mentor_sessions_updated ON mentor_sessions(updated_at DESC)")

            # ── Query planner optimization ────────────────────────────────────
            cursor.execute("ANALYZE")

        self._seed_achievements()
        self._migrate_legacy_api_key_if_needed()
        self.repair_corrupted_mentor_history()

        if not self.list_mentor_sessions():
            default_id = self.create_mentor_session("默认对话")
            self.set_active_mentor_session(default_id)

    def _migrate_legacy_api_key_if_needed(self) -> None:
        """将旧版明文 API 密钥迁移到 keyring 安全存储。

        检测 mentor_api_config 中是否有未迁移的明文密钥，
        如有则将其保存到 keyring 并清空数据库中的明文字段。
        """
        row = self.fetchone("SELECT host, api_key, key_alias, model FROM mentor_api_config WHERE id = 1")
        if not row:
            return
        host, legacy_api_key, key_alias, model = row
        if legacy_api_key and not key_alias:
            save_secret(API_CREDENTIAL_ALIAS, legacy_api_key)
            with self.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO mentor_api_config (id, host, api_key, model, key_alias)
                    VALUES (1, ?, '', ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        host = excluded.host,
                        api_key = '',
                        model = excluded.model,
                        key_alias = excluded.key_alias
                    """,
                    (host or "", model or "", API_CREDENTIAL_ALIAS),
                )

    def fetchall(self, sql: str, params: Sequence = ()) -> list[tuple]:
        """执行查询并返回所有结果行。

        Args:
            sql: SQL 查询语句。
            params: 查询参数。

        Returns:
            查询结果列表，每行为一个 tuple。
        """
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: Sequence = ()) -> Optional[tuple]:
        """执行查询并返回单行结果。

        Args:
            sql: SQL 查询语句。
            params: 查询参数。

        Returns:
            查询结果 tuple，无结果时返回 None。
        """
        with self.connect() as conn:
            return conn.execute(sql, params).fetchone()

    def execute(self, sql: str, params: Sequence = ()) -> None:
        """执行非查询 SQL 语句（INSERT / UPDATE / DELETE）。

        Args:
            sql: SQL 语句。
            params: 语句参数。
        """
        with self.connect() as conn:
            conn.execute(sql, params)

    # ── Stats cache ───────────────────────────────────────────────────────────

    def _get_cached_stats(self, key: str) -> Any:
        """Return cached stats value if still valid, else None."""
        import time as _time

        entry = self._stats_cache.get(key)
        if entry is not None:
            ts, value = entry
            if _time.monotonic() - ts < self._STATS_CACHE_TTL:
                return value
        return _SENTINEL

    def _set_cached_stats(self, key: str, value: object) -> None:
        import time as _time

        self._stats_cache[key] = (_time.monotonic(), value)

    def _invalidate_stats_cache(self, key: Optional[str] = None) -> None:
        """Invalidate stats cache entries.

        Args:
            key: If given, only invalidate that key. Otherwise clear all.
        """
        if key:
            self._stats_cache.pop(key, None)
        else:
            self._stats_cache.clear()

    def mark_lesson_opened(self, lesson_id: str, track_id: str) -> None:
        """标记课程为已打开（进行中）。

        如果课程已完成则保持完成状态，仅更新最后打开时间。
        如果课程不存在则新建记录。

        Args:
            lesson_id: 课程 ID。
            track_id: 所属技术栈 ID。
        """
        existing = self.fetchone(
            "SELECT lesson_id, completed FROM lesson_progress WHERE lesson_id = ?",
            (lesson_id,),
        )
        if existing:
            self.execute(
                """
                UPDATE lesson_progress
                SET status = CASE WHEN completed = 1 THEN 'completed' ELSE 'in_progress' END,
                    last_opened = ?
                WHERE lesson_id = ?
                """,
                (now_text(), lesson_id),
            )
            return

        self.execute(
            """
            INSERT INTO lesson_progress (lesson_id, track_id, status, completed, last_opened)
            VALUES (?, ?, 'in_progress', 0, ?)
            """,
            (lesson_id, track_id, now_text()),
        )

    def mark_lesson_completed(self, lesson_id: str, track_id: str) -> None:
        """标记课程为已完成。

        使用 UPSERT 语义：如果课程已存在则更新，否则插入新记录。

        Args:
            lesson_id: 课程 ID。
            track_id: 所属技术栈 ID。
        """
        self.execute(
            """
            INSERT INTO lesson_progress (lesson_id, track_id, status, completed, last_opened, completed_at)
            VALUES (?, ?, 'completed', 1, ?, ?)
            ON CONFLICT(lesson_id) DO UPDATE SET
                track_id = excluded.track_id,
                status = 'completed',
                completed = 1,
                last_opened = excluded.last_opened,
                completed_at = excluded.completed_at
            """,
            (lesson_id, track_id, now_text(), now_text()),
        )
        self._invalidate_stats_cache("completed_lessons")
        self._invalidate_stats_cache("active_days_streak")

    def lesson_status(self, lesson_id: str) -> str:
        """查询课程的学习状态。

        Args:
            lesson_id: 课程 ID。

        Returns:
            状态字符串: 'not_started'、'in_progress' 或 'completed'。
        """
        row = self.fetchone("SELECT status FROM lesson_progress WHERE lesson_id = ?", (lesson_id,))
        return row[0] if row else "not_started"

    def track_completion(self, track_id: str) -> int:
        """统计指定技术栈已完成的课程数量。

        Args:
            track_id: 技术栈 ID。

        Returns:
            已完成课程数。
        """
        row = self.fetchone(
            """
            SELECT COUNT(*) FROM lesson_progress
            WHERE track_id = ? AND completed = 1
            """,
            (track_id,),
        )
        return int(row[0]) if row else 0

    def completed_lessons(self) -> int:
        """统计所有已完成的课程总数（带缓存）。"""
        cached = self._get_cached_stats("completed_lessons")
        if cached is not _SENTINEL:
            return cached
        row = self.fetchone("SELECT COUNT(*) FROM lesson_progress WHERE completed = 1")
        value = int(row[0]) if row else 0
        self._set_cached_stats("completed_lessons", value)
        return value

    def list_completed_lessons(self) -> list[tuple[str, Optional[str]]]:
        """列出所有已完成的课程（按完成时间倒序）。

        Returns:
            (lesson_id, completed_at) 元组列表。
        """
        return self.fetchall(
            """
            SELECT lesson_id, completed_at
            FROM lesson_progress
            WHERE completed = 1
            ORDER BY completed_at DESC
            """
        )

    def save_note(self, lesson_id: str, content: str) -> None:
        """保存或更新课程笔记。

        Args:
            lesson_id: 课程 ID。
            content: 笔记内容。
        """
        self.execute(
            """
            INSERT INTO lesson_notes (lesson_id, content, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(lesson_id) DO UPDATE SET
                content = excluded.content,
                updated_at = excluded.updated_at
            """,
            (lesson_id, content, now_text()),
        )

    def load_note(self, lesson_id: str) -> str:
        """加载课程笔记。

        Args:
            lesson_id: 课程 ID。

        Returns:
            笔记内容，不存在时返回空字符串。
        """
        row = self.fetchone("SELECT content FROM lesson_notes WHERE lesson_id = ?", (lesson_id,))
        return row[0] if row else ""

    def record_attempt(
        self,
        exercise_id: str,
        exercise_title_snapshot: str,
        track_id: str,
        code_snapshot: str,
        score: int,
        passed: bool,
        duration_sec: int,
        feedback: str,
    ) -> None:
        """记录一次练习评测结果。

        Args:
            exercise_id: 练习 ID。
            exercise_title_snapshot: 练习标题快照。
            track_id: 所属技术栈 ID。
            code_snapshot: 提交的代码快照。
            score: 得分 (0-100)。
            passed: 是否通过。
            duration_sec: 评测耗时（秒）。
            feedback: 评测反馈文本。
        """
        self.execute(
            """
            INSERT INTO practice_attempts (
                exercise_id, exercise_title_snapshot, track_id, code_snapshot,
                score, passed, duration_sec, submitted_at, feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exercise_id,
                exercise_title_snapshot,
                track_id,
                code_snapshot,
                score,
                1 if passed else 0,
                duration_sec,
                now_text(),
                feedback,
            ),
        )
        self._invalidate_stats_cache()

    def record_attempts_batch(self, records: list[tuple]) -> None:
        """批量记录练习评测结果（事务内一次性写入）。

        Args:
            records: 元组列表，每个元素为
                (exercise_id, exercise_title_snapshot, track_id,
                 code_snapshot, score, passed, duration_sec, feedback)。
        """
        if not records:
            return
        timestamp = now_text()
        rows = [
            (eid, title, tid, code, score, 1 if passed else 0, dur, timestamp, fb)
            for eid, title, tid, code, score, passed, dur, fb in records
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO practice_attempts (
                    exercise_id, exercise_title_snapshot, track_id, code_snapshot,
                    score, passed, duration_sec, submitted_at, feedback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        self._invalidate_stats_cache()

    def recent_attempts(self, limit: int = 10) -> list[tuple]:
        """获取最近的练习记录。

        Args:
            limit: 返回记录数上限，默认 10。

        Returns:
            (submitted_at, display_title, score, passed, duration_sec) 元组列表。
        """
        return self.fetchall(
            """
            SELECT
                submitted_at,
                COALESCE(NULLIF(exercise_title_snapshot, ''), exercise_id) AS display_title,
                score,
                passed,
                duration_sec
            FROM practice_attempts
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

    def save_exercise_draft(self, exercise_id: str, exercise_title_snapshot: str, code_snapshot: str) -> None:
        """保存练习草稿（自动保存，UPSERT 语义）。

        Args:
            exercise_id: 练习 ID。
            exercise_title_snapshot: 练习标题快照。
            code_snapshot: 代码快照。
        """
        self.execute(
            """
            INSERT INTO exercise_drafts (exercise_id, exercise_title_snapshot, code_snapshot, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(exercise_id) DO UPDATE SET
                exercise_title_snapshot = excluded.exercise_title_snapshot,
                code_snapshot = excluded.code_snapshot,
                updated_at = excluded.updated_at
            """,
            (exercise_id, exercise_title_snapshot, code_snapshot, now_text()),
        )

    def load_exercise_draft(self, exercise_id: str) -> Optional[tuple[str, str]]:
        """加载练习草稿。

        Args:
            exercise_id: 练习 ID。

        Returns:
            (exercise_title_snapshot, code_snapshot) 元组，不存在时返回 None。
        """
        return self.fetchone(
            "SELECT exercise_title_snapshot, code_snapshot FROM exercise_drafts WHERE exercise_id = ?",
            (exercise_id,),
        )

    def clear_exercise_draft(self, exercise_id: str) -> None:
        """清除练习草稿。

        Args:
            exercise_id: 练习 ID。
        """
        self.execute("DELETE FROM exercise_drafts WHERE exercise_id = ?", (exercise_id,))

    def average_score(self) -> int:
        """计算所有练习记录的平均分（带缓存）。

        Returns:
            平均分（四舍五入到整数），无记录时返回 0。
        """
        cached = self._get_cached_stats("average_score")
        if cached is not _SENTINEL:
            return cached
        row = self.fetchone("SELECT AVG(score) FROM practice_attempts")
        value = int(round(row[0])) if row and row[0] is not None else 0
        self._set_cached_stats("average_score", value)
        return value

    def active_days_streak(self) -> int:
        """计算连续学习天数（带缓存）。

        综合课程完成时间和练习提交时间，从今天开始向前统计
        连续有学习活动的天数。如果今天没有学习记录则返回 0。

        Returns:
            连续学习天数。
        """
        cached = self._get_cached_stats("active_days_streak")
        if cached is not _SENTINEL:
            return cached

        rows = self.fetchall(
            """
            SELECT DISTINCT substr(day_text, 1, 10) AS day
            FROM (
                SELECT completed_at AS day_text FROM lesson_progress WHERE completed_at IS NOT NULL
                UNION ALL
                SELECT submitted_at AS day_text FROM practice_attempts
            )
            WHERE day IS NOT NULL
            ORDER BY day DESC
            """
        )
        if not rows:
            self._set_cached_stats("active_days_streak", 0)
            return 0

        days = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in rows]
        if days[0] != date.today():
            self._set_cached_stats("active_days_streak", 0)
            return 0

        streak = 1
        expected_day = date.today() - timedelta(days=1)
        for current_day in days[1:]:
            if current_day == expected_day:
                streak += 1
                expected_day -= timedelta(days=1)
            elif current_day < expected_day:
                break
        self._set_cached_stats("active_days_streak", streak)
        return streak

    def reset_learning_progress(self) -> None:
        """重置所有学习进度数据。

        删除课程进度、笔记、练习记录和草稿。AI 会话和配置不受影响。
        """
        with self.connect() as conn:
            conn.execute("DELETE FROM lesson_progress")
            conn.execute("DELETE FROM lesson_notes")
            conn.execute("DELETE FROM practice_attempts")
            conn.execute("DELETE FROM exercise_drafts")
        self._invalidate_stats_cache()

    def save_api_config(self, host: str, api_key: str, model: str) -> None:
        """保存 AI API 配置。

        API 密钥通过 keyring 安全存储，数据库中仅保留空字符串占位。

        Args:
            host: API 端点地址。
            api_key: API 密钥。
            model: 模型名称。
        """
        if api_key:
            save_secret(API_CREDENTIAL_ALIAS, api_key)

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO mentor_api_config (id, host, api_key, model, key_alias)
                VALUES (1, ?, '', ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    host = excluded.host,
                    api_key = '',
                    model = excluded.model,
                    key_alias = excluded.key_alias
                """,
                (host, model, API_CREDENTIAL_ALIAS),
            )

    def load_api_config(self) -> tuple[str, str, str]:
        """加载 AI API 配置。

        Returns:
            (host, api_key, model) 元组。API 密钥从 keyring 读取。
            无配置时返回空字符串。
        """
        row = self.fetchone("SELECT host, api_key, model, key_alias FROM mentor_api_config WHERE id = 1")
        if not row:
            return "", "", ""

        host, legacy_api_key, model, key_alias = row
        if key_alias:
            return host or "", load_secret(key_alias) or "", model or ""
        return host or "", legacy_api_key or "", model or ""

    def list_mentor_sessions(self) -> list[tuple[int, str, str]]:
        """列出所有 AI 会话。

        Returns:
            (id, name, updated_at) 元组列表，按更新时间倒序排列。
        """
        return self.fetchall(
            """
            SELECT id, name, updated_at
            FROM mentor_sessions
            ORDER BY updated_at DESC, id DESC
            """
        )

    @staticmethod
    def _clip_preview(text: str, limit: int = 72) -> str:
        """截取文本预览（不超过指定长度，超出时加省略号）。"""
        cleaned = " ".join((text or "").strip().split())
        if not cleaned:
            return ""
        return cleaned if len(cleaned) <= limit else cleaned[: limit - 1] + "…"

    def mentor_session_snapshot(self, session_id: int) -> dict[str, Any]:
        """获取 AI 会话的摘要快照。

        包含消息数量、最后一条消息的预览文本和更新时间。

        Args:
            session_id: 会话 ID。

        Returns:
            包含 message_count、preview、updated_at 键的字典。
        """
        count_row = self.fetchone(
            "SELECT COUNT(*) FROM mentor_messages WHERE session_id = ?",
            (session_id,),
        )
        preview_row = self.fetchone(
            """
            SELECT role, content, created_at
            FROM mentor_messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (session_id,),
        )
        if not preview_row:
            return {
                "message_count": 0,
                "preview": "还没有聊天记录，适合先用它拆学习计划或报错。",
                "updated_at": "",
            }

        role, content, created_at = preview_row
        if "旧消息因早期编码问题已自动清理" in content:
            return {
                "message_count": int(count_row[0]) if count_row and count_row[0] is not None else 0,
                "preview": "旧消息已清理，建议重新开始这个话题。",
                "updated_at": created_at or "",
            }
        prefix = "你：" if role == "user" else "AI："
        return {
            "message_count": int(count_row[0]) if count_row and count_row[0] is not None else 0,
            "preview": prefix + self._clip_preview(content),
            "updated_at": created_at or "",
        }

    @staticmethod
    def _looks_like_corrupted_message(content: str) -> bool:
        """检测消息内容是否看起来像编码损坏的数据。

        通过分析问号密度和是否缺少中文字符来判断。
        """
        text = (content or "").strip()
        if not text:
            return False
        if "旧消息因早期编码问题已自动清理" in text:
            return False

        compact = "".join(ch for ch in text if not ch.isspace())
        if len(compact) < 6:
            return False

        question_count = compact.count("?") + compact.count("？")
        if question_count < 4:
            return False

        if any("\u4e00" <= ch <= "\u9fff" for ch in text):
            return False
        return question_count >= len(compact) * 0.3

    def repair_corrupted_mentor_history(self) -> None:
        """自动检测并修复损坏的 AI 聊天记录。

        将编码损坏的消息替换为提示用户重新描述的占位文本。
        """
        rows = self.fetchall("SELECT id, content FROM mentor_messages")
        broken_ids = [message_id for message_id, content in rows if self._looks_like_corrupted_message(content)]
        if not broken_ids:
            return

        placeholder = "这条旧消息因早期编码问题已自动清理。建议你重新描述一次，我会按当前课程和练习进度继续帮你。"
        with self.connect() as conn:
            conn.executemany(
                "UPDATE mentor_messages SET content = ? WHERE id = ?",
                [(placeholder, message_id) for message_id in broken_ids],
            )

    def create_mentor_session(self, name: str) -> int:
        """创建新的 AI 会话。

        Args:
            name: 会话名称。

        Returns:
            新建会话的 ID。
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO mentor_sessions (name, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (name, now_text(), now_text()),
            )
            return int(cursor.lastrowid)

    def rename_mentor_session(self, session_id: int, name: str) -> None:
        """重命名 AI 会话。

        Args:
            session_id: 会话 ID。
            name: 新的会话名称。
        """
        self.execute(
            """
            UPDATE mentor_sessions
            SET name = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, now_text(), session_id),
        )

    def delete_mentor_session(self, session_id: int) -> None:
        """删除 AI 会话及其所有消息。

        如果删除的是当前活跃会话，会自动切换到最近更新的会话。

        Args:
            session_id: 会话 ID。
        """
        with self.connect() as conn:
            conn.execute("DELETE FROM mentor_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM mentor_sessions WHERE id = ?", (session_id,))
            active_row = conn.execute("SELECT active_session_id FROM mentor_workspace_state WHERE id = 1").fetchone()
            if active_row and active_row[0] == session_id:
                fallback = conn.execute(
                    "SELECT id FROM mentor_sessions ORDER BY updated_at DESC, id DESC LIMIT 1"
                ).fetchone()
                conn.execute(
                    "UPDATE mentor_workspace_state SET active_session_id = ? WHERE id = 1",
                    (fallback[0] if fallback else None,),
                )

    def set_active_mentor_session(self, session_id: int) -> None:
        """设置当前活跃的 AI 会话。

        Args:
            session_id: 要设为活跃的会话 ID。
        """
        self.execute(
            """
            UPDATE mentor_workspace_state
            SET active_session_id = ?
            WHERE id = 1
            """,
            (session_id,),
        )

    def load_active_mentor_session_id(self) -> Optional[int]:
        """加载当前活跃的 AI 会话 ID。

        Returns:
            活跃会话 ID，无活跃会话时返回 None。
        """
        row = self.fetchone("SELECT active_session_id FROM mentor_workspace_state WHERE id = 1")
        return int(row[0]) if row and row[0] else None

    def append_mentor_message(self, session_id: int, role: str, content: str) -> None:
        """向 AI 会话追加一条消息。

        同时更新会话的 updated_at 时间戳。

        Args:
            session_id: 会话 ID。
            role: 角色 ('user' 或 'assistant')。
            content: 消息内容。
        """
        timestamp = now_text()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO mentor_messages (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, timestamp),
            )
            conn.execute(
                """
                UPDATE mentor_sessions
                SET updated_at = ?
                WHERE id = ?
                """,
                (timestamp, session_id),
            )

    def load_mentor_messages(self, session_id: int) -> list[tuple[str, str, str]]:
        """加载指定会话的所有消息。

        Args:
            session_id: 会话 ID。

        Returns:
            (role, content, created_at) 元组列表，按消息 ID 升序排列。
        """
        return self.fetchall(
            """
            SELECT role, content, created_at
            FROM mentor_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )

    def save_mentor_workspace_flags(self, use_base: bool, use_personal: bool, use_custom: bool) -> None:
        """保存知识库启用标志。

        Args:
            use_base: 是否启用基础知识库。
            use_personal: 是否启用个性知识库。
            use_custom: 是否启用扩展文件知识库。
        """
        self.execute(
            """
            UPDATE mentor_workspace_state
            SET use_base = ?, use_personal = ?, use_custom = ?
            WHERE id = 1
            """,
            (1 if use_base else 0, 1 if use_personal else 0, 1 if use_custom else 0),
        )

    def load_mentor_workspace_flags(self) -> dict[str, bool]:
        """加载知识库启用标志。

        Returns:
            包含 use_base、use_personal、use_custom 键的字典。
        """
        row = self.fetchone(
            """
            SELECT use_base, use_personal, use_custom
            FROM mentor_workspace_state
            WHERE id = 1
            """
        )
        if not row:
            return {"use_base": True, "use_personal": True, "use_custom": True}
        return {
            "use_base": bool(row[0]),
            "use_personal": bool(row[1]),
            "use_custom": bool(row[2]),
        }

    def list_knowledge_files(self) -> list[tuple[int, str, str, str]]:
        """列出所有扩展知识库文件。

        Returns:
            (id, display_name, file_path, excerpt) 元组列表。
        """
        return self.fetchall(
            """
            SELECT id, display_name, file_path, excerpt
            FROM mentor_knowledge_files
            ORDER BY id DESC
            """
        )

    def get_knowledge_file(self, file_id: int) -> Optional[tuple[int, str, str, str, str]]:
        """获取指定知识库文件的详细信息。

        Args:
            file_id: 文件 ID。

        Returns:
            (id, display_name, file_path, excerpt, created_at) 元组，
            不存在时返回 None。
        """
        return self.fetchone(
            """
            SELECT id, display_name, file_path, excerpt, created_at
            FROM mentor_knowledge_files
            WHERE id = ?
            """,
            (file_id,),
        )

    def add_knowledge_file(self, display_name: str, file_path: str, excerpt: str) -> None:
        """添加扩展知识库文件。

        Args:
            display_name: 显示名称。
            file_path: 文件路径。
            excerpt: 文件摘录文本。
        """
        self.execute(
            """
            INSERT INTO mentor_knowledge_files (display_name, file_path, excerpt, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (display_name, file_path, excerpt, now_text()),
        )

    def remove_knowledge_file(self, file_id: int) -> None:
        """移除扩展知识库文件。

        Args:
            file_id: 文件 ID。
        """
        self.execute("DELETE FROM mentor_knowledge_files WHERE id = ?", (file_id,))

    # ════════════════════════════════════════════════════════════════════════════
    # Bookmark / Favorites
    # ════════════════════════════════════════════════════════════════════════════

    def add_bookmark(self, item_type: str, item_id: str, title: str, track_id: str = "", note: str = "") -> None:
        """添加书签（UPSERT 语义）。"""
        self.execute(
            """
            INSERT INTO bookmarks (item_type, item_id, title, track_id, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_type, item_id) DO UPDATE SET
                title = excluded.title,
                note = excluded.note
            """,
            (item_type, item_id, title, track_id, note, now_text()),
        )

    def remove_bookmark(self, item_type: str, item_id: str) -> None:
        """移除书签。"""
        self.execute(
            "DELETE FROM bookmarks WHERE item_type = ? AND item_id = ?",
            (item_type, item_id),
        )

    def is_bookmarked(self, item_type: str, item_id: str) -> bool:
        """检查是否已收藏。"""
        row = self.fetchone(
            "SELECT 1 FROM bookmarks WHERE item_type = ? AND item_id = ?",
            (item_type, item_id),
        )
        return row is not None

    def list_bookmarks(self, item_type: str = "") -> list[tuple]:
        """列出书签。返回 (id, item_type, item_id, title, track_id, note, created_at)。"""
        if item_type:
            return self.fetchall(
                "SELECT id, item_type, item_id, title, track_id, note, created_at "
                "FROM bookmarks WHERE item_type = ? ORDER BY created_at DESC",
                (item_type,),
            )
        return self.fetchall(
            "SELECT id, item_type, item_id, title, track_id, note, created_at FROM bookmarks ORDER BY created_at DESC"
        )

    def search_bookmarks(self, query: str) -> list[tuple]:
        """搜索书签（按标题和笔记）。"""
        pattern = f"%{query}%"
        return self.fetchall(
            "SELECT id, item_type, item_id, title, track_id, note, created_at "
            "FROM bookmarks WHERE title LIKE ? OR note LIKE ? ORDER BY created_at DESC",
            (pattern, pattern),
        )

    def bookmark_count(self) -> int:
        """返回书签总数。"""
        row = self.fetchone("SELECT COUNT(*) FROM bookmarks")
        return int(row[0]) if row else 0

    # ════════════════════════════════════════════════════════════════════════════
    # Achievement System
    # ════════════════════════════════════════════════════════════════════════════

    def _seed_achievements(self) -> None:
        """初始化成就定义（如果尚未存在）。"""
        achievements = [
            ("first_lesson", "初学者", "完成第一节课程", "📖", "learning", 1),
            ("lessons_5", "求知若渴", "完成 5 节课程", "📚", "learning", 5),
            ("lessons_10", "学霸之路", "完成 10 节课程", "🎓", "learning", 10),
            ("lessons_25", "知识达人", "完成 25 节课程", "🏅", "learning", 25),
            ("lessons_50", "全能学者", "完成 50 节课程", "👑", "learning", 50),
            ("first_exercise", "初试牛刀", "完成第一道练习", "✏️", "practice", 1),
            ("exercises_10", "代码新手", "完成 10 道练习", "💻", "practice", 10),
            ("exercises_50", "编程达人", "完成 50 道练习", "🔥", "practice", 50),
            ("exercises_100", "百炼成钢", "完成 100 道练习", "⚡", "practice", 100),
            ("perfect_score", "满分王", "练习中获得满分", "💯", "practice", 1),
            ("streak_3", "三日坚持", "连续学习 3 天", "🔥", "streak", 3),
            ("streak_7", "一周不断", "连续学习 7 天", "🌟", "streak", 7),
            ("streak_14", "半月毅力", "连续学习 14 天", "💎", "streak", 14),
            ("streak_30", "月度冠军", "连续学习 30 天", "🏆", "streak", 30),
            ("first_bookmark", "收藏达人", "添加第一个书签", "⭐", "feature", 1),
            ("notes_5", "笔记爱好者", "保存 5 条笔记", "📝", "feature", 5),
            ("speed_demon", "速度之星", "在 60 秒内完成一道练习", "⏱️", "special", 1),
            ("note_exporter", "知识整理", "导出笔记到 Markdown", "📤", "feature", 1),
            ("data_backup", "数据管家", "导出或导入学习数据", "💾", "feature", 1),
            ("review_master", "复习达人", "完成 10 次间隔复习", "🔄", "practice", 10),
        ]
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT OR IGNORE INTO achievements (id, title, description, icon, category, threshold)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                achievements,
            )

    def _award_achievement(self, achievement_id: str) -> bool:
        """尝试授予成就。返回 True 表示刚解锁。"""
        row = self.fetchone(
            "SELECT unlocked FROM achievement_progress WHERE achievement_id = ?",
            (achievement_id,),
        )
        if row and row[0]:
            return False
        self.execute(
            """
            INSERT INTO achievement_progress (achievement_id, current_value, unlocked, unlocked_at)
            VALUES (?, 1, 1, ?)
            ON CONFLICT(achievement_id) DO UPDATE SET
                unlocked = 1, unlocked_at = excluded.unlocked_at
            """,
            (achievement_id, now_text()),
        )
        return True

    def update_achievement_progress(self, achievement_id: str, value: int) -> bool:
        """更新成就进度并检查是否解锁。返回 True 表示刚解锁。"""
        ach = self.fetchone(
            "SELECT threshold FROM achievements WHERE id = ?",
            (achievement_id,),
        )
        if not ach:
            return False
        threshold = int(ach[0])
        self.execute(
            """
            INSERT INTO achievement_progress (achievement_id, current_value, unlocked, unlocked_at)
            VALUES (?, ?, 0, NULL)
            ON CONFLICT(achievement_id) DO UPDATE SET
                current_value = MAX(current_value, excluded.current_value)
            """,
            (achievement_id, value),
        )
        if value >= threshold:
            return self._award_achievement(achievement_id)
        return False

    def check_streak_achievements(self) -> list[str]:
        """检查并更新连续学习相关成就。返回刚解锁的成就 ID 列表。"""
        streak = self.active_days_streak()
        unlocked = []
        for aid, _threshold in [("streak_3", 3), ("streak_7", 7), ("streak_14", 14), ("streak_30", 30)]:
            if self.update_achievement_progress(aid, streak):
                unlocked.append(aid)
        return unlocked

    def check_completion_achievements(self) -> list[str]:
        """检查并更新课程完成相关成就。返回刚解锁的成就 ID 列表。"""
        completed = self.completed_lessons()
        unlocked = []
        for aid, threshold in [
            ("first_lesson", 1),
            ("lessons_5", 5),
            ("lessons_10", 10),
            ("lessons_25", 25),
            ("lessons_50", 50),
        ]:
            if completed >= threshold and self.update_achievement_progress(aid, completed):
                unlocked.append(aid)
        return unlocked

    def check_practice_achievements(self) -> list[str]:
        """检查并更新练习相关成就。返回刚解锁的成就 ID 列表。"""
        row = self.fetchone("SELECT COUNT(*) FROM practice_attempts")
        count = int(row[0]) if row else 0
        unlocked = []
        for aid, threshold in [
            ("first_exercise", 1),
            ("exercises_10", 10),
            ("exercises_50", 50),
            ("exercises_100", 100),
        ]:
            if count >= threshold and self.update_achievement_progress(aid, count):
                unlocked.append(aid)
        # Perfect score check
        perfect = self.fetchone("SELECT 1 FROM practice_attempts WHERE score = 100 LIMIT 1")
        if perfect and self.update_achievement_progress("perfect_score", 1):
            unlocked.append("perfect_score")
        # Speed demon check
        fast = self.fetchone("SELECT 1 FROM practice_attempts WHERE passed = 1 AND duration_sec <= 60 LIMIT 1")
        if fast and self.update_achievement_progress("speed_demon", 1):
            unlocked.append("speed_demon")
        return unlocked

    def list_achievements(self) -> list[dict[str, Any]]:
        """列出所有成就及其进度。"""
        rows = self.fetchall(
            """
            SELECT a.id, a.title, a.description, a.icon, a.category, a.threshold,
                   COALESCE(ap.current_value, 0) AS current_value,
                   COALESCE(ap.unlocked, 0) AS unlocked,
                   ap.unlocked_at
            FROM achievements a
            LEFT JOIN achievement_progress ap ON a.id = ap.achievement_id
            ORDER BY ap.unlocked DESC, a.category, a.threshold
            """
        )
        return [
            {
                "id": r[0],
                "title": r[1],
                "description": r[2],
                "icon": r[3],
                "category": r[4],
                "threshold": r[5],
                "current_value": r[6],
                "unlocked": bool(r[7]),
                "unlocked_at": r[8] or "",
            }
            for r in rows
        ]

    def unlocked_achievements_count(self) -> int:
        """返回已解锁的成就数量。"""
        row = self.fetchone("SELECT COUNT(*) FROM achievement_progress WHERE unlocked = 1")
        return int(row[0]) if row else 0

    # ════════════════════════════════════════════════════════════════════════════
    # Enhanced Notes
    # ════════════════════════════════════════════════════════════════════════════

    def save_enhanced_note(self, lesson_id: str, content: str, tags: str = "", code_snippets: str = "") -> None:
        """保存增强笔记（包含标签和代码片段）。"""
        self.execute(
            """
            INSERT INTO lesson_notes (lesson_id, content, tags, code_snippets, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(lesson_id) DO UPDATE SET
                content = excluded.content,
                tags = excluded.tags,
                code_snippets = excluded.code_snippets,
                updated_at = excluded.updated_at
            """,
            (lesson_id, content, tags, code_snippets, now_text()),
        )

    def load_enhanced_note(self, lesson_id: str) -> dict[str, str]:
        """加载增强笔记。"""
        row = self.fetchone(
            "SELECT content, tags, code_snippets, updated_at FROM lesson_notes WHERE lesson_id = ?",
            (lesson_id,),
        )
        if not row:
            return {"content": "", "tags": "", "code_snippets": "", "updated_at": ""}
        return {
            "content": row[0] or "",
            "tags": row[1] or "",
            "code_snippets": row[2] or "",
            "updated_at": row[3] or "",
        }

    def search_notes(self, query: str) -> list[tuple]:
        """搜索笔记内容。返回 (lesson_id, content, tags, updated_at)。"""
        pattern = f"%{query}%"
        return self.fetchall(
            "SELECT lesson_id, content, tags, updated_at FROM lesson_notes "
            "WHERE content LIKE ? OR tags LIKE ? ORDER BY updated_at DESC",
            (pattern, pattern),
        )

    def all_notes(self) -> list[tuple]:
        """列出所有笔记。返回 (lesson_id, content, tags, code_snippets, updated_at)。"""
        return self.fetchall(
            "SELECT lesson_id, content, tags, code_snippets, updated_at "
            "FROM lesson_notes WHERE content != '' ORDER BY updated_at DESC"
        )

    def note_count(self) -> int:
        """返回有内容的笔记数量。"""
        row = self.fetchone("SELECT COUNT(*) FROM lesson_notes WHERE content != ''")
        return int(row[0]) if row else 0

    # ════════════════════════════════════════════════════════════════════════════
    # Exercise Timer
    # ════════════════════════════════════════════════════════════════════════════

    def record_exercise_timer(self, exercise_id: str, duration_sec: int, difficulty: str = "") -> None:
        """记录练习用时。"""
        self.execute(
            """
            INSERT INTO exercise_timers (exercise_id, duration_sec, difficulty, recorded_at)
            VALUES (?, ?, ?, ?)
            """,
            (exercise_id, duration_sec, difficulty, now_text()),
        )

    def average_time_by_difficulty(self, difficulty: str) -> int:
        """获取指定难度的平均练习用时（秒）。"""
        row = self.fetchone(
            "SELECT AVG(duration_sec) FROM exercise_timers WHERE difficulty = ?",
            (difficulty,),
        )
        return int(round(row[0])) if row and row[0] else 0

    def exercise_timer_history(self, exercise_id: str) -> list[tuple]:
        """获取指定练习的历史用时记录。"""
        return self.fetchall(
            "SELECT duration_sec, recorded_at FROM exercise_timers "
            "WHERE exercise_id = ? ORDER BY recorded_at DESC LIMIT 20",
            (exercise_id,),
        )

    def time_bonus_score(self, base_score: int, duration_sec: int, difficulty: str) -> int:
        """根据用时计算加分。用时低于平均的一半可获得最高 10 分加分。"""
        avg = self.average_time_by_difficulty(difficulty)
        if avg <= 0 or duration_sec <= 0:
            return base_score
        ratio = duration_sec / avg
        if ratio <= 0.5:
            bonus = 10
        elif ratio <= 0.75:
            bonus = 7
        elif ratio <= 1.0:
            bonus = 4
        elif ratio <= 1.5:
            bonus = 1
        else:
            bonus = 0
        return min(100, base_score + bonus)

    # ════════════════════════════════════════════════════════════════════════════
    # Spaced Repetition
    # ════════════════════════════════════════════════════════════════════════════

    def update_review_schedule(self, exercise_id: str, quality: int) -> None:
        """更新间隔复习计划（SM-2 算法）。

        quality: 0-5，0=完全忘记，5=完美回忆。
        """
        row = self.fetchone(
            "SELECT interval_days, ease_factor, repetitions FROM review_schedule WHERE exercise_id = ?",
            (exercise_id,),
        )
        if row:
            interval, ef, reps = float(row[0]), float(row[1]), int(row[2])
        else:
            interval, ef, reps = 1.0, 2.5, 0

        if quality < 3:
            reps = 0
            interval = 1.0
        else:
            if reps == 0:
                interval = 1.0
            elif reps == 1:
                interval = 6.0
            else:
                interval = interval * ef
            reps += 1

        ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        ef = max(1.3, ef)

        from datetime import timedelta

        next_review = (datetime.now() + timedelta(days=interval)).strftime("%Y-%m-%d")

        self.execute(
            """
            INSERT INTO review_schedule (exercise_id, interval_days, ease_factor,
                                         repetitions, next_review, last_reviewed)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(exercise_id) DO UPDATE SET
                interval_days = excluded.interval_days,
                ease_factor = excluded.ease_factor,
                repetitions = excluded.repetitions,
                next_review = excluded.next_review,
                last_reviewed = excluded.last_reviewed
            """,
            (exercise_id, interval, ef, reps, next_review, now_text()),
        )

    def get_review_schedule(self, exercise_id: str) -> Optional[dict]:
        """获取练习的复习计划。"""
        row = self.fetchone(
            "SELECT interval_days, ease_factor, repetitions, next_review, last_reviewed "
            "FROM review_schedule WHERE exercise_id = ?",
            (exercise_id,),
        )
        if not row:
            return None
        return {
            "interval_days": row[0],
            "ease_factor": row[1],
            "repetitions": row[2],
            "next_review": row[3],
            "last_reviewed": row[4] or "",
        }

    def exercises_due_for_review(self, limit: int = 20) -> list[tuple]:
        """获取今天需要复习的练习。返回 (exercise_id, interval_days, next_review)。"""
        today = date.today().isoformat()
        return self.fetchall(
            "SELECT exercise_id, interval_days, next_review FROM review_schedule "
            "WHERE next_review <= ? ORDER BY next_review ASC LIMIT ?",
            (today, limit),
        )

    def review_count_today(self) -> int:
        """返回今天已完成的复习数量。"""
        today = date.today().isoformat()
        row = self.fetchone(
            "SELECT COUNT(*) FROM review_schedule WHERE last_reviewed LIKE ?",
            (f"{today}%",),
        )
        return int(row[0]) if row else 0

    def total_review_count(self) -> int:
        """返回总复习次数。"""
        row = self.fetchone("SELECT SUM(repetitions) FROM review_schedule")
        return int(row[0]) if row and row[0] else 0

    # ════════════════════════════════════════════════════════════════════════════
    # Export / Import
    # ════════════════════════════════════════════════════════════════════════════

    def export_progress_json(self) -> dict[str, Any]:
        """导出所有学习进度数据为字典。"""
        lessons = self.fetchall(
            "SELECT lesson_id, track_id, status, completed, last_opened, completed_at FROM lesson_progress"
        )
        notes = self.fetchall("SELECT lesson_id, content, tags, code_snippets, updated_at FROM lesson_notes")
        attempts = self.fetchall(
            "SELECT exercise_id, exercise_title_snapshot, track_id, code_snapshot, "
            "score, passed, duration_sec, submitted_at, feedback FROM practice_attempts"
        )
        bookmarks = self.fetchall("SELECT item_type, item_id, title, track_id, note, created_at FROM bookmarks")
        achievements = self.fetchall(
            "SELECT achievement_id, current_value, unlocked, unlocked_at FROM achievement_progress"
        )
        reviews = self.fetchall(
            "SELECT exercise_id, interval_days, ease_factor, repetitions, next_review, last_reviewed "
            "FROM review_schedule"
        )
        timers = self.fetchall("SELECT exercise_id, duration_sec, difficulty, recorded_at FROM exercise_timers")

        return {
            "version": "2.0",
            "exported_at": now_text(),
            "lesson_progress": [
                {
                    "lesson_id": r[0],
                    "track_id": r[1],
                    "status": r[2],
                    "completed": r[3],
                    "last_opened": r[4],
                    "completed_at": r[5],
                }
                for r in lessons
            ],
            "lesson_notes": [
                {"lesson_id": r[0], "content": r[1], "tags": r[2], "code_snippets": r[3], "updated_at": r[4]}
                for r in notes
            ],
            "practice_attempts": [
                {
                    "exercise_id": r[0],
                    "exercise_title": r[1],
                    "track_id": r[2],
                    "code_snapshot": r[3],
                    "score": r[4],
                    "passed": r[5],
                    "duration_sec": r[6],
                    "submitted_at": r[7],
                    "feedback": r[8],
                }
                for r in attempts
            ],
            "bookmarks": [
                {"item_type": r[0], "item_id": r[1], "title": r[2], "track_id": r[3], "note": r[4], "created_at": r[5]}
                for r in bookmarks
            ],
            "achievements": [
                {"achievement_id": r[0], "current_value": r[1], "unlocked": r[2], "unlocked_at": r[3]}
                for r in achievements
            ],
            "review_schedule": [
                {
                    "exercise_id": r[0],
                    "interval_days": r[1],
                    "ease_factor": r[2],
                    "repetitions": r[3],
                    "next_review": r[4],
                    "last_reviewed": r[5],
                }
                for r in reviews
            ],
            "exercise_timers": [
                {"exercise_id": r[0], "duration_sec": r[1], "difficulty": r[2], "recorded_at": r[3]} for r in timers
            ],
        }

    def import_progress_json(self, data: dict) -> int:
        """从 JSON 字典导入学习进度数据。返回导入的记录总数。"""
        imported = 0
        with self.connect() as conn:
            for lp in data.get("lesson_progress", []):
                conn.execute(
                    """INSERT OR REPLACE INTO lesson_progress
                       (lesson_id, track_id, status, completed, last_opened, completed_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        lp["lesson_id"],
                        lp["track_id"],
                        lp.get("status", "not_started"),
                        lp.get("completed", 0),
                        lp.get("last_opened"),
                        lp.get("completed_at"),
                    ),
                )
                imported += 1

            for note in data.get("lesson_notes", []):
                conn.execute(
                    """INSERT OR REPLACE INTO lesson_notes
                       (lesson_id, content, tags, code_snippets, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        note["lesson_id"],
                        note.get("content", ""),
                        note.get("tags", ""),
                        note.get("code_snippets", ""),
                        note.get("updated_at", now_text()),
                    ),
                )
                imported += 1

            for att in data.get("practice_attempts", []):
                conn.execute(
                    """INSERT INTO practice_attempts
                       (exercise_id, exercise_title_snapshot, track_id, code_snapshot,
                        score, passed, duration_sec, submitted_at, feedback)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        att["exercise_id"],
                        att.get("exercise_title", ""),
                        att.get("track_id", ""),
                        att.get("code_snapshot", ""),
                        att.get("score", 0),
                        att.get("passed", 0),
                        att.get("duration_sec", 0),
                        att.get("submitted_at", now_text()),
                        att.get("feedback", ""),
                    ),
                )
                imported += 1

            for bm in data.get("bookmarks", []):
                conn.execute(
                    """INSERT OR REPLACE INTO bookmarks
                       (item_type, item_id, title, track_id, note, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        bm["item_type"],
                        bm["item_id"],
                        bm.get("title", ""),
                        bm.get("track_id", ""),
                        bm.get("note", ""),
                        bm.get("created_at", now_text()),
                    ),
                )
                imported += 1

            for ach in data.get("achievements", []):
                conn.execute(
                    """INSERT OR REPLACE INTO achievement_progress
                       (achievement_id, current_value, unlocked, unlocked_at)
                       VALUES (?, ?, ?, ?)""",
                    (
                        ach["achievement_id"],
                        ach.get("current_value", 0),
                        ach.get("unlocked", 0),
                        ach.get("unlocked_at"),
                    ),
                )
                imported += 1

            for rev in data.get("review_schedule", []):
                conn.execute(
                    """INSERT OR REPLACE INTO review_schedule
                       (exercise_id, interval_days, ease_factor, repetitions,
                        next_review, last_reviewed)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        rev["exercise_id"],
                        rev.get("interval_days", 1.0),
                        rev.get("ease_factor", 2.5),
                        rev.get("repetitions", 0),
                        rev.get("next_review", ""),
                        rev.get("last_reviewed"),
                    ),
                )
                imported += 1

            for tmr in data.get("exercise_timers", []):
                conn.execute(
                    """INSERT INTO exercise_timers
                       (exercise_id, duration_sec, difficulty, recorded_at)
                       VALUES (?, ?, ?, ?)""",
                    (
                        tmr["exercise_id"],
                        tmr.get("duration_sec", 0),
                        tmr.get("difficulty", ""),
                        tmr.get("recorded_at", now_text()),
                    ),
                )
                imported += 1

        self._invalidate_stats_cache()
        return imported

    def export_notes_markdown(self) -> str:
        """导出所有笔记为 Markdown 文本。"""
        notes = self.all_notes()
        lines = ["# DevLearner AI 学习笔记导出", "", f"导出时间: {now_text()}", "", "---", ""]
        for lesson_id, content, tags, code_snippets, updated_at in notes:
            lines.append(f"## {lesson_id}")
            if tags:
                lines.append(f"**标签:** {tags}")
            lines.append(f"**更新时间:** {updated_at}")
            lines.append("")
            lines.append(content)
            if code_snippets:
                lines.append("")
                lines.append("### 代码片段")
                lines.append("```")
                lines.append(code_snippets)
                lines.append("```")
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    def trim_mentor_messages(self, session_id: int, keep_last: int = 200) -> int:
        """裁剪会话中的旧消息，只保留最近的 N 条。

        用于防止长时间使用的会话占用过多内存和磁盘空间。

        Args:
            session_id: 会话 ID。
            keep_last: 保留的最新消息数量，默认 200。

        Returns:
            删除的消息数量。
        """
        count_row = self.fetchone(
            "SELECT COUNT(*) FROM mentor_messages WHERE session_id = ?",
            (session_id,),
        )
        total = int(count_row[0]) if count_row else 0
        if total <= keep_last:
            return 0
        delete_count = total - keep_last
        with self.connect() as conn:
            conn.execute(
                """
                DELETE FROM mentor_messages
                WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM mentor_messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (session_id, session_id, keep_last),
            )
        return delete_count
