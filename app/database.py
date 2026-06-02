import shutil
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from app.config import API_CREDENTIAL_ALIAS, DB_DIR, DB_PATH, LEGACY_DB_PATH, ensure_runtime_dirs
from app.credentials import load_secret, save_secret

_connection = None
_connection_lock = threading.Lock()
_db_lock = threading.Lock()


def get_connection(db_path: str):
    global _connection
    with _connection_lock:
        if _connection is not None:
            try:
                _connection.execute("SELECT 1")
            except Exception:
                try:
                    _connection.close()
                except Exception:
                    pass
                _connection = None
        if _connection is None:
            ensure_runtime_dirs()
            _connection = sqlite3.connect(db_path, check_same_thread=False)
            _connection.execute("PRAGMA foreign_keys = ON")
            _connection.execute("PRAGMA journal_mode = WAL")
        return _connection


def close_connection():
    global _connection
    with _connection_lock:
        if _connection is not None:
            _connection.close()
            _connection = None


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class AppDatabase:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self._migrate_legacy_db_if_needed()

    def _migrate_legacy_db_if_needed(self) -> None:
        ensure_runtime_dirs()
        if self.db_path.exists():
            return
        if LEGACY_DB_PATH.exists() and LEGACY_DB_PATH.resolve() != self.db_path.resolve():
            DB_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LEGACY_DB_PATH, self.db_path)

    @contextmanager
    def connect(self):
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

        self._migrate_legacy_api_key_if_needed()
        self.repair_corrupted_mentor_history()

        if not self.list_mentor_sessions():
            default_id = self.create_mentor_session("默认对话")
            self.set_active_mentor_session(default_id)

    def _migrate_legacy_api_key_if_needed(self) -> None:
        row = self.fetchone(
            "SELECT host, api_key, key_alias, model FROM mentor_api_config WHERE id = 1"
        )
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

    def fetchall(self, sql: str, params: Sequence = ()) -> List[Tuple]:
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: Sequence = ()) -> Optional[Tuple]:
        with self.connect() as conn:
            return conn.execute(sql, params).fetchone()

    def execute(self, sql: str, params: Sequence = ()) -> None:
        with self.connect() as conn:
            conn.execute(sql, params)

    def mark_lesson_opened(self, lesson_id: str, track_id: str) -> None:
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

    def lesson_status(self, lesson_id: str) -> str:
        row = self.fetchone("SELECT status FROM lesson_progress WHERE lesson_id = ?", (lesson_id,))
        return row[0] if row else "not_started"

    def track_completion(self, track_id: str) -> int:
        row = self.fetchone(
            """
            SELECT COUNT(*) FROM lesson_progress
            WHERE track_id = ? AND completed = 1
            """,
            (track_id,),
        )
        return int(row[0]) if row else 0

    def completed_lessons(self) -> int:
        row = self.fetchone("SELECT COUNT(*) FROM lesson_progress WHERE completed = 1")
        return int(row[0]) if row else 0

    def list_completed_lessons(self):
        return self.fetchall(
            """
            SELECT lesson_id, completed_at
            FROM lesson_progress
            WHERE completed = 1
            ORDER BY completed_at DESC
            """
        )

    def save_note(self, lesson_id: str, content: str) -> None:
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

    def recent_attempts(self, limit: int = 10) -> List[Tuple]:
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

    def load_exercise_draft(self, exercise_id: str) -> Optional[Tuple[str, str]]:
        return self.fetchone(
            "SELECT exercise_title_snapshot, code_snapshot FROM exercise_drafts WHERE exercise_id = ?",
            (exercise_id,),
        )

    def clear_exercise_draft(self, exercise_id: str) -> None:
        self.execute("DELETE FROM exercise_drafts WHERE exercise_id = ?", (exercise_id,))

    def average_score(self) -> int:
        row = self.fetchone("SELECT AVG(score) FROM practice_attempts")
        if not row or row[0] is None:
            return 0
        return int(round(row[0]))

    def active_days_streak(self) -> int:
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
            return 0

        days = [datetime.strptime(row[0], "%Y-%m-%d").date() for row in rows]
        if days[0] != date.today():
            return 0

        streak = 1
        expected_day = date.today() - timedelta(days=1)
        for current_day in days[1:]:
            if current_day == expected_day:
                streak += 1
                expected_day -= timedelta(days=1)
            elif current_day < expected_day:
                break
        return streak

    def reset_learning_progress(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM lesson_progress")
            conn.execute("DELETE FROM lesson_notes")
            conn.execute("DELETE FROM practice_attempts")
            conn.execute("DELETE FROM exercise_drafts")

    def save_api_config(self, host: str, api_key: str, model: str) -> None:
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

    def load_api_config(self) -> Tuple[str, str, str]:
        row = self.fetchone(
            "SELECT host, api_key, model, key_alias FROM mentor_api_config WHERE id = 1"
        )
        if not row:
            return "", "", ""

        host, legacy_api_key, model, key_alias = row
        if key_alias:
            return host or "", load_secret(key_alias) or "", model or ""
        return host or "", legacy_api_key or "", model or ""

    def list_mentor_sessions(self) -> List[Tuple[int, str, str]]:
        return self.fetchall(
            """
            SELECT id, name, updated_at
            FROM mentor_sessions
            ORDER BY updated_at DESC, id DESC
            """
        )

    @staticmethod
    def _clip_preview(text: str, limit: int = 72) -> str:
        cleaned = " ".join((text or "").strip().split())
        if not cleaned:
            return ""
        return cleaned if len(cleaned) <= limit else cleaned[: limit - 1] + "…"

    def mentor_session_snapshot(self, session_id: int) -> dict:
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
        self.execute(
            """
            UPDATE mentor_sessions
            SET name = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, now_text(), session_id),
        )

    def delete_mentor_session(self, session_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM mentor_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM mentor_sessions WHERE id = ?", (session_id,))
            active_row = conn.execute(
                "SELECT active_session_id FROM mentor_workspace_state WHERE id = 1"
            ).fetchone()
            if active_row and active_row[0] == session_id:
                fallback = conn.execute(
                    "SELECT id FROM mentor_sessions ORDER BY updated_at DESC, id DESC LIMIT 1"
                ).fetchone()
                conn.execute(
                    "UPDATE mentor_workspace_state SET active_session_id = ? WHERE id = 1",
                    (fallback[0] if fallback else None,),
                )

    def set_active_mentor_session(self, session_id: int) -> None:
        self.execute(
            """
            UPDATE mentor_workspace_state
            SET active_session_id = ?
            WHERE id = 1
            """,
            (session_id,),
        )

    def load_active_mentor_session_id(self) -> Optional[int]:
        row = self.fetchone("SELECT active_session_id FROM mentor_workspace_state WHERE id = 1")
        return int(row[0]) if row and row[0] else None

    def append_mentor_message(self, session_id: int, role: str, content: str) -> None:
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

    def load_mentor_messages(self, session_id: int) -> List[Tuple[str, str, str]]:
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
        self.execute(
            """
            UPDATE mentor_workspace_state
            SET use_base = ?, use_personal = ?, use_custom = ?
            WHERE id = 1
            """,
            (1 if use_base else 0, 1 if use_personal else 0, 1 if use_custom else 0),
        )

    def load_mentor_workspace_flags(self) -> dict:
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

    def list_knowledge_files(self) -> List[Tuple[int, str, str, str]]:
        return self.fetchall(
            """
            SELECT id, display_name, file_path, excerpt
            FROM mentor_knowledge_files
            ORDER BY id DESC
            """
        )

    def get_knowledge_file(self, file_id: int) -> Optional[Tuple[int, str, str, str, str]]:
        return self.fetchone(
            """
            SELECT id, display_name, file_path, excerpt, created_at
            FROM mentor_knowledge_files
            WHERE id = ?
            """,
            (file_id,),
        )

    def add_knowledge_file(self, display_name: str, file_path: str, excerpt: str) -> None:
        self.execute(
            """
            INSERT INTO mentor_knowledge_files (display_name, file_path, excerpt, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (display_name, file_path, excerpt, now_text()),
        )

    def remove_knowledge_file(self, file_id: int) -> None:
        self.execute("DELETE FROM mentor_knowledge_files WHERE id = ?", (file_id,))
