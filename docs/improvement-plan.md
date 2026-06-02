# DevLearner AI 改进计划

> 基于深度审计报告，针对 `D:\codelearnhleper` 项目制定的系统性改进方案。

---

## 一、概述

本计划覆盖 **7 大领域、30+ 个改进项**，按优先级分为 P0（阻塞性/高风险）、P1（重要但非阻塞）、P2（优化建议）。改进工作建议分 4 个阶段执行，每阶段结束时进行回归验证，确保已有功能不受影响。

核心目标：

1. **消除版本碎片化**，建立单一版本来源
2. **拆分超大模块**，提升可维护性
3. **补齐关键 UX 缺失**（语法高亮、完成状态、快捷键）
4. **引入基础工程规范**（依赖声明、测试、日志、.gitignore）

---

## 二、优先级总览

| 优先级 | 数量 | 关键项 |
|--------|------|--------|
| P0 | 8 | 版本号统一、依赖声明、模块拆分、语法高亮、完成状态、文档版本、入口文件去重 |
| P1 | 14 | 构建脚本合并、路径硬编码、安全沙箱、测试、日志、性能优化、UX 增强 |
| P2 | 8+ | 代码复用、仪表盘闪烁、算法动画、阅读模式、文档补充、secrets 警告 |

---

## 三、改进项明细

### 阶段一：基础规范与版本治理（P0）

#### 3.1 统一版本号定义

- **目标**：消除 6.0 / 7.0 / 7.0_dashboard_textfix 等分散命名，建立单一版本来源
- **涉及文件**：
  - `app/config.py` — 作为版本号唯一定义处
  - `build_exe.py` — 读取 config 中的版本号
  - `build_dev_exe.py` — 同上
  - `build_codex_switcher_exe.py` — 同上
  - 所有 `.spec` 文件 — 通过 `datas` 或运行时读取
  - `项目说明.md` — 标题与实际版本同步
- **步骤**：
  1. 在 `app/config.py` 中新增 `APP_VERSION = "7.0"` 和 `BUILD_SUFFIX = ""`
  2. 各构建脚本通过 `importlib` 或正则从 `config.py` 读取版本号
  3. `.spec` 文件中的文件名引用统一使用变量替换
  4. 更新 `项目说明.md` 第 1 行标题，或将其合并到 `README.md` 后删除
- **风险**：低。纯配置变更，不影响运行时逻辑
- **收益**：发布流程不再出现版本号错乱，用户和开发者看到一致的版本信息

#### 3.2 新增依赖声明文件

- **目标**：保证环境可复现，为 CI 铺路
- **涉及文件**：
  - 新建 `requirements.txt`
  - 新建 `pyproject.toml`（可选，推荐）
  - `README.md` — 更新安装说明
- **步骤**：
  1. 盘点所有 `import` 语句，列出第三方依赖：PyQt5、mistune、Pygments、keyring、requests 等
  2. 确定各依赖最低兼容版本，生成 `requirements.txt`，示例：
     ```
     PyQt5>=5.15
     mistune>=3.0
     Pygments>=2.14
     keyring>=24.0
     requests>=2.28
     ```
  3. （推荐）创建 `pyproject.toml`，声明 `[project]` 元数据和 `[build-system]`
  4. 更新 README 安装段落，改为 `pip install -r requirements.txt`
- **风险**：低。不改变运行行为
- **收益**：新开发者可一键安装全部依赖；后续可接入 GitHub Actions 自动测试

#### 3.3 合并构建脚本

- **目标**：将三套功能重叠的构建脚本合并为一个统一入口
- **涉及文件**：
  - `build_exe.py`、`build_dev_exe.py`、`build_codex_switcher_exe.py` — 合并
  - 新建 `build.py`（或 `scripts/build.py`）
  - `build/`、`dist/` — 加入 `.gitignore`
- **步骤**：
  1. 新建 `build.py`，使用 `argparse` 支持 `--variant prod|dev|codex` 参数
  2. 将三套脚本的公共逻辑（PyInstaller 调用、图标设置、版本号注入）提取为共享函数
  3. 各 variant 的差异逻辑（入口文件、输出名、console 设置）用字典映射
  4. 旧脚本保留为薄包装（调用新脚本），或直接删除并在 README 中更新构建说明
