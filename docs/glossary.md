# 术语表

本文档定义 DevLearnerAI 文档和技术中使用的专业术语。

---

## A

### ADR (Architecture Decision Record)
架构决策记录。记录关键设计决策的背景、备选方案和最终选择。参见 [ADR 目录](adr/001-pyqt5-choice.md)。

### AI 导师 (AI Mentor)
DevLearnerAI 内置的智能编程辅导功能，基于 OpenAI 兼容 API 提供对话式学习辅助。详见 [AI 导师集成](concepts/ai-integration.md) 和 [AI 导师指南](user-guide/ai-mentor-guide.md)。

### API Key
访问 AI 服务所需的认证密钥，通过 Windows Credential Manager 或 keyring 安全存储。详见 [安全模型](concepts/security-model.md)。

### API Host
AI 服务的 API 端点地址，必须以 `https://` 开头。详见 [API 集成参考](reference/api-integration.md)。

### AST (Abstract Syntax Tree)
抽象语法树。Python 代码被解析为 AST 后进行静态安全分析，拦截危险操作。详见 [安全模型 > AST 静态分析](concepts/security-model.md#1-代码执行沙箱)。

---

## B

### Base64 回退
当 Windows Credential Manager 和 keyring 均不可用时，将 API 密钥以 Base64 编码存储在文件中作为回退方案。详见 [凭证管理](reference/modules.md#appcredentials)。

---

## C

### ContentService
课程内容管理服务，负责从 `course_map.json` 加载 Track/Module/Lesson 三级结构，支持懒加载和 Markdown 缓存。详见 [课程内容体系](concepts/content-system.md)。

### course_map.json
课程元数据配置文件，定义所有技术栈、模块和课程的层次结构。详见 [内容文件格式](reference/content-format.md)。

### 持续学习天数 (Streak)
用户连续每天使用应用学习的天数统计。详见 [仪表盘指南 > 连续学习天数](user-guide/dashboard-guide.md#连续学习天数)。

---

## D

### DashboardWidget
学习仪表盘组件，展示学习进度、统计信息和快速导航入口。详见 [Widget 系统](concepts/widget-system.md#dashboardwidget)。

### DevLearnerWindow
应用主窗口类（QMainWindow），管理侧边栏导航、页面切换和 AI Dock。详见 [系统架构 > Widget 层次](concepts/architecture.md#表示层-widgets)。

### Dock 面板
AI 导师的侧边停靠面板形态，可以在任何页面右侧显示。详见 [Widget 系统 > AIMentorPanel / AIMentorDock](concepts/widget-system.md#aimentorpanel--aimentordock)。

---

## E

### EvaluationResult
评测结果数据类，包含通过状态、分数、反馈信息、输出和耗时。详见 [练习格式](reference/exercise-format.md)。

### Exercise
练习数据类，包含 ID、标题、难度、评测配置等完整信息。详见 [练习格式](reference/exercise-format.md)。

### exercises.json
练习元数据配置文件，定义所有编程练习的题目和评测规则。详见 [练习格式](reference/exercise-format.md)。

### expected_nodes
Python 练习中期望的 AST 节点类型列表，用于代码结构验证。详见 [练习创建指南 > expected_nodes](guides/exercise-creation.md#expected_nodes-字段)。

---

## F

### FIFO 淘汰策略
Markdown 缓存使用先进先出（First In, First Out）策略淘汰旧内容。详见 [ADR-003: 内容加载机制](adr/003-content-loading.md)。

### Fixture
SQL 练习的测试数据配置，包含建表语句、测试数据和期望结果。详见 [练习格式 > sql_query_fixtures.json](reference/exercise-format.md#sql_query_fixturesjson-格式)。

---

## H

### HTTPS 强制
所有 AI API 通信必须使用 HTTPS 协议，非 HTTPS 请求会被拒绝。详见 [安全模型 > 传输安全](concepts/security-model.md#3-传输安全)。

---

## K

### keyring
Python 密钥管理库，用于跨平台安全存储 API 密钥。详见 [凭证管理](reference/modules.md#appcredentials)。

### 知识库 (Knowledge Base)
AI 导师的三层上下文系统：基础知识库（课程摘要）、个性知识库（学习进度）、扩展知识库（用户文件）。详见 [AI 导师集成 > 知识库系统](concepts/ai-integration.md#知识库系统)。

---

## L

### LearnWidget
课程学习页面组件，展示课程列表和 Markdown 渲染内容。详见 [Widget 系统](concepts/widget-system.md#learnwidget)。

### Lesson
课程，最小的学习单元，对应一个 Markdown 文件。详见 [课程内容体系 > Lesson](concepts/content-system.md#lesson-课程)。

### LimitedBuffer
限制标准输出为 12KB 的缓冲区类，防止代码执行产生过多输出。详见 [安全模型 > 输出限制](concepts/security-model.md#5-输出限制)。

---

## M

### Markdown 渲染
将 Markdown 文本转换为 HTML 并通过白名单净化器处理的过程。详见 [AI 导师集成 > Markdown 渲染](concepts/ai-integration.md#markdown-渲染)。

### Module
模块，技术栈下的分组单元，包含一组逻辑相关的课程。详见 [课程内容体系 > Module](concepts/content-system.md#module-模块)。

---

## P

### PracticeService
练习服务，加载练习元数据并分发到对应语言的评测器。详见 [模块一览 > app.practice](reference/modules.md#练习子模块-apppractice)。

### PracticeWidget
练习中心组件，提供代码编辑、运行和评测功能。详见 [Widget 系统](concepts/widget-system.md#practicewidget)。

### PyInstaller
Python 打包工具，将应用打包为独立的 Windows 可执行文件。详见 [构建指南](guides/building.md)。

### PyQt5
Qt 框架的 Python 绑定，DevLearnerAI 的 GUI 框架。详见 [ADR-001: 选择 PyQt5](adr/001-pyqt5-choice.md)。

---

## Q

### QDockWidget
Qt 停靠窗口组件，用于实现 AI 侧边助手面板。详见 [Widget 系统 > AIMentorPanel / AIMentorDock](concepts/widget-system.md#aimentorpanel--aimentordock)。

### QStackedWidget
Qt 堆叠窗口组件，管理多个页面的切换显示。详见 [Widget 系统 > 页面导航机制](concepts/widget-system.md#页面导航机制)。

---

## R

### required_keywords
SQL/C/C# 练习中代码必须包含的关键字列表。详见 [练习格式](reference/exercise-format.md)。

### Ruff
Python 代码检查和格式化工具，统一替代 flake8 + isort + black。详见 [开发工作流 > 工具链](guides/development.md#工具链)。

---

## S

### SAFE_BUILTINS
沙箱中允许使用的受限内置函数集合，移除了 eval、exec、open 等危险函数。详见 [安全模型 > 受限内置函数](concepts/security-model.md#受限内置函数)。

### 沙箱 (Sandbox)
代码执行的安全隔离环境，通过 AST 预检、受限内置函数、进程隔离和超时控制实现多层防护。详见 [安全模型](concepts/security-model.md) 和 [ADR-002: 沙箱方案](adr/002-sandbox-approach.md)。

### 信号与槽 (Signal/Slot)
Qt 的事件通信机制，Widget 间通过信号和槽实现松耦合通信。详见 [Widget 系统 > Widget 间通信](concepts/widget-system.md#widget-间通信)。

### SSE (Server-Sent Events)
服务器推送事件协议，用于 AI 流式响应。详见 [API 集成参考 > 流式请求](reference/api-integration.md#流式请求)。

---

## T

### Track
技术栈，课程体系的顶层组织单元（如 Python、C++、数据库）。详见 [课程内容体系 > Track](concepts/content-system.md#track-技术栈)。

### 测试用例 (Tests)
Python 练习中定义的表达式-期望值对，用于验证代码正确性。详见 [练习创建指南 > tests 字段](guides/exercise-creation.md#tests-字段)。

---

## V

### WAL (Write-Ahead Logging)
SQLite 预写日志模式，允许读写并发，提高数据库性能和数据安全性。详见 [数据库 Schema](reference/database-schema.md)。

---

## W

### Windows Credential Manager
Windows 系统的凭证管理服务，DevLearnerAI 优先使用它存储 API 密钥。详见 [安全模型 > 凭证安全存储](concepts/security-model.md#2-凭证安全存储)。

---

## X

### XSS 防护
跨站脚本攻击防护，通过 HTML 白名单净化器移除 script、事件处理器等危险内容。详见 [安全模型 > XSS 防护](concepts/security-model.md#4-xss-防护)。
