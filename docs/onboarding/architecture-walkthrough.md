# 架构深度导览

本文档详细介绍 DevLearnerAI 的核心架构设计，帮助开发者理解 Widget 层次结构、AI 集成方式、数据库层设计和课程内容系统。

---

## 目录

- [Widget 层次结构](#widget-层次结构)
- [AI 集成架构](#ai-集成架构)
- [数据库层](#数据库层)
- [课程内容系统](#课程内容系统)
- [服务层与依赖注入](#服务层与依赖注入)
- [事件系统](#事件系统)
- [插件架构](#插件架构)
- [安全架构](#安全架构)

---

## Widget 层次结构

### 整体布局

应用采用经典的 QMainWindow + QStackedWidget 架构：

```text
DevLearnerWindow (QMainWindow)
├── Sidebar (左侧导航栏)
│   ├── 首页 -> DashboardWidget
│   ├── 学习路径 -> LearnWidget
│   ├── 练习中心 -> PracticeWidget
│   ├── 融合项目 -> ProjectsWidget
│   ├── 算法动画 -> AlgoVisualizerWidget
│   └── [AI 工作台] -> AIMentorPanel (全页面模式)
│
├── QStackedWidget (右侧内容区)
│   ├── DashboardWidget    -- 学习仪表盘（索引 0）
│   ├── LearnWidget        -- 课程浏览与学习（索引 1）
│   ├── PracticeWidget     -- 练习中心（索引 2）
│   ├── ProjectsWidget     -- 融合项目（索引 3）
│   ├── AlgoVisualizerWidget  -- 算法可视化（索引 4）
│   └── AIMentorPanel      -- AI 工作台（索引 5）
│
├── AIMentorDock (QDockWidget，侧边 AI 助手)
│   └── AIMentorPanel      -- 可停靠的 AI 对话面板
│
└── QStatusBar (底部状态栏)
```

### Widget 职责

| Widget | 文件 | 核心职责 |
|--------|------|----------|
| `DashboardWidget` | `app/widgets/dashboard.py` | 学习进度统计、连续天数、课程完成率、快速导航 |
| `LearnWidget` | `app/widgets/learn.py` | 课程列表浏览、Markdown 内容渲染、学习进度记录、笔记 |
| `PracticeWidget` | `app/widgets/practice.py` | 练习列表筛选、代码编辑器、自动评测、草稿保存 |
| `ProjectsWidget` | `app/widgets/projects.py` | 融合项目文档浏览 |
| `AlgoVisualizerWidget` | `app/widgets/algo.py` | 算法步骤动画可视化 |
| `AIMentorPanel` | `app/ai/chat_handler.py` | AI 对话界面、多会话管理、知识库集成 |

### Widget 间通信

Widget 之间不直接引用对方，而是通过以下机制解耦：

1. **事件总线** (`app/utils/events.py`) -- 发布/订阅模式，如课程完成事件触发仪表盘刷新
2. **共享服务** -- 通过 `ContentService`、`PracticeService`、`AppDatabase` 等服务间接通信
3. **信号/槽** -- PyQt5 原生机制，用于 Widget 内部事件处理

### 初始化顺序

在 `DevLearnerWindow.__init__()` 中：

1. 创建核心服务：`AppDatabase` -> `ContentService` -> `PracticeService`
2. 创建可见 Widget：`DashboardWidget`、`LearnWidget`、`PracticeWidget`
3. 延迟创建非首屏 Widget：`ProjectsWidget`、`AlgoVisualizerWidget`、`AIMentorPanel`
4. 将 Widget 按顺序添加到 `QStackedWidget`
5. 创建 `AIMentorDock`（侧边 AI 助手面板）
6. 建立侧边栏导航与 `QStackedWidget` 的索引映射

---

## AI 集成架构

### 模块结构

AI 功能从原先的单一 `ai_mentor.py`（1200+ 行）拆分为 `app/ai/` 子包：

```text
app/ai/
├── __init__.py            # 导出兼容（AIMentorPanel, AIMentorDock）
├── api_client.py          # API 通信层
├── chat_handler.py        # 对话 UI 组件
├── markdown_renderer.py   # Markdown 渲染 + HTML 净化
└── models.py              # 数据类和安全常量
```

### API 通信流程 (`api_client.py`)

```text
用户输入消息
    │
    ▼
构建系统上下文
    ├── 当前课程摘要
    ├── 学习进度快照
    └── 知识库文件内容
    │
    ▼
加载最近 12 条历史消息
    │
    ▼
send_chat() -- HTTPS POST 请求
    ├── 强制 HTTPS（拒绝 HTTP）
    ├── TLS 证书验证
    └── 超时控制（默认 30 秒）
    │
    ▼
流式响应处理
    │
    ▼
markdown_renderer 渲染为安全 HTML
    ├── mistune 解析 Markdown
    ├── Pygments 代码语法高亮
    └── HTML 白名单净化（XSS 防护）
    │
    ▼
消息持久化到 mentor_messages 表
```

### 多会话管理

`chat_handler.py` 支持按主题拆分对话会话：

- 每个会话有独立的 `session_id` 和 `title`
- 会话列表存储在 `mentor_sessions` 表
- 消息存储在 `mentor_messages` 表（通过 `session_id` 关联）
- 用户可在"Python 调试"、"数据库报表"、"项目拆解"等会话间自由切换

### 知识库系统

AI 导师有三层知识库：

| 层级 | 说明 | 存储位置 |
|------|------|----------|
| 基础知识库 | 内置的编程教学知识 | 代码内嵌 |
| 个性知识库 | 用户添加的笔记和学习记录 | `mentor_knowledge_files` 表 |
| 扩展文件知识库 | 用户上传的外部文档 | 文件系统 + 数据库索引 |

### 安全措施

- **HTTPS 强制** -- `api_client.py` 中拒绝非 HTTPS 连接
- **HTML 净化** -- `markdown_renderer.py` 使用白名单过滤，移除 `script`、`style`、`iframe` 标签和 `onclick` 等事件处理器
- **API Key 安全存储** -- 通过 `credentials.py` 使用 Windows Credential Manager / keyring 存储，不明文保存

---

## 数据库层

### 技术选型

- **SQLite** + WAL 模式 -- 适合桌面单用户场景，读写并发性能好
- **线程安全** -- 使用 `threading.Lock()` 保护写操作
- **连接管理** -- 单例模式，支持失效自动重连

### 核心文件

`app/database.py` -- 所有数据库操作的唯一入口

### 数据表设计

```sql
-- 课程学习进度
lesson_progress (
    lesson_id TEXT PRIMARY KEY,
    track_id TEXT,
    completed INTEGER,
    last_accessed TEXT,
    time_spent_seconds INTEGER
)

-- 课程笔记
lesson_notes (
    lesson_id TEXT PRIMARY KEY,
    note_content TEXT,
    updated_at TEXT
)

-- 练习尝试记录
practice_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id TEXT,
    language TEXT,
    score INTEGER,
    passed INTEGER,
    feedback TEXT,
    submitted_code TEXT,
    created_at TEXT
)

-- 练习草稿
exercise_drafts (
    exercise_id TEXT PRIMARY KEY,
    draft_code TEXT,
    updated_at TEXT
)

-- AI 导师会话
mentor_sessions (
    session_id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT,
    updated_at TEXT
)

-- AI 导师消息
mentor_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT,
    content TEXT,
    created_at TEXT
)

-- AI 导师 API 配置
mentor_api_config (
    key TEXT PRIMARY KEY,
    value TEXT
)

-- AI 导师工作区状态
mentor_workspace_state (
    key TEXT PRIMARY KEY,
    value TEXT
)

-- AI 知识库文件
mentor_knowledge_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    content TEXT,
    added_at TEXT
)
```

### 数据库初始化流程

1. `AppDatabase.__init__()` -- 创建实例
2. `AppDatabase.init_db()` -- 检查旧版数据库（`db/learner.db`）是否存在，若存在则自动迁移
3. 创建所有表（`CREATE TABLE IF NOT EXISTS`）
4. 创建索引（性能优化）
5. 设置 PRAGMA（`foreign_keys=ON`、`journal_mode=WAL`、`cache_size=-8000`）

### 关键设计决策

| 决策 | 原因 |
|------|------|
| 使用 WAL 模式 | 读操作不阻塞写操作，适合 UI 线程和后台线程并发访问 |
| 写操作加锁 | SQLite 不支持真正的并发写，需通过 `threading.Lock()` 序列化 |
| 连接单例 + 失效重连 | 避免频繁创建连接，同时处理数据库文件被替换的场景 |
| 旧版数据库自动迁移 | 用户从旧版本升级时无需手动操作 |

---

## 课程内容系统

### 数据模型

课程采用三级层次结构：

```text
Track（技术栈）
 └── Module（模块）
      └── Lesson（课程）
```

### 元数据定义

`content/metadata/course_map.json` 定义了整个课程体系的结构：

```json
{
  "tracks": [
    {
      "id": "python",
      "title": "Python 路线",
      "icon": "...",
      "summary": "...",
      "modules": [
        {
          "id": "python-foundations",
          "title": "基础模块",
          "lessons": [
            {
              "id": "py-basics-01",
              "title": "Python 入门",
              "path": "python/basics_01.md",
              "difficulty": "基础",
              "estimated_minutes": 30,
              "tags": ["入门", "语法"],
              "prerequisites": [],
              "outcomes": ["理解变量和数据类型"]
            }
          ]
        }
      ]
    }
  ]
}
```

### 数据类定义 (`app/content_service.py`)

```python
@dataclass
class Lesson:
    id: str
    title: str
    path: str           # Markdown 文件相对路径
    difficulty: str      # "基础" / "进阶" / "高级"
    summary: str
    estimated_minutes: int
    tags: list[str]
    prerequisites: list[str]
    outcomes: list[str]

@dataclass
class Module:
    id: str
    title: str
    summary: str
    lessons: list[Lesson]

@dataclass
class Track:
    id: str
    title: str
    icon: str
    summary: str
    modules: list[Module]
```

### 内容加载流程

1. `ContentService.__init__()` -- 读取 `course_map.json`
2. 构建 `Track > Module > Lesson` 对象树（带缓存）
3. `LearnWidget` 展示课程列表
4. 用户选择课程后，从 `content/` 目录读取对应 `.md` 文件
5. `mistune` 解析 Markdown，`Pygments` 提供代码语法高亮
6. 渲染为 HTML 在 `QTextBrowser` 中展示

### 懒加载与缓存

- 课程元数据在首次访问时一次性加载并缓存
- Markdown 文件按需读取，使用 LRU 缓存避免重复磁盘 IO
- 损坏内容自动检测（`_looks_corrupt()` 函数），使用回退值

### 练习系统 (`content/metadata/exercises.json`)

```json
{
  "exercises": [
    {
      "id": "py-hello-world",
      "title": "Hello World",
      "track_id": "python",
      "lesson_id": "py-basics-01",
      "difficulty": "基础",
      "prompt": "编写一个 Python 程序...",
      "starter_code": "print(...)\"",
      "hints": ["使用 print() 函数"],
      "tests": [
        {"input": "", "expected_output": "Hello, World!"}
      ]
    }
  ]
}
```

### 评测系统 (`app/practice/evaluator.py`)

根据练习语言分发到不同的评测器：

| 语言 | 评测方式 | 说明 |
|------|----------|------|
| Python | `evaluate_python_code()` | 沙箱执行 + 测试用例验证 |
| SQL | 内存 SQLite 执行 | 真实执行 + 结果比对 + DDL 验证 |
| C / C# | 关键字结构检查 | 检查必需关键字、禁止关键字、AST 节点 |

评测结果数据类：

```python
@dataclass
class EvaluationResult:
    passed: bool
    score: int              # 0-100
    feedback_lines: list[str]
    stdout: str = ""
    duration_sec: int = 0
```

---

## 服务层与依赖注入

### 服务层 (`app/services/`)

项目引入了正式的服务层，将业务逻辑从 Widget 中解耦：

| 服务 | 文件 | 职责 |
|------|------|------|
| `LessonService` | `lesson_service.py` | 课程读取、进度更新 |
| `PracticeDataService` | `practice_data_service.py` | 练习数据管理 |
| `AchievementService` | `achievement_service.py` | 成就解锁与查询 |
| `BookmarkService` | `bookmark_service.py` | 书签增删查 |
| `NoteService` | `note_service.py` | 课程笔记管理 |
| `ReviewService` | `review_service.py` | 基于 SM-2 算法的复习调度 |
| `ConfigService` | `config_service.py` | 用户配置管理 |
| `MentorService` | `mentor_service.py` | AI 导师业务逻辑 |

### 依赖注入容器 (`app/utils/container.py`)

提供轻量级的 DI 容器：

```python
from app.utils.container import Container

container = Container()

# 注册工厂（惰性构造，首次 resolve 时执行）
container.register_factory("db", lambda: AppDatabase())

# 注册为单例（工厂只执行一次）
container.register_factory("db", lambda: AppDatabase(), singleton=True)

# 解析
db = container.resolve("db")

# 依赖注入装饰器
@inject
def create_dashboard(db: AppDatabase = Depends("db")):
    return DashboardWidget(db)
```

---

## 事件系统

### 设计 (`app/utils/events.py`)

事件系统用于跨组件解耦通信，基于发布/订阅模式：

```python
from app.utils.events import event_bus, LessonCompletedEvent

# 订阅
def on_lesson_done(event: LessonCompletedEvent):
    logger.info("课程 %s 已完成", event.lesson_id)

event_bus.subscribe(LessonCompletedEvent, on_lesson_done)

# 发布
event_bus.publish(LessonCompletedEvent(lesson_id="py-01", track_id="python"))

# 退订
event_bus.unsubscribe(LessonCompletedEvent, on_lesson_done)
```

### 事件基类

所有事件继承自 `Event` 基类（frozen dataclass），`timestamp` 自动填充：

```python
@dataclass(frozen=True)
class Event:
    timestamp: datetime = field(default_factory=datetime.now)
```

---

## 插件架构

### 设计 (`app/utils/plugins.py`)

插件系统允许在不修改核心代码的情况下扩展应用功能：

```python
from app.utils.plugins import Plugin, PluginManager

class MyPlugin(Plugin):
    @property
    def name(self) -> str:
        return "my-plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def on_load(self, app) -> None:
        # 插件加载时执行
        pass

    def on_ready(self, app) -> None:
        # 应用就绪后执行
        pass

pm = PluginManager()
pm.register(MyPlugin())
pm.load_all(app)
```

### 插件生命周期

```text
registered -> loading -> loaded -> ready -> running -> stopping -> stopped
```

---

## 安全架构

### 代码执行沙箱 (`app/python_runner.py`)

```text
用户代码输入
    │
    ▼
AST 预检
    ├── 拦截 os.system / subprocess / eval / exec
    ├── 禁止 __class__ / __bases__ / __subclasses__ 等双下划线属性
    └── 限制 import 白名单（math / json / re 等标准库）
    │
    ▼
受限执行环境
    ├── 自定义 __builtins__（仅保留安全函数）
    ├── 文件操作限制在临时目录
    ├── 标准输出限制 12KB
    └── 执行超时 3 秒
    │
    ▼
返回执行结果
```

### 凭证管理 (`app/credentials.py`)

存储优先级：
1. Windows Credential Manager（推荐）
2. keyring 库后端
3. Base64 编码文件回退

### 数据库安全

- WAL 模式 + 写锁保证线程安全
- 外键约束开启（`PRAGMA foreign_keys = ON`）
- 参数化查询防止 SQL 注入
