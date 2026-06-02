# -*- coding: utf-8 -*-
"""
Rebuild all course content based on the comprehensive learning roadmap document.
Covers Python, C, C++, C#, Database, Algorithms, and Integration tracks.
"""

import json
import os
from pathlib import Path

BASE = str(Path(__file__).resolve().parent / "content")


def load_map():
    with open(
        os.path.join(BASE, "metadata", "course_map.json"), "r", encoding="utf-8"
    ) as f:
        return json.load(f)


def save_map(data):
    with open(
        os.path.join(BASE, "metadata", "course_map.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_md(track, filename, content):
    d = os.path.join(BASE, track)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    lines = len(content.split("\n"))
    print(f"  {filename}: {lines} lines")


# ============================================================
# PYTHON TRACK
# ============================================================
PYTHON_TRACK = {
    "id": "python",
    "title": "Python 主线",
    "icon": "🐍",
    "summary": '从基础语法到 Web 后端开发，系统掌握 Python 工程能力。按"主课-手册-练习-实战"四层体系学习。',
    "modules": [
        {
            "id": "python-foundations",
            "title": "基础模块 · 语法与表达",
            "summary": "建立对变量、流程控制、函数和数据容器的第一性理解。",
            "lessons": [
                {
                    "id": "py-thinking",
                    "title": "Python 学习地图与环境准备",
                    "summary": "理解解释器、脚本、运行环境和学习顺序，避免一开始就被工具链劝退。",
                    "path": "python/py_thinking.md",
                    "difficulty": "基础",
                    "estimated_minutes": 25,
                    "tags": ["环境", "解释器", "入门"],
                    "prerequisites": [],
                    "outcomes": [
                        "能解释解释器、脚本和第三方库的区别",
                        "能在终端运行一个 Python 文件",
                        "知道为什么先学语言再学数据库和项目",
                    ],
                },
                {
                    "id": "py-data-types",
                    "title": "变量、类型与表达式",
                    "summary": "写出稳定代码的前提，是先理解数据长什么样、表达式如何求值。",
                    "path": "python/py_data_types.md",
                    "difficulty": "基础",
                    "estimated_minutes": 35,
                    "tags": ["变量", "类型", "表达式"],
                    "prerequisites": ["py-thinking"],
                    "outcomes": [
                        "能区分常见基础类型",
                        "知道赋值和重新赋值的含义",
                        "能写出正确的算术和逻辑表达式",
                    ],
                },
                {
                    "id": "py-control-flow",
                    "title": "流程控制与循环",
                    "summary": "程序的核心是控制流，理解 if/for/while 如何决定程序走向。",
                    "path": "python/py_control_flow.md",
                    "difficulty": "基础",
                    "estimated_minutes": 35,
                    "tags": ["if", "for", "while"],
                    "prerequisites": ["py-data-types"],
                    "outcomes": [
                        "能用 if/elif/else 做分支判断",
                        "掌握 for 和 while 循环的使用场景",
                        "理解 break/continue/pass 的作用",
                    ],
                },
                {
                    "id": "py-functions",
                    "title": "函数与模块化",
                    "summary": "函数是代码复用的基本单位，理解参数、返回值、作用域和模块导入。",
                    "path": "python/py_functions.md",
                    "difficulty": "基础",
                    "estimated_minutes": 40,
                    "tags": ["函数", "参数", "模块"],
                    "prerequisites": ["py-control-flow"],
                    "outcomes": [
                        "能定义和调用函数",
                        "理解位置参数、关键字参数和默认参数",
                        "知道如何导入和使用模块",
                    ],
                },
                {
                    "id": "py-exceptions-files",
                    "title": "异常处理与文件 I/O",
                    "summary": "学会处理程序运行时的错误，以及读写文件数据。",
                    "path": "python/py_exceptions_files.md",
                    "difficulty": "基础",
                    "estimated_minutes": 40,
                    "tags": ["异常", "文件", "I/O"],
                    "prerequisites": ["py-functions"],
                    "outcomes": [
                        "会用 try/except/finally 处理异常",
                        "能读写文本和二进制文件",
                        "理解上下文管理器 with 的作用",
                    ],
                },
            ],
        },
        {
            "id": "python-data-containers",
            "title": "核心模块 · 数据容器与迭代",
            "summary": "掌握 Python 的核心数据结构，理解迭代器、生成器和上下文管理器。",
            "lessons": [
                {
                    "id": "py-lists-tuples",
                    "title": "列表、元组与序列操作",
                    "summary": "列表和元组是最常用的序列类型，理解它们的区别和操作方式。",
                    "path": "python/py_lists_tuples.md",
                    "difficulty": "基础",
                    "estimated_minutes": 40,
                    "tags": ["list", "tuple", "序列"],
                    "prerequisites": ["py-exceptions-files"],
                    "outcomes": [
                        "熟练使用列表的增删改查",
                        "理解元组的不可变性",
                        "掌握切片和列表推导式",
                    ],
                },
                {
                    "id": "py-dicts-sets",
                    "title": "字典、集合与映射",
                    "summary": "字典和集合基于哈希表实现，理解它们的查找性能和适用场景。",
                    "path": "python/py_dicts_sets.md",
                    "difficulty": "基础",
                    "estimated_minutes": 35,
                    "tags": ["dict", "set", "哈希"],
                    "prerequisites": ["py-lists-tuples"],
                    "outcomes": [
                        "熟练使用字典的增删改查",
                        "理解集合的去重和集合运算",
                        "知道字典推导式的用法",
                    ],
                },
                {
                    "id": "py-iterators-generators",
                    "title": "迭代器、生成器与上下文管理器",
                    "summary": "理解 Python 的迭代协议，学会用生成器节省内存，用上下文管理器管理资源。",
                    "path": "python/py_iterators_generators.md",
                    "difficulty": "进阶",
                    "estimated_minutes": 45,
                    "tags": ["迭代器", "生成器", "with"],
                    "prerequisites": ["py-dicts-sets"],
                    "outcomes": [
                        "理解 __iter__ 和 __next__ 协议",
                        "会用 yield 写生成器",
                        "能实现自定义上下文管理器",
                    ],
                },
                {
                    "id": "py-comprehensions",
                    "title": "推导式与函数式工具",
                    "summary": "掌握列表/字典/集合推导式，学习 functools 和 itertools 的常用工具。",
                    "path": "python/py_comprehensions.md",
                    "difficulty": "进阶",
                    "estimated_minutes": 40,
                    "tags": ["推导式", "functools", "itertools"],
                    "prerequisites": ["py-iterators-generators"],
                    "outcomes": [
                        "会写各种推导式",
                        "理解 map/filter/reduce",
                        "知道 itertools 的常用函数",
                    ],
                },
            ],
        },
        {
            "id": "python-oop",
            "title": "进阶模块 · 面向对象与类型系统",
            "summary": "掌握面向对象编程，理解描述符、魔术方法和 typing 类型系统。",
            "lessons": [
                {
                    "id": "py-oop-basics",
                    "title": "类、对象与继承",
                    "summary": "学习 class 定义、实例方法、继承和多态，理解组合优先于继承的原则。",
                    "path": "python/py_oop_basics.md",
                    "difficulty": "进阶",
                    "estimated_minutes": 45,
                    "tags": ["class", "继承", "多态"],
                    "prerequisites": ["py-comprehensions"],
                    "outcomes": [
                        "会定义类和创建对象",
                        "理解继承和方法重写",
                        "知道组合优先于继承的原则",
                    ],
                },
                {
                    "id": "py-magic-methods",
                    "title": "魔术方法与描述符",
                    "summary": "理解 __init__/__str__/__eq__ 等魔术方法，学习 property 和描述符协议。",
                    "path": "python/py_magic_methods.md",
                    "difficulty": "进阶",
                    "estimated_minutes": 45,
                    "tags": ["魔术方法", "property", "描述符"],
                    "prerequisites": ["py-oop-basics"],
                    "outcomes": [
                        "会实现常用的魔术方法",
                        "理解 property 的工作原理",
                        "知道描述符协议的应用场景",
                    ],
                },
                {
                    "id": "py-typing",
                    "title": "类型注解与静态分析",
                    "summary": "学习 typing 体系（PEP 484），理解类型注解、泛型和静态类型检查工具。",
                    "path": "python/py_typing.md",
                    "difficulty": "进阶",
                    "estimated_minutes": 40,
                    "tags": ["typing", "类型注解", "mypy"],
                    "prerequisites": ["py-oop-basics"],
                    "outcomes": [
                        "会写类型注解",
                        "理解 Optional/Union/Generic",
                        "能用 mypy 做静态类型检查",
                    ],
                },
                {
                    "id": "py-dataclass",
                    "title": "dataclass 与工程化实践",
                    "summary": "学习 dataclass 简化数据类定义，理解 PEP 8 编码规范和工程化最佳实践。",
                    "path": "python/py_dataclass.md",
                    "difficulty": "进阶",
                    "estimated_minutes": 35,
                    "tags": ["dataclass", "PEP 8", "工程化"],
                    "prerequisites": ["py-typing"],
                    "outcomes": [
                        "会用 dataclass 定义数据类",
                        "理解 PEP 8 编码规范",
                        "知道工程化项目的基本结构",
                    ],
                },
            ],
        },
        {
            "id": "python-concurrency",
            "title": "高级模块 · 并发编程与性能",
            "summary": "理解 GIL 与并发模型，掌握 threading、asyncio 和 multiprocessing。",
            "lessons": [
                {
                    "id": "py-concurrency-concepts",
                    "title": "并发 vs 并行与 GIL",
                    "summary": "理解并发和并行的区别，认识 GIL 对多线程的影响，建立正确的并发思维。",
                    "path": "python/py_concurrency_concepts.md",
                    "difficulty": "进阶",
                    "estimated_minutes": 40,
                    "tags": ["并发", "GIL", "并行"],
                    "prerequisites": ["py-dataclass"],
                    "outcomes": [
                        "理解并发和并行的区别",
                        "知道 GIL 的影响",
                        "能选择合适的并发模型",
                    ],
                },
                {
                    "id": "py-threading-multiprocessing",
                    "title": "线程池与进程池",
                    "summary": "学习 threading 和 multiprocessing，掌握 concurrent.futures 的高级接口。",
                    "path": "python/py_threading_multiprocessing.md",
                    "difficulty": "进阶",
                    "estimated_minutes": 45,
                    "tags": ["threading", "multiprocessing", "futures"],
                    "prerequisites": ["py-concurrency-concepts"],
                    "outcomes": [
                        "会用 ThreadPoolExecutor",
                        "会用 ProcessPoolExecutor",
                        "理解 I/O 密集和 CPU 密集的区别",
                    ],
                },
                {
                    "id": "py-asyncio",
                    "title": "asyncio 异步编程",
                    "summary": "理解事件循环、协程、任务，掌握异步 I/O 编程模式。",
                    "path": "python/py_asyncio.md",
                    "difficulty": "进阶",
                    "estimated_minutes": 50,
                    "tags": ["asyncio", "协程", "事件循环"],
                    "prerequisites": ["py-concurrency-concepts"],
                    "outcomes": [
                        "理解 async/await 语法",
                        "会创建和管理任务",
                        "理解异步 I/O 的优势",
                    ],
                },
                {
                    "id": "py-performance",
                    "title": "性能剖析与优化策略",
                    "summary": "学习使用 cProfile、timeit 等工具定位性能瓶颈，理解何时用 C 扩展或多进程。",
                    "path": "python/py_performance.md",
                    "difficulty": "综合",
                    "estimated_minutes": 45,
                    "tags": ["性能", "cProfile", "优化"],
                    "prerequisites": ["py-asyncio"],
                    "outcomes": [
                        "会用 cProfile 定位瓶颈",
                        "理解优化的优先级",
                        "知道何时该用 C 扩展",
                    ],
                },
            ],
        },
        {
            "id": "python-frameworks",
            "title": "实战模块 · 框架与项目",
            "summary": "学习 FastAPI/Flask 框架，掌握 Web 后端开发的完整链路。",
            "lessons": [
                {
                    "id": "py-web-basics",
                    "title": "Web API 与 FastAPI 入门",
                    "summary": "理解 HTTP 协议和 RESTful API 设计，用 FastAPI 快速搭建 Web 服务。",
                    "path": "python/py_web_basics.md",
                    "difficulty": "进阶",
                    "estimated_minutes": 45,
                    "tags": ["FastAPI", "HTTP", "API"],
                    "prerequisites": ["py-asyncio"],
                    "outcomes": [
                        "理解 HTTP 协议基础",
                        "会用 FastAPI 写 API",
                        "知道 Pydantic 数据校验",
                    ],
                },
                {
                    "id": "py-web-engineering",
                    "title": "Web 工程实践",
                    "summary": "学习依赖注入、配置管理、日志、测试和部署，构建生产级 Web 应用。",
                    "path": "python/py_web_engineering.md",
                    "difficulty": "综合",
                    "estimated_minutes": 50,
                    "tags": ["工程化", "测试", "部署"],
                    "prerequisites": ["py-web-basics"],
                    "outcomes": ["会组织 Web 项目结构", "理解依赖注入", "能写单元测试"],
                },
                {
                    "id": "py-web-database",
                    "title": "数据库集成与 ORM",
                    "summary": "学习 SQLAlchemy 和 Alembic，掌握数据库连接、迁移和 ORM 操作。",
                    "path": "python/py_web_database.md",
                    "difficulty": "综合",
                    "estimated_minutes": 45,
                    "tags": ["SQLAlchemy", "ORM", "迁移"],
                    "prerequisites": ["py-web-engineering"],
                    "outcomes": [
                        "会用 SQLAlchemy 操作数据库",
                        "理解 Alembic 迁移",
                        "知道连接池的作用",
                    ],
                },
                {
                    "id": "py-project-complete",
                    "title": "综合实战项目",
                    "summary": "综合运用所学知识，从零开始设计并实现一个完整的 Python Web 项目。",
                    "path": "python/py_project_complete.md",
                    "difficulty": "综合",
                    "estimated_minutes": 90,
                    "tags": ["项目", "实战", "综合"],
                    "prerequisites": ["py-web-database"],
                    "outcomes": [
                        "能独立设计并实现一个 Python 项目",
                        "会组织项目目录结构和模块划分",
                        "掌握基本的单元测试编写",
                        "具备完整的项目交付能力",
                    ],
                },
            ],
        },
    ],
}

print(
    "Python track defined:",
    sum(len(m["lessons"]) for m in PYTHON_TRACK["modules"]),
    "lessons",
)

# Save partial result
data = load_map()
for i, track in enumerate(data["tracks"]):
    if track["id"] == "python":
        data["tracks"][i] = PYTHON_TRACK
        break
save_map(data)
print("Python track saved to course_map.json")
