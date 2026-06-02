"""Progressive Hint System widget.

Provides a 3-level hint system for exercises:
- Level 1: Concept hint (key knowledge point)
- Level 2: Approach hint (algorithm/strategy direction)
- Level 3: Pseudocode hint (step-by-step pseudocode)

Tracks hint usage per exercise and integrates with the database.
"""

import logging
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
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
from app.styles import (
    ACCENT,
    BG_CARD_SOFT,
    BORDER,
    FONT,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUB,
    WARNING,
)

logger = logging.getLogger(__name__)

# ── Hint level definitions ─────────────────────────────────────────────────

HINT_LEVELS = [
    {
        "id": "concept",
        "label": "概念提示",
        "description": "提示相关的知识点和核心概念",
        "icon": "?",
        "delay_sec": 0,
        "color": ACCENT,
    },
    {
        "id": "approach",
        "label": "思路提示",
        "description": "提示解题的方向和算法策略",
        "icon": "->",
        "delay_sec": 5,
        "color": WARNING,
    },
    {
        "id": "pseudocode",
        "label": "伪代码提示",
        "description": "展示分步骤的伪代码框架",
        "icon": "{}",
        "delay_sec": 10,
        "color": "#8b5cf6",
    },
]


class HintLevelCard(QFrame):
    """A single hint level card with reveal/delay mechanics."""

    hint_requested = pyqtSignal(str, int)  # (exercise_id, level_index)

    def __init__(self, level_info: dict, parent=None):
        super().__init__(parent)
        self.level_info = level_info
        self._revealed = False
        self._countdown_active = False
        self._remaining_sec = 0
        self._exercise_id: Optional[str] = None

        self.setStyleSheet(
            f"""
            QFrame {{
                background: {BG_CARD_SOFT};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
            """
        )
        self.setFixedHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        header = QHBoxLayout()
        icon_label = QLabel(level_info["icon"])
        icon_label.setFixedSize(28, 28)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(
            f"""
            background: {level_info["color"]};
            color: white;
            border-radius: 14px;
            font-weight: 700;
            font-size: 14px;
            """
        )
        header.addWidget(icon_label)

        title_label = QLabel(level_info["label"])
        title_label.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: 700; font-size: 16px;")
        header.addWidget(title_label)
        header.addStretch()

        self.status_label = QLabel("待查看")
        self.status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        header.addWidget(self.status_label)
        layout.addLayout(header)

        desc_label = QLabel(level_info["description"])
        desc_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 14px;")
        layout.addWidget(desc_label)

        self.hint_content = QLabel("")
        self.hint_content.setWordWrap(True)
        self.hint_content.setStyleSheet(
            f"""
            QLabel {{
                background: rgba(37, 99, 235, 0.06);
                border: 1px solid rgba(37, 99, 235, 0.12);
                border-radius: 10px;
                padding: 8px 12px;
                color: {TEXT_MAIN};
                font-size: 14px;
                line-height: 1.5;
            }}
            """
        )
        self.hint_content.setVisible(False)
        layout.addWidget(self.hint_content)

        self.reveal_btn = QPushButton(f"查看{level_info['label']}")
        self.reveal_btn.setProperty("variant", "secondary")
        self.reveal_btn.setCursor(Qt.PointingHandCursor)
        self.reveal_btn.setToolTip(f"查看{level_info['label']}：{level_info['description']}")
        self.reveal_btn.setAccessibleName(f"查看{level_info['label']}")
        self.reveal_btn.setAccessibleDescription(f"查看{level_info['label']}：{level_info['description']}")
        self.reveal_btn.clicked.connect(self._on_reveal_clicked)
        layout.addWidget(self.reveal_btn)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self._tick_countdown)

    def set_exercise(self, exercise_id: str) -> None:
        self._exercise_id = exercise_id
        self._revealed = False
        self.hint_content.setVisible(False)
        self.reveal_btn.setVisible(True)
        self.reveal_btn.setEnabled(True)
        self.reveal_btn.setText(f"查看{self.level_info['label']}")
        self.status_label.setText("待查看")
        self.status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self.countdown_timer.stop()

    def reveal_with_content(self, content: str) -> None:
        """Reveal the hint with given content."""
        self._revealed = True
        self.hint_content.setText(content)
        self.hint_content.setVisible(True)
        self.reveal_btn.setVisible(False)
        self.status_label.setText("已查看")
        self.status_label.setStyleSheet(f"color: {self.level_info['color']}; font-weight: 600; font-size: 13px;")
        self.hint_requested.emit(self._exercise_id or "", HINT_LEVELS.index(self.level_info))

    def _on_reveal_clicked(self) -> None:
        delay = self.level_info.get("delay_sec", 0)
        if delay > 0 and not self._revealed:
            self._start_countdown(delay)
        else:
            self.reveal_btn.setEnabled(False)
            self.reveal_btn.setText("加载中...")
            # Signal to parent to provide content
            self.hint_requested.emit(self._exercise_id or "", HINT_LEVELS.index(self.level_info))

    def _start_countdown(self, seconds: int) -> None:
        self._remaining_sec = seconds
        self._countdown_active = True
        self.reveal_btn.setEnabled(False)
        self.reveal_btn.setText(f"{seconds} 秒后可查看")
        self.countdown_timer.start()

    def _tick_countdown(self) -> None:
        self._remaining_sec -= 1
        if self._remaining_sec <= 0:
            self.countdown_timer.stop()
            self._countdown_active = False
            self.reveal_btn.setEnabled(True)
            self.reveal_btn.setText(f"查看{self.level_info['label']}")
        else:
            self.reveal_btn.setText(f"{self._remaining_sec} 秒后可查看")


