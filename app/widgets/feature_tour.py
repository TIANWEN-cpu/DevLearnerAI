"""Feature tour overlay for guided walkthrough of main UI areas.

Provides a semi-transparent overlay that highlights specific widgets
and displays tooltip descriptions to guide new users through the
application's main features.
"""

import logging

from PyQt5.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr
from app.styles import (
    ACCENT,
    BG_CARD,
    BORDER,
    FONT,
    TEXT_MAIN,
    TEXT_SUB,
)

logger = logging.getLogger(__name__)


class FeatureTourOverlay(QWidget):
    """Full-screen semi-transparent overlay that highlights target widgets.

    Draws a darkened background with a cut-out region around the target
    widget, and displays a tooltip card with title and description.

    Signals:
        tour_finished: Emitted when the tour ends (all steps done or skipped).
    """

    tour_finished = pyqtSignal()

    # Tour steps: (target_property_name, title, description)
    STEPS = [
        {
            "target": "sidebar",
            "title": tr("tour.sidebar_title"),
            "desc": tr("tour.sidebar_desc"),
        },
        {
            "target": "dashboard",
            "title": tr("tour.dashboard_title"),
            "desc": tr("tour.dashboard_desc"),
        },
        {
            "target": "learn",
            "title": tr("tour.learn_title"),
            "desc": tr("tour.learn_desc"),
        },
        {
            "target": "practice",
            "title": tr("tour.practice_title"),
            "desc": tr("tour.practice_desc"),
        },
        {
            "target": "ai_mentor",
            "title": tr("tour.ai_title"),
            "desc": tr("tour.ai_desc"),
        },
    ]

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self._main_window = main_window
        self._current_step = 0
        self._target_rect = QRect()
        self._tooltip_widget = None

        # Overlay setup
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._build_tooltip()
        self.hide()

    def _build_tooltip(self) -> None:
        """Build the floating tooltip card."""
        self._tooltip_widget = QWidget(self)
        self._tooltip_widget.setStyleSheet(
            f"""
            QWidget {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
            """
        )
        self._tooltip_widget.setFixedWidth(360)

        layout = QVBoxLayout(self._tooltip_widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Step counter
        self._step_label = QLabel()
        self._step_label.setStyleSheet(f"color: {ACCENT}; font-size: 15px; font-weight: 600;")
        layout.addWidget(self._step_label)

        # Title
        self._title_label = QLabel()
        self._title_label.setFont(QFont(FONT, 20, QFont.Bold))
        self._title_label.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(self._title_label)

        # Description
        self._desc_label = QLabel()
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 17px;")
        layout.addWidget(self._desc_label)

        # Navigation
        nav = QHBoxLayout()
        nav.setSpacing(10)

        self._skip_btn = QPushButton(tr("tour.skip"))
        self._skip_btn.setProperty("variant", "ghost")
        self._skip_btn.setCursor(Qt.PointingHandCursor)
        self._skip_btn.setToolTip(tr("tour.skip_tip"))
        self._skip_btn.clicked.connect(self._finish_tour)
        nav.addWidget(self._skip_btn)

        nav.addStretch()

        self._prev_btn = QPushButton(tr("tour.prev"))
        self._prev_btn.setProperty("variant", "secondary")
        self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.clicked.connect(self._prev_step)
        nav.addWidget(self._prev_btn)

        self._next_btn = QPushButton(tr("tour.next"))
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.setToolTip(tr("tour.next_tip"))
        self._next_btn.clicked.connect(self._next_step)
        nav.addWidget(self._next_btn)

        layout.addLayout(nav)

    # ── Public API ───────────────────────────────────────────────────────────

    def start_tour(self) -> None:
        """Start the feature tour from the first step."""
        self._current_step = 0
        self._show_step()
        self.show()
        self.raise_()

    # ── Step management ──────────────────────────────────────────────────────

    def _show_step(self) -> None:
        """Display the current tour step."""
        step = self.STEPS[self._current_step]
        target_name = step["target"]

        # Update tooltip content
        total = len(self.STEPS)
        self._step_label.setText(f"{self._current_step + 1} / {total}")
        self._title_label.setText(step["title"])
        self._desc_label.setText(step["desc"])

        # Update navigation buttons
        self._prev_btn.setVisible(self._current_step > 0)
        if self._current_step == total - 1:
            self._next_btn.setText(tr("tour.finish"))
            self._next_btn.setToolTip(tr("tour.finish_tip"))
        else:
            self._next_btn.setText("下一个")
            self._next_btn.setToolTip(tr("tour.next_tip"))

        # Find and highlight target widget
        target_widget = self._find_target(target_name)
        if target_widget:
            self._target_rect = self._compute_highlight_rect(target_widget)
        else:
            self._target_rect = QRect()

        # Position tooltip near target
        self._position_tooltip()

        self.update()

    def _find_target(self, name: str) -> QWidget:
        """Find the target widget by name from the main window."""
        target_map = {
            "sidebar": getattr(self._main_window, "sidebar", None),
            "dashboard": getattr(self._main_window, "dashboard", None),
            "learn": getattr(self._main_window, "learn", None),
            "practice": getattr(self._main_window, "practice", None),
            "ai_mentor": (getattr(self._main_window, "ai_dock", None) or getattr(self._main_window, "ai_page", None)),
        }
        return target_map.get(name)

    def _compute_highlight_rect(self, widget: QWidget) -> QRect:
        """Compute the global rect of the target widget with padding."""
        if widget is None or not widget.isVisible():
            return QRect()
        pos = widget.mapToGlobal(QPoint(0, 0))
        local_pos = self.mapFromGlobal(pos)
        pad = 8
        return QRect(
            local_pos.x() - pad,
            local_pos.y() - pad,
            widget.width() + pad * 2,
            widget.height() + pad * 2,
        )

    def _position_tooltip(self) -> None:
        """Position the tooltip to the right of the highlight, or left if no space."""
        tooltip_w = 360
        tooltip_h = self._tooltip_widget.sizeHint().height() or 200

        if self._target_rect.isValid():
            # Place to the right of the target
            x = self._target_rect.right() + 20
            y = self._target_rect.center().y() - tooltip_h // 2

            # If no space on the right, place to the left
            if x + tooltip_w > self.width():
                x = self._target_rect.left() - tooltip_w - 20

            # Clamp to visible area
            x = max(10, min(x, self.width() - tooltip_w - 10))
            y = max(10, min(y, self.height() - tooltip_h - 10))
        else:
            # Center if no target
            x = (self.width() - tooltip_w) // 2
            y = (self.height() - tooltip_h) // 2

        self._tooltip_widget.setGeometry(x, y, tooltip_w, tooltip_h)
        self._tooltip_widget.show()
        self._tooltip_widget.raise_()

    def _next_step(self) -> None:
        if self._current_step < len(self.STEPS) - 1:
            self._current_step += 1
            self._show_step()
        else:
            self._finish_tour()

    def _prev_step(self) -> None:
        if self._current_step > 0:
            self._current_step -= 1
            self._show_step()

    def _finish_tour(self) -> None:
        self.hide()
        self.tour_finished.emit()
        logger.info("Feature tour finished at step %d", self._current_step + 1)

    # ── Painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """Draw semi-transparent overlay with cut-out for the target widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Semi-transparent dark overlay
        overlay_color = QColor(0, 0, 0, 140)
        painter.setBrush(QBrush(overlay_color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        # Cut-out for highlighted target
        if self._target_rect.isValid():
            # Clear the highlight region
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.drawRoundedRect(self._target_rect, 12, 12)

            # Draw highlight border
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            highlight_pen = QPen(QColor(ACCENT))
            highlight_pen.setWidth(3)
            painter.setPen(highlight_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self._target_rect, 12, 12)

        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._tooltip_widget and self._tooltip_widget.isVisible():
            self._position_tooltip()

    def mousePressEvent(self, event):
        """Clicking outside the tooltip advances the tour."""
        if self._tooltip_widget and self._tooltip_widget.isVisible():
            tooltip_rect = self._tooltip_widget.geometry()
            if not tooltip_rect.contains(event.pos()):
                self._next_step()


def start_feature_tour(main_window) -> FeatureTourOverlay:
    """Convenience function to start a feature tour on the given main window.

    Returns the overlay widget so the caller can keep a reference.
    """
    overlay = FeatureTourOverlay(main_window)
    overlay.resize(main_window.size())
    overlay.start_tour()
    return overlay
