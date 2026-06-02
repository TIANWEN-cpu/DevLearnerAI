# 测试指南

本文档描述 DevLearnerAI 的测试体系、编写规范和覆盖率管理。

---

## 测试架构

```text
tests/
├── conftest.py                    # 共享 fixture（含 PyQt5 mock）
├── test_python_runner.py          # 沙箱安全边界测试
├── test_database.py               # 数据库 CRUD + 纯函数测试
├── test_practice_service.py       # 评测逻辑测试
├── test_content_service.py        # 课程内容加载测试
├── test_credentials.py            # 凭证管理测试
├── test_ai_*.py                   # AI 模块测试
├── test_integration_*.py          # 集成测试
└── benchmark/                     # 性能基准测试（不随默认测试运行）
```

### 测试分类

| 分类 | 目录/前缀 | 说明 |
|------|----------|------|
| 单元测试 | `test_*.py` | 测试单个函数/类的功能 |
| 集成测试 | `test_integration_*.py` | 测试多模块协作 |
| 基准测试 | `tests/benchmark/` | 性能基准（需 `--benchmark-enable`） |

---

## 运行测试

### 基本命令

```bash
# 运行全部测试
pytest

# 运行全部测试（详细输出）
pytest -v

# 运行指定文件
pytest tests/test_database.py

# 运行匹配的测试
pytest -k "test_mark_lesson"

# 运行指定类
pytest tests/test_database.py::TestAppDatabase

# 失败时停在第一个失败
pytest -x

# 显示完整回溯
pytest --tb=long
```

### 使用 Makefile

```bash
make test      # 运行全部测试
make coverage  # 运行测试 + 覆盖率报告
make bench     # 运行基准测试
```

### 覆盖率

```bash
# 运行测试并收集覆盖率
coverage run -m pytest

# 终端报告
coverage report

# HTML 报告（生成 htmlcov/ 目录）
coverage html
```

覆盖率配置（`pyproject.toml`）：

```toml
[tool.coverage.run]
source = ["app"]
omit = [
    "app/widgets/*",       # Widget 依赖 GUI 环境
    "app/window.py",
    "app/ai_mentor.py",
    "app/reader_dialog.py",
    "app/highlighter.py",
    "app/effects.py",
    "app/localized_inputs.py",
    "app/codex_switcher.py",
    "app/styles.py",
]
```

> Widget 和 GUI 相关模块已从覆盖率统计中排除，因为它们需要真实的 PyQt5 环境。

---

## Pytest 配置

配置位于 `pyproject.toml`：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
norecursedirs = ["tests/benchmark"]
```

---

## 共享 Fixture

`tests/conftest.py` 提供了以下共享 fixture：

### PyQt5 Mock

在无 GUI 环境（如 CI 或无头服务器）中，`conftest.py` 自动注入 PyQt5 的 MagicMock 替代品：

```python
if "PyQt5" not in sys.modules:
    _pyqt5 = MagicMock()
    # 模拟 QtCore, QtGui, QtWidgets 的核心类
    # ...
    sys.modules["PyQt5"] = _pyqt5
```

这使得核心逻辑测试（database、practice_service 等）可以在没有 PyQt5 的环境中运行。

### 项目路径注入

```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
```

确保 `from app import ...` 始终可以正确导入。

---

## 编写测试规范

### 基本结构

```python
"""app/database.py 的测试。"""

import pytest
from app.database import AppDatabase


class TestAppDatabase:
    """AppDatabase 的 CRUD 操作测试。"""

    def test_init_db_creates_tables(self, tmp_path):
        """init_db 应创建所有必要的表。"""
        db = AppDatabase(tmp_path / "test.db")
        db.init_db()

        # 验证表存在
        tables = db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = {t[0] for t in tables}
        assert "lesson_progress" in table_names
        assert "practice_attempts" in table_names

    def test_mark_lesson_completed(self, tmp_path):
        """标记课程完成后应正确更新数据库。"""
        db = AppDatabase(tmp_path / "test.db")
        db.init_db()

        db.mark_lesson_completed("lesson-1", "python")

        status = db.lesson_status("lesson-1")
        assert status == "completed"
