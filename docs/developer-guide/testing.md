# 测试指南

本文档介绍如何为 DevLearner AI 编写和运行测试。

---

## 目录

- [测试环境](#测试环境)
- [运行测试](#运行测试)
- [测试覆盖率](#测试覆盖率)
- [编写测试的规范](#编写测试的规范)
- [测试分类](#测试分类)
- [共享 Fixtures](#共享-fixtures)
- [集成测试](#集成测试)
- [安全测试](#安全测试)

---

## 测试环境

### 测试工具

| 工具 | 用途 |
|------|------|
| pytest | 测试框架 |
| coverage | 覆盖率统计 |
| Ruff | 代码风格检查 |

### 安装测试依赖

```bash
pip install -e ".[dev]"
```

或单独安装：

```bash
pip install pytest coverage ruff
```

### 测试目录结构

```text
tests/
├── __init__.py
├── conftest.py                        # 共享 fixtures
├── test_python_runner.py              # 沙箱安全边界测试
├── test_python_runner_extended.py     # 沙箱扩展测试
├── test_python_runner_extra.py        # 沙箱额外测试
├── test_python_runner_subprocess.py   # 子进程测试
├── test_database.py                   # 数据库 CRUD 测试
├── test_database_coverage.py          # 数据库覆盖率补充
├── test_database_extended.py          # 数据库扩展测试
├── test_database_extra.py             # 数据库额外测试
├── test_database_stress.py            # 数据库压力测试
├── test_practice_service.py           # 评测逻辑测试
├── test_practice_service_extended.py  # 评测扩展测试
├── test_practice_service_extra.py     # 评测额外测试
├── test_content_service.py            # 课程内容测试
├── test_content_service_extended.py   # 内容扩展测试
├── test_content_parsing_edge_cases.py # 内容解析边界测试
├── test_credentials.py                # 凭证测试
├── test_config_extended.py            # 配置扩展测试
├── test_edge_cases.py                 # 边界条件测试
├── test_ai_package.py                 # AI 模块测试
├── test_ai_chat_handler.py            # AI 对话处理测试
├── test_api_client_extended.py        # API 客户端测试
├── test_chat_handler_extended.py      # 对话处理扩展测试
├── test_markdown_renderer_extended.py # Markdown 渲染测试
├── test_evaluator_extended.py         # 评测器扩展测试
├── test_exercise_loader_extended.py   # 练习加载测试
├── test_security_sandbox_escape.py    # 安全沙箱逃逸测试
├── test_integration_learning_flow.py  # 学习流程集成测试
├── test_integration_practice_flow.py  # 练习流程集成测试
├── test_integration_database_flow.py  # 数据库流程集成测试
└── test_integration_ai_flow.py        # AI 流程集成测试
```

---

## 运行测试

### 运行所有测试

```bash
# 使用 Make
make test

# 直接使用 pytest
pytest
```

### 运行指定文件

```bash
pytest tests/test_database.py
```

### 运行匹配的测试

```bash
pytest -k "test_hello"
```

### 详细输出

```bash
pytest -v
```

### 显示打印输出

```bash
pytest -s
```

### 停止于第一个失败

```bash
pytest -x
```

---

## 测试覆盖率

### 生成覆盖率报告

```bash
# 使用 Make
make coverage

# 手动运行
coverage run -m pytest
coverage report            # 终端报告
coverage html              # HTML 报告（生成 htmlcov/ 目录）
```

### 覆盖率配置

覆盖率配置在 `pyproject.toml` 中：

```toml
[tool.coverage.run]
source = ["app"]
omit = [
    "app/widgets/*",      # Widget 模块需要 GUI 环境
    "app/codex_switcher.py",
]
```

Widget 模块已从覆盖率统计中排除，因为它们需要 PyQt5 GUI 环境。

---

## 编写测试的规范

### 基本规则

1. 测试文件放在 `tests/` 目录，命名为 `test_*.py`
2. 使用 `pytest` 的 `assert` 风格，不要使用 `unittest.TestCase`
3. 测试类以 `Test` 开头，测试函数以 `test_` 开头
4. 使用 `conftest.py` 中的 fixtures 共享测试夹具
5. 核心逻辑测试应在无 GUI 环境下可运行

### 断言风格

```python
# 正确 - pytest 风格
def test_addition():
    result = add(2, 3)
    assert result == 5

def test_list_not_empty():
    items = get_items()
    assert len(items) > 0

# 避免 - unittest 风格
class TestAddition(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(add(2, 3), 5)
```

### 测试命名

```python
# 好的命名 - 描述行为
def test_empty_input_returns_zero():
def test_negative_numbers_raise_error():
def test_sql_select_returns_expected_rows():

# 不好的命名 - 描述实现
def test_function():
def test_case_1():
```

### 参数化测试

对于相似的测试用例，使用 `@pytest.mark.parametrize`：

```python
import pytest

@pytest.mark.parametrize("input_val,expected", [
    ("1+1", 2),
    ("2*3", 6),
    ("10/2", 5),
])
def test_calculate(input_val, expected):
    assert calculate(input_val) == expected
```

### 异常测试

```python
import pytest

def test_invalid_input_raises_error():
    with pytest.raises(ValueError, match="Invalid"):
        process_input("bad data")
```

---

## 测试分类

### 按模块划分

| 模块 | 测试文件 | 测试重点 |
|------|----------|----------|
| `database.py` | `test_database*.py` | CRUD 操作、线程安全、边界条件、压力测试 |
| `python_runner.py` | `test_python_runner*.py` | 沙箱安全边界、危险代码拦截、子进程隔离 |
| `practice/evaluator.py` | `test_practice_service*.py` | 评测逻辑正确性、各语言评测分支 |
| `content_service.py` | `test_content_service*.py` | 课程加载、缓存、损坏数据处理 |
| `credentials.py` | `test_credentials.py` | 密钥存储与读取、平台回退逻辑 |
| `ai/api_client.py` | `test_api_client_extended.py` | HTTPS 强制、URL 构建、错误处理 |
| `ai/chat_handler.py` | `test_ai_chat_handler*.py` | 对话处理、消息构建 |
| `ai/markdown_renderer.py` | `test_markdown_renderer_extended.py` | Markdown 渲染、HTML 净化 |
| `practice/exercise_loader.py` | `test_exercise_loader_extended.py` | 练习数据加载、回退机制 |
| `config.py` | `test_config_extended.py` | 路径构建、版本读取 |

### 按类型划分

| 类型 | 说明 |
|------|------|
| 单元测试 | 测试单个函数或方法的行为 |
| 集成测试 | 测试多个模块协作的流程 |
| 安全测试 | 测试沙箱隔离和安全边界 |
| 边界测试 | 测试极端输入和异常情况 |

---

## 共享 Fixtures

`conftest.py` 中定义了多个共享 fixtures：

### 内存数据库 Fixture

```python
@pytest.fixture
def in_memory_db():
    """提供一个内存 SQLite 数据库连接"""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()
```

### 应用数据库 Fixture

```python
@pytest.fixture
def app_db(tmp_path):
    """提供一个临时目录中的 AppDatabase 实例"""
    db_path = tmp_path / "test.db"
    db = AppDatabase(str(db_path))
    yield db
```

### 测试数据 Fixture

```python
@pytest.fixture
def sample_exercises():
    """提供示例练习数据"""
    return [...]
```

### 使用 Fixture

```python
def test_database_insert(app_db):
    app_db.save_lesson_progress("lesson-1", True)
    result = app_db.get_lesson_progress("lesson-1")
    assert result is not None
```

---

## 集成测试

集成测试验证多个模块协作的完整流程：

### 学习流程测试

文件：`test_integration_learning_flow.py`

测试从课程加载到进度保存的完整流程。

### 练习流程测试

文件：`test_integration_practice_flow.py`

测试从练习加载到评测反馈的完整流程。

### 数据库流程测试

文件：`test_integration_database_flow.py`

测试数据库操作的完整流程，包括创建、读取、更新和删除。

### AI 流程测试

文件：`test_integration_ai_flow.py`

测试 AI 模块的完整流程，包括配置、连接和对话。

---

## 安全测试

### 沙箱逃逸测试

文件：`test_security_sandbox_escape.py`

测试各种沙箱逃逸手段是否被正确拦截：

- `eval()` / `exec()` 调用
- `os.system()` / `subprocess` 调用
- `__class__.__bases__` 属性访问
- 恶意 import 语句
- 文件系统越权访问

### 运行安全测试

```bash
pytest tests/test_security_sandbox_escape.py -v
```

---

> 下一步：[构建指南](building.md) -- 了解如何打包应用为可执行文件
