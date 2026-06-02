# 项目架构详解

本文档详细介绍 DevLearner AI 的技术架构、模块划分和数据流设计。

---

## 目录

- [总体架构](#总体架构)
- [技术栈](#技术栈)
- [目录结构](#目录结构)
- [核心模块详解](#核心模块详解)
- [数据流](#数据流)
- [数据库设计](#数据库设计)
- [安全架构](#安全架构)
- [性能优化](#性能优化)

---

## 总体架构

DevLearner AI 采用经典的桌面应用分层架构：

```
┌──────────────────────────────────────────────────────────────────┐
│                      DevLearnerWindow (QMainWindow)              │
│  ┌─────────────┐  ┌───────────────────────────────────────────┐  │
│  │   Sidebar    │  │          QStackedWidget                  │  │
│  │             │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  [首页]     │  │  │Dashboard │ │  Learn   │ │ Practice │   │  │
│  │  [学习路径]  │──│  Widget   │ │  Widget  │ │  Widget  │   │  │
│  │  [练习中心]  │  │  └──────────┘ └──────────┘ └──────────┘   │  │
│  │  [融合项目]  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  [算法动画]  │  │  │ Projects │ │  Algo    │ │   AI     │   │  │
│  │             │  │  │  Widget  │ │Visualizer│ │  Panel   │   │  │
│  │             │  │  └──────────┘ └──────────┘ └──────────┘   │  │
│  └─────────────┘  └───────────────────────────────────────────┘  │
│                                              ┌──────────────────┐│
│                                              │ AIMentorDock     ││
│                                              │ (侧边 AI 助手)    ││
│                                              └──────────────────┘│
└──────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ ContentService   │  │ PracticeService │  │  AI Module       │
│ (课程加载)       │  │ (练习评测)      │  │ (API + 知识库)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                    AppDatabase (SQLite + WAL)                     │
└──────────────────────────────────────────────────────────────────┘
```

### 分层说明

| 层级 | 说明 |
|------|------|
| **表示层** | PyQt5 Widget，负责 UI 渲染和用户交互 |
| **业务层** | Service 模块，处理课程加载、练习评测、AI 通信 |
| **数据层** | SQLite 数据库 + JSON 元数据文件 |
| **安全层** | 凭证管理、沙箱隔离、HTML 净化 |

---

## 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 语言 | Python | 3.9+ | 主要开发语言 |
| GUI 框架 | PyQt5 | >= 5.15 | 桌面界面 |
| 数据库 | SQLite | 内置 | 本地数据持久化 |
| Markdown | mistune | >= 3.0 | Markdown 渲染 |
| 语法高亮 | Pygments | 内置 | 代码高亮显示 |
| 凭证管理 | keyring | >= 24.0 | API 密钥安全存储 |
| AI 接口 | urllib | 内置 | HTTP 通信（OpenAI 兼容 API） |
| 打包 | PyInstaller | - | 生成可执行文件 |
| 代码检查 | Ruff | - | Linter + Formatter |
| 测试 | pytest + coverage | - | 单元测试和覆盖率 |

---

## 目录结构

```text
D:\codelearnhleper\
├── main.py                  # 生产环境入口
├── dev_main.py              # 开发环境入口（DEBUG 日志）
├── pyproject.toml           # 项目元数据 + Ruff/pytest/coverage 配置
├── requirements.txt         # 运行时依赖（最小集）
├── Makefile                 # 常用开发命令
│
├── app/                     # 应用核心代码
│   ├── __init__.py
│   ├── config.py            # 全局配置（路径、版本、目录初始化）
│   ├── window.py            # 主窗口（侧边栏导航 + 页面管理）
│   ├── database.py          # SQLite 数据库层（线程安全）
│   ├── content_service.py   # 课程内容加载与管理
│   ├── practice_service.py  # 练习服务（兼容 shim，委托到 practice/）
│   ├── python_runner.py     # 代码执行沙箱（AST 预检 + 受限内置函数）
│   ├── credentials.py       # 凭证安全存储
│   ├── styles.py            # 全局样式定义
│   ├── effects.py           # 加载/进度 UI 辅助
│   ├── highlighter.py       # 代码语法高亮
│   ├── localized_inputs.py  # 本地化输入组件
│   │
│   ├── ai/                  # AI 导师子模块
│   │   ├── __init__.py
│   │   ├── api_client.py    # API 通信（HTTPS、SSL、URL 构建）
│   │   ├── chat_handler.py  # 对话 UI（AIMentorPanel、AIMentorDock）
│   │   ├── markdown_renderer.py  # Markdown 渲染 + HTML 净化
│   │   └── models.py        # 数据类和安全常量
│   │
│   ├── practice/            # 练习子模块
│   │   ├── __init__.py
│   │   ├── evaluator.py     # 评测逻辑（SQL、关键字、Python）
│   │   ├── exercise_loader.py  # 练习数据加载与回退
│   │   ├── models.py        # Exercise / EvaluationResult 数据类
│   │   └── normalizer.py    # 结果集标准化
│   │
│   └── widgets/             # UI 组件
│       ├── __init__.py
│       ├── dashboard.py     # 学习仪表盘
│       ├── learn.py         # 学习路径页面
│       ├── practice.py      # 练习中心页面
│       ├── projects.py      # 融合项目页面
│       └── algo.py          # 算法可视化组件
│
├── content/                 # 课程内容（Markdown + JSON 元数据）
│   ├── python/              # Python 课程 Markdown 文件
│   ├── c/                   # C 语言课程
│   ├── cpp/                 # C++ 课程
│   ├── csharp/              # C# 课程
│   ├── database/            # 数据库课程
│   ├── algorithms/          # 算法课程
│   ├── integration/         # 融合项目内容
│   ├── projects/            # 项目文档
│   └── metadata/
│       ├── course_map.json  # 课程元数据（Track/Module/Lesson）
│       ├── exercises.json   # 练习元数据
│       ├── exercise_fallbacks.json  # 练习回退数据
│       └── sql_query_fixtures.json  # SQL 测试数据
│
├── tests/                   # 测试套件
│   ├── conftest.py          # 共享 fixture
│   ├── test_python_runner.py
│   ├── test_database.py
│   └── ...                  # 其他测试文件
│
├── scripts/                 # 构建与数据重建脚本
│   ├── build/               # PyInstaller 打包脚本
│   └── rebuild/             # 课程数据重建脚本
│
├── styles/                  # 样式资源
├── docs/                    # 项目文档
├── db/                      # 旧版数据库目录（自动迁移）
└── codexgame/               # Codex 小游戏子项目
```

---

## 核心模块详解

### config.py -- 全局配置

负责应用的全局配置管理：

| 配置项 | 说明 |
|--------|------|
| `APP_NAME` | 应用名称 `"DevLearnerAI"` |
| `APP_VERSION` | 应用版本（从 pyproject.toml 读取） |
| `BASE_DIR` | 项目根目录 |
| `RUNTIME_DIR` | 运行时目录（PyInstaller 打包后为临时目录） |
| `CONTENT_DIR` | 课程内容目录 |
| `METADATA_DIR` | 元数据目录 |
| `USER_DATA_DIR` | 用户数据根目录 |
| `DB_PATH` | 数据库文件路径 |
| `LOG_DIR` | 日志目录 |
| `CACHE_DIR` | 缓存目录 |

关键函数：
- `ensure_runtime_dirs()` -- 确保所有运行时目录存在
- `_resource_dir()` -- 智能资源目录查找（支持 PyInstaller 打包环境）

### window.py -- 主窗口

应用的主窗口实现，基于 `QMainWindow`：

- **侧边栏导航** -- 左侧导航栏，切换各功能页面
- **QStackedWidget** -- 右侧内容区，管理多个页面的切换
- **AIMentorDock** -- 侧边 AI 助手面板

### database.py -- 数据库层

线程安全的 SQLite 数据库操作封装：

**连接管理**：
- 单例模式，全局共享一个连接
- WAL 日志模式，提高并发性能
- 外键约束开启
- 连接健康检查和自动重建

**写操作保护**：
- 使用 `threading.Lock()` 保护写操作
- 确保多线程环境下数据一致性

**主要表结构**：
- `lesson_progress` -- 课程进度
- `practice_attempts` -- 练习记录
- `lesson_notes` -- 学习笔记
- `mentor_sessions` -- AI 会话
- `mentor_messages` -- AI 消息
- `mentor_api_config` -- API 配置
- `exercise_drafts` -- 练习草稿

### content_service.py -- 课程内容服务

负责课程内容的加载和管理：

1. 读取 `course_map.json` 构建课程层次结构
2. 懒加载课程 Markdown 文件
3. 缓存已加载的课程内容
4. 提供按技术栈、模块、课时查询的接口

### practice_service.py -- 练习服务

练习服务的兼容层，委托到 `practice/` 子模块：

- `evaluator.py` -- 评测引擎
- `exercise_loader.py` -- 练习数据加载
- `models.py` -- 数据模型
- `normalizer.py` -- 结果标准化

### python_runner.py -- 代码执行沙箱

安全的 Python 代码执行环境：

**AST 预检**：
- 使用 Python `ast` 模块解析代码
- 拦截 `os.system`、`subprocess`、`eval`、`exec` 等危险调用
- 禁止访问 `__class__`、`__bases__` 等双下划线属性

**执行限制**：
- 白名单模块导入（`math`、`json`、`re` 等）
- 文件操作限制在临时目录
- 标准输出限制 12KB
- 执行超时 3 秒
- 评测超时 4 秒

### credentials.py -- 凭证管理

安全的 API 密钥存储：

- Windows：使用 Windows Credential Manager
- 其他平台：回退到 keyring 或 base64 编码文件
- 存储别名：`DevLearnerAI:mentor_api_key`

### ai/ -- AI 导师子模块

| 文件 | 职责 |
|------|------|
| `api_client.py` | HTTPS 通信、连接测试、模型列表、消息发送（支持流式响应） |
| `chat_handler.py` | 对话 UI 组件（AIMentorPanel、AIMentorDock） |
| `markdown_renderer.py` | Markdown 渲染 + HTML 白名单净化 |
| `models.py` | 数据类定义和安全常量（标签白名单、危险标签列表） |

---

## 数据流

### 课程加载流程

```
course_map.json → ContentService → Track/Module/Lesson 结构
                                       ↓
                              LearnWidget 展示列表
                                       ↓
                              用户选择课程 → 读取 .md 文件
                                       ↓
                              mistune 渲染 → Pygments 高亮 → 显示
                                       ↓
                              进度写入 lesson_progress 表
```

### AI 对话流程

```
用户输入消息 → AIMentorPanel
                    ↓
           构建系统上下文（课程摘要 + 进度 + 知识库）
                    ↓
           加载最近 12 条历史消息
                    ↓
           api_client.send_chat() → HTTPS → OpenAI 兼容 API
                    ↓
           响应 → markdown_renderer → 安全 HTML
                    ↓
           显示 + 持久化到 mentor_messages 表
```

### 练习评测流程

```
用户编写代码 → PracticeWidget
                    ↓
           保存草稿到 exercise_drafts 表
                    ↓
           根据语言分发评测：
             Python → evaluate_python() → python_runner 沙箱执行
             SQL    → evaluate_sql()    → 内存数据库真实执行
             C/C#   → evaluate_keyword_code() → 关键字检查
                    ↓
           评测结果 → practice_attempts 表
                    ↓
           显示反馈（通过/未通过 + 得分 + 详细信息）
```

---

## 数据库设计

### 技术选型

- **数据库**：SQLite
- **日志模式**：WAL（Write-Ahead Logging）
- **线程安全**：写操作使用 `threading.Lock()`
- **外键约束**：开启 `PRAGMA foreign_keys = ON`

### 表结构

#### lesson_progress -- 课程进度

| 字段 | 类型 | 说明 |
|------|------|------|
| lesson_id | TEXT | 课时标识 |
| completed | INTEGER | 完成状态（0/1） |
| completed_at | TEXT | 完成时间 |

#### practice_attempts -- 练习记录

| 字段 | 类型 | 说明 |
|------|------|------|
| exercise_id | TEXT | 练习标识 |
| code | TEXT | 提交的代码 |
| passed | INTEGER | 是否通过 |
| score | INTEGER | 评测分数 |
| feedback | TEXT | 反馈信息 |
| attempted_at | TEXT | 提交时间 |

#### mentor_sessions -- AI 会话

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | TEXT | 会话标识 |
| title | TEXT | 会话标题 |
| created_at | TEXT | 创建时间 |

#### mentor_messages -- AI 消息

| 字段 | 类型 | 说明 |
|------|------|------|
| session_id | TEXT | 所属会话 |
| role | TEXT | 角色（user/assistant） |
| content | TEXT | 消息内容 |
| created_at | TEXT | 发送时间 |

---

## 安全架构

### 多层安全防护

1. **代码执行沙箱**（`python_runner.py`）
   - AST 预检拦截危险代码
   - 禁止危险内置函数
   - 模块白名单
   - 文件操作隔离
   - 输出和超时限制

2. **API 密钥安全**（`credentials.py`）
   - Windows Credential Manager
   - keyring 回退
   - 不明文存储

3. **网络通信安全**（`api_client.py`）
   - 强制 HTTPS
   - TLS 证书验证
   - SSL 上下文加固

4. **HTML 输出净化**（`markdown_renderer.py`）
   - 标签白名单过滤
   - 危险标签移除（script、style、iframe 等）
   - 事件处理器过滤
   - 危险 URI 拦截

5. **数据库安全**（`database.py`）
   - WAL 模式
   - 写操作线程锁
   - 连接健康检查

---

## 性能优化

### 数据库优化

- WAL 模式提高读写并发
- 索引优化查询性能
- 连接池化和缓存

### 课程加载优化

- Markdown 文件懒加载
- 已加载内容缓存
- 预加载常用课程

### AI 通信优化

- 流式响应支持
- 连接状态缓存（5 分钟 TTL）
- 请求去重（防止并发重复请求）

### 内存管理

- 会话定期清理
- 对话历史限制（最近 12 条上下文）
- 缓存淘汰策略

---

## 参见 (See Also)

- [系统架构（概念版）](../concepts/architecture.md) - 更详细的架构设计
- [模块一览](../reference/modules.md) - 所有模块的完整接口
- [数据库 Schema](../reference/database-schema.md) - 数据表结构详情
- [安全模型](../concepts/security-model.md) - 安全防护详情
- [构建指南](building.md) - PyInstaller 打包
- [术语表](../glossary.md) - 专业术语定义