- **风险**：中。需要逐一验证三个 variant 的打包产物是否正常运行
- **收益**：维护成本降低 2/3，新增 variant 只需添加配置项

#### 3.4 清理重复入口文件

- **目标**：消除 `main.py` 与 `dev_main.py` 完全相同的问题
- **涉及文件**：
  - `main.py` — 生产入口
  - `dev_main.py` — 开发入口
- **步骤**：
  1. 方案 A（推荐）：删除 `dev_main.py`，在 README 中统一入口为 `main.py`
  2. 方案 B：让 `dev_main.py` 设置 `LOG_LEVEL=DEBUG`、加载示例数据、启用开发者工具面板
  3. 更新构建脚本中的入口文件引用
- **风险**：低
- **收益**：消除困惑，新开发者不会不知道该运行哪个文件

#### 3.5 新增 .gitignore

- **目标**：排除构建产物、缓存和数据库文件
- **涉及文件**：
  - 新建 `.gitignore`
- **步骤**：
  1. 添加以下排除规则：
     ```
     build/
     dist/
     __pycache__/
     *.pyc
     *.spec
     *.db
     *.log
     .env
     ```
  2. 从版本控制中移除已跟踪的匹配文件（如有）
- **风险**：低
- **收益**：仓库更干净，减少不必要的文件冲突

---

### 阶段二：模块拆分与架构优化（P0 + P1）

#### 3.6 拆分 practice_service.py（1249 行）

- **目标**：将数据与逻辑分离，主文件缩减到 300 行以内
- **涉及文件**：
  - `app/services/practice_service.py` — 主逻辑
  - 新建 `content/metadata/exercise_fallbacks.json`
  - 新建 `content/metadata/sql_fixtures.json`
- **步骤**：
  1. 将 `EXERCISE_FALLBACKS` 字典（约 440 行）导出为 JSON 文件
  2. 将 `SQL_QUERY_FIXTURES`（约 320 行）导出为 JSON 文件
  3. `PracticeService.__init__()` 中用 `json.load()` 加载这两个文件
  4. 确保 JSON 文件路径使用 `Path(__file__).resolve().parent` 相对定位
  5. 运行所有练习功能验证数据完整性
- **风险**：中。需验证 JSON 序列化/反序列化不会丢失 Python 特有类型（如 tuple）
- **收益**：主文件可读性大幅提升；数据文件可被其他工具（如课程编辑器）直接使用

#### 3.7 拆分 ai_mentor.py（1224 行）

- **目标**：将上帝模块拆分为职责单一的子模块
- **涉及文件**：
  - `app/widgets/ai_mentor.py` — 当前单一文件
  - 新建 `app/widgets/mentor/_sanitize.py` — HTML 安全清洗
  - 新建 `app/widgets/mentor/_chat_engine.py` — API 调用与响应处理
  - 新建 `app/widgets/mentor/_session_panel.py` — 会话管理 UI
  - 新建 `app/widgets/mentor/_settings_panel.py` — 设置面板 UI
  - 新建 `app/widgets/mentor/mentor_widget.py` — 主组装层
  - 新建 `app/widgets/mentor/__init__.py`
- **步骤**：
  1. 创建 `mentor/` 包目录
  2. 按职责将类和函数迁移到对应子模块
  3. `mentor_widget.py` 中导入并组装各子模块
  4. 更新所有 `ai_mentor` 的外部导入路径（`window.py`、`main.py` 等）
  5. 逐步迁移，每拆一个模块运行一次完整功能测试
- **风险**：中高。涉及多处导入路径变更，需仔细排查所有引用
- **收益**：每个子模块可在 200-300 行内完成，修改定位时间缩短 70%

#### 3.8 修复 python_runner.py 中 os.chdir() 全局副作用

- **目标**：消除多线程竞态风险
- **涉及文件**：
  - `app/services/python_runner.py` — 第 203-228 行
- **步骤**：
  1. 将 `_execute_code_impl` 和 `_evaluate_code_impl` 中的 `os.chdir()` 替换为 `subprocess.run(cwd=workdir)` 方式
  2. 如果当前使用 `exec()` 而非 subprocess，则改为在单独线程中执行，线程内先 chdir 再执行
  3. 确保 `finally` 块中的路径恢复逻辑仍然存在（防御性编程）
- **风险**：中。需验证代码执行的输出捕获机制在新方案下仍然正常
- **收益**：消除竞态条件，提升多线程场景下的稳定性

