import ast
import io
import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.config import METADATA_DIR
from app.python_runner import evaluate_python_code


SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "reversed": reversed,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "type": type,
    "tuple": tuple,
    "zip": zip,
}

EXERCISE_FALLBACKS = {
    "py-squares-comprehension": {
        "title": "用推导式生成奇数平方",
        "difficulty": "进阶",
        "prompt": "实现 odd_squares(numbers)，返回 numbers 中所有奇数的平方列表。",
        "hints": ["先筛选奇数，再做平方。", "这道题很适合列表推导式。"],
    },
    "py-factorial-recursive": {
        "title": "递归实现阶乘",
        "difficulty": "进阶",
        "prompt": "实现 factorial(n)，使用递归返回 n 的阶乘。约定 0 和 1 的结果都为 1。",
        "hints": [
            "先写清楚终止条件。",
            "再写递归关系 factorial(n) = n * factorial(n-1)。",
        ],
    },
    "py-save-user-payload": {
        "title": "构造用户资料字典",
        "difficulty": "进阶",
        "prompt": "实现 build_user_payload(name, city)，返回包含 name、city、active 三个字段的字典，其中 active 固定为 True。",
        "hints": ["返回值是一个字典对象。", "键名建议直接使用字符串常量。"],
    },
    "py-test-target-positive": {
        "title": "编写可测试的正数判断函数",
        "difficulty": "进阶",
        "prompt": "实现 is_positive(num)，当 num 大于 0 时返回 True，否则返回 False。",
        "hints": ["返回值应该直接是布尔值。", "注意 0 不算正数。"],
    },
    "py-summarize-status": {
        "title": "统计状态出现次数",
        "difficulty": "进阶",
        "prompt": "实现 summarize_status(items)，统计列表中每种状态出现的次数，并返回一个字典。",
        "hints": ["可以边遍历边累加。", "空列表时返回空字典。"],
    },
    "c-string-contains-zero": {
        "title": "声明一个 C 字符串",
        "difficulty": "进阶",
        "prompt": "写一行 C 代码，声明字符数组 name，并让它保存一个带有 \\0 结尾的字符串字面量。",
        "hints": ["字符串字面量本身会带结尾符。", "重点是 char 数组和双引号。"],
    },
    "c-malloc-int-array": {
        "title": "申请并释放整型数组",
        "difficulty": "精选",
        "prompt": "写出一段 C 代码：使用 malloc 申请 10 个 int 的空间，并在使用后调用 free 释放它。",
        "hints": ["先想清楚 malloc 和 free 成对出现。", "别忘了 sizeof(int)。"],
    },
    "c-node-struct": {
        "title": "定义链表节点结构体",
        "difficulty": "精选",
        "prompt": "定义一个 Node 结构体，至少包含 value 和 next 两个字段，其中 next 指向另一个 Node。",
        "hints": ["next 通常写成 struct Node *next。", "先把结构体声明完整。"],
    },
    "c-gdb-break-main": {
        "title": "写出 GDB 的最小调试命令",
        "difficulty": "精选",
        "prompt": "写出两条 GDB 命令：先在 main 设置断点，再启动程序运行。",
        "hints": ["先写 break main。", "再写 run。"],
    },
    "cs-parse-score-safe": {
        "title": "安全解析分数字符串",
        "difficulty": "进阶",
        "prompt": "写一段 C# 代码，用 int.TryParse 安全解析 scoreText，并在成功时进入 if 分支。",
        "hints": ["TryParse 比 Parse 更稳。", "重点是 if 判断和输出变量。"],
    },
    "cs-declare-saved-event": {
        "title": "声明 Saved 事件",
        "difficulty": "精选",
        "prompt": "在 C# 类中声明一个名为 Saved 的事件，类型使用 Action。",
        "hints": ["要用 event 关键字。", "标准写法通常是 public event Action Saved;"],
    },
    "cs-save-json": {
        "title": "把对象序列化为 JSON",
        "difficulty": "精选",
        "prompt": "写一段 C# 代码，调用 JsonSerializer.Serialize(task) 把 task 转成 JSON 字符串。",
        "hints": [
            "关键调用是 JsonSerializer.Serialize。",
            "先确认 task 变量已经存在。",
        ],
    },
    "cs-mapget-ping": {
        "title": "声明一个 ping 接口",
        "difficulty": "兴趣",
        "prompt": "写一行最小 API 路由代码，为 /ping 声明一个返回对象的 MapGet 接口。",
        "hints": ["重点是 MapGet。", "可以返回 new { ok = true }。"],
    },
    "db-design-enrollment-table": {
        "title": "设计选课关系表",
        "difficulty": "精选",
        "prompt": "写出一条建表语句，创建学生选课关系表，至少包含 student_id 和 course_id 两个字段。",
        "hints": ["表名可以叫 enrollments。", "这是一张关系表。"],
    },
    "db-rank-scores": {
        "title": "给成绩做排名",
        "difficulty": "精选",
        "prompt": "写一条 SQL，使用 RANK() OVER 按 score 对 students 表进行降序排名。",
        "hints": ["先写 rank() over。", "排序条件通常是 order by score desc。"],
    },
    "db-coalesce-phone": {
        "title": "用 COALESCE 处理空手机号",
        "difficulty": "进阶",
        "prompt": "写一条 SQL，从 users 表查询手机号字段；如果 phone 为空，就显示 unknown。",
        "hints": ["这道题核心是 COALESCE。", "目标是把空值转成可读文本。"],
    },
    "db-postgres-connect": {
        "title": "连接 PostgreSQL 数据库",
        "difficulty": "进阶",
        "prompt": "写出一条 psql 命令，连接名为 learn_db 的 PostgreSQL 数据库。",
        "hints": ["命令通常以 psql 开头。", "把数据库名写出来就行。"],
    },
    "integration-add-item-record": {
        "title": "追加库存记录",
        "difficulty": "综合",
        "prompt": "实现 add_item(items, name, count)，把一条包含 name 和 count 的记录追加到列表中，并返回当前列表长度。",
        "hints": ["items 是一个列表。", "先追加，再返回长度。"],
    },
    "integration-build-metric-row": {
        "title": "构造指标行数据",
        "difficulty": "综合",
        "prompt": "实现 build_metric_row(name, value)，返回一个包含 metric 和 value 两个字段的字典。",
        "hints": ["返回值是一个字典。", "字段名固定为 metric 和 value。"],
    },
    "integration-api-brief": {
        "title": "生成 API 摘要文本",
        "difficulty": "综合",
        "prompt": "实现 build_api_brief(source, count)，返回形如“来源:weather, 数量:3”的摘要字符串。",
        "hints": ["可以使用 f-string。", "把 source 和 count 按固定格式拼起来。"],
        "tests": [
            {
                "expression": "build_api_brief('weather', 3)",
                "expected": "来源:weather, 数量:3",
            },
            {
                "expression": "build_api_brief('users', 10)",
                "expected": "来源:users, 数量:10",
            },
        ],
    },
    "integration-progress-badge": {
        "title": "生成进度徽章文本",
        "difficulty": "综合",
        "prompt": "实现 build_badge(done, total)，返回形如“3/10 已完成”的字符串。",
        "hints": ["把两个数字和状态文案组合起来。", "注意返回值是字符串。"],
        "tests": [
            {"expression": "build_badge(3, 10)", "expected": "3/10 已完成"},
            {"expression": "build_badge(0, 5)", "expected": "0/5 已完成"},
        ],
    },
    "c-include-guard-header": {
        "title": "写一个头文件保护宏",
        "difficulty": "精选",
        "prompt": "写出一个最小头文件框架，包含 TASKS_H 的 include guard。",
        "hints": ["三件套通常是 ifndef、define、endif。", "宏名要前后一致。"],
    },
    "c-free-null-safe": {
        "title": "释放后把指针置空",
        "difficulty": "精选",
        "prompt": "写出两行 C 代码：先释放 buffer，再把 buffer 置为 NULL。",
        "hints": ["先 free，再赋值。", "NULL 要大写。"],
    },
    "cs-interface-notifier": {
        "title": "声明 INotifier 接口",
        "difficulty": "精选",
        "prompt": "写一个 C# 接口 INotifier，其中包含 `void Send(string message);` 方法签名。",
        "hints": ["关键字是 interface。", "接口方法不需要方法体。"],
    },
    "cs-record-student": {
        "title": "定义 Student record",
        "difficulty": "进阶",
        "prompt": "写一个 `record Student(string Name, int Score);`，用于表示学生成绩。",
        "hints": ["record 可以直接带主构造。", "字段名注意大小写。"],
    },
    "db-orders-foreign-key": {
        "title": "给订单表加外键",
        "difficulty": "进阶",
        "prompt": "写一条 CREATE TABLE 语句，创建 orders 表，并让 user_id 通过 FOREIGN KEY 引用 users(id)。",
        "hints": [
            "先定义 user_id 列。",
            "再写 FOREIGN KEY (user_id) REFERENCES users(id)。",
        ],
    },
    "db-left-join-users-orders": {
        "title": "写出用户与订单的 LEFT JOIN",
        "difficulty": "精选",
        "prompt": "写一条 SQL，把 users 表和 orders 表按 `users.id = orders.user_id` 做 LEFT JOIN。",
        "hints": ["关键字是 LEFT JOIN。", "别忘了 ON 条件。"],
    },
    "py-make-logger": {
        "title": "构造一个最小日志装饰器",
        "difficulty": "精选",
        "prompt": '实现 make_logger(tag)，它返回一个内部函数 log(message)，调用后返回形如 "[TAG] message" 的字符串。',
        "hints": ["这题重点是函数返回函数。", "可以在内部函数里访问外层的 tag。"],
    },
    "py-build-student-card": {
        "title": "构造学生数据卡片",
        "difficulty": "精选",
        "prompt": "实现 build_student_card(name, score)，返回一个字典，包含 name、score、passed 三个字段，其中 passed 表示分数是否及格。",
        "hints": ["返回值是字典。", "及格线按 60 分处理。"],
    },
    "c-bitmask-check-read": {
        "title": "检查是否包含 READ 标志位",
        "difficulty": "精选",
        "prompt": "写一段 C 表达式或判断代码，用位运算检查 perms 是否包含 READ 标志位。",
        "hints": ["这题核心是 &。", "常见写法是 if (perms & READ) { ... }"],
    },
    "c-main-argc-argv": {
        "title": "写出带参数的 main 函数入口",
        "difficulty": "进阶",
        "prompt": "写出一个 C 程序入口函数声明，能够接收命令行参数 argc 和 argv。",
        "hints": ["重点是 main 的函数签名。", "argv 通常写成 char *argv[]。"],
    },
    "cs-httpclient-get": {
        "title": "发起一个最小 GET 请求",
        "difficulty": "精选",
        "prompt": "写一段 C# 代码，使用 HttpClient 异步请求一个 URL，并通过 await 获取结果。",
        "hints": [
            "关键对象是 HttpClient。",
            "关键调用通常是 GetAsync 或 GetStringAsync。",
        ],
    },
    "cs-xunit-assert-equal": {
        "title": "写一条 Assert.Equal 断言",
        "difficulty": "精选",
        "prompt": "写一条 xUnit 断言，验证 Add(2, 3) 的结果等于 5。",
        "hints": ["关键调用是 Assert.Equal。", "先写预期值，再写实际值。"],
    },
    "db-with-sales-cte": {
        "title": "写一个最小销售汇总 CTE",
        "difficulty": "精选",
        "prompt": "写一条 SQL，用 WITH sales_cte 先汇总 orders 表中的金额，再从 sales_cte 中查询结果。",
        "hints": ["至少要有 WITH、SELECT、FROM。", "中间结果名写成 sales_cte。"],
    },
    "db-group-having-order": {
        "title": "写出分组后筛选的报表查询骨架",
        "difficulty": "精选",
        "prompt": "写一条 SQL，要求包含 GROUP BY、HAVING 和 ORDER BY，用于统计订单数量并筛选高频用户。",
        "hints": [
            "这题重点是 WHERE 和 HAVING 的位置感。",
            "至少把三段关键结构写出来。",
        ],
    },
    "integration-build-desktop-record": {
        "title": "构造桌面记录项",
        "difficulty": "综合",
        "prompt": "实现 build_desktop_record(title, done, source)，返回一个字典，包含 title、done、source 三个字段。",
        "hints": ["返回值是字典。", "字段名固定为 title、done、source。"],
    },
    "integration-build-report-line": {
        "title": "生成报表摘要行",
        "difficulty": "综合",
        "prompt": '实现 build_report_line(day, passed, total)，返回形如 "2026-04-03 · 8/10 已通过" 的字符串。',
        "hints": ["可以直接用 f-string。", "注意输出格式里有圆点分隔符。"],
    },
    "py-yield-range": {
        "title": "写一个最小 yield 生成器",
        "difficulty": "精选",
        "prompt": "实现 count_up(n)，使用 yield 依次产生 1 到 n 的整数。",
        "hints": [
            "这题不是返回列表，而是逐个产出。",
            "可以在循环里反复 yield 当前值。",
        ],
    },
    "py-open-log-summary": {
        "title": "用 with 读取日志首行",
        "difficulty": "精选",
        "prompt": "写一段 Python 代码，使用 with open(...) 读取文本文件的第一行并保存到变量 first_line。",
        "hints": ["重点是 with open 的结构。", "读取一行通常可以用 readline。"],
    },
    "c-save-record-line": {
        "title": "写一条记录到文本文件",
        "difficulty": "精选",
        "prompt": '写一段 C 代码，使用 fprintf(fp, "%s,%d\\n", name, count); 把一条记录写入已打开的文件。',
        "hints": ["这题核心是 fprintf。", "假设 fp、name、count 已经存在。"],
    },
    "c-call-callback": {
        "title": "通过函数指针调用回调",
        "difficulty": "精选",
        "prompt": "已知 `int (*fn)(int)` 指向一个函数，写一行 C 代码调用它并把结果保存到 result。",
        "hints": ["函数指针调用写法和普通函数很像。", "形如 result = fn(3);"],
    },
    "cs-await-delay": {
        "title": "等待一个最小异步任务",
        "difficulty": "精选",
        "prompt": "写一行 C# 代码，使用 await Task.Delay(300); 表示等待 300 毫秒。",
        "hints": ["关键字是 await。", "需要和 Task.Delay 搭配。"],
    },
    "cs-group-score-lines": {
        "title": "按班级做最小分组",
        "difficulty": "精选",
        "prompt": "写一段 C# LINQ 代码，使用 GroupBy(x => x.ClassName) 按班级分组。",
        "hints": ["核心调用是 GroupBy。", "lambda 里返回分组键。"],
    },
    "db-transfer-transaction": {
        "title": "写一个最小转账事务骨架",
        "difficulty": "精选",
        "prompt": "写出一段 SQL 骨架，至少包含 BEGIN、两条 UPDATE 和 COMMIT，用于表达最小转账事务。",
        "hints": ["事务开始于 BEGIN。", "最后要有 COMMIT。"],
    },
    "db-create-index-users-email": {
        "title": "给用户邮箱建索引",
        "difficulty": "精选",
        "prompt": "写一条 SQL，在 users 表的 email 列上创建索引。",
        "hints": ["关键字是 CREATE INDEX。", "要写出表名和列名。"],
    },
    "integration-build-log-entry": {
        "title": "构造日志统计项",
        "difficulty": "综合",
        "prompt": "实现 build_log_entry(level, count)，返回一个字典，包含 level 和 count 两个字段。",
        "hints": ["返回值是字典。", "字段名固定为 level 和 count。"],
    },
    "integration-build-dashboard-card": {
        "title": "生成看板卡片标题",
        "difficulty": "综合",
        "prompt": '实现 build_card_title(source, metric)，返回形如 "weather · requests" 的字符串。',
        "hints": ["可以直接用 f-string。", "注意中间的分隔符是圆点。"],
    },
    "py-safe-parse-int": {
        "title": "安全解析整数并返回默认值",
        "difficulty": "精选",
        "prompt": "实现 safe_parse_int(text, default)，当 text 能转成整数时返回整数，否则返回 default。",
        "hints": ["核心是 try / except。", "只需要处理整数解析失败这个场景。"],
    },
    "py-argparse-add-flag": {
        "title": "给命令行工具加一个 --limit 参数",
        "difficulty": "精选",
        "prompt": "写一行 argparse 配置代码，给 parser 增加一个名为 --limit 的整数可选参数，默认值为 10。",
        "hints": ["核心是 add_argument。", "别忘了 type=int 和 default=10。"],
    },
    "c-open-binary-write": {
        "title": "以二进制写模式打开文件",
        "difficulty": "精选",
        "prompt": "写一行 C 代码，使用 fopen 以二进制写模式打开 data.bin，并把结果保存到 fp。",
        "hints": ["模式字符串是 wb。", "结果要赋给 FILE * 变量。"],
    },
    "c-switch-task-state": {
        "title": "根据枚举状态写 switch 分支",
        "difficulty": "精选",
        "prompt": '写一个最小 C switch 结构，根据状态 STATE_DONE 输出 "done"。',
        "hints": ["核心是 switch / case。", "你只需要表达出 STATE_DONE 这个分支。"],
    },
    "cs-ctor-inject-logger": {
        "title": "通过构造函数注入 ILogger",
        "difficulty": "精选",
        "prompt": "给 UserService 写一个构造函数，接收 ILogger logger，并赋值给字段 _logger。",
        "hints": ["核心是构造函数参数。", "把传入值保存到字段里。"],
    },
    "cs-repository-interface": {
        "title": "定义最小任务仓储接口",
        "difficulty": "精选",
        "prompt": "写一个 C# 接口 ITaskRepository，至少包含 `void Add(TaskItem item);` 方法签名。",
        "hints": ["关键字是 interface。", "方法签名不需要方法体。"],
    },
    "db-exists-active-users": {
        "title": "写一个最小 EXISTS 条件查询",
        "difficulty": "精选",
        "prompt": "写一条 SQL，从 users 表查询至少有一条订单的用户，要求使用 EXISTS。",
        "hints": ["外层查 users。", "子查询里按 user_id 关联 orders。"],
    },
    "db-create-user-view": {
        "title": "创建一个最小用户汇总视图",
        "difficulty": "精选",
        "prompt": "写一条 SQL，创建视图 user_summary，来源是对 users 表的最小 SELECT 查询。",
        "hints": ["关键字是 CREATE VIEW。", "先写最小可运行骨架。"],
    },
    "integration-build-audit-item": {
        "title": "构造结构审计项",
        "difficulty": "综合",
        "prompt": "实现 build_audit_item(table_name, has_pk)，返回一个字典，包含 table_name 和 has_pk 两个字段。",
        "hints": ["返回值是字典。", "字段名固定。"],
    },
    "integration-build-cli-help": {
        "title": "生成命令行帮助摘要",
        "difficulty": "综合",
        "prompt": '实现 build_help_line(command, desc)，返回形如 "scan: 检查数据库结构" 的字符串。',
        "hints": ["可以直接拼接字符串。", "注意冒号和空格的格式。"],
    },
    "py-configure-basic-logger": {
        "title": "配置一个最小日志输出",
        "difficulty": "精选",
        "prompt": "写一行 Python 代码，调用 logging.basicConfig(level=logging.INFO) 配置最小日志级别。",
        "hints": ["关键对象是 logging。", "关键调用是 basicConfig。"],
    },
    "py-build-package-entry": {
        "title": "设计一个最小项目入口骨架",
        "difficulty": "精选",
        "prompt": "写出一个最小项目目录骨架，至少包含 app/main.py 和 tests/ 两个部分。",
        "hints": ["这题重点是结构表达。", "可以用文本树形结构回答。"],
    },
    "c-define-max-macro": {
        "title": "定义一个 MAX_ITEMS 宏",
        "difficulty": "精选",
        "prompt": "写一行 C 代码，使用 #define 定义名为 MAX_ITEMS 的宏，值为 128。",
        "hints": ["关键字是 #define。", "宏名通常用大写。"],
    },
    "c-qsort-compare-int": {
        "title": "写一个最小整数比较器骨架",
        "difficulty": "精选",
        "prompt": "写出 C 函数签名 `int compare_ints(const void *a, const void *b)`，用于给 qsort 传比较函数。",
        "hints": ["这题重点是函数签名。", "参数类型要是 const void *。"],
    },
    "cs-read-config-value": {
        "title": "读取一个 ApiHost 配置值",
        "difficulty": "精选",
        "prompt": "写一行 C# 代码，从配置对象中读取键名为 `ApiHost` 的值，并保存到变量 host。",
        "hints": ["这题重点是“读取配置”的表达。", "变量名固定为 host。"],
    },
    "cs-map-route-id": {
        "title": "声明一个带 id 的最小路由",
        "difficulty": "精选",
        "prompt": "写一行 C# Minimal API 代码，声明 `/users/{id}` 路由，并返回包含 id 的匿名对象。",
        "hints": ["关键调用是 MapGet。", "路由里要有 {id}。"],
    },
    "db-explain-users-query": {
        "title": "给用户查询加 EXPLAIN",
        "difficulty": "精选",
        "prompt": "写一条 SQL，在 `SELECT * FROM users WHERE email = 'a@example.com'` 前加上 EXPLAIN。",
        "hints": ["这题只需要在查询前加 EXPLAIN。", "保持原查询主体即可。"],
    },
    "db-add-column-migration": {
        "title": "写一个给 users 加列的迁移",
        "difficulty": "精选",
        "prompt": "写一条 SQL，给 users 表新增 `last_login` 文本列。",
        "hints": ["关键字是 ALTER TABLE 和 ADD COLUMN。", "列名固定为 last_login。"],
    },
    "integration-build-kpi-row": {
        "title": "构造学习指标行",
        "difficulty": "综合",
        "prompt": "实现 build_kpi_row(name, value)，返回一个字典，包含 name 和 value 两个字段。",
        "hints": ["返回值是字典。", "字段名固定。"],
    },
    "integration-build-note-summary": {
        "title": "生成笔记摘要标题",
        "difficulty": "综合",
        "prompt": '实现 build_note_summary(title, keyword_count)，返回形如 "Python 迭代器 · 3 个关键词" 的字符串。',
        "hints": ["可以用 f-string。", "注意中间的分隔符和中文量词。"],
    },
}


