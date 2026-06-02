# 贡献指南

感谢你对 DevLearner AI 项目的关注！本文档将帮助你快速上手开发流程。

---

## 目录

- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [分支策略](#分支策略)
- [Pull Request 流程](#pull-request-流程)
- [提交规范](#提交规范)
- [常见开发任务](#常见开发任务)

---

## 开发环境搭建

### 前置条件

- Python 3.9 或更高版本（推荐 3.12）
- Git
- Windows 系统（推荐；其他平台部分功能受限）

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

使用 [Ruff](https://github.com/astral-sh/ruff) 统一完成 lint 和格式化。

```bash
# 检查代码风格
ruff check .

# 自动修复
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
| 命名 | 遵循 PEP 8；PyQt5 方法允许 camelCase |
| 类型注解 | 公开函数应添加参数和返回值类型注解 |
| 数据结构 | 复杂数据结构优先使用 `dataclass` 或 `TypedDict` |

### 项目特殊约定

- PyQt5 信号名称使用 camelCase（如 `navigate_requested`、`response_ready`）
- 安全相关代码优先考虑显式分支而非简化写法
- 测试文件放在 `tests/` 目录，命名为 `test_*.py`
- 使用 `pytest` 的 `assert` 风格（不要使用 `unittest.TestCase`）

---

## 分支策略

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `main` | 稳定发布分支 | 需 PR + CI 通过 |
| `feature/*` | 新功能开发 | 从 main 切出 |
| `fix/*` | Bug 修复 | 从 main 切出 |
| `docs/*` | 文档更新 | 从 main 切出 |
| `refactor/*` | 代码重构 | 从 main 切出 |

**命名示例**：
- `feature/add-dark-theme`
- `fix/sql-eval-crash`
- `docs/update-user-guide`
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

### 提交前检查清单

- [ ] 代码通过 `ruff check` 和 `ruff format --check`
- [ ] 所有测试通过 `pytest`
- [ ] 新增功能有对应测试
- [ ] 提交信息遵循 Conventional Commits 格式
- [ ] 没有提交敏感信息（.env、凭证文件等）
- [ ] PR 描述清晰说明了改动内容和原因

### PR 描述要求

1. **做了什么** -- 改动的简要概述
2. **为什么做** -- 改动的动机或修复的 Issue 编号
3. **怎么验证** -- 如何确认改动正确工作
4. **影响范围** -- 涉及哪些模块，是否需要迁移

---

## 提交规范

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

## 常见开发任务

### 添加新的课程内容

1. 在 `content/<技术栈>/` 下添加 `.md` 文件
2. 在 `content/metadata/course_map.json` 中注册
3. 在 `content/metadata/exercises.json` 中注册关联练习（如适用）
4. 运行 `python scripts/rebuild/rebuild_courses.py` 更新课程地图

### 添加新的练习

1. 在 `content/metadata/exercises.json` 中添加练习定义
2. 准备测试数据（SQL fixture 或 expected_output）
3. 如需特殊评测逻辑，修改 `app/practice/evaluator.py`

### 添加新的 Widget 页面

1. 在 `app/widgets/` 下创建新的 Widget 文件
2. 在 `app/window.py` 中注册到 `QStackedWidget`
3. 在侧边栏添加导航入口

### 调试 AI 导师功能

1. 使用 `python dev_main.py` 启动（启用 DEBUG 日志）
2. 在 AI 设置中配置 API Host 和 Key
3. 使用"测试连接"按钮验证
4. 检查控制台日志输出

### 打包为可执行文件

```bash
pip install pyinstaller
python scripts/build/build_dev_exe.py
```

打包产物输出到 `dist/` 目录。

---

> 如有其他问题，请在 [Issues](https://github.com/TIANWEN-cpu/DevLearnerAI/issues) 中提问。
