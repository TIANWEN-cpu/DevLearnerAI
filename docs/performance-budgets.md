# 性能预算 (Performance Budgets)

本文档定义 DevLearnerAI 各核心路径的性能基线和预算目标。所有数值基于
Windows 11 + Python 3.12 + SSD 环境下的 `pytest-benchmark` 测量。

---

## 1. 代码沙箱 (python_runner.py)

| 操作                   | 代码体量 | 预算 (ms) | 说明                     |
|------------------------|----------|-----------|--------------------------|
| validate_code_safety   | ~10 行   | < 0.5     | AST walk + 安全检查      |
| validate_code_safety   | ~80 行   | < 2       | 中等体量                 |
| validate_code_safety   | ~400 行  | < 10      | 大型练习                 |
| ast.parse              | ~10 行   | < 0.1     | 语法解析                 |
| ast.parse              | ~80 行   | < 0.5     |                          |
| ast.parse              | ~400 行  | < 3       |                          |

**关注点**: validate_code_safety 是沙箱入口的热路径。如果超过预算，应检查
`_DANGEROUS_ATTRS` 集合查找或 `ast.walk` 中的 isinstance 分支。

---

## 2. 数据库 (database.py)

| 操作                  | 数据规模  | 预算 (ms) | 说明                       |
|-----------------------|-----------|-----------|----------------------------|
| mark_lesson_opened    | -         | < 2       | 含 SELECT + INSERT/UPDATE  |
| mark_lesson_completed | -         | < 2       | UPSERT                     |
| lesson_status         | -         | < 1       | 单行 SELECT                |
| save_note             | -         | < 2       | UPSERT                     |
| load_note             | -         | < 1       | 单行 SELECT                |
| save_exercise_draft   | -         | < 2       | UPSERT                     |
| record_attempts_batch | 10 条     | < 5       | executemany                |
| record_attempts_batch | 100 条    | < 20      |                            |
| record_attempts_batch | 500 条    | < 80      |                            |
| recent_attempts(10)   | 1000 条   | < 3       | LIMIT + ORDER BY           |
| recent_attempts(100)  | 1000 条   | < 5       |                            |
| average_score         | 1000 条   | < 5       | AVG 聚合                   |
| completed_lessons     | 500 条    | < 3       | COUNT 聚合                 |

**关注点**: 批量插入应利用 WAL 模式和单一事务。如果超标，检查
`connect()` 上下文管理器的锁竞争。

---

## 3. 内容服务 (content_service.py)

| 操作                  | 数据规模     | 预算 (ms) | 说明                   |
|-----------------------|--------------|-----------|------------------------|
| ContentService init   | 3x4x5=60 课 | < 50      | JSON 解析 + 索引构建   |
| ContentService init   | 5x6x10=300 课 | < 200   | 大规模课程体系         |
| lesson_by_id          | 60 课        | < 0.1     | 字典 O(1) 查找         |
| lesson_markdown 首读  | -            | < 5       | 磁盘 I/O              |
| lesson_markdown 缓存  | -            | < 0.01    | 内存缓存命中           |
| _clean_text 正常      | -            | < 0.01    | 字符串操作             |
| _clean_list 50 项     | -            | < 0.1     | 列表遍历               |

**关注点**: init 是启动路径关键项。如果超标，检查 `_discover_tracks` 中的
JSON 解析或 `_build_lesson_index` 的三层循环。

---

## 4. Markdown 渲染 (markdown_renderer.py)

| 操作               | 内容体量    | 预算 (ms) | 说明                       |
|--------------------|-------------|-----------|----------------------------|
| render_message_html | 短文本     | < 1       | mistune + sanitize         |
| render_message_html | 中等 Markdown | < 5    | 含表格、代码块             |
| render_message_html | 大型 Markdown | < 50   | 30 章节                    |
| render_message_html | 纯文本模式 | < 0.5     | escape + br 替换           |
| sanitize_html 简单 | -          | < 0.5     | 白名单过滤                 |
| sanitize_html 复杂 | -          | < 3       | 含 script/事件/危险链接    |
| bubble_html 用户    | -          | < 1       | HTML 模板构建              |
| bubble_html 助手    | 中等       | < 10      | 含 Markdown 渲染           |

**关注点**: render_message_html 是 AI 聊天的关键路径。如果超标，瓶颈可能在
`mistune.html()` 解析或 `_HTMLSanitizer.sanitize()` 的标签遍历。

---

## 5. 练习评测 (evaluator.py / normalizer.py)

| 操作                    | 规模         | 预算 (ms) | 说明                   |
|-------------------------|--------------|-----------|------------------------|
| evaluate_keyword_code   | 5 关键词     | < 1       | 字符串包含检查         |
| evaluate_keyword_code   | 20 关键词    | < 2       |                        |
| evaluate_keyword_code   | 50 关键词    | < 5       |                        |
| evaluate_sql_fixture    | 查询模式     | < 10      | 内存 SQLite 执行       |
| evaluate_sql_fixture    | 脚本模式     | < 15      | executescript          |
| normalize_rows          | 10 行        | < 0.1     | 排序 + tuple 转换      |
| normalize_rows          | 100 行       | < 0.5     |                        |
| normalize_rows          | 1000 行      | < 5       |                        |
| normalize_rows          | 10000 行     | < 50      |                        |
| normalize_rows(ordered) | 1000 行      | < 1       | 跳过排序               |

**关注点**: normalize_rows 排序的 key 函数使用 str() 转换，大规模数据时
可能成为热点。evaluate_sql_fixture 的耗时主要在 SQLite 内存数据库。

---

## 6. 回归策略

- **CI 集成**: `make bench` 可在 CI 中运行，配合 `--benchmark-compare` 与
  基线对比。建议在 PR 中触发但不阻断合并（warn-only）。
- **基线更新**: 每个发布周期运行一次 `pytest --benchmark-save=vX.Y`，
  形成可追溯的性能历史。
- **阈值设置**: 建议使用 `--benchmark-max-time=5` 控制单个测试最长运行
  时间，避免基准测试本身成为瓶颈。

---

## 7. 运行命令

```bash
# 安装依赖
pip install pytest-benchmark

# 运行全部基准测试
make bench

# 运行单个模块基准
pytest tests/benchmark/test_benchmark_database.py --benchmark-enable -v

# 保存基线
pytest tests/benchmark/ --benchmark-enable --benchmark-save=baseline

# 与基线对比
pytest tests/benchmark/ --benchmark-enable --benchmark-compare=baseline
```
