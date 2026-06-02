# 练习格式

本文档描述 `content/metadata/exercises.json` 及相关配置文件的完整格式规范。

---

## exercises.json 格式

### 顶层结构

```json
{
  "exercises": [
    { /* Exercise 对象 */ },
    { /* Exercise 对象 */ }
  ]
}
```

### Exercise 对象

```json
{
  "id": "py-add",
  "title": "实现 add 函数",
  "track_id": "python",
  "difficulty": "基础",
  "prompt": "定义一个函数 add(a, b)，返回两个数字的和。",
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

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一标识符 |
| `title` | string | 是 | 练习标题 |
| `track_id` | string | 是 | 所属技术栈 ID |
| `difficulty` | string | 是 | "基础" / "进阶" / "高级" |
| `prompt` | string | 是 | 题目描述 |
| `lesson_id` | string | 是 | 关联课程 ID |
| `hints` | list[string] | 否 | 提示列表（按难度递进） |
| `starter_code` | string | 否 | 起始代码模板 |
| `expected_nodes` | list[string] | 否 | Python: 期望的 AST 节点类型 |
| `required_names` | list[string] | 否 | Python: 期望定义的名称 |
| `tests` | list[dict] | 否 | Python: 测试用例列表 |
| `required_keywords` | list[string] | 否 | SQL/C/C#: 必须包含的关键字 |
| `forbidden_keywords` | list[string] | 否 | SQL/C/C#: 禁止使用的关键字 |

---

## ID 命名规范

练习 ID 使用以下前缀：

| 技术栈 | 前缀 | 示例 |
|--------|------|------|
| Python | `py-` | `py-add`, `py-filter-even` |
| C++ | `cpp-` | `cpp-hello-world` |
| C | `c-` | `c-printf-basics` |
| C# | `cs-` | `cs-hello-world` |
| 数据库 | `db-` | `db-select-users`, `db-join-orders` |
| 算法 | `algo-` | `algo-bubble-sort` |

---

## Python 练习字段详解

### expected_nodes

AST 节点类型列表，用于代码结构验证：

```python
# 常用 AST 节点类型
"FunctionDef"   # def 函数定义
"Return"        # return 语句
"For"           # for 循环
"While"         # while 循环
"If"            # if 条件
"ClassDef"      # class 类定义
"ListComp"      # [x for x in ...]
"DictComp"      # {k: v for ...}
"Lambda"        # lambda x: ...
"Try"           # try/except
"With"          # with 语句
"Assign"        # 赋值语句
"AugAssign"     # += -= 等复合赋值
```

### tests

测试用例在沙箱执行后通过 `eval()` 求值：

```json
"tests": [
  {
    "expression": "add(3, 5)",
    "expected": 8
  },
  {
    "expression": "normalize_name('  alice  ')",
    "expected": "Alice"
  },
  {
    "expression": "filter_even([1, 2, 3, 4])",
    "expected": [2, 4]
  }
]
```

**字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `expression` | string | Python 表达式，在代码执行后的命名空间中求值 |
| `expected` | any | 期望的返回值，使用 `==` 比较 |

**注意**:
- 表达式可以调用代码中定义的任何函数或访问任何变量
- `expected` 支持各种 Python 字面量（int, float, str, list, dict, bool, None）
- JSON 中的 `null` 对应 Python 的 `None`

### Python 评分规则

```text
语法检查 (20分):   ast.parse(code) 成功
结构检查 (20分):   expected_nodes 全部存在于 AST 中
安全执行 (10分):   沙箱中无异常执行
对象检查 (10分):   required_names 全部在命名空间中定义
测试用例 (40分):   40 * (通过测试数 / 总测试数)
───────────────────────────────────────────
总分: 100 分
通过: ≥ 70 分 且 所有测试通过 且 无缺失节点
```

---

## SQL 练习字段详解

### required_keywords

SQL 练习必须包含的关键字：

```json
"required_keywords": ["select", "from", "users", "where"]
```

关键字匹配规则：大小写不敏感，空格标准化后匹配。

### forbidden_keywords

禁止使用的关键字：

```json
"forbidden_keywords": ["drop", "delete", "truncate"]
```

### SQL 评分规则（有 Fixture）

```text
关键字检查 (20分):   required_keywords 全部存在
禁用检查 (10分):     forbidden_keywords 不存在
执行 + 比对 (70分):  结果集与参考答案一致
───────────────────────────────────────────
总分: 105 分（上限 100 分）
通过: ≥ 70 分
```

### SQL 评分规则（无 Fixture）

```text
提交检查 (20分):     代码非空
关键字检查 (50分):   required_keywords 全部存在
禁用检查 (20分):     forbidden_keywords 不存在
格式检查 (10分):     存在分号结尾
───────────────────────────────────────────
总分: 100 分
通过: ≥ 70 分
```

---

## C/C# 练习字段详解

C/C# 练习使用关键字结构检查：

```json
{
  "id": "c-hello-world",
  "title": "Hello World",
  "track_id": "c",
  "difficulty": "基础",
  "prompt": "编写一个 C 程序输出 Hello, World!",
  "lesson_id": "c-basics",
  "required_keywords": ["printf", "include", "stdio.h", "main"],
  "forbidden_keywords": ["system"]
}
```

### C/C# 评分规则

```text
提交检查 (20分):     代码非空
关键字检查 (50分):   required_keywords 全部存在
禁用检查 (20分):     forbidden_keywords 不存在
格式检查 (10分):     存在 ; 或 { 等语言特征
───────────────────────────────────────────
总分: 100 分
通过: ≥ 70 分
```

---

## sql_query_fixtures.json 格式

SQL 练习的真实执行 fixture 配置：

```json
{
  "db-select-users": {
    "setup": "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, age INTEGER); INSERT INTO users VALUES (1, 'Alice', 25);",
    "mode": "query",
    "expected_rows": [[1, "Alice", 25]],
    "ordered": false
  },
  "db-create-index": {
    "setup": "CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT);",
    "mode": "ddl",
    "check_sql": "",
    "expected_rows": [],
    "ordered": false
  }
}
```

### Fixture 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `setup` | string | 初始化 SQL（建表、插入测试数据） |
| `mode` | string | 评测模式 |
| `expected_rows` | array | 期望的结果集（list of list） |
| `ordered` | bool | 结果是否需要有序比对（默认 false） |
| `check_sql` | string | `script` 模式下的验证查询 |

### 评测模式

| 模式 | 说明 | 执行方式 |
|------|------|---------|
| `query` | 查询模式 | `conn.execute(code).fetchall()` → 比对 expected_rows |
| `script` | 脚本模式 | `conn.executescript(code)` → 执行 check_sql → 比对结果 |
| `ddl` | DDL 模式 | `conn.executescript(code)` → 通过 `validate_sql_side_effect()` 验证结构变更 |
| `explain` | 执行计划 | `conn.execute(code).fetchall()` → 检查是否有结果 |

---

## exercise_fallbacks.json 格式

编码损坏数据的回退值：

```json
{
  "py-add": {
    "title": "实现 add 函数",
    "difficulty": "基础",
    "prompt": "定义一个函数 add(a, b)，返回两个数字的和。",
    "hints": ["先写 def add(a, b):", "函数结果要用 return 返回"],
    "starter_code": "def add(a, b):\n    pass\n",
    "tests": [
      {"expression": "add(3, 5)", "expected": 8}
    ]
  }
}
```

当 `exercises.json` 中的字段值包含 `???` 等损坏标记时，自动使用此文件中的回退值。

---

## 完整示例

### Python 练习

```json
{
  "id": "py-class-person",
  "title": "定义 Person 类",
  "track_id": "python",
  "difficulty": "进阶",
  "prompt": "定义一个 Person 类，包含 name 和 age 属性，以及一个 introduce() 方法返回自我介绍字符串。",
  "lesson_id": "py-classes",
  "hints": [
    "使用 class Person: 定义类",
    "__init__ 方法用于初始化属性",
    "introduce() 返回如 '我是Alice，今年25岁' 的字符串"
  ],
  "starter_code": "class Person:\n    pass\n",
  "expected_nodes": ["ClassDef", "FunctionDef", "Return"],
  "required_names": ["Person"],
  "tests": [
    {"expression": "p = Person('Alice', 25); p.introduce()", "expected": "我是Alice，今年25岁"},
    {"expression": "p = Person('Bob', 30); p.name", "expected": "Bob"},
    {"expression": "p = Person('Bob', 30); p.age", "expected": 30}
  ],
  "required_keywords": [],
  "forbidden_keywords": []
}
```

### SQL 练习

```json
{
  "id": "db-join-orders-users",
  "title": "关联查询订单和用户",
  "track_id": "database",
  "difficulty": "进阶",
  "prompt": "查询所有订单及其对应的用户名。orders 表有 user_id 字段关联 users 表。",
  "lesson_id": "db-join-inner",
  "hints": [
    "使用 INNER JOIN 连接两张表",
    "ON 条件指定关联字段"
  ],
  "required_keywords": ["select", "join", "on", "orders", "users"],
  "forbidden_keywords": ["subquery"]
}
```

---

## 相关文档

- [练习创建指南](../guides/exercise-creation.md) - 如何创建练习
- [内容文件格式](content-format.md) - course_map.json 格式
- [沙箱问题排查](../troubleshooting/sandbox-issues.md) - 评测相关问题
