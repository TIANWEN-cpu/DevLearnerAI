# 练习创建指南

本文档指导开发者如何为 DevLearnerAI 创建新的编程练习。

---

## 概述

练习定义在 `content/metadata/exercises.json` 中，系统支持多种语言的评测方式：

> 代码执行沙箱的完整安全架构详见 [安全模型](../concepts/security-model.md)，练习格式的完整规范见 [练习格式](../reference/exercise-format.md)。

| 语言 | 评测方式 | 说明 |
|------|---------|------|
| Python | 沙箱执行 | AST 预检 + 受限执行 + 测试用例验证 |
| SQL | 真实数据库 | 内存 SQLite 执行 + 结果比对 |
| C / C# | 关键字检查 | 结构分析（暂不编译执行） |

---

## 练习数据结构

### 完整字段说明

```json
{
  "id": "exercise-id",
  "title": "练习标题",
  "track_id": "python",
  "difficulty": "基础",
  "prompt": "题目描述，告诉学生要做什么。",
  "lesson_id": "关联课程ID",
  "hints": ["提示1", "提示2"],
  "starter_code": "def solution():\n    pass\n",
  "expected_nodes": ["FunctionDef", "Return"],
  "required_names": ["solution"],
  "tests": [
    {"expression": "solution()", "expected": 42}
  ],
  "required_keywords": [],
  "forbidden_keywords": []
}
```

### 字段详解

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一标识符 |
| `title` | string | 是 | 练习标题 |
| `track_id` | string | 是 | 所属技术栈 ID |
| `difficulty` | string | 是 | "基础" / "进阶" / "高级" |
| `prompt` | string | 是 | 题目描述 |
| `lesson_id` | string | 是 | 关联课程 ID |
| `hints` | list[str] | 否 | 提示列表（按难度递进） |
| `starter_code` | string | 否 | 起始代码模板 |
| `expected_nodes` | list[str] | 否 | 期望的 AST 节点类型（Python） |
| `required_names` | list[str] | 否 | 期望定义的名称（Python） |
| `tests` | list[dict] | 否 | 测试用例（Python） |
| `required_keywords` | list[str] | 否 | 必须包含的关键字（SQL/C/C#） |
| `forbidden_keywords` | list[str] | 否 | 禁止使用的关键字 |

---

## 创建 Python 练习

### 基本示例

```json
{
  "id": "py-add",
  "title": "实现 add 函数",
  "track_id": "python",
  "difficulty": "基础",
  "prompt": "定义一个函数 add(a, b)，返回两个数字的和。不要只 print，要真正 return 结果。",
  "lesson_id": "py-functions",
  "hints": [
    "先写 def add(a, b):",
    "函数结果要用 return 返回"
  ],
  "starter_code": "def add(a, b):\n    pass\n",
  "expected_nodes": ["FunctionDef", "Return"],
  "required_names": ["add"],
  "tests": [
    {"expression": "add(3, 5)", "expected": 8},
    {"expression": "add(-2, 7)", "expected": 5}
  ],
  "required_keywords": [],
  "forbidden_keywords": []
}
```

### expected_nodes 字段

`expected_nodes` 指定期望在代码 AST 中出现的节点类型：

| 节点类型 | 说明 | 何时使用 |
|----------|------|---------|
| `FunctionDef` | 函数定义 | 要求实现函数 |
| `Return` | return 语句 | 要求返回值 |
| `For` | for 循环 | 要求使用循环 |
| `While` | while 循环 | 要求使用循环 |
| `If` | if 条件 | 要求使用条件判断 |
| `ClassDef` | 类定义 | 要求实现类 |
| `ListComp` | 列表推导 | 要求使用列表推导 |
| `Lambda` | lambda 表达式 | 要求使用 lambda |

### tests 字段

测试用例在沙箱执行后通过 `eval()` 求值：

