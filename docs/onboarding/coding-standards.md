# 编码规范

本文档定义 DevLearnerAI 项目的编码标准，所有代码贡献必须遵循这些规范。

---

## 目录

- [命名规范](#命名规范)
- [文件组织](#文件组织)
- [提交规范](#提交规范)
- [代码风格工具链](#代码风格工具链)
- [类型注解](#类型注解)
- [日志规范](#日志规范)
- [文档字符串](#文档字符串)
- [测试规范](#测试规范)

---

## 命名规范

### Python 命名

| 类别 | 规范 | 示例 |
|------|------|------|
| 模块文件 | 小写 + 下划线 | `content_service.py`、`exercise_loader.py` |
| 类名 | PascalCase | `AppDatabase`、`ContentService`、`EvaluationResult` |
| 函数 / 方法 | 小写 + 下划线 | `get_connection()`、`init_db()`、`evaluate_python_code()` |
| 常量 | 全大写 + 下划线 | `APP_NAME`、`DB_PATH`、`CONTENT_DIR` |
| 私有成员 | 单下划线前缀 | `_connection`、`_init_ui()`、`_evaluate_sql()` |
| 双下划线 | 不使用 | 避免 Python name mangling |
| 变量 | 小写 + 下划线 | `lesson_id`、`track_title`、`score` |

### PyQt5 特殊约定

| 类别 | 规范 | 示例 |
|------|------|------|
| Qt 重写方法 | camelCase（Qt 原生） | `mousePressEvent()`、`keyPressEvent()` |
| Qt 信号名 | camelCase | `navigate_requested`、`response_ready` |
| Widget 内部方法 | 小写 + 下划线 | `_build_sidebar()`、`_switch_page()` |

### Win32 API 结构体

允许大写开头，匹配 Win32 API 命名：

```python
class CREDENTIALW: ...    # Win32 结构体名
class DATA_BLOB: ...      # Win32 结构体名
```

### 文件和目录命名

| 类别 | 规范 | 示例 |
|------|------|------|
| Python 模块 | 小写 + 下划线 | `api_client.py`、`chat_handler.py` |
| 课程 Markdown | 小写 + 下划线 | `python_basics_01.md` |
| 测试文件 | `test_` 前缀 | `test_database.py`、`test_evaluator_extended.py` |
| 构建脚本 | 小写 + 下划线 | `build_dev_exe.py`、`rebuild_courses.py` |

---

## 文件组织

### 模块结构顺序

每个 Python 文件应按以下顺序组织：

```python
"""模块文档字符串 -- 一句话说明模块职责。

详细描述（可选）。
"""

# 1. 标准库导入
import logging
import sqlite3
from pathlib import Path
from typing import Optional

# 2. 第三方库导入
from PyQt5.QtWidgets import QWidget

# 3. 本项目导入
from app.config import DB_PATH
from app.database import AppDatabase

# 4. 模块级 logger
logger = logging.getLogger(__name__)

# 5. 模块级常量
_DEFAULT_TIMEOUT = 30

# 6. 数据类 / 类型定义
@dataclass
class MyModel:
    ...

# 7. 工具函数
def helper_func():
    ...

# 8. 主类
class MyService:
    ...
```

### 导入规则

- 使用绝对导入（`from app.config import ...`），不使用相对导入
- import 排序遵循 isort 规则（由 Ruff 自动处理）
- `known-first-party = ["app"]`（在 `pyproject.toml` 中配置）
- 避免循环导入；如需解耦，使用延迟导入或事件系统

### 目录组织原则

```text
app/
├── 顶层模块    -- 配置、数据库、内容服务等核心模块
├── ai/         -- AI 相关子包
├── practice/   -- 练习评测子包
├── widgets/    -- UI 组件
├── services/   -- 业务服务层
└── utils/      -- 工具模块（事件、容器、中间件、插件）
```

**规则：**
- 新增 AI 功能 -> `app/ai/`
- 新增练习评测功能 -> `app/practice/`
- 新增 UI 页面 -> `app/widgets/`
- 新增业务逻辑 -> `app/services/`
- 新增基础设施 -> `app/utils/`

### `__init__.py` 导出规范

每个子包的 `__init__.py` 应定义 `__all__`，明确公开 API：

```python
# app/ai/__init__.py
from app.ai.api_client import send_chat
from app.ai.chat_handler import AIMentorDock, AIMentorPanel
from app.ai.markdown_renderer import render_markdown

__all__ = ["send_chat", "AIMentorDock", "AIMentorPanel", "render_markdown"]
```

---

## 提交规范

### 提交信息格式

遵循 Conventional Commits 规范：

```
<类型>: <简要描述>

<可选正文>

<可选脚注>
```

### 类型列表

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加 C++ 课程支持` |
| `fix` | 修复 Bug | `fix: 修复 SQL 评测结果不一致` |
| `docs` | 文档变更 | `docs: 更新安装说明` |
| `refactor` | 重构（不改变外部行为） | `refactor: 提取 AI 子模块` |
| `test` | 添加或修改测试 | `test: 增加沙箱安全边界用例` |
| `chore` | 杂务（构建、依赖、配置） | `chore: 升级 PyQt5 依赖版本` |
| `perf` | 性能优化 | `perf: 优化课程列表懒加载` |
| `style` | 代码格式（不影响逻辑） | `style: 统一引号风格` |

### 提交信息示例

```
database: 修复连续学习天数计算的边界条件

当用户今天没有学习记录时，streak 应返回 0 而非上一次的累计值。

Fixes #42
```

```
feat: 添加 JavaScript 练习评测支持

- 在 evaluator.py 中新增 _evaluate_javascript() 评测函数
- 支持关键字结构检查
- 添加对应测试用例
```

### 提交粒度

- 每个提交应是一个独立的、可理解的变更单元
- 避免将不相关的修改混在同一个提交中
- 大功能拆分为多个小提交，每个提交可独立通过 CI

---

## 代码风格工具链

### Ruff -- 统一 linter + formatter

项目使用 Ruff 替代 flake8 + isort + black，所有配置在 `pyproject.toml` 中。

#### 核心规则

| 规则 | 配置值 |
|------|--------|
| 目标 Python 版本 | 3.9 |
| 行宽 | 120 字符 |
| 引号风格 | 双引号 |
| 缩进 | 4 空格 |

#### 启用的规则集

| 规则集 | 说明 |
|--------|------|
| E / W | pycodestyle 错误和警告 |
| F | pyflakes（未使用导入等） |
| I | isort（import 排序） |
| N | pep8-naming（命名规范） |
| UP | pyupgrade（现代化语法） |
| B | flake8-bugbear（常见 bug 模式） |
| SIM | flake8-simplify（简化建议） |

#### 豁免规则

以下规则被有意忽略：

| 规则 | 原因 |
|------|------|
| E402 | 模块级导入位置 -- logger-before-import 模式是刻意的 |
| E501 | 行长度 -- 由 formatter 处理 |
| N802 | 函数名小写 -- PyQt5 重写方法必须 camelCase |
| N815 | 混合大小写变量 -- PyQt5 信号名 camelCase 约定 |
| UP006 | 使用 type[] -- 需要 Python 3.12+ 运行时 |
| UP035 | 弃用导入 -- Python 3.9 兼容性需要 |
| UP045 | 使用 X \| Y -- 需要 Python 3.10+ |

#### 常用命令

```bash
# 检查代码风格
ruff check .

# 自动修复
ruff check --fix .

# 格式化代码
ruff format .

# 通过 Makefile
make lint
make format
```

### 格式化前后对比

```python
# 格式化前
from app.database import  AppDatabase
from app.config import DB_PATH,CONTENT_DIR,ensure_runtime_dirs
import logging,sqlite3

# 格式化后（Ruff 自动处理）
import logging
import sqlite3

from app.config import CONTENT_DIR, DB_PATH, ensure_runtime_dirs
from app.database import AppDatabase
```

---

## 类型注解

### 基本要求

- 所有公开函数和方法必须添加参数和返回值类型注解
- 私有函数建议添加，但不强制
- 复杂数据结构优先使用 `dataclass` 或 `TypedDict`

### 示例

```python
# 好的 -- 完整类型注解
def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
    """获取课程信息。"""
    ...

# 好的 -- dataclass 定义
@dataclass
class Exercise:
    id: str
    title: str
    track_id: str
    difficulty: str
    hints: list[str] = field(default_factory=list)

# 不好的 -- 缺少类型注解
def get_lesson(self, lesson_id):
    ...

# 不好的 -- 使用 dict 而非 dataclass
def get_lesson(self, lesson_id: str) -> dict:
    ...
```

### 兼容性注意事项

项目支持 Python 3.9+，因此：

- 使用 `typing.Optional[X]` 而非 `X | None`（后者需要 3.10+）
- 使用 `typing.List[X]` 而非 `list[X]`（后者在 3.9 中仅限运行时使用有限场景）
- 使用 `from __future__ import annotations` 可在类型注解中使用新语法

```python
from __future__ import annotations

from typing import Optional

def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
    ...
```

---

## 日志规范

### Logger 获取

每个模块使用 `__name__` 获取 logger：

```python
import logging

logger = logging.getLogger(__name__)
```

**注意：** `logger` 赋值必须在模块导入之后（logger-before-import 模式），这是项目有意为之的模式，对应 Ruff 豁免规则 E402。

### 日志级别使用

| 级别 | 用途 | 示例 |
|------|------|------|
| `DEBUG` | 开发调试信息 | `logger.debug("数据库连接失效，尝试重新建立连接")` |
| `INFO` | 正常运行信息 | `logger.info("核心服务初始化耗时 %.1f ms", elapsed)` |
| `WARNING` | 可恢复的异常 | `logger.warning("课程文件损坏: %s, 使用回退值", path)` |
| `ERROR` | 不可恢复的错误 | `logger.error("数据库初始化失败", exc_info=True)` |

### 日志格式

```python
# 推荐 -- 使用 % 格式（延迟求值，性能好）
logger.info("课程 %s 加载完成，耗时 %.1f ms", lesson_id, elapsed)

# 不推荐 -- 使用 f-string（立即求值）
logger.info(f"课程 {lesson_id} 加载完成，耗时 {elapsed:.1f} ms")
```

---

## 文档字符串

### 模块级文档字符串

```python
"""课程内容加载与管理模块。

提供课程元数据的解析、Track/Module/Lesson 三级数据模型的构建、
Markdown 内容的读取，以及课程数据的缓存和懒加载机制。
"""
```

### 类文档字符串

```python
class AppDatabase:
    """SQLite 数据库操作类（线程安全）。

    使用 WAL 模式和写锁确保多线程环境下的数据一致性。
    提供课程进度、练习记录、AI 会话等数据的 CRUD 操作。
    """
```

### 函数文档字符串

```python
def get_connection(db_path: str) -> sqlite3.Connection:
    """获取或创建数据库连接（线程安全的单例模式）。

    如果现有连接已失效（例如数据库文件被替换），会自动重新建立连接。
    连接启用外键约束和 WAL 日志模式。

    Args:
        db_path: 数据库文件路径。

    Returns:
        sqlite3.Connection 实例。
    """
```

### 简短函数

简短的工具函数可以使用单行文档字符串：

```python
def _looks_corrupt(value: str) -> bool:
    """检测文本是否包含编码损坏的特征标记。"""
```

---

## 测试规范

### 文件组织

```
tests/
├── conftest.py                  # 共享 fixtures（含 PyQt5 mock）
├── test_<模块>.py               # 基础测试
├── test_<模块>_extended.py      # 扩展测试
├── test_<模块>_extra.py         # 额外覆盖
├── test_integration_<流程>.py   # 集成测试
├── test_security_<场景>.py      # 安全测试
└── benchmark/                   # 性能基准测试
```

### 编写规则

1. **使用 assert 风格**，不使用 `unittest.TestCase`
2. **测试类以 `Test` 开头**，测试函数以 `test_` 开头
3. **每个测试独立**，不依赖执行顺序
4. **使用 `tmp_path`** 管理临时文件和数据库
5. **核心逻辑测试不依赖 GUI**，可在无 PyQt5 环境运行
6. **Widget 测试使用 conftest.py 中的 mock**

### 测试命名

```python
# 好的 -- 描述意图
def test_init_db_creates_all_tables(self, tmp_path):
def test_evaluate_python_catches_syntax_error(self):
def test_streak_returns_zero_when_no_records(self):

# 不好的 -- 描述实现
def test_create_table(self):
def test_error(self):
def test_zero(self):
```

### 覆盖率目标

- 核心模块（database、content_service、evaluator、python_runner、credentials）：80%+
- Widget 模块：排除在覆盖率统计之外（依赖 GUI 环境）
- 整体目标：40%+（因 Widget 排除而降低）
