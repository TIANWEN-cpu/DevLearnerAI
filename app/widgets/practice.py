import logging
import threading
import time

from PyQt5.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.content_service import ContentService
from app.database import AppDatabase
from app.effects import optimize_scroll_widget, surface_panel
from app.highlighter import CLikeHighlighter, PythonHighlighter, SqlHighlighter
from app.i18n import tr
from app.localized_inputs import LocalizedCodeEditor, LocalizedTextEdit
from app.practice_service import PracticeService
from app.python_runner import run_python_code
from app.styles import (
    ACCENT,
    ACCENT_SOFT,
    BG_CARD,
    BG_CARD_SOFT,
    BORDER,
    F_CODE,
    F_SUB,
    F_TITLE,
    FONT,
    MONO_FONT,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUB,
    WARNING,
    score_color,
    score_label,
)


class PracticeWidget(QWidget):
    run_ready = pyqtSignal(object)
    evaluation_ready = pyqtSignal(object)

    def __init__(
        self,
        content_service: ContentService,
        practice_service: PracticeService,
        db: AppDatabase,
    ):
        super().__init__()
        self.content_service = content_service
        self.practice_service = practice_service
        self.db = db
        self.current_exercise = None
        self.start_time = 0.0
        self.busy_mode = None
        self._loading_exercise = False
        self.topic_map = {}
        self.exercise_cards = []

        self.draft_timer = QTimer(self)
        self.draft_timer.setSingleShot(True)
        self.draft_timer.setInterval(800)
        self.draft_timer.timeout.connect(self._save_current_draft)

        optimize_scroll_widget(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.setSpacing(18)
        layout.addWidget(self._build_hero())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_center_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([320, 840, 320])
        layout.addWidget(splitter, 1)

        self.track_combo.currentIndexChanged.connect(self.refresh_exercises)
        self.diff_combo.currentIndexChanged.connect(self.refresh_exercises)
        self.topic_combo.currentIndexChanged.connect(self.refresh_exercises)
        self.exercise_list.currentRowChanged.connect(self.load_exercise)
        self.hint_btn.clicked.connect(self.show_hint)
        self.run_btn.clicked.connect(self.run_code)
        self.check_btn.clicked.connect(self.evaluate_code)
        self.editor.textChanged.connect(self._schedule_draft_save)
        self.run_ready.connect(self._handle_run_ready)
        self.evaluation_ready.connect(self._handle_evaluation_ready)

        self.refresh_exercises()

    def _surface_panel(self) -> QFrame:
        return surface_panel(self, bg=BG_CARD, border=BORDER)

    def _build_hero(self) -> QFrame:
        hero = self._surface_panel()
        hero.setStyleSheet(
            f"""
            QFrame {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {BG_CARD},
                    stop: 0.46 {BG_CARD_SOFT},
                    stop: 1 #e7f2ff
                );
                border: 1px solid {BORDER};
                border-radius: 24px;
            }}
            """
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 20, 22, 20)
        hero_layout.setSpacing(16)

        left = QVBoxLayout()
        badge = QLabel(tr("practice.badge"))
        badge.setStyleSheet(
            f"""
            QLabel {{
                background: {ACCENT_SOFT};
                border: 1px solid rgba(255,255,255,0.94);
                border-radius: 12px;
                padding: 10px 16px;
                color: {ACCENT};
                font-weight: 700;
            }}
            """
        )
        badge.setFixedWidth(128)
        title = QLabel(tr("practice.title"))
        title.setFont(QFont(FONT, F_TITLE - 2, QFont.Bold))
        subtitle = QLabel(tr("practice.subtitle"))
        subtitle.setStyleSheet(f"color: {TEXT_SUB}; font-size: 21px;")
        subtitle.setWordWrap(True)
        left.addWidget(badge)
        left.addWidget(title)
        left.addWidget(subtitle)
        hero_layout.addLayout(left, 1)

        filter_box = QFrame()
        filter_box.setStyleSheet(
            f"""
            QFrame {{
                background: rgba(255, 253, 248, 0.88);
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            """
        )
        filter_layout = QVBoxLayout(filter_box)
        filter_layout.setContentsMargins(14, 12, 14, 12)
        filter_layout.setSpacing(6)
        filter_title = QLabel("筛选")
        filter_title.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN};")
        filter_layout.addWidget(filter_title)

        row = QHBoxLayout()
        row.setSpacing(8)
        track_label = QLabel("\u8def\u7ebf:")
        track_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self.track_combo = QComboBox()
        self.track_combo.setToolTip("\u6309\u6280\u672f\u6808\u7b5b\u9009\u7ec3\u4e60")
        self.track_combo.setAccessibleName("\u5b66\u4e60\u8def\u7ebf\u7b5b\u9009")
        self.track_combo.setAccessibleDescription("\u6309\u6280\u672f\u6808\u7b5b\u9009\u7ec3\u4e60\u9898\u76ee")
        self.track_combo.addItem("\u5168\u90e8\u8def\u7ebf", "all")
        for track in self.content_service.tracks:
            self.track_combo.addItem(track.title, track.id)

        diff_label = QLabel("\u96be\u5ea6:")
        diff_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self.diff_combo = QComboBox()
        self.diff_combo.setToolTip("\u6309\u96be\u5ea6\u7b5b\u9009\u7ec3\u4e60")
        self.diff_combo.setAccessibleName("\u96be\u5ea6\u7b5b\u9009")
        self.diff_combo.setAccessibleDescription("\u6309\u96be\u5ea6\u7b5b\u9009\u7ec3\u4e60\u9898\u76ee")
        self.diff_combo.addItem("\u5168\u90e8\u96be\u5ea6", "all")
        self.diff_combo.addItem("\u57fa\u7840", "\u57fa\u7840")
        self.diff_combo.addItem("\u8fdb\u9636", "\u8fdb\u9636")
        self.diff_combo.addItem("\u7efc\u5408", "\u7efc\u5408")
        self.diff_combo.addItem("\u7cbe\u9009", "\u7cbe\u9009")
        self.diff_combo.addItem("\u5174\u8da3", "\u5174\u8da3")
        topic_label = QLabel("\u4e13\u9898:")
        topic_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self.topic_combo = QComboBox()
        self.topic_combo.setToolTip("\u6309\u4e13\u9898\u7b5b\u9009\u7ec3\u4e60")
        self.topic_combo.setAccessibleName("\u4e13\u9898\u7b5b\u9009")
        self.topic_combo.setAccessibleDescription("\u6309\u4e13\u9898\u7b5b\u9009\u7ec3\u4e60\u9898\u76ee")
        self.topic_combo.addItem("\u5168\u90e8\u4e13\u9898", "all")
        row.addWidget(track_label)
        row.addWidget(self.track_combo)
        row.addWidget(diff_label)
        row.addWidget(self.diff_combo)
        row.addWidget(topic_label)
        row.addWidget(self.topic_combo)
        filter_layout.addLayout(row)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("\u641c\u7d22\u9898\u76ee\u540d\u79f0\u6216\u63cf\u8ff0...")
        self.search_input.setToolTip("\u8f93\u5165\u5173\u952e\u8bcd\u641c\u7d22\u7ec3\u4e60\u9898\u76ee")
        self.search_input.setAccessibleName("\u641c\u7d22\u7ec3\u4e60\u9898\u76ee")
        self.search_input.setAccessibleDescription(
            "\u8f93\u5165\u5173\u952e\u8bcd\u641c\u7d22\u7ec3\u4e60\u9898\u76ee\u540d\u79f0\u6216\u63cf\u8ff0"
        )
        self.search_input.setStyleSheet(
            f"QLineEdit {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; padding: 8px 14px; color: {TEXT_MAIN}; font-size: 13px; }}"
        )
        self.search_input.textChanged.connect(self.refresh_exercises)
        filter_layout.addWidget(self.search_input)

        self.exercise_count = QLabel("")
        self.exercise_count.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px;")
        filter_layout.addWidget(self.exercise_count)
        hero_layout.addWidget(filter_box)
        return hero

    def _build_left_panel(self) -> QFrame:
        panel = self._surface_panel()
        panel.setMinimumWidth(240)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("题目列表")
        title.setFont(QFont(FONT, F_SUB, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        layout.addWidget(title)

        self.exercise_list = QListWidget()
        self.exercise_list.setSpacing(10)
        self.exercise_list.setAccessibleName("练习题目列表")
        self.exercise_list.setAccessibleDescription("选择一道练习题目开始作答")
        self.exercise_list.setStyleSheet(
            """
            QListWidget {
                background: transparent;
                border: none;
                padding: 2px;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                margin: 0;
                padding: 0;
            }
            QListWidget::item:selected {
                background: transparent;
            }
            """
        )
        layout.addWidget(self.exercise_list, 1)
        return panel

    def _build_center_panel(self) -> QFrame:
        panel = self._surface_panel()
        panel.setMinimumWidth(620)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        prompt_title = QLabel("题目说明")
        prompt_title.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN};")
        self.prompt_box = LocalizedTextEdit()
        self.prompt_box.setReadOnly(True)
        self.prompt_box.setMinimumHeight(180)
        self.prompt_box.setAccessibleName("题目说明")
        self.prompt_box.setAccessibleDescription("当前练习题目的描述和要求")

        editor_title = QLabel("代码编辑区")
        editor_title.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN};")
        self.editor = LocalizedCodeEditor()
        self.editor.setFont(QFont(MONO_FONT, F_CODE))
        self.editor.setAccessibleName("代码编辑区")
        self.editor.setAccessibleDescription("在此编写代码解答当前练习题目")
        self.editor.setStyleSheet(
            """
            QPlainTextEdit {
                background: #f7fbff;
                border: 1px solid rgba(37,99,235,0.18);
                border-radius: 16px;
                padding: 18px 18px 18px 10px;
                selection-background-color: rgba(37,99,235,0.18);
            }
            QPlainTextEdit:focus {
                border: 2px solid rgba(37,99,235,0.34);
                background: #ffffff;
            }
            """
        )
        self.highlighter = PythonHighlighter(self.editor.document())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.hint_btn = QPushButton("\u67e5\u770b\u63d0\u793a")
        self.hint_btn.setProperty("variant", "secondary")
        self.hint_btn.setToolTip(
            "\u9010\u6b65\u663e\u793a\u63d0\u793a\uff0c\u6bcf\u6b21\u70b9\u51fb\u5c55\u5f00\u4e00\u6761 (Ctrl+H)"
        )
        self.hint_btn.setAccessibleName("\u67e5\u770b\u63d0\u793a")
        self.hint_btn.setAccessibleDescription(
            "\u9010\u6b65\u663e\u793a\u63d0\u793a\uff0c\u6bcf\u6b21\u70b9\u51fb\u5c55\u5f00\u4e00\u6761 (Ctrl+H)"
        )
        self.progressive_hint_btn = QPushButton("\u6e10\u8fdb\u63d0\u793a")
        self.progressive_hint_btn.setProperty("variant", "secondary")
        self.progressive_hint_btn.setToolTip(
            "\u6253\u5f003\u7ea7\u6e10\u8fdb\u63d0\u793a\u9762\u677f\uff1a\u6982\u5ff5\u63d0\u793a\u3001\u601d\u8def\u63d0\u793a\u3001\u4f2a\u4ee3\u7801\u63d0\u793a"
        )
        self.progressive_hint_btn.setAccessibleName("\u6e10\u8fdb\u63d0\u793a")
        self.progressive_hint_btn.clicked.connect(self._open_hint_system_dialog)
        self.analyze_btn = QPushButton("\u5206\u6790\u4ee3\u7801")
        self.analyze_btn.setProperty("variant", "secondary")
        self.analyze_btn.setToolTip(
            "\u4f7f\u7528 AI \u5206\u6790\u5f53\u524d\u4ee3\u7801\uff0c\u83b7\u53d6\u89e3\u91ca\u3001\u5ba1\u67e5\u548c Bug \u68c0\u6d4b"
        )
        self.analyze_btn.setAccessibleName("\u5206\u6790\u4ee3\u7801")
        self.analyze_btn.setAccessibleDescription(
            "\u4f7f\u7528 AI \u5206\u6790\u5f53\u524d\u4ee3\u7801\uff0c\u83b7\u53d6\u89e3\u91ca\u3001\u5ba1\u67e5\u548c Bug \u68c0\u6d4b"
        )
        self.analyze_btn.clicked.connect(self._open_code_analyzer)
        self.run_btn = QPushButton("\u8fd0\u884c\u4ee3\u7801")
        self.run_btn.setProperty("variant", "secondary")
        self.run_btn.setToolTip("\u5728\u9694\u79bb\u6c99\u7bb1\u4e2d\u8fd0\u884c\u4ee3\u7801\u67e5\u770b\u8f93\u51fa")
        self.run_btn.setAccessibleName("\u8fd0\u884c\u4ee3\u7801")
        self.run_btn.setAccessibleDescription(
            "\u5728\u9694\u79bb\u6c99\u7bb1\u4e2d\u8fd0\u884c\u4ee3\u7801\u67e5\u770b\u8f93\u51fa"
        )
        self.reset_btn = QPushButton("\u91cd\u7f6e\u4ee3\u7801")
        self.reset_btn.setProperty("variant", "secondary")
        self.reset_btn.setToolTip("\u6062\u590d\u5230\u9898\u76ee\u521d\u59cb\u4ee3\u7801")
        self.reset_btn.setAccessibleName("\u91cd\u7f6e\u4ee3\u7801")
        self.reset_btn.setAccessibleDescription("\u6062\u590d\u5230\u9898\u76ee\u521d\u59cb\u4ee3\u7801")
        self.reset_btn.clicked.connect(self._reset_code)
        self.check_btn = QPushButton("\u63d0\u4ea4\u5e76\u5224\u9898")
        self.check_btn.setMinimumWidth(180)
        self.check_btn.setToolTip("\u63d0\u4ea4\u4ee3\u7801\u8fdb\u884c\u81ea\u52a8\u8bc4\u6d4b (Ctrl+Enter)")
        self.check_btn.setAccessibleName("\u63d0\u4ea4\u5e76\u5224\u9898")
        self.check_btn.setAccessibleDescription(
            "\u63d0\u4ea4\u4ee3\u7801\u8fdb\u884c\u81ea\u52a8\u8bc4\u6d4b (Ctrl+Enter)"
        )
        btn_row.addWidget(self.hint_btn)
        btn_row.addWidget(self.progressive_hint_btn)
        btn_row.addWidget(self.reset_btn)
        btn_row.addWidget(self.analyze_btn)
        btn_row.addWidget(self.run_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.check_btn)
        self.action_layout = btn_row

        layout.addWidget(prompt_title)
        layout.addWidget(self.prompt_box)
        layout.addWidget(editor_title)
        layout.addWidget(self.editor, 1)
        layout.addLayout(btn_row)
        return panel

    def _build_right_panel(self) -> QFrame:
        panel = self._surface_panel()
        panel.setMinimumWidth(260)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        guide_box = QGroupBox("当前练习信息")
        guide_layout = QVBoxLayout(guide_box)
        self.lesson_link = QLabel("")
        self.lesson_link.setWordWrap(True)
        self.lesson_link.setStyleSheet(f"color: {ACCENT}; font-weight: 700;")
        self.guide_label = QLabel("选择一道题开始。")
        self.guide_label.setWordWrap(True)
        self.guide_label.setStyleSheet(f"color: {TEXT_SUB};")
        self.draft_status = QLabel("")
        self.draft_status.setWordWrap(True)
        self.draft_status.setStyleSheet(f"color: {TEXT_MUTED};")
        guide_layout.addWidget(self.lesson_link)
        guide_layout.addWidget(self.guide_label)
        guide_layout.addWidget(self.draft_status)

        # Bookmark and hint tracking row
        bm_row = QHBoxLayout()
        bm_row.setSpacing(8)
        self.bookmark_btn = QPushButton("收藏此题")
        self.bookmark_btn.setProperty("variant", "secondary")
        self.bookmark_btn.setFixedHeight(36)
        self.bookmark_btn.setCursor(Qt.PointingHandCursor)
        self.bookmark_btn.setToolTip("收藏当前练习题以便快速访问")
        self.bookmark_btn.setAccessibleName("收藏练习")
        self.bookmark_btn.clicked.connect(self._toggle_exercise_bookmark)
        bm_row.addWidget(self.bookmark_btn)
        self.hint_usage_label = QLabel("")
        self.hint_usage_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px;")
        bm_row.addWidget(self.hint_usage_label)
        bm_row.addStretch()
        guide_layout.addLayout(bm_row)

        # Delayed hint timer display
        self.hint_timer_label = QLabel("")
        self.hint_timer_label.setStyleSheet(f"color: {WARNING}; font-size: 14px; font-weight: 600;")
        self.hint_timer_label.setVisible(False)
        guide_layout.addWidget(self.hint_timer_label)

        layout.addWidget(guide_box)

        # Score visualization card
        self.score_card = QFrame()
        self.score_card.setStyleSheet(
            f"""
            QFrame {{
                background: {BG_CARD_SOFT};
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
            """
        )
        score_layout = QVBoxLayout(self.score_card)
        score_layout.setContentsMargins(16, 14, 16, 14)
        score_layout.setSpacing(8)

        score_title = QLabel("得分")
        score_title.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN};")
        score_layout.addWidget(score_title)

        self.score_display = QLabel("--")
        self.score_display.setAlignment(Qt.AlignCenter)
        self.score_display.setFont(QFont(FONT, F_TITLE - 8, QFont.Bold))
        self.score_display.setStyleSheet(f"color: {TEXT_MUTED};")
        self.score_display.setAccessibleName("得分显示")
        self.score_display.setAccessibleDescription("当前练习的得分")
        score_layout.addWidget(self.score_display)

        self.score_label_display = QLabel("")
        self.score_label_display.setAlignment(Qt.AlignCenter)
        self.score_label_display.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px;")
        self.score_label_display.setAccessibleName("得分等级")
        score_layout.addWidget(self.score_label_display)

        self.score_bar = QProgressBar()
        self.score_bar.setFixedHeight(10)
        self.score_bar.setTextVisible(False)
        self.score_bar.setValue(0)
        self.score_bar.setAccessibleName("得分进度条")
        self.score_bar.setAccessibleDescription("当前练习得分的可视化进度")
        score_layout.addWidget(self.score_bar)

        layout.addWidget(self.score_card)

        self.run_group = QGroupBox("运行输出")
        run_layout = QVBoxLayout(self.run_group)
        self.output_box = LocalizedTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setMinimumHeight(180)
        self.output_box.setAccessibleName("运行输出")
        self.output_box.setAccessibleDescription("代码运行的标准输出结果")
        run_layout.addWidget(self.output_box)
        layout.addWidget(self.run_group)

        # Inline test results area
        self.test_results_group = QGroupBox("测试用例结果")
        test_results_layout = QVBoxLayout(self.test_results_group)
        self.test_results_box = LocalizedTextEdit()
        self.test_results_box.setReadOnly(True)
        self.test_results_box.setMinimumHeight(100)
        self.test_results_box.setAccessibleName("测试用例结果")
        self.test_results_box.setAccessibleDescription("各测试用例的通过或失败状态")
        test_results_layout.addWidget(self.test_results_box)
        self.test_results_group.setVisible(False)
        layout.addWidget(self.test_results_group)

        self.feedback_group = QGroupBox("判题反馈")
        feedback_layout = QVBoxLayout(self.feedback_group)
        self.feedback_box = LocalizedTextEdit()
        self.feedback_box.setReadOnly(True)
        self.feedback_box.setAccessibleName("判题反馈")
        self.feedback_box.setAccessibleDescription("代码提交后的评分和反馈信息")
        feedback_layout.addWidget(self.feedback_box)
        layout.addWidget(self.feedback_group, 1)
        return panel

    def refresh_exercises(self) -> None:
        track_id = self.track_combo.currentData()
        difficulty = self.diff_combo.currentData()
        search_text = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""
        self._refresh_topic_combo(track_id)
        topic_id = self.topic_combo.currentData()
        exercises = self.practice_service.filtered(track_id, difficulty)
        if topic_id and topic_id != "all":
            exercises = [exercise for exercise in exercises if self._exercise_topic_key(exercise) == topic_id]
        if search_text:
            exercises = [
                exercise
                for exercise in exercises
                if search_text in exercise.title.lower() or search_text in exercise.prompt.lower()
            ]
        self.exercise_count.setText(f"当前筛选下共有 {len(exercises)} 道练习。")
        self.exercise_list.clear()
        self.exercise_cards = []
        for exercise in exercises:
            self._add_exercise_item(exercise)
        if self.exercise_list.count():
            self.exercise_list.setCurrentRow(0)
        else:
            self.current_exercise = None
            self.prompt_box.clear()
            self.editor.clear()
            self.output_box.clear()
            self.feedback_box.clear()
            self.lesson_link.clear()
            self.guide_label.setText(
                "\u5f53\u524d\u7b5b\u9009\u6761\u4ef6\u4e0b\u6ca1\u6709\u9898\u76ee\u3002\u8bd5\u8bd5\uff1a\n"
                "1) \u5207\u6362\u5b66\u4e60\u8def\u7ebf  2) \u9009\u62e9\u5168\u90e8\u96be\u5ea6  3) \u6e05\u9664\u641c\u7d22\u5173\u952e\u8bcd"
            )
            self.draft_status.clear()

    def _refresh_topic_combo(self, track_id: str) -> None:
        current = self.topic_combo.currentData()
        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()
        self.topic_combo.addItem("全部专题", "all")

        topics = {}
        for exercise in self.practice_service.exercises:
            if track_id != "all" and exercise.track_id != track_id:
                continue
            key = self._exercise_topic_key(exercise)
            title = self._exercise_topic_title(exercise)
            if key and key not in topics:
                topics[key] = title

        for key, title in sorted(topics.items(), key=lambda item: item[1]):
            self.topic_combo.addItem(title, key)

        if current:
            for index in range(self.topic_combo.count()):
                if self.topic_combo.itemData(index) == current:
                    self.topic_combo.setCurrentIndex(index)
                    break
        self.topic_combo.blockSignals(False)

    def _exercise_topic_key(self, exercise) -> str:
        payload = self.content_service.lesson_by_id(exercise.lesson_id)
        if not payload:
            return exercise.track_id
        _track, module, _lesson = payload
        return module.id

    def _exercise_topic_title(self, exercise) -> str:
        payload = self.content_service.lesson_by_id(exercise.lesson_id)
        if not payload:
            return "未分类专题"
        _track, module, _lesson = payload
        return module.title

    def _exercise_track_theme(self, track_id: str):
        themes = {
            "python": ("#2f6df6", "#f7f9fc", "#f1f5f9", "rgba(15,23,42,0.08)"),
            "c": ("#ff4f8a", "#f7f9fc", "#f1f5f9", "rgba(15,23,42,0.08)"),
            "cplusplus": ("#659ad2", "#f7f9fc", "#f1f5f9", "rgba(15,23,42,0.08)"),
            "csharp": ("#8b5cf6", "#f7f9fc", "#f1f5f9", "rgba(15,23,42,0.08)"),
            "database": ("#f59e0b", "#f7f9fc", "#f1f5f9", "rgba(15,23,42,0.08)"),
            "algo": ("#84cc16", "#f7f9fc", "#f1f5f9", "rgba(15,23,42,0.08)"),
            "algorithms": ("#84cc16", "#f7f9fc", "#f1f5f9", "rgba(15,23,42,0.08)"),
            "integration": ("#fb7185", "#f7f9fc", "#f1f5f9", "rgba(15,23,42,0.08)"),
        }
        return themes.get(track_id, ("#94a3b8", "#f7f9fc", "#f1f5f9", "rgba(15,23,42,0.08)"))

    def _make_exercise_card(self, exercise) -> QFrame:
        topic_title = self._exercise_topic_title(exercise)
        card = QFrame()
        stripe, bg, selected_bg, border = self._exercise_track_theme(exercise.track_id)
        self._apply_exercise_card_style(card, False, stripe, bg, border, selected_bg)

        outer = QHBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        accent_stripe = QFrame()
        accent_stripe.setObjectName("exerciseAccentStripe")
        accent_stripe.setFixedWidth(6)
        outer.addWidget(accent_stripe)

        body = QWidget()
        outer.addWidget(body, 1)

        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)

        gloss = QFrame()
        gloss.setObjectName("exerciseCardGloss")
        gloss.setFixedHeight(12)
        layout.addWidget(gloss)

        title = QLabel(exercise.title)
        title.setWordWrap(True)
        title.setStyleSheet("color: #0f172a; font-weight: 700; font-size: 19px;")
        track = self.content_service.track_by_id(exercise.track_id)
        track_title = track.title if track else exercise.track_id
        meta = QLabel(f"{track_title} · {topic_title} · {exercise.difficulty}")
        meta.setWordWrap(True)
        meta.setStyleSheet("color: #64748b; font-size: 16px; font-weight: 600;")
        summary = QLabel(
            (exercise.prompt or "").replace("\n", " ")[:74]
            + ("…" if len((exercise.prompt or "").replace("\n", " ")) > 74 else "")
        )
        summary.setWordWrap(True)
        summary.setStyleSheet("color: #4f637a; font-size: 16px;")

        layout.addWidget(title)
        layout.addWidget(meta)
        layout.addWidget(summary)
        return card

    def _apply_exercise_card_style(
        self,
        card: QFrame,
        selected: bool,
        stripe: str = "#2f6df6",
        bg: str = "#f7f9fc",
        border: str = "rgba(15,23,42,0.08)",
        selected_bg: str = "#edf4ff",
    ) -> None:
        paint_bg = selected_bg if selected else bg
        paint_border = "rgba(37,99,235,0.18)" if selected else border
        card.setObjectName("exerciseCard")
        card.setStyleSheet(
            f"""
            QFrame#exerciseCard {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff,
                    stop: 0.18 rgba(255,255,255,0.98),
                    stop: 1 {paint_bg}
                );
                border: 1px solid {paint_border};
                border-radius: 20px;
            }}
            QFrame#exerciseCard QFrame#exerciseAccentStripe {{
                background: {stripe};
                border: none;
                border-top-left-radius: 20px;
                border-bottom-left-radius: 20px;
            }}
            QFrame#exerciseCard QFrame#exerciseCardGloss {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(255,255,255,0.95),
                    stop: 1 rgba(255,255,255,0.0)
                );
                border: none;
                border-radius: 12px;
                max-height: 12px;
            }}
            QFrame#exerciseCard QLabel {{
                background: transparent;
                border: none;
            }}
            """
        )

    def _add_exercise_item(self, exercise) -> None:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, exercise.id)
        stripe, bg, selected_bg, border = self._exercise_track_theme(exercise.track_id)
        item.setData(Qt.UserRole + 10, stripe)
        item.setData(Qt.UserRole + 11, bg)
        item.setData(Qt.UserRole + 12, selected_bg)
        item.setData(Qt.UserRole + 13, border)
        item.setSizeHint(QSize(0, 164))
        self.exercise_list.addItem(item)
        card = self._make_exercise_card(exercise)
        self.exercise_list.setItemWidget(item, card)
        self.exercise_cards.append((item, card))

    def _refresh_exercise_card_selection(self) -> None:
        current_item = self.exercise_list.currentItem()
        for item, card in self.exercise_cards:
            stripe = item.data(Qt.UserRole + 10) or "#94a3b8"
            bg = item.data(Qt.UserRole + 11) or "#f7f9fc"
            selected_bg = item.data(Qt.UserRole + 12) or "#eef2f6"
            border = item.data(Qt.UserRole + 13) or "rgba(15,23,42,0.08)"
            self._apply_exercise_card_style(card, item is current_item, stripe, bg, border, selected_bg)

    def _apply_editor_mode(self, track_id: str) -> None:
        if hasattr(self, "highlighter") and self.highlighter:
            self.highlighter.setDocument(None)
            self.highlighter.deleteLater()
        if track_id == "database":
            self.highlighter = SqlHighlighter(self.editor.document())
        elif track_id == "c":
            self.highlighter = CLikeHighlighter("c", self.editor.document())
        elif track_id == "cplusplus":
            self.highlighter = CLikeHighlighter("cplusplus", self.editor.document())
        elif track_id == "csharp":
            self.highlighter = CLikeHighlighter("csharp", self.editor.document())
        else:
            self.highlighter = PythonHighlighter(self.editor.document())

    def _reset_code(self) -> None:
        if not self.current_exercise:
            return
        reply = QMessageBox.question(
            self,
            "\u786e\u8ba4\u91cd\u7f6e",
            "\u786e\u5b9a\u8981\u91cd\u7f6e\u4ee3\u7801\u5230\u521d\u59cb\u72b6\u6001\u5417\uff1f\u5f53\u524d\u7f16\u8f91\u5185\u5bb9\u5c06\u4e22\u5931\u3002",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.editor.setPlainText(self.current_exercise.starter_code)
        self.draft_status.setText("\u4ee3\u7801\u5df2\u91cd\u7f6e\u4e3a\u521d\u59cb\u72b6\u6001\u3002")

    def show_hint(self) -> None:
        """Show hint with progressive delay system."""
        if not self.current_exercise:
            return
        hints = self.current_exercise.hints or ["这道题没有额外提示，先把输入输出和边界情况想清楚。"]
        if not hasattr(self, "_hint_index"):
            self._hint_index = 0
        if self._hint_index >= len(hints):
            # All hints already shown
            self._reveal_hint()
            return
        # First hint is immediate, subsequent hints have a short delay
        if self._hint_index == 0:
            self._reveal_hint()
        else:
            self._start_hint_delay()

    def _schedule_draft_save(self) -> None:
        if self._loading_exercise or not self.current_exercise:
            return
        self.draft_status.setText("草稿待保存...")
        self.draft_timer.start()

    def _save_current_draft(self) -> None:
        if not self.current_exercise:
            return
        code = self.editor.toPlainText()
        self.db.save_exercise_draft(
            exercise_id=self.current_exercise.id,
            exercise_title_snapshot=self.current_exercise.title,
            code_snapshot=code,
        )
        self.draft_status.setText("草稿已自动保存到本地。")

    def _set_action_state(self, busy: bool, mode: str = "") -> None:
        self.busy_mode = mode if busy else None
        self.hint_btn.setEnabled(not busy)
        self.progressive_hint_btn.setEnabled(not busy)
        self.analyze_btn.setEnabled(not busy)
        self.run_btn.setEnabled(not busy)
        self.check_btn.setEnabled(not busy)
        self.run_btn.setText("运行中..." if busy and mode == "run" else "运行代码")
        self.check_btn.setText("判题中..." if busy and mode == "evaluate" else "提交并判题")

    def run_code(self) -> None:
        if not self.current_exercise:
            return
        if self.current_exercise.track_id in {"database", "c", "csharp"}:
            self.output_box.setPlainText("这类题当前不在应用内直接运行，先提交判题即可。")
            return

        self._save_current_draft()
        code = self.editor.toPlainText()
        self._set_action_state(True, "run")
        self.output_box.setPlainText(
            "\u6b63\u5728\u9694\u79bb\u73af\u5883\u4e2d\u8fd0\u884c\u4ee3\u7801\uff0c\u8bf7\u7b49\u5019..."
        )
        self._run_thread = threading.Thread(target=self._run_code_worker, args=(code,), daemon=True)
        self._run_thread.start()
        # Stop and disconnect any previous timeout timer before creating a new one
        if hasattr(self, "_run_timeout_timer") and self._run_timeout_timer:
            self._run_timeout_timer.stop()
            try:
                self._run_timeout_timer.timeout.disconnect(self._handle_run_timeout)
            except (RuntimeError, TypeError):
                pass
        self._run_timeout_timer = QTimer(self)
        self._run_timeout_timer.setSingleShot(True)
        self._run_timeout_timer.timeout.connect(self._handle_run_timeout)
        self._run_timeout_timer.start(10000)
        # Clean up any previous cancel button before creating a new one
        if hasattr(self, "cancel_btn") and self.cancel_btn:
            self.cancel_btn.deleteLater()
        self.cancel_btn = QPushButton("\u53d6\u6d88\u8fd0\u884c", self)
        self.cancel_btn.setStyleSheet(
            "QPushButton { background: #ef4444; color: white; border: none; border-radius: 12px; padding: 8px 16px; font-size: 13px; }"
        )
        self.cancel_btn.clicked.connect(self._cancel_run)
        self.action_layout.addWidget(self.cancel_btn)

    def _cancel_run(self) -> None:
        if hasattr(self, "_run_timeout_timer"):
            self._run_timeout_timer.stop()
        if hasattr(self, "cancel_btn") and self.cancel_btn:
            self.cancel_btn.deleteLater()
        self._set_action_state(False)
        self.output_box.setPlainText("\u8fd0\u884c\u5df2\u53d6\u6d88\u3002")

    def _handle_run_timeout(self) -> None:
        if hasattr(self, "cancel_btn") and self.cancel_btn:
            self.cancel_btn.deleteLater()
        self._set_action_state(False)
        self.output_box.setPlainText(
            "\u8fd0\u884c\u8d85\u65f6\uff0810 \u79d2\uff09\uff0c\u53ef\u80fd\u5b58\u5728\u6b7b\u5faa\u73af\u6216\u957f\u65f6\u95f4\u64cd\u4f5c\u3002"
        )

    def _run_code_worker(self, code: str) -> None:
        try:
            result = run_python_code(code)
        except Exception as exc:
            logger.error("代码运行过程发生异常: %s", exc, exc_info=True)
            result = {"ok": False, "error": f"运行环境出错: {exc}", "stdout": ""}
        self.run_ready.emit(result)

    def _handle_run_ready(self, result) -> None:
        if hasattr(self, "_run_timeout_timer"):
            self._run_timeout_timer.stop()
        if hasattr(self, "cancel_btn") and self.cancel_btn:
            self.cancel_btn.deleteLater()
        self._set_action_state(False)
        if result.get("ok"):
            output = result.get("stdout", "").strip() or "(没有标准输出)"
            self.output_box.setPlainText(f"运行成功：\n{output}")
            # Show a brief success indicator in feedback
            self.feedback_box.setPlainText("代码运行正常。如果结果符合预期，可以点击「提交并判题」进行正式评测。")
            return
        error = result.get("error", "未知错误")
        # User-friendly error message
        if "SyntaxError" in error:
            friendly = "语法错误：代码中有拼写或格式问题，请检查括号、冒号和缩进。"
        elif "IndentationError" in error:
            friendly = "缩进错误：请检查代码的缩进层级是否一致。"
        elif "NameError" in error:
            friendly = "名称错误：使用了未定义的变量或函数名，请检查拼写。"
        elif "TypeError" in error:
            friendly = "类型错误：对不兼容的类型进行了操作，请检查变量类型。"
        elif "Timeout" in error or "超时" in error:
            friendly = "运行超时：代码执行时间过长，可能存在死循环。"
        else:
            friendly = f"运行时错误：{error}"
        self.output_box.setPlainText(f"运行失败：\n{friendly}\n\n原始信息：\n{error}")

    def evaluate_code(self) -> None:
        if not self.current_exercise:
            return

        self._save_current_draft()
        exercise = self.current_exercise
        code = self.editor.toPlainText()
        started_at = self.start_time or time.time()
        self._set_action_state(True, "evaluate")
        self.feedback_box.setPlainText("正在隔离环境中判题，请稍候...")
        threading.Thread(
            target=self._evaluate_worker,
            args=(exercise, code, started_at),
            daemon=True,
        ).start()

    def _evaluate_worker(self, exercise, code: str, started_at: float) -> None:
        try:
            result = self.practice_service.evaluate(exercise, code)
        except Exception as exc:
            logger.error("评测过程发生异常: %s", exc, exc_info=True)
            from app.practice.models import EvaluationResult

            result = EvaluationResult(
                passed=False,
                score=0,
                feedback_lines=[f"评测过程出错: {exc}。请检查代码后重试。"],
                duration_sec=int(time.time() - started_at),
            )
        elapsed = int(time.time() - started_at)
        self.evaluation_ready.emit((exercise.id, exercise.title, exercise.track_id, code, result, elapsed))

    def _handle_evaluation_ready(self, payload) -> None:
        exercise_id, exercise_title, track_id, code_snapshot, result, elapsed = payload
        self._set_action_state(False)

        self.db.record_attempt(
            exercise_id=exercise_id,
            exercise_title_snapshot=exercise_title,
            track_id=track_id,
            code_snapshot=code_snapshot,
            score=result.score,
            passed=result.passed,
            duration_sec=elapsed or result.duration_sec,
            feedback=result.feedback_text,
        )

        if not self.current_exercise or self.current_exercise.id != exercise_id:
            return

        # Score visualization
        color = score_color(result.score)
        self.score_display.setText(str(result.score))
        self.score_display.setStyleSheet(f"color: {color};")
        self.score_label_display.setText(
            f"{score_label(result.score)} | {'通过' if result.passed else '未通过'} | 用时 {elapsed}s"
        )
        self.score_label_display.setStyleSheet(f"color: {color}; font-size: 18px;")
        self.score_bar.setValue(result.score)
        self.score_bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; border-radius: 5px; }}")

        # Inline test case results
        if hasattr(result, "test_results") and result.test_results:
            self.test_results_group.setVisible(True)
            lines = []
            for i, tc in enumerate(result.test_results, 1):
                status = "通过" if tc.get("passed") else "未通过"
                icon = "+" if tc.get("passed") else "x"
                lines.append(f"[{icon}] 用例 {i}: {status}")
                if tc.get("input"):
                    lines.append(f"    输入: {tc['input']}")
                if tc.get("expected"):
                    lines.append(f"    期望: {tc['expected']}")
                if tc.get("actual"):
                    lines.append(f"    实际: {tc['actual']}")
            self.test_results_box.setPlainText("\n".join(lines))
        else:
            self.test_results_group.setVisible(False)

        # Feedback
        lines = [
            f"得分：{result.score}/100 ({score_label(result.score)})",
            f"是否通过：{'通过' if result.passed else '未通过'}",
            f"用时：{elapsed} 秒",
            "",
            "反馈：",
            result.feedback_text,
        ]
        if result.stdout:
            self.output_box.setPlainText(result.stdout)
        elif result.passed:
            self.output_box.setPlainText("本次判题没有额外标准输出。")
        self.feedback_box.setPlainText("\n".join(lines))

        # Check achievements after evaluation
        unlocked = self.db.check_practice_achievements()
        if result.passed:
            streak_unlocked = self.db.check_streak_achievements()
            unlocked.extend(streak_unlocked)
        if unlocked:
            self._notify_achievements(unlocked)

    # ── Code Analyzer ─────────────────────────────────────────────────────────

    def _open_hint_system_dialog(self) -> None:
        """Open the progressive hint system dialog for the current exercise."""
        if not self.current_exercise:
            return

        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QDialog, QShortcut, QVBoxLayout

        from app.widgets.hint_system import HintSystemWidget

        dialog = QDialog(self)
        dialog.setWindowTitle(f"渐进提示 - {self.current_exercise.title}")
        dialog.setMinimumSize(560, 480)
        dialog.setAccessibleName("渐进提示对话框")
        QShortcut(QKeySequence(Qt.Key_Escape), dialog, dialog.close)
        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(12, 12, 12, 12)

        hint_widget = HintSystemWidget(self.db, dialog)
        hints = self.current_exercise.hints or []
        hint_widget.set_exercise(self.current_exercise.id, hints)
        dlg_layout.addWidget(hint_widget)

        dialog.exec_()

    def _open_code_analyzer(self) -> None:
        """Open code analyzer dialog for the current editor code."""
        code = self.editor.toPlainText()
        if not code.strip():
            self.feedback_box.setPlainText("请先写一些代码，再使用分析功能。")
            return
        track_id = self.current_exercise.track_id if self.current_exercise else "python"
        language_map = {
            "python": "python",
            "c": "c",
            "cplusplus": "cpp",
            "csharp": "csharp",
            "database": "sql",
        }
        language = language_map.get(track_id, "python")

        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QDialog, QShortcut, QVBoxLayout

        from app.widgets.code_analyzer import CodeAnalyzerPanel

        dialog = QDialog(self)
        dialog.setWindowTitle("AI 代码分析")
        dialog.setMinimumSize(820, 660)
        dialog.setAccessibleName("AI 代码分析对话框")
        QShortcut(QKeySequence(Qt.Key_Escape), dialog, dialog.close)
        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setContentsMargins(0, 0, 0, 0)

        panel = CodeAnalyzerPanel(dialog)
        panel.set_code(code, language)
        dlg_layout.addWidget(panel)

        # Wire analysis requests to the AI mentor panel if available
        mentor_panel = self._find_mentor_panel()
        if mentor_panel:
            panel.analysis_requested.connect(
                lambda _atype, c, lang: self._dispatch_analysis(mentor_panel, panel, c, lang)
            )
        else:
            panel.set_analysis_error("未找到 AI 助手面板，请确保 AI 助手已打开并在设置中配置好 API。")

        dialog.exec_()

    def _find_mentor_panel(self):
        """Walk up the widget tree to find an AIMentorPanel instance."""
        from app.ai.chat_handler import AIMentorPanel

        widget = self.parent()
        while widget:
            if isinstance(widget, AIMentorPanel):
                return widget
            # Also check children for dock-based panels
            for child in widget.findChildren(AIMentorPanel):
                return child
            widget = widget.parent()
        return None

    def _dispatch_analysis(self, mentor_panel, analyzer_panel, code, language):
        """Dispatch code analysis via the mentor panel's AI backend."""

        def _on_result(analysis_type, result):
            try:
                mentor_panel.code_analysis_ready.disconnect(_on_result)
            except (RuntimeError, TypeError):
                pass
            if result.get("success"):
                reply = result.get("reply", "")
                analyzer_panel.display_explanation(reply)
                analyzer_panel.display_review(reply)
                analyzer_panel.display_bugs(reply)
                analyzer_panel.set_analysis_complete()
            else:
                analyzer_panel.set_analysis_error(result.get("error", "分析失败"))

        mentor_panel.code_analysis_ready.connect(_on_result)
        mentor_panel.analyze_code_explanation(code, language)

    # ── Bookmark methods ──────────────────────────────────────────────────────

    def _toggle_exercise_bookmark(self) -> None:
        """Toggle bookmark for the current exercise."""
        if not self.current_exercise:
            return
        ex = self.current_exercise
        if self.db.is_bookmarked("exercise", ex.id):
            self.db.remove_bookmark("exercise", ex.id)
            self.bookmark_btn.setText("收藏此题")
            self.bookmark_btn.setProperty("variant", "secondary")
        else:
            self.db.add_bookmark("exercise", ex.id, ex.title, ex.track_id)
            self.bookmark_btn.setText("已收藏")
            self.bookmark_btn.setProperty("variant", "primary")
            self.db.check_bookmark_achievement()
        self.bookmark_btn.style().unpolish(self.bookmark_btn)
        self.bookmark_btn.style().polish(self.bookmark_btn)

    def _update_bookmark_state(self) -> None:
        """Update bookmark button appearance based on current exercise."""
        if not self.current_exercise:
            return
        if self.db.is_bookmarked("exercise", self.current_exercise.id):
            self.bookmark_btn.setText("已收藏")
        else:
            self.bookmark_btn.setText("收藏此题")

    def _update_hint_usage_display(self) -> None:
        """Update hint usage count label."""
        if not self.current_exercise:
            self.hint_usage_label.setText("")
            return
        count = self.db.hint_usage_count(self.current_exercise.id)
        self.hint_usage_label.setText(f"已用 {count} 次提示" if count > 0 else "")

    # ── Delayed hint timer ────────────────────────────────────────────────────

    def _start_hint_delay(self) -> None:
        """Start a countdown timer before showing the hint."""
        if not hasattr(self, "_hint_delay_timer"):
            self._hint_delay_timer = QTimer(self)
            self._hint_delay_timer.setSingleShot(True)
            self._hint_delay_timer.timeout.connect(self._on_hint_delay_complete)
        self._hint_delay_seconds = 5
        self.hint_timer_label.setText(f"提示将在 {self._hint_delay_seconds} 秒后显示...")
        self.hint_timer_label.setVisible(True)
        self.hint_btn.setEnabled(False)
        if not hasattr(self, "_hint_countdown"):
            self._hint_countdown = QTimer(self)
            self._hint_countdown.setInterval(1000)
            self._hint_countdown.timeout.connect(self._tick_hint_countdown)
        self._hint_countdown.start()
        self._hint_delay_timer.start(5000)

    def _tick_hint_countdown(self) -> None:
        self._hint_delay_seconds = max(0, self._hint_delay_seconds - 1)
        if self._hint_delay_seconds > 0:
            self.hint_timer_label.setText(f"提示将在 {self._hint_delay_seconds} 秒后显示...")
        else:
            self._hint_countdown.stop()

    def _on_hint_delay_complete(self) -> None:
        """Called when hint delay timer completes."""
        if hasattr(self, "_hint_countdown"):
            self._hint_countdown.stop()
        self.hint_timer_label.setVisible(False)
        self.hint_btn.setEnabled(True)
        self._reveal_hint()

    def _reveal_hint(self) -> None:
        """Actually reveal the next progressive hint."""
        if not self.current_exercise:
            return
        hints = self.current_exercise.hints or ["这道题没有额外提示，先把输入输出和边界情况想清楚。"]
        if not hasattr(self, "_hint_index"):
            self._hint_index = 0
        self._hint_index = min(self._hint_index, len(hints) - 1)
        # Record hint usage
        self.db.record_hint_usage(self.current_exercise.id, self._hint_index)
        shown = hints[: self._hint_index + 1]
        remaining = len(hints) - self._hint_index - 1
        text = "提示（逐步揭示）：\n" + "\n".join(f"- {item}" for item in shown)
        if remaining > 0:
            text += f"\n\n还有 {remaining} 条提示，再次点击「查看提示」可继续展开。"
        else:
            text += "\n\n已显示全部提示。"
        self.feedback_box.setPlainText(text)
        self._hint_index = min(self._hint_index + 1, len(hints) - 1)
        self._update_hint_usage_display()

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

    def load_exercise(self, _row: int) -> None:
        item = self.exercise_list.currentItem()
        if not item:
            return
        self._refresh_exercise_card_selection()
        exercise = self.practice_service.exercise_by_id(item.data(Qt.UserRole))
        if not exercise:
            return

        self.current_exercise = exercise
        self._hint_index = 0  # Reset progressive hint index
        self._apply_editor_mode(exercise.track_id)
        self.start_time = time.time()
        self._loading_exercise = True
        self.prompt_box.setPlainText(exercise.prompt)
        draft = self.db.load_exercise_draft(exercise.id)
        code_text = draft[1] if draft and draft[1] else exercise.starter_code
        self.editor.setPlainText(code_text)
        self._loading_exercise = False

        lesson_info = self.content_service.lesson_by_id(exercise.lesson_id)
        lesson_title = lesson_info[2].title if lesson_info else "未绑定课程"
        self.lesson_link.setText(f"关联课程：{lesson_title}")
        self.guide_label.setText(
            f"路线：{exercise.track_id}  |  难度：{exercise.difficulty}\n建议先自己完整做一遍，再查看提示和反馈。"
        )
        if draft and draft[1]:
            self.draft_status.setText("已恢复上次草稿，继续写就行。")
        else:
            self.draft_status.setText("当前还没有本地草稿。")
        self.output_box.setPlainText("还没有运行输出。")
        self.feedback_box.setPlainText("还没有判题反馈。")
        self._update_bookmark_state()
        self._update_hint_usage_display()
        self.hint_timer_label.setVisible(False)
