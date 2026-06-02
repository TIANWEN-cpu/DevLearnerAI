# DevLearnerAI 成熟度改进计划

**项目路径**: `D:\codelearnhleper`
**制定日期**: 2026-06-02
**目标**: 从当前综合得分 5.75/10 提升至 8+/10

---

## 一、当前成熟度评分

| 维度 | 当前得分 | 目标得分 | 差距 | 优先级 |
|------|---------|---------|------|--------|
| Build/Release | 4/10 | 8/10 | -4 | P0 |
| 测试 | 5/10 | 8/10 | -3 | P0/P1 |
| DX（开发者体验） | 5/10 | 8/10 | -3 | P1 |
| 代码质量 | 6/10 | 8/10 | -2 | P0/P1 |
| 文档 | 6/10 | 8/10 | -2 | P1 |
| 架构 | 6/10 | 8/10 | -2 | P1/P2 |
| UX/Polish | 7/10 | 8/10 | -1 | P2 |
| 安全 | 7/10 | 8/10 | -1 | P2 |
| **综合** | **5.75/10** | **8/10** | **-2.25** | -- |

---

## 二、P0 阻塞发布（本次会话可实施）

### P0-1: 清理状态栏原型文案

- **目标**: 删除发布版本中不应出现的原型标识文案
- **涉及文件**: `app/window.py`（第 98 行附近）
- **步骤**:
  1. 定位 `window.py` 中状态栏硬编码的 `"v7.0 正在把原型收成正式产品"` 文案
  2. 替换为正式版本信息，如 `"v7.0"` 或从 `config.APP_VERSION` 动态读取
- **风险**: 无，纯文案修改
- **预期收益**: 消除发布版本中的原型痕迹，提升产品专业感

### P0-2: 将 practice_service.py 中的硬编码数据外部化

- **目标**: 将 ~770 行硬编码练习数据从 Python 代码中移出，实现数据与逻辑分离
- **涉及文件**:
  - `app/practice_service.py`（`EXERCISE_FALLBACKS` ~450 行 + `SQL_QUERY_FIXTURES` ~320 行）
  - 新建 `content/metadata/exercise_fallbacks.json`
  - 新建 `content/metadata/sql_query_fixtures.json`
- **步骤**:
  1. 提取 `EXERCISE_FALLBACKS` 字典为 `content/metadata/exercise_fallbacks.json`
  2. 提取 `SQL_QUERY_FIXTURES` 字典为 `content/metadata/sql_query_fixtures.json`
  3. 在 `practice_service.py` 中添加 JSON 加载函数（带缓存）
  4. 将原字典引用替换为加载函数调用
  5. 运行现有测试确认无回归
- **风险**: 中等。需确保 JSON 序列化/反序列化与原字典完全等价，特别注意嵌套结构和数据类型
- **预期收益**: `practice_service.py` 从 1,132 行缩减至 ~360 行，数据可独立编辑和版本管理

### P0-3: 创建 CI 流水线

- **目标**: 建立自动化的 lint + test + coverage 流水线
- **涉及文件**:
  - 新建 `.github/workflows/ci.yml`
- **步骤**:
  1. 创建 `.github/workflows/` 目录
  2. 编写 `ci.yml`，包含:
     - 触发条件: push 到 main, PR 到 main
     - Python 版本矩阵: 3.9 / 3.12
     - 步骤: 安装依赖 -> `ruff check` -> `ruff format --check` -> `pytest --cov`
  3. 更新 README 中的 CI badge 链接指向正确的工作流
- **风险**: 低。首次运行可能因测试环境差异暴露问题，需逐步修复
- **预期收益**: 每次提交自动验证代码质量，防止回归

### P0-4: 统一版本号管理

- **目标**: 消除版本号在多处硬编码的不一致问题
- **涉及文件**:
  - `app/config.py`（`APP_VERSION`）
  - `pyproject.toml`（`version`）
  - `CHANGELOG.md`（当前显示 `[1.0.0]`，应为 `[7.0.0]`）
  - `build_exe.py`、`build_dev_exe.py`、`build_codex_switcher_exe.py` 中的版本引用
