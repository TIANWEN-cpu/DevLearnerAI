FONT = "Microsoft YaHei UI"
MONO_FONT = "Consolas"
F_BASE = 33
F_TITLE = 63
F_SUB = 41
F_CODE = 31
BTN_H = 64

BG_BASE = "#eef4f8"
BG_SHELL = "#f6f8fb"
BG_CARD = "#fffdf8"
BG_CARD_SOFT = "#f8fbff"
BG_SIDEBAR = "#e8eff5"
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
ACCENT_PRESSED = "#1e40af"
ACCENT_SOFT = "#dbeafe"
TEXT_MAIN = "#152033"
TEXT_SUB = "#5f6f86"
TEXT_MUTED = "#8b98ab"
BORDER = "rgba(37, 99, 235, 0.10)"
BORDER_STRONG = "rgba(21, 32, 51, 0.12)"

GLOBAL_STYLE = f"""
QWidget {{
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", "{FONT}", Helvetica, Arial, sans-serif;
    font-size: {F_BASE}px;
    color: {TEXT_MAIN};
    background: transparent;
}}
QMainWindow {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {BG_BASE},
        stop: 0.55 {BG_SHELL},
        stop: 1 #edf6ff
    );
}}
QTabWidget::pane {{
    border: 0;
    top: -2px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: rgba(255, 255, 255, 0.5);
    border: 1px solid rgba(0, 0, 0, 0.05);
    border-radius: 12px;
    padding: 14px 30px;
    margin: 6px 9px 12px 0;
    min-width: 120px;
    color: #3a3a3c;
}}
QTabBar::tab:selected {{
    background: #ffffff;
    color: #000000;
    border: 1px solid rgba(0, 0, 0, 0.1);
    box-shadow: 0 3px 6px rgba(0,0,0,0.05);
}}
QPushButton {{
    background: {ACCENT};
    border: none;
    border-radius: 14px;
    padding: 16px 28px;
    min-height: {BTN_H}px;
    color: white;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {ACCENT_HOVER};
}}
QPushButton:pressed {{
    background: {ACCENT_PRESSED};
}}
QPushButton[nav="true"] {{
    background: transparent;
    border: none;
    border-radius: 12px;
    color: {TEXT_MAIN};
    text-align: left;
    padding: 18px 24px;
    min-height: 84px;
    font-weight: 500;
}}
QPushButton[nav="true"][compact="true"] {{
    text-align: center;
    padding: 0;
    min-height: 72px;
    max-height: 72px;
    border-radius: 18px;
    font-size: 28px;
    font-weight: 700;
}}
QPushButton[nav="true"]:hover {{
    background: rgba(37, 99, 235, 0.08);
}}
QPushButton[nav="true"][active="true"] {{
    background: {ACCENT_SOFT};
    color: {ACCENT};
    font-weight: 600;
}}
QPushButton[variant="secondary"] {{
    background: {BG_CARD};
    border: 1px solid {BORDER_STRONG};
    color: {TEXT_MAIN};
    border-radius: 14px;
}}
QPushButton[variant="secondary"]:hover {{
    background: #f2f7fd;
}}
QPushButton[variant="ghost"] {{
    background: transparent;
    border: none;
    color: {ACCENT};
}}
QPushButton[variant="ghost"]:hover {{
    background: rgba(37, 99, 235, 0.10);
    border-radius: 12px;
}}
QTextEdit, QPlainTextEdit, QTextBrowser, QListWidget, QLineEdit, QComboBox, QTableWidget {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 16px;
    selection-background-color: rgba(37, 99, 235, 0.25);
}}
QTextEdit:focus, QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus {{
    border: 2px solid rgba(37, 99, 235, 0.45);
    background: {BG_CARD};
}}
QListWidget::item {{
    border-radius: 9px;
    padding: 20px 16px;
    margin: 4px 0;
    min-height: 40px;
    color: {TEXT_MAIN};
}}
QListWidget::item:hover {{
    background: rgba(37, 99, 235, 0.07);
}}
QListWidget::item:selected {{
    background: {ACCENT};
    color: white;
    font-weight: 600;
}}
QLineEdit, QComboBox {{
    min-height: 60px;
}}
QComboBox::drop-down {{
    border: none;
    width: 36px;
}}
QComboBox::down-arrow {{
    image: none;
}}
QTableWidget {{
    gridline-color: rgba(0, 0, 0, 0.05);
    alternate-background-color: #fbfdff;
}}
QTableWidget::item {{
    padding: 8px 12px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}}
QTableWidget::item:selected {{
    background: rgba(37, 99, 235, 0.12);
    color: {ACCENT};
    font-weight: 600;
}}
QHeaderView::section {{
    background: #edf3f9;
    color: {TEXT_MUTED};
    padding: 16px;
    border: none;
    border-bottom: 1px solid {BORDER};
    font-weight: 600;
}}
QGroupBox {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 18px;
    margin-top: 24px;
    padding-top: 20px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 24px;
    top: 0px;
    padding: 0 6px;
    color: {TEXT_MUTED};
    font-weight: 600;
}}
QProgressBar {{
    background: #dde7f1;
    border: none;
    border-radius: 9px;
    min-height: 26px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    border-radius: 9px;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #2563eb,
        stop: 1 #14b8a6
    );
}}
QDockWidget {{
    color: #1c1c1e;
}}
QDockWidget::title {{
    background: #edf3f9;
    border-bottom: 1px solid {BORDER};
    padding: 16px 24px;
    text-align: left;
    color: {TEXT_MAIN};
    font-weight: 600;
}}
QStatusBar {{
    background: #edf3f9;
    border-top: 1px solid {BORDER};
    color: {TEXT_MUTED};
}}
QSplitter::handle {{
    background: transparent;
    width: 12px;
    height: 12px;
}}
QScrollBar:vertical {{
    width: 8px;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    background: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(0, 0, 0, 0.3);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    height: 8px;
    background: transparent;
}}
QScrollBar::handle:horizontal {{
    background: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: rgba(0, 0, 0, 0.3);
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QMenu {{
    background: {BG_CARD};
    color: {TEXT_MAIN};
    border: 1px solid {BORDER_STRONG};
    border-radius: 14px;
    padding: 10px 0;
}}
QMenu::item {{
    background: transparent;
    color: {TEXT_MAIN};
    padding: 12px 24px 12px 24px;
    margin: 2px 8px;
    border-radius: 10px;
}}
QMenu::item:selected {{
    background: rgba(37, 99, 235, 0.12);
    color: {ACCENT};
}}
QMenu::separator {{
    height: 1px;
    background: rgba(37, 99, 235, 0.08);
    margin: 8px 14px;
}}
"""
