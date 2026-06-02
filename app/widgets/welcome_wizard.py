"""Welcome wizard for first-run experience.

Guides new users through initial setup in 5 steps:
  1. Welcome & app description
  2. AI API configuration
  3. Choose learning track
  4. Set learning goals
  5. Quick feature tour overview

Completion state is persisted in the database so the wizard
only shows once unless explicitly reset.
"""

import logging

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.content_service import ContentService
from app.database import AppDatabase
from app.i18n import tr
from app.styles import (
    ACCENT,
    ACCENT_SOFT,
    BG_CARD,
    BORDER,
    F_TITLE,
    FONT,
    SUCCESS,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUB,
)

logger = logging.getLogger(__name__)

# ── Step indicator widget ─────────────────────────────────────────────────────


class StepIndicator(QWidget):
    """Visual indicator showing current step and total steps."""

    def __init__(self, total: int = 5, parent=None):
        super().__init__(parent)
        self._total = total
        self._current = 0
        self.setFixedHeight(36)
        self.setAccessibleName("wizard_step_indicator")

    def set_step(self, current: int) -> None:
        self._current = current
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QBrush, QColor, QPainter, QPen

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        dot_r = 8
        gap = 36
        total_w = self._total * dot_r * 2 + (self._total - 1) * gap
        start_x = (w - total_w) // 2
        y = self.height() // 2

        for i in range(self._total):
            x = start_x + i * (dot_r * 2 + gap) + dot_r
            if i <= self._current:
                painter.setBrush(QBrush(QColor(ACCENT)))
            else:
                painter.setBrush(QBrush(QColor(BORDER)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x - dot_r, y - dot_r, dot_r * 2, dot_r * 2)

        # Connecting line
        if self._total > 1:
            line_start_x = start_x + dot_r
            line_end_x = start_x + (self._total - 1) * (dot_r * 2 + gap) + dot_r
            pen = QPen(QColor(BORDER))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(line_start_x, y, line_end_x, y)
            # Redraw dots on top
            for i in range(self._total):
                x = start_x + i * (dot_r * 2 + gap) + dot_r
                if i <= self._current:
                    painter.setBrush(QBrush(QColor(ACCENT)))
                else:
                    painter.setBrush(QBrush(QColor(BORDER)))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(x - dot_r, y - dot_r, dot_r * 2, dot_r * 2)

        painter.end()


# ── Welcome Wizard ────────────────────────────────────────────────────────────


class WelcomeWizard(QDialog):
    """Multi-step welcome wizard dialog for first-run setup.

    Signals:
        wizard_completed: Emitted when the user finishes all steps.
        track_selected(track_id): Emitted when user picks a track.
        goal_selected(target): Emitted when user picks a goal target.
    """

    wizard_completed = pyqtSignal()
    track_selected = pyqtSignal(str)
    goal_selected = pyqtSignal(int)

    _STEPS = 5

    def __init__(self, db: AppDatabase, content_service: ContentService, parent=None):
        super().__init__(parent)
        self.db = db
        self.content_service = content_service
        self._current_step = 0
        self._selected_track_id = ""
        self._goal_target = 1

        self.setWindowTitle(tr("wizard.title"))
        self.setMinimumSize(720, 560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._build_ui()
        self._goto_step(0)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(18)

        # Step indicator
        self._indicator = StepIndicator(self._STEPS)
        root.addWidget(self._indicator)

        # Content stack
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step_welcome())
        self._stack.addWidget(self._build_step_api_config())
        self._stack.addWidget(self._build_step_track())
        self._stack.addWidget(self._build_step_goals())
        self._stack.addWidget(self._build_step_tour())
        root.addWidget(self._stack, 1)

        # Navigation buttons
        nav = QHBoxLayout()
        nav.setSpacing(14)

        self._skip_btn = QPushButton(tr("wizard.skip"))
        self._skip_btn.setProperty("variant", "ghost")
        self._skip_btn.setCursor(Qt.PointingHandCursor)
        self._skip_btn.setToolTip(tr("wizard.skip_tip"))
        self._skip_btn.clicked.connect(self._on_skip)
        nav.addWidget(self._skip_btn)

        nav.addStretch()

        self._back_btn = QPushButton(tr("wizard.back"))
        self._back_btn.setProperty("variant", "secondary")
        self._back_btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.clicked.connect(self._on_back)
        nav.addWidget(self._back_btn)

        self._next_btn = QPushButton(tr("wizard.next"))
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.setToolTip(tr("wizard.next_tip"))
        self._next_btn.clicked.connect(self._on_next)
        nav.addWidget(self._next_btn)

        root.addLayout(nav)

    # ── Step 1: Welcome ──────────────────────────────────────────────────────

    def _build_step_welcome(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(18)

        # App icon / hero
        hero = QLabel("DevLearner AI")
        hero.setFont(QFont(FONT, F_TITLE, QFont.Bold))
        hero.setStyleSheet(f"color: {ACCENT};")
        hero.setAlignment(Qt.AlignCenter)
        layout.addWidget(hero)

        tagline = QLabel(tr("app.subtitle"))
        tagline.setStyleSheet(f"color: {TEXT_SUB}; font-size: 22px;")
        tagline.setAlignment(Qt.AlignCenter)
        layout.addWidget(tagline)

        layout.addSpacing(12)

        description = QLabel(tr("wizard.description"))
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 20px; line-height: 1.6;")
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)

        layout.addSpacing(12)

        features = [
            (tr("wizard.feature_learn"), tr("wizard.feature_learn_desc")),
            (tr("wizard.feature_practice"), tr("wizard.feature_practice_desc")),
            (tr("wizard.feature_projects"), tr("wizard.feature_projects_desc")),
            (tr("wizard.feature_ai"), tr("wizard.feature_ai_desc")),
            (tr("wizard.feature_achievements"), tr("wizard.feature_achievements_desc")),
        ]
        for title, desc in features:
            row = QHBoxLayout()
            row.setSpacing(12)
            badge = QLabel(title)
            badge.setFixedWidth(100)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                f"background: {ACCENT_SOFT}; color: {ACCENT}; "
                f"border-radius: 8px; padding: 6px 10px; font-weight: 600; font-size: 16px;"
            )
            row.addWidget(badge)
            desc_label = QLabel(desc)
            desc_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px;")
            row.addWidget(desc_label, 1)
            layout.addLayout(row)

        layout.addStretch()
        return page

    # ── Step 2: API Configuration ────────────────────────────────────────────

    def _build_step_api_config(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(18)

        title = QLabel(tr("wizard.api_title"))
        title.setFont(QFont(FONT, F_TITLE - 12, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(title)

        desc = QLabel(tr("wizard.api_desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px;")
        layout.addWidget(desc)

        layout.addSpacing(8)

        # Host input
        host_label = QLabel(tr("wizard.api_host"))
        host_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px; font-weight: 600;")
        layout.addWidget(host_label)
        self._api_host = QLineEdit()
        self._api_host.setPlaceholderText("https://api.openai.com/v1")
        self._api_host.setToolTip(tr("wizard.api_host_tip"))
        layout.addWidget(self._api_host)

        # API Key input
        key_label = QLabel(tr("wizard.api_key"))
        key_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px; font-weight: 600;")
        layout.addWidget(key_label)
        self._api_key = QLineEdit()
        self._api_key.setPlaceholderText("sk-...")
        self._api_key.setEchoMode(QLineEdit.Password)
        self._api_key.setToolTip(tr("wizard.api_key_tip"))
        layout.addWidget(self._api_key)

        # Model selector
        model_label = QLabel(tr("wizard.api_model"))
        model_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px; font-weight: 600;")
        layout.addWidget(model_label)
        self._api_model = QComboBox()
        self._api_model.setEditable(True)
        self._api_model.addItems(["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "deepseek-chat", "claude-3-5-sonnet"])
        self._api_model.setToolTip(tr("wizard.api_model_tip"))
        layout.addWidget(self._api_model)

        # Pre-fill existing config if available
        host, key, model = self.db.load_api_config()
        if host:
            self._api_host.setText(host)
        if key:
            self._api_key.setText(key)
        if model:
            idx = self._api_model.findText(model)
            if idx >= 0:
                self._api_model.setCurrentIndex(idx)
            else:
                self._api_model.setEditText(model)

        layout.addStretch()
        return page

    # ── Step 3: Choose Track ─────────────────────────────────────────────────

    def _build_step_track(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(18)

        title = QLabel(tr("wizard.track_title"))
        title.setFont(QFont(FONT, F_TITLE - 12, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(title)

        desc = QLabel(tr("wizard.track_desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px;")
        layout.addWidget(desc)

        layout.addSpacing(8)

        self._track_group = QButtonGroup(self)
        self._track_group.setExclusive(True)

        tracks = self.content_service.tracks
        for i, track in enumerate(tracks):
            card = QFrame()
            card.setCursor(Qt.PointingHandCursor)
            card.setStyleSheet(
                f"""
                QFrame {{
                    background: {BG_CARD};
                    border: 1px solid {BORDER};
                    border-radius: 14px;
                }}
                QFrame:hover {{
                    background: {ACCENT_SOFT};
                    border: 1px solid rgba(37,99,235,0.25);
                }}
                """
            )
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(20, 14, 20, 14)
            card_layout.setSpacing(14)

            icon_label = QLabel(track.icon)
            icon_label.setFont(QFont(FONT, 28))
            icon_label.setFixedWidth(48)
            icon_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(icon_label)

            text_col = QVBoxLayout()
            text_col.setSpacing(4)
            name = QLabel(track.title)
            name.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 20px; font-weight: 600;")
            text_col.addWidget(name)

            lesson_count = len(track.lessons)
            summary = QLabel(tr("wizard.track_lesson_count", count=lesson_count))
            summary.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px;")
            text_col.addWidget(summary)
            card_layout.addLayout(text_col, 1)

            radio = QRadioButton()
            radio.setToolTip(tr("wizard.track_radio_tip", title=track.title))
            self._track_group.addButton(radio, i)
            card_layout.addWidget(radio)

            # Click on card selects radio
            card.mousePressEvent = lambda ev, r=radio, tid=track.id: (r.setChecked(True), self._select_track(tid))
            radio.toggled.connect(lambda checked, tid=track.id: self._select_track(tid) if checked else None)

            layout.addWidget(card)
            if i == 0:
                radio.setChecked(True)
                self._selected_track_id = track.id

        if not tracks:
            no_tracks = QLabel(tr("dashboard.no_tracks"))
            no_tracks.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px;")
            layout.addWidget(no_tracks)

        layout.addStretch()
        return page

    def _select_track(self, track_id: str) -> None:
        self._selected_track_id = track_id

    # ── Step 4: Learning Goals ───────────────────────────────────────────────

    def _build_step_goals(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(18)

        title = QLabel(tr("wizard.goal_title"))
        title.setFont(QFont(FONT, F_TITLE - 12, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(title)

        desc = QLabel(tr("wizard.goal_desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px;")
        layout.addWidget(desc)

        layout.addSpacing(12)

        self._goal_group = QButtonGroup(self)
        self._goal_group.setExclusive(True)

        goals = [
            (tr("wizard.goal_easy"), tr("wizard.goal_easy_sub"), 1, tr("wizard.goal_easy_desc")),
            (tr("wizard.goal_steady"), tr("wizard.goal_steady_sub"), 5, tr("wizard.goal_steady_desc")),
            (tr("wizard.goal_intense"), tr("wizard.goal_intense_sub"), 20, tr("wizard.goal_intense_desc")),
        ]

        for i, (label, subtitle, target, desc_text) in enumerate(goals):
            card = QFrame()
            card.setCursor(Qt.PointingHandCursor)
            card.setStyleSheet(
                f"""
                QFrame {{
                    background: {BG_CARD};
                    border: 1px solid {BORDER};
                    border-radius: 14px;
                }}
                QFrame:hover {{
                    background: {ACCENT_SOFT};
                    border: 1px solid rgba(37,99,235,0.25);
                }}
                """
            )
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(20, 16, 20, 16)
            card_layout.setSpacing(14)

            radio = QRadioButton()
            radio.setToolTip(tr("wizard.goal_radio_tip", label=label))
            self._goal_group.addButton(radio, i)
            card_layout.addWidget(radio)

            text_col = QVBoxLayout()
            text_col.setSpacing(4)
            name = QLabel(f"{label}  --  {subtitle}")
            name.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 20px; font-weight: 600;")
            text_col.addWidget(name)

            desc_label = QLabel(desc_text)
            desc_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px;")
            text_col.addWidget(desc_label)
            card_layout.addLayout(text_col, 1)

            card.mousePressEvent = lambda ev, r=radio, t=target: (r.setChecked(True), self._set_goal(t))
            radio.toggled.connect(lambda checked, t=target: self._set_goal(t) if checked else None)

            layout.addWidget(card)
            if i == 0:
                radio.setChecked(True)
                self._goal_target = target

        layout.addStretch()
        return page

    def _set_goal(self, target: int) -> None:
        self._goal_target = target

    # ── Step 5: Feature Tour Overview ────────────────────────────────────────

    def _build_step_tour(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(18)

        title = QLabel(tr("wizard.tour_title"))
        title.setFont(QFont(FONT, F_TITLE - 12, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(title)

        desc = QLabel(tr("wizard.tour_desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px;")
        layout.addWidget(desc)

        layout.addSpacing(8)

        tour_items = [
            (tr("wizard.tour_sidebar"), tr("wizard.tour_sidebar_desc")),
            (tr("wizard.tour_dashboard"), tr("wizard.tour_dashboard_desc")),
            (tr("wizard.tour_learn"), tr("wizard.tour_learn_desc")),
            (tr("wizard.tour_practice"), tr("wizard.tour_practice_desc")),
            (tr("wizard.tour_ai"), tr("wizard.tour_ai_desc")),
        ]
        for i, (name, detail) in enumerate(tour_items):
            row = QHBoxLayout()
            row.setSpacing(14)

            num = QLabel(str(i + 1))
            num.setFixedSize(36, 36)
            num.setAlignment(Qt.AlignCenter)
            num.setStyleSheet(
                f"background: {ACCENT}; color: #ffffff; border-radius: 18px; font-size: 18px; font-weight: 700;"
            )
            row.addWidget(num)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            name_label = QLabel(name)
            name_label.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 20px; font-weight: 600;")
            text_col.addWidget(name_label)
            detail_label = QLabel(detail)
            detail_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px;")
            text_col.addWidget(detail_label)
            row.addLayout(text_col, 1)

            layout.addLayout(row)

        layout.addSpacing(8)

        finish_note = QLabel(tr("wizard.finish_note"))
        finish_note.setWordWrap(True)
        finish_note.setStyleSheet(f"color: {SUCCESS}; font-size: 19px; font-weight: 600;")
        finish_note.setAlignment(Qt.AlignCenter)
        layout.addWidget(finish_note)

        layout.addStretch()
        return page

    # ── Navigation ───────────────────────────────────────────────────────────

    def _goto_step(self, step: int) -> None:
        self._current_step = step
        self._stack.setCurrentIndex(step)
        self._indicator.set_step(step)

        # Update button states
        self._back_btn.setVisible(step > 0)
        if step == self._STEPS - 1:
            self._next_btn.setText(tr("wizard.start_learning"))
            self._next_btn.setToolTip(tr("wizard.start_learning_tip"))
        else:
            self._next_btn.setText("下一步")
            self._next_btn.setToolTip(tr("wizard.next_tip"))

    def _on_back(self) -> None:
        if self._current_step > 0:
            self._goto_step(self._current_step - 1)

    def _on_next(self) -> None:
        if self._current_step < self._STEPS - 1:
            # Save API config at step 2 before advancing
            if self._current_step == 1:
                self._save_api_config()
            self._goto_step(self._current_step + 1)
        else:
            self._finish()

    def _on_skip(self) -> None:
        self._finish()

    def _save_api_config(self) -> None:
        host = self._api_host.text().strip()
        key = self._api_key.text().strip()
        model = self._api_model.currentText().strip()
        if host or key or model:
            try:
                self.db.save_api_config(host, key, model)
                logger.info("Welcome wizard: API config saved")
            except Exception as exc:
                logger.warning("Welcome wizard: failed to save API config: %s", exc)

    def _finish(self) -> None:
        # Save any pending API config
        self._save_api_config()

        # Persist completion state
        self.db.mark_wizard_completed()

        # Emit signals
        if self._selected_track_id:
            self.track_selected.emit(self._selected_track_id)
        self.goal_selected.emit(self._goal_target)
        self.wizard_completed.emit()

        logger.info("Welcome wizard completed (track=%s, goal=%d)", self._selected_track_id, self._goal_target)
        self.accept()


def is_wizard_completed(db: AppDatabase) -> bool:
    """Check whether the welcome wizard has been completed."""
    return db.is_wizard_completed()


def reset_wizard_state(db: AppDatabase) -> None:
    """Reset wizard completion state (for testing or re-run)."""
    db.reset_wizard_completed()
