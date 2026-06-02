# AI 导师集成

本文档描述 DevLearnerAI 的 AI 导师功能架构，包括 API 通信、知识库系统、流式响应和 UI 集成。

---

## 架构概览

```text
┌──────────────────────────────────────────────────────────┐
│                    AI 导师 UI 层                          │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │  AIMentorPanel    │  │  AIMentorDock    │              │
│  │  (独立页面模式)    │  │  (侧边面板模式)   │              │
│  │                  │  │  内部复用 Panel   │              │
│  └────────┬─────────┘  └────────┬─────────┘              │
│           └──────────┬──────────┘                        │
└──────────────────────┼───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│                   业务逻辑层                               │
│  ┌──────────────────┐  ┌──────────────────┐              │
│  │  chat_handler.py  │  │  知识库管理       │              │
│  │  (对话管理)       │  │  (三级知识库)     │              │
│  └────────┬─────────┘  └────────┬─────────┘              │
│           └──────────┬──────────┘                        │
│                      ▼                                    │
│  ┌──────────────────────────────────────────┐            │
│  │  api_client.py                            │            │
│  │  - send_chat()       (非流式)             │            │
│  │  - send_chat_stream() (流式 SSE)          │            │
│  │  - test_connection()  (连接测试)           │            │
│  │  - fetch_models()     (模型列表)           │            │
│  └──────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│               OpenAI 兼容 API (HTTPS)                     │
└──────────────────────────────────────────────────────────┘
```

---

## API 通信

### 端点构建

API 通信使用标准的 OpenAI 兼容端点：

```python
def build_chat_url(host: str) -> str:
    base = host.rstrip("/")
    # 如果已包含 /v1 则直接拼接，否则自动补全
    return f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"

def build_models_url(host: str) -> str:
    base = host.rstrip("/")
    return f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"
```

### 非流式请求

```python
def send_chat(host, api_key, model, messages, timeout=90) -> str:
    require_https(host)  # 强制 HTTPS
    ctx = create_ssl_context()

    body = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    request = urllib.request.Request(
        build_chat_url(host),
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]
```

### 流式请求

```python
def send_chat_stream(host, api_key, model, messages, on_chunk, timeout=90) -> str:
    require_https(host)
    body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": True,
    }).encode("utf-8")

    # ... 发送请求 ...

    with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
        buffer = ""
        while True:
            chunk = response.read(1024)
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    obj = json.loads(data)
                    content = obj["choices"][0]["delta"].get("content", "")
                    if content:
                        full_text.append(content)
                        on_chunk(content)  # 实时回调
```

### 请求去重

防止相同请求并发发送：

```python
_pending_requests: dict[str, threading.Event] = {}

def send_chat(host, api_key, model, messages, timeout=90) -> str:
    request_key = json.dumps({"host": host, "model": model, "messages": messages}, sort_keys=True)

    with _request_lock:
        if request_key in _pending_requests:
            event = _pending_requests[request_key]
            # 等待已有请求完成，复用结果
            event.wait(timeout=timeout)
            return _pending_results.pop(request_key)
```

### 连接状态缓存

连接测试结果缓存 5 分钟，避免频繁测试：

```python
_connection_cache: dict[str, tuple[float, str]] = {}
_CONNECTION_CACHE_TTL = 300  # 5 分钟
```

---

## 知识库系统

AI 导师支持三级知识库，用于提供上下文感知的回答：

### 知识库层次

```text
┌────────────────────────────────┐
│ 1. 基础知识库 (use_base)       │
│    内置的编程教学知识            │
├────────────────────────────────┤
│ 2. 个性知识库 (use_personal)   │
│    根据学习进度自动构建          │
├────────────────────────────────┤
│ 3. 扩展文件知识库 (use_custom) │
│    用户上传的参考文档            │
└────────────────────────────────┘
```

### 知识库状态持久化

