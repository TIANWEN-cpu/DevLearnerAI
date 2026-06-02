# 内容格式文档

本文档描述 DevLearnerAI 的课程内容文件格式、练习格式和元数据格式。

---

## 目录结构

```
content/
  metadata/
    course_map.json           # 课程体系元数据
    exercises.json            # 练习定义
    exercise_fallbacks.json   # 练习编码损坏回退数据
    sql_query_fixtures.json   # SQL 评测 fixture 数据
  python/                     # Python 课程 Markdown 文件
  database/                   # 数据库课程 Markdown 文件
  csharp/                     # C# 课程 Markdown 文件
  c/                          # C 语言课程 Markdown 文件
  cpp/                        # C++ 课程 Markdown 文件
  algorithms/                 # 算法课程 Markdown 文件
  integration/                # 融合项目课程 Markdown 文件
  projects/                   # 项目实践 Markdown 文件
  stage1/                     # 阶段一课程 Markdown 文件
```

---

## 课程体系元数据 (course_map.json)

### 顶层结构

```json
{
  "tracks": [
    {
      "id": "python",
      "title": "Python 编程",
      "icon": "python",
      "summary": "从零开始掌握 Python 编程...",
      "modules": [...]
    }
  ]
}
```

### Track（技术栈）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `string` | 是 | 唯一标识符，如 `"python"`, `"database"` |
| `title` | `string` | 是 | 技术栈标题 |
| `icon` | `string` | 是 | 图标标识（用于 UI 显示） |
| `summary` | `string` | 是 | 技术栈简介 |
| `modules` | `array` | 是 | 模块列表 |

### Module（模块）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `string` | 是 | 唯一标识符 |
| `title` | `string` | 是 | 模块标题 |
| `summary` | `string` | 是 | 模块简介 |
| `lessons` | `array` | 是 | 课程列表 |

### Lesson（课程）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `string` | 是 | 唯一标识符 |
| `title` | `string` | 是 | 课程标题 |
| `summary` | `string` | 是 | 课程简介 |
| `path` | `string` | 是 | Markdown 文件相对于 `content/` 的路径，如 `"python/01-basics.md"` |
| `difficulty` | `string` | 是 | 难度级别：`"基础"`, `"进阶"`, `"高级"` |
| `estimated_minutes` | `integer` | 是 | 预估学习时间（分钟） |
| `tags` | `array[string]` | 否 | 课程标签 |
| `prerequisites` | `array[string]` | 否 | 前置课程 ID 列表 |
| `outcomes` | `array[string]` | 否 | 学习目标列表 |

### 示例

```json
{
  "tracks": [
    {
      "id": "python",
      "title": "Python 编程",
      "icon": "python",
      "summary": "系统学习 Python 编程语言",
      "modules": [
        {
          "id": "python-basics",
          "title": "Python 基础",
          "summary": "掌握 Python 基本语法和数据类型",
          "lessons": [
            {
              "id": "py-hello-world",
              "title": "Hello World",
              "summary": "编写你的第一个 Python 程序",
              "path": "python/01-hello-world.md",
              "difficulty": "基础",
              "estimated_minutes": 15,
              "tags": ["入门", "print"],
              "prerequisites": [],
              "outcomes": ["理解 print 函数", "运行第一个程序"]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 课程 Markdown 格式

课程内容以标准 Markdown 编写，存储在 `content/` 子目录下。

### 文件命名

文件路径在 `course_map.json` 的 `lesson.path` 字段中指定，相对于 `content/` 目录。

### 内容结构建议

```markdown
# 课程标题

## 概述
简要介绍本节课内容。

## 核心概念
讲解主要知识点。

## 代码示例
```python
# 示例代码
print("Hello, World!")
```

## 练习
配合的练习说明。

