# 第一周上手指南

欢迎加入 DevLearnerAI 开发团队！本指南将帮助你在第一周内完成环境搭建、熟悉代码库、提交第一个 PR。

---

## 目录

- [环境搭建](#环境搭建)
- [代码库导览](#代码库导览)
- [第一个 PR 流程](#第一个-pr-流程)
- [第一周任务清单](#第一周任务清单)

---

## 环境搭建

### 1. 前置条件

| 工具 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.9+ | 推荐 3.12，项目 CI 矩阵覆盖 3.9 和 3.12 |
| Git | 任意近期版本 | 用于版本管理和协作 |
| 操作系统 | Windows 10+ | 推荐，部分功能依赖 Windows Credential Manager |
| 编辑器 | VS Code / PyCharm | 推荐 VS Code + Ruff 扩展 |

### 2. 克隆仓库

```bash
git clone https://github.com/TIANWEN-cpu/DevLearnerAI.git
cd DevLearnerAI
```

### 3. 创建虚拟环境

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
# source .venv/bin/activate   # Linux / macOS
```

### 4. 安装依赖

```bash
# 安装运行时 + 开发依赖（推荐）
pip install -e ".[dev]"

# 或仅安装运行时依赖
pip install -r requirements.txt
```

开发依赖包括：`pytest`、`ruff`、`coverage`、`pyinstaller`、`pytest-benchmark`。

### 5. 验证环境

```bash
# 检查代码风格
make lint

# 运行测试（1000+ 条用例）
make test

# 运行测试 + 覆盖率报告
make coverage
```

三条命令均无报错即表示环境正常。

### 6. 启动应用

```bash
# 生产模式
python main.py

# 开发模式（DEBUG 日志，便于排查问题）
python dev_main.py
```

应用启动后应看到主窗口，包含侧边栏导航和学习仪表盘。

### 7. 常用开发命令速查

| 命令 | 说明 |
|------|------|
| `make lint` | 运行 Ruff 代码风格检查 |
| `make format` | 自动格式化代码 |
| `make test` | 运行全部测试 |
| `make coverage` | 运行测试并生成覆盖率报告 |
| `make bench` | 运行性能基准测试 |
| `make clean` | 清理 `__pycache__`、`.pytest_cache` 等临时文件 |
| `make build-release` | 打包正式发布版 |
| `make build-dev` | 打包开发调试版 |
| `make verify-build` | 验证构建配置（dry-run） |
| `python dev_main.py` | 开发模式启动应用 |

---

## 代码库导览

### 顶层目录结构

```text
D:\codelearnhleper\
├── main.py                  # 生产环境入口
├── dev_main.py              # 开发环境入口（DEBUG 日志）
├── pyproject.toml           # 项目元数据 + Ruff / pytest / coverage 配置
├── Makefile                 # 常用开发命令
├── requirements.txt         # 运行时依赖（最小集）
├── requirements-dev.txt     # 开发依赖
├── app/                     # 应用核心代码（详见下文）
├── content/                 # 课程内容（Markdown + JSON 元数据）
├── tests/                   # 测试套件（1000+ 条用例）
├── scripts/                 # 构建与数据重建脚本
├── styles/                  # 样式资源
├── docs/                    # 项目文档
└── codexgame/               # Codex 账号切换器子项目
```

### 核心代码目录 `app/`

```text
app/
├── __init__.py
├── config.py            # 全局配置（路径、版本号、目录初始化）
├── window.py            # 主窗口 -- 侧边栏导航 + QStackedWidget 页面管理
├── database.py          # SQLite 数据库层（WAL 模式 + 线程安全 + 写锁）
├── content_service.py   # 课程内容加载（Track > Module > Lesson 三级模型）
├── practice_service.py  # 练习服务（兼容 shim，委托到 app/practice/ 子包）
├── python_runner.py     # 代码执行沙箱（AST 预检 + 受限内置函数）
├── credentials.py       # 凭证安全存储（keyring + Windows Credential Manager）
├── styles.py            # 全局样式定义
├── effects.py           # UI 动画效果（阴影、透明度）
├── ai/                  # AI 导师子模块
│   ├── api_client.py    # API 通信（HTTPS 强制 + TLS 验证）
│   ├── chat_handler.py  # 对话 UI 组件（多会话管理）
│   ├── markdown_renderer.py  # Markdown 渲染 + HTML 净化（XSS 防护）
│   └── models.py        # 数据类和安全常量
├── practice/            # 练习子模块
│   ├── evaluator.py     # 评测逻辑（Python / SQL / C / C#）
│   ├── exercise_loader.py  # 练习数据加载（含外部 JSON 数据源）
│   ├── models.py        # Exercise / EvaluationResult 数据类
│   └── normalizer.py    # 结果集标准化
├── widgets/             # UI 组件
│   ├── dashboard.py     # 学习仪表盘（进度追踪、统计图表）
│   ├── learn.py         # 学习路径页面（课程浏览、Markdown 渲染）
│   ├── practice.py      # 练习中心（代码编辑、评测反馈）
│   ├── projects.py      # 融合项目页面
│   ├── algo.py          # 算法可视化组件
│   ├── achievements.py  # 成就系统
│   ├── bookmarks.py     # 书签功能
│   ├── learning_path.py # 学习路径推荐
│   └── export_import.py # 数据导出导入
├── services/            # 服务层
│   ├── base.py          # 基础服务类
│   ├── lesson_service.py    # 课程服务
│   ├── practice_data_service.py  # 练习数据服务
│   ├── achievement_service.py    # 成就服务
│   ├── bookmark_service.py       # 书签服务
│   ├── note_service.py           # 笔记服务
│   ├── review_service.py         # 复习调度服务
│   ├── config_service.py         # 配置服务
│   └── mentor_service.py         # AI 导师服务
└── utils/               # 工具模块
    ├── container.py     # 依赖注入容器
    ├── events.py        # 事件总线（跨组件通信）
    ├── middleware.py     # 中间件模式
    ├── error_handler.py # 错误处理工具
    └── plugins.py       # 插件架构
```

### 课程内容目录 `content/`

```text
content/
├── python/              # Python 课程 Markdown 文件
├── c/                   # C 语言课程
├── cpp/                 # C++ 课程
├── csharp/              # C# 课程
├── database/            # 数据库课程
├── algorithms/          # 算法课程
├── integration/         # 融合项目内容
├── projects/            # 项目文档
├── stage1/ ~ stage6/    # 分阶段课程内容
└── metadata/
    ├── course_map.json  # 课程元数据（Track > Module > Lesson 结构定义）
    └── exercises.json   # 练习元数据（题目定义、评测规则）
```

### 关键数据流（速记）

| 流程 | 入口 | 核心模块 | 存储 |
|------|------|----------|------|
| 课程加载 | `LearnWidget` | `ContentService` | `course_map.json` + `content/*.md` |
| AI 对话 | `AIMentorPanel` | `api_client` + `chat_handler` | `mentor_sessions` / `mentor_messages` 表 |
| 练习评测 | `PracticeWidget` | `evaluator` + `python_runner` | `practice_attempts` / `exercise_drafts` 表 |
| 学习进度 | `DashboardWidget` | `AppDatabase` | `lesson_progress` 表 |

### 入口文件执行顺序

1. `main.py` -- 配置日志（RotatingFileHandler）、调用 `ensure_runtime_dirs()`
2. `app.config` -- 初始化路径常量（`CONTENT_DIR`、`DB_PATH`、`LOG_DIR` 等）
3. `app.window.DevLearnerWindow.__init__()` -- 创建数据库、内容服务、练习服务、所有 Widget
4. `app.window.run()` -- 启动 `QApplication` 事件循环

---

## 第一个 PR 流程

### 步骤 1：创建分支

```bash
git checkout main
git pull origin main
git checkout -b fix/你的修复名
# 或
git checkout -b feature/你的功能名
```

分支命名规范：
- `feature/<功能名>` -- 新功能
- `fix/<问题名>` -- Bug 修复
- `docs/<文档名>` -- 文档更新
- `refactor/<重构名>` -- 代码重构

### 步骤 2：开发与测试

建议第一个 PR 选择以下入门任务之一：

- 修复文档中的错别字或过时信息
- 为某个模块补充一个缺失的测试用例
- 为 `exercises.json` 中添加一道新的练习题

开发过程中频繁运行：

```bash
make lint    # 检查代码风格
make test    # 运行测试
```

### 步骤 3：提交代码

```bash
git add <修改的文件>
git commit -m "fix: 修复某个具体问题的描述"
```

提交信息格式：`<类型>: <简要描述>`，常用类型包括 `feat`、`fix`、`docs`、`test`、`refactor`、`chore`。

### 步骤 4：推送并创建 PR

```bash
git push origin fix/你的修复名
```

在 GitHub 上创建 Pull Request，PR 描述需包含：

1. **做了什么** -- 改动的简要概述
2. **为什么做** -- 改动的动机或修复的 Issue 编号
3. **怎么验证** -- 如何确认改动正确工作
4. **影响范围** -- 涉及哪些模块

### 步骤 5：代码审查

- CI 自动运行 lint + 测试，确保全部通过
- 等待至少一位团队成员审查
- 根据反馈修改后再次推送

### 提交前检查清单

- [ ] `ruff check .` 无报错
- [ ] `ruff format --check .` 无格式差异
- [ ] `pytest` 全部通过
- [ ] 新增功能有对应测试
- [ ] 提交信息遵循 Conventional Commits 格式
- [ ] 未提交敏感信息（`.env`、凭证文件、API Key）

---

## 第一周任务清单

| 天数 | 任务 | 预计耗时 |
|------|------|----------|
| 第 1 天 | 完成环境搭建，启动应用并浏览各页面 | 2 小时 |
| 第 2 天 | 阅读代码库导览，通读 `main.py` -> `config.py` -> `window.py` 启动链路 | 3 小时 |
| 第 3 天 | 通读 `content_service.py` 和 `database.py`，理解数据模型 | 3 小时 |
| 第 4 天 | 阅读测试文件（`conftest.py` + 任一 `test_*.py`），运行测试套件 | 2 小时 |
| 第 5 天 | 完成第一个 PR（修复文档 / 补充测试 / 添加练习题） | 3 小时 |

### 推荐阅读顺序

1. `README.md` -- 项目全貌
2. `CONTRIBUTING.md` -- 贡献规范
3. `main.py` + `dev_main.py` -- 应用启动入口
4. `app/config.py` -- 配置常量定义
5. `app/window.py` -- 主窗口和 Widget 组装
6. `app/database.py` -- 数据库层
7. `app/content_service.py` -- 课程内容加载
8. `app/practice/evaluator.py` -- 练习评测逻辑
9. `app/ai/api_client.py` -- AI API 通信
10. `tests/conftest.py` -- 测试基础设施
