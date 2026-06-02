from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QLabel, QWidget


def apply_shadow(widget: QWidget, blur: int = 28, offset_y: int = 8) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, offset_y)
    shadow.setColor(QColor(15, 23, 42, 26))
    widget.setGraphicsEffect(shadow)


def optimize_scroll_widget(widget: QWidget) -> None:
    widget.setAttribute(Qt.WA_OpaquePaintEvent, False)
    widget.setAttribute(Qt.WA_StaticContents, True)


def surface_panel(
    parent: QWidget = None, radius: int = 24, bg: str = "rgba(255,253,248,0.96)", border: str = "rgba(37,99,235,0.08)"
) -> QFrame:
    """Create a styled QFrame with rounded corners and card-like appearance.

    Eliminates duplicate _surface_panel() implementations across widgets.

    Args:
        parent: Optional parent widget.
        radius: Border radius in pixels.
        bg: Background style string.
        border: Border style string.

    Returns:
        A styled QFrame instance.
    """
    from PyQt5.QtWidgets import QFrame

    panel = QFrame(parent)
    panel.setStyleSheet(
        f"""
        QFrame {{
            background: {bg};
            border: 1px solid {border};
            border-radius: {radius}px;
        }}
        """
    )
    return panel


def fade_in(widget: QWidget, duration: int = 300) -> None:
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
    effect.setOpacity(0.0)

    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.InOutQuad)
    animation.start()
    widget._fade_animation = animation
    animation.finished.connect(lambda: setattr(widget, "_fade_animation", None))


# ── Loading Spinner ──────────────────────────────────────────────────────────


class LoadingSpinner(QWidget):
    """A lightweight animated spinner for loading states.

    The animation timer automatically stops when the widget is hidden
    and restarts when shown, reducing CPU usage for off-screen widgets.
    """

    def __init__(self, parent=None, size=32, color="#2563eb"):
        super().__init__(parent)
        self._angle = 0
        self._size = size
        self._color = QColor(color)
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(40)

    def _rotate(self) -> None:
        self._angle = (self._angle + 12) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(self._color, 3, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        margin = 4
        rect = self.rect().adjusted(margin, margin, -margin, -margin)
        painter.drawArc(rect, self._angle * 16, 270 * 16)
        painter.end()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start(40)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def start(self) -> None:
        self._timer.start(40)
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()


class AnimatedDotsLabel(QLabel):
    """A label that cycles through dots to indicate ongoing work.

    The animation timer automatically stops when the widget is hidden
    and restarts when shown, reducing CPU usage for off-screen widgets.
    """

    def __init__(self, base_text="AI 正在思考", parent=None):
        super().__init__(parent)
        self._base = base_text
        self._count = 0
        self.setText(base_text)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)

    def _tick(self) -> None:
        self._count = (self._count + 1) % 4
        dots = "." * self._count if self._count else ""
        self.setText(f"{self._base}{dots}")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start(500)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    def start(self, base_text: str = None) -> None:
        if base_text:
            self._base = base_text
        self._count = 0
        self.setText(self._base)
        self._timer.start(500)
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()
