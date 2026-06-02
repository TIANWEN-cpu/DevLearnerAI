"""Learning Path Visualization widget.

Displays a visual tree/graph of learning progress with dependency arrows,
completion percentage per path, and recommended next lesson highlighting.
"""

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.content_service import ContentService, Track
from app.database import AppDatabase
from app.styles import (
    ACCENT,
    FONT,
    SUCCESS,
    TEXT_MAIN,
    TEXT_MUTED,
    WARNING,
)


class LearningPathCanvas(QWidget):
    """Custom widget that paints a visual tree of modules and lessons."""

    lesson_clicked = pyqtSignal(str)  # lesson_id

    def __init__(self, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self._nodes = []  # list of dicts: {type, id, title, x, y, w, h, status, pct}
        self._arrows = []  # list of (from_idx, to_idx)
        self._recommended = None
        self.setMinimumHeight(400)
        self.setMinimumWidth(600)
        self.setMouseTracking(True)
        self._hover_idx = -1

    def set_data(self, track: Track) -> None:
        """Build the node graph from a track's modules and lessons."""
        self._nodes.clear()
        self._arrows.clear()
        self._recommended = None

        if not track:
            self.update()
            return

        node_w, node_h = 200, 64
        gap_y = 24
        start_x, start_y = 30, 30

        # Track header node
        self._nodes.append(
            {
                "type": "track",
                "id": track.id,
                "title": track.title,
                "x": start_x,
                "y": start_y,
                "w": node_w + 100,
                "h": 50,
                "status": "header",
                "pct": 0,
                "icon": track.icon,
            }
        )

        y_cursor = start_y + 70
        found_recommendation = False

        for _m_idx, module in enumerate(track.modules):
            # Compute module completion
            total = len(module.lessons)
            completed = sum(1 for lesson in module.lessons if self.db.lesson_status(lesson.id) == "completed")
            pct = int(completed / max(total, 1) * 100)
            status = "completed" if pct == 100 else ("in_progress" if pct > 0 else "not_started")

            mx = start_x + 30
            my = y_cursor
            self._nodes.append(
                {
                    "type": "module",
                    "id": module.id,
                    "title": module.title,
                    "x": mx,
                    "y": my,
                    "w": node_w,
                    "h": node_h,
                    "status": status,
                    "pct": pct,
                    "total": total,
                    "completed": completed,
                }
            )
            mod_idx = len(self._nodes) - 1

            # Arrow from track header to module
            self._arrows.append((0, mod_idx))

            y_cursor += node_h + gap_y

            prev_lesson_idx = None
            for _l_idx, lesson in enumerate(module.lessons):
                ls = self.db.lesson_status(lesson.id)
                lx = start_x + 80
                ly = y_cursor

                is_recommended = False
                if not found_recommendation and ls != "completed":
                    is_recommended = True
                    found_recommendation = True
                    self._recommended = lesson.id

                self._nodes.append(
                    {
                        "type": "lesson",
                        "id": lesson.id,
                        "title": lesson.title,
                        "x": lx,
                        "y": ly,
                        "w": node_w,
                        "h": 52,
                        "status": ls,
                        "pct": 100 if ls == "completed" else 0,
                        "difficulty": lesson.difficulty,
                        "recommended": is_recommended,
                    }
                )
                les_idx = len(self._nodes) - 1

                # Arrow from module to first lesson, and between sequential lessons
                if prev_lesson_idx is None:
                    self._arrows.append((mod_idx, les_idx))
                else:
                    self._arrows.append((prev_lesson_idx, les_idx))
                prev_lesson_idx = les_idx

                y_cursor += 52 + gap_y

            y_cursor += 20  # Extra space between modules

        self.setMinimumHeight(max(y_cursor + 40, 400))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#fafcff"))

        # Draw arrows first (behind nodes)
        for from_idx, to_idx in self._arrows:
            if from_idx >= len(self._nodes) or to_idx >= len(self._nodes):
                continue
            fn = self._nodes[from_idx]
            tn = self._nodes[to_idx]
            start = QPointF(fn["x"] + fn["w"] // 2, fn["y"] + fn["h"])
            end = QPointF(tn["x"] + tn["w"] // 2, tn["y"])
            # Draw arrow line
            pen = QPen(QColor("#cbd5e1"), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(start, end)
            # Arrow head
            import math

            angle = math.atan2(end.y() - start.y(), end.x() - start.x())
            arrow_size = 8
            p1 = QPointF(end.x() - arrow_size * math.cos(angle - 0.4), end.y() - arrow_size * math.sin(angle - 0.4))
            p2 = QPointF(end.x() - arrow_size * math.cos(angle + 0.4), end.y() - arrow_size * math.sin(angle + 0.4))
            painter.setBrush(QBrush(QColor("#cbd5e1")))
            from PyQt5.QtGui import QPolygonF

            painter.drawPolygon(QPolygonF([end, p1, p2]))

        # Draw nodes
        for idx, node in enumerate(self._nodes):
            self._draw_node(painter, node, idx == self._hover_idx)

        painter.end()

    def _draw_node(self, painter: QPainter, node: dict, hovered: bool) -> None:
        x, y, w, h = node["x"], node["y"], node["w"], node["h"]
        status = node["status"]
        ntype = node["type"]

        # Colors based on status
        if status == "completed":
            bg = QColor("#f0fdf4")
            border = QColor(SUCCESS)
            text_color = QColor("#166534")
        elif status == "in_progress" or status == "header":
            bg = QColor("#eff6ff")
            border = QColor(ACCENT)
            text_color = QColor("#1e40af")
        else:
            bg = QColor("#f8fafc")
            border = QColor("#e2e8f0")
            text_color = QColor(TEXT_MUTED)

        if node.get("recommended"):
            bg = QColor("#fefce8")
            border = QColor(WARNING)
            text_color = QColor("#854d0e")

        if hovered:
            border = QColor(ACCENT)

        # Background
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 2 if (status == "completed" or node.get("recommended")) else 1))
        radius = 16 if ntype == "track" else 12
        painter.drawRoundedRect(QRectF(x, y, w, h), radius, radius)

        # Progress bar for modules
        if ntype == "module":
            pct = node.get("pct", 0)
            bar_x = x + 8
            bar_y = y + h - 10
            bar_w = w - 16
            bar_h = 4
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#e2e8f0")))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2, 2)
            painter.setBrush(QBrush(QColor(SUCCESS if pct == 100 else ACCENT)))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w * pct / 100, bar_h), 2, 2)

        # Status icon
        icon_x = x + 10
        if ntype == "track":
            icon_text = node.get("icon", "📘")
            painter.setPen(QPen(text_color))
            font = QFont(FONT, 16)
            painter.setFont(font)
            painter.drawText(QRectF(x + 8, y + 8, 30, h - 16), Qt.AlignCenter, icon_text)
            icon_x = x + 42

        # Title text
        painter.setPen(QPen(text_color))
        font = QFont(FONT, 14 if ntype == "lesson" else 15, QFont.Bold if ntype != "lesson" else QFont.Normal)
        painter.setFont(font)
        title_rect = QRectF(
            icon_x, y + (6 if ntype == "lesson" else 12), w - (icon_x - x) - 10, h - (16 if ntype == "lesson" else 24)
        )
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, node["title"])

        # Completion status icon
        if status == "completed":
            painter.setPen(QPen(QColor(SUCCESS)))
            font = QFont(FONT, 18)
            painter.setFont(font)
            painter.drawText(QRectF(x + w - 32, y, 28, h), Qt.AlignCenter, "V")

        # Recommended badge
        if node.get("recommended"):
            painter.setPen(QPen(QColor(WARNING)))
            font = QFont(FONT, 11, QFont.Bold)
            painter.setFont(font)
            badge_rect = QRectF(x + w - 50, y + 4, 44, 18)
            painter.setBrush(QBrush(QColor(WARNING)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(badge_rect, 6, 6)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(badge_rect, Qt.AlignCenter, "推荐")

        # Module stats
        if ntype == "module":
            total = node.get("total", 0)
            completed = node.get("completed", 0)
            painter.setPen(QPen(QColor(TEXT_MUTED)))
            font = QFont(FONT, 12)
            painter.setFont(font)
            stats_rect = QRectF(x + w - 80, y + 10, 70, 20)
            painter.drawText(stats_rect, Qt.AlignRight | Qt.AlignVCenter, f"{completed}/{total}")

    def mouseMoveEvent(self, event):
        old_hover = self._hover_idx
        self._hover_idx = -1
        for idx, node in enumerate(self._nodes):
            rect = QRectF(node["x"], node["y"], node["w"], node["h"])
            if rect.contains(event.pos()):
                self._hover_idx = idx
                break
        if self._hover_idx != old_hover:
            self.setCursor(Qt.PointingHandCursor if self._hover_idx >= 0 else Qt.ArrowCursor)
            self.update()

    def mousePressEvent(self, event):
        if self._hover_idx >= 0:
            node = self._nodes[self._hover_idx]
            if node["type"] == "lesson":
                self.lesson_clicked.emit(node["id"])
        super().mousePressEvent(event)


class LearningPathWidget(QWidget):
    """Complete learning path visualization widget with track selector."""

    lesson_selected = pyqtSignal(str)  # lesson_id

    def __init__(self, content_service: ContentService, db: AppDatabase, parent=None):
        super().__init__(parent)
        self.content_service = content_service
        self.db = db

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("学习路径可视化")
        title.setFont(QFont(FONT, 28, QFont.Bold))
        title.setStyleSheet(f"color: {TEXT_MAIN};")
        header.addWidget(title)
        header.addStretch()

        self.pct_label = QLabel("")
        self.pct_label.setStyleSheet(f"color: {ACCENT}; font-weight: 700; font-size: 22px;")
        header.addWidget(self.pct_label)
        root.addLayout(header)

        # Legend
        legend = QHBoxLayout()
        legend.setSpacing(16)
        for color, label in [(SUCCESS, "已完成"), (ACCENT, "进行中"), ("#94a3b8", "未开始"), (WARNING, "推荐下一步")]:
            item = QHBoxLayout()
            item.setSpacing(4)
            dot = QLabel()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background: {color}; border-radius: 6px;")
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 15px;")
            item.addWidget(dot)
            item.addWidget(lbl)
            legend.addLayout(item)
        legend.addStretch()
        root.addLayout(legend)

        # Canvas in scroll area
        from PyQt5.QtWidgets import QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.canvas = LearningPathCanvas(db)
        self.canvas.lesson_clicked.connect(self.lesson_selected.emit)
        scroll.setWidget(self.canvas)
        root.addWidget(scroll, 1)

    def set_track(self, track: Track) -> None:
        """Update the visualization for a given track."""
        self.canvas.set_data(track)
        # Update overall percentage
        if track:
            total = len(track.lessons)
            completed = sum(1 for lesson in track.lessons if self.db.lesson_status(lesson.id) == "completed")
            pct = int(completed / max(total, 1) * 100)
            self.pct_label.setText(f"总进度: {pct}%")
        else:
            self.pct_label.setText("")
