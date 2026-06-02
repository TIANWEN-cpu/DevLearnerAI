import logging

import mistune
from PyQt5.QtCore import QEvent, QSize, Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import (
    QComboBox,
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
from app.database import AppDatabase
from app.effects import optimize_scroll_widget, surface_panel
from app.localized_inputs import LocalizedLineEdit, LocalizedTextBrowser, LocalizedTextEdit
from app.reader_dialog import ReaderDialog
from app.styles import F_TITLE, FONT


class LearnWidget(QWidget):
    def __init__(self, content_service: ContentService, db: AppDatabase):
        super().__init__()
        self.content_service = content_service
        self.db = db
        self.markdown = mistune.create_markdown()
        self.current_track = self.content_service.tracks[0] if self.content_service.tracks else None
        self.current_module = None
        self.current_lesson = None
        self._lesson_id_order = []
        self._current_html = ""
        self.browser_cards = []
        optimize_scroll_widget(self)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 12, 18, 18)
        root.setSpacing(16)
        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_main_panel())
        splitter.setSizes([380, 1180])
        root.addWidget(splitter, 1)

        self.track_combo.currentIndexChanged.connect(self._change_track)
        self.search_input.textChanged.connect(self._refresh_browser)
        self.browser_list.itemClicked.connect(self._handle_browser_click)
        self.back_btn.clicked.connect(self._show_module_browser)
        self.complete_btn.clicked.connect(self._complete_current_lesson)
        self.prev_btn.clicked.connect(lambda: self._jump_relative(-1))
        self.next_btn.clicked.connect(lambda: self._jump_relative(1))
        self.save_note_btn.clicked.connect(self._save_note)
        self.reader_btn.clicked.connect(self._open_reader)
        self.bookmark_btn.clicked.connect(self._toggle_lesson_bookmark)
        self.search_notes_btn.clicked.connect(self._show_notes_search)
        self.learning_path_btn.clicked.connect(self._show_learning_path)

        if self.content_service.tracks:
            self._change_track(0)

    def select_track(self, track_id: str) -> None:
        for index in range(self.track_combo.count()):
            if self.track_combo.itemData(index) == track_id:
                self.track_combo.setCurrentIndex(index)
                return

    def _surface_panel(self) -> QFrame:
        return surface_panel(self)

    def _module_category_theme(self, module_key: str):
        module_key = module_key or ""
        if "foundations" in module_key:
            return "#2f6df6", "基础模块"
        if any(token in module_key for token in ["featured", "advanced", "application", "patterns", "oop", "stl"]):
            return "#8b5cf6", "精选模块"
        if any(token in module_key for token in ["interest", "integration", "network", "tools"]):
            return "#10b981", "兴趣模块"
        return "#94a3b8", "通用模块"

    def _build_header(self) -> QFrame:
        header = self._surface_panel()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(18)

        left = QVBoxLayout()
        title = QLabel("学习路径")
        title.setFont(QFont(FONT, F_TITLE - 4, QFont.Bold))
        subtitle = QLabel("按主线进入模块，再从模块里递进学习课程。")
        subtitle.setStyleSheet("color: #64748b; font-size: 18px;")
        subtitle.setWordWrap(True)
        left.addWidget(title)
        left.addWidget(subtitle)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        picker_label = QLabel("切换主线")
        picker_label.setStyleSheet("color: #64748b; font-size: 18px; font-weight: 600;")
        self.track_combo = QComboBox()
        self.track_combo.setToolTip("选择学习主线（技术栈）")
        for track in self.content_service.tracks:
            self.track_combo.addItem(f"{track.icon} {track.title}", track.id)
        self.track_combo.setMinimumWidth(280)
        self.track_stats = QLabel("")
        self.track_stats.setStyleSheet("color: #94a3b8; font-size: 16px;")
        right.addWidget(picker_label)
        right.addWidget(self.track_combo)
        right.addWidget(self.track_stats)
        layout.addLayout(right)
        return header

    def _build_left_panel(self) -> QFrame:
        panel = self._surface_panel()
        panel.setMinimumWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.track_summary = QLabel("")
        self.track_summary.setWordWrap(True)
        self.track_summary.setStyleSheet("color: #64748b; font-size: 18px;")
        layout.addWidget(self.track_summary)

        self.search_input = LocalizedLineEdit()
        self.search_input.setPlaceholderText("搜索当前主线里的模块")
        self.search_input.setToolTip("输入关键词搜索模块或课程")
        self.search_input.setAccessibleName("搜索模块")
        self.search_input.setAccessibleDescription("输入关键词搜索当前学习主线中的模块或课程")
        layout.addWidget(self.search_input)

        crumb_row = QHBoxLayout()
        self.back_btn = QPushButton("返回模块")
        self.back_btn.setProperty("variant", "secondary")
        self.back_btn.setToolTip("返回到模块列表视图")
        self.back_btn.hide()
        self.panel_title = QLabel("模块列表")
        self.panel_title.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 18px;")
        crumb_row.addWidget(self.back_btn)
        crumb_row.addWidget(self.panel_title)
        crumb_row.addStretch()
        layout.addLayout(crumb_row)

        self.browser_list = QListWidget()
        self.browser_list.setWordWrap(True)
        self.browser_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.browser_list.setSpacing(12)
        self.browser_list.setAccessibleName("模块和课程列表")
        self.browser_list.setAccessibleDescription("选择一个模块或课程进行学习")
        self.browser_list.setStyleSheet(
            """
            QListWidget { background: transparent; border: none; padding: 2px; }
            QListWidget::item { background: transparent; border: none; margin: 0; padding: 0; }
            QListWidget::item:selected { background: transparent; }
            """
        )
        layout.addWidget(self.browser_list, 1)

        self.left_helper = QLabel("")
        self.left_helper.setWordWrap(True)
        self.left_helper.setStyleSheet("color: #94a3b8; font-size: 16px;")
        layout.addWidget(self.left_helper)
        return panel

    def _build_main_panel(self) -> QFrame:
        panel = self._surface_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.meta_title = QLabel("学习地图")
        self.meta_title.setFont(QFont(FONT, F_TITLE - 8, QFont.Bold))
        self.meta_meta = QLabel("")
        self.meta_meta.setStyleSheet("color: #64748b; font-size: 17px; font-weight: 600;")
        layout.addWidget(self.meta_title)
        layout.addWidget(self.meta_meta)

        self.content_browser = LocalizedTextBrowser()
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.setMinimumHeight(520)
        self.content_browser.setAccessibleName("课程内容")
        self.content_browser.setAccessibleDescription("当前课程的详细内容")
        self.content_browser.viewport().installEventFilter(self)
        layout.addWidget(self.content_browser, 1)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.reader_btn = QPushButton("放大阅读")
        self.reader_btn.setProperty("variant", "secondary")
        self.reader_btn.setToolTip("在独立窗口中放大阅读课程内容")
        self.prev_btn = QPushButton("上一课")
        self.prev_btn.setProperty("variant", "secondary")
        self.prev_btn.setToolTip("切换到上一节课程")
        self.complete_btn = QPushButton("标记完成")
        self.complete_btn.setToolTip("将当前课程标记为已完成")
        self.next_btn = QPushButton("下一课")
        self.next_btn.setProperty("variant", "secondary")
        self.next_btn.setToolTip("切换到下一节课程")
        self.bookmark_btn = QPushButton("收藏课程")
        self.bookmark_btn.setProperty("variant", "secondary")
        self.bookmark_btn.setToolTip("收藏当前课程以便快速访问")
        self.bookmark_btn.setAccessibleName("收藏课程")
        self.learning_path_btn = QPushButton("学习路径")
        self.learning_path_btn.setProperty("variant", "secondary")
        self.learning_path_btn.setToolTip("查看当前技术栈的学习路径可视化")
        self.learning_path_btn.setAccessibleName("学习路径可视化")
        self.explain_btn = QPushButton("解释代码")
        self.explain_btn.setProperty("variant", "secondary")
        self.explain_btn.setToolTip("使用 AI 解释当前课程中的代码片段")
        self.explain_btn.setAccessibleName("解释代码")
        self.explain_btn.clicked.connect(self._explain_code)
        action_row.addWidget(self.reader_btn)
        action_row.addWidget(self.learning_path_btn)
        action_row.addWidget(self.explain_btn)
        action_row.addWidget(self.bookmark_btn)
        action_row.addWidget(self.prev_btn)
        action_row.addWidget(self.complete_btn)
        action_row.addWidget(self.next_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        note_card = self._surface_panel()
        note_layout = QVBoxLayout(note_card)
        note_layout.setContentsMargins(18, 16, 18, 16)
        note_layout.setSpacing(10)
        note_title = QLabel("学习侧记")
        note_title.setStyleSheet("font-weight: 700; color: #1c1c1e; font-size: 18px;")
        self.note_hint = QLabel("")
        self.note_hint.setStyleSheet("color: #64748b; font-size: 16px;")
        self.note_hint.setWordWrap(True)

        # Tags row
        tags_row = QHBoxLayout()
        tags_row.setSpacing(8)
        tags_label = QLabel("标签:")
        tags_label.setStyleSheet("color: #64748b; font-size: 16px; font-weight: 600;")
        self.tags_input = LocalizedLineEdit()
        self.tags_input.setPlaceholderText("用逗号分隔，如：函数,递归,重要")
        self.tags_input.setToolTip("为笔记添加标签，方便分类和搜索")
        self.tags_input.setAccessibleName("笔记标签")
        tags_row.addWidget(tags_label)
        tags_row.addWidget(self.tags_input)
        note_layout.addWidget(note_title)
        note_layout.addWidget(self.note_hint)
        note_layout.addLayout(tags_row)

        self.note_edit = LocalizedTextEdit()
        self.note_edit.setMinimumHeight(140)
        self.note_edit.setPlaceholderText("把关键结论、自己的理解和易错点记在这里。")
        self.note_edit.setAccessibleName("学习笔记")
        self.note_edit.setAccessibleDescription("记录当前课程的学习笔记和心得体会")
        note_layout.addWidget(self.note_edit)

        # Code snippets section
        code_label = QLabel("代码片段（可选）:")
        code_label.setStyleSheet("color: #64748b; font-size: 16px; font-weight: 600;")
        self.code_snippet_edit = LocalizedTextEdit()
        self.code_snippet_edit.setMinimumHeight(100)
        self.code_snippet_edit.setPlaceholderText("粘贴关键代码片段到这里...")
        self.code_snippet_edit.setAccessibleName("代码片段")
        self.code_snippet_edit.setAccessibleDescription("记录与课程相关的代码片段")
        note_layout.addWidget(code_label)
        note_layout.addWidget(self.code_snippet_edit)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch()
        self.search_notes_btn = QPushButton("搜索笔记")
        self.search_notes_btn.setProperty("variant", "secondary")
        self.search_notes_btn.setToolTip("搜索所有已保存的课程笔记")
        self.search_notes_btn.setAccessibleName("搜索笔记")
        row.addWidget(self.search_notes_btn)
        self.save_note_btn = QPushButton("保存笔记")
        self.save_note_btn.setProperty("variant", "secondary")
        self.save_note_btn.setToolTip("保存当前课程的学习笔记和代码片段")
        row.addWidget(self.save_note_btn)
        note_layout.addLayout(row)
        layout.addWidget(note_card)
        return panel

    def _apply_browser_card_style(self, card: QFrame, selected: bool, stripe: str) -> None:
        bg = "#edf4ff" if selected else "#f7f9fc"
        border = "rgba(37,99,235,0.18)" if selected else "rgba(15,23,42,0.08)"
        card.setObjectName("learnCard")
        card.setStyleSheet(
            f"""
            QFrame#learnCard {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff,
                    stop: 0.16 rgba(255,255,255,0.98),
                    stop: 1 {bg}
                );
                border: 1px solid {border};
                border-radius: 20px;
            }}
            QFrame#learnCard QFrame#learnAccentStripe {{
                background: {stripe};
                border: none;
                border-top-left-radius: 20px;
                border-bottom-left-radius: 20px;
            }}
            QFrame#learnCard QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )

    def _make_browser_card(self, title: str, meta: str, summary: str, stripe: str) -> QFrame:
        card = QFrame()
        self._apply_browser_card_style(card, False, stripe)

        outer = QHBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        accent = QFrame()
        accent.setObjectName("learnAccentStripe")
        accent.setFixedWidth(6)
        outer.addWidget(accent)

        body = QWidget()
        outer.addWidget(body, 1)

        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: #0f172a; font-weight: 700; font-size: 22px;")
        meta_label = QLabel(meta)
        meta_label.setWordWrap(True)
        meta_label.setStyleSheet("color: #64748b; font-size: 18px; font-weight: 600;")
        summary_label = QLabel(summary)
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet("color: #42556b; font-size: 18px;")
        layout.addWidget(title_label)
        layout.addWidget(meta_label)
        layout.addWidget(summary_label)
        return card

    def _refresh_browser_selection(self) -> None:
        current_item = self.browser_list.currentItem()
        for item, card in self.browser_cards:
            stripe = item.data(Qt.UserRole + 10) or "#94a3b8"
            self._apply_browser_card_style(card, item is current_item, stripe)

    def _change_track(self, index: int) -> None:
        if index < 0 or index >= len(self.content_service.tracks):
            return
        self.current_track = self.content_service.tracks[index]
        self.current_module = None
        self.current_lesson = None
        self.track_summary.setText(self.current_track.summary)
        self.track_stats.setText(
            f"共 {len(self.current_track.modules)} 个模块 · {len(self.current_track.lessons)} 节课程"
        )
        self._show_module_browser()

    def _show_module_browser(self) -> None:
        self.current_module = None
        self.current_lesson = None
        self.back_btn.hide()
        self.panel_title.setText("模块列表")
        self.left_helper.setText("先选一个模块进去，再看这一组课程。")
        self.meta_title.setText(f"{self.current_track.title} 学习地图")
        self.meta_meta.setText(
            f"{self.current_track.icon} 共 {len(self.current_track.modules)} 个模块 · {len(self.current_track.lessons)} 节课程"
        )
        overview = [
            f"# {self.current_track.title}",
            "",
            self.current_track.summary,
            "",
            "## 建议的学习方式",
            "- 先点一个模块进去，再挑这组课程里的第一节开始。",
            "- 学完一节立刻记一两句侧记，比囫囵吞全文更有效。",
            "- 如果卡住了，就回到模块层重新缩小范围。",
            "",
            "## 当前主线模块",
        ]
        for module in self.current_track.modules:
            overview.append(f"- **{module.title}**：{module.summary}")
        self._current_html = self.markdown("\n".join(overview))
        self.content_browser.setHtml(self._current_html)
        self.note_hint.setText("你现在看到的是主线总览，还没有进入具体课程。")
        self.note_edit.clear()
        self._refresh_browser()

    def _show_lesson_browser(self, module) -> None:
        self.current_module = module
        self.current_lesson = None
        self.back_btn.show()
        self.panel_title.setText("课程列表")
        self.left_helper.setText("这一栏只显示当前模块里的课程，阅读会清爽很多。")
        self.meta_title.setText(module.title)
        self.meta_meta.setText(f"{len(module.lessons)} 节课程 · {module.summary}")
        self._current_html = self.markdown(
            f"# {module.title}\n\n{module.summary}\n\n## 这组课怎么学\n- 先从第一节开始，把术语和心智模型打牢。\n- 每节课都做一条笔记，帮助你形成自己的表述。"
        )
        self.content_browser.setHtml(self._current_html)
        self.note_hint.setText("先进入一节具体课程，再针对那一课做侧记。")
        self.note_edit.clear()
        self._refresh_browser()

    def _refresh_browser(self) -> None:
        self.browser_list.clear()
        self.browser_cards = []
        query = self.search_input.text().strip().lower()
        if self.current_module is None:
            items = self.current_track.modules
            for module in items:
                haystack = f"{module.title} {module.summary}".lower()
                if query and query not in haystack:
                    continue
                stripe, category = self._module_category_theme(module.key)
                item = QListWidgetItem()
                item.setData(Qt.UserRole, ("module", module.key))
                item.setData(Qt.UserRole + 10, stripe)
                item.setSizeHint(QSize(0, 132))
                self.browser_list.addItem(item)
                card = self._make_browser_card(
                    module.title,
                    f"{category} · {len(module.lessons)} 节课程",
                    module.summary,
                    stripe,
                )
                self.browser_list.setItemWidget(item, card)
                self.browser_cards.append((item, card))
        else:
            lessons = self.current_module.lessons
            self._lesson_id_order = [lesson.id for lesson in lessons]
            for lesson in lessons:
                haystack = f"{lesson.title} {lesson.summary} {' '.join(lesson.tags)}".lower()
                if query and query not in haystack:
                    continue
                stripe, category = self._module_category_theme(self.current_module.key)
                item = QListWidgetItem()
                item.setData(Qt.UserRole, ("lesson", lesson.id))
                item.setData(Qt.UserRole + 10, stripe)
                item.setSizeHint(QSize(0, 150))
                self.browser_list.addItem(item)
                card = self._make_browser_card(
                    lesson.title,
                    f"{category} · {lesson.difficulty} · 预计 {lesson.estimated_minutes} 分钟",
                    lesson.summary,
                    stripe,
                )
                self.browser_list.setItemWidget(item, card)
                self.browser_cards.append((item, card))

    def _handle_browser_click(self, item: QListWidgetItem) -> None:
        kind, identifier = item.data(Qt.UserRole)
        self._refresh_browser_selection()
        if kind == "module":
            module = next((m for m in self.current_track.modules if m.key == identifier), None)
            if module:
                self._show_lesson_browser(module)
        elif kind == "lesson":
            self._open_lesson(identifier)

    def _open_lesson(self, lesson_id: str) -> None:
        try:
            result = self.content_service.lesson_by_id(lesson_id)
            if not result:
                return
            track, module, lesson = result
        except Exception as exc:
            logger.error("加载课程信息失败 [%s]: %s", lesson_id, exc, exc_info=True)
            return

        self.current_track = track
        self.current_module = module
        self.current_lesson = lesson
        self.meta_title.setText(lesson.title)
        self.meta_meta.setText(
            f"模块：{module.title} · 难度：{lesson.difficulty} · 预计 {lesson.estimated_minutes} 分钟 · 标签：{' / '.join(lesson.tags or ['入门'])}"
        )
        try:
            body = self.content_service.lesson_markdown(lesson)
        except Exception as exc:
            logger.error("加载课程内容失败 [%s]: %s", lesson_id, exc, exc_info=True)
            body = f"# {lesson.title}\n\n加载文档时出现错误。请检查课程文件是否存在，或尝试重启应用。"
        self._current_html = self.markdown(body)
        self.content_browser.setHtml(self._current_html)
        self.note_hint.setText("把关键结论、自己的理解和易错点记在这里，会比重读更有效。")
        # Load enhanced note (content, tags, code_snippets)
        try:
            note_data = self.db.load_enhanced_note(lesson.id)
            self.note_edit.setPlainText(note_data.get("content", ""))
            self.tags_input.setText(note_data.get("tags", ""))
            self.code_snippet_edit.setPlainText(note_data.get("code_snippets", ""))
        except Exception as exc:
            logger.warning("加载课程笔记失败 [%s]: %s", lesson_id, exc)
            self.note_edit.setPlainText("")
            self.tags_input.setText("")
            self.code_snippet_edit.setPlainText("")
        # Update bookmark state
        self._update_lesson_bookmark_state()

    def _jump_relative(self, step: int) -> None:
        if not self.current_lesson or not self._lesson_id_order:
            return
        try:
            idx = self._lesson_id_order.index(self.current_lesson.id)
        except ValueError:
            return
        new_idx = idx + step
        if 0 <= new_idx < len(self._lesson_id_order):
            self._open_lesson(self._lesson_id_order[new_idx])

    def _complete_current_lesson(self) -> None:
        if not self.current_lesson:
            return
        self.db.mark_lesson_completed(self.current_lesson.id, self.current_track.id)
        self.note_hint.setText("已标记完成。你可以继续下一课，或者回到模块层换一个方向。")
        # Check achievements
        unlocked = self.db.check_completion_achievements()
        streak_unlocked = self.db.check_streak_achievements()
        unlocked.extend(streak_unlocked)
        if unlocked:
            self._notify_achievements(unlocked)

    def _save_note(self) -> None:
        if not self.current_lesson:
            return
        content = self.note_edit.toPlainText()
        tags = self.tags_input.text().strip()
        code_snippets = self.code_snippet_edit.toPlainText()
        self.db.save_enhanced_note(self.current_lesson.id, content, tags, code_snippets)
        self.note_hint.setText("笔记已保存。继续用自己的话总结，会记得更牢。")
        # Check notes achievements
        self.db.check_notes_achievements()

    def _open_reader(self) -> None:
        if not self._current_html:
            return
        dialog = ReaderDialog(self.meta_title.text(), self._current_html, self.meta_meta.text(), self)
        dialog.exec_()

    def eventFilter(self, watched, event):
        if watched is self.content_browser.viewport() and event.type() == QEvent.MouseButtonDblClick:
            self._open_reader()
            return True
        return super().eventFilter(watched, event)

    # ── Bookmark methods ──────────────────────────────────────────────────────

    def _toggle_lesson_bookmark(self) -> None:
        """Toggle bookmark for the current lesson."""
        if not self.current_lesson:
            return
        lesson = self.current_lesson
        if self.db.is_bookmarked("lesson", lesson.id):
            self.db.remove_bookmark("lesson", lesson.id)
            self.bookmark_btn.setText("收藏课程")
        else:
            track_id = self.current_track.id if self.current_track else ""
            self.db.add_bookmark("lesson", lesson.id, lesson.title, track_id)
            self.bookmark_btn.setText("已收藏")
            self.db.check_bookmark_achievement()
        self.bookmark_btn.style().unpolish(self.bookmark_btn)
        self.bookmark_btn.style().polish(self.bookmark_btn)

    def _update_lesson_bookmark_state(self) -> None:
        """Update bookmark button for current lesson."""
        if not self.current_lesson:
            return
        if self.db.is_bookmarked("lesson", self.current_lesson.id):
            self.bookmark_btn.setText("已收藏")
        else:
            self.bookmark_btn.setText("收藏课程")

    # ── Learning path visualization ──────────────────────────────────────────

    def _show_learning_path(self) -> None:
        """Open learning path visualization dialog."""
        if not self.current_track:
            return
        from PyQt5.QtWidgets import QDialog, QVBoxLayout

        from app.widgets.learning_path import LearningPathWidget

        dialog = QDialog(self)
        dialog.setWindowTitle(f"学习路径 - {self.current_track.title}")
        dialog.setMinimumSize(800, 600)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        path_widget = LearningPathWidget(self.content_service, self.db, dialog)
        path_widget.set_track(self.current_track)
        path_widget.lesson_selected.connect(lambda lid: (self._open_lesson(lid), dialog.accept()))
        layout.addWidget(path_widget)
        dialog.exec_()

    # ── Code Explanation ───────────────────────────────────────────────────────

    def _explain_code(self) -> None:
        """Open code explanation for the current lesson content."""
        # Try to extract code from the current lesson content
        code = self._extract_code_from_content()
        if not code:
            # Fall back to the code snippet in the notes
            code = self.code_snippet_edit.toPlainText().strip()
        if not code:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "解释代码",
                "当前课程中未检测到代码块。\n你可以在笔记区的「代码片段」框中粘贴代码，然后再次点击。",
            )
            return

        language = self._detect_lesson_language()

        from PyQt5.QtWidgets import QDialog, QVBoxLayout

        from app.widgets.code_analyzer import CodeAnalyzerPanel

        dialog = QDialog(self)
        dialog.setWindowTitle("AI 代码解释")
        dialog.setMinimumSize(820, 660)
        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(0, 0, 0, 0)

        panel = CodeAnalyzerPanel(dialog)
        panel.set_code(code, language)
        dlg_layout.addWidget(panel)

        # Wire to AI mentor
        mentor_panel = self._find_mentor_panel()
        if mentor_panel:
            panel.analysis_requested.connect(
                lambda _atype, c, lang: self._dispatch_explanation(mentor_panel, panel, c, lang)
            )
        else:
            panel.set_analysis_error("未找到 AI 助手面板，请确保 AI 助手已打开并配置好 API。")

        dialog.exec_()

    def _extract_code_from_content(self) -> str:
        """Extract the first code block from the current lesson markdown content."""
        import re

        if not self.current_lesson:
            return ""
        try:
            body = self.content_service.lesson_markdown(self.current_lesson)
        except Exception:
            return ""
        # Extract fenced code blocks (``` ... ```)
        code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", body, re.DOTALL)
        if code_blocks:
            # Return the longest code block (likely the main example)
            return max(code_blocks, key=len).strip()
        return ""

    def _detect_lesson_language(self) -> str:
        """Detect the programming language from the current track."""
        if not self.current_track:
            return "python"
        lang_map = {
            "python": "python",
            "c": "c",
            "cplusplus": "cpp",
            "csharp": "csharp",
            "database": "sql",
        }
        return lang_map.get(self.current_track.id, "python")

    def _find_mentor_panel(self):
        """Walk up the widget tree to find an AIMentorPanel instance."""
        from app.ai.chat_handler import AIMentorPanel

        widget = self.parent()
        while widget:
            if isinstance(widget, AIMentorPanel):
                return widget
            for child in widget.findChildren(AIMentorPanel):
                return child
            widget = widget.parent()
        return None

    def _dispatch_explanation(self, mentor_panel, analyzer_panel, code, language):
        """Dispatch code explanation via the mentor panel's AI backend."""
        def _on_result(analysis_type, result):
            try:
                mentor_panel.code_analysis_ready.disconnect(_on_result)
            except (RuntimeError, TypeError):
                pass
            if result.get("success"):
                reply = result.get("reply", "")
                analyzer_panel.display_explanation(reply)
                analyzer_panel.set_analysis_complete()
            else:
                analyzer_panel.set_analysis_error(result.get("error", "解释失败"))

        mentor_panel.code_analysis_ready.connect(_on_result)
        mentor_panel.analyze_code_explanation(code, language)

    # ── Notes search ─────────────────────────────────────────────────────────

    def _show_notes_search(self) -> None:
        """Open a notes search dialog."""
        from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("搜索笔记")
        dialog.setMinimumSize(560, 440)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel("搜索所有课程笔记")
        title.setStyleSheet("font-weight: 700; font-size: 20px; color: #0f172a;")
        layout.addWidget(title)

        search_input = QLineEdit()
        search_input.setPlaceholderText("输入关键词搜索笔记内容和标签...")
        search_input.setAccessibleName("搜索笔记关键词")
        layout.addWidget(search_input)

        result_list = QListWidget()
        result_list.setStyleSheet("QListWidget { border: 1px solid #e2e8f0; border-radius: 12px; }")
        layout.addWidget(result_list, 1)

        def do_search():
            result_list.clear()
            query = search_input.text().strip()
            if not query:
                return
            results = self.db.search_notes(query)
            if not results:
                item = QListWidgetItem("没有找到匹配的笔记。")
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                result_list.addItem(item)
                return
            for lesson_id, content, tags, updated_at in results:
                preview = (content or "")[:80].replace("\n", " ")
                tag_text = f" [标签: {tags}]" if tags else ""
                item = QListWidgetItem(f"{lesson_id}{tag_text}\n{preview}\n更新: {updated_at}")
                item.setData(Qt.UserRole, lesson_id)
                result_list.addItem(item)

        search_input.textChanged.connect(do_search)

        def on_result_clicked(item):
            lesson_id = item.data(Qt.UserRole)
            if lesson_id:
                self._open_lesson(lesson_id)
                dialog.accept()

        result_list.itemClicked.connect(on_result_clicked)
        dialog.exec_()

    # ── Achievement notifications ────────────────────────────────────────────

    def _notify_achievements(self, achievement_ids: list) -> None:
        """Show achievement notification popups."""
        for aid in achievement_ids:
            ach_rows = self.db.list_achievements()
            ach = next((a for a in ach_rows if a["id"] == aid), None)
            if ach:
                from app.widgets.achievements import AchievementNotification

                top = self.window()
                notification = AchievementNotification(ach, top)
                geo = top.geometry()
                notification.move(geo.right() - 380, geo.top() + 60)
                notification.show()
                notification.closed.connect(notification.deleteLater)
