"""Export / Import dialog for learning progress backup and restore."""

import json
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QShortcut,
    QTextEdit,
    QVBoxLayout,
)

from app.config import EXPORT_DIR
from app.database import AppDatabase, now_text
from app.styles import (
    F_TITLE,
    FONT,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUB,
)


class ExportImportDialog(QDialog):
    """Dialog for exporting and importing learning progress data."""

    def __init__(self, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("数据导出 / 导入")
        self.setMinimumSize(640, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        # Escape key to close
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.accept)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(18)

        # Header
        title = QLabel("学习数据管理")
        title.setFont(QFont(FONT, F_TITLE - 12, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        subtitle = QLabel("导出进度数据用于备份，或从之前的备份中恢复。")
        subtitle.setStyleSheet(f"color: {TEXT_SUB}; font-size: 18px;")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        # Action buttons grid
        actions_grid = QVBoxLayout()
        actions_grid.setSpacing(12)

        # Export progress JSON
        row1 = self._action_row(
            "导出学习进度", "将所有课程进度、练习记录、书签和成就导出为 JSON 文件。", "导出", self._export_progress
        )
        actions_grid.addLayout(row1)

        # Import progress JSON
        row2 = self._action_row(
            "导入学习进度", "从之前导出的 JSON 文件中恢复学习进度数据。", "导入", self._import_progress
        )
        actions_grid.addLayout(row2)

        # Export notes markdown
        row3 = self._action_row(
            "导出笔记到 Markdown",
            "将所有课程笔记导出为一个 Markdown 文件，方便在其他工具中阅读。",
            "导出笔记",
            self._export_notes,
        )
        actions_grid.addLayout(row3)

        # Backup (full export)
        row4 = self._action_row("完整备份", "创建包含所有数据的完整备份文件（JSON 格式）。", "备份", self._full_backup)
        actions_grid.addLayout(row4)

        # Restore from backup
        row5 = self._action_row(
            "从备份恢复", "从完整备份文件中恢复所有数据。注意：这会覆盖当前数据。", "恢复", self._restore_backup
        )
        actions_grid.addLayout(row5)

        root.addLayout(actions_grid)

        # Status / log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(100)
        self.log_area.setPlaceholderText("操作日志将显示在这里...")
        self.log_area.setAccessibleName("操作日志")
        self.log_area.setAccessibleDescription("显示导出导入操作的结果和错误信息")
        root.addWidget(self.log_area, 1)

        # Close button
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setProperty("variant", "secondary")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

    def _action_row(self, title: str, desc: str, btn_text: str, callback) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: 600; font-size: 18px;")
        d = QLabel(desc)
        d.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px;")
        d.setWordWrap(True)
        text_col.addWidget(t)
        text_col.addWidget(d)
        row.addLayout(text_col, 1)

        btn = QPushButton(btn_text)
        btn.setMinimumWidth(100)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setAccessibleName(title)
        btn.setAccessibleDescription(desc)
        btn.clicked.connect(callback)
        row.addWidget(btn)

        return row

    def _log(self, message: str) -> None:
        self.log_area.append(f"[{now_text()}] {message}")

    def _export_progress(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出学习进度",
            str(EXPORT_DIR / f"progress_{now_text().replace(':', '-').replace(' ', '_')}.json"),
            "JSON 文件 (*.json)",
        )
        if not path:
            return
        try:
            data = self.db.export_progress_json()
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            count = sum(len(v) for k, v in data.items() if isinstance(v, list))
            self._log(f"成功导出 {count} 条记录到: {path}")
            QMessageBox.information(self, "导出成功", f"已导出 {count} 条记录。")
        except Exception as e:
            self._log(f"导出失败: {e}")
            QMessageBox.warning(self, "导出失败", str(e))

    def _import_progress(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入学习进度",
            str(EXPORT_DIR),
            "JSON 文件 (*.json)",
        )
        if not path:
            return
        try:
            raw = Path(path).read_text(encoding="utf-8")
            data = json.loads(raw)
            count = self.db.import_progress_json(data)
            self._log(f"成功导入 {count} 条记录从: {path}")
            QMessageBox.information(self, "导入成功", f"已导入 {count} 条记录。")
        except Exception as e:
            self._log(f"导入失败: {e}")
            QMessageBox.warning(self, "导入失败", str(e))

    def _export_notes(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出笔记",
            str(EXPORT_DIR / f"notes_{now_text().replace(':', '-').replace(' ', '_')}.md"),
            "Markdown 文件 (*.md)",
        )
        if not path:
            return
        try:
            content = self.db.export_notes_markdown()
            Path(path).write_text(content, encoding="utf-8")
            note_count = self.db.note_count()
            self._log(f"成功导出 {note_count} 条笔记到: {path}")
            # Track achievement
            self.db.update_achievement_progress("note_exporter", 1)
            self.db.update_achievement_progress("data_backup", 1)
            QMessageBox.information(self, "导出成功", f"已导出 {note_count} 条笔记。")
        except Exception as e:
            self._log(f"导出失败: {e}")
            QMessageBox.warning(self, "导出失败", str(e))

    def _full_backup(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "完整备份",
            str(EXPORT_DIR / f"backup_{now_text().replace(':', '-').replace(' ', '_')}.json"),
            "JSON 文件 (*.json)",
        )
        if not path:
            return
        try:
            data = self.db.export_progress_json()
            data["backup_type"] = "full"
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            count = sum(len(v) for k, v in data.items() if isinstance(v, list))
            self._log(f"完整备份已保存 ({count} 条记录): {path}")
            self.db.update_achievement_progress("data_backup", 1)
            QMessageBox.information(self, "备份成功", f"完整备份包含 {count} 条记录。")
        except Exception as e:
            self._log(f"备份失败: {e}")
            QMessageBox.warning(self, "备份失败", str(e))

    def _restore_backup(self) -> None:
        reply = QMessageBox.question(
            self,
            "确认恢复",
            "从备份恢复将覆盖当前所有学习数据。确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择备份文件",
            str(EXPORT_DIR),
            "JSON 文件 (*.json)",
        )
        if not path:
            return
        try:
            raw = Path(path).read_text(encoding="utf-8")
            data = json.loads(raw)
            # Reset then import
            self.db.reset_learning_progress()
            count = self.db.import_progress_json(data)
            self._log(f"已从备份恢复 {count} 条记录: {path}")
            self.db.update_achievement_progress("data_backup", 1)
            QMessageBox.information(self, "恢复成功", f"已恢复 {count} 条记录。建议重启应用以刷新界面。")
        except Exception as e:
            self._log(f"恢复失败: {e}")
            QMessageBox.warning(self, "恢复失败", str(e))