```json
"tests": [
  {"expression": "add(3, 5)", "expected": 8},
  {"expression": "add(0, 0)", "expected": 0},
  {"expression": "add(-1, 1)", "expected": 0},
  {"expression": "add(100, 200)", "expected": 300}
]
```

- `expression`：Python 表达式，在代码执行后的命名空间中求值
- `expected`：期望的返回值，使用 `==` 比较

### 评分规则

Python 评测采用多维度评分：

```text
语法检查:   20 分  (代码可以被 ast.parse 解析)
结构检查:   20 分  (expected_nodes 全部存在)
安全执行:   10 分  (沙箱中无异常执行)
对象检查:   10 分  (required_names 全部定义)
测试用例:   40 分  (按测试通过率分配)
───────────────────
总分:      100 分
通过条件:   ≥ 70 分 且 全部测试通过
```

### 复杂练习示例

```json
{
  "id": "py-filter-even",
  "title": "过滤偶数",
  "track_id": "python",
  "difficulty": "进阶",
  "prompt": "实现 filter_even(numbers)，返回列表中所有偶数组成的新列表。",
  "lesson_id": "py-list-comprehension",
  "hints": [
    "可以用列表推导式: [x for x in numbers if ...]",
    "判断偶数: x % 2 == 0"
  ],
  "starter_code": "def filter_even(numbers):\n    pass\n",
  "expected_nodes": ["FunctionDef", "Return"],
  "required_names": ["filter_even"],
  "tests": [
    {"expression": "filter_even([1, 2, 3, 4])", "expected": [2, 4]},
    {"expression": "filter_even([1, 3, 5])", "expected": []},
    {"expression": "filter_even([2, 4, 6])", "expected": [2, 4, 6]},
    {"expression": "filter_even([])", "expected": []}
  ],
  "required_keywords": [],
  "forbidden_keywords": []
}
```

---

## 创建 SQL 练习

### 基本查询练习

```json
{
  "id": "db-select-users",
  "title": "查询所有用户",
  "track_id": "database",
  "difficulty": "基础",
  "prompt": "查询 users 表中的所有记录。",
  "lesson_id": "db-select-basics",
  "hints": [
    "使用 SELECT * FROM ..."
  ],
  "starter_code": "",
  "expected_nodes": [],
  "required_names": [],
  "tests": [],
  "required_keywords": ["select", "from", "users"],
  "forbidden_keywords": ["drop", "delete"]
}
```

### SQL Fixture 机制

对于需要真实数据库验证的 SQL 练习，需要在 `content/metadata/sql_query_fixtures.json` 中配置 fixture：

```json
{
  "db-select-users": {
    "setup": "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, age INTEGER); INSERT INTO users VALUES (1, 'Alice', 25); INSERT INTO users VALUES (2, 'Bob', 30);",
    "mode": "query",
    "expected_rows": [[1, "Alice", 25], [2, "Bob", 30]],
    "ordered": false
  }
}
```

### Fixture 字段说明

| 字段 | 说明 |
|------|------|
| `setup` | 建表和插入测试数据的 SQL |
| `mode` | 评测模式: `query` / `script` / `ddl` / `explain` |
| `expected_rows` | 期望的结果集 |
| `ordered` | 结果是否需要有序比对 |
| `check_sql` | `script` 模式下的验证查询 |

### SQL 评分规则

```text
关键字检查:   20 分  (required_keywords 全部存在)
禁用检查:    10 分  (forbidden_keywords 不存在)
执行 + 比对:  70 分  (结果集与参考答案一致)
───────────────────
总分:       105 分（上限 100 分）
通过条件:    ≥ 70 分
```

### DDL 练习示例

```json
{
  "id": "db-design-enrollment-table",
  "title": "设计选课表",
  "track_id": "database",
  "difficulty": "进阶",
  "prompt": "创建 enrollments 表，包含 student_id 和 course_id 字段。",
  "lesson_id": "db-table-design",
  "hints": [
    "使用 CREATE TABLE enrollments(...)",
    "需要 student_id 和 course_id 两个字段"
  ],
  "required_keywords": ["create", "table", "enrollments", "student_id", "course_id"],
  "forbidden_keywords": ["drop"]
}
```

