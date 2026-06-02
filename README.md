# DevLearnerAI

[![CI](https://github.com/TIANWEN-cpu/DevLearnerAI/actions/workflows/ci.yml/badge.svg)](https://github.com/TIANWEN-cpu/DevLearnerAI/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/TIANWEN-cpu/DevLearnerAI)](https://github.com/TIANWEN-cpu/DevLearnerAI/releases)
[![License](https://img.shields.io/github/license/TIANWEN-cpu/DevLearnerAI)](LICENSE)

**AI 驱动的桌面编程学习平台 | Python / PyQt5 / SQLite**

DevLearnerAI 是一款面向编程初学者和进阶学习者的桌面应用程序，集成了 AI 智能导师、代码执行沙箱、课程体系、交互式练习、算法可视化和学习仪表盘，将学习路径、练习、项目和 AI 助手整合到一个清晰的工作台中。

---

## 功能特性

- **AI 智能导师** -- 支持 OpenAI 兼容 API 的对话式编程辅导，可切换不同 API 端点和模型，附带上下文感知的知识库
- **代码执行沙箱** -- 安全执行 Python / C / C++ / C# / SQL 代码，通过 AST 预检和危险内置函数限制保障运行安全
- **课程体系** -- 涵盖 Python、C、C++、C#、数据库、算法、AI 等多个技术栈，课程内容以 Markdown 格式组织，支持语法高亮渲染
- **交互式练习** -- 编程练习与自动评测，配合练习中心进行针对性训练
- **融合项目** -- 从单点知识走向可交付的真实项目，培养工程实践能力
- **算法动画** -- 将抽象的算法步骤可视化，帮助理解排序、查找等经典算法
- **学习仪表盘** -- 学习进度追踪、课程完成统计、每日学习概览
- **Codex 账号切换器** -- 快速切换 Codex 账号配置

---

## 截图

<!-- 将截图放入 docs/ 目录，然后取消注释以下行 -->
<!-- 示例：
<p align="center">
  <img src="docs/screenshot-dashboard.png" alt="学习仪表盘" width="600">
  <img src="docs/screenshot-ai-mentor.png" alt="AI 导师" width="600">
  <img src="docs/screenshot-code-sandbox.png" alt="代码沙箱" width="600">
</p>
-->

> 将截图保存至 `docs/` 目录并更新上方引用即可展示

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

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3 |
| GUI 框架 | PyQt5 |
| 数据库 | SQLite（线程安全访问） |
| Markdown 渲染 | mistune |
| 语法高亮 | Pygments |
| AI 接口 | OpenAI 兼容 API（支持自定义端点） |
| 凭证管理 | keyring / Windows Credential Manager |
| 打包 | PyInstaller |

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
├── 项目说明.md              # 项目说明文档
├── app/
│   ├── __init__.py
│   ├── config.py            # 应用配置（路径、标题、目录初始化）
│   ├── window.py            # 主窗口（侧边栏导航 + 页面管理）
│   ├── ai_mentor.py         # AI 导师面板（对话、API 调用）
│   ├── content_service.py   # 课程内容加载与管理
│   ├── database.py          # SQLite 数据库操作（线程安全）
│   ├── practice_service.py  # 练习服务
│   ├── python_runner.py     # 代码执行沙箱（AST 预检 + 受限内置函数）
│   ├── styles.py            # 全局样式定义
│   └── widgets/
│       ├── algo.py          # 算法可视化组件
│       ├── dashboard.py     # 学习仪表盘
│       ├── learn.py         # 学习路径页面
│       ├── practice.py      # 练习中心页面
│       └── projects.py      # 融合项目页面
├── tests/
│   ├── conftest.py          # pytest 共享 fixture
│   ├── test_python_runner.py # 沙箱安全边界测试
│   ├── test_database.py     # 数据库 CRUD + 纯函数测试
│   └── test_practice_service.py # 评测逻辑测试
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
├── codexgame/               # Codex 小游戏子项目（独立 README）
├── styles/                  # 样式资源
└── docs/                    # 开发文档
```

---

## 安全加固

本项目在安全方面进行了以下加固措施：

- **代码执行沙箱** -- 通过 AST 预检拦截危险代码，限制 `os.system`、`subprocess`、`eval`、`exec` 等危险内置函数的使用
- **API 密钥安全存储** -- 使用 keyring 库将 API 密钥存储在 Windows Credential Manager 中，避免明文存储在配置文件
- **HTTPS 强制** -- AI API 通信强制使用 HTTPS，启用 TLS 证书验证
- **数据库线程安全** -- 使用 SQLite WAL 模式配合写操作锁，确保多线程环境下数据一致性
- **HTML 输出净化** -- 对 Markdown 渲染后的 HTML 进行净化处理，防止 XSS 注入

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
