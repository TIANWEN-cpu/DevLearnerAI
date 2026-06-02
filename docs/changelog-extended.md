# 完整更新日志

本文档为 DevLearnerAI 的详细更新日志，包含每个版本的完整变更记录。简要版本请参阅 [CHANGELOG.md](../CHANGELOG.md)。

---

## v1.1.0 (2026-06-02)

### 架构重构

- **ai_mentor.py 拆分**: 将 1230 行的单体文件拆分为 `app/ai/` 包
  - `api_client.py` -- API 通信（HTTPS、SSL、URL 构建）
  - `chat_handler.py` -- 对话 UI（AIMentorPanel、AIMentorDock）
  - `markdown_renderer.py` -- Markdown 渲染 + HTML 净化
  - `models.py` -- 数据类和安全常量
- **practice_service.py 拆分**: 将 1301 行的单体文件拆分为 `app/practice/` 包
  - `evaluator.py` -- 评测逻辑（SQL、关键字、Python）
  - `exercise_loader.py` -- 练习数据加载与回退
  - `models.py` -- Exercise / EvaluationResult 数据类
  - `normalizer.py` -- 结果集标准化
- 保持向后兼容：旧的 `app/ai_mentor.py` 和 `app/practice_service.py` 保留为薄包装层

### 数据外部化

- `EXERCISE_FALLBACKS` 字典（~450 行）导出为 `content/metadata/exercise_fallbacks.json`
- `SQL_QUERY_FIXTURES` 字典（~320 行）导出为 `content/metadata/sql_query_fixtures.json`
- PracticeService 改为运行时 JSON 加载

### 构建系统

- 统一构建脚本 `scripts/build/build.py`，支持三种变体：
  - `release` -- 正式发布版
  - `dev` -- 开发调试版
  - `codex` -- Codex 账号切换器
- 自动生成 `.spec` 文件
- `Makefile` 新增 `build-release` / `build-dev` / `build-codex` 目标
- 版本号单一来源：`pyproject.toml` 的 `version` 字段

### 工程改进

- 引入 Ruff 统一 lint + format（替代 flake8 + isort + black）
- 添加 `pyproject.toml` 声明项目元数据和工具配置
- 添加 `requirements.txt` 和 `requirements-dev.txt`
- `print()` 替换为 `logging` 模块 + RotatingFileHandler
- 硬编码路径改为 `Path(__file__).resolve().parent` 相对定位
- SQLite WAL 模式优化
- 数据库连接池化
- 内容服务延迟加载

### 测试

- 测试用例从 0 增长至 **1000+** 条
- 沙箱安全测试（4 个文件）
- 数据库测试（5 个文件）
- 评测逻辑测试（3 个文件）
- AI 模块测试（5 个文件）
- 内容与凭证测试（3 个文件）
- 集成测试（4 个文件）
- 安全测试（1 个文件）
- 边界与压力测试（4 个文件）

### 文档

- 新增 CHANGELOG.md（Keep a Changelog 规范）
- 新增 CONTRIBUTING.md（完整贡献指南）
- 新增 docs/improvement-plan.md（改进路线图）
- 新增 docs/maturity-plan.md（成熟度计划）
- 新增 docs/distribution.md（构建与发布指南）
- 新增 docs/architecture.md（架构说明）
- 新增 docs/faq.md（常见问题）
- README.md 添加 CI / Release / License / Tests / Coverage 徽章

### CI/CD

- GitHub Actions CI（lint + test，Python 3.9 + 3.12 矩阵）
- GitHub Actions Release（自动构建 + GitHub Release）
- GitHub Actions Security Audit（依赖安全审计）
- CI 覆盖率报告，最低阈值 40%

### Bug 修复

- 修复数据库事务异常时未提交的问题
- 修复 widget 销毁后信号发射的线程安全问题
- 移除 `getattr` 白名单中的潜在逃逸路径
- 整理重复的 `SAFE_BUILTINS` 定义
- 清理根目录冗余的构建脚本（3 个文件）

---

## v1.0.0 (2026-06-02)

### 首次正式发布

DevLearnerAI 首个正式版本。基于 Python + PyQt5 + SQLite 构建的 AI 驱动桌面编程学习平台。

### 核心功能

- **AI 智能导师**: 支持 OpenAI 兼容 API 的对话式编程辅导
- **代码执行沙箱**: 安全执行 Python / C / C++ / C# / SQL 代码
- **课程体系**: 涵盖 Python、C、C++、C#、数据库、算法等多个技术栈
- **交互式练习**: 176 道编程练习与自动评测
- **融合项目**: 10 个真实项目，培养工程实践能力
- **算法动画**: 排序、查找等经典算法步骤可视化
- **学习仪表盘**: 学习进度追踪、课程完成统计、每日学习概览

### 安全

- Python 代码执行沙箱 AST 预检
- API 密钥存储在系统凭证管理器
- AI API 通信强制 HTTPS
- 数据库 threading.Lock 线程安全
- Markdown 渲染 HTML 净化
- 输出 12KB 上限，执行 3 秒超时

### 工程

- GitHub Actions CI（Python 3.9 + 3.12 矩阵）
- pytest 单元测试框架
- Ruff linter + formatter
- pyproject.toml 项目元数据
- Makefile 开发命令
