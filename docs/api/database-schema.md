# 数据库 Schema 文档

本文档描述 DevLearnerAI 应用的 SQLite 数据库表结构、索引和 schema 演进历史。

数据库文件位置：`%APPDATA%/DevLearnerAI/data/app.db`（Windows）或 `~/.devlearnerai/data/app.db`（其他平台）。

---

## 连接配置

- **日志模式**: WAL（Write-Ahead Logging）
- **外键约束**: 启用（`PRAGMA foreign_keys = ON`）
- **线程安全**: 全局写锁 + 连接单例

---

## 表结构

### lesson_progress -- 课程进度

记录用户对每门课程的学习状态。

```sql
CREATE TABLE IF NOT EXISTS lesson_progress (
    lesson_id       TEXT PRIMARY KEY,
    track_id        TEXT NOT NULL,
    status          TEXT DEFAULT 'not_started',  -- 'not_started' | 'in_progress' | 'completed'
    completed       INTEGER DEFAULT 0,           -- 0 或 1
    last_opened     TEXT,                         -- YYYY-MM-DD HH:MM:SS
    completed_at    TEXT                          -- YYYY-MM-DD HH:MM:SS
)
```

**索引**:
- `idx_lesson_progress_track_completed` ON `(track_id, completed)` -- 按技术栈统计完成数
- `idx_lesson_progress_completed_at` ON `(completed_at)` -- 按完成时间排序

### lesson_notes -- 课程笔记

用户为每门课程保存的笔记。

```sql
CREATE TABLE IF NOT EXISTS lesson_notes (
    lesson_id   TEXT PRIMARY KEY,
    content     TEXT DEFAULT '',
    updated_at  TEXT                             -- YYYY-MM-DD HH:MM:SS
)
```

### practice_attempts -- 练习评测记录

每次代码提交的评测结果。

```sql
CREATE TABLE IF NOT EXISTS practice_attempts (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id           TEXT NOT NULL,
    exercise_title_snapshot TEXT,                 -- 练习标题快照（防标题变更丢失）
    track_id              TEXT NOT NULL,
    code_snapshot         TEXT,                   -- 提交代码快照
    score                 INTEGER NOT NULL,       -- 0-100
    passed                INTEGER DEFAULT 0,      -- 0 或 1
    duration_sec          INTEGER DEFAULT 0,
    submitted_at          TEXT NOT NULL,          -- YYYY-MM-DD HH:MM:SS
    feedback              TEXT                    -- 评测反馈文本
)
```

**索引**:
- `idx_practice_attempts_exercise` ON `(exercise_id)` -- 按练习查询历史
- `idx_practice_attempts_submitted` ON `(submitted_at)` -- 按时间排序
- `idx_practice_attempts_track` ON `(track_id)` -- 按技术栈筛选

### exercise_drafts -- 练习草稿

自动保存的练习代码草稿。

```sql
CREATE TABLE IF NOT EXISTS exercise_drafts (
    exercise_id             TEXT PRIMARY KEY,
    exercise_title_snapshot TEXT NOT NULL,
    code_snapshot           TEXT NOT NULL,
    updated_at              TEXT NOT NULL         -- YYYY-MM-DD HH:MM:SS
)
```

### mentor_api_config -- AI API 配置

AI 模型接口的连接配置。每条记录最多一行（id=1）。

```sql
CREATE TABLE IF NOT EXISTS mentor_api_config (
    id          INTEGER PRIMARY KEY,             -- 固定值 1
    host        TEXT,                            -- API 端点地址
    api_key     TEXT,                            -- 已迁移到 keyring 后为空字符串
    model       TEXT,                            -- 模型名称
    key_alias   TEXT                             -- keyring 中的存储标识
)
```

### mentor_sessions -- AI 会话

AI 对话的会话容器。

```sql
CREATE TABLE IF NOT EXISTS mentor_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,                   -- 会话名称
    created_at  TEXT NOT NULL,                   -- YYYY-MM-DD HH:MM:SS
    updated_at  TEXT NOT NULL                    -- YYYY-MM-DD HH:MM:SS
)
```

**索引**:
- `idx_mentor_sessions_updated` ON `(updated_at DESC)` -- 按更新时间倒序

