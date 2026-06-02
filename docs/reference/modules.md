# 模块一览

本文档是 DevLearnerAI 所有模块的完整参考，包括职责、公开接口和依赖关系。

---

## 模块依赖图

```text
main.py / dev_main.py
  │
  └── app.window (DevLearnerWindow)
        │
        ├── app.config          (路径常量)
        ├── app.database        (数据持久化)
        ├── app.content_service (课程管理)
        ├── app.practice_service(练习兼容层)
        ├── app.styles          (全局样式)
        ├── app.effects         (动画效果)
        │
        ├── app.ai/
        │   ├── api_client      (AI API 通信)
        │   ├── chat_handler    (对话 UI)
        │   ├── markdown_renderer(Markdown 渲染)
        │   └── models          (数据类和常量)
        │
        ├── app.practice/
        │   ├── evaluator       (代码评测)
        │   ├── exercise_loader (练习加载)
        │   ├── models          (Exercise/EvaluationResult)
        │   └── normalizer      (结果标准化)
        │
        ├── app.widgets/
        │   ├── dashboard       (学习仪表盘)
        │   ├── learn           (学习路径)
        │   ├── practice        (练习中心)
        │   ├── projects        (融合项目)
        │   └── algo            (算法可视化)
        │
        ├── app.credentials     (凭证管理)
        └── app.python_runner   (代码沙箱)
```

---

## 核心模块

### app.config

**路径**: `app/config.py`
**职责**: 全局配置常量、路径管理、运行时目录初始化

**关键常量**:

| 常量 | 类型 | 说明 |
|------|------|------|
| `APP_NAME` | str | 应用名称 "DevLearnerAI" |
| `APP_VERSION` | str | 当前版本号 |
| `BASE_DIR` | Path | 项目源码根目录 |
| `RUNTIME_DIR` | Path | 运行时目录（开发/打包自适应） |
| `CONTENT_DIR` | Path | 课程内容根目录 |
| `METADATA_DIR` | Path | 元数据目录 |
| `DB_PATH` | Path | 数据库文件路径 |
| `LOG_DIR` | Path | 日志目录 |
| `USER_DATA_DIR` | Path | 用户数据根目录 |

**关键函数**:

```python
def ensure_runtime_dirs() -> None:
    """确保所有运行时目录存在。"""
```

---

### app.database

**路径**: `app/database.py`
**职责**: SQLite 数据库操作封装（线程安全）

**类**: `AppDatabase`

| 方法 | 说明 |
|------|------|
| `init_db()` | 初始化表结构、执行迁移 |
| `mark_lesson_opened(lesson_id, track_id)` | 标记课程为已打开 |
| `mark_lesson_completed(lesson_id, track_id)` | 标记课程为已完成 |
| `lesson_status(lesson_id)` | 查询课程状态 |
| `completed_lessons()` | 已完成课程数（带缓存） |
| `track_completion(track_id)` | 指定技术栈完成数 |
| `save_note(lesson_id, content)` | 保存课程笔记 |
| `load_note(lesson_id)` | 加载课程笔记 |
| `record_attempt(...)` | 记录练习评测 |
| `record_attempts_batch(records)` | 批量记录练习 |
| `recent_attempts(limit)` | 最近练习记录 |
| `save_exercise_draft(...)` | 保存练习草稿 |
| `load_exercise_draft(exercise_id)` | 加载练习草稿 |
| `average_score()` | 练习平均分（带缓存） |
| `active_days_streak()` | 连续学习天数（带缓存） |
| `save_api_config(host, key, model)` | 保存 AI API 配置 |
| `load_api_config()` | 加载 AI API 配置 |
| `list_mentor_sessions()` | 列出 AI 会话 |
| `create_mentor_session(name)` | 创建 AI 会话 |
| `delete_mentor_session(session_id)` | 删除 AI 会话 |
| `append_mentor_message(session_id, role, content)` | 追加消息 |
| `load_mentor_messages(session_id)` | 加载会话消息 |
| `trim_mentor_messages(session_id, keep_last)` | 裁剪旧消息 |
| `list_knowledge_files()` | 列出知识库文件 |
| `add_knowledge_file(name, path, excerpt)` | 添加知识库文件 |
| `reset_learning_progress()` | 重置所有学习数据 |

