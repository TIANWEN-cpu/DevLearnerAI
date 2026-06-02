"""演示数据加载模块。

提供一键加载演示数据的功能，用于展示 DevLearner AI 的完整学习体验。
包含三个难度级别的学习场景、一个"完成第一周"的进度数据和 AI 导师对话示例。
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from app.config import METADATA_DIR
from app.database import AppDatabase

logger = logging.getLogger(__name__)

DEMO_SCENARIOS_PATH = METADATA_DIR / "demo_scenarios.json"

# ---------------------------------------------------------------------------
# Helper: timestamps
# ---------------------------------------------------------------------------


def _day_ts(day_offset: int, hour: int = 10, minute: int = 0) -> str:
    """Return a timestamp string N days before today at a given hour:minute."""
    dt = datetime.now() - timedelta(days=day_offset)
    return dt.replace(hour=hour, minute=minute, second=0).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Scenario data (embedded so no extra JSON dependency at runtime)
# ---------------------------------------------------------------------------


def load_scenarios() -> dict[str, Any]:
    """Load demo scenario metadata from JSON file."""
    if DEMO_SCENARIOS_PATH.exists():
        with open(DEMO_SCENARIOS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"scenarios": {}, "demo_user": {}}


# ---------------------------------------------------------------------------
# Demo progress: "Completed Week 1" Python beginner
# ---------------------------------------------------------------------------


def _build_week1_progress() -> dict[str, Any]:
    """Build progress data for a user who completed week 1 of Python basics."""

    # Day 1 (6 days ago): Environment setup + Variables
    # Day 2 (5 days ago): Control flow
    # Day 3 (4 days ago): Functions
    # Day 4 (3 days ago): Exceptions & files + first exercises
    # Day 5 (2 days ago): Lists & tuples
    # Day 6 (1 day ago): Dicts & sets + more exercises
    # Day 7 (today): Review + final exercises

    lesson_progress = [
        # Completed lessons (Python foundations module)
        {
            "lesson_id": "py-thinking",
            "track_id": "python",
            "status": "completed",
            "completed": 1,
            "last_opened": _day_ts(6, 10, 15),
            "completed_at": _day_ts(6, 10, 45),
        },
        {
            "lesson_id": "py-data-types",
            "track_id": "python",
            "status": "completed",
            "completed": 1,
            "last_opened": _day_ts(6, 14, 0),
            "completed_at": _day_ts(6, 14, 35),
        },
        {
            "lesson_id": "py-control-flow",
            "track_id": "python",
            "status": "completed",
            "completed": 1,
            "last_opened": _day_ts(5, 9, 30),
            "completed_at": _day_ts(5, 10, 10),
        },
        {
            "lesson_id": "py-functions",
            "track_id": "python",
            "status": "completed",
            "completed": 1,
            "last_opened": _day_ts(4, 15, 0),
            "completed_at": _day_ts(4, 15, 40),
        },
        {
            "lesson_id": "py-exceptions-files",
            "track_id": "python",
            "status": "completed",
            "completed": 1,
            "last_opened": _day_ts(3, 10, 0),
            "completed_at": _day_ts(3, 10, 42),
        },
        # In-progress lesson (core module)
        {
            "lesson_id": "py-lists-tuples",
            "track_id": "python",
            "status": "completed",
            "completed": 1,
            "last_opened": _day_ts(2, 16, 0),
            "completed_at": _day_ts(2, 16, 40),
        },
        {
            "lesson_id": "py-dicts-sets",
            "track_id": "python",
            "status": "completed",
            "completed": 1,
            "last_opened": _day_ts(1, 9, 0),
            "completed_at": _day_ts(1, 9, 38),
        },
        # Currently reading
        {
            "lesson_id": "py-iterators-generators",
            "track_id": "python",
            "status": "in_progress",
            "completed": 0,
            "last_opened": _day_ts(0, 14, 0),
            "completed_at": None,
        },
    ]

    # Practice attempts -- realistic scores showing improvement over time
    practice_attempts = [
        # Day 3: First exercises (lower scores)
        {
            "exercise_id": "py-add",
            "exercise_title": "实现 add 函数",
            "track_id": "python",
            "code_snapshot": "def add(a, b):\n    return a + b",
            "score": 100,
            "passed": 1,
            "duration_sec": 45,
            "submitted_at": _day_ts(3, 11, 0),
            "feedback": "完美！函数定义正确，使用 return 返回结果。",
        },
        {
            "exercise_id": "py-normalize-name",
            "exercise_title": "清洗用户名",
            "track_id": "python",
            "code_snapshot": "def normalize_name(text):\n    return text.strip().capitalize()",
            "score": 85,
            "passed": 1,
            "duration_sec": 120,
            "submitted_at": _day_ts(3, 11, 15),
            "feedback": "基本正确。注意 capitalize() 在处理全大写时表现良好。",
        },
        {
            "exercise_id": "py-even-sum",
            "exercise_title": "计算偶数和",
            "track_id": "python",
            "code_snapshot": "def even_sum(numbers):\n    total = 0\n    for x in numbers:\n        if x % 2 == 0:\n            total += x\n    return total",
            "score": 100,
            "passed": 1,
            "duration_sec": 90,
            "submitted_at": _day_ts(3, 11, 35),
            "feedback": "很好！循环 + 条件判断 + 累加，逻辑清晰。",
        },
        # Day 4: More exercises (improving)
        {
            "exercise_id": "py-count-vowels",
            "exercise_title": "统计元音字母",
            "track_id": "python",
            "code_snapshot": "def count_vowels(text):\n    return sum(1 for c in text.lower() if c in 'aeiou')",
            "score": 100,
            "passed": 1,
            "duration_sec": 65,
            "submitted_at": _day_ts(4, 16, 0),
            "feedback": "出色的解法！使用生成器表达式非常 Pythonic。",
        },
        {
            "exercise_id": "py-safe-divide",
            "exercise_title": "安全除法",
            "track_id": "python",
            "code_snapshot": "def safe_divide(a, b):\n    try:\n        return a / b\n    except ZeroDivisionError:\n        return 'cannot divide by zero'",
            "score": 100,
            "passed": 1,
            "duration_sec": 80,
            "submitted_at": _day_ts(4, 16, 20),
            "feedback": "正确使用了 try/except 异常处理。很好！",
        },
        # Day 5: Word count exercise
        {
            "exercise_id": "py-word-count",
            "exercise_title": "统计单词数量",
            "track_id": "python",
            "code_snapshot": "def word_count(text):\n    text = text.strip()\n    if not text:\n        return 0\n    return len(text.split())",
            "score": 100,
            "passed": 1,
            "duration_sec": 55,
            "submitted_at": _day_ts(5, 10, 30),
            "feedback": "完美处理了空字符串和首尾空格的情况。",
        },
        # Day 6: OOP exercise (first attempt at classes)
        {
            "exercise_id": "py-bank-account",
            "exercise_title": "定义一个简单账户类",
            "track_id": "python",
            "code_snapshot": "class BankAccount:\n    def __init__(self, balance):\n        self.balance = balance\n\n    def deposit(self, amount):\n        self.balance += amount\n        return self.balance",
            "score": 75,
            "passed": 1,
            "duration_sec": 180,
            "submitted_at": _day_ts(1, 10, 0),
            "feedback": "逻辑正确，但可以考虑加上金额校验（amount > 0）。",
        },
        # Day 7: Build user exercise
        {
            "exercise_id": "py-build-user",
            "exercise_title": "构造可序列化用户对象",
            "track_id": "python",
            "code_snapshot": "def build_user(name, age):\n    return {'name': name, 'age': age, 'active': True}",
            "score": 100,
            "passed": 1,
            "duration_sec": 30,
            "submitted_at": _day_ts(0, 15, 0),
            "feedback": "简洁明了，完全正确！",
        },
        # Day 7: Unique ordered (lists lesson)
        {
            "exercise_id": "py-unique-ordered",
            "exercise_title": "去重但保留顺序",
            "track_id": "python",
            "code_snapshot": "def unique_ordered(items):\n    seen = set()\n    result = []\n    for item in items:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result",
            "score": 100,
            "passed": 1,
            "duration_sec": 110,
            "submitted_at": _day_ts(0, 15, 30),
            "feedback": "非常好！集合 + 列表的经典组合用法。",
        },
    ]

    # Lesson notes (demonstrate the note-taking feature)
    lesson_notes = [
        {
            "lesson_id": "py-data-types",
            "content": "## 重点记录\n\n- 变量是标签，不是盒子\n- int、float、str、bool 四种基础类型\n- f-string 是格式化首选\n- Python 是动态类型语言，不需要声明类型\n\n## 易错点\n- `1 / 2` 结果是 `0.5`（float），不是 `0`\n- `True + True = 2`（布尔是 int 的子类）",
            "tags": "Python,基础,变量",
            "code_snippets": "x = 42          # int\ny = 3.14        # float\nname = 'Alice'  # str\nflag = True     # bool",
            "updated_at": _day_ts(6, 15, 0),
        },
        {
            "lesson_id": "py-functions",
            "content": "## 函数核心概念\n\n1. **参数类型**：位置参数、关键字参数、默认参数、*args、**kwargs\n2. **返回值**：没有 return 则返回 None\n3. **作用域**：LEGB 规则（Local > Enclosing > Global > Built-in）\n4. **模块导入**：import / from ... import\n\n## 学习心得\n函数是代码复用的基础，写函数时要注意单一职责原则。",
            "tags": "Python,函数,作用域",
            "code_snippets": "def greet(name, greeting='Hello'):\n    return f'{greeting}, {name}!'\n\n# *args 和 **kwargs\ndef show(*args, **kwargs):\n    print(args, kwargs)",
            "updated_at": _day_ts(4, 16, 0),
        },
        {
            "lesson_id": "py-exceptions-files",
            "content": "## 异常处理模式\n\n- try/except/else/finally 完整结构\n- 捕获具体异常优于裸 except\n- 上下文管理器 with 管理资源生命周期\n\n## 文件操作备忘\n- `open()` 默认文本模式，用 `encoding='utf-8'` 避免编码问题\n- 优先用 `with open() as f:` 自动关闭文件",
            "tags": "Python,异常,文件IO",
            "code_snippets": "try:\n    result = 10 / 0\nexcept ZeroDivisionError as e:\n    print(f'Error: {e}')\nfinally:\n    print('Done')",
            "updated_at": _day_ts(3, 11, 0),
        },
    ]

    # Bookmarks
    bookmarks = [
        {
            "item_type": "lesson",
            "item_id": "py-functions",
            "title": "函数与模块化",
            "track_id": "python",
            "note": "重要！LEGB 作用域规则需要反复练习",
            "created_at": _day_ts(4, 16, 30),
        },
        {
            "item_type": "lesson",
            "item_id": "py-control-flow",
            "title": "流程控制与循环",
            "track_id": "python",
            "note": "列表推导式的笔记待补充",
            "created_at": _day_ts(5, 10, 15),
        },
        {
            "item_type": "exercise",
            "item_id": "py-bank-account",
            "title": "定义一个简单账户类",
            "track_id": "python",
            "note": "需要复习：类的 __init__ 和 self 的用法",
            "created_at": _day_ts(1, 10, 5),
        },
    ]

    # Achievement progress (partial unlocks for realism)
    achievements = [
        ("first_lesson", 7, 1, _day_ts(6, 10, 45)),
        ("lessons_5", 7, 1, _day_ts(2, 16, 40)),
        ("lessons_10", 7, 0, None),
        ("first_exercise", 9, 1, _day_ts(3, 11, 0)),
        ("exercises_10", 9, 0, None),
        ("perfect_score", 6, 1, _day_ts(3, 11, 0)),
        ("streak_3", 7, 1, _day_ts(4, 16, 0)),
        ("streak_7", 7, 1, _day_ts(0, 15, 30)),
        ("first_bookmark", 3, 1, _day_ts(5, 10, 15)),
        ("notes_5", 3, 0, None),
        ("speed_demon", 1, 1, _day_ts(0, 15, 0)),
    ]

    # Daily analytics
    analytics_daily = [
        {
            "date": _day_ts(6, 0, 0)[:10],
            "learning_time_sec": 2700,
            "lessons_completed": 2,
            "exercises_completed": 0,
            "exercise_score_sum": 0,
        },
        {
            "date": _day_ts(5, 0, 0)[:10],
            "learning_time_sec": 2400,
            "lessons_completed": 1,
            "exercises_completed": 0,
            "exercise_score_sum": 0,
        },
        {
            "date": _day_ts(4, 0, 0)[:10],
            "learning_time_sec": 3600,
            "lessons_completed": 1,
            "exercises_completed": 2,
            "exercise_score_sum": 200,
        },
        {
            "date": _day_ts(3, 0, 0)[:10],
            "learning_time_sec": 3300,
            "lessons_completed": 1,
            "exercises_completed": 3,
            "exercise_score_sum": 285,
        },
        {
            "date": _day_ts(2, 0, 0)[:10],
            "learning_time_sec": 2400,
            "lessons_completed": 1,
            "exercises_completed": 1,
            "exercise_score_sum": 100,
        },
        {
            "date": _day_ts(1, 0, 0)[:10],
            "learning_time_sec": 2700,
            "lessons_completed": 1,
            "exercises_completed": 1,
            "exercise_score_sum": 75,
        },
        {
            "date": _day_ts(0, 0, 0)[:10],
            "learning_time_sec": 3600,
            "lessons_completed": 0,
            "exercises_completed": 2,
            "exercise_score_sum": 200,
        },
    ]

    return {
        "lesson_progress": lesson_progress,
        "practice_attempts": practice_attempts,
        "lesson_notes": lesson_notes,
        "bookmarks": bookmarks,
        "achievements": achievements,
        "analytics_daily": analytics_daily,
    }


# ---------------------------------------------------------------------------
# Demo AI conversations
# ---------------------------------------------------------------------------


def _build_demo_conversations() -> list[dict[str, Any]]:
    """Build demo mentor session data showing good Q&A patterns."""

    conversations = [
        {
            "name": "Python 变量和类型答疑",
            "messages": [
                ("user", "Python 里变量赋值和 C 语言有什么区别？为什么说变量是'标签'而不是'盒子'？"),
                (
                    "assistant",
                    "这是一个很好的问题！理解这个区别对学好 Python 非常重要。\n\n"
                    "在 C 语言中，变量像一个盒子，赋值就是往盒子里装值：\n"
                    "```c\nint x = 10;  // 盒子 x 里装了 10\nint y = x;   // 盒子 y 里复制了一份 10\n```\n\n"
                    "在 Python 中，变量更像一个标签/名字，贴在值上面：\n"
                    "```python\nx = 10      # 名字 x 指向整数对象 10\ny = x       # 名字 y 也指向同一个 10\nx = 20      # x 改为指向新的 20，y 仍然指向 10\n```\n\n"
                    "核心区别：\n"
                    "1. Python 的值是对象，存储在堆内存中\n"
                    "2. 变量只是引用（指针），赋值是让名字指向新对象\n"
                    "3. Python 有垃圾回收机制，不需要手动管理内存\n\n"
                    "这就是为什么 Python 的 `=` 叫做'绑定'而不是'赋值'。",
                ),
                ("user", "那 Python 里的可变对象和不可变对象又是什么？"),
                (
                    "assistant",
                    "这和刚才的'标签'模型直接相关！\n\n"
                    "**不可变对象**（immutable）：值不能原地修改\n"
                    "- `int`、`float`、`str`、`tuple`、`bool`\n"
                    "- 修改时会创建新对象，标签指向新地址\n\n"
                    "**可变对象**（mutable）：值可以原地修改\n"
                    "- `list`、`dict`、`set`\n"
                    "- 修改不会改变地址，所有引用都看得到变化\n\n"
                    "```python\n# 不可变：字符串\na = 'hello'\nb = a\na += ' world'  # 创建了新字符串，a 指向新的\nprint(b)  # 仍然是 'hello'\n\n# 可变：列表\na = [1, 2]\nb = a\na.append(3)   # 原地修改\nprint(b)       # [1, 2, 3] — b 也变了！\n```\n\n"
                    "记住：**不可变 = 安全但创建新对象有开销**，**可变 = 方便但要注意副作用**。",
                ),
                ("user", "明白了，谢谢！那函数参数传递是传值还是传引用？"),
                (
                    "assistant",
                    "Python 的参数传递既不是纯粹的传值，也不是纯粹的传引用，而是 **传对象引用**（pass by object reference），也叫'传共享'（pass by sharing）。\n\n"
                    "简单理解：函数收到的是对象的引用（标签的副本）。\n\n"
                    "```python\ndef modify(x):\n    x = x + 1     # 创建新对象，局部标签指向新值\n    # 原来的标签不受影响\n\na = 10\nmodify(a)\nprint(a)  # 10 — 没变\n\n\ndef modify_list(lst):\n    lst.append(4)  # 原地修改可变对象\n    # 调用者的列表也变了\n\nnums = [1, 2, 3]\nmodify_list(nums)\nprint(nums)  # [1, 2, 3, 4] — 变了！\n```\n\n"
                    "规则总结：\n"
                    "- 不可变参数（int/str/tuple）：函数内修改不影响外部\n"
                    "- 可变参数（list/dict）：原地修改会影响外部\n"
                    "- 如果想避免副作用，传入 `.copy()` 或 `list(x)`",
                ),
            ],
        },
        {
            "name": "for 循环与列表推导式",
            "messages": [
                ("user", "什么时候该用列表推导式，什么时候该用普通的 for 循环？"),
                (
                    "assistant",
                    "好问题！列表推导式不是 always better，选择标准如下：\n\n"
                    "**适合用列表推导式的场景：**\n"
                    "1. 简单的映射/过滤操作\n"
                    "2. 一行能看懂的逻辑\n"
                    "3. 需要创建一个新列表\n\n"
                    "```python\n# 映射：每个元素做转换\nsquares = [x**2 for x in range(10)]\n\n# 过滤：筛选满足条件的元素\nevens = [x for x in numbers if x % 2 == 0]\n\n# 映射 + 过滤\nlabels = [f'#{n}' for n in numbers if n > 0]\n```\n\n"
                    "**适合用 for 循环的场景：**\n"
                    "1. 逻辑复杂，一行写不下\n"
                    "2. 需要处理异常\n"
                    "3. 需要多个条件分支\n"
                    "4. 有副作用（打印、写文件等）\n\n"
                    "```python\n# 这种推导式可读性差，应该用 for 循环\nresults = []\nfor item in data:\n    try:\n        val = process(item)\n        if val > threshold:\n            results.append(val)\n    except Error:\n        log(item)\n```\n\n"
                    "**记住：可读性 > 简洁性。** 如果同事看不懂你的推导式，就用 for 循环。",
                ),
                ("user", "生成器表达式和列表推导式的区别呢？"),
                (
                    "assistant",
                    "一个字：**惰性求值**（lazy evaluation）。\n\n"
                    "列表推导式 `[]`：立即计算所有结果，存入内存\n"
                    "生成器表达式 `()`：按需计算，每次只产生一个值\n\n"
                    "```python\n# 列表推导式：一次性生成 100 万个元素\nbig_list = [x**2 for x in range(1_000_000)]\n\n# 生成器表达式：逐个计算，几乎不占内存\nbig_gen = (x**2 for x in range(1_000_000))\n\n# 配合 sum/max/min 等聚合函数时，用生成器更高效\ntotal = sum(x**2 for x in range(1_000_000))  # 推荐\n```\n\n"
                    "**选择指南：**\n"
                    "- 需要多次遍历或随机访问 → 列表推导式\n"
                    "- 只遍历一次，或数据量很大 → 生成器表达式\n"
                    "- 配合 `sum`/`any`/`all`/`max`/`min` → 生成器表达式",
                ),
            ],
        },
        {
            "name": "try/except 异常处理最佳实践",
            "messages": [
                ("user", "写 try/except 的时候，应该捕获哪些异常？我看到有人说不要用裸 except。"),
                (
                    "assistant",
                    "绝对正确！裸 `except` 是 Python 中最常见的反模式之一。\n\n"
                    "**错误做法：**\n"
                    "```python\ntry:\n    do_something()\nexcept:          # 捕获所有异常，包括 KeyboardInterrupt\n    pass         # 吞掉错误，调试噩梦\n```\n\n"
                    "**正确做法：**\n"
                    "```python\ntry:\n    result = int(user_input)\nexcept ValueError as e:\n    print(f'输入不是有效数字: {e}')\nexcept (TypeError, AttributeError):\n    print('参数类型错误')\nexcept Exception as e:\n    logger.error(f'未预期的错误: {e}')\n    raise  # 重新抛出，不要吞掉\n```\n\n"
                    "**核心原则：**\n"
                    "1. **捕获具体异常**：知道你在处理什么\n"
                    "2. **不要吞异常**：至少要记录日志\n"
                    "3. **在合适的层级捕获**：底层函数抛出，顶层调用者捕获\n"
                    "4. **EAFP 原则**：先做再道歉（try 比 if 判断更 Pythonic）\n"
                    "5. **finally 用于清理**：关闭文件、释放锁等",
                ),
            ],
        },
    ]

    return conversations


# ---------------------------------------------------------------------------
# Load functions
# ---------------------------------------------------------------------------


def load_demo_data(db: "AppDatabase", include_conversations: bool = True) -> int:
    """Load all demo data into the database.

    Args:
        db: AppDatabase instance.
        include_conversations: Whether to also load demo AI conversations.

    Returns:
        Total number of records inserted.
    """
    total = 0
    progress = _build_week1_progress()

    # 1. Lesson progress
    for lp in progress["lesson_progress"]:
        db.execute(
            """
            INSERT INTO lesson_progress (lesson_id, track_id, status, completed, last_opened, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(lesson_id) DO UPDATE SET
                track_id = excluded.track_id,
                status = excluded.status,
                completed = excluded.completed,
                last_opened = excluded.last_opened,
                completed_at = excluded.completed_at
            """,
            (lp["lesson_id"], lp["track_id"], lp["status"], lp["completed"], lp["last_opened"], lp["completed_at"]),
        )
        total += 1

    # 2. Practice attempts
    for att in progress["practice_attempts"]:
        db.execute(
            """
            INSERT INTO practice_attempts
            (exercise_id, exercise_title_snapshot, track_id, code_snapshot,
             score, passed, duration_sec, submitted_at, feedback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                att["exercise_id"],
                att["exercise_title"],
                att["track_id"],
                att["code_snapshot"],
                att["score"],
                att["passed"],
                att["duration_sec"],
                att["submitted_at"],
                att["feedback"],
            ),
        )
        total += 1

    # 3. Lesson notes
    for note in progress["lesson_notes"]:
        db.execute(
            """
            INSERT INTO lesson_notes (lesson_id, content, tags, code_snippets, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(lesson_id) DO UPDATE SET
                content = excluded.content,
                tags = excluded.tags,
                code_snippets = excluded.code_snippets,
                updated_at = excluded.updated_at
            """,
            (note["lesson_id"], note["content"], note["tags"], note["code_snippets"], note["updated_at"]),
        )
        total += 1

    # 4. Bookmarks
    for bm in progress["bookmarks"]:
        db.add_bookmark(bm["item_type"], bm["item_id"], bm["title"], bm.get("track_id", ""), bm.get("note", ""))
        total += 1

    # 5. Achievement progress
    for ach_id, current, unlocked, unlocked_at in progress["achievements"]:
        db.execute(
            """
            INSERT INTO achievement_progress (achievement_id, current_value, unlocked, unlocked_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(achievement_id) DO UPDATE SET
                current_value = MAX(current_value, excluded.current_value),
                unlocked = excluded.unlocked,
                unlocked_at = COALESCE(excluded.unlocked_at, achievement_progress.unlocked_at)
            """,
            (ach_id, current, unlocked, unlocked_at),
        )
        total += 1

    # 6. Daily analytics
    for day in progress["analytics_daily"]:
        db.update_daily_analytics(
            day["date"],
            learning_time_sec=day["learning_time_sec"],
            lessons_completed=day["lessons_completed"],
            exercises_completed=day["exercises_completed"],
            exercise_score_sum=day["exercise_score_sum"],
        )
        total += 1

    # 7. AI mentor conversations
    if include_conversations:
        for conv in _build_demo_conversations():
            session_id = db.create_mentor_session(conv["name"])
            for role, content in conv["messages"]:
                db.append_mentor_message(session_id, role, content)
                total += 1

    # Invalidate stats cache so dashboard refreshes
    db._invalidate_stats_cache()

    logger.info("Demo data loaded: %d records", total)
    return total


def has_demo_data(db: "AppDatabase") -> bool:
    """Check whether demo data has already been loaded.

    Looks for a distinctive demo lesson note that only the demo data creates.
    """
    row = db.fetchone("SELECT 1 FROM lesson_notes WHERE lesson_id = 'py-data-types' AND tags LIKE '%Python,基础,变量%'")
    return row is not None
