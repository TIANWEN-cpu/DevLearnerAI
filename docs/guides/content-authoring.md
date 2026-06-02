# 课程内容编写指南

本文档指导内容作者如何为 DevLearnerAI 创建新的课程内容。

---

## 概述

课程内容以 Markdown 格式编写，通过 `course_map.json` 注册元数据，由 `ContentService` 加载和管理。

> 课程体系的三级层次结构设计详见 [课程内容体系](../concepts/content-system.md)，完整的 `course_map.json` 格式规范见 [内容文件格式](../reference/content-format.md)。

```text
内容创建流程:
  1. 编写 Markdown 课程文件 → content/<track>/<lesson>.md
  2. 在 course_map.json 中注册元数据
  3. （可选）在 exercises.json 中关联练习
  4. 运行 rebuild 脚本更新索引（如需要）
```

---

## 第 1 步：编写课程 Markdown

### 文件位置

将 `.md` 文件放在 `content/` 下对应技术栈目录中：

```text
content/
├── python/         # Python 课程
│   ├── py_hello_world.md
│   ├── py_variables.md
│   └── ...
├── cpp/            # C++ 课程
│   ├── cpp_thinking_setup.md
│   └── ...
├── database/       # 数据库课程
├── c/              # C 语言课程
├── csharp/         # C# 课程
└── algorithms/     # 算法课程
```

### 文件命名规范

- 使用小写字母和下划线
- 包含技术栈前缀（如 `py_`、`cpp_`、`db_`）
- 使用描述性名称

```text
# 好的命名
py_hello_world.md
py_variables_types.md
cpp_pointers_memory.md
db_select_basics.md

# 不好的命名
lesson1.md          # 不够描述性
HelloWorld.md       # 应该用小写
第1课.md            # 使用英文文件名
```

### Markdown 内容结构

每个课程文档应包含以下部分：

```markdown
# 课程标题

## 本节目标

- 学习目标 1
- 学习目标 2
- 学习目标 3

## 核心内容

正文内容，包含讲解、示例和解释。

### 子主题 1

```python
# 代码示例
print("Hello, World!")
```

### 子主题 2

更多的内容...

## 实战练习

动手练习，巩固所学知识。

## 小结

- 知识点 1
- 知识点 2

## 下一步

预告下一节的内容和方向。
```

### 内容编写建议

1. **渐进式教学**：从简单到复杂，每步只引入一个新概念
2. **代码示例优先**：用代码说明概念，而不是纯文字描述
3. **中文为主**：正文使用中文，代码和标识符保持英文
4. **适度长度**：每节课预估 20-45 分钟，避免内容过多
5. **使用 Markdown 特性**：代码块、列表、表格、强调等

### 代码块格式

使用三反引号代码块，并指定语言标识：

````markdown
```python
def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
```

```sql
SELECT name, age FROM users WHERE age > 18;
```

```cpp
#include <iostream>
int main() {
    std::cout << "Hello!" << std::endl;
    return 0;
}
```
````

### 表格用法

```markdown
| 数据类型 | 示例 | 说明 |
|---------|------|------|
| int | `42` | 整数 |
| float | `3.14` | 浮点数 |
| str | `"hello"` | 字符串 |
| bool | `True` | 布尔值 |
```

---

## 第 2 步：注册课程元数据

在 `content/metadata/course_map.json` 中为新课程添加条目。

### 找到目标位置

