"""Shared fixtures for DevLearnerAI tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure the project root is importable so `from app import ...` works
# regardless of how pytest is invoked.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# PyQt5 mock -- allows importing app.ai and app.window without a real Qt
# installation.  Tests that need real Qt widgets should install PyQt5 or
# skip themselves.
# ---------------------------------------------------------------------------
if "PyQt5" not in sys.modules:
    _pyqt5 = MagicMock()
    # QtCore
    _pyqt5.QtCore.QSize = type("QSize", (), {"__init__": lambda self, *a, **k: None})
    _pyqt5.QtCore.Qt = type(
        "Qt",
        (),
        {
            "Horizontal": 1,
            "RightDockWidgetArea": 2,
            "ScrollBarAsNeeded": 0,
            "AlignRight": 2,
            "WA_OpaquePaintEvent": 1,
            "WA_StaticContents": 2,
            "UserRole": 256,
        },
    )()
    _pyqt5.QtCore.pyqtSignal = lambda *a, **k: MagicMock()
    _pyqt5.QtCore.QPropertyAnimation = type("QPropertyAnimation", (), {"__init__": lambda *a, **k: None})
    _pyqt5.QtCore.QEasingCurve = type("QEasingCurve", (), {"InOutQuad": 0})()
    _pyqt5.QtCore.QDate = MagicMock()
    # QtGui
    _pyqt5.QtGui.QFont = type("QFont", (), {"Bold": 75, "__init__": lambda *a, **k: None})
    _pyqt5.QtGui.QKeySequence = type("QKeySequence", (), {"__init__": lambda *a, **k: None})
    _pyqt5.QtGui.QColor = type("QColor", (), {"__init__": lambda *a, **k: None})
    _pyqt5.QtGui.QSyntaxHighlighter = type(
        "QSyntaxHighlighter",
        (),
        {
            "__init__": lambda self, parent=None: None,
            "setFormat": lambda *a, **k: None,
            "setCurrentBlockState": lambda *a, **k: None,
            "previousBlockState": lambda self: 0,
            "format": lambda self, pos: None,
        },
    )
    _pyqt5.QtGui.QTextCharFormat = type(
        "QTextCharFormat",
        (),
        {
            "__init__": lambda self: None,
            "setForeground": lambda *a, **k: None,
            "setFontWeight": lambda *a, **k: None,
            "setFontItalic": lambda *a, **k: None,
            "setBackground": lambda *a, **k: None,
            "setProperty": lambda *a, **k: None,
            "foreground": lambda self: MagicMock(color=MagicMock(return_value=MagicMock())),
            "FullWidthSelection": 0,
        },
    )
    _pyqt5.QtGui.QTextCursor = type("QTextCursor", (), {"End": 11})
    _pyqt5.QtGui.QPainter = type("QPainter", (), {"__init__": lambda *a, **k: None})

    # QtWidgets
    class _FakeWidget:
        def __init__(self, *a, **k):
            self._mock_signals = {}

        def __getattr__(self, name):
            # Return MagicMock for any signal-like or unknown attribute
            if name.startswith("_"):
                raise AttributeError(name)
            if name not in self._mock_signals:
                self._mock_signals[name] = MagicMock()
            return self._mock_signals[name]

        def style(self):
            return MagicMock(unpolish=lambda *a: None, polish=lambda *a: None)

    class _FakeMainWindow(_FakeWidget):
        pass

    for cls_name in [
        "QWidget",
        "QFrame",
        "QLabel",
        "QPushButton",
        "QVBoxLayout",
        "QHBoxLayout",
        "QScrollArea",
        "QStackedWidget",
        "QStatusBar",
        "QAction",
        "QSplitter",
        "QTabWidget",
        "QCheckBox",
        "QComboBox",
        "QListWidget",
        "QListWidgetItem",
        "QLineEdit",
        "QTextEdit",
        "QPlainTextEdit",
        "QTextBrowser",
        "QPushButton",
        "QDialog",
        "QFileDialog",
        "QInputDialog",
        "QMessageBox",
        "QDockWidget",
        "QGroupBox",
        "QApplication",
    ]:
        setattr(_pyqt5.QtWidgets, cls_name, type(cls_name, (_FakeWidget,), {}))
    _pyqt5.QtWidgets.QMainWindow = type("QMainWindow", (_FakeMainWindow,), {})
    _pyqt5.QtWidgets.QApplication.instance = staticmethod(lambda: None)
    _pyqt5.QtWidgets.QApplication.primaryScreen = lambda self: None
    _pyqt5.QtWidgets.QScrollArea.NoFrame = 0
    # QGraphicsDropShadowEffect / QGraphicsOpacityEffect
    _pyqt5.QtWidgets.QGraphicsDropShadowEffect = type(
        "QGraphicsDropShadowEffect",
        (_FakeWidget,),
        {
            "setBlurRadius": lambda *a: None,
            "setOffset": lambda *a: None,
            "setColor": lambda *a: None,
        },
    )
    _pyqt5.QtWidgets.QGraphicsOpacityEffect = type(
        "QGraphicsOpacityEffect",
        (_FakeWidget,),
        {
            "setOpacity": lambda *a: None,
        },
    )

    sys.modules["PyQt5"] = _pyqt5
    sys.modules["PyQt5.QtCore"] = _pyqt5.QtCore
    sys.modules["PyQt5.QtGui"] = _pyqt5.QtGui
    sys.modules["PyQt5.QtWidgets"] = _pyqt5.QtWidgets
