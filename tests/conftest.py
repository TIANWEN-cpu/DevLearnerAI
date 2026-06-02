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
    _pyqt5.QtCore.QSize = type("QSize", (), {})
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
            pass

        def setStyleSheet(self, *a):
            pass

        def setLayout(self, *a):
            pass

        def addWidget(self, *a, **k):
            pass

        def addLayout(self, *a, **k):
            pass

        def addStretch(self):
            pass

        def setContentsMargins(self, *a):
            pass

        def setSpacing(self, *a):
            pass

        def setFixedSize(self, *a):
            pass

        def setMinimumSize(self, *a):
            pass

        def setMinimumHeight(self, *a):
            pass

        def setMinimumWidth(self, *a):
            pass

        def setMaximumHeight(self, *a):
            pass

        def setFixedWidth(self, *a):
            pass

        def resize(self, *a):
            pass

        def setWindowTitle(self, *a):
            pass

        def setCentralWidget(self, *a):
            pass

        def setStatusBar(self, *a):
            pass

        def addAction(self, *a):
            pass

        def addDockWidget(self, *a):
            pass

        def show(self):
            pass

        def hide(self):
            pass

        def raise_(self):
            pass

        def setProperty(self, *a):
            pass

        def property(self, *a):
            return None

        def style(self):
            return MagicMock(unpolish=lambda *a: None, polish=lambda *a: None)

        def update(self):
            pass

        def setCheckable(self, *a):
            pass

        def setChecked(self, *a):
            pass

        def setToolTip(self, *a):
            pass

        def setEnabled(self, *a):
            pass

        def setText(self, *a):
            pass

        def text(self):
            return ""

        def setFont(self, *a):
            pass

        def setWordWrap(self, *a):
            pass

        def setVisible(self, *a):
            pass

        def isVisible(self):
            return True

        def setEchoMode(self, *a):
            pass

        def setPlaceholderText(self, *a):
            pass

        def setReadOnly(self, *a):
            pass

        def clicked(self):
            return MagicMock(connect=lambda *a: None)

        def setFeatures(self, *a):
            pass

        def setAllowedAreas(self, *a):
            pass

        def setWidget(self, *a):
            pass

        def setAttribute(self, *a):
            pass

        def setGraphicsEffect(self, *a):
            pass

        def graphicsEffect(self):
            return None

        def currentText(self):
            return ""

        def setCurrentText(self, *a):
            pass

        def addItem(self, *a):
            pass

        def addItems(self, *a):
            pass

        def clear(self):
            pass

        def count(self):
            return 0

        def itemText(self, *a):
            return ""

        def itemData(self, *a):
            return None

        def setCurrentIndex(self, *a):
            pass

        def blockSignals(self, *a):
            pass

        def setSizes(self, *a):
            pass

        def setChildrenCollapsible(self, *a):
            pass

        def setHandleWidth(self, *a):
            pass

        def setStretchFactor(self, *a):
            pass

        def setWidgetResizable(self, *a):
            pass

        def setFrameShape(self, *a):
            pass

        def setHorizontalScrollBarPolicy(self, *a):
            pass

        def addItem(self, *a):
            pass

        def item(self, *a):
            return None

        def currentItem(self):
            return None

        def setCurrentItem(self, *a):
            pass

        def setSpacing(self, *a):
            pass

        def setWordWrap(self, *a):
            pass

        def currentRowChanged(self):
            return MagicMock(connect=lambda *a: None)

        def currentIndexChanged(self):
            return MagicMock(connect=lambda *a: None)

        def stateChanged(self):
            return MagicMock(connect=lambda *a: None)

        def itemSelectionChanged(self):
            return MagicMock(connect=lambda *a: None)

        def setChecked(self, *a):
            pass

        def isChecked(self):
            return True

        def toHtml(self):
            return ""

        def toPlainText(self):
            return ""

        def setHtml(self, *a):
            pass

        def setOpenExternalLinks(self, *a):
            pass

        def textCursor(self):
            return MagicMock()

        def setTextCursor(self, *a):
            pass

        def setFocus(self, *a):
            pass

        def selectAll(self, *a):
            pass

        def setWindowTitle(self, *a):
            pass

        def resize(self, *a):
            pass

        def exec(self, *a):
            pass

        def exec_(self, *a):
            pass

        def close(self):
            pass

        def activateWindow(self):
            pass

        def parent(self):
            return None

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
