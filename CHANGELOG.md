# 更新日志

本文件记录 DevLearnerAI 项目的版本变更历史。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

---

## [1.1.0] - 2026-06-02

基于 v1.0.0 发布后的全面成熟度升级（Sprint 4-27），涵盖模块拆分、功能增强、安全加固、测试覆盖、UX 打磨与文档完善。

### 新功能

- **欢迎向导 (WelcomeWizard)** -- 5 步首次启动引导流程，帮助用户完成初始配置
- **功能导览 (Feature Tour)** -- 全屏聚光灯式交互功能介绍
- **设置检查清单 (SetupChecklist)** -- 仪表板环境检查与 API Key 配置引导，读取真实数据库状态
- **代码分析器 (Code Analyzer)** -- AI 驱动的 4 标签页代码分析面板（解释/审查/查错/复杂度）
- **渐进式提示系统 (Hint System)** -- 3 级渐进提示（概念/方法/伪代码），带延迟展示
- **学习推荐 (Learning Recommendations)** -- 下一课推荐、复习计划、薄弱点识别
- **分析工具模块 (Analytics)** -- 用户行为数据采集、数据库表、分析视图组件、周报
- **知识图谱 (KnowledgeGraph)** -- 力导向图可视化，展示知识节点与概念关系
- **自动标签 (AutoTagger)** -- AI 驱动的知识条目自动分类
- **RAG 上下文服务** -- AI 对话时自动注入相关知识库上下文
- **纯 QPainter 图表组件** -- 折线图、柱状图、雷达图、热力图，零外部依赖
- **i18n 国际化** -- 400+ 翻译键，中英文运行时切换
- **共享类型定义 (app/types.py)** -- Protocol 类、TypedDict 类、类型别名
- **练习提示按钮** -- 练习组件集成渐进式提示
- **课程代码解释按钮** -- 一键获取 AI 代码解释
- **AI 导师上下文帮助** -- 与 AI mentor 联动的上下文感知帮助

### 改进

- **模块拆分** -- `ai_mentor.py`（1230 行）拆为 `app/ai/` 包（api_client/chat_handler/markdown_renderer/models），`practice_service.py`（1301 行）拆为 `app/practice/` 包（evaluator/exercise_loader/models/normalizer）
- **数据外部化** -- 练习数据迁移至独立 JSON 文件
- **统一构建脚本** -- 整合 3 个构建脚本为 `scripts/build/build.py`，支持 release/dev/codex 三种变体
- **版本号单一来源** -- `pyproject.toml` 为唯一真相源，`config.py` 通过 `importlib.metadata` 动态读取
- **数据库优化** -- WAL 模式 + PRAGMA 调优（cache_size=-8000, temp_store=MEMORY, mmap_size=256MB）+ 15 个索引 + ANALYZE + 连接池
- **内容服务优化** -- 延迟加载 + LRU Markdown 缓存（64 条）+ 搜索索引 + 相邻预加载 + 内存压力驱逐
- **AI 通信优化** -- HTTPS 强制 + 请求去重 + 连接状态缓存 + 流式响应回退
- **性能监控** -- 慢操作追踪、IPC 通信跟踪、启动耗时插桩
- **结构化日志** -- `print()` 替换为 `logging` 模块 + RotatingFileHandler
- **WCAG AA 对比度修复** -- styles.py 颜色方案无障碍改进
- **键盘导航** -- Tab 顺序、快捷键、屏幕阅读器公告
- **死代码清理** -- 删除 styles/ 目录、services/、events.py、middleware.py、plugins.py、container.py（~3,920 行）
- **代码质量统一** -- Ruff format + Ruff check --fix，消除所有 lint 警告
- **测试断言修复** -- 66+ 个空断言测试补充为精确断言
- **仪表板增强** -- 交互式图表、目标设定、数据导出
- **跨平台路径处理** -- 修复 config.py 中的跨平台路径兼容

### 安全修复

- **Python 沙箱增强** -- AST 预检新增 `__import__`、`__class__`、`__bases__`、`__subclasses__`、`__mro__`、`__globals__`、`__builtins__` 拦截
- **SQL 安全加固** -- `ATTACH`/`DETACH` 拦截、SQL 注释剥离、危险 PRAGMA 过滤、5 秒执行超时
- **路径遍历防护** -- 文件路径验证、异常处理修复
- **凭证安全** -- keyring 跨平台支持 + base64 回退 + 文件权限限制（chmod 600）
- **HTML 净化** -- 协议相对 URL 过滤（`//`）、扩展 STRIP_TAGS 列表、事件处理器剥离
- **HTTPS 强制** -- AI API 通信拒绝 HTTP
- **资源限制** -- 输出 12KB 上限，执行 3 秒超时

### Bug 修复

- 修复数据库事务异常时未提交的问题
- 修复 widget 销毁后信号发射的线程安全问题
- 修复 safeStorage 明文回退警告
- 修复 bare except 和吞没异常
- 修复 AnalyticsCollector 缺失的数据库方法
- 修复 SQL 评测器未捕获 sqlite3.Warning 异常
- 修复多进程 spawn 编码问题
- 修复 CI 中 Python 3.9 兼容性（PEP 604 语法）
- 修复 CI 中 Windows 专属测试在 Linux 上的跳过
- 修复 ruff 版本锁定问题
- 修复测试断言位置偏移和字符串包含检查

### 测试

- 测试用例从 ~1,000 增长至 **1,334** 条
- 新增沙箱安全测试：嵌套函数、装饰器、生成器、async/await、元类、描述符
- 新增数据库边界测试：空操作、大数据集、并发写入、Unicode
- 新增内容解析测试：畸形 Markdown、大文件、BOM、混合编码
- 新增集成测试：learning_flow / practice_flow / database_flow / ai_flow
- CI 测试矩阵支持 Python 3.9 + 3.12

### 文档

- 新增 CONTRIBUTING.md 贡献指南
- 新增 CHANGELOG.md（Keep a Changelog 规范）
- README.md 添加 CI / Release / License / Tests 徽章
- 新增 `docs/` 文档体系：改进计划、成熟度计划、发布指南、功能展示、竞品对比
- 新增 demo 数据和学习路径文档

### 工程改进

- GitHub Actions CI（Python 3.9/3.12 矩阵、lint、format check、pytest）
- Ruff 统一 lint + format（替代 flake8 + isort + black）
- Makefile 封装开发命令
- PyInstaller 打包支持（.spec 自动生成）
- GitHub Actions Release 工作流
- pip-audit 安全审计集成

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
