"""分析仪表板 Widget -- 学习行为可视化与报告。

提供学习时间追踪、课程完成趋势、练习表现、连续学习和技能雷达图。
所有数据从本地数据库聚合，不依赖外部服务。

功能：
- 学习时间追踪（每日分钟数柱状图）
- 课程完成趋势（折线图）
- 练习表现趋势（分数柱状图）
- 连续学习天数追踪
- 技能雷达图（各 track 综合评分）
- 周报/月报生成与展示
"""

from __future__ import annotations

import logging
import math
from datetime import date
from typing import Optional

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.database import AppDatabase
from app.effects import apply_shadow
from app.i18n import tr
from app.styles import (
    ACCENT,
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
)

logger = logging.getLogger(__name__)


# ── 技能雷达图 Widget ─────────────────────────────────────────────────────────


class SkillRadarChart(QWidget):
    """多边形雷达图，展示各 track 的综合技能评分。"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._labels: list[str] = []
        self._values: list[float] = []
        self.setMinimumSize(280, 280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAccessibleName(tr("analytics.radar_name"))
        self.setAccessibleDescription(tr("analytics.radar_desc"))

    def set_data(self, labels: list[str], values: list[float]) -> None:
        self._labels = labels
        self._values = values
        self.setAccessibleDescription(
            tr("analytics.radar_desc") + ": " + ", ".join(f"{lbl} {v}%" for lbl, v in zip(labels, values))
        )
        self.update()

    def paintEvent(self, event):  # noqa: N802
        if not self._labels or not self._values:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx, cy = w / 2, h / 2
        radius = min(cx, cy) - 40
        n = len(self._labels)

        if n < 3:
            painter.end()
            return

        angle_step = 2 * math.pi / n

        # Background grid (3 levels)
        for level in (0.33, 0.66, 1.0):
            r = radius * level
            points = []
            for i in range(n):
                angle = -math.pi / 2 + i * angle_step
                points.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
            polygon = QPolygonF(points)
            painter.setPen(QPen(QColor(BORDER), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(polygon)

        # Axis lines
        painter.setPen(QPen(QColor(BORDER), 1))
        for i in range(n):
            angle = -math.pi / 2 + i * angle_step
            painter.drawLine(QPointF(cx, cy), QPointF(cx + radius * math.cos(angle), cy + radius * math.sin(angle)))

        # Data polygon
        data_points = []
        for i, val in enumerate(self._values):
            r = radius * min(val / 100.0, 1.0)
            angle = -math.pi / 2 + i * angle_step
            data_points.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))

        data_polygon = QPolygonF(data_points)
        fill_color = QColor(ACCENT)
        fill_color.setAlpha(50)
        painter.setBrush(QBrush(fill_color))
        painter.setPen(QPen(QColor(ACCENT), 2))
        painter.drawPolygon(data_polygon)

        # Data points and labels
        font = QFont(FONT, 13)
        painter.setFont(font)
        for i, (label, val) in enumerate(zip(self._labels, self._values)):
            angle = -math.pi / 2 + i * angle_step
            # Dot
            dx = cx + radius * min(val / 100.0, 1.0) * math.cos(angle)
            dy = cy + radius * min(val / 100.0, 1.0) * math.sin(angle)
            painter.setBrush(QBrush(QColor(ACCENT)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(dx, dy), 5, 5)

            # Label
            lx = cx + (radius + 24) * math.cos(angle)
            ly = cy + (radius + 24) * math.sin(angle)
            painter.setPen(QPen(QColor(TEXT_SUB)))
            text_rect = QRectF(lx - 50, ly - 10, 100, 20)
            painter.drawText(text_rect, Qt.AlignCenter, f"{label}\n{val:.0f}%")

        painter.end()


# ── 简易折线图 Widget ─────────────────────────────────────────────────────────


class MiniLineChart(QWidget):
    """简单的折线图，用于趋势展示。"""

    def __init__(self, line_color: str = ACCENT, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._data: list[float] = []
        self._labels: list[str] = []
        self._line_color = QColor(line_color)
        self._fill_color = QColor(line_color)
        self._fill_color.setAlpha(30)
        self.setMinimumHeight(160)
        self.setMinimumWidth(200)

    def set_data(self, data: list[float], labels: Optional[list[str]] = None) -> None:
        self._data = data or []
        self._labels = labels or []
        self.update()

    def paintEvent(self, event):  # noqa: N802
        if not self._data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._data)
        if n < 2:
            painter.end()
            return

        margin_left = 40
        margin_right = 16
        margin_top = 16
        margin_bottom = 28
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom
        max_val = max(max(self._data), 1)

        # Grid lines
        painter.setPen(QPen(QColor(BORDER), 1, Qt.DashLine))
        for i in range(5):
            y = margin_top + chart_h * i / 4
            painter.drawLine(int(margin_left), int(y), int(w - margin_right), int(y))

        # Data points
        points: list[QPointF] = []
        for i, val in enumerate(self._data):
            x = margin_left + (chart_w * i / max(n - 1, 1))
            y = margin_top + chart_h * (1 - val / max_val)
            points.append(QPointF(x, y))

        # Fill area
        fill_polygon = QPolygonF(points)
        bottom_right = QPointF(points[-1].x(), margin_top + chart_h)
        bottom_left = QPointF(points[0].x(), margin_top + chart_h)
        fill_polygon.append(bottom_right)
        fill_polygon.append(bottom_left)
        painter.setBrush(QBrush(self._fill_color))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(fill_polygon)

        # Line
        painter.setPen(QPen(self._line_color, 2.5))
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        # Dots
        painter.setBrush(QBrush(self._line_color))
        painter.setPen(Qt.NoPen)
        for p in points:
            painter.drawEllipse(p, 4, 4)

        # Labels (show every Nth)
        if self._labels:
            step = max(1, n // 7)
            painter.setPen(QPen(QColor(TEXT_MUTED)))
            font = QFont(FONT, 11)
            painter.setFont(font)
            for i in range(0, n, step):
                if i < len(self._labels):
                    x = margin_left + (chart_w * i / max(n - 1, 1))
                    painter.drawText(int(x - 15), h - 4, self._labels[i])

        painter.end()


# ── 学习时间柱状图 Widget ─────────────────────────────────────────────────────


class TimeBarChart(QWidget):
    """每日学习时间柱状图（分钟）。"""

    def __init__(self, bar_color: str = ACCENT, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._data: list[float] = []  # minutes per day
        self._labels: list[str] = []
        self._bar_color = QColor(bar_color)
        self.setMinimumHeight(160)
        self.setMinimumWidth(200)

    def set_data(self, data: list[float], labels: Optional[list[str]] = None) -> None:
        self._data = data or []
        self._labels = labels or []
        self.update()

    def paintEvent(self, event):  # noqa: N802
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
        margin_left = 40
        margin_right = 16
        margin_top = 16
        margin_bottom = 28
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        # Grid
        painter.setPen(QPen(QColor(BORDER), 1, Qt.DashLine))
        for i in range(5):
            y = margin_top + chart_h * i / 4
            painter.drawLine(int(margin_left), int(y), int(w - margin_right), int(y))

        # Bars
        bar_gap = max(2, chart_w / (n * 2.5))
        bar_w = max(4, (chart_w - bar_gap * n) / n)
        for i, val in enumerate(self._data):
            x = margin_left + i * (bar_w + bar_gap)
            bar_h = chart_h * val / max_val if max_val > 0 else 0
            y = margin_top + chart_h - bar_h

            color = self._bar_color
            color.setAlpha(200 if val > 0 else 60)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(bar_h), 3, 3)

        # Labels
        if self._labels:
            step = max(1, n // 10)
            painter.setPen(QPen(QColor(TEXT_MUTED)))
            font = QFont(FONT, 11)
            painter.setFont(font)
            for i in range(0, n, step):
                if i < len(self._labels):
                    x = margin_left + i * (bar_w + bar_gap)
                    painter.drawText(int(x), h - 4, self._labels[i])

        painter.end()


# ── 统计卡片 ──────────────────────────────────────────────────────────────────


def _stat_card(title: str, value: str, color: str = ACCENT) -> QFrame:
    """创建一个统计数字卡片。"""
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: 16px;
        }}
        """
    )
    apply_shadow(card, blur=12, offset_y=2)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(4)

    val_label = QLabel(value)
    val_label.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
    val_label.setStyleSheet(f"color: {color};")
    val_label.setAlignment(Qt.AlignCenter)
    val_label.setObjectName("analytics_stat_value")
    layout.addWidget(val_label)

    title_label = QLabel(title)
    title_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 16px;")
    title_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(title_label)
    return card


