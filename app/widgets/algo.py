import random

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.effects import apply_shadow
from app.localized_inputs import LocalizedTextEdit
from app.styles import (
    ACCENT,
    BG_CARD,
    BG_CARD_SOFT,
    BORDER,
    BTN_H,
    F_TITLE,
    FONT,
    TEXT_MAIN,
    TEXT_SUB,
)


class AlgoVisualizerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.timer = None
        self.scene = QGraphicsScene()
        self.active_data = []
        self.active_target = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 18)
        layout.setSpacing(18)

        hero = QFrame()
        hero.setStyleSheet(
            f"""
            QFrame {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {BG_CARD},
                    stop: 1 {BG_CARD_SOFT}
                );
                border: 1px solid {BORDER};
                border-radius: 24px;
            }}
            """
        )
        apply_shadow(hero, blur=18, offset_y=4)
        hero_layout = QVBoxLayout(hero)
        title = QLabel("算法动画")
        title.setFont(QFont(FONT, F_TITLE - 2, QFont.Bold))
        subtitle = QLabel(
            "把排序、查找这些基础算法拆成可视化步骤，先看懂过程，再回去写代码。"
        )
        subtitle.setStyleSheet(f"color: {TEXT_SUB};")
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        layout.addWidget(hero)

        controls = QHBoxLayout()
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(
            [
                "冒泡排序",
                "选择排序",
                "插入排序",
                "归并排序",
                "快速排序",
                "线性查找",
                "二分查找",
            ]
        )
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(30, 500)
        self.speed_spin.setValue(100)
        self.speed_spin.setPrefix("延迟 ")
        self.speed_spin.setSuffix(" ms")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 30)
        self.size_spin.setValue(14)
        self.size_spin.setPrefix("数量 ")
        self.run_btn = QPushButton("开始演示")
        self.run_btn.setFixedHeight(BTN_H)
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setFixedHeight(BTN_H)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setFixedHeight(BTN_H)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_demo)
        controls.addWidget(self.algo_combo)
        controls.addWidget(self.speed_spin)
        controls.addWidget(self.size_spin)
        controls.addWidget(self.run_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch()
        layout.addLayout(controls)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 24px; }}"
        )
        apply_shadow(card, blur=18, offset_y=4)
        card_layout = QVBoxLayout(card)
        self.view = QGraphicsView(self.scene)
        self.view.setMinimumHeight(420)
        self.view.setStyleSheet(
            f"background: {BG_CARD_SOFT}; border: 1px solid {BORDER}; border-radius: 18px;"
        )
        self.desc = LocalizedTextEdit()
        self.desc.setReadOnly(True)
        self.desc.setFixedHeight(120)
        card_layout.addWidget(self.view)
        card_layout.addWidget(self.desc)
        layout.addWidget(card, 1)

        self.algo_combo.currentTextChanged.connect(self.update_desc)
        self.run_btn.clicked.connect(self.run_algorithm)
        self.update_desc(self.algo_combo.currentText())

    def update_desc(self, name: str):
        descriptions = {
            "冒泡排序": "一轮轮比较相邻元素，把更大的数慢慢推到右边。适合练熟双层循环、比较和交换。",
            "选择排序": "每轮从未排序区域里挑出最小值，放到左侧。适合理解“先找再换”的过程。",
            "插入排序": "把当前值插入左边已经有序的区域。适合理解局部有序如何逐步扩大。",
            "归并排序": "先递归拆分，再把两个有序片段合并起来。适合理解分治法。",
            "快速排序": "围绕基准值分区，再递归处理左右两边。适合理解 partition 思想。",
            "线性查找": "从左往右一个个看，直到找到目标。适合理解最直接的搜索模型。",
            "二分查找": "在有序数组里不断看中间值，把搜索范围砍半。适合理解对数级查找。",
        }
        self.desc.setPlainText(descriptions.get(name, ""))

    def draw_bars(self, data, highlights=None):
        self.scene.clear()
        if not data:
            return
        width = max(22, 620 // len(data))
        max_val = max(data)
        for index, value in enumerate(data):
            height = 290 * value / max_val
            color = QColor(ACCENT)
            if highlights and index in highlights:
                color = QColor("#14b8a6")
            self.scene.addRect(
                index * (width + 6), 320 - height, width, height, brush=color
            )
            text = self.scene.addText(str(value))
            text.setDefaultTextColor(QColor(TEXT_MAIN))
            text.setPos(index * (width + 6), 326)
        if self.active_target is not None:
            target_label = self.scene.addText(f"目标值：{self.active_target}")
            target_label.setDefaultTextColor(QColor(TEXT_SUB))
            target_label.setPos(0, 0)

    def run_algorithm(self):
        data = [random.randint(8, 99) for _ in range(self.size_spin.value())]
        self.active_data = data[:]
        steps = []
        algo = self.algo_combo.currentText()
        self.active_target = None
        if algo == "冒泡排序":
            self._bubble_steps(data[:], steps)
        elif algo == "选择排序":
            self._selection_steps(data[:], steps)
        elif algo == "插入排序":
            self._insertion_steps(data[:], steps)
        elif algo == "归并排序":
            self._merge_steps(data[:], steps)
        elif algo == "快速排序":
            self._quick_steps(data[:], steps)
        elif algo == "线性查找":
            data = sorted(data)
            self.active_target = data[len(data) // 3]
            self._linear_search_steps(data[:], self.active_target, steps)
        else:
            data = sorted(data)
            self.active_target = data[len(data) // 2]
            self._binary_search_steps(data[:], self.active_target, steps)
        self._animate(steps)

    def _bubble_steps(self, data, steps):
        for i in range(len(data)):
            for j in range(len(data) - i - 1):
                steps.append((data[:], {j, j + 1}))
                if data[j] > data[j + 1]:
                    data[j], data[j + 1] = data[j + 1], data[j]
                    steps.append((data[:], {j, j + 1}))

    def _selection_steps(self, data, steps):
        for i in range(len(data)):
            minimum = i
            for j in range(i + 1, len(data)):
                steps.append((data[:], {minimum, j}))
                if data[j] < data[minimum]:
                    minimum = j
            data[i], data[minimum] = data[minimum], data[i]
            steps.append((data[:], {i, minimum}))

    def _insertion_steps(self, data, steps):
        for i in range(1, len(data)):
            current = data[i]
            j = i - 1
            steps.append((data[:], {i}))
            while j >= 0 and data[j] > current:
                data[j + 1] = data[j]
                steps.append((data[:], {j, j + 1}))
                j -= 1
            data[j + 1] = current
            steps.append((data[:], {j + 1}))

    def _merge_steps(self, data, steps):
        def merge_sort(arr, left, right):
            if left >= right:
                return
            mid = (left + right) // 2
            merge_sort(arr, left, mid)
            merge_sort(arr, mid + 1, right)
            merged = []
            i, j = left, mid + 1
            while i <= mid and j <= right:
                steps.append((arr[:], {i, j}))
                if arr[i] <= arr[j]:
                    merged.append(arr[i])
                    i += 1
                else:
                    merged.append(arr[j])
                    j += 1
            merged.extend(arr[i : mid + 1])
            merged.extend(arr[j : right + 1])
            for offset, value in enumerate(merged):
                arr[left + offset] = value
                steps.append((arr[:], {left + offset}))

        merge_sort(data, 0, len(data) - 1)

    def _quick_steps(self, data, steps):
        def quick_sort(arr, low, high):
            if low >= high:
                return
            pivot = arr[high]
            i = low
            for j in range(low, high):
                steps.append((arr[:], {j, high}))
                if arr[j] <= pivot:
                    arr[i], arr[j] = arr[j], arr[i]
                    steps.append((arr[:], {i, j}))
                    i += 1
            arr[i], arr[high] = arr[high], arr[i]
            steps.append((arr[:], {i, high}))
            quick_sort(arr, low, i - 1)
            quick_sort(arr, i + 1, high)

        quick_sort(data, 0, len(data) - 1)

    def _linear_search_steps(self, data, target, steps):
        for index, value in enumerate(data):
            steps.append((data[:], {index}))
            if value == target:
                steps.append((data[:], {index}))
                break

    def _binary_search_steps(self, data, target, steps):
        left, right = 0, len(data) - 1
        while left <= right:
            mid = (left + right) // 2
            steps.append((data[:], {left, mid, right}))
            if data[mid] == target:
                steps.append((data[:], {mid}))
                break
            if data[mid] < target:
                left = mid + 1
            else:
                right = mid - 1

    def _animate(self, steps):
        index = {"value": 0}

        def tick():
            if index["value"] >= len(steps):
                if self.timer:
                    self.timer.stop()
                return
            data, highlights = steps[index["value"]]
            self.draw_bars(data, highlights)
            index["value"] += 1

        if self.timer:
            self.timer.stop()
        self.timer = QTimer()
        self.timer.timeout.connect(tick)
        self.timer.start(self.speed_spin.value())
        self.run_btn.setEnabled(False)
        self.run_btn.setText("\u6f14\u793a\u4e2d...")
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("\u6682\u505c")
        self.stop_btn.setEnabled(True)
        self._anim_steps = steps
        self._anim_index = 0
        self._paused = False

    def _toggle_pause(self) -> None:
        if not self.timer:
            return
        if self._paused:
            self.timer.start(self.speed_spin.value())
            self.pause_btn.setText("\u6682\u505c")
            self._paused = False
        else:
            self.timer.stop()
            self.pause_btn.setText("\u7ee7\u7eed")
            self._paused = True

    def _stop_demo(self) -> None:
        if self.timer:
            self.timer.stop()
        self.run_btn.setEnabled(True)
        self.run_btn.setText("\u5f00\u59cb\u6f14\u793a")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("\u6682\u505c")
        self.stop_btn.setEnabled(False)
        self._paused = False
        if self.active_data:
            self.draw_bars(self.active_data, set())
