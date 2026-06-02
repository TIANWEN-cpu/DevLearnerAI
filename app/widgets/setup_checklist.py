"""Setup checklist widget for the dashboard.

Displays a card with setup items that new users should complete.
Items include: API configured, first lesson completed, first exercise
attempted, and first AI chat.  Each item shows a checkmark when
completed and a brief action hint when not.

The checklist automatically hides itself once all items are completed.
"""

import logging

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.database import AppDatabase
from app.effects import apply_shadow
from app.styles import (
    ACCENT,
    BG_CARD,
    BORDER,
    F_TITLE,
    FONT,
    SUCCESS,
    SUCCESS_SOFT,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUB,
    WARNING,
    WARNING_SOFT,
)

logger = logging.getLogger(__name__)


class ChecklistItem(QWidget):
    """A single checklist item with status indicator and action button.

    Signals:
        action_clicked: Emitted when the action button is clicked.
    """

    action_clicked = pyqtSignal()

    def __init__(self, title: str, description: str, action_label: str, parent=None):
        super().__init__(parent)
        self._completed = False
        self._title = title
        self._description = description
        self._action_label = action_label

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(14)

        # Status icon
        self._icon = QLabel()
        self._icon.setFixedSize(32, 32)
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setStyleSheet(
            f"background: {WARNING_SOFT}; color: {WARNING}; border-radius: 16px; font-size: 16px; font-weight: 700;"
        )
        self._icon.setText("?")
        layout.addWidget(self._icon)

        # Text
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 18px; font-weight: 600;")
        text_col.addWidget(self._title_label)

        self._desc_label = QLabel(description)
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 15px;")
        text_col.addWidget(self._desc_label)
        layout.addLayout(text_col, 1)

        # Action button
        self._action_btn = QPushButton(action_label)
        self._action_btn.setProperty("variant", "secondary")
        self._action_btn.setCursor(Qt.PointingHandCursor)
        self._action_btn.setToolTip(description)
        self._action_btn.clicked.connect(self.action_clicked.emit)
        layout.addWidget(self._action_btn)

        self._update_visual()

    @property
    def completed(self) -> bool:
        return self._completed

    def set_completed(self, value: bool) -> None:
        if self._completed == value:
            return
        self._completed = value
        self._update_visual()

    def _update_visual(self) -> None:
        if self._completed:
            self._icon.setText("✓")
            self._icon.setStyleSheet(
                f"background: {SUCCESS_SOFT}; color: {SUCCESS}; border-radius: 16px; font-size: 18px; font-weight: 700;"
            )
            self._title_label.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 18px; font-weight: 600; text-decoration: line-through;"
            )
            self._action_btn.setVisible(False)
        else:
            self._icon.setText("?")
            self._icon.setStyleSheet(
                f"background: {WARNING_SOFT}; color: {WARNING}; border-radius: 16px; font-size: 16px; font-weight: 700;"
            )
            self._title_label.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 18px; font-weight: 600;")
            self._action_btn.setVisible(True)


