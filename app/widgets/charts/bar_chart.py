"""Enhanced interactive bar chart widget with drill-down support.

Supports vertical bars with hover highlighting, value labels, category
labels, and click-to-drill-down.  Pure QPainter rendering.
"""

import logging
from typing import Optional

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QToolTip, QWidget

logger = logging.getLogger(__name__)

_DEFAULT_BAR_COLOR = "#2563eb"
_DEFAULT_HOVER_COLOR = "#1d4ed8"
_GRID_COLOR = "rgba(100, 120, 150, 0.12)"
_MARGIN = 12
_LABEL_HEIGHT = 22
_VALUE_HEIGHT = 18


class BarChart(QWidget):
    """Interactive vertical bar chart with click-to-drill-down.

    Signals
    -------
    bar_clicked(int index, float value)
        Emitted when a bar is clicked.
    """

    bar_clicked = pyqtSignal(int, float)

    def __init__(
        self,
        data: Optional[list[float]] = None,
        labels: Optional[list[str]] = None,
        bar_color: str = _DEFAULT_BAR_COLOR,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._data: list[float] = data or []
        self._labels: list[str] = labels or []
        self._bar_color = QColor(bar_color)
        self._hover_index: int = -1
        self._bar_rects: list[tuple[int, QRectF]] = []
        self.setMinimumHeight(140)
        self.setMinimumWidth(180)
        self.setMouseTracking(True)

    # ── Public API ────────────────────────────────────────────────────────

    def set_data(self, data: list[float], labels: Optional[list[str]] = None) -> None:
        self._data = list(data or [])
        self._labels = list(labels or [])
        self._hover_index = -1
        self._compute_bar_rects()
        if self._data and self._labels:
            parts = [f"{lbl}: {val:.0f}" for lbl, val in zip(self._labels, self._data)]
            self.setAccessibleDescription("柱状图: " + ", ".join(parts))
        self.update()

    # ── Geometry ──────────────────────────────────────────────────────────

    def _chart_rect(self) -> QRectF:
        return QRectF(
            _MARGIN,
            _MARGIN + _VALUE_HEIGHT,
            self.width() - _MARGIN * 2,
            self.height() - _MARGIN * 2 - _LABEL_HEIGHT - _VALUE_HEIGHT,
        )

    def _compute_bar_rects(self) -> None:
        self._bar_rects = []
        n = len(self._data)
        if n == 0:
            return
        rect = self._chart_rect()
        max_val = max(max(self._data), 1) * 1.1
        gap = max(4, rect.width() * 0.05)
        bar_w = max(8, (rect.width() - gap * (n + 1)) / n)

        for i, val in enumerate(self._data):
            x = rect.x() + gap + i * (bar_w + gap)
            bar_h = (val / max_val) * rect.height() if max_val > 0 else 0
            y = rect.bottom() - bar_h
            self._bar_rects.append((i, QRectF(x, y, bar_w, bar_h)))

    def _hit_test(self, pos) -> int:
        for i, r in self._bar_rects:
            # Expand hit area slightly
            expanded = r.adjusted(-4, -4, 4, 4)
            if expanded.contains(pos.x(), pos.y()):
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
                self.bar_clicked.emit(idx, self._data[idx])
        super().mousePressEvent(event)

    # ── Painting ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if not self._data:
            return

        self._compute_bar_rects()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self._chart_rect()

        # Grid
        painter.setPen(QPen(QColor(_GRID_COLOR), 1, Qt.DashLine))
        for i in range(5):
            y = rect.top() + (i / 4) * rect.height()
            painter.drawLine(rect.left(), y, rect.right(), y)

        # Bars
        for i, bar_rect in self._bar_rects:
            color = QColor(_DEFAULT_HOVER_COLOR if i == self._hover_index else self._bar_color)
            color.setAlpha(230 if i == self._hover_index else 200)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bar_rect, 4, 4)

        # Value labels above bars
        painter.setPen(QPen(QColor("#4f6180")))
        font = QFont("Microsoft YaHei UI", 10)
        painter.setFont(font)
        for i, bar_rect in self._bar_rects:
            if i < len(self._data) and self._data[i] > 0:
                label_rect = QRectF(
                    bar_rect.x() - 10, bar_rect.top() - _VALUE_HEIGHT, bar_rect.width() + 20, _VALUE_HEIGHT
                )
                painter.drawText(label_rect, Qt.AlignHCenter | Qt.AlignVCenter, f"{self._data[i]:.0f}")

        # Category labels
        painter.setPen(QPen(QColor("#94a3b8")))
        for i, bar_rect in self._bar_rects:
            if i < len(self._labels):
                label_rect = QRectF(bar_rect.x() - 10, rect.bottom() + 2, bar_rect.width() + 20, _LABEL_HEIGHT)
                painter.drawText(label_rect, Qt.AlignHCenter | Qt.AlignTop, self._labels[i])

        painter.end()
