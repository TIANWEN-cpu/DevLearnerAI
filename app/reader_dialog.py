"""Full-screen reader dialog for lesson content.

Provides an immersive reading experience with:
- Improved code block rendering with syntax-themed backgrounds
- Per-code-block copy buttons (click the "复制" link inside each code block)
- Table-of-contents sidebar navigation with anchor-based scrolling
- Better typography and spacing
"""

import re
from html import unescape

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


def _make_heading_id(text: str, counter: dict[str, int]) -> str:
    """Generate a unique anchor id for a heading."""
    slug = re.sub(r"[^a-zA-Z0-9一-鿿]+", "-", text).strip("-").lower()
    if not slug:
        slug = "heading"
    count = counter.get(slug, 0)
    counter[slug] = count + 1
    return f"{slug}-{count}" if count > 0 else slug


def _strip_tags(html_text: str) -> str:
    """Remove HTML tags and decode entities to get plain text."""
    return unescape(re.sub(r"<[^>]+>", "", html_text)).strip()


def _add_code_copy_buttons(html: str, copy_index: list[str]) -> str:
    """Inject a copy button into each <pre> code block.

    Each button is an anchor link with href="copy:<index>" so the
    ``anchorClicked`` signal can intercept it.
    """

    def _replace_pre(match: re.Match) -> str:
        code_html = match.group(1)
        plain = _strip_tags(code_html)
        idx = len(copy_index)
        copy_index.append(plain)
        btn = (
            f'<div style="text-align:right;margin-bottom:4px;">'
            f'<a href="copy:{idx}" style="color:#93c5fd;font-size:13px;'
            f"text-decoration:none;background:rgba(147,197,253,0.15);"
            f'padding:2px 8px;border-radius:6px;">复制</a></div>'
        )
        return f"<pre>{btn}{code_html}</pre>"

    return re.sub(r"<pre(?:\s[^>]*)?>(.*?)</pre>", _replace_pre, html, flags=re.DOTALL | re.IGNORECASE)


def _add_heading_anchors(html: str, anchor_map: dict[str, str]) -> str:
    """Add id attributes to <h1>/<h2>/<h3> tags for TOC navigation."""
    counter: dict[str, int] = {}

    def _replace_heading(match: re.Match) -> str:
        tag = match.group(1)
        _attrs = match.group(2) or ""  # captured but unused; kept for regex group alignment
        inner = match.group(3)
        text = _strip_tags(inner)
        hid = _make_heading_id(text, counter)
        anchor_map[hid] = text
        return f'<h{tag} id="{hid}">{inner}</h{tag}>'

    return re.sub(
        r"<h([1-3])([^>]*)>(.*?)</h\1>",
        _replace_heading,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


class ReaderDialog(QDialog):
    def __init__(self, title: str, html: str, meta: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or "放大阅读")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        # Escape key to close
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.accept)

        # Pre-process HTML: add heading anchors and code copy buttons
        self._anchor_map: dict[str, str] = {}
        self._copy_index: list[str] = []
        processed_html = _add_heading_anchors(html or "", self._anchor_map)
        processed_html = _add_code_copy_buttons(processed_html, self._copy_index)
        self._full_html = processed_html

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
        self._populate_toc(html or "")
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
        # Let internal links (code copy buttons) be handled by Python
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(self._on_anchor_clicked)
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
        self.browser.setHtml(processed_html)
        card_layout.addWidget(self.browser, 1)

        # Status label for "copied" feedback
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {ACCENT}; font-size: 15px; font-weight: 600; padding: 4px 0;")
        self._status_label.setVisible(False)
        card_layout.addWidget(self._status_label)

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
        # Use the anchor map built during preprocessing
        if self._anchor_map:
            for anchor_id, text in self._anchor_map.items():
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, anchor_id)
                self.toc_list.addItem(item)
            return

        # Fallback: extract from raw HTML
        headings = re.findall(r"<h([1-3])[^>]*>(.*?)</h\1>", html, re.IGNORECASE | re.DOTALL)
        if not headings:
            item = QListWidgetItem("（无标题）")
            item.setData(Qt.UserRole, "")
            self.toc_list.addItem(item)
            return
        for level, text in headings:
            clean = _strip_tags(text)
            if not clean:
                continue
            indent = "  " * (int(level) - 1)
            item = QListWidgetItem(f"{indent}{clean}")
            item.setData(Qt.UserRole, clean)
            self.toc_list.addItem(item)

    def _on_toc_click(self, item: QListWidgetItem) -> None:
        """Scroll to the selected heading in the content browser."""
        anchor_id = item.data(Qt.UserRole)
        if not anchor_id:
            return
        # If we have a proper anchor id (from preprocessing), scroll to it
        if anchor_id in self._anchor_map:
            self.browser.scrollToAnchor(anchor_id)
            return
        # Fallback: use text search
        cursor = self.browser.document().find(anchor_id)
        if cursor:
            self.browser.setTextCursor(cursor)
            self.browser.ensureCursorVisible()

    def _on_anchor_clicked(self, url) -> None:
        """Handle internal link clicks -- used for code block copy buttons."""
        href = url.toString()
        if href.startswith("copy:"):
            try:
                idx = int(href.split(":", 1)[1])
                if 0 <= idx < len(self._copy_index):
                    clipboard = QApplication.clipboard()
                    if clipboard:
                        clipboard.setText(self._copy_index[idx])
                    self._show_status("代码已复制到剪贴板")
            except (ValueError, IndexError):
                pass
        elif href.startswith("http"):
            # External links -- open in system browser
            import webbrowser

            webbrowser.open(href)

    def _show_status(self, message: str) -> None:
        """Show a brief status message that auto-hides."""
        self._status_label.setText(message)
        self._status_label.setVisible(True)
        from PyQt5.QtCore import QTimer

        QTimer.singleShot(2000, lambda: self._status_label.setVisible(False))

    def _copy_content(self) -> None:
        """Copy the plain text content to clipboard."""
        text = self.browser.toPlainText()
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
        self._show_status("全部内容已复制到剪贴板")
