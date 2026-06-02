import mistune
from PyQt5.QtCore import QEvent, QSize, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.content_service import ContentService
from app.effects import optimize_scroll_widget
from app.localized_inputs import LocalizedTextBrowser
from app.reader_dialog import ReaderDialog
from app.styles import F_SUB, F_TITLE, FONT


class ProjectsWidget(QWidget):
    def __init__(self, content_service: ContentService):
        super().__init__()
        self.content_service = content_service
        self.markdown = mistune.create_markdown()
        self.integration_track = self.content_service.track_by_id("integration")
        self._current_html = ""
        self._current_title = ""
        self._current_meta = ""
        self.project_cards = []
        optimize_scroll_widget(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.setSpacing(16)
        layout.addWidget(self._build_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_main_panel())
        splitter.setSizes([360, 1220])
        layout.addWidget(splitter, 1)

        self.project_list.currentRowChanged.connect(self.load_project)
        self.reader_btn.clicked.connect(self._open_reader)
        if self.project_list.count():
            self.project_list.setCurrentRow(0)

    def _project_category_theme(self, module_title: str):
        if module_title.startswith("基础模块"):
            return "#2f6df6", "基础模块"
        if module_title.startswith("精选模块"):
            return "#8b5cf6", "精选模块"
        if module_title.startswith("兴趣模块"):
            return "#10b981", "兴趣模块"
        return "#94a3b8", "通用模块"

    def _build_header(self) -> QFrame:
        header = self._surface_panel()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(4)
        title = QLabel("融合项目")
        title.setFont(QFont(FONT, F_TITLE - 4, QFont.Bold))
        subtitle = QLabel("从单点知识走向能交付的小作品，重点练范围控制、结构设计和真实落地。")
        subtitle.setStyleSheet("color: #3a506b; font-size: 18px;")
        subtitle.setWordWrap(True)
        left.addWidget(title)
        left.addWidget(subtitle)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(6)
        pace_title = QLabel("建议节奏")
        pace_title.setStyleSheet("color: #1c1c1e; font-weight: 700; font-size: 18px;")
        pace_text = QLabel("先做命令行项目，再做 Python + SQLite，最后再碰 FastAPI 后端。")
        pace_text.setWordWrap(True)
        pace_text.setStyleSheet("color: #3a506b; font-size: 17px;")
        right.addWidget(pace_title)
        right.addWidget(pace_text)
        layout.addLayout(right)
        return header

    def _build_left_panel(self) -> QFrame:
        panel = self._surface_panel()
        panel.setMinimumWidth(320)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("项目列表")
        title.setFont(QFont(FONT, F_SUB, QFont.Bold))
        summary = QLabel("从小而完整的项目开始，逐步提升到带数据库和接口的作品。")
        summary.setWordWrap(True)
        summary.setStyleSheet("color: #3a506b; font-size: 18px;")
        layout.addWidget(title)
        layout.addWidget(summary)

        self.project_list = QListWidget()
        self.project_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.project_list.setWordWrap(True)
        self.project_list.setSpacing(10)
        self.project_list.setAccessibleName("项目列表")
        self.project_list.setAccessibleDescription("选择一个融合项目进行学习")
        self.project_list.setStyleSheet(
            """
            QListWidget { background: transparent; border: none; padding: 2px; }
            QListWidget::item { background: transparent; border: none; padding: 0; margin: 0; }
            QListWidget::item:selected { background: transparent; }
            """
        )
        if self.integration_track:
            for module in self.integration_track.modules:
                for lesson in module.lessons:
                    self._add_project_item(
                        module.title,
                        lesson.id,
                        lesson.title,
                        lesson.summary,
                        lesson.estimated_minutes,
                    )
        layout.addWidget(self.project_list, 1)
        return panel

    def _apply_project_card_style(self, card: QFrame, selected: bool, stripe: str) -> None:
        bg = "#edf4ff" if selected else "#f7f9fc"
        border = "rgba(37,99,235,0.18)" if selected else "rgba(15,23,42,0.08)"
        card.setObjectName("projectCard")
        card.setStyleSheet(
            f"""
            QFrame#projectCard {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff,
                    stop: 0.18 rgba(255,255,255,0.98),
                    stop: 1 {bg}
                );
                border: 1px solid {border};
                border-radius: 20px;
            }}
            QFrame#projectCard QFrame#projectAccentStripe {{
                background: {stripe};
                border: none;
                border-top-left-radius: 20px;
                border-bottom-left-radius: 20px;
            }}
            QFrame#projectCard QFrame#projectCardGloss {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(255,255,255,0.95),
                    stop: 1 rgba(255,255,255,0.0)
                );
                border: none;
                border-radius: 12px;
                max-height: 12px;
            }}
            QFrame#projectCard QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )

    def _make_project_card(self, module_title: str, title: str, summary: str, minutes: int) -> QFrame:
        stripe, category = self._project_category_theme(module_title)
        card = QFrame()
        self._apply_project_card_style(card, False, stripe)

        outer = QHBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        accent_stripe = QFrame()
        accent_stripe.setObjectName("projectAccentStripe")
        accent_stripe.setFixedWidth(7)
        outer.addWidget(accent_stripe)

        body = QWidget()
        outer.addWidget(body, 1)

        layout = QVBoxLayout(body)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(8)

        gloss = QFrame()
        gloss.setObjectName("projectCardGloss")
        gloss.setFixedHeight(14)
        layout.addWidget(gloss)

        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: #0f172a; font-weight: 700; font-size: 22px;")
        meta_label = QLabel(f"{category} · {module_title} · 预计 {minutes} 分钟")
        meta_label.setWordWrap(True)
        meta_label.setStyleSheet("color: #64748b; font-size: 18px; font-weight: 600;")
        summary_label = QLabel(summary)
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet("color: #42556b; font-size: 18px;")
        layout.addWidget(title_label)
        layout.addWidget(meta_label)
        layout.addWidget(summary_label)
        return card

    def _add_project_item(self, module_title: str, lesson_id: str, title: str, summary: str, minutes: int) -> None:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, lesson_id)
        stripe, _category = self._project_category_theme(module_title)
        item.setData(Qt.UserRole + 10, stripe)
        item.setSizeHint(QSize(0, 156))
        self.project_list.addItem(item)
        card = self._make_project_card(module_title, title, summary, minutes)
        self.project_list.setItemWidget(item, card)
        self.project_cards.append((item, card))

    def _refresh_project_selection(self) -> None:
        current_item = self.project_list.currentItem()
        for item, card in self.project_cards:
            stripe = item.data(Qt.UserRole + 10) or "#94a3b8"
            self._apply_project_card_style(card, item is current_item, stripe)

    def _build_main_panel(self) -> QFrame:
        panel = self._surface_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.meta_title = QLabel("选择一个项目")
        self.meta_title.setFont(QFont(FONT, F_TITLE - 6, QFont.Bold))
        self.meta_meta = QLabel("")
        self.meta_meta.setStyleSheet("color: #3a506b; font-size: 18px; font-weight: 600;")
        layout.addWidget(self.meta_title)
        layout.addWidget(self.meta_meta)

        self.tip_strip = QLabel("")
        self.tip_strip.setWordWrap(True)
        self.tip_strip.setStyleSheet(
            """
            QLabel {
                background: #eef6ff;
                border: 1px solid rgba(37,99,235,0.08);
                border-radius: 16px;
                padding: 12px 14px;
                color: #41556d;
                font-size: 17px;
            }
            """
        )
        layout.addWidget(self.tip_strip)

        self.content_browser = LocalizedTextBrowser()
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.setMinimumHeight(540)
        self.content_browser.setAccessibleName("项目文档")
        self.content_browser.setAccessibleDescription("当前选择项目的详细文档内容")
        self.content_browser.viewport().installEventFilter(self)
        layout.addWidget(self.content_browser, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.reader_btn = QPushButton("放大阅读")
        self.reader_btn.setProperty("variant", "secondary")
        self.reader_btn.setToolTip("在独立窗口中放大阅读项目文档")
        self.reader_btn.setAccessibleName("放大阅读")
        self.reader_btn.setAccessibleDescription("在独立窗口中以更大字体阅读项目文档")
        btn_row.addWidget(self.reader_btn)
        layout.addLayout(btn_row)
        return panel

    def load_project(self, row: int) -> None:
        if row < 0 or not self.integration_track:
            return
        self._refresh_project_selection()
        lesson_id = self.project_list.item(row).data(Qt.UserRole)
        for module in self.integration_track.modules:
            for lesson in module.lessons:
                if lesson.id == lesson_id:
                    self.meta_title.setText(lesson.title)
                    self.meta_meta.setText(
                        f"模块：{module.title} · 难度：{lesson.difficulty} · 预计 {lesson.estimated_minutes} 分钟"
                    )
                    self.tip_strip.setText(
                        f"建议先完成：{module.title}\n"
                        f"做完后应该得到：{lesson.summary}\n"
                        "推进建议：先收窄 MVP，再按 数据结构 → 核心流程 → 存储 → 体验优化 的顺序推进。"
                    )
                    self._current_title = lesson.title
                    self._current_meta = self.meta_meta.text()
                    body = self.content_service.lesson_markdown(lesson)
                    self._current_html = self.markdown(body)
                    self.content_browser.setHtml(self._current_html)
                    return

    def _open_reader(self) -> None:
        dialog = ReaderDialog(self._current_title, self._current_html, self._current_meta, self)
        dialog.exec_()

    def eventFilter(self, watched, event):
        if watched is self.content_browser.viewport() and event.type() == QEvent.MouseButtonDblClick:
            self._open_reader()
            return True
        return super().eventFilter(watched, event)