```python
# 数据库表: mentor_workspace_state
CREATE TABLE mentor_workspace_state (
    id INTEGER PRIMARY KEY,
    active_session_id INTEGER,
    use_base INTEGER DEFAULT 1,      -- 是否启用基础知识库
    use_personal INTEGER DEFAULT 1,  -- 是否启用个性知识库
    use_custom INTEGER DEFAULT 1     -- 是否启用扩展文件知识库
);
```

### 扩展知识库文件

用户可以上传参考文件到知识库：

```python
# 数据库表: mentor_knowledge_files
CREATE TABLE mentor_knowledge_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,    -- 显示名称
    file_path TEXT NOT NULL,       -- 原始文件路径
    excerpt TEXT NOT NULL,         -- 文件摘录文本
    created_at TEXT NOT NULL
);
```

---

## 系统上下文构建

AI 对话时会自动构建系统上下文，包含：

```text
系统消息构建:
  ├── 角色设定（编程导师身份）
  ├── 当前课程信息（如果用户正在学习某课程）
  ├── 学习进度摘要
  ├── 知识库内容（根据开关配置）
  └── 最近 12 条历史消息
```

---

## 会话管理

### 多会话支持

用户可以创建多个独立的对话会话，按主题组织：

```python
# 数据库表: mentor_sessions
CREATE TABLE mentor_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

# 数据库表: mentor_messages
CREATE TABLE mentor_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,       -- 'user' 或 'assistant'
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES mentor_sessions(id)
);
```

### 会话裁剪

防止长时间会话占用过多资源：

```python
def trim_mentor_messages(self, session_id, keep_last=200):
    """裁剪旧消息，只保留最近的 N 条"""
    # ... 删除多余消息 ...
```

---

## Markdown 渲染

AI 响应通过安全的 Markdown 渲染器处理：

```text
AI 原始响应 (Markdown 文本)
    │
    ▼
mistune.html(text) → 原始 HTML
    │
    ▼
sanitize_html(html) → 白名单净化
    │
    ▼
bubble_html(role, content) → 聊天气泡 HTML
    │
    ▼
QTextBrowser.setHtml() → 渲染显示
```

### 代码高亮

```python
def bubble_html(role: str, content: str) -> str:
    # 内联 CSS 样式
    style = """
    pre {
        background: #1e293b;
        color: #e2e8f0;
        border-radius: 12px;
        padding: 14px 16px;
        font-family: Consolas, monospace;
    }
    code {
        background: #f0f4ff;
        border-radius: 4px;
        padding: 1px 4px;
        color: #2563eb;
    }
    """
```

---

## 快捷提问功能

AI 导师支持上下文感知的快捷提问：

| 按钮 | 功能 | 构建的提示 |
|------|------|-----------|
| 解释当前课程 | 基于正在学习的课程提问 | "请解释一下这节课的核心知识点..." |
| 分析当前代码 | 分析练习中的代码 | "请帮我分析这段代码..." |
| 拆解当前项目 | 将项目分解为小任务 | "帮我把这个项目拆成可执行的步骤..." |

```python
def ask_ai_about_editor(self):
    selected = self.practice.editor.textCursor().selectedText().strip()
    if not selected:
        selected = self.practice.editor.toPlainText().strip()
    if selected:
        prompt = f"请帮我分析这段代码，并指出如何改进：\n{selected}"
```

---

## 流式响应回退

当流式请求失败时，自动回退到非流式模式：

```python
def send_chat_stream(host, api_key, model, messages, on_chunk, timeout=90) -> str:
    try:
        # 流式请求
        ...
    except Exception:
        # 仅在未收到任何 chunk 时回退
        if not full_text:
            return send_chat(host, api_key, model, messages, timeout)
```

---

## 相关文档

- [API 集成参考](../reference/api-integration.md) - API 通信协议详情
- [安全模型](security-model.md) - HTTPS 和 XSS 防护
- [常见问题](../troubleshooting/common-issues.md) - AI 连接问题排查
