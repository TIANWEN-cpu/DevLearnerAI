# DevLearnerAI

[![CI](https://github.com/TIANWEN-cpu/DevLearnerAI/actions/workflows/ci.yml/badge.svg)](https://github.com/TIANWEN-cpu/DevLearnerAI/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/TIANWEN-cpu/DevLearnerAI)](https://github.com/TIANWEN-cpu/DevLearnerAI/releases)
[![License](https://img.shields.io/github/license/TIANWEN-cpu/DevLearnerAI)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1000%2B-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-40%25%2B-yellowgreen)](tests/)

**AI 驱动的桌面编程学习平台 | Python / PyQt5 / SQLite**

DevLearnerAI 是一款面向编程初学者和进阶学习者的桌面应用程序，集成了 AI 智能导师、代码执行沙箱、课程体系、交互式练习、算法可视化和学习仪表盘，将学习路径、练习、项目和 AI 助手整合到一个清晰的工作台中。

---

## 目录

- [v1.1.0 新增内容](#v110-新增内容)
- [功能特性](#功能特性)
- [截图](#截图)
- [架构概览](#架构概览)
- [安装与运行](#安装与运行)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [安全加固](#安全加固)
- [开发指南](#开发指南)
- [常见问题](#常见问题)
- [故障排除](#故障排除)
- [贡献](#贡献)
- [许可证](#许可证)

---

## v1.1.0 新增内容

v1.1.0 是基于 v1.0.0 的全面成熟度升级，主要改进如下：

- **架构重构** -- 将 `ai_mentor.py` 和 `practice_service.py` 各超 1200 行的巨型模块拆分为独立子包（`app/ai/`、`app/practice/`），保持完全向后兼容
- **测试覆盖** -- 测试用例从 0 增长至 **1000+** 条，涵盖沙箱安全、数据库、评测逻辑、AI 模块、集成流程和安全边界
- **工程化** -- 引入 Ruff（lint + format）、Makefile、pyproject.toml、requirements.txt、GitHub Actions CI（Python 3.9 + 3.12 矩阵）
- **构建系统** -- 统一构建脚本 `scripts/build/build.py`，支持 release / dev / codex 三种变体，自动生成 `.spec` 文件
- **版本管理** -- 版本号以 `pyproject.toml` 为单一来源，`app/config.py` 通过 `importlib.metadata` 动态读取
- **文档** -- 新增 CHANGELOG.md、CONTRIBUTING.md、改进计划、成熟度计划、构建与发布指南

> 详细变更记录见 [CHANGELOG.md](CHANGELOG.md)

---

## 功能特性

### AI 智能导师

- 支持 OpenAI 兼容 API 的对话式编程辅导
- 可切换不同 API 端点和模型
- 上下文感知的知识库（基础知识库、个性知识库、扩展文件知识库）
- 多会话管理：按主题拆分对话（如"Python 调试"、"数据库报表"、"项目拆解"）
- 快捷提问：解释当前课程、分析当前代码、拆解当前项目
- AI 工作台（独立页面）与侧边助手（Dock 面板）两种模式可切换
- Markdown 渲染支持，代码语法高亮

### 代码执行沙箱

- 安全执行 Python 代码，通过 AST 预检拦截危险代码
- 限制 `os.system`、`subprocess`、`eval`、`exec` 等危险内置函数
- 限制可导入模块白名单（math、json、re 等标准库）
- 文件操作限制在临时工作目录内
- 输出缓冲区限制（12KB），防止内存滥用
- 支持 C / C++ / C# / SQL 代码的结构检查评测

### 课程体系

- 涵盖 Python、C、C++、C#、数据库、算法、AI 等多个技术栈
- 课程内容以 Markdown 格式组织，支持语法高亮渲染
- Track > Module > Lesson 三级层次结构
- 课程完成度追踪和笔记功能
- 前置条件和学习目标标注

### 交互式练习

- 编程练习与自动评测，支持 Python 实际运行、SQL 真实数据库比对、C/C# 关键字检查
- 练习中心支持按技术栈和难度筛选
- 练习草稿自动保存与恢复
- 评测反馈包含语法检查、结构检查、运行结果、测试用例通过率等多维度评分
- 练习历史记录持久化

### 融合项目

- 从单点知识走向可交付的真实项目，培养工程实践能力
- 项目文档以 Markdown 格式组织

### 算法动画

- 将抽象的算法步骤可视化，帮助理解排序、查找等经典算法
- 交互式动画控制

### 学习仪表盘

- 学习进度追踪、课程完成统计
- 每日学习概览
- 连续学习天数统计
- 练习平均分展示
- 快速导航到各技术栈

### Codex 账号切换器

- 快速切换 Codex 账号配置（独立子项目）

### 工程化特性

- Ruff 统一 lint + format（替代 flake8 + isort + black）
- pytest 测试框架，1000+ 测试用例，覆盖沙箱安全、数据库、评测、AI 模块
- GitHub Actions CI，支持 Python 3.9 + 3.12 矩阵，覆盖率报告
- 统一构建脚本，支持 release / dev / codex 三种打包变体
- 版本号单一来源管理（pyproject.toml + importlib.metadata）
- 完整的贡献指南和构建发布文档

---

## 截图

<!-- 将截图放入 docs/ 目录，然后取消注释以下行即可展示：
<p align="center">
  <img src="docs/screenshot-dashboard.png" alt="学习仪表盘" width="600">
  <img src="docs/screenshot-learn.png" alt="学习路径" width="600">
  <img src="docs/screenshot-practice.png" alt="练习中心" width="600">
  <img src="docs/screenshot-ai.png" alt="AI 工作台" width="600">
</p>
-->

---

## 架构概览

```text
┌──────────────────────────────────────────────────────────────────┐
│                      DevLearnerWindow (QMainWindow)              │
│  ┌─────────────┐  ┌───────────────────────────────────────────┐  │
│  │   Sidebar    │  │          QStackedWidget                  │  │
│  │             │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  [首页]     │  │  │Dashboard │ │  Learn   │ │ Practice │   │  │
│  │  [学习路径]  │──▶│  Widget   │ │  Widget  │ │  Widget  │   │  │
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

### 数据流

**课程加载流程**:
1. `ContentService` 读取 `content/metadata/course_map.json`
2. 构建 Track > Module > Lesson 层次结构（懒加载 + 缓存）
3. `LearnWidget` 展示课程列表，用户选择后从 `content/` 目录读取 Markdown 文件
4. `mistune` 渲染为 HTML，`Pygments` 提供语法高亮
5. 学习进度写入 `AppDatabase.lesson_progress` 表

**AI 对话流程**:
1. 用户在 `AIMentorPanel` 输入消息
2. 构建系统上下文（课程摘要 + 学习进度 + 知识库文件）
3. 加载最近 12 条历史消息作为上下文
4. 通过 `api_client.send_chat()` 发送 HTTPS 请求到 OpenAI 兼容 API
5. 响应通过 `markdown_renderer` 渲染为安全 HTML
6. 消息持久化到 `mentor_messages` 表

**练习评测流程**:
1. 用户在 `PracticeWidget` 编写代码
2. 根据练习语言分发到对应评测器：
   - Python: `evaluate_python()` -> `python_runner` 沙箱执行
   - SQL: `evaluate_sql()` -> 内存数据库真实执行 + 结果比对
   - C/C#: `evaluate_keyword_code()` -> 关键字结构检查
3. 评测结果写入 `practice_attempts` 表
4. 草稿保存到 `exercise_drafts` 表

---

## 安装与运行

### 环境要求

- Python 3.9+
- Windows（推荐，部分功能依赖 Windows Credential Manager）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动应用

```bash
python main.py
```

或使用开发入口（启用 DEBUG 日志）：

```bash
python dev_main.py
```

### 打包为可执行文件

```bash
pip install pyinstaller
python scripts/build/build_dev_exe.py
```

打包产物将输出到 `dist/` 目录。

### 构建验证

打包前可通过 dry-run 模式验证构建配置：

```bash
python scripts/build/build.py --variant release --dry-run
```

或使用 Makefile：

```bash
make verify-build
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3 |
| GUI 框架 | PyQt5 |
| 数据库 | SQLite（WAL 模式 + 线程锁） |
| Markdown 渲染 | mistune |
| 语法高亮 | Pygments |
| AI 接口 | OpenAI 兼容 API（支持自定义端点） |
| 凭证管理 | keyring / Windows Credential Manager |
| 打包 | PyInstaller |
| 代码检查 | Ruff（linter + formatter） |
| 测试 | pytest + coverage |

---

## 项目结构

```text
D:\codelearnhleper\
├── scripts/                 # 构建与数据重建脚本
│   ├── build/               # PyInstaller 打包脚本
│   └── rebuild/             # 课程数据重建脚本
├── main.py                  # 生产环境启动入口
├── dev_main.py              # 开发环境启动入口
├── pyproject.toml           # 项目元数据 + ruff/pytest/coverage 配置
├── requirements.txt         # 运行时依赖（最小集）
├── Makefile                 # 本地开发命令（lint / format / test）
├── LICENSE                  # MIT 许可证
├── app/
│   ├── __init__.py
│   ├── config.py            # 应用配置（路径、标题、目录初始化，版本号读取）
│   ├── window.py            # 主窗口（侧边栏导航 + 页面管理）
│   ├── database.py          # SQLite 数据库操作（线程安全 + WAL + 连接池）
│   ├── content_service.py   # 课程内容加载与管理（延迟加载）
│   ├── practice_service.py  # 练习服务（兼容 shim，委托 app/practice/）
│   ├── python_runner.py     # 代码执行沙箱（AST 预检 + 受限内置函数）
│   ├── credentials.py       # 凭证安全存储（keyring + Windows Credential Manager）
│   ├── styles.py            # 全局样式定义
│   ├── ai/                  # AI 模块（从 ai_mentor.py 拆分）
│   │   ├── api_client.py    # AI API 通信（HTTPS 强制 + TLS 验证）
│   │   ├── chat_handler.py  # 对话 UI 组件（多会话管理）
│   │   ├── markdown_renderer.py  # Markdown 渲染 + HTML 净化（XSS 防护）
│   │   └── models.py        # 数据类和安全常量
│   ├── practice/            # 练习模块（从 practice_service.py 拆分）
│   │   ├── evaluator.py     # 代码评测逻辑（Python / SQL / C / C#）
│   │   ├── exercise_loader.py  # 练习数据加载（含外部 JSON 数据源）
│   │   ├── models.py        # Exercise / EvaluationResult 数据类
│   │   └── normalizer.py    # 结果集标准化
│   └── widgets/
│       ├── algo.py          # 算法可视化组件
│       ├── dashboard.py     # 学习仪表盘
│       ├── learn.py         # 学习路径页面
│       ├── practice.py      # 练习中心页面
│       └── projects.py      # 融合项目页面
├── tests/
│   ├── conftest.py          # pytest 共享 fixture
│   ├── test_python_runner*.py  # 沙箱安全边界测试（+subprocess +extended +extra）
│   ├── test_database*.py    # 数据库测试（+extended +extra +coverage +stress）
│   ├── test_practice_service*.py  # 评测逻辑测试（+extended +extra）
│   ├── test_ai_*.py         # AI 模块测试（chat_handler + package + api_client）
│   ├── test_content_service*.py  # 内容服务测试（+extended）
│   ├── test_credentials.py  # 凭证存储测试
│   ├── test_security_sandbox_escape.py  # 沙箱逃逸安全测试
│   ├── test_integration_*.py  # 集成测试（learning/practice/database/ai flow）
│   ├── test_edge_cases.py   # 边界条件测试
│   └── benchmark/           # 性能基准测试
├── content/
│   ├── python/              # Python 课程内容
│   ├── c/                   # C 语言课程内容
│   ├── csharp/              # C# 课程内容
│   ├── database/            # 数据库课程内容
│   ├── integration/         # 融合项目内容
│   ├── projects/            # 项目文档
│   └── metadata/
│       ├── course_map.json  # 课程元数据
│       └── exercises.json   # 练习元数据
├── codexgame/               # Codex 小游戏子项目
├── styles/                  # 样式资源
└── docs/                    # 开发文档
```

---

## 安全加固

本项目在安全方面进行了以下加固措施：

- **代码执行沙箱** -- 通过 AST 预检拦截危险代码，限制 `os.system`、`subprocess`、`eval`、`exec` 等危险内置函数的使用；禁止访问 `__class__`、`__bases__`、`__subclasses__` 等双下划线属性；限制可导入模块白名单
- **API 密钥安全存储** -- 使用 keyring 库将 API 密钥存储在 Windows Credential Manager 中，避免明文存储在配置文件；非 Windows 平台回退到 keyring 或 base64 编码文件
- **HTTPS 强制** -- AI API 通信强制使用 HTTPS，启用 TLS 证书验证，拒绝 HTTP 连接
- **数据库线程安全** -- 使用 SQLite WAL 模式配合写操作锁，确保多线程环境下数据一致性
- **HTML 输出净化** -- 对 Markdown 渲染后的 HTML 进行白名单净化处理，移除 `script`、`style`、`iframe` 等危险标签，过滤 `onclick` 等事件处理器和 `javascript:` URI，防止 XSS 注入
- **输出限制** -- 代码执行沙箱限制标准输出为 12KB，防止内存滥用
- **超时控制** -- 代码执行默认 3 秒超时，评测默认 4 秒超时

---

## 开发指南

### 环境搭建

```bash
# 克隆仓库
git clone <repo-url>
cd codelearnhleper

# 安装运行时 + 开发依赖
pip install -e ".[dev]"
# 或仅安装运行时依赖
pip install -r requirements.txt
```

### 代码检查与格式化

本项目使用 [Ruff](https://docs.astral.sh/ruff/) 统一完成 lint 和格式化（替代 flake8 + isort + black）。

```bash
# 检查代码风格
make lint
# 或直接调用
ruff check .

# 自动格式化
make format
# 或直接调用
ruff format .
ruff check --fix .
```

### 运行测试

```bash
# 运行全部测试
make test
# 或直接调用
pytest

# 运行测试并生成覆盖率报告
make coverage
```

### 提交规范

- 提交前请确保 `ruff check .` 和 `pytest` 均通过
- 提交信息建议使用中文，格式：`模块: 简要描述`，例如：
  - `database: 修复连续学习天数计算的边界条件`
  - `python_runner: 增加对 eval() 调用的拦截`

---

## 常见问题

### Q: 启动时报 "No module named 'PyQt5'"?

确保已安装 PyQt5：`pip install PyQt5>=5.15`。

### Q: AI 助手无法连接?

1. 检查 API Host 是否以 `https://` 开头（不支持 HTTP）
2. 确认 API Key 是否正确
3. 使用 AI 设置中的"测试连接"按钮验证
4. 检查网络连接和防火墙设置

### Q: 代码执行超时?

沙箱默认超时为 3 秒。如果代码需要更长时间，请检查是否存在死循环或大量计算。评测超时为 4 秒。

### Q: 如何添加新的课程内容?

1. 在 `content/` 目录对应技术栈子目录下添加 `.md` 文件
2. 在 `content/metadata/course_map.json` 中注册课程元数据
3. 在 `content/metadata/exercises.json` 中注册关联的练习
4. 运行 `python scripts/rebuild/rebuild_courses.py` 更新课程地图（如需要）

### Q: 如何切换 AI 模型?

在 AI 工作台或侧边助手中点击"AI 设置"，填写 API Host 和 Key 后点击"获取模型"，然后从下拉列表中选择模型。

### Q: 学习进度丢失了吗?

学习数据存储在 `%APPDATA%/DevLearnerAI/data/app.db` 中。如果遇到数据库损坏，应用会自动迁移旧版数据库。手动备份可复制该文件。

---

## 故障排除

### 应用启动失败

1. 确认 Python 版本 >= 3.9：`python --version`
2. 确认所有依赖已安装：`pip install -r requirements.txt`
3. 尝试使用开发模式启动查看日志：`python dev_main.py`

### 数据库问题

- 数据库路径：`%APPDATA%/DevLearnerAI/data/app.db`
- 旧版数据库会自动从 `db/learner.db` 迁移
- 如果数据库损坏，可删除 `app.db` 文件后重启应用（学习进度将丢失）

### AI 连接问题

- 确保 API 端点使用 HTTPS
- 检查 API Key 是否有效
- 确认所选模型存在于 API 端点
- 查看 `dev_main.py` 的 DEBUG 日志获取详细错误信息

### 代码执行问题

- Python 代码中不允许使用 `import` 语句（沙箱限制使用内置函数）
- 不允许访问双下划线属性（如 `__class__`、`__builtins__`）
- 文件操作限制在临时工作目录内
- 标准输出限制为 12KB

### PyInstaller 打包问题

- 确保使用 `scripts/build/build_dev_exe.py` 进行打包
- 打包产物在 `dist/` 目录
- 如果遇到缺少模块的问题，检查 `.spec` 文件中的 hidden imports

---

## 贡献

欢迎参与项目贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发环境搭建、分支策略、PR 流程和代码规范。

---

## 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

## 致谢

- Python 官方教程
- PyQt 文档
- SQLite 官方文档
- mistune Markdown 解析器
- Pygments 语法高亮库
