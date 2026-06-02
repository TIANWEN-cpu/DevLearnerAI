# 练习格式指南

本文档介绍如何为 DevLearner AI 创建和管理编程练习。

---

## 目录

- [练习元数据格式（exercises.json）](#练习元数据格式exercisesjson)
- [练习类型详解](#练习类型详解)
- [SQL 测试数据（fixtures）](#sql-测试数据fixtures)
- [练习回退数据](#练习回退数据)
- [添加新练习的完整流程](#添加新练习的完整流程)
- [评测器扩展](#评测器扩展)

---

## 练习元数据格式（exercises.json）

所有练习定义在 `content/metadata/exercises.json` 文件中。

### 顶层结构

```json
{
  "exercises": [
    {
      "id": "py-hello-world",
      "title": "Hello World",
      "description": "编写一个输出 'Hello, World!' 的 Python 程序",
      "track": "python",
      "lesson_id": "py-basics-intro",
      "difficulty": "基础",
      "language": "python",
      "instructions": "编写一个 Python 程序，输出 Hello, World!",
      "hints": ["使用 print() 函数"],
      "expected_output": "Hello, World!\n",
      "test_cases": [
        {
          "input": "",
          "expected": "Hello, World!\n"
        }
      ]
    }
  ]
}
```

### 练习字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 练习唯一标识，如 `py-hello-world` |
| `title` | string | 是 | 练习标题 |
| `description` | string | 是 | 练习描述 |
| `track` | string | 是 | 所属技术栈（python/c/cpp/csharp/database/algorithms） |
| `lesson_id` | string | 否 | 关联的课时 ID |
| `difficulty` | string | 是 | 难度：`基础` / `进阶` / `综合` |
| `language` | string | 是 | 编程语言：`python` / `sql` / `c` / `cpp` / `csharp` |
| `instructions` | string | 是 | 练习说明和要求 |
| `hints` | array | 否 | 提示列表 |
| `expected_output` | string | 否 | 预期输出（Python 练习） |
| `test_cases` | array | 否 | 测试用例列表 |
| `setup_sql` | string | 否 | SQL 练习的前置建表语句 |
| `expected_sql_result` | array | 否 | SQL 练习的预期结果集 |
| `keywords` | array | 否 | C/C# 练习的关键字检查列表 |
| `fixture_id` | string | 否 | 关联的 SQL fixture ID |

### ID 命名规范

- 格式：`<语言前缀>-<简短描述>`
- 示例：
  - `py-hello-world` -- Python Hello World
  - `db-select-all-users` -- SQL 查询所有用户
  - `c-pointer-basics` -- C 语言指针基础
  - `cpp-class-intro` -- C++ 类入门

---

## 练习类型详解

### Python 练习

Python 练习通过沙箱实际执行代码并验证输出。

**基本结构**：

```json
{
  "id": "py-sum-two-numbers",
  "title": "两数之和",
  "description": "编写函数计算两个整数的和",
  "track": "python",
  "difficulty": "基础",
  "language": "python",
  "instructions": "编写一个函数 add(a, b)，返回 a + b 的结果。然后调用函数并打印结果。",
  "hints": ["定义一个接受两个参数的函数", "使用 return 返回结果"],
  "expected_output": "8\n",
  "test_cases": [
    {
      "input": "",
      "expected": "8\n"
    }
  ]
}
```

**评测流程**：
1. AST 预检 -- 检查是否包含危险代码
2. 沙箱执行 -- 在受限环境中运行
3. 输出比对 -- 比对实际输出与预期输出
4. 测试用例验证 -- 运行所有测试用例

### SQL 练习

SQL 练习在内存 SQLite 数据库中执行真实查询。

**使用 fixture 的结构**：

```json
{
  "id": "db-select-active-users",
  "title": "查询活跃用户",
  "description": "编写 SQL 查询所有状态为 active 的用户",
  "track": "database",
  "difficulty": "基础",
  "language": "sql",
  "instructions": "从 users 表中查询所有 status = 'active' 的用户记录",
  "hints": ["使用 WHERE 子句过滤", "注意字符串值需要引号"],
  "fixture_id": "users-basic"
}
```

**使用内联数据的结构**：

```json
{
  "id": "db-count-users",
  "title": "统计用户数量",
  "description": "编写 SQL 统计 users 表中的用户总数",
  "track": "database",
  "difficulty": "基础",
  "language": "sql",
  "instructions": "统计 users 表中的用户总数",
  "hints": ["使用 COUNT() 聚合函数"],
  "setup_sql": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT); INSERT INTO users VALUES (1, 'Alice', 'a@test.com'); INSERT INTO users VALUES (2, 'Bob', 'b@test.com');",
  "expected_sql_result": [{"count(*)": 2}]
}
```

**DDL 练习（表结构验证）**：

```json
{
  "id": "db-design-enrollment-table",
  "title": "设计选课表",
  "description": "创建包含外键的选课表",
  "track": "database",
  "difficulty": "进阶",
  "language": "sql",
  "instructions": "创建 enrollments 表，包含 student_id 和 course_id 列",
  "hints": ["使用 CREATE TABLE 语句"],
  "setup_sql": "CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT); CREATE TABLE courses (id INTEGER PRIMARY KEY, title TEXT);"
}
```

DDL 练习通过 `validate_sql_side_effect()` 函数验证表结构变化。

### C / C# 练习

C 和 C# 练习通过关键字和结构检查进行评测。

```json
{
  "id": "c-pointer-basics",
  "title": "指针基础",
  "description": "使用指针交换两个变量的值",
  "track": "c",
  "difficulty": "进阶",
  "language": "c",
  "instructions": "编写 C 代码，使用指针交换两个整数变量的值",
  "hints": ["使用指针解引用 *", "使用取地址运算符 &"],
  "keywords": ["*", "&", "void", "int", "printf"]
}
```

**评测标准**：
- 代码中必须包含 `keywords` 列表中的所有关键字
- 代码结构必须符合题目要求的模式

---

## SQL 测试数据（fixtures）

SQL 练习可以使用预定义的测试数据集（fixtures），避免在每个练习中重复定义。

### fixture 文件

fixture 定义在 `content/metadata/sql_query_fixtures.json` 中。

### fixture 格式

```json
{
  "users-basic": {
    "setup_sql": [
      "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, status TEXT)",
      "INSERT INTO users VALUES (1, 'Alice', 'alice@test.com', 'active')",
      "INSERT INTO users VALUES (2, 'Bob', 'bob@test.com', 'inactive')",
      "INSERT INTO users VALUES (3, 'Charlie', 'charlie@test.com', 'active')"
    ],
    "queries": {
      "db-select-active-users": {
        "expected": [
          [1, "Alice", "alice@test.com", "active"],
          [3, "Charlie", "charlie@test.com", "active"]
        ]
      }
    }
  }
}
```

### fixture 引用

在练习定义中通过 `fixture_id` 字段引用 fixture：

```json
{
  "id": "db-select-active-users",
  "fixture_id": "users-basic",
  ...
}
```

---

## 练习回退数据

`content/metadata/exercise_fallbacks.json` 提供练习的回退数据，用于在主数据加载失败时使用。

### 回退数据格式

```json
{
  "py-hello-world": {
    "description": "编写一个输出 Hello World 的程序",
    "expected_output": "Hello, World!\n",
    "hints": ["使用 print() 函数"]
  }
}
```

---

## 添加新练习的完整流程

### 第 1 步：确定练习类型

根据练习的语言选择评测方式：
- Python -- 沙箱执行 + 输出比对
- SQL -- 内存数据库执行 + 结果比对
- C/C# -- 关键字结构检查

### 第 2 步：编写练习定义

在 `content/metadata/exercises.json` 的 `exercises` 数组中添加新的练习对象。

### 第 3 步：准备测试数据

- **SQL 练习**：如果使用 fixture，编辑 `sql_query_fixtures.json` 添加测试数据
- **Python 练习**：准备 `expected_output` 和 `test_cases`
- **C/C# 练习**：准备 `keywords` 列表

### 第 4 步：验证练习

1. 启动应用，进入练习中心
2. 确认新练习出现在列表中
3. 尝试提交正确答案和错误答案
4. 验证评测结果是否正确

### 第 5 步：特殊评测逻辑（如需要）

如果新练习需要特殊的评测逻辑，需要修改 `app/practice/evaluator.py`：

1. 对于 SQL DDL 练习，在 `validate_sql_side_effect()` 中添加新的验证分支
2. 对于其他特殊需求，在对应的评测函数中添加逻辑

---

## 评测器扩展

### Python 评测器

Python 评测入口：`app/python_runner.py` 中的 `evaluate_python_code()` 函数。

扩展点：
- 修改 `test_cases` 格式支持更复杂的测试场景
- 扩展沙箱允许的模块白名单

### SQL 评测器

SQL 评测入口：`app/practice/evaluator.py` 中的 `evaluate_sql_fixture()` 和 `evaluate_sql_inline()` 函数。

扩展点：
- 添加新的 DDL 验证规则到 `validate_sql_side_effect()`
- 添加新的 fixture 数据集

### C/C# 评测器

C/C# 评测入口：`app/practice/evaluator.py` 中的 `evaluate_keyword_code()` 函数。

扩展点：
- 调整关键字匹配逻辑
- 添加更复杂的结构检查规则
