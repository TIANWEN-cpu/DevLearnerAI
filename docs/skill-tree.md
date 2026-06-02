# 技能树：课程依赖关系图

本文档展示各路线课程之间的技能依赖关系，帮助学习者理解学习顺序和知识衔接。

---

## Python 主线技能树

```
py-thinking (环境准备)
  └── py-data-types (变量与类型)
       └── py-control-flow (流程控制)
            └── py-functions (函数)
                 └── py-exceptions-files (异常与文件)
                      ├── py-lists-tuples (列表与元组)
                      │    └── py-dicts-sets (字典与集合)
                      │         └── py-iterators-generators (迭代器与生成器)
                      │              └── py-comprehensions (推导式)
                      │                   └── py-oop-basics (类与继承)
                      │                        ├── py-magic-methods (魔术方法)
                      │                        ├── py-typing (类型注解)
                      │                        │    └── py-dataclass (dataclass)
                      │                        │         └── py-concurrency-concepts (并发概念)
                      │                        │              ├── py-threading-multiprocessing (线程/进程)
                      │                        │              ├── py-asyncio (异步编程)
                      │                        │              │    ├── py-web-basics (Web API)
                      │                        │              │    │    └── py-web-engineering (Web 工程)
                      │                        │              │    │         └── py-web-database (数据库集成)
                      │                        │              │    │              └── py-project-complete (综合项目)
                      │                        │              │    └── py-performance (性能优化)
```

---

## C 语言路线技能树

```
c-thinking-setup (环境准备)
  └── c-syntax-basics (基础语法)
       └── c-arrays-strings (数组与字符串)
            └── c-pointers (指针)
                 └── c-functions-scope (函数与作用域)
                      ├── c-dynamic-memory (动态内存)
                      │    ├── c-structs-unions (结构体)
                      │    │    └── c-linked-lists (链表与树)
                      │    ├── c-file-io (文件 I/O)
                      │    │    ├── c-preprocessor (预处理器)
                      │    │    └── c-posix-basics (POSIX)
                      │    │         └── c-project-complete (综合项目)
                      │    ├── c-undefined-behavior (未定义行为)
                      │    └── c-debugging-tools (调试工具)
  └── c-make-build (构建系统)
       └── c-mini-libc (迷你 libc)
            └── c-memory-pool (内存池)
```

---

## C++ 路线技能树

```
cpp-thinking-setup (环境准备)
  ├── cpp-syntax-functions (基础语法)
  │    └── cpp-references-const (引用与 const)
  │         └── cpp-pointers-memory (指针与内存)
  │              └── cpp-arrays-strings (数组与字符串)
  │                   └── cpp-oop-classes (类与对象)
  │                        └── cpp-constructor-destructor (构造/析构)
  │                             └── cpp-inheritance (继承)
  │                                  └── cpp-polymorphism-virtual (多态)
  │                                       ├── cpp-abstract-interfaces (抽象接口)
  │                                       │    └── cpp-string-vector (string/vector)
  │                                       │         ├── cpp-iterators-loops (迭代器)
  │                                       │         │    ├── cpp-map-set (关联容器)
  │                                       │         │    └── cpp-stl-algorithms (STL 算法)
  │                                       │         │         └── cpp-lambda-functional (Lambda)
  │                                       │         │              ├── cpp-raii-smart-pointers (智能指针)
  │                                       │         │              │    ├── cpp-move-semantics (移动语义)
  │                                       │         │              │    ├── cpp-templates-intro (模板)
  │                                       │         │              │    │    └── cpp-templates-advanced (模板进阶)
  │                                       │         │              │    └── cpp-concurrency (并发)
  │                                       │         └── cpp-file-io-basics (文件 IO)
  │                                       └── cpp-design-patterns (设计模式)
  └── cpp-build-debug-workflow (构建调试)
       └── cpp-project-complete (综合项目)
```

---

## C# 路线技能树

```
cs-thinking-setup (环境准备)
  └── cs-syntax-basics (基础语法)
       └── cs-methods-params (方法与参数)
            └── cs-collections (集合与泛型)
                 ├── cs-oop-basics (面向对象)
                 │    ├── cs-generics-constraints (泛型约束)
                 │    ├── cs-delegates-events (委托与事件)
                 │    ├── cs-linq-basics (LINQ)
                 │    └── cs-async (异步编程)
                 │         └── cs-async-files (异步文件)
                 │              ├── cs-ef-core (EF Core)
                 │              │    └── cs-webapi-intro (Web API)
                 │              │         ├── cs-auth-security (认证安全)
                 │              │         │    └── cs-deployment (部署)
                 │              │         └── cs-testing-workflow (测试)
                 │              └── cs-exception-debugging (异常调试)
                 └── cs-dictionary-records (record 类型)
                      └── cs-di-lifetimes (依赖注入)
```