def _update_stat_card(card: QFrame, value: str) -> None:
    """更新统计卡片的值。"""
    label = card.findChild(QLabel, "analytics_stat_value")
    if label:
        label.setText(value)


# ── 报告生成对话框 ────────────────────────────────────────────────────────────


class ReportWidget(QWidget):
    """周报/月报展示组件。"""

    def __init__(self, db: AppDatabase, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._db = db
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # Period selector
        selector_row = QHBoxLayout()
        selector_row.setSpacing(10)
        self.period_combo = QComboBox()
        self.period_combo.addItems([tr("analytics.report_weekly"), tr("analytics.report_monthly")])
        self.period_combo.currentIndexChanged.connect(self._refresh_report)
        selector_row.addWidget(QLabel(tr("analytics.report_period")))
        selector_row.addWidget(self.period_combo)
        selector_row.addStretch()
        layout.addLayout(selector_row)

        # Report content area
        self.report_scroll = QScrollArea()
        self.report_scroll.setWidgetResizable(True)
        self.report_scroll.setFrameShape(QFrame.NoFrame)
        self.report_content = QWidget()
        self.report_layout = QVBoxLayout(self.report_content)
        self.report_layout.setContentsMargins(0, 0, 0, 0)
        self.report_layout.setSpacing(10)
        self.report_scroll.setWidget(self.report_content)
        layout.addWidget(self.report_scroll, 1)

    def refresh(self) -> None:
        self._refresh_report()

    def _refresh_report(self) -> None:
        """生成并显示报告。"""
        # Clear old content
        while self.report_layout.count():
            item = self.report_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        is_weekly = self.period_combo.currentIndex() == 0
        try:
            from app.utils.analytics import AnalyticsCollector

            collector = AnalyticsCollector(self._db)
            if is_weekly:
                report = collector.generate_weekly_report()
                period_label = tr("analytics.report_weekly")
            else:
                report = collector.generate_monthly_report()
                period_label = tr("analytics.report_monthly")
        except Exception as exc:
            logger.warning("生成报告失败: %s", exc)
            err_label = QLabel(tr("analytics.report_error"))
            err_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px;")
            self.report_layout.addWidget(err_label)
            return

        # Title
        title = QLabel(f"{period_label} - {date.today().isoformat()}")
        title.setFont(QFont(FONT, F_TITLE - 20, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        self.report_layout.addWidget(title)

        # Summary stats
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        for label_text, value, color in [
            (tr("analytics.report_time"), f"{report['total_learning_time_min']} {tr('analytics.unit_min')}", ACCENT),
            (tr("analytics.report_lessons"), str(report["total_lessons_completed"]), SUCCESS),
            (tr("analytics.report_exercises"), str(report["total_exercises_completed"]), WARNING),
            (tr("analytics.report_avg_score"), str(report["average_score"]), "#8b5cf6"),
            (tr("analytics.report_active_days"), str(report["active_days"]), ACCENT),
        ]:
            card = _stat_card(label_text, value, color)
            stats_row.addWidget(card)
        self.report_layout.addLayout(stats_row)

        # Daily breakdown
        breakdown_key = "daily_breakdown" if "daily_breakdown" in report else "weekly_breakdown"
        breakdown = report.get(breakdown_key, [])
        if breakdown:
            section_title = QLabel(tr("analytics.report_breakdown"))
            section_title.setFont(QFont(FONT, F_TITLE - 28, QFont.Bold))
            section_title.setStyleSheet(f"color: {TEXT_MAIN}; margin-top: 10px;")
            self.report_layout.addWidget(section_title)

            for entry in breakdown:
                row = QFrame()
                row.setStyleSheet(f"background: {BG_CARD_SOFT}; border-radius: 10px; padding: 6px;")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(14, 8, 14, 8)

                date_lbl = QLabel(entry.get("date", entry.get("week_start", "")))
                date_lbl.setStyleSheet(f"color: {TEXT_SUB}; font-size: 14px; min-width: 100px;")
                row_layout.addWidget(date_lbl)

                if "lessons" in entry:
                    info = f"{tr('analytics.report_lessons')}: {entry['lessons']} | {tr('analytics.report_exercises')}: {entry['exercises']} | {tr('analytics.report_time')}: {entry['time_min']} {tr('analytics.unit_min')}"
                else:
                    info = f"{tr('analytics.report_lessons')}: {entry['lessons_completed']} | {tr('analytics.report_exercises')}: {entry['exercises_completed']} | {tr('analytics.report_time')}: {round(entry['learning_time_sec'] / 60)} {tr('analytics.unit_min')}"
                info_lbl = QLabel(info)
                info_lbl.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 14px;")
                row_layout.addWidget(info_lbl, 1)

                self.report_layout.addWidget(row)

        self.report_layout.addStretch()


# ── 主分析仪表板 Widget ───────────────────────────────────────────────────────


class AnalyticsViewWidget(QWidget):
    """学习分析仪表板。

    包含五个主要视图：
    1. 概览统计卡片
    2. 学习时间追踪
    3. 课程完成趋势
    4. 练习表现趋势
    5. 技能雷达图
    以及周报/月报生成功能。
    """

    def __init__(self, db: AppDatabase, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._db = db
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.setSpacing(20)

        # Header
        header = QLabel(tr("analytics.title"))
        header.setFont(QFont(FONT, F_TITLE - 8, QFont.Bold))
        header.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(header)

        subtitle = QLabel(tr("analytics.subtitle"))
        subtitle.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Stats row
        self.stats_row = QWidget()
        stats_layout = QHBoxLayout(self.stats_row)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(14)
        self.stat_time = _stat_card(tr("analytics.stat_time"), "0 " + tr("analytics.unit_min"), ACCENT)
        self.stat_lessons = _stat_card(tr("analytics.stat_lessons"), "0", SUCCESS)
        self.stat_exercises = _stat_card(tr("analytics.stat_exercises"), "0", WARNING)
        self.stat_streak = _stat_card(tr("analytics.stat_streak"), "0", "#8b5cf6")
        self.stat_avg_score = _stat_card(tr("analytics.stat_avg_score"), "0", ACCENT)
        stats_layout.addWidget(self.stat_time)
        stats_layout.addWidget(self.stat_lessons)
        stats_layout.addWidget(self.stat_exercises)
        stats_layout.addWidget(self.stat_streak)
        stats_layout.addWidget(self.stat_avg_score)
        layout.addWidget(self.stats_row)

        # Tabs for different views
        tabs = QTabWidget()

        # Tab 1: Trends
        trends_widget = QWidget()
        trends_layout = QVBoxLayout(trends_widget)
        trends_layout.setContentsMargins(12, 16, 12, 12)
        trends_layout.setSpacing(18)

        # Time range selector
        range_row = QHBoxLayout()
        range_row.setSpacing(10)
        self.range_combo = QComboBox()
        self.range_combo.addItems(
            [
                tr("analytics.range_7d"),
                tr("analytics.range_30d"),
                tr("analytics.range_90d"),
            ]
        )
        self.range_combo.currentIndexChanged.connect(self.refresh)
        range_row.addWidget(QLabel(tr("analytics.range_label")))
        range_row.addWidget(self.range_combo)
        range_row.addStretch()
        trends_layout.addLayout(range_row)

        # Learning time chart
        time_card = self._card()
        time_layout = QVBoxLayout(time_card)
        time_layout.setContentsMargins(20, 16, 20, 16)
        time_title = QLabel(tr("analytics.chart_time"))
        time_title.setFont(QFont(FONT, F_TITLE - 28, QFont.Bold))
        time_title.setStyleSheet(f"color: {TEXT_MAIN};")
        time_layout.addWidget(time_title)
        self.time_chart = TimeBarChart(bar_color=ACCENT)
        self.time_chart.setAccessibleName(tr("analytics.chart_time_name"))
        time_layout.addWidget(self.time_chart)
        trends_layout.addWidget(time_card)

        # Lessons trend chart
        lessons_card = self._card()
        lessons_layout = QVBoxLayout(lessons_card)
        lessons_layout.setContentsMargins(20, 16, 20, 16)
        lessons_title = QLabel(tr("analytics.chart_lessons"))
        lessons_title.setFont(QFont(FONT, F_TITLE - 28, QFont.Bold))
        lessons_title.setStyleSheet(f"color: {TEXT_MAIN};")
        lessons_layout.addWidget(lessons_title)
        self.lessons_chart = MiniLineChart(line_color=SUCCESS)
        self.lessons_chart.setAccessibleName(tr("analytics.chart_lessons_name"))
        lessons_layout.addWidget(self.lessons_chart)
        trends_layout.addWidget(lessons_card)

        # Exercise performance chart
        perf_card = self._card()
        perf_layout = QVBoxLayout(perf_card)
        perf_layout.setContentsMargins(20, 16, 20, 16)
        perf_title = QLabel(tr("analytics.chart_performance"))
        perf_title.setFont(QFont(FONT, F_TITLE - 28, QFont.Bold))
        perf_title.setStyleSheet(f"color: {TEXT_MAIN};")
        perf_layout.addWidget(perf_title)
        self.perf_chart = MiniLineChart(line_color=WARNING)
        self.perf_chart.setAccessibleName(tr("analytics.chart_performance_name"))
        perf_layout.addWidget(self.perf_chart)
        trends_layout.addWidget(perf_card)

        trends_layout.addStretch()
        tabs.addTab(trends_widget, tr("analytics.tab_trends"))

        # Tab 2: Skills Radar
        skills_widget = QWidget()
        skills_layout = QVBoxLayout(skills_widget)
        skills_layout.setContentsMargins(12, 16, 12, 12)
        skills_layout.setSpacing(14)

        skills_title = QLabel(tr("analytics.skills_title"))
        skills_title.setFont(QFont(FONT, F_TITLE - 20, QFont.Bold))
        skills_title.setStyleSheet(f"color: {TEXT_MAIN};")
        skills_layout.addWidget(skills_title)

        skills_sub = QLabel(tr("analytics.skills_subtitle"))
        skills_sub.setStyleSheet(f"color: {TEXT_SUB}; font-size: 16px;")
        skills_sub.setWordWrap(True)
        skills_layout.addWidget(skills_sub)

        radar_container = QWidget()
        radar_layout = QHBoxLayout(radar_container)
        radar_layout.setContentsMargins(0, 10, 0, 0)
        self.radar_chart = SkillRadarChart()
        radar_layout.addWidget(self.radar_chart, 1)
        skills_layout.addWidget(radar_container)

        skills_layout.addStretch()
        tabs.addTab(skills_widget, tr("analytics.tab_skills"))

        # Tab 3: Reports
        self.report_widget = ReportWidget(self._db)
        tabs.addTab(self.report_widget, tr("analytics.tab_reports"))

        layout.addWidget(tabs, 1)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _card(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            """
        )
        apply_shadow(frame, blur=14, offset_y=3)
        return frame

    def _get_days(self) -> int:
        idx = self.range_combo.currentIndex()
        return [7, 30, 90][idx]

    def refresh(self) -> None:
        """刷新所有分析数据。"""
        days = self._get_days()

        try:
            from app.utils.analytics import AnalyticsCollector

            collector = AnalyticsCollector(self._db)

            # Stats cards
            weekly = collector.generate_weekly_report()
            _update_stat_card(self.stat_time, f"{weekly['total_learning_time_min']} {tr('analytics.unit_min')}")
            _update_stat_card(self.stat_lessons, str(weekly["total_lessons_completed"]))
            _update_stat_card(self.stat_exercises, str(weekly["total_exercises_completed"]))
            _update_stat_card(self.stat_avg_score, str(weekly["average_score"]))

            streak = self._db.active_days_streak()
            _update_stat_card(self.stat_streak, str(streak))

            # Learning time chart
            time_data = collector.get_learning_time_by_day(days)
            time_values = [round(r["learning_time_sec"] / 60, 1) for r in time_data]
            time_labels = [r["date"][5:] for r in time_data]  # MM-DD format
            self.time_chart.set_data(time_values, time_labels)

            # Lessons trend
            lessons_data = collector.get_lessons_trend(days)
            lessons_values = [float(r["count"]) for r in lessons_data]
            lessons_labels = [r["date"][5:] for r in lessons_data]
            self.lessons_chart.set_data(lessons_values, lessons_labels)

            # Exercise performance
            perf_data = collector.get_exercise_performance(days)
            perf_values = [float(r["avg_score"]) for r in perf_data]
            perf_labels = [r["date"][5:] for r in perf_data]
            self.perf_chart.set_data(perf_values, perf_labels)

            # Skills radar
            skill_dist = collector.get_skill_distribution()
            if skill_dist:
                # Truncate long track names
                labels = [k[:8] if len(k) > 8 else k for k in skill_dist]
                values = list(skill_dist.values())
                self.radar_chart.set_data(labels, values)

            # Report tab
            self.report_widget.refresh()

        except Exception as exc:
            logger.error("刷新分析数据失败: %s", exc, exc_info=True)
