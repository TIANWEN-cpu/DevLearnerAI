# 课程内容体系

本文档描述 DevLearnerAI 的课程组织结构、数据模型和内容加载机制。

---

## 三级层次结构

课程内容采用 Track > Module > Lesson 三级层次组织：

```text
Track (技术栈)
  ├── Module (模块)
  │     ├── Lesson (课程)
  │     ├── Lesson
  │     └── Lesson
  ├── Module
  │     ├── Lesson
  │     └── Lesson
  └── Module
        └── Lesson
```

### Track (技术栈)

技术栈是课程体系的顶层组织单元，代表一个完整的学习方向。

```python
@dataclass
class Track:
    id: str                    # 唯一标识符，如 "python", "database"
    title: str                 # 显示标题，如 "Python 主线"
    icon: str                  # 图标标识，如 "🐍", "🚀"
    summary: str               # 简介文本
    modules: list[Module]      # 包含的模块列表

    @property
    def lessons(self) -> list[Lesson]:
        """返回该技术栈下所有课程的扁平列表"""
        return [lesson for module in self.modules for lesson in module.lessons]
```

当前支持的技术栈：

| Track ID | 标题 | 图标 |
|----------|------|------|
| `python` | Python 主线 | 🐍 |
| `cplusplus` | C++ 路线 | 🚀 |
| `c` | C 语言 | ⚙️ |
| `csharp` | C# 开发 | 💎 |
| `database` | 数据库 | 🗃️ |
| `algorithms` | 算法 | 🧮 |
| `stage1` ~ `stage6` | 阶段课程 | 📘 |

### Module (模块)

模块是技术栈下的分组单元，包含一组逻辑相关的课程。

```python
@dataclass
class Module:
    id: str                    # 唯一标识符
    title: str                 # 显示标题
    summary: str               # 简介文本
    lessons: list[Lesson]      # 包含的课程列表
```

### Lesson (课程)

课程是最小的学习单元。

```python
@dataclass
class Lesson:
    id: str                    # 唯一标识符
    title: str                 # 课程标题
    summary: str               # 课程简介
    path: str                  # Markdown 文件路径（相对于 content/）
    difficulty: str            # 难度："基础" / "进阶" / "高级"
    estimated_minutes: int     # 预估学习时间（分钟）
    tags: list[str]            # 标签列表
    prerequisites: list[str]   # 前置课程 ID 列表
    outcomes: list[str]        # 学习目标列表
```

---

## 元数据结构

课程元数据存储在 `content/metadata/course_map.json` 中：

```json
{
  "tracks": [
    {
      "id": "python",
      "title": "Python 主线",
      "icon": "🐍",
      "summary": "从基础语法到工程实践...",
      "modules": [
        {
          "id": "py-foundations",
          "title": "基础模块",
          "summary": "搭建 Python 基础...",
          "lessons": [
            {
              "id": "py-hello-world",
              "title": "第一个 Python 程序",
              "summary": "从 print 开始...",
              "path": "python/py_hello_world.md",
              "difficulty": "基础",
              "estimated_minutes": 20,
              "tags": ["入门", "print"],
              "prerequisites": [],
              "outcomes": ["会用 print 输出", "理解 Python 执行方式"]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 内容目录结构

```text
content/
├── metadata/
│   ├── course_map.json          # 课程元数据（Track/Module/Lesson 定义）
│   ├── exercises.json           # 练习元数据
│   ├── exercise_fallbacks.json  # 编码损坏数据的回退值
│   └── sql_query_fixtures.json  # SQL 练习的测试 fixture
│
├── python/                      # Python 课程 Markdown 文件
│   ├── py_hello_world.md
│   ├── py_variables.md
│   └── ...
│
├── c/                           # C 语言课程
├── cpp/                         # C++ 课程
├── csharp/                      # C# 课程
├── database/                    # 数据库课程
├── algorithms/                  # 算法课程
├── integration/                 # 融合项目
├── projects/                    # 项目文档
├── stage1/ ~ stage6/            # 阶段课程
```

---

## ContentService 加载机制

### 懒加载策略

`ContentService` 采用懒加载模式，避免启动时加载所有课程内容：

```python
class ContentService:
    _MAX_MARKDOWN_CACHE = 64  # 最多缓存 64 个 Markdown 文件

    def __init__(self):
        self._cache: dict[str, Track] = {}
        self._tracks_index = self._discover_tracks()   # 仅加载索引
        self._lesson_index: dict[str, tuple[str, str]] = {}
        self._markdown_cache: dict[str, str] = {}
        self._build_lesson_index()