#### 3.9 统一 SAFE_BUILTINS 定义

- **目标**：消除两份不一致的安全边界定义
- **涉及文件**：
  - `app/services/practice_service.py` — 第 18-40 行
  - `app/services/python_runner.py` — 第 120-149 行
- **步骤**：
  1. 以 `python_runner.py` 中更完整的版本为基准（包含 `isinstance`、`round`、异常类）
  2. 将 `SAFE_BUILTINS` 定义保留在 `python_runner.py`，导出为公开接口
  3. `practice_service.py` 中改为 `from .python_runner import SAFE_BUILTINS`
  4. 对比两份定义的差异，确认合并后不会破坏练习评测逻辑
- **风险**：低。需确认 practice_service 中缺少的 builtins 不影响已有练习
- **收益**：安全边界只维护一份，避免后续加固时遗漏

#### 3.10 优化数据库锁粒度

- **目标**：减少不必要的锁开销
- **涉及文件**：
  - `app/database.py` — 第 13-14 行
- **步骤**：
  1. 在连接初始化时添加 `PRAGMA journal_mode=WAL`
  2. 将 `_db_lock` 仅用于写操作（`execute` 中包含 INSERT/UPDATE/DELETE 时）
  3. 读操作（SELECT）不加锁，依赖 WAL 的并发读特性
  4. 保留 `_connection_lock` 用于连接生命周期管理
- **风险**：低。WAL 模式是 SQLite 推荐的并发方案
- **收益**：读操作不再串行等待，响应更流畅

#### 3.11 修复硬编码路径

- **目标**：消除 `rebuild_courses.py` 中的绝对路径硬编码
- **涉及文件**：
  - `rebuild_courses.py` — 第 10 行
  - `app/config.py` — 第 39 行 `LEGACY_DB_PATH`
- **步骤**：
  1. `rebuild_courses.py`：将 `BASE = r"D:\codelearnhleper\content"` 改为 `BASE = Path(__file__).resolve().parent / "content"`
  2. `config.py`：评估 `LEGACY_DB_PATH` 的使用场景，如已无需支持旧数据则删除；如需保留则在打包模式下跳过
- **风险**：低
- **收益**：任何开发者克隆仓库后即可直接运行所有脚本

---

### 阶段三：UX 增强（P0 + P1）

#### 3.12 课程内容语法高亮

- **目标**：代码块在课程浏览器中有背景色和等宽字体
- **涉及文件**：
  - `app/widgets/learn.py` — 第 30 行附近
- **步骤**：
  1. 启用 mistune 的 code highlight 插件：`mistune.create_markdown(plugins=['speed'])` 并配置 PygmentsRenderer
  2. 或手动为 `<pre><code>` 标签添加 inline CSS：
     ```python
     css = "pre { background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 6px; font-family: Consolas, monospace; }"
     ```
  3. 在 `QTextBrowser` 的 HTML 头部注入该 CSS
  4. 验证多语言代码块（Python、SQL、JavaScript）的高亮效果
- **风险**：低
- **收益**：课程可读性大幅提升，代码示例一目了然

#### 3.13 课程列表显示完成状态

- **目标**：用户在课程列表中一眼看出学习进度
- **涉及文件**：
  - `app/widgets/learn.py` — `_refresh_browser()` 方法
- **步骤**：
  1. 在 `_refresh_browser()` 中查询 `db.lesson_status(lesson_id)`
  2. 在卡片 meta 行追加状态指示：
     - 已完成：绿色圆点 + "已完成"
     - 进行中：黄色圆点 + "进行中"
     - 未开始：灰色圆点 + "未开始"
  3. 列表排序调整为"未完成优先"
  4. 已完成课程使用半透明样式以区分
- **风险**：低。依赖已有的 `db.lesson_status()` API
- **收益**：用户能快速定位待学习内容，提升学习效率

#### 3.14 练习页面显示完成状态

- **目标**：练习卡片标记已通过的题目
- **涉及文件**：
  - `app/widgets/practice.py` — `refresh_exercises()` 方法
- **步骤**：
  1. 查询每道练习的历史记录（通过/未通过/未尝试）
  2. 在卡片标题旁添加状态标记
  3. 筛选器增加"仅显示未通过"选项
  4. 统计并显示当前 track 的通过率
