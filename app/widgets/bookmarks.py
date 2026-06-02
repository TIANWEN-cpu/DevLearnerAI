"""Bookmarks / Favorites widget for the sidebar.

Displays bookmarked lessons and exercises with search and filter capabilities.
"""

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.database import AppDatabase
from app.styles import (
    ACCENT,
    ACCENT_SOFT,
    BG_CARD,
    BORDER,
    F_TITLE,
    FONT,
    TEXT_MAIN,
    TEXT_MUTED,
)


class BookmarksWidget(QWidget):
    """Bookmarks panel showing saved lessons and exercises."""

    bookmark_selected = pyqtSignal(str, str)  # (item_type, item_id)

    def __init__(self, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self._cards = []

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(12)

        # Header
        header = QLabel("我的收藏")
        header.setFont(QFont(FONT, F_TITLE - 16, QFont.Bold))
        header.setStyleSheet(f"color: {TEXT_MAIN};")
        root.addWidget(header)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索书签...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setAccessibleName("搜索收藏")
        self.search_input.setAccessibleDescription("输入关键词搜索已收藏的课程和练习")
        self.search_input.textChanged.connect(self._refresh_list)
        root.addWidget(self.search_input)

        # Filter buttons
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        self.filter_all = QPushButton("全部")
        self.filter_all.setProperty("variant", "secondary")
        self.filter_all.setCheckable(True)
        self.filter_all.setChecked(True)
        self.filter_lesson = QPushButton("课程")
        self.filter_lesson.setProperty("variant", "secondary")
        self.filter_lesson.setCheckable(True)
        self.filter_exercise = QPushButton("练习")
        self.filter_exercise.setProperty("variant", "secondary")
        self.filter_exercise.setCheckable(True)
        for btn, ftype in [(self.filter_all, ""), (self.filter_lesson, "lesson"), (self.filter_exercise, "exercise")]:
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAccessibleName(f"筛选：{btn.text()}")
            btn.clicked.connect(lambda _checked=False, ft=ftype: self._set_filter(ft))
            filter_row.addWidget(btn)
        root.addLayout(filter_row)

        # Bookmark count
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px;")
        root.addWidget(self.count_label)

        # Bookmark list
        self.bookmark_list = QListWidget()
        self.bookmark_list.setSpacing(8)
        self.bookmark_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.bookmark_list.setAccessibleName("收藏列表")
        self.bookmark_list.setAccessibleDescription("已收藏的课程和练习项目列表")
        self.bookmark_list.setStyleSheet(
            """
            QListWidget { background: transparent; border: none; padding: 2px; }
            QListWidget::item { background: transparent; border: none; margin: 0; padding: 0; }
            QListWidget::item:selected { background: transparent; }
            """
        )
        self.bookmark_list.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self.bookmark_list, 1)

        self._current_filter = ""
        self.refresh()

    def _set_filter(self, ftype: str) -> None:
        self._current_filter = ftype
        self.filter_all.setChecked(ftype == "")
        self.filter_lesson.setChecked(ftype == "lesson")
        self.filter_exercise.setChecked(ftype == "exercise")
        self._refresh_list()

    def refresh(self) -> None:
        """Refresh the bookmark list from database."""
        self._refresh_list()

    def _refresh_list(self) -> None:
        self.bookmark_list.clear()
        self._cards = []

        query = self.search_input.text().strip()
        if query:
            bookmarks = self.db.search_bookmarks(query)
        elif self._current_filter:
            bookmarks = self.db.list_bookmarks(self._current_filter)
        else:
            bookmarks = self.db.list_bookmarks()

        self.count_label.setText(f"共 {len(bookmarks)} 个收藏")

        for bm in bookmarks:
            _id, item_type, item_id, title, track_id, note, created_at = bm
            item = QListWidgetItem()
            item.setData(Qt.UserRole, (item_type, item_id))
            item.setSizeHint(QSize(0, 80))
            self.bookmark_list.addItem(item)

            card = self._make_card(item_type, item_id, title, track_id, note, created_at)
            self.bookmark_list.setItemWidget(item, card)
            self._cards.append((item, card))

    def _make_card(self, item_type: str, item_id: str, title: str, track_id: str, note: str, created_at: str) -> QFrame:
        card = QFrame()
        type_label = "课程" if item_type == "lesson" else "练习"
        type_color = ACCENT if item_type == "lesson" else "#8b5cf6"
        card.setStyleSheet(
            f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 14px;
            }}
            QFrame:hover {{
                border: 1px solid rgba(37,99,235,0.25);
            }}
            QFrame QLabel {{ background: transparent; border: none; }}
            """
        )
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        # Type indicator
        indicator = QLabel(type_label)
        indicator.setFixedSize(42, 42)
        indicator.setAlignment(Qt.AlignCenter)
        indicator.setStyleSheet(
            f"background: {ACCENT_SOFT if item_type == 'lesson' else '#f3e8ff'}; "
            f"color: {type_color}; border-radius: 10px; font-weight: 700; font-size: 15px;"
        )
        layout.addWidget(indicator)

        # Info column
        info = QVBoxLayout()
        info.setSpacing(3)
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: 600; font-size: 17px;")
        meta = QLabel(f"{type_label} · {track_id}" if track_id else type_label)
        meta.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 15px;")
        info.addWidget(title_label)
        info.addWidget(meta)
        layout.addLayout(info, 1)

        # Remove button
        remove_btn = QPushButton("x")
        remove_btn.setFixedSize(32, 32)
        remove_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #94a3b8; border: none; "
            "border-radius: 8px; font-size: 16px; font-weight: 700; }"
            "QPushButton:hover { background: #fee2e2; color: #ef4444; }"
        )
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(lambda _checked=False, it=item_type, iid=item_id: self._remove(it, iid))
        layout.addWidget(remove_btn, 0, Qt.AlignTop)

        return card

    def _remove(self, item_type: str, item_id: str) -> None:
        self.db.remove_bookmark(item_type, item_id)
        self._refresh_list()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        item_type, item_id = item.data(Qt.UserRole)
        self.bookmark_selected.emit(item_type, item_id)
