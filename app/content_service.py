"""课程内容加载与管理模块。

提供课程元数据的解析、Track/Module/Lesson 三级数据模型的构建、
Markdown 内容的读取，以及课程数据的缓存和懒加载机制。
"""

import json
import logging
import time as _time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.config import CONTENT_DIR, METADATA_DIR

logger = logging.getLogger(__name__)


def _looks_corrupt(value: str) -> bool:
    """检测文本是否包含编码损坏的特征标记。"""
    if not value:
        return True
    bad_tokens = ("???", "??", "锟", "�", "璇", "妯", "鍩", "绮")
    return any(token in value for token in bad_tokens)


def _clean_text(value: str, fallback: str) -> str:
    """清洗文本：去除损坏内容，返回有效文本或回退值。"""
    if not isinstance(value, str):
        return fallback
    text = value.strip()
    return fallback if _looks_corrupt(text) else text


def _safe_int(value: object, default: int = 0) -> int:
    """安全地将值转换为整数，失败时返回默认值。"""
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_list(values: list[str], fallback: Optional[list[str]] = None) -> list[str]:
    """清洗字符串列表：移除损坏项和空项。"""
    fallback = fallback or []
    if not isinstance(values, list):
        return fallback
    cleaned = [_clean_text(str(item), "") for item in values]
    cleaned = [item for item in cleaned if item]
    return cleaned or fallback


@dataclass
class Lesson:
    """课程数据模型。

    表示课程体系中最小的学习单元，包含课程元数据和关联信息。

    Attributes:
        id: 课程唯一标识符。
        title: 课程标题。
        summary: 课程简介。
        path: Markdown 文件相对于 content/ 目录的路径。
        difficulty: 难度级别（如"基础"、"进阶"）。
        estimated_minutes: 预估学习时间（分钟）。
        tags: 课程标签列表。
        prerequisites: 前置课程 ID 列表。
        outcomes: 学习目标列表。
    """

    id: str
    title: str
    summary: str
    path: str
    difficulty: str
    estimated_minutes: int
    tags: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)


@dataclass
class Module:
    """课程模块数据模型。

    模块是 Track 下的分组单元，包含一组相关的课程。

    Attributes:
        id: 模块唯一标识符。
        title: 模块标题。
        summary: 模块简介。
        lessons: 该模块包含的课程列表。
    """

    id: str
    title: str
    summary: str
    lessons: list[Lesson] = field(default_factory=list)

    @property
    def key(self) -> str:
        """返回模块 ID 作为唯一键。"""
        return self.id


@dataclass
class Track:
    """技术栈数据模型。

    Track 是课程体系的顶层组织单元（如 Python、数据库、C# 等），
    包含多个 Module，每个 Module 包含多个 Lesson。

    Attributes:
        id: 技术栈唯一标识符。
        title: 技术栈标题。
        icon: 图标标识。
        summary: 技术栈简介。
        modules: 该技术栈包含的模块列表。
    """

    id: str
    title: str
    icon: str
    summary: str
    modules: list[Module] = field(default_factory=list)

    @property
    def lessons(self) -> list[Lesson]:
        """返回该技术栈下所有模块中的全部课程（扁平列表）。"""
        return [lesson for module in self.modules for lesson in module.lessons]


