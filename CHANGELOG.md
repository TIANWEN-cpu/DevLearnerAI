# 更新日志

本文件记录 DevLearnerAI 项目的版本变更历史。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

---

## [1.0.0] - 2026-06-02

DevLearnerAI 首个正式版本发布。基于 Python + PyQt5 + SQLite 构建的 AI 驱动桌面编程学习平台（v7.0）。

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
