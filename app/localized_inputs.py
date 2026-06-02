from PyQt5.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import (
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QTextBrowser,
    QTextEdit,
    QWidget,
)

_ACTION_TEXT_MAP = {
    "undo": "撤销",
    "redo": "重做",
    "cut": "剪切",
    "copy": "复制",
    "paste": "粘贴",
    "delete": "删除",
    "select all": "全选",
}


def _normalized_action_text(text: str) -> str:
    cleaned = (text or "").replace("&", "").strip()
    if "\t" in cleaned:
        cleaned = cleaned.split("\t", 1)[0].strip()
    return cleaned.lower()


def localize_standard_menu(menu: QMenu) -> QMenu:
    for action in menu.actions():
        key = _normalized_action_text(action.text())
        if key in _ACTION_TEXT_MAP:
            action.setText(_ACTION_TEXT_MAP[key])
    return menu


class LocalizedLineEdit(QLineEdit):
    def contextMenuEvent(self, event):
        menu = localize_standard_menu(self.createStandardContextMenu())
        menu.exec(event.globalPos())


class LocalizedTextEdit(QTextEdit):
    def contextMenuEvent(self, event):
        menu = localize_standard_menu(self.createStandardContextMenu())
        menu.exec(event.globalPos())


class LocalizedTextBrowser(QTextBrowser):
    readerRequested = pyqtSignal()

    def contextMenuEvent(self, event):
        menu = localize_standard_menu(self.createStandardContextMenu())
        menu.exec(event.globalPos())

    def mouseDoubleClickEvent(self, event):
        self.readerRequested.emit()
        super().mouseDoubleClickEvent(event)


class _LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class LocalizedCodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def contextMenuEvent(self, event):
        menu = localize_standard_menu(self.createStandardContextMenu())
        menu.exec(event.globalPos())

    def line_number_area_width(self):
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 26 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#eef4fb"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#8b98ab"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 12,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        if self.isReadOnly():
            self.setExtraSelections([])
            return
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#f3f8ff"))
        selection.format.setProperty(selection.format.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])