class ContentService:
    """课程内容服务。

    负责从 course_map.json 加载课程元数据，构建 Track > Module > Lesson
    三级数据模型，支持懒加载和缓存。提供 Markdown 内容读取和课程查询接口。

    优化特性：
    - 懒加载 Track 对象（按需构建并缓存）
    - 课程 ID 索引（O(1) 查找）
    - Markdown 内容缓存（避免重复读取文件）
    - 前后课程预加载（减少页面切换延迟）

    Attributes:
        metadata_path: 课程元数据 JSON 文件路径。
    """

    _MAX_MARKDOWN_CACHE = 64  # 最多缓存的 Markdown 文件数

    def __init__(self, metadata_path: Optional[Path] = None):
        """初始化课程内容服务。

        读取课程元数据 JSON 文件，构建技术栈索引。

        Args:
            metadata_path: 课程元数据文件路径，默认使用 config.METADATA_DIR / course_map.json。
        """
        self.metadata_path = metadata_path or (METADATA_DIR / "course_map.json")
        self._cache: dict[str, Track] = {}
        self._tracks_index = self._discover_tracks()
        self._lesson_index: dict[str, tuple[str, str]] = {}  # lesson_id -> (track_id, module_id)
        self._markdown_cache: OrderedDict[str, str] = OrderedDict()  # LRU cache
        self._search_index: dict[str, list[str]] = {}  # token -> [lesson_id, ...]
        self._build_lesson_index()
        self._build_search_index()

    def _discover_tracks(self) -> list[dict[str, Any]]:
        """Discover available tracks without loading lesson content."""
        try:
            raw = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning("课程元数据文件未找到: %s", self.metadata_path)
            return []
        except json.JSONDecodeError as exc:
            logger.error("课程元数据 JSON 解析失败: %s", exc)
            return []
        return raw.get("tracks", [])

    def _build_lesson_index(self) -> None:
        """Build an index mapping lesson_id -> (track_id, module_id) from raw metadata.

        This allows O(1) lookup in lesson_by_id without loading full Track objects.
        """
        for track_data in self._tracks_index:
            track_id = track_data.get("id", "track")
            for module_data in track_data.get("modules", []):
                module_id = module_data.get("id", "module")
                for lesson_data in module_data.get("lessons", []):
                    lesson_id = lesson_data.get("id", "")
                    if lesson_id:
                        self._lesson_index[lesson_id] = (track_id, module_id)

    def _build_search_index(self) -> None:
        """Build a simple inverted index over lesson titles and summaries.

        Enables fast text search without loading full Track objects.
        """
        for track_data in self._tracks_index:
            for module_data in track_data.get("modules", []):
                for lesson_data in module_data.get("lessons", []):
                    lesson_id = lesson_data.get("id", "")
                    if not lesson_id:
                        continue
                    tags = lesson_data.get("tags") or []
                    text = (
                        f"{lesson_data.get('title', '')} "
                        f"{lesson_data.get('summary', '')} "
                        f"{' '.join(str(t) for t in tags if t)}"
                    ).lower()
                    tokens = set(text.split())
                    for token in tokens:
                        if len(token) >= 2:
                            self._search_index.setdefault(token, []).append(lesson_id)

    def search_lessons(self, query: str) -> list[str]:
        """Search lessons by query string using the inverted index.

        Returns a list of lesson_ids sorted by relevance (number of matching tokens).

        Args:
            query: Search query string.

        Returns:
            List of matching lesson IDs, sorted by relevance.
        """
        tokens = query.lower().split()
        if not tokens:
            return []
        scores: dict[str, int] = {}
        for token in tokens:
            for lesson_id in self._search_index.get(token, []):
                scores[lesson_id] = scores.get(lesson_id, 0) + 1
        return [lid for lid, _ in sorted(scores.items(), key=lambda x: -x[1])]

    def _build_track(self, track_data: dict[str, Any]) -> Track:
        """从原始 JSON 数据构建 Track 对象。

        对所有文本字段进行编码损坏检测和清洗。

        Args:
            track_data: 原始 JSON 中的单个 track 字典。

        Returns:
            构建好的 Track 实例。
        """
        modules: list[Module] = []
        for module_data in track_data.get("modules", []):
            lessons: list[Lesson] = []
            for lesson_data in module_data.get("lessons", []):
                lesson_id = lesson_data.get("id", "lesson")
                lessons.append(
                    Lesson(
                        id=lesson_id,
                        title=_clean_text(lesson_data.get("title", ""), "未命名课程"),
                        summary=_clean_text(
                            lesson_data.get("summary", ""),
                            "这节课会带你继续推进当前主线。",
                        ),
                        path=lesson_data.get("path", ""),
                        difficulty=_clean_text(
                            lesson_data.get("difficulty", ""),
                            "基础",
                        ),
                        estimated_minutes=_safe_int(lesson_data.get("estimated_minutes"), 25),
                        tags=_clean_list(lesson_data.get("tags", [])),
                        prerequisites=_clean_list(lesson_data.get("prerequisites", [])),
                        outcomes=_clean_list(lesson_data.get("outcomes", [])),
                    )
                )

            modules.append(
                Module(
                    id=module_data.get("id", "module"),
                    title=_clean_text(module_data.get("title", ""), "未命名模块"),
                    summary=_clean_text(
                        module_data.get("summary", ""),
                        "这组内容会帮你稳步推进当前主线。",
                    ),
                    lessons=lessons,
                )
            )

        return Track(
            id=track_data.get("id", "track"),
            title=_clean_text(track_data.get("title", ""), "未命名主线"),
            icon=_clean_text(track_data.get("icon", ""), "📘"),
            summary=_clean_text(
                track_data.get("summary", ""),
                "按主线推进模块，再从模块里递进学习课程。",
            ),
            modules=modules,
        )

    def _load_track(self, track_data: dict[str, Any]) -> Track:
        """Load a track on demand and cache it."""
        track_id = track_data.get("id", "track")
        if track_id not in self._cache:
            start = _time.perf_counter()
            self._cache[track_id] = self._build_track(track_data)
            elapsed_ms = (_time.perf_counter() - start) * 1000
            track = self._cache[track_id]
            logger.info(
                "Track loaded: id=%s modules=%d lessons=%d latency=%.1fms",
                track_id,
                len(track.modules),
                len(track.lessons),
                elapsed_ms,
            )
            from app.utils.metrics import get_metrics

            get_metrics().record_content_load("track", elapsed_ms, cache_hit=False)
        return self._cache[track_id]

    @property
    def tracks(self) -> list[Track]:
        """返回所有技术栈（懒加载 + 缓存）。"""
        return [self._load_track(td) for td in self._tracks_index]

    def track_by_id(self, track_id: str) -> Optional[Track]:
        """根据 ID 查找技术栈。

        Args:
            track_id: 技术栈 ID。

        Returns:
            Track 实例，未找到时返回 None。
        """
        for td in self._tracks_index:
            if td.get("id") == track_id:
                return self._load_track(td)
        return None

    def lesson_by_id(self, lesson_id: str) -> Optional[tuple[Track, Module, Lesson]]:
        """根据课程 ID 查找课程及其所属的 Track 和 Module。

        使用预构建的索引进行 O(1) 查找，仅加载目标 Track。

        Args:
            lesson_id: 课程 ID。

        Returns:
            (Track, Module, Lesson) 元组，未找到时返回 None。
        """
        indexed = self._lesson_index.get(lesson_id)
        if not indexed:
            return None
        track_id, module_id = indexed
        track = self.track_by_id(track_id)
        if not track:
            return None
        for module in track.modules:
            if module.id == module_id:
                for lesson in module.lessons:
                    if lesson.id == lesson_id:
                        return track, module, lesson
        return None

    def lesson_markdown(self, lesson: Lesson) -> str:
        """读取课程的 Markdown 内容（带 LRU 缓存）。

        已读取的内容会缓存在内存中，后续访问直接返回缓存并移动到最近使用位置。
        当缓存超过上限时淘汰最久未使用的条目（LRU）。

        Args:
            lesson: Lesson 实例。

        Returns:
            Markdown 文本内容。文件不存在或读取失败时返回提示文本。
        """
        cache_key = lesson.path
        if cache_key in self._markdown_cache:
            self._markdown_cache.move_to_end(cache_key)
            from app.utils.metrics import get_metrics

            get_metrics().record_content_load("markdown", 0.0, cache_hit=True)
            return self._markdown_cache[cache_key]

        start = _time.perf_counter()
        path = CONTENT_DIR / lesson.path
        # Security: verify resolved path stays within CONTENT_DIR
        try:
            resolved = path.resolve()
            content_dir_resolved = CONTENT_DIR.resolve()
            if content_dir_resolved not in resolved.parents and resolved != content_dir_resolved:
                logger.warning("课程路径越界: %s", lesson.path)
                content = f"# {lesson.title}\n\n课程文件路径无效。"
                while len(self._markdown_cache) >= self._MAX_MARKDOWN_CACHE:
                    self._markdown_cache.popitem(last=False)
                self._markdown_cache[cache_key] = content
                return content
        except (OSError, ValueError) as exc:
            logger.warning("课程路径解析失败: %s - %s", lesson.path, exc)
            content = f"# {lesson.title}\n\n课程文件路径无效。"
            while len(self._markdown_cache) >= self._MAX_MARKDOWN_CACHE:
                self._markdown_cache.popitem(last=False)
            self._markdown_cache[cache_key] = content
            return content
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("课程 Markdown 文件未找到: %s", path)
            content = f"# {lesson.title}\n\n这节课的文档文件暂时缺失。"
        except Exception as exc:
            logger.error("读取课程 Markdown 失败: %s - %s", path, exc, exc_info=True)
            content = f"# {lesson.title}\n\n加载文档时出现错误。请检查课程文件是否存在，或尝试重启应用。"

        # Evict least-recently-used entries if cache is full
        while len(self._markdown_cache) >= self._MAX_MARKDOWN_CACHE:
            self._markdown_cache.popitem(last=False)
        self._markdown_cache[cache_key] = content

        elapsed_ms = (_time.perf_counter() - start) * 1000
        logger.debug("Markdown loaded: path=%s len=%d latency=%.1fms", lesson.path, len(content), elapsed_ms)
        from app.utils.metrics import get_metrics

        get_metrics().record_content_load("markdown", elapsed_ms, cache_hit=False)

        # Proactive memory pressure response
        try:
            from app.memory_monitor import should_trim_caches

            if should_trim_caches() and len(self._markdown_cache) > 8:
                target = max(8, self._MAX_MARKDOWN_CACHE // 2)
                while len(self._markdown_cache) > target:
                    self._markdown_cache.popitem(last=False)
                logger.debug("Shrunk markdown cache to %d entries due to memory pressure", target)
        except ImportError:
            pass

        return content

    def preload_adjacent_lessons(self, lesson_id: str) -> None:
        """预加载相邻课程的 Markdown 内容。

        根据当前课程在 _lesson_id_order 中的位置，预加载前一课和后一课
        的内容到缓存中，减少用户翻页时的等待时间。

        Args:
            lesson_id: 当前课程 ID。
        """
        all_ids = list(self._lesson_index.keys())
        try:
            idx = all_ids.index(lesson_id)
        except ValueError:
            return
        for offset in (-1, 1):
            adj_idx = idx + offset
            if 0 <= adj_idx < len(all_ids):
                result = self.lesson_by_id(all_ids[adj_idx])
                if result:
                    _track, _module, adj_lesson = result
                    # Only reads into cache if not already cached
                    self.lesson_markdown(adj_lesson)

    def clear_markdown_cache(self) -> None:
        """清空 Markdown 内容缓存，释放内存。"""
        self._markdown_cache.clear()

    def all_lessons(self) -> list[tuple[Track, Module, Lesson]]:
        """返回所有课程的扁平列表。

        Returns:
            (Track, Module, Lesson) 元组列表，遍历所有技术栈和模块。
        """
        rows: list[tuple[Track, Module, Lesson]] = []
        for track in self.tracks:
            for module in track.modules:
                for lesson in module.lessons:
                    rows.append((track, module, lesson))
        return rows