class HintSystemWidget(QWidget):
    """Complete progressive hint system widget with 3 levels."""

    hint_used = pyqtSignal(str, int, str)  # (exercise_id, level, content)

    def __init__(self, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self._exercise_id: Optional[str] = None
        self._exercise_hints: dict = {}  # level_index -> content string

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("渐进式提示")
        title.setFont(QFont(FONT, 18, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        header.addWidget(title)
        header.addStretch()

        self.usage_label = QLabel("")
        self.usage_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px;")
        header.addWidget(self.usage_label)
        root.addLayout(header)

        helper = QLabel("逐级展开提示，先思考再查看。每次查看都会记录。")
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {TEXT_SUB}; font-size: 14px;")
        root.addWidget(helper)

        self.level_cards = []
        for level_info in HINT_LEVELS:
            card = HintLevelCard(level_info)
            card.hint_requested.connect(self._on_hint_requested)
            root.addWidget(card)
            self.level_cards.append(card)

        self._update_usage_display()

    def set_exercise(self, exercise_id: str, hints: Optional[list] = None) -> None:
        """Set the current exercise and its hints."""
        self._exercise_id = exercise_id
        self._exercise_hints = {}

        if hints:
            for i, hint_content in enumerate(hints):
                if i < len(HINT_LEVELS):
                    self._exercise_hints[i] = hint_content

        # Map hints to levels: distribute available hints across 3 levels
        if hints and len(hints) < len(HINT_LEVELS):
            # If fewer hints than levels, map what we have
            for i, hint_content in enumerate(hints):
                self._exercise_hints[i] = hint_content
        elif hints and len(hints) > len(HINT_LEVELS):
            # If more hints than levels, group them
            chunk_size = max(1, len(hints) // len(HINT_LEVELS))
            for level_idx in range(len(HINT_LEVELS)):
                start = level_idx * chunk_size
                end = start + chunk_size if level_idx < len(HINT_LEVELS) - 1 else len(hints)
                chunk = hints[start:end]
                self._exercise_hints[level_idx] = "\n".join(chunk)

        for card in self.level_cards:
            card.set_exercise(exercise_id)

        self._update_usage_display()

    def _on_hint_requested(self, exercise_id: str, level_index: int) -> None:
        """Handle hint reveal request from a level card."""
        if not exercise_id or level_index >= len(self.level_cards):
            return

        content = self._exercise_hints.get(level_index, "")
        if not content:
            # Generate a generic hint for this level
            level_info = HINT_LEVELS[level_index]
            content = self._generate_generic_hint(level_info, level_index)

        card = self.level_cards[level_index]
        card.reveal_with_content(content)

        # Record in database
        self.db.record_hint_usage(exercise_id, level_index)
        self._update_usage_display()

        # Emit signal for external listeners
        self.hint_used.emit(exercise_id, level_index, content)

    def _generate_generic_hint(self, level_info: dict, level_index: int) -> str:
        """Generate a generic hint when no specific hint is available."""
        generic_hints = {
            "concept": "回顾这道题涉及的核心概念。想想输入和输出分别是什么，需要用到哪些基本操作。",
            "approach": "考虑使用什么算法或数据结构。试试把大问题分解成小步骤，先处理最简单的情况。",
            "pseudocode": "1) 读取输入\n2) 初始化变量\n3) 处理核心逻辑（循环或递归）\n4) 输出结果",
        }
        return generic_hints.get(level_info["id"], "暂无提示，请先尝试自己解决。")

    def _update_usage_display(self) -> None:
        if not self._exercise_id:
            self.usage_label.setText("")
            return
        total = self.db.hint_usage_count(self._exercise_id)
        self.usage_label.setText(f"本题已使用 {total} 次提示" if total > 0 else "本题还未使用提示")

    def get_hint_stats(self) -> dict:
        """Get hint usage statistics for the current exercise."""
        if not self._exercise_id:
            return {"total": 0, "levels_used": 0}
        total = self.db.hint_usage_count(self._exercise_id)
        return {
            "total": total,
            "levels_used": min(total, len(HINT_LEVELS)),
        }