---

## 创建 C/C# 练习

C/C# 练习使用关键字结构检查（暂不支持编译执行）：

```json
{
  "id": "c-hello-world",
  "title": "Hello World",
  "track_id": "c",
  "difficulty": "基础",
  "prompt": "编写一个 C 程序，输出 'Hello, World!'",
  "lesson_id": "c-basics",
  "hints": [
    "需要 #include <stdio.h>",
    "使用 printf 输出"
  ],
  "starter_code": "#include <stdio.h>\n\nint main() {\n    // 在这里编写代码\n    return 0;\n}",
  "expected_nodes": [],
  "required_names": [],
  "tests": [],
  "required_keywords": ["printf", "include", "stdio.h", "main"],
  "forbidden_keywords": ["system"]
}
```

### C/C# 评分规则

```text
关键字检查:   50 分  (required_keywords 全部存在)
禁用检查:    20 分  (forbidden_keywords 不存在)
格式检查:    10 分  (存在 ; 或 { 等语言特征)
提交检查:    20 分  (代码非空)
───────────────────
总分:       100 分
通过条件:    ≥ 70 分
```

---

## 创建练习的完整流程

### 1. 确定练习类型

根据关联课程的语言确定评测方式：

- Python 课程 → Python 沙箱评测
- 数据库课程 → SQL 真实执行评测
- C/C# 课程 → 关键字结构检查

### 2. 编写练习定义

在 `content/metadata/exercises.json` 的 `exercises` 数组中添加新条目。

### 3. 配置 Fixture（SQL 练习）

如果是 SQL 练习，在 `content/metadata/sql_query_fixtures.json` 中添加对应的 fixture。

### 4. 配置回退数据（可选）

如果练习文本可能存在编码问题，在 `content/metadata/exercise_fallbacks.json` 中添加回退值。

### 5. 测试练习

```python
from app.practice.exercise_loader import load_exercises
from app.practice.evaluator import evaluate_python, evaluate_sql, evaluate_keyword_code

# 加载练习
exercises = load_exercises()
ex = next(e for e in exercises if e.id == "your-exercise-id")
print(f"练习: {ex.title}")
print(f"提示: {ex.hints}")

# 评测答案（以 Python 为例）
result = evaluate_python(ex, "def solution(): return 42")
print(f"得分: {result.score}")
print(f"通过: {result.passed}")
print(f"反馈:")
for line in result.feedback_lines:
    print(f"  - {line}")
```

### 6. 验证关联

确保练习的 `lesson_id` 在 `course_map.json` 中存在对应的课程。

---

## 最佳实践

### 题目描述

- 清晰明确：告诉学生要实现什么函数/查询
- 包含约束：说明不允许使用的方法
- 给出示例：提供输入输出示例（可以放在 prompt 中）

### 起始代码

- 提供函数签名和 docstring
- 使用 `pass` 占位
- 包含注释提示关键位置

```python
def normalize_name(text):
    """将用户名规范化：去空格 + 首字母大写。"""
    pass  # 在这里实现
```

### 测试用例

- 覆盖正常情况
- 覆盖边界条件（空输入、零值、负数等）
- 覆盖特殊情况（大小写、特殊字符等）
- 测试数量建议 3-5 个

### 提示设计

- 提示按难度递进排列
- 第一个提示：方向性提示（用什么方法）
- 后续提示：具体实现提示（怎么写）

---

## 相关文档

- [练习格式参考](../reference/exercise-format.md) - exercises.json 完整格式
- [课程内容编写](content-authoring.md) - 如何创建课程文档
- [沙箱问题排查](../troubleshooting/sandbox-issues.md) - 评测相关问题
