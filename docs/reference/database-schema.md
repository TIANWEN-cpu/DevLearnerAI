# 数据库 Schema

本文档描述 DevLearnerAI 的 SQLite 数据库表结构、索引和迁移策略。

---

## 概述

- **数据库引擎**: SQLite
- **日志模式**: WAL（Write-Ahead Logging）
- **外键约束**: 启用 (`PRAGMA foreign_keys = ON`)
- **数据库路径**: `%APPDATA%/DevLearnerAI/data/app.db`
- **旧版路径**: `db/learner.db`（自动迁移）

---

## 表结构

### lesson_progress

课程学习进度表。

```sql
CREATE TABLE IF NOT EXISTS lesson_progress (
    lesson_id TEXT PRIMARY KEY,        -- 课程 ID（主键）
    track_id TEXT NOT NULL,            -- 所属技术栈 ID
    status TEXT DEFAULT 'not_started', -- 状态: not_started / in_progress / completed
    completed INTEGER DEFAULT 0,       -- 是否完成: 0=否, 1=是
    last_opened TEXT,                  -- 最后打开时间 (YYYY-MM-DD HH:MM:SS)
    completed_at TEXT                  -- 完成时间 (YYYY-MM-DD HH:MM:SS)
);
```

**索引**:

```sql
CREATE INDEX idx_lesson_progress_track_completed ON lesson_progress(track_id, completed);
CREATE INDEX idx_lesson_progress_completed_at ON lesson_progress(completed_at);
```

**典型查询**:

```python
# 标记课程为已完成（UPSERT）
INSERT INTO lesson_progress (lesson_id, track_id, status, completed, last_opened, completed_at)
VALUES (?, ?, 'completed', 1, ?, ?)
ON CONFLICT(lesson_id) DO UPDATE SET
    status = 'completed', completed = 1, last_opened = excluded.last_opened, completed_at = excluded.completed_at

# 统计已完成课程数
SELECT COUNT(*) FROM lesson_progress WHERE completed = 1

# 查询技术栈完成数
SELECT COUNT(*) FROM lesson_progress WHERE track_id = ? AND completed = 1
```

---

### lesson_notes

课程笔记表。

```sql
CREATE TABLE IF NOT EXISTS lesson_notes (
    lesson_id TEXT PRIMARY KEY,  -- 课程 ID（主键）
    content TEXT DEFAULT '',     -- 笔记内容
    updated_at TEXT              -- 更新时间
);
```

---

### practice_attempts

练习评测记录表。

```sql
CREATE TABLE IF NOT EXISTS practice_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增 ID
    exercise_id TEXT NOT NULL,             -- 练习 ID
    exercise_title_snapshot TEXT,          -- 练习标题快照
    track_id TEXT NOT NULL,                -- 所属技术栈 ID
    code_snapshot TEXT,                    -- 提交的代码快照
    score INTEGER NOT NULL,                -- 得分 (0-100)
    passed INTEGER DEFAULT 0,             -- 是否通过: 0=否, 1=是
    duration_sec INTEGER DEFAULT 0,       -- 评测耗时（秒）
    submitted_at TEXT NOT NULL,           -- 提交时间
    feedback TEXT                         -- 评测反馈文本
);
```

**索引**:

```sql
CREATE INDEX idx_practice_attempts_exercise ON practice_attempts(exercise_id);
CREATE INDEX idx_practice_attempts_submitted ON practice_attempts(submitted_at);
CREATE INDEX idx_practice_attempts_track ON practice_attempts(track_id);
```

**典型查询**:

```python
# 最近练习记录
SELECT submitted_at, COALESCE(NULLIF(exercise_title_snapshot, ''), exercise_id) AS display_title,
       score, passed, duration_sec
FROM practice_attempts ORDER BY id DESC LIMIT ?

# 平均分
SELECT AVG(score) FROM practice_attempts
```

---

### exercise_drafts

练习草稿表（自动保存）。

```sql
CREATE TABLE IF NOT EXISTS exercise_drafts (
    exercise_id TEXT PRIMARY KEY,          -- 练习 ID（主键）
    exercise_title_snapshot TEXT NOT NULL, -- 练习标题快照
    code_snapshot TEXT NOT NULL,           -- 代码快照
    updated_at TEXT NOT NULL              -- 更新时间
);
```

---

### mentor_api_config

AI API 配置表。

```sql
CREATE TABLE IF NOT EXISTS mentor_api_config (
    id INTEGER PRIMARY KEY,  -- 固定为 1（单行配置）
    host TEXT,               -- API 端点地址
    api_key TEXT,            -- API 密钥（迁移后为空字符串）
    model TEXT,              -- 模型名称
    key_alias TEXT           -- keyring 别名（安全存储引用）
);
```

> 注：`api_key` 字段在旧版迁移后为空字符串，实际密钥通过 `key_alias` 引用 keyring 安全存储。

---

### mentor_sessions

AI 对话会话表。

```sql
CREATE TABLE IF NOT EXISTS mentor_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增 ID
    name TEXT NOT NULL,                     -- 会话名称
    created_at TEXT NOT NULL,              -- 创建时间
    updated_at TEXT NOT NULL               -- 最后更新时间
);
```

**索引**:

