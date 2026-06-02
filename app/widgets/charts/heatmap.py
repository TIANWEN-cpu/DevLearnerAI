"""Activity heatmap calendar widget (GitHub-style contribution grid).

Displays a configurable number of recent weeks as coloured squares.
Higher activity = deeper colour.  Hovering shows the date and count;
clicking a day emits a signal for drill-down.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QToolTip, QWidget

logger = logging.getLogger(__name__)

_CELL_SIZE = 16
_CELL_GAP = 3
_LABEL_WIDTH = 32
_TOP_MARGIN = 22
_LEFT_MARGIN = 8

# Intensity palette (empty -> low -> medium -> high -> max)
_PALETTE = [
    "#ebedf0",  # 0
    "#9be9a8",  # 1
    "#40c463",  # 2
    "#30a14e",  # 3
    "#216e39",  # 4
]

_DAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"]


class HeatmapCalendar(QWidget):
    """GitHub-style activity heatmap.

    Parameters
    ----------
    weeks : int
        Number of weeks to display (columns). Default 24 (~6 months).
    data : dict[str, int]
        Mapping of ISO date strings ("YYYY-MM-DD") to activity counts.

    Signals
    -------
    day_clicked(str iso_date, int count)
        Emitted when the user clicks a calendar cell.
    """

    day_clicked = pyqtSignal(str, int)

    def __init__(
        self,
        weeks: int = 24,
        data: Optional[dict[str, int]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._weeks = weeks
        self._data: dict[str, int] = data or {}
        self._cell_rects: list[tuple[str, int, QRectF]] = []  # (iso_date, count, rect)
        self._hover_iso: Optional[str] = None
        self._compute_size()
        self.setMouseTracking(True)

    # ── Public API ────────────────────────────────────────────────────────

    def set_data(self, data: dict[str, int]) -> None:
        """Replace activity data (date -> count mapping)."""
        self._data = dict(data or {})
        self._compute_size()
        self.update()

    def set_weeks(self, weeks: int) -> None:
        self._weeks = max(4, weeks)
        self._compute_size()
        self.update()

    # ── Geometry ──────────────────────────────────────────────────────────

    def _compute_size(self) -> None:
        total_w = _LEFT_MARGIN + _LABEL_WIDTH + self._weeks * (_CELL_SIZE + _CELL_GAP) + 4
        total_h = _TOP_MARGIN + 7 * (_CELL_SIZE + _CELL_GAP) + 4
        self.setMinimumSize(total_w, total_h)
        self.setMaximumHeight(total_h + 10)

    def _compute_cell_rects(self) -> None:
        self._cell_rects = []
        today = date.today()
        # Align to the start of the week (Monday)
        start = today - timedelta(days=today.weekday() + (self._weeks - 1) * 7)

        for week in range(self._weeks):
            for day in range(7):
                d = start + timedelta(weeks=week, days=day)
                if d > today:
                    continue
                iso = d.isoformat()
                count = self._data.get(iso, 0)
                x = _LEFT_MARGIN + _LABEL_WIDTH + week * (_CELL_SIZE + _CELL_GAP)
                y = _TOP_MARGIN + day * (_CELL_SIZE + _CELL_GAP)
                rect = QRectF(x, y, _CELL_SIZE, _CELL_SIZE)
                self._cell_rects.append((iso, count, rect))

    def _color_for_count(self, count: int) -> QColor:
        if count <= 0:
            return QColor(_PALETTE[0])
        if count == 1:
            return QColor(_PALETTE[1])
        if count <= 3:
            return QColor(_PALETTE[2])
        if count <= 6:
            return QColor(_PALETTE[3])
        return QColor(_PALETTE[4])

    def _hit_test(self, pos) -> Optional[str]:
        for iso, _count, rect in self._cell_rects:
            if rect.contains(pos.x(), pos.y()):
                return iso
        return None

    # ── Events ────────────────────────────────────────────────────────────

    def mouseMoveEvent(self, event):
        iso = self._hit_test(event.pos())
        if iso != self._hover_iso:
            self._hover_iso = iso
            self.update()
        if iso is not None:
            count = self._data.get(iso, 0)
            QToolTip.showText(event.globalPos(), f"{iso}: {count} 次活动", self)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hover_iso is not None:
            self._hover_iso = None
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            iso = self._hit_test(event.pos())
            if iso is not None:
                count = self._data.get(iso, 0)
                self.day_clicked.emit(iso, count)
        super().mousePressEvent(event)

    # ── Painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        self._compute_cell_rects()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Day-of-week labels
        painter.setPen(QPen(QColor("#94a3b8")))
        font = QFont("Microsoft YaHei UI", 9)
        painter.setFont(font)
        for i, label in enumerate(_DAY_LABELS):
            y = _TOP_MARGIN + i * (_CELL_SIZE + _CELL_GAP) + _CELL_SIZE / 2 - 6
            painter.drawText(QRectF(_LEFT_MARGIN, y, _LABEL_WIDTH, 14), Qt.AlignRight | Qt.AlignVCenter, label)

        # Cells
        for iso, count, rect in self._cell_rects:
            color = self._color_for_count(count)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(rect, 3, 3)

            # Hover highlight
            if iso == self._hover_iso:
                painter.setPen(QPen(QColor("#2563eb"), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 3, 3)

        # Legend at bottom-right
        self._draw_legend(painter)

        painter.end()

    def _draw_legend(self, painter: QPainter):
        legend_x = self.width() - len(_PALETTE) * (_CELL_SIZE + _CELL_GAP) - 20
        legend_y = _TOP_MARGIN + 7 * (_CELL_SIZE + _CELL_GAP) + 2
        painter.setPen(QPen(QColor("#94a3b8")))
        font = QFont("Microsoft YaHei UI", 8)
        painter.setFont(font)
        painter.drawText(QRectF(legend_x - 30, legend_y, 28, _CELL_SIZE), Qt.AlignRight | Qt.AlignVCenter, "少")
        for i, c in enumerate(_PALETTE):
            x = legend_x + i * (_CELL_SIZE + _CELL_GAP)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(c)))
            painter.drawRoundedRect(QRectF(x, legend_y, _CELL_SIZE, _CELL_SIZE), 2, 2)
        painter.setPen(QPen(QColor("#94a3b8")))
        painter.drawText(
            QRectF(legend_x + len(_PALETTE) * (_CELL_SIZE + _CELL_GAP) + 2, legend_y, 24, _CELL_SIZE),
            Qt.AlignLeft | Qt.AlignVCenter,
            "多",
        )
