"""数据可移植性工具模块 -- 导出、导入、冲突解决与数据校验。

提供与 UI 无关的数据导出/导入核心逻辑，供 widget 层和 CLI 调用。

支持：
- 数据库全量导出为 JSON
- JSON 数据导入数据库（带冲突解决策略）
- 选择性导出（仅导出指定数据类别）
- 数据格式校验与版本兼容性检查
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any

from app.database import AppDatabase, now_text

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

CURRENT_FORMAT_VERSION = "2.0"
SUPPORTED_FORMAT_VERSIONS = ("1.0", "2.0")

# 所有可导出的数据类别
EXPORT_CATEGORIES = (
    "lesson_progress",
    "lesson_notes",
    "practice_attempts",
    "bookmarks",
    "achievements",
    "review_schedule",
    "exercise_timers",
)


# ── Conflict resolution strategy ─────────────────────────────────────────────


class ConflictStrategy(Enum):
    """导入时遇到已有数据的冲突解决策略。"""

    OVERWRITE = "overwrite"  # 覆盖已有记录（默认，INSERT OR REPLACE）
    SKIP = "skip"  # 跳过已存在的记录
    MERGE = "merge"  # 合并：取更新时间较新的记录


# ── Validation ───────────────────────────────────────────────────────────────


class ValidationError(Exception):
    """数据校验错误。"""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


def validate_export_data(data: dict[str, Any]) -> list[str]:
    """校验导出数据格式，返回错误列表（空列表表示通过）。

    Checks:
    - 必须包含 'version' 字段
    - version 必须在已知版本列表中
    - 每个数据类别必须是列表类型
    - 列表元素必须是字典类型
    - 必需字段不得缺失
    """
    errors: list[str] = []

    # Version check
    version = data.get("version")
    if version is None:
        errors.append("缺少 'version' 字段")
    elif str(version) not in SUPPORTED_FORMAT_VERSIONS:
        errors.append(f"不支持的格式版本: {version}（支持: {', '.join(SUPPORTED_FORMAT_VERSIONS)}）")

    # Category-level checks
    required_fields_per_category: dict[str, list[str]] = {
        "lesson_progress": ["lesson_id"],
        "lesson_notes": ["lesson_id"],
        "practice_attempts": ["exercise_id"],
        "bookmarks": ["item_type", "item_id"],
        "achievements": ["achievement_id"],
        "review_schedule": ["exercise_id"],
        "exercise_timers": ["exercise_id"],
    }

    for category, required_fields in required_fields_per_category.items():
        items = data.get(category)
        if items is None:
            continue  # 缺失类别不报错（可能是选择性导出）
        if not isinstance(items, list):
            errors.append(f"'{category}' 必须是列表类型，实际为 {type(items).__name__}")
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"'{category}[{idx}]' 必须是字典类型")
                continue
            for field_name in required_fields:
                if field_name not in item:
                    errors.append(f"'{category}[{idx}]' 缺少必需字段 '{field_name}'")

    return errors


def validate_and_raise(data: dict[str, Any]) -> None:
    """校验数据，有错误时抛出 ValidationError。"""
    errors = validate_export_data(data)
    if errors:
        raise ValidationError(f"数据校验失败（{len(errors)} 个错误）", errors=errors)


# ── Export ───────────────────────────────────────────────────────────────────


def export_database_json(
    db: AppDatabase,
    categories: tuple[str, ...] | None = None,
    include_metadata: bool = True,
) -> dict[str, Any]:
    """将数据库导出为 JSON 字典。

    Args:
        db: 数据库实例。
        categories: 要导出的类别元组，None 表示全部导出。
        include_metadata: 是否包含 version / exported_at 元数据。

    Returns:
        可序列化为 JSON 的字典。
    """
    all_data = db.export_progress_json()

    if categories is not None:
        selected = {cat: all_data.get(cat, []) for cat in categories if cat in all_data}
    else:
        selected = {k: v for k, v in all_data.items() if k != "version" and k != "exported_at"}

    if include_metadata:
        result: dict[str, Any] = {
            "version": CURRENT_FORMAT_VERSION,
            "exported_at": now_text(),
        }
        result.update(selected)
        return result

    return selected


def export_database_to_file(
    db: AppDatabase,
    path: str | Path,
    categories: tuple[str, ...] | None = None,
) -> int:
    """将数据库导出为 JSON 文件。

    Args:
        db: 数据库实例。
        path: 输出文件路径。
        categories: 要导出的类别，None 表示全部。

    Returns:
        导出的记录总数。
    """
    data = export_database_json(db, categories=categories)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    count = sum(len(v) for k, v in data.items() if isinstance(v, list))
    logger.info("导出 %d 条记录到 %s", count, path)
    return count


def export_notes_markdown(db: AppDatabase, path: str | Path) -> int:
    """将笔记导出为 Markdown 文件。

    Args:
        db: 数据库实例。
        path: 输出文件路径。

    Returns:
        导出的笔记数量。
    """
    content = db.export_notes_markdown()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    count = db.note_count()
    logger.info("导出 %d 条笔记到 %s", count, path)
    return count


# ── Import ───────────────────────────────────────────────────────────────────


def import_json_to_database(
    db: AppDatabase,
    data: dict[str, Any],
    strategy: ConflictStrategy = ConflictStrategy.OVERWRITE,
    validate: bool = True,
) -> int:
    """将 JSON 数据导入数据库。

    Args:
        db: 数据库实例。
        data: 由 export_database_json 生成的字典。
        strategy: 冲突解决策略。
        validate: 是否在导入前校验数据。

    Returns:
        导入的记录总数。

    Raises:
        ValidationError: 数据校验失败时。
    """
    if validate:
        validate_and_raise(data)

    if strategy == ConflictStrategy.OVERWRITE:
        return db.import_progress_json(data)

    if strategy == ConflictStrategy.SKIP:
        return _import_with_skip(db, data)

    if strategy == ConflictStrategy.MERGE:
        return _import_with_merge(db, data)

    raise ValueError(f"未知的冲突解决策略: {strategy}")


def import_file_to_database(
    db: AppDatabase,
    path: str | Path,
    strategy: ConflictStrategy = ConflictStrategy.OVERWRITE,
    validate: bool = True,
) -> int:
    """从 JSON 文件导入数据到数据库。

    Args:
        db: 数据库实例。
        path: JSON 文件路径。
        strategy: 冲突解决策略。
        validate: 是否校验数据。

    Returns:
        导入的记录总数。
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    return import_json_to_database(db, data, strategy=strategy, validate=validate)


