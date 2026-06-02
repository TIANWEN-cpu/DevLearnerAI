# 内容问题排查

本文档汇总与课程内容加载、显示和练习数据相关的常见问题及解决方案。

---

## 课程加载问题

> 课程内容的三级层次结构详见 [课程内容体系](../concepts/content-system.md)，内容加载策略见 [ADR-003: 内容加载机制](../adr/003-content-loading.md)。

### Q: 课程列表为空？

**可能原因**:

1. **course_map.json 缺失或损坏**
   ```bash
   # 检查文件是否存在
   ls content/metadata/course_map.json

   # 检查 JSON 格式是否正确
   python -c "import json; json.loads(open('content/metadata/course_map.json', encoding='utf-8').read())"
   ```

2. **文件编码问题**: 确认使用 UTF-8 编码（无 BOM）

3. **路径错误**: `content/` 目录应位于项目根目录下，或由 `config.py` 中的 `CONTENT_DIR` 指定

**解决方案**:

```python
from app.content_service import ContentService

service = ContentService()
print(f"发现 {len(service.tracks)} 个技术栈")
for track in service.tracks:
    print(f"  {track.title}: {len(track.modules)} 个模块")
```

如果输出为 0，检查 `course_map.json` 的 `tracks` 数组是否为空。

---

### Q: 特定课程内容显示 "课程文档暂时缺失"？

**原因**: Markdown 文件不存在或无法读取。

**排查**:

1. 检查 `course_map.json` 中的 `path` 字段是否正确
2. 检查对应的 `.md` 文件是否存在

```python
from app.content_service import ContentService
from app.config import CONTENT_DIR

service = ContentService()
result = service.lesson_by_id("your-lesson-id")
if result:
    track, module, lesson = result
    print(f"path: {lesson.path}")
    full_path = CONTENT_DIR / lesson.path
    print(f"完整路径: {full_path}")
    print(f"文件存在: {full_path.exists()}")
```

---

### Q: 课程内容显示乱码？

**原因**: Markdown 文件的编码不是 UTF-8，或包含编码损坏的文本。

**解决方案**:

1. 使用文本编辑器将文件重新保存为 UTF-8（无 BOM）编码
2. 检查是否有特殊字符导致显示异常
3. 系统内置了编码损坏检测，会自动使用回退值

**系统检测的损坏模式**:

```python
bad_tokens = ("???", "??", "锟", "�", "璇", "妯", "鍩", "绮")
```

---

### Q: 课程渲染的 HTML 中代码没有语法高亮？

**原因**: 代码块未指定语言标识，或使用了不支持的语言。

**正确写法**:

````markdown
```python    # 有高亮
print("hello")
```

```           # 无高亮
print("hello")
```
````

**支持的语言**: Python, SQL, C, C++, C#, JavaScript, Java, HTML, CSS, JSON, YAML, Bash, Shell 等。

---

### Q: 课程中的超链接点击无反应？

QTextBrowser 的链接处理有限制。系统在 HTML 净化时仅保留 `http://`、`https://` 和相对路径的链接。

```markdown
<!-- 有效链接 -->
[示例](https://example.com)
[相对路径](../other.md)

<!-- 可能无效 -->
[文件](file:///C:/path/to/file)
[邮件](mailto:test@example.com)
```

---

## 练习数据问题

> 练习的完整格式规范详见 [练习格式](../reference/exercise-format.md)，创建新练习见 [练习创建指南](../guides/exercise-creation.md)。

### Q: 练习列表为空？

**可能原因**:

1. **exercises.json 缺失或损坏**
   ```bash
   ls content/metadata/exercises.json
   python -c "import json; json.loads(open('content/metadata/exercises.json', encoding='utf-8').read())"
   ```

2. **JSON 格式错误**: 检查是否有语法错误

**验证**:

```python
from app.practice.exercise_loader import load_exercises

exercises = load_exercises()
print(f"加载了 {len(exercises)} 个练习")
for ex in exercises[:5]:
    print(f"  {ex.id}: {ex.title} ({ex.track_id})")
```

---

### Q: 练习标题或描述显示为乱码？

**原因**: exercises.json 中的文本字段存在编码损坏。

**解决方案**:

1. 在 `content/metadata/exercise_fallbacks.json` 中为该练习添加回退值：

