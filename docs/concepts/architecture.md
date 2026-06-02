# 系统架构

本文档描述 DevLearnerAI 的整体架构设计、分层结构和核心数据流。

---

## 整体架构图

```text
┌──────────────────────────────────────────────────────────────────┐
│                    DevLearnerWindow (QMainWindow)                │
│  ┌─────────────┐  ┌───────────────────────────────────────────┐  │
│  │   Sidebar    │  │          QStackedWidget                  │  │
│  │             │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  [首页]     │  │  │Dashboard │ │  Learn   │ │ Practice │   │  │
│  │  [学习路径]  │──│  │  Widget  │ │  Widget  │ │  Widget  │   │  │
│  │  [练习中心]  │  │  └──────────┘ └──────────┘ └──────────┘   │  │
│  │  [融合项目]  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  [算法动画]  │  │  │ Projects │ │  Algo    │ │   AI     │   │  │
│  │             │  │  │  Widget  │ │Visualizer│ │  Panel   │   │  │
│  │             │  │  └──────────┘ └──────────┘ └──────────┘   │  │
│  └─────────────┘  └───────────────────────────────────────────┘  │
│                                              ┌──────────────────┐│
│                                              │ AIMentorDock     ││
│                                              │ (侧边 AI 助手)   ││
│                                              └──────────────────┘│
└──────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ ContentService   │  │ PracticeService │  │  AI Module       │
│ (课程加载)       │  │ (练习评测)      │  │ (API + 知识库)   │
│                  │  │                 │  │                  │
│ Track/Module/    │  │ Exercise/       │  │ api_client.py    │
│ Lesson 数据模型  │  │ EvaluationResult│  │ chat_handler.py  │
│ course_map.json  │  │ evaluator.py    │  │ markdown_render  │
│ exercises.json   │  │ normalizer.py   │  │ models.py        │
└────────┬─────────┘  └────────┬────────┘  └────────┬─────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                    AppDatabase (SQLite + WAL)                     │
│  lesson_progress │ practice_attempts │ mentor_sessions           │
│  lesson_notes    │ exercise_drafts   │ mentor_messages           │
│  mentor_api_config │ mentor_workspace_state                      │
│  mentor_knowledge_files                                          │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────┐
│  Credentials Module   │
│  Windows Credential   │
│  Manager / keyring /  │
│  Base64 文件回退       │
└──────────────────────┘
```

---

## 分层设计

系统采用经典的三层架构模式：

### 1. 表示层 (Widgets)

表示层负责用户界面渲染和交互，基于 PyQt5 构建。所有 UI 组件位于 `app/widgets/` 目录。

**核心组件**：

- `DevLearnerWindow` - 主窗口，管理侧边栏导航和页面切换
- `DashboardWidget` - 学习仪表盘，显示进度概览
- `LearnWidget` - 课程学习页面，渲染 Markdown 课程内容
- `PracticeWidget` - 练习中心，代码编辑和评测
- `ProjectsWidget` - 融合项目展示
- `AlgoVisualizerWidget` - 算法动画可视化
- `AIMentorPanel` / `AIMentorDock` - AI 导师界面（工作台和侧边面板两种形态）

### 2. 业务逻辑层 (Services)

业务逻辑层封装了核心功能的处理逻辑，与 UI 无直接耦合。

| 服务 | 模块 | 职责 |
|------|------|------|
| 课程服务 | `app/content_service.py` | 课程元数据解析、三级数据模型构建、Markdown 内容加载与缓存 |
| 练习服务 | `app/practice/evaluator.py` | 多语言代码评测（Python 沙箱、SQL 真实执行、C/C# 关键字检查） |
| 练习加载 | `app/practice/exercise_loader.py` | 练习 JSON 数据解析、编码损坏修复、SQL fixture 加载 |
| AI 通信 | `app/ai/api_client.py` | HTTPS 请求、流式响应、连接缓存、请求去重 |
| Markdown 渲染 | `app/ai/markdown_renderer.py` | Markdown 转 HTML、XSS 净化、聊天气泡构建 |
| 代码沙箱 | `app/python_runner.py` | AST 预检、受限内置函数、进程隔离执行、超时控制 |

### 3. 数据层

数据层负责所有持久化操作，包括数据库和文件系统。

| 组件 | 模块 | 职责 |
|------|------|------|
| 数据库 | `app/database.py` | SQLite 操作封装（WAL 模式 + 线程锁 + 统计缓存） |
| 凭证管理 | `app/credentials.py` | 跨平台密钥存储（Windows Credential Manager / keyring / Base64 回退） |
| 配置 | `app/config.py` | 全局路径常量、运行时目录初始化、版本号管理 |

---

## 数据流

### 课程加载流程

```text
course_map.json ──→ ContentService ──→ Track/Module/Lesson 对象
                                          │
                                          ▼
content/*.md ──→ Markdown 渲染 (mistune) ──→ HTML 输出
                                          │
                                          ▼
                                    AppDatabase.lesson_progress
```

