"""Application style constants and global stylesheet.

Provides a consistent color scheme, typography scale, and full PyQt5
stylesheet for both light and dark themes.  Font sizes are stored as
module-level constants so every widget reads from a single source of
truth.
"""

# ── Typography ───────────────────────────────────────────────────────────────

FONT = "Microsoft YaHei UI"
MONO_FONT = "Consolas"
F_BASE = 33
F_TITLE = 63
F_SUB = 41
F_CODE = 31
BTN_H = 64

# ── Light theme palette ──────────────────────────────────────────────────────

BG_BASE = "#eef4f8"
BG_SHELL = "#f6f8fb"
BG_CARD = "#fffdf8"
BG_CARD_SOFT = "#f8fbff"
BG_SIDEBAR = "#e8eff5"
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
ACCENT_PRESSED = "#1e40af"
ACCENT_SOFT = "#dbeafe"
TEXT_MAIN = "#0f1a2e"
TEXT_SUB = "#3a506b"
TEXT_MUTED = "#556880"
BORDER = "rgba(37, 99, 235, 0.10)"
BORDER_STRONG = "rgba(21, 32, 51, 0.12)"

# ── Semantic colours ─────────────────────────────────────────────────────────

SUCCESS = "#22c55e"
SUCCESS_SOFT = "#dcfce7"
WARNING = "#f59e0b"
WARNING_SOFT = "#fef3c7"
ERROR = "#ef4444"
ERROR_SOFT = "#fee2e2"
INFO = "#3b82f6"
INFO_SOFT = "#dbeafe"

# ── Score thresholds (used by practice/dashboard) ────────────────────────────

SCORE_EXCELLENT = 90
SCORE_GOOD = 70
SCORE_PASS = 50

# ── Dark theme palette ───────────────────────────────────────────────────────

DARK_BG_BASE = "#0c1222"
DARK_BG_SHELL = "#162035"
DARK_BG_CARD = "#1a2740"
DARK_BG_CARD_SOFT = "#1f2f4d"
DARK_BG_SIDEBAR = "#131d30"
DARK_ACCENT = "#60a5fa"
DARK_ACCENT_HOVER = "#93c5fd"
DARK_ACCENT_PRESSED = "#3b82f6"
DARK_ACCENT_SOFT = "#1e3a5f"
DARK_TEXT_MAIN = "#f1f5f9"
DARK_TEXT_SUB = "#b0c0d4"
DARK_TEXT_MUTED = "#8a9bb5"
DARK_BORDER = "rgba(96, 165, 250, 0.18)"
DARK_BORDER_STRONG = "rgba(241, 245, 249, 0.12)"

# ── Font size presets ────────────────────────────────────────────────────────

FONT_SIZES = {
    "small": {"base": 28, "title": 54, "sub": 36, "code": 26},
    "medium": {"base": 33, "title": 63, "sub": 41, "code": 31},
    "large": {"base": 40, "title": 72, "sub": 48, "code": 38},
}

# ── Stylesheet cache ─────────────────────────────────────────────────────────

_style_cache: dict[tuple, str] = {}


def clear_style_cache() -> None:
    """Clear the stylesheet cache (e.g. after external color changes)."""
    _style_cache.clear()


