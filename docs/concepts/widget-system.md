# PyQt5 Widget 系统

本文档描述 DevLearnerAI 的 UI 组件层次结构、导航模式和 Widget 间通信机制。

---

## 组件层次结构

```text
QApplication
  └── DevLearnerWindow (QMainWindow)
        ├── QFrame (Sidebar - 侧边导航栏)
        │     ├── QLabel ("LEARNING OS")
        │     ├── QPushButton (收起/展开)
        │     ├── QFrame (品牌卡片)
        │     ├── QPushButton[] (导航按钮: 首页/学习路径/练习中心/融合项目/算法动画)
        │     └── QFrame (设置区域: 深色模式/字号调整)
        │
        ├── QFrame (Content Shell - 内容区)
        │     ├── QFrame (Topbar)
        │     │     ├── QLabel (页面标题)
        │     │     ├── QLabel (页面副标题)
        │     │     ├── QLabel (日期 Chip)
        │     │     └── QPushButton ("AI 工作台")
        │     │
        │     └── QStackedWidget (页面栈)
        │           ├── QScrollArea → DashboardWidget (index=0)
        │           ├── QScrollArea → LearnWidget (index=1)
        │           ├── QScrollArea → PracticeWidget (index=2)
        │           ├── QScrollArea → ProjectsWidget (index=3)
        │           ├── QScrollArea → AlgoVisualizerWidget (index=4)
        │           └── QScrollArea → AIMentorPanel (index=5)
        │
        ├── AIMentorDock (QDockWidget - 右侧停靠面板，可选)
        │
        └── QStatusBar (状态栏)
              ├── QLabel (连接状态指示器)
              └── 状态消息区
```

---

## 核心 Widget 详解

### DevLearnerWindow

主窗口是整个应用的骨架，负责：

- **页面导航管理**：通过 `QStackedWidget` 切换各功能页面
- **侧边栏状态**：展开/收起两种形态，宽度分别为 300px / 92px
- **延迟初始化**：非关键 Widget 通过 `QTimer.singleShot` 分批创建
- **键盘快捷键**：注册全局快捷键处理
- **主题切换**：亮色/暗色模式一键切换

```python
class DevLearnerWindow(QMainWindow):
    SIDEBAR_EXPANDED_WIDTH = 300
    SIDEBAR_COLLAPSED_WIDTH = 92

    def __init__(self):
        # 核心服务
        self.db = AppDatabase()
        self.content_service = ContentService()
        self.practice_service = PracticeService()

        # 关键 Widget（启动时创建）
        self.dashboard = DashboardWidget(...)
        self.learn = LearnWidget(...)
        self.practice = PracticeWidget(...)

        # 延迟 Widget（启动后异步创建）
        # self.projects → _ensure_projects()
        # self.algo → _ensure_algo()
        # self.ai_page → _ensure_ai_page()
        # self.ai_dock → _ensure_ai_dock()
```

### DashboardWidget

学习仪表盘，展示：

- 已完成课程数量
- 连续学习天数（streak）
- 练习平均分
- 最近练习记录
- 快速导航到各技术栈

信号：
- `navigate_requested(int)` - 请求切换到指定页面
- `track_requested(str)` - 请求打开指定技术栈

### LearnWidget

课程学习页面，提供：

- 技术栈列表展示
- 模块和课程的层次导航
- Markdown 课程内容渲染（mistune + Pygments）
- 课程完成状态标记
- 笔记功能
- 前后课程预加载

### PracticeWidget

练习中心，提供：

- 练习列表（按技术栈/难度筛选）
- 代码编辑器（QTextEdit + 语法高亮）
- 练习评测（Ctrl+Enter 提交）
- 评测反馈展示
- 提示查看（Ctrl+H）
- 草稿自动保存

### AIMentorPanel / AIMentorDock

AI 导师的两种形态：

| 组件 | 形态 | 用途 |
|------|------|------|
| `AIMentorPanel` | 独立页面（QStackedWidget 中） | AI 工作台，完整功能 |
| `AIMentorDock` | QDockWidget 停靠面板 | 侧边助手，快速提问 |

两者共享同一个 `panel` 实例，支持：