```json
{
  "exercise-id": {
    "title": "正确的标题",
    "difficulty": "基础",
    "prompt": "正确的题目描述",
    "hints": ["正确的提示"]
  }
}
```

2. 系统检测到 `???` 等损坏标记时会自动使用回退值

---

### Q: SQL 练习提示 "SQL 执行失败"？

**可能原因**:

1. **缺少 fixture**: SQL 查询练习需要在 `sql_query_fixtures.json` 中配置测试数据
2. **SQL 语法错误**: 检查 SQL 语法
3. **表不存在**: 确认 fixture 的 `setup` 中创建了所需的表

**排查**:

```python
from app.practice.exercise_loader import get_sql_query_fixtures

fixtures = get_sql_query_fixtures()
print(f"已配置 {len(fixtures)} 个 SQL fixture")
print("Fixture IDs:", list(fixtures.keys()))
```

---

### Q: 练习的 hints 不显示？

**可能原因**:

1. exercises.json 中该练习的 `hints` 数组为空
2. hints 字段存在编码损坏

**检查**:

```python
from app.practice.exercise_loader import load_exercises

exercises = load_exercises()
ex = next((e for e in exercises if e.id == "your-exercise-id"), None)
if ex:
    print(f"hints: {ex.hints}")
else:
    print("练习未找到")
```

---

### Q: 评测结果与预期不符？

**排查步骤**:

1. **检查练习定义**: 确认 `expected_nodes`、`required_names`、`tests` 字段正确
2. **手动测试**: 使用 Python 交互式环境验证代码逻辑
3. **查看详细反馈**: 评测反馈 (`feedback_lines`) 包含详细的评分过程

```python
from app.practice.exercise_loader import load_exercises
from app.practice.evaluator import evaluate_python

exercises = load_exercises()
ex = next(e for e in exercises if e.id == "your-exercise-id")
result = evaluate_python(ex, "your_code_here")

print(f"得分: {result.score}")
print(f"通过: {result.passed}")
print("反馈:")
for line in result.feedback_lines:
    print(f"  - {line}")
```

---

## 脚本工具

### 重建课程数据

```bash
python scripts/rebuild/rebuild_courses.py
```

该脚本会重新扫描 `content/` 目录并更新课程元数据。

### 验证内容完整性

```python
from app.content_service import ContentService
from pathlib import Path

service = ContentService()
content_dir = Path("content")

missing_files = []
for track, module, lesson in service.all_lessons():
    path = content_dir / lesson.path
    if not path.exists():
        missing_files.append((lesson.id, lesson.path))

if missing_files:
    print(f"发现 {len(missing_files)} 个缺失文件:")
    for lesson_id, path in missing_files:
        print(f"  {lesson_id}: {path}")
else:
    print("所有课程文件完整。")
```

### 检查练习数据

```python
from app.practice.exercise_loader import load_exercises

exercises = load_exercises()

# 检查课程关联
from app.content_service import ContentService
cs = ContentService()

orphan_exercises = []
for ex in exercises:
    result = cs.lesson_by_id(ex.lesson_id)
    if not result:
        orphan_exercises.append(ex.id)

if orphan_exercises:
    print(f"发现 {len(orphan_exercises)} 个无关联课程的练习:")
    for eid in orphan_exercises:
        print(f"  {eid}")
else:
    print("所有练习都关联了有效课程。")
```

---

## 日志排查

### 启用详细日志

使用 `dev_main.py` 启动应用，查看详细日志：

```bash
python dev_main.py
```

### 关键日志模式

```text
# 课程加载
[app.content_service] WARNING: 课程元数据文件未找到: ...
[app.content_service] ERROR: 课程元数据 JSON 解析失败: ...
[app.content.content_service] WARNING: 课程 Markdown 文件未找到: ...

# 练习加载
[app.practice.exercise_loader] WARNING: 练习元数据文件未找到: ...
[app.practice.exercise_loader] ERROR: 练习元数据 JSON 解析失败: ...
```

### 日志文件位置

```text
%APPDATA%/DevLearnerAI/logs/app.log
```

日志配置：最大 5MB，保留 3 个备份，UTF-8 编码。

---

## 相关文档

- [课程内容编写指南](../guides/content-authoring.md) - 如何创建课程
- [练习创建指南](../guides/exercise-creation.md) - 如何创建练习
- [内容文件格式](../reference/content-format.md) - 完整格式规范
- [练习格式](../reference/exercise-format.md) - 练习格式规范