- **风险**：低
- **收益**：用户能有针对性地练习薄弱题目

#### 3.15 增强代码编辑器

- **目标**：补充行号显示和 Tab 处理等基础功能
- **涉及文件**：
  - `app/widgets/practice.py` — 第 272-288 行
- **步骤**：
  1. 实现 `LineNumberArea` 组件（继承 `QWidget`），绑定到编辑器的 `blockCountChanged` 和 `updateRequest` 信号
  2. 添加 Tab 键处理：将 Tab 转换为 4 个空格
  3. 添加基本的自动缩进：回车后保持上一行缩进级别
  4. （可选）后续可考虑括号匹配高亮
- **风险**：低
- **收益**：编辑体验接近轻量级 IDE，降低用户跳出应用的概率

#### 3.16 补充快捷键绑定

- **目标**：为常用操作添加键盘快捷键
- **涉及文件**：
  - `app/widgets/window.py` — 快捷键绑定区域
  - `app/widgets/learn.py` — 课程切换
  - `app/widgets/practice.py` — 提交判题
- **步骤**：
  1. `Ctrl+S` — 保存笔记
  2. `F5` — 运行代码
  3. `Ctrl+Enter` — 提交判题 / 标记课程完成
  4. `Ctrl+]` / `Ctrl+[` — 下一课 / 上一课
  5. `Ctrl+Shift+P` — 打开命令面板（如有）
  6. 在帮助菜单或状态栏提示可用快捷键
- **风险**：低
- **收益**：高级用户可完全键盘操作，效率提升显著

#### 3.17 改善 AI 错误提示

- **目标**：区分不同类型的连接错误，给出针对性提示
- **涉及文件**：
  - `app/widgets/ai_mentor.py` — 第 884 行附近
- **步骤**：
  1. 捕获 `requests.exceptions.SSLError` — 提示"SSL 证书验证失败，请检查 HTTPS 配置"
  2. 捕获 `requests.exceptions.Timeout` — 提示"连接超时，请检查网络或增加超时时间"
  3. 捕获 `requests.exceptions.ConnectionError` — 提示"无法连接到服务器，请检查 Host 地址"
  4. 捕获 HTTP 401/403 — 提示"API Key 无效或已过期"
  5. 保留通用异常兜底，但附带原始错误信息
  6. 在保存配置时即校验 HTTPS（而不仅在测试连接时）
- **风险**：低
- **收益**：用户遇到问题时能自助排查，减少技术支持负担

#### 3.18 修复仪表盘"加载中"闪烁

- **目标**：首次启动时显示有意义的内容
- **涉及文件**：
  - `app/widgets/dashboard.py` — 第 62 行
- **步骤**：
  1. 在 `__init__` 末尾直接调用 `self.refresh()`
  2. 或将初始文案从"加载中..."改为应用名和版本号
- **风险**：极低
- **收益**：消除首次启动的不专业感

---

### 阶段四：性能优化与工程完善（P1 + P2）

#### 3.19 ContentService 懒加载

- **目标**：减少启动延迟
- **涉及文件**：
  - `app/services/content_service.py` — 第 77 行
- **步骤**：
  1. `_discover_tracks()` 只解析顶层 track 列表（id、title、icon、描述）
  2. modules 和 lessons 数据延迟到用户选择 track 时才通过 `_load_track()` 加载
  3. 添加 LRU 缓存，避免重复加载已访问的 track
- **风险**：低。需确保 UI 层在数据加载完成前显示占位状态
- **收益**：启动时间随课程数量增长保持线性可控

#### 3.20 PracticeService 分组加载

- **目标**：避免一次性加载全部练习到内存
- **涉及文件**：
  - `app/services/practice_service.py` — 第 839 行
- **步骤**：
  1. 将 `self.exercises` 从全量列表改为按 `track_id` 索引的字典
  2. 实现 `_load_exercises_for_track(track_id)` 方法
  3. 首次访问某 track 时才加载对应练习
- **风险**：低
- **收益**：内存占用降低，练习数量扩展不受瓶颈限制

#### 3.21 AI System Prompt 缓存

- **目标**：避免每次发送消息都重建完整的 system context
- **涉及文件**：
  - `app/widgets/ai_mentor.py` — 第 1099-1113 行