```

### 使用 tmp_path 隔离数据库

```python
def test_something(self, tmp_path):
    """每个测试使用独立的临时数据库。"""
    db = AppDatabase(tmp_path / "test.db")
    db.init_db()
    # ... 测试逻辑
```

### 测试命名规范

```python
# 格式: test_<被测功能>_<场景>_<期望结果>
def test_mark_lesson_completed_updates_status(self, tmp_path):
    ...

def test_evaluate_python_code_blocks_import(self):
    ...

def test_load_exercises_handles_missing_file(self, tmp_path):
    ...
```

### 断言风格

使用 pytest 原生 assert（不要用 unittest.TestCase）：

```python
# 好
assert result["ok"] is True
assert result["score"] >= 70
assert "SyntaxError" not in str(result.get("error", ""))

# 不好
self.assertTrue(result["ok"])
self.assertEqual(result["score"], 100)
```

### 异常测试

```python
def test_validate_code_safety_blocks_eval(self):
    """AST 预检应拦截 eval() 调用。"""
    from app.python_runner import _validate_code_safety

    with pytest.raises(SyntaxError, match="eval"):
        _validate_code_safety("eval('1+1')")
```

---

## 测试重点模块

### database.py 测试

| 测试场景 | 说明 |
|----------|------|
| 表创建 | `init_db()` 创建所有表 |
| CRUD 操作 | `mark_lesson_opened/completed`, `record_attempt` |
| 边界条件 | 空输入、重复插入、不存在的记录 |
| 统计缓存 | 缓存 TTL 和失效机制 |
| 连续天数计算 | `active_days_streak()` 的边界条件 |
| 旧版迁移 | `_migrate_legacy_db_if_needed()` |

### python_runner.py 测试

| 测试场景 | 说明 |
|----------|------|
| 安全拦截 | `eval()`, `exec()`, `import`, `__class__` 等 |
| 代码执行 | 正常代码执行和输出收集 |
| 代码评测 | 语法检查、结构检查、测试用例验证 |
| 超时处理 | 超时后子进程被终止 |
| 输出限制 | 12KB 输出截断 |
| 文件隔离 | 目录逃逸防护 |

### content_service.py 测试

| 测试场景 | 说明 |
|----------|------|
| 元数据加载 | 正常 JSON 解析 |
| 编码损坏修复 | `_looks_corrupt()` 检测 |
| 懒加载 | Track 按需构建和缓存 |
| ID 索引 | `lesson_by_id()` O(1) 查找 |
| Markdown 缓存 | FIFO 淘汰策略 |

### evaluator.py 测试

| 测试场景 | 说明 |
|----------|------|
| Python 评测 | 正常通过和失败场景 |
| SQL 评测 | 查询比对、DDL 副作用验证 |
| 关键字评测 | C/C# 结构检查 |
| 空答案 | 空输入处理 |
| 缺失关键字 | 反馈信息正确性 |

---

## 集成测试

集成测试位于 `tests/test_integration_*.py`，验证多模块的端到端协作：

```python
class TestLearningFlow:
    """学习流程集成测试。"""

    def test_complete_lesson_flow(self, tmp_path):
        """完整学习流程：打开课程 → 读取内容 → 标记完成。"""
        db = AppDatabase(tmp_path / "test.db")
        db.init_db()
        service = ContentService()

        # 模拟用户打开课程
        db.mark_lesson_opened("py-hello-world", "python")
        assert db.lesson_status("py-hello-world") == "in_progress"

        # 模拟用户完成课程
        db.mark_lesson_completed("py-hello-world", "python")
        assert db.lesson_status("py-hello-world") == "completed"
        assert db.completed_lessons() == 1
```

---

## CI 中运行测试

GitHub Actions CI 配置中自动运行测试：

```yaml
# .github/workflows/ci.yml
- name: Run tests
  run: pytest -v --tb=short

- name: Check code style
  run: ruff check .
```

---

## 相关文档

- [开发工作流](development.md) - 日常开发流程
- [模块一览](../reference/modules.md) - 所有模块接口参考
- [常见问题](../troubleshooting/common-issues.md) - 测试相关问题