```json
{
  "tracks": [
    {
      "id": "python",                    // ← 找到目标技术栈
      "title": "Python 主线",
      "modules": [
        {
          "id": "py-foundations",         // ← 找到目标模块
          "title": "基础模块",
          "lessons": [
            // ... 现有课程 ...
            {                            // ← 在这里添加新课程
              "id": "py-new-lesson",
              "title": "新课程标题",
              "summary": "课程简介，一两句话概括。",
              "path": "python/py_new_lesson.md",
              "difficulty": "基础",
              "estimated_minutes": 30,
              "tags": ["标签1", "标签2"],
              "prerequisites": ["py-prev-lesson"],
              "outcomes": [
                "学习目标 1",
                "学习目标 2"
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一标识符，全局唯一 |
| `title` | string | 是 | 课程标题 |
| `summary` | string | 是 | 课程简介 |
| `path` | string | 是 | Markdown 文件相对 content/ 的路径 |
| `difficulty` | string | 是 | "基础" / "进阶" / "高级" |
| `estimated_minutes` | int | 是 | 预估学习时间（分钟） |
| `tags` | list[str] | 否 | 课程标签 |
| `prerequisites` | list[str] | 否 | 前置课程 ID 列表 |
| `outcomes` | list[str] | 否 | 学习目标列表 |

### 创建新模块

如果需要创建全新的模块：

```json
{
  "id": "py-new-module",
  "title": "新模块标题",
  "summary": "模块简介，描述这组课程要解决的问题。",
  "lessons": [
    // ... 课程列表 ...
  ]
}
```

### 创建新技术栈

如果需要创建全新的技术栈：

```json
{
  "id": "new-track",
  "title": "新技术栈",
  "icon": "📘",
  "summary": "技术栈简介。",
  "modules": [
    // ... 模块列表 ...
  ]
}
```

---

## 第 3 步：关联练习（可选）

如果课程配有编程练习，在 `content/metadata/exercises.json` 中添加练习定义。

详见 [练习创建指南](exercise-creation.md)。

---

## 第 4 步：验证

### 检查文件路径

确保 Markdown 文件路径与 `course_map.json` 中的 `path` 字段完全一致：

```python
# content/metadata/course_map.json 中的 path
"path": "python/py_new_lesson.md"

# 对应的实际文件
content/python/py_new_lesson.md  ✓
```

### 测试加载

```python
from app.content_service import ContentService

service = ContentService()
tracks = service.tracks
for track in tracks:
    print(f"技术栈: {track.title} ({len(track.modules)} 个模块)")
    for module in track.modules:
        print(f"  模块: {module.title} ({len(module.lessons)} 节课)")
```

### 检查课程渲染

```python
from app.content_service import ContentService

service = ContentService()
result = service.lesson_by_id("py-new-lesson")
if result:
    track, module, lesson = result
    markdown = service.lesson_markdown(lesson)
    print(f"课程: {lesson.title}")
    print(f"内容长度: {len(markdown)} 字符")
else:
    print("课程未找到！请检查 course_map.json 中的 id 和 path。")
```

---

## 编码注意事项

### 编码格式

- 所有 Markdown 文件使用 **UTF-8** 编码
- JSON 文件使用 **UTF-8** 编码（无 BOM）
- 文件名使用 **ASCII** 字符（小写字母、数字、下划线、连字符）

### 避免的问题

- **特殊字符**：避免使用 Unicode 私用区字符
- **BOM 标记**：JSON 文件不要添加 UTF-8 BOM
- **行尾符号**：统一使用 LF（`\n`），不要混用 CRLF
- **编码损坏检测**：系统会自动检测 `???`、`锟`、`�` 等损坏标记

---

## 内容模板

以下是一个完整的课程文档模板：

````markdown
# Python 函数入门

## 本节目标

- 理解函数的概念和作用
- 学会定义和调用 Python 函数
- 掌握参数传递和返回值机制

## 什么是函数

函数是一段可以重复使用的代码块，它接受输入（参数），
执行特定操作，并返回输出（返回值）。

## 定义函数

使用 `def` 关键字定义函数：

```python
def greet(name):
    """向指定用户打招呼。"""
    return f"你好，{name}！"
```

### 函数的组成部分

| 组成部分 | 说明 | 示例 |
|---------|------|------|
| `def` | 定义关键字 | `def` |
| 函数名 | 遵循 snake_case | `greet` |
| 参数 | 输入值 | `name` |
| 函数体 | 执行逻辑 | 缩进的代码 |
| `return` | 返回值 | `return ...` |

## 调用函数

定义函数后，通过函数名加括号来调用：

```python
message = greet("小明")
print(message)  # 输出: 你好，小明！
```

## 实战练习

编写一个函数 `add(a, b)`，返回两个数字的和。

提示：
- 使用 `def` 定义函数
- 使用 `return` 返回结果
- 不要只用 `print`，要真正返回值

## 小结

- `def` 关键字定义函数
- 参数在括号中声明
- `return` 返回函数结果
- 函数可以被多次调用

## 下一步

下一节我们将学习函数的高级用法，默认参数和可变参数。
````

---

## 相关文档

- [内容文件格式](../reference/content-format.md) - course_map.json 完整格式
- [练习创建指南](exercise-creation.md) - 如何创建配套练习
- [内容问题排查](../troubleshooting/content-issues.md) - 常见问题
