"""Dashboard widget -- learning overview, stats, charts, and goal setting."""

import logging

from PyQt5.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.content_service import ContentService
from app.database import AppDatabase
from app.effects import apply_shadow
from app.i18n import tr
from app.styles import (
    ACCENT,
    ACCENT_SOFT,
    BG_CARD,
    BG_CARD_SOFT,
    BORDER,
    F_TITLE,
    FONT,
    SUCCESS,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUB,
    WARNING,
    score_label,
)

# ── Mini bar chart widget ────────────────────────────────────────────────────


class MiniBarChart(QWidget):
    """A simple vertical bar chart for displaying weekly activity."""

    def __init__(self, data=None, labels=None, bar_color="#2563eb", parent=None):
        super().__init__(parent)
        self._data = data or []
        self._labels = labels or []
        self._bar_color = QColor(bar_color)
        self.setMinimumHeight(120)
        self.setMinimumWidth(200)
        self._chart_description = ""

    def set_data(self, data, labels=None):
        self._data = data or []
        self._labels = labels or []
        # Build accessible description from data
        if self._data and self._labels:
            parts = [f"{label}: {val}" for label, val in zip(self._labels, self._data)]
            self._chart_description = ", ".join(parts)
        elif self._data:
            self._chart_description = f"数据值: {', '.join(str(v) for v in self._data)}"
        self.setAccessibleDescription(self._chart_description)
        self.update()

    def paintEvent(self, event):
        if not self._data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._data)
        if n == 0:
            painter.end()
            return

        max_val = max(max(self._data), 1)
        margin = 10
        label_h = 20
        chart_h = h - label_h - margin * 2
        bar_w = max(8, (w - margin * 2) // (n * 2))

        for i, val in enumerate(self._data):
            x = margin + i * (bar_w * 2) + bar_w // 2
            bar_h = int(chart_h * val / max_val) if max_val > 0 else 0
            y = margin + chart_h - bar_h

            # Bar gradient
            color = self._bar_color
            color.setAlpha(200 if val > 0 else 60)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x, y, bar_w, bar_h, 4, 4)

            # Label
            if i < len(self._labels):
                painter.setPen(QPen(QColor("#94a3b8")))
                painter.drawText(x - 2, h - 4, self._labels[i])

        painter.end()


# ── Streak flame widget ──────────────────────────────────────────────────────


class StreakFlame(QWidget):
    """Visual streak counter with a flame-like indicator."""

    def __init__(self, days=0, parent=None):
        super().__init__(parent)
        self._days = days
        self.setFixedSize(100, 80)

    def set_days(self, days):
        self._days = days
        self.setAccessibleName(f"连续学习 {days} 天")
        self.setAccessibleDescription(f"连续学习天数: {days} 天")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background circle
        color = SUCCESS if self._days >= 7 else (ACCENT if self._days >= 3 else WARNING)
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(10, 5, 60, 60)

        # Day count
        painter.setPen(QPen(QColor("#ffffff")))
        font = QFont(FONT, 24, QFont.Bold)
        painter.setFont(font)
        painter.drawText(10, 5, 60, 60, Qt.AlignCenter, str(self._days))

        # Label
        painter.setPen(QPen(QColor(TEXT_SUB)))
        font_small = QFont(FONT, 14)
        painter.setFont(font_small)
        painter.drawText(0, 66, 80, 14, Qt.AlignCenter, "天连续")

        painter.end()


# ── Dashboard widget ─────────────────────────────────────────────────────────


