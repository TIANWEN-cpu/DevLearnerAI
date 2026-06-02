# DevLearnerAI 架构文档

本文档详细描述 DevLearnerAI 的应用架构、Widget 层次、数据流和安全模型。

---

## 目录

- [应用架构概述](#应用架构概述)
- [Widget 层次结构](#widget-层次结构)
- [数据流](#数据流)
- [安全模型](#安全模型)
- [模块职责](#模块职责)
- [数据库设计](#数据库设计)
- [线程模型](#线程模型)

---

## 应用架构概述

DevLearnerAI 采用经典的分层桌面应用架构，基于 PyQt5 构建 GUI，SQLite 作为本地持久化层。

### 分层结构

```
┌───────────────────────────────────────────────┐
│              表现层 (Presentation)              │
│  DevLearnerWindow / Widgets / AIMentorPanel   │
├───────────────────────────────────────────────┤
│              业务逻辑层 (Service)               │
│  ContentService / PracticeService / AI Module │
├───────────────────────────────────────────────┤
│              数据访问层 (Data)                  │
│  AppDatabase / Credentials / python_runner    │
├───────────────────────────────────────────────┤
│              基础设施层 (Infrastructure)        │
│  SQLite / keyring / Windows Credential Mgr   │
└───────────────────────────────────────────────┘
```

### 核心设计原则

1. **关注点分离**: 每个模块职责单一，AI 对话、课程管理、练习评测、代码执行各自独立
2. **向后兼容**: `ai_mentor.py` 和 `practice_service.py` 作为 shim 保留旧导入路径，实际逻辑已拆分到子包
3. **线程安全**: 数据库操作使用 WAL 模式 + 写锁，AI API 调用在后台线程执行
4. **安全优先**: 代码执行沙箱通过 AST 预检 + 受限内置函数 + 超时控制实现多层防护
5. **懒加载**: 课程数据按需加载并缓存，避免启动时加载全部内容

### 启动流程

```
main.py / dev_main.py
    │
    ├── 配置日志级别（生产 INFO / 开发 DEBUG）
    ├── ensure_runtime_dirs()  确保运行时目录存在
    ├── QApplication 初始化
    ├── 应用全局样式 (GLOBAL_STYLE)
    ├── DevLearnerWindow.__init__()
    │   ├── AppDatabase() + init_db()    初始化数据库
    │   ├── ContentService()             加载课程元数据
    │   ├── PracticeService()            加载练习数据
    │   ├── 创建各 Widget 实例
    │   ├── 构建侧边栏导航
    │   ├── 构建内容区域 (QStackedWidget)
    │   ├── 初始化 AI Dock
    │   └── 绑定信号/槽
    ├── window.show()
    └── app.exec()  事件循环
```

---

## Widget 层次结构

```
DevLearnerWindow (QMainWindow)
├── QFrame (root)
│   ├── QFrame (sidebar) ─── 侧边栏导航
│   │   ├── QLabel "LEARNING OS"
│   │   ├── QPushButton (sidebar toggle)
│   │   ├── QFrame (brand card)
│   │   │   ├── QLabel "DevLearner"
│   │   │   └── QLabel (subtitle)
│   │   ├── QLabel "导航"
│   │   └── QPushButton[] (nav_buttons: 首页/学习路径/练习中心/融合项目/算法动画)
│   │
│   └── QFrame (content shell) ─── 内容区域
│       ├── QFrame (topbar)
│       │   ├── QLabel (page_title)
│       │   ├── QLabel (page_subtitle)
│       │   ├── QLabel (date chip)
│       │   └── QPushButton "AI 工作台"
│       │
│       └── QStackedWidget (stack)
│           ├── [0] QScrollArea > DashboardWidget
│           │   ├── Welcome 区域
│           │   ├── 统计卡片行
│           │   ├── 技术栈入口
│           │   └── 快捷操作
│           │
│           ├── [1] QScrollArea > LearnWidget
│           │   ├── 顶部筛选器
│           │   └── QSplitter
│           │       ├── 左面板: 模块/课程列表 (QListWidget)
│           │       └── 主面板: 课程内容 (QTextBrowser) + 笔记
│           │
│           ├── [2] QScrollArea > PracticeWidget
│           │   ├── 顶部筛选器 (技术栈/难度)
│           │   └── QSplitter
│           │       ├── 左面板: 练习列表 (QListWidget)
│           │       └── 主面板: 题目描述 + 代码编辑器 + 运行/提交按钮 + 反馈区
│           │
│           ├── [3] QScrollArea > ProjectsWidget
│           │
│           ├── [4] QScrollArea > AlgoVisualizerWidget
│           │
│           └── [5] QScrollArea > AIMentorPanel (mode="page")
│               ├── QSplitter
│               │   ├── 左面板: 会话列表 (QListWidget) + 操作按钮
│               │   └── 右面板: 聊天区域
│               │       ├── 聊天标题 + 摘要
│               │       ├── QTextBrowser (chat messages)
│               │       ├── 快捷提问按钮行
│               │       ├── 思考提示 (thinking_hint)
│               │       └── 输入框 + 发送按钮
│               └── AI 设置对话框 (QDialog)
│                   ├── 模型连接 Tab
│                   └── 知识库 Tab
│
├── AIMentorDock (QDockWidget)
│   └── AIMentorPanel (mode="dock")
│       ├── 紧凑会话行 (QComboBox)
│       └── 聊天区域
│
└── QStatusBar
```

### Widget 职责

| Widget | 文件 | 职责 |
|--------|------|------|
| `DevLearnerWindow` | `window.py` | 主窗口，管理侧边栏导航、页面切换、AI Dock |
| `DashboardWidget` | `widgets/dashboard.py` | 学习仪表盘，展示统计和快速入口 |
| `LearnWidget` | `widgets/learn.py` | 学习路径页面，展示课程体系和内容 |
| `PracticeWidget` | `widgets/practice.py` | 练习中心，代码编辑、运行和评测 |
| `ProjectsWidget` | `widgets/projects.py` | 融合项目页面 |
| `AlgoVisualizerWidget` | `widgets/algo.py` | 算法动画可视化 |
| `AIMentorPanel` | `ai/chat_handler.py` | AI 对话面板（页面模式和 Dock 模式共用） |
| `AIMentorDock` | `ai/chat_handler.py` | AI 助手 Dock 容器 |

---

## 数据流

### 1. 课程内容加载

```
course_map.json
    │
    ▼
ContentService._discover_tracks()
    │  读取 JSON，解析 tracks 数组
    ▼
ContentService._load_track()  (懒加载 + 缓存)
    │
    ▼
Track > Module > Lesson 数据模型
    │
    ├── LearnWidget 展示课程列表
    │       用户点击课程
    │           │
    │           ▼
    │       ContentService.lesson_markdown(lesson)
    │           │  从 content/ 目录读取 .md 文件
    │           ▼
    │       mistune.render() + Pygments 高亮
    │           │
    │           ▼
    │       QTextBrowser.setHtml()
    │
    └── DashboardWidget 展示课程统计
            │
            ▼
        AppDatabase.track_completion(track_id)
        AppDatabase.completed_lessons()
```

### 2. AI 对话

```
用户输入消息
    │
    ▼
AIMentorPanel.send_message()
    │
    ├── 保存用户消息到 DB
    │   AppDatabase.append_mentor_message(session_id, "user", message)
    │
    ├── 构建系统上下文
    │   _build_system_context()
    │       ├── 基础知识库: ContentService.tracks 摘要
    │       ├── 个性知识库: DB 查询学习进度、练习记录
    │       └── 扩展知识库: mentor_knowledge_files 摘录
    │
    ├── 加载历史消息（最近 12 条）
    │   AppDatabase.load_mentor_messages(session_id)[-12:]
    │
    ├── 发送 API 请求（后台线程）
    │   api_client.send_chat(host, api_key, model, messages)
    │       │
    │       ├── require_https(host)  强制 HTTPS
    │       ├── create_ssl_context()  TLS 验证
    │       └── urllib.request.urlopen()  发送请求
    │
    ├── 保存 AI 回复
    │   AppDatabase.append_mentor_message(session_id, "assistant", reply)
    │
    └── 信号通知 UI 刷新
        response_ready.emit(session_id)
            │
            ▼
        _reload_sessions() + _render_messages()
            │
            ▼
        markdown_renderer.bubble_html()
            │  mistune 渲染 + HTML 白名单净化
            ▼
        QTextBrowser.setHtml()
```

### 3. 练习评测

```
用户编写代码 + 点击"提交"
    │
    ▼
PracticeWidget._evaluate()
    │
    ├── 保存草稿
    │   AppDatabase.save_exercise_draft(exercise_id, title, code)
    │
    ├── PracticeService.evaluate(exercise, code)
    │   │
    │   ├── track_id == "database"
    │   │   └── evaluate_sql(exercise, code)
    │   │       ├── 有 fixture: evaluate_sql_fixture()
    │   │       │   ├── 检查 required_keywords
    │   │       │   ├── 检查 forbidden_keywords
    │   │       │   ├── 内存 SQLite 执行 + 结果比对
    │   │       │   └── DDL 副作用验证 (validate_sql_side_effect)
    │   │       └── 无 fixture: 关键字结构检查
    │   │
    │   ├── track_id in {"c", "csharp"}
    │   │   └── evaluate_keyword_code(exercise, code)
    │   │       ├── 检查 required_keywords
    │   │       └── 检查 forbidden_keywords
    │   │
    │   └── 默认 (Python)
    │       └── evaluate_python(exercise, code)
    │           └── python_runner.evaluate_python_code()
    │               │
    │               ├── AST 语法检查 (ast.parse)
    │               ├── 结构检查 (expected_nodes)
    │               ├── 安全验证 (_validate_code_safety)
    │               ├── 受限环境执行
    │               │   ├── tempfile.TemporaryDirectory
    │               │   ├── SAFE_BUILTINS (受限内置函数)
    │               │   └── exec(compile(code, ...))
    │               ├── required_names 检查
    │               └── tests 表达式求值
    │
    ├── 评分 >= 70 且所有测试通过 -> passed = True
    │
    └── 记录评测结果
        AppDatabase.record_attempt(exercise_id, ..., score, passed, ...)
```

---

## 安全模型

### 代码执行沙箱

代码执行沙箱是 DevLearnerAI 最关键的安全组件，防护目标是防止用户提交的练习代码对宿主系统造成损害。

#### 多层防护

```
用户代码
    │
    ▼ Layer 1: AST 预检 (_validate_code_safety)
    │  ├── 拦截 import 语句
    │  ├── 拦截 eval/exec/compile/breakpoint 等危险调用
    │  ├── 拦截 __class__/__bases__/__subclasses__ 等双下划线属性访问
    │  ├── 拦截 getattr/hasattr 对双下划线属性的访问
    │  └── 拦截包含 __builtins__/__import__ 的字符串常量
    │
    ▼ Layer 2: 受限内置函数 (SAFE_BUILTINS)
    │  ├── 仅暴露安全函数: print, len, range, int, float, str, ...
    │  ├── 替换 open() 为 _safe_open (限制在临时目录内)
    │  └── 不暴露 __import__ (通过 _safe_import 白名单控制)
    │
    ▼ Layer 3: 文件系统隔离
    │  ├── 在 tempfile.TemporaryDirectory 中执行
    │  ├── _safe_open 验证路径在临时目录内
    │  └── 工作目录切换后恢复
    │
    ▼ Layer 4: 输出限制 (LimitedBuffer)
    │  └── 标准输出限制 12KB，超出则截断
    │
    ▼ Layer 5: 超时控制
    │  ├── 执行超时: 3 秒
    │  ├── 评测超时: 4 秒
    │  └── 超时后 terminate -> kill
    │
    ▼ Layer 6: 进程隔离
    │  ├── 使用 multiprocessing spawn context
    │  ├── 子进程中执行（主进程不受影响）
    │  └── 子进程回退: 当无法使用 mp 时，使用 subprocess
```

#### 允许的导入模块白名单

```python
ALLOWED_IMPORTS = {
    "argparse", "collections", "datetime", "functools",
    "itertools", "json", "logging", "math", "pathlib",
    "re", "statistics",
}
```

### 凭证管理

```
API Key 存储优先级:
    │
    ├── Windows: Windows Credential Manager (加密)
    │   └── 通过 ctypes 调用 Advapi32.dll
    │       ├── CredWriteW (存储)
    │       ├── CredReadW (读取)
    │       └── CredDeleteW (删除)
    │
    ├── 非 Windows + keyring 已安装:
    │   └── keyring.set_password("DevLearnerAI", target, secret)
    │
    └── 回退方案:
        └── ~/.devlearnerai/api_key.txt (Base64 编码，非加密)
```

### HTTPS 强制

所有 AI API 通信通过 `api_client.require_https(host)` 强制使用 HTTPS：

- `api_client.test_connection()`: 测试连接前验证
- `api_client.fetch_models()`: 获取模型列表前验证
- `api_client.send_chat()`: 发送消息前验证

非 HTTPS 请求直接抛出 `ValueError`，拒绝执行。

### HTML 净化

Markdown 渲染后的 HTML 通过白名单净化器处理：

- **允许的标签**: `p`, `br`, `h1`-`h6`, `ul`, `ol`, `li`, `code`, `pre`, `strong`, `em`, `a`, `table` 等
- **移除的标签**: `script`, `style`, `iframe`, `object`, `embed`
- **属性过滤**: 移除所有 `on*` 事件处理器；`<a>` 标签仅允许 `href` 且必须为 `http://`、`https://` 或相对路径
- **URI 过滤**: 拒绝 `javascript:`、`data:`、`vbscript:` URI

---

## 模块职责

### app/config.py

全局配置管理：应用名称、版本号、目录路径（BASE_DIR、CONTENT_DIR、USER_DATA_DIR 等）、运行时目录初始化。

### app/window.py

主窗口 `DevLearnerWindow`：构建侧边栏导航、管理 QStackedWidget 页面切换、初始化各 Widget 和 AI Dock、处理全局快捷键。

### app/database.py

`AppDatabase` 类：SQLite 数据库操作的线程安全封装。使用 WAL 模式和写锁确保并发安全。提供课程进度、练习记录、AI 会话、知识库文件等 CRUD 操作。

### app/content_service.py

`ContentService` 类：课程内容管理。从 `course_map.json` 加载 Track > Module > Lesson 层次结构，支持懒加载和缓存。提供 Markdown 文件读取接口。

### app/practice/ (practice_service.py)

练习服务：加载练习元数据，根据语言类型分发到不同评测器（SQL、Python、C/C#），提供练习筛选和草稿管理。

### app/python_runner.py

代码执行沙箱：AST 预检、受限内置函数、临时目录隔离、输出限制、超时控制、进程隔离。支持独立执行和带测试用例的评测两种模式。

### app/ai/ (ai_mentor.py)

AI 导师模块：API 通信（HTTPS + SSL）、对话 UI（页面模式和 Dock 模式）、Markdown 渲染和 HTML 净化、知识库管理、会话管理。

### app/credentials.py

凭证安全存储：跨平台实现，优先使用 Windows Credential Manager，回退到 keyring 或 Base64 文件。

---

## 数据库设计

### 表结构

**lesson_progress** -- 课程学习进度
| 列名 | 类型 | 说明 |
|------|------|------|
| lesson_id | TEXT PK | 课程 ID |
| track_id | TEXT | 所属技术栈 |
| status | TEXT | 状态: not_started / in_progress / completed |
| completed | INTEGER | 是否完成 (0/1) |
| last_opened | TEXT | 最后打开时间 |
| completed_at | TEXT | 完成时间 |

**lesson_notes** -- 课程笔记
| 列名 | 类型 | 说明 |
|------|------|------|
| lesson_id | TEXT PK | 课程 ID |
| content | TEXT | 笔记内容 |
| updated_at | TEXT | 更新时间 |

**practice_attempts** -- 练习记录
| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| exercise_id | TEXT | 练习 ID |
| exercise_title_snapshot | TEXT | 练习标题快照 |
| track_id | TEXT | 所属技术栈 |
| code_snapshot | TEXT | 代码快照 |
| score | INTEGER | 得分 (0-100) |
| passed | INTEGER | 是否通过 (0/1) |
| duration_sec | INTEGER | 耗时（秒） |
| submitted_at | TEXT | 提交时间 |
| feedback | TEXT | 评测反馈 |

**exercise_drafts** -- 练习草稿
| 列名 | 类型 | 说明 |
|------|------|------|
| exercise_id | TEXT PK | 练习 ID |
| exercise_title_snapshot | TEXT | 练习标题快照 |
| code_snapshot | TEXT | 代码快照 |
| updated_at | TEXT | 更新时间 |

**mentor_sessions** -- AI 会话
| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| name | TEXT | 会话名称 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

**mentor_messages** -- AI 消息
| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| session_id | INTEGER FK | 所属会话 |
| role | TEXT | 角色: user / assistant |
| content | TEXT | 消息内容 |
| created_at | TEXT | 创建时间 |

**mentor_api_config** -- API 配置
| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 固定为 1 |
| host | TEXT | API 端点 |
| api_key | TEXT | (已迁移到 keyring，字段保留为空) |
| model | TEXT | 模型名称 |
| key_alias | TEXT | keyring 中的别名 |

**mentor_workspace_state** -- 工作台状态
| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 固定为 1 |
| active_session_id | INTEGER | 当前活跃会话 |
| use_base | INTEGER | 启用基础知识库 |
| use_personal | INTEGER | 启用个性知识库 |
| use_custom | INTEGER | 启用扩展知识库 |

**mentor_knowledge_files** -- 知识库文件
| 列名 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增 ID |
| display_name | TEXT | 显示名称 |
| file_path | TEXT | 文件路径 |
| excerpt | TEXT | 文件摘录 |
| created_at | TEXT | 添加时间 |

### 数据库迁移

- `init_db()` 使用 `CREATE TABLE IF NOT EXISTS` 兼容表结构演进
- `ALTER TABLE` 添加新列（如 `key_alias`、`exercise_title_snapshot`、`code_snapshot`）
- 旧版 API 密钥自动迁移到 keyring (`_migrate_legacy_api_key_if_needed`)
- 损坏的聊天记录自动检测和修复 (`repair_corrupted_mentor_history`)
- 旧版数据库自动从 `db/learner.db` 迁移 (`_migrate_legacy_db_if_needed`)

---

## 线程模型

```
主线程 (Qt 事件循环)
    │
    ├── UI 渲染、事件处理
    ├── 数据库读操作（通过 connect() 上下文管理器获取锁）
    └── 数据库写操作（通过 connect() 上下文管理器获取写锁）
    │
    ├── AI 后台线程 (daemon)
    │   ├── _chat_worker: 发送 API 请求、保存回复
    │   ├── _test_connection_worker: 测试 API 连接
    │   └── _fetch_models_worker: 获取模型列表
    │   │
    │   └── 通过 PyQt5 Signal 回到主线程更新 UI
    │       ├── response_ready
    │       ├── models_ready
    │       └── status_ready
    │
    └── 代码执行子进程 (multiprocessing spawn)
        ├── _run_exec_worker: 执行代码
        └── _evaluate_worker: 评测代码
        │
        └── 通过 Pipe 返回结果，主线程通过 Signal 更新 UI
            ├── run_ready
            └── evaluation_ready
```

### 数据库并发控制

- **连接管理**: 全局单例连接，使用 `_connection_lock` 保护创建和检查
- **写操作**: 使用 `_db_lock` (threading.Lock) 确保同一时刻只有一个写操作
- **WAL 模式**: `PRAGMA journal_mode = WAL` 允许读写并发
- **上下文管理器**: `connect()` 方法自动获取锁、提交/回滚、释放锁