- **步骤**：
  1. 缓存 `_build_system_context()` 的返回值
  2. 仅在以下场景清除缓存：设置变更、知识库更新、课程切换
  3. 使用 `@lru_cache` 或手动的 dirty flag 机制
- **风险**：低。需确保缓存失效逻辑覆盖所有变更场景
- **收益**：每次消息发送减少一次数据库查询和文件遍历

#### 3.22 提取 widget 公共代码

- **目标**：消除 learn.py、practice.py、projects.py 中的重复代码
- **涉及文件**：
  - `app/widgets/learn.py`、`app/widgets/practice.py`、`app/widgets/projects.py`
  - 新建 `app/widgets/_common.py`
- **步骤**：
  1. 提取 `_surface_panel()` 到 `_common.py` 的 `surface_panel()` 函数
  2. 提取卡片样式渲染逻辑为 `CardMixin` 类
  3. 提取列表项选择高亮刷新为 `SelectableListMixin` 类
  4. 各 widget 通过继承或组合方式复用
- **风险**：低
- **收益**：样式修改只需改一处，三个页面自动同步

#### 3.23 补充自动测试

- **目标**：为核心服务建立测试保护网
- **涉及文件**：
  - 新建 `tests/` 目录
  - 新建 `tests/test_practice_service.py`
  - 新建 `tests/test_python_runner.py`
  - 新建 `tests/test_database.py`
  - 新建 `tests/conftest.py`
- **步骤**：
  1. 搭建 pytest 测试框架，配置 `conftest.py` 提供临时数据库 fixture
  2. **python_runner 安全测试**（最高优先级）：
     - 验证 `import os` 被拦截
     - 验证 `open()` 被拦截
     - 验证 `__import__` 被拦截
     - 验证允许的 builtins 正常可用
  3. **practice_service 评测测试**：
     - 验证各题型（选择、填空、代码）的评测逻辑
     - 验证 fallback 数据加载正确
  4. **database 迁移测试**：
     - 验证新建数据库的表结构正确
     - 验证旧版本数据库迁移后数据完整
  5. 配置 GitHub Actions CI，在 push 时自动运行测试
- **风险**：中。需要构造测试数据和 mock 环境
- **收益**：防止回归 bug，提升重构信心，为后续开发加速

#### 3.24 配置日志文件输出

- **目标**：将日志同时写入文件，方便排查问题
- **涉及文件**：
  - `main.py` — 第 6 行
  - `app/config.py` — `LOG_DIR` 定义（已存在但未使用）
- **步骤**：
  1. 在 `main.py` 中配置 `RotatingFileHandler`，输出到 `LOG_DIR / "app.log"`
  2. 设置日志轮转：单文件最大 5MB，保留 3 个备份
  3. 格式包含时间戳、模块名、级别、消息
  4. 在"关于"页面或设置中提供"打开日志目录"按钮
- **风险**：极低
- **收益**：用户反馈问题时可直接提供日志文件，定位效率提升

#### 3.25 整理项目根目录

- **目标**：降低新开发者的认知负担
- **涉及文件**：
  - `rebuild_courses.py`、`rebuild_part*.py` — 移入 `scripts/`
  - `*.spec` 文件 — 移入 `packaging/`
  - `codexgame/`、`plan/` — 评估是否保留或归档
- **步骤**：
  1. 创建 `scripts/` 目录，将所有 rebuild 脚本移入
  2. 创建 `packaging/` 目录，将 `.spec` 文件移入
  3. 更新构建脚本中的相对路径引用
  4. 评估 `codexgame/` 和 `plan/` 是否仍有价值，无价值则删除
  5. 清理已有的 `__pycache__` 目录
- **风险**：低。需更新引用路径
- **收益**：根目录文件数从 30+ 减少到 10 以内，项目结构清晰

#### 3.26 文档安全描述修正

- **目标**：README 中的安全描述与实际实现一致
- **涉及文件**：
  - `README.md` — 第 125 行附近
- **步骤**：
  1. 将"数据库线程安全：使用 threading.Lock"改为更准确的描述
  2. 如已实施 3.10（WAL 优化），更新为"使用 SQLite WAL 模式配合写操作锁"
- **风险**：极低
- **收益**：文档可信度提升

#### 3.27 补充项目文档

- **目标**：为开发者提供入门指南
- **涉及文件**：
  - 新建 `docs/architecture.md`
  - 新建 `docs/dev-setup.md`
  - 新建 `docs/content-guide.md`