- **步骤**:
  1. 确定单一版本来源（建议使用 `pyproject.toml` 作为源头）
  2. 在 `config.py` 中通过 `importlib.metadata` 读取版本号
  3. 更新 `CHANGELOG.md` 头部版本号为 `7.0.0`
  4. 确保三个构建脚本引用同一版本来源
- **风险**: 低。需确认 PyInstaller 打包后 `importlib.metadata` 可正常工作
- **预期收益**: 版本号单一来源，一处修改全局生效

### P0-5: 清理根目录冗余脚本

- **目标**: 整理根目录散落的脚本文件，改善项目结构
- **涉及文件**:
  - `rebuild_courses.py`
  - `rebuild_part1.py` ~ `rebuild_part5.py`
  - `build_exe.py`
  - `build_dev_exe.py`
  - `build_codex_switcher_exe.py`
  - `dev_main.py`
  - `codex_switcher_main.py`
- **步骤**:
  1. 创建 `scripts/` 目录
  2. 将 `rebuild_*.py` 移入 `scripts/rebuild/`
  3. 将 `build_*.py` 移入 `scripts/build/`（或合并为一个参数化脚本）
  4. 更新 `Makefile` 和文档中的路径引用
  5. 更新 `.gitignore` 如有需要
- **风险**: 中等。需检查是否有其他文件或工具引用这些脚本路径
- **预期收益**: 根目录从 17 个 Python 文件缩减至核心入口文件，结构清晰

---

## 三、P1 发布后 1 个月内

### P1-1: 拆分 ai_mentor.py 上帝类

- **目标**: 将 1,230 行的单体文件拆分为职责单一的模块
- **涉及文件**:
  - `app/ai_mentor.py` -> 拆分为:
    - `app/ai/mentor_view.py`（UI 构建，~300 行）
    - `app/ai/mentor_service.py`（业务逻辑：会话管理、知识库、系统上下文构建）
    - `app/ai/api_client.py`（HTTP 请求：`_chat_worker`、`_test_connection_worker`）
    - `app/ai/mentor_panel.py`（主入口，组合上述模块，暴露公开 API）
- **步骤**:
  1. 分析 `AIMentorPanel` 类的依赖关系图
  2. 提取 API 客户端层（无 UI 依赖，最易分离）
  3. 提取服务层（会话管理、知识库操作）
  4. 剩余 UI 代码保留在视图层
  5. 逐步迁移，每步运行测试验证
- **风险**: 中等。PyQt5 信号/槽连接需要在拆分后保持一致，需仔细处理跨模块引用
- **预期收益**: 每个模块 <400 行，职责清晰，可独立测试

### P1-2: 合并构建脚本

- **目标**: 将三个高度重复的 PyInstaller 构建脚本合并为一个参数化脚本
- **涉及文件**:
  - `scripts/build/build_exe.py`（或 `scripts/build/build.py`）
  - 删除原 `build_dev_exe.py`、`build_codex_switcher_exe.py`
  - 更新 `Makefile`
- **步骤**:
  1. 分析三个脚本的差异点（入口文件、spec 文件、输出名称）
  2. 设计参数化接口（argparse），支持 `--mode dev|prod|switcher`
  3. 实现统一脚本
  4. 更新 Makefile 添加对应 target
- **风险**: 低。PyInstaller 配置差异有限，合并逻辑简单
- **预期收益**: 消除代码重复，构建流程统一

### P1-3: 补充文档

- **目标**: 完善项目文档体系
- **涉及文件**:
  - 新建 `CONTRIBUTING.md`
  - 新建 `.github/ISSUE_TEMPLATE/bug_report.md`
  - 新建 `.github/ISSUE_TEMPLATE/feature_request.md`
  - 新建 `.github/PULL_REQUEST_TEMPLATE.md`
  - 新建 `docs/architecture.md`（架构说明）
  - 更新 `README.md`（添加截图）