**模块级函数**:

```python
def get_connection(db_path: str) -> sqlite3.Connection  # 获取连接（单例）
def close_connection() -> None                           # 关闭连接
def now_text() -> str                                    # 当前时间文本
```

---

### app.content_service

**路径**: `app/content_service.py`
**职责**: 课程内容加载、数据模型构建、Markdown 缓存

**数据类**:

| 类 | 说明 |
|----|------|
| `Lesson` | 课程（id, title, summary, path, difficulty, ...） |
| `Module` | 模块（id, title, summary, lessons） |
| `Track` | 技术栈（id, title, icon, summary, modules） |

**类**: `ContentService`

| 方法 | 说明 |
|------|------|
| `tracks` | 所有技术栈（懒加载 + 缓存） |
| `track_by_id(track_id)` | 按 ID 查找技术栈 |
| `lesson_by_id(lesson_id)` | 按 ID 查找课程（O(1) 索引） |
| `lesson_markdown(lesson)` | 读取 Markdown 内容（带缓存） |
| `preload_adjacent_lessons(lesson_id)` | 预加载相邻课程 |
| `clear_markdown_cache()` | 清空 Markdown 缓存 |
| `all_lessons()` | 所有课程的扁平列表 |

---

### app.credentials

**路径**: `app/credentials.py`
**职责**: 跨平台凭证安全存储

| 函数 | 说明 |
|------|------|
| `save_secret(target, secret)` | 保存密钥 |
| `load_secret(target)` | 读取密钥 |
| `delete_secret(target)` | 删除密钥 |

存储优先级：Windows Credential Manager > keyring > Base64 文件回退

---

### app.python_runner

**路径**: `app/python_runner.py`
**职责**: Python 代码安全执行沙箱

| 函数 | 说明 |
|------|------|
| `run_python_code(code, timeout_sec=3)` | 沙箱执行代码 |
| `evaluate_python_code(code, nodes, names, tests, timeout_sec=4)` | 沙箱评测代码 |

**关键常量**:

| 常量 | 说明 |
|------|------|
| `ALLOWED_IMPORTS` | 允许导入的模块白名单 |
| `SAFE_BUILTINS` | 受限内置函数字典 |
| `_DANGEROUS_ATTRS` | 禁止访问的双下划线属性 |
| `_DANGEROUS_BUILTINS_CALLS` | 禁止调用的内置函数 |

---

### app.styles

**路径**: `app/styles.py`
**职责**: 全局样式定义（颜色、字体、主题）

**关键常量**:

| 常量 | 说明 |
|------|------|
| `FONT` | 主字体 "Microsoft YaHei UI" |
| `MONO_FONT` | 等宽字体 "Consolas" |
| `ACCENT` | 主题色 "#2563eb" |
| `GLOBAL_STYLE` | 全局样式表 |
| `SCORE_EXCELLENT` | 优秀分数线 90 |
| `SCORE_GOOD` | 良好分数线 70 |

**函数**:

```python
def build_style_for_size(size_name: str, dark: bool = False) -> str
def build_dark_style() -> str
```

---

## AI 子模块 (app/ai/)

### app.ai.api_client

**路径**: `app/ai/api_client.py`
**职责**: AI API HTTPS 通信

| 函数 | 说明 |
|------|------|
| `test_connection(host, key)` | 测试连接（带缓存） |
| `fetch_models(host, key)` | 获取模型列表 |
| `send_chat(host, key, model, messages, timeout)` | 非流式聊天 |
| `send_chat_stream(host, key, model, messages, on_chunk, timeout)` | 流式聊天 |
| `require_https(host)` | HTTPS 校验 |
| `clear_connection_cache()` | 清空连接缓存 |