- 多会话管理
- 流式响应渲染
- 知识库配置
- 快捷提问（解释课程、分析代码、拆解项目）

---

## 页面导航机制

页面切换通过 `switch_page(index)` 方法实现：

```python
def switch_page(self, index: int) -> None:
    self.stack.setCurrentIndex(index)
    title, desc, widget, _short = self.learning_pages[index]
    self.page_title.setText(title)
    self.page_subtitle.setText(desc)

    # 更新侧边栏按钮状态
    for button_index, button in enumerate(self.nav_buttons):
        active = button_index == index
        button.setChecked(active)
```

导航来源包括：

1. **侧边栏按钮**：直接调用 `switch_page(index)`
2. **Dashboard 快捷入口**：通过 `navigate_requested` 信号
3. **Dashboard 技术栈卡片**：通过 `track_requested` 信号 → `open_track(track_id)`
4. **AI 工作台**：`open_ai_workspace()` 直接设置 Stack index

---

## Widget 间通信

### 信号与槽

Widget 间通过 Qt 信号机制通信，避免直接耦合：

```python
# Dashboard → MainWindow
self.dashboard.navigate_requested.connect(self.switch_page)
self.dashboard.track_requested.connect(self.open_track)

# AIMentorPanel → AIMentorDock
self.ai_page.request_open_dock.connect(self.open_ai_dock)

# AIMentorDock → AIMentorPanel
self.dock.panel.request_open_page.connect(self.open_ai_workspace)
```

### 共享服务

核心服务通过构造函数注入到各 Widget：

```python
# 所有 Widget 共享同一组服务实例
self.dashboard = DashboardWidget(self.content_service, self.db)
self.learn = LearnWidget(self.content_service, self.db)
self.practice = PracticeWidget(self.content_service, self.practice_service, self.db)
```

---

## 样式系统

### 主题管理

样式定义在 `app/styles.py` 中，支持亮色和暗色两套主题：

```python
# 亮色主题调色板
BG_BASE = "#eef4f8"
ACCENT = "#2563eb"
TEXT_MAIN = "#152033"

# 暗色主题调色板
DARK_BG_BASE = "#0f172a"
DARK_ACCENT = "#3b82f6"
DARK_TEXT_MAIN = "#e2e8f0"
```

### 字号预设

```python
# 三种字号预设
FONT_SIZES = {
    "small":  {"base": 26, "title": 50, "code": 24},
    "medium": {"base": 33, "title": 63, "code": 31},  # 默认
    "large":  {"base": 40, "title": 76, "code": 38},
}
```

### 全局样式切换

```python
def toggle_theme(self) -> None:
    self._dark_mode = not self._dark_mode
    style = build_style_for_size(self._font_size, dark=self._dark_mode)
    QApplication.instance().setStyleSheet(style)

def set_font_size(self, size_name: str) -> None:
    self._font_size = size_name
    style = build_style_for_size(size_name, dark=self._dark_mode)
    QApplication.instance().setStyleSheet(style)
```

---

## 快捷键系统

| 快捷键 | 功能 | 生效范围 |
|--------|------|----------|
| `Ctrl+Enter` | 提交练习答案 | 练习页面 |
| `Ctrl+N` | 下一题 | 练习页面 |
| `Ctrl+H` | 查看提示 | 练习页面 |
| `Ctrl+Shift+A` | 向 AI 提问当前代码 | 全局 |
| `Ctrl+T` | 切换深色/浅色主题 | 全局 |

快捷键通过 `QAction` + `QKeySequence` 注册到主窗口：

```python
ask_action = QAction("向 AI 提问", self)
ask_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
ask_action.triggered.connect(self.ask_ai_about_editor)
self.addAction(ask_action)
```

---

## 状态栏

底部状态栏包含：

- **连接状态指示器**：实时显示 AI API 连接状态
  - 绿色 "在线就绪" / "已连接"
  - 红色 "未连接"
  - 黄色 "请求中..."
- **快捷键提示**：显示常用快捷键说明
- **版本信息**

---

## 相关文档

- [系统架构](architecture.md) - 整体架构设计
- [AI 导师集成](ai-integration.md) - AI 相关组件详情
- [模块一览](../reference/modules.md) - 所有模块接口参考
