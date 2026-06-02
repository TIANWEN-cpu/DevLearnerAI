"""Code Analyzer Widget.

Provides a panel for AI-powered code analysis with:
- Code explanation (step-by-step breakdown)
- Code review (quality and best practices)
- Bug detection (potential issues identification)
- Complexity visualization (cyclomatic complexity estimation)
"""

import logging
import re
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.styles import (
    ACCENT,
    ACCENT_SOFT,
    BG_CARD,
    BG_CARD_SOFT,
    BORDER,
    ERROR,
    F_SUB,
    FONT,
    SUCCESS,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUB,
    WARNING,
)

logger = logging.getLogger(__name__)

# ── Complexity estimation patterns ───────────────────────────────────────────

_COMPLEXITY_PATTERNS = {
    "python": [
        (r"\bif\b", "if"),
        (r"\belif\b", "elif"),
        (r"\belse\b", "else"),
        (r"\bfor\b", "for"),
        (r"\bwhile\b", "while"),
        (r"\btry\b", "try"),
        (r"\bexcept\b", "except"),
        (r"\bwith\b", "with"),
        (r"\band\b", "and"),
        (r"\bor\b", "or"),
        (r"\blambda\b", "lambda"),
        (r"\bdef\b", "def"),
        (r"\bclass\b", "class"),
    ],
    "c": [
        (r"\bif\s*\(", "if"),
        (r"\belse\b", "else"),
        (r"\bfor\s*\(", "for"),
        (r"\bwhile\s*\(", "while"),
        (r"\bdo\b", "do-while"),
        (r"\bswitch\b", "switch"),
        (r"\bcase\b", "case"),
        (r"&&", "logical AND"),
        (r"\|\|", "logical OR"),
        (r"\?", "ternary"),
    ],
    "cpp": [
        (r"\bif\s*\(", "if"),
        (r"\belse\b", "else"),
        (r"\bfor\s*\(", "for"),
        (r"\bwhile\s*\(", "while"),
        (r"\bdo\b", "do-while"),
        (r"\bswitch\b", "switch"),
        (r"\bcase\b", "case"),
        (r"&&", "logical AND"),
        (r"\|\|", "logical OR"),
        (r"\?", "ternary"),
        (r"\bcatch\b", "catch"),
        (r"\btry\b", "try"),
    ],
    "csharp": [
        (r"\bif\s*\(", "if"),
        (r"\belse\b", "else"),
        (r"\bfor\s*(?:each)?\s*\(", "for"),
        (r"\bwhile\s*\(", "while"),
        (r"\bdo\b", "do-while"),
        (r"\bswitch\b", "switch"),
        (r"\bcase\b", "case"),
        (r"&&", "logical AND"),
        (r"\|\|", "logical OR"),
        (r"\?", "ternary"),
        (r"\bcatch\b", "catch"),
        (r"\btry\b", "try"),
    ],
    "sql": [
        (r"\bWHERE\b", "WHERE"),
        (r"\bJOIN\b", "JOIN"),
        (r"\bCASE\b", "CASE"),
        (r"\bWHEN\b", "WHEN"),
        (r"\bAND\b", "AND"),
        (r"\bOR\b", "OR"),
        (r"\bUNION\b", "UNION"),
        (r"\bHAVING\b", "HAVING"),
    ],
}

DEFAULT_PATTERNS = _COMPLEXITY_PATTERNS["python"]


