# 快速入门指南

欢迎使用 DevLearner AI！本指南将帮助你完成从安装到首次运行的全部流程。

---

## 目录

- [系统要求](#系统要求)
- [安装方式一：从源码运行](#安装方式一从源码运行)
- [安装方式二：使用可执行文件](#安装方式二使用可执行文件)
- [首次启动](#首次启动)
- [配置 AI 导师（API 设置）](#配置-ai-导师api-设置)
- [界面概览](#界面概览)
- [常见启动问题](#常见启动问题)

---

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11（推荐）；Linux / macOS 部分功能受限 |
| Python | 3.9 或更高版本（推荐 3.12） |
| 内存 | 建议 4GB 以上 |
| 磁盘空间 | 约 200MB（含课程内容和数据库） |
| 网络 | 使用 AI 助手功能时需要互联网连接 |

---

## 安装方式一：从源码运行

### 第 1 步：获取源码

```bash
git clone https://github.com/TIANWEN-cpu/DevLearnerAI.git
cd DevLearnerAI
```

### 第 2 步：创建虚拟环境（推荐）

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS
```

### 第 3 步：安装依赖

最小运行依赖仅 3 个包：

```bash
pip install -r requirements.txt
```

依赖列表：
- `PyQt5>=5.15` -- GUI 框架
- `mistune>=3.0` -- Markdown 渲染
- `keyring>=24.0` -- 凭证安全存储

如需开发功能（测试、代码检查等）：

```bash
pip install -e ".[dev]"
```

### 第 4 步：启动应用

```bash
python main.py
```

---

## 安装方式二：使用可执行文件

如果你不希望配置 Python 环境，可以直接使用预编译的可执行文件。

1. 前往 [GitHub Releases](https://github.com/TIANWEN-cpu/DevLearnerAI/releases) 页面
2. 下载最新版本的 `.exe` 文件
3. 双击运行即可

可执行文件已内嵌 Python 解释器和所有依赖，无需额外安装。

---

## 首次启动

### 启动入口

| 入口文件 | 用途 | 日志级别 |
|----------|------|----------|
| `python main.py` | 生产环境 | INFO |
| `python dev_main.py` | 开发环境 | DEBUG（更详细的日志输出） |

### 首次启动时的自动操作

应用首次启动时会自动完成以下操作：

1. **创建用户数据目录** -- 在 `%APPDATA%/DevLearnerAI/` 下创建以下子目录：
   - `data/` -- 数据库文件
   - `logs/` -- 运行日志
   - `cache/` -- 缓存文件
   - `exports/` -- 导出文件
   - `drafts/` -- 练习草稿
2. **初始化数据库** -- 创建 SQLite 数据库并建立所有表结构
3. **检测旧版数据库** -- 如存在旧版数据库 `db/learner.db`，自动迁移到新路径
4. **加载课程内容** -- 从 `content/` 目录读取课程元数据

### 主界面布局

启动后，你会看到左侧导航栏和右侧内容区域：

| 导航项 | 功能 |
|--------|------|
| 首页 | 学习仪表盘，显示进度概览和统计 |
| 学习路径 | 浏览和学习课程内容 |
| 练习中心 | 编程练习与自动评测 |
| 融合项目 | 项目实战 |
| 算法动画 | 算法可视化 |
| AI 导师 | AI 智能对话助手 |

---

## 配置 AI 导师（API 设置）

AI 导师功能需要配置 OpenAI 兼容 API。以下是详细步骤：

### 第 1 步：打开 AI 设置

1. 点击左侧导航栏中的 **AI 导师**
2. 在 AI 工作台或侧边助手面板中找到 **AI 设置** 按钮

### 第 2 步：填写 API 配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| API Host | API 服务地址（必须以 `https://` 开头） | `https://api.openai.com` |
| API Key | API 密钥 | `sk-xxxxxxxxxxxx` |
| 模型 | 选择使用的 AI 模型 | `gpt-4o` / `claude-3-opus` |

### 第 3 步：测试连接

点击 **测试连接** 按钮，确认 API 配置正确。成功后会显示"连接成功"提示。

### 第 4 步：获取模型列表

点击 **获取模型** 按钮，从下拉列表中选择你想使用的模型。

### API 密钥的安全存储

API 密钥不会明文保存在配置文件中。系统使用以下方式安全存储：

- **Windows**：使用 Windows Credential Manager
- **其他平台**：回退到 keyring 库或 base64 编码文件

### 支持的 API 服务

任何兼容 OpenAI API 格式的服务均可使用，包括但不限于：

- OpenAI（GPT-4o、GPT-4 等）
- Anthropic Claude（通过兼容网关）
- 其他 OpenAI 兼容 API 服务

---

## 界面概览

### 首页（学习仪表盘）

- 当前学习进度总览
- 课程完成率和统计数据
- 连续学习天数
- 每日学习概览
- 快速导航到各技术栈

### 学习路径

- 8 条技术栈路线（Python、C、C++、C#、数据库、算法、融合项目、实战项目）
- 三级层次结构：技术栈（Track） > 模块（Module） > 课时（Lesson）
- 课程内容以 Markdown 格式渲染，支持代码语法高亮
- 课程完成度追踪和笔记功能

### 练习中心

- 按技术栈和难度筛选练习
- 内置代码编辑器
- 自动评测和即时反馈
- 练习草稿自动保存
- 练习历史记录

### AI 导师

- 两种使用模式：AI 工作台（独立页面）和侧边助手（Dock 面板）
- 多会话管理：按主题拆分对话
- 快捷提问：解释当前课程、分析当前代码
- Markdown 渲染和代码语法高亮
- 上下文感知的知识库

---

## 常见启动问题

### "No module named 'PyQt5'"

```bash
pip install PyQt5>=5.15
```

### 启动后白屏或界面异常

1. 确认 Python 版本 >= 3.9：`python --version`
2. 尝试使用开发模式查看详细日志：`python dev_main.py`
3. 检查 `%APPDATA%/DevLearnerAI/logs/` 中的日志文件

### 数据库初始化失败

1. 确认 `%APPDATA%/DevLearnerAI/data/` 目录有写入权限
2. 如果数据库文件损坏，删除 `app.db` 后重启应用

### 缺少课程内容

1. 确认 `content/` 目录存在且包含课程文件
2. 确认 `content/metadata/course_map.json` 文件完整

---

> 下一步：[学习指南](learning-guide.md) -- 了解如何使用学习系统高效学习编程

---

## 参见 (See Also)

- [用户指南](../user-guide.md) - 功能概览
- [学习指南](learning-guide.md) - 学习系统使用指南
- [练习指南](practice-guide.md) - 练习系统使用指南
- [设置指南](settings-guide.md) - 应用设置配置
- [常见问题](../troubleshooting/common-issues.md) - 安装和启动问题
- [术语表](../glossary.md) - 专业术语定义