def _needs_fallback(value: str) -> bool:
    return "?" in value


DATABASE_EXERCISE_FALLBACKS = {
    "db-design-enrollment-table": {
        "title": "设计选课关系表",
        "difficulty": "精选",
        "prompt": "写出一条建表语句，创建学生选课关系表，至少包含 student_id 和 course_id 两个字段。",
        "hints": ["表名可以叫 enrollments。", "这是一张学生和课程的关系表。"],
    },
    "db-rank-scores": {
        "title": "给成绩做排名",
        "difficulty": "精选",
        "prompt": "写一条 SQL，使用 RANK() OVER 按 score 对 students 表进行降序排名。",
        "hints": ["关键是 rank() over。", "排序条件通常是 order by score desc。"],
    },
    "db-coalesce-phone": {
        "title": "用 COALESCE 处理空手机号",
        "difficulty": "进阶",
        "prompt": "写一条 SQL，从 users 表查询手机号字段；如果 phone 为空，就显示 unknown。",
        "hints": ["这题核心是 COALESCE。", "把空值转成可读文本即可。"],
    },
    "db-postgres-connect": {
        "title": "连接 PostgreSQL 数据库",
        "difficulty": "进阶",
        "prompt": "写出一条 psql 命令，连接名为 learn_db 的 PostgreSQL 数据库。",
        "hints": ["命令通常以 psql 开头。", "把数据库名写出来即可。"],
    },
    "db-orders-foreign-key": {
        "title": "给订单表加外键",
        "difficulty": "进阶",
        "prompt": "写一条 CREATE TABLE 语句，创建 orders 表，并让 user_id 通过 FOREIGN KEY 引用 users(id)。",
        "hints": [
            "先定义 user_id 列。",
            "再写 FOREIGN KEY (user_id) REFERENCES users(id)。",
        ],
    },
    "db-left-join-users-orders": {
        "title": "写出用户与订单的 LEFT JOIN",
        "difficulty": "精选",
        "prompt": "写一条 SQL，把 users 表和 orders 表按 users.id = orders.user_id 做 LEFT JOIN。",
        "hints": ["关键字是 LEFT JOIN。", "别忘了 ON 条件。"],
    },
    "db-with-sales-cte": {
        "title": "写一个最小销售汇总 CTE",
        "difficulty": "精选",
        "prompt": "写一条 SQL，用 WITH sales_cte 先汇总 orders 表中的金额，再从 sales_cte 中查询结果。",
        "hints": ["至少要有 WITH、SELECT、FROM。", "中间结果名写成 sales_cte。"],
    },
    "db-group-having-order": {
        "title": "写出分组后筛选的报表查询骨架",
        "difficulty": "精选",
        "prompt": "写一条 SQL，要求包含 GROUP BY、HAVING 和 ORDER BY，用于统计订单数量并筛选高频用户。",
        "hints": ["重点是 GROUP BY、HAVING、ORDER BY 的顺序。", "先把查询骨架写完整。"],
    },
    "db-transfer-transaction": {
        "title": "写一个转账事务骨架",
        "difficulty": "精选",
        "prompt": "写一段 SQL 事务脚本，至少包含 BEGIN 和 COMMIT，表示一次完整的转账操作。",
        "hints": ["先开启事务。", "最后记得提交。"],
    },
    "db-create-index-users-email": {
        "title": "给用户邮箱创建索引",
        "difficulty": "精选",
        "prompt": "写一条 SQL，给 users 表的 email 列创建索引。",
        "hints": ["关键字是 CREATE INDEX。", "索引目标列是 email。"],
    },
    "db-explain-users-query": {
        "title": "给用户查询加 EXPLAIN",
        "difficulty": "精选",
        "prompt": "写一条 SQL，在 SELECT * FROM users WHERE email = 'a@example.com' 前加上 EXPLAIN。",
        "hints": ["只需要在查询前加 EXPLAIN。", "保持原查询主体不变即可。"],
    },
    "db-add-column-migration": {
        "title": "写一个给 users 加列的迁移",
        "difficulty": "精选",
        "prompt": "写一条 SQL，给 users 表新增 last_login 文本列。",
        "hints": ["关键字是 ALTER TABLE 和 ADD COLUMN。", "列名固定为 last_login。"],
    },
}