```sql
CREATE INDEX idx_mentor_sessions_updated ON mentor_sessions(updated_at DESC);
```

---

### mentor_messages

AI 对话消息表。

```sql
CREATE TABLE IF NOT EXISTS mentor_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增 ID
    session_id INTEGER NOT NULL,            -- 所属会话 ID
    role TEXT NOT NULL,                      -- 角色: user / assistant
    content TEXT NOT NULL,                   -- 消息内容
    created_at TEXT NOT NULL,               -- 创建时间
    FOREIGN KEY(session_id) REFERENCES mentor_sessions(id)
);
```

**索引**:

```sql
CREATE INDEX idx_mentor_messages_session ON mentor_messages(session_id, id);
```

---

### mentor_knowledge_files

扩展知识库文件表。

```sql
CREATE TABLE IF NOT EXISTS mentor_knowledge_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增 ID
    display_name TEXT NOT NULL,             -- 显示名称
    file_path TEXT NOT NULL,                -- 原始文件路径
    excerpt TEXT NOT NULL,                  -- 文件摘录文本
    created_at TEXT NOT NULL                -- 创建时间
);
```

---

### mentor_workspace_state

AI 工作区状态表（单行）。

```sql
CREATE TABLE IF NOT EXISTS mentor_workspace_state (
    id INTEGER PRIMARY KEY,         -- 固定为 1
    active_session_id INTEGER,      -- 当前活跃会话 ID
    use_base INTEGER DEFAULT 1,     -- 是否启用基础知识库: 0/1
    use_personal INTEGER DEFAULT 1, -- 是否启用个性知识库: 0/1
    use_custom INTEGER DEFAULT 1    -- 是否启用扩展文件知识库: 0/1
);
```

---

## 索引一览

| 索引名 | 表 | 列 | 用途 |
|--------|-----|-----|------|
| `idx_lesson_progress_track_completed` | lesson_progress | track_id, completed | 按技术栈统计完成数 |
| `idx_lesson_progress_completed_at` | lesson_progress | completed_at | 连续天数计算 |
| `idx_practice_attempts_exercise` | practice_attempts | exercise_id | 按练习查询历史 |
| `idx_practice_attempts_submitted` | practice_attempts | submitted_at | 按时间排序 |
| `idx_practice_attempts_track` | practice_attempts | track_id | 按技术栈统计 |
| `idx_mentor_messages_session` | mentor_messages | session_id, id | 加载会话消息 |
| `idx_mentor_sessions_updated` | mentor_sessions | updated_at DESC | 按更新时间排序 |

---

## ER 关系图

```text
mentor_sessions (1) ──< mentor_messages (N)
       │
       └── mentor_workspace_state.active_session_id

lesson_progress.lesson_id <── exercise_drafts.exercise_id (逻辑关联)
lesson_progress.lesson_id <── lesson_notes.lesson_id (一对一)
```

> 注：表间关系通过应用层逻辑维护，部分外键未在数据库层面强制。

---

## 数据迁移

### 旧版数据库迁移

当新版数据库不存在时，系统自动从旧版迁移：

```python
def _migrate_legacy_db_if_needed(self):
    if self.db_path.exists():
        return  # 新版数据库已存在
    if LEGACY_DB_PATH.exists():  # db/learner.db
        shutil.copy2(LEGACY_DB_PATH, self.db_path)
```

### 列迁移

`init_db()` 中使用 `ALTER TABLE` 添加新列：

```python
# 如果 mentor_api_config 缺少 key_alias 列
columns = {row[1] for row in cursor.execute("PRAGMA table_info(mentor_api_config)").fetchall()}
if "key_alias" not in columns:
    cursor.execute("ALTER TABLE mentor_api_config ADD COLUMN key_alias TEXT")
```

### API 密钥迁移

旧版明文密钥自动迁移到 keyring：

```python
def _migrate_legacy_api_key_if_needed(self):
    row = self.fetchone("SELECT host, api_key, key_alias, model FROM mentor_api_config WHERE id = 1")
    if row:
        host, legacy_api_key, key_alias, model = row
        if legacy_api_key and not key_alias:  # 有明文但未迁移
            save_secret(API_CREDENTIAL_ALIAS, legacy_api_key)
            # 清空数据库中的明文字段
```

---

## 线程安全

### 写操作锁

所有写操作通过全局锁保护：

```python
_db_lock = threading.Lock()

@contextmanager
def connect(self):
    _db_lock.acquire()
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        _db_lock.release()
```

### 统计缓存

高频统计查询使用内存缓存，TTL 30 秒：

```python
_STATS_CACHE_TTL = 30

def completed_lessons(self) -> int:
    cached = self._get_cached_stats("completed_lessons")
    if cached is not _SENTINEL:
        return cached
    # ... 查询数据库 ...
    self._set_cached_stats("completed_lessons", value)
    return value
```

缓存在以下操作后失效：
- `mark_lesson_completed()`
- `record_attempt()`
- `record_attempts_batch()`
- `reset_learning_progress()`

---

## 相关文档

- [系统架构](../concepts/architecture.md) - 数据流设计
- [模块一览](modules.md) - database 模块接口
- [安全模型](../concepts/security-model.md) - 凭证和加密
