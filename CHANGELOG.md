# 更新日志

本文件记录 DevLearnerAI 项目的版本变更历史。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

---

## [1.1.0] - 2026-06-02

基于 v1.0.0 的全面成熟度升级，涵盖架构重构、测试覆盖、工程化改进和文档完善。

### Features

- **模块拆分** -- 将 `ai_mentor.py`（1230 行）拆分为 `app/ai/` 包（api_client / chat_handler / markdown_renderer / models），将 `practice_service.py`（1301 行）拆分为 `app/practice/` 包（evaluator / exercise_loader / models / normalizer），保持向后兼容
- **数据外部化** -- 新增 `exercise_fallbacks.json` 和 `sql_query_fixtures.json`，将硬编码练习数据迁移至独立 JSON 文件
- **统一构建脚本** -- 整合 `build_exe.py`、`build_dev_exe.py`、`build_codex_switcher_exe.py` 为 `scripts/build/build.py`，支持 release / dev / codex 三种变体，自动生成 `.spec` 文件
- **版本号单一来源** -- `pyproject.toml` 的 `version` 字段为唯一真相源，`app/config.py` 通过 `importlib.metadata` 动态读取
- **CONTRIBUTING.md** -- 添加完整的贡献指南，包含开发环境搭建、分支策略、PR 流程和代码规范

### Improvements

- 引入 Ruff 统一完成 lint 与格式化（替代 flake8 + isort + black）
- 添加 `Makefile` 封装 lint / format / test / coverage / build 命令
- 添加 `pyproject.toml` 声明项目元数据、工具配置（ruff / pytest / coverage）
- 添加 `requirements.txt` 和 `requirements-dev.txt` 明确依赖
- GitHub Actions CI 支持 Python 3.9 + 3.12 矩阵测试
- CI 覆盖率报告并设最低阈值（40%）
- SQLite WAL 模式优化，提升并发读取性能
- 数据库连接池化，提升访问性能
- 内容服务延迟加载，减少启动耗时
- `print()` 调用替换为结构化日志（`logging` 模块 + RotatingFileHandler）
- 硬编码路径改为 `Path(__file__).resolve().parent` 相对定位
- PyQt5 命名约定的 Ruff lint 忽略规则（N801 / N802 / N815）

### Bug Fixes

- 修复数据库事务异常时未提交的问题
- 修复 widget 销毁后信号发射的线程安全问题
- 移除 CI 中未使用的 import 和格式化问题
- 移除 `getattr` 白名单中的潜在逃逸路径，增强 AST 校验
- 整理重复的 `SAFE_BUILTINS` 定义，统一使用 `python_runner` 模块
- 清理根目录冗余的构建脚本（`build_exe.py` 等 3 个文件）

### Documentation

- 添加 CHANGELOG.md 并采用 Keep a Changelog 规范
- README.md 添加 CI / Release / License 徽章
- 添加 `docs/improvement-plan.md` 改进路线图
- 添加 `docs/maturity-plan.md` 成熟度计划
- 添加 `docs/distribution.md` 构建与发布指南

### Testing

- 测试用例从 0 增长至 **1000+** 条
- 沙箱安全测试：`test_python_runner.py` / `test_python_runner_extended.py` / `test_python_runner_extra.py` / `test_python_runner_subprocess.py`
- 数据库测试：`test_database.py` / `test_database_extended.py` / `test_database_extra.py` / `test_database_coverage.py` / `test_database_stress.py`
- 评测逻辑测试：`test_practice_service.py` / `test_practice_service_extended.py` / `test_practice_service_extra.py`
- AI 模块测试：`test_ai_chat_handler.py` / `test_ai_package.py` / `test_api_client_extended.py` / `test_chat_handler_extended.py` / `test_markdown_renderer_extended.py`
- 内容与凭证测试：`test_content_service.py` / `test_content_service_extended.py` / `test_credentials.py`
- 集成测试：`test_integration_learning_flow.py` / `test_integration_practice_flow.py` / `test_integration_database_flow.py` / `test_integration_ai_flow.py`
- 安全测试：`test_security_sandbox_escape.py`
- 边界与压力测试：`test_edge_cases.py` / `test_content_parsing_edge_cases.py` / `test_evaluator_extended.py` / `test_exercise_loader_extended.py`
- 配置测试：`test_config_extended.py`

---

## [1.0.0] - 2026-06-02

DevLearnerAI 首个正式版本发布。基于 Python + PyQt5 + SQLite 构建的 AI 驱动桌面编程学习平台。

### 核心功能

- **AI 智能导师** -- 支持 OpenAI 兼容 API 的对话式编程辅导，可切换不同端点和模型，附带上下文感知知识库
- **代码执行沙箱** -- 安全执行 Python / C / C++ / C# / SQL 代码，通过 AST 预检和危险内置函数限制保障运行安全
- **课程体系** -- 涵盖 Python、C、C++、C#、数据库、算法等多个技术栈，Markdown 格式组织，支持语法高亮渲染
- **交互式练习** -- 编程练习与自动评测，配合练习中心进行针对性训练
- **融合项目** -- 从单点知识走向可交付的真实项目，培养工程实践能力
- **算法动画** -- 将排序、查找等经典算法步骤可视化
- **学习仪表盘** -- 学习进度追踪、课程完成统计、每日学习概览
- **Codex 账号切换器** -- 快速切换 Codex 账号配置

### 安全加固

- Python 代码执行沙箱通过 AST 预检拦截危险代码，限制 `os.system`、`subprocess`、`eval`、`exec` 等危险内置函数
- 移除 `getattr` 白名单中的潜在逃逸路径，增强 AST 校验
- 使用 keyring 库将 API 密钥存储在系统凭证管理器中（跨平台兼容）
- AI API 通信强制 HTTPS，启用 TLS 证书验证，覆盖所有 HTTP 请求路径
- 数据库添加 `threading.Lock` 保证多线程访问安全
- 数据库启用 `PRAGMA journal_mode = WAL` 提升并发读取性能
- SQL 执行添加资源限制
- Markdown 渲染后对 HTML 进行净化处理，移除危险标签，防止 XSS 注入
- 错误信息对用户隐藏内部技术细节

### 工程改进

- 版本号统一为单一来源（`config.py` 中 `APP_VERSION`），消除多处硬编码
- 移除重复的 `SAFE_BUILTINS` 定义，统一使用 `python_runner` 模块
- 数据库实现连接池化，提升访问性能
- 内容服务实现延迟加载，减少启动耗时
- `print()` 调用替换为结构化日志（`logging` 模块 + RotatingFileHandler）
- 硬编码路径改为 `Path(__file__).resolve().parent` 相对定位
- 修复数据库事务异常时未提交的问题
- 修复 widget 销毁后信号发射的线程安全问题
- 引入 Ruff 统一完成 lint 与格式化（替代 flake8 + isort + black）
- 引入 pytest 单元测试框架，覆盖沙箱安全、数据库操作、评测逻辑
- 添加 GitHub Actions CI 工作流（lint、format check、pytest，支持 Python 3.9 + 3.12）
- 添加 `pyproject.toml` 声明项目元数据与工具配置
- 添加 `requirements.txt` 明确运行时依赖
- 添加 `Makefile` 封装开发常用命令