- **步骤**：
  1. `architecture.md`：描述分层架构（数据层 database.py / 服务层 *_service.py / 展示层 widgets/）、模块依赖关系、数据流向
  2. `dev-setup.md`：环境搭建步骤、依赖安装、运行方式、构建方式、测试方式
  3. `content-guide.md`：如何添加新课程 track、如何编写练习题、课程 Markdown 格式规范
- **风险**：极低
- **收益**：新开发者上手时间从数小时缩短到 30 分钟

#### 3.28 secrets 安全提示

- **目标**：在 fallback 存储路径下降低安全风险
- **涉及文件**：
  - `app/credentials.py` — 第 91-95 行
- **步骤**：
  1. 在 fallback 路径写入前弹出警告对话框，告知用户安全性降低
  2. 在文件头部添加注释说明这不是加密存储
  3. （推荐）引导用户安装 keyring 以获得更好的安全性
- **风险**：极低
- **收益**：用户对 API Key 存储安全性有清晰认知

---

## 四、执行顺序建议

```
阶段一（第 1-2 周）：基础规范
  3.1  版本号统一      ─┐
  3.2  依赖声明         ├─ 可并行
  3.5  .gitignore       ─┘
  3.4  入口文件去重     ── 依赖 3.1
  3.3  构建脚本合并     ── 依赖 3.1

阶段二（第 3-5 周）：架构优化
  3.9  SAFE_BUILTINS 统一   ── 可立即开始
  3.11 硬编码路径修复        ── 可立即开始
  3.8  os.chdir 修复         ── 可立即开始
  3.10 数据库锁优化          ── 可立即开始
  3.6  practice_service 拆分  ── 依赖 3.9
  3.7  ai_mentor 拆分         ── 独立，工作量最大

阶段三（第 5-7 周）：UX 增强
  3.12 语法高亮              ── 可立即开始
  3.13 课程完成状态           ── 可立即开始
  3.14 练习完成状态           ── 可立即开始
  3.18 仪表盘闪烁修复         ── 可立即开始
  3.17 AI 错误提示            ── 可立即开始
  3.15 编辑器增强             ── 可立即开始
  3.16 快捷键补充             ── 可立即开始

阶段四（第 7-10 周）：工程完善
  3.23 自动测试              ── 最高优先级，应尽早开始
  3.24 日志文件输出           ── 可立即开始
  3.19 ContentService 懒加载  ── 可立即开始
  3.20 PracticeService 分组   ── 依赖 3.6
  3.21 System Prompt 缓存     ── 可立即开始
  3.22 Widget 公共代码        ── 可立即开始
  3.25 根目录整理             ── 可立即开始
  3.26 文档修正               ── 可立即开始
  3.27 补充文档               ── 依赖其他改进完成后
  3.28 secrets 警告           ── 可立即开始
```

> **特别说明**：3.23（自动测试）虽然排在阶段四，但建议**从阶段二开始就同步编写测试**。每次拆分或修改模块时，先写测试再改代码，确保重构不引入回归。

---

## 五、不在本次范围的后续建议

以下改进项有价值但超出当前审计范围，记录供后续规划参考：

1. **课程编辑器 GUI**：提供可视化课程创建和编辑工具，降低内容贡献门槛
2. **多语言支持（i18n）**：当前 UI 全部硬编码中文，如需国际化需引入 Qt 翻译机制
3. **插件系统**：允许第三方扩展练习类型、算法动画、AI Provider
4. **云端同步**：学习进度和设置的云端备份与多设备同步
5. **CI/CD 流水线**：GitHub Actions 自动测试、自动打包发布、自动更新检测
6. **算法动画扩展**：与课程体系对齐，支持二分查找、图遍历、动态规划等更多算法
7. **侧边阅读模式**：替代模态 `ReaderDialog`，允许同时对照编辑器或 AI 面板
8. **性能监控埋点**：收集启动时间、页面切换耗时等指标，指导后续优化
9. **用户反馈通道**：在应用内集成问题报告功能，附带自动日志上传
10. **accessibility（无障碍）**：键盘导航、屏幕阅读器支持、高对比度主题

---

*本计划基于 2026 年 6 月的深度审计报告制定，建议每完成一个阶段后重新评估优先级。*