- **步骤**:
  1. 编写 `CONTRIBUTING.md`（开发环境搭建、分支策略、PR 流程、代码审查标准）
  2. 创建 GitHub Issue/PR 模板
  3. 编写架构文档（模块职责、数据流图、扩展点说明）
  4. 截取应用截图添加到 README
  5. 在 README 中引用 `项目说明.md`
- **风险**: 无，纯文档工作
- **预期收益**: 降低新贡献者上手门槛，提升项目专业度

### P1-4: 补充 Widget 层基础测试

- **目标**: 为 dashboard 和 practice 关键路径添加冒烟测试
- **涉及文件**:
  - 新建 `tests/test_dashboard_widget.py`
  - 新建 `tests/test_practice_widget.py`
  - 更新 `pyproject.toml` 中的 coverage 排除列表
- **步骤**:
  1. 为 `dashboard.py` 和 `practice.py` 创建测试文件
  2. 使用 pytest-qt 进行 Qt 控件测试（如不可用则使用 mock）
  3. 覆盖关键路径：加载课程、切换标签、提交练习
  4. 从 `pyproject.toml` 的 coverage 排除列表中移除已覆盖的模块
- **风险**: 中等。PyQt5 测试需要 `pytest-qt` 插件和 display 环境（或 xvfb）
- **预期收益**: 测试覆盖率显著提升，防止 UI 回归

### P1-5: 添加 pre-commit hooks

- **目标**: 在提交前自动执行代码质量检查
- **涉及文件**:
  - 新建 `.pre-commit-config.yaml`
  - 更新 `pyproject.toml`（如有需要）
- **步骤**:
  1. 创建 `.pre-commit-config.yaml`
  2. 配置 hooks: `ruff check --fix`、`ruff format`
  3. 在 `CONTRIBUTING.md` 中说明安装方式
- **风险**: 低。可能首次安装时需要开发者运行 `pre-commit install`
- **预期收益**: 提交前自动保证代码风格一致

---

## 四、P2 持续改进

### P2-1: 实现暗色主题

- **目标**: 支持浅色/暗色主题切换
- **涉及文件**: `app/styles.py`、各 widget 文件中的硬编码颜色
- **步骤**:
  1. 将 `styles.py` 中的颜色值提取为主题变量
  2. 定义 `LIGHT_THEME` 和 `DARK_THEME` 两套配色方案
  3. 实现主题切换机制（信号 + 重绘）
  4. 在设置中添加主题选项
- **风险**: 中等。需要遍历所有 widget 文件替换硬编码颜色
- **预期收益**: 满足暗色模式用户需求，提升产品竞争力

### P2-2: 引入依赖注入替代全局数据库单例

- **目标**: 消除 `database.py` 的全局状态，支持依赖注入
- **涉及文件**: `app/database.py`、所有调用 `database.get_connection()` 的模块
- **步骤**:
  1. 将 `_connection` 全局变量重构为 `Database` 类
  2. 支持上下文管理器（`with Database() as db:`）
  3. 各服务类通过构造函数接收 `db` 实例
  4. 测试中可注入 mock 数据库
- **风险**: 中等。需要修改所有数据库调用点，工作量较大
- **预期收益**: 测试隔离、多实例支持、代码可测试性提升

### P2-3: 非 Windows 平台凭证加密

- **目标**: 替换 base64 编码的不安全回退方案
- **涉及文件**: `app/credentials.py`
- **步骤**:
  1. 检测平台是否支持 keyring
  2. 不支持时提示用户安装 `keyring` 或使用系统级密钥管理
  3. 如必须文件存储，使用 `cryptography` 库的 Fernet 对称加密
  4. 密钥派生自用户主密码或机器指纹
- **风险**: 中等。加密方案设计需谨慎，避免密钥管理引入新问题
- **预期收益**: 跨平台凭证安全存储

