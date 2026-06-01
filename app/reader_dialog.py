from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.localized_inputs import LocalizedTextBrowser
from app.styles import F_TITLE, FONT


class ReaderDialog(QDialog):
    def __init__(self, title: str, html: str, meta: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or "放大阅读")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

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

        self.setStyleSheet(
            """
            QDialog {
                background: #f5f5f7;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

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
            meta_label.setStyleSheet("color: #64748b; font-size: 18px;")
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
            code { background: #f5f5f7; border-radius: 8px; padding: 2px 6px; color: #007aff; }
            pre { background: #eff6ff; border-radius: 16px; padding: 22px; }
            a { color: #007aff; }
            """
        )
        self.browser.setHtml(html or "")
        card_layout.addWidget(self.browser, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setProperty("variant", "secondary")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        card_layout.addLayout(footer)

        layout.addWidget(card, 1)
