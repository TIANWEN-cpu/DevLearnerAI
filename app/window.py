import sys

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.ai_mentor import AIMentorDock, AIMentorPanel
from app.config import APP_TITLE
from app.content_service import ContentService
from app.database import AppDatabase
from app.effects import apply_shadow
from app.practice_service import PracticeService
from app.styles import F_TITLE, FONT, GLOBAL_STYLE
from app.widgets.algo import AlgoVisualizerWidget
from app.widgets.dashboard import DashboardWidget
from app.widgets.learn import LearnWidget
from app.widgets.practice import PracticeWidget
from app.widgets.projects import ProjectsWidget


class DevLearnerWindow(QMainWindow):
    SIDEBAR_EXPANDED_WIDTH = 300
    SIDEBAR_COLLAPSED_WIDTH = 92

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(1360, 900)
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            width = min(2200, max(1360, geometry.width() - 60))
            height = min(1380, max(900, geometry.height() - 60))
            self.resize(width, height)
        else:
            self.resize(1600, 980)

        self.db = AppDatabase()
        self.db.init_db()
        self.content_service = ContentService()
        self.practice_service = PracticeService()

        self.dashboard = DashboardWidget(self.content_service, self.db)
        self.learn = LearnWidget(self.content_service, self.db)
        self.practice = PracticeWidget(
            self.content_service,
            self.practice_service,
            self.db,
        )
        self.projects = ProjectsWidget(self.content_service)
        self.ai_page = AIMentorPanel(self.db, self.content_service, mode="page")
        self.algo = AlgoVisualizerWidget()

        self.learning_pages = [
            ("首页", "总览今天学什么、练了什么、下一步去哪里。", self.dashboard, "首"),
            ("学习路径", "按主线进入模块，再从模块里递进学习课程。", self.learn, "路"),
            ("练习中心", "把知识点变成能真正写出来、能通过的代码能力。", self.practice, "练"),
            ("融合项目", "从单点知识走向能交付的小作品。", self.projects, "项"),
            ("算法动画", "把抽象步骤变成更容易看懂的过程。", self.algo, "算"),
        ]
        self.ai_page_spec = (
            "AI 工作台",
            "把对话、知识库和学习上下文放进一个真正可工作的 AI 页面。",
            self.ai_page,
        )
        self.ai_page_index = len(self.learning_pages)
        self.sidebar_expanded = True

        self.dashboard.navigate_requested.connect(self.switch_page)
        self.dashboard.track_requested.connect(self.open_track)
        self.ai_page.request_open_dock.connect(self.open_ai_dock)

        self.nav_buttons = []
        self._build_shell()

        self.ai_dock = AIMentorDock(self.db, self.content_service, self)
        self.ai_dock.setMinimumWidth(420)
        self.ai_dock.setFeatures(
            AIMentorDock.DockWidgetClosable | AIMentorDock.DockWidgetMovable
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.ai_dock)
        self.ai_dock.hide()
        self.ai_dock.panel.request_open_page.connect(self.open_ai_workspace)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(
            "v7.0 正在把原型收成正式产品：Ctrl+Enter 标记课程完成 | Ctrl+Shift+A 唤起 AI 提问"
        )

        ask_action = QAction("向 AI 提问", self)
        ask_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
        ask_action.triggered.connect(self.ask_ai_about_editor)
        self.addAction(ask_action)

        self._apply_sidebar_state()
        self.switch_page(0)

    def _build_shell(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content_shell(), 1)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QFrame:
        self.sidebar = QFrame()
        self.sidebar.setStyleSheet(
            """
            .QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #e6eef6,
                    stop: 1 #eef4f8
                );
                border-right: 1px solid rgba(37,99,235,0.10);
            }
            """
        )

        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(18, 22, 18, 20)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.sidebar_title = QLabel("LEARNING OS")
        self.sidebar_title.setStyleSheet(
            "color: #2563eb; font-size: 18px; font-weight: 700; letter-spacing: 1px;"
        )
        top_row.addWidget(self.sidebar_title)
        top_row.addStretch()
        self.sidebar_toggle_btn = QPushButton("◀")
        self.sidebar_toggle_btn.setProperty("variant", "secondary")
        self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar)
        self.sidebar_toggle_btn.setToolTip("收起导航")
        self.sidebar_toggle_btn.setFixedSize(48, 48)
        top_row.addWidget(self.sidebar_toggle_btn)
        layout.addLayout(top_row)

        self.brand_card = QFrame()
        self.brand_card.setStyleSheet(
            """
            .QFrame {
                background: rgba(255, 252, 246, 0.96);
                border: 1px solid rgba(37,99,235,0.08);
                border-radius: 20px;
            }
            """
        )
        apply_shadow(self.brand_card, blur=18, offset_y=4)
        brand_layout = QVBoxLayout(self.brand_card)
        brand_layout.setContentsMargins(16, 14, 16, 16)
        brand_layout.setSpacing(6)
        self.brand_logo = QLabel("DevLearner")
        self.brand_logo.setFont(QFont(FONT, F_TITLE - 8, QFont.Bold))
        self.brand_sub = QLabel("把学习路径、练习、项目和 AI 助手整合成一个清晰的工作台。")
        self.brand_sub.setWordWrap(True)
        self.brand_sub.setStyleSheet("color: #5f6f86; font-size: 18px;")
        brand_layout.addWidget(self.brand_logo)
        brand_layout.addWidget(self.brand_sub)
        layout.addWidget(self.brand_card)

        self.section = QLabel("导航")
        self.section.setStyleSheet(
            "color: #8b98ab; font-size: 18px; font-weight: 600; padding: 6px 10px;"
        )
        layout.addWidget(self.section)

        nav_icons = ["首", "路", "练", "项", "算"]
        for index, (title, _desc, _widget, short_title) in enumerate(self.learning_pages):
            button = QPushButton(title)
            button.setProperty("nav", "true")
            button.setCheckable(True)
            button.setToolTip(title)
            button.clicked.connect(lambda checked=False, i=index: self.switch_page(i))
            button.full_text = title
            button.short_text = short_title
            button.icon_text = nav_icons[index]
            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()
        return self.sidebar

    def _build_content_shell(self) -> QFrame:
        shell = QFrame()
        shell.setStyleSheet(
            """
            .QFrame {
                background: rgba(246,248,251,0.88);
                border: none;
            }
            """
        )

        layout = QVBoxLayout(shell)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        topbar = QFrame()
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(0, 0, 0, 0)
        topbar_layout.setSpacing(12)

        self.page_title = QLabel("")
        self.page_title.setFont(QFont(FONT, F_TITLE, QFont.Bold))
        self.page_title.setStyleSheet("color: #1c1c1e;")
        self.page_subtitle = QLabel("")
        self.page_subtitle.setStyleSheet("color: #64748b; font-size: 21px;")
        self.page_subtitle.setWordWrap(True)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        title_layout.addWidget(self.page_title)
        title_layout.addWidget(self.page_subtitle)
        topbar_layout.addLayout(title_layout, 1)

        chip_layout = QHBoxLayout()
        chip_layout.setSpacing(10)
        chip_layout.addWidget(self._make_chip(QDate.currentDate().toString("yyyy-MM-dd"), False))
        self.quick_ai_btn = QPushButton("AI 工作台")
        self.quick_ai_btn.setProperty("variant", "secondary")
        self.quick_ai_btn.clicked.connect(self.open_ai_workspace)
        chip_layout.addWidget(self.quick_ai_btn)
        topbar_layout.addLayout(chip_layout)
        layout.addWidget(topbar)

        self.stack = QStackedWidget()
        for _title, _desc, widget, _short in self.learning_pages:
            self.stack.addWidget(self._wrap_page(widget))
        self.stack.addWidget(self._wrap_page(self.ai_page))
        layout.addWidget(self.stack, 1)
        return shell

    def _make_chip(self, text: str, accent: bool) -> QLabel:
        chip = QLabel(text)
        if accent:
            chip.setStyleSheet(
                """
                QLabel {
                    background: rgba(0, 122, 255, 0.1);
                    border: none;
                    border-radius: 12px;
                    padding: 10px 16px;
                    color: #007aff;
                    font-size: 21px;
                    font-weight: 600;
                }
                """
            )
        else:
            chip.setStyleSheet(
                """
                QLabel {
                    background: #f5f5f7;
                    border: none;
                    border-radius: 12px;
                    padding: 10px 16px;
                    color: #64748b;
                    font-size: 21px;
                    font-weight: 500;
                }
                """
            )
        return chip

    def _wrap_page(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 24, 48)
        container_layout.setSpacing(0)
        container_layout.addWidget(widget)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: 0; }")
        return scroll

    def toggle_sidebar(self) -> None:
        self.sidebar_expanded = not self.sidebar_expanded
        self._apply_sidebar_state()

    def _apply_sidebar_state(self) -> None:
        expanded = self.sidebar_expanded
        self.sidebar.setFixedWidth(
            self.SIDEBAR_EXPANDED_WIDTH if expanded else self.SIDEBAR_COLLAPSED_WIDTH
        )
        self.sidebar_title.setVisible(expanded)
        self.brand_card.setVisible(expanded)
        self.brand_sub.setVisible(expanded)
        self.section.setVisible(expanded)
        self.sidebar_toggle_btn.setText("◀" if expanded else "▶")
        self.sidebar_toggle_btn.setToolTip("收起导航" if expanded else "展开导航")

        for button in self.nav_buttons:
            button.setText(button.full_text if expanded else button.icon_text)
            button.setMinimumHeight(58 if expanded else 72)
            button.setMaximumHeight(16777215 if expanded else 72)
            button.setProperty("compact", "false" if expanded else "true")
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def switch_page(self, index: int) -> None:
        if index == self.ai_page_index:
            self.open_ai_workspace()
            return
        if index < 0 or index >= len(self.learning_pages):
            return
        self.stack.setCurrentIndex(index)
        title, desc, widget, _short = self.learning_pages[index]
        self.page_title.setText(title)
        self.page_subtitle.setText(desc)
        if widget is self.dashboard:
            self.dashboard.refresh()

        for button_index, button in enumerate(self.nav_buttons):
            active = button_index == index
            button.setChecked(active)
            button.setProperty("active", "true" if active else "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def open_ai_workspace(self) -> None:
        self.ai_page.refresh_shared_state()
        self.stack.setCurrentIndex(self.ai_page_index)
        self.page_title.setText(self.ai_page_spec[0])
        self.page_subtitle.setText(self.ai_page_spec[1])
        for button in self.nav_buttons:
            button.setChecked(False)
            button.setProperty("active", "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def open_ai_dock(self) -> None:
        self.ai_dock.panel.refresh_shared_state()
        self.ai_dock.show()
        self.ai_dock.raise_()

    def open_track(self, track_id: str) -> None:
        self.learn.select_track(track_id)
        self.switch_page(1)

    def ask_ai_about_editor(self) -> None:
        selected = self.practice.editor.textCursor().selectedText().strip()
        if not selected:
            selected = self.practice.editor.toPlainText().strip()
        if selected:
            prompt = f"请帮我分析这段代码，并指出如何改进：\n{selected}"
            self.ai_page.refresh_shared_state()
            self.ai_dock.panel.refresh_shared_state()
            self.ai_page.input.setText(prompt)
            self.ai_dock.input.setText(prompt)
        self.open_ai_workspace()


def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLE)
    window = DevLearnerWindow()
    window.show()
    sys.exit(app.exec())
