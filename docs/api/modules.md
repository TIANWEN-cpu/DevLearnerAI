# 模块 API 参考文档

本文档覆盖 `app/` 下所有核心模块的公开接口。

---

## 目录

1. [app.ai -- AI 导师模块](#appai----ai-导师模块)
   - [app.ai.models](#appaimodels)
   - [app.ai.markdown_renderer](#appaimarkdown_renderer)
   - [app.ai.api_client](#appaiai_client)
   - [app.ai.chat_handler](#appaichat_handler)
2. [app.practice -- 练习模块](#apppractice----练习模块)
   - [app.practice.models](#apppracticemodels)
   - [app.practice.normalizer](#apppracticenormalizer)
   - [app.practice.exercise_loader](#apppracticeexercise_loader)
   - [app.practice.evaluator](#apppracticeevaluator)
3. [app.database](#appdatabase)
4. [app.python_runner](#apppython_runner)
5. [app.content_service](#appcontent_service)
6. [app.credentials](#appcredentials)

---

## app.ai -- AI 导师模块

包入口文件 `app/ai/__init__.py` 重新导出了所有子模块的公开名称。

### app.ai.models

定义 HTML 净化所需的安全常量和正则模式。

| 名称 | 类型 | 说明 |
|------|------|------|
| `ALLOWED_TAGS` | `frozenset[str]` | 白名单标签集合，包含 `p`, `br`, `h1`-`h6`, `ul`, `ol`, `li`, `code`, `pre`, `strong`, `em`, `b`, `i`, `a`, `blockquote`, `table`, `tr`, `td`, `th`, `thead`, `tbody`, `hr`, `span` |
| `STRIP_TAGS` | `frozenset[str]` | 必须整体剥离的危险标签：`script`, `style`, `iframe`, `object`, `embed` |
| `RE_EVENT_ATTR` | `re.Pattern[str]` | 匹配 `on*` 事件处理器属性 |
| `RE_JAVASCRIPT_URI` | `re.Pattern[str]` | 匹配 `javascript:` URI |
| `RE_DATA_URI` | `re.Pattern[str]` | 匹配 `data:` URI |
| `RE_VBSCRIPT_URI` | `re.Pattern[str]` | 匹配 `vbscript:` URI |

### app.ai.markdown_renderer

提供 Markdown 到 HTML 的渲染（基于 mistune）、白名单 HTML 净化（防 XSS）以及聊天消息气泡构建。

#### 类: `_HTMLSanitizer(HTMLParser)`

基于标准库 `html.parser.HTMLParser` 的白名单 HTML 净化器。

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `sanitize(html)` | `html: str` | `str` | 对 HTML 字符串执行白名单净化，返回安全 HTML |

内部过滤规则：
- 移除所有 `on*` 事件处理器
- `<a>` 标签仅保留安全的 `href`（http/https/相对路径）
- `<span>` 仅保留 `class` 属性
- `<script>`, `<style>`, `<iframe>` 等危险标签及其内容整体移除
- HTML 注释全部剥离

#### 函数

```python
def sanitize_html(html: str) -> str
```

对 HTML 字符串执行白名单净化。内部创建 `_HTMLSanitizer` 实例。

- **参数**: `html` -- 原始 HTML 字符串
- **返回**: 净化后的安全 HTML 字符串

```python
def render_message_html(content: str, allow_markdown: bool = True) -> str
```

将消息文本渲染为安全 HTML。当 `allow_markdown=True` 且 mistune 可用时使用 Markdown 渲染，否则纯文本转义。

- **参数**:
  - `content` -- 消息文本
  - `allow_markdown` -- 是否启用 Markdown 渲染，默认 `True`
- **返回**: 安全 HTML 字符串

```python
def bubble_html(role: str, content: str) -> str
```

构建单条聊天消息的 HTML 气泡块。`role="user"` 显示蓝色主题，`role="assistant"` 显示青色主题。

- **参数**:
  - `role` -- 角色，`"user"` 或 `"assistant"`
  - `content` -- 消息内容
- **返回**: 包含样式的完整 HTML 字符串

### app.ai.api_client

与 OpenAI 兼容 API 的通信模块。所有通信强制使用 HTTPS，启用 TLS 证书验证。

#### 函数

```python
def require_https(host: str) -> None
```

校验主机地址必须以 `https://` 开头，否则抛出 `ValueError`。

```python
def create_ssl_context() -> ssl.SSLContext
```

返回加固的 SSL 上下文，启用证书验证。

```python
def build_models_url(host: str) -> str
```

从主机地址构建 `/models` 端点 URL。如果 host 已包含 `/v1` 则直接拼接，否则自动添加 `/v1/models`。

```python
def build_chat_url(host: str) -> str
```

从主机地址构建 `/chat/completions` 端点 URL。逻辑同上。

```python
def test_connection(host: str, api_key: str) -> str
```

测试 API 连接，返回状态消息字符串。结果缓存 5 分钟。

- **参数**:
  - `host` -- API 主机 URL
  - `api_key` -- API 密钥
- **返回**: 状态消息，如 `"连接成功，状态码 200。"` 或错误提示

```python
def fetch_models(host: str, api_key: str) -> list[str]
```

获取可用模型 ID 列表，按字母排序。失败时抛出异常。

- **参数**:
  - `host` -- API 主机 URL
  - `api_key` -- API 密钥
- **返回**: 模型 ID 字符串列表

```python
def send_chat(host: str, api_key: str, model: str,
              messages: list[dict[str, str]], timeout: int = 90) -> str
```

发送聊天补全请求（非流式）。包含请求去重机制：相同请求并发时只发送一次，其余等待结果。

- **参数**:
  - `host` -- API 主机 URL
  - `api_key` -- API 密钥
  - `model` -- 模型名称
  - `messages` -- 消息列表，每项包含 `role` 和 `content`
  - `timeout` -- 超时秒数，默认 90
- **返回**: 助手回复文本
- **异常**: `ValueError`（HTTPS 违规）、HTTP/网络错误

```python
def send_chat_stream(host: str, api_key: str, model: str,
                     messages: list[dict[str, str]],
                     on_chunk: callable, timeout: int = 90) -> str
```

发送流式聊天请求。通过 SSE 接收分块数据，每收到一个 delta 内容块就调用 `on_chunk(text)` 回调。流式失败时自动回退到非流式模式。

- **参数**:
  - `host` -- API 主机 URL
  - `api_key` -- API 密钥
  - `model` -- 模型名称
  - `messages` -- 消息列表
  - `on_chunk` -- 接收文本块的回调函数
  - `timeout` -- 超时秒数，默认 90
- **返回**: 组装后的完整回复文本

```python
def clear_connection_cache() -> None
```

清除连接状态缓存。

### app.ai.chat_handler

AI 导师的 PyQt5 UI 组件。

#### 类: `AIMentorPanel(QWidget)`

AI 导师主面板，支持 `"page"`（独立页面）和 `"dock"`（侧边停靠）两种模式。

**构造函数**:
```python
def __init__(self, db: AppDatabase, content_service: ContentService,
             mode: str = "dock", parent: Optional[QWidget] = None) -> None
```

**信号**:

| 信号 | 参数 | 说明 |
|------|------|------|
| `request_open_page` | 无 | 请求切换到独立页面模式 |
| `request_open_dock` | 无 | 请求切换到侧边停靠模式 |
| `response_ready` | `int` (session_id) | AI 回复就绪 |
| `models_ready` | `list` | 模型列表获取完成 |
| `status_ready` | `str` | 设置状态消息 |
| `stream_chunk_ready` | `str` | 流式文本块到达 |

**主要公开方法**:

| 方法 | 说明 |
|------|------|
| `save_config()` | 保存当前 API 配置（Host、Key、Model） |
| `test_connection()` | 异步测试 API 连接 |
| `fetch_models()` | 异步获取模型列表 |
| `send_message()` | 发送当前输入框中的消息 |
| `refresh_shared_state()` | 从数据库刷新所有 UI 状态 |

#### 类: `AIMentorDock(QDockWidget)`

侧边停靠式 AI 助手容器。

**构造函数**:
```python
def __init__(self, db: AppDatabase, content_service: ContentService,
             parent: Optional[QWidget] = None) -> None
```

**属性**:
- `input` (`LocalizedLineEdit`): 内部的输入框控件
- `panel` (`AIMentorPanel`): 内部的面板实例

---

## app.practice -- 练习模块

包入口文件 `app/practice/__init__.py` 重新导出了所有子模块的公开名称。

### app.practice.models

#### 数据类: `Exercise`

表示单个编码练习。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `id` | `str` | (必填) | 练习唯一标识 |
| `title` | `str` | (必填) | 练习标题 |
| `track_id` | `str` | (必填) | 所属技术栈 ID |
| `difficulty` | `str` | (必填) | 难度级别 |
| `prompt` | `str` | (必填) | 练习题目描述 |
| `lesson_id` | `str` | (必填) | 关联课程 ID |
| `hints` | `list[str]` | `[]` | 提示列表 |
| `starter_code` | `str` | `""` | 起始代码 |
| `expected_nodes` | `list[str]` | `[]` | 期望的 AST 节点类型（Python 评测用） |
| `required_names` | `list[str]` | `[]` | 期望定义的名称（Python 评测用） |
| `tests` | `list[dict]` | `[]` | 测试用例列表（Python 评测用） |
| `required_keywords` | `list[str]` | `[]` | 必须包含的关键字（SQL/C#/C 评测用） |
| `forbidden_keywords` | `list[str]` | `[]` | 禁止使用的关键字 |

#### 数据类: `EvaluationResult`

评测结果。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `passed` | `bool` | (必填) | 是否通过 |
| `score` | `int` | (必填) | 得分（0-100） |
| `feedback_lines` | `list[str]` | (必填) | 反馈文本列表 |
| `stdout` | `str` | `""` | 标准输出 |
| `duration_sec` | `int` | `0` | 评测耗时（秒） |

**属性**:
- `feedback_text` (`str`): 将 `feedback_lines` 用换行符拼接的文本

### app.practice.normalizer

SQL 结果集标准化工具。

```python
def normalize_rows(rows: list, ordered: bool) -> list[tuple]
```

将 SQL 结果行标准化为元组列表。当 `ordered=False` 时按字典序排序，`None` 值视为空字符串。

- **参数**:
  - `rows` -- SQL 查询结果行列表
  - `ordered` -- 是否保持原始顺序
- **返回**: 标准化后的元组列表

### app.practice.exercise_loader

练习数据加载和回退处理。

```python
def load_json_resource(filename: str) -> dict
```

从 `METADATA_DIR` 加载 JSON 资源文件。文件不存在或解析失败时返回空字典。

```python
@functools.lru_cache(maxsize=1)
def get_exercise_fallbacks() -> dict
```

返回练习回退定义（带缓存），用于修复编码损坏的数据。

```python
@functools.lru_cache(maxsize=1)
def get_sql_query_fixtures() -> dict
```

返回 SQL 查询 fixture（带缓存），包含 `setup`、`expected_rows` 等评测数据。JSON 中的 list 会自动转为 tuple。

```python
def needs_fallback(value: str) -> bool
```

检测文本是否包含编码损坏标记（`?` 字符）。

```python
def load_exercises(metadata_path: Optional[Path] = None) -> list[Exercise]
```

加载练习元数据并自动修复编码损坏字段。从 `METADATA_DIR/exercises.json` 加载，使用 `exercise_fallbacks.json` 中的回退值替换损坏的 `title`、`difficulty`、`prompt`、`hints`、`starter_code`、`tests` 字段。

### app.practice.evaluator

多语言代码评测逻辑。

```python
def validate_sql_side_effect(exercise_id: str, conn: sqlite3.Connection) -> bool
```

验证 DDL 练习是否产生了预期的数据库结构变更。支持的练习 ID 包括：
- `db-design-enrollment-table` -- 验证 enrollments 表包含 `student_id` 和 `course_id`
- `db-orders-foreign-key` -- 验证 orders 表的外键约束
- `db-create-index-users-email` -- 验证 users 表的 email 索引
- `db-add-column-migration` -- 验证 users 表包含 `last_login` 列
- `db-create-covering-index-report` -- 验证 reports 表的覆盖索引
- `db-add-status-column-users` -- 验证 users 表包含 `status` 列
- `db-create-enrollment-foreign-key` -- 验证 enrollments 表的双外键
- `db-explain-users-query` -- 验证 EXPLAIN QUERY PLAN 有输出

```python
def evaluate_sql_fixture(exercise: Exercise, code: str, fixture: dict) -> EvaluationResult
```

使用已知 fixture 评测 SQL 答案。支持三种模式：
- `query` -- 直接执行查询并比对结果集
- `script` -- 执行脚本后通过 check_sql 验证落库结果
- `explain` -- 验证 EXPLAIN 查询有输出

评分维度：关键字覆盖 20 分 + 禁用关键字检查 10 分 + 结果比对 70 分 + 语句格式 5 分。通过条件：总分 >= 70 且无缺失关键字且无禁用关键字且无执行失败。

```python
def evaluate_sql(exercise: Exercise, code: str) -> EvaluationResult
```

SQL 评测调度器。优先使用 fixture 评测，其次对已知 DDL 题目构造临时 fixture，最后回退到关键字结构检查。

```python
def evaluate_keyword_code(exercise: Exercise, code: str) -> EvaluationResult
```

C/C# 代码关键字评测。检查必需结构和禁用关键字，不执行真实编译。

```python
def evaluate_python(exercise: Exercise, code: str) -> EvaluationResult
```

Python 代码评测，委托给 `python_runner.evaluate_python_code()` 执行沙箱评测。

---

## app.database

SQLite 数据库操作模块（线程安全）。使用 WAL 模式和写锁确保多线程数据一致性。

### 模块级函数

```python
def get_connection(db_path: str) -> sqlite3.Connection
```

获取或创建数据库连接（线程安全的单例模式）。启用外键约束和 WAL 日志模式。连接失效时自动重建。

```python
def close_connection() -> None
```

关闭全局数据库连接，通常在应用退出时调用。

```python
def now_text() -> str
```

返回当前时间的文本表示，格式 `YYYY-MM-DD HH:MM:SS`。

### 类: `AppDatabase`

应用数据库操作封装。所有写操作自动获得写锁并提交/回滚。

**构造函数**:
```python
def __init__(self, db_path=DB_PATH) -> None
```
初始化时自动执行旧版数据库迁移（如存在）。

#### 基础查询方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `fetchall(sql, params)` | `sql: str`, `params: Sequence` | `list[tuple]` | 执行查询返回所有行 |
| `fetchone(sql, params)` | `sql: str`, `params: Sequence` | `Optional[tuple]` | 执行查询返回单行 |
| `execute(sql, params)` | `sql: str`, `params: Sequence` | `None` | 执行非查询语句 |

#### 初始化

```python
def init_db(self) -> None
```

初始化数据库表结构：创建所有表、执行列迁移、迁移旧版 API 密钥、修复损坏的聊天记录、确保默认会话存在。

#### 课程进度管理

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `mark_lesson_opened(lesson_id, track_id)` | `str`, `str` | `None` | 标记课程为已打开 |
| `mark_lesson_completed(lesson_id, track_id)` | `str`, `str` | `None` | 标记课程为已完成 |
| `lesson_status(lesson_id)` | `str` | `str` | 查询课程状态 |
| `track_completion(track_id)` | `str` | `int` | 统计技术栈完成数 |
| `completed_lessons()` | 无 | `int` | 总完成课程数（带缓存） |
| `list_completed_lessons()` | 无 | `list[tuple]` | 已完成课程列表 |
| `save_note(lesson_id, content)` | `str`, `str` | `None` | 保存课程笔记 |
| `load_note(lesson_id)` | `str` | `str` | 加载课程笔记 |

#### 练习记录管理

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `record_attempt(...)` | 8 个参数 | `None` | 记录单次评测结果 |
| `record_attempts_batch(records)` | `list[tuple]` | `None` | 批量记录评测结果 |
| `recent_attempts(limit)` | `int=10` | `list[tuple]` | 获取最近练习记录 |
| `save_exercise_draft(...)` | 3 个参数 | `None` | 保存练习草稿 |
| `load_exercise_draft(exercise_id)` | `str` | `Optional[tuple]` | 加载练习草稿 |
| `clear_exercise_draft(exercise_id)` | `str` | `None` | 清除练习草稿 |
| `average_score()` | 无 | `int` | 平均分（带缓存） |
| `active_days_streak()` | 无 | `int` | 连续学习天数（带缓存） |
| `reset_learning_progress()` | 无 | `None` | 重置所有学习进度 |

#### AI 会话管理

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `list_mentor_sessions()` | 无 | `list[tuple[int,str,str]]` | 列出所有会话 |
| `mentor_session_snapshot(session_id)` | `int` | `dict` | 会话摘要快照 |
| `create_mentor_session(name)` | `str` | `int` | 创建会话，返回 ID |
| `rename_mentor_session(session_id, name)` | `int`, `str` | `None` | 重命名会话 |
| `delete_mentor_session(session_id)` | `int` | `None` | 删除会话及消息 |
| `set_active_mentor_session(session_id)` | `int` | `None` | 设置活跃会话 |
| `load_active_mentor_session_id()` | 无 | `Optional[int]` | 加载活跃会话 ID |
| `append_mentor_message(session_id, role, content)` | `int`, `str`, `str` | `None` | 追加消息 |
| `load_mentor_messages(session_id)` | `int` | `list[tuple[str,str,str]]` | 加载会话消息 |
| `trim_mentor_messages(session_id, keep_last)` | `int`, `int=200` | `int` | 裁剪旧消息 |
| `repair_corrupted_mentor_history()` | 无 | `None` | 修复损坏消息 |

#### API 配置与知识库

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `save_api_config(host, api_key, model)` | `str`, `str`, `str` | `None` | 保存 API 配置（密钥存 keyring） |
| `load_api_config()` | 无 | `tuple[str,str,str]` | 加载 API 配置 |
| `save_mentor_workspace_flags(...)` | `bool`, `bool`, `bool` | `None` | 保存知识库标志 |
| `load_mentor_workspace_flags()` | 无 | `dict` | 加载知识库标志 |
| `list_knowledge_files()` | 无 | `list[tuple]` | 列出知识库文件 |
| `get_knowledge_file(file_id)` | `int` | `Optional[tuple]` | 获取文件详情 |
| `add_knowledge_file(...)` | `str`, `str`, `str` | `None` | 添加知识库文件 |
| `remove_knowledge_file(file_id)` | `int` | `None` | 移除知识库文件 |

---

## app.python_runner

Python 代码执行沙箱模块。通过多层防护确保用户代码安全执行。

### 常量

```python
ALLOWED_IMPORTS = {
    "argparse", "collections", "datetime", "functools",
    "itertools", "json", "logging", "math", "pathlib",
    "re", "statistics",
}
```

允许在沙箱中导入的模块白名单。

```python
SAFE_BUILTINS: dict
```

受限的内置函数字典，包含：`print`, `len`, `range`, `int`, `float`, `str`, `bool`, `list`, `dict`, `tuple`, `set`, `sorted`, `enumerate`, `zip`, `map`, `filter`, `sum`, `min`, `max`, `abs`, `round`, `isinstance`, `all`, `any`, `reversed`, `Exception`, `TypeError`, `ValueError`。

### 类: `LimitedBuffer(io.StringIO)`

限制写入量的字符串缓冲区。超过限制时抛出 `RuntimeError`。

```python
def __init__(self, limit: int = 12000) -> None
```

- **参数**: `limit` -- 最大写入字节数，默认 12000

### 公开函数

```python
def run_python_code(code: str, timeout_sec: int = 3) -> dict
```

在沙箱中执行 Python 代码。通过子进程隔离，支持超时控制。

- **参数**:
  - `code` -- Python 代码字符串
  - `timeout_sec` -- 超时秒数，默认 3
- **返回**: 包含 `ok`（`bool`）、`stdout`（`str`）、`error`（`str`）、`duration_sec`（`int`）的字典

```python
def evaluate_python_code(code: str, expected_nodes, required_names,
                         tests, timeout_sec: int = 4) -> dict
```

在沙箱中评测 Python 代码。评测流程：语法检查 -> 结构检查 -> 安全执行 -> 对象检查 -> 测试用例求值。

- **参数**:
  - `code` -- Python 代码字符串
  - `expected_nodes` -- 期望的 AST 节点类型列表（如 `["FunctionDef", "For"]`）
  - `required_names` -- 期望在命名空间中定义的名称列表（如 `["MyClass", "greet"]`）
  - `tests` -- 测试用例列表，每项包含 `expression`（`str`）和 `expected`（任意）
  - `timeout_sec` -- 超时秒数，默认 4
- **返回**: 包含 `passed`（`bool`）、`score`（`int`，0-100）、`feedback_lines`（`list[str]`）、`stdout`（`str`）、`duration_sec`（`int`）的字典

**评分维度**:
- 语法检查通过: 20 分
- 代码结构符合要求: 20 分
- 代码可成功执行: 10 分
- 关键对象已定义: 10 分
- 测试用例通过: 40 分（按比例）

通过条件：总分 >= 70 且所有测试用例通过 且无缺失结构 且无缺失名称。

```python
def cli_main() -> None
```

命令行入口点，供子进程回退方案调用。从 JSON payload 文件读取模式和参数执行。

---

## app.content_service

课程内容加载与管理模块。

### 数据类

#### `Lesson`

课程数据模型（最小学习单元）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 课程唯一标识 |
| `title` | `str` | 课程标题 |
| `summary` | `str` | 课程简介 |
| `path` | `str` | Markdown 文件相对路径 |
| `difficulty` | `str` | 难度级别 |
| `estimated_minutes` | `int` | 预估学习时间（分钟） |
| `tags` | `list[str]` | 标签列表 |
| `prerequisites` | `list[str]` | 前置课程 ID |
| `outcomes` | `list[str]` | 学习目标 |

#### `Module`

课程模块数据模型。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 模块唯一标识 |
| `title` | `str` | 模块标题 |
| `summary` | `str` | 模块简介 |
| `lessons` | `list[Lesson]` | 包含的课程列表 |

**属性**:
- `key` (`str`): 返回模块 ID

#### `Track`

技术栈数据模型（顶层组织单元）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 技术栈唯一标识 |
| `title` | `str` | 技术栈标题 |
| `icon` | `str` | 图标标识 |
| `summary` | `str` | 技术栈简介 |
| `modules` | `list[Module]` | 包含的模块列表 |

**属性**:
- `lessons` (`list[Lesson]`): 该技术栈下所有课程的扁平列表

### 类: `ContentService`

课程内容服务，支持懒加载和缓存。

**构造函数**:
```python
def __init__(self, metadata_path: Optional[Path] = None) -> None
```

默认从 `METADATA_DIR / "course_map.json"` 加载元数据。

**属性**:
- `tracks` (`list[Track]`): 所有技术栈（懒加载 + 缓存）

**方法**:

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `track_by_id(track_id)` | `str` | `Optional[Track]` | 按 ID 查找技术栈 |
| `lesson_by_id(lesson_id)` | `str` | `Optional[tuple[Track,Module,Lesson]]` | O(1) 查找课程 |
| `lesson_markdown(lesson)` | `Lesson` | `str` | 读取课程 Markdown（带缓存，最多 64 条） |
| `preload_adjacent_lessons(lesson_id)` | `str` | `None` | 预加载相邻课程 |
| `clear_markdown_cache()` | 无 | `None` | 清空 Markdown 缓存 |
| `all_lessons()` | 无 | `list[tuple[Track,Module,Lesson]]` | 所有课程的扁平列表 |

---

## app.credentials

凭证安全存储模块。

**存储优先级**:
1. Windows: Windows Credential Manager（加密存储）
2. 非 Windows + keyring 已安装: keyring 后端
3. 回退: Base64 编码的明文文件（`~/.devlearnerai/api_key.txt`）

### 函数

```python
def save_secret(target: str, secret: str, username: str = "DevLearnerAI") -> None
```

保存密钥到安全存储。

- **参数**:
  - `target` -- 存储目标标识（如 `DevLearnerAI:mentor_api_key`）
  - `secret` -- 密钥值
  - `username` -- Windows Credential Manager 的用户名，默认 `"DevLearnerAI"`
- **异常**: `OSError`（Windows 存储失败时）

```python
def load_secret(target: str) -> Optional[str]
```

从安全存储读取密钥。

- **参数**: `target` -- 存储目标标识
- **返回**: 密钥值，不存在时返回 `None`
- **异常**: `OSError`（Windows 读取失败时，NOT_FOUND 除外）

```python
def delete_secret(target: str) -> bool
```

从安全存储删除密钥。

- **参数**: `target` -- 存储目标标识
- **返回**: `True` 表示成功删除，`False` 表示目标不存在
- **异常**: `OSError`（Windows 删除失败时，NOT_FOUND 除外）
