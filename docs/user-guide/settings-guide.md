# 设置指南

本指南介绍如何配置 DevLearner AI 的各项设置，包括 API 配置、主题设置等。

---

## 目录

- [设置入口](#设置入口)
- [AI API 配置](#ai-api-配置)
- [主题与界面设置](#主题与界面设置)
- [数据管理](#数据管理)
- [键盘快捷键](#键盘快捷键)
- [高级设置](#高级设置)

---

## 设置入口

应用的设置分散在不同位置：

| 设置类型 | 位置 | 说明 |
|----------|------|------|
| AI API 设置 | AI 导师界面 -> AI 设置 | 配置 API 连接和模型 |
| 应用配置 | `app/config.py` | 应用全局配置（开发者） |
| 样式设置 | `app/styles.py` | 界面样式定义 |

---

## AI API 配置

### 配置项详解

#### API Host

- **说明**：AI API 服务的基础地址
- **格式**：必须以 `https://` 开头
- **示例**：
  - OpenAI：`https://api.openai.com`
  - 自定义端点：`https://your-api-server.com`
- **安全要求**：出于安全考虑，不允许使用 HTTP 连接

#### API Key

- **说明**：API 访问密钥
- **格式**：由 API 服务商提供的字符串
- **存储方式**：安全存储，不明文保存
  - Windows：Windows Credential Manager
  - 其他平台：keyring 或 base64 编码文件

#### 模型选择

- **说明**：选择使用的 AI 模型
- **获取方式**：点击"获取模型"按钮从 API 自动加载
- **常见模型**：
  - `gpt-4o` -- OpenAI 最新模型
  - `gpt-4-turbo` -- 高性能模型
  - `gpt-3.5-turbo` -- 经济型模型
  - Claude 系列（通过兼容网关）

### 连接测试

配置完成后，点击 **测试连接** 按钮验证：
- 网络连通性
- API Key 有效性
- 服务可用性

测试结果会缓存 5 分钟，避免重复请求。

### 多配置管理

- API 配置存储在 `mentor_api_config` 表中
- 支持随时修改配置
- 修改后立即生效

---

## 主题与界面设置

### 主题选择

DevLearner AI 基于 PyQt5 构建，支持系统原生主题。

### 字体设置

应用支持自定义字体配置，包括：
- 代码字体
- 正文字体
- 字体大小

### 样式系统

全局样式定义在 `app/styles.py` 中，包括：
- 颜色方案
- 间距和布局
- 按钮和输入框样式
- 代码高亮主题

---

## 数据管理

### 数据存储路径

| 数据类型 | 路径 |
|----------|------|
| 数据库 | `%APPDATA%/DevLearnerAI/data/app.db` |
| 日志 | `%APPDATA%/DevLearnerAI/logs/` |
| 缓存 | `%APPDATA%/DevLearnerAI/cache/` |
| 导出 | `%APPDATA%/DevLearnerAI/exports/` |
| 草稿 | `%APPDATA%/DevLearnerAI/drafts/` |

其中 `%APPDATA%` 通常为 `C:\Users\<用户名>\AppData\Roaming`。

### 数据库表结构

| 表名 | 存储内容 |
|------|----------|
| `lesson_progress` | 课程学习进度 |
| `practice_attempts` | 练习提交记录 |
| `lesson_notes` | 课程学习笔记 |
| `mentor_sessions` | AI 导师会话 |
| `mentor_messages` | AI 对话消息 |
| `mentor_api_config` | API 配置 |
| `mentor_workspace_state` | 工作台状态 |
| `mentor_knowledge_files` | 知识库文件 |
| `exercise_drafts` | 练习草稿 |

### 数据库维护

- 数据库使用 SQLite WAL 模式，确保数据安全
- 写操作使用线程锁，保证多线程安全
- 如遇数据库损坏，删除 `app.db` 后重启应用（学习进度将丢失）

### 数据清除

如需重置所有数据：

1. 关闭应用
2. 删除 `%APPDATA%/DevLearnerAI/` 目录
3. 重新启动应用

注意：此操作不可恢复，请提前备份重要数据。

---

## 键盘快捷键

DevLearner AI 支持以下键盘快捷键：

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+S` | 保存当前内容 |
| `Ctrl+Z` | 撤销 |
| `Ctrl+Y` | 重做 |
| `Ctrl+C` | 复制 |
| `Ctrl+V` | 粘贴 |
| `Ctrl+A` | 全选 |

部分快捷键可能因页面不同而有差异。

---

## 高级设置

### 开发者模式

使用 `dev_main.py` 启动时启用 DEBUG 日志模式：

```bash
python dev_main.py
```

DEBUG 模式会输出更详细的日志信息，包括：
- API 请求和响应详情
- 数据库操作日志
- 课程加载过程
- 评测流程细节

### 日志查看

日志文件保存在 `%APPDATA%/DevLearnerAI/logs/` 目录下，可用于排查问题。

### 配置文件位置

| 配置文件 | 路径 | 说明 |
|----------|------|------|
| `config.py` | `app/config.py` | 应用全局配置 |
| `styles.py` | `app/styles.py` | 样式配置 |
| `course_map.json` | `content/metadata/course_map.json` | 课程元数据 |
| `exercises.json` | `content/metadata/exercises.json` | 练习元数据 |

### 环境变量

| 变量 | 说明 |
|------|------|
| `APPDATA` | 用户数据目录（Windows） |
| `LOCALAPPDATA` | 备用数据目录 |

---

> 下一步：[开发者指南](../developer-guide/architecture.md) -- 了解项目技术架构

---

## 参见 (See Also)

- [快速入门指南](getting-started.md) - 安装和首次运行
- [AI 导师指南](ai-mentor-guide.md) - AI 配置详细说明
- [仪表盘指南](dashboard-guide.md) - 数据管理
- [安全模型](../concepts/security-model.md) - 凭证和传输安全
- [模块一览](../reference/modules.md) - 模块配置参考
- [术语表](../glossary.md) - 专业术语定义
