import logging
import sys
import time as _time

from PyQt5.QtCore import QDate, Qt, QTimer

logger = logging.getLogger(__name__)
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
    QSplashScreen,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.ai_mentor import AIMentorDock, AIMentorPanel
from app.config import APP_TITLE, APP_VERSION
from app.content_service import ContentService
from app.database import AppDatabase, close_connection
from app.effects import apply_shadow
from app.practice_service import PracticeService
from app.styles import (
    F_TITLE,
    FONT,
    GLOBAL_STYLE,
    build_style_for_size,
)
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

        self._dark_mode = False
        self._font_size = "medium"

        # Core services (lightweight, always needed)
        _t0 = _time.monotonic()
        self.db = AppDatabase()
        self.db.init_db()
        self.content_service = ContentService()
        self.practice_service = PracticeService()
        _t1 = _time.monotonic()
        logging.getLogger(__name__).info("核心服务初始化耗时 %.1f ms", (_t1 - _t0) * 1000)

        # Critical widgets (visible at startup)
        self.dashboard = DashboardWidget(self.content_service, self.db)
        self.learn = LearnWidget(self.content_service, self.db)
        self.practice = PracticeWidget(
            self.content_service,
            self.practice_service,
            self.db,
        )

        # Deferred widgets - created with deferred_init for staggered loading
        self._projects_ready = False
        self._algo_ready = False
        self._ai_ready = False

        # Create lightweight placeholder widgets first
        self._projects_placeholder = QWidget()
        self._algo_placeholder = QWidget()
        self._ai_page_placeholder = QWidget()

        self.projects = self._projects_placeholder
        self.algo = self._algo_placeholder
        self.ai_page = self._ai_page_placeholder

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

        self.nav_buttons = []
        self._build_shell()

        # AI dock created lazily
        self.ai_dock = None

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Connection status indicator
        self._connection_label = QLabel()
        self._connection_label.setAccessibleName("连接状态")
        self._connection_label.setAccessibleDescription("显示当前网络连接状态")
        self._connection_label.setStyleSheet(
            "padding: 4px 12px; border-radius: 10px; font-size: 16px; font-weight: 600;"
        )
        self._update_connection_status("ready")
        self.status.addPermanentWidget(self._connection_label)

        self.status.showMessage(f"v{APP_VERSION} | Ctrl+Enter 提交 | Ctrl+N 下一题 | Ctrl+H 提示 | Ctrl+/ 快捷键帮助")

        # ── Keyboard shortcuts ───────────────────────────────────────────────

        ask_action = QAction("向 AI 提问", self)
        ask_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
        ask_action.triggered.connect(self.ask_ai_about_editor)
        self.addAction(ask_action)

        submit_action = QAction("提交答案", self)
        submit_action.setShortcut(QKeySequence("Ctrl+Return"))
        submit_action.triggered.connect(self._shortcut_submit)
        self.addAction(submit_action)

        next_ex_action = QAction("下一题", self)
        next_ex_action.setShortcut(QKeySequence("Ctrl+N"))
        next_ex_action.triggered.connect(self._shortcut_next_exercise)
        self.addAction(next_ex_action)

        hint_action = QAction("查看提示", self)
        hint_action.setShortcut(QKeySequence("Ctrl+H"))
        hint_action.triggered.connect(self._shortcut_show_hint)
        self.addAction(hint_action)

        theme_action = QAction("切换主题", self)
        theme_action.setShortcut(QKeySequence("Ctrl+T"))
        theme_action.triggered.connect(self.toggle_theme)
        self.addAction(theme_action)

        help_shortcuts_action = QAction("快捷键帮助", self)
        help_shortcuts_action.setShortcut(QKeySequence("Ctrl+/"))
        help_shortcuts_action.triggered.connect(self._show_shortcuts_help)
        self.addAction(help_shortcuts_action)

        # Page navigation shortcuts (Ctrl+1 through Ctrl+5)
        for page_idx in range(min(5, len(self.learning_pages))):
            nav_action = QAction(f"切换到页面 {page_idx + 1}", self)
            nav_action.setShortcut(QKeySequence(f"Ctrl+{page_idx + 1}"))
            nav_action.triggered.connect(lambda _checked=False, i=page_idx: self.switch_page(i))
            self.addAction(nav_action)

        self._apply_sidebar_state()
        self.switch_page(0)

        # Defer heavy widget initialization after window is visible
        QTimer.singleShot(50, self._deferred_init)

    def _ensure_projects(self) -> QWidget:
        """Lazy-init ProjectsWidget on first access."""
        if self._projects_ready:
            return self.projects

        self.projects = ProjectsWidget(self.content_service)
        self.learning_pages[3] = ("融合项目", "从单点知识走向能交付的小作品。", self.projects, "项")
        self._projects_ready = True
        return self.projects

    def _ensure_algo(self) -> QWidget:
        """Lazy-init AlgoVisualizerWidget on first access."""
        if self._algo_ready:
            return self.algo

        self.algo = AlgoVisualizerWidget()
        self.learning_pages[4] = ("算法动画", "把抽象步骤变成更容易看懂的过程。", self.algo, "算")
        self._algo_ready = True
        return self.algo

    def _ensure_ai_page(self) -> QWidget:
        """Lazy-init AIMentorPanel on first access."""
        if self._ai_ready:
            return self.ai_page
        self.ai_page = AIMentorPanel(self.db, self.content_service, mode="page")
        self.ai_page.request_open_dock.connect(self.open_ai_dock)
        self.ai_page_spec = (
            "AI 工作台",
            "把对话、知识库和学习上下文放进一个真正可工作的 AI 页面。",
            self.ai_page,
        )
        self._ai_ready = True
        return self.ai_page

    def _ensure_ai_dock(self):
        """Lazy-init AIMentorDock on first access."""
        if self.ai_dock is not None:
            return self.ai_dock
        self.ai_dock = AIMentorDock(self.db, self.content_service, self)
        self.ai_dock.setMinimumWidth(420)
        self.ai_dock.setFeatures(AIMentorDock.DockWidgetClosable | AIMentorDock.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ai_dock)
        self.ai_dock.hide()
        self.ai_dock.panel.request_open_page.connect(self.open_ai_workspace)
        return self.ai_dock

    def _deferred_init(self) -> None:
        """Run non-critical initialization after the window is shown.

        Staggers heavy widget creation to avoid blocking the event loop.
        Each widget is created with a small delay to keep the UI responsive.
        """
        QTimer.singleShot(0, self._ensure_projects)
        QTimer.singleShot(150, self._ensure_algo)
        QTimer.singleShot(300, self._ensure_ai_page)
        QTimer.singleShot(500, self._ensure_ai_dock)

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
        self.sidebar_title.setStyleSheet("color: #2563eb; font-size: 18px; font-weight: 700; letter-spacing: 1px;")
        top_row.addWidget(self.sidebar_title)
        top_row.addStretch()
        self.sidebar_toggle_btn = QPushButton("◀")
        self.sidebar_toggle_btn.setProperty("variant", "secondary")
        self.sidebar_toggle_btn.clicked.connect(self.toggle_sidebar)
        self.sidebar_toggle_btn.setToolTip("收起导航")
        self.sidebar_toggle_btn.setAccessibleName("收起导航侧栏")
        self.sidebar_toggle_btn.setAccessibleDescription("收起或展开左侧导航面板")
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
        self.section.setStyleSheet("color: #8b98ab; font-size: 18px; font-weight: 600; padding: 6px 10px;")
        layout.addWidget(self.section)

        nav_icons = ["首", "路", "练", "项", "算"]
        for index, (title, _desc, _widget, short_title) in enumerate(self.learning_pages):
            button = QPushButton(title)
            button.setProperty("nav", "true")
            button.setCheckable(True)
            button.setToolTip(f"切换到{title}页面 (Ctrl+{index + 1})")
            button.setAccessibleName(f"导航到{title}")
            button.setAccessibleDescription(f"切换到{title}页面")
            button.clicked.connect(lambda checked=False, i=index: self.switch_page(i))
            button.full_text = title
            button.short_text = short_title
            button.icon_text = nav_icons[index]
            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()

        # Theme and font size controls
        self._sidebar_settings = QFrame()
        settings_layout = QVBoxLayout(self._sidebar_settings)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(8)

        self.theme_btn = QPushButton("深色模式")
        self.theme_btn.setProperty("variant", "secondary")
        self.theme_btn.setFixedHeight(48)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setToolTip("切换深色/浅色主题 (Ctrl+T)")
        self.theme_btn.setAccessibleName("主题切换")
        self.theme_btn.setAccessibleDescription("切换深色或浅色主题")
        self.theme_btn.clicked.connect(self.toggle_theme)
        settings_layout.addWidget(self.theme_btn)

        font_row = QHBoxLayout()
        font_row.setSpacing(6)
        font_labels = [("small", "A-", "缩小字体"), ("medium", "A", "默认字体"), ("large", "A+", "放大字体")]
        for size_name, label, tip in font_labels:
            btn = QPushButton(label)
            btn.setProperty("variant", "secondary")
            btn.setFixedSize(48, 48)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setAccessibleName(f"字体大小：{tip}")
            btn.setAccessibleDescription(f"将界面字体调整为{tip}")
            btn.clicked.connect(lambda _checked=False, s=size_name: self.set_font_size(s))
            font_row.addWidget(btn)
        settings_layout.addLayout(font_row)

        whats_new_btn = QPushButton("新版本")
        whats_new_btn.setProperty("variant", "ghost")
        whats_new_btn.setCursor(Qt.PointingHandCursor)
        whats_new_btn.setToolTip("查看当前版本的更新内容")
        whats_new_btn.clicked.connect(self._show_whats_new)
        settings_layout.addWidget(whats_new_btn)

        layout.addWidget(self._sidebar_settings)
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
        self.page_title.setAccessibleName("页面标题")
        self.page_subtitle = QLabel("")
        self.page_subtitle.setStyleSheet("color: #64748b; font-size: 21px;")
        self.page_subtitle.setWordWrap(True)
        self.page_subtitle.setAccessibleName("页面描述")

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
        self.quick_ai_btn.setToolTip("打开 AI 工作台 (Ctrl+Shift+A)")
        self.quick_ai_btn.setAccessibleName("AI 工作台")
        self.quick_ai_btn.setAccessibleDescription("打开 AI 工作台进行智能对话")
        self.quick_ai_btn.clicked.connect(self.open_ai_workspace)
        chip_layout.addWidget(self.quick_ai_btn)
        topbar_layout.addLayout(chip_layout)
        layout.addWidget(topbar)

        self.stack = QStackedWidget()
        self.stack.setAccessibleName("主要内容区域")
        self.stack.setAccessibleDescription("显示当前选中页面的内容")
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
        self.sidebar.setFixedWidth(self.SIDEBAR_EXPANDED_WIDTH if expanded else self.SIDEBAR_COLLAPSED_WIDTH)
        self.sidebar_title.setVisible(expanded)
        self.brand_card.setVisible(expanded)
        self.brand_sub.setVisible(expanded)
        self.section.setVisible(expanded)
        if hasattr(self, "_sidebar_settings"):
            self._sidebar_settings.setVisible(expanded)
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
        self.page_title.setAccessibleName(f"当前页面：{title}")
        self.page_subtitle.setAccessibleDescription(desc)
        self.status.showMessage(f"已切换到：{title}", 3000)
        # Announce page change for screen readers
        self.status.setAccessibleDescription(f"当前页面：{title}。{desc}")
        if widget is self.dashboard:
            self.dashboard.refresh()

        for button_index, button in enumerate(self.nav_buttons):
            active = button_index == index
            was_active = button.property("active") == "true"
            if active == was_active:
                continue  # skip unchanged buttons
            button.setChecked(active)
            button.setProperty("active", "true" if active else "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def open_ai_workspace(self) -> None:
        page = self._ensure_ai_page()
        page.refresh_shared_state()
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
        dock = self._ensure_ai_dock()
        dock.panel.refresh_shared_state()
        dock.show()
        dock.raise_()

    def open_track(self, track_id: str) -> None:
        self.learn.select_track(track_id)
        self.switch_page(1)

    def ask_ai_about_editor(self) -> None:
        selected = self.practice.editor.textCursor().selectedText().strip()
        if not selected:
            selected = self.practice.editor.toPlainText().strip()
        if selected:
            prompt = f"请帮我分析这段代码，并指出如何改进：\n{selected}"
            page = self._ensure_ai_page()
            page.refresh_shared_state()
            page.input.setText(prompt)
            dock = self._ensure_ai_dock()
            dock.panel.refresh_shared_state()
            dock.input.setText(prompt)
        self.open_ai_workspace()

    # ── Keyboard shortcut handlers ───────────────────────────────────────────

    def _shortcut_submit(self) -> None:
        """Ctrl+Enter: submit answer in practice view."""
        if self.stack.currentIndex() == 2 and self.practice.current_exercise:
            self.practice.evaluate_code()

    def _shortcut_next_exercise(self) -> None:
        """Ctrl+N: next exercise in practice view."""
        if self.stack.currentIndex() == 2:
            row = self.practice.exercise_list.currentRow()
            if row < self.practice.exercise_list.count() - 1:
                self.practice.exercise_list.setCurrentRow(row + 1)

    def _shortcut_show_hint(self) -> None:
        """Ctrl+H: show hint in practice view."""
        if self.stack.currentIndex() == 2 and self.practice.current_exercise:
            self.practice.show_hint()

    # ── Connection status ────────────────────────────────────────────────────

    # Connection status themes: status_key -> (label, foreground_color, background_color)
    _CONNECTION_THEMES: dict[str, tuple[str, str, str]] = {
        "ready": ("在线就绪", "#22c55e", "#dcfce7"),
        "online": ("已连接", "#22c55e", "#dcfce7"),
        "offline": ("未连接", "#ef4444", "#fee2e2"),
        "busy": ("请求中...", "#f59e0b", "#fef3c7"),
    }

    def _update_connection_status(self, status: str) -> None:
        """Update the permanent connection status indicator in the status bar.

        Args:
            status: One of 'ready', 'online', 'offline', 'busy'.
        """
        text, color, bg = self._CONNECTION_THEMES.get(status, self._CONNECTION_THEMES["ready"])
        self._connection_label.setText(f"  {text}  ")
        self._connection_label.setStyleSheet(
            f"background: {bg}; color: {color}; padding: 4px 12px; "
            f"border-radius: 10px; font-size: 16px; font-weight: 600;"
        )

    # ── Theme toggle ─────────────────────────────────────────────────────────

    def toggle_theme(self) -> None:
        """Switch between light and dark themes."""
        self._dark_mode = not self._dark_mode
        self._apply_style_deferred()
        theme_label = "深色" if self._dark_mode else "浅色"
        self.status.showMessage(f"已切换到{theme_label}主题", 3000)

    def set_font_size(self, size_name: str) -> None:
        """Apply a named font-size preset and rebuild the stylesheet.

        Args:
            size_name: 'small', 'medium', or 'large'.
        """
        self._font_size = size_name
        self._apply_style_deferred()
        size_labels = {"small": "小", "medium": "中", "large": "大"}
        self.status.showMessage(f"字体大小已调整为：{size_labels.get(size_name, size_name)}", 3000)

    def _apply_style_deferred(self) -> None:
        """Apply stylesheet on next event loop tick to batch rapid changes."""
        if not hasattr(self, "_style_pending"):
            self._style_pending = False
        if self._style_pending:
            return
        self._style_pending = True
        QTimer.singleShot(0, self._do_apply_style)

    def _do_apply_style(self) -> None:
        """Actually apply the cached stylesheet."""
        self._style_pending = False
        style = build_style_for_size(self._font_size, dark=self._dark_mode)
        QApplication.instance().setStyleSheet(style)
        self._update_connection_status("ready")

    def _show_whats_new(self) -> None:
        """Show a 'What's New' dialog with the latest changelog entries."""
        from pathlib import Path

        from PyQt5.QtWidgets import QMessageBox

        changelog_path = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
        try:
            raw = changelog_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raw = ""

        # Extract the latest version section (up to the next '---' or '## ')
        lines = raw.splitlines()
        section_lines = []
        in_section = False
        for line in lines:
            if line.startswith("## [") and not in_section:
                in_section = True
                section_lines.append(line)
            elif in_section:
                if line.startswith("## [") or (line.strip() == "---" and len(section_lines) > 2):
                    break
                section_lines.append(line)

        body = "\n".join(section_lines).strip() if section_lines else "暂无更新说明。"
        msg = QMessageBox(self)
        msg.setWindowTitle(f"DevLearner AI v{APP_VERSION} -- 新版本内容")
        msg.setTextFormat(Qt.RichText)
        msg.setText(
            f"<h3>DevLearner AI v{APP_VERSION}</h3>"
            f"<pre style='font-family: Microsoft YaHei UI; font-size: 14px;'>{body}</pre>"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def _show_shortcuts_help(self) -> None:
        """Show a keyboard shortcuts reference dialog."""
        from PyQt5.QtWidgets import QMessageBox

        shortcuts_html = """
        <table style="font-size: 14px; border-collapse: collapse; width: 100%;">
        <tr style="background: #f1f5f9;"><th style="padding: 8px 16px; text-align: left;">快捷键</th>
        <th style="padding: 8px 16px; text-align: left;">功能</th></tr>
        <tr><td style="padding: 6px 16px;"><b>Ctrl+1</b> ~ <b>Ctrl+5</b></td>
            <td style="padding: 6px 16px;">切换页面（首页 / 路径 / 练习 / 项目 / 算法）</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 6px 16px;"><b>Ctrl+Enter</b></td>
            <td style="padding: 6px 16px;">提交答案（练习模式）</td></tr>
        <tr><td style="padding: 6px 16px;"><b>Ctrl+N</b></td>
            <td style="padding: 6px 16px;">下一题（练习模式）</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 6px 16px;"><b>Ctrl+H</b></td>
            <td style="padding: 6px 16px;">查看提示（练习模式）</td></tr>
        <tr><td style="padding: 6px 16px;"><b>Ctrl+Shift+A</b></td>
            <td style="padding: 6px 16px;">向 AI 提问</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 6px 16px;"><b>Ctrl+T</b></td>
            <td style="padding: 6px 16px;">切换深色 / 浅色主题</td></tr>
        <tr><td style="padding: 6px 16px;"><b>Ctrl+/</b></td>
            <td style="padding: 6px 16px;">显示本快捷键帮助</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 6px 16px;"><b>Escape</b></td>
            <td style="padding: 6px 16px;">关闭弹出对话框</td></tr>
        <tr><td style="padding: 6px 16px;"><b>Tab</b></td>
            <td style="padding: 6px 16px;">在控件之间移动焦点</td></tr>
        </table>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("键盘快捷键帮助")
        msg.setTextFormat(Qt.RichText)
        msg.setText(f"<h3>键盘快捷键</h3>{shortcuts_html}")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()


def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLE)

    # Show splash screen while loading
    splash_label = QLabel(f"DevLearner AI\nv{APP_VERSION}\n正在加载...")
    splash_label.setAlignment(Qt.AlignCenter)
    splash_label.setStyleSheet(
        """
        QLabel {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eef4f8, stop:1 #edf6ff);
            color: #2563eb;
            font-size: 32px;
            font-weight: 700;
            font-family: 'Microsoft YaHei UI';
            border: 2px solid rgba(37,99,235,0.15);
            border-radius: 24px;
            padding: 50px 80px;
        }
        """
    )
    splash_label.setFixedSize(480, 300)
    splash = QSplashScreen(splash_label.grab())
    splash.show()
    app.processEvents()

    window = DevLearnerWindow()
    window.show()
    splash.finish(window)

    exit_code = app.exec()
    try:
        close_connection()
    except Exception:
        logger.debug("关闭数据库连接时出错", exc_info=True)
    sys.exit(exit_code)