def set_font_size(size_name: str) -> None:
    """Apply a font-size preset globally (call before stylesheet build).

    .. deprecated::
        Prefer ``build_style_for_size(size_name)`` which does not mutate
        module-level state. This function will be removed in a future release.
    """
    import warnings

    warnings.warn(
        "styles.set_font_size() mutates module globals and is deprecated. Use build_style_for_size() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    global F_BASE, F_TITLE, F_SUB, F_CODE
    preset = FONT_SIZES.get(size_name, FONT_SIZES["medium"])
    F_BASE = preset["base"]
    F_TITLE = preset["title"]
    F_SUB = preset["sub"]
    F_CODE = preset["code"]


# ── Score helpers ────────────────────────────────────────────────────────────


def score_color(score: int) -> str:
    """Return a hex colour appropriate for the given score value."""
    if score >= SCORE_EXCELLENT:
        return SUCCESS
    if score >= SCORE_GOOD:
        return ACCENT
    if score >= SCORE_PASS:
        return WARNING
    return ERROR


def score_label(score: int) -> str:
    """Return a short human-readable label for a score."""
    from app.i18n import tr

    if score >= SCORE_EXCELLENT:
        return tr("score.excellent")
    if score >= SCORE_GOOD:
        return tr("score.good")
    if score >= SCORE_PASS:
        return tr("score.pass")
    return tr("score.fail")


# ── Dynamic stylesheet builder ───────────────────────────────────────────────


def _build_global_style(
    bg_base: str = BG_BASE,
    bg_shell: str = BG_SHELL,
    bg_card: str = BG_CARD,
    bg_card_soft: str = BG_CARD_SOFT,
    accent: str = ACCENT,
    accent_hover: str = ACCENT_HOVER,
    accent_pressed: str = ACCENT_PRESSED,
    accent_soft: str = ACCENT_SOFT,
    text_main: str = TEXT_MAIN,
    text_sub: str = TEXT_SUB,
    text_muted: str = TEXT_MUTED,
    border: str = BORDER,
    border_strong: str = BORDER_STRONG,
    f_base: int = F_BASE,
    f_title: int = F_TITLE,
    f_sub: int = F_SUB,
    f_code: int = F_CODE,
    btn_h: int = BTN_H,
) -> str:
    """Build the full application stylesheet from palette parameters.

    Results are cached so repeated calls with identical parameters
    (e.g. toggling theme back and forth) return the same string object.
    """
    cache_key = (
        bg_base,
        bg_shell,
        bg_card,
        bg_card_soft,
        accent,
        accent_hover,
        accent_pressed,
        accent_soft,
        text_main,
        text_sub,
        text_muted,
        border,
        border_strong,
        f_base,
        f_title,
        f_sub,
        f_code,
        btn_h,
    )
    cached = _style_cache.get(cache_key)
    if cached is not None:
        return cached

    result = f"""
QWidget {{
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", "{FONT}", Helvetica, Arial, sans-serif;
    font-size: {f_base}px;
    color: {text_main};
    background: transparent;
}}
QMainWindow {{
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {bg_base},
        stop: 0.55 {bg_shell},
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
    color: {text_main};
}}
QTabBar::tab:selected {{
    background: #ffffff;
    color: {text_main};
    border: 1px solid rgba(0, 0, 0, 0.1);
}}
QPushButton {{
    background: {accent};
    border: none;
    border-radius: 14px;
    padding: 16px 28px;
    min-height: {btn_h}px;
    color: white;
    font-weight: 600;
    cursor: pointer;
}}
QPushButton:hover {{
    background: {accent_hover};
}}
QPushButton:pressed {{
    background: {accent_pressed};
}}
QPushButton[nav="true"] {{
    background: transparent;
    border: none;
    border-radius: 12px;
    color: {text_main};
    text-align: left;
    padding: 18px 24px;
    min-height: 84px;
    font-weight: 500;
    cursor: pointer;
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
    background: {accent_soft};
    color: {accent};
    font-weight: 600;
}}
QPushButton[variant="secondary"] {{
    background: {bg_card};
    border: 1px solid {border_strong};
    color: {text_main};
    border-radius: 14px;
    cursor: pointer;
}}
QPushButton[variant="secondary"]:hover {{
    background: #f2f7fd;
}}
QPushButton[variant="ghost"] {{
    background: transparent;
    border: none;
    color: {accent};
    cursor: pointer;
}}
QPushButton[variant="ghost"]:hover {{
    background: rgba(37, 99, 235, 0.10);
    border-radius: 12px;
}}
QTextEdit, QPlainTextEdit, QTextBrowser, QListWidget, QLineEdit, QComboBox, QTableWidget {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: 14px;
    padding: 16px;
    selection-background-color: rgba(37, 99, 235, 0.25);
}}
QTextEdit:focus, QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus {{
    border: 2px solid rgba(37, 99, 235, 0.45);
    background: {bg_card};
}}
QListWidget::item {{
    border-radius: 9px;
    padding: 20px 16px;
    margin: 4px 0;
    min-height: 40px;
    color: {text_main};
}}
QListWidget::item:hover {{
    background: rgba(37, 99, 235, 0.07);
}}
QListWidget::item:selected {{
    background: {accent};
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
    color: {accent};
    font-weight: 600;
}}
QHeaderView::section {{
    background: #edf3f9;
    color: {text_muted};
    padding: 16px;
    border: none;
    border-bottom: 1px solid {border};
    font-weight: 600;
}}
QGroupBox {{
    background: {bg_card};
    border: 1px solid {border};
    border-radius: 18px;
    margin-top: 24px;
    padding-top: 20px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 24px;
    top: 0px;
    padding: 0 6px;
    color: {text_muted};
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
    color: {text_main};
}}
QDockWidget::title {{
    background: #edf3f9;
    border-bottom: 1px solid {border};
    padding: 16px 24px;
    text-align: left;
    color: {text_main};
    font-weight: 600;
}}
QStatusBar {{
    background: #edf3f9;
    border-top: 1px solid {border};
    color: {text_muted};
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
    background: {bg_card};
    color: {text_main};
    border: 1px solid {border_strong};
    border-radius: 14px;
    padding: 10px 0;
}}
QMenu::item {{
    background: transparent;
    color: {text_main};
    padding: 12px 24px 12px 24px;
    margin: 2px 8px;
    border-radius: 10px;
}}
QMenu::item:selected {{
    background: rgba(37, 99, 235, 0.12);
    color: {accent};
}}
QMenu::separator {{
    height: 1px;
    background: rgba(37, 99, 235, 0.08);
    margin: 8px 14px;
}}
/* ── Keyboard focus indicators (a11y) ────────────────────────────────── */
QPushButton:focus-visible,
QComboBox:focus-visible,
QLineEdit:focus-visible,
QTextEdit:focus-visible,
QPlainTextEdit:focus-visible,
QListWidget:focus-visible,
QSpinBox:focus-visible,
QTabBar::tab:focus-visible {{
    outline: 2px solid {accent};
    outline-offset: 2px;
    border: 2px solid {accent};
}}
QScrollArea:focus-visible {{
    outline: 1px dashed {accent};
    outline-offset: -1px;
}}
"""
    _style_cache[cache_key] = result
    return result


# Default (light) stylesheet
GLOBAL_STYLE = _build_global_style()


def build_dark_style() -> str:
    """Return a dark-theme version of the global stylesheet."""
    return _build_global_style(
        bg_base=DARK_BG_BASE,
        bg_shell=DARK_BG_SHELL,
        bg_card=DARK_BG_CARD,
        bg_card_soft=DARK_BG_CARD_SOFT,
        accent=DARK_ACCENT,
        accent_hover=DARK_ACCENT_HOVER,
        accent_pressed=DARK_ACCENT_PRESSED,
        accent_soft=DARK_ACCENT_SOFT,
        text_main=DARK_TEXT_MAIN,
        text_sub=DARK_TEXT_SUB,
        text_muted=DARK_TEXT_MUTED,
        border=DARK_BORDER,
        border_strong=DARK_BORDER_STRONG,
    )


def build_style_for_size(size_name: str, dark: bool = False) -> str:
    """Build stylesheet for a given font size and optional dark theme."""
    preset = FONT_SIZES.get(size_name, FONT_SIZES["medium"])
    kwargs = dict(
        f_base=preset["base"],
        f_title=preset["title"],
        f_sub=preset["sub"],
        f_code=preset["code"],
    )
    if dark:
        kwargs.update(
            bg_base=DARK_BG_BASE,
            bg_shell=DARK_BG_SHELL,
            bg_card=DARK_BG_CARD,
            bg_card_soft=DARK_BG_CARD_SOFT,
            accent=DARK_ACCENT,
            accent_hover=DARK_ACCENT_HOVER,
            accent_pressed=DARK_ACCENT_PRESSED,
            accent_soft=DARK_ACCENT_SOFT,
            text_main=DARK_TEXT_MAIN,
            text_sub=DARK_TEXT_SUB,
            text_muted=DARK_TEXT_MUTED,
            border=DARK_BORDER,
            border_strong=DARK_BORDER_STRONG,
        )
    return _build_global_style(**kwargs)