```

### 加载流程

```text
启动时:
  course_map.json → _discover_tracks() → _tracks_index (原始 JSON)
                                        → _build_lesson_index() → _lesson_index

按需加载:
  track_by_id() → _load_track() → _build_track() → _cache[track_id]

读取内容:
  lesson_markdown() → CONTENT_DIR / lesson.path → _markdown_cache
```

### 索引机制

课程 ID 索引提供 O(1) 查找：

```python
def _build_lesson_index(self):
    for track_data in self._tracks_index:
        track_id = track_data.get("id")
        for module_data in track_data.get("modules", []):
            module_id = module_data.get("id")
            for lesson_data in module_data.get("lessons", []):
                lesson_id = lesson_data.get("id")
                self._lesson_index[lesson_id] = (track_id, module_id)

def lesson_by_id(self, lesson_id: str) -> Optional[tuple[Track, Module, Lesson]]:
    indexed = self._lesson_index.get(lesson_id)
    if not indexed:
        return None
    track_id, module_id = indexed
    track = self.track_by_id(track_id)  # 按需加载目标 Track
    # ... 查找具体 Module 和 Lesson
```

### Markdown 缓存

```python
def lesson_markdown(self, lesson: Lesson) -> str:
    cache_key = lesson.path
    if cache_key in self._markdown_cache:
        return self._markdown_cache[cache_key]

    path = CONTENT_DIR / lesson.path
    content = path.read_text(encoding="utf-8")

    # FIFO 淘汰策略
    if len(self._markdown_cache) >= self._MAX_MARKDOWN_CACHE:
        oldest_key = next(iter(self._markdown_cache))
        del self._markdown_cache[oldest_key]

    self._markdown_cache[cache_key] = content
    return content
```

### 相邻课程预加载

```python
def preload_adjacent_lessons(self, lesson_id: str):
    """预加载前一课和后一课的 Markdown 到缓存"""
    all_ids = list(self._lesson_index.keys())
    idx = all_ids.index(lesson_id)
    for offset in (-1, 1):
        adj_idx = idx + offset
        if 0 <= adj_idx < len(all_ids):
            result = self.lesson_by_id(all_ids[adj_idx])
            if result:
                _, _, adj_lesson = result
                self.lesson_markdown(adj_lesson)  # 触发缓存
```

---

## 编码损坏检测与修复

系统内置了编码损坏检测机制，应对历史遗留数据问题：

```python
def _looks_corrupt(value: str) -> bool:
    """检测文本是否包含编码损坏标记"""
    bad_tokens = ("???", "??", "锟", "�", "璇", "妯", "鍩", "绮")
    return any(token in value for token in bad_tokens)

def _clean_text(value: str, fallback: str) -> str:
    """清洗文本：去除损坏内容，返回有效文本或回退值"""
    text = value.strip()
    return fallback if _looks_corrupt(text) else text
```

---

## 课程渲染流程

```text
Lesson.path (如 "python/py_hello_world.md")
    │
    ▼
CONTENT_DIR / lesson.path → 读取 Markdown 文本
    │
    ▼
mistune.html(markdown) → 原始 HTML
    │
    ▼
sanitize_html(html) → 安全 HTML（移除 script 等）
    │
    ▼
QTextBrowser.setHtml() → 渲染显示
```

---

## 相关文档

- [内容文件格式](../reference/content-format.md) - course_map.json 完整格式说明
- [课程内容编写指南](../guides/content-authoring.md) - 如何创建新课程
- [ADR-003: 内容加载机制](../adr/003-content-loading.md) - 设计决策
- [内容问题排查](../troubleshooting/content-issues.md) - 常见问题
