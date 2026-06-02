# 常见问题解答（FAQ）

本文档收集了 DevLearner AI 使用和开发过程中的常见问题及解答。

---

## 目录

- [基础问题](#基础问题)
- [安装与运行](#安装与运行)
- [学习功能](#学习功能)
- [练习功能](#练习功能)
- [AI 导师功能](#ai-导师功能)
- [数据与隐私](#数据与隐私)
- [开发相关](#开发相关)
- [其他问题](#其他问题)

---

## 基础问题

### Q: DevLearner AI 是什么？

DevLearner AI 是一款 AI 驱动的桌面编程学习平台，基于 Python / PyQt5 / SQLite 构建。它集成了 AI 智能导师、代码执行沙箱、课程体系、交互式练习和学习仪表盘，帮助编程初学者和进阶学习者系统性地学习编程。

### Q: DevLearner AI 是免费的吗？

是的，DevLearner AI 完全开源免费，采用 MIT 许可证。但 AI 导师功能需要你自己提供 API Key（如 OpenAI API Key）。

### Q: 支持哪些操作系统？

主要支持 Windows 10/11。部分功能（如 Windows Credential Manager）依赖 Windows 特有 API，其他平台会回退到 keyring 或 base64 编码文件存储。

### Q: 支持哪些编程语言的学习？

支持 8 条学习路线：
- Python
- C 语言
- C++
- C#
- 数据库（SQL / SQLite）
- 算法
- 融合项目
- 实战项目

### Q: 与 LeetCode、Codecademy 等平台有什么区别？

DevLearner AI 的核心差异：
- 将课程内容、练习系统、AI 辅导和项目实战整合到一个桌面应用中
- 支持离线使用
- 完全开源免费
- 内置 SQL 真实查询验证
- 提供跨语言融合项目

---

## 安装与运行

### Q: 如何安装 DevLearner AI？

**方式一：从源码运行**
```bash
git clone https://github.com/TIANWEN-cpu/DevLearnerAI.git
cd DevLearnerAI
pip install -r requirements.txt
python main.py
```

**方式二：使用可执行文件**

从 [GitHub Releases](https://github.com/TIANWEN-cpu/DevLearnerAI/releases) 下载最新版本的 `.exe` 文件，双击运行即可。

### Q: Python 最低版本要求是多少？

Python 3.9 或更高版本，推荐使用 3.12。

### Q: 需要安装哪些依赖？

最小运行依赖仅 3 个包：
- `PyQt5>=5.15` -- GUI 框架
- `mistune>=3.0` -- Markdown 渲染
- `keyring>=24.0` -- 凭证安全存储

### Q: 启动时报 "No module named 'PyQt5'" 怎么办？

```bash
pip install PyQt5>=5.15
```

### Q: main.py 和 dev_main.py 有什么区别？

| 文件 | 用途 | 日志级别 |
|------|------|----------|
| `main.py` | 生产环境 | INFO |
| `dev_main.py` | 开发环境 | DEBUG（更详细） |

功能完全相同，区别仅在于日志输出级别。

---

## 学习功能

### Q: 有多少课时？

当前提供 130+ 课时，覆盖 8 条学习路线，从基础语法到工程实战。

### Q: 课程内容以什么格式呈现？

课程以 Markdown 格式渲染，支持：
- 代码语法高亮
- 代码一键复制
- 目录导航
- 完成度追踪

### Q: 学习进度保存在哪里？

学习进度保存在本地 SQLite 数据库中：
- 路径：`%APPDATA%/DevLearnerAI/data/app.db`
- 数据不会上传到任何服务器
- 卸载应用前请备份此文件

### Q: 可以做笔记吗？

可以。每个课时都支持添加学习笔记，笔记存储在数据库的 `lesson_notes` 表中。

### Q: 推荐什么学习顺序？

**零基础**：Python 入门 -> 数据库基础 -> Python 进阶 -> 融合项目

**有基础**：可直接选择感兴趣的技术栈，注意查看前置依赖。

---

## 练习功能

### Q: 有多少练习题？

当前提供 176+ 道练习题，覆盖全部 8 条学习路线。

### Q: 支持哪些语言的自动评测？

| 语言 | 评测方式 |
|------|----------|
| Python | 沙箱执行 + 测试用例 |
| SQL | 内存数据库真实执行 |
| C / C++ / C# | 关键字结构检查 |

### Q: Python 代码在哪里执行？

Python 代码在应用内置的安全沙箱中执行：
- AST 预检拦截危险代码
- 禁止 `os.system`、`subprocess`、`eval`、`exec` 等危险函数
- 限制可导入模块白名单
- 执行超时 3 秒
- 输出限制 12KB

### Q: SQL 练习是如何验证的？

SQL 代码在内存 SQLite 数据库中执行：
- 对于 SELECT 查询，比对查询结果与预期结果集
- 对于 DDL 操作（CREATE/ALTER），验证表结构变化
- 使用标准化比对，忽略行列顺序差异

### Q: 练习草稿会自动保存吗？

是的。练习代码会自动保存到数据库的 `exercise_drafts` 表中。重新打开同一练习时会自动恢复上次的草稿。

### Q: 评测分数是如何计算的？

评测结果包含多维度评分：
- 语法检查 -- 代码能否正确解析
- 结构检查 -- 是否包含必要的结构
- 运行结果 -- 执行结果是否正确
- 测试用例 -- 测试用例通过率

综合以上维度给出 0-100 分的评测分数。

---

## AI 导师功能

### Q: 使用 AI 导师需要什么？

需要提供 OpenAI 兼容 API 的配置：
- API Host（HTTPS 地址）
- API Key
- 选择的模型

### Q: 支持哪些 AI 模型？

支持所有 OpenAI 兼容 API 提供的模型，包括：
- OpenAI（GPT-4o、GPT-4-turbo、GPT-3.5-turbo 等）
- Anthropic Claude（通过兼容网关）
- 其他 OpenAI 兼容服务

### Q: API Key 安全吗？

是的。API Key 通过以下方式安全存储：
- Windows：Windows Credential Manager
- 其他平台：keyring 库或 base64 编码文件
- 不会明文保存在配置文件中

### Q: 为什么只能用 HTTPS？

出于安全考虑，AI API 通信强制使用 HTTPS，启用 TLS 证书验证，拒绝 HTTP 连接，防止 API Key 在传输过程中被截获。

### Q: 对话历史会保存多久？

所有对话历史永久保存在本地数据库中，直到你手动删除。重新打开应用后自动恢复。

### Q: 可以同时进行多个对话吗？

可以。支持多会话管理，你可以按主题创建多个独立的对话会话（如"Python 调试"、"数据库设计"、"项目拆解"等）。

### Q: AI 导师有哪些快捷功能？

- 解释当前课程 -- 获取当前课程的详细讲解
- 分析当前代码 -- 诊断练习中的代码问题
- 拆解当前项目 -- 获取项目的任务分解和规划

---

## 数据与隐私

### Q: 数据会上传到服务器吗？

不会。所有学习数据、练习记录、AI 对话历史都存储在本地 SQLite 数据库中。只有 AI 对话消息会发送到你配置的 API 服务端。

### Q: 数据存储在哪里？

| 数据类型 | 路径 |
|----------|------|
| 数据库 | `%APPDATA%/DevLearnerAI/data/app.db` |
| 日志 | `%APPDATA%/DevLearnerAI/logs/` |
| 缓存 | `%APPDATA%/DevLearnerAI/cache/` |
| 导出 | `%APPDATA%/DevLearnerAI/exports/` |
| 草稿 | `%APPDATA%/DevLearnerAI/drafts/` |

### Q: 如何备份数据？

1. 关闭应用
2. 复制 `%APPDATA%/DevLearnerAI/data/app.db` 到安全位置

### Q: 如何恢复数据？

1. 关闭应用
2. 将备份的 `app.db` 复制回 `%APPDATA%/DevLearnerAI/data/` 目录
3. 重新启动应用

### Q: 如何清除所有数据？

1. 关闭应用
2. 删除 `%APPDATA%/DevLearnerAI/` 目录
3. 重新启动应用

---

## 开发相关

### Q: 如何搭建开发环境？

```bash
git clone https://github.com/TIANWEN-cpu/DevLearnerAI.git
cd DevLearnerAI
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

详见 [贡献指南](docs/developer-guide/contributing.md)。

### Q: 使用什么代码检查工具？

使用 [Ruff](https://github.com/astral-sh/ruff) 统一完成 lint 和格式化：
```bash
make lint      # 检查代码风格
make format    # 自动格式化
```

### Q: 如何运行测试？

```bash
make test      # 运行所有测试
make coverage  # 运行测试 + 覆盖率
```

### Q: 如何添加新的课程内容？

1. 在 `content/<技术栈>/` 下添加 `.md` 文件
2. 在 `content/metadata/course_map.json` 中注册课程元数据
3. 在 `content/metadata/exercises.json` 中注册关联练习（如适用）

详见 [课程内容格式指南](docs/developer-guide/content-format.md)。

### Q: 如何添加新的练习？

1. 在 `content/metadata/exercises.json` 中添加练习定义
2. 准备测试数据（SQL fixture 或 expected_output）
3. 如需特殊评测逻辑，修改 `app/practice/evaluator.py`

详见 [练习格式指南](docs/developer-guide/exercise-format.md)。

### Q: 如何打包为可执行文件？

```bash
pip install pyinstaller
python scripts/build/build_dev_exe.py
```

产物输出到 `dist/` 目录。详见 [构建指南](docs/developer-guide/building.md)。

---

## 其他问题

### Q: 如何报告 Bug？

请在 [GitHub Issues](https://github.com/TIANWEN-cpu/DevLearnerAI/issues) 中提交问题报告，附上：
1. 问题描述
2. 复现步骤
3. 预期行为 vs 实际行为
4. 日志文件（`%APPDATA%/DevLearnerAI/logs/`）
5. 操作系统和 Python 版本

### Q: 如何贡献代码？

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发环境搭建、分支策略、PR 流程和代码规范。

### Q: 项目使用什么许可证？

MIT 许可证，可自由使用、修改和分发。

### Q: 如何获取帮助？

1. 查看本文档的其他章节
2. 查看 [故障排除指南](docs/troubleshooting.md)
3. 在 [GitHub Issues](https://github.com/TIANWEN-cpu/DevLearnerAI/issues) 中提问
4. 使用应用内的 AI 导师功能（需要配置 API）

---

> 如果你的问题不在上述列表中，请在 GitHub Issues 中提出，我们会尽快回复。