def estimate_complexity(code: str, language: str = "python") -> dict:
    """Estimate cyclomatic complexity metrics from code.

    Returns a dict with:
      - score: estimated cyclomatic complexity (1 + decision points)
      - level: "low", "medium", "high", "very_high"
      - details: list of (pattern_name, count) tuples
      - lines: total line count
      - functions: number of function definitions
      - classes: number of class definitions
    """
    patterns = _COMPLEXITY_PATTERNS.get(language.lower(), DEFAULT_PATTERNS)
    details = []
    decision_count = 0
    for regex, label in patterns:
        count = len(re.findall(regex, code, re.IGNORECASE))
        if count > 0:
            details.append((label, count))
            if label not in ("def", "class", "def", "def"):
                decision_count += count

    complexity_score = 1 + decision_count

    if complexity_score <= 5:
        level = "low"
    elif complexity_score <= 10:
        level = "medium"
    elif complexity_score <= 20:
        level = "high"
    else:
        level = "very_high"

    lines = len(code.strip().splitlines())
    func_count = len(re.findall(r"\bdef\s+\w+", code)) or len(re.findall(r"\bfunction\s+\w+", code))
    class_count = len(re.findall(r"\bclass\s+\w+", code))

    return {
        "score": complexity_score,
        "level": level,
        "level_label": {
            "low": "低复杂度",
            "medium": "中等复杂度",
            "high": "较高复杂度",
            "very_high": "高复杂度",
        }.get(level, "未知"),
        "details": details,
        "lines": lines,
        "functions": func_count,
        "classes": class_count,
    }


# ── Complexity Visualization Widget ──────────────────────────────────────────


