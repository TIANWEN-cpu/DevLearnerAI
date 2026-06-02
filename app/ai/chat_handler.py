"""Chat handler: AIMentorPanel and AIMentorDock UI classes."""

import json
import logging
import threading
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# ── Coaching mode constants ──────────────────────────────────────────────────

COACHING_MODE_STANDARD = "standard"
COACHING_MODE_COACHING = "coaching"

_COACHING_SYSTEM_PROMPT = (
    "你现在处于苏格拉底式教练模式。不要直接给出答案，而是：\n"
    "1. 通过引导性提问帮助学生自己发现答案\n"
    "2. 如果学生犯了错误，用反问引导他们思考为什么这里会出错\n"
    "3. 对学生的正确思路给予肯定，并鼓励他们继续深入\n"
    "4. 在学生卡住时，只给一个小小的线索，然后继续提问\n"
    "5. 分析学生的学习模式（喜欢速解还是深思、是否经常跳步等），适时给出个性化建议\n"
    "6. 每次回答的结构：先一个引导问题，再一小段提示，再一个跟进问题\n"
    "记住：你的目标不是给出答案，而是引导学生自己找到答案。用中文回答。"
)

_LEARNING_PATTERN_ANALYSIS_PROMPT = (
    "根据学生的对话和练习历史，分析其学习模式：\n"
    "- 学习风格：速解型/深思型/实验型\n"
    "- 常见弱点：概念理解/代码实现/调试能力\n"
    "- 学习建议：基于分析给出2-3条具体建议\n"
    "请简要分析，不超过150字。"
)

from app.ai.api_client import (
    fetch_models as api_fetch_models,
)
from app.ai.api_client import (
    send_chat as api_send_chat,
)
from app.ai.api_client import (
    send_chat_stream as api_send_chat_stream,
)
from app.ai.api_client import (
    test_connection as api_test_connection,
)
from app.ai.markdown_renderer import bubble_html as _bubble_html
from app.content_service import ContentService
from app.database import AppDatabase
from app.effects import AnimatedDotsLabel, LoadingSpinner
from app.localized_inputs import (
    LocalizedLineEdit,
    LocalizedTextBrowser,
    LocalizedTextEdit,
)
from app.styles import (
    BG_CARD,
    BG_CARD_SOFT,
    BORDER,
    TEXT_MAIN,
    TEXT_SUB,
)

logger = logging.getLogger(__name__)


def _card_style(radius: int = 20) -> str:
    return f"QFrame {{background: {BG_CARD};border: 1px solid {BORDER};border-radius: {radius}px;}}"


