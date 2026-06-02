"""笔记服务 -- 管理课程笔记的保存、搜索和导出。"""

from __future__ import annotations

from app.database import AppDatabase
from app.services.base import BaseService
from app.utils.events import LessonNoteSavedEvent


class NoteService(BaseService):
    """课程笔记管理服务。"""

    def __init__(self, db: AppDatabase) -> None:
        super().__init__(db)

    def save(self, lesson_id: str, content: str, tags: str = "", code_snippets: str = "") -> None:
        """保存增强笔记。"""
        self._db.save_enhanced_note(lesson_id, content, tags, code_snippets)
        self._publish(LessonNoteSavedEvent(lesson_id=lesson_id, has_content=bool(content)))

    def load(self, lesson_id: str) -> dict:
        """加载增强笔记。"""
        return self._db.load_enhanced_note(lesson_id)

    def search(self, query: str) -> list[tuple]:
        """搜索笔记。"""
        return self._db.search_notes(query)

    def list_all(self) -> list[tuple]:
        """列出所有笔记。"""
        return self._db.all_notes()

    def count(self) -> int:
        """有内容的笔记数量。"""
        return self._db.note_count()

    def export_markdown(self) -> str:
        """导出为 Markdown 文本。"""
        return self._db.export_notes_markdown()
