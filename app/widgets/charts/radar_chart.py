"""Interactive radar (spider) chart for skill distribution visualization.

Draws a polygon overlay on concentric guide rings.  Each axis represents
one skill dimension.  Hover highlights the nearest axis and displays its
value; clicking emits a signal for drill-down.
"""

import logging
import math
from typing import Optional

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QToolTip, QWidget

logger = logging.getLogger(__name__)

_FILL_ALPHA = 40
_LINE_ALPHA = 180
_GUIDE_COLOR = "rgba(100, 120, 150, 0.18)"
_AXIS_LABEL_COLOR = "#4f6180"
_MAX_VALUE = 100  # normalised max


class RadarChart(QWidget):
    """Interactive radar / spider chart.

    Parameters
    ----------
    data : list[float]
        Values in [0, 100] for each axis.
    labels : list[str]
        Axis labels (same length as *data*).
    color : str
        CSS colour for the data polygon.

    Signals
    -------
    axis_clicked(int index, float value)
        Emitted when the user clicks near an axis data point.
    """

    axis_clicked = pyqtSignal(int, float)

    def __init__(
        self,
        data: Optional[list[float]] = None,
        labels: Optional[list[str]] = None,
        color: str = "#2563eb",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._data: list[float] = data or []
        self._labels: list[str] = labels or []
        self._color = QColor(color)
        self._hover_index: int = -1
        self._vertex_points: list[QPointF] = []
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)

    # ── Public API ────────────────────────────────────────────────────────

    def set_data(self, data: list[float], labels: Optional[list[str]] = None) -> None:
        self._data = list(data or [])
        self._labels = list(labels or [])
        self._hover_index = -1
        self._compute_vertices()
        self.update()

    # ── Geometry ──────────────────────────────────────────────────────────

    def _center(self) -> QPointF:
        return QPointF(self.width() / 2, self.height() / 2)

    def _radius(self) -> float:
        return min(self.width(), self.height()) / 2 - 36

    def _angle_for(self, i: int) -> float:
        """Angle in radians for axis *i* (starting at top, going CW)."""
        n = max(len(self._data), 3)
        return -math.pi / 2 + (2 * math.pi * i / n)

    def _point_on_axis(self, i: int, value: float) -> QPointF:
        """Return screen position for axis *i* at *value* in [0, 100]."""
        angle = self._angle_for(i)
        r = self._radius() * min(value / _MAX_VALUE, 1.0)
        c = self._center()
        return QPointF(c.x() + r * math.cos(angle), c.y() + r * math.sin(angle))

    def _compute_vertices(self) -> None:
        self._vertex_points = [self._point_on_axis(i, v) for i, v in enumerate(self._data)]

    def _hit_test(self, pos: QPointF) -> int:
        for i, pt in enumerate(self._vertex_points):
            if (pos - pt).manhattanLength() < 18:
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
            QToolTip.showText(event.globalPos(), f"{label}: {self._data[idx]:.0f}", self)
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
                self.axis_clicked.emit(idx, self._data[idx])
        super().mousePressEvent(event)

    # ── Painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if not self._data:
            return
        self._compute_vertices()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self._draw_guides(painter)
        self._draw_axes(painter)
        self._draw_data_polygon(painter)
        self._draw_vertices(painter)
        self._draw_labels(painter)

        painter.end()

    def _draw_guides(self, painter: QPainter):
        """Draw concentric pentagon / polygon guides."""
        n = len(self._data)
        painter.setPen(QPen(QColor(_GUIDE_COLOR), 1))
        painter.setBrush(Qt.NoBrush)
        for ring in range(1, 5):
            r = self._radius() * ring / 4
            points = []
            for i in range(n):
                angle = self._angle_for(i)
                c = self._center()
                points.append(QPointF(c.x() + r * math.cos(angle), c.y() + r * math.sin(angle)))
            poly = QPolygonF(points + [points[0]])
            painter.drawPolygon(poly)

    def _draw_axes(self, painter: QPainter):
        """Draw axis lines from center to outer ring."""
        painter.setPen(QPen(QColor(_GUIDE_COLOR), 1))
        c = self._center()
        for i in range(len(self._data)):
            outer = self._point_on_axis(i, _MAX_VALUE)
            painter.drawLine(c, outer)

    def _draw_data_polygon(self, painter: QPainter):
        n = len(self._vertex_points)
        if n < 3:
            return

        # Fill
        fill = QColor(self._color)
        fill.setAlpha(_FILL_ALPHA)
        painter.setBrush(QBrush(fill))
        pen = QPen(self._color, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        pen.setColor(QColor(self._color.red(), self._color.green(), self._color.blue(), _LINE_ALPHA))
        painter.setPen(pen)
        poly = QPolygonF(self._vertex_points + [self._vertex_points[0]])
        painter.drawPolygon(poly)

    def _draw_vertices(self, painter: QPainter):
        for i, pt in enumerate(self._vertex_points):
            if i == self._hover_index:
                painter.setBrush(QBrush(QColor("#1d4ed8")))
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.drawEllipse(pt, 7, 7)
            else:
                painter.setBrush(QBrush(self._color))
                painter.setPen(QPen(QColor("#ffffff"), 1.5))
                painter.drawEllipse(pt, 5, 5)

    def _draw_labels(self, painter: QPainter):
        font = QFont("Microsoft YaHei UI", 10)
        painter.setFont(font)
        painter.setPen(QPen(QColor(_AXIS_LABEL_COLOR)))

        for i, label in enumerate(self._labels):
            if i >= len(self._data):
                break
            pt = self._point_on_axis(i, _MAX_VALUE * 1.18)
            angle_deg = math.degrees(self._angle_for(i))
            flags = Qt.AlignCenter
            # Adjust alignment based on position
            if angle_deg < -60 or angle_deg > 60:
                flags = Qt.AlignHCenter | Qt.AlignVCenter
            elif -60 <= angle_deg <= -30:
                flags = Qt.AlignRight | Qt.AlignVCenter
            elif 30 <= angle_deg <= 60:
                flags = Qt.AlignLeft | Qt.AlignVCenter

            text_rect = QRectF(pt.x() - 50, pt.y() - 10, 100, 20)
            painter.drawText(text_rect, flags, label)
