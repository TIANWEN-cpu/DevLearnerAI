"""Achievement system widgets -- display, notifications, and progress tracking."""

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QKeySequence, QPainter, QPen
from PyQt5.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QShortcut,
    QVBoxLayout,
    QWidget,
)

from app.database import AppDatabase
from app.styles import (
    ACCENT,
    F_TITLE,
    FONT,
    SUCCESS,
    TEXT_MAIN,
    TEXT_MUTED,
)


class AchievementBadge(QWidget):
    """A single achievement badge with icon and progress."""

    def __init__(self, achievement: dict, parent=None):
        super().__init__(parent)
        self.achievement = achievement
        self.setFixedSize(140, 160)
        title = achievement.get("title", "成就")
        unlocked = achievement.get("unlocked", False)
        self.setAccessibleName(title)
        self.setAccessibleDescription(f"{title}: {'已解锁' if unlocked else '未解锁'}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        unlocked = self.achievement.get("unlocked", False)
        progress = min(1.0, self.achievement.get("current_value", 0) / max(self.achievement.get("threshold", 1), 1))

        # Background
        if unlocked:
            bg_color = QColor("#f0fdf4")
            border_color = QColor(SUCCESS)
        else:
            bg_color = QColor("#f8fafc")
            border_color = QColor("#e2e8f0")

        painter.setBrush(QBrush(bg_color))
        pen = QPen(border_color, 2 if unlocked else 1)
        painter.setPen(pen)
        painter.drawRoundedRect(4, 4, self.width() - 8, self.height() - 8, 16, 16)

        # Icon circle
        icon_color = QColor(SUCCESS) if unlocked else QColor("#cbd5e1")
        painter.setBrush(QBrush(icon_color))
        painter.setPen(Qt.NoPen)
        cx, cy = self.width() // 2, 48
        painter.drawEllipse(cx - 24, cy - 24, 48, 48)

        # Icon text
        painter.setPen(QPen(QColor("#ffffff")))
        font = QFont(FONT, 20)
        painter.setFont(font)
        icon = self.achievement.get("icon", "?")
        painter.drawText(cx - 24, cy - 24, 48, 48, Qt.AlignCenter, icon)

        # Title
        painter.setPen(QPen(QColor(TEXT_MAIN if unlocked else TEXT_MUTED)))
        font = QFont(FONT, 13, QFont.Bold if unlocked else QFont.Normal)
        painter.setFont(font)
        title = self.achievement.get("title", "")
        painter.drawText(8, 84, self.width() - 16, 20, Qt.AlignCenter, title)

        # Progress text
        painter.setPen(QPen(QColor(TEXT_MUTED)))
        font = QFont(FONT, 12)
        painter.setFont(font)
        current = self.achievement.get("current_value", 0)
        threshold = self.achievement.get("threshold", 1)
        if unlocked:
            text = "已解锁"
        else:
            text = f"{current}/{threshold}"
        painter.drawText(8, 108, self.width() - 16, 18, Qt.AlignCenter, text)

        # Progress bar
        bar_x = 14
        bar_y = 132
        bar_w = self.width() - 28
        bar_h = 6
        painter.setBrush(QBrush(QColor("#e2e8f0")))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)

        bar_color = QColor(SUCCESS) if unlocked else QColor(ACCENT)
        painter.setBrush(QBrush(bar_color))
        painter.drawRoundedRect(bar_x, bar_y, int(bar_w * progress), bar_h, 3, 3)

        painter.end()