SQL_QUERY_FIXTURES = {
    "db-select-active": {
        "setup": """
            CREATE TABLE users(name TEXT, status TEXT);
            INSERT INTO users(name, status) VALUES
                ('Ada', 'active'),
                ('Ben', 'inactive'),
                ('Mina', 'active');
        """,
        "expected_rows": [("Ada",), ("Mina",)],
        "ordered": True,
    },
    "db-order-count": {
        "setup": """
            CREATE TABLE orders(user_id INTEGER, amount REAL);
            INSERT INTO orders(user_id, amount) VALUES
                (1, 12.0),
                (1, 18.5),
                (2, 20.0),
                (3, 7.5);
        """,
        "expected_rows": [(1, 2), (2, 1), (3, 1)],
        "ordered": True,
    },
    "db-join-user-order": {
        "setup": """
            CREATE TABLE users(id INTEGER, name TEXT);
            CREATE TABLE orders(user_id INTEGER, amount REAL);
            INSERT INTO users(id, name) VALUES (1, 'Ada'), (2, 'Ben');
            INSERT INTO orders(user_id, amount) VALUES (1, 20.0), (2, 35.5), (1, 9.9);
        """,
        "expected_rows": [("Ada", 20.0), ("Ada", 9.9), ("Ben", 35.5)],
        "ordered": False,
    },
    "db-subquery-high-score": {
        "setup": """
            CREATE TABLE scores(student TEXT, score INTEGER);
            INSERT INTO scores(student, score) VALUES
                ('Ada', 90),
                ('Ben', 70),
                ('Cici', 95),
                ('Dora', 65);
        """,
        "expected_rows": [("Ada",), ("Cici",)],
        "ordered": True,
    },
    "db-left-join-users-orders": {
        "setup": """
            CREATE TABLE users(id INTEGER, name TEXT);
            CREATE TABLE orders(user_id INTEGER, amount REAL);
            INSERT INTO users(id, name) VALUES (1, 'Ada'), (2, 'Ben'), (3, 'Cici');
            INSERT INTO orders(user_id, amount) VALUES (1, 20.0), (1, 15.0), (2, 35.0);
        """,
        "expected_rows": [("Ada", 15.0), ("Ada", 20.0), ("Ben", 35.0), ("Cici", None)],
        "ordered": False,
    },
    "db-coalesce-phone": {
        "setup": """
            CREATE TABLE users(name TEXT, phone TEXT);
            INSERT INTO users(name, phone) VALUES
                ('Ada', '13800000000'),
                ('Ben', NULL),
                ('Cici', '13900000000');
        """,
        "expected_rows": [("13800000000",), ("unknown",), ("13900000000",)],
        "ordered": True,
    },
    "db-rank-scores": {
        "setup": """
            CREATE TABLE students(name TEXT, score INTEGER);
            INSERT INTO students(name, score) VALUES
                ('Ada', 95),
                ('Ben', 88),
                ('Cici', 95),
                ('Dora', 72);
        """,
        "expected_rows": [
            ("Ada", 95, 1),
            ("Cici", 95, 1),
            ("Ben", 88, 3),
            ("Dora", 72, 4),
        ],
        "ordered": True,
    },
    "db-with-sales-cte": {
        "setup": """
            CREATE TABLE orders(amount REAL);
            INSERT INTO orders(amount) VALUES (10.0), (15.5), (24.5);
        """,
        "expected_rows": [(50.0,)],
        "ordered": True,
    },
    "db-case-report": {
        "setup": """
            CREATE TABLE orders(amount REAL);
            INSERT INTO orders(amount) VALUES (20.0), (45.0), (70.0), (120.0), (95.0);
        """,
        "expected_rows": [("high", 1), ("low", 2), ("medium", 2)],
        "ordered": False,
    },
    "db-group-having-order": {
        "setup": """
            CREATE TABLE orders(user_id INTEGER, amount REAL);
            INSERT INTO orders(user_id, amount) VALUES
                (1, 20.0),
                (1, 22.0),
                (1, 35.0),
                (2, 15.0),
                (2, 18.0),
                (3, 40.0);
        """,
        "expected_rows": [(1, 3), (2, 2)],
        "ordered": True,
    },
    "db-transfer-transaction": {
        "setup": """
            CREATE TABLE accounts(id INTEGER PRIMARY KEY, balance INTEGER);
            INSERT INTO accounts(id, balance) VALUES (1, 100), (2, 80);
        """,
        "mode": "script",
        "check_sql": "SELECT id, balance FROM accounts ORDER BY id;",
        "expected_rows": [(1, 70), (2, 110)],
        "ordered": True,
    },
    "db-insert-daily-report": {
        "setup": """
            CREATE TABLE reports(day TEXT, total INTEGER);
        """,
        "mode": "script",
        "check_sql": "SELECT day, total FROM reports ORDER BY day;",
        "expected_rows": [("2026-04-01", 8)],
        "ordered": True,
    },
    "db-update-null-phone": {
        "setup": """
            CREATE TABLE users(name TEXT, phone TEXT);
            INSERT INTO users(name, phone) VALUES
                ('Ada', NULL),
                ('Ben', '13900000000');
        """,
        "mode": "script",
        "check_sql": "SELECT name, phone FROM users ORDER BY name;",
        "expected_rows": [("Ada", "unknown"), ("Ben", "13900000000")],
        "ordered": True,
    },
    "db-delete-cancelled-orders": {
        "setup": """
            CREATE TABLE orders(id INTEGER PRIMARY KEY, status TEXT);
            INSERT INTO orders(id, status) VALUES
                (1, 'paid'),
                (2, 'cancelled'),
                (3, 'paid'),
                (4, 'cancelled');
        """,
        "mode": "script",
        "check_sql": "SELECT id, status FROM orders ORDER BY id;",
        "expected_rows": [(1, "paid"), (3, "paid")],
        "ordered": True,
    },
    "db-window-running-total": {
        "setup": """
            CREATE TABLE sales(day TEXT, amount INTEGER);
            INSERT INTO sales(day, amount) VALUES
                ('2026-04-01', 10),
                ('2026-04-02', 20),
                ('2026-04-03', 15);
        """,
        "expected_rows": [
            ("2026-04-01", 10, 10),
            ("2026-04-02", 20, 30),
            ("2026-04-03", 15, 45),
        ],
        "ordered": True,
    },
    "db-exists-high-value-users": {
        "setup": """
            CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE orders(user_id INTEGER, amount INTEGER);
            INSERT INTO users(id, name) VALUES (1, 'Ada'), (2, 'Ben'), (3, 'Cici');
            INSERT INTO orders(user_id, amount) VALUES (1, 20), (1, 120), (2, 45), (3, 150);
        """,
        "expected_rows": [("Ada",), ("Cici",)],
        "ordered": True,
    },
    "db-upsert-daily-kpi": {
        "setup": """
            CREATE TABLE kpi(day TEXT PRIMARY KEY, total INTEGER);
            INSERT INTO kpi(day, total) VALUES ('2026-04-01', 3);
        """,
        "mode": "script",
        "check_sql": "SELECT day, total FROM kpi ORDER BY day;",
        "expected_rows": [("2026-04-01", 8)],
        "ordered": True,
    },
    "db-cte-top-users": {
        "setup": """
            CREATE TABLE orders(user_id INTEGER, amount INTEGER);
            INSERT INTO orders(user_id, amount) VALUES
                (1, 40), (1, 60), (2, 100), (3, 30), (3, 20), (3, 70);
        """,
        "expected_rows": [(1, 100), (2, 100), (3, 120)],
        "ordered": True,
    },
    "db-row-number-latest-log": {
        "setup": """
            CREATE TABLE logs(user_id INTEGER, ts TEXT, score INTEGER);
            INSERT INTO logs(user_id, ts, score) VALUES
                (1, '2026-04-01 09:00:00', 10),
                (1, '2026-04-01 12:00:00', 20),
                (2, '2026-04-02 10:00:00', 30),
                (2, '2026-04-02 10:05:00', 35);
        """,
        "expected_rows": [
            (1, "2026-04-01 12:00:00", 20),
            (2, "2026-04-02 10:05:00", 35),
        ],
        "ordered": True,
    },
    "db-join-course-enrollment-count": {
        "setup": """
            CREATE TABLE courses(id INTEGER PRIMARY KEY, title TEXT);
            CREATE TABLE enrollments(course_id INTEGER, student_id INTEGER);
            INSERT INTO courses(id, title) VALUES (1, 'Python'), (2, 'SQL'), (3, 'C#');
            INSERT INTO enrollments(course_id, student_id) VALUES
                (1, 101), (1, 102), (2, 103), (2, 104), (2, 105);
        """,
        "expected_rows": [("Python", 2), ("SQL", 3), ("C#", 0)],
        "ordered": False,
    },
    "db-subquery-above-course-average": {
        "setup": """
            CREATE TABLE scores(course TEXT, student TEXT, score INTEGER);
            INSERT INTO scores(course, student, score) VALUES
                ('Python', 'Ada', 90),
                ('Python', 'Ben', 70),
                ('Python', 'Cici', 95),
                ('SQL', 'Dora', 88),
                ('SQL', 'Eric', 76);
        """,
        "expected_rows": [("Ada",), ("Cici",), ("Dora",)],
        "ordered": True,
    },
    "db-explain-users-query": {
        "setup": """
            CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT);
            INSERT INTO users(email) VALUES ('a@example.com'), ('b@example.com');
        """,
        "mode": "explain",
    },
    "db-exists-active-users": {
        "setup": """
            CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE sessions(user_id INTEGER, status TEXT);
            INSERT INTO users(id, name) VALUES (1, 'Ada'), (2, 'Ben'), (3, 'Cici');
            INSERT INTO sessions(user_id, status) VALUES
                (1, 'active'),
                (1, 'expired'),
                (2, 'expired');
        """,
        "expected_rows": [("Ada",)],
        "ordered": True,
    },
    "db-create-user-view": {
        "setup": """
            CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, status TEXT);
            INSERT INTO users(name, status) VALUES
                ('Ada', 'active'),
                ('Ben', 'inactive');
        """,
        "mode": "script",
        "check_sql": "SELECT name, status FROM active_users ORDER BY name;",
        "expected_rows": [("Ada", "active")],
        "ordered": True,
    },
    "db-create-covering-index-report": {
        "setup": """
            CREATE TABLE reports(id INTEGER PRIMARY KEY, created_at TEXT, status TEXT, owner_id INTEGER);
        """,
        "mode": "ddl",
    },
    "db-add-status-column-users": {
        "setup": """
            CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);
        """,
        "mode": "ddl",
    },
    "db-create-enrollment-foreign-key": {
        "setup": """
            CREATE TABLE students(id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE courses(id INTEGER PRIMARY KEY, title TEXT);
        """,
        "mode": "ddl",
    },
    "db-left-join-course-report": {
        "setup": """
            CREATE TABLE courses(id INTEGER PRIMARY KEY, title TEXT);
            CREATE TABLE enrollments(course_id INTEGER, student_id INTEGER);
            INSERT INTO courses(id, title) VALUES (1, 'Python'), (2, 'SQL'), (3, 'C#');
            INSERT INTO enrollments(course_id, student_id) VALUES
                (1, 101), (1, 102), (2, 201);
        """,
        "expected_rows": [("C#", 0), ("Python", 2), ("SQL", 1)],
        "ordered": False,
    },
    "db-coalesce-city-label": {
        "setup": """
            CREATE TABLE users(name TEXT, city TEXT);
            INSERT INTO users(name, city) VALUES
                ('Ada', 'Shanghai'),
                ('Ben', NULL),
                ('Cici', 'Shenzhen');
        """,
        "expected_rows": [
            ("Ada", "Shanghai"),
            ("Ben", "未知城市"),
            ("Cici", "Shenzhen"),
        ],
        "ordered": True,
    },
}


