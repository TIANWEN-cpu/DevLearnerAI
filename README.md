<p align="center">
  <h1 align="center">DevLearner AI</h1>
  <p align="center"><strong>AI 驱动的桌面编程学习平台</strong></p>
  <p align="center">一个工作台，搞定 8 条技术路线、130 个课时、176 道练习和 AI 实时辅导。</p>
</p>

<p align="center">
  <a href="https://github.com/TIANWEN-cpu/DevLearnerAI/actions/workflows/ci.yml"><img src="https://github.com/TIANWEN-cpu/DevLearnerAI/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/TIANWEN-cpu/DevLearnerAI/releases"><img src="https://img.shields.io/github/v/release/TIANWEN-cpu/DevLearnerAI" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/TIANWEN-cpu/DevLearnerAI" alt="License"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/tests-1334-passing-brightgreen" alt="Tests"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/coverage-40%25%2B-yellowgreen" alt="Coverage"></a>
</p>

<p align="center">
  <strong>Python</strong> / <strong>C</strong> / <strong>C++</strong> / <strong>C#</strong> / <strong>SQL</strong> / <strong>数据库</strong> / <strong>算法</strong> / <strong>融合项目</strong>
</p>

---

## 为什么选择 DevLearner AI

学编程最大的痛点不是缺少教程，而是**看完不会写、卡住没人帮、知识是碎片的**。

DevLearner AI 把课程阅读、动手练习、代码执行、AI 辅导和项目实战整合到一个桌面工作台中。学完一个知识点，马上做练习；做练习卡住，马上问 AI。学习流不中断。

> **课程 + 练习 + 沙箱 + AI + 项目 = 一个应用**

---

## 功能亮点

### AI 智能导师

AI 导师知道你正在学哪门课、做到哪道题。不是通用聊天机器人，而是上下文感知的编程辅导。

- 多会话管理：按主题拆分对话
- 快捷提问：解释当前课程 / 分析当前代码 / 拆解当前项目
- AI 工作台 + 侧边助手双模式
- 支持 OpenAI 兼容 API，可切换端点和模型

### 代码执行沙箱

在安全的沙箱中运行代码，5 层防护让你放心练。

- Python 实际运行 + AST 预检拦截危险代码
- C / C++ / C# 结构检查评测
- SQL 真实数据库查询验证
- 文件隔离 + 输出限制 + 超时控制

### 沉浸式课程体系

130 个课时，从零基础到工程实战。

| 路线 | 覆盖内容 |
|:---|:---|
| Python | 语法 / 数据结构 / OOP / 异步 / 测试 / 工程化 |
| C | 数据类型 / 指针 / 内存管理 / 链表 / 文件 |
| C++ | STL / 类 / RAII / 智能指针 / 迭代器 |
| C# | OOP / LINQ / 委托 / Web API / 文件持久化 |
| 数据库 | SQL / 索引 / 事务 / 窗口函数 / 查询优化 |
| 算法 | 复杂度 / 排序 / 查找 / 动态规划 / 图算法 |
| 融合项目 | 跨语言综合项目，培养工程能力 |
| 实战项目 | 10 个真实项目，从 Todo CLI 到 AI 对话助理 |

### 交互式练习

176 道精选练习题，覆盖全部 8 条技术路线。

- 自动评测：运行结果 + 语法检查 + 结构检查 + 测试用例通过率
- 按技术栈和难度筛选
- 草稿自动保存，中途退出不丢失
- 练习历史记录持久化

### 学习仪表盘和算法可视化

- 学习进度追踪、课程完成统计、每日学习概览、连续学习天数
- 练习平均分展示
- 交互式算法动画，看见排序和查找的每一步

---

## 截图

<p align="center">
  <em>截图待补充 -- 欢迎提 PR 添加实际运行截图</em>
</p>

| 界面 | 说明 |
|:---|:---|
| ![首页仪表板](screenshots/dashboard.png) | 学习仪表盘：进度追踪、目标统计、成绩图表 |
| ![课程阅读器](screenshots/course-reader.png) | 课程阅读器：Markdown 渲染、代码高亮、目录导航 |
| ![练习中心](screenshots/practice.png) | 练习中心：题目列表、代码编辑、自动判题 |
| ![AI 辅导](screenshots/ai-chat.png) | AI 工作台：实时对话、代码解释、学习建议 |
| ![学习路径](screenshots/learning-path.png) | 学习路径：路线选择、进度追踪 |
| ![融合项目](screenshots/integration.png) | 融合项目：跨语言综合项目 |

---

## 快速开始

### 环境要求

- Python 3.9+
- Windows（推荐，部分功能依赖 Windows Credential Manager）

### 三步启动

```bash
# 1. 克隆仓库
git clone https://github.com/TIANWEN-cpu/DevLearnerAI.git
cd DevLearnerAI

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
python main.py
```

