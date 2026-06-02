# 文档搜索索引

本文件为 DevLearnerAI 文档的全文搜索索引，帮助快速定位相关内容。

---

## 按主题索引

### 安装与配置

| 关键词 | 文档位置 |
|--------|----------|
| 安装依赖 | [快速开始](guides/getting-started.md)、[README](../README.md) |
| 虚拟环境 | [快速开始](guides/getting-started.md) |
| Python 版本 | [快速开始](guides/getting-started.md)、[pyproject.toml](../pyproject.toml) |
| PyQt5 安装 | [快速开始](guides/getting-started.md)、[故障排除](troubleshooting.md) |
| AI API 配置 | [AI 导师指南](user-guide/ai-mentor-guide.md) |
| 凭证管理 | [安全模型](concepts/security-model.md)、[credentials.py](../app/credentials.py) |

### 开发

| 关键词 | 文档位置 |
|--------|----------|
| 代码规范 | [编码标准](developer-guide/coding-standards.md)、[CONTRIBUTING](../CONTRIBUTING.md) |
| Ruff 配置 | [pyproject.toml](../pyproject.toml)、[CONTRIBUTING](../CONTRIBUTING.md) |
| 分支策略 | [CONTRIBUTING](../CONTRIBUTING.md) |
| 提交规范 | [CONTRIBUTING](../CONTRIBUTING.md) |
| 调试技巧 | [开发工作流](guides/development.md) |
| 类型注解 | [pyproject.toml](../pyproject.toml)（mypy 配置） |

### 测试

| 关键词 | 文档位置 |
|--------|----------|
| 运行测试 | [测试指南](guides/testing.md)、[CONTRIBUTING](../CONTRIBUTING.md) |
| 覆盖率 | [测试指南](guides/testing.md) |
| 安全测试 | [测试指南](guides/testing.md)、[安全模型](concepts/security-model.md) |
| 集成测试 | [测试指南](guides/testing.md) |
| 编写测试 | [测试指南](guides/testing.md)、[CONTRIBUTING](../CONTRIBUTING.md) |

### 架构

| 关键词 | 文档位置 |
|--------|----------|
| 分层架构 | [系统架构](concepts/architecture.md)、[架构详解](architecture.md) |
| Widget 系统 | [Widget 系统](concepts/widget-system.md) |
| 数据流 | [系统架构](concepts/architecture.md) |
| 模块依赖 | [模块一览](reference/modules.md) |
| 设计决策 | [ADR-001](adr/001-pyqt5-choice.md)、[ADR-002](adr/002-sandbox-approach.md)、[ADR-003](adr/003-content-loading.md) |

### 安全

| 关键词 | 文档位置 |
|--------|----------|
| 代码沙箱 | [安全模型](concepts/security-model.md)、[ADR-002](adr/002-sandbox-approach.md) |
| AST 预检 | [安全模型](concepts/security-model.md)、[python_runner.py](../app/python_runner.py) |
| HTTPS | [安全模型](concepts/security-model.md)、[API 参考](reference/api-integration.md) |
| XSS 防护 | [安全模型](concepts/security-model.md) |
| 凭证存储 | [安全模型](concepts/security-model.md)、[credentials.py](../app/credentials.py) |

### 课程与练习

| 关键词 | 文档位置 |
|--------|----------|
| 课程结构 | [课程内容体系](concepts/content-system.md) |
| 添加课程 | [课程内容编写](guides/content-authoring.md)、[内容格式](reference/content-format.md) |
| 练习格式 | [练习创建](guides/exercise-creation.md)、[练习格式](reference/exercise-format.md) |
| 评测逻辑 | [练习创建](guides/exercise-creation.md) |
| course_map | [内容格式](reference/content-format.md) |
| exercises.json | [练习格式](reference/exercise-format.md) |

### 构建与发布

| 关键词 | 文档位置 |
|--------|----------|
| PyInstaller | [构建指南](guides/building.md)、[distribution](distribution.md) |
| 版本管理 | [distribution](distribution.md) |
| GitHub Actions | [distribution](distribution.md) |
| 发布流程 | [distribution](distribution.md) |

### AI 导师

| 关键词 | 文档位置 |
|--------|----------|
| AI 集成 | [AI 导师集成](concepts/ai-integration.md) |
| API 通信 | [API 参考](reference/api-integration.md) |
| 知识库 | [AI 导师集成](concepts/ai-integration.md) |
| 多会话管理 | [AI 导师指南](user-guide/ai-mentor-guide.md) |

### 用户指南

| 关键词 | 文档位置 |
|--------|----------|
| 仪表盘 | [仪表盘指南](user-guide/dashboard-guide.md) |
| 学习路径 | [学习指南](user-guide/learning-guide.md) |
| 练习中心 | [练习指南](user-guide/practice-guide.md) |
| AI 辅导 | [AI 导师指南](user-guide/ai-mentor-guide.md) |
| 融合项目 | [项目指南](user-guide/projects-guide.md) |
| 设置 | [设置指南](user-guide/settings-guide.md) |

---

## 按文件索引

| 文档 | 说明 |
|------|------|
| [README.md](../README.md) | 项目首页，功能概览和快速开始 |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | 贡献指南，开发环境和流程 |
| [CHANGELOG.md](../CHANGELOG.md) | 版本变更日志 |
| [FAQ.md](../FAQ.md) | 常见问题 |
| [项目说明.md](../项目说明.md) | 项目定位和详细说明 |
| [docs/README.md](README.md) | 文档中心索引 |
| [docs/architecture.md](architecture.md) | 架构详解 |
| [docs/comparison.md](comparison.md) | 同类产品对比 |
| [docs/distribution.md](distribution.md) | 构建与发布指南 |
| [docs/faq.md](faq.md) | 常见问题（文档版） |
| [docs/glossary.md](glossary.md) | 术语表 |
| [docs/troubleshooting.md](troubleshooting.md) | 故障排除指南 |
| [docs/user-guide.md](user-guide.md) | 用户使用指南 |
| [docs/improvement-plan.md](improvement-plan.md) | 改进计划 |
| [docs/maturity-plan.md](maturity-plan.md) | 成熟度计划 |
| [docs/features-showcase.md](features-showcase.md) | 功能展示 |
| [docs/security-audit.md](security-audit.md) | 安全审计报告 |
| [docs/accessibility.md](accessibility.md) | 无障碍功能文档 |
| [docs/learning-path.md](learning-path.md) | 学习路径文档 |
| [docs/skill-tree.md](skill-tree.md) | 技能树文档 |
