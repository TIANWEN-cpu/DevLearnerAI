# 开发工作流

本文档描述 DevLearnerAI 的日常开发流程、代码规范、调试技巧和提交规范。

---

## 开发命令速查

| 命令 | 说明 |
|------|------|
| `python main.py` | 启动生产环境 |
| `python dev_main.py` | 启动开发环境（DEBUG 日志） |
| `make lint` | 运行 Ruff 代码风格检查 |
| `make format` | 自动格式化代码 |
| `make test` | 运行全部测试 |
| `make coverage` | 运行测试 + 覆盖率报告 |
| `make bench` | 运行性能基准测试 |
| `make clean` | 清理临时文件和缓存 |
| `make build-dev` | 打包开发调试版 |
| `make build-release` | 打包正式发布版 |

---

## 代码规范

### 工具链

项目使用 [Ruff](https://docs.astral.sh/ruff/) 统一完成 lint 和格式化（替代 flake8 + isort + black）。

```bash
# 检查代码风格
ruff check .

# 自动修复可修复的问题
ruff check --fix .

# 格式化代码
ruff format .

# 同时格式化 + 修复
make format
```

### Ruff 配置要点

配置位于 `pyproject.toml`：

```toml
[tool.ruff]
target-version = "py39"
line-length = 120

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "SIM"]
```

### 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 模块 | snake_case | `content_service.py` |
| 类 | PascalCase | `AppDatabase`, `ContentService` |
| 函数/方法 | snake_case | `mark_lesson_completed()` |
| PyQt5 方法 | camelCase（允许） | `mousePressEvent()` |
| PyQt5 信号 | camelCase | `navigate_requested` |
| 常量 | UPPER_SNAKE_CASE | `ALLOWED_IMPORTS` |
| 私有属性 | _前缀 | `_cache`, `_db_lock` |
| Win32 结构体 | 大写开头（允许） | `CREDENTIALW` |

### 类型注解

公开函数应添加参数和返回值类型注解：

```python
def mark_lesson_completed(self, lesson_id: str, track_id: str) -> None:
    """标记课程为已完成。"""
    ...

def lesson_by_id(self, lesson_id: str) -> Optional[tuple[Track, Module, Lesson]]:
    """根据课程 ID 查找课程。"""
    ...
```

### 文档字符串

公开类和方法应添加中文文档字符串：

```python
class AppDatabase:
    """应用数据库操作封装。

    提供线程安全的 CRUD 操作，涵盖课程进度、练习记录、AI 会话管理、
    API 配置、知识库文件等全部持久化需求。
    """

    def mark_lesson_opened(self, lesson_id: str, track_id: str) -> None:
        """标记课程为已打开（进行中）。

        如果课程已完成则保持完成状态，仅更新最后打开时间。

        Args:
            lesson_id: 课程 ID。
            track_id: 所属技术栈 ID。
        """
```

---

## 日常开发流程

### 1. 从 main 创建功能分支

```bash
git checkout main
git pull origin main
git checkout -b feature/你的功能名
```

### 2. 开发与自测

```bash
# 编写代码...

# 随时检查代码风格
make lint

# 运行相关测试
pytest tests/test_xxx.py -v

# 运行全部测试确认无回归
make test
```

### 3. 格式化代码

```bash
make format
```

### 4. 提交

```bash
git add <相关文件>
git commit -m "模块: 简要描述"
```

### 5. 推送并创建 PR

```bash
git push origin feature/你的功能名
```

---

## 调试技巧

### 启用详细日志

使用 `dev_main.py` 启动应用，它会启用 DEBUG 级别日志：

```bash
python dev_main.py
```

日志输出到 `%APPDATA%/DevLearnerAI/logs/app.log`，格式为：

```text
2024-01-15 14:30:00 [app.database] INFO: 数据库初始化完成
2024-01-15 14:30:01 [app.content_service] WARNING: 课程元数据文件未找到: ...
```

### 数据库调试

```python
# 直接操作数据库查看状态
from app.database import AppDatabase

db = AppDatabase()

# 查看所有课程进度
rows = db.fetchall("SELECT * FROM lesson_progress")
for row in rows:
    print(row)

# 查看练习记录
rows = db.recent_attempts(limit=20)
for row in rows:
    print(row)
```

数据库路径：`%APPDATA%/DevLearnerAI/data/app.db`

可以使用 [DB Browser for SQLite](https://sqlitebrowser.org/) 等工具直接查看。

### 沙箱调试

```python
from app.python_runner import run_python_code, evaluate_python_code

# 测试代码执行
result = run_python_code("print('hello')")
print(result)
# {'ok': True, 'stdout': 'hello', 'duration_sec': 0}

# 测试代码评测
result = evaluate_python_code(
    code="def add(a, b): return a + b",
    expected_nodes=["FunctionDef", "Return"],
    required_names=["add"],
    tests=[{"expression": "add(1, 2)", "expected": 3}],
)
print(result)
```

### AI 模块调试

```python
from app.ai.api_client import test_connection, send_chat

# 测试连接
status = test_connection("https://api.openai.com", "sk-xxx")
print(status)

# 测试聊天
reply = send_chat(
    host="https://api.openai.com",
    api_key="sk-xxx",
    model="gpt-4",
    messages=[{"role": "user", "content": "你好"}],
)
print(reply)
```

---

## 分支策略

| 分支 | 用途 | 命名示例 |
|------|------|---------|
| `main` | 稳定发布分支 | - |
| `feature/*` | 新功能 | `feature/dark-theme` |
| `fix/*` | Bug 修复 | `fix/sql-eval-crash` |
| `docs/*` | 文档更新 | `docs/update-readme` |
| `refactor/*` | 代码重构 | `refactor/extract-ai-module` |

---

## 提交规范

### 格式

```
<模块>: <简要描述>

<可选正文>

<可选脚注>
```

### 示例

```text
database: 修复连续学习天数计算的边界条件

当用户今天没有学习记录时，streak 应返回 0 而非上一次的累计值。

Fixes #42
```

```text
python_runner: 增加对 eval() 调用的拦截

沙箱 AST 预检现在会拦截 eval()、exec()、compile() 等危险内置函数调用。
```

### 提交前检查清单

- [ ] `ruff check .` 无报错
- [ ] `ruff format --check .` 无差异
- [ ] `pytest` 全部通过
- [ ] 新增功能有对应测试
- [ ] 无敏感信息泄露（.env、API Key 等）

---

## 新增模块指南

### 创建新模块

```bash
# 在对应目录创建模块文件
# 例如：app/widgets/new_widget.py
```

### 典型模块结构

```python
"""模块简要说明。

更详细的模块功能描述。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NewWidget:
    """新组件的封装。"""

    def __init__(self, service):
        """初始化组件。

        Args:
            service: 依赖的服务实例。
        """
        self._service = service

    def do_something(self, param: str) -> bool:
        """执行某个操作。

        Args:
            param: 操作参数。

        Returns:
            操作是否成功。
        """
        try:
            # ... 逻辑
            return True
        except Exception as exc:
            logger.error("操作失败: %s", exc)
            return False
```

### 注册到主窗口

如果需要在主窗口中使用新 Widget，需要在 `app/window.py` 中：

1. 导入新 Widget
2. 在 `__init__` 中实例化
3. 添加到 `self.stack` 中
4. 更新 `self.learning_pages` 列表

---

## 相关文档

- [快速开始](getting-started.md) - 首次安装和运行
- [测试指南](testing.md) - 测试编写和运行
- [构建可执行文件](building.md) - 打包和分发
