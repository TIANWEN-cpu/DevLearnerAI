import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from app.config import CONTENT_DIR, METADATA_DIR


def _looks_corrupt(value: str) -> bool:
    if not value:
        return True
    bad_tokens = ("???", "??", "锟", "�", "璇", "妯", "鍩", "绮", "路")
    return any(token in value for token in bad_tokens)


def _clean_text(value: str, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    text = value.strip()
    return fallback if _looks_corrupt(text) else text


def _clean_list(values: List[str], fallback: Optional[List[str]] = None) -> List[str]:
    fallback = fallback or []
    if not isinstance(values, list):
        return fallback
    cleaned = [_clean_text(str(item), "") for item in values]
    cleaned = [item for item in cleaned if item]
    return cleaned or fallback


@dataclass
class Lesson:
    id: str
    title: str
    summary: str
    path: str
    difficulty: str
    estimated_minutes: int
    tags: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    outcomes: List[str] = field(default_factory=list)


@dataclass
class Module:
    id: str
    title: str
    summary: str
    lessons: List[Lesson] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.id


@dataclass
class Track:
    id: str
    title: str
    icon: str
    summary: str
    modules: List[Module] = field(default_factory=list)

    @property
    def lessons(self) -> List[Lesson]:
        return [lesson for module in self.modules for lesson in module.lessons]


class ContentService:
    def __init__(self, metadata_path: Optional[Path] = None):
        self.metadata_path = metadata_path or (METADATA_DIR / "course_map.json")
        self._tracks = self._load_tracks()

    def _load_tracks(self) -> List[Track]:
        try:
            raw = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"[ContentService] 课程元数据文件未找到: {self.metadata_path}")
            return []
        except json.JSONDecodeError as exc:
            print(f"[ContentService] 课程元数据 JSON 解析失败: {exc}")
            return []

        tracks: List[Track] = []
        for track_data in raw.get("tracks", []):
            modules: List[Module] = []
            for module_data in track_data.get("modules", []):
                lessons: List[Lesson] = []
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
                            estimated_minutes=int(lesson_data.get("estimated_minutes", 25)),
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

            tracks.append(
                Track(
                    id=track_data.get("id", "track"),
                    title=_clean_text(track_data.get("title", ""), "未命名主线"),
                    icon=_clean_text(track_data.get("icon", ""), "📘"),
                    summary=_clean_text(
                        track_data.get("summary", ""),
                        "按主线推进模块，再从模块里递进学习课程。",
                    ),
                    modules=modules,
                )
            )
        return tracks

    @property
    def tracks(self) -> List[Track]:
        return self._tracks

    def track_by_id(self, track_id: str) -> Optional[Track]:
        return next((track for track in self._tracks if track.id == track_id), None)

    def lesson_by_id(self, lesson_id: str) -> Optional[Tuple[Track, Module, Lesson]]:
        for track in self._tracks:
            for module in track.modules:
                for lesson in module.lessons:
                    if lesson.id == lesson_id:
                        return track, module, lesson
        return None

    def lesson_markdown(self, lesson: Lesson) -> str:
        path = CONTENT_DIR / lesson.path
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"[ContentService] 课程 Markdown 文件未找到: {path}")
            return f"# {lesson.title}\n\n这节课的文档文件暂时缺失。"
        except Exception as exc:
            print(f"[ContentService] 读取课程 Markdown 失败: {path} - {exc}")
            return f"# {lesson.title}\n\n加载文档时出现错误：{exc}"

    def all_lessons(self) -> List[Tuple[Track, Module, Lesson]]:
        rows: List[Tuple[Track, Module, Lesson]] = []
        for track in self._tracks:
            for module in track.modules:
                for lesson in module.lessons:
                    rows.append((track, module, lesson))
        return rows