开发模式（启用 DEBUG 日志）：

```bash
python dev_main.py
```

打包为可执行文件：

```bash
pip install pyinstaller
python scripts/build/build_dev_exe.py
```

---

## 同类产品对比

| 特性 | **DevLearner AI** | Duolingo | freeCodeCamp | LeetCode | CS50 |
|:---|:---:|:---:|:---:|:---:|:---:|
| AI 智能辅导 | **内置** | 语言纠错 | -- | -- | -- |
| 代码执行沙箱 | **内置** | -- | 浏览器 | 浏览器 | 本地 IDE |
| 多语言路线 | **8 条** | -- | Web 为主 | 多语言 | C/Python/SQL |
| 练习 + 自动判题 | **176 道** | -- | 项目驱动 | 3000+ | ~10 集 |
| 实战项目 | **10 个** | -- | 5 个认证 | -- | 5 个 |
| 融合项目（跨语言） | **有** | -- | -- | -- | -- |
| 离线使用 | **完全支持** | 有限 | -- | -- | 有限 |
| 开源免费 | **MIT** | 闭源 | 开源 | 闭源 | 部分开源 |

> 详细对比请参阅 [docs/comparison.md](docs/comparison.md)

---

## 技术栈

| 类别 | 技术 |
|:---|:---|
| 语言 | Python 3 |
| GUI 框架 | PyQt5 |
| 数据库 | SQLite（WAL 模式 + 线程锁） |
| Markdown 渲染 | mistune |
| 语法高亮 | Pygments |
| AI 接口 | OpenAI 兼容 API（支持自定义端点） |
| 凭证管理 | keyring / Windows Credential Manager |
| 打包 | PyInstaller |
| 代码检查 | Ruff（linter + formatter） |
| 测试 | pytest + coverage（1334 测试用例） |

---

## 项目结构

```text
DevLearnerAI/
├── main.py                  # 生产环境启动入口
├── dev_main.py              # 开发环境启动入口
├── pyproject.toml           # 项目元数据 + 工具配置
├── requirements.txt         # 运行时依赖
├── Makefile                 # 开发命令（lint / format / test）
├── app/
│   ├── config.py            # 应用配置
│   ├── window.py            # 主窗口（侧边栏 + 页面管理）
│   ├── database.py          # SQLite 数据库（线程安全 + WAL）
│   ├── content_service.py   # 课程内容加载（延迟加载）
│   ├── python_runner.py     # 代码执行沙箱（AST 预检）
│   ├── credentials.py       # 凭证安全存储
│   ├── ai/                  # AI 模块（API / 对话 / 渲染）
│   ├── practice/            # 练习模块（评测 / 加载 / 标准化）
│   └── widgets/             # UI 组件（仪表盘 / 学习 / 练习 / 项目 / 算法）
├── tests/                   # 1000+ 测试用例
├── content/                 # 课程内容（Python / C / C++ / C# / 数据库）
│   └── metadata/            # 课程元数据 + 练习元数据
├── scripts/                 # 构建与数据重建脚本
└── docs/                    # 开发文档
```

---

## 安全设计

- **代码执行沙箱** -- AST 预检拦截危险代码，限制 `os.system` / `subprocess` / `eval` / `exec`
- **API 密钥安全** -- 存储在 Windows Credential Manager，不明文保存
- **HTTPS 强制** -- AI API 通信强制 TLS，拒绝 HTTP
- **数据库线程安全** -- WAL 模式 + 写操作锁
- **HTML 输出净化** -- 防止 Markdown 渲染后的 XSS 注入
- **资源限制** -- 输出 12KB 上限，执行 3 秒超时

---

## 开发指南

```bash
# 代码检查
make lint       # 或 ruff check .

# 自动格式化
make format     # 或 ruff format .

# 运行测试
make test       # 或 pytest

# 覆盖率报告
make coverage
```

提交前请确保 `ruff check .` 和 `pytest` 均通过。详细指南请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 开发路线图

| 阶段 | 计划 |
|:---|:---|
| **v6.0 (已完成)** | 统一课程元数据 / 176 道练习 / AI 辅导 / 10 个实战项目 / 仪表盘 |
| **v6.1 (近期)** | 错题本 / 知识图谱 / 阶段测评 / 判题升级 |
| **v7.0 (中期)** | 协作学习 / 自定义路径 / Go/Rust/TypeScript 路线 / 移动端 |
| **长期愿景** | 自适应学习 / 在线模式 / 社区课程 / 企业版 |

---

## 贡献

欢迎参与项目贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发环境搭建、分支策略、PR 流程和代码规范。

---

## 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

## 致谢

- Python 官方教程 | PyQt 文档 | SQLite 官方文档 | mistune | Pygments
