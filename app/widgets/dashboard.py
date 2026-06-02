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

from app.content_service import ContentService
from app.database import AppDatabase
from app.effects import apply_shadow
from app.styles import (
    ACCENT,
    ACCENT_SOFT,
    BG_CARD,
    BG_CARD_SOFT,
    BORDER,
    F_TITLE,
    FONT,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUB,
)


class DashboardWidget(QWidget):
    navigate_requested = pyqtSignal(int)
    track_requested = pyqtSignal(str)

    def __init__(self, content_service: ContentService, db: AppDatabase):
        super().__init__()
        self.content_service = content_service
        self.db = db

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 12, 18, 18)
        root.setSpacing(24)

        root.addWidget(self._build_welcome())
        root.addWidget(self._build_stats_row())
        root.addWidget(self._build_tracks_section())
        root.addWidget(self._build_quick_actions())
        root.addStretch()

    # ── sections ────────────────────────────────────────

    def _build_welcome(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(8)

        title = QLabel("欢迎回来")
        title.setFont(QFont(FONT, F_TITLE - 8, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(title)

        self.welcome_sub = QLabel("正在加载学习数据...")
        self.welcome_sub.setWordWrap(True)
        self.welcome_sub.setStyleSheet(f"color: {TEXT_SUB}; font-size: 21px;")
        layout.addWidget(self.welcome_sub)
        return card

    def _build_stats_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.stat_lessons = self._stat_card("已完成课程", "0")
        self.stat_score = self._stat_card("练习平均分", "0")
        self.stat_streak = self._stat_card("连续学习天数", "0")

        layout.addWidget(self.stat_lessons)
        layout.addWidget(self.stat_score)
        layout.addWidget(self.stat_streak)
        return row

    def _build_tracks_section(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QLabel("学习路线")
        header.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        layout.addWidget(header)

        self.track_buttons = []
        for track in self.content_service.tracks:
            btn = QPushButton(f"{track.icon}  {track.title}")
            btn.setProperty("variant", "secondary")
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    text-align: left;
                    padding: 18px 24px;
                    font-size: 21px;
                    min-height: 60px;
                    border-radius: 14px;
                    background: {BG_CARD_SOFT};
                    border: 1px solid {BORDER};
                    color: {TEXT_MAIN};
                }}
                QPushButton:hover {{
                    background: {ACCENT_SOFT};
                    color: {ACCENT};
                }}
                """
            )
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, tid=track.id: self.track_requested.emit(tid)
            )
            layout.addWidget(btn)
            self.track_buttons.append(btn)

        if not self.content_service.tracks:
            placeholder = QLabel("暂时没有可用的学习路线。")
            placeholder.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px;")
            layout.addWidget(placeholder)

        return card

    def _build_quick_actions(self) -> QFrame:
        card = self._card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(14)

        actions = [
            ("继续学习", 1),
            ("去练习", 2),
            ("看项目", 3),
            ("算法动画", 4),
        ]
        for label, page_index in actions:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, i=page_index: self.navigate_requested.emit(i)
            )
            layout.addWidget(btn)

        return card

    # ── helpers ──────────────────────────────────────────

    def _card(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
            """
        )
        apply_shadow(frame, blur=18, offset_y=4)
        return frame

    def _stat_card(self, title: str, value: str) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(6)

        val_label = QLabel(value)
        val_label.setFont(QFont(FONT, F_TITLE - 8, QFont.Bold))
        val_label.setStyleSheet(f"color: {ACCENT};")
        val_label.setAlignment(Qt.AlignCenter)
        val_label.setObjectName("stat_value")
        layout.addWidget(val_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        return card

    def _update_stat(self, card: QFrame, value) -> None:
        label = card.findChild(QLabel, "stat_value")
        if label:
            label.setText(str(value))

    # ── refresh ─────────────────────────────────────────

    def refresh(self) -> None:
        completed = self.db.completed_lessons()
        total = len(self.content_service.all_lessons())
        avg_score = self.db.average_score()
        streak = self.db.active_days_streak()

        self._update_stat(self.stat_lessons, completed)
        self._update_stat(self.stat_score, avg_score)
        self._update_stat(self.stat_streak, streak)

        if completed == 0:
            self.welcome_sub.setText(
                "还没有开始学习，选一条路线开始吧！"
            )
        else:
            self.welcome_sub.setText(
                f"你已完成 {completed}/{total} 节课程，平均分 {avg_score}，"
                f"连续学习 {streak} 天。继续加油！"
            )
