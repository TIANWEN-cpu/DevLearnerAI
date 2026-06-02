"""共享类型定义模块。

集中定义项目中使用的类型别名、TypedDict 和 Protocol，
为所有模块提供统一的类型基础。

使用示例::

    from app.types import ExerciseData, LessonRow, ApiResponse

    def fetch_lesson(lesson_id: str) -> Optional[LessonRow]:
        ...
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, TypeAlias, Union

# ---------------------------------------------------------------------------
# 基础类型别名
# ---------------------------------------------------------------------------

# JSON 值类型（递归定义）
JsonValue: TypeAlias = Union[str, int, float, bool, None, list["JsonValue"], dict[str, "JsonValue"]]

# 通用的行 ID 类型
RowId: TypeAlias = int

# 通用的字符串 ID 类型（课程 ID、练习 ID 等）
StringId: TypeAlias = str

# ---------------------------------------------------------------------------
# 数据库行类型
# ---------------------------------------------------------------------------


class LessonProgressRow(Protocol):
    """课程进度数据库行协议。"""

    @property
    def lesson_id(self) -> str: ...
    @property
    def track_id(self) -> str: ...
    @property
    def status(self) -> str: ...
    @property
    def completed(self) -> int: ...
    @property
    def last_opened(self) -> Optional[str]: ...
    @property
    def completed_at(self) -> Optional[str]: ...


class MentorSessionRow(Protocol):
    """AI 会话数据库行协议。"""

    @property
    def id(self) -> int: ...
    @property
    def name(self) -> str: ...
    @property
    def created_at(self) -> str: ...
    @property
    def updated_at(self) -> str: ...


class MentorMessageRow(Protocol):
    """AI 消息数据库行协议。"""

    @property
    def id(self) -> int: ...
    @property
    def session_id(self) -> int: ...
    @property
    def role(self) -> str: ...
    @property
    def content(self) -> str: ...
    @property
    def created_at(self) -> str: ...


# ---------------------------------------------------------------------------
# API 响应类型
# ---------------------------------------------------------------------------


class ApiChatMessage(dict):
    """聊天消息字典（用于 API 请求）。

    Attributes:
        role: 消息角色 ('user', 'assistant', 'system')。
        content: 消息内容。
    """

    role: str
    content: str


class ApiChatResponse(dict):
    """API 聊天响应字典。

    Attributes:
        id: 响应 ID。
        choices: 选项列表。
        usage: 用量信息。
    """

    id: str
    choices: list[dict[str, Any]]
    usage: Optional[dict[str, int]]


class ApiModelInfo(dict):
    """API 模型信息字典。

    Attributes:
        id: 模型 ID。
        object: 对象类型。
        owned_by: 所有者。
    """

    id: str
    object: str
    owned_by: str


# ---------------------------------------------------------------------------
# 练习相关类型
# ---------------------------------------------------------------------------


class ExerciseTestData(dict):
    """练习测试用例字典。

    Attributes:
        expression: 要求值的表达式。
        expected: 期望结果。
    """

    expression: str
    expected: Any


class ExerciseFixture(dict):
    """SQL 练习 fixture 字典。

    Attributes:
        setup: 初始化 SQL 脚本。
        mode: 评测模式 ('query', 'script', 'ddl', 'explain')。
        expected_rows: 期望的结果行。
        ordered: 是否需要保持顺序。
        check_sql: 脚本模式下用于检查结果的 SQL。
    """

    setup: str
    mode: str
    expected_rows: Optional[list[tuple]]
    ordered: Optional[bool]
    check_sql: Optional[str]


class ExerciseFallback(dict):
    """练习回退数据字典。

    Attributes:
        title: 回退标题。
        difficulty: 回退难度。
        prompt: 回退提示。
        hints: 回退提示列表。
        starter_code: 回退起始代码。
        tests: 回退测试用例。
    """

    title: str
    difficulty: str
    prompt: str
    hints: list[str]
    starter_code: str
    tests: list[ExerciseTestData]


# ---------------------------------------------------------------------------
# 内容相关类型
# ---------------------------------------------------------------------------


class CourseMapModuleData(dict):
    """课程地图中的模块数据。

    Attributes:
        id: 模块 ID。
        title: 模块标题。
        summary: 模块简介。
        lessons: 课程列表。
    """

    id: str
    title: str
    summary: str
    lessons: list[dict[str, Any]]


class CourseMapTrackData(dict):
    """课程地图中的技术栈数据。

    Attributes:
        id: 技术栈 ID。
        title: 技术栈标题。
        icon: 图标标识。
        summary: 技术栈简介。
        modules: 模块列表。
    """

    id: str
    title: str
    icon: str
    summary: str
    modules: list[CourseMapModuleData]


# ---------------------------------------------------------------------------
# 代码执行结果类型
# ---------------------------------------------------------------------------


class ExecutionResult(dict):
    """Python 代码执行结果。

    Attributes:
        ok: 是否执行成功。
        stdout: 标准输出。
        error: 错误信息（失败时）。
        duration_sec: 执行耗时（秒）。
    """

    ok: bool
    stdout: str
    error: Optional[str]
    duration_sec: int


class EvaluationDictResult(dict):
    """Python 代码评测结果（字典形式）。

    Attributes:
        passed: 是否通过。
        score: 得分 (0-100)。
        feedback_lines: 反馈信息列表。
        stdout: 标准输出。
        duration_sec: 评测耗时（秒）。
    """

    passed: bool
    score: int
    feedback_lines: list[str]
    stdout: str
    duration_sec: int


# ---------------------------------------------------------------------------
# 成就相关类型
# ---------------------------------------------------------------------------


class AchievementData(dict):
    """成就数据字典。

    Attributes:
        id: 成就 ID。
        title: 成就标题。
        description: 成就描述。
        icon: 图标。
        category: 分类。
        threshold: 阈值。
        current_value: 当前进度值。
        unlocked: 是否已解锁。
        unlocked_at: 解锁时间。
    """

    id: str
    title: str
    description: str
    icon: str
    category: str
    threshold: int
    current_value: int
    unlocked: bool
    unlocked_at: str


# ---------------------------------------------------------------------------
# 导出/导入相关类型
# ---------------------------------------------------------------------------


class ExportData(dict):
    """导出数据字典结构。

    Attributes:
        version: 数据版本号。
        exported_at: 导出时间。
        lesson_progress: 课程进度列表。
        lesson_notes: 课程笔记列表。
        practice_attempts: 练习记录列表。
        bookmarks: 书签列表。
        achievements: 成就列表。
        review_schedule: 复习计划列表。
        exercise_timers: 练习用时列表。
    """

    version: str
    exported_at: str
    lesson_progress: list[dict[str, Any]]
    lesson_notes: list[dict[str, Any]]
    practice_attempts: list[dict[str, Any]]
    bookmarks: list[dict[str, Any]]
    achievements: list[dict[str, Any]]
    review_schedule: list[dict[str, Any]]
    exercise_timers: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# 插件相关类型
# ---------------------------------------------------------------------------


class PluginStatusInfo(dict):
    """插件状态摘要字典。

    Attributes:
        version: 插件版本号。
        state: 生命周期状态。
        error: 错误信息（如果出错）。
    """

    version: str
    state: str
    error: Optional[str]


# ---------------------------------------------------------------------------
# 连接测试结果类型
# ---------------------------------------------------------------------------


class MentorWorkspaceFlags(dict):
    """知识库启用标志字典。

    Attributes:
        use_base: 是否启用基础知识库。
        use_personal: 是否启用个性知识库。
        use_custom: 是否启用扩展文件知识库。
    """

    use_base: bool
    use_personal: bool
    use_custom: bool


# ---------------------------------------------------------------------------
# 数据库操作 Protocol
# ---------------------------------------------------------------------------


class DatabaseProtocol(Protocol):
    """数据库操作协议 -- 定义 AppDatabase 的接口契约。"""

    def fetchall(self, sql: str, params: tuple = ...) -> list[tuple]: ...
    def fetchone(self, sql: str, params: tuple = ...) -> Optional[tuple]: ...
    def execute(self, sql: str, params: tuple = ...) -> None: ...
    def connect(self) -> Any: ...


# ---------------------------------------------------------------------------
# 通用回调类型
# ---------------------------------------------------------------------------

# 事件处理器类型
EventHandler: TypeAlias = Any  # 实际为 Callable[[Event], None]，但需要延迟导入

# 流式回调类型
StreamCallback: TypeAlias = Any  # 实际为 Callable[[str], None]

# 验证函数类型
ValidationCheck: TypeAlias = Any  # 实际为 Callable[..., bool]