1. `ContentService` 读取 `content/metadata/course_map.json`
2. 构建 Track > Module > Lesson 层次结构（懒加载 + 缓存）
3. `LearnWidget` 展示课程列表，用户选择后从 `content/` 目录读取 Markdown 文件
4. `mistune` 渲染为 HTML，`Pygments` 提供语法高亮
5. 学习进度写入 `AppDatabase.lesson_progress` 表

### AI 对话流程

```text
用户输入 ──→ AIMentorPanel ──→ 构建系统上下文
                                 │
                                 ▼
                         api_client.send_chat()
                                 │
                                 ▼
                     OpenAI 兼容 API (HTTPS)
                                 │
                                 ▼
                    markdown_renderer.render_message_html()
                                 │
                                 ▼
                     AppDatabase.mentor_messages
```

1. 用户在 `AIMentorPanel` 输入消息
2. 构建系统上下文（课程摘要 + 学习进度 + 知识库文件）
3. 加载最近 12 条历史消息作为上下文
4. 通过 `api_client.send_chat()` 发送 HTTPS 请求到 OpenAI 兼容 API
5. 响应通过 `markdown_renderer` 渲染为安全 HTML
6. 消息持久化到 `mentor_messages` 表

### 练习评测流程

```text
用户代码 ──→ PracticeWidget ──→ 语言分发
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            Python 沙箱        SQL 真实执行     C/C# 关键字检查
            (AST 预检)        (内存 SQLite)     (结构分析)
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                          EvaluationResult
                                    │
                                    ▼
                    AppDatabase.practice_attempts
                    AppDatabase.exercise_drafts
```

1. 用户在 `PracticeWidget` 编写代码
2. 根据练习语言分发到对应评测器：
   - Python: `evaluate_python()` -> `python_runner` 沙箱执行
   - SQL: `evaluate_sql()` -> 内存数据库真实执行 + 结果比对
   - C/C#: `evaluate_keyword_code()` -> 关键字结构检查
3. 评测结果写入 `practice_attempts` 表
4. 草稿保存到 `exercise_drafts` 表

---

## 启动流程

应用启动经过以下阶段：

```text
main.py
  │
  ├── ensure_runtime_dirs()  ← 确保数据目录存在
  │
  ├── logging 初始化         ← 文件 + 控制台双输出
  │
  └── run()                  ← window.py 中定义
        │
        ├── QApplication 创建 + 全局样式加载
        │
        ├── QSplashScreen 显示
        │
        ├── DevLearnerWindow.__init__()
        │     ├── AppDatabase 初始化 + 迁移检查
        │     ├── ContentService 加载元数据索引
        │     ├── PracticeService 初始化
        │     ├── DashboardWidget / LearnWidget / PracticeWidget 创建
        │     ├── QTimer.singleShot(50, _deferred_init)  ← 延迟加载
        │     │     ├── ProjectsWidget
        │     │     ├── AlgoVisualizerWidget
        │     │     ├── AIMentorPanel
        │     │     └── AIMentorDock
        │     └── 键盘快捷键注册
        │
        ├── window.show()
        ├── splash.finish()
        │
        └── app.exec()  ← Qt 事件循环
```

### 延迟初始化策略

为了保证启动速度，系统采用分层延迟初始化：

| 阶段 | 延迟 | 组件 | 原因 |
|------|------|------|------|
| 立即 | 0ms | Dashboard, Learn, Practice | 用户首次可见 |
| 延迟 1 | 50ms | Projects | 可能不会立即访问 |
| 延迟 2 | 200ms | AlgoVisualizer | 较重的动画组件 |
| 延迟 3 | 350ms | AIMentorPanel | AI 功能可能不会立即使用 |
| 延迟 4 | 550ms | AIMentorDock | 侧边 AI 助手 |

---

## 线程模型

```
主线程 (Qt 事件循环)
  │
  ├── UI 渲染和事件处理
  │
  └── AI API 请求（使用 urllib，在后台线程处理网络 I/O）

代码执行子进程 (multiprocessing.spawn)
  │
  └── Python 代码在隔离子进程中执行，通过 Pipe 传递结果
      超时后 terminate() → kill()
```

- **数据库操作**：使用全局写锁 `_db_lock` 确保线程安全
- **AI API 请求**：请求去重机制防止相同请求并发
- **代码执行**：使用 `multiprocessing.spawn` 上下文创建子进程，通过 `Pipe` 传递结果

---

## 配置管理

所有路径和常量集中在 `app/config.py` 管理：

```python
# 关键路径常量
CONTENT_DIR   # 课程内容根目录（content/）
METADATA_DIR  # 元数据目录（content/metadata/）
DB_PATH       # 数据库路径（%APPDATA%/DevLearnerAI/data/app.db）
LOG_DIR       # 日志目录
CACHE_DIR     # 缓存目录
DRAFT_DIR     # 草稿目录
```

运行时目录在 `ensure_runtime_dirs()` 中自动创建，确保应用首次运行时不会因目录缺失而崩溃。

---

## 相关文档

- [Widget 系统](widget-system.md) - UI 组件层次详情
- [安全模型](security-model.md) - 安全防护机制
- [模块一览](../reference/modules.md) - 所有模块的详细接口