---

## 数据库路线技能树

```
db-concepts (数据库概念)
  └── db-crud (基础 CRUD)
       └── db-constraints-foreign-keys (约束与外键)
            ├── db-joins (连接查询)
            │    └── db-subqueries-sets (子查询)
            │         └── db-aggregation (聚合)
            │              └── db-join-patterns (连接模式)
            │                   └── db-window-functions (窗口函数)
            │                        └── db-cte-patterns (CTE)
            │                             └── db-reporting-case (报表)
            ├── db-normalization (范式)
            │    └── db-normalization-tradeoffs (反范式)
            ├── db-indexes (索引)
            │    ├── db-index-design-patterns (索引设计)
            │    │    └── db-covering-indexes (覆盖索引)
            │    └── db-explain-query-plans (执行计划)
            │         └── db-explain (EXPLAIN 详解)
            └── db-schema-design (Schema 设计)
                 └── db-migrations-basics (迁移)
                      └── db-data-cleaning-sql (数据清洗)
                           └── db-backup-recovery (备份恢复)
```

---

## 算法/数据结构路线技能树

```
algo-complexity (复杂度分析)
  ├── algo-arrays-strings (数组与字符串)
  │    └── algo-binary-search (二分查找)
  │         └── algo-sorting (排序)
  │              └── algo-greedy-backtrack (贪心与回溯)
  ├── algo-linked-lists (链表)
  │    └── algo-binary-trees (二叉树)
  │         ├── algo-bst (二叉搜索树)
  │         ├── algo-heaps (堆)
  │         └── algo-tree-bfs-dfs (树的遍历)
  ├── algo-stacks-queues (栈与队列)
  └── algo-hash-tables (哈希表)
       ├── algo-prefix-sum-window (前缀和与滑窗)
       └── algo-two-pointers (双指针)
            └── algo-graphs (图)
                 └── algo-graph-shortest-path (最短路径)
                      └── algo-dp (动态规划)
```

---

## 融合项目路线技能树

```
前置：Python 主线 + 数据库路线

int-frontend-basics (前端基础)
  └── int-api-design (API 设计)
       ├── int-ci-cd (CI/CD)
       │    └── int-docker (Docker)
       │         └── int-capstone (综合项目)
       └── int-docker (Docker)

前置：C 语言路线
  c 项目系列 (c_inventory, c_log_parser, c_matrix_tool)

前置：C++ 路线
  cpp 项目系列 (cpp_grade_book, cpp_text_stats)

前置：C# 路线
  csharp 项目系列 (csharp_tracker, csharp_notes_manager, csharp_api_dashboard, csharp_sqlite_desktop)

竞赛与拓展：
  int-lanqiao (蓝桥杯) → int-math-modeling (数学建模)
  int-platformio (PlatformIO) → int-wokwi-sim (Wokwi 模拟) → int-robotics (机器人)
  int-simulink (Simulink)
```

---

## 实战项目集技能树

```
前置：Python 基础语法

project-todo-cli (Todo CLI)
  ├── project-crawler (图片爬虫)
  ├── project-orm (ORM 框架)
  └── project-data-analysis (数据分析)
       ├── project-fastapi-ledger (FastAPI 记账本)
       │    ├── project-celery-redis (Redis + Celery)
       │    ├── project-django-blog (Django 博客)
       │    └── project-ai-chatbot (AI 对话助理)
       └── project-pyqt5-player (音乐播放器)

project-django-blog (Django 博客)
  └── project-selenium-test (Selenium 测试)
```

---

## 跨路线依赖关系

以下展示不同路线之间的推荐学习顺序：

| 依赖关系 | 说明 |
|---------|------|
| Python 基础 → 数据库基础 | SQL 练习建议用 Python 辅助验证 |
| Python + 数据库 → 融合项目 | 融合项目需要两者的知识 |
| C 语言 → C++ | 指针和内存管理是 C++ 的前置知识 |
| 任意语言路线 → 算法路线 | 算法练习需要用编程语言实现 |
| Python 全线 + 数据库 → 实战项目 | 项目实战需要完整的工程能力 |
| C# 路线 → 融合项目(C# 项目) | C# 项目需要 .NET 基础 |
