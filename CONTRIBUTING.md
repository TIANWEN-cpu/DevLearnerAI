# 贡献指南

感谢你对 DevLearnerAI 项目的关注！本文档将帮助你快速上手开发流程。

---

## 开发环境搭建

### 前置条件

- Python 3.9 或更高版本（推荐 3.12）
- Git
- Windows 系统（部分功能依赖 Windows Credential Manager）

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

---

## 分支策略

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `main` | 稳定发布分支 | 需 PR + CI 通过 |
| `feature/*` | 新功能开发 | 从 main 切出 |
| `fix/*` | Bug 修复 | 从 main 切出 |
| `docs/*` | 文档更新 | 从 main 切出 |

**命名示例**: `feature/add-dark-theme`, `fix/sql-eval-crash`, `docs/update-readme`

---

## 开发工作流

### 1. 创建分支

```bash
git checkout main
git pull origin main
git checkout -b feature/你的功能名
```

### 2. 开发

- 编写代码，遵循项目编码规范
- 为新增功能添加测试（`tests/` 目录）
- 确保测试通过：`make test`

### 3. 提交

```bash
git add .
git commit -m "feat: 简洁描述你的改动"
```

**提交信息格式**（遵循 Conventional Commits）:

```
<类型>: <简要描述>

<可选正文>

<可选脚注>
```

常用类型：`feat`（新功能）、`fix`（修复）、`docs`（文档）、`refactor`（重构）、`test`（测试）、`chore`（杂务）

### 4. 推送并创建 PR

```bash
git push origin feature/你的功能名
```

然后在 GitHub 上创建 Pull Request，填写 PR 模板中的说明。

---

## 代码规范

### 工具链

本项目使用 [Ruff](https://github.com/astral-sh/ruff) 作为 linter + formatter，配置详见 `pyproject.toml`。

```bash
# 检查代码风格
ruff check .

# 自动修复
ruff check --fix .

# 格式化
ruff format .
```

### 关键规则

- **行宽**: 120 字符
- **引号**: 双引号
- **缩进**: 4 空格
- **import 排序**: isort 规则（Ruff 内置）
- **命名**: 遵循 PEP 8，PyQt5 方法允许 camelCase（如 `mousePressEvent`）

### 类型注解

- 公开函数应添加参数和返回值类型注解
- 复杂数据结构优先使用 `dataclass` 或 `TypedDict`

---

## 测试

### 运行测试

```bash
pytest                    # 运行所有测试
pytest -v                 # 详细输出
pytest tests/test_xxx.py  # 运行指定文件
```

### 覆盖率

```bash
coverage run -m pytest
coverage report            # 终端报告
coverage html              # HTML 报告（生成 htmlcov/ 目录）
```

### 编写测试

- 测试文件放在 `tests/` 目录，命名为 `test_*.py`
- 使用 `pytest` 的 `assert` 风格（非 `unittest`）
- 测试类以 `Test` 开头，测试函数以 `test_` 开头
- 使用 `conftest.py` 中的 fixtures 共享测试夹具

---

## Pull Request 规范

### 提交前检查清单

- [ ] 代码通过 `ruff check` 和 `ruff format --check`
- [ ] 所有测试通过 `pytest`
- [ ] 新增功能有对应测试
- [ ] 提交信息遵循 Conventional Commits 格式

### PR 描述模板

请在 PR 描述中说明：

1. **做了什么**: 改动的简要概述
2. **为什么做**: 改动的动机或修复的 Issue
3. **怎么验证**: 如何确认改动正确工作

---

## 项目结构概览

```
D:\codelearnhleper\
├── main.py                  # 生产环境入口
├── dev_main.py              # 开发环境入口（DEBUG 日志）
├── app/                     # 应用核心代码
│   ├── ai/                  # AI 导师模块
│   ├── widgets/             # UI 组件（dashboard, learn, practice, ...）
│   ├── config.py            # 全局配置
│   ├── database.py          # SQLite 数据库层
│   ├── content_service.py   # 课程内容加载
│   ├── practice_service.py  # 练习评测逻辑
│   └── styles.py            # 全局样式
├── content/                 # 课程内容（Markdown + JSON 元数据）
├── scripts/                 # 构建与数据重建脚本
│   ├── build/               # PyInstaller 打包
│   └── rebuild/             # 课程数据重建
├── tests/                   # 测试套件
├── docs/                    # 项目文档
├── pyproject.toml           # 项目元数据 + 工具配置
├── Makefile                 # 常用开发命令
└── requirements.txt         # 运行时依赖
```

---

## 常见问题

### Q: 测试运行报 "No module named 'PyQt5'"?

确保已安装 PyQt5：`pip install PyQt5>=5.15`

### Q: 如何在没有 GUI 的环境下运行测试?

部分 widget 测试需要 PyQt5，但核心逻辑测试（database, practice_service, content_service 等）可以在无 GUI 环境下运行。

### Q: 如何添加新的课程内容?

1. 在 `content/` 目录对应技术栈子目录下添加 `.md` 文件
2. 在 `content/metadata/exercises.json` 中注册关联的练习
3. 运行 `python scripts/rebuild/rebuild_courses.py` 更新课程地图（如需要）

---

如有其他问题，请在 [Issues](https://github.com/TIANWEN-cpu/DevLearnerAI/issues) 中提问。