class AIMentorPanel(QWidget):
    request_open_page = pyqtSignal()
    request_open_dock = pyqtSignal()
    response_ready = pyqtSignal(int)
    models_ready = pyqtSignal(list)
    status_ready = pyqtSignal(str)
    stream_chunk_ready = pyqtSignal(str)  # streaming text chunk
    code_analysis_ready = pyqtSignal(str, dict)  # (analysis_type, result_dict)

    def __init__(
        self,
        db: AppDatabase,
        content_service: ContentService,
        mode: str = "dock",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.db = db
        self.content_service = content_service
        self.mode = mode
        self.current_session_id: Optional[int] = None
        self.settings_dialog: Optional[QDialog] = None
        self._request_in_flight: bool = False
        self._is_valid: bool = True
        self._coaching_mode: str = COACHING_MODE_STANDARD

        self.response_ready.connect(self._handle_response_ready)
        self.models_ready.connect(self._populate_models)
        self.status_ready.connect(self._set_settings_status)
        self.stream_chunk_ready.connect(self._handle_stream_chunk)
        self.code_analysis_ready.connect(self._handle_code_analysis_result)

        self._build_ui()
        self._build_settings_widgets()
        self._load_initial_state()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        if self.mode == "page":
            root.setContentsMargins(4, 4, 4, 4)
            root.setSpacing(10)
        else:
            root.setContentsMargins(10, 10, 10, 10)
            root.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        title = QLabel("AI 工作台" if self.mode == "page" else "AI 助手")
        title.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN}; font-size: 22px;")
        top_bar.addWidget(title)
        top_bar.addStretch()

        self.settings_btn = QPushButton("AI 设置")
        self.settings_btn.setProperty("variant", "secondary")
        self.settings_btn.clicked.connect(self._open_settings_dialog)
        top_bar.addWidget(self.settings_btn)

        self.mode_btn = QPushButton("打开侧边助手" if self.mode == "page" else "展开为独立页面")
        self.mode_btn.setProperty("variant", "secondary")
        self.mode_btn.clicked.connect(self._toggle_mode)
        top_bar.addWidget(self.mode_btn)
        root.addLayout(top_bar)

        subtitle = QLabel(
            "把课程疑问、报错分析和项目拆解放到不同会话里，聊天记录会在侧栏和工作台之间同步。"
            if self.mode == "page"
            else "这里保留轻量会话和快捷提问，详细设置都放在 AI 设置里。"
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SUB}; font-size: 16px;")
        root.addWidget(subtitle)

        if self.mode == "page":
            splitter = QSplitter(Qt.Horizontal)
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(8)
            splitter.addWidget(self._build_session_panel())
            splitter.addWidget(self._build_chat_panel())
            splitter.setSizes([330, 1040])
            root.addWidget(splitter, 1)
        else:
            root.addWidget(self._build_compact_session_row())
            root.addWidget(self._build_chat_panel(), 1)

    def _build_session_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(_card_style(22))
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("会话")
        title.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN};")
        helper = QLabel("把问题按主题拆成不同会话，后面回看会轻松很多。")
        helper.setWordWrap(True)
        helper.setStyleSheet(f"color: {TEXT_SUB}; font-size: 15px;")
        layout.addWidget(title)
        layout.addWidget(helper)

        self.session_list = QListWidget()
        self.session_list.setWordWrap(True)
        self.session_list.setSpacing(6)
        self.session_list.setStyleSheet(
            f"""
            QListWidget {{
                background: #fffefb;
                border: 1px solid {BORDER};
                border-radius: 18px;
                padding: 8px;
            }}
            QListWidget::item {{
                border-radius: 14px;
                padding: 10px 12px;
                margin: 0;
            }}
            QListWidget::item:selected {{
                background: rgba(37, 99, 235, 0.12);
                color: #0f172a;
            }}
            """
        )
        self.session_list.currentRowChanged.connect(self._on_session_row_changed)
        layout.addWidget(self.session_list, 1)

        row1 = QHBoxLayout()
        self.new_session_btn = QPushButton("新建")
        self.new_session_btn.setProperty("variant", "secondary")
        self.rename_session_btn = QPushButton("重命名")
        self.rename_session_btn.setProperty("variant", "secondary")
        row1.addWidget(self.new_session_btn)
        row1.addWidget(self.rename_session_btn)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.delete_session_btn = QPushButton("删除")
        self.delete_session_btn.setProperty("variant", "secondary")
        self.focus_session_btn = QPushButton("设为当前")
        self.focus_session_btn.setProperty("variant", "secondary")
        row2.addWidget(self.delete_session_btn)
        row2.addWidget(self.focus_session_btn)
        layout.addLayout(row2)

        self.session_summary_label = QLabel("当前会话的摘要会显示在这里。")
        self.session_summary_label.setWordWrap(True)
        self.session_summary_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 15px;")
        layout.addWidget(self.session_summary_label)

        self.new_session_btn.clicked.connect(self._create_session)
        self.rename_session_btn.clicked.connect(self._rename_session)
        self.delete_session_btn.clicked.connect(self._delete_session)
        self.focus_session_btn.clicked.connect(self._focus_current_session)
        return panel

    def _build_compact_session_row(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(_card_style(18))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(10)
        title = QLabel("当前会话")
        title.setStyleSheet("font-weight: 700;")
        row.addWidget(title)
        self.session_combo = QComboBox()
        self.session_combo.currentIndexChanged.connect(self._on_session_combo_changed)
        row.addWidget(self.session_combo, 1)
        self.new_session_btn = QPushButton("新建")
        self.new_session_btn.setProperty("variant", "secondary")
        self.new_session_btn.clicked.connect(self._create_session)
        row.addWidget(self.new_session_btn)
        layout.addLayout(row)

        self.session_summary_label = QLabel("当前会话的摘要会显示在这里。")
        self.session_summary_label.setWordWrap(True)
        self.session_summary_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 14px;")
        layout.addWidget(self.session_summary_label)
        return card

    def _build_chat_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(_card_style(22))
        self.chat_layout = QVBoxLayout(panel)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(12)

        self.chat_title = QLabel("默认对话")
        self.chat_title.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN};")
        self.chat_layout.addWidget(self.chat_title)

        self.chat_meta = QLabel("聊天记录会在侧边栏和独立工作台之间同步。")
        self.chat_meta.setWordWrap(True)
        self.chat_meta.setStyleSheet(f"color: {TEXT_SUB}; font-size: 15px;")
        self.chat_layout.addWidget(self.chat_meta)

        self.chat = LocalizedTextBrowser()
        self.chat.setOpenExternalLinks(True)
        self.chat.setMinimumHeight(620 if self.mode == "page" else 420)
        self.chat.setStyleSheet(
            f"""
            QTextBrowser {{
                background: {BG_CARD_SOFT};
                border: 1px solid {BORDER};
                border-radius: 18px;
                padding: 18px;
            }}
            """
        )
        self.chat_layout.addWidget(self.chat, 1)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        for label, prompt in [
            ("解释当前课程", "结合我当前打开的课程，帮我解释这一节最重要的三个知识点。"),
            ("分析当前代码", "帮我分析我现在这段代码或报错，先讲思路，再说如何修改。"),
            ("拆解当前项目", "把我当前这个项目拆成 5 个最小可执行步骤，并告诉我应该先做哪一步。"),
        ]:
            button = QPushButton(label)
            button.setProperty("variant", "secondary")
            button.clicked.connect(lambda _checked=False, p=prompt: self._seed_prompt(p))
            quick_row.addWidget(button)
        self.chat_layout.addLayout(quick_row)

        # Code analysis quick row
        code_row = QHBoxLayout()
        code_row.setSpacing(8)
        code_row_label = QLabel("代码分析：")
        code_row_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 13px; font-weight: 600;")
        code_row.addWidget(code_row_label)
        for label, atype in [
            ("解释代码", "explanation"),
            ("代码审查", "review"),
            ("Bug 检测", "bug_detection"),
        ]:
            button = QPushButton(label)
            button.setProperty("variant", "secondary")
            button.setToolTip(f"对剪贴板或最近提交的代码进行{label}")
            button.clicked.connect(lambda _checked=False, t=atype: self._quick_code_analysis(t))
            code_row.addWidget(button)
        code_row.addStretch()
        self.chat_layout.addLayout(code_row)

        # Coaching mode toggle row
        coaching_row = QHBoxLayout()
        coaching_row.setSpacing(8)
        coaching_label = QLabel("AI 教练模式：")
        coaching_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 13px; font-weight: 600;")
        coaching_row.addWidget(coaching_label)

        self.coaching_btn = QPushButton("标准模式")
        self.coaching_btn.setProperty("variant", "secondary")
        self.coaching_btn.setFixedHeight(32)
        self.coaching_btn.setCursor(Qt.PointingHandCursor)
        self.coaching_btn.setToolTip("切换到苏格拉底式教练模式：AI 通过引导性提问帮助你自主思考")
        self.coaching_btn.clicked.connect(self._toggle_coaching_mode)
        coaching_row.addWidget(self.coaching_btn)

        self.learning_pattern_btn = QPushButton("分析学习模式")
        self.learning_pattern_btn.setProperty("variant", "secondary")
        self.learning_pattern_btn.setFixedHeight(32)
        self.learning_pattern_btn.setCursor(Qt.PointingHandCursor)
        self.learning_pattern_btn.setToolTip("AI 根据你的学习和练习历史分析学习风格和弱点")
        self.learning_pattern_btn.clicked.connect(self._analyze_learning_pattern)
        coaching_row.addWidget(self.learning_pattern_btn)

        coaching_row.addStretch()
        self.chat_layout.addLayout(coaching_row)

        self.thinking_hint = QLabel("")
        self.thinking_hint.setWordWrap(True)
        self.thinking_hint.setVisible(False)
        self.thinking_hint.setStyleSheet(
            f"""
            QLabel {{
                background: rgba(37, 99, 235, 0.08);
                border: 1px solid rgba(37, 99, 235, 0.14);
                border-radius: 12px;
                padding: 8px 12px;
                color: {TEXT_SUB};
                font-size: 14px;
            }}
            """
        )
        # Loading indicator row
        self.loading_row = QHBoxLayout()
        self.loading_row.setSpacing(8)
        self.spinner = LoadingSpinner(size=24)
        self.spinner.hide()
        self.loading_dots = AnimatedDotsLabel("AI thinking")
        self.loading_dots.hide()
        self.loading_row.addWidget(self.spinner)
        self.loading_row.addWidget(self.loading_dots, 1)

        # Retry button (hidden by default)
        self.retry_btn = QPushButton("retry")
        self.retry_btn.setProperty("variant", "secondary")
        self.retry_btn.setFixedHeight(40)
        self.retry_btn.hide()
        self.retry_btn.clicked.connect(self.retry_last_message)
        self.loading_row.addWidget(self.retry_btn)

        self.chat_layout.addWidget(self.thinking_hint)
        self.chat_layout.addLayout(self.loading_row)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.input = LocalizedLineEdit()
        self.input.setPlaceholderText("把课程疑问、报错信息、项目卡点或学习计划发给 AI 助手")
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_message)
        self.input.returnPressed.connect(self.send_message)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_btn)
        self.chat_layout.addLayout(input_row)
        return panel

    def _build_settings_widgets(self) -> None:
        self.config_card = self._build_config_card()
        self.knowledge_card = self._build_knowledge_card()

    def _build_config_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(_card_style(20))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("模型连接设置")
        title.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN};")
        desc = QLabel("这里保存模型接口配置，方便你在不同页面和不同会话之间复用。")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SUB}; font-size: 16px;")
        layout.addWidget(title)
        layout.addWidget(desc)

        layout.addWidget(QLabel("API Host"))
        self.host_input = LocalizedLineEdit()
        self.host_input.setPlaceholderText("https://api.openai.com/v1")
        layout.addWidget(self.host_input)

        layout.addWidget(QLabel("API Key"))
        self.key_input = LocalizedLineEdit()
        self.key_input.setEchoMode(2)
        self.key_input.setPlaceholderText("sk-...")
        layout.addWidget(self.key_input)

        layout.addWidget(QLabel("模型"))
        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.fetch_btn = QPushButton("获取模型")
        self.fetch_btn.setProperty("variant", "secondary")
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.fetch_btn)
        layout.addLayout(model_row)

        action_row = QHBoxLayout()
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setProperty("variant", "secondary")
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setProperty("variant", "secondary")
        action_row.addWidget(self.save_btn)
        action_row.addWidget(self.test_btn)
        layout.addLayout(action_row)

        self.settings_status = QLabel("连接测试和模型获取的结果会显示在这里，不会写进聊天记录。")
        self.settings_status.setWordWrap(True)
        self.settings_status.setStyleSheet(f"color: {TEXT_SUB}; font-size: 15px;")
        layout.addWidget(self.settings_status)

        self.fetch_btn.clicked.connect(self.fetch_models)
        self.save_btn.clicked.connect(self.save_config)
        self.test_btn.clicked.connect(self.test_connection)
        return card

    def _build_knowledge_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(_card_style(20))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("知识库设置")
        title.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN};")
        desc = QLabel("基础知识来自课程，个性知识来自你的学习记录，扩展知识来自你主动添加的文件。")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SUB}; font-size: 16px;")
        layout.addWidget(title)
        layout.addWidget(desc)

        self.base_cb = QCheckBox("启用基础知识库")
        self.personal_cb = QCheckBox("启用个性知识库")
        self.custom_cb = QCheckBox("启用扩展文件知识库")
        for checkbox in (self.base_cb, self.personal_cb, self.custom_cb):
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self._save_workspace_flags)
            layout.addWidget(checkbox)

        file_title = QLabel("扩展文件列表")
        file_title.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN};")
        layout.addWidget(file_title)

        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(220)
        self.file_list.itemSelectionChanged.connect(self._refresh_kb_preview)
        layout.addWidget(self.file_list)

        file_actions = QHBoxLayout()
        self.add_file_btn = QPushButton("添加文件")
        self.add_file_btn.setProperty("variant", "secondary")
        self.remove_file_btn = QPushButton("移除文件")
        self.remove_file_btn.setProperty("variant", "secondary")
        file_actions.addWidget(self.add_file_btn)
        file_actions.addWidget(self.remove_file_btn)
        layout.addLayout(file_actions)

        self.kb_preview_title = QLabel("知识库总览")
        self.kb_preview_title.setStyleSheet("font-weight: 700; color: #0f172a;")
        layout.addWidget(self.kb_preview_title)

        self.kb_preview_meta = QLabel("没有选中文件时，这里会显示当前启用的知识库摘要。")
        self.kb_preview_meta.setWordWrap(True)
        self.kb_preview_meta.setStyleSheet("color: #64748b; font-size: 15px;")
        layout.addWidget(self.kb_preview_meta)

        self.kb_preview = LocalizedTextEdit()
        self.kb_preview.setReadOnly(True)
        self.kb_preview.setMinimumHeight(260)
        layout.addWidget(self.kb_preview, 1)

        self.add_file_btn.clicked.connect(self._add_knowledge_file)
        self.remove_file_btn.clicked.connect(self._remove_selected_file)
        return card

    def _build_settings_dialog(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle("AI 助手设置")
        dialog.resize(860, 920)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        intro = QLabel("把模型接口和知识库配置都收进这里，主页面只保留对话与会话管理。")
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #64748b; font-size: 16px;")
        layout.addWidget(intro)

        tabs = QTabWidget()
        tabs.addTab(self.config_card, "模型连接")
        tabs.addTab(self.knowledge_card, "知识库")
        layout.addWidget(tabs, 1)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setProperty("variant", "secondary")
        close_btn.clicked.connect(dialog.close)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)
        return dialog

    def _open_settings_dialog(self) -> None:
        if self.settings_dialog is None:
            self.settings_dialog = self._build_settings_dialog()
        self.refresh_shared_state()
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _toggle_mode(self) -> None:
        if self.mode == "page":
            self.request_open_dock.emit()
        else:
            self.request_open_page.emit()

    def _load_initial_state(self) -> None:
        self.refresh_shared_state()

    def refresh_shared_state(self) -> None:
        host, api_key, model = self.db.load_api_config()
        self.host_input.setText(host)
        self.key_input.setText(api_key)

        known_models = [self.model_combo.itemText(i) for i in range(self.model_combo.count())]
        if model and model not in known_models:
            self.model_combo.addItem(model)
        if model:
            self.model_combo.setCurrentText(model)

        flags = self.db.load_mentor_workspace_flags()
        self.base_cb.setChecked(flags.get("use_base", True))
        self.personal_cb.setChecked(flags.get("use_personal", True))
        self.custom_cb.setChecked(flags.get("use_custom", True))

        self._reload_custom_files()
        self._reload_sessions()
        self._refresh_kb_preview()

    def _ensure_sessions(self) -> None:
        sessions = self.db.list_mentor_sessions()
        if sessions:
            return
        default_id = self.db.create_mentor_session("默认对话")
        self.db.set_active_mentor_session(default_id)

    @staticmethod
    def _clean_legacy_message(content: str) -> str:
        text = (content or "").strip()
        compact = "".join(ch for ch in text if not ch.isspace())
        if compact.count("?") >= max(4, int(len(compact) * 0.3)) and not any("一" <= ch <= "鿿" for ch in text):
            return "这条旧消息因早期编码问题已自动清理。你可以重新描述一次，我会继续帮你。"
        return text

    def _session_snapshot(self, session_id: int) -> dict:
        messages = self.db.load_mentor_messages(session_id)
        if not messages:
            return {"message_count": 0, "preview": "还没有聊天记录，适合先用它拆学习计划或整理报错。"}
        role, content, _created_at = messages[-1]
        cleaned = self._clean_legacy_message(content)
        prefix = "你：" if role == "user" else "AI："
        preview = " ".join(cleaned.split())
        if len(preview) > 72:
            preview = preview[:71] + "..."
        return {"message_count": len(messages), "preview": prefix + preview}

    def _reload_sessions(self) -> None:
        self._ensure_sessions()
        sessions = self.db.list_mentor_sessions()
        active_id = self.db.load_active_mentor_session_id() or sessions[0][0]

        if hasattr(self, "session_combo"):
            self.session_combo.blockSignals(True)
            self.session_combo.clear()
            for session_id, name, _updated_at in sessions:
                self.session_combo.addItem(name, session_id)
            for row in range(self.session_combo.count()):
                if self.session_combo.itemData(row) == active_id:
                    self.session_combo.setCurrentIndex(row)
                    break
            self.session_combo.blockSignals(False)

        if hasattr(self, "session_list"):
            self.session_list.blockSignals(True)
            self.session_list.clear()
            for session_id, name, updated_at in sessions:
                snapshot = self._session_snapshot(session_id)
                preview = snapshot["preview"]
                item = QListWidgetItem(f"{name}\n{preview}")
                item.setData(Qt.UserRole, session_id)
                item.setToolTip(f"{preview}\n消息数：{snapshot['message_count']} . 最近更新：{updated_at}")
                item.setSizeHint(QSize(0, 74))
                self.session_list.addItem(item)
                if session_id == active_id:
                    self.session_list.setCurrentItem(item)
            self.session_list.blockSignals(False)

        self.current_session_id = active_id
        # Auto-trim old messages in ALL sessions to prevent memory bloat
        for session_id, _name, _updated_at in sessions:
            self.db.trim_mentor_messages(session_id, keep_last=200)
        self._sync_session_header()
        self._render_messages()

    def _sync_session_header(self) -> None:
        sessions = {session_id: name for session_id, name, _updated_at in self.db.list_mentor_sessions()}
        current_name = sessions.get(self.current_session_id, "默认对话")
        snapshot = (
            self._session_snapshot(self.current_session_id)
            if self.current_session_id
            else {"preview": "还没有聊天记录。", "message_count": 0}
        )
        self.chat_title.setText(current_name)
        self.chat_meta.setText(f"{snapshot['preview']} . 共 {snapshot['message_count']} 条消息。")
        if hasattr(self, "session_summary_label"):
            self.session_summary_label.setText(snapshot["preview"])

    def _on_session_combo_changed(self, index: int) -> None:
        if index < 0:
            return
        self.current_session_id = self.session_combo.itemData(index)
        self.db.set_active_mentor_session(self.current_session_id)
        self.db.trim_mentor_messages(self.current_session_id, keep_last=200)
        self._sync_session_header()
        self._render_messages()

    def _on_session_row_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self.session_list.item(row)
        if not item:
            return
        self.current_session_id = item.data(Qt.UserRole)
        self.db.set_active_mentor_session(self.current_session_id)
        self.db.trim_mentor_messages(self.current_session_id, keep_last=200)
        self._sync_session_header()
        self._render_messages()

    def _focus_current_session(self) -> None:
        if self.current_session_id:
            self.db.set_active_mentor_session(self.current_session_id)
            QMessageBox.information(self, "AI 会话", "当前会话已经设为默认会话。")

    def _create_session(self) -> None:
        default_name = f"新对话 {len(self.db.list_mentor_sessions()) + 1}"
        name, ok = QInputDialog.getText(self, "新建会话", "给这个会话起个名字：", text=default_name)
        if not ok:
            return
        name = name.strip() or default_name
        new_id = self.db.create_mentor_session(name)
        self.db.set_active_mentor_session(new_id)
        self._reload_sessions()

    def _rename_session(self) -> None:
        if not self.current_session_id:
            return
        current_name = self.chat_title.text().strip() or "默认对话"
        name, ok = QInputDialog.getText(self, "重命名会话", "新的会话名称：", text=current_name)
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        self.db.rename_mentor_session(self.current_session_id, name)
        self._reload_sessions()

    def _delete_session(self) -> None:
        if not self.current_session_id:
            return
        sessions = self.db.list_mentor_sessions()
        if len(sessions) <= 1:
            QMessageBox.information(self, "AI 会话", "至少保留一个会话，不能全部删除。")
            return
        reply = QMessageBox.question(self, "删除会话", "确定删除当前会话及其聊天记录吗？")
        if reply != QMessageBox.Yes:
            return
        self.db.delete_mentor_session(self.current_session_id)
        self._reload_sessions()

    def _render_messages(self) -> None:
        if not self.current_session_id:
            self.chat.clear()
            return

        messages = self.db.load_mentor_messages(self.current_session_id)
        blocks = []
        for role, content, _created_at in messages:
            blocks.append(_bubble_html(role, self._clean_legacy_message(content)))

        if not blocks:
            blocks.append(
                """
                <div style="
                    color:#64748b;
                    background:#fffefb;
                    border:1px dashed rgba(37,99,235,0.16);
                    border-radius:16px;
                    padding:14px 16px;
                    line-height:1.72;
                ">
                    这里会保留你和 AI 的对话记录。建议按主题拆分会话，比如"Python 调试""数据库报表""项目拆解"。
                </div>
                """
            )

        self.chat.setHtml("".join(blocks))
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat.setTextCursor(cursor)

    def _handle_response_ready(self, session_id: int) -> None:
        self._set_pending(False)
        self.retry_btn.hide()
        self._reload_sessions()
        if self.current_session_id == session_id:
            self._render_messages()

    def _handle_stream_chunk(self, chunk: str) -> None:
        """Handle a streaming text chunk by appending to the chat display."""
        self._stream_buffer = getattr(self, "_stream_buffer", "") + chunk
        # Show streaming progress in thinking hint
        preview = self._stream_buffer[-80:] if len(self._stream_buffer) > 80 else self._stream_buffer
        self.thinking_hint.setText(f"AI 正在回复... {preview}")

    def _set_settings_status(self, message: str) -> None:
        self.settings_status.setText(message)

    def save_config(self) -> None:
        self.db.save_api_config(
            self.host_input.text().strip(),
            self.key_input.text().strip(),
            self.model_combo.currentText().strip(),
        )
        self._set_settings_status("配置已保存。")

    def test_connection(self) -> None:
        host = self.host_input.text().strip()
        api_key = self.key_input.text().strip()
        if not host or not api_key:
            self._set_settings_status("请先填写 Host 和 API Key。")
            return
        self._set_settings_status("正在测试连接...")
        threading.Thread(target=self._test_connection_worker, args=(host, api_key), daemon=True).start()

    def _test_connection_worker(self, host: str, api_key: str) -> None:
        try:
            message = api_test_connection(host, api_key)
        except ConnectionError:
            message = "无法连接到服务器，请检查 Host 地址和网络连接。"
        except TimeoutError:
            message = "连接超时，服务器响应时间过长。"
        except ValueError as exc:
            message = str(exc)
        except Exception as exc:
            logger.warning("连接测试失败: %s", exc, exc_info=True)
            message = "连接测试失败，请检查 Host 地址和 API Key 是否正确。"
        self.status_ready.emit(message)

    def fetch_models(self) -> None:
        host = self.host_input.text().strip()
        api_key = self.key_input.text().strip()
        if not host or not api_key:
            self._set_settings_status("请先填写 Host 和 API Key。")
            return
        self._set_settings_status("正在获取模型列表...")
        threading.Thread(target=self._fetch_models_worker, args=(host, api_key), daemon=True).start()

    def _fetch_models_worker(self, host: str, api_key: str) -> None:
        try:
            models = api_fetch_models(host, api_key)
            self.models_ready.emit(models)
            self.status_ready.emit(f"已获取 {len(models)} 个模型。")
        except urllib.error.HTTPError as exc:
            logger.warning("获取模型列表 HTTP 错误: %s", exc.code, exc_info=True)
            if exc.code == 401:
                self.status_ready.emit("获取模型失败：API 密钥无效或已过期。")
            elif exc.code == 403:
                self.status_ready.emit("获取模型失败：没有访问权限，请检查 API 密钥。")
            else:
                self.status_ready.emit(f"获取模型失败：服务器返回 HTTP {exc.code}，请稍后重试。")
        except Exception as exc:
            logger.warning("获取模型列表失败: %s", exc, exc_info=True)
            self.status_ready.emit("获取模型失败，请检查 Host 地址和网络连接。")

    def _populate_models(self, models) -> None:
        current = self.model_combo.currentText().strip()
        self.model_combo.clear()
        self.model_combo.addItems(models)
        if current and current in models:
            self.model_combo.setCurrentText(current)

    def _save_workspace_flags(self) -> None:
        self.db.save_mentor_workspace_flags(
            self.base_cb.isChecked(),
            self.personal_cb.isChecked(),
            self.custom_cb.isChecked(),
        )
        self._refresh_kb_preview()

    def _reload_custom_files(self) -> None:
        self.file_list.clear()
        for file_id, display_name, file_path, excerpt in self.db.list_knowledge_files():
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, file_id)
            item.setToolTip(f"{file_path}\n{excerpt[:160].replace(chr(10), ' ')}")
            self.file_list.addItem(item)

    def _knowledge_overview_text(self) -> str:
        blocks = []
        if self.base_cb.isChecked():
            blocks.append(self._base_knowledge_text())
        if self.personal_cb.isChecked():
            blocks.append(self._personal_knowledge_text())
        if self.custom_cb.isChecked():
            blocks.append(self._custom_knowledge_text())
        if not blocks:
            blocks.append("当前没有启用任何知识库。")
        return "\n\n".join(blocks)

    def _selected_file_preview_text(self) -> str:
        item = self.file_list.currentItem()
        if not item:
            return ""
        record = self.db.get_knowledge_file(item.data(Qt.UserRole))
        if not record:
            return ""

        _file_id, display_name, file_path, excerpt, created_at = record
        file_obj = Path(file_path)
        exists = file_obj.exists()
        size_text = "未知大小"
        modified_text = "文件不存在"
        if exists:
            stat = file_obj.stat()
            size_text = f"{stat.st_size} 字节"
            modified_text = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

        header = [
            f"文件：{display_name}",
            f"路径：{file_path}",
            f"加入时间：{created_at}",
            f"当前状态：{'存在' if exists else '原文件已移动或删除'}",
            f"文件大小：{size_text}",
            f"最后修改：{modified_text}",
            "",
            "摘录预览：",
            excerpt.strip() or "这个文件目前没有可显示的文本摘录。",
        ]
        return "\n".join(header)

    def _add_knowledge_file(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择要加入扩展知识库的文件",
            "",
            "文本与代码文件 (*.txt *.md *.py *.c *.h *.cpp *.hpp *.cs *.json *.sql *.log *.csv);;所有文件 (*.*)",
        )
        if not paths:
            return
        for path in paths:
            excerpt = self._read_file_excerpt(path)
            if excerpt:
                self.db.add_knowledge_file(Path(path).name, path, excerpt)
        self._reload_custom_files()
        self._refresh_kb_preview()

    def _remove_selected_file(self) -> None:
        item = self.file_list.currentItem()
        if not item:
            return
        reply = QMessageBox.question(
            self,
            "确认移除",
            f"确定要移除知识文件“{item.text()}”吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.db.remove_knowledge_file(item.data(Qt.UserRole))
        self._reload_custom_files()
        self._refresh_kb_preview()

    @staticmethod
    def _read_file_excerpt(path: str) -> str:
        try:
            raw = Path(path).read_text(encoding="utf-8")
            return raw[:6000]
        except UnicodeDecodeError:
            try:
                raw = Path(path).read_text(encoding="gbk")
                return raw[:6000]
            except Exception as exc:
                logger.warning("读取知识库文件失败（GBK 回退）[%s]: %s", path, exc)
                return ""
        except Exception as exc:
            logger.warning("读取知识库文件失败 [%s]: %s", path, exc)
            return ""

    def _base_knowledge_text(self) -> str:
        lines = ["基础知识库：当前内置课程体系摘要"]
        for track in self.content_service.tracks:
            lines.append(f"- {track.title}: {track.summary}")
            for module in track.modules[:2]:
                lines.append(f"  - {module.title}: {module.summary}")
        return "\n".join(lines)

    def _personal_knowledge_text(self) -> str:
        lines = ["个性知识库：根据你的学习进度和做题情况生成"]
        lines.append(f"- 已完成课程数：{self.db.completed_lessons()}")
        lines.append(f"- 练习平均分：{self.db.average_score()}")
        lines.append(f"- 连续学习天数：{self.db.active_days_streak()}")

        recent_attempts = self.db.fetchall(
            """
            SELECT COALESCE(NULLIF(exercise_title_snapshot, ''), exercise_id), score, passed, submitted_at
            FROM practice_attempts
            ORDER BY id DESC
            LIMIT 8
            """
        )
        if recent_attempts:
            lines.append("- 最近练习记录：")
            for title, score, passed, submitted_at in recent_attempts[:5]:
                lines.append(f"  - {title}: 分数 {score}，{'通过' if passed else '未通过'}，时间 {submitted_at}")

        progress_rows = self.db.fetchall(
            """
            SELECT lesson_id, status, completed
            FROM lesson_progress
            ORDER BY last_opened DESC
            LIMIT 8
            """
        )
        if progress_rows:
            lines.append("- 最近课程进度：")
            for lesson_id, status, completed_flag in progress_rows[:5]:
                lines.append(f"  - {lesson_id}: {'已完成' if completed_flag else status}")
        return "\n".join(lines)

    def _custom_knowledge_text(self) -> str:
        files = self.db.list_knowledge_files()
        if not files:
            return "扩展知识库：还没有添加文件。"
        lines = ["扩展知识库：用户手动加入的文件摘录"]
        for _file_id, display_name, _path, excerpt in files[:6]:
            lines.append(f"- {display_name}: {excerpt.strip().replace(chr(10), ' ')[:220]}")
        return "\n".join(lines)

    def _refresh_kb_preview(self) -> None:
        selected_preview = self._selected_file_preview_text()
        if selected_preview:
            self.kb_preview_title.setText("文件预览")
            self.kb_preview_meta.setText("这里展示选中文件的来源信息和用于知识库的摘录内容。")
            self.kb_preview.setPlainText(selected_preview)
            return

        self.kb_preview_title.setText("知识库总览")
        self.kb_preview_meta.setText("没有选中文件时，这里会显示当前启用的知识库摘要。")
        self.kb_preview.setPlainText(self._knowledge_overview_text())

    def _build_system_context(self) -> str:
        parts = [
            "你是 DevLearner 的学习型 AI 助手。回答时请优先结合当前课程体系、学习进度和做题表现，给出清晰、分步骤、有同理心的中文建议。",
            "如果用户在问编程问题，请先解释思路、常见错误和下一步练习建议，而不是只给结论。",
            "你还具备以下代码分析能力：",
            "- 代码解释：逐步拆解代码逻辑，标注对初学者有难度的地方",
            "- 代码审查：从风格、性能、最佳实践角度审查代码质量",
            "- Bug 检测：检查边界条件、运行时错误、逻辑漏洞",
            "当用户发送代码时，主动识别意图并提供对应的分析。",
        ]

        # Inject coaching mode system prompt when active
        if self._coaching_mode == COACHING_MODE_COACHING:
            parts.append(_COACHING_SYSTEM_PROMPT)
        if self.base_cb.isChecked():
            parts.append(self._base_knowledge_text())
        if self.personal_cb.isChecked():
            parts.append(self._personal_knowledge_text())
        if self.custom_cb.isChecked():
            parts.append(self._custom_knowledge_text())
        if self.current_session_id:
            snapshot = self._session_snapshot(self.current_session_id)
            parts.append(f"当前会话摘要：{snapshot['preview']}")
        return "\n\n".join(parts)

    def _seed_prompt(self, prompt: str) -> None:
        self.input.setText(prompt)
        self.input.setFocus()
        self.input.selectAll()

    def _quick_code_analysis(self, analysis_type: str) -> None:
        """Quick code analysis triggered from the chat panel buttons."""
        from PyQt5.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        code = clipboard.text().strip() if clipboard else ""

        if not code:
            self._seed_prompt("请粘贴你想分析的代码，我会帮你做详细的代码分析。")
            return

        # Detect language heuristically
        language = "python"
        if any(kw in code for kw in ["#include", "int main", "printf", "void "]):
            language = "c"
        elif any(kw in code for kw in ["using namespace", "std::", "cout", "cin"]):
            language = "cpp"
        elif any(kw in code for kw in ["Console.Write", "namespace ", "public class"]):
            language = "csharp"
        elif any(kw.upper() in code.upper() for kw in ["SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE TABLE"]):
            language = "sql"

        type_labels = {
            "explanation": "代码解释",
            "review": "代码审查",
            "bug_detection": "Bug 检测",
        }
        label = type_labels.get(analysis_type, "代码分析")
        self.thinking_hint.setVisible(True)
        self.thinking_hint.setText(f"正在对剪贴板代码进行{label}...")

        if analysis_type == "explanation":
            self.analyze_code_explanation(code, language)
        elif analysis_type == "review":
            self.analyze_code_review(code, language)
        elif analysis_type == "bug_detection":
            self.analyze_code_bugs(code, language)

    def _toggle_coaching_mode(self) -> None:
        """Toggle between standard and Socratic coaching mode."""
        if self._coaching_mode == COACHING_MODE_STANDARD:
            self._coaching_mode = COACHING_MODE_COACHING
            self.coaching_btn.setText("教练模式中")
            self.coaching_btn.setStyleSheet("QPushButton { background: rgba(37, 99, 235, 0.12); font-weight: 700; }")
        else:
            self._coaching_mode = COACHING_MODE_STANDARD
            self.coaching_btn.setText("标准模式")
            self.coaching_btn.setStyleSheet("")

    def _analyze_learning_pattern(self) -> None:
        """Send a learning pattern analysis request to the AI."""
        host = self.host_input.text().strip()
        api_key = self.key_input.text().strip()
        model = self.model_combo.currentText().strip()

        if not host or not api_key or not model:
            self._seed_prompt("请先在 AI 设置中配置 Host、Key 和模型，然后才能分析学习模式。")
            return

        self.thinking_hint.setVisible(True)
        self.thinking_hint.setText("正在分析你的学习模式...")

        # Build analysis context from practice history
        analysis_context = self._build_learning_pattern_context()

        threading.Thread(
            target=self._learning_pattern_worker,
            args=(host, api_key, model, analysis_context),
            daemon=True,
        ).start()

    def _build_learning_pattern_context(self) -> str:
        """Build context for learning pattern analysis."""
        lines = [_LEARNING_PATTERN_ANALYSIS_PROMPT, "", "学生数据摘要："]

        # Practice stats
        lines.append(f"- 已完成课程数：{self.db.completed_lessons()}")
        lines.append(f"- 练习平均分：{self.db.average_score()}")
        lines.append(f"- 连续学习天数：{self.db.active_days_streak()}")

        # Recent attempts
        recent = self.db.recent_attempts(limit=10)
        if recent:
            lines.append("- 最近练习：")
            for _submitted_at, title, score, passed, dur in recent[:6]:
                lines.append(f"  - {title}: 分数 {score}, {'通过' if passed else '未通过'}, 用时 {dur}s")

        # Hint usage patterns
        try:
            hint_rows = self.db.fetchall("SELECT COUNT(*) FROM exercise_timers WHERE difficulty = 'hint'")
            total_hints = int(hint_rows[0][0]) if hint_rows and hint_rows[0][0] else 0
            lines.append(f"- 总提示使用次数：{total_hints}")
        except Exception:
            pass

        return "\n".join(lines)

    def _learning_pattern_worker(self, host: str, api_key: str, model: str, context: str) -> None:
        """Background worker for learning pattern analysis."""
        try:
            api_messages = [
                {
                    "role": "system",
                    "content": "你是一位专业的学习分析师。根据学生的学习数据，用简洁的中文分析其学习模式和弱点。",
                },
                {"role": "user", "content": context},
            ]
            try:
                reply = api_send_chat_stream(host, api_key, model, api_messages)
            except Exception:
                reply = api_send_chat(host, api_key, model, api_messages)

            if self.current_session_id:
                self.db.append_mentor_message(self.current_session_id, "user", "[学习模式分析请求]")
                self.db.append_mentor_message(self.current_session_id, "assistant", reply)

            try:
                self.response_ready.emit(self.current_session_id or 0)
            except RuntimeError:
                pass
        except Exception as exc:
            logger.error("学习模式分析失败: %s", exc, exc_info=True)
            try:
                self.status_ready.emit(f"学习模式分析失败：{exc}")
            except RuntimeError:
                pass

    def retry_last_message(self) -> None:
        """Retry the last user message."""
        if not self.current_session_id:
            return
        messages = self.db.load_mentor_messages(self.current_session_id)
        if not messages:
            return
        # Find the last user message
        last_user_msg = None
        for role, content, _created_at in reversed(messages):
            if role == "user":
                last_user_msg = content
                break
        if last_user_msg:
            self.input.setText(last_user_msg)
            self.send_message()

    def send_message(self) -> None:
        if self._request_in_flight:
            return

        message = self.input.text().strip()
        if not message or not self.current_session_id:
            return

        host = self.host_input.text().strip()
        api_key = self.key_input.text().strip()
        model = self.model_combo.currentText().strip()
        system_context = self._build_system_context()

        self.db.append_mentor_message(self.current_session_id, "user", message)
        self.input.clear()
        self._render_messages()

        if not host or not api_key or not model:
            self.db.append_mentor_message(
                self.current_session_id,
                "assistant",
                "你还没有配置好 Host、Key 和模型。先到“AI 设置”里填好这些，我就能联网帮你了。",
            )
            self._reload_sessions()
            self._render_messages()
            return

        self._set_pending(True)
        threading.Thread(
            target=self._chat_worker,
            args=(host, api_key, model, system_context, self.current_session_id),
            daemon=True,
        ).start()

    def _set_pending(self, pending: bool) -> None:
        self._request_in_flight = pending
        self.send_btn.setEnabled(not pending)
        self.send_btn.setText("思考中..." if pending else "发送")
        self.thinking_hint.setVisible(pending)
        if pending:
            self.thinking_hint.setText("AI 正在整理回答，请稍等片刻。")
        else:
            self.thinking_hint.clear()

    def _chat_worker(self, host: str, api_key: str, model: str, system_context: str, session_id: int) -> None:
        self._stream_buffer = ""
        try:
            api_messages = [{"role": "system", "content": system_context}]
            for role, content, _created_at in self.db.load_mentor_messages(session_id)[-12:]:
                api_messages.append({"role": role, "content": content})

            def _on_chunk(chunk_text: str) -> None:
                try:
                    self.stream_chunk_ready.emit(chunk_text)
                except RuntimeError:
                    pass

            try:
                reply = api_send_chat_stream(host, api_key, model, api_messages, _on_chunk)
            except Exception as exc:
                logger.info("流式传输失败，回退到普通请求: %s", exc)
                # Fall back to non-streaming if streaming fails
                reply = api_send_chat(host, api_key, model, api_messages)
        except ValueError as exc:
            logger.error("AI mentor ValueError: %s", exc, exc_info=True)
            reply = "AI 服务响应解析失败，请稍后重试。"
        except urllib.error.HTTPError as exc:
            try:
                error_body = json.loads(exc.read().decode("utf-8"))
                logger.error("AI mentor HTTP %s: %s", exc.code, error_body, exc_info=True)
            except Exception:
                logger.error("AI mentor HTTP %s: %s", exc.code, exc, exc_info=True)
            if exc.code == 401:
                reply = "AI 密钥无效或已过期，请到 AI 设置里更新密钥。"
            elif exc.code == 429:
                reply = "请求过于频繁，请稍等片刻后重试。"
            else:
                reply = f"AI 服务请求失败（HTTP {exc.code}），请检查设置或稍后重试。"
        except Exception as exc:
            logger.error("AI mentor unexpected error: %s", exc, exc_info=True)
            reply = "AI 服务连接失败，请检查设置或网络连接。"

        try:
            self.db.append_mentor_message(session_id, "assistant", reply)
        finally:
            if self._is_valid:
                try:
                    self.response_ready.emit(session_id)
                except RuntimeError:
                    pass  # underlying C++ object already destroyed

    # ── Code Analysis Methods ─────────────────────────────────────────────────

    def analyze_code_explanation(self, code: str, language: str = "python") -> None:
        """Send a code explanation request to the AI.

        Asks the AI to break down the code step by step, explaining
        what each section does and the overall logic flow.
        """
        if not code.strip():
            return
        prompt = (
            f"请对以下 {language} 代码进行逐步解释：\n"
            f"1. 先给出整体功能概述\n"
            f"2. 然后逐行或逐段解释关键逻辑\n"
            f"3. 标注可能对初学者有难度的地方\n"
            f"4. 总结这段代码的核心知识点\n\n"
            f"```{language}\n{code}\n```"
        )
        self._send_code_analysis_request("explanation", prompt, code, language)

    def analyze_code_review(self, code: str, language: str = "python") -> None:
        """Send a code review request to the AI.

        Asks the AI to review the code for quality, style,
        and best practices compliance.
        """
        if not code.strip():
            return
        prompt = (
            f"请对以下 {language} 代码进行专业代码审查：\n"
            f"1. 代码风格和命名规范\n"
            f"2. 可读性和可维护性\n"
            f"3. 性能方面有没有可优化之处\n"
            f"4. 是否符合 {language} 最佳实践\n"
            f"5. 改进建议（附代码示例）\n\n"
            f"```{language}\n{code}\n```"
        )
        self._send_code_analysis_request("review", prompt, code, language)

    def analyze_code_bugs(self, code: str, language: str = "python") -> None:
        """Send a bug detection request to the AI.

        Asks the AI to analyze the code for potential bugs,
        edge cases, and error-prone patterns.
        """
        if not code.strip():
            return
        prompt = (
            f"请对以下 {language} 代码进行 Bug 检测分析：\n"
            f"1. 逐行检查可能存在的 Bug\n"
            f"2. 边界条件和异常输入处理\n"
            f"3. 潜在的运行时错误（如空指针、越界、类型错误等）\n"
            f"4. 逻辑漏洞或竞态条件\n"
            f"5. 对每个发现的问题给出修复建议\n\n"
            f"```{language}\n{code}\n```"
        )
        self._send_code_analysis_request("bug_detection", prompt, code, language)

    def _send_code_analysis_request(self, analysis_type: str, prompt: str, code: str, language: str) -> None:
        """Internal method to send code analysis requests to the AI backend."""
        host = self.host_input.text().strip()
        api_key = self.key_input.text().strip()
        model = self.model_combo.currentText().strip()

        if not host or not api_key or not model:
            self.code_analysis_ready.emit(
                analysis_type,
                {
                    "success": False,
                    "error": "请先在 AI 设置中配置 Host、Key 和模型。",
                    "code": code,
                    "language": language,
                },
            )
            return

        system_context = (
            "你是一位专业的编程导师和代码分析专家。"
            "你的任务是帮助学生理解代码、发现潜在问题并提供改进建议。"
            "请用清晰的中文回答，必要时使用代码示例。"
            "对于初学者容易犯的错误要特别标注和解释。"
        )

        threading.Thread(
            target=self._code_analysis_worker,
            args=(analysis_type, host, api_key, model, system_context, prompt, code, language),
            daemon=True,
        ).start()

    def _code_analysis_worker(
        self,
        analysis_type: str,
        host: str,
        api_key: str,
        model: str,
        system_context: str,
        prompt: str,
        code: str,
        language: str,
    ) -> None:
        """Background worker for code analysis requests."""
        try:
            api_messages = [
                {"role": "system", "content": system_context},
                {"role": "user", "content": prompt},
            ]
            try:
                reply = api_send_chat_stream(host, api_key, model, api_messages)
            except Exception:
                logger.info("代码分析流式传输失败，回退到普通请求")
                reply = api_send_chat(host, api_key, model, api_messages)

            self.code_analysis_ready.emit(
                analysis_type,
                {
                    "success": True,
                    "reply": reply,
                    "code": code,
                    "language": language,
                },
            )
        except urllib.error.HTTPError as exc:
            logger.error("代码分析 HTTP 错误: %s", exc.code, exc_info=True)
            error_msg = f"AI 服务请求失败（HTTP {exc.code}），请检查设置。"
            if exc.code == 401:
                error_msg = "AI 密钥无效或已过期，请更新密钥。"
            elif exc.code == 429:
                error_msg = "请求过于频繁，请稍后重试。"
            self.code_analysis_ready.emit(
                analysis_type,
                {
                    "success": False,
                    "error": error_msg,
                    "code": code,
                    "language": language,
                },
            )
        except Exception as exc:
            logger.error("代码分析异常: %s", exc, exc_info=True)
            self.code_analysis_ready.emit(
                analysis_type,
                {
                    "success": False,
                    "error": f"代码分析失败：{exc}",
                    "code": code,
                    "language": language,
                },
            )

    def _handle_code_analysis_result(self, analysis_type: str, result: dict) -> None:
        """Handle completed code analysis results by saving to session history."""
        if not self.current_session_id:
            return
        if not result.get("success"):
            return

        type_labels = {
            "explanation": "代码解释",
            "review": "代码审查",
            "bug_detection": "Bug 检测",
        }
        label = type_labels.get(analysis_type, "代码分析")
        language = result.get("language", "python")
        code_preview = result.get("code", "")[:200]
        reply = result.get("reply", "")

        user_msg = f"[{label}] 分析以下 {language} 代码：\n```\n{code_preview}...\n```"
        self.db.append_mentor_message(self.current_session_id, "user", user_msg)
        self.db.append_mentor_message(self.current_session_id, "assistant", reply)
        self._reload_sessions()


class AIMentorDock(QDockWidget):
    def __init__(self, db: AppDatabase, content_service: ContentService, parent: Optional[QWidget] = None) -> None:
        super().__init__("AI 助手", parent)
        self.panel = AIMentorPanel(db, content_service, mode="dock", parent=self)
        self.setAllowedAreas(Qt.RightDockWidgetArea)
        self.setWidget(self.panel)

    @property
    def input(self) -> LocalizedLineEdit:
        return self.panel.input