class DashboardWidget(QWidget):
    navigate_requested = pyqtSignal(int)
    track_requested = pyqtSignal(str)

    def __init__(self, content_service: ContentService, db: AppDatabase):
        super().__init__()
        self.content_service = content_service
        self.db = db
        self._last_refresh_ts = 0.0
        self._refresh_min_interval = 2.0  # seconds - throttle rapid refreshes

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 12, 18, 18)
        root.setSpacing(24)

        root.addWidget(self._build_welcome())
        root.addWidget(self._build_stats_row())
        root.addWidget(self._build_progress_section())
        root.addWidget(self._build_tracks_section())
        root.addWidget(self._build_goal_section())
        root.addWidget(self._build_quick_actions())
        root.addStretch()

    # ── sections ─────────────────────────────────────────────────────────────

    def _build_welcome(self) -> QFrame:
        card = self._card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        text_col = QVBoxLayout()
        text_col.setSpacing(8)

        title = QLabel(tr("dashboard.welcome"))
        title.setFont(QFont(FONT, F_TITLE - 8, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        text_col.addWidget(title)

        self.welcome_sub = QLabel(tr("dashboard.loading"))
        self.welcome_sub.setWordWrap(True)
        self.welcome_sub.setStyleSheet(f"color: {TEXT_SUB}; font-size: 21px;")
        text_col.addWidget(self.welcome_sub)
        layout.addLayout(text_col, 1)

        self.streak_flame = StreakFlame(0)
        layout.addWidget(self.streak_flame)
        return card

    def _build_stats_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        self.stat_lessons = self._stat_card(tr("dashboard.stat_lessons"), "0", ACCENT)
        self.stat_score = self._stat_card(tr("dashboard.stat_score"), "0", SUCCESS)
        self.stat_streak = self._stat_card(tr("dashboard.stat_streak"), "0", WARNING)
        self.stat_attempts = self._stat_card(tr("dashboard.stat_attempts"), "0", "#8b5cf6")

        layout.addWidget(self.stat_lessons)
        layout.addWidget(self.stat_score)
        layout.addWidget(self.stat_streak)
        layout.addWidget(self.stat_attempts)
        return row

    def _build_progress_section(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        title = QLabel(tr("dashboard.progress_title"))
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        header_row.addWidget(title)
        header_row.addStretch()

        self.progress_pct = QLabel("0%")
        self.progress_pct.setStyleSheet(f"color: {ACCENT}; font-weight: 700; font-size: 28px;")
        header_row.addWidget(self.progress_pct)
        layout.addLayout(header_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setAccessibleName(tr("dashboard.progress_name"))
        self.progress_bar.setAccessibleDescription(tr("dashboard.progress_desc"))
        layout.addWidget(self.progress_bar)

        self.chart_container = QFrame()
        chart_layout = QHBoxLayout(self.chart_container)
        chart_layout.setContentsMargins(0, 8, 0, 0)
        chart_layout.setSpacing(18)

        # Weekly activity chart
        chart_left = QVBoxLayout()
        chart_left.setSpacing(6)
        chart_label = QLabel(tr("dashboard.chart_weekly"))
        chart_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px; font-weight: 600;")
        self.weekly_chart = MiniBarChart(bar_color=ACCENT)
        self.weekly_chart.setAccessibleName(tr("dashboard.chart_weekly_name"))
        chart_left.addWidget(chart_label)
        chart_left.addWidget(self.weekly_chart)
        chart_layout.addLayout(chart_left, 1)

        # Recent scores chart
        chart_right = QVBoxLayout()
        chart_right.setSpacing(6)
        score_label_text = QLabel(tr("dashboard.chart_scores"))
        score_label_text.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px; font-weight: 600;")
        self.score_chart = MiniBarChart(bar_color=SUCCESS)
        self.score_chart.setAccessibleName(tr("dashboard.chart_scores_name"))
        chart_right.addWidget(score_label_text)
        chart_right.addWidget(self.score_chart)
        chart_layout.addLayout(chart_right, 1)

        layout.addWidget(self.chart_container)
        return card

    def _build_tracks_section(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QLabel(tr("dashboard.tracks_title"))
        header.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        layout.addWidget(header)

        self.track_buttons = []
        for track in self.content_service.tracks:
            btn = QPushButton(f"{track.icon}  {track.title}")
            btn.setProperty("variant", "secondary")
            btn.setToolTip(tr("dashboard.track_tooltip", title=track.title))
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
            btn.clicked.connect(lambda checked=False, tid=track.id: self.track_requested.emit(tid))
            layout.addWidget(btn)
            self.track_buttons.append(btn)

        if not self.content_service.tracks:
            placeholder = QLabel(tr("dashboard.no_tracks"))
            placeholder.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px;")
            layout.addWidget(placeholder)

        return card

    def _build_goal_section(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel(tr("dashboard.goal_title"))
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        layout.addWidget(title)

        goal_row = QHBoxLayout()
        goal_row.setSpacing(14)
        for label, target, icon in [
            (tr("dashboard.goal_daily"), 1, "D"),
            (tr("dashboard.goal_weekly"), 5, "W"),
            (tr("dashboard.goal_monthly"), 20, "M"),
        ]:
            btn = QPushButton(f"{icon} {label}")
            btn.setProperty("variant", "secondary")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tr("dashboard.goal_tooltip", label=label, target=target))
            btn.clicked.connect(lambda _checked=False, t=target, lbl=label: self._set_goal(t, lbl))
            goal_row.addWidget(btn)
        layout.addLayout(goal_row)

        self.goal_label = QLabel(tr("dashboard.goal_hint"))
        self.goal_label.setWordWrap(True)
        self.goal_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px;")
        layout.addWidget(self.goal_label)

        self.goal_bar = QProgressBar()
        self.goal_bar.setFixedHeight(12)
        self.goal_bar.setTextVisible(False)
        self.goal_bar.setValue(0)
        self.goal_bar.setAccessibleName(tr("dashboard.goal_progress_name"))
        self.goal_bar.setAccessibleDescription(tr("dashboard.goal_progress_desc"))
        layout.addWidget(self.goal_bar)

        self._goal_target = 0
        self._goal_label_text = ""
        return card

    def _build_quick_actions(self) -> QFrame:
        card = self._card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(14)

        quick_tooltips = {
            1: tr("dashboard.quick_learn_tip"),
            2: tr("dashboard.quick_practice_tip"),
            3: tr("dashboard.quick_projects_tip"),
            4: tr("dashboard.quick_algo_tip"),
        }
        actions = [
            (tr("dashboard.quick_learn"), 1),
            (tr("dashboard.quick_practice"), 2),
            (tr("dashboard.quick_projects"), 3),
            (tr("dashboard.quick_algo"), 4),
        ]
        for label, page_index in actions:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(quick_tooltips.get(page_index, ""))
            btn.clicked.connect(lambda checked=False, i=page_index: self.navigate_requested.emit(i))
            layout.addWidget(btn)

        return card

    # ── helpers ──────────────────────────────────────────────────────────────

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

    def _stat_card(self, title: str, value: str, color: str = ACCENT) -> QFrame:
        card = self._card()
        card.setAccessibleName(title)
        card.setAccessibleDescription(f"{title}: {value}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(6)

        val_label = QLabel(value)
        val_label.setFont(QFont(FONT, F_TITLE - 8, QFont.Bold))
        val_label.setStyleSheet(f"color: {color};")
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
            card.setAccessibleDescription(f"{card.accessibleName()}: {value}")

    def _set_goal(self, target: int, label: str) -> None:
        self._goal_target = target
        self._goal_label_text = label
        completed_today = self.db.completed_lessons()
        # For simplicity, use total completed as proxy
        progress = min(100, int(completed_today / max(target, 1) * 100))
        self.goal_bar.setValue(progress)
        self.goal_label.setText(
            tr("dashboard.goal_status", label=label, target=target, completed=completed_today, pct=progress)
        )

    # ── refresh ──────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        # Throttle rapid refreshes to prevent unnecessary DB queries
        import time as _time

        now = _time.monotonic()
        if now - self._last_refresh_ts < self._refresh_min_interval:
            return
        self._last_refresh_ts = now

        try:
            completed = self.db.completed_lessons()
            total = len(self.content_service.all_lessons())
            avg_score = self.db.average_score()
            streak = self.db.active_days_streak()
        except Exception as exc:
            logger.error("刷新仪表板数据失败: %s", exc, exc_info=True)
            self.welcome_sub.setText(tr("dashboard.load_error"))
            return

        self._update_stat(self.stat_lessons, completed)
        self._update_stat(self.stat_score, f"{avg_score} ({score_label(avg_score)})")
        self._update_stat(self.stat_streak, streak)

        # Attempt count
        try:
            count_row = self.db.fetchone("SELECT COUNT(*) FROM practice_attempts")
            attempt_count = int(count_row[0]) if count_row and count_row[0] is not None else 0
        except Exception as exc:
            logger.warning("查询练习次数失败: %s", exc)
            attempt_count = 0
        self._update_stat(self.stat_attempts, attempt_count)

        # Streak flame
        self.streak_flame.set_days(streak)

        # Progress bar
        pct = int(completed / max(total, 1) * 100)
        self.progress_bar.setValue(pct)
        self.progress_pct.setText(f"{pct}%")

        # Weekly chart - compute activity per day of last 7 days
        from datetime import date, timedelta

        today = date.today()
        # Fetch recent attempts for charting (limit to 7 days worth)
        chart_attempts = self.db.recent_attempts(limit=200)
        weekly_data = []
        weekly_labels = ["一", "二", "三", "四", "五", "六", "日"]
        day_names = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            day_names.append(weekly_labels[d.weekday()])
            count = 0
            for _submitted_at, _title, _score, _passed, _dur in chart_attempts:
                if _submitted_at and _submitted_at.startswith(d.isoformat()):
                    count += 1
            weekly_data.append(count)
        self.weekly_chart.set_data(weekly_data, day_names)

        # Score chart - last 8 attempts
        score_data = [s for (_at, _t, s, _p, _d) in chart_attempts[:8]]
        score_data.reverse()
        self.score_chart.set_data(score_data)

        # Goal bar
        if self._goal_target > 0:
            progress = min(100, int(completed / max(self._goal_target, 1) * 100))
            self.goal_bar.setValue(progress)
            self.goal_label.setText(
                tr(
                    "dashboard.goal_status",
                    label=self._goal_label_text,
                    target=self._goal_target,
                    completed=completed,
                    pct=progress,
                )
            )

        # Welcome text
        if completed == 0:
            self.welcome_sub.setText(tr("dashboard.welcome_empty"))
        else:
            self.welcome_sub.setText(
                tr("dashboard.welcome_summary", completed=completed, total=total, avg=avg_score, streak=streak)
            )
