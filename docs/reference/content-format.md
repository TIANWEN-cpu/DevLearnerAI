# 内容文件格式

本文档描述 `content/metadata/course_map.json` 和课程 Markdown 文件的完整格式规范。

---

## course_map.json 格式

### 顶层结构

```json
{
  "tracks": [
    { /* Track 对象 */ },
    { /* Track 对象 */ }
  ]
}
```

### Track 对象

```json
{
  "id": "python",
  "title": "Python 主线",
  "icon": "🐍",
  "summary": "从基础语法到工程实践，系统掌握 Python 编程能力。",
  "modules": [
    { /* Module 对象 */ }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一标识符，全局唯一，使用小写字母和连字符 |
| `title` | string | 是 | 显示标题 |
| `icon` | string | 是 | 图标标识（emoji 或文本） |
| `summary` | string | 是 | 技术栈简介 |
| `modules` | array | 是 | 模块列表 |

### Module 对象

```json
{
  "id": "py-foundations",
  "title": "基础模块 · 语法与核心概念",
  "summary": "搭建 Python 开发环境，掌握基础语法和核心概念。",
  "lessons": [
    { /* Lesson 对象 */ }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一标识符 |
| `title` | string | 是 | 模块标题 |
| `summary` | string | 是 | 模块简介 |
| `lessons` | array | 是 | 课程列表 |

### Lesson 对象

```json
{
  "id": "py-hello-world",
  "title": "第一个 Python 程序",
  "summary": "从 print 开始，理解 Python 程序的执行方式。",
  "path": "python/py_hello_world.md",
  "difficulty": "基础",
  "estimated_minutes": 20,
  "tags": ["入门", "print", "环境"],
  "prerequisites": [],
  "outcomes": [
    "会用 print 输出文本",
    "理解 Python 脚本的执行方式"
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一标识符，全局唯一 |
| `title` | string | 是 | 课程标题 |
| `summary` | string | 是 | 课程简介 |
| `path` | string | 是 | Markdown 文件路径（相对于 `content/`） |
| `difficulty` | string | 是 | "基础" / "进阶" / "高级" |
| `estimated_minutes` | int | 是 | 预估学习时间（分钟），建议 15-60 |
| `tags` | array[string] | 否 | 标签列表 |
| `prerequisites` | array[string] | 否 | 前置课程 ID 列表 |
| `outcomes` | array[string] | 否 | 学习目标列表 |

---

## ID 命名规范

### Track ID

```text
python, c, cpp, csharp, database, algorithms
stage1, stage2, stage3, stage4, stage5, stage6
```

### Module ID

格式: `{track}-{module-name}`

```text
py-foundations, py-strings, py-functions, py-control-flow
cplusplus-foundations, cplusplus-stl
db-select-basics, db-joins, db-design
```

### Lesson ID

格式: `{track}-{lesson-name}`

```text
py-hello-world, py-variables-types, py-strings-collections
cpp-thinking-setup, cpp-syntax-functions, cpp-pointers-memory
db-select-basics, db-where-filter, db-join-inner
```

---

## Markdown 课程文件格式

### 文件编码

- 编码: UTF-8（无 BOM）
- 行尾: LF (`\n`)
- 文件名: 小写字母、数字、下划线、连字符

### 推荐结构

```markdown
# 课程标题

## 本节目标

- 目标 1
- 目标 2
- 目标 3

## 概念讲解

正文内容...

### 子主题 1

详细讲解...

## 代码示例

```python
# 示例代码
```

## 实战练习

动手练习内容...

## 小结

- 知识点 1
- 知识点 2

## 下一步

下一节预告。
```

### 支持的 Markdown 特性

| 特性 | 语法 | 渲染效果 |
|------|------|---------|
| 标题 | `# ~ ######` | h1-h6 |
| 粗体 | `**text**` | 加粗 |
| 斜体 | `*text*` | 斜体 |
| 代码块 | ` ```lang ``` ` | 带语法高亮的代码块 |
| 行内代码 | `` `code` `` | 行内代码样式 |
| 有序列表 | `1. item` | 编号列表 |
| 无序列表 | `- item` | 圆点列表 |
| 表格 | `\| col \| col \|` | 表格 |
| 链接 | `[text](url)` | 超链接 |
| 引用 | `> text` | 引用块 |
| 分割线 | `---` | 水平线 |

### 代码高亮支持

系统使用 Pygments 进行语法高亮，支持以下语言标识：

```text
python, sql, c, cpp, csharp, javascript, java,
html, css, json, xml, bash, shell, markdown,
yaml, toml, ini, makefile, dockerfile, ...
```

---

## 内容目录映射

```text
course_map.json 中的 path        对应的实际文件
──────────────────────────────    ──────────────────────────
"python/py_hello_world.md"       → content/python/py_hello_world.md
"cpp/cpp_thinking_setup.md"      → content/cpp/cpp_thinking_setup.md
"database/db_select_basics.md"   → content/database/db_select_basics.md
"csharp/cs_basics.md"            → content/csharp/cs_basics.md
"algorithms/algo_sort_bubble.md" → content/algorithms/algo_sort_bubble.md
"integration/proj_todo_app.md"   → content/integration/proj_todo_app.md
```

---

## 编码损坏检测

系统自动检测和修复以下编码损坏模式：

| 损坏标记 | 说明 |
|---------|------|
| `???` | 多个连续问号 |
| `??` | 双问号 |
| `锟` | GBK 编码错误特征 |
| `�` | Unicode 替换字符 |
| `璇`、`妯`、`鍩`、`绮` | 常见编码错误特征 |

检测到损坏数据时，系统使用 `_clean_text(value, fallback)` 函数返回回退值。

---

## 完整示例

```json
{
  "tracks": [
    {
      "id": "python",
      "title": "Python 主线",
      "icon": "🐍",
      "summary": "从基础语法到工程实践。",
      "modules": [
        {
          "id": "py-foundations",
          "title": "基础模块",
          "summary": "掌握 Python 核心概念。",
          "lessons": [
            {
              "id": "py-hello-world",
              "title": "第一个 Python 程序",
              "summary": "从 print 开始。",
              "path": "python/py_hello_world.md",
              "difficulty": "基础",
              "estimated_minutes": 20,
              "tags": ["入门", "print"],
              "prerequisites": [],
              "outcomes": ["会用 print 输出"]
            },
            {
              "id": "py-variables",
              "title": "变量与数据类型",
              "summary": "理解 Python 的变量和基本数据类型。",
              "path": "python/py_variables.md",
              "difficulty": "基础",
              "estimated_minutes": 30,
              "tags": ["变量", "类型"],
              "prerequisites": ["py-hello-world"],
              "outcomes": ["理解变量赋值", "掌握基本数据类型"]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 相关文档

- [课程内容编写指南](../guides/content-authoring.md) - 如何创建新课程
- [课程内容体系](../concepts/content-system.md) - 三级层次结构设计
- [内容问题排查](../troubleshooting/content-issues.md) - 常见问题
