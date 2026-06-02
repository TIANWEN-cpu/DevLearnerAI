"""Exercise loading, fallback resolution, and JSON resource management."""

import functools
import json
import logging
from pathlib import Path
from typing import Optional

from app.config import METADATA_DIR
from app.practice.models import Exercise

logger = logging.getLogger(__name__)


def load_json_resource(filename: str) -> dict:
    """Load a JSON file from METADATA_DIR with a single source of truth."""
    path = METADATA_DIR / filename
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("资源文件未找到: %s", path)
        return {}
    except json.JSONDecodeError as exc:
        logger.error("JSON 解析失败 (%s): %s", path, exc)
        return {}


@functools.lru_cache(maxsize=1)
def get_exercise_fallbacks() -> dict:
    """Return the exercise fallback definitions (cached)."""
    return load_json_resource("exercise_fallbacks.json")


@functools.lru_cache(maxsize=1)
def get_sql_query_fixtures() -> dict:
    """Return the SQL query fixtures with tuples restored (cached)."""
    raw = load_json_resource("sql_query_fixtures.json")
    # JSON cannot represent tuples; convert expected_rows lists back to tuples.
    for fixture in raw.values():
        if "expected_rows" in fixture:
            fixture["expected_rows"] = [tuple(row) for row in fixture["expected_rows"]]
    return raw


def needs_fallback(value: str) -> bool:
    """Return True if *value* looks like encoding-corrupted text."""
    return "?" in value


def load_exercises(metadata_path: Optional[Path] = None) -> list[Exercise]:
    """Load and patch exercises from the metadata JSON file."""
    metadata_path = metadata_path or (METADATA_DIR / "exercises.json")
    try:
        raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("练习元数据文件未找到: %s", metadata_path)
        return []
    except json.JSONDecodeError as exc:
        logger.error("练习元数据 JSON 解析失败: %s", exc)
        return []

    fallbacks = get_exercise_fallbacks()
    exercises: list[Exercise] = []
    for item in raw["exercises"]:
        fallback = fallbacks.get(item["id"], {})
        patched = dict(item)
        for field_name in ("title", "difficulty", "prompt"):
            value = patched.get(field_name, "")
            if isinstance(value, str) and needs_fallback(value):
                patched[field_name] = fallback.get(field_name, value)
        hints = patched.get("hints", [])
        if any(needs_fallback(hint) for hint in hints):
            patched["hints"] = fallback.get("hints", hints)
        starter_code = patched.get("starter_code", "")
        if isinstance(starter_code, str) and needs_fallback(starter_code):
            patched["starter_code"] = fallback.get("starter_code", starter_code)
        tests = patched.get("tests", [])
        if any(needs_fallback(str(test.get("expected", ""))) for test in tests):
            patched["tests"] = fallback.get("tests", tests)
        exercises.append(Exercise(**patched))
    return exercises