@dataclass
class Exercise:
    id: str
    title: str
    track_id: str
    difficulty: str
    prompt: str
    lesson_id: str
    hints: List[str] = field(default_factory=list)
    starter_code: str = ""
    expected_nodes: List[str] = field(default_factory=list)
    required_names: List[str] = field(default_factory=list)
    tests: List[Dict] = field(default_factory=list)
    required_keywords: List[str] = field(default_factory=list)
    forbidden_keywords: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    passed: bool
    score: int
    feedback_lines: List[str]
    stdout: str = ""
    duration_sec: int = 0

    @property
    def feedback_text(self) -> str:
        return "\n".join(self.feedback_lines)


class PracticeService:
    def __init__(self, metadata_path: Optional[Path] = None):
        self.metadata_path = metadata_path or (METADATA_DIR / "exercises.json")
        self.exercises = self._load_exercises()

    def _load_exercises(self) -> List[Exercise]:
        try:
            raw = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"[PracticeService] 练习元数据文件未找到: {self.metadata_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"[PracticeService] 练习元数据 JSON 解析失败: {e}")
            return []
        exercises = []
        for item in raw["exercises"]:
            fallback = {**EXERCISE_FALLBACKS, **DATABASE_EXERCISE_FALLBACKS}.get(
                item["id"], {}
            )
            patched = dict(item)
            for field_name in ("title", "difficulty", "prompt"):
                value = patched.get(field_name, "")
                if isinstance(value, str) and _needs_fallback(value):
                    patched[field_name] = fallback.get(field_name, value)
            hints = patched.get("hints", [])
            if any(_needs_fallback(hint) for hint in hints):
                patched["hints"] = fallback.get("hints", hints)
            starter_code = patched.get("starter_code", "")
            if isinstance(starter_code, str) and _needs_fallback(starter_code):
                patched["starter_code"] = fallback.get("starter_code", starter_code)
            tests = patched.get("tests", [])
            if any(_needs_fallback(str(test.get("expected", ""))) for test in tests):
                patched["tests"] = fallback.get("tests", tests)
            exercises.append(Exercise(**patched))
        return exercises

    def filtered(self, track_id: str, difficulty: str) -> List[Exercise]:
        results = self.exercises
        if track_id != "all":
            results = [
                exercise for exercise in results if exercise.track_id == track_id
            ]
        if difficulty != "all":
            results = [
                exercise for exercise in results if exercise.difficulty == difficulty
            ]
        return results

    def exercise_by_id(self, exercise_id: str) -> Optional[Exercise]:
        return next((item for item in self.exercises if item.id == exercise_id), None)

    def evaluate(self, exercise: Exercise, code: str) -> EvaluationResult:
        if exercise.track_id == "database":
            return self._evaluate_sql(exercise, code)
        if exercise.track_id in {"c", "csharp"}:
            return self._evaluate_keyword_code(exercise, code)
        return self._evaluate_python(exercise, code)

    @staticmethod
    def _normalize_rows(rows, ordered: bool):
        normalized = [tuple(row) for row in rows]
        if ordered:
            return normalized
        return sorted(
            normalized,
            key=lambda row: tuple("" if item is None else str(item) for item in row),
        )

    @staticmethod
    def _validate_sql_side_effect(exercise_id: str, conn: sqlite3.Connection) -> bool:
        if exercise_id == "db-design-enrollment-table":
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(enrollments)").fetchall()
            }
            return {"student_id", "course_id"}.issubset(columns)
        if exercise_id == "db-orders-foreign-key":
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()
            }
            foreign_keys = conn.execute("PRAGMA foreign_key_list(orders)").fetchall()
            return {"user_id"}.issubset(columns) and any(
                row[2] == "users" and row[3] == "user_id" for row in foreign_keys
            )
        if exercise_id == "db-create-index-users-email":
            indexes = conn.execute("PRAGMA index_list(users)").fetchall()
            for index in indexes:
                index_name = index[1]
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", index_name):
                    continue
                indexed_columns = {
                    row[2]
                    for row in conn.execute(
                        f"PRAGMA index_info([{index_name}])"
                    ).fetchall()
                }
                if "email" in indexed_columns:
                    return True
            return False
        if exercise_id == "db-add-column-migration":
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
            }
            return "last_login" in columns
        if exercise_id == "db-create-covering-index-report":
            indexes = conn.execute("PRAGMA index_list(reports)").fetchall()
            for index in indexes:
                index_name = index[1]
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", index_name):
                    continue
                indexed_columns = [
                    row[2]
                    for row in conn.execute(
                        f"PRAGMA index_info([{index_name}])"
                    ).fetchall()
                ]
                if indexed_columns and indexed_columns[:2] == ["created_at", "status"]:
                    return True
            return False
        if exercise_id == "db-add-status-column-users":
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
            }
            return "status" in columns
        if exercise_id == "db-create-enrollment-foreign-key":
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(enrollments)").fetchall()
            }
            foreign_keys = conn.execute(
                "PRAGMA foreign_key_list(enrollments)"
            ).fetchall()
            has_student_fk = any(
                row[2] == "students" and row[3] == "student_id" for row in foreign_keys
            )
            has_course_fk = any(
                row[2] == "courses" and row[3] == "course_id" for row in foreign_keys
            )
            return (
                {"student_id", "course_id"}.issubset(columns)
                and has_student_fk
                and has_course_fk
            )
        if exercise_id == "db-explain-users-query":
            rows = conn.execute(
                "EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'a@example.com'"
            ).fetchall()
            return bool(rows)
        return False

    def _evaluate_sql_fixture(
        self, exercise: Exercise, code: str, fixture: Dict
    ) -> EvaluationResult:
        start = time.time()
        normalized = " ".join(code.lower().split())
        feedback: List[str] = []
        score = 0

        if not normalized:
            return EvaluationResult(
                passed=False,
                score=0,
                feedback_lines=["答案为空，先把 SQL 写出来再提交。"],
                duration_sec=int(time.time() - start),
            )

        missing = [
            keyword
            for keyword in exercise.required_keywords
            if keyword.lower() not in normalized
        ]
        if missing:
            feedback.append(f"还缺少这些关键结构: {', '.join(missing)}")
        else:
            score += 20
            feedback.append("关键 SQL 结构已经覆盖。")

        forbidden = [
            keyword
            for keyword in exercise.forbidden_keywords
            if keyword.lower() in normalized
        ]
        if forbidden:
            feedback.append(f"出现了不建议使用的关键字: {', '.join(forbidden)}")
        else:
            score += 10

        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            if fixture.get("setup"):
                conn.executescript(fixture["setup"])

            try:
                mode = fixture.get("mode", "query")
                if mode == "query":
                    rows = conn.execute(code).fetchall()
                    expected_rows = fixture.get("expected_rows", [])
                    actual = self._normalize_rows(rows, fixture.get("ordered", False))
                    expected = self._normalize_rows(
                        expected_rows, fixture.get("ordered", False)
                    )
                    if actual == expected:
                        score += 70
                        feedback.append(
                            "结果集和参考答案一致，已经通过真实数据库比对。"
                        )
                    else:
                        feedback.append("SQL 能执行，但结果集和参考答案不一致。")
                        feedback.append(f"预期结果: {expected}")
                        feedback.append(f"你的结果: {actual}")
                elif mode == "script":
                    conn.executescript(code)
                    rows = conn.execute(fixture["check_sql"]).fetchall()
                    actual = self._normalize_rows(rows, fixture.get("ordered", False))
                    expected = self._normalize_rows(
                        fixture.get("expected_rows", []), fixture.get("ordered", False)
                    )
                    if actual == expected:
                        score += 70
                        feedback.append("脚本执行成功，落库后的结果和参考答案一致。")
                    else:
                        feedback.append(
                            "脚本执行成功，但落库后的结果和参考答案不一致。"
                        )
                        feedback.append(f"预期结果: {expected}")
                        feedback.append(f"你的结果: {actual}")
                elif mode == "explain":
                    plan_rows = conn.execute(code).fetchall()
                    if plan_rows:
                        score += 70
                        feedback.append("EXPLAIN 查询执行成功，已经拿到执行计划结果。")
                    else:
                        feedback.append("SQL 能执行，但没有返回执行计划结果。")
                else:
                    conn.executescript(code)
                    if self._validate_sql_side_effect(exercise.id, conn):
                        score += 70
                        feedback.append(
                            "数据库结构变更符合题目要求，已经通过真实校验。"
                        )
                    else:
                        feedback.append("SQL 已执行，但数据库结构还没有达到题目要求。")
            except sqlite3.Error as exc:
                feedback.append(f"SQL 执行失败: {exc}")
        finally:
            conn.close()

        if ";" in code:
            score += 5
        return EvaluationResult(
            passed=score >= 70
            and not missing
            and not forbidden
            and all("执行失败" not in item for item in feedback),
            score=min(score, 100),
            feedback_lines=feedback,
            duration_sec=int(time.time() - start),
        )

    def _evaluate_sql(self, exercise: Exercise, code: str) -> EvaluationResult:
        fixture = SQL_QUERY_FIXTURES.get(exercise.id)
        if fixture:
            return self._evaluate_sql_fixture(exercise, code, fixture)
        if exercise.id in {
            "db-design-enrollment-table",
            "db-orders-foreign-key",
            "db-create-index-users-email",
            "db-add-column-migration",
            "db-create-covering-index-report",
            "db-add-status-column-users",
            "db-create-enrollment-foreign-key",
            "db-explain-users-query",
        }:
            ddl_fixture = {"setup": "", "mode": "ddl"}
            if exercise.id == "db-orders-foreign-key":
                ddl_fixture["setup"] = (
                    "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);"
                )
            elif exercise.id == "db-create-index-users-email":
                ddl_fixture["setup"] = (
                    "CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT);"
                )
            elif exercise.id == "db-add-column-migration":
                ddl_fixture["setup"] = (
                    "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);"
                )
            elif exercise.id == "db-create-covering-index-report":
                ddl_fixture["setup"] = (
                    "CREATE TABLE reports(id INTEGER PRIMARY KEY, created_at TEXT, status TEXT, owner_id INTEGER);"
                )
            elif exercise.id == "db-add-status-column-users":
                ddl_fixture["setup"] = (
                    "CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT);"
                )
            elif exercise.id == "db-create-enrollment-foreign-key":
                ddl_fixture["setup"] = """
                    CREATE TABLE students(id INTEGER PRIMARY KEY, name TEXT);
                    CREATE TABLE courses(id INTEGER PRIMARY KEY, title TEXT);
                """
            elif exercise.id == "db-explain-users-query":
                return self._evaluate_sql_fixture(
                    exercise, code, SQL_QUERY_FIXTURES["db-explain-users-query"]
                )
            return self._evaluate_sql_fixture(exercise, code, ddl_fixture)

        start = time.time()
        normalized = " ".join(code.lower().split())
        feedback: List[str] = []
        score = 0

        feedback.append(
            "当前为 SQL 结构训练题，本轮先检查查询结构，暂不执行真实数据库结果比对。"
        )

        if normalized:
            score += 20
            feedback.append("已提交 SQL 答案。")
        else:
            feedback.append("答案为空，先写出查询语句。")

        missing = [
            keyword
            for keyword in exercise.required_keywords
            if keyword.lower() not in normalized
        ]
        if not missing:
            score += 50
            feedback.append("关键 SQL 结构完整。")
        else:
            feedback.append(f"缺少关键结构: {', '.join(missing)}")

        forbidden = [
            keyword
            for keyword in exercise.forbidden_keywords
            if keyword.lower() in normalized
        ]
        if forbidden:
            feedback.append(f"出现了不建议使用的关键字: {', '.join(forbidden)}")
        else:
            score += 20
            feedback.append("没有使用禁用关键字。")

        if ";" in code:
            score += 10
            feedback.append("语句结束符处理规范。")

        return EvaluationResult(
            passed=score >= 70 and not missing,
            score=min(score, 100),
            feedback_lines=feedback,
            duration_sec=int(time.time() - start),
        )

    def _evaluate_keyword_code(self, exercise: Exercise, code: str) -> EvaluationResult:
        start = time.time()
        normalized = " ".join(code.lower().split())
        feedback: List[str] = []
        score = 0

        feedback.append("当前为结构训练题，本轮先检查关键结构，暂不执行真实编译运行。")

        if normalized:
            score += 20
            feedback.append("已提交代码草稿。")
        else:
            feedback.append("答案为空，先把函数签名和核心结构写出来。")

        missing = [
            keyword
            for keyword in exercise.required_keywords
            if keyword.lower() not in normalized
        ]
        if not missing:
            score += 50
            feedback.append("关键结构已经覆盖。")
        else:
            feedback.append(f"还缺少这些关键结构: {', '.join(missing)}")

        forbidden = [
            keyword
            for keyword in exercise.forbidden_keywords
            if keyword.lower() in normalized
        ]
        if forbidden:
            feedback.append(f"出现了不建议使用的关键字: {', '.join(forbidden)}")
        else:
            score += 20
            feedback.append("没有出现禁用关键字。")

        if ";" in code or "{" in code:
            score += 10
            feedback.append("代码书写格式看起来像目标语言。")

        return EvaluationResult(
            passed=score >= 70 and not missing,
            score=min(score, 100),
            feedback_lines=feedback,
            duration_sec=int(time.time() - start),
        )

    def _evaluate_python(self, exercise: Exercise, code: str) -> EvaluationResult:
        result = evaluate_python_code(
            code,
            exercise.expected_nodes,
            exercise.required_names,
            exercise.tests,
        )
        return EvaluationResult(
            passed=bool(result["passed"]),
            score=int(result["score"]),
            feedback_lines=list(result["feedback_lines"]),
            stdout=str(result.get("stdout", "")),
            duration_sec=int(result.get("duration_sec", 0)),
        )
