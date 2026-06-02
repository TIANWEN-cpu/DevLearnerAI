# 常见开发任务指南

本文档提供 DevLearnerAI 项目中常见开发任务的详细操作步骤，适合作为日常开发的参考手册。

---

## 目录

- [添加新 Widget](#添加新-widget)
- [添加新练习类型](#添加新练习类型)
- [添加新课程](#添加新课程)
- [添加新测试](#添加新测试)
- [其他常见任务](#其他常见任务)

---

## 添加新 Widget

### 场景

需要在应用中添加一个全新的功能页面，例如"错题本"页面。

### 步骤

#### 1. 创建 Widget 文件

在 `app/widgets/` 目录下创建新文件：

```python
# app/widgets/mistakes.py

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

logger = logging.getLogger(__name__)


class MistakesWidget(QWidget):
    """错题本页面 -- 展示用户历史错题和复习建议。"""

    def __init__(self, db, practice_service):
        super().__init__()
        self.db = db
        self.practice_service = practice_service
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("错题本")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        # ... 其余 UI 构建
```

**要点：**
- Widget 继承 `QWidget`
- 通过构造函数注入依赖的服务（`db`、`practice_service` 等），不自行创建
- UI 构建放在 `_init_ui()` 方法中
- 使用 `logging.getLogger(__name__)` 获取模块级 logger

#### 2. 注册到主窗口

编辑 `app/window.py`：

```python
# 导入新 Widget
from app.widgets.mistakes import MistakesWidget

# 在 DevLearnerWindow.__init__() 中创建实例
self.mistakes = MistakesWidget(self.db, self.practice_service)

# 添加到 QStackedWidget（获取索引）
self.stack.addWidget(self.mistakes)
mistakes_index = self.stack.indexOf(self.mistakes)

# 添加侧边栏导航按钮
# 在 _build_sidebar() 方法中添加对应按钮
```

#### 3. 添加侧边栏入口

在 `DevLearnerWindow._build_sidebar()` 中添加导航按钮：

```python
btn_mistakes = QPushButton("  错题本")
btn_mistakes.setObjectName("sidebarBtn")
btn_mistakes.clicked.connect(lambda: self._switch_page(mistakes_index))
sidebar_layout.addWidget(btn_mistakes)
```

#### 4. 编写测试

```python
# tests/test_mistakes_widget.py

from app.widgets.mistakes import MistakesWidget


class TestMistakesWidget:
    def test_init_creates_ui(self, mock_db, mock_practice_service):
        widget = MistakesWidget(mock_db, mock_practice_service)
        assert widget is not None

    def test_loads_mistakes_from_db(self, mock_db):
        # 测试从数据库加载错题的逻辑
        ...
```

注意：Widget 测试需要 PyQt5 环境。在无 GUI 的 CI 环境中，`conftest.py` 提供了 PyQt5 的 mock。

#### 5. 检查

```bash
make lint    # 确保代码风格正确
make test    # 确保所有测试通过
python dev_main.py  # 启动应用验证 UI
```

---

## 添加新练习类型

### 场景

需要支持一种新的编程语言评测，例如 JavaScript。

### 步骤

#### 1. 在评测器中添加分支

编辑 `app/practice/evaluator.py`，在主评测分发函数中添加新语言分支：

```python
def evaluate_exercise(exercise: Exercise, code: str) -> EvaluationResult:
    """根据练习语言分发到对应评测器。"""
    lang = exercise.track_id.lower()

    if lang == "python":
        return _evaluate_python(exercise, code)
    elif lang in ("c", "csharp"):
        return _evaluate_keyword_code(exercise, code)
    elif lang == "database":
        return _evaluate_sql(exercise, code)
    elif lang == "javascript":                    # 新增
        return _evaluate_javascript(exercise, code)  # 新增
    else:
        return EvaluationResult(
            passed=False,
            score=0,
            feedback_lines=[f"不支持的语言: {lang}"],
        )
```

#### 2. 实现评测函数

在同一文件中实现具体评测逻辑：

```python
def _evaluate_javascript(exercise: Exercise, code: str) -> EvaluationResult:
    """JavaScript 代码评测 -- 关键字结构检查。"""
    feedback = []
    score = 0

    # 检查必需关键字
    for keyword in exercise.required_keywords:
        if keyword in code:
            score += 20
        else:
            feedback.append(f"缺少必需关键字: {keyword}")

    # 检查禁止关键字
    for keyword in exercise.forbidden_keywords:
        if keyword in code:
            feedback.append(f"不应使用: {keyword}")
            score -= 10

    score = max(0, min(100, score))
    passed = score >= 60

    if passed:
        feedback.insert(0, "评测通过！")

    return EvaluationResult(
        passed=passed,
        score=score,
        feedback_lines=feedback,
    )
```

#### 3. 添加练习数据

在 `content/metadata/exercises.json` 中注册新练习：

```json
{
  "id": "js-hello-world",
  "title": "JavaScript Hello World",
  "track_id": "javascript",
  "lesson_id": "js-basics-01",
  "difficulty": "基础",
  "prompt": "编写一个 JavaScript 程序，输出 'Hello, World!'",
  "starter_code": "console.log();",
  "hints": ["使用 console.log() 函数"],
  "required_keywords": ["console.log"],
  "forbidden_keywords": ["eval", "document.write"]
}
```

#### 4. 添加课程内容

在 `content/javascript/` 目录下添加 Markdown 课程文件，并在 `content/metadata/course_map.json` 中注册。

#### 5. 编写测试

```python
# tests/test_javascript_evaluator.py

from app.practice.evaluator import _evaluate_javascript
from app.practice.models import Exercise, EvaluationResult


class TestJavaScriptEvaluator:
    def _make_exercise(self, **kwargs):
        defaults = {
            "id": "js-test",
            "title": "Test",
            "track_id": "javascript",
            "difficulty": "基础",
            "prompt": "Test prompt",
            "lesson_id": "js-01",
            "required_keywords": ["console.log"],
            "forbidden_keywords": ["eval"],
        }
        defaults.update(kwargs)
        return Exercise(**defaults)

    def test_passes_with_correct_code(self):
        exercise = self._make_exercise()
        result = _evaluate_javascript(exercise, 'console.log("Hello");')
        assert result.passed is True
        assert result.score > 0

    def test_fails_with_forbidden_keyword(self):
        exercise = self._make_exercise()
        result = _evaluate_javascript(exercise, 'eval("1+1")')
        assert any("不应使用" in f for f in result.feedback_lines)
```

---

## 添加新课程

### 场景

需要为现有技术栈添加一门新课程，例如在 Python 路线下添加"装饰器深入"课程。

### 步骤

#### 1. 编写课程内容

在 `content/python/` 目录下创建 Markdown 文件：

```markdown
# 装饰器深入

## 学习目标

- 理解装饰器的本质（高阶函数）
- 掌握带参数的装饰器
- 了解 functools.wraps 的作用

## 前置要求

- Python 函数基础
- 闭包概念

## 内容

### 什么是装饰器

装饰器本质上是一个接收函数作为参数并返回新函数的高阶函数...
```

文件名使用小写字母和下划线，例如 `python_decorator_advanced.md`。

#### 2. 注册到课程地图

编辑 `content/metadata/course_map.json`，在对应 Track 的 Module 中添加 Lesson 条目：

```json
{
  "id": "py-decorator-advanced",
  "title": "装饰器深入",
  "summary": "深入理解装饰器的本质和高级用法",
  "path": "python/python_decorator_advanced.md",
  "difficulty": "进阶",
  "estimated_minutes": 60,
  "tags": ["装饰器", "高阶函数", "闭包"],
  "prerequisites": ["py-functions-basics"],
  "outcomes": [
    "理解装饰器的本质（高阶函数）",
    "掌握带参数的装饰器",
    "了解 functools.wraps 的作用"
  ]
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 全局唯一标识符，使用小写字母和连字符 |
| `title` | string | 课程标题 |
| `summary` | string | 一句话摘要 |
| `path` | string | Markdown 文件相对 `content/` 的路径 |
| `difficulty` | string | "基础" / "进阶" / "高级" |
| `estimated_minutes` | int | 预计学习时间（分钟） |
| `tags` | list | 关键词标签 |
| `prerequisites` | list | 前置课程 ID 列表 |
| `outcomes` | list | 学习目标列表 |

#### 3. 添加关联练习（可选）

在 `content/metadata/exercises.json` 中添加练习条目，将 `lesson_id` 指向新课程 ID。

#### 4. 验证

```bash
# 启动应用，确认新课程出现在课程列表中
python dev_main.py

# 检查课程内容渲染是否正常
# 在"学习路径"页面找到新课程，点击进入
```

#### 5. 注意事项

- Markdown 文件使用 UTF-8 编码
- 代码块使用三个反引号包裹，标注语言名称
- 文件大小建议控制在 50KB 以内
- `id` 字段全局唯一，建议使用 `<技术栈>-<主题>` 格式
- `prerequisites` 中引用的 ID 必须在 `course_map.json` 中存在

---

## 添加新测试

### 测试文件命名规范

```
tests/test_<模块名>.py           # 基础测试
tests/test_<模块名>_extended.py  # 扩展测试
tests/test_<模块名>_extra.py     # 额外覆盖
```

### 测试编写规范

#### 基本结构

```python
"""app/database.py 的单元测试。"""

import pytest
from app.database import AppDatabase


class TestAppDatabase:
    """AppDatabase 的测试类。"""

    def test_init_db_creates_tables(self, tmp_path):
        """init_db() 应创建所有必要的表。"""
        db_path = str(tmp_path / "test.db")
        db = AppDatabase(db_path)
        db.init_db()

        # 验证表已创建
        import sqlite3
        conn = sqlite3.connect(db_path)
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()

        assert "lesson_progress" in tables
        assert "practice_attempts" in tables
```

#### 使用 Fixtures

在 `tests/conftest.py` 中定义共享 fixtures。项目已提供 PyQt5 的 mock，确保核心逻辑测试可在无 GUI 环境运行。

```python
# 在测试文件中使用 tmp_path（pytest 内置）
def test_something(self, tmp_path):
    db_path = str(tmp_path / "test.db")
    ...
```

#### 测试风格要求

- 使用 `pytest` 的 `assert` 风格，不使用 `unittest.TestCase`
- 测试类以 `Test` 开头
- 测试函数以 `test_` 开头
- 函数名应描述测试意图，如 `test_init_db_creates_tables`
- 每个测试应独立，不依赖其他测试的执行顺序
- 使用 `tmp_path` fixture 管理临时文件

### 运行测试

```bash
# 运行全部测试
pytest

# 运行指定文件
pytest tests/test_database.py

# 运行匹配的测试
pytest -k "test_init_db"

# 详细输出
pytest -v

# 运行覆盖率
coverage run -m pytest
coverage report
```

### 测试分类与重点

| 模块 | 测试文件 | 测试重点 |
|------|----------|----------|
| `database.py` | `test_database*.py` | CRUD 操作、线程安全、边界条件、压力测试 |
| `python_runner.py` | `test_python_runner*.py` | 沙箱安全边界、危险代码拦截、超时处理 |
| `practice/evaluator.py` | `test_evaluator*.py` | 各语言评测逻辑正确性 |
| `content_service.py` | `test_content_service*.py` | 课程加载、缓存、损坏数据处理 |
| `credentials.py` | `test_credentials.py` | 密钥存储与读取、平台回退逻辑 |
| `ai/api_client.py` | `test_api_client*.py` | HTTPS 强制、URL 构建、错误处理 |
| `ai/chat_handler.py` | `test_ai_chat_handler*.py` | 对话 UI 组件逻辑 |
| 集成测试 | `test_integration_*.py` | 端到端流程（学习/练习/数据库/AI） |
| 安全测试 | `test_security_sandbox_escape.py` | 沙箱逃逸、注入攻击 |

---

## 其他常见任务

### 修改全局样式

编辑 `app/styles.py`，该文件定义了 `GLOBAL_STYLE`（QSS 样式表）和字体常量。

```python
# app/styles.py
GLOBAL_STYLE = """
QMainWindow { background: #f5f5f5; }
#sidebarBtn { ... }
...
"""
```

修改后运行 `python dev_main.py` 即可预览效果。

### 修改数据库 Schema

1. 在 `app/database.py` 的 `init_db()` 方法中添加新的 `CREATE TABLE` 或 `ALTER TABLE` 语句
2. 使用 `IF NOT EXISTS` / `IF NOT EXISTS COLUMN` 保证幂等性
3. 添加对应的 CRUD 方法
4. 编写测试验证
5. 更新本文档中的数据表设计部分

### 修改 AI 系统提示词

AI 导师的系统提示词在 `app/ai/chat_handler.py` 或 `app/ai/models.py` 中定义。修改时注意：

- 提示词应包含课程上下文注入占位符
- 不要在提示词中硬编码 API Key 或敏感信息
- 修改后需要手动测试 AI 对话功能

### 添加新的数据表

```python
# 在 app/database.py 的 init_db() 中添加
self._conn.execute("""
    CREATE TABLE IF NOT EXISTS new_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")
```

然后在 `AppDatabase` 类中添加对应的 CRUD 方法。

### 打包与发布

```bash
# 验证构建配置
make verify-build

# 打包正式版
make build-release

# 打包开发版
make build-dev

# 产物输出到 dist/ 目录
```

版本号唯一来源为 `pyproject.toml` 的 `[project].version` 字段，`app/config.py` 通过 `importlib.metadata` 动态读取。修改版本号请使用：

```bash
python scripts/version_bump.py show           # 查看当前版本
python scripts/version_bump.py set 1.2.0      # 设置新版本
```
