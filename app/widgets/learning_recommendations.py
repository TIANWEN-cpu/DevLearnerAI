"""Learning Recommendations widget.

Provides:
- Next lesson recommendation based on progress
- Review schedule using spaced repetition (SM-2 algorithm)
- Weakness identification from practice attempt history
"""

import logging
from datetime import date

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.content_service import ContentService
from app.database import AppDatabase
from app.effects import apply_shadow
from app.styles import (
    ACCENT,
    BG_CARD,
    BG_CARD_SOFT,
    BORDER,
    FONT,
    SUCCESS,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUB,
    WARNING,
)

logger = logging.getLogger(__name__)


# ── Recommendation Card ──────────────────────────────────────────────────────


class RecommendationCard(QFrame):
    """A single recommendation card with icon, title, and action."""

    clicked = pyqtSignal(str)  # lesson_id or exercise_id

    def __init__(self, title: str, subtitle: str, icon: str = "*", color: str = ACCENT, item_id: str = "", parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {BG_CARD_SOFT};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
            QFrame:hover {{
                border: 1px solid {color};
                background: rgba(37, 99, 235, 0.04);
            }}
            """
        )
        self.setFixedHeight(76)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        icon_label = QLabel(icon)
        icon_label.setFixedSize(36, 36)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(
            f"""
            background: {color};
            color: white;
            border-radius: 18px;
            font-weight: 700;
            font-size: 16px;
            """
        )
        layout.addWidget(icon_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: 700; font-size: 15px;")
        text_col.addWidget(title_label)

        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        sub_label.setWordWrap(True)
        text_col.addWidget(sub_label)
        layout.addLayout(text_col, 1)

        arrow = QLabel(">")
        arrow.setStyleSheet(f"color: {color}; font-weight: 700; font-size: 18px;")
        layout.addWidget(arrow)

    def mousePressEvent(self, event):
        if self.item_id:
            self.clicked.emit(self.item_id)
        super().mousePressEvent(event)


# ── Next Lesson Section ──────────────────────────────────────────────────────


class NextLessonSection(QWidget):
    """Recommends the next lesson based on learning progress."""

    lesson_selected = pyqtSignal(str)  # lesson_id

    def __init__(self, content_service: ContentService, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.content_service = content_service
        self.db = db

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QLabel("推荐下一课")
        header.setFont(QFont(FONT, 16, QFont.Bold))
        header.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(header)

        self.cards_container = QVBoxLayout()
        self.cards_container.setSpacing(6)
        layout.addLayout(self.cards_container)

    def refresh(self) -> None:
        # Clear old cards
        while self.cards_container.count():
            item = self.cards_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        recommendations = self._find_next_lessons()
        if not recommendations:
            placeholder = QLabel("暂无推荐，继续保持学习节奏！")
            placeholder.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px;")
            self.cards_container.addWidget(placeholder)
            return

        for lesson_id, title, track_title, reason in recommendations[:3]:
            card = RecommendationCard(
                title=title,
                subtitle=f"{track_title} - {reason}",
                icon=">",
                color=ACCENT,
                item_id=lesson_id,
            )
            card.clicked.connect(self.lesson_selected.emit)
            self.cards_container.addWidget(card)

    def _find_next_lessons(self) -> list:
        """Find recommended next lessons based on progress."""
        results = []
        for track in self.content_service.tracks:
            found_uncompleted = False
            for module in track.modules:
                for lesson in module.lessons:
                    status = self.db.lesson_status(lesson.id)
                    if status != "completed" and not found_uncompleted:
                        found_uncompleted = True
                        reason = "当前模块下一个未完成的课程"
                        results.append((lesson.id, lesson.title, track.title, reason))
                        break
                if found_uncompleted:
                    break
        return results


# ── Review Schedule Section ──────────────────────────────────────────────────


class ReviewScheduleSection(QWidget):
    """Displays spaced repetition review schedule."""

    exercise_selected = pyqtSignal(str)  # exercise_id

    def __init__(self, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.db = db

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header = QLabel("复习计划")
        header.setFont(QFont(FONT, 16, QFont.Bold))
        header.setStyleSheet(f"color: {TEXT_MAIN};")
        header_row.addWidget(header)

        self.due_count_label = QLabel("")
        self.due_count_label.setStyleSheet(f"color: {WARNING}; font-weight: 700; font-size: 15px;")
        header_row.addWidget(self.due_count_label)
        header_row.addStretch()
        layout.addLayout(header_row)

        desc = QLabel("基于间隔重复算法（SM-2），在最佳时间点安排复习。")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SUB}; font-size: 13px;")
        layout.addWidget(desc)

        self.cards_container = QVBoxLayout()
        self.cards_container.setSpacing(6)
        layout.addLayout(self.cards_container)

    def refresh(self) -> None:
        # Clear old cards
        while self.cards_container.count():
            item = self.cards_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        due_items = self.db.exercises_due_for_review(limit=5)
        today_count = self.db.review_count_today()

        self.due_count_label.setText(f"今日待复习: {len(due_items)} 题 | 已复习: {today_count} 题")

        if not due_items:
            placeholder = QLabel("今天没有需要复习的练习，继续学习新内容吧！")
            placeholder.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px;")
            placeholder.setWordWrap(True)
            self.cards_container.addWidget(placeholder)
            return

        for exercise_id, interval_days, next_review in due_items:
            # Try to get exercise title from practice service
            days_overdue = (date.today() - date.fromisoformat(next_review)).days
            if days_overdue > 0:
                urgency = f"逾期 {days_overdue} 天"
                color = WARNING
            else:
                urgency = "今日待复习"
                color = ACCENT

            subtitle = f"间隔 {interval_days:.0f} 天 - {urgency}"
            card = RecommendationCard(
                title=exercise_id,
                subtitle=subtitle,
                icon="R",
                color=color,
                item_id=exercise_id,
            )
            card.clicked.connect(self.exercise_selected.emit)
            self.cards_container.addWidget(card)


# ── Weakness Identification Section ──────────────────────────────────────────


class WeaknessSection(QWidget):
    """Identifies weak areas from practice attempt history."""

    def __init__(self, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.db = db

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QLabel("薄弱环节")
        header.setFont(QFont(FONT, 16, QFont.Bold))
        header.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(header)

        desc = QLabel("根据练习得分和通过率，识别需要加强的知识领域。")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SUB}; font-size: 13px;")
        layout.addWidget(desc)

        self.weakness_container = QVBoxLayout()
        self.weakness_container.setSpacing(6)
        layout.addLayout(self.weakness_container)

    def refresh(self) -> None:
        # Clear old items
        while self.weakness_container.count():
            item = self.weakness_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        weaknesses = self._analyze_weaknesses()
        if not weaknesses:
            placeholder = QLabel("暂无足够数据进行分析，多做几道练习题即可生成薄弱环节报告。")
            placeholder.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px;")
            placeholder.setWordWrap(True)
            self.weakness_container.addWidget(placeholder)
            return

        for track_id, track_title, avg_score, pass_rate, attempt_count in weaknesses:
            bar_color = WARNING if avg_score < 60 else (ACCENT if avg_score < 80 else SUCCESS)
            subtitle = f"平均分: {avg_score:.0f} | 通过率: {pass_rate:.0f}% | 做题数: {attempt_count}"
            card = RecommendationCard(
                title=track_title,
                subtitle=subtitle,
                icon="!",
                color=bar_color,
                item_id=track_id,
            )
            self.weakness_container.addWidget(card)

    def _analyze_weaknesses(self) -> list:
        """Analyze practice attempts to identify weak areas."""
        try:
            rows = self.db.fetchall(
                """
                SELECT track_id,
                       COUNT(*) as attempt_count,
                       AVG(score) as avg_score,
                       SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pass_rate
                FROM practice_attempts
                GROUP BY track_id
                HAVING attempt_count >= 2
                ORDER BY avg_score ASC
                """
            )
        except Exception as exc:
            logger.warning("分析薄弱环节失败: %s", exc)
            return []

        results = []
        for track_id, attempt_count, avg_score, pass_rate in rows:
            if avg_score < 80:
                track_title = track_id  # Will be resolved by caller
                results.append((track_id, track_title, avg_score, pass_rate, attempt_count))

        return results[:5]


# ── Main Learning Recommendations Widget ─────────────────────────────────────


class LearningRecommendationsWidget(QWidget):
    """Complete learning recommendations widget combining all recommendation sections."""

    lesson_selected = pyqtSignal(str)  # lesson_id
    exercise_selected = pyqtSignal(str)  # exercise_id

    def __init__(self, content_service: ContentService, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.content_service = content_service
        self.db = db

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("学习推荐")
        title.setFont(QFont(FONT, 22, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        header_row.addWidget(title)
        header_row.addStretch()

        refresh_btn = QPushButton("刷新推荐")
        refresh_btn.setProperty("variant", "secondary")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setToolTip("刷新学习推荐数据")
        refresh_btn.setAccessibleName("刷新推荐")
        refresh_btn.setAccessibleDescription("刷新学习推荐数据，获取最新的个性化学习建议")
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn)
        root.addLayout(header_row)

        # Scroll area for all sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # Next lesson section
        self.next_lesson_section = NextLessonSection(content_service, db)
        self.next_lesson_section.lesson_selected.connect(self.lesson_selected.emit)
        content_layout.addWidget(self._wrap_card(self.next_lesson_section))

        # Review schedule section
        self.review_section = ReviewScheduleSection(db)
        self.review_section.exercise_selected.connect(self.exercise_selected.emit)
        content_layout.addWidget(self._wrap_card(self.review_section))

        # Weakness section
        self.weakness_section = WeaknessSection(db)
        content_layout.addWidget(self._wrap_card(self.weakness_section))

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        root.addWidget(scroll, 1)

    def _wrap_card(self, widget: QWidget) -> QFrame:
        """Wrap a section widget in a styled card frame."""
        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            """
        )
        apply_shadow(card, blur=12, offset_y=2)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        layout.addWidget(widget)
        return card

    def refresh(self) -> None:
        """Refresh all recommendation sections."""
        self.next_lesson_section.refresh()
        self.review_section.refresh()
        self.weakness_section.refresh()
