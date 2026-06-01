from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QWidget


def apply_shadow(widget: QWidget, blur: int = 28, offset_y: int = 8) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, offset_y)
    shadow.setColor(QColor(15, 23, 42, 26))
    widget.setGraphicsEffect(shadow)


def optimize_scroll_widget(widget: QWidget) -> None:
    widget.setAttribute(Qt.WA_OpaquePaintEvent, False)
    widget.setAttribute(Qt.WA_StaticContents, True)


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
    animation.finished.connect(lambda: setattr(widget, '_fade_animation', None))
