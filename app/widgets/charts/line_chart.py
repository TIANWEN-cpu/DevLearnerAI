"""Interactive line chart widget for learning progress visualization.

Renders data points as connected lines with area fill, hover tooltips,
and click-to-drill-down support.  Pure QPainter -- no external deps.
"""

import logging
from typing import Optional

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt5.QtWidgets import QToolTip, QWidget

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────────────────────

_DEFAULT_LINE_COLOR = "#2563eb"
_DEFAULT_FILL_COLOR = "rgba(37, 99, 235, 0.12)"
_DEFAULT_GRID_COLOR = "rgba(100, 120, 150, 0.12)"
_DEFAULT_POINT_COLOR = "#2563eb"
_DEFAULT_HOVER_COLOR = "#1d4ed8"
_MARGIN_LEFT = 48
_MARGIN_RIGHT = 20
_MARGIN_TOP = 20
_MARGIN_BOTTOM = 36
_POINT_RADIUS = 5
_HOVER_RADIUS = 7


class LineChart(QWidget):
    """Interactive line chart with area fill and drill-down click support.

    Signals
    -------
    point_clicked(int index, float value)
        Emitted when the user clicks a data point.  *index* is the
        zero-based position in the current data list.
    """

    point_clicked = pyqtSignal(int, float)

    def __init__(
        self,
        data: Optional[list[float]] = None,
        labels: Optional[list[str]] = None,
        line_color: str = _DEFAULT_LINE_COLOR,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._data: list[float] = data or []
        self._labels: list[str] = labels or []
        self._line_color = QColor(line_color)
        self._fill_color = QColor(_DEFAULT_FILL_COLOR)
        self._hover_index: int = -1
        self._points: list[QPointF] = []
        self.setMinimumHeight(160)
        self.setMinimumWidth(220)
        self.setMouseTracking(True)

    # ── Public API ────────────────────────────────────────────────────────

    def set_data(self, data: list[float], labels: Optional[list[str]] = None) -> None:
        """Replace chart data and trigger a repaint."""
        self._data = list(data or [])
        self._labels = list(labels or [])
        self._hover_index = -1
        self._compute_points()
        self.setAccessibleDescription(
            "折线图数据: " + ", ".join(f"{lbl}={val}" for lbl, val in zip(self._labels, self._data))
            if self._labels
            else ""
        )
        self.update()

    # ── Geometry helpers ───────────────────────────────────────────────────

    def _chart_rect(self) -> QRectF:
        return QRectF(
            _MARGIN_LEFT,
            _MARGIN_TOP,
            self.width() - _MARGIN_LEFT - _MARGIN_RIGHT,
            self.height() - _MARGIN_TOP - _MARGIN_BOTTOM,
        )

    def _compute_points(self) -> None:
        """Pre-compute screen coordinates for each data point."""
        self._points = []
        n = len(self._data)
        if n == 0:
            return
        rect = self._chart_rect()
        max_val = max(max(self._data), 1)
        # Add 10% headroom
        max_val *= 1.1
        for i, val in enumerate(self._data):
            x = rect.x() + (i / max(n - 1, 1)) * rect.width()
            y = rect.bottom() - (val / max_val) * rect.height()
            self._points.append(QPointF(x, y))

    def _hit_test(self, pos: QPointF) -> int:
        """Return the index of the nearest point within hover range, or -1."""
        for i, pt in enumerate(self._points):
            if (pos - pt).manhattanLength() < _HOVER_RADIUS * 2.5:
                return i
        return -1

    # ── Events ────────────────────────────────────────────────────────────

    def mouseMoveEvent(self, event):
        idx = self._hit_test(event.pos())
        if idx != self._hover_index:
            self._hover_index = idx
            self.update()
        if 0 <= idx < len(self._data):
            label = self._labels[idx] if idx < len(self._labels) else f"#{idx}"
            QToolTip.showText(
                event.globalPos(),
                f"{label}: {self._data[idx]:.0f}",
                self,
            )
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hover_index != -1:
            self._hover_index = -1
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self._hit_test(event.pos())
            if 0 <= idx < len(self._data):
                self.point_clicked.emit(idx, self._data[idx])
        super().mousePressEvent(event)

    # ── Painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if not self._data:
            return

        self._compute_points()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self._chart_rect()

        # Grid lines
        self._draw_grid(painter, rect)

        # Area fill under the line
        self._draw_fill(painter, rect)

        # Line
        self._draw_line(painter)

        # Data points
        self._draw_points(painter)

        # Axis labels
        self._draw_labels(painter, rect)

        painter.end()

    def _draw_grid(self, painter: QPainter, rect: QRectF):
        painter.setPen(QPen(QColor(_DEFAULT_GRID_COLOR), 1, Qt.DashLine))
        n_guides = 4
        for i in range(n_guides + 1):
            y = rect.top() + (i / n_guides) * rect.height()
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def _draw_fill(self, painter: QPainter, rect: QRectF):
        n = len(self._points)
        if n < 2:
            return
        path = QPainterPath()
        path.moveTo(self._points[0].x(), rect.bottom())
        for pt in self._points:
            path.lineTo(pt)
        path.lineTo(self._points[-1].x(), rect.bottom())
        path.closeSubpath()

        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        fill = QColor(self._line_color)
        fill.setAlpha(35)
        gradient.setColorAt(0, fill)
        fill2 = QColor(self._line_color)
        fill2.setAlpha(5)
        gradient.setColorAt(1, fill2)
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

    def _draw_line(self, painter: QPainter):
        n = len(self._points)
        if n < 2:
            return
        pen = QPen(self._line_color, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        for i in range(n - 1):
            painter.drawLine(self._points[i], self._points[i + 1])

    def _draw_points(self, painter: QPainter):
        for i, pt in enumerate(self._points):
            if i == self._hover_index:
                painter.setBrush(QBrush(QColor(_DEFAULT_HOVER_COLOR)))
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.drawEllipse(pt, _HOVER_RADIUS, _HOVER_RADIUS)
            else:
                painter.setBrush(QBrush(QColor(_DEFAULT_POINT_COLOR)))
                painter.setPen(QPen(QColor("#ffffff"), 1.5))
                painter.drawEllipse(pt, _POINT_RADIUS, _POINT_RADIUS)

    def _draw_labels(self, painter: QPainter, rect: QRectF):
        n = len(self._labels)
        if n == 0:
            return
        painter.setPen(QPen(QColor("#94a3b8")))
        # Show every Nth label to avoid crowding
        step = max(1, n // 8)
        for i in range(0, n, step):
            if i >= len(self._points):
                break
            pt = self._points[i]
            label = self._labels[i]
            painter.drawText(
                QRectF(pt.x() - 20, rect.bottom() + 4, 40, 20),
                Qt.AlignHCenter | Qt.AlignTop,
                label,
            )