## 总结
本节要点回顾。
```

### 支持的 Markdown 特性

- 标题（h1-h6）
- 段落和换行
- 粗体、斜体
- 有序/无序列表
- 代码块和行内代码
- 表格
- 引用块
- 链接和图片
- 水平线

---

## 练习定义 (exercises.json)

### 顶层结构

```json
{
  "exercises": [
    {
      "id": "py-hello-exercise",
      "title": "Hello World 练习",
      "track_id": "python",
      "lesson_id": "py-hello-world",
      "difficulty": "基础",
      "prompt": "编写一个程序，输出 'Hello, World!'",
      ...
    }
  ]
}
```

### Exercise 对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | `string` | 是 | 练习唯一标识 |
| `title` | `string` | 是 | 练习标题 |
| `track_id` | `string` | 是 | 所属技术栈 ID |
| `lesson_id` | `string` | 是 | 关联课程 ID |
| `difficulty` | `string` | 是 | 难度级别 |
| `prompt` | `string` | 是 | 题目描述（支持 Markdown） |
| `hints` | `array[string]` | 否 | 提示列表 |
| `starter_code` | `string` | 否 | 起始代码模板 |
| `required_keywords` | `array[string]` | 否 | SQL/C#/C 评测：必须包含的关键字 |
| `forbidden_keywords` | `array[string]` | 否 | SQL/C#/C 评测：禁止使用的关键字 |
| `expected_nodes` | `array[string]` | 否 | Python 评测：期望的 AST 节点类型 |
| `required_names` | `array[string]` | 否 | Python 评测：期望定义的名称 |
| `tests` | `array[object]` | 否 | Python 评测：测试用例 |

### 测试用例格式 (tests)

Python 练习的测试用例：

```json
{
  "tests": [
    {
      "expression": "add(2, 3)",
      "expected": 5
    },
    {
      "expression": "isinstance(greet, type(lambda: None))",
      "expected": true
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `expression` | `string` | 在代码执行后的命名空间中求值的 Python 表达式 |
| `expected` | `any` | 期望的求值结果 |

### 各语言练习示例

#### Python 练习

```json
{
  "id": "py-functions-add",
  "title": "编写加法函数",
  "track_id": "python",
  "lesson_id": "py-functions",
  "difficulty": "基础",
  "prompt": "定义一个函数 add(a, b)，返回两个数的和。",
  "hints": ["使用 def 关键字定义函数", "使用 return 返回结果"],
  "starter_code": "def add(a, b):\n    pass",
  "expected_nodes": ["FunctionDef"],
  "required_names": ["add"],
  "tests": [
    {"expression": "add(1, 2)", "expected": 3},
    {"expression": "add(-1, 1)", "expected": 0}
  ]
}
```

#### SQL 练习

```json
{
  "id": "sql-select-users",
  "title": "查询所有用户",
  "track_id": "database",
  "lesson_id": "sql-basics",
  "difficulty": "基础",
  "prompt": "编写 SQL 查询 users 表中的所有记录。",
  "hints": ["使用 SELECT * FROM ..."],
  "required_keywords": ["select", "from", "users"],
  "forbidden_keywords": ["delete", "drop"]
}
```

#### C/C# 练习

```json
{
  "id": "csharp-hello",
  "title": "C# Hello World",
  "track_id": "csharp",
  "lesson_id": "csharp-basics",
  "difficulty": "基础",
  "prompt": "编写一个 C# 控制台程序输出 Hello World。",
  "required_keywords": ["console", "writeline", "main"],
  "forbidden_keywords": []
}
```

---

## 编码损坏回退 (exercise_fallbacks.json)

当练习元数据中的文本字段出现编码损坏（如乱码 `???`）时，系统会自动使用回退值替换。

### 结构

```json
{
  "py-hello-exercise": {
    "title": "Hello World 练习",
    "difficulty": "基础",
    "prompt": "编写一个输出 Hello World 的程序。",
    "hints": ["使用 print 函数"],
    "starter_code": "# 在这里编写代码\n",
    "tests": [
      {"expression": "1+1", "expected": 2}
    ]
  }
}
```

键为练习 ID，值为包含可选回退字段的对象。系统仅在检测到原始字段损坏时才使用回退值。

### 损坏检测规则

- 字段值包含 `?` 字符
- `title`、`difficulty`、`prompt`、`hints`、`starter_code`、`tests` 字段均会检测

---

## SQL 查询 Fixture (sql_query_fixtures.json)

为 SQL 练习提供真实数据库执行环境的测试数据。

### 结构

```json
{
  "sql-exercise-id": {
    "setup": "CREATE TABLE users(id INTEGER, name TEXT); INSERT INTO users VALUES (1, 'Alice');",
    "mode": "query",
    "expected_rows": [[1, "Alice"]],
    "ordered": false
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `setup` | `string` | 执行用户代码前运行的 SQL（建表、插入测试数据） |
| `mode` | `string` | 评测模式：`"query"`, `"script"`, `"explain"`, `"ddl"` |
| `expected_rows` | `array` | 期望的结果行（JSON 数组，自动转为 tuple） |
| `check_sql` | `string` | `script` 模式下用于验证落库结果的查询 |
| `ordered` | `boolean` | 结果集是否需要保持顺序，默认 `false` |

### 评测模式

| 模式 | 说明 | 评分方式 |
|------|------|----------|
| `query` | 执行用户 SQL，直接比对结果集 | 结果集完全一致得 70 分 |
| `script` | 执行用户 SQL 脚本，再用 check_sql 验证 | 落库结果一致得 70 分 |
| `explain` | 执行 EXPLAIN 查询，验证有输出 | 有执行计划输出得 70 分 |
| `ddl` | 执行 DDL 语句，验证数据库结构变更 | 结构符合要求得 70 分 |

### 通用评分维度

| 维度 | 分值 |
|------|------|
| 关键字覆盖 | 20 |
| 无禁用关键字 | 10 |
| 结果/结构正确 | 70 |
| 语句格式规范 | 5（bonus） |

**通过条件**: 总分 >= 70 且无缺失关键字且无禁用关键字且无执行失败。

---

## 内容编码注意事项

1. **统一使用 UTF-8**: 所有 JSON 和 Markdown 文件必须使用 UTF-8 编码
2. **旧数据兼容**: 系统会自动检测和修复 GBK/GB2312 等编码损坏的数据
3. **损坏检测标记**: `???`, `??`, `锟`, `�`, `璇`, `妯`, `鍩`, `绮`, `路` 等异常字符序列会被标记为损坏
4. **JSON 中的 tuple**: JSON 不支持 tuple 类型，`expected_rows` 中的数据为 list 格式，加载时自动转为 tuple
