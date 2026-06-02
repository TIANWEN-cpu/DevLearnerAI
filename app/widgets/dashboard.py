"""Dashboard widget -- learning overview, stats, charts, and goal setting.

Enhanced with interactive data-visualization charts:
- LineChart for learning progress over time
- RadarChart for skill distribution across tracks
- HeatmapCalendar for daily activity heat map
- BarChart for score drill-down
"""

import logging
from datetime import date, timedelta

from PyQt5.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QDialog,
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
from app.widgets.charts import HeatmapCalendar, LineChart, RadarChart

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
        root.addWidget(self._build_progress_line_chart_section())
        root.addWidget(self._build_skill_radar_section())
        root.addWidget(self._build_heatmap_section())
        root.addWidget(self._build_recommendations_section())
        root.addWidget(self._build_tracks_section())
        root.addWidget(self._build_analytics_section())
        root.addWidget(self._build_achievements_section())
        root.addWidget(self._build_bookmarks_section())
        root.addWidget(self._build_goal_section())
        root.addWidget(self._build_quick_actions())
        root.addWidget(self._build_data_actions())
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

    def _build_recommendations_section(self) -> QFrame:
        """Build the learning recommendations section for the dashboard."""
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("学习推荐")
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        view_all_btn = QPushButton("查看全部推荐")
        view_all_btn.setProperty("variant", "secondary")
        view_all_btn.setCursor(Qt.PointingHandCursor)
        view_all_btn.setToolTip("打开完整的学习推荐面板")
        view_all_btn.setAccessibleName("查看全部推荐")
        view_all_btn.setAccessibleDescription("打开学习推荐对话框，查看个性化学习建议")
        view_all_btn.clicked.connect(self._show_recommendations_dialog)
        header.addWidget(view_all_btn)
        layout.addLayout(header)

        # Inline summary of recommendations
        self.recommendations_summary = QLabel("加载中...")
        self.recommendations_summary.setWordWrap(True)
        self.recommendations_summary.setStyleSheet(f"color: {TEXT_SUB}; font-size: 16px;")
        layout.addWidget(self.recommendations_summary)

        # Row of recommendation cards
        self.recommendation_cards_row = QHBoxLayout()
        self.recommendation_cards_row.setSpacing(12)
        layout.addLayout(self.recommendation_cards_row)

        return card

    def _show_recommendations_dialog(self) -> None:
        """Open a dialog showing all learning recommendations."""
        from PyQt5.QtWidgets import QVBoxLayout as DlgLayout

        from app.widgets.learning_recommendations import LearningRecommendationsWidget

        dialog = QDialog(self)
        dialog.setWindowTitle("学习推荐")
        dialog.setMinimumSize(720, 580)
        dialog.setAccessibleName("学习推荐对话框")
        dlg_layout = DlgLayout(dialog)
        dlg_layout.setContentsMargins(0, 0, 0, 0)
        widget = LearningRecommendationsWidget(self.content_service, self.db, dialog)
        widget.refresh()
        dlg_layout.addWidget(widget)
        dialog.exec_()

    def _refresh_recommendations(self) -> None:
        """Refresh the inline recommendations summary on the dashboard."""
        # Next lesson recommendation
        next_lesson_text = ""
        for track in self.content_service.tracks:
            for module in track.modules:
                for lesson in module.lessons:
                    status = self.db.lesson_status(lesson.id)
                    if status != "completed":
                        next_lesson_text = f"推荐下一课：{lesson.title}（{track.title}）"
                        break
                if next_lesson_text:
                    break
            if next_lesson_text:
                break

        # Review due count
        due_reviews = self.db.exercises_due_for_review(limit=10)
        review_text = f"今日待复习 {len(due_reviews)} 道练习" if due_reviews else ""

        # Weakness summary
        try:
            weak_rows = self.db.fetchall(
                """
                SELECT track_id, AVG(score) as avg_score
                FROM practice_attempts
                GROUP BY track_id
                HAVING COUNT(*) >= 2 AND AVG(score) < 80
                ORDER BY avg_score ASC
                LIMIT 2
                """
            )
            weak_text = f"发现 {len(weak_rows)} 个薄弱领域" if weak_rows else ""
        except Exception:
            logger.debug("查询薄弱领域失败", exc_info=True)
            weak_text = ""

        # Build summary text
        parts = [p for p in [next_lesson_text, review_text, weak_text] if p]
        if parts:
            self.recommendations_summary.setText("  |  ".join(parts))
        else:
            self.recommendations_summary.setText("暂无推荐数据，开始学习和练习后会自动生成个性化推荐。")

        # Clear old recommendation cards
        while self.recommendation_cards_row.count():
            item = self.recommendation_cards_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Add inline recommendation mini-cards
        from app.widgets.learning_recommendations import RecommendationCard

        if next_lesson_text:
            card = RecommendationCard(
                title="继续学习",
                subtitle=next_lesson_text.replace("推荐下一课：", ""),
                icon=">",
                color=ACCENT,
                item_id="learn",
            )
            self.recommendation_cards_row.addWidget(card)

        if due_reviews:
            card = RecommendationCard(
                title="复习提醒",
                subtitle=f"{len(due_reviews)} 道题等待复习",
                icon="R",
                color=WARNING,
            )
            self.recommendation_cards_row.addWidget(card)

        if weak_rows:
            card = RecommendationCard(
                title="薄弱环节",
                subtitle=weak_text,
                icon="!",
                color="#ef4444",
            )
            self.recommendation_cards_row.addWidget(card)

        self.recommendation_cards_row.addStretch()

    def _build_tracks_section(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QLabel(tr("dashboard.tracks_title"))
        header.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        layout.addWidget(header)

        self.track_buttons = []
        self.track_progress_bars = []
        for track in self.content_service.tracks:
            track_frame = QFrame()
            track_frame.setCursor(Qt.PointingHandCursor)
            track_frame.setAccessibleName(f"学习主线：{track.title}")
            track_frame.setAccessibleDescription(f"{track.title} - 点击进入学习")
            track_frame.setFocusPolicy(Qt.StrongFocus)
            track_frame.setStyleSheet(
                f"""
                QFrame {{
                    background: {BG_CARD_SOFT};
                    border: 1px solid {BORDER};
                    border-radius: 14px;
                }}
                QFrame:hover {{
                    background: {ACCENT_SOFT};
                    border: 1px solid rgba(37,99,235,0.25);
                }}
                """
            )
            track_layout = QVBoxLayout(track_frame)
            track_layout.setContentsMargins(22, 16, 22, 16)
            track_layout.setSpacing(8)

            title_row = QHBoxLayout()
            btn_label = QLabel(f"{track.icon}  {track.title}")
            btn_label.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 21px; font-weight: 600;")
            title_row.addWidget(btn_label)
            title_row.addStretch()

            track_pct = QLabel("0%")
            track_pct.setStyleSheet(f"color: {ACCENT}; font-weight: 700; font-size: 20px;")
            track_pct.setObjectName("track_pct_label")
            title_row.addWidget(track_pct)
            track_layout.addLayout(title_row)

            progress_bar = QProgressBar()
            progress_bar.setFixedHeight(8)
            progress_bar.setTextVisible(False)
            progress_bar.setValue(0)
            progress_bar.setObjectName("track_progress_bar")
            track_layout.addWidget(progress_bar)

            track_frame.mousePressEvent = lambda ev, tid=track.id: self.track_requested.emit(tid)
            track_frame.keyPressEvent = lambda ev, tid=track.id: (
                self.track_requested.emit(tid) if ev.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space) else None
            )
            layout.addWidget(track_frame)
            self.track_buttons.append(track_frame)
            self.track_progress_bars.append((track, progress_bar, track_pct))

        if not self.content_service.tracks:
            placeholder = QLabel(tr("dashboard.no_tracks"))
            placeholder.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px;")
            layout.addWidget(placeholder)

        return card

    # ── New chart sections ────────────────────────────────────────────────

    def _build_progress_line_chart_section(self) -> QFrame:
        """Learning progress line chart -- shows score trend over recent attempts."""
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("学习进度趋势")
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.line_chart_hint = QLabel("点击数据点查看详细信息")
        self.line_chart_hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px;")
        header.addWidget(self.line_chart_hint)
        layout.addLayout(header)

        self.progress_line_chart = LineChart(bar_color=ACCENT)
        self.progress_line_chart.setMinimumHeight(180)
        self.progress_line_chart.point_clicked.connect(self._on_line_point_clicked)
        self.progress_line_chart.setAccessibleName("学习进度折线图")
        layout.addWidget(self.progress_line_chart)

        return card

    def _build_skill_radar_section(self) -> QFrame:
        """Skill distribution radar chart -- shows proficiency per track."""
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("技能分布")
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.radar_hint = QLabel("点击轴线查看该方向详情")
        self.radar_hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px;")
        header.addWidget(self.radar_hint)
        layout.addLayout(header)

        self.skill_radar_chart = RadarChart(color=ACCENT)
        self.skill_radar_chart.setMinimumSize(260, 260)
        self.skill_radar_chart.axis_clicked.connect(self._on_radar_axis_clicked)
        self.skill_radar_chart.setAccessibleName("技能分布雷达图")
        layout.addWidget(self.skill_radar_chart, alignment=Qt.AlignHCenter)

        return card

    def _build_heatmap_section(self) -> QFrame:
        """Activity heatmap calendar -- GitHub-style contribution grid."""
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("学习活跃度")
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.heatmap_streak_label = QLabel("")
        self.heatmap_streak_label.setStyleSheet(f"color: {SUCCESS}; font-weight: 700; font-size: 18px;")
        header.addWidget(self.heatmap_streak_label)
        layout.addLayout(header)

        self.activity_heatmap = HeatmapCalendar(weeks=24)
        self.activity_heatmap.day_clicked.connect(self._on_heatmap_day_clicked)
        self.activity_heatmap.setAccessibleName("学习活跃度热力图")
        layout.addWidget(self.activity_heatmap)

        return card

    # ── Chart drill-down handlers ─────────────────────────────────────────

    def _on_line_point_clicked(self, index: int, value: float) -> None:
        """Handle click on a line chart data point -- show detail dialog."""
        try:
            attempts = self.db.recent_attempts(limit=30)
            if index < len(attempts):
                _at, title, score, passed, _dur = attempts[index]
                status = "通过" if passed else "未通过"
                msg = f"练习: {title}\n分数: {score}\n状态: {status}"
            else:
                msg = f"数据点 #{index + 1}: {value:.0f}"
        except Exception:
            logger.debug("获取练习详情失败 (index=%d)", index, exc_info=True)
            msg = f"数据点 #{index + 1}: {value:.0f}"
        self._show_info_dialog("练习详情", msg)

    def _on_radar_axis_clicked(self, index: int, value: float) -> None:
        """Handle click on a radar axis -- navigate to that track."""
        try:
            tracks = list(self.content_service.tracks)
            if index < len(tracks):
                self.track_requested.emit(tracks[index].id)
        except Exception as exc:
            logger.debug("雷达轴点击跳转失败: %s", exc)

    def _on_heatmap_day_clicked(self, iso_date: str, count: int) -> None:
        """Handle click on a heatmap cell -- show day detail dialog."""
        if count == 0:
            msg = f"{iso_date}\n当天没有学习记录"
        else:
            msg = f"{iso_date}\n完成了 {count} 项学习活动"
        self._show_info_dialog("每日详情", msg)

    def _show_info_dialog(self, title: str, message: str) -> None:
        """Show a simple info dialog with title and message."""
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QMessageBox, QShortcut

        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        box.setIcon(QMessageBox.Information)
        box.setAccessibleName(title)
        box.setAccessibleDescription(message)
        QShortcut(QKeySequence(Qt.Key_Escape), box, box.close)
        box.exec_()

    # ── Chart data computation helpers ────────────────────────────────────

    def _compute_radar_data(self) -> tuple[list[float], list[str]]:
        """Compute per-track average scores for the radar chart.

        Returns (values, labels) with values in [0, 100].
        """
        data: list[float] = []
        labels: list[str] = []
        for track in self.content_service.tracks:
            try:
                track_stats = self.db.get_analytics_track_stats()
                avg = track_stats.get(track.id, 0.0)
            except Exception:
                logger.debug("获取 track 统计数据失败 (track=%s)", track.id, exc_info=True)
                # Fallback: compute from lesson statuses
                completed = sum(1 for lesson in track.lessons if self.db.lesson_status(lesson.id) == "completed")
                avg = (completed / max(len(track.lessons), 1)) * 100
            data.append(min(avg, 100.0))
            # Use short track title for label
            label = track.title if len(track.title) <= 6 else track.title[:5] + ".."
            labels.append(label)
        # Ensure at least 3 axes for a visible polygon
        while len(data) < 3:
            data.append(0.0)
            labels.append("")
        return data, labels

    def _compute_heatmap_data(self) -> dict[str, int]:
        """Build ISO-date -> activity-count mapping for the last 24 weeks.

        Counts both lesson completions and practice attempts per day.
        """
        heatmap: dict[str, int] = {}
        today = date.today()
        start = today - timedelta(weeks=24)

        try:
            # Query lesson completions
            rows = self.db.fetchall(
                """
                SELECT substr(completed_at, 1, 10) AS day, COUNT(*) AS cnt
                FROM lesson_progress
                WHERE completed_at IS NOT NULL AND completed_at >= ?
                GROUP BY day
                """,
                (start.isoformat(),),
            )
            for day_str, cnt in rows:
                if day_str:
                    heatmap[day_str] = heatmap.get(day_str, 0) + int(cnt)

            # Query practice attempts
            rows = self.db.fetchall(
                """
                SELECT substr(submitted_at, 1, 10) AS day, COUNT(*) AS cnt
                FROM practice_attempts
                WHERE submitted_at IS NOT NULL AND submitted_at >= ?
                GROUP BY day
                """,
                (start.isoformat(),),
            )
            for day_str, cnt in rows:
                if day_str:
                    heatmap[day_str] = heatmap.get(day_str, 0) + int(cnt)
        except Exception as exc:
            logger.debug("计算热力图数据失败: %s", exc)

        return heatmap

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
            btn.setAccessibleName(label)
            btn.setAccessibleDescription(tr("dashboard.goal_tooltip", label=label, target=target))
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

    def _build_achievements_section(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("最近成就")
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.achievement_count = QLabel("")
        self.achievement_count.setStyleSheet(f"color: {ACCENT}; font-weight: 700; font-size: 20px;")
        header.addWidget(self.achievement_count)
        layout.addLayout(header)

        self.achievement_row = QHBoxLayout()
        self.achievement_row.setSpacing(12)
        self._achievement_badges = []
        layout.addLayout(self.achievement_row)

        # View all achievements button
        view_all_row = QHBoxLayout()
        view_all_row.addStretch()
        self.view_achievements_btn = QPushButton("查看全部成就")
        self.view_achievements_btn.setProperty("variant", "secondary")
        self.view_achievements_btn.setCursor(Qt.PointingHandCursor)
        self.view_achievements_btn.setToolTip("打开完整的成就殿堂")
        self.view_achievements_btn.setAccessibleName("查看全部成就")
        self.view_achievements_btn.setAccessibleDescription("打开成就殿堂对话框，查看所有已解锁和待解锁的成就")
        self.view_achievements_btn.clicked.connect(self._show_achievements_dialog)
        view_all_row.addWidget(self.view_achievements_btn)
        layout.addLayout(view_all_row)

        return card

    def _build_bookmarks_section(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("最近收藏")
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.bookmark_count_label = QLabel("")
        self.bookmark_count_label.setStyleSheet(f"color: {WARNING}; font-weight: 700; font-size: 20px;")
        header.addWidget(self.bookmark_count_label)
        layout.addLayout(header)

        self.bookmark_items_layout = QVBoxLayout()
        self.bookmark_items_layout.setSpacing(6)
        layout.addLayout(self.bookmark_items_layout)

        view_all_row = QHBoxLayout()
        view_all_row.addStretch()
        self.view_bookmarks_btn = QPushButton("查看全部收藏")
        self.view_bookmarks_btn.setProperty("variant", "secondary")
        self.view_bookmarks_btn.setCursor(Qt.PointingHandCursor)
        self.view_bookmarks_btn.setToolTip("打开收藏管理面板")
        self.view_bookmarks_btn.setAccessibleName("查看全部收藏")
        self.view_bookmarks_btn.setAccessibleDescription("打开收藏管理对话框，查看和管理所有已收藏的课程和练习")
        self.view_bookmarks_btn.clicked.connect(self._show_bookmarks_dialog)
        view_all_row.addWidget(self.view_bookmarks_btn)
        layout.addLayout(view_all_row)

        return card

    def _build_analytics_section(self) -> QFrame:
        card = self._card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel(tr("analytics.title"))
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.analytics_time_label = QLabel("0 " + tr("analytics.unit_min"))
        self.analytics_time_label.setStyleSheet(f"color: {ACCENT}; font-weight: 700; font-size: 20px;")
        header.addWidget(self.analytics_time_label)
        layout.addLayout(header)

        # Mini stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        for label_text, obj_name in [
            (tr("analytics.stat_lessons"), "analytics_mini_lessons"),
            (tr("analytics.stat_exercises"), "analytics_mini_exercises"),
            (tr("analytics.stat_avg_score"), "analytics_mini_score"),
        ]:
            mini = QLabel("0")
            mini.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: 600; font-size: 19px;")
            mini.setObjectName(obj_name)
            col = QVBoxLayout()
            col.setSpacing(2)
            col.addWidget(mini)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 15px;")
            col.addWidget(lbl)
            stats_row.addLayout(col)
        stats_row.addStretch()
        layout.addLayout(stats_row)

        # Open full analytics button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        view_btn = QPushButton(tr("analytics.title"))
        view_btn.setProperty("variant", "secondary")
        view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.setToolTip(tr("analytics.subtitle"))
        view_btn.clicked.connect(self._show_analytics_dialog)
        btn_row.addWidget(view_btn)
        layout.addLayout(btn_row)

        return card

    def _build_data_actions(self) -> QFrame:
        card = self._card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(14)

        export_btn = QPushButton("导出学习数据")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setToolTip("导出进度、笔记、书签和成就数据进行备份")
        export_btn.clicked.connect(self._open_export_dialog)
        layout.addWidget(export_btn)

        import_btn = QPushButton("导入学习数据")
        import_btn.setProperty("variant", "secondary")
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.setToolTip("从之前的备份文件中恢复学习数据")
        import_btn.clicked.connect(self._open_import_dialog)
        layout.addWidget(import_btn)

        layout.addStretch()
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

    # ── Dialog launchers ─────────────────────────────────────────────────────

    def _show_achievements_dialog(self) -> None:
        """Open a dialog showing all achievements."""
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QShortcut, QVBoxLayout

        from app.widgets.achievements import AchievementsWidget

        dialog = QDialog(self)
        dialog.setWindowTitle("成就殿堂")
        dialog.setMinimumSize(720, 520)
        dialog.setAccessibleName("成就殿堂对话框")
        QShortcut(QKeySequence(Qt.Key_Escape), dialog, dialog.close)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = AchievementsWidget(self.db, dialog)
        layout.addWidget(widget)
        dialog.exec_()

    def _show_analytics_dialog(self) -> None:
        """Open a dialog showing the full analytics view."""
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QShortcut, QVBoxLayout

        from app.widgets.analytics_view import AnalyticsViewWidget

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("analytics.title"))
        dialog.setMinimumSize(900, 650)
        dialog.setAccessibleName(tr("analytics.title"))
        QShortcut(QKeySequence(Qt.Key_Escape), dialog, dialog.close)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = AnalyticsViewWidget(self.db, dialog)
        widget.refresh()
        layout.addWidget(widget)
        dialog.exec_()

    def _show_bookmarks_dialog(self) -> None:
        """Open a dialog showing all bookmarks."""
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QShortcut, QVBoxLayout

        from app.widgets.bookmarks import BookmarksWidget

        dialog = QDialog(self)
        dialog.setWindowTitle("我的收藏")
        dialog.setMinimumSize(560, 440)
        dialog.setAccessibleName("收藏管理对话框")
        QShortcut(QKeySequence(Qt.Key_Escape), dialog, dialog.close)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = BookmarksWidget(self.db, dialog)
        layout.addWidget(widget)
        dialog.exec_()

    def _open_export_dialog(self) -> None:
        """Open the export/import dialog."""
        from app.widgets.export_import import ExportImportDialog

        dlg = ExportImportDialog(self.db, self)
        dlg.exec_()

    def _open_import_dialog(self) -> None:
        """Open the import dialog directly."""
        from app.widgets.export_import import ExportImportDialog

        dlg = ExportImportDialog(self.db, self)
        dlg.exec_()

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

        # Per-track progress bars
        if hasattr(self, "track_progress_bars"):
            for track, bar, pct_label in self.track_progress_bars:
                track_total = len(track.lessons)
                track_completed = sum(1 for lesson in track.lessons if self.db.lesson_status(lesson.id) == "completed")
                track_pct = int(track_completed / max(track_total, 1) * 100)
                bar.setValue(track_pct)
                pct_label.setText(f"{track_pct}%")
                bar.setStyleSheet(
                    f"QProgressBar::chunk {{ background: {SUCCESS if track_pct == 100 else ACCENT}; "
                    f"border-radius: 4px; }}"
                )

        # Weekly chart - compute activity per day of last 7 days
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

        # ── Progress line chart ───────────────────────────────────────────
        try:
            line_scores = [s for (_at, _t, s, _p, _d) in chart_attempts[:30]]
            line_scores.reverse()
            line_labels = [f"#{i + 1}" for i in range(len(line_scores))]
            self.progress_line_chart.set_data(line_scores, line_labels)
        except Exception as exc:
            logger.debug("刷新折线图失败: %s", exc)

        # ── Skill radar chart ─────────────────────────────────────────────
        try:
            radar_data, radar_labels = self._compute_radar_data()
            self.skill_radar_chart.set_data(radar_data, radar_labels)
        except Exception as exc:
            logger.debug("刷新雷达图失败: %s", exc)

        # ── Activity heatmap ──────────────────────────────────────────────
        try:
            heatmap_data = self._compute_heatmap_data()
            self.activity_heatmap.set_data(heatmap_data)
            # Update streak label next to heatmap title
            if hasattr(self, "heatmap_streak_label"):
                if streak > 0:
                    self.heatmap_streak_label.setText(f"连续 {streak} 天")
                else:
                    self.heatmap_streak_label.setText("")
        except Exception as exc:
            logger.debug("刷新热力图失败: %s", exc)

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

        # ── Analytics section ─────────────────────────────────────────────────
        try:
            self._refresh_analytics_preview()
        except Exception as exc:
            logger.warning("刷新分析预览失败: %s", exc)

        # ── Recommendations section ────────────────────────────────────────
        try:
            self._refresh_recommendations()
        except Exception as exc:
            logger.warning("刷新学习推荐失败: %s", exc)

        # ── Achievements section ─────────────────────────────────────────────
        try:
            self._refresh_achievements_section()
        except Exception as exc:
            logger.warning("刷新成就数据失败: %s", exc)

        # ── Bookmarks section ────────────────────────────────────────────────
        try:
            self._refresh_bookmarks_section()
        except Exception as exc:
            logger.warning("刷新收藏数据失败: %s", exc)

    def _refresh_analytics_preview(self) -> None:
        """刷新分析预览区域。"""
        from app.utils.analytics import AnalyticsCollector

        collector = AnalyticsCollector(self.db)
        weekly = collector.generate_weekly_report()
        if hasattr(self, "analytics_time_label"):
            from app.i18n import tr as _tr

            self.analytics_time_label.setText(f"{weekly['total_learning_time_min']} {_tr('analytics.unit_min')}")
        for obj_name, value in [
            ("analytics_mini_lessons", str(weekly["total_lessons_completed"])),
            ("analytics_mini_exercises", str(weekly["total_exercises_completed"])),
            ("analytics_mini_score", str(weekly["average_score"])),
        ]:
            lbl = self.findChild(QLabel, obj_name)
            if lbl:
                lbl.setText(value)

    def _refresh_achievements_section(self) -> None:
        """刷新成就区域。"""
        achievements = self.db.list_achievements()
        unlocked_count = sum(1 for a in achievements if a["unlocked"])
        total_achievements = len(achievements)
        self.achievement_count.setText(f"{unlocked_count}/{total_achievements}")

        while self.achievement_row.count():
            item = self.achievement_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._achievement_badges = []

        from app.widgets.achievements import AchievementBadge

        unlocked_achs = [a for a in achievements if a["unlocked"]][:3]
        locked_achs = [a for a in achievements if not a["unlocked"]]
        locked_achs.sort(key=lambda a: a.get("current_value", 0) / max(a.get("threshold", 1), 1), reverse=True)
        display_achs = unlocked_achs + locked_achs[: max(0, 4 - len(unlocked_achs))]
        for ach in display_achs[:4]:
            badge = AchievementBadge(ach)
            badge.setFixedSize(120, 140)
            self.achievement_row.addWidget(badge)
            self._achievement_badges.append(badge)
        if not display_achs:
            placeholder = QLabel("还没有成就记录，继续学习吧！")
            placeholder.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px;")
            self.achievement_row.addWidget(placeholder)

    def _refresh_bookmarks_section(self) -> None:
        """刷新收藏区域。"""
        bookmarks = self.db.list_bookmarks()
        bm_count = len(bookmarks)
        self.bookmark_count_label.setText(f"共 {bm_count} 个收藏")

        while self.bookmark_items_layout.count():
            item = self.bookmark_items_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for bm in bookmarks[:5]:
            _id, item_type, item_id, title, track_id, note, created_at = bm
            type_label = "课程" if item_type == "lesson" else "练习"
            type_color = ACCENT if item_type == "lesson" else "#8b5cf6"
            row = QHBoxLayout()
            row.setSpacing(8)
            badge = QLabel(type_label)
            badge.setFixedSize(36, 24)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                f"background: {ACCENT_SOFT if item_type == 'lesson' else '#f3e8ff'}; "
                f"color: {type_color}; border-radius: 6px; font-size: 13px; font-weight: 600;"
            )
            row.addWidget(badge)
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 17px; font-weight: 600;")
            row.addWidget(title_lbl, 1)
            self.bookmark_items_layout.addLayout(row)

        if not bookmarks:
            placeholder = QLabel("还没有收藏。在学习或练习时点击「收藏」按钮添加。")
            placeholder.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px;")
            placeholder.setWordWrap(True)
            self.bookmark_items_layout.addWidget(placeholder)