def restore_from_backup(
    db: AppDatabase,
    path: str | Path,
    strategy: ConflictStrategy = ConflictStrategy.OVERWRITE,
) -> int:
    """从完整备份恢复数据（先清空再导入）。

    Args:
        db: 数据库实例。
        path: 备份文件路径。
        strategy: 冲突解决策略（恢复时通常用 OVERWRITE）。

    Returns:
        恢复的记录总数。
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    validate_and_raise(data)
    db.reset_learning_progress()
    count = db.import_progress_json(data)
    logger.info("从备份恢复 %d 条记录: %s", count, path)
    return count


# ── Conflict resolution internals ────────────────────────────────────────────


def _import_with_skip(db: AppDatabase, data: dict[str, Any]) -> int:
    """导入时跳过已存在的记录。"""
    imported = 0
    existing_progress = {row[0] for row in db.fetchall("SELECT lesson_id FROM lesson_progress")}
    existing_notes = {row[0] for row in db.fetchall("SELECT lesson_id FROM lesson_notes")}
    existing_bookmarks = {(row[0], row[1]) for row in db.fetchall("SELECT item_type, item_id FROM bookmarks")}
    existing_achievements = {row[0] for row in db.fetchall("SELECT achievement_id FROM achievement_progress")}

    with db.connect() as conn:
        for lp in data.get("lesson_progress", []):
            if lp["lesson_id"] in existing_progress:
                continue
            conn.execute(
                """INSERT INTO lesson_progress
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
            if note["lesson_id"] in existing_notes:
                continue
            conn.execute(
                """INSERT INTO lesson_notes
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
            if (bm["item_type"], bm["item_id"]) in existing_bookmarks:
                continue
            conn.execute(
                """INSERT INTO bookmarks
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
            if ach["achievement_id"] in existing_achievements:
                continue
            conn.execute(
                """INSERT INTO achievement_progress
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

    db._invalidate_stats_cache()
    logger.info("跳过策略导入 %d 条新记录", imported)
    return imported


def _import_with_merge(db: AppDatabase, data: dict[str, Any]) -> int:
    """导入时合并：对有时间戳的记录取较新者。"""
    imported = 0
    existing_progress_times: dict[str, str] = {}
    for row in db.fetchall("SELECT lesson_id, COALESCE(last_opened, '') FROM lesson_progress"):
        existing_progress_times[row[0]] = row[1]

    existing_note_times: dict[str, str] = {}
    for row in db.fetchall("SELECT lesson_id, COALESCE(updated_at, '') FROM lesson_notes"):
        existing_note_times[row[0]] = row[1]

    with db.connect() as conn:
        for lp in data.get("lesson_progress", []):
            lid = lp["lesson_id"]
            incoming_time = lp.get("last_opened", "") or ""
            existing_time = existing_progress_times.get(lid, "")
            if lid in existing_progress_times and incoming_time <= existing_time:
                continue
            conn.execute(
                """INSERT OR REPLACE INTO lesson_progress
                   (lesson_id, track_id, status, completed, last_opened, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    lid,
                    lp["track_id"],
                    lp.get("status", "not_started"),
                    lp.get("completed", 0),
                    lp.get("last_opened"),
                    lp.get("completed_at"),
                ),
            )
            imported += 1

        for note in data.get("lesson_notes", []):
            lid = note["lesson_id"]
            incoming_time = note.get("updated_at", "") or ""
            existing_time = existing_note_times.get(lid, "")
            if lid in existing_note_times and incoming_time <= existing_time:
                continue
            conn.execute(
                """INSERT OR REPLACE INTO lesson_notes
                   (lesson_id, content, tags, code_snippets, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    lid,
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

    db._invalidate_stats_cache()
    logger.info("合并策略导入 %d 条记录", imported)
    return imported


# ── Utility helpers ──────────────────────────────────────────────────────────


def get_export_summary(data: dict[str, Any]) -> dict[str, int]:
    """获取导出数据的摘要统计。

    Returns:
        {类别名: 记录数} 字典。
    """
    summary: dict[str, int] = {}
    for key, value in data.items():
        if isinstance(value, list):
            summary[key] = len(value)
    return summary


def read_export_file(path: str | Path) -> dict[str, Any]:
    """读取并解析导出 JSON 文件，返回字典。

    Raises:
        FileNotFoundError: 文件不存在。
        json.JSONDecodeError: JSON 格式错误。
        ValidationError: 数据校验失败。
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    validate_and_raise(data)
    return data
