"""书签服务 -- 管理收藏操作。"""

from __future__ import annotations

from app.database import AppDatabase
from app.services.base import BaseService
from app.utils.events import BookmarkAddedEvent, BookmarkRemovedEvent


class BookmarkService(BaseService):
    """书签管理服务。"""

    def __init__(self, db: AppDatabase) -> None:
        super().__init__(db)

    def add(self, item_type: str, item_id: str, title: str, track_id: str = "", note: str = "") -> None:
        """添加书签。"""
        self._db.add_bookmark(item_type, item_id, title, track_id, note)
        self._publish(BookmarkAddedEvent(item_type=item_type, item_id=item_id, title=title))

    def remove(self, item_type: str, item_id: str) -> None:
        """移除书签。"""
        self._db.remove_bookmark(item_type, item_id)
        self._publish(BookmarkRemovedEvent(item_type=item_type, item_id=item_id))

    def is_bookmarked(self, item_type: str, item_id: str) -> bool:
        """检查是否已收藏。"""
        return self._db.is_bookmarked(item_type, item_id)

    def list_all(self, item_type: str = "") -> list[tuple]:
        """列出书签。"""
        return self._db.list_bookmarks(item_type)

    def search(self, query: str) -> list[tuple]:
        """搜索书签。"""
        return self._db.search_bookmarks(query)

    def count(self) -> int:
        """书签总数。"""
        return self._db.bookmark_count()
