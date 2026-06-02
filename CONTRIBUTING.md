# DevLearnerAI 贡献指南

感谢你对 DevLearnerAI 项目的关注！本文档将帮助你快速上手开发流程，了解代码规范和提交要求。

---

## 目录

- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [分支策略](#分支策略)
- [Pull Request 流程](#pull-request-流程)
- [测试要求](#测试要求)
- [提交规范](#提交规范)
- [项目结构概览](#项目结构概览)
- [常见问题](#常见问题)

---

## 开发环境搭建

### 前置条件

- Python 3.9 或更高版本（推荐 3.12）
- Git
- Windows 系统（部分功能依赖 Windows Credential Manager；其他平台可使用 keyring 后端）

### 初始化步骤

```bash
# 1. 克隆仓库
git clone https://github.com/TIANWEN-cpu/DevLearnerAI.git
cd DevLearnerAI

# 2. 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

# 3. 安装运行时 + 开发依赖
pip install -e ".[dev]"

# 4. 安装 pre-commit hooks（可选但推荐）
pip install pre-commit
pre-commit install
```

### 验证环境

```bash
make lint        # 代码风格检查
make test        # 运行测试
make coverage    # 运行测试 + 覆盖率报告
```

### 常用开发命令

| 命令 | 说明 |
|------|------|
| `make lint` | 运行 Ruff 代码风格检查 |
| `make format` | 自动格式化代码 |
| `make test` | 运行全部测试 |
| `make coverage` | 运行测试并生成覆盖率报告 |
| `make clean` | 清理临时文件和缓存 |
| `make install-dev` | 安装开发依赖 |
| `python main.py` | 启动生产环境 |
| `python dev_main.py` | 启动开发环境（DEBUG 日志） |

---

## 代码规范

### 工具链

本项目使用 [Ruff](https://github.com/astral-sh/ruff) 作为 linter + formatter，替代 flake8 + isort + black 的组合。配置详见 `pyproject.toml`。

```bash
# 检查代码风格
ruff check .

# 自动修复可修复的问题
ruff check --fix .

# 格式化代码
ruff format .
```

### 关键规则

| 规则 | 约定 |
|------|------|
| 行宽 | 120 字符 |
| 引号 | 双引号 |
| 缩进 | 4 空格 |
| import 排序 | isort 规则（Ruff 内置） |
| 命名 | 遵循 PEP 8；PyQt5 方法允许 camelCase（如 `mousePressEvent`） |
| 类型注解 | 公开函数应添加参数和返回值类型注解 |
| 数据结构 | 复杂数据结构优先使用 `dataclass` 或 `TypedDict` |

### 项目特殊约定

- PyQt5 信号名称使用 camelCase（如 `navigate_requested`、`response_ready`）
- Win32 API 结构体名称允许大写开头（如 `CREDENTIALW`、`DATA_BLOB`）
- 安全相关代码（沙箱、凭证管理）优先考虑显式分支而非简化写法

---

## 分支策略

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `main` | 稳定发布分支 | 需 PR + CI 通过 |
| `feature/*` | 新功能开发 | 从 main 切出 |
| `fix/*` | Bug 修复 | 从 main 切出 |
| `docs/*` | 文档更新 | 从 main 切出 |
| `refactor/*` | 代码重构 | 从 main 切出 |

**命名示例**:

- `feature/add-dark-theme`
- `fix/sql-eval-crash`
- `docs/update-readme`
- `refactor/extract-ai-module`

---

## Pull Request 流程

### 1. 创建分支

```bash
git checkout main
git pull origin main
git checkout -b feature/你的功能名
```

### 2. 开发与提交

- 编写代码，遵循项目编码规范
- 为新增功能添加测试（`tests/` 目录）
- 提交前确保通过检查：

```bash
make lint && make test
```

### 3. 推送并创建 PR

```bash
git push origin feature/你的功能名
```

然后在 GitHub 上创建 Pull Request，使用提供的 PR 模板填写说明。

### 提交前检查清单

- [ ] 代码通过 `ruff check` 和 `ruff format --check`
- [ ] 所有测试通过 `pytest`
- [ ] 新增功能有对应测试
- [ ] 提交信息遵循 Conventional Commits 格式
- [ ] 没有提交敏感信息（.env、凭证文件等）
- [ ] PR 描述清晰说明了改动内容和原因

### PR 描述要求

请在 PR 描述中说明：

1. **做了什么**: 改动的简要概述
2. **为什么做**: 改动的动机或修复的 Issue 编号
3. **怎么验证**: 如何确认改动正确工作
4. **影响范围**: 涉及哪些模块，是否需要迁移

---

## 测试要求

### 运行测试

```bash
pytest                    # 运行所有测试
pytest -v                 # 详细输出
pytest tests/test_xxx.py  # 运行指定文件
pytest -k "test_name"     # 运行匹配的测试
```

### 覆盖率

```bash
coverage run -m pytest
coverage report            # 终端报告
coverage html              # HTML 报告（生成 htmlcov/ 目录）
```

### 编写测试的规范

- 测试文件放在 `tests/` 目录，命名为 `test_*.py`
- 使用 `pytest` 的 `assert` 风格（不要使用 `unittest.TestCase`）
- 测试类以 `Test` 开头，测试函数以 `test_` 开头
- 使用 `conftest.py` 中的 fixtures 共享测试夹具
- 核心逻辑测试（database、practice_service、content_service 等）应在无 GUI 环境下可运行
- Widget 测试可能需要 PyQt5 环境

### 测试分类

| 模块 | 测试重点 |
|------|----------|
| `database.py` | CRUD 操作、线程安全、边界条件 |
| `python_runner.py` | 沙箱安全边界、危险代码拦截 |
| `practice_service.py` | 评测逻辑正确性、各语言评测分支 |
| `content_service.py` | 课程加载、缓存、损坏数据处理 |
| `credentials.py` | 密钥存储与读取、平台回退逻辑 |
| `ai/api_client.py` | HTTPS 强制、URL 构建、错误处理 |

---

## 提交规范

### 提交信息格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<类型>: <简要描述>

<可选正文>

<可选脚注>
```

### 常用类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加 C++ 课程支持` |
| `fix` | 修复 | `fix: 修复 SQL 评测结果不一致` |
| `docs` | 文档 | `docs: 更新安装说明` |
| `refactor` | 重构 | `refactor: 提取 AI 子模块` |
| `test` | 测试 | `test: 增加沙箱安全边界用例` |
| `chore` | 杂务 | `chore: 升级 PyQt5 依赖版本` |
| `perf` | 性能 | `perf: 优化课程列表懒加载` |
| `style` | 格式 | `style: 统一引号风格` |

### 示例

```
database: 修复连续学习天数计算的边界条件

当用户今天没有学习记录时，streak 应返回 0 而非上一次的累计值。

Fixes #42
```

---

## 项目结构概览

```
D:\codelearnhleper\
├── main.py                  # 生产环境入口
├── dev_main.py              # 开发环境入口（DEBUG 日志）
├── pyproject.toml           # 项目元数据 + Ruff/pytest/coverage 配置
├── Makefile                 # 常用开发命令
├── requirements.txt         # 运行时依赖（最小集）
├── app/                     # 应用核心代码
│   ├── config.py            # 全局配置（路径、版本、目录初始化）
│   ├── window.py            # 主窗口（侧边栏导航 + 页面管理）
│   ├── database.py          # SQLite 数据库层（线程安全）
│   ├── content_service.py   # 课程内容加载与管理
│   ├── practice_service.py  # 练习服务（兼容 shim，委托到 practice/）
│   ├── python_runner.py     # 代码执行沙箱（AST 预检 + 受限内置函数）
│   ├── credentials.py       # 凭证安全存储（Windows Credential Manager / keyring）
│   ├── styles.py            # 全局样式定义
│   ├── ai/                  # AI 导师子模块
│   │   ├── api_client.py    # API 通信（HTTPS、SSL、URL 构建）
│   │   ├── chat_handler.py  # 对话 UI（AIMentorPanel、AIMentorDock）
│   │   ├── markdown_renderer.py  # Markdown 渲染 + HTML 净化
│   │   └── models.py        # 数据类和安全常量
│   ├── practice/            # 练习子模块
│   │   ├── evaluator.py     # 评测逻辑（SQL、关键字、Python）
│   │   ├── exercise_loader.py  # 练习数据加载与回退
│   │   ├── models.py        # Exercise / EvaluationResult 数据类
│   │   └── normalizer.py    # 结果集标准化
│   └── widgets/             # UI 组件
│       ├── dashboard.py     # 学习仪表盘
│       ├── learn.py         # 学习路径页面
│       ├── practice.py      # 练习中心页面
│       ├── projects.py      # 融合项目页面
│       └── algo.py          # 算法可视化组件
├── content/                 # 课程内容（Markdown + JSON 元数据）
├── tests/                   # 测试套件
├── scripts/                 # 构建与数据重建脚本
└── docs/                    # 项目文档
```

---

## 常见问题

### Q: 测试运行报 "No module named 'PyQt5'"?

确保已安装 PyQt5：`pip install PyQt5>=5.15`。如果在无 GUI 的 CI 环境中，可能需要额外安装 Qt 的无头依赖。

### Q: 如何在没有 GUI 的环境下运行测试?

核心逻辑测试（database、practice_service、content_service、python_runner、credentials 等）可以在无 GUI 环境下运行。Widget 测试需要 PyQt5 环境。覆盖率配置已排除 widget 模块。

### Q: 如何添加新的课程内容?

1. 在 `content/` 目录对应技术栈子目录下添加 `.md` 文件
2. 在 `content/metadata/course_map.json` 中注册课程元数据
3. 在 `content/metadata/exercises.json` 中注册关联的练习（如适用）
4. 运行 `python scripts/rebuild/rebuild_courses.py` 更新课程地图（如需要）

### Q: 如何添加新的练习?

1. 在 `content/metadata/exercises.json` 中添加练习定义
2. 根据练习类型，在 `content/metadata/` 中添加对应的 fixture 文件
3. 如需特殊评测逻辑，在 `app/practice/evaluator.py` 中添加对应分支

### Q: Ruff 报错但不知道怎么修?

运行 `ruff check --fix .` 尝试自动修复。对于无法自动修复的问题，参考 [Ruff 文档](https://docs.astral.sh/ruff/) 了解具体规则说明。

### Q: 如何调试 AI 导师功能?

1. 在 `AI 设置` 中配置 API Host 和 Key
2. 确保使用 HTTPS 端点
3. 使用 `测试连接` 按钮验证配置
4. 检查日志输出（`dev_main.py` 会启用 DEBUG 级别日志）

### Q: 如何打包为可执行文件?

```bash
pip install pyinstaller
python scripts/build/build_dev_exe.py
```

打包产物将输出到 `dist/` 目录。

---

如有其他问题，请在 [Issues](https://github.com/TIANWEN-cpu/DevLearnerAI/issues) 中提问。