class SetupChecklistWidget(QFrame):
    """Dashboard checklist widget showing initial setup progress.

    Tracks 4 items:
      1. API configured
      2. First lesson completed
      3. First exercise attempted
      4. First AI chat

    Signals:
        navigate_page(index): Request navigation to a page.
        open_ai_chat: Request to open AI chat.
    """

    navigate_page = pyqtSignal(int)
    open_ai_chat = pyqtSignal()

    def __init__(self, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self._all_complete = False

        self.setStyleSheet(
            f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
            """
        )
        apply_shadow(self, blur=18, offset_y=4)

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("新手清单")
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        header.addWidget(title)

        header.addStretch()

        self._progress_label = QLabel("0/4")
        self._progress_label.setStyleSheet(f"color: {ACCENT}; font-weight: 700; font-size: 20px;")
        header.addWidget(self._progress_label)
        layout.addLayout(header)

        subtitle = QLabel("完成以下步骤，开启你的学习之旅。")
        subtitle.setStyleSheet(f"color: {TEXT_SUB}; font-size: 17px;")
        layout.addWidget(subtitle)

        # Checklist items
        self._item_api = ChecklistItem(
            "配置 AI API",
            "设置 API 地址和密钥，启用 AI 导师功能",
            "去配置",
        )
        self._item_api.action_clicked.connect(lambda: self.navigate_page.emit(5))
        layout.addWidget(self._item_api)

        self._item_lesson = ChecklistItem(
            "完成第一节课",
            "进入学习路径，选择并完成一节课程",
            "去学习",
        )
        self._item_lesson.action_clicked.connect(lambda: self.navigate_page.emit(1))
        layout.addWidget(self._item_lesson)

        self._item_exercise = ChecklistItem(
            "完成第一道练习",
            "在练习中心提交一道编码练习",
            "去练习",
        )
        self._item_exercise.action_clicked.connect(lambda: self.navigate_page.emit(2))
        layout.addWidget(self._item_exercise)

        self._item_chat = ChecklistItem(
            "与 AI 导师对话",
            "向 AI 导师提一个问题或请求代码分析",
            "去聊天",
        )
        self._item_chat.action_clicked.connect(self.open_ai_chat.emit)
        layout.addWidget(self._item_chat)

        # Congratulations message (hidden initially)
        self._congrats = QLabel("恭喜！你已完成所有初始设置，开始尽情学习吧！")
        self._congrats.setWordWrap(True)
        self._congrats.setStyleSheet(f"color: {SUCCESS}; font-size: 18px; font-weight: 600;")
        self._congrats.setAlignment(Qt.AlignCenter)
        self._congrats.setVisible(False)
        layout.addWidget(self._congrats)

        # Dismiss button (hidden initially)
        dismiss_row = QHBoxLayout()
        dismiss_row.addStretch()
        self._dismiss_btn = QPushButton("关闭清单")
        self._dismiss_btn.setProperty("variant", "ghost")
        self._dismiss_btn.setCursor(Qt.PointingHandCursor)
        self._dismiss_btn.setToolTip("关闭新手清单")
        self._dismiss_btn.clicked.connect(self._dismiss)
        self._dismiss_btn.setVisible(False)
        dismiss_row.addWidget(self._dismiss_btn)
        layout.addLayout(dismiss_row)

    def refresh(self) -> None:
        """Re-check all items and update visual state."""
        completed_count = 0

        # 1. API configured
        try:
            host, key, _model = self.db.load_api_config()
            api_done = bool(host and key)
        except Exception:
            api_done = False
        self._item_api.set_completed(api_done)
        if api_done:
            completed_count += 1

        # 2. First lesson completed
        try:
            lesson_done = self.db.completed_lessons() > 0
        except Exception:
            lesson_done = False
        self._item_lesson.set_completed(lesson_done)
        if lesson_done:
            completed_count += 1

        # 3. First exercise attempted
        try:
            row = self.db.fetchone("SELECT COUNT(*) FROM practice_attempts")
            exercise_done = bool(row and row[0] > 0)
        except Exception:
            exercise_done = False
        self._item_exercise.set_completed(exercise_done)
        if exercise_done:
            completed_count += 1

        # 4. First AI chat
        try:
            chat_done = self._has_ai_messages()
        except Exception:
            chat_done = False
        self._item_chat.set_completed(chat_done)
        if chat_done:
            completed_count += 1

        # Update progress label
        self._progress_label.setText(f"{completed_count}/4")
        all_done = completed_count == 4

        # Show congratulations when all done
        if all_done and not self._all_complete:
            self._all_complete = True
            self._congrats.setVisible(True)
            self._dismiss_btn.setVisible(True)

        # Auto-hide if all complete and user dismissed
        if self._all_complete and not self.isVisible():
            pass  # Already hidden

    def _has_ai_messages(self) -> bool:
        """Check if user has any AI chat messages (non-system)."""
        row = self.db.fetchone("SELECT COUNT(*) FROM mentor_messages WHERE role = 'user'")
        return bool(row and row[0] > 0)

    def _dismiss(self) -> None:
        """Hide the checklist after all items are complete."""
        self.setVisible(False)