### P2-4: 补充类型注解并启用 mypy

- **目标**: 提升类型安全，启用严格模式
- **涉及文件**: 所有 widget 层文件、`window.py`、`database.py`
- **步骤**:
  1. 为 widget 层方法添加返回值和参数类型注解
  2. 将 `database.py` 的 `fetchall`/`fetchone` 返回类型改为 `NamedTuple` 或 `TypedDict`
  3. 在 `pyproject.toml` 中配置 mypy strict 模式
  4. 逐步修复 mypy 报告的类型错误
- **风险**: 低。纯增量改进，不影响运行时行为
- **预期收益**: 编译期捕获类型错误，IDE 智能提示增强

### P2-5: 魔法数字常量化

- **目标**: 消除散布的硬编码数字，提升可维护性
- **涉及文件**: `app/config.py`（新增常量）、`app/ai_mentor.py`、`app/practice_service.py` 等
- **步骤**:
  1. 在 `config.py` 中定义命名常量（`AI_TIMEOUT_SEC=3`、`CONTEXT_MESSAGE_LIMIT=12`、`EXCERPT_CHAR_LIMIT=6000` 等）
  2. 全局替换硬编码数字为常量引用
  3. 添加注释说明常量选取依据
- **风险**: 低。纯重构，不改变行为
- **预期收益**: 配置集中管理，意图清晰

---

## 五、实施路线图

```
当前 ─────────────────────────────────────────────────────────> 未来
  │                                                              │
  ├── 本次会话 (P0) ──────────────────────────────┤              │
  │   P0-1 清理原型文案                            │              │
  │   P0-2 数据外部化                              │              │
  │   P0-3 CI 流水线                               │              │
  │   P0-4 版本号统一                              │              │
  │   P0-5 根目录清理                              │              │
  │                                                │              │
  ├── 发布后 1 个月 (P1) ───────────────────────────┤              │
  │   P1-1 ai_mentor 拆分                          │              │
  │   P1-2 构建脚本合并                             │              │
  │   P1-3 文档完善                                │              │
  │   P1-4 Widget 测试                             │              │
  │   P1-5 pre-commit hooks                        │              │
  │                                                │              │
  ├── 持续改进 (P2) ──────────────────────────────────────────────┤
  │   P2-1 暗色主题          P2-4 类型注解           │              │
  │   P2-2 依赖注入          P2-5 魔法数字常量化      │              │
  │   P2-3 凭证加密                                   │              │
  └──────────────────────────────────────────────────────────────┘
```

## 六、预期最终评分

| 维度 | 当前 | P0 完成后 | P1 完成后 | P2 完成后 |
|------|------|----------|----------|----------|
| 代码质量 | 6 | 7 | 7.5 | 8.5 |
| 测试 | 5 | 5 | 7 | 8 |
| 文档 | 6 | 6 | 8 | 8 |
| UX/Polish | 7 | 7 | 7 | 8 |
| 安全 | 7 | 7 | 7 | 8 |
| Build/Release | 4 | 7 | 8 | 8 |
| DX | 5 | 6 | 8 | 8.5 |
| 架构 | 6 | 6.5 | 8 | 8.5 |
| **综合** | **5.75** | **6.56** | **7.56** | **8.19** |

---

## 七、附录：关键指标跟踪

| 指标 | 当前值 | P0 目标 | P1 目标 | P2 目标 |
|------|--------|---------|---------|---------|
| 根目录 Python 文件数 | 17 | <5 | <5 | <5 |
| 最大单文件行数 | 1,230 (`ai_mentor.py`) | 1,230 | <400 | <400 |
| 测试覆盖率 | 未测量（大量模块排除） | 有效测量 | >60% | >80% |
| CI 状态 | 不存在 | lint + test 通过 | + coverage 阈值 | + 发布自动化 |
| 版本号不一致处 | 3 处 | 0 | 0 | 0 |
| pre-commit hooks | 无 | 无 | ruff check + format | + mypy |