### mentor_messages -- AI 消息

每条 AI 对话的消息记录。

```sql
CREATE TABLE IF NOT EXISTS mentor_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL,
    role        TEXT NOT NULL,                   -- 'user' | 'assistant'
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL,                   -- YYYY-MM-DD HH:MM:SS
    FOREIGN KEY(session_id) REFERENCES mentor_sessions(id)
)
```

**索引**:
- `idx_mentor_messages_session` ON `(session_id, id)` -- 按会话加载消息

### mentor_knowledge_files -- 扩展知识库文件

用户手动添加到 AI 知识库的文件。

```sql
CREATE TABLE IF NOT EXISTS mentor_knowledge_files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name  TEXT NOT NULL,
    file_path     TEXT NOT NULL,
    excerpt       TEXT NOT NULL,                 -- 文件摘录（前 6000 字符）
    created_at    TEXT NOT NULL                  -- YYYY-MM-DD HH:MM:SS
)
```

### mentor_workspace_state -- AI 工作区状态

全局唯一的 AI 工作区配置（单行表，id=1）。

```sql
CREATE TABLE IF NOT EXISTS mentor_workspace_state (
    id                 INTEGER PRIMARY KEY,      -- 固定值 1
    active_session_id  INTEGER,                  -- 当前活跃会话 ID
    use_base           INTEGER DEFAULT 1,        -- 是否启用基础知识库
    use_personal       INTEGER DEFAULT 1,        -- 是否启用个性知识库
    use_custom         INTEGER DEFAULT 1         -- 是否启用扩展知识库
)
```

---

## Schema 演进历史

### 初始版本

创建所有核心表：`lesson_progress`, `lesson_notes`, `practice_attempts`, `exercise_drafts`, `mentor_api_config`, `mentor_sessions`, `mentor_messages`, `mentor_knowledge_files`, `mentor_workspace_state`。

### 迁移 1: mentor_api_config 添加 key_alias 列

当 `key_alias` 列不存在时执行：
```sql
ALTER TABLE mentor_api_config ADD COLUMN key_alias TEXT
```
用于将 API 密钥从数据库明文迁移到 keyring 安全存储。

### 迁移 2: practice_attempts 添加快照列

当 `exercise_title_snapshot` 列不存在时执行：
```sql
ALTER TABLE practice_attempts ADD COLUMN exercise_title_snapshot TEXT
```

当 `code_snapshot` 列不存在时执行：
```sql
ALTER TABLE practice_attempts ADD COLUMN code_snapshot TEXT
```
用于保存练习标题和代码的历史快照，防止后续编辑影响历史记录。

### 迁移 3: 性能索引

`init_db()` 中无条件执行 `CREATE INDEX IF NOT EXISTS`，为高频查询添加索引覆盖。

### 迁移 4: 旧版 API 密钥迁移到 keyring

检测 `mentor_api_config` 中是否有未迁移的明文 `api_key`，如有则保存到 keyring 并清空数据库字段，同时设置 `key_alias` 指向 keyring 存储标识。

### 迁移 5: 损坏消息自动修复

`repair_corrupted_mentor_history()` 检测所有历史 AI 消息，将编码损坏的内容（高密度 `?` 字符且无中文）替换为占位提示文本。

### 迁移 6: 旧版数据库文件迁移

当目标数据库不存在但 `db/learner.db` 存在时，自动复制到新的用户数据目录。

### 迁移 7: 默认会话创建

如果 `mentor_sessions` 表为空，自动创建名为"默认对话"的会话并设为活跃。

---

## 统计缓存机制

`AppDatabase` 使用内存缓存加速常用统计查询，TTL 为 30 秒：

| 缓存键 | 数据来源 | 失效时机 |
|--------|----------|----------|
| `completed_lessons` | `COUNT(*) FROM lesson_progress WHERE completed=1` | 课程完成时 |
| `average_score` | `AVG(score) FROM practice_attempts` | 新练习记录时 |
| `active_days_streak` | 综合课程完成和练习提交的日期 | 课程完成时 |

任何写操作（`record_attempt`, `record_attempts_batch`, `mark_lesson_completed`）会自动清除相关缓存。