class AchievementNotification(QWidget):
    """Animated popup notification for unlocked achievements."""

    closed = pyqtSignal()

    def __init__(self, achievement: dict, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(360, 120)

        # Escape key to close
        QShortcut(QKeySequence(Qt.Key_Escape), self, self._close)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Icon
        icon_label = QLabel(achievement.get("icon", "🏆"))
        icon_label.setFixedSize(56, 56)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(
            "background: #f0fdf4; border: 2px solid #22c55e; border-radius: 14px; font-size: 28px;"
        )
        layout.addWidget(icon_label)

        # Text
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        title = QLabel("成就解锁!")
        title.setStyleSheet("color: #22c55e; font-weight: 700; font-size: 18px;")
        desc = QLabel(
            f"{achievement.get('icon', '')} {achievement.get('title', '')} - {achievement.get('description', '')}"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_MAIN}; font-size: 16px;")
        text_col.addWidget(title)
        text_col.addWidget(desc)
        layout.addLayout(text_col, 1)

        # Close button
        close_btn = QPushButton("x")
        close_btn.setFixedSize(28, 28)
        close_btn.setAccessibleName("关闭通知")
        close_btn.setAccessibleDescription("关闭成就解锁通知")
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #94a3b8; "
            "font-size: 16px; font-weight: 700; border-radius: 7px; }"
            "QPushButton:hover { background: #fee2e2; color: #ef4444; }"
        )
        close_btn.clicked.connect(self._close)
        layout.addWidget(close_btn, 0, Qt.AlignTop)

        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._close)
        self._dismiss_timer.start(5000)

    def _close(self):
        self._dismiss_timer.stop()
        self.closed.emit()
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor(SUCCESS), 2))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 20, 20)
        painter.end()


class AchievementsWidget(QWidget):
    """Full achievements display widget for the dashboard."""

    def __init__(self, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.db = db

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # Header row
        header = QHBoxLayout()
        title = QLabel("成就殿堂")
        title.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        header.addWidget(title)
        header.addStretch()

        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px; font-weight: 600;")
        header.addWidget(self.count_label)
        root.addLayout(header)

        # Category tabs
        self.category_row = QHBoxLayout()
        self.category_row.setSpacing(8)
        self._category_buttons = {}
        for cat_id, cat_label in [
            ("all", "全部"),
            ("learning", "学习"),
            ("practice", "练习"),
            ("streak", "连续"),
            ("feature", "功能"),
            ("special", "特殊"),
        ]:
            btn = QPushButton(cat_label)
            btn.setProperty("variant", "secondary")
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setChecked(cat_id == "all")
            btn.setAccessibleName(f"筛选类别：{cat_label}")
            btn.setAccessibleDescription(f"显示{cat_label}类别的成就")
            btn.clicked.connect(lambda _checked=False, c=cat_id: self._filter_category(c))
            self.category_row.addWidget(btn)
            self._category_buttons[cat_id] = btn
        root.addLayout(self.category_row)

        # Achievement grid area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setAccessibleName("成就网格")
        self.scroll_area.setAccessibleDescription("显示所有成就徽章的网格区域")
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_area.setWidget(self.grid_container)
        root.addWidget(self.scroll_area, 1)

        self._current_category = "all"
        self.refresh()

    def _filter_category(self, category: str) -> None:
        self._current_category = category
        for cat_id, btn in self._category_buttons.items():
            btn.setChecked(cat_id == category)
        self.refresh()

    def refresh(self) -> None:
        """Refresh achievement display."""
        # Clear grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        achievements = self.db.list_achievements()
        if self._current_category != "all":
            achievements = [a for a in achievements if a["category"] == self._current_category]

        unlocked_count = sum(1 for a in achievements if a["unlocked"])
        self.count_label.setText(f"{unlocked_count}/{len(achievements)} 已解锁")

        cols = 4
        for i, ach in enumerate(achievements):
            badge = AchievementBadge(ach)
            self.grid_layout.addWidget(badge, i // cols, i % cols)

    def show_notification(self, achievement: dict, parent_widget: QWidget) -> None:
        """Show an achievement notification popup near the parent widget."""
        # Find the top-level window
        top = parent_widget.window()
        notification = AchievementNotification(achievement, top)
        # Position at top-right of the window
        geo = top.geometry()
        notification.move(geo.right() - 380, geo.top() + 60)
        notification.show()
        notification.closed.connect(notification.deleteLater)
