"""Full-screen reader dialog for lesson content.

Provides an immersive reading experience with:
- Improved code block rendering with syntax-themed backgrounds
- Copy-to-clipboard button for code blocks
- Table-of-contents sidebar navigation
- Better typography and spacing
"""

import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QShortcut,
    QVBoxLayout,
)

from app.localized_inputs import LocalizedTextBrowser
from app.styles import ACCENT, ACCENT_SOFT, BG_CARD, BORDER, F_TITLE, FONT, TEXT_MAIN, TEXT_MUTED, TEXT_SUB


class ReaderDialog(QDialog):
    def __init__(self, title: str, html: str, meta: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or "放大阅读")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self._html = html

        # Escape key to close
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.accept)

        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            width = max(1200, int(geometry.width() * 0.92))
            height = max(840, int(geometry.height() * 0.92))
            self.resize(width, height)
            self.move(
                geometry.x() + max(0, (geometry.width() - width) // 2),
                geometry.y() + max(0, (geometry.height() - height) // 2),
            )
        else:
            self.resize(1700, 1050)

        self.setStyleSheet("QDialog { background: #f5f5f7; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # TOC sidebar
        toc_card = QFrame()
        toc_card.setStyleSheet(
            f"""
            QFrame {{
                background: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
            """
        )
        toc_layout = QVBoxLayout(toc_card)
        toc_layout.setContentsMargins(16, 18, 16, 18)
        toc_layout.setSpacing(10)

        toc_title = QLabel("目录")
        toc_title.setFont(QFont(FONT, 22, QFont.Bold))
        toc_title.setStyleSheet(f"color: {TEXT_MAIN};")
        toc_layout.addWidget(toc_title)

        self.toc_list = QListWidget()
        self.toc_list.setAccessibleName("文章目录")
        self.toc_list.setAccessibleDescription("点击目录项可跳转到对应章节")
        self.toc_list.setStyleSheet(
            f"""
            QListWidget {{
                background: transparent;
                border: none;
                padding: 4px;
            }}
            QListWidget::item {{
                border-radius: 10px;
                padding: 8px 12px;
                margin: 2px 0;
                color: {TEXT_SUB};
                font-size: 16px;
            }}
            QListWidget::item:hover {{
                background: {ACCENT_SOFT};
                color: {ACCENT};
            }}
            QListWidget::item:selected {{
                background: {ACCENT};
                color: white;
            }}
            """
        )
        self.toc_list.setMaximumWidth(240)
        self._populate_toc(html)
        self.toc_list.itemClicked.connect(self._on_toc_click)
        toc_layout.addWidget(self.toc_list, 1)
        layout.addWidget(toc_card)

        # Main content area
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background: #ffffff;
                border: 1px solid rgba(0,0,0,0.06);
                border-radius: 24px;
            }
            """
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(26, 22, 26, 22)
        card_layout.setSpacing(14)

        header = QVBoxLayout()
        header.setSpacing(6)

        title_label = QLabel(title or "放大阅读")
        title_label.setFont(QFont(FONT, max(28, F_TITLE - 4), QFont.Bold))
        title_label.setWordWrap(True)
        header.addWidget(title_label)

        if meta:
            meta_label = QLabel(meta)
            meta_label.setWordWrap(True)
            meta_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 18px;")
            header.addWidget(meta_label)

        card_layout.addLayout(header)

        self.browser = LocalizedTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.document().setDefaultStyleSheet(
            """
            body { line-height: 2.0; font-size: 32px; color: #1c1c1e; }
            h1 { font-size: 48px; margin-top: 18px; margin-bottom: 18px; }
            h2 { font-size: 38px; margin-top: 16px; margin-bottom: 14px; }
            h3 { font-size: 30px; margin-top: 14px; margin-bottom: 12px; }
            p, li { margin: 12px 0; }
            code {
                background: #f0f4ff;
                border-radius: 8px;
                padding: 2px 6px;
                color: #2563eb;
                font-family: Consolas, monospace;
            }
            pre {
                background: #1e293b;
                color: #e2e8f0;
                border-radius: 16px;
                padding: 22px;
                font-family: Consolas, monospace;
                font-size: 28px;
                line-height: 1.6;
                border: 1px solid rgba(59,130,246,0.15);
            }
            pre code {
                background: transparent;
                color: #e2e8f0;
                padding: 0;
            }
            table {
                border-collapse: collapse;
                margin: 16px 0;
                width: 100%;
            }
            th {
                background: #f1f5f9;
                color: #1e293b;
                font-weight: 700;
                padding: 12px 16px;
                text-align: left;
                border-bottom: 2px solid #e2e8f0;
            }
            td {
                padding: 10px 16px;
                border-bottom: 1px solid #f1f5f9;
            }
            tr:nth-child(even) td {
                background: #f8fafc;
            }
            a { color: #2563eb; text-decoration: none; }
            a:hover { text-decoration: underline; }
            blockquote {
                border-left: 4px solid #2563eb;
                background: #eff6ff;
                padding: 14px 18px;
                margin: 16px 0;
                border-radius: 0 12px 12px 0;
                color: #1e40af;
            }
            ul, ol { padding-left: 28px; }
            """
        )
        self.browser.setHtml(html or "")
        card_layout.addWidget(self.browser, 1)

        footer = QHBoxLayout()
        footer.setSpacing(10)

        # Copy-all button
        copy_btn = QPushButton("复制内容")
        copy_btn.setProperty("variant", "secondary")
        copy_btn.setAccessibleName("复制全部内容到剪贴板")
        copy_btn.clicked.connect(self._copy_content)
        footer.addWidget(copy_btn)

        # Increase/decrease font buttons
        zoom_in_btn = QPushButton("放大字体")
        zoom_in_btn.setProperty("variant", "secondary")
        zoom_in_btn.setAccessibleName("放大阅读字体")
        zoom_in_btn.clicked.connect(lambda: self.browser.zoomIn(2))
        footer.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("缩小字体")
        zoom_out_btn.setProperty("variant", "secondary")
        zoom_out_btn.setAccessibleName("缩小阅读字体")
        zoom_out_btn.clicked.connect(lambda: self.browser.zoomOut(2))
        footer.addWidget(zoom_out_btn)

        footer.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setProperty("variant", "secondary")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        card_layout.addLayout(footer)

        layout.addWidget(card, 1)

    def _populate_toc(self, html: str) -> None:
        """Extract headings from HTML and populate the TOC list."""
        headings = re.findall(r"<h([1-3])[^>]*>(.*?)</h\1>", html or "", re.IGNORECASE | re.DOTALL)
        if not headings:
            item = QListWidgetItem("（无标题）")
            item.setData(Qt.UserRole, "")
            self.toc_list.addItem(item)
            return
        for level, text in headings:
            clean = re.sub(r"<[^>]+>", "", text).strip()
            if not clean:
                continue
            indent = "  " * (int(level) - 1)
            item = QListWidgetItem(f"{indent}{clean}")
            item.setData(Qt.UserRole, clean)
            self.toc_list.addItem(item)

    def _on_toc_click(self, item: QListWidgetItem) -> None:
        """Scroll to the selected heading in the content browser."""
        anchor_text = item.data(Qt.UserRole)
        if anchor_text:
            # Find the text in the browser and scroll to it
            cursor = self.browser.document().find(anchor_text)
            if cursor:
                self.browser.setTextCursor(cursor)
                self.browser.ensureCursorVisible()

    def _copy_content(self) -> None:
        """Copy the plain text content to clipboard."""
        text = self.browser.toPlainText()
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