class ComplexityGauge(QWidget):
    """A circular gauge widget that visualizes cyclomatic complexity."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._score = 0
        self._max_score = 30
        self._level = "low"
        self._label = "未知"
        self.setMinimumSize(180, 180)
        self.setMaximumSize(220, 220)

    def set_complexity(self, score: int, level: str, label: str) -> None:
        self._score = min(score, self._max_score)
        self._level = level
        self._label = label
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height())
        cx, cy = self.width() // 2, self.height() // 2
        radius = side // 2 - 20

        # Background arc
        bg_pen = QPen(QColor("#e2e8f0"), 14, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2, 225 * 16, -270 * 16)

        # Value arc
        ratio = min(self._score / self._max_score, 1.0)
        color_map = {
            "low": SUCCESS,
            "medium": WARNING,
            "high": "#f97316",
            "very_high": ERROR,
        }
        color = color_map.get(self._level, TEXT_MUTED)
        val_pen = QPen(QColor(color), 14, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(val_pen)
        span = int(-270 * 16 * ratio)
        painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2, 225 * 16, span)

        # Center text
        painter.setPen(QColor(TEXT_MAIN))
        painter.setFont(QFont(FONT, 28, QFont.Bold))
        painter.drawText(self.rect().adjusted(0, -20, 0, 0), Qt.AlignCenter, str(self._score))

        painter.setPen(QColor(TEXT_MUTED))
        painter.setFont(QFont(FONT, 13))
        painter.drawText(self.rect().adjusted(0, 28, 0, 0), Qt.AlignCenter, self._label)

        painter.end()


# ── Step Display Widget ──────────────────────────────────────────────────────


class StepExplanationCard(QFrame):
    """A single step card in the step-by-step explanation display."""

    def __init__(self, step_num: int, title: str, content: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 16px;
            }}
            QFrame:hover {{
                border: 1px solid rgba(37, 99, 235, 0.22);
            }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Step number badge
        badge = QLabel(str(step_num))
        badge.setFixedSize(36, 36)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"""
            QLabel {{
                background: {ACCENT_SOFT};
                color: {ACCENT};
                border-radius: 18px;
                font-weight: 700;
                font-size: 16px;
            }}
            """
        )
        layout.addWidget(badge, 0, Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-weight: 700; color: {TEXT_MAIN}; font-size: 15px;")
        title_label.setWordWrap(True)
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 14px; line-height: 1.6;")
        content_label.setTextFormat(Qt.RichText)
        text_col.addWidget(title_label)
        text_col.addWidget(content_label)
        layout.addLayout(text_col, 1)


# ── Main Code Analyzer Panel ─────────────────────────────────────────────────


class CodeAnalyzerPanel(QWidget):
    """Main code analysis panel with tabs for explanation, review, and bug detection."""

    analysis_requested = pyqtSignal(str, str, str)  # (analysis_type, code, language)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_code = ""
        self._current_language = "python"
        self._is_analyzing = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Header
        header = QFrame()
        header.setStyleSheet(
            f"""
            QFrame {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {BG_CARD}, stop:1 {ACCENT_SOFT}
                );
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(12)

        icon_label = QLabel("⚙")
        icon_label.setStyleSheet(f"font-size: 28px; color: {ACCENT};")
        icon_label.setFixedWidth(36)
        header_layout.addWidget(icon_label)

        title_col = QVBoxLayout()
        title = QLabel("AI 代码分析")
        title.setFont(QFont(FONT, F_SUB - 8, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        subtitle = QLabel("使用 AI 深度分析代码，获取解释、审查和 Bug 检测结果。")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color: {TEXT_SUB}; font-size: 14px;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header_layout.addLayout(title_col, 1)

        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.setMinimumWidth(120)
        self.analyze_btn.setToolTip("对当前代码运行全部分析")
        self.analyze_btn.setAccessibleName("开始分析")
        self.analyze_btn.setAccessibleDescription("对当前代码运行 AI 全部分析，包括解释、审查和 Bug 检测")
        self.analyze_btn.clicked.connect(self._run_all_analysis)
        header_layout.addWidget(self.analyze_btn)

        root.addWidget(header)

        # Main content area with tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER};
                border-radius: 14px;
                background: {BG_CARD};
            }}
            QTabBar::tab {{
                background: {BG_CARD_SOFT};
                border: 1px solid {BORDER};
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 8px 18px;
                margin-right: 4px;
                color: {TEXT_SUB};
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {BG_CARD};
                color: {ACCENT};
                border-bottom: 2px solid {ACCENT};
            }}
            """
        )

        self.tabs.addTab(self._build_explanation_tab(), "逐步解释")
        self.tabs.addTab(self._build_review_tab(), "代码审查")
        self.tabs.addTab(self._build_bug_tab(), "Bug 检测")
        self.tabs.addTab(self._build_complexity_tab(), "复杂度分析")
        self.tabs.setAccessibleName("代码分析选项卡")
        self.tabs.setAccessibleDescription("切换不同类型的代码分析结果视图")

        root.addWidget(self.tabs, 1)

        # Status bar
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self.status_label.setVisible(False)
        root.addWidget(self.status_label)

    def _build_explanation_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        self.explanation_layout = QVBoxLayout(container)
        self.explanation_layout.setContentsMargins(16, 16, 16, 16)
        self.explanation_layout.setSpacing(10)

        self.explanation_placeholder = QLabel("点击「开始分析」或选择代码后获取逐步解释。")
        self.explanation_placeholder.setAlignment(Qt.AlignCenter)
        self.explanation_placeholder.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 15px; padding: 40px;")
        self.explanation_layout.addWidget(self.explanation_placeholder)
        self.explanation_layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _build_review_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        self.review_layout = QVBoxLayout(container)
        self.review_layout.setContentsMargins(16, 16, 16, 16)
        self.review_layout.setSpacing(10)

        self.review_text = QTextEdit()
        self.review_text.setReadOnly(True)
        self.review_text.setMinimumHeight(400)
        self.review_text.setStyleSheet(
            f"""
            QTextEdit {{
                background: {BG_CARD_SOFT};
                border: 1px solid {BORDER};
                border-radius: 14px;
                padding: 14px;
                color: {TEXT_MAIN};
                font-size: 14px;
                line-height: 1.6;
            }}
            """
        )
        self.review_text.setPlainText("代码审查结果将显示在这里。")
        self.review_layout.addWidget(self.review_text)

        scroll.setWidget(container)
        return scroll

    def _build_bug_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        self.bug_layout = QVBoxLayout(container)
        self.bug_layout.setContentsMargins(16, 16, 16, 16)
        self.bug_layout.setSpacing(10)

        self.bug_text = QTextEdit()
        self.bug_text.setReadOnly(True)
        self.bug_text.setMinimumHeight(400)
        self.bug_text.setStyleSheet(
            f"""
            QTextEdit {{
                background: {BG_CARD_SOFT};
                border: 1px solid {BORDER};
                border-radius: 14px;
                padding: 14px;
                color: {TEXT_MAIN};
                font-size: 14px;
                line-height: 1.6;
            }}
            """
        )
        self.bug_text.setPlainText("Bug 检测结果将显示在这里。")
        self.bug_layout.addWidget(self.bug_text)

        scroll.setWidget(container)
        return scroll

    def _build_complexity_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Gauge + summary row
        top_row = QHBoxLayout()
        top_row.setSpacing(18)

        self.complexity_gauge = ComplexityGauge()
        top_row.addWidget(self.complexity_gauge)

        summary_col = QVBoxLayout()
        summary_col.setSpacing(8)

        self.complexity_title = QLabel("复杂度分析")
        self.complexity_title.setFont(QFont(FONT, 16, QFont.Bold))
        self.complexity_title.setStyleSheet(f"color: {TEXT_MAIN};")

        self.complexity_summary = QLabel("加载代码后自动计算复杂度指标。")
        self.complexity_summary.setWordWrap(True)
        self.complexity_summary.setStyleSheet(f"color: {TEXT_SUB}; font-size: 14px;")

        self.complexity_stats = QLabel("")
        self.complexity_stats.setWordWrap(True)
        self.complexity_stats.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")

        summary_col.addWidget(self.complexity_title)
        summary_col.addWidget(self.complexity_summary)
        summary_col.addWidget(self.complexity_stats)
        summary_col.addStretch()
        top_row.addLayout(summary_col, 1)
        layout.addLayout(top_row)

        # Breakdown section
        breakdown_group = QGroupBox("决策点分布")
        breakdown_group.setStyleSheet(
            f"""
            QGroupBox {{
                font-weight: 700;
                color: {TEXT_MAIN};
                border: 1px solid {BORDER};
                border-radius: 14px;
                margin-top: 10px;
                padding-top: 18px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
            }}
            """
        )
        self.breakdown_layout = QVBoxLayout(breakdown_group)
        self.breakdown_layout.setContentsMargins(14, 14, 14, 14)
        self.breakdown_layout.setSpacing(6)
        self.breakdown_placeholder = QLabel("暂无数据")
        self.breakdown_placeholder.setStyleSheet(f"color: {TEXT_MUTED};")
        self.breakdown_layout.addWidget(self.breakdown_placeholder)
        layout.addWidget(breakdown_group, 1)

        return container

    # ── Public API ───────────────────────────────────────────────────────────

    def set_code(self, code: str, language: str = "python") -> None:
        """Set the code to be analyzed and update complexity visualization."""
        self._current_code = code
        self._current_language = language
        self._update_complexity(code, language)

    def _update_complexity(self, code: str, language: str) -> None:
        """Update the complexity tab with static analysis results."""
        metrics = estimate_complexity(code, language)
        self.complexity_gauge.set_complexity(metrics["score"], metrics["level"], metrics["level_label"])
        self.complexity_summary.setText(f"圈复杂度评估为 {metrics['score']}，属于{metrics['level_label']}。")
        self.complexity_stats.setText(
            f"代码行数: {metrics['lines']}  |  函数: {metrics['functions']}  |  类: {metrics['classes']}"
        )
        # Update breakdown bars
        self._clear_layout(self.breakdown_layout)
        if metrics["details"]:
            max_count = max(c for _, c in metrics["details"])
            for label, count in metrics["details"]:
                row = QHBoxLayout()
                row.setSpacing(8)
                name_label = QLabel(label)
                name_label.setFixedWidth(90)
                name_label.setStyleSheet(f"color: {TEXT_SUB}; font-size: 13px;")
                bar = QProgressBar()
                bar.setFixedHeight(14)
                bar.setRange(0, max(max_count, 1))
                bar.setValue(count)
                bar.setTextVisible(False)
                bar_color = ACCENT if count <= 3 else WARNING if count <= 6 else ERROR
                bar.setStyleSheet(
                    f"QProgressBar {{ background: {BG_CARD_SOFT}; border-radius: 7px; }}"
                    f"QProgressBar::chunk {{ background: {bar_color}; border-radius: 7px; }}"
                )
                count_label = QLabel(str(count))
                count_label.setFixedWidth(30)
                count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                count_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
                row.addWidget(name_label)
                row.addWidget(bar, 1)
                row.addWidget(count_label)
                self.breakdown_layout.addLayout(row)
        else:
            placeholder = QLabel("未检测到决策点。")
            placeholder.setStyleSheet(f"color: {TEXT_MUTED};")
            self.breakdown_layout.addWidget(placeholder)

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                CodeAnalyzerPanel._clear_layout(child.layout())

    def _run_all_analysis(self) -> None:
        """Trigger all analysis types."""
        if not self._current_code.strip():
            self._show_status("请先加载或选择一段代码。", is_error=True)
            return
        if self._is_analyzing:
            return
        self._is_analyzing = True
        self.analyze_btn.setText("分析中...")
        self.analyze_btn.setEnabled(False)
        self._show_status("AI 正在分析代码，请稍候...")
        self.analysis_requested.emit("all", self._current_code, self._current_language)

    def display_explanation(self, reply: str) -> None:
        """Display the step-by-step explanation result."""
        self._clear_layout(self.explanation_layout)
        steps = self._parse_explanation_steps(reply)
        if steps:
            for i, (title, content) in enumerate(steps, 1):
                card = StepExplanationCard(i, title, content)
                self.explanation_layout.addWidget(card)
        else:
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setHtml(self._plain_to_html(reply))
            text_edit.setStyleSheet(
                f"QTextEdit {{ background: {BG_CARD_SOFT}; border: 1px solid {BORDER};"
                f" border-radius: 14px; padding: 14px; color: {TEXT_MAIN}; font-size: 14px; }}"
            )
            self.explanation_layout.addWidget(text_edit)
        self.explanation_layout.addStretch()
        self.tabs.setCurrentIndex(0)

    def display_review(self, reply: str) -> None:
        """Display the code review result."""
        self.review_text.setPlainText(reply)
        self.tabs.setCurrentIndex(1)

    def display_bugs(self, reply: str) -> None:
        """Display the bug detection result."""
        self.bug_text.setPlainText(reply)
        self.tabs.setCurrentIndex(2)

    def set_analysis_complete(self) -> None:
        """Reset UI state after analysis completes."""
        self._is_analyzing = False
        self.analyze_btn.setText("开始分析")
        self.analyze_btn.setEnabled(True)
        self._show_status("分析完成。")

    def set_analysis_error(self, error_msg: str) -> None:
        """Show an analysis error."""
        self._is_analyzing = False
        self.analyze_btn.setText("开始分析")
        self.analyze_btn.setEnabled(True)
        self._show_status(error_msg, is_error=True)

    def _show_status(self, message: str, is_error: bool = False) -> None:
        self.status_label.setVisible(bool(message))
        color = ERROR if is_error else TEXT_MUTED
        self.status_label.setStyleSheet(f"color: {color}; font-size: 13px;")
        self.status_label.setText(message)

    @staticmethod
    def _parse_explanation_steps(text: str) -> list:
        """Try to parse numbered steps from AI response text."""
        steps = []
        pattern = re.compile(
            r"(?:^|\n)\s*(?:\d+[\.\)、]|[-*])\s*(.+?)(?:\n|$)(.*?)(?=\n\s*(?:\d+[\.\)、]|[-*])\s|\Z)", re.DOTALL
        )
        for m in pattern.finditer(text):
            title = m.group(1).strip().rstrip("：:")
            body = m.group(2).strip()
            if title:
                steps.append((title, body if body else ""))
        if len(steps) < 2:
            return []
        return steps

    @staticmethod
    def _plain_to_html(text: str) -> str:
        """Convert plain text with markdown-like formatting to basic HTML."""
        html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(
            r"`(.+?)`", r"<code style='background:#f1f5f9;padding:2px 6px;border-radius:4px;'>\1</code>", html
        )
        html = html.replace("\n", "<br>")
        return html


# ── Standalone Dialog Wrapper ────────────────────────────────────────────────


class CodeAnalyzerDialog(QWidget):
    """Standalone dialog wrapper for the CodeAnalyzerPanel."""

    def __init__(self, code: str, language: str = "python", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI 代码分析")
        self.setMinimumSize(760, 620)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.panel = CodeAnalyzerPanel(self)
        self.panel.set_code(code, language)
        layout.addWidget(self.panel)