### app.ai.markdown_renderer

**路径**: `app/ai/markdown_renderer.py`
**职责**: Markdown 渲染和 HTML 净化

| 函数 | 说明 |
|------|------|
| `sanitize_html(html)` | HTML 白名单净化 |
| `render_message_html(content, allow_markdown)` | 消息渲染为安全 HTML |
| `bubble_html(role, content)` | 构建聊天气泡 HTML |

### app.ai.models

**路径**: `app/ai/models.py`
**职责**: 数据类和安全常量

| 常量 | 说明 |
|------|------|
| `ALLOWED_TAGS` | HTML 白名单标签 |
| `STRIP_TAGS` | 需要移除的危险标签 |
| `RE_EVENT_ATTR` | 事件处理器正则 |
| `RE_JAVASCRIPT_URI` | javascript: URI 正则 |

### app.ai.chat_handler

**路径**: `app/ai/chat_handler.py`
**职责**: 对话 UI 组件（AIMentorPanel、AIMentorDock）

---

## 练习子模块 (app/practice/)

### app.practice.evaluator

**路径**: `app/practice/evaluator.py`
**职责**: 多语言代码评测

| 函数 | 说明 |
|------|------|
| `evaluate_python(exercise, code)` | Python 沙箱评测 |
| `evaluate_sql(exercise, code)` | SQL 真实执行评测 |
| `evaluate_keyword_code(exercise, code)` | C/C# 关键字评测 |
| `evaluate_sql_fixture(exercise, code, fixture)` | SQL Fixture 评测 |

### app.practice.exercise_loader

**路径**: `app/practice/exercise_loader.py`
**职责**: 练习数据加载和回退处理

| 函数 | 说明 |
|------|------|
| `load_exercises(metadata_path)` | 加载练习列表 |
| `get_exercise_fallbacks()` | 获取回退值（缓存） |
| `get_sql_query_fixtures()` | 获取 SQL Fixture（缓存） |

### app.practice.models

**路径**: `app/practice/models.py`
**职责**: 核心数据类

```python
@dataclass
class Exercise:
    id: str; title: str; track_id: str; difficulty: str
    prompt: str; lesson_id: str; hints: list[str]
    starter_code: str; expected_nodes: list[str]
    required_names: list[str]; tests: list[dict]
    required_keywords: list[str]; forbidden_keywords: list[str]

@dataclass
class EvaluationResult:
    passed: bool; score: int; feedback_lines: list[str]
    stdout: str; duration_sec: int
```

### app.practice.normalizer

**路径**: `app/practice/normalizer.py`
**职责**: SQL 结果集标准化

```python
def normalize_rows(rows: list, ordered: bool) -> list[tuple]
```

---

## Widget 子模块 (app/widgets/)

| 模块 | 路径 | 职责 |
|------|------|------|
| `dashboard` | `app/widgets/dashboard.py` | 学习仪表盘（进度、统计、快捷入口） |
| `learn` | `app/widgets/learn.py` | 学习路径（课程列表、Markdown 渲染、笔记） |
| `practice` | `app/widgets/practice.py` | 练习中心（代码编辑、评测、提示） |
| `projects` | `app/widgets/projects.py` | 融合项目展示 |
| `algo` | `app/widgets/algo.py` | 算法动画可视化 |

---

## 兼容层

### app.practice_service

**路径**: `app/practice_service.py`
**职责**: 练习服务的兼容 shim，委托到 `app/practice/` 子模块

```python
# 向后兼容的导入
from app.practice.evaluator import evaluate_python, evaluate_sql, evaluate_keyword_code
from app.practice.exercise_loader import load_exercises
```

---

## 相关文档

- [系统架构](../concepts/architecture.md) - 整体架构设计
- [数据库 Schema](database-schema.md) - 数据表结构
- [API 集成参考](api-integration.md) - AI API 通信详情
