"""AI 导师服务 -- 管理会话、消息、工作区状态。"""

from __future__ import annotations

from typing import Optional

from app.database import AppDatabase
from app.services.base import BaseService
from app.utils.events import (
    MentorMessageSentEvent,
    MentorSessionCreatedEvent,
    MentorSessionDeletedEvent,
    MentorSessionSwitchedEvent,
)


class MentorService(BaseService):
    """AI 导师管理服务。

    封装 AppDatabase 中 AI 导师相关操作，通过事件总线发布状态变更。
    """

    def __init__(self, db: AppDatabase) -> None:
        super().__init__(db)

    # ── Session management ─────────────────────────────────────────────────

    def create_session(self, name: str) -> int:
        """创建新会话。

        Returns:
            新会话 ID。
        """
        session_id = self._db.create_mentor_session(name)
        self._publish(MentorSessionCreatedEvent(session_id=session_id, session_name=name))
        return session_id

    def delete_session(self, session_id: int) -> None:
        """删除会话。"""
        self._db.delete_mentor_session(session_id)
        self._publish(MentorSessionDeletedEvent(session_id=session_id))

    def rename_session(self, session_id: int, name: str) -> None:
        """重命名会话。"""
        self._db.rename_mentor_session(session_id, name)

    def list_sessions(self) -> list[tuple[int, str, str]]:
        """列出所有会话。

        Returns:
            (id, name, updated_at) 元组列表。
        """
        return self._db.list_mentor_sessions()

    def get_session_snapshot(self, session_id: int) -> dict:
        """获取会话摘要快照。"""
        return self._db.mentor_session_snapshot(session_id)

    # ── Active session ─────────────────────────────────────────────────────

    def set_active(self, session_id: int) -> None:
        """设置活跃会话。"""
        self._db.set_active_mentor_session(session_id)
        self._publish(MentorSessionSwitchedEvent(session_id=session_id))

    def get_active_id(self) -> Optional[int]:
        """获取当前活跃会话 ID。"""
        return self._db.load_active_mentor_session_id()

    # ── Messages ───────────────────────────────────────────────────────────

    def append_message(self, session_id: int, role: str, content: str) -> None:
        """追加消息。"""
        self._db.append_mentor_message(session_id, role, content)
        self._publish(MentorMessageSentEvent(session_id=session_id, role=role))

    def load_messages(self, session_id: int) -> list[tuple[str, str, str]]:
        """加载会话消息。

        Returns:
            (role, content, created_at) 元组列表。
        """
        return self._db.load_mentor_messages(session_id)

    def trim_messages(self, session_id: int, keep_last: int = 200) -> int:
        """裁剪旧消息。

        Returns:
            删除的消息数量。
        """
        return self._db.trim_mentor_messages(session_id, keep_last)

    # ── Workspace state ────────────────────────────────────────────────────

    def save_workspace_flags(self, use_base: bool, use_personal: bool, use_custom: bool) -> None:
        """保存知识库启用标志。"""
        self._db.save_mentor_workspace_flags(use_base, use_personal, use_custom)

    def load_workspace_flags(self) -> dict:
        """加载知识库启用标志。"""
        return self._db.load_mentor_workspace_flags()

    # ── Knowledge files ────────────────────────────────────────────────────

    def list_knowledge_files(self) -> list[tuple]:
        """列出知识库文件。"""
        return self._db.list_knowledge_files()

    def add_knowledge_file(self, name: str, path: str, excerpt: str) -> None:
        """添加知识库文件。"""
        self._db.add_knowledge_file(name, path, excerpt)

    def remove_knowledge_file(self, file_id: int) -> None:
        """移除知识库文件。"""
        self._db.remove_knowledge_file(file_id)
