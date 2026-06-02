# 课程内容格式指南

本文档介绍如何为 DevLearner AI 创建和管理课程内容。

---

## 目录

- [内容目录结构](#内容目录结构)
- [课程元数据格式（course_map.json）](#课程元数据格式course_mapjson)
- [课程文件格式（Markdown）](#课程文件格式markdown)
- [添加新课程的完整流程](#添加新课程的完整流程)
- [内容编写规范](#内容编写规范)
- [课程地图重建](#课程地图重建)

---

## 内容目录结构

课程内容存储在 `content/` 目录下，按技术栈组织：

```text
content/
├── python/              # Python 课程
│   ├── py_data_types.md
│   ├── py_control_flow.md
│   ├── py_functions.md
│   └── ...
├── c/                   # C 语言课程
├── cpp/                 # C++ 课程
├── csharp/              # C# 课程
├── database/            # 数据库课程
├── algorithms/          # 算法课程
├── integration/         # 融合项目内容
├── projects/            # 项目文档
│   ├── p1_todo.md
│   ├── p2_crawler.md
│   └── ...
└── metadata/
    ├── course_map.json        # 课程元数据（必需）
    ├── exercises.json         # 练习元数据
    ├── exercise_fallbacks.json  # 练习回退数据
    └── sql_query_fixtures.json  # SQL 测试数据
```

---

## 课程元数据格式（course_map.json）

`course_map.json` 是课程的核心配置文件，定义了所有课程的层次结构和元信息。

### 顶层结构

```json
{
  "tracks": [
    {
      "id": "python",
      "title": "Python",
      "description": "Python 编程语言学习路线",
      "modules": [...]
    }
  ]
}
```

### Track（技术栈）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 技术栈唯一标识 |
| `title` | string | 是 | 显示标题 |
| `description` | string | 是 | 路线描述 |
| `modules` | array | 是 | 模块列表 |

### Module（模块）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 模块唯一标识 |
| `title` | string | 是 | 显示标题 |
| `description` | string | 否 | 模块描述 |
| `lessons` | array | 是 | 课时列表 |

### Lesson（课时）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 课时唯一标识 |
| `title` | string | 是 | 显示标题 |
| `file` | string | 是 | Markdown 文件路径（相对于 content/ 目录） |
| `difficulty` | string | 是 | 难度等级：`入门` / `进阶` / `高级` |
| `estimated_hours` | number | 否 | 预估学时 |
| `prerequisites` | array | 否 | 前置依赖的课时 ID 列表 |
| `objectives` | array | 否 | 学习目标列表 |

### 完整示例

```json
{
  "tracks": [
    {
      "id": "python",
      "title": "Python",
      "description": "Python 编程语言完整学习路线",
      "modules": [
        {
          "id": "python-basics",
          "title": "Python 基础",
          "description": "Python 基本语法和概念",
          "lessons": [
            {
              "id": "py-data-types",
              "title": "数据类型",
              "file": "python/py_data_types.md",
              "difficulty": "入门",
              "estimated_hours": 2,
              "prerequisites": [],
              "objectives": [
                "理解 Python 基本数据类型",
                "掌握类型转换方法"
              ]
            },
            {
              "id": "py-control-flow",
              "title": "控制流",
              "file": "python/py_control_flow.md",
              "difficulty": "入门",
              "estimated_hours": 3,
              "prerequisites": ["py-data-types"],
              "objectives": [
                "掌握 if/elif/else 条件语句",
                "掌握 for/while 循环",
                "理解 break/continue 的用法"
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 课程文件格式（Markdown）

课程内容以标准 Markdown 格式编写，支持以下特性：

### 基本语法

```markdown
# 课程标题

## 第一节：概述

正文内容...

### 小节标题

更多内容...

## 第二节：代码示例

代码块使用三个反引号围栏：

```python
def hello():
    print("Hello, World!")
```

支持的语言标识：
- `python`
- `c`
- `cpp`
- `csharp`
- `sql`
- `javascript`

### 列表

无序列表：
- 项目 1
- 项目 2
- 项目 3

有序列表：
1. 第一步
2. 第二步
3. 第三步

### 强调

- **粗体** 用于重要概念
- *斜体* 用于术语
- `行内代码` 用于代码标识

### 表格

| 列 1 | 列 2 | 列 3 |
|------|------|------|
| 内容 | 内容 | 内容 |

### 引用

> 提示信息和注意事项使用引用块

### 代码块要求

- 每个代码块必须指定语言标识
- 代码示例应完整可运行
- 复杂代码应添加注释
- 代码块右上角会自动显示复制按钮

### 推荐的课程结构

```markdown
# 课程标题

## 学习目标
- 目标 1
- 目标 2

## 概念讲解
理论内容...

## 代码示例
```python
# 示例代码
```

## 实践练习提示
结合练习中心的对应练习...

## 总结
本课要点回顾...

## 下一步
指向下一课的链接或建议
```

---

## 添加新课程的完整流程

### 第 1 步：编写课程文件

1. 确定课程所属的技术栈
2. 在 `content/<技术栈>/` 目录下创建 `.md` 文件
3. 按照推荐结构编写课程内容

### 第 2 步：注册课程元数据

编辑 `content/metadata/course_map.json`：

1. 找到对应的技术栈（Track）
2. 找到或创建对应的模块（Module）
3. 在模块的 `lessons` 数组中添加新课时的元数据

### 第 3 步：创建关联练习（可选）

如果课程需要配套练习，编辑 `content/metadata/exercises.json` 添加练习定义。

### 第 4 步：验证

1. 启动应用，确认课程在学习路径中正确显示
2. 点击课程，确认内容正确渲染
3. 检查代码高亮是否正常

### 第 5 步：更新课程地图（如需要）

```bash
python scripts/rebuild/rebuild_courses.py
```

---

## 内容编写规范

### 文字规范

- 使用简体中文编写
- 专业术语首次出现时给出英文原文，如"变量（Variable）"
- 语言简洁明了，适合初学者理解
- 每段不超过 5 行，保持良好的可读性

### 代码规范

- 代码示例应遵循对应语言的编码规范
- Python 代码遵循 PEP 8
- 每个代码块应可独立运行
- 复杂代码分步骤讲解
- 避免一次展示过多代码

### 命名规范

- 课程文件使用小写字母和下划线命名，如 `py_data_types.md`
- 课时 ID 使用小写字母和连字符，如 `py-data-types`
- 模块 ID 使用小写字母和连字符，如 `python-basics`
- 技术栈 ID 使用小写字母，如 `python`、`database`

### 难度标注

| 等级 | 适用内容 |
|------|----------|
| 入门 | 基本语法、数据类型、简单操作 |
| 进阶 | 面向对象、设计模式、综合运用 |
| 高级 | 架构设计、性能优化、高级特性 |

---

## 课程地图重建

当课程内容发生较大变更时，可以使用重建脚本更新课程地图：

```bash
python scripts/rebuild/rebuild_courses.py
```

该脚本会：
1. 扫描 `content/` 目录下的所有 Markdown 文件
2. 与 `course_map.json` 对比
3. 发现未注册的课程文件
4. 更新课程地图

### 何时需要重建

- 批量添加了多个课程文件
- 移动或重命名了课程文件
- 课程结构发生重大调整
