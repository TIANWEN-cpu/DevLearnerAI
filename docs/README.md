# DevLearnerAI 文档中心

欢迎来到 DevLearnerAI 的文档中心。本文档集合涵盖了系统架构、开发指南、API 参考和故障排除等完整内容。

---

## 文档目录

### 概念 (Concepts)

理解系统的整体设计和核心机制。

| 文档 | 说明 |
|------|------|
| [系统架构](concepts/architecture.md) | 整体架构、分层设计、数据流 |
| [Widget 系统](concepts/widget-system.md) | PyQt5 组件层次结构与交互模式 |
| [安全模型](concepts/security-model.md) | 沙箱机制、凭证管理、XSS 防护 |
| [课程内容体系](concepts/content-system.md) | Track > Module > Lesson 三级体系 |
| [AI 导师集成](concepts/ai-integration.md) | AI API 通信、知识库、流式响应 |

### 指南 (Guides)

面向开发者和内容作者的实战指南。

| 文档 | 说明 |
|------|------|
| [快速开始](guides/getting-started.md) | 环境搭建、首次运行、验证安装 |
| [开发工作流](guides/development.md) | 日常开发流程、代码规范、调试技巧 |
| [测试指南](guides/testing.md) | 测试体系、编写规范、覆盖率 |
| [课程内容编写](guides/content-authoring.md) | 如何创建课程 Markdown 文档 |
| [练习创建](guides/exercise-creation.md) | 如何定义和配置编程练习 |
| [构建可执行文件](guides/building.md) | PyInstaller 打包与分发 |

### 参考 (Reference)

模块、API 和数据格式的完整参考。

| 文档 | 说明 |
|------|------|
| [模块一览](reference/modules.md) | 所有模块的职责、接口和依赖关系 |
| [数据库 Schema](reference/database-schema.md) | SQLite 表结构、索引、迁移 |
| [API 集成参考](reference/api-integration.md) | AI API 通信协议和配置 |
| [内容文件格式](reference/content-format.md) | course_map.json 和 Markdown 课程文件格式 |
| [练习格式](reference/exercise-format.md) | exercises.json 和评测配置格式 |

### 架构决策记录 (ADR)

关键设计决策的背景和权衡。

| 文档 | 说明 |
|------|------|
| [ADR-001: 选择 PyQt5](adr/001-pyqt5-choice.md) | 为什么选择 PyQt5 作为 GUI 框架 |
| [ADR-002: 沙箱方案](adr/002-sandbox-approach.md) | 代码执行沙箱的安全策略 |
| [ADR-003: 内容加载机制](adr/003-content-loading.md) | 课程内容的懒加载与缓存策略 |

### 故障排除 (Troubleshooting)

常见问题和解决方案。

| 文档 | 说明 |
|------|------|
| [常见问题](troubleshooting/common-issues.md) | 启动、安装、运行时常见问题 |
| [沙箱问题](troubleshooting/sandbox-issues.md) | 代码执行和评测相关问题 |
| [内容问题](troubleshooting/content-issues.md) | 课程加载、练习显示相关问题 |

### 术语表 (Glossary)

| 文档 | 说明 |
|------|------|
| [术语表](glossary.md) | 文档中使用的专业术语定义和索引 |

---

## 文档维护

本文档使用中文编写，与项目代码保持同步更新。文档中的代码示例均来自实际代码库，可直接参考对应源文件获取最新实现。

文档更新流程：

1. 在 `docs/` 目录对应位置编辑或新增 Markdown 文件
2. 如果涉及新目录，请在本文件中添加索引链接
3. 提交前确认文档中的代码示例仍然与代码库一致
